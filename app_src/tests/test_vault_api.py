# -*- coding: utf-8 -*-
"""vault_app の口（入口・B・持ち出し・全削除）と画面の字の検査。標準ライブラリだけ。
N_＝陰性対照（先）／T_＝本物。保存は tempfile の中だけ。"""
import base64
import http.client
import json
import os
import re
import tempfile
import threading
import unittest
import zipfile

from app_src.common import httpkit, words
from app_src.vault_app import main as vmain
from app_src.vault_app import storage

PASS = "test-passphrase-0000000000"
DUMMY_KEY = "dummy-api-key-not-real-0000"
STATIC = vmain.STATIC_DIR
NOTE_KAKO = "過去のことを話す義務はありません"


class FakeClock(object):
    def __init__(self, t=1800000000.0):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, sec):
        self.t += sec


class FakeClaude(object):
    """Claude の代わり（ネットワークへ出ない）。"""
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    def read_image(self, record_id):
        self.calls.append(record_id)
        if self.fail:
            raise RuntimeError("down")
        return {"markdown": "# もも\n\nりんごの 本文", "meta": {"model": "dummy-model", "demo": False}}


class Srv(object):
    """1 つの器を立てて、http.client で叩く。"""
    def __init__(self, env, clock=None):
        self.tmp = tempfile.TemporaryDirectory()
        self.clock = clock or FakeClock()
        self.vault_dir = os.path.join(self.tmp.name, "vault")
        self.router, self.app = vmain.build_app(env, vault_dir=self.vault_dir, clock=self.clock, wire=False)
        self.httpd = httpkit.make_server(0, self.router, vmain.STATIC_DIR, self.app)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.cookie = None

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.tmp.cleanup()

    def call(self, method, path, body=None, raw=None, cookie=True, ctype="application/json"):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=20)
        headers = {}
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = ctype
        if raw is not None:
            data = raw
        if cookie and self.cookie:
            headers["Cookie"] = self.cookie
        conn.request(method, path, body=data, headers=headers)
        r = conn.getresponse()
        payload = r.read()
        hdrs = r.getheaders()
        conn.close()
        j = None
        if payload and "json" in (r.getheader("Content-Type") or ""):
            j = json.loads(payload.decode("utf-8"))
        return r.status, j, payload, hdrs

    def login(self):
        st, j, payload, hdrs = self.call("POST", "/api/login", {"passphrase": PASS}, cookie=False)
        assert st == 204, st
        for k, v in hdrs:
            if k.lower() == "set-cookie":
                self.cookie = v.split(";")[0]
        assert self.cookie
        return self.cookie


def env_ok(**extra):
    e = {"VAULT_PASSPHRASE": PASS}
    e.update(extra)
    return e


def b64(data):
    return base64.b64encode(data).decode("ascii")


class _Base(unittest.TestCase):
    ENV = None

    def make(self, env=None, clock=None):
        s = Srv(env if env is not None else env_ok(), clock)
        self.addCleanup(s.close)
        return s


# ---------------------------------------------------------------- 字の走査

EXTRA_FORBIDDEN = ("診断します", "判定", "スコア", "レベル", "順位", "上達", "成長", "向上",
                   "スキルアップ", "帰属的自己", "続きをどうぞ", "未読")


def forbidden_hits(text):
    hits = [h[1] for h in words.scan(text)]
    for w in EXTRA_FORBIDDEN:
        if w in text:
            hits.append(w)
    return hits


def _read(name):
    with open(os.path.join(STATIC, name), "rb") as f:
        return f.read().decode("utf-8")


# ================================================================ N（陰性対照・入口・境）

