---
parent: context-epic-98.md
workflow: tdd
---

# Story 98-2: S1 Server — per-region system-file resolution in orbital/loader.py (system_root() unchanged)

## Business Context

This is the **server hinge** of the critical path. Once 98-1 splits orbital data
into `systems/<id>.yaml`, the server must load the *right* file for the system the
party currently occupies — replacing today's single hard-coded
`world_dir / "orbits.yaml"`. This is what turns "one file per system" from a
content convention into runtime behavior: drill into a node → load that node's
orrery file → render it via the existing, verified renderer.

The architectural win is **reuse**: `system_root()` (the drill-down scope: one
parent-less primary + direct children) stays **verbatim**. Because 98-1 makes
each system file have exactly one parent-less primary, the existing contract holds
unmodified once the fake root is gone. The whole story is principally a *which
file to load* change, not a rendering or scope change.

## Technical Guardrails

**Lane:** Dev. **Repo:** server.

**Key files (per epic spec §2 seam corrections — the ADR pointer was imprecise):**
- `orbital/loader.py:42` — the hard-coded `world_dir / "orbits.yaml"` → `OrbitalContentMissingError` (loader.py:47). **This is the single path that must become per-region.**
- `orbital/render.py:132` — `system_root()`. **Read-only confirm — used unchanged.** (The ADR pointer said `course.py`; the real definition is in `render.py`.)
- `orbital/scope_bind.py` — scope selection keyed to the current node.
- `orbital/models.py` — `OrbitsConfig` shape is **unchanged per file**; each `systems/<id>.yaml` parses to one `OrbitsConfig`.

**Patterns to follow:**
- Resolve `worlds/<world>/systems/<region_id>.yaml` keyed to the **party's current region**. The region id is the key — confirm where current region lives in session/game state (the cartography/region layer that already feeds `movement.py`).
- **Fail loud** on a missing system file (No Silent Fallbacks): raise a clear error naming the missing path. Do **NOT** fall back to a cluster-wide chart or the retired monolith.
- Emit an **OTEL span** on resolution (region → file → hit/miss) — the GM panel is the lie detector for whether resolution actually fired.

**What NOT to touch:**
- Do **not** modify `system_root()` — the moment you change it, the reuse argument collapses.
- Do **not** touch the ADR-130 intra-system course model.
- Do **not** add jump adjudication (that is 98-5).

## Scope Boundaries

**In scope:**
- Per-region resolution of `systems/<region_id>.yaml` in `loader.py`.
- Fail-loud on missing file, naming the path.
- OTEL span on resolution.
- Confirm `system_root()` works verbatim against a 98-1 `yula.yaml`.
- `coyote_star` regression coverage.

**Out of scope:**
- Authoring content (98-1).
- UI two-scale rendering (98-3).
- Jump mechanics / SWN seam (98-5).

## AC Context

- **AC1 — per-region resolution replaces the hard-coded path.** `loader.py`
  computes `worlds/<world>/systems/<region_id>.yaml` from the party's current
  region, no longer reading `world_dir / "orbits.yaml"`. *Test:* with party in
  `yula`, the loader opens `systems/yula.yaml`; assert the hard-coded path is gone.
- **AC2 — `system_root()` unchanged + wiring test.** The drilled-in scope for
  `yula` returns `yula`'s primary as root, using `render.py:132` verbatim. *Test
  (wiring, CLAUDE.md mandate):* assert the loader is reached from a **production**
  code path (not just a unit harness) for `yula`, and the resolved scope's root is
  `yula`.
- **AC3 — fail loud on missing file.** Current region has no `systems/<id>.yaml`
  → raise a clear error naming the missing path; do **not** fall back to a
  cluster chart. The galactic graph still renders that node; only the orrery
  drill-down is unavailable. *Test:* drill into a node with no system file →
  assert the specific error (with path) is raised, not a silent empty/monolith
  chart. *Edge case:* the retirement-stub form of `orbits.yaml` (if 98-1 chose a
  stub over deletion) must NOT satisfy resolution — coordinate with 98-1 AC4.
- **AC4 — OTEL on resolution.** A span records region, resolved file, and
  hit/miss. *Test:* assert the span is emitted with those attributes on both a hit
  (`yula`) and a miss (unauthored node).
- **AC5 — `coyote_star` regression.** The single-system world's orrery still
  loads as before — its lone-system path collapses the two scales cleanly. *Test:*
  load `coyote_star`; assert its orrery resolves and renders unchanged (one node →
  orrery-as-Map; no per-region key needed because there is one system).

## Assumptions

- The party's **current region id** is available to `loader.py` (or threadable to it) from existing session/game state — the same region layer that feeds `dungeon/region_projection.py` and `movement.py`. If region id is not reachable at the loader seam without new plumbing, log a Design Deviation; that changes the story's size.
- 98-1 is **merged before** this story starts (sequenced C1 → S1), so `systems/yula.yaml` exists to resolve. If 98-1 chose the retirement-stub form for `orbits.yaml`, the loader must treat the stub as "no monolith" — confirm the exact stub shape.
- `coyote_star` genuinely has one system node, so the resolver can collapse to its single orrery without a per-region key. If `coyote_star` turns out to need a `systems/coyote.yaml` rename to share the code path, that is a small content follow-up — flag it rather than special-casing single-system worlds in the loader.
