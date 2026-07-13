---
name: pr-review-bot
description: >-
  Autonomous DevOps/security PR review bot. One invocation = one polling pass:
  find eligible pull requests announced in Slack (a PR URL plus the opt-in
  review keyword, not yet claimed with an :eyes: reaction), review across five vectors
  (code, security, architecture, tests, spec-match), post severity-tagged inline
  comments to GitHub, then reply in the Slack thread that the review is done.
  Designed to be driven on an interval with /loop or a scheduled cloud agent.
  Use when asked to run, set up, or loop the automated PR review bot.
---

# PR Review Bot

An autonomous DevOps + security code-review assistant. **One invocation performs
exactly one polling pass** and is safe to run repeatedly — the `:eyes:` reaction
is the idempotency lock, so a PR is never reviewed twice. Repetition is handled
by the driver (`/loop` or a scheduled agent), not by this skill.

---

## Configuration

Read these values from the invocation args if provided; otherwise use the defaults.
Edit the defaults here to hard-wire your environment.

| Key | Default | Meaning |
|-----|---------|---------|
| `REVIEW_KEYWORD` | `review` | Opt-in trigger. Part of eligibility (case-insensitive substring). NOTE: "review" is common in normal chatter ("needs a human review"), so the `REQUIRE_TAG` + no-`:eyes:` gates do most of the real filtering. |
| `REQUIRE_TAG` | `<@U0OWNER>` (Owner) | The message MUST tag this user. Eligibility = PR URL **and** `REVIEW_KEYWORD` **and** this mention present. |
| `CLAIM_DEBOUNCE_SEC` | `5` | After finding a candidate, wait this long, then re-check for `:eyes:` before claiming — yields to a human who reacts in the window. |
| `SLACK_CHANNEL` | `#your-review-channel` → `C0XXXXXXXXX` | The ONE channel this bot polls. Do not read or post anywhere else. |
| `CLAIM_EMOJI` | `eyes` | Reaction that marks a PR "claimed / in progress". Presence = skip. NOTE: humans in this channel also use `:eyes:` by hand, so any human-eyed message is treated as already claimed and skipped — that is intended. |
| `DONE_EMOJI` | `white_check_mark` | Reaction added when the review is posted. |
| `REPO_ALLOWLIST` | *(empty = all your-org repos)* | Optional list of `owner/repo` the bot may review. A PR outside it is skipped and noted in-thread. |
| `SKIP_OWN_PRS` | `true` | This bot reviews **OTHERS'** PRs only. If the PR author is the gh-authenticated user (you), **skip entirely** — no review, no GitHub post, no findings. Standing rule: you don't review your own PRs. |
| `REVIEW_EVENT` | `COMMENT` | GitHub review event. Keep `COMMENT` — a bot must not `APPROVE`/`REQUEST_CHANGES`. |
| `SLA_MINUTES` | `15` | Per-review completion window: target 10 min, **15 hard ceiling**. If a single PR can't finish in time, post what's confirmed and flag the rest in-thread. |

---

## Prerequisites (check first, fail loudly)

1. **GitHub** — `gh auth status` must succeed. All GitHub reads/writes go through
   the `gh` CLI and `gh api`. This works headless.
2. **Slack** — the **`plugin:productivity:slack`** MCP connector must be
   authorized. Its tools are only enumerable once the connector is authed (in a
   non-interactive/headless run they will be absent). Load the four tools this
   skill uses at the start of a pass:
   ```
   ToolSearch query "select:mcp__<SLACK>__slack_read_channel,mcp__<SLACK>__slack_get_reactions,mcp__<SLACK>__slack_add_reaction,mcp__<SLACK>__slack_send_message"
   ```
   where `<SLACK>` is the Slack MCP server id. As of wiring it is
   `<slack-mcp-server-id>`, but this id can change if the
   connector is re-authorized — if the `select:` load fails, re-discover with
   `ToolSearch query "slack read channel reactions add send message"` and use the
   ids from the results. Tool → step mapping:
   - `slack_read_channel` — Step 1 (channel history; `detailed` format includes reactions)
   - `slack_get_reactions` — Step 2 (the `:eyes:` guard)
   - `slack_add_reaction` — Step 3 (claim) and Step 8 (done)
   - `slack_send_message` with `thread_ts` — Step 8 (threaded reply)
   If discovery returns no Slack tools, the connector is **not connected**: do not
   guess tool names. Report that Slack must be authorized via `/mcp` (interactive)
   or claude.ai connector settings, then stop. The GitHub review step can still
   run via "Manual / GitHub-only mode" (pass a PR URL directly).

