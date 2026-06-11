---
story_id: "104-3"
jira_key: ""
epic: "104"
workflow: "tdd"
---
# Story 104-3: M-C — Wire lore-page Map section + NPC portrait-pin renderer (completes 100-12 dropped seam)

## Story Details
- **ID:** 104-3
- **Jira Key:** (none — Jira integration disabled)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-11T10:34:16Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-11T10:11:14+00:00 | 2026-06-11T10:12:40Z | 1m 26s |
| red | 2026-06-11T10:12:40Z | 2026-06-11T10:22:35Z | 9m 55s |
| green | 2026-06-11T10:22:35Z | 2026-06-11T10:28:01Z | 5m 26s |
| review | 2026-06-11T10:28:01Z | 2026-06-11T10:34:16Z | 6m 15s |
| finish | 2026-06-11T10:34:16Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

### TEA (test design)
- **Improvement** (non-blocking): The server map section emits `is_cluster` (104-1/M-A)
  and `dangling` (dropped adjacencies) alongside `{regions, edges, pins, starting_region}`,
  but M-C's ACs only require graph+pins. `is_cluster` single-vs-cluster branching on the
  lore Map surface and a `dangling`-edge affordance are unspecified for this story.
  Affects `sidequest-ui/src/components/reference/sections/MapSection.tsx` (Dev may pass
  these through inertly now; a follow-on story should decide the lore-surface treatment).
  *Found by TEA during test design.*
- **Gap** (non-blocking): The in-game `MapOverlay` feeds `MapState.cartography`
  (`CartographyMetadata`) which has no `pins` today, so even after CartographyMap gains
  pin rendering (AC2/AC5), the in-game graph won't *show* pins until the server populates
  pins on the in-game cartography payload. AC5 only requires the shared renderer be
  capable + used, which this story delivers; surfacing pins in-game is a separate seam.
  Affects `sidequest-server` map/cartography emission for the in-game path.
  *Found by TEA during test design.*

### Reviewer (code review)
- **Improvement** (non-blocking): The pin filter uses `pin.portrait_url !== null`, so a
  `portrait_url: ""` (type-valid `string`) would pass and render `<img src="">` — contradicting
  the component's own "no broken/empty-src image" docstring. The server never emits `""`
  (resolved-URL-or-`None`), so it's currently unreachable. Affects
  `sidequest-ui/src/components/map/CartographyMap.tsx:135` (change predicate to
  `Boolean(pin.portrait_url)`). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Portrait pins are positioned at `y = node.y - NODE_R -
  PIN_SIZE - 2`; if d3-dag places a layer-0 node at `gn.y ≈ 0` the pin's top edge sits above
  the SVG viewBox (`y ≈ -8`) and is clipped. Whether this fires depends on d3-dag's layer-0
  y-convention (unverified — could be centered at `NODE_H/2`, in which case no clip). Affects
  `sidequest-ui/src/components/map/cartographyDagLayout.ts` (bump `MARGIN`, or render pins
  below near-top nodes). **VISUALLY VERIFY in the next coyote_star/aureate_span playtest.**
  *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `portrait_url` is rendered as `<img src>` with no client-side
  origin allowlist, so a non-R2 URL (homebrew-author content error or bypassed server
  resolution) would leak a `Referer` to an external host. Pre-existing pattern (identical in
  `CastSection`), server-resolved from R2 in the normal path. A content-validation-layer
  concern, not this story's. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

