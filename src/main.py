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
from .processing.lianban_calendar import fetch_events, to_queries
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

    def apply_balanced_digest(self, items, *, log: bool = True):
        return apply_balanced_digest_with_cap(
            self,
            items,
            super().apply_balanced_digest,
            limit=self.per_source_limit,
            log=log,
        )

    async def fetch_all_sources(self, since):
        """抓取前先补日历事件 query，抓完再给事件条目打标。

        连板网日历里的三星事件本身不进正文——读者要的是数据落地后市场怎么读，
        检索回来的报道才进财经要闻。取不到就跳过，抓取照常进行。
        """
        if not self._calendar_injected:
            self._calendar_injected = True
            await self._inject_calendar_queries()
        items = await super().fetch_all_sources(since)
        for item in items:
            query = (item.metadata or {}).get("gn_query")
            if query and query in self._event_queries:
                item.metadata["event_driven"] = True
        return items

    async def _inject_calendar_queries(self) -> None:
        """把前一日 09:00 之后的三星事件变成 Google News 检索 query。

        09:00 之前的事件，前一日早报已经覆盖过，再搜一次是重复；名称残缺的
        条目检索不出东西，由 lianban_calendar 一并跳过。
        """
        sources = self.config.sources.google_news
        if not sources or not sources.enabled:
            return
        # 用北京时间的「昨天」：早报 09:02 起跑，要的是前一日盘后到今早落地的事件。
        yesterday = (
            datetime.now(timezone(timedelta(hours=8))) - timedelta(days=1)
        ).strftime("%Y-%m-%d")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                events = await fetch_events(client, yesterday)
        except Exception as exc:  # noqa: BLE001 - 少一份日历，不能拖垮抓取
            self.console.print(f"[yellow]日历事件注入失败：{exc}[/yellow]")
            return
        existing = {query.query for query in sources.queries}
        for query in to_queries(events):
            if query.query in existing:
                continue
            sources.queries.append(query)
            self._event_queries.add(query.query)
            self.console.print(f"[dim]日历事件进检索：{yesterday} {query.query}[/dim]")

    def _apply_balanced_digest_base(self, items, *, log: bool = True):
        """配额分配后再做一次稳定重排：日历事件检索回来的条目提到同组最前。

        分数不动，页面上不会出现虚高的星级；``sorted`` 是稳定的，其余条目
        保持原来的评分顺序。
        """
        result = super()._apply_balanced_digest_base(items, log=log)
        picked = sorted(
            result.items,
            key=lambda item: not bool((item.metadata or {}).get("event_driven")),
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
