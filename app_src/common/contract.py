# -*- coding: utf-8 -*-
"""common/contract.py — 渡す口の取り決め（V1）の共通モジュール。外部ライブラリ 0。

器（vault_app）と受け口（receiver_app）の両方がこの 1 本を使う＝同じ正規化・同じ指紋。
元＝取り決めの自己検査スクリプトの形と検査をそのまま移した（挙動は同じ・V1 の指紋も同じ）。
"""
import json, hashlib, base64

ITEM_KINDS = ("statement", "record")
DERIVED_LABEL = "派生（Claude が読み取った写し。原本が正）"
BUNDLE_VERSION = "cip-bundle-v1"
RECEIPT_VERSION = "cip-receipt-v1"
REPLY_VERSION = "cip-reply-v1"
EXPORT_VERSION = "cip-export-v1"
MAX_ORIGINAL_BYTES = 5 * 1024 * 1024
MAX_BUNDLE_BYTES = 25 * 1024 * 1024
MAX_ITEMS = 50
EXPORT_COUNT_KEYS = ["originals", "derived", "annotations", "subject_fields", "marks", "statements", "handoffs", "replies"]
STATUTE_FIELDS = ["law_name", "article", "text_verbatim", "source_name", "retrieved_on", "retrieved_by", "set_version"]



def _check_numbers(o, path="$"):
    if isinstance(o, bool) or o is None or isinstance(o, str):
        return
    if isinstance(o, float):
        raise ValueError("float は禁止（整数か文字列にする）: " + path)
    if isinstance(o, int):
        return
    if isinstance(o, list):
        for i, v in enumerate(o):
            _check_numbers(v, "%s[%d]" % (path, i))
        return
    if isinstance(o, dict):
        for k, v in o.items():
            if not isinstance(k, str):
                raise ValueError("キーは文字列だけ: " + path)
            _check_numbers(v, path + "." + k)
        return
    raise ValueError("許さない型: " + path)


def canonical_json(obj):
    """正規化した JSON の bytes（UTF-8）。"""
    _check_numbers(obj)
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def fingerprint(bundle):
    b = {k: v for k, v in bundle.items() if k != "fingerprint"}
    return hashlib.sha256(canonical_json(b)).hexdigest()


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()

# ---- 形の検査（必須の欄と型だけ・値の意味は見ない）----



def _req(d, keys, where, errs):
    for k in keys:
        if k not in d:
            errs.append("%s: 欄が無い %s" % (where, k))


