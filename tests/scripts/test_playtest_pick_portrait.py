"""RED tests for Story 105-1 — teach the headless playtest driver to answer
the Epic-66 ``pick_portrait`` chargen frame.

Context (Epic 105 / ADR-106): ``scenarios/beneath_sunden_engagement.yaml``
(Story 59-15) is the span-proof instrument that proves the surface→deep
crossing fires. Today it dies at chargen with ``WrongPhaseError`` because the
driver's ``AutoChargen`` never answers the one-time ``pick_portrait`` frame the
server interposes at the Confirmation boundary (Epic 66). The frame arrives as
``phase=scene, input_type=pick_portrait``; ``AutoChargen.respond`` falls through
to ``make_chargen_continue()`` (a ``phase=continue`` message), which does NOT
satisfy the server's ``portrait_confirm`` expectation, so chargen stalls and the
next game action is rejected with ``WrongPhaseError``.

The fix: ``AutoChargen.respond`` must answer the ``pick_portrait`` frame with a
``phase=portrait_confirm`` message that SKIPS (no portrait chosen) — deterministic,
cosmetic-free, and additive so Story 90-9's class-honoring chargen change layers
cleanly on top.

These are pure unit tests on the driver's strategy object — no live server. The
fixture frame mirrors the server's emitter verbatim:
``sidequest-server/.../websocket_handlers/chargen_mixin.py::_render_portrait_scene``
(``phase=scene``, ``input_type=pick_portrait``, ``portraits_available``,
``suggest_archetype``, ``suggest_culture``). Keeping the fixture identical to the
production frame is the wiring guard: if the server frame shape drifts, this
fixture must move with it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

from playtest import AutoChargen  # noqa: E402


# ── Fixture: the exact frame the server emits (chargen_mixin._render_portrait_scene) ──


def _pick_portrait_frame(
    *,
    portraits_available: bool = True,
    suggest_archetype: str | None = "mage",
    suggest_culture: str | None = None,
) -> dict:
    """A ``pick_portrait`` CHARACTER_CREATION payload as the server sends it.

    Mirrors ``CharacterCreationPayload`` fields set by ``_render_portrait_scene``:
    ``phase=scene``, ``input_type=pick_portrait``, plus the soft-suggest hints.
    Crucially it carries NO ``choices`` and is NOT ``allows_freeform`` — that is
    precisely why the current generic-scene fall-through misfires.
    """
    return {
        "phase": "scene",
        "prompt": "Choose a portrait for your character — or skip to continue.",
        "input_type": "pick_portrait",
        "portraits_available": portraits_available,
        "suggest_archetype": suggest_archetype,
        "suggest_culture": suggest_culture,
    }


# ── AC-1: the pick_portrait frame is answered with phase=portrait_confirm ─────


class TestPickPortraitAnswered:
    def test_pick_portrait_frame_returns_portrait_confirm(self):
        """AutoChargen.respond on the pick_portrait frame must emit exactly one
        outbound CHARACTER_CREATION message with phase=portrait_confirm."""
        ac = AutoChargen(class_pref="Mage")
        out = ac.respond(_pick_portrait_frame())

        assert len(out) == 1, f"expected exactly one reply, got {out!r}"
        msg = out[0]
        assert msg["type"] == "CHARACTER_CREATION", f"wrong message type: {msg!r}"
        assert msg["payload"].get("phase") == "portrait_confirm", (
            f"pick_portrait frame must be answered with phase=portrait_confirm, "
            f"got {msg['payload'].get('phase')!r}"
        )

    def test_pick_portrait_works_without_class_pref(self):
        """The portrait answer is class-agnostic — a no-class-pref driver (the
        default strategy=auto path) must also clear the frame."""
        ac = AutoChargen()
        out = ac.respond(_pick_portrait_frame(suggest_archetype=None))

        assert len(out) == 1
        assert out[0]["payload"].get("phase") == "portrait_confirm"

    def test_pick_portrait_answered_even_when_no_pickers_available(self):
        """Even when the world ships no picker portraits
        (``portraits_available=False``), the server still interposes the frame
        and still expects a portrait_confirm — the driver must answer it."""
        ac = AutoChargen()
        out = ac.respond(_pick_portrait_frame(portraits_available=False))

        assert len(out) == 1
        assert out[0]["payload"].get("phase") == "portrait_confirm"


# ── AC-2: the answer is a SKIP — the driver never picks a portrait ───────────


class TestPickPortraitSkips:
    def test_portrait_confirm_is_a_skip(self):
        """A skip means no portrait slug: selected_portrait_ref is absent, None,
        or empty. The driver must not invent a portrait ref (cosmetic, and a
        fabricated slug would be an unknown-ref WARN on the server)."""
        ac = AutoChargen(class_pref="Mage")
        out = ac.respond(_pick_portrait_frame())

        payload = out[0]["payload"]
        # Anchor on the portrait_confirm phase first so this is not vacuous —
        # otherwise the buggy phase=continue reply (which also lacks a ref)
        # would satisfy the skip assertion.
        assert payload.get("phase") == "portrait_confirm", (
            f"skip must be a portrait_confirm, got {payload.get('phase')!r}"
        )
        ref = payload.get("selected_portrait_ref")
        assert ref in (None, ""), (
            f"driver must SKIP the portrait step (empty selected_portrait_ref), "
            f"got {ref!r}"
        )


# ── AC-3: the pick_portrait frame must NOT be mishandled as a generic scene ──


class TestPickPortraitNotMisrouted:
    def test_pick_portrait_is_not_answered_with_continue(self):
        """The defect: the generic-scene fall-through answers pick_portrait with
        a phase=continue message, which the server does not accept as a portrait
        confirmation. Guard against the regression explicitly."""
        ac = AutoChargen(class_pref="Mage")
        out = ac.respond(_pick_portrait_frame())

        phases = [m["payload"].get("phase") for m in out]
        assert "continue" not in phases, (
            f"pick_portrait must not be answered with a generic 'continue' — {out!r}"
        )

    def test_pick_portrait_is_not_answered_with_scene_choice(self):
        """The frame carries no choices; the driver must not fabricate a
        scene-choice reply (phase=scene, choice=...) either."""
        ac = AutoChargen(class_pref="Mage")
        out = ac.respond(_pick_portrait_frame())

        assert out[0]["payload"].get("phase") != "scene", (
            f"pick_portrait must not be answered as a generic scene choice — {out!r}"
        )

    def test_pick_portrait_does_not_silently_stall(self):
        """An empty reply ([]) would silently stall chargen (No Silent
        Fallbacks): the driver would send the next game action while still in
        chargen and trigger WrongPhaseError. The frame must produce a reply."""
        ac = AutoChargen()
        out = ac.respond(_pick_portrait_frame())

        assert out, "pick_portrait frame must produce a reply, not silently stall"


# ── AC-4: existing chargen handling is unperturbed (additive change) ─────────


class TestExistingChargenUnaffected:
    """Regression guard: adding pick_portrait handling must be additive and not
    perturb the other input_types. Also protects against Story 90-9's overlapping
    chargen edits regressing these paths."""

    def test_select_scene_still_returns_scene_choice(self):
        ac = AutoChargen()
        out = ac.respond(
            {
                "phase": "scene",
                "input_type": "select",
                "choices": [{"label": "Fighter"}, {"label": "Mage"}],
            }
        )
        assert len(out) == 1
        assert out[0]["payload"].get("phase") == "scene"
        assert out[0]["payload"].get("choice") == "1"

    def test_class_pref_still_picks_matching_choice(self):
        """The Mage class_pref must still select the Mage choice — pick_portrait
        handling must not shadow the class-selection scene."""
        ac = AutoChargen(class_pref="Mage")
        out = ac.respond(
            {
                "phase": "scene",
                "input_type": "select",
                "choices": [{"label": "Fighter"}, {"label": "Mage"}],
            }
        )
        assert out[0]["payload"].get("choice") == "2", (
            "class_pref=Mage must still select the 2nd (Mage) choice"
        )

    def test_confirmation_phase_still_confirms(self):
        ac = AutoChargen()
        out = ac.respond({"phase": "confirmation"})
        assert out[0]["payload"].get("phase") == "confirmation"

    def test_complete_phase_still_marks_done(self):
        ac = AutoChargen()
        out = ac.respond({"phase": "complete"})
        assert out == []
        assert ac.done is True


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
