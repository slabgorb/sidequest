---
story_id: "84-7"
jira_key: ""
epic: ""
workflow: "tdd"
---
# Story 84-7: WI-5 follow-up — epithet extractor POS hardening (replace -s verb heuristic) before §A4 faction/location alias reuse

## Story Details
- **ID:** 84-7
- **Jira Key:** (none — personal project, no Jira)
- **Workflow:** tdd
- **Stack Parent:** none
- **Type:** refactor
- **Points:** 3
- **Priority:** p3

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-11T09:13:44Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-11T08:48:55Z | 2026-06-11T08:51:46Z | 2m 51s |
| red | 2026-06-11T08:51:46Z | 2026-06-11T08:57:51Z | 6m 5s |
| green | 2026-06-11T08:57:51Z | 2026-06-11T09:09:03Z | 11m 12s |
| review | 2026-06-11T09:09:03Z | 2026-06-11T09:13:44Z | 4m 41s |
| finish | 2026-06-11T09:13:44Z | - | - |

## Workflow Details

**Branch Strategy:** gitflow (feat/84-7-epithet-extractor-pos-hardening)
**Base Branch:** develop
**Repository:** sidequest-server

## Story Context

**Title:** WI-5 follow-up — epithet extractor POS hardening (replace -s verb heuristic) before §A4 faction/location alias reuse

**Description:** WI-5 follow-up: harden the epithet extractor's POS handling (replace the -s verb heuristic) before §A4 faction/location alias reuse.

ADDED 2026-06-10 (Keith): the intent router's reference/alias matching must ALSO honor the SAME NFKD-fold normalization adopted in Story 101-8 for slugs. 101-8 unified slug derivation onto a shared stdlib NFKD fold (unicodedata.normalize('NFKD', …) + strip combining marks; ASCII unchanged, diacritics → base letters). Entity retrieval in the intent router (faction/location/NPC alias + epithet matching, ADR-118 §A4) currently risks the same diacritic split-brain: a diacritic-named entity (evropi, coyote_star) won't match its alias if one side folds and the other drops/keeps the accent. Reuse the SAME shared fold helper 101-8 introduces — do not add a second normalization rule.

**Acceptance Criteria:**
- Intent-router reference/alias matching (faction/location/NPC epithet + alias resolution, ADR-118 §A4) normalizes candidate names through the SAME shared NFKD-fold helper introduced in Story 101-8 — a diacritic-named entity resolves its alias regardless of accent. Verified by a fixture/OTEL test with a diacritic entity (no source-text grep), and the normalization is the shared 101-8 helper, NOT a re-implemented rule.

## Technical Notes

