# Handoff: Scene Harness (paused)

**Purpose:** Self-contained prompt for a fresh agent to pick up the scene harness work. Everything needed is in this file and `scene-harness.md`. Do not re-derive the context — it took ~2 hours of architect work and a full codebase verification pass to lock down.

---

## Your role

You are **Dev** (Major Charles Emerson Winchester III). You are executing an already-approved, already-verified plan. You are not here to redesign, re-verify, or improve the plan. You are here to ship the seven success criteria in `docs/plans/scene-harness.md`.

Read `docs/plans/scene-harness.md` in full before you do anything else. It is the source of truth. This handoff file is just orientation.

---

## What's already been done

1. **Architect wrote ADR-style plan v1** — over-confident, had ~15 unverified assumptions.
2. **Keith caught it** — "have we checked all the relevant schema and wiring?" Plan was rewritten after a 19-item verification pass against the real code. The v2 plan in `scene-harness.md` is that verified version.
3. **Verification found two existing ADRs** — ADR-069 (Scenario Fixtures, Accepted but 0/7 shipped) and ADR-074 (Dice Resolution Protocol, Proposed, half-shipped). **Do not update either ADR.** The plan explicitly supersedes 069's schema. Status fields on ADRs are not load-bearing.
4. **All 19 verification items resolved** with file:line citations. Summary:
   - GREEN (no plan change): items 4, 6, 12, 13, 14, 16, 17, 18, 19
   - YELLOW (minor adaptation): items 1, 3, 8, 9, 10, 15
   - RED (plan-shape changes): items 2, 5, 7 — all already folded into v2.
5. **Three starter fixtures mapped to real genre packs:**
   | Scene | Genre | World | ConfrontationDef verified in |
   |---|---|---|---|
   | poker | `spaghetti_western` | `dust_and_lead` | `sidequest-content/genre_packs/spaghetti_western/rules.yaml` |
   | dogfight | `space_opera` | `aureate_span` | `sidequest-content/genre_packs/space_opera/rules.yaml` |
   | negotiation | `pulp_noir` | `annees_folles` | `sidequest-content/genre_packs/pulp_noir/rules.yaml` |
6. **Character schemas for all three genres were read** (rules.yaml files). You can author the character blocks against verified `allowed_classes`, `allowed_races`, `ability_score_names` without more discovery. Quick reference:
   - **spaghetti_western:** classes = Gunslinger, Bounty Hunter, Outlaw, Drifter, Gambler, Marshal. Races = Frontier Born, City Exile, Border Crosser, War Survivor. Stats = GRIT, DRAW, NERVE, CUNNING, PRESENCE, LUCK. `point_buy_budget: 27`.
   - **space_opera:** classes = Officer, Operative, Pilot, Engineer, Medic, Smuggler, Diplomat, Soldier. Races = Coreworlder, Colonial, Spacer, Uplifted, Xeno, Synthetic. Stats = Physique, Reflex, Intellect, Cunning, Resolve, Influence.
   - **pulp_noir:** classes = Detective, Brawler, Grifter, Soldier of Fortune, Scholar, Smuggler, Performer. Races = Old Money, Street, Immigrant, Military, Academic, Frontier. Stats = Brawn, Finesse, Grit, Savvy, Nerve, Charm.
7. **`encounter.rs` was read in full.** `StructuredEncounter::from_confrontation_def()` exists at `sidequest-api/crates/sidequest-game/src/encounter.rs:285-326` and produces a ready-to-use encounter from any `ConfrontationDef`. You just pass it a def and it does the rest. Do not reinvent this.

---

## The three RED items the plan handles

1. **Beats cannot be hand-authored in fixtures.** They come from the genre pack via `find_confrontation_def()` + `from_confrontation_def()`. Your fixture YAML says `encounter.type: poker` and nothing more. If the type doesn't resolve, hydration errors loudly. Do **not** try to hand-author beats inline.

2. **`dispatch_connect()` does not emit `CONFRONTATION` on session restore.** This is a latent bug independent of scene harness — any save with an active encounter is broken on reload. The plan includes a 3-5 line fix in `sidequest-api/crates/sidequest-server/src/dispatch/connect.rs` that emits `CONFRONTATION` after snapshot load if `snapshot.encounter.is_some()`. This fix is **required, in-scope, non-negotiable**. Per Keith's feedback: fixes during cleanup work are never scope creep.

3. **No session creation API.** The dev route writes the fixture save via `persistence().save()` directly, then the normal `dispatch_connect` restore path picks it up when the UI connects with matching `{playerName, genre, world}`. Do not try to create a "create_session" function.

---

## Prerequisite: story 37-14 must land first

**Do not start scene harness work until story 37-14 is merged.** Keith explicitly said "we are finishing up the other one don't worry about it" — 37-14 is the priority.

