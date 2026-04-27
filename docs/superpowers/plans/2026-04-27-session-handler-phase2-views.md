# Session Handler Phase 2 — View Projection Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract seven view-projection methods from `WebSocketSessionHandler` (post-Phase-1 ~5071-line `session_handler.py`) into a new sibling module `sidequest-server/sidequest/server/views.py`, with byte-identical behavior, mandatory wiring tests, and preserved OTEL span surface.

**Architecture:** Each extracted method becomes a free function in `views.py` that takes `handler: WebSocketSessionHandler` as its first argument. The original method on `WebSocketSessionHandler` becomes a thin delegate calling the new free function. No new abstractions, no narrow context dataclasses, no class hierarchies. Behavior is preserved verbatim. Same pattern that shipped in Phase 1.

**Tech Stack:** Python 3.12, FastAPI/Uvicorn, pytest, `uv` package manager. Tests run via `just server-test` from orchestrator root or `uv run pytest -v` from `sidequest-server/`.

**Spec:** `docs/superpowers/specs/2026-04-27-session-handler-decomposition-design.md` (Phase 2 — View Projection → `server/views.py`).

**Branch baseline:** `sidequest-server/develop` at `4ab3e26` (Phase 1 merge commit). Feature branch: `refactor/session-handler-phase2-views`.

**Out of scope for this plan:** Phases 3–8 (lore/embed, media, chargen, small handlers, connect, narration turn). Each gets its own plan after this one merges. Removal of the seven thin delegate methods is deferred to a post-epic cleanup story per the spec.

---

## Standing Rules — applied to every implementer subagent prompt

These are non-negotiable. Subagent prompts MUST repeat them verbatim because subagents do not inherit user-memory rules:

- **NEVER use `git stash`.** Standing user rule. If WIP needs to land somewhere, commit it on the feature branch. A Phase 1 implementer violated this; the rule must be re-stated for every Phase 2 task.
- **DO NOT MODIFY the skeleton import-existence test** (`test_views_module_exposes_required_functions`) until the LAST extraction task lands. It is **intentionally RED** as the epic-level RED→GREEN gate. Subagents tried to "fix" the equivalent test in Phase 1 and were wrong.
- **Pre-existing failures (3 tests) on `4ab3e26` are NOT yours to fix.** They were red before Phase 1 and will remain red after Phase 2. Specifically:
  - `tests/server/dispatch/test_sealed_letter_dispatch_integration.py::test_legacy_beat_selection_path_still_works`
  - `tests/server/test_confrontation_dispatch_wiring.py::test_confrontation_message_active_false_when_resolved`
  - `tests/server/test_confrontation_dispatch_wiring.py::test_confrontation_message_refreshed_on_live_to_live`
  If Phase 2 breaks any of the OTHER ~2623 passing tests, that is a regression you must fix.
- **Pre-existing lint warnings at `session_handler.py:717` (SIM102) and `session_handler.py:1075` (SIM105) are out of scope.** Do not "improve" them — pure decomposition only.
- **Pin working directory:** `/Users/slabgorb/Projects/oq-2/sidequest-server`.
- **Pin branch:** `refactor/session-handler-phase2-views`.
- **Use the orchestrator's `just` recipes when verifying** (`just server-test`, `just server-lint`, `just server-check`) — but per-test invocations via `uv run pytest tests/...` are fine for tight loops.
- **Behavior preservation is byte-identical.** The only acceptable diff in moved code is:
  - `self.X` → `handler.X` (forced by extraction)
  - `self._other_method(...)` → in-module function call when `other` was also extracted (e.g., `self._is_hidden_status_list(...)` → `is_hidden_status_list(...)`)
  - Removing the underscore prefix on the renamed function
  Anything else gets logged in the PR body as an explicit deviation.

## Pre-flight verification — already complete

These were checked while authoring this plan; record here so the implementer doesn't re-do them:

- **Monkeypatch landmines:** `grep -rn "monkeypatch.*session_handler" sidequest-server/tests | grep -E "(_build_game_state_view|status_effects_by_player|_party_member|_resolve_self_character|_backfill_last_narration_block|_is_hidden_status_list|_build_session_start_party_status)"` returned **NO MATCHES**. There are no `monkeypatch.setattr` patches against view-cluster symbols today. **Implication:** all imports in `views.py` may be lazy (function-body) — no need to eagerly import anything at module level for monkeypatch reachability.
- **Direct attribute reassignment:** `tests/server/test_perception_rewriter_wiring.py:262` and `:314` overwrite `handler.status_effects_by_player` via plain attribute assignment (`handler.status_effects_by_player = lambda: ...`). This works against the **delegate method**, not the free function — the delegate must therefore stay on the handler. ✅ Our extraction pattern preserves the delegate.
- **Direct class-attribute lookup:** `tests/server/test_session_handler_view.py:224` does `check = WebSocketSessionHandler._is_hidden_status_list` then calls `check([Status(...)])`. **Implication:** the `_is_hidden_status_list` delegate must remain a `@classmethod` (so the bound-method form `check(statuses)` continues to work).
- **Cross-module references to constants:** `sidequest/game/projection/view.py:32` mentions `WebSocketSessionHandler._HIDDEN_STATUS_TOKENS` in a docstring only (no code reference). Safe to move the constant; the docstring will become slightly stale but is out of scope to update (pure decomposition).
- **External callers of the seven methods (non-test, non-`session_handler.py`):** `emitters.py` calls `handler._build_game_state_view()` and `handler.status_effects_by_player()`. Both go through the delegates and survive the extraction unchanged.

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `sidequest-server/sidequest/server/views.py` | **Create** | Houses seven free functions: `is_hidden_status_list`, `build_game_state_view`, `status_effects_by_player`, `backfill_last_narration_block`, `party_member_from_character`, `resolve_self_character`, `build_session_start_party_status`. Also houses the `_HIDDEN_STATUS_TOKENS` module constant moved from the class. |
| `sidequest-server/sidequest/server/session_handler.py` | **Modify** | The seven method bodies are replaced with thin delegates calling the free functions. The class-level `_HIDDEN_STATUS_TOKENS` constant is removed (it moves to `views.py`). All other content untouched. |
| `sidequest-server/tests/server/test_views.py` | **Create** | Wiring tests for each of the seven delegates plus a behavioral test for the simplest function (`is_hidden_status_list`) and the existing integration tests in `tests/server/test_session_handler_view.py`, `tests/server/test_multiplayer_party_status.py`, and `tests/integration/test_visibility_wiring.py` continue to pass without modification. |

The seven functions are extracted in dependency order:

1. `is_hidden_status_list` first (no callers within this cluster after extraction)
2. `build_game_state_view` (calls `is_hidden_status_list`)
3. `status_effects_by_player` (independent)
4. `backfill_last_narration_block` (independent — uses module-level `_build_message_for_kind`)
5. `party_member_from_character` (no in-cluster callers)
6. `resolve_self_character` (independent)
7. `build_session_start_party_status` (calls `party_member_from_character`)

This order means each task's extracted function has its in-cluster dependencies already extracted.

---

## Task 1: Create empty `views.py` and confirm the import-existence test fails

**Files:**
- Create: `sidequest-server/sidequest/server/views.py`
- Create: `sidequest-server/tests/server/test_views.py`

- [ ] **Step 1.1: Create the empty module file**

Create `sidequest-server/sidequest/server/views.py` with this exact content:

```python
"""View projection helpers extracted from WebSocketSessionHandler.

Phase 2 of the session_handler.py decomposition (see
docs/superpowers/specs/2026-04-27-session-handler-decomposition-design.md).

Each function takes ``handler: WebSocketSessionHandler`` as its first
argument (or operates on read-only inputs in the case of
``is_hidden_status_list``). No new abstractions introduced — this is pure
extraction with byte-identical behavior to the original methods on
WebSocketSessionHandler.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sidequest.game.character import Character
    from sidequest.game.projection.view import SessionGameStateView
    from sidequest.game.status import Status
    from sidequest.protocol.messages import PartyStatusMessage
    from sidequest.server.session_handler import WebSocketSessionHandler, _SessionData
```

- [ ] **Step 1.2: Create the test file with one failing import-existence test**

Create `sidequest-server/tests/server/test_views.py` with this exact content:

```python
"""Unit + wiring tests for sidequest/server/views.py.

Phase 2 of session_handler decomposition. These tests verify:
1. Each extracted function exists with the expected signature.
2. The thin delegate methods on WebSocketSessionHandler still call
   into views.py (wiring guard per CLAUDE.md).
3. Behavior is preserved (functional parity with the pre-extraction
   methods) — supplemented by the existing integration tests in
   tests/server/test_session_handler_view.py and
   tests/server/test_multiplayer_party_status.py which continue to
   exercise the same code paths through the delegates.
"""

from __future__ import annotations


def test_views_module_exposes_required_functions() -> None:
    """Wiring guard — the seven required functions must be importable
    from sidequest.server.views by their canonical names.

    DO NOT MODIFY this test until the last extraction (Task 8) lands.
    It is INTENTIONALLY RED until then — the epic-level RED→GREEN gate
    that proves all seven moves completed.
    """
    from sidequest.server import views

    assert hasattr(views, "is_hidden_status_list")
    assert hasattr(views, "build_game_state_view")
    assert hasattr(views, "status_effects_by_player")
    assert hasattr(views, "backfill_last_narration_block")
    assert hasattr(views, "party_member_from_character")
    assert hasattr(views, "resolve_self_character")
    assert hasattr(views, "build_session_start_party_status")
```

- [ ] **Step 1.3: Run the test and confirm it fails**

Run from `sidequest-server/`:
```bash
uv run pytest tests/server/test_views.py::test_views_module_exposes_required_functions -v
```

Expected: FAIL with `AssertionError` — the seven functions do not exist yet. This is the intentional epic-level RED.

- [ ] **Step 1.4: Commit the skeleton**

```bash
git add sidequest-server/sidequest/server/views.py sidequest-server/tests/server/test_views.py
git commit -m "refactor(server): create views.py skeleton (Phase 2 of session_handler decomposition)"
```

---

## Task 2: Extract `_is_hidden_status_list` → `views.is_hidden_status_list` (and move `_HIDDEN_STATUS_TOKENS`)

**Files:**
- Modify: `sidequest-server/sidequest/server/views.py`
- Modify: `sidequest-server/sidequest/server/session_handler.py:651-669`
- Modify: `sidequest-server/tests/server/test_views.py`

> **Note on the constant move:** `_HIDDEN_STATUS_TOKENS` (currently a class-level frozenset on `WebSocketSessionHandler` at file:651-665) moves to `views.py` as a module-level constant. The classmethod delegate references it through the new module name (`views._HIDDEN_STATUS_TOKENS`). The only in-tree reference outside the class is a docstring mention in `sidequest/game/projection/view.py:32` — out of scope to update.

> **Note on classmethod preservation:** the delegate stays as a `@classmethod` because `tests/server/test_session_handler_view.py:224` does `check = WebSocketSessionHandler._is_hidden_status_list` then calls `check(statuses)`. Bound-class-method behavior must survive.

- [ ] **Step 2.1: Add wiring test**

Append to `sidequest-server/tests/server/test_views.py`:

```python
def test_is_hidden_status_list_delegate_calls_module_function(monkeypatch) -> None:
    """Wiring guard — WebSocketSessionHandler._is_hidden_status_list
    must delegate to views.is_hidden_status_list."""
    from sidequest.game.status import Status
    from sidequest.server import views
    from sidequest.server.session_handler import WebSocketSessionHandler

    captured: list[list[Status]] = []
    sentinel = object()

    def _spy(statuses):
        captured.append(statuses)
        return sentinel

    monkeypatch.setattr(views, "is_hidden_status_list", _spy)

    statuses = [Status(text="hidden")]
    result = WebSocketSessionHandler._is_hidden_status_list(statuses)

    assert result is sentinel
    assert captured == [statuses]
```

- [ ] **Step 2.2: Run the wiring test — confirm it fails**

```bash
uv run pytest tests/server/test_views.py::test_is_hidden_status_list_delegate_calls_module_function -v
```

Expected: FAIL — `views.is_hidden_status_list` does not exist yet, or the delegate still owns the implementation.

- [ ] **Step 2.3: Add the function and constant to `views.py`**

Append to `sidequest-server/sidequest/server/views.py` (below the `if TYPE_CHECKING` block):

```python
_HIDDEN_STATUS_TOKENS: frozenset[str] = frozenset(
    {
        "hidden",
        "invisible",
        "stealth",
        "concealed",
    }
)


def is_hidden_status_list(statuses: list[Status]) -> bool:
    """Return True iff any status's lowercased text matches a hidden-marker
    token (whole-token membership, not substring)."""
    return any(s.text.lower() in _HIDDEN_STATUS_TOKENS for s in statuses)
```

- [ ] **Step 2.4: Replace the classmethod body and remove the class constant**

In `sidequest-server/sidequest/server/session_handler.py`, find this block (currently at file:651-669):

```python
    _HIDDEN_STATUS_TOKENS: frozenset[str] = frozenset(
        {
            "hidden",
            "invisible",
            "stealth",
            "concealed",
        }
    )

    @classmethod
    def _is_hidden_status_list(cls, statuses: list[Status]) -> bool:
        return any(s.text.lower() in cls._HIDDEN_STATUS_TOKENS for s in statuses)
```

Replace it with:

```python
    @classmethod
    def _is_hidden_status_list(cls, statuses: list[Status]) -> bool:
        """Whole-token hidden-status check. Delegates to ``views.is_hidden_status_list``.

        Phase 2 of session_handler decomposition (see
        docs/superpowers/specs/2026-04-27-session-handler-decomposition-design.md).
        """
        from sidequest.server import views

        return views.is_hidden_status_list(statuses)
```

The class-level `_HIDDEN_STATUS_TOKENS` constant is gone. Its sole prior consumer (the classmethod body) now reaches the constant through `views._HIDDEN_STATUS_TOKENS`.

- [ ] **Step 2.5: Run the wiring test — confirm it passes**

```bash
uv run pytest tests/server/test_views.py::test_is_hidden_status_list_delegate_calls_module_function -v
```

Expected: PASS.

- [ ] **Step 2.6: Add a behavioral unit test for the function itself**

Append to `sidequest-server/tests/server/test_views.py`:

```python
def test_is_hidden_status_list_matches_hidden_tokens() -> None:
    """Behavioral test — each of the four hidden tokens triggers a True
    result; an unrelated token returns False; an empty list returns False."""
    from sidequest.game.status import Status
    from sidequest.server import views

    assert views.is_hidden_status_list([]) is False
    assert views.is_hidden_status_list([Status(text="poisoned")]) is False
    for token in ("hidden", "invisible", "stealth", "concealed"):
        assert views.is_hidden_status_list([Status(text=token)]) is True
    # Case-insensitive whole-token (the lowercase comparison is the
    # contract; substring matches are explicitly out of scope per
    # tests/server/test_session_handler_view.py:216).
    assert views.is_hidden_status_list([Status(text="HIDDEN")]) is True
    assert views.is_hidden_status_list([Status(text="hiddenly")]) is False
```

- [ ] **Step 2.7: Run the new behavioral test plus the existing class-method test**

```bash
uv run pytest tests/server/test_views.py tests/server/test_session_handler_view.py -v
```

