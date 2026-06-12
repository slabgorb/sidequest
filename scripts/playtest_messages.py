"""playtest_messages.py — Message styles, rendering, and construction helpers.

Renderers cover the 2026-era SideQuest WebSocket protocol (post-TTS removal,
slug-keyed connect, dice resolution protocol, structured chargen).
"""

import json

from rich.console import Console
from rich.text import Text

console = Console()

# ── Color coding by message type ────────────────────────────────────────────

MSG_STYLES = {
    "NARRATION": "white",
    "NARRATION_END": "dim",
    "THINKING": "dim cyan",
    "SESSION_EVENT": "bold green",
    "CHARACTER_CREATION": "bold yellow",
    "TURN_STATUS": "cyan",
    "PARTY_STATUS": "cyan",
    "CONFRONTATION": "bold magenta",
    "CONFRONTATION_OUTCOME": "bold magenta",
    "COMBAT_EVENT": "bold red",
    "IMAGE": "magenta",
    "RENDER_QUEUED": "dim magenta",
    "AUDIO_CUE": "blue",
    "VOICE_SIGNAL": "dim blue",
    "VOICE_TEXT": "dim blue",
    "ACTION_QUEUE": "cyan",
    "ACTION_REVEAL": "dim cyan",
    "INVENTORY": "yellow",
    "MAP_UPDATE": "green",
    "CHARACTER_SHEET": "yellow",
    "CHAPTER_MARKER": "bold magenta",
    "ERROR": "bold red",
    "DICE_REQUEST": "bold yellow",
    "DICE_THROW": "yellow",
    "DICE_RESULT": "bold yellow",
    "BEAT_SELECTION": "yellow",
    "JOURNAL_REQUEST": "dim",
    "JOURNAL_RESPONSE": "dim",
    "SCRAPBOOK_ENTRY": "dim",
    "TACTICAL_STATE": "green",
    "TACTICAL_GRID": "green",
    "TACTICAL_ACTION": "green",
    "ORBITAL_INTENT": "blue",
    "ORBITAL_CHART": "blue",
    "ACHIEVEMENT_EARNED": "bold green",
    "ITEM_DEPLETED": "yellow",
    "RESOURCE_MIN_REACHED": "bold yellow",
    "PLAYER_PRESENCE": "dim cyan",
    "PLAYER_SEAT": "dim cyan",
    "SEAT_CONFIRMED": "dim cyan",
    "GAME_PAUSED": "bold yellow",
    "GAME_RESUMED": "bold green",
    "SECRET_NOTE": "dim magenta",
    "SCENARIO_EVENT": "dim",
    "YIELD": "dim",
    "narration.delta": "white",
}

# ── Message rendering ───────────────────────────────────────────────────────


