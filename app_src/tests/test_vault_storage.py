# -*- coding: utf-8 -*-
"""vault_app/storage.py の検査。tempfile の中だけで書く。N_＝陰性対照（先）／T_＝本物。"""
import json, os, tempfile, unittest, zipfile

from app_src.common import contract
from app_src.common.vector import vector_v1, receipt_for, reply_v1
from app_src.vault_app import storage

PNG = b"dummy-bytes-momo-001"
JPG = b"dummy-bytes-ringo-002"


def _original_file(v, rid):
    d = os.path.join(v.root, "records", rid)
    return os.path.join(d, [f for f in os.listdir(d) if f.startswith("original.") and f != "original.json"][0])


class _Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = self._tmp.name
        self.v = storage.open_vault(os.path.join(self.dir, "vault"))
        self.out = os.path.join(self.dir, "out")


class N_Original(_Base):
    def test_one_byte_change_breaks_verify(self):
        rid = self.v.add_record("もも", "image/png", PNG, "2026-11-06T18:00:00+09:00")
        self.assertTrue(self.v.verify_original(rid))
        p = _original_file(self.v, rid)
        with open(p, "r+b") as f:
            f.seek(0); f.write(b"X")
        self.assertFalse(self.v.verify_original(rid))

    def test_second_add_with_same_id_raises(self):
        self.v.add_record("もも", "image/png", PNG, record_id="rec-fixed")
        with self.assertRaises(storage.OriginalExists):
            self.v.add_record("りんご", "image/png", JPG, record_id="rec-fixed")
        self.assertEqual(self.v.read_original("rec-fixed")[0], PNG)

    def test_deleted_original_file_fails_verify(self):
        rid = self.v.add_record("もも", "image/jpeg", JPG)
        os.unlink(_original_file(self.v, rid))
        self.assertFalse(self.v.verify_original(rid))

    def test_bad_media_type_raises(self):
        with self.assertRaises(ValueError):
            self.v.add_record("もも", "application/pdf", PNG)

    def test_too_big_raises(self):
        with self.assertRaises(ValueError):
            self.v.add_record("もも", "image/png", b"a" * (contract.MAX_ORIGINAL_BYTES + 1))

    def test_path_like_id_raises(self):
        for bad in ("../x", "a/b", "", "a b"):
            with self.assertRaises(ValueError):
                self.v.add_record("もも", "image/png", PNG, record_id=bad) if bad else self.v.get_turn(bad)

    def test_unknown_record_raises(self):
        with self.assertRaises(KeyError):
            self.v.add_annotation("no-such", "x")
        with self.assertRaises(KeyError):
            self.v.set_derived("no-such", "x", {})


class N_Practice(_Base):
    def test_mark_with_unknown_word_raises(self):
        tid = self.v.add_turn({"amount": "少なく", "split": True, "topic_free": False}, "ぶん", "ぶん")
        for bad in ("良い", "", "true", None):
            with self.assertRaises(ValueError):
                self.v.add_mark(tid, bad)

    def test_mark_without_turn_raises(self):
        with self.assertRaises(KeyError):
            self.v.add_mark("turn-none", "残った")
        self.assertEqual(self.v.counts()["marks"], 0)


class N_Handoff(_Base):
    def test_bad_receipt_status_raises(self):
        b = vector_v1()
        with self.assertRaises(ValueError):
            self.v.save_handoff(b, {"status": "ok"})
        with self.assertRaises(ValueError):
            self.v.save_handoff(b, {"receipt_id": "x"})

    def test_bound_without_record_raises(self):
        self.v.save_reply(reply_v1(True))
        with self.assertRaises(ValueError):
            self.v.set_reply_disposition(reply_v1(True)["reply_id"], "bound")
        with self.assertRaises(ValueError):
            self.v.set_reply_disposition(reply_v1(True)["reply_id"], "read")


class N_ClaudeLog(_Base):
    def test_extra_field_is_refused(self):
        base = {"kind": "reader", "what": "record x の原本", "bytes": 10, "model": "m", "demo": False}
        for extra in ("api_key", "body", "image", "text"):
            with self.assertRaises(ValueError):
                self.v.log_claude(dict(base, **{extra: "x"}))
        self.assertEqual(self.v.get_claude_log(), [])


