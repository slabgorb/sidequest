# NPC Relationship Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the server-tracked NPC relationship state (disposition, the *why* behind each shift, OCEAN personality, and claims-to-party) visible to the player through a new reactive `RELATIONSHIPS` message and a dockview panel, without leaking ADR-053 mystery solutions.

**Architecture:** A persistent per-NPC `disposition_log` ring buffer fed by a single `Npc.record_disposition_beat(...)` seam wired at **all four** disposition-mutation sites; a payload **builder** in `game/projection/relationships.py` that converts engine NPC state into protocol payload models (respecting the leaf-ward `protocol` dependency direction) and applies the claims-only firewall **at build time** (disposition/OCEAN/claims are global, so no per-recipient projection fork is needed); a reactive emitter that broadcasts via `emit_fn` like `LOCATION_DESCRIPTION`, change-gated to honor *Cost Scales with Drama*; and a `relationships` dockview panel with hybrid disclosure (narrative band by default, raw int + beats + numeric OCEAN + claims on expand).

**Tech Stack:** Python 3 / Pydantic v2 / FastAPI (server), pytest + OTEL span assertions (tests), React + TypeScript + dockview + Vitest/RTL (UI).

---

## Refinements discovered during recon (read before starting)

The design spec (`docs/superpowers/specs/2026-06-01-npc-relationship-panel-design.md`) is the authority on intent. Five things the spec's orientation-level pointers got slightly wrong; this plan supersedes them and each is logged as a deviation in the relevant task:

1. **Four disposition-mutation sites, not three.** The spec named the engagement tick, the `update_npc_disposition` tool, and "any morale-event path." The real sites are:
   - `develop_npc_on_engagement` → recorded at its caller `sidequest/server/narration_apply.py:1704` (turn + location in scope).
   - the `update_npc_disposition` tool, `sidequest/agents/tools/update_npc_disposition.py:116`.
   - `GameSnapshot.apply_patch` `npc_attitudes` loop, `sidequest/game/session.py:1418`.
   - `WorldMaterializer._apply_npc` chapter upsert, `sidequest/game/world_materialization.py:502`.
   The tool site and the chapter-upsert site **do not** emit `SPAN_DISPOSITION_SHIFT` today.

2. **`develop_npc_on_engagement` lives in `game/npc_development.py`, not `narration_apply.py`.** It returns a `DevelopmentTick` (with `.disposition_delta`); the caller in `narration_apply.py` owns turn/location and already emits the shift span — record the beat there.

3. **The OCEAN materializer already copies `ocean` — in the wrong shape.** `preload_authored_npcs` (`world_materialization.py:868`) copies the raw authored dict (`{"O":0.5,...}`, short keys, 0..1 scale) straight onto `Npc.ocean`. The 72-9 narrator path writes a different shape (`{"openness":5.0,...}`, full keys, 0..10). Phase B is **normalization**, not "wire seeding."

4. **The firewall is a build-time global filter, not a per-recipient projection stage.** The ADR-104/105 `ComposedFilter` chain is an *include/exclude gate on whole messages*. Disposition, OCEAN, and claims-to-party are all global (per-PC standing is an explicit non-goal), so the claims-only filter is applied once when building the payload and the message broadcasts via `emit_fn` — mirroring the live `LOCATION_DESCRIPTION` emitter, which is also a global per-domain reactive message.

5. **`protocol/` is a leaf.** `game`/`server` import from `protocol`, never the reverse. The payload models (`RelationshipEntry`, `DispositionBeatPayload`, etc.) live in `protocol/models.py` and **must not** import `game.DispositionBeat` or `genre.OceanProfile`. The builder in `game/` does the engine→payload conversion.