def render_message(msg: dict) -> None:
    """Render a GameMessage to the console with color coding."""
    # NarrationDelta and a handful of other side-channel messages use
    # ``kind`` instead of ``type`` (they sit outside the GameMessage
    # discriminated union — see protocol/messages.py NarrationDelta).
    msg_type = msg.get("type") or msg.get("kind", "UNKNOWN")
    payload = msg.get("payload", {}) or {}
    style = MSG_STYLES.get(msg_type, "white")

    if msg_type == "narration.delta":
        chunk = payload.get("chunk", "")
        # Stream chunks inline so the trace reads like the narrator typing.
        console.print(chunk, end="", style="white")
        return

    if msg_type == "NARRATION":
        text = payload.get("text", "")
        console.print()
        console.print(Text(text, style="white"), width=80)
        delta = payload.get("state_delta")
        if delta:
            console.print(f"  [dim][STATE] {json.dumps(delta, indent=None)}[/dim]")
        footnotes = payload.get("footnotes", []) or []
        for fn in footnotes:
            marker = fn.get("marker", "?")
            summary = fn.get("summary", "")
            cat = fn.get("category", "")
            new = " NEW" if fn.get("is_new") else ""
            console.print(f"  [dim][{marker}] {cat}{new}: {summary}[/dim]")

    elif msg_type == "NARRATION_END":
        delta = payload.get("state_delta")
        if delta:
            console.print(f"  [dim][STATE] {json.dumps(delta, indent=None)}[/dim]")

    elif msg_type == "THINKING":
        console.print("[dim]...[/dim]", end="")

    elif msg_type == "SESSION_EVENT":
        event = payload.get("event", "")
        console.print(f"[{style}][SESSION] {event}[/{style}]")
        if event == "connected":
            has_char = payload.get("has_character", False)
            console.print(f"  has_character: {has_char}")
        elif event == "ready":
            state = payload.get("initial_state", {}) or {}
            loc = state.get("location", "unknown")
            console.print(f"  location: {loc}")

    elif msg_type == "CHARACTER_CREATION":
        phase = payload.get("phase", "")
        scene = payload.get("scene_index", "?")
        total = payload.get("total_scenes", "?")
        prompt_text = payload.get("prompt", "")
        choices = payload.get("choices") or []
        console.print(f"[{style}][CHARGEN] phase={phase} ({scene}/{total})[/{style}]")
        if prompt_text:
            console.print(f"  {prompt_text}")
        for i, c in enumerate(choices):
            label = c.get("label", "?") if isinstance(c, dict) else str(c)
            console.print(f"  [{i + 1}] {label}")
        if payload.get("pool") is not None:
            console.print(f"  pool={payload.get('pool')} assignment={payload.get('assignment')}")
        if payload.get("character"):
            console.print("  [bold green]Character created![/bold green]")

    elif msg_type == "IMAGE":
        url = payload.get("image_url", "")
        tier = payload.get("tier", "")
        gen_ms = payload.get("generation_ms", 0)
        console.print(f"[{style}][RENDER] {tier} — {url} ({gen_ms}ms)[/{style}]")

    elif msg_type == "RENDER_QUEUED":
        tier = payload.get("tier", "?")
        console.print(f"[{style}][RENDER_QUEUED] tier={tier}[/{style}]")

    elif msg_type == "AUDIO_CUE":
        mood = payload.get("mood", "")
        track = payload.get("track", "")
        console.print(f"[{style}][AUDIO] mood={mood} track={track}[/{style}]")

    elif msg_type == "COMBAT_EVENT":
        console.print(f"[{style}][COMBAT] {json.dumps(payload, indent=None)}[/{style}]")

    elif msg_type == "DICE_REQUEST":
        rid = payload.get("request_id", "?")
        char = payload.get("character_name", "?")
        dc = payload.get("difficulty", "?")
        stat = payload.get("stat", "?")
        ctx = payload.get("context", "")
        console.print(f"[{style}][DICE_REQ] {char} {stat} DC{dc} req={rid} :: {ctx}[/{style}]")

    elif msg_type == "DICE_RESULT":
        char = payload.get("character_name", "?")
        total = payload.get("total", "?")
        dc = payload.get("difficulty", "?")
        outcome = payload.get("outcome", "?")
        console.print(f"[{style}][DICE_RES] {char} total={total} vs DC{dc} → {outcome}[/{style}]")

    elif msg_type == "DICE_THROW":
        rid = payload.get("request_id", "?")
        face = payload.get("face", [])
        console.print(f"[dim][DICE_THROW] req={rid} face={face}[/dim]")

    elif msg_type == "BEAT_SELECTION":
        beats = payload.get("beats", []) or payload.get("options", [])
        console.print(f"[{style}][BEAT_SEL] {len(beats)} option(s)[/{style}]")
        for i, b in enumerate(beats[:4]):
            label = b.get("label") or b.get("name") or b.get("id") if isinstance(b, dict) else str(b)
            console.print(f"    [{i + 1}] {label}")

    elif msg_type == "CONFRONTATION":
        cid = payload.get("confrontation_id") or payload.get("id", "?")
        state = payload.get("state", "?")
        console.print(f"[{style}][CONFRONTATION] {cid} state={state}[/{style}]")

    elif msg_type == "CONFRONTATION_OUTCOME":
        cid = payload.get("confrontation_id") or payload.get("id", "?")
        branch = payload.get("branch") or payload.get("resolution", "?")
        console.print(f"[{style}][CONFRONTATION_OUTCOME] {cid} → {branch}[/{style}]")
        outputs = payload.get("mandatory_outputs") or []
        for o in outputs:
            console.print(f"    [dim]• {o}[/dim]")

    elif msg_type == "JOURNAL_RESPONSE":
        entries = payload.get("entries", []) or []
        console.print(f"[{style}][JOURNAL] {len(entries)} entries[/{style}]")

    elif msg_type == "INVENTORY":
        items = payload.get("items", []) or []
        gold = payload.get("gold", 0)
        console.print(f"[{style}][INVENTORY] {len(items)} items, {gold} gold[/{style}]")
        for item in items[:5]:
            name = item.get("name", "???")
            console.print(f"  - {name}")
        if len(items) > 5:
            console.print(f"  ... and {len(items) - 5} more")

    elif msg_type == "ITEM_DEPLETED":
        name = payload.get("item_name") or payload.get("name", "?")
        console.print(f"[{style}][ITEM_DEPLETED] {name}[/{style}]")

    elif msg_type == "RESOURCE_MIN_REACHED":
        res = payload.get("resource", "?")
        console.print(f"[{style}][RESOURCE_MIN] {res}[/{style}]")

    elif msg_type == "MAP_UPDATE":
        loc = payload.get("current_location", "")
        regions = payload.get("explored_locations", []) or []
        console.print(f"[{style}][MAP] {loc} ({len(regions)} explored)[/{style}]")

    elif msg_type == "TACTICAL_STATE":
        actors = payload.get("actors", []) or []
        console.print(f"[{style}][TAC_STATE] {len(actors)} actors[/{style}]")

    elif msg_type == "TACTICAL_GRID":
        loc = payload.get("location") or payload.get("room_id", "?")
        console.print(f"[{style}][TAC_GRID] {loc}[/{style}]")

    elif msg_type == "TACTICAL_ACTION":
        actor = payload.get("actor_id") or payload.get("actor", "?")
        action = payload.get("action") or payload.get("kind", "?")
        console.print(f"[{style}][TAC_ACT] {actor}: {action}[/{style}]")

    elif msg_type == "CHAPTER_MARKER":
        title = payload.get("title", "")
        console.print(f"\n[{style}]{'=' * 60}[/{style}]")
        console.print(f"[{style}]  {title}[/{style}]")
        console.print(f"[{style}]{'=' * 60}[/{style}]\n")

    elif msg_type == "TURN_STATUS":
        name = payload.get("player_name", "")
        status = payload.get("status", "")
        console.print(f"[{style}][TURN] {name}: {status}[/{style}]")

    elif msg_type == "PARTY_STATUS":
        members = payload.get("members", []) or []
        names = [m.get("name", "?") for m in members]
        console.print(f"[{style}][PARTY] {', '.join(names)}[/{style}]")

    elif msg_type == "ACTION_QUEUE":
        items = payload.get("queue") or payload.get("actions") or []
        console.print(f"[{style}][ACTION_QUEUE] {len(items)} queued[/{style}]")

    elif msg_type == "ACTION_REVEAL":
        char = payload.get("character_name", "?")
        status = payload.get("status", "?")
        text = (payload.get("action_text") or "")[:60]
        console.print(f"[{style}][REVEAL] {char} {status}: {text}[/{style}]")

    elif msg_type == "PLAYER_PRESENCE":
        members = payload.get("players") or payload.get("members") or []
        console.print(f"[{style}][PRESENCE] {len(members)} player(s)[/{style}]")

    elif msg_type in ("PLAYER_SEAT", "SEAT_CONFIRMED"):
        console.print(f"[{style}][{msg_type}] {json.dumps(payload, indent=None)}[/{style}]")

    elif msg_type == "GAME_PAUSED":
        reason = payload.get("reason", "?")
        console.print(f"[{style}][GAME_PAUSED] {reason}[/{style}]")

    elif msg_type == "GAME_RESUMED":
        console.print(f"[{style}][GAME_RESUMED][/{style}]")

    elif msg_type == "ACHIEVEMENT_EARNED":
        name = payload.get("name") or payload.get("achievement_id", "?")
        console.print(f"[{style}][ACHIEVEMENT] {name}[/{style}]")

    elif msg_type in ("VOICE_SIGNAL", "VOICE_TEXT"):
        kind = payload.get("kind") or payload.get("event", "")
        console.print(f"[{style}][{msg_type}] {kind}[/{style}]")

    elif msg_type == "SCRAPBOOK_ENTRY":
        turn = payload.get("turn_id", "?")
        console.print(f"[{style}][SCRAPBOOK] turn={turn}[/{style}]")

    elif msg_type == "SECRET_NOTE":
        sub = payload.get("subsystem", "?")
        console.print(f"[{style}][SECRET_NOTE] {sub}[/{style}]")

    elif msg_type == "SCENARIO_EVENT":
        ev = payload.get("event") or payload.get("kind", "?")
        console.print(f"[{style}][SCENARIO] {ev}[/{style}]")

    elif msg_type == "ERROR":
        error = payload.get("message", payload.get("error", str(payload)))
        console.print(f"[{style}][ERROR] {error}[/{style}]")

    elif msg_type == "YIELD":
        console.print(f"[{style}][YIELD][/{style}]")

    else:
        console.print(f"[dim][{msg_type}] {json.dumps(payload, indent=None)[:120]}[/dim]")


