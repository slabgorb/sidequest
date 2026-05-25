# Story 61-10 — Promote six byte-static narrator prose sections into the System-bucket cache

**Story ID:** 61-10
**Epic:** 61 — Bounded Narrator Prompt: Slim Snapshot + Wire RAG
**Points:** 2
**Priority:** p1
**Workflow:** tdd
**Phase:** finish
**Repos:** server
**Branch:** feat/61-10-promote-byte-static-narrator-prose
**Jira:** n/a
**Assigned:** slabgorb
**Started:** 2026-05-25

## Description

Six byte-static narrator prose sections currently land in the User bucket (re-sent in full on every turn) despite meeting STABLE_SECTION_NAMES' own criterion — "byte-identical across every turn of the same game". Total: ~764 tok/turn that could ride the cached system prefix as a one-time cost.

Sections to promote (sources at `narrator_prompts/*.md`, all loaded byte-exact by `narrator_prompts/__init__.py`):
- `narrator_constraints` (constraints.md, ~112 tok)
- `narrator_agency` (agency.md, ~201 tok)
- `narrator_consequences` (consequences.md, ~71 tok)
- `narrator_pov_rules` (pov_rules.md, ~200 tok)
- `narrator_referral_rule` (referral_rule.md, ~65 tok)
- `narrator_output_style` (output_style.md, ~115 tok)

The change is a single frozenset edit at `sidequest/agents/prompt_framework/bucket.py:28` plus a regression test asserting each section now lands in `SectionBucket.System`.

Cost: one cache-prefix invalidation on first deploy.
Benefit: ~764 tok/turn savings amortized after turn 1.

## Acceptance Criteria

- [ ] AC-1: All six sections appear in STABLE_SECTION_NAMES in `prompt_framework/bucket.py`
- [ ] AC-2: `default_bucket_for_section` returns `SectionBucket.System` for each of the six names
- [ ] AC-3: A regression test in `tests/agents/test_prompt_framework/test_bucket.py` asserts each name maps to System and is included in a snapshot of STABLE_SECTION_NAMES
- [ ] AC-4: An OTEL span on the next playtest's first narrator turn confirms `system_blocks` contains the six new sections and `user_message` does not (per the dashboard's Prompt panel zone breakdown)
- [ ] AC-5: Total per-turn token count of the `user_message` (post-warmup, neutral action) drops by at least ~700 tok versus a baseline turn captured immediately before the change

## Key Files

- `sidequest-server/sidequest/agents/prompt_framework/bucket.py` — STABLE_SECTION_NAMES frozenset
- `sidequest-server/sidequest/agents/narrator_prompts/__init__.py` — section loader
- `sidequest-server/sidequest/agents/narrator_prompts/*.md` — prose source files
- `sidequest-server/tests/agents/test_prompt_framework/test_bucket.py` — regression tests

## Workflow Tracking

| Phase | Agent | Status | Entered |
|-------|-------|--------|---------|
| setup | sm | active | 2026-05-25 |
| red | tea | pending | |
| green | dev | pending | |
| spec-check | architect | pending | |
| verify | tea | pending | |
| review | reviewer | pending | |
| spec-reconcile | architect | pending | |
| finish | sm | pending | |

## Sm Assessment

**Setup Complete:** Yes
**Session File:** .session/61-10-session.md
**Branch:** feat/61-10-promote-byte-static-narrator-prose (sidequest-server, off develop)
**Context:** sprint/context/context-story-61-10.md
**Workflow:** tdd (phased)
**Handoff:** To Igor (TEA) for RED phase — write failing tests for the six STABLE_SECTION_NAMES additions

## Tea Assessment

**Tests Written:** 9 (all FAILING — RED state confirmed)
**Pre-existing Tests:** 9 (all PASSING — no regression)
**Test File:** `tests/agents/test_prompt_framework/test_bucket.py`
**Commit:** `3a0a43c`

**Test Coverage by AC:**
- AC-1: `test_all_six_in_stable_section_names` — asserts all six names in frozenset
- AC-2: `test_each_resolves_to_system_bucket` — iterates all six, asserts System bucket
- AC-3: `test_minimum_contents_includes_promoted_sections` — full snapshot including the six
- AC-4/5: Playtest validation — not testable in CI, post-merge confirmation

