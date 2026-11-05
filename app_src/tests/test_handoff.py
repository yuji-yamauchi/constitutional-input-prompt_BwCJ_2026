# -*- coding: utf-8 -*-
"""渡す口（器 -> 受け口）の検査。N_＝陰性対照（先）／T_＝本物。

受け口（receiver_app.main.build_app）と器を、同じプロセスの別ポートに立てる（127.0.0.1 だけ）。
控えを偽る受け口は、テストの中の小さな偽の受け口で用意する。
回し方（app_src の親の場所で）: python3 -B -m unittest app_src.tests.test_handoff -v
"""
import base64
import http.server
import json
import os
import re
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from app_src.common import contract, httpkit, ids
from app_src.receiver_app import main as port_main
from app_src.receiver_app.storage import public_view
from app_src.vault_app import routes_handoff, routes_statement, storage
from app_src.vault_app.appctx import VaultApp
from app_src.vault_app.auth import SESSION_COOKIE

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT_PASS = "test-passphrase-0000000000"
PORT_ENV = {"PORT_PASSPHRASE": PORT_PASS, "PORT_ID": "port-reference-01", "PORT_NAME": "受け口（参照用）"}
TEXT1 = "この法律は、検査のための架空の条文である。"
ORIG = b"dummy-bytes-momo-001"


def http_call(port, method, path, body=None, headers=None):
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


class Receiver(object):
    """本物の参照受け口。"""
    def __init__(self, tmp):
        router, self.app = port_main.build_app(dict(PORT_ENV), os.path.join(tmp, "port"))
        self.server = Server(router, self.app, port_main.STATIC_DIR)
        self.port = self.server.port
        self.cookie = None

    def stop(self):
        self.server.stop()

    def login(self):
        st, o, h = http_call(self.port, "POST", "/face/login", {"passphrase": PORT_PASS})
        assert st == 200, (st, o)
        self.cookie = re.search(r"cip_port_session=([0-9a-f]+)", h.get("Set-Cookie") or "").group(1)

    def make_code(self):
        if not self.cookie:
            self.login()
        st, o, _ = http_call(self.port, "POST", "/face/pairings", headers={"Cookie": "cip_port_session=" + self.cookie})
        assert st == 201, (st, o)
        return o["code"]

    def reply(self, bundle_id, text):
        if not self.cookie:
            self.login()
        att = ids.now_jst()
        st, o, _ = http_call(self.port, "POST", "/face/bundles/%s/replies" % bundle_id,
                             {"human_attestation": True, "text": text, "attested_at": att},
                             {"Cookie": "cip_port_session=" + self.cookie})
        assert st == 201, (st, o)
        return o


class FakePort(object):
    """控えを偽る・返事の形を壊す、小さな偽の受け口。"""
    def __init__(self, bundle_status=201, receipt_fp="0" * 64, replies=None, pair_status=200):
        outer = self
        self.bundle_status, self.receipt_fp, self.replies, self.pair_status = bundle_status, receipt_fp, replies or [], pair_status
        self.seen = []

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, status, obj):
                body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(n)
                outer.seen.append((self.path, self.headers.get("Authorization")))
                if self.path == "/v1/pair":
                    if outer.pair_status != 200:
                        return self._send(outer.pair_status, {"error": "unauthorized", "detail": "x"})
                    return self._send(200, {"person_ref": "pr-fake-0001", "token": "fake-token-0000", "port_id": "port-fake", "port_name": "にせの受け口"})
                if self.path == "/v1/bundles":
                    b = json.loads(raw.decode("utf-8"))
                    if outer.bundle_status != 201:
                        return self._send(outer.bundle_status, {"error": "unauthorized", "detail": "x"})
                    return self._send(201, {"receipt_version": "cip-receipt-v1", "receipt_id": "rc-fake", "port_id": "port-fake",
                                            "port_name": "にせの受け口", "bundle_id": b["bundle_id"],
                                            "bundle_fingerprint": outer.receipt_fp, "item_count": b["item_count"],
                                            "received_at": "2026-11-07T10:15:03+09:00"})
                self._send(404, {"error": "not_found"})

            def do_GET(self):
                outer.seen.append((self.path, self.headers.get("Authorization")))
                if self.path.startswith("/v1/replies"):
                    return self._send(200, {"replies": outer.replies})
                self._send(404, {"error": "not_found"})

        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.port = self.httpd.server_address[1]
        self.th = threading.Thread(target=lambda: self.httpd.serve_forever(poll_interval=0.02), daemon=True)
        self.th.start()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.th.join(5)


