#!/usr/bin/env python3
"""
Tests for validate_skill.py (full validator) and quick_validate.py, and the
agreement contract between them (quick is a strict subset of full).

CRITICAL regression (audit 3.1): a SKILL.md using every supported feature -
boolean user-invocable, allowed-tools block list, nested metadata with an
inline list - must pass the full validator with ZERO errors. The fixture in
tests/fixtures/sample-skill stands in for the repo's own SKILL.md (which is
rewritten concurrently); a second test runs against the actual repo SKILL.md
and asserts no PARSER-caused errors.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import quick_validate  # noqa: E402
from validate_skill import SkillValidator, frontmatter_field_checks  # noqa: E402

FIXTURE_SKILL = Path(__file__).resolve().parent / "fixtures" / "sample-skill"

MINIMAL_BODY = """
# Test Skill

Body prose.

| a | b | c |
|---|---|---|
| 1 | 2 | 3 |

## Process

1. Do the thing.

## Verification

- [ ] one
- [ ] two

## Anti-Patterns

- none

## Extension Points

- none yet
"""


def make_skill(tmp: str, frontmatter_text: str, body: str = MINIMAL_BODY) -> Path:
    skill_dir = Path(tmp) / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        f"---\n{frontmatter_text.strip()}\n---\n{body}", encoding="utf-8"
    )
    return skill_dir


GOOD_FRONTMATTER = """
name: test-skill
description: "Use when exercising the validator in unit tests."
license: MIT
user-invocable: true
"""


class FixtureRegressionTest(unittest.TestCase):
    """The fixture skill (every supported feature) must pass with 0 errors."""

    def test_fixture_passes_full_validator_with_zero_errors(self) -> None:
        validator = SkillValidator(str(FIXTURE_SKILL))
        passed, report = validator.validate()
        self.assertEqual(validator.errors, [], report)
        self.assertTrue(passed, report)

    def test_fixture_frontmatter_values_are_typed(self) -> None:
        validator = SkillValidator(str(FIXTURE_SKILL))
        self.assertTrue(validator.load_skill())
        self.assertTrue(validator.parse())
        self.assertIs(validator.frontmatter["user-invocable"], True)
        self.assertEqual(
            validator.frontmatter["allowed-tools"], ["Read", "Grep", "Bash"]
        )
        metadata = validator.frontmatter["metadata"]
        self.assertEqual(metadata["version"], "1.2.3")
        self.assertEqual(metadata["domains"], ["testing", "meta"])

    def test_fixture_passes_quick_validator(self) -> None:
        valid, message = quick_validate.validate_skill(FIXTURE_SKILL)
        self.assertTrue(valid, message)


class RepoSkillMdTest(unittest.TestCase):
    """The actual repo SKILL.md must produce no PARSER-caused errors.

    Content lint (sections, word budget) may legitimately flag it while the
    concurrent rewrite is in flight; parser breakage may not.
    """

    PARSER_ERROR_MARKERS = (
        "Missing YAML frontmatter",
        "Invalid YAML in frontmatter",
        "Frontmatter must be a YAML mapping",
        "Failed to parse frontmatter",
        "got str",  # e.g. "user-invocable must be a boolean (got str)"
        "Unknown tool(s): ['']",
    )

    def test_repo_skill_md_has_no_parser_caused_errors(self) -> None:
        repo_skill = SCRIPTS_DIR.parent
        if not (repo_skill / "SKILL.md").exists():
            self.skipTest("repo SKILL.md not present")
        validator = SkillValidator(str(repo_skill))
        _passed, report = validator.validate()
        for issue in validator.errors + validator.warnings:
            for marker in self.PARSER_ERROR_MARKERS:
                self.assertNotIn(marker, issue, f"parser-caused issue: {issue}\n{report}")
        # Parsed values must be typed
        if "user-invocable" in validator.frontmatter:
            self.assertIsInstance(validator.frontmatter["user-invocable"], bool)


class LintChecksTest(unittest.TestCase):
    def _validate(self, frontmatter_text: str, body: str = MINIMAL_BODY) -> SkillValidator:
        with tempfile.TemporaryDirectory(prefix="skillforge-test-") as tmp:
            skill_dir = make_skill(tmp, frontmatter_text, body)
            validator = SkillValidator(str(skill_dir))
            validator.validate()
            return validator

    def test_pinned_dated_model_is_error(self) -> None:
        validator = self._validate(
            GOOD_FRONTMATTER + "model: claude-opus-4-5-20251101\n"
        )
        self.assertTrue(
            any("pin a family alias or omit" in e for e in validator.errors),
            validator.errors,
        )

    def test_family_alias_model_is_not_error(self) -> None:
        validator = self._validate(GOOD_FRONTMATTER + "model: opus\n")
        self.assertFalse(
            any("dated model ID" in e for e in validator.errors), validator.errors
        )

    def test_description_without_trigger_language_warns(self) -> None:
        fm = """
