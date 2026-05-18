---
story_id: "50-12"
epic: "50"
workflow: "tdd"
repos: server
---

# Story 50-12: Disposition: narrator NPC serialization emits attitude string

## Story Details
- **ID:** 50-12
- **Epic:** 50 (Pingpong-archive triage and dropped-work cleanup)
- **Workflow:** tdd
- **Repos:** sidequest-server
- **Priority:** p2
- **Points:** 3
- **Stack Parent:** 50-10 (Disposition: central Attitude enum + Disposition.attitude() derivation)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-18T07:53:44Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-18 | 2026-05-18T07:18:46Z | 7h 18m |
| red | 2026-05-18T07:18:46Z | 2026-05-18T07:31:28Z | 12m 42s |
| green | 2026-05-18T07:31:28Z | 2026-05-18T07:34:50Z | 3m 22s |
| spec-check | 2026-05-18T07:34:50Z | 2026-05-18T07:36:48Z | 1m 58s |
| verify | 2026-05-18T07:36:48Z | 2026-05-18T07:45:17Z | 8m 29s |
| review | 2026-05-18T07:45:17Z | 2026-05-18T07:51:34Z | 6m 17s |
| spec-reconcile | 2026-05-18T07:51:34Z | 2026-05-18T07:53:44Z | 2m 10s |
| finish | 2026-05-18T07:53:44Z | - | - |

## Story Context

### Problem Statement
The narrator system sees only numeric disposition values when serializing NPCs into the prompt context. The attitude derivation (50-10) moved to central Disposition.attitude() but the _narrator-facing serialization path_ never wired the attitude string output, leaving agents to work with raw numbers instead of semantic labels.

**Gap:** agents see `{"npc": "Soren", "disposition": 45}` but not `{"attitude": "Guarded"}`. This forces the narrator to maintain its own mental mapping of disposition→attitude ranges and makes OTEL tracing opaque (we log numeric dispositions in spans but have to reverse-engineer the semantic in dashboards).

### Root Cause
Story 50-10 established the central `Attitude` enum and `Disposition.attitude()` method. However, the NPC serialization surface (used when building narrator context) still omits the attitude field. This is visible in:
- Game state snapshots passed to narrator via agents/tools/apply_patches.py
- NPC roster serialization in game/characters.py
- Journal/KnownFact context that references NPC dispositions

### Acceptance Criteria

**AC-1: Narrator NPC context includes attitude string**
- When an NPC is serialized for narrator context (e.g., in `snap.npcs` dictionary), the output includes an `attitude` field (string: "Hostile", "Guarded", "Neutral", "Trusting", "Allied")
- The attitude is derived from Disposition.attitude() at serialization time (not static YAML)
- Spot check: a 2-point disposition delta crosses a threshold, serialization reflects the new attitude

**AC-2: Snapshot state carries attitude in all paths**
- GameSnapshot.npcs serialization includes attitude (game/state.py)
- NPC state patches in world_mutation patches carry attitude_before and attitude_after (if crossing threshold) for OTEL reconstruction
- Journal/KnownFact context that mentions an NPC includes the current attitude at retrieval time

**AC-3: OTEL and logging receive attitude strings**
- SPAN_NPC_SERIALIZED or similar span logs `attitude` alongside `disposition` (numeric)
- GM panel sees attitude labels in NPC state traces, not just raw numbers
- Test: mock a disposition change mid-turn, assert OTEL span carries both values

**AC-4: No agent workflow regression**
- Agents still receive numeric disposition (for backward compat with any numeric thresholds in prompts)
- Attitude is an _additional_ field, not a replacement
- Test: existing agent behavior passes without modification

**AC-5: Type safety**
- Attitude field is typed as Literal["Hostile", "Guarded", "Neutral", "Trusting", "Allied"] (matches Attitude enum)
- Pydantic validation enforces the constraint; no string fallback
- Test: attempt to serialize with invalid attitude (e.g., "Unknown") raises validation error

## Technical Approach

### Primary Change Vector
Modify the NPC serialization seam in game/characters.py and game/state.py to call `npc.disposition.attitude()` and include the result in the output dict.

### Affected Modules
- **game/characters.py** — NPC serialization methods (dict_for_context, dict_for_prompt, etc.)
- **game/state.py** — GameSnapshot serialization
- **game/npcs.py** — NPC model; verify Disposition.attitude() is accessible
- **agents/tools/apply_patches.py** — Verify narrator context building uses the serialized form
- **game/journal.py** (if NPC context is embedded in known_facts)
- **Protocol models** (pydantic)—Add attitude field to NPC output schemas if exposed via WebSocket

### Test Strategy
1. **Unit:** NPC serialization with mocked disposition values (0, 30, 50, 70, 100) → verify attitude is correct at each threshold
2. **Integration:** Load a snapshot, mutate an NPC's disposition, re-serialize, assert attitude changed
3. **Wiring:** E2E test that calls narrator with an NPC context that includes attitude, assert no prompt errors or missing-field logs
4. **Regression:** Existing agent tests still pass; numeric disposition is still present

### Dependency Notes
- **Blocked by:** 50-10 (Disposition.attitude() must exist)
- **Blocks:** 50-13 (genre-configurable thresholds; attitude ranges depend on this)

