#!/usr/bin/env python3
"""
Subprocess tests for the Claude Code hook entry points.

Each test runs the hook exactly as Claude Code would: a fresh python3
process with the hook payload piped as JSON on stdin, under a temporary
HOME (and XDG_DATA_HOME) so no real user state is read or written.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
HOOKS_DIR = SCRIPTS_DIR / "hooks"
SESSION_START = HOOKS_DIR / "session_start.py"
USER_PROMPT_SUBMIT = HOOKS_DIR / "user_prompt_submit.py"

CODEREVIEW_SKILL = {
    "name": "codereview",
    "source": "test",
    "path": "/tmp/codereview/SKILL.md",
    "description": "Review code and pull requests for bugs and regressions",
    "triggers": ["code review"],
    "keywords": ["code", "review", "pull", "request"],
    "domains": ["code_quality"],
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class HookHarness(unittest.TestCase):
    """Shared tmp-HOME setup for hook subprocess tests."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="skillforge-hooks-")
        self.home = Path(self._tmp.name) / "home"
        self.project = Path(self._tmp.name) / "project"
        self.home.mkdir(parents=True)
        self.project.mkdir(parents=True)
        self.data_dir = self.home / "xdg-data" / "skillforge"
        self.env = {
            **os.environ,
            "HOME": str(self.home),
            "XDG_DATA_HOME": str(self.home / "xdg-data"),
        }

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_hook(self, hook: Path, payload: dict) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(hook)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=30,
            env=self.env,
            cwd=str(self.project),
            check=False,
        )

    def write_config(self, config: dict) -> None:
        path = self.home / ".config" / "skillforge" / "config.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(config), encoding="utf-8")

    def write_queue(self, items: list[dict]) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps(item) for item in items]
        (self.data_dir / "advice.jsonl").write_text(
            "\n".join(lines) + ("\n" if lines else ""), encoding="utf-8"
        )

    def write_advisor_state(self, state: dict) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "advisor_state.json").write_text(json.dumps(state), encoding="utf-8")

    def write_hook_state(self, state: dict) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "hook_state.json").write_text(json.dumps(state), encoding="utf-8")

    def write_index(self, skills: list[dict]) -> None:
        path = self.home / ".cache" / "skillrecommender" / "skill_index.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"version": "2.0.0", "skills": skills, "domains": {}, "sources": {}, "total_count": len(skills)}),
            encoding="utf-8",
        )

    def queue_item(self, **overrides) -> dict:
        item = {
            "id": "abc123def456",
            "fingerprint": "fingerprint-1",
            "action": "use_existing",
            "skill_name": "codereview",
            "skill_source": "test",
            "skill_path": "/tmp/codereview/SKILL.md",
            "confidence": "high",
            "final_score": 91,
            "scores": {},
            "why_now": "codereview matches the current work",
            "evidence": [{"tier": "session", "path": "session"}],
            "choices": ["use", "snooze", "dismiss", "never for this project"],
            "personal_context_used": False,
            "project_key": str(self.project.resolve()),
            "created_at": utc_now().isoformat(),
            "status": "pending",
        }
        item.update(overrides)
        return item


