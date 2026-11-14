"""Utilities for normalizing app-generated Markdown."""

import html
import re
from typing import Dict
from urllib.parse import urlsplit


_DETAILS_RE = re.compile(
    r"<details>\s*<summary>(.*?)</summary>\s*(.*?)\s*</details>",
    re.IGNORECASE | re.DOTALL,
)
_ANCHOR_LINK_RE = re.compile(
    r"^\s*<a\s+[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>\s*$",
    re.IGNORECASE | re.DOTALL,
)
_LI_RE = re.compile(r"<li>\s*(.*?)\s*</li>", re.IGNORECASE | re.DOTALL)
_ANCHOR_ID_RE = re.compile(
    r"<a\s+[^>]*id=[\"'][^\"']+[\"'][^>]*>\s*</a>", re.IGNORECASE
)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_MARKDOWN_SPECIAL_RE = re.compile(r"([\\`*_{}\[\]<>()#+!|])")
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
_UNSAFE_MARKDOWN_URL_CHAR_RE = re.compile(r"[\s<>\[\]\\]")
_SOFT_BREAK_RE = re.compile(r"(?<!\n)\n(?!\n)")
_TOC_ENTRY_RE = re.compile(
    r"^(?P<index>\d+)\.\s+\[(?P<title>(?:[^\]\\]|\\.)+)\]\(#[^)]*\)\s*"
    r"\u2b50\ufe0f\s*(?P<score>[\d.]+|\?)/10[ \t]*$",
    re.MULTILINE,
)
_ITEM_HEADING_RE = re.compile(
    r"^###\s+\[(?P<title>(?:[^\]\\]|\\.)+)\]\((?P<url>https?://[^)\s]+)\)",
    re.MULTILINE,
)
_TOC_SECTION_RE = re.compile(r"^\*\*(?P<name>[^*\n]+)\*\*[ \t]*$", re.MULTILINE)
_SOURCE_LINE_RE = re.compile(
    r"(?:\d{1,2}月\d{1,2}日\s*\d{1,2}:\d{2})"
    r"|(?:[A-Z][a-z]{2}\s+\d{1,2},\s+\d{1,2}:\d{2})"
)
_RANK_BADGES = {1: "\U0001F947", 2: "\U0001F948", 3: "\U0001F949"}
_BODY_SKIP_PREFIXES = ("#", ">", "- ", "* ", "|", "<", "---")
_BODY_SKIP_EXACT = ("**参考链接**", "**References**", "**标签**", "**Tags**")
_SAFE_URL_SCHEMES = {"http", "https", "mailto"}


def _strip_html_tags(value: str) -> str:
    """Remove simple HTML tags and decode HTML entities."""
    return html.unescape(_HTML_TAG_RE.sub("", value)).strip()


def _escape_markdown_text(value: str) -> str:
    """Escape user-controlled text before embedding it in generated Markdown."""
    clean_value = re.sub(r"\s+", " ", value).strip()
    return _MARKDOWN_SPECIAL_RE.sub(r"\\\1", clean_value)


def _is_safe_markdown_link_url(value: str) -> bool:
    """Return True when a URL can be emitted as an active Markdown link."""
    if _CONTROL_CHAR_RE.search(value):
        return False
    if _UNSAFE_MARKDOWN_URL_CHAR_RE.search(value):
        return False
    if value.count("(") != value.count(")"):
        return False

    try:
        parsed = urlsplit(value)
    except ValueError:
        return False

    scheme = parsed.scheme.lower()
    if scheme not in _SAFE_URL_SCHEMES:
        return False

    if scheme in {"http", "https"}:
        return bool(parsed.netloc)

    return bool(parsed.path)


