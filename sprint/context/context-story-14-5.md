---
parent: context-epic-14.md
---

# Story 14-5: Character Generation Back Button

## Business Context

Two independent players hit the same bug: they made a mistake during character creation
and tried to go back, but the system submitted the character instead. Character creation
needs to be non-destructive until explicit confirmation.

**Playtest evidence:** "Two different players reported that they made mistakes on character
generation and tried to go back, but the system instead submitted the character as is."

## Technical Approach

### Current Flow (broken)

```
Scene → Choice 1 → Choice 2 → ... → Confirmation → SUBMIT (immediate, no review)
```

The confirmation step currently triggers submission. There's no way to navigate back.

### Target Flow

```
Scene → Choice 1 → Choice 2 → ... → Review Screen → "Create Character" → SUBMIT
                ↑       ↑                  │
                └───────┴──── "Edit" ──────┘
```

### UI State Machine

All chargen state is client-side. The server only sees the final CHARACTER_CREATION
complete message with the finished character payload.

```typescript
interface ChargenState {
  steps: ChargenStep[];      // ordered list of completed steps
  currentStep: number;       // index into steps
  isReviewing: boolean;      // true when on review screen
}

// Navigate back: set currentStep = target, isReviewing = false
// Navigate to review: set isReviewing = true (can go back from here)
// Submit: only from review screen via explicit button
```

### Review Screen

Shows all choices made:
- Name, class, faction, appearance, etc.
- "Edit" button per section → navigates to that step
- "Create Character" button → sends CHARACTER_CREATION complete
- No other path triggers submission

### No Server Changes

The server's character creation handler already accepts the final payload. The multi-step
wizard is entirely client-side state. This is a pure UI fix.

## Scope Boundaries

**In scope:**
- Back navigation between chargen steps
- Review screen showing all choices
- Per-section edit from review
- Explicit "Create Character" submit button
- No accidental submission

**Out of scope:**
- Saving partial chargen state for later
- Editing characters after creation
- Server-side chargen validation changes

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Back works | Player can navigate to any previous step |
| Review shows all | Review screen displays every choice made |
| Edit from review | Each section has an "Edit" button returning to that step |
| No accidental submit | Only the "Create Character" button on review triggers submission |
| State preserved | Going back preserves later choices (unless the edited step invalidates them) |
| Server unchanged | CHARACTER_CREATION complete message format identical to current |