---

## One pass — the algorithm

Run these steps in order. A review should complete within `SLA_MINUTES`
(target ~10 min, 15 hard ceiling) from claim to Slack reply.

### Step 1 — Discover candidates (Slack)
- Read recent history of the ONE configured channel:
  `slack_read_channel(channel_id="C0XXXXXXXXX", limit=30, response_format="detailed")`.
  `detailed` includes each message's reactions, which Step 2 needs.
- **Never read any channel other than `C0XXXXXXXXX`.** This bot is scoped to
  `#your-review-channel` only.
- Keep a message only if ALL THREE hold:
  1. it contains a GitHub PR URL (`github.com/<owner>/<repo>/pull/<n>`),
  2. it contains the opt-in `REVIEW_KEYWORD` (case-insensitive), and
  3. it tags `REQUIRE_TAG` (the mention `<@U0OWNER>` / Owner) — the raw
     message text shows this as `<@U0OWNER|Owner>`.
  Record each candidate's `ts` (message timestamp) — it's the id for reactions
  and the thread reply.

### Step 2 — Filter already-handled (the loop guard)
- Using the reactions already returned in Step 1 (or `slack_get_reactions(
  channel_id="C0XXXXXXXXX", message_ts=<ts>)` to be certain), **skip any message
  that already carries the `CLAIM_EMOJI` (`eyes`) reaction** — a review is in
  progress or done.
- This reaction check is the ONLY thing preventing duplicate reviews. Treat it as
  authoritative.

### Step 3 — Debounce, then claim atomically
- **Wait `CLAIM_DEBOUNCE_SEC` (5s), then re-check for `:eyes:` before doing
  anything.** This yields to a human who reacts in the window. Mechanism:
  `Start-Sleep -Seconds 5` (PowerShell) or `sleep 5` (Bash); if the environment
  blocks a foreground sleep, still enforce the debounce by re-reading reactions
  as a separate step a moment later — the re-check is the point, the exact timer
  is secondary.
- After the wait, re-run `slack_get_reactions(channel_id="C0XXXXXXXXX",
  message_ts=<ts>)`. If `eyes` is now present, **skip** — a human (or another
  runner) claimed it during the debounce.
- Otherwise **claim it before any review work**:
  `slack_add_reaction(channel_id="C0XXXXXXXXX", message_ts=<ts>, emoji="eyes")`.
  A concurrent or next-tick pass will now skip it.
- Adding a duplicate reaction succeeds silently, so guard against the race:
  right after adding, re-check with `slack_get_reactions` — if the `eyes` count
  is >1 or was placed by another user before you, assume someone else owns it and
  skip. (Single-runner setups can skip this re-check.)
- Process **one PR per pass** by default (keeps each pass inside the SLA and makes
  the loop naturally fair). Set args to allow more if needed.

