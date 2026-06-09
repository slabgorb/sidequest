---
story_id: "98-1"
jira_key: ""
epic: ""
workflow: "tdd"
---
# Story 98-1: C1 Content — split perseus_cloud orbits.yaml into systems/<id>.yaml, delete fake root, author yula

## Story Details
- **ID:** 98-1
- **Jira Key:** (None — no Jira integration)
- **Workflow:** tdd
- **Type:** refactor
- **Points:** 3
- **Stack Parent:** none
- **Repo:** sidequest-content

## Story Summary

Implement ADR-141 content-authoring slice: split the existing `perseus_cloud/orbits.yaml` (monolithic 140-body orrery) into per-system files under `worlds/perseus_cloud/systems/<id>.yaml`. Delete the fabricated `perseus_cloud` primary tier. Author the `yula` system as the first per-system file, re-homing its primary and children from the monolith into the new file.

**Scope boundary:** `yula` only (5 bodies total: primary star + 1 habitat + 3 sub-habitats). Other 34 systems remain unwritten (Diamonds and Coal — authored on demand).

## Acceptance Criteria

- AC1: `systems/yula.yaml` exists at `worlds/perseus_cloud/systems/yula.yaml`; contains `yula` primary (no parent) as the single root, with `yula_2`, `lisbon`, `mclaughlin_13`, `thule_7` as re-homed children (parent linkages updated to point to `yula` or intermediate parents, not to `perseus_cloud`)
- AC2: The fabricated `perseus_cloud` primary (orbits.yaml line 17, `type: star`, label "PERSEUS CLOUD") is deleted — no body in any system file parents to it anywhere
- AC3: `yula.yaml` carries `clock.epoch_days` and per-body `period_days` + `epoch_phase_deg` (calendar linkage preserved — ADR-130)
- AC4: Monolithic `orbits.yaml` removed entirely for perseus_cloud (or emptied to a retirement stub documenting the split — server story S1 decides which the loader tolerates; **prefer outright removal**)
- AC5: The other ~33 systems remain unwritten (Diamonds-and-Coal — authored on demand via future stories)

## Workflow Tracking

**Workflow:** tdd  
**Phase:** finish  
**Phase Started:** 2026-06-09T11:55:36Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-09 | 2026-06-09T11:35:25Z | 11h 35m |
| red | 2026-06-09T11:35:25Z | 2026-06-09T11:43:07Z | 7m 42s |
| green | 2026-06-09T11:43:07Z | 2026-06-09T11:47:42Z | 4m 35s |
| review | 2026-06-09T11:47:42Z | 2026-06-09T11:55:36Z | 7m 54s |
| finish | 2026-06-09T11:55:36Z | - | - |

## Technical Approach

1. **Extract yula subtree from existing orbits.yaml** — Identify all bodies where `yula` is an ancestor (direct parent or root of subgraph). Current structure:
   - `yula` (primary star, `type: star`, currently has `parent: perseus_cloud` — remove)
   - `yula_2` (habitat, currently `parent: yula` — keep)
   - `lisbon`, `mclaughlin_13`, `thule_7` (habitats, currently `parent: yula_2` — keep)

2. **Create `systems/yula.yaml`** — New file structure:
   ```yaml
   version: "0.1.0"
   clock:
     epoch_days: 0
   travel:
     realism: narrative
   bodies:
     yula:
       type: star
       semi_major_au: 8.343
       period_days: 8801.8
       epoch_phase_deg: 209.7
       label: "YULA"
     yula_2:
       type: habitat
       parent: yula
       semi_major_au: 0.45
       period_days: 110.3
       epoch_phase_deg: 344
       label: "YULA"
     lisbon:
       type: habitat
       parent: yula_2
       [... remaining fields ...]
   ```
   - Copy orbital mechanics fields (`semi_major_au`, `period_days`, `epoch_phase_deg`)
   - Copy all body type / label / hazard fields
   - Update all `parent:` references: `yula` becomes root (no parent), children parent to `yula` or intermediate bodies as before

