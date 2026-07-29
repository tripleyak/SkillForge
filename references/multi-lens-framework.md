# Multi-Lens Analysis Framework

Systematic application of 11 thinking models to skill design. Each lens reveals different aspects of the problem space that single-perspective analysis would miss.

## Overview

The multi-lens framework ensures comprehensive analysis by requiring explicit application of each thinking model to the skill being designed. This prevents the common failure mode of designing from a single perspective.

**Minimum Requirements:**
- Three lenses are load-bearing for every skill: Inversion, Pareto, Root Cause. Scan the rest; apply any that yields an actionable design change
- At least 3 lenses must yield actionable insights
- Conflicting perspectives must be explicitly resolved

---

## The 11 Thinking Models

### Lens 1: First Principles

**Core Question:** What is fundamentally needed? What can we build from scratch?

**Application to Skill Design:**
```
1. Strip away conventional skill patterns
2. Ask: "If skills didn't exist, how would we solve this?"
3. Identify the core utility this skill provides
4. Build up from fundamental requirements
```

**Key Questions:**
- What is the atomic unit of value this skill delivers?
- What assumptions from existing skills are we carrying forward unnecessarily?
- What would a minimal viable skill look like?

**Output:** Core value proposition, stripped of convention

---

### Lens 2: Inversion

**Core Question:** What would guarantee this skill fails?

**Application to Skill Design:**
```
1. List all ways this skill could fail
2. Create explicit anti-patterns from each
3. Design to avoid every failure mode
4. Document why each anti-pattern is dangerous
```

**Failure Categories:**
| Category | Example Failures |
|----------|------------------|
| Adoption | Too complex, unclear triggers, wrong audience |
| Execution | Timeout, wrong output, missing edge cases |
| Integration | Conflicts with other skills, breaks ecosystem |
| Evolution | Obsolete quickly, can't extend, tightly coupled |

**Output:** Comprehensive anti-patterns section

---

### Lens 3: Second-Order Effects

**Core Question:** What happens after the obvious consequences?

**Application to Skill Design:**
```
1. Identify immediate effects of the skill
2. For each effect, ask "then what?"
3. Map the chain 3-4 levels deep
4. Plan for downstream impacts
```

**Example Chain:**
```
Skill generates documentation →
  Developers use documentation →
    Documentation becomes outdated →
      Misleading docs worse than no docs →
        Need sync mechanism with code
```

**Output:** Extended impact analysis, preventive measures

---

### Lens 4: Pre-Mortem

**Core Question:** Assuming this skill failed, why did it fail?

**Application to Skill Design:**
```
1. Imagine complete failure 6 months from now
2. List all reasons it could have failed
3. Prioritize by likelihood × impact
4. Mitigate top risks proactively
```

**Pre-Mortem Template:**
```markdown
## Pre-Mortem Analysis

Date: 6 months from now
Outcome: Skill is unused and deprecated

### Why it failed:
1. [Reason 1] - Likelihood: High - Impact: Critical
2. [Reason 2] - Likelihood: Medium - Impact: Major
3. [Reason 3] - Likelihood: Low - Impact: Minor

### Mitigations Added:
- [Mitigation for Reason 1]
- [Mitigation for Reason 2]
```

**Output:** Risk-aware design with built-in mitigations

---

### Lens 5: Systems Thinking

**Core Question:** How do the parts interact? What are the feedback loops?

**Application to Skill Design:**
```
1. Map skill as a system (inputs, processes, outputs)
2. Identify relationships with other system components
3. Find feedback loops (positive and negative)
4. Locate leverage points for maximum impact
```

**System Diagram Elements:**
- Inputs: User goal, context, configuration
- Processes: Each phase of the skill
- Outputs: Artifacts, side effects, state changes
- Connections: Dependencies, triggers, compositions

**Key Questions:**
- What other skills does this interact with?
- What feedback loops exist (success breeds success, failure cascades)?
- Where are the leverage points that have outsized impact?

**Output:** System integration map, leverage point identification

---

### Lens 6: Devil's Advocate

**Core Question:** What's the strongest argument against this approach?

**Application to Skill Design:**
```
1. State the design decision clearly
2. Actively argue the opposite
3. Find legitimate concerns
4. Strengthen or abandon the decision
```

**Application Protocol:**
For each major design decision:
1. Write the strongest possible counterargument
2. If counterargument wins → change the decision
3. If original wins → document why counterargument was rejected

**Output:** Validated decisions with documented rationale

---

### Lens 7: Constraint Analysis

**Core Question:** What are the real constraints? Which are self-imposed?

**Application to Skill Design:**
```
1. List all perceived constraints
2. Classify: Hard (real) vs Soft (assumed)
3. Challenge soft constraints
4. Work within hard constraints creatively
```

**Constraint Categories:**
| Type | Example | Fixed? |
|------|---------|--------|
| Platform | Claude's token limits | Hard |
| Convention | "Skills should be <500 lines" | Soft |
| Technical | Must work with existing tools | Usually Hard |
| Social | "Users expect X pattern" | Soft |

**Output:** Clear understanding of actual constraints, creative solutions

---

### Lens 8: Pareto Analysis (80/20 Rule)

