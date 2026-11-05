# -*- coding: utf-8 -*-
"""tests/test_brand.py - ブランド層（字体・形・nav の絵・置き物の絵）の検査。N＝陰性対照（先）／T＝本物。
静的の解析だけ（JS は実行しない）。画面の字・構造・口は変えない、外の読み込み 0、旧ブランド名の字 0（語そのものはこのファイルにも書かない＝実行時に組み立てる）、置き物は 1 か所で全部消せる。
回し方（app_src の親の場所で）: python3 -B -m app_src.tests.run_all
"""
import os
import re
import sys
import unittest

from app_src.common import httpkit, words

STATIC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vault_app", "static")
NAMES = ("てくちゃん", "きろちゃん", "ことちゃん", "まなちゃん")
FILES = ("index.html", "app.js", "app.css", "brand.css")
# 旧ブランド名＝成果物のどこにも静的な字として置かない（陰性対照も含む）。検査のためだけに実行時に組み立てる。
OLD_BRAND = "".join(("t", "e", "c")) * 2
APP_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT_EXTS = (".py", ".js", ".html", ".css", ".txt", ".md", ".json", ".svg", ".yaml", ".yml")
EXTRA_FORBIDDEN = ("診断します", "判定", "スコア", "レベル", "順位", "上達", "成長", "向上",
                   "スキルアップ", "帰属的自己", "続きをどうぞ", "未読")


def _read(name):
    with open(os.path.join(STATIC, name), "rb") as f:
        return f.read().decode("utf-8")


def _hits(text):
    hits = [h[1] for h in words.scan(text)]
    hits += [w for w in EXTRA_FORBIDDEN if w in text]
    return hits


def _external_refs(text):
    """外部の参照＝http(s)://・@import・url( の中身が data: でない物。"""
    bad = re.findall(r"https?://|@import", text)
    for m in re.finditer(r"url\(\s*(['\"]?)([^'\")]*)", text):
        if not m.group(2).startswith("data:"):
            bad.append(m.group(0))
    return bad


class N_Brand(unittest.TestCase):
    def test_a_detectors_react(self):
        # 検出の道具が反応すること（わざと入れた字で）
        self.assertEqual(_external_refs("a{background:url(data:image/png;base64,AAA)}"), [])
        scheme = "http" + "s:" + "//"
        self.assertTrue(_external_refs("a{background:url(" + scheme + "h/a.png)}"))
        self.assertTrue(_external_refs("a{background:url(a.png)}"))
        self.assertTrue(_external_refs("@import 'x.css';"))
        self.assertEqual(len(OLD_BRAND), 6)
        self.assertTrue(re.search(OLD_BRAND, "xx " + OLD_BRAND.title() + OLD_BRAND.upper(), re.I))
        self.assertIsNone(re.search(OLD_BRAND, "xx " + OLD_BRAND[:3] + " " + OLD_BRAND[3:], re.I))
        self.assertEqual(_hits("ここに あなたの 記録が あります。"), [])
        self.assertTrue(_hits("ここに 判定が あります。"))

    def test_b_figures_switch_off_removes_every_name(self):
        js = _read("app.js")
        self.assertRegex(js, r"var BRAND_FIGURES = true;")
        off = js.replace("var BRAND_FIGURES = true;", "var BRAND_FIGURES = false;")
        self.assertIn("var BRAND_FIGURES = false;", off)
        # 名の字は figure() の表にだけ在り、figure() は BRAND_FIGURES が偽なら null を返す
        for n in NAMES:
            self.assertEqual(off.count(n), 1, n)
        m = re.search(r"function figure\(who, sizeCls\) \{\s*if \(!BRAND_FIGURES\) \{ return null; \}", off)
        self.assertIsNotNone(m)
        # 絵の部品 figure のクラスは figure() の中だけで作る
        self.assertEqual(len(re.findall(r"'figure fig-'", off)), 1)
        # 偽のとき body に data-figures="0" を付け、CSS でも隠す
        self.assertRegex(off, r"if \(!BRAND_FIGURES\) \{ document\.body\.setAttribute\('data-figures', '0'\); \}")
        self.assertRegex(_read("app.css"), r'body\[data-figures="0"\] \.figure \{ display: none !important; \}')
        # 絵だけを出す呼び出しは figure() を通る（img 要素を使わない）
        self.assertNotRegex(js, r"createElement\(\s*['\"]img['\"]")

    def test_c_no_product_name_and_no_outside_refs(self):
        for name in FILES:
            text = _read(name)
            self.assertIsNone(re.search(OLD_BRAND, text, re.I), name)
            self.assertEqual(_external_refs(text), [], name)

    def test_c2_no_product_name_anywhere_in_app_src(self):
        # 射程＝app_src 全体（static だけでない）。__pycache__ と _to_delete は除く。
        found = []
        for base, dirs, files in os.walk(APP_SRC):
            dirs[:] = sorted(d for d in dirs if d not in ("__pycache__", "_to_delete"))
            for fn in sorted(files):
                if not fn.endswith(TEXT_EXTS):
                    continue
                with open(os.path.join(base, fn), "rb") as f:
                    text = f.read().decode("utf-8", "replace")
                if re.search(OLD_BRAND, text, re.I):
                    found.append(os.path.relpath(os.path.join(base, fn), APP_SRC))
        self.assertEqual(found, [])

    def test_d_no_forbidden_words_in_text_files(self):
        for name in ("app.js", "index.html", "app.css"):
            self.assertEqual(_hits(_read(name)), [], name)

    def test_e_no_banned_characters(self):
        bad = ["\u202a", "\u202b", "\u202c", "\u202d", "\u202e", "\u2066", "\u2067", "\u2068", "\u2069",
               "\u200b", "\u200c", "\u200d", "\ufeff", "\u2028", "\u2029"]
        emoji = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27bf\ufe0f]")
        for name in ("index.html", "app.js", "app.css"):
            text = _read(name)
            for ch in bad:
                self.assertNotIn(ch, text, name)
            self.assertIsNone(emoji.search(text), name)

    def test_f_base64_only_in_brand_css(self):
        for name in ("index.html", "app.js", "app.css"):
            self.assertNotIn(";base64,", _read(name), name)
            self.assertNotRegex(_read(name), r"\brm\b", name) if name == "app.css" else None

    def test_g_no_figure_next_to_claude_speech(self):
        js = _read("app.js")
        # Claude の札は「Claude（聞き役）」のまま・発言の行に絵や名を付けない
        body = js[js.index("function msgNode"):]
        body = body[:body.index("\n  }\n")]
        self.assertNotIn("figure(", body)
        self.assertNotRegex(body, "|".join(NAMES))


