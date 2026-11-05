# -*- coding: utf-8 -*-
"""ネットワークの行き先の検査と、走査の道具・デモ素材の検査。N_＝陰性対照（先）／T_＝本物。

socket.create_connection と http.client.HTTPConnection.connect を差し替えて、行き先（host, port）を記録する。
- 器の全操作で、行き先は受け口の (127.0.0.1, port) だけ。demo mode では Claude へ 0。
- 受け口の全操作で、受け口からの外向きの接続は 0。
- 差し替えは、許す行き先の外へは本当には出さない（OSError で止める）。
回し方（app_src の親の場所で）: python3 -B -m unittest app_src.tests.test_network -v
"""
import contextlib
import http.client
import importlib
import io
import json
import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import xml.dom.minidom
from unittest import mock

from app_src.common import contract, httpkit, vector, words
from app_src.receiver_app import main as port_main
from app_src.tools import scan_network, scan_leaks, scan_words
from app_src.vault_app import claude_client, routes_handoff, routes_practice, routes_statement, storage
from app_src.vault_app.appctx import VaultApp
from app_src.vault_app.auth import SESSION_COOKIE

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT_PASS = "test-passphrase-0000000000"
PORT_ENV = {"PORT_PASSPHRASE": PORT_PASS, "PORT_ID": "port-reference-01", "PORT_NAME": "受け口（参照用）"}
V1_PERSON = vector.vector_v1()["sender"]["person_ref"]
COND = {"amount": "ふつう", "split": "文ごと", "ease": "やさしい", "length": "みじかく", "input": "文字"}
TEXT1 = "この法律は、検査のための架空の条文である。"
LOOPBACK = "127.0.0.1"
PROXY_VARS = ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY")


def optional_routes(name):
    """別の部品の経路（在れば）。ImportError だけ握る。"""
    try:
        return importlib.import_module("app_src.vault_app." + name).ROUTES
    except ImportError:
        return []


class Recorder(object):
    def __init__(self, allowed_ports):
        self.allowed = set((LOOPBACK, p) for p in allowed_ports)
        self.cc, self.hc = [], []
        self.active = True

    def destinations(self):
        return set(self.cc) | set(self.hc)

    def __enter__(self):
        rec = self
        self._orig_cc = socket.create_connection
        self._orig_hc = http.client.HTTPConnection.connect

        def fake_cc(address, *a, **k):
            dest = (address[0], int(address[1]))
            if rec.active:
                rec.cc.append(dest)
            if dest not in rec.allowed:
                raise OSError("blocked by test")
            return rec._orig_cc(address, *a, **k)

        def fake_hc(conn):
            dest = (conn.host, int(conn.port))
            if rec.active:
                rec.hc.append(dest)
            if dest not in rec.allowed:
                raise OSError("blocked by test")
            return rec._orig_hc(conn)
        socket.create_connection = fake_cc
        http.client.HTTPConnection.connect = fake_hc
        return self

    def __exit__(self, *exc):
        socket.create_connection = self._orig_cc
        http.client.HTTPConnection.connect = self._orig_hc
        return False


def call(port, method, path, body=None, headers=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path), data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        r = urllib.request.urlopen(req, timeout=10)
    except urllib.error.HTTPError as e:
        r = e
    text = r.read().decode("utf-8")
    return r.status, (json.loads(text) if text else None), r.headers


class Server(object):
    def __init__(self, router, app, static=None):
        self.srv = httpkit.make_server(0, router, static, app)
        self.port = self.srv.server_address[1]
        self.th = threading.Thread(target=lambda: self.srv.serve_forever(poll_interval=0.02), daemon=True)
        self.th.start()

    def stop(self):
        if self.th is not None:
            self.srv.shutdown()
            self.srv.server_close()
            self.th.join(5)
            self.th = None