3. **Delete the fabricated `perseus_cloud` primary** — Search orbits.yaml for the entry at ~line 17; remove it entirely. Verify no bodies still reference `parent: perseus_cloud`.

4. **Decide on orbits.yaml disposal** — ADR-141 spec leaves loader tolerance to S1 story (98-2). For content authoring:
   - **Option A (preferred):** Delete orbits.yaml entirely if loader handles missing per-world root gracefully
   - **Option B:** Empty orbits.yaml to a stub comment documenting the split (if loader still expects the file to exist)
   - Decision: Verify with S1 story owner; for now, include a decision note in the session file

5. **Verify calendar linkage** — Ensure `clock.epoch_days` and per-body `period_days` + `epoch_phase_deg` are preserved exactly (no transformation); these feed ADR-130 clock math for body position calculation.

6. **Verify adjacency consistency** — Check cartography.yaml: `yula` region should have `adjacent: ['amanta', 'nimia', 'terma']` (as confirmed during research). No system-file change is needed; adjacency lives on cartography.yaml regions, not orrery bodies.

## Delivery Findings

- **ADR-141 spec reconciliation (from epic design doc, §2–3):**
  - Loader target seam is `orbital/loader.py:42` (currently hard-coded `world_dir / "orbits.yaml"`), not course.py
  - `system_root()` in render.py:132 stays unchanged; one parent-less primary per system file satisfies existing contract
  - Connectivity stays on `cartography.yaml` `adjacent:` (already feeds movement.py); `routes:` edges carry jump mechanics (C2/S2 stories)
- **Content structure verified:** yula subtree contains exactly 5 bodies; no cross-dependencies with other systems
- **Cartography adjacency:** yula has 3 neighbors (amanta, nimia, terma); Black Door special route is zephyr↔ceron (not yula)

<!-- TEA delivery findings below -->
### TEA (test design)
- **Improvement** (non-blocking): The production loader `load_orbital_content` still hard-codes `world_dir / "orbits.yaml"` (loader.py:42). Per-system resolution of `systems/<id>.yaml` is S1's job (98-2), so the wiring test (`test_yula_consumable_by_production_loader`) stages the authored file as `orbits.yaml` in a tmp dir to exercise the real loader today. Affects `sidequest-server/sidequest/orbital/loader.py` (S1 rewires it to resolve per-system files). *Found by TEA during test design.*
- **Gap** (non-blocking): This is effectively a **two-repo story** despite the `content` repo tag — Dev edits `sidequest-content` (author yula.yaml, remove fabricated root) and the failing tests sit on a `sidequest-server` feature branch. Affects sprint finish ceremony (both branches need PRs/merge). *Found by TEA during test design.*
- **Question** (non-blocking): AC4 leaves delete-vs-stub of `orbits.yaml` to S1. The tests tolerate **both** (delete preferred; a stub passes iff the fabricated `perseus_cloud` cluster is gone). Dev should default to **outright deletion** unless S1 explicitly needs the stub. *Found by TEA during test design.*

<!-- Dev delivery findings below -->
### Dev (implementation)
- **Gap** (blocking for S1, non-blocking for this story): Deleting `perseus_cloud/orbits.yaml` means perseus_cloud has **no orbital chart at runtime until S1 (98-2) rewires the loader** to resolve `systems/<id>.yaml`. `session_room.py:259` catches `OrbitalContentMissingError` and degrades gracefully (`orbital_content=None`, chart UI unavailable, no crash, debug-logged), so it is fail-soft, not fail-loud-broken. But `rest.py` also calls `load_orbital_content` — S1 must confirm its chart endpoint degrades equally gracefully. Affects `sidequest-server/sidequest/orbital/loader.py` + `rest.py` (S1 scope). This is the inherent C1→S1 sequencing gap, not a defect. *Found by Dev during implementation.*
- **Improvement** (non-blocking): The other ~33 systems' synthesized geometry left the repo with the monolith. It is fully regenerable from `perseus_cloud.sector.json` (still present, 195KB) and recoverable from git history. When future stories author them, mirror the `yula.yaml` shape. *Found by Dev during implementation.*