class N_Words(unittest.TestCase):
    def test_a_detector_reacts_to_an_added_word(self):
        base = "ここに あなたの 記録が あります。"
        self.assertEqual(forbidden_hits(base), [])
        for w in EXTRA_FORBIDDEN:
            self.assertTrue(forbidden_hits(base + w), "検出器が反応しない: " + w)
        # 文書の名は例外（先に外してから走査する）
        self.assertEqual(forbidden_hits("通知表を しまう"), [])

    def test_b_static_files_have_no_forbidden_words(self):
        for name in ("index.html", "app.js", "app.css"):
            self.assertEqual(forbidden_hits(_read(name)), [], name)

    def test_c_static_files_have_no_banned_characters(self):
        bad = ["\u202a", "\u202b", "\u202c", "\u202d", "\u202e", "\u2066", "\u2067", "\u2068", "\u2069",
               "\u200b", "\u200c", "\u200d", "\ufeff", "\u2028", "\u2029"]
        emoji = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27bf\ufe0f]")
        for name in ("index.html", "app.js", "app.css"):
            text = _read(name)
            for ch in bad:
                self.assertNotIn(ch, text, name)
            self.assertIsNone(emoji.search(text), name)

    def test_d_static_files_load_nothing_from_outside(self):
        for name in ("index.html", "app.js", "app.css"):
            text = _read(name)
            self.assertNotRegex(text, r"https?://", name)
            self.assertNotRegex(text, r"@import", name)
        self.assertNotRegex(_read("app.js"), r"\bXMLHttpRequest\b|\bWebSocket\b|\bEventSource\b|sendBeacon|\bimport\s*\(")
        # fetch は自分の配信元の /api だけ
        for m in re.finditer(r"fetch\(\s*['\"]([^'\"]+)['\"]", _read("app.js")):
            self.assertTrue(m.group(1).startswith("/api/"), m.group(1))


