# Skill optimization loop

A closed-loop, token-efficient system for evaluating and improving Claude Code
skills. Two skills (`grade-skill`, `improve-skill`) supply the reasoning; a set
of stdlib-only Python scripts do every deterministic step so **no LLM tokens are
spent on work a script can do reliably**.

```
/grade-skill <skill>
        │  discover + validate + (run tests) + reason + save
        ▼
   latest.json  ◄── compact machine interface ──►  latest.md (human report)
        │
        ▼
/improve-skill <skill>
        │  read latest.json → re-verify → prioritize → targeted edits
        ▼
   run tests  →  re-grade  →  compare-reports.py
        │
        ▼
   ACCEPT / REJECT / NEUTRAL   (behavioral regression ⇒ REJECT)
```

## Where things live

```
skills/
  grade-skill/
    SKILL.md                 # Grade-stage reasoning instructions
    references/
      rubric.md              # per-category 0-10 rubric (read at scoring time)
      report-schema.md       # the assessment/report JSON contract
    scripts/                 # deterministic engine (shared by both skills)
      _common.py             # discovery, frontmatter, timestamps, scoring consts
      discover-skill.py      # locate + inventory a skill
      validate-skill.py      # structural lint (frontmatter, broken refs, size)
      run-tests.py           # run deterministic behavioral tests
      score-results.py       # test results → behavioral_reliability
      save-report.py         # compute scores + render + persist reports
      compare-reports.py     # deterministic ACCEPT/REJECT verdict
    tests/
      manifest.json          # grade-skill's own behavioral tests
      fixtures/              # sample skills + reports the tests run against
  improve-skill/
    SKILL.md                 # Improve-stage reasoning instructions
    references/
      improvement-playbook.md

skill-reports/               # persisted reports, per skill (also default: ~/.claude/skill-reports)
  <skill-name>/
    latest.json
    latest.md
    history/<timestamp>.json
```

`improve-skill` reuses `grade-skill/scripts/*` — they are a matched pair,
installed side by side under `~/.claude/skills/`.

## Reports location
Default reports root is `~/.claude/skill-reports/` (persists across projects).
Override per-invocation with `--reports-root DIR` on `save-report.py` /
`run-tests.py`, or globally with the `SKILL_REPORTS_ROOT` environment variable.
The `skill-reports/` directory in this repo holds committed **example** reports.

## Running the loop

### 1. Grade
```
/grade-skill <skill-name>
```
Produces `latest.json`, `latest.md`, and a `history/<ts>.json` snapshot. With no
deterministic tests, the result is explicitly labeled a **static-analysis score**
(Overall = Design Quality). With tests, Overall = 40% Design + 60% Behavioral.

### 2. Improve
```
/improve-skill <skill-name>
```
Reads `latest.json` first (compact interface), re-verifies each issue against the
*current* skill, applies the smallest safe fixes in priority order (P0→P3),
re-validates, and re-tests.

### 3. Compare (deterministic gate)
```
python skills/grade-skill/scripts/compare-reports.py \
    ~/.claude/skill-reports/<skill>/history/<PREV>.json \
    ~/.claude/skill-reports/<skill>/latest.json
```
Exit code: `0` ACCEPT · `1` REJECT · `2` NEUTRAL. **A drop in behavioral
reliability (or a new P0/P1) is a REJECT even if the design score rose.** A
prettier prompt is never accepted on its own.

## How token usage is minimized
- **Discovery/validation** (file walking, YAML parsing, broken-reference
  detection) → `discover-skill.py` / `validate-skill.py`, not the model.
- **All arithmetic** (design quality, overall score, severity counts,
  behavioral reliability) → `save-report.py` / `score-results.py`.
- **Report rendering** (the big markdown document, tables) → `save-report.py`
  from a compact assessment JSON the model emits.
- **Version comparison / accept-reject** → `compare-reports.py`.
- **Grade → improve handoff** → the compact `latest.json`, not a re-paste of the
  full report into context. `latest.md` is read only when prose reasoning is
  needed.
The model is left with exactly the non-deterministic work: judging instruction
quality, ambiguity, missing behavior, edge cases, and writing fixes.

## Regression testing
- A skill may ship `tests/manifest.json` with `command` tests (deterministic,
  no LLM) and `manual`/`llm` tests (SKIPPED — never counted as passed).
- `run-tests.py` executes the command tests; `score-results.py` turns the pass
  rate into `behavioral_reliability`.
- `grade-skill` ships its own suite (8 command tests over its scripts), so the
  system is self-verifying: `python skills/grade-skill/scripts/run-tests.py grade-skill`.
- The loop refuses to call a change an improvement on prose alone: behavioral
  pass-rate and P0/P1 counts gate acceptance.

## Extending
- **New deterministic check** → add a script under `grade-skill/scripts/` and a
  step in the relevant SKILL.md; keep it stdlib-only.
- **New category weighting or thresholds** → constants live at the top of
  `_common.py` (weights) and `compare-reports.py` (tolerances).
- **Behavioral tests for a target skill** → drop a `tests/manifest.json` next to
  its `SKILL.md`; `run-tests.py` finds it automatically.

## Limitations
- Deterministic behavioral tests only cover what is deterministic (bundled
  scripts, command contracts). Pure-prose skill logic still needs LLM/manual
  evaluation; those tests are declared `manual` and honestly skipped.
- Static grade categories are model judgment; the rubric calibrates them but two
  runs can differ by a point. Trust the deltas and the behavioral numbers over
  absolute static scores.
- `compare-reports.py` needs a previous report in `history/` to compare against;
  the first grade has nothing to compare to.
