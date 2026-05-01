# Canned Openings — Cross-Pack Migration Handoff

**Date:** 2026-05-01
**Branch:** `feat/canned-openings` (server, content)
**Status:** Coyote Star ships; cross-pack migrations are the only thing blocking `just check-all`.
**Companion docs:**
- `docs/superpowers/specs/2026-05-01-canned-openings-design.md` — full design spec
- `docs/superpowers/plans/2026-05-01-canned-openings.md` — 30-task plan (Tasks 1–29 complete)

## TL;DR for whoever picks this up

The canned-openings story landed. Coyote Star solo + MP ships clean (`just check-all`'s lints pass; the targeted server unit tests for Phase 1–5 + plumbing all green). What blocks the **full** server test suite is a single load-time cascade: every test that loads any genre pack now fails because four other genre packs ship `openings.yaml` files that pre-date the unified schema (or ship no file at all), and the new mandatory validators reject them at world-load time.

**Five ways out, in order of effort:**

1. **M1 + M2 in full** — author the migration. ~30 opening entries across 8 worlds. Largest scope; gives a fully green gate.
2. **M1 only, park M2 worlds in workshop** — 4 C&C worlds get the mechanical envelope wrap (preserve prose, remap fields). The 4 worlds without `openings.yaml` (burning_peace, shattered_accord, flickering_reach, blackthorn_moor) move to `genre_workshopping/` until someone authors them, same pattern as aureate_span.
3. **Park everything in workshop, ship Coyote Star alone** — fastest. Aggressive. Leaves substantively-authored worlds parked.
4. **Stop here, file the migrations as separate stories** — the spec §8.4 explicitly anticipated this; the canned-openings PR can land as-is and the cross-pack migrations become their own follow-up tracked work.
5. **Loosen Validator 7 temporarily** — make solo-only OR mp-only worlds load with a warning instead of an error. Cleanest if other genres are at varying maturity tiers and the playgroup only wants Coyote Star selectable for now. This was NOT the design choice in the spec — the spec deliberately chose fail-loud so the pressure surfaced. Don't do this without re-litigating §8.4.

Default recommendation if no preference is expressed: **option 4** (stop, file follow-ups). The spec endorses it.

## Current branch state (2026-05-01 EOD)

### Server (`sidequest-server`, branch `feat/canned-openings`)

Recent commits (top of branch):

```
08eebde chore(lint): clear ruff findings in canned-openings code
aeca2b3 test: canned-openings wiring tests (Tasks 27-29)
c54a09a chore(server): delete dead test_opening_hook.py
fb851f6 feat(character): plumb chargen background/drive/name into Character
b223d26 chore(server): finalize coyote_reach -> coyote_star rename
29c46f8 feat(genre): plumb chassis_instances + magic_register onto World
ae9221e feat(ws-handler): resolve+stash opening directive at chargen-complete
... (Tasks 1-19 above)
```

### Content (`sidequest-content`, branch `feat/canned-openings`)

Branch is **based on `origin/develop`** (cherry-pick of oq-2's `coyote_reach → coyote_star` rename was abandoned in favor of merging develop directly — develop already had the rename plus more). Recent commits on top:

```
24c4f51 chore(content): delete genre-tier space_opera/openings.yaml (Task 26)
e2356c7 chore(content): park aureate_span in genre_workshopping
0caf3ca polish(coyote_star): vary repeated micro-bleed in fallback + MP openings
0ba3046 feat(coyote_star,aureate_span): canned openings + Kestrel crew (Phase 6)
4fe9a79 fix(playtest 2026-04-30): strip exterior-sun language from coyote_star visual_style (#161)
3ca6273 feat(coyote_star): MP opening + POI regen + gitignore housekeeping (#160)
f0d2fd4 Merge pull request #158 from slabgorb/feat/rename-coyote-reach-to-coyote-star
adb8e91 rename world Coyote Reach → Coyote Star
```

**Nothing is pushed.** Both branches are local-only. Push when ready.

### What's selectable today

`space_opera/coyote_star` only. `aureate_span` is parked in `genre_workshopping/space_opera/worlds/aureate_span/` per the cliche-judge audit (see "Aureate Span" section below).

## What blocks the full gate

Run `just check-all` from the orchestrator root. Lints pass. Server tests fail with **232 failures + 105 errors**. Sample first failure trace:

```
sidequest.genre.error.GenreLoadError: failed to load
worlds/dungeon_survivor/openings.yaml: no solo opening declared.
openings.yaml must include at least one entry with triggers.mode in
{'solo', 'either'}.
```

This is Validator 7 firing during pack load. Because nearly every server test loads a genre pack at module import time (via the conftest), the failure cascades through the entire test suite.

**Root cause:** four worlds in three genre packs ship pre-canned-openings YAML, and four more worlds ship no `openings.yaml` at all.

### Inventory

| Genre pack | World | Status | Migration |
|---|---|---|---|
| caverns_and_claudes | dungeon_survivor (= primetime symlink) | old `OpeningHook` shape | M1 envelope wrap |
| caverns_and_claudes | grimvault | old `OpeningHook` shape | M1 envelope wrap |
| caverns_and_claudes | horden | old `OpeningHook` shape | M1 envelope wrap |
| caverns_and_claudes | mawdeep | old `OpeningHook` shape | M1 envelope wrap |
| elemental_harmony | burning_peace | no `openings.yaml` | M2 skeleton author |
| elemental_harmony | shattered_accord | no `openings.yaml` | M2 skeleton author |
| mutant_wasteland | flickering_reach | no `openings.yaml` | M2 skeleton author |
| victoria | blackthorn_moor | no `openings.yaml` | M2 skeleton author |

Note: the user's original brief mentioned "burning_peace, flickering_reach, dust_and_lead." `dust_and_lead` does not exist anywhere in `genre_packs/`; `shattered_accord` and `blackthorn_moor` are present but were not on that list. Reconcile against current state, not the brief.

## M1 — Mechanical envelope wrap (caverns_and_claudes, 4 worlds)

The C&C worlds have substantive existing prose authored against the pre-canned-openings `OpeningHook` schema. **Mechanical migration: preserve prose verbatim, remap fields.** Cliche-judge sign-off is not required (prose is presumed clean and is not being authored fresh).

### Old shape (per entry)

```yaml
- id: dawn_at_the_approach
  archetype: preparation
  situation: >-
    Dawn in Ashgate. The party gathers...
  tone: clinical anticipation, muted
  avoid:
    - combat in the first scene
    - loud or dramatic entrances
    - exposition about the vault's nature (the player knows)
  first_turn_seed: >-
    Dawn. The ridge catches the first light and holds it without...
```

### New shape (per entry)

```yaml
- id: dawn_at_the_approach
  triggers:
    mode: either              # solo OR multiplayer; both fire this entry
    backgrounds: []
  setting:
    location_label: "Ashgate ridge road, the Recovery Bench at dawn"   # extract from `situation`
    situation: >-
      Dawn in Ashgate. The party gathers at the ridge road...           # preserve old `situation` verbatim
  tone:
    register: "clinical anticipation, muted"                            # was the bare `tone:` string; quote and put under register
    stakes: "low — preparation phase"                                    # add — preparation entries are low-stakes
    complication: "defer to descent"                                     # add — preparation entries don't escalate at the gate
    avoid_at_all_costs:                                                  # rename `avoid:` → `avoid_at_all_costs:` and append the universal one
      - combat in the first scene
      - loud or dramatic entrances
      - exposition about the vault's nature (the player knows)
      - ending the turn with a question
  establishing_narration: |
    Dawn. The ridge catches the first light and holds it without...     # use old `first_turn_seed:` verbatim as establishing_narration
  first_turn_invitation: |
    The Recovery Bench is set. The Threshold Stone is marked.            # NEW — author a 1–2 sentence declarative close that does NOT contain `?`
    The descent waits.
```

### Required adds per entry

For every old-shape entry, the migration must add:

- `triggers: { mode, backgrounds: [] }` — set `mode: either` for entries that work in solo and MP. Set `mode: solo` or `mode: multiplayer` only if the prose specifically requires one.
- `tone.stakes` and `tone.complication` — short strings; "preparation" entries are low-stakes, "delve" entries default `stakes: imminent / complication: defer to scene 2`.
- `tone.avoid_at_all_costs` — rename `avoid:` to this. **Append `"ending the turn with a question"`** to every list (universal Validator 1 tripwire).
- `first_turn_invitation` — 1–2 sentences, **NO `?`**. Close declaratively. Recommended pattern: name what's set, name the waiting moment.

### Validator 7 satisfaction

Validator 7 requires ≥1 solo + ≥1 MP entry per world. **The simplest path is `mode: either`** on at least one entry per world — `either` matches both solo and MP filtering passes. If a world's prose is genuinely solo-only or MP-only, set the explicit mode AND add a paired entry on the other axis (can be a fallback at `backgrounds: []`).

### Validator 8 satisfaction (chargen background coverage)

Caverns and Claudes' `char_creation.yaml` may use scene id `background` or another id. **Check first:** `grep "^- id:" genre_packs/caverns_and_claudes/char_creation.yaml`. If the chargen background scene's id is `background`, Validator 8 will derive labels from it and require coverage. If the scene id is anything else, Validator 8 silently falls through and only Validator 7 enforces the bank. Either way, including at least one entry with `triggers.backgrounds: []` (the catch-all) is safe.

### Files

```
genre_packs/caverns_and_claudes/worlds/dungeon_survivor/openings.yaml
genre_packs/caverns_and_claudes/worlds/grimvault/openings.yaml
genre_packs/caverns_and_claudes/worlds/horden/openings.yaml
genre_packs/caverns_and_claudes/worlds/mawdeep/openings.yaml
```

The `primetime` directory is a symlink to `dungeon_survivor` — fixing one fixes both.

### Suggested commit shape

```
feat(caverns_and_claudes): migrate openings.yaml to canned-openings schema (M1)

Mechanical envelope wrap of the 4 caverns_and_claudes worlds' openings:
- triggers, setting, tone block restructured per spec §1.1
- avoid → avoid_at_all_costs (with "ending the turn with a question" appended)
- first_turn_seed prose preserved as establishing_narration verbatim
- first_turn_invitation added per entry (declarative close, no `?`)
- Validator 7 satisfied via mode: either on the preparation entries

Refs: docs/superpowers/specs/2026-05-01-canned-openings-design.md §1.1
```

## M2 — Skeleton authoring (4 worlds without openings.yaml)

These worlds have substantive other content (lore, cartography, cultures) but no openings file. Each needs minimum 1 solo + 1 MP entry with **real prose** (no `[authored]` / `[TBD]` / `[migrated]` markers — Validator 10 rejects them).

### Files to create

```
genre_packs/elemental_harmony/worlds/burning_peace/openings.yaml
genre_packs/elemental_harmony/worlds/shattered_accord/openings.yaml
genre_packs/mutant_wasteland/worlds/flickering_reach/openings.yaml
genre_packs/victoria/worlds/blackthorn_moor/openings.yaml
```

### Skeleton template (location-anchored, 2 entries)

```yaml
version: "0.1.0"
world: <slug>
genre: <genre_slug>

openings:
  - id: solo_<world>_arrival
    name: "<Title>"
    triggers:
      mode: solo
      backgrounds: []
    setting:
      location_label: "<authored real prose>"
      situation: >-
        <authored real prose, ~1 sentence>
    tone:
      register: "<world-specific aesthetic adjectives>"
      stakes: "low on turn 1"
      complication: "defer to turn 2 or 3"
      avoid_at_all_costs:
        - any confrontation
        - any dice roll
        - moving the player without their input
        - ending the turn with a question
    establishing_narration: |
      <authored real prose, ~6-10 sentences. Genre-true. No placeholder markers.>
    first_turn_invitation: |
      <1-2 sentences, declarative, no `?`>

  - id: mp_<world>_arrival
    name: "<Title> — Together"
    triggers:
      mode: multiplayer
      min_players: 2
      max_players: 6
      backgrounds: []
    setting:
      location_label: "<authored real prose>"
      situation: >-
        <authored real prose>
    tone:
      register: "<world-specific>"
      stakes: "low on turn 1"
      complication: "defer to turn 2 or 3"
      avoid_at_all_costs:
        - any confrontation
        - any dice roll
        - re-introducing the PCs to one another
        - ending the turn with a question
    establishing_narration: |
      <authored real prose. Multi-PC. Genre-true.>
    first_turn_invitation: |
      <1-2 sentences, declarative, no `?`>
    party_framing:
      already_a_crew: <true|false>
      bond_tier_default: <neutral|familiar|trusted>
      shared_history_seeds:
        - "<authored real prose>"
      narrator_guidance: >-
        <authored real prose>
```

### Authoring guidance per genre

- **elemental_harmony** — martial-arts / elemental magic; the world should have a temple/dojo/sanctum starting region. Tone register usually "centered, deliberate, breath-paced." `already_a_crew` likely true (school-mates).
- **mutant_wasteland** — post-apocalyptic; world should have a settlement/camp/ruin starting region. Tone "weathered, dust-coated, careful." `already_a_crew` true if the world's `char_creation.yaml` implies a vault-mate / scrap-crew framing, false if not.
- **victoria** — Brontë gothic / drawing-room; world should have a parlor/garden/library starting region. Tone "measured, gas-lit, restrained." `already_a_crew` usually false — Victoria is solo-first per genre register.

### Cliche-judge gate

The cliche-judge audit on the aureate_span bootstrap (commit `0ba3046`) flagged six high-severity issues from rushed authoring (default-fantasy faction names, generic "envoy notices PC across plaza" beats). **Recommended:** dispatch the writer subagent for M2 with explicit cliche-judge follow-up, not as a quick mechanical pass.

If you skip cliche-judge and the prose ends up cliche, Validator 10 won't catch it (real prose is real prose). The audit is the only check.

### Suggested commit shape

```
feat(<genre>): skeleton openings.yaml for <world> (M2)

1 solo + 1 MP entry, location-anchored at <starting region>. Real
prose, no placeholders. Phase-7-equivalent expansion (chassis-anchored
banks, per-PC beats, soft hooks) deferred to a follow-up content story.

Refs: docs/superpowers/specs/2026-05-01-canned-openings-design.md §3
```

One commit per world, or one bundled commit for all four. Either is fine.

## Aureate Span — parked, do not promote without rewrite

`genre_workshopping/space_opera/worlds/aureate_span/` contains the full Aureate world directory including a 2-entry bootstrap `openings.yaml` I authored to unblock the genre-pack load during Phase 6. The cliche-judge audit (see commit `0ba3046` review) flagged six high-severity issues with the bootstrap prose:

1. "Imperatrix's gilded fountain fed from Solenne's corona" — Mass Effect Citadel decor
2. Crystalline Choir + sustained mysterious chord — cantina-mystical-music trope
3. Cinder Collective + ash-grey vestments — generic abstract-noun faction-naming
4. Vaal-Kesh — default-fantasy phoneme grab with no cultural anchor
5. The "envoy notices PC across plaza" beat — exactly the broker/quest-giver framing the entire spec was designed to avoid
6. Missing `aureate_span/npcs.yaml`

**Phase 7 (deferred, tracker #136)** owns the Aureate Span rewrite. The bootstrap files in workshop are starting material — useful for cartography, lore, and history. The `openings.yaml` should be substantially rewritten when Phase 7 lands.

## Useful commands

### Verify pack still loads (smoke gate)

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run python -m sidequest.cli.namegen \
  --genre <genre_slug> \
  --world <world_slug> \
  --culture <culture_name> \
  --gender female --role any \
  --genre-packs-path /Users/slabgorb/Projects/oq-1/sidequest-content/genre_packs \
  2>&1 | tail -10
```

If you get JSON output (NPC identity), validators pass. If you get `Error loading genre pack: ...`, the validator that fired is in the error message.

### Run targeted server tests after each migration commit

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/genre/ tests/server/test_magic_init.py tests/game/ -x 2>&1 | tail -20
```

The full suite has the noisy cascading failures; targeted tests give clean signal during migration.

### After all migrations are done — full gate

```bash
cd /Users/slabgorb/Projects/oq-1
just check-all 2>&1 | tail -40
```

Expected: PASS (server-test, server-lint, client-test, client-lint, daemon-lint).

### Validator reference

| # | Validator | Where it fires | Likely failure mode during migration |
|---|---|---|---|
| 1 | `first_turn_invitation` no `?` | pydantic field | Forgot to remove the closing question mark |
| 2 | `chassis_instance` resolves | cross-file | Old C&C entries reference rigs that don't exist (none should — they're location-anchored) |
| 3 | `interior_room` resolves | cross-file | Same as above |
| 4 | `crew_npcs` resolves | cross-file | Only fires for chassis-anchored entries |
| 5 | `AuthoredNpc.id` unique | cross-file | Only matters if you add `npcs.yaml` |
| 6 | `PerPcBeat.applies_to` keys | pydantic | Use `background`, `drive`, `race`, `class` only |
| 7 | ≥1 solo + ≥1 MP per world | cross-file | **Most common migration failure.** Use `mode: either` on at least one entry to satisfy both axes. |
| 8 | chargen backgrounds reachable | cross-file | Only fires if the world's chargen has a scene with `id: background`; otherwise silent |
| 9 | exactly one anchor per setting | model_validator | Don't set both `chassis_instance` and `location_label` |
| 10 | no `[authored` / `[TBD` / `[migrated` / `[placeholder` markers | pydantic | Real prose only; placeholders cause loud failures |
| 11 | `initial_disposition ∈ [-100, 100]` | pydantic Field | Only matters if you add `npcs.yaml` |
| 12 | `present_npcs` empty for chassis-anchored | model_validator | Don't list NPCs in `setting.present_npcs` when `chassis_instance` is set |
| 13 | `AuthoredNpc.name` non-empty | pydantic | Only matters if you add `npcs.yaml` |

### Tracker entries

The Pennyfarthing task tracker has these pending:

- `#125` — Migration M1: caverns_and_claudes envelope wrap
- `#126` — Migration M2: skeleton openings for the 4 lone-fail worlds (note: worlds list in the tracker description differs from current state; reconcile against `find genre_packs/*/worlds -mindepth 1 -maxdepth 1 -type d \! -path '*/aureate_span'`)
- `#136` — Phase 7 deferred: aureate_span rewrite from workshop

`#127` (Migration M3 — genre-tier old-shape file deletes for victoria/elemental_harmony/mutant_wasteland) is most likely a no-op now, since `space_opera/openings.yaml` was the only genre-tier old-shape file that existed and Task 26 already deleted it. Verify: `find genre_packs -maxdepth 2 -name openings.yaml`. If any genre-tier `openings.yaml` files surface, delete them as part of M3.

## Hard rules (learned the hard way during this work)

- **DO NOT use `git stash`** — not even `git stash --keep-index`. Two implementer subagents tripped this trap. Use `git diff <ref>` / `git show <ref>:path` for read-only inspection. Branches and commits are free; checkpoint via commit when needed.
- **Coyote Star** is the canonical world slug. The earlier "Coyote Reach" name was retired in commit `adb8e91` on develop and pulled in via the `feat/canned-openings` content-side merge.
- **Always run `pf namegen`** for any new authored NPC names. Never invent fantasy-default names ("Mira", "Kael", "Zara"). The cliche-judge will flag them and the names lack the cultural specificity the rest of the world establishes.
- **Spec authoring follows "rules in genre, flavor in world" (SOUL.md).** No per-world conditionals in Python; all tonal differences are achieved via authored prose + AVOID lists.

## Audience anchors (load-bearing for any prose authoring)

Per `CLAUDE.md` and the spec §0:

- **Keith** — forever-GM-finally-playing; the opening must feel *chosen*, not rolled. The narrator must be good enough to fool a 40-year tabletop veteran.
- **James** — narrative-first; cozy crew-as-crew framing for solo, Becky Chambers / Firefly texture.
- **Alex** — slow typist; **NO turn-1 question**, declarative close, the player can sit in the breath as long as they want.
- **Sebastien** — mechanics-first; OTEL spans visible, bond-tier name-form upgrade visible from turn 1.

When writing prose for any of the migrations, hold every line against these readers. "Would Alex feel rushed by this?" is sharper than "is this good UX?"

## What NOT to do

- Don't loosen Validator 7 to make the gate pass. The fail-loud is the design (spec §8.4).
- Don't author M2 prose quickly to "just satisfy the validators" — the cliche-judge will flag it, same as it flagged the aureate_span bootstrap.
- Don't promote `aureate_span` out of workshop without a Phase 7 rewrite that addresses the cliche-judge findings.
- Don't push the branches without explicit user authorization.
- Don't skip the cliche-judge pass on M2 prose.

---

*Handoff written 2026-05-01. Branch state captured at server `08eebde`, content `24c4f51`. Both branches local-only, unpushed.*