<!-- Reviewer delivery findings below -->
### Reviewer (code review)
- **Improvement** (non-blocking): `test_perseus_cloud_systems_split.py` is the **template** future per-system stories will copy (~33 more systems). Five cheap test-polish items are worth landing before it's cloned, ideally as a quick touch-up: (1) add `encoding="utf-8"` to the three file reads (`path.open()` L126, `read_text()` L239/L278) — lang-review Python rule #5; (2) drop the vacuous `assert isinstance(yula_orbits, OrbitsConfig)` L158 (the `.version` assert beside it is the real check) — rule #6; (3) parameterize `yula_raw` return type `dict` → `dict[str, object]` L119 — rule #3; (4) replace the silent `or {}` at L278 with an explicit empty-file assert; (5) add a story-scope comment on `test_only_yula_system_is_authored` L358 so the exact-`["yula.yaml"]` assertion's expected breakage on the next system file is self-documenting. Affects `sidequest-server/tests/orbital/test_perseus_cloud_systems_split.py`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): The grep test `test_perseus_cloud_world_has_no_parent_perseus_cloud_anywhere` uses a substring match over ALL `*.yaml` in the world dir; as more orrery files and narrative YAML accrue it could miss quoted parent variants (`parent: "perseus_cloud"`) or false-positive on a narrative string. Consider scoping to `systems/*.yaml`+`orbits.yaml` and/or a model-level parse check when the next system is authored. Affects same file. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Pre-existing (NOT this story) — `BodyDef.register` field shadows a `BaseModel` attribute, emitting a `UserWarning` on every orbital test run. Affects `sidequest-server/sidequest/orbital/models.py:54`; worth a separate cleanup. *Found by Reviewer during code review (preflight).*

## Design Deviations

### TEA (test design)
- **Tests authored in `sidequest-server`, not the `content` repo of record**
  - Spec source: session file `**Repo:** sidequest-content`; context-story-98-1.md "Testing Approach (RED phase)"
  - Spec text: story repo is `content`; deliverable is `systems/yula.yaml`
  - Implementation: RED tests live at `sidequest-server/tests/orbital/test_perseus_cloud_systems_split.py`, on a parallel `feat/98-1-...` branch in the server repo
  - Rationale: `sidequest-content` has **no test harness** (no pyproject/pytest/justfile). The production code that parses and consumes these files — `OrbitsConfig`, `load_orbital_content`, `_resolve_scope_center` — lives in the server. Testing the content *through its real consumer* is the wiring-correct path per CLAUDE.md "Verify Wiring, Not Just Existence"; the established precedent is `tests/orbital/test_render_coyote_star.py`, which already validates real world content from the server side.
  - Severity: minor
  - Forward impact: This is a **two-repo story**. Dev authors `systems/yula.yaml` + removes the fabricated root on the content branch; the server-branch test goes GREEN as a result. Both branches need PRs. Reviewer/SM-finish must track both.

- **Fixture-setup `errors` used as RED signal for the 23 file-dependent tests**
  - Spec source: TDD policy (RED = failing tests before implementation)
  - Spec text: "Failing tests ready for Dev (RED state)"
  - Implementation: the `yula_raw` fixture asserts the file exists; when absent it raises at setup, so pytest reports those 23 as `errors`, not `failures` (the 4 file-independent tests report as `failures`)
  - Rationale: a single fixture guard keeps each test body clean and yields one unambiguous "not authored yet" message per test. Errors-at-setup are a valid not-passing signal; all 27 flip to PASS once the file exists.
  - Severity: minor
  - Forward impact: none — GREEN is a clean pass once `yula.yaml` lands.

### Dev (implementation)
- No deviations from spec. Authored `systems/yula.yaml` with the five bodies and exact source values (root `yula` keeps its source orbital params per `test_yula_orbital_mechanics_exact`, harmless for a root since `position.py` centers parent-less bodies). Took AC4's **preferred** path — deleted `orbits.yaml` outright rather than stubbing.

