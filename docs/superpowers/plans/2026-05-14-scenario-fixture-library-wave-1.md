# Scenario Fixture Library — Wave 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fill out `scenarios/fixtures/` with 12 reachable-today fixtures (8 net-new + 1 rename + 3 ports) so devs can teleport into specific game states for fast iteration. File 5 hydrator-extension stories that gate Wave 2.

**Architecture:** Pure YAML authoring under `scenarios/fixtures/`. Each fixture is one file consumed by `hydrate_fixture` (`sidequest-server/sidequest/game/scene_harness.py`). Verification per fixture is `POST /dev/scene/{name}` returns `200` with a `slug`, plus an OTEL `scene_harness.hydrate.ok` span. No code changes — Wave 2 hydrator extensions are filed as separate dev stories.

**Tech Stack:** YAML, the SideQuest scene harness (ADR-092), `python scripts/playtest.py --fixture NAME`, and `curl` against the running server (port 8765).

---

## Pre-flight

The plan assumes the SideQuest stack is running with `DEV_SCENES=1`. All verification commands are run from the orchestrator root (`/Users/slabgorb/Projects/oq-2`).

### Task 0: Confirm scene harness is live

**Files:** none (verification only)

- [ ] **Step 1: Start the server with DEV_SCENES enabled**

If `just up` is already running, restart with the env var. From the orchestrator root:

```bash
just down
DEV_SCENES=1 just up
```

Expected: server tails to `/tmp/sidequest-server.log`, no startup errors.

- [ ] **Step 2: Confirm the dev route is registered**

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8765/dev/scene/__nonexistent__
```

Expected: `404` (route exists, fixture doesn't). If you get `404` with `{"detail":"Not Found"}` (FastAPI's default rather than the harness's structured 404), `DEV_SCENES=1` was not set when `create_app()` ran — restart.

- [ ] **Step 3: Confirm an existing fixture loads**

```bash
curl -s -X POST http://localhost:8765/dev/scene/combat_test | python -m json.tool
```

Expected: `{"slug": "..."}` and a new save under `~/.sidequest/saves/`.

- [ ] **Step 4: Confirm playtest CLI honours --fixture**

```bash
python scripts/playtest.py --fixture combat_test --turns 1 2>&1 | tail -20
```

Expected: no stack trace, the script runs one narrator turn against the hydrated state. (If this errors out on grounds unrelated to the fixture, file a bug — do not proceed.)

---

## Phase 1: Triage existing fixtures

Three of the four existing fixtures point at workshopping worlds (verified in spec audit). Triage first so the directory doesn't carry broken artifacts into Wave 1.

### Task 1: Rename `combat_test.yaml` → `combat_brawl_wasteland.yaml`

**Files:**
- Modify (rename): `scenarios/fixtures/combat_test.yaml` → `scenarios/fixtures/combat_brawl_wasteland.yaml`

`combat_test` is the only existing fixture with a live world (`mutant_wasteland/flickering_reach`). Just rename for naming consistency; content stays.

- [ ] **Step 1: Git-mv the file**

```bash
git mv scenarios/fixtures/combat_test.yaml scenarios/fixtures/combat_brawl_wasteland.yaml
```

- [ ] **Step 2: Update the in-file usage comment**

Edit `scenarios/fixtures/combat_brawl_wasteland.yaml`. The first two lines should now read:

```yaml
# Combat fixture — drops directly into a Wasteland Brawl encounter.
# Usage: http://localhost:5173/?scene=combat_brawl_wasteland (requires DEV_SCENES=1)
```

- [ ] **Step 3: Verify the new name hydrates**

```bash
curl -s -X POST http://localhost:8765/dev/scene/combat_brawl_wasteland | python -m json.tool
```

Expected: `{"slug": "..."}`.

- [ ] **Step 4: Verify the old name is gone (no fallback)**

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8765/dev/scene/combat_test
```

Expected: `404`.

- [ ] **Step 5: Commit**

```bash
git add scenarios/fixtures/combat_brawl_wasteland.yaml
git commit -m "fixture(scene-harness): rename combat_test → combat_brawl_wasteland"
```

### Task 2: Port `dogfight.yaml` → `combat_dogfight_space.yaml` (aureate_span → coyote_star)

**Files:**
- Create: `scenarios/fixtures/combat_dogfight_space.yaml`
- Delete: `scenarios/fixtures/dogfight.yaml`

`dogfight.yaml` targets `space_opera/aureate_span`, which lives in `genre_workshopping/`. The active space_opera world is `coyote_star`. Port content + retarget. Reframe Nyx Corvane and the intercept lane to coyote_star geography (a "contested approach lane" near a coyote_star body).

- [ ] **Step 1: Read the original for content reuse**

```bash
cat scenarios/fixtures/dogfight.yaml
```

- [ ] **Step 2: Create the ported fixture**

Write `scenarios/fixtures/combat_dogfight_space.yaml`:

```yaml
# Dogfight fixture — drops into a contested-lane intercept above a coyote_star body.
# Usage: http://localhost:5173/?scene=combat_dogfight_space (requires DEV_SCENES=1)

name: Dogfight — Coyote Intercept
genre: space_opera
world: coyote_star
player_name: fixture-dogfight
description: Two-ship intercept on a contested lane above a coyote_star body. Maneuver, thrust, and nerves.
location: Contested Approach Lane
turn: 3

character:
  name: Nyx Corvane
  description: A former Colonial strike-wing pilot turned freelance escort.
  personality: Clipped, professional, visibly uncomfortable with small talk.
  level: 3
  hp: 14
  max_hp: 18
  inventory:
    items:
      - id: snubfighter-controls
        name: Snubfighter Yoke
        description: A worn flight yoke with custom thumb-triggers
        category: tool
        value: 0
        weight: 0.0
        rarity: common
        narrative_weight: 0.4
        tags: [pilot, vehicle]
        equipped: true
        quantity: 1
    gold: 0
  statuses: []
  backstory: Mustered out after the Coyote Wars; now flies escort for cargo runners who can't afford a proper wing.
  narrative_state: Closing on a hostile contact in a contested lane
  hooks:
    - The contact is squawking a recognised Colonial transponder
  char_class: Pilot
  race: Human
  pronouns: she/her
  stats:
    Brawn: 10
    Instinct: 14
    Presence: 11
    Reflexes: 15
    Toughness: 11
    Wits: 13

npcs:
  - name: Hostile Snubfighter
    role: hostile pilot
    disposition: -25
```

