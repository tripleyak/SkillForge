# SkillForge v4.0

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

## What's New in v4.0

### Phase 0: Universal Skill Triage

SkillForge now analyzes **any input**—prompts, errors, code, URLs—and automatically routes to the right action:

- **USE_EXISTING** - Existing skill handles this perfectly
- **IMPROVE_EXISTING** - Existing skill is close but needs enhancement
- **CREATE_NEW** - No good match, create new skill
- **COMPOSE** - Multiple skills needed, suggest chain

```bash
# These all work - SkillForge routes automatically:

SkillForge: create a skill for automated code review
→ Creates new skill (Phase 1-4)

help me debug this TypeError
→ Recommends debugging skills

do I have a skill for Excel?
→ Searches and recommends matching skills
```

### Universal Domain Matching

- Matches by **concept** (debugging, testing, spreadsheets) not hardcoded skill names
- Works for **everyone** regardless of what skills you have installed
- 20+ domain categories with intelligent synonym matching
- Graceful degradation - returns `CREATE_NEW` when no skills match

---

## The 4-Phase Architecture

SkillForge implements its philosophy through a rigorous, autonomous 4-phase architecture. This structure ensures that every skill undergoes comprehensive analysis, thorough specification, clean generation, and objective approval before it is complete.

![4-Phase Architecture](assets/images/04-four-phase-architecture.png)

---

## Phase 1: Deep Analysis

**Maximum depth before a single line is generated.**

Every problem is systematically deconstructed through **11 distinct thinking lenses**. This framework forces a holistic and unbiased evaluation, moving beyond surface-level requirements to uncover hidden constraints, edge cases, and long-term implications.

![Phase 1: Thinking Lenses](assets/images/05-phase1-thinking-lenses.png)

The 11 lenses include: Systems Thinking, First Principles, User-Centric Thinking, Edge Cases, Temporal Analysis, Security Implications, Ethical Considerations, Regression Analysis, Scalability, Performance, and Long-Term Viability.

---

## Phases 2 & 3: Specification & Generation

**Translating deep analysis into a flawless build.**

The insights from the 11 lenses are codified into a structured, machine-readable specification using a standardized XML template. This spec then guides an autonomous generation phase, ensuring the final skill is a perfect implementation of the exhaustive analysis.

![Phases 2 & 3](assets/images/06-phases-2-3.png)

---

## Phase 4: Multi-Agent Synthesis

**A panel of experts demands unanimous approval.**

A generated skill is not considered complete until it passes a rigorous synthesis protocol. It is submitted to a panel of specialized Opus 4.5 agents, each evaluating the skill against distinct, specialized criteria. **Approval must be unanimous.**

![Phase 4: Multi-Agent Synthesis](assets/images/07-phase4-synthesis.png)

The panel includes:
- **Code Quality Agent** - Architecture, patterns, correctness
- **Evolution Agent** - Timelessness, extensibility, future-readiness
- **Security Agent** - Vulnerability assessment, safe patterns
- **Script Agent** (conditional) - Validates code quality when scripts are present

---

## The Evolution Mandate

**Designing for a multi-year lifespan.**

Skills built with SkillForge are not ephemeral. A dedicated **Evolution & Timelessness Agent** scores every skill on its potential for longevity, extensibility, and future-readiness.

**The skill must achieve a score of ≥7/10 to pass. This is a non-negotiable quality gate.**

---

## Three Core Principles

![Core Principles](assets/images/09-core-principles.png)

| Principle | Implementation |
|-----------|----------------|
| **Engineer for Agents** | Standardized directory structure, XML-based templates, automated validation |
| **Systematize Rigor** | 4-phase architecture, regression questioning, 11 thinking lenses, multi-agent synthesis |
| **Design for Evolution** | Dedicated Evolution agent, mandatory ≥7/10 timelessness score, required extension points |

---

## Agentic Capabilities

