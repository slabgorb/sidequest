---
story_id: "85-3"
jira_key: ""
epic: "85"
workflow: "tdd"
---
# Story 85-3: Confrontation mode — spatial promotion to a dockview panel (opponent portrait + stakes + Guitar-Solo party action)

## Story Details
- **ID:** 85-3
- **Jira Key:** (none — Jira not enabled)
- **Workflow:** tdd
- **Stack Parent:** none
- **Epic:** 85 — Post-Playtest UX Polish — Confrontation Panel & Location Surface

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-04T20:42:26Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-04T00:00:00Z | 2026-06-04T19:37:21Z | 19h 37m |
| red | 2026-06-04T19:37:21Z | 2026-06-04T20:08:07Z | 30m 46s |
| green | 2026-06-04T20:08:07Z | 2026-06-04T20:28:42Z | 20m 35s |
| review | 2026-06-04T20:28:42Z | 2026-06-04T20:42:26Z | 13m 44s |
| finish | 2026-06-04T20:42:26Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (blocking): The CONFRONTATION payload carries NEITHER `actors[].portrait_url` NOR `stakes` — both ACs (#3 opponent portrait, #4 stakes banner) depend on data the server does not currently send. Affects `sidequest-server/sidequest/game/encounter.py` (EncounterActor has no `portrait_url`, lines 105-126), `sidequest-server/sidequest/server/dispatch/confrontation.py` (build_confrontation_payload serializes actors via `model_dump`, line 222 — cannot emit a field that doesn't exist), and `sidequest-server/sidequest/protocol/messages.py` (ConfrontationPayload has no `stakes`, lines 773-834). The UI TS type already declares `portrait_url?` and `ActorChip` renders it (`sidequest-ui/src/components/ConfrontationOverlay.tsx:10-14,235`) but it is dead — the server never populates it. `active_stakes` exists as a session field (`session.py:867`) but is projected only via the separate QUESTS message (`models.py:803`), NOT CONFRONTATION. *Found by TEA during test design.*
- **Question** (blocking): Two architecture decisions gate the server contract and therefore gate what RED tests must assert — these belong to Architect (The White Queen) per the design doc (confrontation-space-usage.md:174-175) and SM setup flag. (1) **Stakes source:** does the UI read existing `active_stakes` off the QUESTS message it already receives (ui-only, couples the panel to quests state), OR does the server add `stakes` to ConfrontationPayload and thread `snapshot.active_stakes` through all 4 build_confrontation_payload call sites (self-contained payload, wider blast radius)? (2) **Portrait resolution:** add `portrait_url: str | None` to server EncounterActor and resolve via the existing `_resolve_npc_portrait_url` helper (emitters.py:761) at serialization, OR resolve portraits client-side from an NPC/character registry the UI already holds? Affects the server protocol contract; RED cannot author non-throwaway contract tests until chosen. *Found by TEA during test design.* **[RESOLVED — see Architect Decision below: stakes=server field; portrait=injected resolver, opponent-only.]**
- **Improvement** (non-blocking): The confrontation dockview panel is a REVIVAL, not greenfield — per operator (Keith, 2026-06-04), this surface WAS a dockview panel, then was moved to the bottom strip when "chandelier swinging" (free environmental action) was wired in, to signal that off-beat creative actions were possible. Vestigial panel-era wiring remains: `sidequest-ui/src/components/GameBoard/widgetRegistry.ts:13` ("Confrontation is intentionally not a widget id … D2 mock 2026-05-13") and `GameBoard.tsx:727` (dynamic add/remove effect comment still says it "only fires for confrontation"). Dev should REVIVE/clean this existing seam — re-add `confrontation` to `WidgetId`/`WIDGET_REGISTRY` as a data-gated, auto-focused widget and fix the two stale comments — NOT build a parallel mounting path beside the fossil. *Found by TEA during test design.*
- **Question** (non-blocking → guarded by test): The bottom-strip move existed to preserve the "you can just DO things" affordance (The Zork Problem — never imply a closed verb set; chandelier swinging as a typed creative action, not a beat tile). The SPLIT decision protects this (narration + InputBar stay reachable). RED includes an explicit test that confrontation mode is SPLIT not takeover: the narration column + InputBar remain present/reachable while the confrontation panel is focused, so free-text creative actions survive the promotion. *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): The live dockview auto-focus (`panel.api.setActive()` on add) and release-on-resolution are verified by code review against the dockview API, NOT by an automated test — jsdom can't drive DockviewReact panel activation reliably. The registry-promotion test guards the structural contract (confrontation is data-gated/closable, narrative stays always-present = SPLIT). Recommend a Playwright/manual playtest pass confirms the panel actually focuses on encounter start and the canvas returns to narration on resolution. Affects `sidequest-ui/src/components/GameBoard/GameBoard.tsx` (the add/remove+setActive effect). *Found by Dev during implementation.*
- **Improvement** (non-blocking): The "meanwhile at the table" strip is fed from `peerActionsByRound.get(round)`, filtered to non-local players (`player_id !== currentPlayerId`) and non-asides (`!e.aside`), mapped to `{actor: character_name, verb: action}`. No role is surfaced (ActionRevealEntry has no role field) — `MeanwhileAction.role` stays optional/unused for now. If a future story wants role tags ("Spark (gunner)"), the role must be added to the peer-action wire shape. Affects `sidequest-ui/src/components/GameBoard/GameBoard.tsx` (renderWidgetContent confrontation case). *Found by Dev during implementation.*
- **Improvement** (non-blocking): Portrait *manifest-backed* wiring (the production lambda → `_resolve_npc_portrait_url` against a real world manifest, proven via the existing `scrapbook_npc_portrait_resolved_span`) is exercised at the builder/seam level but not with a live manifest fixture — the TEA-deferred verify-phase assertion. The 4 call sites all build the resolver via the shared `make_confrontation_portrait_resolver`, so a single manifest-backed test on any one path would cover the lot. Affects `sidequest-server/sidequest/server/dispatch/confrontation.py`. *Found by Dev during implementation.*