class N_Gate(_Base):
    def test_no_passphrase_is_fail_closed(self):
        for env in ({}, {"VAULT_PASSPHRASE": ""}):
            s = self.make(env)
            st, j, _, _ = s.call("GET", "/api/status", cookie=False)
            self.assertEqual(st, 200)
            self.assertIs(j["configured"], False)
            self.assertIs(j["logged_in"], False)
            st, j, _, _ = s.call("POST", "/api/login", {"passphrase": "x"}, cookie=False)
            self.assertEqual(st, 503)
            st, _, _, _ = s.call("GET", "/api/records", cookie=False)
            self.assertEqual(st, 401)
            # 保存の場所にも触らない
            self.assertFalse(os.path.exists(s.vault_dir))

    def test_wrong_passphrase_is_401(self):
        s = self.make()
        st, j, _, hdrs = s.call("POST", "/api/login", {"passphrase": PASS + "x"}, cookie=False)
        self.assertEqual(st, 401)
        self.assertEqual(j["error"], "bad_passphrase")
        self.assertFalse([1 for k, _ in hdrs if k.lower() == "set-cookie"])

    def test_records_need_login(self):
        s = self.make()
        for method, path in (("GET", "/api/records"), ("GET", "/api/replies"), ("GET", "/api/claude_log"),
                             ("POST", "/api/export"), ("GET", "/api/prompts"), ("GET", "/api/catalog")):
            st, _, _, _ = s.call(method, path, {} if method == "POST" else None, cookie=False)
            self.assertEqual(st, 401, path)

    def test_session_expires_after_15_minutes(self):
        s = self.make()
        s.login()
        st, _, _, _ = s.call("GET", "/api/records")
        self.assertEqual(st, 200)
        s.clock.advance(901)
        st, j, _, _ = s.call("GET", "/api/records")
        self.assertEqual(st, 401)
        self.assertIs(j.get("expired"), True)
        self.assertEqual(j["error"], "unauthorized")

    def test_activity_keeps_session_alive(self):
        s = self.make()
        s.login()
        for _ in range(3):
            s.clock.advance(600)
            st, _, _, _ = s.call("GET", "/api/records")
            self.assertEqual(st, 200)

    def test_derive_needs_confirm_send(self):
        s = self.make()
        s.login()
        rid = _add(s, "もも", b"dummy-bytes-momo")
        s.app.claude = FakeClaude()
        for body in ({}, {"confirm_send": False}, {"confirm_send": "true"}, {"confirm_send": 1}):
            st, j, _, _ = s.call("POST", "/api/records/%s/derive" % rid, body)
            self.assertEqual(st, 400, body)
            self.assertEqual(j["error"], "confirm_required")
        self.assertEqual(s.app.claude.calls, [])   # 送っていない

    def test_derive_without_claude_is_503(self):
        s = self.make()
        s.login()
        rid = _add(s, "もも", b"dummy-bytes-momo")
        s.app.claude = None
        st, j, _, _ = s.call("POST", "/api/records/%s/derive" % rid, {"confirm_send": True})
        self.assertEqual(st, 503)
        self.assertEqual(j["error"], "claude_unavailable")
        self.assertEqual(j["detail"], "鍵が 設定されていません。")

    def test_too_large_original_is_413(self):
        s = self.make()
        s.login()
        st, j, _, _ = s.call("POST", "/api/records", {
            "record_name": "おおきい", "media_type": "image/png", "data_base64": b64(b"x" * (6 * 1024 * 1024))})
        self.assertEqual(st, 413)
        self.assertEqual(j["error"], "too_large")
        self.assertEqual(s.app.vault.counts()["originals"], 0)

    def test_bad_media_type_is_400(self):
        s = self.make()
        s.login()
        st, j, _, _ = s.call("POST", "/api/records", {
            "record_name": "ぴーでぃーえふ", "media_type": "application/pdf", "data_base64": b64(b"dummy")})
        self.assertEqual(st, 400)
        self.assertEqual(j["error"], "bad_media_type")

    def test_bad_base64_is_400(self):
        s = self.make()
        s.login()
        st, _, _, _ = s.call("POST", "/api/records", {"record_name": "x", "media_type": "image/png", "data_base64": "***"})
        self.assertEqual(st, 400)

    def test_blank_annotation_is_400(self):
        s = self.make()
        s.login()
        rid = _add(s, "もも", b"dummy-bytes-momo")
        for text in ("", "   ", "\n\t "):
            st, j, _, _ = s.call("POST", "/api/records/%s/annotations" % rid, {"text": text})
            self.assertEqual(st, 400, repr(text))
        self.assertEqual(s.app.vault.counts()["annotations"], 0)

    def test_wipe_needs_exact_confirm(self):
        s = self.make()
        s.login()
        _add(s, "もも", b"dummy-bytes-momo")
        for body in ({}, {"confirm": "消す"}, {"confirm": ""}, {"confirm": True}):
            st, _, _, _ = s.call("DELETE", "/api/vault", body)
            self.assertEqual(st, 400, body)
        self.assertEqual(s.app.vault.counts()["originals"], 1)

    def test_export_path_traversal_is_404(self):
        s = self.make()
        s.login()
        for path in ("/api/export/../x", "/api/export/..%2Fx", "/api/export/%2e%2e%2fmanifest.json",
                     "/api/export/export_x.zip.bak", "/api/export/manifest.json", "/api/export/export_..%2f..%2fx.zip"):
            st, _, _, _ = s.call("GET", path)
            self.assertEqual(st, 404, path)

    def test_unknown_record_is_404(self):
        s = self.make()
        s.login()
        for path in ("/api/records/nothing", "/api/records/nothing/original", "/api/records/..%2f..%2fx"):
            st, _, _, _ = s.call("GET", path)
            self.assertEqual(st, 404, path)

    def test_static_page_has_no_personal_text_before_login(self):
        s = self.make()
        s.login()
        name = "ももの通知表"
        _add(s, name, b"dummy-bytes-momo")
        s.call("POST", "/api/catalog", {"name": "りんごの控え"})
        for path in ("/", "/index.html", "/app.js", "/app.css"):
            st, _, payload, _ = s.call("GET", path, cookie=False)
            self.assertEqual(st, 200, path)
            text = payload.decode("utf-8")
            self.assertNotIn(name, text, path)
            self.assertNotIn("りんごの控え", text, path)

    def test_security_headers_on_every_answer(self):
        s = self.make()
        st, _, _, hdrs = s.call("GET", "/", cookie=False)
        h = {k.lower(): v for k, v in hdrs}
        self.assertIn("script-src 'self'", h["content-security-policy"])
        self.assertEqual(h["x-content-type-options"], "nosniff")
        self.assertEqual(h["cache-control"], "no-store")


