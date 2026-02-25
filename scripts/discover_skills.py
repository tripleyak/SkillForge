#!/usr/bin/env python3
"""
discover_skills.py - Scan skill sources and build a searchable index

Part of the skillrecommender skill.

Responsibilities:
- Scan custom skills (Codex + Claude), superpowers, and plugin marketplaces
- Extract skill metadata (name, triggers, keywords, domain)
- Build searchable JSON index for fast matching

Usage:
    python discover_skills.py
    python discover_skills.py --verbose
    python discover_skills.py --output custom_path.json

Exit Codes:
    0  - Success
    1  - General failure
    3  - Directory not found
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any


# ===========================================================================
# RESULT TYPES
# ===========================================================================

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
            "timestamp": datetime.now().isoformat()
        }


# ===========================================================================
# SKILL SOURCES
# ===========================================================================

SKILL_SOURCES = [
    {
        "name": "codex-custom",
        "path": Path.home() / ".codex" / "skills",
        "patterns": ["*/SKILL.md", "*/skill.md"],
        "priority": 1
    },
    {
        "name": "claude-custom",
        "path": Path.home() / ".claude" / "skills",
        "patterns": ["*/SKILL.md", "*/skill.md"],
        "priority": 2
    },
    {
        "name": "superpowers",
        "path": Path.home() / ".claude" / "plugins" / "cache" / "superpowers" / "skills",
        "pattern": "*/*.md",
        "priority": 3
    },
    {
        "name": "anthropic-agent-skills",
        "path": Path.home() / ".claude" / "plugins" / "marketplaces" / "anthropic-agent-skills",
        "pattern": "skills/*/skill.md",
        "priority": 4
    },
    {
        "name": "claude-code-workflows",
        "path": Path.home() / ".claude" / "plugins" / "marketplaces" / "claude-code-workflows",
        "pattern": "plugins/*/skills/*/skill.md",
        "priority": 5
    },
    {
        "name": "claude-code-plugins",
        "path": Path.home() / ".claude" / "plugins" / "marketplaces" / "claude-code-plugins",
        "pattern": "*/skills/*/skill.md",
        "priority": 6
    }
]

# ===========================================================================
# UNIVERSAL DOMAIN CLASSIFICATION
# ===========================================================================
# These domain names MUST match the DOMAIN_SYNONYMS in triage_skill_request.py
# for consistent matching across discovery and triage.

DOMAIN_KEYWORDS = {
    # Document types (aligns with spreadsheet, document, presentation, pdf domains)
    "spreadsheet": ["excel", "xlsx", "xls", "csv", "spreadsheet", "workbook", "tabular"],
    "document": ["word", "docx", "doc", "document", "report", "write"],
    "presentation": ["powerpoint", "pptx", "slides", "presentation", "deck", "keynote"],
    "pdf": ["pdf", "portable document"],

    # Development domains
    "debugging": ["debug", "error", "trace", "exception", "stack trace", "fix bug", "investigate", "root cause"],
    "testing": ["test", "tdd", "coverage", "e2e", "unit", "integration", "cypress", "jest", "pytest", "spec"],
    "security": ["security", "owasp", "vulnerability", "audit", "pentest", "xss", "injection"],
    "code_quality": ["review", "refactor", "lint", "code smell", "solid", "pr review", "code review"],
    "database": ["database", "db", "sql", "postgres", "mysql", "mongodb", "migration", "schema", "orm"],
    "api": ["api", "rest", "graphql", "openapi", "endpoint", "swagger", "http"],
    "frontend": ["ui", "ux", "frontend", "react", "vue", "angular", "component", "css", "styling"],
    "accessibility": ["accessibility", "a11y", "wcag", "screen reader", "aria"],
    "performance": ["performance", "optimize", "slow", "speed", "cache", "profiling", "bottleneck"],
    "authentication": ["auth", "login", "authentication", "oauth", "jwt", "session", "password"],
    "deployment": ["deploy", "release", "ship", "hosting", "production"],
    "devops": ["ci", "cd", "docker", "kubernetes", "k8s", "container", "helm", "terraform", "pipeline"],
    "documentation": ["documentation", "docs", "readme", "changelog", "jsdoc"],
    "architecture": ["architecture", "system design", "microservices", "monolith", "pattern"],
    "workflow": ["flowchart", "diagram", "workflow", "process", "swimlane", "sequence"],

    # Specialized domains
    "ai_ml": ["ai", "ml", "llm", "rag", "langchain", "prompt", "embedding", "model"],
    "visual": ["visual", "image", "graphic", "art", "canvas", "brand"],
    "meta": ["orchestrate", "compose", "skill", "maker", "proactive", "chain"],
}


# ===========================================================================
# PARSING FUNCTIONS
# ===========================================================================

def extract_frontmatter(content: str) -> Dict[str, Any]:
    """Extract YAML frontmatter from markdown content."""
    frontmatter = {}

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            yaml_content = parts[1].strip()
            for line in yaml_content.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    frontmatter[key.strip()] = value.strip()

    return frontmatter


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
    if "Trigger" in content:
        table_section = content[content.find("Trigger"):content.find("---", content.find("Trigger"))]
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
    """Classify skill into domains based on keywords."""
    domains = []
    content_lower = content.lower()

    for domain, domain_keywords in DOMAIN_KEYWORDS.items():
        score = 0
        for kw in domain_keywords:
            if kw in keywords or kw in content_lower:
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
    except Exception as e:
        return None

    # Extract skill name from path or frontmatter
    frontmatter = extract_frontmatter(content)
    name = frontmatter.get("name", path.parent.name)

    # Extract metadata
    triggers = extract_triggers(content)
    keywords = extract_keywords(content, name)
    domains = classify_domain(keywords, content)

    # Get description
    description = frontmatter.get("description", "")
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
        "version": frontmatter.get("version", "1.0.0")
    }


# ===========================================================================
# DISCOVERY
# ===========================================================================

def discover_skills(verbose: bool = False) -> Result:
    """Scan all skill sources and build index."""
    skills = []
    errors = []
    warnings = []

    for source in SKILL_SOURCES:
        source_path = source["path"]

        if not source_path.exists():
            warnings.append(f"Source not found: {source['name']} ({source_path})")
            continue

        if verbose:
            print(f"Scanning {source['name']}: {source_path}", file=sys.stderr)

        # Find skill files
        source_patterns = source.get("patterns")
        if not source_patterns:
            source_patterns = [source["pattern"]]

        skill_files = []
        for pattern in source_patterns:
            pattern_parts = pattern.split("/")

            if len(pattern_parts) == 2:
                # Simple pattern like */SKILL.md
                skill_files.extend(list(source_path.glob(pattern)))
            else:
                # Complex pattern - use recursive glob
                found = list(source_path.glob("**/*.md"))
                found = [f for f in found if "skill" in f.name.lower()]
                skill_files.extend(found)

        # Deduplicate files across multiple patterns
        unique_files = []
        seen = set()
        for skill_file in skill_files:
            key = str(skill_file.resolve())
            if key in seen:
                continue
            seen.add(key)
            unique_files.append(skill_file)

        for skill_file in unique_files:
            skill_data = parse_skill_file(skill_file, source["name"], source["priority"])
            if skill_data:
                skills.append(skill_data)
                if verbose:
                    print(f"  Found: {skill_data['name']}", file=sys.stderr)
            else:
                warnings.append(f"Failed to parse: {skill_file}")

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
        message=f"Discovered {len(skills)} skills from {len(SKILL_SOURCES)} sources",
        data={
            "skills": skills,
            "domains": domain_index,
            "sources": {s["name"]: str(s["path"]) for s in SKILL_SOURCES},
            "total_count": len(skills)
        },
        warnings=warnings,
        errors=errors
    )


# ===========================================================================
# STATE MANAGEMENT
# ===========================================================================

def get_index_path() -> Path:
    """Get the skill index file path."""
    cache_dir = Path.home() / ".cache" / "skillrecommender"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "skill_index.json"


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

    args = parser.parse_args()

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

    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
