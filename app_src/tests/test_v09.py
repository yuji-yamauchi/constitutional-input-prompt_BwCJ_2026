# -*- coding: utf-8 -*-
"""器 v0.9（きょうの 気分＝60 問を チャットの 中で 出す・条件の 札と 向きを 画面から 消す）で足した物の検査。
N_＝陰性対照（先）／T_＝本物。標準ライブラリだけ・ネットワークへは出ない。

- 60 問の 字と 選択肢（kibun.py）の 走査（禁じる 言い方 0・促しの 形 0）・型ごとの 選択肢
- 口（/api/kibun/items・/api/kibun/runs・/api/kibun/days/<日付>）の 形と 境
- 保存（kibun/<日付>.json）・書き出しの 数（counts_extra.kibun）・全消去・束に 入れない・点を 計算しない
- 録画用の シナリオ（demo/recorded/listener/<sha16>.json）が 入力の 字から 引ける こと
- 画面の 静的な 確かめ（条件の 札・向き・気分の 面が 無い。新しい W の 走査）
"""
import hashlib
import json
import os
import re
import stat
import tempfile
import unittest
import zipfile

from app_src.common import ids, words
from app_src.tests.test_vault_api import Srv, env_ok
from app_src.vault_app import claude_client, kibun, routes_handoff, storage

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(APP_ROOT, "vault_app", "static")
DEMO_LISTENER = os.path.join(APP_ROOT, "demo", "recorded", "listener")
DAY = ids.now_jst()[:10]
COND = {"amount": "ふつう", "split": "区切らない", "ease": "ふつう", "length": "みじかく", "input": "文字"}   # app.js の DEFAULT_COND と同じ
NEW_W = ["W-268", "W-269", "W-270", "W-271", "W-272", "W-273", "W-274", "W-275", "W-276", "W-277", "W-278", "W-279", "W-280", "W-281", "W-282"]
PUSHY = re.compile(r"ましょう|しよう|ください|[一-龥]{1}\s*[！!]")
# 録画用の シナリオの 入力（仕様書 v0.9 §3.7。末尾の「。」の 有無 どちらでも 引ける）
SCENARIO = [
    "きょうは朝早く目がさめた。",
    "外に出て、少し歩いた。",
    "帰ってきてから、ねむくなった。",
    "夕方に友だちから電話があった。",
]


def _read(rel):
    with open(os.path.join(STATIC, rel), "rb") as f:
        return f.read().decode("utf-8").replace("\r\n", "\n")


def _w_value(js, code):
    m = re.search(r"'%s': '([^']*)'" % re.escape(code), js)
    return m.group(1) if m else None


