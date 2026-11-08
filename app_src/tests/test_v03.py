# -*- coding: utf-8 -*-
"""器 v0.3 で足した物の検査。N_＝陰性対照（先）／T_＝本物。標準ライブラリだけ・ネットワークへは出ない。

- 入口の止め（5 回／5 分・423）と Host の検査（421）
- 記録の道具 tools/record_demo.py（--dry-run と、偽の応答を使った書き出し）
- claude_client の入力の組み立て（鍵の値が直す前と同じ）・ClaudeError の status
- 保存の権限・返事の記録への注記・持ち出しの .md・指示の文の 1 行目・発言の札・丸の光の絵
"""
import contextlib
import hashlib
import http.client
import io
import json
import os
import stat
import tempfile
import unittest
import urllib.error
import zipfile

from app_src.common import httpkit, words
from app_src.tests.test_vault_api import PASS, FakeClock, Srv, env_ok
from app_src.tools import record_demo
from app_src.vault_app import claude_client, main as vmain, storage

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPTS = os.path.join(APP_ROOT, "vault_app", "prompts")
RECORDED = os.path.join(APP_ROOT, "demo", "recorded")
STATIC = vmain.STATIC_DIR
COND = {"amount": "ふつう", "split": "文ごと", "ease": "やさしい", "length": "みじかく", "input": "文字"}

# 切り出しの前に計算しておいた値（鍵の値は 1 ビットも変えない）
KNOWN_LISTENER_SHA16 = "a67696839a10e345"
KNOWN_ARRANGER_SHA16 = "5b9c2cdcae8b5954"
KNOWN_READER_SHA16 = "a81ac3e7595c38c2"
KNOWN_PROMPT_SHA256 = {
    "reader": "c9f8adfbe844da466dae602154cd18395e23822f31b70f0ade8ab14c8c322ea0",
    "listener": "d6e318da8238034cda1b647c4dab29026b23715a65f85571a8f59a0978760352",   # v0.14: 「問いの 向き」「きょうの こと」の 2 節を 外した 本文の 指紋（画面から 届かない 物を 約束に 書かない）
    "arranger": "b49673ecbd5ba8e414b366f07de25c46f86894bac24c1bbe2e3432582b4f743f",
}
# 役ごとの 版の字（聞き役だけ v0.3.3 → v0.3.4 に上がった。v0.14: 2 節を 外した）
PROMPT_HEADER = {
    "reader": ("v0.3.1", "2026-11-05"),
    "listener": ("v0.3.4", "2026-11-08"),
    "arranger": ("v0.3.1", "2026-11-05"),
}


def _header_line(kind):
    v, d = PROMPT_HEADER[kind]
    return "# 版: %s / 決めた日: %s" % (v, d)


LAW_INDEX = [{"id": "x-1", "law_name": "法A", "article": "第1条"}]


def _text(b):
    """repo のファイルの字。Windows の checkout（CRLF）でも同じ比較ができるよう改行をそろえる。"""
    return b.decode("utf-8").replace("\r\n", "\n")


def _read(rel):
    with open(os.path.join(STATIC, rel), "rb") as f:
        return _text(f.read())


def _tree_bytes(root):
    out = {}
    for base, _d, files in os.walk(root):
        for f in files:
            p = os.path.join(base, f)
            with open(p, "rb") as g:
                out[os.path.relpath(p, root)] = g.read()
    return out


def _run_tool(argv, env=None, client=None):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = record_demo.run(argv, env=env if env is not None else {}, client=client)
    return rc, buf.getvalue()


class FakeLive(claude_client.ClaudeClient):
    """通信の部品を使わず、決めた字を返す（記録の道具の書き出しの検査用）。"""
    def __init__(self, answers):
        cfg = {"api_key": "dummy-key", "demo_mode": False, "claude_model": "test-model"}
        super().__init__(cfg, None, None, PROMPTS)
        self.answers = answers
        self.calls = []

    def _live_text(self, kind, system, blocks):
        self.calls.append(kind)
        a = self.answers[kind]
        if isinstance(a, Exception):
            raise a
        return a


GOOD = {
    "reader": "# ダミーの書類\n\n- こくご: 字を 読んだ。\n",
    "listener": '{"question": "そのとき、どんな 音が していましたか？"}',
    "arranger": '{"draft_text": "困っていること\\n朝の じゅんびが 大変です。\\n\\nのぞむこと\\n相談したいです。", "statute_ids": ["no-such-id"]}',
}


