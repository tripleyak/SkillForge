# Evolution Scoring Framework

The Evolution/Timelessness lens is the core evaluative perspective for SkillForge v4.0. Every skill must score ≥7 on timelessness to be approved.

## Overview

Evolution scoring answers: "How will this skill age?"

Skills that score poorly become:
- Maintenance burdens
- Sources of confusion as they become outdated
- Obstacles to ecosystem evolution
- Technical debt for future Claude users

**Requirement:** All generated skills must score ≥7/10 on timelessness.

---

## Timelessness Scoring Rubric

### Score 1-2: Ephemeral

**Characteristics:**
- Tightly coupled to specific API versions
- Hardcoded tool versions or paths
- Addresses a transient trend
- No consideration of change

**Example:**
```markdown
# Skill: Format for GPT-3.5-Turbo
Formats prompts specifically for the gpt-3.5-turbo-0301 API...
```

**Lifespan:** Weeks to months

**Verdict:** Reject. Fundamentally flawed approach.

---

### Score 3-4: Short-Lived

**Characteristics:**
- Depends on specific tooling likely to change
- Addresses problem in way specific to current moment
- Some structure but no extension consideration
- May reference volatile external resources

**Example:**
```markdown
# Skill: React Class Component Generator
Generates class components following React 17 patterns...
```

**Lifespan:** 6 months to 1 year

**Verdict:** Reject. Needs fundamental redesign with evolution in mind.

---

### Score 5-6: Moderate Longevity

**Characteristics:**
- Sound core approach
- Some hardcoded elements that may change
- Missing explicit extension points
- Limited temporal projection

**Example:**
```markdown
# Skill: API Documentation Generator
Generates OpenAPI 3.0 specifications...
(No consideration for OpenAPI 4.0 or alternatives)
```

**Lifespan:** 1-2 years

**Verdict:** Requires revision. Add extension points, document evolution path.

---

### Score 7-8: Solid Design

**Characteristics:**
- Principle-based rather than implementation-specific
- Clear extension points documented
- Dependencies abstracted appropriately
- Temporal projection completed
- Graceful degradation designed

**Example:**
```markdown
# Skill: API Documentation Generator
Generates API documentation following industry standards.
Supports OpenAPI 3.x with extension point for future specs.
Pattern-based approach adaptable to new documentation formats.
```

**Lifespan:** 2-4 years

**Verdict:** Approved. Good balance of current utility and future resilience.

---

### Score 9-10: Timeless

**Characteristics:**
- Addresses fundamental, unchanging problem
- Completely principle-based
- Highly composable with other skills
- Designed for evolution from day one
- Could serve as a pattern for other skills

**Example:**
```markdown
# Skill: Systematic Problem Decomposition
Breaks complex problems into verifiable atomic steps.
Pattern: Define → Decompose → Verify → Iterate
(This process is timeless regardless of technology)
```

**Lifespan:** 5+ years

**Verdict:** Exemplary. Consider as template for other skills.

---

## Scoring Process

### Step 1: Temporal Projection Analysis

For each time horizon, evaluate:

```markdown
## Temporal Projection

### 6 Months
- **Usage patterns:** How will typical usage differ?
- **Ecosystem changes:** What in the environment might change?
- **Risk assessment:** What could break?
- **Confidence:** High/Medium/Low

### 1 Year
- **Usage patterns:** ...
- **Ecosystem changes:** ...
- **Risk assessment:** ...
- **Confidence:** ...

### 2 Years
- **Usage patterns:** ...
- **Ecosystem changes:** ...
- **Risk assessment:** ...
- **Confidence:** ...

### 5 Years
- **Core problem relevance:** Is the problem still relevant?
- **Approach validity:** Is the solution approach still valid?
- **Confidence:** ...
```

### Step 2: Dependency Stability Assessment

Classify all dependencies:

| Dependency | Type | Stability | Change Likelihood | Abstraction |
|------------|------|-----------|-------------------|-------------|
| Claude API | External | Stable | Low (backward compat) | Direct |
| Specific model ID | External | Volatile | High | Should abstract |
| Skill patterns | Internal | Stable | Low | Direct OK |
| Specific tool | External | Moderate | Medium | Should abstract |

**Abstraction requirement:** Volatile and Moderate-stability dependencies MUST be abstracted.

### Step 3: Extension Point Evaluation

For each extension point:

