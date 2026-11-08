# -*- coding: utf-8 -*-
"""器 v0.14（聞き役の 指示の 文から 古い 前提の 2 節を 外す・test_v09 の 権限の 行を POSIX に 限る）の検査。
N_＝陰性対照（先）／T_＝本物。標準ライブラリだけ・ネットワークへは出ない。

1. listener.txt に「問いの 向き」節と「きょうの こと」節が 無い（画面から 届く 経路が 無い 物を 約束に 書かない）。
   「やくそく」節と「返す 形」節は そのまま。1 行目は v0.3.4 / 2026-11-08。reader.txt・arranger.txt は 触らない。
2. 本文（1 行目を 除く）の 指紋は test_v03 KNOWN_PROMPT_SHA256 と 同じ 物を 指す。鍵（key_bytes）は 指示の 文に 依らない＝
   demo/recorded/listener/ の 名は 変わらない。
3. tests/test_v09.py の 0o600 の 検査は os.name == "posix" の 中に ある（検査ごと skip には しない）。
"""
import hashlib
import os
import re
import stat
import unittest

from app_src.common import words
from app_src.vault_app import claude_client

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPTS = os.path.join(APP_ROOT, "vault_app", "prompts")
TESTS = os.path.join(APP_ROOT, "tests")
HEADER = "# 版: v0.3.4 / 決めた日: 2026-11-08"
GONE_HEADS = ("問いの 向き\n", "きょうの こと（")
GONE_LINES = ("本人が 向きを えらんだ", "向きは 4 つ", "本人が 伝えると 決めた 日だけ 届きます", "ねる 時刻や たべる ことを すすめません", "問いの 材料に して よい だけで")
KEEP = ("やくそく\n", "- 良し悪しは 言いません。ほめも、直しも しません。\n", "- すすめる 言い方は しません。\n", "返す 形\n", '{"question": "…"}')
PERM_LINE = 'self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)'
COND = {"amount": "ふつう", "split": "文ごと", "ease": "やさしい", "length": "みじかく", "input": "文字"}


def _read(path):
    with open(path, "rb") as f:
        return f.read().decode("utf-8").replace("\r\n", "\n")


def _perm_guard(src):
    """test_v09 の 権限の 行の 直前の 行（if の 条件）を 返す。行が 無ければ None。"""
    lines = src.split("\n")
    for i, ln in enumerate(lines):
        if PERM_LINE in ln:
            return lines[i - 1].strip(), ln
    return None, None


class N_V014(unittest.TestCase):
    def test_a_checks_notice_the_old_things_coming_back(self):
        raw = _read(os.path.join(PROMPTS, "listener.txt"))
        # 2 節を 戻した 写しは 引っかかる
        back = raw.replace("返す 形\n", "問いの 向き\n- 本人が 向きを えらんだ ときは、その 向きの ことを 問います。\n\nきょうの こと（ゆうべ ねた 時刻）\n- 本人が 伝えると 決めた 日だけ 届きます。\n\n返す 形\n", 1)
        self.assertNotEqual(back, raw)
        self.assertTrue(any(h in back for h in GONE_HEADS))
        self.assertTrue(any(l in back for l in GONE_LINES))
        # 版の 行を 戻した 写しは 引っかかる
        old = raw.replace(HEADER, "# 版: v0.3.3 / 決めた日: 2026-11-06", 1)
        self.assertNotEqual(old.split("\n", 1)[0], HEADER)
        # やくそくの 2 行を 消した 写しは 引っかかる
        weak = raw.replace("- すすめる 言い方は しません。\n", "", 1)
        self.assertFalse(all(k in weak for k in KEEP))
        # 権限の 行を 条件なしに 戻した 写し・検査ごと skip に した 写しは 引っかかる
        src = _read(os.path.join(TESTS, "test_v09.py"))
        guard, line = _perm_guard(src)
        self.assertIsNotNone(line)
        flat = src.replace(guard + "\n", "", 1)
        self.assertNotEqual(_perm_guard(flat)[0], guard)
        self.assertNotIn('os.name == "posix"', _perm_guard(flat)[0])
        skipped = src.replace("    def test_run_is_created_then_replaced_and_next_id_follows(self):",
                              '    @unittest.skipIf(os.name != "posix", "x")\n    def test_run_is_created_then_replaced_and_next_id_follows(self):', 1)
        self.assertRegex(skipped, r'skipIf\(os\.name != "posix"[^\n]*\n\s*def test_run_is_created_then_replaced_and_next_id_follows')


