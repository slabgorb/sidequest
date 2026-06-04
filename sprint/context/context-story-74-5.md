---
parent: context-epic-74.md
workflow: tdd
---

# Story 74-5: Convert content-pointing lore-seeding tests to synthetic fixtures (no real-pack coupling)

## Business Context

Epic 74 moves all *flavor* (lore, cultures, archetypes, theme, etc.) out of the genre
tier and into the world tier, then deletes the now-redundant genre-tier files. Tests that
load **real genre packs** from `sidequest-content/` to exercise lore-seeding logic are a
hidden blocker on that end state: the moment a real pack's `lore.yaml` is slimmed, moved,
or deleted, these tests break for reasons that have nothing to do with the seeding code
they claim to test. They couple *engine behavior* to *content shape*.

This story is a direct application of project doctrine (CLAUDE.md / memory
`feedback_no_content_in_unit_tests`): **pytest tests CODE with synthetic fixtures;
content invariants (every world has lore, all packs load) belong in the pack VALIDATOR,
never in unit tests.** Converting the lore-seeding suite to the existing synthetic
`test_genre` fixture pack decouples the seeding logic tests from live content, so the
74-1/74-4 loader and per-world migration work can proceed without a wave of false test
failures. Expected outcome: the lore-seeding unit tests pass identically whether or not
any real pack ships `lore.yaml`.

## Technical Guardrails

**The synthetic-fixture pattern already exists — wire it up, don't reinvent it.**

- **Canonical fixture pack:** `sidequest-server/tests/fixtures/packs/test_genre/` — a
  minimal, complete pack that already ships `lore.yaml`, `tropes.yaml`, and a
  `worlds/flickering_reach/` world. This is the synthetic substitute for
  `caverns_and_claudes`.
- **Clone-a-fixture helper:** `MinimalPack` / `minimal_pack_factory` in
  `sidequest-server/tests/conftest.py` (root-scoped, visible to `tests/game/` and
  `tests/server/`). It copies `test_genre` into `tmp_path` and exposes mutable YAML
  setters (`set_rules_yaml`, `set_classes_yaml`, `create_spells_dir`). **It has no lore
  setter today** — if a test needs custom lore content, add a `set_lore_yaml(...)` /
  `set_world_lore_yaml(...)` method here (one definition, root conftest), mirroring the
  existing setters. Do not scatter ad-hoc YAML writers across test files.
- **Seeding code under test (do NOT modify):**
  `sidequest-server/sidequest/game/lore_seeding.py`. This story changes **tests only** —
  no production behavior change. If a test can only pass by editing `lore_seeding.py`,
  that is a Design Deviation; stop and notify SM.

**Target test files (the content-pointing lore-seeding tests):**

| File | Coupling today | Notes |
|---|---|---|
| `tests/game/test_lore_seeding.py` | `caverns_pack` module fixture → `load_genre_pack(CONTENT_ROOT / "caverns_and_claudes")` (lines 32, 139–143); world-seed tests consume it | Primary target. Swap `caverns_pack` → cloned `test_genre` + `flickering_reach`. |
| `tests/server/test_lore_store_resume_reseed.py` | same `caverns_pack` real-pack fixture (lines 41–49); skips if pack has no worlds | Swap to synthetic; the skip-guard disappears because `test_genre` always ships a world. |
| `tests/game/test_lore_seeding_arc_promotion.py` | only a **string literal** `genre_slug="caverns_and_claudes"` (line 45) — no disk load | **Verify first:** likely needs only the slug string changed (or left as an opaque label), not a real-pack swap. Don't over-convert. |
| `tests/server/test_lore_seeding_dispatch.py` | drives chargen confirmation against `caverns_and_claudes/grimvault` end-to-end (lines 44, 77–81, 144…) | Heavier integration/dispatch test. See Scope Boundaries — the wiring smoke may legitimately keep one real-pack path. |

**Invariants:**
- **No Silent Fallbacks** — synthetic fixtures must assert on *known* synthetic content
  (IDs/strings authored in `test_genre/lore.yaml`), not on whatever the real pack happened
  to contain. Tests should encode their own expected values.
- **CONTENT_ROOT removal** — once a file no longer loads a real pack, delete its
  `CONTENT_ROOT` constant and the `load_genre_pack(CONTENT_ROOT / ...)` import path so the
  coupling can't silently creep back.
