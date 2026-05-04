# Snapshot Split-Brain Wave 2A — NPC Pool / NPC State Split — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve S2 from the snapshot split-brain audit (`docs/superpowers/specs/2026-05-04-snapshot-split-brain-cleanup-design.md`): split today's `NpcRegistryEntry` (which fuses identity, last-seen tracking, and legacy hp/max_hp combat stats) into two purpose-built types — `NpcPoolMember` (identity-only, regenerable, drawn from name-generators × archetypes × culture corpus per ADR-091) and the existing `Npc` (stateful encountered NPC, gaining `pool_origin` and `last_seen_*` fields). Drop `GameSnapshot.npc_registry`. Migrate legacy saves on load. Emit `npc.referenced` OTEL span on every narrator NPC cite so Sebastien's GM panel can detect "did the narrator pull from the pool or invent?" — the lie-detector goal.

**Scope boundary (read carefully):** This plan delivers the **types, migration, projection, and OTEL infrastructure**. It does **NOT** deliver proactive pool population at world-bind (the spec mentions "name generators × archetype tables × culture corpus per ADR-091, generated at world-bind"). Today, `npc_registry` is populated reactively — narrator-mentions-name → entry appears. Wave 2A preserves that reactive lifecycle (now writing to `npc_pool`); proactive pool seeding is a deliberate follow-up story (see "Wave 2A Follow-up: pool seeding" in this plan's Open Questions). 8 points cover the split, not the seeding.

**Architecture:**

- **Two new types, one removed.** `NpcRegistryEntry` (`game/session.py:159-183`) is deleted. In its place, `NpcPoolMember` (identity-only, fields: `name, role, pronouns, appearance, archetype_id, drawn_from`) lives in a new module. The existing `Npc` model (`game/session.py:110-157`) gains three fields: `pool_origin: str | None` (provenance — name of the pool member it was promoted from, or `None` for narrator-invented NPCs), `last_seen_location: str | None`, `last_seen_turn: int = 0`.
- **GameSnapshot field swap.** `npc_registry: list[NpcRegistryEntry]` (`game/session.py:519`) is replaced with `npc_pool: list[NpcPoolMember]`. The existing `npcs: list[Npc]` field is unchanged in declaration; its members gain three new fields via the model change above.
- **Reactive narration_apply path.** `narration_apply.py:1440-1510` is rewritten with a 3-step lookup: (1) match name in `snapshot.npcs` → update `last_seen_*` on the `Npc`; (2) match name in `snapshot.npc_pool` → done, narrator cited a known pool member; (3) no match → append `NpcPoolMember(name=X, drawn_from="narrator_invented", pool_origin=None on future Npc)` and emit `npc.invented`. Pool members are not auto-promoted to `Npc` — promotion happens only when combat handshake publishes stats (existing path; that path now writes a real `Npc` with `core.edge` instead of legacy `hp/max_hp` on registry).
- **Pool members are re-citable, not consumed.** A pool member stays in `npc_pool` after first reference. When the same NPC actually engages mechanically (combat, dialog with persistent state), an `Npc` is created with `pool_origin = pool_member.name`. Subsequent narrator references to that name match step (1) — `Npc` lookup — and shadow the pool. The pool entry remains harmless; can be reaped on a future-cleanup story if telemetry shows pool bloat.
- **Chassis fold removed.** `chassis.py:179-190`'s `_project_chassis_to_npc_entry()` is deleted, and `chassis.py:272`'s append into `npc_registry` is dropped. Chassis project into the narrator prompt via the existing dedicated zone (`prompt_framework/core.py:423-483` — `register_chassis_voice_section`); they never appear in `npc_pool`. Verified safe: no other site reads chassis-as-NPC from the registry.
- **Prompt projection (gaslight preserved).** `prompt_framework/core.py:370-421`'s `register_npc_roster_section` is rewritten to project a unified "people who exist in this world" zone fed from BOTH `npc_pool` (identity-only blocks) and `snapshot.npcs` (identity + `last_seen_*` lines when present). Format remains identical to today's per-entry shape from the narrator's perspective — gaslight discipline preserved by the projection layer, not by the storage shape.
- **Migration on load.** A new `_migrate_s2_npc_registry_split(out: dict) -> dict | None` sub-function in `sidequest-server/sidequest/game/migrations.py` runs alongside Wave 1's `_migrate_s1_world_confrontations`. For each legacy `npc_registry` entry: if a matching `Npc` (by case-folded name) exists in `npcs`, merge `last_seen_location/last_seen_turn` onto the `Npc` and (if hp/max_hp set) log a span attribute that legacy combat stats were dropped (the `Npc.core.edge` path is canonical now; legacy hp counts are not migrated to edge — see Risk #3). If no matching `Npc`: emit a `NpcPoolMember(name, role, pronouns, appearance, archetype_id=None, drawn_from="legacy_registry")`, dropping `last_seen_*` (legacy registry entries fused identity and tracking; without an `Npc`, the tracking is suspect and we don't want a stranded ghost).
- **OTEL: `npc.referenced` span.** Emitted on every narrator-cite of an NPC name during `narration_apply` lookup. Attributes: `name`, `match_strategy ∈ {"npcs_hit", "pool_hit", "invented"}`, `pool_origin: str | None`. The GM panel surfaces a per-session counter of `match_strategy == "invented"` — Sebastien's lie-detector signal that the pool wasn't deep enough or wasn't seeded.
- **Sibling-file safety net (Wave 1).** Already in place from Story 45-45 (`persistence.py:400-424`). Wave 2A's migration inherits the `.canonicalize.bak` discipline for free — no new safety-net work.

**Tech Stack:** Python 3.12, pydantic v2, pytest, uv, OpenTelemetry passthrough (`sidequest.telemetry`), SQLite save store. Same as Wave 1.

---

## File Structure

**Created:**

- `sidequest-server/sidequest/game/npc_pool.py` — `NpcPoolMember` model (identity-only). Single responsibility: define the type. No logic.
- `sidequest-server/tests/game/test_npc_pool_model.py` — Type-roundtrip and field-default tests for `NpcPoolMember`.
- `sidequest-server/tests/game/test_npc_pool_migration.py` — Unit tests for `_migrate_s2_npc_registry_split`. Cases: name-only registry entry → pool member; stats-published entry with matching `Npc` → `last_seen_*` merge; stats-published entry with NO matching `Npc` → drop with span attr; empty registry → no-op.
- `sidequest-server/tests/server/test_npc_pool_narration_apply.py` — Narration-apply tests for the 3-step lookup. Cases: cite known `Npc` → `last_seen_*` updated; cite known pool member → no state change; cite unknown name → `NpcPoolMember` appended with `drawn_from="narrator_invented"`.
- `sidequest-server/tests/agents/test_npc_roster_projection.py` — Golden-text test on `register_npc_roster_section`. Asserts pool members and `Npc` records produce identical narrator-facing format (gaslight preserved); `last_seen_*` lines appear only when set.
- `sidequest-server/tests/integration/test_npc_pool_wiring.py` — End-to-end wiring proof. Spawns a narration_apply with a fresh state, narrator names a new NPC, asserts `NpcPoolMember` lands in snapshot AND the next prompt projection includes that name.
- `sidequest-server/tests/fixtures/legacy_snapshots/with_npc_registry.json` — Captured legacy fixture containing one name-only registry entry, one entry with hp/max_hp + matching `Npc`, and one entry with hp/max_hp without matching `Npc` (the orphan case).

