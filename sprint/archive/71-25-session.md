---
story_id: "71-25"
jira_key: ""
epic: "71"
workflow: "tdd"
---
# Story 71-25: perseus_cloud location grounding — declare world POIs (New Kowloon) as snapshot entities from content

## Story Details
- **ID:** 71-25
- **Jira Key:** (none — SideQuest is personal, no Jira)
- **Workflow:** tdd
- **Stack Parent:** none
- **Type:** bug
- **Priority:** p2
- **Points:** 3

## Repos
- sidequest-content (base: develop)
- sidequest-server (base: develop)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-04T22:45:09Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-04T18:00:00Z | 2026-06-04T22:22:51Z | 4h 22m |
| red | 2026-06-04T22:22:51Z | 2026-06-04T22:32:56Z | 10m 5s |
| green | 2026-06-04T22:32:56Z | 2026-06-04T22:39:47Z | 6m 51s |
| review | 2026-06-04T22:39:47Z | 2026-06-04T22:45:09Z | 5m 22s |
| finish | 2026-06-04T22:45:09Z | - | - |

## Sm Assessment

**Story:** Ground `perseus_cloud`'s named POIs (acceptance target: **New Kowloon**) as typed
`LocationEntity` declarations under the correct region in
`worlds/perseus_cloud/cartography.yaml`, then prove the **already-wired** ADR-109 consumption
path (`_authored_entities_for` → `location_resolver.resolve`) anchors them. This is a
**content-backfill-verified-by-a-wiring-test**, NOT new engine code. "Wire up what exists."

**Routing:** tdd (phased) → handing off to **TEA (Igor)** for the RED phase. Igor writes the
failing tests for AC1 (typed `entities` load through `_authored_entities_for`) and AC2 (New
Kowloon `narrator_proactive` resolve is an authored HIT, not NOT_FOUND/mint — proven via the
real tool path + `location_entity_resolve` OTEL span, with the `player_initiated` Yes-And
mint path verified un-regressed).

**Load-bearing context for downstream agents (read `context-story-71-25.md` in full):**
- The exact `region_id` for New Kowloon's churnworld region MUST be read live from
  `cartography.yaml` (~`:885`) — do NOT assume the slug.
- `LocationEntity` is `extra="forbid"` (`protocol/models.py:557`) — malformed declarations
  must fail load LOUDLY. `tier` is `real_object` | `yes_and` | `flavor_only`; a `real_object`
  SHOULD carry a `binding`. If nothing backs New Kowloon yet, `flavor_only` is the safe
  default (auto-promotes to `yes_and` on mechanical engagement) — confirm vs ADR-109's
  three-tier doctrine at design time.
- OTEL is the lie-detector (project rule): the wiring test drives the resolve through the
  REAL tool/path and asserts a manifest-HIT span, not YAML text.
- **Assumption to validate, not trust:** the `entities` path is fully wired and only data is
  missing. If `ToolContext` doesn't carry `world_id`/`genre_pack` for `perseus_cloud`, that
  wiring fix is IN SCOPE — log it as a Design Deviation and notify SM.

**Gates respected:** session created in `.session/`, fields set, context pre-existing and
validated, feature branches cut in both subrepos off `develop`, merge gate clear (only open
PR is an unrelated dependabot bump), Jira explicitly skipped (SideQuest is personal).

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (6 failing — ready for Dev/Ponder)

**Test Files:**
- `sidequest-server/tests/genre/test_perseus_cloud_poi_grounding.py` — AC1: the real
  `space_opera`/`perseus_cloud` pack loads; the `yula` region (the churnworld hosting New
  Kowloon — region_id read live from `cartography.yaml`, NOT assumed) declares typed
  `LocationEntity` rows; New Kowloon is among them (matched on the resolver's normalized
  label); and the production helper `_authored_entities_for` surfaces them (wiring test).
