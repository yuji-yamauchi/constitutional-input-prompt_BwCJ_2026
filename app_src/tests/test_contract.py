# -*- coding: utf-8 -*-
"""取り決めの検査器（陰性対照 12・本物 7）を unittest に写す＋返事の形＋禁じる言い方の走査（words）。
N_ で始まるクラス＝陰性対照（先に回る）。T_ で始まるクラス＝本物。"""
import copy, json, unittest

from app_src.common import contract, words
from app_src.common.vector import (
    EXPECTED_V1_FINGERPRINT, vector_v1, receipt_for, reply_v1,
)

ZERO_COUNTS = {k: 0 for k in contract.EXPORT_COUNT_KEYS}


def _counts(**over):
    c = {"originals": 1, "derived": 1, "annotations": 1, "subject_fields": 1,
         "marks": 2, "statements": 1, "handoffs": 1, "replies": 1}
    c.update(over)
    return c


class N_Contract(unittest.TestCase):
    def setUp(self):
        self.b = vector_v1()
        self.fp = contract.fingerprint(self.b)

    def test_n01_one_char_changes_fingerprint(self):
        n = copy.deepcopy(self.b); n["items"][0]["text"] += "。"
        self.assertNotEqual(contract.fingerprint(n), self.fp)

    def test_n02_forged_fingerprint_fails(self):
        n = copy.deepcopy(self.b); n["fingerprint"] = "0" * 64
        self.assertTrue(any("fingerprint_mismatch" in e for e in contract.validate_bundle(n)))

    def test_n03_missing_original_sha256_fails(self):
        n = copy.deepcopy(self.b); del n["items"][1]["parts"]["original"]["sha256"]
        self.assertTrue(len(contract.validate_bundle(n)) > 0)

    def test_n04_wrong_derived_label_fails(self):
        n = copy.deepcopy(self.b); n["items"][1]["parts"]["derived"]["label"] = "要約"
        self.assertTrue(any("決まりの字と違う" in e for e in contract.validate_bundle(n)))

    def test_n05_annotation_author_not_person_fails(self):
        n = copy.deepcopy(self.b); n["items"][1]["parts"]["annotations"][0]["author"] = "mentor"
        self.assertTrue(any("注記" in e for e in contract.validate_bundle(n)))

    def test_n06_item_count_mismatch_fails(self):
        n = copy.deepcopy(self.b); n["item_count"] = 9
        self.assertTrue(any("item_count" in e for e in contract.validate_bundle(n)))

    def test_n07_no_attestation_is_unknown(self):
        self.assertEqual(contract.reply_author_label(reply_v1(attest=None)), "不明")

    def test_n08_false_attestation_is_unknown(self):
        self.assertEqual(contract.reply_author_label(reply_v1(attest=False)), "不明")

    def test_n09_string_true_attestation_is_unknown(self):
        self.assertEqual(contract.reply_author_label(reply_v1(attest="true")), "不明")

    def test_n10_wrong_receipt_fingerprint_is_unconfirmed(self):
        rc = receipt_for(self.b); rc["bundle_fingerprint"] = "f" * 64
        self.assertEqual(contract.receipt_status(self.fp, rc), "unconfirmed")

    def test_n11_export_count_mismatch_fails(self):
        self.assertIs(contract.export_manifest_ok({"counts": _counts(marks=3)}, _counts(marks=2)), False)

    def test_n12_float_refused_by_canonical_json(self):
        with self.assertRaises(ValueError):
            contract.canonical_json({"a": 1.5})


class N_Reply(unittest.TestCase):
    def test_string_true_attestation_fails_shape(self):
        self.assertTrue(len(contract.validate_reply(reply_v1(attest="true"))) > 0)

    def test_missing_attestation_fails_shape(self):
        self.assertTrue(any("human_attestation" in e for e in contract.validate_reply(reply_v1(attest=None))))

    def test_wrong_version_fails_shape(self):
        rp = reply_v1(True); rp["reply_version"] = "cip-reply-v0"
        self.assertTrue(len(contract.validate_reply(rp)) > 0)

    def test_not_a_dict_fails_shape(self):
        self.assertTrue(len(contract.validate_reply([])) > 0)


