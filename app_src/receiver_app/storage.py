# -*- coding: utf-8 -*-
"""receiver_app/storage.py - 受け口の保存（標準ライブラリだけ）。

<dir>/bundles/<bundle_id>.json  受けた束そのまま + _received_at / _fingerprint_computed / _person_ref / _seq
<dir>/receipts/<bundle_id>.json 返した控え
<dir>/replies/<reply_id>.json   残した返事 + _seq
<dir>/pairings.json             合言葉と token は sha256 だけで持つ
<dir>/events.log                時刻・出来事の種類・bundle_id / reply_id・指紋・HTTP の番号だけ

書き込みは一時ファイル -> rename。JSON は ensure_ascii=False。
ログに書かない物: 合言葉・token・束の本文・原本・返事の本文・表示名・person_ref。
"""
import hmac
import json
import os
import re
import secrets
import threading
import time

from app_src.common import ids

SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_LOG_SAFE = re.compile(r"[^A-Za-z0-9._:+-]")


def is_safe_id(s):
    return isinstance(s, str) and SAFE_ID.match(s) is not None


def public_view(obj):
    """先頭が _ の内部の欄を除いた写し（外へ出す物）。"""
    return {k: v for k, v in obj.items() if not k.startswith("_")}


class Storage(object):
    def __init__(self, root):
        self.root = os.path.abspath(root)
        self.lock = threading.RLock()
        self._last_seq = 0
        for d in ("", "bundles", "receipts", "replies"):
            os.makedirs(os.path.join(self.root, d), mode=0o700, exist_ok=True)
        self._bundles = {}   # bundle_id -> 一覧用の控え（本文を持たない）
        self._replies = {}   # reply_id -> 返事（_seq つき）
        self._scan()

    # ---- 下請け ----
    def _p(self, *parts):
        return os.path.join(self.root, *parts)

    def next_seq(self):
        with self.lock:
            s = max(time.time_ns(), self._last_seq + 1)
            self._last_seq = s
            return s

    def _write_json(self, path, obj):
        tmp = "%s.tmp-%s" % (path, secrets.token_hex(4))
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        os.replace(tmp, path)

    def _read_json(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _scan(self):
        bdir = self._p("bundles")
        for name in sorted(os.listdir(bdir)):
            if not name.endswith(".json"):
                continue
            bid = name[:-5]
            try:
                b = self._read_json(os.path.join(bdir, name))
                rc = self._read_json(self._p("receipts", name))
                self._bundles[bid] = self._meta(b, rc)
            except Exception:
                continue   # 読めない物は無い物として扱う（再送で作り直せる）
        rdir = self._p("replies")
        for name in sorted(os.listdir(rdir)):
            if not name.endswith(".json"):
                continue
            try:
                r = self._read_json(os.path.join(rdir, name))
                self._replies[r["reply_id"]] = r
                self._last_seq = max(self._last_seq, int(r.get("_seq", 0)))
            except Exception:
                continue
        for m in self._bundles.values():
            self._last_seq = max(self._last_seq, m["seq"])

    @staticmethod
    def _meta(b, rc):
        return {
            "bundle_id": b["bundle_id"],
            "received_at": b["_received_at"],
            "seq": int(b.get("_seq", 0)),
            "person_ref": b["_person_ref"],
            "display_name": b["sender"].get("display_name", ""),
            "item_count": rc["item_count"],
            "fingerprint": b["_fingerprint_computed"],
            "receipt_id": rc["receipt_id"],
        }

    # ---- 束と控え ----
    def find_bundle(self, bundle_id):
        return self._bundles.get(bundle_id)

    def load_bundle(self, bundle_id):
        return self._read_json(self._p("bundles", bundle_id + ".json"))

    def load_receipt(self, bundle_id):
        return self._read_json(self._p("receipts", bundle_id + ".json"))

    def save_bundle(self, bundle, receipt, person_ref, fingerprint, received_at):
        """控えを先に・束を後に書く（途中で止まっても再送で作り直せる）。"""
        bid = bundle["bundle_id"]
        with self.lock:
            stored = dict(bundle)
            stored["_received_at"] = received_at
            stored["_fingerprint_computed"] = fingerprint
            stored["_person_ref"] = person_ref
            stored["_seq"] = self.next_seq()
            self._write_json(self._p("receipts", bid + ".json"), receipt)
            self._write_json(self._p("bundles", bid + ".json"), stored)
            self._bundles[bid] = self._meta(stored, receipt)

    def list_bundle_meta(self, person_ref=None):
        """新しい順。person_ref を渡すとその本人の分だけ。"""
        with self.lock:
            rows = [m for m in self._bundles.values() if person_ref is None or m["person_ref"] == person_ref]
        rows.sort(key=lambda m: m["seq"], reverse=True)
        return rows

    # ---- 返事 ----
    def save_reply(self, reply):
        with self.lock:
            stored = dict(reply)
            stored["_seq"] = self.next_seq()
            self._write_json(self._p("replies", reply["reply_id"] + ".json"), stored)
            self._replies[reply["reply_id"]] = stored
            return stored

    def replies_for(self, bundle_id):
        """新しい順（_seq を含む）。"""
        with self.lock:
            rows = [r for r in self._replies.values() if r.get("in_reply_to") == bundle_id]
        rows.sort(key=lambda r: r["_seq"], reverse=True)
        return rows

    def reply_count(self, bundle_id):
        with self.lock:
            return sum(1 for r in self._replies.values() if r.get("in_reply_to") == bundle_id)

    # ---- 合言葉と token（値は持たない・sha256 だけ）----
    def _load_pairings(self):
        try:
            return self._read_json(self._p("pairings.json"))
        except (OSError, ValueError):
            return []

    def add_pairing(self, code_sha256, created_at, expires_at):
        with self.lock:
            rows = self._load_pairings()
            rows.append({
                "code_sha256": code_sha256, "created_at": created_at, "expires_at": expires_at,
                "used_at": None, "person_ref": None, "token_sha256": None,
            })
            self._write_json(self._p("pairings.json"), rows)

    def consume_pairing(self, code_sha256, now_dt, now_text, person_ref, token_sha256):
        """未使用かつ期限内なら使用済みにして True。それ以外は False。"""
        with self.lock:
            rows = self._load_pairings()
            hit = None
            for row in rows:
                if hmac.compare_digest(row.get("code_sha256") or "", code_sha256):
                    hit = row
            if hit is None or hit.get("used_at") is not None:
                return False
            exp = ids.parse_iso(hit.get("expires_at") or "")
            if exp is None or now_dt > exp:
                return False
            hit["used_at"] = now_text
            hit["person_ref"] = person_ref
            hit["token_sha256"] = token_sha256
            self._write_json(self._p("pairings.json"), rows)
            return True

    def person_for_token(self, token_sha256):
        with self.lock:
            rows = self._load_pairings()
        found = None
        for row in rows:
            t = row.get("token_sha256")
            if t and hmac.compare_digest(t, token_sha256):
                found = row.get("person_ref")
        return found

    def pairing_rows(self):
        """値なしの一覧の元（新しい順）。"""
        with self.lock:
            rows = self._load_pairings()
        return list(reversed(rows))

    # ---- 出来事のログ ----
    def log_event(self, kind, bundle_id=None, reply_id=None, fingerprint=None, status=None, ts=None):
        def clean(v):
            if v is None or v == "":
                return "-"
            return _LOG_SAFE.sub("_", str(v))[:140]
        line = "\t".join([clean(ts or ids.now_jst()), clean(kind), clean(bundle_id), clean(reply_id),
                          clean(fingerprint), clean(status)])
        with self.lock:
            with open(self._p("events.log"), "a", encoding="utf-8") as f:
                f.write(line + "\n")
