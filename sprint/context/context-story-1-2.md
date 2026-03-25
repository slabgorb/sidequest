---
parent: context-epic-1.md
---

# Story 1-2: Protocol Crate — Full GameMessage Enum, All 23 Payload Types, Serde Round-Trips

## Business Context

Port `server/protocol.py` completely. The protocol crate is Layer 0 — every other crate
depends on it. This is not a partial implementation; all 23 message types from the API
contract get full typed payloads. The Python version uses a `GameMessage` dataclass with
an untyped `payload: dict`. The Rust version uses a tagged enum where each variant carries
its own typed payload struct — compile-time safety replaces runtime `KeyError`.

**Python source:** `sq-2/sidequest/server/protocol.py`
**API contract:** `docs/api-contract.md` (437 lines, all message types defined)

## Technical Guardrails

- **Tagged enum:** `#[serde(tag = "type")]` on `GameMessage` — matches the wire format
- **All 23 types:** PLAYER_ACTION, NARRATION, NARRATION_CHUNK, NARRATION_END, THINKING,
  TURN_STATUS, PARTY_STATUS, COMBAT_EVENT, SESSION_EVENT, CHARACTER_CREATION,
  CHARACTER_SHEET, INVENTORY, MAP_UPDATE, IMAGE, AUDIO_CUE, VOICE_SIGNAL, VOICE_TEXT,
  VOICE_AUDIO, ACTION_QUEUE, CHAPTER_MARKER, ERROR, PLAYER_ACTION_ECHO, COMBAT_PATCH
- **Port lesson #9 (newtypes):** Use `NonBlankString` for name fields, `PlayerName` or
  similar where Python had inline `if not v.strip()` validators
- **Port lesson #1 (no god objects):** Each payload is its own struct — small, focused
- **Wire compatibility:** JSON output must match `docs/api-contract.md` exactly. The React
  UI is already built against this contract
- **Input sanitization:** Port `comms/sanitize.py` — strip prompt injection, validate
  section tags. This is a protocol concern

### Python MessageType → Rust GameMessage

```python
# Python: stringly-typed enum + untyped payload dict
class MessageType(str, Enum):
    PLAYER_ACTION = "PLAYER_ACTION"
    NARRATION = "NARRATION"
    ...

@dataclass
class GameMessage:
    type: MessageType
    payload: dict        # ← untyped!
    player_id: str
```

```rust
// Rust: tagged enum with typed payloads
#[derive(Serialize, Deserialize)]
#[serde(tag = "type")]
enum GameMessage {
    #[serde(rename = "PLAYER_ACTION")]
    PlayerAction(PlayerActionPayload),
    #[serde(rename = "NARRATION")]
    Narration(NarrationPayload),
    // ... all 23
}
```

## Scope Boundaries

**In scope:**
- `GameMessage` tagged enum with all 23 variants
- Typed payload struct for every variant
- `NonBlankString` and/or `PlayerName` newtypes with validated construction
- `sanitize_player_text()` function (port of `comms/sanitize.py`)
- Serde round-trip tests for every message type
- Wire compatibility tests against `api-contract.md` examples

**Out of scope:**
- WebSocket transport (story 1-6)
- Binary frame handling for voice audio (future epic)

## AC Context

| AC | Detail |
|----|--------|
| All 23 message types | Every type from api-contract.md has a variant with typed payload |
| Serde round-trip | Every variant serializes to JSON and deserializes back correctly |
| Wire compatible | JSON matches api-contract.md format (React UI can consume it) |
| Newtypes | NonBlankString (or equivalent) used for validated string fields |
| Input sanitization | sanitize_player_text() strips injection attempts |
| deny_unknown_fields | Payloads reject unexpected JSON keys |
