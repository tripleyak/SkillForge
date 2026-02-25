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
            (skill_dir / "notes").mkdir()
            (skill_dir / "notes" / "internal.txt").write_text("internal", encoding="utf-8")

            result = package_skill(skill_dir, out_dir)
            self.assertTrue(result.success, result.message)
            self.assertIsNotNone(result.output_path)

            with zipfile.ZipFile(result.output_path) as zf:
                names = set(zf.namelist())

            self.assertIn("my-skill/public.txt", names)
            self.assertNotIn("my-skill/secret.env", names)
            self.assertNotIn("my-skill/notes/internal.txt", names)


if __name__ == "__main__":
    unittest.main()
