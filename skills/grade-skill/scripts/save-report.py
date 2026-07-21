#!/usr/bin/env python
"""save-report.py — persist a grading report from a structured assessment.

The LLM produces a compact *assessment* JSON (12 category scores + issues +
short prose fields). This script does all deterministic work: validates the
input, computes design_quality / overall_score / severity counts / scoring
mode, timestamps, and writes three artifacts:

    <root>/<skill>/latest.json           machine-readable interface
    <root>/<skill>/latest.md             human-readable report
    <root>/<skill>/history/<ts>.json     immutable historical copy

This keeps the LLM out of arithmetic and markdown table formatting.

Usage:
    python save-report.py <assessment.json | -> [--reports-root DIR] [--quiet]

Reads assessment from a file path or '-' (stdin). Prints a JSON summary
(paths + computed scores) to stdout.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402


def _fail(msg: str) -> int:
    print(C.dump_json({"error": msg}))
    return 1


def compute_scores(assessment: dict) -> dict:
    scores = assessment.get("scores") or {}
    missing = [k for k in C.CATEGORY_KEYS if k not in scores]
    if missing:
        raise ValueError(f"assessment.scores is missing categories: {missing}")
    bad = []
    for k in C.CATEGORY_KEYS:
        v = scores[k]
        if not isinstance(v, (int, float)) or not (0 <= v <= 10):
            bad.append(f"{k}={v!r}")
    if bad:
        raise ValueError(f"scores must be numbers in 0..10; bad: {bad}")

    total = sum(float(scores[k]) for k in C.CATEGORY_KEYS)
    design_quality = round(total / 120.0 * 100.0, 1)

    behavioral = assessment.get("behavioral_reliability")
    if behavioral is not None:
        if not isinstance(behavioral, (int, float)) or not (0 <= behavioral <= 100):
            raise ValueError("behavioral_reliability must be 0..100 or null")
        overall = round(C.DESIGN_WEIGHT * design_quality
                        + C.BEHAVIORAL_WEIGHT * float(behavioral), 1)
        mode = "static+behavioral"
    else:
        overall = design_quality
        mode = "static-analysis"

    return {
        "design_quality": design_quality,
        "behavioral_reliability": behavioral,
        "overall_score": overall,
        "scoring_mode": mode,
    }


def severity_counts(issues: list[dict]) -> dict:
    counts = {s: 0 for s in C.SEVERITIES}
    for it in issues or []:
        sev = str(it.get("severity", "")).upper()
        if sev in counts:
            counts[sev] += 1
    return counts


def build_report(assessment: dict) -> dict:
    computed = compute_scores(assessment)
    issues = assessment.get("issues") or []
    conf = str(assessment.get("confidence", "")).upper()
    if conf not in C.CONFIDENCE_LEVELS:
        conf = "MEDIUM"

    report = {
        "schema_version": C.REPORT_SCHEMA_VERSION,
        "grader_version": C.GRADER_VERSION,
        "skill": assessment.get("skill"),
        "skill_path": assessment.get("skill_path"),
        "evaluated_at": C.iso_now(),
        "scoring_mode": computed["scoring_mode"],
        "overall_score": computed["overall_score"],
        "design_quality": computed["design_quality"],
        "behavioral_reliability": computed["behavioral_reliability"],
        "confidence": conf,
        "recommendation": assessment.get("recommendation", ""),
        "scores": {k: assessment["scores"][k] for k in C.CATEGORY_KEYS},
        "severity_counts": severity_counts(issues),
        "issues": issues,
        "strengths": assessment.get("strengths", []),
        "ambiguities": assessment.get("ambiguities", []),
        "missing_instructions": assessment.get("missing_instructions", []),
        "conflicting_instructions": assessment.get("conflicting_instructions", []),
        "edge_cases": assessment.get("edge_cases", []),
        "redundant_instructions": assessment.get("redundant_instructions", []),
        "top_improvements": assessment.get("top_improvements", []),
        "tests": assessment.get("tests"),
        # prose (kept in JSON so latest.md can be regenerated deterministically)
        "overall_assessment": assessment.get("overall_assessment", ""),
        "skill_contract": assessment.get("skill_contract", ""),
        "behavioral_evaluation": assessment.get("behavioral_evaluation", ""),
    }
    return report


# --------------------------------------------------------------------------- #
# Markdown rendering
# --------------------------------------------------------------------------- #
def _issue_block(it: dict) -> str:
    return (
        f"- **[{it.get('severity','?')}] {it.get('problem','(no title)')}**\n"
        f"  - Category: {it.get('category','-')}\n"
        f"  - Evidence type: {it.get('evidence_type','-')}\n"
        f"  - Why it matters: {it.get('why','-')}\n"
        f"  - Evidence: {it.get('evidence','-')}\n"
        f"  - Recommended fix: {it.get('fix','-')}"
    )


def _bullets(items) -> str:
    if not items:
        return "_None._"
    out = []
    for x in items:
        if isinstance(x, dict):
            out.append("- " + (x.get("text") or C.dump_json(x)))
        else:
            out.append(f"- {x}")
    return "\n".join(out)


def render_markdown(r: dict) -> str:
    L = []
    L.append(f"# Skill Evaluation — `{r['skill']}`")
    L.append("")
    mode_label = ("STATIC-ANALYSIS SCORE (no behavioral tests run)"
                  if r["scoring_mode"] == "static-analysis"
                  else "STATIC + BEHAVIORAL SCORE")
    L.append(f"> **{mode_label}**")
    L.append("")
    L.append(f"- **Overall score:** {r['overall_score']} / 100")
    L.append(f"- **Design quality:** {r['design_quality']} / 100")
    br = r["behavioral_reliability"]
    L.append(f"- **Behavioral reliability:** {br if br is not None else 'n/a'}"
             + ("/ 100" if br is not None else ""))
    L.append(f"- **Confidence:** {r['confidence']}")
    L.append(f"- **Evaluated at:** {r['evaluated_at']}")
    sc = r["severity_counts"]
    L.append(f"- **Issues:** {sc['P0']} P0 · {sc['P1']} P1 · {sc['P2']} P2 · {sc['P3']} P3")
    L.append("")

    L.append("## Overall Assessment")
    L.append(r.get("overall_assessment") or "_Not provided._")
    L.append("")

    L.append("## Skill Contract")
    L.append(r.get("skill_contract") or "_Not provided._")
    L.append("")

    L.append("## Scorecard")
    L.append("")
    L.append("| # | Category | Score |")
    L.append("|---|----------|:-----:|")
    for i, (k, label) in enumerate(C.CATEGORIES, 1):
        L.append(f"| {i} | {label} | {r['scores'][k]}/10 |")
    L.append(f"| | **Design Quality (sum/120×100)** | **{r['design_quality']}** |")
    L.append("")

    L.append("## Behavioral Evaluation")
    if r["tests"]:
        t = r["tests"]
        L.append(f"- Tests: **{t.get('passed','?')}/{t.get('total','?')} passed** "
                 f"(pass rate {t.get('pass_rate','?')})")
        if t.get("skipped"):
            L.append(f"- Skipped (require an LLM / manual run): {t.get('skipped')}")
    else:
        L.append("_No behavioral tests were run. Score above is static-analysis only._")
    if r.get("behavioral_evaluation"):
        L.append("")
        L.append(r["behavioral_evaluation"])
    L.append("")

    L.append("## Strengths")
    L.append(_bullets(r["strengths"]))
    L.append("")

    p0p1 = [it for it in r["issues"] if str(it.get("severity")).upper() in ("P0", "P1")]
    p2p3 = [it for it in r["issues"] if str(it.get("severity")).upper() in ("P2", "P3")]

    L.append("## Critical Issues (P0/P1)")
    L.append("\n\n".join(_issue_block(it) for it in p0p1) if p0p1 else "_None._")
    L.append("")

    L.append("## Other Issues (P2/P3)")
    L.append("\n\n".join(_issue_block(it) for it in p2p3) if p2p3 else "_None._")
    L.append("")

    L.append("## Ambiguities")
    L.append(_bullets(r["ambiguities"]))
    L.append("")
    L.append("## Missing Instructions")
    L.append(_bullets(r["missing_instructions"]))
    L.append("")
    L.append("## Conflicting Instructions")
    L.append(_bullets(r["conflicting_instructions"]))
    L.append("")
    L.append("## Edge Cases")
    L.append(_bullets(r["edge_cases"]))
    L.append("")
    L.append("## Redundant Instructions")
    L.append(_bullets(r["redundant_instructions"]))
    L.append("")

    L.append("## Top 5 Improvements")
    if r["top_improvements"]:
        L.append("")
        L.append("| # | Improvement | Impact | Effort | Regression risk |")
        L.append("|---|-------------|--------|--------|-----------------|")
        for i, imp in enumerate(r["top_improvements"][:5], 1):
            L.append(f"| {i} | {imp.get('title','-')} | {imp.get('impact','-')} "
                     f"| {imp.get('effort','-')} | {imp.get('regression_risk','-')} |")
    else:
        L.append("_None._")
    L.append("")

    L.append("## Recommended Next Step")
    L.append(r.get("recommendation") or "_Not provided._")
    L.append("")
    L.append(f"## Confidence Level\n{r['confidence']}")
    L.append("")
    L.append(f"---\n_Generated by grade-skill v{C.GRADER_VERSION} "
             f"(schema {C.REPORT_SCHEMA_VERSION})._")
    return "\n".join(L) + "\n"


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    root = None
    if "--reports-root" in argv:
        i = argv.index("--reports-root")
        if i + 1 < len(argv):
            root = argv[i + 1]
    if not args:
        return _fail("usage: save-report.py <assessment.json|-> [--reports-root DIR]")

    try:
        assessment = C.read_json_arg(args[0])
    except Exception as e:
        return _fail(f"could not read assessment JSON: {e}")

    skill = assessment.get("skill")
    if not skill:
        return _fail("assessment JSON must include 'skill' (the skill name).")

    try:
        report = build_report(assessment)
    except ValueError as e:
        return _fail(str(e))

    rdir = C.report_dir(skill, root)
    hist = rdir / "history"
    hist.mkdir(parents=True, exist_ok=True)

    latest_json = rdir / "latest.json"
    latest_md = rdir / "latest.md"
    hist_json = hist / f"{C.fs_timestamp()}.json"

    payload = C.dump_json(report)
    latest_json.write_text(payload, encoding="utf-8")
    hist_json.write_text(payload, encoding="utf-8")
    latest_md.write_text(render_markdown(report), encoding="utf-8")

    summary = {
        "saved": True,
        "skill": skill,
        "reports_dir": str(rdir),
        "latest_json": str(latest_json),
        "latest_md": str(latest_md),
        "history_json": str(hist_json),
        "overall_score": report["overall_score"],
        "design_quality": report["design_quality"],
        "behavioral_reliability": report["behavioral_reliability"],
        "scoring_mode": report["scoring_mode"],
        "severity_counts": report["severity_counts"],
    }
    if "--quiet" not in argv:
        print(C.dump_json(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
