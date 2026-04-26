# OTEL Phase 2 — Emission Family Rollouts: Handoff

> **Audience:** the next agent (you, future me, or a subagent) who picks up the
> Phase 2 work deferred from the OTEL Dashboard Restoration plan. Self-contained:
> read this and you can ship without re-reading the spec.

**Date:** 2026-04-25 (handoff written at completion of Phase 0–3)

**Predecessor work (now merged or in review):**
- Spec: `docs/superpowers/specs/2026-04-25-otel-dashboard-restoration-design.md`
- Plan: `docs/superpowers/plans/2026-04-25-otel-dashboard-restoration.md`
- ADR: `docs/adr/090-otel-dashboard-restoration.md` (status `accepted`)
- ADR-031 amended with Python-port section
- PRs:
  - orchestrator [slabgorb/sidequest#143](https://github.com/slabgorb/sidequest/pull/143) → `main`
  - server [slabgorb/sidequest-server#48](https://github.com/slabgorb/sidequest-server/pull/48) → `develop`
  - ui [slabgorb/sidequest-ui#163](https://github.com/slabgorb/sidequest-ui/pull/163) → `develop`

**Read these once before starting** (10 minutes total, then don't re-read):
1. This handoff (you are here).
2. `docs/adr/031-game-watcher-semantic-telemetry.md` — Python-port section at the bottom.
3. `sidequest-server/sidequest/telemetry/spans.py` — see how `SPAN_ROUTES` and `FLAT_ONLY_SPANS` are populated. Note the routes that already exist for live spans (encounter, combat, local_dm, projection).
4. `sidequest-server/tests/telemetry/test_routing_completeness.py` — the lint that will fail your PR if you skip a routing decision.

---

## What "Phase 2" is

The OTEL Dashboard Restoration plan installed the *infrastructure* for the
GM-panel "lie detector":

- `SpanRoute` mechanism colocated with span constants
- `WatcherSpanProcessor.on_end` augments every span close with a typed event
- Routing-completeness lint enforces explicit decisions
- `turn_span()` anchors every dispatch trace
- Layer-3 validator pipeline runs five deterministic checks per `TurnRecord`

But it only wired **`turn_span`** as Phase 2. **~24 other subsystem families are
still empty hulls** — their `SPAN_*` constants exist in `spans.py`, they sit in
`FLAT_ONLY_SPANS`, but no production code opens them. The dashboard's typed
tabs receive nothing for those subsystems.

Phase 2 fills the hulls: for each family, add emission helpers + call sites at
the documented module, move the family's constants from `FLAT_ONLY_SPANS` to
`SPAN_ROUTES` (or keep flat-only with a documented reason), and prove the
wiring works with one integration test per family.

---

## Pre-conditions (what must already be on the branch)

Before starting any family rollout, verify:

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git log --oneline | grep -E "(SpanRoute|turn_span|Validator)" | head
```

You should see commits including:
- `feat(telemetry): add SpanRoute, SPAN_ROUTES, FLAT_ONLY_SPANS scaffolding`
- `feat(telemetry): add turn_span() root context manager`
- `feat(telemetry): Validator skeleton with bounded queue and lifecycle`
- `feat(server): assemble TurnRecord at dispatch end and submit to validator`

If those aren't visible, the OTEL-restoration PRs haven't merged yet — wait or
work on top of `feat/otel-dashboard-restoration` directly.

Also confirm:

```bash
uv run pytest tests/telemetry/test_routing_completeness.py -v
```

Must pass — the lint should already accept the current state.

---

## Strategy: bundle by adjacent module, ship one family per PR

The spec deferred this question: should Phase 2 be ~25 micro-PRs (one per
family) or fewer bundle-PRs?

**Recommendation: one PR per family**, but bundle related families in the same
plan/branch when their modules are adjacent and their reviewers will be the
same. Examples:

- **Trope bundle:** `SPAN_TROPE_TICK`, `_TICK_PER`, `_ROOM_TICK`, `_ACTIVATE`,
  `_RESOLVE`, `_CROSS_SESSION`, `_EVALUATE_TRIGGERS` — all in
  `sidequest/game/trope*.py` + `sidequest/agents/subsystems/troper*.py`. One PR.
- **State-patch bundle:** `SPAN_APPLY_WORLD_PATCH`, `SPAN_QUEST_UPDATE`,
  `SPAN_BUILD_PROTOCOL_DELTA`, `SPAN_COMPUTE_DELTA` — all in
  `sidequest/game/state*.py` + `sidequest/game/delta.py`. One PR.
- **Orchestrator-injection bundle:** the six `SPAN_ORCHESTRATOR_*` injection
  spans — all in `sidequest/agents/orchestrator.py`. One PR.

Single-span families (e.g. `SPAN_NARRATOR_SEALED_ROUND`,
`SPAN_RAG_PROSE_CLEANUP`) get their own one-span PR.

PR titles follow `feat(otel/<family>): wire <family> spans through to dashboard`.

---

## The per-family template (TDD; copy these steps)

For each family, the work is mechanical because the infrastructure already
exists. Each PR should produce ONE bundle of:

### 1. Helper(s) in `spans.py`

If the family doesn't already have a `xxx_span()` context manager, add one.
Pattern (copy from `turn_span`):

```python
@contextmanager
def trope_tick_span(
    *,
    trope_id: str,
    room_id: str,
    tick: int,
    _tracer: trace.Tracer | None = None,
    **attrs: Any,
) -> Iterator[trace.Span]:
    """One trope tick — see ADR-031 §"Layer 2"."""
    t = _tracer or tracer()
    with t.start_as_current_span(SPAN_TROPE_TICK) as span:
        span.set_attribute("trope_id", trope_id)
        span.set_attribute("room_id", room_id)
        span.set_attribute("tick", tick)
        for k, v in attrs.items():
            span.set_attribute(k, v)
        yield span
```

The required positional kwargs come from ADR-031 §"Layer 2"; check there for
the family's contract. Always accept `**attrs` for extras and `_tracer` for
testability.

### 2. `SpanRoute` entry (or stay flat-only) immediately next to the constant

```python
SPAN_TROPE_TICK = "trope.tick"
SPAN_ROUTES[SPAN_TROPE_TICK] = SpanRoute(
    event_type="state_transition",
    component="trope",
    extract=lambda span: {
        "field": "trope.tick",
        "trope_id": (span.attributes or {}).get("trope_id", ""),
        "room_id": (span.attributes or {}).get("room_id", ""),
        "tick": (span.attributes or {}).get("tick", 0),
    },
)
```

**MOVE the constant out of `FLAT_ONLY_SPANS`** at the bottom of `spans.py`.
Either inline-add to `SPAN_ROUTES` (preferred), or if it stays flat-only,
add a comment explaining why it has no semantic payload (e.g. structural
parent span; high-volume read; pure timing).

### 3. Emission site(s) at the documented module

Replace bare `start_as_current_span` calls with the helper. If no emission
site exists yet, add one at the entry of the relevant function:

```python
# sidequest/game/trope.py
def tick_trope(self, trope_id: str, room_id: str) -> None:
    from sidequest.telemetry.spans import trope_tick_span

    with trope_tick_span(
        trope_id=trope_id,
        room_id=room_id,
        tick=self._tick_counter,
    ):
        # existing logic
        ...
```

**Critical:** the emission site's `attributes={...}` keys MUST match the
extract lambda's `.get(...)` calls. Read the existing emission site first;
copy keys verbatim.

### 4. Migrate any direct `publish_event` site this span subsumes

Per spec §6.6, when a span gains a route that emits the same typed event a
direct `publish_event(...)` was previously emitting, **delete the direct
emit** and document in the PR body. Check `sidequest/server/narration_apply.py`,
`session_handler.py`, `session_helpers.py` for direct emits that the new
routing replaces. (Task 21's dedupe of `turn_complete` is the precedent.)

### 5. Translator-routing test row

Add to `tests/server/test_watcher_events.py`:

```python
async def test_trope_tick_routes_to_state_transition() -> None:
    # ... build a fake span with the family's constant + attrs ...
    # ... assert typed event lands with component="trope" ...
```

### 6. Wiring integration test

Per spec §7.1 Layer 3 — one per family:

```python
# tests/integration/test_<family>_wiring.py
@pytest.mark.asyncio
async def test_<family>_emits_state_transition(server_fixture):
    fake_ws = FakeWatcher()
    await watcher_hub.subscribe(fake_ws)

    await server_fixture.dispatch_action(
        player="alice",
        text="<trigger that exercises this subsystem>",
    )

    events = fake_ws.events
    assert any(
        e["event_type"] == "state_transition" and e["component"] == "<family>"
        for e in events
    ), "<family> span never reached the watcher hub"
```

The text input must actually exercise the subsystem. For trope, fire an
action that crosses a beat threshold. For NPC registration, name an unknown
NPC. Etc.

### 7. Routing-completeness lint stays green

```bash
uv run pytest tests/telemetry/test_routing_completeness.py -v
```

If a constant moved from `FLAT_ONLY_SPANS` to `SPAN_ROUTES`, both should still
sum to "all `SPAN_*` constants accounted for". The test should already pass
because `FLAT_ONLY_SPANS.update({...})` minus `SPAN_ROUTES` additions = same
total coverage.

### 8. Commit + PR

Single commit per family bundle. Message:

```
feat(otel/<family>): emit <family> spans to dashboard

- helpers: <list>
- routes: <list> moved from FLAT_ONLY_SPANS to SPAN_ROUTES
- migrated direct publish_event sites: <list, or "none">
- wiring test: tests/integration/test_<family>_wiring.py

ADR-090 §"Phase 2 emission rollouts"
```

PR body should list the validation_warning the validator was previously
emitting (or NOT emitting) for this subsystem and confirm the dashboard now
shows live data via screenshot OR a smoke-run log.

---

## The ~24 family table

Direct port from spec §4.1, with bundling suggestions. Tackle in the order
shown — high-leverage / high-mechanic-trust first.

| # | Bundle | Family / Constants | Target module(s) | Notes |
|---|---|---|---|---|
| 1 | **state-patch** | `SPAN_APPLY_WORLD_PATCH`, `SPAN_QUEST_UPDATE`, `SPAN_BUILD_PROTOCOL_DELTA`, `SPAN_COMPUTE_DELTA` | `game/state*.py`, `game/delta.py` | Highest-leverage; ADR-031 cites this as the patch-legality input |
| 2 | **NPC** | `SPAN_NPC_REGISTRATION`, `SPAN_NPC_MERGE_PATCH` (auto/reinvented are NOT spans — left as logger.info strings — leave them in FLAT_ONLY_SPANS or remove from spans.py entirely) | `server/dispatch/npc_registry.py`, `game/npc*.py` | Cross-check with what Task 5 found |
| 3 | **trope** | `SPAN_TROPE_TICK`, `_TICK_PER`, `_ROOM_TICK`, `_ACTIVATE`, `_RESOLVE`, `_CROSS_SESSION`, `_EVALUATE_TRIGGERS` | `game/trope*.py`, `agents/subsystems/troper*.py` | 7-span bundle; large but cohesive |
| 4 | **encounter** (extras) | Whatever encounter spans were not yet routed in Task 5 | `game/encounter.py` | Most encounter spans already routed; check |
| 5 | **chargen** | `SPAN_CHARGEN_STAT_ROLL`, `_STATS_GENERATED`, `_HP_FORMULA`, `_BACKSTORY_COMPOSED` | `game/builder*.py` | Note: when `wip/hp-to-edge` lands, `_HP_FORMULA` becomes `_EDGE_FORMULA` |
| 6 | **persistence** | `SPAN_PERSISTENCE_SAVE`, `_LOAD`, `_DELETE` | `game/persistence.py` | Each opens its own root span (no parent turn) |
| 7 | **disposition** | `SPAN_DISPOSITION_SHIFT` | `game/disposition.py` | Single-span PR |
| 8 | **creature** | `SPAN_CREATURE_HP_DELTA` | `game/creature_core.py` | hp/edge field rename pending |
| 9 | **barrier** | `SPAN_BARRIER_ACTIVATED`, `_RESOLVED` | `game/barrier*.py`, `server/dispatch/barrier.py` | |
| 10 | **narrator** | `SPAN_NARRATOR_SEALED_ROUND` | `server/dispatch/barrier.py` | One per sealed-round resolution |
| 11 | **orchestrator-injection** | `SPAN_ORCHESTRATOR_NARRATOR_SESSION_RESET`, `_GENRE_IDENTITY_INJECTION`, `_TACTICAL_GRID_INJECTION`, `_TROPE_BEAT_INJECTION`, `_PARTY_PEER_INJECTION`, `_LORE_FILTER` | `agents/orchestrator.py` | 6-span bundle |
| 12 | **agent LLM** | `SPAN_TURN_AGENT_LLM_PROMPT_BUILD`, `_PARSE_RESPONSE` (`_INFERENCE` already flat-only) | `agents/orchestrator.py` | Wrap existing inference call |
| 13 | **content** | `SPAN_CONTENT_RESOLVE` | `genre/resolver*.py` | High volume — confirm sampling rate; consider keeping flat-only if dashboard would drown |
| 14 | **music** | `SPAN_MUSIC_EVALUATE`, `_CLASSIFY_MOOD` | `audio/` modules in server | Verify there's actual audio dispatch in Python (some audio lives in daemon) |
| 15 | **inventory** | `SPAN_INVENTORY_EXTRACTION` | `agents/inventory_extractor*.py` | Drives `json_extraction_result` typed event (severity tier>1 → warning) |
| 16 | **continuity** | `SPAN_CONTINUITY_LLM_VALIDATION` | `agents/continuity_validator*.py` | Same: `json_extraction_result` |
| 17 | **compose** | `SPAN_COMPOSE` | `agents/context_builder*.py` | Wraps prompt-zone composition; routes to `prompt_assembled` |
| 18 | **world** | `SPAN_WORLD_MATERIALIZED` | `agents/agents/world_builder*.py` | |
| 19 | **RAG** | `SPAN_RAG_PROSE_CLEANUP` | `agents/orchestrator.py` (or wherever lore retrieval landed) | Routes to `lore_retrieval` |
| 20 | **script-tool** | `SPAN_SCRIPT_TOOL_PROMPT_INJECTED` | `agents/orchestrator.py` | |
| 21 | **reminders** | `SPAN_REMINDER_SPAWNED`, `_FIRED` | `server/dispatch/connect.py`, `server/app.py` | |
| 22 | **pregen** | `SPAN_PREGEN_SEED_MANUAL` | `server/dispatch/pregen*.py` | |
| 23 | **catch-up** | `SPAN_CATCH_UP_GENERATE` | `server/dispatch/catch_up*.py` | |
| 24 | **scenario** | `SPAN_SCENARIO_ADVANCE`, `_ACCUSATION` | `server/dispatch/*.py`, `server/dispatch/slash*.py` | |
| 25 | **monster-manual** | `SPAN_MONSTER_MANUAL_INJECTED` | `server/dispatch/*.py` | |
| 26 | **merchant** | `SPAN_MERCHANT_CONTEXT_INJECTED`, `_TRANSACTION` | `agents/orchestrator.py`, `game/state*.py` | |

(That's 26, not 24 — I miscounted in the predecessor plan. Same shape.)

---

## When to skip a family / leave flat-only

Not every span needs a typed event. Keep `FLAT_ONLY_SPANS` membership for:

- **Structural parent spans** whose effects propagate via deeper spans
  (e.g. `SPAN_TURN_SYSTEM_TICK`, `SPAN_TURN_BARRIER`).
- **High-volume reads** that would spam the dashboard if every call became
  a typed event (e.g. `SPAN_CONTENT_RESOLVE` — every genre-pack lookup).
- **Pure timing wrappers** with no semantic content (Claude subprocess
  timing, LLM inference duration).

If you decide a family stays flat-only, leave its constants in
`FLAT_ONLY_SPANS` and add a one-line comment near the constant explaining the
decision. The lint will accept this; reviewers should see the rationale
inline.

---

## Validator-side updates (none expected, but watch for these)

When a Phase 2 family lands, occasionally the validator's `subsystem_exercise_check`
window will need to know about the new agent_name. Update
`_KNOWN_SUBSYSTEMS` in `validator.py` if the family introduces a NEW
agent_name string. (Most families don't — they emit through existing
`agent_name="narrator"|"combat"|"merchant"|"world_builder"|"scenario"|
"encounter"|"chargen"|"trope"|"barrier"`.)

---

## Per-PR validation gates

Before marking a family PR ready for review:

1. `uv run pytest tests/telemetry/test_routing_completeness.py` — green
2. `uv run pytest tests/server/test_watcher_events.py` — green (typed-event row added)
3. `uv run pytest tests/integration/test_<family>_wiring.py` — green
4. `uv run pytest tests/server/ tests/telemetry/ -x` — full suite green
5. `uv run ruff check sidequest/telemetry/spans.py sidequest/<target_module>.py tests/integration/test_<family>_wiring.py`
6. Manual smoke: `just up` + `just otel`, drive an action that exercises the subsystem, confirm the `state_transition` (or whatever event_type) shows up with the right `component` tag in the dashboard.

If validator emits `coverage_gap` for the subsystem before AND after your PR
(over a 10-turn window), the wiring isn't actually firing. Debug.

---

## Out of scope for Phase 2

- **TurnRecord field tightening** — `classified_intent`, `extraction_tier`,
  `delta` sentinels remain. These tighten when LocalDM/StateDelta surface
  the signals; track separately.
- **`hp` → `current_edge` rename** in `patch_legality_check`. Wait for
  `wip/hp-to-edge` to merge; rename in a follow-up PR.
- **FastAPI `lifespan=` migration** — 18 deprecation warnings around
  `@app.on_event`. Project-wide chore; not gated on Phase 2.
- **Phase 2 emission for NEW spans not in the current `spans.py` catalog.**
  If you discover a subsystem missing a `SPAN_*` constant entirely, that's
  a separate add-the-constant change; do it in its own commit, then route it.
- **Replay / persistence of `TurnRecord`** — ADR-031 mentions as future;
  not built.
- **Second-LLM validation.** ADR-031's "God lifting rocks" prohibition stands.

---

## Recommended cadence

- **One bundle per session.** Don't batch multiple bundles in the same plan;
  reviewers benefit from focused diffs.
- **State-patch bundle first** (highest mechanic-trust leverage), then NPC,
  then trope, then encounter-extras, then orchestrator-injection. After
  those four, the dashboard has the load-bearing subsystems lit up; the
  remaining bundles are polish.
- **Monthly checkpoint:** count emission sites for the five typed events.
  If `state_transition` emission count plateaus while bundles still remain,
  something's stuck — investigate before continuing.

```bash
cd sidequest-server
for evt in turn_complete state_transition validation_warning subsystem_exercise_summary coverage_gap; do
  count=$(grep -r "\"$evt\"" sidequest/ --include="*.py" | grep -v __pycache__ | wc -l)
  echo "$evt: $count emission sites"
done
```

Track this number in the PR body of each bundle so reviewers see the
trajectory.

---

## When you're done with all bundles

- Delete the "drift" / "deferred" markers from any ADR that referenced this
  Phase-2 work.
- Move ADR-090 from `implementation-status: live` (which it already is) — no
  change needed; the live status was always about the infrastructure, not
  the ~26 follow-ups.
- Update CLAUDE.md ADR Index if any category groupings shift; run
  `python3 scripts/regenerate_adr_indexes.py`.
- Close out any "TODO: tighten in Phase 2" comments left in
  `session_handler.py` (the TurnRecord sentinels become non-sentinel).

---

## How to invoke this handoff

If you want a fresh agent to take over:

```
/superpowers:writing-plans docs/superpowers/plans/2026-04-25-otel-phase-2-emission-rollouts-HANDOFF.md
```

The agent should pick a single bundle from the table above, write a focused
plan for that bundle (using this handoff as the spec), then execute via
subagent-driven-development. Don't try to plan all 26 in one document — that's
how the predecessor plan got too big to be practical.

Or, more directly, if you want to skip the planning ceremony for an obvious
bundle:

```
/pf-dev   # then paste the per-family template above and the row from the table for the bundle
```

The infrastructure is in place. Each family rollout is mechanical. Ship one
bundle a session and the dashboard fills in over time.