class _Base(unittest.TestCase):
    def make(self, env=None, clock=None):
        s = Srv(env if env is not None else env_ok(), clock)
        self.addCleanup(s.close)
        return s

    def tmpdir(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        return t.name


# =====================================================================
# N_ 陰性対照（先）
# =====================================================================

class N_LoginLock(_Base):
    def _login(self, s, pw):
        return s.call("POST", "/api/login", {"passphrase": pw}, cookie=False)[0]

    def test_sixth_try_is_locked_even_with_the_right_passphrase(self):
        clock = FakeClock()
        s = self.make(clock=clock)
        for _ in range(5):
            self.assertEqual(self._login(s, "wrong-" + PASS), 401)
        self.assertEqual(self._login(s, PASS), 423)         # 正しい合言葉でも止まる
        self.assertEqual(self._login(s, "wrong-" + PASS), 423)
        st, j, _, _ = s.call("POST", "/api/login", {"passphrase": PASS}, cookie=False)
        self.assertEqual(j["error"], "locked")
        self.assertTrue(words.is_clean(j["detail"]))

    def test_lock_ends_after_five_minutes(self):
        clock = FakeClock()
        s = self.make(clock=clock)
        for _ in range(5):
            self._login(s, "wrong-" + PASS)
        clock.advance(299)
        self.assertEqual(self._login(s, PASS), 423)
        clock.advance(2)
        self.assertEqual(self._login(s, PASS), 204)

    def test_four_misses_then_right_does_not_lock(self):
        s = self.make()
        for _ in range(4):
            self._login(s, "wrong-" + PASS)
        self.assertEqual(self._login(s, PASS), 204)
        for _ in range(4):                                   # 数は戻っている
            self._login(s, "wrong-" + PASS)
        self.assertEqual(self._login(s, PASS), 204)


class N_Host(_Base):
    def _get(self, s, host):
        conn = http.client.HTTPConnection("127.0.0.1", s.port, timeout=10)
        conn.putrequest("GET", "/api/status", skip_host=True)
        if host is not None:
            conn.putheader("Host", host)
        conn.endheaders()
        r = conn.getresponse()
        body = r.read()
        conn.close()
        return r.status, (json.loads(body.decode("utf-8")) if body else None)

    def test_outside_names_get_421(self):
        s = self.make()
        for h in ("evil.example", "evil.example:80", "127.0.0.1.evil.example", "localhost.evil.example:1", "10.0.0.5:8765", ""):
            st, j = self._get(s, h)
            self.assertEqual(st, 421, h)
            self.assertEqual(j["error"], "misdirected")
        self.assertEqual(self._get(s, "evil.example")[1]["detail"], "この 入口は 手元の 画面からだけ 開けます。")

    def test_local_names_and_missing_host_pass(self):
        s = self.make()
        for h in ("127.0.0.1", "127.0.0.1:%d" % s.port, "localhost", "localhost:8765", "[::1]", "[::1]:8765", "LOCALHOST:1"):
            self.assertEqual(self._get(s, h)[0], 200, h)
        self.assertEqual(self._get(s, None)[0], 200)        # Host が無い要求は通す

    def test_host_allowed_matrix(self):
        self.assertTrue(httpkit.host_allowed(None))
        self.assertFalse(httpkit.host_allowed("evil.example"))
        self.assertFalse(httpkit.host_allowed("127.0.0.1:abc"))
        self.assertFalse(httpkit.host_allowed("127.0.0.1:1234567"))


class N_RecordDemo(_Base):
    def test_dry_run_writes_nothing_and_keeps_placeholders(self):
        before = _tree_bytes(RECORDED)
        rc, out = _run_tool(["--dry-run"])
        self.assertEqual(rc, 0)
        self.assertEqual(_tree_bytes(RECORDED), before)
        for kind in ("reader", "listener", "arranger"):
            with open(os.path.join(RECORDED, kind, "default.json"), "rb") as f:
                self.assertIs(json.loads(f.read().decode("utf-8")).get("recorded_from_live"), False)
        self.assertIn("listener: 入力 3 件", out)
        self.assertIn("reader: 入力 4 件", out)

    def test_dry_run_into_other_dir_does_not_touch_existing_files(self):
        d = self.tmpdir()
        p = os.path.join(d, "listener", "default.json")
        os.makedirs(os.path.dirname(p))
        with open(p, "wb") as f:
            f.write(b'{"question": "x", "recorded_from_live": false}')
        rc, _ = _run_tool(["--dry-run", "--out", d])
        self.assertEqual(rc, 0)
        with open(p, "rb") as f:
            self.assertEqual(f.read(), b'{"question": "x", "recorded_from_live": false}')

    def test_no_key_stops_with_2_and_names_no_key(self):
        rc, out = _run_tool(["--out", self.tmpdir()], env={"CIP_DEMO_MODE": "1"})
        self.assertEqual(rc, 2)
        self.assertIn("鍵が ありません。環境変数 ANTHROPIC_API_KEY に入れてください。", out)

    def test_broken_answers_are_not_recorded(self):
        d = self.tmpdir()
        bad = {"reader": "   ", "listener": '{"question": "評価する ために 聞きます？"}',
               "arranger": '{"draft_text": "", "statute_ids": []}'}
        fake = FakeLive(bad)
        rc, out = _run_tool(["--out", d], env={"ANTHROPIC_API_KEY": "dummy-key"}, client=fake)
        self.assertEqual(rc, 1)
        self.assertEqual(_tree_bytes(d), {})
        self.assertIn("NG（listener 文 1: forbidden_word）", out)
        self.assertIn("まだ仮", out)

    def test_http_failure_is_told_by_number_and_stops_on_401(self):
        d = self.tmpdir()
        fake = FakeLive({"reader": claude_client.ClaudeError("x", status=401), "listener": GOOD["listener"], "arranger": GOOD["arranger"]})
        rc, out = _run_tool(["--out", d], env={"ANTHROPIC_API_KEY": "dummy-key"}, client=fake)
        self.assertEqual(rc, 1)
        self.assertEqual(fake.calls, ["reader"])             # 同じ失敗を続けない
        self.assertIn("401", out)
        self.assertIn("ANTHROPIC_API_KEY", out)

    def test_model_name_is_shown_first_and_key_never_shown(self):
        fake = FakeLive(GOOD)
        rc, out = _run_tool(["--dry-run", "--out", self.tmpdir()], env={"ANTHROPIC_API_KEY": "dummy-key"}, client=fake)
        self.assertTrue(out.startswith("モデル: test-model"))
        self.assertNotIn("dummy-key", out)


class N_Question(unittest.TestCase):
    def test_check_question_drops_broken_values(self):
        for bad, why in ((None, "bad_json"), (5, "bad_json"), ("", "empty"), ("あ\nい？", "multiline"),
                         ("あ" * 61, "too_long"), ("3つ ありますか？", "has_digit"), ("評価しますか？", "forbidden_word"),
                         ("そうですか", "bad_ending")):
            self.assertEqual(claude_client.check_question(bad), why)

    def test_ask_question_drops_broken_answers(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        os.makedirs(os.path.join(d.name, "listener"))
        for payload, why in (({"question": 5}, "bad_json"), ({"question": "続きをどうぞ？"}, "forbidden_word"), ({}, "bad_json")):
            with open(os.path.join(d.name, "listener", "default.json"), "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
            c = claude_client.ClaudeClient({"demo_mode": True}, _NullVault(), lambda: 1800000000.0, PROMPTS, demo_dir=d.name)
            self.assertEqual(c.ask_question("朝です。", COND), (None, why))


class _NullVault(object):
    def log_claude(self, entry):
        pass


# =====================================================================
# T_ 本物
# =====================================================================

class T_Builders(unittest.TestCase):
    def setUp(self):
        self.c = claude_client.ClaudeClient({"demo_mode": False}, None, None, PROMPTS)

    def test_keys_are_the_same_as_before_the_split(self):
        sp = claude_client._sha_prefix
        self.assertEqual(sp(self.c.build_listener("きょうは 朝 早く 目が さめた。", COND)[2]), KNOWN_LISTENER_SHA16)
        self.assertEqual(sp(self.c.build_arranger("朝の 準備に 時間が かかります。", "ゆっくり 準備したい。", ["写しです"], LAW_INDEX)[2]), KNOWN_ARRANGER_SHA16)
        self.assertEqual(sp(self.c.build_reader(b"\x89PNG-dummy", "image/png")[2]), KNOWN_READER_SHA16)

    def test_system_text_is_unchanged_without_the_first_line(self):
        for kind, want in KNOWN_PROMPT_SHA256.items():
            system = getattr(self.c, "build_" + kind)(*{
                "reader": (b"x", "image/png"),
                "listener": ("a", COND),
                "arranger": ("a", "b", [], LAW_INDEX),
            }[kind])[0]
            self.assertEqual(hashlib.sha256(system.encode("utf-8")).hexdigest(), want, kind)
            self.assertNotIn("決めた日", system)
            self.assertFalse(system.startswith("#"))

    def test_blocks_shape(self):
        system, blocks, key = self.c.build_reader(b"abc", "image/png")
        self.assertEqual(key, b"abc")
        self.assertEqual(blocks[0]["type"], "image")
        self.assertEqual(blocks[1]["type"], "text")
        with self.assertRaises(claude_client.ClaudeError):
            self.c.build_reader(b"abc", "image/svg+xml")

    def test_claude_error_status(self):
        self.assertIsNone(claude_client.ClaudeError("x").status)
        self.assertEqual(claude_client.ClaudeError("x", status=404).status, 404)

    def test_live_text_keeps_only_the_status_number(self):
        c = claude_client.ClaudeClient({"api_key": "dummy-key", "demo_mode": False}, None, None, PROMPTS)

        def boom(req, timeout=None):
            raise urllib.error.HTTPError("http://127.0.0.1/x", 429, "secret body words", {}, None)
        real = claude_client.urllib.request.urlopen
        claude_client.urllib.request.urlopen = boom
        try:
            with self.assertRaises(claude_client.ClaudeError) as cm:
                c._live_text("listener", "s", [{"type": "text", "text": "t"}])
        finally:
            claude_client.urllib.request.urlopen = real
        self.assertEqual(cm.exception.status, 429)
        self.assertNotIn("secret", str(cm.exception))
        self.assertNotIn("dummy-key", str(cm.exception))

        def plain(req, timeout=None):
            raise OSError("down")
        claude_client.urllib.request.urlopen = plain
        try:
            with self.assertRaises(claude_client.ClaudeError) as cm:
                c._live_text("listener", "s", [{"type": "text", "text": "t"}])
        finally:
            claude_client.urllib.request.urlopen = real
        self.assertIsNone(cm.exception.status)


class T_RecordDemo(_Base):
    def test_records_with_fake_answers_into_other_dir(self):
        d = self.tmpdir()
        fake = FakeLive(GOOD)
        rc, out = _run_tool(["--out", d], env={"ANTHROPIC_API_KEY": "dummy-key"}, client=fake)
        self.assertEqual(rc, 0, out)
        self.assertEqual(fake.calls.count("reader"), 4)
        self.assertEqual(fake.calls.count("listener"), 3)
        self.assertEqual(fake.calls.count("arranger"), 1)
        self.assertIn("帯: 本物の記録", out)
        for kind in ("reader", "listener", "arranger"):
            names = sorted(os.listdir(os.path.join(d, kind)))
            self.assertIn("default.json", names)
            for n in names:
                with open(os.path.join(d, kind, n), "rb") as f:
                    rec = json.loads(f.read().decode("utf-8"))
                self.assertIs(rec["recorded_from_live"], True)
                self.assertEqual(rec["model"], "test-model")
                self.assertRegex(rec["prompt_sha256"], r"^[0-9a-f]{64}$")
                self.assertRegex(rec["input_sha256_16"], r"^[0-9a-f]{16}$")
                if n != "default.json":
                    self.assertEqual(n, rec["input_sha256_16"] + ".json")
            self.assertEqual(len(names), {"reader": 5, "listener": 4, "arranger": 2}[kind])
        with open(os.path.join(d, "arranger", "default.json"), "rb") as f:
            self.assertEqual(json.loads(f.read().decode("utf-8"))["statute_ids"], [])   # 知らない id は残さない
        blob = json.dumps(_tree_bytes(d), default=lambda b: b.decode("utf-8", "replace"), ensure_ascii=False)
        self.assertNotIn("dummy-key", blob)

    def test_recorded_files_are_replayed_by_demo_mode_with_the_same_keys(self):
        d = self.tmpdir()
        _run_tool(["--out", d], env={"ANTHROPIC_API_KEY": "dummy-key"}, client=FakeLive(GOOD))
        c = claude_client.ClaudeClient({"demo_mode": True}, _NullVault(), lambda: 1800000000.0, PROMPTS, demo_dir=d)
        self.assertFalse(c.demo_is_placeholder())
        # 入力の指紋で引いた物が返る（default でなく、その入力の名の記録）
        inputs = record_demo.load_inputs(record_demo.DEFAULT_INPUTS)
        text, cond = inputs["listener"][0]
        sha = claude_client._sha_prefix(c.build_listener(text, cond)[2])
        self.assertTrue(os.path.isfile(os.path.join(d, "listener", sha + ".json")))
        self.assertEqual(c.ask_question(text, cond), ("そのとき、どんな 音が していましたか？", None))

    def test_inputs_file_matches_screen_conditions_and_is_clean(self):
        inputs = record_demo.load_inputs(record_demo.DEFAULT_INPUTS)
        self.assertEqual(len(inputs["listener"]), 3)
        self.assertEqual(len(inputs["reader"]), 4)
        self.assertEqual(len(inputs["arranger"]), 1)
        for text, cond in inputs["listener"]:
            self.assertTrue(words.is_clean(text))
            self.assertEqual(set(cond), set(COND))

    def test_dry_run_prints_sha16_for_listener(self):
        rc, out = _run_tool(["--dry-run", "--kinds", "listener"])
        self.assertEqual(rc, 0)
        self.assertIn(KNOWN_LISTENER_SHA16, out)
        self.assertNotIn("reader:", out)


@unittest.skipIf(os.name != "posix", "権限の検査は POSIX だけ")
class T_Permissions(_Base):
    def test_files_0600_and_folders_0700(self):
        s = self.make()
        s.login()
        s.call("POST", "/api/records", {"media_type": "image/png", "data_base64": "aGVsbG8=", "record_name": "もも"})
        s.call("POST", "/api/catalog", {"name": "ひかえ"})
        s.call("POST", "/api/export", {})
        root = s.app.vault.root
        seen_f = seen_d = 0
        for base, dirs, files in os.walk(root):
            for dd in dirs:
                m = stat.S_IMODE(os.stat(os.path.join(base, dd)).st_mode)
                self.assertEqual(m, 0o700, os.path.join(base, dd))
                seen_d += 1
            for f in files:
                m = stat.S_IMODE(os.stat(os.path.join(base, f)).st_mode)
                self.assertEqual(m, 0o600, os.path.join(base, f))
                seen_f += 1
        self.assertGreater(seen_f, 3)
        self.assertGreater(seen_d, 0)
        self.assertEqual(stat.S_IMODE(os.stat(root).st_mode), 0o700)
        exp = os.path.join(os.path.dirname(root), "cip_exports")
        self.assertEqual(stat.S_IMODE(os.stat(exp).st_mode), 0o700)
        for n in os.listdir(exp):
            self.assertEqual(stat.S_IMODE(os.stat(os.path.join(exp, n)).st_mode), 0o600)


class T_ReplyAnnotation(_Base):
    def _bound(self, s, rid="rp-v03-001"):
        s.app.vault.save_reply({
            "reply_version": "cip-reply-v1", "reply_id": rid, "port_id": "port-test-01", "port_name": "もも受け口",
            "in_reply_to": "b-001", "text": "読みました。", "written_at": "2026-11-07T11:00:00+09:00",
            "author": {"role": "mentor", "attested_at": "2026-11-07T11:00:00+09:00", "human_attestation": True},
        })
        st, _, _, _ = s.call("POST", "/api/replies/%s/bind" % rid, {"record_name": "ももの返事"})
        self.assertEqual(st, 200)
        return rid

    def test_note_on_a_bound_reply_is_201_and_listed(self):
        s = self.make()
        s.login()
        rid = self._bound(s)
        st, j, _, _ = s.call("POST", "/api/records/%s/annotations" % rid, {"text": "あとで 読みなおす"})
        self.assertEqual(st, 201)
        self.assertEqual(j["text"], "あとで 読みなおす")
        st, j, _, _ = s.call("GET", "/api/records/%s" % rid)
        self.assertEqual([a["text"] for a in j["annotations"]], ["あとで 読みなおす"])
        st, j, _, _ = s.call("GET", "/api/records")
        row = [i for i in j["items"] if i["record_id"] == rid][0]
        self.assertEqual(len(row["annotations"]), 1)
        self.assertEqual(s.app.vault.counts()["annotations"], 1)       # 持ち出しの数え方にも入る

    def test_note_on_unknown_or_discarded_reply_is_404(self):
        s = self.make()
        s.login()
        self.assertEqual(s.call("POST", "/api/records/nothing/annotations", {"text": "x"})[0], 404)
        rid = self._bound(s)
        s.call("DELETE", "/api/records/%s" % rid)
        self.assertEqual(s.call("POST", "/api/records/%s/annotations" % rid, {"text": "x"})[0], 404)

    def test_empty_note_on_reply_is_400_and_photo_still_works(self):
        s = self.make()
        s.login()
        rid = self._bound(s)
        self.assertEqual(s.call("POST", "/api/records/%s/annotations" % rid, {"text": "  "})[0], 400)
        st, j, _, _ = s.call("POST", "/api/records", {"media_type": "image/png", "data_base64": "aGVsbG8=", "record_name": "もも"})
        self.assertEqual(s.call("POST", "/api/records/%s/annotations" % j["record_id"], {"text": "ひとつ"})[0], 201)

    def test_removing_a_bound_reply_removes_its_notes(self):
        s = self.make()
        s.login()
        rid = self._bound(s)
        s.call("POST", "/api/records/%s/annotations" % rid, {"text": "ひとつ"})
        self.assertEqual(s.call("DELETE", "/api/records/%s" % rid)[0], 204)
        self.assertFalse(os.path.exists(os.path.join(s.app.vault.root, "records", rid)))


class T_ExportStatementsMd(_Base):
    def test_zip_has_md_next_to_json_and_counts_are_unchanged(self):
        s = self.make()
        s.login()
        for n in range(2):
            st, j, _, _ = s.call("POST", "/api/statements", {"sections": {"trouble": "困りごと%d" % n, "wish": "のぞみ"}})
            self.assertEqual(st, 201)
        sid = j["item_id"]
        st, _, _, _ = s.call("POST", "/api/statements/%s/finalize" % sid, {"text": "これが 最終版の 字です。"})
        self.assertEqual(st, 200)
        st, ex, _, _ = s.call("POST", "/api/export", {})
        self.assertEqual(st, 200)
        self.assertEqual(ex["counts"]["statements"], 2)
        path = os.path.join(os.path.dirname(s.app.vault.root), "cip_exports", ex["file"])
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            js = sorted(n for n in names if n.startswith("statements/") and n.endswith(".json"))
            md = sorted(n for n in names if n.startswith("statements/") and n.endswith(".md"))
            self.assertEqual(len(js), len(md))
            self.assertEqual([n[:-5] for n in js], [n[:-3] for n in md])
            text = z.read("statements/%s.md" % sid).decode("utf-8")
        self.assertIn("これが 最終版の 字です。", text)
        self.assertIn("## 作った日", text)
        self.assertIn("## 主語の欄", text)
        self.assertIn("## 本文", text)
        self.assertEqual(storage.verify_export_zip(path), ex["counts"])
        self.assertEqual(s.app.vault.counts()["statements"], 2)


class T_PromptHeader(_Base):
    def test_files_start_with_the_header_line(self):
        for kind in ("reader", "listener", "arranger"):
            with open(os.path.join(PROMPTS, kind + ".txt"), "rb") as f:
                first = _text(f.read()).split("\n", 1)[0]
            self.assertEqual(first, _header_line(kind))

    def test_split_prompt(self):
        self.assertEqual(claude_client.split_prompt("# 版: v0.3 / 決めた日: 2026-11-05\n本文です\n"), ("v0.3", "2026-11-05", "本文です\n"))
        self.assertEqual(claude_client.split_prompt("本文です\n"), (None, None, "本文です\n"))
        self.assertEqual(claude_client.split_prompt("# 版: v0.3\n本文\n")[0], None)

    def test_api_reads_version_and_date_from_the_line(self):
        s = self.make()
        s.login()
        st, j, _, _ = s.call("GET", "/api/prompts")
        self.assertEqual(st, 200)
        self.assertEqual(len(j["items"]), 3)
        for it in j["items"]:
            self.assertEqual(it["version"], PROMPT_HEADER[it["name"]][0])
            self.assertEqual(it["decided_on"], PROMPT_HEADER[it["name"]][1])
            self.assertFalse(it["text"].startswith("# 版"))
            with open(os.path.join(PROMPTS, it["name"] + ".txt"), "rb") as f:
                raw = _text(f.read())
            self.assertEqual(_header_line(it["name"]) + "\n" + it["text"], raw)

    def test_falls_back_to_the_old_way_without_the_line(self):
        d = self.tmpdir()
        pd = os.path.join(d, "vault_app", "prompts")
        os.makedirs(pd)
        for k in ("reader", "listener", "arranger"):
            with open(os.path.join(pd, k + ".txt"), "w", encoding="utf-8") as f:
                f.write("本文だけ\n")
        s = self.make(env_ok())
        s.app.cfg["app_root"] = d
        s.login()
        st, j, _, _ = s.call("GET", "/api/prompts")
        self.assertEqual(st, 200)
        for it in j["items"]:
            self.assertEqual(len(it["version"]), 12)
            self.assertRegex(it["decided_on"], r"^\d{4}-\d{2}-\d{2}$")


class T_TurnLabel(_Base):
    def test_turn_response_has_model_and_prompt_version(self):
        s = self.make(env_ok(CIP_DEMO_MODE="1", CIP_CLAUDE_MODEL="label-test-model"))
        s.login()
        s.app.claude = claude_client.ClaudeClient(s.app.cfg, s.app.vault, s.app.clock, PROMPTS)
        st, j, _, _ = s.call("POST", "/api/practice/turns", {"conditions": COND, "text": "朝です。"})
        self.assertEqual(st, 200)
        self.assertEqual(j["model"], "label-test-model")
        self.assertEqual(j["prompt_version"], PROMPT_HEADER["listener"][0])
        self.assertIs(j["demo"], True)
        self.assertEqual(j["readback"], "朝です。")

    def test_turn_without_claude_still_works_and_has_no_label(self):
        s = self.make()
        s.login()
        st, j, _, _ = s.call("POST", "/api/practice/turns", {"conditions": COND, "text": "朝です。"})
        self.assertEqual(st, 200)
        self.assertEqual(j["reason"], "claude_unavailable")
        self.assertNotIn("model", j)


class T_LightMotif(unittest.TestCase):
    def test_cut_out_face_image_is_gone_everywhere_in_static(self):
        for name in sorted(os.listdir(STATIC)):
            p = os.path.join(STATIC, name)
            if os.path.isfile(p) and name.endswith((".css", ".js", ".html")):
                self.assertNotIn("--img-icon-teku", _read(name), name)
        self.assertEqual(_read("brand.css").count("--img-"), 5)

    def test_gate_dot_and_reload_dot_use_the_light_svg(self):
        html = _read("index.html")
        a = html.index('class="gate-dot"')
        seg = html[a:html.index("</span>", a)]
        self.assertIn("<svg", seg)
        self.assertIn('aria-hidden="true"', seg)
        self.assertIn("#FDEFC4", seg)
        self.assertNotIn("<img", html)
        js = _read("app.js")
        self.assertIn("paintSvg(dot, NAV_ICONS.home)", js)
        css = _read("app.css")
        self.assertNotIn("background-image: var(--img-", css.split(".gate-dot")[1].split(".gate-name")[0])

    def test_the_gate_svg_is_the_same_picture_as_the_home_icon(self):
        js = _read("app.js")
        home = js.split("home: '", 1)[1].split("',\n", 1)[0]
        self.assertIn(home, _read("index.html"))


class T_SkipLinkFromTable(unittest.TestCase):
    def test_skip_text_is_in_the_table_not_in_the_html(self):
        with open(os.path.join(APP_ROOT, "receiver_app", "static", "index.html"), "rb") as f:
            html = _text(f.read())
        with open(os.path.join(APP_ROOT, "receiver_app", "static", "port.js"), "rb") as f:
            js = _text(f.read())
        self.assertIn('data-j="J-skip"></a>', html)
        self.assertNotIn("本文へスキップ", html)
        self.assertIn("'J-skip': '本文へスキップ'", js)

    def test_emoji_range_in_the_api_test_is_written_with_escapes(self):
        with open(os.path.join(APP_ROOT, "tests", "test_vault_api.py"), "rb") as f:
            src = _text(f.read())
        line = [l for l in src.split("\n") if "emoji = re.compile" in l][0]
        self.assertTrue(all(ord(ch) < 0x2000 for ch in line), line)
        self.assertIn("\\u2600-\\u27bf", line)


if __name__ == "__main__":
    unittest.main()
