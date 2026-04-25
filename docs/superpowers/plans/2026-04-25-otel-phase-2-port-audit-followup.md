# OTEL Phase 2 — Python-port audit follow-up

> Companion to `2026-04-25-otel-phase-2-emission-rollouts-HANDOFF.md`. Read
> *that* handoff first; this one is the discovered-state correction after
> shipping the first two bundles.

**Date:** 2026-04-25 (post bundles #1, #2)

**Predecessor PRs (merged):**
- `feat(otel/state-patch)` — slabgorb/sidequest-server#49
- `feat(otel/npc)` — slabgorb/sidequest-server#50

---

## TL;DR

The original Phase-2 handoff assumed that the ~26 SPAN_* families it
enumerated all had **live OTEL spans being opened in Python production
code**, and that the Phase-2 work was simply "add a route + extract
lambda + wiring test per family."

That premise is wrong for most of the table. **The Python port (ADR-082)
did not carry over the Rust `info_span!`/`tracer.start_as_current_span`
emissions in most subsystems**; instead, the port replaced them with
`logger.info("subsystem.event_name attr=value", ...)` strings, or with
direct `_watcher_publish("state_transition", ...)` calls.

The `SPAN_*` constants in `sidequest/telemetry/spans.py` are mostly
**byte-identical-to-Rust name strings used for log-line prefixing**, not
spans. Wiring routes for them changes nothing because nothing opens the
spans.

The only Phase-2 work that actually moved the needle was migrating
existing `_watcher_publish` direct calls into span-routed helpers — the
shape the dashboard already consumes is preserved, but the emission
becomes a span the validator can also see.

## What's actually live in Python

Span families that genuinely emit OTEL spans in Python production code:

| Family | Helper | Status |
|---|---|---|
| `turn` | `turn_span()` | Live — Phase-1 work, validator anchor |
| `combat.*` | `combat_*_span()` | Live — Story 3.4 |
| `encounter.*` | `encounter_*_span()` | Live — Story 3.4, all 6 routed |
| `projection.*` | `projection_*_span()` | Live — Group F |
| `local_dm.*` | `local_dm_*_span()` | Live — Group B |
| `mp.*` | `mp_*_span()` | Live — multiplayer lifecycle |
| `agent.call`, `agent.call.session` | `agent_call*_span()` | Live (intentionally flat-only — pure timing) |
| `quest_update` | `quest_update_span()` | **Live as of #49** |
| `npc.auto_registered` | `npc_auto_registered_span()` | **Live as of #50** |
| `npc.reinvented` | `npc_reinvented_span()` | **Live as of #50** |

Span families that are **port-dead** (constant exists, no Python span
opens it; original handoff bundle assumed otherwise):

| Bundle | Constants | Why dead |
|---|---|---|
| Trope (#3) | `SPAN_TROPE_TICK`, `_TICK_PER`, `_ROOM_TICK`, `_ACTIVATE`, `_RESOLVE`, `_CROSS_SESSION`, `_EVALUATE_TRIGGERS` | Trope engine **P2-deferred** in Python (see `game/session.py:339, 397`). No `game/trope*.py` or `agents/subsystems/troper*.py` exist. |
| Chargen (#5) | `SPAN_CHARGEN_STAT_ROLL`, `_STATS_GENERATED`, `_HP_FORMULA`, `_BACKSTORY_COMPOSED` | `game/builder.py` uses `span.add_event(...)` inside the *parent* span, not `start_as_current_span`. The constant strings appear as event names, not span names — `WatcherSpanProcessor.on_end` never sees them. |
| Persistence (#6) | `SPAN_PERSISTENCE_SAVE`, `_LOAD`, `_DELETE` | No `start_as_current_span` calls in `game/persistence.py`. |
| Disposition (#7) | `SPAN_DISPOSITION_SHIFT` | No `game/disposition.py` exists in Python; logic inlined in `narration_apply.py`. |
| Orchestrator-injection (#11) | All 6 `SPAN_ORCHESTRATOR_*` injection spans | All emitted as `logger.info("orchestrator.<event> ...")` strings in `agents/orchestrator.py`, never as spans. |
| Single-span families | `SPAN_NARRATOR_SEALED_ROUND`, `SPAN_RAG_PROSE_CLEANUP`, `SPAN_INVENTORY_EXTRACTION`, `SPAN_CONTINUITY_LLM_VALIDATION`, `SPAN_COMPOSE`, `SPAN_WORLD_MATERIALIZED`, `SPAN_SCRIPT_TOOL_PROMPT_INJECTED`, `SPAN_REMINDER_SPAWNED`, `SPAN_REMINDER_FIRED`, `SPAN_PREGEN_SEED_MANUAL`, `SPAN_CATCH_UP_GENERATE`, `SPAN_SCENARIO_ADVANCE`, `SPAN_SCENARIO_ACCUSATION`, `SPAN_MONSTER_MANUAL_INJECTED` | Same pattern: name strings live as `logger.info` prefixes; no `start_as_current_span` opens them. |
| Encounter-extras (#4) | All `SPAN_COMBAT_*`, `SPAN_ENCOUNTER_*` | All 9 already routed before this audit — empty bundle. |
| State-patch siblings (#1) | `SPAN_APPLY_WORLD_PATCH`, `SPAN_BUILD_PROTOCOL_DELTA`, `SPAN_COMPUTE_DELTA` | Already documented in #49; functions exist but no production caller. |
| NPC siblings (#2) | `SPAN_NPC_REGISTRATION`, `SPAN_NPC_MERGE_PATCH` | Already documented in #50; no production caller. |

## What "Phase 2" should actually be

Two distinct workstreams:

### Workstream A — Migrate live `_watcher_publish` sites

Many existing direct `publish_event("state_transition", ...)` calls in
`narration_apply.py`, `session_handler.py`, and `session_helpers.py`
already produce typed events the dashboard consumes. Migrating them to
span-routed helpers (the pattern bundles #1 and #2 used) preserves the
payload shape but adds:

- A typed span the validator can correlate with `turn_span` parents.
- A canonical OTEL span name the GM panel can filter on.
- Single-source-of-truth payload extraction in `SPAN_ROUTES`.

Live `_watcher_publish` sites worth migrating (rough census, run `grep -rn
'_watcher_publish' sidequest/ --include='*.py' | grep -v telemetry`):

- `narration_apply.py`: location, inventory, encounter started/skipped/
  beat_applied/resolved, lore_established (≈8 sites).
- `session_handler.py`: ≈25 sites covering audio cues, lifecycle events,
  encounter state, projections.

These are the **real** Phase-2 candidates. Each one is a small bundle
(1-3 sites) that picks a coherent slice and migrates it. The
`SPAN_ROUTES` list grows by one entry per bundle; the constant catalog
in `spans.py` may need new constants if the existing dead ones don't
match.

### Workstream B — Port the missing engines

If the project wants the `SPAN_TROPE_*`, `SPAN_CHARGEN_*`,
`SPAN_DISPOSITION_*`, `SPAN_ORCHESTRATOR_*` etc. routes to fire, the
underlying engines have to be ported from Rust. That is **not a
telemetry-restoration task** — it's an engine-port task that telemetry
piggybacks on.

Until that happens, the constants should either:

- Stay in `FLAT_ONLY_SPANS` with a `# Python port did not implement —
  see ADR-082 / engine_X.py:N for status` comment (current pattern), or
- Be removed entirely from `spans.py` so the catalog reflects what
  actually exists. **Recommendation: leave them for now**; removing
  them breaks the byte-identical-to-Rust observability contract that
  ADR-031 cares about, and the comment cost is one line per constant.

## Recommended next-bundle picks

Pick from the Workstream-A census. Suggested order of impact:

1. **Audio cues** in `session_handler.py` — high-volume during play,
   lights up the Subsystems tab's `audio` component immediately.
2. **Encounter lifecycle extras** in `narration_apply.py`
   (`apply_encounter_updates`) — duplicates of `dispatch/` emissions
   that escaped the Story 3.4 wave; routing them dedupes.
3. **Inventory mutations** in `narration_apply.py` (items_gained /
   items_lost) — the validator's `inventory_check` already correlates
   on these; routing closes the loop.
4. **Lore-established events** in `narration_apply.py` — small, drives
   the `lore_retrieval` typed event when paired with a route on a new
   `SPAN_LORE_ESTABLISHED` constant.

Each is a 1-2 hour bundle following the established pattern from #49
and #50.

## What stayed unchanged

- `WatcherSpanProcessor` now has a span-attribute escape hatch for
  `severity` (added in #50). Helpers can set `severity="warning"` as
  a span attribute and the typed event will reflect it. Use this when
  migrating any direct `_watcher_publish(..., severity="warning")` call.
- `SPAN_ROUTES` / `FLAT_ONLY_SPANS` lint
  (`tests/telemetry/test_routing_completeness.py`) is unchanged and
  enforces the explicit-decision rule for any new constants.
- Wiring-test pattern (monkeypatch `spans_module.tracer` to point at a
  local `TracerProvider+WatcherSpanProcessor`) is the only way to test
  end-to-end through production helpers — OTEL refuses to replace an
  already-installed global provider mid-suite. See
  `tests/integration/test_state_patch_wiring.py` and
  `tests/integration/test_npc_wiring.py` for the canonical shape.

## What to delete from the predecessor handoff

The "~24 family table" in
`docs/superpowers/plans/2026-04-25-otel-phase-2-emission-rollouts-HANDOFF.md`
should be marked **superseded** by this document. The bundles labeled
"trope", "chargen", "persistence", "disposition", "orchestrator-injection",
"single-span families" should not be picked up as routing-only work —
they require engine porting first.

The bundles labeled "state-patch", "NPC", and "encounter extras" are
done.

## Open question for the next agent

Should `WatcherSpanProcessor` grow a third tier — convert
`logger.info("subsystem.event ...")` strings into typed events? That
would let the port-dead families "light up" the dashboard without
porting their engines, by parsing log lines instead of OTEL spans. Cost:
adds a string-parsing seam outside the OTEL contract; benefit: bridges
the port gap without engine work. Decide explicitly before going down
that path — recommendation is to **not** do it (string-parsing
log-formatted events is the textbook Illusionism that ADR-031
prohibits) and instead focus Phase 2 on Workstream A only.
