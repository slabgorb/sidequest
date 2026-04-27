---
parent: sprint/epic-45.yaml
workflow: wire-first
---

# Story 45-18: encounter.actors registers all combatants, not just player

## Business Context

**Playtest 3 evidence — Orin's session:** through 6 rounds of combat with
the Crawling Scavenger, `encounter.actors = [Orin only]`. The Scavenger
took damage, dealt damage, and resolved its own beats over those six
rounds, but the actors array never registered it. Per-actor damage and
momentum tracking are impossible when the array contains only the player —
`apply_beat()` falls back to a player-side actor lookup
(`game/beat_kinds.py`), so the Scavenger's beats are recorded against the
wrong side or skipped silently.

**Audience:** Felix and Sebastien both feel this. Felix because his long
combat sessions accumulate the same registration gap and cascade into
broken HP-tracking (sibling story 45-21); Sebastien because the GM panel
shows "encounter active, 1 actor" while the narrator describes a
two-creature fight — exactly the lie-detector miss CLAUDE.md OTEL is
supposed to catch.

This story sits in **Lane A** (MP correctness) and is upstream of
Lane B's NPC-registry write-back chain (45-21). Was 37-41 sub-4;
re-scoped per ADR-085 onto the Python tree. Epic 42 (ADR-082 Phase 3
combat port) closed the structural port; this gap is downstream of that
port and may have been inherited from the original Rust path.

ADRs in play: **ADR-031** (Game Watcher / OTEL on every subsystem
decision); **ADR-014** (Diamonds and Coal — actor registration is the
diamond underneath every per-actor combat fact).

## Technical Guardrails

### Diagnosis (verified 2026-04-27)

`StructuredEncounter.actors` is declared at
`sidequest-server/sidequest/game/encounter.py:151`:

```
actors: list[EncounterActor] = Field(default_factory=list)
```

Actors are written ONLY at instantiation time, in
`server/dispatch/encounter_lifecycle.py:128-143`:

```
else:                                          # non-sealed-letter branch
    role = "combatant" if cdef.category == "combat" else "participant"
    actors = [
        EncounterActor(name=player_name, role=role, side="player"),
    ]
    for npc in npcs_present:
        npc_name = getattr(npc, "name", None) or str(npc)
        side_raw = getattr(npc, "side", None) or "neutral"
        side = _validate_side(npc_name, side_raw)
        actors.append(EncounterActor(name=npc_name, role=role, side=side))
```

This list is then written into the `StructuredEncounter` at
encounter_lifecycle.py:147-165. After instantiation, **no production
site appends to `encounter.actors`** — verified by grep:

```
$ grep -rn "actors\.append\|encounter\.actors" sidequest-server/sidequest/ \
    --include="*.py" | grep -v test
```

returns one append (the line above, at instantiation), and read-only
references at `narration_apply.py:858`, `dispatch/sealed_letter.py:153/233/302/309/314`,
`dispatch/dice.py:313`, `dispatch/confrontation.py:51`. No re-registration
ever fires.

The instantiation site is fed `npcs_present` from the narrator
extraction (`narration_apply.py:422-428`, with the values flowing from
`OrchestratorResult.npcs_present` populated at
`agents/orchestrator.py:1603`). When the narrator emits
`confrontation=True` but `npcs_present=[]` for that turn, the encounter
starts with the player only and stays that way for the entire duration.
The empty-list case has a warning span at `narration_apply.py:413-421`
(`encounter.empty_actor_list` — exists in
`telemetry/spans.py:1110-1119`), but it is a leaf event with no
follow-up registration step.

The Crawling Scavenger case: Orin's narrator either started the
encounter without an `npcs_present` entry for the Scavenger, or the
Scavenger was added to `npcs_present` on a turn where
`snapshot.encounter` was already live (so `instantiate_encounter_from_trigger`
short-circuited at line 83-84 — `if current is not None and not current.resolved: return None`).

The dice dispatch falls back when an actor isn't found:
`dice.py:307-320` — `encounter.find_actor(character_name)` returns
`None`, then it picks the first player-side actor. That is the silent
fallback CLAUDE.md prohibits, and it is what kept Orin's combat
producing prose at all despite the missing registration.

### Outermost reachable seam (wire-first gate)

The wire-first test must drive a complete encounter through narration
+ dice + narration cycles and assert the actors array reflects every
combatant the narrator has named. Two seams matter:

1. **Encounter-start handshake** —
   `instantiate_encounter_from_trigger()`
   (`server/dispatch/encounter_lifecycle.py:49`). If the narrator's
   `npcs_present` is empty at the trigger turn, the encounter must
   either be deferred (no instantiation until at least one opponent
   is named) or registration must occur on the first follow-up turn
   that names an opponent. Pick one; do not silently start with a
   one-actor encounter.

