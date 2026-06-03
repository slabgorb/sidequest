---
story_id: "72-15"
jira_key: ""
epic: "72"
workflow: "trivial"
---
# Story 72-15: Rescue test_pregen.py from the caverns_sunden blanket-skip + fix stale _stub_pack

## Story Details
- **ID:** 72-15
- **Jira Key:** (none — personal project)
- **Workflow:** trivial
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-06-03T19:19:32Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-03T19:02:16Z | 2026-06-03T19:05:08Z | 2m 52s |
| implement | 2026-06-03T19:05:08Z | 2026-06-03T19:15:12Z | 10m 4s |
| review | 2026-06-03T19:15:12Z | 2026-06-03T19:19:32Z | 4m 20s |
| finish | 2026-06-03T19:19:32Z | - | - |

## Sm Assessment

**Setup complete — handing implement to Ponder Stibbons (Dev).**

Trivial test-debt story (2pt, server, tests + conftest only — **no production
change**). Goal: un-skip the ~16 world-agnostic `seed_manual` unit tests that
`tests/conftest.py:217` sweeps into `_CAVERNS_SUNDEN_DEPRECATED_TESTS` because one e2e
binds the deprecated `caverns_sunden` world.

Three moves, all premise-verified against the live tree during setup:
1. Fix stale `_stub_pack` (test_pregen.py:185) — it exposes `.cultures` but
   `seed_manual` now calls `pack.effective_cultures(world)` (pregen.py:223), which
   returns a **2-tuple** `(effective, cultures_source)` — stub must match that arity.
2. Re-point the e2e (`test_e2e_seed_caverns_sunden_populates_manual`, :408) to a
   **dedicated test fixture** pack/world — **operator decision 2026-06-03: a FIXTURE,
   NOT a live world** (coyote_star/caverns_and_claudes are mid-migration per 71-31).
   Dev should reuse-first: check `tests/` for an existing fixture pack before authoring.
3. Remove `test_pregen.py` from the conftest skip set.

Guardrails: do NOT revive caverns_sunden, do NOT touch production code, do NOT couple
the e2e to live content. Context: `sprint/context/context-story-72-15.md` (validated).
Branch `feat/72-15-rescue-test-pregen-skip` (server, off develop).

## Dev Assessment

**Implementation Complete:** Yes (tests + fixtures only — no production change)

**Files Changed (sidequest-server):**
- `tests/server/dispatch/test_pregen.py` — `_stub_pack` gains `effective_cultures(world)`
  returning the 2-tuple `(cultures, source)` the live `seed_manual` expects
  (pregen.py:223); e2e re-pointed from `caverns_and_claudes/caverns_sunden` →
  `test_genre/flickering_reach`, `CONTENT_ROOT`/`_real_content_available` (caverns-only,
  now dead) replaced by `FIXTURE_PACKS`; module docstring + test name updated.
- `tests/fixtures/packs/test_genre/worlds/flickering_reach/cultures.yaml` — the four
  cultures' `given_name` slots (and Drifters' `patronymic`) converted from `corpora`
  (Markov, needs absent corpus files) → `word_list`, so real namegen seeds hermetically.
- `tests/conftest.py` — `test_pregen.py` removed from `_CAVERNS_SUNDEN_DEPRECATED_TESTS`
  with a documented reversible-with-reason note.

**Approach:** Reuse-first per the context — re-used the existing `test_genre` fixture
pack + its `flickering_reach` world (which already ships `creatures.yaml`, so
encountergen worked out of the box) rather than authoring a new pack. The only gap was
namegen's corpus dependency, closed by the word_list conversion. Empirically verified
the fixture seeds end-to-end before wiring the assertions.

**Tests:** `tests/server/dispatch/test_pregen.py` — **17 passed** (was 100% skipped).
Regression scope `tests/server/dispatch/ + cli/test_encountergen* + genre/test_pack_effective_cultures`
— **205 passed, 25 skipped**, no regressions. Integration tests that reference
`flickering_reach` bind the **real** `mutant_wasteland/flickering_reach` (not the
edited fixture), so they are unaffected. Lint + format clean on changed `.py` files.

**Branch:** `feat/72-15-rescue-test-pregen-skip` (pushed, c4e417ed).
**Handoff:** To Granny Weatherwax (Reviewer).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean (GREEN) | none | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (1 enabled subagent returned GREEN; 8 disabled via `workflow.reviewer_subagents`)
**Total findings:** 0 confirmed defects, 0 dismissed, 0 deferred (1 LOW observation noted below)

