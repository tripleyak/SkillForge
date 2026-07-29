#!/usr/bin/env python3
"""
mine_skill_friction.py - Opt-in, PURELY LOCAL skill-friction miner.

Scans your local Claude Code session transcripts (~/.claude/projects/*/
<session>.jsonl) for skill friction signals:

  (a) which skills the Skill tool actually invoked, and how often
  (b) skills that were invoked and then apparently abandoned (the next user
      message is a correction like "no", "stop", "that's not ...")
  (c) repeated Bash command patterns across sessions that no installed
      skill covers - candidates for new skills

PRIVACY: this script REFUSES to run without --consent. It reads only local
files, never opens a network connection, and never sends anything anywhere.
Quoted evidence is redacted for obvious secrets (password / api key / token /
secret patterns) before it is stored. The only output is a local report and
a local evidence file for the Context Skill Advisor.

Usage:
    python3 mine_skill_friction.py --consent
    python3 mine_skill_friction.py --consent --days 14 --json

Exit Codes:
    0  - Report produced
    1  - General failure
    2  - Refused: --consent not given (or bad arguments)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    from common import get_index_path, phrase_in_text
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from common import get_index_path, phrase_in_text

DEFAULT_PROJECTS_DIR = Path.home() / ".claude" / "projects"
DEFAULT_EVIDENCE_PATH = (
    Path.home() / ".local" / "share" / "skillforge" / "friction.json"
)

# --- redaction --------------------------------------------------------------

# key: value / key=value / key "value" forms for obvious secret names
_SECRET_KV_RE = re.compile(
    r"(?i)\b(password|passwd|pwd|api[_-]?key|access[_-]?key|secret|token|"
    r"bearer|authorization|credentials?)\b(\s*[:=]\s*|\s+)(\"[^\"]+\"|'[^']+'|\S+)"
)
# bare token shapes (sk-..., ghp_..., xoxb-..., AWS AKIA...)
_SECRET_TOKEN_RE = re.compile(
    r"\b(?:sk-[A-Za-z0-9_-]{8,}|ghp_[A-Za-z0-9]{8,}|github_pat_[A-Za-z0-9_]{8,}|"
    r"xox[a-z]-[A-Za-z0-9-]{8,}|AKIA[0-9A-Z]{12,})\b"
)


def redact(text: str) -> str:
    """Redact obvious secrets from quoted evidence."""
    text = _SECRET_KV_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]", text)
    return _SECRET_TOKEN_RE.sub("[REDACTED]", text)


# --- correction detection ---------------------------------------------------

CORRECTION_PHRASES = (
    "no", "nope", "stop", "wait", "that's not", "that is not", "not what i",
    "wrong", "undo", "cancel", "don't do that", "do not do that", "not that",
    "never mind", "nevermind",
)
_CORRECTION_WINDOW = 80  # only the opening of the reply signals a correction


def is_correction(user_text: str) -> bool:
    head = user_text.strip()[:_CORRECTION_WINDOW]
    return any(phrase_in_text(phrase, head) for phrase in CORRECTION_PHRASES)


# --- bash normalization -----------------------------------------------------

# Programs whose bare invocations are routine plumbing, never skill candidates.
TRIVIAL_PROGRAMS = frozenset(
    "ls cat echo pwd cd head tail grep egrep fgrep find mkdir rm cp mv which "
    "touch sed awk wc sort uniq tr cut true false test date open chmod chown "
    "export env printf sleep kill ps df du tar unzip zip curl wget man less "
    "more diff tee xargs basename dirname readlink realpath".split()
)
# Programs where the subcommand is the meaningful unit.
SUBCOMMAND_PROGRAMS = frozenset(
    "git npm npx pnpm yarn pip pip3 python python3 docker docker-compose "
    "kubectl gh cargo go make poetry uv aws gcloud az brew node bundle "
    "rails terraform helm".split()
)
TRIVIAL_GIT_SUBCOMMANDS = frozenset(
    "status log diff add commit push pull checkout branch stash show fetch "
    "clone init config remote rev-parse restore switch merge reset mv rm".split()
)

_ENV_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=\S+\s+")
_CD_PREFIX_RE = re.compile(r"^cd\s+\S+\s*&&\s*")


def normalize_command(command: str) -> Optional[str]:
    """Reduce a Bash command to a clusterable prefix, or None if trivial."""
    cmd = command.strip()
    for _ in range(4):  # strip leading `cd x &&` and env assignments
        new = _CD_PREFIX_RE.sub("", cmd)
        new = _ENV_ASSIGNMENT_RE.sub("", new)
        if new == cmd:
            break
        cmd = new.strip()
    tokens = cmd.split()
    if not tokens:
        return None
    program = Path(tokens[0]).name
    if program in TRIVIAL_PROGRAMS:
        return None
    if program in SUBCOMMAND_PROGRAMS and len(tokens) > 1:
        sub = tokens[1]
        if sub.startswith("-"):
            return program
        if program == "git" and sub in TRIVIAL_GIT_SUBCOMMANDS:
            return None
        return f"{program} {sub}"
    return program


# --- transcript parsing (defensive against schema variance) ------------------

def iter_jsonl(path: Path) -> Iterable[dict]:
    """Yield parsed JSON objects from a transcript, skipping bad lines."""
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    yield obj
    except OSError:
        return


def _content_blocks(entry: dict) -> List[Any]:
    """Extract message content blocks, tolerating schema variants."""
    message = entry.get("message")
    if isinstance(message, dict):
        content = message.get("content")
    else:
        content = entry.get("content")
    if isinstance(content, list):
        return content
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return []


def user_text(entry: dict) -> str:
    """Plain text of a user entry ('' when it is only tool results)."""
    parts = []
    for block in _content_blocks(entry):
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(parts).strip()


def tool_uses(entry: dict) -> List[dict]:
    """tool_use blocks in an assistant entry."""
    uses = []
    for block in _content_blocks(entry):
        if isinstance(block, dict) and block.get("type") == "tool_use":
            uses.append(block)
    return uses


# --- mining -----------------------------------------------------------------

def mine_session(path: Path, stats: Dict[str, Any]) -> None:
    """Fold one session transcript into the accumulating stats."""
    session_id = path.stem
    pending_skill: Optional[str] = None
    for entry in iter_jsonl(path):
        entry_type = entry.get("type")
        if entry_type == "assistant":
            for use in tool_uses(entry):
                name = use.get("name")
                tool_input = use.get("input") if isinstance(use.get("input"), dict) else {}
                if name == "Skill":
                    skill = str(tool_input.get("skill") or "").strip()
                    if skill:
                        stats["invocations"][skill] += 1
                        pending_skill = skill
                elif name == "Bash":
                    command = str(tool_input.get("command") or "")
                    prefix = normalize_command(command)
                    if prefix:
                        cluster = stats["bash_clusters"][prefix]
                        cluster["count"] += 1
                        cluster["sessions"].add(session_id)
                        if not cluster["example"]:
                            cluster["example"] = redact(command)[:200]
        elif entry_type == "user":
            text = user_text(entry)
            if not text:
                continue  # tool results are not user speech
            if pending_skill is not None:
                if is_correction(text):
                    stats["abandoned"].append({
                        "skill": pending_skill,
                        "session": session_id,
                        "user_reaction": redact(text)[:160],
                    })
                pending_skill = None


def load_skill_index() -> List[Dict[str, str]]:
    """Load the skill index if present (never rebuilt here - stay light)."""
    index_path = get_index_path()
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    skills = data.get("skills")
    if not isinstance(skills, list):
        return []
    return [
        {"name": str(s.get("name", "")), "description": str(s.get("description", ""))}
        for s in skills if isinstance(s, dict)
    ]


def covered_by_skill(prefix: str, skills: List[Dict[str, str]]) -> Optional[str]:
    """Name of an installed skill covering every token of the prefix, if any."""
    tokens = [t for t in prefix.split() if t]
    if not tokens:
        return None
    for skill in skills:
        haystack = f"{skill['name'].replace('-', ' ')} {skill['description']}"
        if all(phrase_in_text(token, haystack) for token in tokens):
            return skill["name"]
    return None


def mine(projects_dir: Path, days: int, min_sessions: int, min_count: int
         ) -> Dict[str, Any]:
    cutoff = time.time() - days * 86400
    transcripts = [
        p for p in sorted(projects_dir.glob("*/*.jsonl"))
        if p.is_file() and p.stat().st_mtime >= cutoff
    ]
    stats: Dict[str, Any] = {
        "invocations": defaultdict(int),
        "abandoned": [],
        "bash_clusters": defaultdict(
            lambda: {"count": 0, "sessions": set(), "example": ""}),
    }
    for transcript in transcripts:
        mine_session(transcript, stats)

    skills = load_skill_index()
    candidates = []
    covered = []
    for prefix, cluster in stats["bash_clusters"].items():
        if len(cluster["sessions"]) < min_sessions or cluster["count"] < min_count:
            continue
        covering = covered_by_skill(prefix, skills)
        record = {
            "pattern": prefix,
            "occurrences": cluster["count"],
            "sessions": len(cluster["sessions"]),
            "example": cluster["example"],
        }
        if covering:
            record["covered_by"] = covering
            covered.append(record)
        else:
            candidates.append(record)
    candidates.sort(key=lambda c: (c["sessions"], c["occurrences"]), reverse=True)
    covered.sort(key=lambda c: (c["sessions"], c["occurrences"]), reverse=True)

    invocations = dict(sorted(stats["invocations"].items(),
                              key=lambda kv: kv[1], reverse=True))
    return {
        "generated_at": datetime.now().isoformat(),
        "days": days,
        "transcripts_scanned": len(transcripts),
        "skill_invocations": invocations,
        "abandoned": stats["abandoned"],
        "candidate_patterns": candidates,
        "covered_patterns": covered,
    }


# --- output -----------------------------------------------------------------

def format_report(data: Dict[str, Any]) -> str:
    lines = [
        f"\n{'=' * 64}",
        f"Skill friction report - last {data['days']} days "
        f"({data['transcripts_scanned']} transcripts, local only)",
        f"{'=' * 64}",
        f"\n{'Skill invocations':-^64}",
    ]
    if data["skill_invocations"]:
        for skill, count in list(data["skill_invocations"].items())[:20]:
            lines.append(f"  {count:>4}  {skill}")
    else:
        lines.append("  (none found)")

    lines.append(f"\n{'Apparently abandoned invocations':-^64}")
    if data["abandoned"]:
        for item in data["abandoned"]:
            lines.append(f"  {item['skill']} (session {item['session'][:8]}): "
                         f"\"{item['user_reaction']}\"")
    else:
        lines.append("  (none found)")

    lines.append(f"\n{'Candidate new skills (uncovered repeated patterns)':-^64}")
    if data["candidate_patterns"]:
        for c in data["candidate_patterns"][:15]:
            lines.append(f"  {c['occurrences']:>4}x in {c['sessions']} sessions: "
                         f"`{c['pattern']}`")
            lines.append(f"        e.g. {c['example']}")
    else:
        lines.append("  (none met the repetition bar)")

    if data["covered_patterns"]:
        lines.append(f"\n{'Repeated patterns already covered by a skill':-^64}")
        for c in data["covered_patterns"][:10]:
            lines.append(f"  {c['occurrences']:>4}x `{c['pattern']}` "
                         f"-> covered by {c['covered_by']} (is it firing?)")

    lines.append("\nNothing left this machine. Evidence written locally only.")
    lines.append("=" * 64 + "\n")
    return "\n".join(lines)


def write_evidence(data: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# --- CLI ----------------------------------------------------------------------

REFUSAL = """\
Refusing to run: transcript mining requires explicit consent.