- `sidequest-server/tests/agents/tools/test_perseus_cloud_grounding_resolve.py` — AC2: a
  `narrator_proactive` resolve of "New Kowloon" against the real loaded manifest is an
  authored HIT (`resolved=True`, `mode_outcome="matched"`, `provenance="authored"`), proven
  end-to-end through the real `resolve_location_entity` tool via the `location.entity.resolve`
  OTEL span with **no** `location.entity.minted` span (the lie-detector), and the tool
  returns OK not NOT_FOUND.

**RED tally (measured, `uv run pytest -n0`):** 6 failed / 4 passed.
- *Failing (cover the gap — `yula.entities == []` today):*
  `test_yula_region_declares_typed_entities`, `test_new_kowloon_is_declared_as_a_typed_entity`,
  `test_authored_entities_for_surfaces_yula_pois`,
  `test_new_kowloon_proactive_resolves_as_authored_hit`,
  `test_new_kowloon_resolves_through_tool_emits_resolve_hit_span`,
  `test_new_kowloon_tool_returns_ok_not_not_found`.
- *Passing by design (guards that must stay green through GREEN):*
  `test_declared_entities_are_valid_location_entity_rows` (schema/uniqueness invariant — the
  `extra="forbid"` load-loudly edge),
  `test_declared_entities_satisfy_tier_binding_invariant` (mirrors the `pf validate locations`
  HARD-ERROR rule: `real_object`→binding, `flavor_only`→no binding — holds whichever tier the
  author picks), `test_authored_entities_for_unknown_region_returns_none` (no-silent-fallback),
  `test_undeclared_poi_player_initiated_still_mints` (AC2 edge — Yes-And mint path unbroken).

**GREEN guidance for Dev (Ponder):** This is a CONTENT backfill — add a typed `entities:`
list to the `yula` region in
`sidequest-content/genre_packs/space_opera/worlds/perseus_cloud/cartography.yaml` declaring
New Kowloon (label exactly `New Kowloon`) plus optionally the sibling districts (Santa
Abraham, Glitter, the Tether). New Kowloon is NOT in the legacy `landmarks` list (those are
planet/stations) and must NOT be added there — declare it under `entities:`. Tier: pick
`flavor_only` (no binding — safe default, auto-promotes on mechanical engagement) OR
`real_object` WITH a resolvable `binding` (the tier/binding invariant test enforces this
either way). Do NOT touch the `landmarks` field, the resolver engine, the
`location_promotions` runtime path, or other worlds. No server code change is expected — if
GREEN requires one, the "fully-wired" assumption was wrong: log a Design Deviation.

### Rule Coverage

| Rule (python lang-review) | Test(s) | Status |
|---|---|---|
| #6 Test quality — meaningful assertions, no vacuous | every test asserts a specific value/span/status; invariant guards backstopped by the existence test | enforced |
| Wiring (CLAUDE.md — every suite needs a wiring test) | `test_authored_entities_for_surfaces_yula_pois` + `test_new_kowloon_resolves_through_tool_emits_resolve_hit_span` (real tool path + OTEL span, not source grep) | failing (RED) |
| No silent fallbacks (CLAUDE.md) | `test_authored_entities_for_unknown_region_returns_none` | passing (guard) |
| OTEL lie-detector (CLAUDE.md) | `test_new_kowloon_resolves_through_tool_emits_resolve_hit_span` | failing (RED) |

**Rules checked:** test-quality + wiring + no-silent-fallback + OTEL are the applicable rules
(no net-new production `.py` in this story — GREEN is YAML content). **Self-check:** 0 vacuous
tests shipped (the two always-green invariant guards assert real invariants and are guarded by
the existence test that fails RED; they are not `assert True`/`is_none`-on-always-None).

