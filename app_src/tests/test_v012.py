# -*- coding: utf-8 -*-
"""器 v0.12（ホームの「きょうの気分」の 絵の 釦を 釦ごと なくす）の検査。N_＝陰性対照（先）／T_＝本物。標準ライブラリだけ・ネットワークへは出ない。

1. ホームは あいさつ（W-60・W-61）と とどいた返事（W-62）だけ。絵の 釦（.scene-btn）と それを 作る buildMood は 無い
2. 釦の 絵（mood.css）は index.html から 読み込まない（ファイルは 残す。消すかは 別の 決め）
3. チャットは 今までどおり 左の 帯の 釦（#btn-chatback）と openRail('renshu') で 開く
"""
import os
import re
import unittest

from app_src.tests.test_vault_api import Srv, env_ok

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(APP_ROOT, "vault_app", "static")
LINKS = ["brand.css", "boards.css", "app.css", "mobile.css"]      # index.html が 読む CSS の 並び（mood.css は 無い）
GONE = ("buildMood", "scene-btn", "scene-pic", "scene-lbl", "img-mood", "mood.css")


def _read(rel):
    with open(os.path.join(STATIC, rel), "rb") as f:
        return f.read().decode("utf-8").replace("\r\n", "\n")


def _fn_body(js, head, tail):
    m = re.search(re.escape(head) + r"(.*?)" + tail, js, re.S)
    return m.group(1) if m else None


def _home(js):
    return _fn_body(js, "function renderHome(host) {", r"\n  \}\n")


def _links(html):
    return re.findall(r'<link rel="stylesheet" href="([^"]+)">', html)


class N_V012(unittest.TestCase):
    def test_a_checks_notice_the_button_coming_back(self):
        js = _read("app.js")
        html = _read("index.html")
        # 釦を 戻した 写し（renderHome から buildMood を 呼ぶ）は 下の 検査に 引っかかる
        back = js.replace("    // とどいた返事\n", "    sec.appendChild(buildMood());\n    // とどいた返事\n", 1)
        self.assertTrue(back != js)
        self.assertIn("buildMood", _home(back))
        # 釦の 絵の 読み込みを 戻した 写しも 引っかかる
        back_html = html.replace('<link rel="stylesheet" href="app.css">\n', '<link rel="stylesheet" href="app.css">\n<link rel="stylesheet" href="mood.css">\n', 1)
        self.assertTrue(back_html != html)
        self.assertNotEqual(_links(back_html), LINKS)
        self.assertIn("mood.css", back_html)
        # 切り出しの 道具は 本物の 関数を 見つける
        self.assertIsNotNone(_home(js))
        self.assertIsNone(_fn_body(js, "function buildMood() {", r"\n  \}\n"))


class T_HomeHasNoButton(unittest.TestCase):
    def test_home_is_greeting_and_replies_only(self):
        js = _read("app.js")
        body = _home(js)
        for need in ("W['W-60']", "W['W-61a']", "W['W-61b']", "W['W-62']", "figure('teku', 'fig-hero')", "loadRepliesInto(body)"):
            self.assertIn(need, body)
        for bad in GONE + ("openRail(", "board(", "W['W-40']"):
            self.assertNotIn(bad, body)
        # ホームが 足す 札は 2 つ（あいさつ・とどいた返事）＋鍵が 無い ときの 注だけ
        self.assertEqual(body.count("sec.appendChild("), 3)
        self.assertEqual(body.count("card("), 2)
        self.assertIn("if (S.status && S.status.claude === 'no_key') {", body)

    def test_the_button_and_its_maker_are_gone_from_every_static_file(self):
        for name in ("app.js", "app.css", "mobile.css", "index.html"):
            text = _read(name)
            for bad in GONE:
                self.assertNotIn(bad, text, (name, bad))
        js = _read("app.js")
        self.assertNotIn("function buildMood(", js)
        self.assertEqual(js.count("openRail('renshu')"), 1)      # startRun の 中だけ（再開の 釦）
        self.assertIn("$('btn-chatback').addEventListener('click', function () { ui.leftMin = true; ui.railMin = false; saveUi(); applyLayout(); scrollLogBottom(); });", js)
        self.assertEqual(_read("index.html").count('id="btn-chatback"'), 1)


class T_MoodCssNotLoaded(unittest.TestCase):
    def test_index_links_four_css_in_order_and_not_mood_css(self):
        html = _read("index.html")
        self.assertEqual(_links(html), LINKS)
        self.assertNotIn("mood.css", html)
        # 絵の 変数（--img-mood-scene）を 使う 所は 読み込む CSS の どこにも 無い
        for name in ("app.css", "mobile.css", "brand.css", "boards.css"):
            self.assertNotIn("--img-mood", _read(name), name)
        # 絵の 本数は 変わらない（brand 5・boards 9・app.css は 定義 0）
        self.assertEqual(len(re.findall(r"--img-[a-z-]+\s*:", _read("brand.css"))), 5)
        self.assertEqual(len(re.findall(r"--img-board-[a-z0-9-]+\s*:", _read("boards.css"))), 9)
        self.assertEqual(len(re.findall(r"--img-[a-z0-9-]+\s*:", _read("app.css"))), 0)
        self.assertNotIn("base64,", _read("app.css"))

    def test_served_page_does_not_name_mood_css(self):
        s = Srv(env_ok())
        try:
            st, _, payload, _ = s.call("GET", "/", cookie=False)
            self.assertEqual(st, 200)
            text = payload.decode("utf-8") if isinstance(payload, bytes) else str(payload)
            self.assertNotIn("mood.css", text)
            self.assertIn('href="app.css"', text)
        finally:
            s.close()


if __name__ == "__main__":
    unittest.main()
