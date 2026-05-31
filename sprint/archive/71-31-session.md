---
story_id: "71-31"
jira_key: ""
epic: "71"
workflow: "tdd"
---
# Story 71-31: space_opera doctrine — move named/backstoried cultures from genre to world layer

## Story Details
- **ID:** 71-31
- **Jira Key:** (none — SideQuest is personal, no Jira)
- **Workflow:** tdd
- **Type:** refactor
- **Points:** 3
- **Priority:** p3
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-31T07:52:58Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-31T06:08:54Z | 2026-05-31T06:11:50Z | 2m 56s |
| red | 2026-05-31T06:11:50Z | 2026-05-31T07:24:14Z | 1h 12m |
| green | 2026-05-31T07:24:14Z | 2026-05-31T07:39:44Z | 15m 30s |
| spec-check | 2026-05-31T07:39:44Z | 2026-05-31T07:41:24Z | 1m 40s |
| verify | 2026-05-31T07:41:24Z | 2026-05-31T07:44:53Z | 3m 29s |
| review | 2026-05-31T07:44:53Z | 2026-05-31T07:51:38Z | 6m 45s |
| spec-reconcile | 2026-05-31T07:51:38Z | 2026-05-31T07:52:58Z | 1m 20s |
| finish | 2026-05-31T07:52:58Z | - | - |

## Story Context

**Title:** space_opera doctrine — move named/backstoried cultures from genre to world layer, genre ships generic culture slots (Crunch in Genre, Flavor in World)

**Description:** Refactoring story to align space_opera world packs with the genre/world layer separation doctrine established in ADR-003. Named, backstoried cultures belong in world-level overrides (worlds/<world>/cultures/); genre packs ship generic culture slots for the narrator to reference. This separation enables:
- Clean separation of mechanical crunch (genre level) from narrative flavor (world level)
- World-specific culture variation without genre pack duplication
- Easier content reuse and authoring

**Stack:** Single repo (sidequest-content), no parent dependency.

## Sm Assessment

**Setup verified against the real content tree (2026-05-31), not the bare YAML title.** The story shipped with title only — no description/AC — so the story context was reconstructed and then **corrected by SM against actual files** (the setup subagent had invented culture names and missed a world). Key facts for RED:

- **Genre `cultures.yaml`** holds 5 named/flavored cultures: `Hegemonic`, `Frontier`, `Voidborn`, `Synthetic`, `Xeno`. Each bundles prose flavor (`summary`/`description`) WITH mechanical corpus naming `slots` + `person_patterns` (the latter is crunch per ADR-091).
- **All THREE worlds already have world-level cultures** (`aureate_span`, `perseus_cloud`, `coyote_star`) — coyote_star already carries `hegemonic.yaml`/`voidborn.yaml`, a partial migration. AC must complete the pattern across all three, not just two.
- **OPEN DESIGN QUESTION (must resolve before RED writes tests):** "genre ships generic culture slots" is ambiguous — (a) keep naming-slot machinery at genre, move only prose flavor; or (b) move whole named cultures to worlds, leave genre with anonymous slots. Different file shapes. See `sprint/context/71-31-context.md` ⚠️ section. TEA/Architect pins this.
- **Scope guard:** story `repos:` is `sidequest-content` only. If the genre→world culture **loader/merge** code needs a change to satisfy AC3/AC4, that is a server-repo scope escalation to flag — not a silent cross-repo edit.

No Jira (project is personal). Branch `feat/71-31-space-opera-culture-flavor-to-world` created off content/develop. Routing to TEA for RED.

## Architect Assessment (RED-phase design resolution)

**Doctrine decision (Keith, 2026-05-31): epic-74-strict — "strip genre to mechanics-only."** Genre cultures must shed prose flavor; all named/backstoried cultures live at world tier.

**Architectural verdict: 71-31 is BLOCKED BY 74-1. Do not write content-only RED tests now.**

Findings from tracing the live code:

1. **World-over-genre resolution already exists and is REPLACE, not merge.** `Pack.effective_cultures(world)` (`sidequest-server/sidequest/genre/models/pack.py:248`) returns the world's cultures if it declares any, else the genre's. The loader (`genre/loader.py:865`) reads a world `cultures/` dir, loads files with a `name:` key as namegen `Culture`s, and skips `visual_tokens`-only files (daemon art overlays). There is **no slot-merge / prose-overlay layering** — so "keep genre slots, overlay world prose" is architecturally impossible without new server code.

2. **Real per-world state (verified 2026-05-31):**
   - `aureate_span` — 5 namegen world cultures → resolves to **world** ✅
   - `perseus_cloud` — 3 namegen world cultures → resolves to **world** ✅
   - `coyote_star` — **0** namegen world cultures (all 5 files are `visual_tokens`-only art overlays: broken_drift, free_miners, hegemonic, tsveri, voidborn) → **falls back to GENRE namegen** ⚠️. Its art-overlay keys (broken_drift/free_miners/tsveri) don't match the genre namegen names it borrows (Frontier/Synthetic/Xeno) — a latent art/namegen key mismatch.

