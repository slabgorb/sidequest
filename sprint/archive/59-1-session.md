---
story_id: "59-1"
jira_key: "N/A"
epic: "Epic 59 — Confrontation Engagement Regression"
workflow: "tdd"
---

# Story 59-1: Narrator never calls advance_confrontation in tea_and_murder — social confrontations never engage

## Story Details
- **ID:** 59-1
- **Epic:** 59 — Confrontation Engagement Regression
- **Jira Key:** N/A (no Jira in this project)
- **Type:** Bug (P1, 5 points)
- **Workflow:** tdd
- **Stack Parent:** none
- **Repos:** sidequest-server

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-22T14:32:00Z
**Round-Trip Count:** 3

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-22 | 2026-05-22T09:12:49Z | 9h 12m |
| red | 2026-05-22T09:12:49Z | 2026-05-22T09:49:08Z | 36m 19s |
| green | 2026-05-22T09:49:08Z | 2026-05-22T11:35:31Z | 1h 46m |
| spec-check | 2026-05-22T11:35:31Z | 2026-05-22T11:38:26Z | 2m 55s |
| verify | 2026-05-22T11:38:26Z | 2026-05-22T13:21:19Z | 1h 42m |
| review | 2026-05-22T13:21:19Z | 2026-05-22T13:36:13Z | 14m 54s |
| green | 2026-05-22T13:36:13Z | 2026-05-22T13:56:37Z | 20m 24s |
| spec-check | 2026-05-22T13:56:37Z | 2026-05-22T13:58:10Z | 1m 33s |
| verify | 2026-05-22T13:58:10Z | 2026-05-22T14:02:07Z | 3m 57s |
| review | 2026-05-22T14:02:07Z | 2026-05-22T14:10:27Z | 8m 20s |
| green | 2026-05-22T14:10:27Z | 2026-05-22T14:15:18Z | 4m 51s |
| spec-check | 2026-05-22T14:15:18Z | 2026-05-22T14:15:48Z | 30s |
| verify | 2026-05-22T14:15:48Z | 2026-05-22T14:18:11Z | 2m 23s |
| review | 2026-05-22T14:18:11Z | 2026-05-22T14:23:37Z | 5m 26s |
| green | 2026-05-22T14:23:37Z | 2026-05-22T14:25:25Z | 1m 48s |
| spec-check | 2026-05-22T14:25:25Z | 2026-05-22T14:25:48Z | 23s |
| verify | 2026-05-22T14:25:48Z | 2026-05-22T14:26:07Z | 19s |
| review | 2026-05-22T14:26:07Z | 2026-05-22T14:30:49Z | 4m 42s |
| spec-reconcile | 2026-05-22T14:30:49Z | 2026-05-22T14:32:00Z | 1m 11s |
| finish | 2026-05-22T14:32:00Z | - | - |

## Story Context

> **⚠ SUPERSEDED (re-framed 2026-05-22, Houlihan).** The "Story Context",
> "Root Cause Analysis", and "Acceptance Criteria" blocks BELOW are the original
> setup snapshot and contain the WRONG premise (that engagement = calling
> `advance_confrontation`). The AUTHORITATIVE, mechanism-correct ACs and root
> cause are in: (1) the re-framed ACs in `sprint/current-sprint.yaml`,
> (2) `sprint/context/context-story-59-1.md` → **Architecture Decision**, and
> (3) the **TEA Assessment** + **Delivery Findings** in this file. Read those;
> treat everything in this section as historical.
>
> **⚠ FURTHER SUPERSEDED (Story 59-4, 2026-05-24, ADR-113).** Story 59-1
> shipped the narrator-owned engagement signal (`begin_confrontation` SDK
> tool → `result.confrontation` lift → `narration_apply` consumer); Story 59-4
> retired that entire chain atomically and migrated confrontation engagement
> onto the Intent Router engagement spine. ACs 1–6 here (which describe the
> `begin_confrontation` / `result.confrontation` mechanism) are now historical
> — the live engagement mechanism is
> `sidequest/server/intent_router_pass.execute_intent_router_pre_narrator_pass`
> → `sidequest/agents/subsystems/confrontation.run_confrontation_dispatch`,
> running BEFORE the narrator. See `sprint/archive/59-4-session.md` and
> `docs/adr/113-intent-router-mechanical-engagement-spine.md`.

### Problem Statement

Found in 2026-05-21 Glenross (tea_and_murder) solo playtest. The SDK narrator never calls `advance_confrontation`, so the social-confrontation engine (negotiation/trial/auction/social_duel/scandal) never engages. The narrator writes full confrontation prose with no engine state behind it — a SOUL/OTEL "winging it" violation (ADR-002, ADR-031).

### Repro

**Scenario:** Glenross solo; reach an NPC resisting questioning (Solicitor Ewan Forbes); escalate explicitly: **"I block his way and call the bluff: name your client or I'll have the Sergeant ask you"**

**Observed Behavior:** Narrator returns a textbook standoff ("he makes no move to go around Neil — but he makes no move to answer further, either") and NO confrontation engages.

### OTEL Evidence (Turn-by-Turn)

Every turn from the escalation onward logs:
- `game_patch.extracted ... beat_selections=0 confrontation=None`
- Narrator made tool_calls=1..4/turn (apply_world_patch, commit_known_fact)
- **advance_confrontation was invoked 0 times** across ~6 turns
- **0 confrontation.intent* spans** emitted

### Git Context (all on develop)

Epic 50 moved to a **narrator-declared-intent model**:
- **79cea7a** derive `intent_verb_set` per ConfrontationDef
- **60027da** validate(action_rewrite, declared, pack)
- **ad9381b** enumerate Victoria social types

Epic 50 also **deleted the lie-detector**:
- **93c7659** DELETED `_CONFRONTATION_TRIGGER_PATTERNS` — the keyword-based detector that caught narrated-confrontation-without-engine-state

### Root Cause Analysis

Tool is **registered** (agents/tools/__init__.py) and output_only_sdk.md §4 has strong trigger criteria (negotiation/social_duel/scandal), so it's a **behavior/wiring gap**, not a missing tool. Likely causes:

1. SDK tool selection is driven by tool DESCRIPTION, not system prompt (ADR-111)
2. tea_and_murder's derived `intent_verb_set` is too narrow to match natural prose
3. advance_confrontation not actually in the per-turn tool list offered to the narrator (registered ≠ offered)

## Acceptance Criteria

1. **In a tea_and_murder session, an explicit social escalation** (accusation / blocking someone's path / formal challenge) causes the narrator to call `advance_confrontation` on the same turn, with the most specific social type (negotiation/social_duel/trial/auction/scandal) — verified via OTEL (confrontation != None, intent span present).

2. **Verify advance_confrontation is actually in the per-turn tool list** handed to the SDK narrator for tea_and_murder (registered != offered).

3. **Audit the advance_confrontation tool DESCRIPTION** (not just the system prompt) for social-confrontation coverage, since SDK tool selection keys on the description (ADR-111).

4. **Confirm tea_and_murder ConfrontationDefs derive an intent_verb_set** broad enough that natural narrator prose can match (per 79cea7a).

5. **Restore a non-keyword OTEL lie-detector:** a watcher event that flags "narration reads as a confrontation but advance_confrontation was not called this turn", replacing the deleted `_CONFRONTATION_TRIGGER_PATTERNS` so this cannot regress silently again.

6. **Add a regression test** that drives a social escalation turn for tea_and_murder and asserts `advance_confrontation` is invoked / confrontation state is non-None.

## Sm Assessment

Story is well-formed and ready for RED. This is a p1 behavioral regression with a
concrete repro (Glenross / Solicitor Ewan Forbes escalation), hard OTEL evidence
(6 turns, `advance_confrontation` invoked 0 times, 0 `confrontation.intent*` spans),
and a clear git provenance from the Epic 50 keyword→declared-intent shift plus the
`93c7659` deletion of the keyword lie-detector.

Routing note for TEA (Radar): the 6 ACs split into two test surfaces —
(a) **behavioral**: a social-escalation turn must drive `advance_confrontation` /
non-None confrontation state (AC1, AC6), and (b) **regression-proofing**: restore a
non-keyword OTEL lie-detector for "narration reads as confrontation but engine never
engaged" (AC5). ACs 2–4 are diagnostic audits (tool offered? tool description covers
social? intent_verb_set wide enough?) that should be confirmed before/while writing
the failing test so RED targets the real gap, not a guessed one. Per project rule, the
regression test must be fixture-based — do not assert against live `genre_packs/*`.

Single repo: sidequest-server. No Jira (project never uses it). Merge gate clear at
setup (only Dependabot PRs open).

## Delivery Findings

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)

