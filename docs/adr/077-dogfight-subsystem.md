# ADR-077: Dogfight Subsystem via StructuredEncounter Extension

**Status:** Proposed
**Date:** 2026-04-11
**Epic:** TBD (post-Sprint-2)
**Deciders:** Keith
**Relates to:**
- ADR-033 (StructuredEncounter / Confrontation Engine) — parent decision
- ADR-067 (Unified Narrator Agent) — narration contract
- Epic 13 (Sealed-letter multiplayer turns) — shared commit infrastructure
- ADR-074 (Dice Resolution Protocol, proposed) — adjacent resolution mechanism

## Context

### The gap

Space opera already ships a capital-ship encounter (`ship_combat` in
`sidequest-content/genre_packs/space_opera/rules.yaml:163`) that models
multi-station crew combat via a single shared `engagement_range` metric and
narrator-selected beats (broadside, evasive maneuver, close range, target
systems, disengage). That subsystem works for Star Destroyer vs. frigate
drama, where the fiction is about crew roles and collective decisions.

It does **not** model **fighter-class single-seat dogfighting**, where the
fiction is about two pilots each making a hidden maneuver commit per turn and
having the resolution emerge from the cross-product of their choices. X-wing
vs. TIE, Millennium Falcon vs. pursuit fighter, Rocinante corvette vs. stealth
interceptor — these encounters have a fundamentally different decision shape:

| Axis | `ship_combat` (existing) | Dogfight (proposed) |
|---|---|---|
| Scale | Capital ship vs. capital ship | Fighter vs. fighter (1–2 pilots) |
| Decision authority | Crew collective, narrator-selected beat | Each pilot, secret commit |
| Turn resolution | Single beat applied to shared metric | Cross-product lookup of both commits |
| State shape | One metric + shared secondary stats | Per-pilot descriptor (bearing, energy, gun solution) |
| Information | Full public | Sealed-letter then revealed |
| Commitment atom | Narrator beat choice | Player maneuver choice |

The content design for the dogfight subsystem has been authored and paper-
validated by the GM agent in `sidequest-content/genre_packs/space_opera/dogfight/`:

- `descriptor_schema.yaml` — per-pilot scene descriptor (8 MVP fields + 4 future)
- `maneuvers_mvp.yaml` — 4-maneuver MVP menu (straight, bank, loop, kill_rotation)
- `interactions_mvp.yaml` — 16-cell `(red_maneuver, blue_maneuver)` lookup table
- `pilot_skills.yaml` — 4 tier forward-capture (Rookie → Ace) aligned to existing affinity thresholds
- `playtest/duel_01.md` — paper playtest scaffold with commit/reveal/narrate protocol

The paper playtest produced a three-exchange arc with principled per-pilot
commitments and emergent narrative outcomes. The mechanic is validated at the
content abstraction layer. This ADR governs how that content is wired into
the Rust engine, the narrator, and the multiplayer session.

### The architectural question

**Is the dogfight a new engine subsystem, a specialization of
`StructuredEncounter`, or pure content on top of the narrator?**

ADR-033's Epic 28 revision is explicit: `CombatState` and `ChaseState` were
*deleted* and replaced by a unified `StructuredEncounter` whose confrontation
types are YAML-declared in each genre pack. The stated principle is that
every structured encounter in SideQuest flows through that one type. A net-
new "dogfight engine" as a peer would violate that unification by reintroducing
exactly the kind of special-case Rust code ADR-033 removed. That is an
architectural regression we must either justify with extraordinary evidence
or refuse.

Pure-content-only (narrator resolves everything from prose) fails the SOUL
test. The narrator is a language model; it cannot be trusted to compose 3D
rotations across turns without hallucinating geometry. The MVP playtest
*exists* to prove the mechanical backbone before narrator rendering is
attached. Content-only would mean the narrator improvises the geometry, which
is exactly the SOUL violation the lookup table was designed to prevent.

Both alternatives fail on principle. That leaves **specialization of
StructuredEncounter** as the only candidate worth designing — but only if
the existing type can be *extended* rather than warped.

## Decision

