# -*- coding: utf-8 -*-
"""器 v0.3.3（ホームの面の作り替え）で足した物の検査。N_＝陰性対照（先）／T_＝本物。標準ライブラリだけ・ネットワークへは出ない。

- きょうの こと（daily/<日付>.json）の保存・口・書き出しの数・全消去・束に入れない
- 聞き役の入力（問いの向き・きょうの こと）と、鍵（key_bytes）が変わらないこと・記録に値を書かないこと
- 指示の文の版（聞き役だけ v0.3.3）
- 画面の字（新しい W）の走査・画面の部品の静的な確かめ
"""
import datetime
import hashlib
import json
import os
import re
import stat
import tempfile
import unittest
import zipfile

from app_src.common import words
from app_src.common import ids
from app_src.tests.test_vault_api import Srv, env_ok
from app_src.vault_app import claude_client, routes_handoff, storage

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPTS = os.path.join(APP_ROOT, "vault_app", "prompts")
STATIC = os.path.join(APP_ROOT, "vault_app", "static")
COND = {"amount": "ふつう", "split": "文ごと", "ease": "やさしい", "length": "みじかく", "input": "文字"}
DAY = ids.now_jst()[:10]          # きょう（日本時間）＝添えられるのは その日の分だけ なので、固定の日付にしない
DAY2 = (datetime.date.fromisoformat(DAY) - datetime.timedelta(days=1)).isoformat()   # きょうの 前の日＝「きょうと 違う日」を 必ず 作る（2 日分を 数える 検査に 使う）
BED, WAKE = "23:47", "06:13"
NEW_W = ["W-173", "W-174", "W-175", "W-176", "W-177", "W-178", "W-179", "W-241", "W-242", "W-243", "W-244", "W-245",
         "W-246", "W-247", "W-248", "W-250", "W-251", "W-252", "W-253", "W-254", "W-255", "W-256", "W-257", "W-258",
         "W-259", "W-260", "W-261", "W-262", "W-263", "W-264", "W-265"]


def _read(rel):
    with open(os.path.join(STATIC, rel), "rb") as f:
        return f.read().decode("utf-8").replace("\r\n", "\n")


def _w_value(js, code):
    m = re.search(r"'%s': '([^']*)'" % re.escape(code), js)
    return m.group(1) if m else None


class Capture(claude_client.ClaudeClient):
    """通信の部品を使わず、Claude に渡る user の字を覚えておく。"""
    def __init__(self, vault, clock):
        cfg = {"api_key": "dummy-key", "demo_mode": False, "claude_model": "test-model"}
        super().__init__(cfg, vault, clock, PROMPTS)
        self.seen = []

    def _live_text(self, kind, system, blocks):
        self.seen.append(blocks[0]["text"])
        return '{"question": "そのとき、どんな 音が していましたか？"}'


class _Base(unittest.TestCase):
    def make(self, env=None):
        s = Srv(env if env is not None else env_ok())
        self.addCleanup(s.close)
        s.login()
        return s

    def capture(self, s):
        c = Capture(s.app.vault, s.app.clock)
        s.app.claude = c
        return c

    def daily_path(self, s, day=DAY):
        return os.path.join(s.app.vault.root, "daily", day + ".json")

    def put(self, s, day=DAY, bed=BED, wake=WAKE, bf="yes"):
        return s.call("PUT", "/api/daily/" + day, {"bed_time": bed, "wake_time": wake, "breakfast": bf})


# =====================================================================
# N_ 陰性対照（先）
# =====================================================================

