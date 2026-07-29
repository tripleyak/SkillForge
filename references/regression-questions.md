# Regression Questioning Protocol

The core methodology for exhaustive skill analysis. These questions are applied iteratively until no new insights emerge.

## Overview

Regression questioning prevents premature convergence on suboptimal designs by systematically exploring the problem space. The goal is not just to answer questions, but to discover questions that haven't been asked yet.

**Termination Criteria** (honesty note: "no new insights" is self-report and cannot be verified externally - so a hard cap applies: maximum 4 productive rounds, stop earlier when a round changes no design decision):
- Three consecutive rounds produce no new insights
- All thinking models have been applied
- At least 3 simulated expert perspectives considered
- Evolution/timelessness explicitly evaluated with score ≥7

---

## Question Categories

### Category 1: Missing Elements

These questions identify gaps in the current analysis.

| Question | Purpose | When to Ask |
|----------|---------|-------------|
| "What am I missing?" | Open-ended gap detection | Every round |
| "What haven't I considered?" | Blind spot identification | After initial design |
| "What assumptions am I making?" | Expose implicit decisions | When design feels "obvious" |
| "What's not in the requirements but should be?" | Implicit requirement discovery | After requirements analysis |
| "What edge cases haven't I addressed?" | Boundary condition coverage | After main flow defined |

**Red Flag Responses:**
- "I think I've covered everything" → Ask 3 more specific questions
- "This seems complete" → Apply another thinking model

### Category 2: Expert Simulation

Simulate domain experts reviewing the design.

| Expert Type | Key Questions | Focus Areas |
|-------------|---------------|-------------|
| **Domain Expert** | "What would an expert in {DOMAIN} add?" | Domain-specific patterns, jargon, conventions |
| **UX Expert** | "Is this intuitive for the target audience?" | Cognitive load, discoverability, error handling |
| **Systems Architect** | "How does this integrate with existing systems?" | Dependencies, coupling, composition |
| **Security Expert** | "What could go wrong from a security perspective?" | Input validation, privilege escalation, data exposure |
| **Performance Expert** | "What are the performance implications?" | Token usage, iteration count, timeout risks |
| **Maintenance Engineer** | "Will this be maintainable in 2 years?" | Clarity, documentation, extension points |

**Application Protocol:**
1. For each relevant expert type, fully adopt their perspective
2. Critique the current design from that viewpoint
3. Document specific improvements they would suggest
4. Integrate improvements before proceeding

### Category 3: Failure Analysis

Proactively identify failure modes.

| Question | Failure Mode Targeted |
|----------|----------------------|
| "What would make this skill fail completely?" | Catastrophic failures |
| "What would make this skill produce wrong results?" | Silent failures |
| "What would make users abandon this skill?" | Adoption failures |
| "What would make this skill obsolete?" | Evolution failures |
| "What would make this skill unmaintainable?" | Technical debt |
| "What would make this skill conflict with others?" | Ecosystem failures |

**For Each Identified Failure Mode:**
1. Assess likelihood (High/Medium/Low)
2. Assess impact (Critical/Major/Minor)
3. Design mitigation or prevention
4. Document in anti-patterns section

### Category 4: Temporal Projection

Evaluate the design across time horizons.

| Timeframe | Question | Focus |
|-----------|----------|-------|
| **Now** | "Does this solve the immediate problem?" | Current utility |
| **1 week** | "Will the first users succeed?" | Initial experience |
| **1 month** | "What feedback will we receive?" | Early adoption issues |
| **6 months** | "How will usage patterns evolve?" | Maturation |
| **1 year** | "What ecosystem changes are likely?" | External pressures |
| **2 years** | "Will the core approach still be valid?" | Fundamental soundness |
| **5 years** | "Is the underlying problem still relevant?" | Problem evolution |

**Temporal Analysis Output:**
```markdown
## Temporal Projection

| Horizon | Expected State | Risks | Mitigations |
|---------|----------------|-------|-------------|
| 6mo | [description] | [risks] | [mitigations] |
| 1yr | [description] | [risks] | [mitigations] |
| 2yr | [description] | [risks] | [mitigations] |
```

### Category 5: Completeness Verification

Ensure all analytical frameworks have been applied.

| Check | Question |
|-------|----------|
| **Thinking Models** | "Which of the 11 thinking models haven't I applied yet?" |
| **Domain Coverage** | "Have I addressed all relevant domains (design, architecture, UX, etc.)?" |
| **Stakeholder Coverage** | "Have I considered all stakeholder perspectives?" |
| **Integration Coverage** | "Have I evaluated integration with all related skills?" |
| **Quality Attributes** | "Have I addressed performance, security, maintainability?" |

### Category 6: Meta-Questioning

Questions about the questioning process itself.

| Question | Purpose |
|----------|---------|
| "Did the last round change any design decision?" | If no: stop - further rounds are ritual |
| "What question haven't I asked?" | Discover unknown unknowns |
| "If I had to defend this to a critic, where would I struggle?" | Identify weak points |
| "What would I add with unlimited time?" | Identify deferred improvements |
| "What's the most controversial aspect of this design?" | Surface hidden assumptions |

### Category 7: Script and Automation Analysis

