# Brainstorming Handoff — How should the OTEL playtest *prove* combat & magic fire?

**Date:** 2026-06-05
**From:** Dev (story 87-4, green phase)
**For:** a `superpowers:brainstorming` session (start here, do not jump to a plan)
**Status:** AC5 of story 87-4 is **blocked-pending-design** — the verification approach, not the engine, is what needs rethinking.

---

## The one-sentence problem

Our two heavy_metal OTEL playtest scenarios drove a character to fight and cast spells, the narrator *described* fighting and casting — and the mechanical engines (WWN combat confrontation, `wwn.spell.cast`) **never fired**, because the narrator never seated a hostile **Other**. The lie-detector caught it. So: **how do we design an OTEL playtest that deterministically exercises combat + magic, so AC5 can assert the spans actually fired — without violating the epic's "zero engine changes" premise and without faking the narration path we're trying to validate?**

That is the question to brainstorm. Everything below is evidence and constraints.

---

## Background

- **Epic 87** = faithful port of the `heavy_metal` genre pack onto the **WWN** (Worlds Without Number) ruleset. Premise: **zero engine changes** — it's a content + verification effort.
- **Story 87-4** is the final integration gate. AC5 (the lie-detector gate) reads:
  > *"evropi and long_foundry sessions: combat turn fires `wwn.*` spans + ablates HP; a caster turn fires the spell-cast span with cast spent; no mechanically-unbacked combat/magic narration observed. Evidence (span lists) attached to the session file."*
- The WWN mechanics themselves are **already proven by integration tests** (`test_wwn_heavy_metal_combat.py` — HP ablation, no-toothless-Other, opponent reprisal, `cast_spell` routing, caster Effort seeding: 9 passed). What AC5 wants is the *live narrator-in-the-loop* proof on both worlds.
- Authoritative spec: `docs/superpowers/specs/2026-06-04-heavy-metal-wwn-port-design.md` (§5 Story 4, D5, §8).

## What we did

Ran both authored scenarios live against the running stack (Sonnet narrator, OTEL→Jaeger, span capture):
- `scenarios/heavy_metal_evropi_otel.yaml` — Necromancer caller, 10 actions (look → arm → find a fight → strike → press → cast spell → cast again → finishing blow → check wounds → loot).
- `scenarios/heavy_metal_long_foundry_otel.yaml` — Pact-born caller, same 10-action shape.

Span dumps: `~/.sidequest/logs/87-4-playtest/{evropi,long_foundry}-spans.jsonl`. Jaeger UI: http://localhost:16686 (service `sidequest-server`).

## What we found (the evidence)

| Signal | evropi | long_foundry |
|---|---|---|
| `wwn.spell.cast` | **none** | **none** |
| confrontation seated / resolved | **none** | **none** |
| HP-ablation span | **none** | **none** |
| `confrontation.intent_mismatch` (lie-detector) | ×3 (`strike`, `spell`) | yes (`spell`, `press`) |
| `intent_router.dispatch.gated` | ×3 — magic_working | ×3 — magic_working + scenario_state |
| `dispatch_engagement.movement.mismatch` | ×1 (PC never relocated to a fight) | — |
| narration turns | 7 | 8 |

Timing (player-facing narrator latency, from `narration.turn` durations): per-turn **8–23 s**, median ~15–17 s; ~112–135 s total narration; ~261–269 s full wall-clock (chargen + intent-router + dispatch + render-drain account for the rest). Model `claude-sonnet-4-6`. Per-run session cost ~$0.17–0.38.

## Why it happened (root cause)

1. **No Other was ever seated.** The narrator kept the PC in a *social* opening (evropi: Upre Town Hall + a neutral courier). "Find someone hostile / strike the nearest enemy" did **not** produce a seated opponent or even relocate the PC. With no Other, ADR-116/139 correctly refuses to start a confrontation.
2. **`cast_spell` is a confrontation beat.** The WWN spell-cast path only fires *inside* a seated confrontation. No confrontation → no `cast_spell` → the "cast a spell" action fell through to the generic `magic_working` (ADR-126 pact-working) dispatch...
3. **...which gated.** `snapshot.magic_state is None`. In evropi that's expected (no world magic plugin). In **long_foundry it's a surprise** — the world *ships* a `magic.yaml` ADR-126 plugin, yet the runtime snapshot's `magic_state` is still `None`, so the plugin was never instantiated into the session.
4. **The engine was honest.** The lie-detector spans (`confrontation.intent_mismatch`, `dispatch.gated`, `movement.mismatch`) are the system correctly reporting "prose claimed mechanics that didn't engage." This is the OTEL Observability Principle working as designed — it's *good news about the engine*, and *bad news about the test*.

**Conclusion:** This is not an engine bug. It's a verification-design gap — free-form narration from a peaceful opening doesn't deterministically produce combat, so the scenarios can't prove the positive.

---

## The design tension to chew on (the real meat)

