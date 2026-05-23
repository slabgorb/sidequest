---
parent: context-epic-22.md
workflow: tdd
---

# Story 22-3: Seed trope narrator injection — VALLEY-zone context for active seeds (ADR-009), Faded tag for expired ghosts

## Business Context

22-1 (schema + deck engine) and 22-2 (seed content for `tea_and_murder`) are merged.
The schema exists and the content exists, but nothing reads either of them at narration
time — `SeedDeck` and `SeedTrope` have **zero production consumers** today (verified in
the 22-1 archive's wiring audit).

22-3 closes that loop. Per ADR-009 (Attention-Aware Prompt Zones), the VALLEY zone is
the right home for *active* seed context: it's the "background information the narrator
weaves in retroactively" slot, not the high-attention Recency zone where guardrails
live. Expired seeds become **Faded** ghosts — record-only callbacks that let the
narrator reach back to "the matter of that sealed letter, weeks ago…" without
re-promoting them to active status. Without this story, seed content sits in YAML and a
schema sits in Python and the player still experiences the same opening every session.

This is also the story where the gaslighting doctrine (project memory
`project_narrator_gaslighting_doctrine`) applies: the narrator improvises freely unless
game state materializes the constraint. Seeds without VALLEY injection = a narrator
that ignores them. Seeds in VALLEY = a narrator that retroactively wires them to
whatever macro-trope is escalating.

## Technical Guardrails

**Anchor file — narrator prompt assembly:**
- `sidequest-server/sidequest/agents/orchestrator.py` — `build_narrator_prompt` is the
  call site that produces the three-zone (Primacy/Early, Valley, Late/Recency)
  cacheable layout. The Valley block currently builds from `zone_text.get(AttentionZone.Valley, "")`
  emitted by `registry.compose_split_by_zone(agent_name)` — i.e. *registry-driven*.
  Seed injection registers a new Valley contributor; it does **not** edit the assembly
  call site.

**Anchor file — schema (already shipped in 22-1):**
- `sidequest-server/sidequest/genre/models/tropes.py` — `SeedTrope`, `SeedState`, `SeedGhost`
- `sidequest-server/sidequest/game/seed_deck.py` — `SeedDeck` engine (draw without
  replacement, session-seeded)
- `sidequest-server/sidequest/game/session.py` — `GameSnapshot.active_seeds`,
  `GameSnapshot.seed_ghosts` (already persisted via `model_dump_json` round-trip)

**Patterns to follow:**
- **Registry-based zone contribution.** Other Valley contributors (genre confrontations,
  encounter context, magic context, narrator vocabulary) are registered into the prompt
  via the orchestrator's contributor pattern, not hard-coded in the assembly function.
  Mirror that. Look at how `narrator_vocabulary` or genre transition hints flow in for
  the closest precedents; do NOT pattern-match off the Recency-zone guardrails
  (ADR-111/112 deferred work — wrong zone).
- **Cache awareness.** The Valley block is `cache=False` (uncached, per turn). Seeds
  change between turns (active→ghost transitions on lifespan expiry), so Valley is
  correct. Do **not** put seed text into the cached stable block — it would invalidate
  block-0 byte stability (60-2/60-3 work).
- **Draw→record atomicity (carried over from 22-1's forward-looking note).** When this
  story introduces the production consumer that draws a seed, the draw and the
  `active_seeds.append(SeedState(...))` must land in the **same persisted turn**. If a
  draw isn't recorded before save, the derived `{active}∪{ghosts}` reconstruction will
  redeal it. The 22-1 architect recommended a `SeedDeck.from_snapshot(snapshot, seeds)`
  classmethod to centralize the derivation — 22-3 should add it if not already present.
- **Expiry transition.** `SeedState.is_expired()` / `to_ghost()` exist but have no
  caller. 22-3 wires them into the turn loop: each turn (or per-narration-turn), walk
  `snap.active_seeds`, move expired entries to `snap.seed_ghosts` via `to_ghost()`.
  Single seam, one place.

**Prose shape (VALLEY):**
- **Active seeds** — render as a short "Active threads" section with each seed's
  `name`, `description`, `flavor_tags`, and `narrative_hint`. The hint is the
  retroactive-connection guidance authored in 22-2; the narrator needs it visible.
- **Faded ghosts** — render as a short "Faded" or "Dormant threads" section with
  `name` + `description` only. No narrative_hint (the bait is gone; the memory remains
  for callbacks). Tag clearly as Faded so the narrator doesn't treat them as live.
- Keep it terse. VALLEY is shared with confrontations, vocab, magic context — budget
  is real. Aim for 3–6 active seeds × ~2 lines each, plus a short ghost list. If the
  block grows large, prefer summarization over truncation.

**What NOT to touch:**
- Cached stable block (Primacy/Early). Seeds belong in Valley only.
- Recency/guardrail prose (ADR-111/112 deferred). Different zone, different concern.
- Seed content YAML (that was 22-2; do not edit `seed_tropes.yaml`).
- The `SeedTrope`/`SeedState`/`SeedGhost` schema (that was 22-1; no field changes here).
- OTEL spans for seeds (that's 22-4; this story should land *with* its OTEL hooks per
  the OTEL Observability Principle, but the GM-panel surface is 22-4's job).

**Genre pack load path:**
- Seeds were authored to `sidequest-content/genre_packs/tea_and_murder/seed_tropes.yaml`
  (22-2). Verify the genre loader actually parses this file into the in-memory genre
  pack. If 22-2 stopped at "file authored, validates via pydantic" without loader
  wiring, 22-3 wires the loader too — that's still in-scope (it's a seed-engine wiring
  story, and unloaded YAML is the literal "exists but not wired" failure mode CLAUDE.md
  warns against). Check `sidequest/genre/` loader code first.

## Scope Boundaries

**In scope:**
- Genre loader reads `seed_tropes.yaml` into the in-memory genre pack (if not already
  wired in 22-2 — verify first; do not duplicate).
- Production consumer constructs a `SeedDeck` per session (seeded by `session_id` for
  reproducibility, per 22-1 spec), draws an opening hand into `snap.active_seeds`, and
  persists atomically.
- Turn-loop seam advances seed state: expired actives → ghosts.
- VALLEY-zone registry contributor renders active seeds (full detail) and ghosts
  (Faded, name+description only).
- One integration/wiring test proves the seed text appears in the assembled narrator
  prompt's Valley block when a session has active seeds (per the every-test-suite-needs-
  a-wiring-test rule in CLAUDE.md — and use OTEL or fixture-driven behavior, **not**
  source-text grep, per the server CLAUDE.md "No Source-Text Wiring Tests" rule).
- Minimal OTEL on the subsystem decisions (seed drawn, seed expired→ghost, valley
  injection fired) — enough to make 22-4's GM-panel work straightforward. Full
  dashboard surfacing is 22-4.

**Out of scope:**
- GM panel / dashboard visibility (22-4).
- Seed resolution mechanics (taking the bait — future epic).
- Other-pack seed authoring (only `tea_and_murder` is in the content layer).
- Schema changes to `SeedTrope` / `SeedState` / `SeedGhost`.
- Recency-zone guardrail prose changes (ADR-111/112).
- Multiplayer per-player seed visibility — seeds are shared world context for now.

## AC Context

The story YAML ships with `acceptance_criteria: []`. Derived ACs, expanded for
testability:

1. **Genre pack loads seeds.** Loading the `tea_and_murder` pack populates a
   parsed `seed_tropes: list[SeedTrope]` accessor on the in-memory genre pack. Test
   verifies count > 0 and that one known seed (e.g., `sealed-letter`) round-trips with
   all required fields.

2. **Production consumer draws on session start.** When a new (or resumed-with-empty-
   `active_seeds`) session begins, the seed-draw seam produces a deterministic hand
   for `(session_id, seed_count)` and writes it into `snap.active_seeds` in the same
   persisted turn as the draw. Test reseeds with the same session_id, asserts the same
   draw. Test reloads from snapshot and asserts no redraw (atomicity).

3. **Expiry transitions active→ghost.** When `SeedState.is_expired(current_turn)` is
   true, the turn-loop seam moves the entry out of `snap.active_seeds` and appends a
   `SeedGhost` to `snap.seed_ghosts`. Test advances turn count past `lifespan_turns`
   and asserts the migration. Verifies ghost retains `id`, `name`, `description`, and
   creation/expiry turn metadata.

4. **VALLEY injection — actives rendered with full guidance.** With a snapshot
   containing N active seeds, the assembled Valley block contains each seed's name,
   description, flavor_tags, and narrative_hint. Test drives `build_narrator_prompt`
   with a fixture snapshot and asserts the rendered Valley text contains the expected
   substrings via a behavior assertion (fire the real builder; do not regex production
   source). Bonus: assert the seed contributor is registered in the orchestrator's
   contributor list (reflection-based, not source-grep).

5. **VALLEY injection — ghosts rendered as Faded.** With ghosts in the snapshot, the
   Valley block contains a Faded section with name + description for each, and does
   NOT include their narrative_hint. Test asserts both inclusion of name and exclusion
   of hint.

6. **Cache stability preserved.** The stable (cached) block stays byte-identical
   across turns when only seed state changes. Test exercises a two-turn run with
   different `active_seeds` per turn and asserts block-0 text is byte-equal. This
   guards the 60-2/60-3 cache invariant.

7. **OTEL on subsystem decisions.** Spans fire for: seed drawn (with id), seed
   expired→ghost (with id and turn), and valley injection rendered (with active count
   and ghost count). Test drives a turn that triggers each and asserts the span
   payload. Surfacing in the GM panel is 22-4.

## Assumptions

- **Genre loader is the right seam for seed YAML parsing.** Loader-driven model
  population is the established pattern for trope content; seeds parallel that. If
  during implementation the loader path turns out to skip this file (e.g., loader
  reads a fixed allowlist of YAML files), log a Design Deviation — 22-2's authoring
  acceptance criterion ("File created at … `seed_tropes.yaml`") implicitly assumes the
  loader picks it up.
- **`session_id` is stable enough to seed the deck reproducibly.** 22-1 spec'd this.
  If session_id changes mid-session (it shouldn't), reproducibility breaks.
- **Per-turn vs per-narration-turn for expiry.** 22-1 left this seam unspecified. The
  story should commit to one — recommend **per narration turn** (the natural beat where
  lifespan counts), since `lifespan_turns` lives in the schema as an integer turn count.
  Architect to confirm during RED-phase spec-check if ambiguous.
- **Opening hand size is per-pack config or a small constant.** 22-1 didn't specify;
  default to a small constant (e.g., 3) and revisit if the playtest shows it's wrong.
  No new schema field unless absolutely necessary — keep this story scoped.

If any of these prove wrong during RED/GREEN, log Design Deviations and notify SM.

## References

- ADR-009: Attention-Aware Prompt Zones (VALLEY zone definition)
- ADR-018: Trope Engine (the macro-trope sibling system)
- ADR-023: Session Persistence (snapshot_json round-trip — no migration)
- ADR-101 / 102: Anthropic SDK narrator + tool-use protocol (the prompt assembly path
  this story plugs into)
- `sprint/context/context-epic-22.md` (epic-level architecture and component diagram)
- `sprint/context/context-story-22-1.md` (schema + deck engine — predecessor)
- `sprint/context/context-story-22-2.md` (seed content authoring — predecessor)
- `sprint/archive/22-1-session.md` (forward-looking wiring notes: `from_snapshot`
  classmethod recommendation, draw→record atomicity)
- Project memory: `project_narrator_gaslighting_doctrine.md` (materialize state to
  constrain narrator improvisation)
- Server CLAUDE.md: "No Source-Text Wiring Tests" (use OTEL or fixture-driven behavior
  for the wiring test, never regex prod source)