Questions for determining script needs and enabling autonomous operation.

| Question | Purpose |
|----------|---------|
| "What operations will be repeated identically across uses?" | Identify determinism needs |
| "What outputs require validation before the skill can proceed?" | Identify verification scripts |
| "What state needs to persist between skill invocations?" | Identify state management |
| "How will Claude verify the skill executed correctly?" | Enable autonomous verification |
| "What existing scripts in the ecosystem could be reused?" | Avoid reinventing |
| "Can this skill run overnight without human intervention?" | Assess agentic capability |
| "What would break if executed manually vs scripted?" | Identify fragile operations |
| "How would another Claude instance recover from a script failure?" | Design error handling |

**Script Decision Protocol:**

For each affirmative answer:
1. **Classify the script category:**
   - Validation (verify artifacts)
   - State Management (persist data)
   - Generation (create artifacts)
   - Transformation (convert data)
   - Integration (external tools)
   - Visualization (progress/status)
   - Calculation (metrics/scores)

2. **Select patterns from catalog:**
   - Result dataclass for return values
   - ValidationResult for multi-check validation
   - argparse with subcommands for multi-operation
   - JSON state for persistence
   - Graceful fallback for optional dependencies

3. **Document in specification:**
   ```xml
   <script id="S1">
     <name>validate_output.py</name>
     <category>validation</category>
     <purpose>Verify generated artifacts meet quality standards</purpose>
     <patterns_used>
       <pattern>ValidationResult</pattern>
       <pattern>simple_argparse</pattern>
     </patterns_used>
   </script>
   ```

4. **Design self-verification:**
   - Every script should return success/failure via exit code
   - Complex operations should verify their own outputs
   - Error messages should be actionable

**Research Existing Scripts:**
```bash
# Search for similar scripts in the ecosystem
find ~/.claude/skills -name "*.py" -path "*/scripts/*" | xargs grep -l "<pattern>"

# List available validation patterns
grep -r "ValidationResult\|validate" ~/.claude/skills/*/scripts/
```

**Agentic Capability Checklist:**
After script analysis, verify:

- [ ] Autonomous Execution: Can skill run without user intervention?
- [ ] Self-Verification: Can scripts verify their own outputs?
- [ ] Error Recovery: Can scripts retry or recover from failures?
- [ ] State Persistence: Is progress saved across sessions?
- [ ] Structured Output: Do scripts output machine-readable data?

See: [script-integration-framework.md](script-integration-framework.md), [script-patterns-catalog.md](script-patterns-catalog.md)

---

## Round Structure

Each questioning round follows this structure:

```
ROUND N:

1. Apply 2-3 questions from different categories
2. Document all insights discovered
3. Integrate insights into design
4. Assess: New insights > 0?
   - YES → Proceed to Round N+1
   - NO → Check termination criteria
```

### Example Round Execution

```markdown
## Round 3 Analysis

### Questions Applied:
1. Expert Simulation: "What would a UX expert add?"
2. Failure Analysis: "What would make users abandon this skill?"
3. Temporal: "How will usage patterns evolve in 6 months?"

### Insights Discovered:
1. UX Expert: Trigger phrases are too technical; add natural language alternatives
2. Failure: No graceful degradation if analysis takes too long
3. Temporal: May need --quick mode for simpler skills

### Design Updates:
- Added 2 natural language triggers
- Added timeout handling with partial results
- Documented --quick flag as future extension point

### Verdict: 3 new insights → Continue to Round 4
```

---

## Question Bank by Skill Type

### For Executor Skills
- "What inputs could cause unexpected behavior?"
- "What outputs should be validated before returning?"
- "What side effects need to be documented?"

### For Analyzer Skills
- "What analysis could give misleading results?"
- "What context is essential for accurate analysis?"
- "What confidence level should outputs indicate?"

### For Generator Skills
- "What templates or patterns should be used?"
- "What customization points are needed?"
- "What validation ensures output quality?"

### For Orchestrator Skills
- "What skills might this need to compose with?"
- "What handoff format works for all composed skills?"
- "What happens if a composed skill fails?"

### For Validator/Checker Skills
- "What false positives are likely?"
- "What false negatives are dangerous?"
- "What severity levels are appropriate?"

---

## Anti-Patterns in Questioning

| Anti-Pattern | Problem | Instead |
|--------------|---------|---------|
| Surface-level questioning | Misses deep issues | Apply 5 Whys technique |
| Single-perspective | Blind spots | Rotate through expert types |
| Premature termination | Incomplete analysis | Require 3 empty rounds |
| Confirmation bias | Validates existing ideas | Use Devil's Advocate lens |
| Question fatigue | Skip important questions | Use structured checklist |

---

## Integration with Other Phases

### Input to Specification Generation
All insights from regression questioning feed into the specification:
- Requirements discovered → `<requirements><discovered>` section
- Failure modes → `<anti_patterns>` section
- Temporal analysis → `<evolution_analysis>` section
- Expert insights → Architecture and design decisions

### Feedback from Synthesis Panel
If the synthesis panel rejects the skill:
- Panel feedback becomes new questions
- Return to Round 1 with feedback as input
- Re-apply relevant question categories