This sits on a genuine SOUL-principle fault line, which is why it deserves brainstorming rather than a quick patch:

- **Is the narrator's refusal to manufacture a fight *correct behavior*?** "Living World" + "Untaken bait / never force a bite" say the narrator shouldn't conjure a hostile Other just because the player typed "I look for a fight" in a town hall. ADR-116 ("a confrontation requires an Other") backs the engine's refusal. By that reading, the *scenarios* are naive and the system is right.
- **Or is it a gap?** A player who genuinely seeks a fight should be able to find one; a world opening that *can't* escalate to combat within ~10 turns may be a content/scene problem (no proximate antagonist, no "bait" placed). By that reading, the world's opening scenes and/or trope deck under-supply confrontation hooks.
- **And what does that mean for *testing*?** If we make the playtest deterministically seat a fight (scene-harness fixture), we prove the WWN mechanics fire — but we *bypass the narrator's scene-setup judgment*, which is part of what AC5's "live" framing wanted to exercise. Where's the honest line between "deterministic enough to assert spans" and "real enough to be a narrator-in-the-loop test"?

## Open questions for the session

1. What is the **right artifact** for AC5's "combat + magic fire mechanically" proof — a scene-harness fixture run, a smarter scenario, a narrator-steering primitive, or a combination?
2. Should scenarios gain a way to **assert a starting situation** (a seated Other / active confrontation) the way `/dev/scene` fixtures do — and is that a content surface or a harness surface?
3. Is "narrator won't seat a fight from a social opening" a **bug to fix in content** (opening scenes / trope hooks that supply antagonists) or **correct behavior to preserve**? Does the answer differ per world?
4. The **`magic_state is None` for a world that ships `magic.yaml`** (long_foundry) — is the ADR-126 world plugin supposed to instantiate at session start, or only on a trigger? Separate thread; may be engine-side and out of 87-4 scope, but needs a home.
5. Should AC5 be **re-scoped** (split the "mechanics fire" proof from the "narrator engages mechanics from free play" proof)? The former is testable today; the latter is the hard, interesting one.
6. Generalization: **every genre/world OTEL gate** will hit this. Is there a reusable pattern (fixture library? a "combat-capable opening" content requirement? a playtest assertion DSL)?

## Constraints / non-negotiables to respect

- **Zero engine changes** is the epic 87 premise. A solution that needs server code is a different epic — name it as such, don't smuggle it in.
- **Don't reduce the narrator to keyword matching** or gate actions behind menus (the Zork Problem). Whatever we do to force combat for *testing* must not bleed into constraining real play.
- **No source-text wiring tests** (server CLAUDE.md) — assert OTEL spans / behavior, not greps.
- Cost is not a real constraint here (Keith, 2026-06-05: "don't worry about the charges so much" — bounded scenarios are ~$0.40 and the `--max-projected-cost-usd` cap guards runaway).

## Candidate directions (seeds only — do NOT pre-decide)

- **A. Scene-harness fixture.** Author a heavy_metal `/dev/scene` combat fixture (route is live at `scenarios/fixtures/`, no `DEV_SCENES` gate anymore), drive both worlds via `playtest.py --fixture`, assert `wwn.*` + `wwn.spell.cast`. Deterministic; but bypasses chargen/scene-setup narration.
- **B. Content fix.** Give the opening scenes / trope decks a proximate antagonist so "find a fight" can actually escalate; keep the free-narration scenario. Most faithful to "live" intent; least deterministic.
- **C. Scenario primitive.** Extend the scenario schema with an optional "start in confrontation / seat this Other" directive that the harness hydrates. Middle path; new content surface.
- **D. Re-scope AC5.** Accept the integration tests as the "mechanics fire" proof; redefine the *playtest's* job as "the engine stays honest under free play" (which these two runs already demonstrate). Cheapest; may under-deliver the epic's intent.

## Artifacts / pointers

- Findings recorded in `.session/87-4-session.md` (Delivery Findings + Dev Assessment).
- Span dumps: `~/.sidequest/logs/87-4-playtest/{evropi,long_foundry}-spans.jsonl`; run logs alongside.
- Scenarios: `scenarios/heavy_metal_{evropi,long_foundry}_otel.yaml`.
- Spec: `docs/superpowers/specs/2026-06-04-heavy-metal-wwn-port-design.md`.
- Relevant ADRs: 116/139 (a confrontation requires an Other), 113/123 (intent router + dispatch bank), 092 (scene-harness HTTP endpoint), 126 (pluggable magic), 031/090/103 (OTEL).
- Lie-detector span names to know: `confrontation.intent_mismatch`, `intent_router.dispatch.gated`, `dispatch_engagement.{subsystem}.mismatch`.

## Suggested room

Architect (verification strategy + the engine/content/harness boundary), PM/BA (AC re-scope question), and the world-builder/content perspective (opening-scene antagonist supply). Keith is the tie-breaker on the "correct behavior vs gap" SOUL question.
