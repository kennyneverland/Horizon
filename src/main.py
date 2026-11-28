"""CLI entry point for Horizon."""

import argparse
import asyncio
import shlex
import sys
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv
from rich.console import Console

from ._cli import add_data_dir_arguments, add_log_level_argument
from .console_icons import get_icons
from .logging_config import configure_logging
from .storage.manager import ConfigError, StorageManager
from .orchestrator import BalancedDigestResult, HorizonOrchestrator
from .collection_window import collection_hours
from .models import AIProvider
from .processing import ashare_brief
from .processing.lianban_calendar import (
    archive_exists,
    calendar_note,
    fetch_calendar,
    load_events,
    parse,
    save_events,
    to_queries,
)
from .processing.premarket import fetch_premarket
from .processing.mainline import refresh as refresh_mainline
from .processing.source_cap import apply_balanced_digest_with_cap, load_per_source_limit
from .processing.theme_index_refresh import is_refresh_day, refresh_theme_index


console = Console(stderr=True)


class _SourceCappedOrchestrator(HorizonOrchestrator):
    """Orchestrator that also enforces an optional per-source digest cap.

    The cap is read from ``data/digest_limits.json`` and applied on top of the
    regular per-group quotas; when a source exceeds the cap, its lowest-scored
    extra items leave the candidate pool so other sources can fill those slots.
    """

    def __init__(self, *args, per_source_limit=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.per_source_limit = per_source_limit
        # 日历事件只在本次运行注入一次：重复注入会重复检索同一批 query。
        self._calendar_injected = False
        self._event_queries: set[str] = set()
        # 早盘快讯转出来的 query，命中条目打 brief_driven，同样提到组内最前。
        self._brief_queries: set[str] = set()

    def apply_balanced_digest(self, items, *, log: bool = True):
        return apply_balanced_digest_with_cap(
            self,
            items,
            super().apply_balanced_digest,
            limit=self.per_source_limit,
            log=log,
        )

    async def fetch_all_sources(self, since):
        """抓取前先补两类 query，抓完再给命中条目打标。

        两类都不进正文：三星事件要的是「数据落地后市场怎么读」，早盘快讯要的是
        「这条快讯背后有没有一篇完整报道」。检索回来的报道才进板块。任何一个源
        取不到都跳过，抓取照常进行。
        """
        if not self._calendar_injected:
            self._calendar_injected = True
            await self._inject_calendar_queries()
            await self._inject_brief_queries()
        items = await super().fetch_all_sources(since)
        for item in items:
            query = (item.metadata or {}).get("gn_query")
            if not query:
                continue
            if query in self._event_queries:
                item.metadata["event_driven"] = True
            elif query in self._brief_queries:
                item.metadata["brief_driven"] = True
        return items

    async def _inject_calendar_queries(self) -> None:
        """把前一日 09:00 之后的三星事件变成 Google News 检索 query。

        日历页只保留「今天及以后」——次日再抓，前一天那一整块已经不在了。所以
        当天跑的时候先把今天的三星落盘，次日读存档；存档没有（首次上线那天）
        才退回页面，页面里若还留着昨天也能用上。

        09:00 之前的事件，前一日早报已经覆盖过，再搜一次是重复；名称残缺的
        条目检索不出东西，由 lianban_calendar 一并跳过。
        """
        sources = self.config.sources.google_news
        if not sources or not sources.enabled:
            return
        # 北京时间的「今天」和「昨天」：早报 09:02 起跑，要的是前一日盘后到今早
        # 落地的事件，而落盘的是今天这一整天的三星。
        now = datetime.now(timezone(timedelta(hours=8)))
        today = now.strftime("%Y-%m-%d")
        yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        page = None
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                page = await fetch_calendar(client)
        except Exception as exc:  # noqa: BLE001 - 客户端都建不起来，同样只是「没取到」
            self.console.print(f"[yellow]日历客户端不可用：{exc}[/yellow]")
        page_ok = page is not None
        if page_ok:
            today_events = parse(page, today)
            if today_events and save_events(today_events, today):
                self.console.print(
                    f"[dim]日历落盘：{today} {len(today_events)} 条[/dim]"
                )
        events = load_events(yesterday)
        if not events and page_ok:
            events = parse(page, yesterday)
        if not events:
            # 三种「没有」不能共用一句话：页面取到了、昨日确实没有三星，这是确定的
            # 结论；页面取不到、也没有存档，只是这次没取到——讲成「无事件」，下次读
            # 日志的人会以为那天真的没有数据落地。
            level, text = calendar_note(
                yesterday, 0, page_ok, archive_exists(yesterday)
            )
            self.console.print(f"[{level}]{text}[/{level}]")
            return
        existing = {query.query for query in sources.queries}
        for query in to_queries(events):
            if query.query in existing:
                continue
            sources.queries.append(query)
            self._event_queries.add(query.query)
            self.console.print(f"[dim]日历事件进检索：{yesterday} {query.query}[/dim]")

    async def _inject_brief_queries(self) -> None:
        """早盘快讯 → 检索 query。

        09:25 定稿的那份快讯，绝大多数是单行、没有正文的短消息：信息是真的，但
        AI 评分上不去、也落不到题材词上，最后只能挤在「要闻补充」小字块里。拿
        标题去检索，把它补成一篇可评分的完整报道，才有资格进中国股市板块。

        这里读的是此刻页面上的快讯（不等 09:25 定稿）：早报 09:40 要出，等不起。
        定稿那份由 summarizer 自己再读一次，两处互不影响。
        """
        sources = self.config.sources.google_news
        if not sources or not sources.enabled:
            return
        try:
            brief = await fetch_premarket()
        except Exception as exc:  # noqa: BLE001 - 快讯拿不到不影响主流程
            self.console.print(f"[yellow]早盘快讯读取失败：{exc}[/yellow]")
            return
        news = (brief or {}).get("news") or []
        if not news:
            self.console.print("[dim]早盘快讯为空，跳过注入[/dim]")
            return
        existing = {query.query for query in sources.queries}
        for query in ashare_brief.to_queries(news):
            if query.query in existing:
                continue
            sources.queries.append(query)
            self._brief_queries.add(query.query)
            self.console.print(f"[dim]快讯进检索：{query.query}[/dim]")

    def _apply_balanced_digest_base(self, items, *, log: bool = True):
        """配额分配后再做一次稳定重排：事件与快讯检索回来的条目提到同组最前。

        分数不动，页面上不会出现虚高的星级；``sorted`` 是稳定的，其余条目
        保持原来的评分顺序。
        """
        result = super()._apply_balanced_digest_base(items, log=log)
        picked = sorted(
            result.items,
            key=lambda item: not (
                (item.metadata or {}).get("event_driven")
                or (item.metadata or {}).get("brief_driven")
            ),
        )
        return replace(result, items=picked)


def print_banner():
    """Print the application banner."""
    banner = r"""
[bold blue]
  _    _            _
 | |  | |          (_)
 | |__| | ___  _ __ _ ___  ___  _ __
 |  __  |/ _ \| '__| |_  / / _ \| '_ \
 | |  | | (_) | |  | |/ / | (_) | | | |
 |_|  |_|\___/|_|  |_/___| \___/|_| |_|
[/bold blue]
[cyan]  AI-Driven Information Aggregation System[/cyan]
    """
    console.print(banner)


def _hours_argument(value: str) -> int:
    """Parse the CLI override. Positivity is checked later, once, with the config value."""
    try:
        return int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid int value: {value!r}") from exc


def main():
    """Main CLI entry point."""
    configure_logging(console)
    print_banner()
    icons = get_icons()

    parser = argparse.ArgumentParser(description="Horizon - AI-Driven Information Aggregation System")
    parser.add_argument("--hours", type=_hours_argument, help="Force fetch from last N hours")
    add_data_dir_arguments(parser)
    add_log_level_argument(parser)
    args = parser.parse_args()

    configure_logging(console, level=args.log_level)

    try:
        # Load environment variables from .env file
        load_dotenv()

        data_dir = Path(args.data_dir)

        # Initialize storage manager
        storage = StorageManager(data_dir=str(data_dir), config_path=args.config)

        # Load configuration
        try:
            config = storage.load_config()
        except FileNotFoundError:
            console.print(
                f"[bold red]{icons['error']} Configuration file not found![/bold red]\n"
            )
            console.print(f"Expected config: [cyan]{storage.config_path}[/cyan]\n")

            example_path = data_dir / "config.example.json"
            if not example_path.exists():
                example_path = Path("data/config.example.json")
            if example_path.exists():
                target_parent = storage.config_path.parent
                if target_parent != Path("."):
                    console.print(
                        f"Create the destination directory:\n"
                        f"  [cyan]mkdir -p {shlex.quote(str(target_parent))}[/cyan]\n"
                    )
                console.print(
                    f"Copy the example config and edit it:\n"
                    f"  [cyan]cp {shlex.quote(str(example_path))} "
                    f"{shlex.quote(str(storage.config_path))}[/cyan]\n"
                )
            if args.config is None and data_dir == Path("data"):
                console.print(
                    "Or run [bold cyan]uv run horizon-wizard[/bold cyan] to launch the interactive setup wizard.\n"
                )
            sys.exit(1)
        except ConfigError as e:
            console.print(
                f"[bold red]{icons['error']} Error loading configuration: {e}[/bold red]"
            )
            sys.exit(1)
        except Exception as e:
            console.print(
                f"[bold red]{icons['error']} Error loading configuration: {e}[/bold red]"
            )
            sys.exit(1)

        icons = get_icons(config.display.icon_style)

        # The mainline matrix is a fact about the previous close, read once per
        # run: the Sunday refresh records it and the digest annotates candidates
        # with it. Losing it costs the annotation, never the run.
        try:
            refresh_mainline(data_dir)
        except Exception as exc:  # noqa: BLE001 - annotation is optional
            console.print(f"[yellow]Mainline snapshot unavailable: {exc}[/yellow]")

        # Sunday publishes no digest: the only job is keeping the theme
        # catalogue level with the listing page, so the next week's picks can
        # reach themes the shipped snapshot does not carry yet.
        if is_refresh_day():
            console.print(
                "[cyan]Sunday run: refreshing the lianban theme index instead of publishing[/cyan]"
            )
            theme_count = asyncio.run(refresh_theme_index(data_dir))
            if theme_count > 0:
                console.print(f"[green]Theme index holds {theme_count} themes[/green]")
            else:
                console.print(
                    "[yellow]Theme index not updated; the warning above says why[/yellow]"
                )
            return

        if config.ai.provider == AIProvider.OPENAI_CHATGPT:
            from .ai.chatgpt_auth import MANAGE_USAGE_URL
            console.print(f"Using ChatGPT plan. Manage usage: {MANAGE_USAGE_URL}")

        # Config value and CLI override meet here. The orchestrator receives the int.
        try:
            window = collection_hours(config.collection.time_window_hours, args.hours)
        except ValueError as exc:
            console.print(f"[bold red]{icons['error']} {exc}[/bold red]")
            sys.exit(2)

        per_source_limit = load_per_source_limit(data_dir / "digest_limits.json")
        orchestrator = _SourceCappedOrchestrator(
            config, storage, console=console, per_source_limit=per_source_limit
        )
        asyncio.run(orchestrator.run(force_hours=window))

    except KeyboardInterrupt:
        console.print(f"\n[yellow]{icons['warning']} Interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]{icons['error']} Fatal error: {e}[/bold red]")
        console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()