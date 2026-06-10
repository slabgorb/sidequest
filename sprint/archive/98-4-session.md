---
story_id: "98-4"
jira_key: ""
epic: "98"
workflow: "trivial"
---
# Story 98-4: C2 Content — jump mechanics on reached cartography routes (yula neighbors first)

## Story Details
- **ID:** 98-4
- **Jira Key:** (none — content authoring)
- **Workflow:** trivial
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-06-10T04:53:05Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-10 | 2026-06-10T04:43:20Z | 4h 43m |
| implement | 2026-06-10T04:43:20Z | 2026-06-10T04:47:19Z | 3m 59s |
| review | 2026-06-10T04:47:19Z | 2026-06-10T04:53:05Z | 5m 46s |
| finish | 2026-06-10T04:53:05Z | - | - |

## Story Context

**Type:** Content authoring (YAML)  
**Repos:** sidequest-content  
**Points:** 2  
**Epic:** 98 — ADR-141 Two-Scale Spatial Model — Galactic Graph + Per-System Orrery

## Objective

Author jump mechanics (fuel, transit time, drive rating, hazard) on the cartography routes between reached systems in `perseus_cloud`. Start with `yula` and its neighbors. These mechanics override default ruleset-derived jump costs when explicitly authored on route edges.

## Acceptance Criteria

1. For each `adjacent` edge from `yula` that play reaches, a `routes` entry in `sidequest-content/genre_packs/space_opera/worlds/perseus_cloud/cartography.yaml` carries authored jump mechanics in the field names finalized by S2 (98-5).
2. Unreached edges carry **no** routes entry and rely on the SWN ruleset default (valid, not an error).
3. *The Black Door* (`zephyr → ceron`) retains its existing narrative fields; jump-mechanics fields are added if/when reached.

## Implementation Notes

- **Data model:** `cartography.yaml` `routes:` is a list of objects with `from_id`, `to_id`, and optional mechanics fields.
- **Connectivity:** Graph connectivity stays on each system's `adjacent:` list (not on `routes:`); `routes:` entries are mechanics overlays on existing adjacencies.
- **Defaults:** An adjacency with no matching `routes` entry uses the SWN ruleset default; the default cost is explicit and OTEL-logged (No Silent Fallbacks).
- **Spec:** `docs/superpowers/specs/2026-06-08-two-scale-spatial-model-epic-design.md` § Story C2.
- **Depends on:** 98-5 (S2 finalizes field names)

## Related Stories

- **98-1** (DONE): Split `orbits.yaml` into per-system files, authored `yula`
- **98-2** (DONE): Server loader resolution (per-region system files)
- **98-3** (DONE): UI two-scale MapWidget (cartography graph ↔ orrery drill-down)
- **98-5** (DONE): Server jump adjudication via SWN seam (finalizes `routes` field schema)

## Branch Strategy
**Branch Strategy:** gitflow (feat/98-4-jump-mechanics-cartography-routes)

## Key Files

- `sidequest-content/genre_packs/space_opera/worlds/perseus_cloud/cartography.yaml` (add `routes:` entries)
- Spec: `docs/superpowers/specs/2026-06-08-two-scale-spatial-model-epic-design.md`

## Delivery Findings

### Dev (implementation)
- No upstream findings.

### Reviewer (code review)
- **Gap** (non-blocking): The authored `hazard` *tag* is read-but-not-surfaced in the 98-5 seam. `SWN.adjudicate_jump` reads `route.hazard` into `JumpAdjudication.hazard`, but `emit_jump_adjudicated` records only `hazard_roll` (the d6), not the tag, and `_adjudicate_inter_system_jump_for_advance` discards the whole adjudication result (no fuel deduction / clock advance applied). Affects `sidequest-server/sidequest/telemetry/spans/jump.py` (add a `hazard` attr to `jump.adjudicated`) and `sidequest-server/sidequest/server/narration_apply.py:3241` (apply `fuel_spent`/`transit_days`). Out of scope for 98-4 (content authoring into a published schema); belongs to epic 98 / a 98-5 follow-up so authored hazards are GM-panel-verifiable per the OTEL lie-detector principle. *Found by Reviewer during code review.*

