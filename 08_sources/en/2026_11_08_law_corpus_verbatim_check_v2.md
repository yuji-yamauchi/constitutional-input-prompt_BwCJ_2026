# The seven statutory copies, put against the original text — second edition

- Measured at: **2026-11-08 02:4x JST**
- Subject: the **7 articles** in `app_src/law_corpus/` of the repository being
  submitted (the one sample file is out of scope)
- Certainty: **primary verification** — the original text was reached and compared
  character by character

> **What the first edition got wrong.**
>
> The Japanese first edition (2026-11-07) stays where it is. Deleting it would delete
> the record of the mistake. There were two.
>
> 1. **It measured the wrong thing.** The first edition measured **the copy in the
>    implementation workspace.** In the repository being submitted, **none of the 7
>    carried the mark at that time** — and since an unmarked article does not reach the
>    screen, **no statute would have appeared at all.** On 2026-11-08 the two were
>    brought into line, and **this second edition measures the repository being
>    submitted.**
> 2. **The copy itself changed.** The first edition states that the copy of Employment
>    Promotion Act Article 36-4 **includes** the paragraph number. The author decided on
>    2026-11-07 **not to include it**, so **it no longer does.** The first edition was
>    correct at the time and is **now out of date.**
>
> This edition also **changes the method of comparison** (§2), so the shape of the
> numbers changes with it.

---

## 1. The result

| | |
|---|---|
| **Exact** | **6 articles** |
| **Exact once numbering is set aside** | **1 article** (Employment Promotion Act, Article 36-4) |
| **Differing** | **0 articles** |
| Marked as read against the original (`verified_by_person`) | **all 7 carry it** |

**Not one article's body text differs from the original.**

---

## 2. How the comparison was made

- **Retrieval** — the **XML as served** from the national statute API (HTTP 200
  confirmed). **No summary and no screen-reading were used**, because a summary cannot
  carry a character-by-character comparison
- **Method of comparison** — every character is pulled out of the original XML and
  flattened into **one string with all whitespace removed**. The copy's body text is
  flattened the same way, and the question asked is **whether it occurs in that string
  as it stands**
- **Negative control** — a string with **one character added** to the copy was put
  through the same method first. It was confirmed **not to occur** before any "it
  occurs" was used as evidence
- **The limit of this method** — where a number sits **at the front** of an article (an
  item heading, for instance), a copy that omits it still occurs in the string.
  **This method cannot tell you whether the handling of numbers is consistent across
  the 7.** The first edition's method — extracting each article and matching the whole
  string — could see that. **Each method has something it sees and something it does
  not.**

---

## 3. Article by article

| | Article | Characters | Verdict |
|---|---|---|---|
| 1 | Employment Promotion Act, Article 36-3 | 191 | **exact** |
| 2 | Employment Promotion Act, Article 36-4 | 134 | **exact once numbering is set aside** (below) |
| 3 | Act on Elimination of Discrimination, Art. 2(ii) (social barriers) | 67 | **exact** |
| 4 | Act on Elimination of Discrimination, Art. 8(1) | 70 | **exact** |
| 5 | Act on Elimination of Discrimination, Art. 8(2) (expression of intent; reasonable accommodation) | 159 | **exact** |
| 6 | Comprehensive Support Act, Article 1-2 (basic principles) | 381 | **exact** |
| 7 | Comprehensive Support Act, Art. 5(14) (definition of transition-to-employment support) | 194 | **exact** |

**How the characters were counted** — the characters of the copy's body text with all
whitespace removed.

### What number 2 means

The copy **joins paragraphs 1 and 2 into a single string and does not include the
paragraph number** (the author's decision, 2026-11-07). The original carries that
number **in the middle of the text**, so **as one continuous string there is a
difference.**

**The body text itself does not differ by a single character.** A number is part of the
article's structure, not of its body.

---

## 4. On the mark

- Setting `verified_by_person` to `true` is **the author's act.** It goes on **only when
  a person has read the copy against the original**
- **An article without the mark does not reach the screen.** The one sample file is left
  unmarked, and so **sits on the side that is never read, as its name says**
- **A mechanical comparison is not a substitute for the mark.** This document is
  **preparation**

---

## 5. The scope of this document

- **Subject** — the 7 articles in `app_src/law_corpus/` of the repository being submitted
- **Items** — whether the copy's body text occurs in the original string; the state of
  the marks
- **Pass criterion** — 0 differing articles. **Met**
- **Known to be out of scope**
  1. **The date a statute came into force was not retrieved** (the API does not return
     it). Whether a text is current rests on **what the API serves**
  2. Whether the statute itself has since been amended **has to be tracked separately**
  3. **Whether the handling of numbers is consistent across the 7 is not visible by
     this method** (§2)
  4. **This document was written by one party and checked by the same party.** No second
     pair of eyes has gone over it

---

Last updated: 2026-11-08 (second edition, new). The first edition is kept, in Japanese,
at [`../ja/2026_11_07_law_corpus_verbatim_check.md`](../ja/2026_11_07_law_corpus_verbatim_check.md).
