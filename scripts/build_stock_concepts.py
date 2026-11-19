"""Grow the stock -> concept index from Tonghuashun F10 pages.

The index is a cache, not a prerequisite: the evening brief fetches any ticker
the index does not carry, so a cold start still produces a complete page. This
script is for warming that cache deliberately — after a payload dump, or for a
list of names known in advance — so tomorrow's run starts from disk.

Every page is cached on disk as it arrives, so an interrupted build resumes where
it stopped instead of re-spending the rate-limit budget.

    python scripts/build_stock_concepts.py --codes 600619,002242
    python scripts/build_stock_concepts.py --payload payload.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stock_concepts as sc  # noqa: E402

CACHE = Path(".cache/stock_concepts_raw.json")


def _load_cache() -> Dict[str, Any]:
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text(encoding="utf-8"))
        except ValueError:
            return {}
    return {}


def _save_cache(cache: Dict[str, Any]) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


def codes_from_payload(path: Path) -> List[str]:
    """Every ticker the evening brief can name, deduplicated.

    Dragon-tiger rows, the three screening panels and the theme watch pool are
    the places a name arrives from; a name that appears in any of them is a name
    worth having on disk before the run that needs it.
    """
    doc = json.loads(path.read_text(encoding="utf-8"))
    codes: List[str] = []

    def add(code: Any) -> None:
        text = str(code or "").strip()
        if len(text) == 6 and text.isdigit() and text not in codes:
            codes.append(text)

    for item in (doc.get("lhb") or {}).get("items") or []:
        add(item.get("code"))
    for block in (doc.get("filter") or {}).values():
        for row in block.get("rows") or []:
            add(row.get("code"))
    for card in (doc.get("extra") or {}).get("theme_members") or []:
        for member in card.get("members") or []:
            add(member.get("code"))
    for bucket in (doc.get("candidates") or {}).values():
        if isinstance(bucket, dict):
            for row in bucket.get("rows") or []:
                add(row.get("code"))
    return codes


def build(codes: List[str]) -> Dict[str, Any]:
    index = sc.load_index()
    stocks: Dict[str, Any] = index.get("stocks") or {}
    cache = _load_cache()
    added = skipped = failed = 0
    t0 = time.time()
    for i, code in enumerate(codes, 1):
        if code in stocks and stocks[code][1]:
            skipped += 1
            continue
        cached = cache.get(code)
        if cached:
            name, concepts = cached[0], cached[1]
        else:
            name, concepts = sc.fetch_stock(code)
            if not concepts:
                failed += 1
                continue
            cache[code] = [name, concepts]
            _save_cache(cache)
        stocks[code] = [name, concepts]
        added += 1
        if i % 10 == 0:
            logging.warning("progress %d/%d, added=%d", i, len(codes), added)
    doc = {
        "meta": {
            "built": time.strftime("%Y-%m-%d"),
            "stocks": len(stocks),
            "source": (
                "同花顺 F10 概念页（basic.10jqka.com.cn）：概念名称、龙头股、"
                "概念解析原文；仅用于个股题材归属倒查"
            ),
            "align": "概念名与 lianban 题材名做归一化精确匹配，不做子串匹配",
        },
        "stocks": stocks,
    }
    elapsed = time.time() - t0
    print(
        f"codes={len(codes)} added={added} skipped={skipped} failed={failed} "
        f"total={len(stocks)} elapsed={elapsed:.0f}s"
    )
    return doc


def main(argv: List[str] | None = None) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--codes", default="", help="comma-separated tickers")
    parser.add_argument("--payload", default="", help="payload JSON to harvest tickers from")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    codes: List[str] = [c.strip() for c in args.codes.split(",") if c.strip()]
    if args.payload:
        for code in codes_from_payload(Path(args.payload)):
            if code not in codes:
                codes.append(code)
    if not codes:
        parser.error("nothing to do: pass --codes and/or --payload")

    doc = build(codes)
    if args.dry_run:
        print("dry run: index not written")
        return 0
    for path, size in sc.write_index(doc):
        print(f"{path} {size} B")
    return 0


if __name__ == "__main__":
    sys.exit(main())
