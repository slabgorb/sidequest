---
story_id: "65-11"
jira_key: ""
epic: ""
workflow: "tdd"
---
# Story 65-11: Lore POI map view — server-rendered SVG node-link graph with portrait pins

## Story Details
- **ID:** 65-11
- **Jira Key:** N/A (personal project)
- **Workflow:** tdd
- **Stack Parent:** none

## Sm Assessment

**Story:** 65-11 — Lore POI map view: server-rendered SVG node-link graph with portrait pins.
**Repo:** sidequest-server only · **Branch:** feat/65-11-lore-poi-map-svg (off develop) · **Workflow:** tdd (phased) · **Jira:** N/A (personal project).

**Readiness:** READY for red. The story entered the sprint as a title-only stub; before setup it was fully scoped by the Architect (Neo) at the Operator's direction — 8 acceptance criteria + a 1692-char description authored into sprint/epic-65.yaml, and a schema-valid context doc (sprint/context/context-story-65-11.md, 0 validator errors) covering Business Context, Technical Guardrails, Scope Boundaries, and per-AC notes.

**Routing rationale:** 5-pt feature, tdd workflow → phased → first phase owner is TEA (red). Handing off for failing-test authoring against the 8 ACs.

**Load-bearing context for TEA (The Architect):**
- This is a REUSE/wire-up of the 65-8/65-9 reference-page machinery, NOT a new build. The only genuinely new code is a *deterministic* node-link layout — cartography has no coordinates (every world is navigation_mode: region + adjacency list).
- Reuse seams (verified on develop, cited in the context doc): reference_routes.lore_page → reference_renderer.assemble_lore_page; PACK_TOC/TOC_TO_FILES section registration (65-9 Cast append pattern); genre/models/world.CartographyConfig / Region.adjacent / Region.entities; the R2 portrait gate (load_r2_manifest_keys + portrait_image_key + Cast slugify path); svgwrite (already a dep); telemetry/spans/reference + gated_client/otel_capture/span_attrs_by_name fixtures.
- Non-negotiables baked into the ACs: byte-deterministic SVG (AC4); OTEL on every decision with complement assertions (AC6); public-projection-only per ADR-135 (AC7); NO source-text wiring tests per server CLAUDE.md (AC8).
- RED-phase risk to confirm first: the `entity.binding.ref` (npc id) → portrait slug resolution chain (AC5) — confirm the mapping against a fixture before pinning the gate test.

**Checklist:** session ✓ · context ✓ · branch ✓ · fields set ✓ · Jira skipped (no integration) ✓.

---
## TEA Assessment

**Tests Required:** Yes
**Reason:** 5-pt feature (new lore-page Map section + deterministic SVG layout + gated pins). Not a chore.

