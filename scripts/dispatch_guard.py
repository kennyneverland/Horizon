#!/usr/bin/env python3
"""兜底 cron 的去重闸。

外部定时器（Cloudflare Worker）到点调 workflow_dispatch，是准点的主路径；
workflow 里保留的那条 cron 只是它挂掉时的替补，触发时刻故意排在主路径之后
一小时以上。本脚本回答一个问题：这条替补该不该真的跑。

判定只在 schedule 事件下生效 —— 手动 dispatch 一律放行，否则回补和重跑
都会被自己挡住。

  schedule 事件：
    当日产物已在线        -> 跳过（主路径已经出过了）
    当日产物是 artifact   -> artifact 已存在则跳过
    今日已有 run 在排队/进行中 -> 跳过（主路径还在跑，别插队）
    其余                  -> 放行

任何一项探测失败都按"放行"处理：宁可多跑一次，也不能该出报的日子不出。
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, time, timedelta, timezone

SH = timezone(timedelta(hours=8))
API = "https://api.github.com"


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "horizon-dispatch-guard",
    }


def _get(url: str, token: str) -> dict:
    req = urllib.request.Request(url, headers=_headers(token))
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def _probe(url: str, timeout: int = 20) -> int | str:
    """HEAD 一次，返回状态码；网络错误返回 'err:...'。"""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "horizon-dispatch-guard"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:  # noqa: BLE001 - 探测失败按放行处理
        return f"err:{type(e).__name__}"


def _sh_date(iso: str) -> date:
    return (
        datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ")
        .replace(tzinfo=timezone.utc)
        .astimezone(SH)
        .date()
    )


def main() -> int:
    event = os.environ.get("GITHUB_EVENT_NAME", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
    self_id = os.environ.get("GITHUB_RUN_ID", "")
    workflow_file = os.environ.get("GUARD_WORKFLOW_FILE", "").strip()
    product_tpl = os.environ.get("GUARD_PRODUCT_URL", "").strip()
    artifact = os.environ.get("GUARD_ARTIFACT", "").strip()

    today = datetime.now(SH).date()
    today_s = today.isoformat()

    # 只有替补 cron 才需要这道闸
    if event != "schedule":
        print(f"event={event or '?'} -> guard bypassed (只有 schedule 需要去重)")
        return emit(False)

    if not token or not repo:
        print("GH_TOKEN / GITHUB_REPOSITORY 缺失 -> 放行")
        return emit(False)

    reasons: list[str] = []

    # 1) 当日页面已经在线
    if product_tpl:
        url = (
            product_tpl.replace("{date}", today_s)
            .replace("{ymd}", today.strftime("%Y/%m/%d"))
            .replace("{yyyy}", today.strftime("%Y"))
            .replace("{mm}", today.strftime("%m"))
            .replace("{dd}", today.strftime("%d"))
        )
        code = _probe(url)
        print(f"probe {url} -> {code}")
        if code == 200:
            reasons.append(f"今日页面已在线：{url}")
        elif code == 404:
            print("  页面尚未出现，继续看运行记录")
        else:
            print(f"  探测结果 {code} 无法判定，按放行处理")

    # 2) 今日 artifact 已上传（矩阵没有页面产物，只有 artifact）
    if artifact:
        try:
            data = _get(
                f"{API}/repos/{repo}/actions/artifacts?name={artifact}&per_page=50",
                token,
            )
            for a in data.get("artifacts", []):
                if _sh_date(a["created_at"]) == today:
                    reasons.append(
                        f"今日 artifact {artifact} 已上传 "
                        f"({_sh_date(a['created_at']).isoformat()} "
                        f"{datetime.strptime(a['created_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).astimezone(SH).strftime('%H:%M')})"
                    )
                    break
            else:
                print(f"  今日尚无 artifact {artifact}")
        except Exception as e:  # noqa: BLE001
            print(f"  artifact 查询失败（{type(e).__name__}: {e}），按放行处理")

    # 3) 今日已有 run 在排队或进行中（主路径还在跑，替补别插队）
    if workflow_file:
        try:
            since = (
                datetime.combine(today, time(0, 0), tzinfo=SH)
                .astimezone(timezone.utc)
                .strftime("%Y-%m-%dT%H:%M:%SZ")
            )
            data = _get(
                f"{API}/repos/{repo}/actions/workflows/{workflow_file}/runs"
                f"?per_page=100&created=%3E%3D{since}",
                token,
            )
            for r in data.get("workflow_runs", []):
                if str(r["id"]) == self_id:
                    continue
                if _sh_date(r["created_at"]) != today:
                    continue
                if r.get("status") in ("queued", "in_progress", "waiting", "pending"):
                    reasons.append(f"今日 run {r['id']} 仍在 {r['status']}")
                    break
            else:
                print("  今日没有仍在跑的 run")
        except Exception as e:  # noqa: BLE001
            print(f"  run 列表查询失败（{type(e).__name__}: {e}），按放行处理")

    if reasons:
        print("guard: SKIP")
        for r in reasons:
            print(f"  - {r}")
        return emit(True)

    print("guard: RUN（今日尚无产物，也没有在跑的 run）")
    return emit(False)


def emit(skip: bool) -> int:
    line = f"skip={'true' if skip else 'false'}\n"
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(line)
    else:
        sys.stdout.write(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
