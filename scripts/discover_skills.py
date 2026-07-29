#!/usr/bin/env python3
"""
discover_skills.py - Scan all skill sources and build a searchable index

Part of the skillforge skill.

Responsibilities:
- Scan personal skill directories and plugin caches (Claude Code and Codex)
- Extract skill metadata (name, triggers, keywords, domain)
- Dedupe by skill name (personal skills beat plugin-cache copies)
- Build searchable JSON index for fast matching

Usage:
    python discover_skills.py
    python discover_skills.py --verbose
    python discover_skills.py --output custom_path.json
    python discover_skills.py --max-age-hours 24   # skip rebuild if fresh

Exit Codes:
    0  - Success (including a skipped rebuild when the index is fresh)
    1  - General failure
    3  - No skill sources found (every configured source directory missing)
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

try:
    from _constants import DOMAIN_VOCABULARY, INDEX_MAX_AGE_HOURS
    from common import Result, get_index_path, phrase_pattern
    from frontmatter import parse_frontmatter
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _constants import DOMAIN_VOCABULARY, INDEX_MAX_AGE_HOURS
    from common import Result, get_index_path, phrase_pattern
    from frontmatter import parse_frontmatter


# ===========================================================================
# SKILL SOURCES
# ===========================================================================
# Personal skill directories (priority 1-3) beat plugin caches (4-5): when
# the same skill name appears in multiple sources, the lowest priority number
# wins during dedupe.
#
# recursive=False sources have the layout <root>/<skill-name>/SKILL.md.
# recursive=True sources are plugin caches with layouts like
# <root>/<marketplace>/<plugin>/<version>/skills/<skill-name>/SKILL.md
# (and deeper variants), so they are scanned for any file named SKILL.md.

SKILL_SOURCES = [
    {
        "name": "claude-personal",
        "path": Path.home() / ".claude" / "skills",
        "recursive": False,
        "priority": 1,
    },
    {
        "name": "agents-personal",
        "path": Path.home() / ".agents" / "skills",
        "recursive": False,
        "priority": 2,
    },
    {
        "name": "codex-personal",
        "path": Path.home() / ".codex" / "skills",
        "recursive": False,
        "priority": 3,
    },
    {
        "name": "claude-plugin-cache",
        "path": Path.home() / ".claude" / "plugins" / "cache",
        "recursive": True,
        "priority": 4,
    },
    {
        "name": "codex-plugin-cache",
        "path": Path.home() / ".codex" / "plugins" / "cache",
        "recursive": True,
        "priority": 5,
    },
]

# Shared with triage_skill_request.py via _constants.DOMAIN_VOCABULARY
DOMAIN_KEYWORDS = DOMAIN_VOCABULARY


# ===========================================================================
# PARSING FUNCTIONS
# ===========================================================================

def extract_frontmatter(content: str) -> Dict[str, Any]:
    """Extract YAML frontmatter from markdown content (lenient)."""
    parsed, _error = parse_frontmatter(content)
    return parsed


def get_version(frontmatter: Dict[str, Any]) -> str:
    """Extract version from frontmatter, checking both root and metadata."""
    # First check root level (legacy/deprecated)
    if "version" in frontmatter:
        return str(frontmatter["version"])

    # Then check metadata.version (preferred location)
    if "metadata" in frontmatter and isinstance(frontmatter["metadata"], dict):
        version = frontmatter["metadata"].get("version")
        if version:
            return str(version)

    # Default fallback
    return "1.0.0"


def extract_triggers(content: str) -> List[str]:
    """Extract trigger phrases from skill content."""
    triggers = []

    # Look for triggers in frontmatter or content
    trigger_patterns = [
        r'\*\*Triggers?:\*\*\s*`([^`]+)`',
        r'Triggers?:\s*`([^`]+)`',
        r'\|\s*`([^`]+)`\s*\|.*trigger',
        r'trigger[s]?.*`([^`]+)`',
    ]

    for pattern in trigger_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        triggers.extend(matches)

    # Also extract from trigger tables
    table_pattern = r'\|\s*`([^`]+)`\s*\|'
    trigger_start = content.find("Trigger")
    if trigger_start != -1:
        # Guard against find() returning -1
        end_marker = content.find("---", trigger_start)
        if end_marker == -1:
            end_marker = len(content)  # Use end of content if no delimiter found
        table_section = content[trigger_start:end_marker]
        matches = re.findall(table_pattern, table_section)
        triggers.extend(matches)

    return list(set(triggers))


def extract_keywords(content: str, name: str) -> List[str]:
    """Extract keywords from skill content."""
    keywords = []

    # Add name variations
    keywords.append(name.lower())
    keywords.extend(name.lower().replace("-", " ").split())

    # Look for keywords in tables
    keyword_pattern = r'\|\s*\*\*[^*]+\*\*\s*\|[^|]+\|\s*([^|]+)\s*\|'
    matches = re.findall(keyword_pattern, content)
    for match in matches:
        keywords.extend([k.strip().lower() for k in match.split(",")])

    # Extract from purpose/description
    purpose_pattern = r'(?:Purpose|Description)[:\s]+([^\n]+)'
    matches = re.findall(purpose_pattern, content, re.IGNORECASE)
    for match in matches:
        words = re.findall(r'\b[a-z]{4,}\b', match.lower())
        keywords.extend(words)

    return list(set(keywords))


def classify_domain(keywords: List[str], content: str) -> List[str]:
    """Classify skill into domains using word-boundary keyword matching.

    Uses whole-token matching (common.phrase_pattern), so 'ai' does not
    match 'email' and 'ml' does not match 'html'.
    """
    domains = []
    content_lower = content.lower()
    keyword_set = {k.strip().lower() for k in keywords}

    for domain, domain_keywords in DOMAIN_KEYWORDS.items():
        score = 0
        for kw in domain_keywords:
            if kw in keyword_set or phrase_pattern(kw).search(content_lower):
                score += 1
        if score >= 2:
            domains.append(domain)

    if not domains:
        domains.append("general")

    return domains


def parse_skill_file(path: Path, source_name: str, priority: int) -> Optional[Dict]:
    """Parse a skill file and extract metadata."""
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return None

    # Extract skill name from path or frontmatter
    frontmatter = extract_frontmatter(content)
    name = str(frontmatter.get("name") or path.parent.name)

    # Extract metadata
    triggers = extract_triggers(content)
    keywords = extract_keywords(content, name)
    domains = classify_domain(keywords, content)

    # Get description
    description = frontmatter.get("description", "")
    if not isinstance(description, str):
        description = str(description)
    if not description:
        # Try to extract from first paragraph
        lines = content.split("\n")
        for line in lines:
            if line.strip() and not line.startswith("#") and not line.startswith("-"):
                description = line.strip()[:200]
                break

    return {
        "name": name,
        "source": source_name,
        "path": str(path),
        "priority": priority,
        "description": description,
        "triggers": triggers,
        "keywords": keywords,
        "domains": domains,
        "version": get_version(frontmatter)
    }


# ===========================================================================
# DISCOVERY
# ===========================================================================

def find_skill_files(source_path: Path, recursive: bool) -> List[Path]:
    """Find SKILL.md files for a source.

    Only files named exactly SKILL.md (case-insensitive) qualify - README.md,
    SKILLS.md, and other markdown files are rejected.
    """
    files: List[Path] = []
    if recursive:
        for candidate in source_path.rglob("*.md"):
            if candidate.is_file() and candidate.name.lower() == "skill.md":
                files.append(candidate)
    else:
        try:
            children = sorted(source_path.iterdir())
        except OSError:
            return []
        for child in children:
            if not child.is_dir():
                continue
            for candidate in child.iterdir():
                if candidate.is_file() and candidate.name.lower() == "skill.md":
                    files.append(candidate)
                    break
    return files


def dedupe_skills(skills: List[Dict]) -> List[Dict]:
    """Dedupe skills by name, keeping the highest-priority source.

    Priority is the source's priority number (lower wins): personal skills
    beat plugin-cache copies of the same skill.
    """
    best: Dict[str, Dict] = {}
    for skill in sorted(skills, key=lambda s: (s["priority"], s["name"], s["path"])):
        key = skill["name"].lower()
        if key not in best:
            best[key] = skill
    return list(best.values())


def discover_skills(verbose: bool = False) -> Result:
    """Scan all skill sources and build index."""
    skills = []
    errors = []
    warnings = []
    missing_sources = 0

    for source in SKILL_SOURCES:
        source_path = source["path"]

        if not source_path.exists():
            missing_sources += 1
            warnings.append(f"Source not found: {source['name']} ({source_path})")
            continue

        if verbose:
            print(f"Scanning {source['name']}: {source_path}", file=sys.stderr)

        skill_files = find_skill_files(source_path, source["recursive"])

        for skill_file in skill_files:
            skill_data = parse_skill_file(skill_file, source["name"], source["priority"])
            if skill_data:
                skills.append(skill_data)
                if verbose:
                    print(f"  Found: {skill_data['name']}", file=sys.stderr)
            else:
                warnings.append(f"Failed to parse: {skill_file}")

    total_found = len(skills)
    skills = dedupe_skills(skills)
    duplicates_removed = total_found - len(skills)

    # Sort by priority (lower = higher priority)
    skills.sort(key=lambda s: (s["priority"], s["name"]))

    # Build domain index
    domain_index = {}
    for skill in skills:
        for domain in skill["domains"]:
            if domain not in domain_index:
                domain_index[domain] = []
            domain_index[domain].append(skill["name"])

    return Result(
        success=True,
        message=(
            f"Discovered {len(skills)} unique skills from {len(SKILL_SOURCES)} sources "
            f"({duplicates_removed} duplicate name(s) removed)"
        ),
        data={
            "skills": skills,
            "domains": domain_index,
            "sources": {s["name"]: str(s["path"]) for s in SKILL_SOURCES},
            "total_count": len(skills),
            "duplicates_removed": duplicates_removed,
            "missing_sources": missing_sources,
        },
        warnings=warnings,
        errors=errors
    )


# ===========================================================================
# STATE MANAGEMENT
# ===========================================================================

def index_age_hours(path: Optional[Path] = None) -> Optional[float]:
    """Return the index file age in hours, or None if it does not exist."""
    path = path or get_index_path()
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    return max(0.0, (time.time() - mtime) / 3600.0)


def save_index(result: Result, output_path: Optional[Path] = None) -> None:
    """Save skill index to disk."""
    path = output_path or get_index_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    index_data = {
        "version": "2.0.0",
        "generated_at": datetime.now().isoformat(),
        "skills": result.data["skills"],
        "domains": result.data["domains"],
        "sources": result.data["sources"],
        "total_count": result.data["total_count"]
    }

    path.write_text(json.dumps(index_data, indent=2))


# ===========================================================================
# CLI
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Discover and index all available skills",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output file path (default: ~/.cache/skillrecommender/skill_index.json)"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    parser.add_argument(
        "--max-age-hours",
        type=float,
        default=None,
        metavar="HOURS",
        help=(
            "Skip the rebuild when the existing index is younger than HOURS "
            f"(e.g. {INDEX_MAX_AGE_HOURS}). Omit to always rebuild."
        )
    )

    args = parser.parse_args()

    # Staleness gate: skip rebuild when the index is fresh enough
    if args.max_age_hours is not None:
        target = args.output or get_index_path()
        age = index_age_hours(target)
        if age is not None and age <= args.max_age_hours:
            if args.json:
                print(json.dumps({
                    "success": True,
                    "message": f"Index is fresh ({age:.1f}h old); skipping rebuild.",
                    "skipped": True,
                    "index_path": str(target),
                }, indent=2))
            else:
                print(f"Index is fresh ({age:.1f}h old, max {args.max_age_hours}h); skipping rebuild.")
                print(f"Index: {target}")
            sys.exit(0)

    # Discover skills
    result = discover_skills(verbose=args.verbose)

    # Save index
    save_index(result, args.output)

    # Output
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"Discovered {result.data['total_count']} skills")
        print(f"Domains: {', '.join(result.data['domains'].keys())}")
        print(f"Index saved to: {args.output or get_index_path()}")

        if result.warnings:
            print("\nWarnings:")
            for warning in result.warnings:
                print(f"  - {warning}")

    # Exit codes: 0 = success, 1 = general failure, 3 = no sources found.
    # Only count actually-missing source directories (parse warnings must not
    # inflate the count).
    if not result.success:
        sys.exit(1)
    elif result.data["missing_sources"] == len(SKILL_SOURCES):
        sys.exit(3)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