**Handoff:** To Dev (Ponder Stibbons) for GREEN.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-content/genre_packs/space_opera/worlds/perseus_cloud/cartography.yaml` — added a
  typed `entities:` block to the `yula` region declaring the four churnworld districts named in
  its prose: **New Kowloon** (the acceptance target), Santa Abraham, Glitter, and The Tether.
  All `tier: flavor_only` (no binding — no subsystem object backs them; they auto-promote to
  `yes_and` on mechanical engagement per ADR-109). Each carries two concise genre-true
  `affordances` as anchorable grounding hooks. The legacy `landmarks` list (planet + stations)
  was left untouched; resolver engine, `location_promotions`, and other worlds untouched.

**Approach:** Pure content backfill — no server code changed (the "fully-wired" assumption
held: `load_genre_pack` → `_authored_entities_for` → `location_resolver.resolve` → the
`resolve_location_entity` tool already consume `Region.entities` end-to-end). Tier `flavor_only`
chosen per TEA/ADR-109 guidance because no `location_feature` backs these districts; the
tier/binding invariant test passes either way.

**Tests:** 10/10 passing (GREEN) — `uv run pytest -n0` on both story test files (6 previously-RED
+ 4 guards). Validator: `pf validate locations` on `space_opera` → **0 errors** (the new
entities are well-formed; declaring them also clears the yula prose-drift for those names).
**Regression sweep** (`tests/genre tests/agents/tools` + location-resolver + validate-locations
suites): **1344 passed, 49 skipped, 1 failed** — the single failure
(`test_apply_world_patch.py::test_active_stakes_path_applies`) is **pre-existing and unrelated**:
it pins the `/active_stakes` patch path that **Story 77-4 (ADR-137) deliberately removed** from
`apply_world_patch` (now `set_stakes`). It references no cartography/perseus_cloud and cannot be
affected by a content-only change. Flagged below.

**Branches (pushed):**
- `sidequest-content` `feat/71-25-perseus-cloud-poi-grounding` (content change)
- `sidequest-server` `feat/71-25-perseus-cloud-poi-grounding` (Igor's RED tests)

**Env note:** GREEN was verified via the venv pytest after `uv sync --extra dev` (see TEA's
finding); `uv run pytest` now resolves correctly to `.venv/bin/pytest`.

**Handoff:** To Igor (TEA) for the verify phase (simplify + quality-pass).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (10/10 green, ruff clean, validator 0 errors) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings — domain assessed by Reviewer |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings — domain assessed by Reviewer |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings — domain assessed by Reviewer |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings — domain assessed by Reviewer |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings — domain assessed by Reviewer |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings — domain assessed by Reviewer |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings — domain assessed by Reviewer |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings — domain assessed by Reviewer |

**All received:** Yes (1 enabled returned clean; 8 disabled via `workflow.reviewer_subagents`, their domains assessed by Reviewer below)
**Total findings:** 0 confirmed, 0 dismissed, 2 deferred (pre-existing/out-of-scope, carried as delivery findings)

## Reviewer Assessment

**Verdict:** APPROVED

A small, disciplined content backfill: 4 typed `flavor_only` `LocationEntity` rows added to
the `yula` region of `perseus_cloud/cartography.yaml`, plus two new server test files. No
production `.py` changed. Preflight clean (10/10 tests green with `SIDEQUEST_TEST_DATABASE_URL`
set, ruff clean, `pf validate locations` → **0 errors**). I independently assessed the eight
disabled specialist domains against the diff.

**Data flow traced:** narrator/player names "New Kowloon" → `resolve_location_entity` tool →
`_authored_entities_for(ctx, "yula")` walks the loaded pack → `Region.entities` (now non-empty)
→ `location_resolver.resolve` normalizes ("new kowloon") and matches the authored row →
`resolved=True, mode_outcome="matched", provenance="authored"` + `location.entity.resolve` OTEL
span (HIT), no mint. Safe: authored YAML is never mutated; the mention path does not promote.

**Observations (8+):**
- `[VERIFIED]` **Scope coverage complete** — the four declared entities (New Kowloon, Santa
  Abraham, Glitter, The Tether) are exactly the four places named in yula's description
  (`cartography.yaml:885-890`). The Yulan Governance Conglomerate is a faction (`controlled_by`),
  correctly NOT a location entity. Nothing named is left ungrounded.
- `[TEST]` `[VERIFIED]` **No vacuous tests** — the two always-green invariant guards
  (`test_declared_entities_are_valid_location_entity_rows`,
  `test_declared_entities_satisfy_tier_binding_invariant`) now iterate 4 real entities
  post-GREEN; they assert real invariants (isinstance, id-uniqueness, tier↔binding) and are
  backstopped by the existence test that failed RED. Not `assert True`/always-None. Complies
  with python lang-review #6.
- `[TYPE]` `[VERIFIED]` **Schema-valid, tier/binding invariant honored** — all 4 rows are
  `tier: flavor_only` with NO `binding` (`cartography.yaml:907-930`). `LocationEntity` is
  `extra="forbid"`; the validator's hard-error rule (`flavor_only` must NOT carry a binding,
  `real_object` MUST) is satisfied — validator reports 0 errors.
- `[EDGE]` `[VERIFIED]` **Label normalization edge** — "The Tether" normalizes to "tether"
  (leading article stripped, `location_resolver.py:47`); a narrator saying "the Tether" still
  resolves. "New Kowloon" → "new kowloon", matched case-insensitively. No id collisions (each
  id appears once in the world).
- `[SILENT]` `[VERIFIED]` **No-silent-fallback preserved** — the change is data-only; the
  resolver's unknown-region→None→NOT_FOUND path is unchanged and covered by
  `test_authored_entities_for_unknown_region_returns_none`. The Yes-And mint path stays unbroken
  (`test_undeclared_poi_player_initiated_still_mints`).
- `[DOC]` `[VERIFIED]` **Comment accuracy** — the YAML comment block
  (`cartography.yaml:904-909`) correctly states the flavor_only rationale, the auto-promote
  behavior, and that legacy `landmarks` is intentionally untouched. Not stale or misleading.
- `[SIMPLE]` `[VERIFIED]` **No over-engineering** — minimal entities block; affordances are
  authored grounding content (the substance of the story), not code abstraction. The legacy
  `landmarks` list was correctly left in place (read-only legacy).
- `[SEC]` `[VERIFIED]` **No security surface** — content YAML; affordance strings are narrator
  anchors, never executed/interpolated into queries. No secrets, no injection, no auth surface.
- `[RULE]` `[VERIFIED]` **SOUL Genre Truth + ADR-109 doctrine** — districts and affordances are
  genre-true to a cyberpunk churnworld; `flavor_only` is the correct ADR-109 tier when no
  subsystem object backs a place (auto-promotes on mechanical engagement = Diamonds-and-Coal).
- `[LOW]` **CI env note** (deferred): the AC2 tests live under `tests/agents/tools/` whose
  autouse `_pg_isolation` fixture requires `SIDEQUEST_TEST_DATABASE_URL`; without it the 4 AC2
  tests SKIP (not fail). CI must set it. Already captured in TEA's delivery finding.

### Rule Compliance

| Rule (source) | Applies to | Verdict |
|---|---|---|
| ADR-109 three-tier doctrine — `real_object`⇒binding, `flavor_only`⇒no binding | all 4 entities | ✓ compliant (all flavor_only, no binding) |
| `pf validate locations` well-formedness (hard error) — unique ids, schema-valid | yula entities | ✓ compliant (validator: 0 errors) |
| CLAUDE.md No Silent Fallbacks | resolver path (unchanged) | ✓ compliant (unknown-region→None tested) |
| CLAUDE.md "Don't reinvent — wire up what exists" | whole story | ✓ compliant (data-only; no engine code added) |
| python lang-review #6 (test quality) | 2 new test files | ✓ compliant (no vacuous assertions) |
| SOUL Genre Truth / Diamonds-and-Coal | entity flavor + affordances | ✓ compliant (genre-true churnworld POIs) |

### Devil's Advocate

Let me argue this is broken. First: the author chose `flavor_only` for places the party can
physically occupy — New Kowloon is a *district*, not a prop like "cobwebs." Could a narrator
resolve "New Kowloon" with `engagement_kind="mechanical"` (about to fight or move there) and
trigger an auto-promotion to `yes_and` that the AC's "provenance=authored" expectation didn't
account for? Examined: that is exactly the intended Diamonds-and-Coal behavior — the entity is
still grounded (`resolved=True`); promotion is canonization, not a miss. The AC tests the
mention path explicitly, and the mechanical-promote path is a feature, not a regression. Not a
bug. Second: could declaring "Glitter" as an entity collide with the history.yaml POI slug
'glitter' and double-render or confuse the POI image pipeline? Examined: the location-entity
manifest and the POI-image slug system are separate; preflight confirmed the unmatched-slug
warnings are pre-existing (history named them first) — declaring the entity neither creates nor
worsens them. Third: a confused author later adds a `binding` to one of these flavor_only rows —
would it silently corrupt? No: the validator's hard-error rule rejects `flavor_only`+binding at
author time, and `test_declared_entities_satisfy_tier_binding_invariant` would fail. Fourth:
what if the yula region id the narrator passes at runtime isn't "yula"? The tests bind to the
live cartography key, and the wiring test drives the real `_authored_entities_for`; a region-id
mismatch would fail the wiring test, not silently no-op. Fifth: stressed loader — a YAML typo
would raise at `load_genre_pack` (extra="forbid"), caught by the existence test. I cannot
manufacture a failure here. The change is additive, schema-checked, validator-clean, and
behavior-proven through the real tool path with OTEL. It holds.

**Handoff:** To SM (Captain Carrot) for finish-story.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): the oq-2 server venv lacked the `dev` extra, so `uv run pytest`
  silently fell through to a broken global `~/.local/bin/pytest` (opentelemetry namespace
  shadow, `ModuleNotFoundError: No module named 'opentelemetry'`) — affecting *all* server
  tests, not just this story. Fixed by `uv sync --extra dev` (installs pytest 9.0.3 into
  `.venv`). Affects the GREEN/verify runs and the testing-runner: run `uv sync --extra dev`
  first, set `SIDEQUEST_TEST_DATABASE_URL=postgresql://$USER@localhost:5432/sidequest_test`,
  and invoke via the venv (`uv run pytest`). *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (non-blocking): `tests/agents/tools/test_apply_world_patch.py::test_active_stakes_path_applies`
  is a stale pre-existing failure on server develop — it asserts the `/active_stakes` patch path
  applies via `apply_world_patch`, but Story 77-4 (ADR-137 AC-3) deliberately REMOVED that path
  (now `ERROR_RECOVERABLE`, "use `set_stakes`"; see `apply_world_patch.py:119`). The test pins
  removed behavior and was not updated when 77-4 landed. Affects
  `sidequest-server/tests/agents/tools/test_apply_world_patch.py` (update or delete the test to
  assert the path is now rejected). Unrelated to 71-25 — left for the epic-77 owner.
  *Found by Dev during implementation.*
