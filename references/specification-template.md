# Skill Specification Template (tiered)

The spec is written after analysis and BEFORE generation, and is the ONLY analysis artifact the fresh-context generation subagent receives. Write it so a reader with zero conversation history can build the skill. Never fill a section you cannot ground in the analysis or the baseline runs - omit optional sections rather than confabulate.

## Minimal tier (default - most skills)

```markdown
# Spec: <skill-name>

## Problem
What goes wrong without this skill, for whom, in what situations.
Paste the verbatim baseline (RED) failures - these are the ground truth.

## Requirements
- R1 (explicit): what the user asked for
- R2 (implicit): expected but unstated
- R3 (discovered): found in analysis/baseline runs
Each requirement traceable to a source (user words, baseline transcript, lens finding).

## Failure classification & guidance form
Which failure type the baseline showed (rule-skipping / wrong shape / omission /
conditional) and therefore which guidance form the body uses (see failure-form
table in testing-and-evals.md). State the degrees-of-freedom level per major
instruction (high=text, medium=pseudocode, low=exact script) and why.

## Key decisions
| Decision | Choice | WHY | Alternative rejected because |
|---|---|---|---|

## Description draft
Trigger-conditions-only draft + the keyword list mined from baseline failures.

## Scripts
needs_scripts: yes/no + rationale. If yes: name, category, purpose per script.

## Success criteria & eval plan
- The RED target tasks and their baseline failures (become evals/scenarios/)
- Positive + near-miss trigger queries (become evals/triggers.json)
- Any additional measurable criteria
```

## Full tier additions (infrastructure skills only)

Add these ONLY for skills that other skills/workflows will depend on (meta-skills, shared toolchains, org-wide processes) - where wrong early architecture is expensive:

```markdown
## Architecture
Pattern chosen (single-phase / checklist / generator / multi-phase / orchestrator)
with WHY; phase list with per-phase verification.

## Evolution analysis (advisory)
- Extension points: where the skill is expected to grow
- Obsolescence triggers: concrete external changes that would break it
- Temporal notes: only horizons you can actually reason about - no mandatory
  5-year fiction

## Anti-patterns
What adjacent-but-wrong usage looks like + what to do instead.
```

## Validation before generation

- [ ] Every section present is fully written (no placeholders)
- [ ] Every decision has a WHY and a rejected alternative
- [ ] Baseline failures pasted verbatim (not summarized away)
- [ ] Eval plan complete: scenarios + trigger queries + holdouts
- [ ] A stranger could build the skill from this document alone