name: test-skill
description: "Analyzes ANY input to do amazing things."
license: MIT
"""
        validator = self._validate(fm)
        self.assertTrue(
            any("trigger-condition language" in w for w in validator.warnings),
            validator.warnings,
        )

    def test_description_with_trigger_language_does_not_warn(self) -> None:
        validator = self._validate(GOOD_FRONTMATTER)
        self.assertFalse(
            any("trigger-condition language" in w for w in validator.warnings),
            validator.warnings,
        )

    def test_body_over_1500_words_warns_with_count(self) -> None:
        long_body = MINIMAL_BODY + "\n" + ("word " * 1600)
        validator = self._validate(GOOD_FRONTMATTER, body=long_body)
        matching = [w for w in validator.warnings if "recommended max 1500" in w]
        self.assertTrue(matching, validator.warnings)
        # The actual count must be reported
        self.assertRegex(matching[0], r"\d{4,} words")
        self.assertFalse(any("hard limit" in e for e in validator.errors))

    def test_body_over_5000_words_errors(self) -> None:
        long_body = MINIMAL_BODY + "\n" + ("word " * 5100)
        validator = self._validate(GOOD_FRONTMATTER, body=long_body)
        self.assertTrue(
            any("hard limit 5000" in e for e in validator.errors), validator.errors
        )

    def test_details_blocks_warn(self) -> None:
        body = MINIMAL_BODY + "\n<details>\n<summary>Deep dive</summary>\nhidden\n</details>\n"
        validator = self._validate(GOOD_FRONTMATTER, body=body)
        self.assertTrue(
            any("<details>" in w for w in validator.warnings), validator.warnings
        )

    def test_triggers_section_is_informational_not_error(self) -> None:
        # More than 5 backticked triggers used to be a hard error; now info.
        body = MINIMAL_BODY + (
            "\n## Triggers\n\n"
            "`one` `two` `three` `four` `five` `six` `seven`\n"
        )
        validator = self._validate(GOOD_FRONTMATTER, body=body)
        self.assertEqual(validator.errors, [], validator.errors)
        self.assertFalse(any("Triggers" in w for w in validator.warnings))
        self.assertTrue(any("Triggers" in i for i in validator.infos))

    def test_missing_triggers_section_is_not_error(self) -> None:
        validator = self._validate(GOOD_FRONTMATTER)
        self.assertFalse(any("Triggers" in e for e in validator.errors))

    def test_portability_rules_labeled(self) -> None:
        fm = f"""
name: test-skill
description: "Use when testing. {'x' * 1100}"
license: MIT
"""
        validator = self._validate(fm)
        self.assertTrue(
            any("agentskills.io portability" in e for e in validator.errors),
            validator.errors,
        )

    def test_non_boolean_user_invocable_is_error(self) -> None:
        fm = GOOD_FRONTMATTER.replace("user-invocable: true", 'user-invocable: "yes"')
        validator = self._validate(fm)
        self.assertTrue(
            any("user-invocable must be a boolean" in e for e in validator.errors),
            validator.errors,
        )


class QuickFullAgreementTest(unittest.TestCase):
    """quick_validate must be a strict subset of validate_skill: any skill
    quick_validate rejects, the full validator rejects too."""

    CASES = {
        "good": GOOD_FRONTMATTER,
        "missing_description": "name: test-skill\nlicense: MIT\n",
        "bad_name": 'name: Bad_Name\ndescription: "Use when testing."\n',
        "angle_brackets": 'name: test-skill\ndescription: "Use when <thing> happens."\n',
        "unexpected_prop": GOOD_FRONTMATTER + "bogus-field: 1\n",
        "pinned_model": GOOD_FRONTMATTER + "model: claude-sonnet-4-20250514\n",
        "stringly_bool": GOOD_FRONTMATTER.replace(
            "user-invocable: true", 'user-invocable: "true"'
        ),
        "long_description": f'name: test-skill\ndescription: "Use when. {"y" * 1200}"\n',
    }

    def test_quick_rejections_are_full_rejections(self) -> None:
        for label, fm in self.CASES.items():
            with self.subTest(case=label):
                with tempfile.TemporaryDirectory(prefix="skillforge-test-") as tmp:
                    skill_dir = make_skill(tmp, fm)
                    quick_ok, quick_msg = quick_validate.validate_skill(skill_dir)
                    validator = SkillValidator(str(skill_dir))
                    full_ok, report = validator.validate()
                    if not quick_ok:
                        self.assertFalse(
                            full_ok,
                            f"contradictory verdicts for {label}: quick rejected "
                            f"({quick_msg}) but full passed\n{report}",
                        )

    def test_shared_checks_drive_both_validators(self) -> None:
        # The same record list must decide both validators' error sets.
        records = frontmatter_field_checks({"name": "ok-skill"})
        failed_errors = [m for _n, ok, m, sev in records if not ok and sev == "error"]
        self.assertTrue(any("description" in m for m in failed_errors))


if __name__ == "__main__":
    unittest.main()
