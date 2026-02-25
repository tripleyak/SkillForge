#!/usr/bin/env python3
"""
init_skill.py - Scaffold a new agent skill (Claude Code/Codex)

Creates a complete skill directory with SKILL.md template, references/,
scripts/, and assets/ subdirectories pre-populated with starter files.

Usage:
    python init_skill.py <skill-name> [--path <parent-directory>]

Examples:
    python init_skill.py code-reviewer
    python init_skill.py deploy-helper --path ~/my-skills
    python init_skill.py test-generator --path ~/.codex/skills

Exit Codes:
    0  - Success
    1  - General failure
    2  - Invalid arguments
"""

import argparse
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

SKILL_MD_TEMPLATE = """\
---
name: {name}
description: >
  TODO: Describe what this skill does in 1-2 sentences.
---

# {title}

TODO: One-line summary of this skill's purpose.

## Triggers

- `{name}: {{goal}}` - TODO: Primary trigger description
- `TODO: trigger phrase 2` - TODO: Description
- `TODO: trigger phrase 3` - TODO: Description

## Quick Reference

| Input | Output | Duration |
|-------|--------|----------|
| TODO  | TODO   | TODO     |

## Process

### Phase 1: TODO Phase Name

TODO: Describe what happens in this phase.

1. **TODO Step 1** - Description
2. **TODO Step 2** - Description

**Verification:** TODO: How to verify this phase succeeded.

### Phase 2: TODO Phase Name

TODO: Describe what happens in this phase.

1. **TODO Step 1** - Description
2. **TODO Step 2** - Description

**Verification:** TODO: How to verify this phase succeeded.

## Anti-Patterns

| Avoid | Why | Instead |
|-------|-----|---------|
| TODO  | TODO | TODO   |

## Verification

After execution:

- [ ] TODO: Check 1
- [ ] TODO: Check 2
- [ ] TODO: Check 3

## References

- [TODO](references/TODO) - TODO: Description
"""

README_REFERENCES = """\
# References

Supporting documents for the {name} skill.

Place domain knowledge, standards, examples, and long-form context here.
These files are loaded by the agent when deeper context is needed.

## Guidelines

- One topic per file, keep files focused
- Use markdown for prose, JSON/YAML for structured data
- Name files descriptively: `api-conventions.md`, `error-catalog.json`
- Keep individual files under 500 lines
"""

README_SCRIPTS = """\
# Scripts

Automation scripts for the {name} skill.

Scripts extend what the skill can do beyond prompt instructions.
They run via `python scripts/<name>.py` from the skill root.

## Guidelines

- Each script should have a docstring, argparse CLI, and explicit exit codes
- Use the Result dataclass pattern (see script-template.py in SkillForge assets)
- Exit 0 = success, 1 = failure, 2 = bad args, 10 = validation fail
"""

README_ASSETS = """\
# Assets

Static assets for the {name} skill.

Place templates, configuration files, images, and other non-code
resources here.

## Guidelines

- Templates go in `assets/templates/`
- Images go in `assets/images/`
- Keep assets that the skill references, not general documentation
"""

EXAMPLE_REFERENCE = """\
# Domain Knowledge

TODO: Add domain-specific knowledge that the skill needs.

## Key Concepts

- **TODO Concept 1** - Definition
- **TODO Concept 2** - Definition

## Common Patterns

TODO: Document patterns the skill should follow.

## Edge Cases

TODO: Document edge cases and how to handle them.
"""

EXAMPLE_SCRIPT = """\
#!/usr/bin/env python3
\"\"\"
example.py - Example automation script for {name}

Usage:
    python example.py <input> [--verbose]

Exit Codes:
    0  - Success
    1  - General failure
    2  - Invalid arguments
\"\"\"

import argparse
import sys
from pathlib import Path


def process(input_path: Path, verbose: bool = False) -> bool:
    \"\"\"TODO: Implement processing logic.\"\"\"
    if not input_path.exists():
        print(f"Error: File not found: {{input_path}}", file=sys.stderr)
        return False

    if verbose:
        print(f"Processing: {{input_path}}")

    # TODO: Add processing logic
    return True


def main():
    parser = argparse.ArgumentParser(description="Example script for {name}")
    parser.add_argument("input", type=Path, help="Input file path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    success = process(args.input, args.verbose)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
"""


# ---------------------------------------------------------------------------
# Organizational pattern suggestions
# ---------------------------------------------------------------------------

