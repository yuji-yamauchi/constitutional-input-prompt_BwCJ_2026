# -*- coding: utf-8 -*-
"""vault_app/routes_daily.py - きょうの こと（ゆうべ ねた 時刻・おきた 時刻・あさごはん）の口。全部 require_login の後。

本人の箱に 日ごとに 1 つ。束には入れない。聞き役へは、本人が 伝えると 決めた 日だけ、サーバーが ここから 読んで 添える。
"""
from app_src.common.httpkit import HttpError
from app_src.vault_app import storage
from app_src.vault_app.auth import require_login

D_BAD_DATE = "日付が 読めません。"
D_BAD_TIME = "時刻が 読めません。"
D_BAD_BREAKFAST = "あさごはんが 読めません。"
D_BAD_BODY = "送られた 形が 正しくありません。"
D_UNKNOWN_FIELD = "知らない 欄が あります。"
FIELDS = ("bed_time", "wake_time", "breakfast")


def _vault(req):
    v = req.app.vault
    if v is None:
        raise HttpError(503, "not_configured", "設定が ありません。")
    return v


def _body(req):
    if int(req.headers.get("Content-Length") or 0) == 0:
        return {}
    b = req.json()
    if not isinstance(b, dict):
        raise HttpError(400, "bad_json", D_BAD_BODY)
    return b


def _date(req):
    d = req.params["date"]
    try:
        storage._check_date(d)
    except ValueError:
        raise HttpError(400, "bad_date", D_BAD_DATE) from None
    return d


def h_get(req):
    require_login(req)
    v = _vault(req)
    return 200, v.get_daily(_date(req))


def h_put(req):
    require_login(req)
    v = _vault(req)
    date = _date(req)
    body = _body(req)
    if set(body) - set(FIELDS):
        raise HttpError(400, "unknown_field", D_UNKNOWN_FIELD)
    vals = {k: body.get(k) for k in FIELDS}
    for k in ("bed_time", "wake_time"):
        try:
            storage._check_hhmm(vals[k], k)
        except ValueError:
            raise HttpError(400, "bad_time", D_BAD_TIME) from None
    b = vals["breakfast"]
    if b is not None and (not isinstance(b, str) or b not in storage.BREAKFAST_VALUES):
        raise HttpError(400, "bad_breakfast", D_BAD_BREAKFAST)
    return 200, v.set_daily(date, vals["bed_time"], vals["wake_time"], vals["breakfast"])


ROUTES = [
    ("GET", "/api/daily/{date}", h_get),
    ("PUT", "/api/daily/{date}", h_put),
]
