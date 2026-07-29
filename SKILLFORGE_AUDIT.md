# SkillForge 5.2 - Deep Audit & Upgrade Roadmap

Audited 2026-07-29 against: official Claude Code docs, Anthropic's official skill-creator, superpowers writing-skills 6.2.0, plugin-dev skill-development, the agentskills.io spec, and full source review (SKILL.md, 9 references, 15 scripts, templates, live E2E runs on this machine).

Method: four independent review passes (docs fact-check, script-layer code review with E2E execution, methodology/consistency audit, competitive analysis) plus direct review of SKILL.md against skill-authoring best practices.

---

## Executive summary

SkillForge has three genuinely original ideas that no competitor has, wrapped in a quality apparatus that is largely ceremony, documentation with 26+ internal inconsistencies, factually outdated claims about Claude Code, and a script layer whose two most important components (discovery and matching) are measurably broken on this machine.

The defining gap: **SkillForge never runs the skills it creates.** Its 4-agent "unanimous synthesis panel" reads prose. The field converged on the opposite: Anthropic's official skill-creator spawns with-skill and baseline subagents and benchmarks the delta; superpowers requires a failing baseline test before a skill may even be written. SkillForge optimizes documents about a skill, never the skill's behavior.

Scorecard (1-10):

| Dimension | Score | Note |
|---|---|---|
| Original ideas | 9 | Triage, proactive advisor, rationale spec - unique in the field |
| Ecosystem awareness | 7 | Only system that dedups before creating; but index misses the real plugin cache |
| Methodology rigor | 3 | Unfalsifiable self-scored gates; panel cannot execute as configured |
| Factual accuracy | 4 | 10 of 17 frontmatter fields documented; hooks interface described wrong |
| Script quality | 3 | Fails its own validator; substring matching; scheduler is a no-op |
| Context economy | 3 | ~12k tokens per invocation; `<details>` tags save zero tokens for agents |
| Testing of outputs | 1 | Nothing executes generated skills, ever |
| Privacy posture | 4 | Personal-dir scanning opt-out by default; plaintext excerpt accumulation |

---

## 1. What is genuinely good (keep and double down)

1. **Phase 0 ecosystem triage.** No competitor asks "should this skill exist?" SkillForge indexes skills across four runtimes and routes any input through USE / IMPROVE / CREATE / COMPOSE / CLARIFY. In a 300-skill ecosystem, dedup-before-create is the scarce capability. This should become the product's front door and headline.
2. **The Context Skill Advisor concept.** Proactive, evidence-backed skill suggestions with user-controlled proactivity levels, a persistent queue, and feedback actions (use/snooze/dismiss/never). Nothing else in the field does proactive skill surfacing. The concept is right; the implementation is a no-op (see 3.4) and the privacy defaults are wrong (see 3.7).
3. **Design-rationale capture.** The XML spec with per-decision WHY, alternatives considered, obsolescence triggers, and extension points produces a durable design record no competitor has. Anthropic's skill-creator iterates empirically but leaves no rationale artifact. Keep it - but as a complement to behavioral evidence, not a substitute.
4. **Two orphaned references are the best files in the repo.** `references/degrees-of-freedom.md` (matching instruction specificity to task fragility) and `references/iteration-guide.md` (use the skill on a real task, then re-test) are the most Claude-native, highest-signal documents - and SKILL.md never links either one.
5. **Correctly documents two advanced, real features.** `context: fork` + `agent:` and hooks-in-skill-frontmatter with `once: true` are real, current Claude Code features most skill authors don't know exist. SkillForge gets their existence right (though it gets the hook I/O interface wrong - see 3.5).

---

## 2. The defining methodological gap

**No phase ever executes the generated skill.** Verdicts on the pipeline as an executable procedure for an LLM agent:

