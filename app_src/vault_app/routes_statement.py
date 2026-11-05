# -*- coding: utf-8 -*-
"""vault_app/routes_statement.py - C（意思表出文）と法令集の口。全部 require_login の後。

- 画面に出る条文の字は、いつも法令集（law.py）の JSON から出す。モデルの字を条文として出さない。
- Claude が並べた物は「案」の札（item["draft"]）。最終版は本人の finalize だけ。
- 当てはめの字（「あなたに 使えます」の型）は、コードは足さない。
"""
from app_src.common import ids
from app_src.common.httpkit import HttpError
from app_src.vault_app import claude_client, law
from app_src.vault_app.auth import require_login

DRAFT_LABEL = "案"
MAX_FIELD_CHARS = 4000
MAX_FINAL_CHARS = 8000
MAX_LIST = 100

D_BAD_BODY = "送られた 形が 正しくありません。"
D_BAD_SECTIONS = "欄の 形が 正しくありません。"
D_NO_STATEMENT = "この 意思表出文は 見つかりません。"
D_NO_LAW = "この 条は 見つかりません。"
D_NO_RECORD = "記録が 見つかりません。"
D_FINAL = "最終版は 直せません。"
D_CONFIRM = "Claude に 送る 確かめが ありません。"
D_NO_CLAUDE = "鍵が 設定されていません。"
D_FAILED = "いまは接続できません。時間をおいて、もういちどためしてください。"
D_TEXT_EMPTY = "本文が 空です。"
D_TOO_LONG = "字が 長すぎます。"
D_STATUTE_UNKNOWN = "法令集に ない 条が 含まれています。"


def _body(req):
    b = req.json()
    if not isinstance(b, dict):
        raise HttpError(400, "bad_request", D_BAD_BODY)
    return b


def _str_list(v):
    if v is None:
        return []
    if not isinstance(v, list) or len(v) > MAX_LIST or any(not isinstance(x, str) or x == "" for x in v):
        raise HttpError(400, "bad_sections", D_BAD_SECTIONS)
    out = []
    for x in v:
        if x not in out:
            out.append(x)
    return out


def _need_record(vault, rid):
    try:
        return vault.get_record(rid)
    except (KeyError, ValueError):
        raise HttpError(400, "record_unknown", D_NO_RECORD) from None


def _norm_sections(vault, raw):
    if not isinstance(raw, dict):
        raise HttpError(400, "bad_sections", D_BAD_SECTIONS)
    out = {}
    for k in ("trouble", "wish"):
        v = raw.get(k, "")
        if not isinstance(v, str):
            raise HttpError(400, "bad_sections", D_BAD_SECTIONS)
        if len(v) > MAX_FIELD_CHARS:
            raise HttpError(413, "too_large", D_TOO_LONG)
        out[k] = v
    out["grounds"] = _str_list(raw.get("grounds"))
    for rid in out["grounds"]:
        _need_record(vault, rid)
    out["statute_ids"] = _str_list(raw.get("statute_ids"))
    return out


def _load(app, sid):
    try:
        item = app.vault.get_statement(sid)
    except ValueError:
        item = None
    if item is None:
        raise HttpError(404, "not_found", D_NO_STATEMENT)
    return item


def _view(item, corpus):
    """画面用。条文は id -> 法令集の 7 欄にして返す（法令集に無い id は外す）。"""
    v = dict(item)
    sec = dict(item.get("sections") or {})
    known = [i for i in sec.get("statute_ids", []) if corpus.get(i) is not None]
    sec["statute_ids"] = known
    sec["statutes"] = [corpus.get(i) for i in known]
    v["sections"] = sec
    d = item.get("draft")
    if isinstance(d, dict):
        dk = [i for i in d.get("statute_ids", []) if corpus.get(i) is not None]
        v["draft"] = dict(d, statute_ids=dk, statutes=[corpus.get(i) for i in dk])
    return v


# ---- 法令集
def h_law_index(req):
    require_login(req)
    return 200, {"law": law.for_app(req.app).index()}


def h_law_get(req):
    require_login(req)
    e = law.for_app(req.app).get(req.params["id"])
    if e is None:
        raise HttpError(404, "not_found", D_NO_LAW)
    return 200, e