2. **Per-turn re-registration** — `narration_apply.py:395-429`
   (the encounter-lifecycle block). When `result.npcs_present` names
   an opponent that is NOT in `encounter.actors`, append it. Cap by
   `cdef.actor_limit` if the def has one (verify by reading
   `genre/models/rules.py` ConfrontationDef). Validate side via the
   existing `_validate_side()` helper at
   `encounter_lifecycle.py:29-46`.

The boundary test must drive the full narration loop via
`session_handler_factory()` (`tests/server/conftest.py:332`) using
`_FakeClaudeClient` (`conftest.py:197`) returning canned narrator
output across multiple turns. The fixture must include an encounter
that starts with the player only and a follow-up turn where the
narrator names an NPC opponent in `npcs_present`. Assert
`snapshot.encounter.actors` contains both the player and the NPC
after the second turn. A unit test on the registration helper alone
fails the wire-first gate.

### OTEL spans (LOAD-BEARING per CLAUDE.md OTEL principle)

Define in `sidequest/telemetry/spans.py` and register in `SPAN_ROUTES`:

| Span | Attributes | Site |
|------|------------|------|
| `encounter.actor_registered` | `encounter_type`, `actor_name`, `role`, `side`, `source` (`"instantiation"` / `"per_turn_apply"`), `actor_count_after` | every site that appends to `encounter.actors` |
| `encounter.actor_registration_skipped` | `encounter_type`, `actor_name`, `reason` (`"already_registered"`, `"limit_reached"`, `"invalid_side"`), `current_actor_count` | the dedupe / cap check before append |

The existing `encounter.empty_actor_list` span
(`telemetry/spans.py:1110-1119`) stays — it remains the
encounter-start lie-detector flag for the trigger-with-no-NPCs case.
The new `actor_registered` span is what closes the loop: every
visible NPC in combat must produce one `actor_registered` span,
otherwise the GM panel can prove the registration didn't fire.

The dice-dispatch silent fallback at `dice.py:307-320` should ALSO
emit a watcher event when it triggers — not a fix in this story, but
note the gap for follow-up. The silent fallback hid the registration
bug for six rounds in Orin's session.

### Sibling story coupling — 45-21 (NPC registry HP)

45-21 closes the NPC-registry HP/max_hp write-back from combat stats:
"entry cannot report HP=0 unless actually dead." That story takes the
NPC entry as already existing in the registry; **this story makes
sure the entry exists at all** in the encounter's actor view. The two
share the combat-stats emission boundary:

- 45-18 owns: `encounter.actors` (the per-encounter, per-side list
  with role / withdrawn / per_actor_state fields).
- 45-21 owns: NPC registry HP fields (the durable per-NPC stats
  populated by combat extraction).

They overlap at the narrator extraction step
(`agents/orchestrator.py:1575-1603`) — both derive from
`result.npcs_present`. When 45-18 lands, every npc-mention with
combat side produces an `EncounterActor` AND a registry HP
write-back; pair the two stories' tests so neither can regress
without the other noticing. Do NOT merge their fixes — the two
data structures are independent and the failure modes are
distinguishable.

### Reuse, don't reinvent

- `EncounterActor` (`game/encounter.py:102-119`) is the canonical
  actor type. Use it; do not introduce a parallel "combatant"
  dataclass.
- `_validate_side()` (`encounter_lifecycle.py:29-46`) validates the
  closed `{player, opponent, neutral}` set and emits the
  `encounter_invalid_side_span` on rejection. Reuse for per-turn
  registration; do not re-implement the validation.
- `find_actor()` (`encounter.py:168-172`) is the canonical name
  lookup; use it for the dedupe check before append.
- `find_actor_for_player()` (`encounter.py:174-178`) is the canonical
  player-side lookup; the dice-dispatch fallback at
  `dice.py:307-320` should switch to this and raise instead of
  picking the first player-side actor when the named character isn't
  present (separate cleanup, may belong in this story or 45-21).
- `OrchestratorResult.npcs_present` and `NpcMention`
  (`agents/orchestrator.py:257`) are the established narrator-
  extraction shapes; do not introduce a parallel actor-mention type.
- `session_handler_factory()` for multi-turn boundary tests.

### Test files

- New: `sidequest-server/tests/server/test_encounter_actors_registration.py`
  — wire-first boundary test. Drives a 3-turn scenario:
  (1) confrontation triggers with the player only;
  (2) narrator's next turn names an opponent in `npcs_present`;
  (3) opponent's beat resolves. Asserts `encounter.actors` length 2
  after turn 2, beat-apply hits the correct actor on turn 3, and
  the `encounter.actor_registered` span fired with `source="per_turn_apply"`.
- Extend: `sidequest-server/tests/server/test_encounter_apply_narration.py`
  — add a regression case for the per-turn registration path on
  an already-live encounter. Verify the trigger-with-empty-npcs
  case still emits `encounter.empty_actor_list` and does NOT now
  spuriously emit `encounter.actor_registered`.