### Reviewer (audit)
- **TEA: Tests authored in `sidequest-server`, not the `content` repo of record** → ✓ ACCEPTED by Reviewer: content has no test harness; testing content through its real production consumers (`OrbitsConfig`/`load_orbital_content`/`_resolve_scope_center`) is the wiring-correct path and matches the `test_render_coyote_star.py` precedent. The two-repo PR coordination is the only cost, already captured as a Delivery Finding.
- **TEA: Fixture-setup `errors` used as RED signal** → ✓ ACCEPTED by Reviewer: errors-at-setup are a valid not-passing signal; all 27 flipped to clean PASS at GREEN (verified by preflight: 27/27). No lingering effect.
- **Dev: AC4 — deleted `orbits.yaml` outright rather than stubbing** → ✓ ACCEPTED by Reviewer: AC4 explicitly prefers deletion. Verified fail-soft: `session.py:198` checks `orbital_content is None` and returns `False` *before* the init no-match raise (`session.py:210`), so post-deletion perseus_cloud connects cleanly to the documented no-orbital-tier no-op — no crash, no spurious fail-loud. Runtime chart-unavailability until S1 is the inherent epic sequencing gap, not a defect.
- No undocumented deviations found. The deliverable matches every AC.

---

## Sm Assessment

Setup is clean and ready for RED. This is a 3pt pure-content refactor in `sidequest-content` only — split the monolithic perseus_cloud `orbits.yaml` into per-system files, author `yula` as the first one, and delete the fabricated `perseus_cloud` primary tier. ADR-141 is accepted (2026-06-08) and the epic design spec is the authority.

- **Scope is tight and well-bounded:** yula only (5 bodies), other ~33 systems deferred per Diamonds-and-Coal. No code changes — this is YAML authoring.
- **Five concrete ACs** are written, each independently checkable. The sm-setup research already verified the yula subtree (5 bodies, no cross-system deps), confirmed the fabricated primary at orbits.yaml:17, and located the loader seam (`orbital/loader.py:42`) that S1 will own.
- **One open decision deferred to S1 (98-2):** whether to delete `orbits.yaml` outright or leave a retirement stub — AC4 prefers outright removal. TEA/Dev should not block on this; preferred path is delete.
- **TDD on content:** the testable surface is structural — a test asserting `systems/yula.yaml` parses, has `yula` as the sole parent-less root, preserves calendar fields (`epoch_days`/`period_days`/`epoch_phase_deg`), and that no body anywhere parents to `perseus_cloud`. That's the wiring test too: the file must be discoverable where the loader will look.

No blockers. Merge gate clear, no open PRs. Handing to TEA for RED.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Content has a real, testable structural contract — the per-system file must parse through the production orbital model and resolve to a single system root.

**Test Files:**
- `sidequest-server/tests/orbital/test_perseus_cloud_systems_split.py` — 27 tests (on `feat/98-1-...` branch in the **server** repo; see Design Deviations for why server, not content)

**Tests Written:** 27 tests covering all 5 ACs + wiring
**Status:** RED (verified — 4 failures + 23 fixture-setup errors, all naming the missing `systems/yula.yaml` / lingering fabricated root)

### AC Coverage

| AC | Test(s) | Status |
|----|---------|--------|
| AC1 file + hierarchy | `test_yula_system_file_exists`, `test_yula_validates_as_production_orbits_config`, `test_yula_has_exactly_five_bodies`, `test_yula_is_the_sole_parentless_root`, `test_yula_root_is_a_star`, `test_yula_parent_linkages[5]`, `test_yula_orbital_mechanics_exact[5]` | RED |
| AC2 fabricated root deleted | `test_yula_has_no_perseus_cloud_body`, `test_no_body_in_yula_parents_to_perseus_cloud`, `test_perseus_cloud_world_has_no_parent_perseus_cloud_anywhere` | RED |
| AC3 calendar linkage | `test_yula_clock_epoch_days_preserved`, `test_orbiting_bodies_carry_calendar_fields[4]` | RED |
| AC4 orbits.yaml disposal | `test_monolithic_orbits_yaml_no_longer_holds_fabricated_cluster` (tolerates delete **or** stub) | RED |
| AC5 no other systems | `test_only_yula_system_is_authored` | RED |
| Wiring | `test_yula_consumable_by_production_loader` (real `load_orbital_content`), `test_renderer_root_resolver_picks_yula` (real `_resolve_scope_center`) | RED |

