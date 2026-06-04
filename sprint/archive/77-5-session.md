---
story_id: "77-5"
jira_key: ""
epic: "77"
workflow: "tdd"
---
# Story 77-5: Quest/objective panel — render quest_log + quest_anchors + active_stakes (quests payload)

## Story Details
- **ID:** 77-5
- **Jira Key:** N/A (no Jira integration for this project)
- **Workflow:** tdd
- **Stack Parent:** none (not a stacked story)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-04T16:21:14Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-04T00:00:00Z | 2026-06-04T15:33:29Z | 15h 33m |
| red | 2026-06-04T15:33:29Z | 2026-06-04T15:43:43Z | 10m 14s |
| green | 2026-06-04T15:43:43Z | 2026-06-04T15:55:53Z | 12m 10s |
| review | 2026-06-04T15:55:53Z | 2026-06-04T16:05:36Z | 9m 43s |
| red | 2026-06-04T16:05:36Z | 2026-06-04T16:10:28Z | 4m 52s |
| green | 2026-06-04T16:10:28Z | 2026-06-04T16:13:36Z | 3m 8s |
| review | 2026-06-04T16:13:36Z | 2026-06-04T16:21:14Z | 7m 38s |
| finish | 2026-06-04T16:21:14Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

No upstream findings at setup.

### TEA (test design)
- **Conflict** (non-blocking): Story context AC4 + Interaction Patterns describe the
  Quests tab as **data-gated** ("appears only once the spine is non-empty"), but the
  reference it tells us to mirror — the Relationships panel — was changed to
  `dataGated: false` / always-present per Keith's 2026-06-04 playtest override
  (see `GameBoard-relationships-tab.test.tsx`). Tests encode the **always-present**
  pattern (the authoritative code, and the spine is creation-seeded so it is non-empty
  almost immediately). Affects `widgetRegistry.ts` (`quests` entry `dataGated:false`)
  and `GameBoard.tsx` (`availableWidgets` adds `quests` unconditionally).
  *Found by TEA during test design.*
- **Gap** (non-blocking): The legacy `ClientGameState.quests: Record<string,string>`
  field (never populated) collides with the natural name for the rich projection.
  Tests thread the rich payload as a **separate** `state.questsData: QuestsPayload | null`
  field (mirroring how the `relationshipsData` prop maps to `state.relationships`),
  leaving the legacy `quests` Record untouched. Affects `GameStateProvider.tsx`,
  `useStateMirror.ts`, `GameBoard.tsx` (prop `questsData`), `App.tsx`.
  *Found by TEA during test design.*
- **Improvement** (non-blocking): AC5 / Accessibility Requirements mandate the panel
  root be an ARIA `region` with an accessible name — a requirement the reference
  `RelationshipsPanel` does **not** currently meet (its root is a plain div). The
  panel test asserts `getByRole("region", { name: /quest|objective/i })`, so Dev must
  add `role="region"` + `aria-label` to the `QuestsPanel` root. Affects
  `QuestsPanel.tsx`. *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (non-blocking): `MobileTabView.tsx` carries its OWN hardcoded `TABS` array
  that must list each dockable tab independently of `widgetRegistry`/`rightGroupOrder`.
  A new tab does not appear on the mobile (jsdom) render path until it is added there.
  Added the `quests` entry (Scroll icon, after relationships) to match the
  relationships precedent. Affects `src/components/GameBoard/MobileTabView.tsx`.
  Future tab authors must remember this second registration surface.
  *Found by Dev during implementation.*
- **Conflict** (non-blocking): `npx tsc -b` exits 2 on develop due to **5 pre-existing
  type errors** in `src/components/__tests__/ConfrontationOverlay.beatimpact.test.tsx`
  (sibling story 73-4's RED tests, commit `78cd19b`, already an ancestor of develop —
  `BeatEffect` literal mismatch). These are **NOT** from 77-5: every file this story
  touched typechecks clean (verified via `grep` over `tsc -b` output → 0 quest-related
  errors), and the full UI vitest suite is 1842/1842 green. The verify/review phases
  should not misattribute the `tsc -b` failure to this story; it clears when 73-4
  reaches GREEN. *Found by Dev during implementation.*

### TEA (test design — rework round-trip 1)
- No new upstream findings during rework test design. Encoded the 3 Reviewer
  blocking findings as failing tests; the fixes are owned by Dev (green).

### Reviewer (code review — RT2 re-review, APPROVED)
- **Improvement** (non-blocking): Optional defense-in-depth hardening fast-follow — all
  server-unreachable, so not blocking. (a) null-check `msg.payload` before the
  Array.isArray guard in the QUESTS branch; (b) per-entry validation of `quest_id`/
  `anchor_id`; (c) add `|| !renderedAnchorIds.has(a.anchor_id)` to the orphan filter to
  close the asymmetric-back-ref + null-quest_id double-render edges and make the comment
  literally true; (d) soften the "never vanish" comment to "in all server-produced shapes."
  Affects `src/hooks/useStateMirror.ts`, `src/components/QuestsPanel.tsx`.
  *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Tighten tests — assert the dangling-anchor via
  `getByTestId("quests-orphan-anchor")` + `toHaveTextContent`; add a partial-array
  malformed variant; assert `quest_anchors` survives the valid-after-malformed cycle.
  Affects `src/components/__tests__/QuestsPanel.test.tsx`,
  `src/hooks/__tests__/useStateMirror.quests.test.ts`. *Found by Reviewer during code review.*

### Reviewer (code review)
- **Gap** (blocking): Dangling-reference quest anchors are silently dropped and the
  code comment falsely claims otherwise — a No-Silent-Fallbacks `<critical>` rule
  violation. Affects `src/components/QuestsPanel.tsx` (orphan filter must also catch
  `quest_id` not present in `quest_log`; fix the comment).
  *Found by Reviewer during code review.*
- **Gap** (blocking): `isEmptySpine` throws on a malformed/missing-field payload instead
  of degrading to the empty state — less robust than the mirrored `RelationshipsPanel`,
  contra AC2 ("does not white-screen or throw on missing/undefined fields"). Affects
  `src/components/QuestsPanel.tsx` + `src/hooks/useStateMirror.ts` (validate the QUESTS
  payload at the mirror boundary, mirroring the `fact_id` guard at useStateMirror.ts:284).
  *Found by Reviewer during code review.*
- **Gap** (blocking): The `quests-orphan-anchor` render branch has zero test coverage.
  Affects `src/components/__tests__/QuestsPanel.test.tsx` (add orphan-render,
  dangling-anchor, and malformed-payload-degrades tests). *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

No deviations at setup.