- **Improvement** (non-blocking): perseus_cloud `history.yaml` declares POI image slugs
  (`new-kowloon`, `santa-abraham`, `glitter`, …) with no matching location card in
  `locations.yaml`, so their landscape images can never render (`POI_IMAGE_SLUG_UNMATCHED`
  warnings). This is the asset-gate concern explicitly OUT OF SCOPE for 71-25 (grounding ≠
  rendering), but now that these POIs are grounded entities, wiring matching `locations.yaml`
  cards is the natural follow-up. Affects
  `sidequest-content/genre_packs/space_opera/worlds/perseus_cloud/locations.yaml`.
  *Found by Dev during implementation.*

### Reviewer (code review)
- No new upstream findings. The two carried items — the stale 77-4
  `test_active_stakes_path_applies` failure and the perseus_cloud POI-image-slug follow-up — are
  pre-existing/out-of-scope and already logged by Dev; I confirm both and defer them.
  *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Test files live in sidequest-server, not sidequest-content**
  - Spec source: context-story-71-25.md, "In scope" + repos `sidequest-content,sidequest-server`
  - Spec text: "Declare … typed `entities:` in `cartography.yaml` … plus verifying the existing
    consumption path picks them up"
  - Implementation: the GREEN content edit lands in `sidequest-content` (cartography.yaml); the
    verifying tests land in `sidequest-server` (the loader + resolver + tool live there). RED
    commit is server-only.
  - Rationale: the consumption path under test (`load_genre_pack`, `_authored_entities_for`,
    `location_resolver.resolve`, the `resolve_location_entity` tool, OTEL spans) is all
    server-side; tests must run against it. Content carries no test harness.
  - Severity: minor
  - Forward impact: GREEN spans two repos — Dev edits content YAML, runs the server tests;
    SM creates a PR in each subrepo at finish.