3. **The `Culture` model blocks a content-only strip.** `genre/models/culture.py:32` is `extra: "forbid"` with `name: str`, `summary: str`, `description: str` all **required**. "Nameless slots" is impossible (`name` is the identity key for `effective_cultures` and visual_tokens). Removing `summary`/`description` requires relaxing the model to optional — a **sidequest-server change**, out of this story's content-only scope. The only content-only alternative is setting them to `""` (empty-string hack), which violates clean-content / No-Stubbing and is exactly what 74-1 is designed to eliminate.

4. **74-1 is the prerequisite.** Title: "Loader refactor — genre-tier flavor becomes world-tier/optional (no genre flavor)", repos `sidequest-server,sidequest-content`. Epic 74 description: the loader "hard-requires lore/cultures/archetypes/theme/visual_style/audio today" and "the SERVER loader/consumer refactor must land before the remaining MANDATORY genre-tier flavor files can be deleted." That IS the model/loader relaxation 71-31 needs.

**Recommendation:** Set `71-31 depends_on: 74-1` and bounce to SM (Hawkeye) to re-sequence — start 74-1 first. After 74-1 lands, 71-31 becomes the space_opera-specific content migration: (a) strip genre culture prose, (b) author `coyote_star` world namegen cultures (broken_drift/free_miners/tsveri + decide hegemonic/voidborn) so it stops borrowing genre namegen and its art overlays get matching keys. Spec ref: `docs/genre-pack-content-audit.md`.

## SM Re-Sequencing (2026-05-31, post-Architect)

**The Architect's "BLOCKED BY 74-1" verdict was stale on arrival.** 74-1 (`Loader refactor — genre-tier flavor world-tier/optional`, PR #546) was **already DONE** — orchestrator commit `3c7bf00` landed it *before* `bed85fa` recorded the Architect's "start 74-1 first" recommendation. The dependency is satisfied, not pending.

**What 74-1 actually delivered (verified against `origin/develop`):** genre-tier `cultures`/`lore`/`theme`/`audio` loads are now **optional** (`_load_yaml_optional`); `GenrePack` fields Optional. A pack may now **omit genre cultures entirely**. 74-1 did **not** relax the `Culture` model — `name`/`summary`/`description` remain required. So the Architect's claim #3 (model blocks nameless "generic slots") still holds, but is now moot.

**Scope decision (Keith, 2026-05-31): epic-74-strict — DELETE, don't genericize.** The story title's "genre ships generic culture *slots*" is superseded by epic-74-strict doctrine. We do **not** author nameless slots (which would need the model relaxation the Architect flagged). We **delete** genre-tier cultures (now legal per 74-1) and make worlds authoritative. **71-31 is therefore content-only and UNBLOCKED — no sidequest-server change required.**

**Concrete RED scope for TEA (sidequest-content):**
1. **Delete** the space_opera genre-tier `cultures.yaml` (Hegemonic/Frontier/Voidborn/Synthetic/Xeno). Genre = mechanics only.
2. **Verify** `aureate_span` (5 world cultures) and `perseus_cloud` (3) still resolve their own namegen cultures via `effective_cultures` — i.e. namegen does not regress to a genre fallback that no longer exists.
3. **Author** `coyote_star` world namegen cultures (it has 0 — only `visual_tokens` art overlays). Give `broken_drift`/`free_miners`/`tsveri` real namegen `Culture` files (+ decide `hegemonic`/`voidborn`), so coyote_star stops borrowing genre namegen AND its art-overlay keys gain matching namegen keys (fixes the latent key mismatch).
4. **Wiring guard:** at least one server-side test (`tests/genre/`) proving each space_opera world resolves world-tier cultures and none fall back to a now-absent genre `cultures.yaml`. This is a test-only touch of sidequest-server — keep production code untouched; if a non-test server change proves necessary, STOP and flag scope escalation.

**Repos:** primarily `sidequest-content`; sidequest-server is **test-only** (wiring guard). Branch `feat/71-31-space-opera-culture-flavor-to-world` (content) per SM Assessment.

**Routing:** block cleared → handing to Radar (TEA) for RED against the scope above.

## TEA Assessment

### Red Phase (test writing)

**Tests Required:** Yes
**Reason:** Behavioral content migration with a load-bearing regression risk (orphaning coyote_star namegen). Pinned via real-pack `effective_cultures` behavior, not source-text.

**Test Files:**
- `sidequest-server/tests/genre/test_71_31_space_opera_culture_doctrine.py` — loads the REAL space_opera pack; asserts genre tier stripped + every live world self-sufficient.

