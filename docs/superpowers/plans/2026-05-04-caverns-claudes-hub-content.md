# Caverns & Claudes — Hamlet of Sünden Content Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure four `caverns_and_claudes` worlds into one Darkest-Dungeon-shaped world (`caverns_three_sins`) with a single Hamlet (Sünden) and three sub-dungeons (Grimvault/Horden/Mawdeep reframed as Pride/Greed/Gluttony). Drop `dungeon_survivor` and `primetime` entirely.

**Architecture:** Hub world directory contains world-level YAML (`world.yaml`, `hamlet.yaml`, regional lore) plus a `dungeons/` subdirectory with one folder per dungeon. Each dungeon's existing creative work (Keeper, rooms, cartography, creatures, encounter tables, tropes) survives intact, relocated under the hub.

**Tech Stack:** YAML content authoring in `sidequest-content/`. Validation via `pf validate` (genre-pack validator) and `just server-test` (loader tests).

---

## ⚠️ Engine Prerequisites — Read Before Starting

The spec (`docs/superpowers/specs/2026-05-04-caverns-claudes-hub-design.md`) calls out **seven engine items as separate plans**: loader recursion into `dungeons/`, world save persistence, stress field, dungeon-pick UI, drift/wound/Wall prompt zones.

**This content plan produces YAML the current loader CANNOT load.** Specifically:
- The current loader expects `worlds/<name>/world.yaml` to be a flat directory with one Keeper.
- The new structure puts Keepers in `worlds/<name>/dungeons/<dungeon>/dungeon.yaml`.
- Until the loader is taught about `dungeons/`, the genre pack will fail validation/load.

**Two options for sequencing:**
1. **Author on a feature branch** (`feat/caverns-three-sins-content`) and DO NOT merge until the loader plan ships. Validation steps in this plan will fail the "pack loads" check until then; treat YAML-syntax-only validation as the success bar in the meantime.
2. **Pair with the loader plan** — execute both in one combined branch.

The plan below assumes option 1 (branch-isolated authoring). The "validation" steps are scoped to what is achievable without the loader change: YAML schema sanity, no-typos, no missing required fields per existing schema. Full loader validation is gated behind the engine plan.

**Authoring location:** All work happens in `sidequest-content/` subrepo. That repo uses **gitflow → PRs target `develop`, not `main`** (per project memory: `feedback_gitflow_content.md`).

---

## File Structure (Target)

```
sidequest-content/genre_packs/caverns_and_claudes/worlds/
  caverns_three_sins/                   # NEW — replaces grimvault/horden/mawdeep
    world.yaml                          # NEW — describes Sünden + region
    hamlet.yaml                         # NEW — Sünden POIs, NPCs, services, Wall
    archetypes.yaml                     # MERGED from three sources
    archetype_funnels.yaml              # MERGED from three sources
    lore.yaml                           # NEW — regional cosmology
    history.yaml                        # NEW — regional history
    legends.yaml                        # NEW — regional legends
    factions.yaml                       # NEW — regional factions
    visual_style.yaml                   # NEW — world-level base
    portrait_manifest.yaml              # NEW — Sünden cast + per-dungeon NPCs
    pacing.yaml                         # NEW — world-level
    audio.yaml                          # NEW — Sünden music + per-dungeon overrides
    assets/                             # consolidated images
    audio/                              # consolidated audio
    dungeons/
      grimvault/
        dungeon.yaml                    # was world.yaml — slimmed
        drift_profile.yaml              # NEW — Pride drift on Sünden NPCs
        wound_profile.yaml              # NEW — post-wound Butcher
        approach.yaml                   # NEW — Ashgate as half-abandoned mouth
        rooms.yaml                      # MOVED from grimvault/
        cartography.yaml                # MOVED
        creatures.yaml                  # MOVED
        encounter_tables.yaml           # MOVED
        tropes.yaml                     # MOVED
        openings.yaml                   # MOVED, world: field updated
        legends.yaml                    # MOVED — local legends only
        factions.yaml                   # MOVED — local factions only
        visual_style.yaml               # MOVED — dungeon override
      horden/                           # same shape; approach = Copperbridge
      mawdeep/                          # same shape; approach = Gristwell

  # DELETED: dungeon_survivor/, primetime/, grimvault/, horden/, mawdeep/
```

---

## Task 1: Branch setup

**Files:**
- None (git only)

- [ ] **Step 1: Switch to sidequest-content subrepo and cut feature branch off `develop`**

```bash
cd sidequest-content
git checkout develop
git pull origin develop
git checkout -b feat/caverns-three-sins-content
```

- [ ] **Step 2: Verify clean baseline**

```bash
git status   # expect: nothing to commit, working tree clean
ls genre_packs/caverns_and_claudes/worlds/   # expect: dungeon_survivor grimvault horden mawdeep primetime
```

---

## Task 2: Delete dropped worlds (`dungeon_survivor` + `primetime`)

**Files:**
- Delete: `genre_packs/caverns_and_claudes/worlds/dungeon_survivor/`
- Delete: `genre_packs/caverns_and_claudes/worlds/primetime/`

- [ ] **Step 1: Delete both directories**

```bash
cd sidequest-content
git rm -r genre_packs/caverns_and_claudes/worlds/dungeon_survivor
git rm -r genre_packs/caverns_and_claudes/worlds/primetime
```

- [ ] **Step 2: Verify deletion**

```bash
ls genre_packs/caverns_and_claudes/worlds/
# Expected: grimvault horden mawdeep
```

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(caverns): drop dungeon_survivor and primetime worlds

Per spec docs/superpowers/specs/2026-05-04-caverns-claudes-hub-design.md.
The reality-TV concept (both folders held it under different names) is
shelved. grimvault/horden/mawdeep will be merged in subsequent commits."
```

---

## Task 3: Stage `caverns_three_sins/` skeleton with placeholders

**Files:**
- Create: `genre_packs/caverns_and_claudes/worlds/caverns_three_sins/world.yaml` (placeholder)
- Create: `genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/grimvault/.gitkeep`
- Create: `genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/horden/.gitkeep`
- Create: `genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/mawdeep/.gitkeep`

The skeleton lets later tasks land content into a known structure. The placeholder `world.yaml` is real enough to YAML-parse; full content lands in Task 20.

- [ ] **Step 1: Create skeleton directories**

```bash
cd sidequest-content
mkdir -p genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/grimvault
mkdir -p genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/horden
mkdir -p genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/mawdeep
mkdir -p genre_packs/caverns_and_claudes/worlds/caverns_three_sins/assets
mkdir -p genre_packs/caverns_and_claudes/worlds/caverns_three_sins/audio
touch genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/grimvault/.gitkeep
touch genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/horden/.gitkeep
touch genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/mawdeep/.gitkeep
```

- [ ] **Step 2: Write placeholder `world.yaml`**

Write to `genre_packs/caverns_and_claudes/worlds/caverns_three_sins/world.yaml`:

```yaml
# Caverns & Claudes — Hamlet of Sünden
# Hub world consolidating Grimvault, Horden, and Mawdeep into one persistent
# campaign with three dungeons reachable from a single Hamlet.
#
# This file is a placeholder until Task 20. The final version describes
# Sünden and the regional frame; this stub only carries enough to satisfy
# YAML parsing and obvious required fields.

cover_poi: sunden_square
name: "Hamlet of Sünden"
description: >-
  PLACEHOLDER — replaced in Task 20. Three of the Seven Deadly Sins woke
  up next to each other. The town of Sünden sits at the center of that
  wound; three dungeon mouths gape at its borders.

tagline: "Three sins. One town. Send your hirelings down."

axis_snapshot:
  comedy: 0.25
  gravity: 0.85
  outlook: 0.35

# Note: there is no `keeper:` block at world level. Keepers live in
# dungeons/<name>/dungeon.yaml.
```

- [ ] **Step 3: Verify YAML parses**

```bash
python3 -c "import yaml; yaml.safe_load(open('genre_packs/caverns_and_claudes/worlds/caverns_three_sins/world.yaml'))"
# Expected: no output (no exception)
```

- [ ] **Step 4: Commit**

```bash
git add genre_packs/caverns_and_claudes/worlds/caverns_three_sins
git commit -m "feat(caverns): scaffold caverns_three_sins skeleton

Empty hub world directory with placeholder world.yaml. Subsequent commits
fold grimvault/horden/mawdeep content into dungeons/<name>/ and author
Sünden + regional lore."
```

---

## Task 4: Move Grimvault content + slim `world.yaml` → `dungeon.yaml`

**Files:**
- Move: `worlds/grimvault/{rooms,cartography,creatures,encounter_tables,tropes,openings,legends,factions,visual_style}.yaml` → `worlds/caverns_three_sins/dungeons/grimvault/`
- Move: `worlds/grimvault/assets/` → `worlds/caverns_three_sins/dungeons/grimvault/assets/`
- Transform: `worlds/grimvault/world.yaml` → `worlds/caverns_three_sins/dungeons/grimvault/dungeon.yaml`
- Note: `archetypes.yaml`, `archetype_funnels.yaml`, `history.yaml`, `lore.yaml`, `pacing.yaml`, `portrait_manifest.yaml` stay in `worlds/grimvault/` for now — they're consumed in later world-level merge tasks.

- [ ] **Step 1: Move per-dungeon files into the new location**

```bash
cd sidequest-content
SRC=genre_packs/caverns_and_claudes/worlds/grimvault
DST=genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/grimvault

