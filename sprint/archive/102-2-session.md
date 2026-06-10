---
story_id: "102-2"
jira_key: ""
epic: "102"
workflow: "tdd"
---
# Story 102-2: In-combat cast_spell via the dice path routes to the WN cast spine

## Story Details
- **ID:** 102-2
- **Jira Key:** (not tracked)
- **Workflow:** tdd
- **Stack Parent:** none
- **Branch:** feat/102-2-dice-path-spell-cast (created in sidequest-server and sidequest-ui)
- **Branch Strategy:** gitflow (feat/{STORY_ID}-{SLUG})

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-10T17:32:11Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-10T00:00:00Z | 2026-06-10T16:05:53Z | 16h 5m |
| red | 2026-06-10T16:05:53Z | 2026-06-10T16:29:03Z | 23m 10s |
| green | 2026-06-10T16:29:03Z | 2026-06-10T17:11:15Z | 42m 12s |
| review | 2026-06-10T17:11:15Z | 2026-06-10T17:22:37Z | 11m 22s |
| red | 2026-06-10T17:22:37Z | 2026-06-10T17:28:11Z | 5m 34s |
| green | 2026-06-10T17:28:11Z | 2026-06-10T17:30:30Z | 2m 19s |
| review | 2026-06-10T17:30:30Z | 2026-06-10T17:32:11Z | 1m 41s |
| finish | 2026-06-10T17:32:11Z | - | - |

## Sm Assessment

**Story selected:** 102-2 — In-combat `cast_spell` via the dice path routes to the WN cast spine. User-requested (`/pf-work 102-2`); p1 and the AC5b spellcast blocker for 90-3, so it correctly jumps the queue. Note: a stale `.session/90-3-session.md` (setup-only, story still `backlog` in YAML, no TEA work) was parked as `.session/90-3-session.md.parked`.

**Why it matters:** Today `_resolve_wwn_cast_for_beat` only runs on the narrator `apply_beat` path. A player using the dice path ("Work a Spell" beat via ConfrontationOverlay) gets a generic INT dice throw — no `wwn.spell.cast` span, no Effort/cast spend. That's exactly the "Claude winging it" failure mode the OTEL lie-detector exists to catch, and it's the crunch Sebastien/Jade miss. Mechanical resolution must also be legible in the player UI (spell selection, costs).

**Dependencies:** Epic 102 context committed in c01a10bc; story context exists at `sprint/context/context-story-102-2.md`. No blocking PRs (0 in-progress, 0 in-review at setup). Merge gate clear.

**Scope for TEA (RED):** Failing tests asserting:
1. `DiceThrowPayload` accepts a `spell_id` (protocol, pydantic v2) and the dice-path "Work a Spell" beat routes to the WN cast spine — not a generic INT throw.
2. The routed cast fires `wwn.spell.cast` OTEL spans and spends Effort/casts (parity with the `apply_beat` path).
3. UI: ConfrontationOverlay exposes spell selection and sends `spell_id` in the dice throw payload.
4. Wiring test: the new path is reachable from production dispatch (per CLAUDE.md "Every Test Suite Needs a Wiring Test") — no silent fallback to the generic throw when `spell_id` is present.

**Repos:** server, ui. Branches `feat/102-2-dice-path-spell-cast` created off `develop` in both (gitflow per repos.yaml).

## TEA Assessment

**Tests Required:** Yes
**Reason:** n/a (full TDD story — protocol change + dispatch routing + UI flow + wiring)

**Test Files:**
- `sidequest-server/tests/protocol/test_dice_throw_spell_id.py` — `DiceThrowPayload.spell_id` contract: optional, default None, round-trips, legacy keyless wire shape still validates (4 tests)
- `sidequest-server/tests/integration/test_dice_path_spell_cast_102_2.py` — dispatch routing on the REAL heavy_metal pack: cast spine fires (span + casts + HP), d20-face independence (WWN casting is automatic; the INT throw is not a to-hit gate), parity with `_resolve_wwn_cast_for_beat`, loud typed rejections (missing/unknown spell_id, spell_id on non-cast beat), refused-but-recorded economy refusal (casts=0), strike-path regression pin (8 tests)
- `sidequest-server/tests/server/test_dice_throw_spell_cast_wiring_102_2.py` — AC4 wiring: WebSocket-level `handle_message(DICE_THROW + spell_id)` reaches the spine (handler→dispatch→spine, no direct call); wire validation keeps the field (2 tests)
- `sidequest-server/tests/server/test_confrontation_payload_spellcasting_102_2.py` — AC3 data seam: CONFRONTATION payload projects `spellcasting {casts_remaining, casts_per_day, prepared}` for a WWN caster; None for non-casters (2 tests)
- `sidequest-ui/src/__tests__/spell-picker-cast-beat-102-2.test.tsx` — overlay picker: cast tile defers commit and opens `data-testid="spell-picker"` (options addressable by `data-spell-id`, economy on `data-casts-remaining` + visible text), selection commits `onBeatSelect(beatId, spellId)`, strike unchanged, missing-economy click never silently commits (5 tests)
- `sidequest-ui/src/__tests__/cast-spell-throw-wiring-102-2.test.tsx` — App wiring: `spell_id` rides the outbound DICE_THROW alongside typed `player_action` (Zork guardrail), non-cast throws keep the keyless pre-102-2 shape, latched spell consumed atomically per commit (3 tests)

