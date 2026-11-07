# -*- coding: utf-8 -*-
"""vault_app/routes_kibun.py - きょうの 気分（60 問）の口。全部 require_login の後。Claude は 呼ばない。

問いの 字と 選択肢は kibun.py（器の 決まった 字）。答えは 本人の 箱（kibun/<日付>.json）に のこす だけ。
点・合計・くらべは 計算しない。束には 入れない。
"""
from app_src.common.httpkit import HttpError
from app_src.vault_app import kibun, storage
from app_src.vault_app.auth import require_login

D_BAD_BODY = "送られた 形が 正しくありません。"
D_BAD_DATE = "日付が 読めません。"
D_BAD_COUNT = "問いの 数が 正しくありません。"
D_BAD_ANSWER = "答えの 形が 正しくありません。"
D_NO_RUN = "この 回は 見つかりません。"
D_UNKNOWN_FIELD = "知らない 欄が あります。"
FIELDS = ("date", "run_id", "count", "start_id", "version", "answers", "finished")


def _vault(req):
    v = req.app.vault
    if v is None:
        raise HttpError(503, "not_configured", "設定が ありません。")
    return v


def _body(req):
    b = req.json()
    if not isinstance(b, dict):
        raise HttpError(400, "bad_request", D_BAD_BODY)
    return b


def _date(value):
    try:
        return storage._check_date(value)
    except ValueError:
        raise HttpError(400, "bad_date", D_BAD_DATE) from None


def _check_answers(answers, count):
    if not isinstance(answers, list) or len(answers) > count:
        raise HttpError(400, "bad_answer", D_BAD_ANSWER)
    seen = set()
    out = []
    for a in answers:
        if not isinstance(a, dict) or set(a) != {"id", "choice"}:
            raise HttpError(400, "bad_answer", D_BAD_ANSWER)
        i, c = a["id"], a["choice"]
        if isinstance(i, bool) or not isinstance(i, int) or kibun.item(i) is None or i in seen:
            raise HttpError(400, "bad_answer", D_BAD_ANSWER)
        if not isinstance(c, str) or c not in kibun.choice_keys(i):
            raise HttpError(400, "bad_answer", D_BAD_ANSWER)
        seen.add(i)
        out.append({"id": i, "choice": c})
    return out


def h_items(req):
    require_login(req)
    v = _vault(req)
    out = kibun.items_payload()
    out["next_id"] = kibun.next_id_after(v.kibun_last_answered_id())
    return 200, out


def h_day(req):
    require_login(req)
    v = _vault(req)
    return 200, v.get_kibun_day(_date(req.params["date"]))


def h_run(req):
    require_login(req)
    v = _vault(req)
    b = _body(req)
    if set(b) - set(FIELDS):
        raise HttpError(400, "unknown_field", D_UNKNOWN_FIELD)
    date = _date(b.get("date"))
    run_id = b.get("run_id")
    if run_id is not None and not isinstance(run_id, str):
        raise HttpError(400, "bad_request", D_BAD_BODY)
    count = b.get("count")
    if isinstance(count, bool) or count not in kibun.COUNTS:
        raise HttpError(400, "bad_count", D_BAD_COUNT)
    start_id = b.get("start_id")
    if isinstance(start_id, bool) or not isinstance(start_id, int) or kibun.item(start_id) is None:
        raise HttpError(400, "bad_request", D_BAD_BODY)
    if b.get("version") != kibun.VERSION:
        raise HttpError(400, "bad_request", D_BAD_BODY)
    finished = b.get("finished", False)
    if not isinstance(finished, bool):
        raise HttpError(400, "bad_request", D_BAD_BODY)
    answers = _check_answers(b.get("answers"), count)
    try:
        run = v.upsert_kibun_run(date, run_id, count, start_id, kibun.VERSION, answers, finished)
    except (KeyError, ValueError):
        raise HttpError(404, "not_found", D_NO_RUN) from None
    return 200, {"run_id": run["run_id"], "date": date, "saved": len(run["answers"]), "finished": finished}


ROUTES = [
    ("GET", "/api/kibun/items", h_items),
    ("GET", "/api/kibun/days/{date}", h_day),
    ("POST", "/api/kibun/runs", h_run),
]
