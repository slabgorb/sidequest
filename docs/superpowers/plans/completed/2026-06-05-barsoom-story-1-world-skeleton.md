# Barsoom — Story 1: World Skeleton + Red/Green Core — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Author a faithful, *playable* first cut of the `barsoom` world under the `heavy_metal` genre pack — the red/green Martian core anchored on Helium and the dead sea bottoms, with the Frazetta visual override — gated by the real content loader.

**Architecture:** Pure **content authoring** in `sidequest-content` (no engine change — `heavy_metal` already loads through `get_ruleset_module("wwn")`). All files live under `genre_packs/heavy_metal/worlds/barsoom/` except the two naming corpora under `corpus/shared/`. The world ships `draft: true` until assets land (Story 6), so it is intentionally hidden from selection but must still load clean. The **verification gate is the loader and the namegen CLI**, not pytest — `validate pack` PASS is *not* proof a world loads (it misses enum fields, draft-skip, and the unified Opening schema).

**Tech Stack:** YAML content; `corpus/shared/*.txt` Markov seed lists (ADR-091); the Python server's genre loader + namegen CLI as the verification harness.

**Spec:** `docs/superpowers/specs/2026-06-05-barsoom-heavy-metal-world-design.md` (read it — it carries the peoples roster, faction map, magic framing, visual prompts, and the crunch flags this plan does NOT resolve).

**Reference world to mirror (same genre):** `genre_packs/heavy_metal/worlds/evropi/` — copy its file shapes exactly.

---

## File Structure (Story 1)

Create, all under `genre_packs/heavy_metal/worlds/barsoom/` unless noted:

| File | Responsibility |
|------|----------------|
| `world.yaml` | World manifest: slug, `draft: true`, `axis_snapshot`, Helium anchor, `cover_poi`, `extensions`. |
| `cartography.yaml` | Region graph: the dead-sea-bottom frontier + the red city region (Helium). `navigation_mode: region`. |
| `cultures/red_martian.yaml` | Red-Martian culture + naming `slots` bound to the red corpus. |
| `cultures/green_martian.yaml` | Green-Martian culture + naming `slots` bound to the green corpus. |
| `corpus/shared/barsoom_red.txt` (repo root) | Markov seed names, red phonology. |
| `corpus/shared/barsoom_green.txt` (repo root) | Markov seed names, green phonology. |
| `visual_style.yaml` | Frazetta `positive_suffix` (style-only) + Story-1 `visual_tag_overrides`. |
| `lore.yaml` | Narrator-facing factions + geography summary (concrete details, not atmosphere). |
| `history.yaml` | Eras (dying Mars) + `points_of_interest` incl. the hero POI whose `slug` == `cover_poi`. |
| `npcs.yaml` | `authored_npcs` with Living-World goals (the *wired* world-NPC path). |
| `openings.yaml` | Unified Opening schema: solo + MP, per-origin variants. |

**Out of scope (later stories, do NOT author here):** `cast_spell`/magic content & the `magic` extension (Story 4); the Earthman origin trait, green four-arm physiology, archetype_funnels & caster traditions (Story 5 — all blocked on Keith crunch calls); the southern/northern/Lothar regions (Stories 2–3); rendered assets (Story 6).

---

### Task 1: World manifest — `world.yaml`

**Files:**
- Create: `genre_packs/heavy_metal/worlds/barsoom/world.yaml`

- [ ] **Step 1: Author the manifest.** Mirror `worlds/evropi/world.yaml` exactly; `axis_snapshot` uses the three keys the loader reads (`hope`/`tech_level`/`weirdness`), NOT the genre tone-axes.

```yaml
name: Barsoom
slug: barsoom
draft: true            # hidden from selection until assets land (Story 6)
cover_poi: dead_sea_bottom_of_korad   # MUST equal a points_of_interest slug in history.yaml (Task 7)
description: >-
  A dying world of ochre sea-bottoms where the oceans drained an age
  ago and the cities of a vanished green-skied paradise stand as
  marble ruins in the moss. The copper-skinned red men hold their
  scarlet tower-cities — Helium first among them, and Helium's jealous
  rival Zodanga — by the long-sword and a code of honor older than
  their thousand-year lives. Out on the cracked sea-floor the
  fifteen-foot, four-armed green hordes ride their war-mounts between
  the dead cities, warring on each other and on every red city they
  can reach. The whole planet breathes only because a single great
  Atmosphere Plant still turns, far out on the desert, and no one
  alive remembers how to build another. It is a world ending — and a
  world worth a sword raised to save it.
tagline: "A dying world worth the blade raised to save it."
axis_snapshot:
  hope: 0.7
  tech_level: 0.4
  weirdness: 0.7
starting_location: "The Greater Helium landing-stage, beneath the scarlet tower of the twin city"
starting_region: helium
starting_time: "morning"
extensions:
  - archetype_funnels
```

- [ ] **Step 2: Verify it parses as YAML.**

