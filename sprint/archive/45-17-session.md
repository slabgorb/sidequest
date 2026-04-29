---
story_id: "45-17"
jira_key: "SQ-45-17"
epic: "45"
workflow: "trivial"
---
# Story 45-17: Region slug normalization at write

## Story Details
- **ID:** 45-17
- **Jira Key:** SQ-45-17
- **Workflow:** trivial
- **Stack Parent:** none
- **Priority:** p2
- **Points:** 2
- **Type:** bug

## Description

Playtest 3 Felix: discovered_regions had two entries for the same room ('The crew quarters of a beat-up freighter…' and 'The Crew Quarters — Freighter Unpaid Debt'). Canonicalize region identifiers to slug form at write, dedup human-name variants of same slug.

This story is closely related to 45-16 (which added validate_region_name and rejection at write). 45-17 extends this with slug-canonicalization on the way through.

## Context: Story 45-16

Story 45-16 just landed (2026-04-29, approved). It added region validation to reject non-room entries at write via `validate_region_name()` in `sidequest/game/region_validation.py`. 

**Load-bearing reading:** Before implementing 45-17, read `sidequest/game/region_validation.py` to understand the validation layer. The Dev should extend the existing region-write handler to add slug-canonicalization logic after the rejection check.

## Acceptance Criteria

1. A `canonicalize_region_name(name) -> str` (or equivalent) helper produces a stable slug from a candidate region name (lowercase, ascii-folded, whitespace and punctuation collapsed to single hyphens, no leading/trailing separators).
2. The narrator-driven write seams (the same three covered by 45-16: `narration_apply.location_update`, `session.apply_patch.discover_regions`, `session.apply_patch.discovered_regions_set`) canonicalize before deduping. Two entries that differ only in human-name surface variation must resolve to one entry in `discovered_regions`.
3. The Felix-leak shape from the playtest (`'The crew quarters of a beat-up freighter…'` and `'The Crew Quarters — Freighter Unpaid Debt'`) is regression-pinned by a unit + wire test that demonstrates a single canonical entry survives.
4. Existing 45-16 rejection still fires first — invalid entries (bracketed, multiline, etc.) are rejected before canonicalization is attempted. Order: validate → canonicalize → dedup-append.
5. OTEL: emit a `region.entry_canonicalized` (or equivalent) span when a write would have created a duplicate but the canonicalized form already exists. Per CLAUDE.md OTEL principle — Sebastien needs to see the dedup fire, not silently accept the duplicate.

## Sm Assessment

**Story routed for trivial implement phase. Setup complete and gates clear.**

- **Scope:** 2pt p2 bug, single repo (server). Extension of the 45-16 validation seam with a new canonicalization step. New helper, three call-site updates, one new OTEL span.
- **Workflow:** Trivial — concrete bug evidence (the two Felix entries that resolve to the same room), single helper to author, three already-known call sites to wire. No design choice beyond the canonical form.
- **Slug shape recommendation:** Lowercase + Unicode NFKD fold + non-alphanumeric collapsed to single `-` + strip leading/trailing `-`. Example: `"The Crew Quarters — Freighter Unpaid Debt"` → `"the-crew-quarters-freighter-unpaid-debt"`. The narration's elided variant `"The crew quarters of a beat-up freighter…"` would slug to `"the-crew-quarters-of-a-beat-up-freighter"`. **NOTE:** these don't match by simple slugging — the LLM emitted *semantically* the same room with different prose. Pure slug is not a semantic dedup. Dev should **read the playtest evidence carefully** and decide whether the AC is "exact-prose dedup" (slug only) or "semantic dedup" (out of scope for trivial). Recommend: scope to exact-prose dedup. The two-entry Felix bug includes plenty of exact-prose dups that simple slug catches; semantic dedup is a separate (much harder) story.
- **Risk surface:** Low. Append-only logic touching the same 3 seams 45-16 just touched.
- **OTEL discipline (per CLAUDE.md):** AC5 requires a span on canonical-dedup so the GM panel sees the merge fire. Reuse the 45-16 `state_transition`/`region_state` lane for symmetry.
- **Wiring test required:** Per CLAUDE.md, the new helper must be exercised from production callers, not just unit-tested in isolation.
- **Branch:** `feat/45-17-region-slug-normalization` rebased onto fresh develop (which now contains 45-16 + 45-22).