| Phase | Verdict | Why |
|---|---|---|
| Phase 0 triage | Load-bearing concept, theatrical numbers | Backed by a real script, but "confidence %" is keyword-overlap arithmetic presented as calibrated probability, and the documented thresholds contradict each other (80/50 matrix vs a 60% table vs a 0-10 scale in Phase 1A) |
| Phase 1: 11 thinking lenses | Mostly ritual | Three lenses do real work (Inversion → anti-patterns, Pareto → scoping, Root Cause → right problem). The other eight generate fluent filler that changes no design decision. Compliance is unverifiable self-report |
| Phase 1C: regression questioning until "3 empty rounds" | Theater as a gate, useful as a question bank | Termination is unfalsifiable: an LLM can always emit "new insights" or declare emptiness. The question bank itself is good prompting material |
| Phase 2: XML spec | Partially load-bearing | Spec-before-generation is the soundest idea in the pipeline. But mandatory 6mo/1yr/2yr/5yr projections force confabulation for small utility skills |
| Phase 3: generation "with fresh context" | Theater as specified | No mechanism exists. `synthesis-protocol.md` explicitly says all phases run in shared context, and `allowed-tools` excludes the Task tool that could fork one. The claim is impossible as configured |
| Phase 4: unanimous panel of 3-4 Opus agents | Mostly theater | (a) Cannot run - no Task tool granted. (b) Same-model agents spawned by a parent that wants approval, with approval-shaped prompt templates, converge to approval. (c) Weighted criterion scores are pseudo-quantification. (d) All review is static reading |
| Timelessness score >= 7 gate | Grade-your-own-homework | The generating model scores its own artifact; the approve band starts exactly at the required 7. Predictable outcome: every skill gets 7-8 with a fluent justification. The falsifiable fragments (pinned versions, missing extension points) should be lint instead |

The panel-doc even claims subagents "share full history" with the parent - factually wrong about Claude Code (subagents receive only their prompt), so the entire shared-vs-forked analysis rests on a false platform premise.

---

## 3. Critical defects (ranked)

### 3.1 It fails its own validator, and its two validators disagree
`validate-skill.py` rejects SkillForge's own SKILL.md: `user-invocable must be a boolean (got str)`. Root cause: a hand-rolled YAML fallback parser (`validate-skill.py:83-131`) that stores every value as a string - and since PyYAML is not installed on this machine, the fallback is the *default* path. The same broken parser is copy-pasted into `quick_validate.py` (which passes the same skill - exit 0) and a third variant lives in `discover_skills.py`. `package_skill.py` gates on the lenient one, so packaging ships skills the full validator rejects. The parser also can't read YAML lists (producing the nonsense warning `Unknown tool(s): ['']`) and keeps quotes on quoted scalars.

### 3.2 Skill discovery misses the actual Claude Code plugin cache
`discover_skills.py` scans `~/.codex/plugins/cache` but not `~/.claude/plugins/cache`, where Claude Code plugin skills actually live. On this machine: **726 SKILL.md files in the real cache, 0 indexed**; the index holds 173 skills, mostly from Codex paths. Three of eight configured sources are dead paths. The index also never goes stale-and-rebuilds (only rebuilds if the file is missing), has no dedup (13 names duplicated; triage output shows the same skill twice in a top-5), and SKILL.md's "250+ skills" claim doesn't match reality.

### 3.3 Matching is substring soup, so triage rankings are near-meaningless
`classify_domain` and description scoring use raw substring matching: `"ai"` matches "email", `"ml"` matches "html", `"ci"` matches "specialist". Measured result: the ai_ml domain is assigned to 90% of indexed skills, average 7.2 domains per skill. E2E: `triage_skill_request.py "create a skill for code review"` recommends **vercel-agent at 87% confidence**. The codebase already contains a correct word-boundary helper (`phrase_in_text`) and doesn't use it in these paths. Substring inflation also triggers spurious COMPOSE decisions.

### 3.4 The proactive advisor's scheduled mode is a functional no-op
The launchd integration is real (plist written and loaded), but: the plist runs `context_advisor.py run` with no `--cwd`, so every scheduled run analyzes `/` and queues nothing, forever (reproduced: 0 suggestions). Even if it queued something, nothing consumes the queue - the snippet appended to `~/.claude/CLAUDE.md` only tells agents to run `checkpoint`, which never reads `advice.jsonl`. `max_daily` limits are enforced nowhere. The headline v5.2 feature burns a Python process every 2 hours to accomplish nothing.

