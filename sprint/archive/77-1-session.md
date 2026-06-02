---
story_id: "77-1"
jira_key: ""
epic: "77"
workflow: "trivial"
---

# Story 77-1: [DESIGN] Quest & stakes substrate — ADR for create/anchor lane + active_stakes source

## Story Details

- **ID:** 77-1
- **Epic:** 77 (Quest & Stakes Substrate)
- **Jira Key:** (none — Jira not enabled for this project)
- **Workflow:** trivial (phased, 4 phases: setup → implement → review → finish)
- **Repos:** server, ui
- **Points:** 3
- **Priority:** p2

## Delivery Context

This is a **[DESIGN] story** — deliverable is an ADR + implementation-story breakdown, **no production code**. The repos field (server,ui) reflects where the future implementation will land, not where this design work happens.

### Epic Summary

Epic 77 surfaces a critical playtest gap discovered in wry_whimsy/oz (2026-06-02): after 13 turns with an explicit campaign spine ("go home"), the engine showed:
- `quest_log: {}`
- `quest_anchors: []`
- `active_stakes: ""`
- `active_seeds: []`

The player's objective was captured in footnotes but never promoted to a quest anchor or active stake, leaving the engine with no mechanical stakes to drive pacing/escalation (ADR-024/025/128). The session ran on narrator improvisation with zero mechanical backing.

### Root Causes (Dev Smith Analysis)

Four fields, four distinct problems:

1. **quest_anchors** — ZERO write paths. Read into narrator context (orchestrator.py:2413) + shipped to client (session_helpers.py:1230) but never assigned. Not even a WorldStatePatch field → **structurally dead read-only field**.

2. **quest_log** — Two write lanes, both dormant:
   - Narrator quest_updates (narration_apply.py:2862) only UPDATES a quest by id; nothing CREATES one.
   - Trope-resolution handshake (narration_apply.py:5765) writes `quest_log["trope_{id}"]` but requires a resolved trope (`total_beats_fired:0` → never fired).

