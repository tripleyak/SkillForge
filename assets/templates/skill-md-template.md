---
name: {{SKILL_NAME}}
description: >
  {{DESCRIPTION}}
license: MIT
model: claude-opus-4-5-20251101
user-invocable: true
# Uncomment to restrict available tools:
# allowed-tools:
#   - Read
#   - Glob
#   - Grep
#   - Bash
# Uncomment for isolated sub-agent execution:
# context: fork
# agent: general-purpose
metadata:
  version: 1.0.0
  author: {{AUTHOR}}
---

# {{SKILL_TITLE}}

{{BRIEF_INTRODUCTION}}

## Triggers

- `{{TRIGGER_1}}` - {{TRIGGER_1_DESC}}
- `{{TRIGGER_2}}` - {{TRIGGER_2_DESC}}
- `{{TRIGGER_3}}` - {{TRIGGER_3_DESC}}

## Quick Reference

| Input | Output | Duration |
|-------|--------|----------|
| {{INPUT}} | {{OUTPUT}} | {{DURATION}} |

## Process

### Phase 1: {{PHASE_1_NAME}}

{{PHASE_1_PURPOSE}}

1. **{{STEP_1_NAME}}** - {{STEP_1_DESC}}
2. **{{STEP_2_NAME}}** - {{STEP_2_DESC}}

**Verification:** {{PHASE_1_VERIFICATION}}

### Phase 2: {{PHASE_2_NAME}}

{{PHASE_2_PURPOSE}}

1. **{{STEP_1_NAME}}** - {{STEP_1_DESC}}
2. **{{STEP_2_NAME}}** - {{STEP_2_DESC}}

**Verification:** {{PHASE_2_VERIFICATION}}

## Anti-Patterns

| Avoid | Why | Instead |
|-------|-----|---------|
| {{ANTI_PATTERN_1}} | {{REASON_1}} | {{ALTERNATIVE_1}} |
| {{ANTI_PATTERN_2}} | {{REASON_2}} | {{ALTERNATIVE_2}} |

## Verification

After execution:

- [ ] {{CHECK_1}}
- [ ] {{CHECK_2}}
- [ ] {{CHECK_3}}

## Extension Points

1. **{{EXTENSION_1_NAME}}:** {{EXTENSION_1_DESC}}
2. **{{EXTENSION_2_NAME}}:** {{EXTENSION_2_DESC}}

## References

- [{{REF_1_NAME}}](references/{{REF_1_FILE}}) - {{REF_1_DESC}}
