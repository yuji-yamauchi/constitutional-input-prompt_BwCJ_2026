# -*- coding: utf-8 -*-
"""器 v0.11（W の 表の 古い 2 文）の検査。N_＝陰性対照（先）／T_＝本物。標準ライブラリだけ・ネットワークへは出ない。

1. W-263（器の約束の 窓・見える人の 窓）と W-251 が、v0.9 で 無くなった「聞き役に 伝える」の 切替を 前提に して いない
2. 画面は きょうの ことを 聞き役に 送らない（shareDate を 入れる 所が 無い＝shareActive は 常に false）
3. サーバーは、画面が 送る 形の 本文（share_daily 無し）では、きょうの ことも 60 問の こたえも Claude に 渡さない
"""
import os
import re
import unittest

from app_src.common import words
from app_src.common import ids
from app_src.tests.test_v033 import Capture, COND, BED, WAKE
from app_src.tests.test_vault_api import Srv, env_ok

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(APP_ROOT, "vault_app", "static")
PUSHY = re.compile(r"ましょう|しよう|ください|[一-龥]{1}\s*[！!]")
EXTRA_FORBIDDEN = ("診断します", "判定", "スコア", "レベル", "順位", "上達", "成長", "向上",
                   "スキルアップ", "帰属的自己", "続きをどうぞ", "未読")   # test_brand と 同じ
W263 = "きょうの こと（ねた・おきた 時刻・あさごはん）と 60 問の こたえは、あなたの 器に のこります。聞き役の Claude には 送られません。"
W251 = "きょうの ことは、あなたの 器に のこります。聞き役の Claude には 送られません。"
OLD_W263 = "きょうの ことは、「聞き役に 伝える」を 入れた 日だけ、書いた字と いっしょに 聞き役の Claude に 送られます。"
OLD_PHRASE = "「聞き役に 伝える」を 入れた"     # 切替を 前提に した 言い方（W-251・W-263 の 旧文に 共通）
DEFAULT_COND = {"amount": "ふつう", "split": "区切らない", "ease": "ふつう", "length": "みじかく", "input": "文字"}
DAY = ids.now_jst()[:10]


def _read(rel):
    with open(os.path.join(STATIC, rel), "rb") as f:
        return f.read().decode("utf-8").replace("\r\n", "\n")


def _w_value(js, code):
    m = re.search(r"'%s': '([^']*)'" % re.escape(code), js)
    return m.group(1) if m else None


def _fn_body(js, head, tail):
    m = re.search(re.escape(head) + r"(.*?)" + tail, js, re.S)
    return m.group(1) if m else None


class N_V011(unittest.TestCase):
    def test_a_checks_notice_the_old_sentence(self):
        # 旧文（切替を 前提に した 一文）を わざと 戻した 写しで、下の 検査が 落ちる ことを 見る
        js = _read("app.js")
        old = js.replace("'W-263': '%s'" % W263, "'W-263': '%s'" % OLD_W263)
        self.assertTrue(old != js)                      # （長い 字を 落とさない ため assertNotEqual は 使わない）
        self.assertIn(OLD_PHRASE, old)
        self.assertNotEqual(_w_value(old, "W-263"), W263)
        # shareDate に 値を 入れる 行を 足した 写しなら、送る 道が 開く ことに 気づく
        opened = js.replace("    return !!(S && S.daily && S.daily.shareDate && S.daily.shareDate === todayJst());",
                            "    S.daily.shareDate = todayJst();\n    return !!(S && S.daily && S.daily.shareDate && S.daily.shareDate === todayJst());")
        self.assertTrue(opened != js)
        self.assertEqual(len(re.findall(r"\.shareDate\s*=[^=]", opened)), 1)
        self.assertTrue(words.scan("この 問いで 評価する"))
        self.assertTrue(PUSHY.search("やって みましょう"))


