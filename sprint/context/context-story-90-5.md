# Story 90-5 Context

## Title
90-1 fail-loud hardening — pin the failure-path contract from review: test encountergen exit-1 (bestiary-less ruleset pack) + EncounterSeedError raise; emit pregen.seed_manual span (error attr) before raising; assert ruleset span attr in AC4; unit-test Bestiary validators; decide ensure_loaded broad-except policy for EncounterSeedError (ADR-006 vs fail-loud); doc/content polish (stale docstrings, awn in AC6 wording, hp-floor headers, derive AC6 slug list from rules.yaml scan)

## Metadata
- **Story ID:** 90-5
- **Type:** chore
- **Points:** 3
- **Priority:** p2
- **Workflow:** tdd
- **Repo:** server
- **Epic:** Ruleset-Module Worlds — Live Combat & Magic Verification Enablement

## Problem
90-1 shipped the "fail loud, never a silent empty pool" bestiary contract for
ruleset-module packs (encountergen + `pregen.seed_manual`), but the Reviewer
APPROVED-with-findings: the **success path** is fully delivered, pinned, and
CI-guarded — the **failure path** has no regression tests and degraded
observability. The fail-loud retirement is "one revert away from silently
un-happening" (monkeypatch `_generate_encounter → None`, revert the raise to a
warning, and the entire 90-1 suite still passes). This story pins that contract.

**Authoritative source — the 90-1 Reviewer "Gap (blocking-for-epic-90)" finding**
(`sprint/archive/90-1-session.md`, Delivery Findings → Reviewer; the numbered list
below is verbatim from it). Read the full 90-1 archive Reviewer Assessment +
Delivery Findings before writing RED — it carries exact file:line anchors.

## Technical Approach
Six items, drawn from the 90-1 review (TEA refines exact RED encoding):

1. **Test the encountergen exit-1 branch** — synthetic `ruleset != native` pack
   with no `bestiary.yaml` → assert rc 1 + actionable stderr (the missing failure
   test; today a revert to silent-skip passes the suite).
   (`sidequest/cli/encountergen/encountergen.py` main bestiary branch.)
2. **Test the `EncounterSeedError` raise** — monkeypatch `_generate_encounter` →
   `None` on a ruleset pack → assert it raises (not warns).
   (`tests/server/dispatch/test_pregen_bestiary_90_1.py`.)
3. **Emit the `pregen.seed_manual` span (with an error attribute) before raising** —
   today `seed_manual` raises before `Span.open(SPAN_PREGEN_SEED_MANUAL)`, so the
   seeding-failure decision emits NO seeding span (old code at least emitted
   `encounters_after=0`). Make the failure GM-panel-visible at the seeding layer.
   (`sidequest/server/dispatch/pregen.py:~305` vs `:340`.) **OTEL Principle.**
4. **Assert the `ruleset` span attribute in AC4** — the existing AC4 test doesn't
   assert the new `ruleset` attr (the "which path fired" proof the code comment
   claims). (`test_pregen_bestiary_90_1.py:79`.)
5. **Unit-test the `Bestiary`/`BestiaryEntry` validators** — dup-id rejection,
   empty-entries rejection, `ge=1` bounds — via `Bestiary.model_validate`, not raw
   `yaml.safe_load`. (`sidequest/genre/models/bestiary.py`.)
6. **Decide the `ensure_loaded` broad-except policy for `EncounterSeedError`** —
   `monster_manual_inject.py:95`'s pre-existing `except Exception` swallows the new
   typed error → at runtime, behaviorally identical to the 87-4 bug (better logs,
   same empty pool). Decide: re-raise / special-case, or emit a dedicated loud
   watcher event, vs. accept graceful degradation per **ADR-006**. This is the
   load-bearing call — settle it deliberately (Keith may weigh in).

**Doc/content polish sweep** (Reviewer "Improvement" finding):
- Refresh stale docstrings: `seed_manual` ("falls back to humanoid NPCs"),
  encountergen module header (omits bestiary path), `pack.py:253` bestiary field
  (omit pregen raise); retire "RED … FAIL until" framing in both 90-1 test modules.
- AC6 wording: `"wwn/cwn/swn"` → `"wwn/cwn/swn/awn"` in docstring + message.
- hp-floor headers: `space_opera/bestiary.yaml:7` + `mutant_wasteland/bestiary.yaml:8`
  say "hp == average (4.5/HD)" but use floor — fix to "floor".
- **Derive the AC6 slug list from a `genre_packs/*/rules.yaml` scan** (`ruleset != native`)
  instead of the hand-maintained snapshot tuple — 88-2 already proved it goes stale
  mid-flight. (`tests/cli/test_encountergen_bestiary_90_1.py`.)
- Minor: remove dead `rng`/`del rng` lines; pin `--count` in the two bare-truthy
  asserts; add `-> Path` to `_pack_dir_or_skip`; export bestiary models in
  `sidequest/genre/models/__init__.py` `__all__`.

**Two repos:** server carries items 1–6 + most polish; content carries the two
bestiary-header hp-floor wording fixes (`space_opera`, `mutant_wasteland`).

## Scope
- **In scope:** the six failure-path/observability items + the doc/content polish
  sweep above. Pure hardening of the 90-1 contract.
- **Out of scope:** the `pregen.namegen_failed` silent-skip (separate NPC-seeding
  gap, TEA+Dev both flagged it for a different follow-up); WWN-SRD numeric fidelity
  of authored bestiary stats (authoring judgment); any change to the 90-1 success
  path (populated pools, native regression) — those are delivered and must stay green.

## Acceptance Criteria
_TEA owns the final RED encoding. Draft AC checklist = the six numbered items above
(each becomes a failing test or a deliberate decision-with-rationale) + the polish
sweep (verified by the refreshed assertions/docstrings). Item 6 is a decision AC:
its "test" is the documented policy + whatever guard that policy implies (re-raise
test, or a watcher-event assertion). The regression guard: the full 90-1 suite +
`test_wwn_heavy_metal_combat` stay green._

---
_Generated by `pf context create story 90-5` from the sprint YAML._
