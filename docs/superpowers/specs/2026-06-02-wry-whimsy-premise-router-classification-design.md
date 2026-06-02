# wry_whimsy Political Substrate — Intent-Router `witnessed_act` Classification (Plan 2b)

- **Status:** Draft (brainstorm output, pending user review)
- **Date:** 2026-06-02
- **Author:** Dev (Agent Smith)
- **Scope:** `sidequest-server` only — teach the LLM Intent Router (ADR-113) to emit `witnessed_act` dispatches from natural-language player actions.
- **Parent spec:** `docs/superpowers/specs/2026-06-02-wry-whimsy-premise-belief-flow-design.md` (answers its §13 Open Question 4).
- **Plan series:** Plan 1 (content schema + loader — merged), Plan 2 (runtime engine — merged: server PR #582, content PR #334). **This is Plan 2b** per the Plan-2 series map.
- **Related ADRs:** ADR-113 (Intent Router — mechanical-engagement spine), ADR-123 (mechanical-engagement pipeline / confidence gate), ADR-053 (belief/gossip), ADR-110 (snapshot slimming), the OTEL Observability Principle.

---

## 1. Motivation

Plan 2 shipped the `witnessed_act` dispatch subsystem: it is **registered**, **precondition-gated** (inert unless `snapshot.political_state` is hydrated), **confidence-gated** at `0.7` (`wry_whimsy/rules.yaml`), and **reachable** through the production `run_dispatch_bank` — proven by a synthetic-dispatch integration test. The engine drains a Premise's `belief_reserve`, soft-couples defiance into propping Blocs, fires collapse/tip thresholds, injects an ADR-053 contradiction into witness NPCs, and emits OTEL.

But **nothing emits the dispatch in real play.** The Intent Router (`sidequest/agents/intent_router.py`) is the pre-narrator pass that classifies each player action into a `DispatchPackage`; it has no knowledge of witnessed acts. Until it does, a player who clicks the Wizard's curtain aside in front of the Munchkins moves zero dials — the exact "is the game lying?" failure the parent spec exists to prevent. James's promised Munchkin revolution would be pure narration.

This plan is the **non-deterministic, prompt-engineering half** that makes the merged mechanical spine player-triggerable.

## 2. Goal

Teach the router to classify a player action as a witnessed act and emit:

```
SubsystemDispatch(
    subsystem="witnessed_act",
    params={"act_id": "<archetype id>", "witnesses": ["<present NPC names>"]},
    confidence=<0.0-1.0>,
)
```

so that — when confidence clears the `0.7` bar — the already-wired engine engages on the snapshot before the narrator runs.

## 3. Altitude (locked)

Prompt + classification work, surfaced as a **state-summary projection** plus a **static prompt vocabulary entry**, mirroring the existing `confrontation_types` mechanism (Story 59-10) exactly. No new engine, no new model, no content change. Evaluated primarily by playtest/eval; unit tests pin the wiring and the projection gating (the deterministic surface), not the model's classification judgment.

## 4. Design

### 4.1 The pattern being mirrored: `confrontation_types`

Story 59-10 established the template this plan copies:
- `intent_router.py` `_SYSTEM_PROMPT` statically describes the `confrontation` subsystem and instructs the model to pick a `type` **from a closed enum** named `game_state.confrontation_types`.
- `intent_router_pass.py` `_build_state_summary(snapshot, pack)` appends a compact `confrontation_types` projection (only when `pack.rules.confrontations` is non-empty) and fires `intent_router_confrontation_vocabulary_span`.

The closed-enum-in-state + static-instruction-in-prompt split is the idiom. `witnessed_act` follows it.

### 4.2 Edit A — static prompt vocabulary (`intent_router.py` `_SYSTEM_PROMPT`)

Add a `witnessed_act:` entry to the subsystem list (unconditional in the static prompt, like `confrontation`/`movement` — the prompt always *describes* the subsystem; whether the model can *use* it is governed by whether the state projection in 4.3 is present). The entry must convey:

- **Params shape:** `{"act_id": "<one of game_state.witnessed_act_vocabulary[].id>", "witnesses": ["<names drawn from game_state.present_npcs>"]}`.
- **What it is:** an *earned, public* act that contradicts a belief-powered authority or shows a cowed population that defiance survives (pull the curtain, name the humbug, break the forbidden rule and walk away, organize a first small refusal). The `act_id` MUST be one of the surfaced vocabulary ids — never invent an act.
- **The witness rule (spec §5):** witnesses are the NPCs who *perceive* the act. Populate `witnesses` only from `game_state.present_npcs`. **An act with no witness moves nothing** — if no one present perceives it, emit an empty `witnesses` list and a low confidence; do not invent a witness.
- **Confidence discipline:** reshaping a society is earned. Score honestly — a high score engages the dials, a low score degrades to a narrator hint. Don't inflate to force engagement (this is what the `0.7` content gate keys on).

Token cost: one short paragraph in the always-sent static prompt. **Zero per-turn vocabulary cost in the other ten genres** — the vocabulary list and present-NPC set only appear in worlds that hydrate a political layer (4.3).

### 4.3 Edit B — state-summary projections (`intent_router_pass.py` `_build_state_summary`)

Append two projections, **gated on `pack.witnessed_acts` being non-empty AND `snapshot.political_state is not None`**. The double gate ensures we never prompt the model to emit a dispatch the precondition gate would immediately drop (no router/gate contradiction, no wasted tokens in non-political worlds):

1. `witnessed_act_vocabulary`: `[{ "id", "label", "description" } for a in pack.witnessed_acts]` — the closed enum of available acts.
2. `present_npcs`: the witness candidate set — a compact list of present NPC **names**, computed by reusing the canonical scene-membership predicate `is_npc_in_scene(npc, current_room=snapshot.party_location(), encounter=snapshot.encounter)` over `snapshot.npcs` (Don't Reinvent — `sidequest/game/npc_scene.py`). Names come from `npc.core.name`.

Fire a new vocabulary span `intent_router_witnessed_act_vocabulary_span(act_count, present_npc_count, genre_slug)` when the projection is injected — the GM-panel record that the acts were surfaced (mirrors the confrontation-vocabulary span).

`present_npcs` is load-bearing for the "no witness moves nothing" rule: without an explicit closed set, the model cannot reliably distinguish an NPC *present in the scene* from one merely *mentioned in lore* inside the snapshot dump, and would hallucinate witnesses. Surfacing the candidate set makes empty-room acts visibly empty.

### 4.4 Edit C — classification-result OTEL (`intent_router_pass.py`, after `decompose()`)

After the router returns its `DispatchPackage`, when the vocabulary was surfaced this turn, scan the package for `witnessed_act` dispatches and fire `intent_router.witnessed_act_classified` with:
- `emitted`: count of `witnessed_act` dispatches in the package (0 = the router saw the vocabulary and decided this action is *not* a witnessed act),
- `act_ids`: comma-joined ids the router chose,
- `genre_slug`.

This is the classification-decision observability: the GM panel can now distinguish **"router classified this action as `witnessed_act:expose_the_humbug`"** from **"router had the vocabulary and chose not to emit one"** — the lie-detector for the front door, not just the engine.

## 5. Why this is the whole change

The dispatch bank, precondition gate, confidence gate, engine, belief injection, ledger, and engine-side OTEL are all live from Plan 2. The dispatch's *params contract* (`act_id` + `witnesses`) is exactly what the merged handler reads. So the only missing link is **the router producing that dispatch**, which is: (A) the model knowing the subsystem exists and its params, (B) the model knowing the available acts and present witnesses, (C) observability on the decision. Three edits, all in the two router files the brief names.

## 6. Out of scope (explicit non-goals)

- **No content change.** Vocabulary (`witnessed_acts.yaml`) and the `0.7` gate (`rules.yaml`) are already merged.
- **No engine change.** The two Plan-2 follow-ups — the `apply_witnessed_act` "touched-this-turn" collapse guard, and co-locating `witnessed_act` precondition coverage into `tests/agents/test_dispatch_precondition_gate.py` — are engine-side and ship as a **separate** small PR, to keep this a clean router-only diff.
- **No confidence-gate reimplementation.** The `0.7` threshold and the engage-vs-degrade decision already live in the bank (ADR-123). This plan only makes the router *score and emit*; the gate does the rest.
- **No multi-act-per-turn arbitration, no per-world prompt tuning, no spectacles/Standing UI** (Plans 4/5).

## 7. Testing

Prompt/classification work is evaluated by playtest/eval, but the **deterministic surface** (projection gating, span emission, end-to-end wiring) gets real tests. Per "No Source-Text Wiring Tests," wiring is proven by behavior/OTEL, never by grepping the prompt string.

1. **Projection gating (behavioral):** `_build_state_summary` **includes** `witnessed_act_vocabulary` + `present_npcs` for a political-world snapshot+pack; **omits both** when `political_state is None` *or* `pack.witnessed_acts` is empty (anti-bloat proof for the other genres).
2. **`present_npcs` correctness:** an NPC in-scene (via `is_npc_in_scene`) appears; an off-scene / lore-only NPC does not — reusing the canonical predicate, not a parallel one.
3. **Vocabulary span fires** when the projection is injected; **does not** fire in a non-political world (OTEL assertion).
4. **Classification-result span fires** after decompose with the right `emitted` count for a package containing (and not containing) a `witnessed_act` dispatch.
5. **Wiring test (the integration anchor):** drive the production `execute_intent_router_pre_narrator_pass` with a **stub** `IntentRouter` (no real Claude — monkeypatch `build_intent_router_for_session`, per the existing test idiom) whose `decompose` returns a `witnessed_act` package on a hydrated Oz-shaped snapshot; assert the dispatch flows through the bank and **mutates `political_state`** (belief drained, defiance coupled, ledger receipt). This proves router-emission → engine end-to-end on the real pre-narrator path, and that the stub router received a `state_summary` carrying the vocabulary.

DB-dependent flow tests that need `SIDEQUEST_DATABASE_URL` are environmental; the new tests are constructed to avoid Postgres (synthetic snapshot/pack fixtures). OTEL span-count tests run serially (`-n0`) to avoid the known parallel deadlock.

## 8. Risks

- **Router over-fires** witnessed acts on ordinary actions → the `0.7` content gate plus honest-confidence prompting are the backstop; the classification-result span makes over-firing visible in the GM panel for tuning.
- **`present_npcs` empty when it shouldn't be** (scene-membership false negatives) → reuses the single canonical predicate already trusted by the narrator's scene projection, so behavior matches the rest of the system; no new divergence introduced.
- **Prompt bloat** → mitigated by the double gate; non-political worlds see neither projection, and the static-prompt paragraph is small and shared like every other subsystem description.