class _Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = self._tmp.name
        self._env = mock.patch.dict(os.environ)
        self._env.start()
        self.addCleanup(self._env.stop)
        for k in PROXY_VARS:
            os.environ.pop(k, None)
        os.environ["no_proxy"] = os.environ["NO_PROXY"] = "127.0.0.1,localhost"
        p = mock.patch.object(urllib.request, "_opener", None)      # 他の検査が作った opener（環境の proxy を覚えている）を使わない
        p.start()
        self.addCleanup(p.stop)

    def receiver(self):
        router, app = port_main.build_app(dict(PORT_ENV), os.path.join(self.tmp, "port"))
        s = Server(router, app, port_main.STATIC_DIR)
        self.addCleanup(s.stop)
        return s, app

    def vault_env(self, port_base, demo=False, api_key=None):
        os.makedirs(os.path.join(self.tmp, "law"), exist_ok=True)
        with open(os.path.join(self.tmp, "law", "a.json"), "w", encoding="utf-8") as f:
            json.dump({"id": "test-law-1", "law_name": "テスト法", "article": "第一条", "text_verbatim": TEXT1, "source_name": "テストの出典",
                       "retrieved_on": "0000-00-00", "retrieved_by": "検査の役", "set_version": "statutes-test", "verified_by_person": True}, f, ensure_ascii=False)
        cfg = {"vault_dir": os.path.join(self.tmp, "vault"), "port": 0, "passphrase": PORT_PASS, "api_key": api_key, "demo_mode": demo,
               "port_base_url": "http://127.0.0.1:%d" % port_base if port_base else "", "claude_model": "test-model",
               "app_root": APP_ROOT, "law_dir": os.path.join(self.tmp, "law")}
        vault = storage.open_vault(cfg["vault_dir"])
        app = VaultApp(cfg, vault, httpkit.SessionStore(clock=time.time), time.time)
        router = httpkit.Router()
        for mod in (routes_practice, routes_statement, routes_handoff):
            router.add_many(mod.ROUTES)
        router.add_many(optional_routes("routes_auth"))
        router.add_many(optional_routes("routes_records"))
        s = Server(router, app)
        self.addCleanup(s.stop)
        return s, app

    def run_vault_session(self, vs, app, rx, rx_app, code):
        """器の全操作を一通り（ログイン・記録・練習・意思表出文・持ち出し・つなぐ・わたす・返事）。"""
        tok = app.sessions.create()
        hdr = {"Cookie": "%s=%s" % (SESSION_COOKIE, tok)}
        results = []
        # ログイン（その経路が在れば）
        call(vs.port, "POST", "/api/login", {"passphrase": PORT_PASS})
        call(vs.port, "GET", "/api/status")
        # 記録
        rid = app.vault.add_record("もも", "image/png", b"dummy-bytes-momo-001", "2026-11-06T18:00:00+09:00")
        app.vault.set_subject(rid, {"author_role": "学校", "written_at": "2026-03-31", "procedure": "学期の記録", "confirmed_by_person": False})
        app.vault.add_annotation(rid, "注記です。")
        results.append(call(vs.port, "GET", "/api/records", headers=hdr)[0])
        # 読み取り（鍵なし = None・demo = 記録の応答）
        c = claude_client.get_client(app)
        if c is not None:
            try:
                md = c.read_image(rid)["markdown"]
                app.vault.set_derived(rid, md, {"demo": True})
            except claude_client.ClaudeError:
                pass
        # 練習
        st, o, _ = call(vs.port, "POST", "/api/practice/turns", {"conditions": COND, "text": "朝は ねむいです。"}, hdr)
        results.append(st)
        results.append(call(vs.port, "POST", "/api/practice/marks", {"turn_id": o["turn_id"], "mark": "残った"}, hdr)[0])
        results.append(call(vs.port, "GET", "/api/practice/summary", headers=hdr)[0])
        # 法令・意思表出文
        results.append(call(vs.port, "GET", "/api/law", headers=hdr)[0])
        st, o, _ = call(vs.port, "POST", "/api/statements", {"sections": {"trouble": "a", "wish": "b", "grounds": [rid], "statute_ids": ["test-law-1"]}}, hdr)
        sid = o["item_id"]
        arr = call(vs.port, "POST", "/api/statements/%s/arrange" % sid, {"confirm_send": True, "include_records": [rid]}, hdr)[0]
        results.append(arr)
        results.append(call(vs.port, "POST", "/api/statements/%s/finalize" % sid, {"text": "本人の字です。"}, hdr)[0])
        # 持ち出し
        path, _counts = app.vault.export_zip(os.path.join(self.tmp, "out"))
        self.assertTrue(os.path.isfile(path))
        # つなぐ・わたす・返事を読み直す
        st, o, _ = call(vs.port, "POST", "/api/pair", {"pairing_code": code}, hdr)
        self.assertEqual(st, 200, o)
        st, o, _ = call(vs.port, "POST", "/api/handoffs", {"statement_id": sid, "records": [{"record_id": rid, "parts": ["original", "annotations"]}]}, hdr)
        self.assertEqual((st, o["receipt"]["status"]), (201, "confirmed"))
        results.append(call(vs.port, "GET", "/api/handoffs", headers=hdr)[0])
        results.append(call(vs.port, "POST", "/api/replies/refresh", {}, hdr)[0])
        return arr, results


