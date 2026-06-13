---
parent: 106
---

# Story 106-4 Context

## Title
Consumable use in confrontation (KEITH PRIORITY) — wire the heal-potion effect to the HpPool (consume half is wired, effect half is not; magnitude sourced from the WWN SRD healing entry, not invented) AND make beat generation scan carried inventory to surface item-use beats (drink/throw/read) with the item consumed on use; includes the guaranteed-heal-slot content decision so the kit is deterministic for testing

## Metadata
- **Story ID:** 106-4
- **Type:** feature
- **Points:** 5
- **Priority:** p1
- **Workflow:** tdd
- **Repos:** server, content
- **Epic:** 106 — WWN combat hardening for beneath_sunden

## Problem

This story bundles **three tightly-coupled findings** from the 2026-06-13 single-player
combat playtest of `caverns_and_claudes/beneath_sunden` (WWN ruleset, ADR-117), OTEL +
save-forensics confirmed. They are bundled because they are **one feature with a strict
dependency order**: surfacing a "Drink Healing Draught" beat is worthless if drinking a
potion heals nothing. The heal effect must work *before* the beat-scan is meaningful — the
GAP is hollow otherwise.

### Finding 1 — HEAL EFFECT BUG (the foundation; do this first)

At 1/10 HP, a player drank a Potion of Mending. Forensics (pingpong lines 149–163):
1. ✅ **Item consumed** — server log `state.inventory_update player=Harpo turn=8 …
   consumed=['potion of mending']`; snapshot inventory 2→1.
2. ✅ **Narrator described a heal** — "the warmth spreads fast, sealing something ragged
   under the ribs."
3. ❌ **HP did NOT change** — `core.hp = {current:1, max:10}` before AND after; **no
   `state_patch.hp` span, no heal event** anywhere in the turn-8 log.

Classic convincing-narration-with-zero-mechanical-backing. The lie detector fired.

**Root cause (code-confirmed):** the consume half is wired; the effect half is not.
- `sidequest-server/sidequest/server/narration_apply.py` — `_apply_narration_result_to_snapshot`
  (def `narration_apply.py:3511`). The `items_consumed` loop runs at **lines 4765–4823**;
  the actual item removal is **`narration_apply.py:4800–4802`**
  (`recipient_char.core.inventory.items.pop(idx)` → `consumed_names.append(...)`). There is
  **NO consumable-effect application** between the pop and the append — nothing reads the
  item's `healing` tag/magnitude and applies HP. **This (line ~4802, after pop, before
  append) is exactly where the effect hook belongs.**
- The HP-apply path already exists and emits OTEL: `apply_beat_hp_channel()` at
  `sidequest-server/sidequest/game/beat_kinds.py:357–386` calls `target.apply_hp_delta(...)`
  and emits `state_patch_hp_span(...)` → span name **`state_patch.hp`**
  (`sidequest-server/sidequest/telemetry/spans/state_patch.py:150,165`). `HpPool.apply_delta`
  already supports a **positive** delta (heal), capped at max
  (`creature_core.py` `apply_delta` — "Positive delta increases current (capped at max)").
  So the heal *mechanism* is reusable; only the consumable→HP wiring is absent.

**Heal magnitude — NO INVENTED NUMBER.** Standing ruling (Keith, 2026-06-13,
`.pennyfarthing/sidecars/gm-decisions.md` "WWN SRD is the authority"): source the heal
amount from the **WWN SRD** healing entry, citing which SRD rule was used; only escalate to
Keith if the SRD is genuinely silent. The `potion_healing` item does **not** carry a heal
field today (see Finding 3); a heal-amount field must be added to the content item and the
model.

### Finding 2 — BEAT-SCAN GAP (← KEITH'S EXPLICIT PRIORITY ASK)

Operator confirmed verbatim: *"if they did [have a potion] would it provide a beat — that's
what I want fixed."* (pingpong lines 194–207.)