git mv $SRC/rooms.yaml $DST/rooms.yaml
git mv $SRC/cartography.yaml $DST/cartography.yaml
git mv $SRC/creatures.yaml $DST/creatures.yaml
git mv $SRC/encounter_tables.yaml $DST/encounter_tables.yaml
git mv $SRC/tropes.yaml $DST/tropes.yaml
git mv $SRC/openings.yaml $DST/openings.yaml
git mv $SRC/legends.yaml $DST/legends.yaml
git mv $SRC/factions.yaml $DST/factions.yaml
git mv $SRC/visual_style.yaml $DST/visual_style.yaml
git mv $SRC/assets $DST/assets
rm $DST/.gitkeep
```

- [ ] **Step 2: Create `dungeon.yaml` from the slimmed `world.yaml`**

Read `genre_packs/caverns_and_claudes/worlds/grimvault/world.yaml`. Copy it to the new path `worlds/caverns_three_sins/dungeons/grimvault/dungeon.yaml` with these transformations:
- **Keep:** `cover_poi`, `name`, `description`, `tagline`, `axis_snapshot`, `keeper:` (full block including monologue_style, trap_aesthetic, topology_tendency, awareness ladder).
- **Add at top:** a `sin: pride` field declaring this dungeon's Deadly Sin.
- **Add at top:** a `parent_world: caverns_three_sins` field for traceability.
- **Drop:** any town/Hamlet-specific fields (the town demotes to `approach.yaml` in Task 9).

Result starts roughly:

```yaml
# Grimvault — The Patient Butcher's workshop. Sin: Pride.
# Slimmed from worlds/grimvault/world.yaml. Town fields moved to approach.yaml.

parent_world: caverns_three_sins
sin: pride
cover_poi: the_descent
name: Grimvault
description: >-
  A dungeon that takes things apart. Not flesh — qualities. Warmth
  leaves the stone first. Then color drains from the walls. Then
  sound stops carrying. The deeper you go, the less there is of
  everything except the Keeper's attention.

tagline: "It takes what makes things what they are."

axis_snapshot:
  comedy: 0.3
  gravity: 0.8
  outlook: 0.4

keeper:
  name: "The Patient Butcher"
  personality: methodical
  obsession: separation
  # ... rest of the existing keeper block, unchanged
```

- [ ] **Step 3: Update `world:` field references in moved files**

`openings.yaml` has `world: grimvault` near the top. Update it to `world: caverns_three_sins`. Add a new `dungeon: grimvault` field below it.

```bash
# Verify the change
grep -n "^world:\|^dungeon:" genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/grimvault/openings.yaml
# Expected:
# world: caverns_three_sins
# dungeon: grimvault
```

Check `visual_style.yaml`, `cartography.yaml`, `tropes.yaml` for similar `world:` references and update or add `dungeon:` as appropriate.

- [ ] **Step 4: Verify YAML parses for all moved files**

```bash
for f in genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/grimvault/*.yaml; do
  python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" "$f" || echo "FAIL: $f"
done
# Expected: no FAIL lines
```

- [ ] **Step 5: Commit**

```bash
git add genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/grimvault
git commit -m "feat(caverns): relocate grimvault content under caverns_three_sins

Per-dungeon files (rooms, cartography, creatures, encounter_tables, tropes,
openings, dungeon-local legends/factions, visual_style, assets) move into
dungeons/grimvault/. world.yaml slims to dungeon.yaml with sin: pride and
parent_world: caverns_three_sins fields added.

Archetype/lore/history/pacing/portrait files stay in worlds/grimvault/
until they're merged into the world-level files in later tasks."
```

---

## Task 5: Move Horden content + slim to `dungeon.yaml` (sin: greed)

Same shape as Task 4 with these substitutions:
- `grimvault` → `horden`
- `sin: pride` → `sin: greed`
- Keeper is "The Hoarder", not "The Patient Butcher".

- [ ] **Step 1: Move per-dungeon files**

```bash
cd sidequest-content
SRC=genre_packs/caverns_and_claudes/worlds/horden
DST=genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/horden

git mv $SRC/rooms.yaml $DST/rooms.yaml
git mv $SRC/cartography.yaml $DST/cartography.yaml
git mv $SRC/creatures.yaml $DST/creatures.yaml
git mv $SRC/encounter_tables.yaml $DST/encounter_tables.yaml
git mv $SRC/tropes.yaml $DST/tropes.yaml
git mv $SRC/openings.yaml $DST/openings.yaml
git mv $SRC/legends.yaml $DST/legends.yaml
git mv $SRC/factions.yaml $DST/factions.yaml
git mv $SRC/visual_style.yaml $DST/visual_style.yaml
git mv $SRC/assets $DST/assets
rm $DST/.gitkeep
```

- [ ] **Step 2: Create `dungeon.yaml` from `world.yaml`**

Read `worlds/horden/world.yaml`. Write to `worlds/caverns_three_sins/dungeons/horden/dungeon.yaml`:
- Same transformations as Task 4 Step 2.
- Add: `sin: greed`, `parent_world: caverns_three_sins`.
- Keep the full `keeper:` block (Hoarder, obsession: retention).
- Drop town-specific fields (Copperbridge demotes to `approach.yaml` in Task 9).

- [ ] **Step 3: Update `world:` references in moved files**

```bash
grep -rln "^world: horden" genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/horden/
# Update each match: world: caverns_three_sins; add dungeon: horden
```

- [ ] **Step 4: Verify YAML parses**

```bash
for f in genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/horden/*.yaml; do
  python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" "$f" || echo "FAIL: $f"
done
```

- [ ] **Step 5: Commit**

```bash
git add genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/horden
git commit -m "feat(caverns): relocate horden content under caverns_three_sins

Same shape as grimvault relocation. sin: greed, Keeper is The Hoarder."
```

---

## Task 6: Move Mawdeep content + slim to `dungeon.yaml` (sin: gluttony)

Same shape as Task 4 with:
- `grimvault` → `mawdeep`
- `sin: pride` → `sin: gluttony`
- Keeper is "The Glutton Below".

- [ ] **Step 1: Move per-dungeon files**

```bash
cd sidequest-content
SRC=genre_packs/caverns_and_claudes/worlds/mawdeep
DST=genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/mawdeep

git mv $SRC/rooms.yaml $DST/rooms.yaml
git mv $SRC/cartography.yaml $DST/cartography.yaml
git mv $SRC/creatures.yaml $DST/creatures.yaml
git mv $SRC/encounter_tables.yaml $DST/encounter_tables.yaml
git mv $SRC/tropes.yaml $DST/tropes.yaml
git mv $SRC/openings.yaml $DST/openings.yaml
git mv $SRC/legends.yaml $DST/legends.yaml
git mv $SRC/factions.yaml $DST/factions.yaml
git mv $SRC/visual_style.yaml $DST/visual_style.yaml
git mv $SRC/assets $DST/assets
rm $DST/.gitkeep
```

- [ ] **Step 2: Create `dungeon.yaml` from `world.yaml`**

Same transforms as Task 4 Step 2 with `sin: gluttony`, `parent_world: caverns_three_sins`. Keep the full Glutton Below `keeper:` block.

- [ ] **Step 3: Update `world:` references in moved files**

Find/replace `world: mawdeep` → `world: caverns_three_sins`; add `dungeon: mawdeep` lines.

- [ ] **Step 4: Verify YAML parses**

```bash
for f in genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/mawdeep/*.yaml; do
  python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" "$f" || echo "FAIL: $f"
done
```

- [ ] **Step 5: Commit**

```bash
git add genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/mawdeep
git commit -m "feat(caverns): relocate mawdeep content under caverns_three_sins

Same shape as grimvault relocation. sin: gluttony, Keeper is The Glutton Below."
```

---

## Task 7: Author per-dungeon `drift_profile.yaml` × 3

**Files:**
- Create: `worlds/caverns_three_sins/dungeons/grimvault/drift_profile.yaml`
- Create: `worlds/caverns_three_sins/dungeons/horden/drift_profile.yaml`
- Create: `worlds/caverns_three_sins/dungeons/mawdeep/drift_profile.yaml`

Drift profiles describe how Sünden NPCs read after a delve into THIS dungeon. They are content for a Hamlet narrator prompt-zone (engine work in a separate plan). This task authors the content — the engine plan wires it.

**Schema (proposed; finalize in this task by writing files that match):**

```yaml
# Drift profile: how Sünden NPCs are colored after a delve into THIS dungeon.
# Consumed by the Hamlet narrator prompt-zone via latest_delve_sin flag.

dungeon: <slug>
sin: <pride|greed|gluttony>

ambient_drift: >-
  One short paragraph (~80 words) describing the overall feel of Sünden after
  party returns from this dungeon. Not the NPCs — the place. Light, sound,
  air, behavior of inanimate things.

npc_overrides:
  - role: innkeeper
    drift: >-
      How the innkeeper specifically presents post-delve. ~40 words. Voice,
      mannerism, what they say, what they don't.
  - role: recruiter
    drift: >-
      Same shape. ~40 words.
  - role: market_vendor
    drift: >-
      Same shape.
  - role: confessional_keeper
    drift: >-
      Same shape.
  - role: workhouse_master
    drift: >-
      Same shape.
  - role: masquerade_host
    drift: >-
      Same shape.
  - role: itinerant_preacher
    drift: >-
      Same shape.

decay:
  duration_delves: 1
  notes: >-
    Drift is overwritten by the next delve's drift profile. There is no
    fade — it's a flag swap on delve-end.
```

- [ ] **Step 1: Author `dungeons/grimvault/drift_profile.yaml` (sin: pride)**

Drift theme: clinical separation, things-taken-apart, sound/color/warmth withdrawing. Reference the Patient Butcher's `monologue_style` in `dungeon.yaml` for tone. Sample prompts from the design spec §"Sin-Drift on Returning NPCs":
- innkeeper's voice doesn't carry
- market vendor sorts by material, not value
- conversations feel evaluated, not greeted

Author 6–8 NPC drift entries. Keep each entry tight — narrator prompt-zone will assemble them; verbose entries blow context budget.

- [ ] **Step 2: Author `dungeons/horden/drift_profile.yaml` (sin: greed)**

Drift theme: retention, nothing-leaves, things-not-released. Sample prompts from spec:
- coins won't change hands
- shopkeepers add to piles they're not counting
- recruiter quotes prices but doesn't take payment
- doors stay half-closed, sentences trail unfinished

- [ ] **Step 3: Author `dungeons/mawdeep/drift_profile.yaml` (sin: gluttony)**

Drift theme: appetite, consumption, never-full. Sample prompts from spec:
- someone is always eating
- innkeeper talks with mouth full
- preacher's sermon has crumbs
- nobody appears full

- [ ] **Step 4: Verify YAML parses**

```bash
for f in genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/*/drift_profile.yaml; do
  python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" "$f" || echo "FAIL: $f"