### 3.5 The frontmatter/hooks documentation is outdated and partly wrong
Fact-checked against current official docs:
- Documents only 10 of 17 supported frontmatter fields. Missing: `when_to_use`, `argument-hint`, `arguments`, `disable-model-invocation`, `disallowed-tools`, `effort`, `background`, `paths`, `shell`.
- Hook I/O is described wrong: SKILL.md says to read `$TOOL_INPUT`/`$TOOL_OUTPUT` env vars; Claude Code hooks deliver JSON on stdin. The matcher example `"Bash(python:scripts/*)"` uses permission-rule syntax, not hook matcher syntax. As written, the flagship hooks examples would not fire correctly.
- The validator's "64-char name / 1024-char description / no angle brackets" constraints come from the agentskills.io spec, not Claude Code docs (Claude Code's actual cap is 1,536 chars combined description + when_to_use in listings). Fine as a portability target, but it should say so - and `license`/`metadata` are agentskills.io fields, not Claude Code ones.
- `model: claude-opus-4-5-20251101` is pinned in SkillForge's frontmatter, twice in its config block, and **baked into every generated skill** via `skill-md-template.md` - while its own evolution-scoring rubric penalizes hardcoded model IDs at -1. Every SkillForge output starts life violating SkillForge's own timelessness rules.

### 3.6 Description doctrine is wrong, and triggering effort goes to a dead surface
SkillForge's description guidance is "What this skill does and when to use it," and its template ships a bare placeholder. Best current practice (validated by wording tests in superpowers, and by Anthropic's description-optimization loop): descriptions should be triggering-conditions-forward, third person, symptom-rich - and must not summarize workflow, because agents follow the summary and skip the body. SkillForge's own description is the exhibit: "Analyzes ANY input..." is marketing copy with no trigger discrimination, and an over-trigger hazard in a large roster. Meanwhile the mandated body "## Triggers" section (3-5 phrases, enforced by the validator as a hard error) does nothing for invocation - the body is only read after the skill fires. The methodology channels triggering effort into a surface that has no mechanical effect.

### 3.7 Privacy defaults are wrong
- Personal Context (ripgrep sweeps of `~/kb`, `~/Documents/Work`, `~/Projects`, plus GitHub metadata) is **opt-out**, enabled by default, on a schedule as aggressive as every 30 minutes.
- `DEFAULT_CONFIG` hardcodes `"owner_limit": ["tripleyak", "jackatlasov"]` - personal GitHub handles shipped to every installer, causing `gh repo list` network calls on every checkpoint for anyone who installs.
- 700-char excerpts from personal files are persisted in plaintext to `~/.local/share/skillforge/advice.jsonl`. Exclusions are pattern-based only; a loose `passwords.txt` in a scanned directory is fair game for excerpting.
- The README's recommended install is `curl | bash` from an unpinned main branch, and the installer appends to global `~/.claude/CLAUDE.md`, loads a LaunchAgent, and runs the first personal-directory scan at install time, all without prompting.
- (Positive: no exfiltration - everything stays local; subprocess calls use list args, no shell=True.)

### 3.8 Internal consistency is poor (26 documented contradictions)
Highlights: frontmatter says v5.2.0 while the in-file changelog's newest entry is "v4.1.0 (Current)"; panel size is "3-4" in SKILL.md but hardcoded 3 in synthesis-protocol.md with no Script Agent prompt template; three incompatible match-threshold scales (80/50%, 60%, 0-10); the Phase 3 quality check lists 5 allowed frontmatter properties while the frontmatter section lists 10; the config block is still named `SKILLCREATOR_CONFIG`; the index path says `skillrecommender`; two spec templates have diverged (only the XML has `<scripts>`, only the MD has `<data_flow>`); exit-code canon differs across four files; generated-skill structure is specified three incompatible ways.

### 3.9 Context economy contradicts the teaching
SKILL.md is 5,049 words (~11-13k tokens with ASCII diagrams) loaded on every invocation. The four Deep Dive `<details>` blocks duplicate the references nearly verbatim - and `<details>` collapsibility saves zero tokens for an agent; it is progressive disclosure theater. The pipeline then re-reads the references containing the same content a second time. A router/creator core fits in ~1,500 words. Estimated waste: ~8-10k tokens per invocation, from a skill whose founding principle is "the context window is a public good."

