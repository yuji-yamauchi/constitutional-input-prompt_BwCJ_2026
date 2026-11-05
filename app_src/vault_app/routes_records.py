# -*- coding: utf-8 -*-
"""vault_app/routes_records.py - B（自分の記録の引き出し）・返事を綴じる・持ち出し・全削除・Claude に送った物の一覧。

標準ライブラリだけ。ネットワークへ出るコードは無い（Claude を呼ぶのは app.claude の read_image だけ）。
全部の口が require_login の後。エラーは {"error","detail"}（HttpError）。
保存の形は storage.py のまま。storage に口が無い物（返事の綴じ・写しだけを消す・写真なしの控え）は、
この部品が器の中の records/<id>/ と catalog.json に最小の字だけを足す（原本・8 鍵の数え方には触らない）。
"""
import base64
import binascii
import hashlib
import importlib
import json
import os
import re
import threading

from app_src.common import contract, ids
from app_src.common.httpkit import HttpError, Response
from app_src.vault_app.auth import require_login
from app_src.vault_app import claude_client, storage

ALLOWED_MEDIA = ("image/jpeg", "image/png", "image/webp", "image/svg+xml")
MAX_NAME_CHARS = 200
MAX_FIELD_CHARS = 200
MAX_NOTE_CHARS = 4000
MAX_CATALOG_ITEMS = 500
CONFIRM_WIPE = "消します"
EXPORT_NAME_RE = re.compile(r"^export_[0-9A-Za-z_-]+\.zip$")
SUBJECT_FIELDS = ("author_role", "written_at", "procedure", "confirmed_by_person")
PROMPT_NAMES = ("reader", "listener", "arranger")
NO_NAME = "名前なし"

_catalog_lock = threading.Lock()


# ---------------------------------------------------------------- 小さな助け

def _vault(req):
    v = req.app.vault
    if v is None:
        raise HttpError(503, "not_configured", "設定が ありません。")
    return v


def _body(req):
    """本文なしは {}。あれば JSON の辞書。"""
    if int(req.headers.get("Content-Length") or 0) == 0:
        return {}
    b = req.json()
    if not isinstance(b, dict):
        raise HttpError(400, "bad_json", "字の形が正しくありません。")
    return b


def _read_json(path, default=None):
    try:
        with open(path, "rb") as f:
            return json.loads(f.read().decode("utf-8"))
    except FileNotFoundError:
        return default


def _write_json(path, obj):
    """一時ファイルに書いて入れ替える（途中で落ちても壊れない・権限は storage と同じ 0o600／0o700）。"""
    storage._write_json(path, obj)


def _not_found():
    return HttpError(404, "not_found", "記録が ありません。")


def _text_field(body, key, limit, required=False):
    v = body.get(key)
    if v is None:
        v = ""
    if not isinstance(v, str):
        raise HttpError(400, "bad_field", "字の形が正しくありません。")
    v = v.strip()
    if required and not v:
        raise HttpError(400, "empty_field", "空です。")
    if len(v) > limit:
        raise HttpError(400, "too_long", "長すぎます。")
    return v


# ---------------------------------------------------------------- 記録の見せ方

def _subject(rec):
    s = rec.get("subject") or {}
    return {
        "author_role": s.get("author_role") or "",
        "written_at": s.get("written_at") or "",
        "procedure": s.get("procedure") or "",
        "confirmed_by_person": bool(s.get("confirmed_by_person", False)),
    }


def _summary(rec):
    o = rec["original"]
    return {
        "record_id": rec["record_id"],
        "kind": "photo",
        "record_name": o.get("record_name"),
        "imported_at": o.get("imported_at"),
        "media_type": o.get("media_type"),
        "sha256": o.get("sha256"),
        "bytes": o.get("bytes"),
        "taken_at": o.get("taken_at"),
        "has_derived": rec.get("derived") is not None,
        "subject": _subject(rec),
        "annotations": rec.get("annotations") or [],
    }


def _detail(rec):
    out = _summary(rec)
    d = rec.get("derived")
    if d is None:
        out["derived_markdown"] = None
        out["derived_meta"] = None
    else:
        out["derived_markdown"] = d.get("markdown", "")
        out["derived_meta"] = {k: v for k, v in d.items() if k != "markdown"}
    return out


