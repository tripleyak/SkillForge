# ADR 0002: Deliver the Context Skill Advisor through Claude Code hooks, with opt-in Personal Context

- Status: Accepted
- Date: 2026-07-29 (v6)
- Supersedes: [ADR 0001](0001-proactive-context-skill-advisor.md)

## Context

ADR 0001 delivered proactive suggestions via a macOS launchd LaunchAgent plus
an instruction snippet appended to global agent files. The external audit
(SKILLFORGE_AUDIT.md 3.4, 3.7) showed this was a functional no-op with a bad
privacy posture: the scheduled runs analyzed the wrong directory, nothing
read the queue they wrote to, per-day caps existed only in config, personal
directories and hardcoded GitHub handles were scanned by default, and the
installer mutated global state without consent.

The delivery problem has a structural answer: suggestions are only useful
inside an agent session, so they should be produced where the agent already
is, with the session's real cwd and the user's real prompt as input.

## Decision

1. **Delivery moves to Claude Code hooks.**
   - `scripts/hooks/session_start.py` (SessionStart): surfaces pending,
     unexpired, unsnoozed Advisory Queue suggestions for the current project
     as a compact additionalContext block, capped by the Proactivity Level.
     Silent (exit 0, no output) when there is nothing to show.
   - `scripts/hooks/user_prompt_submit.py` (UserPromptSubmit): a fast inline
     checkpoint that scores the submitted prompt against the prebuilt skill
     index and emits at most one short suggestion line. Hard time budget
     under 2 seconds: it never rebuilds the index and never touches Personal
     Context. Per-session and per-day caps from PROACTIVITY_SETTINGS are
     enforced through a local state file, fixing the dead `max_daily` config.
   - Hooks read their JSON payload from stdin (the Claude Code hook
     interface), never interpolate payload text into shell strings, run no
     subprocesses, and always exit 0 so a hook failure cannot break a
     session.
   - Hook registration is opt-in: `install_skillforge.py` offers it
     interactively (or via `--enable-hooks`), backs up
     `~/.claude/settings.json`, and merges into existing hooks config rather
     than replacing it.

2. **Scheduled background advising is no longer installed.** The installer
   removes any previously installed SkillForge launchd plist (unload +
   delete). `context_advisor.py run` remains for users who wire their own
   scheduler, but now requires an explicit `--cwd` so a run can never
   silently analyze an arbitrary directory.

3. **Personal Context becomes strictly opt-in.** `DEFAULT_CONFIG` ships with
   the personal tier disabled, an empty paths list, and an empty GitHub
   owner list. `context_sources.py` refuses to scan personal paths or GitHub
   metadata unless the config records explicit consent
   (`"consented": true` with a timestamp, written only by the installer's
   opt-in flow or the `--personal-paths`/`--github-owners` flags).
   Credential-looking lines (password/api key/token/secret assignments) are
   redacted before any text enters evidence excerpts. Session and Project
   tiers stay enabled by default.

4. **Suggestions become skill use only after user confirmation.** The former
   "explicit host direction" escape hatch is removed; hooks and queue output
   always instruct the agent to ask the user first.

## Alternatives considered

- **Keep launchd, fix the bugs** (pass `--cwd`, add a queue reader).
  Rejected: even fixed, a daemon runs outside any session, must guess which
  project matters, burns a Python process on an interval for a user who may
  not open a session all day, is macOS-only, and requires install-time
  mutation of LaunchAgents. The consumption side would still depend on
  agents voluntarily following a CLAUDE.md snippet.
- **cron / systemd timers for portability.** Rejected for the same
  structural reason: any out-of-session scheduler has no session context and
  no delivery channel into the conversation.
- **Instruction-snippet-only delivery** (agents told to run `checkpoint` at
  key moments). Rejected: compliance is voluntary and unverifiable; the
  audit showed it simply did not happen. Hooks are mechanical.
- **A Stop/PostToolUse hook instead of UserPromptSubmit.** Rejected: the
  user's prompt is the highest-signal, cheapest checkpoint input, and
  UserPromptSubmit is the documented injection point for additionalContext
  before the model acts on the prompt.
- **Skill-frontmatter hooks bundled with the SkillForge skill.** Rejected
  for delivery: skill hooks activate with the skill, but the advisor must
  observe sessions where SkillForge is never invoked. Global settings.json
  registration (with consent) is the honest scope.

## Consequences

- Suggestions arrive in-context where they can be acted on; the dead-queue
  and wrong-cwd failure modes are structurally impossible.
- The UserPromptSubmit hook adds a small latency cost to every prompt in
  consenting installs; the sub-2s budget, prebuilt-index-only rule, and
  personal-tier exclusion bound it, and caps keep it silent almost always.
- Users who never register hooks get no proactive delivery (queue tools
  still work manually); that is the intended consent boundary, not a bug.
- Cross-runtime (Codex) delivery loses its scheduler; other runtimes need
  their own hook-equivalent integration before proactive delivery returns
  there.
- The advisor now depends on the index being refreshed by normal SkillForge
  use (`discover_skills.py` auto-refresh); a machine where SkillForge is
  never used interactively will eventually have a stale index, which the
  hook tolerates by design (stale suggestions beat a 30-second inline
  rebuild).
