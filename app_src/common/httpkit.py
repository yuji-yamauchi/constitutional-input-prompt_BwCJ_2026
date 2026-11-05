# -*- coding: utf-8 -*-
"""common/httpkit.py — http.server の小さな助け（標準ライブラリだけ）。

器（vault_app）と受け口（receiver_app）の両方が使う。
- Router: 経路の表（"/api/records/{id}" の形の照合）
- Request: 1 回の要求（JSON の読み・query・cookie・app への参照）
- Response: bytes を返すとき（画像・zip）
- HttpError: 状態の番号＋短い字（JSON で返る）
- SessionStore: cookie の token と「最後の操作の時刻」（無操作の時間切れ）
- make_handler / run_server: 起動

注: ここにはネットワークへ**出る**コードは無い（待ち受けだけ）。
注: 待ち受けは 127.0.0.1 だけ。
"""
import json, os, re, secrets, threading, time, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http import cookies as _cookies

MAX_JSON_BYTES_DEFAULT = 26 * 1024 * 1024   # 束の上限 25 MB ＋ 余白
DRAIN_MAX_BYTES = 1024 * 1024               # 読まずに返すとき、読み捨てる本文の上限（これ以上は接続を閉じる）
NO_STORE = "no-store"
STATIC_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".txt": "text/plain; charset=utf-8",
    ".ico": "image/x-icon",
}
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": NO_STORE,
    "Content-Security-Policy": "default-src 'self'; img-src 'self' data: blob:; style-src 'self'; script-src 'self'; connect-src 'self'; font-src 'self' data:; frame-ancestors 'none'; form-action 'self'; base-uri 'none'",
    "X-Frame-Options": "DENY",
}


# 手元の名だけ通す（外の名で来た要求は 421）。Host が無い要求は通す。
HOST_RE = re.compile(r"^(127\.0\.0\.1|localhost|\[::1\])(:[0-9]{1,5})?$", re.I)
MISDIRECTED_BODY = {"error": "misdirected", "detail": "この 入口は 手元の 画面からだけ 開けます。"}


def host_allowed(value):
    if value is None:
        return True
    return bool(HOST_RE.match(value.strip()))


class HttpError(Exception):
    def __init__(self, status, code, message=""):
        super().__init__(code)
        self.status = status
        self.code = code
        self.message = message or code


class Response(object):
    """bytes を返すとき。"""
    def __init__(self, status, body, content_type, headers=None):
        self.status = status
        self.body = body
        self.content_type = content_type
        self.headers = headers or {}


class Router(object):
    def __init__(self):
        self._routes = []  # (method, regex, keys, handler)

    def add(self, method, pattern, handler):
        keys = re.findall(r"\{(\w+)\}", pattern)
        rx = "^" + re.sub(r"\{\w+\}", r"([^/]+)", pattern) + "$"
        self._routes.append((method.upper(), re.compile(rx), keys, handler))

    def add_many(self, routes):
        for m, p, h in routes:
            self.add(m, p, h)

    def match(self, method, path):
        allowed = False
        for m, rx, keys, h in self._routes:
            mo = rx.match(path)
            if not mo:
                continue
            if m != method.upper():
                allowed = True
                continue
            return h, dict(zip(keys, [urllib.parse.unquote(v) for v in mo.groups()]))
        if allowed:
            raise HttpError(405, "method_not_allowed")
        return None, None


class SessionStore(object):
    """cookie の token → 最後の操作の時刻。無操作が idle_seconds を超えたら切れる。"""
    def __init__(self, idle_seconds=15 * 60, clock=time.time):
        self.idle = idle_seconds
        self.clock = clock
        self._lock = threading.Lock()
        self._s = {}

    def create(self):
        tok = secrets.token_hex(32)
        with self._lock:
            self._s[tok] = self.clock()
        return tok

    def touch(self, tok):
        """生きていれば時計を巻き戻して True。切れていれば消して False。"""
        if not tok:
            return False
        with self._lock:
            t = self._s.get(tok)
            now = self.clock()
            if t is None:
                return False
            if now - t > self.idle:
                del self._s[tok]
                return False
            self._s[tok] = now
            return True

    def drop(self, tok):
        with self._lock:
            self._s.pop(tok, None)

    def drop_all(self):
        with self._lock:
            self._s.clear()


class Request(object):
    def __init__(self, handler, params):
        self.h = handler
        self.app = handler.server.app
        self.params = params
        u = urllib.parse.urlsplit(handler.path)
        self.path = u.path
        self.query = dict(urllib.parse.parse_qsl(u.query, keep_blank_values=True))
        self.headers = handler.headers
        self.method = handler.command
        self._json = None
        self._raw = None

    def raw(self, limit=MAX_JSON_BYTES_DEFAULT):
        if self._raw is None:
            n = int(self.headers.get("Content-Length") or 0)
            if n > limit:
                raise HttpError(413, "too_large")
            self._raw = self.h.rfile.read(n) if n > 0 else b""
            self.h._body_read = True
        return self._raw

    def json(self, limit=MAX_JSON_BYTES_DEFAULT):
        if self._json is None:
            ct = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if ct != "application/json":
                raise HttpError(415, "unsupported_media_type")
            raw = self.raw(limit)
            try:
                self._json = json.loads(raw.decode("utf-8")) if raw else {}
            except Exception:
                raise HttpError(400, "bad_json")
        return self._json

    def cookie(self, name):
        c = _cookies.SimpleCookie()
        try:
            c.load(self.headers.get("Cookie") or "")
        except Exception:
            return None
        m = c.get(name)
        return m.value if m else None

    def bearer(self):
        a = self.headers.get("Authorization") or ""
        if a.lower().startswith("bearer "):
            return a[7:].strip()
        return None