- **Two always-green invariant guards included alongside the 6 RED tests**
  - Spec source: context-story-71-25.md, AC1 edge ("extra=forbid … fail load loudly") + AC2
    edge ("player_initiated … must still mint")
  - Spec text: "malformed declarations must fail load loudly"; "the Yes-And path is unbroken"
  - Implementation: `test_declared_entities_*` (schema + tier/binding invariants) and
    `test_undeclared_poi_player_initiated_still_mints` pass at RED and must stay green at GREEN
    — they are regression/invariant guards, not gap-coverage.
  - Rationale: the edges are "must NOT break" properties; the correct TDD shape for a
    must-not-break property is a green guard, backstopped by the gap-coverage existence test
    that fails RED.
  - Severity: minor
  - Forward impact: none — Reviewer should expect 4 green + 6 red at RED, all 10 green at GREEN.

### Dev (implementation)
- **Grounded all four yula districts, not New Kowloon alone**
  - Spec source: context-story-71-25.md, "In scope" + "Out of scope"
  - Spec text: "grounds the world's named POIs (New Kowloon as the named acceptance target)";
    "an exhaustive landmark→entity migration of all 34 regions is not required"
  - Implementation: declared New Kowloon + Santa Abraham + Glitter + The Tether (the four
    districts named in the yula description), all in the single acceptance region.
  - Rationale: these four are one coherent prose sentence describing yula; grounding only New
    Kowloon would leave its siblings still re-improvised. This is the named-POIs-of-the-region
    scope, NOT the disallowed all-34-region migration.
  - Severity: minor
  - Forward impact: none — strictly additive content under one region.
