# F2 — Narrator / Intent-Router Integration — Epic Decomposition

> **This is a decomposition map, not an executable plan.** It scopes the four F2 sub-stories
> (F2a–F2d), their shared contracts, dependencies, and test/OTEL strategy. Each slice gets its
> own bite-sized implementation plan (mirroring F1a–F1d) before TDD execution. F2a is written in
> full alongside this doc (`2026-06-14-f2a-fate-action-classifier.md`); F2b/F2c/F2d plans follow
> once F2a's contracts land.

**Decision of record:** ADR-144 (Fate Core binding replaces the native ruleset).
**Design:** `docs/superpowers/specs/2026-06-14-fate-core-binding-replaces-native-design.md` §4.5, §5 (epic F2), §6 (OTEL).
**Depends on:** F1 (merged) — `FateRulesetModule`, `fate_conflict.py`, `FateSheet`, `FateActionPayload`, the 12 live Fate OTEL spans, and `dispatch_fate_action` (F1d).
**Branch base:** `develop` (gitflow). All paths under `sidequest-server/` unless noted.

---

## 1. Goal

F1 built the Fate engine and a single explicit entry channel: a `FATE_ACTION` `GameMessage` →
`FateActionHandler` → `dispatch_fate_action` → the conflict exchange. But **nothing turns a
player's freeform natural-language action into a Fate action**, and the **opponent does nothing
proactive** (F1c's exchange rolls reactive defense only — `fate_conflict.py:326` skips any
opponent slot with no sealed commit, and the module header explicitly defers opponent actions to
"the F2 narrator"). The narrator also can't see aspects, can't surface invokes, and can't propose
compels.

F2 closes that gap: a freeform action in a Fate-bound pack is **classified** into a Fate action and
routed through the existing dispatch spine; the narrator **sees aspects** as prompt fragments and can
**surface invokes and propose compels**; create-advantage outcomes are **rendered honestly** and
checked by a lie-detector; and the **opponent takes proactive Fate actions** via a deterministic AI.

## 2. Architecture (how F2 rides the existing spine)

The mechanical spine is **pre-narrator** (ADR-113, verified live):

```
player freeform action
  → IntentRouter.decompose(action, state_summary)         agents/intent_router.py:342  (Haiku, forced tool-use)
  → run_unregistered_subsystem_gate / run_dispatch_precondition_gate
  → run_dispatch_bank(package, context)                   agents/subsystems/__init__.py:234  (confidence-gated, topo-sorted)
       → run_<subsystem>_dispatch(dispatch, **ctx)        engages the engine on the canonical snapshot
  → LethalityArbiter
  → narrator turn (sees already-real state)               agents/orchestrator.py:1746 build_narrator_prompt
  → dispatch_engagement_watcher                            agents/dispatch_engagement_watcher.py  (the lie-detector)
```