## Reviewer Assessment

**Verdict:** APPROVED

A clean, correctly-scoped test-debt rescue. The previously-skipped `test_pregen.py`
now runs (17 tests, was 100% skipped), pregen — a **live** subsystem — regains its
unit + e2e coverage, and the change touches only test files + one fixture world, with
no production code. Preflight GREEN; my own adversarial checks confirm isolation. No
Critical/High issues.

**Observations (tagged):**

- `[VERIFIED]` `_stub_pack.effective_cultures` matches the live contract — returns the
  2-tuple `(culture_objs, "stub")`; `seed_manual` unpacks `effective, cultures_source`
  and does `[c.name for c in effective]` (pregen.py:223/229), and `culture_objs` are
  `SimpleNamespace(name=...)`. The 6 `seed_manual` unit tests pass, including the
  empty-cultures fallback path. Evidence: test_pregen.py:185-200; 17/17 green.
- `[VERIFIED]` Fixture cultures.yaml fully converted — 0 slots still reference
  `corpora` (all four `given_name` + Drifters' `patronymic` now `word_list`, 10 names
  each); valid YAML, 4 cultures intact. So real namegen seeds with no corpus file.
  Evidence: yaml.safe_load probe → `slots still using corpora: []`.
- `[VERIFIED]` Skip genuinely removed — no `"server/dispatch/test_pregen.py"` entry
  remains in `_CAVERNS_SUNDEN_DEPRECATED_TESTS`; only a documented reversible-with-reason
  comment (conftest.py:217), matching the block's existing 59-16 convention. Preflight
  reports 0 skips on the module.
- `[VERIFIED]` No dangling references — `CONTENT_ROOT` / `_real_content_available`
  (caverns-only, now dead) removed; the sole remaining `caverns` mention is an
  explanatory comment at test_pregen.py:39, not code. No dead code left behind.
- `[VERIFIED]` Isolation — the fixture edit cannot affect live-content tests: the
  integration tests referencing `flickering_reach` bind **real `mutant_wasteland`**,
  not the `test_genre` fixture; `test_pack_effective_cultures` (3 tests) + dispatch
  (198) pass unchanged. Evidence: preflight regression scope green.
- `[SIMPLE]` (self-assessed) **LOW, acceptable:** the e2e asserts `len(manual.npcs) >= 1`
  rather than the full 4×3 seed — it could pass if namegen mostly failed. But this
  preserves the original e2e's assertion strength (it was `>= 1` against caverns_sunden
  too), the per-culture counts are pinned by the unit tests, and word_list dedup makes
  an exact count fragile. Appropriate for an e2e smoke; not a regression.

**Dispatch-tag coverage** (gate requires all 8; 8 specialists disabled, assessed by me):
- `[EDGE]` Empty-cultures path covered by `test_seed_manual_no_cultures_falls_back`
  (stub returns `([], "stub")` → fallback count). No new boundary risk. (disabled)
- `[SILENT]` No swallowed errors introduced — the stub's lambda raises naturally if
  misused; no try/except added. (disabled)
- `[TEST]` This story IS test work — assertions are meaningful (count/state/tier
  checks), no vacuous asserts added; the rescued tests pin real `seed_manual` behavior. (disabled)
- `[DOC]` Module docstring + test name + conftest comment all updated to match the
  re-point; accurate. (disabled)
- `[TYPE]` `effective_cultures` lambda returns the correct tuple shape; stub uses
  `SimpleNamespace` (test-only, no production type contract). (disabled)
- `[SEC]` No security surface — test fixtures only. (disabled)
- `[SIMPLE]` Reuse-first (existing fixture, no new pack); minimal change. See LOW above. (disabled)
- `[RULE]` Honors CLAUDE.md "no skipping tests for live subsystems" (pregen is live) and
  "tests must not point at live content" (fixture, not a live world). Compliant. (disabled)

### Rule Compliance

- **"No skipping tests for live subsystems"** (CLAUDE.md): **now compliant** — this is
  the rule the story restores; pregen's tests run again.
- **"Tests must not point at live content"** (project doctrine): **compliant** — the
  e2e binds the `test_genre` fixture, not a live genre-pack world.
- **"Delete dead code in the same PR"** (CLAUDE.md): **compliant** — `CONTENT_ROOT` and
  `_real_content_available` removed when they became caverns-only dead code.
