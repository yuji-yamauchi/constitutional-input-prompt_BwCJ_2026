# -*- coding: utf-8 -*-
"""common/ids.py — 識別子と時刻（標準ライブラリだけ）。

- new_id(prefix) : 時刻（UTC の秒・16 進 8 桁）＋乱数（16 進 16 桁）。uuid の形は使わない（公開の縁の走査に掛からない形）。
- now_jst()      : 日本時間の ISO 8601（秒まで・+09:00 つき）。取り決めの時刻の欄はこの字。
- today_jst()    : YYYY-MM-DD（日本時間）。
"""
import secrets, time, datetime

JST = datetime.timezone(datetime.timedelta(hours=9))


def new_id(prefix=""):
    t = "%08x" % int(time.time())
    r = secrets.token_hex(8)
    return ("%s-%s%s" % (prefix, t, r)) if prefix else (t + r)


def now_jst(clock=None):
    ts = clock() if clock else time.time()
    return datetime.datetime.fromtimestamp(ts, JST).isoformat(timespec="seconds")


def today_jst(clock=None):
    ts = clock() if clock else time.time()
    return datetime.datetime.fromtimestamp(ts, JST).date().isoformat()


def parse_iso(s):
    """ISO 8601 の字 → aware な datetime。読めなければ None。"""
    try:
        return datetime.datetime.fromisoformat(s)
    except Exception:
        return None
