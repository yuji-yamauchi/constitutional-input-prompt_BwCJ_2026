# -*- coding: utf-8 -*-
"""tests/test_receiver_api.py - 参照用の受け口（取り決めの口 4 本 + 受け口の面の操作）の検査。

回し方: app_src の親の場所で  python3 -B -m unittest app_src.tests.test_receiver_api -v
順序: クラス名 N_（陰性対照・先）-> T_（本物・後）。unittest は名前順に回すので N_ が先。
ここ（テスト）だけは urllib を使う（受け口のコードには無い）。
"""
import copy
import hashlib
import http.client
import json
import os
import re
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

from app_src.common import contract, httpkit, ids, vector
from app_src.receiver_app import main as port_main

# ダミーの合言葉（環境の差し替えで渡す形）
DUMMY_PASS = "test-passphrase-0000000000"
V1_PERSON = vector.vector_v1()["sender"]["person_ref"]


class FakeClock(object):
    def __init__(self):
        import time
        self.t = time.time()

    def __call__(self):
        return self.t

    def advance(self, sec):
        self.t += sec


def base_env(**over):
    env = {"PORT_PASSPHRASE": DUMMY_PASS, "PORT_ID": "port-reference-01", "PORT_NAME": "受け口（参照用）"}
    env.update(over)
    for k in [k for k, v in env.items() if v is None]:
        del env[k]
    return env


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def resign(b):
    """束の中身を変えたあとに、指紋だけ正しく付け直す（形の誤りだけを検査したいとき）。"""
    b = copy.deepcopy(b)
    b["fingerprint"] = contract.fingerprint(b)
    return b


# ---- ログの走査 ----
def scan_log(text, forbidden):
    """text の中に forbidden の字が 1 つでも在れば、当たった字の一覧を返す。"""
    return [f for f in forbidden if f and f in text]