class N_DailyApi(_Base):
    def test_login_required(self):
        s = Srv(env_ok())
        self.addCleanup(s.close)
        self.assertEqual(s.call("GET", "/api/daily/" + DAY, cookie=False)[0], 401)
        self.assertEqual(s.call("PUT", "/api/daily/" + DAY, {}, cookie=False)[0], 401)

    def test_bad_time_is_400_and_nothing_is_written(self):
        s = self.make()
        for bad in ("24:00", "7:00", "12:60", "12:00:00", "ab:cd", "", 5, True, ["07:00"]):
            st, j, _, _ = s.call("PUT", "/api/daily/" + DAY, {"bed_time": bad, "wake_time": None, "breakfast": None})
            self.assertEqual((st, j["error"]), (400, "bad_time"), repr(bad))
            self.assertTrue(words.is_clean(j["detail"]))
        st, j, _, _ = s.call("PUT", "/api/daily/" + DAY, {"bed_time": None, "wake_time": "7:5"})
        self.assertEqual((st, j["error"]), (400, "bad_time"))
        self.assertFalse(os.path.exists(self.daily_path(s)))

    def test_bad_date_is_400_for_get_and_put(self):
        s = self.make()
        for bad in ("2026-13-01", "2026-02-30", "abc", "2026-1-1", "20261106", "2026-11-06x"):
            st, j, _, _ = s.call("GET", "/api/daily/" + bad)
            self.assertEqual((st, j["error"]), (400, "bad_date"), bad)
            self.assertTrue(words.is_clean(j["detail"]))
            st, j, _, _ = s.call("PUT", "/api/daily/" + bad, {"bed_time": "07:00"})
            self.assertEqual((st, j["error"]), (400, "bad_date"), bad)
        self.assertFalse(os.path.isdir(os.path.join(s.app.vault.root, "daily")))

    def test_unknown_field_and_bad_breakfast_are_400(self):
        s = self.make()
        st, j, _, _ = s.call("PUT", "/api/daily/" + DAY, {"bed_time": "07:00", "mood": "x"})
        self.assertEqual((st, j["error"]), (400, "unknown_field"))
        for bad in ("maybe", "YES", 1, False):
            st, j, _, _ = s.call("PUT", "/api/daily/" + DAY, {"breakfast": bad})
            self.assertEqual((st, j["error"]), (400, "bad_breakfast"), repr(bad))
        self.assertFalse(os.path.exists(self.daily_path(s)))

    def test_all_null_put_removes_the_file(self):
        s = self.make()
        self.assertEqual(self.put(s)[0], 200)
        self.assertTrue(os.path.isfile(self.daily_path(s)))
        st, j, _, _ = s.call("PUT", "/api/daily/" + DAY, {"bed_time": None, "wake_time": None, "breakfast": None})
        self.assertEqual(st, 200)
        self.assertFalse(os.path.exists(self.daily_path(s)))
        self.assertEqual((j["bed_time"], j["wake_time"], j["breakfast"], j["updated_at"]), (None, None, None, None))
        # 無い日に 全部 null を送っても 何も起きない
        self.assertEqual(s.call("PUT", "/api/daily/2026-11-07", {})[0], 200)
        self.assertFalse(os.path.exists(self.daily_path(s, "2026-11-07")))

    def test_storage_rejects_bad_values(self):
        s = self.make()
        v = s.app.vault
        for args in ((DAY, "25:00", None, None), (DAY, None, "7:00", None), (DAY, None, None, "maybe"), ("2026-02-30", "07:00", None, None), ("x", None, None, None)):
            with self.assertRaises(ValueError):
                v.set_daily(*args)