**Modified:**

- `sidequest-server/sidequest/game/session.py` — drop `NpcRegistryEntry` class (lines 159-183); drop `npc_registry` field declaration (line 519); add `npc_pool: list[NpcPoolMember] = Field(default_factory=list)` field on `GameSnapshot`; add `pool_origin: str | None = None`, `last_seen_location: str | None = None`, `last_seen_turn: int = 0` to `Npc` model (lines 110-157). Add docstring on `Npc.last_seen_location` clarifying its distinction from `Npc.location` (current scene) and `Npc.current_room` (chassis interior).
- `sidequest-server/sidequest/game/__init__.py` — drop `NpcRegistryEntry` export; export `NpcPoolMember`.
- `sidequest-server/sidequest/game/migrations.py` — add `_migrate_s2_npc_registry_split(out: dict) -> dict | None` sub-function alongside `_migrate_s1_world_confrontations`. Update `migrate_legacy_snapshot` orchestrator to call it and merge OTEL attributes.
- `sidequest-server/sidequest/server/narration_apply.py:1440-1510` — rewrite the `npcs_present` apply loop with the 3-step lookup. Drop registry references entirely. Emit `npc.referenced` span per cite (regardless of match strategy).
- `sidequest-server/sidequest/agents/prompt_framework/core.py:370-421` — `register_npc_roster_section` reads `snapshot.npc_pool` and `snapshot.npcs`. Format pool members and `Npc` records into identical-shape blocks; only `Npc` blocks include `last seen at <location>, turn <N>` lines (when set).
- `sidequest-server/sidequest/game/chassis.py` — delete `_project_chassis_to_npc_entry` (lines 179-190); drop `init_chassis_registry`'s line 272 (the projection append). Verify chassis still surface in narrator prompt via `register_chassis_voice_section` only.
- `sidequest-server/sidequest/telemetry/spans/npc.py` — add `SPAN_NPC_REFERENCED = "npc.referenced"` constant with docstring noting Sebastien-lie-detector wiring. Re-export from `sidequest/telemetry/spans/__init__.py` if `__all__` is used there.
- `sidequest-server/tests/integration/test_npc_wiring.py` — repoint registry references to `npc_pool` / `npcs`.
- `sidequest-server/tests/agents/test_orchestrator.py` — repoint.
- `sidequest-server/tests/server/test_npc_identity_drift.py` — repoint last-seen drift assertions onto `Npc.last_seen_*`.
- `sidequest-server/tests/server/test_dispatch.py` — repoint.
- `sidequest-server/tests/server/test_chargen_persist_and_play.py` — repoint.
- `sidequest-server/tests/server/test_encounter_actors_all_combatants.py` — repoint.
- `sidequest-server/tests/server/test_encounter_lifecycle.py` — repoint.
- `sidequest-server/tests/server/test_party_peer_identity.py` — repoint.
- `sidequest-server/tests/agents/subsystems/test_npc_agency.py` — repoint.
- `sidequest-server/tests/agents/conftest.py` — repoint.

**Deleted:**

- `sidequest-server/tests/server/test_npc_registry_combat_stats.py` — Story 45-21's invariant ("hp/max_hp written only when combat publishes stats; hp == 0 means dead") becomes "Npc.core.edge initialized via `placeholder_edge_pool()` until combat publishes a real EdgePool from edge_config." The invariant moves to a new test `tests/server/test_npc_combat_edge_published.py` against `Npc.core.edge`. The old test is no longer applicable — registry no longer exists, hp/max_hp are not the canonical channel. **DO NOT** delete the test until the replacement test (Task 5) is in place and passing — these are TDD guard rails for the same invariant.

**Note on fixtures:** Step 2.1 captures the legacy `with_npc_registry.json` fixture from a real save BEFORE source changes that touch `npc_registry`. The fixture is committed as part of Task 2 so subsequent tests reference it.

---

## Task 1: Add `NpcPoolMember` type, `npc_pool` field, and `Npc` field extensions (no behavior change)

**Files:**

- Create: `sidequest-server/sidequest/game/npc_pool.py`
- Create: `sidequest-server/tests/game/test_npc_pool_model.py`
- Modify: `sidequest-server/sidequest/game/session.py`
- Modify: `sidequest-server/sidequest/game/__init__.py`

**TDD discipline:** Write the model test first; assert `NpcPoolMember` import fails. Then create the model. Then assert field defaults round-trip correctly. Then add fields to `Npc` and assert legacy `Npc(core=...)` still constructs with new fields defaulted.

- [ ] **Step 1.1: Write the failing test for `NpcPoolMember`**

