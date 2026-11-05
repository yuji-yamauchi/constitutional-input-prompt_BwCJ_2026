# -*- coding: utf-8 -*-
"""tests/negfirst.py — 陰性対照を先に回すための小さな助け（標準ライブラリだけ）。

クラス名が "N" で始まる物＝陰性対照（わざと壊して、検査が反応することを見る）。
それ以外（"T_…" など）＝本物。run_all は N を全部回してから T を回す。
"""
import importlib, os, unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PACKAGE = "app_src.tests"


def is_negative(cls):
    return cls.__name__.startswith("N")


def module_names():
    return sorted(f[:-3] for f in os.listdir(TESTS_DIR) if f.startswith("test_") and f.endswith(".py"))


def _flatten(suite):
    for t in suite:
        if isinstance(t, unittest.TestSuite):
            yield from _flatten(t)
        else:
            yield t


def collect():
    """(negatives, positives, import_errors)。各要素は (file, class名, test名, TestCase) の並び。"""
    loader = unittest.TestLoader()
    neg, pos, errors = [], [], []
    for mod_name in module_names():
        try:
            mod = importlib.import_module("%s.%s" % (PACKAGE, mod_name))
        except Exception as e:   # 読み込めない物は失敗として数える
            errors.append((mod_name, "%s: %s" % (type(e).__name__, e)))
            continue
        for attr in sorted(dir(mod)):
            cls = getattr(mod, attr)
            if not (isinstance(cls, type) and issubclass(cls, unittest.TestCase)):
                continue
            if cls.__module__ != mod.__name__:   # 取り込んだだけのクラスは数えない
                continue
            for t in _flatten(loader.loadTestsFromTestCase(cls)):
                row = (mod_name, cls.__name__, t._testMethodName, t)
                (neg if is_negative(cls) else pos).append(row)
    return neg, pos, errors
