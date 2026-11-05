# -*- coding: utf-8 -*-
"""tools/scan_network.py - ネットワークへ出る import の走査。標準ライブラリだけ。

app_src/**/*.py（tests/ と tools/ を除く）を ast で読み、次を示す:
  - urllib.request / urllib.error / http.client / socket / requests / httpx / aiohttp / urllib3 の import は
    vault_app/claude_client.py と vault_app/handoff.py の 2 本以外に 0
  - receiver_app/ には、それらに加えて vault_app と claude_client の import も 0
  （urllib.parse と http.server は待ち受け・字の処理だけなので数えない）

  python3 -B -m app_src.tools.scan_network              本物の走査だけ
  python3 -B -m app_src.tools.scan_network --selftest   陰性対照を先に回してから本物
"""
import ast
import os
import sys

APP_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOWED = ("vault_app/claude_client.py", "vault_app/handoff.py")
SKIP_DIRS = ("tests", "__pycache__")   # tools も走査する（記録の道具が通信の部品を触っていないことを示す）
ROOTS = ("socket", "requests", "httpx", "aiohttp", "urllib3")
NET_MODULES = ("urllib.request", "urllib.error", "http.client")


def _net(module):
    if not module:
        return False
    if module.split(".")[0] in ROOTS:
        return True
    return module == "urllib" or any(module == m or module.startswith(m + ".") for m in NET_MODULES)


def _net_from(module, names):
    if module == "urllib":
        return any(n in ("request", "error") for n in names)
    if module == "http":
        return "client" in names
    return _net(module)


def banned_imports(source, receiver=False):
    """ソースの中の対象の import を [(行, 名)] で返す。"""
    tree = ast.parse(source)
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if _net(a.name) or (receiver and (a.name.startswith("app_src.vault_app") or a.name.endswith("claude_client"))):
                    hits.append((node.lineno, a.name))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            names = [a.name for a in node.names]
            if _net_from(mod, names) or (receiver and (mod.startswith("app_src.vault_app") or mod.endswith("claude_client")
                                                       or (mod == "app_src" and "vault_app" in names)
                                                       or "claude_client" in names)):
                hits.append((node.lineno, mod + " import " + ",".join(names)))
        elif isinstance(node, ast.Call):
            f = node.func
            fname = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else "")
            if fname in ("__import__", "import_module") and node.args and isinstance(node.args[0], ast.Constant) \
                    and isinstance(node.args[0].value, str) and _net(node.args[0].value):
                hits.append((node.lineno, node.args[0].value))
    return hits


def scan_all(root=APP_SRC):
    """-> (走査した数, [(相対パス, 行, 名)])"""
    found, count = [], 0
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for fn in sorted(files):
            if not fn.endswith(".py"):
                continue
            p = os.path.join(base, fn)
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            count += 1
            with open(p, "rb") as f:
                src = f.read().decode("utf-8")
            hits = banned_imports(src, receiver=rel.startswith("receiver_app/"))
            if rel in ALLOWED and not rel.startswith("receiver_app/"):
                continue
            for line, name in hits:
                found.append((rel, line, name))
    return count, found


def selftest():
    cases = [
        ("import urllib.request\n", False, True),
        ("from urllib import request\n", False, True),
        ("import socket\n", False, True),
        ("from http.client import HTTPConnection\n", False, True),
        ("m = __import__('requests')\n", False, True),
        ("import urllib.parse\nfrom http.server import HTTPServer\n", False, False),
        ("from app_src.vault_app import claude_client\n", True, True),
    ]
    ok = True
    for src, recv, want in cases:
        got = bool(banned_imports(src, receiver=recv))
        good = got == want
        ok = ok and good
        print("陰性対照 %-52s -> %s" % (src.strip().splitlines()[0][:52], ("反応" if got else "反応なし") + ("" if good else "(FAIL)")))
    return ok


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    ok = True
    if "--selftest" in argv:
        ok = selftest()
    n, found = scan_all()
    for rel, line, name in found:
        print("HIT  %s:%d  %s" % (rel, line, name))
    print("本物     走査 %d ファイル -> %d 件 %s" % (n, len(found), "合格" if not found else "FAIL"))
    return 0 if (ok and not found) else 1


if __name__ == "__main__":
    sys.exit(main())