- Story 37-14 is "Beat dispatch silently no-ops when beat_id is not in active encounter beat library"
- Phase: `green` (TDD)
- Branch: `feat/37-14-beat-dispatch-silent-drop` (in `sidequest-api`)
- TEA committed rework RED tests in `0ee0f55`. Session file `.session/37-14-session.md` has the full TEA assessment including a design question for Dev about OTEL event name collision (Option A recommended: rename inner emission to `encounter.state.beat_applied`).
- **Status at handoff:** RED committed, Dev has not started green yet. Scene harness conversation interrupted before 37-14 green started.

When you resume, the sequence is:
1. Pick up 37-14 green phase first. Read `.session/37-14-session.md`. Make the RED tests pass.
2. Ship 37-14 (commit, push, run exit protocol).
3. **Then** start scene harness work on a fresh feature branch off `develop` in each affected subrepo.

---

## Anti-deferral mandate (from Keith, verbatim)

> "DO NOT FUCKING DEFER ANYTHING FOR FUCK SAKE"

No "follow-up story." No "we can fix that later." No "this part is out of scope for v1 and we'll circle back." Every gap the plan names is in-scope for the current story. The plan's anti-scope section explicitly lists what is NOT in scope — trust that section, don't invent new ones.

Specifically forbidden:
- Writing a new ADR to "formalize" the scene harness design. The plan is the design.
- Updating ADR-069 or ADR-074. Status fields on ADRs are not load-bearing.
- Deferring the `dispatch_connect` CONFRONTATION emission fix to a separate story. It ships inside scene harness.
- Adding a "fixture editor UI" / "scene archetype registry" / "multiplayer support" / "character builder bypass". All four are explicitly anti-scope.

---

## Process discipline (also from Keith)

- **Don't be distracted** — every rabbit hole must serve shipping the seven success criteria.
- **Get all the facts but don't be distracted** — the verification pass is done; do not redo it.
- **Branch before editing** — each subrepo branches off `develop`, not `main`, not `docs/fix`.
- **Never checkout main on subrepos** — they use gitflow.
- **Always build on OQ-2** (this repo) before claiming anything works.
- **Verify wiring, not just existence** — the integration test in `sidequest-server/tests/scene_harness.rs` is the wiring gate. No gate, no done.
- **No silent fallbacks** — fixture errors must be loud.
- **Every test suite needs a wiring test** — the integration test is not optional.
- **No stubs** — if you can't finish a thing, don't leave a shell.
- **No competing cargo processes** — when you run tests, check `ps aux | grep cargo` first. One process at a time. 5-minute timeout.

---

## What to do first, in order

1. **Read `docs/plans/scene-harness.md` in full.** Every section. No skimming. This is ~10 minutes and it eliminates 90% of the questions you'd otherwise ask.
2. **Confirm story 37-14 is merged to develop** via `git log develop --oneline | head -5` in `sidequest-api`. If not, stop and go finish 37-14 first.
3. **Resolve the six open dependencies at the bottom of `scene-harness.md`** (grep-only, ~30 min). These are single-file reads:
   - `spaghetti_western/rules.yaml`, `space_opera/rules.yaml`, `pulp_noir/rules.yaml` — already verified during the architect pass, you just need the exact class/race values to plug into the character blocks. Summary in this handoff file above.
   - `encounter.rs` in full — already read. `from_confrontation_def` signature is at line 285.
   - `dispatch_connect.rs` — read to find the exact insertion point for the CONFRONTATION emission fix. File at `sidequest-api/crates/sidequest-server/src/dispatch/connect.rs`, ~600 lines, do **not** read the whole thing — grep for `persistence().load` or `saved_session` and read ±30 lines around the match.
   - `ConnectScreen.tsx` and `App.tsx` session bootstrap — locate the existing returning-player restore path and the function that triggers it. That's your reuse point for `?scene=` query-param handling.
4. **Create `sidequest-fixture` crate skeleton** in a new branch `feat/scene-harness` off `develop`. Register in workspace. Verify `cargo build --workspace` passes.
5. **Work the plan step by step** through sequencing items 3-13 in `scene-harness.md`. Each step has a time estimate and a verifiable output. If a step blows past its estimate by 2×, stop and reassess — do not push through.
6. **The integration test is the gate.** It must exist and pass before you commit the story as done.

---

## Success means

- `just scene poker`, `just scene dogfight`, `just scene negotiation` all land on an active EncounterSheet within 10 seconds of the command, on a fresh server boot, with no manual clicking through ConnectScreen.
- `sidequest-api/crates/sidequest-server/tests/scene_harness.rs` passes end-to-end.
- `dispatch_connect` CONFRONTATION-on-restore fix is in and tested.
- All commits on a clean `feat/scene-harness` branch per affected subrepo.
- No unwired code. No stubs. No deferrals. No ADR updates. No scope creep.

---

## Final reminder

**The plan is verified. The plan is correct. Execute the plan.** If you find yourself tempted to redesign a section, stop — re-read the plan and the relevant verification item. The answer is almost certainly already there.

If you hit something the plan genuinely did not anticipate (new wiring gap, API that disappeared since verification, etc.), stop and report to Keith **before** writing a workaround. Do not make silent shape changes.
