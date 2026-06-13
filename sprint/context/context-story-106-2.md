---
parent: 106
---

# Story 106-2 Context

## Title
WWN reprisal model — defensive beats must mitigate the per-beat opponent reprisal
(ramp lever #2). The unconditional ADR-033 counter-attack stapled to every player
beat ignores Brace/Break Contact and is not WWN-faithful. **DESIGN-BEARING:**
Architect ruling needed (initiative round where the player can full-defend, vs
keeping the beat model but making defensive beats reduce to-hit/damage/grant a save).

## Metadata
- **Story ID:** 106-2
- **Type:** bug
- **Points:** 5
- **Priority:** p1
- **Workflow:** tdd
- **Repo:** server
- **Epic:** 106 — WWN combat hardening for beneath_sunden (fair ramp, ruleset-bleed remediation, narration truth)

## Business Context

This is **easy-ramp survivability lever #2** (lever #1 is 106-1: equip starting
armor / derive AC from the WWN SRD). The two levers share one goal: make L1
`caverns_and_claudes/beneath_sunden` (WWN ruleset, ADR-117) a **fair, WWN-faithful**
fight that a first-level Warrior can survive with good play — 1-of-5 PCs survived the
2026-06-13 playtest.

**The playtest evidence (authoritative, sq-playtest-pingpong.md:56-68):** in
`beneath_sunden` combat, every player beat — `strike`, `committed_blow`, **and even a
defensive `brace`** — is immediately followed in OTEL by an
`ENCOUNTER_OPPONENT_ATTACK` + `ENCOUNTER_OPPONENT_DAMAGE`: an automatic, unconditional
opponent counter-attack stapled to the player's action. Zeppo's **Brace** (a *defensive*
beat) still ate a full `d20=15+2=17 hit, 1d8=5` reprisal that killed him. **The defense
mitigated nothing — Brace was mechanically identical to Strike in damage taken.** There
is no survival play.

**Why this is a WWN bleed, not just a balance dial.** Keith's operator question was
*"the reprisal mechanic, is that a leftover from native rules?"* The answer is yes in the
way that matters. The per-beat action→reprisal exchange is the **native SideQuest
confrontation model** (ADR-033 beat engine / ADR-116 single-opponent-seater), **not** WWN
SRD combat. WWN is **initiative-based rounds**: each side acts on its own initiative, the
enemy attacking is normal but it is *the enemy's own turn* (it can miss, and a PC may
spend their action **defending or disengaging to avoid being hit entirely**). The current
behavior gives the enemy a **free attack every time the player acts**, with no initiative
and no way for a defensive choice to prevent it — the same class of native-mechanic-leaking-
into-a-WWN-world that 106-3 catalogs (native edge/tag, native per-tick XP). The standing
GM ruling (`.pennyfarthing/sidecars/gm-decisions.md`, 2026-06-13) is that **WWN-bound
mechanical values come from the WWN SRD** — so whatever this story builds, its numbers
(save targets, to-hit penalties, AC swings) come from the SRD, not invented.

