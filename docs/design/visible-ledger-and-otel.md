# Visible Ledger + OTEL Lie-Detector

**Status:** Committed feature spec, 2026-04-27
**Audience:** Architect, Dev, UX, GM
**Source:** Party-mode brainstorm — Buttercup (UX) + Miracle Max (DevOps) + The Grandfather (the promise) → Keith confirmed 100%
**Companion docs:** `docs/design/magic-taxonomy.md`, `docs/design/magic-plugins/`

## The Promise

The narrator must not get to invent magical consequences. When the narrator describes a magical effect, the system must:

1. **Show the player what was billed**, in real time, on a visible ledger.
2. **Verify, via OTEL span, that the narration matches what the world actually permits.**

If either of these fails, the magic system is not honest, and the player is being lied to. This is the load-bearing principle.

> *"Claude is excellent at 'winging it' — writing convincing narration with zero mechanical backing. The only way to catch this is OTEL logging on every subsystem decision."* — `CLAUDE.md`

This spec wires the OTEL principle directly into the magic layer, where winging matters most.

## Two Audiences, Two Panels

### Player-facing: The Ledger

A small UI panel in the player view. When a working is narrated, bars rise visibly.

- **Bars displayed:** the cost types active for the current world (driven by world's `magic.yaml`'s `required_costs`). For heavy_metal: Soul/Debt, Vitality, Sanity, Components, Time, Obligation. For mutant_wasteland: Backlash, Karma, Vitality. For spaghetti_western: Karma alone (a single rising bar of reputation/burden).
- **Animation:** bars rise *during* the narration of the working, not after. Player sees the bill accrue in the same beat as the effect.
- **Threshold visualization:** when a bar approaches a fill-state, a dashed line appears showing where "consequence triggers." Players can see the bill coming.
- **Per-character vs. world-level:** some bars are character-bound (Soul/Debt is yours), some are world-bound (Obligation accrues to the village/guild). The panel labels them clearly.
- **Mobile/Alex-paced:** bars animate gently. No flashing. No anxiety pressure. The accrual is observable, not panic-inducing.

### GM-facing: The Span Feed

A panel in the GM view (Keith's DM screen, Sebastien's mechanic-curiosity feature) that mirrors the ledger AND adds:

- **OTEL span trace** of every magical claim the narrator makes
- **Plugin/Source tagging** — which magic-plugin the working ran through
- **Mechanism log** — which delivery mechanism was engaged (faction notified, place tapped, condition met, time-window used, etc.) and the named target within that mechanism
- **World-rule cross-check** — every claim verified against the active world's `magic.yaml`
- **Red-flag system** — three severity levels (see below)

## OTEL Span Shape

Every magical narration emits exactly one span:

```
span_name: magic.working
attributes:
  working_id: <uuid>
  plugin: bargained_for_v1
  source: bargained_for
  declared_effect: "<short description>"
  domains: [psychic, divinatory]
  modes: [invoked]
  debited_costs:
    soul_debt: 0.15
    karma: 0.05
  debited_scales:           # plugin-specific (heavy_metal)
    individual: true
    communal: false
    covenant: false
    divine: true
    stratigraphic: false
  mechanism_engaged: faction      # one of: faction | place | time | condition |
                                   #         native | discovery | relational | cosmic
  mechanism_target:                 # what specifically was tapped through that mechanism
    faction_id: bargainers_guild_eastern_chapter
  reliability_roll: { type: skill_check, result: success }
  world_knowledge_at_event: acknowledged
  visibility_at_event: regulated
events:
  - name: ledger.bar.rise
    attributes: { bar: soul_debt, delta: 0.15 }
  - name: ledger.bar.rise
    attributes: { bar: karma, delta: 0.05 }
  - name: mechanism.engaged
    attributes: { mechanism: faction, target: bargainers_guild_eastern_chapter, severity: routine }
```

**`mechanism_target` shape varies by mechanism type:**

| Mechanism | `mechanism_target` payload |
|---|---|
| `faction` | `{ faction_id, chapter, severity }` |
| `place` | `{ location_id, region, claimed_by? }` |
| `time` | `{ window_id, occurs_next_at, missed_until_next? }` |
| `condition` | `{ condition_id, met: true/false, met_via }` |
| `native` | `{ trait_id }` (no external target — self-source) |
| `discovery` | `{ item_id, found_at, formerly_held_by? }` |
| `relational` | `{ entity_id, relationship_type, bond_status }` |
| `cosmic` | `{ axis }` (the world-truth axis tapped) |

The mechanism field is what makes the OTEL panel useful for plot tracking, not just rule-checking. When the GM panel shows a faction was engaged, Keith can see *which faction* and decide what they do about it. When a place was tapped, the panel shows the location and the panel can flag if other claimants are nearby.

**The narrator agent is responsible for emitting this span** when it describes a magical effect. The agent is constrained by prompt to refuse magical narration that cannot be backed by a span. (Implementation: prompt instruction + post-narration audit; both fire.)

## Red-Flag Severity

The GM panel watches the span stream and applies these checks against the active world's `magic.yaml`:

### YELLOW — Soft warning

- Narration *implies* a magical effect (keyword match) but no `magic.working` span fired
- Narrator emits a span but `declared_effect` is vague (e.g., "magic happens")
- Cost debited zero across all bars (a "free" working — possible but suspicious)

YELLOW does not stop the session; it surfaces in the panel for review.

### RED — Likely lie

- Narration claims a Source not in the world's `allowed_sources`
- Narration uses a Domain not in `manifestation.domains`
- Narration uses a Mode not in `manifestation.modes`
- Reliability roll is omitted on a plugin that requires it
- Mechanism log missing — narrator claims magic without naming HOW the resource was reached (no faction, no place, no condition, no native trait, etc.)

