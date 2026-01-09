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
    'model',          # Specific Claude model (e.g., claude-sonnet-4-20250514)
    'context',        # Execution context ('fork' for isolated sub-agent)
    'agent',          # Agent type when context: fork
    'hooks',          # Lifecycle hooks (PreToolUse, PostToolUse, Stop)
    'user-invocable', # Slash menu visibility (default: true)
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

# Field constraints
NAME_MAX_LENGTH = 64
DESCRIPTION_MAX_LENGTH = 1024

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