### Shared Helper Location
The NFKD-fold helper for alias matching is already implemented and merged:
- **File:** `sidequest/server/slug_fold.py`
- **Function:** `fold_to_ascii(text: str) -> str`
- **Source:** Story 101-8 (PR #789, commit 7275e531)
- **Behavior:** NFKD decomposes precomposed letters (é→e, ñ→n, etc.) and strips combining marks. No lowercasing or separator handling — callers apply those.

### Current Intent Router Location
Intent routing and reference/alias matching logic:
- **File:** `sidequest/agents/intent_router.py`
- **Related:** ADR-118 §A4 (faction/location/NPC alias + epithet matching)

### Key Requirement
- REUSE the existing `fold_to_ascii()` helper from `slug_fold.py`
- DO NOT create a second normalization function
- Update intent router alias/epithet matching to apply the fold before comparison
- Add fixture/OTEL test with a diacritic entity (e.g., "Evropi" or "Coyote Star") to verify the fix

## Sm Assessment

**Routing:** Phased tdd, single repo (sidequest-server). RED → Fezzik (TEA) next. Merge gate clear (no open server PRs). Branch `feat/84-7-epithet-extractor-pos-hardening` created off develop.

**Dependency is satisfied in code (despite the tracker).** The story names Story 101-8's shared NFKD-fold helper as its foundation. 101-8 shows `backlog` in the sprint tracker, but the helper **is live**: `fold_to_ascii(text)` in `sidequest/server/slug_fold.py`, merged via PR #789 (commit `7275e531`). This is stale-tracker drift, NOT a blocker — 84-7 may proceed. (Flagged to Keith; reconcile 101-8 status separately.)

**Two-part scope — keep them distinct:**
1. **POS hardening** — replace the brittle "-s ending ⇒ verb" heuristic in the epithet extractor. Epithet logic touches `sidequest/agents/npc_context.py` and the `sidequest/game/alias_*.py` family; TEA/Dev to pinpoint the exact heuristic.
2. **Fold reuse** — §A4 faction/location/NPC alias + epithet matching must normalize candidates through the SAME `fold_to_ascii` helper. **Measured gap:** `fold_to_ascii` today has callers ONLY in slug surfaces (`server/utils.py`, `server/reference_slug.py`) — **none in the alias/intent-router path**. §A4 matching is in `sidequest/game/alias_resolution.py` + `alias_accretion.py`. The fix is wiring the existing helper into that comparison path.

**Load-bearing constraints for RED/GREEN:**
- REUSE `fold_to_ascii` — do NOT add a second normalization rule (explicit Keith directive).
- AC demands a **fixture/OTEL test with a real diacritic entity** (evropi / coyote_star), NOT a source-text grep, as the wiring proof. The diacritic entity must resolve its alias regardless of accent on either side.
- Watch the project trap (from prior firewall stories): `json.dumps` with `ensure_ascii=True` escapes non-ASCII, making substring asserts vacuous — assert structurally or set `ensure_ascii=False`.

## Delivery Findings

### RED phase (TEA / Fezzik) — 2026-06-11

**Test file:** `sidequest-server/tests/game/test_alias_diacritic_fold_and_pos.py`
**RED result:** 8 failed (drivers), 4 passed (guards). All failures are clean `AssertionError`s (feature missing), no collection/import errors.

Run: `SIDEQUEST_DATABASE_URL=postgresql://$USER@localhost:5432/sidequest_test uv run pytest tests/game/test_alias_diacritic_fold_and_pos.py -p no:randomly -q`

**Two seams Dev must touch (GREEN):**
1. **PRIMARY — `sidequest/game/alias_resolution.py` `_phrase_matches` / `resolve_mention`.** Apply `fold_to_ascii` (from `sidequest.server.slug_fold`) to BOTH the candidate phrase AND `action_text` before the existing `\b…\b` IGNORECASE regex. Folding both sides is required (a plain-ASCII name must resolve an accented reference, and vice-versa). This is the single load-bearing change; the live seam `player_referenced_npcs_from_action` (npc_context.py) delegates to `resolve_mention`, so fixing the resolver fixes the wiring tests too — do NOT fork normalization into npc_context.
2. **SECONDARY — `sidequest/game/alias_accretion.py` `_looks_like_finite_verb`.** Replace the brittle structural `-s ⇒ verb` fallback (line ~89) so plural-NOUN epithets ("the silver spurs", "the twin moons") mint, while finite-verb clauses ("the torch sputters") are still rejected. Dev picks the mechanism (richer stoplist, smarter structural rule, etc.) — the 4 guards pin the boundary.

**Constraints (carry into GREEN):**
- REUSE `fold_to_ascii` — do NOT add a second normalization rule (Keith directive, AC-4). The `test_fold_uses_nfkd_not_ascii_drop` test fails under a naive `encode('ascii','ignore')`, pinning true NFKD semantics behaviorally (no source grep, per "No Source-Text Wiring Tests").
- Note: behavioral tests can't distinguish "imported the shared helper" from "re-typed the same two NFKD lines" — the literal-reuse/import is a code-review (simplify-reuse) concern for Westley, not a test concern.
- Minimal change: `_phrase_matches` is the only matcher both `resolve_mention` paths share — fold there, once.

### Dev (implementation) — 2026-06-11

- **Improvement** (non-blocking): `tests/server/dispatch/test_59_23_materialize_other.py::test_ship_combat_materialized_threat_resolves_on_hull` exhibits a NON-deterministic xdist isolation flake — failed once in the full `tests/game tests/server` parallel run, then passed on rerun (and passes in isolation). Shares ZERO code with this story's changes (no alias/epithet/fold reference). Root cause is pre-existing cross-test state leakage under parallel sharding, surfaced because adding 12 tests shifts shard composition. Affects `tests/server/dispatch/test_59_23_materialize_other.py` (needs isolation hardening — likely a global singleton not reset between tests). *Found by Dev during implementation; not introduced by this story.*

### Reviewer (code review) — 2026-06-11

- **Improvement** (non-blocking): `_phrase_matches` re-folds `action_text` once per name AND per alias inside `resolve_mention`'s loop, though it is invariant across the loop. Affects `sidequest/game/alias_resolution.py` (fold `action_text` once in `resolve_mention`, thread the folded text into `_phrase_matches`). Microseconds today; clean efficiency win on a per-turn path. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): the fold introduced a latent empty-fold footgun — a non-empty phrase of pure combining marks folds to `""`, making `\b\b` match any action text (spurious). Proven live; unreachable with current data sources (determiner-led ASCII epithets, real-word names). Affects `sidequest/game/alias_resolution.py` `_phrase_matches` (add `if not folded_phrase: return False` after the fold — one line). *Found by Reviewer during code review.*
- **Question** (non-blocking): folding both sides collapses accent-only-distinct entities ("Cafe" ≡ "Café") in mention-matching. Consistent with 101-8 slug collapsing, and not a live-world pattern, so left as-is — but flagging for Keith's awareness in case a future world wants accent-distinguished names. Affects content-authoring expectations, not code. *Found by Reviewer during code review.*

## Design Deviations (TEA note)

- The context doc points at `sidequest/agents/intent_router.py` as the alias-matching site. The ACTUAL §A4 matcher is `sidequest/game/alias_resolution.py::resolve_mention` (intent_router.py is the higher-level orchestrator and does not do the name/alias word-match). Tests target the real matcher + its live seam. No scope change — just the precise location.

## Design Deviations

### Dev (implementation)
- **POS hardening "replaced" the -s heuristic by REMOVING the structural fallback (stoplist-only), not substituting a new structural rule**
  - Spec source: session title / context-story-84-7.md ("replace the -s verb heuristic")
  - Spec text: "harden the epithet extractor's POS handling (replace the -s verb heuristic)"
  - Implementation: Deleted the structural `len(w)>3 and endswith('s') and not endswith(_NOUN_S_SUFFIXES)` fallback in `_looks_like_finite_verb` (and the now-dead `_NOUN_S_SUFFIXES` constant). `_FINITE_VERB_STOPLIST` membership is now the sole finite-verb signal.
  - Rationale: `-s` is genuinely ambiguous between a 3sg verb ("sputters") and a plural noun ("spurs", "moons"); the structural rule's only net effect on real epithets was the false-positive that wrongly REJECTED plural-noun epithets — the exact bug the story targets. No reliable structural separator exists without a POS tagger (out of scope — no nltk/spacy dep, mirroring 101-8's "no transliteration dep" stance). The curated stoplist already covers every verb the existing rejection tests use and is well-matched to the narrow determiner-led syntactic position.
  - Severity: minor
  - Forward impact: minor — an UNLISTED present-tense scene verb appearing in the leading 1-3 words of a name-anchored appositive ("Borin, the censer gutters,") would now MINT instead of being structurally rejected. Mitigation if it bites in playtest: add the verb to `_FINITE_VERB_STOPLIST` (content-free, one-line). §A4 "miss before mint-garbage" still holds for every listed verb.
