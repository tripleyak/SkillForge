#!/usr/bin/env python3
"""
Tests for run_skill_evals.py - static structure/lint checks, TODO placeholder
handling, live-mode plumbing (with a monkeypatched claude runner), and exit
codes.
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

import run_skill_evals as rse  # noqa: E402


GOOD_SKILL_MD = """---
name: deploy-checker
description: "Use when deploying a service and the user asks to verify the deploy, check rollout health, or debug a failed release."
---

# Deploy Checker

Body.
"""

GOOD_TRIGGERS = {
    "positive": [
        "verify the deploy went out",
        "check rollout health for the api",
    ],
    "near_miss": ["write a blog post about our release process"],
    "holdout": ["why did my release fail to deploy"],
}

GOOD_SCENARIO = """---
task: "Deploy service X and verify the rollout"
baseline_failure: "Agents declare success without checking rollout status"
assertions:
  - "Output includes a rollout health check: status must be quoted"
  - "Output does not declare success without evidence"
runs: 1
---
Setup notes here.
"""


def build_skill(tmp: str, skill_md: str = GOOD_SKILL_MD,
                triggers=GOOD_TRIGGERS, scenario: str = GOOD_SCENARIO) -> Path:
    skill_dir = Path(tmp) / "deploy-checker"
    scenarios = skill_dir / "evals" / "scenarios"
    scenarios.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")
    if triggers is not None:
        (skill_dir / "evals" / "triggers.json").write_text(
            triggers if isinstance(triggers, str) else json.dumps(triggers),
            encoding="utf-8")
    if scenario is not None:
        (scenarios / "01-example.md").write_text(scenario, encoding="utf-8")
    return skill_dir


class ContentWordsTest(unittest.TestCase):
    def test_stopwords_and_short_tokens_excluded(self) -> None:
        words = rse.content_words("Use this when the API is slow")
        self.assertNotIn("use", words)
        self.assertNotIn("the", words)
        self.assertNotIn("is", words)
        self.assertIn("api", words)
        self.assertIn("slow", words)

    def test_word_boundary_tokens(self) -> None:
        # 'email' must not decompose into a match for 'ai'
        self.assertNotIn("ai", rse.content_words("send an email"))

    def test_placeholder_detection(self) -> None:
        self.assertTrue(rse.is_placeholder("TODO: a real user phrasing"))
        self.assertTrue(rse.is_placeholder("this is a todo item"))
        self.assertFalse(rse.is_placeholder("verify the deployment"))


class StaticPassTest(unittest.TestCase):
    def test_good_skill_passes_and_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = build_skill(tmp)
            code = rse.main([str(skill_dir), "--static", "--json"])
            self.assertEqual(code, 0)

    def test_scenario_returns_parsed_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = build_skill(tmp)
            report = rse.EvalReport(str(skill_dir), "static")
            triggers, scenarios = rse.run_static(skill_dir, report)
            self.assertTrue(report.passed)
            self.assertEqual(len(scenarios), 1)
            self.assertEqual(scenarios[0]["runs"], 1)
            self.assertEqual(len(scenarios[0]["assertions"]), 2)
            self.assertEqual(triggers["near_miss"], GOOD_TRIGGERS["near_miss"])

    def test_assertions_with_colons_in_quotes_parse_as_strings(self) -> None:
        # Regression: the vendored YAML parser used to split quoted list
        # items containing a colon into bogus one-key mappings.
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = build_skill(tmp)
            report = rse.EvalReport(str(skill_dir), "static")
            _triggers, scenarios = rse.run_static(skill_dir, report)
            self.assertIn("status must be quoted", scenarios[0]["assertions"][0])


class StaticFailureTest(unittest.TestCase):
    def _failures(self, skill_dir: Path):
        report = rse.EvalReport(str(skill_dir), "static")
        rse.run_static(skill_dir, report)
        return report.failures

    def test_missing_evals_dir_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "bare"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(GOOD_SKILL_MD, encoding="utf-8")
            failures = self._failures(skill_dir)
            self.assertTrue(any(f.target == "evals/" for f in failures))

    def test_missing_triggers_json_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = build_skill(tmp, triggers=None)
            failures = self._failures(skill_dir)
            self.assertTrue(any("triggers.json" in f.target for f in failures))

    def test_invalid_json_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = build_skill(tmp, triggers="{not json")
            failures = self._failures(skill_dir)
            self.assertTrue(any(f.name == "parses" for f in failures))

    def test_missing_trigger_key_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = build_skill(tmp, triggers={"positive": ["deploy check"]})
            failures = self._failures(skill_dir)
            names = {f.name for f in failures}
            self.assertIn("shape.near_miss", names)
            self.assertIn("shape.holdout", names)

    def test_non_string_trigger_entries_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad = dict(GOOD_TRIGGERS, positive=["ok", 42])
            skill_dir = build_skill(tmp, triggers=bad)
            failures = self._failures(skill_dir)
            self.assertTrue(any(f.name == "shape.positive" for f in failures))

    def test_empty_positive_list_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad = dict(GOOD_TRIGGERS, positive=[])
            skill_dir = build_skill(tmp, triggers=bad)
            failures = self._failures(skill_dir)
            self.assertTrue(any(f.name == "positive.nonempty" for f in failures))

    def test_no_scenarios_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = build_skill(tmp, scenario=None)
            failures = self._failures(skill_dir)
            self.assertTrue(any(f.target == "evals/scenarios/" for f in failures))

    def test_scenario_missing_assertions_fails(self) -> None:
        bad_scenario = """---
