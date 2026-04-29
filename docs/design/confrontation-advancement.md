# Confrontation-Driven Advancement

**Status:** Committed model, 2026-04-28
**Audience:** Architect, Dev, GM, content authors
**Supersedes (in part):** ADR-021's "Milestone Leveling" track and "Affinity Tier" tier-up trigger logic
**Companion docs:** `magic-taxonomy.md`, `visible-ledger-and-otel.md`, `magic-plugins/README.md`, ADR-033 (Confrontation Engine)

## The Promise

Characters in SideQuest do not advance through accumulated keyword frequency, ambient narrative weight, or unspecified play-time. Characters advance because they **survived (or failed) a confrontation**, and the confrontation produced an outcome that *changes the sheet*.

Equivalent statement: **the character is the running total of confrontation outcomes.**

## The Five Locked Decisions

1. **Mandatory output.** Every confrontation produces *at least one* advancement event. No confrontation is mechanically null. If a scene wouldn't change the sheet, it isn't a confrontation — it's exposition, and Cut the Dull Bits applies (SOUL #10).
2. **Player-facing reveal.** When a confrontation resolves, the player sees what changed. Explicit panel callout, not pure narrative inference. The mechanical reality is communicated alongside the prose.
3. **No decay.** Outputs are sticky. A tier earned is a tier kept. A bond formed remains until specifically broken by a later confrontation. The character accumulates; they do not slide back.
4. **Failure also advances.** Losing a confrontation produces a *different output menu* than winning, but it produces real growth. The character that loses is not the same character afterward. Witcher-mood: "you survived this; you're harder now, you trust less, the gun is heavier." Refusing the confrontation altogether also advances — different output menu again.
5. **Confrontations carry plugin tie-ins.** Each magic plugin declares the confrontation type(s) it participates in. The plugin's `confrontations:` block defines the moves, stakes, branches, and outputs specific to that plugin's magic. The Bargain is `bargained_for_v1`'s confrontation. The Working is the same plugin's lower-stakes variant. The Trial belongs to the divine_v1 plugin. Items participating in confrontations bring their own item-specific outputs.

## Confrontation Outcome Schema

A confrontation type defines its outcome branches and the advancement outputs each branch produces:

```yaml
confrontation:
  id: the_bargain
  label: "The Bargain"
  genres: [heavy_metal]
  plugin: bargained_for_v1     # if plugin-anchored

  # Resource pool — driven by ADR-033 confrontation engine
  resource_pool:
    primary: obligation
    secondary: vitality

  # Stakes declaration
  stakes:
    declared_at_start: true    # The Bargain requires the price be named upfront
    hidden_dimensions: false   # nothing under the table for this confrontation type
                               # (other confrontations may have hidden cost reveals)

  # Outcome branches — exhaustive
  outcomes:
    - branch: clear_win
      description: "You got what you wanted; the bill is fair."
      mandatory_outputs:
        - type: pact_tier
          delta: +1
        - type: faction_standing
          target_kind: faction
          target_id: <world-instantiated>
          delta: +1
      optional_outputs:
        - type: item_bond
        - type: ally_named

    - branch: pyrrhic_win
      description: "You got it, but the bill was worse than you knew."
      mandatory_outputs:
        - type: pact_tier
          delta: +1
        - type: scar
          severity: major
        - type: faction_standing
          delta: 0           # they got what they wanted; the Guild is neutral
      optional_outputs:
        - type: counter_dispatched
        - type: ledger_lock          # an obligation bar locks at high

    - branch: clear_loss
      description: "You did not get it, and the bill came due anyway."
      mandatory_outputs:
        - type: scar
          severity: major
        - type: ledger_lock
          bar: obligation
          description: "A debt you cannot pay this session"
        - type: identity_shift
          axis: ocean.agreeableness
          delta: -0.05
      optional_outputs:
        - type: enemy_made
        - type: mechanism_revoked

    - branch: refused
      description: "You walked away. The Guild remembers."
      mandatory_outputs:
        - type: faction_standing
          delta: -1
        - type: scar
          severity: minor
          axis: pride
      optional_outputs: []

  # How is advancement revealed to the player at the outcome moment?
  reveal:
    mode: explicit
    timing: at_outcome
    format: panel_callout       # the visible ledger panel shows the deltas
                                # alongside the narrator's prose
    suppression: none           # always shown; Decision #2 is locked

  # OTEL span emitted at outcome
  otel_span:
    span_name: confrontation.outcome
    required_attributes:
      - confrontation_id
      - branch
      - mandatory_outputs_emitted   # array of {type, target, delta}
      - optional_outputs_chosen     # array — possibly empty
      - resource_pool_final
      - mechanism_engaged           # carries over from confrontation moves
    on_violation: gm_panel_red_flag
```

