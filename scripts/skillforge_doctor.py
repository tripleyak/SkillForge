#!/usr/bin/env python3
"""
skillforge_doctor.py - Ecosystem health report for the whole skill roster.

Scans every skill source (same sources as discover_skills.py), refreshes the
skill index when stale, and reports:

  (a) trigger collisions - skill pairs whose descriptions overlap heavily
      (word-boundary Jaccard on content words); worst pairs reported
  (b) exact/near-duplicate skill names across sources
  (c) stale skills - SKILL.md referencing references/, scripts/, or assets/
      files that do not exist
  (d) description lint - missing, over 1024 chars, no trigger-condition
      language
  (e) token-budget report - body word counts, top-10 heaviest SKILL.md files
  (f) pinned dated model IDs (claude-*-YYYYMMDD)

Read-only over skills: the doctor NEVER mutates a skill. The only write is
refreshing the shared index cache when it is stale.

Usage:
    python3 skillforge_doctor.py
    python3 skillforge_doctor.py --json
    python3 skillforge_doctor.py --strict          # exit 10 when errors found
    python3 skillforge_doctor.py --sources DIR...  # scan only these roots

Exit Codes:
    0  - Report produced (healthy, or warnings only, or errors without --strict)
    1  - General failure
    2  - Invalid arguments
    10 - Errors found and --strict was given
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from _constants import (
        DESCRIPTION_MAX_LENGTH, INDEX_MAX_AGE_HOURS, PINNED_MODEL_REGEX,
        TRIGGER_LANGUAGE_MARKERS, BODY_WORDS_ERROR,
    )
    from common import Result, get_index_path
    from discover_skills import (
        SKILL_SOURCES, dedupe_skills, find_skill_files, index_age_hours,
        parse_skill_file, save_index,
    )
    from frontmatter import parse_frontmatter, split_frontmatter
    from run_skill_evals import content_words
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _constants import (
        DESCRIPTION_MAX_LENGTH, INDEX_MAX_AGE_HOURS, PINNED_MODEL_REGEX,
        TRIGGER_LANGUAGE_MARKERS, BODY_WORDS_ERROR,
    )
    from common import Result, get_index_path
    from discover_skills import (
        SKILL_SOURCES, dedupe_skills, find_skill_files, index_age_hours,
        parse_skill_file, save_index,
    )
    from frontmatter import parse_frontmatter, split_frontmatter
    from run_skill_evals import content_words

DEFAULT_COLLISION_THRESHOLD = 0.4
TOP_N = 10

# Relative references/scripts/assets paths mentioned in a SKILL.md body.
_REL_PATH_RE = re.compile(r"(?<![\w/.-])((?:references|scripts|assets)/[\w][\w\-./]*)")
# Mentions containing template placeholders are not real paths.
_PLACEHOLDER_RE = re.compile(r"\{\{|[<>*$]|TODO", re.IGNORECASE)


@dataclass
class Issue:
    check: str          # collision | duplicate_name | stale_ref | description | model_pin | token_budget
    severity: str       # error | warning | info
    skill: str
    message: str

    def to_dict(self) -> dict:
        return {"check": self.check, "severity": self.severity,
                "skill": self.skill, "message": self.message}


# ===========================================================================
# COLLECTION
# ===========================================================================

def scan_raw_skills(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Scan sources WITHOUT dedupe (duplicate detection needs every copy)."""
    skills: List[Dict[str, Any]] = []
    for source in sources:
        source_path = Path(source["path"])
        if not source_path.exists():
            continue
        for skill_file in find_skill_files(source_path, source["recursive"]):
            data = parse_skill_file(skill_file, source["name"], source["priority"])
            if data:
                skills.append(data)
    return skills


def sources_from_dirs(dirs: List[Path]) -> List[Dict[str, Any]]:
    """Treat ad-hoc directories as non-recursive skill roots (tests/CI)."""
    return [
        {"name": f"adhoc:{d.name}", "path": d, "recursive": False, "priority": i + 1}
        for i, d in enumerate(dirs)
    ]


def refresh_index_if_stale(deduped: List[Dict[str, Any]]) -> Optional[str]:
    """Rebuild the shared index cache when missing or stale.

    Returns a note describing what happened (or None when fresh). This is
    the doctor's only write, and it touches the cache - never a skill.
    """
    age = index_age_hours()
    if age is not None and age <= INDEX_MAX_AGE_HOURS:
        return None
    domain_index: Dict[str, List[str]] = {}
    for skill in deduped:
        for domain in skill.get("domains", []):
            domain_index.setdefault(domain, []).append(skill["name"])
    result = Result(
        success=True,
        message="rebuilt by skillforge_doctor",
        data={
            "skills": deduped,
            "domains": domain_index,
            "sources": {s["name"]: str(s["path"]) for s in SKILL_SOURCES},
            "total_count": len(deduped),
        },
    )
    try:
        save_index(result)
    except OSError as exc:
        return f"index refresh failed: {exc}"
    reason = "missing" if age is None else f"stale ({age:.1f}h old)"
    return f"index was {reason}; rebuilt at {get_index_path()}"