- **"No source-text wiring tests"**: **n/a** — no wiring assertions added; behavior tests.
- **ruff lint/format**: **compliant** — preflight PASS on both changed `.py` files.

### Devil's Advocate

Assume this rescue is broken. First attack: un-skipping a file that was dark for a
reason — maybe those ~16 unit tests rot-passed only in isolation and leak state in the
full suite. But they monkeypatch `load_genre_pack` and mock `Path.home`, so each is
hermetic; preflight ran the whole `tests/server/dispatch/` package (198) green, not just
the file alone. Second attack: the `word_list` conversion silently changed the fixture's
naming *model* (Markov → sampling), so any test asserting Markov-style or corpus-derived
names from `flickering_reach` would now get fixed word-list names. I checked — no suite
asserts on these corpora, and the only `flickering_reach` integration consumers bind the
*real* `mutant_wasteland` world, untouched. Third attack: `effective_cultures` returns a
hardcoded `"stub"` source; if a rescued test (or a future one) asserted
`cultures_source == "world"`, it would break. None of the current 17 do, and the stub is
explicitly a unit-level stand-in. Fourth attack: removing the `skipif(not _real_content_available())`
means the e2e now always runs — could it fail on a machine without sidequest-content?
No: it deliberately moved *off* live content onto the in-repo fixture, which is always
present, so "always runs" is the intended improvement. Fifth: the weak `>= 1` assertion
could mask a namegen that seeds only one of twelve — real but low-severity, and
characterization-preserving (covered above). Nothing here rises to blocking; the change
does exactly what it claims and the doctrine it restores is the right one.

**Handoff:** To SM (Captain Carrot) for finish-story. No code change; one Dev deviation
audited-and-accepted; one LOW observation, non-blocking.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Improvement** (non-blocking): The shared test corpus fallback dir
  `tests/fixtures/corpus/shared/` does not exist, so any fixture culture using
  `corpora:` (Markov) fails namegen in tests. Other fixtures may hit this latently.
  Affects test fixtures (consider a tiny shared corpus set or a word_list convention
  for fixtures). *Found by Dev during implementation.*

### Reviewer (code review)
- **Improvement** (non-blocking): The re-pointed e2e asserts `len(manual.npcs) >= 1`,
  which could pass if namegen seeded only 1 of the expected 4×3. A future hardening
  could assert the per-culture seed count (mindful of word_list dedup). Non-blocking;
  characterization-preserving (the original was also `>= 1`). Affects
  `tests/server/dispatch/test_pregen.py`. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Edited the chosen fixture world's cultures.yaml (corpora → word_list) to make the e2e namegen hermetic**
  - Spec source: `sprint/context/context-story-72-15.md`, Assumptions + AC3
  - Spec text: "re-point the deprecated e2e to a DEDICATED TEST FIXTURE pack/world …
    Dev to check `tests/` for an existing fixture pack before authoring a new one
    (reuse-first)."
  - Implementation: Reused the existing `test_genre/flickering_reach` fixture, but its
    world cultures referenced corpus files (`english/german/finnish/...`) absent from
    the (non-existent) `tests/fixtures/corpus/shared/` fallback, so real namegen seeded
    0 NPCs. Converted the four `given_name` slots + Drifters' `patronymic` from
    `corpora` to `word_list` so namegen runs without corpus files.
  - Rationale: keeps the e2e a *real-subprocess* integration (namegen + encountergen
    actually run) while staying hermetic and corpus-free — lighter than adding 7 corpus
    files or authoring a brand-new pack, and isolated to a fixture world.
  - Severity: minor
  - Forward impact: none — `test_genre/flickering_reach` is a test fixture; no live
    content and no other suite asserts on its culture corpora (verified: the only
    `flickering_reach` integration consumers bind real `mutant_wasteland`).

### Reviewer (audit)
- **Dev — "Edited the chosen fixture world's cultures.yaml (corpora → word_list)"** →
  ✓ ACCEPTED by Reviewer: sound and isolated. Independently verified — 0 slots still
  reference corpora, no other suite asserts on these corpora, and `flickering_reach`
  integration consumers bind the real `mutant_wasteland` world (untouched). Lighter
  than adding 7 corpus files or authoring a new pack, and it keeps the e2e a real
  namegen+encountergen run. Good reuse-first call.
- No undocumented deviations found — the diff matches the logged scope (3 files, tests
  + fixture only, no production change).