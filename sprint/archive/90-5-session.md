---
story_id: "90-5"
jira_key: ""
epic: "90"
workflow: "tdd"
---
# Story 90-5: 90-1 fail-loud hardening

## Story Details
- **ID:** 90-5
- **Jira Key:** (none)
- **Workflow:** tdd
- **Stack Parent:** none
- **Repos:** server
- **Branch Strategy:** gitflow (feat/90-5-fail-loud-hardening)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-10T12:05:50Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-10T00:00:00Z | 2026-06-10T11:33:03Z | 11h 33m |
| red | 2026-06-10T11:33:03Z | 2026-06-10T11:49:08Z | 16m 5s |
| green | 2026-06-10T11:49:08Z | 2026-06-10T12:00:42Z | 11m 34s |
| review | 2026-06-10T12:00:42Z | 2026-06-10T12:05:50Z | 5m 8s |
| finish | 2026-06-10T12:05:50Z | - | - |

## Sm Assessment

**Story:** 90-5 — **fail-loud hardening** of the 90-1 bestiary contract. 90-1 shipped
the "never a silent empty pool" doctrine for ruleset-module packs but the Reviewer
APPROVED-with-findings: the *success path* is delivered and CI-guarded; the *failure
path* has no regression tests and degraded observability ("one revert away from
silently un-happening"). This story pins the failure-path contract.

**Workflow:** tdd (phased) → setup (SM ✓) → **red (TEA)** → green (Dev) → review (Reviewer) → finish (SM).
**Repos:** `server,content` — primary work is **server** (`sidequest/cli/encountergen/`,
`sidequest/server/dispatch/pregen.py`, `monster_manual_inject.py`,
`sidequest/genre/models/bestiary.py`, the two 90-1 test modules); **content** carries
only the two bestiary-header hp-floor wording fixes (`space_opera`, `mutant_wasteland`).
Feature branch `feat/90-5-fail-loud-hardening` created + checked out in both repos.
**Jira:** none — claim skipped.

**Context written + enriched:** `sprint/context/context-story-90-5.md` (parent
`context-epic-90.md`). The sprint-YAML stub was thin (title only); I enriched it with
the Problem, a 6-item Technical Approach, the doc/content polish sweep, and Scope —
**all drawn verbatim from the 90-1 Reviewer "Gap (blocking-for-epic-90)" finding.**

**Load-bearing routing notes for TEA (Fezzik):**
- **The authoritative spec is the 90-1 archive**, not the sprint YAML. Read
  `sprint/archive/90-1-session.md` → **Reviewer Assessment** (the findings table with
  exact file:line anchors) + **Delivery Findings → Reviewer** (the numbered 1–6 Gap).
  The story title compresses six items + a polish sweep — the archive has the detail.
- **Six items, each a failing test or a deliberate decision** (see context Technical
  Approach): (1) encountergen exit-1 branch test; (2) `EncounterSeedError` raise test;
  (3) emit `pregen.seed_manual` span w/ error attr *before* raising (**OTEL Principle**);
  (4) assert the `ruleset` span attr in AC4; (5) unit-test `Bestiary`/`BestiaryEntry`
  validators via `model_validate`; (6) **decide the `ensure_loaded` broad-except policy**
  for `EncounterSeedError` (`monster_manual_inject.py:95`) — ADR-006 graceful-degradation
  vs. fail-loud. Item 6 is the load-bearing call; **Keith may want to weigh in** before
  you pin a test around it.
- **The failure-test design crux** (Reviewer's Devil's Advocate): today a revert of the
  raise to a warning passes the *entire* 90-1 suite. Your RED tests must fail if that
  revert happens — pin the *failure contract*, not just the happy path.
- **Regression guard (mandatory):** the full 90-1 story suite
  (`test_encountergen_bestiary_90_1.py` + `test_pregen_bestiary_90_1.py`) and
  `tests/integration/test_wwn_heavy_metal_combat.py` must stay green. This story hardens
  the contract; it must NOT touch the delivered success path.
- **Out of scope (do not conflate):** the `pregen.namegen_failed` silent-skip is a
  *separate* NPC-seeding gap (different follow-up); WWN-SRD numeric fidelity is authoring
  judgment. Both flagged in 90-1 findings — neither belongs here.
- **Run tests with `SIDEQUEST_GENRE_PACKS=<content>/genre_packs` and
  `SIDEQUEST_DATABASE_URL`** set (the bestiary tests need real content; ~33 phantom
  DB failures without the URL).

**Decision:** Setup complete, gate ready. Handoff to TEA (Fezzik) for RED.

## Tea Assessment (RED)

**Phase:** finish complete. Tests written, RED confirmed for the right reason, lint+format
clean, committed `32a2e2e6` on `feat/90-5-fail-loud-hardening` (sidequest-server).

### Re-baseline (read this first — the story is PARTIALLY OVERTAKEN)
The 90-1 archive is the spec, but **the world-tier bestiary repoint landed since 90-1**
and already closed some of this story's items. Measured against current `develop`:

| Item | State | Action |
|------|-------|--------|
| 1 — encountergen exit-1 test | ✅ **already covered** by `test_main_fails_loud_when_ruleset_module_resolves_no_bestiary` (the repoint added it) | dropped — no duplicate |
| 2 — `EncounterSeedError` raise | behavior EXISTS (`pregen.py:338`), untested | **coverage lock** (passes today) |
| 3 — span (error attr) before raise | **behavior GAP** — raise precedes `Span.open` (`:338` vs `:366`) | **RED test** (fails today) |
| 4 — `ruleset` span attr asserted | attr EXISTS (`:374`), unasserted | folded into the item-3 failure-span assertions |
| 5 — Bestiary validators | validators EXIST, only `model_construct` consumers (bypass) | **coverage locks** (pass today) |
| 6 — `ensure_loaded` policy | **behavior GAP** — swallows `EncounterSeedError` today | **RED test** (fails today) |
| polish — awn wording | ✅ moot (AC6 slug tuple gone; only ref already says `wwn\|cwn\|swn\|awn`) | dropped |

Net: items 2–6 are real (2 genuine fixes + 3 coverage locks); item 1 + the awn-wording
polish are done. This is the "RUN the repro before RED" discipline — I did not write
tests duplicating what the repoint already shipped.

### Tests added (RED: `SIDEQUEST_DATABASE_URL=...` + `SIDEQUEST_GENRE_PACKS=...`,
`uv run pytest -n0` → **2 failed / 15 passed**, all hermetic, no content/subprocess)

