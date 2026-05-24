#!/usr/bin/env python3
"""
Regression tests for proactive Context Skill Advisor primitives.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import context_advisor  # noqa: E402
import skillforge_config  # noqa: E402
from advisor_scoring import Suggestion, build_suggestions  # noqa: E402
from context_sources import Evidence, collect_project_evidence, matches_terms, query_terms  # noqa: E402
from skillforge_config import deep_merge, level_settings  # noqa: E402


class ContextAdvisorTest(unittest.TestCase):
    def test_deep_merge_preserves_defaults_and_applies_project_override(self) -> None:
        base = {
            "proactivity_level": "balanced",
            "context_sources": {"personal": {"enabled": True, "paths": ["~/kb"]}},
        }
        override = {"context_sources": {"personal": {"paths": ["~/Documents/Work"]}}}

        merged = deep_merge(base, override)

        self.assertEqual(merged["proactivity_level"], "balanced")
        self.assertTrue(merged["context_sources"]["personal"]["enabled"])
        self.assertEqual(merged["context_sources"]["personal"]["paths"], ["~/Documents/Work"])

    def test_project_override_takes_precedence_over_global_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skillforge-config-") as tmp:
            root = Path(tmp)
            global_path = root / "home-config" / "config.json"
            project = root / "project"
            project.mkdir()

            skillforge_config.write_json(global_path, {"proactivity_level": "quiet"})
            skillforge_config.write_project_override(project, "active")

            with patch.object(skillforge_config, "CONFIG_FILE", global_path):
                loaded = skillforge_config.load_config(project)

        self.assertEqual(loaded.config["proactivity_level"], "active")
        self.assertIsNotNone(loaded.project_path)
        self.assertEqual(loaded.global_path, global_path)

    def test_balanced_threshold_matches_accepted_design(self) -> None:
        settings = level_settings("balanced")

        self.assertEqual(settings["threshold"], 70)
        self.assertEqual(settings["interval_seconds"], 7200)

    def test_build_suggestions_uses_existing_skill_match_score(self) -> None:
        skills = [
            {
                "name": "codereview",
                "source": "test",
                "path": "/tmp/codereview/SKILL.md",
                "description": "Review code and pull requests for bugs and regressions",
                "triggers": ["code review"],
                "keywords": ["code", "review", "pull", "request"],
                "domains": ["code_quality"],
            }
        ]
        evidence = [
            Evidence(
                tier="session",
                source="provided-context",
                path="session",
                excerpt="Please do a code review for this pull request.",
                matched_terms=["code", "review"],
            )
        ]

        suggestions = build_suggestions(
            context_text="Please do a code review for this pull request.",
            skills=skills,
            evidence=evidence,
            config={"proactivity_level": "balanced"},
            state={},
            project_key="/tmp/project",
        )

        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0].skill_name, "codereview")
        self.assertGreaterEqual(suggestions[0].scores["skill_match"], 80)
        self.assertGreaterEqual(suggestions[0].final_score, 70)

    def test_feedback_updates_queue_and_advisor_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skillforge-advisor-state-") as tmp:
            root = Path(tmp)
            queue_file = root / "advice.jsonl"
            state_file = root / "advisor_state.json"
            suggestion = Suggestion(
                id="abc123",
                fingerprint="fingerprint-1",
                action="use_existing",
                skill_name="codereview",
                skill_source="test",
                skill_path="/tmp/codereview/SKILL.md",
                confidence="high",
                final_score=91,
                scores={
                    "skill_match": 90,
                    "context_evidence": 80,
                    "timeliness": 30,
                    "user_feedback": 0,
                    "directness": 100,
                },
                why_now="codereview matches the current work",
                evidence=[],
                choices=["use", "snooze", "dismiss", "never for this project"],
                personal_context_used=False,
                project_key="/tmp/project",
            )

            with patch.object(context_advisor, "QUEUE_FILE", queue_file), patch.object(context_advisor, "STATE_FILE", state_file):
                queued = context_advisor.append_queue([suggestion])
                self.assertEqual(len(queued), 1)

                accepted = context_advisor.apply_feedback(SimpleNamespace(suggestion_id="abc123"), "accepted")
                self.assertTrue(accepted.success)
                state = context_advisor.load_state()
                self.assertEqual(state["accepted"]["codereview"], 1)

                snoozed = context_advisor.apply_feedback(SimpleNamespace(suggestion_id="abc123", hours=12), "snoozed")
                self.assertTrue(snoozed.success)
                self.assertTrue(context_advisor.is_suppressed(suggestion, context_advisor.load_state()))

                dismissed = context_advisor.apply_feedback(SimpleNamespace(suggestion_id="abc123"), "dismissed")
                self.assertTrue(dismissed.success)
                state = context_advisor.load_state()
                self.assertIn("fingerprint-1", state["dismissed"])

                never = context_advisor.apply_feedback(SimpleNamespace(suggestion_id="abc123"), "project_suppressed")
                self.assertTrue(never.success)
                state = context_advisor.load_state()
                self.assertIn("codereview", state["never_projects"]["/tmp/project"])

                items = context_advisor.read_queue()

        self.assertEqual(items[0]["status"], "project_suppressed")

    def test_duplicate_skill_names_keep_source_path_identity(self) -> None:
        skills = [
            {
                "name": "grill-with-docs",
                "source": "codex-custom",
                "path": "/codex/grill-with-docs/SKILL.md",
                "description": "Challenge a plan against docs and existing domain model",
                "triggers": ["grill with docs"],
                "keywords": ["grill", "docs", "plan"],
                "domains": ["documentation"],
            },
            {
                "name": "grill-with-docs",
                "source": "claude-custom",
                "path": "/claude/grill-with-docs/SKILL.md",
                "description": "Challenge a plan against docs and existing domain model",
                "triggers": ["grill with docs"],
                "keywords": ["grill", "docs", "plan"],
                "domains": ["documentation"],
            },
        ]
        evidence = [
            Evidence(
                tier="session",
                source="provided-context",
                path="session",
                excerpt="please use grill-with-docs to co-design proactive skill suggestions",
                matched_terms=["grill-with-docs"],
            )
        ]

        suggestions = build_suggestions(
            context_text="please use grill-with-docs to co-design proactive skill suggestions",
            skills=skills,
            evidence=evidence,
            config={"proactivity_level": "balanced"},
            state={},
            project_key="/tmp/project",
        )

        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0].skill_name, "grill-with-docs")
        self.assertEqual(suggestions[0].skill_source, "codex-custom")
        self.assertEqual(suggestions[0].skill_path, "/codex/grill-with-docs/SKILL.md")

    def test_direct_session_match_filters_broad_false_positive(self) -> None:
        skills = [
            {
                "name": "grill-with-docs",
                "source": "test",
                "path": "/tmp/grill-with-docs/SKILL.md",
                "description": "Challenge a plan against docs and existing domain model",
                "triggers": ["grill with docs"],
                "keywords": ["grill", "docs", "plan"],
                "domains": ["documentation"],
            },
            {
                "name": "every-style-editor-2",
                "source": "test",
                "path": "/tmp/every-style-editor-2/SKILL.md",
                "description": "Edit visual documents and design files",
                "triggers": ["style editor"],
                "keywords": ["visual", "document", "design"],
                "domains": ["visual", "documentation"],
            },
            {
                "name": "skill-suggestion-planner",
                "source": "test",
                "path": "/tmp/skill-suggestion-planner/SKILL.md",
                "description": "Plan proactive skill suggestions",
                "triggers": ["proactive skill suggestions"],
                "keywords": ["proactive", "suggestions", "skill"],
                "domains": ["workflow"],
            },
        ]
        evidence = [
            Evidence(
                tier="session",
                source="provided-context",
                path="session",
                excerpt="please use grill-with-docs to co-design proactive skill suggestions for SkillForge",
                matched_terms=["grill-with-docs", "proactive"],
            ),
            Evidence(
                tier="project",
                source="project-file",
                path="/tmp/project/README.md",
                excerpt="This project documents proactive skill suggestions.",
                matched_terms=["documents", "proactive", "suggestions"],
            ),
        ]

        suggestions = build_suggestions(
            context_text="please use grill-with-docs to co-design proactive skill suggestions for SkillForge",
            skills=skills,
            evidence=evidence,
            config={"proactivity_level": "balanced"},
            state={},
            project_key="/tmp/project",
        )

        self.assertEqual([suggestion.skill_name for suggestion in suggestions], ["grill-with-docs"])

    def test_context_advisor_does_not_suggest_skillforge_itself(self) -> None:
        skills = [
            {
                "name": "skillforge",
                "source": "test",
                "path": "/tmp/skillforge/SKILL.md",
                "description": "Intelligent skill router and creator",
                "triggers": ["skillforge"],
                "keywords": ["skillforge", "skill", "router"],
                "domains": ["meta"],
            },
            {
                "name": "grill-with-docs",
                "source": "test",
                "path": "/tmp/grill-with-docs/SKILL.md",
                "description": "Challenge a plan against docs and existing domain model",
                "triggers": ["grill with docs"],
                "keywords": ["grill", "docs", "plan"],
                "domains": ["documentation"],
            },
        ]
        evidence = [
            Evidence(
                tier="session",
                source="provided-context",
                path="session",
                excerpt="Use grill-with-docs to improve SkillForge proactive advising.",
                matched_terms=["grill-with-docs", "skillforge"],
            )
        ]

        suggestions = build_suggestions(
            context_text="Use grill-with-docs to improve SkillForge proactive advising.",
            skills=skills,
            evidence=evidence,
            config={"proactivity_level": "balanced"},
            state={},
            project_key="/tmp/project",
        )

        self.assertEqual([suggestion.skill_name for suggestion in suggestions], ["grill-with-docs"])

    def test_niche_kw_skill_requires_specific_name_signal(self) -> None:
        skills = [
            {
                "name": "kw-bio-research-instrument-data-to-allotrope",
                "source": "agents-custom",
                "path": "/tmp/kw-bio/SKILL.md",
                "description": "Convert scientific instrument data to Allotrope",
                "triggers": [],
                "keywords": ["excel", "data", "instrument"],
                "domains": ["spreadsheet"],
            },
            {
                "name": "xlsx",
                "source": "anthropic-agent-skills",
                "path": "/tmp/xlsx/SKILL.md",
                "description": "Create and edit Excel XLSX workbooks and spreadsheets",
                "triggers": [],
                "keywords": ["excel", "xlsx", "spreadsheet", "workbook"],
                "domains": ["spreadsheet"],
            },
        ]
        evidence = [
            Evidence(
                tier="session",
                source="provided-context",
                path="session",
                excerpt="Create an Excel workbook from Amazon advertising data with monthly spend by ASIN and SKU.",
                matched_terms=["excel", "amazon", "advertising", "asin", "sku"],
            )
        ]

        suggestions = build_suggestions(
            context_text="Create an Excel workbook from Amazon advertising data with monthly spend by ASIN and SKU.",
            skills=skills,
            evidence=evidence,
            config={"proactivity_level": "balanced"},
            state={},
            project_key="/tmp/project",
        )

        self.assertEqual([suggestion.skill_name for suggestion in suggestions], ["xlsx"])

    def test_personal_context_does_not_seed_unrelated_skill_name_matches(self) -> None:
        skills = [
            {
                "name": "chronicle",
                "source": "codex-custom",
                "path": "/tmp/chronicle/SKILL.md",
                "description": "Use recent screen history to resolve ambiguous references",
                "triggers": [],
                "keywords": ["chronicle", "screen", "history"],
                "domains": ["visual"],
            },
            {
                "name": "xlsx",
                "source": "anthropic-agent-skills",
                "path": "/tmp/xlsx/SKILL.md",
                "description": "Create and edit Excel XLSX workbooks and spreadsheets",
                "triggers": [],
                "keywords": ["excel", "xlsx", "spreadsheet", "workbook"],
                "domains": ["spreadsheet"],
            },
        ]
        evidence = [
            Evidence(
                tier="session",
                source="provided-context",
                path="session",
                excerpt="Create an Excel workbook from Amazon advertising data with monthly spend by ASIN and SKU.",
                matched_terms=["excel", "amazon", "advertising", "asin", "sku"],
            ),
            Evidence(
                tier="personal",
                source="personal-path",
                path="/tmp/prompt.md",
                excerpt="Codex memory and Chronicle history were useful in a previous setup audit.",
                matched_terms=["chronicle"],
                personal_context_used=True,
            ),
            Evidence(
                tier="personal",
                source="personal-path",
                path="/tmp/amazon-note.md",
                excerpt="Amazon and ASIN notes mention markdown files, code paths, and project setup.",
                matched_terms=["amazon", "asin"],
                personal_context_used=True,
            ),
        ]

        suggestions = build_suggestions(
            context_text="Create an Excel workbook from Amazon advertising data with monthly spend by ASIN and SKU.",
            skills=skills,
            evidence=evidence,
            config={"proactivity_level": "balanced"},
            state={},
            project_key="/tmp/project",
        )

        self.assertEqual([suggestion.skill_name for suggestion in suggestions], ["xlsx"])
        self.assertFalse(suggestions[0].personal_context_used)

    def test_project_context_does_not_seed_checkpoint_candidates(self) -> None:
        skills = [
            {
                "name": "hyperframes-registry",
                "source": "test",
                "path": "/tmp/hyperframes-registry/SKILL.md",
                "description": "Find frontend component registry entries",
                "triggers": [],
                "keywords": ["frontend", "component", "registry"],
                "domains": ["frontend"],
            }
        ]
        evidence = [
            Evidence(
                tier="session",
                source="provided-context",
                path="session",
                excerpt="Verify installed runtime SkillForge advisor after syncing canonical repo.",
                matched_terms=["verify", "installed", "runtime", "advisor"],
            ),
            Evidence(
                tier="project",
                source="project-file",
                path="/tmp/project/CONTEXT.md",
                excerpt="The Advisory Queue preserves component scores for later review.",
                matched_terms=["advisor"],
            ),
        ]

        suggestions = build_suggestions(
            context_text="Verify installed runtime SkillForge advisor after syncing canonical repo.",
            skills=skills,
            evidence=evidence,
            config={"proactivity_level": "balanced"},
            state={},
            project_key="/tmp/project",
        )

        self.assertEqual(suggestions, [])

    def test_query_terms_drop_broad_words_and_keep_sku(self) -> None:
        terms = query_terms("Create an Excel workbook from Amazon advertising data with monthly spend by ASIN and SKU.")

        self.assertIn("excel", terms)
        self.assertIn("sku", terms)
        self.assertNotIn("create", terms)
        self.assertNotIn("data", terms)
        self.assertNotIn("summary", terms)

    def test_source_term_matching_uses_whole_tokens(self) -> None:
        self.assertEqual(matches_terms("Excellent write-up about another topic.", ["excel"]), [])
        self.assertEqual(matches_terms("Build an Excel workbook.", ["excel"]), ["excel"])

    def test_project_evidence_reads_narrow_candidate_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skillforge-advisor-") as tmp:
            root = Path(tmp)
            (root / "README.md").write_text(
                "# Demo\n\nThis repository needs code review workflow support.\n",
                encoding="utf-8",
            )

            evidence = collect_project_evidence(root, ["code", "review"], excludes=[])

        self.assertTrue(evidence)
        self.assertEqual(evidence[0].tier, "project")
        self.assertIn("README.md", evidence[0].path)

    def test_project_evidence_skips_unmatched_candidate_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skillforge-advisor-") as tmp:
            root = Path(tmp)
            (root / "README.md").write_text(
                "# Demo\n\nThis repository documents unrelated frontend components.\n",
                encoding="utf-8",
            )

            evidence = collect_project_evidence(root, ["amazon", "advertising"], excludes=[])

        self.assertEqual(evidence, [])


if __name__ == "__main__":
    unittest.main()