## Delivery Findings

No upstream findings at setup time.

### TEA (test design)
- **Conflict** (blocking): Session AC-1/AC-5 specify a five-tier capitalised attitude `Literal["Hostile","Guarded","Neutral","Trusting","Allied"]` that does not exist. The merged 50-10 dependency defines a **three-tier lowercase** `Attitude` enum (`friendly`/`neutral`/`hostile`) and its module docstring declares those literals the *stable wire contract* (locked by `tests/game/test_disposition_attitude_enum.py`). Affects `.session/50-12-session.md` (AC-1/AC-5 must be rewritten to the real enum; Dev serializes the 3-tier lowercase band, AC-5 type is the `Attitude` enum not the fictional Literal). *Found by TEA during test design.*
- **Conflict** (non-blocking): Session Root Cause misidentifies the seam. `query_npc` already emits `attitude` (`sidequest/agents/tools/query_npc.py:109`); the real gap is the proactive `register_npc_roster_section`. Affects `sidequest/agents/prompt_framework/core.py` (this is the change vector — NOT `game/characters.py`/`game/state.py` as the ACs claim; those modules do not exist with that shape). *Found by TEA during test design.*
- **Gap** (non-blocking): AC-2's `attitude_before`/`attitude_after` sub-clause is already satisfied by merged Story 50-11 (`sidequest/game/session.py:1185-1206`, covered by `tests/integration/test_disposition_otel_wiring.py`). Affects scope only — Dev must NOT re-implement the `SPAN_DISPOSITION_SHIFT` route. *Found by TEA during test design.*
- **Question** (non-blocking): AC-3 asks for a span logging "attitude alongside disposition (numeric)" — but the perception firewall (ADR-104/105) forbids the raw numeric in any narrator-facing surface, so that exact phrasing is self-contradictory. Affects `.session/50-12-session.md` AC-3 (Architect/Reviewer should confirm dashboard-visibility of the coarsened band via the existing prompt-zones dashboard satisfies AC-3). *Found by TEA during test design.*

### Dev (implementation)
- No upstream findings during implementation. TEA's blocking Conflict (the session ACs' fictional 5-tier enum + wrong seam) is confirmed accurate against the code; implementation followed the TEA-corrected change vector. The session ACs (lines 44-69) remain materially wrong on the page — Reviewer/SM should treat the 14 tests + TEA deviations as the authoritative contract, not the verbatim ACs.

### TEA (test verification)
- **Improvement** (non-blocking): Pre-existing `ruff format` nonconformance in `sidequest/agents/prompt_framework/core.py:534-540` (`register_region_section`, the `Depth: …` line) — unrelated to 50-12, already present on `develop`. Deliberately NOT reformatted: it is out of 50-12 scope and blanket-formatting `core.py` would inject unrelated churn into this PR; `ruff format --check` is not a project CI gate (`just server-check` = `ruff check` + pytest, both green). Affects `sidequest/agents/prompt_framework/core.py` (a future format-hygiene chore should `ruff format` the file, or a repo-wide format pass). *Found by TEA during test verification.*

### Reviewer (code review)
- **Improvement** (non-blocking): Three smoke tests (`test_roster_emits_attitude_for_{neutral,hostile,friendly}_npc`) use bare `assert "<band>" in content` rather than the stricter `_band_in` helper used by the derivation/boundary/firewall tests. Safe today (roster boilerplate contains none of the three band words) but `_band_in` would harden them against future roster wording. Affects `tests/agents/test_npc_roster_attitude.py` (optional test hardening; non-blocking). *Found by Reviewer during code review.*
- **Question** (non-blocking): v1 ships a single global `Disposition`; in multiplayer every player's narrator roster shows the same global band (per-PC disposition is "forward-looking" per `query_npc.py` docstring). Not introduced or regressed by 50-12 — it inherits existing v1 `query_npc` semantics — but flagged so 50-13 / spec-reconcile are aware the band is not yet per-perspective. Affects `sidequest/agents/prompt_framework/core.py` (no change required for 50-12; a future per-PC-disposition story owns this). *Found by Reviewer during code review.*

## Design Deviations

None at setup time.

### TEA (test design)
- **Attitude enum is 3-tier lowercase, not the ACs' fictional 5-tier**
  - Spec source: .session/50-12-session.md, AC-1 and AC-5
  - Spec text: 'attitude field (string: "Hostile", "Guarded", "Neutral", "Trusting", "Allied")' / 'typed as Literal["Hostile", "Guarded", "Neutral", "Trusting", "Allied"]'
  - Implementation: Tests assert the real three-tier lowercase `Attitude` enum (`friendly`/`neutral`/`hostile`) from dependency 50-10 (`sidequest/game/disposition.py`); `_BANDS` is derived from the live enum, not a hardcoded list.
  - Rationale: The five-tier capitalised set does not exist and contradicts 50-10's merged wire contract; a factually impossible literal set cannot drive RED tests. Spec-authority hierarchy yields to a dependency that is already shipped and tested.
  - Severity: major
  - Forward impact: 50-13 (genre-configurable thresholds) likely inherits the same fictional framing and will need the identical correction.