**Tests Written:** 9 tests (4 RED on the ACs, 5 green regression guards) covering 3 ACs + the doctrine invariant.
**Status:** RED confirmed — `4 failed, 5 passed` (run `uv run pytest tests/genre/test_71_31_space_opera_culture_doctrine.py`).

**Measured pre-fix state (real pack, 2026-05-31):** genre cultures = Hegemonic/Frontier/Voidborn/Synthetic/Xeno; perseus_cloud + aureate_span resolve `source=world`; **coyote_star resolves `source=genre`** (its 5 `cultures/` files are `visual_tokens`-only art overlays → loader skips → 0 namegen world cultures).

| Test | AC | State | Pins |
|------|----|-------|------|
| `test_ac1_genre_tier_has_no_named_cultures` | AC1/AC3 | 🔴 RED | no named culture remains at genre tier (durable doctrine guard) |
| `test_ac1_genre_cultures_list_is_empty` | AC1 | 🔴 RED | genre `cultures.yaml` deleted outright (epic-74-strict = delete, not genericize) |
| `test_ac2_coyote_star_resolves_world_cultures_not_genre_fallback` | AC2 | 🔴 RED | coyote_star `source=world`, includes world-unique broken_drift/free_miners/tsveri, carries no genre-only names |
| `test_no_space_opera_world_falls_back_to_genre_for_cultures[coyote_star]` | invariant | 🔴 RED | no live world falls back to the (deleted) genre tier |
| `test_ac3_pack_loads_cleanly_with_genre_cultures_gone` | AC1 edge | 🟢 guard | flavor strip must not break genre MECHANICS (rules load) |
| `test_ac2_perseus_cloud_resolves_world_cultures` | AC2 | 🟢 guard | working world must stay world-sourced |
| `test_ac2_aureate_span_resolves_world_cultures` | AC2 | 🟢 guard | working world must stay world-sourced |
| `...world_falls_back...[perseus_cloud]` / `[aureate_span]` | invariant | 🟢 guard | working worlds must not regress |

### Rule Coverage

| Rule (CLAUDE.md / SOUL) | Test(s) | Status |
|------|---------|--------|
| No Source-Text Wiring Tests | all 9 assert `effective_cultures` return values on a really-loaded pack — zero `read_text()`/grep of production source | satisfied |
| No Silent Fallbacks | `test_..._not_genre_fallback` + the parametrized invariant assert source≠'genre' (the silent fallback is the bug) | RED enforces |
| Every suite needs a wiring test | `effective_cultures` is the real consumer path (namegen + `pregen.seed_manual` call it, `pack.py:259-265`) — behavioral, refactor-stable | satisfied |
| Meaningful assertions | every test asserts concrete name sets / source / non-empty; no `assert True`/`is_none()`-on-always-None | self-checked, clean |

**Rules checked:** Python lang-review's type-constructor rules (validated `::new`, `non_exhaustive`, Deserialize-bypass) are Rust/type-system rules N/A to a YAML content migration; the applicable project rules above are covered.
**Self-check:** 0 vacuous tests.

**Open decision flagged for Dev (Winchester):** coyote_star's `hegemonic`/`voidborn` art overlays share a name with the deleted genre cultures. The RED tests REQUIRE only the three world-unique cultures (broken_drift/free_miners/tsveri). **Decide:** author world `hegemonic.yaml`/`voidborn.yaml` namegen cultures too (recommended — otherwise any coyote_star NPC tagged hegemonic/voidborn will fail to resolve once the genre tier is gone; verify against coyote_star NPC content) — or confirm those tags are unused. The tests pass either way; this is a correctness call, not a test gap.

**Handoff:** To Winchester (Dev) for GREEN — content changes in `sidequest-content` (delete `genre_packs/space_opera/cultures.yaml`; author coyote_star world namegen cultures). Server is test-only; do NOT touch production server code.

## Dev Assessment

**Phase:** finish
**Status:** GREEN — all 71-31 tests pass; zero production server code touched.

**Changes:**
- `sidequest-content` (commit `fbb86c7`):
  - **Deleted** `genre_packs/space_opera/cultures.yaml` (genre = mechanics only).
  - **Authored** 5 coyote_star world namegen `Culture` files, grounded in the world's own lore (`lore.yaml` history/factions): `hegemonic_namegen.yaml` (Vaskov Administration — Latin/Russian, ported genre slots), `voidborn_namegen.yaml` (Clan Moana-Teru — Polynesian/Japanese), `free_miners_namegen.yaml` (the Compact — English/Spanish frontier), `tsveri_namegen.yaml` (the Deep Root species — Georgian/Finnish alien phonemics, stone/root patterns), `broken_drift_namegen.yaml` (identity-refusing salvage runners — chosen handles, no surnames). All corpora verified present in `corpus/shared/`.
- `sidequest-server` (commit `70071b7d`, **test-only**): fixed `tests/genre/test_namegen_wiring.py` — see deviation below.

