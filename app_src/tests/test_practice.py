# -*- coding: utf-8 -*-
"""A（れんしゅう）と Claude の口（聞き役）の検査。N_＝陰性対照（先）／T_＝本物。

回し方（app_src の親の場所で）: python3 -B -m unittest app_src.tests.test_practice -v
ここ（テスト）だけは urllib を使う（本物のコードの外）。Claude には出ない（demo mode か偽の応答）。
"""
import json
import os
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from app_src.common import httpkit
from app_src.vault_app import claude_client, routes_practice, storage
from app_src.vault_app.appctx import VaultApp
from app_src.vault_app.auth import SESSION_COOKIE

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPTS = os.path.join(APP_ROOT, "vault_app", "prompts")
COND = {"amount": "ふつう", "split": "文ごと", "ease": "やさしい", "length": "みじかく", "input": "文字"}


class FakeClock(object):
    def __init__(self):
        self.t = time.time()

    def __call__(self):
        return self.t


class Env(object):
    """この部品の経路だけを立てる小さな枠。ログインは cookie を直接作る。"""
    def __init__(self, tmp, demo=False, api_key=None, modules=None, **cfg_over):
        self.clock = FakeClock()
        cfg = {"vault_dir": os.path.join(tmp, "vault"), "port": 0, "passphrase": None, "api_key": api_key,
               "demo_mode": demo, "port_base_url": "", "claude_model": "test-model", "app_root": APP_ROOT}
        cfg.update(cfg_over)
        self.vault = storage.open_vault(cfg["vault_dir"])
        self.app = VaultApp(cfg, self.vault, httpkit.SessionStore(clock=self.clock), self.clock)
        router = httpkit.Router()
        for m in (modules or [routes_practice]):
            router.add_many(m.ROUTES)
        self.srv = httpkit.make_server(0, router, None, self.app)
        self.port = self.srv.server_address[1]
        self.th = threading.Thread(target=lambda: self.srv.serve_forever(poll_interval=0.02), daemon=True)
        self.th.start()
        self.token = self.app.sessions.create()

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.th.join(5)

    def call(self, method, path, body=None, login=True, raw=None):
        data = raw if raw is not None else (None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8"))
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path), data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        if login:
            req.add_header("Cookie", "%s=%s" % (SESSION_COOKIE, self.token))
        try:
            r = urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as e:
            r = e
        text = r.read().decode("utf-8")
        return r.status, (json.loads(text) if text else None)


class _Base(unittest.TestCase):
    modules = None

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = self._tmp.name

    def env(self, **kw):
        e = Env(self.tmp, modules=self.modules, **kw)
        self.addCleanup(e.close)
        return e

    def demo_dir(self, listener=None):
        """偽の応答の置き場。listener の dict を default.json に置く。"""
        d = os.path.join(self.tmp, "demo_fake")
        os.makedirs(os.path.join(d, "listener"), exist_ok=True)
        with open(os.path.join(d, "listener", "default.json"), "w", encoding="utf-8") as f:
            json.dump(listener, f, ensure_ascii=False)
        return d

    def client_with(self, e, listener):
        c = claude_client.ClaudeClient(e.app.cfg, e.vault, e.clock, PROMPTS, demo_dir=self.demo_dir(listener))
        e.app.claude = c
        return c


# =====================================================================
# N_ 陰性対照（先）
# =====================================================================

class N_QuestionRules(_Base):
    """問いの縛り: 外れたら落ちる（偽の応答で ClaudeClient を通す）。"""
    def ask(self, answer):
        e = self.env(demo=True)
        c = self.client_with(e, {"question": answer})
        return c.ask_question("朝は ねむいです。", COND)

    def test_forbidden_word_dropped(self):
        self.assertEqual(self.ask("それを 評価する ために 聞きます？"), (None, "forbidden_word"))

    def test_nudge_word_dropped(self):
        self.assertEqual(self.ask("続きをどうぞ？"), (None, "forbidden_word"))

    def test_61_chars_dropped(self):
        q = "あ" * 60 + "？"
        self.assertEqual(len(q), 61)
        self.assertEqual(self.ask(q), (None, "too_long"))

    def test_digit_dropped(self):
        self.assertEqual(self.ask("朝の 7時の ことを 聞かせて もらえますか？"), (None, "has_digit"))
        self.assertEqual(self.ask("朝の ７時の ことを 聞かせて もらえますか？"), (None, "has_digit"))

    def test_bad_ending_dropped(self):
        self.assertEqual(self.ask("そのとき どんな 音が していましたか"), (None, "bad_ending"))

    def test_empty_and_multiline_dropped(self):
        self.assertEqual(self.ask(""), (None, "empty"))
        self.assertEqual(self.ask("そのとき、\nどんな 音？"), (None, "multiline"))

    def test_not_a_string_dropped(self):
        self.assertEqual(self.ask(123), (None, "bad_json"))

    def test_not_json_dropped(self):
        e = self.env(demo=True)
        c = self.client_with(e, {"question": "x"})
        c._run = lambda *a, **k: "これは JSON ではありません"
        self.assertEqual(c.ask_question("朝は ねむいです。", COND), (None, "bad_json"))

    def test_limit_is_exactly_60(self):
        q = "あ" * 59 + "？"
        self.assertEqual(len(q), 60)
        self.assertEqual(self.ask(q), (q, None))      # 60 字ちょうどは通る（境界の対）