`tests/server/dispatch/test_pregen_fail_loud_90_5.py` (NEW — items 2/3/4):
1. `test_seed_manual_raises_for_ruleset_pack_when_encounters_empty` (item 2) — **PASSES**
   (lock): ruleset stub + failing encountergen → `raises EncounterSeedError`; message names
   ruleset+bestiary. Breaks on revert-to-silent.
2. `test_seed_manual_native_pack_does_not_raise_on_empty_encounters` (regression guard) —
   **PASSES**: native pack keeps warning-only skip (ADR-006), no raise, empty pool.
3. `test_seed_manual_emits_span_with_error_attr_before_raising` (item 3+4) — **FAILS** for
   the right reason (`assert spans` → `assert []`: the `pregen.seed_manual` span never fires
   before the raise). Pins the contract: failure span carries `seed_error` (non-empty str) +
   `ruleset="wwn"` + `encounters_after=0`.

`tests/genre/models/test_bestiary_90_5.py` (NEW — item 5, all coverage locks, **PASS** today):
4–12. `Bestiary.model_validate` / `BestiaryEntry.model_validate`: reject empty `entries`,
   duplicate ids, empty id, empty name, `level/hp/armor_class` < 1; **allow** negative
   `attack_bonus` (deliberate 90-1 decision — pinned so a future "fix" can't add a bound) +
   extra SRD color; forbid stray top-level keys (`extra="forbid"`).

`tests/server/dispatch/test_monster_manual_inject.py` (EDIT — item 6):
13. `test_ensure_loaded_reraises_encounter_seed_error` (item 6) — **FAILS** for the right
   reason (`DID NOT RAISE` — swallowed; the WARNING `monster_manual.seed_failed` log shows
   the swallow). Keith's policy (2026-06-10): strict fail-loud, re-raise.
14. `test_ensure_loaded_swallows_seed_errors` (existing, **kept green**) — a GENERIC
   `RuntimeError` still degrades per ADR-006. The fix must narrow the except to re-raise
   `EncounterSeedError` only (it subclasses `RuntimeError`, so order matters).

### Keith decision pinned (item 6)
`ensure_loaded` must **re-raise** `EncounterSeedError` (crash the bind), NOT degrade. A
ruleset pack with no bestiary is a fatal authoring/config error, not a transient outage.
Generic exceptions keep ADR-006 graceful degradation. (Asked + answered 2026-06-10.)

### Regression guard — VERIFIED GREEN
`uv run pytest -n0` on the 90-1 suite (`test_encountergen_bestiary_90_1`,
`test_pregen_bestiary_90_1`), both owning modules (`test_pregen`,
`test_monster_manual_inject`), and `tests/integration/test_wwn_heavy_metal_combat.py` →
**59 passed** (only my intended item-6 RED fails). The success path 90-1 delivered stays green.

### Handoff to Dev (Inigo Montoya) — GREEN + polish
**Make green (2 fixes):**
- **Item 3:** in `seed_manual`, emit the `pregen.seed_manual` span **before** raising
  `EncounterSeedError` — refactor so the `with Span.open(...)` wraps the encounter loop (or
  emit-then-raise in an except/finally), adding a non-empty `seed_error` attribute (and
  keeping `ruleset` + `encounters_after=0`). `pregen.py:~338` vs `:~366`.
- **Item 6:** narrow `monster_manual_inject.ensure_loaded`'s broad `except Exception`
  (`:~95`) so `EncounterSeedError` re-raises; other exceptions keep the warning-and-degrade
  path. (EncounterSeedError ⊂ RuntimeError — put the specific `except EncounterSeedError:
  raise` first.)

**Doc/content polish (cosmetic — no test, per CLAUDE.md "Not needed for cosmetic changes";
verify against current files, several stragglers remain after the repoint):**
- `pregen.py:211` seed_manual docstring "falls back to humanoid NPCs from rules.yaml" — refresh.
- `encountergen.py:1-12` module header omits the bestiary path — add it.
- `sidequest/genre/models/__init__.py` — export `Bestiary`/`BestiaryEntry` in `__all__`
  (sibling-module inconsistency; **verify** — the `__init__` had no Bestiary ref when I checked).
- **hp-floor headers (CONTENT repo, now world-tier after the repoint — re-scoped):** the
  "hp == average (4.5/HD)" header is wrong (values are floor) in `mutant_wasteland/bestiary.yaml:7`
  (genre tier) **and all 3 space_opera worlds** (`worlds/{aureate_span,coyote_star,perseus_cloud}/bestiary.yaml:8`)
  — 90-1's finding named only space_opera+mutant_wasteland genre-tier; the repoint spread it.
  **Verify the actual hp values are floor before editing the wording** (don't assert — measure).

**Out of scope (do NOT pull in):** `pregen.namegen_failed` silent-skip (separate NPC-seeding
gap, its own follow-up); WWN-SRD numeric fidelity of bestiary stats (authoring judgment).

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Impact Summary

**Upstream Effects:** No upstream effects noted
**Blocking:** None

### Deviation Justifications

3 deviations

- **Dropped item 1 (encountergen exit-1 test) — already covered upstream**
  - Rationale: the 90-1 archive predates the repoint; 90-5's premise is partially stale (see
  - Severity: minor
  - Forward impact: none — coverage exists; if Dev's item-3 refactor touches the encountergen
- **Dropped the "awn in AC6 wording" polish — moot**
  - Rationale: nothing left to reword.
  - Severity: trivial
  - Forward impact: none.
- **Dropped the hp-floor header reword — measurement contradicts the spec premise**
  - Rationale: measure, don't assert — the 90-1 "floor" observation was imprecise. Making a
  - Severity: trivial
  - Forward impact: none — content unchanged; the `sidequest-content` feature branch carries no

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed (sidequest-server, `feat/90-5-fail-loud-hardening`):**
- `sidequest/server/dispatch/pregen.py` — **item 3**: `seed_manual` now captures the
  ruleset-module seeding failure as `seed_error` and BREAKS the tier loop instead of
  raising mid-loop; the `pregen.seed_manual` span fires with a new `seed_error` attribute
  (empty string on success, the loud message on failure) + the existing `ruleset` +
  `encounters_after=0`; the `EncounterSeedError` raise moved to AFTER the span but BEFORE
  `manual.save()` (record the decision, never persist an empty pool). Docstring refreshed
  (stale "falls back to humanoid NPCs" → ruleset-aware bestiary/fail-loud wording).
- `sidequest/server/dispatch/monster_manual_inject.py` — **item 6**: `ensure_loaded`'s
  broad `except Exception` now has a preceding `except EncounterSeedError: raise` so the
  fatal contract violation propagates (crashes the bind, Keith policy 2026-06-10); generic
  exceptions keep the warning-and-degrade path (ADR-006).
- `sidequest/cli/encountergen/encountergen.py` — **polish**: module docstring now documents
  the ruleset-module bestiary routing alongside the native path.
- `sidequest/genre/models/__init__.py` — **polish**: export `Bestiary` + `BestiaryEntry`
  (import + `__all__`), closing the sibling-module inconsistency.

**Tests:** story suite + regression GREEN. `SIDEQUEST_DATABASE_URL` + `SIDEQUEST_GENRE_PACKS`
set, `uv run pytest -n0`:
- The 2 RED tests now pass (`test_seed_manual_emits_span_with_error_attr_before_raising`,
  `test_ensure_loaded_reraises_encounter_seed_error`).
- 75 passed across the story tests + 90-1 suite + both owning modules
  (`test_pregen`, `test_monster_manual_inject`) + `test_wwn_heavy_metal_combat` integration.
- **Full server suite** (`uv run pytest`, content + DB env): **10152 passed / 7 failed /
  1529 skipped**. All 7 failures are **pre-existing and unrelated** to this story (verified:
  none import/touch `pregen`/`monster_manual_inject`/`bestiary`/`encountergen`):
  - `test_api_contract_aside.py::...does_not_lie_about_asides` — `assert CONTRACT.exists()`
    False (missing api-contract artifact; aside-contract work in flight).
  - `test_encounter_actors_all_combatants.py::test_no_orphan_actors_assignment_in_production_code`
    — source-scan offender `sidequest/game/scene_harness.py:709` (untouched file).
  - 4× `test_audit_namegen_corpora.py::test_audit_live_tree_*` — live-corpus threshold audits
    (evropi corpus < 1000 words; corpus expansion in flight).
  - `test_dogfight_player_throw_roundtrip.py::...emits_dice_request_and_stashes_on_sd` —
    untouched dice/dogfight subsystem.
- `ruff check` + `ruff format --check` clean on all 4 changed source files.

**Branch:** `feat/90-5-fail-loud-hardening` (sidequest-server). **sidequest-content: NO CHANGES**
(see deviation — the hp-floor header reword was dropped after measurement; content branch empty).

**Handoff:** To review (Westley).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (GREEN: 43 passed; ruff check+format PASS; 0 smells) | confirmed 0, dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings — covered by Reviewer directly (tier-1-vs-tier-2 failure ordering, break-then-raise, native-vs-ruleset branch traced below) |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings — covered directly (the diff STRENGTHENS No-Silent-Fallbacks: item 6 re-raise + item 3 span-on-failure; broad except narrowed) |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings — covered directly (read all 3 test files; meaningful assertions, pytest.raises+match, non-empty-str span assert, deliberate-decision lock) |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings — covered directly (stale "OTEL fires below regardless" line REMOVED; new comments accurate; 3 docstrings refreshed) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings — covered directly (`seed_error: str \| None`; EncounterSeedError typed catch; pydantic ge=1 bounds tested) |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings — covered directly (no eval/shell/deser; seed_error f-string is str/int only; content is operator-authored) |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings — covered directly (seed_error-capture+break is minimal; no dead code; no over-engineering) |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings — covered directly (Rule Compliance section below: 13 lang-review checks + project criticals) |

**All received:** Yes (1 enabled returned GREEN, 8 disabled pre-filled + covered directly)
**Total findings:** 2 confirmed (both LOW/note), 0 dismissed, 0 deferred

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** ruleset-module pack with failing encounter generation →
`seed_manual` (`pregen.py`) `_generate_encounter` returns `None` → `elif ruleset != "native"`
sets `seed_error` string + `break` → loop exits → `pregen.seed_manual` span opens with
`seed_error` (the message) + `ruleset` + `encounters_after=0` and closes (exported) →
`if seed_error is not None: raise EncounterSeedError` (before `manual.save()`, so no empty
pool persists) → propagates to `ensure_loaded` (`monster_manual_inject.py`) →
`except EncounterSeedError: raise` (re-raised past the broad except) → session bind crashes
loud. Safe + correct: the failure is now OTEL-visible (item 3) AND fatal (item 6, Keith
policy), with no disk write on the failure path.

**Observations (5+, none blocking):**
- `[VERIFIED]` **Span fires before the raise** — `pregen.py:402-413`: `seed_error` is captured
  (not raised) in the loop at `:349-356` with `break`; the `with Span.open(...)` block at
  `:~403` runs unconditionally and closes, THEN `if seed_error is not None: raise` at `:~411`.
  Evidence: the failure-path test reads `otel_capture.get_finished_spans()` and finds the span
  with a non-empty `seed_error` attr — green. Complies with the OTEL Observability Principle.
- `[VERIFIED]` **Raise precedes `save()`** — `pregen.py:~411` raise is above `manual.save()` at
  `:~415`, so a fail-loud seed never persists a silently-empty pool to disk. Complies with No
  Silent Fallbacks.
- `[VERIFIED]` **`except` ordering is correct** — `monster_manual_inject.py:95-101`:
  `except EncounterSeedError: raise` precedes `except Exception` (EncounterSeedError ⊂
  RuntimeError ⊂ Exception; Python matches in order), so the typed contract violation re-raises
  while generic/transient failures keep ADR-006 graceful degradation. Pinned by BOTH
  `test_ensure_loaded_reraises_encounter_seed_error` (re-raise) and the kept-green
  `test_ensure_loaded_swallows_seed_errors` (generic RuntimeError still degrades).
- `[VERIFIED]` **Wiring intact** — preflight confirms
  `test_websocket_session_handler_wires_monster_manual_inject` +
  `test_execute_narration_turn_refreshes_stale_monster_manual` pass; the changed `ensure_loaded`
  + `seed_manual` are on the real narration-turn path; item-3 test asserts the real OTEL span
  (behavior), not source text. Complies with "Every Test Suite Needs a Wiring Test" + "No
  Source-Text Wiring Tests".
- `[VERIFIED]` **Stale comment removed** — the old `ensure_loaded` except comment claimed "OTEL
  fires below regardless" but no span fires inside `ensure_loaded` (the span lives in
  `seed_manual` / per-turn inject); the diff removes that misleading line and the new comments
  accurately describe transient-vs-fatal. `monster_manual_inject.py:96-100`.
- `[LOW][EDGE]` **Behavior-change blast radius (intentional, noted not blocking)** — item 6
  changes a ruleset seeding failure from "empty pool, session runs" to "session bind crashes."
  This is Keith's explicit policy (2026-06-10) and the missing-bestiary case is CI-guarded; the
  partial-bestiary case (tier-2 empty) is mitigated by encountergen's existing tier-pool
  fallback (empty tier → full list), so a populated bestiary won't crash. Surfaced for the
  record — see Delivery Findings.
- `[LOW][EDGE]` **`seed_manual_complete` log now fires on the failure path** — because the raise
  moved past the loop, the `pregen.seed_manual_complete` census log (`:~358`) and the span now
  emit before the raise. The log is a census (counts), not a success assertion, so it's not
  misleading; it's actually desirable (the GM panel sees the failed seed's counts). Noted.