- [ ] **Step 3: Delete the original**

```bash
git rm scenarios/fixtures/dogfight.yaml
```

- [ ] **Step 4: Verify the new fixture hydrates**

```bash
curl -s -X POST http://localhost:8765/dev/scene/combat_dogfight_space | python -m json.tool
```

Expected: `{"slug": "..."}`.

- [ ] **Step 5: Verify the old name returns 404**

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8765/dev/scene/dogfight
```

Expected: `404`.

- [ ] **Step 6: Commit**

```bash
git add scenarios/fixtures/combat_dogfight_space.yaml scenarios/fixtures/dogfight.yaml
git commit -m "fixture(scene-harness): port dogfight to coyote_star (combat_dogfight_space)"
```

### Task 3: Port `negotiation.yaml` → `social_negotiation_tea.yaml` (annees_folles → glenross)

**Files:**
- Create: `scenarios/fixtures/social_negotiation_tea.yaml`
- Delete: `scenarios/fixtures/negotiation.yaml`

The original is a backroom-meeting setup — port the *shape* (closed-door social pressure, one tense NPC) to `tea_and_murder/glenross`. Reframe Halloran/Moretti as a tea-and-murder backroom: an investigator (Mrs. Halloran) confronting a suspect (Mr. Moreton, a Glenross merchant) in a private parlour.

- [ ] **Step 1: Create the ported fixture**

Write `scenarios/fixtures/social_negotiation_tea.yaml`:

```yaml
# Social fixture — closed-door negotiation in a Glenross parlour.
# Usage: http://localhost:5173/?scene=social_negotiation_tea (requires DEV_SCENES=1)

name: Negotiation — Parlour Sit-Down
genre: tea_and_murder
world: glenross
player_name: fixture-negotiation
description: A closed-door sit-down with Mr. Cornelius Moreton, Glenross merchant. One wrong word ends it.
location: Private Parlour, Moreton Residence
turn: 3

character:
  name: Mrs. Halloran
  description: A weary lady investigator with a reputation for reading a room.
  personality: Cynical, patient, and harder to rattle than she looks.
  level: 3
  hp: 14
  max_hp: 14
  inventory:
    items:
      - id: leather-notebook
        name: Leather Notebook
        description: Half-filled with shorthand observations
        category: tool
        value: 1
        weight: 0.4
        rarity: common
        narrative_weight: 0.5
        tags: [investigator]
        equipped: true
        quantity: 1
    gold: 12
  statuses: []
  backstory: Widowed early; took up private inquiries to keep the household afloat. The Moreton case is her third this season.
  narrative_state: Seated across from a man who would rather she were elsewhere
  hooks:
    - Moreton's account doesn't match the housekeeper's
  char_class: Investigator
  race: Human
  pronouns: she/her
  stats:
    Brawn: 9
    Instinct: 14
    Presence: 13
    Reflexes: 11
    Toughness: 11
    Wits: 15

npcs:
  - name: Cornelius Moreton
    role: tense merchant under suspicion
    disposition: -10
```

- [ ] **Step 2: Delete the original**

```bash
git rm scenarios/fixtures/negotiation.yaml
```

- [ ] **Step 3: Verify hydration**

```bash
curl -s -X POST http://localhost:8765/dev/scene/social_negotiation_tea | python -m json.tool
```

Expected: `{"slug": "..."}`.

- [ ] **Step 4: Commit**

```bash
git add scenarios/fixtures/social_negotiation_tea.yaml scenarios/fixtures/negotiation.yaml
git commit -m "fixture(scene-harness): port negotiation to tea_and_murder/glenross (social_negotiation_tea)"
```

### Task 4: Port `poker.yaml` → `social_poker_wasteland.yaml` (dust_and_lead → flickering_reach)

**Files:**
- Create: `scenarios/fixtures/social_poker_wasteland.yaml`
- Delete: `scenarios/fixtures/poker.yaml`

The original is a high-stakes card-table scene — port to `mutant_wasteland/flickering_reach`. Reframe "Black Bart" as "Brand", a wasteland card-table heavy.

- [ ] **Step 1: Create the ported fixture**

Write `scenarios/fixtures/social_poker_wasteland.yaml`:

```yaml
# Social fixture — high-stakes card table in a wasteland watering hole.
# Usage: http://localhost:5173/?scene=social_poker_wasteland (requires DEV_SCENES=1)

name: Cards — High Stakes
genre: mutant_wasteland
world: flickering_reach
player_name: fixture-poker
description: Four-hand card game with Brand. Grit vs cunning across a scarred plastic table.
location: The Slag Bar back room
turn: 3

character:
  name: Vask
  description: A wiry scavver with a tell only she knows about.
  personality: Quiet, calculating, slow to bet but ruthless when she does.
  level: 3
  hp: 14
  max_hp: 16
  inventory:
    items:
      - id: chip-stack
        name: Chit Stack
        description: Bottle-cap chits, three colours
        category: misc
        value: 80
        weight: 1.0
        rarity: common
        narrative_weight: 0.4
        tags: [gambling]
        equipped: false
        quantity: 1
      - id: hidden-blade
        name: Sleeve Blade
        description: Just in case the table turns
        category: weapon
        value: 6
        weight: 0.5
        rarity: common
        narrative_weight: 0.5
        tags: [concealed, melee]
        equipped: true
        quantity: 1
    gold: 80
  statuses: []
  backstory: Grew up running cards in a salvager camp; outlasted three of her old crew at this very table.
  narrative_state: Sitting down for the first hand of a long night
  hooks:
    - Brand has been watching her hands, not her eyes
  char_class: Scavenger
  race: Human
  pronouns: she/her
  stats:
    Brawn: 11
    Instinct: 13
    Presence: 12
    Reflexes: 14
    Toughness: 12
    Wits: 14

npcs:
  - name: Brand
    role: dangerous card-table heavy
    disposition: -20
  - name: Quiet Mel
    role: indifferent card player
    disposition: 0
  - name: Old Soot
    role: friendly drunk regular
    disposition: 15
