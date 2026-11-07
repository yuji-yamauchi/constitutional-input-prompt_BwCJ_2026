# -*- coding: utf-8 -*-
"""vault_app/storage.py — 器の保存（cip-export-v1 の形そのもの）。標準ライブラリだけ。

形と関数の名は 保存の形の決まりのとおり。持ち出しの数え方は 渡す口の取り決めと同じ。
- 書き込みは「一時ファイルに書いて rename」（途中で落ちても壊れない）。
- 原本は一度書いたら書き換えない（同じ record_id に再度 add は OriginalExists）。
- JSON は ensure_ascii=False・インデント 1。
- ネットワークへ出るコードは無い。
"""
import datetime, json, os, re, shutil, threading, zipfile

from app_src.common import contract, ids

MEDIA_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/svg+xml": "svg",
}
MARKS = ("残った", "一部", "残らなかった", "なし")
DISPOSITIONS = ("unread", "bound", "discarded")
RECEIPT_STATUSES = ("confirmed", "unconfirmed", "unsent")
CLAUDE_LOG_KEYS = ("at", "kind", "what", "bytes", "model", "demo")
CONDITION_NAMES = ("amount", "split", "topic_free")
SECRET_NAME = "pairing.secret.json"
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_TIME_RE = re.compile(r"([01][0-9]|2[0-3]):[0-5][0-9]")
BREAKFAST_VALUES = ("yes", "no")


class OriginalExists(FileExistsError):
    """同じ record_id の原本は書き換えない。"""


class UnknownTurn(KeyError):
    """印を付ける先の turn が無い。"""


class ExportCountMismatch(Exception):
    """持ち出しの中を数え直した数が manifest.counts と違う。"""


# ---------------------------------------------------------------- 部品

def _check_id(value, what="id"):
    if not isinstance(value, str) or not _ID_RE.match(value):
        raise ValueError("%s の形が正しくない" % what)
    return value


def _dumps(obj):
    return json.dumps(obj, ensure_ascii=False, indent=1) + "\n"


def ensure_dir(path):
    """フォルダを 0o700 で作る（途中で作った物も）。効かない環境（Windows など）でも例外にしない。"""
    todo = []
    p = os.path.abspath(path)
    while not os.path.isdir(p):
        todo.append(p)
        parent = os.path.dirname(p)
        if parent == p:
            break
        p = parent
    os.makedirs(path, mode=0o700, exist_ok=True)
    for q in todo:
        try:
            os.chmod(q, 0o700)
        except OSError:
            pass


def _atomic_write(path, data):
    """一時ファイルに書いて rename。data は bytes か str。ファイルは 0o600・フォルダは 0o700。"""
    if isinstance(data, str):
        data = data.encode("utf-8")
    d = os.path.dirname(path)
    ensure_dir(d)
    tmp = os.path.join(d, ".%s.%s.tmp" % (os.path.basename(path), ids.new_id()))
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _write_json(path, obj):
    _atomic_write(path, _dumps(obj))


def _read_json(path, default=None):
    try:
        with open(path, "rb") as f:
            return json.loads(f.read().decode("utf-8"))
    except FileNotFoundError:
        return default


def statement_markdown(item):
    """本人の最終版の字を読める形に（見出し＝作った日・主語の欄・本文）。持ち出しの zip の statements/<id>.md。"""
    who = {"person": "本人"}.get(item.get("author"), "")
    body = item.get("text") if item.get("finalized_at") else ""
    if not isinstance(body, str) or body.strip() == "":
        body = "（最終版は まだ ありません）"
    return "# 意思表出文\n\n## 作った日\n%s\n\n## 主語の欄\n%s\n\n## 本文\n%s\n" % (item.get("created_at") or "", who, body)


def condition_key(conditions):
    """条件 → "amount=少なく|split=true|topic_free=false"（鍵の名の順）。"""
    if not isinstance(conditions, dict):
        raise ValueError("conditions は辞書")
    parts = []
    for k in sorted(conditions):
        v = conditions[k]
        if isinstance(v, bool):
            v = "true" if v else "false"
        parts.append("%s=%s" % (k, v))
    return "|".join(parts)


