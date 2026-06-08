# AC5 OTEL Combat & Magic Verification — Design

**Date:** 2026-06-05
**Story:** 87-4 (heavy_metal WWN final integration gate), AC5
**Author:** Architect (brainstorming session)
**Input:** `docs/superpowers/notes/2026-06-05-ac5-otel-combat-engagement-brainstorm-handoff.md`
**Decision:** **D1** — integration tests are AC5's mechanical proof for 87-4; all *live*
narrator-in-the-loop proof (fixture + free-play + caster) deferred to **epic 90**.

---

## Problem

AC5 of story 87-4 wanted a *live* OTEL playtest proving, on both heavy_metal WWN
worlds, that combat fires `wwn.*` spans + ablates HP and a caster fires
`wwn.spell.cast` — with the lie-detector quiet. The two authored free-play
scenarios drove a character to "fight" and "cast"; the narrator described both;
**the mechanical engines never fired.** The lie-detector
(`confrontation.intent_mismatch`, `intent_router.dispatch.gated`,
`movement.mismatch`) correctly caught the mechanically-unbacked narration.

## Root cause (corrected after seating-path investigation)

Two independent reasons the live runs produced no `wwn.*`/`wwn.spell.cast`:

1. **No combat confrontation was ever triggered.** WWN combat seats its Other
   from the confrontation definition's `opponent_default_stats` in `rules.yaml`
   (heavy_metal: `hp 10 / armor_class 12`) at trigger time, via
   `instantiate_encounter_from_trigger`. The Other's *combat numbers are not the
   blocker* — they exist. What was missing was a **triggered confrontation**: the
   narrator kept the PC in a social opening (Upre town hall + a neutral courier)
   and never surfaced/escalated a hostile target, so no combat trigger fired
   (`confrontation.intent_mismatch`). This is *correct* engine behavior
   (ADR-116/139 + "never force a bite").

2. **The caster could not cast.** `cast_spell` is a confrontation beat and the
   WWN cast path requires `CreatureCore.spellcasting` (`SpellcastingState`). With
   no seated confrontation *and* a social-opening PC, the cast fell through to the
   generic `magic_working` dispatch, which gated.

A separate magic-side defect surfaced: **long_foundry ships a `magic.yaml`
(ADR-126) but the runtime `snapshot.magic_state` is `None`** — the world magic
plugin is never instantiated at session-bind.

The engine is honest throughout. The Monster Manual `encounters` pool *is* empty
for both worlds (evropi: 49 NPCs / 0 encounters; long_foundry: 39 / 0) because
**encountergen fails for ruleset-module packs** (`genre heavy_metal has no
allowed_classes in rules.yaml`). That gap matters for *free-play reachability*
(it supplies named, located, varied hostiles a fight-seeker can run into) — but
it is **not** what made seating impossible, because `opponent_default_stats`
already statifies a triggered Other. Correcting an earlier overstatement: the
manual is *a* source of reachable hostile presence, not *the only* source of a
mechanically-capable Other.

## SOUL resolution

The narrator's refusal to conjure a fight from a peaceful opening is **correct**
("Living World", "Untaken bait / never force a bite", ADR-116). The durable fix
is not to force combat but to ensure a **basic, genre-appropriate hostile is
always reachable** when a player genuinely goes looking — *always have bait,
never force a bite.* WWN's own basic bestiary is the appropriate scope for that
floor; no deep monster port is needed.

## Why a content-only fixture cannot prove AC5 in epic-87 scope

Investigated the scene-harness hydrator (`game/scene_harness.py`):

- **No per-character spellcasting seeding.** `_hydrate_character` never sets
  `core.spellcasting`; the fixture `magic_state:` block is the ADR-126 *world*
  plugin, a different object. So `wwn.spell.cast` **cannot** be proven by a
  content-only fixture — it needs hydrator (server) changes.
