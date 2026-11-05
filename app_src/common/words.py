# -*- coding: utf-8 -*-
"""common/words.py — 禁じる言い方の走査（設計の決まり）。標準ライブラリだけ。

出所: 設計の決まり（動詞の形・人に付く数と段の語・文書の名は例外・促しの字）。
走査の順: 先に「例外（文書の名）」を同じ長さの印に置き換える（位置はずれない）→ 残りを走査する。

  scan(text, kinds=None) -> [(kind, word, position), ...]   position は text の先頭からの字の位置
  is_clean(text)         -> bool

kind は "verb" "grade" "nudge" "undecided" のどれか。kinds にその部分集合を渡すと絞れる。
"""
import re

KIND_VERB = "verb"
KIND_GRADE = "grade"
KIND_NUDGE = "nudge"
KIND_UNDECIDED = "undecided"
ALL_KINDS = (KIND_VERB, KIND_GRADE, KIND_NUDGE, KIND_UNDECIDED)

# 動詞の形（「わかる」は状態についてだが、走査では字そのもので見る）
FORBIDDEN_VERBS = (
    "診断する", "診断します",
    "判定する", "判定します",
    "わかります", "わかる",
    "評価する", "評価します",
    "改善した", "悪化した",
    "治療",
)

# 人に付く数・段の語。「点」は 1 字だけだと「点線」「要点」に当たるので、正規表現で形を見る。
FORBIDDEN_GRADES = (
    "スコア", "レベル", "順位", "上達", "成長", "向上", "前回より", "ランク",
)
FORBIDDEN_GRADE_PATTERNS = (
    re.compile(r"[0-9０-９]+\s*点|点数|得点|採点"),
)

# 促しの字
FORBIDDEN_NUDGES = (
    "続きをどうぞ", "つづきをどうぞ", "毎日",
    "がんばろう", "がんばりましょう",
    "未読", "催促", "連続", "日連続",
    "してみよう", "してみましょう",
    "てみよう", "てみましょう", "でみよう", "でみましょう",   # 「話してみましょう」「読んでみましょう」の形も拾う
    "おすすめ", "通知",
)

# まだ使わない語
UNDECIDED = ("スキルアップ", "帰属的自己")

# 文書の名＝先に取り除いてから走査する
EXCEPTIONS = (
    "診断書", "意見書", "通知表", "個別支援計画", "母子手帳", "診療情報提供書",
)

_MASK = "\x00"


def _mask_exceptions(text):
    """例外の語を、同じ長さの印に置き換える（位置がずれない）。"""
    for ex in sorted(EXCEPTIONS, key=len, reverse=True):
        if ex in text:
            text = text.replace(ex, _MASK * len(ex))
    return text


def _find_all(text, word):
    pos = text.find(word)
    while pos != -1:
        yield pos
        pos = text.find(word, pos + 1)


def scan(text, kinds=None):
    """text の中の禁じる言い方を [(kind, word, position)] で返す（position の昇順）。"""
    if not isinstance(text, str):
        raise TypeError("text は str")
    want = set(ALL_KINDS if kinds is None else kinds)
    unknown = want - set(ALL_KINDS)
    if unknown:
        raise ValueError("知らない kind: %s" % ",".join(sorted(unknown)))
    body = _mask_exceptions(text)
    hits = []
    for b, posmap in _variants(body):
        hits.extend(_scan_body(b, posmap, want))
    seen = set()
    uniq = []
    for h in hits:
        if h not in seen:
            seen.add(h)
            uniq.append(h)
    hits = uniq
    hits.sort(key=lambda h: (h[2], h[0], h[1]))
    return hits


def _variants(body):
    """走査する字の変種＝(字, 位置の対応表)。元の字と、空白（半角・全角）を抜いた字の 2 つ。
    分かち書きの文（「話して みましょう」）でも禁じる言い方を拾うため。位置は元の字の位置に戻す。"""
    yield body, None
    out = []
    idx = []
    for i, ch in enumerate(body):
        if ch in (" ", "\u3000"):
            continue
        out.append(ch)
        idx.append(i)
    collapsed = "".join(out)
    if collapsed != body:
        yield collapsed, idx


def _scan_body(body, posmap, want):
    def orig(p):
        return p if posmap is None else posmap[p]
    hits = []
    if KIND_VERB in want:
        for w in FORBIDDEN_VERBS:
            hits.extend((KIND_VERB, w, orig(p)) for p in _find_all(body, w))
    if KIND_GRADE in want:
        for w in FORBIDDEN_GRADES:
            hits.extend((KIND_GRADE, w, orig(p)) for p in _find_all(body, w))
        for rx in FORBIDDEN_GRADE_PATTERNS:
            hits.extend((KIND_GRADE, m.group(0), orig(m.start())) for m in rx.finditer(body))
    if KIND_NUDGE in want:
        for w in FORBIDDEN_NUDGES:
            hits.extend((KIND_NUDGE, w, orig(p)) for p in _find_all(body, w))
    if KIND_UNDECIDED in want:
        for w in UNDECIDED:
            hits.extend((KIND_UNDECIDED, w, orig(p)) for p in _find_all(body, w))
    return hits


def is_clean(text):
    return len(scan(text)) == 0


if __name__ == "__main__":
    # 陰性対照の自己検査（先に: 禁じる語が検出される → 例外だけの字は 0 件）
    neg = scan("この記録を評価する")
    print("陰性対照 禁じる語入りの字 -> %d 件 %s" % (len(neg), "反応" if neg else "反応なし(FAIL)"))
    pos = scan("診断書を しまう")
    print("本物     例外だけの字     -> %d 件 %s" % (len(pos), "合格" if not pos else "FAIL"))
    ok = bool(neg) and not pos
    raise SystemExit(0 if ok else 1)
