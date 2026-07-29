# ADR 0001: Proactive Context Skill Advisor with scheduled background advising

- Status: Superseded by [ADR 0002](0002-hooks-based-advisor.md)
- Date: 2026-07 (v5.2)

## Context

SkillForge could route skill requests only when explicitly asked. Users
working in a 300+ skill ecosystem routinely missed skills that would have
helped them, because nothing surfaced skills proactively. We wanted
evidence-backed, user-controlled proactive suggestions.

## Decision

Add a Context Skill Advisor that:

- surfaces Evidence-Backed Suggestions with `balanced` as the install-time
  Proactivity Level,
- draws on three Context Source Tiers (Session, Project, Personal), all
  enabled by default, constrained by Targeted Content Access (search broadly,
  read narrowly) rather than full indexing,
- runs through Advisor Checkpoints (agent-initiated) and Scheduled Background
  Advising (a launchd LaunchAgent on macOS invoking `context_advisor.py run`
  on an interval),
- writes suggestions to a persistent Advisory Queue, records feedback in
  Advisor State, and requires Confirmed Skill Use before invoking any
  suggested skill.

## Consequences (as designed)

More useful recommendations in exchange for a broader default context
surface, mitigated by confidence thresholds, explicit evidence, proactivity
levels, project overrides, and suppression feedback.

## Why this was superseded

The 2026-07 external audit (SKILLFORGE_AUDIT.md sections 3.4 and 3.7) found
the delivery and privacy design defective in practice:

- The launchd plist ran `context_advisor.py run` without `--cwd`, so every
  scheduled run analyzed `/` and queued nothing, forever.
- Nothing consumed the Advisory Queue: the snippet appended to
  `~/.claude/CLAUDE.md` told agents to run `checkpoint`, which never read
  `advice.jsonl`. `max_daily` caps were enforced nowhere.
- Personal Context scanning (personal directories + GitHub metadata) was
  opt-out and enabled by default, with the repo authors' GitHub handles
  hardcoded in `DEFAULT_CONFIG` for every installer.
- The installer appended to global agent instruction files and loaded a
  LaunchAgent without prompting.

ADR 0002 replaces scheduled background advising with Claude Code hook
delivery and flips Personal Context to explicit opt-in with recorded consent.