```markdown
| Extension Point | Type | Use Case | Mechanism |
|----------------|------|----------|-----------|
| Pattern plugins | Feature | New architecture patterns | Add to patterns/ |
| Lens additions | Capability | New thinking models | Add to lenses/ |
| Output formats | Output | New file formats | Template-based |
| Validation rules | Quality | New checks | Config-based |
```

**Minimum requirement:** At least 2 documented extension points.

### Step 4: Anti-Obsolescence Pattern Check

Verify these patterns are applied:

| Pattern | Applied? | Evidence |
|---------|----------|----------|
| Principle over implementation | ☐ | Shows general approach, not specific tool |
| WHY documented | ☐ | Decisions include rationale |
| Loose coupling | ☐ | Dependencies abstracted |
| Graceful degradation | ☐ | Fallbacks for breaking changes |
| Version-agnostic | ☐ | No hardcoded versions |
| Ecosystem-aware | ☐ | Considers related skills |

---

## Common Evolution Anti-Patterns

### Anti-Pattern 1: Version Pinning

**Wrong:**
```markdown
Uses claude-3-5-sonnet-20241022 for analysis...
```

**Right:**
```markdown
Uses configured model (default: claude-opus-4-6, configurable)...
```

### Anti-Pattern 2: Tool-Specific Design

**Wrong:**
```markdown
# ESLint Config Generator
Generates .eslintrc.json for ESLint 8...
```

**Right:**
```markdown
# Linting Configuration Generator
Generates linting configuration for JavaScript/TypeScript.
Default: ESLint (configurable via lint_tool parameter).
Extension point for future linting tools.
```

### Anti-Pattern 3: Missing Extension Points

**Wrong:**
```markdown
## Supported Patterns
- Single-Phase
- Multi-Phase
- Orchestrator
(closed list)
```

**Right:**
```markdown
## Supported Patterns
Built-in patterns: Single-Phase, Multi-Phase, Orchestrator
Custom patterns: Add to `patterns/` directory following template
```

### Anti-Pattern 4: Implicit Dependencies

**Wrong:**
```markdown
Run `npm run build` to verify...
```

**Right:**
```markdown
Run verification command (default: `npm run build`,
configurable via BUILD_COMMAND or skill config)
```

### Anti-Pattern 5: Point-in-Time Assumptions

**Wrong:**
```markdown
Since Claude now supports 200K context...
```

**Right:**
```markdown
Leverage available context window
(designed to scale with future context increases)
```

---

## Score Adjustment Factors

### Positive Adjustments (+0.5 to +1)

| Factor | Adjustment | Criteria |
|--------|------------|----------|
| Exemplary extension design | +1 | Clear, documented, tested extension mechanism |
| Principle documentation | +0.5 | WHY documented for all decisions |
| Ecosystem integration | +0.5 | Seamless composition with 3+ skills |
| Graceful degradation | +0.5 | Handles all identified breaking changes |

### Negative Adjustments (-0.5 to -2)

| Factor | Adjustment | Criteria |
|--------|------------|----------|
| Hardcoded version | -1 | Any non-abstracted version reference |
| Missing extension points | -1 | Fewer than 2 documented |
| No temporal projection | -2 | No 6mo/1yr/2yr analysis |
| Tight external coupling | -1 | Direct dependency on volatile resource |

---

## Evolution Score Template

```markdown
## Evolution Analysis for [Skill Name]

### Base Score Assessment
| Criterion | Score (1-10) | Evidence |
|-----------|--------------|----------|
| Core approach timelessness | X | [evidence] |
| Dependency management | X | [evidence] |
| Extension point quality | X | [evidence] |
| Temporal projection depth | X | [evidence] |
| **Average** | **X.X** | |

### Adjustments
| Factor | Adjustment | Reason |
|--------|------------|--------|
| [Factor] | +/-X | [Reason] |

### Final Score: X/10

### Verdict: APPROVED / NEEDS REVISION

### If Needs Revision:
1. [Specific improvement required]
2. [Specific improvement required]
```

---

## Integration with Synthesis Panel

The Evolution/Timelessness Agent in the synthesis panel uses this framework to evaluate generated skills. The agent:

1. Applies the full scoring rubric
2. Documents score justification
3. Identifies specific improvements if score < 7
4. Only approves if score ≥ 7

**Unanimous approval requires all three agents, including Evolution Agent, to approve.**
