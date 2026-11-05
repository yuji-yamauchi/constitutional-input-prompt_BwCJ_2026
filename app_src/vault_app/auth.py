# -*- coding: utf-8 -*-
"""vault_app/auth.py — 入口の共通の助け（共通）。routes_auth と routes_*が同じ物を使う。"""
from app_src.common.httpkit import HttpError

SESSION_COOKIE = "cip_vault_session"


def session_token(req):
    return req.cookie(SESSION_COOKIE)


def is_logged_in(req):
    tok = session_token(req)
    return bool(tok) and req.app.sessions.touch(tok)


def require_login(req):
    """ログイン済みでなければ 401。時間切れと未ログインは同じ字（本人の字を出す前なので区別は画面側の時計で）。"""
    if not is_logged_in(req):
        raise HttpError(401, "unauthorized", "ログインが 必要です。")
    return True
