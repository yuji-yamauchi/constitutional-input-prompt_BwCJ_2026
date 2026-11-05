# -*- coding: utf-8 -*-
"""vault_app/appctx.py — 器のアプリの文脈（共通）。

cfg の鍵（値はメモリだけ・ログと画面に出さない）:
  vault_dir, port, passphrase(str|None), api_key(str|None), demo_mode(bool),
  port_base_url(str), claude_model(str), app_root(app_src の絶対パス)
"""
import os
import threading


class VaultApp(object):
    def __init__(self, cfg, vault, sessions, clock):
        self.cfg = cfg
        self.vault = vault
        self.sessions = sessions
        self.clock = clock
        self.claude = None        # claude_client.get_client(app) が入れる
        self.port_client = None   # handoff.get_port_client(app) が入れる
        self.lock = None
        self.auth_lock = threading.Lock()   # 入口の失敗の数え方を守る
        self.fail_count = 0                 # 続けて違えた数
        self.locked_until = 0               # この時刻（clock の秒）まで入口を止める

    @property
    def app_root(self):
        return self.cfg.get("app_root") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def claude_state(self):
        """'demo' | 'ok' | 'no_key'（/api/status と画面の帯の旗）。"""
        if self.cfg.get("demo_mode"):
            return "demo"
        return "ok" if self.cfg.get("api_key") else "no_key"
