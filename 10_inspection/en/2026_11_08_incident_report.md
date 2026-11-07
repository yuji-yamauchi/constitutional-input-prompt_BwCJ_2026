# Incident report

- Period: **2026-11-02 (kick-off, 12:00) to 2026-11-08 01:0x JST**
- Incidents recorded: **15**

> **Why this report exists.**
>
> This container is an attempt to fix one thing: **decisions being made about a
> person on the strength of records that person did not write.**
> So **the record of the side that built it does not get erased by that side
> either.**
>
> Failures are kept as versions, who found each one is written down, and a
> correction is issued as something new rather than written over the old.
> **Zero failures is another name for not having recorded them.**

---

## 0. The numbers

| | Measured | How it was counted |
|---|---|---|
| Letters between seats (2026-11-02–2026-11-08) | **135** | Letter files placed during the period |
| Letters whose failure field holds **a real declaration** | **15** | The same letters parsed mechanically, counting those whose failure field is not "none" |
| Letters that have a failure field at all (including "none") | **78** | |
| Incidents recorded here | **15** | Taken from the failure fields, the bodies of the daily reports, and the primary record of the conversations |

That **63 letters say "none"** is also part of the record.
**Because there is a field for it, "none" gets written when there is none.**

---

## 1. Sorted by cause, there are only three kinds

Sorted by cause, **the same kinds repeat.**

| Kind | Count | What it is |
|---|---|---|
| **A. Wrote it without checking** | **8** | Did not go to the original text, the actual artefact, or the clock — asserted from memory or from another seat's wording |
| **B. Skipped a step in the order** | **4** | Skipped the check before placing, the notice on starting, the pull, or an acceptance condition |
| **C. A wrong assumption about a tool** | **3** | Line endings, time zone, character encoding, a hard-coded date — the environment was not what was assumed |

**A is half of them.** And A has **the same shape as the problem this container
addresses** — asserting something about a person (or about a fact) from the
fragments at hand, without checking.

---

## 2. A. Wrote it without checking (8)

### A-1 A letter was never in the record, so a request never arrived

- **Occurred 2026-11-06 19:01, discovered 2026-11-07 14:2x — 19 hours**
- The design seat placed a request to the implementation seat: compare the 7
  statutory articles character by character against the original text and return by
  2026-11-07 12:00.
  **It existed on disk only. It was not in the record (git), nor on the remote.**
- **Measured** — the command that asks whether a file is in the record answered that
  it is not; counting it on the remote gave **0**
- **Consequence** — **the implementation seat never received the request. The
  deadline passed without it ever arriving.**
- **Cause** — the night before, the gate seat **counted "5 unrecorded letters are
  present" and then neither read nor sent them**
- **Fix** — the gate seat took the comparison over and did it (the result at that time:
  5 exact, 2 differing by one character; for the current result see
  [the inspection report](2026_11_08_inspection_report.md) §3), and left the declaration
  in the same record
- **What changes** — **the moment an unrecorded letter is counted, record and send
  it, on the spot.** Reading can come later.
  **"Counted" is not "delivered."**

### A-2 Wrote "it stopped" without checking

- **2026-11-07 16:2x (wrong) → 16:5x (corrected) — 30 minutes**
- Wrote of the research seat that its allowance had expired, therefore it had
  stopped, and that for some days nobody had been picking up the organisers'
  answers, therefore there was a gap.
- **Actually** — that seat was working (it had placed and sent a 270-line document
  the same day). And **that seat had itself verified** that there were no new
  answers from the organisers — so **there was nothing to pick up**, not a failure to
  pick it up.
- **Cause** — **a plan (the allowance will expire) was written as a result (it
  stopped).** One pull of the record before writing would have prevented it.
- **What changes** — **before writing that another seat has stopped, pull the record
  and list that seat's directory newest-first.**

### A-3 Got wrong who sets the mark on a statute

- **2026-11-07 14:5x and 20:09 → 21:33 (corrected)**
- Wrote that after the author gives the go-ahead, **the design seat** sets the mark
  to `true`.
