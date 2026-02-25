#!/usr/bin/env python3
"""
validate-skill.py - Structural validation for Claude Code skills

Validates that a SKILL.md file meets the requirements defined in
SkillForge 4.0's quality standards.

Usage:
    python validate-skill.py <path-to-skill-directory>
    python validate-skill.py ~/.claude/skills/my-skill/
"""

import sys
import re
import os
from pathlib import Path
from typing import List, Tuple, Dict, Any


class SkillValidator:
    """Validates skill files against SkillForge 4.0 standards."""

    def __init__(self, skill_path: str):
        self.skill_path = Path(skill_path)
        self.skill_md_path = self._find_skill_md()
        self.content = ""
        self.frontmatter: Dict[str, Any] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.checks_passed = 0
        self.checks_total = 0

    def _find_skill_md(self) -> Path:
        """Find the main skill file (SKILL.md or skill.md)."""
        for name in ["SKILL.md", "skill.md"]:
            path = self.skill_path / name
            if path.exists():
                return path
        return self.skill_path / "SKILL.md"  # Default

    def load_skill(self) -> bool:
        """Load the skill file content."""
        if not self.skill_md_path.exists():
            self.errors.append(f"Skill file not found: {self.skill_md_path}")
            return False

        try:
            self.content = self.skill_md_path.read_text(encoding="utf-8")
            return True
        except Exception as e:
            self.errors.append(f"Failed to read skill file: {e}")
            return False

    def parse_frontmatter(self) -> bool:
        """Parse YAML frontmatter from skill file."""
        match = re.match(r'^---\n(.*?)\n---', self.content, re.DOTALL)
        if not match:
            self.errors.append("Missing YAML frontmatter")
            return False

        try:
            import yaml
            self.frontmatter = yaml.safe_load(match.group(1))
            return True
        except ImportError:
            # Parse basic fields without yaml library
            frontmatter_text = match.group(1)
            for line in frontmatter_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    self.frontmatter[key.strip()] = value.strip()
            return True
        except Exception as e:
            self.errors.append(f"Failed to parse frontmatter: {e}")
            return False

    def check(self, name: str, condition: bool, error_msg: str = None, warning: bool = False):
        """Run a check and record result."""
        self.checks_total += 1
        if condition:
            self.checks_passed += 1
            return True
        else:
            if warning:
                self.warnings.append(error_msg or f"Check failed: {name}")
            else:
                self.errors.append(error_msg or f"Check failed: {name}")
            return False

    def validate_frontmatter(self):
        """Validate frontmatter fields.

        New simplified standard: only 'name' and 'description' are required.
        Optional fields: 'license', 'allowed-tools', 'metadata',
        'disable-model-invocation'.
        Fields like 'version', 'model', 'type' belong in metadata if needed.
        """
        required_fields = ["name", "description"]

        for field in required_fields:
            self.check(
                f"frontmatter.{field}",
                field in self.frontmatter and self.frontmatter[field],
                f"Missing required frontmatter field: {field}"
            )

        # Check for disallowed top-level fields
        allowed_top_level = {
            "name", "description", "license", "allowed-tools",
            "metadata", "disable-model-invocation",
        }
        unexpected = set(self.frontmatter.keys()) - allowed_top_level
        if unexpected:
            self.check(
                "frontmatter.unexpected_keys",
                False,
                f"Unexpected top-level frontmatter keys: {', '.join(sorted(unexpected))}. "
                f"Move to 'metadata' block or remove. Allowed: {', '.join(sorted(allowed_top_level))}",
                warning=True,
            )

        # Check name format (kebab-case)
        if "name" in self.frontmatter:
            name = str(self.frontmatter["name"])
            self.check(
                "frontmatter.name.format",
                bool(re.match(r'^[a-z][a-z0-9-]*$', name)),
                f"Skill name should be kebab-case: {name}"
            )
            self.check(
                "frontmatter.name.length",
                len(name) <= 64,
                f"Skill name exceeds 64 character limit ({len(name)} chars)"
            )

        # Check description constraints
        if "description" in self.frontmatter:
            desc = str(self.frontmatter["description"])
            word_count = len(desc.split())
            self.check(
                "frontmatter.description.length",
                word_count >= 10,
                f"Description too short ({word_count} words, minimum 10)",
                warning=True
            )
            self.check(
                "frontmatter.description.max_length",
                len(desc) <= 1024,
                f"Description exceeds 1024 character limit ({len(desc)} chars)"
            )
            self.check(
                "frontmatter.description.no_angle_brackets",
                '<' not in desc and '>' not in desc,
                "Description cannot contain angle brackets (< or >)"
            )

    def validate_triggers(self):
        """Validate trigger phrases section."""
        # Find triggers section
        triggers_match = re.search(
            r'##\s*Triggers\s*\n(.*?)(?=\n##|\Z)',
            self.content,
            re.DOTALL | re.IGNORECASE
        )

        self.check(
            "section.triggers",
            triggers_match is not None,
            "Missing Triggers section"
        )

        if triggers_match:
            triggers_section = triggers_match.group(1)
            # Count trigger phrases (look for backtick-wrapped phrases)
            trigger_count = len(re.findall(r'`[^`]+`', triggers_section))

            self.check(
                "triggers.count",
                3 <= trigger_count <= 5,
                f"Should have 3-5 trigger phrases (found {trigger_count})"
            )

    def validate_process(self):
        """Validate process/phases section."""
        # Look for Process section or phases
        has_process = bool(re.search(r'##\s*Process', self.content, re.IGNORECASE))
        has_phases = bool(re.search(r'###\s*Phase\s*\d', self.content, re.IGNORECASE))

        self.check(
            "section.process",
            has_process or has_phases,
            "Missing Process section or Phase definitions"
        )

        # Count phases if present
        if has_phases:
            phase_count = len(re.findall(r'###\s*Phase\s*\d', self.content, re.IGNORECASE))
            self.check(
                "phases.count",
                1 <= phase_count <= 3,
                f"Recommend 1-3 phases, not over-engineered (found {phase_count})",
                warning=True
            )

    def validate_verification(self):
        """Validate verification/success criteria section."""
        has_verification = bool(re.search(
            r'##\s*(Verification|Success Criteria|Checklist)',
            self.content,
            re.IGNORECASE
        ))

        self.check(
            "section.verification",
            has_verification,
            "Missing Verification/Success Criteria section"
        )

        # Check for checkboxes
        checkbox_count = len(re.findall(r'\[\s*\]', self.content))
        self.check(
            "verification.checkboxes",
            checkbox_count >= 2,
            f"Verification should have concrete checkboxes (found {checkbox_count})",
            warning=True
        )

    def validate_anti_patterns(self):
        """Validate anti-patterns section."""
        has_anti_patterns = bool(re.search(
            r'##\s*Anti[-\s]?Patterns',
            self.content,
            re.IGNORECASE
        ))

        self.check(
            "section.anti_patterns",
            has_anti_patterns,
            "Missing Anti-Patterns section",
            warning=True
        )

    def validate_structure(self):
        """Validate overall document structure."""
        # Check for H1 title
        has_h1 = bool(re.match(r'---.*?---\s*\n#\s+', self.content, re.DOTALL))
        self.check(
            "structure.h1_title",
            has_h1,
            "Missing H1 title after frontmatter"
        )

        # Check for tables (should prefer tables over prose)
        table_count = len(re.findall(r'\|.*\|.*\|', self.content))
        self.check(
            "structure.tables",
            table_count >= 1,
            "Should use tables for structured information",
            warning=True
        )

        # Check for extension points
        has_extensions = bool(re.search(
            r'##\s*(Extension|Future|Evolution)',
            self.content,
            re.IGNORECASE
        ))
        self.check(
            "section.extension_points",
            has_extensions,
            "Missing Extension Points section",
            warning=True
        )

    def validate_references_directory(self):
        """Validate references directory if skill is complex."""
        refs_path = self.skill_path / "references"

        # Complex skills should have references
        line_count = len(self.content.split('\n'))
        if line_count > 200:
            self.check(
                "structure.references",
                refs_path.exists() and any(refs_path.iterdir()),
                "Complex skill (>200 lines) should have references/ directory",
                warning=True
            )

    def validate_scripts_directory(self):
        """Validate scripts directory if present."""
        scripts_path = self.skill_path / "scripts"

        if not scripts_path.exists():
            # Scripts are optional - only warn if skill has bash examples suggesting scripts
            bash_example_count = len(re.findall(r'```bash', self.content))
            python_example_count = len(re.findall(r'python\s+scripts/', self.content))

            if python_example_count > 0:
                self.check(
                    "scripts.presence",
                    False,
                    f"SKILL.md references scripts/ but no scripts directory exists",
                    warning=False
                )
            elif bash_example_count > 3:
                self.check(
                    "scripts.presence",
                    False,
                    f"Skill has {bash_example_count} bash examples - consider adding scripts/",
                    warning=True
                )
            return

        # Validate each Python script
        scripts = list(scripts_path.glob("*.py"))
        for script in scripts:
            self._validate_script(script)

        # Validate script documentation in SKILL.md
        self._validate_script_documentation(scripts)

    def _validate_script(self, script_path: Path):
        """Validate a single Python script file."""
        try:
            content = script_path.read_text(encoding="utf-8")
        except Exception as e:
            self.check(
                f"script.{script_path.name}.readable",
                False,
                f"Cannot read script {script_path.name}: {e}"
            )
            return

        script_name = script_path.name

        # Check for shebang and docstring
        has_shebang = content.strip().startswith('#!/usr/bin/env python3')
        has_docstring = '"""' in content[:500] or "'''" in content[:500]
        self.check(
            f"script.{script_name}.header",
            has_shebang and has_docstring,
            f"Script {script_name} should have shebang and docstring",
            warning=True
        )

        # Check for argparse usage (if main function exists)
        has_main = "def main():" in content or 'if __name__' in content
        has_argparse = "argparse" in content or "sys.argv" in content
        if has_main:
            self.check(
                f"script.{script_name}.argparse",
                has_argparse,
                f"Script {script_name} should use argparse for CLI",
                warning=True
            )

        # Check for explicit exit codes
        has_exit = "sys.exit" in content or "exit(" in content
        self.check(
            f"script.{script_name}.exit_codes",
            has_exit,
            f"Script {script_name} should use explicit exit codes",
            warning=True
        )

        # Check for error handling
        has_try_except = "try:" in content and "except" in content
        self.check(
            f"script.{script_name}.error_handling",
            has_try_except,
            f"Script {script_name} should have error handling",
            warning=True
        )

        # Check for result class or validation result pattern
        has_result_pattern = (
            "Result" in content or
            "ValidationResult" in content or
            "return (True" in content or
            "return (False" in content
        )
        self.check(
            f"script.{script_name}.result_pattern",
            has_result_pattern,
            f"Script {script_name} should use Result/ValidationResult pattern",
            warning=True
        )

    def _validate_script_documentation(self, scripts: List[Path]):
        """Check that scripts are documented in SKILL.md."""
        if not scripts:
            return

        # Check for Scripts section in SKILL.md
        has_scripts_section = bool(re.search(
            r'##\s*Scripts',
            self.content,
            re.IGNORECASE
        ))

        self.check(
            "scripts.documented.section",
            has_scripts_section,
            "Skills with scripts should have a Scripts section documenting usage"
        )

        # Check that each script is mentioned in SKILL.md
        for script in scripts:
            script_mentioned = script.name in self.content
            self.check(
                f"scripts.documented.{script.name}",
                script_mentioned,
                f"Script {script.name} should be documented in SKILL.md",
                warning=True
            )

        # Check for exit code documentation
        has_exit_docs = bool(re.search(
            r'Exit\s*Code|exit\s+code|Exit:\s*\d',
            self.content,
            re.IGNORECASE
        ))
        if len(scripts) > 0:
            self.check(
                "scripts.documented.exit_codes",
                has_exit_docs,
                "Skills with scripts should document exit codes",
                warning=True
            )

    def validate(self) -> Tuple[bool, str]:
        """Run all validations and return result."""
        if not self.load_skill():
            return False, self._format_report()

        if not self.parse_frontmatter():
            return False, self._format_report()

        self.validate_frontmatter()
        self.validate_triggers()
        self.validate_process()
        self.validate_verification()
        self.validate_anti_patterns()
        self.validate_structure()
        self.validate_references_directory()
        self.validate_scripts_directory()

        return len(self.errors) == 0, self._format_report()

    def _format_report(self) -> str:
        """Format validation report."""
        lines = [
            f"\n{'='*60}",
            f"Skill Validation Report: {self.skill_path.name}",
            f"{'='*60}",
            f"\nFile: {self.skill_md_path}",
            f"Checks: {self.checks_passed}/{self.checks_total} passed",
        ]

        if self.errors:
            lines.append(f"\n{'ERRORS':=^60}")
            for error in self.errors:
                lines.append(f"  ✗ {error}")

        if self.warnings:
            lines.append(f"\n{'WARNINGS':=^60}")
            for warning in self.warnings:
                lines.append(f"  ⚠ {warning}")

        if not self.errors and not self.warnings:
            lines.append("\n✓ All checks passed!")

        lines.append(f"\n{'='*60}\n")

        return '\n'.join(lines)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python validate-skill.py <path-to-skill-directory>")
        print("Example: python validate-skill.py ~/.claude/skills/my-skill/")
        sys.exit(1)

    skill_path = sys.argv[1]
    validator = SkillValidator(skill_path)
    passed, report = validator.validate()

    print(report)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
