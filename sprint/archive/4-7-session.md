---
story_id: "4-7"
jira_key: "none"
epic: "4"
workflow: "tdd"
---
# Story 4-7: TTS text segmentation — break narration into speakable segments for streaming delivery

## Story Details
- **ID:** 4-7
- **Jira Key:** none
- **Workflow:** tdd
- **Stack Parent:** 4-6 (feat/4-6-tts-voice-routing)
- **Points:** 3
- **Priority:** p1

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-03-26T19:23:41Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-26T00:00:00Z | 2026-03-26T19:04:10Z | 19h 4m |
| red | 2026-03-26T19:04:10Z | 2026-03-26T19:07:37Z | 3m 27s |
| green | 2026-03-26T19:07:37Z | 2026-03-26T19:13:37Z | 6m |
| spec-check | 2026-03-26T19:13:37Z | 2026-03-26T19:14:24Z | 47s |
| verify | 2026-03-26T19:14:24Z | 2026-03-26T19:17:20Z | 2m 56s |
| review | 2026-03-26T19:17:20Z | 2026-03-26T19:22:57Z | 5m 37s |
| spec-reconcile | 2026-03-26T19:22:57Z | 2026-03-26T19:23:41Z | 44s |
| finish | 2026-03-26T19:23:41Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No upstream findings during test design.

## Impact Summary

**Upstream Effects:** No upstream effects noted
**Blocking:** None

### Deviation Justifications

3 deviations

- **Added Segment struct with metadata beyond Python parity**
  - Rationale: Streaming TTS needs segment ordering and position tracking for chunked delivery; plain strings lose this context
  - Severity: minor
  - Forward impact: Dev must implement Segment struct, not just return Vec<String>
- **Split abbreviation set into title vs terminal categories**
  - Rationale: Tests require "Mr. Smith" to NOT split but "etc. The" to split; Python regex lookahead handles this differently but Rust regex lacks lookahead
  - Severity: minor
  - Forward impact: none — behavior matches test expectations
- **Replaced regex lookahead with character scanning**
  - Rationale: Rust `regex` crate does not support lookahead/lookbehind; functionally equivalent
  - Severity: minor
  - Forward impact: none — same boundary detection, different mechanism

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Added Segment struct with metadata beyond Python parity**
  - Spec source: Python daemon segmenter.py
  - Spec text: Python returns `list[str]` — plain strings only
  - Implementation: Rust returns `Vec<Segment>` with `text`, `index`, `byte_offset`, `is_last` fields
  - Rationale: Streaming TTS needs segment ordering and position tracking for chunked delivery; plain strings lose this context
  - Severity: minor
  - Forward impact: Dev must implement Segment struct, not just return Vec<String>

### Dev (implementation)
- **Split abbreviation set into title vs terminal categories**
  - Spec source: Python daemon segmenter.py
  - Spec text: Python uses a single `_ABBREVIATIONS` frozenset — all treated identically
  - Implementation: Split into `TITLE_ABBREVIATIONS` (Mr., Dr., etc. — never split) and `OTHER_ABBREVIATIONS` (etc., vs. — split when followed by capital letter)
  - Rationale: Tests require "Mr. Smith" to NOT split but "etc. The" to split; Python regex lookahead handles this differently but Rust regex lacks lookahead
  - Severity: minor
  - Forward impact: none — behavior matches test expectations

- **Replaced regex lookahead with character scanning**
  - Spec source: Python daemon segmenter.py
  - Spec text: Python uses `re.compile` with lookahead/lookbehind (`(?=...)`, `(?<!...)`)
  - Implementation: Manual character-by-character scanning with helper functions (`find_split_points`, `is_followed_by_ws_and_capital`)
  - Rationale: Rust `regex` crate does not support lookahead/lookbehind; functionally equivalent
  - Severity: minor
  - Forward impact: none — same boundary detection, different mechanism

### Architect (reconcile)
- No additional deviations found.
  - Forward impact: none — same boundary detection, different mechanism

## Sm Assessment

