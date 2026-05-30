---
parent: context-epic-72.md
workflow: tdd
---

# Story 72-4: Route narrator-invented NPC names through ADR-091 namegen

## Business Context

When the narrator invents an NPC mid-scene, it hands back a **bare name string** of
its own choosing and the engine mints an `NpcPoolMember(drawn_from="narrator_invented")`
with that raw string verbatim (`sidequest/server/narration_apply.py:1292-1301`). That
string never passes through ADR-091's culture-bound generator, so an invented name is
only as genre-true as Claude's improvisation happened to be that turn — it carries none
of the per-culture phonemic distribution that the corpus+Markov pipeline exists to
guarantee. A `space_opera`/`perseus_cloud` table that has carefully authored `spacer` /
`thari` / `yulan` cultures can still get a narrator-minted "Bob Hegemonic" that breaks
the table's sense of place.

This is the exact failure ADR-091 was written to prevent ("LLM-generated names —
rejected (still): inconsistent across sessions, expensive per call, contradicts itself
without a registry"). The naming infrastructure is **already built and shipping in every
genre pack** — `build_from_culture` / `NameGenerator.generate_person`
(`sidequest/genre/names/generator.py`), the `generate_name` tool
(`sidequest/agents/tools/generate_name.py`), per-culture corpora, stem-collision and
corpus-health OTEL guards. What is missing is the **wire** between the narrator-invented
mint site and that generator. This story closes that gap so invented NPCs are
phonetically genre/culture-true by construction, not by luck.

This serves the playgroup directly: Keith-as-player (the career GM the narrator must fool)
notices when a fantasy/sci-fi world suddenly produces a name that "sounds wrong," and
Jade — who **authors** cultures — needs her `cultures.yaml` corpus work to actually govern
the names that appear at the table, including narrator-invented ones, not just
tool-requested ones. The new provenance span also lets the GM panel (Keith/dev) verify
the route fired instead of the engine silently accepting a raw string.

## Technical Guardrails

**This story is WIRING existing infrastructure, not writing a name generator.** Per the
"Don't Reinvent — Wire Up What Exists" principle. The generator, the culture model, the
corpus loading, the Markov chain, the stem-collision filter, and the three corpus-health
OTEL guards already exist and are exercised by the `generate_name` tool and two CLIs
(`namegen`, `encountergen`). Do **not** reimplement any of that. Reuse these real seams:

- **`build_from_culture(culture, corpus_dir, rng=..., fallback_dirs=...)`** —
  `sidequest/genre/names/generator.py:266`. Materializes a `NameGenerator` from one
  `Culture` model + the genre pack's `corpus/` dir. Already applies corpus-health guards
  (`namegen.fail_loud` / `namegen.thin_corpus`).
- **`NameGenerator.generate_person()`** — `generator.py:103`. Returns a culture-true
  person name assembled from `person_patterns`. Title-casing and slot blending are
  already handled.
- **`has_stem_collision(name)`** — `generator.py:152`. The "Frandrew Andrew" reject
  predicate; already emits `namegen.stem_collision`. Re-roll on collision rather than
  emitting a bad name.
- **`Pack.effective_cultures(world)`** — `sidequest/genre/models/pack.py:231`. The
  **authoritative** culture-resolution helper: returns `(cultures, source)` where
  `source ∈ {"world","genre"}`. The epic-source bug (perseus_cloud session 894,
  2026-05-29) was a seeder reading `pack.cultures` raw while namegen resolved via the
  world — diverging culture sets, 0 NPCs seeded. **Resolve culture through
  `effective_cultures`, not raw `pack.cultures`,** so this story does not reintroduce
  that divergence.

**The mint seam.** `_apply_npc_mentions`
(`sidequest/server/narration_apply.py:1171`) — note this file lives in `server/`, not
`game/` as the epic shorthand implies. The Step-3 "novel" branch at **lines
1292-1301** is where `NpcPoolMember(drawn_from="narrator_invented")` is appended with
`name=mention.name` (the raw narrator string). This is the single site to reroute.
The function today takes only `snapshot`, `mentions`, `turn_num`,
`acting_character_name` — **it has no genre-pack / culture context**, so part of this
story is threading the resolved culture (or the built `NameGenerator`, or the pack +
world) into `_apply_npc_mentions` from its caller
(`_apply_narration_result_to_snapshot`, call site at `narration_apply.py:2477`). Prefer
threading the already-resolved generator/culture in rather than reaching for a global.

**`ToolContext.name_generators` is NOT the seam here.** The `generate_name` tool's
"Phase E" production wire (`tool_registry.py:131`, building the per-culture dict at
session-load) **never landed** — `build_from_culture` has zero production callers today
(only the two CLIs call it). Do not assume that dict is populated. This story may
legitimately build the `NameGenerator` at the mint seam (or at session-load and thread
it through); if it builds at session-load, that same construction can later back-fill the
tool dict, but wiring the tool dict is out of scope for 72-4.

**OTEL (server rule: behavioral/span assertions, never source-text greps).** Per the
epic's "72-4: namegen-routed mint span (culture id + generated name vs narrator's bare
name)." Emit a span at the rerouted mint recording at minimum: resolved `culture`
name + culture `source` (`world`/`genre`), the narrator's original bare name, the
generated name actually minted, and a boolean for whether a re-roll fired on stem
collision. NPC spans live in `sidequest/telemetry/spans/npc.py`; the namegen-internal
guards (`namegen.fail_loud` / `thin_corpus` / `stem_collision`) already fire from inside
`build_from_culture` / `has_stem_collision` and must keep firing. Existing mint-branch
spans (`npc.referenced` with `match_strategy="invented"`, `npc.auto_registered`) must
continue to fire unchanged.

