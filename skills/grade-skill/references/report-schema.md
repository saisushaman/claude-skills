# Report schema — the machine interface between grade and improve

Two artifacts per grade, both under `<reports-root>/<skill>/`
(default `~/.claude/skill-reports/<skill>/`):

- `latest.json` — the compact, machine-readable report. **This is the interface
  `/improve-skill` reads first.**
- `latest.md` — the full human-readable report, rendered from the same data.
- `history/<timestamp>.json` — an immutable copy for version comparison.

You (the grader) produce the **assessment** object below. `save-report.py`
consumes it and computes the derived fields, so keep it compact.

## Assessment object (grader output -> save-report.py input)

```json
{
  "skill": "<skill-name>",                     // required
  "skill_path": "<abs path to skill dir>",     // optional (from discover)
  "confidence": "HIGH | MEDIUM | LOW",
  "recommendation": "<one-line next step>",
  "overall_assessment": "<2-4 sentence prose>",
  "skill_contract": "<given X, produce Y with guarantees Z>",
  "behavioral_evaluation": "<prose; optional, only if tests ran>",

  "scores": {                                  // required; each integer 0..10
    "purpose_clarity": 0,
    "instruction_clarity": 0,
    "instruction_completeness": 0,
    "instruction_consistency": 0,
    "output_specification": 0,
    "input_handling": 0,
    "error_handling": 0,
    "edge_case_coverage": 0,
    "tool_resource_reliability": 0,
    "context_efficiency": 0,
    "maintainability": 0,
    "testability": 0
  },

  "behavioral_reliability": null,              // 0..100, or null if no tests ran
  "tests": null,                               // or {total,passed,failed,skipped,pass_rate}

  "issues": [
    {
      "severity": "P0 | P1 | P2 | P3",
      "category": "<one of the 12 category keys>",
      "evidence_type": "OBSERVED | DOCUMENTED | INFERRED | HYPOTHETICAL",
      "problem": "<short title>",
      "why": "<why it matters>",
      "evidence": "<concrete citation: line, quote, validate finding, test id>",
      "fix": "<recommended change>"
    }
  ],

  "strengths": ["..."],
  "ambiguities": ["..."],
  "missing_instructions": ["..."],
  "conflicting_instructions": ["..."],
  "edge_cases": ["..."],
  "redundant_instructions": ["..."],
  "top_improvements": [
    {"title": "...", "impact": "High|Medium|Low",
     "effort": "High|Medium|Low", "regression_risk": "High|Medium|Low"}
  ]
}
```

### What save-report.py adds (do NOT compute these yourself)
- `design_quality` = round(sum(scores)/120×100, 1)
- `overall_score` = `design_quality` if `behavioral_reliability` is null, else
  round(0.40×design + 0.60×behavioral, 1)
- `scoring_mode` = `"static-analysis"` or `"static+behavioral"`
- `severity_counts` = {P0,P1,P2,P3}
- `evaluated_at`, `schema_version`, `grader_version`
- The rendered `latest.md`

### Persisted report (latest.json) — extra top-level keys
Everything from the assessment (prose kept so latest.md can be regenerated) plus
the computed fields above. `/improve-skill` reads: `overall_score`,
`design_quality`, `behavioral_reliability`, `severity_counts`, `issues`,
`top_improvements`, `recommendation`, `confidence`.

## Minimum contract (as required by spec)
`latest.json` always contains at least:
`skill`, `evaluated_at`, `overall_score`, `design_quality`,
`behavioral_reliability`, `confidence`, `recommendation`, `issues`, `strengths`,
`top_improvements`.