```

- [ ] **Step 2: Delete the original**

```bash
git rm scenarios/fixtures/poker.yaml
```

- [ ] **Step 3: Verify hydration**

```bash
curl -s -X POST http://localhost:8765/dev/scene/social_poker_wasteland | python -m json.tool
```

Expected: `{"slug": "..."}`.

- [ ] **Step 4: Commit**

```bash
git add scenarios/fixtures/social_poker_wasteland.yaml scenarios/fixtures/poker.yaml
git commit -m "fixture(scene-harness): port poker to mutant_wasteland/flickering_reach (social_poker_wasteland)"
```

---

## Phase 2: Combat tier scaling (caverns_and_claudes/caverns_sunden)

Same archetype across three fixtures, varying only difficulty. Used today for narrator-behavior-at-Edge testing; once H-3 lands (encounter hydration), pairs with ADR-093 difficulty calibration.

### Task 5: `combat_low_caverns.yaml` — baseline combat math

**Files:**
- Create: `scenarios/fixtures/combat_low_caverns.yaml`

Lvl 1 PC at full Edge (10/10) vs 1 weak goblin. Tests narrator behavior on first hit, EdgePool initialization, baseline confrontation.

- [ ] **Step 1: Write the fixture**

Write `scenarios/fixtures/combat_low_caverns.yaml`:

```yaml
# Combat fixture — low tier baseline. Lvl 1 PC vs 1 weak hostile.
# Usage: http://localhost:5173/?scene=combat_low_caverns (requires DEV_SCENES=1)

name: Combat — Low Tier Baseline
genre: caverns_and_claudes
world: caverns_sunden
player_name: fixture-combat-low
description: A solitary goblin in the entrance tunnel. Test the floor of the combat math.
location: The Entrance Tunnel
turn: 3

character:
  name: Wren
  description: A nervous first-delve scout, lantern shaking in one hand.
  personality: Curious, jumpy, asks too many questions.
  level: 1
  hp: 10
  max_hp: 10
  inventory:
    items:
      - id: short-sword
        name: Short Sword
        description: A serviceable iron blade
        category: weapon
        value: 10
        weight: 2.0
        rarity: common
        narrative_weight: 0.4
        tags: [melee, slashing]
        equipped: true
        quantity: 1
      - id: lantern
        name: Hooded Lantern
        description: Half-full of oil
        category: tool
        value: 5
        weight: 1.5
        rarity: common
        narrative_weight: 0.3
        tags: [light]
        equipped: true
        quantity: 1
    gold: 8
  statuses: []
  backstory: Just signed on with a small delving company. This is her first job.
  narrative_state: Crouched at the tunnel mouth, one hostile in sight
  hooks:
    - The goblin hasn't spotted her yet
  char_class: Scout
  race: Human
  pronouns: she/her
  stats:
    Brawn: 10
    Instinct: 12
    Presence: 9
    Reflexes: 13
    Toughness: 11
    Wits: 12

npcs:
  - name: Stub-tooth Goblin
    role: weak hostile
    disposition: -10
```

- [ ] **Step 2: Verify hydration**

```bash
curl -s -X POST http://localhost:8765/dev/scene/combat_low_caverns | python -m json.tool
```

Expected: `{"slug": "..."}`.

- [ ] **Step 3: Verify a narrator turn fires combat OTEL**

Read the OTEL log to confirm `confrontation.*` spans appear after the next narrator turn:

```bash
python scripts/playtest.py --fixture combat_low_caverns --turns 1 2>&1 | grep -E "confrontation|hydrate" | head
```

Expected: at least one `scene_harness.hydrate.ok` line with `npc_count=1`. (`confrontation.*` may or may not fire on turn 1 depending on the narrator's read; absent is acceptable on this fixture.)

- [ ] **Step 4: Commit**

```bash
git add scenarios/fixtures/combat_low_caverns.yaml
git commit -m "fixture(scene-harness): combat_low_caverns — Lvl 1 baseline combat"
```

### Task 6: `combat_mid_caverns.yaml` — mid-tier party-vs-many feel

**Files:**
- Create: `scenarios/fixtures/combat_mid_caverns.yaml`

Lvl 3 PC at mid Edge (12/16) vs 3 mixed enemies (disposition −15..−25). Tests party-vs-many narrator framing and how the narrator sequences multiple hostiles.

- [ ] **Step 1: Write the fixture**

Write `scenarios/fixtures/combat_mid_caverns.yaml`:

```yaml
# Combat fixture — mid tier. Lvl 3 PC vs 3 mixed hostiles.
# Usage: http://localhost:5173/?scene=combat_mid_caverns (requires DEV_SCENES=1)

name: Combat — Mid Tier Skirmish
genre: caverns_and_claudes
world: caverns_sunden
player_name: fixture-combat-mid
description: An ambush in a fungal gallery. Three hostiles closing from the dark.
location: The Fungal Gallery
turn: 3

character:
  name: Wren
  description: A delve-scout with two seasons under her belt and a lantern that has seen better days.
  personality: Quieter than she used to be. Watches the floor more than the ceiling.
  level: 3
  hp: 12
  max_hp: 16
  inventory:
    items:
      - id: short-sword
        name: Short Sword
        description: A serviceable iron blade, nicked from use
        category: weapon
        value: 10
        weight: 2.0
        rarity: common
        narrative_weight: 0.5
        tags: [melee, slashing]
        equipped: true
        quantity: 1
      - id: hand-crossbow
        name: Hand Crossbow
        description: Three quarrels in the side-loop
        category: weapon
        value: 25
        weight: 2.0
        rarity: uncommon
        narrative_weight: 0.6
        tags: [ranged]
        equipped: true
        quantity: 1
    gold: 30
  statuses: []
  backstory: Two delves in. Lost a partner in the second.
  narrative_state: Pressed against a stalagmite, three contacts in the gallery
  hooks:
    - One contact is bigger than the others — a hobgoblin, maybe
  char_class: Scout
  race: Human
  pronouns: she/her
  stats:
    Brawn: 11
    Instinct: 13
    Presence: 10
    Reflexes: 14
    Toughness: 12
    Wits: 13

npcs:
  - name: Goblin Skirmisher
    role: light hostile
    disposition: -15
  - name: Goblin Bowman
    role: ranged hostile
    disposition: -20
  - name: Hobgoblin Sergeant
    role: hostile leader
    disposition: -25
