# Epic 56: Playgroup QoL Wave 1

## Overview

A small, ongoing epic that holds quality-of-life papercuts surfaced directly by the play table — Sebastien, Alex, James, and (occasionally) Sonia. Stories here are not roadmap features; they are the fast-feedback channel for "this little thing bothered us last session." Each story is intended to be cheap, ship-shaped, and tightly scoped — the epic exists so playgroup signal doesn't queue behind larger architecture work.

**Priority:** P1
**Repo:** ui (other repos possible if a single QoL story crosses the seam)
**Stories:** 1 (2 points)

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| `CLAUDE.md` (project root) | "Who This Is For" — names the playgroup and the design rubric. The audience model is the spec for what counts as a "papercut worth fixing." |
| `SOUL.md` (in CLAUDE.md) | "Tabletop First, Then Better" — these stories are where the *better* lives. |

There is intentionally no PRD or ADR backing this epic. The trigger for each story is a single, verbatim ask from a real human at the table; the spec is the ask itself plus the SP/MP / audience constraints captured in agent memory.

## Background

SideQuest is built for the playgroup first (`CLAUDE.md` "Who This Is For"). The playgroup gives feedback in the most valuable form possible: live, at the table, while their hands are still on the cards. That feedback often takes the shape of small interface frictions — "I can't tell whose character is whose at a glance," "the wait is awkward when Alex is typing," "Sebastien wants to see the dice math" — none of which are big enough to deserve their own epic, all of which compound into "the game feels finished or unfinished."

Without a dedicated home, these asks either (a) get bolted onto unrelated technical stories where the scope warps to fit them, (b) get filed in a generic "polish" bucket that never gets pulled, or (c) get carried verbally by Keith and lost. This epic is the channel that prevents all three.

**Submitting a story to this epic implies:**
- The trigger was a real playgroup statement, not Keith's solo intuition (those go elsewhere).
- The fix is contained — typically a single repo, single screen, one or two components.
- The work is shippable inside Kanban flow without specialist tandem unless the story specifically needs it.
- The story carries the verbatim source ask in its context.

**Wave 1** captures the first batch surfaced after Playtest 3. Future waves (54, 55, …) follow the same pattern as new asks arrive.

## Technical Architecture

This epic deliberately has no architecture of its own — each story uses the architecture of the surface it touches. The architecture statement for an individual story is "respect the existing patterns in the component you are editing; do not introduce new abstractions to satisfy a 1-component change."

What every story in this epic IS expected to share:

- **SP/MP awareness.** Most playgroup asks come from MP sessions because that is where social friction lives. Any feature that displays inter-player information must gate on the multiplayer-ness of the current session (see [the SP/MP project memory](../../.claude/projects/-Users-slabgorb-Projects-oq-1/memory/project_no_player_name_in_sp.md) — single-player surfaces must not render player-disambiguation chrome).
- **Audience-axis sanity.** Before shipping, sanity-check the change against the four audience axes in `CLAUDE.md`: would Alex feel rushed? Would Sebastien lose mechanical visibility? Would Sonia hit a wall? Would Keith-as-player feel improved? A story that improves one axis must not regress another.
- **No new protocol fields unless absolutely required.** Most playgroup papercuts can be served by data already on the wire — the gap is almost always render-side. Stories that require a new server payload field should explicitly justify why an existing field cannot be reused.
- **Test coverage matches the gate.** If the story has an SP/MP gate, both branches need tests. If it has an NPC vs PC gate, both branches need tests. A papercut fix without coverage of its own gate is a future regression waiting to happen.

### Wave 1 surfaces

The Wave 1 story (56-1) touches three character-display components:

| Component | File | Role |
|-----------|------|------|
| `CharacterPanel.tsx` | `sidequest-ui/src/components/CharacterPanel.tsx` | Always-visible party rail — load-bearing for Alex (at-a-glance "whose turn is whose"). |
| `CharacterSheet.tsx` | `sidequest-ui/src/components/CharacterSheet.tsx` | Modal/expanded sheet — the natural home for "played by …" treatment. |
| `CharacterWidget.tsx` | `sidequest-ui/src/components/GameBoard/widgets/CharacterWidget.tsx` | Board widget — tight pixel budget; tooltip-only is the cheap default. |

Future Wave 1 stories may touch additional surfaces; this table is not exhaustive.

## Cross-Epic Dependencies

**Depends on:**
- None. This epic is intentionally independent of the in-flight technical chains (Epic 52 megadungeon→renderer, Epic 51 fixture retarget). Playgroup QoL must be unblockable by other work.

**Depended on by:**
- None directly. Future Waves (54+) will share the pattern but each wave is independent.

**Soft relation:**
- ADR-036 / ADR-037 (multiplayer turn coordination + per-player state) — any story in this epic that displays inter-player state inherits the seated-player concepts those ADRs establish. This is not a hard dependency, but story authors should not violate sealed-rounds doctrine to satisfy a QoL ask.
