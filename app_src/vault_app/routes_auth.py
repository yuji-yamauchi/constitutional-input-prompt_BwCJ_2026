# -*- coding: utf-8 -*-
"""vault_app/routes_auth.py - 入口（合言葉 1 つ・無操作 15 分・ログアウト）と /api/status。

標準ライブラリだけ。ネットワークへ出るコードは無い。
- 合言葉の値はメモリの中だけ（ログ・画面・応答に出さない）。
- 入口を通っているかの確かめは auth.require_login を使う（ほかの routes_*.py も同じ物）。
"""
import hmac

from app_src.common.httpkit import HttpError, set_cookie_header
from app_src.vault_app import auth
from app_src.vault_app.auth import require_login   # noqa: F401  （ほかの部品がここからも取れるように）

MAX_PASSPHRASE_CHARS = 512
LOCK_FAILS = 5            # 続けて違えてよい回数
LOCK_SECONDS = 5 * 60     # 止める長さ

TXT_NOT_CONFIGURED = "設定が ありません。"
TXT_BAD_PASSPHRASE = "ログインできませんでした。合言葉を たしかめてください。"
TXT_EMPTY_PASSPHRASE = "合言葉を 入れてください。"
TXT_LOCKED = "しばらく 待ってください。"


def _configured(app):
    return bool(app.cfg.get("passphrase"))


def status(req):
    app = req.app
    logged_in = auth.is_logged_in(req) if _configured(app) else False
    out = {
        "configured": _configured(app),
        "logged_in": logged_in,
        "claude": app.claude_state(),
        "demo_mode": bool(app.cfg.get("demo_mode")),
        "demo_placeholder": bool(app.claude is not None and app.cfg.get("demo_mode") and getattr(app.claude, "demo_is_placeholder", lambda: True)()),
        "port_paired": False,
    }
    if logged_in and app.vault is not None:
        pairing = app.vault.get_pairing()
        out["port_paired"] = bool(pairing)
        if pairing and isinstance(pairing.get("port_name"), str):
            out["port_name"] = pairing["port_name"]
    return out


def login(req):
    app = req.app
    if not _configured(app):
        raise HttpError(503, "not_configured", TXT_NOT_CONFIGURED)
    body = req.json()
    given = body.get("passphrase") if isinstance(body, dict) else None
    now = app.clock()
    with app.auth_lock:
        if app.locked_until and now < app.locked_until:
            raise HttpError(423, "locked", TXT_LOCKED)     # 止めている間は、正しい合言葉でも通さない
        if not isinstance(given, str) or not given:
            raise HttpError(400, "empty_passphrase", TXT_EMPTY_PASSPHRASE)
        ok = len(given) <= MAX_PASSPHRASE_CHARS and hmac.compare_digest(given.encode("utf-8"), app.cfg["passphrase"].encode("utf-8"))
        if not ok:
            app.fail_count += 1
            if app.fail_count >= LOCK_FAILS:
                app.fail_count = 0
                app.locked_until = now + LOCK_SECONDS
            raise HttpError(401, "bad_passphrase", TXT_BAD_PASSPHRASE)
        app.fail_count = 0
        app.locked_until = 0
    old = auth.session_token(req)
    if old:
        app.sessions.drop(old)
    tok = app.sessions.create()
    return (204, None, [set_cookie_header(auth.SESSION_COOKIE, tok)])


def logout(req):
    tok = auth.session_token(req)
    if tok:
        req.app.sessions.drop(tok)
    return (204, None, [set_cookie_header(auth.SESSION_COOKIE, "", clear=True)])


ROUTES = [
    ("GET", "/api/status", status),
    ("POST", "/api/login", login),
    ("POST", "/api/logout", logout),
]
