#!/usr/bin/env python
"""score-results.py — turn test results into a behavioral score.

Deterministically maps run-tests.py output to a behavioral_reliability number
(0..100) and a compact `tests` block ready to embed in the grading assessment.
Optionally merges those two fields into an existing assessment JSON so the LLM
never has to compute or copy them.

Usage:
    python score-results.py <test-results.json | -> [--into assessment.json]

Prints JSON: {behavioral_reliability, tests:{...}} (or the merged assessment
when --into is used).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402


def score(results: dict) -> dict:
    total = results.get("total") or 0
    passed = results.get("passed") or 0
    pass_rate = results.get("pass_rate")
    if pass_rate is None and total:
        pass_rate = round(passed / total, 4)
    behavioral = round(pass_rate * 100, 1) if pass_rate is not None else None
    tests_block = {
        "total": total,
        "passed": passed,
        "failed": results.get("failed", 0),
        "skipped": results.get("skipped", 0),
        "pass_rate": pass_rate,
    }
    return {"behavioral_reliability": behavioral, "tests": tests_block}


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        C.eprint("usage: score-results.py <test-results.json|-> [--into assessment.json]")
        return 1
    try:
        results = C.read_json_arg(args[0])
    except Exception as e:
        print(C.dump_json({"error": f"could not read results: {e}"}))
        return 1

    scored = score(results)

    if "--into" in argv:
        i = argv.index("--into")
        if i + 1 >= len(argv):
            print(C.dump_json({"error": "--into requires a path"}))
            return 1
        apath = Path(argv[i + 1])
        assessment = C.load_json(apath)
        assessment["behavioral_reliability"] = scored["behavioral_reliability"]
        assessment["tests"] = scored["tests"]
        apath.write_text(C.dump_json(assessment), encoding="utf-8")
        print(C.dump_json({"merged_into": str(apath), **scored}))
        return 0

    print(C.dump_json(scored))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
