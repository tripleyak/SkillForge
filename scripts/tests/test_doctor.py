#!/usr/bin/env python3
"""
Tests for skillforge_doctor.py - trigger collisions, duplicate names, stale
references, description lint, token budgets, pinned model IDs, and exit
codes. All fixtures are tmp-dir skill roots fed through --sources plumbing.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import skillforge_doctor as doctor  # noqa: E402


def write_skill(root: Path, name: str, description: str = "",
                body: str = "# Skill\n\nBody.\n", extra_fm: str = "") -> Path:
    skill_dir = root / name
    skill_dir.mkdir(parents=True)
    desc_line = f'description: "{description}"\n' if description else ""
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\n{desc_line}{extra_fm}---\n{body}", encoding="utf-8")
    return skill_dir


def run_on(roots) -> dict:
    sources = doctor.sources_from_dirs([Path(r) for r in roots])
    return doctor.run_doctor(sources, doctor.DEFAULT_COLLISION_THRESHOLD,
                             manage_index=False)


def issues_of(data: dict, check: str):
    return [i for i in data["issues"] if i.check == check]


class CollisionTest(unittest.TestCase):
    def test_high_overlap_pair_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_skill(root, "pdf-tool",
                        "Use when converting extracting merging splitting pdf documents")
            write_skill(root, "pdf-helper",
                        "Use when converting extracting merging splitting pdf files")
            write_skill(root, "unrelated",
                        "Use when tuning database queries and indexes")
            data = run_on([root])
            collisions = issues_of(data, "collision")
            self.assertEqual(len(collisions), 1)
            self.assertIn("pdf-helper", collisions[0].skill)
            self.assertIn("pdf-tool", collisions[0].skill)

    def test_worst_pairs_capped_at_ten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i in range(8):
                write_skill(root, f"skill-{i}",
                            f"Use when working with widgets gadgets number {i}")
            data = run_on([root])
            self.assertLessEqual(len(data["worst_collision_pairs"]), 10)

    def test_disjoint_descriptions_not_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_skill(root, "alpha", "Use when baking sourdough bread loaves")
            write_skill(root, "beta", "Use when profiling cpu flamegraphs")
            data = run_on([root])
            self.assertEqual(issues_of(data, "collision"), [])


class DuplicateNameTest(unittest.TestCase):
    def test_exact_duplicate_across_sources(self) -> None:
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            write_skill(Path(a), "same-skill", "Use when testing duplicates one")
            write_skill(Path(b), "same-skill", "Use when testing duplicates two")
            data = run_on([a, b])
            dups = issues_of(data, "duplicate_name")
            self.assertTrue(any("exact name" in i.message for i in dups))

    def test_near_duplicate_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_skill(root, "code-review", "Use when reviewing pull requests")
            write_skill(root, "codereview", "Use when auditing merge requests")
            data = run_on([root])
            dups = issues_of(data, "duplicate_name")
            self.assertTrue(any("near-duplicate" in i.message for i in dups))

    def test_unique_names_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_skill(root, "one-skill", "Use when doing task one")
            write_skill(root, "two-skill", "Use when doing task two")
            data = run_on([root])
            self.assertEqual(issues_of(data, "duplicate_name"), [])


class StaleRefTest(unittest.TestCase):
    def test_missing_reference_is_error(self) -> None:
        body = "# S\n\nSee [guide](references/guide.md) and run scripts/run.py\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_dir = write_skill(root, "stale-skill",
                                    "Use when testing stale refs", body=body)
            # Create only one of the two referenced files
            (skill_dir / "references").mkdir()
            (skill_dir / "references" / "guide.md").write_text("x")
            data = run_on([root])
            stale = issues_of(data, "stale_ref")
            self.assertEqual(len(stale), 1)
            self.assertIn("scripts/run.py", stale[0].message)
            self.assertEqual(stale[0].severity, "error")

    def test_existing_references_clean(self) -> None:
        body = "# S\n\nSee [guide](references/guide.md).\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_dir = write_skill(root, "fresh-skill",
                                    "Use when testing fresh refs", body=body)
            (skill_dir / "references").mkdir()
            (skill_dir / "references" / "guide.md").write_text("x")
            data = run_on([root])
            self.assertEqual(issues_of(data, "stale_ref"), [])

    def test_placeholder_paths_ignored(self) -> None:
        body = "# S\n\nsee references/{{topic}}.md and references/TODO.md\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_skill(root, "tpl-skill", "Use when testing placeholders",
                        body=body)
            data = run_on([root])
            self.assertEqual(issues_of(data, "stale_ref"), [])

    def test_extract_relative_refs(self) -> None:
        body = ("Run `python3 scripts/foo.py` then read "
                "[x](references/deep/file.md). Skip references/{{tpl}}.md.")
        refs = doctor.extract_relative_refs(body)
        self.assertIn("scripts/foo.py", refs)
        self.assertIn("references/deep/file.md", refs)
        self.assertEqual(len(refs), 2)


class DescriptionLintTest(unittest.TestCase):
    def test_missing_description_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_skill(root, "no-desc")
            data = run_on([root])
            descs = issues_of(data, "description")
            self.assertTrue(any(i.severity == "error" and "missing" in i.message
                                for i in descs))

    def test_overlong_description_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_skill(root, "long-desc", "Use when " + "x" * 1100)
            data = run_on([root])
            descs = issues_of(data, "description")
            self.assertTrue(any("1024" in i.message for i in descs))

    def test_no_trigger_language_is_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_skill(root, "flat-desc", "A tool that does many things well")
            data = run_on([root])
            descs = issues_of(data, "description")
            self.assertTrue(any(i.severity == "warning" for i in descs))

    def test_good_description_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_skill(root, "good-desc", "Use when the user asks about testing")
            data = run_on([root])
            self.assertEqual(issues_of(data, "description"), [])


class TokenBudgetTest(unittest.TestCase):
    def test_heaviest_skills_ranked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_skill(root, "heavy", "Use when heavy",
                        body="# H\n\n" + ("word " * 300))
            write_skill(root, "light", "Use when light", body="# L\n\nshort")
            data = run_on([root])
            self.assertEqual(data["heaviest_skills"][0]["name"], "heavy")

    def test_over_budget_body_warned(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_skill(root, "bloated", "Use when bloated",
                        body="# B\n\n" + ("word " * 5100))
            data = run_on([root])
            budget = issues_of(data, "token_budget")
            self.assertEqual(len(budget), 1)
            self.assertEqual(budget[0].severity, "warning")


class ModelPinTest(unittest.TestCase):
    def test_dated_model_id_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_skill(root, "pinned", "Use when pinned",
                        extra_fm="model: claude-opus-4-5-20251101\n")
            data = run_on([root])
            pins = issues_of(data, "model_pin")
            self.assertEqual(len(pins), 1)
            self.assertEqual(pins[0].severity, "error")

    def test_family_alias_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_skill(root, "alias", "Use when aliased", extra_fm="model: opus\n")
            data = run_on([root])
            self.assertEqual(issues_of(data, "model_pin"), [])


class CliTest(unittest.TestCase):
    def _healthy_root(self, tmp: str) -> Path:
        root = Path(tmp)
        write_skill(root, "healthy-skill", "Use when testing healthy skills")
        return root

    def test_exit_zero_when_healthy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._healthy_root(tmp)
            self.assertEqual(doctor.main(["--sources", str(root), "--json"]), 0)

    def test_exit_zero_with_errors_without_strict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_skill(root, "no-desc")
            self.assertEqual(doctor.main(["--sources", str(root), "--json"]), 0)

    def test_strict_exits_10_on_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_skill(root, "no-desc")
            code = doctor.main(["--sources", str(root), "--json", "--strict"])
            self.assertEqual(code, 10)

    def test_strict_exits_0_with_warnings_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_skill(root, "flat-desc", "A tool that does many things")
            code = doctor.main(["--sources", str(root), "--json", "--strict"])
            self.assertEqual(code, 0)

    def test_bad_sources_dir_exits_2(self) -> None:
        self.assertEqual(doctor.main(["--sources", "/nonexistent-doctor-dir"]), 2)

    def test_json_output_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._healthy_root(tmp)
            data = run_on([root])
            payload = json.loads(doctor.to_json(data))
            self.assertEqual(payload["skill_count"], 1)
            self.assertIsInstance(payload["issues"], list)


class ReadOnlyTest(unittest.TestCase):
    def test_doctor_never_mutates_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_dir = write_skill(root, "untouched",
                                    "Use when checking read-only behavior")
            before = (skill_dir / "SKILL.md").read_text()
            mtime = (skill_dir / "SKILL.md").stat().st_mtime_ns
            run_on([root])
            self.assertEqual((skill_dir / "SKILL.md").read_text(), before)
            self.assertEqual((skill_dir / "SKILL.md").stat().st_mtime_ns, mtime)


if __name__ == "__main__":
    unittest.main()
