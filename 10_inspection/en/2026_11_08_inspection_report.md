# Inspection report

- Subject: the submission — the container `app_src/` and the documents in this
  repository
- Measured at: **2026-11-08 01:0x–01:2x JST.** Every number is a measurement taken
  then

> **How this report is built.**
>
> "Everything passed" is not a report.
> A report says **what was looked at, and what was not.**
>
> So every section carries a **declaration of its own scope**: subject, items, pass
> criterion, and **what is known to be out of scope**.

---

## 0. The result

| Check | Result |
|---|---|
| The container's tests (371) | **369 PASS / 0 FAIL / 2 SKIP** |
| The container's gates (3) | **0 hits** (keys and URLs / words kept off the screen / outbound traffic) |
| 7 statutory articles vs. the original text | **5 exact / 2 differ by one character** (the body text matches exactly in both) |
| The gate over this repository's documents (65) | **165 relative links, 0 unreachable.** **Three categories left ringing** (§4) |
| The research index (112 topics) | **0 duplicates / 0 unassigned / 0 names that do not exist** |

**Every check had its negative control run first.** That a failing input actually
fails is established before any PASS is used as evidence.

---

## 1. The container's tests — 371

### Breakdown (N = negative control, T = the real thing)

| Tests | N (negative control) | T (real) |
|---|---|---|
| The receiving side's API | 43 | 19 |
| The hand-over contract | 23 | 15 |
| The container's API | 20 | 24 |
| Handing over | 18 | 8 |
| Writing practice | 16 | 12 |
| Statements and statutes | 16 | 12 |
| The container's storage | 16 | 19 |
| Version 0.3.3 | 15 | 15 (1 SKIP) |
| Version 0.3 | 14 | 25 (1 SKIP) |
| The words on screen | 9 | 11 |
| Network | 5 | 14 |
| **Total** | **195** | **176** |

**How this was counted:** each line of the test run output, split by the class-name
prefix (`N_` / `T_`), at 01:0x.

### This is the point — there are more negative controls than real tests

> **195 of them check that a broken input actually fails.**

Establishing that the checks *fail* matters more than establishing that they pass.
It is how **a PASS over an empty set ("0 hits" with 0 files examined) is kept out of
the record.**

For example, the 23 negative controls on the hand-over contract feed it inputs that
break the contract:

- does the fingerprint change when one character changes
- is a forged fingerprint rejected
- is a missing original fingerprint rejected
- is a mislabelled copy rejected
- is a note rejected when its writer is not the person
- is a mismatched count rejected

### The 2 SKIPs (with their reason)

| | Why |
|---|---|
| The file-permission test (0600 / 0700) | **Permission bits are POSIX-only** — not examined in this environment (Windows) |
| The daily-record file-permission test | The same |

**SKIPs are not counted as PASSes.** On POSIX this should read 371/371, but
**the measurement in this report was taken on Windows.**

### Scope of this section

- **Subject** — 11 test files, 371 tests
- **Items** — the container's behaviour: storage, contract, hand-over, practice,
  statutes, the words on screen, network, permissions
- **Pass criterion** — 0 FAIL. A SKIP is allowed when its reason is written down
- **Known to be out of scope**
  1. **File permissions are not examined in this environment**
  2. **The appearance of the screen** (breakage, colour, placement) is not checked
     mechanically
  3. **Behaviour on real hardware in production** has not been observed (local only)
  4. **The seat that wrote the tests and the seat that wrote the container are in
     some cases the same** — a closed loop. §5 covers this

---

## 2. The container's gates — 3 (each with a negative control)

| Gate | What it looks for | Subject | Result |
|---|---|---|---|
| Key scan | Key shapes, identifier shapes, outbound URLs, mail shapes | **80 files** | **0 hits** |
| Word scan | Words kept off the screen (points, ranking, improvement, and others) | **23 files** | **0 hits** |
| Network scan | Imports that reach outward | **32 files** | **0 hits** |

**All three had their negative controls run first.** The network scan, for instance,
confirms both that it fires on an outbound import and that it does **not** fire on a
confusable import that does not reach outward (measured: it does not).

### The network gate is the most important guarantee in this container

> **The container listens on `127.0.0.1` only, and refuses a request that arrives
> under any other name.**
> Claude's API is called from **one place only — the listener** — and
> **the receiving side never calls Claude.**

Both the tests and the gate watch this (19 network tests plus the gate).

---

## 3. The 7 statutory articles vs. the original text

- **Retrieval** — the **XML as served**, from the national statute API.
  **No summary and no screen-reading were used** (a summary cannot be used for a
  character-by-character comparison)
- **Method of comparison** — **exact match** of the strings with all whitespace and
  line breaks removed from both sides