- **Actually** — the statute directory's own documentation says, verbatim:
  **the person who sets it to `true` is the author.**
- **Cause** — **did not open the original; inferred it from another seat's wording.**
- **Found by** — **the implementation seat**, which read the documentation itself and
  issued a correction. The gate seat then read the same original and confirmed.
- **Worth noting** — **two seats made the same error, independently.**
- **What changes** — **when writing who does what, open the original of that rule
  first.**

### A-4 Wrote on the assumption that the video explains the statutes

- **2026-11-06 19:01 (a prediction) → 2026-11-07 22:0x (the author pointed it out)**
- The prediction was: if the statutory marks are not set, **the recording will have a
  hole**; set three of them first and the recording holds. The gate seat then
  **carried that prediction forward as fact, repeatedly.**
- **Actually** — **the video contains no explanation of any statute.** (The gate seat
  pulled **22 frames** out of the video and found none in what it looked at; the
  author said so directly.)
- **Cause** — **the previous day's prediction was carried as fact without being put
  against the artefact.**
- **What changes** — **when carrying another seat's wording, write "this seat has not
  checked it" on the same line.**

### A-5 Wrote "0 hits" before looking at the scan

- **2026-11-06 10:2x — corrected by the same seat within 10 minutes**
- A report on placing 60 questions × 3 versions = 180 files said "scan: 0 hits."
  **There was in fact 1.**
- **Found by** — the seat that wrote it, on running the scan
- **What changes** — **write the body of a report first and fill the numbers in
  last.** (The same kind recurred the next day anyway — see A-6)

### A-6 Claimed absence while the search was narrow

- **2026-11-07 13:3x**
- Wrote that a certain total does not appear in a document. **It did.**
- **Cause** — **the search term was narrow** (one phrasing was searched, another was
  not)
- **Found by** — the author, by putting it to a model from another maker
- **What changes** — **"there is none" is a claim of exhaustiveness. What can be
  written is "not within what was searched"** — plus **what was searched with, on the
  same line.**

### A-7 Misread a figure

- **2026-11-07**
- In a government figure, **the line showing a per-person value and the bars showing
  a total were swapped** (the note would have made it clear)
- **Found by** — a model from another maker. The seat accepted it and corrected
- **What changes** — **a value read off a figure does not count as primary
  verification on the strength of having looked at it.**

### A-8 Measuring the working copy instead of the repository being submitted

- **Written on the night of 2026-11-07, discovered 2026-11-08 02:1x — about four hours**
- The gate seat took its measurements from **the copy in the implementation workspace**
  and wrote them up as being about **the repository being submitted.** Two separate
  things were wrong at once, from the one cause.
  1. **The marks on the 7 statutory articles** — written up as "all 7 carry the mark."
     **In the repository being submitted, none of the 7 did** — meaning no statute
     would have reached the screen at all
  2. **The 60 questions** — the README said "real; they run from a file."
     **The repository being submitted contained no implementation of them at all**
     (the matching files were counted: zero)
- **Cause** — **a number measured in one copy was written up as being about the other.**
  This is type A exactly. Both things had genuinely been reported that way;
  **what was missing was putting that report against the artefact being submitted.**
- **Found by** — the gate seat, after the author said to go and read the implementation
  seat's diary, which led to comparing the two copies file by file
- **Fix** — 29 files were transferred into the repository being submitted and every file
  compared afterwards to confirm they agree. The statutes were **re-measured on the side
  being submitted**, and that result is in the
  [inspection report](2026_11_08_inspection_report.md)
- **What changes** — **when writing the state of the artefact, measure the artefact.**
  Where two copies exist, **write which one the number came from, on the same line.**

---

## 3. B. Skipped a step in the order (4)

### B-1 Ran without announcing the start, and the work was done twice

- **2026-11-06 16:1x–18:5x — two and a half hours**
- The author asked the design seat for primary verification of some numbers. The
  design seat **ran without announcing that it had started.** Two and a half hours
  later the gate seat asked the implementation seat for **the same five items.** The
  implementation seat answered too — **the same work, twice.**
