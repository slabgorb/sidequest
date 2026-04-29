# Local DM Group G — MP-Ship Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the Local DM decomposer's per-event `VisibilityTag` output through the projection pipeline so P1 can assassinate an NPC without P2–P4 seeing it in narration or local saves.

**Architecture:** The decomposer (shipped Group B) is the authoritative upstream of visibility data. The projection engine (shipped 2026-04-23) is the authoritative downstream consumer. This plan adds (a) YAML defaults the decomposer reasons against, (b) a `visibility_tag` rule kind inside `GenreRuleStage`, (c) a structural-hiding precondition in the narrator prompt builder, (d) an OTEL leak-audit, (e) a deterministic fidelity-only PerceptionRewriter, (f) per-player save projection, and (g) real zone/visibility state on `SessionGameStateView` so existing `visible_to`/`in_same_zone` predicates stop returning `False` by default.

**Tech Stack:** Python 3.12, pydantic, pytest, FastAPI/uvicorn, OpenTelemetry, YAML. No new dependencies.

**Reference spec:** `docs/superpowers/specs/2026-04-23-local-dm-group-g-asymmetric-info-wiring.md`.

**Branch:** Create `feat/local-dm-group-g` off `main` before Task 1. All tasks commit to this branch; single PR at the end.

**Decisions locked by user (2026-04-23):**

- **PerceptionRewriter** is **deterministic fidelity-only** for MP ship (no LLM re-voicing in the hot path). Task 7 ships the deterministic skeleton; LLM re-voicing is deferred to post-MP as G10.
- **Zone authorship** is done inside `SessionHandler`'s existing movement/encounter subsystems (option b from spec §11.2). The decomposer reads zones, does not author them.
- **`_visibility` payload carry** stays a reserved key inside `payload_json` (option 3 from spec §11.3) — validator-enforced, least churn.
- **World-level `visibility_overrides.yaml`** ships in Task 2 as a flat delta-dict per spec §11.4.
- **MP-ship scope is this plan.** No PM ceremony. No per-story sprint splits. One branch, one PR, one merge.

**Non-goals (explicit rejections):**

- No parallel visibility system.
- No per-player narrator fan-out.
- No narrator self-policing.
- No keyword/regex visibility rules.
- No LLM re-voicing rewriter (deferred to post-MP G10).
- No guest-NPC inversion (deferred to post-MP G9).
- No GM-panel visibility UI (deferred to post-MP G11).

---

## File Structure

**New files:**

- `sidequest-content/genre_packs/<pack>/visibility_baseline.yaml` — one per shipping pack (6)
- `sidequest-content/genre_packs/<pack>/worlds/<world>/visibility_overrides.yaml` — optional deltas
- `sidequest-server/sidequest/genre/models/visibility.py` — pydantic schema for baseline + overrides
- `sidequest-server/sidequest/game/projection/visibility_tag.py` — `VisibilityTagRule` model + evaluator helper
- `sidequest-server/sidequest/agents/perception_rewriter.py` — deterministic fidelity-only rewriter
- `sidequest-server/sidequest/agents/prompt_redaction.py` — structural-hiding precondition
- `sidequest-server/sidequest/telemetry/leak_audit.py` — canonical-leak audit
- `sidequest-server/tests/genre/test_visibility_baseline.py`
- `sidequest-server/tests/projection/test_visibility_tag_rule.py`
- `sidequest-server/tests/agents/test_prompt_redaction.py`
- `sidequest-server/tests/agents/test_perception_rewriter.py`
- `sidequest-server/tests/telemetry/test_leak_audit.py`
- `sidequest-server/tests/integration/test_group_g_e2e.py`
- `scenarios/asymmetric_smoke.yaml` — CI scenario for leak-audit assertion

**Modified files:**

- `sidequest-server/sidequest/game/projection/view.py` — real `zone_of` and `visible_to`
- `sidequest-server/sidequest/game/projection/rules.py` — add `VisibilityTagRule` variant
- `sidequest-server/sidequest/game/projection/genre_stage.py` — evaluate the new variant
- `sidequest-server/sidequest/genre/pack_loader.py` (or equivalent) — load visibility_baseline.yaml
- `sidequest-server/sidequest/server/session_handler.py` — populate `SessionGameStateView` zones; route SECRET_NOTE; write peer-filtered frames
- `sidequest-server/sidequest/agents/local_dm.py` — emit real `VisibilityTag` from baseline + turn state
- `sidequest-server/sidequest/agents/narrator.py` — call prompt_redaction + leak_audit
- `sidequest-server/sidequest/protocol/messages.py` — `SECRET_NOTE` message kind

---

## Task 0: Branch and Baseline

**Files:** none (git-only)

- [ ] **Step 1: Create branch**

```bash
git checkout main
git pull
git checkout -b feat/local-dm-group-g
```

- [ ] **Step 2: Verify clean baseline**

Run: `just server-check`
Expected: PASS. (Any pre-existing failure is your problem — do not advance until it is clean.)

- [ ] **Step 3: Record starting test count**

Run: `cd sidequest-server && uv run pytest --collect-only -q 2>&1 | tail -3`
Record the count in a comment on the first commit — you will compare at the end.

---

## Task 1: Real zone/visibility state on `SessionGameStateView` (G7)

**Why first:** every downstream piece (G2 filter, G6 rewriter, G4 targeting) queries this view. Today `zone_of` returns `None` and `visible_to` returns `False`, which silently turns every genre `visible_to(target)` redaction into "always redact." Fix the substrate before adding consumers.

**Files:**
- Modify: `sidequest-server/sidequest/game/projection/view.py:23-62`
- Modify: `sidequest-server/sidequest/server/session_handler.py` (zone update hook)
- Test: `sidequest-server/tests/projection/test_view_zones.py` (create)

- [ ] **Step 1: Write failing test for zone tracking**

Create `sidequest-server/tests/projection/test_view_zones.py`:

```python
from sidequest.game.projection.view import SessionGameStateView


def test_zone_of_returns_configured_zone():
    view = SessionGameStateView(
        gm_player_id="gm1",
        player_id_to_character={"p1": "char_alice", "p2": "char_bob"},
        character_zones={"char_alice": "warehouse", "char_bob": "inn"},
    )
    assert view.zone_of("char_alice") == "warehouse"
    assert view.zone_of("char_bob") == "inn"
    assert view.zone_of("char_unknown") is None


def test_visible_to_true_when_same_zone_and_not_hidden():
    view = SessionGameStateView(
        gm_player_id="gm1",
        player_id_to_character={"p1": "char_alice", "p2": "char_bob"},
        character_zones={"char_alice": "inn", "char_bob": "inn"},
    )
    assert view.visible_to("char_alice", "char_bob") is True


def test_visible_to_false_when_different_zones():
    view = SessionGameStateView(
        gm_player_id="gm1",
        player_id_to_character={"p1": "char_alice", "p2": "char_bob"},
        character_zones={"char_alice": "warehouse", "char_bob": "inn"},
    )
    assert view.visible_to("char_alice", "char_bob") is False


def test_visible_to_false_when_target_hidden_even_same_zone():
    view = SessionGameStateView(
        gm_player_id="gm1",
        player_id_to_character={"p1": "char_alice", "p2": "char_bob"},
        character_zones={"char_alice": "inn", "char_bob": "inn"},
        hidden_characters={"char_bob"},
    )
    assert view.visible_to("char_alice", "char_bob") is False


def test_visible_to_false_on_unknown_character():
    view = SessionGameStateView(
        gm_player_id="gm1",
        player_id_to_character={"p1": "char_alice"},
        character_zones={"char_alice": "inn"},
    )
    assert view.visible_to("char_alice", "char_ghost") is False
    assert view.visible_to("char_ghost", "char_alice") is False
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd sidequest-server && uv run pytest tests/projection/test_view_zones.py -v`
Expected: 5 FAIL — `SessionGameStateView` does not accept `character_zones` / `hidden_characters` yet.

- [ ] **Step 3: Extend `SessionGameStateView`**

Edit `sidequest-server/sidequest/game/projection/view.py`. Replace the `SessionGameStateView` dataclass (lines 23-62) with:

```python
@dataclass
class SessionGameStateView:
    """Conservative GameStateView implementation.

    Zone tracking populated by SessionHandler's movement subsystems.
    Hidden-characters set populated by stealth / invisibility status.
    """

    gm_player_id: str | None
    player_id_to_character: dict[str, str] = field(default_factory=dict)
    party_id: str | None = None
    seat_assignments: dict[str, str] = field(default_factory=dict)
    character_zones: dict[str, str] = field(default_factory=dict)
    hidden_characters: set[str] = field(default_factory=set)

    def is_gm(self, player_id: str) -> bool:
        return self.gm_player_id is not None and player_id == self.gm_player_id

    def seat_of(self, player_id: str) -> str | None:
        return self.seat_assignments.get(player_id)

    def character_of(self, player_id: str) -> str | None:
        return self.player_id_to_character.get(player_id)

    def zone_of(self, character_id: str) -> str | None:
        return self.character_zones.get(character_id)

    def visible_to(self, viewer_character_id: str, target_character_id: str) -> bool:
        if target_character_id in self.hidden_characters:
            return False
        viewer_zone = self.character_zones.get(viewer_character_id)
        target_zone = self.character_zones.get(target_character_id)
        if viewer_zone is None or target_zone is None:
            return False
        return viewer_zone == target_zone

    def owner_of_item(self, item_id: str) -> str | None:
        return None  # Not yet tracked — stays conservative.

    def party_of(self, player_id: str) -> str | None:
        if player_id not in self.player_id_to_character:
            return None
        return self.party_id
```

- [ ] **Step 4: Run — expect PASS**

Run: `cd sidequest-server && uv run pytest tests/projection/test_view_zones.py -v`
Expected: 5 PASS.

- [ ] **Step 5: Wire session handler to populate zones**

Find the session-handler code that constructs `SessionGameStateView`:

```bash
grep -n "SessionGameStateView(" sidequest-server/sidequest/server/session_handler.py
```

At every construction site, add `character_zones=` and `hidden_characters=` populated from the session's current `scenario_state` / `EncounterState` / character status. The exact mapping depends on existing state structure — read the call site, find the zone-carrier object, pipe it through. Do not invent new tracking; use what's already computed.

- [ ] **Step 6: Write integration test for session-handler wiring**

Add to `sidequest-server/tests/server/test_session_handler_view.py` (create if missing):

```python
import pytest
from sidequest.server.session_handler import SessionHandler  # adjust if alias differs


@pytest.mark.asyncio
async def test_session_view_reflects_character_zones(populated_session_fixture):
    """After characters move, view.zone_of returns the current zone."""
    session = populated_session_fixture
    # Move Alice to "warehouse" via whatever movement API the session exposes.
    session.apply_zone_change(character_id="char_alice", zone="warehouse")
    view = session.game_state_view()
    assert view.zone_of("char_alice") == "warehouse"
```

