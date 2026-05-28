---
story_id: "64-5"
jira_key: null
epic: "64"
workflow: "tdd"
repos: "server,content"
---
# Story 64-5: Cross-reference content lint — ID membership + adjacency closure

## Story Details
- **ID:** 64-5
- **Jira Key:** (none — personal project)
- **Epic:** 64 — Content Schema Compliance
- **Workflow:** tdd
- **Repos:** server,content
  - _SM deviation 2026-05-28: story YAML says `server`; expanded to `server,content` mid-GREEN. AC5 (10 live packs pass) cannot be satisfied server-only — spaghetti_western + heavy_metal ship 5 genuine dangling trope refs the new lint correctly catches. Fixing those refs is in-scope for epic 64 (repos: content,server). SM creates+merges a PR per repo at finish._
- **Stack Parent:** none

## Acceptance Criteria
- Unresolvable trope ID in history/adjacency → ERROR with the id + file
- archetype typical_classes/typical_races not in rules.yaml allowed sets → ERROR
- archetype_constraints non-canonical jungian/role id, missing/extra genre_flavor entry → ERROR
- theme adjacency closure surfaced as a validator ERROR
- All 10 live packs still PASS

## Story Description

Builds on 64-4. Once file contents parse, add a content-lint layer that validates CROSS-references the per-file pydantic models can't see on their own:

1. **Trope IDs** referenced in history.yaml chapters / adjacency exist in the resolved trope set
2. **Archetype typical_classes/typical_races** resolve against the pack's rules.yaml allowed_classes/allowed_races
3. **archetype_constraints valid_pairings** jungian/role IDs are from the canonical 12 jungian x 7 roles, and genre_flavor covers all of them with no extras (these were hand-audited in epic 64 review)
4. **Theme palette adjacency closure** (prefers/avoids refs exist) — already enforced in load_theme_palette, surface it here too

Report each as an ERROR with the offending id + file.

## Workflow Tracking
**Workflow:** tdd
**Phase:** red

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-28 | 2026-05-28 | - |
| red | 2026-05-28 | - | - |

## TEA Assessment

**Tests Required:** Yes
**Reason:** New cross-reference validation behavior across four AC areas; per-file pydantic models (64-4) cannot enforce cross-file references.

**Test Files:**
- `tests/cli/validate/test_pack_validator_crossref.py` — 16 tests covering AC1–AC5 (8 RED failing + 8 controls/pins passing).

**Tests Written:** 16 tests covering 5 ACs
**Status:** RED (8 failing — ready for Dev; 8 controls/pins green today)

**RED breakdown (fail today, must pass after Dev implements):**

| AC | Test | Why it fails today |
|----|------|--------------------|
| AC1 | `test_history_chapter_trope_id_not_in_set_is_error` | no cross-ref pass yet → `got: []` |
| AC1 | `test_legend_related_trope_not_in_set_is_error` | no cross-ref pass yet → `got: []` |
| AC2 | `test_typical_class_not_allowed_is_error` | no rules.yaml membership check → `got: []` |
| AC2 | `test_typical_race_not_allowed_is_error` | no rules.yaml membership check → `got: []` |
| AC3 | `test_non_canonical_jungian_in_pairing_is_error` | no canonical-set check → `got: []` |
| AC3 | `test_non_canonical_role_in_pairing_is_error` | no canonical-set check → `got: []` |
| AC3 | `test_missing_genre_flavor_jungian_entry_is_error` | no coverage check → `got: []` |
| AC3 | `test_extra_genre_flavor_jungian_entry_is_error` | no coverage check → `got: []` |

**Controls / pins (green today AND must stay green):**
- AC1 controls: `test_baseline_empty_history_passes`, `test_history_chapter_trope_id_in_set_passes`, `test_resolved_set_unions_genre_and_world_tropes`
- AC2 control: `test_typical_class_and_race_allowed_passes`
- AC3 control: `test_fully_canonical_constraints_pass`
- **AC4 (pin — already enforced):** `test_dangling_adjacency_ref_surfaces_as_error`, `test_closed_adjacency_passes`
- **AC5 (wiring + regression):** `test_all_live_packs_pass_cross_reference_lint`

### Implementation notes for Dev (Inigo)