class T_ListenerPrompt(unittest.TestCase):
    def setUp(self):
        self.raw = _read(os.path.join(PROMPTS, "listener.txt"))

    def test_header_and_the_two_sections_are_gone(self):
        self.assertEqual(self.raw.split("\n", 1)[0], HEADER)
        for h in GONE_HEADS:
            self.assertNotIn(h, self.raw)
        for l in GONE_LINES:
            self.assertNotIn(l, self.raw)
        for k in KEEP:
            self.assertIn(k, self.raw)
        self.assertLess(self.raw.index("やくそく\n"), self.raw.index("返す 形\n"))
        self.assertEqual(self.raw.count("\n\n"), 2)                 # 段落は 3 つ（頭・やくそく・返す 形）
        self.assertEqual(words.scan(self.raw), [])
        with open(os.path.join(PROMPTS, "listener.txt"), "rb") as f:
            b = f.read()
        self.assertEqual(b.count(b"\r"), 0)
        self.assertFalse(re.search(rb"\xc2[\x80-\x9f]", b))         # U+0080〜U+009F は 無い

    def test_reader_and_arranger_are_untouched(self):
        for kind in ("reader", "arranger"):
            first = _read(os.path.join(PROMPTS, kind + ".txt")).split("\n", 1)[0]
            self.assertEqual(first, "# 版: v0.3.1 / 決めた日: 2026-11-05", kind)

    def test_body_fingerprint_matches_test_v03_and_keys_do_not_depend_on_the_prompt(self):
        from app_src.tests import test_v03
        body = claude_client.split_prompt(self.raw)[2]
        self.assertEqual(hashlib.sha256(body.encode("utf-8")).hexdigest(), test_v03.KNOWN_PROMPT_SHA256["listener"])
        self.assertEqual(test_v03.PROMPT_HEADER["listener"], ("v0.3.4", "2026-11-08"))
        c = claude_client.ClaudeClient({"demo_mode": False}, None, None, PROMPTS)
        system, blocks, key = c.build_listener("きょうは 朝 早く 目が さめた。", COND)
        self.assertEqual(system, body)
        self.assertEqual(claude_client._sha_prefix(key), test_v03.KNOWN_LISTENER_SHA16)
        self.assertNotIn(b"v0.3", key)                              # 鍵に 指示の 文は 混ざらない


class T_PermissionGuard(unittest.TestCase):
    def test_v09_permission_line_is_inside_a_posix_guard_and_the_test_is_not_skipped(self):
        src = _read(os.path.join(TESTS, "test_v09.py"))
        guard, line = _perm_guard(src)
        self.assertEqual(src.count(PERM_LINE), 1)
        self.assertTrue(guard.startswith('if os.name == "posix":'), guard)
        self.assertEqual(len(line) - len(line.lstrip(" ")), 12)   # if の 中（4 段）
        self.assertNotRegex(src, r'skipIf\([^\n]*\n\s*def test_run_is_created_then_replaced_and_next_id_follows')

    def test_guard_behaves_like_the_siblings_on_a_fake_windows(self):
        # 模擬: os.name を "nt" に 差し替え、S_IMODE が 0o666（Windows の 438）を 返す 状況で、権限の 行だけが 飛ぶ
        src = _read(os.path.join(TESTS, "test_v09.py"))
        guard, line = _perm_guard(src)
        self.assertTrue(guard.startswith("if "), guard)
        snippet = "checked = []\n" + guard + "\n    checked.append(stat.S_IMODE(438))\n"
        for name, want in (("nt", []), ("posix", [0o666])):
            ns = {"os": type("O", (), {"name": name}), "stat": stat}
            exec(snippet, ns)
            self.assertEqual(ns["checked"], want, name)


if __name__ == "__main__":
    unittest.main()