class SessionStartHookTest(HookHarness):
    def payload(self) -> dict:
        return {"session_id": "sess-1", "cwd": str(self.project), "source": "startup"}

    def test_populated_queue_prints_compact_context_block(self) -> None:
        self.write_queue([self.queue_item()])

        proc = self.run_hook(SESSION_START, self.payload())

        self.assertEqual(proc.returncode, 0)
        self.assertIn("SkillForge Context Skill Advisor", proc.stdout)
        self.assertIn("codereview", proc.stdout)
        self.assertIn("abc123def456", proc.stdout)
        self.assertIn("Why now:", proc.stdout)
        self.assertIn("Evidence:", proc.stdout)
        self.assertIn("use|snooze|dismiss", proc.stdout)
        self.assertIn("context_advisor.py", proc.stdout)

    def test_empty_queue_is_completely_silent(self) -> None:
        proc = self.run_hook(SESSION_START, self.payload())

        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")
        self.assertEqual(proc.stderr, "")

    def test_expired_suggestion_is_not_surfaced(self) -> None:
        old = (utc_now() - timedelta(days=30)).isoformat()
        self.write_queue([self.queue_item(created_at=old)])

        proc = self.run_hook(SESSION_START, self.payload())

        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")

    def test_snoozed_suggestion_is_not_surfaced_until_snooze_expires(self) -> None:
        until = (utc_now() + timedelta(hours=6)).isoformat()
        self.write_queue([self.queue_item(status="snoozed")])
        self.write_advisor_state({"snoozed": {"fingerprint-1": until}})

        proc = self.run_hook(SESSION_START, self.payload())

        self.assertEqual(proc.stdout, "")

    def test_snooze_expiry_resurfaces_suggestion(self) -> None:
        until = (utc_now() - timedelta(hours=1)).isoformat()
        self.write_queue([self.queue_item(status="snoozed")])
        self.write_advisor_state({"snoozed": {"fingerprint-1": until}})

        proc = self.run_hook(SESSION_START, self.payload())

        self.assertIn("codereview", proc.stdout)

    def test_proactivity_off_is_silent_even_with_pending_queue(self) -> None:
        self.write_config({"proactivity_level": "off"})
        self.write_queue([self.queue_item()])

        proc = self.run_hook(SESSION_START, self.payload())

        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")

    def test_quiet_level_caps_surfaced_suggestions_to_one(self) -> None:
        self.write_config({"proactivity_level": "quiet"})
        self.write_queue(
            [
                self.queue_item(),
                self.queue_item(id="second-id", fingerprint="fingerprint-2", skill_name="otherskill"),
            ]
        )

        proc = self.run_hook(SESSION_START, self.payload())

        self.assertIn("1 pending suggestion(s)", proc.stdout)
        self.assertIn("codereview", proc.stdout)
        self.assertNotIn("otherskill", proc.stdout)

    def test_other_project_suggestions_are_not_surfaced(self) -> None:
        self.write_queue([self.queue_item(project_key="/somewhere/else")])

        proc = self.run_hook(SESSION_START, self.payload())

        self.assertEqual(proc.stdout, "")

    def test_garbage_stdin_is_silent_and_exits_zero(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SESSION_START)],
            input="this is not json",
            capture_output=True,
            text=True,
            timeout=30,
            env=self.env,
            cwd=str(self.project),
            check=False,
        )

        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")