# ===========================================================================
# CHECKS
# ===========================================================================

def check_collisions(skills: List[Dict[str, Any]], threshold: float
                     ) -> Tuple[List[Issue], List[Dict[str, Any]]]:
    """(a) Pairwise description keyword overlap (word-boundary Jaccard)."""
    issues: List[Issue] = []
    keyword_sets = {
        s["name"]: content_words(str(s.get("description") or ""))
        for s in skills
    }
    pairs: List[Dict[str, Any]] = []
    for a, b in combinations(sorted(keyword_sets), 2):
        wa, wb = keyword_sets[a], keyword_sets[b]
        union = wa | wb
        if not union:
            continue
        shared = wa & wb
        jaccard = len(shared) / len(union)
        if jaccard > 0:
            pairs.append({
                "skills": [a, b],
                "jaccard": round(jaccard, 3),
                "shared_keywords": sorted(shared)[:12],
            })
    pairs.sort(key=lambda p: p["jaccard"], reverse=True)
    worst = pairs[:TOP_N]
    for pair in worst:
        if pair["jaccard"] > threshold:
            issues.append(Issue(
                "collision", "warning", " + ".join(pair["skills"]),
                f"description keyword Jaccard {pair['jaccard']:.2f} "
                f"(> {threshold}) - these skills compete for the same triggers; "
                f"shared: {', '.join(pair['shared_keywords'][:8])}",
            ))
    return issues, worst


def _normalized_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def check_duplicate_names(raw_skills: List[Dict[str, Any]]) -> List[Issue]:
    """(b) Exact and near-duplicate names across sources."""
    issues: List[Issue] = []
    exact: Dict[str, List[Dict[str, Any]]] = {}
    for skill in raw_skills:
        exact.setdefault(skill["name"].lower(), []).append(skill)
    for name, copies in sorted(exact.items()):
        distinct_paths = sorted({c["path"] for c in copies})
        if len(distinct_paths) > 1:
            sources = sorted({c["source"] for c in copies})
            issues.append(Issue(
                "duplicate_name", "warning", name,
                f"exact name appears in {len(distinct_paths)} places "
                f"(sources: {', '.join(sources)}) - "
                f"only the highest-priority copy is routable",
            ))
    # Near-duplicates among distinct names (hyphen/underscore variants etc.)
    by_normalized: Dict[str, set] = {}
    for name in exact:
        by_normalized.setdefault(_normalized_name(name), set()).add(name)
    for normalized, names in sorted(by_normalized.items()):
        if len(names) > 1:
            issues.append(Issue(
                "duplicate_name", "warning", ", ".join(sorted(names)),
                "near-duplicate names (identical after removing separators) - "
                "agents cannot reliably distinguish them",
            ))
    return issues


def extract_relative_refs(body: str) -> List[str]:
    """Relative references/scripts/assets paths mentioned in a SKILL.md body."""
    refs = []
    for match in _REL_PATH_RE.finditer(body):
        ref = match.group(1).rstrip(".,:;)")
        if _PLACEHOLDER_RE.search(ref):
            continue
        refs.append(ref)
    return sorted(set(refs))


def check_skill_files(skills: List[Dict[str, Any]]
                      ) -> Tuple[List[Issue], List[Dict[str, Any]]]:
    """(c)(d)(e)(f) Per-skill file checks. Returns (issues, word_counts)."""
    issues: List[Issue] = []
    word_counts: List[Dict[str, Any]] = []
    for skill in skills:
        name = skill["name"]
        path = Path(skill["path"])
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            issues.append(Issue("stale_ref", "error", name,
                                f"SKILL.md unreadable: {exc}"))
            continue
        frontmatter, _err = parse_frontmatter(text)
        _fm_text, body = split_frontmatter(text)

        # (c) stale relative references
        skill_dir = path.parent
        for ref in extract_relative_refs(body):
            if not (skill_dir / ref).exists():
                issues.append(Issue(
                    "stale_ref", "error", name,
                    f"SKILL.md references missing file: {ref}",
                ))

        # (d) description lint
        description = str(frontmatter.get("description") or "").strip()
        if not description:
            issues.append(Issue("description", "error", name,
                                "missing or empty description"))
        else:
            if len(description) > DESCRIPTION_MAX_LENGTH:
                issues.append(Issue(
                    "description", "error", name,
                    f"description is {len(description)} chars "
                    f"(max {DESCRIPTION_MAX_LENGTH} for portability)",
                ))
            desc_lower = description.lower()
            if not any(marker in desc_lower for marker in TRIGGER_LANGUAGE_MARKERS):
                issues.append(Issue(
                    "description", "warning", name,
                    "description has no trigger-condition language "
                    "('Use when ...') - weak triggering surface",
                ))

        # (e) token budget
        words = len(body.split())
        word_counts.append({"name": name, "path": str(path), "words": words})
        if words > BODY_WORDS_ERROR:
            issues.append(Issue(
                "token_budget", "warning", name,
                f"SKILL.md body is {words} words (over the {BODY_WORDS_ERROR} "
                "hard budget) - the whole body loads on every invocation",
            ))

        # (f) pinned dated model IDs
        model = frontmatter.get("model")
        if model and re.search(PINNED_MODEL_REGEX, str(model)):
            issues.append(Issue(
                "model_pin", "error", name,
                f"pinned dated model ID: {model} - pin a family alias or omit",
            ))
    word_counts.sort(key=lambda w: w["words"], reverse=True)
    return issues, word_counts


