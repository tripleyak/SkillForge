#!/usr/bin/env python3
"""
context_sources.py - Targeted context collection for the SkillForge advisor.

The collector searches broadly for candidate sources, then reads only small
relevant excerpts. It is not a full indexer.
"""

from __future__ import annotations

import fnmatch
import json
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    from skillforge_config import expand_paths
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from skillforge_config import expand_paths


STOP_WORDS = {
    "about", "after", "again", "agent", "and", "being", "clean", "could", "create", "current",
    "data", "default", "every", "feature", "first", "from", "have", "into", "make", "more",
    "need", "for", "including", "monthly", "name", "should", "skill", "skillforge", "that", "their", "there", "this",
    "user", "using", "what", "when", "where", "with", "would", "run", "focus",
    "session", "existing", "summaries", "summary", "wants", "your", "implement", "updates", "scripts",
}

PROJECT_CANDIDATES = [
    "AGENTS.md",
    "README.md",
    "CONTEXT.md",
    "CONTEXT-MAP.md",
    "package.json",
    "pyproject.toml",
    "pnpm-lock.yaml",
    "yarn.lock",
    "package-lock.json",
]


@dataclass
class Evidence:
    tier: str
    source: str
    path: str
    excerpt: str
    matched_terms: list[str]
    personal_context_used: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def query_terms(text: str, cwd: Path | None = None, limit: int = 12) -> list[str]:
    """Extract simple search terms from the current work context."""
    candidates = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower())
    if cwd:
        candidates.extend(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", cwd.name.lower()))

    terms: list[str] = []
    for term in candidates:
        normalized = term.strip("-_")
        if normalized and normalized not in STOP_WORDS and normalized not in terms:
            terms.append(normalized)
        if len(terms) >= limit:
            break
    return terms


def matches_terms(text: str, terms: list[str]) -> list[str]:
    """Return terms found in text."""
    lower = text.lower()
    return [
        term
        for term in terms
        if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", lower)
    ]


def is_excluded(path: Path, patterns: list[str]) -> bool:
    """Check obvious sensitive/cache/dependency exclusions."""
    expanded = str(path.expanduser())
    name = path.name
    for pattern in patterns:
        if fnmatch.fnmatch(expanded, str(Path(pattern).expanduser())):
            return True
        if fnmatch.fnmatch(expanded, pattern):
            return True
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def read_excerpt(path: Path, terms: list[str], max_chars: int = 700) -> str:
    """Read a narrow excerpt from a candidate text file."""
    try:
        if path.stat().st_size > 1_000_000:
            return ""
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""

    if not terms:
        return text[:max_chars].strip()

    lines = text.splitlines()
    for index, line in enumerate(lines):
        if matches_terms(line, terms):
            start = max(0, index - 1)
            end = min(len(lines), index + 2)
            return "\n".join(lines[start:end])[:max_chars].strip()
    return text[:max_chars].strip()


def collect_session_evidence(context_text: str, terms: list[str]) -> list[Evidence]:
    """Create evidence from the current session text passed to the advisor."""
    if not context_text.strip():
        return []
    excerpt = context_text.strip()[:900]
    return [
        Evidence(
            tier="session",
            source="provided-context",
            path="session",
            excerpt=excerpt,
            matched_terms=matches_terms(excerpt, terms),
        )
    ]


def collect_project_evidence(cwd: Path, terms: list[str], excludes: list[str], limit: int = 8) -> list[Evidence]:
    """Collect narrow evidence from the current project."""
    evidence: list[Evidence] = []
    cwd = cwd.resolve()

    for relative in PROJECT_CANDIDATES:
        path = cwd / relative
        if path.exists() and path.is_file() and not is_excluded(path, excludes):
            excerpt = read_excerpt(path, terms)
            matched = matches_terms(excerpt + " " + relative, terms)
            if excerpt and (not terms or matched):
                evidence.append(
                    Evidence(
                        tier="project",
                        source="project-file",
                        path=str(path),
                        excerpt=excerpt,
                        matched_terms=matched,
                    )
                )
        if len(evidence) >= limit:
            return evidence[:limit]

    adr_dir = cwd / "docs" / "adr"
    if adr_dir.exists() and adr_dir.is_dir():
        for path in sorted(adr_dir.glob("*.md"))[:5]:
            if is_excluded(path, excludes):
                continue
            excerpt = read_excerpt(path, terms)
            matched = matches_terms(excerpt + " " + path.name, terms)
            if excerpt and (not terms or matched):
                evidence.append(
                    Evidence(
                        tier="project",
                        source="project-adr",
                        path=str(path),
                        excerpt=excerpt,
                        matched_terms=matched,
                    )
                )
            if len(evidence) >= limit:
                return evidence[:limit]

    return evidence[:limit]


def rg_search(paths: list[Path], terms: list[str], excludes: list[str], limit: int) -> list[tuple[Path, str, list[str]]]:
    """Run ripgrep in a bounded way and return matching file excerpts."""
    if not terms or not shutil.which("rg"):
        return []

    pattern = "|".join(re.escape(term) for term in terms[:8])
    args = ["rg", "--ignore-case", "--line-number", "--max-count", "2", "--no-heading"]
    for exclude in excludes:
        args.extend(["-g", f"!{exclude}"])
    args.extend([pattern, *[str(path) for path in paths]])

    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=8, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return []

    results: list[tuple[Path, str, list[str]]] = []
    seen: set[Path] = set()
    for line in proc.stdout.splitlines():
        if len(results) >= limit:
            break
        parts = line.split(":", 2)
        if len(parts) != 3:
            continue
        path = Path(parts[0])
        if path in seen or is_excluded(path, excludes):
            continue
        excerpt = read_excerpt(path, terms)
        if not excerpt:
            continue
        seen.add(path)
        results.append((path, excerpt, matches_terms(excerpt + " " + str(path), terms)))
    return results


def collect_personal_evidence(config: dict[str, Any], terms: list[str], excludes: list[str], limit: int = 8) -> list[Evidence]:
    """Collect targeted evidence from configured personal paths."""
    personal = config.get("context_sources", {}).get("personal", {})
    if not personal.get("enabled", True):
        return []

    paths = expand_paths(personal.get("paths", []))
    matches = rg_search(paths, terms, excludes, limit)
    evidence = [
        Evidence(
            tier="personal",
            source="personal-path",
            path=str(path),
            excerpt=excerpt,
            matched_terms=matched,
            personal_context_used=True,
        )
        for path, excerpt, matched in matches
    ]
    return evidence[:limit]


def collect_github_metadata(config: dict[str, Any], terms: list[str], limit: int = 5) -> list[Evidence]:
    """Collect matching GitHub repo metadata without reading repository contents."""
    personal = config.get("context_sources", {}).get("personal", {})
    github = personal.get("github", {})
    if not personal.get("enabled", True) or not github.get("enabled", True) or not shutil.which("gh"):
        return []

    owners = github.get("owner_limit", [])
    evidence: list[Evidence] = []
    for owner in owners:
        if len(evidence) >= limit:
            break
        args = [
            "gh",
            "repo",
            "list",
            str(owner),
            "--limit",
            "200",
            "--json",
            "nameWithOwner,description,url,isPrivate,updatedAt",
        ]
        try:
            proc = subprocess.run(args, capture_output=True, text=True, timeout=8, check=False)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if proc.returncode != 0:
            continue
        try:
            repos = json.loads(proc.stdout)
        except json.JSONDecodeError:
            continue
        for repo in repos:
            haystack = f"{repo.get('nameWithOwner', '')} {repo.get('description', '')}"
            matched = matches_terms(haystack, terms)
            if not matched:
                continue
            evidence.append(
                Evidence(
                    tier="personal",
                    source="github-metadata",
                    path=repo.get("url", ""),
                    excerpt=haystack[:700],
                    matched_terms=matched,
                    personal_context_used=True,
                )
            )
            if len(evidence) >= limit:
                break
    return evidence[:limit]


def collect_context_evidence(
    config: dict[str, Any],
    cwd: Path,
    context_text: str = "",
    limit: int = 20,
) -> list[Evidence]:
    """Collect evidence across enabled source tiers."""
    sources = config.get("context_sources", {})
    excludes = config.get("excludes", [])
    terms = query_terms(context_text, cwd=cwd)

    evidence: list[Evidence] = []
    if sources.get("session", {}).get("enabled", True):
        evidence.extend(collect_session_evidence(context_text, terms))
    if sources.get("project", {}).get("enabled", True):
        evidence.extend(collect_project_evidence(cwd, terms, excludes))
    if sources.get("personal", {}).get("enabled", True):
        remaining = max(0, limit - len(evidence))
        evidence.extend(collect_personal_evidence(config, terms, excludes, limit=remaining))
        remaining = max(0, limit - len(evidence))
        evidence.extend(collect_github_metadata(config, terms, limit=min(5, remaining)))

    return evidence[:limit]
