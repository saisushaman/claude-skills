---
name: feature-impl-loop
description: >-
  Autonomous feature-implementation loop. Ingests a Plane ticket, confirms scope
  on the ticket, implements in an isolated git worktree with Claude Code, opens a
  GitHub PR, drives CI to green, requests the multi-bot review ecosystem
  (codex/Charlie/Gemini) and resolves their feedback, broadcasts to the
  #your-review-channel Slack channel tagging only the project's contributors, then
  pauses for human review and incorporates GitHub/Slack feedback. Tracks cycle
  time with a ticket timer. Use when given a Plane ticket id/link or asked to run
  the autonomous feature loop.
---

# Autonomous Feature Implementation Loop

Ingest a Plane ticket → clarify → implement in an isolated worktree → PR → green CI
→ multi-bot review → human review in Slack → incorporate feedback. Five phases.

> ⚠️ **This skill takes powerful, outward-facing actions** (writes code, pushes
> branches, opens PRs, posts to Slack, pings people, comments on Plane). Guardrails
> below are mandatory. It NEVER merges a PR and NEVER force-pushes a shared branch.

---

## Prerequisites & wiring status

| System | Status | Mechanism |
|--------|--------|-----------|
| **Claude Code** | ✅ ready | This agent — does the implementation in the worktree. |
| **git worktree** | ✅ ready | `git worktree add` for isolation (or the EnterWorktree tool). |
| **GitHub** | ✅ ready | `gh` CLI: PR create, `gh pr checks`, `gh run`, review comments. |
| **Slack** | ✅ ready | `plugin:productivity:slack` (server id may change — re-discover if `select:` load fails). Channel `#your-review-channel` = `C0XXXXXXXXX`. |
| **Plane** | 🔑 REST API | No MCP connector — use the Plane REST API. Requires env: `PLANE_BASE_URL`, `PLANE_API_TOKEN`, `PLANE_WORKSPACE`. If unset, fall back to a pasted ticket and skip Plane writes. See "Plane access". |
| **Review bots** (codex/Charlie/Gemini) | ✅ auto-on-open | They run automatically when a PR opens. The bot does NOT @-mention them — it just waits for and reads their reviews. `BOT_HANDLES` is only used to recognize which reviews are theirs. |

If a required system for the current phase is unavailable, **stop cleanly and say
what's missing** — never fake a step (e.g. don't invent a Plane comment you can't post).

### Plane access
No MCP tool exists. Use the REST API via `curl`/`gh api`-style calls:
- `GET  {PLANE_BASE_URL}/api/v1/workspaces/{PLANE_WORKSPACE}/projects/{project}/issues/{issue}/` — read ticket
- `POST …/issues/{issue}/comments/` — post a ticket comment (Phase 1 clarifications)
- Auth header `X-API-Key: {PLANE_API_TOKEN}` (token from env, never hard-coded).
Until these are configured, accept a **pasted ticket** (title + description) as input
and skip Plane writes, logging that clarification comments were not posted.

---

## Configuration

| Key | Default | Meaning |
|-----|---------|---------|
| `SLACK_CHANNEL` | `#your-review-channel` → `C0XXXXXXXXX` | Broadcast channel (Phase 4). |
| `BOT_HANDLES` | `codex`, `charlie`, `gemini` | Names used to RECOGNIZE the auto-run bots' reviews (they trigger on PR open; the bot does not invoke them). Confirm exact login names on first PR. |
| `PAUSE_BEFORE_PR` | `true` | After implementing + local validation, STOP and show the diff for human sign-off BEFORE pushing / opening the PR. Do not push without an explicit OK. |
| `TOP_N` | `3` | How many of the repo's top committers to tag in Slack (Phase 4). `@Assistant Bot` is always tagged on top of these. |
| `BASE_BRANCH` | `main` | Branch PRs target and worktrees branch from. |
| `REPO` | *(from ticket)* | `owner/repo`; resolve from the ticket/links or ask. |
| `NEVER_MERGE` | `true` | Bot never merges; humans merge. Do not change. |
| `MAX_CI_FIX_ROUNDS` | `3` | Cap on auto-fix→push cycles before escalating to a human. |
| `DRY_RUN` | `false` | If true, do everything except the writes (no push/PR/Slack/Plane posts); print what would happen. Use for first runs. |

---

## Phase 1 — Ingestion & verification (start the timer)

1. **Start timer:** record `date -Is` as `t_start` and keep it (a scratchpad file
   `cycle-<ticket>.json`); the ticket timer measures active cycle time (paused in
   Phase 4, resumed in Phase 5).
2. **Read the ticket:** fetch full title + description (Plane API, or the pasted
   ticket). Extract the linked `REPO`, acceptance criteria, and any checklist.