### TEA (test design)
- **Quests tab is always-present, not data-gated**
  - Spec source: context-story-77-5.md, AC4 + Interaction Patterns
  - Spec text: "data-gated so the tab appears only once the spine is non-empty (mirroring relationships' availableWidgets gating)"
  - Implementation: tests require `dataGated: false` and an unconditional `availableWidgets` add — the always-present pattern the Relationships reference now uses (`GameBoard-relationships-tab.test.tsx`, Keith override 2026-06-04). Empty state (AC2) covers the "nothing to show" case.
  - Rationale: the spec says "mirror relationships"; the live relationships code abandoned data-gating, and the quest spine is creation-seeded (77-1) so it is non-empty almost immediately. Following the stale gating language would contradict the authoritative reference and reintroduce the tab-flicker Keith flagged.
  - Severity: minor
  - Forward impact: Dev wires `quests` into `availableWidgets` unconditionally; no data-gating branch. Reviewer should accept always-present over AC4's literal "data-gated" wording.
- **Rich projection threads as `questsData`, not `quests`**
  - Spec source: context-story-77-5.md, Technical Guardrails ("a separate `quests` field on the game-state snapshot")
  - Spec text: "the new rich projection will arrive via a separate `quests` field … analogous to how `relationships` threads separately"
  - Implementation: tests assert `state.questsData` (not `state.quests`), because `ClientGameState.quests: Record<string,string>` already exists and must stay for old-save compatibility.
  - Rationale: a same-name field would either shadow or fight the legacy Record; "separate field" is honored, just under a non-colliding name matching the `relationshipsData` prop convention.
  - Severity: minor
  - Forward impact: Dev adds `questsData?: QuestsPayload | null` to `ClientGameState` + `GameBoardProps`; `App.tsx` threads `questsData={gameState.questsData ?? null}`.
- **Hotkey asserted unique, not pinned to a specific letter**
  - Spec source: context-story-77-5.md, Technical Guardrails (line 88) vs Interaction Patterns (line 206)
  - Spec text: line 88 says avoid `q` ("taken"); line 206 says use `q` "if available" — an internal contradiction. Live `widgetRegistry`/`buildHotkeyMap` shows `q` is in fact FREE.
  - Implementation: the wiring test asserts the `quests` hotkey is a defined single char that collides with no other registry entry — the real accessibility invariant — rather than hard-pinning `q`.
  - Rationale: the spec contradicts itself on `q`; the authoritative invariant is "no collision." `q` remains the natural choice and is free.
  - Severity: trivial
  - Forward impact: Dev may pick `q` (or any free letter); test enforces only uniqueness.
- **Malformed-payload guard tested at the mirror boundary, not the panel (rework RT1)**
  - Spec source: Reviewer Assessment (review RT1), blocking finding #2; AC2
  - Spec text: Reviewer — "Pick one [fix location]; mirror branch validation is preferred (fail loud at the boundary)."
  - Implementation: the new rework tests assert at `useStateMirror` (a malformed QUESTS payload → `state.questsData` stays null) rather than asserting the panel renders an empty state on malformed input. This forces the boundary-validation fix and leaves the panel's guard logic unchanged.
  - Rationale: honors the Reviewer's explicit "pick one — mirror preferred"; matches the file's own `fact_id` validation precedent; one fix, one contract. The panel never receives malformed data once the boundary rejects it, so AC2 ("no white-screen/throw") holds end-to-end without a redundant panel guard.
  - Severity: minor
  - Forward impact: Dev must validate the QUESTS payload in the `useStateMirror` QUESTS branch (Array.isArray(quest_log) && Array.isArray(quest_anchors) && typeof active_stakes === 'string', else console.error + continue). The dangling-anchor fix remains in `QuestsPanel` (orphan filter).

### Dev (implementation)
- **Added Quests to MobileTabView TABS (second registration surface)**
  - Spec source: context-story-77-5.md, AC4 + Technical Guardrails (mirror the dock-panel pattern)
  - Spec text: "Registry/widget/GameBoard/App/provider wiring so the tab actually mounts and is reachable from production code paths"
  - Implementation: in addition to the registry/GameBoard/App wiring TEA enumerated, also added a `{ id: "quests", ... }` entry to the hardcoded `TABS` array in `MobileTabView.tsx` (Scroll icon, after relationships). The story context listed the dockview surfaces but not this mobile one.
  - Rationale: the GameBoard wiring test renders via the jsdom→mobile `MobileTabView` path; the tab does not appear there until listed in its own TABS array (same as relationships). Required for the wiring AC to actually hold on the mobile surface.
  - Severity: minor
  - Forward impact: none for 77-5; documents the dual registration surface for future tab authors (also logged as a Delivery Finding).
- **No other deviations.** Component, types, state-mirror, and dock wiring follow the RelationshipsPanel/RELATIONSHIPS reference exactly as TEA's Dev Contract specified. Hotkey `q` chosen (free, the natural letter). `dataGated:false` always-present per the resolved AC4 conflict.