class Base(unittest.TestCase):
    env_extra = {}
    autostart = True

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name
        self.clock = FakeClock()
        self.srv = None
        if self.autostart:
            self.start(base_env(**self.env_extra))

    def tearDown(self):
        self.stop()
        self._tmp.cleanup()

    def start(self, env, person_ref=None):
        self.stop()
        router, app = port_main.build_app(env, self.dir, self.clock)
        if person_ref is not None:
            app.person_ref_factory = lambda: person_ref
        self.app = app
        self.srv = httpkit.make_server(0, router, port_main.STATIC_DIR, app)
        self.port = self.srv.server_address[1]
        self.th = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.th.start()

    def stop(self):
        if self.srv is not None:
            self.srv.shutdown()
            self.srv.server_close()
            self.th.join(5)
            self.srv = None

    # ---- 呼び出し ----
    def call(self, method, path, body=None, bearer=None, cookie=None, raw=None, ctype="application/json"):
        url = "http://127.0.0.1:%d%s" % (self.port, path)
        data = raw if raw is not None else (None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8"))
        req = urllib.request.Request(url, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", ctype)
        if bearer:
            req.add_header("Authorization", "Bearer " + bearer)
        if cookie:
            req.add_header("Cookie", "cip_port_session=" + cookie)
        try:
            r = urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as e:
            r = e
        text = r.read().decode("utf-8")
        try:
            obj = json.loads(text) if text else None
        except ValueError:
            obj = text
        return r.status, obj, r.headers

    def login(self, pw=DUMMY_PASS):
        st, obj, h = self.call("POST", "/face/login", {"passphrase": pw})
        if st != 200:
            return None
        m = re.search(r"cip_port_session=([0-9a-f]+)", h.get("Set-Cookie") or "")
        return m.group(1)

    def make_code(self, cookie):
        st, obj, _ = self.call("POST", "/face/pairings", cookie=cookie)
        self.assertEqual(st, 201)
        return obj["code"]

    def pair(self, cookie, code=None):
        code = code or self.make_code(cookie)
        st, obj, _ = self.call("POST", "/v1/pair", {"pairing_code": code})
        self.assertEqual(st, 200, obj)
        return obj

    def events_text(self):
        with open(os.path.join(self.dir, "events.log"), encoding="utf-8") as f:
            return f.read()


# =====================================================================
# N_ 陰性対照（先に回す）: 通してはいけない物が、ちゃんと落ちること
# =====================================================================

class N_Unconfigured(Base):
    autostart = False

    def check_off(self, env):
        self.start(env)
        st, obj, _ = self.call("GET", "/face/status")
        self.assertEqual((st, obj), (200, {"configured": False}))
        st, obj, _ = self.call("POST", "/v1/pair", {"pairing_code": "AAAAAAAAAAAA"})
        self.assertEqual((st, obj["error"]), (503, "not_configured"))
        st, obj, _ = self.call("GET", "/v1/bundles", bearer="x")
        self.assertEqual((st, obj["error"]), (503, "not_configured"))
        st, obj, _ = self.call("POST", "/face/login", {"passphrase": DUMMY_PASS})
        self.assertEqual(st, 503)
        st, obj, _ = self.call("GET", "/face/bundles")
        self.assertEqual(st, 503)

    def test_passphrase_missing(self):
        self.check_off(base_env(PORT_PASSPHRASE=None))

    def test_passphrase_empty(self):
        self.check_off(base_env(PORT_PASSPHRASE=""))

    def test_passphrase_short_15(self):
        self.check_off(base_env(PORT_PASSPHRASE="x" * 15))

    def test_port_id_missing(self):
        self.check_off(base_env(PORT_ID=None))

    def test_port_name_missing(self):
        self.check_off(base_env(PORT_NAME=None))

    def test_no_storage_created_when_off(self):
        self.start(base_env(PORT_PASSPHRASE=None))
        self.assertFalse(os.path.exists(os.path.join(self.dir, "bundles")))


class N_Auth(Base):
    def test_face_before_login_401(self):
        for method, path in [("GET", "/face/bundles"), ("GET", "/face/bundles/abc"), ("GET", "/face/pairings"),
                             ("POST", "/face/pairings"), ("POST", "/face/bundles/abc/replies")]:
            st, obj, _ = self.call(method, path, {} if method == "POST" else None)
            self.assertEqual(st, 401, path)

    def test_wrong_passphrase_401_single_message_no_cookie(self):
        st1, o1, h1 = self.call("POST", "/face/login", {"passphrase": DUMMY_PASS + "x"})
        st2, o2, h2 = self.call("POST", "/face/login", {"passphrase": "short"})
        self.assertEqual((st1, st2), (401, 401))
        self.assertEqual(o1, o2)                      # 失敗の字は 1 種
        self.assertIsNone(h1.get("Set-Cookie"))

    def test_five_wrong_then_locked_even_with_right(self):
        for _ in range(5):
            st, _, _ = self.call("POST", "/face/login", {"passphrase": "wrong-wrong-wrong-1"})
            self.assertEqual(st, 401)
        st, obj, h = self.call("POST", "/face/login", {"passphrase": DUMMY_PASS})
        self.assertEqual((st, obj["error"]), (423, "locked"))
        self.assertIsNone(h.get("Set-Cookie"))

    def test_cookie_cannot_pass_v1(self):
        cookie = self.login()
        self.assertTrue(cookie)
        for method, path in [("GET", "/v1/bundles"), ("GET", "/v1/replies"), ("POST", "/v1/bundles")]:
            st, obj, _ = self.call(method, path, {} if method == "POST" else None, cookie=cookie)
            self.assertEqual(st, 401, path)

    def test_bearer_cannot_pass_face(self):
        cookie = self.login()
        tok = self.pair(cookie)["token"]
        for method, path in [("GET", "/face/bundles"), ("GET", "/face/pairings"), ("POST", "/face/pairings"),
                             ("GET", "/face/bundles/abc"), ("POST", "/face/bundles/abc/replies")]:
            st, obj, _ = self.call(method, path, {} if method == "POST" else None, bearer=tok)
            self.assertEqual(st, 401, path)

    def test_v1_without_or_with_bad_token_401(self):
        for tok in (None, "0" * 64, "garbage"):
            for method, path in [("GET", "/v1/bundles"), ("GET", "/v1/replies"), ("POST", "/v1/bundles")]:
                st, obj, _ = self.call(method, path, {} if method == "POST" else None, bearer=tok)
                self.assertEqual((st, obj["error"]), (401, "unauthorized"), (tok, path))


class N_Pairing(Base):
    def test_wrong_code_401(self):
        st, obj, _ = self.call("POST", "/v1/pair", {"pairing_code": "ZZZZZZZZZZZZ"})
        self.assertEqual((st, obj["error"]), (401, "unauthorized"))

    def test_used_code_401(self):
        cookie = self.login()
        code = self.make_code(cookie)
        self.pair(cookie, code)
        st, obj, _ = self.call("POST", "/v1/pair", {"pairing_code": code})
        self.assertEqual((st, obj["error"]), (401, "unauthorized"))

    def test_expired_code_401(self):
        cookie = self.login()
        code = self.make_code(cookie)
        self.clock.advance(24 * 3600 + 5)
        st, obj, _ = self.call("POST", "/v1/pair", {"pairing_code": code})
        self.assertEqual((st, obj["error"]), (401, "unauthorized"))

    def test_malformed_body_400(self):
        st, obj, _ = self.call("POST", "/v1/pair", raw=b"not json")
        self.assertEqual((st, obj["error"]), (400, "schema_invalid"))
        st, obj, _ = self.call("POST", "/v1/pair", {"pairing_code": 12345})
        self.assertEqual((st, obj["error"]), (400, "schema_invalid"))


class N_Bundle(Base):
    def setUp(self):
        Base.setUp(self)
        self.cookie = self.login()
        info = self.pair(self.cookie)
        self.tok = info["token"]
        self.person = info["person_ref"]

    def good(self, bundle_id="bundle-n-0001"):
        b = vector.vector_v1()
        b["bundle_id"] = bundle_id
        b["sender"]["person_ref"] = self.person
        return resign(b)

    def send(self, b, **kw):
        return self.call("POST", "/v1/bundles", b, bearer=self.tok, **kw)

    def listing(self):
        return self.call("GET", "/v1/bundles", bearer=self.tok)[1]["bundles"]

    def assert_rejected(self, b, status, error):
        st, obj, _ = self.send(b)
        self.assertEqual((st, obj["error"]), (status, error), obj)
        self.assertEqual(self.listing(), [])
        self.assertEqual(os.listdir(os.path.join(self.dir, "bundles")), [])

    def test_forged_fingerprint_400_and_not_saved(self):
        b = self.good()
        b["items"][0]["text"] = b["items"][0]["text"] + "!"     # 指紋はそのまま
        self.assert_rejected(b, 400, "fingerprint_mismatch")

    def test_fake_fingerprint_string_400(self):
        b = self.good()
        b["fingerprint"] = "0" * 64
        self.assert_rejected(b, 400, "fingerprint_mismatch")

    def test_wrong_derived_label_400(self):
        b = self.good()
        b["items"][1]["parts"]["derived"]["label"] = "派生"
        self.assert_rejected(resign(b), 400, "schema_invalid")

    def test_statement_author_not_person_400(self):
        b = self.good()
        b["items"][0]["author"] = "mentor"
        self.assert_rejected(resign(b), 400, "schema_invalid")

    def test_annotation_author_mentor_400(self):
        b = self.good()
        b["items"][1]["parts"]["annotations"][0]["author"] = "mentor"
        self.assert_rejected(resign(b), 400, "schema_invalid")

    def test_51_items_413(self):
        b = self.good()
        b["items"] = [copy.deepcopy(b["items"][0]) for _ in range(51)]
        b["item_count"] = 51
        self.assert_rejected(resign(b), 413, "too_large")   # 取り決め＝上限超えは 413

    def test_item_count_mismatch_400(self):
        b = self.good()
        b["item_count"] = 3
        self.assert_rejected(resign(b), 400, "schema_invalid")

    def test_float_400(self):
        b = self.good()
        b["items"][0]["extra_number"] = 1.5
        st, obj, _ = self.send(b)
        self.assertEqual((st, obj["error"]), (400, "schema_invalid"))
        self.assertEqual(self.listing(), [])

    def test_not_json_400(self):
        st, obj, _ = self.send(None, raw=b"{broken", ctype="application/json")
        self.assertEqual((st, obj["error"]), (400, "schema_invalid"))

    def test_unsupported_version_400(self):
        b = self.good()
        b["bundle_version"] = "cip-bundle-v9"
        st, obj, _ = self.send(resign(b))
        self.assertEqual((st, obj["error"], obj["detail"]), (400, "schema_invalid", "unsupported version"))

    def test_unsafe_bundle_id_400(self):
        for bad in ("../evil", "a/b", ".hidden", "x" * 200, ""):
            b = self.good(bad)
            st, obj, _ = self.send(b)
            self.assertEqual((st, obj["error"]), (400, "schema_invalid"), bad)
        self.assertEqual(os.listdir(os.path.join(self.dir, "bundles")), [])

    def test_same_id_different_fingerprint_409(self):
        b = self.good()
        st, obj, _ = self.send(b)
        self.assertEqual(st, 201)
        b2 = copy.deepcopy(b)
        b2["items"][0]["text"] = "ちがう本文"
        st, obj, _ = self.send(resign(b2))
        self.assertEqual((st, obj["error"]), (409, "duplicate_bundle_id"))
        self.assertEqual(len(self.listing()), 1)

    def test_wrong_person_ref_404(self):
        b = self.good()
        b["sender"]["person_ref"] = "pr-someone-else"
        self.assert_rejected(resign(b), 404, "unknown_person")

    def test_other_persons_token_cannot_send_for_me_404(self):
        other = self.pair(self.cookie)
        b = self.good()                                   # person は最初の人
        st, obj, _ = self.call("POST", "/v1/bundles", b, bearer=other["token"])
        self.assertEqual((st, obj["error"]), (404, "unknown_person"))

    def test_too_large_413_before_reading(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.putrequest("POST", "/v1/bundles")
        conn.putheader("Authorization", "Bearer " + self.tok)
        conn.putheader("Content-Type", "application/json")
        conn.putheader("Content-Length", str(contract.MAX_BUNDLE_BYTES + 1))
        conn.endheaders()                                 # 本文は送らない
        r = conn.getresponse()
        obj = json.loads(r.read().decode("utf-8"))
        conn.close()
        self.assertEqual((r.status, obj["error"]), (413, "too_large"))


class N_Reply(Base):
    def setUp(self):
        Base.setUp(self)
        self.cookie = self.login()
        info = self.pair(self.cookie)
        b = vector.vector_v1()
        b["bundle_id"] = "bundle-r-0001"
        b["sender"]["person_ref"] = info["person_ref"]
        b = resign(b)
        st, _, _ = self.call("POST", "/v1/bundles", b, bearer=info["token"])
        self.assertEqual(st, 201)
        self.tok = info["token"]
        self.path = "/face/bundles/bundle-r-0001/replies"

    def reply(self, **over):
        body = {"text": "読みました。", "human_attestation": True, "attested_at": "2026-11-07T11:00:00+09:00"}
        body.update(over)
        for k in [k for k, v in body.items() if v is KeyError]:
            del body[k]
        return self.call("POST", self.path, body, cookie=self.cookie)

    def assert_no_reply(self):
        self.assertEqual(self.call("GET", "/v1/replies", bearer=self.tok)[1], {"replies": []})

    def test_attestation_missing_400(self):
        st, obj, _ = self.reply(human_attestation=KeyError)
        self.assertEqual(st, 400)
        self.assert_no_reply()

    def test_attestation_false_400(self):
        self.assertEqual(self.reply(human_attestation=False)[0], 400)
        self.assert_no_reply()

    def test_attestation_string_true_400(self):
        self.assertEqual(self.reply(human_attestation="true")[0], 400)
        self.assert_no_reply()

    def test_attestation_one_400(self):
        self.assertEqual(self.reply(human_attestation=1)[0], 400)
        self.assert_no_reply()

    def test_blank_text_400(self):
        for t in ("", "   ", "\n\t \n", None, 5):
            self.assertEqual(self.reply(text=t)[0], 400, repr(t))
        self.assert_no_reply()

    def test_4001_chars_400(self):
        self.assertEqual(self.reply(text="あ" * 4001)[0], 400)
        self.assert_no_reply()

    def test_attested_at_without_offset_400(self):
        self.assertEqual(self.reply(attested_at="2026-11-07T11:00:00")[0], 400)
        self.assertEqual(self.reply(attested_at=KeyError)[0], 400)
        self.assert_no_reply()

    def test_unknown_bundle_404(self):
        st, obj, _ = self.call("POST", "/face/bundles/no-such/replies",
                               {"text": "x", "human_attestation": True, "attested_at": "2026-11-07T11:00:00+09:00"},
                               cookie=self.cookie)
        self.assertEqual(st, 404)

    def test_no_cookie_401(self):
        st, _, _ = self.call("POST", self.path, {"text": "x", "human_attestation": True,
                                                  "attested_at": "2026-11-07T11:00:00+09:00"})
        self.assertEqual(st, 401)


class N_Scanners(Base):
    """検査の道具そのものが、わざと混ぜた物を見つけること（空振りの PASS を数えない）。"""
    autostart = False

    def test_log_scanner_detects_a_deliberate_leak(self):
        self.start(base_env())
        self.app.storage.log_event("login_ok", status=200)
        clean = self.events_text()
        self.assertEqual(scan_log(clean, ["SECRET-VALUE-1"]), [])
        with open(os.path.join(self.dir, "events.log"), "a", encoding="utf-8") as f:
            f.write("2026-11-07T10:00:00+09:00\tleak\tSECRET-VALUE-1\n")      # わざと 1 行 書く
        self.assertEqual(scan_log(self.events_text(), ["SECRET-VALUE-1", "other"]), ["SECRET-VALUE-1"])

    def test_log_event_sanitizes_odd_characters(self):
        self.start(base_env())
        self.app.storage.log_event("k\n2000-01-01 forged", bundle_id="a b\tc\nd")
        lines = self.events_text().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(len(lines[0].split("\t")), 6)

    def test_static_scanner_detects_bad_characters(self):
        bad = ["a" + chr(0x202E) + "b", "a" + chr(0x200B) + "b", chr(0xFEFF) + "x", "a" + chr(0x2028) + "b", "smile " + chr(0x1F600)]
        for s in bad:
            self.assertTrue(static_bad_chars(s), repr(s))
        self.assertEqual(static_bad_chars("ふつうの字 abc 123 ／ （）"), [])


def static_bad_chars(text):
    out = []
    for ch in text:
        c = ord(ch)
        if (0x202A <= c <= 0x202E or 0x2066 <= c <= 0x2069 or 0x200B <= c <= 0x200F or c == 0xFEFF
                or c in (0x2028, 0x2029) or c >= 0x1F000 or 0x2600 <= c <= 0x27BF):
            out.append(hex(c))
    return out


# =====================================================================
# T_ 本物（後に回す）
# =====================================================================

class T_Flow(Base):
    """合言葉を作る -> つなぐ -> V1 の束を送る -> 面で返事 -> 器が取りに行く。"""

    def start_flow(self):
        self.start(base_env(), person_ref=V1_PERSON)       # V1 の sender.person_ref と同じ id を出させる
        self.cookie = self.login()
        self.code = self.make_code(self.cookie)
        # 小文字で打っても通る
        st, info, _ = self.call("POST", "/v1/pair", {"pairing_code": "  " + self.code.lower() + " "})
        self.assertEqual(st, 200, info)
        self.info = info
        self.tok = info["token"]

    def test_full_flow(self):
        self.start_flow()
        info = self.info
        self.assertEqual(info["person_ref"], V1_PERSON)
        self.assertEqual((info["port_id"], info["port_name"]), ("port-reference-01", "受け口（参照用）"))
        self.assertEqual(len(info["token"]), 64)

        v1 = vector.vector_v1()
        st, receipt, _ = self.call("POST", "/v1/bundles", v1, bearer=self.tok)
        self.assertEqual(st, 201, receipt)
        self.assertEqual(contract.validate_receipt(receipt), [])
        self.assertEqual(receipt["bundle_fingerprint"], contract.fingerprint(v1))
        self.assertEqual(receipt["bundle_fingerprint"], vector.EXPECTED_V1_FINGERPRINT)
        self.assertEqual(receipt["item_count"], 2)
        self.assertEqual((receipt["port_id"], receipt["bundle_id"]), ("port-reference-01", v1["bundle_id"]))
        self.assertIsNotNone(ids.parse_iso(receipt["received_at"]))

        # 再送 = 200 で同じ控え
        st, again, _ = self.call("POST", "/v1/bundles", v1, bearer=self.tok)
        self.assertEqual(st, 200)
        self.assertEqual(again["receipt_id"], receipt["receipt_id"])

        st, lst, _ = self.call("GET", "/v1/bundles", bearer=self.tok)
        self.assertEqual(st, 200)
        self.assertEqual(len(lst["bundles"]), 1)
        row = lst["bundles"][0]
        self.assertEqual(row["reply_count"], 0)
        self.assertEqual(row["bundle_fingerprint"], vector.EXPECTED_V1_FINGERPRINT)
        self.assertEqual(row["receipt_id"], receipt["receipt_id"])
        self.assertEqual(set(row), {"bundle_id", "received_at", "bundle_fingerprint", "item_count", "receipt_id", "reply_count"})

        # 面: 一覧と束
        st, fl, _ = self.call("GET", "/face/bundles", cookie=self.cookie)
        self.assertEqual(st, 200)
        frow = fl["bundles"][0]
        self.assertEqual((frow["display_name"], frow["item_count"], frow["reply_count"]), ("もも", 2, 0))
        self.assertEqual(frow["fingerprint"], vector.EXPECTED_V1_FINGERPRINT)
        self.assertFalse(fl["truncated"])
        st, det, _ = self.call("GET", "/face/bundles/" + v1["bundle_id"], cookie=self.cookie)
        self.assertEqual(st, 200)
        self.assertEqual(det["bundle"], v1)                        # 束そのまま（原本の base64 を含む）
        self.assertEqual(det["fingerprint"], vector.EXPECTED_V1_FINGERPRINT)
        self.assertEqual(det["receipt_id"], receipt["receipt_id"])
        self.assertEqual(det["replies"], [])

        # 返事 1 通目
        path = "/face/bundles/%s/replies" % v1["bundle_id"]
        text1 = "  読みました。\n始まりの時間のことは、次に会うときに一緒に考えましょう。\n"
        st, r1, _ = self.call("POST", path, {"text": text1, "human_attestation": True,
                                              "attested_at": "2026-11-07T11:00:00+09:00"}, cookie=self.cookie)
        self.assertEqual(st, 201, r1)
        self.assertEqual(r1["text"], text1)                         # 1 字も削らない
        self.assertIs(r1["author"]["human_attestation"], True)
        self.assertEqual(r1["author"]["role"], "mentor")
        self.assertEqual(r1["author"]["attested_at"], "2026-11-07T11:00:00+09:00")
        self.assertEqual(r1["in_reply_to"], v1["bundle_id"])
        self.assertEqual(contract.validate_reply(r1), [])
        self.assertEqual(contract.reply_author_label(r1), "メンター（人）")
        self.assertTrue(r1["written_at"].endswith("+09:00"))
        self.assertNotIn("_seq", r1)

        st, rep, _ = self.call("GET", "/v1/replies", bearer=self.tok)
        self.assertEqual(st, 200)
        self.assertEqual(len(rep["replies"]), 1)
        self.assertEqual(rep["replies"][0]["reply_id"], r1["reply_id"])
        self.assertEqual(contract.reply_author_label(rep["replies"][0]), "メンター（人）")
        self.assertEqual(contract.validate_reply(rep["replies"][0]), [])

        # since で絞れる（+ を逃がさず送っても通る）
        st, rep, _ = self.call("GET", "/v1/replies?since=2999-01-01T00:00:00+09:00", bearer=self.tok)
        self.assertEqual((st, rep["replies"]), (200, []))
        st, rep, _ = self.call("GET", "/v1/replies?since=2000-01-01T00:00:00%2B09:00", bearer=self.tok)
        self.assertEqual(len(rep["replies"]), 1)
        st, rep, _ = self.call("GET", "/v1/replies?since=" + urllib.request.quote(r1["written_at"]), bearer=self.tok)
        self.assertEqual(len(rep["replies"]), 1)

        # 2 通目で 1 通目が残る
        st, r2, _ = self.call("POST", path, {"text": "二通目です。", "human_attestation": True,
                                              "attested_at": "2026-11-07T11:05:00+09:00"}, cookie=self.cookie)
        self.assertEqual(st, 201)
        st, rep, _ = self.call("GET", "/v1/replies", bearer=self.tok)
        self.assertEqual([r["reply_id"] for r in rep["replies"]], [r2["reply_id"], r1["reply_id"]])
        st, lst, _ = self.call("GET", "/v1/bundles", bearer=self.tok)
        self.assertEqual(lst["bundles"][0]["reply_count"], 2)
        st, det, _ = self.call("GET", "/face/bundles/" + v1["bundle_id"], cookie=self.cookie)
        self.assertEqual([r["text"] for r in det["replies"]], ["二通目です。", text1])
        self.assertEqual(det["replies"][0]["author_label"], "メンター（人）")
        st, fl, _ = self.call("GET", "/face/bundles", cookie=self.cookie)
        self.assertEqual(fl["bundles"][0]["reply_count"], 2)

        # 保存の形
        for sub, name in (("bundles", v1["bundle_id"]), ("receipts", v1["bundle_id"]), ("replies", r1["reply_id"])):
            self.assertTrue(os.path.isfile(os.path.join(self.dir, sub, name + ".json")), sub)
        with open(os.path.join(self.dir, "bundles", v1["bundle_id"] + ".json"), encoding="utf-8") as f:
            stored = json.load(f)
        self.assertEqual(stored["_fingerprint_computed"], vector.EXPECTED_V1_FINGERPRINT)
        self.assertEqual(stored["_person_ref"], V1_PERSON)
        self.assertIn("_received_at", stored)
        self.assertEqual(os.listdir(os.path.join(self.dir, "bundles")), [v1["bundle_id"] + ".json"])   # 一時ファイルが残らない

        # events.log: 試しの字を流したあと、秘密の字が 0（走査の道具は N_Scanners で先に確かめた）
        log = self.events_text()
        self.assertTrue(log.strip())
        v1_text = v1["items"][0]["text"]
        forbidden = [DUMMY_PASS, self.code, self.code.lower(), self.tok, V1_PERSON, "もも", v1_text[:12],
                     "読みました", "二通目", v1["items"][1]["parts"]["derived"]["markdown"][:8],
                     v1["items"][1]["parts"]["original"]["bytes_base64"][:20]]
        self.assertEqual(scan_log(log, forbidden), [])
        kinds = set(l.split("\t")[1] for l in log.splitlines())
        for k in ("login_ok", "pairing_created", "pairing_used", "bundle_received", "bundle_resent", "reply_saved"):
            self.assertIn(k, kinds)
        self.assertIn(vector.EXPECTED_V1_FINGERPRINT, log)

        # pairings: 一覧に値が無い・保存に生の値が無い
        st, pl, _ = self.call("GET", "/face/pairings", cookie=self.cookie)
        self.assertEqual(st, 200)
        self.assertEqual(len(pl["pairings"]), 1)
        self.assertEqual(set(pl["pairings"][0]), {"created_at", "expires_at", "status"})
        self.assertEqual(pl["pairings"][0]["status"], "使った")
        dumped = json.dumps(pl, ensure_ascii=False)
        self.assertNotIn(self.code, dumped)
        self.assertNotIn(self.tok, dumped)
        with open(os.path.join(self.dir, "pairings.json"), encoding="utf-8") as f:
            ptxt = f.read()
        self.assertNotIn(self.code, ptxt)
        self.assertNotIn(self.tok, ptxt)
        self.assertIn(sha(self.code), ptxt)
        self.assertIn(sha(self.tok), ptxt)

    def test_reply_4000_chars_ok_and_exact(self):
        self.start_flow()
        v1 = vector.vector_v1()
        self.call("POST", "/v1/bundles", v1, bearer=self.tok)
        text = ("あ" * 3999) + "\n"
        st, r, _ = self.call("POST", "/face/bundles/%s/replies" % v1["bundle_id"],
                             {"text": text, "human_attestation": True, "attested_at": "2026-11-07T11:00:00+09:00"},
                             cookie=self.cookie)
        self.assertEqual(st, 201)
        self.assertEqual(r["text"], text)

    def test_unknown_bundle_detail_404(self):
        self.start_flow()
        for bid in ("nope", "..%2Fx", "a.b"):
            st, obj, _ = self.call("GET", "/face/bundles/" + bid, cookie=self.cookie)
            self.assertEqual(st, 404, bid)


class T_TwoPeople(Base):
    def test_each_person_sees_only_own(self):
        cookie = self.login()
        a = self.pair(cookie)
        b = self.pair(cookie)
        self.assertNotEqual(a["person_ref"], b["person_ref"])
        self.assertNotEqual(a["token"], b["token"])
        bundle = vector.vector_v1()
        bundle["bundle_id"] = "bundle-a-0001"
        bundle["sender"]["person_ref"] = a["person_ref"]
        bundle = resign(bundle)
        st, _, _ = self.call("POST", "/v1/bundles", bundle, bearer=a["token"])
        self.assertEqual(st, 201)
        st, _, _ = self.call("POST", "/face/bundles/bundle-a-0001/replies",
                             {"text": "あなたへ", "human_attestation": True, "attested_at": "2026-11-07T11:00:00+09:00"},
                             cookie=cookie)
        self.assertEqual(st, 201)
        self.assertEqual(len(self.call("GET", "/v1/bundles", bearer=a["token"])[1]["bundles"]), 1)
        self.assertEqual(len(self.call("GET", "/v1/replies", bearer=a["token"])[1]["replies"]), 1)
        self.assertEqual(self.call("GET", "/v1/bundles", bearer=b["token"])[1], {"bundles": []})
        self.assertEqual(self.call("GET", "/v1/replies", bearer=b["token"])[1], {"replies": []})
        # 係は両方の束を見られる
        self.assertEqual(len(self.call("GET", "/face/bundles", cookie=cookie)[1]["bundles"]), 1)


class T_Session(Base):
    def test_idle_15_minutes_ends_session(self):
        cookie = self.login()
        self.clock.advance(14 * 60)
        self.assertEqual(self.call("GET", "/face/bundles", cookie=cookie)[0], 200)      # 操作で時計が戻る
        self.clock.advance(14 * 60)
        self.assertEqual(self.call("GET", "/face/bundles", cookie=cookie)[0], 200)
        self.clock.advance(15 * 60 + 1)
        self.assertEqual(self.call("GET", "/face/bundles", cookie=cookie)[0], 401)
        st, obj, _ = self.call("GET", "/face/status", cookie=cookie)
        self.assertEqual(obj["logged_in"], False)

    def test_logout_ends_session(self):
        cookie = self.login()
        self.assertEqual(self.call("GET", "/face/status", cookie=cookie)[1]["logged_in"], True)
        st, _, h = self.call("POST", "/face/logout", cookie=cookie)
        self.assertEqual(st, 200)
        self.assertIn("Max-Age=0", h.get("Set-Cookie"))
        self.assertEqual(self.call("GET", "/face/bundles", cookie=cookie)[0], 401)

    def test_lock_lifts_after_5_minutes(self):
        for _ in range(5):
            self.call("POST", "/face/login", {"passphrase": "wrong-wrong-wrong-1"})
        self.assertEqual(self.call("POST", "/face/login", {"passphrase": DUMMY_PASS})[0], 423)
        self.clock.advance(5 * 60 + 1)
        self.assertTrue(self.login())

    def test_success_resets_failure_count(self):
        for _ in range(4):
            self.call("POST", "/face/login", {"passphrase": "wrong-wrong-wrong-1"})
        self.assertTrue(self.login())
        for _ in range(4):
            self.call("POST", "/face/login", {"passphrase": "wrong-wrong-wrong-1"})
        self.assertTrue(self.login())

    def test_cookie_attributes(self):
        st, _, h = self.call("POST", "/face/login", {"passphrase": DUMMY_PASS})
        sc = h.get("Set-Cookie")
        self.assertIn("HttpOnly", sc)
        self.assertIn("SameSite=Strict", sc)

    def test_status_shape(self):
        self.assertEqual(self.call("GET", "/face/status")[1],
                         {"configured": True, "logged_in": False, "port_name": "受け口（参照用）"})


class T_Pairings(Base):
    def test_code_format_and_statuses(self):
        cookie = self.login()
        codes = set()
        for _ in range(5):
            st, obj, _ = self.call("POST", "/face/pairings", cookie=cookie)
            self.assertEqual(st, 201)
            self.assertRegex(obj["code"], r"^[A-HJKMNP-Z2-9]{12}$")
            self.assertIsNotNone(ids.parse_iso(obj["expires_at"]))
            codes.add(obj["code"])
        self.assertEqual(len(codes), 5)
        self.call("POST", "/v1/pair", {"pairing_code": sorted(codes)[0]})
        st, pl, _ = self.call("GET", "/face/pairings", cookie=cookie)
        statuses = [p["status"] for p in pl["pairings"]]
        self.assertEqual(sorted(statuses), sorted(["使った"] + ["まだ 使っていない"] * 4))
        self.clock.advance(24 * 3600 + 10)
        cookie = self.login()                                    # 無操作で切れているので入り直す
        st, pl, _ = self.call("GET", "/face/pairings", cookie=cookie)
        self.assertEqual(sorted(p["status"] for p in pl["pairings"]), sorted(["使った"] + ["期限が 切れた"] * 4))

    def test_list_is_newest_first_and_capped_at_20(self):
        cookie = self.login()
        for _ in range(23):
            self.make_code(cookie)
            self.clock.advance(1)
        st, pl, _ = self.call("GET", "/face/pairings", cookie=cookie)
        self.assertEqual(len(pl["pairings"]), 20)
        created = [p["created_at"] for p in pl["pairings"]]
        self.assertEqual(created, sorted(created, reverse=True))


class T_Persistence(Base):
    def test_restart_keeps_bundles_replies_and_pairings(self):
        self.start(base_env(), person_ref=V1_PERSON)
        cookie = self.login()
        tok = self.pair(cookie)["token"]
        v1 = vector.vector_v1()
        st, receipt, _ = self.call("POST", "/v1/bundles", v1, bearer=tok)
        self.assertEqual(st, 201)
        self.call("POST", "/face/bundles/%s/replies" % v1["bundle_id"],
                  {"text": "のこる", "human_attestation": True, "attested_at": "2026-11-07T11:00:00+09:00"}, cookie=cookie)
        self.start(base_env())                                   # 同じ保存で立て直す
        st, lst, _ = self.call("GET", "/v1/bundles", bearer=tok)
        self.assertEqual(st, 200)
        self.assertEqual(lst["bundles"][0]["reply_count"], 1)
        st, again, _ = self.call("POST", "/v1/bundles", v1, bearer=tok)
        self.assertEqual((st, again["receipt_id"]), (200, receipt["receipt_id"]))


class T_Static(Base):
    FILES = ("index.html", "port.css", "port.js")

    def read(self, name):
        with open(os.path.join(port_main.STATIC_DIR, name), encoding="utf-8") as f:
            return f.read()

    def test_served_without_login(self):
        for path, ctype in (("/", "text/html"), ("/index.html", "text/html"), ("/port.css", "text/css"),
                            ("/port.js", "application/javascript")):
            url = "http://127.0.0.1:%d%s" % (self.port, path)
            r = urllib.request.urlopen(url, timeout=10)
            self.assertEqual(r.status, 200, path)
            self.assertTrue(r.headers["Content-Type"].startswith(ctype), path)
            self.assertIn("script-src 'self'", r.headers["Content-Security-Policy"])

    def test_no_inline_script_style_or_external_loads(self):
        html = self.read("index.html")
        self.assertEqual(re.findall(r"<script(?![^>]*\bsrc=)", html), [])
        self.assertNotIn("<style", html)
        self.assertNotRegex(html, r"\sstyle=")
        self.assertNotRegex(html, r"\son[a-z]+=")
        for name in self.FILES:
            txt = self.read(name)
            self.assertNotRegex(txt, r"https?://", name)
            self.assertNotIn("@import", txt)
        js = self.read("port.js")
        for bad in ("localStorage", "sessionStorage", "indexedDB", "innerHTML", "outerHTML", "document.write", "eval(", "insertAdjacentHTML"):
            self.assertNotIn(bad, js, bad)

    def test_no_hidden_or_bad_characters_and_no_banned_words(self):
        for name in self.FILES:
            txt = self.read(name)
            self.assertEqual(static_bad_chars(txt), [], name)
            for w in ("スキルアップ", "帰属的自己", "向上"):
                self.assertNotIn(w, txt, (name, w))

    def test_index_has_no_personal_text_before_login(self):
        html = self.read("index.html")
        for s in ("もも", "通知表", "読みました"):
            self.assertNotIn(s, html)

    def test_theme_tokens_present(self):
        css = self.read("port.css")
        for tok, val in (("--ivory", "#F7F3EA"), ("--brown", "#5A4634"), ("--brown-soft", "#786A59"), ("--mint-deep", "#51764A"),
                         ("--orange-pale", "#FDF3E3"), ("--line", "#E8E0D0")):
            self.assertIn("%s: %s;" % (tok, val), css)
        self.assertEqual(len(re.findall(r"^\s*--[a-z-]+:\s*#[0-9A-Fa-f]{6};", css, re.M)), 13)

    def test_receiver_code_has_no_network_or_model_imports(self):
        here = os.path.dirname(port_main.__file__)
        for name in sorted(os.listdir(here)):
            if not name.endswith(".py"):
                continue
            with open(os.path.join(here, name), encoding="utf-8") as f:
                src = f.read()
            for bad in ("urllib", "http.client", "socket", "vault_app", "claude", "requests"):
                self.assertNotIn(bad, src.lower(), (name, bad))


if __name__ == "__main__":
    unittest.main()
