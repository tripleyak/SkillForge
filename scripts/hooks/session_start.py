#!/usr/bin/env python3
"""
session_start.py - Claude Code SessionStart hook for the SkillForge advisor.

Reads the hook payload as JSON on stdin (session_id, cwd, source, ...),
surfaces pending Advisory Queue suggestions as additionalContext via stdout,
and stays completely silent (exit 0, no output) when there is nothing to
show. Payload values are never interpolated into shell strings; this hook
runs no subprocesses.

Exit code is always 0: a hook must never break a session.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from context_advisor import is_item_suppressed, load_state, read_queue  # noqa: E402
from skillforge_config import level_settings, load_config, project_key  # noqa: E402


# Queue items older than this never resurface; the queue is advice, not a backlog.
SUGGESTION_TTL_DAYS = 14


def read_payload() -> dict[str, Any]:
    """Read the hook JSON payload from stdin, tolerating anything malformed."""
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def is_expired(item: dict[str, Any], now: datetime) -> bool:
    created = parse_timestamp(item.get("created_at"))
    if created is None:
        return True
    return created < now - timedelta(days=SUGGESTION_TTL_DAYS)


def surfaceable_items(items: list[dict[str, Any]], state: dict[str, Any], now: datetime) -> list[dict[str, Any]]:
    """Pending (or snooze-expired) suggestions that are unexpired and unsuppressed."""
    selected: list[dict[str, Any]] = []
    for item in items:
        status = item.get("status", "pending")
        if status not in {"pending", "snoozed"}:
            continue
        if is_expired(item, now):
            continue
        if is_item_suppressed(item, state):
            continue
        selected.append(item)
    return selected


def format_block(items: list[dict[str, Any]]) -> str:
    advisor_cli = SCRIPTS_DIR / "context_advisor.py"
    lines = [
        f"SkillForge Context Skill Advisor - {len(items)} pending suggestion(s). "
        "Suggestions are advice only: never invoke a suggested skill without user confirmation.",
    ]
    for item in items:
        skill = item.get("skill_name") or "create a new skill"
        confidence = item.get("confidence", "unknown")
        lines.append("")
        lines.append(f"- [{item.get('id')}] {item.get('action')}: {skill} ({confidence} confidence)")
        why_now = str(item.get("why_now") or "").strip()
        if why_now:
            lines.append(f"  Why now: {why_now[:200]}")
        for source in (item.get("evidence") or [])[:2]:
            if isinstance(source, dict):
                lines.append(f"  Evidence: {source.get('tier', '')} {source.get('path', '')}".rstrip())
    lines.append("")
    lines.append("To act on a suggestion:")
    lines.append(f"  python3 {advisor_cli} use|snooze|dismiss <id>")
    return "\n".join(lines)


def main() -> int:
    payload = read_payload()
    cwd_raw = payload.get("cwd")
    cwd = Path(cwd_raw) if isinstance(cwd_raw, str) and cwd_raw else Path.cwd()

    config = load_config(cwd).config
    level = config.get("proactivity_level", "balanced")
    settings = level_settings(level)
    if settings["max_session"] <= 0:
        return 0

    now = datetime.now(timezone.utc)
    items = surfaceable_items(read_queue(), load_state(), now)

    # Never surface suggestions suppressed for this project.
    this_project = project_key(cwd)
    items = [item for item in items if item.get("project_key") in (None, "", this_project)]
    items = items[: settings["max_session"]]

    if items:
        print(format_block(items))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:  # noqa: BLE001 - a hook must never break a session
        print(f"skillforge session_start hook error: {error}", file=sys.stderr)
        sys.exit(0)