Run: `cd sidequest-content && python3 -c "import yaml,sys; yaml.safe_load(open('genre_packs/heavy_metal/worlds/barsoom/world.yaml')); print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit.**

```bash
git add genre_packs/heavy_metal/worlds/barsoom/world.yaml
git commit -m "content(barsoom): world manifest skeleton (draft, Helium anchor)"
```

---

### Task 2: Region graph — `cartography.yaml`

**Files:**
- Create: `genre_packs/heavy_metal/worlds/barsoom/cartography.yaml`

- [ ] **Step 1: Author two regions.** Mirror `worlds/evropi/cartography.yaml`. `starting_region` MUST match `world.yaml` (`helium`). The dead-sea-bottom region is the Earthman/green opening zone; Helium is the civilized anchor.

```yaml
world_name: Barsoom
starting_region: helium
navigation_mode: region

map_style: >-
  Hand-painted antique planetary chart on aged ochre parchment — a
  dry dead world of cracked sea-bottoms in pale yellow-green moss,
  scarlet city-glyphs ringed by canal lines ruled dead straight
  across the desert, the great drained ocean basins shaded in faded
  umber, a compass rose with two small moons in the corner, sword-and
  -airship marginalia. Sun-baked palette, no green seas. Style
  reference: heroic sword-and-planet endpaper maps.
map_resolution: [1280, 1024]

regions:
  helium:
    name: Helium
    summary: "The twin scarlet tower-cities of the red empire — honor, fliers, and the long-sword"
    description: >-
      Greater and Lesser Helium, two cities of soaring scarlet and
      crimson towers a few miles apart on the high desert, joined by
      a ruled canal and by the navy of fliers that is the empire's
      pride. This is the most civilized power of the red world —
      jealous of its honor, generous to a guest who keeps the code,
      lethal to one who breaks it. Its workshops cut radium and its
      academies still read the old science, but a Heliumetic settles
      a quarrel with a blade. Beyond the cultivated canal-belt the
      ochre desert begins at once.
    terrain: red_city
    adjacent: [korad_dead_sea_bottom]
    tags: [civilized, red_martian, honor-bound]

  korad_dead_sea_bottom:
    name: The Dead Sea Bottom of Korad
    summary: "Cracked ochre sea-floor and a marble dead city — green hordes, raiders, ruins"
    description: >-
      A vast plain of dried sea-floor, cracked ochre clay furred with
      pale yellow moss, running to low red hills under a thin clear
      sky. At its heart stand the toppled marble colonnades and broken
      dome of Korad, one of the thousands of dead cities the vanished
      ocean left behind. The green hordes camp in the ruins between
      their wars, riding their eight-legged war-mounts across the
      bottom; a lone traveller out here is prey, salvage, or sport.
      The air is thin and the light is hard.
    terrain: dead_sea_bottom
    adjacent: [helium]
    tags: [frontier, green_martian, ruins, dangerous]
```

- [ ] **Step 2: Verify YAML + region/anchor consistency.**

Run: `cd sidequest-content && python3 -c "import yaml; d=yaml.safe_load(open('genre_packs/heavy_metal/worlds/barsoom/cartography.yaml')); assert d['starting_region'] in d['regions'], 'anchor region missing'; print('ok', list(d['regions']))"`
Expected: `ok ['helium', 'korad_dead_sea_bottom']`

- [ ] **Step 3: Commit.**

```bash
git add genre_packs/heavy_metal/worlds/barsoom/cartography.yaml
git commit -m "content(barsoom): cartography — Helium + Korad dead-sea-bottom regions"
```

---

### Task 3: Red-Martian culture + corpus

**Files:**
- Create: `corpus/shared/barsoom_red.txt`
- Create: `genre_packs/heavy_metal/worlds/barsoom/cultures/red_martian.yaml`

- [ ] **Step 1: Author the red-Martian name corpus.** Barsoom names are Burroughs-*invented* with a real phonology → conlang Markov (ADR-091), NOT curated real-world word lists. Red names tend to short open syllables, often two words (Tardos Mors, Mors Kajak, Kantos Kan, Dejah Thoris, Carthoris, Thuvia, Tara). Seed the corpus with ~40 representative tokens (one per line) so the Markov chain learns the phonotactics — these are *seed phonology*, not the names that ship:

```
Dejah
Thoris
Tardos
Mors
Kajak
Kantos
Kan
Carthoris
Thuvia
Tara
Llana
Gahan
Sanoma
Tora
Vad
Varo
Valla
Dia
Thuvan
Dihn
Sab
Than
Djor
Kantos
Hor
Vastus
Notan
Zat
Arras
Fal
Sivas
Kar
Komak
Tan
Hadron
Vor
Daj
Nur
An
Pan
Dan
Chee
```

- [ ] **Step 2: Author the culture file.** Mirror `worlds/evropi/cultures/aldkin.yaml`: `name`, `summary`, `description`, `slots`, `person_patterns`, `place_patterns`. Bind `given_name`/`family_name` to the corpus; supply word-list slots for titles/places.

```yaml
name: Red Martian
summary: Copper-skinned oviparous people of the scarlet tower-cities — honor-bound,
  thousand-year-lived, masters of the flier and the long-sword
