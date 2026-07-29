#!/usr/bin/env python3
"""
compile_skill.py - Compile a skill for a target runtime.

Author once, compile per target. Copies the whole skill directory and
rewrites SKILL.md frontmatter for the target runtime:

  claude       Passthrough - all 17 Claude Code fields are legal as-is.
  codex        Keeps portable fields (name, description, license,
               allowed-tools, metadata); strips Claude-only fields and
               writes MIGRATION_NOTES.md explaining every removal.
  agentskills  Strict agentskills.io spec (name, description, license,
               metadata, allowed-tools) with the 64/1024-char limits
               ENFORCED - violations are compile errors.

The source skill is never mutated.

Usage:
    python3 compile_skill.py <skill-dir> --target claude --out ./dist
    python3 compile_skill.py <skill-dir> --target codex --out ./dist
    python3 compile_skill.py <skill-dir> --target agentskills --out ./dist

Exit Codes:
    0  - Compiled successfully
    1  - General failure (bad paths, unreadable skill)
    2  - Invalid arguments
    10 - Target constraint violated (agentskills 64/1024 limits)
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from _constants import DESCRIPTION_MAX_LENGTH, NAME_MAX_LENGTH
    from frontmatter import parse_yaml_mapping, split_frontmatter
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _constants import DESCRIPTION_MAX_LENGTH, NAME_MAX_LENGTH
    from frontmatter import parse_yaml_mapping, split_frontmatter

TARGETS = ("claude", "codex", "agentskills")

# Portable across every runtime (agentskills.io spec + allowed-tools, which
# codex honors as a plain tool list).
PORTABLE_FIELDS = ("name", "description", "license", "metadata", "allowed-tools")

# Why each Claude-only field cannot survive outside Claude Code.
CLAUDE_ONLY_REASONS: Dict[str, str] = {
    "hooks": "lifecycle hooks (PreToolUse/PostToolUse/Stop) are a Claude Code runtime feature",
    "context": "'context: fork' subagent execution exists only in Claude Code",
    "agent": "subagent type selection requires Claude Code's context: fork",
    "effort": "reasoning-effort hints are Claude Code specific",
    "background": "background task execution is Claude Code specific",
    "paths": "extra directory access scoping is Claude Code specific",
    "shell": "shell override for bash blocks is Claude Code specific",
    "when_to_use": "extra routing text appended to listings is Claude Code specific",
    "argument-hint": "slash-menu hints exist only in Claude Code's / menu",
    "arguments": "declared $ARGUMENTS interpolation is Claude Code specific",
    "disable-model-invocation": "auto-invocation control is Claude Code specific",
    "user-invocable": "slash-menu visibility control is Claude Code specific",
    "disallowed-tools": "tool denylists are Claude Code specific (allowlist is portable)",
    "model": "model selection while a skill is active is Claude Code specific",
}


# ===========================================================================
# CLEAN YAML RE-SERIALIZATION (subset used by skill frontmatter; stdlib only)
# ===========================================================================

def _serialize_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    # json.dumps produces a double-quoted string that is also valid YAML.
    return json.dumps(str(value), ensure_ascii=False)


def _serialize_value(value: Any, indent: int) -> List[str]:
    """Serialize a value that follows `key:` - returns full lines."""
    pad = " " * indent
    lines: List[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            lines.extend(_serialize_entry(str(key), child, indent))
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (dict, list)):
                nested = _serialize_value(item, indent + 2)
                lines.append(f"{pad}-" + (" " + nested[0].strip() if nested else ""))
                lines.extend(nested[1:])
            else:
                lines.append(f"{pad}- {_serialize_scalar(item)}")
    else:
        raise ValueError(f"scalar passed to _serialize_value: {value!r}")
    return lines


def _serialize_entry(key: str, value: Any, indent: int) -> List[str]:
    pad = " " * indent
    if isinstance(value, dict):
        if not value:
            return [f"{pad}{key}: {{}}"]
        return [f"{pad}{key}:"] + _serialize_value(value, indent + 2)
    if isinstance(value, list):
        if not value:
            return [f"{pad}{key}: []"]
        return [f"{pad}{key}:"] + _serialize_value(value, indent + 2)
    if isinstance(value, str) and "\n" in value:
        body = [f"{' ' * (indent + 2)}{line}" for line in value.split("\n")]
        return [f"{pad}{key}: |"] + body
    return [f"{pad}{key}: {_serialize_scalar(value)}"]


def serialize_frontmatter(frontmatter: Dict[str, Any]) -> str:
    """Re-serialize frontmatter cleanly. Round-trips through parse_yaml_mapping."""
    lines: List[str] = []
    for key, value in frontmatter.items():
        lines.extend(_serialize_entry(str(key), value, 0))
    return "\n".join(lines)


# ===========================================================================
# TARGET TRANSFORMS
# ===========================================================================

def ordered_keep(frontmatter: Dict[str, Any], keep: Tuple[str, ...]
                 ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Split frontmatter into (kept, stripped), preserving original key order."""
    kept: Dict[str, Any] = {}
    stripped: Dict[str, Any] = {}
    for key, value in frontmatter.items():
        (kept if key in keep else stripped)[key] = value
    return kept, stripped


