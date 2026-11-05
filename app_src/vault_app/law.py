# -*- coding: utf-8 -*-
"""vault_app/law.py - 法令集（閉じた集合）の読み込み（条文の字は法令集からだけ出す決まり）。標準ライブラリだけ。

1 条 = 1 JSON。verified_by_person が JSON の true の物だけ読み込む（false・欄の欠け・読めない物は無視 = 画面に出ない）。
画面に出る条文の字は、いつもこの JSON の text_verbatim だけ（モデルの字を条文として出さない）。

  load_corpus(dir)  -> {id: entry}
  Corpus(entries)   .index() .get(id) .statute_for_bundle(id) .match_verbatim(text) .ids()
  for_app(app)      -> Corpus   （cfg["law_dir"] か app_root/law_corpus を毎回読む = 確認の済んだ物が すぐ反映される）
"""
import json
import os
import re

from app_src.common import contract

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def _valid_entry(d):
    if not isinstance(d, dict):
        return False
    if d.get("verified_by_person") is not True:      # true だけ（"true" や 1 は通さない）
        return False
    i = d.get("id")
    if not isinstance(i, str) or not _ID_RE.match(i):
        return False
    for k in contract.STATUTE_FIELDS:
        v = d.get(k)
        if not isinstance(v, str) or v.strip() == "":
            return False
    return True


def load_corpus(dir_path):
    """dir の *.json（_ で始まる名は読まない）から、確認の済んだ条だけ {id: entry}。同じ id が 2 つ在れば、どちらも読まない。"""
    out = {}
    dup = set()
    try:
        names = sorted(os.listdir(dir_path))
    except OSError:
        return {}
    for name in names:
        if not name.endswith(".json") or name.startswith("_") or name.startswith("."):
            continue
        try:
            with open(os.path.join(dir_path, name), "rb") as f:
                d = json.loads(f.read().decode("utf-8"))
        except (OSError, ValueError):
            continue
        if not _valid_entry(d):
            continue
        if d["id"] in out or d["id"] in dup:
            dup.add(d["id"])
            out.pop(d["id"], None)
            continue
        out[d["id"]] = d
    return out


class Corpus(object):
    def __init__(self, entries):
        self._e = dict(entries)

    def ids(self):
        return sorted(self._e)

    def __contains__(self, law_id):
        return law_id in self._e

    def index(self):
        """見出しの一覧（id・法令名・条番号だけ）。"""
        return [{"id": i, "law_name": self._e[i]["law_name"], "article": self._e[i]["article"]} for i in self.ids()]

    def get(self, law_id):
        """画面用 = id ＋ 7 欄。無ければ None。"""
        e = self._e.get(law_id) if isinstance(law_id, str) else None
        if e is None:
            return None
        out = {"id": law_id}
        for k in contract.STATUTE_FIELDS:
            out[k] = e[k]
        return out

    def statute_for_bundle(self, law_id):
        """取り決めの 7 欄の辞書。無ければ None。"""
        e = self._e.get(law_id) if isinstance(law_id, str) else None
        if e is None:
            return None
        return {k: e[k] for k in contract.STATUTE_FIELDS}

    def match_verbatim(self, text):
        """本文の完全一致（1 字違えば None）。"""
        if not isinstance(text, str) or text == "":
            return None
        for i in self.ids():
            if self._e[i]["text_verbatim"] == text:
                return i
        return None


def corpus_dir(app):
    return app.cfg.get("law_dir") or os.path.join(app.app_root, "law_corpus")


def for_app(app):
    return Corpus(load_corpus(corpus_dir(app)))
