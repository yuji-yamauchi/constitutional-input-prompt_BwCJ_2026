# Constitutional Input Prompt

**自己の意思表出としてのプロンプトを。誰もが立てる場所を、ここに。**

**A capability-support app.** It does not measure capability — nobody can; what is
observable is only what was achieved. What it does is widen the room a person has
to form an intention of their own, and keep them the author of it.

**ケイパビリティサポートアプリ**です。ケイパビリティ（＝選べたことの広がり）を
**測る**道具ではありません。測れるのは達成の方だけです。この器がするのは、
**本人が自分の意思をかたちづくる場を広げ、その著者であり続けられるようにすること**です。

Built with Claude: Japan 2026 submission.

> **On the name.** "Constitutional" here is not a model's constitution, and this is
> not a prompting technique. It refers to the person's own: the right to remain the
> author of what gets recorded about you — secured at the moment of **input**,
> not corrected at the output.
>
> **名前について。** ここでの "Constitutional" は、モデルの憲法のことでも、プロンプトの技法のことでもありません。**本人のもの**です＝自分について記録されることの著者であり続ける権利を、出力の段階で直すのではなく、**入力の段階で守る**、という意味です。

> **Status:** in progress. Content is being added during the hackathon window (Nov 2–8, 2026 JST).

---

## What this is

An app that one person opens — and only that person. It does three things, and then
hands a **copy** to a human being.

1. **Writing practice.** You write in your own words, under conditions you choose
   (how much at a time, how it is broken up, how plain the wording is, how it is
   entered). Claude asks questions and reads your own sentences back **verbatim**.
   It does not rewrite, summarize, score or advise.
2. **A drawer for records other people wrote about you.** Certificates, plans,
   report cards, notes. The photo you take stays as **the original and is never
   altered**; the text Claude reads out of it is labelled a **copy**. Each record
   carries who wrote it, when, and under which procedure — and you can attach your
   own note or objection beside it. The original does not change.
3. **Putting today's difficulty in order,** in your own words, with statutory text
   quoted from a **closed set** of source texts. Whether a provision applies to you
   is **not** something this app says. A person decides that.

What comes out is a statement in your own words. You choose what to attach, you
press **hand over**, and a copy leaves the app. The receiving side returns a
**receipt**, and the receipt stays with you.

**This app does not judge you.** It records no score, no rank, no level, no
assessment of your condition. What it counts is the **conditions** you chose — not
you.

---

## Theme

**Theme 1 — あなたにしかない深さを。 (The depth only you have.)**

Built from more than ten years inside employment-support practice in Japan: the
missing thing is that the person themselves does not hold the records written
about them.

---

## Who keeps using it after this week

This is not a demo looking for users afterwards. Two groups are already there.

- **The people at the employment-support service the author's company runs.**
  They are first. Every one of them has records written about them by other
  people — certificates, individual support plans, school reports — and almost
  none of them hold those records themselves, in a form they can read.
- **High-school and university students putting together a local community
  magazine.** No disability involved. They gather material about themselves and
  their town, keep the original untouched, decide what to hand to an editor, and
  keep the receipt. The mechanism is the same one.

The second group is the point. What this is for is **not collecting information
about disability. It is being able to hold and control your own information.**
That is what gives a person somewhere to stand when something goes wrong.

---

## How to run it

**Python 3.10 or newer. Nothing else.** No `pip install`, no build step, no network
at startup. Two small servers run locally and listen on `127.0.0.1` only; a request
whose `Host` is not a local name is refused.

Run every command from the top of this repository.

```bash
# 1. the receiving side (a person reads and replies here; Claude is never called)
python3 -m app_src.receiver_app.main          # http://127.0.0.1:8766/

# 2. the tool itself (a different terminal)
python3 -m app_src.vault_app.main             # http://127.0.0.1:8765/
```

Both ask for a passphrase, set through environment variables:

```bash
export VAULT_PASSPHRASE="your passphrase"     # the person's entrance
export PORT_PASSPHRASE="16+ characters"       # the receiving side
export ANTHROPIC_API_KEY="your key"           # optional — see below
```

On Windows use `$env:NAME = "..."` (PowerShell) or `set NAME=...` (Command Prompt).

**Without a key it still works.** Set `CIP_DEMO_MODE=1` and the tool answers from
recorded responses instead of calling Claude. A banner stays on screen the whole
time saying so — the screen never claims a recorded answer is a live one.