description: >-
  The dominant humanlike people of the dying world: smooth copper-red
  skin, black hair, an oviparous people who hatch from the egg and
  live near a thousand years if a blade does not find them first. They
  hold the great tower-cities — Helium, Zodanga, Ptarth, Kaol, Dusar —
  and the canal-belts that feed them, and they keep the old science
  enough to fly and to cut radium. But a red Martian's first law is
  honor: a guest is sacred, a given word is a debt, and a quarrel is
  settled with the long-sword, navy or no navy. They are brilliant,
  proud, jealous, and quick to love and to war.
slots:
  given_name:
    corpora:
      - corpus: barsoom_red.txt
        weight: 1.0
    lookback: 3
  family_name:
    corpora:
      - corpus: barsoom_red.txt
        weight: 1.0
    lookback: 3
  rank:
    word_list:
      - Jed
      - Jeddak
      - Dwar
      - Padwar
      - Odwar
      - Panthan
      - Princess
      - Prince
  place_noun:
    word_list:
      - tower
      - canal
      - landing-stage
      - dock
      - court
      - garden
      - way
      - gate
  adjective:
    word_list:
      - scarlet
      - crimson
      - high
      - jeweled
      - far
      - bright
      - ancient
person_patterns:
  - '{given_name} {family_name}'
  - '{given_name} {family_name}, {rank}'
  - '{rank} {given_name}'
place_patterns:
  - '{adjective} {place_noun}'
  - 'the {place_noun} of {given_name}'
```

- [ ] **Step 3: Verify the corpus resolves through namegen.** Use the server namegen CLI (proves the corpus path + culture binding are live — a namegen that emits "Markov"/garbage means the binding is wrong). Set both env vars (the suite throws `MissingDatabaseUrlError` and silently mis-loads packs without them).

Run:
```bash
cd sidequest-server && \
SIDEQUEST_GENRE_PACKS=../sidequest-content/genre_packs \
SIDEQUEST_DATABASE_URL=postgresql://$USER@localhost:5432/sidequest_test \
uv run python -m sidequest.cli.namegen --genre heavy_metal --world barsoom --culture red_martian --count 5
```
Expected: five plausible red-Martian names (two-word, open-syllable), no literal "Markov", no empty output. *(Confirm the exact CLI flag names against `sidequest/cli/namegen.py` — flag spellings may differ; the success criterion is real names out.)*

- [ ] **Step 4: Commit.**

```bash
git add corpus/shared/barsoom_red.txt genre_packs/heavy_metal/worlds/barsoom/cultures/red_martian.yaml
git commit -m "content(barsoom): red-Martian culture + conlang corpus"
```

---

### Task 4: Green-Martian culture + corpus

**Files:**
- Create: `corpus/shared/barsoom_green.txt`
- Create: `genre_packs/heavy_metal/worlds/barsoom/cultures/green_martian.yaml`

- [ ] **Step 1: Author the green corpus.** Harsher phonology than red — heavier consonants, clipped (Tars Tarkas, Tal Hajus, Lorquas Ptomel, Dak Kova, Sola, Sarkoja, Gozava, Hortan Gur). ~40 seed tokens:

```
Tars
Tarkas
Tal
Hajus
Lorquas
Ptomel
Dak
Kova
Sola
Sarkoja
Gozava
Hortan
Gur
Bar
Comas
Mors
Kab
Dula
Tan
Gama
Hal
Gor
Bantor
Han
Var
Sag
Or
Tor
Kantos
Zad
Bal
Tark
Warhoon
Thark
Gol
Dor
Kan
Vas
Nrr
Grl
Brokar
Tordu
```

- [ ] **Step 2: Author the culture file.** Same schema as Task 3.

```yaml
name: Green Martian
summary: Fifteen-foot, four-armed, tusked nomad hordes of the dead sea bottoms —
  communal, loveless by custom, masters of the war-mount
description: >-
  The green hordes are giants of the cracked sea-floor: fifteen feet
  tall, olive-skinned, with a second pair of arms below the first and
  upthrust tusks framing a lipless mouth. They own no cities of their
  own — they camp in the marble ruins the dead ocean left — and they
  hold all property in common, raise their hatchlings communally with
  no knowledge of a mother, and have bred laughter and love out of
  themselves in favor of cruelty and martial discipline. A horde is
  ruled by its largest and most savage; rank is taken by killing the
  holder. They war ceaselessly — Thark against Warhoon, green against
  every red city — and they ride eight-legged war-mounts across the
  bottom. A few, across a long life, learn something their people
  forgot: that a captive can be a friend.
slots:
  given_name:
    corpora:
      - corpus: barsoom_green.txt
        weight: 1.0
    lookback: 3
  family_name:
    corpora:
      - corpus: barsoom_green.txt
        weight: 1.0
    lookback: 3
  rank:
    word_list:
      - Jed
      - Jeddak
      - Chieftain
      - Warrior
      - Lesser Chieftain
  horde:
    word_list:
      - Thark
      - Warhoon
      - Torquas
      - Thurd
  place_noun:
    word_list:
      - ruin
      - incubator
      - bottom
      - camp
      - dead city
      - hall
  adjective:
    word_list:
      - cracked
      - dead
      - ochre
      - silent
      - broken
      - far
