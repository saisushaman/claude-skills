---
name: grade-skill
description: >-
  Evaluate a Claude Code Skill and produce a persistent, structured grading
  report. Scores 12 design categories (0-10 each), classifies issues by
  severity (P0-P3) and evidence type (OBSERVED/DOCUMENTED/INFERRED/
  HYPOTHETICAL), runs any deterministic behavioral tests, and saves latest.json
  + latest.md + a timestamped history copy. Deterministic bookkeeping (discovery,
  validation, scoring math, report rendering, comparison) is delegated to bundled
  scripts to save tokens; the model only reasons about quality. Use when asked to
  grade, evaluate, score, audit, or review the quality of a skill, or as the first
  half of the grade -> improve optimization loop.
---

# grade-skill

Evaluate a target Skill and persist a report that `/improve-skill` can consume.
This is the **Grade** stage of the closed loop:

```
grade -> diagnose -> improve -> test -> re-grade -> compare -> accept/reject
```

## Operating principle — spend tokens only on reasoning

Deterministic work is done by the bundled Python scripts in `scripts/`
(stdlib-only, run with `python`). **Do not** hand-walk directories, hand-parse
YAML, hand-compute scores, or hand-format the report — the scripts do that
reliably and for free. You spend tokens on exactly one thing: **judging the
quality of the skill's instructions.** Everything else is a script call.

Scripts (invoke with `python scripts/<name>.py`; from this skill's directory, or
use an absolute path):

| Script | Deterministic job |
|--------|-------------------|
| `discover-skill.py <name>` | Locate the skill; inventory files; parse frontmatter; list referenced files + broken ones; size/line/word metrics. |
| `validate-skill.py <name>` | Lint: frontmatter validity, name/dir match, description length, broken references, empty/oversized SKILL.md, script syntax. |
| `run-tests.py <name>` | Run the skill's deterministic behavioral tests (`tests/manifest.json`). Manual/LLM tests are SKIPPED, never counted as passed. |
| `score-results.py <results>` | Convert test results to `behavioral_reliability` + a `tests` block. |
| `save-report.py <assessment.json>` | Compute design_quality/overall/severity counts, timestamp, and write `latest.json`, `latest.md`, `history/<ts>.json`. |
| `compare-reports.py <old> <new>` | Deterministic ACCEPT/REJECT/NEUTRAL verdict (used at re-grade time). |

`<name>` may be a skill name (searched under `./skills`, `.claude/skills`,
`~/.claude/skills`) or a direct path to the skill directory.

## Prerequisites
- `python` on PATH (3.8+). No third-party packages required.
- Read-only intent: **never modify the target skill while grading.** Grading and
  editing are different jobs; editing is `/improve-skill`.

## The algorithm

### Step 1 — Discover (script)
Run `python scripts/discover-skill.py <name>`. Capture the JSON. It tells you
where the skill is, what files it bundles, its frontmatter, and — importantly —
which referenced files exist. Use this to decide what to read; do not `ls`
yourself.

### Step 2 — Validate (script)
Run `python scripts/validate-skill.py <name>`. Every `ERROR`/`WARN` finding is
pre-verified OBSERVED/DOCUMENTED evidence — fold them directly into the relevant
categories (broken references -> *Tool and resource reliability*; oversized body
-> *Context efficiency*; missing description -> *Purpose clarity*). Do not
re-derive these by hand.

### Step 3 — Understand the skill (reasoning)
Read `SKILL.md` in full. Read referenced resources that matter to the contract
(the discover output lists them and whether they exist) — templates, scripts,
examples, tests. From this, state the **Skill Contract**: *given <inputs> under
<preconditions>, it should produce <outputs> with <guarantees>.* You cannot grade
completeness or consistency without first fixing the contract in your own words.

### Step 4 — Behavioral tests (script, optional but preferred)
If `tests/manifest.json` exists (discover shows `test_file_count` > 0), run:
```
python scripts/run-tests.py <name>            # -> results JSON
python scripts/score-results.py <results.json>  # -> behavioral_reliability + tests block
```
Only tests that actually executed count. If there are no deterministic tests,
leave `behavioral_reliability: null` — the report is then explicitly a
**static-analysis score**. Never fabricate a behavioral number, and never claim
tests ran when they did not.