def _add(s, name, data, media="image/png"):
    st, j, _, _ = s.call("POST", "/api/records", {"record_name": name, "media_type": media, "data_base64": b64(data)})
    assert st == 201, (st, j)
    return j["record_id"]


# ================================================================ T（本物）

class T_Records(_Base):
    def test_add_list_and_original_roundtrip(self):
        s = self.make()
        s.login()
        data = b"dummy-bytes-momo-" + bytes(range(64))
        st, j, _, _ = s.call("POST", "/api/records", {
            "record_name": "もも", "media_type": "image/png", "data_base64": b64(data), "taken_at": "2026-11-06T18:00:00+09:00"})
        self.assertEqual(st, 201)
        rid = j["record_id"]
        import hashlib
        self.assertEqual(j["sha256"], hashlib.sha256(data).hexdigest())
        self.assertTrue(s.app.vault.verify_original(rid))
        st, j, _, _ = s.call("GET", "/api/records")
        self.assertEqual(len(j["items"]), 1)
        row = j["items"][0]
        self.assertEqual(row["record_id"], rid)
        self.assertEqual(row["record_name"], "もも")
        self.assertEqual(row["sha256"], hashlib.sha256(data).hexdigest())
        self.assertIs(row["has_derived"], False)
        self.assertEqual(row["subject"]["confirmed_by_person"], False)
        self.assertNotIn("data", row)
        st, _, payload, hdrs = s.call("GET", "/api/records/%s/original" % rid)
        self.assertEqual(st, 200)
        self.assertEqual(payload, data)
        self.assertEqual(dict((k.lower(), v) for k, v in hdrs)["content-type"], "image/png")

    def test_empty_name_becomes_unnamed(self):
        s = self.make()
        s.login()
        rid = _add(s, "   ", b"dummy-bytes-momo")
        st, j, _, _ = s.call("GET", "/api/records/%s" % rid)
        self.assertEqual(j["record_name"], "名前なし")

    def test_subject_fields_stay_unconfirmed_until_person_confirms(self):
        s = self.make()
        s.login()
        rid = _add(s, "もも", b"dummy-bytes-momo")
        body = {"author_role": "学校", "written_at": "2026-07", "procedure": "学期の記録", "confirmed_by_person": False}
        st, j, _, _ = s.call("PUT", "/api/records/%s/subject" % rid, body)
        self.assertEqual(st, 200)
        self.assertIs(j["subject"]["confirmed_by_person"], False)
        self.assertEqual(j["subject"]["author_role"], "学校")
        self.assertIs(s.app.vault.get_record(rid)["subject"]["confirmed_by_person"], False)
        body["confirmed_by_person"] = True
        st, j, _, _ = s.call("PUT", "/api/records/%s/subject" % rid, body)
        self.assertIs(j["subject"]["confirmed_by_person"], True)
        st, _, _, _ = s.call("PUT", "/api/records/%s/subject" % rid, {"author_role": "x"})
        self.assertEqual(st, 400)

    def test_annotations_do_not_change_original(self):
        s = self.make()
        s.login()
        rid = _add(s, "もも", b"dummy-bytes-momo")
        before = s.app.vault.get_record(rid)["original"]["sha256"]
        for t in ("ここは 私の見方と ちがう。", "この時は 事情が あった。"):
            st, j, _, _ = s.call("POST", "/api/records/%s/annotations" % rid, {"text": t})
            self.assertEqual(st, 201)
            self.assertEqual(j["author"], "person")
        rec = s.app.vault.get_record(rid)
        self.assertEqual(len(rec["annotations"]), 2)
        self.assertEqual(rec["original"]["sha256"], before)
        self.assertTrue(s.app.vault.verify_original(rid))
        st, j, _, _ = s.call("GET", "/api/records/%s" % rid)
        self.assertEqual(len(j["annotations"]), 2)

    def test_delete_record(self):
        s = self.make()
        s.login()
        rid = _add(s, "もも", b"dummy-bytes-momo")
        st, _, _, _ = s.call("DELETE", "/api/records/%s" % rid)
        self.assertEqual(st, 204)
        st, j, _, _ = s.call("GET", "/api/records")
        self.assertEqual(j["items"], [])
        self.assertEqual(s.app.vault.counts()["originals"], 0)
        st, _, _, _ = s.call("DELETE", "/api/records/%s" % rid)
        self.assertEqual(st, 404)

    def test_derive_with_stand_in_claude(self):
        s = self.make(env_ok(ANTHROPIC_API_KEY=DUMMY_KEY))
        s.login()
        rid = _add(s, "もも", b"dummy-bytes-momo")
        s.app.claude = FakeClaude()
        st, j, _, _ = s.call("POST", "/api/records/%s/derive" % rid, {"confirm_send": True})
        self.assertEqual(st, 200)
        self.assertIs(j["has_derived"], True)
        self.assertIn("りんごの 本文", j["derived_markdown"])
        self.assertNotIn("original_sha256", j["derived_markdown"])      # 札の行 2 行は本文に入れない
        self.assertEqual(j["derived_meta"]["label"], "派生（Claude が読み取った写し。原本が正）")
        self.assertEqual(s.app.claude.calls, [rid])
        with open(os.path.join(s.app.vault.root, "records", rid, "derived.md"), encoding="utf-8") as f:
            first = f.read().split("\n")
        self.assertEqual(first[0], "派生（Claude が読み取った写し。原本が正）")
        self.assertTrue(first[1].startswith("original_sha256: "))
        self.assertEqual(s.app.vault.counts()["derived"], 1)
        # 写しだけを消す（原本は動かない）
        st, _, _, _ = s.call("DELETE", "/api/records/%s/derived" % rid)
        self.assertEqual(st, 204)
        self.assertEqual(s.app.vault.counts()["derived"], 0)
        self.assertTrue(s.app.vault.verify_original(rid))

    def test_derive_failure_keeps_original_and_says_unreachable(self):
        s = self.make(env_ok(ANTHROPIC_API_KEY=DUMMY_KEY))
        s.login()
        rid = _add(s, "もも", b"dummy-bytes-momo")
        s.app.claude = FakeClaude(fail=True)
        st, j, _, _ = s.call("POST", "/api/records/%s/derive" % rid, {"confirm_send": True})
        self.assertEqual(st, 502)
        self.assertEqual(j["detail"], "いまは接続できません。")
        self.assertTrue(s.app.vault.verify_original(rid))
        self.assertEqual(s.app.vault.counts()["derived"], 0)

    def test_catalog_without_photo(self):
        s = self.make()
        s.login()
        st, j, _, _ = s.call("POST", "/api/catalog", {"name": "りんごの控え", "place": "家のファイル", "memo": "めも"})
        self.assertEqual(st, 201)
        st, j2, _, _ = s.call("GET", "/api/catalog")
        self.assertEqual([i["name"] for i in j2["items"]], ["りんごの控え"])
        st, _, _, _ = s.call("POST", "/api/catalog", {"name": "  "})
        self.assertEqual(st, 400)
        # 8 鍵の数え方には入らない
        self.assertEqual(sum(s.app.vault.counts().values()), 0)
        st, _, _, _ = s.call("DELETE", "/api/catalog/%s" % j["id"])
        self.assertEqual(st, 204)
        st, j2, _, _ = s.call("GET", "/api/catalog")
        self.assertEqual(j2["items"], [])

    def test_prompts_listing_reads_files_if_present(self):
        s = self.make()
        s.login()
        st, j, _, _ = s.call("GET", "/api/prompts")
        self.assertEqual(st, 200)
        names = [i["name"] for i in j["items"]]
        for it in j["items"]:
            self.assertTrue(len(it["version"]) == 12 or re.match(r"^v[0-9]+\.[0-9]+", it["version"]))
            self.assertTrue(it["text"])
        self.assertTrue(set(names) <= set(("reader", "listener", "arranger")))


