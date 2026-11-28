"""A1 守卫测试：删掉 scripts/src 旧副本，并锁住 import 的解析前提。

复核实测（2026-11-28，9a1e104b）：`scripts/src/` 下没有任何 __init__.py，
只是 namespace 包的一段；仓库根 `src/` 是常规包。Python 的规则是常规包优先于
namespace 片段、与 sys.path 顺序无关，所以 **两行 insert 写反也不会命中旧副本**。
原稿把这层说成"顺序一改就静默"，是把风险讲大了。

真正的风险只有一个：一旦有人给 `scripts/src/` 补上 __init__.py（包化、模板生成、
IDE 自动补都会），它立刻变常规包，顺序重新生效。所以根治手段是删掉它，而不是
调换 sys.path —— 本测试由此只剩两条主线：旧副本必须不存在；仓库根必须仍在
sys.path[0]。scripts/ 位置只作记录，不作硬约束。
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
POST_MARKET = REPO_ROOT / "scripts" / "post_market.py"
ORCHESTRATOR = REPO_ROOT / "src" / "orchestrator.py"


def test_scripts_src_legacy_copy_removed():
    """根治项：目录在，风险就在；目录不在，namespace 通道与包通道同时关闭。"""
    assert not (REPO_ROOT / "scripts" / "src").exists(), (
        "scripts/src 是 11 月的旧副本；删掉它才是根治，补 __init__.py 或调 sys.path 都只是掩盖"
    )


def test_repo_root_stays_first_on_sys_path():
    """仓库根必须留在 sys.path[0]；这条是真正挡住旧副本的那一行。"""
    text = POST_MARKET.read_text(encoding="utf-8")
    assert "sys.path.insert(0, str(Path(__file__).resolve().parent.parent))" in text


def test_scripts_dir_not_inserted_first():
    """选型记录：scripts/ 我们放末尾。写反并不致命，但没必要把两行调成一对暗号。"""
    text = POST_MARKET.read_text(encoding="utf-8")
    assert "sys.path.insert(0, str(Path(__file__).resolve().parent))" not in text
    assert "sys.path.append(str(Path(__file__).resolve().parent))" in text


def test_posts_dir_anchored_to_repo_root():
    text = ORCHESTRATOR.read_text(encoding="utf-8")
    assert "_REPO_ROOT = Path(__file__).resolve().parents[1]" in text
    assert 'posts_dir = _REPO_ROOT / "docs" / "_posts"' in text
    assert 'posts_dir = Path("docs/_posts")' not in text, "不得再押当前工作目录"


def test_src_modules_resolve_under_repo_src():
    import src.processing.next_day as next_day

    assert Path(next_day.__file__).resolve().is_relative_to(REPO_ROOT / "src")