### Reviewer (code review)
- **Gap** (non-blocking): The "meanwhile at the table" filter `e.player_id !== currentPlayerId && !e.aside` (`sidequest-ui/src/components/GameBoard/GameBoard.tsx` renderWidgetContent confrontation case) is UNTESTED. `!e.aside` is an ADR-107 perception boundary — keeps OOC out-of-band asides out of the in-fiction concurrent-verb strip. The code is correct, but a future refactor could silently invert it. Recommend a GameBoard-level test that feeds `peerActionsByRound` a mix of own-player / aside / peer entries and asserts only peer non-aside verbs reach `meanwhileActions`. *Found by Reviewer during code review.*
- **Gap** (non-blocking): Three of the four `build_confrontation_payload` call sites (dice.py, websocket_session_handler.py, yield_action.py) carry no fixture-driven wiring test; only `make_confrontation_frame_supplier` is wiring-tested. Per "every test suite needs a wiring test," each delivered-frame call site should assert `stakes` reaches the payload. Affects `sidequest-server/sidequest/server/dispatch/dice.py`, `sidequest/server/websocket_session_handler.py`, `sidequest/handlers/yield_action.py`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `MeanwhileAction.role` is a dead render branch (never populated — ActionRevealEntry has no role; the Duchess mock wants "Spark (gunner)"). Either wire scene-role from a real source in a follow-up or remove the field. Affects `sidequest-ui/src/components/ConfrontationOverlay.tsx` (MeanwhileAction/MeanwhileStrip) + `GameBoard.tsx` (mapping). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): The GameBoard auto-focus (`panel.api.setActive()`) + `availableWidgets` data-gate + the OTEL span `len==1` isolation + the THEM-degrade assertion strength are all noted by test-analyzer as worth a verify-phase test pass. Affects `sidequest-ui/src/components/GameBoard/GameBoard.tsx`, `sidequest-server/tests/telemetry/test_confrontation_stakes_attached_span.py`. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

No design deviations yet.

### Dev (implementation)
- **Enriched two test fixtures to match the real wire shape (not a weakening)**
  - Spec source: TEA RED tests (test_wwn_cast_spell_wiring.py `_FakeGenrePack`; ConfrontationOverlay.confrontationmode.test.tsx `BASE.actors`)
  - Spec text: fixtures omitted `genre_pack.worlds` and `actor.side` (fields the real `GenrePack` / serialized `EncounterActor` always carry)
  - Implementation: added `worlds = {}` to both `_FakeGenrePack` stubs (the new portrait resolver reads `pack.worlds`) and `side: "player"|"opponent"` to the UI actor fixtures (the THEM panel keys off `side === "opponent"`, which is on the wire)
  - Rationale: making incomplete stubs realistic, not relaxing assertions — every original assertion (stakes threading, cast_spell filtering, THEM panel content) is unchanged and still enforced
  - Severity: minor
  - Forward impact: none — aligns fixtures with the production payload

### TEA (test design)
- No deviations from spec. Tests were authored against the Architect-approved protocol contract (The White Queen, 2026-06-04 — recorded above): injected `portrait_resolver` (sibling to `core_resolver`) + optional `active_stakes` kwarg, `portrait_url` on the serialized actor dict (NOT the EncounterActor model), `stakes` always-present on the payload. The Architect explicitly approved this shape over the original in-builder direct-call spec, so the tests match the current recorded contract — no deviation.

### Reviewer (audit)
- **Dev: "Enriched two test fixtures to match the real wire shape"** → ✓ ACCEPTED by Reviewer: sound — `_FakeGenrePack.worlds` and UI `actor.side` are fields the real `GenrePack`/serialized `EncounterActor` always carry; the stubs were incomplete, not the assertions relaxed. Every original assertion still holds (verified: cast_spell filtering, stakes threading, THEM-panel content all intact; rule-checker confirmed the `worlds = {}` is an instance attr, not a mutable class default).
- **TEA: "No deviations from spec"** → ✓ ACCEPTED by Reviewer: confirmed — the injected-resolver / stakes-always-present shape is the recorded Architect-approved contract.
- **UNDOCUMENTED (Reviewer audit):** `MeanwhileAction.role` is rendered conditionally in `MeanwhileStrip` but never populated by the GameBoard mapping (ActionRevealEntry has no role). Spec/design (Duchess mock) shows role tags ("Spark (gunner)"); code declares the affordance but leaves it unwired. Severity: LOW. Not logged as a Design Deviation by Dev (it WAS logged as a Delivery Finding). Accepted as a documented forward affordance, not flagged for reversal — but recorded here so it isn't invisible. Future story should wire scene-role when a data source exists, or remove the field.