- **Fold helper imported across the game→server layer boundary**
  - Spec source: context-story-84-7.md, AC-4 ("REUSE the shared `fold_to_ascii`, not a re-implemented rule")
  - Spec text: "This story must REUSE that exact helper … NOT implement a duplicate normalization rule."
  - Implementation: `sidequest/game/alias_resolution.py` now does a top-level `from sidequest.server.slug_fold import fold_to_ascii`.
  - Rationale: AC-4 mandates reusing the existing helper, which lives in `sidequest.server`. Verified safe: `sidequest/server/__init__.py` is deliberately import-light (no eager re-exports) and `slug_fold` imports only stdlib `unicodedata`; `sidequest.game` already imports from `sidequest.server` at top level elsewhere (`builder.py`, `room_file_loader.py`, ruleset modules). No circular import.
  - Severity: minor
  - Forward impact: none — established precedent; if a future cleanup wants a neutral home for the fold, that is a cross-cutting refactor owned by 101-8, not this story.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/game/alias_resolution.py` — `_phrase_matches` now folds BOTH the candidate phrase and the action text through the shared `fold_to_ascii` (101-8) before the `\b…\b` IGNORECASE regex; closes the §A4 diacritic split-brain. Fixes `resolve_mention` AND its live seam `player_referenced_npcs_from_action` (which delegates here).
- `sidequest-server/sidequest/game/alias_accretion.py` — removed the structural `-s ⇒ verb` fallback in `_looks_like_finite_verb` and the now-dead `_NOUN_S_SUFFIXES`; `_FINITE_VERB_STOPLIST` membership is the sole finite-verb signal, so plural-noun epithets mint while listed scene verbs still reject. (See Design Deviations.)
- `sidequest-server/tests/game/test_alias_diacritic_fold_and_pos.py` — TEA's RED suite (now GREEN).

**Tests:** 12/12 new tests GREEN. Owning modules all green (`test_alias_resolution`, `test_alias_mention_retrieval`, `test_alias_accretion`, `test_npc_epithet_mint_guard` = 56 passed together). Full `tests/game tests/server` = 5766 passed / 0 failed on rerun (one pre-existing non-deterministic flake noted in Delivery Findings). `ruff check` clean on all changed files.

**Branch:** `feat/84-7-epithet-extractor-pos-hardening` (sidequest-server)

**Handoff:** To Westley (review). Watch points: (1) the POS "replace = remove structural fallback" deviation; (2) `fold_to_ascii` reuse is the real helper (NFKD `é→e`), not a re-implementation — pinned behaviorally by `test_fold_uses_nfkd_not_ascii_drop`.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (12/12 GREEN, 0 smells, `_NOUN_S_SUFFIXES` 0 refs) | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | N/A — Disabled via settings (assessed edges myself: EDGE-1/EDGE-2 below) |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | N/A — Disabled via settings (no swallowed errors; both fns fail-loud/return-False) |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | N/A — Disabled via settings (asserts verified structural, no vacuity) |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | N/A — Disabled via settings (new docstrings accurate to behavior) |
| 6 | reviewer-type-design | No | Skipped | disabled | N/A — Disabled via settings (pure str→bool/set helpers, no type concerns) |
| 7 | reviewer-security | No | Skipped | disabled | N/A — Disabled via settings (no auth/secret/injection surface; `re.escape` retained) |
| 8 | reviewer-simplifier | No | Skipped | disabled | N/A — Disabled via settings (EDGE-2 redundant-fold noted myself) |
| 9 | reviewer-rule-checker | No | Skipped | disabled | N/A — Disabled via settings (rule pass done by hand below) |

**All received:** Yes (1 enabled subagent returned clean; 8 disabled via `workflow.reviewer_subagents` and assessed by hand)
**Total findings:** 2 confirmed (both LOW, non-blocking), 0 dismissed, 0 deferred

### Rule Compliance

Enumerated the changed code against the applicable project rules (CLAUDE.md server + `.pennyfarthing/gates/lang-review/python.md` + SOUL.md):

- **No Source-Text Wiring Tests (CLAUDE.md):** ✓ The wiring proof (`TestLiveSeamDiacriticFold`) drives the real seam `player_referenced_npcs_from_action` with fixture data; no `read_text()`/source grep. `test_fold_uses_nfkd_not_ascii_drop` pins the helper behaviorally (NFKD `é→e`), not by import grep.
- **Every Test Suite Needs a Wiring Test (CLAUDE.md):** ✓ Present (live-seam, name + alias paths).
- **Don't Reinvent — Wire Up What Exists (CLAUDE.md):** ✓ Reuses the merged `fold_to_ascii`; no second normalization rule (AC-4 honored).
- **No Silent Fallbacks (CLAUDE.md):** ⚠ `_phrase_matches` returns `False` on blank phrase (correct), but the new fold can produce an empty `folded_phrase` from a non-empty input — see EDGE-1 (LOW, latent). Not a silent *fallback* (no alt path), but a missing post-fold guard.
- **No Stubbing / dead code removed in same PR (CLAUDE.md + feedback):** ✓ `_NOUN_S_SUFFIXES` deleted with its sole consumer; preflight confirms 0 remaining refs.
- **python.md #6 Test quality (vacuous asserts):** ✓ All asserts are structural (`== {set}` / `== []` / explicit `in`); none truthy-only. Negative guards (`== set()`, `== []`) are meaningful (boundary + over-match).
- **python.md #1 silent exception swallowing / #7 resource leaks / #8 unsafe deserialization / #9 async pitfalls:** N/A — pure synchronous string helpers, no I/O, no try/except, no deserialization.
- **OTEL Observability Principle:** N/A — these are pure matcher/extractor helpers (no subsystem *decision* span); the accretion span (`entity.alias_accreted`) is unchanged and untouched. Cosmetic-exempt.

### Devil's Advocate

Argue this is broken. The fold is applied to *both* sides of the match, which means it is now possible for two *distinct* entities to collapse into one match key: an NPC literally named "Cafe" and a faction "Café" both fold to "cafe", so a reference to either resolves *both* — a new cross-entity bleed the pre-fold code could not produce. Is that a bug? In §A4's intent it is a feature (accent-insensitivity is the whole point), and `resolve_mention` is deliberately not single-winner, so surfacing both is consistent — but a world author who *intentionally* used the accent to distinguish two entities now cannot. That is a content-authoring footgun worth one sentence to Keith (recorded as EDGE-3 below, LOW — accent-only-distinct entity names are not an established pattern in any live world, and slugs already collapse them per 101-8, so this merely makes mention-matching consistent with slugging). Next: the empty-fold case (EDGE-1) — a name of pure combining marks folds to `""` and `\b\b` matches everything; I proved this live. Unreachable today (epithets are determiner-led ASCII via `_leading_epithet`; authored names are real words), but the diff *introduced* it. Next: the POS removal — a stressed narration like "Borin, the lantern gutters and dims" now MINTS "the lantern gutters" as an alias because "gutters" is not in the stoplist; previously the structural `-s` caught it. This is the documented, accepted trade (the story's whole point is that plural nouns must mint, and no structural rule separates "gutters"-verb from "spurs"-noun), but it does invert §A4's "miss before mint-garbage" bias for *unlisted* verbs. Mitigation is a one-line stoplist addition when/if it bites in playtest. None of these rise to High: the fold-collapse and empty-fold are unreachable/consistent-with-slugging, and the POS trade is the explicit story intent with a cheap mitigation. Conclusion: correct for the story, with three LOW notes on record.

### Reviewer (audit)
- **Dev deviation #1 (POS "replace" = remove structural fallback)** → ✓ ACCEPTED by Reviewer: the removal is the only way to satisfy the story's "plural nouns must mint" intent without a POS tagger (out of scope); existing rejection tests all use stoplisted verbs so no regression; the §A4-bias-inversion for *unlisted* verbs is documented with a one-line mitigation. Sound.
- **Dev deviation #2 (game→server `fold_to_ascii` import)** → ✓ ACCEPTED by Reviewer: AC-4 mandates reuse; verified non-circular (`server/__init__` import-light, `slug_fold` stdlib-only, established game→server precedent). Sound.
- **EDGE-3 (new, undocumented): accent-only-distinct entities now collapse in mention-matching.** Folding both sides means "Cafe" and "Café" resolve as one. Severity: LOW — not a live-world pattern, and 101-8 slugging already collapses them, so this makes mention consistent with slugs rather than introducing a novel divergence. Recorded for awareness, not a fix.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** player `action_text` → `player_referenced_npcs_from_action` (npc_context.py) → `resolve_mention` → `_phrase_matches(candidate, action_text)` → `fold_to_ascii` on both sides → `\b…\b` IGNORECASE match → matched canonical names → off-stage BRIEF toggle / mention pertinence (ADR-118 §A4). Safe: fold is symmetric, `re.escape` retained after fold (no regex-injection from folded letters), `\b` discipline verified preserved by `test_word_boundary_survives_fold`.

**Pattern observed:** Minimal single-seam fix — both `resolve_mention` paths (name + alias) share the one `_phrase_matches` matcher, so the fold lands in exactly one place (`alias_resolution.py:53-56`). Dead constant removed in-PR. Good.

**Error handling:** Pure helpers; blank/empty inputs return `False`/`set()` (`alias_resolution.py:51`, `:70`). One gap (EDGE-1, LOW): post-fold-empty not guarded.

**Findings (all LOW / non-blocking):**
| Severity | Issue | Location | Recommendation |
|----------|-------|----------|----------------|
| [LOW][SIMPLE] | `fold_to_ascii(action_text)` recomputed for every name+alias in the loop (invariant) | `alias_resolution.py` `resolve_mention` | Fold `action_text` once in `resolve_mention`, pass folded text (or a folded-action param) to `_phrase_matches`. Microseconds today; clean win on a per-turn path. |
| [LOW][EDGE] | A non-empty phrase that folds to `""` (pure combining marks) yields `\b\b` → matches everywhere (spurious). Proven live. Unreachable with current data sources. | `alias_resolution.py` `_phrase_matches` | Add `if not folded_phrase: return False` after the fold. One line. |

Neither is Critical/High; per the blocking rule the story is approved. Both recorded as non-blocking Improvements for an optional quick follow-up.

**Handoff:** To SM (Vizzini) for finish-story.