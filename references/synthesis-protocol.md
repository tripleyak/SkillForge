# Multi-Agent Synthesis Protocol

The final quality gate ensuring generated skills meet the highest standards through diverse perspective evaluation.

## Overview

The synthesis panel applies the "wisdom of crowds" principle to skill evaluation. Three Opus agents, each with a distinct evaluative lens, must unanimously approve the skill before it's finalized.

**Key Principle:** A skill that satisfies a single perspective may have critical blind spots. Multi-perspective evaluation ensures comprehensive quality.

---

## Panel Composition

```
┌────────────────────────────────────────────────────────────────────────┐
│                    SYNTHESIS PANEL (3 Opus Agents)                      │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐  │
│  │ DESIGN AGENT      │  │ AUDIENCE AGENT    │  │ EVOLUTION AGENT   │  │
│  │                   │  │                   │  │                   │  │
│  │ Focus:            │  │ Focus:            │  │ Focus:            │  │
│  │ • Structure       │  │ • Clarity         │  │ • Timelessness    │  │
│  │ • Patterns        │  │ • Discoverability │  │ • Extensibility   │  │
│  │ • Correctness     │  │ • Completeness    │  │ • Future-proofing │  │
│  │ • Consistency     │  │ • Usability       │  │ • Ecosystem fit   │  │
│  │                   │  │                   │  │                   │  │
│  │ Model: Opus 4.5   │  │ Model: Opus 4.5   │  │ Model: Opus 4.5   │  │
│  └───────────────────┘  └───────────────────┘  └───────────────────┘  │
│           │                      │                      │              │
│           └──────────────────────┼──────────────────────┘              │
│                                  ▼                                     │
│                        ┌──────────────────┐                            │
│                        │ CONSENSUS CHECK  │                            │
│                        │ Require: 3/3     │                            │
│                        └──────────────────┘                            │
│                                  │                                     │
│                    ┌─────────────┴─────────────┐                       │
│                    ▼                           ▼                       │
│            ┌─────────────┐            ┌─────────────────┐              │
│            │ APPROVED    │            │ ITERATE         │              │
│            │ → Finalize  │            │ → Return Phase 1│              │
│            └─────────────┘            └─────────────────┘              │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Agent Definitions

### Agent 1: Design/Architecture Agent

**Role:** Technical correctness and structural quality

**Evaluation Criteria:**

| Criterion | Weight | Passing Threshold |
|-----------|--------|-------------------|
| Architecture pattern appropriate | 25% | Pattern matches task complexity |
| Phases logically ordered | 20% | No circular dependencies |
| Verification steps concrete | 20% | Each phase has verifiable output |
| Internal consistency | 20% | No contradictions |
| Code/command accuracy | 15% | All examples valid |

**Key Questions:**
- Is the chosen pattern the right one for this task?
- Are phases ordered correctly with clear dependencies?
- Can each step be verified objectively?
- Are there any logical inconsistencies?
- Would the commands/code actually work?

**Red Flags:**
- Wrong pattern for complexity level
- Circular phase dependencies
- Vague verification ("ensure quality")
- Contradictory instructions
- Invalid syntax in examples

---

### Agent 2: Audience/Usability Agent

**Role:** User experience and accessibility

**Evaluation Criteria:**

| Criterion | Weight | Passing Threshold |
|-----------|--------|-------------------|
| Trigger naturalness | 20% | Triggers match natural language |
| Step actionability | 25% | Each step is clear and doable |
| Assumed knowledge explicit | 20% | No unexplained jargon |
| Examples where helpful | 15% | Complex concepts have examples |
| Discoverability | 20% | Skill is findable and understandable |

**Key Questions:**
- Would the target audience naturally say these trigger phrases?
- Can a user follow each step without guessing?
- Are all technical terms explained or commonly understood?
- Are examples provided where they would help?
- Would users find this skill when they need it?

**Red Flags:**
- Triggers are too technical or obscure
- Steps require unstated prerequisite knowledge
- Jargon without definition
- Complex concepts without examples
- Skill is hard to discover or understand

---

### Agent 3: Evolution/Timelessness Agent

**Role:** Future-proofing and ecosystem integration

**Evaluation Criteria:**

| Criterion | Weight | Passing Threshold |
|-----------|--------|-------------------|
| Timelessness score | 30% | Score ≥ 7/10 |
| Extension points | 25% | At least 2 documented |
| Dependency stability | 20% | Volatile deps abstracted |
| Ecosystem integration | 15% | Works with related skills |
| Principle-based design | 10% | WHY documented for decisions |

**Key Questions:**
- Will this skill still be valuable in 2 years?
- Can it be extended without rewriting?
- Are external dependencies safely abstracted?
- Does it compose well with other skills?
- Are design decisions explained, not just stated?

**Red Flags:**
- Timelessness score < 7
- No documented extension points
- Hardcoded external dependencies
- Conflicts with existing skills
- "What" without "Why"

---

## Execution Protocol

### Step 1: Parallel Agent Launch

All three agents receive the complete skill output simultaneously:

```yaml
SYNTHESIS_INPUT:
  skill_md: [Full SKILL.md content]
  specification: [SKILL_SPEC.md used for generation]
  reference_docs: [Any generated reference documents]
  metadata:
    analysis_iterations: N
    lenses_applied: [list]
    questioning_rounds: N
