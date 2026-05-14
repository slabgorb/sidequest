# Scenario Fixture Library — Wave 1 Design

**Date:** 2026-05-14
**Author:** Radar O'Reilly (DevOps) handed to GM lane mid-session
**Status:** Draft for user review
**Related:** ADR-092 (scene harness), Story 50-18 (hydrator landed 2026-05-13)

## Context

ADR-092's scene harness shipped in 50-18: `POST /dev/scene/{name}` hydrates a YAML fixture into a `GameSnapshot`, persists via `SqliteStore`, and returns a slug. UI accepts `?scene=NAME`; `python scripts/playtest.py --fixture NAME` skips chargen for headless runs.

Four fixtures exist (`combat_test`, `dogfight`, `negotiation`, `poker`), all dated 2026-04-21. They predate the epic-50 scenario/journal/disposition wave, **three of the four point at workshopping worlds** (`aureate_span`, `annees_folles`, `dust_and_lead`) that aren't in the active set — only `combat_test` (mutant_wasteland/flickering_reach) targets a live world. The hydrator also drops most of `GameSnapshot`.

### Active world map (load-bearing constraint for fixture targeting)

| Genre | World(s) available |
|---|---|
| `caverns_and_claudes` | `caverns_sunden` |
| `mutant_wasteland` | `flickering_reach` |
| `space_opera` | `coyote_star` |
| `tea_and_murder` | `glenross` (note: `seaboard_of_saints` spec just merged 2026-05-13 but the `worlds/` dir is not yet created) |
| `elemental_harmony` | **none** — `worlds/` dir is empty |

This drops elemental_harmony from Wave 1: no instantiable world means the hydrator can't validate the fixture against a live genre+world pair.

The need: a fixture library that lets us teleport into specific game states for fast iteration. Reaching states like "level-up moment", "mid-mystery accusation primed", "Edge near zero", or "merchant transaction in progress" naturally takes 20–30 minutes of play, which makes prompt iteration, OTEL verification, and balance tuning impractical.

## Hydrator Audit

`hydrate_fixture` (`sidequest-server/sidequest/game/scene_harness.py`) consumes ~20% of `GameSnapshot`'s surface today.

### Supported

- **Top-level:** `genre` (required), `world` (required), `location` → `current_region`, `turn` → `TurnManager`
- **Character (single, `characters[0]`):** `name`, `description`, `personality`, `level`, `hp`/`max_hp` (→ `EdgePool` via `{current, max, base_max}`), `inventory`, `statuses`, `backstory`, `narrative_state`, `hooks`, `char_class`, `race`, `pronouns`, `stats`. `ac` is dropped (no current home in Python `Character`).
- **NPC list:** `name`, `role`, `disposition` only. `description` and `personality` are seeded from `role` to satisfy non-blank validators.

### Silently dropped (relevant gaps)

| Goal | Missing field(s) on snapshot |
|---|---|
| Mystery mid-state (clues found, accusations primed) | `scenario_state` (`clue_graph`, `discovered_clues`, `npc_roles`, `guilty_npc`, `tension`) |
| Journal mixed-confidence | `Character.known_facts` |
| Pre-armed combat | `encounter` (`StructuredEncounter`) — `combat_test.yaml`'s `encounter:` block silently dropped |
| Magic / rituals | `magic_state`, `Character.abilities` |
| Progression mid-tier (about-to-level) | `Character.affinities` (XP / tier progress) |
| Trope mid-state | `active_tropes` |
| Merchant beyond placeholder | NPC inventory, `resources` pools |
| Companions | `companions` |
| Rigs (mech chassis) | `chassis_registry` |
| NPC relationships / beliefs / gossip | NPC has no fields beyond name/role/disposition |
| Tone axes | `axis_values` |
| Multi-PC fixtures (party) | Hydrator loads only `characters[0]`; no list ingest |

### Reachable today (no hydrator changes needed)

- Combat at specific PC level + Edge cap
- Multi-NPC face-off with set dispositions
- Specific location / region
- PC with starting inventory + stats + class/race
- Basic merchant scene (PC inventory + gold + NPC labeled "merchant")
- Veteran-tier PC drop (high level, full kit)

## Decision

Two-track plan, prioritised:

1. **Wave 1 — author 10 fixtures using only currently-supported fields.** Fix the 4 existing fixtures (rename for consistency, port the 2 broken ones to active packs).
2. **Wave 2 — file 5 hydrator-extension stories** to unlock the gap categories. Each unblocks a follow-on fixture batch.

This ships value now (fast combat tuning, reachable social/merchant scenes, genre coverage), surfaces the hydrator gaps as ranked backlog work, and avoids authoring against fields the hydrator silently drops.

