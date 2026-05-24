#!/usr/bin/env python3
"""
install_skillforge.py - Configure SkillForge proactive advising.

This script writes SkillForge config, optionally writes a project override,
prints an agent integration snippet, and can install a local scheduled advisor
run on macOS via launchd.

Exit Codes:
    0 - Success
    1 - Installation failed
"""

from __future__ import annotations

import argparse
import os
import platform
import plistlib
import sys
from pathlib import Path

try:
    from skillforge_config import (
        CONFIG_FILE,
        PROACTIVITY_SETTINGS,
        ensure_global_config,
        level_settings,
        write_project_override,
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from skillforge_config import (
        CONFIG_FILE,
        PROACTIVITY_SETTINGS,
        ensure_global_config,
        level_settings,
        write_project_override,
    )


LAUNCHD_LABEL = "com.skillforge.context-advisor"


def advisor_script_path() -> Path:
    return Path(__file__).resolve().parent / "context_advisor.py"


def launchd_plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LAUNCHD_LABEL}.plist"


def write_launchd_plist(level: str, cwd: Path | None = None) -> Path:
    """Write a launchd plist for scheduled advisor runs."""
    interval = level_settings(level)["interval_seconds"]
    if interval <= 0:
        raise ValueError("Cannot schedule advisor when Proactivity Level is off")

    args = [sys.executable, str(advisor_script_path()), "run"]
    if cwd:
        args.extend(["--cwd", str(cwd.resolve())])

    plist = {
        "Label": LAUNCHD_LABEL,
        "ProgramArguments": args,
        "StartInterval": interval,
        "RunAtLoad": False,
        "StandardOutPath": str(Path.home() / "Library" / "Logs" / "skillforge-advisor.log"),
        "StandardErrorPath": str(Path.home() / "Library" / "Logs" / "skillforge-advisor.err.log"),
    }

    path = launchd_plist_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        plistlib.dump(plist, handle)
    return path


def integration_snippet() -> str:
    """Return the agent instruction block for Advisor Checkpoints."""
    script = advisor_script_path()
    return f"""# SkillForge Context Advisor

At session start, task shifts, repeated failures, and before final responses, run:

`python {script} checkpoint --cwd "$PWD" --text "<brief current context>"`

Surface only returned suggestions that pass the configured Proactivity Level.
Do not invoke a suggested skill until the user confirms or explicitly asks.
"""


def append_agent_instructions(path: Path) -> None:
    """Append the integration snippet to an agent instruction file."""
    snippet = integration_snippet()
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if "SkillForge Context Advisor" in existing:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    separator = "\n\n" if existing.strip() else ""
    path.write_text(existing.rstrip() + separator + snippet + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Configure SkillForge proactive advising",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--proactivity-level",
        choices=sorted(PROACTIVITY_SETTINGS),
        default="balanced",
        help="Global Proactivity Level (default: balanced)",
    )
    parser.add_argument(
        "--project-override",
        type=Path,
        help="Write a project-level .skillforge/config.json override at this project path",
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Write a local scheduled advisor job when supported",
    )
    parser.add_argument(
        "--schedule-cwd",
        type=Path,
        help="Project/workspace directory for scheduled advisor runs",
    )
    parser.add_argument(
        "--write-agent-instructions",
        type=Path,
        help="Append the Advisor Checkpoint snippet to an instruction file such as ~/AGENTS.md",
    )
    parser.add_argument(
        "--print-snippet",
        action="store_true",
        help="Print the Advisor Checkpoint integration snippet",
    )
    args = parser.parse_args()

    global_path = ensure_global_config(args.proactivity_level)
    print(f"Wrote global config: {global_path}")

    if args.project_override:
        project_path = write_project_override(args.project_override, args.proactivity_level)
        print(f"Wrote project override: {project_path}")

    if args.schedule:
        if platform.system() == "Darwin":
            plist_path = write_launchd_plist(args.proactivity_level, args.schedule_cwd)
            print(f"Wrote launchd schedule: {plist_path}")
            print(f"Load it with: launchctl load {plist_path}")
        else:
            interval = level_settings(args.proactivity_level)["interval_seconds"]
            if interval <= 0:
                print("Proactivity Level is off; no schedule written.")
            else:
                minutes = max(1, interval // 60)
                print("No native scheduler was written on this platform.")
                print(f"Cron example: */{minutes} * * * * {sys.executable} {advisor_script_path()} run")

    if args.write_agent_instructions:
        target = Path(os.path.expanduser(str(args.write_agent_instructions))).resolve()
        append_agent_instructions(target)
        print(f"Updated agent instructions: {target}")

    if args.print_snippet or not args.write_agent_instructions:
        print()
        print(integration_snippet())

    print(f"Config path: {CONFIG_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
