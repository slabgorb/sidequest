---
parent: context-epic-73.md
workflow: tdd
---

# Story 73-4: Make no-dial-move CritSuccess legible

> **Story:** push/angle CritSuccess scores 0 — make beat-kind impact legible so a
> no-dial-move crit reads as intended, not broken (Sebastien/Jade)
> **Epic:** 73 (Confrontation Engine Hardening) · **Points:** 2 · **Type:** bug ·
> **Workflow:** tdd · **Repos:** sidequest-server, sidequest-ui

## Business Context

This story exists for **Sebastien and Jade** — the playgroup's two mechanics-first
players (CLAUDE.md). They want to *see the math* behind every resolution, and right
now a specific, correct outcome lies to them.

When a player commits a `push` beat (the "voluntary exit" move — `walk_away`,
`concede`, `Clean Exit`) and rolls a **CritSuccess**, the engine's default delta
table is `{resolution: True, grants_fleeting_tag: "Clean Exit"}` with `own=0` /
`opponent=0` (`game/beat_kinds.py`, `DEFAULT_DELTAS[BeatKind.push][CritSuccess]`).
This is **by design**: a clean exit doesn't "win" the dial — it ends the
confrontation cleanly. But the only player-facing mechanical readouts are the two
dial bars (`EdgeBar` in `ConfrontationOverlay.tsx`) and the dice tray, and neither
explains *why* the best possible roll moved nothing. A mechanics-first player reads
"CritSuccess → dial +0" as a broken roll, exactly the class of silent-mechanics
failure the project's OTEL doctrine exists to catch — except here the engine is
*correct* and the **presentation** is what's broken.

This is a **player-UI legibility** fix: surface the beat-kind's actual semantic
outcome ("clean exit — resolves the confrontation, no dial change by design")
alongside the 0, so the crit reads as intended. The same illegibility applies to
the `angle` kind on non-CritSuccess tiers (a `Tie` grants a fleeting tag but moves
no dial) and to any beat whose default table yields `own=0`/`opponent=0` with a
non-dial effect (resolution flag, tag grant, backfire).

> **Audience boundary (CLAUDE.md, load-bearing):** This is a *player-facing*
> surface change for Sebastien/Jade. It is **NOT** an OTEL/GM-panel/dev-observability
> task. Do not frame any backend emit as "Sebastien's lie-detector" — that's a
> Keith/dev tool. The existing `beat_no_op` watcher event
> (`beat_kinds.py:~775`) already covers the dev-observability side of "neither
> dial moved"; this story does **not** need to extend it. The deliverable is the
> *player UI* readout (plus whatever structured field the server must add to the
> player-bound payload to feed it).

## Technical Guardrails

**Do NOT change the dial math.** `DEFAULT_DELTAS[push][CritSuccess]` staying
`{own=0, opponent=0, resolution=True, grants_fleeting_tag:"Clean Exit"}` is the
correct, spec-aligned behavior (dual-track momentum design,
`docs/superpowers/specs/2026-04-25-dual-track-momentum-design.md`). The bug is
legibility, not arithmetic. A change that makes the crit move a dial is a
regression, not a fix.

**Real seams (verified):**

- `sidequest-server/sidequest/game/beat_kinds.py`
  - `BeatKind` enum (`strike`/`brace`/`push`/`angle`) and `ResolvedDeltas`
    (`own`, `opponent`, `grants_tag`, `tag_leverage`, `grants_fleeting_tag`,
    `tag_backfire`, `resolution`).
  - `DEFAULT_DELTAS` — `push` Success/CritSuccess carry `resolution: True` with no
    dial move; `angle` Tie/Success/CritSuccess grant tags with no dial move.
  - `resolve_tier_deltas(...)` merges kind defaults + per-beat overrides → flat
    `ResolvedDeltas`.
  - `apply_beat` (~line 860) honors the resolution flag: resolves on
    `deltas.resolution or getattr(beat, "resolution", False)` →
    `enc.outcome = f"resolution_beat:{beat.id}"`. The `beat_no_op` watcher emit
    (~line 775) already exists for the **dev** side — leave it as the model for
    what "no dial moved, by design" means semantically, but the player surface is
    new.
