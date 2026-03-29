---
parent: context-epic-14.md
---

# Story 14-3: Text Length Slider — Per-Session Narrator Verbosity Control

## Business Context

Solo play benefits from rich, detailed narration. Multiplayer sessions need tighter prose
because players are reading while waiting for each other. A per-session verbosity control
lets the DM/host tune this for the group.

**Playtest evidence:** "The players found it difficult to keep up with the text... I enjoy
the longer text when I'm playing solo sessions. But when we're playing group sessions,
the text tends to be long."

## Technical Approach

### Three Verbosity Levels

| Level | Narrator Instruction | Target |
|-------|---------------------|--------|
| Concise | "Keep narration to 2-3 sentences. Focus on actions and outcomes. No atmospheric filler." | Multiplayer default |
| Standard | "Narrate in moderate detail. 4-6 sentences. Balance action with atmosphere." | — |
| Verbose | "Rich, immersive narration. Full sensory detail, atmosphere, and character interiority." | Solo default |

### Server-Side

- Add `narrator_verbosity: NarratorVerbosity` to `SharedGameSession` settings
- Inject verbosity instruction into narrator system prompt via prompt composer
- Default: `Concise` when 2+ players, `Verbose` when solo
- DM can change mid-session via settings

### Protocol

```rust
// Client → Server
SessionSettings {
    narrator_verbosity: Option<String>,  // "concise" | "standard" | "verbose"
    // ... other settings from 14-4
}
```

### UI: Settings Panel

Slider or segmented control in session settings:
`Concise ──●── Standard ────── Verbose`

Changes take effect on the next narrator response (no retroactive rewrite).

## Scope Boundaries

**In scope:**
- Three-level verbosity setting
- Narrator prompt injection
- Session settings message
- UI slider
- Smart defaults (solo vs multiplayer)

**Out of scope:**
- Per-player verbosity preferences
- Retroactive rewriting of previous narration
- Token-count-based control (use descriptive levels, not numbers)

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Three levels | Concise, Standard, Verbose each produce distinct narration length |
| Prompt injected | Verbosity instruction present in narrator system prompt |
| Default smart | Multiplayer defaults to Concise, solo to Verbose |
| UI control | Slider accessible in session settings |
| Mid-session | Changing setting affects next response, not retroactive |
| Persisted | Setting survives reconnect within same session |
