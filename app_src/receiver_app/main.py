# -*- coding: utf-8 -*-
"""receiver_app/main.py - 参照用の受け口（別のプロセス・別の保存）。標準ライブラリだけ。

起動: app_src の親の場所で  python3 -B -m app_src.receiver_app.main
環境変数（名だけ）: PORT_PASSPHRASE PORT_ID PORT_NAME CIP_PORT_DIR CIP_PORT_PORT
設定が足りない（合言葉が 16 字未満・無い・空 / id / 名が無い）ときは、サーバーは立つが
/face/status が {"configured": false} を返し、/v1/* と面の操作は 503 not_configured（fail-closed）。
待ち受けは 127.0.0.1 だけ。
"""
import os
import threading
import time

from app_src.common import httpkit, ids
from app_src.receiver_app import routes_api, routes_face
from app_src.receiver_app.storage import Storage

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
MIN_PASSPHRASE_CHARS = 16
DEFAULT_PORT = 8766


class App(object):
    def __init__(self, env, dir_path, clock=None):
        self.clock = clock or time.time
        self.passphrase = env.get("PORT_PASSPHRASE") or ""
        self.port_id = (env.get("PORT_ID") or "").strip()
        self.port_name = (env.get("PORT_NAME") or "").strip()
        self.configured = bool(len(self.passphrase) >= MIN_PASSPHRASE_CHARS and self.port_id and self.port_name)
        self.dir_path = dir_path
        self.storage = Storage(dir_path) if self.configured else None
        self.sessions = httpkit.SessionStore(idle_seconds=routes_face.IDLE_SECONDS, clock=self.clock)
        self.auth_lock = threading.Lock()
        self.fail_count = 0
        self.locked_until = 0
        # 本人の不透明な id の作り方（テストが差し替える口）
        self.person_ref_factory = lambda: ids.new_id("pr")

    def log_http(self, line):
        """httpkit の行ログ。内部の失敗（500）だけを出来事として残す。"""
        if self.storage is not None and line.startswith("500 "):
            self.storage.log_event("server_error", status=500, ts=ids.now_jst(self.clock))


def build_app(env, dir_path, clock=None):
    """(router, app)。os.environ は読まない（環境は引数で渡す）。"""
    app = App(env, dir_path, clock)
    router = httpkit.Router()
    router.add_many(routes_api.ROUTES)
    router.add_many(routes_face.ROUTES)
    return router, app


def main():
    env = dict(os.environ)
    dir_path = env.get("CIP_PORT_DIR") or os.path.expanduser("~/cip_port_data")
    try:
        port = int(env.get("CIP_PORT_PORT") or DEFAULT_PORT)
    except ValueError:
        port = DEFAULT_PORT
    router, app = build_app(env, dir_path)
    if not app.configured:
        print("設定が ありません。(PORT_PASSPHRASE は 16 字以上、PORT_ID と PORT_NAME も必要です)")
    print("受け口: 127.0.0.1:%d" % port)
    httpkit.run_server(port, router, STATIC_DIR, app, log=app.log_http)


if __name__ == "__main__":
    main()