class N_ListenerInput(_Base):
    # v0.15: 旧「通す側」の 4 件（test_bad_direction_is_400・test_share_daily_needs_a_date・test_key_bytes_do_not_change_with_direction_or_daily・
    # test_daily_values_are_not_in_the_turn_record_or_the_logs）は 消し、「断る／使わない」側の 4 件に 入れ替えた。
    def _turn_files(self, s):
        d = os.path.join(s.app.vault.root, "practice", "turns")
        return os.listdir(d) if os.path.isdir(d) else []

    def test_any_direction_value_is_closed(self):
        s = self.make()
        c = self.capture(s)
        for bad in ("ippo", "kotoba", "wakaranai", "oboeru", "nokosu", "IPPO", "", 1, ["ippo"], True, False):
            st, j, _, _ = s.call("POST", "/api/practice/turns", {"conditions": COND, "text": "朝です。", "direction": bad})
            self.assertEqual((st, j["error"]), (400, "closed_input"), repr(bad))
        self.assertEqual(c.seen, [])
        self.assertEqual(self._turn_files(s), [])

    def test_share_daily_is_closed_even_with_todays_date(self):
        s = self.make()
        c = self.capture(s)
        self.put(s)
        for extra in ({"share_daily": True}, {"share_daily": True, "daily_date": DAY}, {"share_daily": "yes", "daily_date": DAY},
                      {"share_daily": 1, "daily_date": DAY}, {"share_daily": None, "daily_date": DAY}, {"share_daily": True, "daily_date": "2026-02-30"}):
            body = dict({"conditions": COND, "text": "朝です。"}, **extra)
            st, j, _, _ = s.call("POST", "/api/practice/turns", body)
            self.assertEqual((st, j["error"]), (400, "closed_input"), repr(extra))
        self.assertEqual(c.seen, [])
        self.assertEqual(self._turn_files(s), [])

    def test_daily_values_never_reach_the_turn_record_or_the_logs(self):
        s = self.make()
        self.capture(s)
        self.put(s)
        st, j, _, _ = s.call("POST", "/api/practice/turns", {"conditions": COND, "text": "朝です。", "direction": "ippo", "share_daily": True, "daily_date": DAY})
        self.assertEqual((st, j["error"]), (400, "closed_input"))
        st, j, _, _ = s.call("POST", "/api/practice/turns", {"conditions": COND, "text": "朝です。", "direction": None})
        self.assertEqual(st, 200)
        root = s.app.vault.root
        hits = []
        for base, _d, files in os.walk(root):
            if os.path.basename(base) == "daily":
                continue
            for f in files:
                with open(os.path.join(base, f), "rb") as g:
                    raw = g.read().decode("utf-8", "replace")
                if BED in raw or WAKE in raw:
                    hits.append(f)
        self.assertEqual(hits, [])
        turn = s.app.vault.get_turn(j["turn_id"])
        self.assertEqual((turn["direction"], turn["shared_daily"]), (None, False))
        self.assertEqual(sorted(k for k in turn if k in ("bed_time", "wake_time", "breakfast", "daily")), [])

    def test_build_listener_takes_text_and_conditions_only(self):
        s = self.make()
        c = self.capture(s)
        with self.assertRaises(TypeError):
            c.build_listener("朝です。", COND, direction="kotoba")
        with self.assertRaises(TypeError):
            c.build_listener("朝です。", COND, None, None)
        with self.assertRaises(TypeError):
            c.ask_question("朝です。", COND, None, None)
        self.assertFalse(hasattr(claude_client, "DIRECTION_LABELS"))
        self.assertFalse(hasattr(claude_client, "BREAKFAST_LABELS"))
        key = c.build_listener("朝です。", COND)[2]
        self.assertEqual(json.loads(key.decode("utf-8")), {"text": "朝です。", "conditions": COND})

    def test_daily_is_not_in_the_handoff_bundle(self):
        s = self.make()
        v = s.app.vault
        self.put(s)
        v.save_pairing({"person_ref": "p-test", "port_id": "port-test", "port_name": "受け口"})
        sid = v.save_statement({"item_id": "st-test", "finalized_at": "2026-11-06T10:00:00+09:00", "text": "朝の ことを 相談したいです。",
                                "sections": {"trouble": "朝が つらい", "wish": "遅くしたい", "grounds": [], "statute_ids": []}})
        bundle, rows = routes_handoff.build_bundle(s.app, {"statement_id": sid})
        raw = json.dumps(bundle, ensure_ascii=False)
        for bad in ("daily", BED, WAKE, "bed_time", "breakfast"):
            self.assertNotIn(bad, raw)
        with open(routes_handoff.__file__, "rb") as f:
            self.assertNotIn(b"daily", f.read())

    def test_listener_header_is_v034(self):
        # v0.14: 聞き役だけ v0.3.4（2 節を 外した）。reader・arranger は v0.3.1 のまま
        with open(os.path.join(PROMPTS, "listener.txt"), "rb") as f:
            first = f.read().decode("utf-8").replace("\r\n", "\n").split("\n", 1)[0]
        self.assertEqual(first, "# 版: v0.3.4 / 決めた日: 2026-11-08")
        for kind in ("reader", "arranger"):
            with open(os.path.join(PROMPTS, kind + ".txt"), "rb") as f:
                self.assertEqual(f.read().decode("utf-8").replace("\r\n", "\n").split("\n", 1)[0], "# 版: v0.3.1 / 決めた日: 2026-11-05")