class T_Replies(_Base):
    def _reply(self, s, rid="rp-momo-001", human=True, role="mentor"):
        r = {
            "reply_version": "cip-reply-v1", "reply_id": rid, "port_id": "port-test-01", "port_name": "もも受け口",
            "in_reply_to": "b-001", "text": "読みました。\n**次に** 会うときに。", "written_at": "2026-11-07T11:00:00+09:00",
            "author": {"role": role, "attested_at": "2026-11-07T11:00:00+09:00", "human_attestation": human},
        }
        s.app.vault.save_reply(r)
        return rid

    def test_reply_labels_are_two_kinds(self):
        s = self.make()
        s.login()
        self._reply(s, "rp-a", True)
        self._reply(s, "rp-b", False)
        st, j, _, _ = s.call("GET", "/api/replies")
        labels = dict((i["reply_id"], i["author_label"]) for i in j["items"])
        self.assertEqual(labels, {"rp-a": "メンター（人）", "rp-b": "不明"})

    def test_bind_makes_a_record_with_subject_fields_and_discard_does_not(self):
        s = self.make()
        s.login()
        a = self._reply(s, "rp-a", True)
        b = self._reply(s, "rp-b", True)
        st, j, _, _ = s.call("POST", "/api/replies/%s/bind" % a, {"record_name": "ももの返事"})
        self.assertEqual(st, 200)
        self.assertEqual(j["kind"], "reply")
        self.assertEqual(j["record_name"], "ももの返事")
        self.assertEqual(j["subject"]["procedure"], "受け口からの返事")
        self.assertEqual(j["subject"]["author_role"], "mentor")
        self.assertIs(j["subject"]["confirmed_by_person"], True)
        st, j, _, _ = s.call("GET", "/api/records")
        self.assertEqual([i["record_id"] for i in j["items"]], [a])
        st, _, _, _ = s.call("POST", "/api/replies/%s/bind" % a, {})
        self.assertEqual(st, 409)
        st, _, _, _ = s.call("POST", "/api/replies/%s/discard" % b)
        self.assertEqual(st, 204)
        st, j, _, _ = s.call("GET", "/api/records")
        self.assertEqual(len(j["items"]), 1)
        rows = dict((r["reply_id"], r["disposition"]) for r in s.call("GET", "/api/replies")[1]["items"])
        self.assertEqual(rows, {"rp-a": "bound", "rp-b": "discarded"})
        st, _, _, _ = s.call("POST", "/api/replies/nothing/bind", {})
        self.assertEqual(st, 404)
        # 綴じた記録を外す
        st, _, _, _ = s.call("DELETE", "/api/records/%s" % a)
        self.assertEqual(st, 204)
        self.assertEqual(s.call("GET", "/api/records")[1]["items"], [])


