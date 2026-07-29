#!/usr/bin/env python3
"""
frontmatter.py - Shared YAML frontmatter parsing for SkillForge scripts.

Single source of truth for reading SKILL.md frontmatter. Used by
validate_skill.py, quick_validate.py, and discover_skills.py so that every
tool sees the exact same parsed values.

Uses PyYAML when available. When PyYAML is not installed, falls back to a
vendored minimal YAML parser that supports the subset of YAML used by skill
frontmatter:

- string scalars (quoted and unquoted; quotes are stripped)
- booleans (true/false), integers, floats, null
- nested mappings (indentation based)
- block lists (`- item`), including mappings inside list items
- inline lists (`[a, b]`)
- folded (`>`) and literal (`|`) block scalars

Values come back typed: `user-invocable: true` parses to bool True, not the
string "true".
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, List, Optional, Tuple

try:
    import yaml  # type: ignore

    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

# Handles both LF and CRLF line endings.
FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---(?:\r?\n|$)", re.DOTALL)


# ===========================================================================
# PUBLIC API
# ===========================================================================

def split_frontmatter(text: str) -> Tuple[Optional[str], str]:
    """Split a markdown document into (frontmatter_text, body).

    frontmatter_text is None when the document has no frontmatter block.
    """
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None, text
    return match.group(1), text[match.end():]


def parse_frontmatter(text: str) -> Tuple[dict, Optional[str]]:
    """Parse YAML frontmatter from a full markdown document.

    Returns (frontmatter_dict, error). error is None on success; on failure
    the dict is empty and error describes the problem.
    """
    fm_text, _body = split_frontmatter(text)
    if fm_text is None:
        return {}, "Missing YAML frontmatter"
    return parse_yaml_mapping(fm_text)


def read_skill_frontmatter(path) -> Tuple[dict, Optional[str]]:
    """Read and parse the frontmatter of a SKILL.md file.

    Accepts either the path to the file itself or a skill directory
    containing SKILL.md.
    """
    path = Path(path)
    if path.is_dir():
        candidate = None
        try:
            for child in path.iterdir():
                if child.is_file() and child.name.lower() == "skill.md":
                    candidate = child
                    break
        except OSError as exc:
            return {}, f"Cannot read {path}: {exc}"
        if candidate is None:
            return {}, f"SKILL.md not found in {path}"
        path = candidate
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {}, f"Cannot read {path}: {exc}"
    return parse_frontmatter(text)


def parse_yaml_mapping(yaml_text: str) -> Tuple[dict, Optional[str]]:
    """Parse a YAML mapping (already extracted frontmatter text).

    Returns (dict, error). An empty document parses to ({}, None).
    """
    if _HAS_YAML:
        try:
            parsed = yaml.safe_load(yaml_text)
        except yaml.YAMLError as exc:
            return {}, f"Invalid YAML in frontmatter: {exc}"
    else:
        try:
            parsed = _vendored_parse(yaml_text)
        except _YamlError as exc:
            return {}, f"Invalid YAML in frontmatter: {exc}"

    if parsed is None:
        return {}, None
    if not isinstance(parsed, dict):
        return {}, f"Frontmatter must be a YAML mapping, got {type(parsed).__name__}"
    return parsed, None


# ===========================================================================
# VENDORED MINIMAL YAML PARSER (used when PyYAML is unavailable)
# ===========================================================================

class _YamlError(ValueError):
    """Raised by the vendored parser on malformed input."""


_BOOL_TRUE = {"true", "True", "TRUE"}
_BOOL_FALSE = {"false", "False", "FALSE"}
_NULL = {"null", "Null", "NULL", "~"}

_BLOCK_SCALAR_INDICATORS = {">", ">-", ">+", "|", "|-", "|+"}

# A mapping entry looks like `key:` or `key: value` where the colon is
# followed by whitespace or end of line (so `https://x` is not a key).
_MAPPING_KEY_RE = re.compile(r"^(\"[^\"]*\"|'[^']*'|[^:\s][^:]*?)\s*:(\s+|$)")


def _vendored_parse(text: str) -> Any:
    """Parse a YAML mapping document with the vendored minimal parser."""
    lines = text.replace("\r\n", "\n").split("\n")
    parser = _MiniYamlParser(lines)
    i = parser.skip_blank(0)
    if i >= len(lines):
        return None
    indent, _content = parser.info(i)
    value, next_i = parser.parse_block(i, indent)
    next_i = parser.skip_blank(next_i)
    if next_i < len(lines):
        _, leftover = parser.info(next_i)
        raise _YamlError(f"unexpected content at line {next_i + 1}: {leftover!r}")
    return value


def _strip_inline_comment(content: str) -> str:
    """Strip a ` # comment` suffix outside of quotes (PyYAML-compatible)."""
    quote = None
    for idx, ch in enumerate(content):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "#" and idx > 0 and content[idx - 1] in " \t":
            return content[:idx].rstrip()
    return content


def _unquote(token: str) -> str:
    if token.startswith('"'):
        return token[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return token[1:-1].replace("''", "'")


def _parse_scalar(token: str) -> Any:
    """Parse a scalar token into a typed Python value."""
    token = token.strip()
    if not token:
        return None
    if len(token) >= 2 and token[0] == token[-1] and token[0] in "'\"":
        return _unquote(token)
    if token.startswith("[") and token.endswith("]"):
        return _parse_inline_list(token)
    if token in _BOOL_TRUE:
        return True
    if token in _BOOL_FALSE:
        return False
    if token in _NULL:
        return None
    try:
        return int(token)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        pass
    return token


def _parse_inline_list(token: str) -> List[Any]:
    """Parse an inline list like [a, "b, c", 3, true]."""
    inner = token[1:-1].strip()
    if not inner:
        return []
    items: List[Any] = []
    buf: List[str] = []
    depth = 0
    quote = None
    for ch in inner:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
            buf.append(ch)
        elif ch == "[":
            depth += 1
            buf.append(ch)
        elif ch == "]":
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth == 0:
            items.append(_parse_scalar("".join(buf)))
            buf = []
        else:
            buf.append(ch)
    last = "".join(buf).strip()
    if last or not items:
        items.append(_parse_scalar(last))
    return items


class _MiniYamlParser:
    """Indentation-based recursive-descent parser for the YAML subset."""

    def __init__(self, lines: List[str]):
        self.lines = lines
        self.n = len(lines)

    # ---- line inspection -------------------------------------------------

    def is_blank(self, i: int) -> bool:
        stripped = self.lines[i].strip()
        return not stripped or stripped.startswith("#")

    def skip_blank(self, i: int) -> int:
        while i < self.n and self.is_blank(i):
            i += 1
        return i

    def info(self, i: int) -> Tuple[int, str]:
        """Return (indent, content) for a non-blank line."""
        raw = self.lines[i]
        leading = raw[: len(raw) - len(raw.lstrip())]
        if "\t" in leading:
            raise _YamlError(f"tab used for indentation at line {i + 1}")
        indent = len(leading)
        return indent, _strip_inline_comment(raw.strip())

    # ---- block dispatch ---------------------------------------------------

    def parse_block(self, i: int, indent: int) -> Tuple[Any, int]:
        """Parse the block (mapping or sequence) starting at line i."""
        _line_indent, content = self.info(i)
        if content == "-" or content.startswith("- "):
            return self.parse_sequence(i, indent)
        return self.parse_mapping(i, indent)

    # ---- mappings ----------------------------------------------------------

    def parse_mapping(self, i: int, indent: int) -> Tuple[dict, int]:
        result: dict = {}
        while i < self.n:
            if self.is_blank(i):
                i += 1
                continue
            line_indent, content = self.info(i)
            if line_indent < indent:
                break
            if line_indent > indent:
                raise _YamlError(
                    f"unexpected indentation at line {i + 1}: {content!r}"
                )
            if content == "-" or content.startswith("- "):
                # A sequence at mapping indent belongs to the previous key
                # and is handled inside parse_entry; reaching here means a
                # stray list item.
                break
            key, value, i = self.parse_entry(i, indent, content)
            if key in result:
                raise _YamlError(f"duplicate key {key!r} at line {i}")
            result[key] = value
        return result, i

    def parse_entry(self, i: int, indent: int, content: str) -> Tuple[str, Any, int]:
        """Parse one `key: ...` entry whose text is `content` at line i."""
        if not _MAPPING_KEY_RE.match(content) and not content.endswith(":"):
            raise _YamlError(f"expected 'key: value' at line {i + 1}: {content!r}")
        key_part, _, rest = content.partition(":")
        key = key_part.strip()
        if len(key) >= 2 and key[0] == key[-1] and key[0] in "'\"":
            key = _unquote(key)
        if not key:
            raise _YamlError(f"empty mapping key at line {i + 1}")
        rest = rest.strip()

        # Block scalars: key: > / key: |
        if rest in _BLOCK_SCALAR_INDICATORS:
            value, next_i = self.read_block_scalar(i + 1, indent, rest)
            return key, value, next_i

        # Empty value: nested mapping, block list, or null.
        if rest == "":
            j = self.skip_blank(i + 1)
            if j < self.n:
                child_indent, child_content = self.info(j)
                if child_indent > indent:
                    value, next_i = self.parse_block(j, child_indent)
                    return key, value, next_i
                if child_indent == indent and (
                    child_content == "-" or child_content.startswith("- ")
                ):
                    # Sequence items aligned with the parent key (valid YAML).
                    value, next_i = self.parse_sequence(j, child_indent)
                    return key, value, next_i
            return key, None, i + 1

        # Plain scalar, possibly continued on deeper-indented lines
        # (multi-line plain scalar folding).
        value = _parse_scalar(rest)
        next_i = i + 1
        if isinstance(value, str):
            parts = [value]
            while next_i < self.n:
                if self.is_blank(next_i):
                    break
                cont_indent, cont_content = self.info(next_i)
                if cont_indent <= indent:
                    break
                if _MAPPING_KEY_RE.match(cont_content) or cont_content.startswith("- "):
                    raise _YamlError(
                        f"unexpected nested block under scalar value at line {next_i + 1}"
                    )
                parts.append(cont_content)
                next_i += 1
            if len(parts) > 1:
                value = " ".join(parts)
        return key, value, next_i

    # ---- sequences ---------------------------------------------------------

    def parse_sequence(self, i: int, indent: int) -> Tuple[List[Any], int]:
        result: List[Any] = []
        while i < self.n:
            if self.is_blank(i):
                i += 1
                continue
            line_indent, content = self.info(i)
            if line_indent < indent:
                break
            if line_indent > indent:
                raise _YamlError(
                    f"unexpected indentation at line {i + 1}: {content!r}"
                )
            if content != "-" and not content.startswith("- "):
                break
            item_text = content[1:].strip()
            if not item_text:
                # Bare '-' with a nested block underneath.
                j = self.skip_blank(i + 1)
                if j < self.n:
                    child_indent, _child = self.info(j)
                    if child_indent > indent:
                        value, i = self.parse_block(j, child_indent)
                        result.append(value)
                        continue
                result.append(None)
                i += 1
                continue
            offset = content.index(item_text)
            item_indent = line_indent + offset
            if _MAPPING_KEY_RE.match(item_text):
                # '- key: value' starts a mapping; subsequent keys align at
                # the item indent.
                key, value, i = self.parse_entry(i, item_indent, item_text)
                mapping = {key: value}
                rest_map, i = self.parse_mapping(i, item_indent)
                for extra_key, extra_value in rest_map.items():
                    if extra_key in mapping:
                        raise _YamlError(f"duplicate key {extra_key!r} in list item")
                    mapping[extra_key] = extra_value
                result.append(mapping)
            else:
                result.append(_parse_scalar(item_text))
                i += 1
        return result, i

    # ---- block scalars -----------------------------------------------------

    def read_block_scalar(self, i: int, key_indent: int, style: str) -> Tuple[str, int]:
        """Read a folded (>) or literal (|) block scalar body."""
        folded = style.startswith(">")
        raw_lines: List[str] = []
        content_indent: Optional[int] = None
        while i < self.n:
            raw = self.lines[i]
            if not raw.strip():
                raw_lines.append("")
                i += 1
                continue
            line_indent = len(raw) - len(raw.lstrip(" "))
            if line_indent <= key_indent:
                break
            if content_indent is None:
                content_indent = line_indent
            raw_lines.append(raw[content_indent:] if len(raw) >= content_indent else "")
            i += 1
        # Trim trailing blank lines (approximates clip/strip chomping).
        while raw_lines and not raw_lines[-1].strip():
            raw_lines.pop()
        if folded:
            # Fold: newlines become spaces; blank lines become newlines.
            paragraphs: List[str] = []
            current: List[str] = []
            for line in raw_lines:
                if not line.strip():
                    if current:
                        paragraphs.append(" ".join(current))
                        current = []
                else:
                    current.append(line.strip())
            if current:
                paragraphs.append(" ".join(current))
            return "\n".join(paragraphs), i
        return "\n".join(raw_lines), i