done
```

- [ ] **Step 5: Commit**

```bash
git add genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/*/drift_profile.yaml
git commit -m "feat(caverns): author drift profiles per sin

Pride/Greed/Gluttony drift profiles describe how Sünden NPCs read after a
delve into each dungeon. Consumed by Hamlet narrator prompt-zone (engine
plan separate). Tight entries to keep prompt-zone budget manageable."
```

---

## Task 8: Author per-dungeon `wound_profile.yaml` × 3

**Files:**
- Create: `worlds/caverns_three_sins/dungeons/grimvault/wound_profile.yaml`
- Create: `worlds/caverns_three_sins/dungeons/horden/wound_profile.yaml`
- Create: `worlds/caverns_three_sins/dungeons/mawdeep/wound_profile.yaml`

Wound profiles describe how a dungeon changes after a successful boss-floor delve flips the `is_wounded` flag. The dungeon stays delvable but is permanently different.

**Schema (proposed):**

```yaml
# Wound profile: applied to dungeon after boss-floor success.
# Merges into the Keeper definition via narrator prompt-zone (engine plan separate).

dungeon: <slug>
sin: <pride|greed|gluttony>

# Override deltas — narrator prompt-zone applies these on top of base Keeper.
keeper_overrides:
  monologue_style_delta: >-
    1-2 sentences describing how the Keeper's voice has changed post-wound.
    Patient Butcher: colder, slower, more distributed across surfaces.
    Hoarder: paranoid, counting more obsessively, miscounting.
    Glutton Below: slower, larger, more displacement of rooms.

  awareness_delta:
    starting: <int>           # delta on starting awareness (e.g. -1 if wounded means slower to notice)
    tick_rate: <float>        # delta on tick rate
    threshold_overrides:
      "3": >-
        Replacement text for awareness threshold 3 post-wound, OR null to keep base.
      # ... per threshold

ambient_delta: >-
  One paragraph describing how the dungeon's ambient feel has changed.
  Air, light, the way rooms connect. ~80 words.

new_lore_strand: >-
  One paragraph that the Wall and the regional history can reference once
  this dungeon is wounded — what the world says about it now. ~100 words.
```

- [ ] **Step 1: Author `dungeons/grimvault/wound_profile.yaml`**

Patient Butcher post-wound: the precision is still there but distributed across more surfaces — the workshop is now everywhere, less concentrated. Slower, colder, awareness ladder shifts (later notice, but stronger reaction once aware).

- [ ] **Step 2: Author `dungeons/horden/wound_profile.yaml`**

The Hoarder post-wound: paranoid, miscounting, breaking own rules — coins drift back the wrong way occasionally. Awareness becomes erratic.

- [ ] **Step 3: Author `dungeons/mawdeep/wound_profile.yaml`**

The Glutton Below post-wound: slower digestion, displacement — rooms swap places, walls bulge. Awareness slows but the dungeon is physically larger.

- [ ] **Step 4: Verify YAML parses**

```bash
for f in genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/*/wound_profile.yaml; do
  python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" "$f" || echo "FAIL: $f"
done
```

- [ ] **Step 5: Commit**

```bash
git add genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/*/wound_profile.yaml
git commit -m "feat(caverns): author wound profiles per sin

Each dungeon gets a post-boss-delve transformation profile. Sins are wounded,
not killed; the dungeon stays delvable but permanently changed. Engine flag-
flip + prompt-zone consumption are separate plans."
```

---

## Task 9: Author per-dungeon `approach.yaml` × 3

**Files:**
- Create: `worlds/caverns_three_sins/dungeons/grimvault/approach.yaml` (Ashgate)
- Create: `worlds/caverns_three_sins/dungeons/horden/approach.yaml` (Copperbridge)
- Create: `worlds/caverns_three_sins/dungeons/mawdeep/approach.yaml` (Gristwell)

Each existing town demotes from "the world's town" to "a half-abandoned dungeon-mouth hamlet." Sünden is the world's actual town now (Task 19). The approaches still exist as scenes a party walks through to enter a dungeon.

**Source material:** the existing town descriptions in `worlds/grimvault/world.yaml`, `worlds/horden/world.yaml`, `worlds/mawdeep/world.yaml` (currently sitting at top level — they'll be deleted in Task 21). Pull the town material out before Task 21 wipes them.

**Schema (proposed):**

```yaml
# Approach: a half-abandoned hamlet at this dungeon's mouth. The party walks
# through here on the way down and on the way back. NOT a hub town — Sünden
# is the hub. Approaches are sin-touched, hollow, mostly silent.

dungeon: <slug>
name: <e.g. Ashgate>
slug: <e.g. ashgate>

description: >-
  One paragraph describing the hamlet now. Past tense for what it used to be,
  present tense for what it is. The sin's pull on it. ~150 words.

state: hollowed                    # was thriving when grimvault/horden/mawdeep were full worlds
population_remaining: <int>        # rough estimate; small (5–30 typical)

what_remains:
  - one sentence about a building that's still standing
  - one about a person who didn't leave
  - one about a custom that persists despite making no sense

scene_hooks:
  - id: arrival
    when: party_first_enters
    description: >-
      What the party sees on arrival. Tight — narrator riffs on this.
  - id: return
    when: party_returns_from_delve
    description: >-
      What the party sees on the way back. Different beat than arrival.

# These were full POIs in the old world.yaml — preserve the most evocative
# 1-3 as named locations in the approach. Drop the rest.
points_of_interest:
  - name: <e.g. The Quiet Field>
    slug: <e.g. the_quiet_field>
    description: >-
      ~60 words.
```

- [ ] **Step 1: Author `dungeons/grimvault/approach.yaml` (Ashgate)**

Source: existing Ashgate description in `worlds/grimvault/world.yaml` (and the Ashgate Square / The Spillway / Quiet Field POIs from `worlds/grimvault/history.yaml`). The town is hollowed — the prosperity drained away, the Quiet Field still extends between hamlet and dungeon entrance, a few holdouts still live there because they cannot taste food anywhere else either.

- [ ] **Step 2: Author `dungeons/horden/approach.yaml` (Copperbridge)**

Source: existing Copperbridge material in `worlds/horden/world.yaml` and `worlds/horden/history.yaml`. The town survives by picking through what spills out of Horden, but nothing comes out on purpose. Half the buildings are stuffed with items nobody can sell.

- [ ] **Step 3: Author `dungeons/mawdeep/approach.yaml` (Gristwell)**

Source: existing Gristwell material in `worlds/mawdeep/world.yaml` and `worlds/mawdeep/history.yaml`. The town clings to the dungeon mouth like a barnacle on a whale; remaining residents are ones who either profit from delvers' deaths or have nowhere else to go.

- [ ] **Step 4: Verify YAML parses**

```bash
for f in genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/*/approach.yaml; do
  python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" "$f" || echo "FAIL: $f"
