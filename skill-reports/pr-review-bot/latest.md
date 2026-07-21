# Skill Evaluation — `pr-review-bot`

> **STATIC-ANALYSIS SCORE (no behavioral tests run)**

- **Overall score:** 80.8 / 100
- **Design quality:** 80.8 / 100
- **Behavioral reliability:** n/a
- **Confidence:** MEDIUM
- **Evaluated at:** 2026-07-21T20:05:06Z
- **Issues:** 0 P0 · 0 P1 · 2 P2 · 1 P3

## Overall Assessment
A mature, carefully-scoped single-pass skill. Its standout qualities are edge-case handling (idempotency via the :eyes: lock, debounce race, own-PR skip, SLA truncation) and explicit failure handling. The main weakness is testability: the flow is only verifiable by manual end-to-end runs, and no deterministic tests or documented manual protocol are bundled. Scoring is static-analysis only (no behavioral tests exist), so treat the number as a design-quality read.

## Skill Contract
Given one polling pass over a single configured Slack channel, find at most one eligible PR (PR URL + review keyword + required tag, not already :eyes:-claimed), review its diff across five vectors, post one severity-tagged GitHub review, reply in the Slack thread, and mark done — idempotently, within the SLA, never reviewing its own PRs and never APPROVE/REQUEST_CHANGES.

## Scorecard

| # | Category | Score |
|---|----------|:-----:|
| 1 | Purpose clarity | 9/10 |
| 2 | Instruction clarity | 9/10 |
| 3 | Instruction completeness | 9/10 |
| 4 | Instruction consistency | 8/10 |
| 5 | Output specification | 8/10 |
| 6 | Input handling | 8/10 |
| 7 | Error and failure handling | 8/10 |
| 8 | Edge-case coverage | 9/10 |
| 9 | Tool and resource reliability | 9/10 |
| 10 | Context efficiency | 7/10 |
| 11 | Maintainability | 8/10 |
| 12 | Testability | 5/10 |
| | **Design Quality (sum/120×100)** | **80.8** |

## Behavioral Evaluation
_No behavioral tests were run. Score above is static-analysis only._

## Strengths
- Idempotency is designed in: the :eyes: reaction is a single authoritative never-re-review lock.
- Concurrency/races handled explicitly (debounce-then-recheck, duplicate-reaction guard).
- Strong safety posture: own-PR skip, COMMENT-only reviews, never APPROVE/REQUEST_CHANGES.
- Dedicated failure-handling section with fail-loud, claim-retention, and SLA truncation.
- Config isolated in a single table at the top with defaults and arg overrides.

## Critical Issues (P0/P1)
_None._

## Other Issues (P2/P3)
- **[P2] No deterministic tests or documented manual test protocol are bundled**
  - Category: testability
  - Evidence type: DOCUMENTED
  - Why it matters: The nine-step Slack+GitHub flow can silently regress; the only stated validation is two example PRs (#16, #20), which is not repeatable coverage.
  - Evidence: discover-skill.py reports test_file_count=0 and no tests/ dir; SKILL.md 'Manual / GitHub-only mode' references past runs but no re-runnable protocol.
  - Recommended fix: Add a tests/manifest.json with command tests for any extracted helper (e.g. eligibility/URL-parsing), or at minimum a written manual smoke protocol (a fixture PR + expected review shape) so a change can be re-verified.

- **[P2] SKILL.md carries operational detail that could move to references/**
  - Category: context_efficiency
  - Evidence type: INFERRED
  - Why it matters: At ~1880 words the model re-reads the full payload/line-anchoring narrative each invocation; some of it duplicates references/github-review.md.
  - Evidence: discover-skill.py reports skill_md_words=1880 with a single references file; Steps 6-7 restate posting mechanics also covered in the reference.
  - Recommended fix: Trim Steps 6-7 to the decision rules and defer the exact payload/formatting mechanics to references/github-review.md (progressive disclosure).

- **[P3] Hardcoded example Slack MCP server id can go stale**
  - Category: tool_resource_reliability
  - Evidence type: DOCUMENTED
  - Why it matters: A stale id in prose can mislead, though the skill already documents re-discovery via ToolSearch.
  - Evidence: Prerequisites note the id 'can change if the connector is re-authorized' yet still print a concrete placeholder id.
  - Recommended fix: Lead with the ToolSearch re-discovery instruction and mark the concrete id as example-only, so the fallback is the primary path.

## Ambiguities
- 'target ~10 min, 15 hard ceiling' SLA is stated but there is no instruction on how to measure elapsed time within a pass.

## Missing Instructions
- No re-runnable test/verification protocol (see the P2 testability issue).

## Conflicting Instructions
_None._

## Edge Cases
- Handled: empty channel history, already-:eyes:'d messages, own PRs, large diffs, repo not in allowlist, concurrent runners.
- Under-specified: what to do if the same PR URL appears in two eligible messages in one pass.

## Redundant Instructions
- Posting mechanics in Steps 6-7 partially duplicate references/github-review.md.

## Top 5 Improvements

| # | Improvement | Impact | Effort | Regression risk |
|---|-------------|--------|--------|-----------------|
| 1 | Add a re-runnable test/verification protocol (deterministic where possible) | High | Medium | Low |
| 2 | Move payload/formatting detail from Steps 6-7 into references/github-review.md | Medium | Low | Low |
| 3 | Make ToolSearch re-discovery the primary path; mark the Slack server id example-only | Low | Low | Low |
| 4 | Specify how elapsed time is tracked against the SLA | Low | Low | Low |
| 5 | Add a tie-break rule for duplicate PR URLs within one pass | Low | Low | Low |

## Recommended Next Step
Strong skill. Highest-value next step: add a lightweight deterministic test protocol (or bundle a small helper + command tests) to lift Testability from 5, then run /improve-skill pr-review-bot against this report.

## Confidence Level
MEDIUM

---
_Generated by grade-skill v1.0 (schema 1.0)._