class T_ExportAndWipe(_Base):
    def test_export_zip_counts_match_manifest(self):
        s = self.make()
        s.login()
        rid = _add(s, "もも", b"dummy-bytes-momo")
        s.call("POST", "/api/records/%s/annotations" % rid, {"text": "ひとつめ"})
        s.call("POST", "/api/records/%s/annotations" % rid, {"text": "ふたつめ"})
        s.call("PUT", "/api/records/%s/subject" % rid, {"author_role": "a", "written_at": "b", "procedure": "c", "confirmed_by_person": False})
        st, j, _, _ = s.call("POST", "/api/export", {})
        self.assertEqual(st, 200)
        self.assertRegex(j["file"], r"^export_.*\.zip$")
        self.assertEqual(j["counts"]["originals"], 1)
        self.assertEqual(j["counts"]["annotations"], 2)
        self.assertEqual(j["counts"]["subject_fields"], 1)
        st, _, payload, hdrs = s.call("GET", "/api/export/" + j["file"])
        self.assertEqual(st, 200)
        h = dict((k.lower(), v) for k, v in hdrs)
        self.assertEqual(h["content-type"], "application/zip")
        self.assertIn("attachment", h["content-disposition"])
        path = os.path.join(s.tmp.name, "got.zip")
        with open(path, "wb") as f:
            f.write(payload)
        self.assertEqual(storage.verify_export_zip(path), j["counts"])        # 数え直した数＝返した数
        with zipfile.ZipFile(path) as z:
            manifest = json.loads(z.read("manifest.json").decode("utf-8"))
        self.assertEqual(manifest["counts"], j["counts"])
        self.assertEqual(manifest["counts"], s.app.vault.counts())
        # 書き出した物は器の外に置かれる
        self.assertFalse(os.path.exists(os.path.join(s.vault_dir, j["file"])))
        self.assertTrue(os.path.exists(os.path.join(s.tmp.name, "cip_exports", j["file"])))

    def test_wipe_resets_all_counts_to_zero(self):
        s = self.make()
        s.login()
        rid = _add(s, "もも", b"dummy-bytes-momo")
        s.call("POST", "/api/records/%s/annotations" % rid, {"text": "ひとつめ"})
        s.app.vault.save_reply({"reply_id": "rp-z", "port_name": "p", "text": "t", "written_at": "2026-11-07T11:00:00+09:00",
                                "author": {"role": "mentor", "human_attestation": True}})
        self.assertGreater(sum(s.app.vault.counts().values()), 0)
        st, _, _, _ = s.call("DELETE", "/api/vault", {"confirm": "消します"})
        self.assertEqual(st, 204)
        counts = s.app.vault.counts()
        self.assertEqual(sorted(counts), sorted(["originals", "derived", "annotations", "subject_fields", "marks", "statements", "handoffs", "replies"]))
        self.assertEqual(set(counts.values()), {0})
        st, j, _, _ = s.call("GET", "/api/records")
        self.assertEqual(j["items"], [])
        self.assertEqual(s.call("GET", "/api/catalog")[1]["items"], [])

    def test_wipe_can_keep_receipts(self):
        s = self.make()
        s.login()
        _add(s, "もも", b"dummy-bytes-momo")
        bundle = {"bundle_id": "bd-001", "created_at": "2026-11-07T10:00:00+09:00", "item_count": 1, "fingerprint": "f" * 64}
        s.app.vault.save_handoff(bundle, {"status": "confirmed", "receipt_id": "rc-001", "port_name": "p"})
        st, _, _, _ = s.call("DELETE", "/api/vault", {"confirm": "消します", "keep_receipts": True})
        self.assertEqual(st, 204)
        c = s.app.vault.counts()
        self.assertEqual(c["originals"], 0)
        self.assertEqual(c["handoffs"], 1)
        self.assertEqual(s.app.vault.list_handoffs()[0]["receipt"]["receipt_id"], "rc-001")

    def test_claude_log_listing(self):
        s = self.make()
        s.login()
        s.app.vault.log_claude({"kind": "reader", "what": "record x の原本", "bytes": 12, "model": "dummy", "demo": False})
        st, j, _, _ = s.call("GET", "/api/claude_log")
        self.assertEqual(st, 200)
        self.assertEqual(len(j["items"]), 1)
        self.assertEqual(j["items"][0]["bytes"], 12)


