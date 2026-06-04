---
parent: context-epic-85.md
workflow: tdd
---

# Story 85-1: Confrontation panel legibility & layout pass — readable dial, beat-caption fits its card, kill the dead-space/floating-die

## Business Context

A confrontation is the **drama peak** of a scene, and two of the five playgroup members
(**Sebastien, Jade**) play *for the crunch* — the dial/DC math is the thing they came to read.
Today that readout is the thinnest, smallest, lowest-contrast element on the screen, the beat
tiles huddle in a corner, captions overflow their cards, and the die floats in a void away from
the beat that threw it. Keith's playtest note — *"During confrontations I feel we are not using
space well"* — is the trigger.

This story makes the existing confrontation strip **legible and well-spaced** without changing
its container (that bigger spatial promotion is deferred to 85-3). It pays back three SOUL
principles inside the current strip: **Cost Scales with Drama** (the dial becomes the headline,
not a hairline), **Diamonds and Coal** (layout now signals importance), and the
**OTEL-in-the-player-UI** spirit the crunch players want — a beat-history ledger so they can
*see* the engine moved the dial, not just trust the prose. Closes playtest **L162** and the
"not using space well" space-usage finding.

## Technical Guardrails

**Single file to modify:** `sidequest-ui/src/components/ConfrontationOverlay.tsx` (~31KB). All
target sub-pieces are internal to it:

- `StatusLine` → `EdgeBar` — the dial readout (A1). Today: `h-1` hairline tracks,
  `text-[9px]`/`text-[10px]` numerals, dark-on-dark empty track.
- `BeatGrid` — `gridTemplateColumns: repeat(auto-fill, minmax(150px, 1fr))` (A2 → `auto-fit`).
- `BeatTile` — italic flavor caption overflows the right edge (A4).
- `InlineDiceTray` — die in a `flex-shrink-0 w-[200px]` lane, disconnected from the clicked
  tile (A3).

**Patterns to follow:**
- **Pure UI / render-level only. No protocol or payload change.** The CONFRONTATION payload
  already carries dial values, beats, and stat/kind/DC. If you find yourself needing a new
  payload field, STOP and log a deviation — that signals scope has crossed into 85-3.
- Extend the **existing test suite**, don't reinvent it: `src/components/__tests__/`
  (`ConfrontationOverlay.test.tsx`, `.beatimpact*.test.tsx`, `.outcomereveal.test.tsx`,
  `.opponentbeatimpact.test.tsx`). Vitest + React Testing Library. Mirror the existing fixture
  and render-harness conventions in those files.
- Authoritative spec for every AC: `docs/design/confrontation-space-usage.md` **Tier A**
  (recommendations A1–A5) + its Accessibility section. The 6 ACs map 1:1 to A1–A5 + a11y.

**What NOT to touch:**
- The confrontation **mechanics** — dice → dial → tag-fire, stat/kind/DC exposure. These are
  sound and verified (#647); this is presentation only.
- The **container/mount** (the bottom-strip vs dockview question) — that's Tier B / 85-3.
- The location surface (85-2) — unrelated.

## Scope Boundaries

**In scope:**
- A1 — Dial promoted to a single tug-of-war scoreboard: YOU fills from left, THEM from right
  toward a center line; large tabular numerals; a *visible* empty-track color (THEM 0/10 must
  not be dark-on-dark); WCAG AA 4.5:1 on title + numerals.
- A2 — `BeatGrid` `auto-fill` → `auto-fit` (keep `minmax(150px, 1fr)`) so tiles stretch to fill
  the row instead of huddling left with phantom columns.
- A3 — Die anchored to the committed beat: roll in the clicked tile's own row (tile expands to
  show `rolled N vs DC M → tier`); retire or shrink the disconnected fixed 200px die lane.
- A4 — Beat caption wraps inside its tile (or moves to a `title`/`▾` expand); never overflows
  the right edge.
- A5 — Reclaim the freed right space as a 3-line beat-history ledger
  (`actor · beat · roll vs DC · dial Δ`) giving the dial movement visible mechanical provenance.
- Accessibility — beat tiles keyboard-reachable in DOM order with a visible focus ring;
  locked-Enter state has an `aria-live` hint; resolution beat (e.g. `Refuse the Premise ✦`)
  carries a distinct role/label (not just an amber border); die/dial animations respect
  `prefers-reduced-motion`.

**Out of scope:**
- Spatial promotion to a dockview "confrontation mode" panel, opponent portrait, stakes line,
  "Meanwhile at the table" Guitar-Solo row → **85-3** (Tier B), gated on a split-vs-takeover
  Architect decision.
- Any server/protocol/payload change. If a needed field is missing, it belongs to 85-3.
- The location-surface "where am I" divergence → **85-2**.

## AC Context

1. **A1 — Dial as headline (closes L162-1).** Pass = the dial renders as a bidirectional
   tug-of-war scoreboard with both numerals shown as large tabular text, and the empty THEM
   track uses a *visible* color token distinct from the panel background.
   - Edge cases: THEM at `0/10` must be visibly an empty-but-present track (the original defect);
     YOU at `10/10` (full); both mid-value; values changing mid-confrontation re-render
     correctly.
   - Test approach: render with a fixture where THEM=0/10, assert the THEM numeral node is
     present in the DOM and its track element carries the visible empty-track class/token (not
     the panel-bg token). Assert numeral font-size class is the promoted size, not `text-[9px]`/
     `text-[10px]`. Contrast itself is asserted structurally (correct token applied), with the
     AA 4.5:1 rationale documented.