## Wave 1 — Fixtures

### Naming convention

`{category}_{variant}_{genre}.yaml` — flat directory (current hydrator constraint), prefix-sortable. Categories: `combat`, `social`, `merchant`, `veteran`. Genre suffixes (active worlds only): `caverns` (caverns_and_claudes/caverns_sunden), `wasteland` (mutant_wasteland/flickering_reach), `space` (space_opera/coyote_star), `tea` (tea_and_murder/glenross).

### Combat tier scaling — same genre, varying difficulty (3)

Same archetype across the three so the only varying axis is difficulty. Used for ADR-093 confrontation calibration spot checks once H-3 lands; useful today for narrator behavior at varying Edge.

| Fixture | PC Level / Edge | Opposition | Test purpose |
|---|---|---|---|
| `combat_low_caverns` | Lvl 1, 10/10 Edge | 1 weak goblin (disposition −10) | Baseline combat math, narrator behavior on first hit |
| `combat_mid_caverns` | Lvl 3, 12/16 Edge | 3 mixed enemies (disposition −15..−25) | Mid-tier party-vs-many feel |
| `combat_high_caverns` | Lvl 5, 4/20 Edge | 4 enemies + champion | High tier + composure threshold (PC near bottom) |

### Genre coverage — one combat per remaining active pack (3)

| Fixture | Genre / World | Setup |
|---|---|---|
| `combat_brawl_wasteland` | mutant_wasteland / flickering_reach | Replaces `combat_test.yaml` — same content, consistent name |
| `combat_boarding_space` | space_opera / coyote_star | Ship boarding, Lvl 4 PC + 2 hostile crew (note: this batch loses elemental_harmony coverage because the pack has no live worlds — file as Wave 2 once a world ships) |
| `combat_dogfight_space` | space_opera / coyote_star | **Port** of `dogfight.yaml` — was aureate_span (workshopping), reframe Nyx Corvane to coyote_star |

### Social setups — without scenario_state (2)

| Fixture | Genre / World | Setup |
|---|---|---|
| `social_drawing_room_tea` | tea_and_murder / glenross | PC in drawing room with 4 NPCs at varying disposition (+30 / +10 / −5 / −25) — exercises 50-2 social confrontation triggers (negotiation/social_duel/scandal). When `seaboard_of_saints` ships, optionally fork a sibling. |
| `social_tavern_caverns` | caverns_and_claudes / caverns_sunden | Mixed-disposition tavern crowd, 5 NPCs, no clear hostile — tests narrator's social staging |

### Merchant (1)

| Fixture | Setup |
|---|---|
| `merchant_bazaar_wasteland` | PC with 200 gold + 3 trade goods, 1 NPC labeled `merchant` (disposition +5) + 2 other shoppers in marketplace location. Tests inventory_mutation OTEL when player buys/sells. |

### Veteran drop (1)

| Fixture | Setup |
|---|---|
| `veteran_drop_caverns` | Lvl 7 PC, full kit (5 items), 3 friendly NPCs (disposition +20..+40), no immediate threat. Tests late-game narrator behavior with a powerful PC and quiet stakes — does the narrator escalate appropriately or stall? |

### Triage of the 4 existing fixtures

- `combat_test.yaml` → **rename** to `combat_brawl_wasteland.yaml` (consistency with new naming) — the only existing fixture pointing at a live world
- `dogfight.yaml` → **port + rename** to `combat_dogfight_space.yaml` — change `world: aureate_span` (workshopping) to `world: coyote_star` (active), reframe Nyx Corvane / the intercept lane to coyote_star geography. Listed in Wave 1's "Genre coverage" row above
- `negotiation.yaml` → **port + rename** to `social_negotiation_tea.yaml` (was pulp_noir / annees_folles, both in workshopping; reframe Halloran/Moretti as a tea_and_murder backroom meeting) — keeps the well-written shape, points at an active pack
- `poker.yaml` → **port + rename** to `social_poker_wasteland.yaml` (was spaghetti_western / dust_and_lead; reframe Black Bart as a wasteland card-table heavy)

After triage: **13 fixtures total** (9 net-new + 4 ports/renames). `combat_dogfight_space` is counted under "Genre coverage" above; `social_negotiation_tea` and `social_poker_wasteland` are bonus social fixtures from porting (raising Wave 1 social count from 2 to 4).

### Acceptance criteria (per fixture)