PATTERNS_GUIDE = """
## Skill Organization Patterns

Choose the pattern that best fits your skill's purpose:

### 1. Workflow-Based (multi-step processes)
Best for: build pipelines, deployment flows, review processes
Structure: Phases with sequential steps, verification gates between phases
Example: Phase 1: Analyze -> Phase 2: Generate -> Phase 3: Verify

### 2. Task-Based (single focused action)
Best for: formatters, linters, converters, single-purpose tools
Structure: One main action with input/output, minimal phases
Example: Input -> Transform -> Output with verification

### 3. Reference/Guidelines (standards and conventions)
Best for: style guides, API conventions, architectural decisions
Structure: Rules organized by category, examples for each rule
Example: Naming -> Structure -> Patterns -> Anti-patterns

### 4. Capabilities-Based (toolbox of related actions)
Best for: database tools, file utilities, API helpers
Structure: Multiple independent commands under one skill
Example: create | read | update | delete with shared context
"""


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def validate_name(name: str) -> tuple[bool, str]:
    """Validate skill name is kebab-case and within limits."""
    if not name:
        return False, "Skill name cannot be empty"
    if not re.match(r'^[a-z][a-z0-9-]*$', name):
        return False, f"Name '{name}' must be kebab-case (lowercase letters, digits, hyphens)"
    if name.endswith('-') or '--' in name:
        return False, f"Name '{name}' cannot end with hyphen or have consecutive hyphens"
    if len(name) > 64:
        return False, f"Name '{name}' exceeds 64 character limit ({len(name)} chars)"
    return True, ""


def to_title(name: str) -> str:
    """Convert kebab-case to Title Case."""
    return ' '.join(word.capitalize() for word in name.split('-'))


def create_skill(name: str, parent_dir: Path) -> Path:
    """Create the full skill scaffold directory."""
    title = to_title(name)
    skill_dir = parent_dir / name

    if skill_dir.exists():
        print(f"Error: Directory already exists: {skill_dir}", file=sys.stderr)
        sys.exit(1)

    # Create directory structure
    dirs = [
        skill_dir,
        skill_dir / "references",
        skill_dir / "scripts",
        skill_dir / "assets",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # Write SKILL.md
    (skill_dir / "SKILL.md").write_text(
        SKILL_MD_TEMPLATE.format(name=name, title=title)
    )

    # Write README files for subdirectories
    (skill_dir / "references" / "README.md").write_text(
        README_REFERENCES.format(name=name)
    )
    (skill_dir / "scripts" / "README.md").write_text(
        README_SCRIPTS.format(name=name)
    )
    (skill_dir / "assets" / "README.md").write_text(
        README_ASSETS.format(name=name)
    )

    # Write example files
    (skill_dir / "references" / "domain-knowledge.md").write_text(
        EXAMPLE_REFERENCE
    )
    (skill_dir / "scripts" / "example.py").write_text(
        EXAMPLE_SCRIPT.format(name=name)
    )

    return skill_dir


def print_next_steps(skill_dir: Path, name: str):
    """Print guidance for the user after scaffolding."""
    print(f"""
Skill scaffolded: {skill_dir}

Directory structure:
  {name}/
    SKILL.md              <- Main skill definition (edit this first)
    references/
      README.md
      domain-knowledge.md <- Example reference file
    scripts/
      README.md
      example.py          <- Example automation script
    assets/
      README.md

Next steps:
  1. Edit SKILL.md - replace all TODO placeholders
     - Fill in the description in frontmatter
     - Define trigger phrases (3-5 recommended)
     - Write process phases with concrete steps
     - Add anti-patterns and verification checks
  2. Add domain knowledge to references/
  3. Add automation scripts to scripts/ (optional)
  4. Validate: python validate-skill.py {skill_dir}
  5. Install:
     - Codex: copy to $CODEX_HOME/skills/{name}/ (or ~/.codex/skills/{name}/)
     - Claude Code: copy to ~/.claude/skills/{name}/

Tips:
  - Keep SKILL.md under 500 lines (hard limit: 1000)
  - Use tables over prose for structured info
  - Frontmatter only needs 'name' and 'description'
  - Reference files keep SKILL.md lean
{PATTERNS_GUIDE}""")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Scaffold a new skill for Codex or Claude Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s code-reviewer
  %(prog)s deploy-helper --path ~/my-skills
  %(prog)s test-generator --path ~/.codex/skills
        """
    )

    parser.add_argument(
        "name",
        help="Skill name in kebab-case (e.g. code-reviewer, test-generator)"
    )

    parser.add_argument(
        "--path",
        type=Path,
        default=Path.cwd(),
        help="Parent directory for the new skill (default: current directory)"
    )

    args = parser.parse_args()

    # Validate name
    valid, error = validate_name(args.name)
    if not valid:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(2)

    # Validate parent path
    parent = args.path.expanduser().resolve()
    if not parent.exists():
        print(f"Error: Parent directory not found: {parent}", file=sys.stderr)
        sys.exit(2)

    # Create scaffold
    skill_dir = create_skill(args.name, parent)
    print_next_steps(skill_dir, args.name)

    sys.exit(0)


if __name__ == "__main__":
    main()