**Tests Written:** 24 tests covering 4 ACs (+ guardrail edges)
**Status:** RED (verified by testing-runner: 18 failing on missing implementation, 5 regression pins passing, 1 leak-guard passing-by-design; zero collection/import/fixture errors)

Commits: server `7d9ad37f`, ui `7d49ea6` (both on `feat/102-2-dice-path-spell-cast`).

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| py #1 silent fallbacks / swallowed errors | `test_cast_beat_without_spell_id_is_loud_typed_rejection`, `test_cast_with_no_casts_remaining_is_refused_not_generic` (refused-but-RECORDED, never a silent no-op) | failing (RED) |
| py #11 input validation at boundaries | `test_cast_beat_with_unknown_spell_id_is_loud_typed_rejection`, `test_spell_id_on_non_cast_beat_is_loud_typed_rejection`, `test_ws_dice_throw_spell_id_survives_wire_validation` | failing (RED) |
| py #6 / ts #8 test quality | Self-check pass below; every `# type: ignore` carries a specific code | n/a |
| ts #4 null/undefined (absent-key vs undefined) | wiring regression + leak tests pin `"spell_id" in payload === false` (key truly absent, not `undefined`-serialized) | 1 failing / 2 pins |
| CLAUDE.md wiring-test mandate | `test_ws_dice_throw_with_spell_id_reaches_cast_spine` (server, handler-level) + `cast-spell-throw-wiring-102-2` (UI, App wire trap) | failing (RED) |
| OTEL observability principle | every cast-path test asserts `wwn.spell.cast` span presence/absence/attrs, not just state | failing (RED) |

**Rules checked:** 5 of 5 applicable lang-review rule families have test coverage
**Self-check:** 0 vacuous tests found (every test asserts specific values: exact casts deltas, exact HP arithmetic, exact span attrs, exact call args, exact wire keys)

**Handoff:** To Dev (Naomi Nagata) for GREEN. Implementation seams, in dependency order: (1) `spell_id: str | None = None` on `DiceThrowPayload` (`protocol/dice.py:188`) + the TS mirror in `src/types/payloads.ts`; (2) dispatch routing in `dispatch_dice_throw` (`server/dispatch/dice.py`) — extract/share the spine `_resolve_wwn_cast_for_beat` uses (`narration_apply.py:261`), do NOT duplicate it (epic 102 "Reuse-first"); (3) `spellcasting` block in `build_confrontation_payload` (`dispatch/confrontation.py` — `effective_spellcasting` is already derived there); (4) overlay picker + App latch (`pendingSpellIdRef` beside `pendingBeatIdRef`, App.tsx:1740 area). The server tests carry `# type: ignore[arg-type]/[call-arg]` on payload constructions that become unnecessary once the field exists — remove them in GREEN.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed (server, commit `a9358b0c`, pushed):**
- `sidequest/protocol/dice.py` — `DiceThrowPayload.spell_id: str | None = None` (wire-compat: default None)
- `sidequest/protocol/messages.py` — `ConfrontationPayload.spellcasting: dict | None = None` (model is `extra="forbid"`; the payload-dict key needed the field at all four `ConfrontationPayload(**dict)` validation sites)
- `sidequest/server/dispatch/dice.py` — pre-mutation validation (missing spell_id on a wwn cast / spell_id on non-cast / spell_id unknown to the world-first catalog → `DiceDispatchError`), then routes the committed cast through `_resolve_wwn_cast_for_beat` (function-level import; narration_apply is heavy) after `apply_beat` + the strike downed seam — one cast implementation, two entry points; not gated on `resolved.outcome`
- `sidequest/server/dispatch/confrontation.py` — `effective_spellcasting` hoisted above the recipient branch; payload emits the `spellcasting` block (casts_remaining/casts_per_day/prepared) or None
- `tests/integration/test_dice_throw_spell_cast_wiring_102_2.py` — moved from tests/server/ (autouse `_fixture_pack_search_paths` there repoints the loader at frozen fixture packs, so the REAL heavy_metal pack can't load); monster-manual pregen stubbed to not-loaded (downstream of the seam under test, fail-louds on the factory's `world_slug=""`)

**Files Changed (ui, commit `3d7f516`, pushed):**
- `src/types/payloads.ts` — `DiceThrowPayload.spell_id?: string`
- `src/components/ConfrontationOverlay.tsx` — `ConfrontationSpellcasting` type + `ConfrontationData.spellcasting`; cast tile defers commit behind `SpellPicker` (`data-testid="spell-picker"`, per-option `data-spell-id`, `data-casts-remaining` + "casts 2/2" text, humanized id labels); missing economy → loud console.warn refusal, never a bare commit; `onBeatSelect(beatId, spellId?)`
- `src/components/GameBoard/GameBoard.tsx` — threads `spellId` alongside the InputBar draft
- `src/App.tsx` — `pendingSpellIdRef` latched beside `pendingBeatIdRef`, consumed atomically in `handleDiceThrow`, `spell_id` attached iff a cast commit; reset on the unbound-refusal path
- `src/__tests__/confrontation-wiring.test.tsx` — two source-regex pins extended to the three-arg signature (behavior unchanged; the pins hardcode signatures)
- `src/__tests__/cast-spell-throw-wiring-102-2.test.tsx` — removed unused React import (tsc TS6133)