# ── Outbound message construction ──────────────────────────────────────────


def make_slug_connect_msg(game_slug: str, player_name: str, last_seen_seq: int = 0) -> dict:
    """SESSION_EVENT{connect} for the slug-keyed handshake (post-Story 45-26)."""
    return {
        "type": "SESSION_EVENT",
        "payload": {
            "event": "connect",
            "game_slug": game_slug,
            "player_name": player_name,
            "last_seen_seq": last_seen_seq,
        },
        "player_id": "",
    }


def make_action_msg(action: str, aside: bool = False, round_: int = 0) -> dict:
    # ``round`` is required by PlayerActionPayload (Story 71-10, ge=0): a
    # missing round fails loud server-side rather than silently defaulting.
    # The server validates but does not read it (it stamps outbound rounds
    # from the authoritative turn_manager.round), so the driver sends its
    # best-known round, latched from inbound traffic.
    return {
        "type": "PLAYER_ACTION",
        "payload": {"action": action, "aside": aside, "round": round_},
        "player_id": "",
    }


def make_chargen_scene_choice(index_1_based: int) -> dict:
    """Pick the Nth choice on a chargen ``scene`` message (1-based)."""
    return {
        "type": "CHARACTER_CREATION",
        "payload": {"phase": "scene", "choice": str(index_1_based)},
        "player_id": "",
    }