## Sm Assessment

**Readiness:** Story 85-3 is ready for RED. Merge gate clear, both dependencies satisfied (85-1 Tier A and 85-2 location source-of-truth are both `done`), and the design doc (docs/design/confrontation-space-usage.md) is present on disk.

**Gating decision resolved:** The story's blocking "SPLIT vs TAKE OVER" layout question was surfaced to and answered by the operator on 2026-06-04 — **SPLIT** (narration left, confrontation right), matching The Duchess's Tier B recommendation. This is locked in AC #1; no code may assume full-screen takeover.

**Scope flag for TEA:** One open question is deliberately NOT resolved at setup — whether the CONFRONTATION payload already carries `actors[].portrait` and `stakes`. RED phase must verify this first. If those fields are absent, the server half (sidequest-server) enters scope and TEA should record a blocking Delivery Finding for Architect review before green. If present, this is UI-only (sidequest-ui). The branch currently lives in sidequest-ui only; a server branch is created lazily if the protocol gap is confirmed.

**Routing:** Phased TDD → handing off to TEA (The Caterpillar) for RED. No implementation planning done here per SM role discipline.

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (failing — ready for Dev)

**Test Files:**
- `sidequest-server/tests/server/dispatch/test_confrontation_stakes_portrait_payload.py` — builder contract (stakes always-present + normalized; portrait opponent-only via injected resolver; None on miss; player/neutral never resolved) + protocol round-trip (`ConfrontationPayload(**dict)`, extra="forbid") + call-site WIRING via the real `make_confrontation_frame_supplier` (threads `snapshot.active_stakes`). 13 tests.
- `sidequest-server/tests/telemetry/test_confrontation_stakes_attached_span.py` — OTEL `confrontation.stakes_attached` span fires on every build with `has_stakes`/`stakes_len`/`genre_slug`/`confrontation_type` (lie-detector for the stakes wiring). 2 tests.
- `sidequest-ui/src/components/__tests__/ConfrontationOverlay.confrontationmode.test.tsx` — the 3 new panel surfaces: stakes banner (renders/collapses), "meanwhile at the table" strip (Guitar Solo; renders peers / collapses solo), THEM panel (opponent portrait+name+last beat; degrades cleanly). 9 tests (5 positive RED, 4 collapse-guards green).
- `sidequest-ui/src/components/GameBoard/__tests__/confrontationWidgetPromotion.test.ts` — dockview promotion: `confrontation` is a data-gated, closable widget; SPLIT preserved (narrative stays always-present, never replaced); no hotkey collision. 5 tests (3 positive RED, 2 guards green).

**Tests Written:** 29 across 4 files, covering all 6 ACs (AC1 design decision = recorded above, no code test; AC6 protocol check = RESOLVED, server in scope).
**RED verified:** 15 server + 8 UI positive-case tests fail for honest feature-absence reasons (verified by testing-runner, RUN_ID 85-3-tea-red — missing `stakes` key, unknown `active_stakes`/`portrait_resolver` kwargs, unfired span, missing testids, missing registry entry). Guard tests (collapse-when-absent, SPLIT, hotkey) pass and MUST stay green.

### Rule Coverage

| Rule (lang-review) | Test(s) | Status |
|------|---------|--------|
| python #6 test quality (no vacuous asserts) | all server tests assert concrete values (`== stakes`, `is None`, `== url`, `"stakes" in payload`, span attrs) | self-checked clean |
| No-Silent-Fallbacks (SOUL/CLAUDE) | `test_opponent_portrait_url_none_on_resolver_miss`, `test_empty_active_stakes_normalizes_to_none` | failing |
| No-Source-Text-Wiring (server CLAUDE.md) | wiring proven via real `make_confrontation_frame_supplier` + OTEL span, NOT grep | failing |
| Every-suite-needs-a-wiring-test | `test_frame_supplier_threads_active_stakes_onto_the_wire` (server call-site); registry promotion (UI gate) | failing |
| ts test quality | UI tests assert text content / element presence-absence, no `expect(true)` | self-checked clean |

**Self-check:** 0 vacuous tests found in authored code.

**Gaps deferred to Dev/verify (documented, not silently dropped):**
- **GameBoard auto-focus integration** (AC2 "auto-focuses … releases on resolution"): the registry test pins the structural promotion contract, but the live `panel.api.setActive()` on add + removal on resolve is GameBoard+DockviewReact behavior that's heavy/flaky to unit-test in jsdom. Dev MUST wire the add/remove+focus effect (GameBoard.tsx:734-769 + the focus pass) and self-verify; a GameBoard-level integration test (render with `confrontationData` set → confrontation panel active AND narrative still mounted) is recommended in GREEN/verify. Specified in Development Notes.
- **Portrait call-site manifest wiring:** the builder seam fully covers the portrait CONTRACT (injected resolver); the production lambda → `_resolve_npc_portrait_url(pack, world_slug, …)` with `_world_portrait_slugs` precomputed once should get a manifest-backed wiring assertion (existing `scrapbook_npc_portrait_resolved_span` proves the real resolver ran) during GREEN/verify.

