#!/usr/bin/env python3
"""
Tests for install_skillforge.py: hook registration merging, launchd cleanup,
consent recording, and the non-interactive safe defaults.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import install_skillforge  # noqa: E402


class HookMergeTest(unittest.TestCase):
    def test_merge_preserves_existing_hooks(self) -> None:
        settings = {
            "model": "sonnet",
            "hooks": {
                "SessionStart": [
                    {"hooks": [{"type": "command", "command": "echo other-tool"}]}
                ],
                "PreToolUse": [
                    {"matcher": "Bash", "hooks": [{"type": "command", "command": "guard.sh"}]}
                ],
            },
        }

        merged = install_skillforge.merge_hooks_into_settings(settings)

        self.assertEqual(merged["model"], "sonnet")
        session_start = merged["hooks"]["SessionStart"]
        self.assertEqual(len(session_start), 2)
        self.assertEqual(session_start[0]["hooks"][0]["command"], "echo other-tool")
        self.assertIn("session_start.py", session_start[1]["hooks"][0]["command"])
        self.assertIn("user_prompt_submit.py", merged["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"])
        self.assertEqual(len(merged["hooks"]["PreToolUse"]), 1)

    def test_merge_is_idempotent(self) -> None:
        settings: dict = {}
        install_skillforge.merge_hooks_into_settings(settings)
        once = json.dumps(settings, sort_keys=True)
        install_skillforge.merge_hooks_into_settings(settings)

        self.assertEqual(json.dumps(settings, sort_keys=True), once)
        self.assertEqual(len(settings["hooks"]["SessionStart"]), 1)
        self.assertEqual(len(settings["hooks"]["UserPromptSubmit"]), 1)

    def test_register_hooks_backs_up_existing_settings(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skillforge-settings-") as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings_path.write_text('{"model": "sonnet"}', encoding="utf-8")

            notes = install_skillforge.register_hooks(settings_path)

            backups = list(Path(tmp).glob("settings.json.bak-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(json.loads(backups[0].read_text()), {"model": "sonnet"})
            merged = json.loads(settings_path.read_text())
            self.assertEqual(merged["model"], "sonnet")
            self.assertIn("SessionStart", merged["hooks"])
            self.assertTrue(any("Backed up" in note for note in notes))

    def test_register_hooks_refuses_invalid_settings_json(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skillforge-settings-") as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings_path.write_text("{not json", encoding="utf-8")

            with self.assertRaises(ValueError):
                install_skillforge.register_hooks(settings_path)

            self.assertEqual(settings_path.read_text(), "{not json")


class LaunchdCleanupTest(unittest.TestCase):
    def test_removes_only_skillforge_plists(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skillforge-launchd-") as tmp:
            agents = Path(tmp)
            ours = agents / "com.skillforge.context-advisor.plist"
            theirs = agents / "com.example.other.plist"
            decoy = agents / "skillforge-notes.txt"
            for path in (ours, theirs, decoy):
                path.write_text("placeholder", encoding="utf-8")

            notes = install_skillforge.remove_launchd_agents(agents)

            self.assertFalse(ours.exists())
            self.assertTrue(theirs.exists())
            self.assertTrue(decoy.exists())
            self.assertEqual(len(notes), 1)
            self.assertIn("com.skillforge.context-advisor.plist", notes[0])

    def test_missing_directory_is_a_no_op(self) -> None:
        notes = install_skillforge.remove_launchd_agents(Path("/nonexistent/launch/agents"))

        self.assertEqual(notes, [])


class NonInteractiveInstallTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="skillforge-install-")
        self.home = Path(self._tmp.name)
        self.env = {**os.environ, "HOME": str(self.home), "XDG_DATA_HOME": str(self.home / "xdg-data")}
        self.config_path = self.home / ".config" / "skillforge" / "config.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_installer(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "install_skillforge.py"), "--non-interactive", *args],
            capture_output=True,
            text=True,
            timeout=30,
            env=self.env,
            check=False,
        )

    def read_config(self) -> dict:
        return json.loads(self.config_path.read_text(encoding="utf-8"))

    def test_safe_defaults_write_config_only(self) -> None:
        proc = self.run_installer()

        self.assertEqual(proc.returncode, 0, proc.stderr)
        config = self.read_config()
        self.assertEqual(config["proactivity_level"], "balanced")
        self.assertNotIn("personal", config.get("context_sources", {}))
        self.assertFalse((self.home / ".claude" / "settings.json").exists())
        self.assertFalse((self.home / ".claude" / "CLAUDE.md").exists())
        self.assertFalse((self.home / "AGENTS.md").exists())

    def test_enable_hooks_flag_registers_hooks(self) -> None:
        settings_path = self.home / "claude-settings.json"

        proc = self.run_installer("--enable-hooks", "--claude-settings", str(settings_path))

        self.assertEqual(proc.returncode, 0, proc.stderr)
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        commands = [
            hook["command"]
            for event in ("SessionStart", "UserPromptSubmit")
            for entry in settings["hooks"][event]
            for hook in entry["hooks"]
        ]
        self.assertTrue(any("session_start.py" in command for command in commands))
        self.assertTrue(any("user_prompt_submit.py" in command for command in commands))

    def test_personal_paths_flag_records_consent_with_timestamp(self) -> None:
        proc = self.run_installer("--personal-paths", "~/kb", "--github-owners", "someuser")

        self.assertEqual(proc.returncode, 0, proc.stderr)
        personal = self.read_config()["context_sources"]["personal"]
        self.assertTrue(personal["enabled"])
        self.assertIs(personal["consented"], True)
        self.assertIn("consented_at", personal)
        self.assertEqual(personal["paths"], ["~/kb"])
        self.assertTrue(personal["github"]["enabled"])
        self.assertEqual(personal["github"]["owner_limit"], ["someuser"])

    def test_no_personal_context_flag_revokes_consent(self) -> None:
        self.run_installer("--personal-paths", "~/kb")
        proc = self.run_installer("--no-personal-context")

        self.assertEqual(proc.returncode, 0, proc.stderr)
        personal = self.read_config()["context_sources"]["personal"]
        self.assertFalse(personal["enabled"])
        self.assertFalse(personal["consented"])


if __name__ == "__main__":
    unittest.main()