def write_corpus(dir_path):
    os.makedirs(dir_path, exist_ok=True)
    with open(os.path.join(dir_path, "a.json"), "w", encoding="utf-8") as f:
        json.dump({"id": "test-law-1", "law_name": "テスト法", "article": "第一条", "text_verbatim": TEXT1, "source_name": "テストの出典",
                   "retrieved_on": "0000-00-00", "retrieved_by": "検査の役", "set_version": "statutes-test", "verified_by_person": True}, f, ensure_ascii=False)
    return dir_path


class Vault(object):
    def __init__(self, tmp, port_base):
        self.clock = time.time
        self.law_dir = write_corpus(os.path.join(tmp, "law"))
        cfg = {"vault_dir": os.path.join(tmp, "vault"), "port": 0, "passphrase": None, "api_key": None, "demo_mode": False,
               "port_base_url": "http://127.0.0.1:%d" % port_base if port_base else "", "claude_model": "test-model",
               "app_root": APP_ROOT, "law_dir": self.law_dir}
        self.vault = storage.open_vault(cfg["vault_dir"])
        self.app = VaultApp(cfg, self.vault, httpkit.SessionStore(clock=self.clock), self.clock)
        router = httpkit.Router()
        router.add_many(routes_statement.ROUTES)
        router.add_many(routes_handoff.ROUTES)
        self.server = Server(router, self.app)
        self.token = self.app.sessions.create()

    def stop(self):
        self.server.stop()

    def call(self, method, path, body=None, login=True):
        h = {"Cookie": "%s=%s" % (SESSION_COOKIE, self.token)} if login else {}
        st, o, _ = http_call(self.server.port, method, path, body, h)
        return st, o

    # ---- 材料
    def make_record(self, name="もも", annotations=("この学期は 休みが 多かった。",), subject=True, derived=True):
        rid = self.vault.add_record(name, "image/png", ORIG + name.encode("utf-8"), "2026-11-06T18:00:00+09:00")
        if derived:
            self.vault.set_derived(rid, "# 通知表（自作のダミー）\n\n- こくご: たのしく とりくんだ\n", {"demo": True})
        if subject:
            self.vault.set_subject(rid, {"author_role": "学校", "written_at": "2026-03-31", "procedure": "学期の記録", "confirmed_by_person": False})
        for a in annotations:
            self.vault.add_annotation(rid, a)
        return rid

    def final_statement(self, grounds=(), statute_ids=("test-law-1",), text="朝の ことを 相談したいです。"):
        st, o = self.call("POST", "/api/statements", {"sections": {"trouble": "朝が つらい", "wish": "遅くしたい", "grounds": list(grounds), "statute_ids": list(statute_ids)}})
        assert st == 201, (st, o)
        sid = o["item_id"]
        st, o = self.call("POST", "/api/statements/%s/finalize" % sid, {"text": text})
        assert st == 200, (st, o)
        return sid


class _Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = self._tmp.name

    def receiver(self):
        r = Receiver(self.tmp)
        self.addCleanup(r.stop)
        return r

    def fake(self, **kw):
        f = FakePort(**kw)
        self.addCleanup(f.stop)
        return f

    def vault(self, port):
        v = Vault(self.tmp, port)
        self.addCleanup(v.stop)
        return v

    def paired(self, rx=None, fake=None):
        """(vault, 受け口) - つなぎ済み。"""
        target = rx or fake
        v = self.vault(target.port)
        code = rx.make_code() if rx else "AAAAAAAAAAAA"
        st, o = v.call("POST", "/api/pair", {"pairing_code": code})
        self.assertEqual(st, 200, o)
        return v


def handoff_dirs(v):
    base = os.path.join(v.vault.root, "handoffs")
    return os.listdir(base) if os.path.isdir(base) else []


# =====================================================================
# N_ 陰性対照（先）
# =====================================================================