def migration_notes(target: str, stripped: Dict[str, Any]) -> str:
    lines = [
        "# Migration notes",
        "",
        f"This skill was compiled for the `{target}` runtime by "
        "SkillForge's compile_skill.py.",
        "The following frontmatter fields were removed because the target "
        "runtime does not support them:",
        "",
    ]
    for key, value in stripped.items():
        reason = CLAUDE_ONLY_REASONS.get(
            key, f"'{key}' is not part of the {target} field set")
        rendered = json.dumps(value, ensure_ascii=False, default=str)
        if len(rendered) > 200:
            rendered = rendered[:200] + "..."
        lines.append(f"- `{key}` (was: {rendered})")
        lines.append(f"  - why: {reason}")
    lines.append("")
    lines.append("If the skill's body relies on any of these (for example a "
                 "hooks-driven check), port that behavior manually or drop it.")
    lines.append("")
    return "\n".join(lines)


def enforce_agentskills_limits(frontmatter: Dict[str, Any]) -> List[str]:
    """Return hard errors against the agentskills.io 64/1024 limits."""
    errors: List[str] = []
    name = str(frontmatter.get("name") or "")
    description = str(frontmatter.get("description") or "")
    if not name:
        errors.append("agentskills requires a 'name' field")
    elif len(name) > NAME_MAX_LENGTH:
        errors.append(f"name is {len(name)} chars (agentskills max {NAME_MAX_LENGTH})")
    if not description:
        errors.append("agentskills requires a 'description' field")
    elif len(description) > DESCRIPTION_MAX_LENGTH:
        errors.append(f"description is {len(description)} chars "
                      f"(agentskills max {DESCRIPTION_MAX_LENGTH})")
    return errors


# ===========================================================================
# COMPILATION
# ===========================================================================

def compile_skill(skill_dir: Path, target: str, out_dir: Path
                  ) -> Tuple[bool, str, int]:
    """Compile skill_dir for target into out_dir/<skill-name>/.

    Returns (success, message, exit_code).
    """
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return False, f"SKILL.md not found in {skill_dir}", 1
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError as exc:
        return False, f"cannot read {skill_md}: {exc}", 1

    fm_text, body = split_frontmatter(text)
    if fm_text is None:
        return False, f"{skill_md} has no YAML frontmatter", 1
    frontmatter, error = parse_yaml_mapping(fm_text)
    if error:
        return False, f"{skill_md}: {error}", 1

    dest = out_dir / skill_dir.name
    if dest.resolve() == skill_dir.resolve():
        return False, "output directory equals the source skill - refusing to overwrite", 2
    if dest.exists():
        return False, f"output already exists: {dest} (remove it first)", 1

    if target == "agentskills":
        limit_errors = enforce_agentskills_limits(frontmatter)
        if limit_errors:
            details = "; ".join(limit_errors)
            return False, f"agentskills constraint violation: {details}", 10

    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(skill_dir, dest)
    except OSError as exc:
        return False, f"copy failed: {exc}", 1

    stripped: Dict[str, Any] = {}
    if target == "claude":
        pass  # passthrough: all 17 fields are legal
    else:
        kept, stripped = ordered_keep(frontmatter, PORTABLE_FIELDS)
        new_text = f"---\n{serialize_frontmatter(kept)}\n---\n{body}"
        (dest / "SKILL.md").write_text(new_text, encoding="utf-8")
        if stripped:
            (dest / "MIGRATION_NOTES.md").write_text(
                migration_notes(target, stripped), encoding="utf-8")

    summary = f"compiled {skill_dir.name} for {target} -> {dest}"
    if stripped:
        summary += (f" (stripped {len(stripped)} field(s): "
                    f"{', '.join(stripped)}; see MIGRATION_NOTES.md)")
    return True, summary, 0


# ===========================================================================
# CLI
# ===========================================================================

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compile a skill for a target runtime (source is never mutated)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ~/.claude/skills/my-skill --target codex --out ./dist
  %(prog)s ./my-skill --target agentskills --out ./dist
        """,
    )
    parser.add_argument("skill_dir", type=Path, help="Source skill directory")
    parser.add_argument("--target", required=True, choices=TARGETS,
                        help="Target runtime")
    parser.add_argument("--out", required=True, type=Path,
                        help="Output directory (skill is written to OUT/<name>/)")
    args = parser.parse_args(argv)

    skill_dir = args.skill_dir.expanduser().resolve()
    if not skill_dir.is_dir():
        print(f"Error: not a directory: {skill_dir}", file=sys.stderr)
        return 1

    success, message, code = compile_skill(
        skill_dir, args.target, args.out.expanduser().resolve())
    print(message if success else f"Error: {message}",
          file=sys.stdout if success else sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
