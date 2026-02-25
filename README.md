# SkillForge v5.0

**From Art to Engineering: A Manifesto for AI Skill Creation.**

![SkillForge](assets/images/01-title.png)

---

## The Problem

The central challenge in AI development isn't a lack of ideas, but the inconsistent process of turning them into robust, reliable skills. Current methods are often ad-hoc, brittle, and difficult to scale—resembling more of an art form than a predictable engineering discipline.

![The Quality Gap](assets/images/02-quality-gap.png)

---

## The Solution

**Quality is built in, not bolted on.**

SkillForge is a methodology where rigor is integrated into every step of the creation process, from initial conception to final validation. It's a fundamental shift from reactive testing to proactive engineering.

![Quality Built In](assets/images/03-quality-built-in.png)

---

## What's New in v5.0

### Context-Efficient Redesign

v5.0 is built around a single insight: **the context window is a public good.** Every line in SKILL.md competes with the user's actual work. SkillForge now practices what it preaches.

- **SKILL.md slimmed from 872 to 313 lines** (64% reduction)
- Deep dives moved to `references/` where they're loaded only when needed
- Triggers moved into `description` field for pre-load routing

### Simplified Frontmatter

Skills now use only `name` and `description` in frontmatter. The `description` field is the primary triggering mechanism — it determines when a skill activates, so all "when to use" information belongs there.

```yaml
---
name: my-skill
description: What this skill does and when to use it. Include trigger scenarios.
---
```

### Degrees of Freedom

A new design concept for matching instruction specificity to task fragility:

- **High freedom** (text guidance) — when multiple approaches are valid
- **Medium freedom** (pseudocode/parameterized scripts) — when a preferred pattern exists
- **Low freedom** (exact scripts) — when operations are fragile and error-prone

### Scaffold Script

New `init_skill.py` creates rich skill templates with TODO placeholders, organizational pattern suggestions, and example resource files:

```bash
python scripts/init_skill.py my-new-skill --path ~/.codex/skills
```

### Iteration as a Formal Step

Iteration is now built into Phase 3. Skills improve through real usage, not just synthesis panel review.

---

## The 4-Phase Architecture

SkillForge implements its philosophy through a rigorous, autonomous 4-phase architecture. This structure ensures that every skill undergoes comprehensive analysis, thorough specification, clean generation, and objective approval before it is complete.

![4-Phase Architecture](assets/images/04-four-phase-architecture.png)

---

## Phase 0: Skill Triage

Before creating anything, SkillForge analyzes your input to determine the best action:

- **USE_EXISTING** — Existing skill handles this perfectly (match ≥80%)
- **IMPROVE_EXISTING** — Existing skill is close but needs enhancement (match 50-79%)
- **CREATE_NEW** — No good match, create new skill (match <50%)
- **COMPOSE** — Multiple skills needed, suggest chain

```bash
# These all work - SkillForge routes automatically:

SkillForge: create a skill for automated code review
→ Creates new skill (Phase 1-4)

help me debug this TypeError
→ Recommends debugging skills

do I have a skill for Excel?
→ Searches and recommends matching skills
```

---

## Phase 1: Deep Analysis

**Maximum depth before a single line is generated.**

Every problem is systematically deconstructed through **11 distinct thinking lenses**, with degrees of freedom assessed for each design decision.

![Phase 1: Thinking Lenses](assets/images/05-phase1-thinking-lenses.png)

The 11 lenses include: First Principles, Inversion, Second-Order Effects, Pre-Mortem, Systems Thinking, Devil's Advocate, Constraints, Pareto, Root Cause, Comparative, and Opportunity Cost.

---

## Phases 2 & 3: Specification & Generation

**Translating deep analysis into a flawless build.**

The insights from analysis are codified into a structured XML specification, then used to generate the skill with fresh context. Phase 3 now includes an explicit **iteration step** — review output against spec, identify gaps, and refine before panel review.

![Phases 2 & 3](assets/images/06-phases-2-3.png)

---

## Phase 4: Multi-Agent Synthesis

**A panel of experts demands unanimous approval.**

A generated skill is submitted to a panel of specialized agents, each evaluating against distinct criteria. **Approval must be unanimous.**

![Phase 4: Multi-Agent Synthesis](assets/images/07-phase4-synthesis.png)

The panel includes:
- **Design/Architecture Agent** — Structure, patterns, correctness
- **Audience/Usability Agent** — Clarity, discoverability, completeness
- **Evolution Agent** — Timelessness, extensibility, future-readiness (score ≥7/10 required)
- **Script Agent** (conditional) — Validates code quality when scripts are present

---

## Evolution Mandate

Skill quality is not enough on day one. The system must stay maintainable and extensible as the skill ecosystem grows.

![Evolution Mandate](assets/images/08-evolution-mandate.png)

---

## Three Core Principles

![Core Principles](assets/images/09-core-principles.png)

