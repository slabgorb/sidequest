# Handoff Prompt — Evropi Starting Kits Implementation

Copy the block below into a fresh Claude Code session (or hand to another agent) to execute the implementation plan. The plan is self-contained; this prompt tells the executor what they're picking up, how to execute, and where the boundaries are.

---

## Prompt

You are picking up a content-authoring implementation plan for the SideQuest project (orchestrator repo `oq-2`, working directory `/Users/keithavery/Projects/oq-2`).

**What you're building:** Character-unique starting kits for five Evropi playgroup characters (Rux, Prot'Thokk, Hant, Pumblestone, Th`rook) plus a Ludzo test-inheritance kit, a Sunday-playable narrator sheet amendment, and a micro-ADR (ADR-081) defining two new `AdvancementEffect` enum variants. Goal: make each character mechanically distinct at turn one so the party doesn't feel like "attack/block/defend/shield bash" at character creation.

**Scope:** Pure content authoring (YAML + Markdown) plus one ADR. **Zero engine code.** All work lands under:
- `docs/adr/081-advancement-effect-variant-expansion.md` (new)
- `docs/adr/README.md`, `docs/adr/078-edge-composure-advancement-rituals.md` (cross-reference updates)
- `sidequest-content/genre_packs/heavy_metal/_drafts/edge-advancement-content.md` (ADR reference hygiene)
- `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/` (5 existing YAMLs + 1 new `th_rook.yaml` + README)
- `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/sunday-progression.md` (append Th`rook section)

**Plan path:** `docs/superpowers/plans/2026-04-18-evropi-starting-kits.md`

**Spec path (read first for context):** `docs/superpowers/specs/2026-04-18-evropi-starting-kits-design.md`

**Branch:** `feat/37-17-stat-name-casing-drift` — stay on this branch. Keith approved leaving unrelated design commits here rather than reorganizing.

**Execution approach:** Subagent-driven. Dispatch one fresh subagent per task from the plan, review the diff between tasks, hold a tight feedback loop. Use the `superpowers:subagent-driven-development` skill.

**Non-negotiables:**

1. **No engine code.** Content-only. If a task seems to require Rust/TypeScript/Python changes, stop and check — you're off-plan.
2. **Commit after every task.** The plan prescribes exact commit messages; use them (or close variants). Every commit must include `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`.
3. **Do not amend existing commits.** Create new commits. Never use `--no-verify` or `--amend` unless explicitly told.
4. **YAML validation gate.** After every character YAML edit, run `python3 -c "import yaml; yaml.safe_load(open('<path>'))"` and confirm clean parse. The project also has a `pf hooks schema-validation` PreToolUse hook that runs automatically on Write — if it blocks, respect the blocker.
5. **Cross-reference hygiene.** Task 13 is a mandatory audit — do not skip it. If any grep audit finds stale references, fix them inline before claiming completion.
6. **Name placeholder.** Th`rook is a placeholder name (Keith is checking with Sebastien whether a canonical name already exists). The YAML uses `th_rook` / `Th`rook` consistently. Do not rename without Keith's direct input.
7. **Ludzo is a test character.** His YAML's starting_kit uses `inherits: rux`, not its own grants. Do not design party-tension content involving Ludzo — he is QA sandbox only.

**Key design context for understanding the content:**

- **ADR-078** defined the `AdvancementEffect` enum with five day-1 variants (`EdgeMaxBonus`, `BeatDiscount`, `LeverageBonus`, `EdgeRecovery`, `LoreRevealBonus`). ADR-081 adds exactly two more: `AllyEdgeIntercept` (Prot'Thokk's *Lil' Sebastian Stands*) and `ConditionalEffectGating` (Th`rook's *The Dose Helps*). Everything else requested during drafting is explicitly deferred to ADR-082+.
- **ADR-079 numbering conflict:** ADR-078 originally reserved "ADR-079" for these variants, but ADR-079 was subsequently claimed by *Genre Theme System Unification* (Accepted). The plan includes sweeps to retarget all stale ADR-079 references to ADR-081 (for the two landing variants) or ADR-082+ (for everything else deferred).
- **Reniksnad vs. Pę:** reniksnad is the addictive drug fed to Pakook`rook slaves; **Pę** is the Zkędzała slave-city where the drug is administered. Do not confuse them — the spec was corrected mid-brainstorm for this exact reason. Th`rook's character_resource is `reniksnad`; Pę appears only in prose contexts (his birthplace).
- **Character-scoped resources are a new schema pattern.** Voice/Flesh/Ledger are genre-level (`rules.yaml`); reniksnad is character-level (`character_resources:` block in `th_rook.yaml`). The Epic 39 story 5 hydration loader handles both at chargen.
- **Sunday playability is a hard target.** Keith plays this upcoming Sunday. The `sunday-progression.md` sheet is the GM-fiat fallback that runs under any circumstances, including Epic 39 not having landed. Every content deliverable must be usable at the table via that sheet even if no engine changes are made.

**How to start:**

1. Read the spec: `docs/superpowers/specs/2026-04-18-evropi-starting-kits-design.md`.
2. Read the plan: `docs/superpowers/plans/2026-04-18-evropi-starting-kits.md`.
3. Invoke the `superpowers:subagent-driven-development` skill with the plan path as the argument.
4. Proceed through the 13 tasks. Stop and report between tasks per the subagent-driven pattern.

**Stopping conditions:**

- A task's YAML fails to parse and the cause is unclear — stop, report, await guidance.
- A cross-reference sweep surfaces an unexpected reference (e.g., ADR-079 in a file the plan didn't name) — stop, report, confirm the intended fix before making it.
- The `pf hooks schema-validation` hook blocks a Write — stop, read the hook's error output, report what the hook is demanding before proceeding.
- Any step seems to require engine code — stop, confirm with Keith that you're still on-plan.

**Definition of done:**

- All 13 tasks' checkboxes ticked in the plan
- Task 13's audit sign-off commit landed with all grep/parse checks clean
- 13 commits on `feat/37-17-stat-name-casing-drift` branch, each scoped to one task
- No uncommitted changes

Good luck. The plan is thorough; trust it. If something feels off, stop and ask rather than improvise.

---

## End of prompt

Paste everything between "## Prompt" and "## End of prompt" into the fresh session.
