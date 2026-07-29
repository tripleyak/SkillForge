#!/usr/bin/env python3
"""
_constants.py - Shared constants for skill validation scripts

These constants are used by:
- quick_validate.py (packaging validation)
- validate-skill.py (full structural validation)
- discover_skills.py (skill indexing)
"""

# ===========================================================================
# FRONTMATTER PROPERTIES
# ===========================================================================

# Required fields
REQUIRED_PROPERTIES = {
    'name',           # Skill identifier (hyphen-case, max 64 chars)
    'description',    # Discovery text (max 1024 chars, no angle brackets)
}

# Optional fields
OPTIONAL_PROPERTIES = {
    'license',        # Distribution license (MIT, Apache-2.0, etc.)
    'allowed-tools',  # Tool restrictions (comma-separated or YAML list)
    'metadata',       # Custom fields (version, author, domains, etc.)
    'model',          # Claude model family alias (avoid dated model IDs)
    'context',        # Execution context ('fork' for isolated sub-agent)
    'agent',          # Agent type when context: fork
    'hooks',          # Lifecycle hooks (PreToolUse, PostToolUse, Stop)
    'user-invocable', # Slash menu visibility (default: true)
    # Additional fields supported by current Claude Code
    'when_to_use',    # Extra trigger guidance shown in skill listings
    'argument-hint',  # Hint shown in the slash-command menu
    'arguments',      # Declared arguments for user invocation
    'disable-model-invocation',  # Prevent Claude from auto-invoking
    'disallowed-tools',          # Tool denylist
    'effort',         # Reasoning effort hint
    'background',     # Run as a background task
    'paths',          # Directory scoping for the skill
    'shell',          # Shell override for command execution
}

# All allowed properties
ALLOWED_PROPERTIES = REQUIRED_PROPERTIES | OPTIONAL_PROPERTIES

# Recommended but optional fields
RECOMMENDED_PROPERTIES = {'license'}

# ===========================================================================
# VALIDATION CONSTANTS
# ===========================================================================

# Valid agent types for context: fork
VALID_AGENT_TYPES = {'Explore', 'Plan', 'general-purpose'}

# Valid hook event names
VALID_HOOK_EVENTS = {'PreToolUse', 'PostToolUse', 'Stop'}

# Valid hook types
VALID_HOOK_TYPES = {'command', 'prompt'}

# Known tool names for allowed-tools validation (warning only, not error)
KNOWN_TOOLS = {
    'Read', 'Glob', 'Grep', 'Write', 'Edit',
    'Bash', 'Task', 'WebFetch', 'WebSearch',
    'TodoWrite', 'NotebookEdit', 'AskUserQuestion'
}

# Field constraints (agentskills.io portability rules; Claude Code itself is
# more permissive, but staying within these keeps skills portable)
NAME_MAX_LENGTH = 64
DESCRIPTION_MAX_LENGTH = 1024

# ===========================================================================
# LINT CONSTANTS
# ===========================================================================

# Dated model IDs (e.g. claude-opus-4-5-20251101) violate timelessness:
# pin a family alias or omit the field entirely.
PINNED_MODEL_REGEX = r'claude-.*-\d{8}'

# Trigger-condition language expected in descriptions (warn when absent)
TRIGGER_LANGUAGE_MARKERS = ("use when", "use if", "triggers", "for when")

# SKILL.md body word budget (excludes frontmatter)
BODY_WORDS_WARNING = 1500   # warn above this
BODY_WORDS_ERROR = 5000     # error above this

# ===========================================================================
# MATCH SCORE BANDS (single source of truth for triage thresholds)
# ===========================================================================
# Scores are keyword-overlap heuristics, not calibrated confidence. Present
# them as bands, keep the raw numbers only for machine consumers.

STRONG_MATCH_THRESHOLD = 80
MODERATE_MATCH_THRESHOLD = 60
WEAK_MATCH_THRESHOLD = 40


def score_band(score: float) -> str:
    """Map a numeric match score to an honest keyword-match band."""
    if score >= STRONG_MATCH_THRESHOLD:
        return "strong"
    if score >= MODERATE_MATCH_THRESHOLD:
        return "moderate"
    if score >= WEAK_MATCH_THRESHOLD:
        return "weak"
    return "poor"