## Design Deviations

### Dev (implementation)
- No deviations from spec. Used the exact field names the live S2 adjudicator parses (`jump_fuel`, `transit_days`, `drive_rating_min`, `hazard`), confirmed by reading `sidequest-server/sidequest/genre/models/world.py:Route` and `swn.py:adjudicate_jump` (commit 9105a85e) before authoring — Vizzini's load-bearing risk avoided.

### Reviewer (audit)
- **Dev: "No deviations from spec"** → ✓ ACCEPTED by Reviewer: verified the four authored field names match the live `Route` model exactly; the adjudicator returns `source=route` for all three lanes, confirming the fields are consumed (not invented dead keys). No undocumented deviations spotted in the diff.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest-content/genre_packs/space_opera/worlds/perseus_cloud/cartography.yaml` — added 3 `routes` entries annotating yula's mutual adjacencies with ADR-141 jump mechanics; Black Door entry untouched.

**Approach:** Read the 98-5 server seam first (`Route` model + `SWN.adjudicate_jump` + `orbital/jump.py:resolve_route_for_jump`) to get the exact schema and matching rules (undirected, requires mutual `adjacent`). Authored three lore-grounded lanes with a deliberate spread:
- **The Amanti Supply Run** (yula↔amanta): 1 fuel / 4 days — fast clean commercial lane.
- **The Tide Road** (yula↔nimia): 1 fuel / 6 days — standard main lane.
- **The Night Crossing** (yula↔terma): 2 fuel / 8 days, `drive_rating_min: 2`, `hazard: hyperspace_shoal` — grounded in Terma's "half-embedded in Hyperspace" lore.

**Acceptance Criteria:**
- **AC1** ✅ — each reached yula adjacency carries a `routes` entry with the S2-finalized fields. Verified `resolve_route_for_jump` returns each, `adjudicate_jump` returns `source=route`.
- **AC2** ✅ — no entry for unreached edges; `terma↔nimia` adjudicates to `source=ruleset_default` (explicit 1 fuel / 6 days, not a swallowed zero).
- **AC3** ✅ — Black Door retains `danger: deadly` / `distance: long`, no jump mechanics (ceron unreached).

**Verification (live engine, not validator):** Parsed the real `cartography.yaml` through `CartographyConfig.model_validate` (the loader's schema path — 35 regions, 4 routes, no error) and exercised the production consumer `adjudicate_inter_system_jump` (wired into `narration_apply`). The strain gate fires correctly: drive-1 ship on The Night Crossing → fuel **3** (2 authored + 1 strain), drive-2 → fuel **2** (no strain), hazard tag propagates. Per-system orbital files untouched; region count unchanged.

**Tests:** No new tests — pure content; the consumer's wiring tests (synthetic cartography) already exist from 98-5, and a test pointing at the `perseus_cloud` slug would be the prod-rows-in-tests anti-pattern.

**Branch:** `feat/98-4-jump-mechanics-cartography-routes` (sidequest-content, pushed)

**Handoff:** To review (Westley).

## Sm Assessment

**Routing:** Pure content authoring (YAML route edges in one `cartography.yaml`), 2pts, trivial/phased. Straight to dev — no TEA red phase for data-only work. → **dev** for the `implement` phase.

**Load-bearing risk — field names must match the live S2 adjudicator, not be invented.** AC1 says mechanics fields use "the field names finalized by S2 (98-5)." Memory and project doctrine both warn against authoring world content that no Python consumer reads (world `inventory.yaml`/`confrontations.yaml` are engine-unwired; see the world-extension-unwired memory). Before writing any route field, the dev MUST read the 98-5 server jump-adjudication code (SWN ruleset seam, ADR-117 — landed at server commit ~d49cd289) and use the **exact** keys the adjudicator parses off a `routes` entry. Inventing plausible names (fuel/transit_time/drive_rating/hazard) would silently no-op. Confirm the override path is read before authoring.

**Scope discipline:** yula's *reached* neighbors only. Unreached edges get NO `routes` entry (AC2 — SWN default is valid, not an error; No Silent Fallbacks means that default must be explicit/OTEL-logged server-side, which 98-5 owns). Don't pre-author the whole graph. Retain *The Black Door* narrative fields (AC3).

**Verification:** `load_genre_pack` for space_opera/perseus_cloud must still load clean (a validator PASS is not proof — run the loader). Confirm the orbital loader resolves the per-system files unchanged.
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (YAML parse PASS, validator 0 errors, 3/3 mutual adjacencies confirmed, tree clean) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (1 enabled returned clean; 8 disabled via `workflow.reviewer_subagents` — the code-oriented specialists do not apply to a pure-YAML content diff. Their domains self-assessed below.)
**Total findings:** 0 confirmed blocking, 0 dismissed, 1 deferred (Delivery Finding → epic 98).

## Reviewer Assessment

**Verdict:** APPROVED

**What changed:** 47 additive lines in `genre_packs/space_opera/worlds/perseus_cloud/cartography.yaml` — three `routes` entries annotating yula's three mutual adjacencies (amanta/nimia/terma) with ADR-141 jump mechanics, plus a header comment. The Black Door entry is untouched. No code, no tests.

**Data flow traced:** authored route fields → `CartographyConfig.routes` (loader schema parse, PASS) → `orbital/jump.py:resolve_route_for_jump` (undirected endpoint match, requires mutual `adjacent`) → `SWN.adjudicate_jump` → `JumpAdjudication`. All three lanes resolve and return `source=route`; `jump_fuel`/`transit_days`/`drive_rating_min` reach the `jump.adjudicated` span (observable in the GM panel). Unrouted adjacencies return `source=ruleset_default` (AC2). Confirmed against the live engine, not just the validator.

**Observations (≥5, no rubber-stamp):**
- [VERIFIED] Field names match the live schema — `jump_fuel`/`transit_days`/`drive_rating_min` (int) and `hazard` (str) are exactly the fields on `sidequest-server/.../world.py:Route` (lines 245–266). Adjudicator returns `source=route`, proving they are consumed, not invented dead keys. Evidence: `swn.py:adjudicate_jump` lines 184–188 read these attributes.
- [VERIFIED] All three routes annotate real mutual adjacencies — yula↔{amanta,nimia,terma} each list the other in `adjacent` (cartography.yaml lines 68–70, 543–547, 737–740, 899–902). None will be dropped as a route anomaly by `resolve_route_for_jump`.
- [VERIFIED] AC2 honored — only yula's three reached neighbours + the pre-existing Black Door are routed; the rest of the 35-region graph stays at the explicit OTEL-logged ruleset default. No graph-wide pre-authoring.
- [VERIFIED] AC3 honored — Black Door retains `danger: deadly` / `distance: long` / `terrain: vacuum`, no jump-mechanics fields (ceron is unreached). Diff shows the entry unchanged.
- [VERIFIED] The Night Crossing strain gate is genre-correct — `drive_rating_min: 2` makes a default drive-1 ship burn +1 fuel (3 total) without blocking, matching the `Route.drive_rating_min` contract ("crosses but burns an extra fuel load, not a block"). hazard `hyperspace_shoal` is grounded in Terma's "half-embedded in Hyperspace" lore (Genre/World flavor doctrine).
- [LOW] The Tide Road authors `transit_days: 6`, identical to the spike-drive default. Not a defect — authoring the entry is what AC1 requires (a *named, reached* lane = `source=route`), and the explicit value documents intent. No change needed.
- [DEFERRED → Delivery Finding] The authored `hazard` tag is read by the adjudicator but not surfaced on any span nor applied to state (98-5 seam gap). See Delivery Findings; out of 98-4 scope.

**Disabled-specialist domains, self-assessed (content diff):**
- [EDGE] No boundary logic in data; the only conditional behavior (drive strain, unrouted fallback) lives in 98-5 code and was exercised live. Clean.
- [SILENT] No silent fallbacks introduced — unrouted edges fail to an *explicit* `ruleset_default` (named, span-logged), per the header comment and verified run. Clean.
- [TEST] No tests appropriate — pure content; coupling a test to the `perseus_cloud` slug would be the prod-rows-in-tests anti-pattern (project memory). The consumer's synthetic-cartography wiring tests from 98-5 already cover behavior. Clean.
- [DOC] Header comment is accurate (names the real consumer `orbital/jump.py`, the per-field default, the annotate-not-create rule). No stale/misleading docs. Clean.
- [TYPE] Values are correctly typed (ints for fuel/days/drive, string for hazard tag); `Route` model `extra="allow"` accepts the narrative `distance`/`danger` (themselves typed fields). Clean.
- [SEC] No security surface — static world data, no input handling, no secrets, no auth/tenant boundary. Clean.
- [SIMPLE] Minimal, non-redundant; three entries for three reached edges, no over-authoring. Clean.
- [RULE] Complies with "Crunch in the Genre, Flavor in the World" (mechanics on world routes overlay genre ruleset), "No Silent Fallbacks" (explicit default path), and "Verify Wiring" (fields proven consumed). Clean.

### Rule Compliance
- **No Silent Fallbacks (CLAUDE.md/SOUL.md):** Unrouted adjacency → explicit `ruleset_default` with `jump.default_cost` span. COMPLIANT.
- **Crunch in the Genre, Flavor in the World (SOUL.md):** Jump mechanics overlay the *world's* routes; the SWN ruleset (genre) owns the resolution math. Authored values are world-specific; rules stay in the ruleset. COMPLIANT.
- **Verify Wiring, Not Just Existence (CLAUDE.md):** Confirmed `jump_fuel`/`transit_days`/`drive_rating_min` reach a production consumer AND an observable span. The one half-wired field (`hazard` tag) is flagged as a 98-5 Delivery Finding, not silently accepted. COMPLIANT.
- **Tests-point-at-content anti-pattern (project memory):** No test added that references the live `perseus_cloud` slug. COMPLIANT.

### Devil's Advocate
Argue this is broken. First attack: the `hazard: hyperspace_shoal` tag goes nowhere — `emit_jump_adjudicated` drops it and the live advance seam discards the adjudication result entirely, so a player crossing The Night Crossing experiences *no* mechanical hazard and the GM panel never records the authored tag. Is this dead content the project forbids? Examined: the field is part of the schema 98-5 published expressly "for C2/98-4," the adjudicator *does* read it into `JumpAdjudication.hazard`, and the gap is downstream surfacing — a 98-5/epic wiring task, not a 98-4 authoring fault. Removing the tag would be worse (it is the correct design content for Terma). So: real gap, correct scope call, captured as a non-blocking finding. Second attack: could a route annotate a non-adjacency and silently mis-wire connectivity? No — `resolve_route_for_jump` drops anomalous endpoints with a WARN and never promotes a route to connectivity; all three authored edges are verified mutual adjacencies, so none trip that path. Third attack: `transit_days: 6` equals the default — is the dev cargo-culting? No — an authored entry is precisely what AC1 demands for a reached lane (it flips `source` to `route` and names the lane); the value documents intent. Fourth attack: YAML fragility — an unquoted `hyperspace_shoal` or the `>-` folded scalars could mis-parse. Checked: validator + `CartographyConfig.model_validate` both PASS, 35 regions / 4 routes, hazard parses as the expected string. Fifth attack: does adding routes break the existing map/orrery render or per-system loader (98-1/98-2)? Region count unchanged (35), routes are an additive list the renderers already iterate; preflight confirms clean load. Nothing here rises to High/Critical. The content is schema-valid, lore-grounded, wired for the AC-relevant fields, and the single genuine gap is correctly out-of-scope and documented.

**Pattern observed:** Per-field optional override with explicit ruleset fallback — `genre_packs/space_opera/worlds/perseus_cloud/cartography.yaml:1034-1077`. Good pattern: world authors only what differs; the ruleset owns defaults.
**Error handling:** Unrouted/anomalous edges degrade loudly (WARN + explicit default span), never silently — verified at `orbital/jump.py:resolve_route_for_jump`.
**Handoff:** To SM for finish-story.