def count_from_files(names, read):
    """持ち出しと同じ数え方（保存の形の決まり）。names=相対パス(/区切り)の並び・read(name)->bytes。"""
    c = {k: 0 for k in contract.EXPORT_COUNT_KEYS}
    for n in names:
        parts = n.split("/")
        base = parts[-1]
        if len(parts) == 3 and parts[0] == "records":
            if base == "original.json":
                c["originals"] += 1
            elif base == "derived.md":
                c["derived"] += 1
            elif base == "subject.json":
                c["subject_fields"] += 1
            elif base == "annotations.json":
                data = json.loads(read(n).decode("utf-8"))
                c["annotations"] += len(data)
        elif n == "practice/marks.json":
            c["marks"] += len(json.loads(read(n).decode("utf-8")))
        elif len(parts) == 2 and parts[0] == "statements" and base.endswith(".json"):
            c["statements"] += 1
        elif len(parts) == 3 and parts[0] == "handoffs" and base == "bundle.json":
            c["handoffs"] += 1
        elif len(parts) == 2 and parts[0] == "replies" and base.endswith(".json"):
            c["replies"] += 1
    return c


def count_extra_from_files(names):
    """cip-export-v1 の 8 鍵の外の数え物（counts_extra）。きょうの こと（daily/<日付>.json）と きょうの 気分（kibun/<日付>.json）の 日の 数。"""
    n = 0
    k = 0
    for name in names:
        parts = name.split("/")
        if len(parts) == 2 and parts[1].endswith(".json") and not parts[1].startswith("."):
            if parts[0] == "daily":
                n += 1
            elif parts[0] == "kibun":
                k += 1
    return {"daily": n, "kibun": k}


def _check_date(value):
    """YYYY-MM-DD で、実在の日。違えば ValueError。"""
    if not isinstance(value, str) or not _DATE_RE.fullmatch(value):
        raise ValueError("date の形が正しくない")
    try:
        datetime.date(int(value[:4]), int(value[5:7]), int(value[8:10]))
    except ValueError:
        raise ValueError("date が実在の日でない") from None
    return value


def _check_hhmm(value, what):
    if value is None:
        return None
    if not isinstance(value, str) or not _TIME_RE.fullmatch(value):
        raise ValueError("%s の形が正しくない" % what)
    return value


def verify_export_zip(zip_path):
    """zip の中を数え直して manifest.counts と比べる。違えば ExportCountMismatch。counts を返す。"""
    with zipfile.ZipFile(zip_path) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        if "manifest.json" not in names:
            raise ExportCountMismatch("manifest.json が zip に無い")
        manifest = json.loads(z.read("manifest.json").decode("utf-8"))
        counted = count_from_files(names, z.read)
        counted_extra = count_extra_from_files(names)
    if not contract.export_manifest_ok(manifest, counted):
        raise ExportCountMismatch("manifest.counts=%s 数え直し=%s" % (manifest.get("counts"), counted))
    extra = manifest.get("counts_extra")
    if not isinstance(extra, dict):
        extra = {}
    for k in ("daily", "kibun"):
        if extra.get(k, 0) != counted_extra[k]:          # 欄が無い＝0 と読む（在るのに欄が無ければ不一致）
            raise ExportCountMismatch("manifest.counts_extra=%s 数え直し=%s" % (extra, counted_extra))
    return counted


# ---------------------------------------------------------------- 器

def open_vault(dir_path):
    return Vault(dir_path)