| Principle | Implementation |
|-----------|----------------|
| **Engineer for Agents** | Standardized directory structure, simplified frontmatter, automated validation |
| **Systematize Rigor** | 4-phase architecture, regression questioning, 11 thinking lenses, multi-agent synthesis |
| **Design for Evolution** | Dedicated Evolution agent, mandatory ≥7/10 timelessness score, degrees of freedom assessment |

---

## Agentic Capabilities

SkillForge is designed so skills can execute repeatable work, validate outputs, and support autonomous operation where appropriate.

![Agentic Capabilities](assets/images/10-agentic-capabilities.png)

---

## Directory Structure

```
skillforge/
├── SKILL.md                    # Main skill definition (< 500 lines)
├── LICENSE                     # MIT License
├── references/                 # Loaded into context when needed
│   ├── regression-questions.md
│   ├── multi-lens-framework.md
│   ├── specification-template.md
│   ├── evolution-scoring.md
│   ├── synthesis-protocol.md
│   ├── script-integration-framework.md
│   ├── script-patterns-catalog.md
│   ├── degrees-of-freedom.md
│   └── iteration-guide.md
├── assets/                     # Used in output, never loaded into context
│   └── templates/
│       ├── skill-spec-template.xml
│       ├── skill-md-template.md
│       └── script-template.py
└── scripts/                    # Automated quality gates
    ├── init_skill.py
    ├── triage_skill_request.py
    ├── discover_skills.py
    ├── match_skills.py
    ├── verify_recommendation.py
    ├── validate-skill.py
    ├── quick_validate.py
    └── package_skill.py
```

![Directory Structure Visual](assets/images/11-directory-structure.png)

**Key distinction:** `references/` = loaded into context to inform the model's reasoning. `assets/` = used in output, never loaded into context.

---

## Installation & Usage

![Installation](assets/images/12-installation.png)

```bash
# Install (excludes repo-only files like README.md automatically)
git clone https://github.com/tripleyak/SkillForge.git /tmp/skillforge

# Codex install
cp -r /tmp/skillforge ~/.codex/skills/skillforge
rm -rf ~/.codex/skills/skillforge/{README.md,LICENSE,.git,.gitignore,.skillignore}

# Claude Code install
cp -r /tmp/skillforge ~/.claude/skills/skillforge
rm -rf ~/.claude/skills/skillforge/{README.md,LICENSE,.git,.gitignore,.skillignore}

# Or package as .skill file (respects .skillignore)
python scripts/package_skill.py /tmp/skillforge ./dist

# Full autonomous execution
SkillForge: {goal}

# Natural language activation
create skill for {purpose}

# Generate specification only
skillforge --plan-only

# Scaffold a new skill
python scripts/init_skill.py my-skill --path ~/.codex/skills
```

> **Note:** `README.md`, `LICENSE`, and `assets/images/` are for GitHub browsing only. They are excluded from `.skill` packages via `.skillignore` and should not be copied into your skills directory.

---

## Requirements

- Codex CLI or Claude Code CLI
- Python 3.8+ (for validation and scaffold scripts)

---

## Conclusion

![Closing](assets/images/13-closing.png)

**SkillForge is a systematic methodology for quality and repeatability.**

By codifying expert analysis, rigorous specification, and multi-agent peer review into a fully autonomous system, SkillForge provides a blueprint for building the next generation of robust, reliable, and evolution-aware AI skills.

**It transforms skill creation from an art into an engineering discipline.**

---

## License

MIT License — see [LICENSE](LICENSE)

---

## Changelog

### v5.1.0 (Current)
- Added Codex compatibility to SKILL.md instructions and host paths
- Added Codex skill source discovery (`~/.codex/skills`) with uppercase `SKILL.md` support
- Updated scaffold and validation scripts to use Codex path examples
- Kept full backward compatibility with Claude Code paths
- Added additive README visuals for evolution mandate, agentic capabilities, and directory structure

### v5.0.0
- Context-efficient redesign: SKILL.md slimmed from 872 to 313 lines (64% reduction)
- Simplified frontmatter to `name` + `description` only
- Triggers moved into `description` for pre-load routing
- Added Degrees of Freedom concept and reference
- Added Iteration Guide as formal step in Phase 3
- Added `init_skill.py` scaffold script
- Updated validators for new frontmatter standard
- Removed README from skill distribution (GitHub-only)

### v4.0.0
- Renamed from SkillCreator to SkillForge
- Added Phase 0: Universal Skill Triage
- Added universal domain-based matching
- Added triage, discovery, matching, and verification scripts

### v3.2.0
- Added Script Integration Framework for agentic skills
- Added 4th Script Agent to synthesis panel (conditional)
- Added Phase 1D: Automation Analysis

### v3.0.0
- Complete redesign as ultimate meta-skill
- Added regression questioning loop
- Added multi-lens analysis framework (11 models)
- Added evolution/timelessness core lens
- Added multi-agent synthesis panel
