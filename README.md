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

## Install
Clone into your Claude Code skills directory:

```
git clone https://github.com/saisushaman/claude-skills.git
cp -r claude-skills/skills/* ~/.claude/skills/
```

Each skill's `SKILL.md` documents its own configuration (channel/user IDs, keywords,
API tokens via env vars). Update those to match your environment.
