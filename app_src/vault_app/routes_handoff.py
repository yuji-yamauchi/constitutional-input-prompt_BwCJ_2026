# -*- coding: utf-8 -*-
"""vault_app/routes_handoff.py - 渡す口。全部 require_login の後。

- 束は「本人が選んだ物だけ」で作る（parts は選んだ物だけ・最終版の意思表出文は必ず入る）。
- 送る前に contract.validate_bundle を自分で通す（通らなければ送らない）。
- 控えの指紋と自分の指紋を比べて confirmed / unconfirmed を控えに足す。
- 送れなかったときは何も保存しない（束は作り直せる）。
"""
import base64
import copy
import os
import re

from app_src.common import contract, ids
from app_src.common.httpkit import HttpError
from app_src.vault_app import handoff, law
from app_src.vault_app.auth import require_login

ALL_PARTS = ("original", "derived", "subject_fields", "annotations")
PART_NAMES = {"original": "原本", "derived": "写し", "subject_fields": "主語の欄", "annotations": "注記"}
PROCEDURE_REPLY = "受け口からの返事"
MAX_NAME_CHARS = 60
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")

D_BAD_BODY = "送られた 形が 正しくありません。"
D_PAIR_FAILED = "つなげませんでした。合言葉を たしかめてください。"
D_HANDOFF_FAILED = "わたせませんでした。器の中身は そのままです。"
D_NO_PORT = "つなぎ先が 決まっていません。"
D_NOT_PAIRED = "先に つないでください。"
D_NO_STATEMENT = "意思表出文が 見つかりません。"
D_NOT_FINAL = "最終版に してから わたします。"
D_NO_RECORD = "記録が 見つかりません。"
D_BAD_PARTS = "わたす物の 選びが 正しくありません。"
D_PART_MISSING = "選んだ物が まだ ありません。"
D_ORIGINAL_CHANGED = "原本が 変わっています。わたせません。"
D_TOO_MANY = "品目が 多すぎます。分けて わたしてください。"
D_TOO_LARGE = "大きすぎます。分けて わたしてください。"
D_STATUTE_UNKNOWN = "法令集に ない 条が 含まれています。"
D_BUNDLE_INVALID = "束の 形が 正しくありません。わたしません。"
D_PREVIEW_CHANGED = "たしかめた 中身と 変わっています。もういちど たしかめてください。"
D_REPLIES_FAILED = "返事を よみこめませんでした。"


def _body(req):
    b = req.json()
    if not isinstance(b, dict):
        raise HttpError(400, "bad_request", D_BAD_BODY)
    return b


def _client(app):
    pc = handoff.get_port_client(app)
    if pc is None:
        raise HttpError(503, "port_unavailable", D_NO_PORT)
    return pc


# ---------------------------------------------------------------- つなぐ
def h_pair(req):
    require_login(req)
    app = req.app
    code = _body(req).get("pairing_code")
    if not isinstance(code, str) or code.strip() == "" or len(code) > 128:
        raise HttpError(400, "bad_request", D_BAD_BODY)
    pc = _client(app)
    try:
        status, obj = pc.pair(code.strip())
    except handoff.PortError:
        raise HttpError(502, "pair_failed", D_PAIR_FAILED) from None
    if status == 401:
        raise HttpError(401, "pair_failed", D_PAIR_FAILED)
    ok = (status == 200 and isinstance(obj, dict)
          and all(isinstance(obj.get(k), str) and obj.get(k) for k in ("person_ref", "token", "port_id", "port_name")))
    if not ok:
        raise HttpError(502, "pair_failed", D_PAIR_FAILED)
    app.vault.save_pairing(
        {"port_id": obj["port_id"], "port_name": obj["port_name"], "person_ref": obj["person_ref"],
         "paired_at": ids.now_jst(app.clock)},
        secret={"token": obj["token"]})
    return 200, {"port_id": obj["port_id"], "port_name": obj["port_name"]}


