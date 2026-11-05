# -*- coding: utf-8 -*-
"""receiver_app/routes_api.py - 取り決めの 4 本（器 -> 受け口・Bearer だけ）。

POST /v1/pair / POST /v1/bundles / GET /v1/bundles / GET /v1/replies?since=
エラーは {"error","detail"}（httpkit.HttpError）。cookie では通さない。
"""
import datetime
import hashlib
import json
import secrets

from app_src.common import contract, ids
from app_src.common.httpkit import HttpError
from app_src.receiver_app.storage import public_view, is_safe_id

D_UNAUTH = "認証できませんでした。"
D_NOT_CONFIGURED = "設定が ありません。"
SMALL_JSON_LIMIT = 256 * 1024


def sha256_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def now_dt(app):
    return datetime.datetime.fromtimestamp(app.clock(), ids.JST)


def iso(dt):
    return dt.isoformat(timespec="seconds")


def need_configured(app):
    if not app.configured:
        raise HttpError(503, "not_configured", D_NOT_CONFIGURED)


def parse_json_body(req, limit=SMALL_JSON_LIMIT):
    """本文を JSON の辞書として読む。読めない・辞書でない = 400 schema_invalid。"""
    raw = req.raw(limit)
    try:
        obj = json.loads(raw.decode("utf-8"))
    except Exception:
        raise HttpError(400, "schema_invalid", "JSON として読めません。")
    if not isinstance(obj, dict):
        raise HttpError(400, "schema_invalid", "JSON の形が違います。")
    return obj


def auth_person(req):
    """Bearer token -> person_ref。無い・違う = 401。"""
    app = req.app
    need_configured(app)
    tok = req.bearer()
    if not tok:
        raise HttpError(401, "unauthorized", D_UNAUTH)
    person = app.storage.person_for_token(sha256_text(tok))
    if not person:
        raise HttpError(401, "unauthorized", D_UNAUTH)
    return person


def _log(app, kind, **kw):
    app.storage.log_event(kind, ts=ids.now_jst(app.clock), **kw)


def _safe_bid(b):
    if isinstance(b, dict) and is_safe_id(b.get("bundle_id")):
        return b["bundle_id"]
    return None


def _reject(app, status, code, detail, bundle=None, fp=None):
    _log(app, "bundle_rejected", bundle_id=_safe_bid(bundle), fingerprint=fp, status=status)
    raise HttpError(status, code, detail)


def h_pair(req):
    app = req.app
    need_configured(app)
    body = parse_json_body(req)
    code = body.get("pairing_code")
    if not isinstance(code, str):
        raise HttpError(400, "schema_invalid", "pairing_code が文字ではありません。")
    # 器が小文字で打っても通る（受け口の面の決まりの空きをこちらで埋めた）
    code_sha = sha256_text(code.strip().upper())
    person_ref = app.person_ref_factory()
    token = secrets.token_hex(32)
    now = now_dt(app)
    if not app.storage.consume_pairing(code_sha, now, iso(now), person_ref, sha256_text(token)):
        _log(app, "pair_failed", status=401)
        raise HttpError(401, "unauthorized", D_UNAUTH)
    _log(app, "pairing_used", status=200)
    return 200, {"person_ref": person_ref, "token": token, "port_id": app.port_id, "port_name": app.port_name}


def h_post_bundle(req):
    app = req.app
    person = auth_person(req)
    raw = req.raw(contract.MAX_BUNDLE_BYTES)          # 25 MB 超 = 413（読む前に）
    try:
        b = json.loads(raw.decode("utf-8"))
    except Exception:
        _reject(app, 400, "schema_invalid", "JSON として読めません。")
    try:
        errs = contract.validate_bundle(b)
    except Exception:
        errs = ["束の形が読めません"]
    if errs:
        fp = None
        if any("fingerprint_mismatch" in e for e in errs):
            try:
                fp = contract.fingerprint(b)
            except Exception:
                fp = None
            _reject(app, 400, "fingerprint_mismatch", errs[0], b, fp)
        if isinstance(b, dict) and "bundle_version" in b and b.get("bundle_version") != contract.BUNDLE_VERSION:
            _reject(app, 400, "schema_invalid", "unsupported version", b)
        if any(("を超える" in e) for e in errs):      # 50 品目超・原本 5 MB 超＝上限超え（取り決め＝413 too_large）
            _reject(app, 413, "too_large", next(e for e in errs if "を超える" in e), b)
        _reject(app, 400, "schema_invalid", errs[0], b)
    bid = b["bundle_id"]
    if not is_safe_id(bid):
        _reject(app, 400, "schema_invalid", "束.bundle_id の字が使えません", b)
    if b["sender"]["person_ref"] != person:
        _reject(app, 404, "unknown_person", "対になった本人が見つかりません。", b)
    fp = contract.fingerprint(b)                       # 送り手の値を信じず自分で計算する
    st = app.storage
    with st.lock:
        old = st.find_bundle(bid)
        if old is not None:
            if old["fingerprint"] == fp:
                _log(app, "bundle_resent", bundle_id=bid, fingerprint=fp, status=200)
                return 200, st.load_receipt(bid)
            _reject(app, 409, "duplicate_bundle_id", "同じ bundle_id で中身が違います。", b, fp)
        received_at = ids.now_jst(app.clock)
        receipt = {
            "receipt_version": contract.RECEIPT_VERSION,
            "receipt_id": ids.new_id("rc"),
            "port_id": app.port_id,
            "port_name": app.port_name,
            "bundle_id": bid,
            "bundle_fingerprint": fp,
            "item_count": len(b["items"]),
            "received_at": received_at,
        }
        st.save_bundle(b, receipt, person, fp, received_at)
    _log(app, "bundle_received", bundle_id=bid, fingerprint=fp, status=201)
    return 201, receipt


def h_list_bundles(req):
    app = req.app
    person = auth_person(req)
    rows = []
    for m in app.storage.list_bundle_meta(person):
        rows.append({
            "bundle_id": m["bundle_id"],
            "received_at": m["received_at"],
            "bundle_fingerprint": m["fingerprint"],
            "item_count": m["item_count"],
            "receipt_id": m["receipt_id"],
            "reply_count": app.storage.reply_count(m["bundle_id"]),
        })
    return 200, {"bundles": rows}


def h_list_replies(req):
    app = req.app
    person = auth_person(req)
    since = req.query.get("since")
    if since:
        since = since.strip().replace(" ", "+")        # 生の + が空白に化けた時刻を戻す
    mine = set(m["bundle_id"] for m in app.storage.list_bundle_meta(person))
    out = []
    for bid in mine:
        for r in app.storage.replies_for(bid):
            if since and r.get("written_at", "") < since:   # 同じ時差の ISO 8601 の字を辞書順で比べる
                continue
            out.append(r)
    out.sort(key=lambda r: r["_seq"], reverse=True)
    return 200, {"replies": [public_view(r) for r in out]}


ROUTES = [
    ("POST", "/v1/pair", h_pair),
    ("POST", "/v1/bundles", h_post_bundle),
    ("GET", "/v1/bundles", h_list_bundles),
    ("GET", "/v1/replies", h_list_replies),
]
