---
story_id: "65-10"
jira_key: ""
epic: "65"
workflow: "tdd"
---
# Story 65-10: Reference TOC/section-mapping repair + register POI and Cast sections

## Story Details
- **ID:** 65-10
- **Jira Key:** (not configured for this project; YAML-tracked only)
- **Workflow:** tdd
- **Stack Parent:** none
- **Status:** SPARSE STUB — setup phase to research and reconcile scope

## Story Context

**Epic:** 65 — Content Infrastructure — R2 asset tracking and audit

### CRITICAL SCOPE RECONCILIATION REQUIRED

This story entered the sprint as a title-only stub (title + points:2 + workflow:tdd only; no description, no acceptance criteria). **The Dev/Architect MUST resolve the following scope ambiguity FIRST, before writing tests or implementation:**

**The Title Says:** "Reference TOC/section-mapping repair + register POI and Cast sections"

**The Problem:**
- **65-8** (completed, POI gallery) is NOT explicitly titled "register POI"; it renders POI images in the lore page geography section
- **65-9** (completed 2026-06-02, Architect-approved) explicitly registers the Cast section with TOC entry appended dynamically in `assemble_lore_page` (lines 1350-1377 of `reference_renderer.py`)
- **65-11** (completed 2026-06-03, Map section) also registers its section dynamically via the Cast-append pattern
- **65-12** (completed 2026-06-03, Timeline section) also registers its section dynamically via the Cast-append pattern

The title "register POI and Cast sections" suggests 65-10 either:
1. **Predates** 65-9 (and is now partially redundant, since Cast is already registered), OR
2. **Is specifically about TOC/section-mapping repair** (the PACK_TOC / TOC_TO_FILES machinery in `reference_theme.py`) plus **POI registration**, with Cast already handled by 65-9.

The `TOC_TO_FILES` dict in `reference_theme.py` (lines 363-378) is a **static mapping** from `toc_id` → `list[file_stems]`. This governs which YAML-derived file renders belong in which named section. The dynamic sections (Cast, Map, Timeline) are not referenced in `TOC_TO_FILES` because they're not file-stem-based — they're synthesized in `assemble_lore_page`.

**The Architect must decide:** Is 65-10 about:
- **Option A:** Formalizing the registration path for dynamically-appended sections (Cast, Map, Timeline) so they're no longer ad-hoc appends to `kept_toc`, but follow a declarative registration pattern? This would be a refactor of the current pattern in `assemble_lore_page` (lines 1350-1424).
- **Option B:** Ensuring the POI section (from 65-8) is properly registered in PACK_TOC/TOC_TO_FILES (checking whether "geography" needs an entry, or if "lore" + "history" are the correct buckets)?
- **Option C:** Something else entirely related to TOC/section-mapping that this analysis has missed.

**Do NOT proceed with RED until this is clarified.**

### Technical Approach (Pending Architect Reconciliation)

Assuming Option A (the most likely given the story points and the "repair" framing):

**Current State (65-9 / 65-11 / 65-12 pattern):**
- `assemble_lore_page` calls `_wrap_sections_by_toc` first (wraps file-based sections per `TOC_TO_FILES`)
- Returns `(body, kept_toc)` where `kept_toc` contains only TOC entries whose sections rendered content
- Then Cast block (lines 1350–1377): if `cast_entries` render, append HTML to body + append TOC entry manually
- Then Map block (lines 1379–1407): if cartography exists, append HTML + TOC entry manually
- Then Timeline block (lines 1409–1424): if legends exist, append HTML + TOC entry manually
- All three use `_int_to_roman(len(kept_toc) + 1)` to auto-number the TOC entry