**Who this serves:** Sebastien and Jade (mechanics-first) want crunch that *rewards a
correct defensive choice* and is **legible in the player UI** (they should see Brace lower
the enemy's to-hit, not just hope it did something). Keith-as-player needs a fight that
behaves like a WWN round, not a beat-treadmill that punishes defending exactly as hard as
attacking.

## Technical Guardrails

### What the code actually does today (cite-grounded)

There are **two** opponent-attack code paths, and the bug touches both:

1. **Legacy per-beat reprisal** —
   `sidequest-server/sidequest/server/dispatch/dice.py:730-768`. After
   `_apply_committed_player_beat` resolves the player's beat, the seated opponent attacks
   back unconditionally (`module_has_opponent_turn` capability check, dice.py:743-745),
   gated only on `cdef.win_condition == "hp_depletion"` and `not encounter_resolved`. It
   does **not** look at which beat the player committed.

2. **WN sealed initiative round** — `sidequest-server/sidequest/server/dispatch/wn_round.py`.
   This path already does the WWN-correct thing structurally: it walks the persisted
   `encounter.initiative` order and the opponent attacks **at its own slot**, not as a rider
   (`run_wn_round`, wn_round.py:189-297; opponent slot at 273-297). The module docstring
   (wn_round.py:1-18) explicitly frames this as "instead of as an immediate reprisal rider
   on a player's dispatch."

**The dispatch gate that selects between them:** `dice.py:633-650`.
`wn_sealed_round = not opposed_pending and isinstance(ruleset, SwnRulesetModule) and
cdef.win_condition == "hp_depletion" and bool(encounter.initiative)`. **`WwnRulesetModule`
subclasses `SwnRulesetModule`** (`sidequest/game/ruleset/wwn.py:51` —
`class WwnRulesetModule(SwnRulesetModule)`), so a WWN fight *does* qualify — **but only if
`encounter.initiative` is populated.** When it is empty (pre-P4 saves, direct-construction
encounters) the code logs `dice.wn_round_skipped reason=no_persisted_initiative`
(dice.py:645-650) and falls through to the legacy per-beat reprisal. **Dev must first
determine which path the beneath_sunden playtest actually took** (grep the run's OTEL /
server log for `wn_round_skipped` vs `{slug}.round.resolved`). The fix differs in emphasis
per path, but the *root defect below is common to both*.

**The root defect (common to both paths):** the reprisal resolver
`_resolve_opponent_reprisal` (`dice.py:1566-1900`) is **completely blind to the player's
chosen beat.** It does not receive `commit.beat_id`; it reads the player's AC flat
(`target_ac = int(player_core.armor_class)`, dice.py:1636) and rolls
`ruleset.resolve_opponent_attack(...)` (dice.py:1639-1646) with no defensive modifier.
The sealed-round walk calls this *same* blind resolver (wn_round.py:284-296). So even on the
WWN-faithful initiative path, **Brace today changes nothing about the incoming attack.**

**Existing infrastructure to reuse (do not reinvent — CLAUDE.md):**
- `brace` is a first-class `BeatKind` (`beat_kinds.py:37`, `BeatKind.brace`) with per-tier
  deltas (`beat_kinds.py:231-237`) and the `Counter Stance` fleeting tag on CritSuccess.
- The HP channel **already has a mitigation primitive**: `apply_beat_hp_channel(...,
  target_mitigation: int, ...)` (`beat_kinds.py:357-373`) subtracts flat mitigation before
  applying strike damage, and `BeatDef` documents `brace: mitigates incoming HP damage this
  round` (`genre/models/rules.py:53`). The docstring at `beat_kinds.py:911-913` says brace
  "supplies mitigation to the **NEXT strike** (the calling layer holds the pending brace
  value)" — **but no calling layer currently holds it for the opponent reprisal.** That is
  precisely the wiring gap Option B closes.
- `RulesetModule.resolve_opponent_attack` / `SwnRulesetModule.resolve_opponent_attack`
  (`ruleset/base.py:124`, `ruleset/swn.py:126-149`) is the to-hit primitive; it already
  takes `target_ac` and returns hit/total. A defensive to-hit penalty or AC bump is a
  natural parameter extension here — under the **WWN RulesetModule seam (ADR-117)**, so the
  behavior is gated to WWN and native dispatch stays untouched (the wn_round module already
  binds capability by `isinstance`, not by genre string).

---

### THE DESIGN DECISION — Keith owes the ruling; Dev is BLOCKED until it lands

An enemy that hits back is **not** the problem. *Unconditional reprisal that ignores
defensive beats* is. Two options; both deliver the easier ramp.

#### Option A — WWN initiative round (more WWN-faithful, larger change)

Lean fully into the path that already exists: route WWN `hp_depletion` combat through the
**WN sealed initiative round** (`run_wn_round`) as the *only* opponent-attack path, and
**add a defensive action** (full-defend / disengage) that, when the player commits it,
makes the opponent's slot **miss or be skippable** that round per the WWN SRD (e.g. the
defender imposes a to-hit penalty or the attacker rolls at disadvantage; SRD-sourced).
The opponent gets **one independent action per round at its initiative slot**, never a
free rider on the player's beat.