- **Cause** — a task placed in conversation **is invisible to other seats until it
  becomes a letter.**
- **What changes** — design seat: **place a one-line letter on starting** (not only a
  letter on finishing). Gate seat: **before issuing a request, count the day's
  letters from seats other than the addressee too.**
- **Worth noting** — the gate seat has **broken this "count the inbox" rule before.
  This is a recurrence.**

### B-2 Skipped the pull before placing

- 2026-11-05. Result: a 475-line design became something to be set aside (the author ruled
  that it be kept rather than discarded)

### B-3 Ran before the scope was closed

- 2026-11-06. Work was launched before the scope of embedding the artwork was settled; the
  author stopped it; it was rolled back and run again (one run wasted)
- **What changes** — close what goes in, as an explicit choice, before launching

### B-4 The acceptance criteria left out a check on character encoding

- 2026-11-07. The mangled characters the inspecting leg found had been introduced by the
  implementing leg's write
- **What changes** — add **0 control characters** to the implementation's acceptance
  criteria

---

## 4. C. A wrong assumption about a tool (3)

### C-1 A test pinned a date to "today's characters"

- **Written 2026-11-06 → failed on 2026-11-07 only → fixed the same day**
- A test **hard-coded a date** as "a different day," while the other day resolved as
  "today."
  **The moment it became 2026-11-07, both were the same day, and it failed.**
- **Cause** — **a test with a pinned date fails when that date arrives.**
  The pinned dates had been cleaned up the previous day, but **one line was missed.**
- **Fix** — the hard-coded value became a variable. **0 FAIL now.**

### C-2 Line endings (LF and CRLF)

- 2026-11-06–2026-11-07. After the record converted line endings, the tests failed in the
  terminal
- **Fix** — made the container tolerant of line endings, plus a setting on the record
  side (`.gitattributes`)

### C-3 Time zone (recorded in UTC)

- 2026-11-02. The cloud default was UTC, so the record's timestamps came out at **+0000**
  — **the order looked reversed**
- **Fix** — the time zone is stated explicitly from then on.
  **The past records are not corrected** (rewriting history is irreversible, and not
  something to do alone)

---

## 5. Operations that were stopped

Not incidents, but recorded.

| Date | What |
|---|---|
| 2026-11-02 | An attempt to create the submission location automatically was **stopped by permissions.** Self-declared as "an operation that could have counted as acting alone" |
| 2026-11-07 | A push to the public side was **refused twice** by the environment's automatic classification. **No workaround was attempted; permission was requested from the author** |

**An operation that was stopped is written down as having been stopped.** That is
part of the record too.

---

## 6. What this shows

1. **Half were "wrote it without checking."** **Skipping a step** is more common than
   a tool going wrong
2. **The same kind repeats across seats.** In A-3 two seats made **the same error,
   independently**
3. **Many failures were found by someone else.** Models from other makers found 2,
   the author found 2, another seat found 2.
   → **Checking only within one model family means arriving at the same mistake
   together, with confidence.**
4. **Every correction is still there.** Not one correction was written over the
   original
5. **The time to fix varies widely** — ten minutes to nineteen hours. **The fast ones
   are those noticed by the seat itself**; the slow one is the case where
   **nobody noticed that something had not arrived.**

---

## 7. The scope of this report

- **Subject** — the 135 letters between seats during the period, plus the bodies of
  the daily reports, plus the primary record of the conversations
- **Items** — what happened, when, the cause, who found it, the fix, what changes
- **Pass criterion** — none; this is a report, not a check
- **Known to be out of scope**
  1. **A failure that was never written into a letter does not appear here.** The
     mechanism is "there is a field, so it gets written" — **so what is not written
     does not survive**
  2. **Another seat's declaration is, to the seat writing this, a secondary
     agreement** (the original is that seat's own letter)
  3. **Our own failures are written by ourselves.** No other seat inspected this
  4. "Two and a half hours," "nineteen hours" and the like are computed from the
     letters' timestamps; **they are not measured to the second**

---

Last updated: 2026-11-08