### Step 5 — Grade the 12 categories (reasoning)
Score each 0-10 using the scale below. The full per-category rubric —
what earns a 9 vs a 5 in each — is in `references/rubric.md`; read it before
scoring so grades are calibrated and repeatable.

1. Purpose clarity 2. Instruction clarity 3. Instruction completeness
4. Instruction consistency 5. Output specification 6. Input handling
7. Error and failure handling 8. Edge-case coverage 9. Tool and resource
reliability 10. Context efficiency 11. Maintainability 12. Testability

Scale: `0-2` Critical deficiency · `3-4` Poor · `5-6` Adequate · `7-8` Good ·
`9` Excellent · `10` Exceptional.

### Step 6 — Diagnose (reasoning)
Produce issues, each classified by **severity** (P0 critical, P1 high, P2 medium,
P3 low) and **evidence type**:
- `OBSERVED` — you saw it fail (a run, a broken reference confirmed by validate).
- `DOCUMENTED` — the SKILL.md text itself states/omits it.
- `INFERRED` — a reasoned risk from the design, not yet seen fail.
- `HYPOTHETICAL` — a possible risk you cannot substantiate. Label it as such;
  never present it as observed.

Each issue: `severity`, `category`, `evidence_type`, `problem`, `why`,
`evidence`, `fix`.

Discipline (these are hard rules):
- Distinguish **design quality** (how well it's written) from **behavioral
  reliability** (whether it works). Do not let a polished prompt inflate a
  reliability claim you did not test.
- Distinguish observed failures from inferred/hypothetical risk. Do not report a
  hypothetical as if observed.
- **Never invent requirements irrelevant to the skill's intended purpose.** Grade
  the skill it is, not the skill you would have written.

### Step 7 — Assemble the assessment JSON (reasoning -> compact output)
Emit the compact assessment object defined in `references/report-schema.md`. You
provide the 12 scores, the issues, short prose (`overall_assessment`,
`skill_contract`, optional `behavioral_evaluation`), and the qualitative lists
(strengths, ambiguities, missing/conflicting/redundant instructions, edge cases,
top_improvements, confidence, recommendation). **You do not compute
design_quality or overall_score** — save-report.py does. Keep prose tight; the
script renders the full document.

Write it to a file (e.g. the scratchpad), then Step 8. Include
`behavioral_reliability` + `tests` only if Step 4 produced them (or let
score-results.py `--into` inject them).

### Step 8 — Persist (script)
```
python scripts/save-report.py <assessment.json> [--reports-root DIR]
```
This computes all derived numbers and writes `latest.json`, `latest.md`, and
`history/<timestamp>.json` under `<reports-root>/<skill>/` (default
`~/.claude/skill-reports/`). The printed summary has the final scores.

### Step 9 — Report to the user
Summarize concisely: overall + design (+ behavioral if any), scoring mode
(label a no-tests result **static-analysis score**), the P0/P1 count, the top 3
improvements, confidence level, and the recommended next step (usually
`/improve-skill <name>`). Point to `latest.md` for the full report. Do not paste
the entire report back — it is on disk.

## Scoring summary
- **Design Quality** = (sum of 12 scores / 120) × 100. *(save-report computes it.)*
- **Overall** = Design Quality when no behavioral tests ran (a **static-analysis
  score**); otherwise `0.40 × Design + 0.60 × Behavioral`.
- **Confidence**: `HIGH` (read everything, tests ran, evidence mostly OBSERVED/
  DOCUMENTED) · `MEDIUM` (some inference, limited/no tests) · `LOW` (couldn't read
  key resources, or heavy hypothetical reasoning).

## Output contract (what the user gets)
A saved report containing: Overall Assessment · Skill Contract · Scorecard ·
Behavioral Evaluation · Strengths · Critical Issues · Other Issues · Ambiguities ·
Missing Instructions · Conflicting Instructions · Edge Cases · Redundant
Instructions · Top 5 Improvements · Recommended Next Step · Confidence Level.
The markdown is rendered by save-report.py from your assessment JSON.

## Guardrails
- Never modify the target skill.
- Never claim tests were run when they were not; unrun/manual tests are SKIPPED.
- Prefer OBSERVED/DOCUMENTED evidence; mark INFERRED/HYPOTHETICAL honestly.
- If discovery fails (skill not found), report the searched paths and stop.
- Keep the loop honest: a prettier SKILL.md is not an improvement unless the
  scores or behavior say so.
