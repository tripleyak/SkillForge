# Review Protocol - lint plus one adversarial reviewer

SkillForge 6 replaced the former "unanimous panel of 3-4 agents" with this protocol. Rationale: same-model agents spawned by a parent that wants approval, using approval-shaped templates, converge on approval - unanimity measured nothing. Falsifiable properties moved to lint; judgment properties go to a single reviewer whose job is refutation. (Subagents receive only their prompt - they never share the parent's conversation history, so "shared context review" was never real.)

## Step 1: Mechanical gates (must pass first)

```bash
python3 scripts/validate_skill.py <skill-dir>    # frontmatter validity, word budget, pinned-model check, description shape
python3 scripts/check_docs_safety.py <skill-dir>
python3 scripts/run_skill_evals.py <skill-dir> --static
```

Fix every ERROR before spending reviewer tokens. Lint findings are not debatable.

## Step 2: Behavioral gates

Execution testing and trigger testing per [testing-and-evals.md](testing-and-evals.md) must be complete: baseline failures recorded, with-skill runs clear them, trigger recall/precision checked.

## Step 3: The adversarial reviewer

Dispatch ONE fresh subagent (Task tool, no shared history) with:
- The generated skill files
- The spec's success criteria (not its self-assessments)
- The eval scenario results
- This charge:

```
You are reviewing a newly created agent skill. Your job is to REFUTE it, not approve it.
Find concrete cases where it fails. Check, in order of severity:

1. FACTS: every API, command, path, and platform claim - verify against the actual
   system/docs. A skill that teaches something false is worse than no skill.
2. OVER-TRIGGERING: given this description and a roster of hundreds of skills, name
   3 realistic requests where this skill would load but should not.
3. MISLEADING GUIDANCE: a case where following the skill verbatim produces a worse
   outcome than ignoring it.
4. GAPS: the most likely real-world variant of the target task that the skill's
   guidance does not survive.
5. STRUCTURE: description summarizes workflow? body content that belongs in
   references/? sections the agent will never use?

For each finding: state the concrete failing case, not an opinion. If you cannot
construct a failing case for a category, say "no failing case found" - do not
manufacture style feedback to seem thorough.
Verdict: list of findings with severity (blocker / should-fix / note). No scores.
```

## Step 4: Disposition

- **Blockers**: fix, re-run affected evals, re-submit to a fresh reviewer instance (max 3 cycles; if still blocked, surface to the user with both positions).
- **Should-fix**: fix if the fix does not grow SKILL.md past budget; otherwise record in the skill's spec as a known limit.
- **Notes**: author's discretion.

There is no approval step. A skill ships when lint passes, evals pass, and no blocker survives.

## Reviewer checklists (carried by the adversarial reviewer)

**Design**: guidance form matches failure type (see failure-form table in testing-and-evals.md); degrees of freedom match task fragility; scripts included only where deterministic; no circular references between files.

**Usability**: description is trigger-conditions-only and symptom-rich; a first-time agent can execute without assumed context; examples are complete and runnable; reference files are reachable from SKILL.md.

**Evolution** (advisory, not a gate): no pinned dated versions; rationale (WHY) recorded for non-obvious decisions; extension points where growth is plausible. Use [evolution-scoring.md](evolution-scoring.md) as a heuristic lens - never as a numeric gate.
