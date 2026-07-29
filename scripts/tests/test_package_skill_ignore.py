#!/usr/bin/env python3
"""
Regression test: package_skill must honor .skillignore patterns.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from package_skill import package_skill  # noqa: E402


class PackageSkillIgnoreTest(unittest.TestCase):
    def test_skillignore_excludes_files_and_directories(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skillforge-test-") as tmp:
            root = Path(tmp)
            skill_dir = root / "my-skill"
            out_dir = root / "dist"
            skill_dir.mkdir()
            out_dir.mkdir()

            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "name: my-skill\n"
                "description: test packaging behavior for skillignore exclusions\n"
                "---\n",
                encoding="utf-8",
            )
            (skill_dir / ".skillignore").write_text("*.env\nnotes\n", encoding="utf-8")

            (skill_dir / "public.txt").write_text("ok", encoding="utf-8")
            (skill_dir / "secret.env").write_text("PRIVATE=1", encoding="utf-8")
            (skill_dir / ".hidden").mkdir()
            (skill_dir / ".hidden" / "project.json").write_text("{}", encoding="utf-8")
            (skill_dir / "notes").mkdir()
            (skill_dir / "notes" / "internal.txt").write_text("internal", encoding="utf-8")

            result = package_skill(skill_dir, out_dir)
            self.assertTrue(result.success, result.message)
            self.assertIsNotNone(result.output_path)

            with zipfile.ZipFile(result.output_path) as zf:
                names = set(zf.namelist())

            self.assertIn("my-skill/public.txt", names)
            self.assertNotIn("my-skill/secret.env", names)
            self.assertNotIn("my-skill/.hidden/project.json", names)
            self.assertNotIn("my-skill/notes/internal.txt", names)

    def test_trailing_slash_pattern_matches_directories_only(self) -> None:
        """rsync semantics: 'dir/' matches directories (at any depth), never
        plain files with the same name."""
        with tempfile.TemporaryDirectory(prefix="skillforge-test-") as tmp:
            root = Path(tmp)
            skill_dir = root / "my-skill"
            out_dir = root / "dist"
            skill_dir.mkdir()
            out_dir.mkdir()

            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "name: my-skill\n"
                "description: test packaging behavior for trailing-slash patterns\n"
                "---\n",
                encoding="utf-8",
            )
            (skill_dir / ".skillignore").write_text(
                "build/\nassets/tmp/\n", encoding="utf-8"
            )

            # 'build/' should exclude the directory contents...
            (skill_dir / "build").mkdir()
            (skill_dir / "build" / "artifact.bin").write_text("x", encoding="utf-8")
            # ...including nested 'build' directories (any depth)...
            (skill_dir / "sub" / "build").mkdir(parents=True)
            (skill_dir / "sub" / "build" / "deep.txt").write_text("x", encoding="utf-8")
            # ...but NOT a plain file named 'build'
            (skill_dir / "docs").mkdir()
            (skill_dir / "docs" / "build").write_text("keep me", encoding="utf-8")

            # Anchored path pattern 'assets/tmp/'
            (skill_dir / "assets" / "tmp").mkdir(parents=True)
            (skill_dir / "assets" / "tmp" / "scratch.txt").write_text("x", encoding="utf-8")
            (skill_dir / "assets" / "images").mkdir()
            (skill_dir / "assets" / "images" / "logo.png").write_text("x", encoding="utf-8")

            result = package_skill(skill_dir, out_dir)
            self.assertTrue(result.success, result.message)

            with zipfile.ZipFile(result.output_path) as zf:
                names = set(zf.namelist())

            self.assertNotIn("my-skill/build/artifact.bin", names)
            self.assertNotIn("my-skill/sub/build/deep.txt", names)
            self.assertIn("my-skill/docs/build", names)
            self.assertNotIn("my-skill/assets/tmp/scratch.txt", names)
            self.assertIn("my-skill/assets/images/logo.png", names)


if __name__ == "__main__":
    unittest.main()
