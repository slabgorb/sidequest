# Epic 66: Character Creation Depth

## Overview

Make character creation produce **mechanically differentiated, correct, and
legible** characters — not cosmetically distinct ones that collapse to the same
statline under the hood. The epic covers differentiated stat bonuses on chargen
choices, the signature-ability mechanical surface per class (ADR-095/097), a
correctness fix to the names step that currently stores whole prose sentences as
the character name, and a confirmation sheet that shows resolved race/class
instead of raw funnel labels. The throughline is the **player-facing crunch
Sebastien (and Jade) expect** — chargen choices must visibly change the numbers.

**Priority:** P2
**Repo:** server, content
**Stories:** 5 (18 points) — all backlog

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| **ADR-095 — Daemon Music Tier / signature abilities** (`docs/adr/095-*.md`) | Signature-ability authoring referenced by 66-2 (class moves for mutant_wasteland) |
| **ADR-097 — Class Mechanical Surface** (`docs/adr/097-*.md`) | "One signature ability per non-magical class" — the contract 66-4 authors for wry_whimsy |
| **ADR-016 — Three-Mode Character Creation** (`docs/adr/016-*.md`) | The chargen funnel/state-machine whose steps 66-1/66-3/66-5 touch |
| **ADR-015 — Character Builder State Machine** (`docs/adr/015-*.md`) | Step ordering and the names step (66-3) |
| **ADR-007 — Unified Character Model** (`docs/adr/007-*.md`) | Where `stat_bonuses`, race/class, and the resolved statline live |
| **Playtest 2026-05-25 (mutant_wasteland/flickering_reach)** | The session that surfaced flat statlines, prose-as-name, and raw-label confirmation findings |
| **Who-This-Is-For (CLAUDE.md)** | Sebastien/Jade mechanics-first — the player-facing math must be visible in chargen surfaces |

## Background

This epic was spun out of the **2026-05-25 mutant_wasteland/flickering_reach
playtest**, which exposed that chargen *choices* (race, class, mutation,
background) were largely cosmetic — characters that should differ mechanically
came out with effectively the same statline, so the mechanics-first players had
nothing to read. Three distinct correctness/depth problems clustered:

- **Flat statlines.** Chargen choices carry no thematic `stat_bonuses`, so a
  brute and a fixer roll the same numbers. 66-1 adds differentiated bonuses on
  the choices themselves.
- **No class mechanical surface.** Classes have flavor but no *signature
  ability* — the one move that makes a class feel mechanically distinct
  (ADR-097). 66-2 authors these for mutant_wasteland; 66-4 authors them for
  wry_whimsy (decision-gated, since wry_whimsy's class list itself is in flux).
- **Names-step corruption.** The names step stores the whole prose sentence the
  player typed as `char_name` instead of extracting the actual name (rider
  road-name vs rig-name confusion in road_warrior-style flows). 66-3 fixes the
  extraction.
- **Confirmation-sheet illegibility.** The creation confirmation shows *raw
  funnel labels* rather than the resolved race/class, and has no per-genre
  field-label override. 66-5 makes the sheet show what the player actually chose.

Together these make chargen deliver a character whose numbers reflect the
choices and whose summary the player can read — the crunch and legibility the
primary audience's mechanics-first players expect.

## Technical Architecture

The work spans the **chargen pipeline** (server) and **per-pack class/ability
content** (content). It is mostly additive — wiring thematic data into existing
funnel steps and authoring the class mechanical surface — plus two correctness
fixes (names extraction, confirmation rendering).

**Chargen flow touchpoints:**

```
chargen funnel (ADR-016 state machine, ADR-015)
   choice steps ──► [66-1] thematic stat_bonuses applied to the resolved statline
   names step  ──► [66-3] extract real name (rider/rig split or followup answer),
                          stop storing the whole sentence as char_name
   confirm step ──► [66-5] render RESOLVED race/class + per-genre field-label override
                          (not raw funnel labels)

class definitions (content, per pack)
   classes.yaml ──► [66-2 mutant_wasteland] ADR-095 signature abilities + class moves
                ──► [66-4 wry_whimsy] ADR-097 one signature ability per class (decision-gated)
```

**Key files (areas — verify exact paths at story start):**

| Area | Stories |
|------|---------|
| Server chargen pipeline (`sidequest/game/` chargen/character builder + `cli/`) | 66-1 (stat_bonuses application), 66-3 (names-step extraction), 66-5 (confirmation rendering + label override) |
| Unified character model (resolved statline, ADR-007) | 66-1 (where bonuses land) |
| `sidequest-content/genre_packs/mutant_wasteland/.../classes.yaml` (+ abilities) | 66-2 |
| `sidequest-content/genre_packs/wry_whimsy/.../classes.yaml` | 66-4 (decision-gated on the wry_whimsy class roster) |

**Guardrails:**
- 66-1's bonuses must surface in a **player-facing** chargen/confirmation surface
  (Sebastien/Jade see the math) — not merely computed internally. Verify the
  resolved statline reaches the UI/confirmation sheet, per "Verify Wiring, Not
  Just Existence."
- 66-2/66-4 are **content authoring** against the existing ability/class schema
  (ADR-095/097) — should not require engine changes. If authoring a class's
  signature ability needs a server change, that is a content-surface failure to
  flag (CLAUDE.md authoring-without-touching-engine-code requirement).
- 66-4 is **decision-gated**: do not author wry_whimsy classes until the class
  roster is settled, to avoid authoring abilities for classes that get cut.

## Cross-Epic Dependencies

**Depends on:**
- **ADR-095 / ADR-097** — the signature-ability and class-mechanical-surface
  contracts the content stories author against.
- **ADR-016 / ADR-015 / ADR-007** — the chargen state machine and unified
  character model the server stories modify.
- **wry_whimsy class roster** (gates 66-4) — likely intersects epic 77 / the
  wry_whimsy genre buildout.

**Depended on by:**
- **Future playtests of mutant_wasteland and wry_whimsy** — differentiated
  statlines and class moves are the crunch the mechanics-first players are
  waiting on; this epic is a direct response to their feedback.