**Tests:** 24/24 story tests passing (16 server + 8 UI; verified by testing-runner runs `102-2-dev-green-server-4` and `102-2-dev-green-ui-2`). Full server suite: only pre-existing failures (namegen corpora audit ×4, scene_harness orphan-actors policy, dogfight swn_test_pack bestiary, api-contract doc path — all present on develop). Full UI suite: 2036 passing; `lobby-start-ws-open` timeout and 5 `BeatEffect` tsc errors in `ConfrontationOverlay.beatimpact.test.tsx` confirmed pre-existing via stash-bisect. Ruff clean on all changed server files; eslint clean (one pre-existing warning).

**Branch:** `feat/102-2-dice-path-spell-cast` (pushed in both repos)

**Process note:** the first GREEN testing-runner went rogue and edited the shared `test_genre` fixture (converted to wwn + new bestiary/classes/spells files — 90 test files depend on it) and `protocol/messages.py`. Fixture changes reverted; the messages.py field was a genuinely required change (kept, reviewed). All subsequent runner prompts carried an explicit READ-ONLY constraint and results were diff-checked.

**Handoff:** To Amos (TEA) for verify (simplify + quality-pass).

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): the UI has no WWN spellcasting projection anywhere — `src/types/magic.ts` only models the B/X `MagicState` (prepared_spells per level); `casts_remaining` never reaches the client. Confirms the story-context assumption; the CONFRONTATION `spellcasting` block pinned in the new server test is the in-scope reactive projection. Affects `sidequest-ui/src/types/` + `sidequest-server/sidequest/server/dispatch/confrontation.py` (emit the already-derived state). *Found by TEA during test design.*
- **Question** (non-blocking): `build_confrontation_payload` has no pack/catalog parameter, so the spellcasting projection can only carry prepared spell **ids**, not display names — the picker will have to humanize ids (`wracking_bolt` → "Wracking Bolt") until someone threads the catalog through. If Dev or a follow-up story wants real names on the wire, that is a payload-builder signature change. Affects `sidequest-server/sidequest/server/dispatch/confrontation.py` (optional catalog/pack param). *Found by TEA during test design.*
- **Improvement** (non-blocking): the apply_beat spine treats a missing `spell_id` as a watcher-warning no-op (`wwn.cast_spell_no_spell_id`) while the dice path now pins a loud `DiceDispatchError` for the same condition — defensible (narrator omission vs malformed client request) but the asymmetry is worth a doc line in the spine docstring when Dev extracts it. Affects `sidequest-server/sidequest/server/narration_apply.py:261`. *Found by TEA during test design.*
- **Gap** (non-blocking): epic-102 context's "Effort/System-Strain spend" phrasing — `resolve_spellcast`'s High Magic economy is prepared/casts_remaining (+ strain inside the module); there is no separate Effort ledger touch on this path today, so the RED suite pins `casts_remaining` as the observable spend. If 102-4/102-6 add an Effort-visible surface, parity tests should grow an attribute then. Affects `sidequest-server/sidequest/game/ruleset/wwn.py` (documentation of the cast economy). *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (non-blocking): pre-existing red on develop, confirmed by stash-bisect (2026-06-10): `npm run build` fails on 5 `BeatEffect` type errors in `src/components/__tests__/ConfrontationOverlay.beatimpact.test.tsx` (`effect: string` vs the union), and `src/__tests__/lobby-start-ws-open.test.tsx` "Leave + Start" times out even in isolation. Both predate 102-2 and block a clean `just client-build` gate. Affects `sidequest-ui/src/components/__tests__/ConfrontationOverlay.beatimpact.test.tsx` (annotate fixtures with the `BeatEffect` literal type) and `sidequest-ui/src/__tests__/lobby-start-ws-open.test.tsx` (timeout investigation). *Found by Dev during implementation.*
- **Improvement** (non-blocking): tests/server's autouse `_fixture_pack_search_paths` makes `session_handler_factory(genre=...)` silently load FROZEN fixture packs — a test author asking for "heavy_metal" gets a pack with different beats and no error. A loud marker (e.g. fixture packs stamped with a `fixture: true` field the factory logs) would have saved a debugging round. Affects `sidequest-server/tests/server/conftest.py` (discoverability of the repoint). *Found by Dev during implementation.*
- **Question** (non-blocking): the dice-path cast currently runs AFTER `apply_beat`, so the cast beat still applies its dial delta (inert under hp_depletion, but real on a dial-threshold wwn pack) on the d20 tier before the spine resolves the actual cast. Parity holds for heavy_metal (hp_depletion); a future dial-based WN pack should decide whether a cast beat moves the dial at all. Affects `sidequest-server/sidequest/server/dispatch/dice.py` (cast-vs-dial semantics note). *Found by Dev during implementation.*

