# -*- coding: utf-8 -*-
"""tools/record_demo.py - 本物の Claude の応答を 1 回だけ記録する道具（標準ライブラリだけ）。

作成者が自分の鍵で回す。応答を demo/recorded/<役>/<入力の指紋16字>.json と default.json に
recorded_from_live: true で書く。以後 CIP_DEMO_MODE=1 では、鍵なしでも本物の記録が再生される。

使い方（app_src の親の場所で）:
  ANTHROPIC_API_KEY=... python3 -B -m app_src.tools.record_demo
  python3 -B -m app_src.tools.record_demo --dry-run            呼ばずに、役ごとの入力の数と指紋だけ出す
  python3 -B -m app_src.tools.record_demo --kinds reader,listener
  python3 -B -m app_src.tools.record_demo --inputs <path>      入力の置き場を替える

約束:
- CIP_DEMO_MODE は見ない。いつも本物を呼ぶ（--dry-run のときを除く）。
- 通信の部品は自分では触らない。claude_client の _live_text を呼ぶだけ。
- 記録にも画面にも、鍵・原本の画像は書かない。
"""
import argparse
import base64
import hashlib
import json
import os
import sys

from app_src.common import ids, words
from app_src.vault_app import claude_client, law, routes_practice

HERE = os.path.dirname(os.path.abspath(__file__))
APP_SRC = os.path.dirname(HERE)
DEFAULT_INPUTS = os.path.join(APP_SRC, "demo", "record_inputs.json")
DEFAULT_OUT = os.path.join(APP_SRC, "demo", "recorded")
PROMPTS_DIR = os.path.join(APP_SRC, "vault_app", "prompts")
KINDS = ("reader", "listener", "arranger")

T_NO_KEY = "鍵が ありません。環境変数 ANTHROPIC_API_KEY に入れてください。"
T_HTTP = {
    401: "鍵を たしかめてください（ANTHROPIC_API_KEY）。",
    404: "モデル名を確かめてください（CIP_CLAUDE_MODEL）。",
    429: "しばらく 待ってから、もういちど ためしてください。",
}
STOP_STATUSES = (401, 404, 429)       # 続けても同じ失敗になる番号


class InputsError(Exception):
    pass


def _sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


# ---------------------------------------------------------------- 入力

def _check_conditions(c):
    allowed = {k: vals for k, _label, vals in routes_practice.CONDITIONS}
    if not isinstance(c, dict) or set(c) != set(allowed):
        raise InputsError("listener の conditions の鍵が 画面の既定と ちがいます。")
    for k, v in c.items():
        if v not in allowed[k]:
            raise InputsError("listener の conditions の値が 画面の既定に ありません: %s" % k)
    return c


def load_inputs(path):
    """入力の置き場を読む。{"listener":[(text,cond)], "arranger":[dict], "reader":[(name,bytes)]}。"""
    try:
        with open(path, "rb") as f:
            d = json.loads(f.read().decode("utf-8"))
    except (OSError, ValueError):
        raise InputsError("入力の置き場が 読めません。") from None
    if not isinstance(d, dict):
        raise InputsError("入力の置き場の形が ちがいます。")
    out = {"listener": [], "arranger": [], "reader": []}
    for row in d.get("listener") or []:
        text = row.get("text") if isinstance(row, dict) else None
        if not isinstance(text, str) or not text.strip() or not words.is_clean(text):
            raise InputsError("listener の文が 空か、使えない言い方を 含みます。")
        out["listener"].append((text, _check_conditions(row.get("conditions"))))
    for row in d.get("arranger") or []:
        if not isinstance(row, dict):
            raise InputsError("arranger の形が ちがいます。")
        for k in ("trouble", "wish"):
            v = row.get(k)
            if not isinstance(v, str) or not v.strip() or not words.is_clean(v):
                raise InputsError("arranger の %s が 空か、使えない言い方を 含みます。" % k)
        out["arranger"].append(row)
    r = d.get("reader")
    if isinstance(r, dict) and r.get("from_png_json"):
        p = os.path.join(APP_SRC, *r["from_png_json"].split("/")) if not os.path.isabs(r["from_png_json"]) else r["from_png_json"]
        try:
            with open(p, "rb") as f:
                pj = json.loads(f.read().decode("utf-8"))
            for name, b64 in sorted(pj["files"].items()):
                if not name.endswith(".png") or "/" in name or "\\" in name:
                    continue
                data = base64.b64decode(b64)
                if data[:8] != b"\x89PNG\r\n\x1a\n":
                    continue
                out["reader"].append((name, data))
        except (OSError, ValueError, KeyError):
            raise InputsError("画像の置き場が 読めません。") from None
    return out