2. **A2 — BeatGrid auto-fit.** Pass = `BeatGrid`'s `gridTemplateColumns` uses `auto-fit`
   (not `auto-fill`), preserving `minmax(150px, 1fr)`.
   - Edge cases: few beats (2–3) stretch to fill rather than huddle; many beats (6+) wrap
     gracefully; single beat.
   - Test approach: assert the computed/inline `gridTemplateColumns` style string contains
     `auto-fit` and `minmax(150px, 1fr)`, and does NOT contain `auto-fill`.

3. **A3 — Die anchored to beat (closes L162-3).** Pass = on committing a beat, the roll result
   (`rolled N vs DC M → tier`) renders within/under the clicked tile's own row; the standalone
   fixed `w-[200px]` die lane is retired or reduced to a compact docked chip.
   - Edge cases: roll before any beat selected (no orphan die lane); successive beats each show
     their own roll under their own tile; critical vs fail tier labels.
   - Test approach: simulate a beat click, assert the roll-result node is a descendant of that
     tile's row, and assert no element with the old fixed `w-[200px]` standalone die-lane class
     remains (or that it's the compact variant).

4. **A4 — Caption wraps inside its card (closes L162-2).** Pass = a long beat caption wraps
   within the tile and does not overflow horizontally.
   - Edge cases: very long caption; short caption; caption with no spaces (forced break);
     caption moved to `title`/expand variant.
   - Test approach: assert the caption element carries a wrapping class (e.g. `break-words` /
     `whitespace-normal`) and not a clipping/nowrap class; assert it's contained within the tile
     element in the DOM.

5. **A5 — Beat-history ledger.** Pass = a beat-history region renders the last ~3 beats as
   `actor · beat · roll vs DC · dial Δ` rows reflecting committed beats.
   - Edge cases: zero history (confrontation start — ledger empty or shows "chase begins"
     style placeholder, not broken); one entry; more than 3 entries (only most recent ~3 shown);
     dial Δ sign (+/−) correct.
   - Test approach: render with a fixture of committed beats and assert the ledger lists the
     expected rows with actor, beat name, roll-vs-DC, and dial delta; assert it caps at ~3 rows.

6. **Accessibility.** Pass = (a) beat tiles are focusable in DOM order with a visible focus
   ring; (b) when plain-Enter commit is locked, an `aria-live` hint announces "pick a beat to
   commit"; (c) the resolution beat has a distinct accessible role/label beyond color; (d)
   die-roll and dial-pulse animations are gated behind `prefers-reduced-motion`.
   - Edge cases: keyboard-only navigation reaches every commit-path tile; screen-reader hint
     fires on the locked state; resolution beat distinguishable without color.
   - Test approach: assert tiles are in tab order (focusable, no positive tabindex reorder) and
     have a focus-ring class; assert an `aria-live` region exists and carries the locked-commit
     hint; assert the resolution beat has a distinct `role`/`aria-label`; assert reduced-motion
     guard (class/media-query branch) is present on the die/dial animation path.

## Assumptions

- The CONFRONTATION payload already carries everything the ledger (A5) needs — actor, beat
  name, roll, DC, and dial delta per committed beat. If any of these is absent client-side, the
  ledger may need a small derivation from existing state; a *new payload field* would push the
  work into 85-3 → log a deviation if discovered.
- All target sub-pieces (`StatusLine`/`EdgeBar`/`BeatGrid`/`BeatTile`/`InlineDiceTray`) remain
  internal to `ConfrontationOverlay.tsx` and are not separately exported — tests render the
  overlay and assert on its output rather than unit-testing extracted components.
- The existing Vitest + RTL harness and fixtures in `src/components/__tests__/` are reusable for
  the new render assertions.
- Tailwind utility classes are the styling mechanism (consistent with the `h-1`/`text-[9px]`/
  `w-[200px]` literals in the current code), so structural class assertions are a valid proxy
  for the visual ACs.

## Interaction Patterns

- The **only commit path during a confrontation is selecting a beat tile** — plain Enter is
  locked. The redesign must keep beat selection as the primary, obvious affordance.
- Beat click → die rolls **under that tile** → result (`rolled N vs DC M → tier`) appears in the
  same spatial unit → the dial scoreboard animates its delta → the ledger gains a row. This
  beat→roll→result→dial→ledger chain should read as one continuous spatial flow, not scattered
  across the strip.
- The resolution beat (e.g. `Refuse the Premise ✦`) is the win move and should be visually and
  semantically distinguished from ordinary beats.

## Accessibility Requirements

- **Contrast:** dial numerals + title to WCAG AA 4.5:1 against the panel; today they fail
  (dark-gray on near-black). The empty THEM track needs its own visible token, not `bg-muted` at
  panel opacity.
- **Keyboard:** beat tiles must be keyboard-reachable in DOM order with a visible focus ring
  (they are the sole commit path).
- **Screen reader:** the locked-Enter state needs an `aria-live` hint ("pick a beat to commit")
  so it isn't a silent dead-end; the resolution beat needs a distinct role/label, not just an
  amber border.
- **Motion:** respect `prefers-reduced-motion` for the die-roll and dial-pulse animations.

## Visual Constraints

- Stay inside the **existing bottom-strip container** (`confrontation-panel … border-t px-3 pt-2
  pb-1`) — no container/mount change (that is 85-3).
- Reuse the established Tailwind token system; replace the failing literals (`h-1`,
  `text-[9px]`/`text-[10px]` for the dial; `auto-fill`; `w-[200px]` die lane) with the promoted
  scoreboard, `auto-fit` grid, anchored die, and ledger.
- Keep `minmax(150px, 1fr)` on the beat grid so tiles still wrap gracefully at narrow widths.