class N_PracticeInput(_Base):
    modules = None

    def test_login_required(self):
        e = self.env()
        for method, path, body in [("POST", "/api/practice/turns", {"conditions": COND, "text": "a"}),
                                   ("POST", "/api/practice/marks", {"turn_id": "x", "mark": "残った"}),
                                   ("GET", "/api/practice/summary", None), ("GET", "/api/practice/conditions", None)]:
            st, _ = e.call(method, path, body, login=False)
            self.assertEqual(st, 401, path)

    def test_condition_value_out_of_set_400(self):
        e = self.env()
        for k, bad in [("amount", "たくさん"), ("split", "全部"), ("ease", "むずかしい"), ("length", "ふつう"), ("input", "声から文字")]:
            c = dict(COND, **{k: bad})
            st, _ = e.call("POST", "/api/practice/turns", {"conditions": c, "text": "朝です"})
            self.assertEqual(st, 400, k)
        self.assertEqual(e.vault.counts()["marks"], 0)
        self.assertFalse(os.path.isdir(os.path.join(e.vault.root, "practice", "turns")))

    def test_condition_shape_400(self):
        e = self.env()
        short = {k: v for k, v in COND.items() if k != "ease"}
        for c in (short, dict(COND, extra="x"), "ふつう", None, [], dict(COND, amount=True)):
            st, _ = e.call("POST", "/api/practice/turns", {"conditions": c, "text": "朝です"})
            self.assertEqual(st, 400, repr(c))

    def test_whitespace_only_400(self):
        e = self.env()
        for t in ("", "   ", "\n\t 　", None, 5):
            st, _ = e.call("POST", "/api/practice/turns", {"conditions": COND, "text": t})
            self.assertEqual(st, 400, repr(t))

    def test_over_4000_chars_413(self):
        e = self.env()
        st, _ = e.call("POST", "/api/practice/turns", {"conditions": COND, "text": "あ" * 4001})
        self.assertEqual(st, 413)
        st, _ = e.call("POST", "/api/practice/turns", {"conditions": COND, "text": "あ" * 4000})
        self.assertEqual(st, 200)      # 境界の対

    def test_mark_unknown_turn_404(self):
        e = self.env()
        st, _ = e.call("POST", "/api/practice/marks", {"turn_id": "turn-nothing", "mark": "残った"})
        self.assertEqual(st, 404)
        st, _ = e.call("POST", "/api/practice/marks", {"turn_id": "../x", "mark": "残った"})
        self.assertEqual(st, 404)
        self.assertEqual(e.vault.counts()["marks"], 0)

    def test_mark_value_out_of_set_400(self):
        e = self.env()
        st, o = e.call("POST", "/api/practice/turns", {"conditions": COND, "text": "朝です"})
        self.assertEqual(st, 200)
        for m in ("上手", "A", "", None, 3):
            st, _ = e.call("POST", "/api/practice/marks", {"turn_id": o["turn_id"], "mark": m})
            self.assertEqual(st, 400, repr(m))
        self.assertEqual(e.vault.counts()["marks"], 0)


# =====================================================================
# T_ 本物
# =====================================================================

