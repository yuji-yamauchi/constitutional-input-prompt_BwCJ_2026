# An index of what was looked into

This is an **index** of the background research behind this application.

- Period: **2026-04-12 to 2026-10-17** (about six months)
- Topics: **112**
- Documents: **645** (of which **636** could be read mechanically)
- Volume: **100,011 lines / 7.59 million characters**

For comparison, the application in this repository is 15,398 lines.
The research record is roughly six times that.

---

## 1. The research itself is not in this repository

There is one reason.

> The raw research output contains **5,829 instances of academic citation form**.
> Almost none of them have been **verified by reaching the primary source**.

This repository has a directory called [`08_sources`](../../08_sources/), and it
carries three rules: write down the place you reached, divide certainty into three
levels, and never write "there is none."

Putting 5,829 unverified citations into the same repository would **break those
rules inside the same repository.**

So only the index goes here.

**"Looked into" and "verified" are different words.** The index below is a record
of the former, not the latter.

### How each number was counted

| Number | How it was counted |
|---|---|
| 645 documents | Tracked files in the research directory |
| 636 documents | Of those, the `.md` and `.yaml` files readable as UTF-8. The remaining 9 are office documents and images; the scanner does not reach the text inside them |
| 100,011 lines | Sum of newline counts across the 636 |
| 5,829 instances | Regular-expression count of academic citation form (`et al.`, `doi:`, the DOI number pattern) across the body text of the 636. 287 documents matched |

---

## 2. How the research was done

1. **Write the question as a document first.** What is to be known, what must be
   verified against a primary source, and where inference is acceptable — all
   written down before asking.
2. **Give the same question to models from more than one maker.** Of the 112
   topics, **75** still hold output from two or more models.
3. **Place the outputs side by side and keep the disagreements.** Disagreement is
   a sign that one of them is wrong; it is not something to be tidied away.
4. **Do not count agreement as proof of existence.** Three models can make the
   same mistake. Agreement is not a reason to skip verification.

Point 4 is the same principle that runs through the rest of this repository.

---

## 3. The index (six groups, 101 topics, 608 documents)

### 3-1. Whether employment-support methods actually work — 14 topics, 97 documents

For the psychological, behavioural and vocational-rehabilitation methods used in
employment-support practice, how far the research actually demonstrates an effect
when they are applied to employment support for disabled people.

One topic per method. The answers fell into three groups: effect demonstrated,
effect not demonstrated, and thin evidence within the Japanese system.

### 3-2. Measurement and the machinery of evaluation — 20 topics, 143 documents

This group had the largest effect on the design of the application.

It covers instruments that express functioning, ability or quality of life as a
number: what has been built, and what happens when such an instrument is applied
to a disabled person.

What the application chose, as a result of looking into this, was **not to use
them**. This application does not judge the person. It produces no points, no
ranking, no stages, no assessment of condition. This group is the background to
that decision.

The names of the instruments are deliberately not written here, for two reasons.
First, this contest has a rule against stating that a work is based on a named
assessment instrument. Second, and more important, **this application does not
use any of them.** Listing names of things you do not use reads as a claim that
you do.

### 3-3. Law and the welfare system — 19 topics, 83 documents

Statutes, ministerial notices, case law and administrative operating criteria
across disability welfare, housing and employment.

One discipline was held throughout: **the law as it stands and the law as it
ought to be go in separate columns.** What a council is still debating is never
written as what has been decided.

Only the items from this group that were carried through to primary verification
have moved into [`08_sources`](../../08_sources/). Of the 19 topics indexed here,
only some have been verified that far.

### 3-4. Theoretical foundations — 26 topics, 138 documents

The premises the whole undertaking stands on.

- The definitions of the institutional premises currently agreed upon in Japan
  (rule of law, liberty, democracy, modified capitalism, science)
- What it means for a person to be the author of their own record
- The point where a person deciding about themselves and an outside observer
  detecting structural coercion cannot both be satisfied
- How to treat a person's wishes having been reshaped by their environment
  (adaptive preference)
- The difference between asking whether someone has enough (sufficientarianism)
  and asking how to maximise

**Many topics in this group have no answer yet.** They are left without one.

### 3-5. Having the work broken from outside — 9 topics, 37 documents

Records of the project's own ideas, scripts and self-definitions being handed to
models from **other makers, to be examined adversarially.**

- Handing the foundational document over with the instruction to read it
  intending to break it
- Having video and training scripts audited from outside for factual accuracy
- Having self-written definitions evaluated by a different model

This is the execution record of one rule: do not run the final inspection on
your own work. Another window onto the same model does not count as outside.

### 3-6. The container and the technology — 13 topics, 110 documents

Research on the foundations: handling Japanese reading and writing, the design of
where records are kept, what overseas AI regulation designates as high risk,
international standards for operating AI, and how training material is built.

---

## 4. Eleven topics, 37 documents, left out of the index

What was left out is listed with the reason for leaving it out. Quietly removing
things leaves the reader unable to tell "there is none" from "we decided not to
publish it."

| Reason for exclusion | Topics |
|---|---|
| Our own funding, location, or business strategy | 4 |
| Statistics that identify a locality | 1 |
| Material concerning a third-party organisation | 1 |
| Statistics on health, medicine, or death | 2 |
| Research about the judging of this contest (not part of the work) | 2 |
| Documents belonging to no topic | 1 |

101 + 11 = 112. 608 + 37 = 645.

---

## 5. On material brought in from outside

This contest requires that data brought in from outside be stated in the
repository.

- This research was produced **outside this repository**, between April and
  October 2026.
- It used Claude and large language models from other makers. Specific
  configurations and a list of vendor names are not written here.
- **The submitted application reads none of these documents.** Across the 82
  implementation files there are 0 references to the research directory
  (verified mechanically).
- What the application does read is a closed set of statutory articles, copied
  one article at a time. How those copies were checked is in
  [`08_sources`](../../08_sources/).

---

## 6. The scope of this index

- **Subject** — 645 tracked files in the research directory
- **Items** — document counts, topic counts, line counts, citation-form counts,
  and the assignment of topics to groups
- **Pass criterion** — that all 112 topics are assigned to the six groups or to
  the excluded set, with no duplication and nothing left over. Checked
  mechanically: **0 duplicates, 0 unassigned, 0 names that do not exist**
- **Known to be out of scope**
  1. **The text inside the 9 office documents and images** is not reached by the
     scanner
  2. Of the categories the scanner flagged, **some have not had every hit traced
     back to the source** (201 hits shaped like keys, 3 shaped like health
     figures). They are probably false positives, but this is unverified
  3. **Whether the content of the 5,829 citations is correct has not been
     examined.** This index counts only that they are present
  4. **No summaries of the research content are given here.** A summary is a
     derivative, and it displaces the original; placing one in an index was
     judged inappropriate
  5. **This index was written by one party and inspected by the same party.** No
     second pair of eyes has gone over it

---

## 7. The questions this index was put to

In this repository, four questions are put to anything produced. They were put to
this index as well.

1. **Does it leave the person as the author?** This index says nothing about any
   person. It is a record of the side doing the looking
2. **Does it fix a person in place with a number or a label?** What is counted is
   documents and topics, not people
3. **Does the implementation hand a judgement back?** An index judges nothing
4. **Has it drifted toward being a mirror without noticing?** 3-2 is the
   dangerous place. A record of researching evaluation instruments, read plainly,
   becomes a claim that those instruments are in use — which is the mirror side.
   So the names are not written, and **the fact that none of them are used is
   stated first**

---

Last updated: 2026-11-08
