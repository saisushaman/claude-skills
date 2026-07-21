#!/usr/bin/env python
"""validate-skill.py — deterministic lint of a skill's structure.

Catches the mechanical defects an LLM should never spend tokens hunting for:
missing/invalid frontmatter, name/dir mismatch, over-long description, broken
file references, empty SKILL.md, oversized SKILL.md. Findings feed directly
into the grader's "Tool and resource reliability" and "Context efficiency"
categories as OBSERVED/DOCUMENTED evidence.

Usage:
    python validate-skill.py <skill-name-or-path>

Exit code: 0 if no ERROR-level findings, 1 if any ERROR, 2 on bad usage.
Always prints a JSON object to stdout.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402

# Anthropic's documented soft limits for skill frontmatter.
DESC_MAX = 1024
NAME_MAX = 64
SKILL_MD_WARN_WORDS = 5000  # progressive-disclosure smell above this


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        C.eprint("usage: validate-skill.py <skill-name-or-path>")
        return 2
    try:
        skill_dir = C.find_skill(args[0])
    except FileNotFoundError as e:
        print(C.dump_json({"error": str(e), "findings": [
            {"level": "ERROR", "code": "skill-not-found", "message": str(e)}]}))
        return 1

    findings: list[dict] = []

    def add(level, code, message):
        findings.append({"level": level, "code": code, "message": message})

    skill_md = skill_dir / "SKILL.md"
    text = C.read_text(skill_md)
    fm_text, body = C.split_frontmatter(text)
    meta = C.parse_frontmatter(text)

    # Frontmatter presence
    if fm_text is None:
        add("ERROR", "no-frontmatter", "SKILL.md has no YAML frontmatter block.")
    # name
    name = meta.get("name")
    if not name:
        add("ERROR", "missing-name", "Frontmatter is missing required `name`.")
    else:
        if name != skill_dir.name:
            add("WARN", "name-dir-mismatch",
                f"Frontmatter name '{name}' != directory '{skill_dir.name}'.")
        if len(name) > NAME_MAX:
            add("WARN", "name-too-long", f"name is {len(name)} chars (max ~{NAME_MAX}).")
        if not all(c.islower() or c.isdigit() or c == "-" for c in name):
            add("WARN", "name-format",
                "name should be lowercase-kebab-case (letters, digits, hyphens).")
    # description
    desc = meta.get("description")
    if not desc:
        add("ERROR", "missing-description",
            "Frontmatter is missing required `description` (the routing trigger).")
    else:
        if len(desc) > DESC_MAX:
            add("WARN", "description-too-long",
                f"description is {len(desc)} chars (max ~{DESC_MAX}).")
        if len(desc) < 40:
            add("WARN", "description-thin",
                "description is very short; weak routing/trigger signal.")

    # body
    if not body.strip():
        add("ERROR", "empty-body", "SKILL.md has no instructional body.")
    words = C.word_count(body)
    if words > SKILL_MD_WARN_WORDS:
        add("WARN", "skill-md-large",
            f"SKILL.md body is {words} words (>{SKILL_MD_WARN_WORDS}); "
            "consider moving detail into references/ for progressive disclosure.")

    # referenced files
    refs = C.extract_references(skill_dir, body)
    for r in refs:
        if not r["exists"]:
            add("ERROR", "broken-reference",
                f"Referenced file does not exist: {r['ref']} ({r['kind']}).")

    # bundled scripts sanity: python files should compile
    for p in sorted((skill_dir / "scripts").glob("*.py")) if (skill_dir / "scripts").is_dir() else []:
        try:
            compile(C.read_text(p), str(p), "exec")
        except SyntaxError as e:
            add("ERROR", "script-syntax-error",
                f"scripts/{p.name} has a syntax error: {e}")

    n_error = sum(1 for f in findings if f["level"] == "ERROR")
    n_warn = sum(1 for f in findings if f["level"] == "WARN")
    out = {
        "skill": name or skill_dir.name,
        "skill_dir": str(skill_dir),
        "ok": n_error == 0,
        "error_count": n_error,
        "warn_count": n_warn,
        "findings": findings,
    }
    print(C.dump_json(out))
    return 0 if n_error == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