class T_Auth(_Base):
    def test_login_sets_http_only_strict_cookie_and_logout_clears(self):
        s = self.make()
        st, _, _, hdrs = s.call("POST", "/api/login", {"passphrase": PASS}, cookie=False)
        self.assertEqual(st, 204)
        sc = [v for k, v in hdrs if k.lower() == "set-cookie"][0]
        self.assertIn("HttpOnly", sc)
        self.assertIn("SameSite=Strict", sc)
        self.assertIn("Path=/", sc)
        s.cookie = sc.split(";")[0]
        self.assertEqual(s.call("GET", "/api/records")[0], 200)
        st, _, _, hdrs = s.call("POST", "/api/logout", {})
        self.assertEqual(st, 204)
        self.assertIn("Max-Age=0", [v for k, v in hdrs if k.lower() == "set-cookie"][0])
        self.assertEqual(s.call("GET", "/api/records")[0], 401)

    def test_logged_out_session_cannot_come_back(self):
        s = self.make()
        s.login()
        old = s.cookie
        s.call("POST", "/api/logout", {})
        s.cookie = old
        st, j, _, _ = s.call("GET", "/api/records")
        self.assertEqual(st, 401)

    def test_status_claude_states(self):
        for env, want in ((env_ok(), "no_key"), (env_ok(ANTHROPIC_API_KEY=DUMMY_KEY), "ok"), (env_ok(CIP_DEMO_MODE="1"), "demo")):
            s = self.make(env)
            st, j, _, _ = s.call("GET", "/api/status", cookie=False)
            self.assertEqual(j["claude"], want)
            self.assertIs(j["configured"], True)
            self.assertIs(j["logged_in"], False)
            self.assertIs(j["port_paired"], False)
            self.assertIs(j["demo_mode"], want == "demo")
            s.login()
            st, j, _, _ = s.call("GET", "/api/status")
            self.assertIs(j["logged_in"], True)

    def test_status_never_shows_secret_values(self):
        s = self.make(env_ok(ANTHROPIC_API_KEY=DUMMY_KEY))
        s.login()
        st, j, payload, _ = s.call("GET", "/api/status")
        text = payload.decode("utf-8")
        self.assertNotIn(PASS, text)
        self.assertNotIn(DUMMY_KEY, text)

    def test_port_paired_flag_follows_pairing(self):
        s = self.make()
        s.login()
        s.app.vault.save_pairing({"port_id": "port-test-01", "port_name": "もも受け口"})
        st, j, _, _ = s.call("GET", "/api/status")
        self.assertIs(j["port_paired"], True)
        self.assertEqual(j["port_name"], "もも受け口")