```

- [ ] **Step 2: Verify hydration**

```bash
curl -s -X POST http://localhost:8765/dev/scene/combat_mid_caverns | python -m json.tool
```

Expected: `{"slug": "..."}`.

- [ ] **Step 3: Smoke-test one narrator turn**

```bash
python scripts/playtest.py --fixture combat_mid_caverns --turns 1 2>&1 | tail -10
```

Expected: completes without exception.

- [ ] **Step 4: Commit**

```bash
git add scenarios/fixtures/combat_mid_caverns.yaml
git commit -m "fixture(scene-harness): combat_mid_caverns — Lvl 3 party-vs-many skirmish"
```

### Task 7: `combat_high_caverns.yaml` — high tier + composure threshold

**Files:**
- Create: `scenarios/fixtures/combat_high_caverns.yaml`

Lvl 5 PC near bottom of Edge (4/20) vs 4 enemies + champion. Tests narrator behavior near composure threshold (per ADR-078 Edge / composure combat).

- [ ] **Step 1: Write the fixture**

Write `scenarios/fixtures/combat_high_caverns.yaml`:

```yaml
# Combat fixture — high tier. Lvl 5 PC at low Edge vs 4 hostiles + champion.
# Usage: http://localhost:5173/?scene=combat_high_caverns (requires DEV_SCENES=1)

name: Combat — High Tier Crucible
genre: caverns_and_claudes
world: caverns_sunden
player_name: fixture-combat-high
description: A delve gone bad. Edge nearly out, four hostiles closing, and the boss watching from a ledge.
location: The Black Antechamber
turn: 3

character:
  name: Wren
  description: A veteran scout, one delve from retirement, lantern long since shattered.
  personality: Tired. Patient in a way that worries her crewmates.
  level: 5
  hp: 4
  max_hp: 20
  inventory:
    items:
      - id: longsword-blooded
        name: Blooded Longsword
        description: A hilt rewrapped in something that used to be cloth
        category: weapon
        value: 50
        weight: 3.0
        rarity: uncommon
        narrative_weight: 0.7
        tags: [melee, slashing, signature]
        equipped: true
        quantity: 1
      - id: heater-shield
        name: Heater Shield
        description: Strapped to her left arm, dented past the boss
        category: armor
        value: 25
        weight: 5.0
        rarity: common
        narrative_weight: 0.5
        tags: [shield]
        equipped: true
        quantity: 1
      - id: healing-philtre
        name: Healing Philtre
        description: One dose left
        category: consumable
        value: 30
        weight: 0.2
        rarity: uncommon
        narrative_weight: 0.5
        tags: [healing]
        equipped: false
        quantity: 1
    gold: 80
  statuses: []
  backstory: Lost her crew in the upper galleries; came down alone to finish what they started.
  narrative_state: Bleeding, breathing hard, four contacts in the chamber, one on the ledge
  hooks:
    - The champion has a mace she has seen before — on a body she stepped over an hour ago
  char_class: Fighter
  race: Human
  pronouns: she/her
  stats:
    Brawn: 14
    Instinct: 14
    Presence: 11
    Reflexes: 14
    Toughness: 14
    Wits: 13

npcs:
  - name: Bugbear Champion
    role: elite hostile leader
    disposition: -35
  - name: Bugbear Skirmisher
    role: hostile
    disposition: -25
  - name: Goblin Bowman A
    role: ranged hostile
    disposition: -20
  - name: Goblin Bowman B
    role: ranged hostile
    disposition: -20
  - name: Goblin Skirmisher
    role: light hostile
    disposition: -15
```

- [ ] **Step 2: Verify hydration**

```bash
curl -s -X POST http://localhost:8765/dev/scene/combat_high_caverns | python -m json.tool
```

Expected: `{"slug": "..."}`.

- [ ] **Step 3: Smoke-test one narrator turn**

```bash
python scripts/playtest.py --fixture combat_high_caverns --turns 1 2>&1 | tail -10
```

Expected: completes; narrator should reflect low Edge / hard pressure in tone.

- [ ] **Step 4: Commit**

```bash
git add scenarios/fixtures/combat_high_caverns.yaml
git commit -m "fixture(scene-harness): combat_high_caverns — Lvl 5 high-tier crucible at low Edge"
```

---

## Phase 3: Genre coverage — net-new combat per active pack

`combat_brawl_wasteland` is the rename from Task 1 and already covers wasteland; `combat_dogfight_space` is the port from Task 2 and covers space_opera. The remaining net-new is the boarding action below.

### Task 8: `combat_boarding_space.yaml` — ship boarding action

**Files:**
- Create: `scenarios/fixtures/combat_boarding_space.yaml`

Lvl 4 PC + 2 hostile crew, on the deck of a boarded vessel. Different feel from dogfight (close-quarters vs vehicle).

- [ ] **Step 1: Write the fixture**

Write `scenarios/fixtures/combat_boarding_space.yaml`:

```yaml
# Combat fixture — ship boarding action in coyote_star.
# Usage: http://localhost:5173/?scene=combat_boarding_space (requires DEV_SCENES=1)

name: Combat — Boarding Action
genre: space_opera
world: coyote_star
player_name: fixture-boarding
description: The cutter is alongside, the hatch is breached, and two hostile crew are between you and the bridge.
location: Hostile Cutter — Forward Corridor
turn: 3

character:
  name: Calder Vance
  description: A boarding-party petty officer with mag-soles and a stubby coil pistol.
  personality: Loud, decisive, impatient with hesitation.
  level: 4
  hp: 16
  max_hp: 20
  inventory:
    items:
      - id: coil-pistol
        name: Coil Pistol
        description: Six rounds in the magazine
        category: weapon
        value: 60
        weight: 1.5
        rarity: uncommon
        narrative_weight: 0.6
        tags: [ranged, energy]
        equipped: true
        quantity: 1
      - id: bulkhead-cutter
        name: Bulkhead Cutter
        description: A short plasma blade for hatches and necks
        category: weapon
        value: 90
        weight: 2.0
        rarity: uncommon
        narrative_weight: 0.6
        tags: [melee, energy, breach]
        equipped: true
        quantity: 1
      - id: vac-mask
        name: Vac Mask
        description: One hour of sealed atmo in a pinch
        category: tool
        value: 25
        weight: 0.5
        rarity: common
        narrative_weight: 0.5
        tags: [survival]
        equipped: true
        quantity: 1
    gold: 40
  statuses: []
  backstory: Three boardings under his belt. The fourth always feels wrong.
  narrative_state: Through the breach, two contacts at the next bulkhead
  hooks:
    - The corridor lights are flickering — someone is at the breakers
  char_class: Boarder
  race: Human
  pronouns: he/him
  stats:
    Brawn: 14
    Instinct: 12
    Presence: 12
    Reflexes: 14
    Toughness: 14
    Wits: 11