### Rule Coverage

| Rule (CLAUDE.md) | How enforced | Status |
|------|---------|--------|
| Verify Wiring, Not Just Existence | Tests exercise `OrbitsConfig.model_validate`, `load_orbital_content`, `_resolve_scope_center` — the real consumers, not isolated YAML checks | RED |
| No Source-Text Wiring Tests | No `read_text()` grep of *production source*; the one rglob grep is over **content YAML** (the deliverable), asserting an AC2 data invariant, not implementation shape | satisfied |
| No Stubbing / Diamonds & Coal | `test_only_yula_system_is_authored` fails if any skeleton `<system>.yaml` appears | RED |
| No Silent Fallbacks | Relies on `OrbitsConfig` `extra="forbid"` + parent-ref validation to reject malformed/dangling content loudly | RED |

**Self-check:** Reviewed all 27 tests — every test has a meaningful assertion; no `assert True`, no vacuous `is_none()`, no `let _ =` equivalents. The "clean parse" tests (`test_yula_validates_*`) assert on the returned object, and the parametrized exactness tests pin literal source values to catch transcription drift.

**Paranoia notes for Dev (GREEN):**
- Copy orbital values **verbatim** — `test_yula_orbital_mechanics_exact` pins `period_days`/`epoch_phase_deg`/`semi_major_au`/`label` to source (e.g. `yula` = 8.343 / 8801.8 / 209.7). A fat-fingered digit fails.
- `yula` is the **root**: drop its `parent:` field entirely (don't set `parent: null` — `extra="forbid"` allows the field absent; absent is cleanest and is what `_validate_parent_refs` expects).
- Removing the fabricated root means **deleting `orbits.yaml`** (preferred) so AC2's world-wide grep passes — the old file still contains 33 `parent: perseus_cloud` lines.

**Handoff:** To Dev (Bicycle Repair Man) for GREEN — author `systems/yula.yaml` in content, delete the fabricated root, watch all 27 server tests go green.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed (two repos):**
- `sidequest-content/genre_packs/space_opera/worlds/perseus_cloud/systems/yula.yaml` — **created**. First per-system orrery file: `yula` (star, root) + `yula_2` (habitat) + `lisbon`/`mclaughlin_13`/`thule_7` (sub-habitats). All orbital values copied verbatim from the monolith.
- `sidequest-content/genre_packs/space_opera/worlds/perseus_cloud/orbits.yaml` — **deleted** (AC4 preferred path). Removed the fabricated `perseus_cloud` star and the 34-system fake-solar-system structure (42 `parent: perseus_cloud` lines gone).
- `sidequest-server/tests/orbital/test_perseus_cloud_systems_split.py` — TEA's 27 RED tests, now GREEN (committed in RED phase on the server branch).

**Tests:** 27/27 passing (GREEN). Regression: full `tests/orbital/` suite **355/355** green — deleting the monolith broke nothing (`test_scope_bind.py` uses a synthetic fixture, not real content).

**Branches (pushed, both repos):**
- content: `feat/98-1-split-perseus-cloud-systems-author-yula` → commit `7b9d5c5`
- server: `feat/98-1-split-perseus-cloud-systems-author-yula` → commit `48d2711e`

**AC verification:**
- AC1 ✓ yula.yaml created, 5 bodies, correct hierarchy, exact orbital mechanics
- AC2 ✓ fabricated `perseus_cloud` primary gone; zero `parent: perseus_cloud` world-wide
- AC3 ✓ `clock.epoch_days` + per-body `period_days`/`epoch_phase_deg` preserved
- AC4 ✓ `orbits.yaml` deleted outright (preferred)
- AC5 ✓ only `yula.yaml` authored; no skeleton files for other systems

**Note for Reviewer/SM:** Two-repo story — both feature branches need PRs and must merge together (or content-then-server). See Delivery Findings re: perseus_cloud chart unavailable at runtime until S1 (98-2) rewires the loader — graceful degradation, not a crash.

**Handoff:** To verify phase (TEA simplify + quality-pass), then Reviewer.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 actionable (1 pre-existing `register` warning) | confirmed 0, dismissed 0, deferred 1 (pre-existing) |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 9 (1 high→downgraded, 2 med, 6 low) | confirmed 6 (LOW), dismissed 0, deferred 3 (already-covered/clarity) |
| 5 | reviewer-comment-analyzer | Yes | findings | 2 (both high-confidence, LOW severity) | confirmed 2 (LOW), dismissed 0 |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 5 (16 rules / 47 instances checked) | confirmed 5 (LOW, rule-matching — not dismissed), dismissed 0 |

**All received:** Yes (4 enabled returned, 5 disabled via settings)
**Total findings:** 13 confirmed at LOW/MEDIUM severity, 0 dismissed, 4 deferred (3 already-covered, 1 pre-existing). **Zero Critical/High.**

### Rule Compliance (Python lang-review + CLAUDE.md)

Exhaustive enumeration over the one production-language file (`test_perseus_cloud_systems_split.py`); YAML is data.

- **#1 silent exception swallowing** — COMPLIANT (4 fixtures/tests; no try/except, validators raise unswallowed).
- **#2 mutable default args** — COMPLIANT (9 functions; none have mutable defaults).
- **#3 type annotations at boundaries** — 1 VIOLATION (LOW): `yula_raw` returns bare `dict` (L119) — should be `dict[str, object]`. All other helpers/fixtures annotated.
- **#5 path handling** — 3 VIOLATIONS (LOW, rule-matching, confirmed not dismissed): `path.open()` L126, `read_text()` L239/L278 omit `encoding="utf-8"`. Practical risk low (content is ASCII; dev+CI default UTF-8) but it is a stated rule → confirmed, logged for cleanup. `Path.resolve()` used correctly at L90.
- **#6 test quality** — 1 VIOLATION (LOW): vacuous `assert isinstance(yula_orbits, OrbitsConfig)` L158 (fixture is typed+model-validated; cannot fail). 16 other tests use exact equality / not-in / set equality — meaningful. The `pytest.skip` L114 has a descriptive reason (env guard, not a hidden skip).
- **#7 resource leaks** — COMPLIANT (`with path.open()`).
- **#8 unsafe deserialization** — COMPLIANT (`yaml.safe_load`/`yaml.safe_dump` throughout; no pickle/eval/exec).
- **#10 import hygiene** — COMPLIANT (no star imports; `_resolve_scope_center` private-symbol import is the accepted white-box pattern, justified in the docstring).
- **#11 security** — COMPLIANT (test-only; all input from a known content dir, no user input).
- **CLAUDE.md No Source-Text Wiring Tests** — COMPLIANT: the rglob grep targets **content YAML** (the deliverable), not production `.py` source — the legitimate content-data exception. No production source is read.
- **CLAUDE.md Every Test Suite Needs a Wiring Test** — COMPLIANT: `test_yula_consumable_by_production_loader` (real `load_orbital_content`) + `test_renderer_root_resolver_picks_yula` (real `_resolve_scope_center`).
- **CLAUDE.md / ADR-014 No Stubbing** — COMPLIANT: only `yula.yaml` authored, enforced by `test_only_yula_system_is_authored`.

### Observations

- [VERIFIED] **The yula subtree is complete — no body was orphaned by the split.** Evidence: `git show develop:…/orbits.yaml | grep "parent: yula\b|parent: yula_2\b"` returns exactly yula_2 + lisbon/mclaughlin_13/thule_7, and there are zero `parent: lisbon|mclaughlin_13|thule_7` (no grandchildren). The 5 bodies in `yula.yaml` are the entire subtree. Complies with AC1.
- [VERIFIED] **Values are verbatim.** All five bodies' `semi_major_au`/`period_days`/`epoch_phase_deg`/`label` match the deleted source line-for-line (e.g. yula 8.343/8801.8/209.7). `test_yula_orbital_mechanics_exact` pins them; preflight confirms `OrbitsConfig.model_validate` parses to the exact 5 keys. AC1/AC3.
- [VERIFIED] **Deletion is fail-soft at runtime — no crash.** Evidence: `session.py:198` returns `False` on `orbital_content is None` *before* the init no-match raise at `session.py:210`; `session_room.py:257-265` catches `OrbitalContentMissingError`. perseus_cloud connects to the documented no-orbital-tier no-op until S1 rewires the loader. AC4-preferred path is safe to merge.
- [VERIFIED] **Identity join survives.** `cartography.yaml starting_region: yula` → body `yula` (the new root) exists, so bind-on-connect resolves once content is reloadable. No dangling reference: nothing else in the world dir references the deleted root/bodies as orrery ids.
- [TEST][LOW] `test_yula_is_the_sole_parentless_root` uses `roots == ["yula"]` list-equality (encodes dict order); harmless with a single root but `set(roots) == {"yula"}` would be clearer (test-analyzer).
- [TEST][LOW] No suite-local negative test that `_validate_parent_refs` rejects a dangling `parent: perseus_cloud` — but it IS covered in sibling tests (`test_models.py:79`, `test_loader.py:59` both `pytest.raises(... "unknown parent")`), so AC2 is guarded three ways. Deferred, not a gap.
- [DOC][LOW] Test module docstring cites line numbers of the now-deleted `orbits.yaml` (L19) and retains pre-merge "fail RED until… (Dev's GREEN task)" framing (L16) — stale once merged (comment-analyzer).
- [RULE][LOW] Missing `encoding="utf-8"` ×3 + vacuous `isinstance` + bare `dict` annotation (rule-checker; see Rule Compliance).

### Devil's Advocate

Argue this is broken. **First attack: silent data loss.** Deleting a 1015-line monolith to author a 52-line file looks like throwing away 134 bodies — 33 whole systems erased. If those values were the only copy, this is destructive. *Rebuttal:* `perseus_cloud.sector.json` (195KB) is the generator source and is still present; the monolith's own header says the geometry is *synthesized* from it, and git history holds every value. Diamonds-and-Coal (ADR-014) makes "unauthored" a valid state; AC5 mandates exactly this. Not data loss — deferred authoring. **Second attack: a live world breaks.** `world.yaml draft: false` — perseus_cloud is shippable, and its orrery (#748) was verified rendering. Delete its `orbits.yaml` and the chart dies. *Rebuttal:* it dies *gracefully* — `session.py:198` and `session_room.py:261` both handle the missing/None case without raising; the world still connects and plays, only the chart is absent until S1 (98-2) lands the per-system loader. That is the epic's intended C1→S1 sequence, logged as a Delivery Finding. A reviewer could argue C1 shouldn't merge alone — but the spec (AC4) directs deletion and ADR-141 owns the sequencing; degradation is fail-soft, not a crash. **Third attack: the tests lie.** A content test that only ever parses a known-good file proves nothing about rejection. *Rebuttal:* `OrbitsConfig`'s `extra="forbid"` + `_validate_parent_refs` are exercised by the real model, and rejection behavior is proven in `test_models.py`/`test_loader.py`; the wiring tests run the *production* loader and renderer-root resolver, not a mock. **Fourth attack: a confused author.** Someone copies this test for the next system and inherits the dead line-number citation, the brittle substring grep, and the exact-`["yula.yaml"]` assertion that will fail the moment they add `akkad.yaml`. *Rebuttal — conceded:* this is the real residue. It's all LOW and logged as non-blocking Improvements recommending a touch-up *before* the template propagates. None of it makes the current deliverable wrong. Conclusion: the story is correct and safe to ship; the findings are polish on a file that will become a template.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** `cartography.starting_region: yula` → `connect.py:316 bind_region_scope("yula", trigger="init")` → `session.py:202` matches body `yula` in `systems/yula.yaml` (once S1's loader resolves it) → chart centers on yula. Today, with the loader still reading `orbits.yaml` (deleted), `session_room.py:261` catches the miss → `orbital_content=None` → `session.py:198` returns `False` (no-op, no crash). Safe in both the interim and post-S1 states.

