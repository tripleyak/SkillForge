#!/usr/bin/env python3
"""
Tests for mine_skill_friction.py - consent gate, transcript mining against
SYNTHETIC JSONL fixtures (never real transcripts), abandonment detection,
Bash pattern clustering, secret redaction, and evidence output.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import mine_skill_friction as msf  # noqa: E402


# ---------------------------------------------------------------------------
# Synthetic transcript builders (mirror the real ~/.claude/projects schema:
# {"type": "assistant", "message": {"content": [{"type": "tool_use", ...}]}})
# ---------------------------------------------------------------------------

def assistant_tool_use(name: str, tool_input: dict) -> dict:
    return {
        "type": "assistant",
        "message": {"content": [
            {"type": "tool_use", "id": "toolu_x", "name": name, "input": tool_input},
        ]},
    }


def user_message(text: str) -> dict:
    return {"type": "user", "message": {"content": text}}


def user_tool_result() -> dict:
    return {"type": "user",
            "message": {"content": [{"type": "tool_result", "content": "ok"}]}}


def write_session(projects: Path, project: str, session: str, entries) -> Path:
    project_dir = projects / project
    project_dir.mkdir(parents=True, exist_ok=True)
    path = project_dir / f"{session}.jsonl"
    lines = [json.dumps(e) for e in entries]
    lines.insert(1, "{malformed json line")  # every fixture has schema noise
    lines.insert(2, json.dumps({"type": "queue-operation", "operation": "enqueue"}))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run_mine(projects: Path, **kwargs) -> dict:
    defaults = {"days": 30, "min_sessions": 2, "min_count": 2}
    defaults.update(kwargs)
    return msf.mine(projects, **defaults)


class ConsentGateTest(unittest.TestCase):
    def test_refuses_without_consent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code = msf.main(["--projects-dir", tmp,
                             "--output", str(Path(tmp) / "out.json")])
            self.assertEqual(code, 2)
            self.assertFalse((Path(tmp) / "out.json").exists())

    def test_runs_with_consent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp) / "projects"
            projects.mkdir()
            out = Path(tmp) / "out.json"
            code = msf.main(["--consent", "--projects-dir", str(projects),
                             "--output", str(out), "--json"])
            self.assertEqual(code, 0)
            self.assertTrue(out.exists())

    def test_help_states_purely_local(self) -> None:
        import argparse  # noqa: F401
        with self.assertRaises(SystemExit), \
                mock.patch("sys.stdout") as fake_stdout:
            msf.main(["--help"])
        printed = "".join(str(c) for c in fake_stdout.write.call_args_list)
        self.assertIn("local", printed.lower())


class SkillInvocationTest(unittest.TestCase):
    def test_counts_skill_invocations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp)
            write_session(projects, "proj-a", "s1", [
                assistant_tool_use("Skill", {"skill": "deploy-helper", "args": ""}),
                assistant_tool_use("Skill", {"skill": "deploy-helper", "args": ""}),
                assistant_tool_use("Skill", {"skill": "pdf-tool", "args": ""}),
            ])
            data = run_mine(projects)
            self.assertEqual(data["skill_invocations"]["deploy-helper"], 2)
            self.assertEqual(data["skill_invocations"]["pdf-tool"], 1)

    def test_transcripts_scanned_counted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp)
            write_session(projects, "proj-a", "s1", [user_message("hi")])
            write_session(projects, "proj-b", "s2", [user_message("hi")])
            data = run_mine(projects)
            self.assertEqual(data["transcripts_scanned"], 2)


class AbandonmentTest(unittest.TestCase):
    def test_correction_after_skill_is_abandonment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp)
            write_session(projects, "proj-a", "s1", [
                assistant_tool_use("Skill", {"skill": "wrong-skill"}),
                user_message("no, stop - that's not what I wanted at all"),
            ])
            data = run_mine(projects)
            self.assertEqual(len(data["abandoned"]), 1)
            self.assertEqual(data["abandoned"][0]["skill"], "wrong-skill")

    def test_positive_followup_is_not_abandonment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp)
            write_session(projects, "proj-a", "s1", [
                assistant_tool_use("Skill", {"skill": "right-skill"}),
                user_message("great, looks perfect - continue"),
            ])
            data = run_mine(projects)
            self.assertEqual(data["abandoned"], [])

    def test_tool_results_do_not_clear_pending_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp)
            write_session(projects, "proj-a", "s1", [
                assistant_tool_use("Skill", {"skill": "slow-skill"}),
                user_tool_result(),
                user_message("stop, wrong skill"),
            ])
            data = run_mine(projects)
            self.assertEqual(len(data["abandoned"]), 1)

    def test_correction_deep_in_message_not_flagged(self) -> None:
        text = ("thanks, that worked nicely. " * 5) + "there is no rush on the rest"
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp)
            write_session(projects, "proj-a", "s1", [
                assistant_tool_use("Skill", {"skill": "fine-skill"}),
                user_message(text),
            ])
            data = run_mine(projects)
            self.assertEqual(data["abandoned"], [])

    def test_is_correction_word_boundary(self) -> None:
        self.assertTrue(msf.is_correction("No, use the other file"))
        self.assertTrue(msf.is_correction("that's not what I meant"))
        self.assertFalse(msf.is_correction("now let's continue"))  # 'no' not a token
        self.assertFalse(msf.is_correction("nothing else needed, thanks"))


class BashClusteringTest(unittest.TestCase):
    def test_repeated_uncovered_pattern_becomes_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp)
            for i, project in enumerate(("proj-a", "proj-b", "proj-c")):
                write_session(projects, project, f"s{i}", [
                    assistant_tool_use("Bash", {
                        "command": f"ffmpeg -i in{i}.mov -vf scale=640:-1 out{i}.mp4"}),
                ])
            with mock.patch.object(msf, "load_skill_index", return_value=[]):
                data = run_mine(projects, min_sessions=3, min_count=3)
            patterns = [c["pattern"] for c in data["candidate_patterns"]]
            self.assertIn("ffmpeg", patterns)

    def test_trivial_commands_never_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp)
            for i, project in enumerate(("proj-a", "proj-b")):
                write_session(projects, project, f"s{i}", [
                    assistant_tool_use("Bash", {"command": "ls -la /tmp"}),
                    assistant_tool_use("Bash", {"command": "git status"}),
                ])
            data = run_mine(projects)
            self.assertEqual(data["candidate_patterns"], [])

    def test_covered_pattern_excluded_from_candidates(self) -> None:
        index = [{"name": "ffmpeg-encoder",
                  "description": "Use when running ffmpeg encode jobs"}]
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp)
            for i, project in enumerate(("proj-a", "proj-b")):
                write_session(projects, project, f"s{i}", [
                    assistant_tool_use("Bash", {"command": "ffmpeg -i a.mov b.mp4"}),
                ])
            with mock.patch.object(msf, "load_skill_index", return_value=index):
                data = run_mine(projects)
            self.assertEqual(data["candidate_patterns"], [])
            covered = [c["pattern"] for c in data["covered_patterns"]]
            self.assertIn("ffmpeg", covered)

    def test_normalize_command(self) -> None:
        self.assertEqual(msf.normalize_command("cd /x && ffmpeg -i a b"), "ffmpeg")
        self.assertEqual(msf.normalize_command("FOO=1 terraform plan"),
                         "terraform plan")
        self.assertIsNone(msf.normalize_command("ls -la"))
        self.assertIsNone(msf.normalize_command("git status"))
        self.assertEqual(msf.normalize_command("git bisect start"), "git bisect")
        self.assertEqual(msf.normalize_command("/usr/local/bin/jq '.a' f"), "jq")

    def test_min_sessions_threshold_respected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp)
            write_session(projects, "proj-a", "s1", [
                assistant_tool_use("Bash", {"command": "ffmpeg -i a.mov b.mp4"}),
                assistant_tool_use("Bash", {"command": "ffmpeg -i c.mov d.mp4"}),
            ])
            with mock.patch.object(msf, "load_skill_index", return_value=[]):
                data = run_mine(projects, min_sessions=2, min_count=2)
            self.assertEqual(data["candidate_patterns"], [])  # one session only


class RedactionTest(unittest.TestCase):
    def test_key_value_secrets_redacted(self) -> None:
        redacted = msf.redact("export API_KEY=sk_live_abcdef123456 && run")
        self.assertNotIn("sk_live_abcdef123456", redacted)
        self.assertIn("[REDACTED]", redacted)

    def test_password_colon_form_redacted(self) -> None:
        redacted = msf.redact('login with password: "hunter2secret"')
        self.assertNotIn("hunter2secret", redacted)

    def test_bare_tokens_redacted(self) -> None:
        for token in ("sk-abc123def456ghi789", "ghp_AbCdEf123456789",
                      "xoxb-1234-abcdefabcdef", "AKIAIOSFODNN7EXAMPLE"):
            redacted = msf.redact(f"use {token} here")
            self.assertNotIn(token, redacted, token)

    def test_normal_text_untouched(self) -> None:
        text = "run the deploy script and check the tokenizer output"
        self.assertEqual(msf.redact(text), text)

    def test_abandonment_evidence_is_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp)
            write_session(projects, "proj-a", "s1", [
                assistant_tool_use("Skill", {"skill": "auth-skill"}),
                user_message("stop! that leaked my api_key=supersecret999"),
            ])
            data = run_mine(projects)
            self.assertEqual(len(data["abandoned"]), 1)
            self.assertNotIn("supersecret999", json.dumps(data))

    def test_bash_example_evidence_is_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp)
            for i, project in enumerate(("proj-a", "proj-b")):
                write_session(projects, project, f"s{i}", [
                    assistant_tool_use("Bash", {
                        "command": "vault write secret=topsecretvalue123"}),
                ])
            with mock.patch.object(msf, "load_skill_index", return_value=[]):
                data = run_mine(projects)
            self.assertNotIn("topsecretvalue123", json.dumps(data))


class EvidenceOutputTest(unittest.TestCase):
    def test_evidence_file_written_with_expected_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp) / "projects"
            write_session(projects, "proj-a", "s1", [
                assistant_tool_use("Skill", {"skill": "some-skill"}),
            ])
            out = Path(tmp) / "evidence" / "friction.json"
            code = msf.main(["--consent", "--projects-dir", str(projects),
                             "--output", str(out), "--json"])
            self.assertEqual(code, 0)
            payload = json.loads(out.read_text())
            for key in ("generated_at", "days", "skill_invocations",
                        "abandoned", "candidate_patterns"):
                self.assertIn(key, payload)

    def test_missing_projects_dir_exits_1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code = msf.main(["--consent",
                             "--projects-dir", str(Path(tmp) / "missing"),
                             "--output", str(Path(tmp) / "o.json")])
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