The confrontation beat menu is a **filtered archetype list** (combat: Strike / Brace /
Break Contact / Committed Blow; chase: Duck Through / Barricade / Douse Torch / Sprint). It
does **NOT scan the player's carried inventory** to offer item-use beats, and free-text Enter
is locked during confrontation — so there is **no mechanism at all** to drink a potion, throw
oil, or read a scroll once a confrontation is seated. SOUL angle: a **closed verb-set at the
most consequential moment** is a Zork-Problem / Agency violation — the player can articulate
"I drink my potion" but the UI offers no path.

**Code-confirmed seams:**
- Beat kinds enum (strike/brace/push/angle): `sidequest-server/sidequest/game/beat_kinds.py:27–39`.
  Beats themselves are authored per-confrontation in genre-pack YAML as `BeatDef` lists.
- **The single source-of-truth beat filter** is `beats_available_for(confrontation, class_def,
  spell_slots_remaining, prepared_spells, spellcasting)` at
  `sidequest-server/sidequest/game/beat_filter.py:35–102`. **It has NO inventory parameter
  today** — it cannot see the character's items. This is where inventory-scan logic to inject
  "Drink Healing Draught"/"Hurl Oil" beats must hook in (add an inventory arg + a gate that
  scans for `healing`/`throwable`/`consumable`-tagged items).
- Two call sites must thread the inventory through:
  (a) narrator prompt menu — `sidequest-server/sidequest/agents/narrator.py:429` (in
  `build_encounter_context`), and (b) the UI confrontation payload —
  `sidequest-server/sidequest/server/dispatch/confrontation.py:227–240`
  (`build_confrontation_payload`). The character's inventory is available on
  `CreatureCore.inventory.items` (`creature_core.py`).
- The free-text lock is enforced at dispatch: `DICE_THROW` requires a valid `beat_id` while
  an encounter is active —
  `sidequest-server/sidequest/server/dispatch/dice.py:345–371` (missing/unknown beat_id →
  `DiceDispatchError`). So an item-use beat must be a **real `BeatDef`-shaped option with an
  id** the dispatcher will accept, not a free-text bypass.

### Finding 3 — CONTENT DECISION (flagged for Keith; record both branches)

`equipment_tables.yaml`
(`sidequest-content/genre_packs/caverns_and_claudes/equipment_tables.yaml:56–75`) sets
`warrior_kit.consumable`, `expert_kit.consumable`, and `mage_kit.consumable` all to
`[rations_day, waterskin, potion_healing]` with `rolls_per_slot.consumable: 3` (lines 42–45).
The builder rolls 3 times **with replacement** from the 3-item pool
(`sidequest-server/sidequest/game/builder.py:2546–2548`, uniform `randrange`), so
**P(zero potions) = (2/3)³ ≈ 30%**. A Warrior can start with 0, 1, 2, or 3 potions. There is
**no guaranteed-slot mechanism** in the equipment table format today (only random pools +
`rolls_per_slot`). This makes the beat-scan test **flaky**: ~30% of fresh Warriors have no
consumable to exercise the scan against.

## Business Context

This is **Keith's explicit priority ask** within Epic 106 — he stated the beat-scan fix is
"what I want fixed," and the heal-effect bug is what makes that fix worth doing. The two
serve the project's most load-bearing fact: SideQuest exists so a 40-year career GM can be a
**player** without losing agency. Two CLAUDE.md doctrines are directly in play:

- **SOUL / Zork-Problem / Agency.** A confrontation that offers only Strike/Brace at the
  moment a player is at 1 HP — while a healing potion sits unusable in their pack — is the
  closed-verb-set failure SideQuest is built to avoid. The player can *say* "I drink my
  potion"; the system must be able to *do* it.
- **OTEL lie-detector.** The heal bug is the canonical failure the GM panel exists to catch:
  Claude wrote convincing heal prose with zero mechanical backing. A mechanics-first player
  (Sebastien/Jade) checking HP sees 1/10 and knows the heal was theater. Per the OTEL
  principle, every subsystem decision must emit a span — a heal that doesn't emit
  `state_patch.hp` is indistinguishable from improvisation.

Audience served: the lethal beneath_sunden ramp currently has **no in-combat heal path at
all** (Groucho died with no defensive option; Harpo won at 1 HP on luck). Wiring the heal
and surfacing it as a beat gives every table member a real survival play, and gives the
mechanics-first players (Sebastien/Jade) legible HP deltas in the player-facing beat-impact
chip.

