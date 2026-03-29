# Epic 14: Multiplayer Session UX — Spawn, Visibility, Text Tuning, and Chargen Polish

## Overview

Companion epic to Epic 13 (Sealed Letter Turn System). While Epic 13 fixes the core turn
mechanic, this epic addresses every other multiplayer UX issue surfaced in the 2026-03-29
playtest: players spawning on different continents, no location visibility, text too long
and erudite for group play, broken chargen back-navigation, image overload, and unlabeled
audio controls.

These are individually smaller than the turn system overhaul, but collectively they determine
whether multiplayer sessions feel polished or frustrating.

## Background

### Playtest Evidence (2026-03-29)

**Spawn/co-location:**
> "People would spawn in their faction starting locations, which makes sense, but that leaves
> them on basically different continents starting the game. I ended up having to use DM tools
> to teleport them."

**Text tuning:**
> "The players found it difficult to keep up with the text. The language tends to be rather
> erudite. I enjoy the longer text solo, but we need to tone it down for group sessions."

**Character generation:**
> "Two different players reported that they made mistakes on character generation and tried
> to go back, but the system instead submitted the character as is."

**Images:**
> "The images are coming a little too much, a little too fast. Some images with extremely
> weird scenes that break immersion — dealing with a merchant and suddenly getting a huge
> mutant monster."

**Audio:**
> "The sound sliders are not labeled."

**Footnotes:**
> "The footnotes are displaying below the text but are not connected to the text with a number."

### Current Implementation

| Feature | Current State | Gap |
|---------|--------------|-----|
| **Spawn location** | Hardcoded `"Starting area"`, narrator discovers via first action | No multiplayer co-location config |
| **Player location** | Tracked internally but not in PARTY_STATUS/CHARACTER_SHEET payloads | Not visible to other players |
| **Text length** | No control, narrator defaults to literary long-form | No per-session tuning |
| **Vocabulary** | No control, narrator uses full literary range | No accessibility adjustment |
| **Chargen flow** | Linear state machine, no back navigation | Confirmation = immediate submit |
| **Image pacing** | Generated on narrator triggers, no throttle | Can flood during rapid turns |
| **Image relevance** | Art prompt from scene interpreter, no validation | Subject mismatch possible |
| **Sound sliders** | Functional but unlabeled | Players don't know what they control |
| **Footnotes** | Rendered below text | No inline numbered references |

## Technical Architecture

### Party Co-Location (14-1)

```yaml
# In world YAML (e.g., genre_packs/elemental_worlds/worlds/shattered_accord/world.yaml)
session_start:
  multiplayer_location: "The Crossroads Tavern"
  solo_location: null  # null = use faction start
```

Server logic in `dispatch_connect()`:
- If session has 2+ players (or is configured as multiplayer): use `multiplayer_location`
- If solo: use faction start or narrator discovery as today
- DM override via `DM_COMMAND { command: "set_spawn", location: "..." }`

### Location Visibility (14-2)

Add to existing protocol payloads:

```rust
// In PARTY_STATUS member entries
pub struct PartyMember {
    // ... existing fields
    pub current_location: Option<String>,  // NEW
}

// In CHARACTER_SHEET
pub struct CharacterSheet {
    // ... existing fields
    pub current_location: Option<String>,  // NEW
}
```

UI: location displayed under character name in party panel. When players are in different
locations, a location-group divider or badge highlights the split.

### Text Tuning (14-3, 14-4)

Two independent narrator prompt injections:

**Verbosity (14-3):**
```
concise:  "Keep narration to 2-3 sentences. Focus on actions and outcomes."
standard: "Narrate in moderate detail. 4-6 sentences per response."
verbose:  "Rich, immersive narration. Full sensory detail and atmosphere."
```

**Vocabulary (14-4):**
```
accessible: "Use clear, straightforward language. 8th-grade reading level."
literary:   "Moderate literary prose. Varied vocabulary, accessible to adults."
epic:       "Full literary range. Archaic and poetic language welcome."
```

Stored as session-level settings in `SharedGameSession`. UI: two sliders in a settings
panel accessible during play. Defaults: multiplayer = standard/literary, solo = verbose/epic.

### Chargen Back Button (14-5)

Current chargen is a linear state machine in the UI:
`scene → choice → choice → ... → confirmation → submit`

Target: each step is revisitable. The confirmation screen shows a full preview with an
"Edit" button per section that navigates back to that step. Only the explicit "Create
Character" button on the confirmation screen triggers the CHARACTER_CREATION complete message.

No server changes needed — the server already accepts the final character payload. The
multi-step state is entirely client-side.

### Image Pacing (14-6) and Relevance (14-7)

**Pacing:** Simple cooldown timer on the server side. After an IMAGE message is sent,
suppress further image triggers for `image_cooldown_seconds`. Configurable per-session,
default 60s multiplayer / 30s solo. DM can force an image at any time (bypasses cooldown).

**Relevance:** Before forwarding an art prompt to the daemon, cross-reference the prompt's
subjects against the scene interpreter's current subject list (NPCs present, location
features, active entities). Reject or regenerate prompts that reference entities not in
the current scene. This prevents the "merchant scene with mutant monster" problem.

### Sound Slider Labels (14-8)

Pure UI fix. Add visible text labels to each audio slider component. Current slider
component likely uses a generic `<Slider>` — add a `label` prop and render it.

### Footnote References (14-9)

The narrator already emits footnote markers in text (likely `[1]` or similar). The UI
renders footnotes below but doesn't parse/link the inline markers. Fix: parse footnote
markers from narration text, render as `<sup>` links, scroll-to-anchor on click.

## Story Dependency Graph

```
14-1 (party co-location) ─── independent
14-2 (location on sheet) ─── independent
14-3 (text length slider) ── independent
14-4 (vocabulary slider) ─── independent
14-5 (chargen back button) ─ independent
14-6 (image cooldown) ────── independent
  │
  └──► 14-7 (image relevance filter)
14-8 (sound slider labels) ─ independent
14-9 (footnote references) ─ independent
```

Most stories are independent — high parallelism potential. Only 14-7 depends on 14-6.

## Deferred (Not in This Epic)

- **Genre theming differentiation** — Shattered Accord and Flickering Reach looking the
  same is an art prompt / visual_style issue, not a session UX issue. Tracked separately.
  (Playtest findings #9, #10)
- **Music auto-ducking for voice chat** — Needs investigation into whether this is a client
  audio mixing problem or a volume default problem. May be as simple as a lower default
  volume in multiplayer sessions.
- **Per-player text preferences** — Current design is per-session. Individual player
  overrides could come later but add complexity to prompt composition.

## Success Criteria

During a multiplayer session:
1. All players spawn at the same configured location, ready to interact immediately
2. Each player's current location is visible on the party panel
3. DM or host can adjust text length and vocabulary via sliders; changes take effect
   on the next narrator response
4. Players can navigate back during character creation and edit any choice before submitting
5. Images arrive at a reasonable pace (no flooding) and match the current scene
6. All audio sliders are clearly labeled
7. Footnote numbers in narrator text are clickable and scroll to the corresponding note
