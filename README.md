# SkillForge v6

**A skill creator that proves its skills work.**

SkillForge routes any skill-related request (use, improve, create, compose), creates new skills through an evidence-driven pipeline, and maintains the health of your whole skill ecosystem. Its core principle: **skill quality is a property of behavior, not documents** - a skill is done when a fresh agent demonstrably does better with it than without it.

## What v6 changed (and why)

v6 is a ground-up rework following a deep external audit (see `SKILLFORGE_AUDIT.md` on the repo, not shipped with the skill). The headline shifts:

| v5 | v6 |
|---|---|
| 4-agent "unanimous synthesis panel" reads the skill | Skills are **executed**: baseline (RED) runs before writing, with-skill (GREEN) runs after, behavioral delta is the gate |
| Self-scored "timelessness >= 7" approval | Falsifiable checks moved to lint (`validate_skill.py`); one adversarial reviewer refutes what lint can't catch |
| 5,049-word SKILL.md with `<details>` "progressive disclosure" | 1,158-word SKILL.md; depth lives in `references/` loaded on demand |
| Descriptions = "what this skill does" | Descriptions = trigger conditions only (workflow summaries make agents skip the body) |
| launchd background advisor that analyzed `/` and queued into a file nothing read | Advisor delivered through Claude Code hooks (SessionStart + UserPromptSubmit), caps enforced, opt-in |
| Personal-directory scanning on by default, hardcoded GitHub handles | Personal Context strictly opt-in with recorded consent; no shipped defaults |
| Hand-rolled YAML parser that failed SkillForge's own SKILL.md | One shared typed parser (`scripts/frontmatter.py`), 100+ unit tests, and a regression test that SkillForge validates itself |
| Index missed the Claude Code plugin cache entirely | Cross-runtime discovery: personal, Codex, Claude Code plugin cache; deduped; auto-refresh |

## The pipeline

```
Phase 0  TRIAGE      index + word-boundary matching -> USE | IMPROVE | CREATE | COMPOSE | CLARIFY
Phase 0b RED GATE    fresh subagent attempts the task WITHOUT the skill; no failure = no skill
Phase 1  ANALYSIS    load-bearing lenses (Inversion, Pareto, Root Cause), failure-form matching
Phase 2  SPEC        tiered (minimal default / full for infrastructure), decisions + WHY
Phase 3  GENERATE    fresh-context subagent receives ONLY the spec + baseline failures
Phase 4  GREEN GATE  with-skill runs must clear the recorded baseline failures; trigger tests
Phase 5  REVIEW      lint (validate_skill.py) + ONE adversarial reviewer charged to refute
Phase 6  SHIP        with evals/ - a per-skill regression suite runnable forever after
```

## What no other skill creator has

- **Dedup before create** (Phase 0): an index of every skill across runtimes answers "should this exist?" first.
- **Skills ship with their tests**: `evals/` (trigger queries + behavioral scenarios) + `run_skill_evals.py` = regression testing for skills.
- **Ecosystem doctor**: `skillforge_doctor.py` finds trigger collisions between skills, duplicates, stale file references, budget violations, and pinned models across your entire roster.
- **Cross-runtime compile**: author once, `compile_skill.py --target claude|codex|agentskills`.
- **Friction mining** (opt-in): `mine_skill_friction.py --consent` finds skill gaps in your own local session history.
- **Proactive advisor** (opt-in): evidence-backed skill suggestions delivered via hooks, never auto-invoked.

## Install (Claude Code)

```bash
git clone https://github.com/tripleyak/SkillForge.git /tmp/skillforge
cp -r /tmp/skillforge ~/.claude/skills/skillforge
cd ~/.claude/skills/skillforge && rm -rf README.md LICENSE CONTEXT.md docs .git .gitignore .skillignore index.html assets/images scripts/tests SKILLFORGE_AUDIT.md
cp /tmp/skillforge/commands/skillforge.md ~/.claude/commands/skillforge.md   # optional /skillforge command
```

Optional advisor + hooks (interactive, everything opt-in):

```bash
python3 ~/.claude/skills/skillforge/scripts/install_skillforge.py
```

Requirements: Claude Code (or Codex CLI), Python 3.8+ (stdlib only; PyYAML used if present).

## Toolbox

| Command | Purpose |
|---|---|
| `python3 scripts/discover_skills.py` | Build/refresh the skill index |
| `python3 scripts/triage_skill_request.py "<request>" --json` | Route a request |
| `python3 scripts/validate_skill.py <dir>` | Full validation + lint |
| `python3 scripts/run_skill_evals.py <dir> [--live]` | Run a skill's regression evals |
| `python3 scripts/skillforge_doctor.py` | Ecosystem health report |
| `python3 scripts/init_skill.py <name> --path <dir>` | Scaffold (includes evals/) |
| `python3 scripts/compile_skill.py <dir> --target <t>` | Cross-runtime compile |
| `python3 scripts/package_skill.py <dir> ./dist` | Package as .skill |
| `python3 scripts/mine_skill_friction.py --consent` | Mine local transcripts for skill gaps |

CI: copy `assets/templates/github-workflow-skill-ci.yml` into `.github/workflows/` of any skill repo.

## License

MIT - see [LICENSE](LICENSE)