# ---- 意思表出文
def h_create(req):
    require_login(req)
    app = req.app
    sections = _norm_sections(app.vault, _body(req).get("sections"))
    now = ids.now_jst(app.clock)
    item = {
        "item_id": ids.new_id("st"),
        "author": "person",
        "created_at": now,
        "updated_at": now,
        "sections": sections,
        "text": "",
        "finalized_at": None,
        "draft": None,
    }
    sid = app.vault.save_statement(item)
    return 201, {"item_id": sid}


def h_update(req):
    require_login(req)
    app = req.app
    item = _load(app, req.params["id"])
    if item.get("finalized_at"):
        raise HttpError(409, "already_final", D_FINAL)
    item = dict(item, sections=_norm_sections(app.vault, _body(req).get("sections")), updated_at=ids.now_jst(app.clock))
    app.vault.save_statement(item)
    return 200, _view(item, law.for_app(app))


def h_list(req):
    require_login(req)
    corpus = law.for_app(req.app)
    return 200, {"statements": [_view(i, corpus) for i in req.app.vault.list_statements()]}


def h_get(req):
    require_login(req)
    return 200, _view(_load(req.app, req.params["id"]), law.for_app(req.app))


def h_arrange(req):
    require_login(req)
    app = req.app
    body = _body(req)
    if body.get("confirm_send") is not True:
        raise HttpError(400, "confirm_required", D_CONFIRM)
    item = _load(app, req.params["id"])
    if item.get("finalized_at"):
        raise HttpError(409, "already_final", D_FINAL)
    claude = claude_client.get_client(app)
    if claude is None:
        raise HttpError(503, "claude_unavailable", D_NO_CLAUDE)
    texts = []
    for rid in _str_list(body.get("include_records")):
        d = _need_record(app.vault, rid).get("derived")
        if d and isinstance(d.get("markdown"), str):
            texts.append(d["markdown"])                    # 派生の Markdown だけ（原本の画像は送らない）
    corpus = law.for_app(app)
    sec = item.get("sections") or {}
    try:
        out = claude.arrange(sec.get("trouble", ""), sec.get("wish", ""), texts, corpus.index())
    except claude_client.ClaudeError:
        raise HttpError(502, "claude_failed", D_FAILED) from None
    draft = {
        "text": out["draft_text"],
        "label": DRAFT_LABEL,
        "statute_ids": out["statute_ids"],
        "made_at": ids.now_jst(app.clock),
    }
    app.vault.save_statement(dict(item, draft=draft))      # 案は保存するが、最終版にはしない
    return 200, {
        "draft": {"text": draft["text"], "label": DRAFT_LABEL, "statute_ids": draft["statute_ids"]},
        "dropped_ids": out["dropped_ids"],
    }


def h_finalize(req):
    require_login(req)
    app = req.app
    body = _body(req)
    item = _load(app, req.params["id"])
    if item.get("finalized_at"):
        raise HttpError(409, "already_final", D_FINAL)
    text = body.get("text")
    if not isinstance(text, str) or text.strip() == "":
        raise HttpError(400, "text_empty", D_TEXT_EMPTY)
    if len(text) > MAX_FINAL_CHARS:
        raise HttpError(413, "too_large", D_TOO_LONG)
    sections = _norm_sections(app.vault, body["sections"]) if "sections" in body else item.get("sections")
    corpus = law.for_app(app)
    for i in sections.get("statute_ids", []):
        if corpus.get(i) is None:
            raise HttpError(400, "statute_unknown", D_STATUTE_UNKNOWN)
    now = ids.now_jst(app.clock)
    item = dict(item, text=text, sections=sections, finalized_at=now, updated_at=now)    # 本人の字のまま。当てはめの字は足さない
    app.vault.save_statement(item)
    return 200, _view(item, corpus)


ROUTES = [
    ("GET", "/api/law", h_law_index),
    ("GET", "/api/law/{id}", h_law_get),
    ("POST", "/api/statements", h_create),
    ("GET", "/api/statements", h_list),
    ("GET", "/api/statements/{id}", h_get),
    ("PUT", "/api/statements/{id}", h_update),
    ("POST", "/api/statements/{id}/arrange", h_arrange),
    ("POST", "/api/statements/{id}/finalize", h_finalize),
]
