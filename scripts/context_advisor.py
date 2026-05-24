#!/usr/bin/env python3
"""
context_advisor.py - Proactive SkillForge advisor.

Commands:
    python context_advisor.py checkpoint --text "current task"
    python context_advisor.py run --cwd /path/to/project
    python context_advisor.py list
    python context_advisor.py dismiss <suggestion-id>

Exit Codes:
    0 - Success
    1 - Advisor failed
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    from advisor_scoring import Suggestion, build_suggestions
    from context_sources import collect_context_evidence
    from discover_skills import discover_skills, get_index_path, save_index
    from skillforge_config import data_dir, level_settings, load_config, project_key
    from triage_skill_request import load_skill_index
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from advisor_scoring import Suggestion, build_suggestions
    from context_sources import collect_context_evidence
    from discover_skills import discover_skills, get_index_path, save_index
    from skillforge_config import data_dir, level_settings, load_config, project_key
    from triage_skill_request import load_skill_index


QUEUE_FILE = data_dir() / "advice.jsonl"
STATE_FILE = data_dir() / "advisor_state.json"


@dataclass
class AdvisorResult:
    success: bool
    message: str
    suggestions: list[dict[str, Any]]
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return fallback


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_state() -> dict[str, Any]:
    state = read_json(
        STATE_FILE,
        {
            "accepted": {},
            "dismissed": {},
            "snoozed": {},
            "never_projects": {},
        },
    )
    if not isinstance(state, dict):
        return {"accepted": {}, "dismissed": {}, "snoozed": {}, "never_projects": {}}
    state.setdefault("accepted", {})
    state.setdefault("dismissed", {})
    state.setdefault("snoozed", {})
    state.setdefault("never_projects", {})
    return state


def save_state(state: dict[str, Any]) -> None:
    write_json(STATE_FILE, state)


def parse_until(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def read_queue() -> list[dict[str, Any]]:
    if not QUEUE_FILE.exists():
        return []
    items: list[dict[str, Any]] = []
    for line in QUEUE_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            items.append(item)
    return items


def write_queue(items: list[dict[str, Any]]) -> None:
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(item, sort_keys=True) for item in items]
    QUEUE_FILE.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def append_queue(suggestions: list[Suggestion]) -> list[dict[str, Any]]:
    existing = read_queue()
    pending_fingerprints = {
        item.get("fingerprint")
        for item in existing
        if item.get("status", "pending") == "pending"
    }
    now = utc_now().isoformat()
    added: list[dict[str, Any]] = []
    for suggestion in suggestions:
        if suggestion.fingerprint in pending_fingerprints:
            continue
        item = suggestion.to_dict()
        item["created_at"] = now
        item["status"] = "pending"
        existing.append(item)
        added.append(item)
    write_queue(existing)
    return added


def update_queue_item(suggestion_id: str, status: str) -> dict[str, Any] | None:
    items = read_queue()
    found: dict[str, Any] | None = None
    for item in items:
        if item.get("id") == suggestion_id:
            item["status"] = status
            item["updated_at"] = utc_now().isoformat()
            found = item
            break
    write_queue(items)
    return found


def is_suppressed(suggestion: Suggestion, state: dict[str, Any]) -> bool:
    now = utc_now()
    fingerprint = suggestion.fingerprint

    for bucket_name in ("dismissed", "snoozed"):
        bucket = state.get(bucket_name, {})
        until = parse_until(bucket.get(fingerprint)) if isinstance(bucket, dict) else None
        if until and until > now:
            return True

    never_projects = state.get("never_projects", {})
    project_rules = never_projects.get(suggestion.project_key, []) if isinstance(never_projects, dict) else []
    target = suggestion.skill_name or suggestion.action
    return target in project_rules


def ensure_skill_index() -> dict[str, Any]:
    index = load_skill_index()
    if index:
        return index
    result = discover_skills(verbose=False)
    save_index(result, get_index_path())
    index = load_skill_index()
    return index or {"skills": []}


def read_context_text(args: argparse.Namespace) -> str:
    parts: list[str] = []
    if getattr(args, "text", None):
        parts.append(args.text)
    if getattr(args, "context_file", None):
        try:
            parts.append(Path(args.context_file).expanduser().read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            pass
    return "\n".join(part for part in parts if part).strip()


def run_advisor(args: argparse.Namespace, queue: bool) -> AdvisorResult:
    cwd = Path(getattr(args, "cwd", None) or Path.cwd()).expanduser().resolve()
    loaded = load_config(cwd)
    config = loaded.config
    level = config.get("proactivity_level", "balanced")
    if level == "off":
        return AdvisorResult(True, "Proactivity Level is off.", [], [])

    index = ensure_skill_index()
    skills = index.get("skills", [])
    if not skills:
        return AdvisorResult(False, "No skills found in the SkillForge index.", [], ["empty skill index"])

    context_text = read_context_text(args)
    evidence = collect_context_evidence(config, cwd, context_text)
    state = load_state()
    suggestions = build_suggestions(
        context_text=context_text,
        skills=skills,
        evidence=evidence,
        config=config,
        state=state,
        project_key=project_key(cwd),
        limit=level_settings(level)["max_session"],
    )
    suggestions = [suggestion for suggestion in suggestions if not is_suppressed(suggestion, state)]

    if queue:
        queued = append_queue(suggestions)
        return AdvisorResult(True, f"Queued {len(queued)} suggestion(s).", queued, [])
    return AdvisorResult(True, f"Found {len(suggestions)} suggestion(s).", [s.to_dict() for s in suggestions], [])


def list_suggestions(args: argparse.Namespace) -> AdvisorResult:
    status = getattr(args, "status", "pending")
    items = read_queue()
    if status != "all":
        items = [item for item in items if item.get("status", "pending") == status]
    return AdvisorResult(True, f"Found {len(items)} queued suggestion(s).", items, [])


def apply_feedback(args: argparse.Namespace, action: str) -> AdvisorResult:
    item = update_queue_item(args.suggestion_id, action)
    if not item:
        return AdvisorResult(False, f"Suggestion not found: {args.suggestion_id}", [], ["not found"])

    state = load_state()
    fingerprint = item.get("fingerprint")
    skill_name = item.get("skill_name")

    if action == "accepted" and skill_name:
        accepted = state.setdefault("accepted", {})
        accepted[skill_name] = int(accepted.get(skill_name, 0)) + 1
    elif action == "dismissed" and fingerprint:
        until = utc_now() + timedelta(days=7)
        state.setdefault("dismissed", {})[fingerprint] = until.isoformat()
    elif action == "snoozed" and fingerprint:
        hours = int(getattr(args, "hours", 24))
        until = utc_now() + timedelta(hours=hours)
        state.setdefault("snoozed", {})[fingerprint] = until.isoformat()
    elif action == "project_suppressed":
        project = item.get("project_key")
        target = skill_name or item.get("action")
        if project and target:
            rules = state.setdefault("never_projects", {}).setdefault(project, [])
            if target not in rules:
                rules.append(target)

    save_state(state)
    return AdvisorResult(True, f"Recorded feedback: {action}", [item], [])


def format_human(result: AdvisorResult) -> str:
    lines = [result.message]
    for item in result.suggestions:
        skill = item.get("skill_name") or "new skill"
        confidence = item.get("confidence", "unknown")
        lines.append("")
        lines.append(f"[{item.get('id')}] {skill} ({confidence}, {item.get('final_score')}%)")
        lines.append(f"  Action: {item.get('action')}")
        lines.append(f"  Why now: {item.get('why_now')}")
        evidence = item.get("evidence", [])
        for source in evidence[:3]:
            path = source.get("path", "")
            tier = source.get("tier", "")
            lines.append(f"  Evidence: {tier} {path}")
        if item.get("personal_context_used"):
            lines.append("  Personal Context contributed.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the proactive SkillForge Context Skill Advisor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_context_args(command: argparse.ArgumentParser) -> None:
        command.add_argument("--text", help="Current session or checkpoint text")
        command.add_argument("--context-file", type=Path, help="File containing current context text")
        command.add_argument("--cwd", type=Path, help="Project/workspace directory")
        command.add_argument("--json", action="store_true", help="Print JSON")

    checkpoint = sub.add_parser("checkpoint", help="Return inline checkpoint suggestions")
    add_context_args(checkpoint)

    run = sub.add_parser("run", help="Run scheduled advisor and write to the Advisory Queue")
    add_context_args(run)

    list_cmd = sub.add_parser("list", help="List queued suggestions")
    list_cmd.add_argument("--status", choices=["pending", "accepted", "dismissed", "snoozed", "project_suppressed", "all"], default="pending")
    list_cmd.add_argument("--json", action="store_true", help="Print JSON")

    use = sub.add_parser("use", help="Mark a suggestion as accepted")
    use.add_argument("suggestion_id")
    use.add_argument("--json", action="store_true")

    dismiss = sub.add_parser("dismiss", help="Dismiss a suggestion for 7 days")
    dismiss.add_argument("suggestion_id")
    dismiss.add_argument("--json", action="store_true")

    snooze = sub.add_parser("snooze", help="Snooze a suggestion")
    snooze.add_argument("suggestion_id")
    snooze.add_argument("--hours", type=int, default=24)
    snooze.add_argument("--json", action="store_true")

    never = sub.add_parser("never-project", help="Suppress this skill/action for the project")
    never.add_argument("suggestion_id")
    never.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.command == "checkpoint":
        result = run_advisor(args, queue=False)
    elif args.command == "run":
        result = run_advisor(args, queue=True)
    elif args.command == "list":
        result = list_suggestions(args)
    elif args.command == "use":
        result = apply_feedback(args, "accepted")
    elif args.command == "dismiss":
        result = apply_feedback(args, "dismissed")
    elif args.command == "snooze":
        result = apply_feedback(args, "snoozed")
    elif args.command == "never-project":
        result = apply_feedback(args, "project_suppressed")
    else:
        result = AdvisorResult(False, "Unknown command", [], ["unknown command"])

    if getattr(args, "json", False):
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(format_human(result))

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
