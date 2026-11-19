#!/usr/bin/env python3
# 把已发布的盘后洞察晚报页面从蓝绿配色换成暖色。
# 色值与 scripts/post_market_page.py 的 _PAGE_CSS / _THEME_OVERRIDE 完全一致，
# 所以之后重新生成页面时结果相同，不会打架。
import sys

REPL = [
    ('.page-header{color:#fff;text-align:center;background-color:#159957;',
     '.page-header{color:#fdf1e0;text-align:center;background-color:#7a3b1e;'),
    ('background-image:linear-gradient(120deg,#155799,#159957);',
     'background-image:linear-gradient(120deg,#5b2c14,#a85a24);'),
    ('color:rgba(255,255,255,.85);letter-spacing:.3px}',
     'color:rgba(253,241,224,.85);letter-spacing:.3px}'),
    ('main h2{margin:32px 0 12px;font-size:19px;font-weight:600;color:#159957;line-height:1.4}',
     'main h2{margin:32px 0 12px;font-size:19px;font-weight:600;color:#a1521a;line-height:1.4}'),
    ('a{color:#1e6bb8;text-decoration:none}',
     'a{color:#a1521a;text-decoration:none}'),
    ('.read{border-left:3px solid #159957;padding:2px 0 2px 14px}',
     '.read{border-left:3px solid #c97a33;padding:2px 0 2px 14px}'),
    ('.read h3{margin:16px 0 6px;font-size:15px;font-weight:600;color:#159957;letter-spacing:.2px}',
     '.read h3{margin:16px 0 6px;font-size:15px;font-weight:600;color:#a1521a;letter-spacing:.2px}'),
    ('.st-bar i{display:block;height:100%;background:#159957;border-radius:2px}',
     '.st-bar i{display:block;height:100%;background:#c97a33;border-radius:2px}'),
    ('@media (prefers-color-scheme:dark){\n  body{background:#14171c;color:#c3cad6}',
     '@media (prefers-color-scheme:dark){main h2,.read h3{color:#e8a765}.read .verdict{color:#f2e6d8}a{color:#e8a765}\n  body{background:#14171c;color:#c3cad6}'),
    ('<meta name="theme-color" content="#157878">',
     '<meta name="theme-color" content="#7a3b1e">'),
]

COLD = ('#159957', '#155799', '#1e6bb8', '#157878')


def patch(path):
    s = open(path, encoding='utf-8').read()
    if not any(c in s for c in COLD):
        print('already warm:', path)
        return 0
    for a, b in REPL:
        n = s.count(a)
        if n != 1:
            raise SystemExit('pattern hit %d times in %s: %r' % (n, path, a[:60]))
        s = s.replace(a, b)
    open(path, 'w', encoding='utf-8').write(s)
    print('patched:', path, len(s))
    return 1


if __name__ == '__main__':
    for p in sys.argv[1:]:
        patch(p)
