# Iteration Guide

Skill creation does not end at generation. The best skills are shaped by real usage. This guide formalizes iteration as a deliberate step in the skill lifecycle.

---

## Iteration Workflow

```
1. USE the skill on a real task
2. NOTICE where Claude struggles, produces inconsistent output, or asks unnecessary questions
3. IDENTIFY whether the fix belongs in SKILL.md, a reference file, a script, or an asset
4. IMPLEMENT the change
5. TEST by re-running the same task (or a similar one)
6. REPEAT until the skill handles the task cleanly
```

Each iteration should target one specific behavior. Resist the urge to rewrite large sections at once.

---

## What to Look For

| Signal | Likely Fix |
|--------|-----------|
| Claude asks a question the skill should answer | Add the answer to SKILL.md or a reference |
| Output structure varies between runs | Add a low-freedom template or example |
| Claude skips a step | Make the step explicit with a checkpoint |
| Claude invents its own approach | Tighten instructions (lower degrees of freedom) |
| Claude follows instructions but the result is wrong | Fix the instructions, not Claude |
| Script fails on edge cases | Add input validation or error handling |
| Skill works but takes too many turns | Consolidate steps, reduce back-and-forth |

---

## Where to Make Changes

| Change Target | When |
|---------------|------|
| **SKILL.md** | Core workflow, triggers, phase descriptions, anti-patterns |
| **references/** | Supporting knowledge Claude needs during execution |
| **assets/templates/** | Output templates, boilerplate, starter files |
| **scripts/** | Validation, automation, state management |

Keep SKILL.md focused on the workflow. Move detailed knowledge into references. Move reusable output patterns into assets.

---

## Iterate vs Redesign

**Iterate** when:
- The skill's core approach is sound
- Problems are in specific steps or missing details
- Fixes are additive (more examples, tighter instructions, new references)
- Less than 30% of SKILL.md needs to change

**Redesign** when:
- The fundamental approach is wrong (e.g., wrong phases, wrong scope)
- Users consistently work around the skill instead of through it
- More than 50% of SKILL.md would need rewriting
- The skill's purpose has shifted significantly from the original intent

---

## Common Iteration Patterns

**Adding examples.** When Claude produces inconsistent output, add a concrete before/after example in SKILL.md or a reference. Examples are the most effective way to anchor behavior.

**Tightening scripts.** When a manual step is error-prone, replace prose instructions with a script. Move from high freedom to low freedom for that step.

**Expanding references.** When Claude lacks domain knowledge, add a reference file rather than bloating SKILL.md. Reference files are loaded into context but keep the main skill readable.

**Adding checkpoints.** When Claude skips steps, add explicit verification points: "Before proceeding, confirm X is true." Checkpoints break long workflows into verifiable segments.

**Narrowing scope.** When a skill tries to do too much, split it. A focused skill that does one thing well beats a sprawling skill that does many things poorly.

---

## Related References

- [Degrees of Freedom](degrees-of-freedom.md) -- choosing the right level of specificity
- [Evolution Scoring](evolution-scoring.md) -- measuring skill quality over time