class N_Export(_Base):
    def _populate(self):
        rid = self.v.add_record("もも", "image/png", PNG)
        self.v.set_derived(rid, "# もも\n", {"model": "m"})
        self.v.add_annotation(rid, "メモ")
        return rid

    def _rebuild_without(self, zip_path, member):
        out = zip_path + ".new"
        with zipfile.ZipFile(zip_path) as zin, zipfile.ZipFile(out, "w") as zout:
            for n in zin.namelist():
                if n != member:
                    zout.writestr(n, zin.read(n))
        os.replace(out, zip_path)

    def test_removed_member_raises_mismatch(self):
        rid = self._populate()
        path, _ = self.v.export_zip(self.out)
        self._rebuild_without(path, "records/%s/derived.md" % rid)
        with self.assertRaises(storage.ExportCountMismatch):
            storage.verify_export_zip(path)

    def test_removed_original_json_raises_mismatch(self):
        rid = self._populate()
        path, _ = self.v.export_zip(self.out)
        self._rebuild_without(path, "records/%s/original.json" % rid)
        with self.assertRaises(storage.ExportCountMismatch):
            storage.verify_export_zip(path)

    def test_edited_manifest_raises_mismatch(self):
        self._populate()
        path, _ = self.v.export_zip(self.out)
        with zipfile.ZipFile(path) as z:
            m = json.loads(z.read("manifest.json").decode("utf-8"))
        m["counts"]["marks"] = 9
        out = path + ".new"
        with zipfile.ZipFile(path) as zin, zipfile.ZipFile(out, "w") as zout:
            for n in zin.namelist():
                zout.writestr(n, json.dumps(m) if n == "manifest.json" else zin.read(n))
        os.replace(out, path)
        with self.assertRaises(storage.ExportCountMismatch):
            storage.verify_export_zip(path)

    def test_out_dir_inside_vault_refused(self):
        with self.assertRaises(ValueError):
            self.v.export_zip(os.path.join(self.v.root, "inside"))