**Claims semantic note (Phase C):** `BeliefClaim` is modeled as "a statement made by another NPC, which may or may not be believed" (a claim in the NPC's knowledge, sourced via `BeliefSourceToldBy.by`), not literally "what this NPC told the party." Filtering `belief_state.beliefs` to `variant == "claim"` is nonetheless the correct **spoiler boundary**: `Fact`/`Suspicion` (the mystery solution) never cross. We surface claim content + a coarse credibility hint derived from `credibility_scores[source.by]`.

---

## File Structure

**Server — new files:**
- `sidequest/telemetry/spans/relationship.py` — `SPAN_RELATIONSHIP_BEAT_RECORDED` + `SPAN_RELATIONSHIPS_EMITTED` constants and `SPAN_ROUTES` entries.
- `sidequest/game/projection/relationships.py` — pure builder: `band_for`, `trend_for`, `personality_read`, `claims_to_party`, `build_relationship_entries`.
- `sidequest/server/websocket_handlers/relationships_emit.py` — `_maybe_emit_relationships` reactive emitter (mirrors `map_emit.py`).
- `tests/game/test_disposition_beat.py`, `tests/game/test_relationships_builder.py`, `tests/server/test_relationships_emit.py`, `tests/server/test_relationship_beat_wiring.py`, `tests/game/test_ocean_normalize.py`, `tests/game/test_relationships_claims_firewall.py`.

**Server — modified:**
- `sidequest/game/disposition.py` — `DispositionBeat`, `DISPOSITION_LOG_CAP`, reason constants.
- `sidequest/game/session.py` — `Npc.disposition_log` field + `record_disposition_beat` method; beat call in `apply_patch`.
- `sidequest/game/npc_development.py` — `ENGAGEMENT_BEAT_REASON` constant.
- `sidequest/server/narration_apply.py` — beat call at the engagement tick.
- `sidequest/agents/tools/update_npc_disposition.py` — beat call.
- `sidequest/game/world_materialization.py` — beat call (existing-NPC delta branch); OCEAN normalize at preload.
- `sidequest/genre/models/ocean.py` — `OceanProfile.from_authored`.
- `sidequest/protocol/enums.py` — `MessageType.RELATIONSHIPS`.
- `sidequest/protocol/models.py` — `DispositionBeatPayload`, `RelationshipClaimPayload`, `RelationshipEntry`, `RelationshipsPayload`.
- `sidequest/protocol/messages.py` — `RelationshipsMessage` + union member.
- `sidequest/server/session_handler.py` — `_KIND_TO_MESSAGE_CLS` registration.
- `sidequest/server/websocket_session_handler.py` — wire emitter into turn loop + resume.

**UI — new files:**
- `src/components/RelationshipsPanel.tsx` — the panel.
- `src/components/GameBoard/widgets/RelationshipsWidget.tsx` — thin adapter.
- `src/components/__tests__/RelationshipsPanel.test.tsx`, `src/components/GameBoard/__tests__/GameBoard-relationships-tab.test.tsx`.

**UI — modified:**
- `src/types/protocol.ts` — `MessageType.RELATIONSHIPS`.
- `src/types/payloads.ts` — `DispositionBeatPayload`, `RelationshipClaimPayload`, `RelationshipEntryPayload`, `RelationshipsPayload`, `RelationshipsMessage`.
- `src/providers/GameStateProvider.tsx` — `ClientGameState.relationships`.
- `src/hooks/useStateMirror.ts` — `RELATIONSHIPS` case.
- `src/components/GameBoard/widgetRegistry.ts` — `WidgetId` + `WIDGET_REGISTRY` entry.
- `src/components/GameBoard/GameBoard.tsx` — `rightGroupOrder`, `availableWidgets`, `renderWidgetContent`, prop.
- `src/App.tsx` — thread `relationships` prop.

---

# PHASE A — Visibility + beat-log

*Delivers the headline gap on its own: band, raw int, trend, last-seen, and beat history reach the player. OCEAN and claims fields ship empty.*

### Task 1: `DispositionBeat` model + constants

**Files:**
- Modify: `sidequest/game/disposition.py`
- Test: `tests/game/test_disposition_beat.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/game/test_disposition_beat.py`:

```python
from sidequest.game.disposition import (
    DISPOSITION_LOG_CAP,
    DispositionBeat,
)


def test_disposition_beat_fields():
    beat = DispositionBeat(turn=4, delta=3, reason="warmed by your candor", location="parlor")
    assert beat.turn == 4
    assert beat.delta == 3
    assert beat.reason == "warmed by your candor"
    assert beat.location == "parlor"


def test_disposition_beat_location_optional():
    beat = DispositionBeat(turn=1, delta=-2, reason="snubbed")
    assert beat.location is None


def test_disposition_log_cap_is_ten():
    assert DISPOSITION_LOG_CAP == 10
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/test_disposition_beat.py -v`
Expected: FAIL — `ImportError: cannot import name 'DispositionBeat'`.

- [ ] **Step 3: Add the model + constants**

In `sidequest/game/disposition.py`, near the top after the existing imports (the file already imports `BaseModel` for `AttitudeThresholds`), add:

```python
# Disposition beat-log (ADR-136). Persists the delta + reason the engine
# already computes at each disposition-shift site — rescuing data that today
# lives only in transient SPAN_DISPOSITION_SHIFT spans — so the relationship
# panel can show the *why* behind each shift (ADR-014 diamonds/coal: a
# relationship story, not a reputation bar).
DISPOSITION_LOG_CAP = 10


class DispositionBeat(BaseModel):
    """One persisted disposition shift: the delta the engine applied and why.

    ``reason`` is narrator-supplied (``update_npc_disposition``), the engagement
    tick label, or a neutral label for opaque patch/world paths. ``location`` is
    the party location at the time, or ``None`` when not in scope.
    """

    model_config = {"extra": "forbid"}

    turn: int
    delta: int
    reason: str
    location: str | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/test_disposition_beat.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/disposition.py sidequest-server/tests/game/test_disposition_beat.py
git commit -m "feat(adr-136): DispositionBeat model + log cap constant"
```

---

### Task 2: `Npc.disposition_log` field + `record_disposition_beat` seam + OTEL span

**Files:**
- Create: `sidequest/telemetry/spans/relationship.py`
- Modify: `sidequest/telemetry/spans/__init__.py` (export the new constants)
- Modify: `sidequest/game/session.py` (field + method on `Npc`)
- Test: `tests/game/test_disposition_beat.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `tests/game/test_disposition_beat.py`:

```python
from sidequest.game.creature_core import CreatureCore, HpPool, Inventory
from sidequest.game.session import Npc


def _npc(name: str = "Tabitha") -> Npc:
    return Npc(
        core=CreatureCore(
            name=name,
            description="A guest.",
            personality="Wry.",
            level=1,
            xp=0,
            inventory=Inventory(),
            statuses=[],
            hp=HpPool(current=10, max=10, base_max=10),
            acquired_advancements=[],
        )
    )


def test_record_beat_appends():
    npc = _npc()
    npc.record_disposition_beat(turn=2, delta=3, reason="candor", location="parlor")
    assert len(npc.disposition_log) == 1
    assert npc.disposition_log[0].delta == 3


def test_record_beat_skips_zero_delta():
    npc = _npc()
    npc.record_disposition_beat(turn=2, delta=0, reason="no change", location=None)
    assert npc.disposition_log == []


def test_record_beat_trims_to_cap():
    npc = _npc()
    for i in range(1, 16):
        npc.record_disposition_beat(turn=i, delta=1, reason=f"r{i}", location=None)
    assert len(npc.disposition_log) == DISPOSITION_LOG_CAP
    # oldest trimmed, newest kept
    assert npc.disposition_log[0].turn == 6
    assert npc.disposition_log[-1].turn == 15


def test_record_beat_emits_span():
    from sidequest.telemetry.spans import SPAN_RELATIONSHIP_BEAT_RECORDED

    assert SPAN_RELATIONSHIP_BEAT_RECORDED == "relationship.beat_recorded"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/test_disposition_beat.py -v`
Expected: FAIL — `AttributeError: 'Npc' object has no attribute 'record_disposition_beat'` / import error for the span.

- [ ] **Step 3: Create the span module**

Create `sidequest/telemetry/spans/relationship.py` (mirror the shape of `disposition.py` in the same package):

```python
"""Relationship-surface spans (ADR-136).

``relationship.beat_recorded`` confirms a disposition beat was appended to the
log (the GM-panel lie-detector: history is written, not improvised — CLAUDE.md
OTEL principle). ``relationships.emitted`` confirms a RELATIONSHIPS message was
broadcast.
"""

from sidequest.telemetry.spans.routes import SPAN_ROUTES, SpanRoute

SPAN_RELATIONSHIP_BEAT_RECORDED = "relationship.beat_recorded"
SPAN_RELATIONSHIPS_EMITTED = "relationships.emitted"

SPAN_ROUTES[SPAN_RELATIONSHIP_BEAT_RECORDED] = SpanRoute(
    event_type="state_transition",
    component="disposition",
    extract=lambda span: {
        "field": "relationship.beat_recorded",
        "npc_name": (span.attributes or {}).get("npc_name", ""),
        "delta": (span.attributes or {}).get("delta", 0),
        "reason": (span.attributes or {}).get("reason", ""),
        "turn": (span.attributes or {}).get("turn", 0),
        "log_size": (span.attributes or {}).get("log_size", 0),
    },
)

SPAN_ROUTES[SPAN_RELATIONSHIPS_EMITTED] = SpanRoute(
    event_type="state_transition",
    component="relationships",
    extract=lambda span: {
        "field": "relationships.emitted",
        "entry_count": (span.attributes or {}).get("entry_count", 0),
        "changed": bool((span.attributes or {}).get("changed", False)),
    },
)
```

> **Verify before writing:** open `sidequest/telemetry/spans/disposition.py` and confirm the import path for `SPAN_ROUTES`/`SpanRoute` (recon showed `disposition.py` references `SPAN_ROUTES` and `SpanRoute` directly). Match that file's import exactly — if it imports them from `sidequest.telemetry.spans` rather than `.routes`, use that form.

- [ ] **Step 4: Export the span constants**

In `sidequest/telemetry/spans/__init__.py`, find where `SPAN_DISPOSITION_SHIFT` / `Span` are re-exported and add alongside:

```python
from sidequest.telemetry.spans.relationship import (
    SPAN_RELATIONSHIP_BEAT_RECORDED,
    SPAN_RELATIONSHIPS_EMITTED,
)
```

Add both names to the module's `__all__` if one exists (match the existing pattern for `SPAN_DISPOSITION_SHIFT`).

- [ ] **Step 5: Add the field + seam to `Npc`**

In `sidequest/game/session.py`, add the import at the top alongside the existing `from sidequest.game.disposition import Disposition`:

```python
from sidequest.game.disposition import (
    DISPOSITION_LOG_CAP,
    Disposition,
    DispositionBeat,
)
```

In the `Npc` class (after the `belief_state` field, ~line 184), add the field:

```python
    # Disposition beat-log (ADR-136): bounded ring buffer of the delta + reason
    # behind each disposition shift, appended via record_disposition_beat at
    # every mutation site. Trend is derived from this, not stored.
    disposition_log: list[DispositionBeat] = Field(default_factory=list)
```

Add the method to `Npc` (after `name()`, ~line 212):

```python
    def record_disposition_beat(
        self,
        *,
        turn: int,
        delta: int,
        reason: str,
        location: str | None,
    ) -> None:
        """Append a disposition beat and trim to the cap.

        Zero-delta shifts earn no beat — a relationship beat is the *why* a
        standing moved, and nothing moved. Emits ``relationship.beat_recorded``
        so the GM panel can verify the history is engine-written, not narrator-
        improvised (ADR-136 / CLAUDE.md OTEL principle).
        """
        if delta == 0:
            return
        from sidequest.telemetry.spans import SPAN_RELATIONSHIP_BEAT_RECORDED, Span

        self.disposition_log.append(
            DispositionBeat(turn=turn, delta=delta, reason=reason, location=location)
        )
        if len(self.disposition_log) > DISPOSITION_LOG_CAP:
            del self.disposition_log[: len(self.disposition_log) - DISPOSITION_LOG_CAP]
        with Span.open(
            SPAN_RELATIONSHIP_BEAT_RECORDED,
            {
                "npc_name": self.core.name,
                "delta": int(delta),
                "reason": reason,
                "turn": int(turn),
                "log_size": len(self.disposition_log),
            },
        ):
            pass
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run pytest tests/game/test_disposition_beat.py -v`
Expected: PASS (7 tests). If the `CreatureCore`/`HpPool`/`Inventory` import path differs, fix the test helper import to match `sidequest/game/creature_core.py`.

- [ ] **Step 7: Commit**

```bash
git add sidequest-server/sidequest/telemetry/spans/ sidequest-server/sidequest/game/session.py sidequest-server/tests/game/test_disposition_beat.py
git commit -m "feat(adr-136): Npc.disposition_log + record_disposition_beat seam + OTEL span"
```

---

### Task 3: Wire the seam at site 1 — engagement tick

**Files:**
- Modify: `sidequest/game/npc_development.py` (reason constant)
- Modify: `sidequest/server/narration_apply.py:1704-1736` (call the seam)
- Test: `tests/server/test_relationship_beat_wiring.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/server/test_relationship_beat_wiring.py`:

```python
from sidequest.game.npc_development import ENGAGEMENT_BEAT_REASON, develop_npc_on_engagement
from tests.game.test_disposition_beat import _npc


def test_engagement_reason_constant():
    assert isinstance(ENGAGEMENT_BEAT_REASON, str) and ENGAGEMENT_BEAT_REASON


def test_engagement_then_beat_records_with_reason():
    # Mirror the narration_apply call site: tick, then record the beat.
    npc = _npc()
    before = int(npc.disposition)
    tick = develop_npc_on_engagement(npc)
    if tick.disposition_delta != 0:
        npc.record_disposition_beat(
            turn=7,
            delta=tick.disposition_delta,
            reason=ENGAGEMENT_BEAT_REASON,
            location="parlor",
        )
    assert int(npc.disposition) == before + 2  # DISPOSITION_DRIFT_PER_ENGAGEMENT
    assert npc.disposition_log[-1].reason == ENGAGEMENT_BEAT_REASON
    assert npc.disposition_log[-1].turn == 7
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/server/test_relationship_beat_wiring.py -v`
Expected: FAIL — `ImportError: cannot import name 'ENGAGEMENT_BEAT_REASON'`.

- [ ] **Step 3: Add the reason constant**

In `sidequest/game/npc_development.py`, near `DISPOSITION_DRIFT_PER_ENGAGEMENT` (line 44), add:

```python
# Label for the engagement-tick disposition beat (ADR-136). The interest tick
# is a small warm drift from continued player attention (ADR-014/ADR-020).
ENGAGEMENT_BEAT_REASON = "warmed by your continued attention"
```

- [ ] **Step 4: Call the seam at the engagement tick**

In `sidequest/server/narration_apply.py`, add the import to the existing `from sidequest.game.npc_development import develop_npc_on_engagement` (line 39):

```python
from sidequest.game.npc_development import ENGAGEMENT_BEAT_REASON, develop_npc_on_engagement
```

Inside the `if tick.disposition_delta != 0:` block (after the `SPAN_DISPOSITION_SHIFT` `with` block closes, ~line 1736), append the beat call. `actor_loc` is in scope from line 1677, `turn_num` from the enclosing function:

```python
                if tick.disposition_delta != 0:
                    with Span.open(
                        SPAN_DISPOSITION_SHIFT,
                        {
                            "npc_name": npc_hit.core.name,
                            "delta": tick.disposition_delta,
                            "before": tick.disposition_before,
                            "after": tick.disposition_after,
                            "before_attitude": tick.attitude_before,
                            "after_attitude": tick.attitude_after,
                            "crossed": tick.attitude_crossed,
                        },
                    ):
                        pass
                    # ADR-136: persist the why behind this shift.
                    npc_hit.record_disposition_beat(
                        turn=turn_num,
                        delta=tick.disposition_delta,
                        reason=ENGAGEMENT_BEAT_REASON,
                        location=actor_loc,
                    )
```

- [ ] **Step 5: Run test + lint**

Run: `uv run pytest tests/server/test_relationship_beat_wiring.py -v && uv run ruff check sidequest/server/narration_apply.py sidequest/game/npc_development.py`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/game/npc_development.py sidequest-server/sidequest/server/narration_apply.py sidequest-server/tests/server/test_relationship_beat_wiring.py
git commit -m "feat(adr-136): record disposition beat at engagement tick (site 1/4)"
```

---

### Task 4: Wire the seam at site 2 — `update_npc_disposition` tool

**Files:**
- Modify: `sidequest/agents/tools/update_npc_disposition.py:99-140`
- Test: `tests/server/test_relationship_beat_wiring.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `tests/server/test_relationship_beat_wiring.py`:

```python
import inspect

from sidequest.agents.tools import update_npc_disposition as tool_mod


def test_tool_records_beat_from_args_reason():
    """The tool handler must call record_disposition_beat with args.reason.

    Behavioral guard via source-structure is forbidden (CLAUDE.md). Instead we
    assert the handler references the seam by exercising it below in the
    OTEL-driven dispatch test (Task 11). Here we only confirm the handler still
    resolves the npc and computes a delta — a cheap smoke that the edit didn't
    break arg handling.
    """
    sig = inspect.signature(tool_mod.update_npc_disposition.fn)  # underlying coroutine
    assert "args" in sig.parameters and "ctx" in sig.parameters
```

> Note: this is a smoke test only. The real wiring proof is the OTEL-driven dispatch test in **Task 11**, which drives a tool call through the engine and asserts both the `relationship.beat_recorded` span and the emitted `RELATIONSHIPS` message. Per CLAUDE.md "No Source-Text Wiring Tests," we do not grep the handler body. If `update_npc_disposition.fn` is not the right accessor for the wrapped coroutine, adjust to however the `@tool` decorator exposes the callable (check the decorator in `sidequest/agents/tools/`).

- [ ] **Step 2: Run test to verify it fails or errors**

Run: `uv run pytest tests/server/test_relationship_beat_wiring.py::test_tool_records_beat_from_args_reason -v`
Expected: PASS or an `AttributeError` revealing the correct `.fn` accessor — fix the accessor, then it passes. (This task's substance is the edit below; the proof is Task 11.)

- [ ] **Step 3: Call the seam in the tool handler**

In `sidequest/agents/tools/update_npc_disposition.py`, after the mutation block (the lines computing `after_value`/`after_attitude`, ~line 119) and before `ctx.repository.save(snapshot)`, add:

```python
    after_value = npc.disposition.value
    after_attitude = npc.disposition.attitude().value

    # ADR-136: persist the why behind this narrator-declared shift. turn +
    # location are not passed to the tool; read them from the snapshot.
    turn_num = int(getattr(snapshot.turn_manager, "interaction", 0) or 0)
    location = snapshot.party_location(perspective=args.perspective_pc or None)
    npc.record_disposition_beat(
        turn=turn_num,
        delta=after_value - before_value,
        reason=args.reason,
        location=location,
    )

    ctx.repository.save(snapshot)
```

> `args.reason` already exists on `UpdateNpcDispositionArgs` (recon confirmed it's returned in the tool result). If `args` has no `reason` attribute, add `reason: str = ""` to `UpdateNpcDispositionArgs` in the same file and pass it through.

- [ ] **Step 4: Run test + lint**

Run: `uv run pytest tests/server/test_relationship_beat_wiring.py -v && uv run ruff check sidequest/agents/tools/update_npc_disposition.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/agents/tools/update_npc_disposition.py sidequest-server/tests/server/test_relationship_beat_wiring.py
git commit -m "feat(adr-136): record disposition beat in update_npc_disposition tool (site 2/4)"
```

---

### Task 5: Wire the seam at site 3 — `apply_patch` npc_attitudes

**Files:**
- Modify: `sidequest/game/session.py:1410-1446`
- Modify: `sidequest/game/disposition.py` (patch reason constant)
- Test: `tests/game/test_disposition_beat.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `tests/game/test_disposition_beat.py`:

```python
from sidequest.game.disposition import PATCH_BEAT_REASON


def test_patch_beat_reason_constant():
    assert isinstance(PATCH_BEAT_REASON, str) and PATCH_BEAT_REASON
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/test_disposition_beat.py::test_patch_beat_reason_constant -v`
Expected: FAIL — import error.

- [ ] **Step 3: Add the constant**

In `sidequest/game/disposition.py`, after `DISPOSITION_LOG_CAP`, add:

```python
# Neutral label for the apply_patch npc_attitudes path (ADR-136). A narrative
# patch carries a delta but no narrator reason — show the shift without
# inventing a specific cause (No Silent Fallbacks: an honest generic label).
PATCH_BEAT_REASON = "shifted by unfolding events"
```

- [ ] **Step 4: Call the seam in `apply_patch`**

In `sidequest/game/session.py`, inside the `npc_attitudes` loop (after the existing `SPAN_DISPOSITION_SHIFT` `with ... : pass` block, ~line 1446), append. Update the inline import to include `PATCH_BEAT_REASON`:

```python
        for name, delta in patch.npc_attitudes.items():
            for npc in self.npcs:
                if npc.core.name == name:
                    before = int(npc.disposition)
                    npc.disposition = Disposition(before + delta)
                    after = int(npc.disposition)
                    before_attitude = Disposition(before).attitude().value
                    after_attitude = npc.disposition.attitude().value
                    with Span.open(
                        SPAN_DISPOSITION_SHIFT,
                        {
                            "npc_name": name,
                            "delta": int(delta),
                            "before": before,
                            "after": after,
                            "before_attitude": before_attitude,
                            "after_attitude": after_attitude,
                            "crossed": before_attitude != after_attitude,
                        },
                    ):
                        pass
                    # ADR-136: persist the shift. Patch deltas carry no reason;
                    # use the neutral label. Effective delta (after-before)
                    # respects the ±100 clamp so a clamped no-op records nothing.
                    npc.record_disposition_beat(
                        turn=int(getattr(self.turn_manager, "interaction", 0) or 0),
                        delta=after - before,
                        reason=PATCH_BEAT_REASON,
                        location=self.party_location(),
                    )
```

Update the inline import at the top of this branch (~line 1411):

```python
        if patch.npc_attitudes is not None:
            from sidequest.game.disposition import PATCH_BEAT_REASON  # noqa: F401
            from sidequest.telemetry.spans import SPAN_DISPOSITION_SHIFT, Span
```

(If `PATCH_BEAT_REASON` is already importable at module top, skip the inline import and reference it directly.)

- [ ] **Step 5: Run tests + lint**

Run: `uv run pytest tests/game/test_disposition_beat.py -v && uv run ruff check sidequest/game/session.py`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/game/session.py sidequest-server/sidequest/game/disposition.py sidequest-server/tests/game/test_disposition_beat.py
git commit -m "feat(adr-136): record disposition beat in apply_patch npc_attitudes (site 3/4)"
```

---

### Task 6: Wire the seam at site 4 — chapter upsert (existing-NPC delta only)

**Files:**
- Modify: `sidequest/game/world_materialization.py:479-514`
- Test: `tests/game/test_disposition_beat.py` (extend)

**Design decision (deviation from spec, logged here):** A chapter upsert sets an *absolute* authored disposition. On **first materialization** (new NPC) this is the starting baseline — not a shift, so it earns no beat. Only the **existing-NPC** branch, where a chapter advances and an already-known NPC's standing actually moves, records a beat. This matches the spec's intent ("history of *why standing moved*"). The zero-delta guard in the seam covers the no-change case.

- [ ] **Step 1: Write the failing test**

Append to `tests/game/test_disposition_beat.py`:

```python
def test_chapter_upsert_existing_npc_records_delta(monkeypatch):
    """When a chapter moves an already-known NPC's disposition, log the delta."""
    npc = _npc("McCoy")
    npc.disposition = __import__(
        "sidequest.game.disposition", fromlist=["Disposition"]
    ).Disposition(10)
    # Simulate the existing-branch logic: new absolute value 16 → delta +6.
    new_value = 16
    delta = new_value - int(npc.disposition)
    npc.record_disposition_beat(
        turn=3, delta=delta, reason="world_chapter_upsert", location=npc.location
    )
    assert npc.disposition_log[-1].delta == 6
    assert npc.disposition_log[-1].reason == "world_chapter_upsert"
```

(This validates the recording shape the production edit will use; the production behavior is exercised by the materialization integration test in Task 17.)

- [ ] **Step 2: Run test to verify it passes structurally**

Run: `uv run pytest tests/game/test_disposition_beat.py::test_chapter_upsert_existing_npc_records_delta -v`
Expected: PASS (the seam already exists). The substance of this task is the production edit below.

- [ ] **Step 3: Call the seam in `_apply_npc` (existing branch only)**

In `sidequest/game/world_materialization.py`, in `_apply_npc`, the existing-NPC branch (~line 500-503) currently reads:

```python
    if existing is not None:
        if npc_data.disposition is not None:
            existing.disposition = int(npc_data.disposition)
```

Replace with:

```python
    if existing is not None:
        if npc_data.disposition is not None:
            before = int(existing.disposition)
            existing.disposition = int(npc_data.disposition)
            after = int(existing.disposition)
            # ADR-136: a chapter that moves an already-known NPC's standing is a
            # relationship beat. The new-NPC branch below sets a baseline (no
            # shift), so it records nothing. Zero-delta no-ops are dropped by the
            # seam's guard.
            existing.record_disposition_beat(
                turn=int(getattr(snap.turn_manager, "interaction", 0) or 0),
                delta=after - before,
                reason="world_chapter_upsert",
                location=npc_data.location or existing.location,
            )
```

> `existing.disposition = int(...)` relies on `Disposition`'s int-coercion schema hook (recon confirmed) — keep the `int()` to match the existing line. `snap.turn_manager` is read defensively because materialization can run pre-turn-loop (recon line 651 uses the same `getattr` idiom).

- [ ] **Step 4: Run tests + lint**

Run: `uv run pytest tests/game/test_disposition_beat.py -v && uv run ruff check sidequest/game/world_materialization.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/world_materialization.py sidequest-server/tests/game/test_disposition_beat.py
git commit -m "feat(adr-136): record disposition beat on chapter upsert of known NPC (site 4/4)"
```

---

### Task 7: Builder pure functions — `band_for`, `trend_for`

**Files:**
- Create: `sidequest/game/projection/relationships.py`
- Test: `tests/game/test_relationships_builder.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/game/test_relationships_builder.py`:

```python
from sidequest.game.disposition import DispositionBeat
from sidequest.game.projection.relationships import band_for, trend_for


def test_band_thresholds():
    assert band_for(80) == "Devoted"
    assert band_for(50) == "Devoted"
    assert band_for(49) == "Warm"
    assert band_for(10) == "Warm"
    assert band_for(9) == "Neutral"
    assert band_for(0) == "Neutral"
    assert band_for(-9) == "Neutral"
    assert band_for(-10) == "Cool"
    assert band_for(-49) == "Cool"
    assert band_for(-50) == "Hostile"
    assert band_for(-100) == "Hostile"


def test_trend_up_flat_down():
    up = [DispositionBeat(turn=1, delta=2, reason="a"), DispositionBeat(turn=2, delta=1, reason="b")]
    down = [DispositionBeat(turn=1, delta=-3, reason="a")]
    assert trend_for(up) == "up"
    assert trend_for(down) == "down"
    assert trend_for([]) == "flat"


def test_trend_windows_last_k():
    beats = [
        DispositionBeat(turn=1, delta=-10, reason="old"),  # outside window
        DispositionBeat(turn=2, delta=1, reason="x"),
        DispositionBeat(turn=3, delta=1, reason="y"),
        DispositionBeat(turn=4, delta=1, reason="z"),
    ]
    assert trend_for(beats, k=3) == "up"  # last 3 sum +3, ignores the -10
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/test_relationships_builder.py -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Create the builder module with the two functions**

Create `sidequest/game/projection/relationships.py`:

```python
"""Relationship payload builder (ADR-136).

Converts engine NPC state (``snapshot.npcs``) into protocol ``RelationshipEntry``
payloads. Presentation logic (the 5-level display band, trend derivation,
personality read) lives here, keeping the engine ``Attitude`` enum and
``OceanProfile`` untouched. The claims-only firewall (Phase C) is applied here at
build time — disposition/OCEAN/claims are global, so there is no per-recipient
projection fork.
"""

from __future__ import annotations

from sidequest.game.disposition import DispositionBeat

# 5-level DISPLAY band (ADR-136). Distinct from the engine 3-level Attitude enum.
_TREND_WINDOW = 3


def band_for(value: int) -> str:
    """Map a raw disposition value (-100..+100) to the 5-level display band."""
    if value >= 50:
        return "Devoted"
    if value >= 10:
        return "Warm"
    if value > -10:
        return "Neutral"
    if value > -50:
        return "Cool"
    return "Hostile"


def trend_for(beats: list[DispositionBeat], k: int = _TREND_WINDOW) -> str:
    """Derive trend from the sign of the summed deltas in the recent window."""
    recent = beats[-k:]
    total = sum(b.delta for b in recent)
    if total > 0:
        return "up"
    if total < 0:
        return "down"
    return "flat"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/test_relationships_builder.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/projection/relationships.py sidequest-server/tests/game/test_relationships_builder.py
git commit -m "feat(adr-136): relationship builder band + trend derivation"
```

---

### Task 8: Protocol — message type, payloads, message class, registration

**Files:**
- Modify: `sidequest/protocol/enums.py`
- Modify: `sidequest/protocol/models.py`
- Modify: `sidequest/protocol/messages.py`
- Modify: `sidequest/server/session_handler.py`
- Test: `tests/protocol/test_relationships_message.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/protocol/test_relationships_message.py`:

```python
from sidequest.protocol.enums import MessageType
from sidequest.protocol.messages import RelationshipsMessage
from sidequest.protocol.models import (
    DispositionBeatPayload,
    RelationshipEntry,
    RelationshipsPayload,
)


def test_relationships_message_roundtrip():
    entry = RelationshipEntry(
        name="Tabitha",
        portrait_url=None,
        band="Warm",
        disposition=24,
        trend="up",
        last_seen_turn=6,
        last_seen_location="parlor",
        beats=[DispositionBeatPayload(turn=6, delta=3, reason="candor", location="parlor")],
        personality_read=None,
        ocean=None,
        claims=[],
    )
    msg = RelationshipsMessage(payload=RelationshipsPayload(entries=[entry]))
    assert msg.type == MessageType.RELATIONSHIPS
    dumped = msg.model_dump(mode="json")
    assert dumped["type"] == "RELATIONSHIPS"
    assert dumped["payload"]["entries"][0]["band"] == "Warm"
    # round-trip back through the model
    again = RelationshipsMessage.model_validate(dumped)
    assert again.payload.entries[0].disposition == 24
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/protocol/test_relationships_message.py -v`
Expected: FAIL — import errors.

- [ ] **Step 3: Add the message type**

In `sidequest/protocol/enums.py`, in the `MessageType` enum (next to `LOCATION_DESCRIPTION`, line ~117), add:

```python
    # ADR-136: player-facing relationship surface (reactive, per-domain).
    RELATIONSHIPS = "RELATIONSHIPS"
```

- [ ] **Step 4: Add the payload models**

In `sidequest/protocol/models.py`, near `LocationDescriptionPayload`, add (these are payload-local — they must NOT import `game.DispositionBeat` or `genre.OceanProfile`; `protocol` is a leaf):

```python
class DispositionBeatPayload(BaseModel):
    """One disposition shift surfaced to the player (ADR-136)."""

    model_config = {"extra": "forbid"}

    turn: int
    delta: int
    reason: str
    location: str | None = None


class RelationshipClaimPayload(BaseModel):
    """A claim-to-party + coarse credibility hint (ADR-136 claims firewall)."""

    model_config = {"extra": "forbid"}

    text: str
    credibility_hint: str


class RelationshipEntry(BaseModel):
    """One NPC's player-visible relationship state (ADR-136).

    ``band`` is the 5-level display label; ``disposition`` is the raw reveal.
    ``ocean`` is an OceanProfile dump (full keys, 0..10) or None. ``personality_read``
    and ``claims`` are empty until Phases B/C.
    """

    model_config = {"extra": "forbid"}

    name: str
    portrait_url: str | None = None
    band: str
    disposition: int
    trend: str
    last_seen_turn: int
    last_seen_location: str | None = None
    beats: list[DispositionBeatPayload] = Field(default_factory=list)
    personality_read: str | None = None
    ocean: dict[str, float] | None = None
    claims: list[RelationshipClaimPayload] = Field(default_factory=list)


class RelationshipsPayload(BaseModel):
    """Full relationship roster snapshot (ADR-136)."""

    model_config = {"extra": "forbid"}

    entries: list[RelationshipEntry] = Field(default_factory=list)
```

> Confirm `BaseModel` and `Field` are already imported at the top of `models.py` (they are — `LocationDescriptionPayload` uses both).

- [ ] **Step 5: Add the message class + union member**

In `sidequest/protocol/messages.py`, near `LocationDescriptionMessage` (line ~1254), add:

```python
class RelationshipsMessage(ProtocolBase):
    """GameMessage::Relationships — player-facing relationship roster (ADR-136).

    Emitted reactively when the relationship set changes (a disposition shift, a
    new NPC promoted into the stateful roster, or a claim recorded) — not every
    turn (Cost Scales with Drama). Global payload, broadcast to all seated PCs.
    """

    type: Literal[MessageType.RELATIONSHIPS] = MessageType.RELATIONSHIPS
    payload: RelationshipsPayload
    player_id: str = ""
```

Add `RelationshipsPayload` to the imports from `sidequest.protocol.models` at the top of `messages.py` (alongside `LocationDescriptionPayload`). Then add `RelationshipsMessage` to the `_Phase1Variant` union (the discriminated union near line 1444 — find where `LocationDescriptionMessage` is listed and add `| RelationshipsMessage`).

- [ ] **Step 6: Register in `_KIND_TO_MESSAGE_CLS`**

In `sidequest/server/session_handler.py`, find `_KIND_TO_MESSAGE_CLS` (recon ~line 100-130) and add:

```python
    "RELATIONSHIPS": RelationshipsMessage,
```

Add the import for `RelationshipsMessage` at the top of `session_handler.py` next to the other message-class imports.

- [ ] **Step 7: Run test to verify it passes**

Run: `uv run pytest tests/protocol/test_relationships_message.py -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add sidequest-server/sidequest/protocol/ sidequest-server/sidequest/server/session_handler.py sidequest-server/tests/protocol/test_relationships_message.py
git commit -m "feat(adr-136): RELATIONSHIPS message type, payloads, message class + registration"
```

---

### Task 9: `build_relationship_entries` (Phase A fields)

**Files:**
- Modify: `sidequest/game/projection/relationships.py`
- Test: `tests/game/test_relationships_builder.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `tests/game/test_relationships_builder.py`:

```python
from sidequest.game.disposition import Disposition
from sidequest.game.projection.relationships import build_relationship_entries
from tests.game.test_disposition_beat import _npc


def _snapshot_with(npcs):
    class _Snap:
        pass

    s = _Snap()
    s.npcs = npcs
    return s


def test_build_entries_phase_a_fields():
    npc = _npc("Tabitha")
    npc.disposition = Disposition(24)
    npc.last_seen_turn = 6
    npc.last_seen_location = "parlor"
    npc.record_disposition_beat(turn=6, delta=3, reason="candor", location="parlor")

    entries = build_relationship_entries(_snapshot_with([npc]))
    assert len(entries) == 1
    e = entries[0]
    assert e.name == "Tabitha"
    assert e.band == "Warm"
    assert e.disposition == 24
    assert e.trend == "up"
    assert e.last_seen_turn == 6
    assert e.last_seen_location == "parlor"
    assert len(e.beats) == 1 and e.beats[0].reason == "candor"
    # Phase A: OCEAN + claims empty
    assert e.ocean is None
    assert e.personality_read is None
    assert e.claims == []


def test_build_entries_empty_roster():
    assert build_relationship_entries(_snapshot_with([])) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/test_relationships_builder.py -v`
Expected: FAIL — `build_relationship_entries` undefined.

- [ ] **Step 3: Implement the builder**

Append to `sidequest/game/projection/relationships.py`:

```python
from typing import Any

from sidequest.protocol.models import (
    DispositionBeatPayload,
    RelationshipEntry,
)


def build_relationship_entries(snapshot: Any) -> list[RelationshipEntry]:
    """Build one RelationshipEntry per NPC in ``snapshot.npcs``.

    Phase A: band/disposition/trend/last-seen/beats. OCEAN (Phase B) and claims
    (Phase C) ship empty here and are populated by later phases.
    """
    entries: list[RelationshipEntry] = []
    for npc in snapshot.npcs:
        value = int(npc.disposition)
        beats = [
            DispositionBeatPayload(
                turn=b.turn, delta=b.delta, reason=b.reason, location=b.location
            )
            for b in npc.disposition_log
        ]
        entries.append(
            RelationshipEntry(
                name=npc.core.name,
                portrait_url=None,  # Phase A: no portrait wiring (absence shown as absence)
                band=band_for(value),
                disposition=value,
                trend=trend_for(npc.disposition_log),
                last_seen_turn=npc.last_seen_turn,
                last_seen_location=npc.last_seen_location,
                beats=beats,
                personality_read=None,
                ocean=None,
                claims=[],
            )
        )
    return entries
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/test_relationships_builder.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/projection/relationships.py sidequest-server/tests/game/test_relationships_builder.py
git commit -m "feat(adr-136): build_relationship_entries (Phase A fields)"
```

---

### Task 10: Reactive emitter `_maybe_emit_relationships` + change-gate

**Files:**
- Create: `sidequest/server/websocket_handlers/relationships_emit.py`
- Test: `tests/server/test_relationships_emit.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/server/test_relationships_emit.py` (mirror the canonical fixture-driven emit test shape from `tests/server/test_location_description_emit.py`):

```python
from sidequest.game.disposition import Disposition
from sidequest.protocol.messages import RelationshipsMessage
from sidequest.server.websocket_handlers.relationships_emit import (
    _maybe_emit_relationships,
    _relationships_signature,
)
from tests.game.test_disposition_beat import _npc


class _Snap:
    def __init__(self, npcs):
        self.npcs = npcs


class _Handler:
    pass


def test_signature_changes_with_disposition():
    npc = _npc("Tabitha")
    npc.disposition = Disposition(10)
    sig1 = _relationships_signature(_Snap([npc]))
    npc.disposition = Disposition(20)
    sig2 = _relationships_signature(_Snap([npc]))
    assert sig1 != sig2


def test_emit_sends_message_when_changed():
    npc = _npc("Tabitha")
    npc.disposition = Disposition(24)
    npc.record_disposition_beat(turn=6, delta=3, reason="candor", location="parlor")
    handler = _Handler()
    sent = []

    def emit_fn(msg, kind):
        sent.append((msg, kind))

    _maybe_emit_relationships(handler, snapshot=_Snap([npc]), emit_fn=emit_fn)
    assert len(sent) == 1
    msg, kind = sent[0]
    assert kind == "RELATIONSHIPS"
    assert isinstance(msg, RelationshipsMessage)
    assert msg.payload.entries[0].name == "Tabitha"


def test_emit_skipped_when_unchanged():
    npc = _npc("Tabitha")
    npc.disposition = Disposition(24)
    handler = _Handler()
    sent = []

    def emit_fn(msg, kind):
        sent.append((msg, kind))

    _maybe_emit_relationships(handler, snapshot=_Snap([npc]), emit_fn=emit_fn)
    _maybe_emit_relationships(handler, snapshot=_Snap([npc]), emit_fn=emit_fn)
    assert len(sent) == 1  # second call unchanged → skipped


def test_emit_skipped_when_no_npcs():
    handler = _Handler()
    sent = []
    _maybe_emit_relationships(handler, snapshot=_Snap([]), emit_fn=lambda m, k: sent.append(m))
    assert sent == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/server/test_relationships_emit.py -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement the emitter**

Create `sidequest/server/websocket_handlers/relationships_emit.py`:

```python
"""Reactive RELATIONSHIPS emitter (ADR-136).

Mirrors map_emit.py's _maybe_emit_location_description: build a global payload
and broadcast via emit_fn. Change-gated on a lightweight per-roster signature so
the message fires only when the relationship set actually changes (a disposition
shift, a new NPC, a new beat/claim) — Cost Scales with Drama. The payload is the
same for every recipient (disposition/OCEAN/claims are global), so it broadcasts
directly rather than running the per-recipient projection chain.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from sidequest.game.projection.relationships import build_relationship_entries
from sidequest.protocol.messages import RelationshipsMessage
from sidequest.protocol.models import RelationshipsPayload

logger = logging.getLogger(__name__)

_SIG_ATTR = "_last_relationships_sig"


def _relationships_signature(snapshot: Any) -> str:
    """Cheap change signature: name, disposition, log size, claim count per NPC."""
    parts: list[str] = []
    for npc in snapshot.npcs:
        claim_count = sum(
            1 for b in getattr(npc.belief_state, "beliefs", []) if getattr(b, "variant", "") == "claim"
        )
        parts.append(
            f"{npc.core.name}:{int(npc.disposition)}:{len(npc.disposition_log)}:{claim_count}"
        )
    return "|".join(parts)


def _maybe_emit_relationships(
    handler: Any,
    *,
    snapshot: Any,
    emit_fn: Callable[[Any, str], None],
) -> None:
    """Emit a RELATIONSHIPS message when the roster signature changes.

    No NPCs → nothing to show (silent; not an error state). Unchanged signature
    → skip (Cost Scales with Drama).
    """
    if not snapshot.npcs:
        return

    sig = _relationships_signature(snapshot)
    if getattr(handler, _SIG_ATTR, None) == sig:
        return

    entries = build_relationship_entries(snapshot)
    msg = RelationshipsMessage(payload=RelationshipsPayload(entries=entries))

    from sidequest.telemetry.spans import SPAN_RELATIONSHIPS_EMITTED, Span

    with Span.open(
        SPAN_RELATIONSHIPS_EMITTED,
        {"entry_count": len(entries), "changed": True},
    ):
        pass
    logger.info("relationships.emitted entries=%d", len(entries))

    setattr(handler, _SIG_ATTR, sig)
    emit_fn(msg, "RELATIONSHIPS")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/server/test_relationships_emit.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/server/websocket_handlers/relationships_emit.py sidequest-server/tests/server/test_relationships_emit.py
git commit -m "feat(adr-136): reactive RELATIONSHIPS emitter with change-gate"
```

---

### Task 11: Wire the emitter into the turn loop + resume; OTEL wiring test

**Files:**
- Modify: `sidequest/server/websocket_session_handler.py`
- Test: `tests/server/test_relationship_beat_wiring.py` (extend — the load-bearing OTEL wiring test)

- [ ] **Step 1: Write the failing wiring test**

Append to `tests/server/test_relationship_beat_wiring.py`. This drives a real disposition shift through the production emitter path and asserts both the beat span and the emitted message — the behavior-not-source wiring proof (CLAUDE.md):

```python
from sidequest.game.disposition import Disposition
from sidequest.server.websocket_handlers.relationships_emit import _maybe_emit_relationships
from tests.game.test_disposition_beat import _npc


class _Snap:
    def __init__(self, npcs):
        self.npcs = npcs


def test_real_shift_then_emit_carries_beat(capture_spans):
    """A recorded beat fires relationship.beat_recorded AND reaches the message."""
    npc = _npc("Teague")
    npc.disposition = Disposition(8)
    npc.record_disposition_beat(turn=4, delta=2, reason="shared a drink", location="bar")

    # beat_recorded span fired during record_disposition_beat
    assert any(s.name == "relationship.beat_recorded" for s in capture_spans.spans)

    sent = []
    handler = type("H", (), {})()
    _maybe_emit_relationships(handler, snapshot=_Snap([npc]), emit_fn=lambda m, k: sent.append(m))
    assert sent and sent[0].payload.entries[0].beats[0].reason == "shared a drink"
    assert any(s.name == "relationships.emitted" for s in capture_spans.spans)
```

> Use the project's existing span-capture fixture. Find it: `grep -rn "def capture_spans\|InMemorySpanExporter\|capture_spans" tests/conftest.py tests/`. If the fixture has a different name (e.g. `otel_spans`, `span_capture`), use that. If none exists, the canonical pattern is an `InMemorySpanExporter` wired to the tracer in a fixture — copy from whichever disposition/scenario test already asserts spans.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/server/test_relationship_beat_wiring.py -v`
Expected: FAIL until the fixture name is correct; once correct, this test should already pass against Task 2/10 code (it exercises the seam + emitter directly). The production wiring below is what connects it to live turns.

- [ ] **Step 3: Wire the emitter into the turn loop + resume**

In `sidequest/server/websocket_session_handler.py`, add the import next to the `_maybe_emit_location_description` import (line ~150):

```python
from sidequest.server.websocket_handlers.relationships_emit import _maybe_emit_relationships
```

At **each** site where `_maybe_emit_location_description(...)` is called in the turn-apply/resume flow (recon: lines ~1901 and ~1941), add a sibling call immediately after, using the same `emit_fn`/`snapshot` in scope at that site:

```python
                        _maybe_emit_location_description(
                            self, sd=sd, snapshot=snapshot, actor=actor, emit_fn=emit_fn
                        )
                        # ADR-136: relationship roster rides the same post-apply
                        # / resume cadence as the location snapshot.
                        _maybe_emit_relationships(self, snapshot=snapshot, emit_fn=emit_fn)
```

> Match the exact local variable names at each call site (`snapshot` may be `sd.snapshot` or a local — copy whatever the adjacent `_maybe_emit_location_description` call passes). The emitter only needs `snapshot` + `emit_fn`; it reads the change-signature off `self` (the handler).

- [ ] **Step 4: Run the full beat + emit + wiring suite**

Run: `uv run pytest tests/server/test_relationship_beat_wiring.py tests/server/test_relationships_emit.py tests/game/test_disposition_beat.py -v && uv run ruff check sidequest/server/websocket_session_handler.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/server/websocket_session_handler.py sidequest-server/tests/server/test_relationship_beat_wiring.py
git commit -m "feat(adr-136): wire RELATIONSHIPS emitter into turn loop + resume (OTEL wiring test)"
```

---

### Task 12 (UI): MessageType const + payload types

**Files:**
- Modify: `src/types/protocol.ts`
- Modify: `src/types/payloads.ts`

- [ ] **Step 1: Add the message type**

In `sidequest-ui/src/types/protocol.ts`, in the `MessageType` const (next to `LOCATION_DESCRIPTION`, line 79):

```typescript
  RELATIONSHIPS: "RELATIONSHIPS",
```

- [ ] **Step 2: Add the payload types**

In `sidequest-ui/src/types/payloads.ts`, near `LocationDescriptionPayload` (line ~769), add (mirror `RelationshipEntry` from the server exactly):

```typescript
export interface DispositionBeatPayload {
  turn: number;
  delta: number;
  reason: string;
  location: string | null;
}

export interface RelationshipClaimPayload {
  text: string;
  credibility_hint: string;
}

export interface RelationshipEntryPayload {
  name: string;
  portrait_url: string | null;
  band: string;
  disposition: number;
  trend: string;
  last_seen_turn: number;
  last_seen_location: string | null;
  beats: DispositionBeatPayload[];
  personality_read: string | null;
  ocean: Record<string, number> | null;
  claims: RelationshipClaimPayload[];
}

export interface RelationshipsPayload {
  entries: RelationshipEntryPayload[];
}
```

Add the message interface to the `TypedGameMessage` union (find where `LocationDescriptionMessage` is declared, ~line 548-571):

```typescript
export interface RelationshipsMessage extends BaseMessage {
  type: typeof MessageType.RELATIONSHIPS;
  payload: RelationshipsPayload;
}
```

Add `| RelationshipsMessage` to the `TypedGameMessage` union.

- [ ] **Step 3: Verify the build compiles**

Run: `cd sidequest-ui && npx tsc --noEmit`
Expected: no new errors.

- [ ] **Step 4: Commit**

```bash
git add sidequest-ui/src/types/protocol.ts sidequest-ui/src/types/payloads.ts
git commit -m "feat(adr-136): UI RELATIONSHIPS message + payload types"
```

---

### Task 13 (UI): State slice + mirror handler

**Files:**
- Modify: `src/providers/GameStateProvider.tsx`
- Modify: `src/hooks/useStateMirror.ts`
- Test: `src/hooks/__tests__/useStateMirror.relationships.test.ts` (create)

- [ ] **Step 1: Write the failing test**

Create `sidequest-ui/src/hooks/__tests__/useStateMirror.relationships.test.ts` (mirror an existing useStateMirror test; find one with `grep -rln "useStateMirror" src/hooks/__tests__/`). Minimal shape:

```typescript
import { describe, expect, it } from "vitest";
import { applyMessage, initialClientState } from "@/hooks/useStateMirror";
import { MessageType } from "@/types/protocol";

describe("useStateMirror — RELATIONSHIPS", () => {
  it("replaces relationships from a RELATIONSHIPS message", () => {
    const state = initialClientState();
    const next = applyMessage(state, {
      type: MessageType.RELATIONSHIPS,
      payload: {
        entries: [
          {
            name: "Tabitha",
            portrait_url: null,
            band: "Warm",
            disposition: 24,
            trend: "up",
            last_seen_turn: 6,
            last_seen_location: "parlor",
            beats: [],
            personality_read: null,
            ocean: null,
            claims: [],
          },
        ],
      },
    } as never);
    expect(next.relationships?.[0].name).toBe("Tabitha");
  });
});
```

> Adjust `applyMessage`/`initialClientState` to the actual exported reducer/helpers in `useStateMirror.ts`. If the hook does not export a pure reducer, model the test on the closest existing useStateMirror test and use its harness.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-ui && npx vitest run src/hooks/__tests__/useStateMirror.relationships.test.ts`
Expected: FAIL — `relationships` not on state.

- [ ] **Step 3: Add the state slice**

In `src/providers/GameStateProvider.tsx`, in `ClientGameState` (line ~60-80), add:

```typescript
  /** ADR-136: player-facing NPC relationship roster (full replace per message). */
  relationships?: RelationshipEntryPayload[] | null;
```

Import `RelationshipEntryPayload` from `@/types/payloads` at the top.

- [ ] **Step 4: Add the mirror handler**

In `src/hooks/useStateMirror.ts`, alongside the `LOCATION_DESCRIPTION` handler (line ~204-242), add:

```typescript
      // ADR-136: full replace of the relationship roster.
      if (msg.type === MessageType.RELATIONSHIPS) {
        const payload = msg.payload as unknown as RelationshipsPayload;
        relationships = payload.entries;
        continue;
      }
```

Declare `relationships` in the reducer's working state next to `currentLocation` (init from the prior state, e.g. `let relationships = prev.relationships ?? null;`) and include it in the returned state object. Import `RelationshipsPayload` from `@/types/payloads`.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd sidequest-ui && npx vitest run src/hooks/__tests__/useStateMirror.relationships.test.ts`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add sidequest-ui/src/providers/GameStateProvider.tsx sidequest-ui/src/hooks/useStateMirror.ts sidequest-ui/src/hooks/__tests__/useStateMirror.relationships.test.ts
git commit -m "feat(adr-136): UI relationships state slice + mirror handler"
```

---

### Task 14 (UI): `RelationshipsPanel` + widget adapter + registry entry

**Files:**
- Create: `src/components/RelationshipsPanel.tsx`
- Create: `src/components/GameBoard/widgets/RelationshipsWidget.tsx`
- Modify: `src/components/GameBoard/widgetRegistry.ts`
- Test: `src/components/__tests__/RelationshipsPanel.test.tsx` (create)

- [ ] **Step 1: Write the failing test**

Create `sidequest-ui/src/components/__tests__/RelationshipsPanel.test.tsx` (model on `LocationPanel.test.tsx`):

```typescript
import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { RelationshipsPanel } from "@/components/RelationshipsPanel";
import type { RelationshipEntryPayload } from "@/types/payloads";

const entry: RelationshipEntryPayload = {
  name: "Tabitha",
  portrait_url: null,
  band: "Warm",
  disposition: 24,
  trend: "up",
  last_seen_turn: 6,
  last_seen_location: "parlor",
  beats: [{ turn: 6, delta: 3, reason: "warmed by your candor", location: "parlor" }],
  personality_read: null,
  ocean: null,
  claims: [],
};

describe("RelationshipsPanel", () => {
  it("renders the band by default, hides the raw number", () => {
    render(<RelationshipsPanel data={[entry]} />);
    expect(screen.getByText("Tabitha")).toBeInTheDocument();
    expect(screen.getByText(/warm/i)).toBeInTheDocument();
    expect(screen.queryByText("24")).not.toBeInTheDocument();
  });

  it("reveals the raw disposition and beats on expand", () => {
    render(<RelationshipsPanel data={[entry]} />);
    fireEvent.click(screen.getByRole("button", { name: /tabitha/i }));
    expect(screen.getByText(/24/)).toBeInTheDocument();
    expect(screen.getByText(/warmed by your candor/i)).toBeInTheDocument();
  });

  it("renders a loading state when data is null", () => {
    render(<RelationshipsPanel data={null} />);
    expect(screen.getByText(/no one yet/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-ui && npx vitest run src/components/__tests__/RelationshipsPanel.test.tsx`
Expected: FAIL — component does not exist.

- [ ] **Step 3: Implement the panel**

Create `src/components/RelationshipsPanel.tsx` (copy the FOLIO palette + font constants and the null-state idiom from `src/components/LocationPanel.tsx`):

```tsx
import { useState } from "react";
import { useGenreTheme } from "@/hooks/useGenreTheme";
import type { RelationshipEntryPayload } from "@/types/payloads";

// FOLIO semantic palette + fonts — mirror LocationPanel.tsx (no hardcoded colors;
// EB Garamond body, display font for names only).
const FONT_BODY = "'EB Garamond', serif";

interface RelationshipsPanelProps {
  data: RelationshipEntryPayload[] | null;
}

const TREND_ARROW: Record<string, string> = { up: "↗", flat: "→", down: "↘" };

export function RelationshipsPanel({ data }: RelationshipsPanelProps) {
  const theme = useGenreTheme();
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  if (!data || data.length === 0) {
    return (
      <div style={{ fontFamily: FONT_BODY, padding: "1rem", color: theme.colors.textMuted }}>
        No one yet. People you meet and engage will appear here.
      </div>
    );
  }

  const sorted = [...data].sort((a, b) => b.last_seen_turn - a.last_seen_turn);

  const toggle = (name: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });

  return (
    <div style={{ fontFamily: FONT_BODY, padding: "0.5rem" }}>
      {sorted.map((e) => {
        const isOpen = expanded.has(e.name);
        return (
          <div
            key={e.name}
            style={{ borderBottom: `1px solid ${theme.colors.border}`, padding: "0.5rem 0" }}
          >
            <button
              type="button"
              onClick={() => toggle(e.name)}
              aria-expanded={isOpen}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                width: "100%",
                background: "none",
                border: "none",
                cursor: "pointer",
                color: theme.colors.text,
                fontFamily: FONT_BODY,
                textAlign: "left",
              }}
            >
              <span style={{ fontWeight: 600, flex: 1 }}>{e.name}</span>
              <span style={{ color: theme.colors.textMuted }}>{e.band}</span>
              <span aria-label={`trend ${e.trend}`}>{TREND_ARROW[e.trend] ?? "→"}</span>
            </button>
            {isOpen && (
              <div style={{ padding: "0.5rem 0 0 0.5rem", color: theme.colors.textMuted }}>
                <div>
                  Standing: <strong>{e.disposition}</strong> ({e.band})
                </div>
                {e.last_seen_location && (
                  <div>
                    Last seen: {e.last_seen_location} (turn {e.last_seen_turn})
                  </div>
                )}
                {e.beats.length > 0 && (
                  <div style={{ marginTop: "0.5rem" }}>
                    <div style={{ fontWeight: 600 }}>History</div>
                    <ul style={{ margin: "0.25rem 0", paddingLeft: "1rem" }}>
                      {e.beats
                        .slice()
                        .reverse()
                        .map((b, i) => (
                          <li key={`${b.turn}-${i}`}>
                            {b.reason} ({b.delta > 0 ? `+${b.delta}` : b.delta})
                          </li>
                        ))}
                    </ul>
                  </div>
                )}
                {/* Phase B inserts personality_read here; Phase C inserts claims here. */}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
```

> Match `useGenreTheme`'s actual color accessors (`theme.colors.text`, etc.) to the real hook — open `src/hooks/useGenreTheme.ts` and `LocationPanel.tsx` and copy whatever palette keys LocationPanel uses. If LocationPanel uses inline FOLIO constants rather than `useGenreTheme`, mirror that instead.

- [ ] **Step 4: Create the thin widget adapter**

Create `src/components/GameBoard/widgets/RelationshipsWidget.tsx`:

```tsx
import { RelationshipsPanel } from "@/components/RelationshipsPanel";
import type { RelationshipEntryPayload } from "@/types/payloads";

interface RelationshipsWidgetProps {
  data: RelationshipEntryPayload[] | null;
}

// Thin adapter mirroring LocationWidget — GameBoard threads data, not styling.
export function RelationshipsWidget({ data }: RelationshipsWidgetProps) {
  return <RelationshipsPanel data={data} />;
}
```

- [ ] **Step 5: Register the widget**

In `src/components/GameBoard/widgetRegistry.ts`, add `"relationships"` to the `WidgetId` union (line ~16-25) and add the registry entry (mirror the `knowledge` entry, `dataGated: true`):

```typescript
  relationships: {
    id: "relationships",
    label: "Relationships",
    hotkey: "r",
    minW: 3,
    minH: 3,
    defaultW: 4,
    defaultH: 5,
    closable: true,
    dataGated: true,
  },
```

> Confirm `r` isn't already a hotkey in the registry; if taken, pick a free key.

- [ ] **Step 6: Run test to verify it passes**

Run: `cd sidequest-ui && npx vitest run src/components/__tests__/RelationshipsPanel.test.tsx`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add sidequest-ui/src/components/RelationshipsPanel.tsx sidequest-ui/src/components/GameBoard/widgets/RelationshipsWidget.tsx sidequest-ui/src/components/GameBoard/widgetRegistry.ts sidequest-ui/src/components/__tests__/RelationshipsPanel.test.tsx
git commit -m "feat(adr-136): RelationshipsPanel + widget adapter + registry entry"
```

---

### Task 15 (UI): GameBoard wiring + App prop thread + integration test

**Files:**
- Modify: `src/components/GameBoard/GameBoard.tsx`
- Modify: `src/App.tsx`
- Test: `src/components/GameBoard/__tests__/GameBoard-relationships-tab.test.tsx` (create)

- [ ] **Step 1: Write the failing integration test**

Create `sidequest-ui/src/components/GameBoard/__tests__/GameBoard-relationships-tab.test.tsx` (model on `GameBoard-location-tab.test.tsx`):

```typescript
import { describe, expect, it } from "vitest";

describe("GameBoard — relationships widget wiring", () => {
  it("RelationshipsWidget is importable from the registered path", async () => {
    const mod = await import("@/components/GameBoard/widgets/RelationshipsWidget");
    expect(typeof mod.RelationshipsWidget).toBe("function");
  });

  it("widgetRegistry includes the 'relationships' entry with dataGated:true", async () => {
    const mod = await import("@/components/GameBoard/widgetRegistry");
    const entry = (mod.WIDGET_REGISTRY as Record<string, { dataGated?: boolean }>).relationships;
    expect(entry).toBeDefined();
    expect(entry!.dataGated).toBe(true);
  });
});
```

Then add a rendering test that mounts GameBoard with `relationshipsData` and asserts the tab appears (copy the `renderBoard` harness from `GameBoard-location-tab.test.tsx`, adding a `relationshipsData` prop to its props object):

```typescript
describe("GameBoard — relationships tab rendering", () => {
  it("shows the Relationships tab when relationshipsData is present", () => {
    renderBoard({
      relationshipsData: [
        {
          name: "Tabitha",
          portrait_url: null,
          band: "Warm",
          disposition: 24,
          trend: "up",
          last_seen_turn: 6,
          last_seen_location: "parlor",
          beats: [],
          personality_read: null,
          ocean: null,
          claims: [],
        },
      ],
    });
    expect(screen.getByRole("tab", { name: /relationships/i })).toBeInTheDocument();
  });

  it("does NOT show the Relationships tab when relationshipsData is null", () => {
    renderBoard({ relationshipsData: null });
    expect(screen.queryByRole("tab", { name: /relationships/i })).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-ui && npx vitest run src/components/GameBoard/__tests__/GameBoard-relationships-tab.test.tsx`
Expected: FAIL — `relationshipsData` prop not threaded; tab not available.

- [ ] **Step 3: Thread the prop + gate + render case**

In `src/components/GameBoard/GameBoard.tsx`:

1. Add to the props interface (next to `currentLocation`): `relationshipsData?: RelationshipEntryPayload[] | null;` and import the type from `@/types/payloads`.
2. In `rightGroupOrder` (line ~637-645), add `"relationships"` after `"character"`:

```typescript
    const rightGroupOrder: WidgetId[] = [
      "character",
      "relationships",
      "inventory",
      "map",
      "location",
      "knowledge",
      "gallery",
      "audio",
    ];
```

3. In `availableWidgets` (line ~306-330), add the gate:

```typescript
    if (relationshipsData != null && relationshipsData.length > 0) {
      available.add("relationships");
    }
```

(Add `relationshipsData` to the `useMemo` dependency array.)

4. In `renderWidgetContent` (line ~430-498), add the case and the dep:

```typescript
      case "relationships":
        return relationshipsData ? <RelationshipsWidget data={relationshipsData} /> : null;
```

(Add `relationshipsData` to that `useCallback` dependency array; import `RelationshipsWidget`.)

- [ ] **Step 4: Thread the prop from App**

In `src/App.tsx`, in the `<GameBoard ...>` element (line ~2182), next to `currentLocation={gameState.currentLocation ?? null}` (line 2198), add:

```tsx
                relationshipsData={gameState.relationships ?? null}
```

- [ ] **Step 5: Run tests + build**

Run: `cd sidequest-ui && npx vitest run src/components/GameBoard/__tests__/GameBoard-relationships-tab.test.tsx && npx tsc --noEmit`
Expected: PASS, no type errors.

- [ ] **Step 6: Commit**

```bash
git add sidequest-ui/src/components/GameBoard/GameBoard.tsx sidequest-ui/src/App.tsx sidequest-ui/src/components/GameBoard/__tests__/GameBoard-relationships-tab.test.tsx
git commit -m "feat(adr-136): wire relationships widget into GameBoard + App (integration test)"
```

**Phase A checkpoint:** Run `just server-check` and `just client-test`. The relationship surface is live end-to-end with band/int/trend/last-seen/beats. This is independently shippable and closes the headline playtest gap.

---

# PHASE B — OCEAN personality

*Materializes authored OCEAN onto runtime NPCs (normalized), adds a narrative personality read by default and the numeric profile on a further expand.*

### Task 16: `OceanProfile.from_authored` normalizer

**Files:**
- Modify: `sidequest/genre/models/ocean.py`
- Test: `tests/game/test_ocean_normalize.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/game/test_ocean_normalize.py`:

```python
import pytest

from sidequest.genre.models.ocean import OceanProfile


def test_from_authored_short_keys_scaled():
    # authored 0..1 short keys → runtime 0..10 full keys
    p = OceanProfile.from_authored({"O": 0.5, "C": 0.7, "E": 0.4, "A": 0.5, "N": 0.4})
    assert p.openness == 5.0
    assert p.conscientiousness == 7.0
    assert p.extraversion == 4.0
    assert p.agreeableness == 5.0
    assert p.neuroticism == 4.0


def test_from_authored_missing_dimension_defaults_to_center():
    p = OceanProfile.from_authored({"O": 1.0})
    assert p.openness == 10.0
    assert p.conscientiousness == 5.0  # default center


def test_from_authored_unknown_key_raises():
    with pytest.raises(ValueError):
        OceanProfile.from_authored({"X": 0.5})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/test_ocean_normalize.py -v`
Expected: FAIL — `from_authored` undefined.

- [ ] **Step 3: Implement the normalizer**

In `sidequest/genre/models/ocean.py`, add a classmethod to `OceanProfile`:

```python
    _AUTHORED_KEY_MAP = {
        "O": "openness",
        "C": "conscientiousness",
        "E": "extraversion",
        "A": "agreeableness",
        "N": "neuroticism",
    }

    @classmethod
    def from_authored(cls, authored: dict[str, float]) -> "OceanProfile":
        """Normalize an authored OCEAN dict (short keys, 0..1) to a runtime profile.

        Authored content uses short keys (``O/C/E/A/N``) on a 0..1 scale (ADR-042
        / #318). Runtime ``OceanProfile`` uses full keys on 0..10. Unknown keys
        raise — a typo in authored content is an authoring error, not a silent
        default (No Silent Fallbacks). Missing dimensions keep the 5.0 center.
        """
        kwargs: dict[str, float] = {}
        for key, raw in authored.items():
            if key not in cls._AUTHORED_KEY_MAP:
                raise ValueError(
                    f"ocean: unknown authored key {key!r}; expected one of "
                    f"{sorted(cls._AUTHORED_KEY_MAP)}"
                )
            kwargs[cls._AUTHORED_KEY_MAP[key]] = float(raw) * 10.0
        return cls(**kwargs)
```

> `_AUTHORED_KEY_MAP` is a plain class attribute, not a pydantic field — pydantic v2 ignores non-annotated class attributes, so this is safe alongside the model fields. If pydantic complains, move the map to a module-level constant `_AUTHORED_KEY_MAP` above the class and reference it.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/test_ocean_normalize.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/genre/models/ocean.py sidequest-server/tests/game/test_ocean_normalize.py
git commit -m "feat(adr-136): OceanProfile.from_authored normalizer (0..1 short keys → 0..10)"
```

---

### Task 17: Wire the normalizer into the materializer

**Files:**
- Modify: `sidequest/game/world_materialization.py:868`
- Test: `tests/game/test_ocean_normalize.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `tests/game/test_ocean_normalize.py`:

```python
def test_preload_normalizes_authored_ocean():
    from sidequest.genre.models.authored_npc import AuthoredNpc
    from sidequest.game.world_materialization import preload_authored_npcs

    class _State:
        def __init__(self):
            self.npcs = []
            self.characters = []
            self.genre_slug = "tea_and_murder"
            self.world_slug = "the_real_mccoy"

    state = _State()
    authored = [
        AuthoredNpc(
            id="tabitha",
            name="Tabitha",
            ocean={"O": 0.5, "C": 0.7, "E": 0.4, "A": 0.5, "N": 0.4},
        )
    ]
    preload_authored_npcs(state, authored)
    assert len(state.npcs) == 1
    ocean = state.npcs[0].ocean
    # normalized to full-key 0..10 OceanProfile dump
    assert ocean["openness"] == 5.0
    assert ocean["conscientiousness"] == 7.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/test_ocean_normalize.py::test_preload_normalizes_authored_ocean -v`
Expected: FAIL — `ocean["openness"]` KeyError (still the raw short-key dict).

- [ ] **Step 3: Normalize at the seeding point**

In `sidequest/game/world_materialization.py`, in `preload_authored_npcs`, add the import near the top of the function body and change the `ocean=` seeding line (line ~868). Replace:

```python
            ocean=authored_npc.ocean,
```

with:

```python
            ocean=(
                OceanProfile.from_authored(authored_npc.ocean).model_dump()
                if authored_npc.ocean
                else None
            ),
```

Add the import at the top of `world_materialization.py` (or inline in the function, matching the file's import style):

```python
from sidequest.genre.models.ocean import OceanProfile
```

> NPCs with no authored OCEAN keep `ocean=None` — absence shown as absence (the panel renders no personality read for them). This matches the 72-9 narrator-invented path's contract.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/test_ocean_normalize.py -v && uv run ruff check sidequest/game/world_materialization.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/world_materialization.py sidequest-server/tests/game/test_ocean_normalize.py
git commit -m "feat(adr-136): normalize authored OCEAN onto runtime NPCs at materialization"
```

---

### Task 18: `personality_read` descriptor

**Files:**
- Modify: `sidequest/game/projection/relationships.py`
- Test: `tests/game/test_relationships_builder.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `tests/game/test_relationships_builder.py`:

```python
from sidequest.game.projection.relationships import personality_read


def test_personality_read_none_for_no_profile():
    assert personality_read(None) is None


def test_personality_read_picks_salient_traits():
    # extraversion very high, agreeableness very low → outgoing + abrasive
    read = personality_read(
        {"openness": 5.0, "conscientiousness": 5.0, "extraversion": 9.0,
         "agreeableness": 1.0, "neuroticism": 5.0}
    )
    assert read is not None
    assert "outgoing" in read.lower()
    assert "abrasive" in read.lower() or "blunt" in read.lower()


def test_personality_read_flat_profile_is_balanced():
    read = personality_read(
        {"openness": 5.0, "conscientiousness": 5.0, "extraversion": 5.0,
         "agreeableness": 5.0, "neuroticism": 5.0}
    )
    assert read is not None and "even-keeled" in read.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/test_relationships_builder.py -k personality -v`
Expected: FAIL — `personality_read` undefined.

- [ ] **Step 3: Implement `personality_read`**

Append to `sidequest/game/projection/relationships.py`:

```python
# Narrative descriptors per OCEAN dimension at the high / low pole (ADR-040
# narrative read; the numeric profile is the reveal detail).
_OCEAN_DESCRIPTORS: dict[str, tuple[str, str]] = {
    "openness": ("curious and imaginative", "conventional and grounded"),
    "conscientiousness": ("disciplined and reliable", "careless and impulsive"),
    "extraversion": ("outgoing and warm", "reserved and private"),
    "agreeableness": ("gracious and trusting", "abrasive and blunt"),
    "neuroticism": ("anxious and volatile", "calm and steady"),
}


def personality_read(ocean: dict[str, float] | None) -> str | None:
    """Narrative personality read from an OceanProfile dump (full keys, 0..10).

    Picks the up-to-two most salient dimensions (furthest from the 5.0 center,
    distance >= 2.0). A flat profile reads as even-keeled. None in, None out —
    absence is shown as absence, never a fabricated personality.
    """
    if not ocean:
        return None
    scored = sorted(
        ((dim, val - 5.0) for dim, val in ocean.items() if dim in _OCEAN_DESCRIPTORS),
        key=lambda kv: abs(kv[1]),
        reverse=True,
    )
    salient = [(dim, dist) for dim, dist in scored if abs(dist) >= 2.0][:2]
    if not salient:
        return "Even-keeled and hard to read."
    phrases = [
        _OCEAN_DESCRIPTORS[dim][0] if dist > 0 else _OCEAN_DESCRIPTORS[dim][1]
        for dim, dist in salient
    ]
    return f"{'; '.join(phrases).capitalize()}."
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/test_relationships_builder.py -k personality -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/projection/relationships.py sidequest-server/tests/game/test_relationships_builder.py
git commit -m "feat(adr-136): personality_read OCEAN descriptor"
```

---

### Task 19: Builder populates `ocean` + `personality_read`

**Files:**
- Modify: `sidequest/game/projection/relationships.py`
- Test: `tests/game/test_relationships_builder.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `tests/game/test_relationships_builder.py`:

```python
def test_build_entries_populates_ocean_and_read():
    npc = _npc("Tabitha")
    npc.disposition = Disposition(24)
    npc.ocean = {
        "openness": 5.0, "conscientiousness": 7.0, "extraversion": 9.0,
        "agreeableness": 1.0, "neuroticism": 4.0,
    }
    e = build_relationship_entries(_snapshot_with([npc]))[0]
    assert e.ocean == npc.ocean
    assert e.personality_read is not None and "outgoing" in e.personality_read.lower()


def test_build_entries_no_ocean_keeps_none():
    npc = _npc("Stranger")
    assert npc.ocean is None
    e = build_relationship_entries(_snapshot_with([npc]))[0]
    assert e.ocean is None
    assert e.personality_read is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/test_relationships_builder.py -k "ocean or read" -v`
Expected: FAIL — builder still hardcodes `ocean=None`.

- [ ] **Step 3: Populate the fields in the builder**

In `build_relationship_entries`, replace the hardcoded `personality_read=None` and `ocean=None` lines with:

```python
                personality_read=personality_read(npc.ocean),
                ocean=npc.ocean,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/test_relationships_builder.py -v`
Expected: PASS (all builder tests).

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/projection/relationships.py sidequest-server/tests/game/test_relationships_builder.py
git commit -m "feat(adr-136): builder populates OCEAN + personality_read"
```

---

### Task 20 (UI): Panel shows personality read + numeric OCEAN reveal

**Files:**
- Modify: `src/components/RelationshipsPanel.tsx`
- Test: `src/components/__tests__/RelationshipsPanel.test.tsx` (extend)

- [ ] **Step 1: Write the failing test**

Append to `src/components/__tests__/RelationshipsPanel.test.tsx`:

```typescript
it("shows personality read on expand and numeric OCEAN on further expand", () => {
  const withOcean: RelationshipEntryPayload = {
    ...entry,
    personality_read: "Outgoing and warm; disciplined and reliable.",
    ocean: { openness: 5, conscientiousness: 7, extraversion: 9, agreeableness: 5, neuroticism: 4 },
  };
  render(<RelationshipsPanel data={[withOcean]} />);
  fireEvent.click(screen.getByRole("button", { name: /tabitha/i }));
  expect(screen.getByText(/outgoing and warm/i)).toBeInTheDocument();
  // numeric profile hidden until further expand
  expect(screen.queryByText(/extraversion/i)).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /personality|show traits|ocean/i }));
  expect(screen.getByText(/extraversion/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-ui && npx vitest run src/components/__tests__/RelationshipsPanel.test.tsx`
Expected: FAIL — personality read / OCEAN not rendered.

- [ ] **Step 3: Add personality read + OCEAN reveal**

In `RelationshipsPanel.tsx`, add per-row OCEAN-expand state and render the read inside the expanded block (replace the `{/* Phase B inserts... */}` comment). Add near the top of the component:

```tsx
  const [oceanOpen, setOceanOpen] = useState<Set<string>>(new Set());
  const toggleOcean = (name: string) =>
    setOceanOpen((prev) => {
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });
```

Inside the expanded block, where the Phase B comment was:

```tsx
                {e.personality_read && (
                  <div style={{ marginTop: "0.5rem" }}>
                    <div style={{ fontWeight: 600 }}>Personality</div>
                    <div>{e.personality_read}</div>
                    {e.ocean && (
                      <>
                        <button
                          type="button"
                          onClick={() => toggleOcean(e.name)}
                          aria-expanded={oceanOpen.has(e.name)}
                          style={{
                            background: "none",
                            border: "none",
                            cursor: "pointer",
                            color: theme.colors.textMuted,
                            fontFamily: FONT_BODY,
                            padding: "0.25rem 0",
                            textDecoration: "underline",
                          }}
                        >
                          {oceanOpen.has(e.name) ? "Hide traits" : "Show traits"}
                        </button>
                        {oceanOpen.has(e.name) && (
                          <ul style={{ margin: 0, paddingLeft: "1rem" }}>
                            {Object.entries(e.ocean).map(([dim, val]) => (
                              <li key={dim}>
                                {dim}: {val.toFixed(1)}
                              </li>
                            ))}
                          </ul>
                        )}
                      </>
                    )}
                  </div>
                )}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-ui && npx vitest run src/components/__tests__/RelationshipsPanel.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-ui/src/components/RelationshipsPanel.tsx sidequest-ui/src/components/__tests__/RelationshipsPanel.test.tsx
git commit -m "feat(adr-136): panel shows personality read + numeric OCEAN reveal"
```

**Phase B checkpoint:** `just server-check && just client-test`. OCEAN now materializes and reads through the panel.

---

# PHASE C — Claims-to-party (the spoiler firewall)

*Surfaces what NPCs have claimed, filtered to `Claim` entries only. `Fact`/`Suspicion` (the mystery solution) never cross.*

### Task 21: `claims_to_party` firewall + spoiler-guard test

**Files:**
- Modify: `sidequest/game/projection/relationships.py`
- Test: `tests/game/test_relationships_claims_firewall.py` (create)

- [ ] **Step 1: Write the failing (load-bearing) test**

Create `tests/game/test_relationships_claims_firewall.py`:

```python
from sidequest.game.belief_state import (
    BeliefClaim,
    BeliefFact,
    BeliefState,
    BeliefSuspicion,
    BeliefSourceToldBy,
    Credibility,
)
from sidequest.game.projection.relationships import claims_to_party


def test_only_claims_cross_the_firewall():
    bs = BeliefState(
        beliefs=[
            BeliefFact(subject="murder", content="SECRET: the butler did it",
                       source=BeliefSourceToldBy(by="self")),
            BeliefSuspicion.make(subject="murder", content="SECRET: I suspect the maid",
                                 turn_learned=1, source=BeliefSourceToldBy(by="self"),
                                 confidence=0.6),
            BeliefClaim(subject="alibi", content="I was in the garden all evening",
                        source=BeliefSourceToldBy(by="Tabitha"), believed=True),
        ],
        credibility_scores={"Tabitha": Credibility.new(0.8)},
    )
    claims = claims_to_party(bs)
    texts = [c["text"] for c in claims]
    assert "I was in the garden all evening" in texts
    # the firewall is load-bearing: NO secret crosses
    assert not any("SECRET" in t for t in texts)
    assert len(claims) == 1


def test_credibility_hint_buckets():
    bs = BeliefState(
        beliefs=[
            BeliefClaim(subject="x", content="trusted claim",
                        source=BeliefSourceToldBy(by="Trusted"), believed=True),
            BeliefClaim(subject="y", content="dubious claim",
                        source=BeliefSourceToldBy(by="Shady"), believed=False),
        ],
        credibility_scores={
            "Trusted": Credibility.new(0.9),
            "Shady": Credibility.new(0.1),
        },
    )
    by_text = {c["text"]: c["credibility_hint"] for c in claims_to_party(bs)}
    assert by_text["trusted claim"] == "credible"
    assert by_text["dubious claim"] == "doubtful"
```

> Confirm the `BeliefFact` constructor signature — recon showed `subject`, `content`, `turn_learned=0`, `source`. Adjust the test's kwargs if a field is required without a default.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/test_relationships_claims_firewall.py -v`
Expected: FAIL — `claims_to_party` undefined.

- [ ] **Step 3: Implement the firewall**

Append to `sidequest/game/projection/relationships.py`:

```python
def _credibility_hint(claim: Any, belief_state: Any) -> str:
    """Coarse credibility bucket for a claim.

    Prefer the credibility score of the claim's source NPC (when told_by);
    fall back to the claim's own ``believed`` flag.
    """
    source = claim.source
    score: float | None = None
    if getattr(source, "kind", "") == "told_by":
        cred = belief_state.credibility_scores.get(source.by)
        if cred is not None:
            score = cred.score
    if score is None:
        return "credible" if claim.believed else "doubtful"
    if score >= 0.66:
        return "credible"
    if score >= 0.33:
        return "uncertain"
    return "doubtful"


def claims_to_party(belief_state: Any) -> list[dict]:
    """Filter belief_state to Claim entries only — the spoiler firewall (ADR-136).

    Fact and Suspicion entries are the mystery's solution (ADR-053) and are
    dropped entirely. Only Claim entries (statements in the NPC's knowledge,
    sourced from others) cross, each with a coarse credibility hint.
    """
    out: list[dict] = []
    for belief in belief_state.beliefs:
        if getattr(belief, "variant", "") != "claim":
            continue
        out.append(
            {"text": belief.content, "credibility_hint": _credibility_hint(belief, belief_state)}
        )
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/test_relationships_claims_firewall.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/projection/relationships.py sidequest-server/tests/game/test_relationships_claims_firewall.py
git commit -m "feat(adr-136): claims-only belief firewall + spoiler guard test"
```

---

### Task 22: Builder populates `claims`

**Files:**
- Modify: `sidequest/game/projection/relationships.py`
- Test: `tests/game/test_relationships_builder.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `tests/game/test_relationships_builder.py`:

```python
def test_build_entries_populates_claims():
    from sidequest.game.belief_state import BeliefClaim, BeliefSourceToldBy

    npc = _npc("Tabitha")
    npc.belief_state.beliefs.append(
        BeliefClaim(subject="alibi", content="I was in the garden",
                    source=BeliefSourceToldBy(by="Tabitha"), believed=True)
    )
    e = build_relationship_entries(_snapshot_with([npc]))[0]
    assert len(e.claims) == 1
    assert e.claims[0].text == "I was in the garden"
    assert e.claims[0].credibility_hint  # non-empty
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/test_relationships_builder.py::test_build_entries_populates_claims -v`
Expected: FAIL — builder hardcodes `claims=[]`.

- [ ] **Step 3: Populate claims in the builder**

In `build_relationship_entries`, add the import at the top of the module (alongside the existing `RelationshipEntry`/`DispositionBeatPayload` import):

```python
from sidequest.protocol.models import (
    DispositionBeatPayload,
    RelationshipClaimPayload,
    RelationshipEntry,
)
```

Replace `claims=[]` with:

```python
                claims=[
                    RelationshipClaimPayload(text=c["text"], credibility_hint=c["credibility_hint"])
                    for c in claims_to_party(npc.belief_state)
                ],
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/test_relationships_builder.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/projection/relationships.py sidequest-server/tests/game/test_relationships_builder.py
git commit -m "feat(adr-136): builder populates claims-to-party"
```

---

### Task 23 (UI): Panel shows claims + credibility hints

**Files:**
- Modify: `src/components/RelationshipsPanel.tsx`
- Test: `src/components/__tests__/RelationshipsPanel.test.tsx` (extend)

- [ ] **Step 1: Write the failing test**

Append to `src/components/__tests__/RelationshipsPanel.test.tsx`:

```typescript
it("shows claims with credibility hints on expand", () => {
  const withClaims: RelationshipEntryPayload = {
    ...entry,
    claims: [{ text: "I was in the garden all evening", credibility_hint: "credible" }],
  };
  render(<RelationshipsPanel data={[withClaims]} />);
  fireEvent.click(screen.getByRole("button", { name: /tabitha/i }));
  expect(screen.getByText(/i was in the garden all evening/i)).toBeInTheDocument();
  expect(screen.getByText(/credible/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-ui && npx vitest run src/components/__tests__/RelationshipsPanel.test.tsx`
Expected: FAIL — claims not rendered.

- [ ] **Step 3: Render claims in the expanded block**

In `RelationshipsPanel.tsx`, after the personality block inside the expanded `<div>`, add:

```tsx
                {e.claims.length > 0 && (
                  <div style={{ marginTop: "0.5rem" }}>
                    <div style={{ fontWeight: 600 }}>Told the party</div>
                    <ul style={{ margin: "0.25rem 0", paddingLeft: "1rem" }}>
                      {e.claims.map((c, i) => (
                        <li key={i}>
                          “{c.text}”{" "}
                          <span style={{ color: theme.colors.textMuted, fontStyle: "italic" }}>
                            ({c.credibility_hint})
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-ui && npx vitest run src/components/__tests__/RelationshipsPanel.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-ui/src/components/RelationshipsPanel.tsx sidequest-ui/src/components/__tests__/RelationshipsPanel.test.tsx
git commit -m "feat(adr-136): panel shows claims-to-party with credibility hints"
```

---

### Task 24: End-to-end claims firewall wiring test

**Files:**
- Test: `tests/server/test_relationships_emit.py` (extend)

- [ ] **Step 1: Write the test**

Append to `tests/server/test_relationships_emit.py`:

```python
def test_emitted_message_carries_claims_never_secrets():
    from sidequest.game.belief_state import (
        BeliefClaim,
        BeliefFact,
        BeliefSourceToldBy,
    )
    from tests.game.test_disposition_beat import _npc

    npc = _npc("Tabitha")
    npc.disposition = Disposition(24)
    npc.belief_state.beliefs.extend([
        BeliefFact(subject="murder", content="SECRET: the butler did it",
                   source=BeliefSourceToldBy(by="self")),
        BeliefClaim(subject="alibi", content="I was in the garden",
                    source=BeliefSourceToldBy(by="Tabitha"), believed=True),
    ])
    sent = []
    handler = type("H", (), {})()
    _maybe_emit_relationships(handler, snapshot=_Snap([npc]), emit_fn=lambda m, k: sent.append(m))

    entry = sent[0].payload.entries[0]
    claim_texts = [c.text for c in entry.claims]
    assert "I was in the garden" in claim_texts
    assert not any("SECRET" in t for t in claim_texts)
```

- [ ] **Step 2: Run test to verify it passes**

Run: `uv run pytest tests/server/test_relationships_emit.py -v`
Expected: PASS — the firewall holds end-to-end through the emitter.

- [ ] **Step 3: Commit**

```bash
git add sidequest-server/tests/server/test_relationships_emit.py
git commit -m "test(adr-136): end-to-end claims firewall — secrets never reach the message"
```

**Phase C checkpoint:** `just check-all`. Update `docs/adr/136-player-facing-relationship-surface.md` frontmatter `implementation-status: deferred` → `accepted`/`live` (or per the project's convention) and rerun `scripts/regenerate_adr_indexes.py`.

---

## Self-Review

**Spec coverage:**
- Goal 1 (panel: standing/band+number, trend, last-seen, beat history, personality read, claims) → Tasks 7–15 (A), 16–20 (B), 21–24 (C). ✓
- Goal 2 (reuse: disposition/OCEAN/belief/reactive-messaging/firewall/dockview) → builder reuses `Disposition`/`OceanProfile`/`BeliefState`; emitter mirrors `LOCATION_DESCRIPTION`; panel uses the documented 5-step dockview registration + `useGenreTheme`. ✓
- Goal 3 (never leak mystery solutions) → Task 21 spoiler-guard + Task 24 end-to-end. ✓
- Beat-log at all shift sites → Tasks 3–6 enumerate all **four** (spec implied three). ✓
- OCEAN scale normalization → Tasks 16–17 (corrects the spec's "wire seeding": the materializer already copies, in the wrong shape). ✓
- Hybrid disclosure → band default (Task 14), int+beats expand (Task 14), personality read + numeric OCEAN further expand (Task 20). ✓
- Mandatory UI integration test (server payload → mirror → panel) → Task 13 (mirror) + Task 15 (mounted in GameBoard). ✓
- OTEL wiring (behavior, not source-grep) → Task 2 (`relationship.beat_recorded`), Task 10 (`relationships.emitted`), Task 11 (span-driven wiring test). ✓

**Type consistency:** `RelationshipEntry` fields are identical across server (`protocol/models.py`, Task 8) and UI (`RelationshipEntryPayload`, Task 12): `name, portrait_url, band, disposition, trend, last_seen_turn, last_seen_location, beats, personality_read, ocean, claims`. `DispositionBeatPayload`/`RelationshipClaimPayload` match on both sides. `build_relationship_entries` constructs exactly these. `record_disposition_beat` keyword signature (`turn, delta, reason, location`) is identical at all four call sites and in its tests. ✓

**Placeholder scan:** No `TBD`/"handle appropriately"/"similar to Task N". Every code step has complete code. The few "confirm X before writing" notes point at real accessors to verify (span import path, `@tool` `.fn` accessor, `useGenreTheme` palette keys, span-capture fixture name) — these are verification instructions, not placeholders, and each has a concrete fallback. ✓

**Dependency direction:** payload models live in leaf `protocol/`; builder in `game/` imports `protocol` (allowed); no `protocol → game/genre` import. ✓

**Deviations from spec logged inline:** four sites not three (Tasks 3–6); `develop_npc_on_engagement` module location (Task 3); OCEAN already-copied-wrong-shape (Task 17); firewall at build-time not per-recipient stage (Task 10 + Refinements §4); site-4 scoped to existing-NPC delta (Task 6). These belong in the Architect spec-reconcile manifest when this work is run through the pipeline.
