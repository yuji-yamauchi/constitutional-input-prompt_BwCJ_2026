# -*- coding: utf-8 -*-
"""器 v0.13（W-40 を 表から 消す・描く所の 無い CSS を 消す・761px 以上の ホームの 下に 飾りの 絵を 置く）の検査。
N_＝陰性対照（先）／T_＝本物。標準ライブラリだけ・ネットワークへは出ない。

1. W-40『きょうの気分』は W の 表に 無い（描く所は v0.12 で 0 に なっていた）
2. app.css から .mood 系・.dir-card／.dir-pic 系の 規則が 消えた（描く所 0 だった 物だけ。mood.css は 触らない）
3. 761px 以上の ホームの 列の 下に、boards.css の 04 の 場面（ベンチの ある 道・人は 描かれて いない）を 飾りとして 置く。
   CSS の ::after だけ（app.js は 触らない・board( は 呼ばない・字は 足さない）。絵なしの 設定（data-figures="0"）と 背景を 白に する（body.bg-white）で 消える。
   スマホ幅（760px 以下）では 無い＝@media (min-width: 761px) の 中にだけ 在る
"""
import os
import re
import unittest

from app_src.tests.test_vault_api import Srv, env_ok

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(APP_ROOT, "vault_app", "static")
HOME_SEL = '.view[data-accent="home"]::after'
HOME_IMG = "var(--img-board-04-seat-empty-scene)"
GONE_CSS = (".mood", ".dir-card", ".dir-cards", ".dir-pic", ".dir-txt", "mood-h", "mood-sec", "mood-row")
NOT_FOR_HOME = ("seat-taken", "02-filled", "03-seat", "img-badge", "img-hero", "img-mood")


def _read(rel):
    with open(os.path.join(STATIC, rel), "rb") as f:
        return f.read().decode("utf-8").replace("\r\n", "\n")


def _strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def _media_blocks(css, head):
    """@media <head> { ... } の 中身を 全部 返す（入れ子は 無い 前提＝app.css の 形）。"""
    out = []
    for m in re.finditer(re.escape(head) + r"\s*\{", css):
        depth = 1
        i = m.end()
        while i < len(css) and depth:
            if css[i] == "{":
                depth += 1
            elif css[i] == "}":
                depth -= 1
            i += 1
        out.append(css[m.end():i - 1])
    return out


def _home_rule(css):
    """min-width: 761px の 中の ホームの ::after の 宣言部。無ければ None。"""
    for blk in _media_blocks(css, "@media (min-width: 761px)"):
        m = re.search(re.escape(HOME_SEL) + r"\s*\{([^}]*)\}", blk)
        if m:
            return m.group(1)
    return None


class N_V013(unittest.TestCase):
    def test_a_checks_notice_the_old_things_coming_back(self):
        js = _read("app.js")
        css = _read("app.css")
        # W-40 を 戻した 写しは 引っかかる
        back = js.replace("    'W-41':", "    'W-40': 'きょうの気分',\n    'W-41':", 1)
        self.assertNotEqual(back, js)
        self.assertEqual(back.count("'W-40'"), 1)
        # 死んだ 規則を 戻した 写しは 引っかかる
        back_css = css + "\n.mood { background: #EAF1E4; }\n.dir-card .ds { font-size: 11px; }\n"
        self.assertTrue(any(g in _strip_comments(back_css) for g in GONE_CSS))
        # 飾りの 規則を 消した 写し・媒体問い合わせの 外に 出した 写し・人の いる 絵に 替えた 写しは 引っかかる
        rule = _home_rule(css)
        self.assertIsNotNone(rule)
        gone = css.replace(HOME_SEL, '.view[data-accent="home"]::before')
        self.assertIsNone(_home_rule(gone))
        outside = css.replace("@media (min-width: 761px)", "@media (min-width: 0px)")
        self.assertIsNone(_home_rule(outside))
        taken = css.replace(HOME_IMG, "var(--img-board-03-seat-taken-scene)")
        self.assertNotIn(HOME_IMG, _home_rule(taken))
        self.assertTrue(any(b in _home_rule(taken) for b in NOT_FOR_HOME))
        # 切り出しの 道具は、媒体問い合わせの 入れ子なしの 形で 本物を 1 つ 見つける
        self.assertEqual(len(_media_blocks(css, "@media (min-width: 761px)")), 1)


