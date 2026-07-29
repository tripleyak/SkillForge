#!/usr/bin/env python3
"""
install_skillforge.py - Configure the SkillForge Context Skill Advisor.

Interactive by default; every flag exists so automation can run it
non-interactively. What it does:

1. Writes the global SkillForge config (Proactivity Level).
2. OFFERS to register the two advisor hooks (SessionStart +
   UserPromptSubmit) in ~/.claude/settings.json. Registration happens only
   with explicit confirmation or --enable-hooks; the settings file is backed
   up first and existing hooks config is merged, never replaced.
3. OFFERS Personal Context scanning (strictly opt-in). Consent is recorded
   in the config with a timestamp; without it, personal paths and GitHub
   metadata are never scanned.
4. Removes any previously installed SkillForge launchd agent (the old,
   broken delivery mechanism): unloads and deletes
   ~/Library/LaunchAgents/*skillforge* when present.
5. Never touches ~/.claude/CLAUDE.md or ~/AGENTS.md unless
   --write-agent-snippet is passed.

Exit Codes:
    0 - Success
    1 - Installation failed
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from skillforge_config import (
        CONFIG_FILE,
        PROACTIVITY_SETTINGS,
        ensure_global_config,
        record_personal_context_consent,
        update_global_config,
        write_project_override,
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from skillforge_config import (
        CONFIG_FILE,
        PROACTIVITY_SETTINGS,
        ensure_global_config,
        record_personal_context_consent,
        update_global_config,
        write_project_override,
    )


SCRIPTS_DIR = Path(__file__).resolve().parent
HOOK_EVENTS = {
    "SessionStart": {"script": SCRIPTS_DIR / "hooks" / "session_start.py", "timeout": 10},
    "UserPromptSubmit": {"script": SCRIPTS_DIR / "hooks" / "user_prompt_submit.py", "timeout": 5},
}
DEFAULT_CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"
LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"


def ask_yes_no(question: str, default: bool = False) -> bool:
    suffix = " [Y/n] " if default else " [y/N] "
    try:
        answer = input(question + suffix).strip().lower()
    except EOFError:
        return default
    if not answer:
        return default
    return answer in {"y", "yes"}


def ask_list(question: str) -> list[str]:
    try:
        raw = input(question + " (comma-separated, empty for none): ").strip()
    except EOFError:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def ask_choice(question: str, choices: list[str], default: str) -> str:
    prompt = f"{question} ({'/'.join(choices)}) [{default}]: "
    try:
        answer = input(prompt).strip().lower()
    except EOFError:
        return default
    return answer if answer in choices else default


# ---------------------------------------------------------------------------
# Hooks registration
# ---------------------------------------------------------------------------

def hook_command(script: Path) -> str:
    return f"python3 {shlex.quote(str(script))}"


def is_skillforge_hook_command(command: str, event: str) -> bool:
    """Identify a previously registered SkillForge hook command for an event."""
    suffix = f"scripts/hooks/{HOOK_EVENTS[event]['script'].name}"
    return command.replace('"', "").replace("'", "").rstrip().endswith(suffix)


def merge_hooks_into_settings(settings: dict) -> dict:
    """Merge SkillForge hook registrations into a settings dict, in place."""
    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("existing 'hooks' value in settings.json is not an object; refusing to overwrite it")

    for event, spec in HOOK_EVENTS.items():
        entries = hooks.setdefault(event, [])
        if not isinstance(entries, list):
            raise ValueError(f"existing hooks.{event} in settings.json is not a list; refusing to overwrite it")

        new_hook = {"type": "command", "command": hook_command(spec["script"]), "timeout": spec["timeout"]}
        replaced = False
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            for hook in entry.get("hooks", []):
                if isinstance(hook, dict) and is_skillforge_hook_command(str(hook.get("command", "")), event):
                    hook.update(new_hook)
                    replaced = True
        if not replaced:
            entries.append({"hooks": [new_hook]})
    return settings


def backup_file(path: Path) -> Path | None:
    if not path.exists():
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = path.with_name(f"{path.name}.bak-{stamp}")
    backup.write_bytes(path.read_bytes())
    return backup


def register_hooks(settings_path: Path) -> list[str]:
    """Back up settings.json and merge the two advisor hooks in. Returns notes."""
    notes: list[str] = []
    settings: dict = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"{settings_path} is not valid JSON ({error}); fix it before registering hooks")
        if not isinstance(settings, dict):
            raise ValueError(f"{settings_path} does not contain a JSON object; refusing to overwrite it")
        backup = backup_file(settings_path)
        if backup:
            notes.append(f"Backed up existing settings to {backup}")

    merge_hooks_into_settings(settings)
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    notes.append(f"Registered SessionStart + UserPromptSubmit advisor hooks in {settings_path}")
    return notes


# ---------------------------------------------------------------------------
# launchd cleanup (removal of the old, broken delivery mechanism)
# ---------------------------------------------------------------------------

def remove_launchd_agents(launch_agents_dir: Path = LAUNCH_AGENTS_DIR) -> list[str]:
    """Unload and delete any previously installed SkillForge launchd plists."""
    notes: list[str] = []
    if not launch_agents_dir.is_dir():
        return notes
    for plist in sorted(launch_agents_dir.glob("*")):
        if "skillforge" not in plist.name.lower() or plist.suffix != ".plist":
            continue
        try:
            subprocess.run(
                ["launchctl", "unload", str(plist)],
                capture_output=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
        try:
            plist.unlink()
            notes.append(f"Removed obsolete launchd agent: {plist}")
        except OSError as error:
            notes.append(f"Could not remove {plist}: {error}")
    return notes


# ---------------------------------------------------------------------------
# Optional agent snippet (only ever written on explicit request)
# ---------------------------------------------------------------------------

def integration_snippet() -> str:
    advisor_cli = SCRIPTS_DIR / "context_advisor.py"
    return f"""# SkillForge Context Advisor

