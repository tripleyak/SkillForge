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
import os
import re
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


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

    # Read and validate frontmatter
    content = skill_md.read_text()
    if not content.startswith('---'):
        return False, "No YAML frontmatter found"

    # Extract frontmatter
    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return False, "Invalid frontmatter format"

    frontmatter_text = match.group(1)

    # Parse YAML frontmatter
    if HAS_YAML:
        try:
            frontmatter = yaml.safe_load(frontmatter_text)
            if not isinstance(frontmatter, dict):
                return False, "Frontmatter must be a YAML dictionary"
        except yaml.YAMLError as e:
            return False, f"Invalid YAML in frontmatter: {e}"
    else:
        # Basic parsing without yaml library
        frontmatter = {}
        for line in frontmatter_text.split('\n'):
            if ':' in line and not line.startswith(' '):
                key, value = line.split(':', 1)
                frontmatter[key.strip()] = value.strip()

    # Define allowed properties
    ALLOWED_PROPERTIES = {'name', 'description', 'license', 'allowed-tools', 'metadata', 'disable-model-invocation'}

    # Check for unexpected properties (excluding nested keys under metadata)
    unexpected_keys = set(frontmatter.keys()) - ALLOWED_PROPERTIES
    if unexpected_keys:
        return False, (
            f"Unexpected key(s) in SKILL.md frontmatter: {', '.join(sorted(unexpected_keys))}. "
            f"Allowed properties are: {', '.join(sorted(ALLOWED_PROPERTIES))}"
        )

    # Check required fields
    if 'name' not in frontmatter:
        return False, "Missing 'name' in frontmatter"
    if 'description' not in frontmatter:
        return False, "Missing 'description' in frontmatter"

    # Extract name for validation
    name = frontmatter.get('name', '')
    if not isinstance(name, str):
        return False, f"Name must be a string, got {type(name).__name__}"
    name = name.strip()
    if name:
        # Check naming convention (hyphen-case: lowercase with hyphens)
        if not re.match(r'^[a-z0-9-]+$', name):
            return False, f"Name '{name}' should be hyphen-case (lowercase letters, digits, and hyphens only)"
        if name.startswith('-') or name.endswith('-') or '--' in name:
            return False, f"Name '{name}' cannot start/end with hyphen or contain consecutive hyphens"
        # Check name length (max 64 characters per spec)
        if len(name) > 64:
            return False, f"Name is too long ({len(name)} characters). Maximum is 64 characters."

    # Extract and validate description
    description = frontmatter.get('description', '')
    if not isinstance(description, str):
        return False, f"Description must be a string, got {type(description).__name__}"
    description = description.strip()
    if description:
        # Check for angle brackets
        if '<' in description or '>' in description:
            return False, "Description cannot contain angle brackets (< or >)"
        # Check description length (max 1024 characters per spec)
        if len(description) > 1024:
            return False, f"Description is too long ({len(description)} characters). Maximum is 1024 characters."

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
