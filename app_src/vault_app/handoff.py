# -*- coding: utf-8 -*-
"""vault_app/handoff.py - 受け口へ出る唯一の部品（取り決めの 4 本だけ）。

ネットワークへ出る import は、この 1 本と claude_client.py の 2 本だけ。
  POST /v1/pair  /  POST /v1/bundles  /  GET /v1/bundles  /  GET /v1/replies?since=
token は vault.get_pairing_secret() から読むだけ（ログ・画面・束に書かない）。
"""
import json
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT_SECONDS = 15
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


class PortError(Exception):
    """通信の失敗。合言葉・token・本文を含めない。"""


class PortClient(object):
    def __init__(self, cfg, vault):
        self.cfg = cfg
        self.vault = vault

    def _url(self, path):
        base = (self.cfg.get("port_base_url") or "").rstrip("/")
        if not base:
            raise PortError("not_set")
        return base + path

    def _token(self):
        sec = self.vault.get_pairing_secret()
        tok = sec.get("token") if isinstance(sec, dict) else None
        if not isinstance(tok, str) or not tok:
            raise PortError("not_paired")
        return tok

    def _call(self, method, path, body=None, auth=False):
        """(状態の番号, JSON|None)。4xx・5xx も番号で返す。通信そのものの失敗だけ PortError。"""
        headers = {"Accept": "application/json"}
        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"
        if auth:
            headers["Authorization"] = "Bearer " + self._token()
        req = urllib.request.Request(self._url(path), data=data, method=method, headers=headers)
        try:
            try:
                with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as r:
                    status, raw = r.status, r.read(MAX_RESPONSE_BYTES)
            except urllib.error.HTTPError as e:
                status, raw = e.code, e.read(MAX_RESPONSE_BYTES)
                e.close()
        except PortError:
            raise
        except Exception:
            raise PortError("通信に失敗しました。") from None
        try:
            obj = json.loads(raw.decode("utf-8")) if raw else None
        except ValueError:
            obj = None
        return status, obj

    def pair(self, pairing_code):
        return self._call("POST", "/v1/pair", {"pairing_code": pairing_code})

    def post_bundle(self, bundle):
        return self._call("POST", "/v1/bundles", bundle, auth=True)

    def list_bundles(self):
        return self._call("GET", "/v1/bundles", auth=True)

    def get_replies(self, since=None):
        path = "/v1/replies"
        if since:
            path += "?since=" + urllib.parse.quote(since, safe="")
        return self._call("GET", path, auth=True)


def get_port_client(app):
    """app.port_client を返す。無ければ作って入れる。つなぎ先の設定が無ければ None。"""
    if app.port_client is not None:
        return app.port_client
    if not app.cfg.get("port_base_url"):
        return None
    app.port_client = PortClient(app.cfg, app.vault)
    return app.port_client
