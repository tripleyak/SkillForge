#!/usr/bin/env python3
"""
run_skill_evals.py - Run a skill's evals/ regression suite.

Implements references/testing-and-evals.md section 6. Every generated skill
ships an evals/ directory:

    <skill>/evals/
      triggers.json          # {"positive": [...], "near_miss": [...], "holdout": [...]}
      scenarios/
        01-<slug>.md         # frontmatter: task, baseline_failure, assertions, runs

Modes:
    --static (default)  Validate evals/ structure and lint trigger queries
                        against the skill description. CI-safe: no model
                        calls, no network.
    --live              Everything --static does, plus headless `claude -p`
                        runs: each scenario task is executed and its
                        assertions judged by a second headless call; trigger
                        queries are routed live to measure recall/precision.

Usage:
    python3 run_skill_evals.py <skill-dir>
    python3 run_skill_evals.py <skill-dir> --static --json
    python3 run_skill_evals.py <skill-dir> --live --max-turns 12 --timeout 300

Exit Codes:
    0  - All checks passed
    1  - General failure (bad path, unreadable skill)
    2  - Invalid arguments
    10 - One or more eval checks failed
    11 - --live requested but the `claude` CLI is unavailable
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from common import phrase_in_text
    from frontmatter import parse_yaml_mapping, read_skill_frontmatter, split_frontmatter
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from common import phrase_in_text
    from frontmatter import parse_yaml_mapping, read_skill_frontmatter, split_frontmatter


# ===========================================================================
# TOKENIZATION (shared with skillforge_doctor.py - import from here)
# ===========================================================================

# Function words carry no triggering signal; excluded from keyword matching.
STOPWORDS = frozenset("""
a about above after again all also am an and any are as at be because been
before being below between both but by can cannot could did do does doing
down during each few for from further get got had has have having he her
here hers him his how i if in into is it its itself just like me more most
my no nor not now of off on once only or other our ours out over own same
she should so some such than that the their theirs them then there these
they this those through to too under until up use used using very want was
we were what when where which while who whom why will with would you your
yours yourself
""".split())

# TODO placeholders (from init_skill.py scaffolds) are structurally valid but
# carry no lintable keywords - they pass structure checks and skip the lint.
_TODO_RE = re.compile(r"\btodo\b", re.IGNORECASE)

_WORD_RE = re.compile(r"[a-z0-9]+(?:['-][a-z0-9]+)*")


def content_words(text: str) -> set:
    """Extract meaningful lowercase keywords (word-boundary, no stopwords)."""
    words = set()
    for token in _WORD_RE.findall(text.lower()):
        if len(token) < 3 or token in STOPWORDS or token.isdigit():
            continue
        words.add(token)
    return words


def is_placeholder(query: str) -> bool:
    """A TODO placeholder query counts as structurally valid, unlinted."""
    return bool(_TODO_RE.search(query))


# ===========================================================================
# CHECK RECORDING
# ===========================================================================

@dataclass
class Check:
    target: str      # file or logical unit the check belongs to
    name: str
    passed: bool
    message: str = ""
    evidence: str = ""

    def to_dict(self) -> dict:
        return {
            "target": self.target,
            "name": self.name,
            "passed": self.passed,
            "message": self.message,
            "evidence": self.evidence,
        }


@dataclass
class EvalReport:
    skill_dir: str
    mode: str
    checks: List[Check] = field(default_factory=list)
    scoreboard: Dict[str, Any] = field(default_factory=dict)

    def add(self, target: str, name: str, passed: bool,
            message: str = "", evidence: str = "") -> None:
        self.checks.append(Check(target, name, bool(passed), message, evidence))

    @property
    def failures(self) -> List[Check]:
        return [c for c in self.checks if not c.passed]

    @property
    def passed(self) -> bool:
        return not self.failures

    def to_dict(self) -> dict:
        return {
            "skill_dir": self.skill_dir,
            "mode": self.mode,
            "passed": self.passed,
            "checks": [c.to_dict() for c in self.checks],
            "failures": len(self.failures),
            "scoreboard": self.scoreboard,
        }


# ===========================================================================
# STATIC MODE
# ===========================================================================

TRIGGER_KEYS = ("positive", "near_miss", "holdout")


def load_triggers(evals_dir: Path, report: EvalReport) -> Optional[Dict[str, List[str]]]:
    """Load and shape-check triggers.json. Returns None when unusable."""
    triggers_path = evals_dir / "triggers.json"
    rel = "evals/triggers.json"
    if not triggers_path.is_file():
        report.add(rel, "exists", False, "triggers.json is missing")
        return None
    try:
        data = json.loads(triggers_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        report.add(rel, "parses", False, f"triggers.json is not valid JSON: {exc}")
        return None
    if not isinstance(data, dict):
        report.add(rel, "shape", False,
                   f"triggers.json must be a JSON object, got {type(data).__name__}")
        return None

    ok = True
    result: Dict[str, List[str]] = {}
    for key in TRIGGER_KEYS:
        value = data.get(key)
        if not isinstance(value, list) or not all(isinstance(q, str) for q in value):
            report.add(rel, f"shape.{key}", False,
                       f"'{key}' must be a list of strings")
            ok = False
            continue
        result[key] = value
    if not ok:
        return None

    report.add(rel, "shape", True, "positive/near_miss/holdout string lists present")
    if not result["positive"]:
        report.add(rel, "positive.nonempty", False,
                   "'positive' must contain at least one trigger query")
        return None
    report.add(rel, "positive.nonempty", True)
    return result


def lint_trigger_keywords(triggers: Dict[str, List[str]], description: str,
                          report: EvalReport) -> None:
    """Each positive query must share a meaningful keyword with the description.

    Word-boundary matching, stopwords excluded. Holdout queries are linted
    too (they are positives held out from description editing). TODO
    placeholders pass structurally and skip the lint.
    """
    desc_words = content_words(description)
    for key in ("positive", "holdout"):
        for query in triggers.get(key, []):
            target = f"triggers.{key}: {query!r}"
            if is_placeholder(query):
                report.add(target, "keyword_lint", True, "TODO placeholder (unlinted)")
                continue
            query_words = content_words(query)
            shared = sorted(
                w for w in query_words
                if w in desc_words and phrase_in_text(w, description)
            )
            report.add(
                target, "keyword_lint", bool(shared),
                (f"shares keyword(s) with description: {', '.join(shared)}"
                 if shared else
                 "shares NO meaningful keyword with the skill description - "
                 "this query cannot route to the skill"),
            )


SCENARIO_REQUIRED = ("task", "baseline_failure", "assertions")


def load_scenario(path: Path, report: EvalReport) -> Optional[Dict[str, Any]]:
    """Parse and shape-check one scenarios/*.md file. Returns None if invalid."""
    rel = f"evals/scenarios/{path.name}"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        report.add(rel, "readable", False, f"cannot read: {exc}")
        return None
    fm_text, body = split_frontmatter(text)
    if fm_text is None:
        report.add(rel, "frontmatter", False, "missing YAML frontmatter")
        return None
    fm, error = parse_yaml_mapping(fm_text)
    if error:
        report.add(rel, "frontmatter", False, error)
        return None

    ok = True
    for key in ("task", "baseline_failure"):
        value = fm.get(key)
        if not isinstance(value, str) or not value.strip():
            report.add(rel, f"field.{key}", False, f"'{key}' must be a non-empty string")
            ok = False

    assertions = fm.get("assertions")
    if (not isinstance(assertions, list) or not assertions
            or not all(isinstance(a, str) and a.strip() for a in assertions)):
        report.add(rel, "field.assertions", False,
                   "'assertions' must be a non-empty list of strings")
        ok = False

    runs = fm.get("runs", 1)
    if not isinstance(runs, int) or runs < 1:
        report.add(rel, "field.runs", False, "'runs' must be a positive integer")
        ok = False

    if not ok:
        return None
    report.add(rel, "structure", True,
               f"task + baseline_failure + {len(assertions)} assertion(s), runs={runs}")
    return {
        "name": path.name,
        "task": fm["task"],
        "baseline_failure": fm["baseline_failure"],
        "assertions": assertions,
        "runs": runs,
        "setup_notes": body.strip(),
    }


def run_static(skill_dir: Path, report: EvalReport
               ) -> Tuple[Optional[Dict[str, List[str]]], List[Dict[str, Any]]]:
    """Run all static checks. Returns (triggers, scenarios) for reuse by --live."""
    frontmatter, error = read_skill_frontmatter(skill_dir)
    if error:
        report.add("SKILL.md", "frontmatter", False, error)
        return None, []
    description = str(frontmatter.get("description") or "")
    report.add("SKILL.md", "description.present", bool(description.strip()),
               "" if description.strip() else "SKILL.md has no description to lint against")

    evals_dir = skill_dir / "evals"
    if not evals_dir.is_dir():
        report.add("evals/", "exists", False,
                   "no evals/ directory - skills ship with their tests "
                   "(references/testing-and-evals.md section 6)")
        return None, []
    report.add("evals/", "exists", True)

    triggers = load_triggers(evals_dir, report)
    if triggers is not None and description.strip():
        lint_trigger_keywords(triggers, description, report)

    scenarios_dir = evals_dir / "scenarios"
    scenario_files = sorted(scenarios_dir.glob("*.md")) if scenarios_dir.is_dir() else []
    report.add("evals/scenarios/", "exists", bool(scenario_files),
               "" if scenario_files else
               "no scenarios/*.md files - at least one behavioral scenario is required")

    scenarios = []
    for path in scenario_files:
        scenario = load_scenario(path, report)
        if scenario:
            scenarios.append(scenario)
    return triggers, scenarios


# ===========================================================================
# LIVE MODE
# ===========================================================================

CLAUDE_MISSING_HELP = """\
The `claude` CLI was not found on PATH. --live drives headless runs via
`claude -p` and cannot proceed without it.

To install: https://code.claude.com/docs (npm install -g @anthropic-ai/claude-code)
Then verify with: claude --version

--static mode needs no CLI and is safe to run anywhere (including CI).
"""


def claude_available() -> bool:
    """Probe for a working `claude` CLI."""
    if shutil.which("claude") is None:
        return False
    try:
        probe = subprocess.run(
            ["claude", "--version"], capture_output=True, text=True, timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return probe.returncode == 0


def invoke_claude(prompt: str, max_turns: int, timeout: int) -> Tuple[bool, str]:
    """One headless `claude -p` run. Returns (completed, output).

    Tests monkeypatch this function; keep the signature stable.
    """
    try:
        proc = subprocess.run(
            ["claude", "-p", prompt, "--max-turns", str(max_turns)],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout}s"
    except OSError as exc:
        return False, f"failed to launch claude: {exc}"
    if proc.returncode != 0:
        return False, f"claude exited {proc.returncode}: {proc.stderr.strip()[:500]}"
    return True, proc.stdout


def extract_json(text: str) -> Optional[Any]:
    """Pull the first JSON object out of model output (judges must emit JSON)."""
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        break
        start = text.find("{", start + 1)
    return None


JUDGE_PROMPT = """\
You are a strict evaluator. An agent was given this task:

<task>
{task}
</task>

The agent produced this output:

<output>
{output}
</output>

For EACH assertion below, decide whether the output satisfies it. Quote the
specific evidence (or its absence) that decided your verdict.

Assertions:
{assertions}

Respond with ONLY this JSON, nothing else:
{{"verdicts": [{{"assertion": "<assertion text>", "pass": true, "evidence": "<short quote or reason>"}}]}}
"""

TRIGGER_PROMPT = """\
You are an agent deciding whether to load a skill. The skill roster contains:

  name: {name}
  description: {description}

The user says: {query!r}

Would you load THIS skill for that request? Respond with ONLY this JSON:
{{"triggered": true}} or {{"triggered": false}}
"""


def judge_scenario_run(scenario: Dict[str, Any], output: str,
                       max_turns_judge: int, timeout: int) -> List[Dict[str, Any]]:
    """Judge one scenario run's output against its assertions."""
    assertions_text = "\n".join(f"- {a}" for a in scenario["assertions"])
    prompt = JUDGE_PROMPT.format(
        task=scenario["task"], output=output[:20000], assertions=assertions_text,
    )
    completed, judge_output = invoke_claude(prompt, max_turns_judge, timeout)
    if not completed:
        return [{"assertion": a, "pass": False,
                 "evidence": f"judge run failed: {judge_output}"}
                for a in scenario["assertions"]]
    parsed = extract_json(judge_output)
    verdicts = parsed.get("verdicts") if isinstance(parsed, dict) else None
    if not isinstance(verdicts, list):
        return [{"assertion": a, "pass": False,
                 "evidence": f"judge did not return valid JSON verdicts: "
                             f"{judge_output.strip()[:300]}"}
                for a in scenario["assertions"]]
    # Align verdicts to declared assertions; missing ones fail loudly.
    by_assertion = {str(v.get("assertion", "")).strip(): v
                    for v in verdicts if isinstance(v, dict)}
    results = []
    for i, assertion in enumerate(scenario["assertions"]):
        verdict = by_assertion.get(assertion.strip())
        if verdict is None and i < len(verdicts) and isinstance(verdicts[i], dict):
            verdict = verdicts[i]  # positional fallback when judge paraphrased
        if verdict is None:
            results.append({"assertion": assertion, "pass": False,
                            "evidence": "judge returned no verdict for this assertion"})
        else:
            results.append({"assertion": assertion,
                            "pass": bool(verdict.get("pass")),
                            "evidence": str(verdict.get("evidence", ""))[:500]})
    return results


def run_live_scenarios(scenarios: List[Dict[str, Any]], report: EvalReport,
                       max_turns: int, timeout: int) -> Dict[str, Any]:
    """Execute every scenario headlessly and judge each run's assertions."""
    board: Dict[str, Any] = {}
    for scenario in scenarios:
        name = scenario["name"]
        run_results = []
        for run_index in range(scenario["runs"]):
            completed, output = invoke_claude(scenario["task"], max_turns, timeout)
            if not completed:
                report.add(f"scenario:{name}", f"run{run_index + 1}", False,
                           "scenario run did not complete", evidence=output)
                run_results.append({"run": run_index + 1, "passed": False,
                                    "verdicts": [], "error": output})
                continue
            verdicts = judge_scenario_run(scenario, output, 1, timeout)
            run_passed = all(v["pass"] for v in verdicts)
            for verdict in verdicts:
                report.add(
                    f"scenario:{name}",
                    f"run{run_index + 1}: {verdict['assertion']}",
                    verdict["pass"],
                    "" if verdict["pass"] else "assertion failed",
                    evidence=verdict["evidence"],
                )
            run_results.append({"run": run_index + 1, "passed": run_passed,
                                "verdicts": verdicts})
        board[name] = {
            "runs": run_results,
            "passed": bool(run_results) and all(r["passed"] for r in run_results),
        }
    return board


def run_live_triggers(triggers: Dict[str, List[str]], name: str, description: str,
                      report: EvalReport, timeout: int) -> Dict[str, Any]:
    """Live trigger routing: recall on positives+holdout, precision vs near-misses."""
    def fire(query: str) -> Optional[bool]:
        prompt = TRIGGER_PROMPT.format(name=name, description=description, query=query)
        completed, output = invoke_claude(prompt, 1, timeout)
        if not completed:
            return None
        parsed = extract_json(output)
        if isinstance(parsed, dict) and isinstance(parsed.get("triggered"), bool):
            return parsed["triggered"]
        return None

    positives = [q for q in triggers["positive"] + triggers["holdout"]
                 if not is_placeholder(q)]
    near_misses = [q for q in triggers["near_miss"] if not is_placeholder(q)]

    true_pos = false_neg = false_pos = true_neg = errors = 0
    for query in positives:
        result = fire(query)
        if result is None:
            errors += 1
            report.add(f"trigger:{query!r}", "live_routing", False,
                       "router call failed or returned no JSON verdict")
        elif result:
            true_pos += 1
            report.add(f"trigger:{query!r}", "live_routing", True, "triggered (expected)")
        else:
            false_neg += 1
            report.add(f"trigger:{query!r}", "live_routing", False,
                       "positive query did NOT trigger the skill")
    for query in near_misses:
        result = fire(query)
        if result is None:
            errors += 1
            report.add(f"trigger:{query!r}", "live_routing", False,
                       "router call failed or returned no JSON verdict")
        elif result:
            false_pos += 1
            report.add(f"trigger:{query!r}", "live_routing", False,
                       "near-miss query INCORRECTLY triggered the skill")
        else:
            true_neg += 1
            report.add(f"trigger:{query!r}", "live_routing", True,
                       "not triggered (expected)")

    recall = true_pos / len(positives) if positives else None
    fired = true_pos + false_pos
    precision = true_pos / fired if fired else None
    return {
        "positives": len(positives), "near_misses": len(near_misses),
        "true_positive": true_pos, "false_negative": false_neg,
        "false_positive": false_pos, "true_negative": true_neg,
        "errors": errors, "recall": recall, "precision": precision,
    }


# ===========================================================================
# REPORTING
# ===========================================================================

def format_report(report: EvalReport) -> str:
    lines = [
        f"\n{'=' * 64}",
        f"Skill Evals ({report.mode}): {Path(report.skill_dir).name}",
        f"{'=' * 64}",
    ]
    current_target = None
    for check in report.checks:
        if check.target != current_target:
            current_target = check.target
            lines.append(f"\n{current_target}")
        mark = "PASS" if check.passed else "FAIL"
        detail = f" - {check.message}" if check.message else ""
        lines.append(f"  [{mark}] {check.name}{detail}")
        if check.evidence and not check.passed:
            lines.append(f"         evidence: {check.evidence}")

    if report.scoreboard:
        lines.append(f"\n{'SCOREBOARD':-^64}")
        scenarios = report.scoreboard.get("scenarios", {})
        for name, entry in scenarios.items():
            mark = "PASS" if entry["passed"] else "FAIL"
            lines.append(f"  scenario {name}: {mark} "
                         f"({sum(r['passed'] for r in entry['runs'])}/{len(entry['runs'])} runs)")
        trig = report.scoreboard.get("triggers")
        if trig:
            recall = "n/a" if trig["recall"] is None else f"{trig['recall']:.0%}"
            precision = "n/a" if trig["precision"] is None else f"{trig['precision']:.0%}"
            lines.append(f"  trigger recall:    {recall} "
                         f"({trig['true_positive']}/{trig['positives']} positives fired)")
            lines.append(f"  trigger precision: {precision} "
                         f"({trig['false_positive']} near-miss false fire(s))")

    passed = len(report.checks) - len(report.failures)
    lines.append(f"\nChecks: {passed}/{len(report.checks)} passed")
    lines.append("RESULT: " + ("PASS" if report.passed else "FAIL"))
    lines.append("=" * 64 + "\n")
    return "\n".join(lines)


# ===========================================================================
# CLI
# ===========================================================================

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a skill's evals/ suite (static structure lint or live headless runs)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ~/.claude/skills/my-skill                # static (default)
  %(prog)s ~/.claude/skills/my-skill --static --json
  %(prog)s ~/.claude/skills/my-skill --live --max-turns 12
        """,
    )
    parser.add_argument("skill_dir", type=Path, help="Skill directory containing SKILL.md and evals/")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--static", action="store_true",
                      help="Structure + trigger keyword lint only (default; CI-safe)")
    mode.add_argument("--live", action="store_true",
                      help="Additionally drive headless `claude -p` scenario and trigger runs")
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    parser.add_argument("--max-turns", type=int, default=12,
                        help="Turn cap per headless scenario run (default: 12)")
    parser.add_argument("--timeout", type=int, default=300,
                        help="Seconds before a headless run is killed (default: 300)")
    args = parser.parse_args(argv)

    skill_dir = args.skill_dir.expanduser().resolve()
    if not skill_dir.is_dir():
        print(f"Error: not a directory: {skill_dir}", file=sys.stderr)
        return 1

    live = bool(args.live)
    report = EvalReport(skill_dir=str(skill_dir), mode="live" if live else "static")

    if live and not claude_available():
        print(CLAUDE_MISSING_HELP, file=sys.stderr)
        return 11

    triggers, scenarios = run_static(skill_dir, report)

    if live and report.passed:
        frontmatter, _err = read_skill_frontmatter(skill_dir)
        name = str(frontmatter.get("name") or skill_dir.name)
        description = str(frontmatter.get("description") or "")
        report.scoreboard["scenarios"] = run_live_scenarios(
            scenarios, report, args.max_turns, args.timeout)
        if triggers is not None:
            report.scoreboard["triggers"] = run_live_triggers(
                triggers, name, description, report, args.timeout)
    elif live:
        print("Static checks failed; skipping live runs (fix structure first).",
              file=sys.stderr)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(format_report(report))
    return 0 if report.passed else 10


if __name__ == "__main__":
    sys.exit(main())
