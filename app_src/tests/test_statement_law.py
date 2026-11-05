# -*- coding: utf-8 -*-
"""C（意思表出文）と法令集の検査。N_＝陰性対照（先）／T_＝本物。

法令集は、テストの一時フォルダに作った架空の条（「テスト法」）だけを使う。実在の法令の字は書かない。
回し方（app_src の親の場所で）: python3 -B -m unittest app_src.tests.test_statement_law -v
"""
import json
import os
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from app_src.common import contract, httpkit
from app_src.vault_app import claude_client, law, routes_statement, storage
from app_src.vault_app.appctx import VaultApp
from app_src.vault_app.auth import SESSION_COOKIE

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPTS = os.path.join(APP_ROOT, "vault_app", "prompts")
TEXT1 = "この法律は、検査のための架空の条文である。"


def law_entry(i, verified=True, text=TEXT1, article="第一条", **over):
    d = {"id": i, "law_name": "テスト法", "article": article, "text_verbatim": text, "source_name": "テストの出典",
         "retrieved_on": "0000-00-00", "retrieved_by": "検査の役", "set_version": "statutes-test", "verified_by_person": verified,
         "note": "覚え書き"}
    d.update(over)
    return d


def write_law(dir_path, name, obj):
    os.makedirs(dir_path, exist_ok=True)
    with open(os.path.join(dir_path, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def build_corpus(dir_path):
    write_law(dir_path, "a.json", law_entry("test-law-1"))
    write_law(dir_path, "b.json", law_entry("test-law-2", text="この法律の第二条は、これも架空である。", article="第二条"))
    # 読み込まれてはいけない物
    write_law(dir_path, "c_unverified.json", law_entry("test-law-unverified", verified=False))
    write_law(dir_path, "d_string_true.json", law_entry("test-law-strtrue", verified="true"))
    write_law(dir_path, "e_one.json", law_entry("test-law-one", verified=1))
    bad = law_entry("test-law-nofield")
    del bad["set_version"]
    write_law(dir_path, "f_missing_field.json", bad)
    write_law(dir_path, "_g_underscore.json", law_entry("test-law-underscore"))
    write_law(dir_path, "h_dup1.json", law_entry("test-law-dup"))
    write_law(dir_path, "h_dup2.json", law_entry("test-law-dup", text="別の字"))
    write_law(dir_path, "i_badid.json", law_entry("../x"))
    with open(os.path.join(dir_path, "j_broken.json"), "w", encoding="utf-8") as f:
        f.write("{ これは JSON ではない")
    write_law(dir_path, "k_list.json", [law_entry("test-law-inlist")])
    return dir_path


class FakeClock(object):
    def __init__(self):
        self.t = time.time()

    def __call__(self):
        return self.t


class Env(object):
    def __init__(self, tmp, demo=False, api_key=None, **cfg_over):
        self.clock = FakeClock()
        self.law_dir = build_corpus(os.path.join(tmp, "law"))
        cfg = {"vault_dir": os.path.join(tmp, "vault"), "port": 0, "passphrase": None, "api_key": api_key,
               "demo_mode": demo, "port_base_url": "", "claude_model": "test-model", "app_root": APP_ROOT, "law_dir": self.law_dir}
        cfg.update(cfg_over)
        self.vault = storage.open_vault(cfg["vault_dir"])
        self.app = VaultApp(cfg, self.vault, httpkit.SessionStore(clock=self.clock), self.clock)
        router = httpkit.Router()
        router.add_many(routes_statement.ROUTES)
        self.srv = httpkit.make_server(0, router, None, self.app)
        self.port = self.srv.server_address[1]
        self.th = threading.Thread(target=lambda: self.srv.serve_forever(poll_interval=0.02), daemon=True)
        self.th.start()
        self.token = self.app.sessions.create()

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.th.join(5)

    def call(self, method, path, body=None, login=True):
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
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

    def new_statement(self, **sec):
        sections = {"trouble": "朝の じゅんびに 時間が かかります。", "wish": "始まりを すこし 遅くしたいです。", "grounds": [], "statute_ids": []}
        sections.update(sec)
        st, o = self.call("POST", "/api/statements", {"sections": sections})
        assert st == 201, (st, o)
        return o["item_id"]


class _Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = self._tmp.name

    def env(self, **kw):
        e = Env(self.tmp, **kw)
        self.addCleanup(e.close)
        return e

    def fake_arranger(self, e, response):
        d = os.path.join(self.tmp, "demo_fake")
        os.makedirs(os.path.join(d, "arranger"), exist_ok=True)
        with open(os.path.join(d, "arranger", "default.json"), "w", encoding="utf-8") as f:
            json.dump(response, f, ensure_ascii=False)
        c = claude_client.ClaudeClient(e.app.cfg, e.vault, e.clock, PROMPTS, demo_dir=d)
        e.app.claude = c
        return c

    def add_record_with_derived(self, e, name="もも", md="# 通知表（自作のダミー）\n\n- こくご: たのしく とりくんだ\n"):
        rid = e.vault.add_record(name, "image/png", b"dummy-bytes-momo-001", "2026-11-06T18:00:00+09:00")
        e.vault.set_derived(rid, md, {"demo": True})
        return rid


# =====================================================================
# N_ 陰性対照（先）
# =====================================================================

class N_Corpus(_Base):
    def test_only_verified_true_is_loaded(self):
        e = self.env()
        c = law.for_app(e.app)
        self.assertEqual(c.ids(), ["test-law-1", "test-law-2"])
        for bad in ("test-law-unverified", "test-law-strtrue", "test-law-one", "test-law-nofield", "test-law-underscore",
                    "test-law-dup", "test-law-inlist", "../x"):
            self.assertIsNone(c.get(bad), bad)
            self.assertIsNone(c.statute_for_bundle(bad), bad)

    def test_unverified_not_in_api(self):
        e = self.env()
        st, o = e.call("GET", "/api/law")
        self.assertEqual([x["id"] for x in o["law"]], ["test-law-1", "test-law-2"])
        for bad in ("test-law-unverified", "test-law-strtrue", "nothing"):
            st, _ = e.call("GET", "/api/law/" + bad)
            self.assertEqual(st, 404, bad)

    def test_missing_dir_is_empty_corpus(self):
        self.assertEqual(law.load_corpus(os.path.join(self.tmp, "nowhere")), {})

    def test_one_char_change_does_not_match(self):
        c = law.Corpus(law.load_corpus(build_corpus(os.path.join(self.tmp, "l2"))))
        self.assertEqual(c.match_verbatim(TEXT1), "test-law-1")        # 対（本物は通る）
        for t in (TEXT1[:-1], TEXT1 + " ", " " + TEXT1, TEXT1.replace("検査", "検算"), TEXT1.replace("、", ","), "", None, 5):
            self.assertIsNone(c.match_verbatim(t), repr(t))

    def test_shipped_example_is_not_loaded(self):
        self.assertEqual(law.load_corpus(os.path.join(APP_ROOT, "law_corpus")), {})      # 見本は false = 読まれない

    def test_login_required(self):
        e = self.env()
        for method, path in [("GET", "/api/law"), ("GET", "/api/law/test-law-1"), ("GET", "/api/statements"),
                             ("POST", "/api/statements"), ("GET", "/api/statements/x")]:
            st, _ = e.call(method, path, {"sections": {}} if method == "POST" else None, login=False)
            self.assertEqual(st, 401, path)


class N_StatementRules(_Base):
    def test_finalize_with_unknown_or_unverified_statute_400(self):
        e = self.env()
        for bad in ("nothing", "test-law-unverified", "test-law-strtrue"):
            sid = e.new_statement(statute_ids=["test-law-1", bad])
            st, o = e.call("POST", "/api/statements/%s/finalize" % sid, {"text": "本人の 字です。"})
            self.assertEqual((st, o["error"]), (400, "statute_unknown"), bad)
            self.assertIsNone(e.vault.get_statement(sid)["finalized_at"])
            self.assertEqual(e.vault.get_statement(sid)["text"], "")

    def test_finalize_with_sections_carrying_unknown_id_400(self):
        e = self.env()
        sid = e.new_statement()
        st, o = e.call("POST", "/api/statements/%s/finalize" % sid,
                       {"text": "本人の 字です。", "sections": {"trouble": "a", "wish": "b", "statute_ids": ["ghost"]}})
        self.assertEqual((st, o["error"]), (400, "statute_unknown"))

    def test_finalize_empty_text_400(self):
        e = self.env()
        sid = e.new_statement()
        for t in ("", "  \n", None, 5):
            st, _ = e.call("POST", "/api/statements/%s/finalize" % sid, {"text": t})
            self.assertEqual(st, 400, repr(t))

    def test_arrange_needs_confirm_send_true(self):
        e = self.env(demo=True)
        sid = e.new_statement()
        for body in ({}, {"confirm_send": False}, {"confirm_send": "true"}, {"confirm_send": 1}, {"include_records": []}):
            st, o = e.call("POST", "/api/statements/%s/arrange" % sid, body)
            self.assertEqual((st, o["error"]), (400, "confirm_required"), repr(body))
        self.assertEqual(e.vault.get_claude_log(), [])          # 何も送っていない
        self.assertIsNone(e.vault.get_statement(sid)["draft"])

    def test_arrange_without_claude_503(self):
        e = self.env()
        sid = e.new_statement()
        st, o = e.call("POST", "/api/statements/%s/arrange" % sid, {"confirm_send": True})
        self.assertEqual((st, o["error"]), (503, "claude_unavailable"))

    def test_arrange_draft_with_forbidden_word_is_rejected_and_not_saved(self):
        e = self.env(demo=True)
        self.fake_arranger(e, {"draft_text": "この記録を評価する 案です。", "statute_ids": []})
        sid = e.new_statement()
        st, o = e.call("POST", "/api/statements/%s/arrange" % sid, {"confirm_send": True})
        self.assertEqual((st, o["error"]), (422, "draft_rejected"))
        self.assertIsNone(e.vault.get_statement(sid)["draft"])

    def test_arrange_bad_shapes_rejected(self):
        e = self.env(demo=True)
        sid = e.new_statement()
        for resp in ({"draft_text": "", "statute_ids": []}, {"draft_text": 5}, {"statute_ids": []}):
            self.fake_arranger(e, resp)
            st, o = e.call("POST", "/api/statements/%s/arrange" % sid, {"confirm_send": True})
            self.assertEqual((st, o["error"]), (422, "draft_rejected"), repr(resp))

    def test_arrange_unknown_record_400(self):
        e = self.env(demo=True)
        sid = e.new_statement()
        st, o = e.call("POST", "/api/statements/%s/arrange" % sid, {"confirm_send": True, "include_records": ["rec-nothing"]})
        self.assertEqual((st, o["error"]), (400, "record_unknown"))

    def test_final_cannot_be_changed(self):
        e = self.env(demo=True)
        sid = e.new_statement()
        st, _ = e.call("POST", "/api/statements/%s/finalize" % sid, {"text": "本人の 字です。"})
        self.assertEqual(st, 200)
        for method, path, body in [("POST", "/api/statements/%s/finalize" % sid, {"text": "別の字"}),
                                   ("PUT", "/api/statements/%s" % sid, {"sections": {"trouble": "変える"}}),
                                   ("POST", "/api/statements/%s/arrange" % sid, {"confirm_send": True})]:
            st, o = e.call(method, path, body)
            self.assertEqual((st, o["error"]), (409, "already_final"), path)
        self.assertEqual(e.vault.get_statement(sid)["text"], "本人の 字です。")

    def test_bad_sections_and_unknown_ids(self):
        e = self.env()
        for sec in (None, "x", [], {"trouble": 5}, {"grounds": "rec"}, {"grounds": [1]}, {"statute_ids": [""]},
                    {"trouble": "あ" * 4001}):
            st, _ = e.call("POST", "/api/statements", {"sections": sec})
            self.assertIn(st, (400, 413), repr(sec)[:40])
        st, o = e.call("POST", "/api/statements", {"sections": {"grounds": ["rec-nothing"]}})
        self.assertEqual((st, o["error"]), (400, "record_unknown"))
        self.assertEqual(e.vault.list_statements(), [])
        for method in ("GET", "PUT", "POST"):
            path = "/api/statements/st-nothing" + ("/finalize" if method == "POST" else "")
            st, _ = e.call(method, path, {"sections": {}, "text": "a", "confirm_send": True} if method != "GET" else None)
            self.assertEqual(st, 404, method)


# =====================================================================
# T_ 本物
# =====================================================================

class T_Law(_Base):
    def test_index_and_get_shapes(self):
        e = self.env()
        st, o = e.call("GET", "/api/law")
        self.assertEqual(st, 200)
        self.assertEqual(o["law"][0], {"id": "test-law-1", "law_name": "テスト法", "article": "第一条"})
        st, g = e.call("GET", "/api/law/test-law-1")
        self.assertEqual(st, 200)
        self.assertEqual(set(g), set(["id"] + contract.STATUTE_FIELDS))
        self.assertEqual(g["text_verbatim"], TEXT1)

    def test_statute_for_bundle_is_the_seven_fields(self):
        e = self.env()
        s = law.for_app(e.app).statute_for_bundle("test-law-2")
        self.assertEqual(sorted(s), sorted(contract.STATUTE_FIELDS))
        self.assertEqual(s["article"], "第二条")

    def test_exact_match(self):
        c = law.for_app(self.env().app)
        self.assertEqual(c.match_verbatim(TEXT1), "test-law-1")
        self.assertEqual(c.match_verbatim("この法律の第二条は、これも架空である。"), "test-law-2")

    def test_changes_to_verification_take_effect_without_restart(self):
        e = self.env()
        write_law(e.law_dir, "a.json", law_entry("test-law-1", verified=False))
        st, o = e.call("GET", "/api/law")
        self.assertEqual([x["id"] for x in o["law"]], ["test-law-2"])


class T_Statement(_Base):
    def test_create_get_list_update(self):
        e = self.env()
        rid = self.add_record_with_derived(e)
        sid = e.new_statement(grounds=[rid, rid], statute_ids=["test-law-1", "ghost"])
        st, o = e.call("GET", "/api/statements/" + sid)
        self.assertEqual(st, 200)
        self.assertIsNone(o["finalized_at"])
        self.assertEqual(o["text"], "")
        self.assertEqual(o["sections"]["grounds"], [rid])
        self.assertEqual(o["sections"]["statute_ids"], ["test-law-1"])          # 法令集に無い id は外して返す
        self.assertEqual(o["sections"]["statutes"][0]["text_verbatim"], TEXT1)
        st, o = e.call("PUT", "/api/statements/" + sid, {"sections": {"trouble": "書き直し", "wish": "", "grounds": [], "statute_ids": []}})
        self.assertEqual((st, o["sections"]["trouble"]), (200, "書き直し"))
        st, lst = e.call("GET", "/api/statements")
        self.assertEqual([x["item_id"] for x in lst["statements"]], [sid])

    def test_list_is_newest_first(self):
        e = self.env()
        a = e.new_statement()
        time.sleep(0.01)
        b = e.new_statement()
        st, lst = e.call("GET", "/api/statements")
        self.assertEqual([x["item_id"] for x in lst["statements"]], [b, a])

    def test_arrange_drops_ids_outside_corpus_and_labels_as_draft(self):
        e = self.env(demo=True)
        self.fake_arranger(e, {"draft_text": "困っていることを 並べた 案です。", "statute_ids": ["test-law-1", "ghost", "test-law-unverified", 5, "test-law-1"]})
        sid = e.new_statement()
        st, o = e.call("POST", "/api/statements/%s/arrange" % sid, {"confirm_send": True})
        self.assertEqual(st, 200)
        self.assertEqual(o["draft"], {"text": "困っていることを 並べた 案です。", "label": "案", "statute_ids": ["test-law-1"]})
        self.assertEqual(o["dropped_ids"], 3)
        saved = e.vault.get_statement(sid)
        self.assertEqual(saved["draft"]["label"], "案")
        self.assertIsNone(saved["finalized_at"])         # 案は最終版にならない
        self.assertEqual(saved["text"], "")
        st, g = e.call("GET", "/api/statements/" + sid)
        self.assertEqual(g["draft"]["statutes"][0]["id"], "test-law-1")

    def test_arrange_sends_derived_markdown_only_and_index_headings_only(self):
        e = self.env(demo=True)
        c = self.fake_arranger(e, {"draft_text": "案です。", "statute_ids": []})
        seen = {}

        def spy(kind, what, system, blocks, input_bytes):
            seen["blocks"] = json.dumps(blocks, ensure_ascii=False)
            seen["what"] = what
            return {"draft_text": "案です。", "statute_ids": []}
        c._run = spy
        md = "# 通知表（自作のダミー）\n\n- こくご: たのしく とりくんだ\n"
        rid = self.add_record_with_derived(e, md=md)
        other = self.add_record_with_derived(e, name="りんご", md="# 別の写し\n")
        sid = e.new_statement(trouble="朝が つらい", wish="遅くしたい")
        st, _ = e.call("POST", "/api/statements/%s/arrange" % sid, {"confirm_send": True, "include_records": [rid]})
        self.assertEqual(st, 200)
        b = seen["blocks"]
        self.assertIn("朝が つらい", b)
        self.assertIn("遅くしたい", b)
        self.assertIn("たのしく とりくんだ", b)
        self.assertNotIn("別の写し", b)                   # 選ばなかった記録は送らない
        self.assertNotIn("image", b)                      # 原本の画像は送らない
        self.assertNotIn("base64", b)
        self.assertIn("test-law-1 | テスト法 | 第一条", b)
        self.assertNotIn(TEXT1, b)                        # 条文の本文は送らない（見出しだけ）

    def test_arrange_in_demo_with_shipped_recording(self):
        e = self.env(demo=True)
        sid = e.new_statement()
        st, o = e.call("POST", "/api/statements/%s/arrange" % sid, {"confirm_send": True})
        self.assertEqual(st, 200)
        self.assertEqual(o["draft"]["label"], "案")
        log = e.vault.get_claude_log()
        self.assertEqual((log[-1]["kind"], log[-1]["demo"]), ("arranger", True))

    def test_finalize_is_only_by_the_person_and_text_is_verbatim(self):
        e = self.env(demo=True)
        self.fake_arranger(e, {"draft_text": "案の字です。", "statute_ids": ["test-law-1"]})
        sid = e.new_statement(statute_ids=["test-law-1"])
        e.call("POST", "/api/statements/%s/arrange" % sid, {"confirm_send": True})
        self.assertIsNone(e.vault.get_statement(sid)["finalized_at"])           # arrange だけでは最終版にならない
        mine = "朝の ことを\n  相談したいです。 "
        st, o = e.call("POST", "/api/statements/%s/finalize" % sid, {"text": mine})
        self.assertEqual(st, 200)
        self.assertEqual(o["text"], mine)                                       # 1 字も足さない・削らない
        self.assertNotIn("使えます", o["text"])
        self.assertNotIn("該当", o["text"])
        saved = e.vault.get_statement(sid)
        self.assertEqual(saved["text"], mine)
        self.assertIsNotNone(saved["finalized_at"])
        self.assertEqual(saved["author"], "person")
        self.assertEqual(o["sections"]["statutes"][0]["text_verbatim"], TEXT1)

    def test_finalize_can_replace_sections(self):
        e = self.env()
        sid = e.new_statement()
        st, o = e.call("POST", "/api/statements/%s/finalize" % sid,
                       {"text": "本人の 字です。", "sections": {"trouble": "a", "wish": "b", "grounds": [], "statute_ids": ["test-law-2"]}})
        self.assertEqual(st, 200)
        self.assertEqual(e.vault.get_statement(sid)["sections"]["statute_ids"], ["test-law-2"])

    def test_statements_counted_in_manifest(self):
        e = self.env()
        e.new_statement()
        e.new_statement()
        self.assertEqual(e.vault.counts()["statements"], 2)


if __name__ == "__main__":
    unittest.main()