def _sha16(text):
    kb = json.dumps({"text": text, "conditions": COND}, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(kb).hexdigest()[:16]


class _Base(unittest.TestCase):
    def make(self):
        s = Srv(env_ok())
        self.addCleanup(s.close)
        s.login()
        return s

    def run_body(self, answers, run_id=None, count=10, start_id=1, finished=False, date=DAY):
        return {"date": date, "run_id": run_id, "count": count, "start_id": start_id, "version": "c", "answers": answers, "finished": finished}


class N_Kibun(_Base):
    def test_a_counting_notices_a_kibun_file(self):
        self.assertEqual(storage.count_extra_from_files(["manifest.json"]), {"daily": 0, "kibun": 0})
        self.assertEqual(storage.count_extra_from_files(["kibun/2026-11-07.json", "daily/2026-11-07.json"]), {"daily": 1, "kibun": 1})
        self.assertEqual(storage.count_extra_from_files(["kibun/.x.json", "kibun/a/b.json"]), {"daily": 0, "kibun": 0})

    def test_b_zip_with_wrong_kibun_count_is_rejected(self):
        s = self.make()
        v = s.app.vault
        s.call("POST", "/api/kibun/runs", self.run_body([{"id": 1, "choice": "few"}]))
        path, _ = v.export_zip(os.path.join(s.tmp.name, "exp"))
        bad = path + ".bad.zip"
        with zipfile.ZipFile(path) as zin, zipfile.ZipFile(bad, "w") as zout:
            for n in zin.namelist():
                data = zin.read(n)
                if n == "manifest.json":
                    m = json.loads(data.decode("utf-8"))
                    m["counts_extra"]["kibun"] += 1
                    data = json.dumps(m, ensure_ascii=False).encode("utf-8")
                zout.writestr(n, data)
        with self.assertRaises(storage.ExportCountMismatch):
            storage.verify_export_zip(bad)

    def test_c_bad_bodies_are_400(self):
        s = self.make()
        ok = {"id": 1, "choice": "few"}
        cases = [
            (dict(self.run_body([ok]), count=7), "bad_count"),
            (dict(self.run_body([ok]), count="10"), "bad_count"),
            (dict(self.run_body([ok]), date="2026-02-30"), "bad_date"),
            (dict(self.run_body([ok]), extra=1), "unknown_field"),
            (dict(self.run_body([ok]), version="a"), "bad_request"),
            (dict(self.run_body([ok]), start_id=61), "bad_request"),
            (self.run_body([{"id": 1, "choice": "yes"}]), "bad_answer"),          # F 型に E の 鍵
            (self.run_body([{"id": 2, "choice": "few"}]), "bad_answer"),          # E 型に F の 鍵
            (self.run_body([{"id": 0, "choice": "few"}]), "bad_answer"),
            (self.run_body([{"id": 61, "choice": "unsure"}]), "bad_answer"),
            (self.run_body([ok, ok]), "bad_answer"),                                 # 同じ id を 2 回
            (self.run_body([{"id": 1, "choice": "few", "x": 1}]), "bad_answer"),
            (self.run_body([{"id": "1", "choice": "few"}]), "bad_answer"),
            (self.run_body([{"id": i, "choice": "unsure"} for i in range(1, 12)], count=10), "bad_answer"),   # 数より 多い
            (self.run_body("x"), "bad_answer"),
        ]
        for body, err in cases:
            st, j, _, _ = s.call("POST", "/api/kibun/runs", body)
            self.assertEqual((st, j.get("error")), (400, err), body)
        st, j, _, _ = s.call("POST", "/api/kibun/runs", self.run_body([ok], run_id="nope-0123"))
        self.assertEqual((st, j["error"]), (404, "not_found"))
        self.assertFalse(os.path.isdir(os.path.join(s.app.vault.root, "kibun")))

    def test_d_needs_login(self):
        s = Srv(env_ok())
        self.addCleanup(s.close)
        self.assertEqual(s.call("GET", "/api/kibun/items", cookie=False)[0], 401)
        self.assertEqual(s.call("POST", "/api/kibun/runs", self.run_body([]), cookie=False)[0], 401)
        self.assertEqual(s.call("GET", "/api/kibun/days/" + DAY, cookie=False)[0], 401)

    def test_e_scanner_reacts(self):
        self.assertTrue(words.scan("この 問いで 評価する"))
        self.assertTrue(PUSHY.search("やって みましょう"))


class T_Items(unittest.TestCase):
    def test_sixty_items_three_types_and_choices(self):
        self.assertEqual(kibun.N_ITEMS, 60)
        self.assertEqual([r[0] for r in kibun.ITEMS], list(range(1, 61)))
        self.assertEqual(set(r[2] for r in kibun.ITEMS), {"F", "E", "S"})
        self.assertEqual(kibun.VERSION, "c")
        self.assertEqual(kibun.COUNTS, (10, 30, 60))
        self.assertEqual(kibun.choice_keys(1), ("none", "few", "sometimes", "often", "unsure"))
        self.assertEqual(kibun.choice_keys(2), ("yes", "no", "unsure"))
        self.assertEqual(kibun.choice_keys(34), ("yes", "no", "unsure"))
        self.assertEqual(kibun.choice_keys(99), ())

    def test_item_text_and_labels_pass_the_scanner(self):
        for r in kibun.ITEMS:
            self.assertEqual(words.scan(r[3]), [], r)
            self.assertIsNone(PUSHY.search(r[3]), r)
            self.assertLessEqual(len(r[3].replace(" ", "")), 40, r)
            self.assertTrue(r[3].endswith("？") or r[3].endswith("）"), r)
        for t, rows in kibun.CHOICES.items():
            for k, label in rows:
                self.assertEqual(words.scan(label), [], label)
                self.assertRegex(k, r"^[a-z]+$")

    def test_pick_and_next(self):
        self.assertEqual(kibun.pick_ids(1, 10), list(range(1, 11)))
        self.assertEqual(kibun.pick_ids(55, 10), [55, 56, 57, 58, 59, 60, 1, 2, 3, 4])
        self.assertEqual(len(kibun.pick_ids(31, 60)), 60)
        self.assertEqual(kibun.pick_ids(31, 60)[0], 31)
        self.assertEqual(kibun.next_id_after(None), 1)
        self.assertEqual(kibun.next_id_after(10), 11)
        self.assertEqual(kibun.next_id_after(60), 1)


class T_Api(_Base):
    def test_items_endpoint(self):
        s = self.make()
        st, j, _, _ = s.call("GET", "/api/kibun/items")
        self.assertEqual(st, 200)
        self.assertEqual((j["version"], j["counts"], j["next_id"], len(j["items"])), ("c", [10, 30, 60], 1, 60))
        self.assertEqual(j["items"][0], {"id": 1, "group": "ちょうし", "type": "F", "text": kibun.ITEMS[0][3]})
        self.assertEqual([c["key"] for c in j["choices"]["F"]], ["none", "few", "sometimes", "often", "unsure"])
        self.assertEqual([c["label"] for c in j["choices"]["E"]], ["あった", "なかった", "わからない"])
        self.assertEqual([c["label"] for c in j["choices"]["S"]], ["はい", "いいえ", "わからない"])

    def test_run_is_created_then_replaced_and_next_id_follows(self):
        s = self.make()
        v = s.app.vault
        st, j, _, _ = s.call("POST", "/api/kibun/runs", self.run_body([{"id": 1, "choice": "few"}]))
        self.assertEqual((st, j["saved"], j["finished"], j["date"]), (200, 1, False, DAY))
        rid = j["run_id"]
        self.assertRegex(rid, r"^[A-Za-z0-9_-]+$")
        st, j, _, _ = s.call("POST", "/api/kibun/runs", self.run_body([{"id": 1, "choice": "few"}, {"id": 2, "choice": "no"}], run_id=rid, finished=True))
        self.assertEqual((st, j["run_id"], j["saved"], j["finished"]), (200, rid, 2, True))
        st, j, _, _ = s.call("GET", "/api/kibun/days/" + DAY)
        self.assertEqual(st, 200)
        self.assertEqual(len(j["runs"]), 1)
        run = j["runs"][0]
        self.assertEqual(sorted(run), ["answers", "count", "finished_at", "run_id", "start_id", "started_at", "updated_at", "version"])
        self.assertEqual(run["answers"], [{"id": 1, "choice": "few"}, {"id": 2, "choice": "no"}])
        self.assertIsNotNone(run["finished_at"])
        for bad in ("score", "total", "sum", "点", "rank", "level"):
            self.assertNotIn(bad, json.dumps(run, ensure_ascii=False))
        path = os.path.join(v.root, "kibun", DAY + ".json")
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
        st, j, _, _ = s.call("GET", "/api/kibun/items")
        self.assertEqual(j["next_id"], 3)
        # 2 回目は 新しい 回（同じ 日の ファイルに 並ぶ）
        st, j, _, _ = s.call("POST", "/api/kibun/runs", self.run_body([{"id": 60, "choice": "often"}], start_id=60, finished=True))
        self.assertEqual(st, 200)
        self.assertEqual(len(v.get_kibun_day(DAY)["runs"]), 2)
        self.assertEqual(s.call("GET", "/api/kibun/items")[1]["next_id"], 1)      # 60 の つぎは 1

    def test_empty_day_and_bad_date(self):
        s = self.make()
        st, j, _, _ = s.call("GET", "/api/kibun/days/2026-01-01")
        self.assertEqual((st, j), (200, {"date": "2026-01-01", "runs": []}))
        self.assertEqual(s.call("GET", "/api/kibun/days/2026-13-01")[0], 400)
        self.assertEqual(s.call("GET", "/api/kibun/items")[1]["next_id"], 1)

    def test_export_counts_wipe_and_bundle(self):
        s = self.make()
        v = s.app.vault
        self.assertEqual(v.read_manifest()["counts_extra"], {"daily": 0, "kibun": 0})
        s.call("POST", "/api/kibun/runs", self.run_body([{"id": 1, "choice": "few"}], finished=True))
        s.call("POST", "/api/kibun/runs", self.run_body([{"id": 1, "choice": "few"}], date="2026-01-02", finished=True))
        self.assertEqual(v.read_manifest()["counts_extra"], {"daily": 0, "kibun": 2})
        path, counts = v.export_zip(os.path.join(s.tmp.name, "exp"))
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            self.assertIn("kibun/%s.json" % DAY, names)
            self.assertIn("kibun/2026-01-02.json", names)
            self.assertEqual(json.loads(z.read("manifest.json").decode("utf-8"))["counts_extra"], {"daily": 0, "kibun": 2})
        self.assertEqual(storage.verify_export_zip(path), counts)
        # 束には 入れない
        v.save_pairing({"person_ref": "p-test", "port_id": "port-test", "port_name": "受け口"})
        sid = v.save_statement({"item_id": "st-test", "finalized_at": "2026-11-06T10:00:00+09:00", "text": "朝の ことを 相談したいです。",
                                "sections": {"trouble": "朝が つらい", "wish": "遅くしたい", "grounds": [], "statute_ids": []}})
        bundle, rows = routes_handoff.build_bundle(s.app, {"statement_id": sid})
        self.assertNotIn("kibun", json.dumps(bundle, ensure_ascii=False))
        with open(routes_handoff.__file__, "rb") as f:
            self.assertNotIn(b"kibun", f.read())
        # 全消去
        st, _, _, _ = s.call("DELETE", "/api/vault", {"confirm": "消します", "keep_receipts": False})
        self.assertEqual(st, 204)
        self.assertFalse(os.path.isdir(os.path.join(v.root, "kibun")))
        self.assertEqual(v.read_manifest()["counts_extra"], {"daily": 0, "kibun": 0})

    def test_claude_is_not_called_for_kibun(self):
        s = self.make()
        s.call("POST", "/api/kibun/runs", self.run_body([{"id": 1, "choice": "few"}], finished=True))
        self.assertEqual(s.app.vault.get_claude_log(), [])


class T_Demo(unittest.TestCase):
    def test_scenario_recordings_exist_and_follow_the_listener_rules(self):
        for text in SCENARIO:
            for t in (text, text.rstrip("。")):
                p = os.path.join(DEMO_LISTENER, _sha16(t) + ".json")
                self.assertTrue(os.path.isfile(p), t)
                with open(p, "rb") as f:
                    d = json.loads(f.read().decode("utf-8"))
                self.assertIs(d.get("recorded_from_live"), False, t)
                self.assertIsNone(claude_client.check_question(d.get("question")), t)
                self.assertNotIn(t, d["question"])
        for n in os.listdir(DEMO_LISTENER):
            self.assertRegex(n, r"^([0-9a-f]{16}|default)\.json$")

    def test_demo_server_returns_the_scenario_question(self):
        s = Srv(env_ok(CIP_DEMO_MODE="1"))
        self.addCleanup(s.close)
        s.login()
        st, j, _, _ = s.call("POST", "/api/practice/turns", {"conditions": COND, "text": SCENARIO[0]})
        self.assertEqual(st, 200)
        self.assertEqual(j["question"], "目が さめた あと、どんな ことを していましたか？")
        self.assertTrue(j["demo"])
        st, j, _, _ = s.call("POST", "/api/practice/turns", {"conditions": COND, "text": "シナリオに 無い 文"})
        self.assertEqual(j["question"], "そのとき、どんな 音が していましたか？")       # default.json


class T_Screen(unittest.TestCase):
    def test_new_strings_pass_the_scanner(self):
        js = _read("app.js")
        for code in NEW_W:
            v = _w_value(js, code)
            self.assertIsNotNone(v, code)
            self.assertEqual(words.scan(v), [], code)
            self.assertIsNone(PUSHY.search(v), code)
        self.assertEqual(_w_value(js, "W-268"), "きょうの 気分を きかせて くれるかな？")
        self.assertEqual(_w_value(js, "W-245"), "10 ／ 30 ／ 60")
        self.assertIn("'W-29': 'v0.3.3 / 2026-11-06'", js)

    def test_conditions_and_direction_are_gone_from_the_screen(self):
        js = _read("app.js")
        for bad in ("refreshCondBar", "condbar", "startPick", "S.mood", "conditionsTitle", "countsTitle", "summary-box'", "dir-card"):
            self.assertNotIn(bad, js, bad)
        # 裏では 条件の 初期値を 送り続ける
        self.assertIn("var DEFAULT_COND = { amount: 'ふつう', split: '区切らない', ease: 'ふつう', length: 'みじかく', input: '文字' };", js)
        self.assertIn("cond: copy(DEFAULT_COND),", js)
        self.assertIn("var cond = copy(S.cond);", js)
        # 「書く れんしゅう」の 画面は 説明だけ
        m = re.search(r"function renderRenshu\(host\) \{(.*?)\n  \}\n", js, re.S)
        body = m.group(1)
        for need in ("W['W-278']", "W['W-279']", "W['W-280']"):
            self.assertIn(need, body)
        for bad in ("chip-btn", "S.cond", "loadSummary"):
            self.assertNotIn(bad, body)

    def test_kibun_flow_in_the_chat(self):
        js = _read("app.js")
        for need in ("function newKibun()", "function kibunIntro()", "async function kibunStart()", "function kibunAnswer(m, key, label)",
                     "function kibunStop(m)", "function kibunSave(finished)", "function kibunRow(m)",
                     "api('GET', '/api/kibun/items')", "api('POST', '/api/kibun/runs', body)", "api('PUT', '/api/daily/' + d,"):
            self.assertIn(need, js, need)
        m = re.search(r"function kibunSave\(finished\) \{(.*?)\n  \}\n", js, re.S)
        body = m.group(1)
        self.assertIn("var body = { date: k.date, run_id: k.runId, count: k.count, start_id: k.startId, version: 'c', answers: k.answers.slice(), finished: finished };", body)
        for bad in ("bed_time", "wake_time", "breakfast", "S.chat", "readback", "question"):
            self.assertNotIn(bad, body)                       # 本人の 字や きょうの ことの 値は 送らない（送るのは 日付・数・id と 選択肢の 鍵だけ）
        # 問いは 器の 吹き出し（sys）＝Claude の 札（W-141）を 付けない
        m = re.search(r"function kibunAsk\(\) \{(.*?)\n  \}\n", js, re.S)
        self.assertIn("who: 'sys'", m.group(1))
        self.assertNotIn("'them'", m.group(1))
        # 端末には 覚えない
        for m2 in re.finditer(r"lsSet\([^\n]*", js):
            self.assertNotIn("kibun", m2.group(0))
            self.assertNotIn("S.daily", m2.group(0))
        self.assertEqual(len(re.findall(r"lsSet\(", js)), 4)

    def test_readme_mentions_kibun(self):
        with open(os.path.join(APP_ROOT, "README_run.md"), "rb") as f:
            self.assertIn("kibun/", f.read().decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