**Handoff:** To Dev (The White Rabbit) for GREEN.

## Dev Assessment

**Implementation Complete:** Yes
**Tests:** GREEN — server 15/15 new + 62/62 regression + lint clean; UI 14/14 new + 106/106 regression + `tsc --noEmit` clean (testing-runner, RUN_ID 85-3-dev-green).
**Branches (pushed):** sidequest-server `feat/85-3-confrontation-mode-dockview-panel`; sidequest-ui `feat/85-3-confrontation-mode-dockview-panel`.

**Files Changed — server (sidequest-server):**
- `sidequest/protocol/messages.py` — `ConfrontationPayload.stakes: str | None = None` (declared; extra="forbid" safe).
- `sidequest/server/dispatch/confrontation.py` — `build_confrontation_payload` gains `active_stakes` + `portrait_resolver` params; stakes always-present + normalized; opponent-only portrait injection; emits `confrontation.stakes_attached` span; new shared `make_confrontation_portrait_resolver` (precomputes manifest slugs once); supplier threads both.
- `sidequest/telemetry/spans/encounter.py` — `SPAN_CONFRONTATION_STAKES_ATTACHED` + route + `confrontation_stakes_attached_span` helper.
- `sidequest/handlers/yield_action.py`, `sidequest/server/dispatch/dice.py`, `sidequest/server/websocket_session_handler.py` — thread `active_stakes` + `portrait_resolver` into the 3 other build sites (no half-wiring).

**Files Changed — ui (sidequest-ui):**
- `src/components/ConfrontationOverlay.tsx` — `EncounterActor.side`, `ConfrontationData.stakes`, `MeanwhileAction` + `meanwhileActions` prop; StakesBanner, ThemPanel, MeanwhileStrip surfaces.
- `src/components/GameBoard/widgetRegistry.ts` — revived `confrontation` WidgetId/registry entry (dataGated, closable); removed stale comment.
- `src/components/GameBoard/GameBoard.tsx` — `confrontation` renderWidgetContent case (derives meanwhile actions from `peerActionsByRound`); availableWidgets data-gate; auto-focus on add + release on remove; dropped bottom-strip mount; moved `inputBarRef`/`handleBeatTileSelect` above renderWidgetContent (chandelier affordance preserved); refreshed stale comment.

