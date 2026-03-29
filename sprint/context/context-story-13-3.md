---
parent: context-epic-13.md
---

# Story 13-3: Action Reveal Broadcast — Show Each Player's Action to the Full Party

## Business Context

Players can't understand what triggered a narrator response because they never see each
other's submitted actions. The sealed letter reveal moment is both functional (context) and
dramatic (the "opening of the letters").

**Playtest evidence:** "Players have trouble figuring out what the other player is doing to
elicit the prompt that the other player got."

**Depends on:** 13-2 (actions must be collected before they can be revealed)

## Technical Approach

### New Protocol Message: ACTION_REVEAL

```rust
// In sidequest-protocol/src/message.rs
ActionReveal {
    actions: Vec<PlayerActionEntry>,
    turn_number: u64,
    auto_resolved: Vec<String>,  // character names that timed out
}

pub struct PlayerActionEntry {
    pub character_name: String,
    pub action: String,
}
```

### Server-Side: Broadcast After Barrier Resolution

In the barrier resolution path (modified in 13-2):
```
barrier met → broadcast ACTION_REVEAL → orchestrator.process_turn() → narration
```

The reveal happens BEFORE narration starts, so players read what everyone did, then see
the narrator's response to all actions together.

### UI Component: ActionRevealBlock

Renders between the turn status panel and the narrator response:

```
┌─────────────────────────────────┐
│ ⚔ Turn 3 Actions                │
│                                 │
│ Thane: "I search the cart"      │
│ Lyra: "I keep watch for guards" │
│ Brak: waited (auto-resolved)    │
└─────────────────────────────────┘
```

- Brief, compact rendering — one line per character
- Auto-resolved actions shown with "waited" or similar indicator
- Visually distinct from narrator text (different background, smaller font)
- Scrolls with the narration log, becomes part of the history

## Scope Boundaries

**In scope:**
- ACTION_REVEAL message type in protocol
- Server broadcasts ACTION_REVEAL after barrier resolution, before narration
- UI component renders action summary
- Auto-resolved players indicated

**Out of scope:**
- Editing or retracting submitted actions
- Player reactions to revealed actions
- Private/hidden actions (all actions visible to all)

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Message defined | ACTION_REVEAL in GameMessage enum with actions + turn_number |
| Timing correct | Reveal arrives BEFORE first NARRATION_CHUNK |
| All actions shown | Every player's action appears, keyed by character name |
| Auto-resolved flagged | Timed-out players shown with "waited" indicator |
| UI renders | ActionRevealBlock appears in narration log |
| Persists in history | Scrolling back through log shows reveal blocks for past turns |
