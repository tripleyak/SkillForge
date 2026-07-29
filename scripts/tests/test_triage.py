#!/usr/bin/env python3
"""
Tests for triage_skill_request.py: word-boundary matching, honest match
bands, deduped recommendations, and improve-request resolution against the
full index (not the capped top-5 match list).
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

from _constants import score_band  # noqa: E402
from common import phrase_in_text  # noqa: E402
from triage_skill_request import (  # noqa: E402
    Action,
    calculate_match_score,
    find_matching_skills,
    make_triage_decision,
    resolve_skill_by_name,
    triage_request,
)


def skill(name: str, description: str = "", domains=None, keywords=None,
          triggers=None) -> dict:
    return {
        "name": name,
        "source": "test",
        "path": f"/skills/{name}/SKILL.md",
        "priority": 1,
        "description": description,
        "keywords": keywords or name.split("-"),
        "domains": domains or [],
        "triggers": triggers or [],
        "version": "1.0.0",
    }


class WordBoundaryTest(unittest.TestCase):
    def test_ai_does_not_match_email(self) -> None:
        self.assertFalse(phrase_in_text("ai", "send an email to the team"))

    def test_ml_does_not_match_html(self) -> None:
        self.assertFalse(phrase_in_text("ml", "render the html template"))

    def test_ci_does_not_match_specialist(self) -> None:
        self.assertFalse(phrase_in_text("ci", "a specialist tool"))

    def test_whole_word_matches(self) -> None:
        self.assertTrue(phrase_in_text("ai", "an ai assistant"))
        self.assertTrue(phrase_in_text("code review", "run a code review now"))

    def test_email_skill_does_not_score_ai_description_match(self) -> None:
        email_skill = skill(
            "email-digest",
            description="Compiles email digests from mailing lists.",
            domains=["documentation"],
            keywords=["email", "digest"],
        )
        _score, reasons = calculate_match_score("help me with ai prompts", email_skill)
        self.assertFalse(
            any("description: ai" in r for r in reasons), reasons
        )


class BandTest(unittest.TestCase):
    def test_band_boundaries(self) -> None:
        self.assertEqual(score_band(100), "strong")
        self.assertEqual(score_band(80), "strong")
        self.assertEqual(score_band(79), "moderate")
        self.assertEqual(score_band(60), "moderate")
        self.assertEqual(score_band(59), "weak")
        self.assertEqual(score_band(40), "weak")
        self.assertEqual(score_band(39), "poor")
        self.assertEqual(score_band(0), "poor")

    def test_matches_carry_band_field(self) -> None:
        skills = [
            skill(
                "code-review",
                description="Use when running a code review on a pull request.",
                domains=["code_quality"],
                keywords=["code", "review", "code review"],
                triggers=["code review"],
            )
        ]
        matches = find_matching_skills("run a code review", skills)
        self.assertTrue(matches)
        top = matches[0]
        self.assertIn("band", top)
        self.assertEqual(top["band"], score_band(top["score"]))


class DedupeRecommendationsTest(unittest.TestCase):
    def test_duplicate_skill_names_collapse(self) -> None:
        dup_a = skill("code-review", description="Use when reviewing code.",
                      domains=["code_quality"], keywords=["code", "review"])
        dup_b = dict(dup_a, path="/other/code-review/SKILL.md")
        matches = find_matching_skills("code review please", [dup_a, dup_b])
        names = [m["name"] for m in matches]
        self.assertEqual(len(names), len(set(names)), names)


class ImproveResolutionTest(unittest.TestCase):
    def make_index(self, count: int = 30) -> list:
        # Many strong decoys so the named target cannot be in the top 5
        skills = [
            skill(
                f"debug-helper-{i}",
                description="Use when debugging an error or stack trace.",
                domains=["debugging"],
                keywords=["debug", "error", "trace"],
                triggers=["debug this"],
            )
            for i in range(count)
        ]
        skills.append(
            skill(
                "obscure-target",
                description="Use when doing something extremely specific.",
                domains=["general"],
                keywords=["obscure"],
            )
        )
        return skills

    def test_resolve_skill_by_name_exact(self) -> None:
        skills = self.make_index()
        resolved = resolve_skill_by_name("obscure-target", skills)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved["name"], "obscure-target")

    def test_resolve_skill_by_name_partial(self) -> None:
        skills = self.make_index()
        resolved = resolve_skill_by_name("obscure", skills)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved["name"], "obscure-target")

    def test_improve_decision_resolves_beyond_top_5(self) -> None:
        skills = self.make_index()
        query = "improve the obscure-target skill to debug error traces"
        matches = find_matching_skills(query, skills, limit=5)
        # Precondition: the named skill is NOT in the capped match list
        self.assertNotIn("obscure-target", [m["name"] for m in matches])

        signals = {"mentioned_skill_name": "obscure-target"}
        action, details = make_triage_decision(
            "explicit_improve", signals, matches, query, skills=skills
        )
        self.assertEqual(action, Action.IMPROVE_EXISTING)
        self.assertEqual(details["target_skill"], "obscure-target")


class TriageEndToEndTest(unittest.TestCase):
    def _write_index(self, tmp: Path, skills: list) -> Path:
        index_path = tmp / "index.json"
        index_path.write_text(json.dumps({
            "version": "2.0.0",
            "skills": skills,
            "domains": {},
            "sources": {},
            "total_count": len(skills),
        }), encoding="utf-8")
        return index_path

    def test_code_review_query_ranks_code_review_skills_first(self) -> None:
        skills = [
            skill(
                "vercel-agent",
                description="Use when deploying agents to vercel hosting.",
                domains=["deployment", "ai_ml"],
                keywords=["vercel", "agent", "deploy"],
            ),
            skill(
                "code-review",
                description="Use when running a code review or pr review.",
                domains=["code_quality"],
                keywords=["code", "review", "code review"],
                triggers=["code review"],
            ),
        ]
        with tempfile.TemporaryDirectory(prefix="skillforge-test-") as tmp:
            index_path = self._write_index(Path(tmp), skills)
            result = triage_request("create a skill for code review",
                                    index_path=index_path)
        self.assertTrue(result.success)
        top = result.data["top_matches"][0]
        self.assertEqual(top["name"], "code-review")
        # JSON keeps the numeric score plus band
        self.assertIn("score", top)
        self.assertIn("band", top)
        self.assertIsInstance(top["score"], int)

    def test_missing_index_fails_cleanly(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skillforge-test-") as tmp:
            result = triage_request("anything", index_path=Path(tmp) / "no.json")
        self.assertFalse(result.success)

    def test_human_reasons_use_bands_not_percentages(self) -> None:
        skills = [
            skill(
                "code-review",
                description="Use when running a code review or pr review.",
                domains=["code_quality"],
                keywords=["code", "review", "code review"],
                triggers=["code review"],
            ),
        ]
        with tempfile.TemporaryDirectory(prefix="skillforge-test-") as tmp:
            index_path = self._write_index(Path(tmp), skills)
            result = triage_request("do I have a skill for code review?",
                                    index_path=index_path)
        reason = result.data["details"].get("reason", "")
        self.assertNotRegex(reason, r"\d+%", reason)
        self.assertIn("top_band", result.data["details"])


if __name__ == "__main__":
    unittest.main()