- **Change vector relocated from characters.py/state.py to the proactive roster**
  - Spec source: .session/50-12-session.md, Root Cause and AC-1
  - Spec text: "the narrator-facing serialization path never wired the attitude string output" / "snap.npcs dictionary ... includes an attitude field"
  - Implementation: Tests target `register_npc_roster_section` in `sidequest/agents/prompt_framework/core.py`; `snap.npcs` is `list[Npc]` rendered into a text section, asserted against the rendered `npc_roster` section content (not a dict).
  - Rationale: Verified against code — the reactive `query_npc` path already emits attitude; the untouched seam is the proactive roster. Testing the fictional dict shape would yield un-implementable RED.
  - Severity: major
  - Forward impact: none — corrected technical approach handed to Dev in the assessment.
- **AC-2 attitude_before/after not retested (already shipped by 50-11)**
  - Spec source: .session/50-12-session.md, AC-2
  - Spec text: "NPC state patches ... carry attitude_before and attitude_after (if crossing threshold) for OTEL reconstruction"
  - Implementation: Not covered by new tests; the behavior exists at `session.py:1185-1206` with coverage in `tests/integration/test_disposition_otel_wiring.py`.
  - Rationale: Re-testing merged 50-11 behavior is redundant and risks Dev re-implementing a done subsystem; do not preserve coupling to an already-satisfied AC.
  - Severity: minor
  - Forward impact: Dev must NOT touch the disposition-shift span — it is complete.
- **AC-3 observability via existing prompt-zones dashboard, not a bespoke span**
  - Spec source: .session/50-12-session.md, AC-3
  - Spec text: "SPAN_NPC_SERIALIZED or similar span logs attitude alongside disposition (numeric)"
  - Implementation: Tests assert the band rides the `npc_roster` `PromptSection` (Early zone, State category), which the existing prompt-zones dashboard already surfaces to the GM panel; no `SPAN_NPC_SERIALIZED` is asserted.
  - Rationale: This is a serialization enrichment, not a subsystem decision (CLAUDE.md exempts cosmetic serialization from bespoke OTEL); the firewall forbids the numeric in a narrator-facing span, so the AC's literal phrasing cannot be satisfied as written.
  - Severity: major
  - Forward impact: Reviewer must accept dashboard-visibility as AC-3 satisfaction; a dedicated span, if later desired, is a separate story.