**Extend `StructuredEncounter` with two additive affordances and declare
`dogfight` as a new confrontation type in the space_opera genre pack's
`rules.yaml`. No parallel subsystem. No new specialist agent. No changes to
existing confrontation types.**

The extensions are both *additive*, meaning every existing confrontation
(`ship_combat`, `combat`, `chase`, `negotiation`) is untouched and any genre
pack that does not declare a dogfight confrontation sees no behavioral change.

### Extension 1 — `resolution_mode` on `ConfrontationDef`

Add an optional `resolution_mode` field with two variants:

```rust
pub enum ResolutionMode {
    /// Existing behavior. Narrator selects a beat per turn and the engine
    /// applies it to the shared metric. All existing confrontations use this.
    BeatSelection,

    /// Each actor commits a choice from `commit_options` privately via the
    /// session's TurnBarrier. When all commits are in, the engine looks up
    /// the cross-product in `interaction_table` and applies per-actor deltas.
    SealedLetterLookup,
}
```

Default is `BeatSelection`. Existing confrontation YAML does not need to
change.

### Extension 2 — `commit_options` and `interaction_table` on `ConfrontationDef`

Both optional, consumed only when `resolution_mode: SealedLetterLookup`:

```rust
pub struct ConfrontationDef {
    // ... existing fields ...
    pub resolution_mode: ResolutionMode,
    pub commit_options: Option<Vec<String>>,     // legal maneuver ids
    pub interaction_table: Option<InteractionTable>,
}

pub struct InteractionTable {
    /// Cells keyed by (actor_a_commit, actor_b_commit). Symmetric 2-actor only in MVP.
    pub cells: HashMap<(String, String), InteractionCell>,
}

pub struct InteractionCell {
    pub name: String,
    pub shape: String,                           // narrative classification
    pub actor_a_delta: PerActorDelta,
    pub actor_b_delta: PerActorDelta,
    pub narration_hint: String,
}

pub struct PerActorDelta {
    /// Fields to set on the actor's per_actor_state (typed string → Value).
    pub set_fields: HashMap<String, serde_json::Value>,
    /// Shared-metric delta, if this confrontation also has a metric.
    pub metric_delta: Option<i32>,
    /// Secondary stats delta (per-actor, not shared).
    pub secondary_delta: Option<HashMap<String, f64>>,
}
```

### Extension 3 — `per_actor_state` on `EncounterActor`

Each actor already carries actor-specific fields. Add one more:

```rust
pub struct EncounterActor {
    // ... existing fields ...
    /// Per-actor structured state — used by SealedLetterLookup to store
    /// each pilot's scene descriptor between turns. Keyed field values
    /// must validate against the confrontation's content schema
    /// (e.g., dogfight/descriptor_schema.yaml).
    pub per_actor_state: HashMap<String, serde_json::Value>,
}
```

This is the load-bearing piece. It lets per-pilot descriptors (bearing, range,
aspect, energy, gun_solution) live on the actor where they belong. The
narrator reads each actor's `per_actor_state` to render that pilot's cockpit
view, and the engine writes it via the interaction table.

### Extension 4 — New engine handler

A new resolution handler in the confrontation engine dispatches on
`ResolutionMode`:

```rust
match confrontation.def.resolution_mode {
    ResolutionMode::BeatSelection => {
        // existing: narrator outputs a beat, engine applies it
        apply_beat(&mut confrontation, narrator_beat_id)
    }
    ResolutionMode::SealedLetterLookup => {
        // new: gather actor commits via TurnBarrier, lookup, apply deltas
        let commits = session.turn_barrier
            .as_ref()
            .expect("sealed-letter confrontation requires barrier-enabled session")
            .drain_actor_commits();
        let cell = confrontation.def
            .interaction_table.as_ref().unwrap()
            .cells
            .get(&(commits.actor_a, commits.actor_b))
            .expect("interaction table must cover all commit pairs");
        apply_per_actor_delta(&mut confrontation.actors[0], &cell.actor_a_delta);
        apply_per_actor_delta(&mut confrontation.actors[1], &cell.actor_b_delta);
        record_narration_hint(&cell.narration_hint);
    }
}
```

