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
        return f.read().decode("utf-8").replace("\r\n", "\n")   # Windows の checkout（CRLF）でも同じ比較に


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


BOARD_VARS = ("02-empty-tile", "02-filled-tile", "02-empty-scene", "02-filled-scene",
              "03-seat-empty-tile", "03-seat-taken-tile", "03-seat-empty-scene", "03-seat-taken-scene",
              "04-seat-empty-scene")
# board( を呼んでよい関数（renderHome の本文には置かない。v0.9 で ホームの 気分の 面を なくした ので buildMood は 外した）
BOARD_CALLERS = ("renderHikidashi", "renderSeiri", "loadRecordsInto")
SEAT_TEXT = "いっしょに いる 人が います"


def _board_var_count(css):
    return len(re.findall(r"--img-board-[a-z0-9-]+\s*:", css))


def _board_calls_outside(js, allowed):
    """board( の呼び出しが、許す関数の本文の外に在れば、その位置の関数名を返す。"""
    starts = [(m.start(), m.group(1)) for m in re.finditer(r"\n  (?:async )?function (\w+)\(", js)]
    bad = []
    for m in re.finditer(r"(?<![\w.])board\(", js):
        owner = None
        for pos, name in starts:
            if pos < m.start():
                owner = name
        if owner not in allowed and owner != "board":
            bad.append(owner)
    return bad


BOARD_SHA16 = {
    "02-empty-tile": "02788eb1f115f637", "02-filled-tile": "455de888d2870978",
    "02-empty-scene": "9868a9ef4dc8a68d", "02-filled-scene": "bd3cc30d65871168",
    "03-seat-empty-tile": "b465bed74554e4b2", "03-seat-taken-tile": "0d66e82c7347de11",
    "03-seat-empty-scene": "1500072bb627c1d3", "03-seat-taken-scene": "acd408a196e0510c",
    "04-seat-empty-scene": "ac505f68a2278e31",
}


def _board_payload_sha16(css):
    """変数ごとの base64 を復号して sha256 の先頭 16 桁を返す（絵がそのままかを見る）。"""
    import base64
    import hashlib
    out = {}
    for m in re.finditer(r"--img-board-([a-z0-9-]+):\s*url\(\"data:image/png;base64,([A-Za-z0-9+/=]+)\"\)", css):
        try:
            raw = base64.b64decode(m.group(2), validate=True)
        except Exception:
            raw = b""
        out[m.group(1)] = hashlib.sha256(raw).hexdigest()[:16]
    return out


def _seat_handler(js):
    h = js[js.index("seatBtn.addEventListener('click'"):]
    return h[:h.index("});")]


def _seat_default_off(js):
    return ("sel: 'renshu', seat: false };" in js) and ("ui.seat = j.seat === true;" in js) and ("      seat: false,\n" in js)


def _board_has_text(js):
    m = re.search(r"function board\(kind, state, sizeCls\) \{(.*?)\n  \}\n", js, re.S)
    body = m.group(1) if m else ""
    return bool(re.search(r"title|alt|aria-label|textContent|createTextNode|el\('[a-z]+', '[^']*', ", body))