1. `?scene=NAME` loads in the browser without 4xx/5xx error
2. `python scripts/playtest.py --fixture NAME` boots without exception
3. Fixture's PC + NPCs render correctly in the opening narration (names match, disposition reflected in tone)
4. OTEL `scene_harness.hydrate.ok` span fires with expected `character_count` / `npc_count`
5. Where applicable, the targeted subsystem fires its OTEL span on the next narrator turn:
   - combat → `confrontation.*` (and once H-3 lands, encounter pre-loaded)
   - social → `disposition.shift` or social confrontation trigger
   - merchant → `inventory_mutation` on buy/sell

## Wave 2 — Hydrator Extension Stories

File these into the backlog (epic 50 or new mini-epic for scene harness). Each unlocks a Wave 2 fixture batch. Sized by GM eyeball; PM can resize on intake.

| Story | Title | Pts | Unlocks |
|---|---|---|---|
| H-1 | Hydrate `Character.known_facts` (list of `KnownFact` with `Literal["Certain","Suspected","Rumored","Discovered"]` confidence) | 2 | Journal mid-state, mixed-confidence test fixtures |
| H-2 | Hydrate top-level `scenario_state` block (`clue_graph`, `discovered_clues`, `npc_roles`, `guilty_npc`, `tension`) | 5 | Mystery mid-state — accusation primed, gossip ready, clue graph N% explored. Unblocks 50-5/6/7/8 fixture-level testability |
| H-3 | Hydrate `encounter` (`StructuredEncounter`) — currently `combat_test.yaml`'s `encounter:` block silently dropped | 3 | Pre-armed combat fixtures, ADR-093 difficulty calibration spot tests |
| H-4 | Hydrate `magic_state` + `Character.abilities` | 5 | Magic / ritual / class-ability-active fixtures |
| H-5 | Multi-PC hydration: accept `characters:` list (with backwards-compat for legacy single-`character:` shape) | 3 | Party fixtures (multiplayer combat, party social dynamics) |

**Total backlog cost:** 18 points, 5 stories.

### Wave 2 fixture batches (post-extension)

Once H-N lands, author the corresponding fixture batch:

- **After H-1 (known_facts):** `journal_mixed_confidence_caverns.yaml` — PC carries 6 KnownFacts spanning all four confidence tiers; tests Journal UI rendering and accusation evaluator weight lookup
- **After H-2 (scenario_state):** `mystery_mid_tea.yaml` — tea_and_murder scenario with 50% of clue graph discovered, 1 NPC accused (low confidence), gossip mid-cascade; `mystery_redherring_tea.yaml` — clue graph state where the obvious suspect is innocent
- **After H-3 (encounter):** `combat_pretier_low.yaml` / `_mid.yaml` / `_high.yaml` — pre-armed encounter at each calibration band, pairs with ADR-093
- **After H-4 (magic):** `magic_active_elemental.yaml` — elemental harmony PC mid-ritual; `magic_drained_elemental.yaml` — magic_state at empty pool
- **After H-5 (multi-PC):** `party_combat_caverns.yaml` — 4-PC party vs. mixed force; `party_social_tea.yaml` — 3-PC party in tea_and_murder social scene

## Out of Scope

- Hydrator extension implementation (separate stories)
- Tropes mid-state (`active_tropes` not hydrated; defer; could file H-6 if needed)
- Companions, rigs, axis_values fixtures (defer until needed)
- Re-architecting the hydrator (e.g. subdirectory support) — flat directory is fine for Wave 1 scale; revisit at >30 fixtures
- Fixture-driven CI (running fixtures in test suite as smoke checks) — appealing later but not Wave 1

## Open Questions

None blocking. The triage of `negotiation.yaml` and `poker.yaml` (port vs delete) is a judgment call — defaulting to port since the content is already well-shaped.

## Implementation Notes

- Fixture YAMLs live in `scenarios/fixtures/` (orchestrator root)
- `scripts/playtest.py --fixture NAME` requires `DEV_SCENES=1` set when launching the server (per ADR-092)
- Each fixture should include a header comment with the URL form: `# Usage: http://localhost:5173/?scene=NAME (requires DEV_SCENES=1)`
- New fixtures should set `turn: 3` or higher so the dispatcher doesn't think it's turn 1 (per existing combat_test convention)
- Keep `description:` field on each fixture for self-documentation (existing convention)

## Effort Estimate

- Wave 1 fixture authoring: ~9 net-new fixtures × 10 min + 4 ports × 15 min ≈ 2.5 hours wall-clock (one GM session, including smoke-test verification per fixture against a running server). Per the "AI-driven hours / 10" calibration, this is realistic for a single session.
- Wave 2 hydrator stories: 18 points across 5 stories, each follows TDD workflow → variable wall-clock per story.