Expected: all PASS. The existing `test_session_handler_view.py:224` test (`check = WebSocketSessionHandler._is_hidden_status_list`) must continue to pass — it exercises the classmethod delegate, which now routes through `views.is_hidden_status_list`.

- [ ] **Step 2.8: Run the full server test suite**

```bash
uv run pytest -v
```

Expected: all tests PASS except the three pre-existing failures listed in Standing Rules. If anything else fails, the extraction broke behavior — stop and investigate before committing.

- [ ] **Step 2.9: Commit**

```bash
git add sidequest-server/sidequest/server/views.py sidequest-server/sidequest/server/session_handler.py sidequest-server/tests/server/test_views.py
git commit -m "refactor(server): extract _is_hidden_status_list to views.is_hidden_status_list"
```

---

## Task 3: Extract `_build_game_state_view` → `views.build_game_state_view`

**Files:**
- Modify: `sidequest-server/sidequest/server/views.py`
- Modify: `sidequest-server/sidequest/server/session_handler.py:671-796`
- Modify: `sidequest-server/tests/server/test_views.py`

- [ ] **Step 3.1: Add wiring test**

Append to `sidequest-server/tests/server/test_views.py`:

```python
def test_build_game_state_view_delegate_calls_module_function(
    monkeypatch, session_handler_factory
) -> None:
    """Wiring guard — WebSocketSessionHandler._build_game_state_view must
    delegate to views.build_game_state_view."""
    from sidequest.server import views

    sd, handler = session_handler_factory()
    captured: list[object] = []
    sentinel = object()

    def _spy(h):
        captured.append(h)
        return sentinel

    monkeypatch.setattr(views, "build_game_state_view", _spy)

    result = handler._build_game_state_view()

    assert result is sentinel
    assert captured == [handler]
```

- [ ] **Step 3.2: Run the wiring test — confirm it fails**

```bash
uv run pytest tests/server/test_views.py::test_build_game_state_view_delegate_calls_module_function -v
```

Expected: FAIL — function does not exist or delegate still owns the implementation.

- [ ] **Step 3.3: Move the body into `views.py`**

Append to `sidequest-server/sidequest/server/views.py`:

```python
def build_game_state_view(handler: WebSocketSessionHandler) -> SessionGameStateView:
    """Read-only view of current session state for the projection filter.

    Zone + visibility state is populated from the live ``GameSnapshot``:
    all player-characters share the party-level ``snapshot.location``,
    and NPCs report their per-entity ``Npc.location``. Creatures whose
    ``statuses`` contain a stealth-like marker go into
    ``hidden_characters`` so ``visible_to()`` masks them even when
    co-located with the viewer. Per-item ownership is not yet tracked
    and stays at the conservative default.

    **GM identity wiring (C1, still partial):**

    - Solo sessions have no separate GM player by design; ``gm_player_id``
      is correctly ``None`` there. ``CoreInvariantStage`` never
      short-circuits on ``is_gm()`` for solo — which is the right
      behavior, because in solo play the single player is the only
      recipient and has no counterpart to be "GM" to.
    - Multiplayer sessions *should* name a GM player (e.g. the session
      creator or a designated seat) so that ``unless: is_gm()`` in
      ``projection.yaml`` can exempt them. That wiring lives downstream
      of MP-02 seating — ``SessionRoom`` does not yet carry a GM seat
      designation, so we still fall through to ``None`` for multiplayer
      with a logged warning. Genre packs that ship ``unless: is_gm()``
      rules today will mask the GM identically to a regular player
      (the safe direction: over-redact rather than leak).

    **Player-character mapping:** ``Character`` does not yet carry a
    ``player_id`` attribute, so the session's active player_id
    (``sd.player_id``) is mapped to the first entry in
    ``snapshot.characters`` — the single-player case this branch is
    authoritative for today. MP seat-assignment (sprint 2) will feed
    the multi-player case via ``SessionRoom``. When no character
    exists yet (pre-chargen) the mapping stays empty and predicates
    that depend on ``character_of()`` evaluate to ``False`` (the
    masked direction).
    """
    from sidequest.game.persistence import GameMode  # noqa: PLC0415 — break import cycle
    from sidequest.game.projection.view import SessionGameStateView
    from sidequest.server.session_handler import logger

    sd = handler._session_data
    if sd is None:
        return SessionGameStateView(gm_player_id=None, player_id_to_character={})

    # Solo: no human GM. None is correct; CoreInvariantStage's
    # gm-sees-all branch never fires for the single player.
    gm_player_id: str | None = None
    if sd.mode is not None and sd.mode != GameMode.SOLO:
        # Multiplayer: GM seat assignment not yet plumbed through
        # SessionRoom. Log one warning per build so GM-panel users
        # can see that ``unless: is_gm()`` rules are currently
        # over-masking the GM in multiplayer sessions.
        if not getattr(handler, "_gm_wiring_warned", False):
            logger.warning(
                "projection.gm_identity_unwired slug=%s mode=%s — "
                "multiplayer sessions do not yet carry a GM-seat "
                "designation; `unless: is_gm()` rules will mask the "
                "GM like any other player until MP-02 GM seating "
                "lands.",
                sd.game_slug,
                sd.mode,
            )
            handler._gm_wiring_warned = True

    snapshot = sd.snapshot

    # Player -> Character.name mapping. Solo / single-player sessions
    # today have exactly one character; that character belongs to the
    # session's active player_id. Without this mapping, the predicate
    # path (e.g. ``visible_to(target)``) receives
    # ``view.character_of(player_id) is None`` and short-circuits to
    # False before ever consulting zone data. Populated from the
    # existing session state — no new fields introduced.
    mapping: dict[str, str] = {}
    if snapshot.characters:
        mapping[sd.player_id] = snapshot.characters[0].core.name

    # Zone + hidden-character tracking from the live snapshot. Characters
    # share the party-level location today (no per-character zone split
    # in the engine yet); NPCs carry their own ``location``. Keys are
    # creature names — the same identity the rest of the projection
    # system uses when it refers to characters by ID. Single pass per
    # collection so character_zones and hidden_characters stay in sync.
    character_zones: dict[str, str] = {}
    hidden_characters: set[str] = set()
    party_zone = snapshot.location or None

    # One-shot OTEL breadcrumb: if we have player-characters but no
    # party zone, every co-located visible_to() collapses to False.
    # The direction is conservative-correct but invisible to the GM
    # panel — surface it once per session so rule authors can see why
    # their ``visible_to`` rules are masking everything.
    if (
        party_zone is None
        and snapshot.characters
        and not getattr(handler, "_party_zone_absent_warned", False)
    ):
        logger.warning(
            "projection.party_zone_absent_with_characters slug=%s "
            "characters=%d — snapshot.location is empty while "
            "snapshot.characters is non-empty; visible_to() / "
            "in_same_zone() will mask every co-located target until "
            "a location is set (typically the first encounter).",
            sd.game_slug,
            len(snapshot.characters),
        )
        handler._party_zone_absent_warned = True

    for ch in snapshot.characters:
        name = ch.core.name
        if party_zone is not None:
            character_zones[name] = party_zone
        if is_hidden_status_list(ch.core.statuses):
            hidden_characters.add(name)
    for npc in snapshot.npcs:
        name = npc.core.name
        if npc.location:
            character_zones[name] = npc.location
        if is_hidden_status_list(npc.core.statuses):
            hidden_characters.add(name)

    return SessionGameStateView(
        gm_player_id=gm_player_id,
        player_id_to_character=mapping,
        character_zones=character_zones,
        hidden_characters=hidden_characters,
    )
```