def _w_seat_ok(js):
    m = re.search(r"'W-172': '([^']*)'", js)
    return bool(m) and m.group(1) == SEAT_TEXT and len(re.findall(r"'W-172':", js)) == 1


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


    def test_h_boards_negative_controls(self):
        css = _read("boards.css")
        js = _read("app.js")
        # 変数が 8 本・10 本の写しでは 9 本の検査が落ちる
        eight = css.replace("--img-board-02-empty-tile:", "--x-02-empty-tile:")
        self.assertEqual(_board_var_count(eight), 8)
        ten = css + "\n:root { --img-board-99-extra: url(\"data:image/png;base64,AA\"); }\n"
        self.assertEqual(_board_var_count(ten), 10)
        self.assertEqual(_board_var_count(css), 9)
        # 9 枚目（04）の絵を 1 字変えた写しは、指紋が変わる
        j = css.index("--img-board-04-seat-empty-scene")
        k = css.index("base64,", j) + 300
        flip4 = css[:k] + ("A" if css[k] != "A" else "B") + css[k + 1:]
        self.assertNotEqual(_board_payload_sha16(flip4)["04-seat-empty-scene"], BOARD_SHA16["04-seat-empty-scene"])
        # img 要素を使った写しは検出される
        bad_js = js.replace("el('span', 'board-img')", "el('img', 'board-img')")
        self.assertNotEqual(bad_js, js)
        self.assertRegex(bad_js, r"el\('img', 'board-img'\)")
        self.assertNotRegex(js, r"el\('img', 'board-img'\)")
        # data-figures の規則を消した写しは検出される
        rule = r'body\[data-figures="0"\] \.board \{ display: none; \}'
        self.assertIsNone(re.search(rule, css.replace('body[data-figures="0"] .board', 'body .board')))
        self.assertTrue(re.search(rule, css))
        # W-172 を促しの字に変えた写しは、字の走査が拾う
        pushy = js.replace(SEAT_TEXT, "人に 話して みましょう")   # 分かち書きの促しの形
        self.assertFalse(_w_seat_ok(pushy))
        self.assertTrue(_hits(pushy))
        self.assertTrue(_hits(js.replace(SEAT_TEXT, "人を よんで みましょう")))
        # 切替の中で fetch を呼ぶ写し・既定を true にした写し・絵に title を付けた写し・base64 を 1 字変えた写しは落ちる
        self.assertNotEqual(_seat_handler(js.replace("saveUi(); paintSeat();", "saveUi(); paintSeat(); fetch('/api/x');")), _seat_handler(js))
        self.assertFalse(_seat_default_off(js.replace("sel: 'renshu', seat: false };", "sel: 'renshu', seat: true };")))
        self.assertFalse(_seat_default_off(js.replace("ui.seat = j.seat === true;", "ui.seat = j.seat !== false;")))
        self.assertTrue(_board_has_text(js.replace("b.appendChild(el('span', 'board-img'));", "b.appendChild(el('span', 'board-img')); b.title = 'x';")))
        css = _read("boards.css")
        i = css.index("base64,") + 200
        flipped = css[:i] + ("A" if css[i] != "A" else "B") + css[i + 1:]
        self.assertNotEqual(_board_payload_sha16(flipped), _board_payload_sha16(css))
        self.assertEqual(_hits(js), [])
        # board( を許さない関数から呼ぶ写しは検出される
        moved = js.replace("function renderHome(", "function renderHome(", 1)
        moved = re.sub(r"(\n  function renderHome\([^\n]*\n)", r"\1    board('02', 'empty', 'board-160');\n", moved, count=1)
        self.assertNotEqual(moved, js)
        self.assertIn("renderHome", _board_calls_outside(moved, BOARD_CALLERS))
        # 許す 3 関数の 外（buildTier・buildMood）からは許さない
        # （v0.12: buildMood は 無くなった ので、board( を 呼ぶ buildMood を 戻した 写しが 検出される ことを 見る）
        self.assertEqual(_board_calls_outside(js, BOARD_CALLERS), [])
        moved3 = js.replace("\n  function openRail(tier) {", "\n  function buildMood() {\n    board('02', 'empty', 'board-160');\n  }\n  function openRail(tier) {", 1)
        self.assertNotEqual(moved3, js)
        self.assertIn("buildMood", _board_calls_outside(moved3, BOARD_CALLERS))
        moved2 = re.sub(r"(\n  function buildTier\([^\n]*\n)", r"\1    board('02', 'empty', 'board-160');\n", js, count=1)
        self.assertNotEqual(moved2, js)
        self.assertIn("buildTier", _board_calls_outside(moved2, BOARD_CALLERS))


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

    def test_boards_css_nine_vars_and_clean(self):
        css = _read("boards.css")
        self.assertEqual(_board_var_count(css), 9)
        self.assertEqual(len(re.findall(r"base64,", css)), 9)
        for v in BOARD_VARS:
            self.assertRegex(css, r"--img-board-%s:" % v)
        self.assertIsNone(re.search(OLD_BRAND, css, re.I))
        self.assertEqual(_external_refs(css), [])
        self.assertEqual(_hits(css), [])
        for ch in ("\u202a", "\u202e", "\u2066", "\u200b", "\ufeff"):
            self.assertNotIn(ch, css)
        self.assertRegex(css, r'body\[data-figures="0"\] \.board \{ display: none; \}')
        self.assertRegex(_read("app.css"), r'body\[data-figures="0"\] \.board \{ display: none; \}')
        self.assertNotIn("base64,", _read("app.css"))

    def test_boards_css_link_order(self):
        html = _read("index.html")
        a = html.index('<link rel="stylesheet" href="brand.css">')
        b = html.index('<link rel="stylesheet" href="boards.css">')
        c = html.index('<link rel="stylesheet" href="app.css">')
        self.assertLess(a, b)
        self.assertLess(b, c)

    def test_board_only_in_hikidashi_and_seiri(self):
        js = _read("app.js")
        self.assertEqual(_board_calls_outside(js, BOARD_CALLERS), [])
        self.assertNotIn("function buildMood(", js)   # v0.9: 絵の 釦だけ → v0.12: 釦ごと 無い（renderHome は 下の 輪で 見る）
        for name in ("renderHome", "renderRenshu", "renderWatasu", "renderKiroku"):
            m = re.search(r"function %s\(" % name, js)
            if not m:
                continue
            end = js.find("\n  }\n", m.start())
            self.assertNotIn("board(", js[m.start():end], name)
        m = re.search(r"function board\(kind, state, sizeCls\) \{(.*?)\n  \}\n", js, re.S)
        self.assertIsNotNone(m)
        body = m.group(1)
        self.assertIn("if (!BRAND_FIGURES) { return null; }", body)
        self.assertIn("setAttribute('aria-hidden', 'true')", body)
        self.assertIn("el('span', 'board-img')", body)
        self.assertNotRegex(body, r"el\('img'")
        self.assertNotRegex(body, r"textContent|createTextNode|el\('[a-z]+', '[^']*', ")

    def test_seat_word_and_toggle(self):
        js = _read("app.js")
        self.assertTrue(_w_seat_ok(js))
        self.assertIn("'W-29': 'v0.3.4 / 2026-11-08'", js)   # v0.15: 画面の版も 聞き役の 指示の文（listener.txt 1 行目）と 同じ 版・日に 揃える
        self.assertEqual(len(re.findall(r"seat-toggle", js)), 1)
        self.assertRegex(js, r"seat-toggle'?, W\['W-172'\]|'linkbtn body-size seat-toggle', W\['W-172'\]")
        self.assertIn("aria-pressed", js)
        self.assertIn("seat-taken", js)
        self.assertIn("seat-empty", js)
        m = re.search(r"function saveUi\(\) \{[^\n]*lsSet\('cip_ui'[^\n]*seat: ui\.seat", js)
        self.assertIsNotNone(m)
        # 切替は端末に覚えるだけ＝押した所で通信しない・既定は「席が空」・絵に字を付けない
        h = _seat_handler(js)
        for bad in ("api(", "fetch(", "XMLHttpRequest", "sendBeacon", "S.chat"):
            self.assertNotIn(bad, h)
        self.assertTrue(_seat_default_off(js))
        self.assertFalse(_board_has_text(js))
        # ログアウトで切替を戻す
        self.assertIn("ui.seat = false; saveUi();", js)

    def test_boards_payload_is_the_delivered_picture(self):
        got = _board_payload_sha16(_read("boards.css"))
        self.assertEqual(got, BOARD_SHA16)

    def test_csp_allows_data_fonts(self):
        self.assertIn("font-src 'self' data:", httpkit.SECURITY_HEADERS["Content-Security-Policy"])


if __name__ == "__main__":
    unittest.main()
