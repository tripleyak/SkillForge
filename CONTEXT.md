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
A category of work context the Context Skill Advisor may use when forming Proactive Skill Suggestions. SkillForge uses three source tiers: Session Context and Project Context are enabled by default; Personal Context is disabled until the user opts in with recorded consent.
_Avoid_: Data source, connector class, search scope

**Session Context**:
The current work conversation and immediate agent workspace state.
_Avoid_: Chat history, transcript

**Project Context**:
The repository or workspace context tied to the current task.
_Avoid_: Codebase scan, repo crawl

**Personal Context**:
The user's broader local and connected knowledge context, such as knowledge bases, vaults, GitHub repos, saved memories, and work documents. Strictly opt-in: it is never scanned unless the user has chosen the paths and owners and the config records that consent with a timestamp.
_Avoid_: Private data, background knowledge

**Personal Context Consent**:
The recorded opt-in (`"consented": true` plus a timestamp, written by the installer) that Personal Context scanning requires. Without it, personal paths and GitHub metadata are refused at the source-collection layer, not merely skipped by preference.
_Avoid_: Privacy setting, toggle, opt-out flag

**Targeted Content Access**:
A context access rule where SkillForge searches broadly for candidate sources, then reads only specific relevant files, excerpts, or metadata needed to justify a suggestion.
_Avoid_: Full indexing, unrestricted crawl, metadata-only mode

**Advisor Checkpoint**:
A meaningful work moment when the Context Skill Advisor evaluates whether to surface a Proactive Skill Suggestion. Delivered mechanically by Hook Delivery, not by asking agents to remember.
_Avoid_: Per-turn scan, manual review

**Hook Delivery**:
The advisor's delivery mechanism: two opt-in Claude Code hooks. The SessionStart hook surfaces the Advisory Queue as a Session Start Digest; the UserPromptSubmit hook runs a fast checkpoint against the prebuilt skill index and may emit one Checkpoint Inline Suggestion. There is no scheduled background advising by default; `context_advisor.py run` exists only for users who wire their own scheduler and requires an explicit `--cwd`.
_Avoid_: Scheduled Background Advising, daemon, watcher, launchd agent

**Suggestion Caps**:
The per-session and per-day suggestion limits defined by the Proactivity Level and enforced by the UserPromptSubmit hook through a local state file. When a cap is reached, checkpoints stay silent.
_Avoid_: Rate limit, throttle, quota

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
A short presentation of pending Proactive Skill Suggestions at the beginning of an agent session, injected by the SessionStart hook and silent when the Advisory Queue has nothing to show.
_Avoid_: Startup notification, daily digest

**Checkpoint Inline Suggestion**:
A single Proactive Skill Suggestion surfaced during an Advisor Checkpoint when it is relevant to the current work, emitted by the UserPromptSubmit hook within its time budget and Suggestion Caps.
_Avoid_: Pop-up, interruption

**Confirmed Skill Use**:
SkillForge invoking or applying a suggested skill only after the user confirms. There is no other path: hooks and queue output always instruct the agent to ask first.
_Avoid_: Auto-invoke, silent activation, host-directed invocation

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

Domain Expert: "Session Context and Project Context. Personal Context requires Personal Context Consent."

Developer: "Does enabling Personal Context mean SkillForge reads every file immediately?"

Domain Expert: "No. It uses Targeted Content Access, and only after consent is recorded."

Developer: "When should SkillForge evaluate whether to suggest a skill?"

Domain Expert: "At Advisor Checkpoints, delivered mechanically through Hook Delivery."

Developer: "Where do queued suggestions go?"

Domain Expert: "An Advisor Run writes Proactive Skill Suggestions to the Advisory Queue, and the Session Start Digest surfaces them."

Developer: "What keeps the advisor from suggesting on every prompt?"

Domain Expert: "Suggestion Caps, enforced per session and per day by the Proactivity Level."

Developer: "Where does SkillForge remember dismissed suggestions?"

Domain Expert: "It records that feedback in Advisor State."

Developer: "Can SkillForge automatically run the skill it suggests?"

Domain Expert: "No. Suggestions become Confirmed Skill Use only after the user confirms."

Developer: "Can SkillForge proactively suggest creating a new skill?"

Domain Expert: "Yes, when it identifies a New Skill Opportunity."
