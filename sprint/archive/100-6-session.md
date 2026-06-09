---
story_id: "100-6"
jira_key: ""
epic: "100"
workflow: "tdd"
---
# Story 100-6: Phase 1 — Rules page JSON projection API + firewall reuse (/reference/api/rules/{pack})

## Story Details
- **ID:** 100-6
- **Jira Key:** (not in use)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** red
**Phase Started:** 2026-06-09T08:26:42Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| red | 2026-06-09T08:26:42Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Reviewer (code review) — 2026-06-09

- **Gap** (blocking): The obstacle-keeper firewall assertion is **vacuous**. `_KEEPER_OBSTACLE_STAT` contains an em-dash (—, U+2014); the keeper-absence checks compare against `json.dumps(...)` with the default `ensure_ascii=True`, which escapes the em-dash to `—`, so `_KEEPER_OBSTACLE_STAT not in blob` is vacuously True even when the field fully leaks. Proven end-to-end: with the `beat_vocabulary.obstacles` carves removed, `stat_check` STRUCTURALLY leaks into the `/reference/api/rules/{pack}` JSON payload, yet `test_generic_yaml_beat_vocabulary_blocks_obstacles`, `test_rules_projection_whole_doc_no_keeper_leak`, and `test_rules_api_endpoint_scrubs_keeper_fields` all still PASS. The obstacle carve breaks 0 tests when removed = vacuous guard. Root cause ties to TEA deviation note (keeper strings lifted verbatim from space_opera — the lifted string carries an em-dash). Affects `tests/server/test_reference_rules_projection.py`. Test-side (TEA). Fix (both verified to catch the leak): use `ensure_ascii=False` on every keeper-absence `json.dumps`, or assert structurally over the projected dict's leaf values. *Found by Reviewer during code review.*
- **Verified good** (non-blocking): narrator_hint and power_tiers.npc carves are genuinely guarded — mutation-removing each produces real test failures (B1: 4 failed, B2: 3 failed). Wiring is genuine: `/reference/api/rules/{pack}` reachable via `create_reference_router()` → `app.include_router`; a raw-splat mutation correctly fails the endpoint firewall test. Dev's `_seed_pack` edits STRENGTHENED the two endpoint tests (made the keeper assertions actually reachable; no assertion weakened). Full suite 10251 passed / 1538 skipped / 0 failed; ruff format + check clean. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Keeper carves pre-exist (no classify() change needed):** Unlike 100-5 (which *added* a `related_tropes` KEEPER carve), the rules-tier spoiler fields are already carved KEEPER in `reference_visibility.py` from prior stories: `rules` confrontations/edge/resources `narrator_hint`, `power_tiers.*.*.npc`, `beat_vocabulary.obstacles`. Verified all three fire `Visibility.KEEPER` against my fixture key-paths. So 100-6 needs NO firewall code — only reuse of `build_generic_yaml_section`. The firewall tests are therefore meaningful in a different way: they guard against a **raw-splat** projector (`yaml.safe_load` → `JSONResponse`) that bypasses the firewall. Non-vacuity is proven by `test_raw_splat_would_leak_narrator_hint_but_projection_does_not` (positive control: keeper value IS in raw YAML; firewalled projection scrubs it).
- **No live-pack assertions (AC5 reinterpreted):** AC5 says "verify end-to-end against a live pack (e.g. space_opera)." The project rule *no assertions against live genre_packs* + the prod-rows-in-tests prohibition override the literal AC. The end-to-end test points the real FastAPI router at a SYNTHETIC tmp pack whose rules.yaml/power_tiers.yaml/beat_vocabulary.yaml mirror space_opera's real keeper-field SHAPES; the keeper STRINGS asserted-absent are lifted verbatim from space_opera for fidelity. This matches the 100-2..100-5 pattern (real slug names, synthetic tmp content).
- **Rework (review round 1 — `b12945e5`): fixed vacuous obstacle firewall.** Reviewer correctly flagged that the lifted `_KEEPER_OBSTACLE_STAT` carries an em-dash (U+2014); `json.dumps`'s default `ensure_ascii=True` escaped it to `—`, so the obstacle keeper-absence checks were vacuously True (removing the carve broke 0 tests). Fix: added a `_blob(obj)` helper using `ensure_ascii=False` and routed every keeper-absence + public-presence substring assertion through it. **Mutation-verified non-vacuity:** removing the `beat_vocabulary.obstacles` carves now fails the 3 obstacle-guarding tests; restoring makes them green. Lesson for future TEA test design: when asserting substring-absence against `json.dumps` output, ALWAYS use `ensure_ascii=False` (or assert structurally) — verbatim-lifted real content can carry non-ASCII (em-dashes, smart quotes) that the default escaping hides.