**Connecting the two:** on the receiving side press *issue a connecting phrase*
(single use, 24 hours), then enter it in the tool under *hand to a person*. After
that, copies the person hands over arrive on the receiving side, and a reply comes
back only when the person presses *check for replies*.

```bash
python3 -m app_src.tools.unpack_demo          # writes the dummy documents as PNG
python3 -B -m app_src.tests.run_all           # the tests: negatives first, then the rest
```

`app_src/README_run.md` lists every environment variable, where files are stored,
and how to delete everything.

**The tests run the deliberately broken inputs first.** A detector that has not
been seen to fail is not evidence that anything passed.

---

## Built with Claude

How Claude was used in this project:

- **Claude Code** as the primary development environment, through a fixed order:
  design → specification → implementation → inspection by a different reader.
- Inside the app, Claude is used for exactly three things:
  - asking questions and reading the person's own sentences back verbatim (1 and 3)
  - reading text out of a photograph (2)
  - choosing candidate provisions **from the closed set only** (3)
- **Where Claude is deliberately not used:** the reply from the receiving side (a
  human writes it), the marks and their counts (the person marks; the app counts),
  confirming who wrote a record, applying a provision to a person, and judging a
  person's state — which this app does not do at all.

### Parts that were not made with Claude

So that the judging scope is unambiguous:

- **The speaking segment of the demo video** was produced with **HeyGen**, from the
  author's own photograph and the author's own recorded voice. Not made with Claude.
  The author has after-effects of a cerebral haemorrhage — no hearing in the left
  ear, and a stutter. That is the reason a separate service was used there.
- **The illustration embedded in the screen** (`app_src/vault_app/static/mood.css`)
  was drawn by a person during the event, as brand artwork. **Copyright is held by
  合同会社HOHOHO (HOHOHO LLC).** Not made with Claude.
- **Some of the fact-checking was deliberately not Claude.** Numbers and claims in
  the script, and the statutory copies, were also put to large language models from
  other makers. This was on purpose: a check run inside one model family is not an
  outside check. Those results are not Claude's output, and the final call on each
  one was the author's.

Everything else in this repository — the specifications, the implementation, the
inspection reports and this README — was produced through Claude Code.

---

## How this was checked, and what went wrong

Two reports, in [`10_inspection/`](10_inspection/):

- **The inspection report** — 371 tests on the container (195 of them negative
  controls), 3 gates, the 7 statutory articles against the original text, and 56
  documents in this repository. Every section declares its own scope, including
  **what is known to be out of scope** — among it the one closed loop we could not
  get out of: these documents were written and inspected by the same seat.
- **The incident report** — the **14 things that went wrong** while building this,
  with who found each one. Half of them were the same failure: **wrote it without
  checking.** The operations that were stopped are written down as stopped.

**Zero failures is another name for not having recorded them.** The specification of
the deliverable is in [`02_spec/`](02_spec/).

---

## What is real, and what is staged

Stated plainly, because a demo that looks like something it is not is worse than
a smaller demo.

| | In this submission |
|---|---|
| **The person's own screens** — writing, the day's row, the marks, handing over | **Real.** They run. |
| **The sixty questions** | **Real.** They run from files; no database is involved. |
| **The replies in the conversation** | **Prepared in advance.** The screen says so where they appear. The design connects to Claude through the API; that connection is not in this submission. |
| **Analysis of past records by the model** | **Not present at all.** Deliberately. Reading someone's own past back to them through a model, with no one else in the room, is the one thing this design refuses. |
| **Storing photographs of records / handing a history to a supporter** | **Mock-up only.** The security design is not finished, so nothing real is stored. |

---

## Measuring happens only when three are present

What this tool will do depends on **who is in the room.**

