---
name: {{skill-name}}
description: "Use when {{trigger conditions: concrete situations, user phrasings, symptoms, error messages - third person, no workflow summary}}"
---

# {{Skill Title}}

{{One-paragraph overview: what this enables and the core principle. 2-3 sentences.}}

## When to use

- {{Symptom or situation}}
- {{Symptom or situation}}

When NOT to use: {{adjacent cases that belong to other skills or need no skill}}

## {{Core section: the recipe, checklist, or pattern - matched to the failure type}}

{{The actual guidance. One excellent worked example beats many mediocre ones.
Keep total SKILL.md under 1,500 words; move depth to references/ and link it:
see [references/{{topic}}.md](references/{{topic}}.md)}}

## Common mistakes

| Mistake | Fix |
|---|---|
| {{what goes wrong}} | {{what to do instead}} |

<!--
Template notes (delete before shipping):
- description = trigger conditions ONLY. No "this skill does X then Y" - agents
  act on workflow summaries and skip the body.
- No model: pin unless required; never a dated ID (claude-*-YYYYMMDD).
- No body "Triggers" section - only the description triggers.
- No <details> blocks - use references/ files.
- Ship evals/ (triggers.json + scenarios/) per references/testing-and-evals.md.
- Add frontmatter fields only as needed: allowed-tools, context: fork, hooks
  (see references/claude-code-frontmatter.md for the current field set).
-->