- `sidequest-server/sidequest/server/narration_apply.py`
  - Beat-kind reporting / `ENCOUNTER_BEAT_APPLIED` watcher emit at **~line 3199**
    (`op: "beat_applied"`, carries `beat_kind`, `outcome_tier`, `own_delta`,
    `opponent_delta`). This is where the structured beat-kind impact is assembled
    server-side; the **player-bound** payload the UI consumes is built near the
    same pipeline. The structured "intended impact" data the UI needs to render
    the explanation must ride a **player-facing** message/payload, not (only) the
    watcher stream.
- `sidequest-ui/src/components/ConfrontationOverlay.tsx`
  - `BeatOption` interface (mirrors server `BeatDef`): `kind`, `base`,
    `resolution?`, `target_tag?`, `risk?`, `flavor?`.
  - `EdgeBar` renders the two dials; `InlineDiceTray` renders the roll outcome.
    **Neither** explains beat-kind intent — this is the gap.
  - `ConfrontationOutcomeReveal` (~line 486) is the existing precedent for a
    "what just resolved" callout panel (currently fed by the Phase-5
    `ConfrontationOutcome` / `CONFRONTATION_OUTCOME` magic-confrontation path). It
    is the natural home/pattern for a beat-kind impact explanation, but note its
    current data source is magic-confrontation-specific; do not conflate the two
    branches without confirming the dial-confrontation path actually delivers a
    payload there.
- `sidequest-ui/src/types/payloads.ts`
  - `RollOutcome` union (`CritSuccess | Success | Tie | Fail | CritFail`),
    `DiceResultPayload`, `ConfrontationPayload`. Any new player-facing impact field
    is typed here.

**TDD expectations (epic + repo doctrine):**
- Server: a unit test over `resolve_tier_deltas` / the impact-description helper
  asserting that `push` CritSuccess yields a "resolves / no dial move by design"
  descriptor; plus a **wiring test** that the descriptor is present on the
  player-bound payload emitted from the `narration_apply.py` beat path (not just
  derivable in isolation). Per CLAUDE.md "Every Test Suite Needs a Wiring Test."
- UI: a `ConfrontationOverlay` test asserting that a no-dial-move CritSuccess
  renders the explanation (resolution/tag), not a bare "0", and that a
  dial-moving outcome still renders the dial delta normally. Follow the existing
  `ConfrontationOverlay.outcomereveal.test.tsx` pattern.

## Scope Boundaries

**In scope:**
- Server: derive/expose a structured **beat-kind impact descriptor** for the
  applied beat (kind + outcome tier → human-legible effect: "resolves
  confrontation", "grants tag X", "no dial change by design") on the
  **player-facing** payload the overlay consumes.
- UI: render that descriptor so a no-dial-move CritSuccess reads as intended,
  covering `push` (resolution + Clean Exit tag) and `angle` (tag-grant) and any
  `{own=0, opponent=0}`-with-effect tier.

**Out of scope:**
- **Recipe conversions** (negotiation/scandal/trial → opposed_check). That is
  73-1 / 73-2. This story touches **no** `rules.yaml`.
- The `advance_confrontation` lost-update (73-3) and the re-fired
  `confrontation_initiated` span (73-5).
- **Any dial-math change.** The 0 is correct.
- **Extending dev observability.** The `beat_no_op` / `beat_applied` watcher
  emits are sufficient on the dev side; do not gold-plate the OTEL/GM-panel
  surface. If you find yourself adding a span "so Sebastien can verify," stop —
  that's the wrong association per CLAUDE.md.

## AC Context

No explicit ACs were authored. Derived, testable:

**AC1 — No-dial-move CritSuccess is explained, not bare-zero (push).**
A `push` beat resolved at `CritSuccess` (`own=0`, `opponent=0`, `resolution=True`,
`grants_fleeting_tag="Clean Exit"`) renders, in the player-facing confrontation
surface, an explanation of its actual effect — e.g. "Clean Exit — resolves the
confrontation (no dial change by design)" — instead of, or alongside, a 0 that
reads as a failed/broken roll. The CritSuccess tier is visibly *good*.

**AC2 — Beat-kind intended impact is legible for tag-granting no-dial outcomes
(angle).** An `angle` beat at a tier whose default table grants a tag with no dial
move (e.g. `Tie` → fleeting tag, `Success`/`CritSuccess` → durable tag +
leverage) renders the tag grant as its legible impact, not a bare 0.

**AC3 — Server emits the structured beat-kind impact data the UI needs.**
The beat-application path in `narration_apply.py` (~line 3199) produces, on the
**player-bound** payload, a structured impact descriptor (kind, outcome tier,
dial deltas, and the semantic effect: resolution / tag / no-dial-by-design) — and
a wiring test proves the UI's render path actually receives it (imported, sent,
consumed), not merely that a helper can compute it.

