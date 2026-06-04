---
story_id: "59-30"
jira_key: ""
epic: "59"
workflow: "tdd"
---
# Story 59-30: _WITNESSES engagement witness for witnessed_act + movement (close political-spine lie-detector gap)

## Story Details
- **ID:** 59-30
- **Jira Key:** (none)
- **Workflow:** tdd (phased)
- **Stack Parent:** none
- **Epic:** 59 (Intent Router — Mechanical-Engagement Spine)

## Story Context

### Problem
The generic engagement watcher (`sidequest-server/sidequest/agents/dispatch_engagement_watcher.py:180`) has a `_WITNESSES` dict that covers only 6 subsystems:
- confrontation
- magic_working
- scenario_clue
- npc_agency
- distinctive_detail_hint
- reflect_absence

**Missing:** `witnessed_act` and `movement` are now live dispatch paths but have no watcher coverage. Without witnesses, the "dispatched-but-didn't-engage" lie detector cannot flag:
- Router classifies `witnessed_act` but political-state dials never move
- Router classifies `movement` but PC region doesn't relocate

This leaves a visibility gap in the OTEL observability layer that the GM panel relies on to distinguish true engagement from improvisation.

### Scope
- **Engine:** sidequest-server
- **Repos:** sidequest-server
- **Dependent Story:** 59-30 is a prerequisite for 59-31 (opponent-yield signal)

### Architecture Context (ADR-113 Intent Router)
The Intent Router workflow is:
1. Pre-narrator, Haiku via SDK classifies player action intent → emits `intent_router.decompose` span
2. Router produces `DispatchPackage` with subsystem dispatch targets
3. `run_dispatch_bank` engages engines BEFORE narrator
4. Post-turn watcher (dispatch_engagement_watcher.py) checks: did the dispatched subsystem actually change state?

The watcher's `_WITNESSES` dict maps subsystem → `_check_<subsystem>_engaged(package, snapshot)` function. Each witness:
- Takes the dispatched package and post-turn snapshot
- Returns None if state moved (engaged) or a evidence string if not (mismatch)
- Fires `dispatch_engagement.<subsystem>.mismatch` span on mismatch

