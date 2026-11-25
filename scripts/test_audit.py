#!/usr/bin/env python3
"""误用检测的自测：四段里各埋一个错，外加一段正确引用做对照。"""

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

spec = importlib.util.spec_from_file_location("audit", HERE / "audit_llm_usage.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

# 11-25 的真实站点值：冰点期 longest=6、themes_health 含 71.0、
# 全样本 1进2=16.7、冰点期 1进2=18.5、转移矩阵降温格为「·」。
PAGE = """<div class='read'>
<h3>盘面总结</h3><p>今日为深度冰点市，情绪已持续6天，与历史最长持续天数一致。</p>
<h3>重点信号</h3><p>银行板块上涨71.0%，为全场最强。</p>
<h3>盘面变动归因</h3><p>冰点期首板晋级率18.5%高于全样本16.7%，说明更容易晋级。</p>
<h3>趋势展望</h3><p>冰点期次日降温概率0%，不会继续降温；另有53%概率转入修复期。</p>
</div>"""

secs = audit.sections(PAGE)
assert len(secs) == 4, secs

emotion = {
    "relay_promotion": [{"rate": "16.7%"}, {"rate": "33.7%"}],
    "relay_by_phase": [{"phase": "冰点期", "next_1to2": "18.5% (849/4581)"}],
    "phase_duration": [{"phase": "冰点期", "mean": "1.4天", "longest": "6天", "share": "17%"}],
    "phase_transition": {"phase": "冰点期", "next": {"修复": "53%", "降温": "·"}},
}
themes = {"strong": [{"uptrend_share": "71.0%"}], "weak": [{"uptrend_share": "0.0%"}]}

exp = audit.expected_values(emotion, themes)
hits = audit.find_refs(secs, exp)
misuse = audit.find_misuse(secs, emotion, themes, "冰点期")

got = [m["type"] for m in misuse]
want = ["历史分布当本轮天数", "趋势底座当涨跌幅", "两套样本并排比", "无样本读成 0%"]

print("命中误用：", got)
ok = True
for w in want:
    hit = w in got
    ok &= hit
    print(("PASS" if hit else "FAIL"), w)

strong = [h for h in hits if h["strong"]]
print("\n强引用：", [(h["field"], h["values"]) for h in strong])
ok &= any(h["field"] == "phase_transition" and 53.0 in h["values"] for h in strong)
print(("PASS" if any(h["field"] == "phase_transition" for h in strong) else "FAIL"),
      "正确引用被识别（53% 修复）")

# 误用段同时也算引用，这是对的：它确实引用了，只是用错了。
ok &= any(h["field"] == "relay_by_phase" for h in hits)
print(("PASS" if any(h["field"] == "relay_by_phase" for h in hits) else "FAIL"),
      "误用段同时被记为引用")

print("\n总体：", "全绿" if ok else "有失败")
sys.exit(0 if ok else 1)
