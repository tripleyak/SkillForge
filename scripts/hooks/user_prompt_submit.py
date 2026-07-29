#!/usr/bin/env python3
"""
user_prompt_submit.py - Claude Code UserPromptSubmit hook for the SkillForge advisor.

Reads the hook payload as JSON on stdin (prompt, cwd, session_id, ...), runs a
fast advisor checkpoint against the PREBUILT skill index, and emits at most one
short suggestion line as additionalContext via stdout. Silent (exit 0, no
output) when nothing clears the Proactivity Level threshold or a cap.

Hard constraints:
- Time budget under 2 seconds: uses the prebuilt index only (never rebuilds),
  skips Personal Context entirely, and bails silently if the budget is spent.
- Per-session and per-day caps from PROACTIVITY_SETTINGS are enforced through
  a small state file (hook_state.json).
- Payload values are never interpolated into shell strings; this hook runs no
  subprocesses.

Exit code is always 0: a hook must never break prompt processing.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from advisor_scoring import build_suggestions  # noqa: E402
from context_advisor import append_queue, is_suppressed, load_state  # noqa: E402
from context_sources import collect_context_evidence  # noqa: E402
from skillforge_config import (  # noqa: E402
    data_dir,
    deep_merge,
    level_settings,
    load_config,
    project_key,
)
from triage_skill_request import load_skill_index  # noqa: E402


# The hard budget is 2s; the soft deadline leaves headroom for scoring,
# printing, and interpreter teardown.
SOFT_DEADLINE_SECONDS = 1.5
MAX_TRACKED_SESSIONS = 64


def hook_state_path() -> Path:
    return data_dir() / "hook_state.json"


def read_payload() -> dict[str, Any]:
    """Read the hook JSON payload from stdin, tolerating anything malformed."""
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def load_hook_state(today: str) -> dict[str, Any]:
    """Load cap-tracking state, resetting the daily counter on a new day."""
    path = hook_state_path()
    state: dict[str, Any] = {}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                state = loaded
        except (json.JSONDecodeError, OSError):
            state = {}

    if state.get("day") != today:
        state = {"day": today, "daily_count": 0, "sessions": {}}
    state.setdefault("daily_count", 0)
    sessions = state.get("sessions")
    if not isinstance(sessions, dict):
        state["sessions"] = {}
    return state


def save_hook_state(state: dict[str, Any]) -> None:
    sessions = state.get("sessions", {})
    if len(sessions) > MAX_TRACKED_SESSIONS:
        state["sessions"] = dict(list(sessions.items())[-MAX_TRACKED_SESSIONS:])
    path = hook_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def caps_reached(state: dict[str, Any], session_id: str, settings: dict[str, int]) -> bool:
    if int(state.get("daily_count", 0)) >= settings["max_daily"]:
        return True
    session_count = int(state.get("sessions", {}).get(session_id, 0))
    return session_count >= settings["max_session"]


def record_emission(state: dict[str, Any], session_id: str) -> None:
    state["daily_count"] = int(state.get("daily_count", 0)) + 1
    sessions = state.setdefault("sessions", {})
    sessions[session_id] = int(sessions.get(session_id, 0)) + 1
    save_hook_state(state)


def format_line(item: dict[str, Any]) -> str:
    advisor_cli = SCRIPTS_DIR / "context_advisor.py"
    skill = item.get("skill_name")
    subject = f"the '{skill}' skill looks relevant" if skill else "this looks like a new-skill opportunity"
    why_now = str(item.get("why_now") or "").strip()[:160]
    return (
        f"SkillForge advisor: {subject} ({item.get('confidence', 'unknown')} confidence). "
        f"{why_now} Ask the user before invoking any skill. "
        f"Act: python3 {advisor_cli} use|snooze|dismiss {item.get('id')}"
    )


def main() -> int:
    started = time.monotonic()
    payload = read_payload()
    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return 0

    cwd_raw = payload.get("cwd")
    cwd = Path(cwd_raw) if isinstance(cwd_raw, str) and cwd_raw else Path.cwd()
    session_id = str(payload.get("session_id") or "unknown-session")

    config = load_config(cwd).config
    level = config.get("proactivity_level", "balanced")
    settings = level_settings(level)
    if settings["max_session"] <= 0 or settings["max_daily"] <= 0:
        return 0

    today = date.today().isoformat()
    hook_state = load_hook_state(today)
    if caps_reached(hook_state, session_id, settings):
        return 0

    # Prebuilt index only. A missing index means no suggestion, never a rebuild.
    index = load_skill_index()
    skills = (index or {}).get("skills", [])
    if not skills:
        return 0

    # Personal Context is out of budget for an inline hook regardless of consent.
    fast_config = deep_merge(
        config,
        {"context_sources": {"personal": {"enabled": False, "consented": False}}},
    )
    evidence = collect_context_evidence(fast_config, cwd, prompt)

    if time.monotonic() - started > SOFT_DEADLINE_SECONDS:
        return 0

    advisor_state = load_state()
    suggestions = build_suggestions(
        context_text=prompt,
        skills=skills,
        evidence=evidence,
        config=fast_config,
        state=advisor_state,
        project_key=project_key(cwd),
        limit=1,
    )
    suggestions = [s for s in suggestions if not is_suppressed(s, advisor_state)]
    if not suggestions:
        return 0

    queued = append_queue(suggestions[:1])
    item = queued[0] if queued else suggestions[0].to_dict()

    record_emission(hook_state, session_id)
    print(format_line(item))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:  # noqa: BLE001 - a hook must never break the prompt
        print(f"skillforge user_prompt_submit hook error: {error}", file=sys.stderr)
        sys.exit(0)
