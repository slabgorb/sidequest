# Playtest Cookbook — How to Test X

Quick-reference for testing specific game mechanics, subsystems, and scenarios.

## Headed vs. Headless — Pick Your Mode

SideQuest has two distinct playtest modes that test different things:

### Headless (Python driver — `scripts/playtest.py`)

**What it is:** A Python WebSocket client that connects directly to the server, sends player actions programmatically, and logs responses to the terminal. No browser, no UI, no daemon needed.

**What it tests:** Game loop, narrator quality, OTEL subsystem engagement, confrontation mechanics, state mutations, cost projection. Everything server-side.

**What it can't test:** UI rendering, React components, audio playback, image display, WebSocket reconnection, CSS/layout, client-side state mirror.

**When to use it:**
- Testing narrator behavior against a specific scenario
- Verifying OTEL spans fire for a subsystem
- Cost-checking a scenario before running it in the UI
- Regression testing after a server change
- CI-style automated checks

```bash
# Prerequisites: just the server
just server

# Run a scenario (chargen + scripted actions)
just playtest-scenario smoke_test

# Run a fixture (skip chargen, land in a scene)
just playtest --fixture combat_brawl_wasteland

# With OTEL span capture to Jaeger
just up-traced    # server + Jaeger
just playtest --scenario scenarios/combat_otel.yaml --span-jsonl /tmp/spans.jsonl

# Cost projection only (no actual run)
just playtest-scenario combat_stress
# → prints projected cost, refuses if > $0.50 (bypass with --confirm-cost)
```

**Key flags:**
| Flag | Purpose |
|------|---------|
| `--scenario PATH` | Run a YAML scenario (chargen + actions) |
| `--fixture NAME` | Load an ADR-092 fixture (skip chargen) |
| `--fresh` | Force a new COLD session (cache-bust). Default REUSES the same-day slug so the 1h prompt cache stays warm across runs (ADR-101) — reuse resumes the existing character (chargen skipped) |
| `--span-jsonl PATH` | Capture OTEL spans to JSONL via Jaeger |
| `--seed INT` | Deterministic dice rolls |
| `--max-projected-cost-usd N` | Cost cap (default $0.50) |
| `--confirm-cost` | Bypass cost cap |
| `--idle-timeout SECS` | WebSocket inactivity threshold (default 60s) |

### Full-Stack (UI + Playwright — `/sq-playtest`)

**What it is:** A Playwright-driven headed browser session against the full stack (server + UI + daemon). An agent drives gameplay through the actual React UI, takes screenshots, and coordinates bug fixes with a second workspace via a ping-pong file.

**What it tests:** The complete player experience — UI rendering, audio, images, WebSocket behavior, client-side state, layout, accessibility, and narrator quality all at once.

**What it can't test:** Nothing — it's the real thing. But it's slow, expensive (every turn costs an LLM call), and requires all services running.

**When to use it:**
- End-to-end validation before a release
- Testing UI changes (new components, layout, theme)
- Visual QA on narration cards, dice overlays, party panel
- Multiplayer testing (multiple Playwright tabs)
- UX review with a tandem UX Designer agent

```bash
# Prerequisites: full stack
just up   # server + client + daemon

# Launch via skill (in Claude Code)
/sq-playtest                    # full-stack mode (default)
/sq-playtest headless           # headless mode (falls back to Python driver)
```

**Full-stack architecture (two workspaces):**
```
OQ-2 (playtest driver)              OQ-1 (fix team)
├─ Playwright browser               ├─ Dev agent
├─ UX Designer agent                ├─ Architect agent
├─ SM coordinates                   ├─ SM coordinates
└─ Writes to pingpong.md ──────────→└─ Reads from pingpong.md
   (bugs, screenshots)                  (fixes, restarts)
```

**Ping-pong protocol:**
- OQ-2 adds `[BUG]`, `[BUG-LOW]`, `[UX]`, `[GAP]` entries with repro steps + screenshots
- OQ-1 picks them up: `open → in-progress → fixed`
- OQ-2 verifies: `fixed → verified`
- Neither side deletes entries — status transitions only
- Blocking bugs get an `ATTENTION` signal at the top of the file
- File lives at `~/Projects/sq-playtest-pingpong.md`