## Output Type Catalog

These are the structural advancement outputs available to confrontation branches. Plugin specs and genre `confrontations.yaml` files draw from this set.

| Output type | Description | Decay |
|---|---|---|
| `level_up` | Genre-traditional level (caverns_and_claudes OSR, elemental_harmony tier 1→2) | None |
| `pact_tier` | Depth of relationship with a magic source (bargained / divine / learned). See three-axis note below. | None |
| `control_tier` | Innate-only: discipline over the wild thing the character *is*. Higher tier = less involuntary expression, more aim. | None |
| `faction_standing` | +/− with a named faction | None |
| `bond` | New relationship (NPC, item, place, spirit) | None |
| `bond_broken` | Existing bond severed | N/A |
| `item_bond` | A wielded/held item bonds to character; gains personality reactivity | None |
| `item_unbond` | Item rejects character; refuses to fire / answer | N/A |
| `scar` | Visible mark — physical, psychic, social, moral. Severity: minor / major / defining | None |
| `reputation_tier` | Karma-bar promotion to a new social tier (spaghetti_western "stranger" → "the man with no name") | None |
| `mechanism_unlocked` | New delivery mechanism becomes available (you've earned the right to bargain at the Crossroads) | None |
| `mechanism_revoked` | A delivery mechanism becomes unavailable (the Guild has cast you out) | N/A |
| `affinity_tier` | ADR-021 affinity advanced (kept; trigger now confrontation-driven) | None |
| `secret_known` | Player learns something the world tries to keep hidden | None |
| `identity_shift` | OCEAN axis shifts; the character is becoming someone else | None |
| `ledger_lock` | A cost-bar locks high; cannot be discharged this session | Resolves only via specific confrontation |
| `counter_dispatched` | A counter-archetype NPC is dispatched against the character | N/A |
| `enemy_made` | A specific named NPC becomes an antagonist | None |
| `wealth_tier` | ADR-021 wealth tier shifts | None |
| `vehicle_mod` / `gear_mod` | A named item gains a permanent modification | None |
| `crew_bond` | Crew/party-level bond changes | None |
| `world_state` | A diegetic fact in the world flips | None |
| `ledger_bar_rise` | A specific cost bar rises by `delta` | Bar is in-session pool; advancement is the delta itself being recorded |
| `ledger_bar_fall` | A specific cost bar falls by `delta` (only for bidirectional bars) | Same |
| `ledger_bar_set` | A specific cost bar is initialized at `level` (used at acquisition events) | Same |
| `ledger_bar_discharge` | A specific cost bar is paid down (only for monotonic-up bars; The Calling, The Severance) | Same |
| `ledger_lock` | A cost-bar locks high; cannot be discharged this session | Resolves only via specific confrontation |
| `vitality_cost` | A one-time vitality hit not tied to a tracked bar (used when a refused-action hurts the character) | None |

The "Decay: None" rule is universal except for `ledger_lock`. **Decision #3 is binding** — for *character advancement outputs*. World-state bars (e.g. divine_v1's `Hunger`, which is shared across all worshippers of a god) MAY decay slightly to model background activity outside the player's view; that is a property of the *bar*, not of the *output event*. The output event itself (the moment Hunger rose by 0.5) is recorded permanently on the character's contribution to the world's state. Decay applies to the world's collective bar, not to the character's footprint on it.

### Output target_kind

Several output types specify a target. The `target_kind` field disambiguates:

| `target_kind` | Used when | Examples |
|---|---|---|
| `character` | Output applies to the character themselves | `pact_tier`, `identity_shift`, most `scar` |
| `item` | Output applies to a named item (item-as-NPC) | `pact_tier` on a deeply-bonded weapon; `bond` to an item |
| `faction` | Output applies to a faction relationship | `faction_standing`, `bond` with a faction |
| `patron` | Output applies to a sentient patron entity | `bond` to a patron, `bond_broken` from patron |
| `bond_pair` | Output applies to a relationship between two characters | Multiplayer crew-bonds, party-internal |
| `place` | Output applies to a location relationship | Standing-with-a-place after pilgrimage; gothic "the house remembers" |

### Cross-plugin advancement

Some confrontation outcomes advance the character along a *different* plugin's track. Example: The Severance in `bargained_for_v1` clear_win includes an optional `pact_tier` output with `target_plugin: another_plugin` — breaking the pact opens the door to a new path (an Innate awakening, an Item adoption, a Divine calling). Item Legacy's Renunciation has the same shape.

Cross-plugin outputs are a feature, not a hack. They are how characters move between magic systems through the natural arc of confrontation outcomes. Schema: `target_plugin: <plugin_id>`.

### Three tier-axes coexist intentionally

`pact_tier`, `control_tier`, and `discipline_tier` (the last not yet registered — it lands when a learned-using world ships) measure different things on the same character sheet, and a character may have any subset simultaneously:

| Axis | What it measures | Plugin owners |
|---|---|---|
| `pact_tier` | depth of relationship with the magic source | bargained, divine, learned |
| `control_tier` | discipline over the wild thing the character *is* | innate |
| `discipline_tier` | mastery within a taught tradition (deferred — registers when first learned-using world ships) | learned |

A voidborn at `control_tier 3` may have *no* `pact_tier` — there is no source to bond with; the character *is* the source. A bargained_for character with `pact_tier 3` may have no `control_tier` — they don't have to control anything; the patron does the work. Collapsing these into a single `pact_tier` would require every confrontation outcome to disambiguate "which tier" with a `target_axis` field, and the player-facing panel would say "Tier: 3" without telling them *which kind of three*. The split keeps the readout legible.

**Architect call: 2026-04-29 (magic-system-coyote-reach-v1 architect addendum).** `control_tier` registers in v1 (Coyote Reach uses `innate_v1.control_tier`). `discipline_tier` registers when a learned-using world ships — additive work, no retrofit on `pact_tier`-using plugins.

### Output catalog stability

Plugins MAY add output types (e.g., a hypothetical `harmony_balance` for elemental_harmony's spirit-system) but MUST do so by registering the type in their own spec and adding it here on ratification. The catalog is open at the bottom but stable at the top.

## ADR-021 Re-Interpretation

| ADR-021 track | What changes |
|---|---|
| **Milestone Leveling** | **Superseded.** Levels (where genres use them — caverns_and_claudes, elemental_harmony, mutant_wasteland) are output of `level_up`-bearing confrontation branches, not narrative-significance accumulation. The world-state agent's milestone judging role is repurposed to confrontation-stake assessment. |
| **Affinity Tiers** | **Kept; retriggered.** Affinity tier-up is `affinity_tier` output of confrontation branches. The keyword-trigger lists in current `progression.yaml` files become *confrontation triggers* (when this affinity is engaged in a confrontation, this affinity is eligible for tier-up). |
| **Item Evolution** | **Kept; anchored.** Item naming and item-power events are `item_bond` and `gear_mod` outputs of confrontations. The named gun bonds *in the standoff*, not via attention drift. |
| **Wealth Tiers** | **Kept; anchored.** Wealth tier shifts are `wealth_tier` outputs of confrontation branches (heists, poker games, inheritances, betrayals). |

A new ADR superseding ADR-021's Milestone Leveling track is warranted. **GM does not author ADRs** — handing this off to the Architect agent (Man in Black) when ready.

## Plugin Integration

Each magic-plugin spec gains a `confrontations:` block listing the confrontation types it participates in. See `magic-plugins/README.md` for the updated template.

A plugin's confrontations live with the plugin because:
- They define what The Bargain looks like for `bargained_for_v1`
- The branches and outputs are plugin-specific (a Bargain win unlocks deeper Bargainers Guild access; a Trial win unlocks deeper Divine apparatus access)
- Genre `confrontations.yaml` may reference plugin-defined confrontations OR define its own genre-shared confrontations (Combat is genre-level, not plugin-level)

## Per-Genre Confrontation Types (sketch)

These are the confrontation catalogs to populate. Each row needs a `confrontations.yaml` per genre.

| Genre | Confrontation types | Notes |
|---|---|---|
| **heavy_metal** | The Working, The Bargain, The Trial, The Duel, The Severance | The Severance is the ledger_lock-resolution confrontation |
| **caverns_and_claudes** | Combat, Trap, Negotiation, The Identification | The Identification is the unique "is this scroll/potion safe?" confrontation |
| **spaghetti_western** | The Quickdraw, The Standoff, The Chase, The Negotiation, The Reckoning | The Reckoning is the campaign-scale "everyone you've wronged shows up" |
| **victoria** | The Conversation, The Investigation, The Séance, The Confrontation, The Revelation | The Revelation is the "the secret is out" social earthquake |
| **mutant_wasteland** | Combat, The Surge, Scavenge, Negotiation, The Settlement | The Surge is the mutation-out-of-control confrontation |
| **space_opera** | The Dogfight, The Negotiation, The Heist, The Crew Crisis, The Stand | |
| **road_warrior** | The Chase, The Raid, The Wrench-Job, The Showdown, The Gas Run | The Gas Run is fuel-as-time-bomb confrontation |
| **elemental_harmony** | The Duel, The Spirit-Council, The Test, The Imbalance | The Imbalance is the harmony-collapse confrontation |
| **low_fantasy** | Combat, The Council, The Crossing, The Reckoning | |
| **neon_dystopia** | The Quickhack, The Run, The Negotiation, The Daemon | The Daemon is AI-encounter confrontation |
| **pulp_noir** | The Interrogation, The Stakeout, The Confrontation, The Reveal | |

Each one is a `confrontations.yaml` entry with: resource pool, valid moves, stakes, four-or-five branches each carrying mandatory + optional outputs.

## Player-Facing Reveal Format

When a confrontation resolves, the **visible ledger panel** displays an outcome callout:

```
THE BARGAIN — pyrrhic_win

⚡ Pact tier: 2 → 3
🩸 Scar: A new mark on the back of your left hand. Major. Visible.
⚖ Bargainers Guild: standing unchanged (they got what they wanted)
🔒 Obligation bar: locked at 0.85 until next Severance

[Optional, narrator-chosen this session]
🦂 Counter dispatched: a Severer has begun looking for you.
```

Format draws on Buttercup's UX brief — clear, beautiful, mechanical. The narrator's prose runs alongside (the WHAT in story; the WHAT in mechanics; both visible).

The callout is **always shown.** Decision #2 is binding. No genre-default suppression. (Per-player accessibility setting — *show callout / show inline / show both* — is fine; the underlying advancement events are always emitted.)

## Failure Advances — Worked Examples

A reminder of what Decision #4 actually delivers:

**spaghetti_western — The Quickdraw, branch: clear_loss**
- Mandatory: `scar` (the bullet wound that should have killed you), `reputation_tier` (you're now "the man who lost to him"), `bond_broken` if a faction watched
- Optional: `enemy_made`, `item_unbond` (your gun didn't fire when called)

**heavy_metal — The Trial, branch: clear_loss**
- Mandatory: `mechanism_revoked` (the divine apparatus has cast you out), `scar` (psychic), `identity_shift` (something in you has cooled)
- Optional: `counter_dispatched` (an inquisitor is now hunting you)

**victoria — The Conversation, branch: clear_loss**
- Mandatory: `secret_known` (something has been admitted that cannot be unsaid), `bond` (cracked or strengthened depending on what was said), `reputation_tier` (the social position is altered)
- Optional: `enemy_made` (the listener is now your antagonist)

**A character who lost three confrontations in a row is profoundly different from a character who won three.** Both have advanced. Both have changed sheets. Neither is "the same character with fewer hit points."

## Open Questions for Later

1. **Confrontation chains.** If The Bargain ends `pyrrhic_win` with a counter dispatched, is the next session's encounter with that counter a *new* confrontation or a *continuation*? Probably new — but the OTEL span chain links them.
2. **Multi-character confrontations in multiplayer.** When the party engages a single confrontation together, do all characters get outputs? Different outputs? Shared? Default: each character gets at least one mandatory output keyed to their participation.
3. **Confrontation refusal vs. confrontation avoided.** A character who refuses a confrontation gets the `refused` branch. A character who *never enters one* gets nothing. The narrator/GM is responsible for not allowing a session to drift entirely past confrontation. This is a SOUL #10 (Cut the Dull Bits) enforcement issue.
4. **Output stacking.** If a confrontation grants `pact_tier +1` and the character is at the genre-cap, does it overflow? Probably converts to `mechanism_unlocked` on a per-plugin basis.
5. **Item-side advancement.** Items as NPCs get their own outputs — the named gun bonds *to* the wielder, but does the gun's OCEAN drift? Probably yes (a vehicle that's been in 50 chases gets crankier). Defer.

## Next Concrete Moves

- [ ] Architect formalizes the supersession of ADR-021's Milestone Leveling track in a new ADR (ADR-091 or whichever is next)
- [ ] GM drafts `bargained_for_v1` plugin spec with full `confrontations:` block (The Bargain) — concrete worked example
- [ ] Architect spike: WebSocket message shape for `confrontation.outcome` events; how the panel renders outputs
- [ ] UX (Buttercup) draft: outcome callout panel mockup
- [ ] Dev (Inigo) implement: confrontation outcome event emission, panel rendering, character state mutation hooks
- [ ] Each genre gets a `confrontations.yaml` (eight to twelve entries each — substantial content authoring work)