3. **active_stakes** — Written only by:
   - Trope handshake (didn't fire in prose-only pack).
   - DEPRECATED `apply_world_patch` escape hatch (narrator explicitly told NOT to use; deprecation criterion = zero uses).
   - **No first-class "set the current stakes" affordance in normal play.**

4. **active_seeds** — CONTENT gap, not engine. Wry_whimsy authors no seed_tropes (only tea_and_murder does). ADR-128 seed deck simply not authored. **Carved out as a separate content task, NOT solved here.**

### Core Engine Gap

- There is a lane to UPDATE a quest but no mechanism to CREATE/anchor one.
- Stakes only flow from tropes that never fire in a prose-only pack.
- No client component renders quests/quest_log/quest_anchors/active_stakes.

## Story Acceptance Criteria

1. **ADR drafted:** Defines the CREATE/anchor lane for quest_log + quest_anchors and the first-class source for active_stakes, with a decision among options A (seed-at-creation) / B (typed narrator tool) / C (both) / D (full-stack + UI panel) and the rationale.

2. **quest_anchors fate:** Promote to a first-class WorldStatePatch field with a write path, OR retire the dead read-only field (no structurally-dead fields left).

3. **One-mechanism resolution:** The dead legacy quest_updates lane and the deprecated apply_world_patch escape hatch are reconciled (retired/replaced), not left coexisting with a new tool.

4. **OTEL spans:** Specifies the OTEL span(s) for quest-create + stakes-set (GM-panel lie-detector), per the OTEL Observability Principle (CLAUDE.md).

5. **Implementation stories:** Enumerates the implementation stories to spawn under epic 77 (engine, and optional UI quest/objective panel) with point estimates.

6. **active_seeds carve-out:** Explicitly carved out as a SEPARATE content task (author a wry_whimsy seed_tropes deck, ADR-128; delegate to a gm agent) — referenced in the ADR, not solved here.

## Design Options to Weigh

(Per Dev Smith sketch — to be evaluated and decided in the ADR):

- **Option A: Seed-at-creation** — Write one quest_anchor + active_stakes at session init from the PC's drive/calling. Smallest scope, server-only, +OTEL span.

- **Option B: Typed narrator tool (ADR-102)** — set_stakes / record_quest so the narrator creates+evolves quests in play, replacing the dead legacy lane + the discouraged escape hatch (one-mechanism-per-problem).

- **Option C: Both server fixes** — A + B together.

- **Option D: Full-stack** — C plus a client quest/objective panel. (Note: `quests` field exists in payloads.ts / GameStateProvider but displays nowhere today.)

### Related ADRs in Scope

- ADR-102 (tool-use protocol — narrator tools as structured output)
- ADR-024/025 (tension & pacing models that consume active_stakes)
- ADR-128 (seed deck governance)
- One-mechanism-per-problem principle (don't leave dead legacy lane + escape hatch + new tool all live simultaneously)

## Workflow Tracking

**Workflow:** trivial (phased)
**Phase:** finish
**Phase Started:** 2026-06-02T19:46:51Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-02 | 2026-06-02T19:35:09Z | 19h 35m |
| implement | 2026-06-02T19:35:09Z | 2026-06-02T19:41:02Z | 5m 53s |
| review | 2026-06-02T19:41:02Z | 2026-06-02T19:46:51Z | 5m 49s |
| finish | 2026-06-02T19:46:51Z | - | - |

## Sm Assessment

**Setup Complete:** Yes
**Session file:** created with full Delivery Context, root-cause analysis, 6 ACs, design options A–D, related ADRs.
**Branch:** `feat/77-1-quest-stakes-substrate-design` (created)
**Status:** epic-77.yaml → in_progress
**Context:** story scope captured in this session file (DESIGN story — ADR + implementation-story breakdown, no production code).

**Note (workflow-type correction):** `sm-setup` mis-reported this story's `workflow_type` as `stepped`; `pf workflow type trivial` and `pf workflow show trivial` both confirm `trivial` is **phased** (setup → implement → review → finish). The "stepped" strings in this file were corrected to "phased" so the phased handoff chain (resolve-gate → complete-phase → marker) works. Setup gate `sm_setup_exit` resolves `ready`.

**Handoff:** To implement phase (dev / Agent Smith).

## Dev Assessment

**Implementation Complete:** Yes (DESIGN deliverable — ADR + story breakdown, no production code)
**Files Changed:**
- `docs/adr/137-quest-stakes-substrate.md` — NEW. The ADR. Code-grounded root cause (all four fields verified against `sidequest-server` HEAD), decision (Option C engine-core + Option D UI as fast-follow), quest_anchors promotion, one-mechanism consolidation, OTEL span table, 6-story breakdown, active_seeds carve-out.
- `docs/adr/README.md` — regenerated by `scripts/regenerate_adr_indexes.py` (ADR-137 indexed; 137 ADRs loaded). SUPERSEDED.md/DRIFT.md/CLAUDE.md rewritten but unchanged (no diff).

**Verification (Verify Wiring, Not Just Existence):**
- `quest_anchors` — confirmed ZERO write paths (grep for assignment/append/setattr empty), absent from `WorldStatePatch` (`session.py:420`), yet read in 4 sites + consumed by `orbital/course.py:125,157` (ADR-130). Dead field, live consumer → ADR decision is PROMOTE not retire.
- `active_stakes` — confirmed writers are only `apply_world_patch.py:195` (deprecated escape hatch) + trope handshake `narration_apply.py:5812`.
- `quest_log` — confirmed live narrator lane (`narration_apply.py:2872`) sets `{quest_id: status}` (update), no mint-a-structured-quest affordance; trope lane (`:5805`) needs a fired trope.
- `WorldStatePatch` fields read directly from `session.py:420-451`.

**Acceptance Criteria:** 6/6 addressed —
1. ADR drafted with A/B/C/D decision + rationale ✓
2. quest_anchors fate decided (promote → first-class WorldStatePatch field, story 77-4) ✓
3. One-mechanism resolution (retire quest_updates lane + strip quest/stakes from apply_world_patch, story 77-5) ✓
4. OTEL spans specified (5-span table) ✓
5. Implementation stories enumerated with points (77-2…77-7) ✓
6. active_seeds carved out as content task 77-7 (delegate to gm) ✓

**Tests:** N/A — DESIGN story, no code. ADR validated by `regenerate_adr_indexes.py` (frontmatter schema, ADR-088).
**Branch:** `feat/77-1-quest-stakes-substrate-design` (to be pushed)

**Handoff:** To review phase (reviewer / The Merovingian).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 1 (I-1 minor) | confirmed 1, dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | Yes | clean | 2 impl-notes | confirmed 2 (as fwd findings), dismissed 0, deferred 0 |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings |

**All received:** Yes (2 enabled subagents returned; 7 disabled via `workflow.reviewer_subagents` and pre-filled as Skipped)
**Total findings:** 3 confirmed (all non-blocking, carried to implementation stories), 0 dismissed, 0 deferred

## Reviewer Assessment

**Verdict:** APPROVED

This is a DESIGN story; the deliverable is ADR-137 (markdown), no production code. The
review focus is therefore (a) are the ADR's "code-grounded" claims actually true, (b)
is the decision sound against the 6 ACs, (c) does it honor project rules. I
independently re-traced every code citation rather than trusting the Dev assessment.

### Independent claim verification (cause → effect)

- **[VERIFIED] `quest_anchors` has zero write paths** — grep for `.quest_anchors =`,
  `.append`, `.extend`, `setattr`, dict-literal keys (excluding field defaults)
  returns empty across `sidequest-server/sidequest/`. The ADR's central premise holds.
- **[VERIFIED] `quest_anchors` is a live, wired consumer** — `orbital/course.py:157`
  iterates `quest_anchors` and assigns `CourseSource.QUEST_OBJECTIVE` (top selection
  priority, preserved under the 12-entry cap). `compute_courses(quest_anchors=…)` is
  called at `orchestrator.py:2413`, `session_helpers.py:1230`, `narration_apply.py:1974`.
  The consumer is fully built but **starved** — it always receives `[]` because nothing
  writes the field. This makes the ADR's "promote, don't retire" decision *more* correct
  than stated: promoting the field activates dormant-but-complete downstream machinery.
- **[VERIFIED] `active_stakes` writers are only the deprecated escape hatch + trope
  handshake** — `apply_world_patch.py:195` and `narration_apply.py:5812`. Confirmed.
- **[VERIFIED] `quest_log` live lane is update-only** — `narration_apply.py:2872`
  `snapshot.quest_log[quest_id] = status`; no mint-a-structured-quest affordance.
- **[VERIFIED] UI `quests` field exists** — `sidequest-ui/src/types/payloads.ts:46`
  `quests?: Record<string, string>`; `GameStateProvider.tsx` present. Story 77-6 is grounded.
- **[VERIFIED] `SPAN_QUEST_UPDATE` exists** — `telemetry/spans/state_patch.py:29`. The
  ADR's "`quest.updated` replaces SPAN_QUEST_UPDATE" claim is accurate.

### Observations

1. **[MEDIUM] Option A's source is empty in the motivating pack.** `character.py:117
   drive: str = ""` exists, but `builder.py:423` populates it only for genres with a
   *drive-shaped scene*. wry_whimsy (prose-only, the pack that triggered epic 77)
   likely has no drive scene → seed-at-creation yields an empty seed in exactly the
   case the ADR exists to fix. Option B is the load-bearing fix for prose packs; A is
   belt-and-suspenders. The ADR acknowledges the empty-drive risk (line 182-184) but
   frames it as an edge case, not *the* case. Non-blocking — the decision (C) survives
   because B covers it — but 77-2's AC should verify behavior against a no-drive pack.
2. **[SEC] [LOW] Unbounded narrator-controlled state.** `record_quest`/`set_stakes`
   (77-3) persist narrator strings to Postgres via `WorldStatePatch`. The ADR delegates
   bounds to ADR-102 but doesn't quantify them. A concrete mechanism already exists —
   `_ACTIVE_STAKES_GUARDRAIL = 1024` (`narration_apply.py:5762`) — which 77-3 should
   reuse for `set_stakes` and mirror for quest_log/quest_anchors cardinality.
3. **[SEC] [LOW] "Degrade loudly" needs severity.** The empty-drive span (77-2) should
   carry a warning-severity attribute, not be a no-op span nobody reads. Make it an
   explicit 77-2 AC.
4. **[LOW] 77-5 likely underpointed.** Retiring `quest_updates` touches 6+ sites
   (`orchestrator.py:472,1258,3219,3549`, `narration_apply.py:2861`, `session.py:1278`)
   across extraction, apply, and the `WorldStatePatch` model. 2pts is optimistic;
   re-estimate at story-add time. The ADR correctly gates 77-5 on 77-3.
5. **[VERIFIED] Internal consistency.** The risk "gate 77-5 on 77-3" matches the
   suggested order (77-2→77-3→77-4→77-5). All 6 ACs map to concrete sections. No
   contradictions between Decision, Consolidation, and Alternatives.
6. **[VERIFIED] No-Reinvent compliance.** The design promotes an existing field, reuses
   an existing wired consumer (course.py), an existing payload field (quests), and an
   existing span route — rather than inventing parallel machinery. Exemplary per
   "Don't Reinvent — Wire Up What Exists."

### Rule Compliance

- **No Silent Fallbacks (CLAUDE.md):** ADR §Consequences (line 184) mandates loud
  degradation (OTEL span) on empty drive. COMPLIANT (sharpened by Observation 3).
- **OTEL Observability Principle (CLAUDE.md):** §OTEL spans defines 5 named spans
  covering every write path. COMPLIANT.
- **One-mechanism-per-problem (CLAUDE.md):** §Consolidation retires the legacy lane +
  escape-hatch quest/stakes paths in favor of the typed tools. COMPLIANT.
- **Crunch in Genre, Flavor in World (SOUL):** quest/stakes treated as mechanics →
  engine; active_seeds content carved to the world/pack (77-7). COMPLIANT.
- **Don't Reinvent — Wire Up What Exists (CLAUDE.md):** promotes/reuses existing
  fields + consumers. COMPLIANT (Observation 6).
- **ADR-088 frontmatter schema:** id/status/implementation-status/related/tags valid;
  index regenerated and in-sync (preflight). COMPLIANT.

### Devil's Advocate

Argue the ADR is broken. First attack: "the decision dodges AC-1 — it was asked to
pick A/B/C/D and instead invented a fifth option." Rebuttal holds: it commits to C as
the engine decision and enumerates D's increment as a discrete story (77-6); all four
options are weighed in §Alternatives. This is sound scoping, not evasion. Second
attack, and the sharp one: "Option A — the ADR's smallest, highest-certainty fix —
does not actually fix the case that motivated the epic." This landed. wry_whimsy is a
prose-only pack; `drive` is populated only when a genre authors a drive-shaped scene
(`builder.py:423`), so seed-at-creation would hand the engine an empty string in the
exact wry_whimsy/oz session the ADR opens with. A reviewer skimming the Decision could
walk away believing A closes the playtest gap; it does not — B does, for prose packs.
The ADR does name the empty-drive risk, but buries it as a Negative bullet rather than
foregrounding that A is conditional and B is load-bearing for the packs most likely to
exhibit the bug. Captured as Observation 1 (MEDIUM). Third attack: "retiring
quest_updates (77-5) will break the extraction pipeline mid-flight." The ADR hedges
("gate 77-5 on 77-3", "once migrated"), but the point-estimate understates the blast
radius (6+ call sites) — Observation 4. Fourth attack: "the new tools let a misfiring
narrator flood Postgres." Real, but the ADR flags it and a 1024-char guardrail already
exists to reuse — Observation 2. Fifth: "is `quest_anchors` truly worth promoting, or
is course.py itself dead?" I verified three live callers — the consumer is wired and
waiting. None of these rise to High/Critical: the decision is correct, the gaps are
scope-sharpening for the implementation stories, and every risk is at least
acknowledged in the ADR. No blocker found.

### Deviation audit

See `### Reviewer (audit)` under Design Deviations.

**Data flow traced:** PC `drive` (chargen) → [proposed 77-2] seed → `quest_log` +
`quest_anchors` + `active_stakes` on snapshot → `compute_courses` (orbital) + client
`quests` payload → [proposed 77-6] quest panel. The one weak link (empty `drive` in
no-drive-scene packs) is captured as Observation 1.

**Dispatch tags:**
- `[EDGE]` — subagent disabled via settings; doc-only diff (no execution paths to enumerate). N/A.
- `[SILENT]` — subagent disabled via settings; ADR's own No-Silent-Fallbacks posture verified under Rule Compliance.
- `[TEST]` — subagent disabled via settings; DESIGN story, no tests authored. N/A.
- `[DOC]` — subagent disabled via settings; ADR doc-quality checked directly by Reviewer (links/consistency clean, per preflight).
- `[TYPE]` — subagent disabled via settings; proposed types (record_quest schema) deferred to 77-3. N/A.
- `[SEC]` — Observations 2 & 3: bound narrator-controlled `active_stakes`/`quest_log` (reuse `_ACTIVE_STAKES_GUARDRAIL`); empty-drive span needs warning severity.
- `[SIMPLE]` — subagent disabled via settings; design reuses existing machinery (Observation 6), no over-engineering observed.
- `[RULE]` — all six applicable project rules COMPLIANT (see Rule Compliance).

**Handoff:** To SM (Morpheus) for finish-story. All findings non-blocking — carry into
implementation stories 77-2/77-3/77-5 at story-add time.

## Delivery Findings

<!-- Agents append below. Never edit/remove another agent's entries. -->

### Dev (implementation)

- **Improvement** (non-blocking): The `sm-setup` subagent mis-reported `workflow_type` as `stepped` for the phased `trivial` workflow, writing "stepped" into the session file + SM prime and trapping SM in a `pf workflow start trivial` error loop. Affects the `sm-setup` subagent's workflow-type detection (should trust `pf workflow type <name>`). Worked around by correcting the session labels + completing the setup→implement transition manually. *Found by Dev during implementation.*
- **Gap** (non-blocking): Story `77-1` `repos` field is `server,ui`, but the design deliverable (ADR) lands in the orchestrator repo (`docs/adr/`). The future *implementation* stories (77-2…77-6) are correctly server/ui; the design story's repos field is cosmetically misleading. Affects `sprint/epic-77.yaml` (no action required — noted for accuracy). *Found by Dev during implementation.*

### Reviewer (code review)

- **Gap** (non-blocking): Option A (seed-at-creation) seeds from `Character.drive`, but `drive` is populated only for genres with a drive-shaped scene (`sidequest-server/sidequest/game/builder.py:423`); prose-only packs like wry_whimsy (the epic-77 trigger) leave it `""`. Affects story **77-2** (its AC must verify seed behavior against a no-drive pack and clarify that Option B, not A, is the load-bearing fix for prose packs). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `record_quest`/`set_stakes` persist narrator-controlled strings to Postgres; reuse the existing `_ACTIVE_STAKES_GUARDRAIL = 1024` (`sidequest-server/sidequest/server/narration_apply.py:5762`) for `set_stakes` and add a cardinality cap for `quest_log`/`quest_anchors`. Affects story **77-3** (schema bounds at the ADR-102 layer). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): The empty-drive "degrade loudly" span (ADR §Consequences) should carry a warning-severity attribute, not be a silent no-op span. Affects story **77-2** (make span severity an explicit AC). *Found by Reviewer during code review.*
- **Question** (non-blocking): Story **77-5** (retire `quest_updates`) is pointed at 2pts but touches 6+ sites (`orchestrator.py:472,1258,3219,3549`, `narration_apply.py:2861`, `session.py:1278`); re-estimate at `pf sprint story add` time. *Found by Reviewer during code review.*
- **Gap** (non-blocking): `sprint/epic-77.yaml` has an uncommitted status bump (`in_progress`→`in_review` + branch-field reorder) from the phase machinery. SM's finish flow commits sprint YAML — flagged so it isn't lost. *Found by Reviewer (via preflight) during code review.*

## Design Deviations

### Dev (implementation)
- **Decision framed as "C-core + D-as-fast-follow" rather than a single A/B/C/D pick**
  - Spec source: 77-1 session AC-1 ("a decision among options A / B / C / D")
  - Spec text: "with a decision among options A (seed-at-creation) / B (typed narrator tool) / C (both) / D (full-stack + UI panel) and the rationale"
  - Implementation: ADR-137 selects Option C as the engine core AND commits Option D's UI panel as a separately-enumerated fast-follow story (77-6), rather than choosing pure C or pure D.
  - Rationale: pure D bundles server+UI into one story and defeats independent OTEL verification of the server lane (GM panel is the lie-detector); pure C leaves the player unable to see the spine. Splitting D's panel into its own story honors "Verify Wiring, Not Just Existence" while keeping stories shippable.
  - Severity: minor
  - Forward impact: none — D's increment is still delivered, just as a discrete story; all four options were weighed in §Alternatives.

### Reviewer (audit)
- **Decision framed as "C-core + D-as-fast-follow"** → ✓ ACCEPTED by Reviewer: sound scoping, not AC-1 evasion. The ADR commits to C as the engine decision, enumerates D's increment as story 77-6, and weighs all four options in §Alternatives. Splitting the UI panel enables independent OTEL verification of the server lane before the panel consumes it — agrees with author reasoning.
- No undocumented deviations found. The ADR's claims were independently re-traced to code (see Reviewer Assessment §Independent claim verification); all citations are accurate. The one substantive gap (Option A's empty-drive source in prose packs) is a forward-looking scope note for 77-2, not a spec deviation in this story's deliverable — captured under Delivery Findings.