**Multiplayer in full-stack:** Open multiple Playwright tabs to `player1.local:5173`, `player2.local:5173`, etc. (`/etc/hosts` maps these to `127.0.0.1` for per-origin cookie isolation per ADR-036.)

### Decision Matrix

| Question | Headless | Full-Stack |
|----------|----------|------------|
| "Does the narrator handle combat correctly?" | **Yes** | Yes but slow |
| "Do OTEL spans fire for trope engine?" | **Yes** | Possible but noisy |
| "Does the dice overlay render?" | No | **Yes** |
| "Is the narration card layout broken?" | No | **Yes** |
| "Does multiplayer turn barrier work?" | Partially (WS only) | **Yes** (visual) |
| "What does this scenario cost?" | **Yes** (preflight) | No cost projection |
| "Is the audio wired?" | No | **Yes** |
| "Can I regression-test 10 scenarios fast?" | **Yes** | No |

## Prerequisites

```bash
# Headless only — just the server
just server

# Full-stack — everything
just up

# Full-stack with OTEL
just up-traced
just otel          # Dashboard at http://localhost:9765
# Jaeger UI at http://localhost:16686
```

## Three Ways to Load a Test

### 1. Fixtures (scene harness) — Drop into a pre-built scene

Open in browser: `http://localhost:5173/?scene=<fixture_name>`

Or headless: `just playtest --fixture <fixture_name>`

Fixtures skip chargen entirely. You land mid-game with a character, NPCs, inventory, and location already set. They live in `scenarios/fixtures/`. Works in both headed and headless modes.

### 2. Scenarios — Script a sequence of player actions

`just playtest-scenario <name>`

Scenarios run chargen (strategy: auto) then execute a list of player actions in order. They live in `scenarios/`. Headless only (the Python driver sends the actions).

### 3. Interactive (browser) — Play manually

Navigate to `http://localhost:5173`, pick a genre/world, create a character, and play. This is what `/sq-playtest` automates with Playwright. Full-stack only.

## How to Test: Combat

### Melee brawl (mutant_wasteland)
```bash
# Browser — lands you in a hostile encounter with Rust Jaw
http://localhost:5173/?scene=combat_brawl_wasteland

# Headless
just playtest --fixture combat_brawl_wasteland
```
- **Fixture:** Skar (Beastkin, lvl 1, Sharpened Rebar) vs. Rust Jaw
- **What to verify:** Confrontation spans fire, dice rolls resolve, HP changes emit state_patch, Edge/Composure mechanics engage
- **OTEL spans:** `confrontation.*`, `state_patch` (HP delta), `narrator.turn`

### Dungeon combat — three tiers (caverns_and_claudes)
```bash
# Low: Fighter vs. lone Wight in a collapsed guard post
http://localhost:5173/?scene=combat_caverns_low

# Mid: Fighter vs. two Ghouls in a flooded passage
http://localhost:5173/?scene=combat_caverns_mid

# High: Fighter vs. Wight Lord + two Shadows in a defiled shrine
http://localhost:5173/?scene=combat_caverns_high
```
- **What to verify:** Difficulty scaling feels right, beat selection varies by tier, death saves if HP hits 0
- **Classes available:** Fighter, Mage, Cleric, Thief (edit `char_class` in fixture to test each)

### Dogfight — space combat (space_opera)
```bash
http://localhost:5173/?scene=combat_dogfight_space
```
- **Fixture:** Nyx Corvane (Pilot, Snubfighter) vs. hostile snubfighter on a contested lane
- **What to verify:** Dogfight subsystem (ADR-077), maneuver/thrust mechanics, vehicle-scale resolution
- **OTEL spans:** `confrontation.dogfight.*`

### Ship boarding (space_opera)
```bash
http://localhost:5173/?scene=combat_boarding_space
```

## How to Test: Social Encounters