### 3.10 Script hygiene
16 unit tests pass, but zero tests cover the two most defect-dense files (validate-skill.py, discover_skills.py). SkillForge's validator emits 11 warnings against SkillForge's own scripts (missing Result pattern, exit codes) and enforces argparse on other skills while three of its own scripts use raw `sys.argv`. Three copies of `Result`, two of `get_index_path`, a DOMAIN_SYNONYMS/DOMAIN_KEYWORDS pair whose comment says "MUST match" with no enforcement (already drifted). `validate-skill.py`'s hyphenated filename is why its parser got copy-pasted instead of imported. `.skillignore` semantics silently differ between `package_skill.py` (ignores `dir/` patterns) and `install_workshop.sh` (rsync honors them).

---

## 4. Upgrade roadmap: how to make this the best skill creator in existence

The strategy in one line: **SkillForge already owns the "before" (should this exist?) and the "meta" (why is it designed this way?). Marry that to the field's converged practice - empirically running skills against baselines - and add a closed learning loop nobody has, and it is strictly stronger than everything currently available.**

### Tier 1 - Fix the foundation (days)

1. **One real YAML parser.** Require PyYAML or vendor a correct minimal parser (booleans, lists, quoted scalars); share it across all three scripts; add the one regression test that would have caught everything: "SkillForge's own SKILL.md must pass validate-skill.py."
2. **Fix discovery.** Add `~/.claude/plugins/cache/**/skills/*/SKILL.md`, delete dead sources, dedupe by name with the existing priority field, rebuild on staleness (mtime), not just absence.
3. **Kill substring matching.** Use the existing `phrase_in_text` word-boundary helper in domain classification and description scoring. This single change fixes most ranking garbage.
4. **Cut SKILL.md to ~1,500 words.** Delete the four Deep Dive blocks (they duplicate references verbatim), the changelog, one of two ASCII pipeline diagrams, and the hooks tutorial (point to the reference). Link the two orphaned references. Saves ~8-10k tokens per invocation.
5. **Correct the platform facts.** All 17 frontmatter fields; hooks read stdin JSON; fix matcher syntax; label the 64/1024 constraints as agentskills.io portability rules; unpin `model:` everywhere (frontmatter, config, template); reconcile the version story and the 26 contradictions (single source of truth: the scripts' actual thresholds).
6. **Grant the tools the pipeline needs.** Add Task to `allowed-tools` (or drop the phases that require it). Phase 3/4 must be executable as written.

### Tier 2 - Adopt the field's converged practice (the big one, ~1-2 weeks)

7. **Baseline-first (RED) gate.** Before writing any skill: run the target scenario with a subagent WITHOUT the skill and capture verbatim behavior. If the baseline doesn't fail, don't create the skill. This is an empirical necessity-check that complements Phase 0's index-based dedup - and it is the cheapest, highest-value addition available (from superpowers' Iron Law).
8. **Execution testing (new Phase 3.5).** Run the generated skill on 2-3 representative tasks via forked subagents, with a baseline run for comparison; gate on behavioral delta; feed transcripts, not prose, to the reviewer (from Anthropic's skill-creator eval loop).
9. **Description optimization loop.** Generate ~20 realistic trigger + near-miss queries, 60/40 train/test split, iterate the description against failures, select by held-out score. Makes triggering measurable instead of vibes (Anthropic's `run_loop.py` pattern).
10. **Make "fresh context" real.** Generate in a forked subagent (`context: fork`) that receives only the XML spec. This is what the spec artifact exists for - it finally becomes load-bearing.
11. **Replace the panel with one adversarial reviewer + lint.** Convert every falsifiable rubric fragment (pinned model IDs, missing WHY, <2 extension points, token budget via `wc -w`, description-shape rules) into `validate-skill.py` checks. Keep a single fresh-context adversarial reviewer prompted to REFUTE, carrying the three existing checklists. Unanimity among three same-model agents primed by approval-shaped templates measures nothing; a refutation-framed reviewer plus mechanical lint measures something.
12. **Blind A/B for IMPROVE_EXISTING.** Old vs new skill outputs judged by an agent that doesn't know which is which - proof the improvement improved something (Anthropic's comparator pattern).
13. **Adopt the failure-type taxonomy.** Classify what kind of failure a skill guards against (rule-skipping vs wrong-shaped output vs omission vs conditional) and pick the guidance form accordingly - prohibitions + rationalization tables for discipline, recipes for shaping, structural slots for omissions (superpowers' "Match the Form to the Failure," which has empirical backing that prohibitions backfire on shaping problems).

### Tier 3 - Rebuild the differentiators on Claude-native mechanics (~2-4 weeks)

14. **Replace launchd with Claude Code hooks.** The advisor's entire delivery problem dissolves if it runs where the agent already is: a `SessionStart` hook surfaces queued suggestions at session open; a `UserPromptSubmit` hook does the checkpoint scoring inline (exactly how the scout-radar hook works on this machine). No daemon, no dead queue, no cwd bug - and suggestions arrive in-context, where they can actually be acted on.
15. **Privacy: flip to opt-in.** Personal paths and GitHub owners empty by default, chosen at install; consent-before-read, not sensitivity-notes-after; encrypt or at least scope the advice queue; drop `curl | bash` for a pinned-release installer that prompts before touching global CLAUDE.md or LaunchAgents.
16. **Triage as the front door, honestly labeled.** Keep USE/IMPROVE/CREATE/COMPOSE/CLARIFY, source thresholds from the script, and stop presenting keyword overlap as calibrated confidence - report "strong/weak keyword match" bands instead.
17. **Tiered spec.** Minimal tier (problem, requirements, decisions + WHY, success criteria) for small skills; full tier (temporal projection, obsolescence triggers) only for infrastructure skills. Mandatory ungroundable sections force confabulation.

### Tier 4 - Capabilities nobody has (the "best in the world" layer)

18. **Skills ship with their own eval suite.** Every generated skill gets an `evals/` directory: trigger queries (positive and near-miss), behavioral scenarios, and expected-property assertions. Regression testing for skills becomes possible: after any edit, re-run the suite. No system in the field does per-skill regression evals today - this is the single most defensible upgrade.
19. **Closed-loop learning from real usage.** Mine session transcripts (locally, with consent) for skill friction: skills that triggered and were abandoned, tasks where no skill fired but one should have, repeated manual work that should become a skill. Feed this into the Advisor as evidence and into IMPROVE_EXISTING as change candidates. This turns the Advisor from keyword-matcher into a flywheel: usage → evidence → improvement → usage.
20. **Ecosystem health dashboard.** The index already exists; add `skillforge doctor`: duplicate/overlapping descriptions across the roster (trigger-collision detection between skills - nobody does this), stale skills referencing dead files or deprecated APIs, description-shape lint for every installed skill, token-budget report. SkillForge becomes the maintainer of the whole skill ecosystem, not just a creator.
21. **Cross-runtime compilation.** Author once against the agentskills.io spec, compile per-target: Claude Code (17-field frontmatter, hooks, fork), Codex, plain agentskills. The multi-runtime ambition is already in the repo; make it a deliberate compile step instead of lowest-common-denominator authoring.
22. **CI integration.** A GitHub Action template that runs validate + eval suite on every skill-repo PR, so shared skill libraries get the same regression discipline as code.

---

## 5. Post-install notes for this machine

- Installed: `~/.claude/skills/skillforge` (repo-only files stripped per README) and `/skillforge` command at `~/.claude/commands/skillforge.md`. Registered and visible to Claude Code.
- Working clone: `~/Skills/skillforge`.
- Known caveat: `validate-skill.py` fails on the skill itself (defect 3.1) - cosmetic for usage, but real.
- **Deliberately not done:** `install_workshop.sh` and `install_skillforge.py` were not run. They would load a LaunchAgent, append to your global `~/.claude/CLAUDE.md`, and start scanning `~/Documents/Work`, `~/kb`, `~/Projects` and GitHub on a schedule - given defects 3.4 and 3.7, the advisor delivers nothing in exchange for that footprint. Recommend leaving it off until Tier 3 fixes land.
- Note: `DEFAULT_CONFIG` in `skillforge_config.py` hardcodes the GitHub handles `tripleyak` and `jackatlasov` as repo-scan targets for every installer of this public repo - worth flagging to the repo owner regardless of anything else.
