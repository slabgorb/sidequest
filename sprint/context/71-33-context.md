# Story Context: 71-33 — Migrate pulp_noir scenarios to world tier

**Type:** bug (regression) · **Points:** 3 · **Priority:** p2
**Workflow:** trivial (re-scoped from tdd by SM — see Scope Deviation)
**Repos:** content (re-scoped from `server,content` — see Scope Deviation)
**Branch:** `71-33-migrate-pulp-noir-scenarios-world-tier` (content)

## The regression (CONFIRMED real, not stale)

71-32 ("World-level scenario discovery + world-aware binding", merged) made
`bind_scenario` read **only** `pack.worlds[world_slug].scenarios` — Option A, no
pack-level fallback (No Silent Fallbacks). pulp_noir's sole world `annees_folles`
ships **no** `worlds/annees_folles/scenarios/` dir, so pulp_noir now **binds no
scenario at session start** (it previously bound `midnight_express` via the old
world-agnostic `next(iter(pack.scenarios))`).

This was the **intended, deferred** Option-A consequence. The 71-32 Architect
spec-check explicitly recommended SM file this exact follow-up
(see `sprint/archive/71-32-session.md`, Architect Delivery Finding + reconcile manifest).

**Grounded facts (verified 2026-05-30, SM):**
- pulp_noir scenarios live at PACK tier as directory-style multi-file scenarios:
  - `genre_packs/pulp_noir/scenarios/midnight_express/` (scenario.yaml, clue_graph.yaml, npcs.yaml, assignment_matrix.yaml, atmosphere_matrix.yaml)
  - `genre_packs/pulp_noir/scenarios/the_warehouse/` (same 5-file structure)
- `genre_packs/pulp_noir/worlds/annees_folles/` has NO `scenarios/` dir. Confirmed `NO_SCENARIOS_DIR_CONFIRMED`.
- Precedent: 71-32 did the identical move for tea_and_murder — `git mv scenarios/the_morning_train → worlds/glenross/scenarios/the_morning_train`.

## The fix (content-only)

`git mv` both scenario directories from pack tier into the `annees_folles` world:

```
git mv genre_packs/pulp_noir/scenarios/midnight_express \
       genre_packs/pulp_noir/worlds/annees_folles/scenarios/midnight_express
git mv genre_packs/pulp_noir/scenarios/the_warehouse \
       genre_packs/pulp_noir/worlds/annees_folles/scenarios/the_warehouse
```

Use `git mv` so history follows. After the move, the pack-tier
`genre_packs/pulp_noir/scenarios/` dir should be empty — remove it if git leaves it.

### Check before moving — does anything need editing inside the YAML?
- 71-32's loader (`_load_single_world`) discovers `worlds/<w>/scenarios/` by
  **directory location**, mirroring pack-root discovery. The tea_and_murder move
  in 71-32 was a pure relocation. **Default expectation: pure `git mv`, no YAML edits.**
- BUT measure, don't assume: open each `scenario.yaml` and check whether it carries
  any pack-relative path, `world:` key, or `world_specific:` flag that the
  world-tier loader keys on. The 71-32 tea_and_murder scenario did not need flag
  edits — match that precedent. Only edit a field if live verification proves the
  loader requires it.

## Acceptance Criteria
1. `midnight_express` and `the_warehouse` relocated to
   `genre_packs/pulp_noir/worlds/annees_folles/scenarios/` via `git mv` (history preserved).
2. Pack-tier `genre_packs/pulp_noir/scenarios/` no longer contains them (empty/removed).
3. **Live verification (the real AC):** loading pulp_noir with `annees_folles` active,
   `bind_scenario` binds a scenario (no `scenario.bind_skipped` /
   `reason: no_world_scenario`). Capture the OTEL/return evidence — measure, don't assert.
4. Both scenario YAMLs still parse and load (no schema breakage from the move).

## Verification (no new server tests)
- **Operator directive (load-bearing):** do NOT write a server test that points at the
  live pulp_noir content (prod-rows-in-tests anti-pattern). 71-32 already covers the
  *mechanism* with hermetic synthetic-pack fixtures; this story changes only content.
  This is why the story was re-scoped off the server repo.
- Verify by **loading the real pack** (a one-off script / REPL / the validator), not a
  committed test:
  - Confirm `pack.worlds["annees_folles"].scenarios` is non-empty and contains
    `midnight_express` + `the_warehouse`.
  - Confirm a bind against `annees_folles` returns a scenario (was `None` pre-fix).
  - Confirm both YAMLs `safe_load` cleanly.
- Relevant server code to read for the verification harness (DO NOT edit):
  `sidequest/genre/loader.py` (`_load_single_world`), `models/pack.py` (`World.scenarios`),
  `sidequest/server/dispatch/scenario_bind.py` (`bind_scenario`).

## Scope Deviation (logged by SM)
- **YAML says `repos: server,content` + `workflow: tdd`.** Re-scoped to
  **content-only + trivial** because: (a) the binding mechanism already shipped in
  71-32 — no server code change is needed; (b) the Operator directive forbids server
  tests pointing at real content, so a tdd RED test would be hermetic-synthetic and
  would NOT actually guard pulp_noir; (c) the real work is a 2-directory `git mv`.
- CLI limitation: `pf sprint story update` has no `--repos` flag. Workflow set to
  `trivial` via CLI; **repos is governed by this context + the session `Repos:` line**
  (per project convention — the session Repos line is authoritative). YAML still reads
  `server,content`; this mismatch is a known, accepted deviation. At finish, create +
  merge the PR for **content only**.

## Out of scope
- No new world scaffolding. No server code changes. No edits to scenario narrative
  content beyond any loader-required field (none expected). No changes to `midnight_express`
  / `the_warehouse` story logic.

## References
- `sprint/archive/71-32-session.md` (the parent story — full mechanism + the Architect
  follow-up recommendation that spawned this story)
- `sprint/context/context-story-71-32.md` (71-32 design narrative)
- ADR-053 (Scenario System)
