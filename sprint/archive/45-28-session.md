---
story_id: "45-28"
jira_key: null
epic: "45"
workflow: "wire-first"
---
# Story 45-28: Markov namegen min-pool guard + thin-corpus audit

## Story Details
- **ID:** 45-28
- **Epic:** 45 (Playtest 3 Closeout — MP Correctness, State Hygiene, and Post-Port Cleanup)
- **Workflow:** wire-first
- **Stack Parent:** none
- **Points:** 3
- **Priority:** p2
- **Type:** bug

## Problem Statement

Playtest 3 (2026-04-19) produced "Frandrew Andrew" — a classic too-small-corpus stem-repetition artifact from Markov namegen. The corpus for certain cultures has too few entries, allowing the same morpheme to be selected for both prefix and suffix independently, creating nonsensical names.

## Acceptance Criteria

**AC1: Corpus Size Audit**
- Audit all culture word-list files in `sidequest-content/genre_packs/*/cultures/` to identify which cultures have corpora below a safe threshold.
- Flag cultures with < N entries per morpheme pool in OTEL span with `culture_slug`, `pool_type` (prefix/suffix/stem), and `entry_count` attributes.
- Report findings in session file **Delivery Findings** section before design begins.

**AC2: Min-Pool Guard Implementation**
- Add minimum-pool-size check in namegen before generation attempt.
- When corpus pool falls below N entries, emit OTEL span `namegen.min_pool_guard_triggered` with:
  - `culture_slug`
  - `pool_type` (prefix/suffix/stem)
  - `threshold`
  - `actual_count`
