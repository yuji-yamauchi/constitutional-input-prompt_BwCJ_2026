# -*- coding: utf-8 -*-
"""tools/scan_words.py - 禁じる言い方・促しの字・未裁定の語の走査。標準ライブラリだけ。

使い方（app_src の親の場所で）:
  python3 -B -m app_src.tools.scan_words              本物の走査だけ
  python3 -B -m app_src.tools.scan_words --selftest   陰性対照を先に回し（わざと 1 件 入れた字で検出する）、そのあと本物を走査
終了コード 0 = 陰性対照が反応し、本物が 0 件。

対象: vault_app/static と receiver_app/static の *.html *.js ／ vault_app/prompts/*.txt ／
      vault_app/routes_*.py と claude_client.py handoff.py law.py の字列 ／ demo/recorded/*/*.json と demo/docs/*.svg
例外の文書の名（診断書 等）は words.scan が先に外す。語の一覧そのものは common/words.py だけ。
"""
import ast
import glob
import os
import sys

from app_src.common import words

APP_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def scan_py_source(source):
    """Python のソースの字列定数（docstring を除く）を走査 -> [(行, kind, word)]。"""
    tree = ast.parse(source)
    skip = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
                    and isinstance(body[0].value.value, str):
                skip.add(id(body[0].value))
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip:
            for kind, w, _pos in words.scan(node.value):
                hits.append((node.lineno, kind, w))
    return hits


def scan_text(text):
    return [(0, kind, w) for kind, w, _pos in words.scan(text)]


def targets(root=APP_SRC):
    """(path, mode) の並び。mode = 'py' か 'text'。"""
    out = []
    for pat in ("vault_app/static/*.html", "vault_app/static/*.js", "receiver_app/static/*.html", "receiver_app/static/*.js",
                "vault_app/prompts/*.txt", "demo/recorded/*/*.json", "demo/docs/*.svg"):
        for p in sorted(glob.glob(os.path.join(root, pat))):
            out.append((p, "text"))
    py = set(glob.glob(os.path.join(root, "vault_app", "routes_*.py")))
    for n in ("claude_client.py", "handoff.py", "law.py"):
        p = os.path.join(root, "vault_app", n)
        if os.path.isfile(p):
            py.add(p)
    for p in sorted(py):
        out.append((p, "py"))
    return out


def scan_all(root=APP_SRC):
    """-> (走査した数, [(path, 行, kind, word)])"""
    found = []
    files = targets(root)
    for p, mode in files:
        with open(p, "rb") as f:
            src = f.read().decode("utf-8")
        hits = scan_py_source(src) if mode == "py" else scan_text(src)
        for line, kind, w in hits:
            found.append((os.path.relpath(p, root), line, kind, w))
    return len(files), found


def selftest():
    """陰性対照: わざと 1 件 入れた入力で検出し、例外の文書の名だけの入力では検出しない。"""
    bad_py = 'x = "この記録を評価する"\n'
    bad_txt = "続きをどうぞ"
    ok_py = 'x = "診断書を しまう"\n'
    a = scan_py_source(bad_py)
    b = scan_text(bad_txt)
    c = scan_py_source(ok_py)
    print("陰性対照 禁じる語入りの py の字列 -> %d 件 %s" % (len(a), "反応" if a else "反応なし(FAIL)"))
    print("陰性対照 促しの字入りの text      -> %d 件 %s" % (len(b), "反応" if b else "反応なし(FAIL)"))
    print("陰性対照 例外の文書の名だけの字    -> %d 件 %s" % (len(c), "合格" if not c else "FAIL"))
    return bool(a) and bool(b) and not c


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    ok = True
    if "--selftest" in argv:
        ok = selftest()
    n, found = scan_all()
    for rel, line, kind, w in found:
        print("HIT  %s:%d  [%s] %s" % (rel, line, kind, w))
    print("本物     走査 %d ファイル -> %d 件 %s" % (n, len(found), "合格" if not found else "FAIL"))
    return 0 if (ok and not found) else 1


if __name__ == "__main__":
    sys.exit(main())
