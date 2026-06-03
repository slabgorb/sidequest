---
parent: context-epic-72.md
workflow: trivial
---

# Story 72-15: Rescue test_pregen.py from the caverns_sunden blanket-skip + fix stale _stub_pack

## Business Context

Test debt surfaced by 72-11. `tests/server/dispatch/test_pregen.py` is **entirely**
skip-listed in `tests/conftest.py` (`_CAVERNS_SUNDEN_DEPRECATED_TESTS`,
conftest.py:201/217) because its *one* e2e test
(`test_e2e_seed_caverns_sunden_populates_manual`, test_pregen.py:408) binds the
**deprecated** `caverns_sunden` world. That over-broad **file-level** skip sweeps in
~16 world-**agnostic** `seed_manual` unit tests that have nothing to do with
caverns_sunden — the same trap the conftest's own NOTE rescued `test_pov_swap` from.

Why it matters: pregen (server-side Monster-Manual seeding, ADR-059) is a **live**
subsystem, and CLAUDE.md forbids skipping tests for live subsystems. Right now ~16
unit tests that should guard it are dark, so a regression in `seed_manual`'s
culture/archetype logic would pass CI silently. This story turns the tests back on.

## Technical Guardrails

**Tests + conftest only — no production change.** Repo: `sidequest-server`.

The rescue has three parts (all verified against the live tree):

1. **Fix the stale `_stub_pack`** (`test_pregen.py:185`). It currently exposes a
   `.cultures` attribute, but `seed_manual` now calls `pack.effective_cultures(world)`
   (`sidequest/server/dispatch/pregen.py:223`). So if the unit tests were naively
   un-skipped they would **ERROR**, not pass. `_stub_pack` must implement
   `effective_cultures(world)` returning the stub's culture list (matching the real
   `effective_cultures` contract — see ADR-121 effective-cultures resolution).
2. **Re-point the deprecated e2e** (`test_e2e_seed_caverns_sunden_populates_manual`,
   test_pregen.py:408/411/415) off `caverns_sunden`. **Operator decision (2026-06-03):
   target a DEDICATED TEST FIXTURE pack/world, NOT a live genre-pack world**
   (coyote_star / caverns_and_claudes). Live content is mid-migration (71-31) and
   coupling a test to it would re-introduce exactly the fragility 72-11 deliberately
   avoided. This also honors the standing rule that *tests must not point at live
   content*.
3. **Remove `test_pregen.py` from the conftest skip set**
   (`_CAVERNS_SUNDEN_DEPRECATED_TESTS`, conftest.py:217) so all ~16 unit tests **and**
   the re-pointed e2e run.

**Do not:**
- Re-render, re-add, or revive the `caverns_sunden` world — it is deprecated; the e2e
  must move *off* it, not resurrect it.
- Touch production code — `_stub_pack` and the e2e fixture are test-side only.
- Couple the re-pointed e2e to any live genre-pack world.

## Scope Boundaries

**In scope:**
- `_stub_pack` gains a working `effective_cultures(world)`.
- The caverns_sunden e2e re-pointed to a dedicated test fixture pack/world.
- `test_pregen.py` removed from the conftest skip set; all ~16 unit tests + the
  re-pointed e2e run green.
- This is the proper home for 72-11's AC5 ("existing pregen tests stay green") — those
  named tests were skipped-and-stale; this story makes them actually green.

**Out of scope:**
- Any `seed_manual` / pregen production behavior change.
- Broader conftest skip-list cleanup beyond `test_pregen.py`.
- The 71-31 live-content culture migration (only the *fixture* is built here).

## AC Context

Trivial workflow — Dev implements directly, no separate RED phase. Completion criteria:

- **AC1 — Unit tests un-skipped and green.** `test_pregen.py` is removed from
  `_CAVERNS_SUNDEN_DEPRECATED_TESTS`; the ~16 world-agnostic `seed_manual` unit tests
  run and pass. *Verify:* `uv run pytest tests/server/dispatch/test_pregen.py -v` shows
  them collected (not skipped) and passing.
- **AC2 — `_stub_pack` implements `effective_cultures(world)`.** The stub no longer
  ERRORs against the current `seed_manual` call site (pregen.py:223). *Verify:* the
  unit tests that build `_stub_pack([...])` exercise the `effective_cultures` path
  without AttributeError.
- **AC3 — e2e re-pointed to a dedicated fixture, off caverns_sunden.** No live
  genre-pack world is bound; `caverns_sunden` is no longer referenced by the test.
  *Verify:* grep the test file for `caverns_sunden` → absent; the e2e passes against
  the fixture.
- **AC4 — Full suite stays green.** No other test regresses from un-skipping (run with
  `SIDEQUEST_GENRE_PACKS` + `SIDEQUEST_DATABASE_URL` set — see the testing-env notes;
  the genre-calibration tests need the packs path).

## Assumptions

- The dedicated test fixture pack/world does not yet exist and must be built minimally
  (just enough for `seed_manual` to populate a `MonsterManual`), OR an existing
  test-fixture pack under `tests/` can be reused. Dev to check `tests/` for an existing
  fixture pack before authoring a new one (reuse-first).
- `effective_cultures(world)` on the real pack returns `(effective, cultures_source)`
  (pregen.py:223 unpacks a 2-tuple) — the stub must match that arity, not return a bare
  list.
- The ~16 unit tests are genuinely world-agnostic (they monkeypatch `load_genre_pack`
  with `_stub_pack`), so re-pointing the *e2e* and fixing the *stub* is sufficient to
  un-skip the whole file.