done
```

- [ ] **Step 5: Commit**

```bash
git add genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/*/approach.yaml
git commit -m "feat(caverns): author dungeon approaches (Ashgate, Copperbridge, Gristwell)

Each old per-dungeon town demotes to a half-abandoned approach hamlet. The
party walks through on the way to and from the dungeon. Sünden (Task 19) is
the actual hub town; approaches preserve the most evocative POIs from each."
```

---

## Task 10: Merge `archetypes.yaml` + `archetype_funnels.yaml` (three sources → one)

**Files:**
- Create: `worlds/caverns_three_sins/archetypes.yaml`
- Create: `worlds/caverns_three_sins/archetype_funnels.yaml`
- Reads (will be deleted in Task 21): `worlds/grimvault/archetypes.yaml`, `worlds/horden/archetypes.yaml`, `worlds/mawdeep/archetypes.yaml` and their `archetype_funnels.yaml` counterparts.

The hireling roster is **world-level** in the new structure. A hireling exists in Sünden, gets sent into any of the three dungeons. Per-dungeon archetypes (Assayer for Grimvault, etc.) remain in the world-level file but are tagged with their sin-association so the recruiter can flavor them and the narrator can apply drift correctly.

**Strategy:**
1. Concatenate all three sources.
2. **Deduplicate exact name matches** (e.g. "Torchbearer" if it appears in multiple — likely doesn't since these are world-level not genre-level).
3. **Preserve near-duplicates** but rename for clarity (e.g. an Assayer-style cataloger from Grimvault stays distinct from a Horden inventory-keeper).
4. **Tag with sin association** — add an optional `sin_origin: pride|greed|gluttony` field on each archetype.
5. **Add sin-neutral archetypes** as they emerge — generic Sünden townsfolk archetypes that aren't tied to one sin.

- [ ] **Step 1: Concatenate and dedupe `archetypes.yaml`**

Read all three source files. Build the merged file:

```yaml
# Caverns & Claudes — Hamlet of Sünden — World-Level Archetypes
#
# Hirelings are world-level: they live in Sünden and can be sent into any
# of the three dungeons. Each archetype tagged with sin_origin where it
# was originally authored for one sin's culture.

# Pride-origin archetypes (from Grimvault / Ashgate Assayer culture)
- name: Assayer
  sin_origin: pride
  description: >-
    A meticulous cataloger ...   # copy verbatim from worlds/grimvault/archetypes.yaml
  # ... rest of fields

- name: Recovery Specialist
  sin_origin: pride
  # ...

# Greed-origin archetypes (from Horden / Copperbridge culture)
- name: <pull each from worlds/horden/archetypes.yaml>
  sin_origin: greed
  # ...

# Gluttony-origin archetypes (from Mawdeep / Gristwell culture)
- name: <pull each from worlds/mawdeep/archetypes.yaml>
  sin_origin: gluttony
  # ...
```

If two archetypes have the same `name`, rename the latter (e.g. "Cataloger (Hoarder-side)") and keep both unless they're functionally identical. Comment any merges/renames at the file head so future readers know what happened.

- [ ] **Step 2: Concatenate and dedupe `archetype_funnels.yaml`**

Same strategy. Funnels in `worlds/grimvault/archetype_funnels.yaml` reference `faction: The Assayers` etc. — those factions become regional (Task 14), so the funnel references stay valid.

```yaml
funnels:
  # ── Pride-origin funnels (was grimvault) ────────────────────────────
  - name: Cataloging Delver
    sin_origin: pride
    absorbs:
      - [hero, tank]
      # ... copy verbatim
  # ── Greed-origin funnels (was horden) ───────────────────────────────
  # ... etc
```

- [ ] **Step 3: Verify YAML parses**

```bash
python3 -c "import yaml; yaml.safe_load(open('genre_packs/caverns_and_claudes/worlds/caverns_three_sins/archetypes.yaml'))"
python3 -c "import yaml; yaml.safe_load(open('genre_packs/caverns_and_claudes/worlds/caverns_three_sins/archetype_funnels.yaml'))"
# Expected: no output
```

- [ ] **Step 4: Spot-check archetype count**

```bash
python3 -c "
import yaml
m = yaml.safe_load(open('genre_packs/caverns_and_claudes/worlds/caverns_three_sins/archetypes.yaml'))
g = yaml.safe_load(open('genre_packs/caverns_and_claudes/worlds/grimvault/archetypes.yaml'))
h = yaml.safe_load(open('genre_packs/caverns_and_claudes/worlds/horden/archetypes.yaml'))
w = yaml.safe_load(open('genre_packs/caverns_and_claudes/worlds/mawdeep/archetypes.yaml'))
print(f'merged={len(m)} grim={len(g)} horden={len(h)} mawdeep={len(w)} sum={len(g)+len(h)+len(w)}')
"
# Expected: merged ≤ sum (some may have deduped; should not lose distinct ones)
```

- [ ] **Step 5: Commit**

```bash
git add genre_packs/caverns_and_claudes/worlds/caverns_three_sins/archetypes.yaml \
        genre_packs/caverns_and_claudes/worlds/caverns_three_sins/archetype_funnels.yaml
git commit -m "feat(caverns): merge per-dungeon archetypes into world-level roster

Hirelings live in Sünden and can be sent to any dungeon. Each archetype
keeps its origin culture via sin_origin tag (pride/greed/gluttony). Source
files in worlds/{grimvault,horden,mawdeep}/ stay until Task 21 cleanup."
```

---

## Task 11: Author regional `lore.yaml`

**Files:**
- Create: `worlds/caverns_three_sins/lore.yaml`
- Reads (deleted in Task 21): `worlds/grimvault/lore.yaml`, `worlds/horden/lore.yaml`, `worlds/mawdeep/lore.yaml`

**Schema (match existing `worlds/grimvault/lore.yaml`):**
- `world_name` (string) — `"Hamlet of Sünden"` or `"Caverns Three Sins"`
- `history` (long string) — 200–400 words, regional history; what was the area before, what changed when three sins woke close together
- `geography` (long string) — 150–300 words, the region around Sünden, the three dungeon entrances, the approaches between
- `cosmology` (long string) — **THIS IS THE NEW LOAD-BEARING WRITING**. 250–400 words explaining the three-of-seven framing. The Seven sleep in the world's old places; three of them woke up here; the other four are stories elsewhere. Loose kinship — implied connection without committed canonical bond.
- `themes` (list of strings, ~6–8) — regional themes drawing from all three sins
- `genre_conventions` (list of strings) — preserve from existing files where relevant; this is genre-level convention reminders the narrator pulls from

**Authoring constraints:**
- Banned words list (per memory `feedback_made_up_names.md`): "Reach", "Veil", "Spire", "Hollow", "Drift" (as suffix), "Mire", "Shroud", "Sanctum", "Bastion". Check final prose for these.
- Names already in use that you can lean on: Sünden, Ashgate, Copperbridge, Gristwell, Grimvault, Horden, Mawdeep.
- Keep the **loose kinship** framing — three sins woke up close; the *why* is left ambiguous; the other four are referenced ("they say Wrath sleeps somewhere east, they say Sloth's grave is under the southern marsh, but those are stories told elsewhere") without commitment.

- [ ] **Step 1: Read all three source `lore.yaml` files**

```bash
cat genre_packs/caverns_and_claudes/worlds/grimvault/lore.yaml
cat genre_packs/caverns_and_claudes/worlds/horden/lore.yaml
cat genre_packs/caverns_and_claudes/worlds/mawdeep/lore.yaml
```

- [ ] **Step 2: Author `worlds/caverns_three_sins/lore.yaml`**

Match the schema of the source files. World-name is the merged hub. History tells the regional story. Cosmology explicitly establishes "three of seven" framing.

- [ ] **Step 3: Verify YAML parses + check banned words**

```bash
python3 -c "import yaml; yaml.safe_load(open('genre_packs/caverns_and_claudes/worlds/caverns_three_sins/lore.yaml'))"
grep -wEi "Reach|Veil|Spire|Hollow|Mire|Shroud|Sanctum|Bastion" \
  genre_packs/caverns_and_claudes/worlds/caverns_three_sins/lore.yaml \
  || echo "OK no banned words"
```

- [ ] **Step 4: Commit**

```bash
git add genre_packs/caverns_and_claudes/worlds/caverns_three_sins/lore.yaml
git commit -m "feat(caverns): author regional lore.yaml

Three-of-seven sins cosmology. Loose thematic kinship — three sins woke up
close to each other; the other four are stories told elsewhere. Sünden as
the only inhabited point at the regional center."
```

---

## Task 12: Author regional `history.yaml`

**Files:**
- Create: `worlds/caverns_three_sins/history.yaml`
- Reads (deleted in Task 21): three source `history.yaml` files

**Schema (match existing `worlds/grimvault/history.yaml`):**
- Top-level key `chapters:` is a list.
- Each chapter has: `id`, `label`, `session_range` ([start, end]), `lore` (list of long strings), `location`, `time_of_day`, `atmosphere`, `points_of_interest` (list of {name, slug, region, type, description}).

**Strategy:** the new `history.yaml` is a **regional** progression covering all three dungeons. Chapters track campaign maturity (early Sünden delves vs later, more wounds inflicted, more roster history) rather than per-dungeon depth.

Suggested chapter outline (engineer adjusts during authoring):
- `id: arrival` — party first arrives in Sünden, all three sins are stories. Roster is fresh. Sessions 1-2.
- `id: first_blood` — first meaningful loss or first dungeon scratched. Sessions 3-5.
- `id: wounded_one` — at least one sin has been wounded. Sessions 6-10.
- `id: wounded_two` — two sins wounded. The Hamlet's character has shifted. Sessions 11-15.
- `id: wounded_all` — all three sins wounded. The campaign's late phase. Sessions 16+.

POIs at the chapter level should reference Sünden landmarks (Square, the Wall, the three stress services, the recruiter) — these get authored in Task 19's hamlet.yaml; cross-reference them here.

- [ ] **Step 1: Read source histories**

```bash
cat genre_packs/caverns_and_claudes/worlds/grimvault/history.yaml
cat genre_packs/caverns_and_claudes/worlds/horden/history.yaml
cat genre_packs/caverns_and_claudes/worlds/mawdeep/history.yaml
```

- [ ] **Step 2: Author chapters**

Author 5 chapters following the suggested outline. Each chapter's `lore` block draws from the regional cosmology authored in Task 11. Each chapter's POI list references Sünden + at least one approach.

- [ ] **Step 3: Verify schema**

```bash
python3 -c "
import yaml
data = yaml.safe_load(open('genre_packs/caverns_and_claudes/worlds/caverns_three_sins/history.yaml'))
assert 'chapters' in data, 'missing chapters key'
for c in data['chapters']:
    for required in ['id','label','session_range','lore','location','atmosphere','points_of_interest']:
        assert required in c, f'chapter {c.get(\"id\",\"?\")} missing {required}'
print(f'OK {len(data[\"chapters\"])} chapters')
"
```

- [ ] **Step 4: Commit**

```bash
git add genre_packs/caverns_and_claudes/worlds/caverns_three_sins/history.yaml
git commit -m "feat(caverns): author regional history.yaml

Five-chapter campaign progression: arrival, first_blood, wounded_one,
wounded_two, wounded_all. Tracks Hamlet/roster maturity, not per-dungeon
depth. POIs reference Sünden + approaches."
```

---

## Task 13: Author regional `legends.yaml`

**Files:**
- Create: `worlds/caverns_three_sins/legends.yaml`
- Reads (NOT deleted — they survive at per-dungeon level): the moved per-dungeon `legends.yaml` files in `dungeons/<name>/legends.yaml`.

The world-level `legends.yaml` carries **regional** legends — stories about Sünden, the three-of-seven framing, the founding of the Hamlet, the four absent sins (told as rumor). Per-dungeon legends remain per-dungeon.

**Schema (match existing per-dungeon `legends.yaml`):**
- Top-level: list of legend objects.
- Each: `name`, `summary`, `era`, `affected_cultures`, `cultural_impact`, optional `faction_grudges`, `lost_arts`, `monuments`, `terrain_scars`.

Suggested regional legends (engineer expands during authoring):
- "The Three Wakings" — when each sin woke, briefly told.
- "The Founding of Sünden" — why a town exists at the center of three horrors.
- "The Wall Begins" — the first name carved into the Wall.
- "The Four Absent" — what people whisper about Wrath, Sloth, Lust, Envy.
- "The First Hireling Who Came Back Wrong" — apocryphal, told in the Spillway-equivalent tavern.

- [ ] **Step 1: Read per-dungeon legends for tone consistency**

```bash
cat genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/grimvault/legends.yaml
cat genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/horden/legends.yaml
cat genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/mawdeep/legends.yaml
```

- [ ] **Step 2: Author 4-6 regional legends matching schema**

- [ ] **Step 3: Verify YAML parses + banned-words check**

```bash
python3 -c "import yaml; yaml.safe_load(open('genre_packs/caverns_and_claudes/worlds/caverns_three_sins/legends.yaml'))"
grep -wEi "Reach|Veil|Spire|Hollow|Mire|Shroud|Sanctum|Bastion" \
  genre_packs/caverns_and_claudes/worlds/caverns_three_sins/legends.yaml \
  || echo "OK no banned words"
```

- [ ] **Step 4: Commit**

```bash
git add genre_packs/caverns_and_claudes/worlds/caverns_three_sins/legends.yaml
git commit -m "feat(caverns): author regional legends.yaml

Regional legends — the Three Wakings, founding of Sünden, the Wall, the
four absent sins as rumor. Per-dungeon legends stay in dungeons/<name>/."
```

---

## Task 14: Author regional `factions.yaml`

**Files:**
- Create: `worlds/caverns_three_sins/factions.yaml`
- Reads (will be partially preserved per-dungeon): the moved per-dungeon `factions.yaml` files.

Some factions are world-level (operating across all three dungeons — e.g. a guild based in Sünden), others stay per-dungeon (the Assayers belong to Ashgate-Grimvault, not Sünden). Strategy:
1. Promote any faction whose described scope includes the broader region OR Sünden.
2. Leave dungeon-local factions in `dungeons/<name>/factions.yaml`.
3. Author at least 2-3 NEW Sünden-resident factions that operate across the region:
   - The keepers of the Wall (whoever maintains the monument).
   - A guild that vets returning hirelings (sees who came back changed).
   - A confraternity tied to one or all of the three stress services.

**Schema (match existing per-dungeon `factions.yaml`):**
- Top-level: `factions:` list.
- Each: `name`, `description`, `goal`, `urgency`, `scene_event`, `disposition_to_players`, `resources`, `key_npcs` (list of {name, role, description}), `relationships`.

- [ ] **Step 1: Read each per-dungeon `factions.yaml` and decide for each faction: keep local OR promote to regional**

Annotate the decision in a working note (not committed). Most factions stay local (Assayers, Ledger-equivalents).

- [ ] **Step 2: Author regional factions.yaml**

Include at least the 2-3 NEW Sünden-resident factions. Reference Sünden NPCs by name where possible (cross-referenced with Task 19's hamlet.yaml).

- [ ] **Step 3: Verify YAML parses**

```bash
python3 -c "
import yaml
data = yaml.safe_load(open('genre_packs/caverns_and_claudes/worlds/caverns_three_sins/factions.yaml'))
assert 'factions' in data
print(f'OK {len(data[\"factions\"])} factions')
"
```

- [ ] **Step 4: Commit**

```bash
git add genre_packs/caverns_and_claudes/worlds/caverns_three_sins/factions.yaml
git commit -m "feat(caverns): author regional factions.yaml

Sünden-resident factions: Wall-keepers, hireling vetters, sin-virtue
confraternity. Per-dungeon factions (Assayers, etc.) stay in
dungeons/<name>/factions.yaml."
```

---

## Task 15: Author world-level `visual_style.yaml`

**Files:**
- Create: `worlds/caverns_three_sins/visual_style.yaml`
- Per-dungeon overrides already in place at `dungeons/<name>/visual_style.yaml`.

**Schema (match existing per-dungeon `visual_style.yaml`):**
- `positive_suffix` (long string) — Z-Image positive prompt suffix appended to genre-level B&W ink suffix.
- `negative_prompt` (empty string — Z-Image ignores it; reject clauses go in positive_suffix per `PROMPTING_Z_IMAGE.md` and project memory).
- `color_palette` (dict: primary/secondary/accent/shadow/highlight as hex).
- `atmosphere` (dict by depth/level — for the world this is more like by-area: square, market, the Wall, approaches).

**Authoring focus:** Sünden is the world-level visual base. The Hamlet is a town — warmer than the dungeons but sin-touched, never quite at ease. Cold limestone like Ashgate but with more lived-in weathering. The dungeons keep their existing sharper visual_style overrides (cold-precise / acquisitive-clutter / wet-organic).

Per project memory: **Z-Image ignores `negative_prompt`. Rejection clauses go into `positive_suffix` as "No X, no Y" — not into `negative_prompt`.**

- [ ] **Step 1: Read existing per-dungeon visual_style files for tone reference**

- [ ] **Step 2: Author world-level visual_style.yaml**

- [ ] **Step 3: Verify YAML parses + Z-Image discipline**

```bash
python3 -c "
import yaml
v = yaml.safe_load(open('genre_packs/caverns_and_claudes/worlds/caverns_three_sins/visual_style.yaml'))
assert v.get('negative_prompt','') == '', 'negative_prompt must be empty (Z-Image ignores it)'
assert v.get('positive_suffix'), 'positive_suffix required'
print('OK')
"
```

- [ ] **Step 4: Commit**

```bash
git add genre_packs/caverns_and_claudes/worlds/caverns_three_sins/visual_style.yaml
git commit -m "feat(caverns): author world-level visual_style.yaml

Sünden visual base — limestone hamlet, sin-touched but lived-in. Per-dungeon
overrides preserved at dungeons/<name>/visual_style.yaml."
```

---

## Task 16: Author world-level `pacing.yaml`

**Files:**
- Create: `worlds/caverns_three_sins/pacing.yaml`
- Reads: three source `worlds/<name>/pacing.yaml` files (deleted in Task 21).

**Schema (match existing `worlds/grimvault/pacing.yaml`):**
- `drama_thresholds` (dict: sentence_delivery, render, escalation, climax thresholds 0-1).
- `pacing_profile.default_tempo` (string).
- `pacing_profile.tempo_overrides` (list of {context, tempo, notes}) — context is exploration/combat/extraction/boss + new ones for Sünden contexts.
- `narration_style` (sub-block).

**World-level pacing** describes the **default** for the world (most Sünden scenes — slower, more deliberate, hireling-aware). Per-dungeon delves can override via per-dungeon pacing if needed (the existing files in dungeons/ — they had pacing? double check, may need to move them).

Wait — `pacing.yaml` was world-level in the OLD structure (one per old world). In the new structure, per-dungeon pacing is OPTIONAL. The world `pacing.yaml` is now Sünden-default + add new contexts:
- `context: hamlet` (returning to Sünden between delves).
- `context: recruitment` (rolling up new hirelings).
- `context: stress_relief` (one of the three services).
- `context: the_wall` (a scene at the Wall).

- [ ] **Step 1: Read three sources, find common pacing patterns**

- [ ] **Step 2: Author world-level pacing.yaml**

Default tempo `deliberate`. Add new context overrides for hamlet/recruitment/stress_relief/the_wall scenes. Keep dungeon-context tempo entries flexible (they're overridden by per-dungeon if needed).

- [ ] **Step 3: Verify YAML parses**

```bash
python3 -c "import yaml; yaml.safe_load(open('genre_packs/caverns_and_claudes/worlds/caverns_three_sins/pacing.yaml'))"
```

- [ ] **Step 4: Commit**

```bash
git add genre_packs/caverns_and_claudes/worlds/caverns_three_sins/pacing.yaml
git commit -m "feat(caverns): author world-level pacing.yaml

Sünden default tempo plus new contexts: hamlet, recruitment, stress_relief,
the_wall. Per-dungeon overrides remain optional."
```

---

## Task 17: Consolidate `audio.yaml` + `audio/` + `assets/`

**Files:**
- Create: `worlds/caverns_three_sins/audio.yaml`
- Move/merge: existing `worlds/<name>/audio/` and `worlds/<name>/assets/` directories.
- Note: of the three source worlds, only `primetime/` (deleted in Task 2) had a fully populated `audio/` dir. Grimvault, horden, mawdeep do not appear to have per-world audio dirs — they inherit from genre-level. Check this when authoring.

**Schema (reference: `worlds/primetime/audio.yaml` — but that file is deleted; refer to commit `c438c52^` if needed, or to genre-level `genre_packs/caverns_and_claudes/audio.yaml`):**
- `world` (string) — the world slug.
- `genre` (string).
- `inherits_from` (path to genre-level audio.yaml).
- `override_policy` (string).
- `mixer` (dict: music_volume, sfx_volume, crossfade_default_ms).
- `mood_tracks` (list).
- `sfx_library` (list).

Sünden audio: hamlet ambience (low, lived-in), three sin-themed mood tracks for delve scenes (already present at genre level — check before re-authoring), stress-service-specific cues (Confessional / Workhouse / Masquerade) if music is intended for those scenes.

**Likely outcome:** small audio.yaml that mostly inherits, adds Sünden-specific mood tracks, references existing per-dungeon mood material in genre-level audio.

- [ ] **Step 1: Inventory existing audio**

```bash
ls genre_packs/caverns_and_claudes/audio/ 2>/dev/null
ls genre_packs/caverns_and_claudes/worlds/grimvault/audio/ 2>/dev/null
ls genre_packs/caverns_and_claudes/worlds/horden/audio/ 2>/dev/null
ls genre_packs/caverns_and_claudes/worlds/mawdeep/audio/ 2>/dev/null
cat genre_packs/caverns_and_claudes/audio.yaml
```

- [ ] **Step 2: Author world-level audio.yaml**

Inherits from genre-level. Adds Sünden hamlet ambient cue if appropriate.

- [ ] **Step 3: Move per-dungeon audio assets**

If any of the three source worlds had audio assets, move them under `worlds/caverns_three_sins/dungeons/<name>/audio/` (or to world level if regional). Use `git mv` to preserve history. **Do not duplicate** — if an asset exists at genre level, reference it; do not copy.

- [ ] **Step 4: Move per-dungeon `assets/` into `dungeons/<name>/assets/`**

Already done in Task 4-6 (dungeon `assets/` moved with the rest of dungeon content). World-level `assets/` directory in Task 3 stays empty until populated by portrait-generation work (separate plan).

- [ ] **Step 5: Verify YAML parses + audio path validity**

```bash
python3 -c "import yaml; yaml.safe_load(open('genre_packs/caverns_and_claudes/worlds/caverns_three_sins/audio.yaml'))"
# If audio.yaml references files, sanity-check they exist:
python3 -c "
import yaml, os
data = yaml.safe_load(open('genre_packs/caverns_and_claudes/worlds/caverns_three_sins/audio.yaml'))
# walk for 'file:' or 'path:' keys (best-effort)
def walk(d, p='root'):
    if isinstance(d, dict):
        for k,v in d.items():
            if k in ('file','path') and isinstance(v,str):
                full = os.path.join('genre_packs/caverns_and_claudes', v)
                if not os.path.exists(full) and not os.path.exists(v):
                    print(f'MISSING: {p}.{k} = {v}')
            else:
                walk(v, f'{p}.{k}')
    elif isinstance(d, list):
        for i, x in enumerate(d):
            walk(x, f'{p}[{i}]')
walk(data)
print('done')
"
```

- [ ] **Step 6: Commit**

```bash
git add genre_packs/caverns_and_claudes/worlds/caverns_three_sins/audio.yaml \
        genre_packs/caverns_and_claudes/worlds/caverns_three_sins/audio \
        genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/*/audio
