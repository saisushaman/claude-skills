# Improvement playbook

Concrete, minimal edit patterns per issue category, plus the accept/reject
decision table. Goal: the **smallest** change that resolves a *verified* issue
without disturbing working behavior or bloating the prompt.

## Edit patterns by category

| Category | Typical fix (minimal) | Watch out for |
|----------|-----------------------|---------------|
| Purpose clarity | Tighten the frontmatter `description`; add a one-line scope boundary ("does X, not Y"). | Don't rewrite the whole intro; keep triggers that already route correctly. |
| Instruction clarity | Convert a prose blob into numbered imperative steps. | Don't reorder steps that have real dependencies. |
| Instruction completeness | Add the missing setup/teardown/prereq step only. | Don't pad the happy path with obvious filler. |
| Instruction consistency | Reconcile the contradiction to one source of truth; align body with description. | Fixing one side of a contradiction can strand a reference elsewhere — grep for it. |
| Output specification | Add an explicit output contract (format, fields, destination, "done" state). | Match what the skill actually produces today, not an aspiration. |
| Input handling | Name each input with default + how it's obtained; add invalid-input handling. | Don't invent inputs the skill doesn't take. |
| Error/failure handling | Add named failure modes with responses (retry/skip/fail-loud/cleanup). | Keep "fail loudly, don't half-do it" where partial state is dangerous. |
| Edge-case coverage | Add the specific boundary the issue cites (empty/dup/concurrency/idempotency). | Only cases relevant to the purpose; don't enumerate impossible ones. |
| Tool/resource reliability | Fix the broken reference / add a tool-availability check. | Re-run validate-skill.py to confirm the path resolves. |
| Context efficiency | Move detail into `references/`; delete redundancy; push determinism to a script. | Progressive disclosure, not deletion of needed instruction. |
| Maintainability | Isolate config/constants; label sections; single source of truth. | Refactors are high regression risk — keep them surgical. |
| Testability | Add a deterministic `tests/manifest.json` command test for a bundled script/contract. | Don't fake behavioral coverage for pure-prose logic. |

## Deterministic-vs-reasoning check for every proposed edit
Before editing, ask: *is this issue mechanical?* If a script already proves or
disproves it (broken refs, frontmatter, oversized body via `validate-skill.py`),
let the script confirm — don't argue it in prose. Spend edits on the reasoning
gaps: ambiguity, missing behavior, weak contracts, unhandled failure.

## Accept / reject decision table (mirrors compare-reports.py)

| Situation | Verdict |
|-----------|---------|
| Behavioral reliability drops > 2 pts | **REJECT** (behavioral regression is serious) |
| Test pass rate drops | **REJECT** |
| Any P0 or P1 count increases | **REJECT** |
| Behavioral improves ≥ 2, or P0/P1 reduced, no regressions | **ACCEPT** |
| Only design score moved, behavior unchanged/untested, no new P0/P1 | **ACCEPT** if P-counts improved, else **NEUTRAL** |
| No net movement | **NEUTRAL** — reconsider whether the edit was worth it |

Rules of thumb:
- A higher design score **never** overrides a behavioral regression.
- NEUTRAL means "did no harm but proved no gain" — prefer to either strengthen
  the change into a real improvement or revert it to avoid churn.
- On REJECT: revert the edit (git) or rework it; re-run Step 6-7 before shipping.

## Writing the improvement report
Keep it to the six headings from the SKILL (`Changes made`, `Problems fixed`,
`Problems intentionally not fixed`, `Regression risks`, `Recommended tests`,
`Verdict`). Reference issues by their `problem`/severity from latest.json so the
report ties back to the grade. Cite the compare-reports before/after metrics as
the objective evidence.