### Reviewer (code review)
- **Gap** (blocking): a killing dice-path cast leaves the dead opponent free to take its reprisal swing — `_resolve_opponent_reprisal` is gated on `apply_result.resolved` (stale: the cast resolves the encounter in the spine via `check_hp_depletion`, AFTER `apply_beat`), and neither the reprisal body nor `_opposite_side_first_actor` checks `encounter.resolved` or opponent HP (only `withdrawn`, which the kill path never sets). ADR-139 win-condition liveness violation, reachable in normal play. Affects `sidequest-server/sidequest/server/dispatch/dice.py` (reprisal gate must read authoritative `encounter.resolved`). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): a wwn `cast_spell` beat on an `opposed_check` ConfrontationDef would pass the new validation and then silently skip the cast spine (the spine call lives in the non-opposed else branch) — no current content ships that combination, but it is a latent silent-fallback shape; a loud guard would close it. Affects `sidequest-server/sidequest/server/dispatch/dice.py` (opposed_pending × is_wwn_cast). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): the UI repo still carries source-grep wiring tests (`confrontation-wiring.test.tsx` regex-reads App.tsx/GameBoard.tsx source) — the server repo bans the pattern; a follow-up could migrate these to behavior assertions like `cast-spell-throw-wiring-102-2.test.tsx`. Affects `sidequest-ui/src/__tests__/confrontation-wiring.test.tsx` (pattern migration). *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Malformed-vs-economy rejection split pinned where the spec left a choice open**
  - Spec source: context-story-102-2.md, AC1 edge + Technical Guardrails (validation)
  - Spec text: "spell_id absent on a cast beat → loud, typed rejection (or a defined fallback the story explicitly chooses — no silent generic-INT resolution remains possible)" / "reject spell_id the caster doesn't have prepared / lacks casts for — loudly, with a typed error the UI can render"
  - Implementation: Tests pin TWO distinct behaviors — malformed requests (missing spell_id, spell_id unknown to the catalog, spell_id on a non-cast beat) raise `DiceDispatchError`; the valid-but-refused economy case (casts_remaining=0) mirrors the spine's refused-but-recorded semantics (`wwn.spell.cast refused=True`, no raise, no state change)
  - Rationale: the UI gate already filters cast_spell at 0 casts, so a 0-cast commit is a stale-overlay race, not a protocol violation — raising would crash a legitimate race while a refused span keeps AC2 parity with apply_beat refusals; malformed fields, by contrast, are client bugs and No Silent Fallbacks demands the typed error
  - Severity: minor
  - Forward impact: Dev must implement both semantics; Reviewer should check the asymmetry is documented at the seam
  - → ✓ ACCEPTED by Reviewer: the split matches the dispatch error idiom and the spine's refused-but-recorded contract; asymmetry documentation flagged separately as a LOW doc finding.
- **Cast outcome pinned as independent of the d20 face**
  - Spec source: context-story-102-2.md AC2 (parity) + story title ("instead of resolving as a generic INT dice throw")
  - Spec text: "The same spell cast via the narrator apply_beat path and via the dice path produce equivalent mechanical outcomes" (the apply_beat path never consults a player d20)
  - Implementation: `test_cast_outcome_is_independent_of_the_d20_face` asserts face=20 and face=1 produce identical cast results
  - Rationale: WWN SRD casting is automatic (the defender saves); gating the cast on the INT throw would silently re-introduce a generic-INT resolution wearing a robe and break parity with the reference path
  - Severity: minor
  - Forward impact: the UI still runs the dice animation for the cast beat; what the throw MEANS for a cast (pure theater vs future to-hit variants) may need a UX note in 102-4's turn model
  - → ✓ ACCEPTED by Reviewer: WWN SRD-faithful and required by AC2 parity — though the test CONSTRUCTION proves less than it claims (see [TEST] findings; the pin itself is sound doctrine).