git commit -m "feat(caverns): consolidate audio.yaml + audio/ assets

World-level audio.yaml inherits from genre-level. Per-dungeon audio assets
relocated under dungeons/<name>/audio/. Sünden hamlet cues at world level."
```

---

## Task 18: Update `portrait_manifest.yaml`

**Files:**
- Create: `worlds/caverns_three_sins/portrait_manifest.yaml`
- Reads: three source `worlds/<name>/portrait_manifest.yaml` files. Their contents (the per-dungeon NPCs like Falk Stonehelm, Wren Peatford) move to per-dungeon `portrait_manifest.yaml` files in dungeons/<name>/.

**Schema (match existing `worlds/grimvault/portrait_manifest.yaml`):**
- Top-level `characters:` list.
- Each: `name`, `role`, `type` (npc_major/npc_minor/etc.), `appearance` (long string, Flux prompt material), `culture_aesthetic` (long string).

**Strategy:**
1. Move per-dungeon NPC portrait entries (Falk, Wren, Hoarder-side townsfolk, Mawdeep townsfolk) into `dungeons/<name>/portrait_manifest.yaml` so they live alongside the dungeon they belong to.
2. World-level `portrait_manifest.yaml` lists the **Sünden cast** — the 6-10 named recurring NPCs from `hamlet.yaml` (Task 19). Author Flux-style appearance prompts for each.
3. Existing Sünden NPC portraits don't exist yet — they're net-new authoring with the rest of the Sünden cast.

- [ ] **Step 1: Move per-dungeon NPC portrait entries**

Read each source `worlds/<name>/portrait_manifest.yaml`. Split entries: NPCs that are clearly Ashgate/Copperbridge/Gristwell-resident go into `dungeons/<name>/portrait_manifest.yaml` (new file per dungeon). NPCs that should be Sünden-resident (rare — most are local) go into the world-level file.

- [ ] **Step 2: Author world-level `portrait_manifest.yaml` with Sünden cast**

Cross-reference Task 19's `hamlet.yaml` named NPC list (this task and Task 19 may need to alternate — author hamlet.yaml first if names aren't yet locked).

For each Sünden NPC: name, role (e.g. "Wall-keeper at the monument"), type (npc_major), appearance (Flux prompt — clothing, posture, scene context, B&W ink consistent), culture_aesthetic.

- [ ] **Step 3: Verify YAML parses**

```bash
for f in genre_packs/caverns_and_claudes/worlds/caverns_three_sins/portrait_manifest.yaml \
         genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/*/portrait_manifest.yaml; do
  python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" "$f" || echo "FAIL: $f"
done
```

- [ ] **Step 4: Commit**

```bash
git add genre_packs/caverns_and_claudes/worlds/caverns_three_sins/portrait_manifest.yaml \
        genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/*/portrait_manifest.yaml
