# Class Mechanical Surface — Brainstorm Handoff

**Origin:** Playtest 2026-05-10 (caverns_and_claudes / caverns_sunden, multiplayer Cleric + Thief).
**Author:** Architect (post-playtest assessment).
**Status:** Open question — needs brainstorm before any code or content moves.
**For:** the next agent who runs `/brainstorm` (or `/pf-brainstorming`) on this question.

## What This Is

A two-axis design question that surfaced when a Lv 1 Cleric and a Lv 1 Thief, both freshly created in caverns_and_claudes, opened the **Abilities** tab on their character sheet and saw the literal text "No abilities."

The data is honestly empty. The UI is honestly rendering. **The question is whether the data should be empty.** If the answer is "yes, abilities are earned through play," the UI is misleading. If the answer is "no, classes should have signature mechanics at L1," the data is incomplete. Either fix is small. The decision behind which fix is the actual brainstorm.

## Why This Matters

The playgroup the design has to satisfy (per `CLAUDE.md`):

- **Keith** — 40-year B/X veteran. Will read the sheet and ask "where is Turn Undead? Where are the Thief percentages?"
- **Sebastien** — mechanics-first player. Reads the sheet first, the prose second. "No abilities." reads as a load failure.
- **James / Alex** — narrative-first players who don't care about the sheet, but lean on the narrator's class-flavored calls.

Two of the four primary-audience players will *immediately* notice this gap. The narrator currently compensates well (the playtest log shows Cleric divine-sense and Thief tactical recon both engaging beautifully through prose alone) — but a B/X veteran reads narration *and* sheet, and the sheet is currently silent.

## What's Already True (Architectural Facts)

### Four ability sources defined

`sidequest-server/sidequest/game/ability.py`:

```python
class AbilitySource(StrEnum):
    Race = "Race"   # Innate to species
    Class = "Class" # Granted by class/archetype
    Item = "Item"   # Bestowed by item/artifact
    Play = "Play"   # Earned through gameplay
```

### Population status at L1, per source

| Source | Defined where | Lv 1 Cleric | Lv 1 Thief |
|---|---|---|---|
| Race | (no race packs surface them yet) | empty | empty |
| Class | `classes.yaml` per class | **no `abilities` key on any class** | **no `abilities` key** |
| Item | item kit definitions | starting kits don't grant abilities | starting kits don't grant abilities |
| Play | `progression.yaml` affinity tiers | tier 1 unlocks at 100 EXP | tier 1 unlocks at 100 EXP |

**Result:** `Character.abilities: list[AbilityDefinition]` (`character.py:97`) is empty at chargen for every class.

### What classes DO carry today

`sidequest-content/genre_packs/caverns_and_claudes/classes.yaml`:

- `prime_requisite` (STR/INT/WIS/DEX)
- `kit_table` (drives starting equipment)
- `flavor` (one-line prose)
- `encounter_beat_choices: list[str]` — Cleric: `[attack, defend, flee, shield_bash, turn_undead, pray]`. Thief: `[attack, defend, flee, feint, backstab, sneak]`.
- `magic_access: innate_v1` (Cleric/Mage) or `null` (Fighter/Thief).
- `magic_config` for casters — Cleric carries `turn_undead: true` as a flag, plus B/X-canon spell slot table starting at L2.
- `saving_throws` — five-axis B/X table.

### What B/X classic carries that we don't

- **Cleric:** Turn Undead matrix (per HD). Currently a flag, not a usable ability.
- **Thief:** Pick Locks 15%, Move Silently 20%, Hide in Shadows 10%, Find Traps 10%, Climb Walls 87%, Hear Noise 1-on-d6, Read Languages 0% at L1. Entirely absent from any data file.
- **All classes:** Turn-undead matrix shown nowhere; saves not surfaced in UI.

### What the UI actually does

`sidequest-ui/src/components/CharacterPanel.tsx`:

- Line 825: `abilities: string[]` — flattened name list, not full `AbilityDefinition`s.
- Line 843: hardcoded empty state `"No abilities."`.
- The Stats / Abilities tabs are the only mechanical surface; encounter beats, saves, and class flavor live in YAML and never reach the screen.

### Adjacent design that's already settled

- **Affinities** (`progression.yaml`) — Delver / Plunderer / Survivor / Breaker / Schemer. Earned through play. Tier-1 abilities (Stonewise, Trap Sense, Quiet Feet, Vicious Strike, etc.) overlap heavily with classic Thief/Fighter skills. This is the "abilities are emergent" half of the design philosophy and it is **already shipped**.
- **Magic plugins** (`docs/design/magic-plugins/`) — handled separately. Cleric's L1-no-spells is intentional B/X canon; Mage gets the Detect Magic / Read Magic / Sleep package at L1. Magic is not part of the class-abilities question — it's a separate, working surface.

