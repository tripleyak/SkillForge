# Degrees of Freedom in Skill Design

When writing SKILL.md instructions, choose how much latitude to give Claude. Not every section needs the same level of specificity. The right choice depends on how fragile the operation is and how much valid variation exists.

Think of Claude as exploring a path: a narrow bridge with cliffs needs specific guardrails (low freedom), while an open field allows many routes (high freedom).

---

## The Three Levels

### High Freedom (Text-Based Instructions)

Give Claude prose descriptions and heuristics. Multiple approaches are valid.

**Use when:**
- Decisions depend on runtime context (user's codebase, project type)
- Heuristics guide the approach rather than exact steps
- Creative judgment adds value

**Example:**
```markdown
Analyze the user's codebase to determine the best testing strategy.
Consider the existing test framework, project size, and CI setup.
Prefer integration tests for API-heavy projects, unit tests for utility libraries.
```

**Typical sections:** Analysis phases, decision-making, recommendations, explanations.

### Medium Freedom (Pseudocode or Parameterized Steps)

Provide a preferred pattern with clear parameters, but allow variation in details.

**Use when:**
- A known-good pattern exists but details vary by context
- Configuration affects behavior
- The structure matters but exact values do not

**Example:**
```markdown
Generate the config file using this structure:

1. Read the user's package.json for project name and version
2. Set `output_dir` to `dist/` unless the user has a custom build directory
3. Include all `src/**/*.ts` files, excluding test files
4. Write to `<project-root>/<config-filename>`
```

**Typical sections:** Generation steps, file structures, configuration, templates.

### Low Freedom (Exact Scripts or Commands)

Provide specific scripts, exact commands, or rigid sequences. Minimal deviation allowed.

**Use when:**
- Operations are fragile and error-prone (file system mutations, API calls)
- Consistency is critical (validation, scoring, formatting)
- A specific sequence must be followed (multi-step workflows with dependencies)
- Getting it wrong has high cost (data loss, broken state)

**Example:**
```markdown
Run the validation script exactly as shown:

\`\`\`bash
python scripts/validate_output.py --strict --format json "$OUTPUT_PATH"
\`\`\`

Exit code 0 = pass. Any other code = fail. Do not proceed if validation fails.
```

**Typical sections:** Validation gates, script invocations, deployment steps, state mutations.

---

## Decision Matrix

| Factor | High Freedom | Medium Freedom | Low Freedom |
|--------|-------------|----------------|-------------|
| Valid approaches | Many | Several | One |
| Failure cost | Low | Medium | High |
| Context-dependent | Very | Somewhat | Not at all |
| Reproducibility need | Low | Medium | Critical |
| Example | "Choose a testing strategy" | "Generate config with this structure" | "Run this exact command" |

---

## Mixing Levels in One Skill

Most skills combine all three levels. A typical pattern:

1. **Analysis phase** -- high freedom (understand the problem)
2. **Planning phase** -- medium freedom (follow this structure, adapt details)
3. **Execution phase** -- low freedom (run these scripts, check these gates)
4. **Iteration phase** -- high freedom (decide what to improve)

The key insight: freedom should decrease as you move from thinking to acting. Analysis benefits from latitude; execution benefits from precision.

---

## Common Mistakes

| Mistake | Problem | Fix |
|---------|---------|-----|
| Low freedom everywhere | Skill is brittle, breaks on unexpected input | Use high freedom for analysis/decision phases |
| High freedom everywhere | Inconsistent outputs, no quality guarantees | Use low freedom for validation and execution |
| Medium freedom for validation | Validation must be deterministic | Drop to low freedom with exact scripts |
| Low freedom for analysis | Overfits to one scenario | Raise to high freedom with heuristics |

---

## Related References

- [Script Integration Framework](script-integration-framework.md) -- scripts are the primary tool for low-freedom sections
- [Multi-Lens Framework](multi-lens-framework.md) -- analysis lenses are high-freedom by design