git commit -m "feat(caverns): split portrait_manifest by location

Per-dungeon NPCs (Falk, Wren, Hoarder-side, Mawdeep-side) live in
dungeons/<name>/portrait_manifest.yaml. World-level file lists the new
Sünden cast cross-referenced with hamlet.yaml (Task 19)."
```

---

## Task 19: Author `hamlet.yaml` — Sünden, NPCs, services, the Wall

**Files:**
- Create: `worlds/caverns_three_sins/hamlet.yaml`

This is the **biggest creative authoring task**. Plan to spend real time. The Hamlet is the campaign's home — its texture is what makes the world feel alive.

**Schema (PROPOSED — author this file establishing the schema):**

```yaml
# Sünden — the Hamlet at the center of three sins.
# This file describes the persistent town: POIs, named NPCs, the three
# stress-relief services, and the Wall (campaign memory monument).

name: "Sünden"
slug: sunden
description: >-
  ~300 words. Sünden is the only inhabited point at the regional center.
  Three dungeon entrances visible from the upper terraces. The town's
  character: weathered limestone, lived-in but never at ease, the kind
  of place that knows it's the seam where three bad things almost meet.
  Founded by who, sustained by who, what its rhythms look like.

geography: >-
  ~150 words. Layout: town square at center, market alley, the Wall
  along the north face, the three service-houses arranged around the
  square (Confessional / Workhouse / Masquerade), the recruiter's
  posting at the south edge, three roads out toward the three approaches.