class N_BeforeSending(_Base):
    def test_login_required(self):
        v = self.vault(None)
        for method, path in [("POST", "/api/pair"), ("POST", "/api/handoffs"), ("POST", "/api/handoffs/preview"),
                             ("GET", "/api/handoffs"), ("POST", "/api/replies/refresh")]:
            st, _ = v.call(method, path, {}, login=False)
            self.assertEqual(st, 401, path)

    def test_not_final_statement_400_and_nothing_sent(self):
        rx = self.receiver()
        v = self.paired(rx)
        st, o = v.call("POST", "/api/statements", {"sections": {"trouble": "a", "wish": "b", "grounds": [], "statute_ids": []}})
        sid = o["item_id"]
        for path in ("/api/handoffs", "/api/handoffs/preview"):
            st, o = v.call("POST", path, {"statement_id": sid})
            self.assertEqual((st, o["error"]), (400, "statement_not_final"), path)
        self.assertEqual(v.vault.list_handoffs(), [])
        self.assertEqual(rx.app.storage.list_bundle_meta(), [])

    def test_unknown_statement_404(self):
        v = self.paired(self.receiver())
        st, _ = v.call("POST", "/api/handoffs", {"statement_id": "st-nothing"})
        self.assertEqual(st, 404)
        st, _ = v.call("POST", "/api/handoffs", {"statement_id": 5})
        self.assertEqual(st, 400)

    def test_not_paired_400(self):
        rx = self.receiver()
        v = self.vault(rx.port)
        sid = v.final_statement()
        st, o = v.call("POST", "/api/handoffs", {"statement_id": sid})
        self.assertEqual((st, o["error"]), (400, "not_paired"))
        st, o = v.call("POST", "/api/replies/refresh", {})
        self.assertEqual((st, o["error"]), (400, "not_paired"))

    def test_bad_parts_selection(self):
        v = self.paired(self.receiver())
        rid = v.make_record()
        sid = v.final_statement()
        bad = [
            [{"record_id": rid, "parts": []}],
            [{"record_id": rid, "parts": ["everything"]}],
            [{"record_id": rid, "parts": "original"}],
            [{"record_id": rid, "parts": [5]}],
            [{"record_id": rid}],
            [{"parts": ["original"]}],
            [{"record_id": rid, "parts": ["original"]}, {"record_id": rid, "parts": ["derived"]}],
            "all",
        ]
        for recs in bad:
            st, o = v.call("POST", "/api/handoffs", {"statement_id": sid, "records": recs})
            self.assertEqual(st, 400, repr(recs))
        st, _ = v.call("POST", "/api/handoffs", {"statement_id": sid, "records": [{"record_id": "rec-nothing", "parts": ["original"]}]})
        self.assertEqual(st, 404)
        self.assertEqual(v.vault.list_handoffs(), [])

    def test_missing_part_400(self):
        v = self.paired(self.receiver())
        rid = v.make_record(annotations=(), subject=False, derived=False)
        sid = v.final_statement()
        for p in ("derived", "subject_fields", "annotations"):
            st, o = v.call("POST", "/api/handoffs", {"statement_id": sid, "records": [{"record_id": rid, "parts": [p]}]})
            self.assertEqual((st, o["error"]), (400, "part_missing"), p)

    def test_changed_original_409(self):
        v = self.paired(self.receiver())
        rid = v.make_record()
        sid = v.final_statement()
        d = os.path.join(v.vault.root, "records", rid)
        p = os.path.join(d, [f for f in os.listdir(d) if f.startswith("original.") and f != "original.json"][0])
        with open(p, "r+b") as f:
            f.write(b"X")
        st, o = v.call("POST", "/api/handoffs", {"statement_id": sid, "records": [{"record_id": rid, "parts": ["original"]}]})
        self.assertEqual((st, o["error"]), (409, "original_changed"))
        self.assertEqual(v.vault.list_handoffs(), [])

    def test_statute_removed_from_corpus_after_finalize_400(self):
        v = self.paired(self.receiver())
        sid = v.final_statement()
        os.unlink(os.path.join(v.law_dir, "a.json"))
        st, o = v.call("POST", "/api/handoffs", {"statement_id": sid})
        self.assertEqual((st, o["error"]), (400, "statute_unknown"))

    def test_bad_name_and_ids(self):
        v = self.paired(self.receiver())
        sid = v.final_statement()
        for extra in ({"display_name": "あ" * 61}, {"display_name": 5}, {"bundle_id": "../x"}, {"bundle_id": 5}, {"created_at": "昨日"},
                      {"created_at": "2026-11-07T10:15:00"}):
            st, _ = v.call("POST", "/api/handoffs/preview", dict(extra, statement_id=sid))
            self.assertEqual(st, 400, repr(extra))

    def test_expected_fingerprint_mismatch_409_and_nothing_sent(self):
        rx = self.receiver()
        v = self.paired(rx)
        sid = v.final_statement()
        st, o = v.call("POST", "/api/handoffs", {"statement_id": sid, "expected_fingerprint": "f" * 64})
        self.assertEqual((st, o["error"]), (409, "preview_changed"))
        self.assertEqual(rx.app.storage.list_bundle_meta(), [])
        self.assertEqual(v.vault.list_handoffs(), [])

    def test_too_many_records_400(self):
        v = self.paired(self.receiver())
        sid = v.final_statement()
        recs = [{"record_id": "r%d" % i, "parts": ["original"]} for i in range(50)]
        st, o = v.call("POST", "/api/handoffs", {"statement_id": sid, "records": recs})
        self.assertEqual((st, o["error"]), (400, "too_many"))