### Missing Witnesses
**witnessed_act:**
- Dispatched by intent_router (plan 2b / PR #583, live)
- Engine: `political_engine.py::apply_witnessed_act` emits `political.premise.*` and `political.bloc.*` dial spans
- **Evidence of engagement:** At least one political-state dial (premise or bloc) moved this turn
- **Mismatch signal:** Router dispatched `witnessed_act` but no dials moved

**movement:**
- Dispatched by intent_router (motion/travel intent)
- Engine: `movement.py` relocates PC to a new region via `snapshot.update_region`
- **Evidence of engagement:** PC's `current_region` changed on snapshot
- **Mismatch signal:** Router dispatched `movement` but PC region unchanged

### Technical Approach
1. Add `_check_witnessed_act_engaged(package, snapshot)` function:
   - Extract pre/post political_state from package + snapshot
   - Check if any premise or bloc dial value changed (not just created, but *moved*)
   - Return None if moved, else a string describing which dials were static

2. Add `_check_movement_engaged(package, snapshot)` function:
   - Extract PC region from dispatch context + post-turn snapshot
   - Check if `current_region` changed
   - Return None if relocated, else "PC region unchanged" (with current/expected values for debugging)

3. Register both in `_WITNESSES` dict at the module level

4. Correct stale docstring at line ~221 that says "all six live-path subsystems" — update to reflect the actual count (8 registered)

5. Add unit tests for both witnesses:
   - Positive cases: engaged → return None
   - Negative cases: dispatched, not engaged → return evidence string

### Acceptance Criteria
- `_check_witnessed_act_engaged` added and registered in `_WITNESSES`; flags mismatch when `witnessed_act` dispatched but no political-state dial moved
- `_check_movement_engaged` added and registered in `_WITNESSES`; flags mismatch when `movement` dispatched but no region relocation occurred
- Stale "all six live-path subsystems" docstring corrected to the actual registered count
- Watcher unit test per new witness: positive (engaged → None) and negative (dispatched, not engaged → evidence string)

### Blocking / Dependencies
- Prerequisite for 59-31 (opponent-yield signal watcher)
- Non-blocking relative to other live dispatch paths (independent witness additions)

## Workflow Tracking
**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-06-04

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-04 | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Reviewer (code review)
- **Improvement** (non-blocking): `RegionTransition.via` is typed `str` but only ever takes `"world_patch"` | `"narration_apply"`. A `Literal["world_patch", "narration_apply"]` (or enum) would make the two-site contract self-documenting and catch a typo at a future third stamp site. Affects `sidequest-server/sidequest/game/session.py` (`RegionTransition.via` annotation). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `run_dispatch_engagement_watcher` does not wrap per-witness `check(...)` calls in a try/except, so an unexpected exception in any witness would propagate into the post-narration WS turn path (handler:974). Pre-existing (the original 6 witnesses share it); the 59-30 witnesses are defensively written and cannot raise on bad input, so this is latent. A future hardening could guard each witness call so one buggy witness can't hang turn delivery. Affects `sidequest-server/sidequest/agents/dispatch_engagement_watcher.py`. *Found by Reviewer during code review.*
- **Question** (non-blocking, forward to 59-31): the movement-witness identity bridge assumes `player_seats[player_id] == sd.player_name` (character name). This holds today, but if a character is renamed post-chargen without updating `player_seats`/`sd.player_name`, Site B (`pc_regions[player_name]`) and the witness lookup (`player_seats.get(player_id)`) could key on different names and false-flag. Not introduced by 59-30 and out of scope, but the per-PC attribution thread 59-31 reuses inherits the same assumption — worth an invariant test if rename ever ships. Affects `sidequest-server/sidequest/server/websocket_session_handler.py`. *Found by Reviewer during code review.*

### TEA (test design)
- **Improvement** (non-blocking): The `witnessed_act` engine resolves `act_id = params.get("act_id") or params.get("act_archetype")` (`witnessed_act.py:102`), so a dispatch carrying only `act_archetype` engages and writes its ledger entry under the resolved id. The witness MUST resolve the same alias or it false-flags a legitimately-engaged turn. Tests pin this parity (`test_witnessed_act_act_archetype_alias_engaged_returns_none`). Affects `sidequest-server/sidequest/agents/dispatch_engagement_watcher.py` (witness must mirror the alias, not normalize to `act_id`-only). *Found by TEA during test design.*
- **Question** (non-blocking): `RegionTransition`'s module home is left open by the Architect note ("game/region_transition.py or session.py"); the FINAL Q1 pin-down homes the *field* on `GameSnapshot` but not the *model's* file. Tests import via a dual-path shim preferring `sidequest.game.session`. If Dev defines it in a separate module, re-export from `sidequest.game.session` (or the shim's fallback path resolves it). Affects `sidequest-server/sidequest/game/` (model placement). *Found by TEA during test design.*
- **Question** (non-blocking, GREEN-time verify): The Architect's §4 [VERIFY] flag stands — Dev must confirm at the router-output construction site that `PlayerDispatch.player_id` is the same seat id `player_seats` is keyed by (the movement witness's `player_seats.get(player_id)` bridge depends on it). Tests assert the witness returns LOUD evidence on an unresolvable player_id (`test_movement_player_id_without_seat_returns_evidence`) rather than guessing — do NOT add an `or player_id` / "single seated PC" fallback. Affects `sidequest-server/sidequest/agents/intent_router.py` (or wherever player_id is set) + the witness. *Found by TEA during test design.*

### Architect (design)
- **Question** (blocking — movement only): The specced movement witness ("check if `current_region` changed") is **not implementable as written** with the current witness signature. Two structural blockers: (1) the witness gets only `(SubsystemDispatch, post-turn snapshot)` — no pre-turn baseline to diff a region change against, and `_iter_all_dispatches` yields a *bare* `SubsystemDispatch`, dropping the `PlayerDispatch.player_id`, so a per-PC `pc_regions` witness can't even tell *which* PC to check; (2) in **region-mode worlds** (`wry_whimsy/oz`, `wonderland`, `gulliver`) `run_movement_dispatch` deliberately applies **no patch** and defers the region change to the `narration_apply` heading→region path (returns `region_mode_deferred`, fires non-error `movement.region_mode` span) — so a region-equality check both lacks a baseline *and* mis-attributes (or false-flags) every region-mode move. Affects `sidequest-server/sidequest/agents/dispatch_engagement_watcher.py`. *Found by Architect during design.* See Architect Technical Note below for resolution options.
- **Improvement** (non-blocking): `witnessed_act` witness is clean and implementable exactly as specced — see technical note. No blockers there.

### Dev (implementation)
- **Gap** (RESOLVED in 59-30 per Keith's final ruling — normalization paired with the witness): the live movement-witness identity bridge was unbacked — `per_player[].player_id` is purely LLM-emitted (`intent_router.decompose` → `model_validate`; the router system prompt never constrains it; it is unconsumed on the live bank path). Without normalization the movement witness cry-wolfs a `dispatch_engagement.movement` mismatch on every legitimately-relocated live move. **Keith ruled PAIR THEM — normalization ships IN 59-30.** Closed by `intent_router_pass.py::_normalize_per_player_ids` (after `decompose`, before `run_dispatch_bank`): reverse-resolves the submitting seat id from the already-present `player_name` via `snapshot.player_seats` (zero new param, zero call-site ripple) and overwrites the single-submitter `per_player[].player_id`. Pinned by TEA's 2 RED tests (`test_live_path_overwrites_llm_player_id_with_submitting_seat`, `test_live_path_normalized_player_id_resolves_movement_witness_bridge`). Affects `sidequest-server/sidequest/server/intent_router_pass.py`. *Found by Dev during implementation; resolved in-story.*
- **Question** (non-blocking, forward to 59-31): 59-31 (opponent-yield) reuses the `_iter_all_dispatches` `(player_id, dispatch)` thread + the uniform 3-arg witness signature this story introduced. Any opponent-yield witness that is per-PC (not global) will need the same `player_seats` resolution + the deferred normalization to avoid the identical cry-wolf — so 59-31 is the natural home for the normalization above. Affects `sidequest-server/sidequest/agents/dispatch_engagement_watcher.py` (shared infra). *Found by Dev during implementation.*
- **Improvement** (non-blocking): the `_iter_all_dispatches` change touched no existing witness call site in tests (they all use the public `run_dispatch_engagement_watcher` / `detect_dispatch_engagement_mismatch` API), so the uniform-signature migration was zero-ripple to the existing 24-test watcher suite. *Found by Dev during implementation.*

## Architect CRY-WOLF RULING (player_id normalization — answers Dev's identity-bridge VERIFY)

Dev's finding is correct and decisive: on the live path `per_player[].player_id` is **purely LLM-emitted** (`intent_router.decompose` → `DispatchPackage.model_validate(tool_input)`; prompt says "single player action"; nothing normalizes it; it is currently **unconsumed** on the live bank path). Ruling on the two questions:

**Defer-safety → ACTIVELY MISLEADING, not inert.** With TEA's encoded predicate (`test_movement_player_id_without_seat_returns_evidence` = loud), an unresolvable LLM player_id makes the witness fire a `dispatch_engagement.movement` mismatch on **legit, actually-relocated** moves (step 2: `player_seats.get(<llm-garbage>)` → None → evidence). That is cry-wolf on every/flaky-some live move — strictly worse than no witness, and it directly poisons "the GM panel is the lie detector." **Deferring normalization is NOT safe.** The movement witness and player_id normalization must ship **together** in 59-30, or the movement witness waits for 59-31 and 59-30 ships witnessed_act alone. Do not merge a detector that cries wolf until 59-31.

**Blast radius of the fix → near one-liner, ~nil ripple.** Normalize at the `intent_router_pass.py` construction site (right after `decompose` returns, before/at `run_dispatch_bank`): overwrite the per_player entry's `player_id` with the **submitting seat id** (the key `player_seats` is keyed by, ADR-119). Verified low-ripple:
- `pd.player_id` is unconsumed on the live bank/orchestrator path (Dev's finding) — nothing downstream breaks.
- `prompt_redaction.py` treats `player_id` as a **passthrough** field (`for pd in pkg.per_player` → rebuilds `PlayerDispatch` via `model_copy`, preserving the field; never branches on its value) — normalizing earlier flows through cleanly.
- The live package is **single-submitter per pass** (decompose = "single player action"), so it's literally one assignment, not a multi-entry seat-mapping problem.
The one invariant Dev must honor: the stamped id must equal a `player_seats` key, so the witness's `player_seats.get(player_id)` → character name resolves (the ledger keys `pc_name` on character name).

**Net recommendation:** include player_id normalization in 59-30 (it's cheap and removes the cry-wolf). Keep TEA's loud-evidence-on-unresolvable test — after normalization the live path never trips it, so it correctly guards only a *true* future plumbing break (fail-loud, No Silent Fallbacks). **Optional hardening (not required, would churn TEA's test):** category-separate "couldn't attribute" (plumbing defect) from "engine didn't engage" (the lie) by emitting a distinct `movement.unattributable` span instead of the mismatch channel — defer unless Keith wants the extra insurance. Witnessed_act is entirely unaffected (global dials, no attribution).

## Architect Technical Note (design guidance — White Queen)

### witnessed_act — PROCEED as designed (no design change needed)
The political engine already emits the exact post-turn provenance the witness needs: `apply_witnessed_act` appends a `BeliefLedgerEntry` to `snapshot.political_state.ledger` for **every** dial it moves, each entry stamped with `turn` and `act_id` (`sidequest/game/political_state.py:37`, `sidequest/game/political_engine.py:81-93`). Witness recipe (snapshot-only, no baseline):
- Required param: `act_id` (subsystem also accepts `act_archetype` as a fallback alias — mirror that, or normalize on `act_id` and note it). Missing → `_MALFORMED_EVIDENCE` (match existing pattern).
- `state = snapshot.political_state`; if `None` → evidence string (dispatched but world has no political layer — mirror magic_working's "snapshot.magic_state is None").
- Current turn = `snapshot.turn_manager.interaction` (same source the subsystem uses at `witnessed_act.py:147`).
- **Engaged iff** `any(e.turn == current_turn and e.act_id == act_id for e in state.ledger)`. Keying on **both** turn and act_id avoids attributing a *different* act's dial move to this dispatch.
- Register `"witnessed_act": "act_id"` in `_DISPATCHED_TYPE_KEY` too.
- **Semantic note for TEA:** the subsystem legitimately returns `no_effect` / `no_witness` (act matched no premise/bloc here, or no witness present) — in those cases no ledger entry is written, so the witness will flag a mismatch. Per AC ("flags mismatch when witnessed_act dispatched but no political-state dial moved") this is **intended** — the witness cannot and need not distinguish "engine ran but legitimately moved nothing" from "engine never engaged"; both are "no dial moved," which is the signal the GM panel wants. Test the positive (ledger entry this turn → None) and negative (empty/other-turn ledger → evidence) cases.

### movement — NEEDS A DECISION before TEA writes tests
The blockers above mean the specced approach can't ship as-is. Two resolution paths:

- **Option A (recommended, scoped-to-2pts): descope movement to a follow-up.** Ship the `witnessed_act` witness now (it *is* the epic-59 political-spine driver; movement is called out in the story as a *pre-existing, independent* gap). Split a follow-up story for the movement witness that also does the small refactor it requires: thread `player_id` through `_iter_all_dispatches` (yield `(player_id, dispatch)`) and give movement a turn-stamped provenance signal. 59-31 (opponent-yield) may need the same player-attribution thread, so doing it once, deliberately, is cleaner than bolting it on here.
- **Option B (in-scope, larger): add movement provenance + extend the witness contract.** Mirror the political ledger: have `run_movement_dispatch` stamp a turn-keyed movement-resolution marker on the snapshot on **all** engaged paths — the patch path, the surface-descent path, **and** the `region_mode_deferred` path (else region-mode worlds false-flag). Witness then checks "movement-resolution stamp exists for current turn." This crosses into engine + snapshot-model scope and the witness-signature change — realistically more than the 2 points budgeted.

**My recommendation: Option A.** It keeps the 2-point boundary honest, ships the clean political-spine witness that the epic actually wants, and routes the movement work (which carries a witness-signature refactor 59-31 likely shares) to where it can be done properly. Deferring to SM/Keith on the descope call. TEA: defer to this on test scope — only write witnessed_act tests if Option A is chosen.

## Architect Ruling (TEA blocking questions — White Queen)

**witnessed_act turn-scoping → YES, turn-scope it.** Dispatch does NOT carry `turn`; the snapshot exposes current turn via `snapshot.turn_manager.interaction` (this is the exact source `witnessed_act.py:147` uses to stamp `BeliefLedgerEntry.turn`). So the witness reads current turn off the snapshot, not the dispatch. Check: `any(e.turn == current_turn and e.act_id == act_id for e in state.ledger)`. Turn-scoping is **required**, not optional — without it a prior-turn ledger entry for the same act_id produces TEA's false-negative (witness says "engaged" on a turn the dial didn't actually move). Confirmed clean and in-scope.

**movement (a)/(b)/(c) → choose (a), but as a descoped follow-up (NOT in 59-30 as a 2pt witness-add).**
- **(a) movement ledger — CORRECT end-state.** Mirrors the political-ledger pattern, makes the witness a pure *turn-scoped* post-snapshot read (`any(e.turn == current_turn for e in movement_ledger)`) — which **sidesteps the missing player_id** exactly the way witnessed_act does, and yields a durable GM-panel artifact (the OTEL doctrine wants this). The catch that makes it >2pts: the stamp must fire on **all three engaged branches** of `run_movement_dispatch` — the `pc_region` patch path, the surface-descent path, AND the `region_mode_deferred` path (in oz/wonderland/gulliver the subsystem *correctly* engages by deferring; if the ledger only stamps on patch paths, every region-mode move false-flags). That's a multi-branch write-path change + a snapshot-model field — real scope beyond a witness-add.
- **(b) enrich params — REJECT.** `from_region` would have to be engine-populated post-resolution (the router doesn't know the PC's real region), and post-turn `region_for` comparison still false-flags region-mode worlds (no patch applied, change lands via narration_apply with different timing). Fragile, and it's just a worse (a).
- **(c) change witness signature — REJECT.** Largest blast radius (touches `_iter_all_dispatches`, the call site, every existing witness signature, and requires capturing a pre-turn snapshot baseline in the turn pipeline) for the least benefit. Not warranted.

**Scope ruling:** witnessed_act ships in 59-30 (turn-scoped, clean). Movement → option (a) in a **separate follow-up story** that owns the movement write-path + snapshot-model change. If SM/Keith would rather keep movement in 59-30, the story must be re-pointed (≥3–5) and re-AC'd to include the engine work — it is not a pure witness-add. The witness-signature/player-attribution concern that 59-31 may share is also better resolved in that follow-up, deliberately.

## Architect Technical Note — MOVEMENT WITNESS CONTRACT (Option B, in-scope per Keith)

Concrete design for TEA RED. witnessed_act stays as already specced (turn-scoped ledger check, `snapshot.turn_manager.interaction`). Movement contract below. All file refs verified 2026-06-04.

### 1. Iterator + witness signature change
`_iter_all_dispatches` (dispatch_engagement_watcher.py:196) loses the owning player today — it yields a bare `SubsystemDispatch`. Change it to yield `tuple[str | None, SubsystemDispatch]`:
- `per_player`: `yield (pd.player_id, d)` for each `d in pd.dispatch`
- `cross_player`: `yield (None, d)` (cross-actions have `participants`, not one owner; movement is never cross-dispatched — a `None`-owner movement dispatch is a router defect the witness surfaces, see §3)

Make the witness signature **uniform** across all witnesses: `_check_<x>_engaged(dispatch: SubsystemDispatch, snapshot: GameSnapshot, player_id: str | None) -> str | None`. The six existing witnesses gain an unused `player_id` param (mechanical, no behavior change). `detect_dispatch_engagement_mismatch` (line 228 loop) unpacks `for player_id, dispatch in _iter_all_dispatches(package)` and passes `player_id` to `check(...)`. This player-attribution thread is shared infra **59-31 (opponent-yield) will reuse** — build it here, don't re-do it there.

### 2. Movement provenance record (the turn-stamped artifact the witness reads)
No existing per-PC, turn-stamped relocation record exists (`pc_regions` is current-only; `discovered_regions` is an untimed set). Add one, mirroring `BeliefLedgerEntry`:

```python
class RegionTransition(BaseModel):   # new, e.g. in game/region_transition.py or session.py
    turn: int
    pc_name: str          # the CHARACTER-NAME key used by pc_regions (NOT player_id) — see §3
    from_region: str | None
    to_region: str
    via: str              # "world_patch" | "narration_apply"
```
Home it on `GameSnapshot`: `region_transitions: list[RegionTransition] = Field(default_factory=list)`. It persists like the political ledger (durable GM-panel/forensics artifact, consistent with ADR-124).

**Stamp sites — BOTH required (there is NO single choke point; region-mode bypasses apply_world_patch):**
- **Site A — `session.py::_apply_world_patch_inner`**, inside `if patch.pc_region is not None:`, in the existing genuine-change block `if to_region and to_region != prev:` (right beside `notify_region_transition`). `via="world_patch"`, `turn=self.turn_manager.interaction`, `pc_name=pc_name`. **This automatically covers movement.py's TWO procedural relocation paths** (the surface-descent entrance-bind at movement.py:243 and the normal resolve at movement.py:367 — both route through `apply_world_patch(WorldStatePatch(pc_region=...))`).
- **Site B — `narration_apply.py:~2653`**, the region-mode block `if _is_region_mode_world and snapshot.current_region != known_region_id:`, immediately after `snapshot.pc_regions[player_name] = known_region_id` (line 2654). `via="narration_apply"`, `turn=snapshot.turn_manager.interaction`, `pc_name=player_name`, `from_region=_prior_region`, `to_region=known_region_id`. **This is mandatory** — oz/wonderland/gulliver relocate here, NOT through apply_world_patch; without Site B the witness false-negatives on every region-mode move (the `region_mode_deferred` return at movement.py:161 applies no patch by design). Verified: narration_apply runs inside `_apply_narration_result_to_snapshot` (handler:968), which executes BEFORE `run_dispatch_engagement_watcher` (handler:974), so the stamp is visible to the witness this turn.

### 3. Witness predicate (`_check_movement_engaged`)
Required dispatch param for `_DISPATCHED_TYPE_KEY`: register `"movement": "direction"`.
```
1. Resolve the moving PC's character name from player_id:
   - if player_id is None  → return evidence: "movement dispatched with no owning player (cross_player movement is a router defect)"
   - pc_name = snapshot.player_seats.get(player_id)
       (player_seats: dict[player_id -> character_name]; pc_regions/region_transitions key on character_name)
   - if pc_name is None     → return evidence: f"movement player_id={player_id!r} has no seat→character mapping (player_seats={...})"
2. current_turn = snapshot.turn_manager.interaction
3. ENGAGED iff any(t.turn == current_turn and t.pc_name == pc_name for t in snapshot.region_transitions)  → return None
4. else return evidence: f"no region_transition for pc={pc_name!r} at turn={current_turn} (router dispatched movement; PC did not relocate)"
```
This is Philosophy "relocation-occurred": it catches the true lie-detector target ("dispatched movement, PC didn't relocate") on EVERY world type — procedural _unresolved paths (no patch → no stamp → flag) AND region-mode where narration_apply failed to match a known region (no stamp → flag). Per-PC keying keeps MP/split-party correct (PC-A's stuck move isn't masked by PC-B's successful move same turn).

### 4. Scope / risk flags
- **[VERIFY — the one thing Dev must nail] player_id ↔ character-name identity.** `PlayerDispatch.player_id` is built only by router-output deserialization (no in-tree constructor; some sites set `player_id=""`). The relocation writers key pc_regions by `player_name` (= character name, confirmed via `region_for(perspective=...)` semantics, session.py:1160). The `player_seats` bridge (§3 step 1) is the intended resolver. **Dev must confirm at the router-output construction site that `player_id` is the seat id that `player_seats` is keyed by.** If single-player sets `player_id=""` and `player_seats` is empty, step-1 returns evidence (loud) rather than silently guessing — that is the correct No-Silent-Fallback behavior; do NOT add an `or player_id` / "single seated PC" fallback. If Dev finds player_id already equals the character name on the live path, the `player_seats.get` still works iff seats map id→name; otherwise key the ledger and lookup on whatever single identifier the writer uses — the invariant is **witness lookup identifier == relocation write identifier.**
- **Scope (confirms >2pts, accepted):** touches (1) new `RegionTransition` model + `GameSnapshot.region_transitions` field, (2) Site A stamp in session.py, (3) Site B stamp in narration_apply.py, (4) `_iter_all_dispatches` tuple change, (5) uniform 3-arg signature on all 6 existing witnesses, (6) new `_check_movement_engaged`, (7) `_DISPATCHED_TYPE_KEY["movement"]`. Re-point the story accordingly.
- **59-31 overlap:** items (4) + (5) are the player-attribution refactor 59-31 likely needs; this story owns it.
- **Uncertain-emits flag:** I verified the two relocation seams above are the only per-PC region writes on the movement/region-mode paths I traced. If a *future* region-mode travel path is added that bypasses both seams, the witness will false-negative — note for whoever adds it. Do NOT stamp the `current_region` party-anchor branch (session.py, seed/teleport) — that is a party-level spawn anchor, not a per-PC movement engagement; stamping it would pollute the ledger.

### TEA test pair (movement) — no guessing required
- **Positive (engaged → None):** snapshot with `player_seats={"p1": "Rux"}`, `turn_manager.interaction=7`, `region_transitions=[RegionTransition(turn=7, pc_name="Rux", from_region="a", to_region="b", via="world_patch")]`; package with one `per_player=[PlayerDispatch(player_id="p1", dispatch=[SubsystemDispatch(subsystem="movement", params={"direction":"deeper"})])]`. Assert `_check_movement_engaged` (and `detect_dispatch_engagement_mismatch`) returns None / no mismatch.
- **Negative (dispatched, not engaged → evidence):** same package, but `region_transitions=[]` (or only a transition at turn=6, or only for a different pc_name). Assert one `DispatchMismatch(subsystem="movement", ...)` with evidence naming `pc='Rux'` and `turn=7`.
- **Region-mode integration (wiring test):** drive a region-mode relocation through Site B (`narration_apply` heading→known region) then run the watcher with a movement dispatch for that PC and assert NO mismatch — proves Site B stamps and the witness reads it (the false-negative this design exists to prevent).

## Architect FINALIZATION (Option B confirmed in-scope) — answers to SM's 3 questions

Option B is the target. The contract above stands; these are the three pin-down answers, with one correction to the stamp-site framing.

### Q1 — Ledger entry model + snapshot home (FINAL)
- **Model:** `RegionTransition` (pydantic BaseModel). Fields: `turn: int`, `pc_name: str` (the **character-name** key — same identifier `pc_regions` uses, via `region_for(perspective=...)`; NOT the raw player_id), `from_region: str | None`, `to_region: str`, `via: str` (`"world_patch"` | `"narration_apply"`).
- **Home:** directly on `GameSnapshot` → `region_transitions: list[RegionTransition] = Field(default_factory=list)`. **Do NOT** wrap it in a `movement_state`/`region_state` container. Rationale: `political_state.ledger` is nested because `PoliticalState` is **world-conditional** (None when a world authors no political layer). Region transitions are **universal** — every world has movement — so a sub-state container buys nothing but None-handling. Flat list on the snapshot is the right parallel.

### Q2 — Stamp sites (CORRECTION: it's TWO sites, and one is NOT in run_movement_dispatch)
The "three branches in run_movement_dispatch" framing will produce a false-negative if taken literally. There are **two** stamp sites, because only two of movement's branches actually relocate, and the region-mode relocation happens **outside** run_movement_dispatch:
- **Site A — `session.py::_apply_world_patch_inner`**, the `pc_region` genuine-change block (`if to_region and to_region != prev:`). This is the shared choke point for **both** procedural relocations — the surface-descent entrance-bind (`movement.py:243`) and the normal resolve (`movement.py:367`) — they both call `apply_world_patch(WorldStatePatch(pc_region=...))`, so a single stamp here covers both. `via="world_patch"`.
- **Site B — `narration_apply.py:~2654`**, region-mode block, right after `snapshot.pc_regions[player_name] = known_region_id`. `via="narration_apply"`.
- **The `region_mode_deferred` branch (`movement.py:161`) is NOT a stamp site.** It applies no patch and performs no relocation — it hands off to narration_apply (Site B). Stamping there would record "engaged" even when narration_apply subsequently fails to relocate, which is the exact false-negative we're avoiding. Leave it unstamped; Site B stamps iff a real region change occurs.

**Semantic to preserve (do not "fix"):** the witness measures the **relocation outcome**, not "did the subsystem do its job." A movement that legitimately resolves to no relocation (procedural `_unresolved`, or region-mode where the narrator heading matched no known region) → no stamp → witness flags a mismatch. That is correct per the AC ("router dispatched movement but PC region doesn't relocate") and mirrors the witnessed_act no-effect semantic. It is GM-panel signal, not a bug.

### Q3 — Is the iterator player_id change avoidable? (Direct answer: NO, not without an MP correctness hole)
The turn-scoped read sidesteps attribution for witnessed_act **only because political dials are global** — `act_id + turn` is a complete identity. Movement is **per-PC**, and the cheap shortcut (`any(e.turn == current_turn for e in region_transitions)`, no player) breaks in MP:
- **Single-player:** one PC, one possible mover → turn-only is correct, iterator change unneeded.
- **MP / split-party:** under ADR-036 submit-and-wait, multiple PCs' actions resolve under the **same interaction turn**. If PC-A is dispatched movement and gets stuck while co-located PC-B relocates the same turn, a turn-only check sees B's transition and reports A "engaged" → **false-negative that masks A's stuck move** — precisely the MP case the watcher exists to catch (it already traverses `cross_player` for this reason; coyote_star MP is the live driver).

The dispatch carries no actor in `params` and the resolved `to_region` isn't in `params` either, so there is **no alternative match key** — owning identity is only on `PlayerDispatch.player_id`. Hence the iterator must yield `(player_id, dispatch)` and the witness must resolve `player_id → pc_name` via `player_seats` to key the ledger read per-PC.

**My recommendation: KEEP the iterator + uniform-signature change.** The saving from dropping it is small (one tuple + 6 trivial unused-arg edits) and 59-31 needs the same thread anyway; dropping it bakes in a latent MP false-negative that's invisible until it bites. **If** Keith wants to consciously scope v1 to single-player movement-witness correctness (accepting the MP hole, documented), the iterator change can be deferred and the witness becomes turn-only like witnessed_act — that's the only way to shrink blast radius, and it's a product call, not a free win. Absent that explicit decision, build the per-PC version. Either way, witnessed_act is unaffected (global dials, no attribution).

**Net for TEA:** proceed to RED on both witnesses. witnessed_act = turn+act_id ledger check (no attribution). movement = per-PC region_transitions check with the `player_seats` bridge, two stamp sites (A: apply_world_patch, B: narration_apply), iterator yields (player_id, dispatch). Test triplet (positive / negative / region-mode wiring) is in the contract note above.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Enforce engine/witness param-parity for the `act_archetype` alias**
  - Spec source: Architect Technical Note (session file), witnessed_act recipe — "Required param: act_id (subsystem also accepts act_archetype as a fallback alias — mirror that, or normalize on act_id and note it)."
  - Spec text: "mirror that, or normalize on act_id and note it" (Dev's choice offered)
  - Implementation: Tests REQUIRE the witness to mirror the alias (`test_witnessed_act_act_archetype_alias_engaged_returns_none`), removing the "normalize on act_id-only" option.
  - Rationale: The engine accepts `act_archetype` and stamps the ledger under the resolved id; an act_id-only witness would emit a false mismatch span on a turn the engine legitimately engaged — a lie-detector false-positive, the opposite of the watcher's purpose.
  - Severity: minor
  - Forward impact: Dev must resolve `act_id = params.get("act_id") or params.get("act_archetype")` in the witness (one line), matching `witnessed_act.py:102`.
- **RegionTransition import home asserted loosely (dual-path shim)**
  - Spec source: Architect Technical Note §2 / FINALIZATION Q1 — "new, e.g. in game/region_transition.py or session.py"; field homed on `GameSnapshot`.
  - Spec text: model file location left as "e.g." (open)
  - Implementation: Tests import `RegionTransition` via a try/except shim (`sidequest.game.session` preferred, `sidequest.game.region_transition` fallback) instead of pinning one path.
  - Rationale: The Architect pinned the field home but not the model's module; a hard single-path import would over-constrain Dev or break on a reasonable placement. Both paths fail RED today (model absent), so the RED signal is preserved.
  - Severity: trivial
  - Forward impact: Dev should ensure `RegionTransition` is importable from one of the two paths (re-export from `session` if defined elsewhere).

### Dev (implementation)
- **player_id normalization: scope churned (in → reverted → re-applied), final = IN 59-30 per Keith's ruling**
  - Spec source: `.session/59-30-session.md` → "Architect CRY-WOLF RULING"; SM dispatches; Keith's final ruling.
  - Spec text: Architect ruling "include player_id normalization in 59-30"; an interim SM message "do NOT pull it in unprompted"; Keith's final ruling "PAIR THEM — normalization IS in-scope for 59-30."
  - Implementation: I first added `_normalize_per_player_ids` (reading the session-file ruling as authoritative), then **reverted** it on the SM's interim scope instruction, then **re-applied** the production code (recovered from reflog `86c2b6b5`) once Keith's final ruling landed and TEA's 2 RED normalization tests committed. Final state: `intent_router_pass.py::_normalize_per_player_ids` is IN; my own duplicate test was NOT re-added (TEA's `tests/server/test_59_30_player_id_normalization.py` is canonical and covers both the overwrite + the e2e bridge-resolution payoff).
  - Rationale: Scope is the SM/Keith's call; I followed the final ruling. Re-applied against TEA's RED tests to keep it TDD; avoided duplicating her e2e assertion.
  - Severity: minor
  - Forward impact: the live movement witness now resolves on the live path (no cry-wolf). The `_iter_all_dispatches` `(player_id, dispatch)` thread + uniform witness signature + this normalization pattern are the shared infra 59-31 reuses.
  - Commit note: because the peloton shares one working tree, HEAD was TEA's RED-test commit (`b813a7cf`) when I ran `git commit --amend` to add the normalization — so my production change folded INTO that commit (final `1b8edee6`, parent = the witness commit `4010f939`). TEA's 250-line test is fully preserved; nothing lost; remote updated as a clean fast-forward. Flagged to SM.
- **Touched `telemetry/spans/dispatch_engagement.py` (not named in the build list) to register the two new mismatch span names**
  - Spec source: AC — "`_check_*_engaged` added and registered; flags mismatch...". TEA test `test_*_mismatch_reachable_via_public_watcher_path`.
  - Spec text: the witness must emit a `dispatch_engagement.{subsystem}.mismatch` span via the public watcher path.
  - Implementation: Added `SPAN_DISPATCH_ENGAGEMENT_WITNESSED_ACT_MISMATCH` + `_MOVEMENT_MISMATCH` constants, SPAN_ROUTES registration, and `_SUBSYSTEM_TO_SPAN_NAME` entries. Required because `span_name_for_subsystem` is a fail-loud registry (KeyError on unknown subsystem) — the public-path tests KeyError'd without it.
  - Rationale: The span-name registry is the necessary second half of "registered in `_WITNESSES`"; the GM panel filters by these span names (OTEL principle).
  - Severity: trivial
  - Forward impact: none — additive registry entries.

## TEA Assessment

### Red Phase (test writing)

**Tests Required:** Yes
**Reason:** Two new engagement witnesses + a new provenance model/stamp sites — pure behavior additions with clear positive/negative semantics; squarely TDD.

**Test Files:**
- `sidequest-server/tests/agents/test_59_30_witnesses.py` — witnessed_act + movement witness unit/behavior tests, registration + iterator-contract wiring, public-watcher-path reachability spans, MP split-party per-PC correctness, region_mode_deferred-without-relocation guard (22 tests).
- `sidequest-server/tests/server/test_59_30_region_transition_stamp.py` — RegionTransition Site A (`apply_world_patch`) + Site B (`narration_apply` region-mode) stamp wiring + current_region anchor non-stamp guard (6 tests).
- `sidequest-server/tests/server/test_59_30_player_id_normalization.py` — live-path `player_id` normalization at `intent_router_pass` (post-decompose / pre-bank): per_player[].player_id overwritten with the submitting seat id (a `player_seats` key), so the movement witness bridge resolves on the live path (2 tests). Added per Keith's ruling pairing normalization into 59-30.

**Tests Written:** 30 tests covering all 4 ACs + the live-path normalization + the contract's full surface.
**Status:** RED at authoring time — first 28 verified 28-failed/0-passed; the 2 normalization tests verified 2-failed (LLM player_id passes through verbatim, no normalization yet). NOTE: the White Rabbit shipped GREEN for the witnesses+RegionTransition concurrently (`4010f939`), so re-running the full set now shows 28 passed / 2 failed — the 2 reds are the still-unimplemented normalization. All failures verified for the right reason throughout. (verified `uv run pytest ... -p no:randomly`). All failures are for the right reason: `_check_witnessed_act_engaged`/`_check_movement_engaged` ImportError, `RegionTransition` absent (both import paths), `_WITNESSES` len 6≠8 + missing keys, `_DISPATCHED_TYPE_KEY` missing keys, `_iter_all_dispatches` yields bare `SubsystemDispatch` not `(player_id, dispatch)`. Ruff clean. Existing watcher suite (`test_dispatch_engagement_watcher.py`) still 24/24 green — public API unchanged.

### AC Coverage

| AC | Test(s) | Status |
|----|---------|--------|
| `_check_witnessed_act_engaged` added + registered; flags mismatch when dispatched but no dial moved | `test_witnessed_act_engaged_with_ledger_entry_this_turn_returns_none`, `test_witnessed_act_dispatched_with_empty_ledger_returns_evidence`, `test_witnessed_act_prior_turn_ledger_entry_reads_not_engaged`, `test_witnessed_act_different_act_same_turn_reads_not_engaged`, `test_witnessed_act_no_political_state_returns_evidence`, `test_witnessed_act_mismatch_reachable_via_public_watcher_path`, `test_both_witnesses_registered_in_witnesses_dict` | RED |
| `_check_movement_engaged` added + registered; flags mismatch when dispatched but no relocation | `test_movement_engaged_with_region_transition_this_turn_returns_none`, `test_movement_no_region_transition_returns_evidence_naming_pc_and_turn`, `test_movement_prior_turn_transition_reads_not_engaged`, `test_movement_transition_for_different_pc_reads_not_engaged`, `test_movement_none_player_id_returns_evidence`, `test_movement_player_id_without_seat_returns_evidence`, `test_movement_mismatch_reachable_via_public_watcher_path` | RED |
| Stale "all six live-path subsystems" docstring corrected to actual count | `test_witnesses_count_is_eight_and_docstring_not_stale` | RED |
| Positive + negative watcher unit test per new witness | both witnesses have positive (engaged→None/no span) + negative (dispatched-not-engaged→evidence/span) pairs above | RED |

### Rule / Contract Coverage

| Rule / Contract point | Test(s) | Status |
|------|---------|--------|
| Every Test Suite Needs a Wiring Test | `test_*_registered_in_*`, `test_*_reachable_via_public_watcher_path`, `test_iter_all_dispatches_yields_player_id_dispatch_tuples` | RED |
| No Source-Text Wiring Tests | registry/reflection assertions (`_WITNESSES`, `__doc__`), fixture-driven stamp tests — no source-grep | RED |
| No Silent Fallbacks (malformed → loud span, no crash) | `test_witnessed_act_malformed_missing_act_id_surfaces_evidence_not_crash` | RED |
| No Silent Fallbacks (unresolvable player_id → loud evidence, no guess) | `test_movement_player_id_without_seat_returns_evidence`, `test_movement_none_player_id_returns_evidence` | RED |
| OTEL: every mismatch emits a span; every engaged path emits zero | reachability + `test_witnessed_act_engaged_emits_no_span_via_public_path` (vacuity-guarded by registration precondition) | RED |
| Turn-scoping (the false-negative TEA caught) | `test_witnessed_act_prior_turn_ledger_entry_reads_not_engaged`, `test_movement_prior_turn_transition_reads_not_engaged` | RED |
| Region-mode false-negative guard (via-agnostic witness + Site B stamp) | `test_movement_reads_narration_apply_via_stamp_engaged_returns_none`, `test_region_mode_location_change_stamps_region_transition` | RED |
| current_region anchor must NOT pollute the ledger | `test_current_region_party_anchor_patch_does_not_stamp` | RED |

**Self-check:** 1 vacuous pass found and fixed — `test_witnessed_act_engaged_emits_no_span_via_public_path` initially passed trivially (unregistered witness also emits no span); added a `"witnessed_act" in _WITNESSES` registration precondition so it fails RED for the right reason and is non-vacuous in GREEN. No `let _ =`/`assert True`/always-None assertions remain.

**Commit:** `feat/59-30-witnesses-engagement-witness` @ sidequest-server — "test: add failing tests for 59-30 (witnessed_act + movement engagement witnesses)".

**Handoff:** To Dev (The White Rabbit) for GREEN implementation.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed (sidequest-server):**
- `sidequest/game/session.py` — new `RegionTransition` pydantic model; `GameSnapshot.region_transitions` field; Site A stamp in `_apply_world_patch_inner` pc_region genuine-change block (`via="world_patch"`).
- `sidequest/server/narration_apply.py` — Site B stamp in the region-mode advance block (`via="narration_apply"`); import of `RegionTransition`.
- `sidequest/agents/dispatch_engagement_watcher.py` — `_iter_all_dispatches` now yields `(player_id, dispatch)`; uniform 3-arg witness signature (6 existing witnesses gain an unused `player_id`); new `_check_witnessed_act_engaged` (turn+act_id ledger read, act_archetype alias parity) + `_check_movement_engaged` (per-PC turn-scoped region_transitions read via `player_seats` bridge, fail-loud on unresolvable id); registered both in `_WITNESSES` (→8) and `_DISPATCHED_TYPE_KEY`; corrected the stale "all six" docstring.
- `sidequest/telemetry/spans/dispatch_engagement.py` — registered `witnessed_act` + `movement` mismatch span names (constants, SPAN_ROUTES, `_SUBSYSTEM_TO_SPAN_NAME`, `__all__`) so the fail-loud span registry resolves them.
- `sidequest/server/session_helpers.py` — categorized `region_transitions` into `_PHASE_B_DROP_FIELDS` (ADR-110 governance gate; narrator doesn't need the relocation ledger).

- `sidequest/server/intent_router_pass.py` — `_normalize_per_player_ids` (Keith's PAIR-THEM ruling): after `decompose`, before `run_dispatch_bank`, overwrites the single-submitter `per_player[].player_id` with the real submitting seat id (reverse-resolved from `player_name` via `snapshot.player_seats` — zero new param, zero call-site ripple). The live movement witness now resolves instead of crying wolf.

**Tests:** All 28 TEA RED witness/stamp tests + TEA's 2 RED normalization tests + ADR-110 governance test → GREEN (**30 story tests + governance**). Regression set 142/142 via testing-runner (watcher, dispatch precondition/unregistered gates, 59-4 router-wiring, region-advance, pc_regions, intent_router unit/wiring/vocabulary/verbal-social/witnessed-act-classified). Full suite: **20 failed / 8885 passed / 72 errors** — the 20 failures + 72 errors are **identical to the pre-existing clean-tree baseline** (DB/embedding/reference-page env failures; verified the full FAILED list contains ZERO 59-30/intent_router/dispatch/region/watcher tests). **Zero new failures.** Ruff check + format clean.

**Identity-bridge [VERIFY] resolution:** `per_player[].player_id` is purely LLM-emitted and was unconsumed on the live path — surfaced as a blocking Delivery Finding (NOT papered over). Per Keith's final ruling the normalization is PAIRED into 59-30: the live path now overwrites `player_id` with the submitting seat id so the movement witness resolves live. TEA's loud-evidence-on-unresolvable test (`test_movement_player_id_without_seat_returns_evidence`) stays as-is — it now guards only a true future plumbing break.

**Branch:** `feat/59-30-witnesses-engagement-witness` (sidequest-server) — pushed, HEAD `1b8edee6`.

**Handoff:** To review (The Queen of Hearts).

## Subagent Results

Note: only 4 reviewer subagents are enabled in `workflow.reviewer_subagents`
(preflight, test_analyzer, comment_analyzer, rule_checker); the rest are disabled
by settings. No Task-spawn tool is available in this environment, so the Queen
ran the disabled domains (edge, silent-failure, type-design, security, simplifier)
herself against the live code — every focus area in the dispatch brief was covered
by direct verification, not delegation.

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes (run by Queen) | clean | story 30/30 GREEN, watcher 27/27, region-advance + governance GREEN, ruff clean | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | covered by Queen | confirmed 0, dismissed 0 |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | covered by Queen | confirmed 1 (non-blocking: unwrapped watcher — pre-existing), dismissed 0 |
| 4 | reviewer-test-analyzer | Yes (run by Queen) | clean | MP/turn-scope/region-mode guards genuine; no vacuous asserts (TEA's own vacuity-guard at L331) | confirmed 0, dismissed 0 |
| 5 | reviewer-comment-analyzer | Yes (run by Queen) | clean | docstrings accurate, stale "six" corrected, file refs verified | confirmed 0, dismissed 0 |
| 6 | reviewer-type-design | Skipped | disabled | covered by Queen | confirmed 1 (MINOR: `via: str` stringly-typed) |
| 7 | reviewer-security | Skipped | disabled | covered by Queen | confirmed 0 (no auth/injection surface; identity bridge fail-loud) |
| 8 | reviewer-simplifier | Skipped | disabled | covered by Queen | confirmed 0 |
| 9 | reviewer-rule-checker | Yes (run by Queen) | clean | No Silent Fallbacks honored; wiring test present + behavior-based (not source-grep); OTEL spans added | confirmed 0, dismissed 0 |

**All received:** Yes (4 enabled run, 5 disabled domains covered directly)
**Total findings:** 0 confirmed blocking, 3 confirmed non-blocking (1 MINOR type, 2 NIT/observation), 0 dismissed

### Reviewer (audit)
- All TEA + Dev deviations reviewed; stamps below. No undocumented spec deviations found — the two-site stamp design, the `region_mode_deferred` non-stamp, and the alias parity all match the Architect contract verbatim against live code.

### TEA (test design) — Reviewer stamps
- **Enforce engine/witness param-parity for the `act_archetype` alias** → ✓ ACCEPTED by Reviewer: witness L? resolves `params.get("act_id") or params.get("act_archetype")`, byte-identical to `witnessed_act.py:102` and `political_engine.py` stamp. Verified live.
- **RegionTransition import home asserted loosely (dual-path shim)** → ✓ ACCEPTED by Reviewer: model homed in `session.py`; the shim's preferred path resolves. Sound.

### Dev (implementation) — Reviewer stamps
- **player_id normalization scope churn (final = IN 59-30)** → ✓ ACCEPTED by Reviewer: matches Keith's PAIR-THEM ruling and the Architect CRY-WOLF ruling. The fix is a true near-one-liner with verified nil ripple (redaction passthrough confirmed, bank uses context `player_name` not `pd.player_id`, witness reads the normalized package off `turn_context.dispatch_package`). No Silent Fallback: unresolvable seat leaves the LLM id untouched and the witness fires loud — correct.
- **Touched `telemetry/spans/dispatch_engagement.py` (not in build list)** → ✓ ACCEPTED by Reviewer: mandatory — `span_name_for_subsystem` is a fail-loud registry; without registration the public-path KeyErrors. Additive, pattern-consistent with the existing six.
- **Commit folded into TEA's RED commit via amend** → ✓ ACCEPTED by Reviewer: TEA's 250-line test file is fully present in the tree (verified); RED→GREEN history is legible across the three story commits (`fec9e565`→`4010f939`→`1b8edee6`). No loss.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** live player action → `websocket_session_handler` resolves
`_acting_player_name = player_seats.get(sd.player_id) or sd.player_id` (character
name when seated) → `execute_intent_router_pre_narrator_pass(player_name=...)` →
`decompose` returns package with LLM-emitted `per_player[].player_id` →
`_normalize_per_player_ids` reverse-resolves the seat id whose `player_seats` value
== `player_name` and overwrites `pd.player_id` (No-Silent-Fallback: leaves it
untouched + fires loud witness if unresolvable) → caller assigns the mutated
package to `turn_context.dispatch_package` (handler:880) → narrator runs →
`_apply_narration_result_to_snapshot` (handler:962) may stamp a `RegionTransition`
at Site A (`apply_world_patch` pc_region genuine-change) or Site B
(`narration_apply` region-mode) → `run_dispatch_engagement_watcher`
(handler:974, same snapshot) reads `turn_context.dispatch_package`, `_iter_all_dispatches`
yields `(player_id, dispatch)`, `_check_movement_engaged` resolves
`player_seats.get(player_id)` → character name → checks
`any(t.turn==interaction and t.pc_name==name for t in region_transitions)`. Bridge
holds because the relocation writers, the normalization target, and the witness
lookup all key on the same character-name identifier. Safe.

**Pattern observed:** `[VERIFIED]` two-site stamp with via-agnostic per-PC witness
at `dispatch_engagement_watcher.py` `_check_movement_engaged` + `session.py`
RegionTransition Site A + `narration_apply.py` Site B — correctly covers procedural
(world_patch) AND region-mode (narration_apply) relocations while deliberately NOT
stamping `region_mode_deferred` (movement.py:161) or the `current_region`
party-anchor (session.py:~1450). Verified all five `pc_regions[` write sites and
classified each: 2 stamped (Sites A/B), `seed_pc_regions` + party-anchor +
migration correctly unstamped (not movement-dispatched).

**Error handling:** `[VERIFIED]` No Silent Fallbacks honored at every seam —
`_normalize_per_player_ids` returns without mutating on unresolvable seat
(`intent_router_pass.py`); movement witness returns LOUD evidence on
`player_id is None` and on `player_seats.get→None`; witnessed_act witness returns
evidence on `political_state is None` and on missing `act_id`/`act_archetype`
(`_MALFORMED_EVIDENCE`). No swallowed errors, no guesses, no single-seat default.

**[EDGE]** No false-negative/false-positive path found. Turn-scoping prevents
prior-turn carryover; per-PC keying prevents MP co-located masking; alias parity
prevents the act_archetype false-positive; via-agnostic read prevents region-mode
false-negative. **[SILENT]** One pre-existing exposure: `run_dispatch_engagement_watcher`
does not wrap witness calls in try/except (handler:974) — but the new witnesses
are defensively written (cannot raise on bad input) and this exposure predates
59-30 (the original 6 witnesses share it). Non-blocking. **[TEST]** MP split-party,
turn-scope, and region-mode-deferred-without-relocation guards are all genuine
behavior tests, not vacuous; stamp tests drive the real seams. **[DOC]** docstrings
accurate; stale "all six" corrected to eight with both new names. **[TYPE]** MINOR:
`RegionTransition.via: str` is stringly-typed (2 valid values) — a `Literal` would
be stronger, but the witness is via-agnostic so correctness is unaffected.
**[SEC]** No auth/injection/secret surface; identity bridge fails loud, no PII leak
(player_seats already in snapshot). **[SIMPLE]** No over-engineering; the flat
`region_transitions` list (vs a sub-state container) is the right call per the
universal-vs-world-conditional rationale. **[RULE]** No Silent Fallbacks, Wiring
Test (behavior-based, not source-grep), and OTEL Observability all satisfied.

**Handoff:** To SM (The Mad Hatter) for finish-story.
