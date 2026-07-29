#!/usr/bin/env python3
"""
Tests for discover_skills.py: source scanning, dedupe by priority,
strict SKILL.md name filtering, domain classification word boundaries,
and index staleness helpers.
"""

from __future__ import annotations

import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import discover_skills  # noqa: E402
from discover_skills import (  # noqa: E402
    classify_domain,
    dedupe_skills,
    discover_skills as run_discovery,
    find_skill_files,
    index_age_hours,
)


def write_skill(root: Path, rel_dir: str, name: str, description: str,
                filename: str = "SKILL.md") -> Path:
    skill_dir = root / rel_dir
    skill_dir.mkdir(parents=True, exist_ok=True)
    path = skill_dir / filename
    path.write_text(
        f"---\nname: {name}\ndescription: \"{description}\"\n---\n\n# {name}\n",
        encoding="utf-8",
    )
    return path


class FindSkillFilesTest(unittest.TestCase):
    def test_flat_source_finds_skill_md(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skillforge-test-") as tmp:
            root = Path(tmp)
            write_skill(root, "alpha", "alpha", "Use when testing alpha.")
            write_skill(root, "beta", "beta", "Use when testing beta.",
                        filename="skill.md")  # lowercase accepted
            files = find_skill_files(root, recursive=False)
            self.assertEqual(len(files), 2)

    def test_flat_source_ignores_other_markdown(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skillforge-test-") as tmp:
            root = Path(tmp)
            (root / "alpha").mkdir()
            (root / "alpha" / "README.md").write_text("nope", encoding="utf-8")
            files = find_skill_files(root, recursive=False)
            self.assertEqual(files, [])

    def test_recursive_source_finds_nested_layouts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skillforge-test-") as tmp:
            root = Path(tmp)
            # Claude Code plugin-cache layout:
            # <marketplace>/<plugin>/<version>/skills/<skill>/SKILL.md
            write_skill(root, "market/plugin/1.0.0/skills/gamma", "gamma",
                        "Use when testing gamma.")
            # Deeper variant (e.g. skills/<skill>/upstream/SKILL.md)
            write_skill(root, "market/plugin/1.0.0/skills/delta/upstream",
                        "delta", "Use when testing delta.")
            files = find_skill_files(root, recursive=True)
            self.assertEqual(len(files), 2)

    def test_recursive_source_rejects_non_skill_md_names(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skillforge-test-") as tmp:
            root = Path(tmp)
            nested = root / "market/plugin/1.0.0/skills/x"
            nested.mkdir(parents=True)
            (nested / "SKILLS.md").write_text("---\nname: x\n---\n", encoding="utf-8")
            (nested / "README.md").write_text("readme", encoding="utf-8")
            (nested / "MY-SKILL.md").write_text("---\nname: y\n---\n", encoding="utf-8")
            files = find_skill_files(root, recursive=True)
            self.assertEqual(files, [])


class DedupeTest(unittest.TestCase):
    def test_dedupe_prefers_lower_priority_number(self) -> None:
        skills = [
            {"name": "dup", "priority": 4, "path": "/cache/dup"},
            {"name": "dup", "priority": 1, "path": "/personal/dup"},
            {"name": "unique", "priority": 4, "path": "/cache/unique"},
        ]
        deduped = dedupe_skills(skills)
        self.assertEqual(len(deduped), 2)
        winner = next(s for s in deduped if s["name"] == "dup")
        self.assertEqual(winner["path"], "/personal/dup")

    def test_dedupe_is_case_insensitive_on_name(self) -> None:
        skills = [
            {"name": "Dup", "priority": 2, "path": "/a"},
            {"name": "dup", "priority": 5, "path": "/b"},
        ]
        deduped = dedupe_skills(skills)
        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0]["path"], "/a")


class DiscoveryEndToEndTest(unittest.TestCase):
    def _sources(self, root: Path):
        return [
            {"name": "personal", "path": root / "personal", "recursive": False,
             "priority": 1},
            {"name": "cache", "path": root / "cache", "recursive": True,
             "priority": 4},
            {"name": "missing", "path": root / "does-not-exist",
             "recursive": False, "priority": 5},
        ]

    def test_discovery_scans_dedupes_and_counts_missing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skillforge-test-") as tmp:
            root = Path(tmp)
            write_skill(root, "personal/shared", "shared-skill",
                        "Use when testing personal wins.")
            write_skill(root, "cache/m/p/1.0.0/skills/shared", "shared-skill",
                        "Use when testing cache copy.")
            write_skill(root, "cache/m/p/1.0.0/skills/other", "other-skill",
                        "Use when testing other.")

            with mock.patch.object(discover_skills, "SKILL_SOURCES",
                                   self._sources(root)):
                result = run_discovery()

            self.assertTrue(result.success)
            names = {s["name"]: s for s in result.data["skills"]}
            self.assertEqual(set(names), {"shared-skill", "other-skill"})
            # Personal copy beats the plugin-cache copy
            self.assertEqual(names["shared-skill"]["source"], "personal")
            self.assertEqual(result.data["duplicates_removed"], 1)
            self.assertEqual(result.data["missing_sources"], 1)

    def test_all_sources_missing_reported(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skillforge-test-") as tmp:
            root = Path(tmp)
            sources = [
                {"name": "gone-1", "path": root / "gone-1", "recursive": False,
                 "priority": 1},
                {"name": "gone-2", "path": root / "gone-2", "recursive": True,
                 "priority": 2},
            ]
            with mock.patch.object(discover_skills, "SKILL_SOURCES", sources):
                result = run_discovery()
            # missing_sources drives exit code 3 - parse warnings must not
            # inflate it (audit 3.10 #9)
            self.assertEqual(result.data["missing_sources"], 2)
            self.assertEqual(result.data["total_count"], 0)


class ClassifyDomainTest(unittest.TestCase):
    def test_ai_does_not_match_email(self) -> None:
        content = (
            "# Email helper\n\nSends email digests. Handles html templates "
            "and specialist formatting for machine-generated messages."
        )
        domains = classify_domain(["email-helper", "email", "helper"], content)
        self.assertNotIn("ai_ml", domains)

    def test_real_ai_content_classifies_ai_ml(self) -> None:
        content = (
            "# RAG pipeline\n\nBuilds a rag pipeline with llm prompts and "
            "embedding search."
        )
        domains = classify_domain(["rag-pipeline", "rag", "pipeline"], content)
        self.assertIn("ai_ml", domains)

    def test_code_review_classifies_code_quality(self) -> None:
        content = (
            "# Code review\n\nUse when running a code review or pr review on "
            "a pull request."
        )
        domains = classify_domain(["code-review", "code", "review"], content)
        self.assertIn("code_quality", domains)


class IndexAgeTest(unittest.TestCase):
    def test_missing_index_age_is_none(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skillforge-test-") as tmp:
            self.assertIsNone(index_age_hours(Path(tmp) / "nope.json"))

    def test_fresh_index_age_is_small(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skillforge-test-") as tmp:
            path = Path(tmp) / "index.json"
            path.write_text("{}", encoding="utf-8")
            age = index_age_hours(path)
            self.assertIsNotNone(age)
            self.assertLess(age, 0.1)

    def test_old_index_age_reported(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skillforge-test-") as tmp:
            path = Path(tmp) / "index.json"
            path.write_text("{}", encoding="utf-8")
            two_days_ago = time.time() - 48 * 3600
            import os
            os.utime(path, (two_days_ago, two_days_ago))
            age = index_age_hours(path)
            self.assertGreater(age, 47.0)


if __name__ == "__main__":
    unittest.main()