**Test Files:**
- `tests/server/test_reference_map.py` — 18 tests, the full AC matrix + 1 rule-enforcement test.
- Fixtures (new worlds in `tests/fixtures/packs/reference_v2_fixture/worlds/`): `map_fixture` (positive: 4 regions, reciprocal edge, dangling edge, 2 npc pins [1 on-R2 / 1 absent], 1 flavor_only + 1 location_feature non-pin entity), `map_perm_fixture` (same graph, region keys reordered — AC4 determinism), `map_malformed_fixture` (broken YAML — AC1 loud), `map_escape_fixture` (HTML-special region name — rule #11).
- `tests/fixtures/r2_manifest.json` — +1 entry (`map_fixture/.../portraits/vivian_harbormaster.png`). Safe: the cast test reads its count dynamically (line 232); the POI `== 1743` assertion is against the production manifest; nothing iterdir-globs the fixture worlds.

**Tests Written:** 18 tests covering 8 ACs. **Status:** RED — verified `16 failed, 2 passed` (`uv run pytest -n0`). The 2 passing are intentional regression guards (graceful no-cartography absence + existing-Cast-section-unchanged), which assert *existing* behavior must hold. The 16 new-behavior tests fail on meaningful assertions ("no Map section"), not import/collection errors — the route renders 200, the feature is simply absent.

**AC coverage map:**
| AC | Tests |
|----|-------|
| AC1 section present / graceful-absent / loud-500 | test_map_section_present_for_world_with_cartography · test_no_cartography_world_renders_without_map_section (guard) · test_malformed_cartography_fails_loud_500 |
| AC2 nodes from regions | test_every_region_is_a_node · test_region_name_is_the_node_label |
| AC3 edges + reciprocal dedup + dangling WARN | test_edges_match_adjacency_with_reciprocal_dedup · test_dangling_adjacency_is_skipped_and_warns |
| AC4 deterministic layout | test_map_svg_is_byte_deterministic · test_node_order_independent_of_yaml_key_order |
| AC5 gated npc pins | test_both_npc_entities_render_as_pins · test_on_r2_pin_emits_portrait_image · test_absent_portrait_pin_has_no_broken_image |
| AC6 OTEL + complements | test_map_rendered_span_carries_exact_counts · test_pin_decisions_emit_spans_with_complements |
| AC7 public-only | test_only_npc_entities_pin |
| AC8 wiring/regression/chrome | test_existing_sections_unchanged_by_map_feature (guard) · test_map_emits_semantic_chrome_classes |

**Observable contract pinned for Dev (behavioral — no source-text wiring tests):**
- Section `<section id="map">` (heading "Map", one inline `<svg>`) + TOC entry `{"id":"map","label":"Map"}`, appended in `assemble_lore_page` the way the 65-9 Cast section is.
- Node per region: attribute `data-region-id="<id>"`, region `name` as visible label.
- Edge per adjacency: `data-edge="<a>--<b>"` with endpoints **sorted ascending**, joined `--`; reciprocal collapses to one; unknown-region adjacency dropped.
- Pin per npc entity: `data-npc-slug="<slug>"`; portrait `<img>` iff `portrait_image_key(pack,world,slug)` ∈ r2_manifest.json (reuse `load_r2_manifest_keys`).
- CSS classes: `ref-map__node`, `ref-map__edge`, `ref-map__pin`.
- Spans (register in `FLAT_ONLY_SPANS`): `sidequest.reference.map_rendered` (attrs `reference.map_node_count`/`map_edge_count`/`map_npc_pin_count`/`map_resolved_pin_count`), `sidequest.reference.map_pin_resolved` / `map_pin_not_found` (attr `slug`), `sidequest.reference.map_dangling_edge` (attr `reference.map_dangling_region`).

### Rule Coverage
| Rule (lang-review/python.md) | Test(s) | Status |
|------|---------|--------|
| #11 HTML output escaped (CWE-79) | `test_region_name_is_html_escaped_in_svg` | failing |
| #1 No silent fallbacks (loud on malformed) | `test_malformed_cartography_fails_loud_500` | failing |
| #6 Test quality (self-check) | self-review pass | 1 vacuous assertion found + fixed (`len(edges)==len(edges)` → `len(set(edges))==len(edges)`) |

**Rules checked:** 3 of 13 lang-review rules are behaviorally testable for this feature at RED. Deferred to review (production-code rules not behaviorally assertable in RED): #8 unsafe-deserialization (the cartography loader MUST use `yaml.safe_load` — Reviewer to verify), #3 type annotations, #5 path handling, #2 mutable defaults, #7 resource leaks, #9 async, #10 imports, #12 deps.
**Self-check:** 1 vacuous assertion found and fixed; all 18 tests carry a meaningful assertion.

**Handoff:** To Dev (Agent Smith) for implementation.

---
## Dev Assessment

**Status:** GREEN — all 18 map tests pass; full server suite **9832 passed, 362 skipped, 0 failures**; reference suite 437 passed (incl. the chrome-wiring keystone now rendering cartography). `ruff check` clean, `ruff format` applied, `pyright` 0 errors. Pushed to `feat/65-11-lore-poi-map-svg` (`2f40519`).

**Files changed:**
- `sidequest/server/reference_map.py` (new) — `load_cartography_config` (loud on malformed), deterministic BFS `_layout_order`/`_positions`, `_edges_and_dangling` (sorted-endpoint dedup + dangling list), `_npc_pins`, `present_lore_map` (SVG emission + spans).
- `sidequest/server/reference_renderer.py` — import + Map block in `assemble_lore_page` (after Cast): loads cartography, gathers npc slugs, reuses `_gate_cast_slugs_on_manifest`, appends `<section id="map">` + `{"id":"map","label":"Map"}` TOC entry.
- `sidequest/telemetry/spans/reference.py` — 4 spans (`map_rendered`, `map_pin_resolved`, `map_pin_not_found`, `map_dangling_edge`) registered in `FLAT_ONLY_SPANS` + their helper context managers.
- `sidequest/server/static/reference/presenters.css` — rules for `.ref-map`, `.ref-map__svg`, `.ref-map__edge`, `.ref-map__node`, `.ref-map__pin`.
- `tests/server/test_reference_chrome_wiring.py` — `_seed_space_opera_world` now writes a pin-free `cartography.yaml` so the keystone class-vs-CSS test validates the map classes (closes the AC8 chrome blind spot).

**AC accountability:**
| AC | Status | How |
|----|--------|-----|
| AC1 section / graceful / loud | DONE | Map section appended when cartography present; absent → unchanged 200; malformed YAML → `ValueError` → route 500 |
| AC2 nodes from regions | DONE | one `data-region-id` node per region, `name` as `<text>` label |
| AC3 edges + dedup + dangling WARN | DONE | sorted-endpoint `data-edge` set; unknown ref dropped + `map_dangling_edge` span |
| AC4 deterministic layout | DONE | BFS from `starting_region`, sorted neighbours; no time/random/dict-order; byte-identical + order-stable |
| AC5 gated npc pins | DONE | `slugify_player_name(entity.label)` slug, reuses `_gate_cast_slugs_on_manifest`; resolved → `<img>`, absent → marker (no broken img) |
| AC6 OTEL + complements | DONE | `map_rendered` (4/3/2/1 counts) + per-pin resolved/not_found |
| AC7 public-only | DONE | only `binding.kind=="npc"` entities pin |
| AC8 wiring/regression/chrome | DONE | integration via real route; existing sections unchanged; CSS rules added + chrome-wiring seed extended |

**OTEL:** every map subsystem decision emits a span (render census, per-pin gate, dropped edge) — the GM panel can confirm the graph engaged rather than improvised.

**Handoff:** To TEA (verify phase — simplify + quality-pass).

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None blocking — 2 minor, pre-logged deviations adjudicated below.

Verified each AC's *intent* against the GREEN code (`reference_map.py`, the `assemble_lore_page` Map block, the spans, the CSS + chrome-seed):
- AC1/2/3/4/7 — exact match: section appended only when cartography present (`None` → unchanged page), `load_cartography_config` fails loud (YAMLError **and** pydantic ValidationError → `ValueError` → route 500); one node per region (BFS-reachable + sorted leftover guarantees ALL regions); sorted-endpoint edge dedup with dangling drop; BFS seeded at `starting_region` with sorted neighbours + sorted leftover + sorted edges = byte-deterministic and YAML-order-independent; only `binding.kind=="npc"` entities pin.
- AC5/6/8 — match: pins reuse `_gate_cast_slugs_on_manifest` (same R2 oracle as Cast), resolved→`<img>` in `<foreignObject>`, absent→marker; `map_rendered` fires once with the exact census + per-pin `resolved`/`not_found`; CSS rules added and the chrome-wiring seed now carries cartography so the keystone class-vs-CSS test validates the map classes.

**Deviation adjudication:**
- **Hand-built escaped SVG instead of svgwrite** (Behavioral/implementation, Trivial) — Spec: context Technical Guardrails "Prefer svgwrite." Code: escaped string builder. **Recommendation A (update spec / accept):** svgwrite cannot cleanly emit hyphenated `data-*` attributes, an HTML `<img src>` pin via `<foreignObject>`, or guarantee byte-determinism without extra ceremony; the string builder mirrors the existing `_cast_portrait_img_html` escaping idiom. Non-breaking, self-contained `<svg>`. Accepted.
- **AC5 slug = `slugify_player_name(entity.label)`** (Ambiguous spec — Behavioral, Minor) — Spec: "resolve ref → display name → slug." Code: slugifies the entity `label` directly (not `binding.ref`). **Recommendation C (clarify spec):** for the *public* map the entity `label` IS the display name, and using the same `slugify(name)` rule as Cast means a map pin and a Cast card resolve the identical R2 portrait key — which is the spec's actual goal (Cast parity). **Defer (D)** any richer `ref → npc-record → canonical-name` resolution to a future story: no current content binds an npc entity whose `label` differs from its portrait name, and Cast carries the same label==name assumption. Authoring guidance already captured in the Dev deviation. Non-breaking.

**Decision:** Proceed to verify (TEA). No hand-back to Dev — alignment is clean and both deviations are minor and accepted.

---
## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report
**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 3 (`reference_map.py`, `reference_renderer.py`, `telemetry/spans/reference.py`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | No new duplication — confirms deliberate reuse of `_gate_cast_slugs_on_manifest`, `portrait_image_key`, `slugify_player_name`, `resolve_asset_url`; the dungeon `bfs_dist` serves a different purpose (not a missed extraction). |
| simplify-quality | clean | Naming/structure/error-handling sound; all dynamic content (region.name, rid, slug, src, label) HTML-escaped; imports all used. |
| simplify-efficiency | clean | No over-engineering; each helper single-purpose; sorted iteration is the required determinism, not waste. |

**Applied:** 0 high-confidence fixes (all teammates clean)
**Flagged for Review:** 0 · **Noted:** 0 · **Reverted:** 0
**Overall:** simplify: clean

**Quality Checks:** All passing — `ruff check` clean, `pyright` 0 errors on the new module, 21 tests pass (18 map + 3 chrome-wiring); the green-phase full suite (9832 passed) is unchanged (no verify edits).
**Handoff:** To Reviewer (The Merovingian) for code review.

---
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (436 passed, 0 fail, 0 smells; ruff/pyright clean on changed files) | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | Yes | clean | none (0 violations across 6 rule families; 10 escape sites, safe_load, loud-fail, path-guard, ADR-135) | N/A |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings |

**All received:** Yes (2 enabled subagents returned; 7 disabled via `workflow.reviewer_subagents`)
**Total findings:** 0 confirmed, 0 dismissed, 2 deferred (own-read observations, below bar — see assessment)

## Reviewer Assessment

**Verdict:** APPROVED

**Scope reviewed:** the GREEN diff for 65-11 (`git diff develop...HEAD`, 6 code files / 1012 insertions) — the new `reference_map.py`, the Map block in `assemble_lore_page`, 4 new OTEL spans, the `presenters.css` rules, and the two touched test files.

**Enabled subagents (preflight + security) both clean; the other seven are disabled via settings.** I did not rely on the clean preflight — I read the diff myself and corroborated each domain:

- **Correctness / ACs** — the Map block renders only when cartography is present (`None` → page unchanged); `load_cartography_config` fails loud (YAMLError **and** pydantic ValidationError → `ValueError` → route 500); BFS layout covers every region (reachable + sorted leftover); edges de-duplicate via sorted-endpoint key; dangling refs dropped + WARN span; only `npc`-binding entities pin; pins reuse the Cast R2 gate. All 8 ACs are behaviorally verified by the 18 passing tests.
- **Security [SEC]** — confirmed clean by reviewer-security and my own read: all 10 SVG interpolation sites `html.escape()`'d (CWE-79); `yaml.safe_load` (CWE-502); `Path` ops + `encoding=`; `_SAFE_SLUG` regex guards `pack`/`world` traversal (pre-existing route code, CWE-22); `cartography.yaml` in `EXCLUDED_FILES` so raw YAML never dumps; ADR-135 public-only holds (no secret tier exists in the `LocationEntity.tier` schema).
- **Determinism (AC4)** — codepoint-sorted neighbours/leftover/edges; no time/random/dict-order leakage. Byte-identical + order-independent, proven by tests.
- **OTEL** — every map decision emits a span (render census, per-pin gate, dropped edge); GM-panel observable per the project principle.

**Rule Compliance (lang-review/python.md):** #1 silent-fallbacks (loud 500 on malformed) ✓ · #5 path-handling (`Path` + `encoding`) ✓ · #8 unsafe-deserialization (`safe_load`) ✓ · #11 input-validation/HTML-escaping ✓ · #6 test-quality (TEA fixed 1 vacuous assertion; 18 meaningful tests) ✓. No violations.

**Deferred (own-read, below bar — non-blocking):**
1. A region whose `adjacent` lists **itself** would render a zero-length `<line>` (sorted-endpoint key `("x","x")`). Cosmetic only; no current content does this. Could be a one-line guard in a future polish.
2. A region listing the **same missing** neighbour twice fires two `map_dangling_edge` WARN spans. Telemetry noise only; not incorrect. Authoring error surfaces either way.

Neither rises to a change request. Both deviations logged by Dev (hand-built SVG; AC5 label-slug) were adjudicated by the Architect in spec-check and are minor/accepted.

**Decision:** APPROVED — merge-ready. Hand to SM for the finish ceremony.

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-03T11:48:00Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-03T11:08:29Z | 2026-06-03T11:10:16Z | 1m 47s |
| red | 2026-06-03T11:10:16Z | 2026-06-03T11:24:29Z | 14m 13s |
| green | 2026-06-03T11:24:29Z | 2026-06-03T11:36:48Z | 12m 19s |
| spec-check | 2026-06-03T11:36:48Z | 2026-06-03T11:38:37Z | 1m 49s |
| verify | 2026-06-03T11:38:37Z | 2026-06-03T11:42:45Z | 4m 8s |
| review | 2026-06-03T11:42:45Z | 2026-06-03T11:46:58Z | 4m 13s |
| spec-reconcile | 2026-06-03T11:46:58Z | 2026-06-03T11:48:00Z | 1m 2s |
| finish | 2026-06-03T11:48:00Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->
### TEA (test design)
- **Gap** (non-blocking): AC5 does not define HOW an npc entity's portrait slug is derived — `entity.binding.ref` (an npc id), `slugify(entity.label)`, or an `npcs.yaml`/`portrait_manifest.yaml` lookup. `map_fixture` is authored so `slugify(label) == binding.ref == the r2 portrait slug`, so the gating tests pass under any of these. Dev MUST pick one resolution path and document it. Affects the new cartography→pin code in `sidequest/server/reference_renderer.py` (or a new `reference_presenters` helper). *Found by TEA during test design.*
- **Gap** (non-blocking): `assemble_lore_page` does not load `cartography.yaml` today (it is in `EXCLUDED_FILES`); Dev must add an explicit cartography load to the lore-page path, mirroring `load_cast_entries(world_dir)`. Confirmed against `reference_renderer.py:assemble_lore_page`. Affects `sidequest/server/reference_renderer.py`. *Found by TEA during test design.*
- **Question** (non-blocking): the lore page may carry chrome `<svg>` icons elsewhere; `_map_section`/`_map_svg` scope to `<section id="map">` to avoid grabbing the wrong svg. If Dev wraps the map svg differently, keep the `id="map"` section wrapper so the scoping holds. Affects the section-append site in `reference_renderer.py`. *Found by TEA during test design.*
### Dev (implementation)
- **Resolved** (non-blocking): both TEA gaps are closed — `assemble_lore_page` now loads cartography via `load_cartography_config(world_dir)`, and the AC5 slug path is `slugify_player_name(entity.label)` (Cast parity; see Design Deviations). The `id="map"` section wrapper is kept exactly as the TEA scoping assumes. *Found by Dev during implementation.*
- No new upstream findings during implementation.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->
### TEA (test design)
- **Dedicated map-pin spans instead of reusing the scrapbook portrait family**
  - Spec source: context-story-65-11.md, AC6 ("reuse the reference-portrait family OR a dedicated reference_map_pin_resolved/not_found pair")
  - Spec text: "a per-pin resolved/not_found span pair (reuse the reference-portrait family or a dedicated reference_map_pin_resolved/not_found pair registered in FLAT_ONLY_SPANS)"
  - Implementation: tests pin DEDICATED spans `sidequest.reference.map_pin_resolved` / `map_pin_not_found` rather than reusing `scrapbook.npc_portrait_{resolved,not_found}`.
  - Rationale: 65-13 already flags that reusing the scrapbook spans on the reference page is semantically muddy (their docstrings describe scene-time scrapbook attachment). Dedicated reference-namespaced spans avoid inheriting that defect and keep map-pin telemetry distinguishable from Cast-portrait telemetry.
  - Severity: minor
  - Forward impact: Dev registers two new spans in `telemetry/spans/reference.py` `FLAT_ONLY_SPANS`; no impact on sibling stories.
- **AC8 chrome coverage is lighter than the AC's "extend the chrome-wiring fixture" wording**
  - Spec source: context-story-65-11.md, AC8
  - Spec text: "The chrome-wiring fixture (test_reference_chrome_wiring.py seed world) is extended so the new map CSS classes are actually rendered and validated"
  - Implementation: RED adds `test_map_emits_semantic_chrome_classes` (asserts `ref-map__node/edge/pin` appear in the emitted SVG) rather than extending `test_reference_chrome_wiring.py::_seed_space_opera_world` to carry cartography.
  - Rationale: the seed-world extension + CSS-rule definition is Dev/GREEN work (the CSS rules don't exist yet); pinning the emitted classes behaviorally is the RED-appropriate contract. Dev should still add the CSS rules and extend the chrome-wiring seed during GREEN to fully close the 65-13 blind spot.
  - Severity: minor
  - Forward impact: Dev must add CSS rules for the map classes and extend the chrome-wiring seed; Reviewer to confirm the blind spot is closed.

### Dev (implementation)
- **Hand-built escaped SVG string instead of svgwrite**
  - Spec source: context-story-65-11.md, Technical Guardrails
  - Spec text: "svgwrite is already a dependency, used by orbital/render.py ... Prefer svgwrite over hand-built string SVG for consistency."
  - Implementation: `present_lore_map` builds the SVG as a string with explicit `html.escape()` on every interpolation, mirroring `_cast_portrait_img_html`.
  - Rationale: three hard requirements made svgwrite the harder, riskier path — (1) custom `data-region-id`/`data-edge`/`data-npc-slug` attributes (hyphenated, not Python kwargs), (2) HTML `<img src>` pins inside the SVG via `<foreignObject>` (svgwrite has no foreignObject class; the test contract is `src="…"`, which SVG `<image href>` would not satisfy), and (3) byte-determinism + escaping control. Hand-built string is the simpler code that passes the tests (Agent Smith minimalism) and matches the existing Cast escaping idiom.
  - Severity: minor
  - Forward impact: none — output is a self-contained `<svg>`; if a future story needs richer geometry, svgwrite can be revisited.
- **AC5 portrait-slug resolution: slugify(entity.label)**
  - Spec source: context-story-65-11.md, AC5; Delivery Findings → TEA Gap (binding.ref→slug)
  - Spec text: "resolve ref → display name → slug through the same path the Cast section uses"
  - Implementation: the pin slug is `slugify_player_name(entity.label)` — NOT `binding.ref`. This matches the Cast section's `slugify_player_name(name)`, so a map pin and a Cast card resolve the SAME R2 portrait key for the same person. The fixture is authored so `slugify(label) == binding.ref`, so the gate tests pass either way; the chosen path is label-slugify for Cast parity.
  - Rationale: keeps map pins and Cast portraits on one slug rule (one R2 key per person) and avoids coupling the public map to internal npc-id strings.
  - Severity: minor
  - Forward impact: authors must ensure an npc entity's `label` slugifies to its portrait filename (same rule Cast already requires); `binding.ref` is used for identity, not portrait lookup.

### Architect (reconcile)
**Existing entries verified:** all four (TEA ×2, Dev ×2) carry the full 6-field format with accurate spec sources, quoted spec text, and implementation descriptions matching the landed code. No corrections needed.

**Status change — AC8 chrome deviation resolved in GREEN.** The TEA "AC8 chrome coverage is lighter" deviation logged a forward-impact ("Dev must add CSS rules + extend the chrome-wiring seed"). That impact is now **discharged**: Dev added the five `.ref-map*` rules to `presenters.css` and extended `test_reference_chrome_wiring.py::_seed_space_opera_world` with a pin-free `cartography.yaml`, so the keystone `test_every_emitted_class_has_matching_css_rule` now renders the Map section and validates its classes against the served CSS. The 65-13-style chrome blind spot is **closed**, not deferred — confirmed by the green chrome-wiring test in the Reviewer's preflight (436 passed).

**AC deferral check:** none — the Dev AC accountability table marks all 8 ACs DONE (no DEFERRED/DESCOPED rows). No-op.

**Missed deviations:** No additional deviations found. The two Reviewer own-read observations (a self-adjacent region would render a zero-length `<line>`; a region naming the same missing neighbour twice fires duplicate `map_dangling_edge` WARN spans) are below-bar, non-spec, future-polish notes — neither contradicts any spec text, AC, or rule, so neither is a deviation. No current content exercises either.

**Reconcile verdict:** the deviation manifest is complete and accurate; the story is ready for SM finish.