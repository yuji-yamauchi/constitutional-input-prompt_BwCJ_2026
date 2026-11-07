# -*- coding: utf-8 -*-
"""器 v0.10（小さな 直し 4 件）の検査。N_＝陰性対照（先）／T_＝本物。標準ライブラリだけ・ネットワークへは出ない。

1. デモの 帯の 字（DEMO-PLACEHOLDER）が 録画用の シナリオ（決まった 入力に 決まった 返事）と 食い違わない
2. 印を 押した ときの 一文（L.markDone）に 書き方の 条件の 字が 出ない
3. README_run.md の「聞き役に 伝える」の 古い 1 行が 無い
4. 朝の あいさつが 出ている ときは、入口の「きょうの 気分を きかせて くれるかな？」（W-268）を 省く
"""
import os
import re
import unittest

from app_src.common import words

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(APP_ROOT, "vault_app", "static")
PUSHY = re.compile(r"ましょう|しよう|ください|[一-龥]{1}\s*[！!]")
EXTRA_FORBIDDEN = ("診断します", "判定", "スコア", "レベル", "順位", "上達", "成長", "向上",
                   "スキルアップ", "帰属的自己", "続きをどうぞ", "未読")   # test_brand と 同じ
BAND = "この入口の応答は 用意した 物です（Claude を 呼んでいません）"
MARK_DONE = "markDone: function (mark) { return mark === 'なし' ? '印を のこしました（印なし）。' : '印を のこしました（' + mark + '）。'; },"
INTRO_LINE = "box.appendChild(msgNode({ who: 'sys', text: (S.morning ? '' : W['W-268'] + '\\n') + W['W-269'] }));"


def _read(rel):
    with open(os.path.join(STATIC, rel), "rb") as f:
        return f.read().decode("utf-8").replace("\r\n", "\n")


def _text(rel):
    with open(os.path.join(APP_ROOT, rel), "rb") as f:
        return f.read().decode("utf-8").replace("\r\n", "\n")


def _w_value(js, code):
    m = re.search(r"'%s': '([^']*)'" % re.escape(code), js)
    return m.group(1) if m else None


def _fn_body(js, head, tail):
    m = re.search(re.escape(head) + r"(.*?)" + tail, js, re.S)
    return m.group(1) if m else None


class N_V010(unittest.TestCase):
    def test_a_checks_notice_the_old_forms(self):
        # 古い 帯の 字・古い markDone・古い README の 行を、わざと 入れた 写しで 落ちる ことを 見る
        js = _read("app.js")
        old_js = js.replace(MARK_DONE, "markDone: function (mark, cond) { return '印を のこしました（' + mark + '・' + cond + '）。'; },")
        self.assertNotEqual(old_js, js)
        self.assertIsNone(re.search(re.escape(MARK_DONE), old_js))
        self.assertIn("' + cond + '", old_js)
        old_intro = js.replace(INTRO_LINE, "box.appendChild(msgNode({ who: 'sys', text: W['W-268'] + '\\n' + W['W-269'] }));")
        self.assertNotEqual(old_intro, js)
        body = _fn_body(old_intro, "function kibunIntro() {", r"\n  \}\n")
        self.assertNotIn("S.morning", body)
        self.assertTrue(words.scan("この 問いで 評価する"))
        self.assertTrue(PUSHY.search("やって みましょう"))


class T_DemoBand(unittest.TestCase):
    def test_placeholder_band_matches_the_scenario_behaviour(self):
        js = _read("app.js")
        v = _w_value(js, "DEMO-PLACEHOLDER")
        self.assertEqual(v, BAND)
        for bad in ("どの入力にも", "同じ字", "仮の物"):
            self.assertNotIn(bad, v)
        self.assertEqual(words.scan(v), [])
        self.assertIsNone(PUSHY.search(v))
        self.assertEqual([w for w in EXTRA_FORBIDDEN if w in v], [])
        # 本物の 記録の ときの 字（DEMO）と、吹き出しの 一文（W-267）は 変えない
        self.assertEqual(_w_value(js, "DEMO"), "この入口の応答は 録画用に記録した物です")
        self.assertIn("あらかじめ 用意した 物です（Claude は 呼んでいません）", _w_value(js, "W-267"))
        self.assertEqual(js.count("W['DEMO-PLACEHOLDER'] : W['DEMO']"), 2)
        # README の 帯の 説明も 同じ 字
        for rel in ("README_run.md", os.path.join("demo", "README.md")):
            t = _text(rel)
            self.assertNotIn("「仮の物です」", t, rel)
            self.assertIn("「用意した 物です」", t, rel)
            self.assertIn("「録画用に記録した物です」", t, rel)


class T_MarkLine(unittest.TestCase):
    def test_mark_line_has_no_condition_text(self):
        js = _read("app.js")
        self.assertIn(MARK_DONE, js)
        body = _fn_body(js, "function marksRow(m) {", r"\n  \}\n")
        self.assertIn("L.markDone(p[0])", body)
        for bad in ("condText", "S.cond", "cond)"):
            self.assertNotIn(bad, body)
        # 条件の 字を 画面に 出す 口は、もう 無い（condText は 送る 時の 写し（sendTier・C-19）にだけ 残る）
        self.assertEqual(len(re.findall(r"\bcondText\(", js)), 2)        # 定義 1 ＋ sendTier の 1
        self.assertEqual(js.count("m.condText"), 0)
        self.assertIn("condText: condText(cond)", js)                     # sendTier は 変えない
        # 裏では 条件の 初期値を 送り続ける
        self.assertIn("var cond = copy(S.cond);", js)
        self.assertIn("var body = { conditions: cond, text: text, direction: S.practice ? S.practice.direction : null };", js)


class T_Readme(unittest.TestCase):
    def test_readme_no_longer_says_daily_is_sent_on_a_toggle(self):
        t = _text("README_run.md")
        self.assertNotIn("を入れた日だけ送られます", t)
        self.assertNotIn("聞き役に 伝える」を入れた日", t)
        self.assertEqual(t.count("聞き役へは送られません"), 2)             # daily と kibun の 2 行
        for bad in ("問いの 向き", "条件の 札", "気分の 面"):
            self.assertNotIn(bad, t)
        self.assertIn("daily/", t)
        self.assertIn("kibun/", t)


class T_Morning(unittest.TestCase):
    def test_greeting_and_mood_question_do_not_double(self):
        js = _read("app.js")
        self.assertIn(INTRO_LINE, js)
        body = _fn_body(js, "function kibunIntro() {", r"\n  \}\n")
        self.assertIn("S.morning ? ''", body)
        self.assertEqual(body.count("W['W-268']"), 1)
        self.assertEqual(body.count("W['W-269']"), 1)
        # 朝の あいさつは paintLog が 今までどおり 出す（v0.4 の 字の まま）
        self.assertIn("morningAsk: 'おはよう。今日の気分はどう？',", js)
        self.assertIn("if (morning) { log.appendChild(msgNode({ who: 'sys', text: L.morningAsk })); }", js)
        # W-268 は 表に 残る（朝で ない ときに 出す）
        self.assertEqual(_w_value(js, "W-268"), "きょうの 気分を きかせて くれるかな？")


if __name__ == "__main__":
    unittest.main()
