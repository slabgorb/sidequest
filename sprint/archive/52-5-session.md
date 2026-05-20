---
story_id: "52-5"
jira_key: null
epic: "52"
workflow: "tdd"
---
# Story 52-5: UI end-to-end wiring test — TacticalGridRenderer renders runtime-sourced cavern_image_url + OTEL assert

## Story Details
- **ID:** 52-5
- **Jira Key:** N/A (SideQuest does not use Jira)
- **Workflow:** tdd
- **Epic:** 52 — Wire Procedural Megadungeon Output to the ADR-096 Cavern Renderer Pipeline
- **Stack Parent:** none (52-4 completed; no blocking dependency)
- **Points:** 2
- **Priority:** p1
- **Type:** feature
- **Repos:** ui, server

## Epic Context

**Epic 52: Wire Procedural Megadungeon Output to the ADR-096 Cavern Renderer Pipeline**

ADR-096 defined a static-authoring approach for cavern visualization. ADR-106 (Runtime Procedural Jaquaysed Megadungeon) supersedes with a runtime generator that produces procedural regions. This epic bridges the gap: the renderer consumer end is fully implemented (UI can render cavern PNGs), but the procedural materializer is starved. We build the seam so procedural regions serialize ADR-096-shaped mask+PNG sidecars that the live UI already renders.

**Verdict:** SUBSUME (no new ADR supersedes; ADR-096 amendment clarifies the runtime path).

### Architecture Pipeline

1. **ADR-106 Runtime Generator** → produces procedural dungeon regions
2. **Materializer Seam (Story 52-2)** → emits ADR-096 mask + derived block per region
3. **Persistence (Story 52-3)** → mask-BLOB column, loader, reload on resume
4. **Server Sidecar (Story 52-4)** → PNG generation from runtime mask via resolve_asset_url
5. **UI Wiring (Story 52-5)** → TacticalGridRenderer renders runtime-sourced cavern_image_url + OTEL

## Story Scope

Story 52-5 is the final integration point: the UI renderer (TacticalGridRenderer) must consume the runtime-sourced cavern_image_url and render the procedural cavern PNG. Two dimensions of work:

### Frontend (sidequest-ui)
- Verify TacticalGridRenderer component receives cavern_image_url from server game state snapshot
- Render the runtime cavern PNG when available (fallback graceful if missing)
- Integration test demonstrating end-to-end wiring

### Backend (sidequest-server)
- Verify game state snapshot includes cavern_image_url from the room_file_loader sidecar
- OTEL span on the resolve_asset_url call so GM panel can verify sidecar materialization
- Server integration test verifying the wiring contract

### OTEL Observability
Per ADR-090 and CLAUDEMD development principles: every subsystem decision must emit OTEL spans so the GM panel can verify engagement. This story adds watcher events to prove cavern PNG is being sourced and rendered.

## Delivery Findings

No upstream findings yet. Story 52-4 (PNG sidecar emit) completed the server-side data pipeline; 52-5 consumes that pipeline on the UI and confirms end-to-end function.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No upstream findings during implementation. TEA's `caverns_sunden` silent-skip finding for `test_room_enter_cavern.py` was re-observed during regression sweep (7 skipped, all from that suite) and remains the right next-up cleanup — no new gaps surfaced.

### Reviewer (code review)
- **Improvement** (non-blocking): `_maybe_build_runtime_cavern_payload`'s docstring at `sidequest-server/sidequest/server/websocket_session_handler.py:503-506` claims that a corrupt mask BLOB or PIL failure "is caught by the outer `_maybe_emit_tactical_grid`'s generic `except Exception` handler" — but the helper is called inside the sibling `except RoomNotFoundError:` clause at `:667`, so exceptions raised by the runtime helper escape the outer try/except entirely rather than being caught by `except Exception` at `:707`. Affects `sidequest-server/sidequest/server/websocket_session_handler.py:667` (wrap the runtime helper call in a try/except that emits `tactical_grid.load_failed` symmetrically with the static branch, OR correct the docstring to reflect that runtime corruption surfaces as an unhandled exception to the WebSocket session-level handler). Predates 52-5 — introduced by 52-4 (#347). *Found by Reviewer during code review.*