> **Note on the in-module call:** `self._is_hidden_status_list(...)` becomes `is_hidden_status_list(...)` (the free function in this same module). Both call sites at the original file:782 and file:788 use the new bare name.

> **Note on `logger`:** `views.py` imports `logger` from `sidequest.server.session_handler`. This matches the Phase 1 pattern (`emitters.py` does the same). Per the spec's "out of scope" section, we do not split out a per-module logger in this epic — that's a post-epic cleanup story.

- [ ] **Step 3.4: Replace the method body in `session_handler.py`**

In `sidequest-server/sidequest/server/session_handler.py`, find:

```python
    def _build_game_state_view(self) -> SessionGameStateView:
```

(currently at file:671)

Replace its full body (file:671-796) with:

```python
    def _build_game_state_view(self) -> SessionGameStateView:
        """Read-only view of current session state. Delegates to ``views.build_game_state_view``.

        Phase 2 of session_handler decomposition (see
        docs/superpowers/specs/2026-04-27-session-handler-decomposition-design.md).
        """
        from sidequest.server import views

        return views.build_game_state_view(self)
```

- [ ] **Step 3.5: Run the wiring test — confirm it passes**

```bash
uv run pytest tests/server/test_views.py::test_build_game_state_view_delegate_calls_module_function -v
```

Expected: PASS.

- [ ] **Step 3.6: Run the canonical integration tests for this code path**

```bash
uv run pytest tests/server/test_session_handler_view.py tests/integration/test_visibility_wiring.py tests/server/test_projection_end_to_end_wiring.py -v
```

Expected: all PASS. These exercise `_build_game_state_view` end-to-end — a regression here is unmistakable.

- [ ] **Step 3.7: Run the full server test suite**

```bash
uv run pytest -v
```

Expected: all PASS except the three pre-existing failures.

- [ ] **Step 3.8: Commit**

```bash
git add sidequest-server/sidequest/server/views.py sidequest-server/sidequest/server/session_handler.py sidequest-server/tests/server/test_views.py
git commit -m "refactor(server): extract _build_game_state_view to views module"
```

---

## Task 4: Extract `status_effects_by_player` → `views.status_effects_by_player`

**Files:**
- Modify: `sidequest-server/sidequest/server/views.py`
- Modify: `sidequest-server/sidequest/server/session_handler.py:798-823`
- Modify: `sidequest-server/tests/server/test_views.py`

- [ ] **Step 4.1: Add wiring test**

Append to `sidequest-server/tests/server/test_views.py`:

```python
def test_status_effects_by_player_delegate_calls_module_function(
    monkeypatch, session_handler_factory
) -> None:
    """Wiring guard — WebSocketSessionHandler.status_effects_by_player
    must delegate to views.status_effects_by_player."""
    from sidequest.server import views

    sd, handler = session_handler_factory()
    captured: list[object] = []
    sentinel = {"sentinel": ["yes"]}

    def _spy(h):
        captured.append(h)
        return sentinel

    monkeypatch.setattr(views, "status_effects_by_player", _spy)

    result = handler.status_effects_by_player()

    assert result is sentinel
    assert captured == [handler]
```

- [ ] **Step 4.2: Run the wiring test — confirm it fails**

```bash
uv run pytest tests/server/test_views.py::test_status_effects_by_player_delegate_calls_module_function -v
```

Expected: FAIL.

- [ ] **Step 4.3: Move the body into `views.py`**

Append to `sidequest-server/sidequest/server/views.py`:

```python
def status_effects_by_player(handler: WebSocketSessionHandler) -> dict[str, list[str]]:
    """Per-player status-effect tokens, for PerceptionRewriter.

    Reads the *existing* character-status map on the active
    ``GameSnapshot`` — no new state is introduced. Mirrors the
    player->character mapping used by :func:`build_game_state_view`:
    the session's active ``player_id`` is mapped to the first entry
    in ``snapshot.characters`` (single-player authoritative today;
    MP seat-assignment will feed the multi-player case via
    ``SessionRoom`` in a later sprint, at which point this accessor
    should fan out the same way).

    Returns ``dict[player_id, list[status_token]]``. An empty dict
    (no session, no snapshot, no characters) is safe: the rewriter
    treats missing entries as "no status effects".
    """
    sd = handler._session_data
    if sd is None:
        return {}
    snapshot = sd.snapshot
    if not snapshot.characters:
        return {}
    # Mirror build_game_state_view's mapping: active player_id ->
    # first character. Any connected non-active player_id gets []
    # until MP seat-assignment plumbs a real mapping.
    return {sd.player_id: [s.text for s in snapshot.characters[0].core.statuses]}
```

- [ ] **Step 4.4: Replace the method body in `session_handler.py`**

In `sidequest-server/sidequest/server/session_handler.py`, find:

```python
    def status_effects_by_player(self) -> dict[str, list[str]]:
```

(currently at file:798)

Replace its full body (file:798-823) with:

```python
    def status_effects_by_player(self) -> dict[str, list[str]]:
        """Per-player status-effect tokens. Delegates to ``views.status_effects_by_player``.

        Phase 2 of session_handler decomposition (see
        docs/superpowers/specs/2026-04-27-session-handler-decomposition-design.md).
        """
        from sidequest.server import views

        return views.status_effects_by_player(self)
```

- [ ] **Step 4.5: Run the wiring test — confirm it passes**

```bash
uv run pytest tests/server/test_views.py::test_status_effects_by_player_delegate_calls_module_function -v
```

Expected: PASS.

- [ ] **Step 4.6: Run the canonical integration test**

```bash
uv run pytest tests/server/test_perception_rewriter_wiring.py -v
```

Expected: all PASS. Note specifically that lines 262 and 314 of that test overwrite `handler.status_effects_by_player = lambda: ...` via direct attribute assignment — they replace the bound delegate method with a lambda. Because that assignment happens to the instance attribute, it shadows the class delegate and the lambda is what runs. The free function in `views.py` is bypassed by design in those tests. Both tests must continue to pass.

- [ ] **Step 4.7: Run the full server test suite**

```bash
uv run pytest -v
```

Expected: all PASS except the three pre-existing failures.

- [ ] **Step 4.8: Commit**

```bash
git add sidequest-server/sidequest/server/views.py sidequest-server/sidequest/server/session_handler.py sidequest-server/tests/server/test_views.py
git commit -m "refactor(server): extract status_effects_by_player to views module"
```

---

## Task 5: Extract `_backfill_last_narration_block` → `views.backfill_last_narration_block`

**Files:**
- Modify: `sidequest-server/sidequest/server/views.py`
- Modify: `sidequest-server/sidequest/server/session_handler.py:829-909`
- Modify: `sidequest-server/tests/server/test_views.py`

> **Note on `_build_message_for_kind`:** the function uses module-level `_build_message_for_kind` (defined at `session_handler.py:319`). The free function imports it lazily from `sidequest.server.session_handler` — same pattern Phase 1 used for `_KIND_TO_MESSAGE_CLS` and `_project_frames`.

- [ ] **Step 5.1: Add wiring test**

Append to `sidequest-server/tests/server/test_views.py`:

```python
def test_backfill_last_narration_block_delegate_calls_module_function(
    monkeypatch, session_handler_factory
) -> None:
    """Wiring guard — WebSocketSessionHandler._backfill_last_narration_block
    must delegate to views.backfill_last_narration_block."""
    from sidequest.server import views

    sd, handler = session_handler_factory()
    captured: list[tuple] = []
    sentinel: list[object] = []

    def _spy(h, *, player_id):
        captured.append((h, player_id))
        return sentinel

    monkeypatch.setattr(views, "backfill_last_narration_block", _spy)

    result = handler._backfill_last_narration_block(player_id="p:test")

    assert result is sentinel
    assert captured == [(handler, "p:test")]
```