### Dev (implementation)
- **Added missing `_seed_pack` setup to two of TEA's HTTP-endpoint tests**
  - Spec source: `tests/server/test_reference_rules_projection.py` (TEA RED suite, commit bd24db97), `test_rules_api_endpoint_returns_sections` + `test_rules_api_endpoint_scrubs_keeper_fields`
  - Spec text: both tests' docstrings say the endpoint is "pointed at a synthetic pack mirroring space_opera's keeper-field shapes" and assert `resp.status_code == 200`
  - Implementation: both tests called `_client(tmp_path)` against an **empty** tmp root — `_seed_pack(tmp_path)` was never invoked, so `_resolve_pack_dir` correctly 404'd (no `space_opera` dir on disk) and the `== 200` assertion failed against any correct implementation. Added the one-line `_seed_pack(tmp_path)` setup before `_client(tmp_path)` in both.
  - Rationale: TEA test defect — the synthetic pack the docstrings describe was never written to disk. The fix *strengthens* the firewall assertions (the endpoint now actually serves and scrubs the keeper-bearing pack) rather than weakening any security check. The 10 other tests (which seed correctly) were unaffected.
  - Severity: minor
  - Forward impact: none — test-only setup correction; no production-code or contract change.

## TEA Assessment

**Tests Required:** Yes
**Reason:** New public JSON projection endpoint with a security firewall — exactly the surface a paranoid test suite must guard.

**Test Files:**
- `tests/server/test_reference_rules_projection.py` — 13 tests across 3 groups (projector basics/shape, keeper firewall, production HTTP wiring).

**Tests Written:** 13 tests covering AC1 (endpoint), AC2 (firewall reuse), AC3 (data shape mirrors RULES_FILES generic-YAML), AC4 (public, 404 on unknown pack), AC5 (end-to-end keeper scrub through the real router).
**Status:** RED — `ImportError: cannot import name 'build_rules_projection'` (collection-level; the contract symbol + route do not exist yet). Verified the existing `classify()` carves fire on all fixture key-paths, so the firewall + wiring tests pass once Dev routes the projector through `build_generic_yaml_section`.

**Contract pinned for Dev:**
- `build_rules_projection(pack: str, *, pack_dir: Path) -> dict` in `reference_projection.py` → `{"schema_version": 1, "pack": str, "sections": [...]}` (NO `world` key — pack-tier). Loop over present `RULES_FILES` (skip `EXCLUDED_FILES`), project each via `build_generic_yaml_section`; omit empty sections.
- `GET /reference/api/rules/{pack}` route in `reference_routes.py` → `JSONResponse`; public; 404 on unknown pack via `_resolve_pack_dir`.
- Keeper fields (already carved): `rules`→`narrator_hint`, `power_tiers.*.*.npc`, `beat_vocabulary.obstacles`. No `classify()` change required.

**Handoff:** To Dev for GREEN implementation.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/server/reference_projection.py` — added `build_rules_projection(pack, *, pack_dir)`: pack-tier loop over `RULES_FILES` (skip `EXCLUDED_FILES`), each file routed through the existing `build_generic_yaml_section(..., world="")` firewall; returns `{"schema_version": 1, "pack", "sections": [...]}` with **no `world` key**. Added `RULES_FILES` to the `reference_renderer` import.
- `sidequest/server/reference_routes.py` — added `GET /reference/api/rules/{pack}` (`rules_api`) mirroring `lore_api`: `_resolve_pack_dir` (404 on unknown pack) → `build_rules_projection` → `JSONResponse`, with the same `(ValueError, MissingThemeFieldError) → 500` try/except. Imported `build_rules_projection`; updated the module docstring route list.
- `tests/server/test_reference_rules_projection.py` — added the missing `_seed_pack(tmp_path)` setup to two HTTP-endpoint tests (see Design Deviations).

**No `classify()` change** — reused the pre-existing rules-tier keeper carves (TEA's design). The firewall is automatic because every section routes through `build_generic_yaml_section`; a raw splat would leak (pinned by `test_raw_splat_would_leak_*`).

**Tests:** 12/12 passing in `tests/server/test_reference_rules_projection.py` (TEA's "13" was an off-by-one miscount — the file defines 12 test functions). Full server suite: **10252 passed, 1537 skipped, 0 failed** (DB + genre packs env). `ruff format --check` + `ruff check` clean on all 3 diff files.
**Branch:** feat/100-6-rules-page-json-projection (pushed)

**Handoff:** To review (Reviewer).