- **Picker contract pinned via DOM data attributes**
  - Spec source: context-story-102-2.md AC3
  - Spec text: "Clicking 'Work a Spell' surfaces the prepared-spell picker; selection populates spell_id; overlay render with casts_remaining visible"
  - Implementation: tests pin `data-testid="spell-picker"`, per-option `data-spell-id`, and `data-casts-remaining` + the number in visible text — not specific markup, copy, or styling
  - Rationale: a RED contract needs machine-checkable hooks Dev implements TO; data attributes pin behavior while leaving presentation free (precedent: BeatImpactPanel's `data-effect` pins in 73-10)
  - Severity: minor
  - Forward impact: the attributes become part of the overlay's test surface; UX polish can restyle freely as long as the hooks stay
  - → ✓ ACCEPTED by Reviewer: data-attribute pins are the established house pattern (73-10 precedent cited correctly).
- **Spellcasting projection carries spell ids, not display names**
  - Spec source: context-story-102-2.md AC3 + Assumptions ("prepared-spell list... via existing state-mirror projections; if not, exposing it is in-scope as a reactive projection")
  - Spec text: "the prepared-spell picker" / "casts_remaining visible" (names not explicitly required)
  - Implementation: the CONFRONTATION `spellcasting` block is pinned as `{casts_remaining, casts_per_day, prepared: [spell-id strings]}` — a pure projection of the already-derived `SpellcastingState`
  - Rationale: `build_confrontation_payload` has no pack/catalog parameter, so names would force a signature change this story doesn't need; ids humanize acceptably for v1 (logged as a Delivery Finding for follow-up)
  - Severity: minor
  - Forward impact: picker labels are id-derived until a catalog thread-through lands; 102-3/102-5 may want the names
  - → ✓ ACCEPTED by Reviewer: avoiding a payload-builder signature change is the right scope call; the names gap is properly logged as a Delivery Finding.

### Dev (implementation)
- **Wiring test relocated + monster-manual pregen stubbed**
  - Spec source: TEA RED suite, `test_dice_throw_spell_cast_wiring_102_2.py` (AC4)
  - Spec text: test as written lived in tests/server/ and drove `session_handler_factory(genre="heavy_metal")` expecting the real pack
  - Implementation: moved the file to tests/integration/ (tests/server's autouse `_fixture_pack_search_paths` repoints the loader at frozen fixture packs, so the real heavy_metal pack is unreachable there) and stubbed `monster_manual_inject.ensure_loaded` → None (on real wwn packs the narration turn fail-louds on the factory's `world_slug=""` missing world bestiary — downstream of the handler→dispatch→spine seam under test)
  - Rationale: preserves the test's intent (wire-level chain proof on the real pack) exactly; assertions unchanged — only the harness assumptions were corrected
  - Severity: minor
  - Forward impact: none — the file documents both constraints in its docstring
  - → ✓ ACCEPTED by Reviewer: harness-only correction, assertions byte-identical; the docstring records both constraints so the next author doesn't repeat the round-trip.
- **Source-regex pins in confrontation-wiring.test.tsx extended**
  - Spec source: existing UI suite (pre-102-2), `confrontation-wiring.test.tsx`
  - Spec text: pins `/onBeatSelect\?\.\(beatId,\s*draft\)/` and the two-arg `handleBeatSelect` signature
  - Implementation: regexes extended to the three-arg signature (`draft, spellId` / `playerAction?, spellId?`)
  - Rationale: the pins hardcode implementation shape, not behavior; 102-2 legitimately changes the signature and the pins must follow (behavioral coverage of the same chain is provided by the new cast-spell-throw-wiring suite)
  - Severity: minor
  - Forward impact: none
  - → ✓ ACCEPTED by Reviewer: extending the legacy pin was correct (deleting pre-existing tests is out of story scope); the behavioral chain is independently proven by cast-spell-throw-wiring-102-2. The source-grep pattern itself is pre-existing UI debt — logged as a Delivery Finding, not this story's burden.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (45/45 tests green, ruff clean, 1 pre-existing eslint warning) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 7 (2 medium, 5 low) | confirmed 2, dismissed 1, deferred 4 |
| 5 | reviewer-comment-analyzer | Yes | findings | 4 (1 high-conf, 2 medium, 1 low) | confirmed 2, deferred 2 |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 2 violations across 28 rules / 94 instances | confirmed 2, dismissed 0, deferred 0 |

**All received:** Yes (4 ran, 5 disabled via settings)
**Total findings:** 7 confirmed (incl. 1 Reviewer-original HIGH), 1 dismissed (with rationale), 6 deferred

Dismissed: test-analyzer's "remove the handleBeatSelect source-grep pin entirely" — the source-grep pattern is pre-existing UI-repo debt; this diff correctly EXTENDED the pin to keep it green rather than deleting an inherited test, and the behavioral chain is independently proven by `cast-spell-throw-wiring-102-2.test.tsx`. Migration logged as a Delivery Finding instead.
Deferred (non-blocking polish, folded into the fix list as LOW): monster-manual-stub ordering comment, global randint pin scope note, data-attribute coupling note, toContain("2") weak assertion, overlay onBeatSelect jsdoc layering note, dispatch docstring under-description.

### Rule Compliance

Rule-checker swept 28 numbered checks (13 py + 13 ts + CLAUDE.md/SOUL.md) across 94 instances in the diff; my own pass cross-checked the load-bearing ones:

| Rule | Instances checked | Verdict |
|------|-------------------|---------|
| py #1 silent exceptions | catalog KeyError re-raised as DiceDispatchError `from exc` (dice.py:377); no bare except | compliant |
| py #2 mutable defaults | both new pydantic fields default None; no mutable defaults | compliant |
| py #3 boundary annotations | spell_id `str \| None`, spellcasting `dict[str, Any] \| None` (Any commented) | compliant |
| py #11 input validation | client `spell_id` validated against resolved catalog BEFORE any mutation; non-cast/missing/unknown all raise typed errors | compliant |
| ts #1 type escapes | **VIOLATION** `as { payload: never }` (cast-spell-throw-wiring:223) — `never` misrepresents intent; should be `unknown` | LOW finding |
| ts #4 null/undefined | `spellId ?? null`, `data?.spellcasting ?? null` — correct `??` usage throughout | compliant |
| ts #6 React/JSX | all three new useCallbacks have correct deps; picker keys on stable spellId | compliant |
| ts #8 test quality | **VIOLATION** `mock.calls[0] as [string, string]` (spell-picker:144) — real signature is `[string, string \| undefined]` | LOW finding |
| CLAUDE.md No Silent Fallbacks | four loud raises on the dispatch boundary; overlay refuses bare cast commits | compliant (one LATENT gap: opposed_check × wwn cast — MEDIUM below) |
| CLAUDE.md wiring test | WS-level handler test drives handle_message → dispatch → spine | compliant |
| Server no-source-grep | server tests are span/behavior-driven; the UI regex pins are pre-existing debt, extended not added | compliant |
| OTEL principle | `wwn.spell.cast` fires on every cast attempt incl. refusals; tests assert spans, not just state | compliant |
| SOUL.md Zork Problem | `player_action` rides the same DICE_THROW as `spell_id` (App.tsx:1844-1848); test pins both keys on one frame | compliant |

Per the no-dismissal rule: both ts violations match stated checklist rules and are CONFIRMED (severity LOW — test-file type hygiene, runtime assertions still catch regressions).

### Devil's Advocate

Assume this code is broken and the tests are lying. Where does it bleed? Start with the thing the tests never asserted: the OPPONENT'S turn. Every dice-path cast test pins the opponent surviving or checks only opponent-side state — none asks what happens to the PLAYER after a killing cast. Trace it: Vesska's second wracking_bolt drops the Furnace Thrall to 0. The spine applies damage, runs the downed seam, and `check_hp_depletion` stamps `encounter.resolved = True`. Then control returns to `dispatch_dice_throw`, which computes `encounter_resolved = apply_result.resolved` — the value from `apply_beat`, which ran BEFORE the cast with `damage_channel: none` and therefore resolved nothing. False. The reprisal gate passes. `_opposite_side_first_actor` filters on `withdrawn` only — the corpse is not withdrawn, so it is returned, rolls d20 + 1d8, and lands its blade in the winner. If that drops Vesska to 0, the reprisal's own `check_hp_depletion` no-ops (`if enc.resolved: return`) — so the player sits at 0 HP in a WON fight with no lethality processing at all. That is a confirmed HIGH, not a hypothetical: two casts kill the 10-HP mook in ordinary play. The strike path never had this bug because a killing strike resolves INSIDE apply_beat. What else? A confused content author ships a wwn `opposed_check` confrontation with a cast_spell beat: validation accepts the spell_id, the opposed branch skips the spine, and the cast silently evaporates — the precise illusionism this epic exists to kill (MEDIUM, latent). A malicious client sends `spell_id: ""` — not None, so it reaches `catalog.get("")` → KeyError → loud typed rejection; fine. Multiplayer leakage? The spellcasting block is derived per-recipient in the per-PC frame path, so one caster's economy doesn't broadcast to the table. The picker with `prepared: []`? Refused loudly, no commit. The devil found one kill and one latent ghost — both in the severity table.

## Reviewer Assessment

**Verdict:** REJECTED

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] | Dead opponent takes its reprisal after a killing dice-path cast — reprisal gate reads stale `apply_result.resolved`; the cast resolves via the spine's `check_hp_depletion` AFTER apply_beat. ADR-139 win-condition liveness violation; player can be mauled (to 0 HP, unprocessed) in a fight already won. Strike path unaffected (resolves inside apply_beat). | `sidequest-server/sidequest/server/dispatch/dice.py:903` (`encounter_resolved = apply_result.resolved`) + reprisal gate `:921` | RED test: killing dice-path cast ⇒ encounter resolved, NO `encounter.opponent_attack_resolved` span, player HP untouched. Fix: derive the gate from authoritative state — `encounter_resolved = apply_result.resolved or encounter.resolved` (after the cast-spine block) so the outcome/log/return also report the cast kill truthfully. |
| [MEDIUM] | Latent silent spine-skip: wwn cast_spell on an `opposed_check` cdef passes validation then never reaches the cast spine (spine call is in the non-opposed else branch) — no span, no spend, silent. No current content ships the combo; the shape still violates No Silent Fallbacks. | `sidequest-server/sidequest/server/dispatch/dice.py` (opposed_pending branch vs `is_wwn_cast`) | Loud `DiceDispatchError` when `is_wwn_cast and cdef.resolution_mode == ResolutionMode.opposed_check`, with a test pinning it. |
| [MEDIUM] [TEST] | Parity test compares unequal BeatSelections: reference path defaults `outcome=Success` while dice path passes `resolved.outcome` (Fail at face=1). Parity holds only because the spine ignores `sel.outcome` today — the test stops proving parity the day the spine reads it. | `sidequest-server/tests/integration/test_dice_path_spell_cast_102_2.py` (parity test) | Pass the matching outcome on the reference BeatSelection (or assert outcome-tier equality across the two spans). |
| [MEDIUM] [TEST] | Face-independence test can't distinguish "cast ignores d20" from "damage pinned to 1" — both faces run under the same rng pin against fresh snapshots with identical arithmetic. | same file (face-independence test) | Assert the full span attr set (refused/save_made/damage) is identical across face=1 and face=20, and/or assert outcome-tier differs while cast result doesn't. |
| [LOW] [RULE] | `as { payload: never }` type escape — `never` misrepresents intent (ts checklist #1). | `sidequest-ui/src/__tests__/cast-spell-throw-wiring-102-2.test.tsx:223` | Use `{ payload: unknown }` (or a typed message union) and narrow. |
| [LOW] [RULE] | `mock.calls[0] as [string, string]` — mock tuple type doesn't match the `(beatId, spellId?)` signature (ts checklist #8). | `sidequest-ui/src/__tests__/spell-picker-cast-beat-102-2.test.tsx:144` | Cast to `[string, string \| undefined]`. |
| [LOW] [DOC] | `_resolve_wwn_cast_for_beat` docstring still describes one caller ("WWN Content Plan 3 Task 7"); it now has two entry points — the diff's own "one implementation, two entry points" invariant is invisible at the function. Sibling: `dispatch_dice_throw` docstring's "beat apply only runs after stat validation" under-describes the new cast-validation gate. | `sidequest-server/sidequest/server/narration_apply.py:261` / `sidequest-server/sidequest/server/dispatch/dice.py:273` | One docstring line each. |

**Observations (verified-good):**
- [VERIFIED] Wire compat both directions — `spell_id`/`spellcasting` optional-with-None (protocol/dice.py:201, messages.py:824, both `extra="forbid"`-safe); legacy keyless frame validates (test_dice_throw_spell_id.py); non-cast DICE_THROW omits the key (`App.tsx:1848` conditional spread; pinned by the wiring regression test). Complies with py #2/#3, ts #4.
- [VERIFIED] Input validation precedes ALL mutation — the dispatch guard block (dice.py:340-380) runs before `emit_ability_invocation_unrouted`, stat canonicalization, and apply_beat; rejection tests assert zero state drift. Complies with py #11 + No Silent Fallbacks.
- [VERIFIED] Zork guardrail wired, not just claimed — `player_action` and `spell_id` ride the same frame (App.tsx:1844-1848), asserted together on one outbound message in the UI wiring test. Complies with SOUL.md.
- [VERIFIED] [SILENT]-domain self-check (subagent disabled): the four new raise sites are typed and contextual; the overlay's missing-economy branch warns and refuses rather than silently committing; the one silent shape found is the MEDIUM opposed_check gap above.
- [VERIFIED] [TYPE]-domain self-check (subagent disabled): `ConfrontationSpellcasting` is a proper interface; no `as any` in production code; the two test-file escapes are the LOW [RULE] findings.
- [EDGE]/[SEC]/[SIMPLE] domains (subagents disabled): covered by my own trace (empty-string spell_id → loud KeyError rejection; per-recipient spellcasting derivation → no MP economy leakage; no dead code added — the catalog double-resolve is accepted reuse, not complexity).
- [TEST] Confirmed: parity-outcome divergence + face-independence weakness (table above). [DOC] Confirmed: two stale docstrings (table above). [RULE] Confirmed: two ts escapes (table above).

**Data flow traced:** picker click → `onBeatSelect("cast_spell", spellId)` → GameBoard inserts InputBar draft → App latches `pendingSpellIdRef` → physics settle → DICE_THROW `{beat_id, player_action, spell_id}` → handler `_handle_dice_throw` → `dispatch_dice_throw` validation (catalog-checked) → apply_beat → cast spine → `wwn.spell.cast` + casts decrement + HP channel + downed seam + `check_hp_depletion`. Safe until the post-kill reprisal gate — the HIGH.
**Pattern observed:** good — pre-mutation validation block mirrors the existing net_run fail-loud idiom (dice.py:340 vs :365 pre-existing); bad — resolution state forked between `apply_result.resolved` and `encounter.resolved` with the gate reading the stale fork (dice.py:903).
**Error handling:** typed `DiceDispatchError` at every malformed-commit branch, surfaced to the UI by the existing handler error path; economy refusals recorded on-span per spine contract.

**Handoff:** Back through TEA (Amos) — the HIGH and both MEDIUMs are testable (missing edge cases / logic gap): RED the killing-cast-no-reprisal test + opposed_check guard test + parity/face-independence strengthening, then Dev fixes. LOW items ride along in the same rework.

## TEA Rework Assessment (round 2)

**Trigger:** Reviewer REJECTED — 1 HIGH + 2 MEDIUM testable findings (+2 LOW ts rule violations in TEA-owned test files).

**Tests Written/Changed:**
- `tests/integration/test_dice_path_spell_cast_102_2.py` (server commit `7ccaceea`, pushed):
  - NEW `test_killing_cast_resolves_encounter_and_suppresses_reprisal` — [HIGH] RED: fails today on the `encounter.opponent_attack_resolved` span firing after a killing cast (the corpse swings). Span absence is the primary assertion — it fires on every reprisal attempt, hit or miss, so a player-HP check alone could pass vacuously when the pinned reprisal d20 misses. rng pin split by die size (`a if b == 20 else b`): saves roll 1, damage dice roll max — level-2 wracking_bolt = 2d6 = 12 overkills the 10-HP opponent through a failed save.
  - NEW `test_cast_on_opposed_check_confrontation_rejects_loudly` — [MEDIUM] RED: fails today on DID-NOT-RAISE (validation passes, opposed branch silently skips the spine). Mutates the loaded cdef via `monkeypatch.setattr` (auto-restored — the loaded pack may be cached).
  - STRENGTHENED `test_cast_parity_with_apply_beat_path` — reference BeatSelection now carries the same outcome tier the dice path derives (face=2 → Fail, avoiding nat-1 specials); the two invocations are equal on every field.
  - STRENGTHENED `test_cast_outcome_is_independent_of_the_d20_face` — both faces run, full span-attr sets compared; a to-hit gate would now diverge the attr sets instead of slipping past a pinned arithmetic check.
- UI (commit `57b0bc2`, pushed): `sentThrows` typed via `SentThrow` (was `payload: never`), spell-picker mock tuple cast matches the real `(beatId, spellId?)` signature — the two [RULE] LOWs.

**Status:** RED verified by testing-runner (`102-2-tea-red-2`): exactly the 2 new tests failing, each on the intended assertion; all 16 other server tests + 8 UI tests green.

**Not covered here (Dev's lane in GREEN):** the two [DOC] LOWs (docstrings on `_resolve_wwn_cast_for_beat` + `dispatch_dice_throw`).

**Handoff:** To Dev (Naomi) for GREEN — fix sketch per Reviewer: derive the reprisal gate from authoritative state (`encounter_resolved = apply_result.resolved or encounter.resolved` after the cast-spine block) and add a loud `DiceDispatchError` for `is_wwn_cast` × `opposed_check`.

### TEA (test design — rework round 2)
- No new deviations from spec; the two new tests implement the Reviewer's severity table verbatim, and the two strengthened tests implement her suggested constructions (matching outcome tier; cross-run span-attr comparison).
  - → ✓ ACCEPTED by Reviewer (round 2): verified against the severity table line-by-line; the killing-cast test's span-absence primary assertion is exactly the non-vacuous construction required.

## Dev Assessment (rework round 2)

**Implementation Complete:** Yes

**Files Changed (server, commit `3be24467`, pushed):**
- `sidequest/server/dispatch/dice.py` — [HIGH fix] reprisal gate now derives from authoritative state: `encounter_resolved = apply_result.resolved or encounter.resolved` (a killing cast resolves in the spine AFTER apply_beat; strikes resolve inside apply_beat, so the widening is strict). [MEDIUM fix] loud `DiceDispatchError` for a wwn cast_spell commit on an `opposed_check` cdef — the cast spine has no opposed arm and silently skipping it was the latent fallback shape. [DOC] `dispatch_dice_throw` docstring now names the full pre-apply validation gate.
- `sidequest/server/narration_apply.py` — [DOC] `_resolve_wwn_cast_for_beat` docstring documents the two entry points (apply_beat sidecar / dice-path payload) and the narrator-vs-dice missing-spell_id asymmetry the Reviewer asked to see at the seam.

**Tests:** 52/52 passing (testing-runner `102-2-dev-green-2`): both formerly-RED round-2 tests now green, plus regression neighbors — `test_opponent_reprisal_e2e` (9/9, the critical suite for the gate change), heavy_metal combat, space_opera hp e2e, dice-throw wiring, cast dispatch. Ruff clean.

**Branch:** `feat/102-2-dice-path-spell-cast` (pushed)

**Handoff:** Back to Chrisjen (Reviewer) for re-review.

### Dev (implementation — rework round 2)
- No deviations from the Reviewer's fix specification; both fixes implement the severity-table "Fix Required" column verbatim.
  - → ✓ ACCEPTED by Reviewer (round 2): diff-verified; the `or encounter.resolved` widening is provably strict (pre-resolved encounters are rejected at dispatch entry, so the gate can only observe this dispatch's own resolution).

## Reviewer Assessment (round 2)

**Verdict:** APPROVED

**Scope:** the rework delta — server `7ccaceea` (TEA round-2 tests) + `3be24467` (Dev fixes), ui `57b0bc2` (test type fixes) — re-read line-by-line against the round-1 severity table. The round-1 Subagent Results table and full battery stand for the feature diff; round 2 was verified by direct diff audit plus the read-only testing-runner evidence below (proportionate to a 4-file, ~200-line corrective delta).

**Round-1 findings disposition:**
| Round-1 finding | Disposition |
|---|---|
| [HIGH] dead-opponent reprisal after killing cast | FIXED — `encounter_resolved = apply_result.resolved or encounter.resolved` (dice.py); RED test `test_killing_cast_resolves_encounter_and_suppresses_reprisal` now green, asserting span ABSENCE (non-vacuous: `encounter.opponent_attack_resolved` fires on every attempt, hit or miss) |
| [MEDIUM] silent spine-skip on opposed_check wwn cast | FIXED — loud `DiceDispatchError` inside the pre-mutation validation block; pinned by `test_cast_on_opposed_check_confrontation_rejects_loudly` (cdef mutated via auto-restoring monkeypatch — cache-safe) |
| [MEDIUM][TEST] parity outcome divergence | FIXED — reference BeatSelection carries the dice path's tier (face=2 → Fail, no nat-1 special) |
| [MEDIUM][TEST] face-independence weakness | FIXED — both faces run; full span-attr sets compared cross-run; a to-hit gate would now diverge the sets |
| [LOW][RULE] `payload: never` / `[string, string]` casts | FIXED — typed `SentThrow` shape; tuple matches `(beatId, spellId?)` |
| [LOW][DOC] stale docstrings ×2 | FIXED — `dispatch_dice_throw` names the full validation gate; `_resolve_wwn_cast_for_beat` documents two entry points + the missing-spell_id asymmetry |

**Adversarial re-checks on the fix itself (all clean):**
- [VERIFIED] The widened gate cannot mask a pre-existing resolution — `dispatch_dice_throw` raises "requires an active encounter" at entry when `encounter.resolved` (dice.py:~308), so the `or encounter.resolved` term can only observe a resolution produced by THIS dispatch (strike-in-apply_beat or cast-in-spine). Complies with No Silent Fallbacks; widening is strict.
- [VERIFIED] The opposed_check branch's own `encounter_resolved = False` assignment is untouched — no behavior drift on opposed packs (road_warrior). Evidence: round-2 diff touches only the else-branch assignment.
- [VERIFIED] The opposed-cast guard sits inside the `is_wwn_cast` + spell_id-validated block — an opposed wwn cast WITHOUT spell_id still hits the earlier missing-spell_id raise; both malformed shapes are loud.
- [VERIFIED] Regression evidence: read-only testing-runner `102-2-dev-green-2` — 52/52 incl. `test_opponent_reprisal_e2e` 9/9 (the suite most exposed to the gate change), heavy_metal combat 3/3, space_opera hp e2e 4/4, confrontation-clear 5/5; ruff clean. UI 8/8 (runner `102-2-tea-red-2` post-type-fix).

Subagent tags for the gate: round-1 battery stands — [EDGE]/[SILENT]/[TYPE]/[SEC]/[SIMPLE] domains self-covered (subagents disabled via settings, covered in round-1 assessment), [TEST]/[DOC]/[RULE] findings all now closed, preflight green both rounds.

**Data flow traced (round 2):** killing cast → spine `check_hp_depletion` sets `encounter.resolved` → widened gate reads it → reprisal suppressed → outcome/log report the kill truthfully.
**Pattern observed:** good — the fix collapses the forked resolution state at its single read site rather than adding a second mutation path (dice.py:916-923).
**Error handling:** opposed-cast rejection is typed, pre-mutation, and content-author-actionable (names the cdef and the authoring fix).

**Handoff:** To Drummer (SM) for finish — PR creation and merge.