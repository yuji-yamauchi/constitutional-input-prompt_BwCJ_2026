# Specification of the deliverable

- Deliverable: **Constitutional Input Prompt** (a capability-support app)
- Measured at: **2026-11-08 01:0x JST**
- Every number here is a measurement taken at that moment. The counting method is
  written on the same line as the number.

---

## 0. What this is

> **One application, which only the person themselves can open.**

It does three things, and beyond those there is one opening: a way to hand
something to another person.

| | What it does | The point |
|---|---|---|
| **1** | **Practice at writing** | The person writes in their own words. The conditions of writing — how much at a time, where it breaks, how plain the language is, how it is entered — are **chosen by the person**. Claude asks a question and **reads the person's own sentences back without changing a character**. It does not rewrite, summarise, score, or advise |
| **2** | **A drawer for one's own records** | The person photographs records that others wrote about them (certificates, plans, report cards). **The photograph stays as the original**, and the text read out of it is labelled **a copy**. Who wrote it, when, and under what procedure travels with it, and the person can attach **notes and objections as separate lines**. **The original does not change** |
| **3** | **Sorting out what is difficult now** | In the person's own words. Statutory provisions are offered **only from a closed set copied in advance from the original text**, with the source attached. **Whether a provision applies to this person is something the application does not say** |
| **＋** | **Handing something over** | A **copy** leaves only when the person selects it and presses the hand-over. The receiving side returns **a receipt**, and the receipt stays in the person's own hands |

**This application does not judge the person.** It produces no points, no ranking,
no stages, no assessment of condition.
**What is counted is the conditions the person chose, not the person.**

---

## 1. Size (measured)

| | Measured | How it was counted |
|---|---|---|
| Tracked files | **82** | `git ls-files app_src`, with `__pycache__` removed |
| Lines | **15,392** | Sum of lines across the `.py` `.js` `.css` `.html` `.txt` `.json` `.md` files in that list |
| Tests | **371** | Lines in the test run output, of which **195 are negative controls** |
| Dependencies | **Python 3.10 or later, and nothing else** | No `pip install`, no build step, no network call at startup |

---

## 2. Structure

```
app_src/
├ vault_app/      the person's own container (25 files)
│  ├ main.py appctx.py auth.py storage.py handoff.py law.py claude_client.py
│  ├ routes_auth.py routes_records.py routes_practice.py routes_statement.py
│  │  routes_handoff.py routes_daily.py
│  ├ prompts/     arranger.txt / listener.txt / reader.txt   <- one file per role
│  └ static/      index.html app.js app.css brand.css boards.css mobile.css mood.css
├ receiver_app/   the receiving side (8 files; never calls Claude)
│  └ main.py routes_api.py routes_face.py storage.py index.html port.css port.js
├ law_corpus/     statutes (one article = one JSON; 7 articles plus a sample)
├ common/         contract.py httpkit.py ids.py vector.py words.py
├ demo/           demo material (all self-made; the people are invented)
├ tools/          scan_leaks / scan_words / scan_network / record_demo / unpack_demo
└ tests/          11 test files, 371 tests
```

### One file per role, for the instructions given to Claude

| File | Role | Lines |
|---|---|---|
| `listener.txt` | **The listener** — asks a question, nothing more. Does not rewrite | 26 |
| `reader.txt` | **The reader** — reads text out of a photograph | 14 |
| `arranger.txt` | **The arranger** — lays out what the person wants now | 21 |

**The full text of the instruction appears on screen.**

> "This is the complete instruction being given to the listener.
> Nothing else is running behind your back."

---

## 3. The shape of the data

### The person's container

- Opened with the person's own passphrase (the `VAULT_PASSPHRASE` environment
  variable). **There is no settings field on screen**
- The original (the photograph) and the text read out of it (the copy) are **held
  as separate things**
- Each record carries a **`sha256` fingerprint**: **change one character and the
  fingerprint changes**
- Notes and objections are added **as separate lines**. **The original does not
  change**
- The daily record holds: went to bed, woke, breakfast, how today felt

### The contract when something is handed over

- **Only the copy leaves. The original does not**
- The bundle carries **the count, the fingerprints, and the label saying who wrote
  each item**
- The receiving side returns **a receipt**, and **the receipt stays with the person**
- **The receiving side never calls Claude** (checked by both the tests and a gate)

### The statutes

- **One article = one JSON file.** Fields: `id`, `law_name`, `article`,
  `text_verbatim`, `source_name`, `retrieved_on`, `retrieved_by`, `set_version`,
  `verified_by_person`, `note`
- **Only articles whose `verified_by_person` is `true`** reach the screen
- **The person who sets it to `true` is the author** — a human reads the copy
  against the original text. Files with a missing field, files that will not parse,
  files whose name starts with `_`, and files with a duplicate `id` are **not read**
- Currently **all 7 are `true`**. The result of comparing them with the original
  text is in [`08_sources/`](../../08_sources/)

---

## 4. The guarantee that nothing goes out