class T_Brand(unittest.TestCase):
    def test_brand_css_loaded_before_app_css(self):
        html = _read("index.html")
        a = html.index('<link rel="stylesheet" href="brand.css">')
        b = html.index('<link rel="stylesheet" href="app.css">')
        self.assertLess(a, b)

    def test_brand_css_contents(self):
        css = _read("brand.css")
        self.assertEqual(len(re.findall(r"@font-face", css)), 2)
        self.assertEqual(len(re.findall(r"--img-[a-z-]+\s*:", css)), 5)

    def test_app_uses_brand_font_and_shapes(self):
        css = _read("app.css")
        self.assertIn("font-family: var(--font-brand);", css)
        self.assertNotIn("Zen Maru Gothic", css)
        for token in ("--radius-card: 16px;", "--radius-btn: 12px;", "--shadow-soft: 0 4px 12px rgba(90, 70, 52, 0.10);"):
            self.assertIn(token, css)
        self.assertRegex(css, r"\.btn-main \{ background: var\(--mint\); color: #3C3024; \}")
        self.assertRegex(css, r"\.btn-main\.btn-send \{ background: var\(--orange\); color: #3C3024; \}")
        for c in ("#90B596", "#9FD6F1", "#F5C9D0"):
            self.assertIn(c, css)

    def test_names_and_nav_icons(self):
        js = _read("app.js")
        for n in NAMES:
            self.assertIn(n, js)
        html = _read("index.html")
        for v in ("home", "renshu", "hikidashi", "kiroku", "seiri", "watasu"):
            self.assertIn('data-view="%s"' % v, html)
            self.assertRegex(js, r"\b%s: '<" % v)
        self.assertEqual(len(re.findall(r'<span class="ico" aria-hidden="true"></span>', html)), 6)

    def test_send_buttons_stay_orange(self):
        js = _read("app.js")
        self.assertEqual(len(re.findall(r"'btn-main btn-send", js)), 4)

    def test_csp_allows_data_fonts(self):
        self.assertIn("font-src 'self' data:", httpkit.SECURITY_HEADERS["Content-Security-Policy"])


if __name__ == "__main__":
    unittest.main()
