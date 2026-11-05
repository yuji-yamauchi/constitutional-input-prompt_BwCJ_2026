# -*- coding: utf-8 -*-
"""tools/unpack_demo.py — demo/docs_png_base64.json を PNG に書き出す（標準ライブラリだけ）。

使い方:  python3 -B -m app_src.tools.unpack_demo [出力フォルダ]
  既定の出力＝app_src/demo/png/（repo の allowlist で画像は止まるので、この場所は git に乗らない）。
  書き出した PNG は、器の「写真を えらぶ・撮る」から取り込む自作のダミー書類。
"""
import base64, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "demo", "docs_png_base64.json")


def main(argv):
    out = argv[1] if len(argv) > 1 else os.path.join(os.path.dirname(HERE), "demo", "png")
    with open(SRC, "r", encoding="utf-8") as f:
        d = json.load(f)
    os.makedirs(out, exist_ok=True)
    n = 0
    for name, b64 in d["files"].items():
        if not name.endswith(".png") or "/" in name or "\\" in name:
            continue
        data = base64.b64decode(b64)
        if data[:8] != b"\x89PNG\r\n\x1a\n":
            print("PNG でない物は書きません:", name)
            continue
        with open(os.path.join(out, name), "wb") as g:
            g.write(data)
        n += 1
    print("書き出し %d 枚 → %s" % (n, out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
