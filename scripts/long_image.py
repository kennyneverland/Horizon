#!/usr/bin/env python3
"""把一期页面拍成一张长图，传到 OSS，再单独推一条只含这张图的 Server酱 消息。

为什么单独成脚本：长图必须拍已经部署上线的那一版，而推送发生在 commit 之前。
所以这一步挂在 workflow 的 commit 之后，轮询页面 200 再拍，不会拍到上一期。

收件人来自 HORIZON_WEBHOOK_URL，和文字版是同一份名单、同一个顺序：第 1 条是
收件人自己，第 2 条是朋友；问候语按位置从 data/webhook_banners.json 取，所以
朋友收到的长图上也带着「噜妹天天发财」那一行，两版观感一致。

依赖只有标准库 + playwright：OSS 走 V1 签名自己拼，不引 oss2，省掉动 uv.lock。

用法：
    python scripts/long_image.py --url https://.../post-market/2026-11-20.html \\
        --title "11月20日 盘后洞察晚报"        # 读 HORIZON_WEBHOOK_URL，按人分别推

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
import re
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
        f"{k.lower()}:{headers[k]}\\n" for k in sorted(headers) if k.lower().startswith("x-oss-")
    )
    resource = f"/{bucket}/{key}"
    to_sign = f"{verb}\\n\\n{headers.get('Content-Type', '')}\\n{headers.get('Date', '')}\\n{canon_headers}{resource}"
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

    # 必须用三级域名（虚拟主机）寻址：path-style 的 oss-cn-beijing.aliyuncs.com/桶/key
    # 会被 OSS 拒成 SecondLevelDomainForbidden（403），早报第一次跑就会挂在这里。
    url = f"https://{bucket}.{host}/{urllib.parse.quote(key)}"
    # GitHub 托管 runner 到华北2 的跨境带宽很低：1.5 MB 的图 60s 写不完就报
    # "The write operation timed out"，所以超时放宽到 OSS_TIMEOUT（默认 240s）并重试三次。
    timeout = int(os.environ.get("OSS_TIMEOUT", "240"))
    for attempt in range(1, 4):
        started = time.time()
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method="PUT")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status not in (200, 201):
                    raise RuntimeError(f"OSS 返回 {resp.status}")
            print(
                f"upload: {key} {len(body) / 1024:.0f} KB in "
                f"{time.time() - started:.1f}s (attempt {attempt})"
            )
            break
        except Exception as exc:  # noqa: BLE001 - 慢链路要重试
            print(
                f"upload retry {attempt}/3: {key} {len(body) / 1024:.0f} KB failed after "
                f"{time.time() - started:.1f}s: {type(exc).__name__}: {exc}"
            )
            if attempt == 3:
                raise
            time.sleep(5 * attempt)
    if public_base:
        return public_base.rstrip("/") + "/" + urllib.parse.quote(key)
    return f"https://{bucket}.{host}/{urllib.parse.quote(key)}"


# ---------------------------------------------------------------- 截图
def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _local_mirror(url: str) -> Optional[Path]:
    """把线上地址映射回 runner 里的构建产物，用来判断远端是不是已经是新版本。

    Pages 部署有 CDN 缓存：commit 完立刻请求，拿到的常常还是上一版 HTML。而
    --marker 只认「2026-11-20」这种日期字样，旧页面同样含这串，于是会立刻放行，
    拍出来的就是一张旧图（2026-11-22 晚报就栽在这里：部署 09:33:11 推完，长图
    09:33:12 开等，13 秒就"成功"了）。所以再加一道闸：远端 HTML 必须和本地刚
    构建的 docs/ 那份逐字节一致，才算真的上线。
    """
    path = urllib.parse.urlsplit(url).path
    parts = [seg for seg in path.split("/") if seg]
    if parts and parts[0] == "Horizon":
        parts = parts[1:]
    if not parts:
        return None
    candidate = Path("docs").joinpath(*parts)
    return candidate if candidate.is_file() else None


def wait_ready(url: str, timeout: int = 300, marker: str = "") -> str:
    """等页面真的上线，返回拿去截图的地址（带 cache-buster）。

    Pages 部署有延迟，commit 完立刻拍会拍到 404 或上一期。两道闸：marker 必须在
    页面里，且远端 HTML 必须和本地刚构建的那份逐字节一致。请求带 cb= 时间戳，
    绕开 CDN 缓存，否则缓存没过期前会一直读到旧版、白等到超时。
    """
    mirror = _local_mirror(url)
    want = _sha256(mirror.read_bytes()) if mirror else ""
    if mirror:
        print(f"ready-check: 比对本地 {mirror}（{mirror.stat().st_size} B，sha={want[:12]}）")
    else:
        print("ready-check: 没找到本地构建产物，只校验 marker（可能拍到旧版）")
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        probe = f"{url}{'&' if '?' in url else '?'}cb={int(time.time())}"
        try:
            with urllib.request.urlopen(probe, timeout=20) as resp:
                raw = resp.read()
            body = raw.decode("utf-8", "replace")
            hit = not marker or marker in body
            fresh = not want or _sha256(raw) == want
            if resp.status == 200 and hit and fresh:
                print(f"ready: {url}（marker={'hit' if marker else 'n/a'}，远端已是新版本）")
                return probe
            last = (
                f"status={resp.status} "
                f"marker={'hit' if marker and marker in body else 'miss'} "
                f"版本={'新' if fresh else '旧'}"
            )
        except Exception as exc:  # noqa: BLE001 - 没上线就继续等
            last = f"{type(exc).__name__}: {exc}"
        time.sleep(10)
    raise RuntimeError(f"页面 {timeout}s 内没就绪（{last}）")


MAX_PIXEL_HEIGHT = 20000


def _plan_slices(marks: list, total: int, max_h: int) -> list:
    """按标题位置把整页切成若干段，每段不超过 max_h，切点落在标题上。

    早报 3.9 万 CSS px，一张图是 7.8 万像素高、十几兆，微信里打不开；切成几段
    仍是一条消息里的几张图，读者往下划就是连续的，断点也不会切在句子中间。

    默认「能塞就塞满」的贪心切法，断点尽量落在标题上。只有一种情况例外：末段
    短得像个空尾巴（晚报 1.07 万 px 会被切成 10000 + 751），这时按段数均分重排，
    让几段长度接近；重排时仍优先吸附到标题，并且每段都不得超过 max_h。
    """
    if total <= max_h:
        return [(0, total)]

    greedy, start = [], 0
    while total - start > max_h:
        limit = start + max_h
        cands = [m for m in marks if start + max_h * 0.35 < m <= limit]
        cut = max(cands) if cands else limit
        greedy.append((start, cut - start))
        start = cut
    greedy.append((start, total - start))

    n = len(greedy)
    if greedy[-1][1] >= (total / n) * 0.5:
        return greedy

    # 末段过短：按 n 段均分，切点优先吸附标题，否则退回均分位置。
    target = total / n
    balanced, start = [], 0
    for k in range(1, n):
        want = k * target
        lo = max(start + 1, total - max_h * (n - k))
        hi = min(start + max_h, total - 1)
        if lo > hi:
            cut = int(hi)
        else:
            window = max(target * 0.18, 300)
            cands = [m for m in marks if lo <= m <= hi and abs(m - want) <= window]
            if cands:
                cut = int(min(cands, key=lambda m: abs(m - want)))
            else:
                cut = int(round(min(max(want, lo), hi)))
        balanced.append((start, cut - start))
        start = cut
    balanced.append((start, total - start))
    return balanced


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
def _load_banners(path) -> list:
    """问候语按位置对应推送地址，和文字版共用同一份 data/webhook_banners.json。

    第 1 条是收件人自己、不配问候语；第 2 条是朋友、配「噜妹天天发财」那行。
    文件缺失时返回空表，长图照推，只是不带问候语。
    """
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rows = doc.get("banners") if isinstance(doc, dict) else None
    if not isinstance(rows, list):
        return []
    return [str(row or "").strip() for row in rows]


def _split_targets(targets: str) -> list:
    """HORIZON_WEBHOOK_URL 是逗号或换行分隔的多条完整地址，一条一个收件人。"""
    return [t.strip() for t in re.split(r"[,\\n]+", targets or "") if t.strip()]


def push_image(targets: str, title: str, image_urls, link: str = "", banners_path=None) -> bool:
    """Server酱 只认 Markdown：正文一行一张图，微信里点开就是长图。

    收件人来自 HORIZON_WEBHOOK_URL，和文字版是同一份名单、同一个顺序；问候语
    按位置从 webhook_banners.json 取，所以朋友收到的长图上也带着「噜妹天天发财」。
    直接 POST 整条地址，不自己拼域名——Server酱³ 的地址是 push.ft07.com，
    旧版是 sctapi.ftqq.com，拼错了只会拿到 404。
    """
    ends = _split_targets(targets)
    if not ends:
        print("push failed: 没有推送地址", file=sys.stderr)
        return False
    urls = [image_urls] if isinstance(image_urls, str) else list(image_urls)
    desc = "\\n\\n".join(f"![长图]({u})" for u in urls)
    if link:
        desc += f"\\n\\n[网页版]({link})"
    banners = _load_banners(banners_path) if banners_path else []
    print(f"push: {len(ends)} endpoints, {len(banners)} banners")
    delivered = 0
    for index, endpoint in enumerate(ends):
        banner = banners[index] if index < len(banners) else ""
        if banner and "*" not in banner:
            banner = f"**{banner}**"
        body = f"{banner}\\n\\n{desc}" if banner else desc
        data = urllib.parse.urlencode(
            {"title": title[:32], "desp": body, "short": title[:48]}
        ).encode()
        req = urllib.request.Request(endpoint, data=data, method="POST")
        print(f"push[{index + 1}/{len(ends)}]: banner={'yes' if banner else 'no'}")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                doc = json.loads(resp.read().decode("utf-8", "replace") or "{}")
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", "replace")[:200]
            except Exception:  # noqa: BLE001
                pass
            print(f"push[{index + 1}/{len(ends)}]: failed HTTP {exc.code} {detail}", file=sys.stderr)
            continue
        ok = doc.get("code") == 0
        print(f"push[{index + 1}/{len(ends)}]: {'ok' if ok else 'failed'} {doc.get('message', '')}")
        if ok:
            delivered += 1
    return delivered == len(ends)


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
    ap.add_argument("--webhook", default=os.environ.get("HORIZON_WEBHOOK_URL", ""),
                    help="逗号或换行分隔的完整推送地址，与文字版共用 HORIZON_WEBHOOK_URL")
    ap.add_argument("--banners", default="data/webhook_banners.json",
                    help="问候语文件，按位置对应推送地址")
    ap.add_argument("--sendkey", default=os.environ.get("SENDKEY", ""),
                    help="兼容旧用法：单个 SendKey，会自动拼 sctapi 地址")
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--key-prefix", default="horizon/")
    ap.add_argument("--max-height", type=int, default=MAX_PIXEL_HEIGHT,
                    help="单张图最大 CSS 高度，超过就按标题切段")
    args = ap.parse_args(argv)

    if not args.url and not args.html:
        ap.error("--url 或 --html 至少给一个")

    if args.url:
        target = wait_ready(args.url, timeout=args.wait, marker=args.marker)
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
    targets = (args.webhook or "").strip()
    if not targets and args.sendkey:
        targets = f"https://sctapi.ftqq.com/{args.sendkey}.send"
    if not targets:
        print("没有推送地址（HORIZON_WEBHOOK_URL / --sendkey 都为空），只落图不推送", file=sys.stderr)
        return 1
    urls = [upload_oss(path, key_prefix=args.key_prefix) for path in paths]
    for u in urls:
        print(f"upload: {u}")
    return 0 if push_image(targets, args.title, urls, args.url or "", args.banners) else 1


if __name__ == "__main__":
    sys.exit(main())