- The cross-ref layer extends `sidequest/cli/validate/pack.py::validate_pack_structure` (the 64-4 content-validation seam). All four checks must report an ERROR string carrying **the offending id AND the filename**.
- **AC1 resolved trope set** = union of genre `tropes.yaml` ids ∪ world `tropes.yaml` ids (TropeDefinition `id`). Trope refs to check: history `chapters[].tropes[].id` (beneath_sunden-style top-level `chapters:`) **and** legend `related_tropes` (legends live as per-file `*.yaml` under the world `legends/` dir).
- **AC2** reads `rules.yaml` `allowed_classes`/`allowed_races` (RulesConfig, pack tier) and checks each NpcArchetype's `typical_classes`/`typical_races` against them.
- **AC3** canonical sets come from the repo-global `sidequest-content/archetypes_base.yaml`, parsed via the `BaseArchetypes` leaf model (`sidequest.genre.models.archetype_axes` — leaf, no loader import). Discover it by walking up from the pack dir the way `_find_default_schema` finds `pack_schema.yaml`. Tests place a copy at the content root so both walk-up and schema-sibling discovery resolve. Check: every jungian/role id in `valid_pairings` (common/uncommon/rare/forbidden, each `[jungian, role]`) is canonical; `genre_flavor.jungian`/`genre_flavor.rpg_roles` cover **exactly** the canonical jungian(12)/rpg_role(7) sets (missing **or** extra → ERROR). `npc_roles_available` is a SEPARATE field checked against the separate `npc_roles`(9) set — do NOT conflate it with genre_flavor coverage.
- **AC4** is already enforced by `_validate_theme_palette` → `load_theme_palette` ("affinity id not in palette → ValueError"); no new impl expected — the pin tests confirm it surfaces.

**Handoff:** To Dev (Inigo) for implementation (GREEN).