def _reply_label(reply):
    """返事の札は 2 つだけ。人の印が JSON の true で役が mentor のときだけ『メンター（人）』。"""
    label = contract.reply_author_label(reply)
    return label if label == "メンター（人）" else "不明"


def _find_reply(vault, reply_id):
    for r in vault.list_replies():
        if r.get("reply_id") == reply_id:
            return r
    return None


def _reply_meta_path(vault, rid):
    return os.path.join(vault.root, "records", rid, "reply.json")


def _reply_record(vault, row):
    rid = row.get("bound_record_id") or row.get("reply_id")
    meta = _read_json(_reply_meta_path(vault, rid), {}) or {}
    author = row.get("author") if isinstance(row.get("author"), dict) else {}
    name = meta.get("record_name") or ("返事（%s）" % (row.get("port_name") or ""))
    return {
        "record_id": rid,
        "kind": "reply",
        "record_name": name,
        "imported_at": meta.get("bound_at") or row.get("written_at"),
        "media_type": None,
        "sha256": None,
        "bytes": None,
        "taken_at": None,
        "has_derived": False,
        "subject": {
            "author_role": author.get("role") or "",
            "written_at": row.get("written_at") or "",
            "procedure": "受け口からの返事",
            "confirmed_by_person": True,
        },
        "annotations": _read_json(os.path.join(vault.root, "records", rid, "annotations.json"), []) or [],
        "author_label": _reply_label(row),
        "port_name": row.get("port_name"),
        "body": row.get("text") or "",
    }


def _bound_reply_records(vault):
    return [_reply_record(vault, r) for r in vault.list_replies() if r.get("disposition") == "bound"]


def _get_photo(vault, rid):
    try:
        return vault.get_record(rid)
    except (KeyError, ValueError):
        raise _not_found()


def _bound_reply_by_record(vault, rid):
    for r in vault.list_replies():
        if r.get("disposition") == "bound" and (r.get("bound_record_id") or r.get("reply_id")) == rid:
            return r
    return None


# ---------------------------------------------------------------- 記録

def list_records(req):
    require_login(req)
    v = _vault(req)
    rows = [_summary(r) for r in v.list_records()] + _bound_reply_records(v)
    rows.sort(key=lambda r: (r.get("imported_at") or "", r["record_id"]), reverse=True)
    return {"items": rows}


def get_record(req):
    require_login(req)
    v = _vault(req)
    rid = req.params["id"]
    try:
        return _detail(v.get_record(rid))
    except (KeyError, ValueError):
        row = _bound_reply_by_record(v, rid) if re.match(r"^[A-Za-z0-9_-]{1,128}$", rid) else None
        if row is None:
            raise _not_found()
        return _reply_record(v, row)


def get_original(req):
    require_login(req)
    v = _vault(req)
    _get_photo(v, req.params["id"])
    data, media_type = v.read_original(req.params["id"])
    return Response(200, data, media_type)


def add_record(req):
    require_login(req)
    v = _vault(req)
    body = req.json()
    if not isinstance(body, dict):
        raise HttpError(400, "bad_json", "字の形が正しくありません。")
    media_type = body.get("media_type")
    if media_type not in ALLOWED_MEDIA:
        raise HttpError(400, "bad_media_type", "この形の写真は 入れられません。")
    b64 = body.get("data_base64")
    if not isinstance(b64, str) or not b64:
        raise HttpError(400, "bad_base64", "写真を 読めませんでした。")
    if len(b64) > (contract.MAX_ORIGINAL_BYTES * 4) // 3 + 16:
        raise HttpError(413, "too_large", "5 MB を こえています。")
    try:
        data = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError):
        raise HttpError(400, "bad_base64", "写真を 読めませんでした。")
    if len(data) == 0:
        raise HttpError(400, "bad_base64", "写真を 読めませんでした。")
    if len(data) > contract.MAX_ORIGINAL_BYTES:
        raise HttpError(413, "too_large", "5 MB を こえています。")
    name = _text_field(body, "record_name", MAX_NAME_CHARS) or NO_NAME
    taken_at = body.get("taken_at")
    if taken_at is None or taken_at == "":
        taken_at = ids.now_jst(req.app.clock)
    if not isinstance(taken_at, str) or len(taken_at) > 64:
        raise HttpError(400, "bad_field", "字の形が正しくありません。")
    rid = v.add_record(name, media_type, data, taken_at)
    return (201, {"record_id": rid, "sha256": contract.sha256_hex(data)})


