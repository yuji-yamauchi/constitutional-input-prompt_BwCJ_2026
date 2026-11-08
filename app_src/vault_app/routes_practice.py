# -*- coding: utf-8 -*-
"""vault_app/routes_practice.py - A（れんしゅう）の口。全部 require_login の後。

読み返しは本人の文を 1 字も変えずに返す（コードが作る）。Claude に頼むのは問い 1 文だけ。
印と回数は「あったことの数」だけ。割合・合計・順位は計算しない。
"""
from app_src.common.httpkit import HttpError
from app_src.vault_app import claude_client, storage
from app_src.vault_app.auth import require_login

MAX_TEXT_CHARS = 4000

CONDITIONS = [
    ("amount", "一度に 書く量", ("すくなめ", "ふつう", "おおめ")),
    ("split", "区切り方", ("区切らない", "文ごと", "段ごと")),
    ("ease", "ことばの やさしさ", ("やさしい", "ふつう")),
    ("length", "長さ", ("みじかく", "ながく")),
    ("input", "入力の形", ("文字", "えらぶ形の たすけ")),
]
_ALLOWED = {k: vals for k, _label, vals in CONDITIONS}

D_BAD_BODY = "送られた 形が 正しくありません。"
D_BAD_CONDITIONS = "書き方の条件が 正しくありません。"
D_EMPTY_TEXT = "文が 空です。"
D_TOO_LONG = "4000字を こえています。"
D_BAD_MARK = "印の 字が 正しくありません。"
D_NO_TURN = "この やりとりは 見つかりません。"
D_CLOSED_INPUT = "この 送り方は 受け付けません。"      # v0.15: 画面から 届かない 入力（direction の 値・share_daily）は 受け取らない


def _body(req):
    b = req.json()
    if not isinstance(b, dict):
        raise HttpError(400, "bad_request", D_BAD_BODY)
    return b


def _check_conditions(c):
    if not isinstance(c, dict) or set(c) != set(_ALLOWED):
        raise HttpError(400, "bad_conditions", D_BAD_CONDITIONS)
    for k, v in c.items():
        if not isinstance(v, str) or v not in _ALLOWED[k]:
            raise HttpError(400, "bad_conditions", D_BAD_CONDITIONS)
    return {k: c[k] for k in _ALLOWED}


def h_conditions(req):
    require_login(req)
    return 200, {"conditions": [{"key": k, "label": label, "values": list(vals)} for k, label, vals in CONDITIONS]}


def _check_closed(body):
    """v0.15: 画面は direction を 常に null で 送り、share_daily は 送らない。
    それ以外の 形（direction が null でない・share_daily が false でない）は 使わずに 断る＝サーバーが 受け取れる 口を 残さない。"""
    if body.get("direction") is not None or body.get("share_daily", False) is not False:
        raise HttpError(400, "closed_input", D_CLOSED_INPUT)


def h_turn(req):
    require_login(req)
    app = req.app
    body = _body(req)
    conds = _check_conditions(body.get("conditions"))
    text = body.get("text")
    if not isinstance(text, str) or text.strip() == "":
        raise HttpError(400, "text_empty", D_EMPTY_TEXT)
    if len(text) > MAX_TEXT_CHARS:
        raise HttpError(413, "too_large", D_TOO_LONG)
    _check_closed(body)
    question, reason = None, None
    claude = claude_client.get_client(app)
    if claude is None:
        reason = "claude_unavailable"
    else:
        try:
            question, reason = claude.ask_question(text, conds)
        except claude_client.ClaudeError:
            question, reason = None, "claude_failed"       # 問いが無くても、読み返しと記録は残す
    readback = text                                        # 1 字も変えない
    turn_id = app.vault.add_turn(conds, text, readback, question, reason)   # direction=None・shared_daily=False（欄は 残す。過去の 記録と 同じ 形）
    out = {"turn_id": turn_id, "readback": readback, "question": question, "reason": reason}
    model = getattr(claude, "model", None)
    if isinstance(model, str):
        out["model"] = model                         # 発言の下の札（モデル・指示の版）。demo のときも実際の名
        out["demo"] = bool(getattr(claude, "demo", False))
        out["prompt_version"] = claude_client.read_prompt_version(getattr(claude, "prompts_dir", ""), "listener")
    return 200, out


def h_mark(req):
    require_login(req)
    app = req.app
    body = _body(req)
    turn_id = body.get("turn_id")
    mark = body.get("mark")
    if not isinstance(turn_id, str) or not isinstance(mark, str):
        raise HttpError(400, "bad_request", D_BAD_BODY)
    if mark not in storage.MARKS:
        raise HttpError(400, "bad_mark", D_BAD_MARK)
    try:
        turn = app.vault.get_turn(turn_id)
    except ValueError:
        turn = None
    if turn is None:
        raise HttpError(404, "not_found", D_NO_TURN)
    try:
        app.vault.add_mark(turn_id, mark)
    except storage.UnknownTurn:
        raise HttpError(404, "not_found", D_NO_TURN) from None
    c = turn["conditions"]
    line = "印を のこしました（%s・%s／%s）。" % (mark, c.get("amount", ""), c.get("split", ""))
    return 200, {"ok": True, "summary_line": line}


def h_summary(req):
    require_login(req)
    return 200, req.app.vault.practice_summary()


ROUTES = [
    ("GET", "/api/practice/conditions", h_conditions),
    ("POST", "/api/practice/turns", h_turn),
    ("POST", "/api/practice/marks", h_mark),
    ("GET", "/api/practice/summary", h_summary),
]