- **Pros:** genuinely WWN-faithful; one opponent action per round (kills the
  double-damage-vs-an-initiative-round problem in 106-2's evidence point #2); the
  infrastructure (initiative walk, per-slot opponent attack, sealed barrier) is **already
  built** in `wn_round.py`. Directly answers Keith's "is the reprisal native?" with "we
  retired the native rider for WWN."
- **Cons:** larger surface. Requires guaranteeing `encounter.initiative` is **always**
  populated for WWN fights (so the dispatch gate at dice.py:633-638 never falls to the
  legacy path — that fallback may need to become a **loud failure** for WWN rather than a
  silent legacy resolve). Requires a new player-facing *defend* beat in the beneath_sunden
  / WWN confrontation content and its tier semantics. Touches turn-economy expectations
  (the player may forgo offense to defend).

#### Option B — Keep the beat model, make defensive beats mitigate (smaller change)

Keep the per-beat structure but make the reprisal **read the player's committed beat** and,
when it is `brace` / `break_contact`, **reduce the opponent's to-hit and/or damage, or grant
the player a save** (magnitudes from the WWN SRD). Concretely: thread the pending-brace
mitigation value (the infra `beat_kinds.py:911-913` already anticipates) and/or a to-hit
penalty into `_resolve_opponent_reprisal` (dice.py:1566) so `target_ac` / the
`resolve_opponent_attack` call (dice.py:1636-1646) reflects the defense; optionally suppress
the reprisal entirely on a *successful* Break Contact.

- **Pros:** small, surgical; reuses the existing mitigation primitive
  (`apply_beat_hp_channel` / `target_mitigation`) and the `brace` BeatKind; no new content
  beat required; lands fast. Makes Brace immediately *worth choosing*.
- **Cons:** does **not** fix evidence point #2 (the reprisal still fires on the player's
  own turn, so two combatants still effectively act per player action — it is *mitigated*,
  not *one-action-per-round*). Less WWN-faithful; leaves the native rider in place, just
  declawed against defenders. The 106-3 "native mechanic ungated in a WWN world" critique
  partially persists.

> **Recommendation (Architect, non-binding):** Option A is the WWN-true answer and the
> infrastructure is 80% built (`wn_round.py`). If schedule forces it, Option B is a
> legitimate *first* increment that makes Brace matter and can be superseded by A later —
> but if we take B, the dispatch gate's silent legacy fallback for WWN
> (dice.py:639-650) should still be hardened toward A's "always have initiative or fail
> loud" stance so we don't ship two divergent WWN combat behaviors. **This is Keith's
> ruleset-design call per the epic (106 thread 2) and the bug entry's "Decision needed
> (Keith — ruleset design)."**

### Hard guardrails for Dev (whichever option)
- **WWN seam only (ADR-117).** Bind capability by `isinstance` against the WWN/SWN module
  class (as `wn_round.py` and dice.py:743-745 already do) — **no genre-string branches**,
  and the **native dial/confrontation path must be untouched** (native combat is unaffected).
- **SRD-sourced numbers.** Any to-hit penalty, AC swing, save target, or mitigation
  magnitude comes from the **WWN SRD** (gm-decisions.md standing ruling), not invented and
  hand-balanced. See MEMORY "Defer to SRD for mechanics."
- **No silent fallbacks.** If WWN combat can't resolve through the chosen path (e.g. missing
  initiative under Option A), fail **loud** — do not silently degrade to the unconditional
  legacy reprisal for a WWN world.
- **OTEL is the gate (CLAUDE.md OTEL principle + ADR-090/103).** The defensive decision must
  emit a span the GM panel can read — extend the existing
  `encounter.opponent_attack_resolved` span (dice.py:1649-1676) so it carries the player's
  defensive beat and the resulting to-hit/AC/damage delta, and/or add a
  `defensive_beat_mitigation` event. A reviewer must be able to see in OTEL that Brace
  *changed the enemy's roll*.
- **No source-text wiring tests** (CLAUDE.md): prove the wiring with an OTEL span assertion
  or a fixture-driven behavior test (synthetic WWN pack + seated opponent + a braced player,
  fire the real reprisal path, assert reduced to-hit/damage), not by grepping source.

## Scope Boundaries

