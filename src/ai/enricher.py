"""Profile-driven content enrichment."""

import asyncio
import json
import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, TypeVar

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
)
from tenacity import retry, retry_if_exception_type, retry_if_not_exception_type, stop_after_attempt, wait_exponential

from .client import AIClient
from .errors import AIProviderUnavailableError
from .localization import normalize_language
from .theme_direction import ThemeDirectionJudge
from .theme_picker import ThemePicker
from .prompting.enrichment import (
    MAX_TOOL_REQUESTS,
    artifact_prompt,
    block_prompt,
    item_context,
    tool_planning_prompt,
    tool_results_text,
)
from .utils import gather_ai_tasks, parse_json_response
from ..models import ArtifactSource, ContentArtifact, ContentBlock, ContentItem
from ..processing.ashare_themes import (
    NEUTRAL,
    MemberFetcher,
    ThemeIndex,
    attach_themes,
    matching_text,
    pick_members,
)
from ..processing.mainline import load_state as load_mainline_state
from ..processing.member_profile import MemberProfiles, render_listing
from ..processing.profiles import LoadedProfile, ProfileBlock, ProfileRegistry
from ..processing.tools import ToolRegistry, ToolResult

logger = logging.getLogger(__name__)

# The page ranks members by three-month relative strength, not by how well they
# fit the story. Five is what a line can carry; the first item that names a
# theme keeps the page order, and later items re-rank the same list against
# their own story so the digest does not repeat one ticker set all day.
MEMBER_LIMIT = 5
MEMBER_RANK_PROMPT = """你是 A 股分析师。给定一条新闻、一个题材和该题材的成分股名单，选出与这条新闻关系最直接的 5 只股票。

规则：
- 只能从名单里逐字选择，不要新造名称。
- 按"新闻事件→该股票主营是否直接受影响"排序，越直接越靠前。
- 只做业务相关判断，不考虑股价涨跌、市值大小。
- 名单里确实没有直接相关的，按名单顺序补足 5 只。
- 部分股票后面用「｜」标注了主营构成（如「吉视传媒(601929)｜有线电视传输」）。优先据此判断业务相关性；未标注的按名称判断。

输出格式：只输出 JSON。
{"picks": ["股票名", "股票名"]}"""

ModelT = TypeVar("ModelT", bound=BaseModel)

class ToolRequest(BaseModel):
    block_id: str
    tool: str
    arguments: dict[str, Any]
    purpose: str


class ToolPlan(BaseModel):
    tool_requests: list[ToolRequest] = Field(default_factory=list)


class GeneratedArtifact(BaseModel):
    title: str
    blocks: list[ContentBlock]

    @model_validator(mode="after")
    def validate_non_empty_content(self) -> "GeneratedArtifact":
        if not self.title.strip():
            raise ValueError("title must not be empty")
        for block in self.blocks:
            if not block.title.strip() or not block.content.strip():
                raise ValueError(f"block {block.id} must not be empty")
        return self


class GeneratedBlock(BaseModel):
    title: str = ""
    block: Optional[ContentBlock] = None

    @model_validator(mode="after")
    def validate_non_empty_block(self) -> "GeneratedBlock":
        if self.block and (
            not self.block.title.strip() or not self.block.content.strip()
        ):
            raise ValueError(f"block {self.block.id} must not be empty")
        return self


class GeneratedBlockWithHeader(GeneratedBlock):
    @field_validator("title")
    @classmethod
    def validate_non_empty_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value


@dataclass
class EnrichmentBatchResult:
    succeeded_ids: list[str] = field(default_factory=list)
    failures: dict[str, str] = field(default_factory=dict)

    @property
    def succeeded_count(self) -> int:
        return len(self.succeeded_ids)

    @property
    def failed_count(self) -> int:
        return len(self.failures)

    @property
    def failed_ids(self) -> list[str]:
        return list(self.failures)

    @property
    def status(self) -> str:
        if not self.failures:
            return "success"
        if self.succeeded_ids:
            return "partial_failure"
        return "failure"