### TEA (test design)
- **Gap** (non-blocking): The entire `tests/integration/test_room_enter_cavern.py` suite (6 tests) is currently silently skipping because its fixture references `caverns_sunden`, which has been deprecated and moved out of `genre_packs/`. Affects `sidequest-server/tests/integration/test_room_enter_cavern.py` (update fixtures to use `beneath_sunden` or another live world, or delete if the static path is no longer exercised in live content). *Found by TEA during test design.*
- **Gap** (non-blocking): Zero live packs ship an authored `*.cavern.png` + `room_type: cavern` YAML pair. The static branch of `_maybe_emit_tactical_grid` is currently unreachable from any live content. Affects `sidequest-content/genre_packs/*/worlds/*/rooms/*.yaml` (Epic 52's static path is dormant — runtime is the only consumer; document or retire the static path). *Found by TEA during test design.*
- **Improvement** (non-blocking): The `tactical_grid.emitted` watcher event today carries no `source` attribute, leaving the GM panel unable to distinguish runtime PNG from static PNG without span correlation. The fix landing on this story will close that hole; the symmetric `source: "static"` add on the static branch is a one-liner Dev should land in the same diff for free, even though no test currently covers it. Affects `sidequest-server/sidequest/server/websocket_session_handler.py` (both `_maybe_build_runtime_cavern_payload` and the static success branch in `_maybe_emit_tactical_grid`). *Found by TEA during test design.*
- **Question** (non-blocking): `MapWidget` uses `tacticalGridFromWire(loc.cavern_payload) ?? undefined` (sidequest-ui/src/components/GameBoard/widgets/MapWidget.tsx:190). The `??` only catches `null`, not the `throw` the adapter currently does. If the adapter changes from "throw on bad shape" to "return null on bad shape" rather than "accept the runtime shape," the silent-fallback bomb stays armed for any future bad payload. Affects `MapWidget.tsx:190` (consider whether the GREEN diff also tightens this site so a future broken payload is loud, not silent). *Found by TEA during test design.*

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/server/websocket_session_handler.py` — track `source` ("static" default, "runtime" in the RoomNotFoundError → runtime-payload branch) and publish it on the `tactical_grid.emitted` watcher event so the GM panel sees runtime vs static at a glance (ADR-090 / CLAUDE.md OTEL Observability Principle).
- `sidequest-ui/src/types/tactical.ts` — `TacticalGridData.cellular` now `CavernCellularParams | null` with a JSDoc note explaining the runtime-vs-static distinction.
- `sidequest-ui/src/lib/tacticalGridFromWire.ts` — drop `cellular` from the missing-fields guard so runtime payloads (cellular=null) survive the adapter; mask + cavern_image_url + cell_size + derived remain required.
- `sidequest-ui/src/components/TacticalGridRenderer.tsx` — when `cellular` is null, derive canvas dimensions from the mask string (longest row × row count) instead of `cellular.size`.

**Tests:**
- Server: `tests/integration/test_tactical_grid_runtime_wiring.py` — 1/1 PASS. Full server suite 6809 passed, 396 skipped (no new skips, no regressions).
- UI: `src/__tests__/tactical-grid-runtime-wiring.test.tsx` — 7/7 PASS. Full UI suite 1462/1462 PASS.
- `uv run ruff check sidequest/server/websocket_session_handler.py` — clean.
- `npx tsc --noEmit` (UI) — clean.

**Branches (both pushed):**
- Server: `feat/52-5-tactical-grid-runtime-cavern-image-wiring` @ cda1015
- UI: `feat/52-5-tactical-grid-runtime-cavern-image-wiring` (just pushed)

**Wiring confirmed end-to-end:**
- Server: live `_maybe_emit_tactical_grid` (the production dispatch site at websocket_session_handler.py:2365 and :4307) now publishes `source` on every `tactical_grid.emitted`.
- UI: `MapWidget` (the production consumer per the existing wiring guard test) continues to call `tacticalGridFromWire`; the adapter+renderer now accept the runtime shape the server emits.
- Both halves of Epic 52's last seam are live and load-bearing in production code, not behind a flag.

**Handoff:** To Reviewer (Col. Potter) for code review.

## Architect Assessment (spec-check)

**Spec Alignment:** Drift detected (2 minor mismatches, both acceptable; no rework)
**Mismatches Found:** 2

- **OTEL: spec said "span", implementation added an attribute to an existing watcher event** (Different behavior — Architectural, Trivial)
  - Spec (`context-story-52-5.md` AC3, line 119): "OTEL span fires distinguishing runtime path from static. Server test asserts the runtime-discriminator span (name + attrs verified) appears in the emitted span set when the payload is built for a runtime-mask room"
  - Code: Adds `source: "runtime" | "static"` as an *attribute* on the already-existing `tactical_grid.emitted` watcher event in `websocket_session_handler.py`, rather than emitting a new span.
  - Recommendation: **A — Update spec** (no code change). Reusing the live event is the right architectural call here: (a) `tactical_grid.emitted` is the canonical OTEL signal the GM panel already correlates against runtime/static; (b) the existing sibling events `tactical_grid.room_not_found` and `tactical_grid.load_failed` use the same single-event-namespace-with-attributes pattern, so a new span would be the inconsistency; (c) the GM-panel question "is this PNG runtime or static?" is answered identically by an attribute on an existing event as by a new span — but at lower cardinality and zero new instrumentation surface. This is a reuse-first win, consistent with ADR-090's existing taxonomy. The spec's word "span" was looser than intended; treat as terminology drift, not behavioral drift. TEA pre-cleared this exact interpretation in the RED's Improvement Finding (line 65 of the session file).

- **AC5 "no silent fallback on missing runtime PNG (loader raises loudly)" — failure-path assertion not directly exercised** (Missing in code — Behavioral, Minor)
  - Spec (`context-story-52-5.md` AC5, line 121): "Server test exercises the failure mode: when the runtime mask is present but the PNG cannot be resolved, the loader raises loudly instead of returning `cavern_image_url=None`"
  - Code: The server test asserts the *happy path* no-silent-fallback canary (URL is non-None + sidecar lands on disk at the claimed URL) but does not deliberately disable the PNG emitter to drive the "mask-present-PNG-missing" failure branch and assert it raises rather than returning None.
  - Recommendation: **D — Defer**, with a note. The deferral is defensible: (a) 52-4's `test_room_file_loader_runtime_png.py` already covers `room_file_loader.resolve_asset_url`'s loud-failure contract for the runtime PNG path at the unit boundary (per the spec's own References section, line 130); (b) the live `_maybe_emit_tactical_grid` already has a `FileNotFoundError` branch that emits `tactical_grid.load_failed` + warning log (websocket_session_handler.py:686–706) — a loud-failure path that pre-dates this story; (c) driving the "mask present + PNG missing" race in the wiring test would require either deleting the file mid-test or stubbing the emitter, the latter of which the spec explicitly bans ("do not mock `room_file_loader.resolve_asset_url`"); (d) the no-silent-fallback contract for the *value* (URL is non-None, points at real bytes on disk) is what the wiring test actually needs to prove, and it does. Forward impact: if a future regression silently drops the runtime PNG between emitter and resolver, the existing `tactical_grid.load_failed` watcher event is the GM-panel canary, not this story's test. Acceptable.

**Decision:** Proceed to review. Neither mismatch is a behavioral defect; both are reasonable engineering choices the spec under-specified. No hand-back to Dev. The OTEL drift is genuinely a spec wording issue (span → event attribute); the AC5 narrowing is pragmatic and covered by adjacent existing tests.

**Handoff:** To TEA (Radar O'Reilly) for verify phase.

## TEA Assessment

**Phase:** finish
**Tests Required:** Yes
**Status:** RED (failing — ready for Dev)

**Test Files:**
- `sidequest-server/tests/integration/test_tactical_grid_runtime_wiring.py` — one integration test driving the runtime branch of `_maybe_emit_tactical_grid` end-to-end with a fake DungeonStore. 5 ACs asserted (emit, URL prefix, mask round-trip, source discriminator, sidecar on disk). RED at the source-discriminator assertion (the other four pass on RED — that is the desired narrow failure surface).
- `sidequest-ui/src/__tests__/tactical-grid-runtime-wiring.test.tsx` — 7 tests covering adapter+renderer integration for runtime payloads (`cellular: null` shape). 5 fail loudly on `tacticalGridFromWire` rejection; 2 pass (the wiring guard + static regression guard).

**Tests Written:** 8 tests (1 server integration, 7 UI) covering 5 ACs from the story context.

**Failing tests:** 6 (5 UI adapter/renderer + 1 server source-discriminator). Passing: 2 (UI guards). The narrow failure surface is intentional — Dev's GREEN diff is two changes:
1. Server (`websocket_session_handler.py`): add `"source": "runtime"` to `_watcher_publish("tactical_grid.emitted", ...)` in the runtime branch (and `"source": "static"` symmetrically in the static-success branch as a free freebie, per Improvement Finding above).
2. UI (`tacticalGridFromWire.ts` + `TacticalGridRenderer.tsx`): accept `cellular: null` in the adapter, derive canvas dimensions from the mask string in the renderer when cellular is absent.

### Rule Coverage

| Rule (Python lang-review) | Test(s) | Status |
|---------------------------|---------|--------|
| #5 path handling — pathlib | `test_runtime_cavern_path_emits_*` uses `Path` and `tmp_path` throughout; no string concatenation | covered |
| #6 test quality — meaningful assertions | Every assertion is a value check with explanatory message; no `assert result` truthiness, no vacuous `assert True` | covered |
| #1 silent exception swallowing | Not directly testable in this slice (no exception handlers added); the test docstring calls out the no-silent-fallback contract for Dev's GREEN | n/a |
| #11 input validation at boundaries | Server test validates the URL prefix discriminator and the on-disk sidecar exists at the URL the payload claims — boundary contract | covered |

| Rule (project) | Test(s) | Status |
|----------------|---------|--------|
| Every Test Suite Needs a Wiring Test (CLAUDE.md) | UI: `MapWidget still imports tacticalGridFromWire` guard; Server: drives `_maybe_emit_tactical_grid` (the live dispatch site) end-to-end, not a mock | covered |
| No Silent Fallbacks (SOUL.md / CLAUDE.md) | UI: explicit "must NOT silently fall back to placeholder/static URL" assertion; Server: asserts sidecar lands on disk at the URL the payload returns | covered |
| OTEL Observability Principle | Server: the entire RED failure is "the discriminator must be on the watcher event" | covered |
| No Stubbing (CLAUDE.md) | Server test uses a `_FakeDungeonStore` (one method, returns a real mask dict) instead of a mock. The fake exists because spinning up the full DungeonStore schema (campaign_seed write-once, expansion commit) is fixture bloat for a 2pt wiring story | acceptable — minimal seam fake, not a stub |

**Rules checked:** 4 of 14 applicable Python lang-review rules and 4 of 4 project principles have direct test coverage. The remaining lang-review rules (#2 mutable defaults, #4 logging, #7 resource leaks, etc.) are not applicable to a wiring-test diff that introduces only test code.

**Self-check:** Zero vacuous assertions found in the new tests. Every assertion has a real value check + an explanatory failure message.

**Pitfall surfaced during RED:** The original test asserted against `caverns_sunden`, which the testing-runner correctly flagged as silently-skipping. Pivoted to `beneath_sunden`. Logged as a Delivery Finding (the existing `test_room_enter_cavern.py` has the same drift and is dead test-time).

**Handoff:** To Dev (Major Charles Emerson Winchester III) for GREEN.

## TEA Verify Assessment

**Phase:** finish
**Status:** PASS — ready for Reviewer

**Quality gates:**
- Server: `uv run ruff check` clean (auto-detected I001 import-order issue fixed in test file with documented `noqa` — see below).
- Server: full suite 6809 passed, 396 skipped (parity with baseline; the 7-skip caverns_sunden suite was pre-existing per TEA's prior Delivery Finding).
- Server: targeted `tests/integration/test_tactical_grid_runtime_wiring.py` 1/1 PASS.
- UI: `npx tsc --noEmit` clean.
- UI: full suite 1462/1462 PASS across 138 test files.
- UI: targeted `src/__tests__/tactical-grid-runtime-wiring.test.tsx` 7/7 PASS.

**Verify-phase fix landed (commit b45e420 in sidequest-server):**
- `tests/integration/test_tactical_grid_runtime_wiring.py`: added `# noqa: I001` on the import block with a header comment explaining why auto-sort is unsafe. Alphabetical re-ordering would place bare `sidequest.server` before `sidequest.server.session_handler` and re-introduce the circular-import the original comment block warned against. The original comment block (between imports) didn't break the ruff block; I consolidated it as a header preceding the noqa'd block.

### Simplify Report

**Teammates:** reuse, quality, efficiency (Haiku model, all three spawned in parallel)
**Files Analyzed:** 6 (2 server: `websocket_session_handler.py` diff scope + `test_tactical_grid_runtime_wiring.py`; 4 UI: `TacticalGridRenderer.tsx`, `tacticalGridFromWire.ts`, `tactical.ts`, `tactical-grid-runtime-wiring.test.tsx`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 2 findings | 1 high (duplicated test fixture helper), 1 medium (extractable UI mask-dimension helper) |
| simplify-quality | clean | No naming, dead-code, type-safety, or architecture-violation issues. |
| simplify-efficiency | clean | The renderer's IIFE for null-cellular dimension derivation and the server's `source` variable are both deliberate and well-sized; not over-engineered. |

**Applied:** 0 high-confidence fixes (see deferral rationale below)
**Flagged for Review:** 1 medium-confidence finding (Reviewer / future story)
**Noted:** 1 high-confidence finding deferred to a follow-up
**Reverted:** 0

**Detailed findings:**

1. **HIGH (deferred to follow-up): duplicated mask-fixture helper across two test files.**
   - `tests/integration/test_tactical_grid_runtime_wiring.py:61` defines `_runtime_mask_dict()`; `tests/game/test_room_file_loader_runtime_png.py:76` already defines `_mask_dict()` returning the same `RegionMask.to_dict()`-shaped dict.
   - Suggested fix: extract to a shared conftest or test-fixtures module so both suites import the same helper.
   - **Why deferred, not applied:** the existing helper lives in 52-4 territory and is exercised by 30+ assertions in that suite. Extracting it requires moving the helper, updating both callsites, and re-running both suites — that crosses the SM's explicit guardrail ("Don't widen scope into materializer/persistence/PNG-emitter changes — those are 52-2/52-3/52-4's territory and shipped"). The duplication is ~10 lines of trivial dict-building. The right home for this cleanup is a dedicated test-hygiene story that also folds in the deprecated-`caverns_sunden` skip fix already flagged in Delivery Findings.
   - Forward action: file as a follow-up under epic 52 or sprint-2621 tech-debt.

2. **MEDIUM (flagged for Reviewer / future story): extractable `getMaskDimensions` helper for cellMath.ts.**
   - `sidequest-ui/src/components/TacticalGridRenderer.tsx:26` derives `[cols, rows]` from the mask string inline. `sidequest-ui/src/lib/cellMath.ts:29` already parses mask rows (`mask.split("\n").filter(r => r.length > 0)`) for `isFloor()`.
   - Suggested fix: extract `getMaskDimensions(mask: string): [cols, rows]` into `cellMath.ts` and import it from the renderer.
   - **Not auto-applied per workflow:** confidence: medium. Flagged for Reviewer or a UI-cleanup follow-up story.

**Overall:** simplify: clean (no auto-applied changes; quality + efficiency clean; reuse findings deferred to follow-up with documented rationale).

**Wiring confirmed end-to-end (re-verified):**
- Server `_maybe_emit_tactical_grid` is called at `websocket_session_handler.py:2365` and `:4307` (the live narrator-location-change branch and chargen room-graph init) — both publish `source` now.
- UI: `MapWidget` consumer guard test in `tactical-grid-runtime-wiring.test.tsx` confirms `tacticalGridFromWire` is still imported by production code.

**Handoff:** To Reviewer (Col. Sherman Potter) for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (1 skip note evaluated as expected `_packs_available()` guard, not a real skip — test PASSED with content present) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings (`workflow.reviewer_subagents.edge_hunter: false`) — reviewer covered edge cases via own analysis (see Devil's Advocate below). |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings — reviewer covered silent-failure paths via own analysis (`source` default, adapter throw, `tactical_grid.load_failed` branch). |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings — reviewer hand-verified test quality against Python lang-review #6 and TypeScript lang-review #8 (see Rule Compliance). |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings — reviewer noted that the load-bearing `noqa: I001` header and `_maybe_build_runtime_cavern_payload` docstring inaccuracy are documented as Delivery Findings. |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings — reviewer verified `CavernCellularParams \| null` correctness, `source: str` (stringly-typed but consistent with watcher-event attr dicts), and `type: ignore[attr-defined]` on documented dynamic attribute. |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings — no security-sensitive code in diff (no user input, no SQL, no deserialization of untrusted bytes, no auth). |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings — TEA's verify-phase simplify trio already ran (`reuse`, `quality`, `efficiency`). Quality+efficiency clean; reuse flagged 1 high (deferred, crosses 52-4 territory) + 1 medium (flagged for future story). See TEA Verify Assessment. |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings — reviewer performed exhaustive rule enumeration against Python + TypeScript lang-review checklists (see Rule Compliance section below). |

**All received:** Yes (1 spawned + 8 pre-filled as disabled per `pf settings get workflow.reviewer_subagents`)
**Total findings:** 0 confirmed, 0 dismissed, 1 deferred (preflight's "skip" was a `_packs_available()` runtime guard, not a real skip)

## Reviewer Assessment

**Verdict:** APPROVED

**Story summary verified end-to-end:**

The PR closes the Epic 52 wiring loop. Server now publishes a `source: "runtime" | "static"` attribute on the existing `tactical_grid.emitted` watcher event so the GM panel (Sebastien) can distinguish procedural cavern PNGs from authored ones without correlating sibling spans. UI accepts the `cellular: null` shape the server's runtime branch emits (the persisted mask BLOB carries no generation params), and derives canvas dimensions from the mask string when cellular is absent. Production code change is 6 server lines + 22 UI lines; tests are a 312-line server integration test exercising the live `_maybe_emit_tactical_grid` dispatch site and a 213-line UI suite (7 tests) covering adapter+renderer+wiring-guard.

**Data flow traced (end-to-end):**
- Player enters a procedural region (`snapshot.character_locations[actor] = region_id`).
- Narrator/chargen dispatch calls `_maybe_emit_tactical_grid` (live sites at `websocket_session_handler.py:2365` and `:4307`).
- Static `load_room_payload` raises `RoomNotFoundError` (procedural region has no YAML).
- `except RoomNotFoundError:` branch calls `_maybe_build_runtime_cavern_payload(sd=sd, room_id=region_id)`.
- That helper reads `sd.dungeon_store` (documented `getattr` pattern at `:516`), pulls the persisted mask via `load_masks()`, writes `<output>/artifacts/dungeon/<save>/regions/<region_id>.cavern.png` via `emit_runtime_cavern_png`, and returns a `TacticalGridPayload` with `cellular=None`.
- Outer function sets `source = "runtime"`, publishes `tactical_grid.emitted` with `source` attribute, and calls `emit_fn(msg, "TACTICAL_GRID")`.
- WebSocket transports the message to the client. `MapWidget` (`MapWidget.tsx:189-190`) extracts `cavern_payload` and calls `tacticalGridFromWire(cavern_payload)`. Adapter now accepts `cellular: null` (still throws on missing mask/url/cell_size/derived). Returns `TacticalGridData`.
- `TacticalGridRenderer` consumes `grid`; when `cellular === null`, derives `[cols, rows]` from `grid.mask.split("\n")` and renders `<img data-testid="cavern-floor" src={grid.cavern_image_url} width={cols * cellSize} height={rows * cellSize}>`.

Safe because: no silent fallback at any seam (adapter throws on missing required fields; renderer uses deterministic mask-string parse; `source` defaults to `"static"` only inside a fresh function-local scope, not via mutable default).

**Pattern observed:**
- `websocket_session_handler.py:651-668` — the new `source = "static"` / `source = "runtime"` flag-then-emit pattern matches the existing `tactical_grid.*` event taxonomy (sibling events `room_not_found`, `load_failed` use the same single-event-namespace-with-attributes idiom). Architecturally consistent.
- `TacticalGridRenderer.tsx:20-29` — the conditional `grid.cellular ? grid.cellular.size : (() => { ... })()` IIFE is a deliberate read-the-source-once optimisation; the alternative (e.g. `Math.max(...lines.map(l => l.length))`) would double-parse the mask. Acceptable but worth refactoring to a `cellMath.ts` helper in a follow-up (TEA's flagged-medium finding).

**Error handling:**
- Adapter still throws on missing required fields (mask/cavern_image_url/cell_size/derived). The throw is silently swallowed by `MapWidget`'s `?? undefined` at `MapWidget.tsx:190` — but this is the pre-existing surface; the wiring test now actively guards against the runtime payload triggering this path. TEA's RED captured this as a "Question" finding for a future hardening story.
- Server: `source` is local to the function call; the early-return paths (RoomNotFoundError → runtime returns None; FileNotFoundError; bare Exception) skip the emit entirely, so the `source` attribute is never published on error events. Correct behavior — error events have their own watcher names.

**Wiring:**
- UI: `MapWidget` continues to import `tacticalGridFromWire` (verified at line 6 of MapWidget.tsx and called at line 190). The new wiring test asserts this import survives — guards against a quiet refactor that would bypass the adapter.
- Server: `_maybe_emit_tactical_grid` is called at `websocket_session_handler.py:2365` and `:4307` (narrator location-change + chargen room-graph init). The new `source` attribute fires on every call. No new dispatch site needed.

**Security analysis:**
- Diff has no user input, no auth, no SQL, no deserialization, no command execution, no template rendering. The `source` attribute is a server-generated string literal ("static" or "runtime"), never derived from input. No security surface.

**Hard questions answered:**
- *Trailing newline on mask?* `"#####\n#...#\n".split("\n")` returns `["#####", "#...#", ""]` — `lines.length === 3` over-counts by 1. Server's runtime emitter joins rows with `"\n"` without trailing newline (verified at `websocket_session_handler.py:480-490` runtime code path uses `RegionMask.to_dict()` shape produced by `RegionMask`), so this is a contract risk, not a current bug. Test fixture matches the server contract (no trailing newline). Acceptable — flagging in Devil's Advocate.
- *Variable-length rows?* Width = `max(line.length)`, height = row count. Shorter rows render to undefined cell space but no crash. Test fixture is uniform-width. Server contract guarantees uniform rows (all caverns are rectangular ASCII grids per ADR-096).
- *`grid.cellular` is undefined (not null)?* Type is `CavernCellularParams | null`. Truthy check `grid.cellular ? ...` handles both null and undefined identically — falls to mask-derivation. Benign even if a future bug passes undefined.
- *Multiple regions in one snapshot?* `_maybe_emit_tactical_grid` only emits one per call, and is called once per actor-location-change. No coalescing needed.

### Rule Compliance

Exhaustive enumeration against `.pennyfarthing/gates/lang-review/python.md` and `typescript.md`. The reviewer-rule-checker subagent is disabled in settings, so this is a manual sweep.

**Python lang-review checklist (`python.md`, 14 numbered checks):**

| # | Rule | In-diff items | Status |
|---|------|---------------|--------|
| 1 | Silent exception swallowing | No new `except` clauses in the 6-LOC production diff. Test has no try/except. | Compliant |
| 2 | Mutable default arguments | No new function signatures with defaults. `_runtime_mask_dict` uses `cell_width=28` (int literal, immutable). | Compliant |
| 3 | Type annotation gaps at boundaries | `_maybe_emit_tactical_grid` was already annotated; `source: str` local doesn't need annotation (inferred from literal). Test helpers `_runtime_mask_dict` and `_packs_available` have full annotations. Function parameters typed (`monkeypatch: pytest.MonkeyPatch, tmp_path: Path`). | Compliant |
| 4 | Logging coverage and correctness | No new logging in production diff (existing log paths at lines 670, 689, 708 unchanged). | Compliant — no regression |
| 5 | Path handling — pathlib | Test uses `Path(__file__).resolve().parents[3]` and `tmp_path` throughout. No string concatenation. No raw `open()`. | Compliant |
| 6 | Test quality | All 5 ACs assert with specific value comparisons + explanatory messages. No `assert True`, no `assert result` truthiness, no `mock.patch`. `pytest.skip()` has explanatory string. | Compliant |
| 7 | Resource leaks | `SqliteStore.open_in_memory()` is used without explicit close; in-memory SQLite is auto-cleaned at GC and the test's pytest fixture lifecycle bounds it. No new file handles, no requests sessions, no threading locks. | Compliant |
| 8 | Unsafe deserialization | `base64.b64encode` is encoding, not decoding. `_runtime_mask_dict` builds a dict literal — no JSON/yaml/pickle from external input. | Compliant |
| 9 | Async/await pitfalls | No async code in diff. | N/A |
| 10 | Import hygiene | No star imports. Function-local imports inside `test_*` are documented (the noqa block explains circular-import avoidance). | Compliant |
| 11 | Input validation at boundaries | No new boundary code. The `source` attribute is generated from internal control flow, never from input. | Compliant |
| 12 | Dependency hygiene | No `pyproject.toml`/`requirements` changes. | N/A |
| 13 | Fix-introduced regressions | Verify-phase added `# noqa: I001` to fix ruff I001 finding. The noqa is scoped to the one block and has a header comment. Not a regression. The reviewer-phase slug fix (`caverns_sunden → beneath_sunden` at e445e6b) cross-checks against checks #1–#12 — clean. | Compliant |
| 14 | State cleanup ordering with fallible side effects | No register/save-then-clear pattern in diff. | N/A |

**TypeScript lang-review checklist (`typescript.md`, 13 numbered checks):**

| # | Rule | In-diff items | Status |
|---|------|---------------|--------|
| 1 | Type safety escapes | No new `as any`, `as unknown as T`, `@ts-ignore`, or `!`. Test uses `as HTMLImageElement` on `getByTestId` results — standard `@testing-library/react` pattern, not a violation. The `as const` on `[width, lines.length]` is correct for tuple literal inference. | Compliant |
| 2 | Generic and interface pitfalls | No `Record<string, any>`, no `object` type, no `Function` type. `WirePayload.cellular` is a precise discriminated union (`{...} \| null`). | Compliant |
| 3 | Enum anti-patterns | No enums in diff. | N/A |
| 4 | Null/undefined handling | `grid.cellular ? grid.cellular.size : (...)` — truthy check on a `CavernCellularParams \| null` is correct (both null and undefined fall to else). Adapter uses `!p.cellular`/`!p.mask` etc. — could in principle treat `cell_size: 0` as missing (cell_size 0 is invalid anyway), but the contract guarantees positive cell sizes. No `\|\|` vs `??` confusion. | Compliant |
| 5 | Module and declaration issues | `import type` not used (re-exports are runtime values). No `.js` extension issues (Vite resolves). No reference directives. | Compliant |
| 6 | React/JSX (.tsx files) | `useState` in renderer unchanged. No new `useEffect`. No `dangerouslySetInnerHTML`. No `key={index}`. Test uses `@testing-library/react`'s `render` + `screen.getByTestId` — idiomatic. | Compliant |
| 7 | Async/Promise patterns | Test uses `async`/`await` on `import("@/components/.../MapWidget?raw")` correctly. No `Promise<void>` mistakes. | Compliant |
| 8 | Test quality | Every `expect` has a specific matcher. No `as any` to make types match. No `vi.mock()` (the test uses real adapter + renderer). Includes negative assertions (`not.toContain("placeholder")`). Includes static-regression guard. | Compliant |
| 9 | Build and config concerns | No `tsconfig.json` changes; project's `strict: true` setting carried over. `npx tsc --noEmit` clean per TEA Verify. | Compliant |
| 10 | Security: type-level input validation | No `JSON.parse()` `as T`. The `WirePayload` interface is the boundary contract; runtime validation lives at the server-emission seam. Acceptable for an internal protocol boundary. | Compliant |
| 11 | Error handling | Adapter `throw new Error(...)` is explicit and tested. No `catch(e: any)`. | Compliant |
| 12 | Performance and bundle | No new barrel imports. No `JSON.stringify` in hot paths. No sync fs. Inline IIFE for mask-dimension derivation is O(rows + chars) and avoids double-parsing. | Compliant |
| 13 | Fix-introduced regressions | No fixes were applied during reviewer phase to TS code. | N/A |

**Project rules (CLAUDE.md, SOUL.md):**

| Rule | Verdict |
|------|---------|
| No Silent Fallbacks | ✓ adapter throws on missing required fields; renderer's mask-derivation is deterministic; server `source` defaults to a real literal (`"static"`), not `None`/`""`/silently-missing. |
| No Stubbing | ✓ `_FakeDungeonStore` is a one-method seam fake, not a stub. Returns real `RegionMask.to_dict()`-shaped data that `_maybe_build_runtime_cavern_payload` exercises end-to-end. |
| Don't Reinvent — Wire Up What Exists | ✓ extends existing `tactical_grid.emitted` event with an attribute. No new span. No new dispatch path. No new helper modules. |
| Verify Wiring, Not Just Existence | ✓ server test calls live `_maybe_emit_tactical_grid` (not the inner helper); UI test asserts `MapWidget` imports `tacticalGridFromWire`. |
| Every Test Suite Needs a Wiring Test | ✓ both repos have explicit wiring assertions in this PR. |
| OTEL Observability Principle | ✓ the `source` attribute IS the new observability hook the GM panel reads. |

**Devil's Advocate**

I will now argue this code is broken.

The server-side `source` discriminator is wrong by omission. The flat `try/except` chain at `websocket_session_handler.py:653-726` looks like it handles every failure mode of cavern rendering, but `_maybe_build_runtime_cavern_payload` is called inside the `except RoomNotFoundError:` clause. In Python, an exception raised inside an `except` clause is NOT caught by sibling `except` clauses at the same `try` level — it propagates out of the entire `try` statement. The docstring of `_maybe_build_runtime_cavern_payload` (lines 503-506) claims that "a corrupt mask BLOB or PIL failure propagates as a ValueError/OSError and is caught by the outer `_maybe_emit_tactical_grid`'s generic `except Exception` handler". That is factually false at the language level. If a corrupted BLOB or PIL crash occurs inside the runtime branch, the exception escapes `_maybe_emit_tactical_grid` entirely and lands in the WebSocket session's outer error handler — which may or may not present a graceful error to the player. The `source = "runtime"` line is not even reached, so the OTEL channel sees no `tactical_grid.emitted` event AND no `tactical_grid.load_failed` event — silently failing one of the project's two cardinal rules. *However*, this is NOT a regression from 52-5. The exception-propagation surface was introduced by 52-4 (`feat(52-4): emit_runtime_cavern_png + tactical-grid runtime wiring (#347)`, commit 015a152). 52-5's diff adds 6 LOC of `source` tracking; it does not touch the try/except structure. The defect lives in 52-4's territory and is flagged below as a Delivery Finding for a follow-up. It does not block 52-5.

On the UI side, the renderer's mask-string parse has a subtle contract risk. `grid.mask.split("\n")` returns a list whose `.length` equals the number of separators plus one. If the server ever emits a trailing newline (`"#####\n#...#\n"`), `lines.length` becomes 3 instead of 2 and the rendered canvas height adds an extra cellSize of empty space. The current contract is uniform-width rectangular grids without trailing newlines (verified against `RegionMask.to_dict()`'s join logic, no trailing `\n`), but the renderer doesn't enforce or assert this. A future server change that adds a trailing newline would silently produce an off-by-one canvas overflow. Not a current bug, not a blocker — but the contract is implicit, not enforced. The renderer could filter empty lines (`lines.filter(l => l.length > 0)`) the way `cellMath.ts:29` already does for `isFloor()`; the inconsistency between renderer (no filter) and cellMath (filter) is the kind of small drift that becomes a real bug when the next test fixture differs.

Confused-user / stressed-filesystem cases: `SIDEQUEST_OUTPUT_DIR` env var unset at turn time triggers `_maybe_build_runtime_cavern_payload` to return None (per its docstring "the local-renders output directory is not configured"); the runtime branch then falls through to `else: return` and emits `tactical_grid.room_not_found`. That is the correct behaviour — loud-fail at startup via `render_assets.no_output_dir` + per-turn skip event for the GM panel. The new `source` attribute is consistent in that path: it stays `"static"` and is never published (return short-circuits before emit). No regression.

A malicious-input vector? None. The new `source` value is a hardcoded server-side literal. The UI `cavern_image_url` flows from server config (`SIDEQUEST_ASSET_BASE_URL`) and the server's own region_id, never from player input. The cavern PNG is rendered server-side from a server-persisted mask, never from player-supplied bytes. There's no injection surface, no XSS vector (the URL goes into `<img src=>`, not `dangerouslySetInnerHTML`), no auth bypass.

Devil's advocate conclusion: the only real concern (server exception propagation in the runtime-payload helper) predates this PR and is correctly out of scope. The mask-parse contract risk is benign under the current server contract. **No new findings rise to blocker severity for 52-5.**

**Observations (≥5 required):**

1. `[VERIFIED]` `source` discriminator defaults to `"static"` and is reassigned only inside the runtime success branch — control flow is mutually exclusive by structure. Evidence: `websocket_session_handler.py:654` (default), `:669` (runtime assignment), `:750` (publish). Complies with No-Silent-Fallback (real literal, never None).
2. `[VERIFIED]` UI adapter still throws on truly-missing required fields (mask, cavern_image_url, cell_size, derived); only `cellular` was relaxed. Evidence: `tacticalGridFromWire.ts:36-41`. Complies with No-Silent-Fallback. Note: the throw is swallowed by `MapWidget`'s `?? undefined` at `MapWidget.tsx:190` — pre-existing surface, captured by TEA as a non-blocking Question for future hardening.
3. `[VERIFIED]` UI renderer derives dimensions deterministically when `cellular` is null. Evidence: `TacticalGridRenderer.tsx:23-29`. `width = max(line.length)`, `height = lines.length`. Single mask parse, no double work.
4. `[VERIFIED]` Wiring test for `MapWidget` import is real — `MapWidget.tsx:6` imports `tacticalGridFromWire`, `MapWidget.tsx:190` calls it. The wiring-guard test would fail if a future refactor removed either.
5. `[VERIFIED]` Server test exercises the live dispatch site (`_maybe_emit_tactical_grid`, not the inner helper). Confirms project rule "Verify Wiring, Not Just Existence". Evidence: `test_tactical_grid_runtime_wiring.py:201-207`.
6. `[VERIFIED]` Test's `# type: ignore[attr-defined]` on `sd.dungeon_store` assignment is justified — production code uses `getattr(sd, "dungeon_store", None)` at `websocket_session_handler.py:516` as a documented dynamic-attribute Decision-N gate. Specific-error-code form complies with Python lang-review #3.
7. `[VERIFIED]` Test `noqa: I001` has a header comment explaining why auto-sort is unsafe (would re-introduce circular import). Complies with Python lang-review #10.
8. `[LOW — fixed in-review at e445e6b]` Test had stale `store.init_session("caverns_and_claudes", "caverns_sunden")` — should match the rest of the test fixture's `beneath_sunden` slug. Reviewer fixed and re-verified. See Reviewer (audit) deviation entry.
9. `[LOW — deferred to follow-up]` Reuse simplify-finding: `_runtime_mask_dict` duplicates `_mask_dict` from 52-4's `test_room_file_loader_runtime_png.py`. Extraction to shared conftest crosses 52-4 territory and is rightfully a separate hygiene story. TEA's verify report documented the rationale.
10. `[LOW — deferred to follow-up]` Simplify-finding: `TacticalGridRenderer`'s mask-dimension IIFE could become a `cellMath.ts` helper alongside the existing row-parsing logic. Inline form is acceptable for now (avoids double-parse vs the obvious alternatives).
11. `[LOW — IMPROVEMENT, out of scope, captured as Delivery Finding]` `_maybe_build_runtime_cavern_payload` raises inside `except RoomNotFoundError:` — exception escapes the entire `try/except` chain rather than being caught by sibling `except Exception`. Docstring lines 503-506 of that helper are factually wrong about which handler catches the failure. Predates 52-5 (introduced in 52-4 / commit 015a152).

**Handoff:** To SM (Hawkeye Pierce) for finish-story.

## Sm Assessment

**Routing rationale.** 52-5 is the wiring-test capstone for Epic 52. 52-2/52-3/52-4 are merged and the renderer end has been live for static caverns since pre-epic. The risk surface is *whether the runtime path reaches the renderer end-to-end without a silent fallback to None or a static URL*. Per CLAUDE.md ("Every Test Suite Needs a Wiring Test") and SOUL.md ("No Silent Fallbacks"), the test is the deliverable; production code only changes if the test exposes a real wiring bug.

**Workflow.** TDD with two-repo RED: one UI test (React/Vitest) + one server test (Pytest) must land failing before any production change. Phased routing — TEA owns RED.

**Scope guardrails for downstream agents.**
- The story is *wiring*, not redesign. `TacticalGridRenderer` is a black-box consumer; do not refactor it unless the wiring test forces it.
- Do not mock `room_file_loader.resolve_asset_url` — exercise the real loader against a fixture mask. Mocks defeat the entire premise of this story.
- Reuse 52-4's fixture pattern (`test_room_file_loader_runtime_png.py`, `test_cavern_static_mount.py`). Do not invent a parallel harness.
- OTEL: if 52-4 already emits the runtime-vs-static discriminator span, the server test just asserts it. If it does not, add it here. Check before writing.
- Both repos use **gitflow** — base `develop`, `gh pr create --base develop`. Branches already created off develop in both repos.
- caverns_sunden is a deprecated *content target* but acceptable as a fixture input (52-4 already does this).

**Pitfalls to avoid.**
- Don't widen scope into materializer/persistence/PNG-emitter changes — those are 52-2/52-3/52-4's territory and shipped.
- Don't write a unit test that asserts string equality on a URL constant and call it "end-to-end." The test must thread the wire payload through `tacticalGridFromWire` on UI and through `room_file_loader` on server.
- The story is 2 points — right-size the plan ceremony. No multi-method TDD spec; one RED commit per repo is the target.

**Handoff:** TEA (Radar) for RED.

## Design Deviations

### TEA (test design)
- **Dropped the planned static-branch counterpart test in favor of a code-only comment**
  - Spec source: SM Assessment, "Pitfalls to avoid" — implied both branches covered
  - Spec text: "discriminator [tells] runtime PNG from static" — implied symmetric assertion
  - Implementation: Only the runtime-side `source: "runtime"` assertion is written. A NOTE comment in the test module asks Dev's GREEN diff to add `source: "static"` symmetrically to the static branch's `_watcher_publish` call, but no test runs against it.
  - Rationale: Zero live packs ship an authored `.cavern.png` + cavern-type room YAML today (caverns_sunden moved to genre_workshopping/, beneath_sunden rooms are all room_type=settlement). The static branch of `_maybe_emit_tactical_grid` cannot be exercised against a real fixture without authoring new content — out of scope for a 2pt wiring story. Runtime branch is the *only* path to a rendered cavern PNG in the current live system, so it is the load-bearing assertion.
  - Severity: minor
  - Forward impact: a follow-up story should land the static-branch test alongside the first authored cavern room when one ships; until then the runtime-side discriminator is the canary on the GM panel.

- **Switched fixture world from caverns_sunden → beneath_sunden**
  - Spec source: context-story-52-5.md "Constraints" + project memory
  - Spec text: "caverns_sunden is a deprecated content target but acceptable as a fixture input"
  - Implementation: Test fixtures use `beneath_sunden` instead of `caverns_sunden`. The deprecated `caverns_sunden` world is no longer present at `genre_packs/caverns_and_claudes/worlds/` (it was moved to `genre_workshopping/`), so the existing `tests/integration/test_room_enter_cavern.py` suite silently skips all 6 of its tests on this codebase. Using `caverns_sunden` would have produced the same silent skip and made the RED unverifiable.
  - Rationale: The context-story memo permitted caverns_sunden as a fixture input, but on the current checkout the world is absent entirely. beneath_sunden is the live procedural-region world Epic 52 is built for.
  - Severity: minor
  - Forward impact: the existing static integration tests in test_room_enter_cavern.py are currently silently skipping — flagged as a Delivery Finding below for a separate cleanup.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec. The GREEN diff is exactly what TEA's RED commit prescribed: (a) server `_maybe_emit_tactical_grid` tracks a local `source` variable defaulting to `"static"` and flipped to `"runtime"` in the RoomNotFoundError → `_maybe_build_runtime_cavern_payload` branch, then publishes it on `tactical_grid.emitted`; (b) UI `TacticalGridData.cellular` becomes nullable, `tacticalGridFromWire` drops `cellular` from the missing-fields guard, and `TacticalGridRenderer` derives canvas dimensions from the mask string (longest row × row count) when `cellular` is null. Static branch gets `source: "static"` as the symmetric freebie TEA called out.

### Reviewer (audit)

**Stamps on prior deviations:**
- **TEA — Dropped static-branch counterpart test** → ✓ ACCEPTED by Reviewer: rationale is sound. The static path is dormant content (zero authored cavern rooms in live packs); driving it would require new YAML+PNG content out of scope for a 2pt wiring story. The runtime-side discriminator IS the load-bearing assertion for the only currently-live path. Architect Assessment also flagged this as "D — Defer, with note", and the symmetric `source: "static"` literal is wired symmetrically in the code even without a test, so when the first authored cavern room ships the discriminator already works — a follow-up test is the only outstanding action.
- **TEA — Switched fixture world caverns_sunden → beneath_sunden** → ✓ ACCEPTED by Reviewer: aligns with project doctrine (`project_deprecated_caverns_sunden` memory) and with the on-disk reality (caverns_sunden is in `genre_workshopping/`, not `genre_packs/`). Test would silently skip otherwise.
- **Dev — No deviations** → ✓ ACCEPTED by Reviewer: verified against diff. The GREEN implementation is exactly TEA's prescribed surface — 6 LOC of server change for the discriminator, 22 LOC of UI change for the nullable-cellular path. No scope creep observed.
- **Architect — 2 spec-check mismatches (OTEL "span" wording + AC5 failure-path narrowing)** → ✓ ACCEPTED by Reviewer: rationales are sound. The "span vs attribute" choice is a reuse-first win consistent with sibling `tactical_grid.*` event taxonomy. The AC5 narrowing is covered by 52-4's `test_room_file_loader_runtime_png.py` at the unit boundary plus the live `tactical_grid.load_failed` watcher event, and the wiring-test contract genuinely needs the positive-path no-silent-fallback canary (URL non-None + sidecar on disk), not a mocked failure injection.

**New deviations discovered by Reviewer (undocumented):**

- **Stale `caverns_sunden` slug in `store.init_session()` (fixed mid-review at commit e445e6b)**
  - Spec source: project memory `project_deprecated_caverns_sunden` + the TEA deviation above ("Switched fixture world from caverns_sunden → beneath_sunden")
  - Spec text: "never re-render/re-add it [caverns_sunden]"; TEA's stated intent was that the entire test fixture uses beneath_sunden
  - Implementation (as-pushed before review): the test correctly used `world_slug="beneath_sunden"` on `GameSnapshot` and `_SessionData`, but `store.init_session("caverns_and_claudes", "caverns_sunden")` still referenced the deprecated slug. This contradicted the TEA deviation entry that claimed the fixture world had been fully switched.
  - Reviewer correction: changed to `store.init_session("caverns_and_claudes", "beneath_sunden")`. Single-line edit, committed as e445e6b on `feat/52-5-tactical-grid-runtime-cavern-image-wiring`, test still 1/1 PASS, full server suite still 6809/396.
  - Severity: low (init_session does not validate world existence — purely clears per-slot tables and INSERT-OR-REPLACE's session_meta row 1; the inconsistency was misleading documentation, not behavioural)
  - Forward impact: none (caught and fixed in-review)

### Architect (reconcile)

**Existing-entry verification:**
- **TEA #1 (Dropped static-branch counterpart test):** all 6 fields accurate. Spec source (SM Assessment "Pitfalls to avoid" implying symmetric coverage) is correctly cited. Spec text is a fair paraphrase of SM's "OTEL: if 52-4 already emits the runtime-vs-static discriminator span, the server test just asserts it; if not, the story includes adding the span and asserting it" — implies both branches. Implementation (NOTE comment + runtime-only assertion) verified at `test_tactical_grid_runtime_wiring.py:300-311`. Rationale (zero authored cavern rooms in live packs) cross-verified — `beneath_sunden`'s rooms are all `room_type: settlement` and the deprecated `caverns_sunden` is in `genre_workshopping/`, not on the loader's search path. Forward impact accurate.
- **TEA #2 (Switched fixture world):** all 6 fields accurate. Spec source (`context-story-52-5.md` Constraints + project memory `project_deprecated_caverns_sunden`) verified — context line 86-90 reads "if a fixture pack is needed, use an existing world (e.g. `caverns_and_claudes/worlds/caverns_sunden`)". Spec text directly quoted. Implementation (beneath_sunden used) verified at `test_tactical_grid_runtime_wiring.py:54, 156, 167`. Rationale and forward impact both accurate.
- **Dev (No deviations):** verified against diff. The implementation surface is exactly what TEA's RED commit prescribed at session-file lines 77-79. 6 LOC of server change (`source` default + flip + attribute), 22 LOC of UI change across types/adapter/renderer. No scope creep observed. Note: renderer + adapter + type signature changes are NOT scope deviations because `context-story-52-5.md` line 35-37 and lines 141-142 explicitly authorise renderer changes when the wiring test forces them ("If Dev finds production code needs to change to make the wiring test pass, that change is the bug 52-5 exists to surface — treat it as in-scope and fix it here").
- **Reviewer audit stamps:** all four stamps are sound. The mid-review fix at commit e445e6b is properly documented with a complete 6-field entry. The severity assessment (low — init_session does not validate world existence) is correct: `SqliteStore.init_session` at `sidequest/game/persistence.py:380` only clears per-slot tables and INSERT-OR-REPLACE's session_meta row 1; world existence is never checked.
- **Architect (spec-check) deviations:** the two mismatches logged during spec-check (OTEL "span" wording → attribute; AC5 failure-path assertion narrowed) are documented in the Architect Assessment section above and ratified by the Reviewer audit. They do not need re-logging here — the assessment IS the deviation log for spec-interpretation choices made during review.

**Missed deviations:** No additional deviations found.

The reconciliation pass confirms that every spec deviation in this story is documented with the full 6-field format. The audit chain is complete: TEA logged at RED → Dev confirmed at GREEN → Architect (spec-check) added two interpretation deviations → Reviewer stamped all entries + added one undocumented deviation (init_session slug) caught and fixed mid-review.

**AC deferral verification:** No ACs were formally deferred via the ac-completion gate's accountability table — all six ACs from `context-story-52-5.md` are addressed (5 directly tested, 1 — AC5 failure-path — narrowed to the positive-path no-silent-fallback canary with explicit deferral rationale in the Architect spec-check assessment). The Reviewer ratified this narrowing. No status changes to record.

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-20T07:55:28Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-20 | 2026-05-20T04:09:41Z | 4h 9m |
| red | 2026-05-20T04:09:41Z | 2026-05-20T04:22:53Z | 13m 12s |
| green | 2026-05-20T04:22:53Z | 2026-05-20T07:34:41Z | 3h 11m |
| spec-check | 2026-05-20T07:34:41Z | 2026-05-20T07:36:11Z | 1m 30s |
| verify | 2026-05-20T07:36:11Z | 2026-05-20T07:45:15Z | 9m 4s |
| review | 2026-05-20T07:45:15Z | 2026-05-20T07:53:49Z | 8m 34s |
| spec-reconcile | 2026-05-20T07:53:49Z | 2026-05-20T07:55:28Z | 1m 39s |
| finish | 2026-05-20T07:55:28Z | - | - |

## TDD Test Plan (Discovery)

Tests must verify the end-to-end contract:

1. **Server Contract Test** — Game state snapshot includes cavern_image_url for procedural regions
   - Load procedural dungeon region (reuse story 52-4 fixture)
   - Snapshot must include room with cavern_image_url populated
   - OTEL span from resolve_asset_url must fire

2. **UI Component Test** — TacticalGridRenderer consumes cavern_image_url
   - Pass mock game state with cavern_image_url
   - Verify component renders the image element
   - Verify fallback behavior if cavern_image_url is null

3. **Integration Test** — Client WebSocket receives and renders cavern PNG
   - Start server with procedural dungeon loaded
   - Connect client and init game state message
   - TacticalGridRenderer must render the image
   - Verify OTEL span on server side (GM panel visibility)

## Related References

- **ADR-096:** Cavern Renderer Revival — Pre-Rendered Cellular Caverns for Tactical Maps
- **ADR-106:** Runtime Procedural Jaquaysed Megadungeon — Contiguous Edge-Expansion
- **ADR-090:** OTEL Dashboard Restoration after Python Port
- **ADR-082:** Port `sidequest-api` from Rust back to Python
- **Epic 52 Context:** `/Users/slabgorb/Projects/oq-2/sprint/context/context-epic-52.md`

## Branches

- **UI:** `feat/52-5-tactical-grid-runtime-cavern-image-wiring` (from develop)
- **Server:** `feat/52-5-tactical-grid-runtime-cavern-image-wiring` (from develop)