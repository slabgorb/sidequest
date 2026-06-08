# SWN Gear & Pharmacopeia (Lane A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich `space_opera`'s `inventory.yaml` with an SWN-derived weapon / armor / gear catalog and a stim pharmacopeia, using only the existing `CatalogItem` schema, so every `space_opera` playtest has genre-true, scene-hook-bearing gear.

**Architecture:** Pure content authoring against the *existing* strict (`extra="forbid"`) `CatalogItem` model in `sidequest-server/sidequest/genre/models/inventory.py`. We translate SWN's *nouns, flavor, and relative power*, not its d20 stats. Relative lethality rides `power_level` + `tags`; flavor rides `lore` + `narrative_weight`; stims are `category: consumable`. The "test" for each task is that the pack still loads through `InventoryConfig` via `just content-validate space_opera`.

**Tech Stack:** YAML content; pydantic-v2 schema validation via the `sidequest.cli.validate` CLI.

**Explicitly out of scope (rides Plan #1 — HP substrate):** a `damage` field on weapons. `CatalogItem` is `extra="forbid"`, so a damage number needs a server model change *and* HP to subtract from — dead data without it (No-Stubbing rule). Weapons here carry relative lethality via `power_level`/`tags` only; the concrete `damage` descriptor is added when HP lands.

---

## File Structure

- Modify: `sidequest-content/genre_packs/space_opera/inventory.yaml`
  - `item_catalog:` — append new weapon, armor, consumable, and gear entries.
  - `starting_equipment:` / `starting_gold:` — light touch-ups so new items are reachable from chargen.
- No server, UI, or daemon files change in this plan.

**Voice note for the author:** match the existing `lore:` register — dry, wry, one beat of character per line ("Every station market has a bin of these. They all work. Mostly."). Every item's `lore` should imply a scene or a world, not just describe the object.

**Branching:** `sidequest-content` is github-flow on `develop`. Branch `feat/swn-gear-pharmacopeia` off `develop` in the content subrepo *before the first commit* (the pf commit hook scans subrepos — see house rules). All commits in this plan land in `sidequest-content`.

---

### Task 1: Branch the content subrepo

**Files:** none (git only)

- [ ] **Step 1: Create the feature branch off develop**

```bash
cd sidequest-content
git checkout develop && git pull
git checkout -b feat/swn-gear-pharmacopeia
```

- [ ] **Step 2: Confirm the pack validates clean BEFORE any edits (baseline)**

Run (from orchestrator root): `just content-validate space_opera`
Expected: exits 0, no schema errors. This is the green baseline every later task must preserve.

---

### Task 2: Expand the weapon catalog

**Files:**
- Modify: `sidequest-content/genre_packs/space_opera/inventory.yaml` (append to `item_catalog`, in the `--- WEAPONS ---` region)

- [ ] **Step 1: Append the new weapon entries**

Add these entries under `item_catalog:` after the existing weapons:

```yaml
  - id: mag_pistol
    name: Mag Pistol
    description: Magnetic flechette sidearm. No power cell — the slugs carry their own charge.
    category: weapon
    value: 400
    weight: 1.0
    rarity: uncommon
    power_level: 2
    tags: [ranged, kinetic, one-handed, sidearm, armor-piercing]
    lore: Punches through plate a blaster would just scorch. Customs hates them for exactly that reason.
    narrative_weight: 0.2

  - id: void_carbine
    name: Void Carbine
    description: Recoilless carbine built for vacuum and zero-gee. Rounds won't scratch ship plating.
    category: weapon
    value: 400
    weight: 2.0
    rarity: uncommon
    power_level: 2
    tags: [ranged, kinetic, two-handed, shipboard, no-recoil]
    lore: Boarders' favorite. You can empty a magazine in a corridor without venting yourself to the black.
    narrative_weight: 0.2

  - id: scattergun
    name: Scattergun
    description: Short-barrelled shot weapon. Devastating up close, useless across a hangar.
    category: weapon
    value: 300
    weight: 3.0
    rarity: common
    power_level: 2
    tags: [ranged, kinetic, two-handed, close-range]
    lore: The argument-ender of every frontier cantina. Nobody asks for a second barrel.
    narrative_weight: 0.2

  - id: marksman_rifle
    name: Marksman Rifle
    description: Long-barrelled precision rifle with a smartscope. Built to end a thing before it knows you're there.
    category: weapon
    value: 400
    weight: 3.0
    rarity: uncommon
    power_level: 3
    tags: [ranged, kinetic, two-handed, long-range, precision]
    lore: One breath, one round. The people who carry these don't talk much, and never about work.
    narrative_weight: 0.3

  - id: plasma_projector
    name: Plasma Projector
    description: Two-handed energy weapon that hurls a sphere of magnetically-bottled plasma.
    category: weapon
    value: 400
    weight: 4.0
    rarity: uncommon
    power_level: 3
    tags: [ranged, energy, two-handed, loud, military]
    lore: Loud as a god clearing its throat. Short range, but whatever it touches stops being a problem.
    narrative_weight: 0.3

  - id: thunder_gun
    name: Thunder Gun
    description: Grav-disruption weapon that shakes a target apart from the inside. Felt before it's heard.
    category: weapon
    value: 1000
    weight: 3.0
    rarity: rare
    power_level: 3
    tags: [ranged, grav, two-handed, pretech, structural]
    lore: They named it for the sound your bones make. Walls don't stop it; they just join in.
    narrative_weight: 0.5

  - id: distortion_cannon
    name: Distortion Cannon
    description: Pretech weapon that folds the space inside a target until the target gives up being whole.
    category: weapon
    value: 1250
    weight: 4.0
    rarity: rare
    power_level: 4
    tags: [ranged, pretech, two-handed, spatial, cover-ignoring]
    lore: It reaches through a meter of bulkhead like the bulkhead apologised and stepped aside. Mandate-era. Irreplaceable. Feared.
    narrative_weight: 0.7

  - id: monoblade
    name: Monoblade
    description: A blade honed to a single molecule's edge. Sheaths in a whisper, cuts without resistance.
    category: weapon
    value: 60
    weight: 0.5
    rarity: uncommon
    power_level: 2
    tags: [melee, blade, one-handed, advanced, silent]
    lore: Ignores the armor that stops a vibroknife. Quiet enough that the first anyone hears of it is the quiet.
    narrative_weight: 0.2

  - id: suit_ripper
    name: Suit Ripper
    description: A short fractal-edged rod that shreds vacc-suit self-repair. Strictly illegal in any vacuum.
    category: weapon
    value: 75
    weight: 0.5
    rarity: uncommon
    power_level: 1
    tags: [melee, sabotage, one-handed, illegal, anti-suit]
    lore: Won't kill a man in shirtsleeves. In hard vacuum it's a death sentence with a handle. Spacers execute people for carrying one aboard.
    narrative_weight: 0.4
```

- [ ] **Step 2: Validate the pack still loads**

Run: `just content-validate space_opera`
Expected: exits 0, no errors. If a field name is rejected, you used a key outside `CatalogItem` (`id,name,description,category,value,weight,rarity,power_level,tags,lore,narrative_weight,resource_ticks`) — fix it; do **not** add a `damage` key (out of scope).

- [ ] **Step 3: Commit**

```bash
cd sidequest-content
git add genre_packs/space_opera/inventory.yaml
git commit -m "content(space_opera): expand weapon catalog from SWN"
```

---

### Task 3: Expand the armor catalog

**Files:**
- Modify: `sidequest-content/genre_packs/space_opera/inventory.yaml` (append under the `--- ARMOR ---` region)

- [ ] **Step 1: Append the new armor entries**

```yaml
  - id: armored_undersuit
    name: Armored Undersuit
    description: Skin-tight TL4 weave with shock-activated rigidity. Wears clean under ordinary clothes.
    category: armor
    value: 600
    weight: 0.0
    rarity: uncommon
    power_level: 2
    tags: [light, concealed, shipboard]
    lore: Looks like long underwear, stops a knife like a breastplate. Half the diplomats in the sector are wearing one right now.
    narrative_weight: 0.2

  - id: combat_field_uniform
    name: Combat Field Uniform
    description: Standard front-line battledress — ablative coatings, rigid plates, shock-soft components.
    category: armor
    value: 1000
    weight: 4.0
    rarity: uncommon
    power_level: 3
    tags: [medium, ballistic, military]
    lore: What soldiers actually wear, as opposed to what recruiting posters draw. Smells of ozone and old fear.
    narrative_weight: 0.2

  - id: deflector_array
    name: Deflector Array
    description: A scatter of force-field nodes worn under clothing. Flares blue only when something deadly is incoming.
    category: armor
    value: 30000
    weight: 0.0
    rarity: rare
    power_level: 4
    tags: [light, force-field, concealed, pretech]
    lore: Invisible until the instant it saves you, then a brief bright apology where the bolt should have landed. Worth more than most ships.
    narrative_weight: 0.6

  - id: assault_suit
    name: Assault Suit
    description: Powered combat armor with encrypted comms, low-light vision, and an unlimited-feed weapon port.
    category: armor
    value: 10000
    weight: 2.0
    rarity: rare
    power_level: 4
    tags: [powered, military, sealed, requires-power-cell]
    lore: Immune to anything a primitive world can throw and most of what a civilised one can. Burns a type-B cell a day. Wearing one anywhere civil is a declaration.
    narrative_weight: 0.5
```

- [ ] **Step 2: Validate**

Run: `just content-validate space_opera`
Expected: exits 0, no errors.

- [ ] **Step 3: Commit**

```bash
cd sidequest-content
git add genre_packs/space_opera/inventory.yaml
git commit -m "content(space_opera): expand armor catalog from SWN"
```

---

### Task 4: Add the stim pharmacopeia

**Files:**
- Modify: `sidequest-content/genre_packs/space_opera/inventory.yaml` (extend the `--- CONSUMABLES ---` region)

Each stim is a `category: consumable` item whose *effect lives in `lore` + `tags`* — the mechanical handle (heal/cost) wires up once HP lands (Plan #1). The point now is the **scene each drug opens**.

- [ ] **Step 1: Append the stim entries**

```yaml
  - id: lift_stim
    name: Lift
    description: Recovery stim that floods the body's repair response. Useless on the mortally wounded — stabilise them first.
    category: consumable
    value: 50
    weight: 0.1
    rarity: common
    power_level: 1
    tags: [stimulant, healing, recovery, single-use]
    lore: Five minutes and a Lift and you're on your feet again, mostly. The "mostly" compounds. Old soldiers rattle when they walk.
    narrative_weight: 0.2

  - id: lazarus_patch
    name: Lazarus Patch
    description: Heavy trauma compress — antibiotics, coagulant, plasma, and a one-shot diagnostic. Buys a dying body time.
    category: consumable
    value: 30
    weight: 0.1
    rarity: common
    power_level: 2
    tags: [medical, stabilize, trauma, single-use]
    lore: Slap it on someone bleeding out and pray to the diagnostic. Each second you waited is a second it counts against you. No use on the already-gone.
    narrative_weight: 0.4

  - id: reverie
    name: Reverie
    description: Combat drug that subdues fear and adrenaline completely, leaving the user calm in the middle of dying.
    category: consumable
    value: 100
    weight: 0.1
    rarity: uncommon
    power_level: 2
    tags: [stimulant, combat, cold, single-use]
    lore: Perfect aim, perfect calm, perfect indifference to the round that just opened your shoulder. Reaction time goes to glass. The people who like Reverie too much are not people anymore.
    narrative_weight: 0.4

  - id: hush
    name: Hush
    description: Heavy neurotranquilizer. Leaves a subject awake, biddable, and unable to refuse a simple instruction.
    category: consumable
    value: 200
    weight: 0.1
    rarity: uncommon
    power_level: 2
    tags: [sedative, compliance, control, illegal, single-use]
    lore: They'll walk, sit, sign, and remember none of it. Every world that bans it bans it loudly, which tells you who's buying.
    narrative_weight: 0.5

  - id: squeal
    name: Squeal
    description: Unreliable but effective interrogation serum. The willing — or the restrained — answer plainly for a few minutes.
    category: consumable
    value: 300
    weight: 0.1
    rarity: uncommon
    power_level: 2
    tags: [interrogation, truth, control, illegal, single-use]
    lore: It pulls facts, not judgement — ask the wrong question and you'll get the wrong truth, perfectly sincere. They can refuse to speak at all. They just can't lie about what they do say.
    narrative_weight: 0.5

  - id: psych_stim
    name: Psych
    description: Field-brewed courage in a capsule. Floods the user with confidence and a reckless contempt for danger.
    category: consumable
    value: 25
    weight: 0.1
    rarity: common
    power_level: 1
    tags: [stimulant, combat, reckless, addictive, single-use]
    lore: You will not take cover. You will not retreat. You will feel magnificent right up until the part where you don't. Habitual, in the way that bad decisions are habitual.
    narrative_weight: 0.3

  - id: tsunami
    name: Tsunami
    description: Emergency combat stim that mortgages tomorrow's body against tonight's fight. The bill always comes due.
    category: consumable
    value: 50
    weight: 0.1
    rarity: uncommon
    power_level: 2
    tags: [stimulant, combat, backlash, single-use]
    lore: Borrowed life, with reckless aggression thrown in free. When it ebbs it takes back everything it lent — and sometimes a little more than you had to spare.
    narrative_weight: 0.4

  - id: bezoar
    name: Bezoar
    description: Broad-spectrum antibiotic cocktail. The default answer to most infectious diseases, given time.
    category: consumable
    value: 200
    weight: 0.1
    rarity: common
    power_level: 1
    tags: [medical, cure, disease, single-use]
    lore: Won't touch a poison, a cancer, or an engineered bioweapon — which is exactly when you find out which one you've got.
    narrative_weight: 0.3
```

- [ ] **Step 2: Validate**

Run: `just content-validate space_opera`
Expected: exits 0, no errors.

- [ ] **Step 3: Commit**

```bash
cd sidequest-content
git add genre_packs/space_opera/inventory.yaml
git commit -m "content(space_opera): add SWN stim pharmacopeia"
```

---

### Task 5: Add field & tech gear

**Files:**
- Modify: `sidequest-content/genre_packs/space_opera/inventory.yaml` (extend `--- TOOLS ---`, add a `--- FIELD & TECH ---` region)

- [ ] **Step 1: Append the gear entries**

```yaml
  - id: vacc_suit
    name: Vacc Suit
    description: Sealed pressure suit with hours of air. The difference between a hull breach and an obituary.
    category: tool
    value: 100
    weight: 2.0
    rarity: common
    power_level: 1
    tags: [survival, sealed, shipboard, vacuum]
    lore: Nobody loves wearing one. Everybody loves having worn one. Check the seals twice; the black doesn't give second chances.
    narrative_weight: 0.2

  - id: low_light_goggles
    name: Low-Light Goggles
    description: Light-amplifying optics for dark holds, dead stations, and moonless nights.
    category: tool
    value: 200
    weight: 0.5
    rarity: common
    power_level: 1
    tags: [optical, sensor, shipboard]
    lore: Turns a black corridor into a green one. Whatever was waiting in the dark is still there — now you just get to see it coming.
    narrative_weight: 0.1

  - id: grav_chute
    name: Grav Chute
    description: Compact gravitic descender. Replaces a parachute with an unhurried fall from any height.
    category: tool
    value: 300
    weight: 1.0
    rarity: uncommon
    power_level: 2
    tags: [grav, survival, single-charge]
    lore: Step off the gantry, count to nothing, land like you meant it. One good fall per charge. Count your charges.
    narrative_weight: 0.2

  - id: survey_scanner
    name: Survey Scanner
    description: Finely-tuned multi-spectrum array — maps terrain, charts hazards, sniffs out what's hiding.
    category: tool
    value: 250
    weight: 1.0
    rarity: uncommon
    power_level: 2
    tags: [electronic, sensor, survey]
    lore: The handheld tells you what's in front of you. This one tells you what's over the ridge, and whether it's breathing.
    narrative_weight: 0.2

  - id: translator_torc
    name: Translator Torc
    description: Neck-worn translation collar keyed to two tongues. Eccentric, half a beat slow, indispensable anyway.
    category: tool
    value: 200
    weight: 0.0
    rarity: common
    power_level: 1
    tags: [electronic, comms, language, social]
    lore: Renders insults as compliments and contracts as poetry about as often as not. Whole feuds have started inside the delay between a word and its echo.
    narrative_weight: 0.2

  - id: black_slab
    name: Black Slab
    description: A dataslab that looks ordinary and isn't — packed with intrusion gear and line-tapping tools.
    category: tool
    value: 10000
    weight: 0.5
    rarity: rare
    power_level: 3
    tags: [electronic, hacking, illegal, intrusion]
    lore: Passes a casual glance, fails a serious one, and on most worlds the serious ones carry sentences. The people who sell them don't take credits.
    narrative_weight: 0.4

  - id: line_shunt
    name: Line Shunt
    description: A coin of polychromatic film that splices a hardened data line without a physical tap.
    category: tool
    value: 100
    weight: 0.0
    rarity: uncommon
    power_level: 2
    tags: [electronic, hacking, single-use]
    lore: Stick it near the right conduit and the wall starts telling secrets. Single-use, blends with whatever it's stuck to, and very illegal to be caught holding.
    narrative_weight: 0.2

  - id: stiletto_charge
    name: Stiletto Charge
    description: Thumb-sized Mandate-era intrusion charge. Walks straight through primitive security like the door owed it money.
    category: treasure
    value: 2000
    weight: 0.0
    rarity: rare
    power_level: 3
    tags: [pretech, hacking, single-use, valuable]
    lore: Made to crack colonial locks for agents who no longer exist. One use, then dead. Worth a fortune to the kind of people who need exactly one door opened.
    narrative_weight: 0.5
```

- [ ] **Step 2: Validate**

Run: `just content-validate space_opera`
Expected: exits 0, no errors.

- [ ] **Step 3: Commit**

```bash
cd sidequest-content
git add genre_packs/space_opera/inventory.yaml
git commit -m "content(space_opera): add field and tech gear from SWN"
```

---

### Task 6: Wire new gear into chargen & verify id resolution

**Files:**
- Modify: `sidequest-content/genre_packs/space_opera/inventory.yaml` (`starting_equipment:` block)

Light touch only — give the medical/infiltration classes one new starting item each so the catalog is reachable at character creation, without churning the existing kits.

- [ ] **Step 1: Add new starting items to fitting classes**

In `starting_equipment:`, append to these existing class lists:

```yaml
  Medic:
    - medkit_field
    - medpatch
    - medpatch
    - datapad
    - flight_suit
    - lazarus_patch     # new
  Operative:
    - blaster_sidearm
    - vibroknife
    - flight_suit
    - datapad
    - line_shunt        # new
  Soldier:
    - blaster_rifle
    - tactical_vest
    - medpatch
    - stim_pack
    - combat_field_uniform   # new
```

- [ ] **Step 2: Verify every starting_equipment id resolves to a catalog item**

Run this resolution check (catches typos that schema validation alone won't):

```bash
cd sidequest-content
uv run --project ../sidequest-server python - <<'PY'
import sys, yaml
from pathlib import Path
data = yaml.safe_load(Path("genre_packs/space_opera/inventory.yaml").read_text())
catalog = {i["id"] for i in data.get("item_catalog", [])}
missing = []
for klass, items in (data.get("starting_equipment") or {}).items():
    for item_id in items:
        if item_id not in catalog:
            missing.append((klass, item_id))
if missing:
    print("UNRESOLVED starting_equipment ids:")
    for k, i in missing:
        print(f"  {k}: {i}")
    sys.exit(1)
print(f"OK: all starting_equipment ids resolve ({len(catalog)} catalog items)")
PY
```

Expected: `OK: all starting_equipment ids resolve (...)`. If it lists unresolved ids, fix the typo in either the catalog `id` or the `starting_equipment` reference.

- [ ] **Step 3: Final pack validation**

Run: `just content-validate space_opera`
Expected: exits 0, no errors.

- [ ] **Step 4: Commit**

```bash
cd sidequest-content
git add genre_packs/space_opera/inventory.yaml
git commit -m "content(space_opera): wire new SWN gear into chargen kits"
```

---

### Task 7: Open the PR

**Files:** none (git only)

- [ ] **Step 1: Push and open the PR against develop**

```bash
cd sidequest-content
git push -u origin feat/swn-gear-pharmacopeia
env -u GITHUB_TOKEN gh pr create -R slabgorb/sidequest-content -B develop \
  -t "SWN gear & pharmacopeia for space_opera" \
  -b "Lane A of the SWN-crunch design (docs/superpowers/specs/2026-05-25-swn-crunch-ablative-hp-design.md). Adds an SWN-derived weapon/armor/gear catalog + stim pharmacopeia to space_opera inventory.yaml using existing CatalogItem fields only. Weapon \`damage\` field deferred to the HP-substrate plan."
```

- [ ] **Step 2: Merge when green**

```bash
cd sidequest-content
env -u GITHUB_TOKEN gh pr merge -R slabgorb/sidequest-content --squash --delete-branch
```

---

## Self-Review

**Spec coverage (Lane A only):** Spec §2 Lane A asks for (a) a richer weapon/armor/gear spread and (b) the stim pharmacopeia with scene-hooks — Tasks 2–5 cover both. The spec's weapon `damage` descriptor is explicitly deferred to Plan #1 with rationale (schema is `extra="forbid"`; damage is dead data without HP) — called out in the header and front matter, not silently dropped.

**Placeholder scan:** No TBD/TODO. Every item entry is complete authored YAML. Every verify step has a concrete command + expected output. The chargen resolution check is a real runnable script, not "verify ids are valid."

**Type consistency:** Every key used (`id,name,description,category,value,weight,rarity,power_level,tags,lore,narrative_weight`) is a field on `CatalogItem` (`sidequest-server/sidequest/genre/models/inventory.py:31-47`). No `damage` key anywhere. `category` values (`weapon`/`armor`/`consumable`/`tool`/`treasure`) match the existing catalog's usage. `starting_equipment` references in Task 6 (`lazarus_patch`, `line_shunt`, `combat_field_uniform`) are all defined in Tasks 3–5.