**Decision on TEA's open question (hegemonic/voidborn):** Authored **all five** coyote_star cultures including hegemonic + voidborn. Rationale: the world's `lore.yaml` makes both load-bearing — the Vaskov Administration (Hegemonic) and Clan Moana-Teru (Voidborn) are central factions; an NPC tagged either would have failed to resolve once the genre tier was deleted. Authoring them is the safe-correctness choice and fully resolves the Architect's art/namegen key mismatch (all 5 art-overlay stems now have matching namegen cultures).

**File-coexistence design:** the daemon `StyleCatalog` keys culture art overlays by **file stem** (`catalogs.py:321`) and reads only `visual_tokens`; the server `Culture` model is `extra: forbid` (no `visual_tokens` field). So art overlays and namegen cultures cannot share a file. Art overlays keep their bare-slug names (`broken_drift.yaml` — daemon stem preserved); namegen cultures take a `_namegen.yaml` suffix. The loader keys by `name:` presence (`loader.py:902`), so it loads only the namegen files and skips the art overlays — unchanged behavior.

**Verification (full, with content + DB env):**
| Suite | Result |
|-------|--------|
| `test_71_31_space_opera_culture_doctrine.py` | 9 passed (was 4 RED) |
| `test_namegen_wiring.py` | 11 passed (fixed 2 regressions) |
| full `tests/genre/` | 723 passed, 49 skipped, **0 failed** |
| culture/namegen/reference server tests (8 files) | 151 passed, 2 skipped |
| space_opera integration (reprisal + hp e2e) | 9 passed |
| daemon `test_catalogs`/`test_composer`/`test_composer_wiring` | 76 passed |

**Handoff:** To Radar (TEA) for verify/spec-check — simplify + quality pass.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (deviations are documented, already-logged scope decisions — no code fix required)
**Gate:** spec-check passed (AC coverage, implementation-complete, TEA+Dev deviation subsections all present).
**Mismatches Found:** 3 — all resolved by prior decision, plus 1 deferred follow-up.

Substance check against the three ACs (real-pack verified, not rubber-stamped):