# ---------------------------------------------------------------- 束を作る
def _record_item(vault, spec):
    if not isinstance(spec, dict) or not isinstance(spec.get("record_id"), str):
        raise HttpError(400, "bad_parts", D_BAD_PARTS)
    rid = spec["record_id"]
    parts = spec.get("parts")
    if not isinstance(parts, list) or not parts or any(p not in ALL_PARTS for p in parts if isinstance(p, str)) \
            or any(not isinstance(p, str) for p in parts):
        raise HttpError(400, "bad_parts", D_BAD_PARTS)
    parts = [p for p in ALL_PARTS if p in parts]            # 重なりを除き、決まった順にする
    try:
        rec = vault.get_record(rid)
    except (KeyError, ValueError):
        raise HttpError(404, "not_found", D_NO_RECORD) from None
    out = {}
    if "original" in parts:
        if not vault.verify_original(rid):
            raise HttpError(409, "original_changed", D_ORIGINAL_CHANGED)
        raw, media = vault.read_original(rid)
        o = {"media_type": media, "sha256": contract.sha256_hex(raw), "bytes_base64": base64.b64encode(raw).decode("ascii")}
        if rec["original"].get("taken_at"):
            o["taken_at"] = rec["original"]["taken_at"]
        out["original"] = o
    if "derived" in parts:
        d = rec.get("derived")
        if not d:
            raise HttpError(400, "part_missing", D_PART_MISSING)
        out["derived"] = {          # 札の行は storage が付けた物 = markdown には入っていない
            "label": contract.DERIVED_LABEL,
            "markdown": d["markdown"],
            "generated_at": d["generated_at"],
            "sha256": contract.sha256_hex(d["markdown"].encode("utf-8")),
        }
    if "subject_fields" in parts:
        s = rec.get("subject")
        if not s:
            raise HttpError(400, "part_missing", D_PART_MISSING)
        out["subject_fields"] = {k: s[k] for k in ("author_role", "written_at", "procedure", "confirmed_by_person")}
    if "annotations" in parts:
        a = rec.get("annotations") or []
        if not a:
            raise HttpError(400, "part_missing", D_PART_MISSING)
        out["annotations"] = [{"text": x["text"], "written_at": x["written_at"], "author": x["author"]} for x in a]
    name = (rec["original"].get("record_name") or "").strip() or "名前なし"
    return {"kind": "record", "item_id": rid, "record_name": name, "parts": out}


def build_bundle(app, body):
    """(束, 一覧の行)。送らない。"""
    vault = app.vault
    sid = body.get("statement_id")
    if not isinstance(sid, str):
        raise HttpError(400, "bad_request", D_BAD_BODY)
    try:
        st = vault.get_statement(sid)
    except ValueError:
        st = None
    if st is None:
        raise HttpError(404, "not_found", D_NO_STATEMENT)
    if not st.get("finalized_at"):
        raise HttpError(400, "statement_not_final", D_NOT_FINAL)
    pairing = vault.get_pairing()
    if not isinstance(pairing, dict) or not pairing.get("person_ref") or not pairing.get("port_id"):
        raise HttpError(400, "not_paired", D_NOT_PAIRED)
    name = body.get("display_name", "")
    if not isinstance(name, str) or len(name) > MAX_NAME_CHARS:
        raise HttpError(400, "bad_request", D_BAD_BODY)
    specs = body.get("records", [])
    if not isinstance(specs, list):
        raise HttpError(400, "bad_parts", D_BAD_PARTS)
    if 1 + len(specs) > contract.MAX_ITEMS:
        raise HttpError(400, "too_many", D_TOO_MANY)
    seen = set()
    rec_items = []
    for spec in specs:
        it = _record_item(vault, spec)
        if it["item_id"] in seen:
            raise HttpError(400, "bad_parts", D_BAD_PARTS)
        seen.add(it["item_id"])
        rec_items.append(it)
    # 意思表出文（最終版）
    sec = st.get("sections") or {}
    corpus = law.for_app(app)
    statutes = []
    for lid in sec.get("statute_ids", []):
        s = corpus.statute_for_bundle(lid)
        if s is None:
            raise HttpError(400, "statute_unknown", D_STATUTE_UNKNOWN)
        statutes.append(s)
    sections = {}
    if sec.get("trouble"):
        sections["trouble"] = sec["trouble"]
    if sec.get("wish"):
        sections["wish"] = sec["wish"]
    grounds = [g for g in sec.get("grounds", []) if g in seen]       # 同じ束の記録だけ
    if grounds:
        sections["grounds"] = grounds
    if statutes:
        sections["statutes"] = statutes
    st_item = {"kind": "statement", "item_id": st["item_id"], "author": "person",
               "finalized_at": st["finalized_at"], "text": st.get("text", ""), "sections": sections}
    items = [st_item] + rec_items
    bid = body.get("bundle_id")
    created = body.get("created_at")
    if bid is None:
        bid = ids.new_id("bd")
    elif not isinstance(bid, str) or not _ID_RE.match(bid) or os.path.isdir(os.path.join(vault.root, "handoffs", bid)):
        raise HttpError(400, "bad_request", D_BAD_BODY)
    if created is None:
        created = ids.now_jst(app.clock)
    else:
        dt = ids.parse_iso(created) if isinstance(created, str) else None
        if dt is None or dt.tzinfo is None:
            raise HttpError(400, "bad_request", D_BAD_BODY)
    bundle = {
        "bundle_version": contract.BUNDLE_VERSION,
        "bundle_id": bid,
        "created_at": created,
        "sender": {"person_ref": pairing["person_ref"], "display_name": name.strip()},
        "recipient": {"port_id": pairing["port_id"], "port_name": pairing.get("port_name", "")},
        "items": items,
        "item_count": len(items),
    }
    bundle["fingerprint"] = contract.fingerprint(bundle)
    if len(contract.canonical_json(bundle)) > contract.MAX_BUNDLE_BYTES:
        raise HttpError(413, "too_large", D_TOO_LARGE)
    if contract.validate_bundle(bundle):
        raise HttpError(400, "bundle_invalid", D_BUNDLE_INVALID)      # 通らなければ送らない
    rows = [{"kind": "statement", "name": "意思表出文"}]
    for it in rec_items:
        rows.append({"kind": "record", "name": it["record_name"], "parts": [PART_NAMES[p] for p in ALL_PARTS if p in it["parts"]]})
    return bundle, rows


