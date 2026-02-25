---
name: skillforge
description: >-
  Intelligent skill router and creator for Claude Code. Analyzes any input to
  recommend existing skills, improve them, or create new ones from scratch.
  Uses deep iterative analysis with 11 thinking models, regression questioning,
  evolution scoring, and multi-agent synthesis panel. Phase 0 triage prevents
  duplicates by scanning the skill ecosystem first.

  Triggers: "SkillForge: {goal}", "create skill", "design skill for {purpose}",
  "skillforge --plan-only", "do I have a skill for", "which skill", "what skill",
  "improve {skill} skill", "help me with", "I need to", "ultimate skill".

  Use for: creating new skills, improving existing skills, finding matching skills,
  routing task requests to the right skill, skill triage and discovery.
---

# SkillForge - Intelligent Skill Router & Creator

Analyzes ANY input to find, improve, or create the right skill.

---

## Quick Start

**Any input works.** SkillForge routes to the right action:

```
SkillForge: create a skill for automated code review
-> Creates new skill (after checking no duplicates exist)

help me debug this TypeError
-> Recommends ErrorExplainer skill (existing)

improve the testgen skill to handle React components better
-> Enters improvement mode for TestGen

do I have a skill for database migrations?
-> Recommends DBSchema, database-migration skills
```

---

## Process Overview

```
ANY USER INPUT
    |
    v
+---------------------------------------------------+
| Phase 0: SKILL TRIAGE                             |
| - Classify input (create/improve/question/task)   |
| - Scan skill ecosystem for matches                |
| - Route: USE | IMPROVE | CREATE | COMPOSE         |
+---------------------------------------------------+
    | (if CREATE or IMPROVE)
    v
+---------------------------------------------------+
| Phase 1: DEEP ANALYSIS                            |
| - Expand requirements (explicit/implicit/unknown) |
| - Apply 11 thinking models + automation lens      |
| - Regression questioning until 3 empty rounds     |
| - Assess degrees of freedom                       |
| - Identify script opportunities                   |
+---------------------------------------------------+
    |
    v
+---------------------------------------------------+
| Phase 2: SPECIFICATION                            |
| - Generate XML spec with all decisions + WHY      |
| - Validate timelessness score >= 7                |
| - Include scripts section if applicable           |
+---------------------------------------------------+
    |
    v
+---------------------------------------------------+
| Phase 3: GENERATION                               |
| - Write SKILL.md with fresh context               |
| - Generate references/, assets/, scripts/         |
| - Iterate: review output, identify gaps, refine   |
+---------------------------------------------------+
    |
    v
+---------------------------------------------------+
| Phase 4: SYNTHESIS PANEL                          |
| - 3-4 Opus agents review independently            |
| - Unanimous approval required                     |
| - If rejected -> loop back with feedback          |
+---------------------------------------------------+
    |
    v
Production-Ready Agentic Skill
```

**Key principles:**
- Phase 0 prevents duplicates -- always checks existing skills first
- Evolution/timelessness is the core lens (score >= 7 required)
- Every decision includes WHY
- Degrees of freedom assessed before locking in design choices
- Scripts enable self-verification and agentic operation
- Iteration step ensures output quality before panel review

---

## Commands

| Command | Action |
|---------|--------|
| `SkillForge: {goal}` | Full autonomous execution |
| `SkillForge --plan-only {goal}` | Generate specification only |
| `SkillForge --quick {goal}` | Reduced depth (not recommended) |
| `SkillForge --triage {input}` | Run Phase 0 triage only |
| `SkillForge --improve {skill}` | Improvement mode for existing skill |

---

## Phase 0: Skill Triage

Before creating anything, classify the input and scan existing skills.

### Input Classification

Inputs are classified as: `explicit_create`, `explicit_improve`, `skill_question`, `task_request`, `error_message`, or `code_snippet`.

### Decision Matrix

| Condition | Action |
|-----------|--------|
| Match >= 80% + explicit create | CLARIFY (duplicate warning) |
| Match >= 80% + other input | USE_EXISTING (recommend skill) |
| Match 50-79% | IMPROVE_EXISTING (enhance match) |
| Match < 50% + explicit create | CREATE_NEW (proceed to Phase 1) |
| Multi-domain detected | COMPOSE (suggest skill chain) |
| Ambiguous input | CLARIFY (ask for more info) |

### Triage Scripts

```bash
# Run triage on any input
python scripts/triage_skill_request.py "help me debug this error"

# JSON output for automation
python scripts/triage_skill_request.py "create a skill for payments" --json

# Rebuild skill index (after installing new skills)
python scripts/discover_skills.py
# Index: ~/.cache/skillrecommender/skill_index.json
```

### Routing After Triage

- **USE_EXISTING**: Exit early, recommend skill
- **IMPROVE_EXISTING**: Load skill -> Phase 1 analyzes gaps -> Phases 2-4 enhance
- **CREATE_NEW**: Full pipeline (Phase 1 -> 2 -> 3 -> 4)
- **COMPOSE**: Suggest SkillComposer for multi-skill chain
- **CLARIFY**: Pause for user input

---

## Phase 1-4 Execution

Phases 1 through 4 are documented in detail in the reference files. Here is a summary of each phase and what it produces.

### Phase 1: Deep Analysis

Expand the user's goal into comprehensive requirements across three layers: explicit (what they asked for), implicit (what they expect but didn't say), and discovered (what analysis reveals they need). Apply the 11 thinking models from the multi-lens framework. Run regression questioning rounds until three consecutive rounds produce no new insights. Assess degrees of freedom to understand which design decisions are fixed vs. flexible. Identify automation and script opportunities.

