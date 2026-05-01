# Canned Openings — Unified `Opening` Schema, AuthoredNpc, World-Tier Authoring

**Date:** 2026-05-01
**Status:** Design — pre-implementation
**Author:** The Man in Black (architect)
**Brainstormed with:** Keith Avery
**Companion docs:**
- `docs/relationship-systems.md` (relationship-systems reference; READ FIRST)
- `docs/adr/014-diamonds-and-coal.md` (chassis bond ledger)
- `docs/adr/020-npc-disposition.md` (NPC disposition system; drift)
- `docs/superpowers/specs/2026-04-29-rig-mvp-coyote-star-design.md` (rig taxonomy slice)

## Purpose

Solo opening for Coyote Star currently freelances. The narrator picks an arbitrary canonical location (Mendes' Post on New Claim) instead of the world's authored starting region (Far Landing) and runs the textbook RPG bar-quest cliché — bartender, deal-broker, "I've got a job for you" — against three explicit AVOID directives that say not to do exactly that.

Root cause is structural: the existing `OpeningHook` schema (used for solo) ships only sketch templates — `archetype + situation + tone + avoid + first_turn_seed` — and lets the narrator improvise prose. The existing `MpOpening` schema (used for MP) ships full authored prose plus chassis/crew/per-PC composition slots. **Solo gets a sketch; MP gets a scene.** The asymmetry is the bug.

This design unifies the two into a single `Opening` schema, makes world-tier authoring the canonical path (genre tier dies), and introduces an `AuthoredNpc` model so named NPCs (especially the Kestrel's crew) live as authored content rather than narrator improv. Coyote Star ships a chargen-keyed bank; Aureate Span migrates the four genre-tier archetypes into world-tier content.

## Audience anchors

Per CLAUDE.md, weighed against the playgroup:

- **Keith** (forever-GM, solo first-fired this design): opening must land at the world's authored starting region. The Kestrel's voice — already authored, already dialed — must be the load-bearing register on turn 1. The first scene must feel *chosen*, not rolled.
- **Sebastien** (mechanics-first): every opening firing surfaces in OTEL — `opening.resolved`, `opening.played`, `npc.authored_loaded`, `rig.voice_register_change`. The bond-tier name-form upgrade is visible in the panel from the first turn.
- **James** (narrative-first): the cozy galley scene with named crew (Becky Chambers / Firefly texture) is the primary fictive contract for solo Coyote Star. The opening establishes "you are crew of this ship with these people" before the first player input.
- **Alex** (slow typist): no turn-1 question. The first turn closes on a declarative, not a "what do you do?" — the player can sit in the breath as long as they want.

## Locked decisions (this brainstorm)

1. **Single `Opening` schema** replaces both `OpeningHook` (solo, sketch) and `MpOpening` (MP, prose). One file per world: `worlds/{slug}/openings.yaml`.
2. **Genre-tier `space_opera/openings.yaml` is deleted.** Its four archetypes (`arena_trial`, `diplomatic_incident`, `ship_crisis`, `first_contact`) migrate to `aureate_span/openings.yaml` where their high-stakes tone fits the world. World-tier becomes mandatory; no genre-tier fallback.
3. **Bank size: small bank, keyed to chargen `background`.** Coyote Star ships 4 background-keyed solo openings + 1 fallback + 1 MP entry. The chargen `background` choice determines which scene fires.
4. **Crew lives on `chassis_instance` as a flat reference list.** `crew_npcs: list[str]` references AuthoredNpc ids in `worlds/{slug}/npcs.yaml`. No `CrewMembership` wrapper — relationship is "this NPC is aboard this ship," nothing more.
5. **Authored NPCs use the existing relationship machinery.** `AuthoredNpc.initial_disposition` pre-seeds `Npc.disposition` (ADR-020); chassis bond stays in `rigs.yaml:bond_seeds` (ADR-014). No new relationship system invented in this story.
6. **Names come from the namegen, not from invention.** Authored NPCs get names via `pf namegen` against `worlds/{slug}/cultures/*.yaml`. Validator rejects empty names; no defaults, no fallbacks.
7. **No turn-1 question.** Validator: `first_turn_invitation` MUST NOT contain `?`. Existing `coyote_star/mp_opening.yaml` violates this; migration revises it.
8. **`OpeningSetting` supports both ship-anchored and location-anchored.** Coyote Star openings are chassis-anchored ("aboard the Kestrel, galley"). Aureate openings are location-anchored ("the Imperatrix's arena, threshold gate"). Exactly one anchor per opening, model_validator-enforced.
9. **Forward-only migration.** Live `2026-05-01-coyote_star` and `2026-04-30-coyote_star-mp` saves keep their narrative as-is. Resumed sessions skip opening resolution and AuthoredNpc pre-loading; only fresh sessions get the new pipeline.
10. **Out of scope:** mid-session catalysts, per-PC NPC disposition, NPC↔NPC relationships, granular attitudes, additional chassis instances, conlang/voice integration, `ScenarioNpc`/`AuthoredNpc` unification, watcher-event location-validation. Each listed in §10.

## Architectural invariant — rules-in-genre / flavor-in-world

Per SOUL.md "Crunch in the Genre, Flavor in the World." This design is governed by it strictly.

| Layer | Owns | Files in this design |
|---|---|---|
| **Cross-genre Python** | `Opening` schema, `AuthoredNpc` schema, renderer, trigger taxonomy, validators, OTEL spans, mandatory-world-tier policy, "no turn-1 question" rule | `genre/models/narrative.py`, `genre/models/world.py`, `genre/models/rigs_world.py`, `server/dispatch/opening.py` |
| **Genre-tier YAML** (rules) | Cross-world structural defaults — chassis classes, archetype catalogs (already follows this pattern: `chassis_classes.yaml` is rules; `rigs.yaml` is flavor) | No new files at genre tier. `space_opera/openings.yaml` deleted because its content was flavor masquerading as rules. |
| **World-tier YAML** (flavor) | All prose, names, AVOID lists, voice lines, crew rosters, micro-bleed catalogs, chargen-keyed bank entries | `coyote_star/openings.yaml`, `coyote_star/npcs.yaml`, `coyote_star/rigs.yaml` (extended), `aureate_span/openings.yaml`, `aureate_span/npcs.yaml` |

**Anti-pattern callout:** the schema does NOT encode per-world or per-genre tonal preferences. No `world_slug == "coyote_star"` branches. No `if genre == "space_opera"` logic. No `tone.stakes_max: low` at the model level. "Cozy" is achieved through authored prose + AVOID lists. "High-stakes" is achieved through the same mechanism with different prose. Coyote Star and Aureate Span compile through *exactly the same code path*.

---

## 1. Schema

### 1.1 `Opening` (in `sidequest/genre/models/narrative.py`)

Replaces both `OpeningHook` and `MpOpening`. Single model handles solo and MP.

```python
class OpeningTrigger(BaseModel):
    """Selection rules — how the bank picks this Opening at chargen-complete time."""
    model_config = {"extra": "forbid"}
    mode: Literal["solo", "multiplayer", "either"] = "either"
    min_players: int = 1
    max_players: int = 6
    backgrounds: list[str] = Field(default_factory=list)
    # Empty backgrounds = matches any chargen background (fallback entry).
    # Non-empty = only fires when PC's background is in the list.

class OpeningSetting(BaseModel):
    """Either ship-anchored OR location-anchored. Exactly one."""
    model_config = {"extra": "forbid"}
    chassis_instance: str | None = None
    interior_room: str | None = None        # required iff chassis_instance set
    location_label: str | None = None       # required iff chassis_instance is None
    situation: str = ""
    present_npcs: list[str] = Field(default_factory=list)
    # NPCs to pre-load for location-anchored openings. MUST be empty when
    # chassis_instance is set (then crew_npcs supplies the list).

    @model_validator(mode="after")
    def _exactly_one_anchor(self) -> Self:
        ship = self.chassis_instance is not None
        place = self.location_label is not None
        if ship == place:
            raise ValueError(
                "OpeningSetting must specify exactly one of "
                "chassis_instance (with interior_room) OR location_label"
            )
        if ship and not self.interior_room:
            raise ValueError("interior_room required when chassis_instance is set")
        if ship and self.present_npcs:
            raise ValueError(
                "present_npcs must be empty for chassis-anchored openings; "
                "use chassis_instance.crew_npcs instead"
            )
        return self

class OpeningTone(BaseModel):
    model_config = {"extra": "forbid"}
    register: str = ""
    stakes: str = ""
    complication: str = ""
    sensory_layers: dict[str, str] = Field(default_factory=dict)
    avoid_at_all_costs: list[str] = Field(default_factory=list)

class PerPcBeat(BaseModel):
    model_config = {"extra": "forbid"}
    applies_to: dict[str, str]
    # keys constrained to {"background", "drive", "race", "class"}
    beat: str

class SoftHook(BaseModel):
    model_config = {"extra": "forbid"}
    kind: str = "pull_not_push"
    timing: str = "surfaces if conversation lulls; otherwise wait for turn 2"
    narration: str = ""
    escalation_path: dict[str, str] = Field(default_factory=dict)

class PartyFraming(BaseModel):
    """MP-only. Omitted from directive when mode == solo."""
    model_config = {"extra": "forbid"}
    already_a_crew: bool = False
    bond_tier_default: BondTier = "trusted"
    shared_history_seeds: list[str] = Field(default_factory=list)
    narrator_guidance: str = ""

class MagicMicrobleed(BaseModel):
    """Optional — Reach-bleeds-through detail at intensity 0.25."""
    model_config = {"extra": "forbid"}
    detail: str
    cost_bar: str | None = None

class Opening(BaseModel):
    model_config = {"extra": "allow"}
    id: str
    name: str = ""
    triggers: OpeningTrigger
    setting: OpeningSetting
    tone: OpeningTone = Field(default_factory=OpeningTone)
    establishing_narration: str
    first_turn_invitation: str = ""
    rig_voice_seeds: list[dict[str, Any]] = Field(default_factory=list)
    per_pc_beats: list[PerPcBeat] = Field(default_factory=list)
    soft_hook: SoftHook = Field(default_factory=SoftHook)
    party_framing: PartyFraming | None = None
    magic_microbleed: MagicMicrobleed | None = None

    @field_validator("first_turn_invitation")
    @classmethod
    def _no_question(cls, v: str) -> str:
        if "?" in v:
            raise ValueError(
                "first_turn_invitation must not contain '?'. "
                "Per SOUL pacing, turn 1 closes on a declarative; the player "
                "should be able to sit in the breath without being prompted."
            )
        return v

    @field_validator("establishing_narration", "first_turn_invitation")
    @classmethod
    def _no_placeholder_text(cls, v: str) -> str:
        forbidden = ["[authored", "[TBD", "[migrated", "[placeholder"]
        for marker in forbidden:
            if marker.lower() in v.lower():
                raise ValueError(
                    f"Field contains placeholder marker {marker!r} — "
                    "world-builder pass not complete"
                )
        return v
```

### 1.2 `AuthoredNpc` (new file or in `sidequest/genre/models/world.py`)

```python
class AuthoredNpc(BaseModel):
    """World-authored NPC. Lives in worlds/{slug}/npcs.yaml. Instantiated
    as runtime Npc at world materialization (fresh sessions only) and
    pre-loaded into the registry — authored NPCs are 'present from session
    start.' Distinct from ScenarioNpc (mystery-pack-specialized — keeps
    its own subset; possible future unification).

    Voice mannerisms / distinctive verbal tics: write them as
    history_seeds prose. Narrator extracts and uses them. NPCs are good
    at being themselves — no parallel voice schema needed."""
    model_config = {"extra": "forbid"}
    id: str
    name: str                              # produced via namegen, never invented
    pronouns: str = ""
    role: str = ""
    ocean: dict[str, float] | None = None  # same shape as Npc.ocean
    appearance: str = ""
    age: str = ""
    distinguishing_features: list[str] = Field(default_factory=list)
    history_seeds: list[str] = Field(default_factory=list)
    initial_disposition: int = Field(default=0, ge=-100, le=100)
    # Pre-seeds Npc.disposition at world materialization. ADR-020 system.
    # Crew authored at +50 to +70 (firmly friendly).
```

### 1.3 `ChassisInstanceConfig` extension (in `genre/models/rigs_world.py`)

```python
class ChassisInstanceConfig(BaseModel):
    # ... existing fields ...
    crew_npcs: list[str] = Field(default_factory=list)
    # Each entry references an AuthoredNpc.id in worlds/{slug}/npcs.yaml.
    # No wrapper class; relationship is "this NPC is aboard this ship,"
    # nothing more. Role / personality / mannerisms live on the AuthoredNpc.
```

### 1.4 Validators (cross-file, run after world load)

| # | Validator |
|---|---|
| 1 | `Opening.first_turn_invitation` does not contain `?` (pydantic field validator) |
| 2 | `OpeningSetting.chassis_instance` (when set) resolves to a real chassis in `worlds/{slug}/rigs.yaml` |
| 3 | `OpeningSetting.interior_room` (when set) is in the chassis's `interior_rooms` |
| 4 | Every entry in `chassis_instance.crew_npcs` resolves to an `AuthoredNpc.id` in `worlds/{slug}/npcs.yaml` |
| 5 | `AuthoredNpc.id` unique per world |
| 6 | `PerPcBeat.applies_to` keys ∈ `{"background", "drive", "race", "class"}` |
| 7 | World ships ≥1 solo opening AND ≥1 MP opening (by `triggers.mode`) |
| 8 | Every chargen background in `char_creation.yaml` is reachable by some opening (either via `triggers.backgrounds` containing it, or via a `triggers.backgrounds: []` fallback) |
| 9 | `OpeningSetting._exactly_one_anchor` model_validator |
| 10 | `Opening` prose fields contain no placeholder markers (`[authored`, `[TBD`, etc.) |
| 11 | `AuthoredNpc.initial_disposition` ∈ [-100, 100] (pydantic Field constraint) |
| 12 | `present_npcs` empty when `chassis_instance` set; non-empty entries resolve to AuthoredNpc ids |
| 13 | `AuthoredNpc.name` non-empty (pydantic + cross-validator) |

---

## 2. Runtime data flow

### 2.1 Lifecycle

```
World load → Materialization → Connect → Chargen → First turn
```

### 2.2 Stage detail

**World load** (`genre/loader.py`): parse `openings.yaml` (mandatory) and `npcs.yaml` (optional but referenced by `crew_npcs`). Run all 13 validators. Fail loud on any violation. Delete `mp_opening.yaml` and genre-tier `openings.yaml` parser paths.

**World materialization** (`game/world_materialization.py`): for fresh sessions only (interaction == 0 AND character_count == 0), instantiate runtime `Npc` per `AuthoredNpc` with `disposition = initial_disposition`. Pre-load into `state.npcs`. Emit `npc.authored_loaded` per. Resumed sessions skip this step.

**Connect** (`handlers/connect.py`): remove pre-chargen `resolve_opening` calls. Session-data `opening_directive` slot stays but is populated post-chargen.

**Chargen completion** (`server/websocket_session_handler.py`): on transition Building → Playing, call new `_resolve_opening_post_chargen(snapshot, pack, world_slug, mode)`:
- Filter `world.openings` by mode, player_count, PC's background
- Validator 8 guarantees ≥1 candidate; defensive code raises `OpeningResolutionError` if zero
- RNG-seeded pick from candidates; emit `opening.resolved {opening_id, mode, candidates_count, rng_seed, pc_background}`
- Render directive via `_render_directive`; emit `opening.directive_rendered`
- Stash on session_data as `(opening_seed, opening_directive)`
- Trigger first narrator turn

**Directive renderer** (`server/dispatch/opening.py` — renamed from `opening_hook.py`): structured directive with sections (Setting, Establishing Narration, Chassis Voice or Location Pre-loaded NPCs, Magic Register, Microbleed if present, Per-PC Beat, Tone, Soft Hook, Party Framing if MP, First Turn Invitation). Boilerplate `=== OPENING SCENARIO === / === END OPENING ===` preserved for GM-panel regex parity. See §6 for full directive shape.

**First turn**: directive injected into Early zone (Full tier, opening only). Existing one-shot consumption: directive cleared after, emits `opening.played {opening_id, narrator_session_id, turn_id}`.

### 2.3 OTEL inventory

| Span | When | Payload |
|---|---|---|
| `npc.authored_loaded` | Materialization, per AuthoredNpc | `{npc_id, name, disposition, world}` |
| `opening.resolved` | Chargen-complete, post-selection | `{opening_id, mode, candidates_count, rng_seed, pc_background}` |
| `opening.directive_rendered` | Post-render | `{opening_id, sections_present, char_count, has_microbleed, has_party_framing}` |
| `opening.played` | First-turn consumption | `{opening_id, narrator_session_id, turn_id}` |
| `opening.no_match` | Defensive — Validator 8 bypass | `{world, mode, pc_background, candidate_count}` — fails loud |

Plus existing: `rig.voice_register_change` fires on first-turn name-form resolution (initial bond_tier → name-form mapping is observable from turn 1).

---

## 3. Coyote Star content shape

Solo bank: 4 background-keyed entries + 1 fallback + 1 MP entry, all aboard the Kestrel.

### 3.1 `worlds/coyote_star/openings.yaml` (new)

Per-entry shape illustrated; world-builder fills `[authored]` placeholders.

```yaml
version: "0.1.0"
world: coyote_star
genre: space_opera

openings:
  # Solo bank — chargen-keyed
  - id: solo_far_landing_morning
    name: "Galley, Morning Coast — Far Landing Approach"
    triggers:
      mode: solo
      backgrounds: ["Far Landing Raised Me"]
    setting:
      chassis_instance: kestrel
      interior_room: galley
      situation: "Inbound for Far Landing, an hour out, slow approach."
    tone:
      register: "warm, lived-in, dry"
      stakes: "none on turn 1"
      complication: "defer to turn 2 or 3"
      avoid_at_all_costs:
        - any confrontation
        - any dice roll
        - rig-emergency framing
        - moving the player without their input
        - introducing an antagonist in dialogue range
        - ending the turn with a question
    establishing_narration: "[authored — galley scene, Far Landing in the porthole]"
    first_turn_invitation: "[authored — declarative close, NO `?`]"
    rig_voice_seeds:
      - context: "first PC enters the galley"
        line: "[authored — uses {first_name} per trusted bond_tier]"
    per_pc_beats:
      - applies_to: { background: "Far Landing Raised Me" }
        beat: "[authored — datapad on the counter, the strip outside, etc.]"
    soft_hook:
      kind: pull_not_push
      timing: "surfaces if conversation lulls; otherwise wait for turn 2"
      narration: "[authored — Kestrel queues an inbound comm]"
      escalation_path:
        turn_2_or_3: "[authored — the wrinkle]"
    magic_microbleed:
      detail: "[authored — one quiet uncanny detail at intensity 0.25]"

  - id: solo_turning_hub_cockpit
    name: "Cockpit, Coast — Hub on the Rear Scope"
    triggers: { mode: solo, backgrounds: ["Turning Hub Was the Whole World"] }
    setting:
      chassis_instance: kestrel
      interior_room: cockpit
    # ... same shape ...

  - id: solo_engineering_wirework
    triggers: { mode: solo, backgrounds: ["Wirework Made Me"] }
    setting:
      chassis_instance: kestrel
      interior_room: engineering
    # ... same shape ...

  - id: solo_galley_fixer
    triggers: { mode: solo, backgrounds: ["Far Landing Fixer"] }
    setting:
      chassis_instance: kestrel
      interior_room: galley
    # ... same shape ...

  - id: solo_galley_fallback
    name: "Galley, Morning Coast — Coast Day"
    triggers: { mode: solo, backgrounds: [] }       # fallback for unmatched bg
    setting:
      chassis_instance: kestrel
      interior_room: galley
    # ... most generic "morning aboard" prose ...

  # MP entry — folded from existing mp_opening.yaml
  - id: mp_galley_jumprest
    name: "Galley, Jump-Rest"
    triggers:
      mode: multiplayer
      min_players: 2
      max_players: 6
      backgrounds: []
    setting:
      chassis_instance: kestrel
      interior_room: galley
      situation: "Mid-jump-rest. Inbound for Mendes' Post, fourteen hours."
    establishing_narration: "[migrated from mp_opening.yaml]"
    first_turn_invitation: "[migrated — `?` REMOVED per validator 1]"
    rig_voice_seeds:    # [migrated]
    per_pc_beats:       # [migrated, keyed to chargen `drive`]
    soft_hook:          # [migrated]
    party_framing:
      already_a_crew: true
      bond_tier_default: trusted
      shared_history_seeds: # [migrated]
      narrator_guidance: "[migrated]"
```

### 3.2 `worlds/coyote_star/npcs.yaml` (new)

```yaml
version: "0.1.0"
world: coyote_star

npcs:
  # Kestrel crew — names produced via `pf namegen` against
  # cultures/{voidborn,free_miners,tsveri,hegemonic,broken_drift}.yaml.
  # World-builder picks: ~1 voidborn captain, 1 free_miner engineer,
  # 1 tsveri or hegemonic doc (multispecies texture), 1 voidborn cook.
  # 4 crew is the suggested minimum; world-builder may add more.

  - id: kestrel_captain
    name: "[namegen: voidborn]"
    pronouns: "[authored]"
    role: "captain"
    ocean: { O: 0.5, C: 0.7, E: 0.4, A: 0.5, N: 0.4 }   # tuned by world-builder
    appearance: "[authored brief]"
    age: "[authored]"
    distinguishing_features: ["[authored]"]
    history_seeds:
      - "[authored]"
    initial_disposition: 60   # firmly friendly — PC's captain

  - id: kestrel_engineer
    name: "[namegen: free_miners]"
    role: "engineer"
    initial_disposition: 55
    # ... same shape ...

  - id: kestrel_doc
    name: "[namegen: tsveri or hegemonic]"
    role: "ship's doctor"
    initial_disposition: 50
    # ... same shape — multispecies texture if tsveri ...

  - id: kestrel_cook
    name: "[namegen: voidborn or free_miners]"
    role: "cook"
    initial_disposition: 60
    # ... same shape ...

  # Pre-canon NPC referenced by cartography.yaml — keeps narrator from
  # auto-registering with random naming each session.
  - id: dura_mendes
    name: "Dura Mendes"
    pronouns: "[authored]"
    role: "matriarch — Mendes' Post"
    appearance: "[authored from cartography]"
    history_seeds:
      - "Cado Mendes' granddaughter"
      - "[authored]"
    initial_disposition: 0
```

### 3.3 `worlds/coyote_star/rigs.yaml` (modified)

```yaml
chassis_instances:
  - id: kestrel
    # ... existing fields ...
    crew_npcs:
      - kestrel_captain
      - kestrel_engineer
      - kestrel_doc
      - kestrel_cook
```

---

## 4. Aureate Span content shape

Four genre-tier archetypes migrate to world-tier `aureate_span/openings.yaml`. High-stakes / in-medias-res tone is the *right* fit for Aureate (gladiatorial spectacle, brittle alien negotiations, dying-star drama), so the prose KEEPS its in-medias-res character — only the schema changes.

### 4.1 `worlds/aureate_span/openings.yaml` (new)

```yaml
version: "0.1.0"
world: aureate_span
genre: space_opera

openings:
  - id: solo_arena_trial
    name: "Sand on the Threshold"
    triggers:
      mode: solo
      backgrounds: ["[Aureate background label TBD]"]
    setting:
      location_label: "the Imperatrix's Arena, threshold gate"
      situation: "Pre-bout assembly; the crowd's noise already a wall."
      present_npcs: ["[arena master / patron — id from npcs.yaml]"]
    tone:
      register: "[authored — operatic, gilded, charged]"
      stakes: "imminent — this opening is in-medias-res by design"
      avoid_at_all_costs:
        - ending the turn with a question
        # Note: arena_trial KEEPS in-medias-res tone. Coyote Star's
        # "any confrontation / any dice roll" AVOIDs are world-specific
        # contracts and do NOT carry over.
    establishing_narration: "[authored — migrated from genre-tier first_turn_seed]"
    first_turn_invitation: "[authored — declarative close, NO `?`]"

  - id: solo_diplomatic_incident
    triggers: { mode: solo, backgrounds: ["[TBD]"] }
    setting:
      location_label: "[authored — Promenade landing, envoy hall, etc.]"
    # ... same shape ...

  - id: solo_ship_crisis
    triggers: { mode: solo, backgrounds: ["[TBD]"] }
    setting:
      location_label: "[authored — docking ring, lifeboat bay, etc.]"
      # IF world-builder wants this anchored to a ship, add a chassis_instance
      # to aureate_span/rigs.yaml and switch the anchor. Optional.
    # ... same shape ...

  - id: solo_first_contact
    triggers: { mode: solo, backgrounds: ["[TBD]"] }
    setting:
      location_label: "[authored — alien delegation chamber, sensor outpost]"
    # ... same shape ...

  - id: mp_arrival_at_the_span
    triggers: { mode: multiplayer, min_players: 2, max_players: 6, backgrounds: [] }
    setting:
      location_label: "[authored — shared arrival point, e.g., the Promenade]"
    party_framing:
      already_a_crew: false
      bond_tier_default: neutral
      narrator_guidance: "[authored — Aureate may not be found-family]"
    # ... rest of shape ...
```

### 4.2 `worlds/aureate_span/npcs.yaml` (new)

Minimal; world-builder adds 4–8 named NPCs (arena master, patron, ambassadors, alien envoy + handler). Names via `pf namegen` against `aureate_span/cultures/*.yaml`.

---

## 5. Files in scope (full inventory)

### 5.1 Content (YAML)

| File | Action |
|---|---|
| `genre_packs/space_opera/openings.yaml` | **delete** |
| `genre_packs/space_opera/worlds/coyote_star/mp_opening.yaml` | **delete** |
| `genre_packs/space_opera/worlds/coyote_star/openings.yaml` | **create** — solo bank + MP entry |
| `genre_packs/space_opera/worlds/coyote_star/npcs.yaml` | **create** — Kestrel crew + Dura Mendes |
| `genre_packs/space_opera/worlds/coyote_star/rigs.yaml` | **modify** — `kestrel.crew_npcs` added |
| `genre_packs/space_opera/worlds/aureate_span/openings.yaml` | **create** — 4 solo + 1 MP migrated |
| `genre_packs/space_opera/worlds/aureate_span/npcs.yaml` | **create** — referenced NPCs |

### 5.2 Python

| File | Action |
|---|---|
| `genre/models/narrative.py` | **modify** — delete `OpeningHook`, `MpOpening`; add `Opening` and sub-models |
| `genre/models/rigs_world.py` | **modify** — `crew_npcs: list[str]` on `ChassisInstanceConfig` |
| `genre/models/world.py` (or new file) | **add** — `AuthoredNpc` model |
| `genre/models/scenario.py` | **untouched** |
| `genre/loader.py` | **modify** — load `openings.yaml`, `npcs.yaml`; remove old paths |
| `game/world_materialization.py` | **modify** — pre-load AuthoredNpcs (fresh sessions only) |
| `server/dispatch/opening_hook.py` | **rename to `opening.py`, rewrite** |
| `handlers/connect.py` | **modify** — remove pre-chargen `resolve_opening` calls |
| `server/websocket_session_handler.py` | **modify** — call `_resolve_opening_post_chargen` at chargen-complete |
| `telemetry/spans/opening.py` | **create** — five new spans |

### 5.3 Tests

See §7 below.

---

## 6. Directive structure (renderer output)

For a chassis-anchored solo opening, the directive injected into the narrator's Early zone:

```
=== OPENING SCENARIO ===
Mode: solo
Title: {opening.name}

Setting: aboard the {chassis.name}, {interior_room.display_name}
Situation: {opening.setting.situation}

ESTABLISHING NARRATION (play this scene):
{opening.establishing_narration}

CHASSIS VOICE (the {chassis.name} speaks):
- Name-form for this PC at bond_tier {bond.bond_tier_chassis}: "{resolved_name_form}"
- Default register: {chassis.voice.default_register}
- Vocal tics: {chassis.voice.vocal_tics}
- Silence register: {chassis.voice.silence_register}
{rig_voice_seeds rendered as "context: line" pairs}

MAGIC REGISTER ({world.name} bleeds through):
{magic.narrator_register}

{IF opening.magic_microbleed:}
MICROBLEED (one quiet uncanny detail to weave in once):
{microbleed.detail}
{IF microbleed.cost_bar: tick {cost_bar} by 0.05 via narration}

PRE-LOADED NPCS PRESENT (already in registry — do NOT auto-register):
{for each npc_id in chassis.crew_npcs:}
- {npc.name} ({npc.role}): {npc.appearance}, disposition: {npc_attitude}
  History: {1-2 history_seeds picked deterministically by opening_id+npc_id}

PER-PC BEAT (textural moment for this PC's chargen):
{first matching beat, or omitted}

TONE:
- Register: {opening.tone.register}
- Stakes: {opening.tone.stakes}
- Sensory layers: {opening.tone.sensory_layers}
- AVOID: {opening.tone.avoid_at_all_costs}

SOFT HOOK (only when conversation lulls; otherwise wait turn 2 or 3):
{opening.soft_hook.narration}
- Timing: {opening.soft_hook.timing}
- Escalation paths: {opening.soft_hook.escalation_path}

FIRST TURN INVITATION (close the scene on this — NO closing question):
{opening.first_turn_invitation}

=== END OPENING ===
```

For MP, add `PARTY FRAMING:` block. For location-anchored (Aureate), replace `Setting: aboard the {chassis}, {room}` with `Setting: at {location_label}`; omit the CHASSIS VOICE block; pre-loaded NPCs come from `setting.present_npcs` instead of `chassis.crew_npcs`.

---

## 7. Test strategy

### 7.1 Unit tests

- `test_opening_schema_parse.py` — YAML round-trips through pydantic
- One test per validator 1–13 (see §1.4)
- `test_opening_renderer_determinism.py` — same opening + same RNG seed → same directive output
- `test_filter_logic.py` — mode × backgrounds × player_count combinations

### 7.2 Integration tests

- `test_world_load_cross_file_validation.py` — broken cross-references fail with specific messages
- `test_world_load_clean.py` — both Coyote Star and Aureate Span produce fully-resolved worlds
- `test_chassis_anchored_vs_location_anchored.py` — both renderer paths produce well-formed directives

### 7.3 Wiring tests (load-bearing)

- `test_first_turn_uses_authored_setting.py` — connect → chargen → first turn. Asserts `state.location_update` matches the chosen opening's setting (interior_room display name OR location_label), NOT a narrator-invented place. **Catches the regression that motivated this design.**
- `test_authored_npcs_in_state_before_first_turn.py` — same flow. Asserts every `chassis.crew_npcs` entry is in `state.npcs` with seeded disposition before turn 1 fires.
- `test_no_silent_genre_fallback.py` — world without `openings.yaml` fails at load
- `test_chargen_background_uncovered.py` — world whose `char_creation.yaml` declares background X without coverage → load fails

### 7.4 Migration tests

- `test_existing_mp_opening_preserves_intent.py` — old `coyote_star/mp_opening.yaml` (kept as a fixture string), new `coyote_star/openings.yaml` MP entry — rendered directive contains the same authored prose excerpts (modulo `?` removal)

### 7.5 OTEL tests

- `test_opening_otel_spans_fire.py` — all five new spans fire on the right transitions, with the right payloads

---

## 8. Migration / rollout

### 8.1 Forward-only

Live saves stay as-is. Resumed sessions guard:
- World materialization for resumed sessions (interaction > 0 OR character_count > 0) does **not** pre-load AuthoredNpcs — registry is what it is.
- Resumed sessions skip opening resolution (existing guard at `connect.py:535-545`).
- Genre pack data is reloaded on resume; AuthoredNpc data is available in `pack.worlds[slug].authored_npcs` for narrator prompt construction if a future story chooses to consume it.

### 8.2 Existing live saves

- `2026-05-01-coyote_star` (solo, mid-game, round 5, location "New Claim — Refinery Causeway"): "Yes, And" applies — the bar opening is now canon. Mendes' Post and the Vela-9 spur are part of Zanzibar's backstory. No retro-fix.
- `2026-04-30-coyote_star-mp` (MP, mid-game): same — resumed-session guard skips opening resolution.

### 8.3 Order within the implementation PR

Single PR ships content + code together. Schema cuts over atomically. Existing saves' `opening_directive` was already None (consumed turn 1) so no re-render attempt happens on resume.

### 8.4 World-builder pass timing

Coyote Star content authoring is on the critical path for this story (drives the live playtest fix). Aureate Span content can lag — Validator 10 (`[authored]` rejection) makes Aureate fail-loud-on-load until prose is filled in. That's the right pressure; Aureate becomes unselectable until a content story lands.

---

## 9. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Aureate Span content authoring lags | High | Validator 10 fails loud; aureate becomes unselectable. Follow-up content story tracked. |
| Validator 1 (`?`) catches existing prose | Certain | Migration step rewrites `coyote_star/mp_opening.yaml`'s closing line during the same PR |
| Narrator ignores directive and freelances | Moderate | (a) `establishing_narration` is "play this scene" framing — much stronger than today's "Setting:" line; (b) wiring test forces regression to surface; (c) future watcher event for `state.location_update` validation listed in out-of-scope |
| RNG seed not threaded through | Medium | `_resolve_opening_post_chargen` accepts optional `rng: random.Random \| None = None`, defaulted; tests pass seeded |
| Other space_opera worlds exist and break | None — verified at design time | Confirmed 2026-05-01: only `coyote_star` and `aureate_span` exist under `genre_packs/space_opera/worlds/`. Both covered by this design. If future worlds are added later, they must ship `openings.yaml` from creation; Validator 7+8 makes the requirement load-time enforced. |
| `present_npcs` dead weight for ship-anchored openings | Low | Validator 12 enforces empty + documented |

---

## 10. Out of scope (deferred follow-ups)

1. **Watcher event: `state.location_update` matches `opening.setting` on turn 1.** State-apply layer story.
2. **`discovered_regions` pollution bug** — separate story.
3. **Mid-session catalysts** — if Aureate's archetypes are ever wanted as turn-30 escalators in other worlds, a `Catalyst` model + trope-engine routing.
4. **Per-PC NPC disposition** — ADR-020 known gap.
5. **PC↔NPC pairwise bonds** — no system today.
6. **NPC↔NPC relationships** — same.
7. **Granular attitudes** (`wary`, `grateful`, `terrified`) — ADR-020 future work.
8. **Additional chassis instances** for Coyote Star (Bright Margin, Tide Singer) — content authoring.
9. **Conlang/voice integration for crew NPCs** — orthogonal subsystem.
10. **`ScenarioNpc` / `AuthoredNpc` unification** — possible cleanup, not on critical path.

---

## 11. Reference index

| Concern | File / ADR |
|---|---|
| Relationship systems guide | `docs/relationship-systems.md` |
| Chassis bond ledger | ADR-014, `game/chassis.py`, `genre/models/chassis.py`, `genre/models/rigs_world.py` |
| NPC disposition | ADR-020, `Npc.disposition` in `game/session.py`, `telemetry/spans/disposition.py` |
| Rig MVP spec | `docs/superpowers/specs/2026-04-29-rig-mvp-coyote-star-design.md` |
| Existing mp_opening.yaml | `genre_packs/space_opera/worlds/coyote_star/mp_opening.yaml` (deleted by this story) |
| Existing genre-tier openings | `genre_packs/space_opera/openings.yaml` (deleted by this story) |
| Magic register | `genre_packs/space_opera/worlds/coyote_star/magic.yaml:narrator_register` |
| Namegen CLI | `sidequest-server/sidequest/cli/namegen/`, `genre/names/generator.py` |

---

*Brainstormed 2026-05-01 with Keith Avery in `/superpowers:brainstorming` mode. Implementation plan to follow via `superpowers:writing-plans`.*
