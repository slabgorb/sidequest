---
story_id: "71-6"
jira_key: null
epic: "71"
workflow: "trivial"
---
# Story 71-6: Narration POV person-agreement — anchor-PC bare-possessive + mixed-person slips

## Story Details
- **ID:** 71-6
- **Jira Key:** None (personal project — no Jira)
- **Workflow:** trivial (implement → review → finish)
- **Repository:** sidequest-server (CONFIRMED — POV swap is server-side prose post-processing in `agents/pov_swap.py`, called per-recipient from `server/emitters.py::emit_event`. epic-71.yaml correctly records `repos: sidequest-server` this time; verified by code search — same family as 71-5/#485.)
- **Branch:** feat/71-6-narration-pov-person-agreement (off origin/develop @ 260e911, includes 71-2/#486)
- **Story Type:** Bug
- **Points:** 2
- **Priority:** p3 (LAST story this epic-71 peloton run)

## Problem Statement

`swap_to_second_person()` in `sidequest-server/sidequest/agents/pov_swap.py` rewrites third-person NAME references to the anchor PC into second person on that player's own narration card ("Carl plants a boot" → "You plant a boot"). It is a pure, name-driven, sentence-local string transform (pronoun passes 5/6/7 were retired 2026-05-23 as antecedent-blind). Two residual grammar defects produce **person-disagreement** in the rewritten prose:

### Bug 1 — anchor-PC bare (predicate/absolute) possessive
**Pass 1** (lines ~248–254) maps `"{Name}'s"` → `"Your"`/`"your"` UNCONDITIONALLY:
```python
text = re.sub(rf"\b{name_esc}'s\b", _pos_name_sub, text)   # always "Your"/"your"
```
But English distinguishes the **dependent** possessive (`your hand` — modifies a following noun) from the **absolute/predicate** possessive (`the hand was yours` — stands alone). When `{Name}'s` is clause-final / predicate (followed by sentence-end punctuation, a comma, or a coordinating conjunction, or with no noun it governs), the correct second-person form is **`yours`**, not `your`.
- Repro: `"The polearm was Carl's."` → current output `"The polearm was your."` (ungrammatical) → expected `"The polearm was yours."`
- Sentence-initial predicate must capitalize: `"Yours, that decision."`

### Bug 2 — mixed-person verb slip (stranded verb after a connector+adverb)
**Passes 8 and 9** conjugate a continuation verb only when it is the **token immediately** after `and` / `,`:
```python
text = re.sub(r"\band\s+(\w+)", _and_verb_sub, text)   # Pass 8
text = re.sub(r",\s+(\w+)", _comma_verb_sub, text)     # Pass 9
```
When an adverb or `then` sits between the connector and the real verb, the verb is stranded in 3rd-person form and survives the swap, producing person disagreement within one sentence:
- Repro: `"Carl steadies the pistol, then fires."` → Pass 2 swaps the subject (`Carl steadies` → `You steady`); Pass 9 captures `"then"` after the comma (not a verb → skipped), so `"fires"` is never conjugated → current `"You steady the pistol, then fires."` (mixed person) → expected `"You steady the pistol, then fire."`
- Same pattern under `and`: `"Carl turns and slowly raises the lantern."` → `"You turn and slowly raises the lantern."` → expected `"...slowly raise..."`

This mirrors the Pass-2b "interrupter" problem (already solved for the subject→verb gap): the fix is to skip a bounded leading adverb/`then` run to reach the first stranded verb in the `and`/comma continuations, gated exactly as Passes 8/9 are (`had_subject_swap` + `_looks_like_verb`).

## Acceptance Criteria

1. **Predicate/absolute possessive → `yours`:** When `{anchor_name}'s` appears in predicate/absolute position (clause-final: followed by `.!?…`, a comma, a coordinating conjunction, or end-of-text — i.e. NOT governing a following noun), it rewrites to `yours` (capitalized `Yours` at sentence start). Dependent/attributive `{anchor_name}'s <noun>` continues to rewrite to `your`/`Your` (NO regression to existing Pass-1 behavior).
2. **Stranded continuation verb conjugated:** A 3rd-person continuation verb separated from its `and`/comma connector by a bounded adverb run (incl. `then`) is conjugated to 2nd-person when the sentence already had a subject swap — eliminating the mixed-person slip. Gated by `had_subject_swap` and `_looks_like_verb` (no over-firing on plural nouns / appositive commas).
3. **No regression:** All existing `test_pov_swap.py` / `test_pov_swap_otel.py` cases stay green; dialogue-preservation, antecedent-safety (NPC sharing PC pronouns), and the retired-pronoun-pass guarantees are untouched. `swap_count` continues to reflect the true number of edits (increment on each new substitution).
4. **OTEL:** No new span required — this is deterministic prose post-processing on the EXISTING `narration.second_person_swap` span. New substitutions must be reflected in the existing `swap_count` attribute (count each predicate-possessive and stranded-verb edit). Do NOT add a separate watcher event.

## Technical Approach (scoped, in `agents/pov_swap.py::_rewrite_sentence`)

- **Bug 1:** In Pass 1's `_pos_name_sub`, look at what follows the matched `{Name}'s`. If the next non-space char is `.!?…`, `,`, `;`, `:`, end-of-text, or the next token is a coordinating conjunction (`and/or/but/nor/so/yet`), emit `yours`/`Yours` (capitalization via existing `_is_sentence_start_in`). Otherwise keep `your`/`Your`. Use a `re.Match`-aware lookahead on `text` (the sub already receives `m` and closes over `text`).
- **Bug 2:** Add a bounded leading-adverb skip to the Pass 8 (`and`) and Pass 9 (`,`) continuation regexes — pattern shape like `(?:and|,)\s+((?:\w+\s+){0,2}?)(\w+)` then conjugate the trailing verb group only if `_looks_like_verb`. Reuse Pass-2b's interrupter idea; keep `count=1`-style discipline and the `had_subject_swap` gate. Confirm `then`/adverb tokens pass through unchanged (only the verb is rewritten).
- Both fixes are sentence-local and name/subject-gated — they do NOT reintroduce antecedent-blind pronoun rewriting.

## Test Plan (inline — trivial workflow, Dev writes the test)

Extend `sidequest-server/tests/agents/test_pov_swap.py`:
- Bug 1: predicate possessive → `yours` (`"The polearm was Carl's."` → `"...was yours."`); sentence-start `Yours`; **regression guard** that attributive `"Carl's polearm"` still → `"Your polearm"`/`"your polearm"`.
- Bug 2: `"Carl steadies the pistol, then fires."` → `"You steady the pistol, then fire."`; the `and` + adverb variant; **regression guard** that a plural noun after a comma (`"..., the bronze fittings gleam."`) is NOT conjugated.
- Behavioral assertions on returned prose (and `swap_count` deltas), not source-text greps (per server CLAUDE.md "No Source-Text Wiring Tests").

## Sm Assessment

Setup verified for peloton handoff to Dev (Major Winchester) — trivial workflow (implement → review → finish); Dev owns implement and writes the test inline. Well-scoped, pure-function grammar fix entirely inside `agents/pov_swap.py::_rewrite_sentence`. The two defects are both **person-disagreement** residue from the 2026-05-23 pronoun-pass retirement era — name-driven passes are correct but incomplete for (1) predicate possessives and (2) connector-stranded continuation verbs.

**Routing notes:**
- ⚠️ REPO = **sidequest-server** (CONFIRMED by code search — `agents/pov_swap.py`; epic YAML agrees this time). Branch `feat/71-6-narration-pov-person-agreement` already created off origin/develop; PR targets server **develop** (squash-merge).
- I located concrete repros from the code (above) so Dev does not have to hunt: Bug 1 = `"...was Carl's."` → must be `yours`; Bug 2 = `"...steadies it, then fires."` → `fires` left 3rd-person. **OPEN ITEM for Dev:** if a real playtest line for the "mixed-person slip" differs from my constructed `then`-adverb repro, fix the actual observed construction — but the adverb/`then`-stranded-verb gap is the structurally obvious one given Passes 8/9 only conjugate the immediately-adjacent token.
- **TRAP — antecedent safety:** do NOT solve either bug by reintroducing a pronoun pass (5/6/7 were retired for antecedent-blindness — see module docstring lines 14–24 + Pass-5/6/7 retirement comment ~368–383). Both fixes stay name-/subject-gated and sentence-local.
- **TRAP — Pass-1 regression:** the predicate-possessive branch must NOT change attributive `"Carl's polearm"` → `"Your polearm"`. Reviewer holds the attributive-vs-predicate split as the primary focus check.
- **TRAP — Pass 8/9 over-firing:** the leading-adverb skip must keep the `_looks_like_verb` + `had_subject_swap` gates so it never conjugates plural nouns or appositive commas. Reviewer holds "no over-conjugation" as the second focus check.
- OTEL: NO new span — deterministic prose transform; fold the new edits into the existing `narration.second_person_swap` `swap_count`. (Reviewer: don't block on a missing watcher event — this is text post-processing, not a subsystem AI decision.)

## Workflow Tracking

**Workflow:** trivial (quick fix, no TDD ceremony)
**Phase:** finish (current)
**Phase Started:** 2026-05-28T07:54:14Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | (this session) | 2026-05-28T07:18:36Z | — |
| implement | 2026-05-28T07:18:36Z | 2026-05-28T07:29:23Z | 10m 47s |
| review | 2026-05-28T07:29:23Z | 2026-05-28T07:44:15Z | 14m 52s |
| finish | 2026-05-28T07:44:15Z | - | - |

## Design Deviations

### Dev (implementation)
- **`_is_pronoun()` guard on Pass 8/9 adverb-skip**
  - Spec source: 71-6-session.md Technical Approach, AC-2
  - Spec text: "Add a bounded leading-adverb skip… gated exactly as Passes 8/9 are (`had_subject_swap` + `_looks_like_verb`)"
  - Implementation: Added `_is_pronoun(word1)` guard to the adverb-skip branch: only skip word1 as an adverb when it is NOT a pronoun. Required adding a `_is_pronoun()` helper.
  - Rationale: Without this guard, `"and he hauls"` would wrongly conjugate "hauls" to "haul" (treating the pronoun "he" as an adverb to skip). This is the exact antecedent-blindness failure that caused Passes 5/6/7 to be retired. The spec said "gated by `_looks_like_verb`" but did not anticipate that pronoun-word1 would satisfy the adverb-skip path. Discovered by test coverage during implementation.
  - Severity: minor (scope addition, not a spec contradiction)
  - Forward impact: none — `_is_pronoun()` is a pure utility; the pronoun sets are stable.

- **`word1[0:1].islower()` guard on Pass 8/9 adverb-skip (rework fix)**
  - Spec source: 71-6-session.md Technical Approach, AC-2 + AC-3 (no regression)
  - Spec text: "gated by `had_subject_swap` and `_looks_like_verb` (no over-firing on plural nouns / appositive commas)"
  - Implementation: Added `and word1[0:1].islower()` to both Pass 8 and Pass 9 adverb-skip branches. Proper-noun NPC names (capitalized) are now correctly excluded from the adverb-skip path.
  - Rationale: `_is_pronoun()` only blocks he/she/they pronouns, not NPC proper names. `"Carl nods, Maria steps forward."` was incorrectly producing `"You nod, Maria step forward."` — "Maria" was treated as a skippable adverb. Real adverbs ("then", "slowly") are always lowercase. NPC names always begin uppercase. The `islower()` check is the minimal, correct discriminator.
  - Severity: minor (rework to close review gap)
  - Forward impact: none — lowercase check is stable; single-char guard.

### Reviewer (audit)
- **Dev deviation `_is_pronoun()` guard** → ✓ ACCEPTED by Reviewer: The guard is not merely acceptable — it is *required*. The existing test at `test_pov_swap.py:348` (`"Carl plants a boot and he hauls the polearm out wet."`) is a regression test for exactly this antecedent-blindness failure. The new two-word pattern would have broken this pre-existing test without the guard. Dev's deviation logging correctly identifies this as necessary scope addition, not spec contradiction.
- **Rework deviation `word1[0:1].islower()` guard** → ✓ ACCEPTED by Reviewer: Minimal and correct. Real adverbs ("then", "slowly") are always lowercase in narrator prose; NPC proper names always capitalize. The `islower()` check is the correct discriminator, and `word1[0:1]` is safe (slice, not index — can't raise IndexError). The two new tests `test_npc_name_after_comma_verb_not_conjugated` and `test_npc_name_after_and_verb_not_conjugated` directly exercise the fix. APPROVE.

## Subagent Results (rework review)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A |
| 2 | reviewer-edge-hunter | Yes | Skipped | disabled | N/A |
| 3 | reviewer-silent-failure-hunter | Yes | Skipped | disabled | N/A |
| 4 | reviewer-test-analyzer | Yes | Skipped | disabled | N/A |
| 5 | reviewer-comment-analyzer | Yes | Skipped | disabled | N/A |
| 6 | reviewer-type-design | Yes | Skipped | disabled | N/A |
| 7 | reviewer-security | Yes | clean | none | N/A |
| 8 | reviewer-simplifier | Yes | Skipped | disabled | N/A |
| 9 | reviewer-rule-checker | Yes | Skipped | disabled | N/A |

**All received:** Yes (2 ran, 0 findings; 7 skipped per settings)

## Reviewer Assessment (rework)

**Verdict:** APPROVED

**Data flow traced:** Narrator prose → `_rewrite_sentence` → Pass 9 regex matches `", Maria steps"` → word1="Maria", word2="steps" → `_looks_like_verb("steps")` True, `not _is_pronoun("Maria")` True, `"M".islower()` **False** → guard fires, returns unchanged → NPC verb preserved.

**Pattern observed:** Symmetric guard at `pov_swap.py:465` and `pov_swap.py:529` — both Pass 8 and Pass 9 have identical invariant. Consistent with the existing `_is_pronoun()` pattern preceding it.

**Error handling:** `word1[0:1]` is a safe slice (no IndexError); `(\w+)` guarantees non-empty. `islower()` on empty string returns False (safe conservative result). Security subagent confirmed: no injection path, no data leakage.

**[VERIFIED] Rework fix correctness:** `"Carl nods, Maria steps forward."` → Pass 9 word1="Maria", `"M".islower()` → False → NPC verb "steps" preserved. `"Carl steadies, then fires."` → word1="then", `"t".islower()` → True → PC verb "fires" still conjugated. Both paths verified.

**[SEC][VERIFIED] Security clean:** `word1[0:1].islower()` is a pure boolean predicate on a regex-captured word character. No injection, no IndexError, no sensitive data.

**[LOW] Deferred — `pronouns = {…}` set rebuilt per call in `_is_pronoun`:** Pre-existing from the initial implementation. A module-level `_PRONOUNS: frozenset` would be marginally more efficient. Non-blocking; not a correctness issue.

**Devil's Advocate:** Could `islower()` misfire? (1) Multi-word NPC names starting with lowercase? Not possible in narrator prose — proper names always capitalize. (2) All-caps adverbs ("THEN")? `"T".islower()` → False → skipped. In narrator prose all-caps is unusual for adverbs; acceptable edge case. (3) NPC with lowercase name? Not grammatically valid in English (e.g., "mcallister"). Non-issue.

**Handoff:** To SM (Hawkeye Pierce) for finish-story

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A |
| 2 | reviewer-edge-hunter | Yes | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Yes | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Yes | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | clean | none | N/A |
| 8 | reviewer-simplifier | Yes | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (2 ran, 0 findings; 7 skipped per settings)

## Reviewer Assessment

**Verdict:** APPROVED

### Rule Compliance (Python lang-review checklist, 14 rules)

Checked against `pov_swap.py` and `test_pov_swap.py` diff:

1. **Silent exception swallowing** — no try/except in changed code. ✓
2. **Mutable default arguments** — `_is_pronoun(word: str)` has immutable str default context; `pronouns` set is a literal inside the function body (recreated each call — not a default arg). ✓
3. **Type annotations** — `_is_pronoun(word: str) -> bool` fully typed. Pass 1/8/9 closures are internal. ✓
4. **Logging** — no logging in this module; OTEL span unchanged. ✓
5. **Path handling** — no file paths. ✓
6. **Test quality** — all 9 new tests assert specific output strings or specific substrings; `assert count == 3` in `test_comma_then_verb_conjugated` pins exact substitution count. No vacuous assertions. ✓
7. **Resource leaks** — none. ✓
8. **Unsafe deserialization** — none. ✓
9. **Async pitfalls** — synchronous module, no async. ✓
10. **Import hygiene** — no new imports. ✓
11. **Input validation** — `swap_to_second_person` already raises on empty name/bad pronouns (unchanged). ✓
12. **Dependency hygiene** — no dep changes. ✓
13. **Fix regressions** — checked below. ✓
14. **State cleanup** — no lifecycle queues. ✓

**Minor note on rule 2:** `pronouns = {"he", "him", ...}` inside `_is_pronoun()` is a set literal recreated each call. Functionally correct, but a module-level constant would be marginally more efficient. Non-blocking; does not violate the mutable-default-argument rule (it's a local variable, not a default parameter).

### Data Flow Traced

Narrator prose (LLM output) → `swap_to_second_person(text, target_name, pronouns)` → `_split_by_dialogue` (preserve quoted dialogue) → `_rewrite_sentence` → Pass 1: `re.sub(rf"\b{name_esc}'s\b", _pos_name_sub, text)` where `_pos_name_sub` reads `text[m.end():]` to detect predicate position → `_is_sentence_start_in` for capitalization → returns `"yours"`/`"Yours"` or `"your"`/`"Your"`. Pass 8/9: `re.sub(r"\band\s+(\w+)(?:\s+(\w+))?", ...)` gated by `had_subject_swap`; `_is_pronoun(word1)` guards against NPC-pronoun misfire. All reads are from the same sentence-local `text` string (no external state). ✓

### Observations

[VERIFIED] **TRAP 1 — Attributive possessive regression:** `"Carl's polearm lies across the threshold."` — `rest = " polearm lies..."`, `stripped = "polearm..."`, `stripped[0] = "p"` (not in `.!?,;:…`), no coordinating-conj match → `is_predicate = False` → returns `"Your"`. Test `test_attributive_possessive_still_becomes_your` asserts `out.startswith("Your polearm")` and `"Yours" not in out`. Evidence: `pov_swap.py` predicate branch at `stripped[0] in ".!?,;:…"` — `"p"` is not in that set. Complies with TRAP 1. ✓

[VERIFIED] **TRAP 2 — No over-conjugation on plural-noun comma:** `"Carl nods, the bronze fittings gleam."` — Pass 9 matches `", the bronze"` (word1="the", word2="bronze"). `_looks_like_verb("the")` → False; `_looks_like_verb("bronze")` → False → no change. Engine advances past match; `" fittings gleam"` has no leading comma → never matched. `"fittings"` unchanged. Test `test_plural_noun_after_comma_not_conjugated` asserts `"fittings gleam" in out`. Evidence: `_looks_like_verb` at `render.py` line 135-150 — "the" and "bronze" fail both the irregular-verb check and the endswith-s check. ✓

[VERIFIED] **`_is_pronoun()` antecedent safety:** Existing test at `test_pov_swap.py:348` — `"Carl plants a boot and he hauls the polearm out wet."` → expected `"...and he hauls..."` (NPC "hauls" preserved). With new two-word pattern `\band\s+(\w+)(?:\s+(\w+))?`, this matches `"and he hauls"` (word1="he", word2="hauls"). `_looks_like_verb("he")` → False. `_looks_like_verb("hauls") and not _is_pronoun("he")` → True AND not True → False. Returns unchanged. Test passes. Evidence: `_is_pronoun` set includes "he". Pre-existing regression test CATCHES this without requiring a new test. ✓

[SEC][VERIFIED] **Security — no injection surface:** `re.match(r"\b(?:and|or|but|nor|so|yet)\b", stripped)` is a fixed-length alternation with no nested quantifiers — ReDoS risk nil. `stripped[0]` behind `not stripped` short-circuit — IndexError impossible. Confirmed by security subagent. ✓

[LOW] **`_is_pronoun()` set recreation per call:** The `pronouns = {...}` set is recreated on every call. A module-level `_PRONOUNS: frozenset[str]` constant would avoid this. Non-blocking; prose post-processor is not a hot loop. Defer to future cleanup.

[LOW] **`"hers"` not in `_is_pronoun` set:** `_is_pronoun("hers")` → False, and `_looks_like_verb("hers")` → True (ends in -s). In `", hers"` context, "hers" would be treated as a verb and `_conjugate("hers")` → "her". This is a pre-existing `_looks_like_verb` limitation (can't distinguish possessive pronouns from 3rd-person verbs). Real narrator prose rarely produces `", hers verb"` construction. Non-blocking corner case; documented as pre-existing.

### Devil's Advocate

Could this break? Consider: (1) What if the narrator writes `"The gun was yours, Carl."` — does Pass 1 fire on a sentence that *already contains* "yours"? No — Pass 1 only fires on `{name_esc}'s`, not on pre-existing "yours". (2) What about `"Carl's, then fires."` — predicate possessive followed by "then fires"? `stripped = ", then fires."`, `stripped[0] = ","` → predicate → "Yours, then fires." Then Pass 9 on `", then fires"`:  word1="then", word2="fires". `_looks_like_verb("then")` → False. `_looks_like_verb("fires")` → True. `_is_pronoun("then")` → False. Returns `", then fire."`. Full: `"Yours, then fire."` — unusual but grammatically plausible. (3) What if "and" appears in the predicate check for Pass 1 AND as a verb connector for Pass 8? `"The choice was Carl's and he took it."` → Pass 1: `stripped = "and he took it."`, matches coordinating-conj → `is_predicate = True` → "yours". Then Pass 8 on `"and he took"` (word1="he", word2="took"). `_looks_like_verb("he")` → False. `_looks_like_verb("took")` → False (no -s). No change. Result: `"The choice was yours and he took it."` ✓ (4) Can Pass 8 fire on `"and"` within a predicate-possessive rewrite? No — Pass 8 is in `_rewrite_sentence`, and Pass 1's substitution of `"Carl's"` → `"yours"` happens first (no change to `"and"` position), so Pass 8 operates on the text after Pass 1. Fine. No interference. None of these scenarios reveal correctness issues.

**Pattern observed:** The `_is_pronoun()` guard mirrors the antecedent-safety doctrine established for Passes 5/6/7 retirement — name-driven passes only, pronoun guard prevents NPC misfire. Consistent with the module's design philosophy. Evidence: `pov_swap.py` docstring lines 14-24 ("the only safe rewrites are NAME-driven") + Pass 5/6/7 retirement comment at lines 368-383.

**Error handling:** `swap_to_second_person` raises `ValueError` on empty target_name and unsupported pronouns (unchanged from prior implementation). ✓

**Handoff:** To SM (Hawkeye Pierce) for finish-story

## Dev Assessment (rework)

**Implementation Complete:** Yes (rework complete — islower() guard added)
**Files Changed:**
- `sidequest/agents/pov_swap.py` — Pass 8 + Pass 9: added `word1[0:1].islower()` guard to adverb-skip branch; prevents NPC proper-noun names from being treated as skippable adverbs.
- `tests/agents/test_pov_swap.py` — 2 new regression tests: `test_npc_name_after_comma_verb_not_conjugated`, `test_npc_name_after_and_verb_not_conjugated`.

**Tests:** 59/59 passing (GREEN)
**Branch:** feat/71-6-narration-pov-person-agreement (pushed)

**Handoff:** To review (Colonel Potter)

## Delivery Findings

### Dev (implementation)
- No upstream findings during implementation.

**Tests:** 57/57 passing (GREEN)
**Branch:** feat/71-6-narration-pov-person-agreement (pushed)

**Handoff:** To review (Colonel Potter)

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none blocking (2 cosmetic) | confirmed 0 / dismissed 2 cosmetic |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | N/A — Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | N/A — Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | N/A — Disabled via settings |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | N/A — Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | N/A — Disabled via settings |
| 7 | reviewer-security | Yes | clean | none | N/A |
| 8 | reviewer-simplifier | No | Skipped | disabled | N/A — Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | N/A — Disabled via settings |

**All received:** Yes (2 enabled ran; 7 skipped per settings. Preflight cosmetics dismissed; 1 HIGH finding from Reviewer's own adversarial analysis.)

## Design Deviations — Reviewer Audit

### Reviewer (audit)
- **`_is_pronoun()` guard on Pass 8/9 adverb-skip** → ✓ ACCEPTED by Reviewer: guard is necessary and correct — prevents "and he hauls" → "and he haul" antecedent-blindness regression. Pronoun set covers all required forms (he/him/his, she/her, they/them/their + i/me/we/us/you/it). However: guard is INSUFFICIENT — it does not protect NPC proper names from the adverb-skip path. See HIGH finding below.

## Reviewer Assessment

**Verdict:** REJECTED

### Rule Compliance (Python lang-review checklist)

Checked all 14 rules against changed `.py` files:

1. **Silent exception swallowing** — No bare except. ✓
2. **Mutable default arguments** — `_is_pronoun` is a new function with no mutable defaults. Pass 8/9 functions are closures with no mutable defaults. ✓
3. **Type annotation gaps** — `_is_pronoun(word: str) -> bool` correctly typed. `_pos_name_sub`, `_and_verb_sub`, `_comma_verb_sub` are inline closures (private, exempt). ✓
4. **Logging coverage** — OTEL span at line 633–636. No logging module used. ✓
5. **Path handling** — No filesystem paths in changed code. ✓
6. **Test quality** — 9 new tests all assert specific prose output. count=3 assertion is exact and behavioral. No vacuous assertions. ✓ (but coverage gap — see HIGH finding)
7. **Resource leaks** — No file handles or connections. ✓
8. **Unsafe deserialization** — None. ✓
9. **Async pitfalls** — No async code. ✓
10. **Import hygiene** — No new imports. ✓
11. **Input validation** — `text` is LLM narrator output (server-trusted). `target_name` goes through `re.escape()`. ✓
12. **Dependency hygiene** — No changes. ✓
13. **Fix-introduced regressions** — **FAIL.** Pass 8/9 two-word capture fires on NPC names after connector: `"Carl nods, Maria steps forward."` → `"You nod, Maria step forward."`. Test suite does not cover this. ✗
14. **State cleanup ordering** — No queues/buffers. ✓

### Data Flow Traced

`swap_to_second_person("Carl steadies the pistol, then fires.", target_name="Carl", pronouns="he/him")` → `_split_by_dialogue` (no dialogue) → per-sentence loop → `_rewrite_sentence` → Pass 1 (no Carl's) → Pass 2 detects `"Carl steadies"` → `"You steady"`, had_subject_swap=True, count+=2 → Pass 9 regex `r",\s+(\w+)(?:\s+(\w+))?"` matches `, then fires` → word1="then", word2="fires" → `_looks_like_verb("then")` False → `_looks_like_verb("fires")` True → `_is_pronoun("then")` False → conjugate "fires"→"fire", count+=1 → returns `"You steady the pistol, then fire."` count=3. Correct. ✅

### Observations

[VERIFIED] **Antecedent guard (`_is_pronoun()`):** Correctly blocks "and he hauls" → "and he haul". Test confirmed: `"Carl spots the thief and he hauls him down."` → `"You spot the thief and he hauls him down."` (hauls preserved). Covers he/him/his, she/her, they/them/their, I/me/we/us/you/it. ✓

[VERIFIED] **TRAP — Pass-1 regression (attributive stays `your`):** `"Carl's polearm lies across the threshold."` → `"Your polearm lies across the threshold."` — NOT "Yours". `test_attributive_possessive_still_becomes_your` passes. Predicative lookahead `text[m.end():]` correctly discriminates "polearm" (non-terminal) from `.!?,;:…` (terminal). ✓

[VERIFIED] **TRAP — plural noun after comma (test case):** `"Carl nods, the bronze fittings gleam."` → `"You nod, the bronze fittings gleam."` — "fittings" not conjugated because article "the" is word1 (`_looks_like_verb("the")` → False). ✓ Test covered.

[VERIFIED] **AC5 OTEL — swap_count correct:** count=3 for "Carl steadies the pistol, then fires." confirmed (subject swap=2, then-fire=1). Existing `narration.second_person_swap` span emitted once per call with final count. ✓

[HIGH] **[TEST] NPC-name-after-comma/and regression — missing guard and no test.** The adverb-skip path in Pass 8 and Pass 9 gates only on `not _is_pronoun(word1)`. This does NOT protect proper-noun NPC names. Confirmed:
- `"Carl nods, Maria steps forward."` → `"You nod, Maria step forward."` ← wrong (on feature branch)
- `"Carl advances, Elena watches the door."` → `"You advance, Elena watch the door."` ← wrong
- `"Carl runs and Maria steps forward."` → `"You run and Maria step forward."` ← wrong
- On develop, all three produce correct output because the OLD single-word regex `r",\s+(\w+)"` only captures `Maria` (not a verb), leaving `steps` untouched.
- Fix: add `word1[0:1].islower()` guard to the adverb-skip branch in both Pass 8 and Pass 9. Proper nouns (NPC names) always start with a capital letter; adverbs like "then"/"slowly" start lowercase. One-line fix per pass + test asserting "Carl nods, Maria steps forward." is preserved. Also add corresponding "and NPC verb" test.

[LOW] **Pre-existing "and his" → "and hi" bug** (not introduced by this PR): `_looks_like_verb("his")` → True (ends in "s") causes "and his sword" → "and hi sword" on both develop and feature branch. Out of scope for 71-6 but worth a follow-up chore.

[SEC] **Clean.** `re.escape(target_name)` at every use site. New regex has no ReDoS risk (`\s` and `\w` are character-class disjoint). `text[m.end():]` slice is safe by Python language spec. ✓

### Devil's Advocate

What breaks this? (1) Most obviously — any sentence where the anchor PC and an NPC both appear: "Carl turns, Maria calls out." → "You turn, Maria call out." — wrong, and extremely common in ensemble-cast narration. This will produce visible grammar errors in exactly the scenarios the game is designed for. (2) Double-adverb: "Carl turns and very slowly raises the flag." — only one word captured past "and", so "very slowly" is captured as (word1="very", word2="slowly"), neither verb-like, no conjugation. "raises" is left 3rd-person — mixed-person miss. Within spec (one-adverb skip only). (3) NPC predicate possessive in a pov-swapped sentence: "Carl wins and the glory is Maria's." — the predicate possessive pass fires on "Maria's" only if `target_name="Maria"`. If target_name="Carl", "Maria's" is untouched. ✓ (4) The `_is_pronoun()` guard misses "hers"/"theirs" (end in "s", so treated as verbs in word1-is-verb path pre-guard anyway). Pre-existing. (5) The `word1[0].islower()` fix would also need to handle `word1` being the empty string — but `(\w+)` guarantees at least one character.

**The `_is_pronoun()` guard is necessary but not sufficient.** It handles the pronoun case (he/she/they) correctly. It does not handle the NPC name case (Maria, Elena, Thomas). Every sentence with `[PC_name] [verb], [NPC_name] [verb]` will incorrectly conjugate the NPC's verb.

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] | NPC name after comma/and treated as adverb; NPC's verb incorrectly conjugated. `"Carl nods, Maria steps."` → `"You nod, Maria step."` | `pov_swap.py` Pass 8 `_and_verb_sub` + Pass 9 `_comma_verb_sub`, adverb-skip branch | Add `and word1[0:1].islower()` to the `if _looks_like_verb(word2) and not _is_pronoun(word1):` guard in both passes. Add tests: `"Carl nods, Maria steps forward."` → `"You nod, Maria steps forward."` and `"Carl turns and Maria calls out."` → `"You turn and Maria calls out."` |

**Handoff:** Back to Dev (Major Winchester) — fix is one-line per pass + 2 tests. Route to green phase.

## Delivery Findings

### Dev (implementation)
- No upstream findings during implementation.

### Reviewer (code review)
- **Gap** (blocking): NPC-name-after-comma regression in Pass 8/9 adverb-skip. `_is_pronoun()` guard blocks pronouns but not proper nouns. Affects `sidequest/agents/pov_swap.py` (add `word1[0:1].islower()` to adverb-skip guard in `_and_verb_sub` and `_comma_verb_sub`) + `tests/agents/test_pov_swap.py` (add 2 NPC-after-connector tests). *Found by Reviewer during adversarial analysis.*

---

**Co-Authored-By:** Claude Opus 4.7 (1M context) <noreply@anthropic.com>