### Step 4 — Fetch PR data (GitHub)
```
gh pr view  <n> --repo <owner>/<repo> --json title,body,author,state,additions,deletions,changedFiles,baseRefName,headRefName,headRefOid
gh pr diff  <n> --repo <owner>/<repo>
```
- **Own-PR skip (`SKIP_OWN_PRS`):** compare the PR author (`.author.login`) to the
  gh-authenticated user (`gh api user -q .login`). If they match, this is YOUR own
  PR — **do not review it.** Post a one-line thread note ("Skipping — bot doesn't
  review its owner's PRs"), leave the `:eyes:`/`:white_check_mark:` so it isn't
  re-picked, and stop. The bot only reviews OTHER people's PRs.
- Capture `headRefOid` — inline comments MUST be anchored to this commit.
- If the diff is large, fetch changed-file contents at `headRefOid` as needed to
  compute exact line numbers (see references/github-review.md).
- Enforce `REPO_ALLOWLIST` here; if the repo isn't allowed, reply in-thread that it
  was skipped and stop.

### Step 5 — Review across the five vectors
Analyze the diff (and surrounding code where needed) against all five. This is an
IaC / Entra ID bot, so weight security and architecture heavily.

1. **Code base** — syntax, clean-code standards, formatting, dead code,
   obvious optimizations.
2. **Security base** — hardcoded secrets/credentials, overly permissive IAM /
   Entra ID roles or app permissions (wildcards, `Owner`/`Contributor` at wide
   scope, `Directory.ReadWrite.All`, consent grants), public exposure, missing
   encryption, injection/SSRF, unpinned dependencies.
3. **Architecture base** — alignment with the org's established patterns
   (module structure, naming, tagging, network topology, state management).
   Flag drift from convention, not personal preference.
4. **Test base** — are tests added/updated/accounted for? Untested new logic,
   deleted tests, assertions that don't actually exercise the change.
5. **Specification matching** — cross-reference the triggering **Slack message
   description** and any linked SOW / spec / ticket against the **PR title +
   description** and the **actual diff**. Flag drift: work described but not done,
   done but not described, or scope creep beyond the stated intent.

### Step 6 — Apply the reliability guardrail (BEFORE posting)
> ⚠️ **Do not post low-confidence or filler comments.** For each candidate
> finding, ask: *"Would this survive a skeptical senior engineer, and can I cite
> the concrete failure or violation?"* Post a finding only if yes.
- Prefer **fewer, high-signal** comments. If a suggested fix is uncertain, phrase
  it as a question or drop it — never invent a line-anchored code fix you can't
  stand behind.
- Assign each surviving finding a severity:
  - **High** — critical bug, security vulnerability, or major architectural violation.
  - **Medium** — optimization, missing tests, or minor security risk.
  - **Low** — style, nitpick, or docs suggestion.
- If nothing meets the bar, that is a valid result: post a clean review with no
  inline comments and say so.

### Step 7 — Post the GitHub review (inline comments)
(Own PRs were already skipped in Step 4, so anything reaching here is someone
else's PR.) Post one review with all inline comments in a single API call. Each
comment body is prefixed with its severity, e.g. `**[High]** …`. See
`references/github-review.md` for the exact payload, line-anchoring rules, and the
Windows scratchpad-file gotcha. In short:
- Build a `reviews` payload: `commit_id` = `headRefOid`, `event` = `REVIEW_EVENT`,
  a short `body` summary (counts by severity + overall read), and a `comments[]`
  array of `{path, line, side:"RIGHT", body}`.
- Write it to a file in the scratchpad dir and POST with
  `gh api repos/<owner>/<repo>/pulls/<n>/reviews --method POST --input <file>`.

### Step 8 — Notify Slack + finalize the lock
- Reply **in the triggering message's thread** with
  `slack_send_message(channel_id="C0XXXXXXXXX", thread_ts=<candidate ts>, message=…)`.
  Setting `thread_ts` keeps it in-thread; leave `reply_broadcast` unset.
  Message: `"✅ Automated review posted: N High, N Medium, N Low — <review html_url>"`.
  (Own PRs never reach this step — they were skipped in Step 4.)
- Mark done: `slack_add_reaction(channel_id="C0XXXXXXXXX", message_ts=<ts>,
  emoji="white_check_mark")` so the channel can tell "in progress" from "done".
  Leave the `eyes` reaction in place regardless — it is the permanent
  never-re-review lock.
- Note: `slack_send_message` posts directly (no draft/approval step). That is
  intended for an autonomous bot; if you want a human to approve each Slack post,
  switch this to `slack_send_message_draft`.

### Step 9 — Report the pass
Emit a compact summary of what the pass did (PR reviewed, findings by severity,
Slack thread updated) or "no eligible PRs this pass."

---

## Failure handling
- **Any step fails after the claim (Step 3):** post a Slack thread reply that the
  automated review errored and needs a human, and **leave `CLAIM_EMOJI` on** so the
  bot doesn't thrash retrying a broken PR every tick. Include the error.
- **SLA exceeded on one PR:** post the confirmed findings you have, reply in-thread
  that the review was truncated for time, and stop.
- **Slack unavailable:** see Prerequisites — stop cleanly, don't half-review.

---

## Manual / GitHub-only mode
If invoked with a PR URL directly (`/pr-review-bot <github-pr-url>`), skip Steps
1–3 and 8 (no Slack). Do Steps 4–7 and print the summary. This is the path that
works today without the Slack connector, and it's how the bot was validated on
<repo-a> PRs #16 and #20.

---

## Running it as a loop
This skill is one pass. Drive repetition with one of:

- **Interactive polling loop** (foreground session):
  `/loop 5m /pr-review-bot`  → runs a pass every 5 minutes. Omit the interval to
  let the model self-pace. Stop with the loop's stop control.
- **Unattended scheduled agent** (recommended for real operation): use the
  `schedule` skill / a cron routine to run `/pr-review-bot` every 5 minutes. This
  survives without an open terminal. Pick 5 min to stay within the SLA and the
  provider cache window.

Keep passes idempotent (the `:eyes:` guard) so overlapping runs are harmless.