- **Determinism** — synthetic lore IDs/slugs must be stable so world-scoped-ID assertions
  (e.g. `test_world_lore_seeded_with_world_scoped_ids`) remain meaningful.

## Scope Boundaries

**In scope:**
- Convert the unit-level lore-seeding tests (`test_lore_seeding.py`,
  `test_lore_store_resume_reseed.py`, and the lore-seeding portions of any sibling) from
  real-pack loads to the synthetic `test_genre` fixture pack via `MinimalPack`.
- Add a lore setter to `MinimalPack` in root `conftest.py` if custom lore content is
  required by any converted test.
- Verify `test_lore_seeding_arc_promotion.py` — change only what's actually coupled (the
  slug literal), don't manufacture a real-pack→synthetic swap where none exists.
- Remove now-dead `CONTENT_ROOT` constants / real-pack imports from converted files.
- Keep at least one wiring/integration test proving the seeder reaches the LoreStore from
  a production-style load path (CLAUDE.md: "Every Test Suite Needs a Wiring Test").

**Out of scope:**
- Any change to `lore_seeding.py` or other production seeding code.
- Slimming, moving, or deleting real packs' `lore.yaml` (that's the per-world migration /
  74-1 loader work).
- Converting non-lore real-pack tests (chargen, dispatch, retrieval) except where they are
  *part of* the lore-seeding suite.
- Deciding the genre-lore-optional loader change (74-1) — this story does not touch the
  loader contract.

## AC Context

1. **No lore-seeding unit test loads a real genre pack.** Verify: `grep` the converted
   files for `caverns_and_claudes` / `space_opera` / `CONTENT_ROOT` / `load_genre_pack(...
   genre_packs ...)` returns nothing in the unit-level files. A test must pass with the
   `sidequest-content/` tree absent or with `lore.yaml` removed from any real pack.

2. **Converted tests use the `test_genre` fixture pack and assert on synthetic content.**
   World-scoped-ID and slug-metadata assertions reference IDs authored in
   `test_genre/lore.yaml` + `worlds/flickering_reach/`, not values inherited from a real
   pack. Edge case: a fixture world with an empty/duplicate lore entry should still drive
   the idempotency and dedup tests (`test_idempotent_second_call_adds_nothing`,
   `test_duplicate_ids_are_skipped_not_raised`).

3. **`MinimalPack` gains a lore setter only if needed**, defined once in root
   `conftest.py`, with safe defaults for all required fields (mirror `set_rules_yaml`).
   Verify: no per-file YAML-writing helpers duplicate it.

4. **The skip-guard for "pack has no worlds" is removed** in
   `test_lore_store_resume_reseed.py` — `test_genre` always ships `flickering_reach`, so
   the resume-reseed path is exercised unconditionally (no silent skip masking a regression).

5. **At least one wiring test remains** proving world-lore seeding reaches the LoreStore
   through a production-style code path. Edge case: this test may use a synthetic pack but
   must exercise the real `lore_seeding` entry point, not a hand-rolled stub.

6. **Full server suite stays green.** `just server-test` (or the affected files) passes.
   Note (memory `project_server_test_otel_deadlock`): OTEL span-count tests can deadlock
   under full parallel runs — run any touched OTEL-adjacent files serially with `-n0`.

## Assumptions

- The `test_genre` fixture pack's `lore.yaml` + `flickering_reach` world contain (or can
  be extended to contain) enough lore entries to exercise world-scoped-ID generation,
  metadata stamping, idempotency, and dedup. If the fixture lore is too thin, extend the
  fixture pack (preferred) or add a `set_lore_yaml` override — do not fall back to a real
  pack.
- `test_lore_seeding_arc_promotion.py`'s `genre_slug="caverns_and_claudes"` is a label
  passed to seeding logic, not a disk load — so it needs at most a string change. Confirm
  during RED.
- `test_lore_seeding_dispatch.py` is an integration/dispatch test; if the team rules it the
  designated wiring test, it may retain a single real-pack path (AC5) rather than being
  fully synthesized. Confirm scope with SM if conversion would delete the only end-to-end
  seeding wiring proof.
- Base branch for `sidequest-server` is `develop` (dual-clone topology — orchestrator PRs
  target `main`, subrepo PRs target `develop`).

If any assumption proves wrong during implementation, log a Design Deviation and notify SM.