### TEA (test design)
- **Defined the pin/graph DOM contract the sprint YAML left unspecified**
  - Spec source: context-story-104-3.md, "Acceptance Criteria" ("No acceptance criteria
    recorded in the sprint YAML — TEA to define"); spec addendum §5 Story M-C AC2/AC4
  - Spec text: "CartographyMap renders NPC portrait pins"; "the map section renders a
    graph (not nothing) and pins appear when portrait_url is present"
  - Implementation: Tests assert the graph via the shared CartographyMap testids
    (`map-region-graph`, `map-region-node-{id}`, `map-region-edge-{a}--{b}`), and a
    resolved pin as an accessible image NAMED by the NPC pin label
    (`getByRole("img", { name })`) with `src` = portrait_url; a null portrait_url renders
    no image.
  - Rationale: M-C left "reconcile shapes in the adapter" to the implementer. The testid
    contract is already owned by CartographyMap (100-10), and the named-image pin contract
    mirrors the Cast section's established a11y/nullable-portrait pattern — so the tests
    pin behavior the house already uses, not an invented shape.
  - Severity: minor
  - Forward impact: Dev must render resolved pins as accessible images (HTML `<img>` or
    SVG `<image role="img" aria-label>`); pin capability must live in CartographyMap (the
    shared renderer), not in MapSection, to satisfy AC2/AC5.
- **Updated an obsolete pre-existing test that pinned the dropped-seam behavior**
  - Spec source: spec addendum §3 (Correction/Completion B) + §5 M-C AC1
  - Spec text: M-C "gains `case \"map\"` → MapSection" — reversing the prior
    "map degrades to nothing" behavior.
  - Implementation: Rewrote `SectionDispatch.test.tsx`'s "renders nothing for an unknown
    section without a node" case (which used `{id:"map"}` to assert nothing rendered) to
    assert the `map` section now routes to the graph; kept a graceful-degrade test using a
    genuinely unknown node-less id (`ledger`). Updated the stale file-header comment.
  - Rationale: That test encoded the exact behavior M-C deletes; leaving it would make
    GREEN impossible (contradictory tests).
  - Severity: minor
  - Forward impact: none — the graceful-degrade guarantee is preserved via a different id.

### Dev (implementation)
- **Adapter folds adjacency/pins into the Record and lets the shared layout derive edges; server `edges`/`dangling`/`is_cluster` are not threaded through**
  - Spec source: context-story-104-3.md Problem; spec addendum §5 Story M-C AC1
  - Spec text: "adapting the server `{regions, edges, pins, starting_region}` to what
    CartographyMap consumes (… reconcile shapes in the adapter)"
  - Implementation: `MapSection.toCartography` maps the server region LIST →
    `CartographyMetadata.regions` Record (name + adjacent + pins) and sets `routes: []`.
    Graph edges are derived by the existing shared `computeCartographyDagLayout` from
    `regions[].adjacent` (deterministic, sorted-endpoint) — the server's `edges` list is
    built the same way, so it is not separately threaded. `is_cluster` and `dangling` are
    not consumed (no AC requires a lore-surface treatment yet; see TEA findings).
  - Rationale: The shared layout already owns edge derivation from adjacency (100-10);
    re-passing server `edges` would create a second, redundant edge source. The RED edge
    test (`map-region-edge-deep_root--far_landing`) asserts exactly this adjacency-derived
    behavior and passes.
  - Severity: minor
  - Forward impact: A future story wiring single-vs-cluster branching or a dangling-edge
    affordance on the lore Map surface must read `is_cluster`/`dangling` off `MapSectionData`
    (both are typed and available on the section) rather than re-deriving them.
- **Null-portrait pins render nothing (no placeholder) on the graph node**
  - Spec source: MapSection.test.tsx ("renders NO portrait image for a pin whose
    portrait_url is null"); spec addendum §5 M-C AC2
  - Spec text: "CartographyMap renders NPC portrait pins"
  - Implementation: `CartographyMap` filters pins to `portrait_url !== null` before
    rendering; an unresolved pin draws no image (unlike the Cast section's FolioPlaceholder).
  - Rationale: No test/AC requires a placeholder on a tiny graph node, and an empty/broken
    `<img>` would violate the nullable-portrait contract. Minimal, test-driven.
  - Severity: minor
  - Forward impact: none — pins gain R2 portraits as art is rendered; no schema change.

### Reviewer (audit)
- **TEA — Defined the pin/graph DOM contract** → ✓ ACCEPTED by Reviewer: the testid contract
  is owned by CartographyMap (100-10) and the named-image pin contract mirrors the Cast
  section's a11y/nullable-portrait pattern; sound, house-consistent, not an invented shape.
- **TEA — Updated the obsolete "map → nothing" test** → ✓ ACCEPTED by Reviewer: that test
  encoded the exact behavior M-C deletes; the graceful-degrade guarantee is preserved via a
  genuinely-unknown node-less id (`ledger`). Correct.
- **Dev — Adapter lets the shared layout derive edges; server `edges`/`dangling`/`is_cluster`
  not threaded** → ✓ ACCEPTED by Reviewer: the server builds `edges` from adjacency the same
  way `computeCartographyDagLayout` does (verified `_edges_and_dangling` semantics match the
  client `edgesAndDangling`), so re-passing `edges` would be a redundant second source. The
  edge test (`map-region-edge-deep_root--far_landing`) confirms parity. `is_cluster`/`dangling`
  remain typed on `MapSectionData` for the follow-on story.
- **Dev — Null-portrait pins render nothing (no placeholder)** → ✓ ACCEPTED by Reviewer:
  matches the test contract and the POI gallery-exclusion philosophy; no AC requires a
  placeholder on a graph node. (See Observation [EDGE-1] — the *filter predicate* `!== null`
  vs truthiness is a separate, non-blocking hardening note, not a deviation problem.)
- No undocumented spec deviations found. The adapter matches the server contract
  (`reference_projection.py:126`) field-for-field.

## Sm Assessment

Story 104-3 (5pt, tdd, sidequest-ui) completes the dropped seam from 100-12. The work
is purely client-side and session-free (reference SPA, no WebSocket): add a `'map'` case
to `SectionDispatch` that renders a `MapSection`, adapting the server-side payload
`{regions, edges, pins, starting_region}` into the `CartographyMap` component, with NPC
portrait pins rendered when `portrait_url` is present. Per the spec note, the same
upgraded renderer must also serve the in-game cluster graph — one component feeding both
surfaces (honors 100-10 intent).

**Scope & boundaries:** Single repo (ui), no engine/server change required — the server
payload shape already exists; this is a wiring + render task. Watch for the dual-clone
subrepo branch hazard: branch `feat/104-3-wire-lore-map-npc-portrait-pins` was cut off
`develop` in sidequest-ui, and the PR targets `develop`.

**TDD entry point for TEA (O'Brien):** The acceptance test the description calls out is
the natural RED target — a UI test asserting the lore map section renders an actual graph
(not nothing) and renders pins when `portrait_url` is present. A wiring test must confirm
`MapSection` is reachable from `SectionDispatch`'s `'map'` case, not just unit-tested in
isolation.

**No blocking findings.** Routing to TEA for the RED phase.

---
## TEA Assessment

**Tests Required:** Yes
**Reason:** N/A — this is a feature (new renderer + dispatch wiring), not a chore bypass.

**Test Files:**
- `sidequest-ui/src/components/reference/sections/__tests__/MapSection.test.tsx` (NEW) —
  10 tests covering all five M-C ACs: graph renders (AC1/AC4), one node per server region
  + adjacency edge (list→graph adaptation, AC1), portrait pin when `portrait_url` present
  (AC2/AC4), no image for null `portrait_url` (paranoia/negative), no literal
  "null"/"undefined" leak, session-free C2 render (AC3), SectionDispatch `case "map"`
  routing + ReferenceDocument end-to-end WIRING (AC1), and a direct CartographyMap pin test
  proving the pin capability lives in the shared renderer so both surfaces inherit it
  (AC2/AC5).
- `sidequest-ui/src/components/reference/sections/__tests__/SectionDispatch.test.tsx`
  (MODIFIED) — flipped the obsolete "map → nothing" test to assert the new `map` routing;
  preserved graceful-degrade via a genuinely-unknown node-less id.

**Tests Written:** 10 new (+1 modified) covering 5 ACs.
**Status:** RED — verified by testing-runner (RUN_ID 104-3-tea-red):
- MapSection.test.tsx **fails to collect** (missing `MapSection` component / `MapSectionData`
  type) — canonical house RED signal (cf. 100-10/100-11).
- SectionDispatch.test.tsx: the new `map`-routing test **fails** (`map-region-graph` absent);
  the other 7 dispatch tests still **pass** (no collateral breakage).

### Authoritative contract (pinned for Dev)
Server map section (`reference_projection.py:126`, verbatim):
`{ id:"map", label:"Map", starting_region:str, is_cluster:bool, regions:[{id,name,adjacent:[…],pins:[{slug,label,portrait_url:str|null}]}], edges:[[a,b]…], dangling:[[src,missing]…] }`.
`regions` is a **list with embedded pins** (NOT a Record) — the adapter must reconcile to
CartographyMetadata's `regions: Record<id,{name,adjacent}>` + `routes:[]`. Pin rendering
must live in **CartographyMap** (shared), driven by region-embedded `pins`.

### Rule Coverage (TypeScript lang-review checklist)

| Rule | Test(s) | Status |
|------|---------|--------|
| #4 null/undefined handling (nullable `portrait_url`) | `renders NO portrait image for a pin whose portrait_url is null` | failing (RED) |
| #6 React/JSX — no broken/empty-src `<img>`, list keys | null-portrait + per-region node tests (stable `slug`/`id` keys implied) | failing (RED) |
| #8 test quality — meaningful assertions, no `as any` | all tests assert testids/roles/attributes; no `as any` (one documented `as unknown` for the deliberately-malformed unknown-section case) | n/a (self-checked) |
| #10 input validation — typed projection at boundary | fixtures typed via `MapSectionData` (forces the type to exist) | failing (RED, type missing) |
| a11y (house Cast pattern) — portrait named by NPC | `renders an NPC portrait pin … getByRole("img",{name})` | failing (RED) |

**Rules checked:** 5 of the applicable TS checklist rules have test coverage (the rest —
async/promises, enums, modules, perf/bundle — are not exercised by this pure render+wiring story).
**Self-check:** 0 vacuous tests. Every test has a meaningful assertion; negative/paranoia
cases (null portrait, no-literal-null, graceful-degrade) included.

**Handoff:** To Dev (Julia) for GREEN — implement `MapSection` + `MapSectionData` type +
`SectionDispatch` `case "map"` + extend CartographyMap/region shape with `pins` rendering.
---
## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest-ui/src/types/reference.ts` — added `MapPin`, `MapRegion`, `MapSectionData`
  types (pinned verbatim from the server projection) and `MapSectionData` to the
  `ReferenceSection` union.
- `sidequest-ui/src/components/reference/sections/MapSection.tsx` (NEW) — adapts the
  server map section (region LIST + embedded pins) into `CartographyMetadata` and renders
  the shared `CartographyMap`.
- `sidequest-ui/src/components/reference/sections/SectionDispatch.tsx` — added
  `case "map"` → `MapSection` (completes the 100-12 dropped seam).
- `sidequest-ui/src/components/map/CartographyMap.tsx` — renders NPC portrait pins as an
  HTML `<img>` inside an SVG `<foreignObject>` (accessible by the NPC's name, `src` =
  portrait_url, only when present). The pin upgrade lives in the SHARED renderer, so both
  the lore Map surface and the in-game map inherit it (AC2/AC5).
- `sidequest-ui/src/components/map/cartographyDagLayout.ts` — carries `pins` onto each
  `DagLayoutNode`.
- `sidequest-ui/src/components/MapOverlay.tsx` — added optional `pins?: MapPin[]` to
  `CartographyRegion` (in-game cartography omits them; the lore adapter populates them).

**Tests:** 33/33 passing (GREEN) across MapSection, SectionDispatch, CartographyMap, and
MapOverlay.shared-map suites. Verified by testing-runner (RUN_ID 104-3-dev-green).
TypeScript build clean (`tsc -b` via `npm run build`); ESLint clean on all changed files.

**ACs:** AC1 (dispatch `case "map"` + adapter) ✓ · AC2 (CartographyMap portrait pins) ✓ ·
AC3 (session-free) ✓ · AC4 (graph renders + pins when portrait_url present) ✓ ·
AC5 (same shared renderer, both surfaces) ✓.

**Branch:** feat/104-3-wire-lore-map-npc-portrait-pins (pushed)

**Handoff:** To TEA (O'Brien) for the verify phase (simplify + quality-pass).

### Dev (implementation) — Delivery Findings
- No upstream findings during implementation.
---
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (33/33 green, tsc+build clean, eslint clean, 0 smells) | N/A |
| 2 | reviewer-edge-hunter | Yes | findings | 9 (2 high, 3 medium, 4 low) | confirmed 2 (non-blocking), dismissed 5 (server-guaranteed / unreachable), deferred 2 (test-coverage notes) |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | findings | 1 (low) | confirmed 1 (non-blocking, pre-existing pattern) |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (3 enabled returned; 6 disabled via `workflow.reviewer_subagents`)
**Total findings:** 3 confirmed (all non-blocking Medium/Low), 5 dismissed (with rationale), 2 deferred (test-coverage follow-ups)

### Edge-hunter finding dispositions
- **[EDGE-1] empty-string `portrait_url` passes `!== null` filter → `<img src="">`** (high conf) —
  CONFIRMED as a non-blocking Improvement (Medium). The server contract is `str | None`
  (`reference_projection.py:113` sets a resolved URL or `None`, never `""`), so it is currently
  unreachable, but it contradicts the file's own docstring. Recommended cheap fix: `Boolean(...)`.
- **[EDGE-2] top-row pin clips above viewBox (`y ≈ -8`)** (high conf) — CONFIRMED as a
  non-blocking Improvement (Medium); premise depends on d3-dag's layer-0 y-convention which I
  could not verify without rendering. Flagged for visual playtest verification.
- **[EDGE] duplicate `region.id` overwrite in `toCartography`** (med) — DISMISSED: the server's
  `regions` is a Python dict keyed by region id (`sorted(cart.regions)`), so ids are unique by
  construction; the client cannot receive duplicates.
- **[EDGE] duplicate `pin.slug` React key collision** (med) — DISMISSED as non-blocking: requires
  two slug-colliding NPC pins in one region; server `_npc_pins` derives slugs from distinct NPC
  entries. Low real-world likelihood; noted, not fixed.
- **[EDGE] dangling `starting_region`** (low) — DISMISSED: the reference Map surface does not pass
  `activeNodeId`, so an unknown starting_region is inert here; latent only for future in-game reuse.
- **[EDGE] double-assignment of `pins` in layout** (low) — DISMISSED: both reads use `?? []`;
  d3-dag does not mutate node data; no crash, cosmetic-only inconsistency that cannot manifest.
- **[EDGE] CartographyMap.test / MapOverlay.shared-map lack a direct pin test** (med/low) —
  DEFERRED as test-coverage follow-up: MapSection.test.tsx's "Shared renderer" describe already
  renders `<CartographyMap>` directly with pin data (AC5), so the shared component's pin path IS
  covered; adding a MapOverlay pin variant is a nice-to-have, not a gap that blocks.

## Rule Compliance (TypeScript lang-review checklist — exhaustive over the diff)

- **#1 type-safety escapes:** `MapSection.tsx:?` and `SectionDispatch.tsx:44` use `section as
  MapSectionData` — this is the SAME discriminated-union narrowing pattern already used for
  poi/cast/timeline (the `switch (section.id)` proves the variant), not an `as any`. No `as any`,
  no `@ts-ignore`, no non-null assertion on nullable. One `as unknown as ReferenceSection` in the
  TEST for a deliberately-malformed fixture — acceptable. COMPLIANT.
- **#2 generic/interface:** New types (`MapPin`, `MapRegion`, `MapSectionData`) are proper
  interfaces; `edges`/`dangling` typed as `[string, string][]` (tuple), not `any[]`. `pins?:
  MapPin[]` optional on `CartographyRegion`. No `Record<string, any>`/`object`/`Function`. COMPLIANT.
- **#3 enums:** None added. N/A.
- **#4 null/undefined:** `regions[id]?.pins ?? []` (layout, 2 sites) uses `??` correctly — `pins`
  is never `0`/`""`. `src={pin.portrait_url ?? undefined}` correct. The ONE imperfection is the
  pin filter `!== null` instead of truthiness ([EDGE-1]) — Medium, non-blocking. Mostly COMPLIANT.
- **#5 module/declaration:** All new imports use `import type` for type-only (`MapPin`,
  `MapSectionData`, `CartographyMetadata`); value imports (`MapSection`, `CartographyMap`) are
  runtime. No missing-extension/reference-directive issues. COMPLIANT.
- **#6 React/JSX:** No `useEffect`/hooks added. `key={pin.slug}` — stable unless slug-collision
  ([EDGE], dismissed). No `dangerouslySetInnerHTML`. `key={node.id}` already stable. COMPLIANT
  (one keying caveat noted).
- **#7 async:** No async added. N/A.
- **#8 test quality:** No `as any` in tests; assertions are meaningful (testid/role/attribute);
  negative + paranoia cases present (verified by TEA self-check + preflight). COMPLIANT.
- **#9 build/config:** No config changes; strict mode untouched; build clean. COMPLIANT.
- **#10 input validation:** `portrait_url` rendered without runtime URL validation ([SEC], Low) —
  pre-existing pattern (CastSection), non-blocking. Noted.
- **#11 error handling:** No new catch blocks. N/A.
- **#12 perf/bundle:** No barrel over-imports; `import type` keeps types out of the runtime
  bundle; no hot-path `JSON.stringify`. COMPLIANT.
- **#13 fix-regressions:** No review-fix commits yet. N/A.

## Reviewer Observations

- [VERIFIED] AC5 "one renderer, both surfaces" — pin rendering lives in the shared
  `CartographyMap` (CartographyMap.tsx:137-159), NOT in `MapSection`; MapSection only adapts and
  delegates (MapSection.tsx renders `<CartographyMap .../>`). The in-game `MapOverlay` renders the
  same component (MapOverlay.shared-map.test green). Evidence: pin JSX is inside CartographyMap's
  node `<g>`, so both surfaces inherit it. Complies with SOUL "Crunch in the Genre" / 100-10 intent.
- [VERIFIED] AC1 adapter fidelity — `toCartography` maps every server field that CartographyMap
  consumes (regions list→Record with name/adjacent/pins, starting_region) and edge derivation
  matches the server (`_edges_and_dangling` ↔ `edgesAndDangling`, both sorted-endpoint de-dup).
  Evidence: MapSection.tsx `toCartography`; edge test asserts `deep_root--far_landing`.
- [VERIFIED] AC3 session-free — `MapSection` imports only CartographyMap + types + `slugify`; no
  provider/socket/GameState import. Renders bare in the test with no wrapper. Evidence: import block.
- [VERIFIED] graceful-degrade preserved — `SectionDispatch` default still returns `null` for a
  node-less unknown section (SectionDispatch.tsx:46-50); the regression test uses id `ledger`.
- [EDGE] [MEDIUM] empty-string `portrait_url` would render `<img src="">` — CartographyMap.tsx:135
  (unreachable from server; recommend `Boolean(...)` filter). Non-blocking.
- [EDGE] [MEDIUM] top-row portrait pin may clip above the viewBox — cartographyDagLayout MARGIN /
  CartographyMap.tsx:142-144 (verify visually in playtest; bump MARGIN if confirmed). Non-blocking.
- [SEC] [LOW] `portrait_url` → `<img src>` with no origin allowlist → referrer leak to a non-R2
  host — CartographyMap.tsx:149 (pre-existing pattern, server-resolved from R2). Non-blocking.

## Devil's Advocate

Argue this code is broken. The headline feature is the "fancy node" portrait pin, and the most
damning charge is that the pins are drawn in a coordinate space the SVG actively clips. Every map
has a top row; pins are the whole point; therefore the most-looked-at pins are precisely the ones
at risk of having their top sheared off (`y ≈ node.y - 40`, and a layer-0 node can sit at
`y = MARGIN = 32`). The tests never catch this because jsdom has no layout engine — `getByRole`
finds the `<img>` in the DOM and asserts `src`, but a human staring at the lore page sees a
guillotined portrait. Green tests, broken feature: exactly the "winging it" the OTEL/lie-detector
doctrine exists to prevent, except here it's the *visual* layer with no telemetry to catch it.
Second charge: the empty-string `portrait_url`. The component's own docstring promises "no
broken/empty-src image," and the filter breaks that promise for `""` — a confused content author
who types `portrait_url: ""` instead of omitting the field gets a broken-image glyph AND a
spurious self-GET on the document URL. Third: a malicious or fat-fingered homebrew author
(Jade — a real, named author per CLAUDE.md) could point `portrait_url` at `evil.example.com` and
the player's browser dutifully fetches it, leaking the referrer; nothing on the client says no.
Fourth: duplicate region ids silently collapse in `toCartography`'s Record build — a "No Silent
Fallbacks" violation in spirit.

Rebuttals: the clipping premise is unverified — d3-dag may center layer-0 at `NODE_H/2 = 45`,
yielding `node.y = 77` and a pin top at `37` (no clip); I cannot confirm without rendering, so it
is flagged for visual playtest verification rather than asserted. The empty-string and external-URL
cases are unreachable through the real server (`reference_projection.py` resolves to an R2 URL or
`None`, never `""`, and never a raw author URL), and the external-URL pattern is identical to the
already-shipped CastSection. Duplicate region ids are impossible: the server's `regions` is a dict
keyed by id, so ids are unique by construction. None of the four charges is a reachable
Critical/High defect on the current server contract — they are hardening notes and a polish item,
correctly Medium/Low. The feature meets all five ACs with 33 green tests, a clean type build, and
clean lint.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** server `build_lore_map_section` JSON (`{regions[{id,name,adjacent,pins[{slug,label,portrait_url}]}], edges, starting_region, is_cluster, dangling}`) → `ReferenceDocument` → `SectionDispatch` `case "map"` → `MapSection.toCartography` (list→Record, pins folded onto regions) → `CartographyMap` → `computeCartographyDagLayout` (pins onto nodes) → SVG node `<g>` with `<foreignObject><img src={portrait_url} alt={label}>` only when `portrait_url !== null`. Safe: server text-escaped by React; no `dangerouslySetInnerHTML`; null portraits render nothing.

**Pattern observed:** Discriminated-union dispatch (`switch (section.id)` + `as VariantData`) at SectionDispatch.tsx:32-45 — consistent with the poi/cast/timeline pattern. Shared-renderer reuse (one `CartographyMap`, two surfaces) honors ADR/100-10.

**Error handling:** Null `portrait_url` → no image (CartographyMap.tsx:135). Missing/empty `pins` → `?? []`, safe `.filter`. Unknown node-less section → `null` (graceful degrade). One non-blocking robustness note ([EDGE-1] empty-string filter).

**Tags present:** [EDGE], [SEC], [TEST], [DOC], [TYPE], [SIMPLE], [RULE], [SILENT] — see dispositions above; [TEST]/[DOC]/[TYPE]/[SIMPLE]/[RULE]/[SILENT] specialists were disabled via settings and their domains were covered by my own Rule Compliance + Observations pass; [EDGE] and [SEC] findings are confirmed non-blocking.

**Blocking issues:** None (no Critical/High). 3 non-blocking findings recorded as Delivery Findings; 2 trivial fixes recommended; 1 item flagged for visual playtest verification.

**Handoff:** To SM (Winston Smith) for finish-story.