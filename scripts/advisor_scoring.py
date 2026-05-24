#!/usr/bin/env python3
"""
advisor_scoring.py - Proactive suggestion scoring for SkillForge.

This module preserves the existing SkillForge matcher as the Skill Match Score
and adds advisor-specific context, timing, and feedback components.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    from context_sources import Evidence
    from skillforge_config import level_settings
    from triage_skill_request import classify_input, find_matching_skills
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from context_sources import Evidence
    from skillforge_config import level_settings
    from triage_skill_request import classify_input, find_matching_skills


FRICTION_TERMS = {
    "again", "blocked", "broke", "broken", "error", "failed", "failing",
    "failure", "retry", "same", "still", "stuck", "unclear", "unknown",
}

BROAD_EVIDENCE_TERMS = {
    "about", "after", "again", "against", "agent", "and", "being", "could", "create",
    "clean", "current", "data", "default", "design", "doc", "docs", "document",
    "documentation", "every", "existing", "feature", "first", "focus", "for", "from", "have",
    "including", "into", "make", "monthly", "more", "name", "need", "project", "proactive", "run", "session", "should",
    "skill", "skillforge", "that", "their", "there", "this", "wants",
    "suggestion", "suggestions", "summaries", "summary", "user", "visual", "work", "workflow",
    "using", "what", "when", "where", "with", "would", "your",
    "implement", "updates", "scripts",
}

DOMAIN_EVIDENCE_TERMS = {
    "spreadsheet": {"excel", "workbook", "workbooks", "xlsx", "xls", "csv", "sheet", "sheets"},
    "code_quality": {"code", "review", "reviews", "pull", "request", "pr"},
}


@dataclass
class Suggestion:
    id: str
    fingerprint: str
    action: str
    skill_name: str | None
    skill_source: str | None
    skill_path: str | None
    confidence: str
    final_score: int
    scores: dict[str, int]
    why_now: str
    evidence: list[dict[str, Any]]
    choices: list[str]
    personal_context_used: bool
    project_key: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def confidence_band(score: int) -> str:
    """Convert numeric score to a user-facing confidence band."""
    if score >= 80:
        return "high"
    if score >= 60:
        return "medium"
    return "low"


def candidate_key(candidate: dict[str, Any]) -> tuple[str, str, str]:
    """Preserve source/path identity for duplicate skill names."""
    return (
        str(candidate.get("name") or ""),
        str(candidate.get("source") or ""),
        str(candidate.get("path") or ""),
    )


def relevant_terms(skill: dict[str, Any]) -> set[str]:
    """Extract terms used to connect evidence to a skill."""
    terms: set[str] = set()
    name = str(skill.get("name", ""))
    terms.update(part for part in re.split(r"[-_\s]+", name.lower()) if len(part) > 3)
    terms.update(str(trigger).lower() for trigger in skill.get("triggers", []) if len(str(trigger)) > 3)
    terms.update(
        str(domain).lower()
        for domain in skill.get("domains", [])
        if len(str(domain)) > 3 and str(domain).lower() not in BROAD_EVIDENCE_TERMS
    )
    for domain in skill.get("domains", []):
        terms.update(DOMAIN_EVIDENCE_TERMS.get(str(domain).lower(), set()))
    terms.update(str(keyword).lower() for keyword in skill.get("keywords", []) if len(str(keyword)) > 3)
    description = str(skill.get("description", "")).lower()
    terms.update(word for word in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{3,}", description) if len(word) > 3)
    return {term for term in terms if term not in BROAD_EVIDENCE_TERMS}


def term_in_text(term: str, text: str) -> bool:
    """Return True when a relevant term appears as a whole token or phrase."""
    if not term:
        return False
    return re.search(rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])", text.lower()) is not None


def any_term_in_text(terms: set[str], text: str) -> bool:
    """Return True when any relevant term appears in text."""
    return any(term_in_text(term, text) for term in terms)


def evidence_text_for_skill_match(item: Evidence) -> str:
    """Return the evidence text used for skill relevance checks."""
    if item.tier == "personal":
        return " ".join(item.matched_terms).lower()
    return f"{item.path} {item.excerpt} {' '.join(item.matched_terms)}".lower()


def direct_match_strength(match: dict[str, Any], evidence: list[Evidence]) -> int:
    """Score how explicit the candidate match is in current context."""
    reasons = [str(reason) for reason in match.get("reasons", [])]
    strength = 0
    if any(reason.startswith("name match:") for reason in reasons):
        strength += 45
    if any(reason.startswith("trigger:") for reason in reasons):
        strength += 35
    if any(item.tier == "session" for item in evidence):
        name = str(match.get("name") or "").lower()
        triggers = [str(trigger).lower() for trigger in match.get("triggers", [])]
        session_text = "\n".join(
            f"{item.path} {item.excerpt} {' '.join(item.matched_terms)}".lower()
            for item in evidence
            if item.tier == "session"
        )
        if name and re.search(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", session_text):
            strength += 20
        elif any(
            trigger and re.search(rf"(?<![a-z0-9]){re.escape(trigger)}(?![a-z0-9])", session_text)
            for trigger in triggers
        ):
            strength += 15
    return min(100, strength)


def has_specific_name_signal(skill: dict[str, Any], context_text: str, evidence: list[Evidence]) -> bool:
    """Return True when a niche skill has a specific name token in context."""
    name = str(skill.get("name") or "").lower()
    tokens = [
        token
        for token in re.split(r"[-_\s]+", name)
        if len(token) > 2 and token not in BROAD_EVIDENCE_TERMS and token not in {"kw"}
    ]
    if not tokens:
        return True
    haystack = context_text.lower() + "\n" + "\n".join(
        f"{item.path} {item.excerpt} {' '.join(item.matched_terms)}".lower()
        for item in evidence[:8]
    )
    return any(re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", haystack) for token in tokens)


def evidence_score(skill: dict[str, Any], evidence: list[Evidence]) -> int:
    """Score source-tier evidence for a candidate skill."""
    terms = relevant_terms(skill)
    if not evidence:
        return 0

    matched_count = 0
    session_matched = 0
    tiers: set[str] = set()
    for item in evidence:
        haystack = evidence_text_for_skill_match(item)
        if not terms or any_term_in_text(terms, haystack):
            matched_count += 1
            if item.tier == "session":
                session_matched += 1
            tiers.add(item.tier)

    if matched_count == 0:
        return min(45, len(evidence) * 10)
    return min(100, matched_count * 18 + len(tiers) * 10 + session_matched * 40)


def has_session_skill_evidence(skill: dict[str, Any], evidence: list[Evidence]) -> bool:
    """Return True when session evidence supports a candidate skill."""
    terms = relevant_terms(skill)
    if not terms:
        return False
    for item in evidence:
        if item.tier != "session":
            continue
        haystack = f"{item.excerpt} {' '.join(item.matched_terms)}".lower()
        if any_term_in_text(terms, haystack):
            return True
    return False


def select_relevant_evidence(skill: dict[str, Any], evidence: list[Evidence], limit: int = 3) -> list[Evidence]:
    """Choose evidence that actually supports this skill."""
    terms = relevant_terms(skill)
    if not terms:
        return evidence[:limit]
    selected: list[Evidence] = []
    for item in evidence:
        haystack = evidence_text_for_skill_match(item)
        if any_term_in_text(terms, haystack):
            selected.append(item)
        if len(selected) >= limit:
            break
    return selected[:limit]


def timeliness_score(context_text: str, evidence: list[Evidence]) -> int:
    """Score whether the suggestion appears useful now."""
    haystack = context_text.lower() + "\n" + "\n".join(item.excerpt.lower() for item in evidence[:8])
    friction = sum(1 for term in FRICTION_TERMS if term in haystack)
    evidence_bonus = min(35, len(evidence) * 5)
    return min(100, friction * 15 + evidence_bonus)


def feedback_score(skill_name: str | None, state: dict[str, Any]) -> int:
    """Score prior accepted feedback for this skill."""
    if not skill_name:
        return 0
    accepted = state.get("accepted", {})
    count = int(accepted.get(skill_name, 0)) if isinstance(accepted, dict) else 0
    return min(100, count * 20)


def final_score(
    skill_match: int,
    context_evidence: int,
    timeliness: int,
    feedback: int,
    directness: int = 0,
) -> int:
    """Combine component scores into the Advisor Confidence Score."""
    score = (
        skill_match * 0.70
        + context_evidence * 0.15
        + timeliness * 0.05
        + feedback * 0.05
        + directness * 0.05
    )
    return int(round(min(100, max(0, score))))


def suggestion_fingerprint(action: str, skill_name: str | None, evidence: list[Evidence], project_key: str) -> str:
    """Build a stable fingerprint for suppression and deduplication."""
    evidence_keys = [item.path for item in evidence[:3]]
    raw = "|".join([action, skill_name or "new-skill", project_key, *evidence_keys])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def suggestion_id(fingerprint: str) -> str:
    """Build a short display id."""
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:12]


def phrase_in_context(phrase: str, context_text: str) -> bool:
    """Return True when a phrase appears as a whole token in session context."""
    return term_in_text(phrase, context_text)


def explicitly_named_skills(context_text: str, skills: list[dict[str, Any]]) -> set[str]:
    """Return explicit multi-token skill names mentioned in session context."""
    if not context_text.strip():
        return set()
    names: set[str] = set()
    for skill in skills:
        name = str(skill.get("name") or "").lower()
        if "-" not in name or len(name) < 6:
            continue
        if phrase_in_context(name, context_text):
            names.add(name)
    return names


def build_why_now(match: dict[str, Any], scores: dict[str, int]) -> str:
    """Create a compact reason for an existing-skill suggestion."""
    name = match.get("name", "this skill")
    reasons = match.get("reasons", [])
    reason_text = "; ".join(reasons[:2]) if reasons else "context matches this skill"
    return f"{name} matches the current work ({reason_text}) with {scores['context_evidence']} context evidence."


def build_new_skill_why(top_score: int, evidence: list[Evidence]) -> str:
    """Create a compact reason for a new-skill opportunity."""
    return (
        "No installed skill matched this repeated or well-evidenced work pattern "
        f"above {top_score}%, with {len(evidence)} relevant evidence item(s)."
    )


def build_suggestions(
    context_text: str,
    skills: list[dict[str, Any]],
    evidence: list[Evidence],
    config: dict[str, Any],
    state: dict[str, Any],
    project_key: str,
    limit: int | None = None,
) -> list[Suggestion]:
    """Build proactive suggestions from context and the existing skill index."""
    level = config.get("proactivity_level", "balanced")
    settings = level_settings(level)
    if level == "off":
        return []

    combined_text = context_text.strip()
    matching_evidence = evidence
    if context_text.strip():
        matching_evidence = [item for item in evidence if item.tier == "session"]
    if matching_evidence:
        combined_text = "\n".join([combined_text, *[item.excerpt for item in matching_evidence[:8]]]).strip()
    if not combined_text:
        combined_text = project_key

    _, signals = classify_input(combined_text)
    matches = find_matching_skills(combined_text, skills, limit=24, signals=signals)
    if context_text.strip():
        _, session_signals = classify_input(context_text)
        session_matches = find_matching_skills(context_text, skills, limit=12, signals=session_signals)
        seen_candidates: set[tuple[str, str, str]] = set()
        seeded_matches: list[dict[str, Any]] = []
        for match in [*session_matches, *matches]:
            key = candidate_key(match)
            if key in seen_candidates:
                continue
            seen_candidates.add(key)
            seeded_matches.append(match)
        matches = seeded_matches
    skill_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    first_skill_by_name: dict[str, dict[str, Any]] = {}
    for skill in skills:
        name = skill.get("name")
        if name:
            skill_by_key[candidate_key(skill)] = skill
            first_skill_by_name.setdefault(str(name), skill)
    suggestions: list[Suggestion] = []
    seen_names: set[str] = set()
    explicit_names = explicitly_named_skills(context_text, skills)

    for match in matches:
        match_name = match.get("name")
        if match_name == "skillforge":
            continue
        if explicit_names and str(match_name).lower() not in explicit_names:
            continue
        if match_name in seen_names:
            continue
        if match_name:
            seen_names.add(match_name)

        skill = skill_by_key.get(candidate_key(match), first_skill_by_name.get(str(match.get("name")), match))
        display_evidence = select_relevant_evidence(skill, evidence)
        skill_match = int(match.get("score", 0))
        context_evidence = evidence_score(skill, evidence)
        session_support = has_session_skill_evidence(skill, evidence)
        timeliness = timeliness_score(context_text, evidence)
        feedback = feedback_score(match.get("name"), state)
        directness = direct_match_strength(match, evidence)
        session_evidence = [item for item in evidence if item.tier == "session"]
        if str(match_name).startswith("kw-") and not (
            directness > 0 or has_specific_name_signal(skill, context_text, session_evidence)
        ):
            continue
        scores = {
            "skill_match": skill_match,
            "context_evidence": context_evidence,
            "timeliness": timeliness,
            "user_feedback": feedback,
            "directness": directness,
        }
        score = final_score(skill_match, context_evidence, timeliness, feedback, directness)
        strong_direct_match = any(
            str(reason).startswith(("name match:", "trigger:"))
            for reason in match.get("reasons", [])
        )
        if context_text.strip() and not strong_direct_match and not session_support:
            continue
        if not strong_direct_match and context_evidence < 50:
            continue
        if score < settings["threshold"]:
            continue

        action = "use_existing"
        fingerprint = suggestion_fingerprint(action, match.get("name"), evidence, project_key)
        suggestions.append(
            Suggestion(
                id=suggestion_id(fingerprint),
                fingerprint=fingerprint,
                action=action,
                skill_name=match.get("name"),
                skill_source=match.get("source"),
                skill_path=match.get("path") or skill.get("path"),
                confidence=confidence_band(score),
                final_score=score,
                scores=scores,
                why_now=build_why_now(match, scores),
                evidence=[item.to_dict() for item in display_evidence],
                choices=["use", "snooze", "dismiss", "never for this project"],
                personal_context_used=any(item.personal_context_used for item in display_evidence),
                project_key=project_key,
            )
        )

    top_score = int(matches[0]["score"]) if matches else 0
    allow_create = level in {"balanced", "active"}
    if allow_create and top_score < 50 and len(evidence) >= (2 if level == "active" else 3):
        context_evidence = min(100, len(evidence) * 18)
        timeliness = timeliness_score(context_text, evidence)
        score = final_score(35, context_evidence, timeliness, 0)
        if score >= settings["threshold"]:
            fingerprint = suggestion_fingerprint("create_new", None, evidence, project_key)
            suggestions.append(
                Suggestion(
                    id=suggestion_id(fingerprint),
                    fingerprint=fingerprint,
                    action="create_new",
                    skill_name=None,
                    skill_source=None,
                    skill_path=None,
                    confidence=confidence_band(score),
                    final_score=score,
                    scores={
                        "skill_match": top_score,
                        "context_evidence": context_evidence,
                        "timeliness": timeliness,
                        "user_feedback": 0,
                    },
                    why_now=build_new_skill_why(top_score, evidence),
                    evidence=[item.to_dict() for item in evidence[:3]],
                    choices=["use", "snooze", "dismiss", "never for this project"],
                    personal_context_used=any(item.personal_context_used for item in evidence),
                    project_key=project_key,
                )
            )

    suggestions.sort(key=lambda item: item.final_score, reverse=True)
    return suggestions[: (limit or settings["max_session"])]
