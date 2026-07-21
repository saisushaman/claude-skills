---
name: good-skill
description: >-
  A minimal, well-formed fixture skill used by grade-skill's deterministic test
  suite. It has valid frontmatter, a resolvable reference, and a lean body, so
  validate-skill.py must report it clean (ok=true, zero errors).
---

# good-skill

A fixture. Given an input, it produces a greeting in the format `Hello, <name>!`.

## Steps
1. Read the `name` argument (default: `world`).
2. Emit `Hello, <name>!`.

See `references/notes.md` for the rationale.