## The Three Options

(From the architect's pre-brainstorm assessment. None is a redesign. Pick one, or phase across them.)

### Option 1 — Minimum visibility fix

**Lift:** ~1-2 hours of UI + tiny content fill.

1. UI: change `"No abilities."` to a phrase that names the design philosophy (e.g., `"Earned through play. Your moves are sharpened by what you survive."`).
2. Surface **Turn Undead** as a Class-source ability for Cleric (it already exists as `magic_config.turn_undead: true` — pure wiring).
3. Surface `encounter_beat_choices` somewhere on the sheet (a "Class Moves" read-only section, or under Stats).

Closes the visible gap. Doesn't decide the deeper design question.

### Option 2 — Promote class beats to abilities

**Lift:** ~1-2 days of model + content + UI work.

Treat class-distinctive `encounter_beat_choices` (filtered: drop `attack`/`defend`/`flee`) as Class-source `AbilityDefinition`s with short prose. Cleric gets Turn Undead, Pray, Shield Bash. Thief gets Backstab, Sneak, Feint. Fighter gets Cleave, Parry, Feint, Shield Bash. Mage gets Cast Cantrip, Cast Spell. The encounter engine and the abilities tab read the **same source**.

Collapses two abstractions ("encounter beats" + "class abilities") into one. Cleanest reuse-first move if classes should have signature mechanics.

### Option 3 — Restore B/X canonical class data

**Lift:** ~3-5 days, all genre packs (not just C&C).

Add the percentage-skill table (Pick Locks 15%, etc.) to Thief data. Add the Turn Undead matrix to Cleric data. Surface saves. Walk all four classes through canonical B/X feature parity. Then propagate the pattern to every other genre pack's class definitions (Heavy Metal, Mutant Wasteland, etc.) since uniformity matters.

Highest fidelity for the veteran ear. Biggest content lift. Forces a decision on whether non-B/X genre packs (Mutant, Coyote Star, Tea & Murder) should ALSO carry rich per-class mechanical tables, or whether they remain encounter-beat-only.

## The Deeper Question

Below the three options sits a load-bearing decision that future ADRs (probably ADR-014's neighborhood, possibly a new one) will need to answer:

> **Are classes a mechanical lane, or are they a flavor lane and Affinities are the only mechanical lane?**

The current data shape says "flavor lane only" — classes pick their stat prime, their kit, their save row, their encounter beats, their magic plugin. That's flavor + binding to subsystems, not mechanical signature moves. The Affinities (Delver/Plunderer/Survivor/Breaker/Schemer) are the actual growth lane and they're class-agnostic.

If that's the intended design, **classes are character archetypes, not mechanical archetypes**, and the three options above all fight that grain to varying degrees:

- Option 1 makes peace with it (just labels the design).
- Option 2 fights it gently (promotes a class-distinctive surface).
- Option 3 fights it hard (restores a canonical mechanical lane per class).

This is the question the brainstorm should answer before picking an option. The answer also informs:

- How `encounter_beat_choices` should be authored across the 11 genre packs (currently shipped: caverns_and_claudes; the others vary).
- Whether saves belong on the sheet at all, or whether the dice-resolution protocol (ADR-074) supersedes them.
- Whether the Confrontation Engine (ADR-033) should resolve combat from class-flavored abilities or only from encounter beats and dice.
- How "level up" feels — is leveling up a class thing (new abilities, better saves) or an Affinity-tier thing (new earned abilities, no class change)?

## Recommended Brainstorm Starting Sequence

Suggested questions for the brainstorm, in order. Treat them as a starting trail, not a script.

1. **Audience-first.** "Sebastien opens his Cleric's sheet. What is the first sentence of mechanical signal that should jump off the page?" — This anchors the discussion in the actual reader and forces a concrete answer.
2. **Affinities yes-and.** "Affinities ship and work. Does Sebastien's class still need a mechanical signature *in addition to* his Affinity tier, or is the Affinity tier the entire mechanical signature once earned?" — Forces the deeper-question answer.
3. **Tabletop calibration.** "If we strip away the digital amplifier and put this character on a paper sheet, what does it have on it?" — Tests the SOUL.md "tabletop first, then better" principle. A Cleric with no Turn Undead on paper would be wrong.
4. **Cross-genre stress test.** "Does a Heavy Metal pact-priest, a Mutant scavenger, a Coyote Star bounty hunter all want the same answer here? Or do different genres carry different class shapes?" — Catches premature universalism. The answer might be "C&C wants Option 3 because it's B/X-flavored; Mutant wants Option 1 because the class IS the mutation; Coyote Star wants Option 2."
5. **Once the option is picked, scope.** "Is this a single-genre fix (C&C only) or a system-wide pattern? If system-wide, what's the order of genre-pack rollout?"

## Files To Pre-Load Before The Brainstorm

| File | Why it's relevant |
|---|---|
| `sidequest-content/genre_packs/caverns_and_claudes/classes.yaml` | The data shape we're deciding about. Read all four class blocks. |
| `sidequest-content/genre_packs/caverns_and_claudes/progression.yaml` | The Affinity system that already ships. Read enough to feel the tone (the prose for Stonewise, Quiet Feet, Vicious Strike). |
| `sidequest-server/sidequest/game/ability.py` | The four ability sources. 30 lines. |
| `sidequest-server/sidequest/game/character.py` (lines 1-100) | `AbilityDefinition` model and `Character.abilities` field. |
| `sidequest-server/sidequest/genre/models/character.py` (the genre-side ClassDefinition) | Where `encounter_beat_choices` lives in the genre model. |
| `sidequest-ui/src/components/CharacterPanel.tsx` (lines 820-910) | Where "No abilities." is hardcoded; the rendering shape we'd need to update. |
| `docs/adr/README.md` (and ADR-014, ADR-021) | Diamonds and Coal + Progression — the design principles this question lives inside. |
| `CLAUDE.md` "Who This Is For" section | The audience rubric that should drive the answer. |
| `/Users/slabgorb/Projects/sq-playtest-pingpong.md` | The playtest finding that opened this. Read the `[QUESTION]` entry on Cleric/Thief abilities for the exact symptom. |

## Out Of Scope For This Brainstorm

To keep the design tight, the following adjacent questions should be **named and deferred** rather than absorbed:

- The `[BUG]` filed against story-autogen (Background-only, not Description/Pronouns) — that's a chargen bug, separate fix.
- The `[UX]` MP turn-state desync during narration ("Waiting on X to act…" stale text) — that's a multiplayer protocol question, separate fix.
- B/X save-throw matrices in the UI — adjacent but solvable independently of this question.
- Ranged combat rules / weapon properties — class-adjacent but separate.
- Race abilities (the `Race` source in the enum) — race packs not yet shipped; this question should not block on them.

## Locked Decisions (Do Not Re-Litigate)

These were settled before this brainstorm and are inputs, not topics:

1. **Affinities ship and stay.** `progression.yaml` is canon. Whatever class abilities decision lands, Affinities continue to be the through-line growth lane.
2. **L1 Cleric has zero spells.** B/X canon, intentional. This is not a "missing spells" bug.
3. **Magic plugins handle casters.** `magic_access: innate_v1` and the `magic_config` block are the casting surface, working as designed. Class abilities discussion is *non-magical* class signature — Turn Undead, Backstab, etc.
4. **The Zork Problem stands.** No matter what we surface on the sheet, the natural-language declaration field stays the primary verb input. Ability cards on the sheet are reference, not menus.

## Exit Criteria For The Brainstorm

The brainstorm is done when:

1. One of the three options (or a documented hybrid) is chosen.
2. The deeper-question answer is recorded — class-as-mechanical-lane or class-as-flavor-lane.
3. Cross-genre scope is stated — single-pack fix or system-wide pattern.
4. A spec doc is written to `docs/superpowers/specs/YYYY-MM-DD-class-mechanical-surface-design.md` (per the brainstorming skill's own rules).
5. An ADR slot is reserved if the deeper-question answer warrants one (likely yes — this lives near ADR-014 and possibly amends ADR-021).

---

## Appendix — Direct Quotes From The Playtest

From `/Users/slabgorb/Projects/sq-playtest-pingpong.md`, the entry that started this:

> **[QUESTION] Level-1 Cleric and Thief both show "No abilities." in the Abilities tab — is that intended?**
>
> Both classes display literally "No abilities." at level 1. Is this intentional under the Edge / advancement design (abilities unlock via spends or progression), or is the abilities catalog not yet wired for Lv 1 Cleric/Thief? A 40-year TTRPG vet expects at least one signature move at Lv 1: Cleric → Turn Undead / Channel / Bless; Thief → Sneak Attack / Backstab / Thieves' Tools. If the design is "no Lv1 abilities, all motion through narration", that's a defensible choice but the Abilities tab should say **"Earned through play."** or similar — "No abilities." reads as a missing data load.

From the same session's narration on turn 1, demonstrating that **the narrator engages class-flavor correctly even with empty data**:

> *Eadhelm.* He walks the slate end to end, fingers on the brass, voice low. Pride's column gives nothing back. Greed's column gives nothing back. Gluttony's column is warmer in places — but the warmth tracks the morning sun, not the stone. The symbol stays the temperature of his throat.

> *Wulfa.* The thin man's shoulders stay square to the fountain; his eyes drift across the pair of you as one shape — the way a counterman watches strangers come in together. His weight rides his right foot. He is logging arrivals, not blocking exits.

The narrator already knows what a Cleric and a Thief are. The question is what the **sheet** knows.
