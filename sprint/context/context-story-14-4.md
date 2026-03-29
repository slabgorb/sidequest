---
parent: context-epic-14.md
---

# Story 14-4: Vocabulary Level Slider — Narrator Prose Complexity Control

## Business Context

Separate from length. The narrator's vocabulary is highly literary — great for Keith, too
much for casual players. A vocabulary control adjusts prose complexity without affecting
length.

**Playtest evidence:** "The language tends to be rather erudite. Which, of course, I love...
But we need to tone it down for people who are not as literary."

## Technical Approach

### Three Vocabulary Levels

| Level | Narrator Instruction | Approx. Grade |
|-------|---------------------|---------------|
| Accessible | "Use clear, everyday language. Short sentences. Avoid archaic or obscure words. Aim for an 8th-grade reading level." | 8th grade |
| Literary | "Moderate literary prose. Varied sentence structure. Vocabulary accessible to adult readers." | College |
| Epic | "Full literary range. Archaic, poetic, and elaborate language are welcome. Elevate the prose." | Unrestricted |

### Server-Side

- Add `narrator_vocabulary: NarratorVocabulary` to `SharedGameSession` settings
- Inject alongside verbosity instruction in narrator system prompt
- Default: `Accessible` for multiplayer, `Epic` for solo
- Both vocabulary and verbosity compose independently in the prompt

### Combined Prompt Example

```
[Verbosity: Concise] Keep narration to 2-3 sentences. Focus on actions and outcomes.
[Vocabulary: Accessible] Use clear, everyday language. Avoid archaic or obscure words.
```

### UI

Slider in session settings alongside verbosity:
```
Verbosity:  Concise ──●── Standard ────── Verbose
Vocabulary: Accessible ──●── Literary ────── Epic
```

## Scope Boundaries

**In scope:**
- Three-level vocabulary setting
- Narrator prompt injection (composes with verbosity)
- Session settings message (shares with 14-3)
- UI slider

**Out of scope:**
- Per-player vocabulary preferences
- Genre-specific vocabulary defaults (all genres use same levels)
- Automated readability scoring of output

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Three levels | Accessible, Literary, Epic produce distinct prose styles |
| Independent | Vocabulary and verbosity settings are orthogonal |
| Prompt injected | Vocabulary instruction in narrator system prompt |
| Default smart | Multiplayer defaults to Accessible, solo to Epic |
| UI control | Slider in session settings |
| Combined | Both settings compose cleanly in the prompt |
