---
parent: context-epic-102.md
workflow: tdd
---

# Story 102-3: Explicit free-play cast classified as magic_working

## Business Context

The AC5b "from a world opening" blocker — and the purest Illusionism case in the epic. A player types "I cast foundation_of_flame" in free play and the narrator simply *narrates magic happening*: no `wwn.spell.cast`, `casts_remaining` unchanged, no Effort spent, and no `dispatch_engagement.magic_working.mismatch` to flag the miss. This is the exact scenario the OTEL-as-Illusionism-detector doctrine (SOUL purpose statement, CLAUDE.md OTEL principle) exists to catch: convincing narration with zero mechanical backing. It also violates the Zork-Problem counterpart — natural language must be a *first-class* mechanical verb, not a narration-only one; a career-GM player (Keith) immediately notices a cast that costs nothing.

## Technical Guardrails

- **The category exists; the route doesn't.** `agents/intent_router.py:145` already defines `magic_working` ("spell or magical ability usage") in the router's classification prompt/contract. The work is routing a classified `magic_working` intent into `resolve_spellcast` through the ADR-123 mechanical-engagement dispatch bank — check the dispatch bank's registration/precondition gates for where `magic_working` is currently unregistered or unhandled.
- **Reuse the cast spine** shared with 102-2 (`_resolve_wwn_cast_for_beat` / `resolve_spellcast`): same resolution, same spans, third entry point. No new cast implementation.
- **Spell-name resolution:** the typed name ("foundation_of_flame", "Foundation of Flame") must resolve against the caster's prepared/known spells. Unknown or unprepared spell → this is a *gate decision*, not a silent pass-through: either the precondition gate fires a mismatch span and the narrator handles the failed premise, or a typed refusal — never improv-with-no-spend.
- **Lie-detector assertion is the named deliverable:** `dispatch_engagement.magic_working.*` spans (engaged + mismatch variants) per ADR-123's confidence-gated dispatch. When the router classifies `magic_working` but no mechanical resolution fires, `dispatch_engagement.magic_working.mismatch` MUST be emitted — that span is the AC.
- **Router test discipline (project memory):** the intent-router pass must be stubbed in e2e/handler tests or they flake; test the router classification and the dispatch routing as separate seams, plus one live-ish wiring test.
- **Confidence gating:** respect ADR-123's confidence thresholds — an ambiguous "I draw on the fire within" may legitimately classify below threshold; the AC scenario is an explicit named cast, which must clear it.
- Scope is WN `core.spellcasting`/`core.effort` — NOT the retired plugin-framework `magic_state` path; the `magic_init.py:204` AND-gate bug is explicitly out of scope (epic context, non-goal).

## Scope Boundaries

**In scope:**
- Intent-router → dispatch-bank routing for `magic_working` to `resolve_spellcast` (free-play, out-of-confrontation world openings; in-confrontation free-text casts if the dispatch bank already seats them naturally)
- Spell-name → spell_id resolution against the caster's list
- `dispatch_engagement.magic_working.*` span coverage incl. mismatch
- Server tests: classification fixture, dispatch assertion, mismatch lie-detector assertion, wiring test

**Out of scope:**
- The dice-path/UI cast (102-2)
- New router categories or reclassification of other intents
- Psionics (102-6); narrator tool contract (102-5)
- The retired plugin-magic `magic_init` gate; long_foundry's orphaned 78KB `magic.yaml`

## AC Context

1. **Named free-play cast resolves mechanically.** "I cast foundation_of_flame" from a world opening in a WN genre → router classifies `magic_working` → `resolve_spellcast` fires → `wwn.spell.cast` span, `casts_remaining` decremented, Effort/Strain applied — and the narration reflects the *mechanical* outcome.
   - Edge: fuzzy name ("foundation of flame") still resolves; gibberish spell name → failed-premise handling with mismatch span, no spend.
   - Edge: caster with 0 casts remaining → mechanical refusal surfaced to narration, not silent success.
2. **Mismatch lie-detector fires.** If classification succeeds but dispatch cannot engage (precondition/unregistered gate), `dispatch_engagement.magic_working.mismatch` is emitted with reason attributes. Test forces the gate closed and asserts the span.
3. **Non-WN genre safety.** Same input in a native-ruleset genre does not crash and does not emit WN spans — follows that genre's magic story or a clean mismatch.
4. **Wiring proof.** One test drives player free-text through the real router (live classification, not stubbed) to the span, marked/isolated appropriately for determinism.

## Assumptions

- The ADR-123 dispatch bank has a registration surface where `magic_working` can be seated without reshaping the bank (if the bank needs structural change, flag to Architect before building).
- Spell catalogs (hydrated per 90-7 `wwn.magic_hydrated`) expose enough metadata for name-matching server-side.
- Router classification of explicit "I cast X" phrasing clears the confidence threshold reliably (if benchmarking shows it doesn't, prompt-contract tuning of the router is in-scope; new categories are not).