### Dev (implementation)
- No deviations from spec. Implemented exactly the TEA-corrected change vector against the 14-test contract; no abstractions, helpers, or scope beyond what the tests demand (one `parts.append` line). The four spec corrections are already logged by TEA above and are not re-logged here (append-only; not Dev's subsection to restate).

### Reviewer (audit)
- **TEA: "Attitude enum is 3-tier lowercase, not the ACs' fictional 5-tier"** → ✓ ACCEPTED by Reviewer: independently verified `disposition.py:52-54` (`FRIENDLY/NEUTRAL/HOSTILE` = lowercase) + `:77-82` derivation; the 5-tier capitalised set does not exist. Sound.
- **TEA: "Change vector relocated from characters.py/state.py to the proactive roster"** → ✓ ACCEPTED by Reviewer: `query_npc.py:109` already emits attitude; the named modules do not exist with the claimed shape; `register_npc_roster_section` is the correct proactive seam. Sound.
- **TEA: "AC-2 attitude_before/after not retested (already shipped by 50-11)"** → ✓ ACCEPTED by Reviewer: `session.py:1185-1206` emits before/after/crossed; re-implementing would duplicate merged 50-11. Correct scope exclusion.
- **TEA: "AC-3 observability via existing prompt-zones dashboard, not a bespoke span"** → ✓ ACCEPTED by Reviewer: ADR-104/105 forbids the raw numeric in a narrator-facing span, so the AC's literal phrasing is unsatisfiable as written; the band rides the `npc_roster` PromptSection which the prompt-zones dashboard already surfaces — the GM-panel lie-detector requirement is met without a redundant span. CLAUDE.md exempts cosmetic serialization from bespoke OTEL. Sound.
- **Architect spec-check (4 mismatches, all Option-A)** → ✓ ACCEPTED by Reviewer: all four are spec-side drift already documented; zero Option-B; agrees the verbatim ACs are superseded by the 14-test contract.
- **TEA verify "Improvement: pre-existing core.py:534 ruff-format nonconformance left untouched"** → ✓ ACCEPTED by Reviewer: out of 50-12 scope, already on `develop`, `ruff format --check` is not a project CI gate; reformatting would inject unrelated PR churn. Correct restraint; the non-blocking Improvement finding correctly preserves the trail.
- No UNDOCUMENTED deviations found. The diff implements exactly the corrected contract; nothing diverged that TEA/Dev/Architect did not already log.

### Architect (reconcile)

**Manifest verification:** All in-flight entries (TEA test-design ×4, Dev, TEA verify, Reviewer audit/code-review) were checked for the 6-field contract. Spec source `.session/50-12-session.md` exists and is the *sole* spec source (no `sprint/context/context-{epic-50,story-50-12}.md` exists — story context is embedded in the session file, consistent across all phases). Spec-text excerpts were verified verbatim against session lines 50-73 (AC-1/AC-5/Root-Cause/AC-2/AC-3). Implementation descriptions match the shipped diff (`core.py:478`, one coarsened-band append). No field was inaccurate; no entry required annotation or a missing-field backfill. No AC accountability table was emitted by the ac-completion gate and no AC was formally DEFERRED/DESCOPED — every AC was *addressed under the corrected contract* (AC-1/AC-5 against the real 3-tier enum, AC-2 dict-clause fictional + before/after pre-satisfied by 50-11, AC-3 via prompt-zones dashboard, AC-4 fully met), so the AC-deferral-justification step is a no-op.

**One deviation the in-flight logs only *implied* — recorded here in full for the audit artifact:**

- **AC-2 "all paths" narrowed to stateful NPCs; `npc_pool` members deliberately excluded**
  - Spec source: .session/50-12-session.md, AC-2 (lines 55-58)
  - Spec text: "AC-2: Snapshot state carries attitude in all paths — GameSnapshot.npcs serialization includes attitude … Journal/KnownFact context that mentions an NPC includes the current attitude at retrieval time"
  - Implementation: The band is appended only to the **stateful `Npc`** lines of `register_npc_roster_section` (`core.py:478`). The `NpcPoolMember` loop in the same roster (`core.py:447-458`) is intentionally untouched; no `GameSnapshot.npcs`-dict nor Journal/KnownFact attitude surface was added. TEA's `test_pool_only_members_get_no_attitude_token` guards the exclusion as an invariant; Dev/TEA assessments mention it, but it was never written as a standalone 6-field deviation against AC-2's literal "all paths."
  - Rationale: `NpcPoolMember` is an identity-only regenerable cast record with **no `Disposition` field** — it is structurally incapable of carrying an attitude, so "all paths" is satisfied for every path that *has* a disposition. The `GameSnapshot.npcs`-dict and Journal/KnownFact sub-clauses target a serialization shape that does not exist (already covered by TEA's "change vector relocated" deviation); the before/after sub-clause is pre-satisfied by merged 50-11 (TEA "AC-2 … not retested"). This entry makes the *pool-exclusion* facet explicit so the audit shows AC-2's "all paths" was a conscious, bounded scope decision, not an oversight.
  - Severity: minor
  - Forward impact: None for 50-12. Positive coupling note for **50-13** (genre-configurable thresholds, `depends_on: 50-10`): the roster delegates 100% to `Disposition.attitude()`, so 50-13's configurable ±10 thresholds flow into the rendered band automatically with **zero 50-12 rework**. 50-13's ACs are likely authored by the same sm-setup pass and may inherit the fictional 5-tier framing (already flagged by TEA's enum deviation) — spec-reconcile for 50-13 should expect the same Option-A correction.

## SM Assessment

**Story selected:** 50-12 — chosen by product owner from a 7-story backlog. Rationale: highest-leverage cleanly-operable case. p2, 3pt, server-only, dependency 50-10 (central Attitude enum + Disposition.attitude()) is **done**, so the work is unblocked. Sits dead-center of Sprint 3's goal ("MP correctness, state hygiene") — it is a perception/serialization-correctness fix, not a feature add.

**Setup verification:**
- Session file created and populated with problem statement, root cause, 5 ACs, technical approach, test strategy. ✅
- Feature branch `feat/50-12-disposition-narrator-attitude-serialization` created off the server subrepo base per repos.yaml. ✅
- Jira: **explicitly skipped** — SideQuest is a personal project with no Jira; sprint YAML is the source of truth.

**Routing:** Workflow is `tdd` (phased). Per resolve-gate, next agent is **tea** for the **red** phase. No implementation planning performed at SM — that is tea/dev's lane.

**Risk notes for downstream:** Attitude must be *additive* (AC-4) — numeric disposition stays in the payload for backward compat. AC-5 requires the field be typed as a `Literal` matching the Attitude enum, not a loose string. Watch the OTEL requirement (AC-3): per project doctrine every subsystem touch adds a watcher span — attitude must appear alongside numeric disposition in the span so the GM panel stays a lie detector.

## TEA Assessment

**Tests Required:** Yes
**Reason:** n/a — behavioral story, RED tests written.

**Test Files:**
- `sidequest-server/tests/agents/test_npc_roster_attitude.py` — 14 tests covering the corrected interpretation of all 5 ACs against the real code/enum, plus perception-firewall and scope guards and the mandatory end-to-end wiring test.

**Tests Written:** 14 tests covering 5 ACs (corrected per the 4 TEA deviations above)
**Status:** RED (13 failing, 1 intentional invariant guard green — see note)

**The actual deliverable (corrected change vector for Dev):** wire the coarsened qualitative `attitude` band (`Disposition.attitude().value` — `friendly`/`neutral`/`hostile`) into the **stateful-NPC loop** of `register_npc_roster_section` (`sidequest/agents/prompt_framework/core.py:460-471`). Today that roster gives the narrator name/pronouns/appearance/last-seen but no disposition stance, forcing a per-NPC `query_npc` round-trip. The band must be **coarsened only** — never emit `disposition.value` into this always-on broadcast-layer section (ADR-104/105 firewall; the roster line at core.py:474-476 already says "only emotional perception is POV", so the band belongs there). Do **not** add attitudes to `npc_pool` members (identity-only, no `Disposition`). Do **not** touch the 50-11 `SPAN_DISPOSITION_SHIFT` route.

### Rule Coverage

| Rule (lang-review python.md) | Test(s) | Status |
|------|---------|--------|
| #6 Test quality (no vacuous asserts) | self-check caught & strengthened 2 weak tests: `test_attitude_lands_in_built_narrator_prompt` (was a whole-prompt `"hostile" in prompt` false positive — boilerplate match; now scoped to the `npc_roster` section) and `test_roster_rejects_fictional_five_tier_labels` (was trivially green; now RED-coupled to the correct lowercase band). `_band_in` helper rejects empty/ambiguous matches. | failing (correct) |
| #3 Type annotations / type-safety | `test_roster_band_is_a_real_attitude_enum_member` (band ∈ live `Attitude` enum, AC-5 corrected) | failing |
| #9 Async/await pitfalls | `test_attitude_lands_in_built_narrator_prompt`, `test_wiring_attitude_is_carried_by_npc_roster_state_early_section` (`await orch.build_narrator_prompt`; a missing-await regression in the seam would leave the band absent) | failing |
| #14 State-cleanup ordering w/ fallible side effect (origin: 50-4 I3) | `register_npc_roster_section` calls the one-shot `register_section` once with a locally-built `lines` list and has **no consume-then-clear** today — covered by design, not a contrived test. **Flagged for Dev:** if you refactor to stage/clear, clear the source BEFORE `register_section`. | n/a (noted) |
| #1,#2,#5,#7,#8,#10,#11,#12 | Not applicable — pure in-memory prompt-string enrichment: no I/O, untrusted input, new deps, resources, or mutable defaults introduced. Fabricating tests here would be vacuous (violates the meaningful-assertion rule). | n/a |

**Rules checked:** 4 of 14 lang-review checks are applicable to test design for this story; all 4 have coverage or a documented rationale.
**Self-check:** 2 weak tests found and strengthened (details in #6 row); 0 vacuous assertions remain. 1 test (`test_pool_only_members_get_no_attitude_token`) is an **intentional invariant guard** — correctly green before and after implementation; it proves Dev does not fabricate attitudes for identity-only pool members. This is deliberate, not a non-RED defect.

**Regression sweep:** `test_npc_identity_drift.py`, `test_disposition_attitude_enum.py`, `test_query_npc.py` (56 tests) remain green — new file has no side effects on adjacent seams.

**Handoff:** To Dev for implementation. **Read the 4 TEA deviations + Delivery Findings first** — the session ACs are materially wrong (fictional 5-tier enum, wrong seam, AC-2 pre-done, AC-3 self-contradictory). Implement against the corrected change vector above; the 13 RED tests are the real contract.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest-server/sidequest/agents/prompt_framework/core.py` — `register_npc_roster_section`: appended `[attitude: <band>]` to each **stateful** NPC roster line, derived from `npc.disposition.attitude().value` (`friendly`/`neutral`/`hostile`). 8 lines added (1 statement + an explanatory firewall comment). `npc_pool` identity-only members untouched; the closing "emotional perception is POV" instruction now has a concrete referent.

**Approach:** Minimal — the single `parts.append(...)` the test contract demands, nothing more. The band is the coarsened `Attitude` StrEnum value only; the raw `disposition.value` integer is never emitted into this always-on narrator-facing broadcast section (ADR-104/105 perception firewall — verified by `test_roster_does_not_leak_raw_disposition_integer` and the `-50` wiring assertion). Boundary correctness (`>10`/`<-10`) is delegated to the existing, 50-10-tested `Disposition.attitude()` — no duplicated threshold logic. The 50-11 `SPAN_DISPOSITION_SHIFT` route was not touched.

**Lang-review self-check (changed file):** #1/#2/#5/#7/#8/#11 n/a (no exceptions, mutable defaults, paths, resources, deserialization, or untrusted input introduced). #3 type annotations: change is one line inside an existing fully-typed method; no new signatures. #14 state-cleanup ordering (TEA-flagged): the per-NPC append mutates the local `parts`/`lines` lists *before* the single terminal `register_section(...)` call — no consume-then-clear introduced, side-effect ordering unchanged. Clean.

**Tests:** 14/14 story tests passing (GREEN). Regression sweep 149/149 (`test_npc_identity_drift`, `test_disposition_attitude_enum`, `test_query_npc`, full `test_prompt_framework/`). 163 passed, 0 failed.

**Branch:** `feat/50-12-disposition-narrator-attitude-serialization` (pushed, tracking origin).

**Handoff:** To verify (TEA simplify + quality-pass).

## Architect Assessment (spec-check)

**Spec Alignment:** Drift detected — but the drift is in the *written ACs*, not the code. The implementation correctly delivers the story's intent ("narrator NPC serialization emits attitude string, close the agents-see-only-attitude gap") against the real codebase. Every mismatch traces to the session ACs (lines 47-70) being authored against a non-existent five-tier enum and the wrong seam — already documented in full 6-field form by TEA (4 deviations + a blocking Conflict) and confirmed by Dev. Structural spec-check gate: **passed**. Code verified by direct diff read (not assessment-chain trust): 8 lines, stateful-NPC loop only, emits the coarsened `Attitude` StrEnum value, no raw-int leak, `npc_pool` untouched, reuses 50-10's `Disposition.attitude()` with zero duplicated threshold logic.

**Mismatches Found:** 4 (all spec-side; all pre-logged by TEA)

- **AC-1/AC-5 fictional five-tier capitalised enum** (Ambiguous spec / Different behavior — Behavioral, Major)
  - Spec: `attitude` is one of `Literal["Hostile","Guarded","Neutral","Trusting","Allied"]`, on a `snap.npcs` dict.
  - Code: emits the real three-tier lowercase `Attitude` StrEnum (`friendly`/`neutral`/`hostile`) on the rendered `npc_roster` PromptSection; type-safety is the enum itself (an invalid value is unconstructable — stronger than the AC's pydantic-Literal ask).
  - Recommendation: **A — Update spec.** The AC was written against an enum that does not exist; 50-10's three-tier enum is the merged, docstring-declared wire contract. Deviation already logged (TEA, "Attitude enum is 3-tier lowercase…"). No code change.
- **AC-1/Root-Cause wrong seam** (Different behavior — Architectural, Major)
  - Spec: change `game/characters.py`/`game/state.py`; "the serialization path never wired the attitude string."
  - Code: `register_npc_roster_section` in `agents/prompt_framework/core.py` — the actual proactive narrator-facing seam. `query_npc` already emitted attitude; the named modules do not exist with the claimed shape.
  - Recommendation: **A — Update spec.** Deviation already logged (TEA, "Change vector relocated…"). No code change.
- **AC-2 GameSnapshot/Journal dict sub-clauses + attitude_before/after** (Missing in code / pre-satisfied — Behavioral, Major→Minor)
  - Spec: `GameSnapshot.npcs` dict carries attitude; world-mutation patches carry `attitude_before/after`; Journal/KnownFact carries attitude.
  - Code: not implemented — the dict sub-clauses target a fictional serialization shape; `attitude_before/after` is already shipped by merged Story 50-11 (`session.py:1185-1206`).
  - Recommendation: **A — Update spec** for the fictional dict sub-clauses; **D — Defer/already-done** for the 50-11 portion (correctly out of scope; Dev was right not to re-implement it). Deviation already logged (TEA, "AC-2 attitude_before/after not retested…").
- **AC-3 "span logs attitude alongside disposition (numeric)"** (Different behavior — Architectural, Major)
  - Spec: a `SPAN_NPC_SERIALIZED` span carrying attitude *and the numeric disposition*.
  - Code: observability via the band riding the `npc_roster` PromptSection (Early/State), surfaced by the existing prompt-zones dashboard. No bespoke span; the numeric is deliberately absent.
  - Recommendation: **A — Update spec.** The AC's literal phrasing is self-contradictory: ADR-104/105 forbids the raw numeric in any narrator-facing surface, so "alongside disposition (numeric)" cannot be satisfied without breaching the firewall. Dashboard-visibility of the coarsened band is the correct observability surface for a serialization enrichment (CLAUDE.md exempts cosmetic serialization from bespoke OTEL). Deviation already logged (TEA, "AC-3 observability via existing prompt-zones dashboard…"). No code change. A dedicated span, if ever wanted, is a separate story.

**AC-4** (no regression; additive; agents still get numeric): **Aligned.** Change is purely additive; the world-state-agent numeric path (`query_npc.disposition_value`) is untouched; regression sweep 149/149 green.

**Reuse-first verdict:** Exemplary. No new component, no new pattern, no duplicated threshold logic — the change extends one existing rendered section by one line, delegating all derivation to the already-tested 50-10 `Disposition.attitude()`. This is the second-best code: someone already debugged the hard part.

**Decision:** Proceed to verify. No hand-back to Dev — zero Option-B mismatches; the code is correct and all spec drift is Option-A (spec already superseded by the test contract + TEA deviation manifest). The verbatim ACs in lines 47-70 should be read as historical/superseded; the 14 tests + TEA/Architect deviations are the authoritative contract for Reviewer and the spec-reconcile phase.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 2 (`sidequest/agents/prompt_framework/core.py`, `tests/agents/test_npc_roster_attitude.py`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | New line mirrors the existing `[last seen: …]` pattern; unconditional append correct (every NPC has a `disposition`). No extraction warranted for one domain-specific line. |
| simplify-quality | 1 finding (low) | Stale RED-phase module docstring ("expected to FAIL until Dev wires…") now misleading post-implementation. |
| simplify-efficiency | clean | `npc.disposition.attitude().value` is optimal — no abstraction, no redundancy; delegates derivation to existing 50-10 method. |

**Applied:** 1 — the low-confidence simplify-quality docstring finding. *Workflow says flag-don't-apply for low confidence; overridden by TEA judgment: a "tests will FAIL" note in a now-passing file is actively misleading documentation, a zero-risk factual correction in the TEA-authored file, not a speculative refactor. Rationale logged.*
**Flagged for Review:** 0 medium-confidence findings
**Noted:** 0 low-confidence observations left unaddressed
**Reverted:** 0

**Additional verify-phase fix (not from a simplify teammate):** the verify-phase format check surfaced a pre-existing `ruff format` nonconformance in the TEA-authored test file (one over-wrapped short `assert` from the RED commit). Applied the deterministic project formatter to the **in-scope test file only** — semantics unchanged (1 insertion, 3 deletions, single assert collapsed). A separate, pre-existing, unrelated nonconformance in `core.py:534` (`register_region_section`) was deliberately left untouched and logged as a non-blocking Improvement finding rather than injecting unrelated churn into a 3-point story's PR.

**Quality Checks:** All passing — `ruff check` clean on both changed files; full regression sweep **163/163 green** (story file 14/14, `test_npc_identity_drift` 33, `test_disposition_attitude_enum` 18, `test_query_npc` 8, `test_prompt_framework/` 90). No regression from the simplify/format edits.

**Overall:** simplify: applied 1 fix (+ 1 in-scope format normalization); no reverts; code unchanged in behavior.

**Handoff:** To Reviewer (Colonel Potter) for code review. Reviewer note: the verbatim session ACs (lines 47-70) are superseded — the 14-test contract + TEA/Architect deviation manifest are authoritative (fictional 5-tier enum, wrong seam, self-contradictory AC-3; all Option-A per Architect spec-check).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (6235 pass / 0 fail / 400 pre-existing skips; 0 smells, 0 TODOs) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (1 enabled subagent returned; 8 disabled via `workflow.reviewer_subagents` — domains assessed directly by Reviewer below)
**Total findings:** 0 confirmed blocking, 0 dismissed, 2 deferred (non-blocking Improvement/Question — see Delivery Findings)

Since 8 specialist domains are disabled via settings, I assessed edge/silent-failure/test/doc/type/security/simplify/rule domains myself (see Observations + Rule Compliance).

## Reviewer Assessment

**Verdict:** APPROVED

**Diff:** 8 lines in `sidequest/agents/prompt_framework/core.py` (1 statement + a 7-line WHY comment) + new `tests/agents/test_npc_roster_attitude.py` (14 tests). 320 additions, 0 deletions.

### Observations

1. `[VERIFIED]` **Perception firewall holds.** `parts.append(f"[attitude: {npc.disposition.attitude().value}]")` (core.py:478) emits ONLY the coarsened band — `Disposition.attitude()` returns `Attitude` StrEnum (`disposition.py:77-82`), values lowercase `friendly/neutral/hostile` (`:52-54`). The raw `disposition.value` int never reaches the always-on narrator roster. Complies with ADR-104/105 and the disposition.py "narrator reasons in attitudes, world-state agent reasons in numbers" doctrine. Test `test_roster_does_not_leak_raw_disposition_integer` + the `-50`/`60` wiring assertions enforce it.
2. `[VERIFIED]` **No None / AttributeError path.** `Npc.disposition: Disposition = Field(default_factory=Disposition)` (session.py:140) — always a `Disposition`; pydantic coerces legacy int via the core-schema union. `.attitude()` is total over the constructor-clamped −100..+100. No crash surface.
3. `[VERIFIED]` **No parser-contract break.** Grep across `sidequest/**/*.py`: nothing machine-parses the `npc_roster` content or the `[attitude:`/`[last seen:` tags — it is freeform narrator-prompt text. The bracket-tag idiom is the established `[last seen: …]` precedent (core.py:470). Adding `[attitude: …]` introduces no downstream schema dependency.
4. `[VERIFIED]` **Wired end-to-end.** Production call site `orchestrator.py:1523` passes `npcs=context.npcs` into `register_npc_roster_section`; the two async wiring tests prove the band reaches the built prompt's `npc_roster` section (Early zone / State category) through the real `Orchestrator.build_narrator_prompt`. Not a unit-only illusion.
5. `[VERIFIED]` **Minimalism & pattern fidelity.** Unconditional append is correct (every NPC has a default `Disposition`; contrast the Optional `last_seen_location` guard). No helper, no abstraction, no scope creep — exactly the one line the contract demands. Gaslight discipline intact: attitude is the "only emotional perception is POV" layer the closing roster instruction (core.py:473-476) already declares.
6. `[LOW]` `[TEST]` Three smoke tests use bare `assert "<band>" in content` instead of the stricter `_band_in` (test file:142-149). Safe today; logged as a non-blocking Improvement for optional hardening.
7. `[LOW]` v1 single global `Disposition` → in MP all players' narrator rosters show the same band (per-PC is forward-looking per query_npc.py docstring). Not introduced/regressed here; logged as a non-blocking Question for 50-13/spec-reconcile awareness.
8. `[VERIFIED]` **Comment quality.** The 7-line comment states the non-obvious WHY (the ADR-104/105 firewall constraint and the per-NPC round-trip it eliminates) — load-bearing rationale, not a what-restatement. Compliant with project comment doctrine.

### Rule Compliance

Checked against `.pennyfarthing/gates/lang-review/python.md` (14 checks), `CLAUDE.md`, `SOUL.md` (no `.claude/rules/` dir exists).

- **#1 silent exceptions / #2 mutable defaults / #5 paths / #7 resource leaks / #8 unsafe deser / #12 deps** — none introduced (pure in-memory string append). Compliant (N/A).
- **#3 type annotations** — one line inside an existing fully-typed method; no new signature. Compliant.
- **#4 logging** — serialization path, not an error path; no logging required. Compliant (N/A).
- **#6 test quality** — 14 tests, meaningful assertions; `_band_in` rejects vacuous/no-match; one *documented intentional* invariant guard (`test_pool_only_members_get_no_attitude_token`). One LOW hardening note (#6 above). Compliant.
- **#9 async** — both wiring tests `await orch.build_narrator_prompt` correctly; no blocking call, no missing await. Compliant.
- **#10 import hygiene** — all test imports used; no star import; `from __future__ import annotations`. Compliant.
- **#11 input validation** — band is `Attitude`-enum-constrained, not user input; NPC name/appearance were already unescaped pre-existing (no new injection surface; enum value cannot inject). Compliant.
- **#13 fix-introduced regressions** — full suite 6235/0. Compliant.
- **#14 state-cleanup ordering w/ fallible side effect** (origin 50-4 I3) — the per-NPC `parts.append` mutates local `parts`/`lines` BEFORE the single terminal `register_section(...)` call; no consume-then-clear introduced. TEA flagged this proactively; **verified compliant**.
- **CLAUDE.md "No Silent Fallbacks"** — band is unconditionally emitted; no silent skip. Compliant.
- **CLAUDE.md OTEL principle** — serialization enrichment surfaced via the existing prompt-zones dashboard (the `npc_roster` PromptSection the GM panel renders); CLAUDE.md explicitly exempts cosmetic serialization from a bespoke span. The GM-panel lie-detector requirement IS met (the band is dashboard-visible). Compliant.
- **SOUL.md "Diamonds and Coal" / "The Test"** — one band word per NPC line is proportional, not overbaiting; introduces no player-action text. Compliant.

### Devil's Advocate

Argue this is broken. *First attack — the firewall comment is aspirational, not enforced.* A comment saying "MUST NOT leak the int" is worthless if the code can. But it cannot: `.attitude()`'s return type is the `Attitude` StrEnum and `.value` is one of three lowercase literals; there is no code path from `npc.disposition.attitude().value` to the integer. The firewall test pins disposition=37→"friendly" and asserts "37" absent. Attack fails.

*Second — a hostile NPC named "37th Street Tough" or an appearance "scarred, ~50 years"* would put a bare number in the roster line and the firewall test would still pass for THAT npc (different fixture), but the production concern is: does the *attitude tag itself* ever carry a number? No — the tag is `[attitude: <enum>]`, numbers in name/appearance are pre-existing author-supplied identity, unrelated to disposition leakage. Not a 50-12 regression.

*Third — what if `npc.disposition` is a raw int on a legacy save?* The pydantic core schema (`disposition.py:90-119`) coerces int→`Disposition` on load; `.attitude()` exists on the wrapper, not the int. If a truly malformed save bypassed validation, model construction would already have failed upstream long before the roster — this line is not the weak point.

*Fourth — empty/extreme inputs.* Disposition constructor clamps to ±100; `attitude()` is total (>10 / <−10 / else). No NPCs → the outer `if not npc_pool and not npcs: return` short-circuits (unchanged). One NPC, 0 disposition → "neutral". Boundary 10/11/−10/−11 all tested. No unhandled branch.

*Fifth — a confused future maintainer* deletes the firewall comment and "optimises" to `f"[disp: {npc.disposition.value}]"`. That is a future hypothetical, not this diff; and the firewall test would fail loudly (red CI) — exactly the guard rail TEA built. *Sixth — MP perception:* the global-disposition band is identical for all players. Real, but it is the documented v1 model (query_npc.py) and pre-dates this story; logged as a non-blocking Question, not a 50-12 defect. No attack lands as Critical/High.

### Verdict Detail

**Data flow traced:** `Npc.disposition` (default_factory `Disposition`, or pydantic-coerced int on load) → `register_npc_roster_section` per-NPC loop → `npc.disposition.attitude().value` (3-tier StrEnum value, coarsened — firewall-safe) → `[attitude: <band>]` appended to the `npc_roster` PromptSection (Early/State) → `Orchestrator.build_narrator_prompt` → narrator prompt + prompt-zones GM dashboard. Safe: no raw int on the path; no user-controlled value in the tag.

**Pattern observed:** bracket-tag roster idiom mirrors `[last seen: …]` at core.py:470 — consistent, no new pattern introduced.

**Error handling:** no new failure modes; `.attitude()` total over clamped domain; no None path (default_factory).

**Zero Critical/High.** Two LOW observations recorded as non-blocking Delivery Findings. Implementation is minimal, correct, firewall-respecting, fully wired, and well-tested. The 14-test contract + TEA/Architect deviation manifest are sound and accepted.

**Handoff:** To SM (Hawkeye Pierce) for finish-story.