- **In scope:** making a **defensive beat (Brace / Break Contact, or a new full-defend
  action under Option A) measurably reduce the WWN opponent reprisal** — lower to-hit and/or
  damage, grant a save, or (successful Break Contact / full-defend) prevent the attack that
  round; the OTEL span(s) that prove it; the WWN `RulesetModule` seam plumbing
  (`_resolve_opponent_reprisal` and/or the `run_wn_round` opponent slot); the
  dispatch-gate hardening required by the chosen option (loud-fail, not silent legacy
  fallback, for WWN). Content: if Option A needs a defend beat, the beneath_sunden / WWN
  confrontation content gets it.
- **Out of scope:**
  - **106-1** (equip starting armor / derive AC). That fixes the *baseline* AC the reprisal
    rolls against; this story fixes the *defensive-beat* response. They compound but are
    separate.
  - **106-3** (gate native edge/tag bleed + native XP). Option B leaves the native rider
    partially in place by design; do not expand into the edge/tag or XP bleed here. Note any
    overlap, don't fix it.
  - **106-4 / 106-5 / 106-6** (consumable-use, death-state coherence, narration-truth).
  - **Native (non-WWN) confrontation balance** — native dial combat is untouched.
  - UI polish beyond emitting the player-facing math the existing dice overlay already
    consumes (the to-hit/AC/damage values flow through the standard
    `DiceRequest`/`DiceResult` broadcast at dice.py:1678-1700; surfacing them is enough).

## AC Context

Acceptance criteria (TDD — RED tests first, OTEL/behavior assertions, no source-grep wiring):

1. **Brace measurably reduces the reprisal.** In a WWN `hp_depletion` fixture (seated
   opponent vs a player who commits **Brace**), the opponent's reprisal resolves with a
   **lower to-hit** (higher effective AC / to-hit penalty) **and/or reduced damage**
   (mitigation applied) **and/or a granted save** — i.e. the *same* opponent roll that would
   land against a Striking player is measurably worse against a Bracing player. (The
   playtest counter-fact: today Brace = Strike in damage taken; the test must show they now
   differ.) Numbers sourced from the WWN SRD.

2. **The player is not taking a full enemy attack on every beat regardless of choice.**
   Either (Option A) the opponent attacks **once per round at its own initiative slot** and a
   committed **full-defend / Break Contact** can make that attack **miss or not occur** that
   round; or (Option B) a **successful Break Contact** (and/or a sufficiently strong Brace)
   suppresses or substantially blunts the reprisal. A behavior test drives the defensive beat
   and asserts the player's HP loss for that round is **zero or strictly less** than the
   undefended baseline.

3. **OTEL-observable (the gate).** The reprisal/defense decision emits a span the GM panel
   reads — `encounter.opponent_attack_resolved` (or a new `defensive_beat_mitigation` event)
   carries the player's committed defensive beat and the resulting to-hit / target_ac /
   damage delta, so a reviewer can confirm in OTEL that **the defensive choice changed the
   enemy's roll** (lie-detector: prose claiming "you brace and the blow glances off" must be
   backed by a span showing reduced to-hit/damage). Drive the flow, assert the span fired
   with the mitigation values — do **not** assert on source text.

4. **WWN-gated, native untouched, fail-loud.** A native-ruleset (dial) confrontation fixture
   shows **identical** opponent behavior before and after this change (no regression to
   native combat). The capability is bound by module `isinstance` (ADR-117), not a genre
   string. A WWN fight that cannot resolve through the chosen path fails **loud** (no silent
   degrade to the unconditional legacy reprisal).

5. **Wiring test.** At least one integration/behavior test fires the **real** WWN dispatch
   path (`dispatch_dice_throw` → reprisal/`run_wn_round`) end-to-end with a braced player and
   asserts the mitigated outcome — proving the defensive mitigation is reachable from
   production code, per the CLAUDE.md wiring rule.

## Dependencies & Blockers

- **BLOCKED on Keith's ruleset-design ruling (Option A vs Option B).** Dev cannot start
  implementation until the ruling lands — the two options diverge in surface, content, and
  the dispatch-gate treatment. Architect recommendation is non-binding (lean A; B acceptable
  as a first increment if scheduled).
- **Compounds with 106-1** (armor/AC). Not a hard dependency — this story is testable
  against the current flat-AC reprisal — but ramp fairness is only fully realized with both
  levers.
- **Architect seam note** (this document) is the design-bearing prerequisite; Keith's ruling
  converts it into a buildable spec.
