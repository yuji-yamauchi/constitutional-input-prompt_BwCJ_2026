# -*- coding: utf-8 -*-
"""vault_app/main.py - 器（本人のアプリ）の起動と経路の表。標準ライブラリだけ。

起動: app_src の親の場所で  python3 -B -m app_src.vault_app.main
環境変数（名だけ。値はどこにも書かない）:
  VAULT_PASSPHRASE  入口の合言葉（無い・空 = 「設定が ありません。」だけ）
  ANTHROPIC_API_KEY Claude の鍵（無ければ Claude の機能は無効）
  CIP_DEMO_MODE     1 のとき Claude の呼び出しを記録済みの応答で返す
  CIP_VAULT_DIR     保存の場所（既定: ホームの cip_vault/）
  CIP_VAULT_PORT    待ち受けの番号（既定 8765）
  PORT_BASE_URL     受け口の場所（既定: 手元の 8766）
  CIP_CLAUDE_MODEL  Claude のモデル名
  CIP_LAW_DIR       法令集の置き場（既定: app_src/law_corpus）
待ち受けは 127.0.0.1 だけ。os.environ を読むのは main() の中だけ。
"""
import importlib
import os
import time

from app_src.common import httpkit
from app_src.common.httpkit import HttpError
from app_src.vault_app import auth, routes_auth, routes_records, storage
from app_src.vault_app.appctx import VaultApp

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
DEFAULT_PORT = 8765
DEFAULT_PORT_BASE_URL = "http://127.0.0.1:8766"
IDLE_SECONDS = 15 * 60
OPTIONAL_ROUTES = ("routes_practice", "routes_statement", "routes_handoff", "routes_daily")
PACKAGE = "app_src.vault_app"


def _import_optional(name):
    """在れば読み込む。その部品自身が無いときだけ None（中の失敗は隠さない）。"""
    full = "%s.%s" % (PACKAGE, name)
    try:
        return importlib.import_module(full)
    except ImportError as e:
        if getattr(e, "name", None) == full:
            return None
        raise


def _wrap(handler):
    """入口の 401 のうち、cookie を持っていた物は『時間切れ』の旗を付けて返す（画面が W-03 を出せるように）。"""
    def wrapped(req):
        try:
            req.raw()   # 本文を読み切る（読まない口があっても、次の要求に字が残らない）
            return handler(req)
        except HttpError as e:
            if e.status == 401 and e.code == "unauthorized" and req.cookie(auth.SESSION_COOKIE):
                clear = httpkit.set_cookie_header(auth.SESSION_COOKIE, "", clear=True)
                return (401, {"error": "unauthorized", "detail": e.message, "expired": True}, [clear])
            raise
    return wrapped


def _make_cfg(env, vault_dir):
    try:
        port = int(env.get("CIP_VAULT_PORT") or DEFAULT_PORT)
    except ValueError:
        port = DEFAULT_PORT
    return {
        "vault_dir": os.path.abspath(vault_dir or env.get("CIP_VAULT_DIR") or os.path.expanduser("~/cip_vault")),
        "port": port,
        "passphrase": env.get("VAULT_PASSPHRASE") or None,
        "api_key": env.get("ANTHROPIC_API_KEY") or None,
        "demo_mode": (env.get("CIP_DEMO_MODE") or "").strip() == "1",
        "port_base_url": env.get("PORT_BASE_URL") or DEFAULT_PORT_BASE_URL,
        "claude_model": env.get("CIP_CLAUDE_MODEL") or None,
        "law_dir": env.get("CIP_LAW_DIR") or None,   # 法令集の置き場（無ければ app_src/law_corpus）＝作成者が足した
        "app_root": os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    }


def build_app(env, vault_dir=None, clock=None, wire=True):
    """(router, app)。env は辞書で渡す（os.environ は読まない）。
    wire=True のとき、在れば claude_client / handoff の口を app につなぐ。"""
    clock = clock or time.time
    cfg = _make_cfg(env, vault_dir)
    configured = bool(cfg["passphrase"])
    # 設定なしのときは保存の場所にも触らない（fail-closed）
    vault = storage.open_vault(cfg["vault_dir"]) if configured else None
    sessions = httpkit.SessionStore(idle_seconds=IDLE_SECONDS, clock=clock)
    app = VaultApp(cfg, vault, sessions, clock)

    router = httpkit.Router()
    for m, p, h in routes_auth.ROUTES + routes_records.ROUTES:
        router.add(m, p, _wrap(h))
    for name in OPTIONAL_ROUTES:
        mod = _import_optional(name)
        if mod is not None:
            for m, p, h in mod.ROUTES:
                router.add(m, p, _wrap(h))

    if wire and configured:
        cc = _import_optional("claude_client")
        if cc is not None and hasattr(cc, "get_client"):
            got = cc.get_client(app)
            if app.claude is None:
                app.claude = got
        ho = _import_optional("handoff")
        if ho is not None and hasattr(ho, "get_port_client"):
            got = ho.get_port_client(app)
            if app.port_client is None:
                app.port_client = got
    return router, app


def main():
    env = dict(os.environ)
    router, app = build_app(env)
    cfg = app.cfg
    print("器: 127.0.0.1:%d ／ 合言葉 %s ／ 鍵 %s ／ デモ %s" % (
        cfg["port"],
        "あり" if cfg["passphrase"] else "なし（設定が ありません。）",
        "あり" if cfg["api_key"] else "なし",
        "入" if cfg["demo_mode"] else "切",
    ))
    httpkit.run_server(cfg["port"], router, STATIC_DIR, app)


if __name__ == "__main__":
    main()