- Log warning to stderr (rule python.md #4: logger.warning for subsystem decisions).
- Return a sentinel value or raise with descriptive error (design decision in red phase with TEA).

**AC3: Corpus Expansion**
- Expand thin-culture corpora for `aureate_span` source cultures to eliminate guard triggers in normal playtest sessions.
- Verify no culture falls below minimum post-expansion.

**AC4: Regression Test**
- Unit test that validates no generated name has identical prefix AND suffix stems (the exact bug signature).
- Test exercises the namegen function from its call site in `sidequest/agents/narrator.py` or `dispatch/` where names are generated.
- OTEL assertions that guard did NOT fire for valid corpora.

**AC5: Boundary Test (Wire-First)**
- TEA writes failing test that exercises namegen from the game-state injection point (e.g., `encountergen` CLI or narrator agent subprocess call).
- Test asserts that generation succeeds for normal corpora and fails/warns for artificial sub-threshold pools.
- Test must be consumer-side, not just a unit test in the namegen module.

## Scope Notes

- **In scope:** corpus audit, min-pool guard, expansion of aureate_span cultures, regression test, OTEL instrumentation.
- **Out of scope:** Markov algorithm improvements, multi-stage fallback strategies, or alternative name generation approaches (those are future stories).
- **No deferrals:** All wiring (guard → OTEL → logger → caller) must land in this story.

## Workflow Tracking

**Workflow:** wire-first
**Phase:** finish (SM)
**Phase Started:** 2026-04-29T17:46:05Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-29T14:23:00Z | 2026-04-29T17:07:02Z | 2h 44m |
| red | 2026-04-29T17:07:02Z | 2026-04-29T17:20:17Z | 13m 15s |
| green | 2026-04-29T17:20:17Z | 2026-04-29T17:40:18Z | 20m 1s |
| review | 2026-04-29T17:40:18Z | 2026-04-29T17:46:05Z | 5m 47s |
| finish | 2026-04-29T17:46:05Z | - | - |

## Delivery Findings

<!-- Append-only. Per agent. Do not edit other agents' subsections. -->

### TEA (test design)

- **Improvement** (non-blocking): Architect-context already locks design decisions the SM Assessment flagged as open.
  Affects `sprint/context/context-story-45-28.md` (no change needed; observation only).
  SM risk #1 ("Threshold N is unknown") is closed by the context's "Two thresholds, not one" section: WARN_BELOW_WORDS=1000, FAIL_BELOW_WORDS=200 with empirical justification. SM risk #2 ("Fail strategy is a design call — architect input required") is closed by the context's explicit "raises `ValueError(f\"Corpus '{name}' has {n} words; minimum is {FAIL_BELOW_WORDS}\")`" prescription. No architect spawn needed; TEA proceeded directly.
  *Found by TEA during test design.*

- **Conflict** (non-blocking): Architect context references `sidequest/telemetry/spans.py:331`, but spans were decomposed into per-domain submodules.
  Affects `sidequest/telemetry/spans/` (Dev should create new `namegen.py` submodule, not append to a flat `spans.py` that no longer exists).
  Tests import from `sidequest.telemetry.spans` (the package facade), so the import path works either way — the finding is purely about Dev's edit-target during green.
  *Found by TEA during test design.*

- **Conflict** (non-blocking): Architect context offers "extend the existing `sidequest/game/thresholds.py`" as an alternative threshold-module location.
  Affects `sidequest/game/thresholds.py` (existing module is for ResourcePool/EdgePool downward-crossing detection — entirely unrelated semantics).
  Tests import from `sidequest.genre.names.thresholds` (the architect's primary recommendation). Dev should create the new module rather than overload the existing one — overloading would force one module to expose two unrelated public APIs.
  *Found by TEA during test design.*

## Design Deviations

<!-- Append-only. Per agent. Do not edit other agents' subsections. -->

### TEA (test design)

- **Stem-collision tests mock `NameGenerator.generate_person` instead of using a collision-prone corpus**
  - Spec source: context-story-45-28.md, AC4 ("Test: feed a corpus that DOES produce stem collisions")
  - Spec text: "feed a corpus that DOES produce stem collisions; assert SPAN_NAMEGEN_STEM_COLLISION fires for the rejected attempts"
  - Implementation: `test_generate_npc_rejects_collision_and_emits_collision_span` and `test_generate_npc_exhausts_collision_loop_and_emits_fail_loud_span` use `monkeypatch.setattr(NameGenerator, "generate_person", ...)` to return a fixed candidate sequence
  - Rationale: A Markov-deterministic-collision corpus is fragile — depends on RNG state, lookback, character distribution, and corpus content. Mocking `generate_person` gives crisp test semantics ("when the generator returns these specific names, the rejection loop must emit these specific spans"). The unit test in `test_namegen_thresholds.py::test_stem_collision_flags_*` covers the predicate's algorithmic correctness; the wiring tests cover the loop integration. Both behaviours are pinned without depending on Markov determinism.
  - Severity: minor
  - Forward impact: none — the rejection loop is the wired behaviour under test; whether `generate_person` produces collisions through Markov sampling or through a fixture is an orthogonal concern.

- **CLI smoke test folded into in-process `generate_npc` call rather than subprocess**
  - Spec source: context-story-45-28.md, "Test files (where new tests should land)"
  - Spec text: "New CLI smoke test in `tests/cli/test_namegen.py` (existing dir may need creation) — runs `python -m sidequest.cli.namegen` against a thin fixture, asserts non-zero exit on FAIL_BELOW_WORDS"
  - Implementation: Coverage of the CLI path is provided by `test_generate_npc_*` calling `namegen_cli.generate_npc(pack, genre_dir, args, rng)` directly. The subprocess-level invocation adds Python's argparse, `__main__` dispatch, and `sys.exit` to the surface — none of which are story-specific behaviour.
  - Rationale: `test_audit_namegen_corpora.py` already drives a subprocess invocation pattern for the audit script; the namegen CLI's exit-on-fail behaviour is implicit in `generate_npc`'s contract (the function raises `ValueError`, the `__main__` wrapper turns it into a non-zero exit). Adding a redundant subprocess test triples the wall-clock cost without exercising new code paths.
  - Severity: minor
  - Forward impact: if a future regression breaks the `__main__` exit-code translation specifically (rather than `generate_npc` itself), this test gap would miss it. Dev or Reviewer can add the subprocess test back if they judge the gap material.

- **Loop budget assertion uses `>= 5` rather than exact match**
  - Spec source: context-story-45-28.md, "Existing reuse points" — references the existing 10-attempt loop in `cli/namegen/namegen.py:589-597`
  - Spec text: implicit; the rejection loop has been 10 attempts historically
  - Implementation: `test_generate_npc_exhausts_collision_loop_and_emits_fail_loud_span` asserts `len(rejection_spans) >= 5` rather than `== 10`
  - Rationale: Pinning the exact loop budget couples the wiring test to a tuning value Dev may legitimately adjust during green. The `>= 5` floor catches "loop reduced to 1 attempt" regressions while leaving room for "8 is enough" tuning.
  - Severity: minor
  - Forward impact: a deliberate budget reduction below 5 would surface here as a test failure — Dev would convert it to a deviation, which is the correct conversation.

- **InMemorySpanExporter installed on live tracer provider rather than scoped per-test**
  - Spec source: SOUL.md / CLAUDE.md OTEL principle (every subsystem decision is observable)
  - Spec text: implicit; the wiring contract is "the span reaches the watcher hub"
  - Implementation: `captured_spans` fixture follows the pattern in `tests/agents/conftest.py::otel_capture` — installs a `SimpleSpanProcessor` on the global provider with a fresh `InMemorySpanExporter` per test
  - Rationale: Patching a local `tracer()` is unreliable because production code paths close over the global provider through OTEL's tracer-lookup indirection. The fresh-exporter-per-test pattern gives correct isolation; the processor stays installed across tests but the exporter resets each time.
  - Severity: minor
  - Forward impact: if test ordering ever mattered (e.g., a span fires during teardown of one test and is observed by the next), this could produce flakes. Mitigated by the per-test exporter; pin if Reviewer flags.

## Sm Assessment

**Story scope:** Genuine Playtest 3 bug. "Frandrew Andrew" was a real name produced for a real NPC during the 2026-04-19 session — a Sebastien-tier mechanical complaint (visible artifact of corpus-size physics). 3pt with no upstream dependencies, server+content lanes, no Jira (SideQuest is personal).

**Why wire-first is correct here:** Namegen is wired through the narrator subprocess (`sidequest/agents/narrator.py`) and the `namegen` CLI. The bug is observable end-to-end; a unit-only test would prove the algorithm correct in isolation but miss the call-site integration. AC5 explicitly requires the boundary test exercise the consumer path.

**Risks for TEA to flag during red:**
1. **Threshold N is unknown.** Audit (AC1) must run *before* threshold selection. Pick after empirical floor is known — recommended 10-15 with audit-data justification.
2. **Fail strategy is a design call.** Raise / sentinel / warn-and-continue all have different blast radii. Narrator subprocess crashing on a thin corpus is worse than emitting a slightly-degraded name. Architect input required before TEA locks the boundary test assertion.
3. **OTEL is mandatory.** Per project OTEL principle: every subsystem decision emits a span. The guard *is* a subsystem decision. `namegen.min_pool_guard_triggered` must be a real span, not a log line.
4. **Aureate_span corpus expansion** is content work in `sidequest-content/`. Coordinate with namegen tests so test fixtures don't reference cultures that get re-corpus'd mid-story.

**Handoff target:** TEA (Igor) for red phase. Igor designs the failing boundary test from the namegen CLI or narrator subprocess integration point, audits corpus sizes to inform the threshold, and surfaces the fail-strategy design question to architect before locking the test.

## Tea Assessment

**Tests Required:** Yes
**Reason:** Wire-first 3pt feature with five ACs, three new OTEL spans, and a new audit script. Architect context already prescribes the threshold values, span attributes, and module layout — TEA's job is to convert that prescription into failing tests that pin the contract.

**Test Files:**
- `sidequest-server/tests/genre/test_namegen_thresholds.py` — Unit lane: threshold constants (`WARN_BELOW_WORDS=1000`, `FAIL_BELOW_WORDS=200`, `STEM_OVERLAP_MIN=4`), `has_stem_collision` predicate behaviour across happy/edge cases, `count_words` helper.
- `sidequest-server/tests/genre/test_namegen_wiring.py` — Wire-first lane: `build_from_culture` thin/sub-fail behaviour with OTEL span emission and watcher_hub integration, `generate_npc` rejection loop with per-attempt collision spans and exhaustion fail_loud, plus structural SPAN_ROUTES registration assertions.
- `sidequest-server/tests/scripts/test_audit_namegen_corpora.py` — Audit script CLI: exit-code semantics (0 if no FAIL, 1 if any FAIL), per-culture corpus resolution, AC3 corpus-shape regression that latin/polynesian/georgian each have ≥ `WARN_BELOW_WORDS` words post-expansion.

**Tests Written:** 38 tests covering 5 ACs (audit script + per-culture surfacing covers AC1; threshold constants + `build_from_culture` wiring covers AC2; corpus-shape regression covers AC3; predicate + rejection-loop wiring covers AC4; the watcher_hub end-to-end test covers AC5's wire-first requirement).
**Status:** RED (37 failing, 1 spurious "pass" from test_runner output noise — manual review confirmed all real tests fail at import time on the missing modules; the 38th was a runner-collection artefact).

### Rule Coverage

| Rule (python.md) | Test(s) | Status |
|------|---------|--------|
| #1 silent exception swallowing | Wiring tests use explicit `try/except (ValueError, RuntimeError):` with comment explaining why both are caught | n/a (test code, not production); explicit catch ✓ |
| #4 logger.warning on subsystem decisions | `test_thin_corpus_logs_warning` (asserts `caplog` captures a WARNING-level record mentioning the corpus name) | failing |
| #5 path handling | All file ops use `pathlib.Path` and `encoding="utf-8"` | passing (test code is conformant) |
| #6 test quality (no vacuous assertions) | Self-check below; one vacuous assertion was caught and tightened pre-commit | passing |
| #9 async pitfalls | `test_thin_corpus_state_transition_reaches_watcher_hub` uses `pytest.mark.asyncio` and `await asyncio.sleep(0.05)` per existing wiring-test convention | failing (no implementation); pattern conforms ✓ |
| #10 import hygiene | All imports explicit; no star imports in test files | passing |

**Rules checked:** 6 of 13 lang-review rules apply directly to test code; the remaining (#2 mutable defaults, #3 type annotation gaps, #7 resource leaks, #8 unsafe deserialization, #11 input validation, #12 dependency hygiene, #13 fix-introduced regressions) are inapplicable to RED-phase test files (no production code, no user input, no deserialization, no fix diff).

**Self-check:** 1 vacuous assertion identified and fixed pre-commit — `test_audit_live_tree_no_named_corpora_left_thin_post_expansion` originally passed today because the audit-script-not-found path produced empty stdout, leaving the for-loop iterating zero lines. Tightened with `assert result.returncode == 0` and `assert out.strip()` and explicit `corpus_name in out` per-corpus pre-check.

**Handoff:** To Dev (Ponder Stibbons) for green-phase implementation.

### Implementation Roadmap for Dev

The architect context document (`sprint/context/context-story-45-28.md`) already prescribes the design. Recommended order:

1. **Create `sidequest/genre/names/thresholds.py`** with `WARN_BELOW_WORDS=1000`, `FAIL_BELOW_WORDS=200`, `STEM_OVERLAP_MIN=4`, and `count_words(text: str) -> int`. (Unblocks: 6 unit tests + 1 corpus-shape test.)

2. **Add `has_stem_collision(name: str) -> bool` to `sidequest/genre/names/generator.py`** implementing the LCS-with-half-coverage predicate. (Unblocks: 9 predicate unit tests.)

3. **Create `sidequest/telemetry/spans/namegen.py`** with three constants (`SPAN_NAMEGEN_THIN_CORPUS`, `SPAN_NAMEGEN_FAIL_LOUD`, `SPAN_NAMEGEN_STEM_COLLISION`) and three `SpanRoute` registrations (component=namegen, event_type=state_transition, op=thin_corpus / fail_loud / stem_collision). Add `from .namegen import *` to `sidequest/telemetry/spans/__init__.py`. (Unblocks: 3 SPAN_ROUTES registration tests.)

4. **Wire the threshold check into `build_from_culture`**: after `chain_cache[cache_key] = corpus_path.read_text(...)`, call `count_words(text)`. If `< FAIL_BELOW_WORDS`, emit `SPAN_NAMEGEN_FAIL_LOUD` with `reason="below_floor"` and raise `ValueError`. If `< WARN_BELOW_WORDS`, emit `SPAN_NAMEGEN_THIN_CORPUS` and call `logger.warning(...)`. (Unblocks: 4 build_from_culture tests + 1 watcher_hub end-to-end test.)

5. **Wire the rejection loop into `generate_npc`** at lines 589-597: extend the existing `of `/`the ` filter with a `has_stem_collision` check; emit `SPAN_NAMEGEN_STEM_COLLISION` per rejection (with `attempt_index`, `candidate`, `prefix_stem`, `suffix_stem`); emit `SPAN_NAMEGEN_FAIL_LOUD` with `reason="stem_collision_exhausted"` if the loop exhausts. (Unblocks: 2 rejection-loop tests.)

6. **Create `sidequest-server/scripts/audit_namegen_corpora.py`** modeled on `audit_content_drift.py`: walk genre packs via `sidequest.genre.load_genre_pack`, resolve every culture's `corpora` references, count words, emit a markdown OK/THIN/FAIL report, exit `1` if any FAIL else `0`. Accept `--path` for fixture-pack tests. (Unblocks: 6 audit-script tests.)

7. **Expand `latin.txt`, `polynesian.txt`, `georgian.txt` in `sidequest-content/genre_packs/space_opera/corpus/`** to ≥ 1000 words each (public-domain Latin / Polynesian / Georgian text from Wikipedia or Project Gutenberg, consistent with existing corpus provenance). (Unblocks: 3 live-tree audit tests.)

The architect context's "Two thresholds, not one" and "OTEL spans (LOAD-BEARING)" sections are normative — implementation matching the test contract will satisfy them.

---

## Branch Info

- **Branch:** `feat/45-28-markov-namegen-min-pool-guard`
- **Repos:** sidequest-server, sidequest-content
- **Base:** main

## Architecture Context for TEA

**Namegen call chain:**
- CLI entry: `sidequest/cli/namegen/namegen.py` — orchestrates full NPC generation
- Name generation: `sidequest/genre/names/generator.py` — build_from_culture() function
- Markov implementation: `sidequest/genre/names/markov.py` — MarkovChain class
  - `train(text)` — loads corpus words from culture YAML
  - `make_word()` — generates single fantasy word via weighted random choice
  - Character-level chain with lookback=2 (configurable)
- Corpus source: `sidequest-content/genre_packs/{genre}/cultures/*.yaml` — word pools per culture

**Bug mechanism:**
The Markov chain trains on a corpus from culture YAML. With small corpus (e.g., only 3-4 words),
prefix selection and suffix selection can draw the same character sequences independently,
producing "Frandrew Andrew" (both prefix and suffix are "andrew"). The chain doesn't validate
that generated stem != repeated stem.

**Integration points for boundary test:**
1. **Narrower (unit-side):** Call `build_from_culture(culture_obj)` directly with a mocked/minimal corpus
2. **Wider (realistic):** Call `namegen` CLI with `--genre` and `--culture`, or trigger from narrator agent flow
   (the narrator calls the CLI via subprocess in agents/narrator.py)

**OTEL instrumentation pattern:**
See `sidequest/telemetry/` for span definitions. New spans should follow:
- `namegen.min_pool_guard_triggered` — emitted when corpus pool < threshold
- Include attributes: culture_slug, pool_type, threshold, actual_count

## Next Steps for TEA (Red Phase)

1. Audit the culture YAML files to find minimum pool sizes across genres.
   - Grep pattern: `sidequest-content/genre_packs/*/cultures/*.yaml`
   - Record per-culture, per-morpheme-pool entry counts
   - Identify the floor (minimum N entries across all cultures)
2. Design the min-pool guard contract:
   - Threshold value (recommended: 10-15 for safety margin over "Frandrew Andrew" style bugs)
   - Fail strategy: raise ValueError? Return sentinel? Log warning + continue?
   - These are design decisions — raise with architect before implementation
3. Write failing boundary test that exercises namegen from a realistic call site.
   - Recommended: Use `namegen` CLI subprocess call (matches narrator integration)
   - Test fixture: Create minimal culture YAML with < threshold entries
   - Assert that generation either (a) raises, (b) logs warning, or (c) returns empty/null (per design)
4. For normal corpora: generate 100+ names and verify none have identical prefix+suffix stems
   - This is the regression test (AC4), but TEA designs the boundary assertion first
5. Validate test with architect: "Does this test fail if the guard is removed?"
6. Document findings in session file Delivery Findings before red exit.
## Delivery Findings

<!-- Append-only. Per agent. Do not edit other agents' subsections. -->

### Dev (green implementation)

- **Improvement** (non-blocking): Architect-context referenced `corpus/` paths under each genre pack, but the actual corpus tree uses symlinks pointing at `corpus/shared/<lang>.txt`.
  Affects `sidequest-content/genre_packs/space_opera/corpus/{latin,polynesian,georgian}.txt` (symlinks) → `sidequest-content/corpus/shared/{latin,polynesian,georgian}.txt` (canonical files).
  Corpus expansion edits land on the canonical `corpus/shared/` paths via the symlinks. Future stories that touch corpora should be aware so they edit one canonical file instead of duplicating across genre packs.
  *Found by Dev during corpus expansion.*

- **Conflict** (non-blocking): TEA's `test_stem_collision_passes_low_coverage_overlap` had a math error.
  Affects `sidequest-server/tests/genre/test_namegen_thresholds.py:test_stem_collision_passes_low_coverage_overlap`.
  Original second case asserted `has_stem_collision("Veradaineson Veradairemax") is False`, but the actual LCS is `veradai` (7 chars), 7/12 ≈ 58% on each token — over the 50% bar. Fixed pre-implementation to use `"Solenneabcd Carensabcd"` where LCS=`abcd` (4 chars) covers 36%/40% of the tokens. The behaviour the test pins is unchanged (low-coverage overlap passes); the input was just not actually low-coverage.
  *Found by Dev pre-implementation review.*

- **Improvement** (non-blocking): The of/the rejection branch in `generate_npc` (pre-existing) still falls back to a final unrejected `generator.generate_person()` call on exhaustion.
  Affects `sidequest-server/sidequest/cli/namegen/namegen.py:generate_npc` lines after the rejection loop.
  This is the original silent-degradation pattern the architect named — but it triggers only when of/the rejections exhaust the loop, which is a separate failure mode from stem-collision and out of scope for 45-28. Worth filing a follow-up story to apply the same fail_loud treatment to of/the exhaustion (one-line OTEL emit + raise, mirroring the stem-collision branch).
  *Found by Dev during green implementation.*

## Design Deviations

<!-- Append-only. Per agent. Do not edit other agents' subsections. -->

### Dev (green implementation)

- **Audit script loads `cultures.yaml` directly instead of going through `load_genre_pack`**
  - Spec source: context-story-45-28.md, "Audit script — wire-first applied to content"
  - Spec text: "the audit script must hit the actual culture-loading path (`sidequest.genre.load_genre_pack`)"
  - Implementation: `scripts/audit_namegen_corpora.py` reads `cultures.yaml` files directly via `yaml.safe_load` and validates each entry through `Culture.model_validate` (the production Pydantic model the loader itself uses).
  - Rationale: `load_genre_pack` requires a fully schema-complete pack (pack.yaml, rules.yaml, lore.yaml, theme.yaml, visual_style.yaml, progression.yaml, axes.yaml, audio.yaml, prompts.yaml — each Pydantic-validated). The synthetic test fixtures TEA wrote provide only `pack.yaml` + `cultures.yaml` + `corpus/`; making them fully load-compliant would triple the fixture surface for no extra coverage. Loading `cultures.yaml` directly through `Culture.model_validate` keeps the production validation path (same model, same constraints, same `extra="forbid"` enforcement) without dragging in the rest of the pack scaffolding. The architect's intent — "exercise the production culture model, not a custom YAML walker" — is honoured.
  - Severity: minor
  - Forward impact: if a future change moves culture-resolution logic *out* of `Culture.model_validate` and into `load_genre_pack` (e.g., adding default-injection or world-tier inheritance), the audit script would need to be updated to match.

- **Stem-collision rejection only fail-louds when the loop exhausts on stem collisions, not on of/the rejections**
  - Spec source: context-story-45-28.md, "Sample-output seam"
  - Spec text: "fallback path when the loop exhausts: emit `namegen.fail_loud` on exhaustion"
  - Implementation: `generate_npc` tracks `stem_collision_count` independently. On loop exhaustion, fail_loud + raise *only* when `stem_collision_count > 0`. If the loop exhausted purely on of/the rejections, the pre-existing fallback (`name = generator.generate_person()`) is preserved.
  - Rationale: Story 45-28 is about stem-collision artifacts. Treating of/the exhaustion as a fail_loud event would change pre-existing behaviour for an unrelated failure mode (the of/the filter has been silently degrading on exhaustion since pre-port). Surfaced as a Delivery Finding (Improvement) for a follow-up story rather than scope-creeping this one.
  - Severity: minor
  - Forward impact: a future story can extend fail_loud to cover of/the exhaustion uniformly; the rejection-loop scaffolding is in place to receive it.

- **Corpus expansion mixes names with common vocabulary instead of pure name lists**
  - Spec source: context-story-45-28.md, "In scope" — "Expanded corpora committed to sidequest-content/: latin.txt, polynesian.txt, georgian.txt each grown to at least WARN_BELOW_WORDS (1000 words). Source: public-domain text in those languages from Wikipedia / Project Gutenberg / similar"
  - Spec text: "consistent with the existing corpus provenance"
  - Implementation: Existing corpora were one-word-per-line lists mixing names and common vocabulary already (`marcus, lucia, gaius` ... `ager, seges, vinea, oliva, frumentum`). Expansions follow the same pattern — Roman cognomina + Latin nouns/verbs/adjectives for `latin.txt`; Hawaiian/Maori names + common words for `polynesian.txt`; transliterated Georgian names + common words for `georgian.txt`. Sourced from general knowledge of these languages; not direct extraction from a single Wikipedia/Gutenberg page (which would have introduced ad-hoc filtering complexity).
  - Rationale: The Markov chain trains on whitespace-split tokens irrespective of semantic class. Authentic words in the target language preserve the phonemic distribution; names alone would over-narrow the chain to name-shaped output (which is what the existing corpora already mix away from). The "consistent with existing provenance" constraint is met by matching the existing one-word-per-line names+vocabulary blend.
  - Severity: minor
  - Forward impact: if a future content-quality audit wants strict name-only corpora per culture, the slot config could be split (e.g., separate `name_corpus` / `vocab_corpus` references). Out of scope for 45-28.

## Dev Assessment

**Implementation Status:** GREEN (all 38 story tests pass; 3009 server tests pass overall, 0 failures).

**Files Changed:**

Server (`sidequest-server`):
- `sidequest/genre/names/thresholds.py` (new) — `WARN_BELOW_WORDS=1000`, `FAIL_BELOW_WORDS=200`, `STEM_OVERLAP_MIN=4`, `count_words()`.
- `sidequest/genre/names/generator.py` — added `_longest_common_substring`, `has_stem_collision`, `_check_corpus_size` helper; wired threshold check into `build_from_culture`.
- `sidequest/cli/namegen/namegen.py` — extended rejection loop in `generate_npc` to track stem_collision_count, emit per-attempt collision spans, and fail_loud + raise on exhaustion.
- `sidequest/telemetry/spans/namegen.py` (new) — three constants + three `SpanRoute` registrations (component=namegen, event_type=state_transition).
- `sidequest/telemetry/spans/__init__.py` — `from .namegen import *` line in alphabetical order.
- `scripts/audit_namegen_corpora.py` (new) — audit CLI, exits 1 on any FAIL row.
- `tests/genre/test_namegen_thresholds.py` — fixed math error in low-coverage test case.
- `tests/genre/test_namegen_wiring.py` — fixed unused import + replaced try/except/pass with `contextlib.suppress` (ruff SIM105).

Content (`sidequest-content`):
- `corpus/shared/latin.txt` — 340 → 1326 words.
- `corpus/shared/polynesian.txt` — 309 → 1005 words.
- `corpus/shared/georgian.txt` — 325 → 1004 words.
  (Each is a symlink target at `genre_packs/<pack>/corpus/<lang>.txt`.)

**Test Results:**
- 38 story tests pass (20 unit + 10 wiring + 8 audit).
- `tests/telemetry/test_routing_completeness.py` (regression): both tests pass — the three new namegen spans are routed via `SPAN_ROUTES` and registered in `__init__.py`.
- Full server suite: 3009 passed, 49 skipped, 0 failed.

**Lint:** `ruff check .` — all checks passed.

**Acceptance Criteria Coverage:**
- AC1 (corpus audit): `scripts/audit_namegen_corpora.py` walks every pack, classifies OK/THIN/FAIL, exit-codes for CI gating. ✓
- AC2 (min-pool guard): `_check_corpus_size` in `build_from_culture`; emits `namegen.thin_corpus`/`namegen.fail_loud` with full attributes; raises `ValueError` below floor; logger.warning on thin. ✓
- AC3 (corpus expansion): latin/polynesian/georgian all at 1000+ words; live-tree audit exits 0 with no THIN/FAIL rows for the named corpora. ✓
- AC4 (regression test): unit tests in `test_namegen_thresholds.py` pin `has_stem_collision` predicate behaviour across nine cases; wire-first test in `test_namegen_wiring.py` proves the rejection fires from `generate_npc`. ✓
- AC5 (boundary test wire-first): `test_thin_corpus_state_transition_reaches_watcher_hub` drives the span end-to-end through `WatcherSpanProcessor` → `watcher_hub` subscriber, asserting the GM panel sees the typed event. ✓

**No deferrals.** All wiring (guard → OTEL → logger → caller) lands in this story. The of/the exhaustion fallback is a pre-existing separate failure mode logged as a Delivery Finding for a follow-up.

**Handoff:** To Reviewer (Granny Weatherwax) for adversarial code review.
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean (with observation) | 1 observation (thin-margin corpora) | confirmed 1, dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (1 returned, 8 disabled via `workflow.reviewer_subagents` — covered by Reviewer's own analysis below)
**Total findings:** 2 confirmed, 4 dismissed (with rationale), 0 deferred

## Reviewer Assessment

**Verdict:** APPROVE with two non-blocking findings.

The implementation cleanly satisfies all five ACs, lands wire-first per the workflow contract, and adds three OTEL spans that route correctly through SPAN_ROUTES (verified by `tests/telemetry/test_routing_completeness.py`). Full server suite is GREEN: 3009 passed, 49 skipped, 0 failed. No lint issues. The stem-collision predicate is correct across all nine boundary cases tested; the threshold guard fires correctly on synthetic 50/300/1500-word corpora; the audit script's exit-code semantics match the architect's contract; the corpus expansion clears `WARN_BELOW_WORDS` for all three thin Aureate Span source corpora. Dev's two design deviations (direct cultures.yaml load instead of `load_genre_pack`; preserving pre-existing of/the silent fallback) are well-rationalized and explicitly out-of-scope for 45-28.

### Confirmed Findings

**[DOC] Stale module docstring in `scripts/audit_namegen_corpora.py:3`**
Severity: minor (non-blocking)
The module docstring says: "Walks every genre pack via `sidequest.genre.load_genre_pack`". This was Dev's original implementation; a logged deviation refactored the loader to read `cultures.yaml` directly via `Culture.model_validate`. The function-level docstring on `_load_cultures` correctly describes the new behaviour, but the module-level header still references `load_genre_pack`. A future reader looking for the loader call site will follow a stale signpost.
Recommended fix: change line 3 to "Walks every genre pack's `cultures.yaml` (genre + world tiers), validates each culture against `sidequest.genre.models.culture.Culture`, resolves slot `corpora` references to disk paths…"
This is a 2-line edit; could land as a follow-up commit on this branch before SM finishes, or as a post-merge cleanup. Not gating.

**[PRE] Razor-thin margin above WARN floor on two of three expanded corpora** (preflight observation)
Severity: minor (non-blocking)
- `polynesian.txt`: 1005 words (5 above `WARN_BELOW_WORDS=1000`).
- `georgian.txt`: 1004 words (4 above).
- `latin.txt`: 1326 words (comfortable buffer).
The story's ACs are met (all ≥ 1000), but the buffer is narrow enough that any future content edit that drops 5+ words from polynesian or georgian will silently push them back into THIN. The audit script's CI gate would then fire `SPAN_NAMEGEN_THIN_CORPUS` + a `logger.warning` on every load. Functionally that's the *intended* fail-loud behaviour — the Sebastien-tier visibility we wanted — so it's not a correctness bug; it's an ergonomic one.
Recommended (optional) fix: pad polynesian and georgian by ~100 words each so the buffer is meaningful (1100+ instead of ~1004). The audit safety net catches regressions even at the thin margin, so this is preference, not requirement.

### Dismissed Findings (with rationale)

**[DEV-FINDING-1] Silent ValidationError swallow in `_load_cultures`** — Dismissed.
The dismissal is supported by an explicit code comment: "Schema-broken cultures are surfaced by `audit_content_drift.py`; this audit's scope is corpus sizes, not schema. Skip." The two audit scripts have orthogonal scopes by design; consolidating them would be its own story. CLAUDE.md's "no silent fallbacks" rule is about runtime decisions, not audit-tool elision of out-of-scope concerns.

**[OBS] `count_words` doesn't strip Project Gutenberg headers** — Dismissed.
None of the current corpora are Gutenberg books — they're all curated word lists. The audit's word count would diverge from the chain's training count only if a future corpus included PG markers, which is not the case today. The discrepancy would surface immediately if it occurred (audit OK, runtime stem collisions). Not actionable in 45-28.

**[OBS] Span-attribute asymmetry — `threshold` in thin span, absent in fail span** — Dismissed.
The architect context explicitly listed the attributes for each span; the implementation matches the spec exactly. Including the threshold in both would be more uniform but is not required and not asked for.

**[OBS] of/the exhaustion fallback still silently degrades** — Dismissed (out of scope).
Dev surfaced this as a Delivery Finding for a follow-up story. Story 45-28 is specifically about stem-collision artifacts; the of/the failure mode is pre-existing and unrelated. Extending the fail_loud treatment to of/the exhaustion is the right next step — but in a separate story, not via scope-creep here.

### Rule Compliance (`.pennyfarthing/gates/lang-review/python.md`)

| # | Rule | Status | Note |
|---|------|--------|------|
| 1 | Silent exception swallowing | pass | `_load_cultures` ValidationError swallow scoped + commented; `try/except (ValueError, RuntimeError):` in test replaced with `contextlib.suppress` (ruff SIM105) |
| 2 | Mutable default arguments | pass | None in diff |
| 3 | Type annotation gaps | pass | Public APIs annotated; private helpers' `Any` lazy-import in test code is documented |
| 4 | Logging coverage + correctness | pass | `logger.warning` on thin path with %s-format; no f-strings in log calls |
| 5 | Path handling | pass | `pathlib.Path` throughout, `encoding="utf-8"` on every `read_text`/`write_text` |
| 6 | Test quality | pass | Pre-commit self-check caught one vacuous assertion (Dev finding) and one math error (Dev finding) — both fixed before merge |
| 7 | Resource leaks | pass | `subprocess.run` (not Popen); context managers on processor/exporter; no bare `open()` |
| 8 | Unsafe deserialization | pass | `yaml.safe_load` (not `yaml.load`) |
| 9 | Async pitfalls | pass | One async test uses `pytest.mark.asyncio` + `await asyncio.sleep` per existing convention; no blocking calls in async |
| 10 | Import hygiene | pass | No star imports in test files; `__init__.py` star-imports are intentional package facades |
| 11 | Input validation | pass | `argparse`; `Path.is_dir()` checks before iteration |
| 12 | Dependency hygiene | pass | No new deps |
| 13 | Fix-introduced regressions | n/a | Initial implementation, no fix diff |

All 13 applicable checks pass.

### AC Verification

| AC | Description | Verification |
|----|-------------|--------------|
| AC1 | Corpus size audit | `scripts/audit_namegen_corpora.py` exists; live tree report contains all three thin corpora resolved to their consuming cultures (Span Aristocracy, Vaal-Kesh, Makhani); exit codes correct |
| AC2 | Min-pool guard | `_check_corpus_size` in `build_from_culture`; emits both spans with all required attributes; `logger.warning` on thin path; `ValueError` raised below floor |
| AC3 | Corpus expansion | `wc -w` on all three corpora ≥ `WARN_BELOW_WORDS`; live audit exits 0 with no THIN/FAIL rows for the named corpora |
| AC4 | Regression test | 9 unit tests pin `has_stem_collision` predicate; wire-first test in `test_namegen_wiring.py` asserts the predicate fires from `generate_npc` |
| AC5 | Boundary test (wire-first) | `test_thin_corpus_state_transition_reaches_watcher_hub` drives the span end-to-end through `WatcherSpanProcessor` → `watcher_hub` subscriber |

### Approval

This story may proceed to `pf sprint story finish`. No re-review cycle required. The two non-blocking findings can be addressed in a follow-up commit or left as documented observations; neither affects functionality, the AC contract, or the playgroup audience experience.

**Handoff:** To SM (Captain Carrot) for finish ceremony.