**AC status:** AC1 SPLIT (operator) ✓ recorded + structurally enforced. AC2 dockview auto-focus/release ✓ wired (the TEA-deferred GameBoard integration is now IMPLEMENTED + self-verified GREEN; jsdom can't drive live dockview focus, so the registry test guards the contract and the setActive/remove behavior was verified by code review against the dockview API). AC3 THEM portrait+name+last beat + degrade ✓. AC4 stakes banner ✓. AC5 meanwhile strip + solo collapse ✓ (fed from peerActionsByRound, asides excluded). AC6 protocol ✓ (server in scope, delivered).

**Self-review:** wired end-to-end (server 4 sites + UI panel mount + data derivation); No-Silent-Fallbacks honored (portrait None on miss, stakes None-not-empty); OTEL span added per discipline; no debug code; both branches pushed.

**Handoff:** To verify phase (TEA simplify + quality-pass).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (49 tests green; ruff/tsc/eslint clean; 2 TODOs pre-existing) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 7 | confirmed 1 + FIXED inline (requiredIds gap); 5 deferred non-blocking (Medium coverage gaps); 1 dismissed |
| 5 | reviewer-comment-analyzer | Yes | findings | 4 | confirmed 4, ALL FIXED inline (3 stale comments + docstring); 1 sub-claim dismissed (see below) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 6 | confirmed 6, all LOW/informational; 1 (role dead-branch) downgraded with rationale; 0 dismissed |

**All received:** Yes (4 enabled returned, 5 disabled pre-filled)
**Total findings:** 5 confirmed+FIXED inline, ~7 confirmed non-blocking (Low/Medium), 1 dismissed (with rationale)

## Rule Compliance

Exhaustive per rule-checker (26 rules, 87 instances) + my own enumeration:

- **No Silent Fallbacks** (SOUL/CLAUDE): COMPLIANT. `_actor_with_portrait` sets `portrait_url=None` on miss — the key is always present with an explicit `None` (loud absence, observable by the UI), never a missing key or substituted placeholder. `stakes` normalizes `""→None` and is always present. Verified `confrontation.py:_actor_with_portrait`, builder dict, `test_opponent_portrait_url_none_on_resolver_miss`.
- **No half-wired features / No Stubbing** (CLAUDE): COMPLIANT for the core feature — all 4 `build_confrontation_payload` call sites (supplier, dice union, websocket union, yield projection) thread `active_stakes`+`portrait_resolver`. ONE LOW exception: `MeanwhileAction.role` render branch never fires (ActionRevealEntry has no role) — see findings; downgraded (documented forward affordance, design-intended, degrades cleanly).
- **OTEL Observability** (CLAUDE): COMPLIANT. `confrontation.stakes_attached` registered in `SPAN_ROUTES` (not flat-only), extract lambda matches the 4 emitted attrs, fires unconditionally on every build. `test_routing_completeness` will enforce routing. Verified `encounter.py:SPAN_CONFRONTATION_STAKES_ATTACHED`.
- **Verify Wiring, Not Just Existence** (CLAUDE): COMPLIANT — every new symbol (`confrontation_stakes_attached_span`, `make_confrontation_portrait_resolver`, `ConfrontationPayload.stakes`, the 3 UI components, the `confrontation` widget) has a production consumer, not just a test.
- **Every Test Suite Needs a Wiring Test** (CLAUDE): PARTIAL — the supplier path has a real fixture-driven wiring test (`test_frame_supplier_threads_active_stakes_onto_the_wire`); the dice/websocket/yield call sites do NOT (Medium coverage finding, non-blocking — behavior verified GREEN, deferral documented). The UI `confrontation` widget is now guarded in `gameboard-wiring.test.tsx` (fixed inline).
- **No Source-Text Wiring Tests** (server CLAUDE): COMPLIANT — server wiring proven via real supplier + OTEL span, no grep.
- **Mutable defaults / exception swallowing / async / deserialization / type-at-boundaries** (python.md 1-13): COMPLIANT (rule-checker: 0 violations except `genre_pack: Any` lacks an inline rationale comment — LOW, pre-existing pattern).
- **TypeScript null-handling / hook-deps / enum-as-union / JSX** (typescript.md): COMPLIANT — `renderWidgetContent` useCallback deps correctly expanded (all 8 new captures present); `availableWidgets` dep includes `confrontationData`; `peerActionsByRound?.get(round) ?? []` correct nullish handling; `side` is a union not an enum. LOW: `MeanwhileStrip` key includes array index.

## Reviewer Observations

- [VERIFIED] Data flow traced end-to-end: `snapshot.active_stakes → build_confrontation_payload(active_stakes=) → payload["stakes"] → ConfrontationPayload.stakes (declared, extra="forbid"-safe) → wire → ConfrontationData.stakes → StakesBanner`. Opponent: `EncounterActor.side=="opponent" → portrait_resolver → _resolve_npc_portrait_url(manifest_slugs) → actor dict portrait_url → ActorChip in ThemPanel`. Evidence: confrontation.py:217-264, messages.py:842, ConfrontationOverlay.tsx StakesBanner/ThemPanel. Complies with No-Silent-Fallbacks + extra="forbid" round-trip rules.
- [VERIFIED] SPLIT preserved (operator AC1): `narrative` stays `dataGated:false` (always present); `confrontation` is a separate data-gated widget anchored to the right group — can never replace the prose column. Chandelier affordance intact: `handleBeatTileSelect` reads `inputBarRef.consumeDraft()`, InputBar stays mounted in `gameboard-input-region`. Evidence: widgetRegistry.ts, GameBoard.tsx renderWidgetContent confrontation case + inputBar block.
- [DOC] Stale post-migration comments (comment-analyzer, high) — ConfrontationOverlay JSDoc "mounted between workspace and InputBar", GameBoard:77 "D2 mock" removal comment, missing docstring params, root bottom-strip styling. **CONFIRMED + FIXED inline** (operator-directed) — commits `docs(85-3)` in both repos.
- [TEST] gameboard-wiring.test.tsx omitted `confrontation` from requiredIds with a stale exclusion comment (test-analyzer, high) — a real regression gap (widget could silently vanish). **CONFIRMED + FIXED inline** (added `confrontation` + corrected comment).
- [TEST] Coverage gaps (test-analyzer, Medium, non-blocking): (a) dice/websocket/yield call-site wiring tests absent — only the supplier path is wiring-tested; (b) the meanwhile-actions filter `player_id !== currentPlayerId && !e.aside` is untested (note: `!e.aside` keeps OOC asides out of the strip — correct in code, but an untested perception boundary); (c) `panel.api.setActive()` auto-focus + `availableWidgets` data-gate untested (TEA-deferred); (d) `make_confrontation_portrait_resolver` never exercised with a non-empty manifest; (e) OTEL span test reads `spans[-1]` without `len==1`; (f) THEM degrade test asserts absence-of-`true` rather than presence-of-`false`. All CONFIRMED, DEFERRED to a verify/follow-up — behavior is correct and GREEN; these are regression-protection, not bugs.
- [RULE] `MeanwhileAction.role` render branch never fires (rule-checker, LOW) — ActionRevealEntry carries no role; the `({a.role})` branch is dead. CONFIRMED, severity DOWNGRADED with rationale (NOT dismissed): role is design-intended (the Duchess mock shows "Spark (gunner)"), the field is optional and degrades to nothing, Dev documented the wire gap, and "gunner/nav" are scene-roles with no current data source — a documented forward affordance, not a hidden stub. Recommend a follow-up wires scene-role when a source exists.
- [RULE] LOW/informational (rule-checker): `genre_pack: Any` lacks inline rationale comment (pre-existing pattern); RED-scaffolding casts in the two new test files (`as Record<...>`, `as unknown as OverlayProps` — self-documented, redundant post-GREEN); `MeanwhileStrip` key includes array index (actor names unique per session — low practical risk); private-name import of `_resolve_npc_portrait_url`/`_world_portrait_slugs` (justified by "Don't Reinvent"). None blocking.
- [SEC] reviewer-security DISABLED this run. My own check: no tenant model in this codebase (personal project); `stakes`/`verb`/`portrait_url` are server-sourced display strings rendered as text content (not innerHTML), `portrait_url` used as `<img src>` — no injection surface. No secrets. No auth surface touched.
- [TYPE] reviewer-type-design DISABLED this run. My own check: `EncounterActor.side` and `WidgetId` are string unions (preferred over enums); `ConfrontationPayload.stakes` declared (extra="forbid" requires it); no stringly-typed regressions.
- [SIMPLE] reviewer-simplifier DISABLED this run. My own check: `make_confrontation_portrait_resolver` is a clean DRY extraction shared by all 4 sites (precomputes manifest slugs once) — the opposite of duplication. No over-engineering spotted.
- [EDGE] reviewer-edge-hunter DISABLED. My own check: `peerActionsByRound?.get(round) ?? []` handles missing round; empty stakes → None; missing opponent → ThemPanel renders null; missing portrait → ActorChip degrades. Boundaries covered.
- [SILENT] reviewer-silent-failure-hunter DISABLED. My own check: no swallowed errors in the diff; portrait None-on-miss is explicit/loud; no empty catches.

## Devil's Advocate

Argue the code is broken. **Attack 1 — the stakes span floods the GM panel.** `confrontation.stakes_attached` fires on EVERY `build_confrontation_payload`, and the supplier calls the builder once per connected recipient PLUS the union build fires once. A 4-player table emits ~5 stakes spans per confrontation frame, every turn. A malicious or just-large table could make the watcher dashboard noisy — but this mirrors the existing `confrontation_beat_filter` per-recipient firing, the attrs are tiny, and "noise" is not "broken." Not a defect, a known tradeoff. **Attack 2 — the meanwhile strip leaks OOC table-talk.** If `!e.aside` were ever inverted, ADR-107 out-of-band asides would surface as in-fiction concurrent verbs in front of the whole table — a genuine perception-firewall break. I read the filter: it is correct (`&& !e.aside`). BUT it is untested — a future refactor could invert it silently. This is the single finding I'd most want covered; I've flagged it Medium/deferred rather than blocking because the current code is correct and GREEN. **Attack 3 — auto-focus steals focus mid-turn.** `setActive()` fires whenever `confrontation` enters `availableWidgets`. If `confrontationData` flickers null→non-null on reconnect, the panel could yank focus repeatedly. But `availableWidgets` is memoized on `confrontationData` identity and the add only fires when the panel isn't already present (`!dockviewIds.has(id)`), so re-focus only on genuine appearance. Acceptable. **Attack 4 — a confused author sees the dead `role` branch and assumes role works.** Mitigated: Dev + this review documented it; downgraded, not hidden. **Attack 5 — the moved `inputBarRef`/`handleBeatTileSelect` change hook order.** Re-read: they moved UP (before renderWidgetContent), preserving useRef→useCallback ordering; no conditional hooks. tsc + 106 UI regression tests pass. No TDZ. Conclusion: the devil finds noise and untested-but-correct logic, no actual breakage.

## Reviewer Assessment

**Verdict:** APPROVED

**Findings by source:** [DOC] 4 confirmed → all FIXED inline (stale JSDoc/comments + missing docstring params). [TEST] 7 — 1 confirmed+FIXED inline (gameboard-wiring requiredIds gap), 5 deferred non-blocking (Medium coverage gaps: meanwhile-filter, 3 call-site wiring, setActive/availableWidgets, factory-with-manifest, OTEL len, THEM-degrade strength), 1 sub-claim dismissed ("plain Enter not locked" — the `confrontationActive` lock is unchanged, only the mounting-location claim was stale). [RULE] 6 confirmed, all LOW/informational (role dead-branch downgraded with rationale; genre_pack Any; RED-scaffolding casts; index key; private import) — 0 dismissed. [EDGE] / [SILENT] / [TYPE] / [SEC] / [SIMPLE] — subagents DISABLED via settings this run; covered by my own analysis in Reviewer Observations (boundaries, swallowed-errors, type unions, injection surface, DRY all checked clean).

**Rationale:** No Critical or High severity issues. The feature is correct, wired end-to-end across all 4 server call sites + the UI panel mount, GREEN (server 15/15 new + 62/62 regression; UI 14/14 new + 106/106 regression + 30 in the re-verified suites; ruff/tsc/eslint clean). The only high-confidence "wrong" findings were stale post-migration documentation and a missing widget regression-guard — both FIXED inline per operator direction and re-verified. Remaining findings are Medium test-coverage gaps (documented, deferred — regression protection, not bugs) and Low/informational items (a documented forward-affordance field, RED-scaffolding casts, an index key). All rule-matching findings were confirmed (none dismissed); the one half-wired surface (`MeanwhileAction.role`) was severity-downgraded with rationale, not waved away.

**Data flow traced:** snapshot.active_stakes → CONFRONTATION payload → StakesBanner; opponent side → portrait resolver → ThemPanel (safe — server-sourced display strings, text content, no injection).
**Pattern observed:** DRY shared resolver `make_confrontation_portrait_resolver` at confrontation.py:438; data-gated dockview widget revival at GameBoard.tsx renderWidgetContent + availableWidgets.
**Error handling:** portrait None-on-miss (loud), stakes ""→None, missing-opponent/round/portrait all degrade cleanly.

**Strongly recommended for a follow-up (non-blocking):** a test on the meanwhile-actions filter (`player_id !== currentPlayerId && !e.aside`) — it is an ADR-107 perception boundary; and the dice/websocket/yield call-site wiring tests + the GameBoard auto-focus integration test that TEA/Dev deferred.

**Handoff:** To SM (The Mad Hatter) for finish-story.

## Architect Decision (Protocol Contract — The White Queen, 2026-06-04)

Resolves the two blocking Delivery Findings. Story is confirmed **ui + server**.

**Q1 — Stakes source: Option B (server field).** Add `stakes: str | None = None` to `ConfrontationPayload` (`messages.py` ~L834). Populate in `build_confrontation_payload` (`confrontation.py` L218-234) as `"stakes": snapshot.active_stakes or None` (normalize `""`→`None`). QUESTS projection of `active_stakes` stays as-is. Rationale: self-contained channel, avoids the QUESTS-arrival race where the auto-focused panel mounts before QUESTS lands.

**Q2 — Portrait resolution: Option A (server resolver). Q2-B is INVALID** — verified the UI's only name→portrait maps are `CharacterSummary`/`CompanionSummary` from PARTY_STATUS (`sidequest-ui/src/types/party.ts:9`), covering players/companions only; there is NO client-side adversarial-opponent portrait registry. Add `portrait_url: str | None = None` to server `EncounterActor` (`encounter.py:126`). In `build_confrontation_payload` actor serialization (L222), resolve via existing `_resolve_npc_portrait_url` (`emitters.py:761`) **only for `side == "opponent"`** (players/companions get portraits via PARTY_STATUS); `None` on manifest miss (No Silent Fallbacks). Centralize inside the builder — do not duplicate at the 4 call sites; thread `snapshot`/`pack`/`world_slug` as required-args (fail loud, no silent `None` default).

**OTEL:** reuse existing `scrapbook_npc_portrait_resolved_span`/`..._not_found_span` for portraits; add ONE new span `confrontation.stakes_attached` (attrs: `genre_slug`, `confrontation_type`/`category`, `has_stakes` bool, `stakes_len` int) per builder call.

**UI contract:** add `stakes?: string` to `ConfrontationData` (`ConfrontationOverlay.tsx`); `actors[].portrait_url?` already present + `ActorChip` already renders it (dead field becomes live). App.tsx cast unchanged.

Full decision + exact RED assertions captured by The Caterpillar; tests authored against this contract.

## Story Context

**Problem Statement:** Tier B of the confrontation space-usage design (docs/design/confrontation-space-usage.md, The Duchess 2026-06-04). Promote the confrontation from a thin bottom strip into a focused dockview 'confrontation mode' that claims the board canvas while an encounter is active — giving the drama peak the screen it earns (Cost Scales with Drama; Diamonds and Coal).

**Design Decision (GATING — recorded 2026-06-04 by operator):** Confrontation mode uses **SPLIT layout** (NOT full-screen takeover). When an encounter is active, the board canvas splits: narration prose on the LEFT, confrontation panel on the RIGHT (opponent portrait + stakes + Guitar-Solo party actions). This is the Duchess-recommended option from docs/design/confrontation-space-usage.md (Tier B). Rationale: keeps the soloist reachable and the rest of the band playing (SOUL.md "The Guitar Solo" — the others stay in the fiction and can act on it; never a silent audience). Cost Scales with Drama / Diamonds and Coal: the drama peak earns the screen, but not at the cost of cutting the table off from the prose.

**Technical Approach — Dockview Integration:**
- Reuse the existing dockview pattern (Character/Inventory/Map are already panels)
- Auto-focus the Confrontation dockview panel when an encounter is active
- Release focus on confrontation resolution
- THEM side displays opposing actor: portrait + name + their last beat (ADR-116 'requires an Other')
- Dial reads as a VS scoreboard (tug-of-war style)
- Stakes banner (set_stakes) shown prominently at the top of confrontation mode
- 'Meanwhile at the table' strip surfaces non-soloing players' concurrent verbs (The Guitar Solo)
- Solo play: opponent row degrades cleanly; 'meanwhile' strip collapses to nothing

**Protocol Dependency (OPEN SCOPING QUESTION):**
Confirm whether CONFRONTATION payload already carries `actors[].portrait` and `stakes` fields. If missing, server/protocol half (sidequest-server) is in scope and must be flagged for Architect review. Otherwise, this story is UI-only.

## References

- **docs/design/confrontation-space-usage.md** — The Duchess 2026-06-04, Tier B scope (split-with-narration layout)
- **docs/SOUL.md** — The Guitar Solo doctrine: non-soloists stay reachable and in the fiction
- **CLAUDE.md → Jade (author/playgroup member)** — mechanics-first player; benefits from legible opponent portrait + dial readout in player UI
- **ADR-116** — A Confrontation Requires an Other — Participant Membership Invariant
- **ADR-033** — Genre Mechanics Engine — Confrontations & Resource Pools
- **Epic 85-1** (status=done) — Tier A polish (dial legibility, beat-caption layout, dead-space removal)
- **Epic 85-2** (status=done) — Location surface source-of-truth design decision

## Acceptance Criteria

1. Architect decision recorded: **SPLIT layout chosen** (prose left, confrontation right) — locked in on 2026-06-04 by operator
2. While an encounter is active, a Confrontation dockview panel auto-focuses and releases focus on resolution
3. THEM side shows opposing actor: portrait + name + their last beat; dial reads as VS scoreboard; solo play degrades cleanly
4. Stakes banner (set_stakes) shown prominently at the top of confrontation mode
5. 'Meanwhile at the table' strip surfaces non-soloing players' concurrent verbs; collapses in solo play
6. Protocol check: if CONFRONTATION payload lacks `actors[].portrait` / `stakes`, flag server scope for Architect

## Branch Strategy
**Branch Strategy:** gitflow (feat/85-3-confrontation-mode-dockview-panel)

## Development Notes

- RED phase (TEA): ✅ Complete. 29 tests across 4 files, RED-verified. Protocol gap found + Architect-resolved (server in scope). See TEA Assessment.

### GREEN implementation map (Dev — The White Rabbit)

**Server (`sidequest-server`):**
1. `protocol/messages.py` `ConfrontationPayload` (~L834): add `stakes: str | None = None`. (`actors` is `list[dict[str,Any]]` → `portrait_url` rides the dict, no schema change.)
2. `server/dispatch/confrontation.py` `build_confrontation_payload` (L105): add params `active_stakes: str | None = None` and `portrait_resolver: Callable[[str], str | None] | None = None` (sibling to `core_resolver`, additive-optional). In the payload dict (L218): add `"stakes": active_stakes or None` (ALWAYS present, even legacy path). Replace actor serialization (L222) so each actor dict gets `"portrait_url": portrait_resolver(a.name) if (portrait_resolver and a.side == "opponent") else None`.
3. Emit OTEL span `confrontation.stakes_attached` once per build with attrs `genre_slug`, `confrontation_type` (=`encounter.encounter_type`), `has_stakes` (bool), `stakes_len` (int, 0 when absent). Define the span constant in `telemetry/spans/encounter.py` alongside the existing confrontation spans.
4. Thread at call sites — centralize, don't duplicate. `make_confrontation_frame_supplier` (L402, has `snapshot`+`genre_pack`) and the other 3 sites (`websocket_session_handler.py:1737`, `dispatch/dice.py:903`, `handlers/yield_action.py:149`) pass `active_stakes=snapshot.active_stakes` and a `portrait_resolver` lambda that precomputes `_world_portrait_slugs(pack, world_slug)` ONCE and closes over it → `_resolve_npc_portrait_url(pack=…, genre_slug=…, world_slug=…, npc_name=name, manifest_slugs=_slugs)` (emitters.py:761). Reuses existing scrapbook portrait spans — no new portrait span.

**UI (`sidequest-ui`):**
5. `components/ConfrontationOverlay.tsx`: add `stakes?: string` to `ConfrontationData`; add a `meanwhileActions?: { actor: string; role?: string; verb: string }[]` prop. Render: stakes banner (`data-testid="confrontation-stakes-banner"`, collapse on falsy); "meanwhile" strip (`data-testid="confrontation-meanwhile-strip"`, collapse on empty/undefined); dedicated THEM panel (`data-testid="confrontation-them-panel"`) with opponent name + portrait (reuse ActorChip `data-has-portrait`) + their last beat (`opponent_last_beat_impact.summary`), degrading cleanly when portrait absent.
6. `components/GameBoard/widgetRegistry.ts`: REVIVE `confrontation` — add to `WidgetId` union + `WIDGET_REGISTRY` (dataGated:true, closable:true). DELETE the stale "intentionally not a widget id" comment (L13).
7. `components/GameBoard/GameBoard.tsx`: gate `confrontation` in `availableWidgets` (L326) on `confrontationData != null` (add to deps); the add/remove effect (L734-769) auto-adds/removes; ADD `panel.api.setActive()` so it auto-FOCUSES on appear (AC2) and releases on resolve. Fix the stale L727 comment. Replace the bottom-strip `confrontationPanel` mount (L571-636) with the dockview panel — but keep SPLIT (narrative stays mounted; confrontation anchors to the right group). **Preserve the chandelier affordance:** narration + InputBar must remain reachable so free-text creative actions still work (operator note 2026-06-04).
8. Wire `meanwhileActions` from existing MP peer-action state (ADR-036 2026-05-03 amendment — peer action text visible during wait phase); collapses in solo.

- Recommended verify-phase tests (see TEA Assessment "Gaps deferred"): GameBoard auto-focus/release integration; manifest-backed portrait wiring assertion.