npcs:
  - name: Hostile Crewer A
    role: hostile spacer
    disposition: -25
  - name: Hostile Crewer B
    role: hostile spacer
    disposition: -25
```

- [ ] **Step 2: Verify hydration**

```bash
curl -s -X POST http://localhost:8765/dev/scene/combat_boarding_space | python -m json.tool
```

Expected: `{"slug": "..."}`.

- [ ] **Step 3: Commit**

```bash
git add scenarios/fixtures/combat_boarding_space.yaml
git commit -m "fixture(scene-harness): combat_boarding_space — Lvl 4 boarding action in coyote_star"
```

---

## Phase 4: Social setups (no scenario_state needed)

### Task 9: `social_drawing_room_tea.yaml` — Glenross drawing room with mixed disposition

**Files:**
- Create: `scenarios/fixtures/social_drawing_room_tea.yaml`

Exercises 50-2 social confrontation triggers (negotiation/social_duel/scandal). PC enters a drawing room with 4 NPCs at varying disposition (+30 / +10 / −5 / −25) — the spread should bait several confrontation paths.

- [ ] **Step 1: Write the fixture**

Write `scenarios/fixtures/social_drawing_room_tea.yaml`:

```yaml
# Social fixture — Glenross drawing room with mixed disposition.
# Usage: http://localhost:5173/?scene=social_drawing_room_tea (requires DEV_SCENES=1)

name: Social — Drawing Room
genre: tea_and_murder
world: glenross
player_name: fixture-drawing-room
description: A small Glenross drawing room. Tea is poured. Four guests, four temperaments, one investigator.
location: The Glenross Drawing Room
turn: 3

character:
  name: Mrs. Halloran
  description: A widow who turned an inheritance into a private investigative practice.
  personality: Patient, observant, allergic to small talk that goes nowhere.
  level: 3
  hp: 12
  max_hp: 14
  inventory:
    items:
      - id: leather-notebook
        name: Leather Notebook
        description: Half-filled with shorthand observations
        category: tool
        value: 1
        weight: 0.4
        rarity: common
        narrative_weight: 0.5
        tags: [investigator]
        equipped: true
        quantity: 1
      - id: pearl-earrings
        name: Pearl Earrings
        description: Inherited; worn for the look of the thing
        category: misc
        value: 40
        weight: 0.0
        rarity: uncommon
        narrative_weight: 0.4
        tags: [society]
        equipped: true
        quantity: 1
    gold: 30
  statuses: []
  backstory: Three quiet successes have made her a known quantity in Glenross society. Tonight is the fourth invitation.
  narrative_state: Settled into the wing-back chair, observing
  hooks:
    - Lady Ashe spent yesterday in the conservatory; tonight she is wearing gloves
  char_class: Investigator
  race: Human
  pronouns: she/her
  stats:
    Brawn: 9
    Instinct: 14
    Presence: 13
    Reflexes: 11
    Toughness: 11
    Wits: 15

npcs:
  - name: Lady Margaret Ashe
    role: warm hostess
    disposition: 30
  - name: Reverend Pell
    role: pleasant guest
    disposition: 10
  - name: Mr. Cornelius Moreton
    role: cool merchant guest
    disposition: -5
  - name: Captain Hawkins
    role: openly hostile retired officer
    disposition: -25
```

- [ ] **Step 2: Verify hydration**

```bash
curl -s -X POST http://localhost:8765/dev/scene/social_drawing_room_tea | python -m json.tool
```

Expected: `{"slug": "..."}` with `npc_count: 4` in the OTEL `scene_harness.hydrate.ok` span.

- [ ] **Step 3: Commit**

```bash
git add scenarios/fixtures/social_drawing_room_tea.yaml
git commit -m "fixture(scene-harness): social_drawing_room_tea — mixed-disposition Glenross drawing room"
```

### Task 10: `social_tavern_caverns.yaml` — mixed-disposition tavern crowd

**Files:**
- Create: `scenarios/fixtures/social_tavern_caverns.yaml`

Tests narrator's social staging when no NPC is overtly hostile. 5 NPCs at varying disposition, a working-tavern setting.

- [ ] **Step 1: Write the fixture**

Write `scenarios/fixtures/social_tavern_caverns.yaml`:

```yaml
# Social fixture — mixed-disposition tavern crowd in Caverns Sunden.
# Usage: http://localhost:5173/?scene=social_tavern_caverns (requires DEV_SCENES=1)

name: Social — The Brace and Pick
genre: caverns_and_claudes
world: caverns_sunden
player_name: fixture-tavern
description: A working tavern at second bell. Five regulars, one stranger at the door.
location: The Brace and Pick
turn: 3

character:
  name: Joran Vell
  description: A delver between contracts, looking for work and not finding it.
  personality: Easy company until pushed; quiet anger when the bill comes due.
  level: 3
  hp: 14
  max_hp: 16
  inventory:
    items:
      - id: pickaxe
        name: Delver's Pickaxe
        description: Honest tool, dishonest history
        category: weapon
        value: 12
        weight: 4.0
        rarity: common
        narrative_weight: 0.5
        tags: [melee, tool]
        equipped: true
        quantity: 1
      - id: copper-coin
        name: Copper Coin
        description: His last
        category: misc
        value: 1
        weight: 0.0
        rarity: common
        narrative_weight: 0.6
        tags: [token]
        equipped: false
        quantity: 1
    gold: 4
  statuses: []
  backstory: Hired off four expeditions in a row. Knows every face in the room and not all of them owe him good will.
  narrative_state: Standing at the bar, drink half-finished
  hooks:
    - The barkeep keeps glancing at the back booth
  char_class: Delver
  race: Human
  pronouns: he/him
  stats:
    Brawn: 13
    Instinct: 12
    Presence: 12
    Reflexes: 12
    Toughness: 13
    Wits: 12

