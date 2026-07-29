#!/usr/bin/env python3
"""
Tests for compile_skill.py - per-target frontmatter transforms, migration
notes, agentskills limit enforcement, clean YAML round-tripping, and the
never-mutate-the-source guarantee.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import compile_skill as cs  # noqa: E402
from frontmatter import parse_frontmatter, parse_yaml_mapping  # noqa: E402

FULL_FRONTMATTER = """\
name: rich-skill
description: "Use when testing the compiler with every field present."
license: MIT
allowed-tools:
  - Read
  - Bash
metadata:
  version: 1.2.0
  author: tester
model: opus
effort: high
context: fork
agent: general-purpose
background: false
when_to_use: "extra routing text"
argument-hint: "[target]"
disable-model-invocation: false
user-invocable: true
disallowed-tools:
  - WebSearch
paths:
  - ../shared
shell: bash
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "python3 scripts/check.py"
"""

BODY = "\n# Rich Skill\n\nBody stays byte-identical.\n"


def build_source(tmp: str) -> Path:
    skill_dir = Path(tmp) / "rich-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(f"---\n{FULL_FRONTMATTER}---\n{BODY}",
                                        encoding="utf-8")
    (skill_dir / "references").mkdir()
    (skill_dir / "references" / "notes.md").write_text("depth", encoding="utf-8")
    (skill_dir / "scripts").mkdir()
    (skill_dir / "scripts" / "check.py").write_text("print('x')", encoding="utf-8")
    return skill_dir


def compile_to(skill_dir: Path, target: str, out: Path):
    success, message, code = cs.compile_skill(skill_dir, target, out)
    return success, message, code, out / skill_dir.name


class SerializerTest(unittest.TestCase):
    def test_round_trip_through_parser(self) -> None:
        original, err = parse_yaml_mapping(FULL_FRONTMATTER)
        self.assertIsNone(err)
        dumped = cs.serialize_frontmatter(original)
        reparsed, err = parse_yaml_mapping(dumped)
        self.assertIsNone(err)
        self.assertEqual(reparsed, original)

    def test_scalar_types_preserved(self) -> None:
        fm = {"name": "x", "user-invocable": True, "runs": 3, "empty": None}
        reparsed, err = parse_yaml_mapping(cs.serialize_frontmatter(fm))
        self.assertIsNone(err)
        self.assertIs(reparsed["user-invocable"], True)
        self.assertEqual(reparsed["runs"], 3)
        self.assertIsNone(reparsed["empty"])

    def test_description_with_colon_and_quotes(self) -> None:
        fm = {"description": 'Use when: the user says "deploy: now"'}
        reparsed, err = parse_yaml_mapping(cs.serialize_frontmatter(fm))
        self.assertIsNone(err)
        self.assertEqual(reparsed, fm)


class ClaudeTargetTest(unittest.TestCase):
    def test_passthrough_keeps_all_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = build_source(tmp)
            success, _msg, code, dest = compile_to(source, "claude", Path(tmp) / "dist")
            self.assertTrue(success)
            self.assertEqual(code, 0)
            self.assertEqual((dest / "SKILL.md").read_text(),
                             (source / "SKILL.md").read_text())
            self.assertFalse((dest / "MIGRATION_NOTES.md").exists())

    def test_supporting_files_copied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = build_source(tmp)
            _s, _m, _c, dest = compile_to(source, "claude", Path(tmp) / "dist")
            self.assertTrue((dest / "references" / "notes.md").is_file())
            self.assertTrue((dest / "scripts" / "check.py").is_file())


class CodexTargetTest(unittest.TestCase):
    def _compiled(self, tmp: str):
        source = build_source(tmp)
        success, msg, code, dest = compile_to(source, "codex", Path(tmp) / "dist")
        self.assertTrue(success, msg)
        fm, err = parse_frontmatter((dest / "SKILL.md").read_text())
        self.assertIsNone(err)
        return source, dest, fm

    def test_portable_fields_kept(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _src, _dest, fm = self._compiled(tmp)
            self.assertEqual(fm["name"], "rich-skill")
            self.assertIn("description", fm)
            self.assertEqual(fm["license"], "MIT")
            self.assertEqual(fm["allowed-tools"], ["Read", "Bash"])
            self.assertEqual(fm["metadata"]["version"], "1.2.0")

    def test_claude_only_fields_stripped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _src, _dest, fm = self._compiled(tmp)
            for field in ("hooks", "context", "agent", "effort", "background",
                          "paths", "shell", "when_to_use", "argument-hint",
                          "disable-model-invocation", "user-invocable",
                          "disallowed-tools", "model"):
                self.assertNotIn(field, fm, field)

    def test_migration_notes_list_every_stripped_field_with_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _src, dest, _fm = self._compiled(tmp)
            notes = (dest / "MIGRATION_NOTES.md").read_text()
            for field in ("hooks", "context", "model", "when_to_use", "shell"):
                self.assertIn(f"`{field}`", notes)
            self.assertIn("why:", notes)

    def test_body_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _src, dest, _fm = self._compiled(tmp)
            self.assertTrue((dest / "SKILL.md").read_text().endswith(BODY))


class AgentskillsTargetTest(unittest.TestCase):
    def test_strict_field_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = build_source(tmp)
            success, msg, code, dest = compile_to(source, "agentskills",
                                                  Path(tmp) / "dist")
            self.assertTrue(success, msg)
            fm, err = parse_frontmatter((dest / "SKILL.md").read_text())
            self.assertIsNone(err)
            self.assertEqual(
                set(fm), {"name", "description", "license", "metadata",
                          "allowed-tools"})

    def test_overlong_description_is_compile_error_10(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "long-skill"
            skill_dir.mkdir()
            desc = "Use when " + "x" * 1100
            (skill_dir / "SKILL.md").write_text(
                f'---\nname: long-skill\ndescription: "{desc}"\n---\n# L\n')
            success, msg, code = cs.compile_skill(
                skill_dir, "agentskills", Path(tmp) / "dist")
            self.assertFalse(success)
            self.assertEqual(code, 10)
            self.assertIn("1024", msg)
            # nothing was written on a failed compile
            self.assertFalse((Path(tmp) / "dist" / "long-skill").exists())

    def test_overlong_name_is_compile_error_10(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            long_name = "a" * 70
            skill_dir = Path(tmp) / long_name
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f'---\nname: {long_name}\ndescription: "Use when testing"\n---\n# X\n')
            _s, msg, code = cs.compile_skill(skill_dir, "agentskills",
                                             Path(tmp) / "dist")
            self.assertEqual(code, 10)
            self.assertIn("64", msg)

    def test_limits_ok_within_bounds(self) -> None:
        errors = cs.enforce_agentskills_limits(
            {"name": "ok", "description": "Use when fine"})
        self.assertEqual(errors, [])


class SafetyTest(unittest.TestCase):
    def test_source_never_mutated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = build_source(tmp)
            before = (source / "SKILL.md").read_text()
            for target in cs.TARGETS:
                compile_to(source, target, Path(tmp) / f"dist-{target}")
            self.assertEqual((source / "SKILL.md").read_text(), before)
            self.assertFalse((source / "MIGRATION_NOTES.md").exists())

    def test_refuses_out_equal_to_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = build_source(tmp)
            success, _msg, code = cs.compile_skill(source, "codex", source.parent)
            self.assertFalse(success)
            self.assertEqual(code, 2)

    def test_refuses_existing_destination(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = build_source(tmp)
            out = Path(tmp) / "dist"
            (out / source.name).mkdir(parents=True)
            success, _msg, code = cs.compile_skill(source, "codex", out)
            self.assertFalse(success)
            self.assertEqual(code, 1)

    def test_missing_skill_md_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "empty"
            empty.mkdir()
            success, _msg, code = cs.compile_skill(empty, "claude", Path(tmp) / "d")
            self.assertFalse(success)
            self.assertEqual(code, 1)

    def test_cli_main_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = build_source(tmp)
            code = cs.main([str(source), "--target", "codex",
                            "--out", str(Path(tmp) / "dist")])
            self.assertEqual(code, 0)
            code = cs.main(["/nonexistent", "--target", "codex", "--out", tmp])
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
