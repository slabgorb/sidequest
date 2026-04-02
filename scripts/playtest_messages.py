"""playtest_messages.py — Message styles, rendering, and construction helpers.

Extracted from playtest.py (story 21-1).
"""

import json

from rich.console import Console
from rich.text import Text

console = Console()

# ── Color coding by message type ────────────────────────────────────────────

MSG_STYLES = {
    "NARRATION": "white",
    "NARRATION_CHUNK": "white",
    "NARRATION_END": "dim",
    "THINKING": "dim cyan",
    "SESSION_EVENT": "bold green",
    "CHARACTER_CREATION": "bold yellow",
    "TURN_STATUS": "cyan",
    "PARTY_STATUS": "cyan",
    "COMBAT_EVENT": "bold red",
    "IMAGE": "magenta",
    "AUDIO_CUE": "blue",
    "INVENTORY": "yellow",
    "MAP_UPDATE": "green",
    "CHARACTER_SHEET": "yellow",
    "CHAPTER_MARKER": "bold magenta",
    "ERROR": "bold red",
    "TTS_START": "dim",
    "TTS_CHUNK": "dim",
    "TTS_END": "dim",
}

# ── Message rendering ───────────────────────────────────────────────────────


def render_message(msg: dict) -> None:
    """Render a GameMessage to the console with color coding."""
    msg_type = msg.get("type", "UNKNOWN")
    payload = msg.get("payload", {})
    style = MSG_STYLES.get(msg_type, "white")

    if msg_type == "NARRATION":
        text = payload.get("text", "")
        console.print()
        console.print(Text(text, style="white"), width=80)
        delta = payload.get("state_delta")
        if delta:
            console.print(f"  [dim][STATE] {json.dumps(delta, indent=None)}[/dim]")
        footnotes = payload.get("footnotes", [])
        for fn in footnotes:
            marker = fn.get("marker", "?")
            summary = fn.get("summary", "")
            cat = fn.get("category", "")
            new = " NEW" if fn.get("is_new") else ""
            console.print(f"  [dim][{marker}] {cat}{new}: {summary}[/dim]")

    elif msg_type == "NARRATION_CHUNK":
        text = payload.get("text", "")
        console.print(text, end="", style="white")

    elif msg_type == "NARRATION_END":
        console.print()
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
            state = payload.get("initial_state", {})
            loc = state.get("location", "unknown")
            console.print(f"  location: {loc}")

    elif msg_type == "CHARACTER_CREATION":
        phase = payload.get("phase", "")
        scene = payload.get("scene_index", "?")
        total = payload.get("total_scenes", "?")
        prompt_text = payload.get("prompt", "")
        choices = payload.get("choices", [])
        console.print(f"[{style}][CHARGEN] phase={phase} ({scene}/{total})[/{style}]")
        if prompt_text:
            console.print(f"  {prompt_text}")
        if choices:
            for i, c in enumerate(choices):
                label = c.get("label", c) if isinstance(c, dict) else c
                console.print(f"  [{i + 1}] {label}")
        if payload.get("character"):
            console.print(f"  [bold green]Character created![/bold green]")

    elif msg_type == "IMAGE":
        url = payload.get("image_url", "")
        tier = payload.get("tier", "")
        gen_ms = payload.get("generation_ms", 0)
        console.print(
            f"[{style}][RENDER] {tier} — {url} ({gen_ms}ms)[/{style}]"
        )

    elif msg_type == "AUDIO_CUE":
        mood = payload.get("mood", "")
        track = payload.get("track", "")
        console.print(f"[{style}][AUDIO] mood={mood} track={track}[/{style}]")

    elif msg_type == "COMBAT_EVENT":
        console.print(f"[{style}][COMBAT] {json.dumps(payload, indent=None)}[/{style}]")

    elif msg_type == "INVENTORY":
        items = payload.get("items", [])
        gold = payload.get("gold", 0)
        console.print(f"[{style}][INVENTORY] {len(items)} items, {gold} gold[/{style}]")
        for item in items[:5]:
            name = item.get("name", "???")
            console.print(f"  - {name}")
        if len(items) > 5:
            console.print(f"  ... and {len(items) - 5} more")

    elif msg_type == "MAP_UPDATE":
        loc = payload.get("current_location", "")
        regions = payload.get("explored_locations", [])
        console.print(f"[{style}][MAP] {loc} ({len(regions)} explored)[/{style}]")

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
        members = payload.get("members", [])
        names = [m.get("name", "?") for m in members]
        console.print(f"[{style}][PARTY] {', '.join(names)}[/{style}]")

    elif msg_type == "ERROR":
        error = payload.get("message", payload.get("error", str(payload)))
        console.print(f"[{style}][ERROR] {error}[/{style}]")

    elif msg_type in ("TTS_START", "TTS_CHUNK", "TTS_END"):
        pass  # Silently skip TTS in headless mode

    else:
        console.print(f"[dim][{msg_type}] {json.dumps(payload, indent=None)}[/dim]")


# ── Session connect message ─────────────────────────────────────────────────


def make_connect_msg(genre: str, world: str, player_name: str) -> dict:
    return {
        "type": "SESSION_EVENT",
        "payload": {
            "event": "connect",
            "genre": genre,
            "world": world,
            "player_name": player_name,
        },
        "player_id": "",
    }


def make_action_msg(action: str) -> dict:
    return {
        "type": "PLAYER_ACTION",
        "payload": {"action": action, "aside": False},
        "player_id": "",
    }


def make_chargen_choice(choice: str) -> dict:
    return {
        "type": "CHARACTER_CREATION",
        "payload": {"phase": "scene", "choice": choice},
        "player_id": "",
    }


def make_chargen_confirm() -> dict:
    return {
        "type": "CHARACTER_CREATION",
        "payload": {"phase": "confirmation", "choice": "yes"},
        "player_id": "",
    }

