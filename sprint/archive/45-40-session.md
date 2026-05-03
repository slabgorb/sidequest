# Standalone: Course overlay aesthetic alignment with Star Wars HUD palette

**Story:** 45-40
**Epic:** 45 — Playtest 3 Closeout — MP Correctness, State Hygiene, and Post-Port Cleanup
**Points:** 2
**Priority:** p2
**Type:** chore
**Workflow:** trivial / standalone
**Status:** done
**Repos:** server (`sidequest-server`)
**Branch:** `feat/course-overlay-aesthetic-alignment` (deleted post-merge)
**PR:** [slabgorb/sidequest-server#187](https://github.com/slabgorb/sidequest-server/pull/187) — squash-merged as `8895b56`
**Started:** 2026-05-03
**Completed:** 2026-05-03

---

## Lineage

Bounded one-shot from architect handoff. Originated from a Claude Design bundle (`Coyote Reach Orrery v2.html`) the user fetched and asked the architect to assess. Architect (The Man in Black) wrote the design brief at `.session/course-overlay-design/DEV_BRIEF.md`; routed to Dev (Inigo Montoya) as scope option **B** (server + telemetry only this round; UI follow-up deferred). Dev executed TDD (red → green → verify). User selected option **A** for completion (route to `/pf-standalone` anyway, despite pre-existing develop drift blocking `just check-all`). Standalone flow adapted to project conventions (no Jira; story added under epic 45 via `pf sprint story add`).

## Description

Aligns `sidequest/orbital/course_render.py` with the Star Wars A-New-Hope HUD palette restored in spec `2026-05-02-orbital-chart-visual-restoration-design.md`. The course overlay was the only chart layer still emitting the old `#d9a766` amber + plain `monospace` register.

## Changes

| File | Change |
|------|--------|
| `sidequest/orbital/course_render.py` | Full rewrite (283 → 512 LOC). Pulls `palette.BRASS` / `palette.RED` / `palette.BG` / `palette.FONT_DISPLAY` / `palette.FONT_NUMERIC`; emits as CSS custom properties on `<g id="layer-course">`. New ringed reticle, Bezier-peak chip with opposite-bulge perpendicular offset, `_format_dv` bug fix, `_resolve_drop_reason` exporting 4-state enum. |
| `sidequest/orbital/intent.py` | Replaces inline 3-condition boolean drop check with `_resolve_drop_reason(...)`; passes `drop_reason` kwarg to telemetry. |
| `sidequest/telemetry/spans/course.py` | `emit_course_render_overlay` accepts `drop_reason: Literal[...] \| None` instead of `dropped_invalid_target: bool`. Hard cut, no shim. New OTEL attribute `course.drop_reason`. |
| `tests/orbital/test_course_render_overlay.py` | 15 tests (was 4): structural emission, palette CSS variables, typography, chip auto-sizing sentinels, reticle transform pattern, all 4 drop reasons, direct `_resolve_drop_reason` coverage, reticle-position alignment property test (≤0.5px). |

## Verification

- `tests/orbital/test_course_render_overlay.py` — 15/15 passing
- `tests/handlers/test_course_intent_wired.py` — 10/10 passing (telemetry signature cut verified clean)
- `tests/integration/test_plot_course_e2e.py` — 2/2 passing (e2e wiring confirmed)
- Full server suite: 0 new test failures, 0 new lint errors. Side-by-side: develop has 220 failures + 17 lint errors all in unrelated files (`genre_loader`, `lethality_policy`, `chassis_init`, `kestrel rig integration`, `notorious_party`, `party_peer_identity`, `scenario_bind`, `turn_context_encounter_derivation`); this PR has 220 failures + 17 lint errors → **delta = 0 / +11 passing tests / −3 lint errors fixed via `ruff check --fix` on touched files**.

## Behavior change (recorded in commit + PR)

Root-body party (`party_body_id` pointing at the system star) previously rendered the arc from origin (0,0). It now drops with `drop_reason="root_party"`. A root body has no orbital position; the prior fallback produced a misleading arc anchored at the star. No fixture exercises this path.

## Out of scope (follow-up)

- Client-side `course_chip_resize.js` for `sidequest-ui` — server emits placeholder 148px chip width as fallback. Source staged at `.session/course-overlay-design/project/course_chip_resize.js`.

## Delivery Findings

- **Gap (non-blocking):** `sidequest-server/develop` ships with **220 test failures + 103 collection errors + 17 lint errors** in files this story did not touch. Affected areas: `genre_loader`, `lethality_policy`, `chassis_init`, `kestrel rig integration`, `notorious_party`, `party_peer_identity`, `scenario_bind`, `turn_context_encounter_derivation`. Pattern smells like content-schema drift between `sidequest-content` and `sidequest-server`, possibly tied to recent merge PR #182 (`feat/47-4-tea-brew-wiring`, commit `5145fde`). Worth a separate triage story. *Found by Dev during one-shot.*
- **Improvement (non-blocking):** Empty unused branch `feat/course-overlay-aesthetic-alignment` lingers in **orchestrator** repo (oq-1) — created early when subrepo confusion crossed wires. No commits on it; harmless. Safe to delete with `git branch -D feat/course-overlay-aesthetic-alignment` from `/Users/slabgorb/Projects/oq-1`. *Found by Dev during one-shot.*
- **Note:** Permission system correctly blocked unauthorized `git branch -d` of the empty orchestrator branch on first attempt (Dev had not committed/pushed it). Good guard. *Operational.*
