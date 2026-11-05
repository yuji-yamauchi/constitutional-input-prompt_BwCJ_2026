# -*- coding: utf-8 -*-
"""receiver_app/routes_face.py - 受け口の面の操作（cookie のセッションだけ・Bearer では通さない）。"""
import datetime
import hmac
import secrets

from app_src.common import contract, httpkit, ids
from app_src.common.httpkit import HttpError
from app_src.receiver_app.routes_api import (
    need_configured, parse_json_body, sha256_text, now_dt, iso, _log,
)
from app_src.receiver_app.storage import public_view, is_safe_id

COOKIE = "cip_port_session"
IDLE_SECONDS = 15 * 60
LOCK_FAILS = 5
LOCK_SECONDS = 5 * 60
LIST_LIMIT = 200
REPLY_MAX_CHARS = 4000
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"   # 英大文字と数字から 0 1 O I L を除く
CODE_LEN = 12
CODE_HOURS = 24

J07 = "ログインできませんでした。合言葉を たしかめてください。"
J10 = "しばらく ログインできません。5分 たってから、もういちど ためしてください。"
J33 = "この束は 見つかりません。"
J79 = {"unused": "まだ 使っていない", "used": "使った", "expired": "期限が 切れた"}


def session_required(req):
    app = req.app
    need_configured(app)
    if not app.sessions.touch(req.cookie(COOKIE)):
        raise HttpError(401, "unauthorized", "ログインしてください。")


def h_status(req):
    app = req.app
    if not app.configured:
        return 200, {"configured": False}
    return 200, {
        "configured": True,
        "logged_in": bool(app.sessions.touch(req.cookie(COOKIE))),
        "port_name": app.port_name,
    }


def h_login(req):
    app = req.app
    need_configured(app)
    body = parse_json_body(req)
    pw = body.get("passphrase")
    now = app.clock()
    with app.auth_lock:
        if app.locked_until and now < app.locked_until:
            _log(app, "login_blocked", status=423)
            raise HttpError(423, "locked", J10)
        ok = isinstance(pw, str) and hmac.compare_digest(pw.encode("utf-8"), app.passphrase.encode("utf-8"))
        if not ok:
            app.fail_count += 1
            _log(app, "login_failed", status=401)
            if app.fail_count >= LOCK_FAILS:
                app.fail_count = 0
                app.locked_until = now + LOCK_SECONDS
                _log(app, "login_locked", status=401)
            raise HttpError(401, "unauthorized", J07)    # 失敗の字は 1 種
        app.fail_count = 0
        app.locked_until = 0
    tok = app.sessions.create()
    _log(app, "login_ok", status=200)
    return 200, {"ok": True}, [httpkit.set_cookie_header(COOKIE, tok)]  # 期限は付けない（無操作の時間切れはサーバーの時計で見る＝操作を続けていれば切れない）


def h_logout(req):
    app = req.app
    app.sessions.drop(req.cookie(COOKIE))
    if app.configured:
        _log(app, "logout", status=200)
    return 200, {"ok": True}, [httpkit.set_cookie_header(COOKIE, "", clear=True)]


def h_list(req):
    session_required(req)
    app = req.app
    metas = app.storage.list_bundle_meta()
    rows = [{
        "bundle_id": m["bundle_id"],
        "received_at": m["received_at"],
        "display_name": m["display_name"],
        "item_count": m["item_count"],
        "fingerprint": m["fingerprint"],
        "reply_count": app.storage.reply_count(m["bundle_id"]),
    } for m in metas[:LIST_LIMIT]]
    return 200, {"bundles": rows, "truncated": len(metas) > LIST_LIMIT}


def _reply_out(r):
    out = public_view(r)
    out["author_label"] = contract.reply_author_label(r)
    return out


def h_detail(req):
    session_required(req)
    app = req.app
    bid = req.params["id"]
    meta = app.storage.find_bundle(bid) if is_safe_id(bid) else None
    if meta is None:
        raise HttpError(404, "not_found", J33)
    b = public_view(app.storage.load_bundle(bid))
    return 200, {
        "bundle": b,
        "received_at": meta["received_at"],
        "fingerprint": meta["fingerprint"],
        "receipt_id": meta["receipt_id"],
        "replies": [_reply_out(r) for r in app.storage.replies_for(bid)],
    }


def h_reply(req):
    session_required(req)
    app = req.app
    bid = req.params["id"]
    if not is_safe_id(bid) or app.storage.find_bundle(bid) is None:
        raise HttpError(404, "not_found", J33)
    body = parse_json_body(req)
    if body.get("human_attestation") is not True:      # JSON の true だけ（"true" や 1 は通さない）
        raise HttpError(400, "attestation_required", "「これは人が書きました」の確かめが ありません。")
    text = body.get("text")
    if not isinstance(text, str) or text.strip() == "":
        raise HttpError(400, "text_invalid", "本文が 空です。")
    if len(text) > REPLY_MAX_CHARS:
        raise HttpError(400, "text_invalid", "4000字を こえています。")
    attested_at = body.get("attested_at")
    parsed = ids.parse_iso(attested_at) if isinstance(attested_at, str) else None
    if parsed is None or parsed.tzinfo is None:
        raise HttpError(400, "attested_at_invalid", "確かめた時刻の字が 読めません。")
    reply = {
        "reply_version": contract.REPLY_VERSION,
        "reply_id": ids.new_id("rp"),
        "port_id": app.port_id,
        "port_name": app.port_name,
        "in_reply_to": bid,
        "text": text,                                   # 前後の空白・改行を削らない
        "written_at": ids.now_jst(app.clock),
        "author": {"role": "mentor", "human_attestation": True, "attested_at": attested_at},
    }
    if contract.validate_reply(reply):
        raise HttpError(400, "text_invalid", "返事の形が合いません。")
    stored = app.storage.save_reply(reply)
    _log(app, "reply_saved", bundle_id=bid, reply_id=reply["reply_id"], status=201)
    return 201, _reply_out(stored)


def h_pairing_create(req):
    session_required(req)
    app = req.app
    code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LEN))
    now = now_dt(app)
    exp = now + datetime.timedelta(hours=CODE_HOURS)
    app.storage.add_pairing(sha256_text(code), iso(now), iso(exp))
    _log(app, "pairing_created", status=201)
    return 201, {"code": code, "expires_at": iso(exp)}     # 値はこの応答の中だけ


def h_pairing_list(req):
    session_required(req)
    app = req.app
    now = now_dt(app)
    out = []
    for row in app.storage.pairing_rows()[:20]:
        exp = ids.parse_iso(row.get("expires_at") or "")
        if row.get("used_at"):
            st = J79["used"]
        elif exp is None or now > exp:
            st = J79["expired"]
        else:
            st = J79["unused"]
        out.append({"created_at": row.get("created_at"), "expires_at": row.get("expires_at"), "status": st})
    return 200, {"pairings": out}


ROUTES = [
    ("GET", "/face/status", h_status),
    ("POST", "/face/login", h_login),
    ("POST", "/face/logout", h_logout),
    ("GET", "/face/bundles", h_list),
    ("GET", "/face/bundles/{id}", h_detail),
    ("POST", "/face/bundles/{id}/replies", h_reply),
    ("POST", "/face/pairings", h_pairing_create),
    ("GET", "/face/pairings", h_pairing_list),
]