Create `sidequest-server/tests/game/test_npc_pool_model.py` with these cases (use Wave 1's `tests/game/test_migrations.py` style):
1. `NpcPoolMember(name="Marya", drawn_from="legacy_registry")` constructs with all optional fields defaulting.
2. JSON round-trip: `NpcPoolMember.model_validate(member.model_dump())` returns equal value.
3. `archetype_id` defaults to `None`; `drawn_from` is required.

Run: `uv run pytest tests/game/test_npc_pool_model.py -v` (in `sidequest-server/`). Expected: ImportError on `from sidequest.game.npc_pool import NpcPoolMember`.

- [ ] **Step 1.2: Create the `NpcPoolMember` model**

Author `sidequest-server/sidequest/game/npc_pool.py`:

```python
"""NPC pool members — identity-only entries that the narrator can cite as
"people who exist in this world." Regenerable; no mechanical state. Promote
to ``Npc`` (with ``pool_origin = member.name``) when the NPC actually engages
mechanically (combat handshake, persistent dialog state).

Distinct from ``Npc`` (sidequest.game.session) which carries CreatureCore,
EdgePool, beliefs, and last-seen tracking. The split was Wave 2A of the
snapshot split-brain cleanup (spec: 2026-05-04-snapshot-split-brain-cleanup-design.md)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class NpcPoolMember(BaseModel):
    """Identity-only member of the world's NPC cast pool.

    Pool members exist as scaffolding for narrator name-continuity: when the
    narrator wants to introduce "the bartender at the Black Hart," the pool
    provides a name + appearance hook so the same character can be re-cited
    in a later narration without drift.

    Pool members are re-citable, not consumed. When the same name engages
    mechanically (combat, persistent dialog), an ``Npc`` is created with
    ``pool_origin = self.name``; the pool member remains in ``GameSnapshot.npc_pool``
    and is shadowed by the ``Npc`` lookup at narration_apply time.
    """

    name: str
    role: str | None = None
    pronouns: str | None = None
    appearance: str | None = None
    archetype_id: str | None = None
    """OTEL attribution back to genre-pack archetype source. ``None`` for
    narrator-invented members (see ``drawn_from``) or legacy-migrated members
    where provenance was lost."""
    drawn_from: str
    """Source tag: ``"name_generator"``, ``"world_authored"``,
    ``"legacy_registry"``, ``"narrator_invented"``."""
```

Re-run the test from Step 1.1. All cases pass.

- [ ] **Step 1.3: Re-export `NpcPoolMember` from `sidequest.game`**

Modify `sidequest-server/sidequest/game/__init__.py`: add `from sidequest.game.npc_pool import NpcPoolMember` and include in `__all__` if used.

Verify: `uv run python -c "from sidequest.game import NpcPoolMember; print(NpcPoolMember)"` succeeds.

- [ ] **Step 1.4: Write failing tests for `Npc` field extensions and `GameSnapshot.npc_pool` field**

Add to `sidequest-server/tests/game/test_npc_pool_model.py` (or a sibling test file `test_npc_extensions.py`):

1. `Npc(core=CreatureCore(name="X", ...))` round-trips with `pool_origin == None`, `last_seen_location == None`, `last_seen_turn == 0`.
2. `GameSnapshot()` (with required minimal fields) has `npc_pool == []`.

Run; expect `AttributeError` or pydantic validation error on `pool_origin`.

- [ ] **Step 1.5: Add fields to `Npc` and `GameSnapshot`**

Modify `sidequest-server/sidequest/game/session.py`:

- In the `Npc` class (around lines 110-157), add (alphabetize against existing fields, but keep these grouped near `current_room`):

  ```python
  pool_origin: str | None = None
  """Name of the ``NpcPoolMember`` this NPC was promoted from, or ``None`` for
  narrator-invented NPCs. Lie-detector signal: per-session counts of ``None``
  values measure how often the narrator invents off-pool. (Wave 2A — story 45-47)"""

  last_seen_location: str | None = None
  """Location string from the most recent narration that mentioned this NPC.
  Distinct from ``location`` (current scene location, set when actively
  framed) and ``current_room`` (chassis interior). Used by the narrator
  prompt's NPC roster section for continuity hints."""

  last_seen_turn: int = 0
  """Interaction turn of the most recent narration mention. Defaults to ``0``
  (never mentioned in this session). Updated by ``narration_apply`` on every
  cite."""
  ```

- In the `GameSnapshot` class:
  - **Replace** `npc_registry: list[NpcRegistryEntry] = Field(default_factory=list)` (line 519) with:
    ```python
    npc_pool: list[NpcPoolMember] = Field(default_factory=list)
    """Cast pool of identity-only NPC members the narrator can cite. Replaces
    the legacy ``npc_registry`` field (Wave 2A — story 45-47, spec
    2026-05-04-snapshot-split-brain-cleanup-design.md). Pool members are
    promoted to ``Npc`` (in ``self.npcs``) when they engage mechanically."""
    ```
  - **Do not delete** `NpcRegistryEntry` class yet — keep it in the file for now so legacy migration code in Task 2 can still reference its shape via dict access (we're parsing dicts pre-validation, so the class isn't strictly needed, but it'll be referenced by deprecation imports). Mark with a comment: `# DEPRECATED — removed in Task 6, used only by tests until then.`

- Add `from sidequest.game.npc_pool import NpcPoolMember` near the top imports.

Run Step 1.4 tests; pass.

- [ ] **Step 1.6: Verify legacy code still type-checks**

Run: `uv run mypy sidequest/` — should pass for now (registry class still exists; `npc_registry` callers will be repointed in later tasks).

If mypy yells: the `GameSnapshot.npc_registry` field is gone but readers still reference it. That's expected — Task 3 fixes the readers. For Task 1, allow the type errors and fix in Task 3. (Alternative: add a transitional `@property def npc_registry(self) -> list[NpcRegistryEntry]: warnings.warn(...); return []` shim. Decision: don't bother — the cascade from removing the field is tractable in one PR per Wave 1's pragma.)

- [ ] **Step 1.7: Run full test suite to identify breakage**

Run: `uv run pytest -x --no-header 2>&1 | tail -40`

Capture which tests fail because they reference `npc_registry` or `NpcRegistryEntry`. This list informs Tasks 3-6's repoint scope. Save to `.session/45-47-test-breakage.txt` for reference.

---

## Task 2: Migration sub-function `_migrate_s2_npc_registry_split` + legacy fixture capture

**Files:**

- Modify: `sidequest-server/sidequest/game/migrations.py`
- Modify: `sidequest-server/sidequest/telemetry/spans/__init__.py` or `spans/npc.py`
- Create: `sidequest-server/tests/fixtures/legacy_snapshots/with_npc_registry.json`
- Create: `sidequest-server/tests/game/test_npc_pool_migration.py`

- [ ] **Step 2.1: Capture a legacy fixture (DO THIS BEFORE TASK 3 TOUCHES NARRATION_APPLY)**

```bash
ls ~/.sidequest/saves/ | head -10
```

Pick a save that's been through encounters (likely has populated `npc_registry`). Extract:

```bash
SAVE=~/.sidequest/saves/<chosen>.db
sqlite3 "$SAVE" "SELECT snapshot_json FROM game_state WHERE id = 1" \
  | python -m json.tool > sidequest-server/tests/fixtures/legacy_snapshots/with_npc_registry.json
```

Verify the fixture has registry entries:

```bash
python -c "
import json
d = json.load(open('sidequest-server/tests/fixtures/legacy_snapshots/with_npc_registry.json'))
reg = d.get('npc_registry', [])
print('npc_registry len:', len(reg))
for e in reg[:3]:
    print('  -', e.get('name'), 'hp=', e.get('hp'), 'last_seen=', e.get('last_seen_location'))
print('npcs len:', len(d.get('npcs', [])))
"
```

Expected: at least one `npc_registry` entry. If the chosen save has none, pick another. If no save in `~/.sidequest/saves/` has registry entries, hand-author a minimal fixture (extend Wave 1's `pre_cleanup.json` with three registry entries: one name-only, one with hp+matching Npc by name, one with hp+no matching Npc).

- [ ] **Step 2.2: Add `SPAN_NPC_REFERENCED` constant**

Edit `sidequest-server/sidequest/telemetry/spans/npc.py` — add:

```python
SPAN_NPC_REFERENCED = "npc.referenced"
"""Emitted by ``narration_apply`` on every narrator-cite of an NPC name.
Attributes:
- ``name``: cited name (case-preserved)
- ``match_strategy``: ``"npcs_hit"`` | ``"pool_hit"`` | ``"invented"``
- ``pool_origin``: name of the ``NpcPoolMember`` the resulting/existing ``Npc`` was promoted from, or ``None``

Sebastien-lie-detector hook: per-session count of ``match_strategy == "invented"``
tells the GM panel when the pool wasn't deep enough or wasn't seeded for the scene.
(Wave 2A — story 45-47)"""
```

If `__all__` is used in `spans/npc.py` or `spans/__init__.py`, add `SPAN_NPC_REFERENCED` to it.

- [ ] **Step 2.3: Write failing tests for `_migrate_s2_npc_registry_split`**

Create `sidequest-server/tests/game/test_npc_pool_migration.py`:

```python
"""Unit tests for _migrate_s2_npc_registry_split (Wave 2A — story 45-47)."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from sidequest.game.migrations import migrate_legacy_snapshot

_FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "legacy_snapshots"


def test_name_only_registry_entry_becomes_pool_member() -> None:
    legacy = {
        "npcs": [],
        "npc_registry": [
            {"name": "Marya", "role": "barkeep", "pronouns": "she/her",
             "appearance": "weathered hands", "last_seen_location": None,
             "last_seen_turn": 0, "hp": None, "max_hp": None}
        ],
    }
    out = migrate_legacy_snapshot(legacy)
    assert "npc_registry" not in out
    pool = out["npc_pool"]
    assert len(pool) == 1
    assert pool[0]["name"] == "Marya"
    assert pool[0]["drawn_from"] == "legacy_registry"
    assert pool[0]["archetype_id"] is None


def test_stats_published_with_matching_npc_merges_last_seen() -> None:
    legacy = {
        "npcs": [
            # minimal Npc shape — fill in to match real model defaults
            {"core": {"name": "Boris", "description": "...", "personality": "...",
                      "level": 1, "xp": 0,
                      "inventory": {"items": [], "max_slots": 10},
                      "statuses": [],
                      "edge": {"current": 10, "max": 10, "base_max": 10,
                               "recovery_triggers": [{"kind": "OnResolution"}],
                               "thresholds": []},
                      "acquired_advancements": []},
             "voice_id": None, "disposition": 0, "location": "Inn",
             "current_room": None, "pronouns": "he/him",
             "appearance": "bearded", "age": "40s", "build": "stocky",
             "height": "tall", "distinguishing_features": [],
             "ocean": None, "belief_state": {"beliefs": []},
             "resolution_tier": "spawn", "non_transactional_interactions": 0,
             "jungian_id": None, "rpg_role_id": None, "npc_role_id": None,
             "resolved_archetype": None}
        ],
        "npc_registry": [
            {"name": "Boris", "role": None, "pronouns": None,
             "appearance": None, "last_seen_location": "TavernRow",
             "last_seen_turn": 7, "hp": 12, "max_hp": 12}
        ],
    }
    out = migrate_legacy_snapshot(legacy)
    assert "npc_registry" not in out
    assert out["npc_pool"] == []
    npc = out["npcs"][0]
    assert npc["last_seen_location"] == "TavernRow"
    assert npc["last_seen_turn"] == 7
    assert npc["pool_origin"] is None  # legacy provenance lost


def test_stats_published_orphan_dropped_with_span_attr() -> None:
    """Edge case: registry entry has hp set but no matching Npc.
    Drop with OTEL attribute. Don't synthesize an Npc — that's a legacy bug
    state we don't want to canonicalize."""
    legacy = {
        "npcs": [],
        "npc_registry": [
            {"name": "GhostStat", "role": None, "pronouns": None,
             "appearance": None, "last_seen_location": None,
             "last_seen_turn": 0, "hp": 5, "max_hp": 10}
        ],
    }
    out = migrate_legacy_snapshot(legacy)
    assert out["npc_pool"] == []
    assert out["npcs"] == []
    # Verify span attr was set — assert via OTEL spy fixture (see Wave 1 pattern)


def test_empty_npc_registry_is_no_op() -> None:
    legacy = {"npcs": [], "npc_registry": []}
    out = migrate_legacy_snapshot(legacy)
    assert "npc_registry" not in out
    assert out["npc_pool"] == []


def test_canonical_already_migrated_unchanged() -> None:
    """If snapshot already has npc_pool and no npc_registry, no rewrite."""
    canonical = {
        "npcs": [], "npc_pool": [{"name": "X", "drawn_from": "world_authored"}]
    }
    out = migrate_legacy_snapshot(copy.deepcopy(canonical))
    assert out["npc_pool"] == canonical["npc_pool"]
    assert "npc_registry" not in out


def test_legacy_fixture_round_trips() -> None:
    """Integration: load the captured fixture, run migration, validate
    against current GameSnapshot."""
    fixture_path = _FIXTURE_DIR / "with_npc_registry.json"
    legacy = json.loads(fixture_path.read_text())
    out = migrate_legacy_snapshot(legacy)
    assert "npc_registry" not in out
    # Spot-check: pool members are well-formed
    for member in out.get("npc_pool", []):
        assert "name" in member
        assert "drawn_from" in member
```

Run: `uv run pytest tests/game/test_npc_pool_migration.py -v`

Expected: all tests fail with `_migrate_s2_npc_registry_split` not implemented (or `npc_registry` still present in output).

- [ ] **Step 2.4: Implement `_migrate_s2_npc_registry_split`**

Edit `sidequest-server/sidequest/game/migrations.py`. Add alongside Wave 1's `_migrate_s1_world_confrontations`:

```python
def _migrate_s2_npc_registry_split(out: dict) -> dict | None:
    """S2 (Wave 2A): split legacy npc_registry into npc_pool + Npc.last_seen_*.

    For each entry in legacy ``out["npc_registry"]``:
    - If matching ``Npc`` (by case-folded name) exists in ``out["npcs"]``:
      merge ``last_seen_location`` and ``last_seen_turn`` onto the ``Npc`` dict.
      Legacy ``hp/max_hp`` are NOT migrated — ``Npc.core.edge`` is canonical.
    - Otherwise, if ``hp`` or ``max_hp`` is set: orphan stat block, drop and
      record in span attr (legacy bug state, not canonicalized).
    - Otherwise: emit ``NpcPoolMember`` dict into ``out["npc_pool"]`` with
      ``drawn_from="legacy_registry"``, ``archetype_id=None``.

    Drops ``out["npc_registry"]`` on success. Returns OTEL attribute dict
    if any rewrite happened, else ``None``.
    """
    legacy = out.get("npc_registry")
    if not legacy:
        # No legacy field, or empty — drop the empty key silently if present
        if "npc_registry" in out:
            del out["npc_registry"]
            return {"s2_empty_registry_dropped": True}
        return None

    npcs = out.setdefault("npcs", [])
    pool = out.setdefault("npc_pool", [])

    by_name = {npc.get("core", {}).get("name", "").casefold(): npc for npc in npcs}

    pool_added = 0
    last_seen_merged = 0
    orphans_dropped = 0

    for entry in legacy:
        name = entry.get("name", "")
        key = name.casefold()
        if key in by_name:
            npc = by_name[key]
            if entry.get("last_seen_location") is not None:
                npc["last_seen_location"] = entry["last_seen_location"]
            npc["last_seen_turn"] = entry.get("last_seen_turn", 0)
            npc.setdefault("pool_origin", None)
            last_seen_merged += 1
        elif entry.get("hp") is not None or entry.get("max_hp") is not None:
            # Orphan stat block — drop
            orphans_dropped += 1
        else:
            pool.append({
                "name": name,
                "role": entry.get("role"),
                "pronouns": entry.get("pronouns"),
                "appearance": entry.get("appearance"),
                "archetype_id": None,
                "drawn_from": "legacy_registry",
            })
            pool_added += 1

    del out["npc_registry"]

    return {
        "s2_pool_added": pool_added,
        "s2_last_seen_merged": last_seen_merged,
        "s2_orphans_dropped": orphans_dropped,
    }
```

Wire into `migrate_legacy_snapshot` orchestrator: call alongside Wave 1's S1 sub-function, merge attrs into the OTEL span emission.

Run Step 2.3 tests; all pass.

- [ ] **Step 2.5: Verify Wave 1 `snapshot.canonicalize` span carries S2 attributes**

Add to the existing Wave 1 OTEL tests (or new test in `test_npc_pool_migration.py`): assert that loading a snapshot with both legacy `world_confrontations` AND `npc_registry` emits a single `snapshot.canonicalize` span with both `s1_*` and `s2_*` attributes.

- [ ] **Step 2.6: Verify mypy still passes on `migrations.py`**

Run: `uv run mypy sidequest/game/migrations.py`. Pass.

---

## Task 3: Rewrite `narration_apply.py:1440-1510` — 3-step lookup, drop registry references, emit `npc.referenced`

**Files:**

- Modify: `sidequest-server/sidequest/server/narration_apply.py`
- Create: `sidequest-server/tests/server/test_npc_pool_narration_apply.py`

**Discipline:** This is the load-bearing behavioral change. Write tests for every branch first.

- [ ] **Step 3.1: Write failing tests for the 3-step lookup**

Create `sidequest-server/tests/server/test_npc_pool_narration_apply.py`. Test cases:

1. **Cite known `Npc` (npcs_hit)** — narration result names "Boris" who is in `snapshot.npcs`. Assert `Npc.last_seen_location` and `Npc.last_seen_turn` are updated; no new `NpcPoolMember` appended; `npc.referenced` span emitted with `match_strategy="npcs_hit"`, `pool_origin=<existing Npc.pool_origin>`.

2. **Cite known pool member (pool_hit)** — narration names "Marya" who is in `snapshot.npc_pool`. Assert: no new `Npc` created (promotion is reserved for combat handshake); pool unchanged; `npc.referenced` span with `match_strategy="pool_hit"`, `pool_origin="Marya"`.

3. **Cite unknown name (invented)** — narration names "Erewhon" who is in neither. Assert: `NpcPoolMember(name="Erewhon", drawn_from="narrator_invented")` appended to `npc_pool`; `npc.referenced` span with `match_strategy="invented"`, `pool_origin=None`.

4. **Cite name matching PC (existing skip path)** — narration names player character. Existing `npc_pc_name_skipped_span` still emitted; no `npc.referenced` span emitted. (Preserve current behavior at lines 1446-1465.)

5. **Identity drift on existing Npc** — narration names "Boris" with new pronouns. Assert: existing `Npc` fields are NOT clobbered (additive upsert: only fill `None`-valued fields, preserve set values). This preserves Story 45's identity-drift discipline. Existing `npc_reinvented` span still emits when applicable. (Move drift detection logic from `NpcRegistryEntry` shape onto `Npc` shape.)

Run: `uv run pytest tests/server/test_npc_pool_narration_apply.py -v`

Expect: all fail (existing code still writes to `npc_registry`).

- [ ] **Step 3.2: Survey existing narration_apply NPC code**

Read `sidequest-server/sidequest/server/narration_apply.py:1440-1510` end-to-end. Note all helper calls: `npc_auto_registered_span`, `npc_pc_name_skipped_span`, `npc_reinvented_span`, `SPAN_NPC_REGISTRY_HP_SET`. Decide repoint:

- `npc_auto_registered_span` — semantically becomes "narrator invented an NPC name not in pool/npcs." Repoint to fire on the `match_strategy="invented"` branch. Rename to `npc_invented_span` if call sites are few; otherwise keep the name but update its docstring.
- `npc_reinvented_span` — fires when narrator's identity for a name diverges from registered one. Repoint to compare against `Npc` (when match_strategy="npcs_hit") or `NpcPoolMember` (when match_strategy="pool_hit").
- `SPAN_NPC_REGISTRY_HP_SET` — Story 45-21's combat-stats-published span. This fires from the encounter-handshake path, NOT from narration_apply. Trace its emission site (likely `sidequest/game/encounter*.py` or similar). The span's intent — "combat stats just landed, here's the hp/max_hp" — needs to retarget to "combat stats just landed, here's the EdgePool max." Rename to `SPAN_NPC_EDGE_PUBLISHED` and emit from the same site against `Npc.core.edge.max`. Defer to Task 5 (sibling test relocation).

- [ ] **Step 3.3: Implement the 3-step lookup**

Rewrite the loop at `narration_apply.py:1440-1510`. Pseudo-shape:

```python
for mention in result.npcs_present:
    if _is_pc_name(mention.name, snapshot):
        emit npc_pc_name_skipped_span(...)
        continue

    name_key = mention.name.casefold()

    # Step 1: Npc lookup
    npc = next((n for n in snapshot.npcs
                if n.core.name.casefold() == name_key), None)
    if npc is not None:
        # Update last_seen
        if mention.location:
            npc.last_seen_location = mention.location
        npc.last_seen_turn = current_turn
        # Drift detection (existing logic, repointed)
        _detect_and_log_npc_drift(npc, mention)
        emit_span(SPAN_NPC_REFERENCED, attrs={
            "name": mention.name,
            "match_strategy": "npcs_hit",
            "pool_origin": npc.pool_origin,
        })
        continue

    # Step 2: Pool lookup
    pool_member = next((m for m in snapshot.npc_pool
                        if m.name.casefold() == name_key), None)
    if pool_member is not None:
        # Optional: additive upsert appearance/role from mention onto pool member
        emit_span(SPAN_NPC_REFERENCED, attrs={
            "name": mention.name,
            "match_strategy": "pool_hit",
            "pool_origin": pool_member.name,
        })
        continue

    # Step 3: Novel — append to pool with drawn_from="narrator_invented"
    new_member = NpcPoolMember(
        name=mention.name,
        role=mention.role,
        pronouns=mention.pronouns,
        appearance=mention.appearance,
        archetype_id=None,
        drawn_from="narrator_invented",
    )
    snapshot.npc_pool.append(new_member)
    emit_span(SPAN_NPC_REFERENCED, attrs={
        "name": mention.name,
        "match_strategy": "invented",
        "pool_origin": None,
    })
    emit_span(npc_invented_span(...))  # existing telemetry, repoint
```

Drop all references to `snapshot.npc_registry` and `NpcRegistryEntry`. Drop the import.

Run Step 3.1 tests; all pass.

- [ ] **Step 3.4: Run the broader narration_apply test suite**

Run: `uv run pytest tests/server/test_dispatch.py tests/server/test_npc_identity_drift.py tests/server/test_party_peer_identity.py -v`

Expect: failures pointing at `npc_registry` access in test bodies. Don't fix the tests yet — capture the list, fix in Task 6 (test repoint pass).

---

## Task 4: Drop chassis-into-registry projection

**Files:**

- Modify: `sidequest-server/sidequest/game/chassis.py`
- Verify: `sidequest-server/sidequest/agents/prompt_framework/core.py:423-483` (`register_chassis_voice_section`)

- [ ] **Step 4.1: Verify no other site reads chassis-as-NPC from registry**

Run: `grep -rn "_project_chassis_to_npc_entry\|chassis.*npc_registry\|npc_registry.*chassis" sidequest-server/sidequest/`

Expected: only the chassis.py producer site. If anything else surfaces, the chassis-as-NPC projection has hidden consumers — add to the test repoint list before deletion.

- [ ] **Step 4.2: Delete `_project_chassis_to_npc_entry` and the fold**

In `sidequest-server/sidequest/game/chassis.py`:
- Delete the function definition at lines 179-190.
- In `init_chassis_registry` (around line 193+), remove the line that appends the projected entry to the npc_registry (line 272). Keep the `chassis_registry` append (line 271).

- [ ] **Step 4.3: Verify chassis still surface in narrator prompt via voice section**

Run a smoke playtest scenario that has a chassis (caverns_and_claudes has a ship chassis): `just playtest-scenario <scenario-with-chassis>` (or fall back to a unit test that constructs a `GameSnapshot` with a chassis, calls `register_chassis_voice_section`, and asserts the chassis name appears in the projection output).

- [ ] **Step 4.4: Run chassis tests**

Run: `uv run pytest -k chassis -v`. All pass.

---

## Task 5: Repoint Story 45-21's combat-stats-published invariant from registry hp/max_hp onto `Npc.core.edge`

**Files:**

- Modify: producer of `SPAN_NPC_REGISTRY_HP_SET` (locate via grep — likely `sidequest/game/encounter*.py` or `narration_apply.py`)
- Modify: `sidequest-server/sidequest/telemetry/spans/npc.py` (rename `SPAN_NPC_REGISTRY_HP_SET` → `SPAN_NPC_EDGE_PUBLISHED`)
- Create: `sidequest-server/tests/server/test_npc_combat_edge_published.py`
- Delete: `sidequest-server/tests/server/test_npc_registry_combat_stats.py`

**Why a separate task:** Story 45-21's invariant ("hp/max_hp set unambiguously means stats published; hp == 0 means dead") is load-bearing for combat narration. This task preserves the invariant on the new shape — `Npc.core.edge.max > 0 AND not placeholder` means stats published; `Npc.core.edge.current == 0 AND broken_on_zero=True` means broken. The semantic mapping is direct.

- [ ] **Step 5.1: Locate `SPAN_NPC_REGISTRY_HP_SET` emitter**

Run: `grep -rn "SPAN_NPC_REGISTRY_HP_SET\|npc_registry.*hp" sidequest-server/sidequest/`. Find the emission site.

- [ ] **Step 5.2: Write failing test for the new span on `Npc.core.edge`**

Author `tests/server/test_npc_combat_edge_published.py` mirroring the structure of the deleted `test_npc_registry_combat_stats.py`. Assertions: when combat handshake publishes stats, `SPAN_NPC_EDGE_PUBLISHED` fires with `name`, `edge_max: int`, `edge_current: int`. When the npc.core.edge is `placeholder_edge_pool()` (current == 10, base_max == 10, no thresholds), the span is NOT yet emitted.

- [ ] **Step 5.3: Rename the span constant and update emitter**

In `telemetry/spans/npc.py`: rename `SPAN_NPC_REGISTRY_HP_SET` → `SPAN_NPC_EDGE_PUBLISHED`. Update the emitter to source attributes from `Npc.core.edge` instead of `NpcRegistryEntry.hp`.

- [ ] **Step 5.4: Delete `test_npc_registry_combat_stats.py`**

After Step 5.3 tests pass: `git rm sidequest-server/tests/server/test_npc_registry_combat_stats.py`.

- [ ] **Step 5.5: Run combat-related test suite**

Run: `uv run pytest tests/server/test_encounter_lifecycle.py tests/server/test_encounter_actors_all_combatants.py -v`. All pass.

---

## Task 6: Refactor `register_npc_roster_section` (prompt projection — gaslight preserved)

**Files:**

- Modify: `sidequest-server/sidequest/agents/prompt_framework/core.py:370-421`
- Create: `sidequest-server/tests/agents/test_npc_roster_projection.py`

- [ ] **Step 6.1: Write golden-text test for projection format**

Create `tests/agents/test_npc_roster_projection.py`. Assertions:

1. **Pool member produces identity-only block.** Given `NpcPoolMember(name="Marya", role="barkeep", pronouns="she/her", appearance="weathered hands")`, the projection contains a block matching the canonical format used today (use a snapshot/golden-text comparison against a saved string).

2. **`Npc` produces identity + last-seen block when last_seen set.** Given `Npc` with `last_seen_location="TavernRow"`, `last_seen_turn=7`, the projection block matches identity-only format PLUS a `last seen at TavernRow, turn 7` line.

3. **`Npc` with no last-seen produces identity-only block (gaslight preservation).** Given `Npc(last_seen_location=None, last_seen_turn=0)`, the projection is indistinguishable from a `NpcPoolMember`.

4. **Mixed projection.** Given a snapshot with 2 pool members and 1 `Npc`, all 3 appear in the roster section in a stable order (alphabetic by name, or insertion order — match Wave 1 / today's behavior).

5. **Empty snapshot produces empty section** (or section omitted; match current behavior).

Run; expect failures (current code reads `npc_registry`).

- [ ] **Step 6.2: Rewrite `register_npc_roster_section`**

In `prompt_framework/core.py`, change the function to read from `snapshot.npc_pool` and `snapshot.npcs` instead of `snapshot.npc_registry`. Format both into identical-shape blocks (pool members and `Npc` records). Add `last seen at...` line ONLY when `Npc.last_seen_location is not None`.

The narrator must not be able to tell from the projection which entries are pool vs. `Npc`. This is the gaslight discipline — the narrator sees "people who exist in this world."

Run Step 6.1 tests; pass.

---

## Task 7: Drop `NpcRegistryEntry` class, drop `npc_registry` field references, repoint test files

**Files:**

- Modify: `sidequest-server/sidequest/game/session.py` (delete `NpcRegistryEntry`)
- Modify: `sidequest-server/sidequest/game/__init__.py` (drop `NpcRegistryEntry` export if exported)
- Modify: 11 test files listed in File Structure

- [ ] **Step 7.1: Final grep for remaining registry references**

Run: `grep -rn "NpcRegistryEntry\|npc_registry" sidequest-server/sidequest/ sidequest-server/tests/ | grep -v "\.session" | grep -v migrations.py`

Expected callers after Tasks 1-6: only the test files plus possibly fixture-loading paths. The `migrations.py` reference is required (it parses the legacy field name from dict).

- [ ] **Step 7.2: Repoint test files**

For each of the 11 test files in File Structure:Modified, replace `NpcRegistryEntry(...)` constructions with the appropriate split:
- Where the test asserts narrator name-continuity → use `NpcPoolMember(...)` and add to `snapshot.npc_pool`.
- Where the test asserts last-seen tracking → construct an `Npc` and assert `Npc.last_seen_*`.
- Where the test asserts combat-stats-published → use `Npc.core.edge` (covered in Task 5; this step verifies the rest are repointed).

- [ ] **Step 7.3: Delete `NpcRegistryEntry` class**

In `session.py`, delete the class definition at lines 159-183. Remove from any `__all__`.

- [ ] **Step 7.4: Verify clean state**

Run:
```bash
grep -rn "NpcRegistryEntry" sidequest-server/sidequest/ sidequest-server/tests/
# Expected: zero results
grep -rn "snapshot.npc_registry\|\.npc_registry" sidequest-server/sidequest/ sidequest-server/tests/
# Expected: only migrations.py legacy-shape parsing
```

- [ ] **Step 7.5: Full test suite**

Run: `just server-check` (lint + test). Pass.

---

## Task 8: Wiring test — pool projection appears in real prompt

**Files:**

- Create: `sidequest-server/tests/integration/test_npc_pool_wiring.py`

This is the mandatory wiring test per CLAUDE.md "Every Test Suite Needs a Wiring Test."

- [ ] **Step 8.1: Author the integration test**

Spawn a minimal session, run a narration_apply that names a new NPC, assert:
1. `snapshot.npc_pool` contains the new `NpcPoolMember`.
2. The next prompt-build call (via the actual prompt assembly path) produces a narrator prompt string containing the new NPC's name in the roster section.

This proves the full chain: narration → pool append → next-turn projection → narrator sees the name.

- [ ] **Step 8.2: Run the wiring test**

Pass.

---

## Task 9: Migration integration test on captured fixture

**Files:**

- Modify: `sidequest-server/tests/game/test_npc_pool_migration.py` (extend `test_legacy_fixture_round_trips`)

- [ ] **Step 9.1: Round-trip the captured fixture through `SqliteStore.load`**

Extend `test_legacy_fixture_round_trips` (or add a sibling test in `tests/game/test_canonicalize_backup.py`) that:

1. Creates a temp SQLite save populated with the legacy fixture's `snapshot_json`.
2. Calls `SqliteStore.load(temp_path)`.
3. Asserts the returned `GameSnapshot` has `npc_pool` populated, `npc_registry` field absent (pydantic ignores or doesn't include it).
4. Asserts `Npc` records in the result carry `last_seen_*` for the entries that had matching names.
5. Asserts `<temp_path>.canonicalize.bak` was created (Wave 1's safety net carries through).
6. Re-saves and re-loads; asserts second load is no-op (no migration runs because canonical).

- [ ] **Step 9.2: Run all migration tests**

Run: `uv run pytest tests/game/test_npc_pool_migration.py tests/game/test_canonicalize_backup.py tests/game/test_migrations.py -v`. Pass.

---

## Task 10: Doc updates (epic context, ADR, changelog)

**Files:**

- Modify: `sprint/context/context-epic-45.md` (add Wave 2A delivery summary)
- Modify: `docs/adr/README.md` if the ADR index references the registry
- Update: spec doc with status note (`docs/superpowers/specs/2026-05-04-snapshot-split-brain-cleanup-design.md` → mark Wave 2A "Implemented" in the story decomposition section)
- Run: `pf changelog` flow if applicable

- [ ] **Step 10.1: Spec status update**

In the spec doc's "Story decomposition (preview)" section, change "Story Y — Wave 2A: NPC pool / state split" line to indicate `(implemented in 45-47, 2026-05-04)`.

- [ ] **Step 10.2: Open question resolution log**

The spec listed three open questions. Wave 2A's plan resolves #1 (pool-promotion is leave-in-place re-citable) and partially addresses #2 (per-field deprecation surface — N/A for Wave 2A since the field is dropped cleanly, not warned-on-read). Question #3 (wave ordering) was answered by shipping Wave 1 first. Document these resolutions in a brief addendum to the spec.

---

## Wave 2A-specific Risks

1. **Pool seeding deferred — empty pool for new sessions.** `npc_pool` is empty for new sessions until the narrator invents a name (which appends with `drawn_from="narrator_invented"`). The spec's vision of "pool generated at world-bind from name-generators × archetype tables × culture corpus" is **not** delivered by this story. The `npc.referenced` span will report `match_strategy="invented"` for nearly every NPC in early sessions. **Mitigation:** this is the intended Sebastien-lie-detector signal — we want to see how often the narrator invents off-pool, because that data drives the priority of the follow-up seeding story (Wave 2A.1, file as a sprint follow-up). Reviewer should confirm this scope split is acceptable before TEA red phase.

2. **`Npc.last_seen_location` overlaps with `Npc.location` and `Npc.current_room`.** Three location-flavored fields on one model. `location` is current scene location (active framing); `current_room` is chassis-interior position; `last_seen_location` is the most recent narration mention regardless of scene. Different semantics, but a maintainer could conflate them. **Mitigation:** docstring on `last_seen_location` explicitly distinguishes from siblings (Step 1.5). Reviewer should challenge whether all three are necessary; if `last_seen_location` can be derived from `location` (e.g. "current location at the most recent turn this NPC appeared"), prefer derivation. Architect's recommendation: keep the explicit field — derivation requires walking narrative_log per-turn-per-NPC, which is not free. Stored field, single writer (`narration_apply`), single reader (`register_npc_roster_section` last-seen line).

3. **Legacy hp/max_hp on registry entries are dropped, not migrated to EdgePool.** The migration's "stats-published, no matching Npc" branch drops the orphan stat block (Task 2). The "stats-published, matching Npc" branch ALSO does not migrate hp/max_hp onto the `Npc.core.edge` (the existing `Npc.core.edge` is canonical and was set when the `Npc` was created via combat handshake; legacy registry hp is redundant in this case). **Mitigation:** OTEL attribute `s2_orphans_dropped` lets the GM panel show how often this fired. If it's non-zero on real saves, those saves had a bug-state where combat published stats to the registry but never created a real `Npc` — undefined behavior pre-cleanup, undefined behavior post-cleanup. We're not regressing.

4. **Chassis fold removal could break narrator naming continuity.** Today the chassis appears in `npc_registry` as `role="ship_ai"` AND in the chassis voice section. After Task 4, only the voice section. If the narrator's prompt today relies on seeing chassis names in the NPC roster, removing the fold could cause the narrator to forget chassis names. **Mitigation:** Step 4.3 verifies chassis still surface via voice section. Run a chassis-bearing playtest scenario (caverns_and_claudes ship-AI scene) before merge to confirm narrator behavior unchanged.

5. **11 test files require repoint.** The blast radius is wide. Step 1.7 captures the breakage list upfront. Task 7's repoint must be exhaustive — leftover references will cause CI red after Task 1 lands. **Mitigation:** the plan's tasks are ordered such that Task 1 introduces the new fields without removing the old class (transitional state with both). Tests can keep using `NpcRegistryEntry` until Task 7 forces their migration.

6. **Promotion-to-Npc not implemented in this story.** The plan documents that a pool member becomes an `Npc` "when the NPC actually engages mechanically." That promotion path (combat handshake creates `Npc` with `pool_origin=member.name`) is in scope of the existing combat handshake code, but the plan doesn't enumerate that wiring. **Mitigation:** trace the existing combat-handshake path that creates `Npc` records (find via `grep -n "snapshot.npcs.append\|state.npcs.append" sidequest-server/sidequest/`). If the path constructs `Npc` from a name match against `npc_registry` today, repoint to `npc_pool` and set `pool_origin = pool_member.name`. Add this as a sub-task under Task 3 if discovery shows the path is registry-coupled. The plan defers exact line work to discovery, but Task 3's lookup logic must include this re-pointing.

---

## Wave 2A-specific Acceptance Criteria

- [ ] **AC1.** `GameSnapshot.npc_registry` field is removed; `GameSnapshot.npc_pool: list[NpcPoolMember]` exists with default empty list.
- [ ] **AC2.** `Npc` model has `pool_origin: str | None = None`, `last_seen_location: str | None = None`, `last_seen_turn: int = 0` fields.
- [ ] **AC3.** `NpcRegistryEntry` class is deleted from `sidequest/game/session.py`. `grep` for `NpcRegistryEntry` in production code returns zero results.
- [ ] **AC4.** Loading a save with legacy `npc_registry` populates `npc_pool` (for name-only entries) and merges `Npc.last_seen_*` (for entries matching an existing `Npc` by case-folded name); orphan stats-published entries are dropped with span attribute. The legacy field is absent from the canonicalized snapshot.
- [ ] **AC5.** `snapshot.canonicalize` OTEL span carries `s2_pool_added`, `s2_last_seen_merged`, `s2_orphans_dropped` attributes alongside Wave 1's `s1_*` attributes when a save with both legacy fields is loaded.
- [ ] **AC6.** `npc.referenced` OTEL span emitted on every narrator-cite of an NPC name (after PC-skip filter), carrying `name`, `match_strategy ∈ {"npcs_hit", "pool_hit", "invented"}`, and `pool_origin: str | None`. The GM panel surfaces a per-session counter of `match_strategy == "invented"`.
- [ ] **AC7.** Narrator prompt's NPC roster section reads from `snapshot.npc_pool` and `snapshot.npcs`. The format is identical for pool members and `Npc` records (gaslight preserved); `Npc` records include a `last seen at...` line only when `last_seen_location` is set.
- [ ] **AC8.** Chassis-into-`npc_registry` projection (`_project_chassis_to_npc_entry` and the append at chassis.py:272) is deleted. Chassis surface in the narrator prompt via `register_chassis_voice_section` only.
- [ ] **AC9.** Story 45-21's combat-stats-published invariant is preserved on the new shape: `SPAN_NPC_EDGE_PUBLISHED` (renamed from `SPAN_NPC_REGISTRY_HP_SET`) emits when combat handshake publishes a non-placeholder `EdgePool` onto an `Npc.core.edge`.
- [ ] **AC10.** Wiring test (`test_npc_pool_wiring.py`) proves a narrator-invented name lands in `npc_pool` AND surfaces in the next prompt projection.
- [ ] **AC11.** All existing tests that referenced `NpcRegistryEntry` are repointed to `NpcPoolMember` (for identity-continuity assertions) or `Npc.last_seen_*` (for last-seen assertions). `just server-check` passes.

---

## Open Questions for Reviewer (BEFORE TEA Red Phase)

1. **Scope split confirmation.** This plan delivers types + migration + reactive lifecycle + OTEL. It does **NOT** deliver proactive pool seeding (name-generators × archetypes × culture corpus → world-bind population). Is the 8-point scope correct as planned, or should pool seeding be folded in (raising estimate to ~13 points)? Architect's recommendation: keep split — Wave 2A.1 (seeding) is a discrete story with its own design questions (which name-generator? which archetypes? per-genre or per-world catalog? scale by world size?) that deserve a separate plan.

2. **Three location-flavored fields on `Npc`** (`location`, `current_room`, `last_seen_location`). Confirm all three are kept. Architect's recommendation: keep. Derivation of `last_seen_location` from `location` requires per-NPC narrative_log walks; not worth the cost.

3. **Pool member promotion semantics.** Plan chooses leave-in-place re-citable (pool member stays after first reference; `Npc` lookup at narration_apply step 1 shadows it). Spec listed this as deferrable. Confirm this choice over one-shot draw, or instruct otherwise.

4. **Combat handshake re-pointing scope.** Risk #6 notes the combat path that creates `Npc` records may today reference `npc_registry`; if so, Task 3 must include that repoint. The plan defers the specific scope to Step 3.2's discovery. Reviewer should confirm this discovery-first approach is acceptable, or pre-survey the combat path to lock scope before TEA.

---

## References

- **Spec:** `docs/superpowers/specs/2026-05-04-snapshot-split-brain-cleanup-design.md` (commit b910399)
- **Wave 1 plan (completed):** `docs/superpowers/plans/completed/2026-05-04-snapshot-split-brain-wave-1.md`
- **Story 45-45 (Wave 1):** delivered S1 + S4 + S5 + migration scaffolding + sibling-file safety net.
- **ADR-007** Unified Character Model (Character + Npc compose CreatureCore).
- **ADR-014** Diamonds and Coal (pool members are coal — minor; promoted Npcs are diamond — narrative weight earned).
- **ADR-026/027** Client State Mirror / Reactive State Messaging (projection shape preserved; UI `views.py:164` already iterates `snapshot.npcs`, not registry).
- **ADR-058** Claude Subprocess OTEL Passthrough; **ADR-090** OTEL Dashboard Restoration.
- **ADR-067** Unified Narrator Agent (single persistent session — narrator cannot tool-call; cast pool must be in-prompt).
- **ADR-091** Culture-Corpus + Markov Naming (source of pool identity samples for the Wave 2A.1 follow-up).
- **CLAUDE.md** — "GM panel is the lie detector"; "Every Test Suite Needs a Wiring Test."
- **Story 39 / EdgePool** — composure model that supersedes legacy hp/max_hp.
- **Story 45-21** — registry hp/max_hp discipline; invariant moves onto `Npc.core.edge` in Task 5.

---

## Wave 2A Follow-up (separate story, not in scope here)

**Wave 2A.1: Proactive pool seeding at world-bind.** Once Wave 2A lands and OTEL telemetry shows the rate of `match_strategy == "invented"`, file a follow-up story to populate `npc_pool` at world-bind from genre-pack name-generators × archetype tables × culture corpus (per ADR-091). Estimated 5 points. Acceptance: pool is non-empty for new sessions; `match_strategy` distribution shifts measurably toward `pool_hit`.