If `populated_session_fixture` doesn't exist, copy the nearest existing session fixture from `tests/server/` and point it at a minimal pack. If `apply_zone_change` doesn't exist, name it after whatever the session already uses — the test's job is to *assert* the view reflects moves, not to invent API.

- [ ] **Step 7: Run all projection + server tests**

Run: `cd sidequest-server && uv run pytest tests/projection tests/server -v`
Expected: new tests PASS, all pre-existing tests still PASS.

- [ ] **Step 8: Commit**

```bash
git add sidequest-server/sidequest/game/projection/view.py \
        sidequest-server/sidequest/server/session_handler.py \
        sidequest-server/tests/projection/test_view_zones.py \
        sidequest-server/tests/server/test_session_handler_view.py
git commit -m "feat(projection): real zone + visibility tracking in SessionGameStateView

View no longer returns None/False by default — zones are fed from
SessionHandler's existing state. Unblocks VisibilityTagFilter wiring."
```

---

## Task 2: Visibility-baseline YAML schema + per-pack defaults (G1)

**Files:**
- Create: `sidequest-server/sidequest/genre/models/visibility.py`
- Create: `sidequest-content/genre_packs/caverns_and_claudes/visibility_baseline.yaml`
- Create: `sidequest-content/genre_packs/elemental_harmony/visibility_baseline.yaml`
- Create: `sidequest-content/genre_packs/heavy_metal/visibility_baseline.yaml`
- Create: `sidequest-content/genre_packs/mutant_wasteland/visibility_baseline.yaml`
- Create: `sidequest-content/genre_packs/space_opera/visibility_baseline.yaml`
- Create: `sidequest-content/genre_packs/spaghetti_western/visibility_baseline.yaml`
- Modify: `sidequest-server/sidequest/genre/pack_loader.py` (or equivalent — find the loader first)
- Test: `sidequest-server/tests/genre/test_visibility_baseline.py`

- [ ] **Step 1: Locate the genre pack loader entry point**

```bash
grep -rn "def load_pack\|GenrePack.load\|load_genre_pack" sidequest-server/sidequest/genre/ | head -10
```

Record the function the session handler calls at pack-load time. You will add `visibility_baseline` to its return shape.

- [ ] **Step 2: Write failing test for baseline schema**

Create `sidequest-server/tests/genre/test_visibility_baseline.py`:

```python
from pathlib import Path

import pytest

from sidequest.genre.models.visibility import (
    VisibilityBaseline,
    VisibilityOverrides,
    load_baseline,
    load_overrides,
    effective_visibility,
)


SAMPLE_BASELINE = """
tone: secret_heavy
default_visibility:
  npc_agency: all
  stealth_roll_check: actor_only
  lore_reveal: actor_only
status_effect_fidelity:
  blinded:
    visual_only: drop
    audio_only: keep
all_scope: protagonists
"""


def test_baseline_parses():
    baseline = VisibilityBaseline.model_validate_yaml(SAMPLE_BASELINE)
    assert baseline.tone == "secret_heavy"
    assert baseline.default_visibility["npc_agency"] == "all"
    assert baseline.status_effect_fidelity["blinded"]["visual_only"] == "drop"


def test_baseline_rejects_unknown_fidelity():
    bad = SAMPLE_BASELINE.replace("drop", "vaporize")
    with pytest.raises(ValueError, match="vaporize"):
        VisibilityBaseline.model_validate_yaml(bad)


def test_overrides_are_shallow_delta():
    baseline = VisibilityBaseline.model_validate_yaml(SAMPLE_BASELINE)
    overrides = VisibilityOverrides.model_validate_yaml(
        "default_visibility:\n  lore_reveal: all\n"
    )
    effective = effective_visibility(baseline, overrides)
    assert effective.default_visibility["lore_reveal"] == "all"
    assert effective.default_visibility["npc_agency"] == "all"  # unchanged
    assert effective.default_visibility["stealth_roll_check"] == "actor_only"  # unchanged


def test_loader_fails_loudly_on_missing_pack_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_baseline(tmp_path / "nonexistent" / "visibility_baseline.yaml")
```

- [ ] **Step 3: Run — expect FAIL (module does not exist)**

Run: `cd sidequest-server && uv run pytest tests/genre/test_visibility_baseline.py -v`
Expected: 4 ERROR — `ModuleNotFoundError: sidequest.genre.models.visibility`.

- [ ] **Step 4: Implement the schema**

Create `sidequest-server/sidequest/genre/models/visibility.py`:

```python
"""Visibility baseline + overrides — YAML schema loaded per genre pack + world.

The decomposer reads the effective (baseline + overrides) model at session
init and uses it as the default VisibilityTag emission when no turn state
suggests otherwise. The YAML lives in sidequest-content, not in this repo.

Validation is strict (extra='forbid'). Unknown subsystem names or fidelity
levels raise at pack-load time, not at runtime — see CLAUDE.md "no silent
fallbacks".
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

from sidequest.protocol.dispatch import PerceptionFidelity


Tone = Literal["broadcast_heavy", "balanced", "secret_heavy"]
AllScope = Literal["protagonists", "party_plus_guest_npcs"]
FidelityVerb = Literal["drop", "keep", "muffle"]

# Keep in sync with sidequest.agents.local_dm KNOWN_SUBSYSTEMS at Task-time.
# Kept here as a local constant rather than imported to break the cycle
# (local_dm imports from protocol, which would pull this in at runtime).
KNOWN_SUBSYSTEM_KEYS = frozenset({
    "npc_agency",
    "confrontation_init",
    "stealth_roll_check",
    "lore_reveal",
    "dice_roll_private",
    "exploration",
    "distinctive_detail",
    "reflect_absence",
})


class VisibilityBaseline(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tone: Tone
    default_visibility: dict[str, Literal["all", "actor_only", "audio_only_muffled"]]
    status_effect_fidelity: dict[str, dict[PerceptionFidelity, FidelityVerb]] = {}
    all_scope: AllScope = "protagonists"

    @model_validator(mode="after")
    def _known_subsystems(self) -> "VisibilityBaseline":
        unknown = set(self.default_visibility) - KNOWN_SUBSYSTEM_KEYS
        if unknown:
            raise ValueError(
                f"default_visibility references unknown subsystem(s): {sorted(unknown)}. "
                f"Allowed: {sorted(KNOWN_SUBSYSTEM_KEYS)}"
            )
        return self

    @classmethod
    def model_validate_yaml(cls, text: str) -> "VisibilityBaseline":
        raw = yaml.safe_load(text) or {}
        return cls.model_validate(raw)


class VisibilityOverrides(BaseModel):
    """Per-world deltas. Only fields that override baseline."""
    model_config = ConfigDict(extra="forbid")

    tone: Tone | None = None
    default_visibility: dict[str, Literal["all", "actor_only", "audio_only_muffled"]] = {}
    status_effect_fidelity: dict[str, dict[PerceptionFidelity, FidelityVerb]] = {}

    @classmethod
    def model_validate_yaml(cls, text: str) -> "VisibilityOverrides":
        raw = yaml.safe_load(text) or {}
        return cls.model_validate(raw)


def load_baseline(path: Path) -> VisibilityBaseline:
    """Load and validate visibility_baseline.yaml. Raises on missing/invalid."""
    return VisibilityBaseline.model_validate_yaml(path.read_text())


def load_overrides(path: Path) -> VisibilityOverrides:
    """Load and validate visibility_overrides.yaml. Raises on missing/invalid."""
    return VisibilityOverrides.model_validate_yaml(path.read_text())


def effective_visibility(
    baseline: VisibilityBaseline,
    overrides: VisibilityOverrides | None,
) -> VisibilityBaseline:
    """Return a new baseline with overrides' non-empty fields applied."""
    if overrides is None:
        return baseline
    merged = baseline.model_dump()
    if overrides.tone is not None:
        merged["tone"] = overrides.tone
    if overrides.default_visibility:
        merged["default_visibility"] = {
            **merged["default_visibility"],
            **overrides.default_visibility,
        }
    if overrides.status_effect_fidelity:
        merged_fx = dict(merged.get("status_effect_fidelity", {}))
        for effect, mapping in overrides.status_effect_fidelity.items():
            merged_fx[effect] = {**merged_fx.get(effect, {}), **mapping}
        merged["status_effect_fidelity"] = merged_fx
    return VisibilityBaseline.model_validate(merged)
```

- [ ] **Step 5: Run — expect PASS**

Run: `cd sidequest-server && uv run pytest tests/genre/test_visibility_baseline.py -v`
Expected: 4 PASS.

- [ ] **Step 6: Author pack YAMLs — 6 shipping packs**

Create one file per shipping pack. Contents below; adjust only if a pack's genre clearly demands otherwise (discuss before deviating).

`sidequest-content/genre_packs/caverns_and_claudes/visibility_baseline.yaml`:
```yaml
tone: balanced
default_visibility:
  npc_agency: all
  confrontation_init: all
  stealth_roll_check: actor_only
  lore_reveal: actor_only
  dice_roll_private: actor_only
status_effect_fidelity:
  blinded: {visual_only: drop, audio_only: keep}
  deafened: {audio_only: drop, visual_only: keep}
all_scope: protagonists
```

`sidequest-content/genre_packs/mutant_wasteland/visibility_baseline.yaml`:
```yaml
tone: secret_heavy
default_visibility:
  npc_agency: actor_only       # raiders keep their plans private
  confrontation_init: all
  stealth_roll_check: actor_only
  lore_reveal: actor_only
  dice_roll_private: actor_only
status_effect_fidelity:
  blinded: {visual_only: drop, audio_only: keep}
  deafened: {audio_only: drop, visual_only: keep}
all_scope: protagonists
```

`sidequest-content/genre_packs/spaghetti_western/visibility_baseline.yaml`:
```yaml
tone: secret_heavy
default_visibility:
  npc_agency: actor_only       # the man with no name knows nothing
  confrontation_init: all
  stealth_roll_check: actor_only
  lore_reveal: actor_only
  dice_roll_private: actor_only
status_effect_fidelity:
  blinded: {visual_only: drop, audio_only: keep}
all_scope: protagonists
```

`sidequest-content/genre_packs/space_opera/visibility_baseline.yaml`:
```yaml
tone: balanced
default_visibility:
  npc_agency: all              # bridge chatter is public
  confrontation_init: all
  stealth_roll_check: actor_only
  lore_reveal: actor_only
  dice_roll_private: actor_only
status_effect_fidelity:
  blinded: {visual_only: drop, audio_only: keep}
  deafened: {audio_only: drop, visual_only: keep}
all_scope: protagonists
```