The `TurnBarrier` used here is the **same infrastructure Sprint 2 Epic 13
already built** for sealed-letter multiplayer turns (`sidequest_game::barrier::TurnBarrier`,
attached at `SharedSession.turn_barrier`). The barrier's existing contract —
"hold actions until all expected players commit, then release atomically" —
is exactly the contract the dogfight subsystem needs. **Zero new infrastructure
for commit-and-reveal.**

### Content plumbing

Space opera's `rules.yaml` gains a new confrontation entry that references
the GM-authored content files:

```yaml
confrontations:
  # ... existing entries (negotiation, ship_combat, combat, chase) ...

  - type: dogfight
    label: "Dogfight"
    category: fighter_combat
    resolution_mode: sealed_letter_lookup
    metric:
      name: engagement_control
      direction: bidirectional
      starting: 0
      threshold_high: 100
      threshold_low: -100
    commit_options_from: dogfight/maneuvers_mvp.yaml
    interaction_table_from: dogfight/interactions_mvp.yaml
    descriptor_schema_from: dogfight/descriptor_schema.yaml
    pilot_skill_tiers_from: dogfight/pilot_skills.yaml
    secondary_stats:
      - name: energy
        source_stat: Reflex
        spendable: true
        per_actor: true
      - name: hull
        source_stat: Physique
        spendable: false
        per_actor: true
    mood: dogfight
    narrator_hints:
      - "Two pilots, two cockpits, one decision each turn."
      - "Never narrate geometry not present in the actor's descriptor."
```

The `_from:` fields are a new loader pattern: the confrontation def loads
MVP tables from adjacent YAML files rather than inlining them, so the content
stays authorable by the GM agent without touching `rules.yaml`. The loader
merges them into a single `ConfrontationDef` at genre pack parse time.

### Narrator integration (ADR-067 compliance)

The unified narrator (ADR-067) handles all turn narration. For dogfight turns,
the engine passes to the narrator:

1. Each actor's updated `per_actor_state` (the resolved scene descriptor)
2. The cell's `narration_hint` as a beat the narrator should hit
3. Explicit instructions that the narrator MUST NOT invent geometry outside
   the descriptor fields — if a bearing isn't set, the narrator can't reference
   one

The narrator emits **two narration blocks per turn** — one per pilot, in each
pilot's private view. The existing per-player perception filter infrastructure
(`SharedSession.perception_filters`) is the correct hook for this — it already
solves "rewrite narration per-player based on what each player perceives."
Dogfight narration is a natural extension: each pilot's descriptor is their
perceptual filter.

**No new specialist agent.** The narrator receives the per-actor state and
narration hint; system prompt extensions (added to the existing narrator prompt
template) teach it to render cockpit POV. ADR-067 collapsed specialist agents
into the unified narrator and this ADR does not reverse that.

### OTEL observability (required per CLAUDE.md)

Every new subsystem touch-point MUST emit OTEL spans so the GM panel can
verify the engine is engaged and the narrator isn't improvising. Minimum
required spans:

| Span | Emitted when | Attributes |
|---|---|---|
| `dogfight.confrontation_started` | New dogfight StructuredEncounter created | starting_state id, actors, skill tiers |
| `dogfight.maneuver_committed` | Each actor commit arrives at the barrier | actor_id, maneuver_id, turn |
| `dogfight.cell_resolved` | Interaction table lookup completes | cell_name, shape, actor_a_delta summary, actor_b_delta summary |
| `dogfight.gun_solution_fired` | An actor with `gun_solution: true` fires | actor_id, target_id, damage_modifier, hit_severity |
| `dogfight.energy_depleted` | An actor's energy pool drops below a threshold | actor_id, energy_value |
| `dogfight.skill_tier_resolved` | Pilot tier determined at confrontation start | actor_id, tier, available_maneuvers |
| `dogfight.ace_instinct_used` | Tier-3 ace uses the once-per-duel peek | actor_id, opponent_commit_peeked |

Without these, the GM panel cannot distinguish "the engine resolved a cell"
from "the narrator made something up." CLAUDE.md explicitly forbids shipping
a subsystem that can't be observed; this table is non-negotiable.

## Consequences

### Positive