### Drawing room interrogation (tea_and_murder)
```bash
http://localhost:5173/?scene=social_drawing_room_tea
```
- **Fixture:** Mrs. Halloran (Investigator) in a Glenross drawing room with 4 NPCs at varying dispositions (+30 to -25)
- **What to verify:** NPC disposition shifts, OCEAN personality, dialogue variety, clue discovery
- **OTEL spans:** `npc_registry`, `state_patch` (disposition)

### Negotiation (tea_and_murder)
```bash
http://localhost:5173/?scene=social_negotiation_tea
```

### Poker game (mutant_wasteland)
```bash
http://localhost:5173/?scene=social_poker_wasteland
```

### Tavern crowd (caverns_and_claudes / beneath_sunden)
```bash
http://localhost:5173/?scene=social_tavern_caverns
```
- **Fixture:** Ersi (Rogue) at the kept fire in Ropefoot with 3 NPCs — the winch-keeper, a retired delver, and a newcomer
- **What to verify:** Social staging when tension is ambient, NPC voice differentiation

### Veteran social drop (caverns_and_claudes / beneath_sunden)
```bash
http://localhost:5173/?scene=social_veteran_drop_caverns
```
- **Fixture:** High-level delver at Ropefoot with knowledge to trade — tests narrator pacing with a powerful PC and quiet stakes

## How to Test: Merchant / Economy

```bash
http://localhost:5173/?scene=merchant_bazaar_wasteland
```
- **What to verify:** Inventory mutations, gold transactions, item pricing, narrative weight on items
- **OTEL spans:** `inventory_mutation` (items added/removed with source)

## How to Test: Class Abilities

Edit a fixture's `char_class` and `abilities` fields, then load it. Or create a new fixture.

### Template: Testing a specific class ability
```yaml
# scenarios/fixtures/ability_test_<class>.yaml
name: Ability Test — <Class Name>
genre: <genre>
world: <world>
player_name: fixture-ability-test
location: <somewhere appropriate>
turn: 1

character:
  name: Test Character
  char_class: <class_id from classes.yaml>
  level: 3
  hp: 20
  max_hp: 20
  narrative_state: Ready to use abilities
  hooks:
    - A situation that invites using the target ability

npcs:
  - name: Target NPC
    role: <hostile or neutral depending on ability>
    disposition: <set to provoke the ability>
```

### Available classes by genre:
- **caverns_and_claudes:** Fighter (Taunt), Mage, Cleric, Thief
- **tea_and_murder:** Investigator, Doctor, Clergy, Retired Officer
- **road_warrior:** check `road_warrior/classes.yaml`
- **Other genres:** Use `archetypes.yaml` — archetype = class equivalent

### Testing a specific ability:
1. Copy an existing fixture for that genre
2. Set `char_class` to the target class
3. Set `narrative_state` and `hooks` to create a situation where the ability is relevant
4. Add NPCs/encounter block as needed
5. Load fixture in browser, then type a player action that should trigger the ability
6. Check OTEL: did the confrontation/ability spans fire, or did the narrator improvise?

## How to Test: Exploration / Navigation

### Scripted walkthrough
```yaml
# scenarios/explore_<world>.yaml
name: Exploration — <World>
genre: <genre>
world: <world>
character:
  strategy: auto
actions:
  - "look around"
  - "go to the <adjacent region>"
  - "examine the <landmark>"
  - "search the area"
  - "head back to where I came from"
```

### What to verify:
- `state_patch` with location changes
- Room graph navigation (ADR-055) if wired for that genre
- Location descriptions match cartography.yaml content

## How to Test: Multiplayer

```bash
# Start server
just server

# Open two browser tabs to the same genre/world
# Both connect to the same game slug
```

- **What to verify:** Turn barrier (ADR-036 sealed rounds), peer action visibility, party-wide XP, no fast-typist monopoly
- **OTEL spans:** `multiplayer.*`, `turn_barrier.*`

## How to Test: Persistence / Save-Load

Sessions persist to PostgreSQL (ADR-115). No local `.db` files — the session lives in the `sessions` table, keyed by slug.

1. Play a few turns in any scenario
2. Stop the server (`Ctrl-C`)
3. Restart the server (`just server`) and reconnect — the default reuses the same-day slug, so do **not** pass `--fresh`
4. Verify state restored correctly (inventory, HP, location, NPC dispositions)