class T_Sentences(unittest.TestCase):
    def test_w263_and_w251_match_what_the_screen_does(self):
        js = _read("app.js")
        self.assertEqual(_w_value(js, "W-263"), W263)
        self.assertEqual(_w_value(js, "W-251"), W251)
        for v in (W263, W251):
            self.assertEqual(words.scan(v), [])
            self.assertIsNone(PUSHY.search(v))
            self.assertEqual([w for w in EXTRA_FORBIDDEN if w in v], [])
            self.assertNotIn("送られます", v)
            self.assertNotIn("伝える", v)
        # 切替を 前提に した 言い方は、表の どこにも 無い
        self.assertNotIn(OLD_PHRASE, js)
        self.assertNotIn("入れた 日だけ", js)
        # W-263 を 描く 口は 2 つ の まま（器の約束の 窓・見える人の 窓の renshu の 枝）
        self.assertEqual(js.count("W['W-263']"), 2)
        self.assertIn("wrap.appendChild(el('p', null, W['W-263']));", _fn_body(js, "async function openPromise() {", r"\n  \}\n"))
        self.assertIn("if (S.rail === 'renshu') { wrap.appendChild(el('p', null, W['W-263'])); }", _fn_body(js, "function openVisible() {", r"\n  \}\n"))
        # となりの 字と 矛盾しない（60 問の こたえ＝W-282『だれにも 送りません』）
        self.assertIn("だれにも 送りません", _w_value(js, "W-282"))


class T_ScreenNeverShares(unittest.TestCase):
    def test_share_date_is_never_set(self):
        js = _read("app.js")
        # shareDate は 初期値（null）だけ。値を 入れる 行が 無い ので shareActive() は 常に false
        self.assertEqual(len(re.findall(r"\.shareDate\s*=[^=]", js)), 0)
        self.assertEqual(len(re.findall(r"shareDate:\s*null", js)), 1)
        self.assertEqual(js.count("W['W-257']"), 0)      # 「聞き役に 伝える」の 釦を 描く 所は 無い
        body = _fn_body(js, "async function sendTier(name) {", r"\n  /\* =====")
        self.assertIn("if (shareActive()) { body.share_daily = true;", body)   # C-19: sendTier は 触らない
        self.assertIn("var body = { conditions: cond, text: text, direction: S.practice ? S.practice.direction : null };", body)


class T_ServerNeverShares(unittest.TestCase):
    def test_screen_shaped_body_carries_no_daily_and_no_kibun(self):
        # 画面が 送る 形（share_daily 無し・direction null）では、器に きょうの ことと 60 問の こたえが 在っても Claude には 渡らない
        s = Srv(env_ok())
        self.addCleanup(s.close)
        s.login()
        c = Capture(s.app.vault, s.app.clock)
        s.app.claude = c
        st, _, _, _ = s.call("PUT", "/api/daily/" + DAY, {"bed_time": BED, "wake_time": WAKE, "breakfast": "yes"})
        self.assertEqual(st, 200)
        st, _, _, _ = s.call("POST", "/api/kibun/runs", {"date": DAY, "run_id": None, "count": 10, "start_id": 1, "version": "c",
                                                         "answers": [{"id": 1, "choice": "few"}], "finished": False})
        self.assertEqual(st, 200)
        st, j, _, _ = s.call("POST", "/api/practice/turns", {"conditions": DEFAULT_COND, "text": "きょうは朝早く目がさめた。", "direction": None})
        self.assertEqual(st, 200)
        self.assertEqual(len(c.seen), 1)
        user = c.seen[0]
        for bad in ("きょうの こと", BED, WAKE, "あさごはん", "ねた 時刻", "few", '"choice"', "問いの 向き"):
            self.assertNotIn(bad, user)
        self.assertIn("きょうは朝早く目がさめた。", user)
        self.assertEqual(s.app.vault.get_turn(j["turn_id"])["shared_daily"], False)


if __name__ == "__main__":
    unittest.main()