def set_cookie_header(name, value, max_age=None, clear=False):
    parts = ["%s=%s" % (name, "" if clear else value), "Path=/", "HttpOnly", "SameSite=Strict"]
    if clear:
        parts.append("Max-Age=0")
    elif max_age is not None:
        parts.append("Max-Age=%d" % max_age)
    return ("Set-Cookie", "; ".join(parts))


def _safe_static_path(static_dir, url_path):
    rel = urllib.parse.unquote(url_path).lstrip("/") or "index.html"
    if rel.endswith("/"):
        rel += "index.html"
    full = os.path.normpath(os.path.join(static_dir, rel))
    if not (full == static_dir or full.startswith(static_dir + os.sep)):
        return None
    if not os.path.isfile(full):
        return None
    return full


def make_handler():
    class Handler(BaseHTTPRequestHandler):
        server_version = "cip/0.1"
        sys_version = ""
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):  # 既定のログ（要求の行）を出さない＝本文や query の字を残さない
            logger = getattr(self.server, "log", None)
            if logger:
                try:
                    logger("%s %s %s" % (self.command, urllib.parse.urlsplit(self.path).path, args[1] if len(args) > 1 else ""))
                except Exception:
                    pass

        def _drain_body(self):
            """本文を読まずに返すときも、同じ接続（keep-alive）が壊れないように読み捨てる。大きすぎる物は接続を閉じる。"""
            if getattr(self, "_body_read", False):
                return
            self._body_read = True
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except Exception:
                n = 0
            if n <= 0:
                return
            if n > DRAIN_MAX_BYTES:   # 読まずに返した大きな本文＝読み捨てず接続を閉じる（413 など）
                self.close_connection = True
                return
            try:
                left = n
                while left > 0:
                    chunk = self.rfile.read(min(left, 65536))
                    if not chunk:
                        break
                    left -= len(chunk)
            except Exception:
                self.close_connection = True

        def _send(self, status, body, content_type, extra=None):
            self._drain_body()
            self.send_response(status)
            for k, v in SECURITY_HEADERS.items():
                self.send_header(k, v)
            if extra:
                for k, v in extra:
                    self.send_header(k, v)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _json(self, status, obj, extra=None):
            body = json.dumps(obj, ensure_ascii=False).encode("utf-8") if obj is not None else b""
            self._send(status, body, "application/json; charset=utf-8", extra)

        def _dispatch(self):
            if not host_allowed(self.headers.get("Host")):
                return self._json(421, MISDIRECTED_BODY)
            router = self.server.router
            path = urllib.parse.urlsplit(self.path).path
            try:
                handler, params = router.match(self.command, path)
                if handler is None:
                    if self.command in ("GET", "HEAD") and self.server.static_dir:
                        full = _safe_static_path(self.server.static_dir, path)
                        if full:
                            with open(full, "rb") as f:
                                data = f.read()
                            ct = STATIC_TYPES.get(os.path.splitext(full)[1].lower(), "application/octet-stream")
                            return self._send(200, data, ct)
                    raise HttpError(404, "not_found")
                req = Request(self, params)
                result = handler(req)
                if isinstance(result, Response):
                    return self._send(result.status, result.body, result.content_type, list(result.headers.items()))
                if isinstance(result, tuple):
                    status, obj = result[0], result[1]
                    extra = result[2] if len(result) > 2 else None
                    return self._json(status, obj, extra)
                return self._json(200, result)
            except HttpError as e:
                return self._json(e.status, {"error": e.code, "detail": e.message})
            except Exception as e:  # 中身を外に出さない
                logger = getattr(self.server, "log", None)
                if logger:
                    try:
                        logger("500 %s" % type(e).__name__)
                    except Exception:
                        pass
                return self._json(500, {"error": "internal", "detail": "いまは処理できません。"})

        do_GET = _dispatch
        do_POST = _dispatch
        do_PUT = _dispatch
        do_DELETE = _dispatch
        do_HEAD = _dispatch

    return Handler


class AppServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, addr, router, static_dir, app, log=None):
        super().__init__(addr, make_handler())
        self.router = router
        self.static_dir = os.path.abspath(static_dir) if static_dir else None
        self.app = app
        self.log = log


def make_server(port, router, static_dir, app, host="127.0.0.1", log=None):
    """port=0 ならテスト用に空いている番号を取る。serve_forever は呼ぶ側で。"""
    return AppServer((host, port), router, static_dir, app, log)


def run_server(port, router, static_dir, app, host="127.0.0.1", log=None):
    srv = make_server(port, router, static_dir, app, host, log)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