def _claude(app):
    """app.claude。まだ無ければ、在る部品に作ってもらう（無ければ None）。"""
    if app.claude is not None:
        return app.claude
    full = "app_src.vault_app.claude_client"
    try:
        mod = importlib.import_module(full)
    except ImportError as e:
        if getattr(e, "name", None) == full:
            return None
        raise
    getter = getattr(mod, "get_client", None)
    return getter(app) if getter else None


def derive(req):
    require_login(req)
    v = _vault(req)
    body = _body(req)
    if body.get("confirm_send") is not True:
        raise HttpError(400, "confirm_required", "送る前の 確かめが 要ります。")
    rid = req.params["id"]
    _get_photo(v, rid)
    client = _claude(req.app)
    if client is None:
        raise HttpError(503, "claude_unavailable", "鍵が 設定されていません。")
    try:
        out = client.read_image(rid)
    except HttpError:
        raise
    except Exception as e:
        # Claude の口の失敗の字は、鍵も本文も含まない約束（その字をそのまま見せる）
        said = str(e).strip() if type(e).__name__ == "ClaudeError" else ""
        raise HttpError(502, "claude_unreachable", said[:200] or "いまは接続できません。")
    if not isinstance(out, dict) or not isinstance(out.get("markdown"), str):
        raise HttpError(502, "claude_bad_answer", "読み取れませんでした。")
    meta = out.get("meta") if isinstance(out.get("meta"), dict) else {}
    v.set_derived(rid, out["markdown"], meta)
    return _detail(v.get_record(rid))


def delete_derived(req):
    """写しだけを消す（原本は動かない）。"""
    require_login(req)
    v = _vault(req)
    rid = req.params["id"]
    _get_photo(v, rid)
    d = os.path.join(v.root, "records", rid)
    for name in ("derived.md", "derived.json"):
        try:
            os.unlink(os.path.join(d, name))
        except FileNotFoundError:
            pass
    v.write_manifest()
    return (204, None)


def put_subject(req):
    require_login(req)
    v = _vault(req)
    rid = req.params["id"]
    _get_photo(v, rid)
    body = req.json()
    if not isinstance(body, dict):
        raise HttpError(400, "bad_json", "字の形が正しくありません。")
    for k in SUBJECT_FIELDS:
        if k not in body:
            raise HttpError(400, "missing_field", "欄が足りません。")
    if not isinstance(body["confirmed_by_person"], bool):
        raise HttpError(400, "bad_field", "字の形が正しくありません。")
    fields = {
        "author_role": _text_field(body, "author_role", MAX_FIELD_CHARS),
        "written_at": _text_field(body, "written_at", MAX_FIELD_CHARS),
        "procedure": _text_field(body, "procedure", MAX_FIELD_CHARS),
        "confirmed_by_person": body["confirmed_by_person"],
    }
    v.set_subject(rid, fields)
    return _detail(v.get_record(rid))


def add_annotation(req):
    require_login(req)
    v = _vault(req)
    rid = req.params["id"]
    is_photo = True
    try:
        v.get_record(rid)
    except (KeyError, ValueError):
        is_photo = False
        if not (re.match(r"^[A-Za-z0-9_-]{1,128}$", rid) and _bound_reply_by_record(v, rid) is not None):
            raise _not_found() from None
    body = req.json()
    if not isinstance(body, dict):
        raise HttpError(400, "bad_json", "字の形が正しくありません。")
    text = body.get("text")
    if not isinstance(text, str) or not text.strip():
        raise HttpError(400, "empty_note", "注記が 空です。")
    if len(text) > MAX_NOTE_CHARS:
        raise HttpError(400, "too_long", "長すぎます。")
    try:
        entry = v.add_annotation(rid, text) if is_photo else v.add_reply_annotation(rid, text)
    except KeyError:
        raise _not_found() from None
    return (201, entry)