RED interrupts the GM with an audible/visible alert. Does not block player view; lets Keith decide whether to retcon.

### DEEP RED — Hard-limit violation

- Narration produces an effect listed in `hard_limits.forbidden`
- e.g., narrator describes a resurrection in a `resurrection: forbidden` world

DEEP RED stops the working. The narrator is forced to retcon. This is the absolute fence — if the narrator improvs a hard_limit-banned effect, the system blocks it before the player sees it.

## Plugin-Driven Bar Configuration

Each magic-plugin (`bargained_for_v1`, `divine_v1`, etc.) declares the bars it contributes:

```yaml
ledger_bars:
  - id: soul_debt
    label: "Soul / Debt"
    color: ember
    scope: character          # vs. world / faction / location
    threshold: 1.0            # at what fill does consequence trigger
    consequence_on_fill: "patron collects"
    decay_per_session: 0.0    # soul_debt does not decay
```

A world's active set of bars is the union of all bars declared by its active plugins. If heavy_metal runs three plugins (bargained, divine, learned-ritual), the player ledger may show 6–8 bars total. Some are shared (Karma is universal); some are plugin-specific.

## Cost Pre-payment / Forward Debt *(stretch goal)*

Captured in party mode (idea #10): a player can pre-pay sanity/karma to *guarantee* a future working fires. The ledger supports this by allowing pre-fill — bars rise *before* the working, locking the bill in. The OTEL span fires on the eventual cast and reconciles against the pre-payment.

Defer until base spec lands.

## Implementation Notes (sketch)

- **Span emission:** add `magic.working` span to the narrator subprocess via OTEL passthrough (ADR-058). Narrator agent prompt updated to include "you must emit `magic.working` for any magical narration."
- **Span watcher:** extend the existing `/ws/watcher` dashboard (`just otel`) with magic-specific filters. The watcher feeds the GM panel.
- **Ledger UI:** new component in `sidequest-ui` — `<MagicLedger />`. Subscribes to magic events on the WebSocket. Player and GM variants share the rendering core; GM variant adds the span trace pane.
- **World loader:** when a session loads, build a *flag-rule lookup table* from the world's `magic.yaml` so the panel can check claims in O(1).
- **Retcon protocol:** when DEEP RED fires, the system intercepts the narration before delivery. This needs careful UX work — Keith doesn't want the game to stutter visibly.

## Tabletop-First Justification

A human DM can see when they've improvised a consequence. A human DM gets to retcon. This panel gives the AI narrator the same self-correction loop a human DM has — but exposed to the GM (Keith) so a *career GM can fact-check the AI narrator in real time*. This is the single most playgroup-relevant feature of the magic system, because Keith is the only person at the table who can tell when the narrator is bullshitting, and he should not have to do so by feel alone.

It also serves Sebastien's mechanics-first interest: he can *see how the magic system works* through the GM panel without breaking immersion for narrative-first players (Alex, James). The panel is genre-truth made legible.

## Confrontation Outcomes Are Advancement Events *(added 2026-04-28)*

A confrontation that resolves emits a second span class — `confrontation.outcome` — alongside any `magic.working` spans the confrontation produced. The OTEL lie-detector treats *advancement* improvisation the same way it treats magical improvisation:

- If the narrator says "you have gained the Severer's respect" and no `confrontation.outcome` span fired with `bond` in its outputs, **YELLOW flag** — advancement was claimed without a confrontation.
- If a `confrontation.outcome` span emits `mandatory_outputs: []`, **RED flag** — every confrontation must produce at least one output (Decision #1 in `confrontation-advancement.md`).
- If the narrator's prose contradicts the span (claims a `bond` formed but the span shows `clear_loss` with `bond_broken`), **RED flag**.

The visible ledger panel renders the confrontation outcome callout when this span fires, showing the player exactly what changed (Decision #2: player-facing reveal is mandatory). See `confrontation-advancement.md` for the full output catalog and reveal format.

## Open Questions

1. **Player-facing bars on by default?** Or a setting? Some players (Alex, narrative-first) may prefer bars hidden during normal play and visible only when a working fires. Others (Keith-as-player) want them always-on. *(Confrontation outcome callouts are NOT subject to this — Decision #2 makes them always-shown.)*
2. **Animation language.** Buttercup says "rising bars," but heavy_metal-mood would call for ember-flicker, victoria-mood for ink-bleeding-on-paper, neon_dystopia for glitching readouts. Per-genre theming of the ledger.
3. **Mechanism-engagement consequences.** Faction notification → NPC dispatched. Place tapped → other claimants alerted. Time window used → can't be tapped again until next occurrence. Each mechanism has its own consequence-cadence; the plugin declares default, world tunes it.
4. **Multi-plugin overlap.** If a working could be claimed by two plugins, who claims it? (e.g., a cleric using a relic — Divine plugin or Item-Legacy plugin?) The narrator must declare; the GM may override.

## Next Concrete Moves

- [ ] Architect spike: WebSocket message shape for ledger events; OTEL span schema vs. narrator-agent prompt constraints
- [ ] UX Designer (Buttercup) draft: ledger panel mocks, player view + GM view, three genre themings
- [ ] DevOps (Miracle Max) wire-up: extend `/ws/watcher` with magic-domain filters; red-flag system
- [ ] Dev (Inigo) implement: `<MagicLedger />` component; the OTEL hook in narrator subprocess
- [ ] GM (me) draft: first plugin spec (`bargained_for_v1`) including its `ledger_bars` and `otel_span` shape — concrete to work against