class T_Screen(unittest.TestCase):
    def test_index_has_six_views_and_gate_note(self):
        html = _read("index.html")
        self.assertEqual(len(re.findall(r'data-view="', html)), 6)
        for v in ("home", "renshu", "hikidashi", "kiroku", "seiri", "watasu"):
            self.assertIn('data-view="%s"' % v, html)
        self.assertIn('data-w="W-03"', html)
        self.assertIn('src="app.js"', html)
        self.assertIn('href="app.css"', html)
        # 本人の字は骨に入れない（字は app.js の表から）
        self.assertNotIn(NOTE_KAKO, html)

    def test_app_js_table_has_the_fixed_sentences(self):
        js = _read("app.js")
        self.assertIn(NOTE_KAKO, js)
        self.assertIn("しばらく操作がなかったため、あなたの記録を守るために自動でログアウトしました。", js)
        self.assertIn("派生（Claude が読み取った写し。原本が正）", js)
        self.assertIn("この入口の応答は 録画用に記録した物です", js)
        self.assertIn("設定が ありません。", js)
        self.assertIn("このやりとりが見える人: あなただけ。", js)

    def test_every_data_w_key_in_index_exists_in_the_table(self):
        html = _read("index.html")
        js = _read("app.js")
        for key in set(re.findall(r'data-w(?:-title|-label)?="([^"]+)"', html)):
            self.assertRegex(js, r"['\"]%s['\"]\s*:" % re.escape(key), key)

    def test_static_served_with_right_types(self):
        s = Srv(env_ok())
        try:
            for path, ct in (("/", "text/html"), ("/app.js", "application/javascript"), ("/app.css", "text/css")):
                st, _, payload, hdrs = s.call("GET", path, cookie=False)
                self.assertEqual(st, 200)
                self.assertTrue(dict((k.lower(), v) for k, v in hdrs)["content-type"].startswith(ct), path)
        finally:
            s.close()


if __name__ == "__main__":
    unittest.main()