**Per-section pins (6 tests):** Each section has its own test for regression isolation — if one is accidentally removed, the per-section test names which one.

**Rule Coverage:**
- Meaningful assertions: every test asserts bucket membership AND routing result
- No vacuous assertions: no `let _ =`, no `assert True`
- Wiring: tests import production `STABLE_SECTION_NAMES` and `default_bucket_for_section` directly

**Handoff:** To Ponder Stibbons (Dev) for GREEN phase — add the six names to `STABLE_SECTION_NAMES` frozenset in `bucket.py`

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/agents/prompt_framework/bucket.py` — added six names to STABLE_SECTION_NAMES frozenset

**Tests:** 18/18 passing (GREEN)
**Branch:** feat/61-10-promote-byte-static-narrator-prose (pushed)

**Handoff:** To Leonard of Quirm (Architect) for spec-check phase

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

AC-1 through AC-3 are satisfied by the frozenset edit and the 9 regression tests. AC-4/5 are post-merge playtest validation per the story context ("AC-4/5 require a live playtest... not blocking for the code change itself"). The six section names in the code match the six in the spec exactly. The comment block is appropriately concise and references the story ID + rationale for the omission.

**Decision:** Proceed to verify

## Tea Assessment (verify)

**Tests:** 18/18 passing (GREEN confirmed)
**Lint:** ruff check clean
**Format:** ruff format applied (1 file, committed as `879ae22`)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 2

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 1 finding | per-section test duplication (dismissed — deliberate regression isolation) |
| simplify-quality | clean | no issues |
| simplify-efficiency | 4 findings | 2 dismissed (same rationale), 2 flagged for review (minor overlap, class wrapper) |

**Applied:** 0 fixes (formatting fix was a separate ruff-format correction)
**Flagged for Review:** 2 medium-confidence observations (aggregate test overlap, class wrapper)
**Reverted:** 0

**Overall:** simplify: clean — all high-confidence findings are deliberate design choices matching the existing test pattern

**Handoff:** To Granny Weatherwax (Reviewer) for review phase

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 18/18 tests green, lint clean, format clean | N/A |
| 2 | reviewer-edge-hunter | Yes | 2 findings | (1) `narrator_dialogue` in STABLE but no registration site — pre-existing, not from this PR; (2) other conditionally-registered .md sections left demoted — correct per ADR-112 §Defer | (1) Log as delivery finding; (2) Dismiss — conditional registration is incompatible with Stable |
| 3 | reviewer-security | Yes | clean | No security concerns — change adds string literals to a frozenset, no user input, no injection surface | N/A |

All received: Yes

## Reviewer Assessment

**Decision:** APPROVE
**Findings:** None

The change is surgical and correct. Verified:
- All six sections are unconditionally registered in `narrator.py:build_prompt()` (lines 174-248) with no conditional guards
- Content is loaded at import time via `narrator_prompts/__init__.py:_load()` — byte-identical across turns
- Section names match exactly between `bucket.py` additions and `narrator.py` registrations
- 18/18 tests pass including 9 new regression pins
- Lint and format clean

AC-1/2/3 are satisfied by code + tests. AC-4/5 are post-merge playtest validation (not blocking).

[SEC] No security concerns — adds string literals to a frozenset with no user input or injection surface.

## Design Deviations

### TEA (red)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

### Architect (reconcile)
- No additional deviations found.

## Delivery Findings

### TEA (red)
- No upstream findings during implementation.

### Dev (implementation)
- No upstream findings during implementation.

### Reviewer (review)
- **Gap** (non-blocking): `narrator_dialogue` appears in `STABLE_SECTION_NAMES` and `test_allowlist_minimum_contents` but no code registers a section with this exact name. `narrator_dialogue_rules` IS registered (in `build_dialogue_context`). Pre-existing issue, not introduced by this PR. Affects `sidequest/agents/prompt_framework/bucket.py` (may be a stale entry or a naming mismatch). *Found by Reviewer edge-hunter during review.*