**Core Question:** Which 20% of features deliver 80% of value?

**Application to Skill Design:**
```
1. List all potential features/capabilities
2. Estimate value contribution of each
3. Identify the vital few (20%)
4. Focus resources on high-value features
```

**Pareto Matrix:**
| Feature | Value Contribution | Effort | Include? |
|---------|-------------------|--------|----------|
| Core function | 60% | Medium | Yes - Must have |
| Edge case handling | 10% | High | Maybe - Later |
| Nice-to-have UI | 5% | Low | Maybe - Easy win |
| Advanced config | 5% | High | No - Defer |

**Output:** Focused feature set, deferred backlog

---

### Lens 9: Root Cause Analysis (5 Whys)

**Core Question:** Why is this skill needed? (Asked 5 times)

**Application to Skill Design:**
```
1. State the need: "We need a skill for X"
2. Ask "Why?" and answer
3. For the answer, ask "Why?" again
4. Repeat until root cause emerges
5. Ensure skill addresses root cause, not symptoms
```

**Example:**
```
Need: "We need a skill to generate API docs"
Why? → Developers don't document APIs
Why? → Documentation is tedious
Why? → Requires switching contexts
Why? → No integration with coding workflow
Why? → Tools don't support inline doc generation

Root Cause: Lack of integrated documentation tooling
Skill Should: Integrate seamlessly with coding workflow, not just generate docs
```

**Output:** Skill that addresses root cause, not symptoms

---

### Lens 10: Comparative Analysis

**Core Question:** How do design options stack up against each other?

**Application to Skill Design:**
```
1. Define evaluation criteria
2. Weight criteria by importance
3. Score each option
4. Calculate weighted totals
5. Consider intangibles
```

**Comparison Template:**
```markdown
## Architecture Comparison

| Criteria | Weight | Option A | Option B | Option C |
|----------|--------|----------|----------|----------|
| Simplicity | 25% | 8 | 6 | 9 |
| Power | 30% | 7 | 9 | 6 |
| Extensibility | 25% | 6 | 8 | 8 |
| Maintenance | 20% | 8 | 5 | 7 |
|------------|--------|----------|----------|----------|
| **Weighted** | | 7.15 | 7.2 | 7.4 |

Winner: Option C (with consideration for team familiarity)
```

**Output:** Justified architecture selection

---

### Lens 11: Opportunity Cost

**Core Question:** What are we giving up by choosing this approach?

**Application to Skill Design:**
```
1. List all options considered
2. For each, identify what's sacrificed
3. Quantify trade-offs
4. Make informed choice with eyes open
```

**Trade-off Documentation:**
```markdown
## Opportunity Costs

Chosen: Multi-agent synthesis panel

What we gain:
- Multiple perspectives
- Higher quality output
- Reduced blind spots

What we sacrifice:
- Execution speed (3 agents vs 1)
- Token usage (3x for panel)
- Complexity of coordination

Why the trade-off is worth it:
- Quality is primary goal
- Speed can be optimized later
- Coordination complexity is bounded
```

**Output:** Explicit trade-off documentation

---

## Lens Application Protocol

### Phase 1: Rapid Scan (All 11 Lenses)

Scan each lens briefly to identify which are most relevant:

```markdown
## Lens Relevance Assessment

| Lens | Relevance (H/M/L) | Key Insight |
|------|-------------------|-------------|
| First Principles | High | Need to strip away X convention |
| Inversion | High | Clear failure mode: Y |
| Second-Order | Medium | Minor downstream effects |
| Pre-Mortem | High | Major risk: Z |
| Systems | Medium | Integration point: W |
| Devil's Advocate | Low | Decision is clear-cut |
| Constraints | Medium | False constraint: V |
| Pareto | High | 80% value from 2 features |
| Root Cause | High | Addressing symptom not cause |
| Comparative | Low | Only one viable option |
| Opportunity Cost | Medium | Trade-off is acceptable |
```

### Phase 2: Deep Dive (High-Relevance Lenses)

For each High-relevance lens:
1. Apply the full protocol described above
2. Document insights in structured format
3. Integrate insights into design
4. Note any conflicts with other lenses

### Phase 3: Conflict Resolution

When lenses suggest conflicting approaches:
1. State each perspective clearly
2. Identify the underlying tension
3. Determine which lens should dominate for this decision
4. Document the resolution and rationale

---

## Integration with Skill Creation

### Output Format

Each lens produces structured output that feeds into the specification:

```xml
<lens_analysis>
  <lens name="first_principles">
    <core_insight>The fundamental need is X, not Y</core_insight>
    <implications>
      <implication>Design should focus on A</implication>
      <implication>Remove unnecessary B</implication>
    </implications>
    <design_changes>
      <change>Simplified phase structure</change>
    </design_changes>
  </lens>
  <!-- Additional lenses... -->
</lens_analysis>
```

### Minimum Coverage

Before proceeding to specification generation:
- [ ] All 11 lenses scanned for relevance
- [ ] At least 5 lenses applied in depth
- [ ] At least 3 actionable insights documented
- [ ] All High-relevance lenses fully applied
- [ ] Conflicts between lenses resolved