### Reviewer (audit)
- **TEA: Quests tab always-present, not data-gated** → ✓ ACCEPTED by Reviewer: sound. The live `RelationshipsPanel` reference is `dataGated:false` (Keith's 2026-06-04 override) and the spine is creation-seeded; following AC4's stale "data-gated" wording would contradict the authoritative reference. AC2's empty-state covers "nothing to show."
- **TEA: Rich projection threads as `questsData`, not `quests`** → ✓ ACCEPTED by Reviewer: the legacy `ClientGameState.quests: Record<string,string>` genuinely occupies the name and must stay for old-save compat; a separate `questsData` field honors the "separate field" intent and mirrors the `relationshipsData→relationships` convention. Verified the legacy Record is left untouched (`useStateMirror.quests.test.ts` asserts `state.quests` stays `{}`).
- **TEA: Hotkey asserted unique, not pinned to `q`** → ✓ ACCEPTED by Reviewer: the story context self-contradicts on `q` (line 88 vs 206); `buildHotkeyMap` confirms `q` is free. Asserting uniqueness is the real accessibility invariant; Dev chose `q`, which is correct.
- **Dev: Added Quests to MobileTabView TABS (second registration surface)** → ✓ ACCEPTED by Reviewer: necessary and correct. The mobile `TABS` array is a genuine second registration surface independent of the dockview registry; without it the wiring AC fails on the mobile render path. Mirrors the `relationships` precedent (icon + position). Good catch.
- **No undocumented deviations spotted.** The implementation faithfully tracks TEA's Dev Contract; the blocking findings above are robustness/coverage gaps, not undocumented spec divergences.

### Reviewer (audit) — RT2 (re-review)
- **TEA: Malformed-payload guard tested at the mirror boundary, not the panel (rework RT1)** → ✓ ACCEPTED by Reviewer: correct and follows my own RT1 "pick one — mirror preferred" guidance. Boundary validation matches the file's `fact_id` precedent and is one fix, one contract. Verified the boundary rejects malformed top-level shapes (3 green mirror tests) and the panel no longer receives them.
- **Dev: No new RT1 deviations** → ✓ ACCEPTED by Reviewer: the two fixes implement the TEA Dev Contract exactly (widened orphan filter + mirror-boundary validation). No undocumented divergence in the rework.

## SM Assessment

**Story:** 77-5 — Quest/objective panel: render `quest_log` + `quest_anchors` + `active_stakes` (quests payload). Render-only UI panel in `sidequest-ui`. 5 pts, tdd (phased) workflow.

**Unblocked:** This story was sequenced behind 77-8 (server quests projection). 77-8 is now **done and merged** (server PR #650). The outbound rich quests payload reaches the client, so this panel finally has something to consume. No remaining dependency block (`depends_on: null`).

**Setup state:**
- Session file created at `.session/77-5-session.md`.
- Story context at `sprint/context/context-story-77-5.md` **refreshed** — old version predated 77-8's merge and described the projection as a blocking dependency; now updated to point at the live payload contract.
- Branch `feat/77-5-quest-objective-panel` created on `sidequest-ui` (base: `develop`).
- Jira claim **skipped** — Jira integration is not configured for this project (`pf jira` refuses to contact).
- Merge gate clear — no open PRs.

**Technical guardrail for TEA/Dev (load-bearing):** Mirror the server `QuestsPayload` shape into a real `QuestsPayload` TS interface (`quest_log: QuestLogEntry[]`, `quest_anchors: QuestAnchorEntry[]`, `active_stakes: string`). **Do NOT** fabricate it into a thin `Record<string,string>`. Server source of truth: `sidequest-server/sidequest/protocol/models.py`. Follow the `RelationshipsPanel` (ADR-136) dockable-panel pattern, and include a wiring test proving the panel is reachable from a production code path (per the project's "Every Test Suite Needs a Wiring Test" principle).

**Routing:** Phased TDD → handoff to **TEA (Amos Burton)** for RED phase.

---
## TEA Assessment

**Tests Required:** Yes
**Status:** RED (failing — ready for Dev)

**Test Files:**
- `sidequest-ui/src/components/__tests__/QuestsPanel.test.tsx` — component render: quest_log title/objective, anchor resolution (rich-shape guard), active_stakes, null + empty-projection empty states, ARIA region. (AC1, AC2, AC5)
- `sidequest-ui/src/hooks/__tests__/useStateMirror.quests.test.ts` — QUESTS snapshot mirror: starts null, populates `questsData`, later message full-replaces (snapshot), legacy `quests` Record left untouched. (AC3)
- `sidequest-ui/src/components/GameBoard/__tests__/GameBoard-quests-tab.test.tsx` — **wiring test**: QuestsWidget/QuestsPanel importable, registry entry `dataGated:false` + defined/unique hotkey, tab always present (null + populated), empty-state copy, seeded quest renders from GameBoard's render path. (AC4)
- `sidequest-ui/src/types/__tests__/quests-protocol.test.ts` — `MessageType.QUESTS` + rich `QuestsPayload`/`QuestLogEntry`/`QuestAnchorEntry` shape parity (nullable anchor linkage). (no-fabrication contract)

**Tests Written:** 17 tests across 4 files covering AC1–AC5 + the no-fabrication payload contract.

### RED Evidence (two gates)
- **vitest run:** `QuestsPanel.test.tsx` and `GameBoard-quests-tab.test.tsx` fail at transform (`Cannot find module ../QuestsPanel`, `…/QuestsWidget`); `useStateMirror.quests.test.ts` fails on `questsData` undefined; `quests-protocol.test.ts` fails on `MessageType.QUESTS` undefined. No unexpected passes that test real behavior.
- **tsc -b (typecheck gate, part of `client-build`/`check-all`):** exits 2 with named errors for every missing artifact — `../QuestsPanel` module, `QuestsPayload`/`QuestLogEntry`/`QuestAnchorEntry` exports, `@/components/GameBoard/widgets/QuestsWidget`, `MessageType.QUESTS`, `ClientGameState.questsData`. The typed-fixture parity tests are therefore genuine compile-time guards, **not** runtime-vacuous.

### Rule Coverage (lang-review: typescript.md)
| Rule | Test(s) | Status |
|------|---------|--------|
| #4 null/undefined — no white-screen on missing fields | `QuestsPanel` "empty state when data is null", "well-formed empty projection" | failing |
| #4 `??` not `\|\|` on nullable snapshot | `useStateMirror` "starts with projection null" | failing |
| #6 React snapshot full-replace (no stale accumulation) | `useStateMirror` "later message fully replaces" | failing |
| #10 input-validation / typed payload (no `Record<string,any>` fabrication) | `quests-protocol` rich-shape fixture; `QuestsPanel` "renders rich anchor resolution" | failing |
| Enum completeness (MessageType parity w/ server) | `quests-protocol` "MessageType includes QUESTS" | failing |
| Wiring (project rule: every suite needs a wiring test) | `GameBoard-quests-tab` importable + tab reachable from render path | failing |
| Accessibility (AC5 ARIA region, no color-only emphasis) | `QuestsPanel` "ARIA region with accessible name" | failing |

**Rules checked:** 7 applicable lang-review/project rules have test coverage.
**Self-check:** 0 vacuous tests. The two `quests-protocol` payload-shape tests pass under bare `vitest` only because esbuild erases types — but they FAIL the `tsc -b` typecheck gate (the dev's `client-build`/`check-all` runs it), so they are real guards. Confirmed via direct `npx tsc -b`.

### Dev Contract (the names these tests pin)
- Component `QuestsPanel` at `src/components/QuestsPanel.tsx`, props `{ data: QuestsPayload | null }`; root `role="region"` + accessible name; testid `quests-empty`; empty copy matches `/no objective/i`.
- Widget `QuestsWidget` at `src/components/GameBoard/widgets/QuestsWidget.tsx` (thin adapter).
- Types in `src/types/payloads.ts`: `QuestLogEntry` (quest_id, title, objective, status, anchor_id), `QuestAnchorEntry` (anchor_id, quest_id?, resolution?), `QuestsPayload` (quest_log, quest_anchors, active_stakes) — mirror `protocol/models.py` snake_case exactly.
- `MessageType.QUESTS = "QUESTS"` in `src/types/protocol.ts`.
- State: `ClientGameState.questsData?: QuestsPayload | null` (default null); `useStateMirror` full-replaces it on a QUESTS message (mirror the RELATIONSHIPS handler).
- `widgetRegistry.ts`: `"quests"` WidgetId + entry, label `/quests|objectives/i`, `dataGated:false`, free unique hotkey (`q` is available).
- `GameBoard.tsx`: `questsData` prop, `renderWidgetContent` case, `availableWidgets` unconditional add, `rightGroupOrder` slot, useMemo deps.
- `App.tsx`: thread `questsData={gameState.questsData ?? null}`.

**Handoff:** To Dev (Naomi Nagata) for GREEN.

---
## Dev Assessment

**Implementation Complete:** Yes
**Tests:** 20/20 story tests passing (GREEN). Full `sidequest-ui` suite: **1842/1842** passing, 193 files, **0 regressions**.
**Branch:** `feat/77-5-quest-objective-panel` (pushed to origin).

**Files Changed (implementation — commit on top of TEA's RED commit):**
- `src/types/payloads.ts` — added `QuestLogEntry`, `QuestAnchorEntry`, `QuestsPayload` interfaces mirroring `protocol/models.py` snake_case.
- `src/types/protocol.ts` — `MessageType.QUESTS = "QUESTS"` snapshot channel.
- `src/components/QuestsPanel.tsx` *(new)* — presentational panel: `active_stakes` ("At stake"), `quest_log` (title + status + objective, with inline anchor resolution), orphan `quest_anchors`; empty-state branch first; `role="region"` + `aria-label="Quests and objectives"`; Folio CSS-custom-property styling (ADR-079). No `!` non-null assertions (narrowed via guard).
- `src/components/GameBoard/widgets/QuestsWidget.tsx` *(new)* — thin adapter.
- `src/components/GameBoard/widgetRegistry.ts` — `"quests"` WidgetId + entry (label "Quests", hotkey `q`, `dataGated:false`).
- `src/components/GameBoard/GameBoard.tsx` — `questsData` prop + default, `availableWidgets` unconditional add, `renderWidgetContent` case, `rightGroupOrder` slot (after relationships), useMemo deps.
- `src/components/GameBoard/MobileTabView.tsx` — `quests` entry in the mobile `TABS` array (committed by the test run as `bfc2524`; reviewed and accepted by Dev — see deviations/findings).
- `src/hooks/useStateMirror.ts` — QUESTS full-replace snapshot → `state.questsData`; legacy `quests` Record untouched.
- `src/providers/GameStateProvider.tsx` — `ClientGameState.questsData?: QuestsPayload | null` + `EMPTY_GAME_STATE` default `null`.
- `src/App.tsx` — thread `questsData={gameState.questsData ?? null}` to GameBoard.

**AC coverage:** AC1 (renders all three spine fields) ✓ · AC2 (empty + seeded states, no white-screen) ✓ · AC3 (reactive full-replace snapshot) ✓ · AC4 (wired + reachable from GameBoard render path on both desktop dockview and mobile tab surfaces) ✓ · AC5 (ARIA region + theme custom properties, no hardcoded colors) ✓.

**Type-level:** every 77-5 file typechecks clean under `tsc -b` (0 quest-related errors). The repo-wide `tsc -b` exits 2 ONLY because of 5 pre-existing `BeatEffect` errors in sibling story 73-4's RED test (`ConfrontationOverlay.beatimpact.test.tsx`, already on develop) — documented as a Delivery Finding so it is not misattributed.

**Self-review:** Wired to App→GameBoard (desktop + mobile) ✓ · follows RelationshipsPanel/RELATIONSHIPS pattern ✓ · all ACs met ✓ · empty/undefined handled (no throw) ✓ · no debug code / clean tree ✓.

**Handoff:** To verify/review phase.

---
## Subagent Results — Review RT1 (REJECTED, superseded)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (1842/1842 green; lint/type clean on all 77-5 files; pre-existing develop noise isolated) | N/A |
| 2 | reviewer-edge-hunter | Yes | findings | 9 | confirmed 3, dismissed 4, deferred 2 |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 4 | confirmed 1, dismissed 1, deferred 2 |
| 4 | reviewer-test-analyzer | Yes | findings | 9 | confirmed 3, dismissed 4, deferred 2 |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings — assessed by Reviewer ([DOC]) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings — assessed by Reviewer ([TYPE]) |
| 7 | reviewer-security | Yes | findings | 2 | confirmed 0, dismissed 0, deferred 2 (both low, forward-looking) |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings — assessed by Reviewer ([SIMPLE]) |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings — assessed by Reviewer ([RULE]) |

**All received:** Yes (5 enabled returned, 4 with findings; 4 disabled pre-filled and assessed by Reviewer)
**Total findings:** 7 confirmed, 9 dismissed (with rationale), 8 deferred/non-blocking

---
## Reviewer Assessment — Review RT1 (REJECTED, superseded)

**Verdict:** REJECTED

A clean, well-patterned, fully-green diff (1842/1842, lint/type clean on every changed file) — but the review found a **No-Silent-Fallbacks `<critical>` rule violation with a self-contradicting comment**, a **robustness regression vs. the `RelationshipsPanel` this story is required to mirror** (AC2: "does not white-screen or throw on missing/undefined fields"), and an **entirely untested render branch**. These converge across three independent specialists. None is reachable from today's pydantic-validated server, but a player-facing legibility surface that can silently drop an objective or white-screen on a malformed payload is exactly the "Illusionism" the project's No-Silent-Fallbacks/OTEL culture exists to prevent. Fixes are cheap and testable → back to TEA for a hardening round.

### Blocking findings

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] [SILENT][RULE] | Dangling-reference anchor silently dropped: the orphan filter `!a.quest_id` catches only null `quest_id`. An anchor with a non-null `quest_id` whose quest is absent from `quest_log` is rendered neither inline nor in the orphan list — silently dropped. The comment at the block claims "surfaced explicitly rather than silently dropped" — the comment is **false**. Violates the No-Silent-Fallbacks `<critical>` rule (CLAUDE.md). Confirmed by silent-failure-hunter (high) + edge-hunter (medium). | `src/components/QuestsPanel.tsx:118-134` | Build a `Set` of `quest_log` quest_ids and filter orphans as `!a.quest_id \|\| !questIds.has(a.quest_id)` so dangling anchors are surfaced (and the comment becomes true). |
| [HIGH] [EDGE] | `isEmptySpine` dereferences `data.quest_log.length`, `data.quest_anchors.length`, `data.active_stakes.trim()` with no field guard. A malformed/partial QUESTS payload (null `active_stakes`, missing array) throws a TypeError in the render path — white-screening the panel — instead of degrading to the empty state. AC2 explicitly requires "does not white-screen or throw on missing/undefined fields." The mirrored reference `RelationshipsPanel` is MORE robust (its `!data \|\| data.length === 0` guard degrades a missing array to empty-state). Confirmed edge-hunter (high mechanism) + silent-failure-hunter (medium) + security (low). | `src/components/QuestsPanel.tsx:31-39,76` and `src/hooks/useStateMirror.ts:~240` | Validate the payload shape at the QUESTS mirror branch (mirror the existing `fact_id` guard at `useStateMirror.ts:284-289`: `if (!Array.isArray(p.quest_log) \|\| !Array.isArray(p.quest_anchors) \|\| typeof p.active_stakes !== 'string') { console.error(...); continue; }`), OR field-guard `isEmptySpine` (`data.quest_log?.length ?? 0`, `(data.active_stakes ?? "").trim()`). Pick one; mirror branch validation is preferred (fail loud at the boundary). |
| [MEDIUM] [TEST] | The `quests-orphan-anchor` render branch (the `quest_id: null` path) has **zero test coverage** — every fixture in the suite uses a non-null `quest_id`, so the orphan filter always yields `[]`. A regression that drops orphans entirely would pass every test. | `src/components/__tests__/QuestsPanel.test.tsx` | Add a test: a payload with an anchor `quest_id: null`; assert `getByTestId("quests-orphan-anchor")` renders the anchor id. Add a dangling-`quest_id` case and a malformed-payload-degrades-to-empty-state case to lock the fixes above. |

### Non-blocking findings (address opportunistically with the rework)

- [DOC] (comment_analyzer disabled — assessed by Reviewer) `QuestsPanel.tsx:118-119` comment over-claims No-Silent-Fallbacks compliance; it becomes true once the orphan filter is fixed. Fix together.
- [TEST] `useStateMirror.quests.test.ts:69` "starts null" asserts `state.questsData ?? null` → `toBeNull()`; the `?? null` coercion passes even if the field is misspelled or absent from `EMPTY_GAME_STATE`. Strengthen to assert `state.questsData` directly with `toBeNull()`. (test-analyzer, high)
- [EDGE] `QuestsPanel.tsx:61` duplicate `anchor_id` → silent `Map` clobber; duplicate `quest_id` → React key collision. Same risk class as `RelationshipsPanel`'s `key={e.name}`; malformed-data-only. LOW.
- [SEC] (security, low, forward-looking) If `resolution`/`title` ever gain markdown/rich-text rendering, narrator-authored strings MUST be sanitized (DOMPurify) before any `dangerouslySetInnerHTML`. Not vulnerable today (all text children, auto-escaped).
- [EDGE] long-string overflow on `anchor_id`/`title` — pre-existing pattern across all panels; CSS-level, non-blocking.

### Dismissed (with rationale)

- [TEST] "whitespace-only `active_stakes` hides the quest list" (test-analyzer, medium) — **DISMISSED**: `isEmptySpine` is `&&` of all three conditions; a non-empty `quest_log` makes `quest_log.length === 0` false → not empty → quests render. The analyzer misread `&&` as `||`. No bug. (A whitespace-stakes test is a harmless nice-to-have, not a defect.)
- [TEST] snapshot replace test "uses 1→1, can't prove replace vs accumulate" (test-analyzer, medium) — **DISMISSED**: the two payloads carry different `quest_id`s, so an accumulating/merging mirror would yield `length 2`; the test asserts `toHaveLength(1)` AND the new title, which catches accumulation. Adequate.
- [EDGE] same-length-replace `setState` gap (edge, low) — **DISMISSED**: pre-existing for `relationships`/`currentLocation`, inherited not introduced; messages are append-only in practice.
- [TYPE][SEC] `as unknown as QuestsPayload` double-cast (security/edge/silent) — **CONFIRMED-as-idiom but folded** into the isEmptySpine/mirror-validation blocking finding: it matches the codebase-wide wire-trust pattern (RELATIONSHIPS, LOCATION_DESCRIPTION), so the cast itself is not a regression — but the file's OWN `fact_id` precedent shows validation is the house posture where a malformed payload can crash, which is the fix above.
- [TEST] typeof-importability tests "low value" (test-analyzer, medium) — **NOTED, keep**: redundant given the render tests but harmless; not worth churn.
- [SEC] `sessionStorage` empty-catch (silent-failure, low) — **DISMISSED**: pre-existing hydration resilience, not in this diff.
- [EDGE] App.tsx `?? null` redundancy (silent-failure, low) — **DISMISSED**: consistent with `relationshipsData={... ?? null}`; harmless.

### Rule Compliance (lang-review typescript.md + CLAUDE.md/SOUL.md — exhaustive, since type_design + rule_checker disabled)

- **No Silent Fallbacks (CLAUDE.md `<critical>`):** ✗ VIOLATION — dangling-reference anchor dropped silently (`QuestsPanel.tsx:120`). Blocking finding #1. Every other field-absence path checked: `q.anchor_id ?` (line 91, handled), `anchor.resolution ?` (line 111, handled), `!a.quest_id` orphan (line 120, INCOMPLETE).
- **TS #1 type-safety escapes:** `as unknown as QuestsPayload` (useStateMirror) — matches established idiom; no `as any`, no `@ts-ignore`, no non-null `!` in production (verified `QuestsPanel.tsx` uses a guard-narrow, not `data!`). Compliant-by-consistency; validation-gap folded into blocking finding #2.
- **TS #2 generic/interface:** `QuestLogEntry`/`QuestAnchorEntry`/`QuestsPayload` are proper interfaces, no `Record<string,any>`. Nullable fields correctly `| null`. Mirrors server `protocol/models.py` snake_case. ✓
- **TS #3 enum:** `MessageType.QUESTS` added to the const-object union; useStateMirror uses the existing if-`continue` chain (no `assertNever`), consistent with the RELATIONSHIPS/LOCATION handlers. ✓
- **TS #4 null/undefined:** ✗ partial — `isEmptySpine` field derefs are the robustness gap (finding #2). `?? null` used correctly (not `||`) in App/GameBoard/mirror. The `?? null` in the "starts null" TEST is too weak (non-blocking finding).
- **TS #6 React/JSX:** `key={q.quest_id}` / `key={a.anchor_id}` stable (not index) ✓; `questsData` correctly added to the `renderWidgetContent` useMemo deps ✓; no `useEffect` added; no `dangerouslySetInnerHTML` ✓.
- **TS #10 input validation:** no runtime schema validation on the wire payload — consistent with the whole mirror, but finding #2 asks for a boundary guard (the file's own `fact_id` precedent).
- **Wiring (CLAUDE.md "every suite needs a wiring test"):** ✓ `GameBoard-quests-tab.test.tsx` mounts GameBoard and asserts the tab is reachable + renders the seeded quest (not just `typeof`). Desktop dockview switch-case path is untested in jsdom (mobile path runs) — noted, non-blocking.

### Five+ observations

1. [VERIFIED] XSS-safe — `QuestsPanel.tsx` has zero `dangerouslySetInnerHTML`; all narrator strings (`title`, `objective`, `status`, `active_stakes`, `anchor_id`, `resolution`) render as JSX text children, auto-escaped. Evidence: security specialist confirmed 0 innerHTML sites; grep-verified.
2. [VERIFIED] Full wiring on both surfaces — data flow QUESTS → `useStateMirror.ts:~240` → `current.questsData` → `GameStateProvider` → `App.tsx:2280` → `GameBoard` `renderWidgetContent` case "quests" → `QuestsWidget` → `QuestsPanel`; desktop via `availableWidgets`+`rightGroupOrder`+useMemo deps, mobile via `MobileTabView` TABS. Evidence: read all wiring hunks.
3. [HIGH] [SILENT][RULE] Dangling-anchor silent drop + false comment — `QuestsPanel.tsx:120`. (Blocking #1.)
4. [HIGH] [EDGE] `isEmptySpine` throws on malformed/missing fields; less robust than the mirrored `RelationshipsPanel`; AC2 conformance gap — `QuestsPanel.tsx:31-39`. (Blocking #2.)
5. [MEDIUM] [TEST] Orphan-anchor render branch entirely untested — `QuestsPanel.test.tsx`. (Blocking #3.)
6. [LOW] [DOC] Self-contradicting orphan comment — `QuestsPanel.tsx:118`.
7. [VERIFIED] [SIMPLE] (simplifier disabled — assessed by Reviewer) No over-engineering — `isEmptySpine` helper + `anchorsById` Map are minimal and idiomatic; no dead code, no premature abstraction. The orphan-list branch is the only complexity and it's load-bearing (once corrected).

### Devil's Advocate

Assume this panel is broken and a player is about to be misled. The whole reason this story exists is so a forever-GM (Keith) can *see* the campaign spine and trust it — the antidote to a narrator that improvises objectives that live only in its head. Now: what does the narrator/server actually feed this panel? Narrator-authored, LLM-generated strings and a quest graph that is *eventually* consistent, not transactionally consistent. The narrator mints a quest, sets its `anchor_id`, later the quest resolves or is pruned — and for a beat the snapshot can carry an anchor whose `quest_id` points at a quest no longer in the log. The panel's response to that exact condition is to **show nothing** — no anchor, no "objective resolves here," no warning — while the comment in the code reassures the next developer that nothing is dropped. That is the precise failure the project's OTEL/no-silent-fallbacks doctrine is built to catch: the surface looks fine, the mechanical truth quietly disappeared. A confused player sees a stakes line and a quest but never learns *where* it resolves; a GM auditing the panel against the engine sees a discrepancy with no signal. Worse: feed this component a single malformed snapshot — `active_stakes: null` from a server version skew, or a payload that lost `quest_log` to a serialization bug — and `isEmptySpine` doesn't degrade to "No objective yet," it throws a TypeError mid-render. Without an error boundary around the dock, that unmounts the React tree: a white screen, mid-session, for the whole table. The sibling `RelationshipsPanel` was written to survive exactly this (`!data || data.length === 0` on the array itself); this panel, which claims to "mirror" it, regressed the robustness. The counter-argument — "pydantic guarantees the shape, the dangling case can't happen" — is the same confidence that precedes every production incident; the server is one refactor or one cross-version client away from violating it, and the cost of the guard is one line that already has a precedent in the same file (`fact_id`, line 284). For a brand-new player-facing legibility surface, "correct against today's server" is not the bar; "fails loud and never white-screens" is. Hence: harden it, test the dropped branch, fix the lying comment.

### Handoff: Back to TEA for rework (red) — add failing tests for the dangling-anchor surfacing, the malformed-payload-degrades-to-empty-state guard, and the orphan render branch; then Dev (green) implements the fixes.
---
## TEA Assessment — Rework RT1 (red)

**Tests Required:** Yes (rework — encode Reviewer blocking findings as failing tests)
**Status:** RED (3 new failing tests ready for Dev)

**Tests added/changed:**
- `src/components/__tests__/QuestsPanel.test.tsx`
  - **RED** "surfaces a dangling-reference anchor whose owning quest is absent from the log" → covers Reviewer finding #1 (No-Silent-Fallbacks). Fails now (resolution text not rendered — anchor dropped).
  - "renders an orphan anchor whose quest_id is null" → coverage for finding #3 (the orphan branch was untested). Passes now (the null path already works) — locks it against regression during the filter fix.
- `src/hooks/__tests__/useStateMirror.quests.test.ts`
  - **RED** "degrades a malformed QUESTS payload (missing arrays) to null" → covers finding #2 at the mirror boundary. Fails now (stores garbage).
  - **RED** "degrades a QUESTS payload with a non-string active_stakes to null" → same. Fails now.
  - "keeps a valid projection after a malformed one is rejected" → regression guard; passes now and after the fix.
  - Strengthened "starts with the quests projection null" → `toBeNull()` directly (dropped the `?? null` coercion) per Reviewer non-blocking test-quality finding.

**RED evidence:** `npx vitest run` on both files → **3 failed / 11 passed**. The 3 failures are exactly the dangling-drop + 2 malformed cases, each failing for the right reason (anchor not rendered; mirror stored the malformed object rather than null). All coverage/regression locks pass.

### Reviewer-finding → test map
| Reviewer finding | Test | Status |
|------------------|------|--------|
| #1 dangling anchor silently dropped (No-Silent-Fallbacks) | QuestsPanel "surfaces a dangling-reference anchor…" | RED |
| #2 malformed payload throws (AC2) — fix at mirror boundary | useStateMirror "degrades … missing arrays" + "non-string active_stakes" | RED ×2 |
| #3 orphan branch zero coverage | QuestsPanel "renders an orphan anchor whose quest_id is null" | green (coverage lock) |
| (non-blocking) weak `?? null` assertion | useStateMirror "starts … null" strengthened | green |

### Dev Contract (the fixes these tests force)
1. **`useStateMirror` QUESTS branch:** validate before storing — `Array.isArray(p.quest_log) && Array.isArray(p.quest_anchors) && typeof p.active_stakes === 'string'`, else `console.error(...) ` + `continue` (fail loud at the boundary; mirrors the `fact_id` precedent). A malformed payload leaves `questsData` null.
2. **`QuestsPanel` orphan filter:** include dangling-reference anchors — build a `Set` of `quest_log` quest_ids and filter `quest_anchors` as `!a.quest_id || !questIds.has(a.quest_id)`. **Fix the comment** so it stops claiming compliance the old filter didn't have.

**Self-check:** 0 vacuous tests — every new test asserts an observable (rendered text / `questsData` null). The one new always-green test (orphan-null) is an intentional coverage lock for a branch the fix touches, not a vacuous assertion.

**Handoff:** To Dev (Naomi Nagata) for GREEN — implement the two fixes; do not weaken or delete the failing tests.
---
## Dev Assessment — Rework RT1 (green)

**Implementation Complete:** Yes
**Tests:** 3 previously-RED rework tests now PASS. Full `sidequest-ui` suite: **1847/1847** passing, 193 files, **0 regressions**.
**Branch:** `feat/77-5-quest-objective-panel` (pushed; commit `24dd865`).

**Reviewer blocking findings → fixes:**
1. **No-Silent-Fallbacks: dangling anchor dropped** (`QuestsPanel.tsx`) → orphan filter widened to `!a.quest_id || !loggedQuestIds.has(a.quest_id)` (built a `Set` of `quest_log` quest_ids). A dangling-reference anchor (owning quest absent from the log) is now surfaced in the orphan list. **Comment corrected** to describe both the null-quest_id and dangling cases accurately. No double-render introduced for the normal case (an anchor owned by a logged quest has `quest_id ∈ loggedQuestIds` → excluded from orphans, rendered inline).
2. **AC2: malformed payload throws** (`useStateMirror.ts` QUESTS branch) → boundary validation per the Reviewer's preferred location: `Array.isArray(p.quest_log) && Array.isArray(p.quest_anchors) && typeof p.active_stakes === 'string'`, else `console.error(...)` + `continue` (fail loud, leave `questsData` unchanged). Mirrors the file's `fact_id` precedent. A valid snapshot after a rejected malformed one still lands (regression-guarded).
3. **Orphan branch zero coverage** → TEA added the orphan-null coverage test (green) + the dangling-anchor RED test (now green).

**Non-blocking items addressed:** strengthened the `?? null` "starts null" assertion to `toBeNull()` (TEA, RT1). The lower-priority items (duplicate-id handling, long-string overflow, dockview-path test) were left as documented non-blocking — they match pre-existing patterns and the Reviewer deferred them.

**Quality:** typecheck clean on both changed files (0 errors); eslint clean on both. No `as any`, no new non-null assertions, no debug code (the `console.error` is the intentional fail-loud signal, not debug). Clean tree, pushed.

**Self-review:** No-Silent-Fallbacks honored (anchor surfaced + fail-loud on malformed) ✓ · AC2 no-throw satisfied at the boundary ✓ · all rework tests green ✓ · no regressions (1847/1847) ✓.

**Handoff:** To Reviewer (Chrisjen Avasarala) for re-review.

### Dev (implementation) — Rework RT1 deviations
- No new deviations. Both fixes implement exactly the TEA Dev Contract (mirror-boundary validation + widened orphan filter). The malformed-payload guard is at the mirror boundary, not the panel, per the Reviewer's explicit "pick one — mirror preferred" guidance and TEA's RT1 deviation note.
---
## Subagent Results

(Re-review — Review RT2, after rework round-trip 1. Subagents re-run on the rework delta `5e3a25c..HEAD`.)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (1847/1847 green; rework files lint/type clean; console.error correctly classified as fail-loud) | N/A |
| 2 | reviewer-edge-hunter | Yes | findings | 4 | confirmed 0 blocking, 4 non-blocking (all server-unreachable / consistent-with-codebase) |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 3 | confirmed 0 blocking, 2 non-blocking, 1 dismissed (OTEL — story cosmetic-UI carve-out) |
| 4 | reviewer-test-analyzer | Yes | findings | 3 | confirmed 0 blocking, 3 non-blocking test-tightening; all 3 RT1 blockers verified test-locked |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings — assessed by Reviewer ([DOC]) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings — assessed by Reviewer ([TYPE]) |
| 7 | reviewer-security | Yes | clean | 2 (both low/informational — no new XSS, no info-leak) | confirmed 0 |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings — assessed by Reviewer ([SIMPLE]) |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings — assessed by Reviewer ([RULE]) |

**All received:** Yes (5 enabled returned, 4 with findings; 4 disabled pre-filled and assessed by Reviewer)
**Total findings:** 0 confirmed blocking, 1 dismissed (with rationale), 9 confirmed non-blocking (recorded as hardening follow-ups)

---
## Reviewer Assessment

**Verdict:** APPROVED

The rework fully resolved all three RT1 blocking findings, each now test-locked, with zero regressions (1847/1847 green, rework files lint+type clean, no new XSS/secrets). The re-review surfaced a deeper layer of defense-in-depth edges — but every one is **unreachable from the pydantic-validated server** (the only producer), and the originally-flagged, plausibly-reachable failures are fixed. Holding a correct, fully-green, player-facing render surface for server-impossible edges would be disproportionate and non-convergent. The residuals are recorded as non-blocking hardening follow-ups.

### RT1 blocking findings — resolution (all fixed + test-locked)
| RT1 finding | Fix | Test lock | Status |
|-------------|-----|-----------|--------|
| #1 [SILENT][RULE] dangling anchor silently dropped + false comment | `QuestsPanel` orphan filter widened to `!a.quest_id \|\| !loggedQuestIds.has(a.quest_id)`; comment corrected | `QuestsPanel.test.tsx` "surfaces a dangling-reference anchor…" (green) | RESOLVED |
| #2 [EDGE] `isEmptySpine` throws on malformed payload (AC2) | `useStateMirror` QUESTS branch validates `Array.isArray(quest_log) && Array.isArray(quest_anchors) && typeof active_stakes==='string'`, else `console.error`+`continue` (fail loud, leave `questsData` unchanged) | `useStateMirror.quests.test.ts` 2 malformed-degrade tests + valid-after-malformed (green) | RESOLVED |
| #3 [TEST] orphan branch zero coverage | orphan-null coverage test added | `QuestsPanel.test.tsx` "renders an orphan anchor whose quest_id is null" (green) | RESOLVED |

### Non-blocking findings (recorded for an optional hardening fast-follow — none reachable from today's server)

- [EDGE][SILENT] **Null/undefined payload envelope** (`useStateMirror.ts`): the new guard reads `p.quest_log` before null-checking `p`, so a null `msg.payload` would TypeError. **Consistent with the whole file** — every handler (RELATIONSHIPS `payload.entries`, LOCATION_DESCRIPTION, …) dereferences `msg.payload` and would crash identically; the server envelope always carries a payload. My guard is strictly MORE defensive than the sibling handlers (it validates content shape, which they don't). A one-line `if (!p || typeof p !== 'object') continue;` would close it. Non-blocking (codebase-wide assumption; server-unreachable).
- [EDGE][SILENT] **Nested-entry validation gap**: the boundary guard validates top-level shape, not per-entry. A `quest_log` entry missing `quest_id` (or anchor missing `anchor_id`) would pass → `undefined`/`null` React keys + `undefined` in `loggedQuestIds`. Server-unreachable: `quest_id`/`anchor_id` are **required** pydantic fields (no default). Follow-up: per-entry guards.
- [EDGE][SILENT] **Asymmetric back-reference anchor**: an anchor whose `quest_id` names a logged quest that does NOT claim it back (`q.anchor_id !== a.anchor_id`) is neither inline nor orphan-listed. Server-unreachable: the server **derives** `anchor.quest_id` from `quest.anchor_id`, so the forward/back refs are symmetric by construction. Follow-up: add `\|\| !renderedAnchorIds.has(a.anchor_id)` to the orphan filter to make the "never vanish" comment literally true.
- [EDGE] **Double-render on null-quest_id anchor claimed inline**: an anchor with `quest_id:null` that a quest claims via `anchor_id` renders both inline and in the orphan list. Pre-existing blind spot (the old `!a.quest_id` filter had it too); same `renderedAnchorIds` follow-up closes it.
- [TEST] **Tighten the dangling-anchor test** to `getByTestId("quests-orphan-anchor")` + `toHaveTextContent` (pins the render path, not just "text appears somewhere"); add a partial-array malformed variant (`quest_log` present, `quest_anchors` absent); assert `quest_anchors` survives in the valid-after-malformed test. (test-analyzer)
- [DOC] (comment_analyzer disabled — assessed by Reviewer) The corrected comment's absolute "must never vanish without a trace" is true for all **server-produced** shapes but not the asymmetric/double-render edges above; soften to "in all server-produced shapes" or close the edges. Non-blocking.

### Dismissed (with rationale)
- [SILENT] "console.error isn't loud enough — emit OTEL/watcher event" (silent-failure-hunter, medium) — **DISMISSED**, citing a contradicting AC: the story context explicitly scopes this panel as "a cosmetic/render surface [that] does not emit subsystem OTEL (per the 'Not needed for: cosmetic UI' carve-out in the UI CLAUDE.md)." Requiring OTEL here contradicts the story scope. `console.error` is the appropriate fail-loud channel for a client deserialization boundary.

### Rule Compliance (re-review — exhaustive, type_design + rule_checker disabled)
- **No Silent Fallbacks (CLAUDE.md `<critical>`):** ✓ for all server-reachable data — dangling anchors now surfaced; malformed top-level payloads rejected with a loud `console.error`. Residual server-unreachable silent edges recorded as non-blocking (cannot dismiss a rule-match → confirmed + downgraded with reachability rationale, not dismissed).
- **TS #1 type-safety / #2 generic / #3 enum / #6 React / #10 input-validation:** ✓ — `as unknown as` matches the file idiom; new code is `Array.isArray`/`typeof`/`Set`, no `as any`, no non-null `!`; stable React keys for server data; the boundary validation is the input-validation the prior review asked for.
- **OTEL (UI CLAUDE.md):** ✓ correctly omitted — cosmetic UI carve-out applies.
- **Wiring (every suite needs a wiring test):** ✓ unchanged from RT1 (GameBoard mount + reachability).

### Observations (5+)
1. [VERIFIED] RT1 finding #1 fixed — dangling anchor surfaced via `!loggedQuestIds.has(a.quest_id)`; no double-render for the normal owned-anchor case (excluded from orphans, rendered inline). Evidence: `QuestsPanel.tsx` orphan filter + edge-hunter Path A.
2. [VERIFIED] RT1 finding #2 fixed at the boundary — `useStateMirror` rejects malformed top-level shapes, fail-loud, leaves `questsData` unchanged; valid-after-malformed still lands. Evidence: 3 mirror tests green + edge-hunter Path F.
3. [VERIFIED] [SEC] No new XSS/info-leak — orphan render stays auto-escaped JSX text children; `console.error` logs only narrative quest text (no secrets/PII). Evidence: security specialist, both low/informational.
4. [LOW] [EDGE][SILENT] Residual server-unreachable edges (null envelope, nested-entry, asymmetric back-ref, double-render) — non-blocking hardening.
5. [LOW] [TEST] Dangling-anchor test could pin the testid; partial-array variant untested — non-blocking.
6. [VERIFIED] [SIMPLE] (simplifier disabled — assessed by Reviewer) The fixes are minimal — a `Set` + one filter clause + a 3-clause boundary guard. No over-engineering, no dead code.
7. [VERIFIED] [TYPE] (type_design disabled — assessed by Reviewer) No new type escapes; the `as unknown as` is the established mirror idiom; the guard narrows via runtime checks.

### Devil's Advocate
Try to break the approved code. The strongest attack is the one the edge-hunter found: feed the mirror a QUESTS message whose `payload` is literally `null`, and the guard I demanded in RT1 crashes on `p.quest_log` before it can reject anything — the fix to prevent a render crash contains a crash of its own. Damning? Only until you check the blast radius: every other handler in `useStateMirror` (RELATIONSHIPS reading `payload.entries`, LOCATION_DESCRIPTION, the overlay delta) dereferences `msg.payload` the same way and would die on the same null envelope. The server's message envelope always carries a payload object; a null envelope is a transport-layer corruption that takes down the whole mirror regardless of this story. So the QUESTS handler isn't a regression — it's strictly more defensive than its siblings, which validate nothing about payload content at all. The next attack: inconsistent quest/anchor graphs — an anchor that claims a quest the quest doesn't claim back, or a `quest_log` entry with a null `quest_id`. Real silent-drop and key-collision risks in the abstract — but the server *derives* `anchor.quest_id` from `quest.anchor_id` and types `quest_id`/`anchor_id` as required, so producing these requires the server to break its own model in two independent ways at once. A confused player? They see their objectives, stakes, and anchors exactly as the engine holds them; the panel's purpose — make the spine legible — is met for every shape the engine can emit. The honest verdict: the fixes resolved the reachable failures I rejected for, the panel is now strictly more robust than the sibling it mirrors, and the remaining counterexamples live in a region of the input space the server cannot reach. Shipping with a documented hardening follow-up is the proportionate call; a third rejection over server-impossible graphs would be perfectionism that never converges, at the cost of the playgroup's actual feature.

**Data flow traced:** server QUESTS snapshot → `useStateMirror` (validated, full-replace) → `state.questsData` → `App.tsx` → `GameBoard` (`renderWidgetContent`/`availableWidgets`/`rightGroupOrder` + `MobileTabView`) → `QuestsWidget` → `QuestsPanel` (empty-state-first, ARIA region, auto-escaped). Safe end-to-end for all server-producible payloads.

**Handoff:** To SM (Camina Drummer) for finish-story.