## Delivery Findings

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Improvement** (non-blocking): the testing-runner subagent clobbered this session file (`sprint/.session/64-5-session.md`) during the RED verify run — a known gotcha. Reconstructed by TEA from the SM-authored original + this assessment. Affects orchestration hygiene, not the story. *Found by TEA during test design.*
- **Question** (non-blocking): live-tree pre-existing failures unrelated to 64-5 are in the baseline — 4× `tests/scripts/test_audit_namegen_corpora.py` (missing corpus files, e.g. `space_opera/corpus/latin.txt`) and 1× `tests/agents/test_prompt_cache_attribution_otel.py::test_zones_carry_cache_boundary_flag`. Any failure NOT in this set at GREEN is a regression. *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (RESOLVED in place): 6 genuine AC2 class/race violations across 3 packs — RESOLVED via Keith-approved archetype remaps (content commit cc5c64c). NOT deferred; story 64-11 is unneeded/cancelled. Both live-pack wiring tests stay STRICT (zero errors) and now PASS. The verified violation list (id, pack, tier, field, value, confirmed-genuine) = the record of what was fixed, with the remap applied:
  - `space_opera` | genre | typical_races | `Frontier` | Y → remapped to `Colonial` — archetypes 'Station Bartender', 'Free Trader', 'Grease Monkey'. (`Frontier` was defined as a CULTURE, miscategorized as a race.) allowed_races=[Coreworlder, Colonial, Spacer, Uplifted, Xeno, Synthetic].
  - `heavy_metal` | world evropi | typical_races | `Half-Orc` | Y → remapped to `Human` (Human already listed → dropped the Half-Orc line to avoid a `[Human, Human]` duplicate) — archetypes 'Daggereye Contractor', 'Refuser of the Long Mine'. allowed_races=[Human, Dwarf, Elf, Halfling].
  - `neon_dystopia` | world franchise_nations | typical_classes | `Detective` | Y → remapped to `Solo` — archetype 'The Federal Agent'. allowed_classes=[Netrunner, Solo, Fixer, Tech, Nomad, Face, Ghost].
  - Masking ruled out before remapping: no `_from:` on any allowed_classes/allowed_races (only `_from:` in the tree is space_opera's dogfight interaction table); no genre+world allowed-set merge (loader.py:1040 loads rules once per pack; none of those worlds ship a rules.yaml → all three resolve against the GENRE allowed sets). No allowed-set expansion — archetypes remapped to existing allowed values. *Found + resolved by Dev during implementation.*
- **Note** (non-blocking): both live-pack wiring tests (`test_pack_validator_crossref.py::test_all_live_packs_pass_cross_reference_lint` + the 64-4 sibling `test_pack_validator.py::TestContentValidation::test_all_live_packs_pass_content_validation`) kept STRICT (assert zero errors) and now PASS — no AC5 rescope needed. Full lint coverage (AC1 trope-ref + AC2 class/race + AC3 constraint axes + AC4 theme adjacency) is green across all 10 live packs. *Found by Dev during implementation.*

### Reviewer (code review)
- **Gap** (blocking): `_validate_history_trope_refs` (pack.py:393-398) and `_validate_legend_trope_refs` (pack.py:438-440) discard the `read_err` from `_read_yaml` on a YAML parse failure and return `[]`/`continue`. The history comment claims "A YAML parse failure is already surfaced by the parse layer" — but **no pydantic model validates history.yaml or legends/*.yaml** (verified: `_validate_single_model`/`_validate_list_of_model` are wired only to archetypes/tropes/archetype_constraints). A syntactically broken history.yaml or legend file therefore passes the validator with ZERO errors — a silent fallback that violates the `<critical>` No Silent Fallbacks rule, in the very epic meant to close validator gaps. Fix: surface the `read_err` as a loud ERROR in both functions; correct the false comment; add a RED test (broken history.yaml → ERROR). `sidequest/cli/validate/pack.py`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): space_opera/archetypes.yaml remap left a duplicate — the 2nd archetype hunk's `typical_races: [Frontier, Colonial]` became `[Colonial, Colonial]`. Dev explicitly dedup'd the analogous heavy_metal case but missed this one. Passes the lint (dup-of-allowed is allowed) but should be dedup'd to `[Colonial]`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): inline-definition path in `_validate_history_trope_refs` adds a name-carrying entry's `id` to `inline_ids` WITHOUT validating it against the resolved set. Sound + necessary for elemental_harmony (empty tropes.yaml; history seeds inline-defined tropes — verified resolved-set size 0), so the alternative would false-fail AC5. Residual: a typo'd id on a name-carrying entry is unprotected. Documented limitation. *Found by Reviewer during code review.*
- **Question** (non-blocking): heavy_metal/evropi legend fixes DELETE dangling refs (`the_mountain_remembers`, `the_stratum_stirs`) rather than correcting them. Legit if truly phantom; if those tropes were intended to exist, the right fix is to define them. Keith to confirm intent. *Found by Reviewer during code review.*

## Design Deviations

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **AC1 "history/adjacency" scoped to history chapters + legends related_tropes**
  - Spec source: context-story-64-5.md, AC-1 ("trope IDs referenced in history.yaml chapters / adjacency")
  - Spec text: "trope IDs referenced in history.yaml chapters / adjacency exist in the resolved trope set"
  - Implementation: tests check trope refs in history `chapters[].tropes[].id` AND legend `related_tropes` (per team-lead RED clarification); the separate "adjacency closure" sense of the title is covered by AC4 (theme palette).
  - Rationale: history.yaml carries no `adjacency` field; the only trope-adjacency-style refs in live content are legends' `related_tropes`. If a distinct trope-adjacency field is intended, Dev should flag it and TEA will add coverage.
  - Severity: minor
  - Forward impact: none (controls + live-pack wiring test guard the union semantics)
- **AC3 canonical sets derived by parsing archetypes_base.yaml, not pinned as literals**
  - Spec source: context-story-64-5.md, AC-3 ("canonical 12 jungian x 7 roles")
  - Spec text: "jungian/role IDs are from the canonical 12 jungian x 7 roles, and genre_flavor covers all of them with no extras"
  - Implementation: tests parse `archetypes_base.yaml` via `BaseArchetypes` and assert behaviour (known-bad ids ERROR, full canonical coverage PASS) rather than hard-coding the 12+7 literal ids.
  - Rationale: team-lead directive — assert behaviour, not literals, so the test survives any future canonical-set change and isn't coupled to an impl that hardcodes ids.
  - Severity: minor
  - Forward impact: none
- **AC5 live-pack wiring test iterates shipped content**
  - Spec source: CLAUDE.md "Every Test Suite Needs a Wiring Test" + AC-5
  - Spec text: "All 10 live packs still PASS"
  - Implementation: `test_all_live_packs_pass_cross_reference_lint` runs the real validator over every shipped pack (the documented exception to the "tests must not point at live content" rule — it IS the end-to-end wiring/regression guard, mirroring 64-4's `test_all_live_packs_pass_content_validation`).
  - Rationale: only a real-content run proves the new cross-ref pass doesn't falsely reject hand-audited shipped content.
  - Severity: minor
  - Forward impact: none

### Dev (implementation)
- **Trope-ref typo fix `railroad_coming` → `railroad_comes` (NOT `the_railroad_comes`)**
  - Spec source: team-lead GREEN dispatch — suggested target `the_railroad_comes`
  - Spec text: "railroad_coming→the_railroad_comes"
  - Implementation: corrected dust_and_lead/history.yaml `railroad_coming` to `railroad_comes`.
  - Rationale: measured the actual defined `id:` field in dust_and_lead/tropes.yaml — it is `railroad_comes`. `the_railroad_comes` was only the slugified-name form, not a real trope id, so it would not have resolved. Used the real id.
  - Severity: minor
  - Forward impact: none — ref now resolves against the defined id.
- **Story scope expanded server → server,content (also logged by SM above)**
  - Spec source: story 64-5 YAML `repos: server`
  - Spec text: "Repos: server"
  - Implementation: fixed 6 dangling trope refs in sidequest-content (4 typo corrections + 2 phantom-ref removals) on branch feat/64-5-cross-reference-content-lint.
  - Rationale: AC5 (all 10 packs PASS) is unsatisfiable server-only — the lint correctly surfaces genuine content danglers. Epic 64 repos are content,server. AC2 class/race danglers split to 64-11 per Keith's ruling.
  - Severity: minor
  - Forward impact: SM creates+merges a PR per repo (server + content) at finish; finish will not auto-discover the 2nd repo from story YAML.

## Dev Assessment

**Implementation Complete:** Yes — full 64-5 scope (lint + all content fixes; no split, no 64-11)
**Files Changed:**
- `sidequest-server/sidequest/cli/validate/pack.py` (commits 3eab91a8 + 8a218235) — cross-reference content-lint layer (AC1 trope-id membership, AC2 class/race membership, AC3 archetype_constraints canonical axes), wired into `validate_pack_structure` (genre tier) + `_validate_world` (world tier). AC4 already enforced by `_validate_theme_palette`. Reviewer-fix round (8a218235): malformed history.yaml / legend YAML now surfaces a loud ERROR naming the file instead of being silently swallowed (No Silent Fallbacks); false "parse layer already surfaces" comment corrected.
- `sidequest-content` (commits 3754db4 + cc5c64c + d2dfcfe) — (a) 6 dangling trope-ref fixes: dust_and_lead `railroad_coming`→`railroad_comes`; the_real_mccoy `the_*`-prefix removals (watchmakers_apprentice, bessemers_shadow, presidential_request); heavy_metal evropi phantom legend refs removed (the_stratum_stirs, the_mountain_remembers). (b) 3 Keith-approved AC2 remaps: space_opera Frontier→Colonial, heavy_metal/evropi Half-Orc→Human, neon_dystopia/franchise_nations Detective→Solo. (c) dedup (d2dfcfe): space_opera 'Free Trader' typical_races `[Colonial, Colonial]`→`[Colonial]` (Frontier→Colonial collided with a pre-existing Colonial).

**Tests:** all 18 crossref tests PASS (incl. 2 new TEA RED tests for malformed history/legend YAML); both live-pack wiring tests (crossref AC5 + 64-4 sibling) PASS (kept strict). ruff clean.
**Full suite:** 5 failed / 7513 passed / 1362 skipped — exactly the known baseline (test_zones_carry_cache_boundary_flag + 4× audit_namegen_corpora). No regressions; GREEN target met.
**Branches (pushed):** server (8a218235) + content (d2dfcfe) both on `feat/64-5-cross-reference-content-lint`.

**Handoff:** To TEA (verify) — all ACs green across 10 live packs; no rescope needed.

---

## Appendix — RED Test Run (2026-05-28, RUN_ID 64-5-tea-red)

Full server suite (env: `SIDEQUEST_DATABASE_URL`, `SIDEQUEST_GENRE_PACKS` set):
**13 failed, 7503 passed, 1362 skipped** (~29s, 8877 collected, no import/collection errors).

- 8 of the 13 failures are the new RED tests (all `Expected an ERROR ... got: []` — feature unimplemented).
- 5 pre-existing/unrelated failures (the baseline):
  - `tests/agents/test_prompt_cache_attribution_otel.py::test_zones_carry_cache_boundary_flag`
  - `tests/scripts/test_audit_namegen_corpora.py::test_audit_live_tree_exits_zero_after_corpus_expansion`
  - `tests/scripts/test_audit_namegen_corpora.py::test_audit_live_tree_reports_named_thin_corpora_resolved`
  - `tests/scripts/test_audit_namegen_corpora.py::test_audit_live_tree_no_named_corpora_left_thin_post_expansion`
  - `tests/scripts/test_audit_namegen_corpora.py::test_audit_live_tree_corpora_above_warn_threshold`

---

## TEA Verify Assessment (2026-05-28)

**Phase:** verify
**Verdict:** ✅ PASS — GREEN independently verified. Ready for Reviewer.
**Verified branches:** server `3eab91a8`, content `cc5c64c` (both on `feat/64-5-cross-reference-content-lint`).

All 5 verify checks from team-lead PASS:

1. **Full suite (env set):** 7511 passed / **5 failed** / 1362 skipped, no collection/import errors. The 5 failures are EXACTLY the known baseline (`test_zones_carry_cache_boundary_flag` + 4× `test_audit_namegen_corpora`) — nothing new, no regression.
2. **Crossref file 16/16:** all 8 RED targets now PASS and all controls/pins/AC4 still PASS. The 64-4 sibling `test_all_live_packs_pass_content_validation` PASSES.
3. **Strictness — STRONGEST evidence:** `git diff --stat 6615b5d5 3eab91a8 -- tests/` is EMPTY — Dev modified **zero** test files. Both live-pack tests still `assert not failures` (zero errors). GREEN was earned by implementation + content fixes, not by weakening tests.
4. **Wiring (non-test consumer):** ran the production CLI (`python -m sidequest.cli.validate pack`). Live pack `space_opera` → PASS, exit 0. Synthesized-bad fixture → FAIL, exit 1, surfacing both `history.yaml references unknown trope id 'zzz_phantom_trope'` (AC1) and `archetypes.yaml archetype 'The Stranger' references class 'ZZZNotAClass' not in rules.yaml allowed_classes` (AC2) — id + file in each. Code path confirmed: `validate_pack_structure` (genre tier) + `_validate_world` (world tier) both call the new helpers; `genre_trope_ids`/`genre_allowed` threaded into worlds for the genre∪world union.
5. **Remap completeness:** the 3 remapped files carry no danglers — `space_opera/archetypes.yaml` has no `Frontier` (now `Colonial`); `heavy_metal/evropi/archetypes.yaml` has no `Half-Orc` (net `Human`); `neon_dystopia/franchise_nations/archetypes.yaml` has no `Detective` (now `Solo`). Comprehensive coverage guaranteed by the strict live-pack tests.

Note (per team-lead): OTEL not expected — this is a dev-time CLI validator, not a runtime GM-panel subsystem. Not flagged.

No simplify pass run: the verify scope was independent verification of a Dev-completed GREEN per team-lead's explicit 5-point checklist (peloton mode); no new code authored by TEA.

### Delivery Findings — TEA (test verification)
- No upstream findings during test verification. All 5 verify checks pass; cross-ref lint is strict, wired, and green across all live packs.
- **Improvement** (non-blocking): the testing-runner subagent again clobbered `sprint/.session/64-5-session.md` during the verify run (known gotcha). TEA backed the file up before the run and restored it (Dev's Delivery Findings + Dev Assessment preserved) before appending this verify assessment. *Found by TEA during test verification.*

**Handoff:** To Reviewer (Westley) — verified GREEN, strict tests, wiring confirmed end-to-end.

## Reviewer Assessment

**Verdict:** REJECTED (one blocking finding; rest of the work is strong)

**Data flow traced:** broken/dangling content ref → `validate_pack_structure` → per-tier cross-ref validators → ERROR list. For trope-id membership (AC1/AC2/AC3) the flow is correct and strict. For a *syntactically broken* history.yaml/legend, the flow silently drops the parse error → validator reports PASS (the blocking gap).

**Pattern observed:** parse layer (64-4) validates only files with a registered pydantic model (archetypes/tropes/archetype_constraints); history.yaml + legends/*.yaml have NO model, so the cross-ref layer is their only touch — and it swallows parse errors (pack.py:393-398, 438-440).

**Verified good:**
- AC2 raw `safe_load` to dodge `_from:` — Dev's claim holds across all 10 packs: only space_opera uses `_from:`, at rules.yaml:521 (dogfight interactions), NOT on allowed_classes/allowed_races (lines 23/33, plain inline lists).
- `_iter_history_chapters` both shapes are real in live content (top-level `chapters:` in many worlds; `history_structure.chapters:` in spaghetti_western genre tier) and both handled.
- `_find_archetypes_base` fails loud (ERROR), rules.yaml absence is a required-file structural error, archetypes_base parse failure surfaces as ERROR.
- ArchetypeConstraints model (`extra: forbid` + required `genre_flavor`) means typo'd weight keys / absent genre_flavor already error at the parse layer — the crossref's fixed-tuple weight scan is safe.
- 16/16 crossref tests pass; RED→GREEN tests diff is empty (no test-weakening); all 10 live packs PASS the lint including the content fixes.
- Content remaps: heavy_metal (net `[Human]`) + neon_dystopia (`[Solo, Face]`) clean; spaghetti_western trope-id corrections legitimate.

**Findings:**
| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] | Broken history.yaml / legend YAML passes validator silently; comment falsely claims parse-layer coverage that doesn't exist (No Silent Fallbacks `<critical>` rule) | server pack.py:393-398, 438-440 | Surface `read_err` as a loud ERROR in both functions; fix the false comment; add RED test for broken history.yaml → ERROR |
| [LOW] | Remap created duplicate `typical_races: [Colonial, Colonial]` (Dev dedup'd heavy_metal but missed this) | content space_opera/archetypes.yaml (2nd hunk) | Dedup to `[Colonial]` |
| [LOW] | Inline-def id added to known set unvalidated (typo on name-carrying entry unprotected) | server pack.py:411-415 | Documented limitation — defensible (elemental_harmony needs it); no change required, note for follow-up |
| [LOW] | Two evropi legend dangling refs DELETED, not corrected | content evropi/legends/*.yaml | Keith confirm phantom-vs-missing-trope intent |

**Handoff:** Back to Dev — blocking fix is server-only (~5 lines + one test). Content Lows (dup-Colonial, legend intent) can ride the same round.

## TEA Re-Verify Assessment — rejection-fix delta (2026-05-28)

**Verdict:** ✅ PASS — fix delta verified GREEN at unit AND consumer level. Ready for Reviewer re-approval.
**Verified:** server `8a218235`, content `d2dfcfe`.

1. **Full suite (env set):** 7513 passed / **5 failed (EXACTLY the baseline)** / 1362 skipped, 0 errors, no collection/import errors. **crossref 18/18.** No regressions.
2. **HIGH fixed at the CONSUMER path (No-Silent-Fallbacks proof):** ran the real CLI `python -m sidequest.cli.validate pack` against a pack/world with a malformed `history.yaml` AND a malformed `legends/broken_legend.yaml` → **exit 1**, two loud ERRORs: `world 'dust_and_lead': history.yaml is not valid YAML: ...` and `world 'dust_and_lead': broken_legend.yaml is not valid YAML: ...`. Previously a silent pass. Fix is the right shape: `_validate_history_trope_refs` `return []`→`return [read_err]`; `_validate_legend_trope_refs` `continue`→`errors.append(read_err)`.
3. **No over-correction:** live `space_opera` (valid history/legend) → CLI **exit 0, PASS**; the strict 10-live-pack test is part of the green 18/18 — the new error fires ONLY on malformed YAML.
4. **space_opera 'Free Trader' typical_races = `['Colonial']`** — single value, no dup, not empty (content `d2dfcfe`).

Session backed up before each suite run; not clobbered this round.
