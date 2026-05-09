# Caverns & Claudes — Chargen Big Improvements

**Date:** 2026-05-09
**Author:** Architect (Major Margaret Houlihan)
**Genre pack:** `caverns_and_claudes` (single pack scope)
**Status:** approved-design — pending writing-plans

## 1. Overview

Today's C&C chargen is a five-scene scripted flow whose load-bearing mechanical step
— the 3d6-in-order stat roll — is invisible. The server runs a class-qualification
reroll loop silently and reveals only a final stat block. The narrator vouches for
math the player never sees. This is exactly the Sebastien lie-detector failure mode
SOUL warns about, and it leaves James and Alex without the satisfying
ritual-of-creation a B/X-style RPG promises.

This design replaces the silent flow with **player-visible 3d6, player-driven stat
arrangement, and a reject-and-reroll escape valve**, plus a real
background-and-description scene with autogen for low-typing-tolerance players. It
also drops two B/X scaffolds the playgroup has never wanted: prime-requisite XP
bonuses, and the manual-edit affordance on the confirmation screen.

**Goal:** Make the moment of character creation a real mechanical event the player
performs, not a result the server hands them. Make Sebastien see the dice. Make
Alex able to finish without typing. Make James feel like he rolled.

**Approach:** Wire the existing 3D dice overlay (ADR-074 / ADR-075 — proposed) into
chargen, with graceful degrade to numeric reveal if those ADRs slip. Add one
arrangement scene with a click-to-assign pool and a live-qualifying class panel.
Replace the silent kit prelude with a story scene that folds pronouns, background,
and description together. Remove the silent reroll loop, the prime-requisite XP
bonus, and the manual-edit Pencil button.

**Deliverables:**
1. This spec (scene flow + schema + content + UI contract).
2. Server changes (Dev story) — see §4.
3. UI changes (Dev story) — see §5.
4. Content changes (GM lane) — see §6.

## 2. Scene flow

The new flow is six scenes. Scene IDs in `char_creation.yaml`:

| # | ID                | Purpose                                                                           |
| - | ----------------- | --------------------------------------------------------------------------------- |
| 1 | `the_roll`        | 3d6 ×6 visible on dice overlay; results land in pool                              |
| 2 | `the_arrangement` | Click-to-assign pool → six stat slots; live-qualify panel; **reject-and-reroll**  |
| 3 | `the_calling`     | Only the classes the arrangement qualifies for                                    |
| 4 | `the_story`       | Pronouns + background + description; autogen button for the two text fields      |
| 5 | `the_kit`         | Auto reveal of class kit + starting coin (read-only)                              |
| 6 | `the_mouth`       | Unchanged bookend                                                                 |

### 2.1 — `the_roll`

Brecca's framing changes from "Roll them in order" to "in any order you can stomach."
Six 3d6 rolls fire sequentially through the dice protocol (ADR-074), ~400ms apart.
Each roll's three dice land on the dice tray, sum is computed, and the sum joins a
visible pool above the tray.

**No reject button on this scene.** The player watches all six land. Reject is
arrangement-only.

`mechanical_effects`:
```yaml
stat_generation: roll_3d6_arrange_visible   # replaces roll_3d6_strict
```

The old `class_qualification_loop: true` flag is **deleted** — qualification is
checked at arrangement-confirm time, not at roll time.

### 2.2 — `the_arrangement`

Layout (UI):

```
┌──────────────────────────────────────────────┐
│ Pool:  [12]  [9]   [15]  [8]   [14]  [11]    │
├──────────────────────────────────────────────┤
│ STR ___  DEX ___  CON ___                    │
│ INT ___  WIS ___  CHA ___                    │
├──────────────────────────────────────────────┤
│ Qualifies:                                   │
│   Fighter  ✓   (STR 9+)                      │
│   Mage     ✗   needs INT 9+                  │
│   Cleric   ✗   needs WIS 9+                  │
│   Thief    ✓   (DEX 9+)                      │
├──────────────────────────────────────────────┤
│   [Reject these dice]   [Confirm arrangement]│
└──────────────────────────────────────────────┘
```

**Interaction:**
- Tap a number in the pool → the number highlights.
- Tap an empty slot → the highlighted number lands there.
- Tap a filled slot → its number returns to the pool.
- The qualifying-class panel updates after every assignment.
- "Confirm arrangement" enables only when all six slots are filled **and** at least one class qualifies (per §3.1 trap-prevention).
- "Reject these dice" reseeds: returns to scene 1 and rerolls all six. No partial reroll, no per-die reroll.