class Vault:
    def __init__(self, dir_path):
        self.root = os.path.abspath(str(dir_path))
        self._lock = threading.RLock()
        ensure_dir(self.root)
        if not os.path.exists(self._p("manifest.json")):
            self.write_manifest()

    # ---- パス
    def _p(self, *parts):
        return os.path.join(self.root, *parts)

    def _rec_dir(self, record_id):
        return self._p("records", _check_id(record_id, "record_id"))

    def _need_record(self, record_id):
        d = self._rec_dir(record_id)
        if not os.path.isfile(os.path.join(d, "original.json")):
            raise KeyError("記録が無い: " + record_id)
        return d

    # ---- 数え上げ・manifest
    def _names(self):
        out = []
        for base, dirs, files in os.walk(self.root):
            for f in files:
                if f.endswith(".tmp") or f == SECRET_NAME:
                    continue
                rel = os.path.relpath(os.path.join(base, f), self.root)
                out.append(rel.replace(os.sep, "/"))
        return sorted(out)

    def counts(self):
        with self._lock:
            def read(n):
                with open(self._p(*n.split("/")), "rb") as f:
                    return f.read()
            return count_from_files(self._names(), read)

    def counts_extra(self):
        with self._lock:
            return count_extra_from_files(self._names())

    def write_manifest(self):
        with self._lock:
            m = {
                "export_version": contract.EXPORT_VERSION,
                "counts": self.counts(),
                "counts_extra": self.counts_extra(),
                "updated_at": ids.now_jst(),
            }
            _write_json(self._p("manifest.json"), m)
            return m

    def read_manifest(self):
        return _read_json(self._p("manifest.json"))

    # ---- B: 記録
    def add_record(self, record_name, media_type, data, taken_at=None, record_id=None):
        if media_type not in MEDIA_EXT:
            raise ValueError("media_type が許す形でない")
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("data は bytes")
        data = bytes(data)
        if len(data) == 0:
            raise ValueError("原本が空")
        if len(data) > contract.MAX_ORIGINAL_BYTES:
            raise ValueError("原本が 5 MB を超える")
        if not isinstance(record_name, str) or not record_name.strip():
            raise ValueError("record_name が空")
        with self._lock:
            rid = _check_id(record_id, "record_id") if record_id else ids.new_id("rec")
            d = self._rec_dir(rid)
            ensure_dir(os.path.dirname(d))
            try:
                os.mkdir(d, 0o700)
            except FileExistsError:
                raise OriginalExists("原本は書き換えない: " + rid)
            try:
                os.chmod(d, 0o700)
            except OSError:
                pass
            sha = contract.sha256_hex(data)
            _atomic_write(os.path.join(d, "original." + MEDIA_EXT[media_type]), data)
            meta = {
                "media_type": media_type,
                "sha256": sha,
                "bytes": len(data),
                "taken_at": taken_at,
                "imported_at": ids.now_jst(),
                "record_name": record_name,
            }
            _write_json(os.path.join(d, "original.json"), meta)
            self.write_manifest()
            return rid

    def _original_path(self, record_id):
        d = self._need_record(record_id)
        meta = _read_json(os.path.join(d, "original.json"))
        return os.path.join(d, "original." + MEDIA_EXT[meta["media_type"]]), meta

    def read_original(self, record_id):
        """(bytes, media_type)。"""
        path, meta = self._original_path(record_id)
        with open(path, "rb") as f:
            return f.read(), meta["media_type"]

    def verify_original(self, record_id):
        path, meta = self._original_path(record_id)
        try:
            with open(path, "rb") as f:
                raw = f.read()
        except FileNotFoundError:
            return False
        return contract.sha256_hex(raw) == meta["sha256"] and len(raw) == meta["bytes"]

    def get_record(self, record_id):
        d = self._need_record(record_id)
        out = {"record_id": record_id, "original": _read_json(os.path.join(d, "original.json"))}
        dj = _read_json(os.path.join(d, "derived.json"))
        if dj is not None:
            try:
                with open(os.path.join(d, "derived.md"), "rb") as f:
                    lines = f.read().decode("utf-8").split("\n")
                dj = dict(dj, markdown="\n".join(lines[3:]))
            except FileNotFoundError:
                dj = None
        out["derived"] = dj
        out["subject"] = _read_json(os.path.join(d, "subject.json"))
        out["annotations"] = _read_json(os.path.join(d, "annotations.json"), [])
        return out

    def list_records(self):
        base = self._p("records")
        if not os.path.isdir(base):
            return []
        recs = []
        for rid in os.listdir(base):
            if _ID_RE.match(rid) and os.path.isfile(os.path.join(base, rid, "original.json")):
                recs.append(self.get_record(rid))
        recs.sort(key=lambda r: (r["original"].get("imported_at") or "", r["record_id"]), reverse=True)
        return recs

    def set_derived(self, record_id, markdown, meta=None):
        meta = meta or {}
        if not isinstance(markdown, str):
            raise TypeError("markdown は str")
        with self._lock:
            d = self._need_record(record_id)
            orig = _read_json(os.path.join(d, "original.json"))
            text = "%s\noriginal_sha256: %s\n\n%s" % (contract.DERIVED_LABEL, orig["sha256"], markdown)
            _atomic_write(os.path.join(d, "derived.md"), text)
            _write_json(os.path.join(d, "derived.json"), {
                "label": contract.DERIVED_LABEL,
                "generated_at": meta.get("generated_at") or ids.now_jst(),
                "sha256": contract.sha256_hex(markdown.encode("utf-8")),
                "model": meta.get("model"),
                "prompt_sha256": meta.get("prompt_sha256"),
                "demo": bool(meta.get("demo", False)),
            })
            self.write_manifest()

    def set_subject(self, record_id, fields):
        need = ("author_role", "written_at", "procedure", "confirmed_by_person")
        if not isinstance(fields, dict):
            raise ValueError("fields は辞書")
        for k in need:
            if k not in fields:
                raise ValueError("欄が無い: " + k)
        if not isinstance(fields["confirmed_by_person"], bool):
            raise ValueError("confirmed_by_person は true/false")
        with self._lock:
            d = self._need_record(record_id)
            _write_json(os.path.join(d, "subject.json"), {k: fields[k] for k in need})
            self.write_manifest()

    def add_annotation(self, record_id, text):
        if not isinstance(text, str) or not text.strip():
            raise ValueError("注記が空")
        with self._lock:
            d = self._need_record(record_id)
            path = os.path.join(d, "annotations.json")
            items = _read_json(path, [])
            entry = {"text": text, "written_at": ids.now_jst(), "author": "person"}
            items.append(entry)
            _write_json(path, items)
            self.write_manifest()
            return entry

    def add_reply_annotation(self, record_id, text):
        """綴じた返事の記録（records/<id>/reply.json）への注記。保存先は写真と同じ annotations.json。"""
        if not isinstance(text, str) or not text.strip():
            raise ValueError("注記が空")
        with self._lock:
            d = self._rec_dir(record_id)
            if not os.path.isfile(os.path.join(d, "reply.json")):
                raise KeyError("記録が無い: " + record_id)
            path = os.path.join(d, "annotations.json")
            items = _read_json(path, [])
            entry = {"text": text, "written_at": ids.now_jst(), "author": "person"}
            items.append(entry)
            _write_json(path, items)
            self.write_manifest()
            return entry

    def delete_record(self, record_id):
        with self._lock:
            d = self._need_record(record_id)
            shutil.rmtree(d)
            self.write_manifest()

    # ---- A: 練習
    def add_turn(self, conditions, text, readback, question=None, question_dropped_reason=None,
                 direction=None, shared_daily=False):
        """direction＝問いの向き（無ければ None）・shared_daily＝きょうの ことを添えたか（真偽だけ。値は書かない）。"""
        condition_key(conditions)
        with self._lock:
            tid = ids.new_id("turn")
            _write_json(self._p("practice", "turns", tid + ".json"), {
                "at": ids.now_jst(),
                "conditions": conditions,
                "text": text,
                "readback": readback,
                "question": question,
                "question_dropped_reason": question_dropped_reason,
                "direction": direction,
                "shared_daily": bool(shared_daily),
            })
            return tid

    def get_turn(self, turn_id):
        return _read_json(self._p("practice", "turns", _check_id(turn_id, "turn_id") + ".json"))

    def add_mark(self, turn_id, mark):
        if mark not in MARKS:
            raise ValueError("mark が許す字でない")
        with self._lock:
            turn = self.get_turn(turn_id)
            if turn is None:
                raise UnknownTurn("turn が無い: " + str(turn_id))
            path = self._p("practice", "marks.json")
            items = _read_json(path, [])
            entry = {
                "turn_id": turn_id,
                "at": ids.now_jst(),
                "conditions": turn["conditions"],
                "mark": mark,
                "text_sha256": contract.sha256_hex(str(turn["text"]).encode("utf-8")),
            }
            items.append(entry)
            _write_json(path, items)
            self.write_manifest()
            return entry

    def practice_summary(self):
        out = {}
        for m in _read_json(self._p("practice", "marks.json"), []):
            row = out.setdefault(condition_key(m["conditions"]), {})
            row[m["mark"]] = row.get(m["mark"], 0) + 1
        return out

    # ---- きょうの こと（daily/<日付>.json・本人の箱。束には入れない）
    def _daily_path(self, date):
        return self._p("daily", _check_date(date) + ".json")

    def get_daily(self, date):
        path = self._daily_path(date)
        row = _read_json(path)
        if not isinstance(row, dict):
            return {"date": date, "bed_time": None, "wake_time": None, "breakfast": None, "updated_at": None}
        return {
            "date": date,
            "bed_time": row.get("bed_time"),
            "wake_time": row.get("wake_time"),
            "breakfast": row.get("breakfast"),
            "updated_at": row.get("updated_at"),
        }

    def set_daily(self, date, bed_time, wake_time, breakfast):
        path = self._daily_path(date)
        _check_hhmm(bed_time, "bed_time")
        _check_hhmm(wake_time, "wake_time")
        if breakfast is not None and (not isinstance(breakfast, str) or breakfast not in BREAKFAST_VALUES):
            raise ValueError("breakfast は yes か no か null")
        with self._lock:
            if bed_time is None and wake_time is None and breakfast is None:
                try:
                    os.unlink(path)
                except FileNotFoundError:
                    pass
                self.write_manifest()
                return self.get_daily(date)
            _write_json(path, {
                "date": date,
                "bed_time": bed_time,
                "wake_time": wake_time,
                "breakfast": breakfast,
                "updated_at": ids.now_jst(),
            })
            self.write_manifest()
            return self.get_daily(date)

    # ---- きょうの 気分（kibun/<日付>.json・本人の箱。束には入れない。点を つけない）
    def _kibun_path(self, date):
        return self._p("kibun", _check_date(date) + ".json")

    def get_kibun_day(self, date):
        """その日の 回の 並び。無ければ 空。"""
        row = _read_json(self._kibun_path(date))
        runs = row.get("runs") if isinstance(row, dict) else None
        return {"date": date, "runs": runs if isinstance(runs, list) else []}

    def upsert_kibun_run(self, date, run_id, count, start_id, version, answers, finished):
        """回を 1 つ 書く（run_id が None なら 新しく 作る・在れば 中身を 置き換える）。答えの 中身の 検査は 経路が 済ませている。
        返り＝書いた 回。run_id が 在るのに 見つからなければ KeyError。"""
        path = self._kibun_path(date)
        with self._lock:
            day = self.get_kibun_day(date)
            now = ids.now_jst()
            if run_id is None:
                run = {"run_id": ids.new_id(), "started_at": now}
                day["runs"].append(run)
            else:
                _check_id(run_id, "run_id")
                found = [r for r in day["runs"] if isinstance(r, dict) and r.get("run_id") == run_id]
                if not found:
                    raise KeyError("回が無い: " + run_id)
                run = found[0]
            run["updated_at"] = now
            run["finished_at"] = now if finished else None
            run["count"] = int(count)
            run["start_id"] = int(start_id)
            run["version"] = version
            run["answers"] = [{"id": int(a["id"]), "choice": a["choice"]} for a in answers]
            _write_json(path, {"date": date, "runs": day["runs"]})
            self.write_manifest()
            return dict(run)

    def kibun_last_answered_id(self):
        """いちばん 新しく 書いた 回の、最後に 答えた 問いの id。何も 無ければ None（「前回の 続きから」の 材料）。"""
        best = None
        base = self._p("kibun")
        try:
            names = os.listdir(base)
        except FileNotFoundError:
            return None
        for n in sorted(names):
            if not n.endswith(".json") or n.startswith("."):
                continue
            row = _read_json(os.path.join(base, n))
            runs = row.get("runs") if isinstance(row, dict) else None
            for r in runs or []:
                if not (isinstance(r, dict) and isinstance(r.get("answers"), list) and r["answers"]):
                    continue
                stamp = str(r.get("updated_at") or "")
                if best is None or stamp >= best[0]:      # 同じ 秒なら 後に 並ぶ 回（新しい 方）
                    best = (stamp, r["answers"][-1].get("id"))
        return best[1] if best else None

    # ---- C: 意思表出文
    def save_statement(self, item):
        if not isinstance(item, dict):
            raise ValueError("item は辞書")
        with self._lock:
            sid = _check_id(item.get("item_id") or ids.new_id("st"), "item_id")
            item = dict(item, item_id=sid)
            _write_json(self._p("statements", sid + ".json"), item)
            self.write_manifest()
            return sid

    def get_statement(self, item_id):
        return _read_json(self._p("statements", _check_id(item_id, "item_id") + ".json"))

    def list_statements(self):
        """新しい順（最後に保存した順）。"""
        base = self._p("statements")
        if not os.path.isdir(base):
            return []
        rows = []
        for f in os.listdir(base):
            if f.endswith(".json") and not f.startswith("."):
                p = os.path.join(base, f)
                rows.append((os.stat(p).st_mtime_ns, f, _read_json(p)))
        rows.sort(key=lambda r: (r[0], r[1]), reverse=True)
        return [r[2] for r in rows]

    # ---- 渡す口
    def save_handoff(self, bundle, receipt=None):
        bid = _check_id(bundle.get("bundle_id"), "bundle_id")
        if receipt is None:
            receipt = {"status": "unsent"}
        if receipt.get("status") not in RECEIPT_STATUSES:
            raise ValueError("receipt.status が confirmed/unconfirmed/unsent でない")
        with self._lock:
            d = self._p("handoffs", bid)
            _write_json(os.path.join(d, "bundle.json"), bundle)
            _write_json(os.path.join(d, "receipt.json"), receipt)
            self.write_manifest()
            return bid

    def list_handoffs(self):
        base = self._p("handoffs")
        if not os.path.isdir(base):
            return []
        rows = []
        for bid in os.listdir(base):
            b = _read_json(os.path.join(base, bid, "bundle.json"))
            if b is not None:
                rows.append({"bundle_id": bid, "bundle": b,
                             "receipt": _read_json(os.path.join(base, bid, "receipt.json"), {"status": "unsent"})})
        rows.sort(key=lambda r: (r["bundle"].get("created_at") or "", r["bundle_id"]), reverse=True)
        return rows

    def save_reply(self, reply):
        rid = _check_id(reply.get("reply_id"), "reply_id")
        with self._lock:
            path = self._p("replies", rid + ".json")
            old = _read_json(path)
            if old is not None:
                return old   # 読み直しで同じ返事が来ても、本人が付けた扱いを戻さない
            row = dict(reply)
            row.setdefault("disposition", "unread")
            if row["disposition"] not in DISPOSITIONS:
                raise ValueError("disposition が許す字でない")
            _write_json(path, row)
            self.write_manifest()
            return row

    def set_reply_disposition(self, reply_id, disposition, bound_record_id=None):
        if disposition not in DISPOSITIONS:
            raise ValueError("disposition が許す字でない")
        if disposition == "bound" and not bound_record_id:
            raise ValueError("bound には bound_record_id が要る")
        with self._lock:
            path = self._p("replies", _check_id(reply_id, "reply_id") + ".json")
            row = _read_json(path)
            if row is None:
                raise KeyError("返事が無い: " + reply_id)
            row["disposition"] = disposition
            if disposition == "bound":
                row["bound_record_id"] = bound_record_id
            else:
                row.pop("bound_record_id", None)
            _write_json(path, row)
            self.write_manifest()
            return row

    def list_replies(self):
        base = self._p("replies")
        if not os.path.isdir(base):
            return []
        rows = [_read_json(os.path.join(base, f)) for f in os.listdir(base)
                if f.endswith(".json") and not f.startswith(".")]
        rows.sort(key=lambda r: (r.get("written_at") or "", r.get("reply_id") or ""), reverse=True)
        return rows

    # ---- つなぎ先（pairing.secret.json は持ち出しに入れない）
    def save_pairing(self, info, secret=None):
        with self._lock:
            _write_json(self._p("pairing.json"), info)
            if secret is not None:
                _write_json(self._p(SECRET_NAME), secret)

    def get_pairing(self):
        return _read_json(self._p("pairing.json"))

    def get_pairing_secret(self):
        return _read_json(self._p(SECRET_NAME))

    # ---- Claude に送った物の記録（鍵・本文・画像は入れない）
    def log_claude(self, entry):
        if not isinstance(entry, dict):
            raise ValueError("entry は辞書")
        extra = set(entry) - set(CLAUDE_LOG_KEYS)
        if extra:
            raise ValueError("entry に許さない欄: " + ",".join(sorted(extra)))
        for k in ("kind", "what", "bytes", "model", "demo"):
            if k not in entry:
                raise ValueError("欄が無い: " + k)
        if not isinstance(entry["demo"], bool) or not isinstance(entry["bytes"], int):
            raise ValueError("bytes は整数・demo は真偽")
        row = dict(entry)
        row.setdefault("at", ids.now_jst())
        with self._lock:
            path = self._p("claude_log.json")
            items = _read_json(path, [])
            items.append(row)
            _write_json(path, items)
            return row

    def get_claude_log(self):
        return _read_json(self._p("claude_log.json"), [])

    # ---- 持ち出し・全削除
    def export_zip(self, out_dir):
        out_dir = os.path.abspath(str(out_dir))
        if out_dir == self.root or out_dir.startswith(self.root + os.sep):
            raise ValueError("out_dir は器の外")
        with self._lock:
            self.write_manifest()
            ensure_dir(out_dir)
            stamp = ids.now_jst()   # YYYY-MM-DDTHH:MM:SS+09:00
            name = "export_%s_%s" % (stamp[:10], stamp[11:19].replace(":", ""))
            path = os.path.join(out_dir, name + ".zip")
            n = 2
            while os.path.exists(path):
                path = os.path.join(out_dir, "%s_%d.zip" % (name, n))
                n += 1
            tmp = path + ".tmp"
            try:
                with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
                    for rel in self._names():
                        z.write(self._p(*rel.split("/")), rel)
                    for item in self.list_statements():     # 読める形（.md）も並べる。数え方には入らない
                        if isinstance(item, dict) and isinstance(item.get("item_id"), str) and _ID_RE.match(item["item_id"]):
                            z.writestr("statements/%s.md" % item["item_id"], statement_markdown(item).encode("utf-8"))
                counts = verify_export_zip(tmp)
                try:
                    os.chmod(tmp, 0o600)
                except OSError:
                    pass
                os.replace(tmp, path)
            except BaseException:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                raise
            return path, counts

    def wipe(self):
        with self._lock:
            for name in os.listdir(self.root):
                p = os.path.join(self.root, name)
                if os.path.isdir(p) and not os.path.islink(p):
                    shutil.rmtree(p)
                else:
                    os.unlink(p)
            self.write_manifest()