**Pattern observed:** Content-through-real-consumer testing — `tests/orbital/test_perseus_cloud_systems_split.py` validates the authored YAML against the production `OrbitsConfig`, `load_orbital_content`, and `_resolve_scope_center`, mirroring `test_render_coyote_star.py`. Correct pattern for a content deliverable with no in-repo harness.

**Error handling:** Fail-soft and fail-loud both verified — missing content degrades to a no-op (`session.py:198`, `session_room.py:261`); malformed content would fail loud via `OrbitsConfig` `extra="forbid"` + `_validate_parent_refs` (proven in `test_models.py:79`).

**Findings:** 13 confirmed at LOW/MEDIUM, zero Critical/High. Rule-matching findings confirmed (not dismissed) and logged as non-blocking Delivery Findings recommending a touch-up before this file is cloned for the next ~33 systems. The deliverable (`yula.yaml`) is correct against all five ACs. Confirmed findings, tagged by source:

- [RULE] Missing `encoding="utf-8"` on three file reads (L126/L239/L278) — Python lang-review #5 — at `test_perseus_cloud_systems_split.py`. LOW (content ASCII; dev+CI default UTF-8).
- [RULE] Vacuous `assert isinstance(yula_orbits, OrbitsConfig)` at `test_perseus_cloud_systems_split.py:158` — lang-review #6. LOW (neighbouring `.version` assert is the real check).
- [RULE] Bare `dict` return annotation on `yula_raw` at `test_perseus_cloud_systems_split.py:119` — lang-review #3. LOW.
- [DOC] Module docstring cites line numbers of the now-deleted `orbits.yaml` at `test_perseus_cloud_systems_split.py:19` — stale provenance. LOW.
- [DOC] Pre-merge "fail RED until… (Dev's GREEN task)" framing at `test_perseus_cloud_systems_split.py:16` outlives the story. LOW.
- [TEST] `roots == ["yula"]` list-equality at `test_perseus_cloud_systems_split.py:171` encodes dict order; `set(roots) == {"yula"}` clearer. LOW.
- [TEST] No suite-local negative test for `_validate_parent_refs` rejection (claimed in fixture docstring) — but covered in sibling `test_models.py:79` / `test_loader.py:59`; AC2 guarded three ways. LOW, deferred.
- [TEST] Brittle substring grep + silent `or {}` fallback (L278) + story-scoped exact-`["yula.yaml"]` assertion (L358) in `test_perseus_cloud_systems_split.py` — will need attention as more systems are authored. LOW/MEDIUM.

**Two-repo note for SM:** both `feat/98-1-…` branches (content `7b9d5c5`, server `48d2711e`) must be PR'd and merged together.

**Handoff:** To SM for finish-story.

## Story Context

**Epic:** ADR-141 Two-Scale Spatial Model  
**Repo:** sidequest-content  
**Files:**
- Create: `genre_packs/space_opera/worlds/perseus_cloud/systems/yula.yaml`
- Delete: `genre_packs/space_opera/worlds/perseus_cloud/orbits.yaml` (or stub it per S1 decision)

**Dependencies:**
- S1 story (98-2) decides orbits.yaml disposal strategy (delete vs. stub) and verifies loader tolerates per-system file resolution
- C1 blocks S1 (content must be authored before loader can be tested)
- S1 blocks U1 (orrery must be loadable per-system before UI wiring)

## Branch

**Strategy:** gitflow (standard)  
**Branch:** `feat/98-1-split-perseus-cloud-systems-author-yula`
**Target:** `develop` (content repos use develop for feature branches)

---

**Session created:** 2026-06-09  
**Author:** sm-setup