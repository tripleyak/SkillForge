#!/usr/bin/env python3
"""
validate_skill.py - Structural validation and lint for Claude Code skills

Validates that a SKILL.md file meets SkillForge's quality standards:
frontmatter correctness, required sections, and falsifiable lint gates
(pinned model IDs, body word budget, description shape).

Usage:
    python validate_skill.py <path-to-skill-directory>
    python validate_skill.py ~/.claude/skills/my-skill/
    python validate_skill.py <path> --json

Exit Codes:
    0 - Validation passed (no errors; warnings allowed)
    1 - Validation failed (one or more errors)
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    from _constants import (
        ALLOWED_PROPERTIES, REQUIRED_PROPERTIES, RECOMMENDED_PROPERTIES,
        VALID_AGENT_TYPES, VALID_HOOK_EVENTS, VALID_HOOK_TYPES, KNOWN_TOOLS,
        NAME_MAX_LENGTH, DESCRIPTION_MAX_LENGTH, SEMVER_REGEX, NAME_REGEX,
        PINNED_MODEL_REGEX, TRIGGER_LANGUAGE_MARKERS,
        BODY_WORDS_WARNING, BODY_WORDS_ERROR,
    )
    from frontmatter import parse_frontmatter, split_frontmatter
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _constants import (
        ALLOWED_PROPERTIES, REQUIRED_PROPERTIES, RECOMMENDED_PROPERTIES,
        VALID_AGENT_TYPES, VALID_HOOK_EVENTS, VALID_HOOK_TYPES, KNOWN_TOOLS,
        NAME_MAX_LENGTH, DESCRIPTION_MAX_LENGTH, SEMVER_REGEX, NAME_REGEX,
        PINNED_MODEL_REGEX, TRIGGER_LANGUAGE_MARKERS,
        BODY_WORDS_WARNING, BODY_WORDS_ERROR,
    )
    from frontmatter import parse_frontmatter, split_frontmatter


# ===========================================================================
# SHARED FRONTMATTER FIELD CHECKS
# ===========================================================================
# quick_validate.py imports this so the quick validator is a strict subset of
# the full validator: everything quick_validate rejects, this validator also
# rejects (never the other way around).

def frontmatter_field_checks(frontmatter: Dict[str, Any]) -> List[Tuple[str, bool, str, str]]:
    """Run the core frontmatter field checks shared by both validators.

    Returns a list of (check_name, passed, message, severity) records where
    severity is "error" or "warning".
    """
    records: List[Tuple[str, bool, str, str]] = []

    def check(name: str, passed: bool, message: str, severity: str = "error") -> None:
        records.append((name, bool(passed), message, severity))

    # Required fields
    for field in sorted(REQUIRED_PROPERTIES):
        check(
            f"frontmatter.{field}",
            field in frontmatter and bool(frontmatter[field]),
            f"Missing required frontmatter field: {field}",
        )

    # Unexpected properties
    unexpected_keys = set(frontmatter.keys()) - ALLOWED_PROPERTIES
    check(
        "frontmatter.allowed_properties",
        not unexpected_keys,
        f"Unexpected frontmatter properties: {', '.join(sorted(unexpected_keys))}. "
        f"Allowed: {', '.join(sorted(ALLOWED_PROPERTIES))}",
    )

    # Name format and length
    if "name" in frontmatter:
        name = str(frontmatter["name"]).strip()
        check(
            "frontmatter.name.format",
            bool(re.match(NAME_REGEX, name)) and "--" not in name,
            f"Skill name should be hyphen-case (start with letter, no consecutive hyphens): {name}",
        )
        check(
            "frontmatter.name.length",
            len(name) <= NAME_MAX_LENGTH,
            f"Skill name too long ({len(name)} chars, max {NAME_MAX_LENGTH} "
            "per agentskills.io portability rules)",
        )

    # Description shape and length
    if "description" in frontmatter:
        desc = str(frontmatter["description"])
        check(
            "frontmatter.description.characters",
            "<" not in desc and ">" not in desc,
            "Description cannot contain angle brackets (< or >) "
            "(agentskills.io portability rule)",
        )
        check(
            "frontmatter.description.length",
            len(desc) <= DESCRIPTION_MAX_LENGTH,
            f"Description too long ({len(desc)} chars, max {DESCRIPTION_MAX_LENGTH} "
            "per agentskills.io portability rules)",
        )

    # user-invocable must be a real boolean
    if "user-invocable" in frontmatter:
        value = frontmatter["user-invocable"]
        check(
            "frontmatter.user-invocable.type",
            isinstance(value, bool),
            f"user-invocable must be a boolean (got {type(value).__name__})",
        )

    # model must not be pinned to a dated model ID
    if "model" in frontmatter:
        model = str(frontmatter["model"])
        check(
            "frontmatter.model.pinned",
            re.search(PINNED_MODEL_REGEX, model) is None,
            f"model: pinned to a dated model ID ({model}) - pin a family alias or omit",
        )

    return records


class SkillValidator:
    """Validates skill files against SkillForge quality standards."""

    def __init__(self, skill_path: str):
        self.skill_path = Path(skill_path)
        self.skill_md_path = self._find_skill_md()
        self.content = ""
        self.body = ""
        self.frontmatter: Dict[str, Any] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.infos: List[str] = []
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

    def parse(self) -> bool:
        """Parse YAML frontmatter via the shared frontmatter module."""
        parsed, error = parse_frontmatter(self.content)
        if error:
            self.errors.append(error)
            return False
        self.frontmatter = parsed
        _fm_text, self.body = split_frontmatter(self.content)
        return True

    def check(self, name: str, condition: bool, error_msg: str = None,
              warning: bool = False, info: bool = False):
        """Run a check and record result."""
        self.checks_total += 1
        if condition:
            self.checks_passed += 1
            return True
        message = error_msg or f"Check failed: {name}"
        if info:
            self.infos.append(message)
        elif warning:
            self.warnings.append(message)
        else:
            self.errors.append(message)
        return False

    def validate_frontmatter(self):
        """Validate frontmatter fields."""
        # Core field checks shared with quick_validate.py
        for name, passed, message, severity in frontmatter_field_checks(self.frontmatter):
            self.check(name, passed, message, warning=(severity == "warning"))

        # Warn about recommended fields (not required)
        for field in RECOMMENDED_PROPERTIES:
            self.check(
                f"frontmatter.{field}",
                field in self.frontmatter,
                f"Recommended frontmatter field missing: {field}",
                warning=True
            )

        # Description should lead with trigger conditions
        if self.frontmatter.get("description"):
            desc = str(self.frontmatter["description"]).lower()
            has_trigger_language = any(marker in desc for marker in TRIGGER_LANGUAGE_MARKERS)
            self.check(
                "frontmatter.description.trigger_language",
                has_trigger_language,
                "Description has no trigger-condition language (e.g. 'Use when ...'). "
                "Descriptions should be trigger-conditions-forward so the agent knows "
                "when to fire the skill, not what the workflow is.",
                warning=True
            )

        # Check version location (should be in metadata, not root)
        if "version" in self.frontmatter:
            self.check(
                "frontmatter.version.location",
                False,
                "'version' should be under 'metadata', not at root level. "
                "Move to metadata.version for better organization.",
                warning=True
            )

        # Validate version format if in metadata
        if "metadata" in self.frontmatter and isinstance(self.frontmatter["metadata"], dict):
            version = self.frontmatter["metadata"].get("version")
            if version:
                self.check(
                    "metadata.version.format",
                    re.match(SEMVER_REGEX, str(version)),
                    f"Version should be semver format (e.g., 1.0.0 or 1.0.0-beta.1): {version}",
                    warning=True
                )

        # Validate context field - warning not error for future-proofing
        if "context" in self.frontmatter:
            context = self.frontmatter["context"]
            self.check(
                "frontmatter.context.value",
                context == "fork",
                f"context should be 'fork' (got '{context}'). Other values may be added in future.",
                warning=True
            )

        # Validate agent field
        if "agent" in self.frontmatter:
            agent = self.frontmatter["agent"]
            self.check(
                "frontmatter.agent.value",
                agent in VALID_AGENT_TYPES,
                f"agent should be one of {VALID_AGENT_TYPES} (got '{agent}')",
                warning=True
            )
            # Agent requires context: fork
            if "context" not in self.frontmatter or self.frontmatter.get("context") != "fork":
                self.check(
                    "frontmatter.agent.requires_context",
                    False,
                    "'agent' field requires 'context: fork' to be set",
                    warning=True
                )

        # Validate allowed-tools field
        self.validate_allowed_tools()

        # Validate hooks field
        self.validate_hooks()

    def validate_allowed_tools(self):
        """Validate allowed-tools field if present."""
        if "allowed-tools" not in self.frontmatter:
            return

        tools_value = self.frontmatter["allowed-tools"]

        # Parse as list or comma-separated string
        if isinstance(tools_value, str):
            tools = [t.strip() for t in tools_value.split(",")]
        elif isinstance(tools_value, list):
            tools = [str(t) for t in tools_value]
        else:
            self.check(
                "frontmatter.allowed-tools.type",
                False,
                f"allowed-tools should be string or list (got {type(tools_value).__name__})"
            )
            return

        # Check for unknown tools (warning only - custom tools may exist)
        unknown_tools = [t for t in tools if t and t not in KNOWN_TOOLS]
        if unknown_tools:
            self.check(
                "frontmatter.allowed-tools.values",
                False,
                f"Unknown tool(s): {unknown_tools}. Known tools: {sorted(KNOWN_TOOLS)}. "
                "This may be intentional for custom tools.",
                warning=True
            )

    def validate_hooks(self):
        """Validate hooks object structure if present."""
        if "hooks" not in self.frontmatter:
            return

        hooks = self.frontmatter["hooks"]

        # Hooks must be a dictionary
        if not isinstance(hooks, dict):
            self.check(
                "frontmatter.hooks.type",
                False,
                f"hooks must be an object/dictionary (got {type(hooks).__name__})"
            )
            return

        # Validate each hook event
        for hook_name, hook_config in hooks.items():
            # Check hook name is valid
            self.check(
                f"frontmatter.hooks.{hook_name}.name",
                hook_name in VALID_HOOK_EVENTS,
                f"Unknown hook event: '{hook_name}'. Valid events: {VALID_HOOK_EVENTS}"
            )

            # Hook config should be a list
            if not isinstance(hook_config, list):
                self.check(
                    f"frontmatter.hooks.{hook_name}.type",
                    False,
                    f"Hook '{hook_name}' config should be a list of matchers"
                )
                continue

            # Validate each matcher in the hook
            for i, matcher_config in enumerate(hook_config):
                if not isinstance(matcher_config, dict):
                    self.check(
                        f"frontmatter.hooks.{hook_name}[{i}].type",
                        False,
                        f"Hook matcher should be an object with 'matcher' and 'hooks' keys"
                    )
                    continue

                # PreToolUse and PostToolUse require matcher field
                if hook_name in {'PreToolUse', 'PostToolUse'}:
                    self.check(
                        f"frontmatter.hooks.{hook_name}[{i}].matcher",
                        "matcher" in matcher_config,
                        f"'{hook_name}' hook requires 'matcher' field",
                        warning=True
                    )

                # Validate inner hooks array
                inner_hooks = matcher_config.get("hooks", [])
                if not isinstance(inner_hooks, list):
                    self.check(
                        f"frontmatter.hooks.{hook_name}[{i}].hooks.type",
                        False,
                        "Inner 'hooks' should be a list"
                    )
                    continue

                for j, inner_hook in enumerate(inner_hooks):
                    if not isinstance(inner_hook, dict):
                        continue

                    # Validate hook type
                    hook_type = inner_hook.get("type")
                    if hook_type:
                        self.check(
                            f"frontmatter.hooks.{hook_name}[{i}].hooks[{j}].type",
                            hook_type in VALID_HOOK_TYPES,
                            f"Hook type should be one of {VALID_HOOK_TYPES} (got '{hook_type}')"
                        )

                    # command type requires command field
                    if hook_type == "command":
                        self.check(
                            f"frontmatter.hooks.{hook_name}[{i}].hooks[{j}].command",
                            "command" in inner_hook and inner_hook["command"],
                            "Hook with type 'command' requires non-empty 'command' field"
                        )

                    # Validate 'once' field if present
                    if "once" in inner_hook:
                        self.check(
                            f"frontmatter.hooks.{hook_name}[{i}].hooks[{j}].once",
                            isinstance(inner_hook["once"], bool),
                            "'once' field must be a boolean"
                        )

    def validate_body_budget(self):
        """Enforce the SKILL.md body word budget (context economy)."""
        word_count = len(self.body.split())

        self.check(
            "body.word_budget.error",
            word_count <= BODY_WORDS_ERROR,
            f"SKILL.md body is {word_count} words (hard limit {BODY_WORDS_ERROR}). "
            "The whole body loads on every invocation - move depth to references/.",
        )
        if word_count <= BODY_WORDS_ERROR:
            self.check(
                "body.word_budget.warning",
                word_count <= BODY_WORDS_WARNING,
                f"SKILL.md body is {word_count} words (recommended max {BODY_WORDS_WARNING}). "
                "Consider moving detail to references/.",
                warning=True
            )

        # <details> blocks are progressive-disclosure theater: collapsibility
        # saves zero tokens for an agent. (Mentions inside inline code spans,
        # e.g. `<details>`, do not count.)
        has_details_block = bool(re.search(r"(?<!`)<details\b", self.body, re.IGNORECASE))
        self.check(
            "body.details_blocks",
            not has_details_block,
            "SKILL.md contains <details> blocks. Collapsible sections save zero "
            "tokens for an agent - move that content to references/ instead.",
            warning=True
        )

    def validate_triggers(self):
        """Report on the body Triggers section (informational only).

        A body '## Triggers' section is not a triggering mechanism - the body
        is only read after the skill fires. Actual triggering comes from the
        frontmatter description, so nothing here is an error or warning.
        """
        triggers_match = re.search(
            r'##\s*Triggers\s*\n(.*?)(?=\n##|\Z)',
            self.content,
            re.DOTALL | re.IGNORECASE
        )

        self.check(
            "section.triggers",
            triggers_match is not None,
            "No body Triggers section. That is fine - triggering is driven by "
            "the frontmatter description, not the body.",
            info=True
        )

        if triggers_match:
            triggers_section = triggers_match.group(1)
            # Count trigger phrases (look for backtick-wrapped phrases)
            trigger_count = len(re.findall(r'`[^`]+`', triggers_section))

            self.check(
                "triggers.count",
                3 <= trigger_count <= 5,
                f"Body Triggers section lists {trigger_count} phrases. This section "
                "has no mechanical effect on invocation; put triggering effort into "
                "the frontmatter description instead.",
                info=True
            )

    def validate_process(self):
        """Validate process/phases section."""
        # Look for Process section or phases
        has_process = bool(re.search(r'##\s*Process', self.content, re.IGNORECASE))
        has_phases = bool(re.search(r'#+\s*Phase\s*\d|\bPhase\s+\d', self.content, re.IGNORECASE))

        self.check(
            "section.process",
            has_process or has_phases,
            "Missing Process section or Phase definitions"
        )

        # Count phases if present
        if has_phases:
            phase_count = len(re.findall(r'###\s*Phase\s*\d', self.content, re.IGNORECASE))
            if phase_count:
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
            python_example_count = len(re.findall(r'python3?\s+scripts/', self.content))

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

        # Skip CLI-related checks for non-CLI modules: private helpers
        # (starting with _) and library modules with no __main__ guard.
        is_private_module = script_name.startswith('_')
        is_library_module = 'if __name__' not in content

        # Check for shebang and docstring (applies to all Python files)
        has_shebang = content.strip().startswith('#!/usr/bin/env python3')
        has_docstring = '"""' in content[:500] or "'''" in content[:500]
        self.check(
            f"script.{script_name}.header",
            has_shebang and has_docstring,
            f"Script {script_name} should have shebang and docstring",
            warning=True
        )

        # Skip CLI-related checks for private/library modules
        if is_private_module or is_library_module:
            return

        # Check for argparse usage (if main function exists)
        has_main = "def main():" in content or 'if __name__' in content
        has_argparse = "argparse" in content
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
        # Matches: Result, ValidationResult, return (True/False, or return True/False,
        has_result_pattern = (
            "Result" in content or
            "ValidationResult" in content or
            re.search(r'return\s*\(?\s*(True|False)\s*,', content) is not None
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

        # Check for Scripts section in SKILL.md, or inline script usage docs
        has_scripts_section = bool(re.search(
            r'##\s*Scripts',
            self.content,
            re.IGNORECASE
        )) or bool(re.search(r'python3?\s+scripts/', self.content))

        self.check(
            "scripts.documented.section",
            has_scripts_section,
            "Skills with scripts should document script usage in SKILL.md "
            "(a Scripts section or inline `python scripts/...` commands)",
            warning=True
        )

        # Check that each CLI script is mentioned in SKILL.md. Private
        # helpers (_*) and library modules (no __main__ guard) are internal
        # plumbing and need no user-facing documentation. Hyphen/underscore
        # spellings count as the same script (e.g. a validate-skill.py shim
        # for validate_skill.py).
        for script in scripts:
            if script.name.startswith("_"):
                continue
            try:
                script_content = script.read_text(encoding="utf-8")
            except OSError:
                continue
            if "if __name__" not in script_content:
                continue
            spellings = {
                script.name,
                script.name.replace("-", "_"),
                script.name.replace("_", "-"),
            }
            script_mentioned = any(s in self.content for s in spellings)
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

        if not self.parse():
            return False, self._format_report()

        self.validate_frontmatter()
        self.validate_body_budget()
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

        if self.infos:
            lines.append(f"\n{'INFO':=^60}")
            for info in self.infos:
                lines.append(f"  ℹ {info}")

        if not self.errors and not self.warnings:
            lines.append("\n✓ All checks passed!")

        lines.append(f"\n{'='*60}\n")

        return '\n'.join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Machine-readable validation result."""
        return {
            "skill_path": str(self.skill_path),
            "skill_md": str(self.skill_md_path),
            "passed": len(self.errors) == 0,
            "checks_passed": self.checks_passed,
            "checks_total": self.checks_total,
            "errors": self.errors,
            "warnings": self.warnings,
            "infos": self.infos,
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate a Claude Code skill (structure, frontmatter, lint)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ~/.claude/skills/my-skill/
  %(prog)s . --json
        """
    )
    parser.add_argument(
        "skill_path",
        help="Path to the skill directory (containing SKILL.md)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    args = parser.parse_args()

    validator = SkillValidator(args.skill_path)
    passed, report = validator.validate()

    if args.json:
        print(json.dumps(validator.to_dict(), indent=2))
    else:
        print(report)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
