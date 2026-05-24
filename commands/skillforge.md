---
description: Route, create, improve, or inspect reusable AI skills with SkillForge
---

# SkillForge

Use SkillForge for skill routing, creation, improvement, and proactive advice.

## Arguments

$ARGUMENTS = a SkillForge request, such as:

- `create a skill for Amazon review gap analysis`
- `do I have a skill for PPC search term audits?`
- `improve the listing audit skill`
- `advice`
- `checkpoint <brief current context>`

## Instructions

1. Read `~/.claude/skills/skillforge/SKILL.md`.
2. If arguments are empty, show the available modes and ask what the user wants to do.
3. If arguments start with `advice`, run:
   ```bash
   python ~/.claude/skills/skillforge/scripts/context_advisor.py list
   ```
4. If arguments start with `checkpoint`, run:
   ```bash
   python ~/.claude/skills/skillforge/scripts/context_advisor.py checkpoint --cwd "$PWD" --text "<remaining arguments>"
   ```
5. For all other arguments, use the SkillForge skill workflow with `$ARGUMENTS` as the input.
6. Before creating a new skill, confirm SkillForge has checked for existing matching skills.
7. Report the recommended action clearly: use existing, improve existing, create new, compose skills, or clarify.

Request:

$ARGUMENTS
