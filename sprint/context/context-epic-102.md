# Epic 102: Complete the Without Number Family (SWN/WWN/CWN/AWN) — Retire Deferred Live-Dispatch Wiring

## Overview

Keith directive (2026-06-10): the deferred "Without Number" (WN) module surfaces stop being deferred. The WN combat/magic crunch is **built** — `SwnRulesetModule`, `WwnRulesetModule`, `CwnRulesetModule`, and `AwnRulesetModule` all exist behind the ADR-117 ruleset seam, and fixtures pass on the apply_beat/downed-seam paths — but **live narrator-in-the-loop play hits unwired seams**. The 90-3 AC5b free-play playtest (heavy_metal/long_foundry, PC Vesska, slug `2026-06-10-long_foundry`) measured exactly which seams: a dying PC emits no WN lethality span, an in-combat "Work a Spell" beat resolves as a generic INT throw, and a typed free-play cast never reaches the intent router's `magic_working` classification. This epic closes those three measured gaps (102-1..3), then retires the remaining deferred plan phases — the WN turn model (102-4), narrator tool contract (102-5), psionics (102-6) — proves AWN live for mutant_wasteland (102-7), and reconciles doc drift (102-8).

**Priority:** P2 (stories 102-1..3 are P1 — they block 90-3 AC5b proof)
**Repos:** server, content, ui
**Stories:** 8 (49 points)

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| **SWN module design** (`docs/superpowers/specs/completed/2026-05-26-swn-module-design.md`) | §3 interface reshape ("module owns the whole turn"), §6–7 turn model + sealed action menu (→102-4), §8 narrator tool contract (→102-5), §6/P7 psionics (→102-6), §11 sequencing, §12 risks (tool-contract isolation note) |
| **AWN / mutant_wasteland design** (`docs/superpowers/specs/completed/2026-06-05-ashes-without-number-mutant-wasteland-design.md`) | §6 Plan 1 (module + binding + ablative HP — **already landed**), §6.5 OTEL wiring test mandate, §8 epic decomposition, §11 architect addendum (binding styles, change-list) (→102-7) |
| **SWN crunch / ablative-HP design** (`docs/superpowers/specs/completed/2026-05-25-swn-crunch-ablative-hp-design.md`) | Ablative-HP substrate the downed seam rides on (→102-1) |
| **SWN P4 initiative spine** (`docs/superpowers/specs/completed/2026-05-27-swn-p4-initiative-spine-design.md`) | Initiative-ordered resolution groundwork (→102-4) |
| **ADR-114** (`docs/adr/114-*.md`) | Ablative HP substrate; Part 2 death-clock remains future |
| **ADR-116 / ADR-139** | Confrontation participant invariants; win-condition liveness, seated-actor HP durability, dispatch applicability gate |
| **ADR-117** (`docs/adr/117-pluggable-ruleset-module-system.md`) | The RulesetModule seam every story in this epic extends |

## Background

### Why this epic exists

Sebastien and Jade — the group's two mechanics-first players — ran a 140+ turn session on narrative strength alone while the confrontation engine was broken, and specifically missed the crunch. The WN family is the answer: faithful Sine-Nomine-style resolution (d20 attack vs AC, 2d6 skills, four saves, Shock/Trauma/Mortal-Injury lethality, Effort-based casting) behind the pluggable ruleset seam, per genre: SWN→space_opera, WWN→heavy_metal/elemental_harmony/barsoom, CWN→neon_dystopia/road_warrior, AWN→mutant_wasteland.

The modules were built across sprints 2522–2624 with a deliberate "fixtures first, live wiring deferred" sequencing. The bill for that deferral is now due: the 90-3 AC5b acceptance criterion ("prove WN crunch engages in live free play, watched on the GM panel") cannot pass, because the live paths bypass the module surfaces the fixtures exercise.

### The three measured AC5b gaps (FIXER investigation, oq-2, 2026-06-10)

1. **PC-death runs no WN downed seam.** `run_cwn_wwn_downed_seam` fires `{ruleset}.mortal_injury`/`.shock` only when the **player drops an opponent** (strike path, `dispatch/dice.py:760`). When the **player is dropped** by opponent reprisal (`_resolve_opponent_reprisal`, `dice.py:1057` → `check_hp_depletion`), `server/post_resolution_lethality.py` applies the generic genre verdict (`verdict=dead`) with **zero `wwn.*` spans** — its own docstring documents the asymmetry. A dying PC emits `hp_depletion.resolved` + `post_resolution_lethality.applied` and nothing module-scoped, so the GM panel cannot show WN lethality engaged on the combat half of AC5b.
2. **In-combat cast via the dice path skips the WN cast spine.** `DiceThrowPayload` (`protocol/dice.py:160`) carries `beat_id` but **no `spell_id`**. `_resolve_wwn_cast_for_beat` (`server/narration_apply.py:261`, called at `:5453`) only runs on the narrator-driven apply_beat path, where `spell_id` arrives via the BeatSelection sidecar. Clicking "Work a Spell (INT)" fires `dispatch_dice_throw` → generic INT throw: no `wwn.spell.cast`, `casts_remaining` stays 2/2, no Effort/System-Strain spend.
3. **Explicit free-play cast is never classified `magic_working`.** The intent router defines the `magic_working` category (`agents/intent_router.py:145`) but a typed, named cast ("I cast foundation_of_flame") is not routed to `resolve_spellcast` — the narrator improvises the working with zero mechanical backing. This is precisely the Illusionism the OTEL lie-detector doctrine exists to catch.

**Explicit non-goal:** the `magic_init` AND-gate (`magic_init.py:204`) is a separate latent bug in the **retired plugin-framework magic** path. WWN magic uses `core.spellcasting`/`core.effort`, not `magic_state`. long_foundry's 78KB `magic.yaml` is orphaned draft content in an incompatible schema. Not on the AC5b path; not in this epic.