**AC4 — Dial-moving outcomes still render their delta unchanged (no regression).**
A `strike`/`brace` (or `push`/`angle`) outcome that *does* move a dial renders the
dial advance exactly as today; the new explanation surfaces in addition to, and
does not replace or distort, normal dial-delta presentation.

**Edge cases to exercise:**
- **CritSuccess that DOES move a dial** — e.g. `strike` CritSuccess
  (`own_expr:"b"`, `grants_fleeting_tag:"Opening"`): shows dial advance *and* the
  Opening tag; not swallowed by the new no-op explanation. (Covered by AC4.)
- **CritFailure** — `push` CritFail = `{own: -1}` (a *negative* dial move). Must
  read as a setback, distinct from the "0 by design" case. Don't lump "negative"
  in with "no change."
- **Mixed-effect beat** — `angle` CritFail (`tag_backfire: True` + fleeting tag on
  the opposing side) and any beat with a per-tier `deltas:` override (via
  `resolve_tier_deltas`): the legibility layer must read the *resolved* deltas,
  not the kind's nominal default, so an override that adds/removes a dial move is
  described correctly.

## Assumptions

- The `ConfrontationOutcomeReveal` panel is the established UX precedent for a
  "what just resolved" callout, but its current feed is the Phase-5 magic
  `ConfrontationOutcome` payload. **Assumption:** the dial-confrontation beat path
  needs its own player-facing impact field (likely on the beat-result/dice-result
  or a CONFRONTATION update payload) rather than reusing
  `ConfrontationOutcome.branch`, which is magic-confrontation-specific. Confirm
  the actual payload the overlay receives on a beat-resolution turn before wiring.
- The impact descriptor should be **derived server-side** (single source of
  truth for kind+tier semantics lives in `beat_kinds.py`), not re-implemented as a
  lookup table in TypeScript — the UI renders a server-provided string/struct.
  This keeps Sebastien/Jade seeing the *engine's* truth, not the client's guess.
- The fleeting-tag text ("Clean Exit", "Opening", "Counter Stance") is already
  authored in `DEFAULT_DELTAS`; the descriptor can surface those verbatim.
- "No saves to migrate" (user memory) — no back-compat concern for a new
  player-facing field on the confrontation payload.

## Interaction Patterns

This story touches `sidequest-ui`, so UI legibility is a first-class deliverable.

- **Where it appears:** in/near `ConfrontationOverlay`, at outcome time — the
  moment a beat resolves and the dice settle. The natural slot is the existing
  "what just resolved" zone (the `ConfrontationOutcomeReveal` anchor between the
  status line and the beat grid, ~line 547) and/or adjacent to the
  `InlineDiceTray` outcome, so the explanation sits where the player already looks
  for "what just happened." Do not bury it in a tooltip — a mechanics-first player
  should not have to hover to learn the crit wasn't broken.
- **Reads as intended, not broken:** the CritSuccess tier must visually present as
  a *good* result even at dial +0. Tie the explanation to the outcome tier so the
  player sees "best roll → clean exit," not an unlabeled 0 next to a green die.
- **Distinguish the three zero-ish cases:** "no dial change *by design*"
  (push/angle resolve/tag), "no change because the roll failed" (Fail tier,
  genuinely inert), and "negative dial move" (CritFail). These must not read
  identically — the bug is precisely that the first currently reads like the
  second.
- **Don't regress the dial bars:** `EdgeBar` fill/`current`/`threshold` continues
  to be the canonical dial display; the new explanation is an *adjunct* readout of
  beat-kind intent, not a replacement for the dials.
- **Pacing/visibility (ADR-036):** this is a post-resolution readout, not a
  submission-phase element, so it does not interact with the submit-and-wait turn
  barrier. It should not add latency or block the next move-set.