| | |
|---|---|
| Listening | **`127.0.0.1` only.** A request arriving under a different name is **refused** |
| Outbound traffic | **One place only** — the listener (Claude's API). **The receiving side never calls it** |
| Tests | **19** network tests, plus a gate (scanned 32 files, 0 hits) |
| Keys | Environment variables only. **No value exists in the code or in the repository** (the gate scanned 80 files, 0 hits) |
| Personal information | **0 in the repository.** All demo material is self-made, and **the people in it are invented** |

The results of the checks, and what they do not cover, are in
[`10_inspection/`](../../10_inspection/).

---

## 5. Running it

See "How to run it" in the repository [README](../../README.md). Two entry points
(the receiving side, and the person's container) are started in separate terminals.

---

## 6. What was deliberately not built

> **A demo that looks like a different product is worse than a small one.**

| | This time |
|---|---|
| The person's screens (writing, the daily entry, marks, handing over) | **Real. They work** |
| The 60 questions | **Real. They run from a file. No database is used** |
| The replies in conversation | **Prepared in advance.** **The screen says so.** The design connects to Claude through the API |
| **AI analysing the person's past records** | **Absent. Deliberately.** (Having one's own past read back by an AI with no one else present — that is the one thing this design refuses) |
| Storing photographs of records; handing a development history to a supporter | **Mock-ups only.** The security design is not finished, so **nothing real is stored** |
| The connection to the provider side (an API) | **Planned.** The first intended use is connecting to the author's own welfare-services application, in real operation. **Written as a plan, and left as one** |

The whole picture is **nine cells** (down: past, present, future / across: the
person alone, the person with AI, the person with AI and a supporter).
**What was built this time is one cell — present × the person alone** — and its
receiving side.
**The cell "past × the person with AI" is one we have decided will not exist.**

---

## 6-2. Measuring happens only when three are present

| Who is present | What can happen |
|---|---|
| **The person alone** | **Recording only. No measuring.** |
| **The person and AI** | **Recording only. No measuring.** |
| **The person, AI, and a supporter** | **Only if the person has decided so**, past records may be used to look at **change**, and at how fast it is going |

### Mapped onto the nine cells

| Cells | Treatment |
|---|---|
| The three "person alone" cells | **Recording only.** The change view does not open |
| The three "person with AI" cells | **Recording only.** The change view does not open |
| The three "person with AI and supporter" cells | The change view opens **only where the person has decided it should** |

### What this means for the implementation

1. Even where the questions end up revealing vocabulary or reading, **that value is
   never handed back to the person.** It is used only to decide **how the AI speaks**
2. **The change view opens only in the cells where a supporter is present.** Without
   one it does not open. This is **a lock, not an absolution**
3. Even when change is shown, **no points, no ranking, no stages, no comparison with
   last time, and no language of improvement reach the screen**
4. **The person's decision comes first.** Neither the container nor the supporter
   opens it from their side
5. In public writing the word "growth" is avoided; it is **change**, and **how fast
   it is going**

### Why it is divided this way

The same number becomes a mirror if it is **a judgement handed back to the person**,
and a self-portrait if it is **material the person uses to draw themselves**. The
dividing line is not the instrument. It is **how it is handed back, and who is
present when it is**.

When it closes around just the person and an AI, **an interpretation returns to the
person with no one there to disagree with.** With a person in between, the
interpretation arrives in a room where someone can say **"that is wrong."**

So this is not a setting that switches measuring on and off. **It is decided by who
is in the room.**

---

## 7. How Claude was used

### While building

**Claude Code was the centre of the work.** It was split into seats (separate
sessions) which connect through **exactly one thing: a letter on disk.**

| Seat | Role |
|---|---|
| vsclaude | Routing, and **the gate to anything public** (the submission passes through here) |
| hacka | Implementation and research |
| fable | Design (specification, implementation and inspection on separate legs) |
| vision | Checking from the side of the principles |
| bclaude | External research (rules, statutes, prior work) |
| rules | The rulebook for the contest |
| (seats that are not Claude) | The same question, given to a model from another maker |

**The seat that made a thing does not run the final inspection on it.**

### Inside the container

Claude is used for **exactly three things**.

1. Asking a question, and reading the person's sentences back **without changing a
   character**
2. Reading text out of a photograph
3. Offering candidate provisions **from the closed set only**

**Deliberately not used:** the reply from the receiving side (a human writes it),
the marks and their counts (the person marks; the container counts), confirming who
wrote a record, **applying a provision to a person**, and **judging a person's
state**.

---

## 8. The scope of this document

- **Subject** — `app_src/` (82 tracked files) and the documents in the submitted
  repository
- **Pass criterion** — none. This is a specification, not a check. The checks are in
  [`10_inspection/`](../../10_inspection/)
- **Known to be out of scope**
  1. **The container can still change up to the moment of submission.** The numbers
     here were measured at 2026-11-08 01:0x
  2. Behaviour on real hardware, in a production environment, has not been observed
  3. The appearance of the screen has not been checked mechanically
  4. **This document was written by one party and inspected by the same party.** No
     other seat has gone over it

---

Last updated: 2026-11-08