class T_Practice(_Base):
    def test_readback_is_exact_string(self):
        e = self.env()
        for t in ("朝は ねむいです。", "  前後に 空白  ", "一行目\n\n三行目\n", "<b>タグ</b> & \"引用\" 'x'", "ＡＢＣ　全角 ｱｲｳ", "a" * 4000):
            st, o = e.call("POST", "/api/practice/turns", {"conditions": COND, "text": t})
            self.assertEqual(st, 200)
            self.assertEqual(o["readback"], t)
            self.assertEqual(e.vault.get_turn(o["turn_id"])["readback"], t)
            self.assertEqual(e.vault.get_turn(o["turn_id"])["text"], t)

    def test_claude_text_never_replaces_readback(self):
        """偽の聞き役が 読み返しの字を返そうとしても、読み返しは本人の文のまま。"""
        e = self.env(demo=True)
        self.client_with(e, {"question": "そのとき、どんな 音が していましたか？", "readback": "書き換えた字"})
        st, o = e.call("POST", "/api/practice/turns", {"conditions": COND, "text": "朝は ねむいです。"})
        self.assertEqual(o["readback"], "朝は ねむいです。")

    def test_no_claude_still_keeps_turn(self):
        e = self.env()      # 鍵なし・demo なし
        st, o = e.call("POST", "/api/practice/turns", {"conditions": COND, "text": "朝です"})
        self.assertEqual(st, 200)
        self.assertIsNone(o["question"])
        self.assertEqual(o["reason"], "claude_unavailable")
        t = e.vault.get_turn(o["turn_id"])
        self.assertEqual((t["question"], t["question_dropped_reason"], t["conditions"]), (None, "claude_unavailable", COND))
        self.assertEqual(e.vault.get_claude_log(), [])      # 何も送っていない

    def test_demo_mode_gives_recorded_question_and_logs(self):
        e = self.env(demo=True)
        st, o = e.call("POST", "/api/practice/turns", {"conditions": COND, "text": "朝は ねむいです。"})
        self.assertEqual(st, 200)
        self.assertEqual(o["question"], "そのとき、どんな 音が していましたか？")
        self.assertIsNone(o["reason"])
        log = e.vault.get_claude_log()
        self.assertEqual(len(log), 1)
        self.assertEqual((log[0]["kind"], log[0]["demo"]), ("listener", True))
        self.assertNotIn("朝は", json.dumps(log, ensure_ascii=False))      # 本文は記録に入れない

    def test_bad_question_dropped_but_readback_kept(self):
        e = self.env(demo=True)
        self.client_with(e, {"question": "もっと 評価する ために 話してください？"})
        st, o = e.call("POST", "/api/practice/turns", {"conditions": COND, "text": "朝は ねむいです。"})
        self.assertEqual((st, o["question"], o["reason"], o["readback"]), (200, None, "forbidden_word", "朝は ねむいです。"))
        self.assertEqual(e.vault.get_turn(o["turn_id"])["question_dropped_reason"], "forbidden_word")

    def test_claude_error_keeps_turn(self):
        e = self.env(demo=True)

        class Boom(object):
            def ask_question(self, *a):
                raise claude_client.ClaudeError("x")
        e.app.claude = Boom()
        st, o = e.call("POST", "/api/practice/turns", {"conditions": COND, "text": "朝です"})
        self.assertEqual((st, o["question"], o["reason"]), (200, None, "claude_failed"))
        self.assertIsNotNone(e.vault.get_turn(o["turn_id"]))

    def test_mark_then_summary_count_up_by_one(self):
        e = self.env()
        st, before = e.call("GET", "/api/practice/summary")
        self.assertEqual((st, before), (200, {}))
        st, o = e.call("POST", "/api/practice/turns", {"conditions": COND, "text": "朝です"})
        st, m = e.call("POST", "/api/practice/marks", {"turn_id": o["turn_id"], "mark": "一部"})
        self.assertEqual(st, 200)
        self.assertEqual(m["summary_line"], "印を のこしました（一部・ふつう／文ごと）。")
        st, after = e.call("GET", "/api/practice/summary")
        key = storage.condition_key(COND)
        self.assertEqual(after, {key: {"一部": 1}})
        e.call("POST", "/api/practice/marks", {"turn_id": o["turn_id"], "mark": "一部"})
        st, after2 = e.call("GET", "/api/practice/summary")
        self.assertEqual(after2[key]["一部"], 2)
        self.assertEqual(e.vault.counts()["marks"], 2)

    def test_summary_has_only_counts_by_mark(self):
        e = self.env()
        for mark in ("残った", "一部", "残らなかった", "なし"):
            st, o = e.call("POST", "/api/practice/turns", {"conditions": COND, "text": "朝です"})
            e.call("POST", "/api/practice/marks", {"turn_id": o["turn_id"], "mark": mark})
        st, s = e.call("GET", "/api/practice/summary")
        self.assertEqual(len(s), 1)
        row = list(s.values())[0]
        self.assertEqual(set(row), set(storage.MARKS))
        self.assertTrue(all(isinstance(v, int) for v in row.values()))
        text = json.dumps(s, ensure_ascii=False)
        for bad in ("rate", "total", "percent", "rank", "score", "割合", "合計", "順位", "点"):
            self.assertNotIn(bad, text)

    def test_conditions_list(self):
        e = self.env()
        st, o = e.call("GET", "/api/practice/conditions")
        self.assertEqual(st, 200)
        self.assertEqual([c["key"] for c in o["conditions"]], ["amount", "split", "ease", "length", "input"])
        self.assertEqual(o["conditions"][0]["values"], ["すくなめ", "ふつう", "おおめ"])


class T_ClaudeClientDemo(_Base):
    def test_demo_log_has_no_secrets_or_bodies(self):
        e = self.env(demo=True, api_key="dummy-key-value-0000")
        c = claude_client.get_client(e.app)
        c.ask_question("ひみつの 本文です。", COND)
        log = e.vault.get_claude_log()
        self.assertEqual(set(log[0]), set(storage.CLAUDE_LOG_KEYS))
        s = json.dumps(log, ensure_ascii=False)
        self.assertNotIn("ひみつ", s)
        self.assertNotIn("dummy-key-value-0000", s)

    def test_get_client_none_without_key_or_demo(self):
        e = self.env()
        self.assertIsNone(claude_client.get_client(e.app))
        e2 = self.env(demo=True)
        self.assertIsNotNone(claude_client.get_client(e2.app))

    def test_fenced_json_from_live_text_is_read(self):
        e = self.env(demo=True)
        c = self.client_with(e, {"question": "x"})
        c._run = lambda *a, **k: '```json\n{"question": "そのとき、どんな 音が していましたか？"}\n```'
        self.assertEqual(c.ask_question("朝です", COND), ("そのとき、どんな 音が していましたか？", None))


if __name__ == "__main__":
    unittest.main()