# ---------------------------------------------------------------- 検査（器の本番と同じ縛り）

def check_reader(text):
    md = claude_client._strip_fence(text)
    if md.strip() == "":
        return None, "empty"
    return {"markdown": md}, None


def check_listener(text):
    try:
        d = claude_client.extract_json(text)
    except ValueError:
        return None, "bad_json"
    q = d.get("question")
    reason = claude_client.check_question(q)
    if reason:
        return None, reason
    return {"question": q.strip()}, None


def check_arranger(text, known_ids):
    try:
        d = claude_client.extract_json(text)
    except ValueError:
        return None, "bad_json"
    draft = d.get("draft_text")
    if not isinstance(draft, str) or draft.strip() == "":
        return None, "empty"
    if words.scan(draft):
        return None, "forbidden_word"
    raw = d.get("statute_ids")
    kept = []
    for i in (raw if isinstance(raw, list) else []):
        if isinstance(i, str) and i in known_ids and i not in kept:
            kept.append(i)
    return {"draft_text": draft, "statute_ids": kept}, None


# ---------------------------------------------------------------- 書き出し

def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write((json.dumps(obj, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _record(out_dir, kind, sha16, body, model, system, first):
    rec = dict(body)
    rec.update({
        "recorded_from_live": True,
        "recorded_at": ids.now_jst(),
        "model": model,
        "prompt_sha256": hashlib.sha256(system.encode("utf-8")).hexdigest(),
        "input_sha256_16": sha16,
    })
    _write(os.path.join(out_dir, kind, sha16 + ".json"), rec)
    if first:
        _write(os.path.join(out_dir, kind, "default.json"), rec)


def _existing_reader_texts(out_dir):
    p = os.path.join(out_dir, "reader", "default.json")
    try:
        with open(p, "rb") as f:
            d = json.loads(f.read().decode("utf-8"))
        md = d.get("markdown")
        return [md] if isinstance(md, str) and md.strip() else []
    except (OSError, ValueError):
        return []


# ---------------------------------------------------------------- 本体

def dry_run(client, inputs, kinds, out):
    for kind in KINDS:
        if kind not in kinds:
            continue
        rows = []
        if kind == "reader":
            for name, data in inputs["reader"]:
                rows.append((name, _sha16(client.build_reader(data, "image/png")[2])))
        elif kind == "listener":
            for n, (text, cond) in enumerate(inputs["listener"], 1):
                rows.append(("文 %d" % n, _sha16(client.build_listener(text, cond)[2])))
        else:
            index = law.Corpus(law.load_corpus(_law_dir())).index()
            for n, row in enumerate(inputs["arranger"], 1):
                if row.get("use_reader_outputs"):
                    rows.append(("組 %d" % n, "読み取りの結果で決まります"))
                else:
                    texts = row.get("derived_texts") or []
                    rows.append(("組 %d" % n, _sha16(client.build_arranger(row["trouble"], row["wish"], texts, index)[2])))
        print("%s: 入力 %d 件" % (kind, len(rows)))
        for label, sha in rows:
            print("  %s  %s" % (label, sha))
    print("（呼んでいません・書いていません）")
    return 0


def _law_dir():
    return os.environ.get("CIP_LAW_DIR") or os.path.join(APP_SRC, "law_corpus")


def run(argv, env=None, client=None):
    ap = argparse.ArgumentParser(prog="record_demo", add_help=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--kinds", default=",".join(KINDS))
    ap.add_argument("--inputs", default=DEFAULT_INPUTS)
    ap.add_argument("--out", default=DEFAULT_OUT)
    a = ap.parse_args(argv)
    env = os.environ if env is None else env
    kinds = [k.strip() for k in a.kinds.split(",") if k.strip()]
    bad = [k for k in kinds if k not in KINDS]
    if bad:
        print("知らない役: %s" % ",".join(bad))
        return 2
    key = env.get("ANTHROPIC_API_KEY") or None
    if not a.dry_run and client is None and not key:
        print(T_NO_KEY)
        return 2
    try:
        inputs = load_inputs(a.inputs)
    except InputsError as e:
        print(str(e))
        return 2
    cfg = {"api_key": key, "demo_mode": False, "claude_model": env.get("CIP_CLAUDE_MODEL") or None}
    c = client or claude_client.ClaudeClient(cfg, None, None, PROMPTS_DIR)
    print("モデル: %s" % c.model)
    if a.dry_run:
        return dry_run(c, inputs, kinds, a.out)

    index = law.Corpus(law.load_corpus(_law_dir())).index()
    known = set(e["id"] for e in index)
    table = {k: {"ok": 0, "ng": 0} for k in kinds}
    reader_texts = []
    stopped = False

    def attempt(kind, label, build, check):
        """1 件を呼んで検査して書く。書けたら本文を、だめなら None を返す。止めるべき失敗なら stopped を立てる。"""
        nonlocal stopped
        system, blocks, key_bytes = build
        sha16 = _sha16(key_bytes)
        try:
            text = c._live_text(kind, system, blocks)
        except claude_client.ClaudeError as e:
            table[kind]["ng"] += 1
            st = getattr(e, "status", None)
            if st is None:
                print("NG（%s %s: 接続）" % (kind, label))
            else:
                print("NG（%s %s: %s）%s" % (kind, label, st, T_HTTP.get(st, "番号は %d です。" % st)))
                if st in STOP_STATUSES:
                    stopped = True
            return None
        body, reason = check(text)
        if body is None:
            table[kind]["ng"] += 1
            print("NG（%s %s: %s）" % (kind, label, reason))
            return None
        _record(a.out, kind, sha16, body, c.model, system, first=(table[kind]["ok"] == 0))
        table[kind]["ok"] += 1
        print("記録 %s %s -> %s.json" % (kind, label, sha16))
        return body

    if "reader" in kinds:
        for name, data in inputs["reader"]:
            if stopped:
                break
            body = attempt("reader", name, c.build_reader(data, "image/png"), check_reader)
            if body is not None:
                reader_texts.append(body["markdown"])
    if "listener" in kinds:
        for n, (text, cond) in enumerate(inputs["listener"], 1):
            if stopped:
                break
            attempt("listener", "文 %d" % n, c.build_listener(text, cond), check_listener)
    if "arranger" in kinds:
        for n, row in enumerate(inputs["arranger"], 1):
            if stopped:
                break
            texts = list(row.get("derived_texts") or [])
            if row.get("use_reader_outputs"):
                texts = (reader_texts or _existing_reader_texts(a.out))[:2]
            attempt("arranger", "組 %d" % n, c.build_arranger(row["trouble"], row["wish"], texts, index),
                    lambda t: check_arranger(t, known))

    print("")
    print("役        記録  NG  default")
    for k in kinds:
        has = os.path.isfile(os.path.join(a.out, k, "default.json"))
        print("%-9s %4d %3d  %s" % (k, table[k]["ok"], table[k]["ng"], "あり" if has else "なし"))
    probe = claude_client.ClaudeClient(dict(cfg, demo_mode=True), None, None, PROMPTS_DIR, demo_dir=a.out)
    print("帯: %s" % ("まだ仮" if probe.demo_is_placeholder() else "本物の記録"))
    if stopped:
        return 1
    return 0 if all(t["ng"] == 0 for t in table.values()) else 1


def main(argv=None):
    return run(sys.argv[1:] if argv is None else argv)


if __name__ == "__main__":
    sys.exit(main())
