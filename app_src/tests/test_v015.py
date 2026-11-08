# -*- coding: utf-8 -*-
"""器 v0.15（画面の版を v0.3.4 に揃える・聞き役への direction／share_daily の口を閉じる）の検査。
N_＝陰性対照（先）／T_＝本物。標準ライブラリだけ・ネットワークへは出ない。
"""
import json
import os
import re
import unittest

from app_src.common import ids, words
from app_src.tests.test_vault_api import Srv, env_ok
from app_src.vault_app import claude_client, routes_practice

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPTS = os.path.join(APP_ROOT, "vault_app", "prompts")
STATIC = os.path.join(APP_ROOT, "vault_app", "static")
VAULT_APP = os.path.join(APP_ROOT, "vault_app")
COND = {"amount": "ふつう", "split": "文ごと", "ease": "やさしい", "length": "みじかく", "input": "文字"}
BED, WAKE = "23:47", "06:13"
OLD_VERSION = "v0.3.3 / 2026-11-06"


def _text(path):
    with open(path, "rb") as f:
        return f.read().decode("utf-8").replace("\r\n", "\n")


def _prompt_version(kind):
    first = _text(os.path.join(PROMPTS, kind + ".txt")).split("\n", 1)[0]
    m = re.match(r"^# 版: (v[0-9.]+) / 決めた日: ([0-9]{4}-[0-9]{2}-[0-9]{2})$", first)
    assert m, first
    return "%s / %s" % (m.group(1), m.group(2))


def _w29(js):
    m = re.search(r"'W-29': '([^']*)'", js)
    return m.group(1) if m else None


class Capture(claude_client.ClaudeClient):
    """Claude に渡る user の字を覚えておく（通信しない）。"""
    def __init__(self, vault, clock):
        super().__init__({"demo_mode": True}, vault, clock, PROMPTS)
        self.seen = []

    def _run(self, kind, what, system, blocks, input_bytes):
        self.seen.append(blocks[0]["text"])
        return {"question": "そのとき、どんな 音が していましたか？"}


class _Base(unittest.TestCase):
    def make(self):
        s = Srv(env_ok())
        self.addCleanup(s.close)
        s.login()
        c = Capture(s.app.vault, s.app.clock)
        s.app.claude = c
        return s, c

    def put_daily(self, s):
        day = ids.now_jst()[:10]
        st = s.call("PUT", "/api/daily/" + day, {"bed_time": BED, "wake_time": WAKE, "breakfast": "yes"})[0]
        self.assertEqual(st, 200)
        return day

    def turns(self, s):
        d = os.path.join(s.app.vault.root, "practice", "turns")
        return os.listdir(d) if os.path.isdir(d) else []

    def post(self, s, **extra):
        return s.call("POST", "/api/practice/turns", dict({"conditions": COND, "text": "朝です。"}, **extra))


class N_Closed(_Base):
    def test_old_screen_version_would_fail(self):
        want = _prompt_version("listener")
        self.assertNotEqual(OLD_VERSION, want)
        js = _text(os.path.join(STATIC, "app.js"))
        old_js = js.replace("'W-29': '%s'" % _w29(js), "'W-29': '%s'" % OLD_VERSION)
        self.assertNotEqual(_w29(old_js), want)

    def test_closed_shapes_are_refused_before_claude_and_storage(self):
        s, c = self.make()
        self.put_daily(s)
        shapes = [{"direction": "ippo"}, {"direction": "nokosu"}, {"direction": ""}, {"direction": False},
                  {"share_daily": True}, {"share_daily": "yes"}, {"share_daily": None}, {"share_daily": 0},
                  {"direction": "ippo", "share_daily": True}]
        for extra in shapes:
            st, j, _, _ = self.post(s, **extra)
            self.assertEqual((st, j["error"], j["detail"]), (400, "closed_input", routes_practice.D_CLOSED_INPUT), repr(extra))
        self.assertEqual(c.seen, [])
        self.assertEqual(self.turns(s), [])

    def test_old_names_are_gone(self):
        rp = _text(os.path.join(VAULT_APP, "routes_practice.py"))
        for gone in ("_check_direction", "bad_direction", "bad_daily_date", "D_BAD_DIRECTION", "D_BAD_DAILY_DATE", "get_daily(",
                     "from app_src.common import ids"):
            self.assertNotIn(gone, rp, gone)
        cc = _text(os.path.join(VAULT_APP, "claude_client.py"))
        for gone in ("DIRECTION_LABELS", "BREAKFAST_LABELS", "問いの 向き", "きょうの こと", "ゆうべ ねた 時刻", "direction=None", "daily=None"):
            self.assertNotIn(gone, cc, gone)


class T_Closed(_Base):
    def test_screen_version_matches_listener_prompt(self):
        want = _prompt_version("listener")
        self.assertEqual(want, "v0.3.4 / 2026-11-08")
        self.assertEqual(_w29(_text(os.path.join(STATIC, "app.js"))), want)
        for kind in ("reader", "arranger"):
            self.assertEqual(_text(os.path.join(PROMPTS, kind + ".txt")).split("\n", 1)[0], "# 版: v0.3.1 / 決めた日: 2026-11-05")

    def test_screen_shapes_pass_with_text_and_conditions_only(self):
        s, c = self.make()
        for extra in ({}, {"direction": None}, {"share_daily": False}, {"direction": None, "share_daily": False, "daily_date": "2026-01-01"}):
            st, j, _, _ = self.post(s, **extra)
            self.assertEqual(st, 200, repr(extra))
            self.assertEqual(j["readback"], "朝です。")
            turn = s.app.vault.get_turn(j["turn_id"])
            self.assertEqual((turn["direction"], turn["shared_daily"]), (None, False))
        want = "本人の文:\n朝です。\n\n条件:\n" + "\n".join("- %s: %s" % (k, COND[k]) for k in sorted(COND))
        self.assertEqual(set(c.seen), {want})
        self.assertEqual(len(c.seen), 4)   # 4 通りとも Claude を 1 回ずつ 呼んだ（検品の指摘で 足した）
        self.assertEqual(len(self.turns(s)), 4)

    def test_build_listener_signature_and_key(self):
        s, c = self.make()
        # 3 引数（direction だけ 戻した 形）でも 断られる こと（検品の指摘で 仕様 §6 の 3 引数に そろえた）
        with self.assertRaises(TypeError):
            c.build_listener("朝です。", COND, None)
        with self.assertRaises(TypeError):
            c.ask_question("朝です。", COND, None)
        with self.assertRaises(TypeError):
            c.build_listener("朝です。", COND, None, None)
        with self.assertRaises(TypeError):
            c.ask_question("朝です。", COND, None, None)
        system, blocks, key = c.build_listener("朝です。", COND)
        self.assertEqual(blocks, [{"type": "text", "text": "本人の文:\n朝です。\n\n条件:\n- amount: ふつう\n- ease: やさしい\n- input: 文字\n- length: みじかく\n- split: 文ごと"}])
        self.assertEqual(key.decode("utf-8"), json.dumps(
            {"conditions": {"amount": "ふつう", "ease": "やさしい", "input": "文字", "length": "みじかく", "split": "文ごと"}, "text": "朝です。"},
            ensure_ascii=False, sort_keys=True))

    def test_closed_message_is_clean(self):
        d = routes_practice.D_CLOSED_INPUT
        self.assertEqual(words.scan(d), [])
        self.assertIsNone(re.search(r"ましょう|しよう|ください|[！!]", d))
        self.assertFalse(hasattr(routes_practice, "D_BAD_DIRECTION"))


if __name__ == "__main__":
    unittest.main()