npcs:
  - name: Mira the Barkeep
    role: friendly proprietor
    disposition: 20
  - name: Old Tarn
    role: regular drinker, indifferent
    disposition: 5
  - name: Pell the Banker
    role: cool moneylender
    disposition: -10
  - name: The Tinker
    role: loud regular with strong opinions
    disposition: 0
  - name: Stranger in the Booth
    role: watchful stranger
    disposition: -5
```

- [ ] **Step 2: Verify hydration**

```bash
curl -s -X POST http://localhost:8765/dev/scene/social_tavern_caverns | python -m json.tool
```

Expected: `{"slug": "..."}` with `npc_count: 5`.

- [ ] **Step 3: Commit**

```bash
git add scenarios/fixtures/social_tavern_caverns.yaml
git commit -m "fixture(scene-harness): social_tavern_caverns — mixed-disposition tavern crowd"
```

---

## Phase 5: Merchant + veteran drop

### Task 11: `merchant_bazaar_wasteland.yaml` — wasteland market scene

**Files:**
- Create: `scenarios/fixtures/merchant_bazaar_wasteland.yaml`

PC with 200 gold + 3 trade goods. Tests `inventory_mutation` OTEL on buy/sell. NPC merchant + 2 other shoppers for crowd texture.

- [ ] **Step 1: Write the fixture**

Write `scenarios/fixtures/merchant_bazaar_wasteland.yaml`:

```yaml
# Merchant fixture — wasteland bazaar with goods to trade.
# Usage: http://localhost:5173/?scene=merchant_bazaar_wasteland (requires DEV_SCENES=1)

name: Merchant — The Slag Market
genre: mutant_wasteland
world: flickering_reach
player_name: fixture-merchant
description: A wasteland market under tarp-shade. Three things to sell, gold in pocket, and a merchant who watches her hands.
location: The Slag Market
turn: 3

character:
  name: Krayle
  description: A scavenger in patched leathers carrying a bundle that clinks.
  personality: Friendly but never first to name a price.
  level: 3
  hp: 14
  max_hp: 14
  inventory:
    items:
      - id: pre-war-tin
        name: Pre-War Tin
        description: Sealed; rattles when shaken
        category: misc
        value: 60
        weight: 1.0
        rarity: uncommon
        narrative_weight: 0.5
        tags: [trade-good, salvage]
        equipped: false
        quantity: 1
      - id: med-vial
        name: Medical Vial
        description: Half-full of something amber
        category: consumable
        value: 35
        weight: 0.2
        rarity: uncommon
        narrative_weight: 0.5
        tags: [trade-good, healing]
        equipped: false
        quantity: 1
      - id: brass-fitting
        name: Brass Fitting
        description: Heavy, useful, not mine
        category: misc
        value: 25
        weight: 1.5
        rarity: common
        narrative_weight: 0.4
        tags: [trade-good, salvage]
        equipped: false
        quantity: 2
      - id: utility-knife
        name: Utility Knife
        description: Belted, mostly for show
        category: weapon
        value: 5
        weight: 0.5
        rarity: common
        narrative_weight: 0.3
        tags: [melee]
        equipped: true
        quantity: 1
    gold: 200
  statuses: []
  backstory: Half her year is spent on the road, half spent in markets like this.
  narrative_state: Bundle on the counter, waiting for the merchant's first offer
  hooks:
    - The fitting is recognisable — the merchant may know whose stall it came from
  char_class: Scavenger
  race: Human
  pronouns: she/her
  stats:
    Brawn: 12
    Instinct: 13
    Presence: 12
    Reflexes: 12
    Toughness: 12
    Wits: 13

npcs:
  - name: Goss the Trader
    role: shrewd merchant
    disposition: 5
  - name: Browsing Drifter
    role: indifferent shopper
    disposition: 0
  - name: Loud Buyer
    role: another customer haggling at the next stall
    disposition: 0
```

- [ ] **Step 2: Verify hydration**

```bash
curl -s -X POST http://localhost:8765/dev/scene/merchant_bazaar_wasteland | python -m json.tool
```

Expected: `{"slug": "..."}`.

- [ ] **Step 3: Commit**

```bash
git add scenarios/fixtures/merchant_bazaar_wasteland.yaml
git commit -m "fixture(scene-harness): merchant_bazaar_wasteland — PC with goods + gold in wasteland market"
```

### Task 12: `veteran_drop_caverns.yaml` — late-game PC, no immediate threat

**Files:**
- Create: `scenarios/fixtures/veteran_drop_caverns.yaml`

Lvl 7 PC, full kit, 3 friendly NPCs. Tests narrator behavior with a powerful PC and quiet stakes — does the narrator escalate appropriately or stall?

- [ ] **Step 1: Write the fixture**

Write `scenarios/fixtures/veteran_drop_caverns.yaml`:

```yaml
# Veteran-drop fixture — Lvl 7 PC, full kit, no immediate threat.
# Tests narrator pacing/escalation when stakes are quiet.
# Usage: http://localhost:5173/?scene=veteran_drop_caverns (requires DEV_SCENES=1)

name: Veteran Drop — A Quiet Hall
genre: caverns_and_claudes
world: caverns_sunden
player_name: fixture-veteran
description: A veteran delver, three friendly faces, no immediate threat. What does the narrator do?
location: The Hall of Quiet Lamps
turn: 3

character:
  name: Wren the Long-Veteran
  description: A delver of many seasons, scarred and slow to startle, still carrying the lantern.
  personality: Calm. Speaks rarely. Listens to the rock.
  level: 7
  hp: 28
  max_hp: 28
  inventory:
    items:
      - id: longsword-blooded
        name: Blooded Longsword
        description: A signature weapon, hilt rewrapped a dozen times
        category: weapon
        value: 60
        weight: 3.0
        rarity: rare
        narrative_weight: 0.8
        tags: [melee, slashing, signature]
        equipped: true
        quantity: 1
      - id: heater-shield-engraved
        name: Engraved Heater Shield
        description: Crew names down the inside of the boss
        category: armor
        value: 50
        weight: 5.0
        rarity: uncommon
        narrative_weight: 0.6
        tags: [shield, signature]
        equipped: true
        quantity: 1
      - id: lantern-veteran
        name: The Long Lantern
        description: The same lantern she has carried since her first delve
        category: tool
        value: 10
        weight: 1.5
        rarity: uncommon
        narrative_weight: 0.7
        tags: [light, signature]
        equipped: true
        quantity: 1
      - id: healing-philtre
        name: Healing Philtre
        description: Two doses
        category: consumable
        value: 30
        weight: 0.4
        rarity: uncommon
        narrative_weight: 0.4
        tags: [healing]
        equipped: false
        quantity: 2
      - id: signet-ring
        name: Crew Signet
        description: Brass, well-worn, not technically hers
        category: misc
        value: 5
        weight: 0.0
        rarity: uncommon
        narrative_weight: 0.5
        tags: [token]
        equipped: true
        quantity: 1
    gold: 320
  statuses: []
  backstory: She is older than most of the people who hire her. The crews she trained are running their own delves now.
  narrative_state: Standing in the hall, lantern down, no contacts in sight
  hooks:
    - One of the lamps in the hall is hers — left here years ago
  char_class: Fighter
  race: Human
  pronouns: she/her
  stats:
    Brawn: 15
    Instinct: 15
    Presence: 13
    Reflexes: 14
    Toughness: 15
    Wits: 14