Advisor suggestions arrive via hooks. To manage them:

`python3 {advisor_cli} list|use|snooze|dismiss [<id>]`

Never invoke a suggested skill until the user confirms.
"""


def write_agent_snippet(path: Path) -> None:
    snippet = integration_snippet()
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if "SkillForge Context Advisor" in existing:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    separator = "\n\n" if existing.strip() else ""
    path.write_text(existing.rstrip() + separator + snippet + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------

PERSONAL_CONTEXT_DISCLOSURE = """Personal Context is OFF by default. If you enable it, SkillForge will:
  - run targeted keyword searches (ripgrep) over ONLY the directories you list,
  - optionally list GitHub repo metadata (name/description) for owners you name via 'gh',
  - store small matching excerpts locally in ~/.local/share/skillforge/
    (credential-looking lines are redacted before storage).
Nothing leaves this machine. You can disable it anytime by rerunning this installer."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Configure the SkillForge Context Skill Advisor (interactive by default)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--proactivity-level",
        choices=sorted(PROACTIVITY_SETTINGS),
        help="Global Proactivity Level (prompted interactively when omitted; default balanced)",
    )
    hooks_group = parser.add_mutually_exclusive_group()
    hooks_group.add_argument(
        "--enable-hooks",
        action="store_true",
        help="Register the SessionStart + UserPromptSubmit hooks without prompting",
    )
    hooks_group.add_argument(
        "--no-hooks",
        action="store_true",
        help="Skip hook registration without prompting",
    )
    parser.add_argument(
        "--personal-paths",
        nargs="*",
        metavar="PATH",
        help="Opt in to Personal Context scanning of these directories (counts as consent)",
    )
    parser.add_argument(
        "--github-owners",
        nargs="*",
        metavar="OWNER",
        help="Opt in to GitHub repo metadata for these owners (counts as consent)",
    )
    parser.add_argument(
        "--no-personal-context",
        action="store_true",
        help="Explicitly disable Personal Context (revokes any prior consent)",
    )
    parser.add_argument(
        "--project-override",
        type=Path,
        help="Also write a project-level .skillforge/config.json override at this path",
    )
    parser.add_argument(
        "--write-agent-snippet",
        type=Path,
        help="Append the advisor snippet to this instruction file (never done by default)",
    )
    parser.add_argument(
        "--claude-settings",
        type=Path,
        default=DEFAULT_CLAUDE_SETTINGS,
        help="Path to the Claude Code settings.json used for hook registration",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Never prompt; take only what the flags say (safe defaults otherwise)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    interactive = sys.stdin.isatty() and not args.non_interactive
    touched: list[str] = []

    # 1. Proactivity Level and global config.
    level = args.proactivity_level
    if level is None:
        if interactive:
            level = ask_choice("Proactivity Level", sorted(PROACTIVITY_SETTINGS), "balanced")
        else:
            level = "balanced"
    global_path = ensure_global_config(level)
    touched.append(f"Wrote global config ({level}): {global_path}")

    if args.project_override:
        project_path = write_project_override(args.project_override, level)
        touched.append(f"Wrote project override: {project_path}")

    # 2. Personal Context (opt-in with recorded consent).
    personal_paths = list(args.personal_paths or [])
    github_owners = list(args.github_owners or [])
    if args.no_personal_context:
        update_global_config(
            {"context_sources": {"personal": {"enabled": False, "consented": False}}}
        )
        touched.append("Personal Context disabled (consent revoked).")
    elif personal_paths or github_owners:
        record_personal_context_consent(personal_paths, github_owners)
        touched.append(
            "Personal Context enabled with recorded consent "
            f"(paths: {personal_paths or 'none'}, GitHub owners: {github_owners or 'none'})."
        )
    elif interactive:
        print()
        print(PERSONAL_CONTEXT_DISCLOSURE)
        if ask_yes_no("Enable Personal Context scanning?", default=False):
            personal_paths = ask_list("Directories to scan (e.g. ~/kb, ~/notes)")
            github_owners = ask_list("GitHub owners for repo metadata")
            record_personal_context_consent(personal_paths, github_owners)
            touched.append(
                "Personal Context enabled with recorded consent "
                f"(paths: {personal_paths or 'none'}, GitHub owners: {github_owners or 'none'})."
            )
        else:
            update_global_config(
                {"context_sources": {"personal": {"enabled": False, "consented": False}}}
            )
            touched.append("Personal Context left disabled.")
    else:
        touched.append("Personal Context left disabled (opt in with --personal-paths/--github-owners).")

    # 3. Hooks registration (explicit confirmation or --enable-hooks only).
    register = False
    if args.enable_hooks:
        register = True
    elif not args.no_hooks and interactive:
        print()
        print("SkillForge can deliver advisor suggestions through two Claude Code hooks:")
        print("  SessionStart      - shows pending queued suggestions when a session opens")
        print("  UserPromptSubmit  - fast inline checkpoint against the prebuilt skill index")
        register = ask_yes_no(f"Register these hooks in {args.claude_settings}?", default=False)
    if register:
        try:
            touched.extend(register_hooks(args.claude_settings))
        except ValueError as error:
            print(f"Hook registration failed: {error}", file=sys.stderr)
            return 1
    else:
        touched.append("Hooks not registered (rerun with --enable-hooks to register).")

    # 4. Clean up the old launchd delivery mechanism.
    touched.extend(remove_launchd_agents())

    # 5. Agent snippet only on explicit request.
    if args.write_agent_snippet:
        target = args.write_agent_snippet.expanduser().resolve()
        write_agent_snippet(target)
        touched.append(f"Appended advisor snippet to {target}")

    print()
    print("SkillForge advisor setup summary:")
    for note in touched:
        print(f"  - {note}")
    print(f"  - Config path: {CONFIG_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
