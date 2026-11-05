# -*- coding: utf-8 -*-
"""tests/run_all.py — 陰性対照(N) → 本物(T) の順に全部回す。

使い方（app_src の親で）:  python3 -B -m app_src.tests.run_all
1 行ずつ  PASS|FAIL  <file>.<Class>.<test>  を出し、最後に数と終了コード（全部通れば 0）。
test_*.py は自動で拾う（後から足した物も同じ規則）。
"""
import sys, unittest

from app_src.tests import negfirst


def _run_one(case):
    result = unittest.TestResult()
    case.run(result)
    bad = result.failures + result.errors
    if bad:
        return "FAIL", bad[0][1].strip().splitlines()[-1] if bad[0][1].strip() else ""
    if result.skipped:
        return "SKIP", result.skipped[0][1]
    return "PASS", ""


def _run_group(rows):
    ok = 0
    for mod, cls, name, case in rows:
        status, note = _run_one(case)
        print("%s  %s.%s.%s%s" % (status, mod, cls, name, ("   [%s]" % note) if note else ""))
        if status == "PASS":
            ok += 1
    return ok


def main():
    neg, pos, errors = negfirst.collect()
    for mod, msg in errors:
        print("FAIL  %s  [読み込めない: %s]" % (mod, msg))
    n_ok = _run_group(neg)
    t_ok = _run_group(pos)
    t_total = len(pos) + len(errors)
    code = 0 if (n_ok == len(neg) and t_ok == t_total) else 1
    print("---- 結果 ----")
    print("陰性対照 %d/%d 反応・本物 %d/%d 合格" % (n_ok, len(neg), t_ok, t_total))
    print("終了コード %d" % code)
    return code


if __name__ == "__main__":
    sys.exit(main())