class N_ExportCount(_Base):
    def _rebuild(self, src, dst, edit):
        with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w") as zout:
            for n in zin.namelist():
                data = edit(n, zin.read(n))
                if data is not None:
                    zout.writestr(n, data)

    def test_counts_extra_that_differs_raises(self):
        s = self.make()
        self.put(s)
        path, _ = s.app.vault.export_zip(os.path.join(os.path.dirname(s.app.vault.root), "out"))
        tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(tmp, ignore_errors=True))

        def bump(n, data):
            if n == "manifest.json":
                m = json.loads(data.decode("utf-8"))
                m["counts_extra"]["daily"] += 1
                return json.dumps(m)
            return data
        bad = os.path.join(tmp, "bump.zip")
        self._rebuild(path, bad, bump)
        with self.assertRaises(storage.ExportCountMismatch):
            storage.verify_export_zip(bad)

    def test_a_daily_file_missing_from_the_zip_is_noticed(self):
        s = self.make()
        self.put(s)
        path, _ = s.app.vault.export_zip(os.path.join(os.path.dirname(s.app.vault.root), "out"))
        tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(tmp, ignore_errors=True))
        bad = os.path.join(tmp, "drop.zip")
        self._rebuild(path, bad, lambda n, d: None if n.startswith("daily/") else d)
        with self.assertRaises(storage.ExportCountMismatch):
            storage.verify_export_zip(bad)


class N_Words(unittest.TestCase):
    def test_scanner_reacts_to_a_nudge_in_a_new_string(self):
        self.assertTrue(words.scan("早く 寝ましょう。毎日 つづけよう"))
        self.assertTrue(words.scan("この記録を評価する。"))


# =====================================================================
# T_ 本物
# =====================================================================

