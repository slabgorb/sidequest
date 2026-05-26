---
parent: context-epic-63.md
workflow: tdd
---

# Story 63-6: LocationPanel region-header reference deep-link (re-scoped from "test parity")

## Business Context

Epic 63 turns the server-rendered `/reference/lore/<pack>/<world>` pages into SideQuest's
in-world wiki and wires the game-client panels to deep-link *into* those pages via
server-emitted `reference_url` fields. CharacterSheet (abilities + class), PartyMember,
KnowledgeJournal (JournalEntry), and LocationEntity all received this treatment in 63-4.

The **LocationPanel region header** was the one slice that did not ship. It was originally
descoped from 63-4 because it entangles server and UI, then mis-filed as a 1-point UI-only
"test parity" task on the false assumption the production code already existed. It does not
(verified against `develop`: no `reference_url` on `LocationDescriptionPayload` in either
the server protocol model or the UI type; `LocationPanel.tsx:83` renders the region header
as a plain `<span>`). This story builds that deep-link end-to-end so a player reading a
location panel can click the region name and jump to its lore-page anchor — the same
affordance CharacterSheet already gives for class/abilities.

**Audience fit:** Keith and the high-reading-tolerance players (James, Jade) use the wiki
pages; a consistent "click the title to read more" affordance across every dock panel is
the payoff. This is cosmetic-adjacent wiring, not a mechanical surface — no player-facing
math is involved.

## Technical Guardrails

**Follow the CharacterSheet `class_reference_url` precedent exactly — do not invent a new pattern.**

- **Server payload:** `sidequest-server/sidequest/protocol/models.py` → add
  `reference_url: str | None = None` to `LocationDescriptionPayload`. Optional + defaulted
  so old saves/snapshots deserialize cleanly.
- **Server emit:** `sidequest-server/sidequest/server/reference_anchors.py` and
  `server/views.py` already resolve anchors for character/journal payloads (63-4). Resolve
  the location anchor the same way — region → `/reference/lore/<pack>/<world>#location-<slug>` —
  and populate the field where the `LocationDescriptionPayload` is constructed. **No silent
  fallback:** if the anchor does not resolve, set `None` (graceful, renders plain text); do
  not emit a guessed or broken URL.
- **UI type:** `sidequest-ui/src/types/payloads.ts:753` → add
  `reference_url?: string | null` to `LocationDescriptionPayload` (mirror the
  `LocationEntity.reference_url` field already at ~line 761).
- **UI render:** `sidequest-ui/src/components/LocationPanel.tsx:83` → region header becomes a
  conditional anchor (`<a target="_blank" rel="noopener" href={...}>` when set, `<span>` when
  null/undefined). Mirror the CharacterSheet class-subtitle anchor.
- **OTEL:** the reference-anchor decision should ride the existing
  `sidequest-server/sidequest/telemetry/spans/reference.py` span family added in 63-4, so the
  GM panel can confirm location anchors resolve. Do not add a parallel span — extend/reuse.

**Do NOT touch:**
- Entity rendering in `LocationPanel`. The component renders prose only by design
  (Zork-Problem doctrine, ADR-109 / story 54-9). The top-of-file comment is explicit:
  "Do not add entity chips here." Adding clickable entities is out of scope and a doctrine
  violation.
- The `prettifyRegionId` display logic — wrap its output in the anchor, don't replace it.

## Scope Boundaries

**In scope:**
- `reference_url` field on `LocationDescriptionPayload` (server model + UI type).
- Server-side resolution + population of that field via existing anchor machinery.
- LocationPanel region-header conditional anchor rendering.
- `LocationPanel.reference.test.tsx` covering the three render cases.
- Verifying OTEL coverage for the location anchor decision.

**Out of scope:**
- Entity / manifest rendering in LocationPanel (ADR-109 — stays excluded).
- Any other panel's reference links (CharacterSheet, KnowledgeJournal, PartyMember already shipped in 63-4).
- Reference-page (server-rendered HTML) chrome/styling — that is 63-7/63-8 territory.
- Changing the `#location-<slug>` anchor scheme itself (reuse what the lore page already emits).

## AC Context

1. **Server field + emit.** A `LocationDescriptionPayload` built for a region that has a
   matching lore-page anchor carries `reference_url == "/reference/lore/<pack>/<world>#location-<slug>"`.
   For a region with no resolvable anchor, `reference_url is None`. Edge cases a test should
   cover: region slug that exists in cartography but has no POI/lore entry → `None` (not a
   crash, not a guessed URL); pack/world with no reference pages at all → `None`.
2. **UI type.** `LocationDescriptionPayload` in `payloads.ts` includes the optional field;
   existing consumers compile unchanged (field is optional).
3. **UI render — the testable core.** Given `data.reference_url` set, the region header is a
   single `<a>` with `href` == that value, `target="_blank"`, and `rel` containing `noopener`.
   Given `null` or omitted, the header is plain text and `queryByRole('link')` returns null.
   The region label text (`prettifyRegionId(region_id)`) must be present in both cases.
4. **Test file.** `LocationPanel.reference.test.tsx` mirrors `CharacterSheet.reference.test.tsx`
   structure: a `makeData`-style payload factory, three `it()` cases (set / null / omitted),
   assertions on `getByRole('link')` href+target+rel and `queryByRole('link')` null. Must not
   duplicate the existing `LocationPanel.test.tsx` prose/terrain/overlay coverage. Must not
   reference a live pack/world slug — use a synthetic payload (per project rule: tests don't
   point at live content).
5. **OTEL.** A location anchor resolution emits (or is covered by) the `reference.py` span so
   the GM panel shows location anchors firing. A wiring check should confirm the span is
   reachable from the location-payload code path, not just the character one.

## Assumptions

- The 63-4 anchor machinery (`reference_anchors.py`, `reference.py` span) is generic enough to
  resolve a location/region anchor with minimal new code — i.e. the same helper that builds
  `#class-<slug>` and journal anchors can build `#location-<slug>`. **If this proves false**
  (location anchors need a distinct resolver), log a Design Deviation and notify SM —
  that could push points past 3.
- The lore page already emits `id="location-<slug>"` anchors (63-8 / cartography work), so the
  URL the server produces will actually resolve in-page. If the anchor id scheme differs, the
  href is still correct to emit; coordinating the in-page anchor is 63-8's job, not this story's.
- `region_id` → slug mapping for the URL uses the same convention the lore page uses. If there's
  a slug-consistency gap (cartography region key vs history.yaml POI slug — a known 63-8 risk),
  the server resolves to `None` rather than emitting a non-resolving link.