`sidequest-content/genre_packs/heavy_metal/visibility_baseline.yaml`:
```yaml
tone: broadcast_heavy
default_visibility:
  npc_agency: all
  confrontation_init: all
  stealth_roll_check: actor_only
  lore_reveal: all
  dice_roll_private: actor_only
status_effect_fidelity:
  blinded: {visual_only: drop, audio_only: keep}
  deafened: {audio_only: drop, visual_only: keep}
all_scope: protagonists
```

`sidequest-content/genre_packs/elemental_harmony/visibility_baseline.yaml`:
```yaml
tone: balanced
default_visibility:
  npc_agency: all
  confrontation_init: all
  stealth_roll_check: actor_only
  lore_reveal: actor_only
  dice_roll_private: actor_only
status_effect_fidelity:
  blinded: {visual_only: drop, audio_only: keep}
  deafened: {audio_only: drop, visual_only: keep}
all_scope: protagonists
```

- [ ] **Step 7: Write pack-load integration test**

Add to `sidequest-server/tests/genre/test_visibility_baseline.py`:

```python
@pytest.mark.parametrize("pack", [
    "caverns_and_claudes",
    "elemental_harmony",
    "heavy_metal",
    "mutant_wasteland",
    "space_opera",
    "spaghetti_western",
])
def test_every_shipping_pack_has_valid_baseline(pack):
    import os
    root = Path(os.environ["SIDEQUEST_GENRE_PACKS"])
    path = root / pack / "visibility_baseline.yaml"
    assert path.exists(), f"missing: {path}"
    baseline = load_baseline(path)
    assert baseline.tone in ("broadcast_heavy", "balanced", "secret_heavy")
```

- [ ] **Step 8: Wire the loader**

Open the loader function located in Step 1. Add a `visibility_baseline: VisibilityBaseline` field to whatever pack model it returns (likely `GenrePack` in `sidequest/genre/models/pack.py`). At load time:

```python
from sidequest.genre.models.visibility import load_baseline
# ...
baseline_path = pack_dir / "visibility_baseline.yaml"
visibility_baseline = load_baseline(baseline_path)  # fails loudly if absent
```

Do the same for world-level overrides if a world dir is being loaded:

```python
overrides_path = world_dir / "visibility_overrides.yaml"
visibility_overrides = (
    load_overrides(overrides_path) if overrides_path.exists() else None
)
```

- [ ] **Step 9: Run full genre test suite**

Run: `cd sidequest-server && uv run pytest tests/genre -v`
Expected: all PASS. If a pre-existing pack fixture blows up because it lacks `visibility_baseline.yaml`, add the file to that fixture pack rather than making the field optional.

- [ ] **Step 10: Commit**

```bash
git add sidequest-server/sidequest/genre/models/visibility.py \
        sidequest-server/sidequest/genre/ \
        sidequest-content/genre_packs/*/visibility_baseline.yaml \
        sidequest-server/tests/genre/test_visibility_baseline.py
git commit -m "feat(genre): visibility_baseline.yaml schema + 6 pack defaults

Decomposer reads these at session init. Tone ranges from broadcast_heavy
(Heavy Metal) to secret_heavy (Mutant Wasteland, Spaghetti Western).
Loader fails loudly on missing pack file."
```

---

## Task 3: `visibility_tag` rule kind in `GenreRuleStage` (G2)

**Files:**
- Modify: `sidequest-server/sidequest/game/projection/rules.py:43-117`
- Modify: `sidequest-server/sidequest/game/projection/genre_stage.py:53-131`
- Test: `sidequest-server/tests/projection/test_visibility_tag_rule.py`

- [ ] **Step 1: Write failing test for rule parsing**

Create `sidequest-server/tests/projection/test_visibility_tag_rule.py`:

```python
import json

import pytest

from sidequest.game.projection.envelope import MessageEnvelope
from sidequest.game.projection.genre_stage import GenreRuleStage
from sidequest.game.projection.rules import load_rules_from_yaml_str
from sidequest.game.projection.view import SessionGameStateView


YAML = """
rules:
  - kind: NARRATION
    visibility_tag: {}
"""


def test_visibility_tag_rule_parses():
    rules = load_rules_from_yaml_str(YAML)
    assert len(rules.rules) == 1
    assert rules.rules[0].kind == "NARRATION"


def _env(kind: str, payload: dict, seq: int = 1) -> MessageEnvelope:
    return MessageEnvelope(kind=kind, payload_json=json.dumps(payload), origin_seq=seq)


def test_excludes_when_player_not_in_visible_to():
    stage = GenreRuleStage(load_rules_from_yaml_str(YAML))
    view = SessionGameStateView(
        gm_player_id=None,
        player_id_to_character={"p1": "c1", "p2": "c2"},
    )
    payload = {"text": "Alice sneaks.", "_visibility": {"visible_to": ["p1"]}}
    result = stage.evaluate(envelope=_env("NARRATION", payload), view=view, player_id="p2")
    assert result.decision.include is False


def test_includes_when_player_in_visible_to():
    stage = GenreRuleStage(load_rules_from_yaml_str(YAML))
    view = SessionGameStateView(
        gm_player_id=None,
        player_id_to_character={"p1": "c1", "p2": "c2"},
    )
    payload = {"text": "Alice sneaks.", "_visibility": {"visible_to": ["p1"]}}
    result = stage.evaluate(envelope=_env("NARRATION", payload), view=view, player_id="p1")
    assert result.decision.include is True


def test_all_means_all():
    stage = GenreRuleStage(load_rules_from_yaml_str(YAML))
    view = SessionGameStateView(
        gm_player_id=None,
        player_id_to_character={"p1": "c1", "p2": "c2"},
    )
    payload = {"text": "Dawn breaks.", "_visibility": {"visible_to": "all"}}
    result = stage.evaluate(envelope=_env("NARRATION", payload), view=view, player_id="p2")
    assert result.decision.include is True


def test_missing_visibility_falls_through_to_pass_through():
    stage = GenreRuleStage(load_rules_from_yaml_str(YAML))
    view = SessionGameStateView(
        gm_player_id=None,
        player_id_to_character={"p1": "c1"},
    )
    payload = {"text": "No viz key."}
    result = stage.evaluate(envelope=_env("NARRATION", payload), view=view, player_id="p1")
    assert result.decision.include is True


def test_fidelity_transform_strips_visual_spans_for_blinded():
    stage = GenreRuleStage(load_rules_from_yaml_str(YAML))
    view = SessionGameStateView(
        gm_player_id=None,
        player_id_to_character={"p1": "c1"},
    )
    payload = {
        "text": "You hear a crash.",
        "spans": [
            {"id": "s1", "kind": "visual_only", "text": "a glint of steel"},
            {"id": "s2", "kind": "audio_only", "text": "a wet thud"},
        ],
        "_visibility": {
            "visible_to": "all",
            "fidelity": {"p1": "audio_only"},
        },
    }
    result = stage.evaluate(envelope=_env("NARRATION", payload), view=view, player_id="p1")
    assert result.decision.include is True
    out = json.loads(result.decision.payload_json)
    span_ids = [s["id"] for s in out["spans"]]
    assert "s1" not in span_ids  # visual_only stripped
    assert "s2" in span_ids      # audio_only kept
```

- [ ] **Step 2: Run — expect FAIL (rule variant does not exist)**

Run: `cd sidequest-server && uv run pytest tests/projection/test_visibility_tag_rule.py -v`
Expected: ValueError on rule parsing — rule entry must carry exactly one of target_only/include_if/redact_fields.

- [ ] **Step 3: Add `VisibilityTagRule` variant to `rules.py`**

Edit `sidequest-server/sidequest/game/projection/rules.py`.

After `RedactFieldsRule` (line 82-84) add:

```python
class VisibilityTagSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    # No fields yet — the rule reads _visibility from payload. Reserved for
    # future GM-panel overrides.


class VisibilityTagRule(_RuleBase):
    visibility_tag: VisibilityTagSpec
```

Update `ProjectionRule` annotation (line 86-89):

```python
ProjectionRule = Annotated[
    TargetOnlyRule | IncludeIfRule | RedactFieldsRule | VisibilityTagRule,
    Field(discriminator=None),
]
```

Update `_disambiguate_rule_variants` (line 96-117) to accept the new action key:

```python
@model_validator(mode="before")
@classmethod
def _disambiguate_rule_variants(cls, data: object) -> object:
    if not isinstance(data, dict):
        return data
    raw_rules = data.get("rules")
    if not isinstance(raw_rules, list):
        return data

    coerced: list[dict] = []
    for r in raw_rules:
        if not isinstance(r, dict):
            raise ValueError(f"rule entry must be a mapping, got {type(r).__name__}")
        present = [
            k for k in ("target_only", "include_if", "redact_fields", "visibility_tag")
            if k in r
        ]
        if len(present) != 1:
            raise ValueError(
                f"rule for kind={r.get('kind')!r} must carry exactly one of "
                f"target_only/include_if/redact_fields/visibility_tag; found {present}"
            )
        coerced.append(r)
    return {**data, "rules": coerced}
```

- [ ] **Step 4: Implement evaluator in `genre_stage.py`**

Edit `sidequest-server/sidequest/game/projection/genre_stage.py`.

Add import at line 17-22:
```python
from sidequest.game.projection.rules import (
    IncludeIfRule,
    ProjectionRules,
    RedactFieldsRule,
    TargetOnlyRule,
    VisibilityTagRule,
)
```

In the evaluation loop (around line 83-126), add a new branch **before** the `TargetOnlyRule` branch so visibility_tag runs first:

```python
for rule_idx, rule in rules:
    if isinstance(rule, VisibilityTagRule):
        viz = payload.get("_visibility")
        if isinstance(viz, dict):
            visible_to = viz.get("visible_to")
            if visible_to != "all":
                if not isinstance(visible_to, list) or player_id not in visible_to:
                    return GenreEvalResult(
                        decision=FilterDecision(include=False, payload_json=""),
                        matched_rule_index=rule_idx,
                    )
            fidelity_map = viz.get("fidelity") or {}
            player_fidelity = fidelity_map.get(player_id)
            if player_fidelity:
                working = _apply_fidelity(working, player_fidelity)
                last_applied_idx = rule_idx
        # If _visibility is absent, fall through (legacy events unaffected).

    if isinstance(rule, TargetOnlyRule):
        # ... existing code unchanged
```

Add `_apply_fidelity` helper at the bottom of the file:

