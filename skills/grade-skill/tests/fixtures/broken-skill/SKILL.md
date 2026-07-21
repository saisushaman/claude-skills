---
name: broken-skill
---

# broken-skill

A deliberately broken fixture used by grade-skill's test suite. It is missing the
required `description` in frontmatter and points at a file that does not exist:
[missing doc](references/does-not-exist.md).

validate-skill.py must flag `missing-description` (ERROR) and `broken-reference`
(ERROR) and exit non-zero.
