#!/usr/bin/env python3
"""
check_docs_safety.py - Guard against unsafe hook command examples in docs.

Flags markdown lines where $TOOL_INPUT or $TOOL_OUTPUT appear in command
strings without explicit quoting.

Usage:
    python scripts/check_docs_safety.py
    python scripts/check_docs_safety.py SKILL.md references/script-integration-framework.md

Exit codes:
    0 - no unsafe patterns found
    1 - unsafe patterns found
    2 - bad input / file read error
"""

from __future__ import annotations

import sys
from pathlib import Path


def default_targets(repo_root: Path) -> list[Path]:
    return [
        repo_root / "SKILL.md",
        repo_root / "references" / "script-integration-framework.md",
        repo_root / "references" / "synthesis-protocol.md",
    ]


def is_unquoted_tool_var(line: str, var: str) -> bool:
    token_a = f"${var}"
    token_b = f"${{{var}}}"
    if token_a not in line and token_b not in line:
        return False

    safe_forms = (
        f"\"${var}\"",
        f"\"${{{var}}}\"",
    )
    return not any(safe in line for safe in safe_forms)


def scan_file(path: Path) -> list[str]:
    issues: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception as exc:
        raise RuntimeError(f"Cannot read {path}: {exc}") from exc

    for idx, line in enumerate(lines, start=1):
        if "command:" not in line:
            continue
        if is_unquoted_tool_var(line, "TOOL_INPUT") or is_unquoted_tool_var(line, "TOOL_OUTPUT"):
            issues.append(f"{path}:{idx}: {line.strip()}")
    return issues


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    targets = [Path(arg).resolve() for arg in sys.argv[1:]] if len(sys.argv) > 1 else default_targets(repo_root)

    all_issues: list[str] = []
    try:
        for target in targets:
            all_issues.extend(scan_file(target))
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if all_issues:
        print("Unsafe command interpolation found:")
        for issue in all_issues:
            print(f"  - {issue}")
        return 1

    print("No unsafe command interpolation patterns found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