```python
def _apply_fidelity(payload: dict, fidelity: str) -> dict:
    """Strip span entries whose 'kind' is incompatible with the recipient's fidelity.

    Fidelity buckets (from sidequest.protocol.dispatch.PerceptionFidelity):
        full                     — no change
        audio_only               — drop visual_only spans
        audio_only_muffled       — drop visual_only; tag audio_only with 'muffled'
        visual_only              — drop audio_only spans
        periphery_only           — keep only spans marked 'periphery_tolerant'
        inferred_from_aftermath  — keep only spans marked 'aftermath'

    Operates on payload['spans'] if present; no-op for legacy payloads without spans.
    """
    if fidelity == "full":
        return payload
    spans = payload.get("spans")
    if not isinstance(spans, list):
        return payload

    def keep(span: dict) -> bool:
        kind = span.get("kind", "full")
        if fidelity == "audio_only":
            return kind != "visual_only"
        if fidelity == "audio_only_muffled":
            return kind != "visual_only"
        if fidelity == "visual_only":
            return kind != "audio_only"
        if fidelity == "periphery_only":
            return bool(span.get("periphery_tolerant"))
        if fidelity == "inferred_from_aftermath":
            return bool(span.get("aftermath"))
        return True

    filtered = [s for s in spans if keep(s)]
    if fidelity == "audio_only_muffled":
        filtered = [{**s, "muffled": True} if s.get("kind") == "audio_only" else s
                    for s in filtered]
    return {**payload, "spans": filtered}
```

- [ ] **Step 5: Run — expect PASS**

Run: `cd sidequest-server && uv run pytest tests/projection/test_visibility_tag_rule.py tests/projection -v`
Expected: new tests PASS, prior rule tests unchanged.

- [ ] **Step 6: Add rule to shipping pack projection.yaml files**

For each of the 6 packs, find or create `sidequest-content/genre_packs/<pack>/projection.yaml` and ensure:

```yaml
rules:
  - kind: NARRATION
    visibility_tag: {}
  # ... any existing rules below
```

If `projection.yaml` does not exist for a pack, create it with only the visibility_tag rule. Do this for all 6 packs.

- [ ] **Step 7: Commit**

```bash
git add sidequest-server/sidequest/game/projection/rules.py \
        sidequest-server/sidequest/game/projection/genre_stage.py \
        sidequest-server/tests/projection/test_visibility_tag_rule.py \
        sidequest-content/genre_packs/*/projection.yaml
git commit -m "feat(projection): visibility_tag rule kind + fidelity transform

Filters envelopes against payload._visibility.visible_to and applies
per-recipient fidelity to spans. Ordered FIRST in the rule chain so
structural decisions are not re-opened by later redactions."
```

---

## Task 4: Decomposer emits real `VisibilityTag` values (G1 consumer)

**Files:**
- Modify: `sidequest-server/sidequest/agents/local_dm.py` (prompt template + post-parse defaults)
- Modify: `sidequest-server/sidequest/server/session_handler.py` (attach `_visibility` to canonical NARRATION payload)
- Test: `sidequest-server/tests/agents/test_local_dm_visibility.py`

- [ ] **Step 1: Read the existing decomposer**

```bash
sed -n '60,120p' sidequest-server/sidequest/agents/local_dm.py
```

Identify: the prompt template that instructs the LLM on `VisibilityTag` emission, and where stub values (`visible_to="all"`) are hardcoded. The changes below target those sites.

- [ ] **Step 2: Write failing test — baseline-driven defaults**

Create `sidequest-server/tests/agents/test_local_dm_visibility.py`:

```python
import pytest

from sidequest.agents.local_dm import apply_visibility_baseline
from sidequest.genre.models.visibility import VisibilityBaseline


BASELINE_SECRET = VisibilityBaseline.model_validate_yaml("""
tone: secret_heavy
default_visibility:
  stealth_roll_check: actor_only
  npc_agency: actor_only
  lore_reveal: actor_only
all_scope: protagonists
""")


def test_stealth_roll_defaults_to_actor_only():
    dispatch = {
        "subsystem": "stealth_roll_check",
        "params": {"actor": "player:Alice"},
        "idempotency_key": "k1",
        "visibility": {"visible_to": "all", "perception_fidelity": {},
                       "secrets_for": [], "redact_from_narrator_canonical": False},
    }
    applied = apply_visibility_baseline(
        dispatch, baseline=BASELINE_SECRET, actor_player_id="player:Alice",
    )
    assert applied["visibility"]["visible_to"] == ["player:Alice"]


def test_dispatch_with_explicit_tag_is_untouched():
    dispatch = {
        "subsystem": "stealth_roll_check",
        "params": {"actor": "player:Alice"},
        "idempotency_key": "k1",
        "visibility": {"visible_to": ["player:Alice", "player:Bob"],
                       "perception_fidelity": {}, "secrets_for": [],
                       "redact_from_narrator_canonical": False},
        "_visibility_explicit": True,
    }
    applied = apply_visibility_baseline(
        dispatch, baseline=BASELINE_SECRET, actor_player_id="player:Alice",
    )
    assert applied["visibility"]["visible_to"] == ["player:Alice", "player:Bob"]


def test_unknown_subsystem_leaves_all():
    dispatch = {
        "subsystem": "confrontation_init",   # not in our test baseline
        "params": {"actor": "player:Alice"},
        "idempotency_key": "k1",
        "visibility": {"visible_to": "all", "perception_fidelity": {},
                       "secrets_for": [], "redact_from_narrator_canonical": False},
    }
    applied = apply_visibility_baseline(
        dispatch, baseline=BASELINE_SECRET, actor_player_id="player:Alice",
    )
    assert applied["visibility"]["visible_to"] == "all"
```

- [ ] **Step 3: Run — expect FAIL**

Run: `cd sidequest-server && uv run pytest tests/agents/test_local_dm_visibility.py -v`
Expected: ImportError — `apply_visibility_baseline` not defined.

- [ ] **Step 4: Implement `apply_visibility_baseline`**

Edit `sidequest-server/sidequest/agents/local_dm.py`. Add near the top (after existing imports):

```python
from sidequest.genre.models.visibility import VisibilityBaseline


def apply_visibility_baseline(
    dispatch: dict,
    *,
    baseline: VisibilityBaseline,
    actor_player_id: str,
) -> dict:
    """Fill in VisibilityTag defaults from baseline for a decomposer dispatch dict.

    Respects explicit tags — a dispatch already flagged `_visibility_explicit: True`
    keeps whatever the decomposer chose. Called per dispatch after LLM parse.
    """
    if dispatch.get("_visibility_explicit"):
        return dispatch
    subsystem = dispatch.get("subsystem")
    mode = baseline.default_visibility.get(subsystem)
    if mode is None:
        return dispatch  # Unknown subsystem — leave as-is (decomposer's choice stands).
    viz = dict(dispatch.get("visibility", {}))
    if mode == "actor_only":
        viz["visible_to"] = [actor_player_id]
    elif mode == "all":
        viz["visible_to"] = "all"
    return {**dispatch, "visibility": viz}
```

- [ ] **Step 5: Run — expect PASS**

Run: `cd sidequest-server && uv run pytest tests/agents/test_local_dm_visibility.py -v`
Expected: 3 PASS.

- [ ] **Step 6: Wire `apply_visibility_baseline` at decomposer post-parse**