class ContentEnricher:
    """Generate localized block artifacts with profile-scoped tools."""

    def __init__(
        self,
        ai_client: AIClient,
        profiles: ProfileRegistry,
        languages: list[str],
        console: Optional[Console] = None,
        tools: Optional[ToolRegistry] = None,
        *,
        concurrency: int = 1,
    ):
        self.client = ai_client
        self.profiles = profiles
        self.languages = languages
        self.console = console or Console(stderr=True)
        self.tools = tools or ToolRegistry()
        self.concurrency = max(concurrency, 1)
        self._theme_index: Optional[ThemeIndex] = None
        # One extra short call per item that matched themes, sharing the
        # enrichment concurrency so the run does not fan out any wider.
        self._direction_judge = ThemeDirectionJudge(
            ai_client, concurrency=self.concurrency
        )
        # Fallback for items the top-200 heat list does not name: one short
        # call per such item, so the run does not fan out any wider. The daily
        # mainline matrix rides along with it: which industry line each theme
        # belongs to, and how many limit-ups that line had at the last close.
        self._mainline = load_mainline_state()
        # Main-business strings for the names the re-rank pass sees. A bare
        # name cannot tell 景观设计 from 算力租赁, which is why the page order
        # kept putting unrelated companies at the front of a theme.
        self._member_profiles = MemberProfiles()
        self._theme_picker = ThemePicker(ai_client, mainline=self._mainline)
        # Themes whose tickers this run already rendered; see _attach_members.
        self._rendered_themes: set[str] = set()
        self._validate_profile_tools()

    def _validate_profile_tools(self) -> None:
        for profile_id in self.profiles.ids:
            profile = self.profiles.get(profile_id)
            for block in profile.definition.enrichment.blocks:
                unknown = set(block.tools) - self.tools.names
                if unknown:
                    raise ValueError(
                        f"Profile {profile_id} block {block.id} uses unknown tools: "
                        f"{', '.join(sorted(unknown))}"
                    )

    @retry(
        retry=retry_if_exception_type(Exception) & retry_if_not_exception_type(AIProviderUnavailableError),
        stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10), reraise=True,
    )
    async def _complete(self, **kwargs: Any) -> str:
        return await self.client.complete(**kwargs)

    async def _complete_model(
        self,
        model: type[ModelT],
        *,
        system: str,
        user: str,
        error_message: str,
        validator: Optional[Callable[[ModelT], None]] = None,
    ) -> ModelT:
        validation_error: Optional[Exception] = None
        for attempt in range(2):
            request: dict[str, Any] = {
                "system": system,
                "user": user,
                "temperature": 0,
            }
            response = await self._complete(**request)
            parsed = parse_json_response(response)
            try:
                result = model.model_validate(parsed)
                if validator:
                    validator(result)
                return result
            except (ValidationError, ValueError) as exc:
                validation_error = exc
                user += (
                    "\n\nYour previous response did not satisfy the output contract. "
                    f"Validation error: {exc}. Return only a corrected JSON object."
                )
        raise ValueError(error_message) from validation_error

    async def enrich_batch(self, items: list[ContentItem]) -> EnrichmentBatchResult:
        semaphore = asyncio.Semaphore(self.concurrency)

        async def process(
            item: ContentItem, task_id: TaskID
        ) -> tuple[str, Optional[Exception]]:
            async with semaphore:
                try:
                    await self._enrich_item(item)
                except AIProviderUnavailableError:
                    raise
                except Exception as exc:
                    logger.error("Error enriching item %s: %s", item.id, exc)
                    if self._apply_analysis_fallback(item):
                        logger.warning(
                            "Kept item %s with its analysis summary only; the "
                            "enriched blocks are missing for this run",
                            item.id,
                        )
                        return item.id, None
                    return item.id, exc
                finally:
                    progress.advance(task_id)
            return item.id, None

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            transient=True,
            console=self.console,
        ) as progress:
            task_id = progress.add_task("Enriching", total=len(items))
            outcomes = await gather_ai_tasks([process(item, task_id) for item in items])

        self._log_theme_metrics(items)

        return EnrichmentBatchResult(
            succeeded_ids=[item_id for item_id, exc in outcomes if exc is None],
            failures={
                item_id: f"{type(exc).__name__}: {exc}"
                for item_id, exc in outcomes
                if exc is not None
            },
        )

    def _annotate_mainline(self, item: ContentItem) -> None:
        """Attach each theme's industry line and its last-close limit-up count.

        Kept here rather than in the index lookup: the line is a digest-time
        annotation about the market, not a property of the theme catalogue.
        """
        if self._mainline is None or not self._mainline.available:
            return
        for theme in (item.metadata or {}).get("ashare_themes") or []:
            self._mainline.annotate(theme)

    def _log_decision(self, item: ContentItem) -> None:
        """One line per item: which themes, which pass, which line, how many names.

        The published digest shows the result but not how it was reached, and
        the default log level is WARNING, so this line is the only record of
        which pass chose a theme and whether the mainline annotation was there.
        """
        themes = (item.metadata or {}).get("ashare_themes") or []
        if not themes:
            return
        parts = []
        for theme in themes:
            state = theme.get("mainline") or {}
            parts.append(
                f"{theme.get('name')}"
                f"[{theme.get('picked') or '?'}"
                f"/{theme.get('direction') or '?'}"
                f"/主线{state.get('line', '-')}{state.get('today', '-')}"
                f"/{len(theme.get('members') or [])}只]"
            )
        logger.warning(
            "Theme decision %s | %s | %s",
            item.id,
            (item.title or "")[:40],
            " ".join(parts),
        )

    def _log_theme_metrics(self, items: list[ContentItem]) -> None:
        """One WARNING block with the run's countable theme statistics.

        Each number points at a specific failure: a high model share means the
        heat list and the keyword recall missed the day's wording, a repeated
        ticker means the member list is not being re-ranked per story, a theme
        without members means the lianban fetch ran out of budget, and a low
        mainline-active share means the picks are drifting away from what the
        market traded.
        """
        sources: Counter = Counter()
        names: list[str] = []
        tickers: list[str] = []
        no_members = 0
        neutral = 0
        lines_total = 0
        lines_active = 0
        for item in items:
            for theme in (item.metadata or {}).get("ashare_themes") or []:
                sources[str(theme.get("picked") or "?")] += 1
                name = str(theme.get("name") or "")
                if name:
                    names.append(name)
                members = theme.get("members") or []
                if not members:
                    no_members += 1
                tickers.extend(str(member).split("（")[0].strip() for member in members)
                if theme.get("direction") == NEUTRAL:
                    neutral += 1
                state = theme.get("mainline")
                if state:
                    lines_total += 1
                    if state.get("today"):
                        lines_active += 1
        if not names:
            logger.warning("Theme metrics: no theme line this run")
            return
        repeated_theme = "、".join(
            f"{name}x{count}" for name, count in Counter(names).most_common(3) if count > 1
        ) or "none"
        repeated_ticker = "、".join(
            f"{name}x{count}" for name, count in Counter(tickers).most_common(3) if count > 1
        ) or "none"
        logger.warning(
            "Theme metrics: %d theme lines over %d items, source %s, no-members %d, "
            "neutral %d, mainline-active %d/%d, repeated themes %s, repeated tickers %s",
            len(names),
            len(items),
            "、".join(f"{key}{value}" for key, value in sorted(sources.items())),
            no_members,
            neutral,
            lines_active,
            lines_total,
            repeated_theme,
            repeated_ticker,
        )

    def _apply_analysis_fallback(self, item: ContentItem) -> bool:
        """Keep a failed item in the digest using its first-pass analysis.

        The daily summary only renders items that carry an artifact for the
        language, so a single enrichment failure used to drop the story from
        the digest entirely. Reusing the analysis summary keeps the item, just
        without the background and impact blocks.
        """
        processing = item.processing
        analysis = processing.analysis if processing else None
        summary = (analysis.summary or "").strip() if analysis else ""
        if not summary:
            return False
        for language in self.languages:
            if language in processing.artifacts:
                continue
            processing.artifacts[language] = ContentArtifact(
                language=language,
                title=normalize_language(item.title, language),
                blocks=[
                    ContentBlock(
                        id="summary",
                        type="section",
                        title="",
                        content=summary,
                        primary=True,
                    )
                ],
                sources=[],
            )
        return True

    async def _enrich_item(self, item: ContentItem) -> None:
        if not item.processing or not item.processing.analysis:
            raise ValueError("Item must be analyzed before enrichment")
        profile = self.profiles.get(item.processing.classification.profile)
        for language in self.languages:
            item.processing.artifacts.pop(language, None)
        tool_results = await self._plan_and_execute_tools(item, profile)
        sources = self._sources_from_tool_results(tool_results)

        artifacts = {}
        for language in self.languages:
            generated = await self._generate_artifact(
                item, profile, language, tool_results
            )
            self._expand_request_source_refs(generated.blocks, tool_results)
            self._validate_blocks(generated.blocks, profile, tool_results)
            generated.title = normalize_language(generated.title, language)
            for block in generated.blocks:
                block.title = normalize_language(block.title, language)
                block.content = normalize_language(block.content, language)
            referenced = {
                source_id
                for block in generated.blocks
                for source_id in block.source_refs
            }
            artifacts[language] = ContentArtifact(
                language=language,
                title=generated.title,
                blocks=generated.blocks,
                sources=[source for source in sources.values() if source.id in referenced],
            )
        item.processing.artifacts.update(artifacts)
        await self._refresh_themes(item)

    async def _refresh_themes(self, item: ContentItem) -> None:
        """Re-run the A-share theme lookup now that the enriched blocks exist.

        The analysis pass only sees the headline and the one-line summary, and
        most theme terms first appear in the background or impact block. The
        heat-list lookup itself is token-free; only an item the heat list misses
        costs one short pick call, and the direction verdict that follows is one
        more call per item that ended up with themes. Members are fetched last,
        for the themes the line will actually show.
        """
        if self._theme_index is None:
            self._theme_index = ThemeIndex()
        if not self._theme_index.available:
            return
        await attach_themes(
            item, self._theme_index, MemberFetcher(), picker=self._theme_picker
        )
        self._annotate_mainline(item)
        await self._direction_judge.judge(item)
        await self._attach_members(item)
        self._log_decision(item)

    async def _attach_members(self, item: ContentItem) -> None:
        """Fetch member lists for the themes the digest will actually render.

        Runs after the direction pass: a theme judged neutral never reaches the
        line, so fetching its members first spent roughly half of the lianban
        budget on lists nobody saw. On 2026-11-18 that extra load is what
        tripped the limiter and left five themes with no names at all. A theme
        whose verdict call failed still renders under 方向待定, so it is
        fetched here too.

        A theme's first item keeps the page order and shows five names. Later
        items re-rank the same member list against their own story, because the
        page order is a three-month strength ranking rather than a fit for the
        story: repeating it unchanged put one ticker set in nine of thirty-three
        lines on 2026-11-18.
        """
        themes = (item.metadata or {}).get("ashare_themes") or []
        fetcher = MemberFetcher()
        for theme in themes:
            if theme.get("direction") == NEUTRAL or theme.get("members"):
                continue
            key = str(theme.get("slug") or theme.get("name") or "")
            members = await fetcher.get(
                theme["slug"], theme.get("members_count"), theme.get("name")
            )
            theme["member_total"] = len(members)
            if key and key in self._rendered_themes:
                theme["members"] = await self._rank_members(
                    item, str(theme.get("name") or ""), members
                )
                continue
            if key:
                self._rendered_themes.add(key)
            theme["members"] = pick_members(members, MEMBER_LIMIT)

    async def _rank_members(
        self, item: ContentItem, theme_name: str, members: list[str]
    ) -> list[str]:
        """Re-rank a repeated theme's members against this story.

        The page order is a three-month strength ranking, so the same theme on a
        second story would otherwise print the same five tickers again. The
        model sees the story and the theme's own list and keeps the names whose
        business the event actually touches; anything it cannot place falls back
        to the page order so the line is never short.
        """
        if len(members) <= MEMBER_LIMIT:
            return list(members)
        excerpt = " ".join(matching_text(item).split())[:800]
        profiles = await self._member_profiles.annotate(members)
        listing = render_listing(members, profiles, 120)
        try:
            response = await self.client.complete(
                system=MEMBER_RANK_PROMPT,
                user=f"新闻：{excerpt}\n\n题材：{theme_name}\n成分股：{listing}",
                temperature=0,
                max_tokens=160,
            )
        except Exception as exc:  # noqa: BLE001 - page order is still a valid line
            logger.warning("Member re-rank failed for %s: %s", theme_name, exc)
            return pick_members(members, MEMBER_LIMIT)
        parsed = parse_json_response(response or "")
        raw = parsed.get("picks") if isinstance(parsed, dict) else None
        picked: list[str] = []
        if isinstance(raw, list):
            for entry in raw:
                name = str(entry or "").strip()
                name = name.split("（")[0].split("(")[0].strip()
                if not name:
                    continue
                for member in members:
                    if name in member and member not in picked:
                        picked.append(member)
                        break
        for member in pick_members(members, MEMBER_LIMIT):
            if member not in picked:
                picked.append(member)
        final = picked[:MEMBER_LIMIT]
        # Where the model's picks sit in lianban's own order. If they cluster in
        # the first thirty, the 120-name window is mostly dead weight and can be
        # tightened without losing anything.
        positions = [members.index(name) + 1 for name in final if name in members]
        logger.warning(
            "Member re-rank %s: %s | 原序位置 %s",
            theme_name,
            "、".join(final),
            positions,
        )
        return final

    @staticmethod
    def _expand_request_source_refs(
        blocks: list[ContentBlock],
        tool_results: list[ToolResult],
    ) -> None:
        """Expand a request-level citation to its concrete result citations."""
        request_sources = {
            (result.block_id, result.request_id): [
                f"{result.request_id}-{index}"
                for index, _ in enumerate(result.results, start=1)
            ]
            for result in tool_results
        }
        for block in blocks:
            expanded = []
            for source_ref in block.source_refs:
                expanded.extend(
                    request_sources.get((block.id, source_ref), [source_ref])
                )
            block.source_refs = list(dict.fromkeys(expanded))

    async def _plan_and_execute_tools(
        self, item: ContentItem, profile: LoadedProfile
    ) -> list[ToolResult]:
        allowed = {
            block.id: set(block.tools)
            for block in profile.definition.enrichment.blocks
        }
        if not any(allowed.values()):
            return []

        def validate_tool_plan(plan: ToolPlan) -> None:
            for request in plan.tool_requests[:MAX_TOOL_REQUESTS]:
                if request.block_id not in allowed:
                    raise ValueError(f"Tool request targets unknown block: {request.block_id}")
                if request.tool not in allowed[request.block_id]:
                    raise ValueError(
                        f"Tool {request.tool} is not allowed for block {request.block_id}"
                    )

        plan = await self._complete_model(
            ToolPlan,
            system=tool_planning_prompt(profile.definition.enrichment.blocks),
            user=item_context(item, profile, include_content=True),
            error_message="Invalid enrichment tool plan",
            validator=validate_tool_plan,
        )

        results = []
        seen = set()
        history_requested = False
        for request in plan.tool_requests[:MAX_TOOL_REQUESTS]:
            if request.tool == "history_search":
                if history_requested:
                    continue
                history_requested = True
            key = (request.block_id, request.tool, json.dumps(request.arguments, sort_keys=True))
            if key in seen:
                continue
            seen.add(key)
            results.append(
                await self.tools.execute(
                    request_id=f"tool-{len(results) + 1}",
                    block_id=request.block_id,
                    tool=request.tool,
                    arguments=request.arguments,
                    current_item=item,
                )
            )
        return results

    async def _generate_artifact(
        self,
        item: ContentItem,
        profile: LoadedProfile,
        language: str,
        tool_results: list[ToolResult],
    ) -> GeneratedArtifact:
        configured_blocks = profile.definition.enrichment.blocks
        result_block_ids = {result.block_id for result in tool_results}
        base_blocks = [
            block for block in configured_blocks if block.id not in result_block_ids
        ]
        title = ""
        generated_by_id: dict[str, ContentBlock] = {}

        if base_blocks:
            required_base_ids = {
                block.id for block in base_blocks if not block.optional
            }
            allowed_base_ids = {block.id for block in base_blocks}

            def validate_required_blocks(generated: GeneratedArtifact) -> None:
                generated_ids = [block.id for block in generated.blocks]
                unknown = set(generated_ids) - allowed_base_ids
                if unknown:
                    raise ValueError(
                        "unknown blocks: " + ", ".join(sorted(unknown))
                    )
                if len(generated_ids) != len(set(generated_ids)):
                    raise ValueError("duplicate block IDs")
                missing = required_base_ids - set(generated_ids)
                if missing:
                    raise ValueError(
                        "missing required blocks: " + ", ".join(sorted(missing))
                    )

            generated = await self._complete_model(
                GeneratedArtifact,
                system=artifact_prompt(profile, language, base_blocks),
                user=(
                    item_context(item, profile, include_content=True)
                    + "\n\n# Tool results\n\nNo tool results are available to these blocks."
                ),
                error_message="Invalid enrichment artifact",
                validator=validate_required_blocks,
            )
            title = generated.title.strip()
            allowed_ids = {block.id for block in base_blocks}
            configured_ids = {block.id for block in configured_blocks}
            for generated_block in generated.blocks:
                if generated_block.id not in allowed_ids:
                    if generated_block.id in configured_ids:
                        continue
                    raise ValueError(
                        f"Artifact contains unknown block: {generated_block.id}"
                    )
                if generated_block.id in generated_by_id:
                    raise ValueError(
                        f"Artifact contains duplicate block: {generated_block.id}"
                    )
                generated_by_id[generated_block.id] = generated_block
            missing = {
                block.id
                for block in base_blocks
                if not block.optional and block.id not in generated_by_id
            }
            if missing:
                raise ValueError(
                    f"Artifact is missing required blocks: {', '.join(sorted(missing))}"
                )

        for block in configured_blocks:
            if block.id not in result_block_ids:
                continue
            block_results = [
                result for result in tool_results if result.block_id == block.id
            ]
            response_model = GeneratedBlockWithHeader if not title else GeneratedBlock

            def validate_requested_block(generated: GeneratedBlock) -> None:
                if generated.block is None:
                    if not block.optional:
                        raise ValueError(f"missing required block: {block.id}")
                    return
                if generated.block.id != block.id:
                    raise ValueError(
                        f"block ID {generated.block.id} does not match {block.id}"
                    )

            generated = await self._complete_model(
                response_model,
                system=block_prompt(
                    profile,
                    language,
                    block,
                    include_header=not title,
                ),
                user=(
                    item_context(item, profile, include_content=True)
                    + f"\n\n# Tool results for block `{block.id}`\n\n"
                    + tool_results_text(block_results)
                ),
                error_message=f"Invalid enrichment block: {block.id}",
                validator=validate_requested_block,
            )

            if not title:
                title = generated.title.strip()
            if generated.block is None:
                if not block.optional:
                    raise ValueError(f"Artifact is missing required block: {block.id}")
                continue
            if generated.block.id != block.id:
                raise ValueError(
                    f"Artifact block {generated.block.id} does not match requested block {block.id}"
                )
            generated_by_id[block.id] = generated.block

        if not title:
            raise ValueError("Enrichment artifact title cannot be empty")
        blocks = [
            generated_by_id[block.id]
            for block in configured_blocks
            if block.id in generated_by_id
        ]
        configured_by_id = {block.id: block for block in configured_blocks}
        for generated_block in blocks:
            generated_block.primary = configured_by_id[generated_block.id].primary
        return GeneratedArtifact(title=title, blocks=blocks)

    @staticmethod
    def _sources_from_tool_results(
        results: list[ToolResult],
    ) -> dict[str, ArtifactSource]:
        sources = {}
        for result in results:
            for index, entry in enumerate(result.results, start=1):
                source_id = f"{result.request_id}-{index}"
                sources[source_id] = ArtifactSource(
                    id=source_id,
                    title=entry["title"],
                    url=entry["url"],
                )
        return sources

    @staticmethod
    def _validate_blocks(
        blocks: list[ContentBlock],
        profile: LoadedProfile,
        tool_results: list[ToolResult],
    ) -> None:
        configured: dict[str, ProfileBlock] = {
            block.id: block for block in profile.definition.enrichment.blocks
        }
        seen = set()
        for block in blocks:
            if block.id not in configured:
                raise ValueError(f"Artifact contains unknown block: {block.id}")
            if block.id in seen:
                raise ValueError(f"Artifact contains duplicate block: {block.id}")
            seen.add(block.id)
            if not block.title.strip() or not block.content.strip():
                raise ValueError(f"Artifact block {block.id} cannot be empty")
            block_source_ids = {
                f"{result.request_id}-{index}"
                for result in tool_results
                if result.block_id == block.id
                for index, _ in enumerate(result.results, start=1)
            }
            unknown_refs = set(block.source_refs) - block_source_ids
            if unknown_refs:
                raise ValueError(
                    f"Block {block.id} contains unknown source refs: "
                    f"{', '.join(sorted(unknown_refs))}"
                )
        required = {block.id for block in configured.values() if not block.optional}
        missing = required - seen
        if missing:
            raise ValueError(
                f"Artifact is missing required blocks: {', '.join(sorted(missing))}"
            )