# ===========================================================================
# SKILL INDEX
# ===========================================================================

# Rebuild the skill index when it is older than this (see discover_skills.py
# --max-age-hours and context_advisor.ensure_skill_index)
INDEX_MAX_AGE_HOURS = 24

# ===========================================================================
# DOMAIN VOCABULARY (shared by discovery classification and triage matching)
# ===========================================================================
# One vocabulary, two consumers: discover_skills.classify_domain tags skills
# with domains; triage_skill_request.detect_query_domains maps queries to the
# same domains. All matching is word-boundary based (common.phrase_in_text).

DOMAIN_VOCABULARY = {
    # Document types
    "spreadsheet": ["excel", "xlsx", "xls", "csv", "spreadsheet", "workbook",
                    "tabular", "data table", "cells", "rows columns"],
    "document": ["word", "docx", "doc", "document", "text document",
                 "write document", "report"],
    "presentation": ["powerpoint", "pptx", "slides", "presentation", "deck",
                     "slide deck", "keynote", "pitch"],
    "pdf": ["pdf", "export pdf", "portable document"],

    # Development domains
    "debugging": ["debug", "error", "trace", "exception", "stack trace",
                  "traceback", "crash", "fix bug", "breakpoint", "investigate",
                  "root cause"],
    "testing": ["test", "tdd", "coverage", "e2e", "unit test",
                "integration test", "cypress", "jest", "vitest", "pytest",
                "mocha", "spec"],
    "security": ["security", "owasp", "vulnerability", "audit", "secure",
                 "penetration", "pentest", "xss", "injection"],
    "code_quality": ["review", "refactor", "lint", "code smell", "solid",
                     "pr review", "code review", "pull request", "clean code"],
    "database": ["database", "db", "sql", "postgres", "mysql", "mongodb",
                 "migration", "schema", "data model", "orm"],
    "api": ["api", "rest", "graphql", "openapi", "endpoint", "swagger",
            "restful", "http"],
    "frontend": ["ui", "ux", "frontend", "react", "vue", "angular",
                 "component", "css", "styling", "user interface"],
    "accessibility": ["accessibility", "a11y", "wcag", "screen reader",
                      "aria", "keyboard navigation"],
    "performance": ["performance", "optimize", "slow", "speed", "fast",
                    "cache", "profiling", "bottleneck"],
    "authentication": ["auth", "login", "authentication", "oauth", "jwt",
                       "session", "sign in", "sign up", "password"],
    "deployment": ["deploy", "deployment", "release", "ship", "hosting",
                   "production"],
    "devops": ["ci", "cd", "docker", "kubernetes", "k8s", "container",
               "helm", "terraform", "pipeline", "infrastructure"],
    "documentation": ["documentation", "docs", "readme", "changelog",
                      "jsdoc", "api docs"],
    "architecture": ["architecture", "system design", "microservices",
                     "monolith", "design pattern"],
    "workflow": ["flowchart", "diagram", "workflow", "process", "swimlane",
                 "sequence diagram", "uml"],

    # Specialized domains
    "ai_ml": ["ai", "ml", "machine learning", "llm", "rag", "langchain",
              "prompt", "embedding", "model"],
    "visual": ["visual", "image", "graphic", "art", "canvas", "brand",
               "design"],
    "meta": ["orchestrate", "compose", "skill", "maker", "proactive",
             "chain"],
}

# Skill name regex (unified across all validators)
# - Must start with lowercase letter
# - Can contain lowercase letters, digits, and hyphens
# - Cannot have consecutive hyphens (checked separately)
# - Cannot start or end with hyphen (enforced by regex requiring letter start)
NAME_REGEX = r'^[a-z][a-z0-9-]*[a-z0-9]$|^[a-z]$'  # Single char or multi-char ending in alnum

# Semver regex (supports pre-release versions like 1.0.0-beta.1)
SEMVER_REGEX = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?(\+[a-zA-Z0-9.]+)?$'

# Frontmatter regex (handles both LF and CRLF line endings)
FRONTMATTER_REGEX = r'^---\r?\n(.*?)\r?\n---'