**Class-qualification probabilities.** With four B/X-classic classes
(Fighter STR ≥9, Mage INT ≥9, Cleric WIS ≥9, Thief DEX ≥9) and 3d6-arrange,
the probability that *zero* classes qualify equals the probability that all six
3d6 rolls fall below 9, ≈ 0.025%. The reject button is therefore catharsis +
optimization re-rolls, not a frequent failure handler. This is fine.

`mechanical_effects`:
```yaml
assignment_required: true
qualifying_class_filter: archetype_constraints   # reuse existing predicate
allow_reject: true
```

### 2.3 — `the_calling`

Unchanged from today's narration ("These are the trades the bones will let you
take"), but the choices array is **server-filtered** — only classes whose minimum
is satisfied by the current arrangement appear. Removes the today-misleading
"(STR 9+)" hints from descriptions, since unqualifying classes are gone.

### 2.4 — `the_story`

New scene. Replaces today's `pronouns` scene and absorbs the prelude work that the
silent kit scene used to gate.

UI shape:

```
┌──────────────────────────────────────────────┐
│ Brecca dips the quill and looks up. "For the │
│ tally. In case you don't come back."         │
├──────────────────────────────────────────────┤
│ Pronouns:  ( ) she/her                       │
│            ( ) he/him                        │
│            ( ) they/them                     │
│            ( ) ____________ (freeform)       │
├──────────────────────────────────────────────┤
│ Background:                                  │
│ [textarea — e.g. "former apprentice to a    ]│
│ [one-eyed alchemist. Ran when his fourth   ]│
│ [experiment killed his third assistant."   ]│
├──────────────────────────────────────────────┤
│ Description:                                 │
│ [textarea — e.g. "tall, soot-stained,      ]│
│ [missing a tooth, walks with a slight limp"]│
├──────────────────────────────────────────────┤
│ [Let Brecca tell my story]   [Confirm]       │
└──────────────────────────────────────────────┘
```

**Autogen button:** generates **background and description only**. Pronouns are
not auto-filled — the player must select. The player can edit the autogen result
before confirming. Empty text fields are allowed at confirm; autogen is an
affordance, not a requirement.

**Autogen source:** server reads the existing `caverns_and_claudes/backstory_tables.yaml`
and rolls deterministically with a seed sent down to the client for re-roll
visibility (the player can tap autogen multiple times for variants). **No Claude
call** — pure table roll, fast for Alex, no narrator-latency tax.

`mechanical_effects`:
```yaml
identity_capture:
  pronouns_required: true
  background_optional: true
  description_optional: true
background_autogen_source: backstory_tables
```

### 2.5 — `the_kit`

Same narration as today. Choices remain empty. `class_kit` equipment generation
runs server-side (existing behavior). UI reveals the resulting kit + starting
coin as a read-only itemized list with a single "Continue" button. **No
shopping, no swapping.**

### 2.6 — `the_mouth`

Unchanged.

## 3. What gets removed

### 3.1 Silent reroll loop

`mechanical_effects.class_qualification_loop` is deleted from `the_roll`. The
server no longer rerolls behind the curtain. The new mechanism is:

- Player rolls (visibly).
- Player arranges.
- If no class qualifies (≈ 0.025%), the qualifying-class panel shows all four
  failures and the only way forward is **Reject these dice** → back to roll.
- The "Confirm arrangement" button stays disabled until at least one class
  qualifies *and* all six slots are filled, so the player cannot trap themselves
  into a no-class state.

### 3.2 Prime-requisite XP bonus

`caverns_and_claudes/progression.yaml` — remove any `prime_req_bonus` table /
field for the four classic classes. Per playgroup judgment: piling a stat
discount on top of class choice is mechanical clutter the table never wanted.

### 3.3 Manual edit (Pencil) affordance

`CharacterCreation.tsx` — remove the per-section Pencil edit button on the
confirmation screen, plus the `onRespond({action: "edit", target_step: index})`
emission and the matching server handler. Characters evolve through play; chargen
is not an editable form.

## 4. Server changes

### 4.1 Builder FSM (ADR-015)

`CharacterBuilder` adds two pieces of state, both reset on reject:

```python
arrangement_pool: list[int]                   # six 3d6 totals, indexable
arrangement_assignment: dict[StatName, int | None]  # six slots, None until assigned
```

State transitions:

| From            | Event                          | To                |
| --------------- | ------------------------------ | ----------------- |
| `ROLLING`       | six rolls confirmed by client  | `ARRANGING`       |
| `ARRANGING`     | reject pressed                 | `ROLLING` (clear) |
| `ARRANGING`     | confirm + qualifying ≥1        | `CLASS_SELECT`    |
| `CLASS_SELECT`  | class chosen                   | `STORY`           |
| `STORY`         | confirm                        | `KIT`             |
| `KIT`           | continue                       | `MOUTH`           |
| `MOUTH`         | continue                       | (chargen done)    |