**No Silent Fallbacks.** If culture cannot be resolved for the active world (no
cultures bound, or the generator cannot produce a name), the engine must fail **loud** —
emit a warning-severity span and surface the condition, not silently fall back to the
raw narrator string with no signal. (A *deliberate, span-recorded* degrade is acceptable;
a silent swallow is not. The TEA/Dev should pin down which in the AC discussion — the
loudness, not the specific recovery, is the invariant.)

## Scope Boundaries

**In scope:**
- Rerouting the narrator-invented (Step-3 "novel") mint branch at
  `narration_apply.py:1292-1301` through the ADR-091 culture-bound generator.
- Resolving the active culture via `Pack.effective_cultures(world)` and threading that
  context into `_apply_npc_mentions`.
- A provenance OTEL span at the rerouted mint (culture id/source, bare name vs generated
  name, collision-reroll flag).
- Loud failure when culture is unresolved or generation fails.

**Out of scope (other stories — do not touch):**
- OCEAN personality + scenario `belief_state` seeding for invented NPCs — **72-9**.
- Born-hostile `disposition=-20` default fix / neutral spawn — **72-5**
  (`_npc_from_patch` ~line 1533).
- Disposition preservation on promotion + load-time reconcile — **72-2**.
- Identity-drift authoritative overwrite (warn-only → applied) — **72-7**.
- `npc_pool` LRU cap / stale-`observation_pending` prune — **72-6**.
- Wiring the `generate_name` tool's `ToolContext.name_generators` dict (Phase E) — not
  required by this story; only the mint-seam route is.
- The `_auto_mint_prose_only_npcs` / `observation_pending` gate paths (72-10) — this
  story touches the **Step-3 explicit-mention** novel branch only.

## AC Context

No explicit ACs exist on the story. Derive ~4-5 testable ACs (behavioral / span
assertions per server rule — never source-text greps). Suggested coverage:

1. **Generated, not raw.** Given a world with a bound culture and a narrator mention of
   a name absent from both `npcs` and `npc_pool`, the minted `NpcPoolMember.name` is a
   value produced by the culture-bound generator, **not** the narrator's bare
   `mention.name`. (Drive the real `_apply_npc_mentions` with a synthetic genre pack +
   snapshot fixture; assert on the minted pool member.)

2. **Culture resolved from world/scene context.** Culture is resolved via
   `Pack.effective_cultures(world)`; a world that supplies its own culture list uses
   `source="world"`, otherwise `source="genre"`. Assert the resolved culture/source the
   route used (via the provenance span) matches the world binding — covering the
   perseus_cloud divergence regression.

3. **Provenance span fired.** The rerouted mint emits an OTEL span recording resolved
   culture name + source, the narrator's original bare name, and the generated name.
   Assert the span fired with those attributes (drive flow → assert span).

4. **Loud on unresolved culture.** When no culture is bound for the active world (or the
   generator cannot produce a name), the path fails loud — a warning-severity span fires
   and the condition is surfaced rather than silently minting the raw string. Assert the
   loud signal.

5. **Player-named / pre-existing names respected (edge cases).** A name that already
   matches `snapshot.npcs` (Step 1) or `snapshot.npc_pool` (Step 2) is **not** rerouted
   or overwritten — only the Step-3 novel branch generates. (Per ADR-091, intentional
   in-culture stem reuse is not a collision; the generator's own re-roll handles the
   cross-token "Frandrew Andrew" artifact and a name-collision against an existing store
   member must resolve to the existing member, never a fresh mint.)

Edge cases the ACs/tests should pin: (a) **culture not bound** → loud, not silent;
(b) **player-named NPC** already in a store → respected, not regenerated; (c) **name
collision** — generated name equals an existing pool/npc name → resolve to the existing
member or re-roll, never create a duplicate identity.

## Assumptions

- The narrator-invented reroute targets the **Step-3 novel branch only**
  (`narration_apply.py:1292-1301`); Steps 1 (`npcs` hit) and 2 (`npc_pool` hit) keep
  their existing additive/match behavior — generation never overwrites an
  already-known name. (Validate with TEA; this preserves the "player-named NPC
  respected" edge case.)
- "Culture resolved from world/scene context" means
  `Pack.effective_cultures(<active world>)`, not raw `pack.cultures` — chosen to avoid
  re-introducing the session-894 divergence bug. If a world binds multiple cultures, the
  selection rule among them (single primary, NPC-role-keyed, or seeded-random) is a small
  design choice for the TEA/Dev to settle; the wiring and provenance span are the
  load-bearing parts.
- The generator may be built at the mint seam (per-call `build_from_culture`) or at
  session-load and threaded through. Construction cost is non-trivial (corpus read +
  Markov train), so session-load construction with caching is preferable, but either is
  acceptable so long as the corpus-health guards still fire and the route is reachable
  from the production narration path.
- The corpus directory for the active genre pack is discoverable at the mint seam (the
  CLIs already resolve a `corpus_dir` + `fallback_dirs` for `build_from_culture`); this
  story reuses that same resolution rather than inventing a new path scheme.
- Per the server "Every Test Suite Needs a Wiring Test" rule, at least one test must
  drive the **real** `_apply_narration_result_to_snapshot` → `_apply_npc_mentions`
  production path (not a direct unit call to the generator) and assert the provenance
  span fired — proving the route is wired end-to-end, not merely callable.