- **Fixture `encounter:` builds a dial-engine `StructuredEncounter`**
  (player_metric/opponent_metric), which is wrong for WWN `hp_depletion` combat.
  A WWN combat fixture would instead place a hostile NPC and rely on a scripted
  strike to trigger production seating — **narrator-mediated, not deterministic.**
- **Fixture NPCs carry no `hp`/`armor_class`** — but that is moot, since seating
  pulls the Other's stats from `opponent_default_stats`.

Therefore the AC5a-via-fixture idea (content-only proof of *both* combat and
magic) is **not achievable** without server work, which breaks epic 87's
zero-engine-changes premise.

## Decision — D1

For **story 87-4**, AC5 is satisfied by the **existing integration tests** and
the *live* proof is deferred:

- `tests/integration/test_wwn_heavy_metal_combat.py` (3 passing, verified 2026-06-05) drives the
  **production** seating seam (`instantiate_encounter_from_trigger`) and dice
  seam (`dispatch_dice_throw`) on the real `ruleset: wwn` pack and asserts:
  ruleset bound = wwn; Other seats with `hp`/`armor_class` from
  `opponent_default_stats`; a strike ablates the Other's HP through the HP
  channel; the `state_patch.hp` span fires (the GM-panel lie-detector); the
  no-toothless-Other and opponent-reprisal invariants hold; `cast_spell` routes.
- AC5 acceptance text re-scopes to: *"WWN combat + magic mechanics are proven by
  `test_wwn_heavy_metal_combat.py`; the live narrator-in-the-loop OTEL proof
  (deterministic fixture + free-play discovery + caster) is deferred to epic
  90."* The 87-4 honesty bar — "no mechanically-unbacked combat/magic ships
  silently" — is *met*: the lie-detector fired correctly in the live runs, which
  is the OTEL Observability Principle working as designed.

This closes 87-4 without server code and routes the real engineering to epic 90.

## Deferred to epic 90

**Epic 90 — Ruleset-Module Worlds: Live Combat & Magic Verification Enablement**
(server/content; out of epic 87's zero-engine-changes premise):

- **90-1** Encountergen ruleset-awareness — emit WWN/CWN/SWN-aligned enemy stat
  blocks via the RulesetModule seam so `pregen.seed_manual` populates the manual
  with reachable, located, named hostiles (the "basic bestiary floor"). Reframed:
  this supplies *reachable hostile presence/variety* for free play — combat
  numbers still come from `opponent_default_stats` at trigger time.
- **90-2** WWN/ADR-126 magic plugin not instantiated at session-bind
  (`magic_state is None` for long_foundry despite shipping `magic.yaml`).
- **90-3** AC5b live free-play OTEL proof across heavy_metal evropi +
  long_foundry + **barsoom** (depends on 90-1, 90-2).
- **90-4** Scene-harness hydrator: seed per-character WWN `spellcasting` and a
  WWN-correct `hp_depletion` encounter so a *deterministic* fixture can prove
  `wwn.*` combat + `wwn.spell.cast` live (the deterministic counterpart to the
  free-play proof in 90-3).

**Beneficiaries (all RulesetModule worlds):** heavy_metal (evropi, long_foundry,
and the in-progress **Barsoom** world — epic 89, also WWN), elemental_harmony
(wwn), neon_dystopia (cwn), space_opera (swn). Barsoom (epic 89) **depends on**
epic 90 for reachable statted hostiles and its own live combat proof.

**Process note:** a non-empty Monster Manual `encounters` pool should join the
world asset-gate checklist, so "0 encounters" is caught at authoring time.

## Constraints respected

- **Zero engine changes** (epic 87): D1 adds no server code — it re-scopes an AC
  and leans on existing passing integration tests. All engine/tooling work is in
  epic 90, named as such.
- **The Zork Problem:** nothing here reduces the narrator to keyword matching.
  Epic-90 work makes hostiles *reachable*, never *forced*.
- **No silent fallbacks / no source-grep wiring tests:** the proof is OTEL spans
  asserted by integration tests.