task: "Do the thing"
baseline_failure: "Fails"
---
"""
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = build_skill(tmp, scenario=bad_scenario)
            failures = self._failures(skill_dir)
            self.assertTrue(any(f.name == "field.assertions" for f in failures))

    def test_scenario_bad_runs_fails(self) -> None:
        bad_scenario = GOOD_SCENARIO.replace("runs: 1", "runs: 0")
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = build_skill(tmp, scenario=bad_scenario)
            failures = self._failures(skill_dir)
            self.assertTrue(any(f.name == "field.runs" for f in failures))

    def test_exit_code_10_on_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = build_skill(tmp, triggers=None)
            code = rse.main([str(skill_dir), "--static", "--json"])
            self.assertEqual(code, 10)

    def test_exit_code_1_on_missing_dir(self) -> None:
        code = rse.main(["/nonexistent/skill-dir", "--static"])
        self.assertEqual(code, 1)


class KeywordLintTest(unittest.TestCase):
    def test_unrelated_positive_query_fails_lint(self) -> None:
        bad = dict(GOOD_TRIGGERS, positive=["make me a sandwich"])
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = build_skill(tmp, triggers=bad)
            report = rse.EvalReport(str(skill_dir), "static")
            rse.run_static(skill_dir, report)
            failures = [f for f in report.failures if f.name == "keyword_lint"]
            self.assertEqual(len(failures), 1)
            self.assertIn("sandwich", failures[0].target)

    def test_todo_placeholder_passes_lint(self) -> None:
        placeholder = dict(GOOD_TRIGGERS,
                           positive=["TODO: a user phrasing that should trigger"])
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = build_skill(tmp, triggers=placeholder)
            report = rse.EvalReport(str(skill_dir), "static")
            rse.run_static(skill_dir, report)
            self.assertTrue(report.passed)

    def test_holdout_is_linted_too(self) -> None:
        bad = dict(GOOD_TRIGGERS, holdout=["completely unrelated cooking question"])
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = build_skill(tmp, triggers=bad)
            report = rse.EvalReport(str(skill_dir), "static")
            rse.run_static(skill_dir, report)
            failures = [f for f in report.failures if "holdout" in f.target]
            self.assertEqual(len(failures), 1)

    def test_near_miss_is_not_linted(self) -> None:
        # near-misses SHOULD be unrelated to the description; never linted.
        bad = dict(GOOD_TRIGGERS, near_miss=["completely unrelated cooking question"])
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = build_skill(tmp, triggers=bad)
            report = rse.EvalReport(str(skill_dir), "static")
            rse.run_static(skill_dir, report)
            self.assertTrue(report.passed)


class ExtractJsonTest(unittest.TestCase):
    def test_plain_json(self) -> None:
        self.assertEqual(rse.extract_json('{"a": 1}'), {"a": 1})

    def test_json_embedded_in_prose(self) -> None:
        text = 'Sure, here is my verdict:\n{"triggered": true}\nDone.'
        self.assertEqual(rse.extract_json(text), {"triggered": True})

    def test_nested_json(self) -> None:
        text = 'x {"verdicts": [{"pass": true, "evidence": "{quoted}"}]} y'
        parsed = rse.extract_json(text)
        self.assertEqual(parsed["verdicts"][0]["pass"], True)

    def test_no_json_returns_none(self) -> None:
        self.assertIsNone(rse.extract_json("no json here"))


def fake_claude_factory(scenario_output: str, verdicts, triggered_map):
    """Build an invoke_claude stub covering scenario, judge, and router calls."""
    def fake(prompt: str, max_turns: int, timeout: int):
        if "strict evaluator" in prompt:
            return True, json.dumps({"verdicts": verdicts})
        if "deciding whether to load a skill" in prompt:
            for query, fire in triggered_map.items():
                if repr(query) in prompt:
                    return True, json.dumps({"triggered": fire})
            return True, json.dumps({"triggered": False})
        return True, scenario_output
    return fake


class LiveModeTest(unittest.TestCase):
    def test_missing_cli_exits_11(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = build_skill(tmp)
            with mock.patch.object(rse, "claude_available", return_value=False):
                code = rse.main([str(skill_dir), "--live"])
            self.assertEqual(code, 11)

    def test_live_all_pass(self) -> None:
        verdicts = [
            {"assertion": "Output includes a rollout health check: status must be quoted",
             "pass": True, "evidence": "quoted status"},
            {"assertion": "Output does not declare success without evidence",
             "pass": True, "evidence": "evidence shown"},
        ]
        triggered = {
            "verify the deploy went out": True,
            "check rollout health for the api": True,
            "why did my release fail to deploy": True,
            "write a blog post about our release process": False,
        }
        fake = fake_claude_factory("agent output", verdicts, triggered)
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = build_skill(tmp)
            with mock.patch.object(rse, "claude_available", return_value=True), \
                 mock.patch.object(rse, "invoke_claude", side_effect=fake):
                report = rse.EvalReport(str(skill_dir), "live")
                triggers, scenarios = rse.run_static(skill_dir, report)
                board = rse.run_live_scenarios(scenarios, report, 12, 60)
                trig = rse.run_live_triggers(triggers, "deploy-checker",
                                             "desc", report, 60)
            self.assertTrue(board["01-example.md"]["passed"])
            self.assertEqual(trig["recall"], 1.0)
            self.assertEqual(trig["precision"], 1.0)
            self.assertTrue(report.passed)

    def test_live_failed_assertion_shows_evidence(self) -> None:
        verdicts = [
            {"assertion": "Output includes a rollout health check: status must be quoted",
             "pass": False, "evidence": "no health check appears in output"},
            {"assertion": "Output does not declare success without evidence",
             "pass": True, "evidence": "ok"},
        ]
        fake = fake_claude_factory("agent output", verdicts, {})
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = build_skill(tmp)
            with mock.patch.object(rse, "invoke_claude", side_effect=fake):
                report = rse.EvalReport(str(skill_dir), "live")
                _triggers, scenarios = rse.run_static(skill_dir, report)
                board = rse.run_live_scenarios(scenarios, report, 12, 60)
            self.assertFalse(board["01-example.md"]["passed"])
            failing = [f for f in report.failures
                       if f.evidence == "no health check appears in output"]
            self.assertEqual(len(failing), 1)

    def test_live_scenario_timeout_fails_run(self) -> None:
        def timeout_stub(prompt, max_turns, timeout):
            return False, "timed out after 60s"
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = build_skill(tmp)
            with mock.patch.object(rse, "invoke_claude", side_effect=timeout_stub):
                report = rse.EvalReport(str(skill_dir), "live")
                _t, scenarios = rse.run_static(skill_dir, report)
                board = rse.run_live_scenarios(scenarios, report, 12, 60)
            self.assertFalse(board["01-example.md"]["passed"])

    def test_judge_garbage_output_fails_all_assertions(self) -> None:
        def garbage_judge(prompt, max_turns, timeout):
            if "strict evaluator" in prompt:
                return True, "I think it went well!"
            return True, "agent output"
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = build_skill(tmp)
            with mock.patch.object(rse, "invoke_claude", side_effect=garbage_judge):
                report = rse.EvalReport(str(skill_dir), "live")
                _t, scenarios = rse.run_static(skill_dir, report)
                board = rse.run_live_scenarios(scenarios, report, 12, 60)
            self.assertFalse(board["01-example.md"]["passed"])

    def test_trigger_precision_counts_false_positives(self) -> None:
        triggered = {
            "verify the deploy went out": True,
            "check rollout health for the api": False,
            "why did my release fail to deploy": True,
            "write a blog post about our release process": True,  # false fire
        }
        fake = fake_claude_factory("out", [], triggered)
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = build_skill(tmp)
            with mock.patch.object(rse, "invoke_claude", side_effect=fake):
                report = rse.EvalReport(str(skill_dir), "live")
                triggers, _s = rse.run_static(skill_dir, report)
                trig = rse.run_live_triggers(triggers, "deploy-checker",
                                             "desc", report, 60)
            self.assertEqual(trig["true_positive"], 2)
            self.assertEqual(trig["false_negative"], 1)
            self.assertEqual(trig["false_positive"], 1)
            self.assertAlmostEqual(trig["recall"], 2 / 3)
            self.assertAlmostEqual(trig["precision"], 2 / 3)


class JsonOutputTest(unittest.TestCase):
    def test_json_output_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = build_skill(tmp)
            report = rse.EvalReport(str(skill_dir), "static")
            rse.run_static(skill_dir, report)
            payload = report.to_dict()
            self.assertTrue(payload["passed"])
            self.assertEqual(payload["mode"], "static")
            self.assertIsInstance(payload["checks"], list)
            self.assertIn("target", payload["checks"][0])


if __name__ == "__main__":
    unittest.main()