**Error handling:** ruleset seeding failure → typed `EncounterSeedError` with an actionable
message (names genre, ruleset, world, tier, the bestiary contract, and the log line to check),
OTEL-recorded, then fatal at the bind. Generic failures → warning + degrade. Bestiary content
boundary → pydantic validators (tested via `model_validate`). Correct and complete.

### Rule Compliance (lang-review/python.md — 13 checks + project criticals)

| Check | Verdict | Notes |
|-------|---------|-------|
| 1 Silent exception swallowing | **improved** | Diff ADDS a specific `except EncounterSeedError: raise` above the broad `except Exception` (noqa'd, warning-logged) — narrows, doesn't widen. |
| 2 Mutable defaults | compliant | `seed_error: str \| None = None`; no mutable defaults. |
| 3 Type annotations | compliant | `seed_error` annotated; test helpers annotated (`-> int`, `-> Any` on the SimpleNamespace stub, matching sibling `_stub_pack`). |
| 4 Logging | compliant | unchanged warning call; lazy `%s`. |
| 5 Path handling | n/a | no path handling in diff. |
| 6 Test quality | compliant | `pytest.raises(..., match=)`, non-empty-str span assert, parametrized bounds, deliberate-decision lock; no vacuous asserts. |
| 7 Resource leaks | compliant | `with Span.open(...)` closes; no new resources. |
| 8 Unsafe deserialization | n/a | none in diff. |
| 9 Async pitfalls | n/a | no async. |
| 10 Import hygiene | compliant | `Bestiary`/`BestiaryEntry` exported in `__init__` + `__all__`; `EncounterSeedError` added to the existing late import. Full suite passes → no circular import. |
| 11 Input validation | compliant | bestiary validators tested at the content boundary. |
| 12 Dependency hygiene | n/a | no dep changes. |
| 13 Fix-introduced regressions | compliant | full suite 10152 passed; 7 failures pre-existing + unrelated (audit/aside/dogfight/scene_harness — none touch this diff). |
| **No Silent Fallbacks** | compliant (strengthened) | item 6 re-raise + item 3 span-on-failure; no new fallback. |
| **No Stubbing** | compliant | no placeholders. |
| **Verify Wiring** | compliant | non-test consumers: narration turn → ensure_loaded → seed_manual; e2e span path. |
| **OTEL Principle** | compliant (the point) | failure path now emits `seed_error` on the `pregen.seed_manual` span. |
| **Test-suite wiring test** | compliant | item-3 span assertion + real ensure_loaded drive; no source-grep. |

### Devil's Advocate

Assume this is broken. The story moves a `raise` from mid-loop to after a span block — what if
the span block itself throws and pre-empts the raise? Then a failed seed would emit no error.
But `Span.open` is the same context manager used on the success path 10k times a suite; its
attrs here are str/int/bool only (`seed_error or ""` is always a str), so it cannot throw on
this input — and if it did, the exception would still propagate (louder, not silent). Next:
the re-raise in `ensure_loaded` crashes the session bind — a confused operator who adds a new
`ruleset:` pack without a bestiary now gets a hard crash instead of a quiet empty pool. Is that
a footgun? It's the *intended* footgun (Keith's strict-fail-loud policy), and it's strictly
better than the 87-4 bug it replaces (silent empty pool that looks fine until forensics). The
missing-bestiary case is named by a CI content-contract test, and the partial-bestiary case
(a bestiary with tier-1 but no tier-2 entries) is caught by encountergen's tier-pool fallback
(empty tier → sample the full list), so a *populated* bestiary never trips the crash. Third:
could `seed_error` be set but the raise skipped? No — `if seed_error is not None: raise` is
unconditional after the span, and `seed_error` is only assigned the non-None message string.
Fourth: the generic `except Exception` still swallows — could a real bug masquerade as a
"transient outage"? Yes, in principle (a `KeyError` in seed_manual would degrade silently) —
but that's the pre-existing ADR-006 posture this story deliberately scopes around (item 6
narrows the FATAL set to the typed contract error only; widening it further is out of scope and
would regress ADR-006). What saves the verdict: every assertion the story makes — span fires on
failure, ruleset attr present, validators enforced, re-raise fatal, generic still degrades — is
pinned by a test, and the 90-1 success path + integration suite stay green. The holes are
either intentional policy (the crash blast radius) or pre-existing posture (the generic
swallow), both on the record. Nothing blocks.

