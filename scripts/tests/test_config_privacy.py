#!/usr/bin/env python3
"""
Regression tests for SkillForge privacy defaults and consent gating.

Personal Context (personal paths + GitHub metadata) must be opt-in:
disabled by default, empty paths, empty owner list, and never scanned
without a recorded consent flag.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import context_sources  # noqa: E402
from context_sources import (  # noqa: E402
    SECRET_REDACTION,
    collect_context_evidence,
    collect_github_metadata,
    collect_personal_evidence,
    read_excerpt,
    redact_secrets,
)
from skillforge_config import (  # noqa: E402
    DEFAULT_CONFIG,
    deep_merge,
    personal_context_allowed,
)


def consented_personal_config(paths: list[str], github_owners: list[str] | None = None) -> dict:
    return deep_merge(
        DEFAULT_CONFIG,
        {
            "context_sources": {
                "personal": {
                    "enabled": True,
                    "consented": True,
                    "consented_at": "2026-07-29T00:00:00+00:00",
                    "paths": paths,
                    "github": {
                        "enabled": bool(github_owners),
                        "owner_limit": github_owners or [],
                    },
                }
            }
        },
    )


class PrivacyDefaultsTest(unittest.TestCase):
    def test_default_config_has_no_personal_paths_or_owner_handles(self) -> None:
        personal = DEFAULT_CONFIG["context_sources"]["personal"]

        self.assertFalse(personal["enabled"])
        self.assertFalse(personal["consented"])
        self.assertEqual(personal["paths"], [])
        self.assertFalse(personal["github"]["enabled"])
        self.assertEqual(personal["github"]["owner_limit"], [])

    def test_default_config_keeps_session_and_project_tiers_enabled(self) -> None:
        sources = DEFAULT_CONFIG["context_sources"]

        self.assertTrue(sources["session"]["enabled"])
        self.assertTrue(sources["project"]["enabled"])

    def test_personal_context_allowed_requires_enabled_and_consented(self) -> None:
        self.assertFalse(personal_context_allowed(DEFAULT_CONFIG))
        enabled_only = deep_merge(
            DEFAULT_CONFIG, {"context_sources": {"personal": {"enabled": True}}}
        )
        self.assertFalse(personal_context_allowed(enabled_only))
        consent_string = deep_merge(
            DEFAULT_CONFIG,
            {"context_sources": {"personal": {"enabled": True, "consented": "yes"}}},
        )
        self.assertFalse(personal_context_allowed(consent_string))
        self.assertTrue(personal_context_allowed(consented_personal_config(["~/kb"])))


class ConsentGatingTest(unittest.TestCase):
    def test_personal_scan_refused_without_consent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skillforge-personal-") as tmp:
            root = Path(tmp)
            (root / "notes.md").write_text("code review checklist notes\n", encoding="utf-8")
            config = deep_merge(
                DEFAULT_CONFIG,
                {"context_sources": {"personal": {"enabled": True, "paths": [str(root)]}}},
            )

            with patch.object(context_sources, "rg_search") as rg:
                evidence = collect_personal_evidence(config, ["review"], excludes=[])

        self.assertEqual(evidence, [])
        rg.assert_not_called()

    def test_personal_scan_allowed_with_recorded_consent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skillforge-personal-") as tmp:
            root = Path(tmp)
            note = root / "notes.md"
            note.write_text("code review checklist notes\n", encoding="utf-8")
            config = consented_personal_config([str(root)])

            with patch.object(
                context_sources, "rg_search", return_value=[(note, "code review checklist notes", ["review"])]
            ):
                evidence = collect_personal_evidence(config, ["review"], excludes=[])

        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].tier, "personal")
        self.assertTrue(evidence[0].personal_context_used)

    def test_github_metadata_refused_without_consent(self) -> None:
        config = deep_merge(
            DEFAULT_CONFIG,
            {
                "context_sources": {
                    "personal": {
                        "enabled": True,
                        "github": {"enabled": True, "owner_limit": ["someone"]},
                    }
                }
            },
        )

        with patch.object(context_sources.subprocess, "run") as run:
            evidence = collect_github_metadata(config, ["review"])

        self.assertEqual(evidence, [])
        run.assert_not_called()

    def test_collect_context_evidence_skips_personal_tier_without_consent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skillforge-project-") as tmp:
            config = deep_merge(
                DEFAULT_CONFIG,
                {"context_sources": {"personal": {"enabled": True, "paths": [tmp]}}},
            )
            with patch.object(context_sources, "collect_personal_evidence") as personal, patch.object(
                context_sources, "collect_github_metadata"
            ) as github:
                collect_context_evidence(config, Path(tmp), "code review work")

        personal.assert_not_called()
        github.assert_not_called()


class SecretRedactionTest(unittest.TestCase):
    def test_redacts_common_credential_assignment_lines(self) -> None:
        text = "\n".join(
            [
                "normal line about deployment",
                "password = hunter2",
                "API_KEY: sk-abc123",
                "api-key=sk-abc123",
                "token: ghp_abcdef",
                "CLIENT_SECRET=shhh",
                "another normal line",
            ]
        )

        redacted = redact_secrets(text)

        self.assertIn("normal line about deployment", redacted)
        self.assertIn("another normal line", redacted)
        self.assertNotIn("hunter2", redacted)
        self.assertNotIn("sk-abc123", redacted)
        self.assertNotIn("ghp_abcdef", redacted)
        self.assertNotIn("shhh", redacted)
        self.assertEqual(redacted.count(SECRET_REDACTION), 5)

    def test_keeps_prose_that_merely_mentions_secrets(self) -> None:
        text = "Rotate the API key monthly and never commit a password to git."

        self.assertEqual(redact_secrets(text), text)

    def test_read_excerpt_redacts_before_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skillforge-redact-") as tmp:
            path = Path(tmp) / "settings.md"
            path.write_text(
                "deployment notes for review\napi_key = sk-live-999\nmore notes\n",
                encoding="utf-8",
            )

            excerpt = read_excerpt(path, ["review"])

        self.assertIn("deployment notes for review", excerpt)
        self.assertNotIn("sk-live-999", excerpt)


if __name__ == "__main__":
    unittest.main()