```

Agents run in parallel using `run_in_background: true`.

### Step 2: Individual Evaluation

Each agent produces a structured review:

```markdown
## [Agent Name] Review

### Verdict: APPROVED / CHANGES_REQUIRED

### Scores
| Criterion | Score (1-10) | Notes |
|-----------|--------------|-------|
| Criterion 1 | 8 | [specific observation] |
| Criterion 2 | 9 | [specific observation] |
| Criterion 3 | 7 | [specific observation] |
| ... | ... | ... |
| **Weighted Average** | **X.X** | |

### Strengths
1. [Specific strength with evidence]
2. [Specific strength with evidence]

### Issues (if CHANGES_REQUIRED)
| Issue ID | Description | Severity | Required Change |
|----------|-------------|----------|-----------------|
| D1 | [Issue description] | Critical | [Specific fix] |
| D2 | [Issue description] | Major | [Specific fix] |

### Recommendations (even if APPROVED)
1. [Optional improvement suggestion]
2. [Optional improvement suggestion]

### Confidence Level: High / Medium / Low
[Explanation for confidence level]
```

### Step 3: Consensus Aggregation

After all agents complete:

```markdown
## Synthesis Panel Results

### Verdicts
| Agent | Verdict | Avg Score | Critical Issues |
|-------|---------|-----------|-----------------|
| Design | APPROVED/CHANGES | X.X | N |
| Audience | APPROVED/CHANGES | X.X | N |
| Evolution | APPROVED/CHANGES | X.X | N |

### Consensus: UNANIMOUS APPROVED / REQUIRES ITERATION

### If REQUIRES ITERATION:
Combined issues from all agents:

| Issue ID | Source Agent | Severity | Required Change |
|----------|--------------|----------|-----------------|
| D1 | Design | Critical | [fix] |
| A2 | Audience | Major | [fix] |
| E1 | Evolution | Critical | [fix] |

### Next Steps:
1. Return to Phase 1 with issues as new input
2. Apply targeted regression questioning
3. Regenerate skill
4. Re-submit to synthesis panel
```

---

## Iteration Protocol

### When Consensus Not Reached

1. **Collect all issues** from all agents
2. **Prioritize by severity:** Critical → Major → Minor
3. **Return to Phase 1** with issues as structured input:

```yaml
ITERATION_INPUT:
  round: N
  previous_skill: [reference to previous version]
  panel_feedback:
    design_issues:
      - id: D1
        severity: critical
        description: [issue]
        required_fix: [fix]
    audience_issues:
      - id: A1
        severity: major
        description: [issue]
        required_fix: [fix]
    evolution_issues:
      - id: E1
        severity: critical
        description: [issue]
        required_fix: [fix]
```

4. **Targeted questioning** focuses on issue areas
5. **Regenerate** with explicit attention to fixes
6. **Re-submit** to panel

### Iteration Limits

| Round | Action if No Consensus |
|-------|------------------------|
| 1-3 | Normal iteration |
| 4 | Require only critical fixes |
| 5 | Flag for human review |

**At Round 5 without consensus:**

```markdown
## Human Review Required

The synthesis panel has not reached consensus after 5 iterations.

### Remaining Disagreements:
| Agent | Position | Rationale |
|-------|----------|-----------|
| Design | [position] | [why] |
| Audience | [position] | [why] |
| Evolution | [position] | [why] |

### Options for Human Decision:
1. Accept with Agent X's recommendations
2. Accept with Agent Y's recommendations
3. Accept current state with documented limitations
4. Abandon and redesign from scratch

### Recommendation: [Human-readable recommendation]
```

---

## Quality Thresholds

### Minimum for APPROVED Verdict

| Agent | Minimum Average Score | Critical Issues Allowed |
|-------|----------------------|------------------------|
| Design | 7.0 | 0 |
| Audience | 7.0 | 0 |
| Evolution | 7.0 (timelessness ≥7) | 0 |

### Issue Severity Definitions

| Severity | Definition | Impact on Approval |
|----------|------------|-------------------|
| Critical | Blocks core functionality or violates key principle | Automatic CHANGES_REQUIRED |
| Major | Significant quality issue but workaround exists | ≥2 → CHANGES_REQUIRED |
| Minor | Improvement opportunity, not blocking | Noted but doesn't block |

---

## Agent Prompt Templates

### Design Agent System Prompt

```
You are the Design/Architecture Agent in a skill evaluation panel.

Your focus: Technical correctness, structural quality, pattern appropriateness.

Evaluate the skill against these criteria:
1. Architecture pattern matches task complexity
2. Phases are logically ordered with no circular dependencies
3. Each phase has concrete, verifiable outputs
4. Internal consistency throughout
5. All code/command examples are valid

Produce a structured review with:
- Scores for each criterion (1-10)
- Specific strengths with evidence
- Issues with severity and required fixes
- Confidence level

