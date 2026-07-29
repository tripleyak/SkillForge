#!/usr/bin/env python3
"""
Tests for init_skill.py - the scaffold must pass validate_skill.py with zero
errors, pass run_skill_evals.py --static (TODO placeholders are structurally
valid), and follow the skill-md-template.md doctrine: trigger-conditions
description, no model pin, no body Triggers section, no <details> blocks.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import init_skill  # noqa: E402
import run_skill_evals as rse  # noqa: E402
from frontmatter import read_skill_frontmatter  # noqa: E402
from validate_skill import SkillValidator  # noqa: E402


def scaffold(tmp: str, name: str = "sample-scaffold") -> Path:
    return init_skill.create_skill(name, Path(tmp))


class ScaffoldStructureTest(unittest.TestCase):
    def test_directories_and_files_created(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = scaffold(tmp)
            for rel in ("SKILL.md", "references/README.md", "scripts/README.md",
                        "assets/README.md", "scripts/example.py",
                        "evals/triggers.json", "evals/scenarios/01-example.md"):
                self.assertTrue((skill_dir / rel).is_file(), rel)

    def test_triggers_json_matches_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = scaffold(tmp)
            data = json.loads((skill_dir / "evals" / "triggers.json").read_text())
            for key in ("positive", "near_miss", "holdout"):
                self.assertIsInstance(data[key], list)
                self.assertTrue(all(isinstance(q, str) for q in data[key]))
            self.assertTrue(data["positive"])  # non-empty
            self.assertTrue(all("TODO" in q for q in data["positive"]))

    def test_scenario_matches_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = scaffold(tmp)
            scenario = skill_dir / "evals" / "scenarios" / "01-example.md"
            report = rse.EvalReport(str(skill_dir), "static")
            parsed = rse.load_scenario(scenario, report)
            self.assertIsNotNone(parsed)
            self.assertEqual(parsed["runs"], 1)
            self.assertEqual(len(parsed["assertions"]), 2)


class ScaffoldGatesTest(unittest.TestCase):
    def test_passes_validate_skill_with_zero_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = scaffold(tmp)
            validator = SkillValidator(str(skill_dir))
            passed, report = validator.validate()
            self.assertTrue(passed, report)
            self.assertEqual(validator.errors, [], report)

    def test_passes_run_skill_evals_static(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = scaffold(tmp)
            code = rse.main([str(skill_dir), "--static", "--json"])
            self.assertEqual(code, 0)


class ScaffoldDoctrineTest(unittest.TestCase):
    def _skill_md(self, tmp: str) -> str:
        return (scaffold(tmp) / "SKILL.md").read_text(encoding="utf-8")

    def test_description_is_trigger_conditions_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = scaffold(tmp)
            fm, err = read_skill_frontmatter(skill_dir)
            self.assertIsNone(err)
            description = str(fm["description"])
            self.assertTrue(description.lower().startswith("use when"))
            self.assertNotIn("<", description)
            self.assertNotIn(">", description)

    def test_no_model_pin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = scaffold(tmp)
            fm, _err = read_skill_frontmatter(skill_dir)
            self.assertNotIn("model", fm)

    def test_no_body_triggers_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            content = self._skill_md(tmp)
            self.assertIsNone(re.search(r"^##\s*Triggers\b", content,
                                        re.MULTILINE | re.IGNORECASE))

    def test_no_details_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertNotIn("<details", self._skill_md(tmp).lower())

    def test_name_interpolated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = scaffold(tmp, "my-neat-skill")
            fm, _err = read_skill_frontmatter(skill_dir)
            self.assertEqual(fm["name"], "my-neat-skill")
            self.assertIn("# My Neat Skill", (skill_dir / "SKILL.md").read_text())


class NameValidationTest(unittest.TestCase):
    def test_valid_names(self) -> None:
        for name in ("a", "code-reviewer", "x2-tool"):
            valid, _msg = init_skill.validate_name(name)
            self.assertTrue(valid, name)

    def test_invalid_names(self) -> None:
        for name in ("", "Upper-Case", "ends-", "two--hyphens", "9starts-digit",
                     "x" * 65):
            valid, _msg = init_skill.validate_name(name)
            self.assertFalse(valid, name)


if __name__ == "__main__":
    unittest.main()