npcs:
  - name: Elin Brace
    role: friendly fellow delver, owes her
    disposition: 35
  - name: Old Tarn
    role: friendly retired delver, knew her crew
    disposition: 25
  - name: Apprentice Pell
    role: friendly young delver, in awe
    disposition: 40
```

- [ ] **Step 2: Verify hydration**

```bash
curl -s -X POST http://localhost:8765/dev/scene/veteran_drop_caverns | python -m json.tool
```

Expected: `{"slug": "..."}`.

- [ ] **Step 3: Smoke-test one narrator turn**

```bash
python scripts/playtest.py --fixture veteran_drop_caverns --turns 1 2>&1 | tail -10
```

Expected: completes; narrator should not invent a hostile encounter on turn 1 (the SOUL test — Living World means the world doesn't pause, but it also shouldn't jump-scare a Lvl 7 PC for no reason).

- [ ] **Step 4: Commit**

```bash
git add scenarios/fixtures/veteran_drop_caverns.yaml
git commit -m "fixture(scene-harness): veteran_drop_caverns — Lvl 7 PC, quiet stakes, late-game pacing test"
```

---

## Phase 6: File Wave 2 hydrator extension stories

These are dev tasks (Python). The GM lane authors **only the story records** in the sprint backlog; implementation is a Dev (Major Charles Emerson Winchester III) handoff. Each story unlocks a follow-on fixture batch.

Use epic 50 (active, "Pingpong-archive triage and dropped-work cleanup") as the parent — the scope creep is mild and these stories are scene-harness follow-ons. Alternatively the GM may file under a new epic at ticketing time. Pick `--workflow tdd` for all five.

### Task 13: File hydrator extension stories in the backlog

**Files:**
- Modify: `sprint/epic-50.yaml` (via `pf sprint story add`)

- [ ] **Step 1: File H-1 (`Character.known_facts` hydration)**

```bash
pf sprint story add 50 \
  "Scene harness: hydrate Character.known_facts (ADR-092 follow-on)" \
  2 --type feature --priority p2 --workflow tdd --repos server
```

Expected: new story `50-19` (or next available) added to `sprint/epic-50.yaml` with `status: backlog`.

- [ ] **Step 2: Add description to H-1**

The `pf sprint story add` command does not accept `--description` inline — add the description by editing the new story entry in `sprint/epic-50.yaml`. Locate the story by ID and add a `description:` field:

```yaml
    description: |
      Extend hydrate_fixture (sidequest/game/scene_harness.py) to read
      `known_facts:` under the `character:` block and project to
      Character.known_facts. Each entry must validate as a KnownFact with
      confidence in Literal["Certain","Suspected","Rumored","Discovered"]
      (post-50-17 promotion). Unblocks the journal_mixed_confidence_caverns
      Wave 2 fixture. Test: load a fixture with 4 KnownFacts spanning all
      tiers; assert character.known_facts has the right confidence values
      and accusation evaluator weight lookup succeeds.
```

- [ ] **Step 3: File H-2 (`scenario_state` hydration)**

```bash
pf sprint story add 50 \
  "Scene harness: hydrate top-level scenario_state (ADR-092 follow-on)" \
  5 --type feature --priority p2 --workflow tdd --repos server
```

- [ ] **Step 4: Add description to H-2**

Add to the new story entry:

```yaml
    description: |
      Extend hydrate_fixture to read a top-level `scenario_state:` block
      and project to GameSnapshot.scenario_state (clue_graph,
      discovered_clues, npc_roles, guilty_npc, tension). Unblocks Wave 2
      mystery fixtures: mystery_mid_tea (50% clue graph discovered, 1
      accusation primed) and mystery_redherring_tea (obvious suspect is
      innocent). Tests epic-50 wiring (50-5/6/7/8) at fixture level.
      Schema reference: sidequest/game/scenario_state.py and
      sidequest/genre/models/scenario.py (ClueGraph, ClueNode).
```

- [ ] **Step 5: File H-3 (`encounter` hydration)**

```bash
pf sprint story add 50 \
  "Scene harness: hydrate StructuredEncounter (ADR-092 follow-on)" \
  3 --type feature --priority p2 --workflow tdd --repos server
```

- [ ] **Step 6: Add description to H-3**

Add to the new story entry:

```yaml
    description: |
      Extend hydrate_fixture to read a top-level `encounter:` block and
      project to GameSnapshot.encounter (StructuredEncounter, ADR-033).
      The combat_brawl_wasteland fixture (formerly combat_test) currently
      includes `encounter: type: combat` which is silently dropped — wire
      it through. Unblocks Wave 2 pre-armed combat fixtures
      (combat_pretier_low/mid/high) for ADR-093 confrontation difficulty
      calibration spot tests. Schema reference: ADR-033 confrontation
      engine + sidequest/game/encounter.py.
```

- [ ] **Step 7: File H-4 (`magic_state` + `Character.abilities` hydration)**

```bash
pf sprint story add 50 \
  "Scene harness: hydrate magic_state + Character.abilities (ADR-092 follow-on)" \
  5 --type feature --priority p2 --workflow tdd --repos server