- **Reuses StructuredEncounter** — preserves the ADR-033 unification, no god-object regression, no parallel encounter types
- **Reuses TurnBarrier** — Sprint 2 Epic 13's sealed-letter infrastructure is the generic primitive; the dogfight just declares itself a barrier consumer
- **Reuses the unified narrator** — ADR-067 stays intact, no new specialist agent, cockpit rendering is a prompt extension
- **Content-authorable in YAML** — GM agent can keep editing maneuvers, interaction cells, descriptors, and skill tiers without Rust changes
- **Skinnable across genres** — once `SealedLetterLookup` and `per_actor_state` exist on StructuredEncounter, they're available to any genre that declares a dogfight-shaped confrontation (low_fantasy dragon duel, victoria airship combat, neon_dystopia mech duel)
- **UI reuses EncounterOverlay** — the per-actor descriptor fields drive a new cockpit panel component, but the overlay shell is the one ADR-033 already ships
- **OTEL observable from day one** — the GM panel sees every resolved cell and can verify the engine is engaged
- **Paper-validated** — the MVP mechanic has been playtested on paper before any code is written

### Negative

- **ConfrontationDef schema grows** — `resolution_mode`, `commit_options`, `interaction_table`, `_from:` loader fields. Mitigated: all additive, all optional, existing packs unaffected.
- **`per_actor_state` is a typed-Value escape hatch** — `HashMap<String, serde_json::Value>` is less type-safe than a named struct. Mitigated: each confrontation type's descriptor_schema YAML is the validation contract; the engine validates on write. A future refinement can introduce a typed wrapper per confrontation kind.
- **Two-actor assumption in MVP** — the 16-cell interaction table is symmetric 2-actor. Three-player dogfights would require a 3D lookup (8^3 = 512 cells) which is impractical to hand-author. Mitigated: start with 1v1, add wingman mechanics only after the core proves out. Explicit scope boundary.
- **Narrator must be taught cockpit POV** — prompt engineering work to add "render from descriptor, never invent geometry" to the narrator system prompt. Mitigated: the GM-authored narration hints are explicit beats the narrator follows, and SOUL enforcement catches drift via OTEL span comparison.

### Risks

- **Interaction table is design-sensitive.** The 16-cell MVP table encodes rock-paper-scissors balance; if the math is wrong, the game is either solved (one maneuver dominates) or incoherent (no maneuver helps). **Mitigation:** the `duel_01.md` playtest scaffold is the calibration gate. Run it, tag each cell with `calibrated | exciting | lopsided | confusing | dull`, and only expand to 8 maneuvers after the 4-maneuver table scores clean.

- **TurnBarrier may be session-granular, not confrontation-granular.** Epic 13 built the barrier for session-wide turn boundaries. A dogfight confrontation that wants to run internal commit-reveal cycles inside a single narrative turn needs verification that the barrier can be engaged/disengaged per-confrontation without breaking multiplayer turn accounting. **Open question — needs Dev investigation before implementation (see Open Questions below).**

- **"Extend and return" between exchanges is not yet modeled.** The MVP table only authors the `merge` starting state. Real multi-exchange duels need either (a) auto-reset to merge between exchanges with energy carried over, or (b) additional starting states (tail_chase, beam, overhead) each with their own 16-cell table. **Mitigation:** start with (a) as a simple engine rule ("after a no-hit turn with `closure: opening_fast`, both actors reset to merge with current energy"), and only author additional starting states after the MVP graduates.

- **Damage model is unauthored.** The MVP playtest used ad-hoc house rules (graze/clean/devastating, 2 grazes = kill). The interaction cells have no hit-severity column. **Mitigation:** add a `hit_severity` field to the `PerActorDelta` schema before first implementation. Defer detailed damage tables to a second content pass.

- **Mutual gunline cells may be over-lethal.** At 60 starting energy and the current mutual-kill cell count (3 of 16), any three-exchange duel that reaches turn 3 with one pilot wounded tends to resolve via trade-kill. May devalue skill. **Mitigation:** watch calibration tags across multiple playtest runs before expanding to 8 maneuvers. The fix is a cell-level delta adjustment, not an architectural change.

## Alternatives Considered

### A — New parallel `DogfightEngine` subsystem