SkillForge includes a comprehensive script integration framework, enabling skills to possess fully agentic capabilities like self-verification, error recovery, and state persistence.

![Agentic Capabilities](assets/images/10-agentic-capabilities.png)

**Key Features:**
- **Phase 1D: Automation Analysis** - Proactively identifies opportunities for Python scripts
- **Conditional 4th Agent** - Script Agent validates code quality when scripts are present
- **Self-verification** - Scripts can verify their own outputs
- **State persistence** - Track progress across sessions

### New Scripts in v4.0

| Script | Purpose |
|--------|---------|
| `triage_skill_request.py` | Intelligent input classification and skill matching |
| `discover_skills.py` | Scans all skill sources and builds searchable index |
| `match_skills.py` | Multi-factor confidence scoring |
| `verify_recommendation.py` | Self-verification of recommendation quality |

---

## Directory Structure

The methodology is reflected in a clean, predictable, and standardized directory structure. Every component has its place, from templates and references to validation scripts.

![Directory Structure](assets/images/11-directory-structure.png)

```
skillforge/
├── SKILL.md                    # Main skill definition
├── README.md                   # This file
├── LICENSE                     # MIT License
├── references/                 # The "brain" of the system
│   ├── regression-questions.md
│   ├── multi-lens-framework.md
│   ├── specification-template.md
│   ├── evolution-scoring.md
│   ├── synthesis-protocol.md
│   └── script-integration-framework.md
├── assets/
│   └── templates/              # Reusable blueprints
│       ├── skill-spec-template.xml
│       ├── skill-md-template.md
│       └── script-template.py
└── scripts/                    # Automated quality gates
    ├── triage_skill_request.py
    ├── discover_skills.py
    ├── match_skills.py
    ├── verify_recommendation.py
    ├── validate-skill.py
    └── package_skill.py
```

---

## Installation & Usage

![Installation](assets/images/12-installation.png)

```bash
# Installation
cp -r skillforge ~/.claude/skills/

# Full autonomous execution
SkillForge: {goal}

# Natural language activation
create skill for {purpose}

# Generate specification only
skillforge --plan-only
```

### Triggers

**Creation:**
- `SkillForge: {goal}` - Full autonomous skill creation
- `create skill` - Natural language activation
- `design skill for {purpose}` - Purpose-first creation

**Routing (v4.0):**
- `{any input}` - Analyzes and routes automatically
- `do I have a skill for` - Searches existing skills
- `which skill` / `what skill` - Recommends matching skills
- `improve {skill-name} skill` - Enters improvement mode

---

## Requirements

- Claude Code CLI
- Claude Opus 4.5 model access
- Python 3.8+ (for validation scripts)

---

## Conclusion

![Closing](assets/images/13-closing.png)

**SkillForge is a systematic methodology for quality.**

By codifying expert analysis, rigorous specification, and multi-agent peer review into a fully autonomous system, SkillForge provides a blueprint for building the next generation of robust, reliable, and evolution-aware AI skills.

**It transforms skill creation from an art into an engineering discipline.**

---

## License

MIT License - see [LICENSE](LICENSE)

---

## Changelog

### v4.0.0 (Current)
- Renamed from SkillCreator to SkillForge
- Added Phase 0: Universal Skill Triage
- Added universal domain-based matching (works for everyone)
- Added triage, discovery, matching, and verification scripts
- Intelligent routing: USE → IMPROVE → CREATE → COMPOSE

### v3.2.0
- Added Script Integration Framework for agentic skills
- Added 4th Script Agent to synthesis panel (conditional)
- Added Phase 1D: Automation Analysis

### v3.1.0
- Added progressive disclosure structure
- Fixed frontmatter for packaging compatibility

### v3.0.0
- Complete redesign as ultimate meta-skill
- Added regression questioning loop
- Added multi-lens analysis framework (11 models)
- Added evolution/timelessness core lens
- Added multi-agent synthesis panel
