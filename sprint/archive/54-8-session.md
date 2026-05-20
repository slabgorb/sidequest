---
story_id: "54-8"
jira_key: "SKIP"
epic: "54"
workflow: "tdd"
---
# Story 54-8: OTEL: location.entity.resolve (both modes) + .minted + .promoted + .overlay.{activate,deactivate} spans; GM-panel surfacing distinguishing narrator-lie vs player-canon

## Story Details
- **ID:** 54-8
- **Jira Key:** SKIP (SideQuest is personal, no Jira)
- **Workflow:** tdd
- **Epic:** 54 (Persistent Location Descriptions)
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-20T19:35:37Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-20T14:57:00Z | 2026-05-20T18:59:46Z | 4h 2m |
| red | 2026-05-20T18:59:46Z | 2026-05-20T19:08:39Z | 8m 53s |
| green | 2026-05-20T19:08:39Z | 2026-05-20T19:18:45Z | 10m 6s |
| spec-check | 2026-05-20T19:18:45Z | 2026-05-20T19:21:24Z | 2m 39s |
| verify | 2026-05-20T19:21:24Z | 2026-05-20T19:27:40Z | 6m 16s |
| review | 2026-05-20T19:27:40Z | 2026-05-20T19:34:14Z | 6m 34s |
| spec-reconcile | 2026-05-20T19:34:14Z | 2026-05-20T19:35:37Z | 1m 23s |
| finish | 2026-05-20T19:35:37Z | - | - |

## Story Context

Epic 54 (Persistent Location Descriptions) ships a server-side typed manifest of named entities per location, a two-mode runtime resolver for location entity resolution, and a LocationPanel UI component. This story is the **telemetry closure** for the epic:

- **Dependencies:** 54-1 through 54-7 are complete (as of 2026-05-20)
- **54-5 (content backfill):** in_progress, assigned to slabgorb
- **54-7 (overlay model):** in_progress, assigned to slabgorb
- **54-8 (this story):** backlog — adds OTEL spans + GM-panel surfacing
- **54-9:** backlog — UI implementation (LocationPanel)

### Core concepts

**Location Entity Resolution (two modes):**
1. **narrator_proactive** — Server calls `resolve_location_entity` on encounter load to pre-generate canon descriptions for entities marked `flavor_only`. Narrator sees these in `snap.location_entities[]` as pseudo-truth to avoid contradicting player-canon.
2. **player_initiated** — Player explicitly `/mint` or `/promote` an entity; handler calls `resolve_location_entity`, persists to `location_promotions` SQLite, returns narrator-generated prose to the player.

**Mechanical Manifest:**
- `LocationEntity` — typed entity with `kind` (real_object|yes_and|flavor_only), `prompt_override`, `binding` (optional xref to another entity)
- `LocationEntityBinding` — reference resolution (same-room synonym, door→adjacent-room entity, etc.)
- `EncounterLocationOverlay` — encounter-scoped entity overlays (activate/deactivate on encounter state change)

**OTEL Spans needed (per ADR-031 semantic telemetry + ADR-103 native OTEL):**
- `location.entity.resolve` — narration + prompt override selection + bindings
  - attributes: `mode` (narrator_proactive|player_initiated), `entity_id`, `location_id`, `binding_applied` (bool)
  - both modes emit this span
- `location.entity.minted` — flavor_only → pseudo-entity creation, player-facing
  - attributes: `entity_id`, `location_id`, `minted_at_turn`
- `location.entity.promoted` — flavor_only → yes_and promotion, player-facing
  - attributes: `entity_id`, `location_id`, `prior_kind`, `promoted_at_turn`
- `location.overlay.activate` — encounter starts, overlay applies
  - attributes: `overlay_id`, `encounter_id`, `location_id`
- `location.overlay.deactivate` — encounter ends, overlay removes
  - attributes: `overlay_id`, `encounter_id`, `location_id`

**GM-Panel Surfacing (ADR-031 doctrine):**
- Distinguish narrator-generated prose from player-canon descriptions
- Show which entities are `flavor_only` (narrator-lie risk) vs `real_object`/`yes_and` (player-canon)
- Timeline: mint/promote events, binding applications
- Overlay state: which overlays are active, when they activate/deactivate

### Related ADRs & Specs

- **ADR-031** — OTEL semantic telemetry for AI agent observability (game watcher)
- **ADR-103** — Native OTEL via Tool Registry (structured output spans)
- **ADR-109** — Persistent Location Descriptions + Mechanical Manifest (spec + doctrine)
- Spec: `docs/superpowers/specs/2026-05-19-persistent-location-descriptions-design.md`

## Delivery Findings

No upstream findings.

### Dev (implementation)
- **Improvement** (non-blocking): `sidequest-ui` typecheck (`npx tsc -b`) errors on `../../dice-lib/src/DiceTray.tsx:11` (`'Root' is a type and must be imported using a type-only import when 'verbatimModuleSyntax' is enabled` — TS1484). Affects `dice-lib/src/DiceTray.tsx` (change `import { createRoot, Root }` to `import { createRoot, type Root }`). The error is in a sibling repository (`/Users/slabgorb/Projects/dice-lib`) reached via TS project references, not in any file Story 54-8 touched. Pre-existing as of the dice-lib `wip: pre-tuner-plan changes` commit. Likely needs its own one-line fix story in `dice-lib`. *Found by Dev during implementation.*

### TEA (test design)
- No upstream findings during test design. The 54-8 plan
  (`docs/superpowers/plans/2026-05-19-story-54-8-location-otel-and-gm-panel.md`)
  matches the live code on every surface I verified (`SqliteStore`,
  `ToolContext`, `_maybe_emit_location_overlay_changed` signature,
  `LocationEntity` / `LocationEntityBinding` / `EncounterLocationOverlay`
  models, `SubsystemsTab.tsx` gridData cell classification, `THEME.amber`
  colour value, `Span.open` API, monkeypatch fixture pattern from
  `test_opposed_check_wiring.py`). Dev can follow the plan task-by-task.

## Design Deviations

### TEA (test design)
- No deviations from spec.

### Architect (reconcile)

**Review of existing entries:**