person_patterns:
  - '{given_name} {family_name}'
  - '{given_name} {family_name} of the {horde}'
  - '{rank} {given_name}'
place_patterns:
  - '{adjective} {place_noun}'
  - 'the {place_noun} of the {horde}'
```

- [ ] **Step 3: Verify via namegen** (as Task 3, Step 3, with `--culture green_martian`).
Expected: five plausible green-Martian names, harsher register, no "Markov", no empties.

- [ ] **Step 4: Commit.**

```bash
git add corpus/shared/barsoom_green.txt genre_packs/heavy_metal/worlds/barsoom/cultures/green_martian.yaml
git commit -m "content(barsoom): green-Martian culture + conlang corpus"
```

---

### Task 5: Visual override — `visual_style.yaml`

**Files:**
- Create: `genre_packs/heavy_metal/worlds/barsoom/visual_style.yaml`

- [ ] **Step 1: Author the Frazetta override.** `positive_suffix` is **style/medium/palette ONLY** (no setting nouns — per the Z-Image guide they bleed onto every portrait). Add Story-1 `visual_tag_overrides` (replacing the genre's baroque-doom tags, which don't exist on Mars). Mirror the file shape of `worlds/evropi/visual_style.yaml` plus the genre file's `visual_tag_overrides` block.

```yaml
positive_suffix: >-
  heroic sword-and-planet oil painting in the tradition of Frank
  Frazetta, Roy Krenkel, and Michael Whelan, lush painterly brushwork
  and rich tonal modeling, romantic dramatic composition, sun-baked
  palette of ochre and rust-red, pale sea-moss green, bone marble,
  crimson and gold, brass and worn leather, a wan small sun in a clear
  sky shading from rose to violet, hard low-angle light through thin
  air with long shadows and high contrast, vast melancholy-beautiful
  dying-world atmosphere. No text, no caption, no title, no writing,
  no labels, no signature, no watermark, no frame, no border.

preferred_model: dev
base_seed: 233

visual_tag_overrides:
  dead_sea_bottom: >-
    a cracked ochre plain of dried sea-floor furred with pale yellow
    moss, scattered bone-white stones, low red hills on the horizon,
    a vast clear sky shading rose to violet, a wan small sun low and
    hard, long shadows, thin dry air

  red_city_plaza: >-
    a plaza of a red-Martian tower-city — soaring scarlet and crimson
    towers, jeweled domes, ruled canal-water catching the light,
    fliers moored at high landing-stages, ornate but airy stonework,
    hard sun and long shadows

  dead_city_ruin: >-
    the ruins of an ancient marble city on the sea-bottom — toppled
    colonnades and a broken dome half-drowned in ochre moss, dust in
    the hard low light, the bones of a vanished green-skied age

  flier_deck: >-
    the deck of a Martian flier — a long ornate airship hull with a
    carved serpent prow, brass fittings and worn leather rigging,
    moored above a drop, the ochre desert and a rose-violet sky beyond

  thark_camp: >-
    a green-horde camp among marble ruins — eight-legged war-mounts
    picketed in the broken colonnades, harness and weapons of giants,
    cookfires low in the dead city, the cracked ochre bottom stretching
    away under a hard thin sky
```

- [ ] **Step 2: Verify YAML.**

Run: `cd sidequest-content && python3 -c "import yaml; d=yaml.safe_load(open('genre_packs/heavy_metal/worlds/barsoom/visual_style.yaml')); assert 'positive_suffix' in d and d['visual_tag_overrides']; print('ok', list(d['visual_tag_overrides']))"`
Expected: `ok ['dead_sea_bottom', 'red_city_plaza', 'dead_city_ruin', 'flier_deck', 'thark_camp']`

- [ ] **Step 3: Commit.**

```bash
git add genre_packs/heavy_metal/worlds/barsoom/visual_style.yaml
git commit -m "content(barsoom): Frazetta visual override + Story-1 location tags"
```

---

### Task 6: Narrator lore — `lore.yaml`

**Files:**
- Create: `genre_packs/heavy_metal/worlds/barsoom/lore.yaml`

- [ ] **Step 1: Author concrete narrator-facing lore.** Lore feeds the narrator's context — concrete handles, not atmosphere (the OTEL principle: give the narrator facts so it isn't improvising). Mirror `worlds/evropi/lore.yaml` shape. Cover the Story-1 surface only (red empires, green hordes, the Atmosphere Plant, the canal/flier facts, the honor code, the telepathy baseline). Keep the southern/northern cults to one-line "rumored" hooks (authored in Stories 2–3).

```yaml
world_name: Barsoom