| Who is present | What it will do |
|---|---|
| **The person alone** | **Record only. It does not measure.** |
| **The person and Claude** | **Record only. It does not measure.** |
| **The person, Claude, and a supporter** | Only if **the person decides so**, past records (the day's mood and so on) may be used to look at **change**, and at how fast it moves |

**Why split it this way.**

The same number is a mirror when it is **returned to the person as a verdict**, and a
self-portrait when it is **material the person draws with**. What divides them is not
the instrument. It is **how it comes back, and who is there when it does.**

Close the loop with only the person and the model in it, and an interpretation comes
back to the person with **nobody there to disagree with it.** With a human in the room,
it comes back to someone who can say **"that is wrong."**

So this is not a setting that toggles measuring on and off. **It is decided by who is present.**

---

## What comes next

Written as plans, not as claims:

- **An API will be built.** The first intended use is connecting this to the
  author's own welfare-services application, in real operation.
- **The analysis feature and the storing of past records stay mock-ups** until the
  security design is done.

---

## Data

- All demonstration material is **self-made**. The certificates, report cards and
  plans shown in the demo were written for this submission; the people in them are
  invented.
- **No personal information is included in this repository.**
- No real service-user record is used anywhere in this project.
- **The background research was done outside this repository, and is not
  included.** Six months, 112 topics, 100,011 lines — and 5,829 citations that
  were never traced back to a primary source. An index of what was looked into,
  and the reason the research itself stays out, is in
  [`09_research/`](09_research/). "Looked into" and "verified" are different
  words; only the verified work sits in [`08_sources/`](08_sources/).

---

## License

Two tracks, and they are different:

- **Source code — MIT.** See [LICENSE](LICENSE). Copyright (c) 2026 yuji-yamauchi.
- **Images, logos, illustrations, the project name and other brand assets — All
  rights reserved.** Not reusable without permission. The illustrations and
  characters are the property of **合同会社HOHOHO (HOHOHO LLC)** and are used here
  with permission granted on 2026-11-02.
- **The bundled typeface** is Zen Maru Gothic, under the SIL Open Font License 1.1.
  The licence text ships with it at `app_src/vault_app/static/FONT_LICENSE_OFL.txt`.

- **Prose — CC BY-NC-ND 4.0.** This README and the writing in the numbered
  directories may be shared with attribution, but not commercially and not in
  modified form. Quoting with a citation is fine; a rewritten version standing in
  for the original is not.

---

## 日本語

**これは何か** — 本人だけが開ける一つのアプリです。働きは三つ、そしてその先に「人に渡す口」が一つあります。

1. **書く練習** — 本人が自分の言葉で書きます。書き方の条件（一度に書く量・区切り方・言葉のやさしさ・入力の形）は本人が選びます。Claude は問いを返し、本人の文を**一字も変えずに**読み返すだけです。書きかえ・要約・採点・助言はしません。
2. **自分の記録の引き出し** — 他の人が自分について書いた記録（診断書・計画・通知表など）を、本人が写真で入れます。**写真は原本のまま**で、Claude が読み取った文字は「写し」の札が付きます。記録には「誰が・いつ・どの手続きで書いたか」が添えられ、本人は注記や異議を別の行として付けられます。**原本は変わりません。**
3. **今の困りごとの整理** — 本人の言葉で並べます。法令は、あらかじめ原文から写した**閉じた集合**からだけ、出典つきで出します。**その条文が自分に当てはまるかどうかを、このアプリは言いません。** 人が考えます。

できあがるのは、本人の言葉による**意思表出文**です。本人が選び、**「わたす」**を押したときだけ、**写し**が外に出ます。受け取った側は**控え**を返し、控えは本人の手元に残ります。

**このアプリは、本人を判定しません。** 点も、順位も、段階も、状態の評価も出しません。数えるのは、本人が選んだ**条件**であって、本人ではありません。

**使い続ける人** — この一週間のあとに使う人を探す、という話ではありません。すでに二組います。**ひとつは、著者の会社が運営する就労移行支援の現場の利用者の方**。自分について他の人が書いた記録（診断書・個別支援計画・通知表）を、ほとんどの人が読める形で自分の手元に持っていません。**もうひとつは、地域の情報誌をつくる高校生・大学生**。障がいは関係ありません。自分と自分の町について材料を集め、原本はそのまま残し、編集の人に何を渡すかを自分で決め、控えを持つ——働きは同じです。

二つ目が要点です。この器が要るのは、**障がいの情報を集めるためではなく、自分の情報を自分で持てるようにするため**です。それが、困ったことが起きたときに、その人が**立つ場所**になります。

### 本物と、仮の物

小さいデモより、**違う物に見えるデモ**のほうが悪いので、先に書きます。

| | この提出物では |
|---|---|
| **本人の画面**（書く・今日の欄・印・わたす） | **本物です。** 動きます |
| **60 問の問い** | **本物です。** ファイルから動きます。データベースは使っていません |
| **会話の返事** | **あらかじめ用意した物です。** 画面にもそう出ます。設計は API で Claude につなぐ形にしてあります（今回はつないでいません） |
| **過去の記録を AI が分析すること** | **ありません。** 意図して置いていません。自分の過去を、他に誰も居ない所で、AI に読み返されること——この設計が唯一ことわっているのが、そこです |
| **記録の写真の保存／支援者へ育成歴を渡すこと** | **モックアップだけです。** セキュリティの設計が終わっていないので、本物は何も保存しません |

### 測るのは、三人そろったときだけ

この器は、**誰がその場に居るか**で、できることを変えます。

| その場に居るのは | できること |
|---|---|
| **本人だけ** | **記録だけ。測りません。** |
| **本人と AI** | **記録だけ。測りません。** |
| **本人と AI と支援者** | **本人がそう決めたときに限り**、過去の記録（きょうの気分など）を使って、**変化**や、その**速さ**を見ます |

**なぜ、こう分けるのか。**

同じ数字でも、**本人に返される判定**なら鏡になり、**本人が自分を描くための素材**なら自画像になります。
分かれ目は、道具ではありません。**返し方と、そのときに誰が居るか**です。

本人と AI の二人だけで閉じると、**解釈が、異議を言う相手のいないまま本人に返ります。**
人が間に入っていれば、解釈は「**違う**」と言える相手がいる状態で返ります。

だから「測る／測らない」を設定で切り替えるのではなく、**その場に誰が居るかで決まる**形にしています。

---

### どう検査したか、そして何が失敗したか

[`10_inspection/`](10_inspection/) に二本あります。

- **検品報告書** — 器の検査 371 本（うち**陰性対照 195 本**）・門 3 本・法令 7 条の原文との突合・
  このリポジトリの文書 56 本。**各節に射程の自己申告**つきで、**既知の射程外**も書いています。
  そこには**抜け出せなかった閉ループ**も入っています＝**これらの文書は、書いた席が自分で検査しています。**
- **インシデント報告書** — 作っているあいだに起きた**失敗 14 件**を、誰が見つけたかとともに。
  **半分が同じ失敗**＝**確かめずに書いた。** **止められた操作も、止められたと書いています。**

**失敗 0 は、記録していないことの別名です。**
納品物の仕様書は [`02_spec/`](02_spec/) にあります。

### これからの予定

**予定として書きます。できることとしては書きません。**

- **API は作ります。** まず、著者の会社が運営する**福祉事業向けのアプリ**と接続して、実運用する予定です。
- **分析の機能と、過去の記録の保存は、セキュリティの設計が終わるまでモックアップのまま**です。

### Claude で作っていない部分

審査の範囲がはっきりするように書きます。

- **デモ動画の話者の区間**は、**HeyGen** で作りました（著者本人の写真と、著者本人が読んだ録音から）。
  **Claude で作った物ではありません。**
  著者には脳出血の後遺症があり、**左耳が聴こえず、吃音があります。**
  話者の区間に別のサービスを使ったのは、そのためです。
- **画面に埋め込んだ絵**（`app_src/vault_app/static/mood.css`）は、期間中に**人が描いた**ブランドの絵で、
  **著作権は合同会社HOHOHO が所有**しています。**Claude で作った物ではありません。**
- **事実確認の一部は、わざと Claude ではありません。** 台本の数字や主張、法令の写しは、
  **ほかの作り手の大規模言語モデルにも当てました。** 意図してそうしています。
  **同じモデルの系統の中で検査しても、それは外の検査になりません。**
  その結果は Claude の出力ではなく、一つ一つを最後に判断したのは著者です。

ほかは全部——仕様書も、実装も、検品の報告も、この README も——**Claude Code を通して作りました。**

### 調べた物と、確かめた物

このアプリの背景に、**6 か月・112 テーマ・100,011 行**の調査の記録があります。
**その記録は、この repo に置いていません。**

置かない理由は一つです。調査の生の出力には、**学術引用の形が 5,829 件**あり、
その**ほとんどを一次資料に到達して確かめていない**からです。
確かめた物だけが [`08_sources/`](08_sources/) にあります。

**「調べた」と「確かめた」は、別の言葉です。**
何を調べたかの索引と、置かない理由は [`09_research/`](09_research/) にあります。

---

- **テーマ**: 1「あなたにしかない深さを。」
- **動かし方**: 上の "How to run it" を参照
- **データ**: デモ素材はすべて自作です。**個人情報は含みません。** 実在の利用者の記録は使っていません。
- **ライセンス**: コードは MIT／画像・ロゴ・名称などは再利用不可