def _convert_details_to_markdown(value: str) -> str:
    """Convert HTML details blocks into plain Markdown sections."""

    def _replace(match: re.Match) -> str:
        title = _escape_markdown_text(_strip_html_tags(match.group(1)) or "References")
        body = match.group(2)
        items: list[str] = []

        for item in _LI_RE.findall(body):
            link_match = _ANCHOR_LINK_RE.match(item)
            if link_match:
                href, label = link_match.groups()
                clean_label = _strip_html_tags(label)
                escaped_label = _escape_markdown_text(clean_label)
                clean_href = html.unescape(href).strip()
                if escaped_label and clean_href and _is_safe_markdown_link_url(clean_href):
                    items.append(f"- [{escaped_label}]({clean_href})")
                elif escaped_label:
                    items.append(f"- {escaped_label}")
                continue

            clean_item = _escape_markdown_text(_strip_html_tags(item))
            if clean_item:
                items.append(f"- {clean_item}")

        if not items:
            fallback = _escape_markdown_text(_strip_html_tags(body))
            return f"**{title}**\n\n{fallback}" if fallback else f"**{title}**"

        return f"**{title}**\n\n" + "\n".join(items)

    return _DETAILS_RE.sub(_replace, value)


def _rank_badge(index: int) -> str:
    """Return a rank marker whose rendered width matches the medal emojis.

    Medals and circled digits both occupy one emoji-width cell, so entry text
    starts at the same offset for every rank instead of drifting left after the
    third item.
    """
    badge = _RANK_BADGES.get(index)
    if badge:
        return badge
    if 4 <= index <= 20:
        return chr(0x2460 + index - 1)
    return f"**{index}**"


def _collect_item_urls(value: str) -> Dict[str, str]:
    """Map item titles to their article URLs using the detail headings."""
    return {
        match.group("title"): match.group("url")
        for match in _ITEM_HEADING_RE.finditer(value)
    }


def _render_ranked_entry(match: re.Match, url_by_title: Dict[str, str]) -> str:
    """Render one digest entry as a hot-list line with a rank badge."""
    title = match.group("title")
    url = url_by_title.get(title)
    label = f"[**{title}**]({url})" if url else f"**{title}**"
    return (
        f"{_rank_badge(int(match.group('index')))} {label} "
        f"\u2b50\ufe0f {match.group('score')}/10"
    )


def _promote_toc_sections(value: str) -> str:
    """Turn table-of-contents group labels into headings so they stand out."""
    marker = "\n## "
    start = value.find(marker)
    if start == -1:
        return value

    head, tail = value[:start], value[start:]
    head = _TOC_SECTION_RE.sub(lambda m: f"### {m.group('name')}", head)
    return head + tail


def _promote_body_paragraphs(value: str) -> str:
    """Render digest body paragraphs as blockquotes so they stay legible.

    Chat renderers paint plain paragraphs in a dim grey that is hard to read on
    a dark background, while blockquote text uses the brighter body colour.
    Only the item detail area (everything after the first ``## `` heading) is
    rewritten, so the ranked table of contents keeps its plain layout, and
    source lines, tags and reference lists stay visually secondary.
    """
    marker = "\n## "
    start = value.find(marker)
    if start == -1:
        return value

    head, tail = value[:start], value[start:]
    out: list[str] = []
    for line in tail.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith(_BODY_SKIP_PREFIXES):
            out.append(line)
            continue
        if any(stripped.startswith(prefix) for prefix in _BODY_SKIP_EXACT):
            out.append(line)
            continue
        if " \u00b7 " in stripped and _SOURCE_LINE_RE.search(stripped):
            out.append(line)
            continue
        out.append(f"> {stripped}")

    return head + "\n".join(out)


def clean_app_summary_markdown(value: str) -> str:
    """Flatten app-generated HTML snippets embedded in summary Markdown.

    Unknown raw HTML is intentionally left in place so callers can choose their
    own safety boundary. Email, for example, escapes after this cleanup step.

    Chat and webhook Markdown renderers treat a single newline as a soft break
    and merge adjacent lines into one paragraph, which turns the digest list
    into an unreadable block. Lone newlines are promoted to blank-line breaks so
    every entry renders on its own line, table-of-contents entries are rewritten
    as rank-badged single lines with the article link restored and the title
    bolded, group labels become headings, and body paragraphs become blockquotes
    so they render in the brighter body colour.
    """
    value = _ANCHOR_ID_RE.sub("", value)
    value = _convert_details_to_markdown(value)
    url_by_title = _collect_item_urls(value)
    value = _TOC_ENTRY_RE.sub(
        lambda match: _render_ranked_entry(match, url_by_title), value
    )
    value = _promote_toc_sections(value)
    value = _SOFT_BREAK_RE.sub("\n\n", value)
    return _promote_body_paragraphs(value)