- [ ] **Step 5.2: Run the wiring test — confirm it fails**

```bash
uv run pytest tests/server/test_views.py::test_backfill_last_narration_block_delegate_calls_module_function -v
```

Expected: FAIL.

- [ ] **Step 5.3: Move the body into `views.py`**

Append to `sidequest-server/sidequest/server/views.py`:

```python
def backfill_last_narration_block(
    handler: WebSocketSessionHandler,
    *,
    player_id: str,
) -> list[object]:
    """Fetch the most recent NARRATION (and its preceding CHAPTER_MARKER,
    if one was emitted without an intervening narration) from the event
    log and re-emit them as cached-projection messages — regardless of
    ``last_seen_seq``.

    Used to paint the narrative pane on a fresh-browser slug-resume
    where the normal replay would otherwise be empty because the
    client's persisted ``last_seen_seq`` already covers the tail.

    Returns the messages in emit order (CHAPTER_MARKER first if present,
    then NARRATION). Silently returns an empty list when no narration
    has been logged, when the cache has no include=True decision for
    the relevant event, or when the event log is unavailable. The
    caller is responsible for updating replay telemetry.
    """
    from sidequest.server.session_handler import _build_message_for_kind

    if handler._event_log is None or handler._projection_cache is None:
        return []
    store = handler._event_log.store
    with store._conn:
        narration_row = store._conn.execute(
            "SELECT seq, kind, payload_json FROM events "
            "WHERE kind = 'NARRATION' "
            "ORDER BY seq DESC LIMIT 1",
        ).fetchone()
    if narration_row is None:
        return []
    narration_seq = int(narration_row[0])

    with store._conn:
        chapter_row = store._conn.execute(
            "SELECT seq, kind, payload_json FROM events "
            "WHERE kind = 'CHAPTER_MARKER' AND seq < ? "
            "  AND seq > COALESCE("
            "    (SELECT MAX(seq) FROM events "
            "     WHERE kind = 'NARRATION' AND seq < ?),"
            "    0"
            "  ) "
            "ORDER BY seq DESC LIMIT 1",
            (narration_seq, narration_seq),
        ).fetchone()

    def _cached_payload(seq: int) -> str | None:
        with store._conn:
            row = store._conn.execute(
                "SELECT include, payload_json FROM projection_cache "
                "WHERE player_id = ? AND event_seq = ?",
                (player_id, seq),
            ).fetchone()
        if row is None or not bool(row[0]) or row[1] is None:
            return None
        return str(row[1])

    messages: list[object] = []
    if chapter_row is not None:
        chapter_seq = int(chapter_row[0])
        chapter_payload = _cached_payload(chapter_seq)
        if chapter_payload is not None:
            messages.append(
                _build_message_for_kind(
                    kind="CHAPTER_MARKER",
                    payload_json=chapter_payload,
                    seq=chapter_seq,
                )
            )

    narration_payload = _cached_payload(narration_seq)
    if narration_payload is None:
        return messages  # Can't emit bare chapter without its narration
    messages.append(
        _build_message_for_kind(
            kind="NARRATION",
            payload_json=narration_payload,
            seq=narration_seq,
        )
    )
    return messages
```

- [ ] **Step 5.4: Replace the method body in `session_handler.py`**

In `sidequest-server/sidequest/server/session_handler.py`, find:

```python
    def _backfill_last_narration_block(
        self,
        *,
        player_id: str,
    ) -> list[object]:
```

(currently at file:829)

Replace its full body (file:829-909) with:

```python
    def _backfill_last_narration_block(
        self,
        *,
        player_id: str,
    ) -> list[object]:
        """Backfill last narration block on slug-resume.
        Delegates to ``views.backfill_last_narration_block``.

        Phase 2 of session_handler decomposition (see
        docs/superpowers/specs/2026-04-27-session-handler-decomposition-design.md).
        """
        from sidequest.server import views

        return views.backfill_last_narration_block(self, player_id=player_id)
```

- [ ] **Step 5.5: Run the wiring test — confirm it passes**

```bash
uv run pytest tests/server/test_views.py::test_backfill_last_narration_block_delegate_calls_module_function -v
```

Expected: PASS.

- [ ] **Step 5.6: Run any integration tests that exercise slug-resume backfill**

```bash
uv run pytest -k "slug_resume or backfill or last_narration" -v
```

Expected: all PASS (or no tests collected if there are no name-matching tests; the global-suite run in step 5.7 still covers them indirectly).

- [ ] **Step 5.7: Run the full server test suite**

```bash
uv run pytest -v
```

Expected: all PASS except the three pre-existing failures.

- [ ] **Step 5.8: Commit**

```bash
git add sidequest-server/sidequest/server/views.py sidequest-server/sidequest/server/session_handler.py sidequest-server/tests/server/test_views.py
git commit -m "refactor(server): extract _backfill_last_narration_block to views module"
```

---

## Task 6: Extract `_party_member_from_character` → `views.party_member_from_character`

**Files:**
- Modify: `sidequest-server/sidequest/server/views.py`
- Modify: `sidequest-server/sidequest/server/session_handler.py:4860-4947`
- Modify: `sidequest-server/tests/server/test_views.py`

> **Note on `_resolve_location_display`:** imported lazily from `sidequest.server.session_helpers` — that's its canonical home (`session_handler.py` re-exports it for back-compat).