- **Result** — **5 exact / 2 differ by one character**
- **What the one-character difference is** — one copy **omits the item number**;
  the other **includes the paragraph number**. In other words, **whether the number
  is included is not consistent across the 7.**
  **The body text matches exactly in both**, so neither differs from the original
  (a number is part of the article's structure, not of its body)

The per-article character counts and verdicts are in
[`08_sources/`](../../08_sources/).

### The state of the marks

> **All 7 carry `verified_by_person: true`.** The author read each copy against the
> original text and set the mark.
> Confirmed from the record's diff: **only the mark lines changed. Not one character
> of the articles moved.**

### Scope of this section

- **The date a statute came into force was not retrieved** (the API does not return
  it) — whether a text is current rests on **what the API serves**
- Whether the statute itself has since been amended has to be tracked separately
- **This comparison is preparation.** The mark is set when the author reads the copy
  against the original; **a mechanical comparison is not a substitute for that.**

---

## 4. The gate over this repository's documents — 65

| Item | Result |
|---|---|
| Negative control | **6/6 fired as expected** |
| Relative links | **165, 0 unreachable** |
| Bidi and zero-width characters | **0** |
| Words kept off the screen | **0** |
| Place names, postcodes, dialling codes | **0** |

### Three categories left ringing (the detector is not weakened)

| Category | Hits | Result of tracing every hit |
|---|---|---|
| The internal emphasis mark | **4,138 across 16 files** | **All 16 are inside `01_vision/`** (12 original theory documents plus 4 guide files). **0 outside `01_vision/`** (verified mechanically). The originals are published with a stated declaration that they are untouched, and the guide says in as many words: "this mark is an emphasis mark used internally" |
| Names of internal working locations | **31 across 9 files** | All inside `01_vision/rinen/`. The guide already declares: **"the folder and file names point at places that are not public. They cannot be followed."** Traced verbatim, each reference turns out to be **a line stating that the content itself is not written here** |
| Strings shaped like health figures | **6 across 5 files** | **All six are false positives.** Traced verbatim: four on the side of the original theory documents (one date notation, two ruling numbers, one chapter number), and **two instances of this report's own "371 / 371"**. **Not one is a figure such as a blood pressure** |

**The detector has not been weakened.** It is left ringing, with the reason for
leaving it recorded.

### Scope of this section

- **Subject** — the **65** tracked `.md` files outside `app_src/`
- **Items** — the five in the table above, plus whether relative links resolve
- **Pass criterion** — 0 hits in newly placed documents; every pre-existing hit
  traced to source with the reason recorded
- **Known to be out of scope**
  1. **Whether the translation carries the meaning** is not checked mechanically
  2. **Text inside figures and images** is not reached by the scanner
  3. **The category covering certain proper nouns cannot be tested from this seat**
     (the list needed to match against is held on the non-public side) — so
     **that category's "0" carries no meaning**

---

## 5. Who inspected what

> **The seat that made a thing does not run the final inspection on it.**

| The thing | Made by | Inspected by |
|---|---|---|
| Each version of the container | The design seat, then an implementation leg | **A different leg** |
| The screen revisions | The implementation seat (spec, build and inspection on separate legs) | The gate seat (the gate and the transfer) |
| The statutory copies | Copied by the author | **The gate seat, compared mechanically with the original text** (not the side that made them) |
| The documents in this repository | The gate seat | **This is the one closed loop** (below) |
| The numbers in the script | The implementation seat | **Two models from other makers**, plus the author |

### The largest hole in this report

- **The documents in this repository were written by the gate seat and inspected by
  the gate seat.** No other seat went over them
- **This report itself was written by the gate seat**
- **The rule "do not run the final inspection on your own work" is not being kept
  here.** The constraint is time

---

## 6. The scope of this report

- **Subject** — the container `app_src/` (82 tracked files, 15,392 lines); 65
  documents in this repository; 7 statutory articles; the 112-topic research index
- **Items** — §1 through §5
- **Pass criterion** — as written in each section
- **Known to be out of scope**
  1. **File permissions** (POSIX-only; SKIP in this environment)
  2. **The appearance of the screen** (breakage, colour, placement, legibility)
  3. **Real hardware and production** (local only)
  4. **Whether the translation carries the meaning**
  5. **Text inside figures and images**
  6. **The date a statute came into force**
  7. **The inspection of the documents is a closed loop** (§5)
  8. **One proper-noun category cannot be tested from this seat** (§4)
- **Time of measurement** — 2026-11-08 01:0x–01:2x. **The container can still change
  up to the moment of submission**, so **these numbers need re-measuring right
  before it.**

---

Last updated: 2026-11-08