class UserPromptSubmitHookTest(HookHarness):
    PROMPT = "Please do a code review for this pull request."

    def payload(self, prompt: str | None = None, session_id: str = "sess-1") -> dict:
        return {
            "session_id": session_id,
            "cwd": str(self.project),
            "prompt": self.PROMPT if prompt is None else prompt,
        }

    def test_matching_prompt_emits_one_suggestion_line(self) -> None:
        self.write_index([CODEREVIEW_SKILL])

        proc = self.run_hook(USER_PROMPT_SUBMIT, self.payload())

        self.assertEqual(proc.returncode, 0)
        lines = [line for line in proc.stdout.splitlines() if line.strip()]
        self.assertEqual(len(lines), 1)
        self.assertIn("SkillForge advisor", lines[0])
        self.assertIn("codereview", lines[0])
        self.assertIn("Ask the user before invoking", lines[0])
        self.assertIn("use|snooze|dismiss", lines[0])

    def test_emitted_suggestion_lands_in_advisory_queue(self) -> None:
        self.write_index([CODEREVIEW_SKILL])

        self.run_hook(USER_PROMPT_SUBMIT, self.payload())

        queue = (self.data_dir / "advice.jsonl").read_text(encoding="utf-8")
        item = json.loads(queue.splitlines()[0])
        self.assertEqual(item["skill_name"], "codereview")
        self.assertEqual(item["status"], "pending")

    def test_session_cap_is_enforced(self) -> None:
        self.write_index([CODEREVIEW_SKILL])

        outputs = [
            self.run_hook(USER_PROMPT_SUBMIT, self.payload()).stdout.strip()
            for _ in range(3)
        ]

        # balanced allows max_session=2 for one session id.
        self.assertTrue(outputs[0])
        self.assertTrue(outputs[1])
        self.assertEqual(outputs[2], "")

    def test_daily_cap_is_enforced_across_sessions(self) -> None:
        self.write_index([CODEREVIEW_SKILL])
        from datetime import date

        self.write_hook_state({"day": date.today().isoformat(), "daily_count": 3, "sessions": {}})

        proc = self.run_hook(USER_PROMPT_SUBMIT, self.payload(session_id="fresh-session"))

        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")

    def test_daily_counter_resets_on_a_new_day(self) -> None:
        self.write_index([CODEREVIEW_SKILL])
        self.write_hook_state({"day": "2020-01-01", "daily_count": 99, "sessions": {}})

        proc = self.run_hook(USER_PROMPT_SUBMIT, self.payload())

        self.assertIn("codereview", proc.stdout)

    def test_below_threshold_prompt_is_silent(self) -> None:
        self.write_index([CODEREVIEW_SKILL])

        proc = self.run_hook(USER_PROMPT_SUBMIT, self.payload(prompt="what time is it"))

        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")

    def test_missing_index_is_silent_and_never_rebuilds(self) -> None:
        proc = self.run_hook(USER_PROMPT_SUBMIT, self.payload())

        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")
        self.assertFalse((self.home / ".cache" / "skillrecommender" / "skill_index.json").exists())

    def test_proactivity_off_is_silent(self) -> None:
        self.write_config({"proactivity_level": "off"})
        self.write_index([CODEREVIEW_SKILL])

        proc = self.run_hook(USER_PROMPT_SUBMIT, self.payload())

        self.assertEqual(proc.stdout, "")

    def test_dismissed_suggestion_is_not_re_emitted(self) -> None:
        self.write_index([CODEREVIEW_SKILL])
        first = self.run_hook(USER_PROMPT_SUBMIT, self.payload())
        self.assertIn("codereview", first.stdout)
        item = json.loads((self.data_dir / "advice.jsonl").read_text(encoding="utf-8").splitlines()[0])
        until = (utc_now() + timedelta(days=7)).isoformat()
        self.write_advisor_state({"dismissed": {item["fingerprint"]: until}})

        proc = self.run_hook(USER_PROMPT_SUBMIT, self.payload(session_id="sess-2"))

        self.assertEqual(proc.stdout, "")

    def test_empty_prompt_is_silent(self) -> None:
        self.write_index([CODEREVIEW_SKILL])

        proc = self.run_hook(USER_PROMPT_SUBMIT, self.payload(prompt="   "))

        self.assertEqual(proc.stdout, "")

    def test_hook_completes_within_time_budget(self) -> None:
        self.write_index([CODEREVIEW_SKILL] * 1 + [
            {
                "name": f"filler-skill-{i}",
                "source": "test",
                "path": f"/tmp/filler-{i}/SKILL.md",
                "description": "A filler skill for volume testing of the index",
                "triggers": [],
                "keywords": ["filler", "volume"],
                "domains": ["workflow"],
            }
            for i in range(400)
        ])

        started = time.monotonic()
        proc = self.run_hook(USER_PROMPT_SUBMIT, self.payload())
        elapsed = time.monotonic() - started

        self.assertEqual(proc.returncode, 0)
        self.assertLess(elapsed, 2.0)
        self.assertIn("codereview", proc.stdout)


if __name__ == "__main__":
    unittest.main()
