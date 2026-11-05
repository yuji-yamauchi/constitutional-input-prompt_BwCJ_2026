# -*- coding: utf-8 -*-
"""vault_app/claude_client.py - Claude を呼ぶ唯一の部品（設計の決まり）。

ネットワークへ出る import は、この 1 本と handoff.py の 2 本だけ。
- 送る前に vault.log_claude に「いつ・何を・何バイト」（本文・画像・鍵は入れない）。
- 鍵の値は cfg から読むだけ。ログ・例外の字・画面に出さない。
- demo mode（cfg["demo_mode"]）= ネットワークへ出ず、demo/recorded/<kind>/ の記録を返す。
- 出力は必ず、コードの縛りを通す（通らなければ落とす = fail-closed）。
"""
import base64
import hashlib
import json
import os
import re
import urllib.error
import urllib.request

from app_src.common import ids, words
from app_src.common.httpkit import HttpError

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-4-5"      # [未確認] 作成者の鍵で確かめる。cfg["claude_model"]（環境変数 CIP_CLAUDE_MODEL）で替える。
MAX_TOKENS = {"reader": 2000, "listener": 200, "arranger": 1200}
TIMEOUT_SECONDS = 60
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
SENDABLE_IMAGES = ("image/jpeg", "image/png", "image/webp")

QUESTION_MAX_CHARS = 60
QUESTION_ENDINGS = ("？", "?", "。")
_DIGIT_RE = re.compile(r"[0-9\uff10-\uff19]")

D_FAILED = "いまは接続できません。時間をおいて、もういちどためしてください。"
D_SVG = "この形式は 読み取りに 送れません。"
D_DERIVED_REJECTED = "読み取れませんでした（写しに 使えない言い方が 含まれたため）。"
D_DERIVED_EMPTY = "読み取れませんでした。"
D_DRAFT_REJECTED = "案を 出せませんでした。"


class ClaudeError(Exception):
    """Claude の口の失敗。鍵や本文を含めない（経路は 502 claude_failed を返す）。
    status＝HTTP の失敗のときだけ入る整数（それ以外は None）。"""

    def __init__(self, msg, status=None):
        super().__init__(msg)
        self.status = status


_PROMPT_HEADER_RE = re.compile(r"^# 版: (\S+) / 決めた日: (\d{4}-\d{2}-\d{2})\n")


def split_prompt(raw):
    """指示の文の 1 行目（「# 版: v0.3 / 決めた日: YYYY-MM-DD」）を分ける。(版, 決めた日, 本文)。
    1 行目が無ければ (None, None, raw)。Claude へ送るのは本文だけ。"""
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")   # Windows の checkout（CRLF）でも同じ本文・同じ指紋にする
    m = _PROMPT_HEADER_RE.match(raw)
    if not m:
        return None, None, raw
    return m.group(1), m.group(2), raw[m.end():]


def read_prompt_version(prompts_dir, kind):
    """指示の文の版（1 行目から）。読めない・1 行目が無いときは None。"""
    try:
        with open(os.path.join(prompts_dir, kind + ".txt"), "rb") as f:
            return split_prompt(f.read().decode("utf-8"))[0]
    except (OSError, UnicodeDecodeError):
        return None


def _sha_prefix(data):
    return hashlib.sha256(data).hexdigest()[:16]


def _strip_fence(text):
    t = text.strip()
    m = re.match(r"^```[A-Za-z]*\n(.*)\n```$", t, re.S)
    return m.group(1) if m else t


def extract_json(text):
    """モデルの字から JSON の辞書を取り出す。読めなければ ValueError。"""
    if not isinstance(text, str):
        raise ValueError("not text")
    t = _strip_fence(text)
    a, b = t.find("{"), t.rfind("}")
    if a < 0 or b <= a:
        raise ValueError("no json")
    d = json.loads(t[a:b + 1])
    if not isinstance(d, dict):
        raise ValueError("not dict")
    return d


def check_question(q):
    """問いの縛り。通れば None、外れれば短い理由の字。"""
    if not isinstance(q, str):
        return "bad_json"
    s = q.strip()
    if s == "":
        return "empty"
    if "\n" in s or "\r" in s:
        return "multiline"
    if len(s) > QUESTION_MAX_CHARS:
        return "too_long"
    if _DIGIT_RE.search(s):
        return "has_digit"
    if not words.is_clean(s):
        return "forbidden_word"
    if not s.endswith(QUESTION_ENDINGS):
        return "bad_ending"
    return None


