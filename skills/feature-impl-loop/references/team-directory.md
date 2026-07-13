# Team directory — Slack tagging without wide-channel pings

Goal (Phase 4): tag **only the active contributors for the ticket's project**, never
`@channel`/`@here`, never the whole team.

## Resolution order

1. **Determine who to tag** — source = **top committers on the PR's repo** (user's
   choice), NOT Plane project members. Rank the repo's contributors by commit count
   and take the top `TOP_N` (default 3), excluding bots:
   - `gh api repos/{owner}/{repo}/contributors --paginate -q '.[].login'`
     (GitHub returns contributors already sorted by contributions, descending), or
   - `git -C <repo-or-worktree> shortlog -sne` (commit counts per author).
   These give **GitHub logins / author emails** → map to Slack IDs in step 3.
   Fall back to the static `PROJECT_CONTRIBUTORS` map only if the repo lookup fails.
2. **ALWAYS also tag `@Assistant Bot` (`U0ASSISTANTBOT`) on every PR** — standing
   instruction, regardless of the committer ranking. Add it to the tag set every time.
3. **Map each person → Slack user ID** via `IDENTITY_MAP` below (exact, no guessing).
   The key lookup here is **GitHub login → Slack ID** (that's what the committer
   list gives). If someone isn't in the map, resolve once with
   `slack_search_users(query="<full name or email>")`, then **add them to this file**
   so the map stays authoritative and we don't re-query.
4. **Tag** by building `<@SLACKID>` mentions for the resolved set (top committers +
   always-on `U0ASSISTANTBOT`). Never expand beyond this to a broad ping.

## IDENTITY_MAP (verified from #your-review-channel, 2026-07-13)

| Person | Email | Slack ID | GitHub login |
|--------|-------|----------|--------------|
| Owner | sushama@example.com | `U0OWNER` | your-org (verify) |
| Contributor One | alden@example.com | `U0MEMBER1` | contributor-one |
| Contributor Two | sourab@example.com | `U0MEMBER2` | (verify) |
| Contributor Three | prastut@example.com | `U0MEMBER3` | (verify) |
| Contributor Four | muskan@example.com | `U0MEMBER4` | (verify) |
| Contributor Five | — | `U0MEMBER5` | (verify) |
| Assistant Bot (bot) | — | `U0ASSISTANTBOT` | — (exclude from tags) |
| Claude (bot) | — | `U0CLAUDEBOT` | — (exclude from tags) |

**GitHub login → Slack ID** is the mapping actually needed to tag the PR author +
GitHub reviewers. Only `contributor-one` is confirmed so far; fill the rest by running
`gh pr view <n> --json author,reviewRequests` and matching names, then record here.

## PROJECT_CONTRIBUTORS (static fallback, edit to taste)

Until Plane project-member lookup is wired, tag by repo/project:

| Project / repo | Contributors to tag (Slack IDs) |
|----------------|---------------------------------|
| `<repo-a>` | Muskan `U0MEMBER4`, Prastut `U0MEMBER3`, Alden `U0MEMBER1`, Justin `U0MEMBER5` |
| `<repo-b>` | Sourab `U0MEMBER2`, Alden `U0MEMBER1`, Owner `U0OWNER` |

> These are seeded from who has been posting/reviewing each repo's PRs in the
> channel — CONFIRM with the user before relying on them for real pings.

## Never
- Never `@channel` / `@here` / `@everyone`.
- Never tag the Claude bot account (`U0CLAUDEBOT`).
- **Exception:** `@Assistant Bot` (`U0ASSISTANTBOT`) IS always tagged on every PR
  (standing instruction) — it is the one bot-style account that is intentionally pinged.
- Never expand the tag set beyond {top committers} + {Assistant Bot}.