def delete_record(req):
    require_login(req)
    v = _vault(req)
    rid = req.params["id"]
    try:
        v.delete_record(rid)
        return (204, None)
    except (KeyError, ValueError):
        pass
    row = _bound_reply_by_record(v, rid) if re.match(r"^[A-Za-z0-9_-]{1,128}$", rid) else None
    if row is None:
        raise _not_found()
    # 綴じた返事の記録を外す（返事そのものは「捨てた」扱いで残る）
    for name in ("reply.json", "annotations.json"):
        try:
            os.unlink(os.path.join(v.root, "records", rid, name))
        except OSError:
            pass
    try:
        os.rmdir(os.path.dirname(_reply_meta_path(v, rid)))
    except OSError:
        pass
    v.set_reply_disposition(row["reply_id"], "discarded")
    return (204, None)


# ---------------------------------------------------------------- 返事

def list_replies(req):
    require_login(req)
    v = _vault(req)
    rows = []
    for r in v.list_replies():
        row = dict(r)
        row["author_label"] = _reply_label(r)
        rows.append(row)
    return {"items": rows}


def bind_reply(req):
    require_login(req)
    v = _vault(req)
    body = _body(req)
    row = _find_reply(v, req.params["id"])
    if row is None:
        raise HttpError(404, "not_found", "返事が ありません。")
    if row.get("disposition") == "bound":
        raise HttpError(409, "already_bound", "もう 綴じています。")
    name = _text_field(body, "record_name", MAX_NAME_CHARS)
    rid = row["reply_id"]
    _write_json(_reply_meta_path(v, rid), {
        "reply_id": rid,
        "record_name": name or ("返事（%s）" % (row.get("port_name") or "")),
        "bound_at": ids.now_jst(req.app.clock),
    })
    v.set_reply_disposition(rid, "bound", rid)
    return _reply_record(v, _find_reply(v, rid))


def discard_reply(req):
    require_login(req)
    v = _vault(req)
    row = _find_reply(v, req.params["id"])
    if row is None:
        raise HttpError(404, "not_found", "返事が ありません。")
    if row.get("disposition") == "bound":
        raise HttpError(409, "already_bound", "もう 綴じています。")
    v.set_reply_disposition(row["reply_id"], "discarded")
    return (204, None)


# ---------------------------------------------------------------- 写真なしの控え

def _catalog_path(v):
    return os.path.join(v.root, "catalog.json")


def list_catalog(req):
    require_login(req)
    v = _vault(req)
    with _catalog_lock:
        return {"items": _read_json(_catalog_path(v), [])}


def add_catalog(req):
    require_login(req)
    v = _vault(req)
    body = req.json()
    if not isinstance(body, dict):
        raise HttpError(400, "bad_json", "字の形が正しくありません。")
    item = {
        "id": ids.new_id("cat"),
        "name": _text_field(body, "name", MAX_NAME_CHARS, required=True),
        "place": _text_field(body, "place", MAX_NAME_CHARS),
        "memo": _text_field(body, "memo", MAX_NOTE_CHARS),
        "added_at": ids.now_jst(req.app.clock),
    }
    with _catalog_lock:
        items = _read_json(_catalog_path(v), [])
        if len(items) >= MAX_CATALOG_ITEMS:
            raise HttpError(400, "too_many", "これ以上は たせません。")
        items.insert(0, item)
        _write_json(_catalog_path(v), items)
    return (201, item)


def delete_catalog(req):
    require_login(req)
    v = _vault(req)
    cid = req.params["id"]
    with _catalog_lock:
        items = _read_json(_catalog_path(v), [])
        keep = [i for i in items if i.get("id") != cid]
        if len(keep) == len(items):
            raise HttpError(404, "not_found", "ありません。")
        _write_json(_catalog_path(v), keep)
    return (204, None)


# ---------------------------------------------------------------- 持ち出し・全削除・Claude に送った物

def _export_dir(v):
    return os.path.join(os.path.dirname(v.root), "cip_exports")