This tool reads your LOCAL Claude Code session transcripts under
~/.claude/projects/ to find skill friction. It is purely local - nothing is
ever sent anywhere - but reading transcripts is opt-in by design.

Re-run with --consent to proceed.
"""


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Opt-in skill-friction miner over LOCAL session transcripts. "
            "Purely local: reads only files under --projects-dir, writes only "
            "a local report and evidence file, never opens the network."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --consent
  %(prog)s --consent --days 14 --json
        """,
    )
    parser.add_argument("--consent", action="store_true",
                        help="Required: explicitly allow reading local transcripts")
    parser.add_argument("--days", type=int, default=30,
                        help="Only scan transcripts modified in the last N days (default: 30)")
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    parser.add_argument("--projects-dir", type=Path, default=DEFAULT_PROJECTS_DIR,
                        help="Transcript root (default: ~/.claude/projects)")
    parser.add_argument("--output", type=Path, default=DEFAULT_EVIDENCE_PATH,
                        help="Advisor evidence file (default: "
                             "~/.local/share/skillforge/friction.json)")
    parser.add_argument("--min-sessions", type=int, default=3,
                        help="Sessions a pattern must span to be a candidate (default: 3)")
    parser.add_argument("--min-count", type=int, default=5,
                        help="Total occurrences a pattern needs (default: 5)")
    args = parser.parse_args(argv)

    if not args.consent:
        print(REFUSAL, file=sys.stderr)
        return 2

    projects_dir = args.projects_dir.expanduser().resolve()
    if not projects_dir.is_dir():
        print(f"Error: transcript directory not found: {projects_dir}", file=sys.stderr)
        return 1

    try:
        data = mine(projects_dir, args.days, args.min_sessions, args.min_count)
        write_evidence(data, args.output.expanduser())
    except OSError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print(format_report(data))
        print(f"Evidence written to: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
