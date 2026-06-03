---
story_id: "65-13"
jira_key: ""
epic: "65"
workflow: "tdd"
---
# Story 65-13: Cast-section docstring & Chrome guard gaps — follow-up from 65-9 review

## Story Details
- **ID:** 65-13
- **Jira Key:** (not configured for this project; YAML-tracked only)
- **Workflow:** tdd
- **Stack Parent:** none
- **Epic:** 65 — Content Infrastructure — R2 asset tracking and audit
- **Triggered By:** 65-9 review findings (Delivery Findings + Design Deviations)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-03T20:38:36Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-03T00:00:00Z | 2026-06-03T20:07:29Z | 20h 7m |
| red | 2026-06-03T20:07:29Z | 2026-06-03T20:20:10Z | 12m 41s |
| green | 2026-06-03T20:20:10Z | 2026-06-03T20:25:50Z | 5m 40s |
| spec-check | 2026-06-03T20:25:50Z | 2026-06-03T20:27:13Z | 1m 23s |
| verify | 2026-06-03T20:27:13Z | 2026-06-03T20:32:15Z | 5m 2s |
| review | 2026-06-03T20:32:15Z | 2026-06-03T20:37:22Z | 5m 7s |
| spec-reconcile | 2026-06-03T20:37:22Z | 2026-06-03T20:38:36Z | 1m 14s |
| finish | 2026-06-03T20:38:36Z | - | - |

## Story Context

**Epic:** 65 — Content Infrastructure — R2 asset tracking and audit

This is a follow-up story capturing **10 non-blocking findings** from the 65-9 review (Delivery Findings + Design Deviations) that warrant cleanup and clarification in the Cast-section and Chrome-guard infrastructure.

### Source Context

65-9 delivered the Cast section (public NPC projection with manifest-gated portraits), reusing 65-8's POI gate machinery. During dev → architect → reviewer phases, the following gaps emerged:

1. **Misleading OTEL span semantics** (Reviewer finding #4)
   - `_cast_portrait_img_html` reuses `scrapbook.npc_portrait_{resolved,not_found}` spans
   - These spans are documented (scrapbook.py:133,152) for scene-time scrapbook-ref attachment
   - On the reference page, no scrapbook ref exists, so the panel description misleads
   - Span still fires with correct attrs (engagement IS detectable); only prose misleads
   - Clean fix: AC8's deferred `reference_cast_image_not_in_manifest` span (or docstring note)

2. **Lying docstring: `load_cast_entries` mirrors genre loader** (Reviewer finding #5)
   - Claims "mirrors the genre loader … non-dict items are dropped"
   - Genre loader's `_load_portrait_manifest` does NOT drop non-dicts; it `model_validate`s and would raise
   - Shared two-shape tolerance is real; non-dict-drop is local to Cast function

3. **Incomplete span assertions in `test_cast_portrait_decisions_emit_spans`** (Reviewer finding #6)
   - No complement assertions (e.g., absent-slug ∉ resolved, present-slug ∉ not_found)
   - Currently gate suppression is proven only by the sibling text-only test
   - Also: missing `match=r"missing 'key'"` on loud-fail pytest.raises; missing cache-clear isolation; 500 test not manifest-specific

4. **Test fixture params untyped** (Reviewer finding #8)
   - `gated_client` and `otel_capture` at test_reference_cast_manifest_gate.py:200,225 lack type hints
   - Pre-existing pattern in POI suite; lang-review #3 violation

5. **Undefined CSS classes on Cast section** (Architect + Reviewer finding #9, carried forward)
   - `ref-card__portrait` undefined (inline-styled, consistent with pre-existing `ref-card__poi`)
   - Chrome-wiring fixture renders `coyote_star` (no Cast/POI manifest) → classes never validated
   - Both image classes remain unguarded against future CSS drift
   - Pre-existing blind spot 65-9 inherits

6. **Latent edge: non-list `characters:` in `portrait_manifest.yaml`** (Reviewer devil's advocate)
   - `characters: 42` raises uncaught `TypeError` → unhandled (still loud) 500
   - First-party authoring error; loud either way
   - Should guard with `isinstance(chars, list)` in `load_cast_entries`

7. **No test for absent `portrait_manifest.yaml` graceful path** (Reviewer finding #7)
   - `load_cast_entries` returns `[]` on missing file (feature-less worlds)
   - No test covers this graceful codepath; coverage incomplete

8. **Two `reference_manifest_loaded` spans per both-features render** (Dev + Architect deviation)
   - Spec assumed one-span-per-render; actual behavior is one-per-gated-feature
   - A world with both POIs and Cast NPCs emits TWO manifest_loaded spans
   - File read once (lru_cache), but span fires per gate
   - Clean resolution: unify load (one span, keys to both gates) — deferred to follow-up

9. **TEA-imposed Cast card marker: `id="cast-{slug}`** (TEA deviation)
   - Not explicitly in spec; pinned to assert per-NPC image-vs-text behavior
   - Mirrors established `id="location-{slug}"` POI convention
   - Accepted; forward-noted in 65-13

10. **AC5/AC7 docstring accuracy requires independent verification** (TEA deviation)
    - AC5: three docstrings fixed (raw-key/`resolve_asset_url` boundary, `lru_cache` precision, span-when-feature-present)
    - AC7: cache-staleness runbook note on `load_r2_manifest_keys`
    - No failing tests (docstring prose not behaviorally assertable)
    - Reviewer confirmed accuracy at code-review time; they land correctly

### Acceptance Criteria

1. **Dual-use docstring or dedicated reference span for Cast portrait observability** — either (a) add a docstring note to `scrapbook.py` explaining the dual-use (`scene-time scrapbook refs` + `reference-page image gates`), OR (b) implement AC8's deferred `reference_cast_image_not_in_manifest` span and migrate `test_cast_portrait_decisions_emit_spans` to use it. Route (b) is cleaner and also resolves finding #1. Recommendation: implement AC8 (reference span).

2. **Fix `load_cast_entries` docstring: "mirrors" claim** — rewrite reference_renderer.py:1218 to accurately state the shared two-shape tolerance and note that non-dict-drop is local to this function, unlike the genre loader.

3. **Strengthen span test with complement assertions** — add `_ABSENT_SLUG not in resolved` and `_PRESENT_SLUG not in not_found` assertions to `test_cast_portrait_decisions_emit_spans`; add `match=r"missing 'key'"` regex to the loud-fail `pytest.raises`; add a `load_r2_manifest_keys.cache_clear()` isolation guard; add a 500-test body assertion that confirms manifest-specific (not a catch-all 500).

4. **Add test for absent `portrait_manifest.yaml` graceful path** — write `test_cast_absent_manifest_renders_empty_section` covering the `[]` return on missing file (feature-less world).

5. **Annotate test fixture params** — add type hints to `gated_client: TestClient` and `otel_capture` fixture params at test_reference_cast_manifest_gate.py:200,225 (mirror POI suite pattern).

6. **Guard non-list `characters:` in `load_cast_entries`** — add `isinstance(chars, list)` check after `chars = data.get("characters", [])` to raise `ValueError` on malformed authoring, enabling clean logged 500 instead of unhandled `TypeError`.

7. **Extend chrome-wiring fixture to render a Cast+POI world** — update `_seed_space_opera_world` in test_reference_chrome_wiring.py to author both `portrait_manifest.yaml` (with at least one NPC) and a POI (via `history.yaml` or `poi_locations.yaml`), so the image classes (`ref-card__poi`, `ref-card__portrait`) pass through the contract guard and validate against the CSS bundle or allowlist.

8. **Allowlist the Cast+POI inline-styled image classes** — add `ref-card__portrait` (and review `ref-card__poi`) to `SEMANTIC_ALLOWLIST` in reference_renderer.py with a justification comment (e.g., "inline-styled decorative image containers, not CSS-bundled"), or confirm both already pass the contract if the fixture extends to emit them.

9. **Unify the two-gate manifest load (optional, deferred)** — refactor `assemble_lore_page` to load `r2_manifest_keys` once, emit one `reference_manifest_loaded` span, and pass the keys to both `_gate_poi_slugs_on_manifest` and `_gate_cast_slugs_on_manifest`. Deferred to a future optimization unless a GM-panel metric demands it. (Low priority; test coverage is sufficient with the current per-gate span model.)

10. **Accept and forward the TEA Cast card marker (`id="cast-{slug}"`) convention** — confirm this convention is stable and document it as the expected contract for future reference-section renders (if a third section joins the pattern). No code change required; forward-note in architecture docs or JARGONFILE as part of the lore-page markup contract.

### Technical Approach

- **Scope:** server-only; all changes in `sidequest-server/` and its test suites
- **Baseline:** feature branch off `sidequest-server/develop` (65-9 has already landed)
- **TDD workflow:** RED → GREEN → VERIFY → REVIEW → FINISH
- **OTEL principle:** every change that touches a subsystem must preserve/improve observability (especially AC1's span choice and AC3's test rigor)
- **CLAUDE.md principles:** No Silent Fallbacks (AC6 guards non-list), Verify Wiring (fixture extension AC7), Every Test Needs a Wiring Test (chromeguard fixture + live route)

## Sm Assessment

Story 65-13 is a 3-pt, server-only TDD follow-up bundling 10 non-blocking findings
from the 65-9 review (Reviewer APPROVED). Scope is well-bounded and fully traced:
all findings + audit trail archived in `sprint/archive/65-9-session.md`, and the
story context captures them as ACs. The surface is the reference-page Cast section.

Routing: phased `tdd` workflow → TEA (The Architect) owns the RED phase. The
testable findings cluster into clear failing-test targets — AC8 `reference_portrait_*`
spans (replacing the misleading reused `scrapbook.npc_portrait_*` spans), span-test
complement assertions, the non-list `characters:` manifest edge (clean 500 vs
uncaught TypeError), the absent-`portrait_manifest.yaml` graceful `[]` path, and the
`ref-card__portrait` chrome-contract guard. Docstring-accuracy findings
(`load_cast_entries`, AC5/AC7) are verification-only, not behaviorally testable —
TEA should flag those for Dev to land as docstring edits without a corresponding test.

No blockers. Jira not configured (skipped per protocol). Branch + session verified.
Handing off to TEA for RED.

## TEA Assessment

**Tests Required:** Yes
**Reason:** n/a

**Test Files:**
- `tests/server/test_reference_cast_manifest_gate.py` — AC8 reference portrait spans,
  span-test complement rigor, scrapbook-span non-emission, span registration wiring,
  EDGE non-list-`characters` guard, graceful no-manifest coverage, manifest-specific
  500, RULE #3 fixture type hints, missing-key `match=` + `cache_clear()` isolation.
- `tests/server/test_reference_chrome_wiring.py` — CHROME contract: a content-root
  fixture that actually emits `ref-card__poi` + `ref-card__portrait`, asserted against
  the class-vs-CSS / allowlist contract.

**Tests Written/Modified:** 6 new + 5 strengthened, across the 8 ACs (1 optional AC
and 2 DOC-only ACs intentionally untested — see Design Deviations).
**Status:** RED — **5 failed, 12 passed** (`uv run pytest -n0` on the two files).

### Rule Coverage

| Rule / AC | Test(s) | Status |
|-----------|---------|--------|
| AC8 reference_portrait spans | `test_cast_portrait_decisions_emit_spans` | failing (RED) |
| DOC span-semantics (no scrapbook reuse) | `test_cast_render_does_not_emit_scene_scrapbook_spans` | failing (RED) |
| Span wiring (FLAT_ONLY_SPANS) | `test_reference_portrait_spans_are_registered` | failing (RED) |
| EDGE non-list `characters:` | `test_load_cast_entries_non_list_characters_raises_loudly` | failing (RED) |
| CHROME class-vs-CSS contract | `test_cast_and_poi_image_classes_pass_chrome_contract` | failing (RED) |
| TEST complement assertions | (in `test_cast_portrait_decisions_emit_spans`) | failing (RED) |
| TEST missing-key `match=` + cache_clear | `test_load_manifest_entry_missing_key_raises_loudly` | passing (hardening of correct behavior) |
| TEST manifest-specific 500 | `test_absent_manifest_on_cast_world_returns_500` | passing (control added) |
| TEST graceful no-manifest path | `test_load_cast_entries_returns_empty_when_manifest_absent`, `test_world_without_cast_renders_no_cast_section` | passing (coverage close) |
| RULE #3 typed fixture params | `gated_client: TestClient`, `otel_capture: InMemorySpanExporter` annotations applied | n/a (lint-style, applied) |

**Rules checked:** No `.pennyfarthing/gates/lang-review/python.md` checklist is present in
this checkout; applied the server CLAUDE.md rules instead — notably "No Source-Text
Wiring Tests" (the span/registration tests assert behavior + the registry, never grep
source) and "Every Test Suite Needs a Wiring Test" (`test_reference_portrait_spans_are_registered`
proves the new spans are routed, not merely defined).
**Self-check:** 0 vacuous tests — every assertion checks a value or a non-empty/empty
span set; the chrome test guards against vacuity by first asserting both image classes
are actually emitted before applying the contract.

**Note for Dev (DOC-only, no test):** Fix the `load_cast_entries` docstring
(`reference_renderer.py:1218`) — the genre loader's `_load_portrait_manifest` does NOT
drop non-dicts (it `model_validate`s and would raise); only the two-shape tolerance is
shared, and non-dict-drop is local to this function. AC5/AC7 docstrings land as prose
edits verified at review time.

**Handoff:** To Dev (Agent Smith) for implementation (GREEN).

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest/telemetry/spans/reference.py` — added `SPAN_REFERENCE_PORTRAIT_{RESOLVED,NOT_FOUND}`
  constants + `FLAT_ONLY_SPANS` registration + `reference_portrait_{resolved,not_found}_span`
  contextmanagers (carry `slug`/`reference.pack`/`reference.world`), mirroring the 65-11
  map-pin spans. (AC8 + wiring)
- `sidequest/server/reference_presenters.py` — `_cast_portrait_img_html` now opens the new
  reference portrait spans instead of `scrapbook.npc_portrait_*`; dropped the now-unused
  scrapbook import. (AC8 / DOC span-semantics migration)
- `sidequest/server/reference_renderer.py` — `load_cast_entries` raises `ValueError` on a
  non-list `characters:` value (was an uncaught `TypeError`); corrected the misleading
  "mirrors the genre loader / non-dict items are dropped" docstring. (EDGE + DOC)
- `tests/server/test_reference_chrome_wiring.py` — added `ref-card__poi` + `ref-card__portrait`
  to `SEMANTIC_ALLOWLIST` with justification (inline-styled images, not bundle-styled);
  allowlist now exactly 5 (cap). (CHROME)
- `tests/server/test_reference_cast_manifest_gate.py` — ruff format only (line-wrap of the
  span-set comprehensions).

**Tests:** 17/17 story tests passing (GREEN). Regression sweep: 556 reference/scrapbook/
portrait tests pass, 0 failures, no regressions. `ruff check` clean, `ruff format` applied,
`pyright` 0 errors on changed source.

**Branch:** `feat/65-13-cast-docstring-span-chrome-guard` (pushed)

**Note on DOC-only ACs:** `load_cast_entries` "mirrors" docstring fixed. AC5/AC7 docstrings
were 65-9 deliverables already verified at that story's review — no change needed here.

**Handoff:** To Reviewer (The Merovingian) for code review.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None requiring action (3 pre-logged minor deviations confirmed correct)

AC-by-AC verification against `context-story-65-13.md`:

| AC | Spec | Implementation | Verdict |
|----|------|----------------|---------|
| DOC span-semantics | note dual-use OR implement AC8 (route b recommended) | route b: scrapbook reuse removed, presenter migrated to reference spans | Aligned |
| AC8 reference_portrait spans | dedicated `reference_portrait_{resolved,not_found}`, migrate test | spans added (mirror 65-11 map-pin pattern), registered in FLAT_ONLY_SPANS, presenter + test migrated | Aligned |
| DOC `load_cast_entries` docstring | correct the "mirrors genre loader / drops non-dicts" claim | docstring rewritten — two-shape tolerance shared, non-dict-drop local | Aligned |
| TEST rigor | complement asserts, `match=`, cache_clear, manifest-specific 500, graceful no-manifest | all present; 500 test adds control-200; graceful path unit + route tests | Aligned |
| RULE #3 typed fixtures | annotate `gated_client`/`otel_capture` | `: TestClient` / `: InMemorySpanExporter` applied | Aligned |
| EDGE non-list `characters:` | `isinstance(chars, list)` → ValueError | guard added, raises ValueError (was TypeError) | Aligned |
| CHROME | resolve `ref-card__portrait` + fixture validates both image classes | allowlisted both image classes (cap=5, exactly 5) + dedicated content-root contract test | Aligned (see deviation) |
| REFACTOR (optional) | one manifest_loaded span per both-features render | not done — optional | Deferred (see deviation) |

**On the three logged deviations** (all minor, all sound):
- **CHROME — new dedicated test vs editing `_seed_space_opera_world`** (Option A — Update spec):
  TEA's rationale is architecturally correct. `_seed_space_opera_world` puts the pack at
  `tmp_path/space_opera`, so the gate's `pack_dir.parent.parent` manifest discovery would
  resolve *outside* `tmp_path` — authoring a gated-image fixture there is not cleanly
  possible without restructuring three call sites and coupling the keystone test to an
  r2_manifest. The dedicated `_seed_cast_and_poi_content_root` test validates the identical
  contract (`_extract_emitted_classes` + `_served_css_text` + `SEMANTIC_ALLOWLIST`) and
  closes the same blind spot with zero blast radius. The AC's *intent* (image classes are
  validated) is fully met; the literal fixture-name target is the right thing to relax.
- **REFACTOR optional not done** (Option D — Defer): correct; the per-gate `manifest_loaded`
  span model is honest (one span per feature gate that actually fires), and the AC marks it
  optional. No GM-panel metric demands the unification today.
- **DOC-only ACs carry no test** (Option C — Clarify): correct per the server CLAUDE.md
  "No Source-Text Wiring Tests" rule; docstring accuracy is a Reviewer eyeball check.

**AC8 semantic distinction check:** AC8 asks to distinguish "authored but not on R2" from
"not authored." The implementation achieves this at the span-namespace level —
`sidequest.reference.portrait_not_found` now exclusively means *authored-but-not-on-R2*
(every Cast NPC is authored from the manifest), while `scrapbook.npc_portrait_not_found`
remains exclusively the scene-time *not-authored* (ad-hoc NPC) signal. The two facts are
now separable by span name. Correct.

**Decision:** Proceed to review (TEA verify next).

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (573 passed, 0 failed, 3 skipped across the reference/scrapbook/portrait suites; the two story files 17/17)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 5 (3 source, 2 test)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 4 findings | 2 high (unify POI/Cast gate helpers; unify POI/Cast image-html), 1 medium (unify image-key builders), 1 low (load_cast_entries filter helper) |
| simplify-quality | 1 finding | 1 high (`_portrait_attrs` return type → `dict[str, Any]`) |
| simplify-efficiency | clean | the POI/Cast/Map parallel structure is intentional pattern-mirroring, not over-engineering |

**Applied:** 1 high-confidence fix
- simplify-quality: widened `_portrait_attrs` return type to `dict[str, Any]` to match the
  sibling `_poi_attrs` (commit `refactor: simplify code per verify review`). No runtime change;
  ruff + pyright clean; 573 tests green.

**Flagged for Review (not applied):** the 3 reuse DRY findings (2 high, 1 medium)
- **Deliberately deferred, not skipped.** Each unification (`_gate_poi/cast_slugs_on_manifest`,
  `_poi_image_html`/`_cast_portrait_img_html`, `poi_image_key`/`portrait_image_key`) would
  modify **pre-existing, out-of-story-scope** code (the 63-8/65-8 POI path and the 65-11 Map
  path that also calls `_gate_cast_slugs_on_manifest`), and directly overlaps the **optional
  REFACTOR AC that TEA logged and Architect ratified as deferred**. simplify-efficiency
  independently judged the parallel structure intentional. Auto-applying a three-call-site
  refactor during a cleanup follow-up — against an explicit deferral decision — is the wrong
  trade. Recommend a dedicated future "unify reference manifest gates + gated-image html"
  story if a third gate variant ever lands.
- **Noted (low):** a generic list-of-dicts filter helper for `load_cast_entries` — not worth
  it for one call site.

**Reverted:** 0

**Overall:** simplify: applied 1 fix (3 high/medium DRY findings deferred as out-of-scope per the ratified optional-REFACTOR deferral)

**Quality Checks:** ruff check clean, ruff format clean, pyright 0 errors, full reference/scrapbook/portrait suite green.
**Handoff:** To Reviewer (The Merovingian) for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 smells, 17 tests green, lint clean | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | Yes | findings | 1 (medium, CWE-209 path leak) | confirmed 1 (non-blocking), dismissed 0, deferred 1 (fix point) |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings |

**All received:** Yes (2 enabled subagents returned; 7 disabled via `workflow.reviewer_subagents`)
**Total findings:** 1 confirmed (medium, non-blocking), 0 dismissed, 1 deferred (fix belongs at the route handler / module-wide)

### Rule Compliance

Project rules applied (no `.pennyfarthing/gates/lang-review/python.md` present; sourced from CLAUDE.md / SOUL.md / server CLAUDE.md):

| Rule | Instances in diff | Verdict |
|------|-------------------|---------|
| No Silent Fallbacks | `load_cast_entries` non-list guard (reference_renderer.py:1240) raises `ValueError` → route 500 | Compliant — loud, caught at reference_routes.py:125 |
| OTEL: every subsystem decision emits a span | `reference_portrait_{resolved,not_found}_span` both branches of `_cast_portrait_img_html`; registered in FLAT_ONLY_SPANS (reference.py:111-112) | Compliant — wiring test enforces registration |
| Reference page is public (ADR-135); never read keeper-only `npcs.yaml` | `load_cast_entries` reads only `portrait_manifest.yaml` | Compliant — diff adds no new reads; docstring reaffirms |
| All HTML interpolation escaped (XSS) | `<img>` src/alt/accent — `escape()` on all three (reference_presenters.py, unchanged by diff) | Compliant — escaping untouched by the span migration |
| No Source-Text Wiring Tests | new span wiring test asserts `FLAT_ONLY_SPANS` membership, not source grep | Compliant |
| Every Test Suite Needs a Wiring Test | `test_reference_portrait_spans_are_registered` proves routing, not just definition | Compliant |

### Devil's Advocate

I tried to break this. Attack surface and stress paths considered:

- **Malformed authoring inputs to `load_cast_entries`:** `characters: 42` → new `isinstance(chars, list)` guard raises `ValueError` (was an uncaught `TypeError`). `characters: "a string"` → a string is iterable but `isinstance(str, list)` is False → guard catches it, preventing the per-character mis-parse the test docstring warned about. `characters: []` → returns `[]`. Empty file → `yaml.safe_load` returns `None` → `else: chars=[]` → `[]`. A bare top-level list with a scalar element (`[42, {...}]`) → passes the list guard, then `[c for c in chars if isinstance(c, dict)]` drops the scalar — correct and intentional. No unhandled path remains.
- **Info disclosure:** the security subagent's real catch — the new `ValueError` embeds the absolute `{path}`, forwarded to the 500 body via `detail=str(exc)`. Confirmed genuine, but it is the established module convention (`load_r2_manifest_keys` ValueErrors at lines 1160/1167 and the absent-manifest `FileNotFoundError` all leak the same way through the same handler, approved at 65-9), the full path is already logged server-side via `_LOG.exception`, and severity is Medium (non-blocking). Fixing only my new line would leave the more-common absent-manifest leak open and make my message inconsistent with its siblings — so the correct fix is module-wide at `detail=str(exc)` (deferred, see Delivery Findings).
- **Span leakage:** span attrs are `slug`/`pack`/`world` — `slug` derives from a public NPC name on a *public* page; pack/world are already in the URL. No keeper content, no secrets.
- **Chrome test false-pass:** the new contract test could be vacuous if the fixture stopped emitting the image classes — but it guards both `ref-card__poi` and `ref-card__portrait` presence *before* the contract assertion, so a broken gate fails loudly on the guard.
- **Allowlist growth:** adding 2 entries brings `SEMANTIC_ALLOWLIST` to exactly 5 — `test_semantic_allowlist_stays_small` (cap 5) still passes, but the cap is now saturated; a future image class would force a real decision (CSS rule vs allowlist). Acceptable and intentional.

No Critical or High issue surfaced. The one real finding is Medium/non-blocking and pre-existing in pattern.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** `portrait_manifest.yaml` → `load_cast_entries` (now guarded against non-list `characters:`) → `present_lore_cast` → `_cast_portrait_img_html` → gated `<img>` (escaped) + `reference_portrait_{resolved,not_found}` span (registered in FLAT_ONLY_SPANS). Malformed authoring fails loud (ValueError → 500, logged server-side). Public projection only — `npcs.yaml` never read.

**Pattern observed:** new spans mirror the 65-11 map-pin reference-namespaced span pattern exactly (reference.py:529-573) — correct reuse, not reinvention. Migration off the scene-time scrapbook family is complete (no scrapbook import remains; `test_cast_render_does_not_emit_scene_scrapbook_spans` enforces it).

**Error handling:** `load_cast_entries` non-list guard (reference_renderer.py:1240-1244) → `ValueError`, caught at reference_routes.py:125 → clean 500, full path logged via `_LOG.exception` at line 129.

| Severity | Issue | Location | Disposition |
|----------|-------|----------|-------------|
| [MEDIUM][SEC] | CWE-209: ValueError detail embeds absolute filesystem path, forwarded to 500 body via `detail=str(exc)` | reference_renderer.py:1243 → reference_routes.py:130 | Non-blocking; pre-existing module convention (siblings at :1160/:1167 + absent-manifest FileNotFoundError leak identically). Deferred — see Delivery Findings (fix at the route handler, module-wide). |

**Handoff:** To SM (Morpheus) for finish-story.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Improvement** (non-blocking): The 65-11 Map section already established the exact
  dedicated-reference-span pattern AC8 wants — `sidequest.reference.map_pin_{resolved,not_found}`
  ("dedicated reference-namespaced spans rather than the scene-time scrapbook family",
  per `reference.py:64-72`). Dev should mirror that pattern verbatim for the new
  `sidequest.reference.portrait_{resolved,not_found}` spans. Affects
  `sidequest/telemetry/spans/reference.py` (add constants, FLAT_ONLY_SPANS entry, two
  contextmanagers) + `sidequest/server/reference_presenters.py:_cast_portrait_img_html`
  (swap the scrapbook imports for the new spans). *Found by TEA during test design.*
- **Improvement** (non-blocking): `_cast_portrait_img_html` keeps a `theme` param only to
  read `theme.palette_accent` for the inline `<img>` style. Since the chrome AC resolves
  `ref-card__portrait` as an inline-styled image, this is fine — but note the cast/POI
  `<img>` styling lives inline in the presenter, not the CSS bundle. If a future story
  moves these to real CSS rules, remove the allowlist entries Dev adds in this story.
  Affects `reference_presenters.py` + `tests/server/test_reference_chrome_wiring.py`
  (SEMANTIC_ALLOWLIST). *Found by TEA during test design.*
- **Gap** (non-blocking): SM-setup did not create `sprint/context/context-story-65-13.md`
  (the `sm_setup_exit` gate was satisfied by the session-embedded `## Story Context`, but
  TEA's `pf validate context-story` requires the standalone file). Recovered via the
  sanctioned `pf context create story 65-13`. Affects the sm-setup→TEA gate seam. *Found
  by TEA during test design.*
- **Improvement** (non-blocking): three reuse/DRY opportunities exist between the parallel
  POI, Cast, and Map manifest-gate code paths — `_gate_poi_slugs_on_manifest` ≈
  `_gate_cast_slugs_on_manifest`, `_poi_image_html` ≈ `_cast_portrait_img_html`, and
  `poi_image_key` ≈ `portrait_image_key`. Deferred from this story (out of scope; overlaps
  the ratified optional-REFACTOR deferral; would touch the 65-11 Map call site). Worth a
  dedicated "unify reference manifest gates" story if a third gate variant lands. Affects
  `sidequest/server/reference_renderer.py` + `sidequest/server/reference_presenters.py`.
  *Found by TEA during test verification.*

### Reviewer (code review)
- **Improvement** (non-blocking): CWE-209 information disclosure — every loud-fail `ValueError`
  / `FileNotFoundError` in `reference_renderer.py` (lines 629, 1113, 1160, 1167, 1233, the new
  1243, plus the absent-manifest `FileNotFoundError`) embeds an **absolute server filesystem
  path** that the lore/rules route returns verbatim to clients via
  `raise HTTPException(status_code=500, detail=str(exc))` (`reference_routes.py:116,130`). The
  full path is already logged server-side via `_LOG.exception`, so the fix is to sanitize the
  client-facing `detail` (e.g. a generic message + pack/world identifiers only) at the two
  route catch-blocks — one change closes all reference-module path leaks at once. Out of scope
  for 65-13 (this story's new ValueError merely follows the established convention); recommend a
  dedicated follow-up. Affects `sidequest/server/reference_routes.py` (`detail=str(exc)` → sanitized).
  *Found by Reviewer during code review.*

### Dev (implementation)
- **Improvement** (non-blocking): The `scrapbook.npc_portrait_{resolved,not_found}` spans
  are now used ONLY by the scene-time path (65-6 emitters) after this story removed their
  reference-page reuse. Their docstrings (`scrapbook.py:133,152`) are accurate-by-default
  again (no dual-use), so no docstring note was needed there — the misleading-semantics
  finding is resolved by *migration*, not annotation. Affects
  `sidequest/telemetry/spans/scrapbook.py` (no change required; noted for the record).
  *Found by Dev during implementation.*
- No other upstream findings during implementation.

## Impact Summary

**Upstream Effects:** No upstream effects noted
**Blocking:** None

### Deviation Justifications

3 deviations

- **Optional REFACTOR AC intentionally not tested**
  - Rationale: The AC is explicitly marked optional, and the current per-gate span
  - Severity: minor
  - Forward impact: If a future story makes the unification mandatory, add a both-features
- **CHROME AC: new dedicated test instead of literally editing `_seed_space_opera_world`**
  - Rationale: `_seed_space_opera_world` places its pack at `tmp_path/space_opera`, so the
  - Severity: minor
  - Forward impact: none — the contract coverage is equivalent.
- **DOC-only ACs (load_cast_entries "mirrors" docstring; AC5/AC7 docstrings) carry no test**
  - Rationale: Docstring accuracy is not behaviorally assertable (a source-text grep
  - Severity: minor
  - Forward impact: Reviewer must eyeball the docstring at code-review time (as 65-9 did).

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Optional REFACTOR AC intentionally not tested**
  - Spec source: context-story-65-13.md, "REFACTOR (optional)" AC
  - Spec text: "unify the POI + Cast manifest gates so a both-features world emits one
    reference_manifest_loaded span per render (load once, pass keys to both gates)
    instead of one-per-gate."
  - Implementation: No RED test written for the one-span-per-both-features behavior.
  - Rationale: The AC is explicitly marked optional, and the current per-gate span
    model is honest (one `reference_manifest_loaded` span per feature gate that actually
    fires — observable, not misleading). Writing a RED test would *compel* the optional
    refactor (RED tests must go green), contradicting "optional". Dev may still do it; if
    so, the existing `test_cast_render_fires_manifest_loaded_span_with_exact_count`
    (cast-only world, asserts exactly 1 span) already guards the single-feature count.
  - Severity: minor
  - Forward impact: If a future story makes the unification mandatory, add a both-features
    fixture asserting exactly one `manifest_loaded` span.
- **CHROME AC: new dedicated test instead of literally editing `_seed_space_opera_world`**
  - Spec source: context-story-65-13.md, CHROME AC
  - Spec text: "extend the chrome-wiring fixture (test_reference_chrome_wiring.py:
    _seed_space_opera_world) to render a cast+POI-bearing world so the lore-page image
    classes (ref-card__poi, ref-card__portrait) are actually validated."
  - Implementation: Added a new `_seed_cast_and_poi_content_root` fixture +
    `test_cast_and_poi_image_classes_pass_chrome_contract` that applies the SAME chrome
    contract (`_extract_emitted_classes` + `_served_css_text` + `SEMANTIC_ALLOWLIST`),
    rather than mutating the shared `_seed_space_opera_world`.
  - Rationale: `_seed_space_opera_world` places its pack at `tmp_path/space_opera`, so the
    gate's `pack_dir.parent.parent / "r2_manifest.json"` discovery resolves to
    `tmp_path.parent` — *outside* the test's tmp dir — making a gated-image fixture
    impossible to author cleanly without restructuring the shared fixture and its three
    call sites (risking the keystone test). The dedicated content-root-structured fixture
    closes the same blind spot (both image classes emitted and contract-validated) with
    no blast radius. Dev may fold it into the shared fixture later if desired.
  - Severity: minor
  - Forward impact: none — the contract coverage is equivalent.
- **DOC-only ACs (load_cast_entries "mirrors" docstring; AC5/AC7 docstrings) carry no test**
  - Spec source: context-story-65-13.md, DOC AC (reference_renderer.py:1218) + SM Assessment
  - Spec text: "Fix the lying load_cast_entries docstring … the genre loader's
    _load_portrait_manifest does NOT drop non-dicts."
  - Implementation: No test. Flagged for Dev as a prose-only edit.
  - Rationale: Docstring accuracy is not behaviorally assertable (a source-text grep
    assertion is forbidden by the server CLAUDE.md "No Source-Text Wiring Tests" rule).
  - Severity: minor
  - Forward impact: Reviewer must eyeball the docstring at code-review time (as 65-9 did).

### Dev (implementation)
- No deviations from spec. Implemented all 5 RED-test ACs exactly as TEA pinned them
  (new `sidequest.reference.portrait_*` spans mirroring the 65-11 map-pin pattern,
  presenter migration off the scrapbook family, `load_cast_entries` non-list guard,
  chrome allowlist entries) plus the DOC-only `load_cast_entries` docstring fix
  (corrected the "mirrors the genre loader / non-dict items are dropped" claim per the
  DOC AC). Took TEA's CHROME-AC deviation as-is — the new dedicated test is the contract
  guard; did not restructure the shared `_seed_space_opera_world`. Did NOT do the
  optional one-span-per-both-features REFACTOR AC (TEA intentionally left it untested;
  the per-gate span model is honest as-is).

### Reviewer (audit)
- **TEA: Optional REFACTOR AC not tested** → ✓ ACCEPTED by Reviewer: forcing an optional AC
  green via a RED test would be wrong; the per-gate `manifest_loaded` span model is honest and
  observable. Agrees with author reasoning.
- **TEA: CHROME new dedicated test vs editing `_seed_space_opera_world`** → ✓ ACCEPTED by
  Reviewer: the shared fixture's pack-at-tmp-root layout makes `pack_dir.parent.parent`
  manifest discovery land outside `tmp_path`; the new content-root test validates the identical
  contract (`_extract_emitted_classes` + `_served_css_text` + `SEMANTIC_ALLOWLIST`) with no
  blast radius. AC intent (image classes validated) fully met.
- **TEA: DOC-only ACs carry no test** → ✓ ACCEPTED by Reviewer: docstring accuracy is not
  behaviorally assertable (server CLAUDE.md "No Source-Text Wiring Tests"); verified by eyeball
  — the `load_cast_entries` docstring now correctly states the two-shape tolerance is the only
  shared behavior and the non-dict-drop is local. Accurate.
- **Dev: No deviations from spec** → ✓ ACCEPTED by Reviewer: implementation matches the pinned
  tests and the spec; the DOC docstring fix is correct.
- No undocumented deviations found. The diff matches the logged deviation set exactly.

### Architect (reconcile)

**Deviation manifest — definitive audit for Story 65-13.**

Reviewed all in-flight deviation entries (TEA × 3, Dev × 1) and the Reviewer audit against the
story context (`context-story-65-13.md`), epic context (`context-epic-65.md`), the source
trail (`sprint/archive/65-9-session.md`), and the committed diff. Verification result:

- **TEA — Optional REFACTOR AC not tested.** Accurate. Spec text quoted correctly ("unify the
  POI + Cast manifest gates so a both-features world emits one reference_manifest_loaded span
  per render"). The AC is marked optional in the context; the per-gate span model is honest.
  Resolution: **Defer (D)** — no GM-panel metric demands the unification. Forward impact: a
  future "unify reference manifest gates" story (see Delivery Findings) would address it; the
  three parallel gate/image/key helper pairs TEA flagged are the natural scope. All 6 fields
  present and substantive.
- **TEA — CHROME new dedicated test vs editing `_seed_space_opera_world`.** Accurate. The
  `pack_dir.parent.parent` manifest-discovery constraint is real and correctly diagnosed.
  Resolution: **Update spec (A)** — the literal fixture-name target relaxes; AC *intent* (the
  `ref-card__poi`/`ref-card__portrait` classes are validated against the chrome contract) is
  fully met by `test_cast_and_poi_image_classes_pass_chrome_contract`. All 6 fields present.
- **TEA — DOC-only ACs carry no test.** Accurate. Verified the `load_cast_entries` docstring at
  `reference_renderer.py:1217-1224` now correctly states the two-shape tolerance is the *only*
  shared behavior and the non-dict-drop is local (contrasted with the genre loader's
  `model_validate`). Resolution: **Clarify (C)** — prose-only, Reviewer-eyeballed. Compliant
  with the "No Source-Text Wiring Tests" rule. All 6 fields present.
- **Dev — No deviations from spec.** Accurate. The implementation matches the pinned tests;
  the only added scope is the DOC docstring fix, which is itself an AC.

**AC accountability:** 8 of 8 ACs addressed (7 implemented + tested; 1 — optional REFACTOR —
explicitly deferred with rationale above). No AC was silently dropped. No deferred AC was
inadvertently addressed or invalidated during review.

**Reviewer CWE-209 finding (not a 65-13 spec deviation):** the absolute-path-in-`detail`
information disclosure the Reviewer confirmed is a **pre-existing module-wide convention**
(`reference_renderer.py` ValueErrors at lines 629/1113/1160/1167/1233 + the absent-manifest
`FileNotFoundError`, all surfaced via `reference_routes.py:116,130 detail=str(exc)`). Story
65-13's new ValueError merely follows that convention, so it is **not a deviation from this
story's spec** — it is captured as a non-blocking Delivery Finding recommending a dedicated
follow-up to sanitize the route handler (the single fix point that closes all reference-module
path leaks at once). Logging it here for the audit trail, not as a 65-13 deviation.

- No additional deviations found.