## Technical Guardrails

- **Heal magnitude comes from the WWN SRD — no invented number.** Per the standing ruling
  (`.pennyfarthing/sidecars/gm-decisions.md`, 2026-06-13: "WWN SRD is the authority"), source
  the Potion of Mending heal amount (and whether it's fixed or dice) from the WWN SRD healing
  entry and **cite which SRD rule was used**. Note WWN's healing model is `system_strain`-based
  (`caverns_and_claudes/rules.yaml:56` already declares `system_strain`); confirm whether the
  potion restores HP, relieves strain, or both, against the SRD. Escalate to Keith **only** if
  the SRD is genuinely silent.
- **No silent fallback (CLAUDE.md "No Silent Fallbacks").** An effect that applies must emit
  an OTEL span. The heal MUST emit `state_patch.hp`
  (`telemetry/spans/state_patch.py:150`) with a positive delta, and the item-use beat MUST
  emit an inventory-mutation span. A heal that changes HP with no span is itself a bug — it
  defeats the lie-detector.
- **Reuse, don't reinvent (CLAUDE.md "Don't Reinvent").** The HP-apply path
  (`apply_beat_hp_channel` / `HpPool.apply_delta` with a positive delta) and the
  `state_patch.hp` span **already exist** — wire the consumable into them. The beat filter
  (`beats_available_for`) is the single source of truth for the menu — extend its signature,
  don't fork a parallel menu builder.
- **Item-use beats must be real, dispatchable beats.** Because dispatch requires a valid
  `beat_id` (`dispatch/dice.py:345–371`), an injected "Drink Healing Draught" must be a
  proper `BeatDef`-shaped option with an id the dispatcher accepts — not a free-text bypass
  and not a UI-only affordance the server will reject.
- **Wiring test required (CLAUDE.md "Every Test Suite Needs a Wiring Test").** Unit tests
  for the effect-apply and the inventory-scan are not enough: include an integration test
  proving (a) drinking a potion in the real `narration_apply` path moves HP and emits
  `state_patch.hp`, and (b) the inventory scan reaches the actual narrator/UI beat menu via
  `narrator.py:429` and `confrontation.py:227` — not just `beats_available_for` in isolation.
- **Heal-amount field is additive.** `CatalogItem`
  (`sidequest-server/sidequest/genre/models/inventory.py:145–166`) has `extra: "forbid"` and
  no heal field; the runtime dict builder (`item_catalog_resolution.py:59–87`) does not
  serialize one. Adding `heal_amount`/`heal_dice` requires updating BOTH the model and the
  dict builder, or the field will be silently dropped on resolution.

## Scope Boundaries

**In scope:**
- **Heal-effect wiring (Finding 1):** read the consumed item's healing tag/magnitude at the
  consume hook (`narration_apply.py` ~line 4802) and apply HP via the existing
  `apply_beat_hp_channel`/`HpPool` path, emitting `state_patch.hp`.
- **Heal-amount content field (Finding 3 mechanics):** add a heal-amount field to the
  `CatalogItem` model + runtime dict builder, and populate `potion_healing` in
  `caverns_and_claudes/inventory.yaml` (lines 283–293, currently fields only — no magnitude)
  with the **WWN-SRD-sourced** value.
- **Beat-menu inventory scan (Finding 2):** extend `beats_available_for`
  (`beat_filter.py:35`) to scan carried inventory and surface item-use beats
  (drink/throw/read), thread inventory from `narrator.py:429` and `confrontation.py:227`,
  and ensure committing the beat heals + consumes the item with OTEL (inventory mutation +
  `state_patch.hp` delta).

**Flagged for Keith (content decision — record both branches, do NOT silently pick one):**
- **Guaranteed dedicated heal slot vs intended random scarcity (Finding 3).**
  - *Branch A — guaranteed slot:* pull `potion_healing` out of the random `consumable` pool
    into its own guaranteed entry so every Warrior/Expert/Mage starts with exactly N heal
    potions. Makes the beat-scan test deterministic. Requires a new guaranteed-slot pattern
    in `equipment_tables.yaml` (none exists today). **Verification:** every fresh Warrior
    snapshot shows ≥1 Potion of Mending.
  - *Branch B — intended random scarcity:* leave the ~30%-zero random roll; heal is a lucky
    find, otherwise rest/Mage. Close the content half as wontfix with rationale recorded.
    **Implication:** the beat-scan test must seed a deterministic kit via fixture rather than
    rely on chargen, since chargen is ~30% empty.
  - The default for *this story's testing* is a deterministic kit (fixture-seeded if Keith
    chooses Branch B); the production kit composition is Keith's call.