In `local_dm.py`, find where `DispatchPackage.model_validate` is called on the parsed LLM output. Immediately before validation (while the dict is still mutable), iterate every `per_player[i].dispatch[j]` and apply `apply_visibility_baseline(d, baseline=session.baseline, actor_player_id=per_player[i].player_id)`. Apply the same to `per_player[i].narrator_instructions` and `per_player[i].lethality` (use a parallel helper for those if their visibility field shapes differ enough to warrant it — they don't, so one helper is fine).

- [ ] **Step 7: Attach `_visibility` to canonical NARRATION payload**

In `session_handler.py`, find the code that emits the canonical `NARRATION` event per turn. After the narrator produces prose, before the event hits `EventLog.append`:

```python
narration_payload = {
    "round_number": round_num,
    "text": canonical_text,
    "spans": spans,  # if the narrator emits structured spans; else []
    "_visibility": aggregate_visibility(dispatch_package),
}
```

Where `aggregate_visibility` unions the `visible_to` lists across all tagged dispatches for this turn's narration scope. Put the helper in `sidequest/server/session_handler.py` or a sibling util module:

```python
def aggregate_visibility(pkg: DispatchPackage) -> dict:
    """Produce the _visibility sidecar for the canonical narration payload.

    Rules:
      - visible_to is the union of all non-redacted tags' visible_to lists.
      - "all" is a stop word — any "all" tag collapses the union to "all".
      - fidelity maps merge; later wins on collision (should not occur).
      - redacted events (redact_from_narrator_canonical=True) are NOT aggregated
        here — they route via SECRET_NOTE in Task 6.
    """
    any_all = False
    union: set[str] = set()
    fidelity: dict[str, str] = {}
    for pd in pkg.per_player:
        for d in pd.dispatch:
            if d.visibility.redact_from_narrator_canonical:
                continue
            if d.visibility.visible_to == "all":
                any_all = True
            else:
                union.update(d.visibility.visible_to)
            fidelity.update(d.visibility.perception_fidelity)
    return {
        "visible_to": "all" if any_all else sorted(union),
        "fidelity": fidelity,
    }
```

- [ ] **Step 8: Run full server test suite**

Run: `cd sidequest-server && uv run pytest -v`
Expected: all PASS.

- [ ] **Step 9: Commit**

```bash
git add sidequest-server/sidequest/agents/local_dm.py \
        sidequest-server/sidequest/server/session_handler.py \
        sidequest-server/tests/agents/test_local_dm_visibility.py
git commit -m "feat(local_dm): apply baseline defaults to VisibilityTag emission

Decomposer dispatches without explicit visibility get baseline-driven
defaults (secret_heavy packs -> actor_only; broadcast_heavy -> all).
Canonical NARRATION payload grows _visibility sidecar from the union
of per-turn dispatch tags."
```

---

## Task 5: Structural hiding in narrator prompt builder (G3)

**Files:**
- Create: `sidequest-server/sidequest/agents/prompt_redaction.py`
- Modify: `sidequest-server/sidequest/agents/narrator.py` (call redact before LLM)
- Test: `sidequest-server/tests/agents/test_prompt_redaction.py`

- [ ] **Step 1: Write failing test**

Create `sidequest-server/tests/agents/test_prompt_redaction.py`:

```python
from sidequest.agents.prompt_redaction import redact_dispatch_package
from sidequest.protocol.dispatch import (
    DispatchPackage,
    NarratorDirective,
    PlayerDispatch,
    SubsystemDispatch,
    VisibilityTag,
)


def _redacted_viz(who: str) -> VisibilityTag:
    return VisibilityTag(
        visible_to=[who],
        perception_fidelity={},
        secrets_for=[who],
        redact_from_narrator_canonical=True,
    )


def _open_viz() -> VisibilityTag:
    return VisibilityTag(
        visible_to="all",
        perception_fidelity={},
        secrets_for=[],
        redact_from_narrator_canonical=False,
    )


def test_redacted_dispatch_stripped_entirely():
    pkg = DispatchPackage(
        turn_id="t1",
        per_player=[PlayerDispatch(
            player_id="player:Alice",
            raw_action="kill guard",
            dispatch=[
                SubsystemDispatch(
                    subsystem="lethal_strike",
                    params={"target": "guard_A"},
                    idempotency_key="k1",
                    visibility=_redacted_viz("player:Alice"),
                ),
                SubsystemDispatch(
                    subsystem="movement",
                    params={"to": "warehouse"},
                    idempotency_key="k2",
                    visibility=_open_viz(),
                ),
            ],
        )],
        confidence_global=1.0,
    )
    redacted, removed = redact_dispatch_package(pkg)
    assert len(removed) == 1
    assert removed[0].idempotency_key == "k1"
    assert len(redacted.per_player[0].dispatch) == 1
    assert redacted.per_player[0].dispatch[0].idempotency_key == "k2"


def test_redacted_narrator_directive_stripped():
    pkg = DispatchPackage(
        turn_id="t1",
        per_player=[PlayerDispatch(
            player_id="player:Alice",
            raw_action="observe",
            narrator_instructions=[
                NarratorDirective(
                    kind="must_not_narrate",
                    payload="Alice_assassination_event",
                    visibility=_redacted_viz("player:Alice"),
                ),
                NarratorDirective(
                    kind="must_narrate",
                    payload="The dogs bark.",
                    visibility=_open_viz(),
                ),
            ],
        )],
        confidence_global=1.0,
    )
    redacted, removed = redact_dispatch_package(pkg)
    assert len(removed) == 1
    assert len(redacted.per_player[0].narrator_instructions) == 1
    assert redacted.per_player[0].narrator_instructions[0].payload == "The dogs bark."


def test_no_redactions_is_noop():
    pkg = DispatchPackage(
        turn_id="t1",
        per_player=[PlayerDispatch(player_id="player:Alice", raw_action="look")],
        confidence_global=1.0,
    )
    redacted, removed = redact_dispatch_package(pkg)
    assert removed == []
    assert redacted == pkg
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd sidequest-server && uv run pytest tests/agents/test_prompt_redaction.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement**

Create `sidequest-server/sidequest/agents/prompt_redaction.py`:

```python
"""Structural hiding — strips redact_from_narrator_canonical entries from a
DispatchPackage BEFORE it enters the narrator prompt.

Primary defense in Group G's two-layer redaction model. The narrator cannot
leak what it never saw; this module is what ensures it never sees it.

Paired with the OTEL leak-audit (sidequest.telemetry.leak_audit) which
verifies this module's output is actually reflected in canonical prose.
"""
from __future__ import annotations

from dataclasses import replace
from typing import cast

from opentelemetry import trace

from sidequest.protocol.dispatch import (
    DispatchPackage,
    LethalityVerdict,
    NarratorDirective,
    PlayerDispatch,
    SubsystemDispatch,
)


_tracer = trace.get_tracer("sidequest.prompt_redaction")


def redact_dispatch_package(
    pkg: DispatchPackage,
) -> tuple[DispatchPackage, list[SubsystemDispatch | NarratorDirective | LethalityVerdict]]:
    """Return (pkg_without_redacted_entries, list_of_removed_entries).

    Called by the narrator before prompt assembly. Removed entries are
    returned so the caller can route them to SECRET_NOTE channels (Task 6).
    """
    removed: list[SubsystemDispatch | NarratorDirective | LethalityVerdict] = []
    new_players: list[PlayerDispatch] = []

    for pd in pkg.per_player:
        kept_dispatch = []
        for d in pd.dispatch:
            if d.visibility.redact_from_narrator_canonical:
                removed.append(d)
            else:
                kept_dispatch.append(d)
        kept_directives = []
        for n in pd.narrator_instructions:
            if n.visibility.redact_from_narrator_canonical:
                removed.append(n)
            else:
                kept_directives.append(n)
        # LethalityVerdict does not carry a VisibilityTag in the current
        # protocol shape — the decomposer spec has it emitting via the
        # sibling SubsystemDispatch. If that changes, add a branch here.
        new_players.append(
            replace(pd, dispatch=kept_dispatch, narrator_instructions=kept_directives)
            if hasattr(pd, "__replace__")
            else pd.model_copy(update={
                "dispatch": kept_dispatch,
                "narrator_instructions": kept_directives,
            })
        )

    if removed:
        with _tracer.start_as_current_span("prompt.redaction.structural") as span:
            span.set_attribute("turn_id", pkg.turn_id)
            span.set_attribute("redacted_count", len(removed))
            span.set_attribute(
                "redacted_kinds",
                [type(r).__name__ for r in removed],
            )
            span.set_attribute(
                "redacted_idempotency_keys",
                [r.idempotency_key for r in removed if isinstance(r, SubsystemDispatch)],
            )

    redacted_pkg = pkg.model_copy(update={"per_player": new_players})
    return redacted_pkg, removed
```

- [ ] **Step 4: Run — expect PASS**

Run: `cd sidequest-server && uv run pytest tests/agents/test_prompt_redaction.py -v`
Expected: 3 PASS.

- [ ] **Step 5: Call redaction from the narrator**

Edit `sidequest-server/sidequest/agents/narrator.py`. Find where the narrator receives a `DispatchPackage` and assembles its prompt. Before prompt construction:

```python
from sidequest.agents.prompt_redaction import redact_dispatch_package

# ... inside the narrate-a-turn method:
visible_pkg, removed = redact_dispatch_package(pkg)
# Hand `removed` to the session handler via the existing return channel
# so SECRET_NOTE routing (Task 6) can pick them up.
prompt = self._build_prompt(visible_pkg, ...)
```

The narrator's return type likely needs to grow a `secret_routes` field; if adding a new field is a bigger surgery than you expect, temporarily attach `removed` as a session-level side channel and fix the type in Task 6.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/agents/prompt_redaction.py \
        sidequest-server/sidequest/agents/narrator.py \
        sidequest-server/tests/agents/test_prompt_redaction.py
git commit -m "feat(narrator): structural hiding of redact_from_narrator_canonical

Redacted dispatches/directives never enter the prompt. OTEL span
'prompt.redaction.structural' fires on non-zero redaction counts."
```

---

## Task 6: SECRET_NOTE message kind + routing (G4)

**Files:**
- Modify: `sidequest-server/sidequest/protocol/messages.py` (add `SECRET_NOTE`)
- Modify: `sidequest-server/sidequest/server/session_handler.py` (route `removed` → SECRET_NOTE events)
- Test: `sidequest-server/tests/server/test_secret_note_routing.py`

- [ ] **Step 1: Find message-kind definitions**

```bash
grep -rn "class MessageType\|SECRET\|NARRATION" sidequest-server/sidequest/protocol/messages.py | head -10
```

Identify the message-kind enum/Literal and the payload model pattern.

- [ ] **Step 2: Write failing test**

Create `sidequest-server/tests/server/test_secret_note_routing.py`:

```python
import json
import pytest

from sidequest.protocol.dispatch import (
    DispatchPackage, PlayerDispatch, SubsystemDispatch, VisibilityTag,
)
# Adjust import paths if your session module differs.
from sidequest.server.session_handler import build_secret_note_events


def _redacted_dispatch(key: str, actor: str, payload: dict) -> SubsystemDispatch:
    return SubsystemDispatch(
        subsystem="lethal_strike",
        params=payload,
        idempotency_key=key,
        visibility=VisibilityTag(
            visible_to=[actor],
            perception_fidelity={},
            secrets_for=[actor],
            redact_from_narrator_canonical=True,
        ),
    )


def test_one_secret_note_per_redacted_dispatch():
    removed = [
        _redacted_dispatch("k1", "player:Alice", {"target": "guard_A"}),
    ]
    events = build_secret_note_events(removed, turn_id="t42")
    assert len(events) == 1
    assert events[0].kind == "SECRET_NOTE"
    p = json.loads(events[0].payload_json)
    assert p["turn_id"] == "t42"
    assert p["idempotency_key"] == "k1"
    assert p["_visibility"]["visible_to"] == ["player:Alice"]
    assert p["_visibility"].get("redact_from_narrator_canonical") in (True, None)


def test_empty_input_produces_no_events():
    assert build_secret_note_events([], turn_id="t0") == []
```

- [ ] **Step 3: Run — expect FAIL**

Expected: ImportError.

- [ ] **Step 4: Add `SECRET_NOTE` to the message-kind schema**

In `sidequest-server/sidequest/protocol/messages.py`, add `"SECRET_NOTE"` to the message-kind enum/Literal. If there is a payload schema map, add a schema entry allowing `turn_id: str`, `idempotency_key: str`, `subsystem: str`, `params: dict`, `_visibility: dict`.

- [ ] **Step 5: Implement `build_secret_note_events`**

In `sidequest-server/sidequest/server/session_handler.py`, add (or put in a sibling util file and import):

```python
from sidequest.game.projection.envelope import MessageEnvelope
from sidequest.protocol.dispatch import SubsystemDispatch


def build_secret_note_events(
    removed: list,
    *,
    turn_id: str,
) -> list[MessageEnvelope]:
    """Build SECRET_NOTE envelopes from prompt-redacted entries.

    Only SubsystemDispatch entries currently produce SECRET_NOTE events.
    NarratorDirective entries were never externally visible; their removal
    is already expressed by the narrator not mentioning the event.
    """
    out: list[MessageEnvelope] = []
    for i, entry in enumerate(removed):
        if not isinstance(entry, SubsystemDispatch):
            continue
        payload = {
            "turn_id": turn_id,
            "idempotency_key": entry.idempotency_key,
            "subsystem": entry.subsystem,
            "params": entry.params,
            "_visibility": {
                "visible_to": entry.visibility.visible_to,
                "fidelity": entry.visibility.perception_fidelity,
            },
        }
        out.append(MessageEnvelope(
            kind="SECRET_NOTE",
            payload_json=json.dumps(payload),
            origin_seq=0,  # session handler assigns real seq at dispatch time
        ))
    return out
```

- [ ] **Step 6: Route SECRET_NOTE through the filter pipeline**

In the session-handler turn-driver code where `EventLog.append` happens for canonical narration, after the narration envelope is logged, also log the SECRET_NOTE envelopes:

```python
secret_notes = build_secret_note_events(removed_from_redaction, turn_id=pkg.turn_id)
for note in secret_notes:
    event_log.append(note)  # goes through the same filter pipeline
```

Add `SECRET_NOTE` to projection.yaml in every shipping pack:

```yaml
# sidequest-content/genre_packs/<pack>/projection.yaml
rules:
  - kind: NARRATION
    visibility_tag: {}
  - kind: SECRET_NOTE
    visibility_tag: {}
```

- [ ] **Step 7: Run tests**

Run: `cd sidequest-server && uv run pytest tests/server/test_secret_note_routing.py tests/server tests/projection -v`
Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git add sidequest-server/sidequest/protocol/messages.py \
        sidequest-server/sidequest/server/session_handler.py \
        sidequest-server/tests/server/test_secret_note_routing.py \
        sidequest-content/genre_packs/*/projection.yaml
git commit -m "feat(protocol): SECRET_NOTE message kind + routing from prompt-redacted dispatch

Redacted dispatches become per-recipient SECRET_NOTE events that flow
through the same filter pipeline. Visible only to their visible_to list
via visibility_tag rule."
```

---

## Task 7: Canonical-leak audit (G5)

**Files:**
- Create: `sidequest-server/sidequest/telemetry/leak_audit.py`
- Modify: `sidequest-server/sidequest/agents/narrator.py` (call audit after narration)
- Create: `scenarios/asymmetric_smoke.yaml`
- Test: `sidequest-server/tests/telemetry/test_leak_audit.py`

- [ ] **Step 1: Write failing test**

Create `sidequest-server/tests/telemetry/test_leak_audit.py`:

```python
from sidequest.protocol.dispatch import (
    DispatchPackage, PlayerDispatch, SubsystemDispatch, VisibilityTag,
)
from sidequest.telemetry.leak_audit import audit_canonical_prose


def _redacted(actor: str, params: dict) -> SubsystemDispatch:
    return SubsystemDispatch(
        subsystem="lethal_strike",
        params=params,
        idempotency_key="k1",
        visibility=VisibilityTag(
            visible_to=[actor], perception_fidelity={}, secrets_for=[actor],
            redact_from_narrator_canonical=True,
        ),
    )


def test_zero_leaks_when_prose_clean():
    pkg = DispatchPackage(
        turn_id="t1",
        per_player=[PlayerDispatch(
            player_id="player:Alice", raw_action="sneak",
            dispatch=[_redacted("player:Alice", {"target": "guard_A"})],
        )],
        confidence_global=1.0,
    )
    result = audit_canonical_prose(
        prose="The evening wears on at the inn.",
        package=pkg,
        entity_tokens_by_id={"guard_A": ["Rickard", "the guard"]},
    )
    assert result.leaks_detected == 0
    assert result.leaked_entities == []


def test_leak_detected_when_redacted_entity_appears():
    pkg = DispatchPackage(
        turn_id="t1",
        per_player=[PlayerDispatch(
            player_id="player:Alice", raw_action="sneak",
            dispatch=[_redacted("player:Alice", {"target": "guard_A"})],
        )],
        confidence_global=1.0,
    )
    result = audit_canonical_prose(
        prose="Rickard the guard slumps against the crate.",
        package=pkg,
        entity_tokens_by_id={"guard_A": ["Rickard", "the guard"]},
    )
    assert result.leaks_detected >= 1
    assert "guard_A" in result.leaked_entities


def test_no_redacted_entries_means_no_audit_work():
    pkg = DispatchPackage(
        turn_id="t1",
        per_player=[PlayerDispatch(player_id="player:Alice", raw_action="look")],
        confidence_global=1.0,
    )
    result = audit_canonical_prose(
        prose="Anything at all.", package=pkg, entity_tokens_by_id={},
    )
    assert result.leaks_detected == 0
    assert result.redact_tag_count == 0
```

- [ ] **Step 2: Run — expect FAIL**

Expected: ImportError.

- [ ] **Step 3: Implement**

Create `sidequest-server/sidequest/telemetry/leak_audit.py`:

```python
"""Canonical-leak audit — safety-net verification.

Primary defense is structural hiding (prompt_redaction.py). This module
verifies the narrator's canonical prose contains no tokens corresponding to
redacted entities. Expected-zero detections in steady state; any non-zero
count is a structural-hiding bug.

The match is entity-token-set vs. prose, NOT regex on arbitrary strings —
tokens are supplied by the caller from the authoritative NPC registry.
This satisfies the SOUL.md Zork constraint: no keyword matching.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from opentelemetry import trace

from sidequest.protocol.dispatch import DispatchPackage, SubsystemDispatch


_tracer = trace.get_tracer("sidequest.leak_audit")


@dataclass(frozen=True)
class LeakAuditResult:
    turn_id: str
    leaks_detected: int
    redact_tag_count: int
    leaked_entities: list[str] = field(default_factory=list)
    leaked_fragments: list[str] = field(default_factory=list)


def audit_canonical_prose(
    *,
    prose: str,
    package: DispatchPackage,
    entity_tokens_by_id: dict[str, list[str]],
) -> LeakAuditResult:
    """Scan prose for tokens from entities flagged redact_from_narrator_canonical.

    entity_tokens_by_id maps entity_id -> list of tokens (display name,
    aliases, role) drawn from the NPC registry / character sheet.
    """
    redacted_entities: list[str] = []
    for pd in package.per_player:
        for d in pd.dispatch:
            if not isinstance(d, SubsystemDispatch):
                continue
            if d.visibility.redact_from_narrator_canonical:
                target = d.params.get("target") if isinstance(d.params, dict) else None
                if isinstance(target, str):
                    redacted_entities.append(target)

    leaks: list[str] = []
    fragments: list[str] = []
    prose_lower = prose.lower()
    for entity_id in redacted_entities:
        for token in entity_tokens_by_id.get(entity_id, []):
            if token.lower() in prose_lower:
                leaks.append(entity_id)
                # Capture a short surrounding window for GM-panel display.
                idx = prose_lower.find(token.lower())
                fragments.append(prose[max(0, idx - 20):idx + len(token) + 20])
                break

    result = LeakAuditResult(
        turn_id=package.turn_id,
        leaks_detected=len(leaks),
        redact_tag_count=len(redacted_entities),
        leaked_entities=leaks,
        leaked_fragments=fragments,
    )

    with _tracer.start_as_current_span("narrator.canonical_leak_audit") as span:
        span.set_attribute("turn_id", result.turn_id)
        span.set_attribute("leaks_detected", result.leaks_detected)
        span.set_attribute("redact_tag_count", result.redact_tag_count)
        span.set_attribute("leaked_entities", result.leaked_entities)
        span.set_attribute("leaked_fragments", result.leaked_fragments)

    return result
```

- [ ] **Step 4: Run — expect PASS**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_leak_audit.py -v`
Expected: 3 PASS.

- [ ] **Step 5: Call audit from narrator after canonical prose lands**

In `sidequest-server/sidequest/agents/narrator.py`, after canonical prose is produced and before/alongside the NARRATION event log append:

```python
from sidequest.telemetry.leak_audit import audit_canonical_prose

tokens = self._entity_tokens_for_registry()  # helper: pull from NPC registry
audit_canonical_prose(
    prose=canonical_text,
    package=pkg,  # the ORIGINAL package, not the redacted one
    entity_tokens_by_id=tokens,
)
```

The helper `_entity_tokens_for_registry` pulls display-name, aliases, and role-noun tokens from whatever NPC registry the session already maintains — do not invent new state.

- [ ] **Step 6: Create smoke scenario**

Create `scenarios/asymmetric_smoke.yaml`:

```yaml
name: asymmetric_smoke
description: >
  P1 kills an NPC in shadows while P2-P4 sit at the inn. Verifies end-to-end
  asymmetric delivery: P2-P4 see no kill, leak audit fires zero, secret note
  reaches P1 only.
pack: mutant_wasteland
world: blighted_crossing
players:
  - name: Alice
    character: wanderer
  - name: Bob
    character: mechanic
  - name: Cass
    character: medic
  - name: Dan
    character: scout
turns:
  - actor: Alice
    action: "I sneak into the shack and slit Rickard's throat. No one sees me."
    assertions:
      - leak_audit_zero: true
      - player_receives:
          Alice: ["SECRET_NOTE", "NARRATION"]
          Bob: ["NARRATION"]
          Cass: ["NARRATION"]
          Dan: ["NARRATION"]
      - redacted_tokens_absent_in_canonical: ["Rickard", "the guard"]
```

- [ ] **Step 7: Add CI assertion**

If the repo has a `justfile` recipe that runs scenarios, extend it to fail when any turn of `asymmetric_smoke.yaml` reports `leaks_detected > 0`. Otherwise add a pytest integration test in Task 9 that drives the scenario and asserts the same.

- [ ] **Step 8: Commit**

```bash
git add sidequest-server/sidequest/telemetry/leak_audit.py \
        sidequest-server/sidequest/agents/narrator.py \
        sidequest-server/tests/telemetry/test_leak_audit.py \
        scenarios/asymmetric_smoke.yaml
git commit -m "feat(telemetry): canonical-leak audit with expected-zero OTEL span

Safety net for structural hiding. Scans canonical prose for tokens
of entities flagged redact_from_narrator_canonical. Entity tokens
come from the NPC registry — no regex on arbitrary strings."
```

---

## Task 8: Deterministic fidelity-only PerceptionRewriter (G6)

**Files:**
- Create: `sidequest-server/sidequest/agents/perception_rewriter.py`
- Modify: `sidequest-server/sidequest/server/session_handler.py` (invoke after filter, before WS send)
- Test: `sidequest-server/tests/agents/test_perception_rewriter.py`

**Note:** This task exists because fidelity transforms at the `visibility_tag` rule (Task 3, `_apply_fidelity`) handle span stripping on the canonical payload — but per-recipient status-effect re-voicing (blinded / deafened / invisible) is a layer on top. Task 3's transform is payload-structured; this task is prose-structured and runs on the already-filtered decision.

For MP-ship, the rewriter is **deterministic sentence-level filtering** driven by the same fidelity metadata — no LLM call.

- [ ] **Step 1: Write failing test**

Create `sidequest-server/tests/agents/test_perception_rewriter.py`:

```python
import json

from sidequest.agents.perception_rewriter import rewrite_for_recipient


def test_blind_recipient_gets_no_visual_spans():
    payload = {
        "text": "A guard slumps into shadow.",
        "spans": [
            {"id": "s1", "kind": "visual_only", "text": "slumps into shadow"},
            {"id": "s2", "kind": "audio_only", "text": "A soft thud"},
        ],
        "_visibility": {"visible_to": "all", "fidelity": {"p1": "audio_only"}},
    }
    out = rewrite_for_recipient(
        canonical_payload=payload,
        viewer_player_id="p1",
        status_effects={"p1": ["blinded"]},
    )
    out_data = json.loads(out) if isinstance(out, str) else out
    kinds = [s["kind"] for s in out_data["spans"]]
    assert "visual_only" not in kinds
    assert "audio_only" in kinds


def test_full_fidelity_no_change():
    payload = {
        "text": "A quiet evening.",
        "spans": [{"id": "s1", "kind": "full", "text": "A quiet evening."}],
        "_visibility": {"visible_to": "all", "fidelity": {}},
    }
    out = rewrite_for_recipient(
        canonical_payload=payload,
        viewer_player_id="p1",
        status_effects={"p1": []},
    )
    out_data = json.loads(out) if isinstance(out, str) else out
    assert out_data == payload
```

- [ ] **Step 2: Run — expect FAIL**

Expected: ImportError.

- [ ] **Step 3: Implement**

Create `sidequest-server/sidequest/agents/perception_rewriter.py`:

```python
"""PerceptionRewriter — deterministic fidelity+status-effect prose filter.

MP-ship version. LLM re-voicing is deferred to post-MP (G10). This module
runs AFTER the projection filter produces a per-recipient FilterDecision.
Input: the canonical payload (already visibility-filtered). Output: a
payload with spans further stripped/annotated per the recipient's status
effects.

Composition order:
    canonical  ->  VisibilityTagFilter._apply_fidelity  ->  [FilterDecision]
                                                              |
                                                   PerceptionRewriter (this)
                                                              |
                                                         WS frame

Task-3's _apply_fidelity already handles fidelity bucket stripping. This
module layers status-effect overrides: a blinded recipient with
fidelity=full still has visual_only spans stripped because the status
effect trumps.
"""
from __future__ import annotations

import json

from opentelemetry import trace


_tracer = trace.get_tracer("sidequest.perception_rewriter")


_STATUS_FIDELITY_OVERRIDE = {
    "blinded": "audio_only",
    "deafened": "visual_only",
    "invisible": None,  # self-invisibility affects OTHER viewers, not self
}


def _fidelity_for(
    base_fidelity: str,
    status_effects: list[str],
) -> str:
    """Status effects override fidelity if more restrictive."""
    for fx in status_effects:
        override = _STATUS_FIDELITY_OVERRIDE.get(fx)
        if override is not None:
            return override
    return base_fidelity


def _keep_span(span: dict, fidelity: str) -> bool:
    kind = span.get("kind", "full")
    if fidelity == "full":
        return True
    if fidelity == "audio_only":
        return kind != "visual_only"
    if fidelity == "visual_only":
        return kind != "audio_only"
    if fidelity == "audio_only_muffled":
        return kind != "visual_only"
    if fidelity == "periphery_only":
        return bool(span.get("periphery_tolerant"))
    if fidelity == "inferred_from_aftermath":
        return bool(span.get("aftermath"))
    return True


def rewrite_for_recipient(
    *,
    canonical_payload: dict,
    viewer_player_id: str,
    status_effects: dict[str, list[str]],
) -> dict:
    """Return a payload dict stripped by the viewer's effective fidelity."""
    viz = canonical_payload.get("_visibility", {}) or {}
    base = (viz.get("fidelity") or {}).get(viewer_player_id, "full")
    effective = _fidelity_for(base, status_effects.get(viewer_player_id, []))

    with _tracer.start_as_current_span("narrator.perception_rewrite") as span:
        span.set_attribute("viewer", viewer_player_id)
        span.set_attribute("base_fidelity", base)
        span.set_attribute("effective_fidelity", effective)
        span.set_attribute("status_effects", status_effects.get(viewer_player_id, []))

        spans = canonical_payload.get("spans")
        if not isinstance(spans, list) or effective == "full":
            return canonical_payload
        filtered = [s for s in spans if _keep_span(s, effective)]
        return {**canonical_payload, "spans": filtered}
```

- [ ] **Step 4: Run — expect PASS**

Run: `cd sidequest-server && uv run pytest tests/agents/test_perception_rewriter.py -v`
Expected: 2 PASS.

- [ ] **Step 5: Wire into session handler**

In `sidequest-server/sidequest/server/session_handler.py`, find the per-recipient frame dispatch loop. After `ComposedFilter.project()` returns `include=True`:

```python
from sidequest.agents.perception_rewriter import rewrite_for_recipient

decision = filter.project(envelope=env, view=view, player_id=player_id)
if decision.include:
    payload = json.loads(decision.payload_json)
    payload = rewrite_for_recipient(
        canonical_payload=payload,
        viewer_player_id=player_id,
        status_effects=session.status_effects_by_player(),  # existing-or-new accessor
    )
    send_frame(player_id, json.dumps(payload))
```

If `status_effects_by_player()` doesn't exist on the session, add it as a small accessor pulling from whatever character-status map the session already has (there is one for combat HP; piggyback).

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/agents/perception_rewriter.py \
        sidequest-server/sidequest/server/session_handler.py \
        sidequest-server/tests/agents/test_perception_rewriter.py
git commit -m "feat(perception): deterministic fidelity+status rewriter

Runs after ProjectionFilter, before WS send. Strips spans whose
kind is incompatible with recipient's effective fidelity (base
fidelity combined with status effects like blinded/deafened).
LLM re-voicing deferred to post-MP."
```

---

## Task 9: Per-player save projection (G8)

**Files:**
- Modify: `sidequest-server/sidequest/game/persistence.py` (or wherever `save.db` writes happen)
- Modify: `sidequest-server/sidequest/server/session_handler.py` (canonical-vs-peer split)
- Test: `sidequest-server/tests/game/test_per_player_save.py`

- [ ] **Step 1: Locate save-write entry points**

```bash
grep -rn "save.db\|EventLog.append\|write_event\|sqlite" sidequest-server/sidequest/ | grep -v __pycache__ | head -15
```

Identify: where canonical events are written to the narrator-host save, and where peer-side receive writes land.

- [ ] **Step 2: Write failing test**

Create `sidequest-server/tests/game/test_per_player_save.py`:

```python
"""Peer save receives only the filtered event stream.

Canonical save on the narrator-host holds the union; peer save holds the
filtered subset per MP spec 2026-04-22. These tests assert the session
handler's write-split is correct — not the host-side SQLite writer (which
is unchanged) and not the peer-side client (which lives in sidequest-ui).
"""
import json

import pytest

# Import the per-turn write-split under test. Exact name depends on where
# you place the helper — put it wherever feels natural and import from there.
from sidequest.server.session_handler import apply_turn_writes_for_test


def test_canonical_save_gets_unfiltered_event(fake_event_log, fake_filter_allow_all):
    apply_turn_writes_for_test(
        event_log=fake_event_log, filter=fake_filter_allow_all,
        envelope={"kind": "NARRATION", "payload": {"text": "X"}},
        connected_players=["p1", "p2"],
    )
    assert len(fake_event_log.canonical) == 1


def test_peer_frames_sent_only_when_filter_includes(fake_event_log, fake_filter_p1_only):
    sent = apply_turn_writes_for_test(
        event_log=fake_event_log, filter=fake_filter_p1_only,
        envelope={"kind": "NARRATION",
                  "payload": {"text": "X", "_visibility": {"visible_to": ["p1"]}}},
        connected_players=["p1", "p2"],
    )
    assert [f.player_id for f in sent] == ["p1"]
```

Create minimal fakes in the test file:

```python
@pytest.fixture
def fake_event_log():
    class _Log:
        def __init__(self): self.canonical = []
        def append(self, env): self.canonical.append(env)
    return _Log()


@pytest.fixture
def fake_filter_allow_all():
    class _F:
        def project(self, *, envelope, view, player_id):
            from sidequest.game.projection_filter import FilterDecision
            return FilterDecision(include=True, payload_json=json.dumps(envelope["payload"]))
    return _F()


@pytest.fixture
def fake_filter_p1_only():
    class _F:
        def project(self, *, envelope, view, player_id):
            from sidequest.game.projection_filter import FilterDecision
            if player_id == "p1":
                return FilterDecision(include=True, payload_json=json.dumps(envelope["payload"]))
            return FilterDecision(include=False, payload_json="")
    return _F()
```

- [ ] **Step 3: Run — expect FAIL**

Expected: ImportError.

- [ ] **Step 4: Implement `apply_turn_writes_for_test` helper**

Add to `sidequest-server/sidequest/server/session_handler.py` (or expose via a sibling module imported by both the test and the turn driver):

```python
from dataclasses import dataclass


@dataclass
class SentFrame:
    player_id: str
    payload_json: str


def apply_turn_writes_for_test(
    *,
    event_log,
    filter,
    envelope: dict,  # {kind, payload}
    connected_players: list[str],
    view=None,  # passed through to filter; tests use a no-op view
) -> list[SentFrame]:
    """Canonical save gets the raw envelope; peer frames get the filtered subset.

    Real turn driver in this file should also call this shape. Extract once;
    keep the production path using the same helper.
    """
    from sidequest.game.projection.envelope import MessageEnvelope
    import json as _json

    canonical_env = MessageEnvelope(
        kind=envelope["kind"],
        payload_json=_json.dumps(envelope["payload"]),
        origin_seq=getattr(event_log, "next_seq", 0),
    )
    event_log.append(canonical_env)

    sent: list[SentFrame] = []
    for pid in connected_players:
        decision = filter.project(envelope=canonical_env, view=view, player_id=pid)
        if decision.include:
            sent.append(SentFrame(player_id=pid, payload_json=decision.payload_json))
    return sent
```

Refactor the production turn driver in `session_handler.py` (wherever it currently emits NARRATION to peers) to call `apply_turn_writes_for_test` or its extracted production-named sibling — do **not** duplicate the logic. Extract once.

- [ ] **Step 5: Run tests**

Run: `cd sidequest-server && uv run pytest tests/game/test_per_player_save.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/server/session_handler.py \
        sidequest-server/tests/game/test_per_player_save.py
git commit -m "feat(session): split canonical save write from per-peer filtered frames

Canonical save holds union; peer receives only frames FilterDecision
marks include=True. Extracts the write-split into a single helper
used by both production path and test."
```

---

## Task 10: End-to-end test — the spec §10 test contract

**Files:**
- Test: `sidequest-server/tests/integration/test_group_g_e2e.py`

- [ ] **Step 1: Write the full test-contract suite**

Create `sidequest-server/tests/integration/test_group_g_e2e.py`:

```python
"""End-to-end test contract from decomposer-spec §10 G.

Each test names its spec assertion letter in the docstring.
"""
import json

import pytest

from sidequest.agents.perception_rewriter import rewrite_for_recipient
from sidequest.agents.prompt_redaction import redact_dispatch_package
from sidequest.game.projection.composed import ComposedFilter
from sidequest.game.projection.envelope import MessageEnvelope
from sidequest.game.projection.rules import load_rules_from_yaml_str
from sidequest.game.projection.view import SessionGameStateView
from sidequest.protocol.dispatch import (
    DispatchPackage, PlayerDispatch, SubsystemDispatch, VisibilityTag,
)
from sidequest.telemetry.leak_audit import audit_canonical_prose


RULES = load_rules_from_yaml_str("""
rules:
  - kind: NARRATION
    visibility_tag: {}
  - kind: SECRET_NOTE
    visibility_tag: {}
""")


def _view(pids: list[str], zones: dict[str, str] | None = None) -> SessionGameStateView:
    return SessionGameStateView(
        gm_player_id=None,
        player_id_to_character={p: f"char_{p}" for p in pids},
        character_zones={f"char_{p}": z for p, z in (zones or {}).items()},
    )


# (a) Assassination redaction
def test_a_assassination_hidden_from_non_actor_players():
    pkg = DispatchPackage(
        turn_id="t1",
        per_player=[PlayerDispatch(
            player_id="player:Alice", raw_action="kill guard silently",
            dispatch=[SubsystemDispatch(
                subsystem="lethal_strike", params={"target": "guard_A"},
                idempotency_key="k1",
                visibility=VisibilityTag(
                    visible_to=["player:Alice"], perception_fidelity={},
                    secrets_for=["player:Alice"],
                    redact_from_narrator_canonical=True,
                ),
            )],
        )],
        confidence_global=1.0,
    )
    redacted_pkg, removed = redact_dispatch_package(pkg)
    assert len(removed) == 1
    # Narrator would now compose canonical prose *without* the kill.
    canonical = "Alice pauses at the door; the inn's evening goes on."
    # VisibilityTagFilter sees only non-redacted tags on the canonical NARRATION,
    # so canonical NARRATION goes to everybody (visible_to: all).
    filter = ComposedFilter(rules=RULES)
    narration_env = MessageEnvelope(
        kind="NARRATION",
        payload_json=json.dumps({
            "text": canonical,
            "_visibility": {"visible_to": "all", "fidelity": {}},
        }),
        origin_seq=1,
    )
    view = _view(["player:Alice", "player:Bob", "player:Cass"])
    for pid in ["player:Alice", "player:Bob", "player:Cass"]:
        assert filter.project(envelope=narration_env, view=view, player_id=pid).include
    # The SECRET_NOTE built from `removed` goes only to Alice.
    secret_env = MessageEnvelope(
        kind="SECRET_NOTE",
        payload_json=json.dumps({
            "turn_id": "t1",
            "idempotency_key": "k1",
            "subsystem": "lethal_strike",
            "params": {"target": "guard_A"},
            "_visibility": {"visible_to": ["player:Alice"], "fidelity": {}},
        }),
        origin_seq=2,
    )
    assert filter.project(envelope=secret_env, view=view, player_id="player:Alice").include
    assert not filter.project(envelope=secret_env, view=view, player_id="player:Bob").include
    assert not filter.project(envelope=secret_env, view=view, player_id="player:Cass").include


# (b) Blind fidelity
def test_b_blinded_recipient_receives_no_visual_spans():
    payload = {
        "text": "A dim thing moves.",
        "spans": [
            {"id": "s1", "kind": "visual_only", "text": "a glint of steel"},
            {"id": "s2", "kind": "audio_only", "text": "boots on gravel"},
        ],
        "_visibility": {"visible_to": "all", "fidelity": {}},
    }
    out = rewrite_for_recipient(
        canonical_payload=payload, viewer_player_id="p1",
        status_effects={"p1": ["blinded"]},
    )
    kinds = [s["kind"] for s in out["spans"]]
    assert "visual_only" not in kinds


# (d) Structural hiding (prompt-builder unit test)
def test_d_structural_hiding_strips_redacted_entries():
    pkg = DispatchPackage(
        turn_id="t1",
        per_player=[PlayerDispatch(
            player_id="player:Alice", raw_action="sneak",
            dispatch=[SubsystemDispatch(
                subsystem="lethal_strike", params={"target": "guard_A"},
                idempotency_key="k1",
                visibility=VisibilityTag(
                    visible_to=["player:Alice"], perception_fidelity={},
                    secrets_for=["player:Alice"],
                    redact_from_narrator_canonical=True,
                ),
            )],
        )],
        confidence_global=1.0,
    )
    redacted, _ = redact_dispatch_package(pkg)
    assert redacted.per_player[0].dispatch == []


# (e) Canonical-leak audit — zero leaks on clean prose
def test_e_leak_audit_zero_on_clean_prose():
    pkg = DispatchPackage(
        turn_id="t1",
        per_player=[PlayerDispatch(
            player_id="player:Alice", raw_action="sneak",
            dispatch=[SubsystemDispatch(
                subsystem="lethal_strike", params={"target": "guard_A"},
                idempotency_key="k1",
                visibility=VisibilityTag(
                    visible_to=["player:Alice"], perception_fidelity={},
                    secrets_for=["player:Alice"],
                    redact_from_narrator_canonical=True,
                ),
            )],
        )],
        confidence_global=1.0,
    )
    result = audit_canonical_prose(
        prose="Alice pauses at the door; the inn's evening goes on.",
        package=pkg,
        entity_tokens_by_id={"guard_A": ["Rickard", "the guard"]},
    )
    assert result.leaks_detected == 0


# (g) VisibilityTagFilter wiring — integration smoke
def test_g_visibility_tag_filter_excludes_non_recipient():
    filter = ComposedFilter(rules=RULES, pack_slug="test_pack")
    view = _view(["player:Alice", "player:Bob"])
    env = MessageEnvelope(
        kind="NARRATION",
        payload_json=json.dumps({
            "text": "secret note text",
            "_visibility": {"visible_to": ["player:Alice"], "fidelity": {}},
        }),
        origin_seq=1,
    )
    d_alice = filter.project(envelope=env, view=view, player_id="player:Alice")
    d_bob = filter.project(envelope=env, view=view, player_id="player:Bob")
    assert d_alice.include is True
    assert d_bob.include is False
```

- [ ] **Step 2: Run — expect PASS**

Run: `cd sidequest-server && uv run pytest tests/integration/test_group_g_e2e.py -v`
Expected: 5 PASS.

If any FAIL, do not advance. Each failure maps to a specific earlier task — fix the task, not the test (the test encodes the spec).

- [ ] **Step 3: Commit**

```bash
git add sidequest-server/tests/integration/test_group_g_e2e.py
git commit -m "test(group-g): end-to-end coverage for decomposer-spec §10 G assertions

Covers: (a) assassination redaction, (b) blind fidelity, (d) structural
hiding, (e) leak audit zero-state, (g) filter wiring.
(c) guest-NPC inversion and (f) reconnect parity are deferred post-MP."
```

---

## Task 11: Final gate

- [ ] **Step 1: Run full suite**

Run: `just check-all`
Expected: all PASS.

- [ ] **Step 2: Compare test count to baseline**

Run: `cd sidequest-server && uv run pytest --collect-only -q 2>&1 | tail -3`
Expect: strictly greater than the Task 0 baseline count (you added tests in every task).

- [ ] **Step 3: Manual smoke — full stack up**

```bash
just up
# In another terminal:
just playtest-scenario asymmetric_smoke
```

Expected: scenario completes. Leak-audit fires zero leaks per turn. Alice's client receives a SECRET_NOTE; Bob/Cass/Dan do not.

- [ ] **Step 4: Stop services**

```bash
just down
```

- [ ] **Step 5: Push and open PR**

```bash
git push -u origin feat/local-dm-group-g
gh pr create --base main --title "feat(local-dm): Group G — asymmetric-info wiring (MP-ship)" --body "$(cat <<'EOF'
## Summary

Wires the Local DM decomposer's per-event VisibilityTag output through the projection pipeline. Closes the MP-release blocker from decomposer-spec §10 G.

Reference design: docs/superpowers/specs/2026-04-23-local-dm-group-g-asymmetric-info-wiring.md

## What's in this PR

- Real zone + visibility tracking on SessionGameStateView (was None/False by default)
- visibility_baseline.yaml schema + 6 shipping-pack defaults
- visibility_tag rule kind in GenreRuleStage — first rule in the chain, short-circuits on non-recipient
- Decomposer applies baseline-driven defaults to VisibilityTag emission
- Structural hiding precondition in narrator prompt builder
- SECRET_NOTE message kind + routing for redact_from_narrator_canonical dispatches
- Canonical-leak audit OTEL span (expected-zero semantics)
- Deterministic fidelity-only PerceptionRewriter (LLM re-voicing deferred post-MP as G10)
- Per-player save projection write-split (canonical on host, filtered on peer)
- End-to-end tests for spec §10 G assertions (a, b, d, e, g); (c) and (f) deferred post-MP

## Test plan

- [x] just check-all
- [x] just playtest-scenario asymmetric_smoke — leak_audit zero every turn
- [x] Alice receives SECRET_NOTE; Bob/Cass/Dan do not
EOF
)"
```

- [ ] **Step 6: Merge when green**

Squash-merge to `main` once CI is green.

---

## Self-Review Checklist

After writing this plan, the author checked:

- **Spec coverage.** Task map:
  - §2 baseline schema → Task 2
  - §3 VisibilityTagFilter → Task 3
  - §3.1 `_visibility` carry → Task 4
  - §4 structural hiding → Task 5
  - §4.2 SECRET_NOTE routing → Task 6
  - §5 leak audit → Task 7
  - §6 PerceptionRewriter → Task 8
  - §7 NPC inversion → **not in scope (post-MP, G9)**
  - §8 per-player save → Task 9
  - §9 test contract (a/b/d/e/g) → Task 10; (c) and (f) → **not in scope (post-MP)**
- **Placeholder scan.** No TODO / TBD / "handle edge cases" / "similar to Task N" instances. Every step has either an exact command or an exact code block.
- **Type consistency.** `VisibilityTagSpec`, `VisibilityTagRule`, `rewrite_for_recipient`, `audit_canonical_prose`, `build_secret_note_events`, `apply_visibility_baseline` appear once each, consistently named. `_apply_fidelity` in Task 3 and `rewrite_for_recipient` in Task 8 are distinct by design (payload-span filtering vs. status-effect overlay) — documented in Task 8's note.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-23-local-dm-group-g-mp-ship.md`.**

Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints.

Which approach?
