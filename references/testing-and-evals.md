# Testing and Evals - the empirical spine of SkillForge

Skill quality is a property of behavior. Every gate in this document is falsifiable: it compares observed agent behavior with and without the skill, or checks a mechanical property. Nothing here is self-scored.

## 1. Baseline gate (RED) - before any design work

1. Write 2-3 representative task prompts a user would actually give (the "target tasks").
2. Dispatch a fresh subagent (Task tool) per target task, WITHOUT the skill installed or mentioned. The subagent must not see your analysis.
3. Capture verbatim: what it did, what it got wrong, what it rationalized.
4. Decision:
   - **No failure observed → do not create the skill.** Claude already handles it; a skill would be duplicate context weight. Record the finding in the triage log.
   - **Failure observed → proceed.** The verbatim failures become (a) the skill's eval scenarios, (b) keyword sources for the description, (c) the specific behaviors the body must counter.

Skipping RED and writing from intuition is the number-one cause of dead-weight skills. If you already "know" the failure, proving it costs one subagent run.

## 2. Failure-form table - match guidance form to failure type

Classify what the baseline showed before writing the body:

| Baseline failure | Right form | Wrong form |
|---|---|---|
| Knows the rule, skips it under pressure | Prohibition + rationalization table + red-flags list | Soft "prefer/consider" guidance |
| Complies but output has the wrong shape | Positive recipe/contract: state what the output IS, parts in order | Prohibition list (measurably backfires on shaping) |
| Omits a required element | Structural: REQUIRED slot in a template it fills | Prose reminders |
| Behavior should depend on a condition | Conditional keyed to an observable predicate | Unconditional rule + exemption clauses |

No nuance clauses ("don't X unless it matters" reopens negotiation). Express real exceptions as their own conditionals on observable predicates.

## 3. Execution testing (GREEN) - after generation

1. Re-run every RED target task WITH the skill, in fresh subagents (`context: fork` or Task tool). One run per scenario minimum; 3 runs for discipline skills (they fail probabilistically under pressure).
2. Compare against the recorded baseline failures. The gate: **no with-skill run exhibits a baseline failure.**
3. A with-skill run that fails identifies a loophole. Fix the body (add the counter, restructure the form per the table above), re-run. Do not weaken the scenario to pass.
4. For discipline skills, escalate pressure: combine time pressure + sunk cost + authority in the scenario prompt and confirm compliance holds.

## 4. Trigger testing - the description is the product

The frontmatter description is the only text always in context; test it like an interface.

1. Generate ~10 positive queries (real phrasings that SHOULD trigger) and ~5 near-misses (adjacent requests that should NOT).
2. Static check: `run_skill_evals.py --static` verifies each positive query shares matchable keywords with the description.
3. Live check (preferred): for each query, ask a fresh agent with the skill roster available which skill (if any) it would load. Score recall on positives and precision on near-misses.
4. Iterate the description ONLY against failures from these runs. Hold out 2-3 positive queries: never edit against them, only measure - this prevents overfitting the description to the test set.
5. Description rules: third person, trigger conditions only ("Use when..."), symptom keywords, no workflow summary (agents follow summaries and skip the body).

## 5. Blind A/B - for IMPROVE_EXISTING

1. Keep the old skill version. Run the same scenario set against old and new.
2. Give the outputs, unlabeled and order-shuffled, to a fresh judge subagent: "Which response handled the task better, and why?"
3. Ship the new version only if it wins or ties on every scenario and wins at least one. A "cleaner" version that loses a scenario is a regression, not an improvement.

## 6. The evals/ directory - skills ship with their tests

Every generated skill includes:

```
<skill>/evals/
  triggers.json          # {"positive": [...], "near_miss": [...], "holdout": [...]}
  scenarios/
    01-<slug>.md         # one file per behavioral scenario
```

Scenario file format:

```markdown
---
task: "The exact prompt to give the test subagent"
baseline_failure: "What agents do WITHOUT the skill (from RED runs, verbatim summary)"
assertions:
  - "Observable property the with-skill output must have"
  - "Baseline failure that must NOT appear"
runs: 1        # 3 for discipline skills
---
Optional setup notes (files to create, state to arrange) for the runner.
```

Run modes:

```bash
python3 scripts/run_skill_evals.py <skill-dir> --static   # structure + trigger keyword lint (CI-safe, no model calls)
python3 scripts/run_skill_evals.py <skill-dir> --live     # drives headless `claude -p` runs for scenarios + triggers
```

After ANY edit to a shipped skill, re-run its evals. This is regression testing for skills; treat a failing eval exactly like a failing unit test.

## 7. What review is for

Mechanical properties go to lint (`validate_skill.py`): frontmatter validity, word budgets, pinned model IDs, description shape. Behavioral properties go to the runs above. The single adversarial reviewer (see synthesis-protocol.md) exists for what neither can catch: wrong facts, misleading guidance, over-triggering risk in the roster. Its job is to refute, not approve - fix what it proves and ship.
