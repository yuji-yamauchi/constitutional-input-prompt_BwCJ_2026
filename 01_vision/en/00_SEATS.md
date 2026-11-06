# On the "seats" that wrote this theory

> **On the seats.** The documents in this folder were written by several Claude
> sessions with separate roles, corresponding over files. They are not subagents
> spawned inside one run: each is its own session, and the only thing that passes
> between them is a letter on disk. A seat does not inspect its own work. The
> seat names appear throughout the texts, so this page says who they are.
>
> The Japanese original is at [`../ja/00_SEATS.md`](../ja/00_SEATS.md).

The documents placed in this `01_vision/` folder contain **the names of the seats**
as they are. They have not been removed. A theory document where you cannot tell
who wrote it is the same thing as an assertion with no source.

---

## What a "seat" is

**A separate Claude session, divided by role.**

Not a helper agent invoked from inside a single run. Each is an independent
session, and **the only thing they can receive from one another is one letter
(YAML) placed on disk.** The contents of a conversation are not shared. What can be
read is only what the other side wrote and placed.

There is exactly one intention in this shape.

> **The seat that wrote a thing does not perform the final inspection on it.**

When the same model with the same context inspects its own work, it carries the
blind spots over along with everything else. So a seat other than the one that
designed it inspects it, and whether it may be published is decided by yet another.

---

## The seats

| Seat | Role | Letters |
|---|---|---|
| **vsclaude** | Routing and relaying, and **the publishing edge** (deciding whether a thing may go out from here, and actually putting it out) | 108 |
| **bclaude** | Outside research (rules, statutes, prior work — primary-source confirmation) | 48 |
| **fable** | Design and implementation (specifications, the app itself, allocating inspection) | 24 |
| **hacka** | Coding, and re-reading with different eyes | 17 |
| **chatgpt** / **gemini** | **Seats that are not Claude.** Putting the same question to a different maker's model | 12 / 9 |
| **vision** | Inspection from the theory side (watching for collisions with the canon) | 5 |

How counted: the letters in the non-public workspace, counted on the `from:`
field (as of 2026-11-06).

**The presence of non-Claude seats is deliberate.** If inspection is run only
within one model family, everyone confirms the same mistake together. That is not
a substitute for inspection from outside.

---

## About model names

Each seat writes the name of the model it is using into its letters. But every
seat also adds that **"this is a self-declaration; the entity that actually
responded may differ".** A session's configured value and the model that actually
answered can diverge. The same treatment holds here — **a model name is a
declaration, not a verified fact.**

---

## Why the seat names were not removed

At first the intention was to replace the seat names with generic ones when
publishing. After replacing them, it became clear that the replacement itself was
the wrong move.

- These documents are **internal working documents.** The version histories, the
  source tags, the marks for "not yet verified", "waiting on whose reply" —
  **that is itself the record of how this was arrived at.**
- Erase the sources and what remains is **a bundle of groundless assertions.**
  Which is precisely the reverse of what this tool is trying to do.

One thing written honestly: the rule "do not put seat names on a public surface"
sat in this workspace's internal regulations **with no reason written beside it.**
It was asked about, searched for, and not found — **so the rule was the thing that
got changed.**

---

## Notes for reading

- **The folder and file names that appear in the texts point at places that are not
  public.** They cannot be followed. They are the names of originals in the
  non-public workspace.
- `★` is an emphasis mark. The marks used internally have been left as they are.
- The tags `[一次確認]` / `[2次一致]` / `[未確認]` express **the strength of the
  grounds**: *primary source reached* / *agreement between secondary sources* /
  *unverified*. Only something whose original text the writer reached themselves is
  `[一次確認]`.
