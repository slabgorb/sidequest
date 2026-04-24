# Primetime World — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Author a new world `primetime` under the `caverns_and_claudes` genre pack that inverts the default grim-dungeon tone — a televised gameshow crawl at `comedy: 0.95`, Running Man spine, Last Starfighter summoning, mistaken-identity engine. Content-only; no code.

**Architecture:** Follow the existing `worlds/mawdeep/` structure exactly. Each YAML file mirrors its mawdeep counterpart in schema/shape but carries Primetime-specific content sourced from the spec at `docs/superpowers/specs/2026-04-24-primetime-world-design.md`. Commit per file for clean rollback and easy review. Portraits, music, and playtest scenarios are deferred to follow-up skills (`/sq-poi`, `/sq-music`, scenario authoring).

**Tech Stack:** YAML 1.2 (the only tech here). Schema validated by `pf hooks schema-validation` on each `Write`. End-to-end validation via server genre-pack load at the end.

**Spoiler Protection:** This plan references the spec as the content source; it does NOT quote the content. The spec file is the authoritative spoiler zone. The plan's executor reads the spec to author files. The user can skip reading this plan's individual content steps to preserve their surprise at the table.

---

## File Structure

The world lives at: `sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/`

| File | Responsibility | Schema template |
|---|---|---|
| `world.yaml` | World identity: name, description, tagline, axis_snapshot, keeper block | `worlds/mawdeep/world.yaml` |
| `lore.yaml` | Present-day setting — the Network, the Summoning Engine, how the show works | `worlds/mawdeep/lore.yaml` |
| `history.yaml` | Campaign-progression chapters (fresh/early/mid/veteran) with lore, POIs, atmosphere | `worlds/mawdeep/history.yaml` |
| `legends.yaml` | Discoverable lore shards (prior Hosts, Season Zero, the Wyrm Incident, the Audience Revolt) | `worlds/mawdeep/legends.yaml` |
| `factions.yaml` | 5 factions: Network, Stalkers, Stagehands, Fans, Unaired | `worlds/mawdeep/factions.yaml` |
| `creatures.yaml` | 8 named Stalkers + Stagehand crews + Fan swarms + Network Suits + Ad Spirits + Props | `worlds/mawdeep/creatures.yaml` |
| `rooms.yaml` | 8 POIs from spec, room-graph format with exits and tactical grids | `worlds/mawdeep/rooms.yaml` |
| `cartography.yaml` | Region/adjacency map — studio-adjacent topology | `worlds/mawdeep/cartography.yaml` |
| `encounter_tables.yaml` | Per-zone wandering encounters referencing creature IDs | `worlds/mawdeep/encounter_tables.yaml` |
| `pacing.yaml` | Ratings-aware escalation; commercial-break cadence | `worlds/mawdeep/pacing.yaml` |
| `tropes.yaml` | 8 signature tropes (Catchphrase Trigger, Audience Vote, etc.) | `worlds/mawdeep/tropes.yaml` |
| `openings.yaml` | Mundane-moment → summoning-flash opening variants | `worlds/mawdeep/openings.yaml` |
| `archetype_funnels.yaml` | Stage-title funnel overlay on genre archetypes | `worlds/mawdeep/archetype_funnels.yaml` |
| `archetypes.yaml` | World-specific NPC archetypes (the Host, PAs, Stalker proxies, Unaired contacts) | `worlds/mawdeep/archetypes.yaml` |
| `visual_style.yaml` | Flux prompt suffix: overlit studio TV look (distinct from mawdeep's ink-organic) | `worlds/mawdeep/visual_style.yaml` |
| `portrait_manifest.yaml` | Portrait scenes for the Host, 8 Stalkers, key Unaired, named PAs, Fan archetypes | `worlds/mawdeep/portrait_manifest.yaml` |
| `assets/` | Empty directory scaffold; images/audio deferred | `worlds/mawdeep/assets/` |

**Optional genre-level change:**
| File | Responsibility |
|---|---|
| `caverns_and_claudes/axes.yaml` | Add a `Primetime` preset at 0.95 / 0.5 / 0.6 under `presets:` |

---

## Execution Rules (applies to every task)

1. **Read the analog first.** Before authoring a Primetime file, read the corresponding `mawdeep/` file to lock the schema. Do not invent fields.
2. **Source content from the spec.** All content comes from `docs/superpowers/specs/2026-04-24-primetime-world-design.md`. Do not improvise setting material that isn't already there — if the spec is silent, add content consistent with the spec's premise and flag it in the commit message.
3. **One commit per file.** Atomic commits — easy to revert, easy to review. Commits go into the orchestrator repo? **NO.** Content lives in `sidequest-content/`, which is its own git repo. See "Repo note" below.
4. **Hook validates on Write.** `pf hooks schema-validation` runs automatically. If it fails, fix and re-write before committing.
5. **No code.** If any subsystem is missing, stop and flag it — do not patch server/daemon/UI.

**Repo note.** `sidequest-content/` is a separate git repository. All per-file commits happen in that repo. The spec stays in the orchestrator. The plan stays in the orchestrator. Only the YAML files land in `sidequest-content/`.

---

## Task 0: Prep & Directory Scaffold

**Files:**
- Create: `sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/` (directory)
- Create: `sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/assets/` (directory)

- [ ] **Step 1: Verify clean working tree in the content repo**

Run:
```bash
cd sidequest-content && git status && git log --oneline -3
```
Expected: clean tree; recent commits listed.

- [ ] **Step 2: Create the world directory and assets subdirectory**

Run:
```bash
mkdir -p sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/assets
```
Expected: no output (success). Verify:
```bash
ls sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/
```
Expected: `assets` listed.

- [ ] **Step 3: Confirm mawdeep is present as the schema template**

Run:
```bash
ls sidequest-content/genre_packs/caverns_and_claudes/worlds/mawdeep/
```
Expected: 16 files + `assets/` directory.

- [ ] **Step 4: Re-read the spec (executor)**

Open `docs/superpowers/specs/2026-04-24-primetime-world-design.md` in full. This is the authoritative content source for all subsequent tasks.

No commit for Task 0 — directory creation is staged by the first file commit.

---

## Task 1: `world.yaml` (foundation)

**Files:**
- Create: `sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/world.yaml`

- [ ] **Step 1: Read the schema template**

```bash
cat sidequest-content/genre_packs/caverns_and_claudes/worlds/mawdeep/world.yaml
```
Note these required fields: `cover_poi`, `name`, `description`, `tagline`, `axis_snapshot`, `keeper` (with `name`, `personality`, `obsession`, `tone_override`, `awareness`, `monologue_style`, `trap_aesthetic`, `topology_tendency`).

- [ ] **Step 2: Author `world.yaml`**

Content from spec sections:
- `name`: `Primetime`
- `tagline`: from spec — *"We asked for heroes. We got… you. Let's see if we can make it work."*
- `description`: 6–10 lines summarizing the Network / Summoning Engine / mistaken-identity premise from spec's "The premise" + "The setup" sections.
- `axis_snapshot`: `comedy: 0.95`, `gravity: 0.5`, `outlook: 0.6`.
- `cover_poi`: `the_summoning_stage` (matches the room id from Task 7).
- `keeper`:
  - `name`: `The Host` (open question in spec resolved in favor of no proper name).
  - `personality`: `warmly vicious`
  - `obsession`: `ratings and legacy`
  - `tone_override`: `comedy: 0.98`, `gravity: 0.4` (Host slightly lighter than world baseline).
  - `awareness`: tracks ratings, not stealth. Use mawdeep's shape with `starting: 0`, `tick_rate: 1`, thresholds keyed on viewership milestones (3/6/10/15/20 → boredom / sponsor-call / forced-ad / stalker-dispatch / finale-mode). Phrase each threshold as an in-world cue.
  - `monologue_style`: follow spec's "Monologue style" paragraph verbatim in essence (stage-voice, catchphrase economy).
  - `trap_aesthetic`: spec's "Trap aesthetic" paragraph — theatrical, spotlights, trapdoors, confetti cannons firing shrapnel, mock-wedding guillotines.
  - `topology_tendency`: spec's "Topology tendency" paragraph — studio-adjacent, wings, green rooms, commercial-break pocket dimensions, gift shop on every level.

- [ ] **Step 3: Verify YAML parses**

Run:
```bash
python -c "import yaml; yaml.safe_load(open('sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/world.yaml'))"
```
Expected: no output (success). If error, fix and re-run.

- [ ] **Step 4: Commit**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/worlds/primetime/world.yaml
git commit -m "$(cat <<'EOF'
world(primetime): add world.yaml — Host as Keeper, axes 0.95/0.5/0.6

Dungeon Crawler Claude world under caverns_and_claudes. Televised
gameshow crawl. The Host as Keeper — warmly vicious, ratings-obsessed,
with ratings-tracking awareness escalation. Studio-adjacent topology.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: `lore.yaml` (setting foundation)

**Files:**
- Create: `sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/lore.yaml`

- [ ] **Step 1: Read the schema template**

```bash
cat sidequest-content/genre_packs/caverns_and_claudes/worlds/mawdeep/lore.yaml
```
Schema: top-level keys include `overview`, one or more domain sections (`the_dungeon`, `gristwell`, etc.). Free-form but each block has a `nature`/`description`/`behavior` shape.

- [ ] **Step 2: Author `lore.yaml`**

Domains to cover (derive from spec):
- `overview`: 8–12 lines — what Primetime is, who watches, what the Summoning Engine does. Do NOT explain the broken-algorithm twist in overview (that's a discoverable). Overview is the Host's pitch.
- `the_network`: corporate entity — faceless, ancient, memo-based. Include `interaction_style` key noting HR-rep apparitions and NDAs-under-doors.
- `the_summoning_engine`: the mechanism — how it's supposed to work vs how it actually works. This is where the broken-algorithm truth is canonized as a lore fact (not surfaced until late-game discovery, but present in the file).
- `the_broadcast`: audience scope (14 billion worlds, mandatory viewership), ad tiers, ratings economics.
- `the_arena`: the studio-dungeon itself — its nature, its architecture, what resets between seasons and what doesn't.
- `the_gift_shop_economy`: currency (`PrimeBux`), merch-as-save, the gift shop on every level.

Keep prose Pratchett-sharp — satire is love with a harder edge. No cruelty-for-its-own-sake.

- [ ] **Step 3: Verify YAML parses**

Run:
```bash
python -c "import yaml; yaml.safe_load(open('sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/lore.yaml'))"
```
Expected: no output.

- [ ] **Step 4: Commit**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/worlds/primetime/lore.yaml
git commit -m "world(primetime): add lore.yaml — the Network, the Summoning Engine, the broadcast

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: `history.yaml` (campaign progression)

**Files:**
- Create: `sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/history.yaml`

- [ ] **Step 1: Read the schema template**

```bash
cat sidequest-content/genre_packs/caverns_and_claudes/worlds/mawdeep/history.yaml
```
Schema: top-level `chapters:` list. Each chapter has `id`, `label`, `session_range: [N, M]`, `lore: []`, `location`, `time_of_day`, `atmosphere`, `points_of_interest: []`.

- [ ] **Step 2: Author `history.yaml`**

4 chapters covering the maturity arc:
- `id: fresh`, range `[1, 3]`, `label: "Season Premiere"` — party just summoned, tutorial zone, the Promo is the threat, audience is intrigued.
- `id: early`, range `[4, 8]`, `label: "Building the Audience"` — mid-pack Stalkers appear, first Commercial Break, first Gift Shop.
- `id: mid`, range `[9, 15]`, `label: "Sweeps Week"` — serious Stalkers, Network attention, the party becomes a brand.
- `id: veteran`, range `[16, 25]`, `label: "The Season Finale"` — late-game Stalkers, Dressing Room reachable, bargain with the Host available.

Each chapter's `lore:` list has 3–5 entries establishing what has changed. `points_of_interest` lists the POIs that become relevant at that chapter.

- [ ] **Step 3: Verify YAML parses**

Run:
```bash
python -c "import yaml; yaml.safe_load(open('sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/history.yaml'))"
```

- [ ] **Step 4: Commit**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/worlds/primetime/history.yaml
git commit -m "world(primetime): add history.yaml — 4-chapter season progression

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: `legends.yaml` (discoverable shards)

**Files:**
- Create: `sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/legends.yaml`

- [ ] **Step 1: Read the schema template**

```bash
cat sidequest-content/genre_packs/caverns_and_claudes/worlds/mawdeep/legends.yaml
```
Schema: top-level list of objects with `name`, `summary`, `era`, `affected_cultures: []`, `cultural_impact`.

- [ ] **Step 2: Author `legends.yaml`**

Legends from spec's "Legends" section:
1. `The 42 Hosts Before This One` — summary with three specific one-line predecessor fates.
2. `Season Zero` — the pilot episode. No survivors. Network calls it a classic.
3. `The Wyrm Incident` — last time the Summoning Engine worked. She won. She's Unaired now.
4. `The Time the Audience Revolted` — three-episode arc edited out of history. Rumor only.
5. `The Sponsored Messiah` — a contestant who leaned so hard into their mistaken title they achieved it for real. Died at the peak of their popularity. Merch still sells.
6. `The Gift Shop Anomaly` — the gift shop once stocked a plushie of a contestant who hadn't been summoned yet. The Network swears it's a production error.

Use `affected_cultures` broadly: `[Galactic Audience]`, `[The Unaired]`, `[Network Employees]`, etc.

- [ ] **Step 3: Verify YAML parses**

Run:
```bash
python -c "import yaml; yaml.safe_load(open('sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/legends.yaml'))"
```

- [ ] **Step 4: Commit**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/worlds/primetime/legends.yaml
git commit -m "world(primetime): add legends.yaml — 6 discoverable shards

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: `factions.yaml` (5 factions)

**Files:**
- Create: `sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/factions.yaml`

- [ ] **Step 1: Read the schema template**

```bash
cat sidequest-content/genre_packs/caverns_and_claudes/worlds/mawdeep/factions.yaml
```
Schema: top-level `factions:` list. Each faction has `name`, `description`, `goal`, `urgency`, `scene_event`, `disposition_to_players`, `resources: []`, `key_npcs: []`.

Each `key_npc` has `name`, `role`, `description` (and optionally more).

- [ ] **Step 2: Author `factions.yaml`**

5 factions from spec:
1. `The Network` — faceless corporate. Interaction style: memos and HR reps. 2–3 key_npcs (the VP of Ratings, an HR rep with a clipboard, an anonymous memo-writer).
2. `The Stalkers` — the 8 celebrity monsters. `key_npcs` here are the 8 Stalker names as a faction roster (full creature stats live in `creatures.yaml`).
3. `The Stagehands` — unionized goblins/kobolds. Key NPCs: the shop steward, a trap-resetter, a lighting tech.
4. `The Fans` — superfan mobs. Key NPCs: a front-row regular, a superfan who's been to every season, a heckler.
5. `The Unaired` — resistance. Key NPCs: the Wyrm Incident survivor (from legends), a cancelled-show stagehand defector, a PA who went off-script and lived.

Dispositions:
- Network: `hostile` (administrative, not violent)
- Stalkers: `hostile`
- Stagehands: `neutral` (tippable)
- Fans: `variable` (see Fan Ambush trope)
- Unaired: `friendly` (wary)

- [ ] **Step 3: Verify YAML parses**

Run:
```bash
python -c "import yaml; yaml.safe_load(open('sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/factions.yaml'))"
```

- [ ] **Step 4: Commit**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/worlds/primetime/factions.yaml
git commit -m "world(primetime): add factions.yaml — Network, Stalkers, Stagehands, Fans, Unaired

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: `creatures.yaml` (8 Stalkers + minor classes)

**Files:**
- Create: `sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/creatures.yaml`

- [ ] **Step 1: Read the schema template**

```bash
cat sidequest-content/genre_packs/caverns_and_claudes/worlds/mawdeep/creatures.yaml
```
Schema: top-level `creatures:` list. Each creature has `id`, `name`, `description`, `threat_level` (1–10), `morale`, `hp`, `max_hp`, `ac`, `damage`, `abilities: []`, `loot: []`, `tags: []`, `rooms: []`, `notes`. Each ability has `name` + `description`.

- [ ] **Step 2: Author `creatures.yaml`**

**Stalkers (threat_level 4–9):**
Use IDs `promo`, `mother_in_law`, `sublime`, `buzzkill`, `dynamo`, `ad_breaks`, `legal_department`, `the_franchise` (ordered low-to-high threat).

For each Stalker, encode:
- `id`, `name` (all-caps stage name), `description` (spec's Stalker section).
- `abilities:` — one signature gimmick ability from spec, plus a secondary (entrance-music buff, sponsor-tie-in debuff, catchphrase reaction).
- `loot:` — a themed merchandise drop (a plushie, a signed headshot, a branded weapon prop).
- `tags:` — `[stalker, boss, celebrity]` plus a per-Stalker flavor tag.
- `rooms:` — list the POI slugs where each Stalker is encounterable (see Task 7 rooms).

Stat-budget hints (calibrate against mawdeep's creature bestiary):
- Promo: threat 3, hp 10, boss-lite
- Mother-in-Law, Sublime: threat 5
- Buzzkill, Dynamo, Ad Breaks: threat 6
- Legal Department: threat 7
- The Franchise: threat 9 (season-finale tier)

**Minor creature classes (threat_level 1–3):**
- `stagehand_crew` (threat 1, neutral) — default non-combatant, attacks only if provoked.
- `fan_swarm` (threat 2–3) — morale-based, triggered by Fan Ambush trope.
- `network_suit` (threat 4) — administrative apparition; signed-NDA weakness.
- `ad_spirit` (threat 2) — commercial-break minion.
- `prop` (threat 1–3, variable) — the-scenery-is-dangerous class; chandeliers, trapdoors-as-mouths.

- [ ] **Step 3: Verify YAML parses and every Stalker id matches the spec roster**

Run:
```bash
python -c "
import yaml
d = yaml.safe_load(open('sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/creatures.yaml'))
stalker_ids = {c['id'] for c in d['creatures'] if 'stalker' in c.get('tags', [])}
expected = {'promo','mother_in_law','sublime','buzzkill','dynamo','ad_breaks','legal_department','the_franchise'}
missing = expected - stalker_ids
extra = stalker_ids - expected
assert not missing, f'Missing Stalkers: {missing}'
assert not extra, f'Unexpected Stalkers: {extra}'
print('8 Stalkers present')
"
```
Expected: `8 Stalkers present`.

- [ ] **Step 4: Commit**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/worlds/primetime/creatures.yaml
git commit -m "world(primetime): add creatures.yaml — 8 Stalkers + Stagehands, Fans, Suits, Ad Spirits, Props

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: `rooms.yaml` (8 POIs)

**Files:**
- Create: `sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/rooms.yaml`

- [ ] **Step 1: Read the schema template**

```bash
cat sidequest-content/genre_packs/caverns_and_claudes/worlds/mawdeep/rooms.yaml
```
Schema: top-level list of rooms, each with `id`, `name`, `room_type`, `size: [W, H]`, `keeper_awareness_modifier`, `description`, `exits: []`, `tactical_scale` (use `4`), `grid` (ASCII map — optional for non-combat rooms).

- [ ] **Step 2: Author `rooms.yaml`**

The 8 POIs from spec (IDs in snake_case):
1. `the_summoning_stage` — entrance, cover_poi for world.yaml.
2. `the_green_room` — hub.
3. `the_audience_pit` — chorus room (unique: audience heard not seen).
4. `the_gift_shop` — merch + save point.
5. `the_commercial_break` — pocket-dimension encounter room.
6. `the_dressing_room` — late-game bargain location.
7. `the_control_booth` — endgame, Unaired-only access.
8. `the_soundstage_alley` — liminal between-sets hideout.

For each: `room_type` (`entrance`, `normal`, `hub`, `boss`, `secret`), `description` sourced from spec's POI section, `exits` cross-referencing other room IDs. Only author `grid` ASCII maps for rooms where combat is expected (Summoning Stage, Audience Pit, Commercial Break, Dressing Room). Others can omit `grid`.

`keeper_awareness_modifier`: tune per room — hub rooms (Green Room, Gift Shop, Soundstage Alley) get `0.5` (boring = ratings dip); spectacle rooms (Audience Pit, Commercial Break, Dressing Room) get `1.2` (high-visibility).

- [ ] **Step 3: Verify YAML parses and 8 rooms present**

Run:
```bash
python -c "
import yaml
d = yaml.safe_load(open('sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/rooms.yaml'))
assert len(d) == 8, f'Expected 8 rooms, got {len(d)}'
ids = {r['id'] for r in d}
expected = {'the_summoning_stage','the_green_room','the_audience_pit','the_gift_shop','the_commercial_break','the_dressing_room','the_control_booth','the_soundstage_alley'}
missing = expected - ids; extra = ids - expected
assert not missing and not extra, f'ID mismatch. Missing: {missing}, Extra: {extra}'
print('8 POIs present with expected IDs')
"
```
Expected: `8 POIs present with expected IDs`.

- [ ] **Step 4: Commit**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/worlds/primetime/rooms.yaml
git commit -m "world(primetime): add rooms.yaml — 8 studio-adjacent POIs

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: `cartography.yaml` (region/adjacency map)

**Files:**
- Create: `sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/cartography.yaml`

- [ ] **Step 1: Read the schema template**

```bash
cat sidequest-content/genre_packs/caverns_and_claudes/worlds/mawdeep/cartography.yaml
```
Schema: top-level `world_name`, `starting_region`, `navigation_mode` (use `room_graph`), then `regions:` as a dict keyed by region id. Each region has `name`, `summary`, `description`, `terrain`, `adjacent: []`, `landmarks: []`.

- [ ] **Step 2: Author `cartography.yaml`**

Single-region world map since the studio is one contiguous production complex:
- `starting_region`: `the_summoning_stage`.
- Mirror room IDs as region IDs; each region's `adjacent` cross-references room exits from Task 7.
- `terrain` values: `stage`, `backstage`, `audience`, `retail`, `pocket_dimension`, `executive`, `liminal`.
- Include 2–3 `landmarks` per region where relevant (e.g., the Summoning Stage has "the clipboard", "the podium", "the door that opens to the arena").

- [ ] **Step 3: Verify YAML parses and all referenced adjacencies exist**

Run:
```bash
python -c "
import yaml
d = yaml.safe_load(open('sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/cartography.yaml'))
regs = d['regions']
for rid, r in regs.items():
    for adj in r.get('adjacent', []):
        assert adj in regs, f'{rid} references unknown region {adj}'
print(f'{len(regs)} regions, all adjacencies resolve')
"
```

- [ ] **Step 4: Commit**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/worlds/primetime/cartography.yaml
git commit -m "world(primetime): add cartography.yaml — studio-adjacent region map

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: `encounter_tables.yaml` (per-zone wandering encounters)

**Files:**
- Create: `sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/encounter_tables.yaml`

- [ ] **Step 1: Read the schema template**

```bash
cat sidequest-content/genre_packs/caverns_and_claudes/worlds/mawdeep/encounter_tables.yaml
```
Schema: top-level `levels:` list. Each level has `id`, `name`, `wandering_monster_chance`, `wandering_monster_awareness_bonus`, `wandering_monsters: []`. Each monster entry has `creature_id`, `weight`, `count` (dice string), `description`, `loot: []`.

- [ ] **Step 2: Author `encounter_tables.yaml`**

Three "levels" (zones) mapped to room clusters:
- `level_1_stage` — encounters in Summoning Stage / Green Room / Audience Pit. Weighted toward Fan Swarms, Stagehands, Promo appearances.
- `level_2_arena` — encounters in Commercial Break / Gift Shop / Soundstage Alley. Weighted toward Ad Spirits, mid-tier Stalkers, Network Suits.
- `level_3_backstage` — encounters in Dressing Room / Control Booth. Weighted toward high-tier Stalkers, The Franchise, Network Suits.

Use `wandering_monster_chance: 0.15–0.20`. Use `creature_id` values matching Task 6. Each entry's `description` is one in-scene sentence the narrator can adapt.

- [ ] **Step 3: Verify YAML parses and every creature_id exists in creatures.yaml**

Run:
```bash
python -c "
import yaml
enc = yaml.safe_load(open('sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/encounter_tables.yaml'))
creatures = yaml.safe_load(open('sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/creatures.yaml'))
valid_ids = {c['id'] for c in creatures['creatures']}
for lvl in enc['levels']:
    for m in lvl['wandering_monsters']:
        assert m['creature_id'] in valid_ids, f'Unknown creature: {m[\"creature_id\"]}'
print(f'{len(enc[\"levels\"])} zones, all creature_ids resolve')
"
```

- [ ] **Step 4: Commit**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/worlds/primetime/encounter_tables.yaml
git commit -m "world(primetime): add encounter_tables.yaml — 3 zones with weighted encounters

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: `tropes.yaml` (8 signature tropes)

**Files:**
- Create: `sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/tropes.yaml`

- [ ] **Step 1: Read the schema template**

```bash
cat sidequest-content/genre_packs/caverns_and_claudes/worlds/mawdeep/tropes.yaml
```
Schema: top-level list of tropes, each with `id`, `name`, `description`, `category`, `triggers: []`, `narrative_hints: []`, `tension_level` (0.0–1.0), `resolution_hints: []`, `tags: []`, `escalation: []` (with `at` + `event` + `npcs_involved` + `stakes`), `passive_progression.rate_per_turn`.

- [ ] **Step 2: Author `tropes.yaml`**

8 tropes from spec:
1. `catchphrase_trigger` — Host deploys catchphrase; audience response buffs/debuffs. Triggers: Host-addressed scenes, milestones, party victories.
2. `audience_vote` — mid-scene poll, binding. Triggers: morally-ambiguous player choices, scenes where the party splits on a decision.
3. `sponsor_intervention` — sponsor "helps" with monkey's-paw. Triggers: party in visible trouble + sponsor hook is available.
4. `ratings_drought` — System cranks difficulty when session gets quiet. Triggers: 3+ consecutive low-tension turns.
5. `fan_ambush` — Fans rush stage. Triggers: spotlight moments, boss-fight openings, trending-up state.
6. `commercial_break` — pocket-dimension forced break. Triggers: Host-overridden, random cadence (every 7–12 scenes).
7. `product_placement` — sponsor mention in narration; engage-bonus / mock-penalty fork. Triggers: any scene involving consumption, choice of gear, shop interactions.
8. `mistaken_identity` — Host introduces a PC with inflated stage title; lean-in vs deny fork. Triggers: PC introductions, first appearances after summoning, applause moments.

Each trope's `triggers` list must use keyword strings the narrator will actually encounter in play. Include `tension_level` (0.2–0.7 range), 2–3 `escalation` entries each.

- [ ] **Step 3: Verify YAML parses and 8 tropes present**

Run:
```bash
python -c "
import yaml
d = yaml.safe_load(open('sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/tropes.yaml'))
assert len(d) == 8, f'Expected 8 tropes, got {len(d)}'
ids = {t['id'] for t in d}
expected = {'catchphrase_trigger','audience_vote','sponsor_intervention','ratings_drought','fan_ambush','commercial_break','product_placement','mistaken_identity'}
assert ids == expected, f'ID mismatch: missing {expected-ids}, extra {ids-expected}'
print('8 tropes present with expected IDs')
"
```

- [ ] **Step 4: Commit**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/worlds/primetime/tropes.yaml
git commit -m "world(primetime): add tropes.yaml — 8 signature gameshow-crawl tropes

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 11: `pacing.yaml` (ratings-aware escalation)

**Files:**
- Create: `sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/pacing.yaml`

- [ ] **Step 1: Read the schema template**

```bash
cat sidequest-content/genre_packs/caverns_and_claudes/worlds/mawdeep/pacing.yaml
```
Schema: top-level `sentence_delivery_min`, `streaming_delivery_min`, `escalation_streak`, then `levels:` — per-level pacing objects with `id`, `name`, `pacing_mode`, `beat_tempo`, `description`, `narrator_guidance`, `tension_range`, `resource_pressure`, `combat_frequency`, `exploration_weight`.

- [ ] **Step 2: Author `pacing.yaml`**

Mirror the 3 zones from Task 9 (level_1_stage, level_2_arena, level_3_backstage). Additionally encode the **commercial-break cadence** and **ratings-drought escalation** as pacing-level guidance:
- Act I (stage): `pacing_mode: spectacle`, `beat_tempo: fast`, tension `[0.3, 0.6]`. The Host is charming. The audience is primed.
- Act II (arena): `pacing_mode: escalating`, `beat_tempo: fast`, tension `[0.5, 0.8]`. Sweeps mode.
- Act III (backstage): `pacing_mode: revelatory`, `beat_tempo: variable`, tension `[0.4, 0.9]`. The mask slips.

Add a top-level `commercial_break_cadence: every 7-12 scenes` comment (YAML comment, not a schema field) for the trope/engine reference.

`narrator_guidance` is the key prose block — 6–10 lines per level instructing the narrator on tone, camera language ("cut to close-up", "the audience gasps"), and when to break the fourth wall.

- [ ] **Step 3: Verify YAML parses**

Run:
```bash
python -c "import yaml; yaml.safe_load(open('sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/pacing.yaml'))"
```

- [ ] **Step 4: Commit**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/worlds/primetime/pacing.yaml
git commit -m "world(primetime): add pacing.yaml — 3-act ratings-aware escalation

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 12: `openings.yaml` (session openers)

**Files:**
- Create: `sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/openings.yaml`

- [ ] **Step 1: Read the schema template**

```bash
cat sidequest-content/genre_packs/caverns_and_claudes/worlds/mawdeep/openings.yaml
```
Schema: top-level list of openings, each with `id`, `archetype`, `situation`, `tone`, `avoid: []`, `first_turn_seed`.

- [ ] **Step 2: Author `openings.yaml`**

5 opening variants:
1. `id: the_prescription` — mundane-moment → summoning flash. Spec's opening hook verbatim or close paraphrase.
2. `id: mid_shift` — delver was at work when summoned. Night-shift variant.
3. `id: the_argument` — delver was mid-argument with a manager. Unflattering title earned.
4. `id: the_picnic` — delver was having a perfectly nice day. Now they aren't.
5. `id: returning_contestant` — second-session opening; party wakes up in the Green Room, knows the score now.

Each opening's `avoid:` block rules out spoilers (no premature Host reveal, no early Stalker introduction). `first_turn_seed` is 5–10 lines of scene-setting prose the narrator uses verbatim as the opening beat.

- [ ] **Step 3: Verify YAML parses**

Run:
```bash
python -c "import yaml; d = yaml.safe_load(open('sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/openings.yaml')); assert len(d) == 5, f'Expected 5 openings, got {len(d)}'; print('5 openings present')"
```

- [ ] **Step 4: Commit**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/worlds/primetime/openings.yaml
git commit -m "world(primetime): add openings.yaml — 5 summoning-flash session openers

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 13: `archetype_funnels.yaml` (stage-title overlay)

**Files:**
- Create: `sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/archetype_funnels.yaml`

- [ ] **Step 1: Read the schema template**

```bash
cat sidequest-content/genre_packs/caverns_and_claudes/worlds/mawdeep/archetype_funnels.yaml
```
Schema: top-level `funnels:` list. Each funnel has `name`, `absorbs: [[archetype, role], ...]`, `faction` (or null), `lore`, `cultural_status`, `disposition_toward: {faction: relation}`.

- [ ] **Step 2: Author `archetype_funnels.yaml`**

6 funnels corresponding to stage-title categories from spec:
1. `Slayer of the Wyrm` — absorbs hero/tank, ruler/tank, everyman/tank. Faction: null. Mistaken-identity flavor: the algorithm confused one moment of proximity for heroism.
2. `Legendary of Fortune` — absorbs hero/dps, ruler/dps. Office temp, Secret Santa winner.
3. `Walker Between Worlds` — absorbs caregiver/support, everyman/support. Night-shift janitor, long-haul driver.
4. `Defier of Tyrants` — absorbs rebel/dps, jester/dps, outlaw/dps. Argued with a manager, filed a complaint.
5. `Silent Blade` — absorbs outlaw/tank, magician/dps. Actually a mime, a librarian, a dental hygienist.
6. `Witness to the Dark` — absorbs sage/support, magician/support. Saw a car accident once.

Each funnel's `lore` block: 4–6 lines canonizing the mistaken-identity narrative — who they really are, what the algorithm misread, how the Host spins it.

- [ ] **Step 3: Verify YAML parses and 6 funnels present**

Run:
```bash
python -c "
import yaml
d = yaml.safe_load(open('sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/archetype_funnels.yaml'))
assert len(d['funnels']) == 6, f'Expected 6 funnels, got {len(d[\"funnels\"])}'
print('6 stage-title funnels present')
"
```

- [ ] **Step 4: Commit**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/worlds/primetime/archetype_funnels.yaml
git commit -m "world(primetime): add archetype_funnels.yaml — 6 stage-title mistaken-identity overlays

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 14: `archetypes.yaml` (world-specific NPCs)

**Files:**
- Create: `sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/archetypes.yaml`

- [ ] **Step 1: Read the schema template**

```bash
cat sidequest-content/genre_packs/caverns_and_claudes/worlds/mawdeep/archetypes.yaml
```
Schema: top-level list of NPCs, each with `name`, `description`, `personality_traits: []`, `typical_classes: []`, `typical_races: []`, `stat_ranges: {}`, `catalog_items: []`, `inventory_hints: []`, `dialogue_quirks: []`, `disposition_default`, `ocean: {openness, conscientiousness, extraversion, agreeableness, neuroticism}`.

- [ ] **Step 2: Author `archetypes.yaml`**

6 named archetypes:
1. **The Host** — OCEAN: high extraversion (9), low neuroticism publicly but 6+ privately, high openness, agreeableness 4 (warmly vicious).
2. **The Stage PA** — low-level NPC with a clipboard. Always in a hurry.
3. **Network HR Rep** — apparition. Speaks in clauses. Low agreeableness.
4. **Fan in Row 3** — superfan archetype. High conscientiousness (merch collector).
5. **Shop Steward (Stagehands Union)** — union rep. High agreeableness, high conscientiousness.
6. **Unaired Contact** — resistance archetype. High openness, low extraversion, medium neuroticism.

Each NPC gets `disposition_default` aligned to their faction's disposition from Task 5.

- [ ] **Step 3: Verify YAML parses**

Run:
```bash
python -c "
import yaml
d = yaml.safe_load(open('sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/archetypes.yaml'))
assert len(d) >= 6, f'Expected 6+ archetypes, got {len(d)}'
names = {a['name'] for a in d}
assert 'The Host' in names, 'The Host archetype missing'
print(f'{len(d)} archetypes present including The Host')
"
```

- [ ] **Step 4: Commit**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/worlds/primetime/archetypes.yaml
git commit -m "world(primetime): add archetypes.yaml — Host + PA + HR + Fan + Steward + Unaired

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 15: `visual_style.yaml` (overlit studio palette)

**Files:**
- Create: `sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/visual_style.yaml`

- [ ] **Step 1: Read the schema template**

```bash
cat sidequest-content/genre_packs/caverns_and_claudes/worlds/mawdeep/visual_style.yaml
```
Schema: top-level keys `flux_prompt_suffix`, `portrait_style`, `creature_style`, `poi_style`. Each is a multi-line prompt-suffix string for Flux image generation.

- [ ] **Step 2: Author `visual_style.yaml`**

Intentionally **inverts** mawdeep's palette:
- Mawdeep is B&W pen-and-ink Otus/Trampier organic-horror.
- Primetime is **overlit TV studio color**: saturated primaries, harsh key lights, visible lighting rigs, 1980s-game-show-set aesthetic, slight lens flare, staged tableaux, obvious production design, cheap-but-shiny. Think *Press Your Luck* meets *The Running Man* meets *Squid Game* set photography.

Prompt keywords to include: `overlit studio lighting`, `saturated primary colors`, `visible lighting rigs`, `staged tableau`, `1980s game show aesthetic`, `harsh key light`, `studio audience silhouettes`, `slightly-too-shiny production design`, `spotlights`, `confetti`, `TV broadcast composition`.

Separate suffixes for `portrait_style` (press-kit-glam), `creature_style` (Stalker entrance-card aesthetic — headshot + signature weapon + sponsor logo), `poi_style` (game-show-set architecture — cyclorama walls, obvious seams, rigging visible from certain angles).

- [ ] **Step 3: Verify YAML parses and all 4 keys present**

Run:
```bash
python -c "
import yaml
d = yaml.safe_load(open('sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/visual_style.yaml'))
for k in ('flux_prompt_suffix','portrait_style','creature_style','poi_style'):
    assert k in d and d[k], f'Missing or empty: {k}'
print('4 style suffixes present')
"
```

- [ ] **Step 4: Commit**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/worlds/primetime/visual_style.yaml
git commit -m "world(primetime): add visual_style.yaml — overlit studio palette (inverts mawdeep)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 16: `portrait_manifest.yaml` (portrait scene specs)

**Files:**
- Create: `sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/portrait_manifest.yaml`

- [ ] **Step 1: Read the schema template**

```bash
cat sidequest-content/genre_packs/caverns_and_claudes/worlds/mawdeep/portrait_manifest.yaml
```
Schema: top-level `characters:` list. Each character has `name`, `role`, `type` (`npc_major`, `npc_minor`, `creature`, `boss`), `appearance`, `culture_aesthetic`.

- [ ] **Step 2: Author `portrait_manifest.yaml`**

Required portraits (scene-level specs, NOT generation — images are deferred to `/sq-poi`):

**Majors (bosses + the Host):**
- `The Host` — tailored jumpsuit, teeth-too-shiny, mid-catchphrase, spotlit.
- 8 Stalkers — each with their signature gimmick, entrance-card framing, sponsor logo visible somewhere.

**NPC-major:**
- The Shop Steward (Stagehands Union).
- The Wyrm Incident Survivor (Unaired leader).
- A named HR Rep.

**NPC-minor / archetype plates:**
- A Stage PA with clipboard.
- A Fan in Row 3.
- A Sponsored Beverage Table (environmental character — the set itself).

Each entry's `appearance` is 4–8 lines of Flux-ready prose describing the physical composition. `culture_aesthetic` is 2–4 lines on the Primetime production-design flavor (overlit, staged, shiny).

- [ ] **Step 3: Verify YAML parses and 12+ characters present**

Run:
```bash
python -c "
import yaml
d = yaml.safe_load(open('sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/portrait_manifest.yaml'))
chars = d['characters']
assert len(chars) >= 12, f'Expected 12+ portraits, got {len(chars)}'
host = [c for c in chars if c['name'] == 'The Host']
assert host, 'The Host portrait missing'
print(f'{len(chars)} portraits present including The Host')
"
```

- [ ] **Step 4: Commit**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/worlds/primetime/portrait_manifest.yaml
git commit -m "world(primetime): add portrait_manifest.yaml — Host, 8 Stalkers, Unaired, fans, PAs

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 17: Genre-level `axes.yaml` preset addition

**Files:**
- Modify: `sidequest-content/genre_packs/caverns_and_claudes/axes.yaml` (append to `presets:` list)

- [ ] **Step 1: Read the current axes.yaml**

```bash
cat sidequest-content/genre_packs/caverns_and_claudes/axes.yaml | tail -20
```
Note the existing presets: `Tomb of Horrors`, `Dungeon Crawl Classics`, `Classic B/X`.

- [ ] **Step 2: Append the `Primetime` preset**

Add to the `presets:` list:
```yaml
  - name: Primetime
    description: >-
      The televised gameshow crawl. Humor at 11, lethality deliberately
      dialed down, the dungeon is a broadcast studio and the Keeper is
      a captive MC. Absurd but winnable. For pick-me-up campaigns where
      the joke is the point and contestants get to go home.
    values:
      comedy: 0.95
      gravity: 0.5
      outlook: 0.6
```

- [ ] **Step 3: Verify YAML parses and 4 presets present**

Run:
```bash
python -c "
import yaml
d = yaml.safe_load(open('sidequest-content/genre_packs/caverns_and_claudes/axes.yaml'))
presets = d['presets']
names = {p['name'] for p in presets}
assert 'Primetime' in names, 'Primetime preset missing'
assert len(presets) == 4, f'Expected 4 presets, got {len(presets)}'
print(f'{len(presets)} presets: {sorted(names)}')
"
```

- [ ] **Step 4: Commit**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/axes.yaml
git commit -m "genre(caverns_and_claudes): add Primetime tone preset (0.95/0.5/0.6)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 18: End-to-End Load Validation

**Files:** none (read-only check)

- [ ] **Step 1: Confirm directory listing matches expected manifest**

Run:
```bash
ls sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime/
```
Expected: 16 `.yaml` files + `assets/` directory.

- [ ] **Step 2: Parse every world YAML to catch any lurking syntax errors**

Run:
```bash
python -c "
import yaml, os
wd = 'sidequest-content/genre_packs/caverns_and_claudes/worlds/primetime'
for f in sorted(os.listdir(wd)):
    if f.endswith('.yaml'):
        try:
            yaml.safe_load(open(os.path.join(wd, f)))
            print(f'OK  {f}')
        except Exception as e:
            print(f'ERR {f}: {e}')
            raise
print('all world YAMLs parse cleanly')
"
```
Expected: every file marked `OK`, final line `all world YAMLs parse cleanly`.

- [ ] **Step 3: Server genre-pack load smoke test**

Boot the server briefly in a one-shot mode (no full `just up` needed) and confirm the genre pack loads Primetime without errors.

Run (from orchestrator root):
```bash
cd sidequest-server && uv run python -c "
from sidequest.genre_pack.loader import load_genre_pack
import os
packs = os.environ.get('SIDEQUEST_GENRE_PACKS') or '../sidequest-content/genre_packs'
pack = load_genre_pack(os.path.join(packs, 'caverns_and_claudes'))
worlds = [w for w in pack.worlds if 'primetime' in w.id.lower() or 'primetime' in w.name.lower()]
assert worlds, f'Primetime world not found; loaded worlds: {[w.id for w in pack.worlds]}'
print(f'Primetime loaded: {worlds[0].name} ({worlds[0].id})')
"
```
Expected: a single-line `Primetime loaded: Primetime (primetime)` (exact module path may differ — if `sidequest.genre_pack.loader` does not exist, `grep -rn 'def load_genre_pack\|GenrePack(' sidequest/` to find the real symbol, then retry).

If the loader rejects a file, fix the flagged file, re-commit, and re-run.

- [ ] **Step 4: Check the content repo status is clean**

Run:
```bash
cd sidequest-content && git status
```
Expected: `nothing to commit, working tree clean`.

- [ ] **Step 5: Log summary**

Report to user:
- 16 world YAML files authored under `worlds/primetime/`
- 1 genre-level file modified (`axes.yaml` Primetime preset)
- N commits landed in `sidequest-content/`
- Load validation passed
- Deferred: portrait generation (`/sq-poi`), music tracks (`/sq-music`), smoke-test scenario (separate task)

No commit in this task — this is validation only.

---

## Self-Review (writing-plans skill — completed)

**1. Spec coverage:**
- ✅ All 16 files from manifest have a task.
- ✅ Optional genre-level `axes.yaml` preset has Task 17.
- ✅ "Out of scope" items (portraits, music, scenarios, code, LoRA) are not tasked — correctly deferred.
- ✅ Success criteria #1 (loadable world) covered by Task 18.
- ✅ Success criteria #3 (Stalker distinctness) enforced by Task 6's 8-Stalker validation.
- ✅ Success criteria #5 (mistaken-identity system) covered by Task 13 funnels.

**2. Placeholder scan:** No `TBD`/`TODO`. Steps that reference the spec do so because spoiler-protection demands it; the spec is the content source-of-truth and is complete. Executor has actionable files + schema + structural guidance at every step.

**3. Type consistency:**
- Room IDs referenced in Task 6 (Stalker `rooms:`), Task 8 (cartography regions), Task 9 (encounter-table zones → rooms), and Task 10 (trope triggers) all use the same 8-id snake_case set from Task 7.
- Creature IDs in Task 9 encounter tables match Task 6 creature IDs.
- Faction dispositions in Task 5 match archetype dispositions in Task 14.
- `cover_poi` in Task 1 (`the_summoning_stage`) matches the room ID in Task 7.

**4. Scope check:** Single world under one genre pack. Content-only. No code. Reasonable plan size (18 tasks, ~1 commit per task). Portraits/music/scenarios explicitly deferred. ✅

No issues found. Plan is ready.
