"""Shared helpers for the skill grade/improve toolkit.

Stdlib-only, no third-party dependencies, so these run from a bare `python`
on any platform. PyYAML is used *if present* for frontmatter parsing, with a
minimal built-in fallback otherwise.

Design principle: everything deterministic lives here or in the sibling
scripts. The LLM does reasoning; these do bookkeeping, path resolution,
timestamping, and arithmetic.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Force UTF-8 on stdout/stderr so JSON and reports print on a Windows console
# (default cp1252) without UnicodeEncodeError. Safe no-op where unsupported.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

# The 12 grading categories, in canonical order. Keys are the JSON keys the
# grader must emit; labels are for human-readable rendering.
CATEGORIES = [
    ("purpose_clarity", "Purpose clarity"),
    ("instruction_clarity", "Instruction clarity"),
    ("instruction_completeness", "Instruction completeness"),
    ("instruction_consistency", "Instruction consistency"),
    ("output_specification", "Output specification"),
    ("input_handling", "Input handling"),
    ("error_handling", "Error and failure handling"),
    ("edge_case_coverage", "Edge-case coverage"),
    ("tool_resource_reliability", "Tool and resource reliability"),
    ("context_efficiency", "Context efficiency"),
    ("maintainability", "Maintainability"),
    ("testability", "Testability"),
]
CATEGORY_KEYS = [k for k, _ in CATEGORIES]

SEVERITIES = ["P0", "P1", "P2", "P3"]
EVIDENCE_TYPES = ["OBSERVED", "DOCUMENTED", "INFERRED", "HYPOTHETICAL"]
CONFIDENCE_LEVELS = ["HIGH", "MEDIUM", "LOW"]

REPORT_SCHEMA_VERSION = "1.0"
GRADER_VERSION = "1.0"

# Weighting when behavioral tests are available.
DESIGN_WEIGHT = 0.40
BEHAVIORAL_WEIGHT = 0.60


# --------------------------------------------------------------------------- #
# Time
# --------------------------------------------------------------------------- #
def iso_now() -> str:
    """UTC timestamp, e.g. 2026-07-21T14:03:09Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fs_timestamp() -> str:
    """Filesystem-safe timestamp for history filenames, e.g. 20260721T140309Z."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


# --------------------------------------------------------------------------- #
# Frontmatter
# --------------------------------------------------------------------------- #
def split_frontmatter(text: str):
    """Return (frontmatter_text_or_None, body). Handles a leading '---' block."""
    if not text.startswith("---"):
        return None, text
    # match ---\n ... \n---\n
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
    if not m:
        return None, text
    return m.group(1), m.group(2)


def parse_frontmatter(text: str) -> dict:
    """Parse YAML frontmatter into a dict. Uses PyYAML if available, else a
    minimal parser that understands `key: value`, quoted values, and folded
    block scalars (`>`, `>-`, `|`). Returns {} when there is no frontmatter."""
    fm, _ = split_frontmatter(text)
    if fm is None:
        return {}
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(fm)
        return data if isinstance(data, dict) else {}
    except Exception:
        return _minimal_yaml(fm)


def _minimal_yaml(fm: str) -> dict:
    """Very small YAML-subset parser sufficient for SKILL.md frontmatter."""
    out: dict = {}
    lines = fm.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key, val = m.group(1), m.group(2).strip()
        if val in (">", ">-", "|", "|-", ">+", "|+"):
            # folded/literal block scalar: gather more-indented following lines
            block = []
            i += 1
            while i < len(lines) and (lines[i].startswith((" ", "\t")) or not lines[i].strip()):
                block.append(lines[i].strip())
                i += 1
            joiner = "\n" if val.startswith("|") else " "
            out[key] = joiner.join(b for b in block).strip()
            continue
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        out[key] = val
        i += 1
    return out


# --------------------------------------------------------------------------- #
# Skill discovery
# --------------------------------------------------------------------------- #
def candidate_roots() -> list[Path]:
    """Directories that may contain skills, most-specific first."""
    roots = []
    cwd = Path.cwd()
    roots.append(cwd / "skills")
    roots.append(cwd / ".claude" / "skills")
    home = Path.home()
    roots.append(home / ".claude" / "skills")
    roots.append(cwd)  # allow a skill folder directly in cwd
    # de-dup preserving order
    seen, uniq = set(), []
    for r in roots:
        rp = str(r)
        if rp not in seen:
            seen.add(rp)
            uniq.append(r)
    return uniq


def find_skill(name_or_path: str) -> Path:
    """Resolve a skill name or path to its directory (the one holding SKILL.md).

    Raises FileNotFoundError with the searched locations if not found."""
    p = Path(name_or_path).expanduser()
    # Direct path to a skill dir or its SKILL.md
    if p.exists():
        if p.is_file() and p.name.upper() == "SKILL.MD":
            return p.parent
        if p.is_dir() and (p / "SKILL.md").exists():
            return p
    searched = []
    for root in candidate_roots():
        cand = root / name_or_path
        searched.append(str(cand))
        if (cand / "SKILL.md").exists():
            return cand
    raise FileNotFoundError(
        f"Could not locate skill '{name_or_path}'. Searched:\n  "
        + "\n  ".join(searched)
    )


# --------------------------------------------------------------------------- #
# Referenced-file extraction
# --------------------------------------------------------------------------- #
_MD_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
# A backticked path token: no whitespace/backticks inside, and it points at one
# of the bundled resource dirs. Whitespace is disallowed so a large inline-code
# span can never be mis-read as a single (broken) path reference.
_BACKTICK_PATH = re.compile(
    r"`([^`\s]*(?:references|scripts|tests|assets|templates)/[^`\s]+)`")


def extract_references(skill_dir: Path, body: str) -> list[dict]:
    """Find local file references in SKILL.md body and report existence.

    Considers markdown links and backticked paths that point at bundled
    resource dirs. External URLs and absolute/`~` paths are ignored."""
    refs: dict[str, dict] = {}

    def consider(raw: str, kind: str):
        raw = raw.strip()
        if not raw:
            return
        low = raw.lower()
        if low.startswith(("http://", "https://", "mailto:", "#")):
            return
        if raw.startswith(("/", "~")) or re.match(r"^[A-Za-z]:", raw):
            return  # absolute — not a bundled relative resource
        # strip anchors / line suffixes like file.md#foo or file.py:12
        clean = raw.split("#", 1)[0]
        clean = re.sub(r":\d+$", "", clean)
        if not clean or clean in refs:
            return
        target = (skill_dir / clean).resolve()
        refs[clean] = {
            "ref": clean,
            "kind": kind,
            "exists": target.exists(),
        }

    for m in _MD_LINK.finditer(body):
        consider(m.group(1), "markdown-link")
    for m in _BACKTICK_PATH.finditer(body):
        consider(m.group(1), "backtick-path")
    return list(refs.values())


# --------------------------------------------------------------------------- #
# Reports root
# --------------------------------------------------------------------------- #
def reports_root(explicit: str | None = None) -> Path:
    """Resolve where reports live. Priority: explicit arg > env
    SKILL_REPORTS_ROOT > ~/.claude/skill-reports."""
    if explicit:
        return Path(explicit).expanduser()
    env = os.environ.get("SKILL_REPORTS_ROOT")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".claude" / "skill-reports"


def report_dir(skill_name: str, explicit_root: str | None = None) -> Path:
    return reports_root(explicit_root) / skill_name


# --------------------------------------------------------------------------- #
# IO helpers
# --------------------------------------------------------------------------- #
def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict:
    return json.loads(read_text(path))


def read_json_arg(arg: str) -> dict:
    """Load JSON from a file path, or from stdin when arg is '-'."""
    if arg == "-":
        return json.loads(sys.stdin.read())
    return load_json(Path(arg))


def dump_json(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)


def eprint(*a, **k):
    print(*a, file=sys.stderr, **k)


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))