def make_export(req):
    require_login(req)
    v = _vault(req)
    try:
        path, counts = v.export_zip(_export_dir(v))
    except storage.ExportCountMismatch:
        raise HttpError(500, "export_failed", "書き出せませんでした。")
    return {"file": os.path.basename(path), "counts": counts}


def get_export(req):
    require_login(req)
    v = _vault(req)
    name = req.params["file"]
    if not EXPORT_NAME_RE.match(name):
        raise HttpError(404, "not_found", "ありません。")
    path = os.path.join(_export_dir(v), name)
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        raise HttpError(404, "not_found", "ありません。")
    return Response(200, data, "application/zip",
                    {"Content-Disposition": 'attachment; filename="%s"' % name})


def wipe_vault(req):
    require_login(req)
    v = _vault(req)
    body = req.json()
    if not isinstance(body, dict) or body.get("confirm") != CONFIRM_WIPE:
        raise HttpError(400, "confirm_required", "確かめの字が ちがいます。")
    keep = body.get("keep_receipts") is True
    kept = v.list_handoffs() if keep else []
    v.wipe()
    # 持ち出しの zip（器の外の置き場）も消す＝「器の中身はすべて消える」を嘘にしない
    exp = _export_dir(v)
    if os.path.isdir(exp):
        for n in os.listdir(exp):
            if n.startswith("export_") and n.endswith(".zip"):
                try:
                    os.unlink(os.path.join(exp, n))
                except OSError:
                    pass
    for row in kept:
        # 「控えを のこす」＝控え（受け口の名・日時・束の指紋・番号）だけを残す。束の写し（原本の画像・意思表出文・注記）は残さない。
        b = row.get("bundle") or {}
        stub = {k: b.get(k) for k in ("bundle_version", "bundle_id", "created_at", "recipient", "item_count", "fingerprint") if k in b}
        stub["items"] = []
        stub["items_removed"] = True
        v.save_handoff(stub, row.get("receipt"))
    return (204, None)


def claude_log(req):
    require_login(req)
    v = _vault(req)
    return {"items": v.get_claude_log()}


# ---------------------------------------------------------------- 器の約束（指示の全文）

def prompts(req):
    require_login(req)
    base = os.path.join(req.app.app_root, "vault_app", "prompts")
    items = []
    for n in PROMPT_NAMES:
        p = os.path.join(base, n + ".txt")
        try:
            with open(p, "rb") as f:
                raw = f.read()
            mtime = os.stat(p).st_mtime
        except OSError:
            continue
        text = raw.decode("utf-8", "replace")
        ver, decided, body = claude_client.split_prompt(text)
        items.append({
            "name": n,
            "version": ver or hashlib.sha256(raw).hexdigest()[:12],      # 1 行目が無ければ、これまでの方法
            "decided_on": decided or ids.today_jst(lambda: mtime),
            "text": body,                                                # 送る物と同じ字（1 行目は除く）
        })
    return {"items": items}


ROUTES = [
    ("GET", "/api/records", list_records),
    ("POST", "/api/records", add_record),
    ("GET", "/api/records/{id}", get_record),
    ("DELETE", "/api/records/{id}", delete_record),
    ("GET", "/api/records/{id}/original", get_original),
    ("POST", "/api/records/{id}/derive", derive),
    ("DELETE", "/api/records/{id}/derived", delete_derived),
    ("PUT", "/api/records/{id}/subject", put_subject),
    ("POST", "/api/records/{id}/annotations", add_annotation),
    ("GET", "/api/replies", list_replies),
    ("POST", "/api/replies/{id}/bind", bind_reply),
    ("POST", "/api/replies/{id}/discard", discard_reply),
    ("GET", "/api/catalog", list_catalog),
    ("POST", "/api/catalog", add_catalog),
    ("DELETE", "/api/catalog/{id}", delete_catalog),
    ("POST", "/api/export", make_export),
    ("GET", "/api/export/{file}", get_export),
    ("DELETE", "/api/vault", wipe_vault),
    ("GET", "/api/claude_log", claude_log),
    ("GET", "/api/prompts", prompts),
]
