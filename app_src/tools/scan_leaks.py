# -*- coding: utf-8 -*-
"""tools/scan_leaks.py - 鍵・uuid・URL・メールの形の走査。標準ライブラリだけ。

app_src/**（.py .js .html .css .txt .md .json .svg）に次が 0 であることを示す:
  - sk- で始まる鍵の形  - uuid の形（00000000-0000-4000-8000-… のダミーは例外）
  - 通信先の URL の形（127.0.0.1 と api.anthropic.com は例外。svg の名前空間の識別子も例外 = 通信先ではない）
  - メールの形

  python3 -B -m app_src.tools.scan_leaks              本物の走査だけ
  python3 -B -m app_src.tools.scan_leaks --selftest   陰性対照を先に回してから本物
"""
import os
import re
import sys

APP_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTS = (".py", ".js", ".html", ".css", ".txt", ".md", ".json", ".svg")
SKIP_DIRS = ("__pycache__",)

KEY_RE = re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{8,}")
UUID_RE = re.compile(r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}(?![0-9A-Fa-f])")
URL_RE = re.compile(r"https?://([^\s/\"'<>)\]:]+)")
MAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
DUMMY_UUID_PREFIX = "00000000-0000-4000-8000-"
OK_HOSTS = ("127.0.0.1", "api.anthropic.com", "www.w3.org")      # w3.org は SVG の名前空間の識別子


def scan_text(text):
    """-> [(種類, 一致した字の一部)]"""
    hits = []
    for m in KEY_RE.finditer(text):
        hits.append(("key", m.group(0)[:6] + "..."))
    for m in UUID_RE.finditer(text):
        if not m.group(0).lower().startswith(DUMMY_UUID_PREFIX):
            hits.append(("uuid", m.group(0)[:8] + "..."))
    for m in URL_RE.finditer(text):
        if m.group(1).lower() not in OK_HOSTS:
            hits.append(("url", m.group(1)))
    for m in MAIL_RE.finditer(text):
        hits.append(("mail", m.group(0)[:3] + "..."))
    return hits


def scan_all(root=APP_SRC):
    found, count = [], 0
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for fn in sorted(files):
            if not fn.endswith(EXTS):
                continue
            if "LICENSE" in fn:   # 同梱する字体のライセンス文（原文のまま置く義務がある）＝原文に在る URL は走査の例外
                continue
            p = os.path.join(base, fn)
            count += 1
            with open(p, "rb") as f:
                text = f.read().decode("utf-8", "replace")
            for kind, what in scan_text(text):
                found.append((os.path.relpath(p, root), kind, what))
    return count, found


def selftest():
    # 検査器の字そのものが自分に当たらないよう、組み立てて作る
    samples = {
        "key": "sk" + "-" + "A1b2C3d4E5f6",
        "uuid": "12345678-1234-4234-8234-" + "1234567890ab",
        "url": "ht" + "tps://evil.example/x",
        "mail": "taro" + "@" + "example.org",
    }
    ok = True
    for kind, s in samples.items():
        got = [k for k, _ in scan_text("x " + s + " y")]
        good = kind in got
        ok = ok and good
        print("陰性対照 %-5s -> %s" % (kind, "反応" if good else "反応なし(FAIL)"))
    exempt = "00000000-0000-4000-8000-000000000011 " + "ht" + "tp://127.0.0.1:8765/x " + "ht" + "tps://api.anthropic.com/v1/messages"
    got = scan_text(exempt)
    good = not got
    ok = ok and good
    print("陰性対照 例外（ダミーの id・127.0.0.1・api.anthropic.com） -> %d 件 %s" % (len(got), "合格" if good else "FAIL"))
    return ok


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    ok = True
    if "--selftest" in argv:
        ok = selftest()
    n, found = scan_all()
    for rel, kind, what in found:
        print("HIT  %s  [%s] %s" % (rel, kind, what))
    print("本物     走査 %d ファイル -> %d 件 %s" % (n, len(found), "合格" if not found else "FAIL"))
    return 0 if (ok and not found) else 1


if __name__ == "__main__":
    sys.exit(main())
