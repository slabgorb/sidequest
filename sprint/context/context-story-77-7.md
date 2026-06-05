# Story 77-7 Context

## Title
Engine lull-escalation — drive a Bang/complication when turns_since_meaningful climbs (ADR-024/025/128)

## Metadata
- **Story ID:** 77-7
- **Type:** story
- **Points:** 5
- **Priority:** p2
- **Workflow:** tdd
- **Repo:** sidequest-server
- **Epic:** Quest & Stakes Substrate

## Problem
GAP (Keith playtest, wry_whimsy/gulliver): the engine is PASSIVE — 'had to prod a bit to get the action going.' Both set-pieces were player-initiated; the narrator reacted well but never DROVE. Per Living World + Cut-the-Dull-Bits, when a game lulls the engine should PUSH: name a stake, fire a complication, an NPC acts on its own goal. Today nothing fires — the scenario subsystem went silent the whole session (coverage_gap turn 29: subsystem=scenario, silent_turns=10), active_seeds=[], active_stakes=''. For a forever-GM who wants to be SURPRISED, this is the difference between 'fun but I had to prod' and 'fun and it kept coming at me.'

REUSE MAP (Explore 2026-06-04, develop): the lull SIGNAL already exists — TensionTracker (game/tension_tracker.py) computes boring_streak + drama_weight every turn (fed via observe() at websocket_session_handler.py:~2048) and pacing_hint() ALREADY trips escalation_beat at boring_streak>=escalation_streak (tension_tracker.py:~359-383) — but only as a GENERIC narrator text hint ('The environment shifts — introduce a new element'), consumed by NO engine. The Bang CATALOG already exists — seed_tropes deck (ADR-128): game/seed_deck.py (deterministic draw-without-replacement via SHA-256 of session_id), game/seed_tick.py (ensure_initial_draw/draw_engaged_seed/tick_seeds), rendered to the narrator by agents/seed_context_builder.py; SeedTrope.narrative_hint (genre/models/tropes.py:81) exists. Governor caps live (game/trope_tuning.py: MAX_SIMULTANEOUS_ACTIVE, FIRE_COOLDOWN_TURNS). SPAN_SEED_FIRED exists (telemetry/spans/seed.py) but has NO consumer. MISSING: a SELECTOR that, on the live lull signal, picks one active seed (or draws one) and FIRES it as a CONCRETE escalation directive into the next turn — plus an OTEL span proving the engine pushed.

DESIGN (Architect / White Queen — v1 load-bearing slice, reuse-first, NO new ADR — enacts ADR-024/025/128): (1) TRIGGER reuses the EXISTING signal — boring_streak>=escalation_streak (pacing_hint.escalation_beat present). NO new ADR-025 per-category quiet-turn detector in v1; ride the live ADR-024 tension track. (2) SELECT one seed from snapshot.active_seeds (prefer scene-fit via flavor_tags/delivery_hints; deterministic resume-safe tie-break from (session_id, turn, drawn_ids) — reuse the seed_deck SHA-256 pattern, NO Math.random/wallclock). If active_seeds empty, draw one first (reuse draw_engaged_seed). (3) FIRE — convert the selected seed's narrative_hint into the concrete escalation directive injected for the NEXT turn's narrator context, REPLACING the generic escalation_beat text; mark the seed fired (give SPAN_SEED_FIRED its first real consumer) and advance lifespan via the existing tick. (4) GOVERN — respect FIRE_COOLDOWN_TURNS (never fire two turns running). (5) SEAM — post-bump, peer to tick_seeds (websocket_session_handler.py:~1170-1191), reads sd.tension_tracker, mutates snapshot.active_seeds in place, same shape as tick_tropes/tick_seeds. (6) OTEL is LOAD-BEARING here (the whole point — the lie detector for 'did the engine push or did Claude improvise?'): new routed SPAN_LULL_ESCALATION.

DEFER (explicit non-goals, documented not built): (a) NPC-autonomous-goal escalation (ADR-053 living-world/gossip is DORMANT; npc_agency is reactive-only) — v2; (b) the full ADR-025 per-category quiet-turn detector (boring_streak is the sufficient v1 lull signal); (c) a separate Bang-catalog struct distinct from seed_tropes. v1 = wire the EXISTING lull signal to fire an EXISTING seed, with proof. If the selector policy (which seed / cooldown composition with the ADR-128 governor) needs ratification during the dev's first design pass, escalate to a thin ADR then (epic-59 pattern). Sibling content: 77-6 (author the wry_whimsy seed_tropes deck — gives the selector something to throw; FIXER already PR'd #347).

## Technical Approach
_Approach hints to be refined by TEA/Dev. The story title above defines the
intended behavior._

## Scope
- In scope: the behavior described by the story title.
- Out of scope: unrelated changes.

## Acceptance Criteria
- Lull trigger reuses the LIVE signal: when TensionTracker reports boring_streak >= escalation_streak (pacing_hint.escalation_beat present), the new post-bump escalation step engages; below threshold it is a no-op. NO new pacing detector — ride the existing ADR-024 tension track. Test: synth a snapshot with boring_streak at threshold → step fires; below → no-op.
- Select-and-fire an active seed: on lull, select one seed from snapshot.active_seeds (deterministic, resume-safe tie-break from session_id+turn+drawn_ids) and FIRE it — its narrative_hint becomes the concrete escalation directive in the NEXT turn's narrator context, REPLACING the generic 'environment shifts' escalation_beat text. If active_seeds is empty, draw one first (reuse draw_engaged_seed) then fire. Test: active seed present → that seed's hint is the injected directive; empty → a seed is drawn then fired.
- Respect the ADR-128 governor: never fire on consecutive turns (FIRE_COOLDOWN_TURNS, game/trope_tuning.py); mark the fired seed's state so it expires normally via tick_seeds. Test: two lull turns in a row → fires turn 1, cooldown-skips turn 2 with reason=cooldown.
- OTEL (LOAD-BEARING — the lie detector for engine-push vs narrator-improv): emit a ROUTED SPAN_LULL_ESCALATION every time the step runs, carrying boring_streak, drama_weight, fired(bool), selected_seed_id|null, reason(fired|cooldown|none_available). It must light the pacing/tension subsystem on the GM panel ③ grid for the firing turn. SPAN_SEED_FIRED gains its first real consumer on fire. Test: span asserted on fire AND on cooldown-skip with correct reason (OTEL span assertion, not source-grep).
- Seam + resume safety + wiring: the step runs post-record_interaction, peer to tick_seeds (websocket_session_handler.py:~1170-1191), reads sd.tension_tracker, mutates snapshot.active_seeds in place; selection is deterministic (no Math.random/wallclock) so a resume re-fires identically. Wiring test (behavioral, not source-grep): drive a real lull turn through the handler and assert the NEXT turn's narrator context carries the seed-derived escalation directive.
- DEFER — explicit non-goals, documented in the story, NOT built: (a) NPC-autonomous-goal escalation (ADR-053 dormant; npc_agency reactive-only); (b) full ADR-025 per-category quiet-turn detector; (c) a separate Bang-catalog struct distinct from seed_tropes. v1 fires an existing seed on the existing lull signal with OTEL proof.

---
_Generated by `pf context create story 77-7` from the sprint YAML._