Key references:
- [Multi-Lens Framework](references/multi-lens-framework.md) -- 11 thinking models
- [Regression Questions](references/regression-questions.md) -- iterative question bank
- [Degrees of Freedom](references/degrees-of-freedom.md) -- design flexibility assessment
- [Script Integration Framework](references/script-integration-framework.md) -- automation analysis

### Phase 2: Specification

Capture all Phase 1 insights in an XML specification. Every decision must include WHY. Timelessness score must be >= 7. Scripts section included when applicable.

Key reference: [Specification Template](references/specification-template.md)

### Phase 3: Generation

Generate the skill with fresh context (no analysis artifacts polluting). Follow this order:

1. Create directory structure (`SKILL.md`, `references/`, `assets/`, `scripts/`)
2. Write SKILL.md with frontmatter, triggers, process, commands, anti-patterns
3. Generate reference documents for complex topics
4. Create scripts if needed (Result dataclass pattern, exit codes, self-verification)
5. **Iterate**: Review output against spec, identify gaps, refine before panel

Key reference: [Iteration Guide](references/iteration-guide.md) -- self-review step

**Generation quality checks:**

| Check | Requirement |
|-------|-------------|
| Frontmatter | `name` and `description` only |
| Name | Hyphen-case, <= 64 chars |
| Description | <= 1024 chars, includes trigger phrases |
| Triggers | 3-5 distinct, natural language |
| Tables over prose | Structured info in tables |
| No placeholders | Every section fully written |
| Scripts | Result pattern, argparse, exit codes |

### Phase 4: Multi-Agent Synthesis

3-4 Opus agents review independently with distinct lenses:

| Agent | Focus |
|-------|-------|
| Design/Architecture | Structure, patterns, correctness |
| Audience/Usability | Clarity, discoverability, completeness |
| Evolution/Timelessness | Future-proofing, extension points, ecosystem fit |
| Script/Automation | Agentic capability, self-verification (when scripts present) |

**Unanimous approval required.** If any agent rejects, loop back to Phase 1 with feedback. Max 5 iterations before escalating to human review.

Key references:
- [Synthesis Protocol](references/synthesis-protocol.md) -- panel details
- [Evolution Scoring](references/evolution-scoring.md) -- timelessness evaluation

---

## Skill Output Structure

```
~/.claude/skills/{skill-name}/
  SKILL.md              # Main entry point (required)
  references/           # Deep documentation (optional)
  assets/templates/     # Output templates (optional)
  scripts/              # Automation scripts (optional)
    validate.py         # Validation/verification
    generate.py         # Artifact generation
    state.py            # State management
```

**Scripts make skills agentic.** Include them when operations are repeatable, outputs need validation, or state must persist across sessions. See [Script Patterns Catalog](references/script-patterns-catalog.md) for standard Python patterns.

---

## Validation & Packaging

```bash
# Quick validation (required before packaging)
python scripts/quick_validate.py ~/.claude/skills/my-skill/

# Full structural validation
python scripts/validate-skill.py ~/.claude/skills/my-skill/

# Package for distribution
python scripts/package_skill.py ~/.claude/skills/my-skill/ ./dist
```

---

## Anti-Patterns

| Avoid | Why | Instead |
|-------|-----|---------|
| Duplicate skills | Bloats ecosystem | Check existing first (Phase 0) |
| Single trigger | Hard to discover | 3-5 varied phrases in description |
| No verification | Can't confirm success | Measurable outcomes |
| Over-engineering | Complexity without value | Start simple |
| Missing WHY | Can't evolve | Document rationale |
| Inlining deep content | Wastes context window | Use references/ for detail |

---

## Verification Checklist

After creation:

- [ ] Frontmatter has `name` and `description` only
- [ ] Name is hyphen-case, <= 64 chars
- [ ] Description <= 1024 chars, includes trigger phrases
- [ ] 3-5 trigger phrases in description
- [ ] Timelessness score >= 7
- [ ] `python scripts/quick_validate.py` passes
- [ ] Context window cost is minimal (< 500 lines in SKILL.md)

---

## References

- [Regression Questions](references/regression-questions.md) -- iterative question bank (7 categories)
- [Multi-Lens Framework](references/multi-lens-framework.md) -- 11 thinking models guide
- [Specification Template](references/specification-template.md) -- XML spec structure
- [Evolution Scoring](references/evolution-scoring.md) -- timelessness evaluation
- [Synthesis Protocol](references/synthesis-protocol.md) -- multi-agent panel details
- [Script Integration Framework](references/script-integration-framework.md) -- when and how to create scripts
- [Script Patterns Catalog](references/script-patterns-catalog.md) -- standard Python patterns
- [Degrees of Freedom](references/degrees-of-freedom.md) -- design flexibility assessment
- [Iteration Guide](references/iteration-guide.md) -- self-review before panel

---

## Related Skills

| Skill | Relationship |
|-------|--------------|
| skill-composer | Orchestrates created skills |
| claude-authoring-guide | Deeper patterns reference |
| codereview | Pattern for multi-agent panels |
| maker-framework | Zero error standard source |

---

## Extension Points

1. **Additional Lenses** -- add thinking models to `references/multi-lens-framework.md`
2. **New Synthesis Agents** -- extend panel for domain-specific review
3. **Custom Patterns** -- add architecture patterns to selection guide
4. **Domain Templates** -- add templates to `assets/templates/`
5. **Script Patterns** -- extend `references/script-patterns-catalog.md`
