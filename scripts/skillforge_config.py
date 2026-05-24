#!/usr/bin/env python3
"""
skillforge_config.py - Configuration helpers for SkillForge scripts.

Configuration precedence:
1. .skillforge/config.json in the current project or an ancestor
2. ~/.config/skillforge/config.json
3. built-in defaults
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


CONFIG_DIR = Path.home() / ".config" / "skillforge"
CONFIG_FILE = CONFIG_DIR / "config.json"
DATA_DIR = Path.home() / ".local" / "share" / "skillforge"
PROJECT_CONFIG_DIR = ".skillforge"
PROJECT_CONFIG_FILE = "config.json"

PROACTIVITY_SETTINGS = {
    "off": {"threshold": 101, "max_session": 0, "max_daily": 0, "interval_seconds": 0},
    "quiet": {"threshold": 85, "max_session": 1, "max_daily": 1, "interval_seconds": 86400},
    "balanced": {"threshold": 70, "max_session": 2, "max_daily": 3, "interval_seconds": 7200},
    "active": {"threshold": 55, "max_session": 4, "max_daily": 8, "interval_seconds": 1800},
}

DEFAULT_EXCLUDES = [
    "**/.git/**",
    "**/node_modules/**",
    "**/.env*",
    "**/secrets/**",
    "**/credentials/**",
    "**/cookies/**",
    "**/Library/**",
    "**/__pycache__/**",
    "**/.venv/**",
    "**/venv/**",
    "**/dist/**",
    "**/build/**",
]

DEFAULT_CONFIG: dict[str, Any] = {
    "version": 1,
    "proactivity_level": "balanced",
    "watched_projects": [],
    "context_sources": {
        "session": {"enabled": True},
        "project": {"enabled": True},
        "personal": {
            "enabled": True,
            "paths": ["~/kb", "~/Documents/Work", "~/Projects"],
            "github": {
                "enabled": True,
                "owner_limit": ["tripleyak", "jackatlasov"],
            },
        },
    },
    "excludes": DEFAULT_EXCLUDES,
}


@dataclass
class LoadedConfig:
    config: dict[str, Any]
    global_path: Path
    project_path: Optional[Path]


def read_json(path: Path) -> dict[str, Any]:
    """Read a JSON object, returning an empty object when missing or invalid."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: dict[str, Any]) -> None:
    """Write JSON with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge override into base without mutating either input."""
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def find_project_config(start: Optional[Path] = None) -> Optional[Path]:
    """Find the nearest project-level SkillForge config."""
    current = (start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent

    for directory in [current, *current.parents]:
        candidate = directory / PROJECT_CONFIG_DIR / PROJECT_CONFIG_FILE
        if candidate.exists():
            return candidate
    return None


def load_config(cwd: Optional[Path] = None) -> LoadedConfig:
    """Load effective SkillForge config."""
    global_config = read_json(CONFIG_FILE)
    project_path = find_project_config(cwd)
    project_config = read_json(project_path) if project_path else {}

    config = deep_merge(DEFAULT_CONFIG, global_config)
    config = deep_merge(config, project_config)
    level = config.get("proactivity_level", "balanced")
    if level not in PROACTIVITY_SETTINGS:
        config["proactivity_level"] = "balanced"

    return LoadedConfig(config=config, global_path=CONFIG_FILE, project_path=project_path)


def level_settings(level: str) -> dict[str, int]:
    """Return threshold and schedule settings for a Proactivity Level."""
    return PROACTIVITY_SETTINGS.get(level, PROACTIVITY_SETTINGS["balanced"])


def expand_paths(paths: list[str]) -> list[Path]:
    """Expand user paths and keep only existing locations."""
    expanded: list[Path] = []
    for raw in paths:
        path = Path(raw).expanduser()
        if path.exists():
            expanded.append(path)
    return expanded


def data_dir() -> Path:
    """Return and create SkillForge data directory."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR


def project_key(cwd: Optional[Path] = None) -> str:
    """Return a stable project key for feedback suppression."""
    return str((cwd or Path.cwd()).resolve())


def ensure_global_config(proactivity_level: str = "balanced") -> Path:
    """Create or update the global config with a Proactivity Level."""
    if proactivity_level not in PROACTIVITY_SETTINGS:
        raise ValueError(f"Unknown Proactivity Level: {proactivity_level}")
    existing = read_json(CONFIG_FILE)
    updated = deep_merge(DEFAULT_CONFIG, existing)
    updated["proactivity_level"] = proactivity_level
    write_json(CONFIG_FILE, updated)
    return CONFIG_FILE


def write_project_override(project: Path, proactivity_level: str) -> Path:
    """Write a project-level Proactivity Level override."""
    if proactivity_level not in PROACTIVITY_SETTINGS:
        raise ValueError(f"Unknown Proactivity Level: {proactivity_level}")
    path = project.resolve() / PROJECT_CONFIG_DIR / PROJECT_CONFIG_FILE
    existing = read_json(path)
    existing["proactivity_level"] = proactivity_level
    write_json(path, existing)
    return path