### The deferred plan phases being retired

From the SWN module design's sequencing (§11): **P4** turn model (sealed-letter commitment, 1d8+DEX initiative-ordered resolution, `dead_premise` narrator call) and **P5** narrator tool contract (§8) were explicitly deferred; **P7** psionics likewise. AWN Plan 1 (module + `ruleset: awn` binding + ablative HP) **already landed** — `AwnRulesetModule` subclasses `CwnRulesetModule` with zero overrides and `mutant_wasteland/rules.yaml:14` binds it — but live proof (the §6.5 OTEL wiring-test mandate) has not been run. Meanwhile `wwn.py`/`swn.py`/`cwn.py` and `DRIFT.md` still carry stale "not wired to dispatch (Plan 3)"/"deferred" markers for surfaces that ARE now wired (e.g. `apply_killing_blow` at `dice.py:644`/`725`).

## Technical Architecture

### The seam map

```
player free-text ──► intent_router ──► magic_working? ──► resolve_spellcast ──► wwn.spell.cast   (102-3)
                                       (today: never)

UI beat tile ──► DiceThrowPayload{beat_id, +spell_id} ──► dispatch_dice_throw
                                                            ├─ WN cast spine (102-2; today generic INT throw)
                                                            ├─ player strike ──► run_cwn_wwn_downed_seam ✅ (dice.py:760)
                                                            └─ _resolve_opponent_reprisal (dice.py:1057)
                                                                 └─► check_hp_depletion ──► post_resolution_lethality
                                                                       └─► WN downed seam for the PC (102-1; today generic verdict)

narrator apply_beat ──► _resolve_wwn_cast_for_beat ✅ (narration_apply.py:261/5453)
```

### Key files

| File | Role |
|------|------|
| `sidequest-server/sidequest/server/dispatch/dice.py` | Dice dispatch; strike-path downed seam (`:760`), opponent reprisal (`:1057`), `apply_killing_blow` (`:644`, `:725`) |
| `sidequest-server/sidequest/server/dispatch/downed_seam.py` | `run_cwn_wwn_downed_seam` — the WN lethality stack (Shock/Mortal Injury spans) |
| `sidequest-server/sidequest/server/post_resolution_lethality.py` | Genre `lethality_policy.verdicts_on_zero_hp.pc` seam for the downed **PC** — 102-1 extends this to also run the WN module's lethality surface |
| `sidequest-server/sidequest/server/narration_apply.py` | `_resolve_wwn_cast_for_beat` (`:261`, call `:5453`) — the WN cast spine 102-2 must reach from the dice path |
| `sidequest-server/sidequest/agents/intent_router.py` | `magic_working` category (`:145`) — 102-3 routing target |
| `sidequest-server/sidequest/protocol/dice.py` | `DiceThrowPayload` (`:160`) — gains optional `spell_id` (102-2) |
| `sidequest-server/sidequest/game/ruleset/{base,registry,swn,wwn,cwn,awn,native,resolution}.py` | ADR-117 module family; AWN subclasses CWN with an honest `slug = "awn"` |
| `sidequest-ui/src/components/...ConfrontationOverlay` | Spell-selection UI for the "Work a Spell" beat (102-2) |
| `sidequest-content/genre_packs/mutant_wasteland/rules.yaml` | `ruleset: awn` binding (already present) + any 102-7 content |
| `docs/adr/DRIFT.md`, `sidequest/game/ruleset/*.py` headers | 102-8 doc-drift reconciliation |

### Architectural invariants

- **One seam, no forks.** Everything module-scoped flows through the ADR-117 `RulesetModule` interface. No `if genre == "heavy_metal"` branches in dispatch; capability binding is `isinstance` against module classes (AWN is covered for free as a `CwnRulesetModule` subclass).
- **OTEL or it didn't happen.** Every story lands `{ruleset}.{surface}` spans assertable in tests and visible on the GM panel. The AC5b proof is span-shaped: `wwn.mortal_injury`, `wwn.spell.cast`, `dispatch_engagement.magic_working.*`, `{ruleset}.effort.commit/reclaim`, `system_strain.delta`.
- **The slug is honest.** Spans, saves, and GM panel show the binding module's slug (`awn`, not `cwn`), per the AWN design's "lie the lie-detector can't catch" rationale.
- **Zork Problem guardrail (102-2).** Spell selection in the overlay is an alternate submit verb for typed text (the `player_action` carry pattern already in `DiceThrowPayload`), never a replacement for natural language casting — which 102-3 handles.
- **Reuse-first.** Each gap is wiring an existing, tested surface to a path that bypasses it: 102-1 calls the existing downed seam from `post_resolution_lethality`; 102-2 routes the dice path into the existing `_resolve_wwn_cast_for_beat` spine; 102-3 routes the existing intent-router category to the existing `resolve_spellcast`. Build nothing that exists.

## Cross-Epic Dependencies

**Depends on:**
- Epic 90 (ruleset-world combat & magic) — built the WN modules, hydration, and fixtures this epic wires live; 90-7 landed WWN effort hydration + `wwn.magic_hydrated`
- ADR-114 ablative-HP substrate; ADR-117 ruleset seam; ADR-139 confrontation integrity invariants
- AWN Plan 1 (already merged: `AwnRulesetModule` + `ruleset: awn` binding)

**Depended on by:**
- **90-3 AC5b** — the live free-play proof is BLOCKED on 102-1/102-2/102-3
- 90-8 (lie-detector spans → typed GM-panel feed) — consumes the spans these stories emit
- Future AWN plans 2–7 (mutations, radiation, stress, hexcrawl) — assume 102-7's live-proven foundation