**Story:** 4-7 — TTS text segmentation (3pts, p1)
**Workflow:** tdd (phased)
**Repos:** sidequest-api (branch: feat/4-7-tts-text-segmentation)
**Dependencies:** 4-6 (TTS voice routing) — completed, merged to develop

**Routing:** Tyr One-Handed (TEA) for RED phase — write failing tests for narration-to-segment splitting.

**Context:** This story breaks narration text into speakable segments for streaming TTS delivery. Builds on the voice routing infrastructure from 4-6. The daemon's TTS pipeline needs properly segmented input to stream audio chunks without awkward mid-sentence breaks.

**Jira:** Skipped (personal project, no Jira integration).

## Tea Assessment

**Tests Required:** Yes
**Reason:** Core text processing logic with many edge cases — needs thorough coverage

**Test Files:**
- `crates/sidequest-game/tests/tts_segmentation_story_4_7_tests.rs` — 29 tests for SentenceSegmenter

**Tests Written:** 29 tests covering 6 ACs + metadata + narrative patterns + Python parity
**Status:** RED (compilation failure — `segmenter` module does not exist)

### Test Coverage by AC

| AC | Tests | Description |
|----|-------|-------------|
| AC-1 | 3 | Basic sentence splitting (1, 2, 3 sentences) |
| AC-2 | 5 | Abbreviation handling (Mr., Dr., Mrs., Gen./Lt./Col., etc.) |
| AC-3 | 3 | Exclamation marks, question marks, mixed punctuation |
| AC-4 | 3 | Ellipsis (ASCII ..., Unicode …, continuation without capital) |
| AC-5 | 3 | Quoted speech (straight quotes, smart quotes, period+quote) |
| AC-6 | 5 | Edge cases (empty, whitespace, no punctuation, trimming, newlines) |
| Metadata | 4 | Sequential indices, byte offsets, is_last flag |
| Narrative | 3 | Dialogue attribution, long narration, combat text |
| Parity | 3 | Python SentenceSegmenter equivalence checks |

### Rule Coverage

No lang-review rules file exists for this project. Tests enforce:
- Validated constructor pattern (SentenceSegmenter::new())
- Struct with named fields (Segment has text, index, byte_offset, is_last)
- Empty/whitespace input handling (returns empty Vec, not panic)

**Self-check:** 0 vacuous tests found. All 29 tests have meaningful assert_eq!/assert! calls checking specific values.

### Dev Instructions

1. Create `crates/sidequest-game/src/segmenter.rs` with:
   - `SentenceSegmenter` struct with `new()` constructor
   - `Segment` struct: `{ text: String, index: usize, byte_offset: usize, is_last: bool }`
   - `segment(&self, text: &str) -> Vec<Segment>` method
2. Add `pub mod segmenter;` to `crates/sidequest-game/src/lib.rs`
3. Port regex logic from Python `sidequest_daemon/voice/segmenter.py`
4. Export `SentenceSegmenter` and `Segment` from lib.rs