Reject from `ARRANGING` is the only backward transition. Forward-only otherwise.
The `STORY` state replaces today's `PRONOUNS` state.

### 4.2 Dice protocol wiring (ADR-074)

`the_roll` resolution emits six sequential `dice_roll` round-trips:

```
server → client : dice_roll {kind: "3d6", roll_id: "chargen.roll.0"}
client → server : dice_roll_played {roll_id: "chargen.roll.0"}
server → client : dice_roll_revealed {roll_id: "chargen.roll.0", result: 12}
... ×6 ...
server → client : scene_advance {to: "the_arrangement", pool: [12,9,15,8,14,11]}
```

**Graceful degrade (ADR-006):** if ADR-074 has not shipped, server falls back
to immediate-reveal numeric mode — emits all six results in one payload, UI
shows them in the pool without animation. This design is forward-compatible:
the same payload shape (`pool: [int×6]`) carries both modes.

### 4.3 Qualifying-class predicate

Reuses `archetype_constraints.yaml` (already wired for today's silent loop). The
predicate is exported from the existing class-qualification code path and called
twice:

1. After every assignment, server replies with `qualifying_classes: list[str]` so the UI panel updates live. (Cheap — pure dict lookup.)
2. At confirm-arrangement, server validates that the qualifying set is non-empty before transitioning to `CLASS_SELECT`.

### 4.4 Backstory autogen endpoint

```
server ← client : story_autogen_request {seed?: int}
server → client : story_autogen_result {seed, background, description}
```

Server reads `caverns_and_claudes/backstory_tables.yaml`, rolls with the supplied
seed (or generates a fresh one), formats the result. Stateless — no FSM
side-effect; the player still has to confirm with their own (possibly edited)
text.

### 4.5 New chargen YAML schema fields

`CharCreationScene` model (`sidequest.genre.models.character`):

```python
class CharCreationScene(BaseModel):
    model_config = {"extra": "forbid"}
    # ... existing fields ...
    mechanical_effects: dict[str, Any] | None = None  # already present
```

The `mechanical_effects` dict is loose-keyed today; this design adds three
new recognized keys (`assignment_required`, `qualifying_class_filter`,
`allow_reject` for the_arrangement; `identity_capture` for the_story;
`background_autogen_source` for the_story). No new pydantic submodels — the
loose dict carries genre-pack-specific dispatch as it does today. Adding
strict submodels is **out of scope** for this story; revisit if a future
genre pack adds another arrange-style flow.

## 5. UI changes (`sidequest-ui`)

### 5.1 `CharacterCreation.tsx`

Two new render branches keyed by `scene.input_type`:

- **`"stat_arrange"`** — pool + slots + qualifying-class panel + reject + confirm.
  Maintains arrangement state locally; commits via `onRespond({phase: "arrange_confirm", assignment: {...}})`. Reject sends `onRespond({phase: "arrange_reject"})`.

- **`"story"`** — pronouns radio + freeform textbox + two textareas + autogen + confirm.
  Autogen tap sends `onRespond({phase: "story_autogen", seed?: number})` and waits for the server's `story_autogen_result`, which the UI then drops into the textareas. The player edits and presses Confirm to send `onRespond({phase: "story_confirm", pronouns, background, description})`.

### 5.2 Confirmation screen

Remove the per-section Pencil button (`button[data-testid^="review-edit-"]`) and
its onClick. The "Create Character" / "Go Back" pair remains. `Go Back` continues
to step backward through scenes one at a time (existing behavior).

### 5.3 Live-qualifying class panel

The qualifying-class panel reads from `scene.qualifying_classes: string[]` plus a
static `scene.class_requirements: {name, requirement_label}[]` so it can render
both qualified and disqualified rows with their min-stat hint. Both arrive in the
arrangement scene's payload; client recomputes the panel locally on each
assignment to avoid a server round-trip per click. (Server still re-validates at
confirm.)

## 6. Content changes (`sidequest-content`)

### 6.1 `caverns_and_claudes/char_creation.yaml`

Replace the existing five-scene list with the six-scene list described in §2.
Narration cues:

- `the_roll` — "in any order you can stomach"; loading_text "Brecca counts the bones..."
- `the_arrangement` — narration: "Brecca taps the table once. 'Now arrange them. The trade is yours to choose, if the bones allow it.'"
- `the_calling` — unchanged narration; choices generated server-side.
- `the_story` — narration as in §2.4 above.
- `the_kit` — unchanged narration; choices empty.
- `the_mouth` — unchanged.

### 6.2 `caverns_and_claudes/progression.yaml`

Remove `prime_req_bonus` field/table from each of the four classic classes if
present. Verify with a load test that no consumer expects the field.

### 6.3 `caverns_and_claudes/archetype_constraints.yaml`

No edits — predicates are already correct for the new flow. Confirm-only.

### 6.4 `caverns_and_claudes/backstory_tables.yaml`

No edits required for v1. Tables are already authored. (If audit shows tables
generate thin or repetitive output, that is a follow-on content story, not a
blocker for this design.)

## 7. OTEL events

Per ADR-058 and SOUL's lie-detector principle, every chargen mechanical decision
emits a watcher event:

| Event                         | Trigger                              | Payload                                          |
| ----------------------------- | ------------------------------------ | ------------------------------------------------ |
| `chargen.roll.die`            | each of the six 3d6 rolls            | `{index, dice: [a,b,c], total}`                  |
| `chargen.roll.complete`       | all six revealed                     | `{pool: [int×6]}`                                |
| `chargen.arrange.assign`      | each slot assignment                 | `{stat, value, qualifying_after: [class…]}`      |
| `chargen.arrange.reject`      | reject button                        | `{rejected_pool: [int×6]}`                       |
| `chargen.arrange.confirm`     | confirm button                       | `{assignment: {STR:int, …}, qualifying: [class…]}` |
| `chargen.class.selected`      | class chosen                         | `{class_name, qualifying_options: [class…]}`     |
| `chargen.story.autogen`       | autogen button pressed               | `{seed, background_len, description_len}`        |
| `chargen.story.confirm`       | story confirmed                      | `{pronouns, background_len, description_len, autogen_used: bool}` |

Sebastien must be able to open the GM panel mid-chargen and see the rolls, the
qualification math, and the assignment audit trail. If those events don't fire,
the GM panel will be silent and that's a wiring bug, not a feature gap.

## 8. Risks and open questions

- **R1 — ADR-074 / ADR-075 not yet accepted.** Both are *proposed* per the ADR
  index. This design bets on shipping them first; if they slip, the
  graceful-degrade path (§4.2) keeps chargen functional with numeric reveal.
  No design rework needed when the dice ADRs land — same payload shape.

- **R2 — Reject button utility is mostly catharsis.** Probability of zero
  qualifying classes ≈ 0.025%. The button still earns its keep because Sebastien
  will reroll for optimization, not for qualification. Worth shipping.

- **R3 — Backstory autogen quality.** `backstory_tables.yaml` may produce thin
  results. Mitigation: output is editable, autogen is rerollable. If audit
  reveals systemic thinness, that's a content story, not a chargen blocker.

- **R4 — Manual-edit removal regret.** The Pencil affordance works today and
  serves a real need (typo on character name). Removing it is reversible — one
  component, one server message. If post-playtest feedback flags a need, restore
  it with a single follow-on story.

- **R5 — Live-qualifying panel server load.** Re-validating after every
  assignment click could chatter. Mitigation: client recomputes locally from a
  static class-requirements payload sent once with the arrangement scene; server
  only revalidates at confirm. (See §5.3.) No round-trip per click.

## 9. Out of scope

- Stat-method choice (3d6-in-order, 4d6-drop-lowest, point-buy). Locked to 3d6-arrange.
- Hit Die / starting HP roll. C&C uses momentum/edge/fate per ADR-014; no HP exists.
- Alignment, starting age, encumbrance — not requested.
- Equipment shopping or kit swapping. Auto kit + coin only.
- Manual edit affordance. Removed; characters evolve through play.
- Strict pydantic submodels for `mechanical_effects`. The loose dict carries
  this design's new keys; revisit if/when another pack adds an arrange flow.

## 10. Repo split (for writing-plans)

This design touches three repos; PRs target `develop` per `repos.yaml`:

| Repo                | Scope                                                                              |
| ------------------- | ---------------------------------------------------------------------------------- |
| `sidequest-server`  | Builder FSM states, dice protocol wiring, qualifying-class predicate hookup, autogen endpoint, OTEL events, prime-req bonus removal |
| `sidequest-ui`      | `CharacterCreation.tsx` two new render branches + Pencil removal + qualifying-class panel |
| `sidequest-content` | `char_creation.yaml` rewrite + `progression.yaml` prime-req removal in `caverns_and_claudes` |

The orchestrator repo holds this spec and the implementation plan only — no code.