**Handoff:** To SM for finish-story.

## Delivery Findings (continued)

### TEA (RED)
- **Gap** (non-blocking): Story 90-5 was **partially overtaken** by the world-tier bestiary
  repoint — item 1 (encountergen exit-1 test) is already covered by
  `test_main_fails_loud_when_ruleset_module_resolves_no_bestiary`, and the awn-wording polish
  is moot (the AC6 slug tuple was removed). Re-scoped RED to items 2–6 + remaining polish; no
  duplicate tests written. The story still carries ~2pt of real failure-path hardening (2 fixes
  + 3 coverage locks). *Found by TEA during 90-5 RED.*
- **Improvement** (non-blocking): the hp-floor-header polish (Reviewer 90-1) spread with the
  repoint — now 3 space_opera world-tier bestiaries + mutant_wasteland genre-tier, not the 2
  genre-tier files 90-1 named. Listed for Dev; verify values are floor before rewording. *Found
  by TEA during 90-5 RED.*
- **Gap** (non-blocking, **echo of 90-1**): `pregen.namegen_failed (exit_code=1)` still silently
  skips NPC seeding for some cultures via the same warning-only `_run_cli_capturing_json` path —
  the SAME anti-pattern 90-5 retires for *encounters*. 90-5 deliberately scopes to encounters;
  this NPC-seeding twin still wants its own follow-up (TEA+Dev both flagged it in 90-1). *Found
  by TEA during 90-5 RED.*