```bash
# Reconnect to existing slug (reuse is the default; --fresh would mint a new session)
just playtest --genre mutant_wasteland
```

## How to Test: Narration Quality (SOUL Compliance)

This is manual GM-eye review. For any fixture or scenario:

1. Play through several turns
2. Check each narrator response against SOUL principles:
   - **Agency:** Did the narrator describe the player doing something they didn't ask?
   - **Living World:** Do NPCs act on their own goals?
   - **Genre Truth:** Do consequences match the genre's tone?
   - **Diamonds and Coal:** Is detail proportional to importance?
   - **The Test:** If the response includes the player acting, it's wrong
3. Cross-reference with OTEL: are subsystems actually firing, or is the narrator improvising?

## How to Test: OTEL Subsystem Engagement

The GM panel is the lie detector. If a subsystem isn't emitting spans, the narrator is winging it.

```bash
# Start with full telemetry
just up-traced

# Run any fixture or scenario
# Open Jaeger: http://localhost:16686
# Search service: sidequest-server
```

### Key spans to watch:
| Span | Subsystem | "Missing" means |
|------|-----------|-----------------|
| `confrontation.*` | Combat/social engine | Narrator improvising combat |
| `state_patch` | Game state mutations | HP/location/inventory not tracked |
| `inventory_mutation` | Item tracking | Items appearing/disappearing without record |
| `trope_engine` | Trope progression | Tropes not ticking (ADR-087 dark) |
| `npc_registry` | NPC management | NPCs not properly registered |
| `narrator.turn` | Narration pipeline | Narration not going through proper pipeline |
| `magic.*` | Magic system | Magic not mechanically resolved |

## Writing New Fixtures

### Fixture Schema
```yaml
name: <Display name>
genre: <genre_pack_slug>
world: <world_slug>
player_name: <fixture-prefix>
description: <one-line context for the GM>
location: <starting location name>
turn: 3                                        # skip early-game awkwardness

character:
  name: <character name>
  description: <physical/personality sketch>
  personality: <one-line personality>
  level: <1-10>
  hp: <current>
  max_hp: <maximum>
  ac: <armor class>                            # optional, genre-dependent
  char_class: <class_id from classes.yaml>
  race: <race>
  pronouns: <they/them, she/her, he/him>
  stats:                                       # genre-specific stat block
    STR: 14
    DEX: 11
    # ...
  inventory:
    items:
      - id: <slug>
        name: <display name>
        description: <one line>
        category: <weapon|armor|tool|misc|consumable|light>
        value: <gold value>
        weight: <pounds>
        rarity: <common|uncommon|rare|legendary>
        narrative_weight: <0.0-1.0>            # Diamonds and Coal signal
        tags: [<tag>, ...]
        equipped: <true|false>
        quantity: <n>
    gold: <starting gold>
  statuses: []
  backstory: <1-2 sentences>
  narrative_state: <what the character is doing right now>
  hooks:
    - <something the narrator should notice/introduce>

npcs:
  - name: <NPC name>
    role: <role description>
    disposition: <-50 to +50>

encounter:                                     # optional — forces immediate encounter
  type: combat                                 # combat | social | chase
```

### Tips:
- Set `turn: 3` so the narrator treats this as mid-session, not cold-open
- `hooks` are the narrator's cue — make them specific and actionable
- `narrative_state` tells the narrator what the player is already doing
- `disposition` range: -50 (mortal enemy) to +50 (devoted ally)
- Match `stats` keys to the genre's stat system (STR/DEX/CON for caverns, Brawn/Instinct/Presence for wasteland)

## Quick Reference

