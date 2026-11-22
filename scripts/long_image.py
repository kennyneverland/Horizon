#!/usr/bin/env python3
"""把一期页面拍成一张长图，传到 OSS，再单独推一条只含这张图的 Server酱 消息。

为什么单独成脚本：长图必须拍已经部署上线的那一版，而推送发生在 commit 之前。
所以这一步挂在 workflow 的 commit 之后，轮询页面 200 再拍，不会拍到上一期。

依赖只有标准库 + playwright：OSS 走 V1 签名自己拼，不引 oss2，省掉动 uv.lock。

用法：
    python scripts/long_image.py --url https://.../post-market/2026-11-20.html \
        --title "11月20日 盘后洞察晚报" --sendkey "$SENDKEY"

    # 本地调样式：直接拍文件，不推
    python scripts/long_image.py --html docs/post-market/2026-11-20.html --out /tmp/a.png --no-push
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.utils import formatdate
from pathlib import Path
from typing import Optional

# 爱马仕橙。整张图用橙底 + 米白卡片，深棕字，和站内的浅色页是两套皮，互不影响。
HERMES_ORANGE = "#f37021"
HERMES_INK = "#3a1c0c"
HERMES_CREAM = "#fffaf3"

THEME_CSS = f"""
/* 长图专用：橙色画布 + 米白内容卡，站点本身不受影响 */
html, body {{
  background: {HERMES_ORANGE} !important;
  background-image: none !important;
}}
body {{
  padding: 18px 14px 26px !important;
  margin: 0 !important;
  max-width: none !important;
  font-size: 16px !important;
  color: {HERMES_INK} !important;
  -webkit-font-smoothing: antialiased;
}}
/* 顶部标题带：橙底白字，不另起色块 */
.page-header, header.page-header {{
  background: transparent !important;
  background-image: none !important;
  border: 0 !important;
  padding: 6px 4px 14px !important;
  margin: 0 !important;
  text-align: center !important;
}}
.page-header .project-name,
.page-header h1 {{
  color: #fff !important;
  font-size: 21px !important;
  line-height: 1.45 !important;
  font-weight: 700 !important;
  letter-spacing: .5px;
  margin: 0 !important;
  text-shadow: 0 1px 0 rgba(0,0,0,.08);
}}
.page-header .project-tagline, .page-header h2 {{ color: rgba(255,255,255,.92) !important; }}
/* 正文卡：所有内容装进一张米白卡，边缘留橙，长图才有版式感 */
main, main.main-content, .main-content {{
  background: {HERMES_CREAM} !important;
  border-radius: 18px !important;
  box-shadow: 0 8px 26px rgba(94, 36, 4, .18) !important;
  padding: 20px 18px 26px !important;
  margin: 0 auto !important;
  max-width: 680px !important;
  width: auto !important;
  float: none !important;
}}
main h2 {{
  color: #b4470f !important;
  border-bottom: 0 !important;
  padding-bottom: 0 !important;
}}
.read {{ border-left-color: {HERMES_ORANGE} !important; }}
.stat, .st, .ovr, .zc, .wl {{
  background: #fff !important;
  border-color: #f2e2d2 !important;
}}
footer, .site-footer {{ border-top-color: #f0dcc8 !important; color: #9a7a63 !important; }}
.site-footer a {{ color: #b4470f !important; }}
/* 早报的代码块是深灰底，在米白卡上会跳出来，压成浅底深字 */
pre, code, .highlight pre {{
  background: #f6ece2 !important;
  color: #3a1c0c !important;
  border: 0 !important;
}}
pre {{ border-radius: 10px !important; }}
/* 长图不需要交互态，去掉悬停阴影和滚动条 */
* {{ scrollbar-width: none; }}
::-webkit-scrollbar {{ display: none; }}
"""


# ---------------------------------------------------------------- OSS 上传
def _oss_headers(key: str, body: bytes, bucket: str, content_type: str) -> dict:
    return {
        "Content-Type": content_type,
        "Content-Length": str(len(body)) if body else "0",
        "Date": formatdate(usegmt=True),
    }


def _oss_signature(secret: str, verb: str, bucket: str, key: str, headers: dict) -> str:
    """OSS V1 签名：VERB\\nContent-MD5\\nContent-Type\\nDate\\nCanonicalizedOSSHeaders\\nCanonicalizedResource"""
    canon_headers = "".join(
        f"{k.lower()}:{headers[k]}\n" for k in sorted(headers) if k.lower().startswith("x-oss-")
    )
    resource = f"/{bucket}/{key}"
    to_sign = f"{verb}\n\n{headers.get('Content-Type', '')}\n{headers.get('Date', '')}\n{canon_headers}{resource}"
    digest = hmac.new(secret.encode(), to_sign.encode(), hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


def upload_oss(path: Path, key_prefix: str = "horizon/") -> str:
    """把图传到 OSS，返回公网 URL。凭据全走环境变量，配置里不落密钥。"""
    endpoint = os.environ.get("OSS_ENDPOINT", "").strip()
    bucket = os.environ.get("OSS_BUCKET", "").strip()
    ak_id = os.environ.get("OSS_AK_ID", "").strip()
    ak_secret = os.environ.get("OSS_AK_SECRET", "").strip()
    public_base = os.environ.get("OSS_PUBLIC_BASE", "").strip()
    missing = [
        name
        for name, value in (
            ("OSS_ENDPOINT", endpoint),
            ("OSS_BUCKET", bucket),
            ("OSS_AK_ID", ak_id),
            ("OSS_AK_SECRET", ak_secret),
        )
        if not value
    ]
    if missing:
        raise RuntimeError("OSS 未配置，缺少 " + "、".join(missing))

    body = path.read_bytes()
    ctype = mimetypes.guess_type(path.name)[0] or "image/png"
    key = f"{key_prefix}{path.name}"
    host = endpoint.replace("https://", "").replace("http://", "").strip("/")
    headers = _oss_headers(key, body, bucket, ctype)
    headers["Authorization"] = f"OSS {ak_id}:{_oss_signature(ak_secret, 'PUT', bucket, key, headers)}"

    req = urllib.request.Request(
        f"https://{host}/{urllib.parse.quote(key)}", data=body, headers=headers, method="PUT"
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        if resp.status not in (200, 201):
            raise RuntimeError(f"OSS 返回 {resp.status}")
    if public_base:
        return public_base.rstrip("/") + "/" + urllib.parse.quote(key)
    return f"https://{bucket}.{host}/{urllib.parse.quote(key)}"


# ---------------------------------------------------------------- 截图
def wait_ready(url: str, timeout: int = 300, marker: str = "") -> None:
    """等页面真的上线：Pages 部署有延迟，commit 完立刻拍会拍到 404 或上一期。"""
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=20) as resp:
                body = resp.read().decode("utf-8", "replace")
            if resp.status == 200 and (not marker or marker in body):
                print(f"ready: {url}")
                return
            last = f"status={resp.status} marker={'hit' if marker and marker in body else 'miss'}"
        except Exception as exc:  # noqa: BLE001 - 没上线就继续等
            last = f"{type(exc).__name__}: {exc}"
        time.sleep(10)
    raise RuntimeError(f"页面 {timeout}s 内没就绪（{last}）")


MAX_PIXEL_HEIGHT = 20000


def _plan_slices(marks: list, total: int, max_h: int) -> list:
    """按标题位置把整页切成若干段，每段不超过 max_h，切点落在标题上。

    早报 3.9 万 CSS px，一张图是 7.8 万像素高、十几兆，微信里打不开；切成几段
    仍是一条消息里的几张图，读者往下划就是连续的，断点也不会切在句子中间。
    """
    if total <= max_h:
        return [(0, total)]
    cuts, start = [], 0
    while total - start > max_h:
        limit = start + max_h
        cands = [m for m in marks if start + max_h * 0.35 < m <= limit]
        cut = max(cands) if cands else limit
        cuts.append((start, cut - start))
        start = cut
    cuts.append((start, total - start))
    return cuts


def shoot(
    target: str,
    out: Path,
    width: int = 430,
    dpr: float = 3,
    theme: str = "hermes",
    max_px: int = MAX_PIXEL_HEIGHT,
) -> list:
    """整页截图：量高度 → 按标题切段 → 逐段拍。返回落盘的 PNG 列表。

    像素密度按每段的高度反推，总高压在 max_h 以内再定 DPR，下限 2 倍——手机上
    看仍是一倍屏的两倍清晰度；超长页不会被相册或微信二次压缩。
    """
    from playwright.sync_api import sync_playwright

    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": 900})
        page.goto(target, wait_until="networkidle", timeout=60000)
        if theme == "hermes":
            page.add_style_tag(content=THEME_CSS)
        page.evaluate("() => document.fonts && document.fonts.ready")
        # 滚一遍：懒加载图片、IntersectionObserver 的块要进过视口才会出现
        page.evaluate(
            """async () => {
                const step = window.innerHeight * 0.8;
                for (let y = 0; y < document.body.scrollHeight; y += step) {
                    window.scrollTo(0, y);
                    await new Promise(r => setTimeout(r, 50));
                }
                window.scrollTo(0, 0);
                await new Promise(r => setTimeout(r, 400));
            }"""
        )
        page.wait_for_timeout(500)
        info = page.evaluate(
            """() => ({
                total: document.documentElement.scrollHeight,
                marks: [...document.querySelectorAll('h2, h3')]
                    .map(e => Math.round(e.getBoundingClientRect().top + window.scrollY))
            })"""
        )
        # 像素密度先定：整页能塞进一张图就用请求的倍数，塞不进退到 2 倍，
        # 再用「像素上限 ÷ 倍数」算出每段允许多高，按标题切。
        eff = round(max(2.0, min(dpr, max_px / max(info["total"], 1))), 2)
        slices = _plan_slices(info["marks"], info["total"], int(max_px / eff))
        print(
            f"page: {info['total']} css px → {len(slices)} 段，dpr {eff}，"
            f"每段 ≤ {int(max_px / eff)} css px / {max_px} 像素高"
        )

        page.close()
        page = browser.new_page(
            viewport={"width": width, "height": 900},
            device_scale_factor=eff,
            is_mobile=True,
            has_touch=True,
        )
        page.goto(target, wait_until="networkidle", timeout=60000)
        if theme == "hermes":
            page.add_style_tag(content=THEME_CSS)
        page.wait_for_timeout(800)

        paths = []
        for index, (y, height) in enumerate(slices, start=1):
            path = out if len(slices) == 1 else out.with_name(f"{out.stem}-{index}{out.suffix}")
            page.screenshot(
                path=str(path),
                clip={"x": 0, "y": y, "width": width, "height": height},
                full_page=True,
            )
            paths.append(path)
            print(f"shot {index}/{len(slices)}: {path.name} {path.stat().st_size / 1024:.0f} KB")
        browser.close()
    return paths


# ---------------------------------------------------------------- 推送
def push_image(sendkey: str, title: str, image_urls, link: str = "") -> bool:
    """Server酱 只认 Markdown：正文一行一张图，微信里点开就是长图。"""
    urls = [image_urls] if isinstance(image_urls, str) else list(image_urls)
    desc = "\n\n".join(f"![长图]({u})" for u in urls)
    if link:
        desc += f"\n\n[网页版]({link})"
    data = urllib.parse.urlencode(
        {"title": title[:32], "desp": desc, "short": title[:48]}
    ).encode()
    req = urllib.request.Request(
        f"https://sctapi.ftqq.com/{sendkey}.send", data=data, method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        doc = json.loads(resp.read().decode("utf-8", "replace") or "{}")
    ok = doc.get("code") == 0
    print(f"push: {'ok' if ok else 'failed'} {doc.get('message', '')}")
    return ok


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description="页面 → 长图 → OSS → 单独一条 Server酱 推送")
    ap.add_argument("--url", help="线上页面地址（会轮询等它上线）")
    ap.add_argument("--html", help="本地 HTML 路径（调样式用，不轮询）")
    ap.add_argument("--title", default="Horizon 长图")
    ap.add_argument("--out", default="", help="本地 PNG 落盘路径")
    ap.add_argument("--width", type=int, default=430, help="CSS 像素宽，iPhone 逻辑宽")
    ap.add_argument("--dpr", type=float, default=3.0, help="像素密度，3=三倍图")
    ap.add_argument("--theme", default="hermes", choices=["hermes", "none"])
    ap.add_argument("--wait", type=int, default=300, help="等页面就绪的秒数")
    ap.add_argument("--marker", default="", help="页面里必须出现的字样，防拍到上一期")
    ap.add_argument("--sendkey", default=os.environ.get("SENDKEY", ""))
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--key-prefix", default="horizon/")
    ap.add_argument("--max-height", type=int, default=MAX_PIXEL_HEIGHT,
                    help="单张图最大 CSS 高度，超过就按标题切段")
    args = ap.parse_args(argv)

    if not args.url and not args.html:
        ap.error("--url 或 --html 至少给一个")

    if args.url:
        wait_ready(args.url, timeout=args.wait, marker=args.marker)
        target = args.url
    else:
        target = Path(args.html).resolve().as_uri()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out = Path(args.out) if args.out else Path(f"/tmp/horizon-long-{stamp}.png")
    paths = shoot(
        target, out, width=args.width, dpr=args.dpr, theme=args.theme, max_px=args.max_height
    )
    print(f"shot: {len(paths)} 张，合计 {sum(p.stat().st_size for p in paths) / 1024:.0f} KB")

    if args.no_push:
        return 0
    if not args.sendkey:
        print("没有 sendkey，只落图不推送", file=sys.stderr)
        return 1
    urls = [upload_oss(path, key_prefix=args.key_prefix) for path in paths]
    for u in urls:
        print(f"upload: {u}")
    return 0 if push_image(args.sendkey, args.title, urls, args.url or "") else 1


if __name__ == "__main__":
    sys.exit(main())