# ─── POIs ───
points_of_interest:
  - name: Sünden Square
    slug: sunden_square
    type: settlement
    description: >-
      The town's heart. Where the party arrives. Where the Wall stands.
      What's there, what's missing, what the cobblestones have seen.
  - name: The Wall
    slug: the_wall
    type: monument
    description: >-
      A stone wall along the north face of the square. Names carved.
      Successful delves on one side, cenotaphs on the other. Maintained
      by [a Sünden faction — cross-ref factions.yaml]. The narrator
      pulls Wall entries via the engine prompt-zone.
  - name: The Recruiter's Post
    slug: recruiters_post
    type: service
    description: >-
      Where new hirelings are presented. Run by [named NPC]. The board
      lists the current roster, days available, and which sin each
      candidate's archetype points toward.
  - name: The Confessional
    slug: the_confessional
    type: stress_service
    cures: greed_stress
    cost: scaled_currency
    description: >-
      A small room with a screen and a bench. The hireling gives away
      currency to the poor through the screen. Cost scales with current
      wealth — the more they have, the more they give. Best at curing
      stress accrued from Horden delves (greed-touched).
  - name: The Workhouse
    slug: the_workhouse
    type: stress_service
    cures: gluttony_stress
    cost: time
    description: >-
      A barn-shaped building where hirelings labor for a delve-tick.
      Bread baked, stones split, fields turned. Cost is time, not
      money. Best at curing stress accrued from Mawdeep delves.
  - name: The Masquerade
    slug: the_masquerade
    type: stress_service
    cures: pride_stress
    cost: identity_risk
    description: >-
      A festival hall. Hireling adopts a false identity at a town
      festival. There is a small chance the false identity STICKS
      and overwrites a flavor trait permanently. Best at curing
      stress accrued from Grimvault delves.
  - name: The Spillway (or rename — check banned words)
    slug: the_spillway
    type: tavern
    description: >-
      The town's tavern. Where hirelings between delves drink and
      tell stories. The narrator pulls flavor here.

# ─── NPCs (named, recurring; 6-10) ───
recurring_npcs:
  - name: <name>
    role: recruiter
    description: >-
      ~80 words. Voice, age, history, what they know about hirelings,
      a quirk the narrator can lean on.
  - name: <name>
    role: wall_keeper
    description: ~80 words.
  - name: <name>
    role: confessional_keeper
    description: ~80 words.
  - name: <name>
    role: workhouse_master
    description: ~80 words.
  - name: <name>
    role: masquerade_host
    description: ~80 words.
  - name: <name>
    role: innkeeper
    description: ~80 words. Runs the Spillway-equivalent.
  - name: <name>
    role: market_vendor
    description: ~80 words.
  - name: <name>
    role: itinerant_preacher
    description: ~80 words. Speaks of the four absent sins; warns that
    they will wake.

# ─── The Wall ───
wall:
  description: >-
    Physical description matching the POI entry above. The mechanics
    are owned by the engine plan; this entry is content.
  carving_style: >-
    How names are carved (chisel, scroll-script, blocked initials,
    whatever fits the world). What distinguishes a victory entry
    from a cenotaph.
  empty_columns: >-
    Four blank columns reserved for the absent sins (Wrath, Sloth,
    Lust, Envy) — visible space for stories not yet told.
```

**Authoring constraints:**
- Banned words (per memory): Reach, Veil, Spire, Hollow (suffix), Mire, Shroud, Sanctum, Bastion. Check final.
- The Hamlet name **Sünden** is locked (German for "sins").
- NPC names should not pattern-match obvious fantasy clichés. Lean unfamiliar, slightly archaic. Plausible to all three players (Keith, James, Sebastien) and not jarring for Alex.
- The three stress services map to virtues opposing each sin (per spec):
  - Confessional → Generosity (vs. Greed) → cures greed_stress best.
  - Workhouse → Temperance (vs. Gluttony) → cures gluttony_stress best.
  - Masquerade → Humility (vs. Pride) → cures pride_stress best.

- [ ] **Step 1: Read the spec section "Sünden — the Hamlet" carefully**

```bash
sed -n '/^## Sünden/,/^##[^#]/p' ../docs/superpowers/specs/2026-05-04-caverns-claudes-hub-design.md
# or just open the file
```

- [ ] **Step 2: Lock the Sünden NPC names**

Author 6-10 names. Avoid the banned-word list. Avoid generic-fantasy-name pattern-matching. Cross-check each against grep for clichés:

```bash
echo "<name candidates>" | grep -wEi "Reach|Veil|Spire|Hollow|Mire|Shroud|Sanctum|Bastion"
# Expected: no matches
```

- [ ] **Step 3: Author hamlet.yaml**

Follow the schema above. Each NPC entry ~80 words. Each POI entry tight enough that a narrator can riff. Square description ~300 words.

- [ ] **Step 4: Verify YAML parses + banned words**

```bash
python3 -c "import yaml; yaml.safe_load(open('genre_packs/caverns_and_claudes/worlds/caverns_three_sins/hamlet.yaml'))"
grep -wEi "Reach|Veil|Spire|Hollow|Mire|Shroud|Sanctum|Bastion" \
  genre_packs/caverns_and_claudes/worlds/caverns_three_sins/hamlet.yaml \
  || echo "OK no banned words"
```

- [ ] **Step 5: Commit**

```bash
git add genre_packs/caverns_and_claudes/worlds/caverns_three_sins/hamlet.yaml
git commit -m "feat(caverns): author Sünden hamlet.yaml

Sünden POIs (square, Wall, recruiter's post, three stress services,
tavern), 6-10 named recurring NPCs, three stress services keyed to
opposing virtues (Confessional/Workhouse/Masquerade vs Greed/Gluttony/
Pride), the Wall as monument with four empty columns reserved for the
absent sins."
```

---

## Task 20: Replace `world.yaml` placeholder with full description

**Files:**
- Modify: `worlds/caverns_three_sins/world.yaml`

The placeholder from Task 3 satisfies YAML parsing but doesn't carry real content. Replace it now that hamlet.yaml + lore.yaml + history.yaml are in place.

**Schema (match existing per-dungeon `world.yaml`, with these differences):**
- **NO** `keeper:` block (Keepers live in dungeons).
- **YES** `cover_poi: sunden_square` (or whichever Sünden POI is the cover).
- **YES** `axis_snapshot` — averaged across the three sins, slightly tempered toward the Hamlet's lived-in tone.
- **NEW** `dungeons:` field listing the three dungeon slugs (purely informational; the loader walks the directory regardless).

```yaml
cover_poi: sunden_square
name: "Hamlet of Sünden"
description: >-
  ~250 words. Pull from spec §"Concept" and §"Sünden — the Hamlet".
  Three of the Seven Deadly Sins woke up close together; Sünden sits
  at their center. Three dungeons reachable from the Hamlet:
  Grimvault (Pride), Horden (Greed), Mawdeep (Gluttony). The four
  absent sins are stories told elsewhere.

tagline: "Three sins. One town. Send your hirelings down."

axis_snapshot:
  comedy: 0.25         # tempered down from per-dungeon avg toward Hamlet warmth
  gravity: 0.85        # campaign-level weight; deeper than any single dungeon
  outlook: 0.4         # slightly more hope than any single sin

# Informational; loader walks dungeons/ regardless.
dungeons:
  - grimvault
  - horden
  - mawdeep

# No keeper: block at world level. Keepers live in dungeons/<name>/dungeon.yaml.
```

- [ ] **Step 1: Replace the placeholder**

- [ ] **Step 2: Verify YAML parses**

```bash
python3 -c "import yaml; yaml.safe_load(open('genre_packs/caverns_and_claudes/worlds/caverns_three_sins/world.yaml'))"
```

- [ ] **Step 3: Commit**

```bash
git add genre_packs/caverns_and_claudes/worlds/caverns_three_sins/world.yaml
git commit -m "feat(caverns): finalize caverns_three_sins/world.yaml

Replaces placeholder. Description, tagline, axis_snapshot, dungeons list.
No keeper at world level — Keepers live in dungeons/<name>/dungeon.yaml."
```

---

## Task 21: Delete original `grimvault/` `horden/` `mawdeep/` directories

By this point, every load-bearing file has been moved or merged. The original directories should contain only files whose content has been folded elsewhere.

- [ ] **Step 1: Audit what's left in each source directory**

```bash
cd sidequest-content
for d in grimvault horden mawdeep; do
  echo "=== $d ==="
  ls genre_packs/caverns_and_claudes/worlds/$d/
