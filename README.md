# claude-skills

Personal backup of my [Claude Code](https://claude.com/claude-code) skills. These
run locally from `~/.claude/skills/`; this repo is a versioned record, not a
deployment target.

> **Private repo.** Contains environment-specific IDs (Slack channel/user IDs,
> internal repo names, teammate contacts). Do not make public without sanitizing.

## Skills

### `skills/pr-review-bot/`
Autonomous PR review bot. One polling pass over a single Slack channel: find an
eligible PR request (PR URL + opt-in keyword + a specific tag, not yet claimed with
`:eyes:`), review it across five vectors (code, security, architecture, tests,
spec-match), post severity-tagged inline comments to GitHub, reply in the Slack
thread, and mark done. Reviews others' PRs only. Driven on an interval with `/loop`.

### `skills/feature-impl-loop/`
Autonomous feature-implementation loop. Ingests a Plane ticket → confirms scope on
the ticket → implements in an isolated `git worktree` → pauses for human sign-off →
opens a PR → drives CI green → waits for the auto-run review bots → broadcasts to
Slack (tagging the repo's top committers + a fixed assistant) → incorporates human
feedback. Tracks cycle time. Never merges, never force-pushes.

### `skills/grade-skill/` + `skills/improve-skill/` — the skill optimization loop
A closed-loop, **token-efficient** system for evaluating and improving skills.

- **`grade-skill`** scores a skill across 12 design categories (0-10 each),
  classifies issues by severity (P0-P3) and evidence type (OBSERVED / DOCUMENTED /
  INFERRED / HYPOTHETICAL), runs any deterministic behavioral tests, and saves a
  persistent report (`latest.json` + `latest.md` + `history/<ts>.json`).
- **`improve-skill`** reads `latest.json`, re-verifies each issue against the
  current skill, applies the smallest safe fixes in priority order, re-tests, and
  re-grades — then `compare-reports.py` returns a deterministic **ACCEPT / REJECT**
  (a behavioral-reliability regression is rejected even when the design score rose).

All deterministic work — discovery, validation, scoring math, report rendering,
comparison, test running — is delegated to stdlib-only Python scripts in
`skills/grade-skill/scripts/`, so LLM tokens are spent only on judgment. The two
skills hand off through the compact `latest.json`, not by re-pasting reports.

```
/grade-skill <skill-name>        # evaluate -> writes latest.json + latest.md
/improve-skill <skill-name>      # read report -> fix -> re-grade -> ACCEPT/REJECT
```

Self-verifying test suite (8 deterministic tests over the scripts):
```
python skills/grade-skill/scripts/run-tests.py grade-skill
```
Full design, data flow, and token-efficiency rationale:
**[`docs/skill-optimization-loop.md`](docs/skill-optimization-loop.md)**.

## Install
Clone into your Claude Code skills directory:

```
git clone https://github.com/saisushaman/claude-skills.git
cp -r claude-skills/skills/* ~/.claude/skills/
```

Each skill's `SKILL.md` documents its own configuration (channel/user IDs, keywords,
API tokens via env vars). Update those to match your environment.
