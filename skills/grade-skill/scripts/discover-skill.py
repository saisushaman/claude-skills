#!/usr/bin/env python
"""discover-skill.py — locate a skill and inventory its contents.

Deterministic filesystem work so the LLM never has to stat files, walk
directories, or eyeball frontmatter. Emits one JSON object to stdout.

Usage:
    python discover-skill.py <skill-name-or-path> [--json]

Output (JSON): resolved paths, parsed frontmatter, file inventory with sizes
and line counts, presence of scripts/tests/references dirs, referenced files
with existence flags, and coarse context-efficiency metrics.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402


def inventory(skill_dir: Path) -> list[dict]:
    files = []
    for p in sorted(skill_dir.rglob("*")):
        if p.is_dir():
            continue
        rel = p.relative_to(skill_dir).as_posix()
        try:
            raw = p.read_bytes()
            text = raw.decode("utf-8", errors="replace")
            lines = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
        except Exception:
            raw, lines = b"", 0
        files.append({
            "path": rel,
            "bytes": len(raw),
            "lines": lines,
            "ext": p.suffix.lower(),
        })
    return files


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        C.eprint("usage: discover-skill.py <skill-name-or-path>")
        return 2
    try:
        skill_dir = C.find_skill(args[0])
    except FileNotFoundError as e:
        print(C.dump_json({"error": str(e)}))
        return 1

    skill_md = skill_dir / "SKILL.md"
    text = C.read_text(skill_md)
    meta = C.parse_frontmatter(text)
    _, body = C.split_frontmatter(text)

    files = inventory(skill_dir)
    refs = C.extract_references(skill_dir, body)

    subdirs = {
        "references": (skill_dir / "references").is_dir(),
        "scripts": (skill_dir / "scripts").is_dir(),
        "tests": (skill_dir / "tests").is_dir(),
        "assets": (skill_dir / "assets").is_dir(),
        "templates": (skill_dir / "templates").is_dir(),
    }

    skill_md_words = C.word_count(body)
    result = {
        "name": meta.get("name") or skill_dir.name,
        "skill_dir": str(skill_dir),
        "skill_md": str(skill_md),
        "frontmatter": {
            "name": meta.get("name"),
            "description": meta.get("description"),
            "keys": sorted(meta.keys()),
            "allowed_tools": meta.get("allowed-tools") or meta.get("allowed_tools"),
        },
        "subdirs_present": subdirs,
        "file_count": len(files),
        "files": files,
        "references": refs,
        "broken_references": [r["ref"] for r in refs if not r["exists"]],
        "metrics": {
            "skill_md_bytes": skill_md.stat().st_size,
            "skill_md_lines": text.count("\n") + 1,
            "skill_md_words": skill_md_words,
            "reference_file_count": sum(1 for f in files if f["path"].startswith("references/")),
            "script_file_count": sum(1 for f in files if f["path"].startswith("scripts/")),
            "test_file_count": sum(1 for f in files if f["path"].startswith("tests/")),
        },
    }
    print(C.dump_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