- **AC1 — genre ships no named cultures:** genre `cultures.yaml` deleted (−217 lines) → `pack.cultures == []`. ✅
- **AC2 — named cultures live under `worlds/`, world loading binds them:** coyote_star now resolves `source='world'` with exactly 5 namegen cultures; the loader correctly skips the 5 coexisting `visual_tokens` art overlays (dir holds 10 files, loader binds 5 — AC2's overlay-skip edge satisfied). perseus_cloud/aureate_span unchanged and still world-sourced. ✅
- **AC3 — doctrine invariant (no named/backstoried cultures at genre tier):** satisfied by the deletion; pinned by `test_ac1_genre_tier_has_no_named_cultures`. ✅

Mismatches:

- **Story title "genre ships generic culture *slots*" vs implementation deletes the genre cultures** (Different behavior — Behavioral, Minor)
  - Spec: title implies nameless generic slots remain at genre tier.
  - Code: genre `cultures.yaml` deleted outright; no slots remain.
  - Recommendation: **A — Update spec.** Superseded by Keith's epic-74-strict doctrine ("genre = mechanics only, delete don't genericize"); nameless slots would require a `Culture`-model relaxation that was explicitly ruled out of this content-only story. Already logged in `## SM Re-Sequencing`.

- **Context doc marks "authoring new per-world cultures" OUT OF SCOPE vs Dev authored 5 coyote_star cultures** (Different behavior — Behavioral, Minor)
  - Spec: context-story-71-31.md Scope Boundaries → "removal-from-genre + verification, not new flavor authoring."
  - Code: 5 coyote_star world namegen cultures authored.
  - Recommendation: **A — Update spec.** The context-doc premise ("all three worlds already self-sufficient") was factually wrong — coyote_star had 0 namegen cultures (art overlays only) and would have been orphaned by the deletion. Session scope (higher authority) + the context doc's own Assumption #1 escape hatch authorize it. Already logged as TEA + Dev deviations.

- **Dev authored all 5 coyote_star cultures vs TEA's RED required only 3 unique ones** (Extra in code — Behavioral, Minor)
  - Spec: RED tests require broken_drift/free_miners/tsveri; hegemonic/voidborn left as a Dev decision.
  - Code: all 5 authored.
  - Recommendation: **A — note.** Correctness-positive and lore-grounded (Vaskov Administration + Clan Moana-Teru are central `lore.yaml` factions); fully closes the Architect's art/namegen key mismatch. Not drift — completeness.

- **Daemon art↔namegen association** (Different behavior — Behavioral, Minor) — Dev's delivery-finding/question.
  - Recommendation: **D — Defer.** The two-files-per-culture coexistence (art keyed by stem, namegen by `name`) works and is daemon-test-clean; formalizing the pairing + confirming the portrait path slugifies culture names to art stems belongs to a future daemon story. Out of this story's server-test scope.

**Decision:** Proceed to review (verify). No hand-back to Dev.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (carried from green-phase verification; no new code applied during verify)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 7 (2 server test files + 5 content namegen YAMLs; the deleted `cultures.yaml` is a removal)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | No cross-file test duplication; the 5 YAMLs share a schema but their content is intentional thematic variation (YAML has no inheritance — nothing to extract). |
| simplify-efficiency | clean | Tests fit-for-purpose (synthetic fixtures + real-pack load + OTEL capture); YAMLs appropriately scoped; no over-engineering. |
| simplify-quality | 2 findings | (1 medium, 1 low — both flagged, not applied; see below) |

**Applied:** 0 high-confidence fixes (no high-confidence findings surfaced)
**Flagged for Review:** 1 medium — two `test_ac1_*` tests (`..._has_no_named_cultures` + `..._genre_cultures_list_is_empty`) both carry the `ac1` prefix. *Dismissed as a defect:* this is intentional — they pin two distinct forms of the doctrine invariant (no-named-leak = the durable AC1/AC3 guard that survives a future generic-slot scaffold; list-empty = the strict epic-74 delete form). Docstrings disambiguate. Renaming is churn for no behavioral gain; left as-is.
**Noted:** 1 low — `assert isinstance(space_opera_pack, GenrePack)` (line ~150) flagged as a near-vacuous type check; the quality teammate itself withdrew it ("documented and explained well" — it asserts the AC1-edge that deleting flavor doesn't break the pack load). Kept.
**Reverted:** 0

**Overall:** simplify: clean (2 cosmetic quality observations dismissed/noted, 0 fixes applied)

**Quality Checks:** Full green-phase verification stands (71-31 9✅, namegen-wiring 11✅, genre suite 723✅, culture/reference 151✅, space_opera integration 9✅, daemon catalogs 76✅). No code changed in verify → no regression re-run required.
**Handoff:** To Colonel Potter (Reviewer) for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 smells; tests GREEN 723/0/49 | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings |

**All received:** Yes (1 enabled subagent returned; 8 disabled via `workflow.reviewer_subagents` and assessed by Reviewer directly)
**Total findings:** 2 confirmed (both Low, non-blocking), 0 dismissed, 0 deferred-blocking

## Reviewer Assessment

**Verdict:** APPROVED

A content + test-only migration (no production code touched). I independently traced the live paths rather than trusting the green suite — the real risks here are runtime hazards the load-time tests don't exercise.

**Observations:**
- `[VERIFIED]` AC1/AC3 — genre `cultures.yaml` deleted; `pack.cultures == []` and `effective_cultures` returns `source='world'` for all 3 worlds. Evidence: probe + `test_ac1_*`/`test_no_*_falls_back` GREEN.
- `[VERIFIED]` Pattern/slot consistency — every `{slot}` referenced in `person_patterns`/`place_patterns` is defined in `slots`, and every slot is used, across all 5 new cultures. (The `Culture` model does NOT validate this — a typo'd slot would pass load and fail only at name-generation. Checked all 5: none missing.)
- `[VERIFIED]` Live namegen + seeding + narrator-culture-reference are all world-aware via `effective_cultures` — `narration_apply.py:1481` (explicitly "NOT raw pack.cultures"), `pregen.py:224`, `culture_context.py:resolve_culture_reference` (world-first). coyote_star will use its new world cultures in production.
- `[VERIFIED]` No perseus-bug reintroduction — `pregen.py:225` passes each Culture's own `.name` to namegen (`--culture`), matched case-insensitively at `namegen.py:574`; it never passes the lowercase content tags. hegemonic/voidborn deliberately kept Title-Case → identical match to the prior genre behavior.
- `[VERIFIED]` No orphaned culture tags — coyote_star content tags are `broken_drift`/`free_miners`/`hegemonic`/`tsveri`/`voidborn` (19 occurrences); none reference the deleted genre names (Frontier/Synthetic/Xeno). Pre-authored ManualNpcs match case-insensitively via `monster_manual.get_npc`.
- `[VERIFIED]` Art overlays preserved — 5 `visual_tokens` files keep bare-slug stems (daemon `catalogs.py:321` keys), loader binds only the 5 `name:`-bearing `_namegen.yaml` files; coexistence confirmed (dir holds 10, loader resolves 5).
- `[LOW]` `[SIMPLE]` `encountergen.py:559` reads `pack.cultures` raw (not world-aware) → `encountergen --genre space_opera` now fails-loud ("genre has no cultures", exit 1). Pre-existing dev-CLI limitation the migration surfaces; fails loud (not silent), dev tool not live path, fix is server prod code (out of this story's test-only scope). → Delivery Finding.
- `[LOW]` `[DOC]` `generate_name.py:29` docstring says the production name-generator dict is built "by walking `genre_pack.cultures`" — the actual live seam (`narration_apply.py:1481`) uses `effective_cultures`. Either stale docstring or a second namegen surface to confirm world-aware. Pre-existing; not touched by 71-31. → Delivery Finding.

### Rule Compliance

| Rule (CLAUDE.md / SOUL) | Applies to | Verdict |
|------|-----------|---------|
| No Silent Fallbacks | genre-culture deletion; encountergen empty-pool | Compliant — `effective_cultures` returns `source` explicitly; encountergen exits loud on empty; no silent genre→world masking |
| No Source-Text Wiring Tests | new test file | Compliant — all assertions are behavioral (`effective_cultures` returns), zero `read_text()`/grep of prod source |
| No Stubbing | 5 new culture YAMLs | Compliant — full `Culture` shapes (name/summary/description/slots/patterns), lore-grounded, no empty-string placeholders |
| Crunch in Genre, Flavor in World (ADR-003) | the whole change | Compliant — this IS the doctrine: genre = mechanics only, cultural identity at world tier |
| Every suite needs a wiring test | test file | Compliant — `effective_cultures` is the real consumer path (namegen + pregen) |

### Devil's Advocate

*Arguing this is broken:* The most dangerous angle is the lowercase-slug vs Title-Case-name gap. coyote_star content tags cultures as `broken_drift` (underscore); the new Culture names are "Broken Drift" (space). `namegen.py:574` matches only case-insensitively — `"broken drift" != "broken_drift"` — so any code path that hands a *content tag* to namegen as `--culture` would 0-match and silently fall to narrator invention (the perseus failure mode). I chased every seeding/namegen entry point: pregen passes `c.name` (not tags); the narrator tool resolves from the effective set (names); pre-authored ManualNpcs carry their own authored names and match via case-insensitive `get_npc`. So no *current* path passes a tag into namegen — but it's a latent landmine: a future story that seeds "by content tag" will trip it. Worth a slug-normalization helper someday (noted, not blocking — no live path hits it).

Second angle: `MAX_CULTURES=4` in pregen — coyote_star now has 5 world cultures, so auto-seed covers only the first 4 sorted (broken_drift, free_miners, hegemonic, tsveri); **voidborn is excluded from per-culture auto-seed**. But this is a pre-existing Rust-parity cap and before the change it took 4 of 5 genre cultures too — net neutral, not a regression. Voidborn NPCs still seed via pre-authored ManualNpcs.

Third angle: empty genre cultures could IndexError a `pack.cultures[0]` consumer. Checked: `culture_context` guards (`if not eligible: return ""`), `encountergen` guards (`if not cultures: exit`), live namegen uses `effective_cultures`. No unguarded index into the now-empty genre list. Confused-author risk: someone re-adding a named culture to the genre tier would be caught by `test_ac1_genre_tier_has_no_named_cultures` — the durable guard. Nothing here rises to blocking.

**Data flow traced:** narrator/seeding requests a culture for world `coyote_star` → `Pack.effective_cultures("coyote_star")` → world set [Broken Drift, Free Miners, Hegemonic, Tsveri, Voidborn] (`source='world'`) → `build_from_culture(culture, corpus_dir)` with real corpora → name generated. Safe: world-authoritative, corpora present, patterns slot-consistent.
**Pattern observed:** world-over-genre REPLACE resolution via `effective_cultures` — `pack.py:267`; honored by every live consumer.
**Error handling:** empty genre pool is guarded at every raw-read site (culture_context, encountergen); namegen fails loud on unknown culture (`namegen.py:579`).
**Handoff:** To Hawkeye (SM) for finish-story.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Architect (RED-phase design)
- **Conflict** (blocking): 71-31's chosen doctrine (epic-74-strict, strip genre culture prose) requires the `Culture` model's `summary`/`description` to become optional — a sidequest-server change owned by **74-1**, outside this story's content-only scope. Affects `sidequest-server/sidequest/genre/models/culture.py` (relax required str fields) and `genre/loader.py`/`models/pack.py` (fallback behavior). **71-31 must depend_on 74-1; do 74-1 first.** Decision by Keith 2026-05-31.
- **Gap** (non-blocking): `coyote_star` has zero namegen world cultures (5 files are `visual_tokens`-only) so it falls back to GENRE namegen, and its art-overlay keys (broken_drift/free_miners/tsveri) don't match the borrowed genre names (Frontier/Synthetic/Xeno). Affects `sidequest-content/genre_packs/space_opera/worlds/coyote_star/cultures/` (author namegen culture files). This is the concrete content deliverable for 71-31 once 74-1 unblocks it.

### TEA (test design)
- **Confirmed (measured) coyote_star genre fallback — Architect's Gap is real and load-bearing**, not theoretical: real-pack probe shows `effective_cultures("coyote_star") → source='genre'`, names = the full genre set. Affects `sidequest-content/genre_packs/space_opera/worlds/coyote_star/cultures/` (must gain namegen Culture files). *Found by TEA during test design.*
- **Question** (non-blocking): coyote_star `hegemonic`/`voidborn` art overlays collide by name with deleted genre cultures — author them as world namegen cultures or confirm unused? Affects `coyote_star/cultures/` + the coyote_star NPC content that tags cultures. *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): the daemon `StyleCatalog` now scans 10 files in `coyote_star/cultures/` — 5 art overlays (real `visual_tokens`) + 5 `*_namegen.yaml` (no `visual_tokens` → inert empty `culture_tokens` entries keyed by the `_namegen` stem). The empties are never queried (lookups use the real culture slug), and daemon catalog tests pass. A future daemon story could formalize the art↔namegen pairing (e.g. derive the art slug from the namegen culture name) so the two-files-per-culture convention is explicit rather than incidental. Affects `sidequest-daemon/.../media/catalogs.py` (overlay keying). *Found by Dev during green.*
- **Question** (non-blocking): the daemon `get_culture` raises `CatalogMissError` (no silent fallback) when a character's `.culture` value isn't a known overlay stem. With coyote_star now producing world culture names ("Broken Drift" etc.), confirm the portrait path slugifies the culture name to the art stem (`broken_drift`) before lookup — otherwise coyote_star portraits could miss. Not exercised by this story's tests (server-only scope). Affects the server→daemon culture-tag handoff. *Found by Dev during green.*

### TEA (test verification)
- No new upstream findings during test verification. Simplify pass clean (reuse/efficiency clean; 2 cosmetic quality observations dismissed/noted, 0 fixes applied). Dev's daemon art↔namegen finding above is the right call for a follow-up daemon story.

### Reviewer (code review)
- **Improvement** (non-blocking): `encountergen` dev CLI reads `pack.cultures` raw (not world-aware), so `sidequest-encountergen --genre space_opera` now fails-loud ("genre has no cultures") post-migration. Affects `sidequest-server/sidequest/cli/encountergen/encountergen.py:559` (add `--world` + `effective_cultures` like `namegen` already does). Pre-existing CLI gap the doctrine surfaces; fails loud, not silent. *Found by Reviewer during code review.*
- **Question** (non-blocking): `generate_name.py:29` docstring says the production name-generator dict is built "by walking `genre_pack.cultures`" — confirm the narrator namegen tool's production wiring resolves via `effective_cultures(world)` (the primary seam at `narration_apply.py:1481` already does) or correct the stale docstring. Affects `sidequest-server/sidequest/agents/tools/generate_name.py`. Pre-existing; not touched by 71-31. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Tested coyote_star world-culture authoring, which the story-context doc marks OUT OF SCOPE**
  - Spec source: context-story-71-31.md, "Scope Boundaries → Out of scope" (lines 98-100) + "Assumptions" (lines 139-145)
  - Spec text: "Authoring NEW per-world cultures — the three live worlds already have their `cultures/` dirs; this is a removal-from-genre + verification, not new flavor authoring."
  - Implementation: RED tests REQUIRE coyote_star to resolve world-tier namegen cultures (`source='world'`, includes broken_drift/free_miners/tsveri), i.e. they mandate authoring new world cultures for coyote_star.
  - Rationale: The context doc's premise ("all three worlds already self-sufficient") is **factually wrong** — measured: coyote_star's 5 culture files are `visual_tokens`-only art overlays, so it resolves `source='genre'` and declares 0 namegen cultures. The higher-authority session scope (SM Re-Sequencing, Keith 2026-05-31) explicitly puts coyote_star authoring in scope, and the context doc's own Assumption #1 provides the escape hatch ("porting that culture into the world is the fix, not reverting the genre removal"). Per spec-authority hierarchy (session scope > context doc), session wins.
  - Severity: minor
  - Forward impact: Dev's GREEN work includes authoring coyote_star world cultures (content), not just deleting genre cultures.

### Dev (implementation)
- **Modified a pre-existing test (`test_namegen_wiring.py`) outside the story's RED set**
  - Spec source: session SM Re-Sequencing scope ("sidequest-server is test-only; do NOT touch production server code") + story-context Scope Boundaries
  - Spec text: "Server is test-only; do NOT touch production server code."
  - Implementation: changed `_stub_namespace`'s `world=None` → `world="perseus_cloud"` in `tests/genre/test_namegen_wiring.py` (test-only; no production code).
  - Rationale: deleting the genre `cultures.yaml` makes `effective_cultures("space_opera", world=None)` empty, so `generate_npc` correctly fails loud (`sys.exit(2)`, No Silent Fallbacks). Two collision-span wiring tests called `generate_npc` with `world=None` and relied on genre-tier cultures existing — a coupling the doctrine change invalidates. Pointing the stub at a self-sufficient world (perseus_cloud) preserves the tests' actual purpose (collision spans) while aligning with the new world-authoritative behavior. Verified pre-existing-vs-regression by tracing the exact `sys.exit(2)` site (`namegen.py:551`) to the emptied culture pool — this is a direct consequence of the deletion, not an unrelated failure.
  - Severity: minor
  - Forward impact: none — the test still exercises the same wiring, now via a world tier.

### TEA (test verification)
- No deviations from spec during the verify phase. Simplify applied 0 fixes (no high-confidence findings); no code changed.

### Reviewer (audit)
- **TEA — "Tested coyote_star world-culture authoring (context doc marks OUT OF SCOPE)"** → ✓ ACCEPTED by Reviewer: the context-doc premise ("all three worlds self-sufficient") was factually wrong; coyote_star resolved `source='genre'` with 0 namegen cultures. Higher-authority session scope (Keith) put authoring in scope, and the context doc's own Assumption #1 sanctions porting. Sound.
- **Dev — "Modified pre-existing `test_namegen_wiring.py` outside the RED set"** → ✓ ACCEPTED by Reviewer: a direct, correctly-traced consequence of the genre-culture deletion (`effective_cultures(world=None)` empties → `sys.exit(2)` fail-loud). Repointing the stub to a self-sufficient world (perseus_cloud) preserves the collision-span test's purpose; test-only, no production code. Sound.
- **Dev — "Authored all 5 coyote_star cultures vs TEA's required 3" (spec-check entry)** → ✓ ACCEPTED by Reviewer: lore-grounded (Vaskov Administration + Clan Moana-Teru are central factions); hegemonic/voidborn kept Title-Case preserves prior seeding-match behavior. Correctness-positive completeness, not scope creep.
- No undocumented deviations found. Every spec divergence is logged and accepted.

### Architect (reconcile)

**Entry verification:** The TEA (test design) and Dev (implementation) deviation entries were checked against source. Spec sources resolve (context-story-71-31.md "Scope Boundaries"/"Assumptions" exist; SM Re-Sequencing scope is in this session file), quoted spec text is accurate, and implementation descriptions match the committed code (content `fbb86c7`, server `70071b7d`/`68821b25`). All 6 fields present and substantive.

- **Correction to the Dev entry's line reference** (annotation, not a new deviation): the empty-culture-pool `sys.exit(2)` fail-loud site is `namegen.py:559` (the `if not effective_cultures:` guard block), not `:551`. The cited behavior and root cause are correct; only the line number was imprecise. No code or decision changes.

**Missed deviations added to the manifest:**

- **New content convention: namegen culture files use a `_namegen.yaml` suffix to coexist with `visual_tokens` art overlays**
  - Spec source: context-story-71-31.md "Technical Guardrails" (destination shape) — quoted: *"`worlds/perseus_cloud/cultures/` — `spacer.yaml`, `thari.yaml`, `yulan.yaml` (one `Culture` per file, `name:` + `summary:` + ...)"* (the precedent worlds use the bare-slug filename for the namegen Culture).
  - Implementation: coyote_star's bare-slug filenames were already taken by `visual_tokens` art overlays, so the 5 new namegen Cultures use `<slug>_namegen.yaml` instead of `<slug>.yaml`. coyote_star is therefore the first world where namegen and art-overlay culture files coexist in one `cultures/` dir under different stems.
  - Rationale: the `Culture` model is `extra: forbid` (no `visual_tokens` field), so a single file cannot carry both; the daemon `StyleCatalog` keys art by file stem (`catalogs.py:321`), so the art file must keep the bare slug. Content-only constraint, no engine change.
  - Severity: trivial
  - Forward impact: future world authors adding namegen cultures to a world that already has art overlays should follow the `_namegen.yaml` convention. A future daemon story (see Dev/Reviewer Delivery Findings) may formalize the art↔namegen pairing.

- **Behavioral: `MAX_CULTURES=4` pregen cap excludes one of coyote_star's 5 world cultures from per-culture auto-seed**
  - Spec source: epic-74/story scope (genre→world culture migration); the cap itself is `pregen.py` MAX_CULTURES (Rust parity) — quoted intent from the story: cultures resolve against *"the SAME set the table actually authored."*
  - Implementation: coyote_star now resolves 5 world cultures; `pregen.seed_manual` takes `effective[:4]` (sorted: broken_drift, free_miners, hegemonic, tsveri), so **voidborn is excluded from per-culture auto-seed**. Voidborn NPCs still seed via pre-authored ManualNpcs and resolve in live namegen/narrator paths.
  - Rationale: pre-existing engine cap, not introduced by this story; before the change pregen also took 4 of 5 genre cultures. Net-neutral, surfaced (not caused) by the migration.
  - Severity: minor
  - Forward impact: none for this story; if a table wants all 5 coyote_star cultures auto-seeded, raising/removing MAX_CULTURES is a separate engine story.

**AC deferral check:** No ACs were deferred (all DONE — AC1/AC2/AC3 satisfied per spec-check). No-op.