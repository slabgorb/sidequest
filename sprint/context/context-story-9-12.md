---
parent: context-epic-9.md
---

# Story 9-12: Footnote Rendering in Narration View

## Business Context

When the narrator emits footnotes (story 9-11), the player should see them contextually
in the narration view. Superscript markers appear inline with prose text, and footnote
entries render at the bottom of each narration block — like marginalia in a medieval
manuscript. New discoveries are visually distinct from callbacks to prior knowledge,
giving the player an intuitive sense of what's fresh information vs continuity.

This is the **presentation layer** of the living journal system. The footnotes exist
in structured data (9-11); this story makes them visible.

**Depends on:** Story 9-11 (structured footnote output)

## Technical Approach

### GameMessage Extension

Extend `GameMessage::Narration` in `sidequest-protocol` to carry footnote data to the
client. The `NarrationPayload` from 9-11 flows through the WebSocket as-is.

```rust
// In sidequest-protocol
pub struct NarrationMessage {
    pub prose: String,
    pub footnotes: Vec<FootnoteMessage>,
}

pub struct FootnoteMessage {
    pub marker: u32,
    pub summary: String,
    pub category: String,
    pub is_new: bool,
}
```

### React UI Rendering

In `sidequest-ui`, the narration component:

1. **Parses markers:** Scans prose for `[N]` patterns, replaces with superscript elements
2. **Renders footnote block:** Below the narration prose, a footnote section appears:
   ```
   ─────
   [1] 📖 The Corrupted Grove — corruption detected in the oldest tree (New)
   [2] ↩ The Northern Gate Sigil — first seen at the gate entrance (Turn 4)
   ```
3. **Styles by type:** New discoveries get a distinct treatment (e.g., book icon, highlight).
   Callbacks get a muted treatment (e.g., return arrow, dimmed).

### Interaction

Footnotes are **read-only** in this story. No click-to-expand, no linking to journal.
That comes with 9-13 (journal browse view). Here, footnotes are simply displayed.

## Scope Boundaries

**In scope:**
- `NarrationMessage` / `FootnoteMessage` types in sidequest-protocol
- WebSocket serialization of footnote data
- React component for superscript marker rendering in prose
- React component for bottom-of-block footnote entries
- Visual distinction between new discoveries and callbacks
- Genre-appropriate footnote presentation

**Out of scope:**
- Interactive footnotes (click to expand, link to journal) — future enhancement
- Journal browse view (that's 9-13)
- Footnote creation logic (that's 9-11)
- Footnote injection into narrator prompt (that's 9-4)

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Superscript markers | `[N]` patterns in prose render as superscript elements in the narration view |
| Footnote block | Footnote entries appear below narration prose with marker, category icon, and summary |
| Discovery styling | `is_new: true` footnotes have visually distinct styling from callbacks |
| Callback styling | `is_new: false` footnotes show muted treatment with reference to original turn |
| No footnotes graceful | Narration blocks without footnotes render normally (no empty footnote section) |
| Mobile responsive | Footnote block renders correctly on mobile viewport widths |