class T_DailyStorage(_Base):
    def test_get_put_get_round_trip(self):
        s = self.make()
        st, j, _, _ = s.call("GET", "/api/daily/" + DAY)
        self.assertEqual(st, 200)
        self.assertEqual(j, {"date": DAY, "bed_time": None, "wake_time": None, "breakfast": None, "updated_at": None})
        st, j, _, _ = self.put(s)
        self.assertEqual(st, 200)
        self.assertEqual((j["date"], j["bed_time"], j["wake_time"], j["breakfast"]), (DAY, BED, WAKE, "yes"))
        self.assertRegex(j["updated_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+09:00$")
        st, j2, _, _ = s.call("GET", "/api/daily/" + DAY)
        self.assertEqual(j2, j)
        # 欠けた鍵は null 扱い
        st, j3, _, _ = s.call("PUT", "/api/daily/" + DAY, {"wake_time": "07:00"})
        self.assertEqual((st, j3["bed_time"], j3["wake_time"], j3["breakfast"]), (200, None, "07:00", None))
        with open(self.daily_path(s), "rb") as f:
            row = json.loads(f.read().decode("utf-8"))
        self.assertEqual(sorted(row), ["bed_time", "breakfast", "date", "updated_at", "wake_time"])

    @unittest.skipIf(os.name == "nt", "権限の数字は Windows では見ない")
    def test_file_permission_is_600(self):
        s = self.make()
        self.put(s)
        self.assertEqual(stat.S_IMODE(os.stat(self.daily_path(s)).st_mode), 0o600)

    def test_manifest_zip_and_wipe(self):
        s = self.make()
        v = s.app.vault
        self.assertEqual(v.read_manifest()["counts_extra"], {"daily": 0, "kibun": 0})
        self.put(s)
        self.put(s, day=DAY2, bed=None, wake="07:00", bf=None)
        m = v.read_manifest()
        self.assertEqual(m["counts_extra"], {"daily": 2, "kibun": 0})
        self.assertEqual(m["counts"], {k: 0 for k in m["counts"]})      # 8 鍵は そのまま
        path, counts = v.export_zip(os.path.join(os.path.dirname(v.root), "out"))
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            self.assertIn("daily/%s.json" % DAY, names)
            self.assertIn("daily/%s.json" % DAY2, names)
            self.assertEqual(json.loads(z.read("daily/%s.json" % DAY).decode("utf-8"))["bed_time"], BED)
            self.assertEqual(json.loads(z.read("manifest.json").decode("utf-8"))["counts_extra"], {"daily": 2, "kibun": 0})
        self.assertEqual(storage.verify_export_zip(path), counts)
        self.assertEqual(sorted(counts), sorted(m["counts"]))
        v.wipe()
        self.assertFalse(os.path.isdir(os.path.join(v.root, "daily")))
        self.assertEqual(v.read_manifest()["counts_extra"], {"daily": 0, "kibun": 0})


class T_ListenerInput(_Base):
    # v0.15: 旧 4 件（test_user_text_has_daily_section_without_null_rows・test_nothing_is_added_when_off_or_empty・
    # test_direction_line_for_every_direction・test_direction_comes_before_daily）は 消し、次の 1 件に 入れ替えた。
    def test_screen_shaped_bodies_pass_and_add_nothing(self):
        s = self.make()
        c = self.capture(s)
        self.put(s)
        shapes = ({}, {"direction": None}, {"direction": None, "share_daily": False}, {"share_daily": False, "daily_date": DAY})
        want = "本人の文:\n朝です。\n\n条件:\n" + "\n".join("- %s: %s" % (k, COND[k]) for k in sorted(COND))
        for extra in shapes:
            st, j, _, _ = s.call("POST", "/api/practice/turns", dict({"conditions": COND, "text": "朝です。"}, **extra))
            self.assertEqual(st, 200, repr(extra))
            turn = s.app.vault.get_turn(j["turn_id"])
            self.assertEqual((turn["direction"], turn["shared_daily"]), (None, False))
        self.assertEqual(len(c.seen), 4)
        for user in c.seen:
            self.assertEqual(user, want)
            for bad in ("問いの 向き", "きょうの こと", BED, WAKE, "あさごはん"):
                self.assertNotIn(bad, user)

    def test_listener_prompt_keeps_the_promise_lines(self):
        # v0.14: 「問いの 向き」「きょうの こと」の 2 節は 外した（画面から 届く 経路が 無い。無い ことの 検査は test_v014）。
        # 外した 節に あった 安全の 決め（良し悪しを 言わない・すすめない）は「やくそく」節の 2 行が 同じ 趣旨で 残る＝ここで 見る。
        with open(os.path.join(PROMPTS, "listener.txt"), "rb") as f:
            raw = f.read().decode("utf-8").replace("\r\n", "\n")
        for need in ("やくそく\n", "- 良し悪しは 言いません。ほめも、直しも しません。\n", "- すすめる 言い方は しません。\n", "- 数字は 使いません。\n"):
            self.assertIn(need, raw)
        self.assertLess(raw.index("やくそく\n"), raw.index("返す 形"))
        self.assertEqual(words.scan(raw), [])


class T_Screen(unittest.TestCase):
    def test_new_strings_pass_the_scanner_and_have_no_pushy_words(self):
        js = _read("app.js")
        for code in NEW_W:
            v = _w_value(js, code)
            self.assertIsNotNone(v, code)
            self.assertEqual(words.scan(v), [], code)
            self.assertNotRegex(v, r"ましょう|しよう|ください|[一-龥]{1}\s*[！!]", code)

    def test_decided_strings(self):
        js = _read("app.js")
        self.assertEqual(_w_value(js, "W-29"), "v0.3.4 / 2026-11-08")   # v0.15: listener.txt の 版と 同じ
        self.assertEqual(_w_value(js, "W-252"), "ゆうべ ねた 時刻")
        self.assertEqual(_w_value(js, "W-242"), "おぼえて おきたい こと")
        self.assertEqual(_w_value(js, "W-243"), "きょう あった ことで、おぼえて おきたい ことを たずねます。")
        self.assertIn("{ key: 'oboeru', title: 'W-242', desc: 'W-243' }", js)
        self.assertNotIn("nokosu", js)
        self.assertNotIn("moods", js)
        self.assertNotIn("mood-card", js)
        self.assertIsNone(_w_value(js, "W-249"))

    def test_home_has_no_mood_face_and_no_scene_button(self):
        # v0.12: ホームの「きょうの気分」の 絵の 釦も なくした（ホームは あいさつと とどいた返事だけ。チャットは 左の 帯の 釦から 開く）。
        # （v0.3.3〜v0.8 の test_direction_cards＝4 枚の 向きの 札 → v0.9 の test_home_scene_button_opens_the_chat＝絵の 釦だけ → 本検査。
        #   見たい ことは 同じ＝ホームに 向きの 札・数の 札・時刻の 欄・「聞き役に 伝える」・board( が 無い こと。釦が 無い ことは test_v012 が 見る）
        js = _read("app.js")
        self.assertNotIn("function buildMood(", js)
        m = re.search(r"function renderHome\(host\) \{(.*?)\n  \}\n", js, re.S)
        body = m.group(1)
        self.assertEqual(len(re.findall(r"\bboard\(", body)), 0)
        for bad in ("buildMood", "scene-btn", "dir-card", "S.daily", "shareDate", "daily-time", "W['W-257']", "openRail("):
            self.assertNotIn(bad, body)
        self.assertNotRegex(body, "てくちゃん|きろちゃん|ことちゃん|まなちゃん")

    def test_send_never_carries_the_daily_values(self):
        js = _read("app.js")
        m = re.search(r"async function sendTier\(name\) \{(.*?)\n  /\* =====", js, re.S)
        body = m.group(1)
        self.assertIn("share_daily", body)
        self.assertIn("daily_date", body)
        for bad in ("bed_time", "wake_time", "breakfast", "S.daily.bed", "S.daily.wake", "S.daily.bf"):
            self.assertNotIn(bad, body)
        self.assertIn("if (shareActive())", body)
        self.assertIn("typeof r.question === 'string' && r.question.trim() !== ''", body)
        self.assertIn("pr.run === runAtSend", body)

    def test_nothing_is_stored_on_the_device(self):
        js = _read("app.js")
        for name in ("shareDate", "S.practice", "S.daily", "runSeq"):
            for m in re.finditer(r"lsSet\([^\n]*", js):
                self.assertNotIn(name, m.group(0))
        self.assertNotIn("sessionStorage", js)
        self.assertNotRegex(js, r"question_count")

    def test_reached_state_is_enforced_in_send(self):
        js = _read("app.js")
        self.assertIn("if (name === 'renshu' && S.practice && S.practice.reached) { return; }", js)
        self.assertIn("ta.hidden = done; send.hidden = done; again.hidden = !done;", js)
        self.assertIn("if (S.practice && S.practice.reached) { cont.disabled = true; }", js)

    def test_cond_is_not_touched_by_the_start_button(self):
        js = _read("app.js")
        m = re.search(r"function startRun\(direction, limit\) \{(.*?)\n  \}\n", js, re.S)
        self.assertNotIn("S.cond", m.group(1))
        # v0.12: buildMood は 無くなった（ホームの 釦ごと）。ホームの 描画が 条件に 触らない ことを 代わりに 見る
        m = re.search(r"function renderHome\(host\) \{(.*?)\n  \}\n", js, re.S)
        self.assertNotIn("S.cond", m.group(1))
        self.assertNotIn("DEFAULT_COND", m.group(1))

    def test_readme_mentions_daily(self):
        with open(os.path.join(APP_ROOT, "README_run.md"), "rb") as f:
            self.assertIn("daily/", f.read().decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