- **Improvement** (non-blocking): `_SDK_TOOL_OWNED_FIELDS` maps `confrontation` → "confrontation_advances / encounter_advances" (orchestrator.py:957), but those are the ADVANCE tools — they cannot WRITE the start field. That mislabel was part of the bug's confusion. Now that `begin_confrontation` is the SDK start-writer, the comment is stale. Affects `sidequest/agents/orchestrator.py` (the `_SDK_TOOL_OWNED_FIELDS` comment for `confrontation`/`beat_selections` should name `begin_confrontation`). Left as-is to keep the diff scoped to the fix; cosmetic.
- **Gap** (non-blocking): The legacy `claude -p` path still registers `CONFRONTATION_TRIGGER_CONSTRAINT` in the Recency zone via `_maybe_register_legacy_guardrail` (orchestrator.py:1954) — unchanged and correct (ADR-111 backend-gates). But the orchestrator comment at orchestrator.py:1911 still references the deleted `narration_apply._scan_for_confrontation_trigger_keywords` lie-detector. Stale comment only; affects `sidequest/agents/orchestrator.py`.
- **Question** (non-blocking): `begin_confrontation` is the SDK engagement *signal*, but whether the live `tea_and_murder` narrator actually CALLS it on a social escalation is the LLM's free tool-choice — not unit-testable (per TEA's substrate-only deviation). Needs the OQ-2 Glenross playtest loop to confirm the original repro (Solicitor Ewan Forbes standoff) now engages a `negotiation`. Affects the Epic 59 close criteria.
- **Gap** (non-blocking, potential P1 — surfaced during rework): SDK WRITE tools that mutate via `ctx.store.load()` → mutate → `ctx.store.save()` (e.g. `apply_damage`, `apply_status`, `advance_encounter_beat`, `advance_confrontation`) write to a FRESH deserialized snapshot, while the canonical in-memory `sd.snapshot`/`room._snapshot` is what `room.save()` persists at turn end — **and nothing reloads the canonical from the store after the dispatch loop** (verified: `SqliteStore.load` deserializes fresh at persistence.py:466; `SessionRoom.save` persists `self._snapshot` at session_room.py:279; no reload in `_execute_narration_turn` or the orchestrator SDK path). I empirically reproduced the clobber for the confrontation field. If this is live for the other WRITE tools, their mutations are lost at turn end. Story 59-1 sidesteps it for confrontation by routing through `result.confrontation` → narration_apply (in-place canonical mutation). The broader question — do HP/status/beat mutations actually round-trip? — needs a dedicated end-to-end test (none exists) and likely a post-dispatch canonical reload or an in-place-mutation rework of the SDK tool persistence model. **Out of 59-1 scope; flagged for the SDK-backend owner.** Affects `sidequest/agents/tools/*` + `sidequest/server/websocket_session_handler.py` persistence phase.

### TEA (test design)

- **Conflict** (blocking): The story's central premise — "narrator never calls `advance_confrontation`, so social confrontations never engage" — mis-identifies the engagement mechanism. Engagement (STARTING a confrontation) is the narrator populating the **`confrontation` field** in its `game_patch`, NOT a call to `advance_confrontation`. `advance_confrontation` only *advances an already-active* `StructuredEncounter` dial and "fails fatally if no encounter is active" (`sidequest/agents/tools/advance_confrontation.py:124-128`); the guardrail confirms "Only emit `confrontation` on the turn the encounter STARTS; once it is active, use `beat_selections`" (`sidequest/agents/narrator_guardrails.py:109-111`). So "`advance_confrontation` invoked 0 times" is EXPECTED when no encounter started — the real OTEL signal was `confrontation=None`. **Affects ACs 1, 2, 3, 6** (they audit/assert the wrong tool). Affects `sprint/context/context-story-59-1.md` and the Epic 59 ACs — needs Architect re-framing to the real mechanism.
  *Found by TEA during test design.*

- **Gap** (non-blocking): The social trigger criteria (negotiation/trial/auction/social_duel/scandal, with concrete prose cues) DO exist — but in `CONFRONTATION_TRIGGER_CONSTRAINT`, a **Recency-zone guardrail for the legacy `claude -p` path** (`narrator_guardrails.py:56-113`). The default backend is the Anthropic SDK (ADR-101), where tool *descriptions* drive selection, not the recency zone (ADR-111). The likely real gap: whether the SDK-offered engagement tool description (`generate_encounter` / `apply_world_patch` `confrontation` field) carries these social triggers. This is where a failing test belongs, once ACs are re-framed.
  *Found by TEA during test design.*

- **Gap** (non-blocking): The "restore a non-keyword lie-detector" mechanism (AC5) partly exists — `confrontation_intent_validator.validate()` emits `confrontation.intent_mismatch` spans — but it only fires when the narrator emits an `action_rewrite.intent` to tokenize (returns `None` when `action_rewrite is None`; see `test_validate_returns_none_when_action_rewrite_is_none`). The playtest failure was the narrator emitting NOTHING, which the validator structurally cannot catch. The restored detector must cover "confrontation-shaped prose, no `confrontation` field, AND no intent." Affects `sidequest/agents/confrontation_intent_validator.py` + its production call site in `narrator_guardrails.py`.
  *Found by TEA during test design.*

## Design Deviations

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)

- **Chose a dedicated `begin_confrontation` tool over extending `apply_world_patch`**
  - Spec source: context-story-59-1.md, "Architecture Decision (Houlihan)" + "Recommended fix direction (reuse-first)"
  - Spec text: "extend the existing `apply_world_patch` tool to carry the `confrontation` engagement field … A new dedicated `begin_confrontation` tool is an acceptable alternative … Dev: confirm the exact `result.confrontation` assembly site on the SDK path before choosing extension vs new tool."
  - Implementation: added a new WRITE tool `sidequest/agents/tools/begin_confrontation.py` (arg `confrontation_type`) that creates the `StructuredEncounter` during SDK tool-dispatch via `instantiate_encounter_from_trigger`; relocated `CONFRONTATION_TRIGGER_CONSTRAINT` onto its description; left `apply_world_patch` untouched.
  - Rationale: confirmed the assembly site — `result.confrontation` is in `_SDK_TOOL_OWNED_FIELDS` and is **zeroed** by `_assemble_turn_result_sdk` (orchestrator.py:3082), so a tool cannot "carry the field" through to `narration_apply`; the writer must create the encounter itself during dispatch. Two further reasons against `apply_world_patch`: (1) it is the ADR-011 deprecation-targeted *escape hatch* (target = zero spans across 10 playtests) — bolting a load-bearing engagement path onto it is the wrong home, and its `path`/`value` required args make confrontation-only calls awkward; (2) story 57-4's `test_confrontation_guardrail_migrates_into_an_encounter_tool` requires the trigger fingerprint on a tool whose name contains `confront`/`encounter` — `begin_confrontation` satisfies that filter, `apply_world_patch` does not. The Architect pre-authorized this as "acceptable."
  - Severity: minor
  - Forward impact: ADR-111's routing table named `generate_encounter` as the SDK home for `confrontation_trigger_constraint`; that home is now `begin_confrontation`. If ADR-111 or ADR-033/102 is amended to ratify the tool→engagement contract (the story context flags this), reference `begin_confrontation`. Sibling Epic-59/60 stories assuming `apply_world_patch` carries `confrontation` should target `begin_confrontation` instead.