class T_Original(_Base):
    def test_sha256_matches_and_meta_written(self):
        rid = self.v.add_record("もも", "image/jpeg", JPG, "2026-11-06T18:00:00+09:00")
        meta = self.v.get_record(rid)["original"]
        self.assertEqual(meta["sha256"], contract.sha256_hex(JPG))
        self.assertEqual(meta["bytes"], len(JPG))
        self.assertEqual(meta["media_type"], "image/jpeg")
        self.assertEqual(meta["record_name"], "もも")
        self.assertTrue(_original_file(self.v, rid).endswith("original.jpg"))
        self.assertTrue(self.v.verify_original(rid))

    def test_extensions(self):
        for mt, ext in (("image/jpeg", "jpg"), ("image/png", "png"), ("image/webp", "webp"), ("image/svg+xml", "svg")):
            rid = self.v.add_record("n", mt, b"abc")
            self.assertTrue(_original_file(self.v, rid).endswith("." + ext))

    def test_annotation_keeps_original_fingerprint(self):
        rid = self.v.add_record("もも", "image/png", PNG)
        before = open(_original_file(self.v, rid), "rb").read()
        before_meta = self.v.get_record(rid)["original"]
        e = self.v.add_annotation(rid, "ひとこと")
        self.v.add_annotation(rid, "ふたこと")
        self.assertEqual(e["author"], "person")
        self.assertRegex(e["written_at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+09:00$")
        self.assertEqual(open(_original_file(self.v, rid), "rb").read(), before)
        self.assertEqual(self.v.get_record(rid)["original"], before_meta)
        self.assertTrue(self.v.verify_original(rid))
        self.assertEqual(len(self.v.get_record(rid)["annotations"]), 2)

    def test_derived_md_head_lines_and_json(self):
        rid = self.v.add_record("もも", "image/png", PNG)
        md = "# もも\n\n- ひとつめ\n"
        self.v.set_derived(rid, md, {"model": "dummy-model", "prompt_sha256": "a" * 64, "demo": True})
        d = os.path.join(self.v.root, "records", rid)
        lines = open(os.path.join(d, "derived.md"), encoding="utf-8").read().split("\n")
        self.assertEqual(lines[0], contract.DERIVED_LABEL)
        self.assertEqual(lines[1], "original_sha256: " + contract.sha256_hex(PNG))
        self.assertEqual(lines[2], "")
        self.assertEqual("\n".join(lines[3:]), md)
        dj = json.load(open(os.path.join(d, "derived.json"), encoding="utf-8"))
        self.assertEqual(dj["label"], contract.DERIVED_LABEL)
        self.assertEqual(dj["sha256"], contract.sha256_hex(md.encode("utf-8")))
        self.assertEqual((dj["model"], dj["prompt_sha256"], dj["demo"]), ("dummy-model", "a" * 64, True))
        self.assertIn("generated_at", dj)
        self.assertEqual(self.v.get_record(rid)["derived"]["markdown"], md)

    def test_subject_and_delete(self):
        rid = self.v.add_record("もも", "image/png", PNG)
        self.v.set_subject(rid, {"author_role": "学校", "written_at": "2026-03-31", "procedure": "記録", "confirmed_by_person": False})
        self.assertEqual(self.v.get_record(rid)["subject"]["confirmed_by_person"], False)
        self.v.delete_record(rid)
        self.assertEqual(self.v.list_records(), [])
        self.assertFalse(os.path.exists(os.path.join(self.v.root, "records", rid)))
        self.assertEqual(self.v.counts()["originals"], 0)

    def test_list_records_newest_first(self):
        a = self.v.add_record("a", "image/png", PNG)
        self.assertEqual([r["record_id"] for r in self.v.list_records()], [a])


class T_Practice(_Base):
    def test_summary_by_condition(self):
        c1 = {"amount": "少なく", "split": True, "topic_free": False}
        c2 = {"amount": "ふつう", "split": False, "topic_free": False}
        t1 = self.v.add_turn(c1, "ぶん1", "ぶん1", "どんな？", None)
        t2 = self.v.add_turn(c1, "ぶん2", "ぶん2", None, "too_long")
        t3 = self.v.add_turn(c2, "ぶん3", "ぶん3", None, None)
        self.v.add_mark(t1, "残った"); self.v.add_mark(t2, "残った"); self.v.add_mark(t3, "なし")
        s = self.v.practice_summary()
        self.assertEqual(s, {"amount=少なく|split=true|topic_free=false": {"残った": 2},
                             "amount=ふつう|split=false|topic_free=false": {"なし": 1}})
        self.assertEqual(self.v.counts()["marks"], 3)
        self.assertEqual(self.v.get_turn(t2)["question_dropped_reason"], "too_long")


class T_Counts(_Base):
    def _build(self):
        r1 = self.v.add_record("もも", "image/png", PNG)
        r2 = self.v.add_record("りんご", "image/jpeg", JPG)
        self.v.set_derived(r1, "# もも\n", {})
        self.v.set_subject(r1, {"author_role": "学校", "written_at": "2026-03-31", "procedure": "記録", "confirmed_by_person": True})
        for t in ("あ", "い"):
            self.v.add_annotation(r1, t)
        self.v.add_annotation(r2, "う")
        c = {"amount": "少なく", "split": True, "topic_free": True}
        for _ in range(2):
            self.v.add_mark(self.v.add_turn(c, "ぶん", "ぶん"), "一部")
        sid = self.v.save_statement({"text": "ぶん", "finalized_at": None, "sections": {}})
        b = vector_v1()
        rc = dict(receipt_for(b)); rc["status"] = contract.receipt_status(contract.fingerprint(b), rc)
        self.v.save_handoff(b, rc)
        self.v.save_reply(reply_v1(True))
        return sid, r1, r2

    EXPECTED = {"originals": 2, "derived": 1, "annotations": 3, "subject_fields": 1,
                "marks": 2, "statements": 1, "handoffs": 1, "replies": 1}

    def test_eight_keys_counted(self):
        self._build()
        self.assertEqual(self.v.counts(), self.EXPECTED)
        self.assertEqual(self.v.read_manifest()["counts"], self.EXPECTED)
        self.assertEqual(self.v.read_manifest()["export_version"], "cip-export-v1")

    def test_manifest_follows_every_write(self):
        self.assertEqual(self.v.read_manifest()["counts"], {k: 0 for k in contract.EXPORT_COUNT_KEYS})
        rid = self.v.add_record("もも", "image/png", PNG)
        self.assertEqual(self.v.read_manifest()["counts"]["originals"], 1)
        self.v.add_annotation(rid, "x")
        self.assertEqual(self.v.read_manifest()["counts"]["annotations"], 1)
        self.v.delete_record(rid)
        self.assertEqual(self.v.read_manifest()["counts"]["annotations"], 0)

    def test_export_count_equals_manifest(self):
        self._build()
        self.v.save_pairing({"port_id": "port-x", "port_name": "受け口"}, {"token": "dummy"})
        path, counts = self.v.export_zip(os.path.join(self.dir, "out"))
        self.assertRegex(os.path.basename(path), r"^export_\d{4}-\d\d-\d\d_\d{6}(_\d+)?\.zip$")
        self.assertEqual(counts, self.EXPECTED)
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            self.assertEqual(json.loads(z.read("manifest.json").decode("utf-8"))["counts"], counts)
        self.assertNotIn(storage.SECRET_NAME, names)
        self.assertIn("pairing.json", names)
        self.assertEqual(storage.verify_export_zip(path), self.EXPECTED)

    def test_export_original_bytes_are_same(self):
        rid = self.v.add_record("もも", "image/png", PNG)
        path, _ = self.v.export_zip(os.path.join(self.dir, "out"))
        with zipfile.ZipFile(path) as z:
            self.assertEqual(z.read("records/%s/original.png" % rid), PNG)

    def test_wipe_sets_everything_to_zero(self):
        self._build()
        self.v.log_claude({"kind": "reader", "what": "record x の原本", "bytes": 3, "model": "m", "demo": True})
        self.v.save_pairing({"port_id": "p"}, {"token": "dummy"})
        self.v.wipe()
        self.assertEqual(self.v.counts(), {k: 0 for k in contract.EXPORT_COUNT_KEYS})
        self.assertEqual(self.v.read_manifest()["counts"], {k: 0 for k in contract.EXPORT_COUNT_KEYS})
        self.assertEqual(os.listdir(self.v.root), ["manifest.json"])
        self.assertEqual(self.v.list_records(), [])
        rid = self.v.add_record("もも", "image/png", PNG)   # wipe の後も使える
        self.assertTrue(self.v.verify_original(rid))

    def test_reopen_sees_same_data(self):
        self._build()
        again = storage.open_vault(self.v.root)
        self.assertEqual(again.counts(), self.EXPECTED)


class T_Statements_Handoffs(_Base):
    def test_statements_newest_first_and_get(self):
        a = self.v.save_statement({"text": "ひとつめ"})
        b = self.v.save_statement({"text": "ふたつめ", "item_id": "st-given"})
        self.assertEqual(b, "st-given")
        os.utime(os.path.join(self.v.root, "statements", a + ".json"), ns=(1, 1))
        self.assertEqual([s["text"] for s in self.v.list_statements()], ["ふたつめ", "ひとつめ"])
        self.assertEqual(self.v.get_statement(a)["item_id"], a)
        self.assertIsNone(self.v.get_statement("st-none"))

    def test_handoff_files_and_unsent(self):
        b = vector_v1()
        self.v.save_handoff(b, None)
        h = self.v.list_handoffs()
        self.assertEqual(h[0]["receipt"], {"status": "unsent"})
        self.assertEqual(h[0]["bundle"]["fingerprint"], b["fingerprint"])
        rc = dict(receipt_for(b), status="confirmed")
        self.v.save_handoff(b, rc)
        self.assertEqual(self.v.list_handoffs()[0]["receipt"]["status"], "confirmed")
        self.assertEqual(self.v.counts()["handoffs"], 1)

    def test_reply_default_unread_then_bound_then_discarded(self):
        rp = reply_v1(True)
        row = self.v.save_reply(rp)
        self.assertEqual(row["disposition"], "unread")
        self.assertEqual(rp.get("disposition"), None)   # 呼び出し側の辞書は変えない
        self.v.set_reply_disposition(rp["reply_id"], "bound", "rec-1")
        again = self.v.save_reply(rp)                     # 読み直しで同じ返事が来ても戻さない
        self.assertEqual((again["disposition"], again["bound_record_id"]), ("bound", "rec-1"))
        self.v.set_reply_disposition(rp["reply_id"], "discarded")
        self.assertNotIn("bound_record_id", self.v.list_replies()[0])
        self.assertEqual(self.v.counts()["replies"], 1)

    def test_claude_log_appends_without_secrets(self):
        e = {"kind": "listener", "what": "turn x の文", "bytes": 12, "model": "dummy-model", "demo": False}
        self.v.log_claude(e); self.v.log_claude(dict(e, kind="arranger", demo=True))
        log = self.v.get_claude_log()
        self.assertEqual([r["kind"] for r in log], ["listener", "arranger"])
        self.assertEqual(set(log[0]), set(storage.CLAUDE_LOG_KEYS))

    def test_pairing_roundtrip(self):
        self.v.save_pairing({"port_id": "p", "port_name": "受け口"}, {"token": "dummy"})
        self.assertEqual(self.v.get_pairing()["port_id"], "p")
        self.assertEqual(self.v.get_pairing_secret(), {"token": "dummy"})


class T_Format(_Base):
    def test_json_style_and_no_temp_leftovers(self):
        rid = self.v.add_record("もも", "image/png", PNG)
        text = open(os.path.join(self.v.root, "records", rid, "original.json"), encoding="utf-8").read()
        self.assertIn("もも", text)                    # ensure_ascii=False
        self.assertIn('\n "media_type"', text)         # インデント 1
        for base, _d, files in os.walk(self.v.root):
            for f in files:
                self.assertFalse(f.endswith(".tmp"), f)
