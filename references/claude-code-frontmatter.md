# Claude Code SKILL.md frontmatter - current field reference

Verified against code.claude.com/docs/en/skills (2026). Claude Code supports 17 fields; the agentskills.io spec adds portability fields. Unknown fields are tolerated but do nothing.

## Claude Code fields

| Field | Type | Purpose |
|---|---|---|
| `name` | string | Skill/slash-command name. Defaults to directory name |
| `description` | string | THE triggering surface - the only text always in context. Trigger conditions only, third person |
| `when_to_use` | string | Extra routing text appended to description in listings (combined cap: 1,536 chars) |
| `argument-hint` | string | Hint shown in the slash menu, e.g. `[issue-number]` |
| `arguments` | - | Declared arguments; access via `$ARGUMENTS`, `$ARGUMENTS[N]`, `$N` |
| `disable-model-invocation` | bool | `true` = only the user can invoke (not auto-loaded by Claude) |
| `user-invocable` | bool | `false` = hidden from the `/` menu (Claude can still auto-invoke) |
| `allowed-tools` | list | Tools available while the skill is active |
| `disallowed-tools` | list | Tools removed while the skill is active |
| `model` | string | Model while active. Use family aliases; never pin dated IDs (`claude-*-YYYYMMDD` rots) |
| `effort` | string | Reasoning effort while active |
| `context` | `fork` | Run the skill in a forked subagent context instead of inline |
| `agent` | string | Subagent type when `context: fork` (`Explore`, `Plan`, custom; default `general-purpose`) |
| `background` | bool | Run as a background task |
| `hooks` | object | Lifecycle hooks scoped to this skill (see below) |
| `paths` | list | Extra directories the skill may access |
| `shell` | string | Shell for bash blocks |

## agentskills.io portability fields (valid, cross-runtime)

`license`, `metadata` (free-form: version, author, domains). Portability limits enforced by `validate_skill.py`: name ≤64 chars (lowercase, hyphens, must match directory), description ≤1024 chars.

## Hooks - correct interface

```yaml
hooks:
  PreToolUse:
    - matcher: "Bash"          # tool-name regex, e.g. "Bash" or "Write|Edit" - NOT permission syntax like Bash(python:*)
      hooks:
        - type: command
          command: "python3 scripts/check_input.py"
          once: true           # once: only honored for hooks declared in skill frontmatter
```

- Hook commands receive a **JSON payload on stdin** (`tool_name`, `tool_input`, etc.) and reply via exit code / stdout JSON. There are no `$TOOL_INPUT`/`$TOOL_OUTPUT` environment variables - parse stdin.
- Never interpolate tool payload text into shell command strings; read it from stdin inside the script.
- Skill-frontmatter hooks live only while the skill is active. Session-wide hooks belong in `~/.claude/settings.json`.

## Placement and structure

- Personal skills: `~/.claude/skills/<name>/SKILL.md`. Project: `.claude/skills/`. Plugins ship `skills/` directories.
- `.claude/commands/*.md` still work and share the `/` namespace; skills are the recommended form (supporting files, frontmatter).
- Keep SKILL.md under 500 lines / 1,500 words. Depth goes in `references/` (loaded on demand); files used in outputs go in `assets/`; executable helpers in `scripts/`. `<details>` tags do not save agent tokens - use separate files.
