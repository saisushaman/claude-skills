---
name: improve-skill
description: >-
  Improve a Claude Code Skill using its latest grading report. Reads latest.json
  (the compact machine interface written by grade-skill), re-verifies that each
  reported issue still exists, prioritizes fixes by impact (P0>P1>P2>P3) against
  effort and regression risk, makes targeted edits that preserve working
  behavior, re-validates structure, then re-grades and runs compare-reports.py
  to ACCEPT or REJECT the change (a behavioral regression is rejected even if the
  design score rose). Produces a concise improvement report. Use when asked to
  improve, fix, optimize, refactor, or apply the evaluation of a skill, or as the
  second half of the grade -> improve loop.
---

# improve-skill

The **Improve** stage of the closed loop. It is driven by the report on disk,
never by conversational memory of a previous grade:

```
grade -> [latest.json] -> improve -> test -> re-grade -> compare -> accept/reject
```

## Operating principle — verify, then change the minimum

The grading report is a **hypothesis**, possibly stale. Do not blindly apply
every recommendation. Re-verify each issue against the *current* skill, fix the
highest-impact real ones with the smallest safe edit, and prove the change is a
net improvement with the deterministic comparison — never by asserting the prose
"reads better". A prettier SKILL.md is not the goal; measurably better
reliability, correctness, consistency, and robustness is.

Reuse grade-skill's scripts (they are a matched pair, installed side by side).
From this skill, reference them at the sibling path:
`../grade-skill/scripts/<name>.py` (in this repo) or
`~/.claude/skills/grade-skill/scripts/<name>.py` (when installed). Resolve once
at the start and reuse.

## Prerequisites
- `python` on PATH. No third-party packages.
- `grade-skill` available (for its scripts). If its scripts can't be found,
  say so and stop — improve depends on them for validation and comparison.

## The algorithm

### Step 1 — Identify the target and load the report (script + read)
- Resolve the skill: `python <grade>/scripts/discover-skill.py <name>`.
- **Read `latest.json` first** from `<reports-root>/<name>/latest.json`
  (default `~/.claude/skill-reports/<name>/`). It is the compact interface: it
  has `issues`, `severity_counts`, `top_improvements`, scores, `recommendation`.
- Read `latest.md` **only if** you need the prose reasoning behind an issue that
  latest.json states too tersely. Do not load the whole markdown by reflex — that
  wastes the tokens the JSON interface exists to save.
- If no report exists, tell the user to run `/grade-skill <name>` first, and stop.
  (Do not invent a grade.)

### Step 2 — Re-verify each issue against the CURRENT skill (reasoning)
The report may predate edits. For every issue you intend to act on:
- Re-read the relevant part of the current `SKILL.md`/resources.
- Re-run `python <grade>/scripts/validate-skill.py <name>` — broken-reference and
  structural issues are confirmed or cleared here deterministically.
- Mark each issue: **still-present**, **already-fixed**, or **invalid**
  (misdiagnosis / not actually a problem for this skill's purpose). Only
  still-present issues are eligible for change.

### Step 3 — Prioritize (reasoning)
Order eligible fixes by severity first (**P0 -> P1 -> P2 -> P3**), then within a
tier by expected impact. For each, weigh:
- **Expected impact** — how much it moves reliability/correctness/clarity.
- **Effort** — size of the edit.
- **Regression risk** — chance of breaking working behavior.
Skip or defer low-impact/high-risk items and cosmetic rewrites. Prefer the
smallest edit that resolves the issue. Do not expand the prompt unnecessarily.

### Step 4 — Make targeted edits (edit)
- Change only what a chosen fix requires. **Preserve behavior that already
  works** — do not reflow untouched sections, rename things gratuitously, or
  "tidy" beyond the fix.
- Keep edits localized and legible so the change is reviewable.
- If a fix needs a new referenced file or script, add it and reference it
  correctly (validate will confirm the reference resolves).

### Step 5 — Re-check the whole skill after editing (script + reasoning)
- Re-read the complete SKILL.md. Check for **contradictions** introduced by the
  edit, that **referenced files/paths** still resolve, that **frontmatter** is
  intact (name/description), and that the **original purpose is preserved**.
- Run `python <grade>/scripts/validate-skill.py <name>` again — it must be clean
  (or cleaner). Fix any new ERROR before proceeding.

### Step 6 — Test (script)
- If `tests/manifest.json` exists: `python <grade>/scripts/run-tests.py <name>`.
  All previously-passing tests must still pass; a regression here blocks accept.
- If **no** tests exist, judge whether a lightweight deterministic test is worth
  adding (e.g. a command test asserting a bundled script's contract). If cheap
  and meaningful, add one to `tests/manifest.json`; if the skill is pure LLM
  prose with nothing deterministic to assert, say so honestly and rely on the
  design-quality delta instead. Never claim tests pass when none ran.

### Step 7 — Re-grade and compare (script-assisted)
- Re-grade the edited skill (invoke `/grade-skill <name>` or run its steps) so a
  fresh `latest.json` is written. The prior report is already preserved under
  `history/`.
- Compare old vs new deterministically:
  ```
  python <grade>/scripts/compare-reports.py <history/PREV.json> <latest.json>
  ```
  Exit code / verdict: **ACCEPT** (0), **REJECT** (1), **NEUTRAL** (2).
- **Honor the verdict.** A REJECT — most importantly a behavioral-reliability
  drop or a new P0/P1 even when design quality rose — means the change is not an
  improvement. Revert or rework; do not ship a behavioral regression.

### Step 8 — Improvement report (output)
Produce a concise report (to the user; optionally save alongside the report dir):
- **Changes made** — file + what/why, keyed to the issue ids addressed.
- **Problems fixed** — issues now resolved (with the evidence they're gone).
- **Problems intentionally not fixed** — and why (low impact, high risk, invalid,
  out of scope).
- **Regression risks** — what could break, and what you checked.
- **Recommended tests** — deterministic checks to add or run next.
- **Verdict** — the compare-reports result and before/after metrics.

## Guardrails
- Report-driven, not memory-driven: read `latest.json` from disk each run.
- Verify before editing — the report can be stale or wrong.
- Minimum viable edit; preserve working behavior; avoid prompt bloat and cosmetic
  churn.
- Never accept a change that regresses behavioral reliability or adds a P0/P1,
  regardless of design-score movement.
- Never claim tests ran/passed when they did not.
- Preserve the skill's original purpose and frontmatter.

See `references/improvement-playbook.md` for concrete edit patterns per issue
category and the accept/reject decision table.
