# Grading rubric — the 12 categories

Read this before scoring so grades are calibrated and repeatable across runs.
Each category is scored 0-10 on the shared scale:

`0-2` Critical deficiency · `3-4` Poor · `5-6` Adequate · `7-8` Good ·
`9` Excellent · `10` Exceptional

For every category, anchor the score to **evidence in the skill**, not to a
generic ideal. Grade the skill for *its own stated purpose*.

---

### 1. Purpose clarity
Is it unambiguous what the skill is for and when it should fire?
- **9-10**: One-sentence purpose obvious from the description; trigger conditions
  crisp; scope boundaries stated ("does X, explicitly not Y").
- **5-6**: Purpose inferable but the description is vague or overloaded.
- **0-2**: Missing/empty description, or purpose contradicts the body.

### 2. Instruction clarity
Can a competent agent follow the steps without guessing?
- **9-10**: Numbered, ordered, imperative steps; no undefined terms; each step
  has a clear actor and action.
- **5-6**: Mostly clear but some steps are prose blobs or assume context.
- **0-2**: Stream-of-consciousness; steps you cannot execute as written.

### 3. Instruction completeness
Are all steps needed to fulfill the contract present?
- **9-10**: Full happy path plus setup/prereqs and teardown; no "and then somehow".
- **5-6**: Happy path covered; setup or finalization steps implicit.
- **0-2**: Major gaps — key actions referenced but never specified.

### 4. Instruction consistency
Do the instructions agree with themselves and the frontmatter?
- **9-10**: No contradictions; terminology, tool names, and paths consistent
  throughout; body matches the description.
- **5-6**: Minor drift (a step reorders something stated earlier).
- **0-2**: Directly conflicting instructions, or body contradicts description.

### 5. Output specification
Is the produced artifact's shape/format/location defined?
- **9-10**: Explicit output contract — format, schema/fields, destination, and
  what "done" looks like.
- **5-6**: Output described in prose but not pinned (no schema, fuzzy location).
- **0-2**: No statement of what the skill produces.

### 6. Input handling
Are inputs, arguments, and their defaults/validation defined?
- **9-10**: Every input named with type, default, and how it's obtained (arg vs
  discovered vs prompted); invalid input handled.
- **5-6**: Inputs named but defaults/validation unclear.
- **0-2**: Inputs assumed; no argument contract.

### 7. Error and failure handling
Does it say what to do when steps fail?
- **9-10**: Named failure modes with explicit responses (retry, skip, fail loud,
  clean up); "fail loudly, don't half-do it" is stated where it matters.
- **5-6**: Some error handling; several failure paths unaddressed.
- **0-2**: No failure handling — silent failure or hang is possible.

### 8. Edge-case coverage
Are boundary conditions considered?
- **9-10**: Empty inputs, duplicates, concurrency, large inputs, missing
  resources, idempotency/re-run safety all addressed where relevant.
- **5-6**: Common cases handled; boundaries mostly unmentioned.
- **0-2**: Only the sunny-day path exists.

### 9. Tool and resource reliability
Do referenced tools/files/paths exist and are they used safely?
- **9-10**: All referenced files present (validate: no broken refs); tool
  availability checked before use; deterministic work delegated to scripts.
- **5-6**: Mostly fine; a fragile assumption about a tool/path.
- **0-2**: Broken references, or hard dependence on an unchecked tool.
  *(validate-skill.py findings are authoritative here.)*

### 10. Context efficiency
Does it use tokens/context economically?
- **9-10**: Lean SKILL.md; detail pushed to `references/` (progressive
  disclosure); deterministic work in scripts, not prose the model must execute.
- **5-6**: Serviceable but bloated or repetitive.
- **0-2**: Enormous monolithic prompt; the model must read everything every time.
  *(validate flags an oversized body.)*

### 11. Maintainability
Can someone safely change this skill in six months?
- **9-10**: Modular, well-labeled sections; config isolated; single source of
  truth for constants; comments/rationale where non-obvious.
- **5-6**: Understandable but changes risk unintended ripple.
- **0-2**: Tangled; magic values scattered; no structure.

### 12. Testability
Can its behavior be verified, ideally without an LLM?
- **9-10**: Ships deterministic tests (`tests/manifest.json`) or exposes a clear,
  checkable contract; bundled scripts are unit-testable.
- **5-6**: Testable in principle but nothing provided.
- **0-2**: Behavior only observable by full manual LLM runs; no contract to assert.

---

## Evidence discipline (applies to every issue you raise)

| Evidence type | Means | Use when |
|---------------|-------|----------|
| `OBSERVED` | You saw it happen | A test failed; validate confirmed a broken ref; a run misbehaved. |
| `DOCUMENTED` | The text says/omits it | The SKILL.md itself states or clearly lacks something. |
| `INFERRED` | Reasoned risk | Design implies a failure you have not triggered. |
| `HYPOTHETICAL` | Unsubstantiated risk | A possibility you cannot back with evidence — label it plainly. |

- Prefer OBSERVED/DOCUMENTED. Do not present INFERRED/HYPOTHETICAL as fact.
- Do not invent requirements outside the skill's purpose.
- Separate *design quality* (this rubric) from *behavioral reliability* (tests).