Be rigorous but fair. Critical issues must block approval.
Minor improvements can be noted without blocking.
```

### Audience Agent System Prompt

```
You are the Audience/Usability Agent in a skill evaluation panel.

Your focus: User experience, clarity, accessibility, discoverability.

Evaluate the skill against these criteria:
1. Trigger phrases match natural language patterns
2. Each step is clear and actionable
3. No unexplained jargon or assumed knowledge
4. Examples provided where helpful
5. Skill is discoverable and understandable

Produce a structured review with:
- Scores for each criterion (1-10)
- Specific strengths with evidence
- Issues with severity and required fixes
- Confidence level

Think like a user encountering this skill for the first time.
Would they succeed? Would they be confused?
```

### Evolution Agent System Prompt

```
You are the Evolution/Timelessness Agent in a skill evaluation panel.

Your focus: Future-proofing, extensibility, ecosystem integration.

Evaluate the skill against these criteria:
1. Timelessness score (use evolution-scoring.md rubric, require ≥7)
2. Extension points documented (require ≥2)
3. Volatile dependencies abstracted
4. Composes well with existing skills
5. Decisions include WHY, not just WHAT

Produce a structured review with:
- Scores for each criterion (1-10)
- Specific strengths with evidence
- Issues with severity and required fixes
- Confidence level

Think 2 years ahead. Will this skill still be valuable?
Can it evolve without rewriting?
```

---

## Integration with Skill Creation Flow

```
Phase 1: Deep Analysis
        │
        ▼
Phase 2: Specification Generation
        │
        ▼
Phase 3: Skill Generation
        │
        ▼
Phase 4: Synthesis Panel ──────────┐
        │                          │
        ▼                          │
   ┌─────────┐                     │
   │Unanimous│──No──► Return to ───┘
   │  3/3?   │        Phase 1 with
   └─────────┘        feedback
        │
       Yes
        │
        ▼
   ┌─────────────┐
   │  Finalize   │
   │  Skill      │
   │  Update     │
   │  Registry   │
   └─────────────┘
```

---

## Forked Context for Panel Agents

Skills can run in isolated forked contexts using `context: fork`. This has implications for the synthesis panel.

### What is Forked Context?

```yaml
---
name: isolated-skill
context: fork
agent: general-purpose
---
```

When `context: fork` is set:
- Skill executes in a separate sub-agent process
- Sub-agent has its own conversation history (starts fresh)
- Parent conversation context is NOT inherited
- Results are returned to parent when sub-agent completes

### Implications for Multi-Agent Synthesis

**Current Approach (Shared Context):**
```
Main Context
    │
    ├── Phase 1: Analysis (in main context)
    ├── Phase 2: Specification (in main context)
    ├── Phase 3: Generation (in main context)
    └── Phase 4: Synthesis Panel
        ├── Design Agent (Task, shares context)
        ├── Audience Agent (Task, shares context)
        └── Evolution Agent (Task, shares context)
```

Agents share context but run via Task tool with `run_in_background: true`.

**Alternative Approach (Forked Contexts):**

For skills that NEED context isolation (e.g., security-sensitive reviews):

```
Main Context
    │
    └── Phase 4: Synthesis Panel
        ├── Design Agent (context: fork) ─── Clean slate
        ├── Audience Agent (context: fork) ─── Clean slate
        └── Evolution Agent (context: fork) ─── Clean slate
```

### When to Use Forked Contexts

| Scenario | Recommendation | Rationale |
|----------|----------------|-----------|
| Standard skill creation | Shared context | Agents need spec + generated skill |
| Security-sensitive review | Forked context | Prevent context pollution |
| Independent evaluations | Forked context | Each agent judges without bias |
| Iterative refinement | Shared context | Agents need previous feedback |

### Skill Configuration for Forked Panel Agents

If creating a skill that spawns forked review agents:

```markdown
## Phase 4: Synthesis Panel

Launch review agents in forked contexts:

\`\`\`yaml
# Agent configuration for forked execution
- name: design-reviewer
  context: fork
  agent: general-purpose
  prompt: |
    You are the Design Agent. Review this skill for:
    - Architecture pattern appropriateness
    - Phase ordering and dependencies
    - Verification concreteness

    Skill to review:
    {{SKILL_CONTENT}}

    Specification:
    {{SPEC_CONTENT}}
\`\`\`

Note: When using forked context, you MUST include all necessary context
in the prompt since the agent cannot access parent conversation history.
```

### Trade-offs

| Aspect | Shared Context | Forked Context |
|--------|----------------|----------------|
| Context access | Full history | Prompt only |
| Independence | May be biased by prior discussion | Clean evaluation |
| Efficiency | Lower token usage | Higher (must include context) |
| Coordination | Easier | Requires explicit data passing |
| Setup complexity | Minimal | Must include all context in prompt |
| Use case | Iterative workflows | Independent evaluations |

### SkillForge's Choice

SkillForge uses **shared context** (no `context: fork`) because:
1. Phase 0 triage results must inform later phases
2. Specification from Phase 2 must be available in Phase 3
3. Panel agents need both specification AND generated skill
4. Iteration requires feedback from previous rounds

Skills created BY SkillForge may choose either approach based on their needs.
