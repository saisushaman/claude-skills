#!/usr/bin/env python
"""run-tests.py — run a skill's deterministic behavioral tests.

Behavioral reliability of a *skill* (which is a prompt) can only be measured
deterministically for the parts that are deterministic — typically the helper
scripts/tools the skill bundles, or command-level contracts. This runner
executes those and reports honest pass/fail. Tests that genuinely need an LLM
or a human are declared `type: "manual"` and are SKIPPED, never counted as
passed — so the tool never claims tests ran when they did not.

Test manifest: <skill>/tests/manifest.json
    {
      "version": "1.0",
      "tests": [
        {"id":"...", "type":"command",
         "argv":["{python}","{skill_dir}/scripts/validate-skill.py","{skill_dir}"],
         "expect_exit":0,
         "expect_stdout_contains":["\"ok\": true"],
         "expect_stdout_not_contains":["ERROR"],
         "timeout":30},
        {"id":"...", "type":"manual", "description":"needs human/LLM"}
      ]
    }

Placeholders substituted in argv/cwd: {python} {skill_dir} {scripts} {tests}
{fixtures} {reports_root}.

Usage:
    python run-tests.py <skill-name-or-path> [--reports-root DIR] [--json]

Exit code: 0 if all executed tests pass (or none exist), 1 if any fail.
Always prints a JSON results object to stdout (unless suppressed).
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402


def substitute(value: str, ctx: dict) -> str:
    for k, v in ctx.items():
        value = value.replace("{" + k + "}", str(v))
    return value


def run_command_test(test: dict, ctx: dict) -> dict:
    argv = [substitute(a, ctx) for a in test.get("argv", [])]
    if not argv:
        return {"id": test.get("id"), "status": "fail",
                "reason": "command test has empty argv"}
    cwd = substitute(test.get("cwd", "{skill_dir}"), ctx)
    timeout = test.get("timeout", 60)
    try:
        proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                              timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"id": test.get("id"), "status": "fail",
                "reason": f"timed out after {timeout}s", "argv": argv}
    except Exception as e:
        return {"id": test.get("id"), "status": "fail",
                "reason": f"could not run: {e}", "argv": argv}

    reasons = []
    exp_exit = test.get("expect_exit", 0)
    if exp_exit is not None and proc.returncode != exp_exit:
        reasons.append(f"exit {proc.returncode} != expected {exp_exit}")
    out = proc.stdout
    for needle in test.get("expect_stdout_contains", []):
        if substitute(needle, ctx) not in out:
            reasons.append(f"stdout missing: {needle!r}")
    for needle in test.get("expect_stdout_not_contains", []):
        if substitute(needle, ctx) in out:
            reasons.append(f"stdout unexpectedly contains: {needle!r}")
    rx = test.get("expect_stdout_regex")
    if rx and not re.search(rx, out):
        reasons.append(f"stdout does not match /{rx}/")

    status = "pass" if not reasons else "fail"
    res = {"id": test.get("id"), "status": status, "exit": proc.returncode}
    if reasons:
        res["reason"] = "; ".join(reasons)
        res["stdout_tail"] = out[-400:]
        res["stderr_tail"] = proc.stderr[-400:]
    return res


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    root = None
    if "--reports-root" in argv:
        i = argv.index("--reports-root")
        if i + 1 < len(argv):
            root = argv[i + 1]
    if not args:
        C.eprint("usage: run-tests.py <skill-name-or-path> [--reports-root DIR]")
        return 1
    try:
        skill_dir = C.find_skill(args[0])
    except FileNotFoundError as e:
        print(C.dump_json({"error": str(e)}))
        return 1

    manifest_path = skill_dir / "tests" / "manifest.json"
    name = C.parse_frontmatter(C.read_text(skill_dir / "SKILL.md")).get("name", skill_dir.name)

    if not manifest_path.exists():
        out = {"skill": name, "manifest": None, "total": 0, "passed": 0,
               "failed": 0, "skipped": 0, "pass_rate": None,
               "note": "no tests/manifest.json — no deterministic behavioral tests",
               "results": []}
        if "--json" in argv or True:
            print(C.dump_json(out))
        return 0

    manifest = C.load_json(manifest_path)
    ctx = {
        "python": sys.executable or "python",
        "skill_dir": str(skill_dir),
        "scripts": str(skill_dir / "scripts"),
        "tests": str(skill_dir / "tests"),
        "fixtures": str(skill_dir / "tests" / "fixtures"),
        "reports_root": str(C.reports_root(root)),
    }

    results, passed, failed, skipped = [], 0, 0, 0
    for test in manifest.get("tests", []):
        ttype = test.get("type", "command")
        if ttype != "command":
            skipped += 1
            results.append({"id": test.get("id"), "status": "skipped",
                            "reason": f"type={ttype} (needs human/LLM)"})
            continue
        r = run_command_test(test, ctx)
        results.append(r)
        if r["status"] == "pass":
            passed += 1
        else:
            failed += 1

    executed = passed + failed
    pass_rate = round(passed / executed, 4) if executed else None
    out = {
        "skill": name,
        "manifest": str(manifest_path),
        "total": executed,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "pass_rate": pass_rate,
        "results": results,
    }
    print(C.dump_json(out))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