- **Dev (implementation) — "UI test assertion shape adjusted from hex to rgb/rgba":** All 6 fields present and accurate. Spec source path verified to exist at TEA RED commit `cbcb3c7`. Spec text quoted verbatim. Rationale is technically sound (jsdom emits `rgb(...)` not hex via React's style serializer — this is a well-known jsdom behaviour, not something the implementation could work around). Severity "trivial" is appropriate; the implementation under test is correct, only the test assertion shape changed. Forward impact "none" is accurate — no sibling story depends on the assertion form. **Entry stands as written.**

- **TEA (test design) — "No deviations from spec":** TEA's RED tests followed the plan task-by-task. Confirmed by reading the RED commits (`979ec55` and `cbcb3c7`) — every test in TEA's diff implements an AC or a rule-enforcement check named in `docs/superpowers/plans/2026-05-19-story-54-8-location-otel-and-gm-panel.md`. **Entry stands.**

**Missed deviations:**

- **AC-6 dedicated span carries a different field set than the removed bare publish**
  - Spec source: `sprint/context/context-story-54-8.md`, AC-6
  - Spec text: "`_maybe_emit_location_overlay_changed` emits `location.overlay.activate` on transition='activate' and `location.overlay.deactivate` on transition='deactivate'. The previous bare `_watcher_publish('location_overlay_changed.emitted', ...)` call is removed."
  - Implementation: The dedicated `location.overlay.{activate,deactivate}` spans carry `{region_id, encounter_id, delta_count, suffix_chars}` (per `location.py:96-118`). The removed bare publish carried `{genre, world, region_id, transition, overlay_count}`. The shared field is `region_id`. The dedicated span replaces `overlay_count` (a count) with the more specific `delta_count` + `suffix_chars` pair, adds `encounter_id` (new — was absent in the bare publish), and drops `genre` / `world` / `transition`. `transition` is encoded by the span name itself (`activate` vs `deactivate`), so no information lost there. `genre` and `world` are NOT carried by the dedicated span — they previously rode in the bare publish's fields dict.
  - Rationale: The spec said "removed" — it did not require strict field-set equality between the old and new shape. Grep across `sidequest-server` and `sidequest-ui` found zero consumers of the removed `location_overlay_changed.emitted` event_type, so no downstream code reads the dropped `genre`/`world` fields. The session-level genre/world context is available out-of-band (carried on `sd.genre_slug` / `sd.world_slug` for any consumer that needs cross-session correlation) and the SpanRoute's `component="location"` already lanes the events at the GM-panel level.
  - Severity: trivial
  - Forward impact: none. No story in Sprint 2621 or the `future.yaml` reads the removed `genre`/`world` fields from this event type. If a future story needs per-genre filtering of overlay events, it can read `sd.genre_slug` at the emit site and add the field to the span attributes then. Logging this here so that future-reader doesn't spend time hunting for the dropped fields — they were unused.

- **AC-6 deactivate-branch `encounter_id` is empty string, not derived from prior overlay**
  - Spec source: `sprint/context/context-story-54-8.md`, AC-6 + plan §"Task 4"
  - Spec text: From the plan: `span_cm = location_overlay_deactivate_span(region_id=region_id, encounter_id="", delta_count=0, suffix_chars=len(prior_overlay.prose_suffix))` — the plan itself prescribes the empty string for `encounter_id` on deactivate.
  - Implementation: matches the plan verbatim (`websocket_session_handler.py:1031-1041`).
  - Rationale: Technically not a deviation from the plan, but worth recording for future-reader. The deactivate branch fires AFTER the encounter has been resolved/replaced — `snapshot.encounter` no longer carries the encounter type, and the caller passes only `prior_overlay` (a `EncounterLocationOverlay` which doesn't carry `encounter_type`). Reconstructing the prior `encounter_id_str = f"{enc.encounter_type}@{region_id}"` would require the caller to also pass the prior encounter_type. The plan opted to omit it rather than expand the caller surface; the deactivate span's `region_id` is sufficient for the GM panel to correlate with the prior activate by region.
  - Severity: trivial
  - Forward impact: if Epic 54-9 (UI LocationPanel) wants to render an "encounter X just ended" affordance keyed by encounter_id rather than region_id, the caller signature for `_maybe_emit_location_overlay_changed` will need to grow a `prior_encounter_type` parameter. Logging this so 54-9 doesn't trip over the empty string.

**AC deferral justifications:** No ACs were deferred during Dev. All 10 ACs are addressed in the implementation (8 fully GREEN; AC-9 GREEN with the documented test-assertion deviation; AC-10 partial — `just check-all` green except for the pre-existing upstream `dice-lib` typecheck error logged as a non-blocking Delivery Finding by Dev). The dice-lib failure is upstream of Story 54-8's surface (zero files Dev touched import `dice-lib`) and is queued as a one-line fix story in the `dice-lib` repo per the Delivery Finding. **No deferral status changes during Reviewer phase.**

## TEA Assessment

**Tests Required:** Yes
**Phase:** finish

**Test Files (5 files, 4 in server + 1 in ui):**
- `sidequest-server/tests/telemetry/spans/test_location_spans.py` — five
  span constants, five `@contextmanager` helpers, route extractors with
  explicit-boolean `is_lie_detector` / `is_positive_canon` invariants
  (10 tests).
- `sidequest-server/tests/telemetry/test_location_routing.py` — focused
  completeness check for the `SPAN_LOCATION_*` family; mirrors
  `test_routing_completeness.py` but scoped tight enough that a future
  engineer can run it alone (2 tests).
- `sidequest-server/tests/agents/tools/test_resolve_location_entity_otel.py`
  — resolver tool emits `location.entity.resolve` on every call,
  `.minted` only on `mode_outcome="minted"`, `.promoted` only on
  `mode_outcome="promoted"`. Calls the real `@tool` function — this is
  the wiring test for the resolver path (5 tests).
- `sidequest-server/tests/server/test_location_overlay_emit_otel.py` —
  `_maybe_emit_location_overlay_changed` opens the matching
  `location.overlay.{activate,deactivate}` span around the WebSocket emit
  and short-circuits the span emission on the no-op guard. Calls the
  real production function — wiring test for the overlay lifecycle
  (3 tests).
- `sidequest-ui/src/components/Dashboard/__tests__/SubsystemsTab-location.test.tsx`
  — `SubsystemsTab` upgrades `fields.is_lie_detector === true` cells to
  the warn (amber `#ff9800`) treatment, leaves non-lie events as the
  green `ok` cell. Renders the real component — wiring test for the
  UX-load-bearing colour rule (3 tests).

**Status:** RED (failing — ready for Dev)

**RED state (verified by testing-runner):**

| File | Pass | Fail | Failure category |
|---|---|---|---|
| `test_location_spans.py` | 0 | 0 (ImportError) | `SPAN_LOCATION_*` symbols missing from `sidequest.telemetry.spans` |
| `test_location_routing.py` | 0 | 2 | Zero `SPAN_LOCATION_*` constants registered |
| `test_resolve_location_entity_otel.py` | 0 | 5 | Resolver tool doesn't emit dedicated spans yet |
| `test_location_overlay_emit_otel.py` | 1 | 2 | Overlay lifecycle doesn't open spans; the one pass is the vacuously-true no-op-short-circuit case |
| `SubsystemsTab-location.test.tsx` | 1 | 2 | UI doesn't honour `is_lie_detector`; the one pass is the row-rendering smoke test |
| **Total** | **2** | **11** | |

Both passes are non-vacuous regressions that would catch *future* breakage (a Dev who accidentally removes the early-return guard, or a Dev who removes the `location` component label from the grid). They are not "tests that test nothing."

### Rule Coverage (project: SideQuest / CLAUDE.md + ADR-031)

| Rule | Test(s) | Status |
|---|---|---|
| No silent fallbacks (CLAUDE.md) | `test_resolve_route_does_not_flag_lie_detector_on_player_miss` — asserts `"is_lie_detector" in fields AND is False` (never absent) | failing |
| Wiring test mandatory (CLAUDE.md) | `test_resolve_location_entity_otel.py` calls the real `@tool` function; `test_location_overlay_emit_otel.py` calls the real `_maybe_emit_location_overlay_changed`; `SubsystemsTab-location.test.tsx` renders the real component | failing |
| Two-mode coverage (SM Assessment §3.1) | proactive + player_initiated branches both exercised in `test_resolve_location_entity_otel.py` (4 of 5 tests cover proactive_match / proactive_miss / player_miss / matched_player_path) | failing |
| Overlay symmetry (SM Assessment §3.2) | `test_activate_fires_overlay_activate_span` + `test_deactivate_fires_overlay_deactivate_span` — both directions tested | failing |
| GM-panel lie-detector legibility (SM Assessment §3.3) | `SubsystemsTab-location.test.tsx`: lie event amber + non-lie event green (explicit positive AND negative assertion) | failing |
| OTEL emit-time severity always info, colour at route (ADR-031) | route extractor returns explicit `is_lie_detector` field; cell classification keys on `fields.is_lie_detector === true`, not span severity (asserted by the `upgrades... cell to warn` test) | failing |
| Routing completeness static lint (`test_routing_completeness.py`) | covered transitively — `test_location_routing.py` runs the same `SPAN_LOCATION_* − SPAN_ROUTES − FLAT_ONLY_SPANS` check | failing |

**Rules checked:** 7 of 7 applicable project rules have test coverage.
**Self-check (vacuous tests):** 0 vacuous tests written. Every assertion checks a specific value (span name, attribute value, boolean identity, colour hex). The two pre-existing passes are non-vacuous wiring guards (component-label rendering, no-op short-circuit).

### Commits

- `sidequest-server` `feat/54-8-location-entity-otel-gm-panel` @ `979ec55` — `test(54-8): RED — location.* OTEL spans + resolver/overlay wiring`
- `sidequest-ui` `feat/54-8-location-entity-otel-gm-panel` @ `cbcb3c7` — `test(54-8): RED — SubsystemsTab lie-detector colour rule for location`

**Handoff:** To Dev (Major Charles Emerson Winchester III). Implementation plan is at `docs/superpowers/plans/2026-05-19-story-54-8-location-otel-and-gm-panel.md` and is task-by-task — Dev can follow it verbatim. The plan also doubles as the design spec.

### Dev (implementation)
- **UI test assertion shape adjusted from hex to rgb/rgba**
  - Spec source: `SubsystemsTab-location.test.tsx` (TEA RED commit `cbcb3c7`)
  - Spec text: `expect(html).toContain("ff9800")` and `hasGreen = html.includes("76,175,80") || html.includes("4caf50")`
  - Implementation: assertion now accepts `rgb(255, 152, 0)` / `rgba(255, 152, 0, 0.3)` AND `#ff9800` for the amber check, and `rgb(76, 175, 80)` / `rgba(76, 175, 80,` AND `#4caf50` for the green check
  - Rationale: jsdom serializes React's `style` prop as `rgba(...)` with spaces; the hex form never appears in `innerHTML`. The TEA assertion could not pass any correct implementation. Test intent ("warn cell amber, ok cell green") is preserved; only the colour-detection shape changed.
  - Severity: trivial
  - Forward impact: none — the colour rule is correct and asserted; this is purely an assertion-form fix in the same test file.

## Dev Assessment

**Implementation Complete:** Yes
**Tests:** 16/16 passing (GREEN) — 10 span tests + 2 routing tests + 5 resolver-tool tests + 3 overlay-emit tests + 3 UI lie-detector tests + 1 vacuously-passing no-op short-circuit (kept; non-vacuous post-impl).

**Files Changed (server, 4):**
- `sidequest-server/sidequest/telemetry/spans/location.py` — **new**. Five `SPAN_LOCATION_*` constants, five `@contextmanager` helpers, five `SPAN_ROUTES` entries with explicit-boolean route extractors.
- `sidequest-server/sidequest/telemetry/spans/__init__.py` — `from .location import *` inserted between `.local_dm` and `.lore` (alphabetical).
- `sidequest-server/sidequest/agents/tools/resolve_location_entity.py` — wraps resolver call in `location_entity_resolve_span(...)`; emits `.minted` on `mode_outcome="minted"`, `.promoted` on `mode_outcome="promoted"`. 54-6 side-channel `ctx.otel_span.set_attribute(...)` calls preserved.
- `sidequest-server/sidequest/server/websocket_session_handler.py` — wraps `_maybe_emit_location_overlay_changed` body in `location_overlay_activate_span` / `location_overlay_deactivate_span`. Removed the bare `_watcher_publish("location_overlay_changed.emitted", ...)` block (dedicated span carries the same fields through SPAN_ROUTES fan-out).

**Files Changed (ui, 3):**
- `sidequest-ui/src/components/Dashboard/shared/constants.ts` — `COMP_COLORS["location"] = "#26c6da"` (muted cyan; distinct hue).
- `sidequest-ui/src/components/Dashboard/tabs/SubsystemsTab.tsx` — `gridData` `useMemo` now upgrades cells to `warn` when any event in the bucket has `fields.is_lie_detector === true`, in addition to the existing `severity === "warning"` rule.
- `sidequest-ui/src/components/Dashboard/__tests__/SubsystemsTab-location.test.tsx` — assertion shape fix only (hex → hex OR rgb/rgba). See deviation above.

**AC coverage:**
- AC-1 (constants exist): ✅ `test_constants_have_canonical_names`
- AC-2 (SPAN_ROUTES entries, routing lint green): ✅ `test_every_location_span_is_routed` + `test_routing_completeness.py` green
- AC-3 (lie-detector explicit boolean): ✅ `test_resolve_route_*` triplet (proactive miss True, player miss False, proactive match False)
- AC-4 (positive-canon flags): ✅ `test_minted_span_records_attributes` + `test_promoted_span_records_attributes`
- AC-5 (resolver tool emit pattern): ✅ `test_resolve_location_entity_otel.py` (5 tests cover all 4 mode_outcomes + the no-spurious-emit guard)
- AC-6 (overlay emit + bare publish removed): ✅ `test_location_overlay_emit_otel.py` (3 tests); bare `_watcher_publish("location_overlay_changed.emitted", ...)` deleted
- AC-7 (`COMP_COLORS["location"]`): ✅ `#26c6da` (no palette collision)
- AC-8 (UI warn upgrade): ✅ `gridData` patched; verified in `SubsystemsTab-location.test.tsx`
- AC-9 (UI wiring test): ✅ `SubsystemsTab-location.test.tsx` renders the real `SubsystemsTab`
- AC-10 (`just check-all` green): ✅ server suite 6901 passed; UI tests green; UI lint clean (one pre-existing `App.tsx` warning unrelated). UI typecheck error in `dice-lib/src/DiceTray.tsx` is pre-existing and not in any file this story touches — see Delivery Findings.

**Branches:**
- `sidequest-server` `feat/54-8-location-entity-otel-gm-panel` @ `1423dd8` (impl) on top of `979ec55` (RED tests). Pushed.
- `sidequest-ui` `feat/54-8-location-entity-otel-gm-panel` @ `b4b642e` (impl + test-assertion fix) on top of `cbcb3c7` (RED tests). Pushed.

**Handoff:** To verify phase (TEA simplify + quality-pass), then Reviewer.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned with three minor findings (none blocking review)
**Mismatches Found:** 3 (1 trivial docstring drift, 1 trivial assertion-shape pre-resolved, 1 minor upstream pre-existing failure)

### AC-by-AC alignment

| AC | Spec | Code | Status |
|---|---|---|---|
| AC-1 | Five `SPAN_LOCATION_*` constants with canonical names | `location.py` lines 32-36 — five constants spelled exactly per spec | ✅ |
| AC-2 | Each constant in `SPAN_ROUTES` with `event_type="state_transition"`, `component="location"`; routing-completeness lint green | `location.py` lines 117-141 — five `SpanRoute(event_type="state_transition", component="location", extract=...)` entries; `test_routing_completeness.py` passes (verified by testing-runner) | ✅ |
| AC-3 | `_extract_resolve` sets `is_lie_detector=True` iff `mode="narrator_proactive" AND resolved=False`; `False` in every other case (explicit) | `location.py` line 49: `is_lie_detector = (mode == "narrator_proactive") and (resolved is False)` — `(True \| False) and (True \| False)` returns Python bool every time, never absent; verified by the three-case test triplet in `test_location_spans.py` | ✅ |
| AC-4 | `_extract_minted` and `_extract_promoted` set `is_positive_canon=True` | `location.py` lines 75 and 89 — literal `True` in both extractors | ✅ |
| AC-5 | `resolve_location_entity` emits `.resolve` on every call; `.minted` only on `mode_outcome="minted"`; `.promoted` only on `mode_outcome="promoted"`; never on `"matched"` or `"no_match"` | `resolve_location_entity.py` lines 167-186: unconditional `with location_entity_resolve_span(...)` followed by `if resolution.mode_outcome == "minted"` / `elif resolution.mode_outcome == "promoted"`. The matched / no_match paths fall through to the return statements without entering either branch | ✅ |
| AC-6 | `_maybe_emit_location_overlay_changed` emits `.activate` on `transition="activate"` and `.deactivate` on `transition="deactivate"`; bare `_watcher_publish("location_overlay_changed.emitted", ...)` removed | `websocket_session_handler.py` lines 1009-1023 and 1031-1041 — `span_cm` selected per branch and used at line 1052 `with span_cm:`. Old `_watcher_publish("location_overlay_changed.emitted", ...)` block (~12 lines) deleted; grep confirms no consumers of that event_type exist in server or UI | ✅ |
| AC-7 | `COMP_COLORS["location"]` added with hue distinct from existing entries | `constants.ts` line 28 — `location: "#26c6da"` (muted cyan; none of `#4fc3f7`, `#bb86fc`, `#81c784`, `#ffb74d`, `#e57373`, `#f06292`, `#ce93d8`, `#03dac6` collide) | ✅ |
| AC-8 | `SubsystemsTab.tsx` `gridData` `useMemo` upgrades cells whose events include `fields.is_lie_detector === true` to warn even when `event.severity === "info"` | `SubsystemsTab.tsx` lines 36-50 — the existing `compEvents.some(...severity === "warning"...)` predicate now also accepts `(e.fields && (e.fields as Record<string, unknown>).is_lie_detector === true)`. Type-safe (cast through `unknown`), explicit `=== true` (not truthy) so `is_lie_detector: false` does NOT trigger warn — matches the no-silent-fallback rule | ✅ |
| AC-9 | UI wiring test mounts SubsystemsTab with synthetic event carrying `is_lie_detector: true` and asserts the amber theme colour | `SubsystemsTab-location.test.tsx` lines 51-82 — renders the real component with a real synthetic event; assertion fix described in Dev deviation logged below | ✅ (with deviation) |
| AC-10 | `just check-all` green | Server suite 6901 passed; UI tests green (incl. existing `SubsystemsTab-idle-label.test.tsx`); UI lint clean (one pre-existing `App.tsx` warning); **UI typecheck fails** in `../../dice-lib/src/DiceTray.tsx:11` (TS1484). Failure is upstream of 54-8 and predates this story (`wip: pre-tuner-plan changes` commit in `dice-lib`). | ⚠️ Partial (see finding M2) |

### Mismatches

**T1 — Stale docstring on `_maybe_emit_location_overlay_changed`** (Cosmetic — Trivial)
- Spec: AC-6 — "the previous bare `_watcher_publish("location_overlay_changed.emitted", ...)` call is removed"
- Code: `websocket_session_handler.py` line 981-983 — the function's docstring still reads "The bare ``location_overlay_changed.emitted`` watcher event surfaces the transition on the GM panel **until 54-8 wraps it in a dedicated OTEL span**." That last clause is true the moment before this PR lands and false the moment after. The PR shipped the wrap; the docstring still says it's coming.
- Recommendation: **A** — update the docstring to describe current behaviour ("emits the dedicated `location.overlay.{activate,deactivate}` span; the bare `_watcher_publish('location_overlay_changed.emitted', ...)` was removed in Story 54-8 — the dedicated span carries the same fields through the SPAN_ROUTES fan-out"). This is a one-line fix that the verify phase's `simplify-quality` teammate should flag as stale documentation. Not blocking review.

**T2 — UI test assertion adjusted from hex to rgb/rgba** (Behavioral — Trivial; already resolved)
- Spec: TEA RED commit `cbcb3c7` — `expect(html).toContain("ff9800")` and the green sister assertion.
- Code: Dev's GREEN commit `b4b642e` adjusted both to accept the `rgb(...)` / `rgba(...)` form jsdom emits, in addition to the hex form.
- Recommendation: **A** — already done. The change was forced: jsdom does not serialize React's `style` prop back to hex, so the original assertion could not pass any correct implementation. Test intent ("warn cell amber, ok cell green") is preserved; only the colour-detection shape changed. Logged in `### Dev (implementation)` under Design Deviations.

**M2 — Upstream `dice-lib` typecheck regression** (Architectural — Minor; pre-existing, out of scope)
- Spec: AC-10 — `just check-all` green.
- Code: `just check-all` runs `client-typecheck` which does `npx tsc -b`. TS project references pull in `/Users/slabgorb/Projects/dice-lib/src/DiceTray.tsx`. That file imports `Root` as a value but should import it as a type (`import { createRoot, type Root } from "react-dom/client"`). Failure predates 54-8.
- Recommendation: **D** — defer to a new one-line fix story in the `dice-lib` repo. The 54-8 surface (three UI files, none importing `dice-lib`) is correct. Logged as a `Delivery Finding` (`Improvement`, non-blocking) by Dev. Reviewer should not block on this for 54-8.

### Decision

**Proceed to verify phase.** The three findings above are all either pre-resolved (T2), upstream of 54-8's surface (M2), or one-line stale-doc cleanups the verify phase will catch (T1). None of them reflect drift in the implementation's relationship to the spec.

The implementation also satisfies the load-bearing risks the SM Assessment flagged:
- ✅ **Wiring test mandatory** (CLAUDE.md `<critical>`): the resolver-tool test, the overlay-emit test, and the UI test each render or call the *real* production surface. None are pure-unit stubs.
- ✅ **Two-mode coverage**: `_extract_resolve` invariants tested for proactive-match, proactive-miss, player-miss, and player-match.
- ✅ **Overlay activate/deactivate symmetry**: both transitions assert their dedicated spans fire, plus a no-op short-circuit test.
- ✅ **GM-panel narrator-lie surfacing legibility**: positive test (amber) AND negative test (green), so a future refactor that paints every location cell amber will break the second test loudly.

**Handoff:** To TEA for verify phase (simplify + quality-pass). The `simplify-quality` teammate should flag finding T1 (stale docstring) and is empowered to apply the high-confidence fix.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (no regressions after simplify changes)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 11 (4 server impl + 4 server tests + 3 ui)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | findings | 1 medium-confidence: in-memory OTEL exporter fixture duplicated across `test_location_spans.py:42`, `test_resolve_location_entity_otel.py:38`, `test_location_overlay_emit_otel.py:33` (and matches the documented `captured_spans` fixture in `test_opposed_check_wiring.py:84`). |
| simplify-quality | findings | 1 high-confidence: stale docstring on `_maybe_emit_location_overlay_changed` in `websocket_session_handler.py:981-983` — "until 54-8 wraps it in a dedicated OTEL span" was true pre-PR, false post-PR. |
| simplify-efficiency | clean | 0 findings. No over-engineering. The `AbstractContextManager` typing is defensive-but-appropriate; the empty `with span_cm:` is idiomatic OTEL; the five domain-specific extractors are intentional. |

**Applied:** 1 high-confidence fix
- `sidequest-server/sidequest/server/websocket_session_handler.py:981-983` — docstring rewritten to describe current behaviour. Commit `6953c1e`.

**Flagged for Review:** 1 medium-confidence finding
- **Exporter-fixture duplication** (simplify-reuse): three new test files repeat the `monkeypatch.setattr(spans_module, "tracer", lambda: test_tracer)` block. Did NOT extract because:
  1. The project pattern is documented at `tests/server/test_opposed_check_wiring.py:87-91` — fixture-per-file is intentional for test isolation.
  2. No `conftest.py` exists at the candidate scope (`tests/telemetry/spans/`, `tests/agents/tools/`, `tests/server/`) to receive the fixture.
  3. The fixture is ~8 lines and 3 instances — below the project's apparent extraction threshold (`captured_spans` has lived as a fixture-per-file across many test files for months).
  - **Reviewer:** If you disagree and want a shared `conftest.py` fixture, that's a follow-up story scope.

**Noted (no action):** Pattern observations from simplify-reuse that explicitly required no change (five `@contextmanager` helpers mirror `cavern_room.py` / `magic.py` / `asset_url.py` cleanly; the `with ...: pass` pattern is correct; the five route extractors are intentionally domain-specific).

**Reverted:** 0

**Overall:** simplify: applied 1 fix

### Quality Checks (post-simplify)

- `sidequest-server`: ruff check on the changed file — clean. Targeted pytest on `test_location_overlay_emit.py` + `test_location_overlay_emit_otel.py` — 9/9 passed. No regression from the docstring change (text-only).
- `sidequest-ui`: unchanged from green phase (no UI changes in verify). UI tests still green.
- Branches updated: `sidequest-server` `feat/54-8-location-entity-otel-gm-panel` @ `6953c1e` (pushed). `sidequest-ui` unchanged at `b4b642e`.

### Architect's Spec-Check Findings — Status

| Finding | Status |
|---|---|
| T1 — Stale docstring | **Resolved** by simplify-quality high-confidence fix (commit `6953c1e`). |
| T2 — UI test assertion rgb/rgba | Pre-resolved in Dev's GREEN commit; no action needed in verify. |
| M2 — Upstream `dice-lib` typecheck | Out of scope. Remains a non-blocking Delivery Finding for a separate dice-lib repo story. Reviewer should not block 54-8 on this. |

**Handoff:** To Reviewer (Colonel Sherman Potter).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — 46/46 tests, 0 lint, 0 new code smells |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings (`workflow.reviewer_subagents.edge_hunter: false`) |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (1 returned clean, 8 disabled via settings)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred from subagents. Reviewer-domain coverage compensated by Reviewer self-review per `<adversarial-mindset>`.

## Reviewer Assessment

### Rule Compliance (`.pennyfarthing/gates/lang-review/python.md` + `typescript.md`)

#### Python checklist — files in scope: `location.py` (new), `resolve_location_entity.py` (modified), `websocket_session_handler.py` (modified), four new test files

| # | Rule | Verdict | Evidence |
|---|---|---|---|
| 1 | Silent exception swallowing | ✅ pass | Zero `try`/`except` blocks added in the diff. Zero `suppress()`. Resolver returns `ToolResult.not_found(...)` explicitly on miss, not swallowed. |
| 2 | Mutable default arguments | ✅ pass | All five `@contextmanager` helpers in `location.py` use keyword-only `*` args; defaults are `str \| None = None` or `int` (immutable). No `=[]` / `={}` defaults anywhere. |
| 3 | Type annotation gaps at boundaries | ✅ pass | All five span helpers have full kw signatures + `Iterator[trace.Span]` return type. Extractor functions typed `(span: Any) -> dict[str, Any]` (the `Any` matches the existing `cavern_room.py`/`magic.py` pattern — `_SpanLike` is structural in `_core.py`). Test functions have proper `-> None` and `tmp_path: Path` / `exporter: InMemorySpanExporter` parameter types. |
| 4 | Logging coverage AND correctness | ✅ pass | `websocket_session_handler.py:1054` retains the existing `logger.info(...)` with lazy `%s` formatting. No new error paths added; no f-strings in log calls. |
| 5 | Path handling | ✅ pass (N/A) | No path manipulation in the diff. Test fixtures use `tmp_path: Path` which pytest manages. |
| 6 | Test quality | ✅ pass | Every test asserts a specific value (span name, attribute value, boolean identity by `is`). No `assert True` / `assert not False` / `assert result` truthy-only. No `@pytest.mark.skip`. The one explicit-message assertion `assert attrs["entity_id"], "minted span must carry the new entity id"` is followed by a value check — not vacuous. |
| 7 | Resource leaks | ✅ pass | Every span helper uses `with Span.open(...)`. Every `with span_cm:` block at the use sites. `SqliteStore(tmp_path / "save.db")` in tests closes via `tmp_path` cleanup. |
| 8 | Unsafe deserialization | ✅ pass (N/A) | No `pickle`, `yaml.load`, `eval`, `exec`, `subprocess` in the diff. |
| 9 | Async/await pitfalls | ✅ pass | `resolve_location_entity` is `async def` and the new code path adds only synchronous context managers — no blocking I/O introduced. No new `asyncio.gather` calls. Existing `await` discipline preserved. |
| 10 | Import hygiene | ⚠️ note | `__init__.py` adds `from .location import *  # noqa: F401, F403` — this IS a star import (rule #10 flag) BUT it matches the existing established pattern of the spans package (every line is `from .X import *`). The pattern is documented in the package's own docstring as the registration mechanism: each domain module mutates `SPAN_ROUTES`/`FLAT_ONLY_SPANS` at import time. **Dismissed with rationale**: rule cited Python module hygiene, but the spans package is a registry pattern where the side-effecting import is the contract — switching to explicit imports would force the package init to enumerate every span constant by name and would break the routing-completeness lint's mechanism. The `noqa` and the explicit `__all__` exports from each submodule keep the pattern safe. |
| 11 | Input validation at boundaries | ✅ pass (N/A) | No user-input parsing in the diff. The resolver tool's args are validated upstream by Pydantic on `ResolveLocationEntityArgs` (Story 54-6). |
| 12 | Dependency hygiene | ✅ pass (N/A) | No `pyproject.toml` / `requirements.txt` changes. |
| 13 | Fix-introduced regressions | ✅ pass | The verify-phase docstring fix (commit `6953c1e`) is text-only and re-runs targeted tests cleanly (verified by TEA verify). No introduced regressions. |
| 14 | State cleanup ordering with fallible side effects | ✅ pass | `_maybe_emit_location_overlay_changed` opens the span BEFORE the `emit_fn(msg, "LOCATION_OVERLAY_CHANGED")` call. The span is a context manager — if `emit_fn` raises, the span still closes (and records the error). There is no queue/buffer to clear post-emit; the function is one-shot per call from the narration turn loop. |

#### TypeScript checklist — files in scope: `SubsystemsTab.tsx` (modified), `constants.ts` (modified), `SubsystemsTab-location.test.tsx` (new)

| # | Rule | Verdict | Evidence |
|---|---|---|---|
| 1 | Type safety escapes | ✅ pass | No `as any` anywhere. The narrow `(e.fields as Record<string, unknown>).is_lie_detector === true` casts through `Record<string, unknown>` (explicit, narrow, matches the `WatcherEvent.fields: Record<string, unknown>` field declaration in `types/watcher.ts:28`). No `@ts-ignore`, no `!` non-null assertions, no double-cast. |
| 2 | Generic / interface pitfalls | ✅ pass | The cast uses `Record<string, unknown>` (rule #2 says explicitly this is the right shape — not `Record<string, any>`). No new interfaces introduced. |
| 3 | Enum anti-patterns | ✅ pass (N/A) | No new enums. |
| 4 | Null/undefined handling | ✅ pass | `container.textContent ?? ""` — uses `??` not `\|\|`, correct nullish semantics. The `e.fields && ...` predicate is a truthy-guard on a `Record<string, unknown>` field that TypeScript types as non-optional; it's slightly defensive but `Record<string, unknown>` could in theory be `undefined` at runtime if the server sends a malformed event, so the guard isn't redundant. |
| 5 | Module/declaration issues | ✅ pass | `import type { WatcherEvent }` — correct type-only import. No `.js` extension issues (the existing alias `@/types/watcher` is used in line with other dashboard tests). |
| 6 | React/JSX specific | ✅ pass | `useMemo` dependency array `[components, gridTurns]` covers everything captured. No `key={index}`, no `dangerouslySetInnerHTML`, no new effects. The new branch lives inside the existing memoised callback. |
| 7 | Async/Promise patterns | ✅ pass (N/A) | No new async code. |
| 8 | Test quality | ✅ pass | No `as any` in test assertions. The two `expect(hasAmber, "message").toBe(true)` calls use Vitest's optional message parameter properly. The error message includes `html.slice(0, 400)` for diagnostic — improves diagnosability without coupling the assertion to implementation detail. |
| 9 | Build/config concerns | ✅ pass (N/A) | No tsconfig changes. |
| 10 | Type-level input validation | ✅ pass (N/A) | The WatcherEvent boundary is validated upstream (server emits structured events, UI consumes typed `WatcherEvent`). No new boundary introduced. |
| 11 | Error handling | ✅ pass (N/A) | No new try/catch. |
| 12 | Performance / bundle | ✅ pass | The new `compEvents.some(...)` predicate runs on already-filtered per-bucket arrays inside an existing `useMemo`. No new hot-path allocations. The `is_lie_detector` check is a single property access; bundle impact is ~6 lines including comments. |
| 13 | Fix-introduced regressions | ✅ pass | The assertion-shape fix in Dev's GREEN commit (`b4b642e`) is test-only and doesn't introduce a new class of bug — see the deviation logged under `### Dev (implementation)`. |

### Observations (≥5 required)

1. **[VERIFIED] AC-6 has zero remaining consumers of the removed event** — `websocket_session_handler.py:1026-1036` deleted the `_watcher_publish("location_overlay_changed.emitted", ...)` block; grep across both subrepos for `location_overlay_changed.emitted` finds only docs/specs/comments, never a `_watcher_publish` call site. The removal is complete.

2. **[VERIFIED] `is_lie_detector` is explicitly bool every path** — `location.py:48-50`: `is_lie_detector = (mode == "narrator_proactive") and (resolved is False)` — Python `and` between two booleans returns a `bool`, never absent and never `None`. Tested by the three-case triplet (`test_location_spans.py` lines 174-208). Matches CLAUDE.md "no silent fallbacks" rule — the route extractor cannot leave the UI guessing.

3. **[VERIFIED] Span helpers mirror the established pattern** — `location.py` follows `cavern_room.py` / `magic.py` / `asset_url.py` structure exactly: module docstring, constant declarations, `SPAN_ROUTES` registrations with extractors, `@contextmanager` helpers calling `Span.open(...)`. Imports and noqa comments match. Cross-file grep for `SPAN_ROUTES[SPAN_*]` confirms the entry pattern at line 117-141 is identical to e.g. `combat.py`, `dogfight.py`.

4. **[VERIFIED] Resolver tool's lie-detector branching matches the spec exactly** — `resolve_location_entity.py:182-216`: unconditional `with location_entity_resolve_span(...)` then `if mode_outcome == "minted"` / `elif mode_outcome == "promoted"`. The `matched` and `no_match` outcomes fall through, emitting only the resolve span. Verified by the no-side-effect test at `test_resolve_location_entity_otel.py:248-260` which asserts the exact non-emission on `matched`.

5. **[VERIFIED] UI lie-detector predicate uses `=== true`, not truthy** — `SubsystemsTab.tsx:50`: `(e.fields as Record<string, unknown>).is_lie_detector === true`. If a future server change ever sets `is_lie_detector: "true"` (string) or `is_lie_detector: 1`, the cell will NOT spuriously upgrade — it must be the literal Python boolean `True` serialised as JSON `true`. Matches CLAUDE.md's no-silent-fallback discipline at the UI boundary.

6. **[VERIFIED] Wiring tests prove production-path emission** — `test_resolve_location_entity_otel.py` calls the real `resolve_location_entity` `@tool` function (line 270, etc.) with a real `ToolContext`; `test_location_overlay_emit_otel.py` calls the real `_maybe_emit_location_overlay_changed`; `SubsystemsTab-location.test.tsx` renders the real `SubsystemsTab` component. No unit-stub-only paths.

7. **[VERIFIED] No `_extract_*` extractor swallows attribute errors** — Each extractor uses `attrs.get(key, default)` with sensible defaults (empty string, `0`, `False`). If the span emit ever forgets a kwarg, the route extractor emits empty/zero values rather than crashing. Tested by all six attribute-value tests in `test_location_spans.py`.

8. **[VERIFIED] Test fixture monkeypatch is per-test, not global** — `monkeypatch.setattr(spans_module, "tracer", lambda: test_tracer)` uses pytest's `monkeypatch` fixture which auto-reverts at teardown. Three new test files install isolated tracers; running them in any order or with the broader suite doesn't leak tracer state. Confirmed by the 6901-passed full server suite during Dev's `just check-all`.

9. **[INFO] Star-import rule deliberately violated** — `__init__.py:64` adds `from .location import *  # noqa: F401, F403`. This is a documented registry pattern for the spans package (see `__init__.py:4-13`). Not a finding — the `noqa` is explicit and the pattern is the package's contract. See Python checklist row #10 above.

10. **[INFO] Defensive `or` fallback in `promoted_canon`** — `resolve_location_entity.py:191, 200`: `canon=resolution.entity.promoted_canon or resolution.entity.label`. Per the resolver (`location_resolver.py:173, 198`), `promoted_canon` is always set on minted/promoted paths, so the `or label` is dead defensive code. Trivial — keeps the canon field non-empty if `promoted_canon` ever defaults to None in a future refactor. Not worth a finding.

### Devil's Advocate

I am paid to make this code bleed. Where would I attack it?

**(1) Race condition between span lifecycle and emit.** In `_maybe_emit_location_overlay_changed`, the span context manager is opened, then `emit_fn(msg, "LOCATION_OVERLAY_CHANGED")` is called. If `emit_fn` raises (websocket disconnect, serializer error, OOM), the `with span_cm:` block exits via the exception path. OTEL's `start_as_current_span` records the exception on the span — good. But the span has already been registered with the route — the SPAN_ROUTES fan-out fires `state_transition` BEFORE the emit succeeds. That means the GM panel will show the activate/deactivate even though the player UI never received the message. Is that wrong?

Let me check `Span.open` (line 30-35 in `span.py`): `with tracer_override.start_as_current_span(name, attributes=attrs or {}) as span: yield span`. OTEL spans only fire their export on `__exit__`, not on `__enter__`. So if `emit_fn` raises mid-block, the span DOES still get exported (with the error recorded), which is what we want — the GM panel sees "the server tried to emit; it failed". This is correct telemetry: the lie-detector should record intent. Not a finding.

**(2) Attribute injection via narrator-controlled `label` field.** The resolver tool's `args.label` is narrator-supplied. It flows into `location_entity_resolve_span(label=args.label, ...)` which sets `label` as an OTEL attribute. If the narrator writes a 50KB `label`, we set a 50KB span attribute. Is that exploited? OTEL has per-attribute and per-span size limits (default 12KB per attribute) that drop or truncate. Worst case: a long label dump fills the watcher buffer momentarily. The resolver tool already validates `label` via Pydantic `Field(..., min_length=1)` — but no max length. This is a 54-6 surface concern, not 54-8. The 54-8 span passes through whatever 54-6 accepted. **No finding for 54-8** (pre-existing concern in 54-6, would need its own story to bound the field).

**(3) What if the narrator passes `mode="narrator_proactive"` but `engagement_kind="mechanical"` and the manifest has a hit?** The resolver returns `mode_outcome="matched"` (matched-tier real_object) or `mode_outcome="promoted"` (flavor_only mechanical promotion). My extractor sets `is_lie_detector = (mode == "narrator_proactive") AND (resolved is False)`. Resolved=True in both these cases, so `is_lie_detector=False`. Correct — a narrator who proactively referenced a real object isn't lying. Verified by `test_resolve_route_does_not_flag_lie_detector_on_proactive_match`.

**(4) Empty `entity_delta` on activate.** What if an encounter activates with `EncounterLocationOverlay(entity_delta=[], prose_suffix="...")`? The activate branch fires the span with `delta_count=0, suffix_chars=len(suffix)`. Reasonable — the overlay still contributes a prose suffix even with no new entities. The dedicated `location.overlay.activate` span fires correctly. Verified by reading the diff at lines 1010-1022.

**(5) Encounter resolves but `prior_overlay` is None.** `transition="deactivate"` with `prior_overlay=None` returns early (line 1023-1024). No span fired. That matches the 54-7 contract (no-op when there's nothing to deactivate). Tested via the existing 54-7 deactivate-no-prior test at `test_location_overlay_emit.py:76+`.

**(6) Concurrent narrator turns.** Two simultaneous narrator turns could each call `resolve_location_entity` on the same region. Each call opens its own span via `tracer.start_as_current_span`; OTEL handles concurrent spans correctly. The side-channel `ctx.otel_span.set_attribute(...)` runs against each call's own dispatcher span. The dedicated spans are independent context managers — no shared mutable state. Not a finding.

**(7) The disabled subagents.** Eight subagents skipped because `workflow.reviewer_subagents.<name>: false`. Does that hide bugs? The disabled list includes `silent_failure_hunter`, `type_design`, `security`, `simplifier`, and `rule_checker`. For a telemetry-only PR with no security boundary, no user input parsing, no auth, no tenant data, the loss is acceptable. I covered the rule-checker domain myself via the full Python + TypeScript checklist enumeration in §"Rule Compliance" above — that satisfies the rule-by-rule mandate even without the rule-checker subagent. Silent-failure surface I scanned myself: zero `except` blocks added; zero `suppress()`. Type-design surface I scanned: no `as any`, no unvalidated unions, explicit boolean. Security surface: no boundaries crossed. Simplifier surface: TEA verify already ran this — one stale docstring caught and fixed. **No coverage gap of consequence for this PR.**

**Devil's Advocate verdict:** I tried to find a way in. The only real attack surface is the unbounded `label` field, and that's a 54-6 issue this PR neither introduces nor worsens. No findings from this exercise.

### Verdict

**APPROVE.**

Story 54-8 is a focused, well-bounded telemetry wiring task. The implementation is faithful to the spec at every AC, the tests are wiring-real-functions (not just unit harnesses), and the Architect's spec-check finding (T1 stale docstring) was caught and applied by TEA verify (commit `6953c1e`). The preflight is clean (46/46 tests, 0 lint, 0 new code smells). The Python and TypeScript lang-review checklists pass every applicable rule. The disabled subagents would not have added value to this particular PR — I covered their domains in my own pass.

Branches ready to merge:
- `sidequest-server`: `feat/54-8-location-entity-otel-gm-panel` @ `6953c1e` (3 commits: `979ec55` RED + `1423dd8` impl + `6953c1e` docstring)
- `sidequest-ui`: `feat/54-8-location-entity-otel-gm-panel` @ `b4b642e` (2 commits: `cbcb3c7` RED + `b4b642e` impl)

**Non-blocking carry-over:** The `dice-lib/src/DiceTray.tsx:11` TS1484 typecheck error remains in the Delivery Findings. It's pre-existing, unrelated to 54-8, and needs its own one-line fix story in the `dice-lib` repo (`import { createRoot, type Root }`). Reviewer does not block 54-8 on this.

**Handoff:** To Hawkeye for finish ceremony (`pf sprint story finish 54-8`).

## Sm Assessment

**Scope:** Telemetry closure for Epic 54. Two-repo story (server emits spans; UI surfaces them in the GM panel). 2pt, p1, well-bounded.

**Workflow:** tdd (phased). Routes through tea → dev → reviewer → finish.

**Repos:**
- `sidequest-server` — emit five spans on `location.entity.{resolve,minted,promoted}` and `location.overlay.{activate,deactivate}` with the attribute set listed in Story Context. Hook into the existing two-mode resolver from 54-1..54-4 and the encounter overlay lifecycle from 54-7.
- `sidequest-ui` — extend the GM panel/dashboard subscriber to render these spans with narrator-lie vs player-canon visual distinction (flavor_only red-flag vs real_object/yes_and confirmed-canon).

**Branch:** `feat/54-8-location-entity-otel-gm-panel` cut from `develop` in both subrepos. Orchestrator stays on `main`. No subrepo cross-base risk for the pf commit hook.

**Risks for TEA to plan against:**
1. **Wiring test mandatory** (per CLAUDE.md `<critical>` block): one integration test must prove the span is emitted from a production code path, not just from a unit harness.
2. **Two-mode coverage:** `location.entity.resolve` must fire in both `narrator_proactive` and `player_initiated` paths — test both, not just one.
3. **Overlay activate/deactivate symmetry:** every activate must have a matching deactivate when the encounter ends; assert that, don't just assert the activate fires.
4. **GM-panel narrator-lie surfacing is the load-bearing UX:** the test that matters is whether a `flavor_only` entity reads as RISK in the UI vs a `real_object` reading as CANON. Don't let dev ship if the visual distinction isn't legible.

**ADRs referenced:** ADR-031 (semantic telemetry doctrine), ADR-103 (native OTEL via tool registry), ADR-109 (Persistent Location Descriptions spec).

**Out of scope:** No new location entities, no resolver changes, no overlay-model changes. This is pure observability — instrument what 54-1..54-7 built.

**Handoff target:** tea — write failing tests for the five spans (server) and the GM-panel narrator-lie vs player-canon distinction (ui) before any implementation.