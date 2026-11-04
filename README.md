# Constitutional Input Prompt

**自己の意思表出としてのプロンプトを。誰もが立てる場所を、ここに。**

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

> ⚠️ Judges: this section is the entry point. It will be filled before submission.

```
# TBD
```

- Requirements: _TBD_
- Setup: _TBD_
- Try it: _TBD_

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

---

## Data

- All demonstration material is **self-made**. The certificates, report cards and
  plans shown in the demo were written for this submission; the people in them are
  invented.
- **No personal information is included in this repository.**
- No real service-user record is used anywhere in this project.

---

## License

Two tracks, and they are different:

- **Source code — MIT.** See [LICENSE](LICENSE). Copyright (c) 2026 yuji-yamauchi.
- **Images, logos, illustrations, the project name and other brand assets — All
  rights reserved.** Not reusable without permission.

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

- **テーマ**: 1「あなたにしかない深さを。」
- **動かし方**: 上の "How to run it" を参照（提出前に記入）
- **データ**: デモ素材はすべて自作です。**個人情報は含みません。** 実在の利用者の記録は使っていません。
- **ライセンス**: コードは MIT／画像・ロゴ・名称などは再利用不可