factions:
  - name: Helium
    kind: red_empire
    summary: "The first city of the red world — fliers, honor, the long-sword. The PCs' likely home or host."
    goals: ["hold the canal-belt", "out-fly Zodanga", "keep the guest-code"]
  - name: Zodanga
    kind: red_empire
    summary: "Helium's jealous rival — the city of the assassins' guild, where a quarrel is settled by a hired blade in the dark."
    goals: ["undercut Helium", "expand the canal tribute", "deny the assassins exist"]
  - name: The Green Hordes
    kind: green_nomads
    summary: "Thark and Warhoon — fifteen-foot four-armed nomads of the dead sea bottoms, at war with each other and every red city."
    goals: ["take rank by combat", "raid the canal-belt", "hold the dead cities"]

setting_facts:
  - "The oceans drained an age ago; the world is a desert of cracked ochre sea-bottoms furred with pale moss, dotted with thousands of marble dead cities."
  - "The whole planet breathes only because one great Atmosphere Plant still turns, far out on the desert. No one alive can build another. It is the single overdue ledger of the world."
  - "Red cities are fed by ruled canals carrying water from the far poles; outside the canal-belt the desert begins at once."
  - "Fliers — airships buoyed by a repulsion ray — are the navies and the pride of the red empires. The long-sword settles personal honor regardless."
  - "Every Martian reads surface thought unless they shield; a trained mind hides its surface and reads another's. This telepathy is universal and assumed, not a marvel."
  - "Radium ammunition explodes in sunlight; a red Martian's pistol is deadly by day and inert in the dark."

rumored:
  - "Pilgrims who grow old voyage down the River Iss to a southern paradise from which none return. (The truth of the Valley Dor is a southern matter.)"
  - "Bearded yellow men are said to live behind the ice at the north pole, in cities under glass. (A northern matter.)"
  - "An ancient white people in a hidden city are said to conjure armies out of nothing but their minds. (Lothar — a matter for those who reach it.)"
```

- [ ] **Step 2: Verify YAML.**

Run: `cd sidequest-content && python3 -c "import yaml; yaml.safe_load(open('genre_packs/heavy_metal/worlds/barsoom/lore.yaml')); print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit.**

```bash
git add genre_packs/heavy_metal/worlds/barsoom/lore.yaml
git commit -m "content(barsoom): narrator lore — red/green factions, Atmosphere Plant, telepathy baseline"
```

---

### Task 7: History + hero POI — `history.yaml`

**Files:**
- Create: `genre_packs/heavy_metal/worlds/barsoom/history.yaml`

- [ ] **Step 1: Author eras + the hero POI.** Mirror `worlds/evropi/history.yaml`: `world_name`, `overview`, `eras[]`, and a `points_of_interest[]` list. The hero POI's `slug` MUST equal `world.yaml`'s `cover_poi` (`dead_sea_bottom_of_korad`) or the lobby hero-shot 404s. Each POI carries a `visual_prompt.solo` authored to the Z-Image guide (foreground/middle/background, hard thin-air light, the safety clause; archetypes not proper nouns).

```yaml
world_name: Barsoom

overview: >-
  A world in its long ending. An age ago Barsoom had green seas, a
  blue sky, and a white-skinned seafaring people; the oceans drained,
  the sky thinned, and the survivors changed — into the copper red
  men of the tower-cities, the green giants of the dead bottoms, and
  stranger remnants at the poles and in hidden places. The cities of
  the vanished age stand empty as marble ruins in the moss. The living
  world breathes on one failing Atmosphere Plant and the water of two
  poles carried by ruled canals. Honor, the long-sword, and the flier
  hold what is left.

eras:
  - name: The Green-Sea Age
    period: "ages past"
    summary: >-
      Barsoom bears oceans, a blue sky, and a white seafaring people
      whose cities ring the seas. Their science is high; their art
      survives only as the marble bones of dead cities.

  - name: The Draining
    period: "the long drying"
    summary: >-
      The oceans recede over centuries into the deep basins and then
      to nothing. The seafaring cities are left stranded miles inland
      on drying sea-floor. Civilization all but dies; the survivors
      scatter and begin to change.

  - name: The Age of the Red and the Green
    period: "now"
    summary: >-
      The copper red men raise the scarlet tower-cities along the new
      canal-lines and rebuild a science enough to fly. The green
      hordes take the dead bottoms and the ruins. The Atmosphere Plant
      is built to hold the thinning air — and is never matched again.
      This is the world the players walk: dying, brilliant, and at war.

points_of_interest:
  - name: The Dead Sea Bottom of Korad
    slug: dead_sea_bottom_of_korad
    region: korad_dead_sea_bottom
    type: ruin
    description: >-
      A vast plain of cracked ochre sea-floor furred with pale moss,
      running to low red hills. At its heart stand the toppled marble
      colonnades and broken dome of Korad, a dead city of the vanished
      age, now a camp-ground of the green hordes between their wars.
    visual_prompt:
      solo: >-
        heroic sword-and-planet oil painting in the tradition of Frank
        Frazetta and Roy Krenkel, lush painterly brushwork. Wide
        low-angle landscape. Foreground: a cracked ochre plain of dried
        sea-floor scattered with pale yellow moss and bone-white
        stones, a lone armored warrior in crimson-and-brass leather
        harness standing with a long-sword. Middle ground: the ruins
        of an ancient marble city — toppled colonnades and a broken
        dome half-drowned in ochre moss. Background: low red hills
        under a vast clear sky shading rose to violet, a wan small sun
        low on the horizon, two faint small moons. Hard raking light,
        long shadows, high contrast, thin dry air. Vast, romantic,
        melancholy. No text, no caption, no labels, no signature, no
        watermark, no frame.
      backdrop: >-
        cracked ochre sea-bottom and toppled marble ruins under a
        rose-violet sky, a wan low sun, long hard shadows.

  - name: The Greater Helium Landing-Stage
    slug: greater_helium_landing_stage
    region: helium
    type: settlement
    description: >-
      The high mooring-stage beneath the great scarlet tower of
      Greater Helium, where the fliers dock and the city's business
      arrives and departs. Ruled canal-water shines below; the twin
      city stands a few miles off across the desert.
    visual_prompt:
      solo: >-
        heroic sword-and-planet oil painting in the tradition of Frank
        Frazetta and Michael Whelan, lush painterly brushwork. Wide
        view. Foreground: a high stone mooring-stage with an ornate
        airship moored at it, carved serpent prow, brass fittings and
        worn leather rigging, a figure in crimson-and-brass leather
        harness on the deck. Middle ground: soaring scarlet and crimson
        towers and jeweled domes of a tower-city, ruled canal-water
        shining below. Background: the ochre desert and a second
        tower-city far off under a rose-violet sky, a wan low sun. Hard
        light, long shadows, thin clear air. No text, no caption, no
        labels, no signature, no watermark, no frame.
      backdrop: >-
        scarlet towers and jeweled domes above a ruled canal, an
        ornate flier moored, ochre desert and rose-violet sky beyond.
```