- Extend: `sidequest-server/tests/server/test_encounter_lifecycle.py`
  (or create) — instantiation path coverage for actor-cap and
  duplicate-name cases.
- New: `sidequest-server/tests/telemetry/test_encounter_actor_registered_span.py`
  — span attribute + SPAN_ROUTES routing assertions.

## Scope Boundaries

**In scope:**

- New per-turn actor registration in `narration_apply.py` for an
  already-live encounter, gated on
  `npcs_present` not already in `encounter.actors`.
- New `encounter.actor_registered` and
  `encounter.actor_registration_skipped` OTEL spans + SPAN_ROUTES
  entries.
- Wire-first boundary test exercising a multi-turn encounter where
  opponents arrive after instantiation.
- Side validation reuse (existing `_validate_side`).
- Optional: tighten `dice.py:307-320` silent fallback into a hard
  error or a watcher-event-emitting fallback. If included, MUST add
  a test that exercises the named-character-missing case.

**Out of scope:**

- NPC registry HP/max_hp write-back. **Sibling story 45-21** owns
  that. Scope boundary: this story stops at `encounter.actors`;
  45-21 starts at the NPC registry. Do not touch
  `npc_registry` write paths.
- Sealed-letter encounters (red/blue duel pattern,
  `encounter_lifecycle.py:98-133`). Sealed-letter is exactly-two-actors
  by construction; this story addresses the
  combatant/participant branch only.
- Withdrawn-actor handling. `EncounterActor.withdrawn` flips during
  yield (`game/encounter.py:118`); this story registers actors but
  does not alter withdrawal semantics.
- Actor removal on encounter resolution. Resolution clears the
  encounter; the actors array is dropped with it. No removal step
  needed inside an active encounter.
- Re-keying `apply_beat()` to honor the side-corrected actor
  (`game/beat_kinds.py`). If the existing first-player-side fallback
  at `dice.py:307-320` continues to behave as today after this fix,
  that's acceptable — but instrument the fallback (see Optional
  above) so future regressions surface.

## AC Context

1. **Encounter-start handshake registers every named NPC, not just the
   player.**
   - Test: drive an encounter trigger turn whose `npcs_present`
     contains one opponent NPC. Assert `snapshot.encounter.actors`
     has length 2 (player + NPC) after `instantiate_encounter_from_trigger`
     runs. The `encounter.actor_registered` span fires twice with
     `source="instantiation"` and `actor_count_after` of 1 then 2.
   - Negative: when `npcs_present=[]`, the encounter starts with one
     actor and the existing `encounter.empty_actor_list` span fires.
     `encounter.actor_registered` fires once (player only).

2. **Per-turn registration appends NPCs that arrive on a follow-up
   turn.**
   - Test: instantiate an encounter with player-only on turn N
     (empty `npcs_present`). On turn N+1, narrator emits
     `npcs_present=[Crawling Scavenger]`. Assert
     `encounter.actors` has length 2 after `_apply_narration_result_to_snapshot`
     completes; `actor_registered` span fires with
     `source="per_turn_apply"` and `actor_count_after=2`.
   - Negative: on turn N+2, narrator re-emits the same NPC. Assert
     `encounter.actors` length is still 2 (dedupe), and the
     `encounter.actor_registration_skipped` span fires with
     `reason="already_registered"`.

3. **Side validation rejects invalid `side` values consistently.**
   - Test: a per-turn registration with `side="enemy"` (not in the
     closed set) raises `ValueError` and emits the existing
     `encounter_invalid_side_span`. Match the instantiation path's
     behaviour (`encounter_lifecycle.py:142`).

4. **Dice-dispatch beat application targets the correct registered
   actor after a per-turn registration.**
   - Test: register an NPC on turn N+1 (per AC #2). On turn N+2,
     simulate the narrator selecting a beat for that NPC actor.
     Assert `apply_beat()` finds the actor by name (no first-player-
     side fallback at `dice.py:307-320`) and the
     `encounter.beat_applied` span carries the correct `actor` and
     `actor_side`.

5. **OTEL spans route to the GM panel watcher feed.**
   - Test: register `encounter.actor_registered` and
     `encounter.actor_registration_skipped` in SPAN_ROUTES with
     `event_type="state_transition"`, `component="encounter"`. Drive
     a registration tick; assert the watcher event arrives at the
     GM panel with the lifted attributes.

6. **No regression to sealed-letter actor pairing.**
   - Regression test: a sealed-letter encounter (e.g., dogfight)
     still instantiates with exactly two actors (red + blue), no
     per-turn re-registration ever fires, and the existing
     red/blue role assertions in
     `test_dogfight_sealed_letter*` continue to pass.