class N_Words(unittest.TestCase):
    def test_forbidden_verb_detected(self):
        self.assertTrue(words.scan("この記録を評価する"))

    def test_grade_word_detected(self):
        self.assertTrue(words.scan("レベルが 上がった"))

    def test_digit_ten_detected(self):
        self.assertTrue(words.scan("80点"))

    def test_nudge_detected(self):
        self.assertTrue(words.scan("続きをどうぞ"))

    def test_undecided_detected(self):
        self.assertTrue(words.scan("スキルアップ"))

    def test_exception_does_not_hide_other_word(self):
        hits = words.scan("診断書を 評価する")
        self.assertEqual([h[1] for h in hits], ["評価する"])

    def test_kinds_filter_limits_result(self):
        self.assertEqual(words.scan("毎日 評価する", kinds=["nudge"])[0][:2], ("nudge", "毎日"))
        self.assertEqual(len(words.scan("毎日 評価する", kinds=["nudge"])), 1)


class T_Contract(unittest.TestCase):
    def setUp(self):
        self.b = vector_v1()
        self.fp = contract.fingerprint(self.b)

    def test_t01_v1_passes_shape_check(self):
        self.assertEqual(contract.validate_bundle(self.b), [])

    def test_t02_v1_fingerprint_is_fixed_value(self):
        self.assertEqual(self.fp, EXPECTED_V1_FINGERPRINT)

    def test_t03_receipt_shape_passes(self):
        self.assertEqual(contract.validate_receipt(receipt_for(self.b)), [])

    def test_t04_correct_receipt_is_confirmed(self):
        self.assertEqual(contract.receipt_status(self.fp, receipt_for(self.b)), "confirmed")

    def test_t05_true_attestation_is_mentor_person(self):
        self.assertEqual(contract.reply_author_label(reply_v1(True)), "メンター（人）")

    def test_t06_matching_counts_ok(self):
        self.assertTrue(contract.export_manifest_ok({"counts": _counts()}, _counts()))

    def test_t07_canonical_json_is_stable(self):
        again = json.loads(json.dumps(self.b, ensure_ascii=False))
        self.assertEqual(contract.canonical_json(self.b), contract.canonical_json(again))

    def test_derived_label_is_fixed_text(self):
        self.assertEqual(contract.DERIVED_LABEL, "派生（Claude が読み取った写し。原本が正）")


class T_Reply(unittest.TestCase):
    def test_true_attestation_passes_shape(self):
        self.assertEqual(contract.validate_reply(reply_v1(True)), [])

    def test_false_attestation_passes_shape_but_is_unknown(self):
        rp = reply_v1(False)
        self.assertEqual(contract.validate_reply(rp), [])
        self.assertEqual(contract.reply_author_label(rp), "不明")


class T_Words(unittest.TestCase):
    def test_document_names_are_exceptions(self):
        for s in ("診断書を しまう", "通知表", "意見書と 個別支援計画", "母子手帳", "診療情報提供書"):
            self.assertEqual(words.scan(s), [], s)

    def test_ten_in_ordinary_words_is_not_hit(self):
        for s in ("点線を ひく", "要点を まとめる", "句読点"):
            self.assertEqual(words.scan(s), [], s)

    def test_position_is_kept_after_exception_masking(self):
        hits = words.scan("診断書と 毎日")
        self.assertEqual(hits, [("nudge", "毎日", 5)])

    def test_is_clean(self):
        self.assertTrue(words.is_clean("きょうは 写真を 一枚 入れた。"))
        self.assertFalse(words.is_clean("通知"))

    def test_notice_table_is_not_a_nudge(self):
        self.assertTrue(words.is_clean("通知表を 入れる"))
