# SkillForge

SkillForge is a skill routing and creation system. Its language distinguishes between finding the right existing skill, creating or improving a skill, and advising the user when a skill should be used.

## Language

**Proactive Skill Suggestion**:
A skill recommendation surfaced without the user explicitly asking for a skill recommendation. It is based on current or recent work context and must include enough reason for the user to judge whether it is useful.
_Avoid_: Passive recommendation, background tip, reminder

**Evidence-Backed Suggestion**:
A Proactive Skill Suggestion that names the suggested skill, explains why it is relevant now, cites context evidence, states confidence, gives a next action, offers user choices, and notes whether Personal Context contributed.
_Avoid_: Ungrounded suggestion, vague recommendation

**Skill Match Score**:
SkillForge's estimate that a skill fits an explicit input, based on the skill's name, triggers, domains, keywords, description, and immediate input signals.
_Avoid_: Search rank, keyword score

**Advisor Confidence Score**:
The Context Skill Advisor's estimate that a Proactive Skill Suggestion is worth surfacing now. It combines the Skill Match Score with context evidence, repeated work signals, source-tier evidence, and prior user feedback; users see a confidence band while the Advisory Queue preserves component scores.
_Avoid_: Match score, relevance score

**Context Skill Advisor**:
The SkillForge capability that produces Proactive Skill Suggestions from available work context.
_Avoid_: Skill recommender, watcher, monitor

**Proactivity Level**:
The user-selected intensity of the Context Skill Advisor. Supported levels are `off`, `quiet`, `balanced`, and `active`; `balanced` is the default level at install. Higher levels lower the Advisor Confidence Score threshold and allow more surfaced suggestions.
_Avoid_: Notification setting, alert level, aggressiveness

**Global Proactivity Level**:
The user's default Proactivity Level across SkillForge contexts on a machine.
_Avoid_: Account setting, machine policy

**Project Proactivity Override**:
A workspace-specific Proactivity Level that replaces the Global Proactivity Level for that project.
_Avoid_: Local notification setting, repo preference

**Context Source Tier**:
A category of work context the Context Skill Advisor may use when forming Proactive Skill Suggestions. SkillForge uses three source tiers: Session Context, Project Context, and Personal Context; all three are enabled by default.
_Avoid_: Data source, connector class, search scope

**Session Context**:
The current work conversation and immediate agent workspace state.
_Avoid_: Chat history, transcript

**Project Context**:
The repository or workspace context tied to the current task.
_Avoid_: Codebase scan, repo crawl

**Personal Context**:
The user's broader local and connected knowledge context, such as knowledge bases, vaults, GitHub repos, saved memories, and work documents.
_Avoid_: Private data, background knowledge

**Targeted Content Access**:
A context access rule where SkillForge searches broadly for candidate sources, then reads only specific relevant files, excerpts, or metadata needed to justify a suggestion.
_Avoid_: Full indexing, unrestricted crawl, metadata-only mode

**Advisor Checkpoint**:
A meaningful work moment when the Context Skill Advisor evaluates whether to surface a Proactive Skill Suggestion.
_Avoid_: Per-turn scan, manual review

**Scheduled Background Advising**:
A recurring Context Skill Advisor evaluation that runs without a user explicitly asking for skill advice. In v1, it is a local scheduled advisor run rather than an always-on daemon.
_Avoid_: Manual triage, passive routing, always-on watcher

**Advisor Run**:
One execution of the Context Skill Advisor against available context.
_Avoid_: Scan, crawl, monitor cycle

**Advisory Queue**:
A persistent list of Proactive Skill Suggestions waiting to be surfaced to the user.
_Avoid_: Notification inbox, alert log, recommendation cache

**Advisor State**:
The local record of user feedback that changes future Context Skill Advisor behavior, including accepted, snoozed, dismissed, and project-suppressed suggestions.
_Avoid_: Skill index, project config, memory

**Session Start Digest**:
A short presentation of pending Proactive Skill Suggestions at the beginning of an agent session.
_Avoid_: Startup notification, daily digest

**Checkpoint Inline Suggestion**:
A single Proactive Skill Suggestion surfaced during an Advisor Checkpoint when it is relevant to the current work.
_Avoid_: Pop-up, interruption

**Agent Integration Snippet**:
A short instruction block that tells an active agent when to ask the Context Skill Advisor for checkpoint suggestions.
_Avoid_: Global rule, install mutation, hidden hook

**Confirmed Skill Use**:
SkillForge invoking or applying a suggested skill only after user confirmation or an explicit host request.
_Avoid_: Auto-invoke, silent activation

**New Skill Opportunity**:
An Evidence-Backed Suggestion that proposes creating a new skill because available skills do not adequately cover a repeated or well-evidenced work pattern.
_Avoid_: Missing skill alert, gap detection, create-skill prompt

**Explicit Skill Routing**:
A skill recommendation generated in response to a direct user request or input passed to SkillForge.
_Avoid_: Manual recommendation, reactive mode

## Example Dialogue

Developer: "Should I invoke SkillForge to find a testing skill?"

Domain Expert: "That is Explicit Skill Routing because the user asked for skill help directly."

Developer: "Should SkillForge suggest a migration-planning skill after noticing repeated database schema work?"

Domain Expert: "That is a Proactive Skill Suggestion produced by the Context Skill Advisor."

Developer: "What makes a suggestion trustworthy enough to show?"

Domain Expert: "It should be an Evidence-Backed Suggestion."

Developer: "Does proactive advising replace SkillForge's existing scoring?"

Domain Expert: "No. The Advisor Confidence Score builds on the Skill Match Score."

Developer: "If the installer asks how active suggestions should be, what is that called?"

Domain Expert: "That is the Proactivity Level."

Developer: "Can one project be quieter than the user's default?"

Domain Expert: "Yes. That project uses a Project Proactivity Override."

Developer: "Which context sources are available by default?"

Domain Expert: "Session Context, Project Context, and Personal Context are all enabled by default."

Developer: "Does enabling Personal Context mean SkillForge reads every file immediately?"

Domain Expert: "No. It uses Targeted Content Access."

Developer: "When should SkillForge evaluate whether to suggest a skill?"

Domain Expert: "It uses Advisor Checkpoints and Scheduled Background Advising."

Developer: "Where do scheduled suggestions go?"

Domain Expert: "An Advisor Run writes Proactive Skill Suggestions to the Advisory Queue."

Developer: "Where does SkillForge remember dismissed suggestions?"

Domain Expert: "It records that feedback in Advisor State."

Developer: "Can SkillForge automatically run the skill it suggests?"

Domain Expert: "No. Suggestions become Confirmed Skill Use only after confirmation or explicit host direction."

Developer: "Can SkillForge proactively suggest creating a new skill?"

Domain Expert: "Yes, when it identifies a New Skill Opportunity."

Developer: "How does an active agent know when to run Advisor Checkpoints?"

Domain Expert: "It uses an Agent Integration Snippet."