def validate_bundle(b):
    errs = []
    if not isinstance(b, dict):
        return ["束が辞書でない"]
    _req(b, ["bundle_version", "bundle_id", "created_at", "sender", "recipient", "items", "item_count", "fingerprint"], "束", errs)
    if b.get("bundle_version") != "cip-bundle-v1":
        errs.append("束: bundle_version が cip-bundle-v1 でない")
    s = b.get("sender", {})
    if isinstance(s, dict):
        _req(s, ["person_ref", "display_name"], "束.sender", errs)
    else:
        errs.append("束.sender が辞書でない")
    r = b.get("recipient", {})
    if isinstance(r, dict):
        _req(r, ["port_id", "port_name"], "束.recipient", errs)
    else:
        errs.append("束.recipient が辞書でない")
    items = b.get("items")
    if not isinstance(items, list) or len(items) == 0:
        errs.append("束.items が空か配列でない")
        items = []
    if len(items) > MAX_ITEMS:
        errs.append("束.items が 50 を超える")
    if b.get("item_count") != len(items):
        errs.append("束.item_count が items の数と違う")
    for i, it in enumerate(items):
        w = "束.items[%d]" % i
        if not isinstance(it, dict):
            errs.append(w + " が辞書でない"); continue
        _req(it, ["kind", "item_id"], w, errs)
        k = it.get("kind")
        if k not in ITEM_KINDS:
            errs.append(w + ": kind が statement/record でない"); continue
        if k == "statement":
            _req(it, ["text", "finalized_at", "author", "sections"], w, errs)
            if it.get("author") != "person":
                errs.append(w + ": statement.author は person だけ")
            sec = it.get("sections", {})
            if isinstance(sec, dict):
                for st in sec.get("statutes", []) or []:
                    _req(st, STATUTE_FIELDS, w + ".statutes", errs)
        if k == "record":
            _req(it, ["record_name", "parts"], w, errs)
            parts = it.get("parts", {})
            if not isinstance(parts, dict) or len(parts) == 0:
                errs.append(w + ": parts が空（原本・派生・主語の欄・注記のどれか 1 つは要る）")
                parts = {}
            if "original" in parts:
                _req(parts["original"], ["media_type", "sha256", "bytes_base64"], w + ".original", errs)
                try:
                    raw = base64.b64decode(parts["original"]["bytes_base64"], validate=True)
                    if sha256_hex(raw) != parts["original"]["sha256"]:
                        errs.append(w + ".original: sha256 が中身と違う")
                    if len(raw) > MAX_ORIGINAL_BYTES:
                        errs.append(w + ".original: 5 MB を超える")
                except Exception:
                    errs.append(w + ".original: base64 が読めない")
            if "derived" in parts:
                _req(parts["derived"], ["label", "markdown", "generated_at", "sha256"], w + ".derived", errs)
                if parts["derived"].get("label") != DERIVED_LABEL:
                    errs.append(w + ".derived: 札の字が決まりの字と違う")
                if sha256_hex(parts["derived"].get("markdown", "").encode("utf-8")) != parts["derived"].get("sha256"):
                    errs.append(w + ".derived: sha256 が markdown と違う")
            if "subject_fields" in parts:
                _req(parts["subject_fields"], ["author_role", "written_at", "procedure", "confirmed_by_person"], w + ".subject_fields", errs)
                if not isinstance(parts["subject_fields"].get("confirmed_by_person"), bool):
                    errs.append(w + ".subject_fields: confirmed_by_person は true/false")
            if "annotations" in parts:
                for a in parts["annotations"]:
                    _req(a, ["text", "written_at", "author"], w + ".annotations", errs)
                    if a.get("author") != "person":
                        errs.append(w + ".annotations: author は person だけ（原本は変えない・注記は本人の行）")
    if "fingerprint" in b and errs == []:
        if b["fingerprint"] != fingerprint(b):
            errs.append("束.fingerprint が計算と違う（fingerprint_mismatch）")
    return errs


def validate_receipt(rc):
    errs = []
    _req(rc, ["receipt_version", "receipt_id", "port_id", "port_name", "bundle_id", "bundle_fingerprint", "item_count", "received_at"], "控え", errs)
    if rc.get("receipt_version") != "cip-receipt-v1":
        errs.append("控え: receipt_version が cip-receipt-v1 でない")
    return errs


def reply_author_label(rp):
    """返事の表示の札。人の印が JSON の true のときだけ『メンター（人）』。"""
    a = rp.get("author") if isinstance(rp, dict) else None
    if isinstance(a, dict) and a.get("human_attestation") is True:
        return "メンター（人）" if a.get("role") == "mentor" else "人（%s）" % a.get("role", "")
    return "不明"


def receipt_status(own_fp, rc):
    return "confirmed" if rc.get("bundle_fingerprint") == own_fp else "unconfirmed"


def export_manifest_ok(manifest, counted):
    """D1: manifest.counts の 8 種が、実際に数えた数と一致するか。"""
    keys = EXPORT_COUNT_KEYS
    c = manifest.get("counts", {})
    return all(k in c for k in keys) and all(c[k] == counted.get(k) for k in keys)


def validate_reply(rp):
    """返事の形（取り決め）。人の印の真偽は reply_author_label で見る＝ここでは欄の有無だけ。"""
    errs = []
    if not isinstance(rp, dict):
        return ["返事が辞書でない"]
    _req(rp, ["reply_version", "reply_id", "port_id", "port_name", "in_reply_to", "text", "written_at", "author"], "返事", errs)
    if rp.get("reply_version") != REPLY_VERSION:
        errs.append("返事: reply_version が cip-reply-v1 でない")
    a = rp.get("author")
    if not isinstance(a, dict):
        errs.append("返事.author が辞書でない")
    else:
        _req(a, ["role", "human_attestation", "attested_at"], "返事.author", errs)
        if not isinstance(a.get("human_attestation"), bool):
            errs.append("返事.author.human_attestation は JSON の真偽だけ")
    return errs