F2 adds to this spine rather than building anything parallel (CLAUDE.md "Don't Reinvent — Wire Up
What Exists"):

- **F2a** registers a new `fate_action` subsystem in the bank and feeds the router a Fate
  vocabulary (skills + aspects) so it can classify freeform text into a `FateActionPayload`. The
  handler calls **the existing** `dispatch_fate_action` (F1d) — the freeform path and the explicit
  `FATE_ACTION` channel converge on one engine entry.
- **F2b** registers Fate prompt sections (aspects, fate points, invokable aspects) into the
  narrator prompt zones (`orchestrator.py` / `prompt_framework`) and adds a `propose_fate_compel`
  narrator tool.
- **F2c** surfaces the situation aspects F1c already creates into the prompt + the narration, and
  adds a Fate honesty watcher mirroring `dispatch_engagement_watcher`.
- **F2d** adds a deterministic opponent AI (mirroring WN's `_resolve_opponent_reprisal`,
  `dice.py:2011`) that auto-commits opponent Fate actions so the exchange resolves both sides.

## 3. Slice map

| Slice | Title | Depends on | Net-new surface |
|-------|-------|-----------|-----------------|
| **F2a** | Fate action classifier (router → `fate_action` subsystem → `dispatch_fate_action`) | F1d | `agents/subsystems/fate_action.py`, router Fate vocabulary, `fate.action.classified` span |
| **F2b** | Aspects-as-prompt + invoke surfacing + compel proposal | F1b, F2a | narrator Fate prompt sections, `propose_fate_compel` tool, invokable-aspect directive |
| **F2c** | Create-advantage rendering + Fate honesty lie-detector | F1c, F2a, F2b | situation-aspect prompt surface, `fate_engagement_watcher`, `fate.narration.mismatch` span |
| **F2d** | Opponent AI (deterministic proactive opponent action) | F1c, F2a | `game/fate_opponent.py` decision fn, auto-commit hook, `fate.opponent.decided` span |

**Ordering:** F2a first (it settles the shared contracts). F2b and F2d can run in parallel after
F2a. F2c depends on F2b (it renders into the prompt sections F2b registers) and on F2a's classifier.
F2d is engine-side and independent of the narrator slices, so it can land any time after F2a.

## 4. Shared contracts (defined in F2a, consumed by F2b/F2c/F2d)

1. **`fate_action` subsystem** — `run_fate_action_dispatch(dispatch, *, snapshot, pack, player_name)`
   in `agents/subsystems/fate_action.py`, registered in `_register_defaults()`
   (`subsystems/__init__.py:176`). Reads `dispatch.params` → builds a `FateActionPayload` → calls
   `dispatch_fate_action`. Returns an empty `SubsystemOutput()` on success (the engagement *is* the
   directive — same convention as `run_confrontation_dispatch`).

2. **`dispatch.params` shape for `fate_action`** (the router's typed output):
   `{"action": "overcome"|"create_advantage"|"attack"|"concede", "skill": str, "target": str|None,
   "difficulty": int, "invoke_aspect": str, "aspect_text": str}` — a 1:1 mirror of
   `FateActionPayload` (`protocol/fate.py`) minus `request_id` (the handler synthesizes one).

3. **Fate state-summary block** — `_build_fate_summary(snapshot, pack)` appends a `fate` key to the
   router state summary **only when `pack.rules.ruleset == "fate"`**:
   `{"skills": {pc_name: {skill: rating}}, "fate_points": {pc_name: int},
   "character_aspects": {pc_name: [aspect_text]}, "scene_aspects": [aspect_text],
   "active_conflict": bool}`. F2b reuses this same projection logic to build the narrator prompt
   sections (one source of truth for "what aspects/skills/points exist this turn").

4. **`fate.action.classified` OTEL span** — `fate_action_classified_span(actor, action, skill,
   target, confidence, ...)` in `telemetry/spans/fate.py`, with a `SPAN_ROUTES` entry. This is the
   F2 lie-detector anchor reserved by the spec (it does not exist yet — confirmed by grep). F2c's
   honesty watcher reads it.

5. **Precondition** — `fate_action` is structurally inert when `snapshot.encounter is None or
   snapshot.encounter.resolved` (the in-conflict scope, matching `dispatch_fate_action`'s own guard).
   Registered in `_INERT_PRECONDITIONS` (`dispatch_precondition_gate.py:130`).

## 5. OTEL inventory (the lie detector — spec §6)

Live after F1 (do not re-add): `fate.action_resolved`, `fate.fate_point.delta`,
`fate.aspect.invoked`, `fate.compel.offered`, `fate.compel.accepted`, `fate.stress.applied`,
`fate.consequence.taken`, `fate.exchange.{committed,order,resolved}`, `fate.aspect.created`,
`fate.taken_out`, `fate.conceded`.

New in F2:

| Span | Slice | Fires when |
|------|-------|-----------|
| `fate.action.classified` | F2a | the router classified a freeform action into a `fate_action` dispatch (action + skill + target + confidence) |
| `fate.compel.offered` (already exists — F2b just *fires* it) | F2b | the narrator proposes a compel via the new tool |
| `fate.narration.mismatch` | F2c | the narrator's prose claims a Fate outcome the engine never produced (mirrors `dispatch_engagement.{subsystem}.mismatch`) |
| `fate.opponent.decided` | F2d | the deterministic opponent AI picked an action/target/skill and auto-committed it |

## 6. Test strategy (per slice)

- **Wiring tests are mandatory and must not be source greps** (server CLAUDE.md "No Source-Text
  Wiring Tests"). Every slice drives its path through the **real** registry/bank/handler and
  asserts an **OTEL span** or a **state mutation**, never `read_text()` on a source file.
- **F2a:** (1) a freeform `fate_action` dispatch driven through the real `run_dispatch_bank` reaches
  `dispatch_fate_action` and the exchange resolves (`fate.exchange.resolved` + `fate.action.classified`
  fire); (2) `fate_action` is a registered subsystem key (runtime `get_registered()` check); (3) the
  precondition gate drops a `fate_action` with no active encounter and emits the gated span;
  (4) state-summary enrichment is absent for a non-Fate pack and present for a Fate pack.
- **F2b:** the Fate prompt sections appear in the assembled prompt for a Fate pack (behavior test on
  `build_narrator_prompt` output, not a grep); the `propose_fate_compel` tool dispatches through the
  real tool registry and fires `fate.compel.offered`.
- **F2c:** a narrator turn that creates an advantage surfaces the new situation aspect into the next
  prompt; the honesty watcher fires `fate.narration.mismatch` on a fabricated-outcome fixture.
- **F2d:** an exchange with an undefeated opponent has the opponent auto-commit a proactive action
  (a PC takes stress) and fires `fate.opponent.decided`; subprocess registry test for any
  import-time registration (in-process autouse conftest masks it — project memory
  `import-sideeffect-registry-wiring-needs-subprocess-test`).

## 7. Open design decisions (resolve at slice-plan time / Keith review)

1. **Out-of-conflict overcome/create-advantage.** Fate's four actions also apply *outside* a
   conflict (overcome to pick a lock, create-advantage to set up a scene). `dispatch_fate_action`
   (F1d) requires an active encounter and is conflict-scoped. **F2a scopes to in-conflict actions**
   (the keystone). Out-of-conflict overcome is a plain `ruleset.resolve_action` call with no
   exchange machinery — recommend a small follow-up (F2a-2 or folded into F2c) rather than
   overloading `dispatch_fate_action`. **Flagged, not silently dropped.**
2. **Compel acceptance channel.** A compel is narrator-*proposed* (`fate.compel.offered`), but
   acceptance earns a fate point and is the player's choice. ADR-107 (out-of-band aside channel) is
   the natural carrier. F2b proposes; the accept/refuse round-trip may be an F2b task or deferred to
   F3 (UI). Recommend: F2b emits the offer + stores a pending compel on the snapshot; the
   accept path (calling `ruleset.accept_compel`, F1b) lands with the F3 UI surface.
3. **Opponent action selection heuristic (F2d).** Deterministic, mirroring WN. Proposed rule:
   attack a PC who already took a consequence this exchange; else invoke an available situation
   aspect the opponent benefits from; else attack the first live opposing actor (or the taunter, as
   WN does). Skill = the NPC's best physical/social skill for the conflict track. No LLM call.
4. **Honesty watcher mechanism (F2c).** Reuse the `dispatch_engagement_watcher` pattern (a post-turn
   pure check + a thin span-emitting wrapper). The Fate check: if the narration claims an advantage
   was created / a foe taken out, assert the matching `fate.aspect.created` / `fate.taken_out` span
   fired this turn; else emit `fate.narration.mismatch`.

## 8. Non-goals (YAGNI — inherited from spec §9)

- 4dF dice overlay + Fate-point/aspect UI panels (F3).
- Binding `ruleset: fate` on the four packs + per-genre skill lists (F4).
- Native removal + seam re-cut (F5).
- A `MagicPlugin` for Fate (Extras/stunts are content).
