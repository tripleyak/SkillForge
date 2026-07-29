#!/usr/bin/env python3
"""
quick_validate.py - Fast validation for Claude Code skills

Validates that a skill meets the packaging requirements for distribution.
This is the minimal validation required before packaging with package_skill.py.

quick_validate is a strict SUBSET of validate_skill.py: it runs the same
shared frontmatter field checks (via validate_skill.frontmatter_field_checks)
and fails only on their errors. A skill rejected here is always rejected by
the full validator too; the full validator may additionally reject on
structural/lint checks that quick_validate skips.

Usage:
    python quick_validate.py <skill_directory>
    python quick_validate.py ~/.claude/skills/my-skill/

Exit Codes:
    0 - Skill is valid for packaging
    1 - Validation failed
"""

import argparse
import sys
from pathlib import Path

try:
    from frontmatter import parse_frontmatter
    from validate_skill import frontmatter_field_checks
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from frontmatter import parse_frontmatter
    from validate_skill import frontmatter_field_checks


def validate_skill(skill_path):
    """
    Basic validation of a skill for packaging compatibility.

    Checks (shared with validate_skill.py):
    - SKILL.md exists
    - Valid YAML frontmatter
    - Only allowed properties in frontmatter
    - Required fields present (name, description)
    - Name format (hyphen-case, max 64 chars - agentskills.io portability)
    - Description format (max 1024 chars, no angle brackets - agentskills.io
      portability)
    - user-invocable is a boolean
    - model is not pinned to a dated model ID

    Returns:
        tuple: (is_valid: bool, message: str)
    """
    skill_path = Path(skill_path)

    # Check SKILL.md exists
    skill_md = skill_path / 'SKILL.md'
    if not skill_md.exists():
        return False, "SKILL.md not found"

    try:
        content = skill_md.read_text(encoding='utf-8')
    except OSError as e:
        return False, f"Failed to read SKILL.md: {e}"

    frontmatter, error = parse_frontmatter(content)
    if error:
        return False, error

    # Run the shared field checks; fail on errors only (warnings are the
    # full validator's business).
    failures = [
        message
        for _name, passed, message, severity in frontmatter_field_checks(frontmatter)
        if not passed and severity == "error"
    ]
    if failures:
        return False, failures[0]

    return True, "Skill is valid!"


def main():
    parser = argparse.ArgumentParser(
        description="Fast packaging validation for a Claude Code skill",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ~/.claude/skills/my-skill/
        """
    )
    parser.add_argument(
        "skill_path",
        help="Path to the skill directory (containing SKILL.md)"
    )
    args = parser.parse_args()

    if not Path(args.skill_path).exists():
        print(f"Error: Path not found: {args.skill_path}")
        sys.exit(1)

    valid, message = validate_skill(args.skill_path)

    if valid:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")

    sys.exit(0 if valid else 1)


if __name__ == "__main__":
    main()