```

- [ ] **Step 8: Add description to H-4**

Add to the new story entry:

```yaml
    description: |
      Extend hydrate_fixture to read top-level `magic_state:` block
      (project to GameSnapshot.magic_state, MagicState shape per
      sidequest/magic/) and `abilities:` under the `character:` block
      (project to Character.abilities). Unblocks Wave 2 magic fixtures:
      magic_active_elemental (mid-ritual), magic_drained_elemental
      (empty pool), and class-ability-active fixtures. Note: blocked on
      elemental_harmony having no live worlds — file a content story
      to land at least one elemental world before authoring those
      fixtures. Schema reference: ADR-095 (class mechanical surface)
      and ADR-014 (Diamonds and Coal — magic state is Diamond, must
      be hydrated faithfully).
```

- [ ] **Step 9: File H-5 (multi-PC hydration)**

```bash
pf sprint story add 50 \
  "Scene harness: hydrate multi-PC characters list (ADR-092 follow-on)" \
  3 --type feature --priority p2 --workflow tdd --repos server
```

- [ ] **Step 10: Add description to H-5**

Add to the new story entry:

```yaml
    description: |
      Extend hydrate_fixture to accept a top-level `characters:` list
      (each entry the existing single-character shape) and project to
      GameSnapshot.characters. Keep backwards-compat: legacy `character:`
      singular continues to work as `characters[0]`. Unblocks Wave 2
      party fixtures: party_combat_caverns (4-PC vs mixed force) and
      party_social_tea (3-PC drawing room). Multiplayer playtest is
      currently bottlenecked here — every MP smoke test starts with
      4 chargen sessions.
```

- [ ] **Step 11: Verify all 5 stories landed**

```bash
grep -E "id: 50-(19|20|21|22|23)" sprint/epic-50.yaml
```

Expected: 5 lines, IDs sequential from 50-19 (or wherever the counter is). If IDs differ from 50-19..50-23 (e.g., a story was added in another worktree), record the actual IDs.

- [ ] **Step 12: Commit the sprint YAML changes**

```bash
git add sprint/epic-50.yaml
git commit -m "sprint(50): file 5 scene-harness hydrator extension stories (ADR-092 follow-ons)

H-1: known_facts (2 pts)
H-2: scenario_state (5 pts)
H-3: StructuredEncounter (3 pts)
H-4: magic_state + abilities (5 pts)
H-5: multi-PC characters list (3 pts)

Total: 18 pts. Each unblocks a Wave 2 fixture batch per spec
docs/superpowers/specs/2026-05-14-scenario-fixture-library-wave-1-design.md."
```

---

## Phase 7: Final verification + handoff note

### Task 14: Sweep — confirm all 12 fixtures load

**Files:** none (verification only)

- [ ] **Step 1: Loop over all 12 fixtures**

```bash
for f in combat_brawl_wasteland combat_dogfight_space social_negotiation_tea social_poker_wasteland \
         combat_low_caverns combat_mid_caverns combat_high_caverns combat_boarding_space \
         social_drawing_room_tea social_tavern_caverns merchant_bazaar_wasteland veteran_drop_caverns; do
  code=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8765/dev/scene/$f)
  echo "$code  $f"
done
```

Expected: 12 lines, every code `200`.

- [ ] **Step 2: Loop over all 12 via the playtest CLI**

```bash
for f in combat_brawl_wasteland combat_dogfight_space social_negotiation_tea social_poker_wasteland \
         combat_low_caverns combat_mid_caverns combat_high_caverns combat_boarding_space \
         social_drawing_room_tea social_tavern_caverns merchant_bazaar_wasteland veteran_drop_caverns; do
  echo "=== $f ==="
  python scripts/playtest.py --fixture $f --turns 0 2>&1 | tail -3
done
```

Expected: each fixture boots without exception. (`--turns 0` exercises hydration without spending a Claude turn.)

- [ ] **Step 3: Confirm no orphan fixtures remain**

```bash
ls scenarios/fixtures/
```

Expected: 12 `.yaml` files (the four originals are gone), names matching the convention. The `fixtures` subdirectory is otherwise empty.

- [ ] **Step 4: No commit needed for verification**

If sweep is clean, no commit. If sweep finds breakage, fix the fixture and recommit per its phase task.

### Task 15: Handoff note in CHANGELOG

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Read the changelog header to match style**

```bash
head -30 CHANGELOG.md
```

- [ ] **Step 2: Add an entry under the current sprint's section**

Edit `CHANGELOG.md` and add (under the current Unreleased / Sprint 3 section, in the "Added" or "Changed" group following the project's existing convention):

```markdown
- Scene harness fixture library Wave 1 (12 fixtures): combat tier scaling
  (low/mid/high caverns), genre coverage (wasteland brawl, space dogfight,
  space boarding), social setups (tea drawing room, caverns tavern, tea
  negotiation, wasteland poker), merchant bazaar (wasteland), and a
  veteran-drop caverns scene. Replaces the four original fixtures
  (combat_test/dogfight/negotiation/poker), three of which targeted
  workshopping worlds. Spec: docs/superpowers/specs/2026-05-14-scenario-fixture-library-wave-1-design.md.
- Filed 5 scene-harness hydrator extension stories (Wave 2): known_facts,
  scenario_state, StructuredEncounter, magic_state + abilities, multi-PC
  characters list. 18 pts total.
```

- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): scene harness Wave 1 fixture library + Wave 2 stories filed"
```

---

## Notes for the executor

- **Trust the existing fixtures' shape.** The hydrator is permissive about extra fields (`extra: ignore` on `GameSnapshot`), so including fields like `encounter:` or `description:` does no harm even when the hydrator currently drops them. They become live when Wave 2 lands.
- **Verify hydration after every fixture.** A typo in a literal field name (`charcter:` instead of `character:`) will not error — the hydrator just skips it. The proof of life is the OTEL `scene_harness.hydrate.ok` span with the expected `character_count` / `npc_count`.
- **Names and locations are creative work.** The PC names, NPC names, locations, and backstories in this plan are the canonical first-pass. If the executor knows the live world lore better and prefers a substitution, that's fine — keep the mechanical state (level, hp/max_hp, inventory, NPC count + disposition) intact.
- **No test stubs, no dead code.** Per CLAUDE.md, do not commit a fixture that "almost works" with the intention of fixing it later. If it doesn't hydrate, fix it before committing.
- **Saves accumulate.** Every fixture load mints a fresh slug under `~/.sidequest/saves/`. After this plan completes, expect ~12+ scene-harness saves. Sweep with `ls ~/.sidequest/saves/` and prune fixture-prefixed saves manually if they pile up — they're safe to delete.
