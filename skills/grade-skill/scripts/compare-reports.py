#!/usr/bin/env python
"""compare-reports.py — deterministic before/after verdict.

Compares two report JSONs (as written by save-report.py) and renders an
ACCEPT / REJECT / NEUTRAL verdict. The rules encode the core design principle:
a rise in design score NEVER excuses a behavioral regression, and new critical
issues are a hard fail.

Usage:
    python compare-reports.py <old.json> <new.json> [--json]

Exit codes: 0 ACCEPT, 1 REJECT, 2 NEUTRAL, 3 usage/error.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402

# Tolerances.
BEHAVIORAL_REGRESSION_TOL = 2.0   # behavioral drop beyond this = REJECT
BEHAVIORAL_IMPROVE_MIN = 2.0      # behavioral gain of at least this = strong ACCEPT
OVERALL_REGRESSION_TOL = 1.0      # overall drop beyond this counts against ACCEPT
PASS_RATE_TOL = 0.001


def _metric(report: dict, key: str):
    return report.get(key)


def _tests_pass_rate(report: dict):
    t = report.get("tests")
    if isinstance(t, dict):
        return t.get("pass_rate")
    return None


def compare(old: dict, new: dict) -> dict:
    signals = []       # human-readable reasons
    reject = False
    accept_points = 0

    o_over = _metric(old, "overall_score")
    n_over = _metric(new, "overall_score")
    o_des = _metric(old, "design_quality")
    n_des = _metric(new, "design_quality")
    o_beh = _metric(old, "behavioral_reliability")
    n_beh = _metric(new, "behavioral_reliability")
    o_sev = old.get("severity_counts", {}) or {}
    n_sev = new.get("severity_counts", {}) or {}
    o_pr = _tests_pass_rate(old)
    n_pr = _tests_pass_rate(new)

    # --- Hard-fail: behavioral regression (only meaningful if both measured) ---
    if o_beh is not None and n_beh is not None:
        delta = n_beh - o_beh
        if delta < -BEHAVIORAL_REGRESSION_TOL:
            reject = True
            signals.append(
                f"REJECT: behavioral reliability regressed {o_beh}->{n_beh} "
                f"({delta:+.1f}); behavioral regression is a serious failure.")
        elif delta >= BEHAVIORAL_IMPROVE_MIN:
            accept_points += 2
            signals.append(f"behavioral reliability improved {o_beh}->{n_beh} ({delta:+.1f}).")
        else:
            signals.append(f"behavioral reliability ~flat {o_beh}->{n_beh} ({delta:+.1f}).")

    # --- Hard-fail: pass-rate regression ---
    if o_pr is not None and n_pr is not None:
        if n_pr < o_pr - PASS_RATE_TOL:
            reject = True
            signals.append(f"REJECT: test pass rate regressed {o_pr}->{n_pr}.")
        elif n_pr > o_pr + PASS_RATE_TOL:
            accept_points += 1
            signals.append(f"test pass rate improved {o_pr}->{n_pr}.")

    # --- Hard-fail: new critical/high issues ---
    for sev in ("P0", "P1"):
        o_c, n_c = int(o_sev.get(sev, 0)), int(n_sev.get(sev, 0))
        if n_c > o_c:
            reject = True
            signals.append(f"REJECT: {sev} issue count increased {o_c}->{n_c}.")
        elif n_c < o_c:
            accept_points += 1
            signals.append(f"{sev} issues reduced {o_c}->{n_c}.")

    # --- Soft signals: P2, overall, design ---
    o_p2, n_p2 = int(o_sev.get("P2", 0)), int(n_sev.get("P2", 0))
    if n_p2 < o_p2:
        accept_points += 1
        signals.append(f"P2 issues reduced {o_p2}->{n_p2}.")
    elif n_p2 > o_p2:
        signals.append(f"note: P2 issues increased {o_p2}->{n_p2}.")

    if o_over is not None and n_over is not None:
        d = n_over - o_over
        if d < -OVERALL_REGRESSION_TOL:
            signals.append(f"note: overall score dropped {o_over}->{n_over} ({d:+.1f}).")
            accept_points -= 1
        elif d > OVERALL_REGRESSION_TOL:
            accept_points += 1
            signals.append(f"overall score improved {o_over}->{n_over} ({d:+.1f}).")

    if o_des is not None and n_des is not None and n_des != o_des:
        signals.append(f"design quality {o_des}->{n_des} ({n_des - o_des:+.1f}).")

    # --- Verdict ---
    if reject:
        verdict = "REJECT"
    elif accept_points > 0:
        verdict = "ACCEPT"
    else:
        verdict = "NEUTRAL"

    return {
        "verdict": verdict,
        "signals": signals,
        "metrics": {
            "overall_score": [o_over, n_over],
            "design_quality": [o_des, n_des],
            "behavioral_reliability": [o_beh, n_beh],
            "P0": [int(o_sev.get("P0", 0)), int(n_sev.get("P0", 0))],
            "P1": [int(o_sev.get("P1", 0)), int(n_sev.get("P1", 0))],
            "P2": [o_p2, n_p2],
            "test_pass_rate": [o_pr, n_pr],
        },
        "accept_points": accept_points,
    }


def render(cmp: dict, old: dict, new: dict) -> str:
    m = cmp["metrics"]
    L = []
    L.append(f"# Comparison — `{new.get('skill', old.get('skill','?'))}`")
    L.append("")
    L.append("| Metric | Before | After |")
    L.append("|--------|:------:|:-----:|")

    def row(label, pair):
        a, b = pair
        a = "n/a" if a is None else a
        b = "n/a" if b is None else b
        return f"| {label} | {a} | {b} |"

    L.append(row("Overall score", m["overall_score"]))
    L.append(row("Design quality", m["design_quality"]))
    L.append(row("Behavioral reliability", m["behavioral_reliability"]))
    L.append(row("P0 issues", m["P0"]))
    L.append(row("P1 issues", m["P1"]))
    L.append(row("P2 issues", m["P2"]))
    L.append(row("Test pass rate", m["test_pass_rate"]))
    L.append("")
    L.append("## Signals")
    for s in cmp["signals"]:
        L.append(f"- {s}")
    L.append("")
    L.append(f"## Verdict: **{cmp['verdict']}**")
    return "\n".join(L) + "\n"


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if len(args) < 2:
        C.eprint("usage: compare-reports.py <old.json> <new.json> [--json]")
        return 3
    try:
        old = C.load_json(Path(args[0]))
        new = C.load_json(Path(args[1]))
    except Exception as e:
        C.eprint(f"error reading reports: {e}")
        return 3

    cmp = compare(old, new)
    if "--json" in argv:
        print(C.dump_json(cmp))
    else:
        print(render(cmp, old, new))

    return {"ACCEPT": 0, "REJECT": 1, "NEUTRAL": 2}[cmp["verdict"]]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