class T_W40Gone(unittest.TestCase):
    def test_w40_is_not_in_the_table_and_nowhere_else(self):
        js = _read("app.js")
        self.assertEqual(js.count("'W-40'"), 0)
        self.assertEqual(js.count("W['W-40']"), 0)
        self.assertNotIn("きょうの気分", js)
        for name in ("app.css", "mobile.css", "index.html"):
            self.assertNotIn("W-40", _read(name), name)
        # 隣の 札は 残る（表を 削りすぎて いない）
        self.assertEqual(js.count("'W-41'"), 1)
        self.assertEqual(js.count("'W-42'"), 1)
        self.assertIn("    'UNCONF':", js)


class T_DeadCssGone(unittest.TestCase):
    def test_mood_and_dir_rules_are_gone_from_app_css_and_mobile_css(self):
        for name in ("app.css", "mobile.css"):
            css = _strip_comments(_read(name))
            for g in GONE_CSS:
                self.assertNotIn(g, css, (name, g))
        js = _read("app.js")
        for g in ("'mood", "dir-card", "dir-pic", "mood-row", "mood-sec"):
            self.assertNotIn(g, js, g)
        # 残す 物は 残る（v0.9 の 60 問の 入口・時刻の 欄・置き物）
        css = _read("app.css")
        for keep in (".kibun-intro .daily-fields", ".daily-time {", ".daily-f {", ".fig-hero .fig-img", ".board-scene {", 'body[data-figures="0"] .board { display: none; }'):
            self.assertIn(keep, css, keep)


class T_HomePicture(unittest.TestCase):
    def test_home_after_rule_is_decorative_and_only_above_760(self):
        css = _read("app.css")
        rule = _home_rule(css)
        self.assertIsNotNone(rule)
        self.assertIn('content: ""', rule)            # 字は 足さない（空の content）
        self.assertIn(HOME_IMG, rule)
        self.assertIn("aspect-ratio: 600 / 314", rule)
        self.assertIn("max-width: 600px", rule)
        for b in NOT_FOR_HOME:
            self.assertNotIn(b, rule, b)
        self.assertNotIn("cursor", rule)
        self.assertNotIn("url(", rule)
        # 媒体問い合わせの 外には ホームの ::after は 無い（＝760px 以下では 無い）
        outside = css
        for blk in _media_blocks(css, "@media (min-width: 761px)"):
            outside = outside.replace(blk, "")
        self.assertNotIn(HOME_SEL, outside)
        # 絵なしの 設定と 背景を 白に する で 消える
        blk = _media_blocks(css, "@media (min-width: 761px)")[0]
        self.assertRegex(blk, r'body\[data-figures="0"\] \.view\[data-accent="home"\]::after, body\.bg-white \.view\[data-accent="home"\]::after \{ display: none; \}')
        # app.js・index.html は 絵の ために 触らない（board( の 呼び出し元は 3 関数のまま・ホームに board( は 無い）
        js = _read("app.js")
        m = re.search(r"function renderHome\(host\) \{(.*?)\n  \}\n", js, re.S)
        self.assertNotIn("board(", m.group(1))
        self.assertNotIn("home-pic", js + css + _read("index.html"))

    def test_image_counts_and_places_do_not_change(self):
        self.assertEqual(len(re.findall(r"--img-[a-z-]+\s*:", _read("brand.css"))), 5)
        self.assertEqual(len(re.findall(r"--img-board-[a-z0-9-]+\s*:", _read("boards.css"))), 9)
        css = _read("app.css")
        self.assertEqual(len(re.findall(r"--img-[a-z0-9-]+\s*:", css)), 0)
        self.assertNotIn("base64,", css)
        self.assertNotIn("url(", css)
        self.assertEqual(css.count("var(--img-board-"), 4)          # 3 つの 段の 背景 ＋ ホームの 飾り
        self.assertEqual(css.count(HOME_IMG), 2)                     # mirai の 段の 背景 ＋ ホームの 飾り
        self.assertNotIn("--img-mood", css)

    def test_served_app_css_carries_the_rule(self):
        s = Srv(env_ok())
        try:
            st, _, payload, _ = s.call("GET", "/app.css", cookie=False)
            self.assertEqual(st, 200)
            text = payload.decode("utf-8") if isinstance(payload, bytes) else str(payload)
            self.assertIsNotNone(_home_rule(text))
            st, _, payload, _ = s.call("GET", "/", cookie=False)
            self.assertEqual(st, 200)
            text = payload.decode("utf-8") if isinstance(payload, bytes) else str(payload)
            self.assertNotIn("mood.css", text)
        finally:
            s.close()


if __name__ == "__main__":
    unittest.main()
