---
parent: context-epic-14.md
---

# Story 14-9: Footnote Inline References

## Business Context

The narrator emits footnotes that display below narration text, but they're not connected
to the text with numbered references. Players see footnotes but don't know which part of
the text they relate to.

**Playtest evidence:** "The footnotes are displaying below the text but are not connected
to the text with a number."

## Technical Approach

### Current State

Narrator text includes footnote markers (likely `[1]`, `[^1]`, or similar markdown
convention). The UI renders a footnote section below the narration block. But the inline
markers aren't parsed and linked.

### Fix

1. **Parse**: Scan narration text for footnote marker patterns
2. **Render inline**: Replace markers with superscript numbered links (`<sup><a href="#fn-1">1</a></sup>`)
3. **Render footnotes**: Add `id="fn-1"` anchors to each footnote entry
4. **Click behavior**: Clicking inline reference scrolls to footnote; clicking footnote
   back-reference scrolls to inline position

### Implementation

This is a UI rendering fix in whatever component handles narration text display. Check
whether narration uses markdown rendering (likely) — if so, this may be a matter of
configuring the markdown renderer's footnote plugin correctly.

## Scope Boundaries

**In scope:**
- Parse footnote markers in narration text
- Render as clickable superscript links
- Anchor footnotes below text
- Bidirectional scroll (inline ↔ footnote)

**Out of scope:**
- Changing how the narrator generates footnotes
- Footnote styling/theming
- Footnote persistence across narration blocks

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Markers parsed | Footnote markers in text rendered as superscript numbers |
| Clickable | Clicking inline number scrolls to corresponding footnote |
| Back-reference | Footnote has link back to inline position |
| Multiple | Handles 1-N footnotes per narration block |
| No raw markers | Original marker syntax not visible to player |