**Handoff:** To Loki Silvertongue (Dev) for GREEN phase

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-game/src/segmenter.rs` — SentenceSegmenter with character-scanning boundary detection
- `crates/sidequest-game/src/lib.rs` — added `pub mod segmenter` and re-exports

**Tests:** 33/33 passing (GREEN)
**Branch:** feat/4-7-tts-text-segmentation (pushed)

**Implementation Notes:**
- Rust `regex` crate lacks lookahead/lookbehind, so replaced Python regex with manual character scanning
- Split abbreviations into title (never split) vs terminal (split when followed by new sentence) to match test expectations
- Zero-copy where possible, `LazyLock` for static initialization

**Handoff:** To next phase (verify/review)

### Dev (implementation)
- No upstream findings during implementation.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

The implementation faithfully ports the Python `SentenceSegmenter` to Rust with appropriate adaptations:
- Character-scanning replaces regex lookahead (Rust `regex` limitation) — functionally equivalent
- Abbreviation split into title/terminal categories is a sound design decision that produces correct behavior
- `Segment` struct with metadata (`index`, `byte_offset`, `is_last`) is a valuable enhancement for streaming delivery

All 33 tests pass. Both TEA and Dev deviations are properly logged with complete 6-field format. No story/epic context files exist to check against — session file is the sole spec authority.

**Decision:** Proceed to verify

## Tea Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 2

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 1 finding | Duplicate helper logic (high confidence) |
| simplify-quality | 5 findings | unwrap() safety (2 high, 2 medium, 1 low) |
| simplify-efficiency | 2 findings | Redundant find() (high), duplicate helper (medium) |

**Applied:** 3 high-confidence fixes
- Extracted `trimmed_segment` helper to eliminate duplicate offset calculation
- Consolidated `is_followed_by_ws_and_capital`/`is_followed_by_ws_and_opening_quote` into shared `is_followed_by_ws_and` with predicate
- Replaced `unwrap()` with `if let`/`map_or` for defensive safety

**Flagged for Review:** 0 medium-confidence findings (medium items were subsumed by the high-confidence consolidation)
**Noted:** 2 low-confidence observations (manual Default impl, unused re-exports — no action)
**Reverted:** 0

**Overall:** simplify: applied 3 fixes

**Quality Checks:** 33/33 tests passing
**Handoff:** To Heimdall (Reviewer) for code review

### TEA (test verification)
- No upstream findings during test verification.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 1 new clippy lint, 1 unused import | Fixed lint, dismissed import |
| 2 | reviewer-edge-hunter | Yes | findings | 7 | Fixed byte offset calc, noted test gaps |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 2 | Subsumed by edge-hunter fix |
| 4 | reviewer-test-analyzer | Yes | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Yes | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Yes | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Yes | findings | 7 | Fixed sort/dedup, deferred optimizations |
| 9 | reviewer-rule-checker | Yes | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (4 returned with results, 5 disabled via settings)

## Reviewer Assessment

**PR:** slabgorb/sidequest-api#47 (merged)
**Verdict:** APPROVED with 3 fixes applied

### Finding Decisions

**Confirmed:**
1. [EDGE] `find(trimmed)` semantically wrong for byte offset (line 102) — `str::find` returns first substring match, not trim offset. Fixed: use `slice.len() - slice.trim_start().len()`. Severity: **HIGH**.
2. [EDGE] Unnecessary `sort_unstable+dedup` on already-ordered splits vec (line 210) — O(n log n) no-op. Fixed: replaced with `debug_assert!`. Severity: **MEDIUM**.
3. [EDGE] `map_or(false, ...)` → `is_some_and(...)` clippy lint (line 225). Fixed. Severity: **LOW**.

**Dismissed:**
- [SILENT] `unwrap_or(0)` masks invariant (line 102) — DISMISSED: subsumed by fix #1 which eliminates `find()` entirely.
- [SILENT] `total - 1` unsigned subtraction risk (line 83) — DISMISSED: control flow guarantees `total >= 1` for non-whitespace input; early return on line 55 guards empty case.
- [EDGE] Zero-sized struct "wrapper-no-value" — DISMISSED: follows crate convention (SubjectExtractor, BeatFilter are same pattern).
- [EDGE] No-space adjacency `Hello.World` not splitting — DISMISSED: intentional for TTS narration; no whitespace = no sentence boundary.

**[RULE] findings:** None — no lang-review rules file exists for this project. reviewer-rule-checker was disabled.

**Deferred:**
- [EDGE] `word_before_dot` double-reverse allocation — deferred, correct behavior, optimization for future.
- [EDGE] `char_indices` Vec allocation — deferred, needed for lookahead/lookbehind pattern.
- [EDGE] No multibyte UTF-8 byte_offset test — deferred, test gap not code bug.
- [EDGE] Four-dot `....` and double punctuation `!!` untested — deferred, edge cases for future hardening.

**Fixes Applied:** 3 (byte offset calculation, sort/dedup removal, clippy lint)
**Tests:** 33/33 GREEN after fixes
**Handoff:** To Baldur the Bright (SM) for finish