# =====================================================================
# N_ 陰性対照（先）
# =====================================================================

class N_Recorder(_Base):
    """記録の道具が、本当に行き先を拾い・外へ出さないこと。"""
    def test_recorder_catches_a_foreign_destination_and_blocks_it(self):
        with Recorder(allowed_ports=[]) as rec:
            with self.assertRaises(OSError):
                socket.create_connection(("api.anthropic.com", 443), timeout=1)
            with self.assertRaises(OSError):
                http.client.HTTPSConnection("example.invalid", timeout=1).connect()
        self.assertIn(("api.anthropic.com", 443), rec.destinations())
        self.assertIn(("example.invalid", 443), rec.destinations())

    def test_recorder_restores_originals(self):
        a, b = socket.create_connection, http.client.HTTPConnection.connect
        with Recorder(allowed_ports=[]):
            pass
        self.assertIs(socket.create_connection, a)
        self.assertIs(http.client.HTTPConnection.connect, b)

    def test_live_claude_call_is_seen_and_blocked(self):
        """鍵が在って demo でないとき、Claude の口は api.anthropic.com:443 へ向かう（この検査では出さない）。"""
        vs, app = self.vault_env(None, demo=False, api_key="dummy-key-value-0000")
        with Recorder(allowed_ports=[vs.port]) as rec:
            c = claude_client.get_client(app)
            with self.assertRaises(claude_client.ClaudeError) as cm:
                c.ask_question("朝です", COND)
        self.assertEqual(rec.destinations(), {("api.anthropic.com", 443)})
        self.assertNotIn("dummy-key-value-0000", str(cm.exception))
        self.assertEqual(str(cm.exception), claude_client.D_FAILED)
        log = app.vault.get_claude_log()
        self.assertEqual((len(log), log[0]["demo"]), (1, False))        # 送る前に記録は残る

    def test_scan_network_detects_injected_imports(self):
        root = os.path.join(self.tmp, "app_src_fake")
        for rel, src in [("vault_app/x.py", "import socket\n"), ("vault_app/y.py", "from urllib import request\n"),
                         ("receiver_app/z.py", "from app_src.vault_app import claude_client\n"),
                         ("receiver_app/w.py", "import http.client\n"),
                         ("vault_app/claude_client.py", "import urllib.request\n"), ("vault_app/handoff.py", "import urllib.request\n"),
                         ("vault_app/ok.py", "import urllib.parse\n")]:
            p = os.path.join(root, *rel.split("/"))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(src)
        n, found = scan_network.scan_all(root)
        self.assertEqual(sorted(set(f[0] for f in found)), ["receiver_app/w.py", "receiver_app/z.py", "vault_app/x.py", "vault_app/y.py"])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(scan_network.selftest())

    def test_scan_words_and_secrets_detect_injected_samples(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(scan_words.selftest())
            self.assertTrue(scan_leaks.selftest())
        self.assertTrue(scan_words.scan_py_source('a = "上達しました"\n'))
        self.assertTrue(scan_words.scan_text("あなたの 順位は"))
        self.assertFalse(scan_words.scan_py_source('"""評価 を 説明する docstring"""\nb = "通知表を 入れる"\n'))
        self.assertTrue(scan_leaks.scan_text("key = 'sk" + "-abcdefgh12345'"))
        self.assertFalse(scan_leaks.scan_text("task-id と desk-lamp と 00000000-0000-4000-8000-000000000011"))


# =====================================================================
# T_ 本物
# =====================================================================

class T_VaultDestinations(_Base):
    def one_run(self, demo):
        rx, rx_app = self.receiver()
        code = None
        # 受け口の面の準備は、記録を始める前に済ませる
        st, o, h = call(rx.port, "POST", "/face/login", {"passphrase": PORT_PASS})
        import re
        ck = re.search(r"cip_port_session=([0-9a-f]+)", h.get("Set-Cookie") or "").group(1)
        st, o, _ = call(rx.port, "POST", "/face/pairings", headers={"Cookie": "cip_port_session=" + ck})
        code = o["code"]
        vs, app = self.vault_env(rx.port, demo=demo)
        with Recorder(allowed_ports=[rx.port, vs.port]) as rec:
            arr, results = self.run_vault_session(vs, app, rx, rx_app, code)
        dests = rec.destinations() - {(LOOPBACK, vs.port)}        # テスト自身が器を叩いた分は数えない
        return dests, rx, arr, results

    def test_vault_without_key_goes_only_to_receiver(self):
        dests, rx, arr, results = self.one_run(demo=False)
        self.assertEqual(dests, {(LOOPBACK, rx.port)})
        self.assertEqual(arr, 503)                                  # 鍵なし = Claude を呼ばない
        self.assertTrue(all(r in (200, 201) for r in results if r != 503), results)

    def test_vault_in_demo_mode_goes_only_to_receiver_zero_to_claude(self):
        dests, rx, arr, results = self.one_run(demo=True)
        self.assertEqual(dests, {(LOOPBACK, rx.port)})
        self.assertNotIn(("api.anthropic.com", 443), dests)
        self.assertEqual(arr, 200)                                  # demo でも案は出る（記録の応答）

    def test_vault_does_not_connect_anywhere_before_handoff(self):
        rx, _ = self.receiver()
        vs, app = self.vault_env(rx.port, demo=True)
        tok = app.sessions.create()
        hdr = {"Cookie": "%s=%s" % (SESSION_COOKIE, tok)}
        with Recorder(allowed_ports=[rx.port, vs.port]) as rec:
            call(vs.port, "GET", "/api/practice/summary", headers=hdr)
            call(vs.port, "POST", "/api/practice/turns", {"conditions": COND, "text": "朝です"}, hdr)
            call(vs.port, "GET", "/api/law", headers=hdr)
            call(vs.port, "GET", "/api/handoffs", headers=hdr)
            time.sleep(0.3)                                         # 定期の読み直しが無いこと
        self.assertEqual(rec.destinations() - {(LOOPBACK, vs.port)}, set())


class T_ReceiverDestinations(_Base):
    def test_receiver_makes_no_outbound_connection(self):
        import re
        rx, app = self.receiver()
        app.person_ref_factory = lambda: V1_PERSON
        with Recorder(allowed_ports=[rx.port]) as rec:
            st, o, h = call(rx.port, "POST", "/face/login", {"passphrase": PORT_PASS})
            self.assertEqual(st, 200)
            ck = {"Cookie": "cip_port_session=" + re.search(r"cip_port_session=([0-9a-f]+)", h.get("Set-Cookie") or "").group(1)}
            st, o, _ = call(rx.port, "POST", "/face/pairings", headers=ck)
            st, o, _ = call(rx.port, "POST", "/v1/pair", {"pairing_code": o["code"]})
            self.assertEqual(st, 200)
            auth = {"Authorization": "Bearer " + o["token"]}
            b = vector.vector_v1()
            st, o, _ = call(rx.port, "POST", "/v1/bundles", b, auth)
            self.assertEqual(st, 201)
            self.assertEqual(call(rx.port, "GET", "/v1/bundles", headers=auth)[0], 200)
            self.assertEqual(call(rx.port, "GET", "/face/bundles", headers=ck)[0], 200)
            self.assertEqual(call(rx.port, "GET", "/face/bundles/" + b["bundle_id"], headers=ck)[0], 200)
            st, o, _ = call(rx.port, "POST", "/face/bundles/%s/replies" % b["bundle_id"],
                            {"human_attestation": True, "text": "読みました。", "attested_at": "2026-11-07T11:00:00+09:00"}, ck)
            self.assertEqual(st, 201)
            self.assertEqual(call(rx.port, "GET", "/v1/replies", headers=auth)[0], 200)
            time.sleep(0.2)
        # テストの呼び出し先（受け口自身）以外への接続は 0
        self.assertEqual(rec.destinations() - {(LOOPBACK, rx.port)}, set())


class T_Tools(_Base):
    def test_scan_network_zero_hits(self):
        n, found = scan_network.scan_all()
        self.assertGreater(n, 10)
        self.assertEqual(found, [])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(scan_network.main([]), 0)

    def test_claude_client_and_handoff_are_the_only_importers(self):
        """許す 2 本が、本当に urllib.request を使っている（走査が空振りでないことの対）。"""
        for rel in scan_network.ALLOWED:
            with open(os.path.join(APP_ROOT, *rel.split("/")), "rb") as f:
                src = f.read().decode("utf-8")
            self.assertTrue(scan_network.banned_imports(src), rel)

    def test_scan_words_zero_hits(self):
        n, found = scan_words.scan_all()
        self.assertGreater(n, 8)
        self.assertEqual(found, [], found)

    def test_scan_leaks_zero_hits(self):
        n, found = scan_leaks.scan_all()
        self.assertGreater(n, 20)
        self.assertEqual(found, [], found)


class T_DemoAssets(_Base):
    def test_recorded_responses_pass_the_same_rules_as_live_ones(self):
        base = os.path.join(APP_ROOT, "demo", "recorded")
        with open(os.path.join(base, "listener", "default.json"), encoding="utf-8") as f:
            self.assertIsNone(claude_client.check_question(json.load(f)["question"]))
        with open(os.path.join(base, "reader", "default.json"), encoding="utf-8") as f:
            md = json.load(f)["markdown"]
        self.assertTrue(md.strip())
        for line in md.split("\n"):
            self.assertEqual(words.scan(line), [], line)
        with open(os.path.join(base, "arranger", "default.json"), encoding="utf-8") as f:
            d = json.load(f)
        self.assertEqual(words.scan(d["draft_text"]), [])
        self.assertEqual(d["statute_ids"], [])

    def test_svg_docs(self):
        docs = os.path.join(APP_ROOT, "demo", "docs")
        names = sorted(os.listdir(docs))
        self.assertEqual(len(names), 4)
        for n in names:
            with open(os.path.join(docs, n), "rb") as f:
                raw = f.read()
            text = raw.decode("utf-8")
            dom = xml.dom.minidom.parseString(raw)
            root = dom.documentElement
            self.assertEqual((root.getAttribute("width"), root.getAttribute("height")), ("794", "1123"), n)
            self.assertNotIn("<script", text.lower(), n)
            self.assertNotIn("onload", text.lower(), n)
            self.assertIn("自作のダミー（デモ用）", text, n)
            self.assertIn("（自作のダミー）", text, n)
            self.assertNotIn("<image", text.lower(), n)

    def test_reader_refuses_svg(self):
        vs, app = self.vault_env(None, demo=True)
        rid = app.vault.add_record("ダミー", "image/svg+xml", b"<svg xmlns='x'></svg>")
        c = claude_client.get_client(app)
        with self.assertRaises(claude_client.ClaudeError) as cm:
            c.read_image(rid)
        self.assertEqual(str(cm.exception), "この形式は 読み取りに 送れません。")
        self.assertEqual(app.vault.get_claude_log(), [])            # 送っていない・記録も無い

    def test_reader_demo_result_and_rejection_of_forbidden_lines(self):
        vs, app = self.vault_env(None, demo=True)
        rid = app.vault.add_record("ダミー", "image/png", b"dummy-bytes-momo-001")
        c = claude_client.get_client(app)
        out = c.read_image(rid)
        self.assertIn("通知表（自作のダミー）", out["markdown"])
        self.assertEqual(out["meta"]["demo"], True)
        self.assertRegex(out["meta"]["prompt_sha256"], r"^[0-9a-f]{64}$")
        # 写しは他者の字の写し＝「治療」「評価」の字が在っても落とさない（検収の指摘）。促しの字の数だけ meta に残る。
        d = os.path.join(self.tmp, "demo_fake", "reader")
        os.makedirs(d)
        with open(os.path.join(d, "default.json"), "w", encoding="utf-8") as f:
            json.dump({"markdown": "# 診断書（自作のダミー）\n\n- 治療の方針: （省略）\n- 続きをどうぞ\n"}, f, ensure_ascii=False)
        c2 = claude_client.ClaudeClient(app.cfg, app.vault, time.time, os.path.join(APP_ROOT, "vault_app", "prompts"),
                                        demo_dir=os.path.join(self.tmp, "demo_fake"))
        out2 = c2.read_image(rid)
        self.assertIn("治療の方針", out2["markdown"])
        self.assertEqual(out2["meta"]["nudge_hits"], 1)
        with open(os.path.join(d, "default.json"), "w", encoding="utf-8") as f:
            json.dump({"markdown": "   "}, f)
        with self.assertRaises(httpkit.HttpError) as cm:
            c2.read_image(rid)
        self.assertEqual(cm.exception.code, "derived_empty")

    def test_demo_lookup_prefers_input_hash_file(self):
        vs, app = self.vault_env(None, demo=True)
        data = b"dummy-bytes-hash-lookup"
        rid = app.vault.add_record("ダミー", "image/png", data)
        d = os.path.join(self.tmp, "demo_fake", "reader")
        os.makedirs(d)
        with open(os.path.join(d, "default.json"), "w", encoding="utf-8") as f:
            json.dump({"markdown": "既定の写し"}, f, ensure_ascii=False)
        import hashlib
        with open(os.path.join(d, hashlib.sha256(data).hexdigest()[:16] + ".json"), "w", encoding="utf-8") as f:
            json.dump({"markdown": "この画像専用の写し"}, f, ensure_ascii=False)
        c = claude_client.ClaudeClient(app.cfg, app.vault, time.time, os.path.join(APP_ROOT, "vault_app", "prompts"),
                                       demo_dir=os.path.join(self.tmp, "demo_fake"))
        self.assertEqual(c.read_image(rid)["markdown"], "この画像専用の写し")
        other = app.vault.add_record("ダミー2", "image/png", b"another-bytes")
        self.assertEqual(c.read_image(other)["markdown"], "既定の写し")

    def test_prompts_have_no_forbidden_words_and_name_the_output_shape(self):
        pdir = os.path.join(APP_ROOT, "vault_app", "prompts")
        for n in ("reader", "listener", "arranger"):
            with open(os.path.join(pdir, n + ".txt"), encoding="utf-8") as f:
                t = f.read()
            self.assertEqual(words.scan(t), [], n)
            for extra in ("要約", "まとめ", "助言", "スキルアップ", "帰属的自己"):
                self.assertNotIn(extra, t, n)
        with open(os.path.join(pdir, "listener.txt"), encoding="utf-8") as f:
            self.assertIn('"question"', f.read())
        with open(os.path.join(pdir, "arranger.txt"), encoding="utf-8") as f:
            t = f.read()
        self.assertIn('"draft_text"', t)
        self.assertIn('"statute_ids"', t)


if __name__ == "__main__":
    unittest.main()
