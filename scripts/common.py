#!/usr/bin/env python3
"""
common.py - Shared runtime helpers for SkillForge scripts.

Single home for the Result dataclass, the skill index path, and the
word-boundary phrase matcher, so no script carries its own diverging copy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import List


@dataclass
class Result:
    """Standard result object for script operations."""

    success: bool
    message: str
    data: dict = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "errors": self.errors,
            "warnings": self.warnings,
            "timestamp": datetime.now().isoformat(),
        }


def get_index_path() -> Path:
    """Return the canonical skill index file path."""
    return Path.home() / ".cache" / "skillrecommender" / "skill_index.json"


@lru_cache(maxsize=4096)
def phrase_pattern(phrase: str) -> "re.Pattern[str]":
    """Compile a word-boundary pattern for a (lowercased) phrase."""
    return re.compile(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])")


def phrase_in_text(phrase: str, text: str) -> bool:
    """Return True when phrase appears in text as a whole token/phrase.

    Word-boundary matching: 'ai' does NOT match 'email', 'ml' does NOT
    match 'html'. Case-insensitive.
    """
    phrase = phrase.strip().lower()
    if not phrase:
        return False
    return phrase_pattern(phrase).search(text.lower()) is not None