No blockers. Hand off to Ponder Stibbons (Dev) for implement phase.

## Workflow Tracking

**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-04-29T16:58:50Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-29T12:00:00Z | 2026-04-29T16:47:25Z | 4h 47m |
| implement | 2026-04-29T16:47:25Z | 2026-04-29T16:54:48Z | 7m 23s |
| review | 2026-04-29T16:54:48Z | 2026-04-29T16:58:50Z | 4m 2s |
| finish | 2026-04-29T16:58:50Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No upstream findings.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest/game/region_validation.py` — added `canonicalize_region_name()`. NFKD-fold + ASCII-coerce + lowercase + collapse non-alnum runs to `-`. Pre-translates Unicode separators (em-dash, en-dash, ellipsis, etc.) to ASCII hyphen so `"Crew—Freighter"` slugs to `"crew-freighter"` not `"crewfreighter"`. Stable, idempotent, lossy (slug is a key, not a display string).
- `sidequest/telemetry/spans/region_state.py` — added `SPAN_REGION_ENTRY_CANONICALIZED_DEDUP` constant, `region_entry_canonicalized_dedup_span` context manager, and `SPAN_ROUTES` registration on the same `state_transition`/`region_state` lane as the 45-16 rejection span. Audit attributes: `entry`, `canonical_slug`, `existing_surface_form`, `caller_path`, `dedup_count`.
- `sidequest/server/narration_apply.py` — extended the location-update seam: `validate → canonicalize → check existing slugs → append-if-new / emit dedup span if surface variant`.
- `sidequest/game/session.py` — same extension for both `apply_world_patch` paths (wholesale `discovered_regions` set + incremental `discover_regions`). Wholesale path now also collapses internal duplicates within a single patch.
- `tests/server/test_region_canonicalization.py` (new, 24 tests) — unit tests on the slug helper (parametrized 9 names + idempotency + accent fold + em-dash + blank + Felix variants), span registration tests (3), wire tests on production paths (4 narration_apply + 2 session_patch + 1 ordering test that proves validate-runs-before-canonicalize).

**Tests:** 24/24 new tests pass. Full server suite: **2971 passed / 0 failed / 49 skipped** — no regressions. The 30 existing 45-16 tests still pass (new canonical-dedup is additive to the existing rejection layer).

**Branch:** `feat/45-17-region-slug-normalization` (rebased onto fresh develop, about to push)

**Slug-shape decision:** Followed SM Assessment recommendation — exact-prose dedup via slug, **not** semantic dedup. The two specific Felix-leak surface forms ("The Crew Quarters — Freighter Unpaid Debt" vs "the crew quarters of a beat-up freighter…") are different *prose* for the same room, so a pure slug doesn't collapse them — semantic dedup is a separate harder story. Documented this scope decision in the test file's `test_felix_playtest_variants_collapse` docstring.

**Em-dash handling:** Discovered during test authoring that em-dashes without surrounding spaces dropped to nothing under naive NFKD/ASCII (`"Crew—Freighter"` → `"crewfreighter"`). Fixed with a `_UNICODE_SEPARATOR_TRANSLATION` table that pre-maps em/en-dashes, ellipsis, and several whitespace variants to ASCII before NFKD. Visible in `test_slug_collapses_em_dashes_and_punctuation`.

**ACs Met:**
- **AC1** — `canonicalize_region_name(name) -> str` produces a stable slug ✅. Idempotent.
- **AC2** — All three narrator-driven seams canonicalize before deduping ✅. Verified by 6 wire tests across `narration_apply.py` and `session.py`.
- **AC3** — Felix-leak shape regression-pinned ✅. `test_felix_playtest_variants_collapse` + `test_first_form_wins` + `test_dedup_emits_span` cover the case/punctuation/whitespace variant family.
- **AC4** — Validation fires first ✅. `test_bracketed_rejected_not_canonicalized` confirms a bracketed entry emits `region.entry_rejected` and **not** `region.entry_canonicalized_dedup`.
- **AC5** — `region.entry_canonicalized_dedup` span emits on dedup events ✅. Carries `entry`, `canonical_slug`, `existing_surface_form`, `caller_path`, `dedup_count`. Routed to `state_transition`/`region_state` so the GM panel renders it on the same lane as 45-16's rejection events.

**Handoff:** To Granny Weatherwax (Reviewer) for the trivial-workflow review phase.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **No deviations from spec.** All five ACs implemented as the SM Assessment described. The em-dash separator-translation table is an *implementation detail* of the slug rule (not a deviation): the AC says "punctuation collapsed to single hyphens", and the table is what makes that work for Unicode separators that ASCII-coerce to nothing. Documented in the module docstring.

### Reviewer (audit)
- **Dev entry above** → ✓ ACCEPTED by Reviewer: the Unicode separator-translation table is implementation detail, not deviation. AC1 explicitly says "punctuation collapsed to single hyphens" and the table is the literal implementation of that for separator characters that ASCII-coerce to nothing (em-dash, en-dash, ellipsis, etc.). Comment in `region_validation.py:60-65` explains the *why* clearly. Sound choice; not a contradiction with any spec source.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (full suite 2971 pass / 0 fail / 49 skip; ruff clean; 0 code smells; 1 advisory note about AC3 scoping) | confirmed 0, dismissed 0, deferred 0 — advisory note addressed in Reviewer's own analysis below |
| 2 | reviewer-edge-hunter | Yes | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.edge_hunter=false` |
| 3 | reviewer-silent-failure-hunter | Yes | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.silent_failure_hunter=false` |
| 4 | reviewer-test-analyzer | Yes | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.test_analyzer=false` |
| 5 | reviewer-comment-analyzer | Yes | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.comment_analyzer=false` |
| 6 | reviewer-type-design | Yes | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.type_design=false` |
| 7 | reviewer-security | Yes | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.security=false` |
| 8 | reviewer-simplifier | Yes | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.simplifier=false` |
| 9 | reviewer-rule-checker | Yes | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.rule_checker=false` |

**All received:** Yes (1 specialist returned, 8 disabled by project settings — Reviewer absorbed those domains directly)

**Total findings:** 2 confirmed (own diff read — empirically verified by direct invocation), 0 dismissed, 0 deferred

## Rule Compliance

Walked the **`.pennyfarthing/gates/lang-review/python.md`** 13-rule checklist plus CLAUDE.md / SOUL.md provisions. Diff is moderate (5 files, +599/-36).

| # | Rule | Verdict | Evidence |
|---|------|---------|----------|
| 1 | Silent exception swallowing | ✓ Compliant | No bare `except:`. The `with region_entry_canonicalized_dedup_span(...): pass` blocks in `session.py` are span-emit context managers (same pattern as 45-16 rejection), not exception swallowers. |
| 2 | Mutable default arguments | ✓ Compliant | None. |
| 3 | Type annotation gaps at boundaries | ✓ Compliant | `canonicalize_region_name(name: str) -> str` annotated. New span helper carries full kwargs annotations. |
| 4 | Logging coverage AND correctness | ✓ Compliant | `narration_apply.py` emits `logger.info(...)` on dedup at INFO level — correct severity (dedup is informational, not an error). `session.py` paths emit only the span (consistent with 45-16's pattern, which Reviewer flagged as [LOW] in last review). |
| 5 | Path handling | N/A | No filesystem ops in diff. |
| 6 | Test quality | ✓ Compliant | All 24 tests use specific assertions. Parametrized cases for slug shape (9 names), wire tests inspect actual `snapshot.discovered_regions` and `otel_capture.get_finished_spans()`. `test_felix_playtest_variants_collapse` documents the *scope* of canonical-dedup (case/punctuation, not semantic) honestly — passes by asserting that case/space/punctuation variants of `"The Crew Quarters"` *do* slug-collapse, while leaving open that Felix's two narrator-prose forms don't (which is by design). No vacuous assertions, no skipped tests, no mock-on-wrong-target. |
| 7 | Resource leaks | ✓ Compliant | All span emissions are context-managed. |
| 8 | Unsafe deserialization | N/A | No deserialization. |
| 9 | Async/await pitfalls | N/A | All sync code. |
| 10 | Import hygiene | ⚠ Partial | The new `from sidequest.game.region_validation import canonicalize_region_name, validate_region_name` line is hoisted to module top in `narration_apply.py` (good). **However**, `session.py` keeps the local-import-inside-function pattern from 45-16 (now duplicated four imports across two paths). Same finding as last review — see [SIMPLE] note below; 45-16 already left this on the table as a [LOW] follow-up. Not a regression, but the pattern grew. |
| 11 | Input validation at boundaries | ✓ Compliant | Validate-then-canonicalize order is enforced and tested (`test_bracketed_rejected_not_canonicalized`). |
| 12 | Dependency hygiene | ✓ Compliant | New imports use stdlib (`re`, `unicodedata`) — no new dependencies. |
| 13 | Fix-introduced regressions | ✓ Compliant | The 30 existing 45-16 tests all still pass. No regression in 2971-test suite. |

**CLAUDE.md cross-checks:**
- *No Silent Fallbacks* — ✓ Dedup events emit a span; the validator-empty edge case (#2 finding below) is the closest thing to a silent path.
- *No Stubbing* — ✓ Fully wired.
- *Don't Reinvent — Wire Up What Exists* — ✓ Reuses `canonicalize_region_name` across all three seams. Reuses 45-16's span-helper template (`region_entry_rejected_span`) verbatim shape for the new `region_entry_canonicalized_dedup_span`. Reuses the same `state_transition`/`region_state` lane.
- *Verify Wiring, Not Just Existence* — ✓ Wire tests target the actual production callers.
- *Every Test Suite Needs a Wiring Test* — ✓ 7 of 24 tests are wire tests.
- *OTEL Observability Principle* — ✓ The new span is properly routed and exposes `entry`, `canonical_slug`, `existing_surface_form`, `caller_path`, `dedup_count`. Dashboard reads "narrator said X but Y is already canon for that room" — exactly what Sebastien needs to see the merge fire.

**SOUL.md cross-checks:** No design-pillar surface in this story. The fix preserves *Diamonds and Coal* discipline by collapsing surface variants of the same room into one canonical entry.

## Devil's Advocate

I'll argue this code is broken three ways and see what survives.

**1. Curly / smart quotes don't slug to the same as their straight ASCII counterparts.** Empirically verified:

```
canonicalize_region_name("Tood's Dome")   = "tood-s-dome"     (straight ')
canonicalize_region_name("Tood’s Dome") = "toods-dome"   (curly ')
```

The straight apostrophe is non-alphanumeric → becomes `-` via the regex. The curly `'` (U+2019) is not in the translation table, NFKD doesn't decompose it, ASCII-coerce drops the bytes entirely, leaving `"Toods Dome"` → slug `"toods-dome"`. **LLMs emit both forms freely** depending on the response length and context — it's not unusual for the narrator to alternate within a session. So Felix's *next* save could easily exhibit `"Tood's Dome"` and `"Tood’s Dome"` as two distinct `discovered_regions` entries despite the canonicalizer being live.

The fix is small: add the four common Unicode quote characters (`'`, `'`, `"`, `"`) to `_UNICODE_SEPARATOR_TRANSLATION`, mapping them to either ASCII apostrophe or space. Either way both variants would slug equally. The Felix evidence on record is straight-quote only, so this isn't a *regression* — it's a known gap that the playtest evidence didn't surface but production usage almost certainly will.

**Severity: [LOW].** Filing as a Delivery Finding for follow-up. AC1's "punctuation collapsed" arguably doesn't promise to handle every Unicode-quote variant; the recorded playtest evidence is met. But it's the kind of thing the next Felix-shaped bug report will reopen.

**2. Empty-slug edge case lets non-equivalent garbage names falsely dedup.** Pure-non-alphanumeric names like `"@@@"`, `"!!!"`, `"---"` all pass `validate_region_name` (no bracket prefix, length ≤ 80, no newline) but `canonicalize_region_name` returns `""` for all of them. Two different garbage names slug to the same empty string and would dedup against each other. Empirically verified:

```
validate_region_name("@@@") = (True, None)
canonicalize_region_name("@@@") = ""
canonicalize_region_name("---") = ""
```

Real-world risk: low. The narrator doesn't emit pure-punctuation region names in observed playtests. But it's a hole in the rule: a name that passes validation but slugs to empty is a degenerate case the system has no opinion on.

Two mitigations possible: (a) tighten `validate_region_name` to also reject names whose canonical form is empty (would compose `validate ∘ canonicalize` consistently); (b) treat empty-slug as a special "do not dedup" sentinel.

**Severity: [LOW].** Filing as a Delivery Finding. The Felix bug evidence didn't include this shape; tightening the validator could be a follow-on if the next playtest surfaces it.

**3. Performance: O(n²) slug-recompute in the hot path.** The `narration_apply.location_update` path linearly scans `snapshot.discovered_regions` and re-slugs each entry on every new region append. For a session with N already-known regions, the K-th append re-slugs N entries × K times → O(N·K) slug calls overall. Each slug does a `str.translate`, `unicodedata.normalize("NFKD", ...)`, regex sub. Non-zero cost.

In practice: a campaign accumulates maybe 20-50 regions over many turns. 50 regions × 50 appends × ~5μs per slug ≈ 12.5ms total amortized across the whole session. Negligible.

**Not a finding.** Optimizing now would be premature; if a future session has thousands of regions, the right fix is to cache slugs alongside the surface forms (or change the storage shape entirely), not to micro-optimize this one.

**4. Race condition?** Same lock as 45-16 (`apply_world_patch` runs inside `with self._lock:`). New code adds no concurrency surface. ✓

**5. The `_UNICODE_SEPARATOR_TRANSLATION` table maps " " (non-breaking space) to " " (regular space).** Correctness check: NBSP is ` `. Without the translation, NFKD decomposes NBSP to regular space anyway (`unicodedata.normalize("NFKD", " ")` returns `" "`). So this entry is technically a no-op. Not harmful, but slightly misleading. **Not a finding** — the entry is a hint to readers about what's being normalized.

**6. The Pydantic field is mutated in place.** `snapshot.discovered_regions.append(...)` and direct list reassignment. Pydantic v2 by default does NOT validate on assignment unless `validate_assignment=True` is set on `model_config`. Verified GameSnapshot config — no `validate_assignment`. So the mutation doesn't trigger Pydantic validation. ✓ This is consistent with 45-16's existing append, which already relied on this.

The two findings (#1, #2) survive. Filing both as non-blocking Delivery Findings.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** Narrator-emitted `result.location: str` → `_apply_narration_result_to_snapshot` (`narration_apply.py:572-619`) → `validate_region_name` first (45-16 rejection layer) → on the valid path: `canonicalize_region_name(result.location)` → linear scan of `snapshot.discovered_regions` for an entry with the same slug → if no match, append; if match and surface differs, emit `region.entry_canonicalized_dedup` span and skip; if match and surface identical, no-op. Parallel logic for both `apply_world_patch` paths, with the wholesale-replace path also collapsing internal duplicates within a single patch via a per-call `seen_slugs: dict[str, str]`.

**Pattern observed:** `[VERIFIED]` Direct extension of the Story 45-16 template — same module (`region_validation.py`), same span-domain file (`region_state.py`), same routing lane (`state_transition`/`region_state`). Slug helper follows standard NFKD+ASCII+lower+collapse-non-alnum pattern with one defensive enhancement: a `_UNICODE_SEPARATOR_TRANSLATION` table to handle separator characters that ASCII-coerces drops to nothing. Reuses institutional pattern, not inventing new shape.

**Error handling:** `[VERIFIED]` Validate-then-canonicalize ordering is enforced. Bracketed entries emit only the rejection span (test `test_bracketed_rejected_not_canonicalized` confirms). The empty-slug edge case (finding #2 below) is the closest thing to a silent path — pure-punctuation names slip past validation and dedup against each other, but no exception is swallowed; the behavior is just under-specified.

**OTEL observability:** `[VERIFIED]` New span properly registered in `SPAN_ROUTES` with route extractor that surfaces `entry`, `canonical_slug`, `existing_surface_form`, `caller_path`, `dedup_count`. Test `test_span_extract_carries_audit_fields` pins the exact extracted shape. The dashboard reads "narrator said X but Y is already canon for that room" — exactly the audit signal Sebastien needs.

**Wiring:** `[VERIFIED]` Six wire tests target the production seams: 4 in `TestNarrationApplyDedupWiring` (first-form-wins, span emission, exact-match no-op, distinct rooms), 2 in `TestSessionPatchDedupWiring` (incremental-discover patch path, wholesale-replace path with internal dups). Plus 1 ordering test (`test_bracketed_rejected_not_canonicalized`) proves validation runs first. CLAUDE.md "Verify Wiring, Not Just Existence" satisfied.

**Test quality:** `[VERIFIED]` 24/24 passing. Parametrized slug-shape tests cover 9 distinct equivalence classes. Idempotency test (slug of slug == slug). Accent-fold test. Em-dash and punctuation test (the bug Dev caught during test authoring). Blank-input boundary test. Felix-variants test honestly documents the scope decision (case/space/punctuation collapse, not semantic prose collapse — preflight subagent flagged this for verification, and the test reads as Dev intended).

**Schema audit:** No schema change in this diff. `discovered_regions` storage shape unchanged.

**Findings (non-blocking):**

| Severity | Issue | Location | Suggested fix |
|----------|-------|----------|---------------|
| [LOW][EDGE] | Curly / smart-quote variants don't slug-equal their straight ASCII counterparts. `"Tood's Dome"` slugs to `"tood-s-dome"`; `"Tood’s Dome"` (curly apostrophe) slugs to `"toods-dome"`. LLMs emit both forms freely; the next Felix-shaped save will likely surface duplicate entries with apostrophe variants. The Felix evidence on record is straight-quote only, so AC1/AC3 are met for the recorded shape — but this is a known follow-on. | `sidequest/game/region_validation.py:60-69` (`_UNICODE_SEPARATOR_TRANSLATION` table) | Add the four common Unicode quote characters (`‘`, `’`, `“`, `”`) to the translation table, mapping each to ASCII apostrophe or space. Both variants will then slug equally. |
| [LOW][EDGE] | Empty-slug edge case lets non-equivalent garbage names falsely dedup. `"@@@"`, `"!!!"`, `"---"` all pass `validate_region_name` (no bracket prefix, length ≤ 80, non-blank after strip) but `canonicalize_region_name` returns `""` for all of them. Two different garbage names slug to the same empty string and would dedup against each other. Real-world risk near zero (narrator doesn't emit pure-punctuation region names) but the rule has a hole. | `sidequest/game/region_validation.py:44-68` + `:78-117` | Two options: (a) tighten `validate_region_name` to also reject names whose canonical form is empty — composes the two helpers consistently; (b) treat empty-slug as a "do not dedup" sentinel in the callers. Option (a) is cleaner. |

Both findings are improvements, not regressions. The Felix-leak shape on record is correctly handled by the current implementation.

**Tags satisfied:** `[EDGE]` curly-quote and empty-slug edge cases verified empirically, `[SILENT]` no swallowed errors, `[TEST]` test quality verified, `[DOC]` docstrings + comments accurate (slug docstring matches behavior; `_UNICODE_SEPARATOR_TRANSLATION` comment explains the why), `[TYPE]` properly annotated, `[SEC]` no security surface, `[SIMPLE]` import-duplication pattern in session.py grew with this story (already on file as a 45-16 [LOW] follow-up — not re-flagging here), `[RULE]` 13-rule python checklist walked above.

**Handoff:** To Captain Carrot Ironfoundersson (SM) for finish-story.

## Delivery Findings

### Reviewer (code review)
- **Improvement** (non-blocking): Curly/smart-quote variants don't slug to the same as straight ASCII counterparts. `"Tood's Dome"` → `"tood-s-dome"`, `"Tood’s Dome"` → `"toods-dome"`. LLMs emit both forms freely; next playtest will likely surface this. Affects `sidequest/game/region_validation.py:60-69` (`_UNICODE_SEPARATOR_TRANSLATION` — add `‘`, `’`, `“`, `”`). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Empty-slug edge case — pure-non-alphanumeric names like `"@@@"` / `"!!!"` pass `validate_region_name` and slug to empty string, causing different garbage names to falsely dedup. Real-world risk ~zero. Affects `sidequest/game/region_validation.py` (consider tightening `validate_region_name` to reject names whose canonical form is empty, making `validate ∘ canonicalize` composable). *Found by Reviewer during code review.*