- [ ] **Step 2: Verify `cover_poi` linkage.**

Run:
```bash
cd sidequest-content && python3 -c "
import yaml
w=yaml.safe_load(open('genre_packs/heavy_metal/worlds/barsoom/world.yaml'))
h=yaml.safe_load(open('genre_packs/heavy_metal/worlds/barsoom/history.yaml'))
slugs={p['slug'] for p in h['points_of_interest']}
assert w['cover_poi'] in slugs, f\"cover_poi {w['cover_poi']} not in POI slugs {slugs}\"
print('ok cover_poi resolves:', w['cover_poi'])
"
```
Expected: `ok cover_poi resolves: dead_sea_bottom_of_korad`

- [ ] **Step 3: Commit.**

```bash
git add genre_packs/heavy_metal/worlds/barsoom/history.yaml
git commit -m "content(barsoom): history eras + hero POI (cover_poi linkage)"
```

---

### Task 8: Authored NPCs — `npcs.yaml`

**Files:**
- Create: `genre_packs/heavy_metal/worlds/barsoom/npcs.yaml`

- [ ] **Step 1: Author core NPCs with Living-World goals.** `npcs.yaml` is the *wired* world-NPC path (carries Living-World goals; `faction_agendas.yaml` has zero consumers — do NOT use it). Top-level key is `authored_npcs`. Give each a goal/timeline so the narrator has mechanical backing, not improvisation. Mirror `worlds/evropi/npcs.yaml`. These are *original* figures (PCs are the players' own; canonical names like Tars Tarkas stay in history/lore as legend, not as the seated cast).

```yaml
world_name: Barsoom

authored_npcs:
  - id: helium_jed_host
    name: "Kantos Vah"
    culture: red_martian
    role: "A Heliumetic dwar (captain) who vouches for newcomers at the landing-stage"
    location: helium
    disposition: cautious-honorable
    goals:
      - "judge whether the newcomers keep the guest-code"
      - "raise fliers and blades against a coming Zodangan move he can't yet prove"
    timeline: "If the party proves honorable, he offers a commission; if they break the code, he calls a blade-debt."

  - id: zodanga_agent
    name: "Sab Tor"
    culture: red_martian
    role: "A quiet Zodangan in Helium who is not what his papers say"
    location: helium
    disposition: smiling-false
    goals:
      - "learn Helium's flier dispositions"
      - "turn or remove anyone who notices him — by the guild, never by his own hand"
    timeline: "Advances whether or not the party engages; the canal tribute talks are his clock."

  - id: thark_chieftain
    name: "Gor Hajus"
    culture: green_martian
    role: "A lesser chieftain of the Thark horde camped in Korad's ruins"
    location: korad_dead_sea_bottom
    disposition: cruel-curious
    goals:
      - "take rank by killing the holder above him"
      - "decide whether a captive is sport, salvage, or — rarely — a thing worth keeping alive"
    timeline: "His challenge for rank comes whether or not the party is present; a captive who shows courage can change his calculus."
```

- [ ] **Step 2: Verify YAML + key shape.**

Run: `cd sidequest-content && python3 -c "import yaml; d=yaml.safe_load(open('genre_packs/heavy_metal/worlds/barsoom/npcs.yaml')); assert d['authored_npcs'] and all('goals' in n for n in d['authored_npcs']); print('ok', [n['id'] for n in d['authored_npcs']])"`
Expected: `ok ['helium_jed_host', 'zodanga_agent', 'thark_chieftain']`

- [ ] **Step 3: Commit.**

```bash
git add genre_packs/heavy_metal/worlds/barsoom/npcs.yaml
git commit -m "content(barsoom): authored NPCs with Living-World goals"
```

---

### Task 9: Openings — `openings.yaml`

**Files:**
- Create: `genre_packs/heavy_metal/worlds/barsoom/openings.yaml`

- [ ] **Step 1: Author the unified Opening schema** (NOT the simple genre shape — the loader needs `triggers.mode`, `establishing_narration`, `first_turn_invitation`, or it parses hollow). Mirror `worlds/evropi/openings.yaml`. Provide solo + MP, per-origin variants: the Earthman waking on the dead sea bottom (solo, the iconic arrival), a red-Martian at the Helium landing-stage (either), and a multiplayer table convened at Helium.

```yaml
version: "0.1.0"
world: barsoom
genre: heavy_metal

openings:
  - id: earthman_dead_sea_arrival
    name: "The Dead Sea Bottom — A Stranger Wakes"
    triggers:
      mode: solo
      backgrounds: []
    setting:
      location_label: "The cracked sea-bottom near the dead city of Korad"
    tone:
      register: vast, disorienting, wondrous-then-dangerous
      avoid_at_all_costs:
        - explaining the planet to the player as exposition
        - a friendly guide arriving to narrate the rules
        - softening the immediate danger of the green camp nearby
    establishing_narration: >-
      You wake on cracked ochre ground under a sky the wrong color,
      the air thin and cold in your chest, your own body suddenly
      strange — light, springy, as if the ground wants to throw you
      at the sky. A few hundred yards off, among toppled marble
      columns, something enormous moves: a camp of fifteen-foot
      figures and eight-legged mounts. You are naked, unarmed, and
      newly, impossibly strong. They have not seen you yet.
    first_turn_invitation: >-
      The moss under your hands is real, the cold is real, and the
      giants in the ruins are real. Your first careless step nearly
      launches you off your feet — whatever world this is, it holds
      you lighter than the one you left. The nearest column is twenty
      yards. The camp is a hundred. Nothing here is waiting for you to
      be ready.

  - id: helium_landing_stage
    name: "Greater Helium — The Landing-Stage"
    triggers:
      mode: either
      backgrounds: []
    setting:
      location_label: "The high mooring-stage of Greater Helium"
    tone:
      register: proud, formal, honor-bound
      avoid_at_all_costs:
        - tavern-style quest boards
        - NPCs who trust strangers instantly
        - treating Helium as a generic fantasy city
    establishing_narration: >-
      A flier has set you down on the high stage beneath the great
      scarlet tower of Greater Helium, where the dwar Kantos Vah is
      taking the measure of new arrivals — not rudely, but completely,
      the way an honorable man weighs a stranger he may have to trust
      with a blade at his back. The canal shines far below. A Zodangan
      with very correct papers is also on the stage, and is also being
      weighed, and is enjoying it more than he should.
    first_turn_invitation: >-
      The wind off the desert is thin and hard at this height. Kantos
      Vah stands with one hand resting on the hilt of a long-sword he
      has clearly used, his copper face unreadable, waiting to hear
      how you account for yourself. The smiling man a few steps away
      lets you go first.

  - id: helium_table_convened
    name: "Greater Helium — A Common Cause"
    triggers:
      mode: multiplayer
      backgrounds: []
      min_players: 2
      max_players: 6
    setting:
      location_label: "A high chamber of the scarlet tower, Greater Helium"
    tone:
      register: formal, urgent, honor-bound
      avoid_at_all_costs:
        - a single NPC monologuing the mission
        - forcing the party to already know each other
        - softening the stakes of the canal-tribute crisis
    establishing_narration: >-
      You have each been summoned to a high chamber of the scarlet
      tower for reasons that are about to become one reason. The
      canal-tribute talks with Zodanga have gone wrong; a flier is
      overdue; and the dwar Kantos Vah has decided he would rather
      trust an untried band that owes the city nothing than the court
      factions that owe it everything. He has not told you yet that
      you are now, collectively, his unprovable suspicion made flesh.
    first_turn_invitation: >-
      The chamber is tall and scarlet and very quiet. Kantos Vah looks
      from one of you to the next, taking your measure as a group the
      way he would a hand of cards he did not deal. Then he says that
      what he is about to say does not leave this room, and waits to
      see which of you answers first.
```

- [ ] **Step 2: Verify schema completeness (the loader's real gate).**

Run:
```bash
cd sidequest-content && python3 -c "
import yaml
d=yaml.safe_load(open('genre_packs/heavy_metal/worlds/barsoom/openings.yaml'))
ops=d['openings']
modes={o['triggers']['mode'] for o in ops}
assert {'solo','multiplayer'} & modes or 'either' in modes, 'need solo+MP coverage'
for o in ops:
    assert o.get('establishing_narration') and o.get('first_turn_invitation'), f\"{o['id']} missing unified-schema fields\"
print('ok', [o['id'] for o in ops], 'modes:', modes)
"
```
Expected: `ok [...] modes: {'solo', 'either', 'multiplayer'}`

- [ ] **Step 3: Commit.**

```bash
git add genre_packs/heavy_metal/worlds/barsoom/openings.yaml
git commit -m "content(barsoom): unified openings — solo Earthman arrival + Helium solo/MP"
```

---

### Task 10: The real gate — full loader + reference page

**Files:** none (verification only).

- [ ] **Step 1: Load the pack the way the running game does.** `validate pack` PASS is not proof; `load_genre_pack` is. Confirm `barsoom` is enumerated by the world list and that it is **intentionally** `draft`-skipped from *selection* but still loads without error (a `draft:true` world that silently fails to load looks identical to one correctly hidden — distinguish them).

Run (confirm the exact loader entry against `sidequest/genre/loader.py`; this is the shape):
```bash
cd sidequest-server && \
SIDEQUEST_GENRE_PACKS=../sidequest-content/genre_packs \
SIDEQUEST_DATABASE_URL=postgresql://$USER@localhost:5432/sidequest_test \
uv run python -c "
from sidequest.genre.loader import load_genre_pack
pack = load_genre_pack('heavy_metal')
worlds = {w.slug: w for w in pack.worlds}
assert 'barsoom' in worlds, f'barsoom did not load; got {list(worlds)}'
b = worlds['barsoom']
assert getattr(b, 'draft', False) is True, 'expected draft:true'
print('ok barsoom loaded; draft-hidden but valid; cultures:', [c.name for c in b.cultures])
"
```
Expected: `ok barsoom loaded; draft-hidden but valid; cultures: ['Red Martian', 'Green Martian']`

- [ ] **Step 2: Boot the server + reference page (visual + anchor smoke test).** With the running stack (`just up` or the server alone), open `/reference/lore/heavy_metal/barsoom` and confirm: the page renders (no "Anchor not found" banner), the cultures/factions/POIs appear, and no 500. (Lore Cast display names come from `portrait_manifest` — absent in Story 1, so a thin Cast section is expected, not a bug.)

Run: start the server, then
`curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8765/reference/lore/heavy_metal/barsoom`
Expected: `200`

- [ ] **Step 3 (optional, recommended): Render the hero POI to preview the Frazetta look.** Use the orchestrator render script via `uv run` (boto3 lives in the orchestrator uv env — never bare `python3`). This previews the look and proves the prompt; assets are formally Story 6.

Run (from orchestrator root): `uv run python scripts/generate_poi_images.py --genre heavy_metal --world barsoom --poi dead_sea_bottom_of_korad`
Expected: a PNG written locally for visual review. *(Confirm flag names against the script; do not pass `--output-dir` — let the world-scoped routing fire.)*

- [ ] **Step 4: Final commit (any fixes from the gate).**

```bash
git add -A genre_packs/heavy_metal/worlds/barsoom corpus/shared/barsoom_red.txt corpus/shared/barsoom_green.txt
git commit -m "content(barsoom): Story 1 loader gate — playable red/green core green"
```

---

## Self-Review (against the spec)

- **Spec §3 tone (heroic, not doom)** → Task 1 `axis_snapshot` (hope 0.7), Task 6 lore, Task 9 openings. ✓
- **Spec §4 peoples (red + green for Story 1)** → Tasks 3–4 (cultures + corpora). ✓ (Black/White/Yellow/Lotharian = Stories 2–3, correctly deferred.)
- **Spec §5 factions** → Task 6 lore + Task 8 NPCs (wired path; `faction_agendas.yaml` correctly avoided). ✓
- **Spec §6 magic** → correctly **out of scope** (Story 4); Task 6 carries telepathy as narrator-framed baseline only, no `cast_spell`. ✓
- **Spec §8.1 files** → Tasks 1–9 cover world/cartography/cultures/visual/lore/history/npcs/openings + corpora. ✓
- **Spec §8.2 loader gate, unified Opening schema, draft-skip, authored_npcs** → Task 9 Step 2 + Task 10 Step 1. ✓
- **Spec §9 crunch flags (Earthman boon, green physiology) + origin-trait wiring** → correctly **deferred to Story 5**; the Earthman boon appears only as *fiction* in the Task 9 solo opening (no stat), so no unwired crunch ships. ✓
- **Spec §10 visual** → Task 5 (style-only suffix + tag overrides), Task 7 (POI visual_prompts to the guide), Task 10 Step 3 (preview render). ✓

**Placeholder scan:** Two intentional confirm-the-flag notes (namegen CLI flags, POI render flags) — these are real "verify against the script" instructions, not content placeholders; the success criterion is stated in each. No content gaps.

**Naming consistency:** `cover_poi: dead_sea_bottom_of_korad` (Task 1) == POI slug (Task 7) == verified (Task 7 Step 2, Task 10 Step 1). `starting_region: helium` (Task 1) == cartography region (Task 2) == verified (Task 2 Step 2). Corpus filenames `barsoom_red.txt`/`barsoom_green.txt` (Tasks 3–4) referenced by the culture `slots` and resolved via namegen. ✓