**Out of scope (other Epic 106 / 107 stories):**
- Armor-equip / AC ramp (106-1); WWN reprisal-mitigation model (106-2); native edge/tag + XP
  ruleset-bleed gating (106-3); death-state coherence (106-5); narration knockdown/hit-truth
  guardrail (106-6).
- UI polish: confrontation panel portraits, scrapbook captions, narration register
  (Epic-excluded). Monster Manual / dungeon-scene cluster (Epic 107).
- Throwables/scrolls beyond what proves the inventory-scan generalizes — a healing drink is
  the load-bearing case; author oil/scroll beats only if cheap, otherwise note as follow-up.

## AC Context

The dependency order is load-bearing: **AC1–AC2 (heal works) gate AC3–AC4 (beat surfaces a
heal that heals).** A beat that drinks a potion that heals nothing is not done.

1. **Heal effect applies (out of combat).** At reduced HP, drinking a Potion of Mending
   increases the HP pool by the **WWN-SRD-sourced** heal amount, emits a `state_patch.hp`
   (heal) OTEL span with a positive delta, consumes the item, and the narration matches the
   real new HP — no convincing-prose-with-zero-HP-change. (Repro from pingpong line 162.)
2. **No silent heal.** The heal amount is the WWN-SRD value (cite the SRD rule); the engine
   never invents a number, and an HP change without a `state_patch.hp` span is treated as a
   failure. The `potion_healing` content item and `CatalogItem` model carry the heal-amount
   field end-to-end (model + runtime dict + YAML).
3. **Item-use beat surfaces in confrontation.** In combat, a PC carrying a healing consumable
   sees a use/drink beat (e.g. "Drink Healing Draught") in the confrontation beat menu —
   produced by the inventory scan in `beats_available_for`, reaching both the narrator menu
   (`narrator.py:429`) and the UI payload (`confrontation.py:227`).
4. **Committing the item-use beat heals + consumes.** Selecting the drink beat heals the PC,
   consumes the item, emits OTEL (inventory mutation + HP delta `state_patch.hp`), and the
   change shows in the **beat-impact chip**. The beat is a real dispatchable `BeatDef` with an
   id (passes `dispatch/dice.py:345–371` beat_id validation).
5. **Deterministic test kit.** The beat-scan integration test runs against a kit that
   deterministically contains a healing consumable (guaranteed slot if Keith picks Branch A;
   fixture-seeded otherwise), so the test is not subject to the ~30%-empty chargen roll.
6. **Wiring test present.** At least one integration test exercises the real production path
   end-to-end (consume → heal → span via `narration_apply`; inventory → beat menu via the
   narrator/UI call sites), per the CLAUDE.md wiring-test rule.

## Dependencies & Notes
- **Independent of sibling 106 stories** (armor 106-1, reprisal 106-2, bleed 106-3, death
  106-5, narration 106-6) — none block this, but 106-2's reprisal-mitigation work and this
  beat-menu work both touch the confrontation loop; coordinate if landed concurrently.
- **WWN SRD is the correctness oracle** for the heal magnitude — the same standing ruling
  governing 106-1 (AC) and 106-3 (XP). Confirm HP-vs-system_strain semantics against the SRD
  before authoring the number.
- The earlier "content half done" note in the pingpong (adding `potion_healing` to
  warrior/expert kits) made a potion **possible, not guaranteed** — Finding 3 is the open
  loop that the content decision closes.