Rejected. Would reintroduce exactly the kind of parallel encounter type ADR-033
deleted in Epic 28. Violates the single-source-of-truth principle for
structured encounters. The only argument for it is that `SealedLetterLookup`
resolution is "different" from `BeatSelection` — but that difference is a
resolution mode, not a fundamental type distinction. A match expression in one
handler is vastly cheaper than a duplicated encounter type.

### B — Merge dogfight into existing `ship_combat` confrontation

Rejected. `ship_combat` models capital-ship crew combat (broadside, evasive
maneuver, target systems — each a collective decision). The decision shape is
fundamentally different. Forcing both into one type would produce a
confrontation with mode-dependent semantics — the worst of both worlds.
`ship_combat` stays a `BeatSelection` confrontation; `dogfight` is a new
`SealedLetterLookup` confrontation. They are siblings under StructuredEncounter,
not the same thing.

### C — Pure content layer, narrator resolves geometry from prose

Rejected on SOUL grounds. The entire point of the lookup table is that LLMs
cannot reliably compose 3D rotations across turns. If the narrator resolves
geometry, every turn drifts the fiction a few degrees from mechanical truth
until by turn 5 the two ships are in a position that doesn't follow from any
maneuver either pilot chose. This is the exact improvisation failure mode
SOUL principle #12 (The Test) forbids. Paper playtest confirmed the table
works; the job of code is to preserve that guarantee at run time.

### D — Introduce a dedicated "Pilot" class and use four-track progression
directly, skipping the skill_tiers capture

Rejected as a non-solution. Skill tiers describe what the dogfight engine
does *given* a pilot, not how pilots advance overall. Progression affinities
(Command/Grit/Savvy/Craft/Kinship/Horizon) are the RPG advancement track; the
skill tiers are a per-confrontation projection of those affinities into
"which maneuvers are unlocked and how hard do hits land." They must both
exist. The skill tiers file is not a replacement for progression, it's a
confrontation-local lookup from affinity score to dogfight affordance.

### E — Spawn a specialist `dogfight_narrator` agent (reverses ADR-067)

Rejected. ADR-067 collapsed specialist agents into the unified narrator
explicitly to reduce latency and preserve persistent session context. The
dogfight subsystem has no latency or context argument for a dedicated agent;
cockpit-POV rendering is a system-prompt extension to the narrator, not a
new agent. Anything else violates ADR-067 and must be re-justified.

## Open Questions (for Dev during implementation)

1. **TurnBarrier granularity.** Can `TurnBarrier` be engaged at confrontation
   scope rather than session scope, so a dogfight can run internal commit
   cycles without breaking broader session-level turn accounting? If yes,
   proceed as designed. If no, propose either (a) extending the barrier
   with a scope parameter or (b) adding a per-confrontation barrier-like
   primitive.

2. **`_from:` loader pattern.** Does the genre pack loader already support
   sourcing sub-files into a single struct (e.g., `commit_options_from:
   dogfight/maneuvers_mvp.yaml`)? If not, add this loader capability as a
   prerequisite story. It is a one-time addition that benefits any future
   confrontation with large tables.

3. **`per_actor_state` validation.** Should the engine validate writes
   against `descriptor_schema.yaml` at runtime, or trust the content author?
   Recommendation: validate at genre pack load time (pre-check that all cell
   deltas only set fields present in the schema), skip runtime validation
   for throughput. This matches how the existing ConfrontationDef loader
   handles beat validation.

4. **Damage model.** The MVP has no hit-severity column. Before implementation,
   the content team (GM agent) must extend `interactions_mvp.yaml` cells with
   a `hit_severity` field, and the secondary_stats `hull` pool needs defined
   damage increments per severity. This is a content-only blocker, not a
   code blocker, and can be authored in parallel with engine work.

5. **Extend-and-return rule.** Content-only or engine rule? Recommendation:
   engine rule with content override — if no content rule fires, the engine
   auto-resets to the confrontation's default starting state after any turn
   where no hit landed and `closure: opening_fast` appears in at least one
   actor's descriptor. Content can override this via a future `post_turn_rule`
   field on the confrontation def.

## Implementation Order

Six stories, ordered to front-load de-risking and back-load content work:

1. **077-1: `ResolutionMode` enum + `resolution_mode` field on ConfrontationDef.**
   Additive, no behavior change. Existing confrontations default to `BeatSelection`.
   Pure type plumbing; zero runtime impact until consumed. Safe change to ship
   ahead of everything else.

2. **077-2: `per_actor_state` on `EncounterActor` + serialization round-trip
   tests.** Adds the HashMap field, ensures save/load preserves it, fixes any
   serde integration. The `HashMap<String, Value>` shape is validated here
   once so every downstream story can rely on it.

3. **077-3: `TurnBarrier` confrontation-scope investigation + extension.**
   Answer Open Question #1. If the barrier is already confrontation-safe,
   this is a documentation story. If not, it's a targeted extension. Must
   resolve before 077-5.

4. **077-4: Interaction table loader + `_from:` file pattern.** Add loader
   support for sourcing confrontation sub-files from adjacent YAML. Unit
   tests on the space_opera dogfight files as the test fixture. Resolves
   Open Question #2.

5. **077-5: `SealedLetterLookup` resolution handler.** The new match arm in
   the confrontation resolution dispatch. Reads actor commits from the
   barrier, looks up the cell, applies per-actor deltas. Requires 077-1,
   077-2, 077-3, 077-4 complete. OTEL spans land here.

6. **077-6: Narrator cockpit-POV prompt extension.** Teach the unified
   narrator to render per-actor views from `per_actor_state`, strictly
   forbidding geometry not present in the descriptor. Full integration
   test with the `duel_01` scenario end-to-end through a real narrator
   call. OTEL span audit gate (see CLAUDE.md).

Stories 077-1 through 077-4 are independent and can run in parallel. 077-5
depends on all four. 077-6 depends on 077-5. Total: four parallel tracks
then a sequential two-story tail.

### Content-side parallel work (no code dependency, can start immediately)

- **077-C1:** Extend `interactions_mvp.yaml` cells with `hit_severity` column
  (graze | clean | devastating). Closes damage-model blocker.
- **077-C2:** Author the "extend-and-return" rule as either a post-turn
  content clause or a marker for engine rule (per Open Question #5).
- **077-C3:** Paper-playtest `duel_01.md` 3-5 more times, annotate calibration
  tags, adjust cell deltas for any `lopsided` or `confusing` tags.
- **077-C4:** After MVP validates, author `duel_02.md` with a `tail_chase`
  starting state and a 16-cell interaction table for it. This is the proof
  that the confrontation generalizes to additional starting states.

Content stories block nothing but have pre-req information for later code
stories, particularly 077-5 (which needs final interaction cells) and 077-6
(which needs refined narration hints).

---

## Addendum — Reuse Audit (for the Ministry's records)

The Architect's pragmatic-restraint doctrine requires proving existing
infrastructure cannot solve the problem before proposing new code. Audit
summary:

| Need | Existing infrastructure | Verdict |
|---|---|---|
| Encounter container | `StructuredEncounter` (ADR-033) | **Reuse with additive extensions** |
| Commit-and-reveal | `TurnBarrier` (Epic 13) | **Reuse as-is, pending scope check** |
| Narrator rendering | Unified narrator (ADR-067) | **Reuse with prompt extension only** |
| Per-player views | `SharedSession.perception_filters` | **Reuse hook for cockpit filter** |
| Genre YAML loading | Genre pack loader | **Extend with `_from:` sub-file pattern** |
| Save/load | StructuredEncounter serde | **Reuse; round-trip tested by 077-2** |
| Mood wiring | MusicDirector `mood_override` (ADR-033) | **Reuse; declares `mood: dogfight`** |
| Observability | OTEL span infrastructure (ADR-031, ADR-058) | **Reuse; new span names only** |
| Progression | Four-track affinities (existing) | **Reuse; dogfight reads affinity → skill tier** |

**Net new Rust code:** one enum, three optional struct fields, one match arm
in the confrontation handler, one serialization round-trip test, one OTEL
span module. **Everything else is reuse.** This is the correct shape for a
subsystem that leverages two years of accumulated encounter infrastructure
rather than reinventing it.

---

**Stamp:** `ARCHITECTURALLY APPROVED — PENDING COMMITTEE REVIEW`