def h_preview(req):
    require_login(req)
    bundle, rows = build_bundle(req.app, _body(req))
    return 200, {
        "fingerprint": bundle["fingerprint"],
        "items": rows,
        "recipient": bundle["recipient"],
        "bundle_id": bundle["bundle_id"],       # わたすときに そのまま 返すと、たしかめた 指紋と 同じ束になる
        "created_at": bundle["created_at"],
    }


def h_send(req):
    require_login(req)
    app = req.app
    body = _body(req)
    bundle, _rows = build_bundle(app, body)
    expected = body.get("expected_fingerprint")
    if expected is not None and expected != bundle["fingerprint"]:
        raise HttpError(409, "preview_changed", D_PREVIEW_CHANGED)
    pc = _client(app)
    try:
        status, obj = pc.post_bundle(bundle)
    except handoff.PortError:
        raise HttpError(502, "handoff_failed", D_HANDOFF_FAILED) from None
    if status not in (200, 201) or not isinstance(obj, dict):
        raise HttpError(502, "handoff_failed", D_HANDOFF_FAILED)
    receipt = dict(obj)
    own = bundle["fingerprint"]
    if contract.validate_receipt(receipt) or receipt.get("bundle_id") != bundle["bundle_id"]:
        receipt["status"] = "unconfirmed"
    else:
        receipt["status"] = contract.receipt_status(own, receipt)
    app.vault.save_handoff(bundle, receipt)
    return 201, {"bundle_id": bundle["bundle_id"], "fingerprint": own, "receipt": receipt}


def _strip_bytes(row):
    r = copy.deepcopy(row)
    for it in (r.get("bundle") or {}).get("items", []):
        o = (it.get("parts") or {}).get("original")
        if isinstance(o, dict):
            o.pop("bytes_base64", None)
    return r


def h_list(req):
    require_login(req)
    return 200, {"handoffs": [_strip_bytes(r) for r in req.app.vault.list_handoffs()]}


# ---------------------------------------------------------------- 返事
def _clean_reply(rp):
    """既知の欄だけを写す。人の印は**そのまま**写す（無い・false・字の "true"・1 も残す）＝画面の札は
    contract.reply_author_label が決める（JSON の true だけ「メンター（人）」・それ以外は「不明」＝取り決め）。
    黙って捨てると本人に見えないので、形が最低限 読める返事は全部 残す。"""
    a = rp.get("author") if isinstance(rp.get("author"), dict) else {}
    author = {"role": a.get("role", "")}
    if "human_attestation" in a:
        author["human_attestation"] = a["human_attestation"]
    if "attested_at" in a:
        author["attested_at"] = a["attested_at"]
    return {
        "reply_version": rp.get("reply_version", ""), "reply_id": rp["reply_id"],
        "port_id": rp.get("port_id", ""), "port_name": rp.get("port_name", ""), "in_reply_to": rp["in_reply_to"],
        "text": rp["text"], "written_at": rp["written_at"],
        "author": author,
    }


_REPLY_MIN_KEYS = ("reply_id", "in_reply_to", "text", "written_at")


def _reply_readable(rp):
    return isinstance(rp, dict) and all(isinstance(rp.get(k), str) and rp.get(k) != "" for k in _REPLY_MIN_KEYS)


def h_refresh(req):
    require_login(req)
    app = req.app
    if not isinstance(app.vault.get_pairing(), dict):
        raise HttpError(400, "not_paired", D_NOT_PAIRED)
    pc = _client(app)
    have = app.vault.list_replies()
    existing = set(r.get("reply_id") for r in have)
    since = max((r.get("written_at") or "" for r in have), default="") or None
    try:
        status, obj = pc.get_replies(since)
    except handoff.PortError:
        raise HttpError(502, "replies_failed", D_REPLIES_FAILED) from None
    if status != 200 or not isinstance(obj, dict) or not isinstance(obj.get("replies"), list):
        raise HttpError(502, "replies_failed", D_REPLIES_FAILED)
    new = 0
    for rp in obj["replies"]:
        if not _reply_readable(rp):     # 読めない物だけ捨てる（印の形の違いでは捨てない＝「不明」で見せる）
            continue
        try:
            row = _clean_reply(rp)
            was = row["reply_id"] in existing
            app.vault.save_reply(row)
        except (ValueError, TypeError, KeyError):
            continue
        if not was:
            existing.add(row["reply_id"])
            new += 1
    return 200, {"new": new}


ROUTES = [
    ("POST", "/api/pair", h_pair),
    ("POST", "/api/handoffs/preview", h_preview),
    ("POST", "/api/handoffs", h_send),
    ("GET", "/api/handoffs", h_list),
    ("POST", "/api/replies/refresh", h_refresh),
]
