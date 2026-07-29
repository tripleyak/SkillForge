#!/usr/bin/env python3
"""
Tests for the shared frontmatter parser (scripts/frontmatter.py).

The vendored minimal YAML parser is exercised directly (via
frontmatter._vendored_parse) so these tests hold regardless of whether
PyYAML is installed. The public API (parse_frontmatter,
read_skill_frontmatter, split_frontmatter) is tested on top.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import frontmatter  # noqa: E402
from frontmatter import (  # noqa: E402
    _vendored_parse,
    _YamlError,
    parse_frontmatter,
    read_skill_frontmatter,
    split_frontmatter,
)


class VendoredScalarTypingTest(unittest.TestCase):
    """Values must come back typed, not stringly."""

    def test_boolean_true_is_bool(self) -> None:
        parsed = _vendored_parse("user-invocable: true")
        self.assertIs(parsed["user-invocable"], True)

    def test_boolean_false_is_bool(self) -> None:
        parsed = _vendored_parse("enabled: false")
        self.assertIs(parsed["enabled"], False)

    def test_capitalized_booleans(self) -> None:
        parsed = _vendored_parse("a: True\nb: False\nc: TRUE\nd: FALSE")
        self.assertIs(parsed["a"], True)
        self.assertIs(parsed["b"], False)
        self.assertIs(parsed["c"], True)
        self.assertIs(parsed["d"], False)

    def test_quoted_true_stays_string(self) -> None:
        parsed = _vendored_parse('flag: "true"')
        self.assertEqual(parsed["flag"], "true")
        self.assertIsInstance(parsed["flag"], str)

    def test_integer(self) -> None:
        parsed = _vendored_parse("count: 42")
        self.assertEqual(parsed["count"], 42)
        self.assertIsInstance(parsed["count"], int)

    def test_negative_integer(self) -> None:
        parsed = _vendored_parse("delta: -7")
        self.assertEqual(parsed["delta"], -7)

    def test_float(self) -> None:
        parsed = _vendored_parse("ratio: 0.75")
        self.assertAlmostEqual(parsed["ratio"], 0.75)

    def test_null_values(self) -> None:
        parsed = _vendored_parse("a: null\nb: ~\nc:")
        self.assertIsNone(parsed["a"])
        self.assertIsNone(parsed["b"])
        self.assertIsNone(parsed["c"])

    def test_plain_string(self) -> None:
        parsed = _vendored_parse("name: my-skill")
        self.assertEqual(parsed["name"], "my-skill")

    def test_version_like_string_not_mangled(self) -> None:
        parsed = _vendored_parse("version: 1.2.3")
        self.assertEqual(parsed["version"], "1.2.3")


class VendoredQuotedScalarTest(unittest.TestCase):
    def test_double_quotes_stripped(self) -> None:
        parsed = _vendored_parse('description: "A quoted description"')
        self.assertEqual(parsed["description"], "A quoted description")

    def test_single_quotes_stripped(self) -> None:
        parsed = _vendored_parse("description: 'single quoted'")
        self.assertEqual(parsed["description"], "single quoted")

    def test_colon_inside_quoted_value(self) -> None:
        parsed = _vendored_parse('description: "Use when: things break"')
        self.assertEqual(parsed["description"], "Use when: things break")

    def test_escaped_double_quote(self) -> None:
        parsed = _vendored_parse('title: "say \\"hi\\""')
        self.assertEqual(parsed["title"], 'say "hi"')

    def test_doubled_single_quote(self) -> None:
        parsed = _vendored_parse("title: 'it''s fine'")
        self.assertEqual(parsed["title"], "it's fine")

    def test_hash_inside_quotes_kept(self) -> None:
        parsed = _vendored_parse('note: "keep # this"')
        self.assertEqual(parsed["note"], "keep # this")

    def test_inline_comment_stripped(self) -> None:
        parsed = _vendored_parse("name: my-skill  # a comment")
        self.assertEqual(parsed["name"], "my-skill")

    def test_full_line_comment_skipped(self) -> None:
        parsed = _vendored_parse("# leading comment\nname: my-skill")
        self.assertEqual(parsed, {"name": "my-skill"})

    def test_url_value_not_treated_as_comment(self) -> None:
        parsed = _vendored_parse("homepage: https://example.com/path")
        self.assertEqual(parsed["homepage"], "https://example.com/path")


class VendoredListTest(unittest.TestCase):
    def test_inline_list(self) -> None:
        parsed = _vendored_parse("domains: [testing, meta, ai]")
        self.assertEqual(parsed["domains"], ["testing", "meta", "ai"])

    def test_inline_list_typed_items(self) -> None:
        parsed = _vendored_parse('mixed: [1, true, "x, y", plain]')
        self.assertEqual(parsed["mixed"], [1, True, "x, y", "plain"])

    def test_empty_inline_list(self) -> None:
        parsed = _vendored_parse("items: []")
        self.assertEqual(parsed["items"], [])

    def test_block_list(self) -> None:
        parsed = _vendored_parse("allowed-tools:\n  - Read\n  - Grep\n  - Bash")
        self.assertEqual(parsed["allowed-tools"], ["Read", "Grep", "Bash"])

    def test_block_list_typed_items(self) -> None:
        parsed = _vendored_parse("values:\n  - 1\n  - true\n  - text")
        self.assertEqual(parsed["values"], [1, True, "text"])

    def test_block_list_at_key_indent(self) -> None:
        # Valid YAML: sequence items aligned with the parent key
        parsed = _vendored_parse("tools:\n- Read\n- Write")
        self.assertEqual(parsed["tools"], ["Read", "Write"])

    def test_block_list_of_mappings(self) -> None:
        text = (
            "hooks:\n"
            "  PreToolUse:\n"
            "    - matcher: Bash\n"
            "      hooks:\n"
            "        - type: command\n"
            "          command: echo hi\n"
            "          once: true\n"
        )
        parsed = _vendored_parse(text)
        matchers = parsed["hooks"]["PreToolUse"]
        self.assertEqual(len(matchers), 1)
        self.assertEqual(matchers[0]["matcher"], "Bash")
        inner = matchers[0]["hooks"][0]
        self.assertEqual(inner["type"], "command")
        self.assertEqual(inner["command"], "echo hi")
        self.assertIs(inner["once"], True)


class VendoredMappingTest(unittest.TestCase):
    def test_nested_mapping(self) -> None:
        parsed = _vendored_parse("metadata:\n  version: 1.0.0\n  author: me")
        self.assertEqual(parsed["metadata"], {"version": "1.0.0", "author": "me"})

    def test_deeply_nested_mapping(self) -> None:
        parsed = _vendored_parse("a:\n  b:\n    c: 3")
        self.assertEqual(parsed["a"]["b"]["c"], 3)

    def test_nested_mapping_with_inline_list(self) -> None:
        parsed = _vendored_parse("metadata:\n  version: 6.0.0\n  domains: [x, y]")
        self.assertEqual(parsed["metadata"]["domains"], ["x", "y"])

    def test_folded_scalar(self) -> None:
        parsed = _vendored_parse("description: >\n  line one\n  line two")
        self.assertEqual(parsed["description"], "line one line two")

    def test_folded_strip_scalar(self) -> None:
        parsed = _vendored_parse("description: >-\n  line one\n  line two")
        self.assertEqual(parsed["description"], "line one line two")

    def test_literal_scalar(self) -> None:
        parsed = _vendored_parse("script: |\n  line one\n  line two")
        self.assertEqual(parsed["script"], "line one\nline two")

    def test_multiline_plain_scalar_folds(self) -> None:
        parsed = _vendored_parse("description: starts here\n  and continues here")
        self.assertEqual(parsed["description"], "starts here and continues here")

    def test_blank_lines_ignored(self) -> None:
        parsed = _vendored_parse("a: 1\n\nb: 2\n")
        self.assertEqual(parsed, {"a": 1, "b": 2})

    def test_empty_document(self) -> None:
        self.assertIsNone(_vendored_parse(""))

    def test_duplicate_key_rejected(self) -> None:
        with self.assertRaises(_YamlError):
            _vendored_parse("a: 1\na: 2")

    def test_tab_indentation_rejected(self) -> None:
        with self.assertRaises(_YamlError):
            _vendored_parse("metadata:\n\tversion: 1.0.0")


class PublicApiTest(unittest.TestCase):
    DOC = (
        "---\n"
        "name: demo\n"
        "user-invocable: true\n"
        "allowed-tools:\n"
        "  - Read\n"
        "metadata:\n"
        "  version: 1.0.0\n"
        "---\n"
        "\n"
        "# Demo\n"
        "\n"
        "Body text.\n"
    )

    def test_parse_frontmatter_success(self) -> None:
        parsed, error = parse_frontmatter(self.DOC)
        self.assertIsNone(error)
        self.assertEqual(parsed["name"], "demo")
        self.assertIs(parsed["user-invocable"], True)
        self.assertEqual(parsed["allowed-tools"], ["Read"])
        self.assertEqual(parsed["metadata"]["version"], "1.0.0")

    def test_parse_frontmatter_missing(self) -> None:
        parsed, error = parse_frontmatter("# No frontmatter here\n")
        self.assertEqual(parsed, {})
        self.assertIsNotNone(error)

    def test_parse_frontmatter_crlf(self) -> None:
        doc = self.DOC.replace("\n", "\r\n")
        parsed, error = parse_frontmatter(doc)
        self.assertIsNone(error)
        self.assertEqual(parsed["name"], "demo")

    def test_split_frontmatter_body(self) -> None:
        fm_text, body = split_frontmatter(self.DOC)
        self.assertIn("name: demo", fm_text)
        self.assertNotIn("---", body)
        self.assertIn("# Demo", body)

    def test_split_frontmatter_absent(self) -> None:
        fm_text, body = split_frontmatter("just a body")
        self.assertIsNone(fm_text)
        self.assertEqual(body, "just a body")

    def test_read_skill_frontmatter_file_and_dir(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skillforge-test-") as tmp:
            skill_dir = Path(tmp) / "demo"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(self.DOC, encoding="utf-8")

            parsed, error = read_skill_frontmatter(skill_dir / "SKILL.md")
            self.assertIsNone(error)
            self.assertEqual(parsed["name"], "demo")

            parsed, error = read_skill_frontmatter(skill_dir)
            self.assertIsNone(error)
            self.assertEqual(parsed["name"], "demo")

    def test_read_skill_frontmatter_missing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skillforge-test-") as tmp:
            parsed, error = read_skill_frontmatter(Path(tmp))
            self.assertEqual(parsed, {})
            self.assertIsNotNone(error)

    def test_repo_skill_md_parses_with_typed_values(self) -> None:
        """Regression for audit 3.1: SkillForge's own SKILL.md must parse."""
        repo_skill = SCRIPTS_DIR.parent / "SKILL.md"
        if not repo_skill.exists():
            self.skipTest("repo SKILL.md not present")
        parsed, error = read_skill_frontmatter(repo_skill)
        self.assertIsNone(error)
        self.assertEqual(parsed.get("name"), "skillforge")
        if "user-invocable" in parsed:
            self.assertIsInstance(parsed["user-invocable"], bool)
        if "allowed-tools" in parsed:
            self.assertIsInstance(parsed["allowed-tools"], list)
            self.assertNotIn("", parsed["allowed-tools"])


class VendoredIsDefaultPathTest(unittest.TestCase):
    def test_environment_note(self) -> None:
        """Document which parser path the public API exercises here.

        On machines without PyYAML the vendored parser IS the hot path; the
        suite above pins its behavior either way by calling it directly.
        """
        self.assertIn(frontmatter._HAS_YAML, (True, False))


if __name__ == "__main__":
    unittest.main()