> **Note on protocol types:** `PartyMember`, `CharacterSheetDetails`, `InventoryPayload`, `InventoryItem`, `NonBlankString` are imported lazily inside the function body (mirrors the original method's existing pattern).

- [ ] **Step 6.1: Add wiring test**

Append to `sidequest-server/tests/server/test_views.py`:

```python
def test_party_member_from_character_delegate_calls_module_function(
    monkeypatch, session_handler_factory
) -> None:
    """Wiring guard — WebSocketSessionHandler._party_member_from_character
    must delegate to views.party_member_from_character."""
    from sidequest.server import views

    sd, handler = session_handler_factory()
    sentinel = object()
    captured: list[tuple] = []

    def _spy(h, sd_arg, character, player_id, player_name):
        captured.append((h, sd_arg, character, player_id, player_name))
        return sentinel

    monkeypatch.setattr(views, "party_member_from_character", _spy)

    fake_char = object()
    result = handler._party_member_from_character(sd, fake_char, "p:abc", "Alice")

    assert result is sentinel
    assert captured == [(handler, sd, fake_char, "p:abc", "Alice")]
```

- [ ] **Step 6.2: Run the wiring test — confirm it fails**

```bash
uv run pytest tests/server/test_views.py::test_party_member_from_character_delegate_calls_module_function -v
```

Expected: FAIL.

- [ ] **Step 6.3: Move the body into `views.py`**

Append to `sidequest-server/sidequest/server/views.py`:

```python
def party_member_from_character(
    handler: WebSocketSessionHandler,
    sd: _SessionData,
    character: Character,
    player_id: str,
    player_name: str,
):
    """Build a single PartyMember from a Character object.

    Factored out of :func:`build_session_start_party_status` so the
    same construction can run for the requesting socket's PC and for
    peer PCs that landed in the snapshot via multiplayer chargen.
    """
    from sidequest.protocol.messages import (
        CharacterSheetDetails,
        InventoryItem,
        InventoryPayload,
        PartyMember,
    )
    from sidequest.protocol.types import NonBlankString
    from sidequest.server.session_helpers import _resolve_location_display

    # Inventory is stored as list[dict] in Phase 1 (creature_core.py:158).
    # Filter to Carried items — identical to Rust's inventory.carried()
    # iterator, which skips Stored/Dropped.
    carried = [
        item
        for item in character.core.inventory.items
        if str(item.get("state", "Carried")) == "Carried"
    ]

    stats = dict(character.stats)
    abilities = [a.name for a in character.abilities]
    equipment = [
        f"{item['name']} [equipped]" if item.get("equipped") else item["name"]
        for item in carried
    ]

    sheet = CharacterSheetDetails(
        race=NonBlankString(character.race),
        stats=stats,
        abilities=abilities,
        backstory=NonBlankString(character.backstory or "(no backstory)"),
        personality=NonBlankString(character.core.personality),
        pronouns=NonBlankString(character.pronouns) if character.pronouns else None,
        equipment=equipment,
    )

    # Currency noun from inventory.yaml::currency.name (pingpong
    # 2026-04-24 fantasy-leak bug). None → UI neutral fallback;
    # no silent default to "gold".
    currency_name: str | None = None
    if sd.genre_pack.inventory is not None and sd.genre_pack.inventory.currency is not None:
        currency_name = sd.genre_pack.inventory.currency.name

    inventory_payload = InventoryPayload(
        items=[
            InventoryItem(
                name=NonBlankString(str(item["name"])),
                # Protocol alias: "type". Dicts carry "category" from
                # the loadout encoder; map and keep a non-blank string.
                **{"type": str(item.get("category", "equipment") or "equipment")},  # type: ignore[arg-type]
                equipped=bool(item.get("equipped", False)),
                quantity=int(item.get("quantity", 1)),
                description=NonBlankString(str(item.get("description") or item["name"])),
            )
            for item in carried
        ],
        gold=character.core.inventory.gold,
        currency_name=currency_name,
    )

    location_nbs: NonBlankString | None = None
    loc_display = _resolve_location_display(sd.genre_pack, sd.world_slug, sd.snapshot.location)
    if loc_display:
        try:
            location_nbs = NonBlankString(loc_display)
        except Exception:
            location_nbs = None

    class_nbs = NonBlankString(character.char_class or "Adventurer")
    char_name_nbs = NonBlankString(character.core.name)

    return PartyMember(
        player_id=NonBlankString(player_id or "anon"),
        name=NonBlankString(player_name or "Player"),
        character_name=char_name_nbs,
        current_hp=character.core.edge.current,
        max_hp=character.core.edge.max,
        statuses=[s.text for s in character.core.statuses],
        **{"class": class_nbs},  # type: ignore[arg-type]
        level=character.core.level,
        portrait_url=None,
        current_location=location_nbs,
        sheet=sheet,
        inventory=inventory_payload,
    )
```

- [ ] **Step 6.4: Replace the method body in `session_handler.py`**

In `sidequest-server/sidequest/server/session_handler.py`, find:

```python
    def _party_member_from_character(
        self,
        sd: _SessionData,
        character: Character,
        player_id: str,
        player_name: str,
    ) -> PartyMember:
```

(currently at file:4860)

Replace its full body (file:4860-4947) with:

```python
    def _party_member_from_character(
        self,
        sd: _SessionData,
        character: Character,
        player_id: str,
        player_name: str,
    ) -> PartyMember:
        """Build a single PartyMember. Delegates to ``views.party_member_from_character``.

        Phase 2 of session_handler decomposition (see
        docs/superpowers/specs/2026-04-27-session-handler-decomposition-design.md).
        """
        from sidequest.server import views

        return views.party_member_from_character(self, sd, character, player_id, player_name)
```

- [ ] **Step 6.5: Run the wiring test — confirm it passes**

```bash
uv run pytest tests/server/test_views.py::test_party_member_from_character_delegate_calls_module_function -v
```

Expected: PASS.

- [ ] **Step 6.6: Run the canonical integration test**

```bash
uv run pytest tests/server/test_multiplayer_party_status.py -v
```

Expected: all PASS. This test exercises `_party_member_from_character` end-to-end through `_build_session_start_party_status`.

- [ ] **Step 6.7: Run the full server test suite**

```bash
uv run pytest -v
```

Expected: all PASS except the three pre-existing failures.

- [ ] **Step 6.8: Commit**

```bash
git add sidequest-server/sidequest/server/views.py sidequest-server/sidequest/server/session_handler.py sidequest-server/tests/server/test_views.py
git commit -m "refactor(server): extract _party_member_from_character to views module"
```

---

## Task 7: Extract `_resolve_self_character` → `views.resolve_self_character`

**Files:**
- Modify: `sidequest-server/sidequest/server/views.py`
- Modify: `sidequest-server/sidequest/server/session_handler.py:4949-4981`
- Modify: `sidequest-server/tests/server/test_views.py`

- [ ] **Step 7.1: Add wiring test**

Append to `sidequest-server/tests/server/test_views.py`:

```python
def test_resolve_self_character_delegate_calls_module_function(
    monkeypatch, session_handler_factory
) -> None:
    """Wiring guard — WebSocketSessionHandler._resolve_self_character
    must delegate to views.resolve_self_character."""
    from sidequest.server import views

    sd, handler = session_handler_factory()
    sentinel = object()
    captured: list[tuple] = []

    def _spy(h, sd_arg):
        captured.append((h, sd_arg))
        return sentinel

    monkeypatch.setattr(views, "resolve_self_character", _spy)

    result = handler._resolve_self_character(sd)

    assert result is sentinel
    assert captured == [(handler, sd)]
```

- [ ] **Step 7.2: Run the wiring test — confirm it fails**

```bash
uv run pytest tests/server/test_views.py::test_resolve_self_character_delegate_calls_module_function -v
```

Expected: FAIL.

- [ ] **Step 7.3: Move the body into `views.py`**

Append to `sidequest-server/sidequest/server/views.py`:

```python
def resolve_self_character(
    handler: WebSocketSessionHandler,
    sd: _SessionData,
) -> Character | None:
    """Find the Character belonging to ``sd.player_id`` in the snapshot.

    Used to disambiguate "which PC is *me*" when the snapshot carries
    multiple PCs (multiplayer). Returning ``snapshot.characters[0]`` is
    wrong for any player whose seat isn't first — that's the playtest
    2026-04-25 "Tab 2 sees Laverne (YOU)" bug. The seat map (written at
    chargen-commit, lines 2440-2475) is the source of truth; the room
    seat is the live runtime mirror used as a fallback.

    Returns ``None`` for legacy saves with no ``player_seats`` binding
    AND no live room seat (very old solo saves). Callers should fall
    back to ``snapshot.characters[0]`` in that case to keep solo
    single-PC sessions working.
    """
    snapshot = sd.snapshot
    if not snapshot.characters:
        return None
    if sd.player_id and snapshot.player_seats:
        char_name = snapshot.player_seats.get(sd.player_id)
        if char_name:
            for c in snapshot.characters:
                if c.core.name == char_name:
                    return c
    if sd.player_id and handler._room is not None:
        seat_lookup = getattr(handler._room, "slot_to_player_id", None)
        if callable(seat_lookup):
            for slot, pid in seat_lookup().items():
                if pid == sd.player_id:
                    for c in snapshot.characters:
                        if c.core.name == slot:
                            return c
    return None
```

- [ ] **Step 7.4: Replace the method body in `session_handler.py`**

In `sidequest-server/sidequest/server/session_handler.py`, find:

```python
    def _resolve_self_character(self, sd: _SessionData) -> Character | None:
```

(currently at file:4949)

Replace its full body (file:4949-4981) with:

```python
    def _resolve_self_character(self, sd: _SessionData) -> Character | None:
        """Find the Character belonging to ``sd.player_id``. Delegates to
        ``views.resolve_self_character``.

        Phase 2 of session_handler decomposition (see
        docs/superpowers/specs/2026-04-27-session-handler-decomposition-design.md).
        """
        from sidequest.server import views

        return views.resolve_self_character(self, sd)
```

- [ ] **Step 7.5: Run the wiring test — confirm it passes**

```bash
uv run pytest tests/server/test_views.py::test_resolve_self_character_delegate_calls_module_function -v
```

Expected: PASS.

- [ ] **Step 7.6: Run the canonical integration tests**

```bash
uv run pytest tests/server/test_multiplayer_party_status.py -v
```

Expected: all PASS — specifically `test_resolve_self_character_uses_player_seats_binding`, `test_resolve_self_character_uses_room_seat_when_player_seats_empty`, and `test_resolve_self_character_returns_none_for_legacy_solo`.

- [ ] **Step 7.7: Run the full server test suite**

```bash
uv run pytest -v
```

Expected: all PASS except the three pre-existing failures.

- [ ] **Step 7.8: Commit**

```bash
git add sidequest-server/sidequest/server/views.py sidequest-server/sidequest/server/session_handler.py sidequest-server/tests/server/test_views.py
git commit -m "refactor(server): extract _resolve_self_character to views module"
```

---

## Task 8: Extract `_build_session_start_party_status` → `views.build_session_start_party_status`

**Files:**
- Modify: `sidequest-server/sidequest/server/views.py`
- Modify: `sidequest-server/sidequest/server/session_handler.py:4983-5022`
- Modify: `sidequest-server/tests/server/test_views.py`

> **Note on intra-module call:** `self._party_member_from_character(...)` becomes `party_member_from_character(handler, ...)` (the in-module free function from Task 6).

- [ ] **Step 8.1: Add wiring test**

Append to `sidequest-server/tests/server/test_views.py`:

```python
def test_build_session_start_party_status_delegate_calls_module_function(
    monkeypatch, session_handler_factory
) -> None:
    """Wiring guard — WebSocketSessionHandler._build_session_start_party_status
    must delegate to views.build_session_start_party_status."""
    from sidequest.server import views

    sd, handler = session_handler_factory()
    sentinel = object()
    captured: list[tuple] = []

    def _spy(h, sd_arg, character, player_id):
        captured.append((h, sd_arg, character, player_id))
        return sentinel

    monkeypatch.setattr(views, "build_session_start_party_status", _spy)

    fake_char = object()
    result = handler._build_session_start_party_status(sd, fake_char, "p:abc")

    assert result is sentinel
    assert captured == [(handler, sd, fake_char, "p:abc")]
```

- [ ] **Step 8.2: Run the wiring test — confirm it fails**

```bash
uv run pytest tests/server/test_views.py::test_build_session_start_party_status_delegate_calls_module_function -v
```

Expected: FAIL.

- [ ] **Step 8.3: Move the body into `views.py`**

Append to `sidequest-server/sidequest/server/views.py`:

```python
def build_session_start_party_status(
    handler: WebSocketSessionHandler,
    sd: _SessionData,
    character: Character,
    player_id: str,
) -> PartyStatusMessage:
    """PARTY_STATUS frame at chargen end (Rust connect.rs:2533).

    MP: enumerates every PC; maps each slot back to its seating
    player_id via the room. Falls back to ``peer:<name>`` when
    no seat record is available.
    """
    from sidequest.protocol.messages import (
        PartyMember,
        PartyStatusMessage,
        PartyStatusPayload,
    )

    seat_map: dict[str, str] = {}
    if handler._room is not None:
        seat_lookup = getattr(handler._room, "slot_to_player_id", None)
        if callable(seat_lookup):
            seat_map = seat_lookup()

    members: list[PartyMember] = []
    all_chars = list(sd.snapshot.characters or [])
    if not all_chars:
        all_chars = [character]
    # Stable ordering: self first, then peers in snapshot order.
    self_chars = [c for c in all_chars if c.core.name == character.core.name]
    peer_chars = [c for c in all_chars if c.core.name != character.core.name]
    for char in self_chars + peer_chars:
        is_self = char.core.name == character.core.name
        if is_self:
            pid = player_id or "anon"
            pname = sd.player_name or "Player"
        else:
            pid = seat_map.get(char.core.name) or f"peer:{char.core.name}"
            pname = char.core.name
        members.append(party_member_from_character(handler, sd, char, pid, pname))

    return PartyStatusMessage(
        type="PARTY_STATUS",  # type: ignore[arg-type]
        payload=PartyStatusPayload(members=members),
        player_id=player_id,
    )
```

> **Note on intra-module calls:** `self._party_member_from_character(sd, char, pid, pname)` becomes `party_member_from_character(handler, sd, char, pid, pname)` (direct in-module call, byte-identical behavior). The handler delegate is reserved for callers outside this module.

- [ ] **Step 8.4: Replace the method body in `session_handler.py`**

In `sidequest-server/sidequest/server/session_handler.py`, find:

```python
    def _build_session_start_party_status(
        self,
        sd: _SessionData,
        character: Character,
        player_id: str,
    ) -> PartyStatusMessage:
```

(currently at file:4983)

Replace its full body (file:4983-5022) with:

```python
    def _build_session_start_party_status(
        self,
        sd: _SessionData,
        character: Character,
        player_id: str,
    ) -> PartyStatusMessage:
        """PARTY_STATUS frame at chargen end. Delegates to ``views.build_session_start_party_status``.

        Phase 2 of session_handler decomposition (see
        docs/superpowers/specs/2026-04-27-session-handler-decomposition-design.md).
        """
        from sidequest.server import views

        return views.build_session_start_party_status(self, sd, character, player_id)
```

- [ ] **Step 8.5: Run the wiring test — confirm it passes**

```bash
uv run pytest tests/server/test_views.py::test_build_session_start_party_status_delegate_calls_module_function -v
```

Expected: PASS.

- [ ] **Step 8.6: Run the skeleton import-existence test — it must finally GO GREEN**

```bash
uv run pytest tests/server/test_views.py::test_views_module_exposes_required_functions -v
```

Expected: **PASS for the first time.** All seven functions are now extracted. The epic-level RED→GREEN gate has flipped.

- [ ] **Step 8.7: Run the canonical integration test**

```bash
uv run pytest tests/server/test_multiplayer_party_status.py -v
```

Expected: all PASS — exercises the full PARTY_STATUS construction.

- [ ] **Step 8.8: Run the full server test suite**

```bash
uv run pytest -v
```

Expected: all PASS except the three pre-existing failures.

- [ ] **Step 8.9: Commit**

```bash
git add sidequest-server/sidequest/server/views.py sidequest-server/sidequest/server/session_handler.py sidequest-server/tests/server/test_views.py
git commit -m "refactor(server): extract _build_session_start_party_status to views module"
```

---

## Task 9: OTEL parity verification

**Files:** none modified — read-only verification.

> **Why this task is short for Phase 2:** the view-projection cluster has very few OTEL emissions compared to the emitters cluster. `_build_game_state_view` emits two `logger.warning` lines (no `_watcher_publish`); the other six methods are pure projection with zero telemetry. Parity is therefore a quick count rather than a structural check.

- [ ] **Step 9.1: Confirm `_watcher_publish` count is preserved across `session_handler.py` + `views.py` + `emitters.py`**

```bash
# Baseline at branch base (Phase 1 merge commit 4ab3e26)
git -C sidequest-server show 4ab3e26:sidequest/server/session_handler.py | grep -cE "_watcher_publish\("
git -C sidequest-server show 4ab3e26:sidequest/server/emitters.py | grep -cE "_watcher_publish\("
# Now (after Phase 2)
grep -cE "_watcher_publish\(" sidequest-server/sidequest/server/session_handler.py
grep -cE "_watcher_publish\(" sidequest-server/sidequest/server/emitters.py
grep -cE "_watcher_publish\(" sidequest-server/sidequest/server/views.py
```

Expected: `(session_handler@4ab3e26) + (emitters@4ab3e26)` == `(session_handler now) + (emitters now) + (views now)`. The view cluster did not own any `_watcher_publish` calls in the original methods, so `views.py` should report `0`. The session_handler.py and emitters.py counts must be unchanged from `4ab3e26`.

- [ ] **Step 9.2: Confirm `tracer.start_as_current_span` count is preserved**

```bash
git -C sidequest-server show 4ab3e26:sidequest/server/session_handler.py | grep -cE "tracer\.start_as_current_span"
grep -cE "tracer\.start_as_current_span" sidequest-server/sidequest/server/session_handler.py
grep -cE "tracer\.start_as_current_span" sidequest-server/sidequest/server/views.py
```

Expected: combined count after Phase 2 ≥ original. The view cluster did not own any spans, so `views.py` should report `0`.

- [ ] **Step 9.3: No commit — this task is verification only**

If parity is preserved, proceed to Task 10. If not, the most likely culprit is a missing `logger.warning` in `build_game_state_view` (the GM-identity and party-zone-absent warnings) — read the diff and reconcile.

---

## Task 10: Final cleanup and integration check

**Files:**
- Modify: `sidequest-server/sidequest/server/session_handler.py` (line-count check only)

- [ ] **Step 10.1: Confirm `session_handler.py` line count dropped**

```bash
wc -l sidequest-server/sidequest/server/session_handler.py
```

Expected: approximately **4611 lines** (down from 5071 at `4ab3e26`). Allow ±20 lines of variance from the spec's `-460` estimate — exact count depends on delegate-method docstring length.

- [ ] **Step 10.2: Run lint**

```bash
just server-lint
```

Or from `sidequest-server/`:
```bash
uv run ruff check .
```

Expected: clean (the two pre-existing `SIM102`/`SIM105` warnings on `session_handler.py:717` and `:1075` may still be present — those are out of scope per Standing Rules). If `views.py` has any lint warnings, fix them inline. Common likely warnings: `UP037` for quoted forward references (none should appear since we used unquoted names with `from __future__ import annotations`), `F401` for unused imports.

- [ ] **Step 10.3: Run formatter**

```bash
just server-fmt
```

Or:
```bash
uv run ruff format .
```

Expected: no changes. If `views.py` got reformatted, capture the diff and commit it as a separate cosmetic-format commit at Step 10.5.

- [ ] **Step 10.4: Run the full check gate**

```bash
just server-check
```

Expected: lint clean (modulo the two pre-existing warnings) and tests all pass except the three pre-existing failures.

- [ ] **Step 10.5: Final commit if formatter made changes**

If `just server-fmt` produced a diff:

```bash
git add -u
git commit -m "refactor(server): apply ruff format to views.py extraction"
```

Otherwise skip this step.

---

## Definition of Done — Phase 2

- ✅ `sidequest-server/sidequest/server/views.py` exists with seven free functions (`is_hidden_status_list`, `build_game_state_view`, `status_effects_by_player`, `backfill_last_narration_block`, `party_member_from_character`, `resolve_self_character`, `build_session_start_party_status`) plus the module-level `_HIDDEN_STATUS_TOKENS` constant.
- ✅ Seven thin delegate methods on `WebSocketSessionHandler` route to the new module. The classmethod nature of `_is_hidden_status_list` is preserved.
- ✅ The class-level `_HIDDEN_STATUS_TOKENS` constant on `WebSocketSessionHandler` is removed.
- ✅ `tests/server/test_views.py` exists with the skeleton import-existence test (now green) plus seven wiring tests (one per delegate) plus the behavioral test for `is_hidden_status_list`.
- ✅ All existing server integration tests pass without modification (especially `test_session_handler_view.py`, `test_multiplayer_party_status.py`, `test_perception_rewriter_wiring.py`, `test_visibility_wiring.py`, and the projection wiring tests that pull views indirectly through `emitters.emit_event`).
- ✅ `session_handler.py` line count dropped by ~460 lines (from 5071 → ~4611).
- ✅ OTEL `_watcher_publish` and span surface preserved across `session_handler.py`, `emitters.py`, and `views.py` combined.
- ✅ `just server-check` passes (modulo the two pre-existing lint warnings and three pre-existing test failures listed in Standing Rules).
- ✅ Eight commits land in this order: skeleton, is_hidden_status_list, build_game_state_view, status_effects_by_player, backfill_last_narration_block, party_member_from_character, resolve_self_character, build_session_start_party_status (plus an optional formatter commit if step 10.5 produced one).

## What This Plan Does NOT Cover

- Phases 3–8 of the spec (lore/embed, media, chargen, small handlers, connect, narration turn). Each gets its own plan after Phase 2 lands.
- Removal of the seven thin delegate methods on `WebSocketSessionHandler`. Per the spec, the delegates stay for the duration of the epic; their removal is a follow-up cleanup story.
- A per-module `logger = logging.getLogger(__name__)` in `views.py`. The final reviewer in Phase 1 flagged this as logger-namespace debt; per spec it is post-epic cleanup, not in scope here.
- Any behavioral change. Pure decomposition only.
- Updating the stale docstring reference at `sidequest/game/projection/view.py:32` (`WebSocketSessionHandler._HIDDEN_STATUS_TOKENS`). Out of scope; can be addressed in the post-epic cleanup story.

---

## Self-Review Notes

**Spec coverage check:**
- All seven Phase 2 source methods listed in spec → Tasks 2–8 (in dependency order).
- Spec acceptance criteria: ✅ free functions exist (Tasks 2–8), ✅ thin delegates (each Task's "replace body" step), ✅ wiring test per delegate (each Task), ✅ behavioral test for the simplest function — `is_hidden_status_list` (Task 2 step 2.6), ✅ existing integration tests pass (each Task's full-suite step, plus targeted canonical tests in steps 3.6, 4.6, 6.6, 7.6, 8.7), ✅ OTEL parity (Task 9), ✅ line-count delta and lint (Task 10).

**Placeholder scan:** No `TBD`, `TODO`, "implement later", or skeleton-only steps. Every code block is complete and copy-pasteable; every command has explicit expected output.

**Type consistency:**
- All seven free functions take `handler: WebSocketSessionHandler` as their first positional argument (or, in the case of `is_hidden_status_list`, no handler — it's pure on `list[Status]`).
- Function names use the unprefixed forms (`build_*`, `resolve_*`, `party_*`, `is_*`) consistently.
- Delegate names retain their original underscore conventions (`_build_game_state_view`, `_resolve_self_character`, etc.) — public delegate `status_effects_by_player` (no leading underscore) likewise stays unchanged because it is publicly invoked from `emitters.py:130` and via direct attribute reassignment in `test_perception_rewriter_wiring.py:262/314`.
- Return types match the original method signatures (`SessionGameStateView`, `dict[str, list[str]]`, `list[object]`, `PartyMember`, `Character | None`, `PartyStatusMessage`, `bool`).
- Inter-task references: Task 3's `is_hidden_status_list(...)` calls match Task 2's signature. Task 8's `party_member_from_character(handler, sd, char, pid, pname)` calls match Task 6's signature.

**Known imperfection:** Task 9's OTEL parity check uses a "≥ original count" threshold like Phase 1 did. The view cluster owns zero `_watcher_publish` and zero spans by inspection, so the practical check is "did session_handler.py + emitters.py counts decrease unexpectedly?" An exact `git show 4ab3e26:...` baseline is provided in step 9.1; the implementer can run the diff in seconds.

**Subagent prompt rules baked in:** Standing Rules section at the top of this plan repeats the no-`git stash`, do-not-modify-skeleton-test, pre-existing-failures, and pinned-cwd directives that subagents do not inherit from user memory. Each per-task implementer prompt should re-quote these rules verbatim.