class N_PairingAndSend(_Base):
    def test_wrong_pairing_code_401_and_nothing_saved(self):
        rx = self.receiver()
        v = self.vault(rx.port)
        st, o = v.call("POST", "/api/pair", {"pairing_code": "ZZZZZZZZZZZZ"})
        self.assertEqual((st, o["error"]), (401, "pair_failed"))
        self.assertIsNone(v.vault.get_pairing())
        self.assertIsNone(v.vault.get_pairing_secret())
        for bad in ({}, {"pairing_code": ""}, {"pairing_code": "  "}, {"pairing_code": 5}, {"pairing_code": "x" * 129}):
            st, _ = v.call("POST", "/api/pair", bad)
            self.assertEqual(st, 400, repr(bad))

    def test_used_pairing_code_cannot_pair_twice(self):
        rx = self.receiver()
        code = rx.make_code()
        v1 = self.vault(rx.port)
        st, _ = v1.call("POST", "/api/pair", {"pairing_code": code})
        self.assertEqual(st, 200)
        st, o = v1.call("POST", "/api/pair", {"pairing_code": code})
        self.assertEqual((st, o["error"]), (401, "pair_failed"))

    def test_receiver_down_502_and_no_handoff_saved(self):
        rx = self.receiver()
        v = self.paired(rx)
        sid = v.final_statement()
        rx.stop()
        before = len(v.vault.list_handoffs())
        st, o = v.call("POST", "/api/handoffs", {"statement_id": sid})
        self.assertEqual((st, o["error"]), (502, "handoff_failed"))
        self.assertEqual(o["detail"], "わたせませんでした。器の中身は そのままです。")
        self.assertEqual(len(v.vault.list_handoffs()), before)
        self.assertEqual(handoff_dirs(v), [])
        self.assertEqual(v.vault.counts()["handoffs"], 0)
        st, o = v.call("POST", "/api/replies/refresh", {})
        self.assertEqual((st, o["error"]), (502, "replies_failed"))

    def test_receiver_rejects_502_and_nothing_saved(self):
        f = self.fake(bundle_status=401)
        v = self.paired(fake=f)
        sid = v.final_statement()
        st, o = v.call("POST", "/api/handoffs", {"statement_id": sid})
        self.assertEqual((st, o["error"]), (502, "handoff_failed"))
        self.assertEqual(v.vault.list_handoffs(), [])

    def test_forged_receipt_fingerprint_is_unconfirmed(self):
        f = self.fake(receipt_fp="0" * 64)
        v = self.paired(fake=f)
        sid = v.final_statement()
        st, o = v.call("POST", "/api/handoffs", {"statement_id": sid})
        self.assertEqual(st, 201)
        self.assertEqual(o["receipt"]["status"], "unconfirmed")
        self.assertNotEqual(o["receipt"]["bundle_fingerprint"], o["fingerprint"])
        rows = v.vault.list_handoffs()
        self.assertEqual((len(rows), rows[0]["receipt"]["status"]), (1, "unconfirmed"))      # 控えは残す
        st, lst = v.call("GET", "/api/handoffs")
        self.assertEqual(lst["handoffs"][0]["receipt"]["status"], "unconfirmed")

    def test_receipt_for_another_bundle_is_unconfirmed(self):
        f = self.fake(receipt_fp=None)       # 指紋が空 = 比べて合わない
        v = self.paired(fake=f)
        sid = v.final_statement()
        st, o = v.call("POST", "/api/handoffs", {"statement_id": sid})
        self.assertEqual((st, o["receipt"]["status"]), (201, "unconfirmed"))

    def test_malformed_replies_dropped_and_unattested_kept_as_unknown(self):
        good = {"reply_version": "cip-reply-v1", "reply_id": "rp-good", "port_id": "port-fake", "port_name": "にせの受け口",
                "in_reply_to": "bd-x", "text": "読みました。", "written_at": "2026-11-07T11:00:00+09:00",
                "author": {"role": "mentor", "human_attestation": True, "attested_at": "2026-11-07T11:00:00+09:00"}}
        no_att = json.loads(json.dumps(good))
        no_att["reply_id"] = "rp-noatt"
        del no_att["author"]["human_attestation"]
        string_att = json.loads(json.dumps(good))
        string_att["reply_id"] = "rp-strtrue"
        string_att["author"]["human_attestation"] = "true"
        bad_id = json.loads(json.dumps(good))
        bad_id["reply_id"] = "../x"
        wrong_ver = dict(good, reply_id="rp-ver", reply_version="cip-reply-v9")
        no_text = dict(good, reply_id="rp-notext")
        del no_text["text"]
        f = self.fake(replies=[no_att, string_att, bad_id, wrong_ver, no_text, "string", 5, good])
        v = self.paired(fake=f)
        st, o = v.call("POST", "/api/replies/refresh", {})
        # 読めない物（id の字が使えない・本文が無い・辞書でない）だけ捨てる。
        # 人の印が無い／字の "true" の返事は**捨てずに残す**＝画面の札は「不明」（取り決め＝黙って捨てると本人に見えない）。
        self.assertEqual((st, o), (200, {"new": 4}))
        kept = {r["reply_id"]: r for r in v.vault.list_replies()}
        self.assertEqual(sorted(kept), ["rp-good", "rp-noatt", "rp-strtrue", "rp-ver"])
        self.assertEqual(contract.reply_author_label(kept["rp-good"]), "メンター（人）")
        self.assertEqual(contract.reply_author_label(kept["rp-noatt"]), "不明")
        self.assertEqual(contract.reply_author_label(kept["rp-strtrue"]), "不明")