### Dev (implementation)
- **Improvement** (non-blocking): the affected bestiary `hp` values are `round(4.5 × HD)`
  (banker's rounding: L1=4, L2=9, L3=14, L5=22 — note L3=14 ≠ `floor(13.5)=13`), so the
  existing "hp == average (4.5/HD)" headers are ACCURATE; the 90-1 "floor" diagnosis was
  imprecise. No content change made. If a future pass wants exactness, the precise wording is
  "average (4.5/HD), banker's-rounded." Affects 4 content bestiary headers (left as-is).
  *Found by Dev during implementation.*

### Reviewer (code review)
- **Improvement** (non-blocking): item 6 changes a ruleset seeding failure's blast radius from
  "empty pool, session runs" to "session bind crashes" — Keith's intended strict-fail-loud
  policy, mitigated for populated bestiaries by encountergen's tier-pool fallback. If a future
  ruleset binding (e.g. epic-89 Barsoom) ever ships without a bestiary, the session will now
  hard-crash at bind rather than degrade — that is by design, but worth a one-line note in the
  pack-authoring docs so an author sees "bestiary REQUIRED or the session won't start." Affects
  pack-authoring docs (no code change). *Found by Reviewer during code review.*
- **Gap** (non-blocking, echo of TEA/Dev): the generic `except Exception` in `ensure_loaded`
  still swallows non-`EncounterSeedError` seed failures (ADR-006). 90-5 correctly scopes the
  fatal set to the typed contract error only; if a future story wants tighter seeding
  observability, a dedicated `monster_manual.seed_failed` OTEL span at that swallow point (vs
  the current `logger.warning`) would close it. Affects
  `sidequest/server/dispatch/monster_manual_inject.py`. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (RED)
- **Dropped item 1 (encountergen exit-1 test) — already covered upstream**
  - Spec source: 90-5 story title + context Technical Approach item 1 ("test encountergen
    exit-1 (bestiary-less ruleset pack)")
  - Spec text: "test encountergen exit-1 (bestiary-less ruleset pack)"
  - Implementation: NOT written — `tests/cli/test_encountergen_bestiary_90_1.py::test_main_fails_loud_when_ruleset_module_resolves_no_bestiary`
    (added by the world-tier bestiary repoint after 90-1) already drives a ruleset-module pack
    with no bestiary and asserts `rc == 1` + stderr names the bestiary/REQUIRE contract. Writing
    a second is the prod-duplicate anti-pattern.
  - Rationale: the 90-1 archive predates the repoint; 90-5's premise is partially stale (see
    Delivery Findings). Confirmed the repro is already covered before writing RED.
  - Severity: minor
  - Forward impact: none — coverage exists; if Dev's item-3 refactor touches the encountergen
    exit-1 path, that test guards it.
- **Dropped the "awn in AC6 wording" polish — moot**
  - Spec source: story title polish list ("awn in AC6 wording")
  - Spec text: "awn in AC6 wording"
  - Implementation: NOT done — the AC6 slug tuple the wording lived in was removed by the
    repoint (the generality assertion is now seam tests), and the surviving ruleset reference
    (`pregen.py:50`) already reads `wwn|cwn|swn|awn`.
  - Rationale: nothing left to reword.
  - Severity: trivial
  - Forward impact: none.

### Dev (implementation)
- **Dropped the hp-floor header reword — measurement contradicts the spec premise**
  - Spec source: 90-5 story title + context polish sweep ("hp-floor headers")
  - Spec text: "fix 'hp == average (4.5/HD)' header wording to 'floor' in space_opera +
    mutant_wasteland bestiaries"
  - Implementation: NO content change. Measured the actual values: L1=4, L2=9, L3=14, L5=22 =
    `round(4.5 × HD)` (banker's rounding), NOT floor — `floor(13.5)` would be 13, but L3=14.
    The existing "average (4.5/HD)" header is therefore accurate; rewording to "floor" would
    INTRODUCE an inaccuracy.
  - Rationale: measure, don't assert — the 90-1 "floor" observation was imprecise. Making a
    cosmetic edit that makes the doc wrong fails the polish's own intent.
  - Severity: trivial
  - Forward impact: none — content unchanged; the `sidequest-content` feature branch carries no
    commits for this story (SM finish can skip/clean it). If exactness is ever wanted, the precise
    phrase is "average (4.5/HD), banker's-rounded."

### Reviewer (audit)
- **TEA: Dropped item 1 (encountergen exit-1 test)** → ✓ ACCEPTED by Reviewer: confirmed
  `test_main_fails_loud_when_ruleset_module_resolves_no_bestiary` already drives a ruleset pack
  with no bestiary and asserts rc 1 + the contract message; a second test would be a prod-duplicate.
  Re-baselining before RED is exactly right.
- **TEA: Dropped the "awn in AC6 wording" polish** → ✓ ACCEPTED by Reviewer: the AC6 slug tuple
  was removed by the repoint and the surviving ruleset reference already reads `wwn|cwn|swn|awn`;
  nothing to reword.
- **Dev: Bestiary REQUIRED enforced at the generation seam, not load-time** (inherited 90-1
  contract; this story's item 6 hardens the seam) → ✓ ACCEPTED by Reviewer: item 6's re-raise puts
  the fatal enforcement exactly at the seam (`ensure_loaded`), where the 87-4 bug lived — load-time
  enforcement would break synthetic-fixture packs for no production benefit.
- **Dev: Dropped the hp-floor header reword (measurement contradicts premise)** → ✓ ACCEPTED by
  Reviewer: independently confirmed the values are `round(4.5 × HD)` (L3=14 ≠ floor 13), so the
  "average (4.5/HD)" header is accurate and the "floor" reword would introduce an error. Measuring
  before editing is the correct call; content branch legitimately empty.