def make_chargen_freeform(text: str) -> dict:
    """Scene with freeform input (input_type='text', allows_freeform)."""
    return {
        "type": "CHARACTER_CREATION",
        "payload": {"phase": "scene", "choice": text},
        "player_id": "",
    }


def make_chargen_confirm() -> dict:
    """Accept the chargen confirmation summary."""
    return {
        "type": "CHARACTER_CREATION",
        "payload": {"phase": "confirmation", "choice": "1"},
        "player_id": "",
    }


def make_chargen_continue() -> dict:
    return {
        "type": "CHARACTER_CREATION",
        "payload": {"phase": "continue"},
        "player_id": "",
    }


def make_chargen_portrait_confirm(selected_portrait_ref: str | None = None) -> dict:
    """Answer the Epic-66 ``pick_portrait`` frame (phase=portrait_confirm).

    The headless driver always SKIPS the portrait step — portraits are
    cosmetic and an invented slug would trip the server's unknown-ref warning.
    A skip is ``selected_portrait_ref=None``. Without this the driver would
    fall through to a generic ``continue``, the server never clears
    ``portrait_step_shown``, and the next action raises WrongPhaseError.
    """
    return {
        "type": "CHARACTER_CREATION",
        "payload": {"phase": "portrait_confirm", "selected_portrait_ref": selected_portrait_ref},
        "player_id": "",
    }


def make_arrange_assign(stat: str, value: int) -> dict:
    return {
        "type": "CHARACTER_CREATION",
        "payload": {"phase": "arrange_assign", "stat": stat, "value": value},
        "player_id": "",
    }


def make_arrange_confirm() -> dict:
    return {
        "type": "CHARACTER_CREATION",
        "payload": {"phase": "arrange_confirm"},
        "player_id": "",
    }


def make_story_autogen() -> dict:
    return {
        "type": "CHARACTER_CREATION",
        "payload": {"phase": "story_autogen"},
        "player_id": "",
    }


def make_story_confirm(pronouns: str, background: str, description: str) -> dict:
    return {
        "type": "CHARACTER_CREATION",
        "payload": {
            "phase": "story_confirm",
            "pronouns": pronouns,
            "background": background,
            "description": description,
        },
        "player_id": "",
    }


def make_dice_throw(request_id: str, faces: list[int], throw_params: dict | None = None) -> dict:
    """Auto-throw response to a DICE_REQUEST.

    ``throw_params`` mirrors the rolling client's physics-throw params; for
    headless playtest we synthesize a minimal record. ``faces`` is the rolled
    face value per die — the server treats these as authoritative.
    """
    return {
        "type": "DICE_THROW",
        "payload": {
            "request_id": request_id,
            "face": list(faces),
            "throw_params": throw_params or {
                "seed": 0,
                "power": 0.0,
                "angle": 0.0,
            },
        },
        "player_id": "",
    }


def make_yield() -> dict:
    """End-of-turn yield so the room advances under ADR-036 turn coordination."""
    return {"type": "YIELD", "payload": {}, "player_id": ""}