done
# Expected leftovers (these were merged, not moved): archetypes.yaml,
# archetype_funnels.yaml, history.yaml, lore.yaml, pacing.yaml,
# portrait_manifest.yaml, world.yaml.
# Anything ELSE is a sign that Task 4-6 didn't move it.
```

- [ ] **Step 2: Verify all leftover content has been folded**

For each leftover file, confirm its content has been merged into the corresponding `worlds/caverns_three_sins/...` file (lore → lore, history → history, archetypes → merged archetypes). If any content was missed, **STOP** — go back to the relevant task.

- [ ] **Step 3: Delete the three directories**

```bash
git rm -r genre_packs/caverns_and_claudes/worlds/grimvault
git rm -r genre_packs/caverns_and_claudes/worlds/horden
git rm -r genre_packs/caverns_and_claudes/worlds/mawdeep
```

- [ ] **Step 4: Verify final structure**

```bash
ls genre_packs/caverns_and_claudes/worlds/
# Expected: caverns_three_sins
ls genre_packs/caverns_and_claudes/worlds/caverns_three_sins/dungeons/
# Expected: grimvault horden mawdeep
```

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(caverns): remove original grimvault/horden/mawdeep dirs

All content has been folded into caverns_three_sins/ — per-dungeon files
under dungeons/<name>/, world-level lore/history/archetypes merged at
the hub. The four-world layout is now one hub world + three dungeons."
```

---

## Task 22: Validation pass

**What's achievable without the engine plan:**
- ✅ YAML schema sanity (every file parses, every required field present).
- ✅ No banned words in authored prose.
- ✅ No broken cross-references between files (NPC names match between hamlet.yaml and portrait_manifest.yaml, faction references resolve).
- ❌ Loader integration (gated by engine plan).
- ❌ Pack loading in server (gated by engine plan).
- ❌ Server unit tests for loader (gated by engine plan).

- [ ] **Step 1: Run YAML parse over the entire new world**

```bash
cd sidequest-content
fail=0
for f in $(find genre_packs/caverns_and_claudes/worlds/caverns_three_sins -name '*.yaml'); do
  python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" "$f" 2>&1 \
    || { echo "FAIL: $f"; fail=1; }
done
[ $fail -eq 0 ] && echo "ALL YAML OK" || echo "FAILURES PRESENT"
```

- [ ] **Step 2: Banned-words sweep across all authored prose**

```bash
grep -rwEi "Reach|Veil|Spire|Hollow|Mire|Shroud|Sanctum|Bastion" \
  genre_packs/caverns_and_claudes/worlds/caverns_three_sins/ \
  --include='*.yaml' \
  || echo "OK no banned words"
```

If matches show up, **review each one** — some legitimate uses might exist (e.g. a place name authored deliberately). Override only with clear intent.

- [ ] **Step 3: Cross-reference NPC names: hamlet.yaml ↔ portrait_manifest.yaml ↔ factions.yaml**

```bash
python3 << 'EOF'
import yaml
hamlet = yaml.safe_load(open('genre_packs/caverns_and_claudes/worlds/caverns_three_sins/hamlet.yaml'))
portraits = yaml.safe_load(open('genre_packs/caverns_and_claudes/worlds/caverns_three_sins/portrait_manifest.yaml'))
factions = yaml.safe_load(open('genre_packs/caverns_and_claudes/worlds/caverns_three_sins/factions.yaml'))

hamlet_npcs = {n['name'] for n in hamlet.get('recurring_npcs',[])}
portrait_chars = {c['name'] for c in portraits.get('characters',[])}
faction_npcs = set()
for f in factions.get('factions',[]):
    for n in f.get('key_npcs', []):
        faction_npcs.add(n['name'])

missing_portraits = hamlet_npcs - portrait_chars
print(f'hamlet NPCs without portrait entry: {missing_portraits or "(none)"}')

extra_portraits = portrait_chars - hamlet_npcs - faction_npcs
print(f'portrait entries not in hamlet or factions (could be per-dungeon NPCs — expected): {extra_portraits or "(none)"}')
EOF
```

- [ ] **Step 4: Try the validate CLI (will likely fail loader checks, but YAML-syntax checks should pass)**

```bash
cd ../sidequest-server
SIDEQUEST_GENRE_PACKS=../sidequest-content/genre_packs uv run python -m sidequest.cli.validate 2>&1 | tee /tmp/caverns_validate.log
```

Expected outcome **before engine plan ships**: validate fails on loader checks (e.g. "no world.yaml found" or "unknown directory dungeons/"). YAML-syntax errors should NOT appear. If YAML-syntax errors appear, fix them before continuing.

- [ ] **Step 5: Commit any fixes from steps 1-3**

```bash
git add -A
git commit -m "chore(caverns): fix validation issues from Task 22 sweep

YAML parse / banned words / NPC cross-reference fixes." || echo "nothing to commit"
```

---

## Task 23: Push branch + open draft PR (gated on engine plan)

**Final step.** The branch is content-complete but cannot be merged until the loader plan ships. Open a draft PR so the work is visible and reviewable.

- [ ] **Step 1: Push the branch**

```bash
cd sidequest-content
git push -u origin feat/caverns-three-sins-content
```

- [ ] **Step 2: Open a DRAFT PR against `develop`**

Per memory `feedback_gitflow_content.md`: sidequest-content uses gitflow → PR base is `develop`, NOT `main`.

```bash
gh pr create --draft --base develop --title "Caverns & Claudes: Hamlet of Sünden — content restructure" --body "$(cat <<'EOF'
## Summary
- Drops `dungeon_survivor/` and `primetime/` worlds.
- Merges `grimvault/`, `horden/`, `mawdeep/` into one hub world `caverns_three_sins/` with three dungeons under `dungeons/<name>/`.
- Adds the Hamlet of **Sünden** with 6-10 named recurring NPCs, three stress-relief services keyed to opposing virtues (Confessional/Workhouse/Masquerade), and the Wall (campaign memory monument).
- Reframes the three Keepers as Deadly Sins: **Pride** (Patient Butcher), **Greed** (Hoarder), **Gluttony** (Glutton Below). The other four sins are stories told elsewhere.
- Adds per-dungeon `drift_profile.yaml` (how Sünden NPCs read post-delve), `wound_profile.yaml` (post-boss-delve transformation), and `approach.yaml` (the demoted dungeon-mouth town).

## ⚠️ DRAFT — DO NOT MERGE YET
Per the design spec (`docs/superpowers/specs/2026-05-04-caverns-claudes-hub-design.md`), this content is paired with engine work that is **a separate plan**. Specifically, the genre-pack loader does not yet recurse into `dungeons/<name>/` and does not recognize `dungeon.yaml` as a slim variant of `world.yaml`. Until that loader change ships:
- The pack will fail server-side validation.
- The world will not appear correctly in the world picker.

This PR stays as a draft until the loader plan ships and the two are validated together.

## Test plan
- [ ] All YAML files parse cleanly (Task 22 step 1 — done).
- [ ] No banned words in authored prose (Task 22 step 2 — done).
- [ ] NPC cross-references valid (Task 22 step 3 — done).
- [ ] Once the loader plan lands: full `pf validate` pass.
- [ ] Once the loader plan lands: `just server-test` passes.
- [ ] Once UI dungeon-pick lands: manual playtest of a delve from Sünden.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 3: Note next plans needed in PR description**

After PR is opened, comment on it linking to the engine plan once that plan exists. The two should land together when both are reviewed.

---

## Self-Review Notes

After writing this plan, I checked the spec section-by-section. Coverage:

| Spec section | Plan task(s) |
|---|---|
| Drop dungeon_survivor + primetime | Task 2 |
| `caverns_three_sins/` directory + new files | Task 3, 11-19 |
| Per-dungeon relocation + slim `dungeon.yaml` | Task 4-6 |
| `dungeons/<name>/drift_profile.yaml` | Task 7 |
| `dungeons/<name>/wound_profile.yaml` | Task 8 |
| `dungeons/<name>/approach.yaml` | Task 9 |
| World-level archetypes merge | Task 10 |
| Regional lore/history/legends/factions | Task 11-14 |
| World-level visual_style/pacing/audio/portraits | Task 15-18 |
| Sünden hamlet.yaml | Task 19 |
| Final world.yaml | Task 20 |
| Delete originals | Task 21 |
| Validation | Task 22 |
| PR | Task 23 |
| **Engine items (loader, persistence, stress, UI, drift/wound/wall consumption)** | **NOT IN THIS PLAN** — separate plans, called out at top |

No placeholders found. No "TBD" / "Similar to Task N". All code blocks have actual content. NPC names left for the engineer (Task 19) — that's the work itself, not a placeholder.

Type consistency: `dungeon` slug used throughout (lowercased: grimvault/horden/mawdeep). `sin` enum is `pride|greed|gluttony` everywhere. World name is `caverns_three_sins` everywhere. Hamlet name is `Sünden`/`sunden` consistently.