**Issues / Opportunities:**
1. **TOC registration is ad-hoc** — each dynamic section manually appends to `kept_toc` and body; no central registry or pattern enforcement
2. **PACK_TOC entries are unused** — the static `PACK_TOC` dict is NOT queried by `assemble_lore_page` (it's only used by `_build_toc` at render-time to emit the `<nav>`); dynamic sections bypass it entirely
3. **No section IDs are registered in PACK_TOC** — "cast", "map", "timeline" don't exist as entries in any pack's `PACK_TOC` list, so if the `<section id="cast">` fails to render, the TOC still tries to link to it
4. **Inconsistent numbering** — file-based sections use Roman numerals from `PACK_TOC`; dynamic sections auto-compute numerals based on `len(kept_toc)`

**Likely Repair Path:**
- Add "geography" (POI section) + "cast" + "map" + "timeline" entries to `PACK_TOC` for all packs that support them (or to `DEFAULT_TOC` for consistency)
- Extend `TOC_TO_FILES` to handle pseudo-sections that are not file-based (e.g., map `"map": []` to signal "this is a synthesized section")
- OR, refactor `assemble_lore_page` to use a declarative registry (e.g., `{"cast": <section_renderer>, "map": <section_renderer>}`) so registration + rendering + TOC entry are unified
- Ensure PACK_TOC numbering is preserved and auto-computed numerals don't conflict
- Add tests to verify that absent dynamic sections (world with no `portrait_manifest.yaml` → no Cast) don't leave dangling TOC entries

### Acceptance Criteria (To Be Authored After Reconciliation)

**Pending Architect Decision:** Do not write ACs until the reconciliation decision is documented. The following are PLACEHOLDER SKETCHES pending the actual scope:

**Placeholder AC1:** All synthesized sections (Cast, Map, Timeline) are registered with explicit TOC entries in `PACK_TOC` or via a central registry, not ad-hoc appends to `kept_toc`.

**Placeholder AC2:** A world whose Portrait manifest is absent (no Cast section) does not emit a dangling TOC entry pointing to a non-existent `<section id="cast">` anchor.

**Placeholder AC3:** A world whose cartography.yaml is absent (no Map section) does not emit a dangling TOC entry.

**Placeholder AC4:** POI section (from 65-8, if separate) is properly registered in TOC/TOC_TO_FILES.

**Placeholder AC5:** PACK_TOC entries for all 11 live packs include any newly-registered dynamic sections (cast, map, timeline).

### Key Code References

- **TOC machinery:** `PACK_TOC` + `TOC_TO_FILES` in `sidequest/server/reference_theme.py` (lines 268–378)
- **Dynamic section appends:** `assemble_lore_page` in `sidequest/server/reference_renderer.py` (lines 1313–1434), specifically:
  - Cast block: lines 1350–1377
  - Map block: lines 1379–1407
  - Timeline block: lines 1409–1424
- **Section wrapping:** `_wrap_sections_by_toc` in `reference_renderer.py` (lines 960–1005)
- **TOC building:** `_build_toc` in `reference_renderer.py` (referenced but not shown; controls HTML `<nav>` generation)
- **Route:** `lore_page` in `sidequest/server/reference_routes.py` (line 119–131), GET /reference/lore/{pack}/{world}
- **Test fixtures & patterns:** 
  - `tests/server/test_reference_cast_manifest_gate.py` (65-9 Cast tests)
  - `tests/server/test_reference_poi_manifest_gate.py` (65-8 POI tests)
  - `tests/server/test_reference_map.py` (65-11 Map tests)
  - `tests/server/conftest.py` — `gated_client`, `otel_capture`, `span_attrs_by_name` fixtures
- **OTEL spans:** `sidequest/telemetry/spans/reference.py`, `FLAT_ONLY_SPANS`
- **Related ADRs:** ADR-135 (Reference Pages as public table tools), ADR-088 (ADR Frontmatter / registration patterns)

### Dependencies & Coordination

- **Blocks:** Nothing (standalone repair)
- **Blocked by:** Architect decision on scope (Option A/B/C above)
- **Coordinate with:**
  - 65-8 (POI gallery — determine if "register" work needed)
  - 65-9 (Cast — cast-registration pattern established; 65-10 likely generalizes it)
  - 65-11 (Map — already follows cast-append pattern)
  - 65-12 (Timeline — already follows cast-append pattern)
  - Reviewer notes from 65-9 PR #573 (carryover findings folded into the Cast approach)

### Open Questions for Architect

1. **What exactly is "TOC/section-mapping repair"?** (TOC entries dangling on absent dynamic sections? PACK_TOC out of sync with rendered sections? TOC_TO_FILES unused?)
2. **Should POI (from 65-8) be explicitly registered as a named section in PACK_TOC/TOC_TO_FILES?** Or is POI content already correctly bucketed under "lore" / "world" / "history"?
3. **Should Cast, Map, Timeline be added to PACK_TOC for all packs, or only for packs that author those features?** (A pack without cartography.yaml shouldn't have a dangling "Map" TOC entry.)
4. **Is the repair a refactor (centralize the registration pattern) or a gating fix (ensure TOC entries only render when their section renders)?**

## SM Assessment

**Routing decision (Camina Drummer, SM):** Story 65-10 entered as a sparse stub
(title + 2pts only). Setup is complete — branch `feat/65-10-reference-toc-section-mapping`
off `develop`, session + standalone story-context recovered
(`sprint/context/context-story-65-10.md`; sm-setup had skipped it — known recurring gap).

**Load-bearing handoff note:** This is NOT a normal RED handoff. The story title
is partially STALE — epic-65 siblings 65-8 (POI), 65-9 (Cast), 65-11 (Map),
65-12 (Timeline) all shipped after the title was written, so "register POI and
Cast sections" is largely already done. The real remaining work is almost
certainly the **"TOC/section-mapping repair"** half: the three dynamic sections
ad-hoc append to `kept_toc` after `_wrap_sections_by_toc` instead of registering
declaratively, with no guard against TOC↔section parity drift.

**TEA must reconcile scope BEFORE writing the RED tests** — pick interpretation
A (formalize/guard dynamic-section registration), B (POI TOC registration audit),
or C (close-as-mostly-done with evidence). Pull Architect if the choice isn't
clear from the code. ACs are intentionally left TBD in the context doc; TEA
authors them post-reconciliation. Standard guardrails apply: real-route
integration test via `gated_client`, OTEL span with complement assertion, loud
failure on missing input, regression on existing sections.

Jira: not configured for this project (YAML-tracked only) — claim explicitly skipped.

## TEA Assessment

**Scope reconciliation (resolved by Operator, 2026-06-03):** Presented the stub's
two live interpretations to Bossmang via AskUserQuestion — (A) build the repair vs
(C) close as superseded. **Operator chose (A) Build the repair.** Code analysis
confirmed the literal title is stale: POI is inline imagery (65-8), not a section;
Cast is already registered (65-9). The genuine remaining work is the
**TOC/section-mapping repair**: today the three dynamic sections (Cast/Map/Timeline)
register via three near-identical ad-hoc append blocks in `assemble_lore_page`
(`reference_renderer.py:1349-1424`), the TOC/section *assembly* emits NO OTEL span
(every sub-feature has one; the composition that stitches them does not), and the
only TOC↔section parity check is the **client-side** `ref-bad-anchor` JS banner —
nothing server-side, nothing in OTEL.

**Tests Required:** Yes

**Test Files:**
- `sidequest-server/tests/server/test_reference_lore_assembled.py` — 12 tests, 6 ACs.
- `sidequest-server/tests/fixtures/packs/reference_v2_fixture/worlds/assembled_fixture/`
  — new combined fixture world authoring all three dynamic sections at once
  (cast+map+timeline+base reckoning); composed TOC = reckoning/cast/map/timeline
  (verified by direct render before pinning).

**Acceptance Criteria (authored by TEA post-reconciliation):**
- **AC1** — A single `sidequest.reference.lore_assembled` span fires once per lore
  render (incl. bare worlds), carrying `reference.pack`/`reference.world`.
- **AC2** — The span records the composed TOC: `reference.lore_section_ids`
  ("/"-joined, in composed order) and `reference.lore_section_count` (int). For the
  combined world: `reckoning/cast/map/timeline`, count 4.
- **AC3** — `reference.lore_dynamic_sections` honestly records which of
  cast/map/timeline registered this render (complement-tested across a cast-only,
  map-only, timeline-only, and bare world — proves it's not an always-list constant).
- **AC4** — `reference.lore_parity_ok` (bool) is True iff every composed TOC id has a
  matching `id="…"` body anchor (the dangling-link guarantee), and a well-formed
  world fires NO orphan span.
- **AC5** — Parity GUARD (server-side, observable): `emit_lore_assembled_span(*, pack,
  world, toc_entries, anchor_ids) -> bool` returns False AND fires exactly one
  `sidequest.reference.lore_section_orphaned` WARN span naming the ghost id when a
  TOC entry has no matching anchor; clean input fires none (No Silent Fallbacks).
- **AC6** — Regression: all of reckoning/cast/map/timeline still render after the
  three ad-hoc blocks are unified (DRY); ADR-135 single fixed projection holds
  (`?audience` doesn't change composed section ids).

**Tests Written:** 12 (11 RED, 1 regression-green)
**Status:** RED confirmed via testing-runner (`65-10-tea-red`): 11 failed, 1 passed.
All failures are the expected kind — `lore_assembled` span never fires (`got 0` /
IndexError on empty span list) or `emit_lore_assembled_span` ImportError. No 500s,
no fixture errors, clean collection. The 1 green is `test_all_dynamic_sections_
still_render_after_repair` — a deliberate regression guard pinning existing
behavior the DRY refactor must preserve.

### Rule Coverage

| Rule (lang-review/python.md + CLAUDE.md) | Test(s) | Status |
|------|---------|--------|
| OTEL on every subsystem decision (CLAUDE.md) | all AC1–AC4 assembly-span tests | failing (RED) |
| No Silent Fallbacks (drift is loud) | `test_emit_lore_assembled_span_flags_orphan_toc_entry` | failing (RED) |
| Span complement (real gate, not constant) | AC3 cast/map/timeline-only + AC5 clean-vs-drift | failing (RED) |
| Test quality — specific-value asserts, no vacuous/truthy-only | every test asserts exact ids/counts/bools | n/a (self-checked) |
| No source-text wiring tests (server CLAUDE.md) | all route tests assert via OTEL/HTML behavior, never source grep | n/a |

**Rules checked:** test-quality rules satisfied; the load-bearing implementation
rule (No Silent Fallbacks) is enforced behaviorally via the orphan span. The
feature emits span attrs + reuses existing section presenters — no new
prose-to-HTML surface, so no CWE-79 escaping test is owed here.
**Self-check:** 0 vacuous tests.

**Handoff:** To Dev (Naomi Nagata) for GREEN.

**Dev guidance (implementation sketch, non-binding):**
- Add `SPAN_REFERENCE_LORE_ASSEMBLED = "sidequest.reference.lore_assembled"` and
  `SPAN_REFERENCE_LORE_SECTION_ORPHANED = "sidequest.reference.lore_section_orphaned"`
  to `telemetry/spans/reference.py` + `FLAT_ONLY_SPANS`, with ctx-manager helpers
  matching the existing reference-span style.
- Implement `emit_lore_assembled_span(*, pack, world, toc_entries, anchor_ids)` in
  `reference_renderer.py`: compute `missing = [e["id"] for e in toc_entries if e["id"]
  not in anchor_ids]`; `parity_ok = not missing`; fire one assembly span (section
  ids/count/dynamic-sections/parity_ok) + one orphan WARN span per missing id;
  return `parity_ok`.
- Wire it into `assemble_lore_page` just before `_wrap_document`, passing `kept_toc`
  + `_collect_anchor_ids(hero_html + body)`. Derive `lore_dynamic_sections` from the
  registration path (the cast/map/timeline blocks).
- DRY the three append blocks (`reference_renderer.py:1372-1424`) behind one helper
  (e.g. `_append_dynamic_section(body, kept_toc, *, id, label, html)`). The DRY is
  guarded only by AC6 regression (no source-text test asserts the helper exists).

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest-server/sidequest/telemetry/spans/reference.py` — added
  `SPAN_REFERENCE_LORE_ASSEMBLED` + `SPAN_REFERENCE_LORE_SECTION_ORPHANED` (both in
  `FLAT_ONLY_SPANS`) and their ctx-manager helpers `reference_lore_assembled_span` /
  `reference_lore_section_orphaned_span`, matching the existing reference-span style.
- `sidequest-server/sidequest/server/reference_renderer.py` — (1)
  `emit_lore_assembled_span(*, pack, world, toc_entries, anchor_ids) -> bool` computes
  composed section ids, the dynamic-section subset (`_DYNAMIC_SECTION_IDS =
  cast/map/timeline`), and parity (TOC ids ⊆ anchors), fires one assembly span + one
  orphan WARN span per dangling id, returns `parity_ok`; (2) `_append_dynamic_section(...)`
  unifies the three triplicated Cast/Map/Timeline append blocks (the DRY); (3)
  `assemble_lore_page` calls the append helper ×3 + emits the assembly span before
  `_wrap_document`, using the same `_collect_anchor_ids(hero_html + body)` anchor set the
  client banner sees.

**Minimalism note:** Parity is one-directional (composed TOC ids ⊆ body anchors — the
dangling-link case), exactly as TEA's AC4/AC5 specify. No PACK_TOC/TOC_TO_FILES schema
change — the dynamic sections stay runtime-synthesized; 65-10 adds observability + a
guard, not the declarative-registry rewrite the stub's discarded "Option A" sketch
floated (the Operator's "build the repair" decision + TEA's ACs did not require it).

**Tests:** 12/12 new passing (GREEN); 120/120 sibling reference-suite regression
passing (132 total, 0 failures) — verified via testing-runner `65-10-dev-green`.
**Branch:** feat/65-10-reference-toc-section-mapping (pushed)

**Handoff:** To next phase (verify/review).

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

Verified each TEA-authored AC against the diff (`git diff develop`):
- **AC1/AC2** — `emit_lore_assembled_span` is called unconditionally once per render
  before `_wrap_document`; span carries `lore_section_ids` + `lore_section_count`. ✓
- **AC3** — `dynamic_sections` is derived as `composed section_ids ∩ _DYNAMIC_SECTION_IDS`
  (cast/map/timeline), so it is honest by construction — a dynamic section appears iff it
  registered into the composed TOC. The complement tests prove it isn't a constant. ✓
- **AC4/AC5** — parity is the one-directional `TOC ids ⊆ anchors`; `parity_ok = not missing`;
  one orphan WARN per dangling id; helper returns `parity_ok`. Matches the TEA contract
  signature exactly. ✓
- **AC6** — DRY via `_append_dynamic_section` (the three ad-hoc blocks collapse to one
  helper, behavior-preserving); 120 sibling-suite regression tests green; audience-param
  invariance covered. ✓

**Scoping note (aligned, not drift):** Dev correctly declined the stub's discarded
"Option A — declarative PACK_TOC/TOC_TO_FILES registry" sketch. That sketch lived in the
sm-setup Story Context as a *placeholder*, explicitly superseded by the higher-authority
Operator decision ("build the repair", AskUserQuestion 2026-06-03) and TEA's authored ACs.
Per the spec-authority hierarchy (session scope > story context), the placeholder is not
binding. The reuse-first call is correct: the repair extends the existing runtime-synthesis
+ `_collect_anchor_ids` infrastructure rather than introducing a registry abstraction no AC
required.

**Decision:** Proceed to review (TEA verify next).

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 3 (reference_renderer.py, telemetry/spans/reference.py,
test_reference_lore_assembled.py)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | 0 findings. `_append_dynamic_section` DRY is intentional+correct; noted (MINOR, not a finding) that a `_lore_attrs` helper could share pack/world attrs across the two new spans — not worth it for two different-signature spans. |
| simplify-quality | clean | 0 findings. Naming, FLAT_ONLY_SPANS registration, loud-fail orphan span, type hints all conform to project patterns. |
| simplify-efficiency | clean | 0 findings. Minimal, no premature abstraction, no defensive over-handling. |

**Applied:** 0 high-confidence fixes (all teammates clean)
**Flagged for Review:** 0
**Noted:** 1 low-confidence observation (the `_lore_attrs` extraction — dismissed)
**Reverted:** 0

**Overall:** simplify: clean

**Quality Checks:** ruff clean; pyright 0 errors/0 warnings on both impl files;
132 reference tests green (12 new + 120 sibling regression) per `65-10-dev-green`.
**Handoff:** To Reviewer (Chrisjen Avasarala) for code review.

### TEA (test verification)
- No upstream findings during test verification. Simplify pass clean; no new
  deviations beyond those already logged at red/spec-check.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 new (1 pre-existing TODO at reference_renderer.py:395, not in diff) | N/A |
| 2 | reviewer-edge-hunter | Yes | findings | 0 bugs; 5 obs (2 med, 3 low) | confirmed 0 new (parity-discard already counted under [SILENT]; rules-page already logged by Architect); dismissed: KeyError-on-id (all builders set id), empty-html-append (callers guard), "/"-delimiter (internal constants) |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 2 | confirmed 1 (downgraded LOW), dismissed 1 |
| 4 | reviewer-test-analyzer | Yes | findings | 7 (1 high, 3 med, 3 low) | confirmed 3 (non-blocking), dismissed 4 |
| 5 | reviewer-security | Yes | clean | none | N/A |
| 6 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings |

**All received:** Yes (5 enabled returned, 4 disabled pre-filled)
**Total findings:** 4 confirmed (all LOW/non-blocking), 5 dismissed (with rationale), 0 deferred

## Reviewer Assessment

**Verdict:** APPROVED

No Critical or High issues. Production code is correct across all five reviewers
(edge: 0 bugs; security: clean; silent-failure: 1 by-design observation; preflight:
GREEN). The test-analyzer's findings are real but minor and largely cross-covered;
none would let a real 65-10 defect ship. Confirmed gaps are logged as non-blocking
Delivery Findings for a 65-13-style follow-up test-hardening pass.

### Observations

- **[VERIFIED]** Assembly span is genuinely wired into production — `assemble_lore_page`
  calls `emit_lore_assembled_span(...)` unconditionally before `_wrap_document`
  (reference_renderer.py:~1491), and both span names are registered in `FLAT_ONLY_SPANS`
  (spans/reference.py). Not a stub; the one decision (TOC composition) that emitted nothing
  now emits. Complies with the OTEL-on-every-subsystem-decision rule.
- **[VERIFIED]** Data flow traced: route params `pack`/`world` → span attributes only;
  section ids come from internal TOC constants + the three hardcoded `_append_dynamic_section`
  calls. No author/user string reaches a section id or an HTML sink. `escape()` on
  `entry["id"]` in the TOC `<a href>` render is unchanged. Evidence corroborated by [SEC]
  (clean). Complies with ADR-135 public-projection + CWE-79.
- **[LOW][SILENT]** `parity_ok` return is discarded at the `assemble_lore_page` call site
  (reference_renderer.py:~1491). Confirmed by both silent-failure-hunter and edge-hunter.
  **Downgraded to LOW / accepted:** the loud channel for content drift in this subsystem is
  the OTEL WARN span (`lore_section_orphaned`), exactly matching the established sibling
  pattern (`reference_map_dangling_edge_span`, `reference_toc_missing_span`) which also
  observe-via-OTEL without raising. The bool is consumed by the AC5 unit test (a real
  testability seam — so the suggested "make it return None" would break that test). Not a
  silent failure: drift IS surfaced loudly in OTEL.
- **[DISMISSED][SILENT]** Orphan span sets `reference.level="WARN"` as an attribute without
  an OTEL span *status*. Dismissed: the hunter itself confirms this matches the existing
  reference drift-span convention (`reference_map_dangling_edge_span`, spans/reference.py:~533)
  — not a regression introduced here; changing it is a cross-cutting span-family decision,
  out of 65-10 scope.
- **[DISMISSED][TEST]** test-analyzer HIGH ("positive `lore_parity_ok` span attr never
  asserted"). **Dismissed with evidence:** `test_well_formed_world_reports_parity_ok_and_no_orphan_span`
  (AC4) already asserts `attrs.get("reference.lore_parity_ok") is True` through the real route.
  The positive span-attr is covered; the unit-test complement the hunter wants is redundant.
- **[LOW][TEST]** Multi-orphan case not exercised — the orphan unit test uses one ghost id,
  so an impl that short-circuited after the first orphan would still pass. Confirmed,
  non-blocking: the impl is a plain `for sid in missing` comprehension with no short-circuit
  (verified reference_renderer.py), behavior is correct. Logged for follow-up.
- **[LOW][TEST]** `test_audience_param_does_not_change_composed_sections` lacks an explicit
  `assert len(spans) == 2` guard, so a one-span-fired regression would pass trivially.
  Confirmed, non-blocking: mitigated by AC1 (`test_lore_assembled_span_fires_once_per_render`)
  which already pins exactly-one-span-per-render. Logged for follow-up.
- **[LOW][TEST]** No live-route test of the NEGATIVE parity branch (orphan via real
  `_collect_anchor_ids` miss). Confirmed, non-blocking: a presenter that emits its section
  without its own anchor is artificial to author, and the positive route test (AC4) validates
  the contrapositive — `assemble_lore_page` passing a wrong anchor set would flip well-formed
  worlds to `parity_ok=False` and fail AC4. Logged for follow-up.
- **[DISMISSED][EDGE]** `/`-delimiter collision, KeyError on `entry["id"]`, empty
  `toc_entries`, anchor-collection-type, duplicate ids — all dismissed: section ids are
  internal constants (no `/`), every `kept_toc` builder sets `"id"`, empty/typed paths handled,
  `set(anchor_ids)` normalizes input. Edge-hunter: 0 bugs.

### Rule Compliance

| Rule (CLAUDE.md / SOUL.md / lang-review python.md) | Applies to | Verdict |
|------|-----------|---------|
| No Silent Fallbacks | orphan WARN span per dangling id; parity drift loud in OTEL | Compliant |
| OTEL on every subsystem decision | the TOC-assembly decision now emits `lore_assembled` | Compliant |
| No source-text wiring tests | all 12 tests assert via OTEL/HTML behavior, no `read_text()` | Compliant |
| No stubs / no half-wired | emit wired into `assemble_lore_page` + FLAT_ONLY_SPANS registration | Compliant |
| ADR-135 public projection | span carries only public structural metadata; `?audience` invariance tested | Compliant ([SEC]) |
| #6 test quality (no vacuous asserts) | every test asserts exact ids/counts/bools | Compliant (gaps are coverage, not vacuity) |
| #7 resource leaks / #8 unsafe deser / #10 import hygiene | no open()/connect()/yaml.load/pickle/eval; named imports only | Compliant |
| Type annotations | `Collection[str]`, `-> bool`, `-> tuple[...]` all annotated | Compliant (pyright 0 errors) |

### Devil's Advocate

Suppose I argue this code is broken. The strongest case: the parity guard is theater. Its
return value is thrown away at the only production call site, so in production *nothing acts
on parity* — a page with a dangling TOC link still renders 200, identical to before. If the
real goal were to prevent broken nav, this fails: it observes, it does not enforce. A
malicious or careless author who introduces a section id that never anchors gets a clean
page and one WARN span buried among thousands — no operator is paged, because the span has no
ERROR status (Finding 2). So "the GM panel is the lie detector" only works if someone is
actually watching that panel; absent a backend alert rule keyed on the span, drift is
effectively invisible at runtime. Second angle: the parity check is one-directional by design,
so an *orphan section* (rendered `<section id=>` with no TOC entry) is never flagged — a whole
section could silently lose its nav entry and the guard would report `parity_ok=True`. Third:
the tests lean on a single combined fixture and cross-test coverage; the negative branch
through the live route is untested, so a wiring slip in which `assemble_lore_page` feeds
`emit_lore_assembled_span` a stale/partial anchor set would only be caught indirectly.

Rebuttal: every one of these is a *scope* argument, not a *correctness* argument. The story
(Operator-decided) is "add observability + a guard," explicitly NOT "fail the render on
drift" — failing a public reference page over a cosmetic nav issue would be an availability
regression. One-directionality is documented and deliberate (unmapped-file tail sections
legitimately lack TOC entries — full bijection would false-positive). The WARN-status and
orphan-section gaps match the entire existing reference span family; fixing them is an
epic-wide decision, not a 65-10 one. The contrapositive of AC4 covers the wiring slip. So the
devil's case reduces to "this could be a bigger feature" — true, and out of scope — not "this
feature is wrong." Nothing here rises to blocking.

**Data flow traced:** route `pack`/`world` → span attributes (not HTML); section ids →
internal constants only → safe (no injection, no leakage).
**Pattern observed:** DRY extraction `_append_dynamic_section` + observe-only span emitter,
consistent with the existing reference span family — reference_renderer.py:~1321,1345.
**Error handling:** no error paths to swallow; drift is loud via the orphan WARN span.
**Handoff:** To SM for finish-story.

## Design Deviations

### Architect (reconcile)
Reviewed all in-flight deviation entries (TEA test-design ×2, Architect spec-check, Dev
implementation, Reviewer audit) — all six fields present where required, spec sources real,
implementation descriptions match the shipped diff. No prior entry needed correction. AC
accountability: all six TEA-authored ACs are DONE (none deferred/descoped), so the AC-deferral
cross-check is a no-op. One substantive design decision was implicit across the in-flight logs
and is recorded here in full so the manifest is self-contained:

- **Parity drift is observe-only (WARN span), not render-failing**
  - Spec source: sprint/context/context-story-65-10.md, "AC Context" section
  - Spec text: "They must cover: the chosen repair behavior, a real-route integration test, an
    OTEL span proving the decision engaged (with a complement assertion), **a loud-failure
    edge**, and regression that the existing geography/cast/map/timeline/history sections still
    render unchanged."
  - Implementation: The "loud-failure edge" is realized as a `sidequest.reference.lore_section_orphaned`
    **WARN span** (plus `lore_parity_ok=false` on the assembly span) — NOT an HTTP 500 / raised
    exception. A lore page with a dangling TOC entry still renders 200; `emit_lore_assembled_span`'s
    `parity_ok` return is discarded at the `assemble_lore_page` call site (observe, don't enforce).
  - Rationale: Matches the established reference drift-span doctrine (`reference_map_dangling_edge_span`,
    `reference_toc_missing_span` also surface content drift via OTEL without raising), and honors
    availability — a public ADR-135 reference page must not 500 over a cosmetic nav-anchor mismatch.
    "No Silent Fallbacks" is satisfied because drift IS loud in OTEL (the GM panel is the lie
    detector), just not fatal to the render.
  - Severity: minor
  - Forward impact: The four non-blocking Reviewer follow-ups (multi-orphan coverage, audience
    span-count guard, negative-route integration test, WARN-attribute-vs-OTEL-status) all inherit
    this observe-only stance; a future epic-wide decision could promote parity drift to an
    alertable span status across the whole reference span family (out of 65-10 scope).

### Reviewer (audit)
- **TEA: "Literal story title superseded by sibling slices"** → ✓ ACCEPTED by Reviewer:
  the title is stale; 65-10 correctly scoped to the repair half. Evidence confirms Cast(65-9)/
  POI(65-8) already shipped.
- **TEA: "DRY refactor asserted only by regression, not directly"** → ✓ ACCEPTED by Reviewer:
  correct call per the no-source-text-wiring-tests rule; the DRY diff was eyeballed and is a
  clean, behavior-preserving extraction.
- **Architect: "No additional deviations found" / Dev: "No deviations from spec"** → ✓ ACCEPTED:
  spec alignment confirmed independently against the diff.

### Architect (spec-check)
- No additional deviations found. TEA's two deviation entries (title-staleness,
  DRY-asserted-only-by-regression) are accurate and complete; Dev implemented to spec
  with no further drift.

### Dev (implementation)
- No deviations from spec. Implemented the assembly-span + parity-guard contract
  exactly as TEA pinned it (span names, attribute keys, `emit_lore_assembled_span`
  signature, DRY of the three append blocks via `_append_dynamic_section`).

### TEA (test design)
- **Literal story title superseded by sibling slices**
  - Spec source: session title / context-story-65-10.md ("register POI and Cast sections")
  - Spec text: "Reference TOC/section-mapping repair + register POI and Cast sections"
  - Implementation: Tests cover the TOC/section-mapping *repair* only. "Register Cast"
    was delivered by 65-9; "register POI" is void (POI is inline imagery from 65-8,
    never a registered section). No tests assert POI/Cast *registration* as new work.
  - Rationale: Those features already shipped + are approved; re-testing them as 65-10
    work would be redundant. Operator chose "Build the repair" (AskUserQuestion 2026-06-03).
  - Severity: minor
  - Forward impact: none — Reviewer should read 65-10 as the repair story, not a
    POI/Cast registration story.
- **DRY refactor asserted only by regression, not directly**
  - Spec source: Operator decision (A) "DRY the 3 triplicated append blocks"
  - Spec text: "DRY the 3 triplicated append blocks behind one helper"
  - Implementation: No test asserts a specific helper exists/shape (that would be a
    forbidden source-text wiring test). AC6 regression proves all three sections still
    render after the refactor; the DRY itself is left to Dev + Reviewer judgement.
  - Rationale: server CLAUDE.md forbids source-text wiring tests; behavioral regression
    is the correct stable guard for a pure refactor.
  - Severity: minor
  - Forward impact: Reviewer should eyeball the unify-the-3-blocks diff for actual DRY.

## Delivery Findings
<!-- Append-only. Each agent writes under its own subheading. -->

### Reviewer (code review)
- **Improvement** (non-blocking): Multi-orphan coverage gap — the orphan unit test exercises
  exactly one dangling id, so a short-circuiting loop would pass. Affects
  `tests/server/test_reference_lore_assembled.py` (add a two-ghost-id case asserting
  `len(orphans) == 2`). Candidate for a 65-13-style follow-up. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `test_audience_param_does_not_change_composed_sections`
  lacks an `assert len(spans) == 2` guard (mitigated today by AC1's one-span-per-render pin).
  Affects `tests/server/test_reference_lore_assembled.py`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): No live-route test of the negative parity branch (orphan via
  a real `_collect_anchor_ids` miss); the contrapositive of AC4 covers the wiring today.
  Affects `tests/server/test_reference_lore_assembled.py`. *Found by Reviewer during code review.*
- **Question** (non-blocking): The orphan span uses `reference.level="WARN"` as an attribute
  with no OTEL span *status* (UNSET) — consistent with the whole reference drift-span family,
  but a backend alert rule keyed on span status would not fire on parity drift. Affects
  `sidequest/telemetry/spans/reference.py` (and the sibling drift spans) — an epic-wide
  decision, not 65-10. *Found by Reviewer during code review.*

### Architect (spec-check)
- **Improvement** (non-blocking): The new `lore_assembled` assembly span + parity guard
  are wired into `assemble_lore_page` only; `assemble_rules_page`
  (`sidequest/server/reference_renderer.py`) composes a TOC via the same
  `_wrap_sections_by_toc` + `_wrap_document` path and now has the same observability/parity
  gap the lore page just closed. A future story could call `emit_lore_assembled_span` (or a
  renamed `emit_reference_assembled_span`) from the rules page too. Out of 65-10 scope
  (TEA ACs are lore-only per ADR-135). *Found by Architect during spec-check.*

### Dev (implementation)
- No upstream findings during implementation. TEA's two findings (legends
  double-render; one-directional parity scope) are accurate and acknowledged —
  both confirmed pre-existing / by-design and out of 65-10 scope.

### TEA (test design)
- **Improvement** (non-blocking): The `legends` stem renders TWICE on the lore page —
  once as a raw unmapped-file section (`id="file-legends"`) and once as the synthesized
  Timeline section (`id="timeline"`). Observed while validating `assembled_fixture`.
  Affects `sidequest/server/reference_renderer.py` (legends could be added to a
  TOC_TO_FILES bucket or suppressed from the raw-file tail once the Timeline consumes
  it). Pre-existing (65-12), out of 65-10 scope. *Found by TEA during test design.*
- **Question** (non-blocking): Parity is intentionally one-directional (TOC ids ⊆ body
  anchors — the dangling-link case). Orphan *sections* (a `<section id=>` with no TOC
  entry) are NOT flagged, because unmapped-file tail sections legitimately have no TOC
  entry. If a future story wants full bijective parity, the unmapped-file sections need
  a different anchor convention first. Affects the parity guard's scope. *Found by TEA
  during test design.*

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-03T23:09:31Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-03T16:00:00Z | 2026-06-03T22:32:36Z | 6h 32m |
| red | 2026-06-03T22:32:36Z | 2026-06-03T22:52:38Z | 20m 2s |
| green | 2026-06-03T22:52:38Z | 2026-06-03T22:57:20Z | 4m 42s |
| spec-check | 2026-06-03T22:57:20Z | 2026-06-03T22:58:51Z | 1m 31s |
| verify | 2026-06-03T22:58:51Z | 2026-06-03T23:01:01Z | 2m 10s |
| review | 2026-06-03T23:01:01Z | 2026-06-03T23:08:32Z | 7m 31s |
| spec-reconcile | 2026-06-03T23:08:32Z | 2026-06-03T23:09:31Z | 59s |
| finish | 2026-06-03T23:09:31Z | - | - |