- **Added `affordances` to each entity (not required by any test)**
  - Spec source: context-story-71-25.md, AC1 ("a fixed set to reference") + LocationEntity schema
  - Spec text: "gives the narrator a fixed set to reference"
  - Implementation: two concise snake_case affordances per district (e.g.
    `thread_the_superblock_stacks`). Tests assert only id/label/tier/binding.
  - Rationale: affordances are the authored grounding hooks the narrator anchors to — the
    substance of the story, matching the existing backfilled shape (beneath_sunden, wonderland);
    they are content, not code abstraction/scope-creep.
  - Severity: minor
  - Forward impact: none — free-form flavor; no consumer requires specific affordance strings.

### Reviewer (audit)
- **TEA: Test files live in sidequest-server, not sidequest-content** → ✓ ACCEPTED by Reviewer:
  the consumption path under test (loader, resolver, tool, OTEL) is all server-side; content
  carries no harness. Correct placement.
- **TEA: Two always-green invariant guards alongside the 6 RED tests** → ✓ ACCEPTED by Reviewer:
  the must-not-break edges (schema/extra=forbid, tier↔binding, Yes-And mint) are correctly
  modeled as green guards backstopped by the RED existence test. Confirmed non-vacuous post-GREEN.
- **Dev: Grounded all four yula districts, not New Kowloon alone** → ✓ ACCEPTED by Reviewer:
  the four are one prose sentence describing yula; grounding only one would leave siblings
  re-improvised. This is the named-POIs-of-the-region scope, NOT the disallowed all-34-region
  migration. Genre-true and additive.
- **Dev: Added `affordances` to each entity (not required by any test)** → ✓ ACCEPTED by
  Reviewer: affordances are the authored grounding hooks the narrator anchors to — the substance
  of the story — and match the existing backfilled shape (beneath_sunden, wonderland). Content,
  not code scope-creep.
- No undocumented deviations found: the diff matches the spec (typed `entities:` under the
  acceptance region, `flavor_only` per ADR-109, legacy `landmarks` untouched, no engine code).