# =====================================================================
# T_ 本物
# =====================================================================

class T_Handoff(_Base):
    def test_pair_saves_name_and_secret_but_never_shows_token(self):
        rx = self.receiver()
        v = self.vault(rx.port)
        st, o = v.call("POST", "/api/pair", {"pairing_code": rx.make_code()})
        self.assertEqual((st, o), (200, {"port_id": "port-reference-01", "port_name": "受け口（参照用）"}))
        p = v.vault.get_pairing()
        self.assertEqual((p["port_id"], p["port_name"]), ("port-reference-01", "受け口（参照用）"))
        self.assertTrue(p["person_ref"] and p["paired_at"])
        tok = v.vault.get_pairing_secret()["token"]
        self.assertTrue(tok)
        # token は秘密の置き場の外には書かれない
        for base, _d, files in os.walk(v.vault.root):
            for fn in files:
                if fn == storage.SECRET_NAME:
                    continue
                with open(os.path.join(base, fn), "rb") as fh:
                    self.assertNotIn(tok.encode("ascii"), fh.read(), fn)

    def test_full_round_trip(self):
        rx = self.receiver()
        v = self.paired(rx)
        rid = v.make_record(annotations=("この学期は 休みが 多かった。", "二つ目の 注記"))
        rid2 = v.make_record("りんご")
        sid = v.final_statement(grounds=[rid, rid2])
        spec = {"statement_id": sid, "display_name": "もも", "records": [{"record_id": rid, "parts": ["derived", "subject_fields"]}]}
        st, pv = v.call("POST", "/api/handoffs/preview", spec)
        self.assertEqual(st, 200)
        self.assertRegex(pv["fingerprint"], r"^[0-9a-f]{64}$")
        self.assertEqual(pv["recipient"], {"port_id": "port-reference-01", "port_name": "受け口（参照用）"})
        self.assertEqual([i["kind"] for i in pv["items"]], ["statement", "record"])
        self.assertEqual(pv["items"][1]["parts"], ["写し", "主語の欄"])
        self.assertEqual(v.vault.list_handoffs(), [])           # 見るだけでは何も送らない・何も残さない
        self.assertEqual(rx.app.storage.list_bundle_meta(), [])
        # わたす（たしかめた束と同じ id・時刻・指紋で）
        st, o = v.call("POST", "/api/handoffs", dict(spec, bundle_id=pv["bundle_id"], created_at=pv["created_at"], expected_fingerprint=pv["fingerprint"]))
        self.assertEqual(st, 201, o)
        self.assertEqual(o["fingerprint"], pv["fingerprint"])
        self.assertEqual(o["bundle_id"], pv["bundle_id"])
        self.assertEqual(o["receipt"]["status"], "confirmed")
        self.assertEqual(o["receipt"]["bundle_fingerprint"], o["fingerprint"])
        # 受け口が自分で計算した指紋と同じ
        meta = rx.app.storage.find_bundle(o["bundle_id"])
        self.assertEqual(meta["fingerprint"], o["fingerprint"])
        got = public_view(rx.app.storage.load_bundle(o["bundle_id"]))
        self.assertEqual(contract.fingerprint(got), o["fingerprint"])
        # 選んだ parts だけ
        rec = [i for i in got["items"] if i["kind"] == "record"]
        self.assertEqual(len(rec), 1)
        self.assertEqual(sorted(rec[0]["parts"]), ["derived", "subject_fields"])
        self.assertNotIn("annotations", rec[0]["parts"])
        self.assertNotIn("original", rec[0]["parts"])
        self.assertEqual(rec[0]["parts"]["derived"]["label"], contract.DERIVED_LABEL)
        self.assertNotIn("bytes_base64", json.dumps(got))
        self.assertNotIn("休みが 多かった", json.dumps(got, ensure_ascii=False))
        self.assertNotIn("りんご", json.dumps(got, ensure_ascii=False))                # 選ばなかった記録は入らない
        self.assertEqual(got["sender"]["display_name"], "もも")
        stm = got["items"][0]
        self.assertEqual((stm["kind"], stm["author"], stm["text"]), ("statement", "person", "朝の ことを 相談したいです。"))
        self.assertEqual(stm["sections"]["grounds"], [rid])                         # 同じ束に在る記録だけ
        self.assertEqual(stm["sections"]["statutes"][0]["text_verbatim"], TEXT1)
        self.assertEqual(sorted(stm["sections"]["statutes"][0]), sorted(contract.STATUTE_FIELDS))
        # 器の側の控え
        rows = v.vault.list_handoffs()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["receipt"]["status"], "confirmed")
        self.assertEqual(rows[0]["bundle"], got)             # 送った束の写し = 受け口が持つ束
        self.assertEqual(v.vault.counts()["handoffs"], 1)
        # 返事 -> 読み直す
        rx.reply(o["bundle_id"], "読みました。\n始まりの時間は 一緒に 考えましょう。")
        st, r = v.call("POST", "/api/replies/refresh", {})
        self.assertEqual((st, r), (200, {"new": 1}))
        st, r = v.call("POST", "/api/replies/refresh", {})
        self.assertEqual((st, r), (200, {"new": 0}))
        reps = v.vault.list_replies()
        self.assertEqual(len(reps), 1)
        self.assertEqual(contract.reply_author_label(reps[0]), "メンター（人）")
        self.assertEqual(reps[0]["in_reply_to"], o["bundle_id"])
        self.assertEqual(reps[0]["disposition"], "unread")
        self.assertEqual(reps[0]["text"], "読みました。\n始まりの時間は 一緒に 考えましょう。")
        self.assertEqual(v.vault.counts()["replies"], 1)

    def test_refresh_does_not_undo_what_the_person_decided(self):
        rx = self.receiver()
        v = self.paired(rx)
        sid = v.final_statement()
        st, o = v.call("POST", "/api/handoffs", {"statement_id": sid})
        rx.reply(o["bundle_id"], "一つ目")
        v.call("POST", "/api/replies/refresh", {})
        rp = v.vault.list_replies()[0]
        v.vault.set_reply_disposition(rp["reply_id"], "discarded")
        st, r = v.call("POST", "/api/replies/refresh", {})
        self.assertEqual(r, {"new": 0})
        self.assertEqual(v.vault.list_replies()[0]["disposition"], "discarded")

    def test_original_part_is_carried_with_matching_sha_and_stripped_in_listing(self):
        rx = self.receiver()
        v = self.paired(rx)
        rid = v.make_record()
        sid = v.final_statement(grounds=[rid])
        st, o = v.call("POST", "/api/handoffs", {"statement_id": sid, "records": [{"record_id": rid, "parts": ["annotations", "original", "derived", "subject_fields"]}]})
        self.assertEqual((st, o["receipt"]["status"]), (201, "confirmed"))
        got = public_view(rx.app.storage.load_bundle(o["bundle_id"]))
        part = [i for i in got["items"] if i["kind"] == "record"][0]["parts"]
        self.assertEqual(sorted(part), ["annotations", "derived", "original", "subject_fields"])
        raw, media = v.vault.read_original(rid)
        self.assertEqual(base64.b64decode(part["original"]["bytes_base64"]), raw)
        self.assertEqual(part["original"]["sha256"], contract.sha256_hex(raw))
        self.assertEqual(part["original"]["media_type"], media)
        self.assertEqual(part["annotations"][0]["author"], "person")
        self.assertEqual(part["subject_fields"]["confirmed_by_person"], False)           # 未確認のまま渡す
        st, lst = v.call("GET", "/api/handoffs")
        self.assertEqual(len(lst["handoffs"]), 1)
        text = json.dumps(lst["handoffs"], ensure_ascii=False)
        self.assertNotIn("bytes_base64", text)
        self.assertIn(part["original"]["sha256"], text)
        # 器の保存の中の束には原本が残る（一覧で落としただけ）
        self.assertIn("bytes_base64", json.dumps(v.vault.list_handoffs()[0]["bundle"]))

    def test_statement_only_bundle(self):
        rx = self.receiver()
        v = self.paired(rx)
        sid = v.final_statement(statute_ids=())
        st, o = v.call("POST", "/api/handoffs", {"statement_id": sid})
        self.assertEqual((st, o["receipt"]["status"]), (201, "confirmed"))
        got = public_view(rx.app.storage.load_bundle(o["bundle_id"]))
        self.assertEqual(got["item_count"], 1)
        self.assertNotIn("statutes", got["items"][0]["sections"])
        self.assertEqual(got["sender"]["display_name"], "")

    def test_same_input_without_echo_makes_new_bundle_each_time(self):
        rx = self.receiver()
        v = self.paired(rx)
        sid = v.final_statement()
        a = v.call("POST", "/api/handoffs", {"statement_id": sid})[1]
        b = v.call("POST", "/api/handoffs", {"statement_id": sid})[1]
        self.assertNotEqual(a["bundle_id"], b["bundle_id"])
        self.assertEqual(len(v.vault.list_handoffs()), 2)

    def test_bundle_id_already_used_is_refused(self):
        rx = self.receiver()
        v = self.paired(rx)
        sid = v.final_statement()
        a = v.call("POST", "/api/handoffs", {"statement_id": sid})[1]
        st, o = v.call("POST", "/api/handoffs", {"statement_id": sid, "bundle_id": a["bundle_id"]})
        self.assertEqual(st, 400)
        self.assertEqual(len(v.vault.list_handoffs()), 1)

    def test_bearer_token_is_sent_only_to_the_four_paths(self):
        f = self.fake(receipt_fp=None)
        v = self.paired(fake=f)
        sid = v.final_statement()
        v.call("POST", "/api/handoffs", {"statement_id": sid})
        v.call("POST", "/api/replies/refresh", {})
        paths = sorted(set(p.split("?")[0] for p, _a in f.seen))
        self.assertEqual(paths, ["/v1/bundles", "/v1/pair", "/v1/replies"])
        auth = dict(f.seen)
        self.assertIsNone(f.seen[0][1])                                 # pair には token が無い
        self.assertEqual(auth["/v1/bundles"], "Bearer fake-token-0000")


if __name__ == "__main__":
    unittest.main()