# ===========================================================================
# REPORT
# ===========================================================================

def run_doctor(sources: List[Dict[str, Any]], threshold: float,
               manage_index: bool) -> Dict[str, Any]:
    raw = scan_raw_skills(sources)
    deduped = dedupe_skills(raw)

    index_note = refresh_index_if_stale(deduped) if manage_index else None

    issues: List[Issue] = []
    dup_issues = check_duplicate_names(raw)
    collision_issues, worst_pairs = check_collisions(deduped, threshold)
    file_issues, word_counts = check_skill_files(deduped)
    issues.extend(dup_issues)
    issues.extend(collision_issues)
    issues.extend(file_issues)

    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    return {
        "skill_count": len(deduped),
        "raw_count": len(raw),
        "index_note": index_note,
        "issues": issues,
        "worst_collision_pairs": worst_pairs,
        "heaviest_skills": word_counts[:TOP_N],
        "total_words": sum(w["words"] for w in word_counts),
        "error_count": len(errors),
        "warning_count": len(warnings),
    }


def format_report(data: Dict[str, Any], threshold: float) -> str:
    lines = [
        f"\n{'=' * 64}",
        "SkillForge Doctor - ecosystem health report",
        f"{'=' * 64}",
        f"\nSkills: {data['skill_count']} unique "
        f"({data['raw_count']} copies across sources); "
        f"total SKILL.md load: {data['total_words']:,} words",
    ]
    if data["index_note"]:
        lines.append(f"Index: {data['index_note']}")

    lines.append(f"\n{'Worst trigger-collision pairs':-^64}")
    if data["worst_collision_pairs"]:
        for pair in data["worst_collision_pairs"]:
            flag = "  <-- over threshold" if pair["jaccard"] > threshold else ""
            lines.append(f"  {pair['jaccard']:.2f}  {pair['skills'][0]} + "
                         f"{pair['skills'][1]}{flag}")
    else:
        lines.append("  (no description overlap found)")

    lines.append(f"\n{'Top-10 heaviest SKILL.md files (body words)':-^64}")
    for entry in data["heaviest_skills"]:
        lines.append(f"  {entry['words']:>6}  {entry['name']}")

    issues: List[Issue] = data["issues"]
    for severity, header in (("error", "ERRORS"), ("warning", "WARNINGS")):
        matching = [i for i in issues if i.severity == severity]
        if matching:
            lines.append(f"\n{header + f' ({len(matching)})':-^64}")
            for issue in matching:
                lines.append(f"  [{issue.check}] {issue.skill}: {issue.message}")

    lines.append(f"\nSummary: {data['error_count']} error(s), "
                 f"{data['warning_count']} warning(s) "
                 f"across {data['skill_count']} skills")
    lines.append("=" * 64 + "\n")
    return "\n".join(lines)


def to_json(data: Dict[str, Any]) -> str:
    payload = dict(data)
    payload["issues"] = [i.to_dict() for i in data["issues"]]
    return json.dumps(payload, indent=2)


# ===========================================================================
# CLI
# ===========================================================================

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ecosystem health report over every installed skill (read-only)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # scan all standard sources
  %(prog)s --json --strict    # CI: machine output, exit 10 on errors
  %(prog)s --sources ./skills # scan only an ad-hoc directory
        """,
    )
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    parser.add_argument("--strict", action="store_true",
                        help="Exit 10 when errors are found (default: always 0)")
    parser.add_argument("--threshold", type=float, default=DEFAULT_COLLISION_THRESHOLD,
                        help=f"Collision Jaccard threshold (default: {DEFAULT_COLLISION_THRESHOLD})")
    parser.add_argument("--sources", nargs="+", type=Path, metavar="DIR",
                        help="Scan only these directories (each holds <skill>/SKILL.md); "
                             "skips the shared index entirely")
    args = parser.parse_args(argv)

    if args.sources:
        dirs = [d.expanduser().resolve() for d in args.sources]
        missing = [d for d in dirs if not d.is_dir()]
        if missing:
            print(f"Error: not a directory: {missing[0]}", file=sys.stderr)
            return 2
        sources = sources_from_dirs(dirs)
        manage_index = False
    else:
        sources = SKILL_SOURCES
        manage_index = True

    try:
        data = run_doctor(sources, args.threshold, manage_index)
    except OSError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(to_json(data))
    else:
        print(format_report(data, args.threshold))

    if args.strict and data["error_count"] > 0:
        return 10
    return 0


if __name__ == "__main__":
    sys.exit(main())