| I want to test... | Command |
|-------------------|---------|
| Basic game loop | `just playtest-scenario smoke_test` |
| Melee combat | `?scene=combat_brawl_wasteland` |
| Dungeon combat (low) | `?scene=combat_caverns_low` |
| Dungeon combat (mid) | `?scene=combat_caverns_mid` |
| Dungeon combat (high) | `?scene=combat_caverns_high` |
| Space dogfight | `?scene=combat_dogfight_space` |
| Ship boarding | `?scene=combat_boarding_space` |
| Social / interrogation | `?scene=social_drawing_room_tea` |
| Negotiation | `?scene=social_negotiation_tea` |
| Poker / card game | `?scene=social_poker_wasteland` |
| Tavern crowd | `?scene=social_tavern_caverns` |
| Veteran social | `?scene=social_veteran_drop_caverns` |
| Merchant / economy | `?scene=merchant_bazaar_wasteland` |
| Specific class ability | Create fixture (see template above) |
| Exploration | Write scenario with movement actions |
| Multiplayer | Two browser tabs, same slug |
| OTEL verification | `just up-traced` + Jaeger |
| Cost projection | `just playtest-scenario smoke_test` (shows projected cost) |
| Stress test | `just playtest-scenario combat_stress` |

## Feature Coverage Audit Checklist

Run through this after any significant server change to verify nothing regressed. Tick each row when exercised; note the span or UI signal that confirmed it.

| System | Span / Signal | Notes |
|--------|---------------|-------|
| WebSocket connection | ConnectScreen shows "connected" | |
| Character creation | `chargen.*` spans | |
| Intent classification | `intent_router.*` spans (state-override, no LLM) | |
| Unified narrator (ADR-067) | `narrator.turn` span | |
| Auxiliary subsystems | `chassis_voice`, `distinctive_detail`, `npc_agency`, `reflect_absence` spans | |
| State patching + projection filter | `state_patch` events in watcher | |
| Confrontation engine (ADR-033 Pillars 1+2) | `confrontation.*` spans | |
| HP / ablative HP (ADR-114) | `player_hp`/`opponent_hp` in UI; `state_patch` HP delta | |
| Trope engine | `trope_engine` spans (engine dark — ADR-087 P1) | Verify data ticks even if beats don't fire |
| Image generation (Z-Image MLX) | `IMAGE` message in watcher | |
| Music (mood-based library playback) | `AUDIO_CUE` message; crossfade on beat change | |
| Audio mixing (music + SFX, 2-channel) | AudioStatus panel; SFX on combat | TTS retired ADR-076 |
| Slash commands (server + client routes) | `/character`, `/inventory`, `/map`, etc. respond | |
| Map overlay | SVG overlay loads; location highlight updates | |
| Inventory (within state_delta) | `/inventory` panel shows items | |
| Character sheet | `/character` panel; stat grid renders | |
| Journal / KnowledgeJournal | `/journal` panel; handout thumbnails | |
| Multiplayer (2+ players) | Turn barrier holds; peer actions visible | |
| GM Mode / Watcher / Dashboard tabs | Event stream live; trope timeline; snapshot inspector | |
| PostgreSQL persistence (ADR-115) | Reconnect restores session; no `.db` file in `~/.sidequest/saves/` | |
| Genre theming (CSS — ADR-079) | Genre-specific palette applies | |
| Beat filter | Low-drama actions suppress image render | |
| 3D dice (inline tray) | `InlineDiceTray` renders; physics active | ADR-075 |
| Magic system (WWN/SWN/CWN pluggable) | `magic.*` spans fire for spell actions | |
| Orbital chart (ADR-094) | Orrery renders for space_opera / coyote_star | |

---

## Gaps — Fixtures We Don't Have Yet

These would be valuable to add (gated on Wave 2 hydrator stories):

- **Chase scene** — no chase fixture exists (road_warrior or tea_and_murder)
- **Magic/channeling** — no dedicated magic fixture (caverns mage or elemental_harmony channeler). Blocked on H-4 (magic_state hydration).
- **Class ability gauntlet** — per-class fixture for each genre exercising the signature ability. Blocked on H-4.
- **Pre-armed encounter** — fixture that drops you into an active StructuredEncounter mid-beat. Blocked on H-3.
- **Mystery mid-investigation** — fixture with clue graph partially discovered. Blocked on H-2 (scenario_state hydration).
- **Multiplayer party** — 4-PC fixture. Blocked on H-5 (multi-PC hydration).
- **Advancement / level-up** — fixture at XP threshold to test progression
- **Item discovery** — fixture with searchable environment to test inventory pipeline