class ClaudeClient(object):
    def __init__(self, cfg, vault, clock, prompts_dir, demo_dir=None):
        self.cfg = cfg
        self.vault = vault
        self.clock = clock
        self.prompts_dir = prompts_dir
        base = os.path.dirname(os.path.dirname(os.path.abspath(prompts_dir)))     # app_src
        self.demo_dir = demo_dir or cfg.get("demo_dir") or os.path.join(base, "demo", "recorded")

    # ---- 設定
    @property
    def demo(self):
        return bool(self.cfg.get("demo_mode"))

    @property
    def model(self):
        return self.cfg.get("claude_model") or DEFAULT_MODEL

    def _prompt(self, kind):
        try:
            with open(os.path.join(self.prompts_dir, kind + ".txt"), "rb") as f:
                return split_prompt(f.read().decode("utf-8"))[2]
        except OSError:
            raise ClaudeError("指示の文が 見つかりません。") from None

    def _log(self, kind, what, nbytes):
        self.vault.log_claude({
            "at": ids.now_jst(self.clock),
            "kind": kind,
            "what": what,
            "bytes": int(nbytes),
            "model": self.model,
            "demo": self.demo,
        })

    # ---- 1 回の呼び出し（唯一の出口）
    def demo_is_placeholder(self):
        """記録済みの応答が「本物の Claude から記録した物」か「仮の手書き」か。
        1 つでも recorded_from_live が true でない物が在れば仮（画面の帯の字が変わる＝嘘にしない）。"""
        if not self.demo:
            return False
        for kind in ("reader", "listener", "arranger"):
            base = os.path.join(self.demo_dir, kind)
            if not os.path.isdir(base):
                return True
            names = [n for n in os.listdir(base) if n.endswith(".json")]
            if not names:
                return True
            for n in names:
                try:
                    with open(os.path.join(base, n), "rb") as f:
                        d = json.loads(f.read().decode("utf-8"))
                except (OSError, ValueError):
                    return True
                if not (isinstance(d, dict) and d.get("recorded_from_live") is True):
                    return True
        return False

    def _demo_payload(self, kind, input_bytes):
        base = os.path.join(self.demo_dir, kind)
        for name in (_sha_prefix(input_bytes) + ".json", "default.json"):
            p = os.path.join(base, name)
            if os.path.isfile(p):
                try:
                    with open(p, "rb") as f:
                        d = json.loads(f.read().decode("utf-8"))
                except (OSError, ValueError):
                    raise ClaudeError("デモの応答が 読めません。") from None
                if isinstance(d, dict):
                    return d
        raise ClaudeError("デモの応答が ありません。")

    def _live_text(self, kind, system, blocks):
        key = self.cfg.get("api_key")
        if not key:
            raise ClaudeError("鍵が ありません。")
        body = {
            "model": self.model,
            "max_tokens": MAX_TOKENS[kind],
            "system": system,
            "messages": [{"role": "user", "content": blocks}],
        }
        req = urllib.request.Request(
            API_URL,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={
                "x-api-key": key,
                "anthropic-version": API_VERSION,
                "content-type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as r:
                raw = r.read(MAX_RESPONSE_BYTES)
            obj = json.loads(raw.decode("utf-8"))
            parts = [b.get("text", "") for b in obj.get("content", []) if isinstance(b, dict) and b.get("type") == "text"]
        except urllib.error.HTTPError as e:
            raise ClaudeError(D_FAILED, status=int(e.code)) from None   # 番号だけ残す（本文・鍵は残さない）
        except Exception:
            raise ClaudeError(D_FAILED) from None      # 原因の字は残さない（鍵・本文を含みうるため）
        return "".join(parts)

    def _run(self, kind, what, system, blocks, input_bytes):
        """送る前に記録 -> demo なら記録の応答（dict）、そうでなければ Claude の字（str）。"""
        self._log(kind, what, len(input_bytes))
        if self.demo:
            return self._demo_payload(kind, input_bytes)
        return self._live_text(kind, system, blocks)

    # ---- 入力の組み立て（器の本番と記録の道具が、同じ物・同じ鍵で引くための切り出し）
    def build_reader(self, data, media):
        """(system, blocks, key_bytes)。key_bytes＝画像の bytes そのもの。"""
        if media not in SENDABLE_IMAGES:
            raise ClaudeError(D_SVG)
        blocks = [
            {"type": "image", "source": {"type": "base64", "media_type": media, "data": base64.b64encode(data).decode("ascii")}},
            {"type": "text", "text": "この 画像の 字を、そのまま 写してください。"},
        ]
        return self._prompt("reader"), blocks, data

    def build_listener(self, text, conditions):
        """(system, blocks, key_bytes)。"""
        cond_lines = "\n".join("- %s: %s" % (k, conditions[k]) for k in sorted(conditions))
        user = "本人の文:\n%s\n\n条件:\n%s" % (text, cond_lines)
        key_bytes = json.dumps({"text": text, "conditions": conditions}, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return self._prompt("listener"), [{"type": "text", "text": user}], key_bytes

    def build_arranger(self, trouble, wish, derived_texts, law_index):
        """(system, blocks, key_bytes)。"""
        parts = ["困っていること:\n%s" % trouble, "のぞむこと:\n%s" % wish]
        for n, t in enumerate(derived_texts, 1):
            parts.append("記録の写し %d:\n%s" % (n, t))
        parts.append("法令集の見出し:\n" + "\n".join("%s | %s | %s" % (e["id"], e["law_name"], e["article"]) for e in law_index))
        user = "\n\n".join(parts)
        return self._prompt("arranger"), [{"type": "text", "text": user}], user.encode("utf-8")

    # ---- 2.1 読み取り役
    def read_image(self, record_id):
        data, media = self.vault.read_original(record_id)
        system, blocks, key_bytes = self.build_reader(data, media)
        payload = self._run("reader", "記録の画像 1 枚（読み取り）", system, blocks, key_bytes)
        if isinstance(payload, dict):
            md = payload.get("markdown")
        else:
            md = _strip_fence(payload)
        if not isinstance(md, str) or md.strip() == "":
            raise HttpError(422, "derived_empty", D_DERIVED_EMPTY)
        # 写しは「他者が書いた字」の写し＝診断書や計画には「治療」「評価」の字が入っているのが普通。
        # ここで禁じる言い方の走査に掛けて落とすと、読み取りがほぼ通らなくなる（検収の指摘）。
        # 走査は Claude 自身の言葉（問い・案・画面の字・指示）に当てる。写しは当てず、当たった数だけ meta に残す（本人が原本と見比べられる）。
        hits = 0
        for line in md.split("\n"):
            hits += len(words.scan(line, kinds=("nudge",)))   # 促しの字（Claude の足し書きの疑い）だけ数える
        meta = {
            "generated_at": ids.now_jst(self.clock),
            "model": self.model,
            "prompt_sha256": hashlib.sha256(system.encode("utf-8")).hexdigest(),
            "demo": self.demo,
            "nudge_hits": hits,
        }
        return {"markdown": md, "meta": meta}

    # ---- 2.2 聞き役
    def ask_question(self, text, conditions):
        """(question|None, reason|None)。読み返しは作らない（経路が本人の文をそのまま入れる）。"""
        system, blocks, key_bytes = self.build_listener(text, conditions)
        payload = self._run("listener", "本人の文 1 つ（問いを 1 つ）", system, blocks, key_bytes)
        try:
            d = payload if isinstance(payload, dict) else extract_json(payload)
        except ValueError:
            return None, "bad_json"
        q = d.get("question")
        reason = check_question(q)
        if reason:
            return None, reason
        return q.strip(), None

    # ---- 2.3 並べ役
    def arrange(self, trouble, wish, derived_texts, law_index):
        system, blocks, key_bytes = self.build_arranger(trouble, wish, derived_texts, law_index)
        payload = self._run("arranger", "本人の 2 欄＋記録の写し %d 件＋条の見出し" % len(derived_texts), system, blocks, key_bytes)
        try:
            d = payload if isinstance(payload, dict) else extract_json(payload)
        except ValueError:
            raise HttpError(422, "draft_rejected", D_DRAFT_REJECTED) from None
        draft = d.get("draft_text")
        if not isinstance(draft, str) or draft.strip() == "":
            raise HttpError(422, "draft_rejected", D_DRAFT_REJECTED)
        if words.scan(draft):
            raise HttpError(422, "draft_rejected", D_DRAFT_REJECTED)
        known = set(e["id"] for e in law_index)
        raw_ids = d.get("statute_ids")
        if not isinstance(raw_ids, list):
            raw_ids = []
        kept, seen, dropped = [], set(), 0
        for i in raw_ids:
            if isinstance(i, str) and i in known:
                if i not in seen:
                    seen.add(i)
                    kept.append(i)
            else:
                dropped += 1
        return {"draft_text": draft, "statute_ids": kept, "dropped_ids": dropped, "demo": self.demo}


def get_client(app):
    """app.claude を返す。無ければ作って入れる。鍵も demo も無ければ None（経路は 503 claude_unavailable）。"""
    if app.claude is not None:
        return app.claude
    cfg = app.cfg
    if not (cfg.get("demo_mode") or cfg.get("api_key")):
        return None
    prompts_dir = os.path.join(app.app_root, "vault_app", "prompts")
    app.claude = ClaudeClient(cfg, app.vault, app.clock, prompts_dir)
    return app.claude
