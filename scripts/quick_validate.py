#!/usr/bin/env python3
"""
quick_validate.py - Fast validation for Claude Code skills

Validates that a skill meets the packaging requirements for distribution.
This is the minimal validation required before packaging with package_skill.py.

Usage:
    python quick_validate.py <skill_directory>
    python quick_validate.py ~/.claude/skills/my-skill/
"""

import sys
import re
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# Import shared constants
try:
    from _constants import (
        ALLOWED_PROPERTIES, REQUIRED_PROPERTIES,
        NAME_MAX_LENGTH, DESCRIPTION_MAX_LENGTH, NAME_REGEX
    )
except ImportError:
    # Fallback if _constants.py not available
    ALLOWED_PROPERTIES = {
        'name', 'description', 'license', 'allowed-tools', 'metadata',
        'model', 'context', 'agent', 'hooks', 'user-invocable'
    }
    REQUIRED_PROPERTIES = {'name', 'description'}
    NAME_MAX_LENGTH = 64
    DESCRIPTION_MAX_LENGTH = 1024
    NAME_REGEX = r'^[a-z][a-z0-9-]*[a-z0-9]$|^[a-z]$'


def _parse_frontmatter_fallback(frontmatter_text: str) -> dict:
    """Fallback YAML parser for when PyYAML is not available.

    Handles folded (>) and literal (|) scalars for multi-line descriptions.
    """
    frontmatter = {}
    lines = frontmatter_text.split('\n')
    current_key = None
    current_value_lines = []
    is_folded = False  # Track folded scalar (>)
    is_literal = False  # Track literal scalar (|)

    for line in lines:
        # Check for top-level key
        if ':' in line and not line.startswith(' ') and not line.startswith('\t'):
            # Save previous key if exists
            if current_key and (is_folded or is_literal):
                frontmatter[current_key] = ' '.join(current_value_lines).strip()

            key, value = line.split(':', 1)
            current_key = key.strip()
            value = value.strip()

            # Check for folded (>) or literal (|) scalar
            if value == '>' or value == '>-':
                is_folded = True
                is_literal = False
                current_value_lines = []
            elif value == '|' or value == '|-':
                is_literal = True
                is_folded = False
                current_value_lines = []
            else:
                is_folded = False
                is_literal = False
                frontmatter[current_key] = value
                current_value_lines = []

        elif (is_folded or is_literal) and (line.startswith('  ') or line.startswith('\t')):
            # Continuation of folded/literal scalar
            current_value_lines.append(line.strip())

        elif line.startswith('  ') and current_key == 'metadata':
            # Basic nested parsing for metadata
            if 'metadata' not in frontmatter or not isinstance(frontmatter['metadata'], dict):
                frontmatter['metadata'] = {}
            if ':' in line:
                nested_key, nested_value = line.strip().split(':', 1)
                frontmatter['metadata'][nested_key.strip()] = nested_value.strip()

    # Save final key if it was a folded/literal scalar
    if current_key and (is_folded or is_literal) and current_value_lines:
        frontmatter[current_key] = ' '.join(current_value_lines).strip()

    return frontmatter


def validate_skill(skill_path):
    """
    Basic validation of a skill for packaging compatibility.

    Checks:
    - SKILL.md exists
    - Valid YAML frontmatter
    - Only allowed properties in frontmatter
    - Required fields present (name, description)
    - Name format (hyphen-case, ≤64 chars)
    - Description format (≤1024 chars, no angle brackets)

    Returns:
        tuple: (is_valid: bool, message: str)
    """
    skill_path = Path(skill_path)

    # Check SKILL.md exists
    skill_md = skill_path / 'SKILL.md'
    if not skill_md.exists():
        return False, "SKILL.md not found"

    # Read and validate frontmatter (explicit UTF-8 encoding)
    content = skill_md.read_text(encoding='utf-8')
    if not content.startswith('---'):
        return False, "No YAML frontmatter found"

    # Extract frontmatter (handles both LF and CRLF line endings)
    match = re.match(r'^---\r?\n(.*?)\r?\n---', content, re.DOTALL)
    if not match:
        return False, "Invalid frontmatter format"

    frontmatter_text = match.group(1)

    # Parse YAML frontmatter
    if HAS_YAML:
        try:
            frontmatter = yaml.safe_load(frontmatter_text)
            if frontmatter is None:
                frontmatter = {}
            elif not isinstance(frontmatter, dict):
                return False, "Frontmatter must be a YAML dictionary"
        except yaml.YAMLError as e:
            return False, f"Invalid YAML in frontmatter: {e}"
    else:
        # Basic parsing without yaml library (handles folded scalars)
        frontmatter = _parse_frontmatter_fallback(frontmatter_text)

    # Check for unexpected properties
    unexpected_keys = set(frontmatter.keys()) - ALLOWED_PROPERTIES
    if unexpected_keys:
        return False, (
            f"Unexpected key(s) in SKILL.md frontmatter: {', '.join(sorted(unexpected_keys))}. "
            f"Allowed properties are: {', '.join(sorted(ALLOWED_PROPERTIES))}"
        )

    # Check required fields
    for field in REQUIRED_PROPERTIES:
        if field not in frontmatter:
            return False, f"Missing '{field}' in frontmatter"

    # Validate name field
    name = frontmatter.get('name', '')
    if not isinstance(name, str):
        return False, f"Name must be a string, got {type(name).__name__}"
    name = name.strip()
    if name:
        # Check naming convention (hyphen-case: starts with letter, lowercase with hyphens)
        if not re.match(NAME_REGEX, name):
            return False, f"Name '{name}' should be hyphen-case (start with letter, lowercase letters, digits, and hyphens only)"
        if '--' in name:
            return False, f"Name '{name}' cannot contain consecutive hyphens"
        # Check name length
        if len(name) > NAME_MAX_LENGTH:
            return False, f"Name is too long ({len(name)} characters). Maximum is {NAME_MAX_LENGTH} characters."

    # Validate description field
    description = frontmatter.get('description', '')
    if not isinstance(description, str):
        return False, f"Description must be a string, got {type(description).__name__}"
    description = description.strip()
    if description:
        # Check for angle brackets
        if '<' in description or '>' in description:
            return False, "Description cannot contain angle brackets (< or >)"
        # Check description length
        if len(description) > DESCRIPTION_MAX_LENGTH:
            return False, f"Description is too long ({len(description)} characters). Maximum is {DESCRIPTION_MAX_LENGTH} characters."

    return True, "Skill is valid!"


def main():
    if len(sys.argv) != 2:
        print("Usage: python quick_validate.py <skill_directory>")
        print("\nExample:")
        print("  python quick_validate.py ~/.claude/skills/my-skill/")
        sys.exit(1)

    skill_path = sys.argv[1]

    if not Path(skill_path).exists():
        print(f"Error: Path not found: {skill_path}")
        sys.exit(1)

    valid, message = validate_skill(skill_path)

    if valid:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")

    sys.exit(0 if valid else 1)


if __name__ == "__main__":
    main()