3. **Analyze & align:**
   - Evaluate: is this a direct implementation, or are there **explicit
     dependencies/blockers**? If blocked, post a Plane comment naming the blocker
     and **stop** (don't start a worktree).
   - For each clarification/iteration, **post a comment on the Plane ticket**
     (not just internal reasoning).
   - **Before writing any code, post a final Plane comment stating exactly what
     you will do** (the understood acceptance criteria + planned change). This is a
     hard gate — no code before this comment (or, in `DRY_RUN`/no-Plane mode, print it).

## Phase 2 — Implementation

1. **Isolate:** `git worktree add ../wt-<ticket> -b feat/<ticket>-<slug> {BASE_BRANCH}`
   — a fresh worktree + branch, never work on `main` or a shared checkout.
2. **Implement** with Claude Code: make the change, follow existing conventions,
   add/update tests, keep lint + build green locally. Validate locally before pushing.
3. **Sign-off gate (`PAUSE_BEFORE_PR`):** commit to the branch, then **STOP and
   present the diff + a summary to the human, and wait for an explicit OK.** Do not
   push or open the PR until approved. (This is the deliberate human gate before any
   outward-facing action.)
4. **Commit & PR (after OK):** push, `gh pr create` targeting `{BASE_BRANCH}` with a
   body that links the Plane ticket and lists the acceptance criteria. Capture the
   PR number + `headRefOid`.

## Phase 3 — CI & multi-bot review

1. **CI to green:** poll `gh pr checks <n>` / `gh run list`. If a check fails, read
   the logs, fix, push, re-check — up to `MAX_CI_FIX_ROUNDS`, then escalate to a
   human (Plane + Slack) rather than looping forever.
   - *Permissions exception:* if a check is blocked purely by missing permissions
     (not a real failure), post a Plane comment noting it and continue **if safe**;
     otherwise wait for all checks 100% green.
2. **Await the bots (auto-on-open):** codex/Charlie/Gemini run automatically when the
   PR opens — do NOT @-mention them. Poll the PR reviews/comments for feedback from
   the `BOT_HANDLES` accounts.
3. **Self-correct:** read each bot's feedback, fix genuinely valid issues, push,
   and **resolve those bot review threads**. Ignore/《explain》 false positives rather
   than blindly complying. Re-run CI after fixes.

## Phase 4 — Human review & Slack (PAUSE + stop timer)

1. **Resolve contributors to tag** — see `references/team-directory.md`. Source =
   the **top `TOP_N` committers on the PR's repo** (`gh api repos/{owner}/{repo}/
   contributors`, sorted by commits desc; or `git shortlog -sne`), mapped
   GitHub-login → Slack ID. **ALWAYS also tag `@Assistant Bot` (`U0ASSISTANTBOT`) on
   every PR.** Never `@channel`/`@here`, never the whole team, never the Claude bot.
2. **Broadcast** to `SLACK_CHANNEL` via `slack_send_message`: a single concise
   one-line summary of what the ticket addresses + the PR link + the resolved
   `<@ID>` tags. (Include the word "review" so it also satisfies the pr-review-bot
   trigger, if that bot is running.)
3. **Pause + stop timer:** record `date -Is`, add the elapsed active time to the
   cycle total, and **stop** — wait for human feedback. Do not proceed on your own.

## Phase 5 — Feedback incorporation (RESUME + restart timer)

Trigger: a reply thread appears on the Slack PR message, OR new review comments land
on the GitHub PR.
1. **Restart timer** (`date -Is` → resume accumulating).
2. **Fetch the authoritative feedback from GitHub** (`gh pr view <n> --comments`,
   `gh api .../pulls/<n>/comments`) — GitHub is the source of truth, not the Slack
   paraphrase.
3. **Refactor & push** to resolve the comments; resolve the GitHub threads.
4. **Reply in the Slack thread** with `slack_send_message(thread_ts=<msg ts>,
   message="Addressed!")` so reviewers are notified.
5. Loop Phase 4↔5 until approved. **Never self-merge** (`NEVER_MERGE`).

---

## Cross-cutting rules
- **One ticket at a time** per invocation; the worktree is the isolation boundary.
- **Timer** = active cycle time: running in Phases 1–3 and 5, paused in Phase 4.
- **Idempotency:** before acting, check whether a worktree/branch/PR for this ticket
  already exists; resume rather than duplicate.
- **Never**: merge, force-push shared branches, tag broadly, post secrets, or
  fabricate a step for an unavailable system.
- **Cleanup:** when the PR merges (human action) or the ticket closes, remove the
  worktree (`git worktree remove`).

## Running it
- One ticket, on demand: `/feature-impl-loop <plane-ticket-id-or-link>`.
- Polling for newly-assigned tickets: drive with `/loop` or a scheduled agent, but
  ONLY once Plane read access is wired (otherwise there's nothing to poll).