- **Relocated `CONFRONTATION_TRIGGER_CONSTRAINT` OFF `generate_encounter` (TEA's AC3 tests retargeted)**
  - Spec source: context-story-59-1.md, AC-3 + Scope ("this story only relocates the trigger criteria off it"); TEA Design Deviation "AC3 description test targets `apply_world_patch` specifically" (forward impact: "retarget the AC3 test and re-log")
  - Spec text: "move the social trigger criteria onto *that* live tool's description (off the dead `generate_encounter` stub)"
  - Implementation: removed the constant + import from `generate_encounter.py` (its description now states engagement routes through `begin_confrontation`). Updated 59-1 AC3 positive test (`test_live_engagement_tool_description_carries_social_triggers`) to assert against `begin_confrontation`, and rewrote AC3 negative (`test_generate_encounter_cannot_be_the_engagement_path`) from a description-text precondition to a structural assertion (generate_encounter exposes no engagement field) per repo CLAUDE.md "No Source-Text Wiring Tests." TEA's RED test message explicitly anticipated this move ("If this fails, the criteria have moved — re-check AC3 home").
  - Rationale: keying the SDK narrator's start-confrontation criteria to an always-erroring stub mis-routed the call — that mis-routing IS the engagement-regression root cause the story fixes. Leaving it on the stub would only partially close the gap.
  - Severity: minor
  - Forward impact: none beyond the ADR-111 routing note above.

- **AC5 watcher kept the proposed span name `confrontation.unengaged_turn`; fires on the no-intent blind spot**
  - Spec source: context-story-59-1.md, AC-5; TEA Design Deviation "AC5 watcher span name is prescribed, not specified"
  - Spec text: "a non-keyword OTEL watcher fires when a turn is confrontation-shaped but nothing engaged AND no `action_rewrite.intent` was emitted … Must NOT reintroduce prose keyword-scanning."
  - Implementation: emits `confrontation.unengaged_turn` (no rename — `_UNENGAGED_SPAN` unchanged) from `narration_apply` when, with a pack loaded, `not result.confrontation` AND no active encounter AND `_intent_text == ""`. The structural discriminator is the **absent intent** (the validator's documented blind spot), NOT prose content — no keyword scan. The two synthetic fixtures (positive: no field/no intent; negative: engaged field) are structurally identical except the engagement field, so absent-intent + no-engagement is the only non-keyword signal available, and is the correct one (a turn the validator could not even evaluate).
  - Rationale: with no `action_rewrite.intent`, `confrontation_intent_validator.validate()` returns `None` and the existing `intent_mismatch` span never fires — the exact silent miss from the 2026-05-21 playtest. The watcher closes that one blind spot via a structured signal; the deleted `_CONFRONTATION_TRIGGER_PATTERNS` regex stays dead (one-mechanism-per-problem).
  - Severity: minor
  - Forward impact: superseded by the rework entry below — the watcher is now precise (opponent-NPC-gated), not "rare by design."

- **REWORK (post-review): begin_confrontation does NOT create the encounter; engagement routes through result.confrontation → narration_apply on the CANONICAL snapshot**
  - Spec source: Reviewer Assessment C1/C2/C3 (this file); CLAUDE.md "Verify Wiring, Not Just Existence"
  - Spec text (Reviewer): "begin_confrontation mutates a fresh ctx.store.load() snapshot, distinct from the canonical sd.snapshot used by the AC5 watcher + room.save — no reload reconciles them; the encounter may be clobbered at turn end."
  - Implementation: **Verified the clobber empirically** — a tool's `ctx.store.save` write is overwritten by end-of-turn `room.save(canonical)` (`SqliteStore.load` deserializes fresh; `SessionRoom.save` persists the canonical in-memory object; nothing reloads after the dispatch loop). Reworked: (1) `begin_confrontation` validates type + active-encounter and emits OTEL (`tool.begin_confrontation.signalled`) but no longer creates/persists an encounter; (2) `_assemble_turn_result_sdk` sets `result.confrontation` from the begin_confrontation tool-call ledger, validated against `context.available_confrontations`; (3) removed `confrontation` from `_SDK_TOOL_OWNED_FIELDS` so narration_apply's existing consumer creates the encounter on the canonical snapshot in place — ONE creation mechanism on BOTH backends. Also: C2 (gate watcher on `not already_reprompted`), C3 (require an opponent-side NPC — the structural confrontation-shape signal — so the watcher does not fire on quiet turns), C4 (tool no longer calls instantiate, so the false "ValueErrors crash the turn" comment is gone), C6/C7 (stale comments + test annotations).
  - Rationale: the original "tool creates the encounter during dispatch" framing was wrong — an SDK tool cannot mutate the canonical snapshot; only narration_apply (and other in-place mutators) can, and `room.save` persists only the canonical. This also fixes the AC5 false-positive (result.confrontation is now set on engaged turns).
  - Severity: major (corrects a non-functional engagement path)
  - Forward impact: the ADR-111 note (orchestrator docs) still holds — begin_confrontation is the narrator-facing start signal. New SDK-assembly seam: a START-confrontation tool sets `result.confrontation` via the ledger, NOT a tool ctx.store write. Sibling stories must follow that. The broader SDK-tool store-clobber (advance_encounter_beat / apply_damage share the pattern) is flagged in Delivery Findings for separate investigation.

### TEA (test design)

- **AC5 watcher span name is prescribed, not specified**
  - Spec source: context-story-59-1.md, AC-5
  - Spec text: "Restore/extend a NON-KEYWORD OTEL watcher that fires when a turn is confrontation-shaped but nothing engaged"
  - Implementation: the RED test asserts a concrete span name `confrontation.unengaged_turn` (constant `_UNENGAGED_SPAN` in `tests/server/test_59_1_confrontation_engagement.py`); the spec leaves the name open.
  - Rationale: a behavioral OTEL-span test needs a concrete observable; chose a descriptive name as the proposed contract and documented it as adjustable in the test docstring.
  - Severity: minor
  - Forward impact: Dev may rename the span — if so, update `_UNENGAGED_SPAN` and re-log. The behavior (fires on no-emission confrontation-shaped turn; silent on engaged turn) is the binding contract.

- **LLM tool-choice is NOT unit-tested (substrate-only)**
  - Spec source: context-story-59-1.md, AC-1 / AC-6
  - Spec text: "an explicit social escalation … causes the narrator to call …" / "drives the engagement path end-to-end"
  - Implementation: tests pin the deterministic `result.confrontation` → `StructuredEncounter` substrate, NOT the SDK model's free decision to set the field.
  - Rationale: an LLM's tool/field selection is non-deterministic and cannot be asserted in a unit test; per the re-framed ACs this is a playtest deliverable.
  - Severity: minor
  - Forward impact: live confirmation that the narrator actually engages social confrontations in `tea_and_murder` must happen at playtest — flagged for Reviewer + the OQ-2 playtest loop, not gated by this suite.

- **AC3 description test targets `apply_world_patch` specifically**
  - Spec source: context-story-59-1.md, AC-2 / AC-3
  - Spec text: "the LIVE engagement tool the SDK narrator actually uses"
  - Implementation: AC2 (writer-exists) is impl-agnostic, but the AC3 description test asserts social triggers on `apply_world_patch` (the Architect's reuse-first recommendation).
  - Rationale: a description assertion needs a concrete tool target; chose the recommended one.
  - Severity: minor
  - Forward impact: if Dev adds a dedicated `begin_confrontation` tool instead of extending `apply_world_patch`, retarget the AC3 test and re-log.

### Architect (reconcile)

Reviewed every TEA and Dev deviation entry against the source documents and the merged code; all are accurate, fully-fielded, and self-contained. Verification:

- TEA "AC5 span name prescribed" — accurate; `confrontation.unengaged_turn` is the live span name (`telemetry/spans/confrontation_intent.py`). Honored.
- TEA "LLM tool-choice not unit-tested (substrate-only)" — accurate; live tool-choice is the OQ-2 playtest deliverable. Carried to Delivery Findings.
- TEA "AC3 description test targets `apply_world_patch`" — its forward-impact ("if Dev adds a dedicated begin_confrontation tool, retarget AC3 + re-log") was realized exactly: Dev's REWORK chose `begin_confrontation` and retargeted AC3. Closed.
- Dev "Chose begin_confrontation over apply_world_patch" — accurate; spec source (context "Architecture Decision") quoted correctly; the assembly-zeroing premise verified against `_assemble_turn_result_sdk`.
- Dev "Relocated CONFRONTATION_TRIGGER_CONSTRAINT off generate_encounter" — accurate; constant now on `begin_confrontation.description`, removed from `generate_encounter`.
- Dev "AC5 watcher / no-intent blind spot" — superseded by the REWORK entry; the live watcher is opponent-gated + reprompt-guarded.
- Dev "REWORK: route via result.confrontation → narration_apply" — the load-bearing deviation; spec source (Reviewer C1) and the empirically-verified clobber are accurate; engagement is created on the canonical snapshot, one mechanism on both backends.

**No additional deviations found.** The single forward-carried item is the broader SDK-tool store-clobber (apply_damage / advance_* share the load/mutate/save pattern), recorded in Delivery Findings as an out-of-scope spike for the SDK-backend owner — not a 59-1 deviation.

## TEA Assessment

**Tests Required:** Yes
**Reason:** p1 behavioral regression with concrete, mechanism-correct ACs.

**Test Files:**
- `sidequest-server/tests/agents/test_59_1_confrontation_engagement.py` — tool/prompt path (AC2, AC3, AC4) + negative anchors.
- `sidequest-server/tests/server/test_59_1_confrontation_engagement.py` — apply-path engagement consumer (AC1, AC6) + no-emission watcher (AC5), all fixture-based.

**Tests Written:** 10 tests covering 6 ACs.
**Status:** RED (4 failing, ready for Dev) — verified via testing-runner (RUN_ID 59-1-tea-red, serial).

| Test | AC | State | Meaning |
|------|----|-------|---------|
| some_sdk_tool_can_write_the_confrontation_engagement_field | 2 | **FAIL** | No SDK tool writes `result.confrontation` |
| advance_confrontation_is_not_the_engagement_writer | 2 | pass | Negative anchor (axis/delta, advance-only) |
| live_engagement_tool_description_carries_social_triggers | 3 | **FAIL** | Social triggers absent from `apply_world_patch` desc |
| generate_encounter_cannot_be_the_engagement_path | 3 | pass | Confirms criteria stranded on the dead stub |
| sdk_prompt_does_not_route_starting_through_advance_confrontation | 4 | **FAIL** | Prompt §4 still routes STARTING to advance_confrontation |
| confrontation_field_creates_structured_encounter | 1 | pass | Consumer anchor (field → encounter) |
| no_confrontation_field_creates_no_encounter | 1 | pass | Negative anchor |
| social_engagement_end_to_end_non_none_state | 6 | pass | Substrate anchor |
| unengaged_confrontation_turn_emits_watcher_span | 5 | **FAIL** | No-emission watcher span absent |
| engaged_turn_does_not_emit_unengaged_watcher_span | 5 | pass | No false-positive guard |

### Rule Coverage (python lang-review)

| Rule | Coverage | Status |
|------|----------|--------|
| #6 test quality | Self-checked: every test has a meaningful assertion + message; no `assert True`, no vacuous truthy checks, no skips/xfail. One false-pass (AC4) was caught via testing-runner and fixed (markdown line-wrap). | pass |
| #1 silent exceptions | Deferred to Dev GREEN — the new watcher/engagement path must not swallow errors (No Silent Fallbacks). Flagged for Dev. | dev-gate |
| #3 type annotations | Deferred — the new `confrontation` tool field + any new tool args must be annotated. Flagged for Dev. | dev-gate |
| #4 logging | Deferred — the watcher path must log/emit at correct severity (it's the GM-panel lie-detector). Flagged for Dev. | dev-gate |

**Rules checked:** #6 enforced in the test suite itself; #1/#3/#4 are implementation-time and flagged for Dev (TEA cannot enforce impl-code rules in RED).
**Self-check:** 1 vacuous/false-pass found (AC4, line-wrap) and fixed.

**Handoff:** To Dev (Winchester) for GREEN. Recommended path (Architect, reuse-first): extend `apply_world_patch` with a `confrontation` field, relocate `CONFRONTATION_TRIGGER_CONSTRAINT` onto its description, correct `output_only_sdk.md` §4, and emit the `confrontation.unengaged_turn` watcher (rename allowed → update `_UNENGAGED_SPAN`). If the SDK assembly can't carry the field cleanly, a `begin_confrontation` tool is the documented fallback — log a deviation.

## Dev Assessment

**Implementation Complete:** Yes
**Approach:** Took the documented `begin_confrontation` fallback (not the reuse-first `apply_world_patch` extension) after confirming `result.confrontation` is zeroed on the SDK assembly path — see Design Deviations for the full rationale.

**Files Changed (production):**
- `sidequest/agents/tools/begin_confrontation.py` — NEW. SDK engagement writer; creates the `StructuredEncounter` during tool-dispatch via `instantiate_encounter_from_trigger` (one creation mechanism shared with the legacy `narration_apply` consumer). Carries `CONFRONTATION_TRIGGER_CONSTRAINT` on its description (AC2 + AC3). Fails loudly on missing pack/PC; recoverable error when an encounter is already active.
- `sidequest/agents/tools/__init__.py` — register the new tool (28 → 29).
- `sidequest/agents/tools/generate_encounter.py` — relocated `CONFRONTATION_TRIGGER_CONSTRAINT` off the always-erroring stub; description now points engagement at `begin_confrontation` (AC3).
- `sidequest/agents/narrator_prompts/output_only_sdk.md` — §4 rewritten: STARTING routes to `begin_confrontation`; `advance_confrontation` is advance-only (AC4).
- `sidequest/telemetry/spans/confrontation_intent.py` — NEW `confrontation.unengaged_turn` span + `SpanRoute` + `confrontation_unengaged_turn_span` helper (AC5).
- `sidequest/server/narration_apply.py` — emit the no-emission watcher when `not result.confrontation` AND no active encounter AND no `action_rewrite.intent` (AC5). No prose keyword-scanning.
- `sidequest/agents/orchestrator.py` — added `TurnContext.pack`; stamp `genre_pack=context.pack` onto the SDK `ToolContext` so `begin_confrontation` can resolve the Confrontation Def.
- `sidequest/server/session_helpers.py` — populate `pack=sd.genre_pack` in `_build_turn_context`.

**Files Changed (tests):**
- `tests/agents/tools/test_begin_confrontation.py` — NEW. Registration, AC2 schema, encounter-creation happy path, already-active guard, fail-loud on missing pack/PC, and the mandatory registry-dispatch wiring test.
- `tests/agents/test_59_1_confrontation_engagement.py` — AC3 pos retargeted to `begin_confrontation`; AC3 neg rewritten to a structural assertion (deviation-logged).
- `tests/agents/test_narrator_uses_sdk_client.py` — tool-count 28 → 29.
- `tests/agents/test_50_24_dice_contract_parity.py` + `tests/agents/test_50_24_player_check_seam.py` — §4 forbiddance sentinels updated to name `begin_confrontation` (the corrected start tool).

**Rule coverage (TEA dev-gate items):**
- #1 silent exceptions — the `begin_confrontation` handler and the AC5 watcher fail/emit loudly: missing pack/PC → fatal `ToolResult.error`; `NoOpponentAvailableError` → recoverable error; unknown-type `ValueError` PROPAGATES (no swallow). No silent fallback.
- #3 type annotations — new args model (`confrontation_type: str`, `reason: str`) and span helper are fully annotated; `pyright` adds **0** new errors (the 28 reported are pre-existing baseline debt in narration_apply's encounter-resolution block, present identically on `develop`).
- #4 logging — the watcher logs at WARNING and emits the routed `confrontation.unengaged_turn` span (GM-panel lie-detector).

**Tests:** Full server suite **7164 passed, 400 skipped, 0 failed** (`uv run pytest -q`). All 4 RED tests now GREEN; no regressions. Lint clean (`ruff check`), formatted (`ruff format`).
**Branch:** `feat/59-1-confrontation-engagement-regression` (sidequest-server, pushed; commit `ca276bf`).

**Handoff:** To Architect (Houlihan) for spec-check, then TEA verify.
## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (one logged architectural deviation, resolved Option A)
**Mismatches Found:** 1 (the Dev's documented tool-choice deviation; no behavioral drift)

Reviewed the re-framed ACs (context-story-59-1.md "Architecture Decision"), the Dev
diff, and the full test surface. AC-by-AC:

- **AC1 (engagement consumer)** — `narration_apply.py:2531` `result.confrontation` →
  `StructuredEncounter` is UNCHANGED; the consumer anchor tests pass. Aligned.
- **AC2 (SDK writer exists)** — `begin_confrontation` exposes `confrontation_type` and
  creates the encounter during dispatch. Aligned. *Mismatch (below).*
- **AC3 (trigger criteria on a live tool)** — `CONFRONTATION_TRIGGER_CONSTRAINT` now
  rides `begin_confrontation`'s description and was removed from the `generate_encounter`
  stub. Aligned.
- **AC4 (prompt routing)** — `output_only_sdk.md` §4 routes STARTING to
  `begin_confrontation`; `advance_confrontation` is advance-only. Aligned.
- **AC5 (no-emission lie-detector)** — `confrontation.unengaged_turn` span fires on the
  no-engagement + no-intent blind spot; structural signal, no prose keyword-scan. Aligned.
- **AC6 (fixture regression)** — substrate anchors + the new `test_begin_confrontation.py`
  wiring test (registry-dispatch → mutated state). Aligned.

**Mismatch:**
- **Engagement writer is a new `begin_confrontation` tool, not an extension of `apply_world_patch`**
  (Extra-in-code vs the reuse-first recommendation — Architectural, Minor)
  - Spec: context "Recommended fix direction (reuse-first): extend the existing
    `apply_world_patch` tool … A new dedicated `begin_confrontation` tool is an
    acceptable alternative."
  - Code: new WRITE tool `begin_confrontation`; `apply_world_patch` untouched.
  - Recommendation: **A — update spec.** The deviation is sound and was pre-authorized
    as "acceptable." I confirm the load-bearing premise: `result.confrontation` is in
    `_SDK_TOOL_OWNED_FIELDS` and zeroed by `_assemble_turn_result_sdk` (orchestrator.py:3082),
    so no tool can "carry the field" through to `narration_apply` — the writer MUST create
    the encounter during dispatch. Routing engagement through the ADR-011 deprecation-target
    escape hatch would also have been wrong. The tool-choice is the better design. ADR-111
    amended this PR (orchestrator `docs/adr/111-…md`, 2026-05-22 implementation note):
    its routing rule already named a hypothetical `start_confrontation` tool and explicitly
    permits table refinement — `begin_confrontation` is that concretization; the routing
    rule is unchanged and honored.

The two consequent test edits (AC3 retarget; 50-24 §4 forbiddance sentinels renamed to
`begin_confrontation`) are correct — they track the corrected tool name, not a loosened
contract. The 57-4 `confront`/`encounter`-named-tool filter stays green because
`begin_confrontation` matches it.

**Note for the OTEL/ADR follow-up (non-blocking, Dev Delivery Findings):** the stale
`_SDK_TOOL_OWNED_FIELDS` comment (orchestrator.py:957) and the dead-reference comment at
orchestrator.py:1911 are cosmetic; out of scope for this fix's diff.

**Decision:** Proceed to TEA verify. No hand-back to Dev.
## TEA Assessment (verify — test verification)

**GREEN confirmed.** Full server suite re-run during green showed 7164 passed / 400 skipped / 0 failed; all 4 RED tests are now GREEN and the 6 ACs are covered (AC1/AC6 substrate anchors + the new begin_confrontation wiring test; AC2 schema; AC3 description + structural negative; AC4 prompt; AC5 the unengaged watcher span + no-false-positive guard).

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 8 (changed production files + the new test)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 1 finding | `additional_pc_names` comprehension duplicated in `begin_confrontation.py:138` and `narration_apply.py:~2552` |
| simplify-quality | clean | naming/architecture/error-handling/OTEL/wiring all conform |
| simplify-efficiency | clean | no over-engineering; loud errors + per-decision OTEL are CLAUDE.md-mandated, not excess |

**Applied:** 0 fixes.
**Flagged (noted, not applied):** 1 — the reuse finding. **Decision: do NOT extract.** It is a single expression duplicated across exactly two call sites (the legacy `narration_apply` consumer + the new SDK `begin_confrontation` writer), both in the encounter-engagement path. Per the project's pragmatic-restraint culture and the "rule of three / three-similar-lines-beats-premature-abstraction" principle, a one-line comprehension at two sites does not warrant a cross-layer shared helper. If a THIRD encounter-creation entry point appears, the clean home is a free function in `sidequest/server/dispatch/encounter_lifecycle.py` (already imported by both current sites — zero new coupling). Logged as a Dev-deviation forward note rather than churned now.
**Reverted:** 0.

**Overall:** simplify: clean (1 finding reviewed and intentionally deferred).
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (GREEN 7164/0/400; 0 smells) | N/A |
| 2 | reviewer-edge-hunter | Yes | findings | 6 | confirmed 3, dismissed 1, folded 2 |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 2 | confirmed 2 (snapshot-identity + comment-lie) |
| 4 | reviewer-test-analyzer | Yes | findings | 5 | confirmed 3, deferred 2 |
| 5 | reviewer-comment-analyzer | Yes | findings | 4 | confirmed 3, dismissed 1 (false positive) |
| 6 | reviewer-type-design | Yes | findings | 2 | dismissed 2 (convention-consistent, low) |
| 7 | reviewer-security | Yes | clean | 0 | N/A |
| 8 | reviewer-simplifier | Yes | findings | 1 | dismissed 1 (low stylistic) |
| 9 | reviewer-rule-checker | Yes | findings | 4 | confirmed 3, folded 1 (#14 into C1) |

**All received:** Yes (9 returned, 7 with findings)
**Total findings:** 9 confirmed, 5 dismissed (with rationale), 2 deferred

## Reviewer Assessment

**Verdict: CHANGES REQUESTED.** The core engagement fix (begin_confrontation) and the
trigger-criteria relocation are well-built and the suite is green — but adversarial
analysis surfaced a real, unverified correctness risk in the production round-trip plus
two concrete watcher defects. I verified the load-bearing facts against the code myself;
this is not a rubber-stamp pass.

### Confirmed findings (must address before merge)

**C1 — [SILENT][EDGE][RULE#14] Snapshot-identity gap: tool writes vs. canonical snapshot (HIGH, blocking).**
Verified by reading the code:
- `SqliteStore.load()` (persistence.py:466-527) deserializes a FRESH `GameSnapshot` every call — it does not return the live object.
- `begin_confrontation` does `session = ctx.store.load()` → mutates `session.snapshot` → `ctx.store.save(...)`. That snapshot is a DISTINCT object from the room's canonical `sd.snapshot`.
- `SessionRoom.save()` (session_room.py:279) persists the canonical in-memory snapshot at turn end; the orchestrator SDK path (orchestrator.py:3402) and `_execute_narration_turn` (websocket_session_handler.py:3298) do NOT reload/replace_with the canonical from the store after the tool-dispatch loop.
- Consequence (a): the AC5 watcher checks `snapshot.encounter` on the canonical `sd.snapshot` (narration_apply.py:2481) — which will be `None` even when begin_confrontation created an encounter on its fresh copy → **false-fire on every successful engagement turn.** Consequence (b): `room.save()` may clobber the tool's disk write → **the confrontation may not actually engage in the live session** — the story's core goal.
- This is shared by the other 26 SDK WRITE tools, so a reconciliation step likely exists — but I could not find it, and `test_narrator_sdk_hybrid_split` uses a SPY dispatch (never exercises the real store round-trip). Per repo "Verify Wiring, Not Just Existence" + "Every Test Suite Needs a Wiring Test": the story ships NO test proving the tool→canonical→watcher→room.save round-trip. The isolated `test_begin_confrontation_dispatched_through_registry_engages` asserts store state, not canonical-snapshot state.
- **Required:** an integration test that drives begin_confrontation through the full turn flow (orchestrator dispatch → narration_apply → room.save) and asserts (1) the encounter is live on the CANONICAL snapshot afterward, and (2) the AC5 watcher does NOT fire on that successful turn. If the encounter does not round-trip, fix the wiring (the same fix the other WRITE tools rely on). Rule-checker's #14 ordering finding folds into this — the save-then-mutate concern is moot once the round-trip is correct.

**C2 — [EDGE] AC5 watcher double-fires on the reprompt path (HIGH, blocking).**
`_apply_narration_result_to_snapshot` is called a second time with `already_reprompted=True` (websocket_session_handler.py:3326/3356). If the second result also has no confrontation/no intent, the unengaged span fires twice for one player turn. **Required:** gate the emission on `not already_reprompted` (the param is already threaded into this function) and add a test.

**C3 — [EDGE][SILENT][TEST] AC5 watcher fires on every quiet no-intent turn (HIGH).**
The condition (`not result.confrontation and _no_active_encounter and not _intent_text`) has no confrontation-shape signal, so it fires on ordinary travel/dialogue/rest turns that emit no intent. The AC5 positive test fixture is structurally identical to a peaceful turn (empty npcs, no confrontation, no intent), so it does not actually prove "confrontation-shaped" detection. **Required:** add the negative test (peaceful, confrontation=None, no intent) and EITHER narrow the production condition with a structural signal (e.g., an opponent-side NPC in `npcs_present`, updating the AC5 positive fixture to supply one) OR explicitly accept the breadth with a test that locks it + a documented GM-panel note. This was deviation-logged at green, but the breadth is unverified and the SOUL "cost scales with drama" lie-detector loses value if it fires every turn.

**C4 — [EDGE][SILENT][DOC] begin_confrontation error contract (MED).**
(a) The comment at begin_confrontation.py:150 ("Unknown-type / bad-side ValueErrors PROPAGATE — those crash the turn") is FACTUALLY WRONG: the registry's `except Exception` (tool_registry.py:258) absorbs them into ERROR_FATAL — the turn does not crash. (b) `SealedLetterArityError` (a ValueError subclass) is caught gracefully by narration_apply but not by the tool, so a sealed-letter social type with no npcs becomes an opaque ERROR_FATAL with `created` never set on the span. **Required:** catch ValueError (incl. SealedLetterArityError) explicitly, set `tool.begin_confrontation.created=False` + a named reason on the span, return a clear error; and correct the comment to describe actual behavior.

**C5 — [TEST] begin_confrontation error paths untested (MED).** Add tests: NoOpponentAvailableError → ERROR_RECOVERABLE with "no opponent available"; unknown confrontation_type → the (corrected, per C4) behavior.

**C6 — [DOC] Stale comments + docstring omission (LOW, cheap).** Dev-flagged + confirmed: orchestrator.py:957 `_SDK_TOOL_OWNED_FIELDS` comment should name `begin_confrontation` as the start-writer; orchestrator.py:1911 references the deleted `_scan_for_confrontation_trigger_keywords` (replace with the `confrontation.unengaged_turn` span); begin_confrontation.py module-docstring OTEL table omits `tool.begin_confrontation.reason`. Fix while in here (bounded).

**C7 — [RULE#3] Test type-annotation gaps (LOW).** `test_begin_confrontation.py:_call(arguments: dict)` → `dict[str, Any]`; `test_59_1...server::otel_capture()` fixture missing `-> Generator[InMemorySpanExporter, None, None]`.

### Deferred

- **AC4 source-text tombstone (rule-checker + test-analyzer, MED).** The AC4 test reads `output_only_sdk.md` and asserts a substring is ABSENT. It's a negative tombstone (weaker than the banned positive source-text wiring assertion) and is TEA's deliberate design. Deferred — note for TEA: prefer a behavioral check, but not blocking this story.
- **AC1≈AC6 near-duplicate (test-analyzer, MED).** Intentional consumer-anchor vs end-to-end-anchor per TEA Assessment; add a one-line comment distinguishing them. Non-blocking.

### Dismissed (with rationale)

- comment-analyzer "`with a pack loaded` docstring is misleading" — FALSE POSITIVE: the watcher emission is nested inside `if pack is not None:` (narration_apply.py:2442 → 2483); the docstring is accurate. Verified.
- type-design TypedDict-result + ConfigDict — low; every tool in the package uses the plain-dict + raw-dict-return convention; diverging in one tool would be inconsistent and the project rule (pydantic model w/ Field + extra=forbid) is already satisfied.
- simplifier inline-the-`result`-var — low stylistic; conflicts with type-design's TypedDict suggestion; harmless either way.
- rule-checker #14 save-then-mutate ordering — folded into C1 (moot once the round-trip is correct; mutation is internal to `instantiate_encounter_from_trigger`).
- `additional_pc_names` + test-fixture duplication — confirmed below rule-of-three by simplify pass and reviewer-simplifier; leave.

### Rule Compliance (lang-review/python.md, 14 checks + CLAUDE.md)

Rule-checker ran the full 14-check enumeration over all changed `.py` files + 4 CLAUDE.md rules (No Silent Fallbacks, No Stubbing, Verify-Wiring, OTEL-on-decisions). Pass except: #3 (2 test annotation gaps → C7), #6 (AC4 source-text tombstone → deferred), #14 (ordering → folded into C1). No violations of #1/#2/#4/#5/#7/#8/#9/#11/#12/#15-#18. Notably #15 (No Silent Fallbacks) PASSES in begin_confrontation's explicit error returns — but C4 shows the *documented* contract diverges from the registry's actual absorption behavior, which is why C4 is confirmed.

**Decision:** Hand back to Dev (Winchester). C1 (round-trip verification), C2 (double-fire), C3 (quiet-turn breadth), C4 (error contract), C5 (error-path tests) before re-review. C6/C7 cheap cleanups in the same pass. C1 is the priority — it questions whether the engagement actually persists in the live session.

### Dispatch-tag coverage (gate)

All specialist lanes assessed: [EDGE] C1/C2/C3, [SILENT] C1/C4, [TEST] C3/C5/C7, [DOC] C4/C6, [RULE] C7 + Rule Compliance, [TYPE] dismissed (convention-consistent, low), [SEC] clean (reviewer-security: 0 violations), [SIMPLE] dismissed (low stylistic; duplications below rule-of-three).

### Reviewer (deviation audit)

- Dev "Chose begin_confrontation over apply_world_patch" — **ACCEPTED.** Sound; architect-confirmed at spec-check; the assembly-zeroing premise verified.
- Dev "Relocated CONFRONTATION_TRIGGER_CONSTRAINT off generate_encounter" — **ACCEPTED.** Correct; removes the mis-routing root cause.
- Dev "AC5 watcher kept confrontation.unengaged_turn, fires on no-intent blind spot" — **FLAGGED.** The deviation's own forward-impact note ("rare by design; re-scope if intent-absent turns common") is exactly the unverified assumption findings C1/C3 challenge. Re-audit after rework.
- TEA "AC5 span name prescribed" — **ACCEPTED.** Name retained; behavior is the contract.
- TEA "LLM tool-choice not unit-tested (substrate-only)" — **ACCEPTED.** Correct; playtest deliverable.
- TEA "AC3 description test targets apply_world_patch" — **ACCEPTED.** Dev retargeted to begin_confrontation + logged, as the entry's forward-impact instructed.
## Dev Assessment (rework R1 — post-review)

**Rework Complete:** Yes. Addressed all Reviewer findings C1–C7.

**The core fix (C1):** Confirmed the Reviewer's snapshot-identity concern is a REAL clobber (empirically reproduced: a tool's `ctx.store.save` is overwritten by end-of-turn `room.save(canonical)`). Reworked engagement to route through `result.confrontation` → narration_apply, which mutates the **canonical** snapshot in place — the same single mechanism the legacy backend uses, clobber-free.

**Files changed (production):**
- `sidequest/agents/tools/begin_confrontation.py` — now a validate-and-signal tool (type ∈ genre, no active encounter, OTEL `signalled`); no longer creates/persists an encounter. Docstring rewritten to explain why the store write would be clobbered.
- `sidequest/agents/orchestrator.py` — `_assemble_turn_result_sdk` sets `result.confrontation` from the begin_confrontation tool-call ledger (validated vs `available_confrontations`); removed `confrontation` from `_SDK_TOOL_OWNED_FIELDS`; fixed the stale `_scan_for_confrontation_trigger_keywords` comment → names the `confrontation.unengaged_turn` span + `begin_confrontation`.
- `sidequest/server/narration_apply.py` — AC5 watcher now requires an opponent-side NPC (C3 precision) and is gated on `not already_reprompted` (C2 no double-fire).

**Files changed (tests):**
- `tests/agents/tools/test_begin_confrontation.py` — validate-and-signal semantics; asserts NO store mutation; unknown-type recoverable (C5); `.signalled` OTEL.
- `tests/agents/test_59_1_confrontation_engagement.py` — added the C1 assembler-wiring integration tests (begin_confrontation call → `result.confrontation`; unknown type → not routed) via a fake SDK through the real orchestrator.
- `tests/server/test_59_1_confrontation_engagement.py` — AC5 positive now includes an opponent NPC; added the quiet-turn negative (C3), the reprompt double-fire guard (C2), the canonical-persist round-trip (C1 part b); `otel_capture` return-type annotation (C7).
- `tests/agents/test_narrator_sdk_hybrid_split.py` + `tests/agents/test_narrator_output_format_backend_gate.py` — partition + field-map updated to reflect `confrontation` no longer being tool-owned-zeroed.

**Tests:** Full server suite **7169 passed / 400 skipped / 0 failed**. Lint clean, formatted, 0 new pyright errors (the lone orchestrator.py:2504 `send_stream` error is pre-existing on develop).

**New finding:** the broader SDK-tool store-clobber (apply_damage / advance_* share the pattern) is flagged in Delivery Findings as a potential P1 for the SDK-backend owner — out of 59-1 scope.

**Handoff:** To Architect (Houlihan) for spec-check re-run, then TEA verify, then Reviewer re-review.
## Architect Assessment (spec-check — R1 rework re-run)

**Spec Alignment:** Aligned. **Mismatches Found:** None.

Re-reviewed the rework against the ACs after the Reviewer's C1 reject. The
architectural correction is sound and tightens, not loosens, the design:

- **AC1/AC6 (engagement consumer)** — now the SOLE creation path on BOTH
  backends (narration_apply on the canonical snapshot). The rework strengthens
  the "one mechanism per problem" principle: there is no longer a parallel
  tool-store creation path that `room.save()` would clobber. Aligned, improved.
- **AC2 (SDK writer/signal)** — `begin_confrontation` still exposes
  `confrontation_type`; it is now a validate-and-signal tool, and
  `_assemble_turn_result_sdk` routes the type to `result.confrontation` via the
  tool-call ledger (validated against `available_confrontations`, so an unknown
  type cannot reach narration_apply). Aligned.
- **AC3 (trigger criteria on a live tool)** — unchanged on `begin_confrontation`. Aligned.
- **AC4 (prompt routing)** — unchanged (§4 → begin_confrontation). Aligned.
- **AC5 (lie-detector)** — now PRECISE: gated on an opponent-side NPC (structural
  confrontation-shape signal) and `not already_reprompted`. Resolves the
  false-positive-storm and double-fire the Reviewer flagged, without prose
  keyword-scanning. Aligned, improved.

**Verified the load-bearing claim myself:** `SqliteStore.load` deserializes fresh,
`SessionRoom.save` persists the canonical, no post-dispatch reload — so a tool
`ctx.store` write IS clobbered, and routing through `result.confrontation` (in-place
canonical mutation) is the correct fix. The Dev's empirical probe confirms it.

**ADR housekeeping:** corrected the ADR-111 implementation note (orchestrator
`docs/adr/111-…md`) — it previously said begin_confrontation "instantiates the
StructuredEncounter during tool-dispatch," which the rework makes false. Now
states the validate-and-signal → result.confrontation → narration_apply path.

**Delivery Finding concurrence:** the Dev's flagged broader SDK-tool store-clobber
(apply_damage / advance_* share the load/mutate/save pattern) is a legitimate
architectural concern worth a dedicated spike. Endorsed as out-of-scope for 59-1.

**Decision:** Proceed to TEA verify. No hand-back to Dev.
## TEA Assessment (verify — R1 rework re-run)

**GREEN confirmed** post-rework: full server suite 7169 passed / 400 skipped / 0 failed (Dev R1). The rework's new tests (assembler-wiring integration, canonical-persist round-trip, quiet-turn negative, reprompt double-fire guard) cover the C1/C2/C3 fixes.

### Simplify Report (R1)

**Teammates:** reuse, quality, efficiency · **Files Analyzed:** 4 (reworked production)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | no new duplication; type lookup centralized (find_confrontation_def), available-types reused from TurnContext |
| simplify-quality | clean | error-handling/OTEL/type-safety/architecture conform; 1 low note on comment completeness (no action — accurate) |
| simplify-efficiency | 1 finding | "assembler re-validates type → redundant" |

**Applied:** 0.
**Dismissed:** 1 — the efficiency finding (orchestrator.py:3105 type re-validation). **NOT redundant, do NOT remove.** The assembler reads the tool-call LEDGER (the calls the narrator made), NOT the tool RESULTS — so a begin_confrontation call with a type the tool REJECTED (recoverable error) still appears in the ledger. Without the `_ctype in available_confrontations` guard, that unknown type would be set on `result.confrontation` and reach `instantiate_encounter_from_trigger`, which raises `ValueError` (uncaught in the consumer) → crashes the turn. The guard is the load-bearing safety, pinned by `test_sdk_unknown_begin_confrontation_type_is_not_routed`. The agent's premise ("an invalid type would not be in the ledger") is incorrect.

**Overall:** simplify: clean (1 finding reviewed and dismissed with rationale).
## Subagent Results (R1 re-review)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (GREEN 7169/0/400) | N/A |
| 2 | reviewer-edge-hunter | Yes | findings | 3 | confirmed 1 (assembler honor-rejection), folded 1 (dead getattr), dismissed 1 (offered-list ['']—wrong), deferred 1 (resolved-edge) |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 2 | confirmed 1 (assembler honor-rejection, dup of edge), folded 1 (dead getattr) |
| 4 | reviewer-test-analyzer | Yes | findings | 3 | confirmed 1 (tautological negative test), deferred 2 (clobber-demo, fixture flakiness) |
| 5 | reviewer-comment-analyzer | Yes | findings | 2 | confirmed 2 (lying docstrings) |
| 6 | reviewer-type-design | Yes | findings | 3 | folded 1 (dead getattr), confirmed 2 LOW (m.side, _tc.arguments convention) |
| 7 | reviewer-security | Yes | clean | 0 | N/A (confirms assembler validation is a real allowlist gate) |
| 8 | reviewer-simplifier | Yes | findings | 1 | confirmed (dead getattr) |
| 9 | reviewer-rule-checker | Yes | findings | 3 | confirmed 1 (AC4 source-text test), confirmed 2 LOW (test annotations) |

**All received:** Yes (9 returned, 7 with findings)
**Total findings:** 5 confirmed (2 must-fix, 3 should-fix) + 4 LOW cleanups, 2 dismissed, 3 deferred.

## Reviewer Assessment (R1 re-review)

**Verdict: CHANGES REQUESTED** (round-trip #2 of 3). The R0 functional blockers are **RESOLVED and proven** — preflight GREEN, security clean, test-analyzer confirms C1/C2/C3 gaps closed, edge-hunter found NO functional/state bug. What remains is a quality cluster I will not approve over: two lying docstrings about the core mechanism and a CLAUDE.md-banned source-text test, plus small correctness/test items. All fixes are trivial-to-small.

### Confirmed — must-fix (blocking)

**R1 (HIGH) [DOC] Two lying docstrings about the load-bearing mechanism.** `sidequest/agents/orchestrator.py` (TurnContext.pack comment) and `sidequest/server/session_helpers.py` (genre_pack= kwarg comment) BOTH say begin_confrontation "resolves the Confrontation Def and instantiates the encounter during tool dispatch." The rework made that FALSE — begin_confrontation is a validate-and-signal tool; narration_apply creates the encounter on the canonical snapshot. These were written in commit 1 (the abandoned approach) and not updated. They directly contradict every other comment in the diff. Fix both to the signal-then-route wording.

**R2 (HIGH) [SIMPLE][TYPE][EDGE][SILENT] Dead getattr fallback.** `begin_confrontation.py` offered-list: `getattr(d, "confrontation_type", None) or getattr(d, "type", "")`. `confrontation_type` is a required field (its alias is `type`), so the primary always succeeds and the fallback is unreachable dead code (NOT broken output — the `or` short-circuits; edge-hunter's `['','']` claim is incorrect). Replace with `sorted(d.confrontation_type for d in defs)`. Flagged by 4 specialists.

### Confirmed — should-fix (bundle in same pass)

**R3 (MED) [EDGE][SILENT] Assembler does not honor the tool's active-encounter rejection.** When an encounter is already active and the narrator mis-calls begin_confrontation, the tool returns ERROR_RECOVERABLE (`signalled=False`), but `_assemble_turn_result_sdk` still finds the ledger call, validates the type (valid), and sets `result.confrontation`. narration_apply's consumer correctly drops it (no double-create) — so NO state bug — but the misfire is masked from the AC5 watcher (`not result.confrontation` is False) and from per-turn telemetry. Mirror the tool's guard: in the assembler, skip routing when `context.encounter` is active+unresolved. Confirmed independently by edge-hunter + silent-failure-hunter.

**R4 (MED) [TEST] Tautological negative test.** `test_sdk_unknown_begin_confrontation_type_is_not_routed` asserts `result.confrontation is None` — the dataclass default — so it would pass even if the assembler routing code were absent. Add an assertion that the begin_confrontation call DID appear in `result.tool_calls` (proving the assembler ran and filtered), so the test distinguishes "filtered correctly" from "code never reached."

**R5 (MED) [RULE][TEST] AC4 test is a banned source-text wiring test.** `test_sdk_prompt_does_not_route_starting_through_advance_confrontation` does `output_only_sdk.md.read_text()` and asserts a phrase is absent — exactly the pattern CLAUDE.md sidequest-server's "No Source-Text Wiring Tests" forbids (passes on benign reformatting; tests shape not behavior). Flagged at R0 (deferred to TEA) and again at R1 by rule-checker. AC4's behavior is already covered by AC3 (triggers live on begin_confrontation) + the assembler routing only begin_confrontation calls. Replace the source-text read with a behavioral assertion or remove it as redundant.

### Confirmed — LOW (cleanup, bundle)

- **[TYPE]** `narration_apply.py` `getattr(m, "side", "neutral")` → use `m.side` (concrete field; matches every other side-check in the file). `orchestrator.py` `(_tc.arguments or {}).get(...)` → `_tc.arguments.get(...)` (arguments is non-optional `dict[str, Any]`).
- **[RULE]** Test annotation gaps: 4 `otel_capture` params (`tests/server/test_59_1...py`) → `: InMemorySpanExporter`; `_FakeRegistry.compose_split_by_zone` return type.

### Deferred / Dismissed

- **[EDGE] LOW** watcher fires on a just-resolved-encounter opponent mention — accept: `resolved` must count as "no active encounter" so a new confrontation can start later; the immediate-post-resolution describe-the-fallen-foe case is a narrow, low-cost false positive. Note for the OTEL owner; not gating.
- **[TEST] LOW** clobber-demonstration companion test — optional nice-to-have; the correct-path round-trip test is the meaningful regression anchor.
- **[SIMPLE] DISMISSED** "assembler re-validation is redundant" (efficiency, R0 verify) — false positive; security R1 confirms it is a real allowlist gate; the ledger holds the call regardless of the tool's error result.
- **[EDGE] DISMISSED** "offered list renders ['','']" — incorrect; `or` short-circuits on the always-present primary. Folded into R2 as dead-code only.

### Rule Compliance (lang-review/python.md + CLAUDE.md)

rule-checker ran all 14 checks + 6 CLAUDE.md rules over the reworked files. PASS on #1/#2/#4-#12/#14, No-Silent-Fallbacks, No-Stubbing, Verify-Wiring, Every-Suite-Wiring-Test, OTEL-on-decisions. Violations: #3 (5 test annotation gaps → LOW cleanup) and "No Source-Text Wiring Tests" (AC4 → R5). Test quality #6: clean except the R4 tautological negative.

### Dispatch-tag coverage

[EDGE] R3 + resolved-edge · [SILENT] R3 · [TEST] R4/R5 + LOW annotations · [DOC] R1 · [TYPE] R2 + LOW conventions · [SEC] clean · [SIMPLE] R2 + dismissed-redundant · [RULE] R5 + #3 annotations.

### Reviewer (deviation audit)

All Design Deviation entries (Dev incl. the REWORK entry, TEA) re-audited: **ACCEPTED.** The REWORK deviation (route via result.confrontation → narration_apply) is the correct response to R0/C1 and is sound. No FLAGGED entries.

**Decision:** Hand back to Dev (green rework). R1 + R2 are blocking (lying docs + dead code); R3/R4/R5 + LOWs bundle in the same small pass. No functional changes required — the engagement fix is correct.
## Dev Assessment (rework R2 — post-re-review)

**Rework Complete:** Yes. All R1 re-review findings addressed; no functional changes (the engagement fix was confirmed correct).

- **R1 (lying docstrings):** corrected the TurnContext.pack comment (orchestrator.py) and the genre_pack= comment (session_helpers.py) — both now say begin_confrontation VALIDATES + signals; narration_apply creates the encounter on the canonical snapshot.
- **R2 (dead getattr):** `offered = sorted(d.confrontation_type for d in defs)` — dropped the unreachable `or getattr(d, "type", "")` fallback.
- **R3 (assembler honor-rejection):** `_assemble_turn_result_sdk` now skips routing when `context.encounter` is active+unresolved (mirrors the tool's guard), so a misfired begin_confrontation during an active encounter no longer sets result.confrontation. Also `_tc.arguments.get(...)` direct (LOW).
- **R4 (tautological test):** `test_sdk_unknown_begin_confrontation_type_is_not_routed` now also asserts the begin_confrontation call appears in `result.tool_calls` (proves the assembler ran and filtered, not absent).
- **R5 (source-text test):** removed the `output_only_sdk.md` `read_text` phrase-absence test; replaced with `test_advance_confrontation_call_does_not_set_result_confrontation` (behavioral — an advance_confrontation call does NOT set result.confrontation). Removed the now-unused `Path` import.
- **LOW:** `m.side` direct access (narration_apply); 4 `otel_capture: InMemorySpanExporter` param annotations; `_FakeRegistry.compose_split_by_zone` return type.

**Tests:** Full suite 7169 passed / 0 failed. Lint clean, formatted.
**Handoff:** To Architect (spec-check), then TEA verify, then Reviewer re-review.
## Architect Assessment (spec-check — R2 cleanup re-run)

**Spec Alignment:** Aligned. **Mismatches Found:** None.

The R2 changes are doc-accuracy + test-quality + cleanup, with one correctness tightening (R3: the assembler now honors begin_confrontation's active-encounter rejection — it skips routing result.confrontation when an encounter is active, mirroring the tool's own guard). None alter the engagement contract validated at the R1 spec-check: begin_confrontation signals → `_assemble_turn_result_sdk` routes the type → narration_apply creates the encounter on the canonical snapshot. The lying docstrings that contradicted that contract are now corrected. AC1-AC6 remain aligned; AC4 is now covered behaviorally (advance_confrontation does not set result.confrontation) instead of by a banned source-text read.

**Decision:** Proceed to TEA verify. No hand-back.
## TEA Assessment (verify — R2 cleanup re-run)

**GREEN confirmed:** full suite 7169 passed / 0 failed (Dev R2). New/strengthened tests (behavioral AC4, ledger assertion on the unknown-type negative, opponent-gated AC5, reprompt double-fire guard) all pass.

### Simplify Report (R2)

| Teammate | Status |
|----------|--------|
| simplify-reuse | clean — no new duplication; the assembler active-encounter guard intentionally mirrors the tool's (cross-seam contract, not extractable) |
| simplify-quality | clean — docstrings now accurate (signal/validator pattern), OTEL on every decision, error handling sound |
| simplify-efficiency | clean — assembler guard + type-validation are load-bearing safety, not redundant |

**Applied:** 0. **Overall:** simplify: clean.
## Subagent Results (R2 re-review — round 3)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (GREEN 7169/0/400, ruff clean) | N/A |
| 2 | reviewer-edge-hunter | Yes | findings | 4 | deferred 1 (double-call is_error), dismissed 3 (getattr-Any correct, m.side defaults neutral, pack.rules diag LOW) |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 2 | deferred 2 (assembler-skip OTEL — tool already emits signalled=False) |
| 4 | reviewer-test-analyzer | Yes | findings | 1 | **confirmed 1 (FIX-2: AC4 test vacuous)** |
| 5 | reviewer-comment-analyzer | Yes | findings | 2 | **confirmed (FIX-1: residual lying comment)** |
| 6 | reviewer-type-design | Yes | findings | 2 | deferred 2 (3-tuple NamedTuple pre-existing; stringly-typed pre-existing) |
| 7 | reviewer-security | Yes | clean | 0 | N/A |
| 8 | reviewer-simplifier | Yes | findings | 2 | deferred 2 (test-harness + _negotiation_pack rule-of-three — test-infra DRY) |
| 9 | reviewer-rule-checker | Yes | clean | 0 | N/A — confirms ALL R1 violations RESOLVED (annotations, source-text test gone) |

**All received:** Yes (9 returned, 6 with findings)
**Total findings:** 2 confirmed (both trivial, doc/test-only), 0 dismissed-incorrectly, 7 deferred/dismissed with rationale.

## Reviewer Assessment (R2 re-review — round 3)

**Verdict: CHANGES REQUESTED** (final rework attempt, 3 of 3) — for TWO trivial one-line fixes only. The engagement fix is **correct, proven, and unchanged**; preflight GREEN, security clean, rule-checker clean, all prior R1 violations RESOLVED. I am NOT approving over a third instance of the exact lying-docstring class I rejected in R0/R1 — consistency requires it be fixed. Both items are doc/test-only with zero functional risk.

### Confirmed — must-fix (the ONLY two changes for this pass)

**FIX-1 (HIGH) [DOC] Residual lying comment.** `sidequest/agents/orchestrator.py:3343` — the comment at the `genre_pack=context.pack` ToolContext-construction site still reads "the begin_confrontation tool resolves the Confrontation Def off this pack and instantiates the encounter during dispatch." R2 fixed the TurnContext.pack field comment and session_helpers, but missed this third instance. It contradicts the now-correct module docstring, _SDK_TOOL_OWNED_FIELDS note, and assembler block. Rewrite to: begin_confrontation VALIDATES the type against this pack and signals via result.confrontation; narration_apply creates the encounter on the canonical snapshot.

**FIX-2 (HIGH) [TEST] AC4 behavioral test is vacuous.** `tests/agents/test_59_1_confrontation_engagement.py::test_advance_confrontation_call_does_not_set_result_confrontation` asserts `result.confrontation is None` — the dataclass default — with no proof the assembler processed the advance_confrontation call. Asymmetric with the R4 fix. Add (before the None assertion): `assert any(tc["name"] == "advance_confrontation" for tc in result.tool_calls)` — same template as the R4 test. (The behavior itself is correct and also covered by the begin_confrontation positive test; this only strengthens the negative.)

### Deferred / Dismissed (do NOT change this pass — accepted as-is)

- **[EDGE] MED double-call is_error filtering** — if the narrator calls begin_confrontation twice (first rejected, second valid), the assembler routes the first. Requires plumbing ToolResultBlock.is_error into the ledger (architectural); the active-encounter guard covers the dominant rejection case and "first valid wins" is acceptable. DEFER (note for a future SDK-ledger enrichment).
- **[TYPE] MED 3-tuple → NamedTuple** for `available_confrontations` — pre-existing field/shape, not introduced by 59-1. DEFER.
- **[SIMPLE] MED test-harness + `_negotiation_pack` rule-of-three** — the fake-SDK stubs are a pre-existing repo-wide test pattern (now 3 files); legit DRY but test-infra only. DEFER to a test-helpers consolidation chore.
- **[SILENT] assembler-skip lacks its own OTEL** — the begin_confrontation tool already emits `signalled=False` + a recoverable error; the assembler skip is defense-in-depth. DEFER.
- **[EDGE] DISMISSED** `getattr(context.encounter, "resolved", False)` — correct: `context.encounter` is `Any` (documented), getattr-with-default is the right guard (type-design concurred). `m.side` None-case — moot: `NpcMention.side` defaults `"neutral"`, never None. `pack.rules=None` diagnostic — LOW, defer.
- **[TYPE] stringly-typed `confrontation_type`** — pre-existing tool-arg pattern, validated at two runtime gates. ACCEPT.

### Dispatch-tag coverage

[EDGE] double-call (deferred) + dismissed edges · [SILENT] assembler-skip (deferred) · [TEST] FIX-2 + deferred harness DRY · [DOC] FIX-1 · [TYPE] deferred NamedTuple/stringly · [SEC] clean · [SIMPLE] deferred rule-of-three · [RULE] clean (R1 violations resolved).

### Reviewer (deviation audit)

All Design Deviation entries re-audited: **ACCEPTED** (no change since R1 audit). No FLAGGED entries.

**Decision:** Hand back to Dev (green rework) — FINAL pass. Change ONLY FIX-1 (one comment) and FIX-2 (one test assertion). Make no other code changes, so the R3 re-review delta is two lines and converges clean. Everything else is accepted/deferred above.
## Dev Assessment (rework R3 — final cleanup)

**Rework Complete:** Yes. Made ONLY the two fixes the Reviewer requested; no other changes.
- **FIX-1:** corrected the residual lying comment at orchestrator.py:3343 (genre_pack=context.pack site) — now says begin_confrontation validates+signals; narration_apply creates the encounter on the canonical snapshot.
- **FIX-2:** added the ledger-presence guard to test_advance_confrontation_call_does_not_set_result_confrontation (asserts the advance_confrontation call appears in result.tool_calls before the None assertion) — non-vacuous, mirrors the R4 template.

All deferred/dismissed items left untouched per the Reviewer's instruction. Full suite 7169 passed / 0 failed; lint clean. **Handoff:** Architect spec-check → TEA verify → Reviewer (final re-review).
## Architect Assessment (spec-check — R3 final cleanup)

**Spec Alignment:** Aligned. **Mismatches Found:** None. The R3 delta is one comment correction + one test assertion — no code logic or contract change. The engagement contract (begin_confrontation signals → assembler routes → narration_apply creates on canonical) is unchanged and now described accurately at every comment site. Proceed to TEA verify.
## TEA Assessment (verify — R3 final cleanup)

**GREEN confirmed:** full suite 7169 passed / 0 failed (Dev R3). The R3 delta is one comment correction (orchestrator.py) + one test ledger-assertion (AC4 behavioral test) — no production logic changed. Per the verify workflow, simplify fan-out is skipped (no substantive code change to analyze). **Overall:** simplify: skipped (comment + test-assert delta).
## Subagent Results (R3 final re-review)

| # | Specialist | Received | Status | Findings |
|---|-----------|----------|--------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (GREEN 7169/0/400, ruff clean) |
| 2 | reviewer-edge-hunter | Yes | clean | 0 (2-line delta introduces no edge) |
| 3 | reviewer-silent-failure-hunter | Yes | clean | 0 |
| 4 | reviewer-test-analyzer | Yes | clean | 0 — confirms FIX-2 (AC4 test) now non-vacuous |
| 5 | reviewer-comment-analyzer | Yes | clean | 0 — confirms FIX-1 (no comment claims the tool instantiates) |
| 6 | reviewer-type-design | Yes | clean | 0 |
| 7 | reviewer-security | Yes | clean | 0 |
| 8 | reviewer-simplifier | Yes | clean | 0 |
| 9 | reviewer-rule-checker | Yes | clean | 0 — all prior violations resolved, 20 rule-groups pass |

**All received:** Yes (9 returned, 0 with findings)
**Total findings:** 0 confirmed, 0 deferred, 0 dismissed.

## Reviewer Assessment (R3 final re-review)

**Verdict: APPROVED.** Unanimous clean pass across all nine specialists. FIX-1 (residual lying comment, orchestrator.py:3343) and FIX-2 (vacuous AC4 test ledger guard) are both confirmed resolved by their respective lanes. The engagement fix is correct and proven: begin_confrontation validates+signals → `_assemble_turn_result_sdk` routes `result.confrontation` from the tool-call ledger → narration_apply creates the StructuredEncounter on the canonical snapshot (clobber-free, one mechanism on both backends), with a precise opponent-gated `confrontation.unengaged_turn` lie-detector. Suite 7169 passed / 0 failed; ruff clean; rule-checker clean.

Dispatch-tag coverage: [EDGE] clean · [SILENT] clean · [TEST] clean (FIX-2 verified) · [DOC] clean (FIX-1 verified) · [TYPE] clean · [SEC] clean · [SIMPLE] clean · [RULE] clean.

### Reviewer (deviation audit)

All Design Deviation entries (Dev incl. the REWORK entry, TEA) — **ACCEPTED**. The begin_confrontation-over-apply_world_patch choice and the route-via-result.confrontation rework are both sound and proven. No FLAGGED entries.

### Delivery Findings (Reviewer)

- The broader SDK-tool store-clobber (apply_damage / advance_* share the load/mutate/save pattern that room.save can clobber) — endorsed as a real out-of-scope concern for a dedicated SDK-backend persistence spike (already in Dev Delivery Findings). Non-blocking for 59-1.

**Decision:** APPROVED. Hand to SM (Hawkeye) for finish — PR creation + merge. Reviewer does not merge.