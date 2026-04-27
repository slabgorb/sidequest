---
parent: sprint/epic-45.yaml
workflow: wire-first
---

# Story 45-6: Chargen partial-completion path leaves resolved_archetype=NULL

## Business Context

**Playtest 3 evidence (2026-04-19, evropi session):**
`pumblestone_sweedlewit` exited chargen with `resolved_archetype=NULL`,
no derived hp/ac, and never advanced past the opening turn. The
character was on the snapshot, the player was bound to a seat, the
narrator emitted the opening prose — and yet the GM panel showed a
chargen that had structurally not finished. The `chargen.complete`
log line fired, the persist span fired, the state flipped to
`Playing`. The slot was wedged silently.

This is the canonical **wire-first** failure mode that CLAUDE.md flags:
"tests pass but nothing is wired." `_chargen_confirmation()` runs the
archetype resolver (`session_handler.py:2626`), but the resolver has
**three early-return branches** that succeed-silent-without-resolving
— and one of them was hit on `pumblestone`. Sebastien's lie-detector
is supposed to catch exactly this; the existing
`character_creation.archetype_resolution_failed` span fires only on
caught `GenreValidationError`, not on the silent-skip branches.

For James (narrative-first) the tell is downstream: the narrator's
prompt loses the resolved archetype as a Valley-zone anchor, so
character voice drifts; for Sebastien the tell is the GM-panel
character sheet showing a class with no archetype to back it; for
Alex the tell is the session that opens but never advances. ADR-014
(Diamonds and Coal) is the framing — `resolved_archetype` is
**diamond** (load-bearing for narrator and mechanics), but it can be
silently null and nothing in the system notices.

ADR-085 (port-drift) applies: the resolver shim is a faithful Rust
port (`connect.rs:1644-1737`), but the early-return branches predate
the Phase-2 chargen-port plan (`docs/plans/phase-2-chargen-port.md`),
which marked the loadout/archetype wiring as a known IOU.

## Technical Guardrails

### The three silent-skip branches (THIS IS THE BUG SURFACE)

`_resolve_character_archetype()` at `session_handler.py:2488–2570`
returns silently from three sites; each one leaves
`character.resolved_archetype` in a partial state:

1. **Builder produced no axis pair.** `builder.py:1588–1590`:
   `resolved_archetype = None` when `acc.jungian_hint` OR
   `acc.rpg_role_hint` is missing. The resolver short-circuits at
   `session_handler.py:2514` (`if raw is None or "/" not in raw: return`).
   `pumblestone`'s scene path almost certainly hit this — the
   `evropi` chargen scenes don't all set both axes.

2. **Pack lacks resolver inputs.** `session_handler.py:2519–2520`:
   `if pack.base_archetypes is None or pack.archetype_constraints is None:
   return`. The raw `"jungian/rpg_role"` literal is left on the
   character. The GM panel sees garbage but the snapshot is "valid."

3. **Resolver raises `GenreValidationError`.** `session_handler.py:2535–2552`:
   the catch logs and emits `archetype_resolution_failed`, then
   returns. The raw pair stays. The character ships.

The wire-first fix is to **gate `_chargen_confirmation()` on archetype
resolution being non-partial** — exactly one of `resolved_archetype is
None` (no axes — pack chose not to use them) OR
`resolved_archetype == resolution.resolved.name` (resolver succeeded).
The middle states ("raw `j/r` left on character" and "axes accumulated
but pack lacks resolver inputs") are not allowed to ship.

### Outermost reachable layer (wire-first seam)

The boundary test must exercise the WS-driven chargen flow end-to-end,
not unit-test `_resolve_character_archetype()` in isolation. The seams:

1. **Chargen completion seam** — `_chargen_confirmation()` at
   `session_handler.py:2573–2999`. The gate lands AFTER
   `_resolve_character_archetype()` (line 2626) and BEFORE the persist
   block (line 2938). Fail-loud on partial resolution; either a typed
   error frame back to the client (preferred) or a `BuilderError`
   thrown from `builder.build()` itself if the gate is pulled upstream.
2. **Builder seam** — alternative gate site is
   `CharacterBuilder.build()` at `builder.py:1585–1620`. Currently
   silently sets `resolved_archetype = None` if either hint is missing
   (`builder.py:1588–1590`). Pulling the gate here gives an earlier
   error but loses the pack-context check (the resolver only knows
   axes are unused after seeing the pack). Recommend gating in
   `_chargen_confirmation()` so the pack context is available.

### Three-step gate (what to wire)

In `_chargen_confirmation()`, after `_resolve_character_archetype()`
returns:

```python
# After line 2626 — BEFORE apply_starting_loadout.
gate = _gate_archetype_resolution(character, sd.genre_pack, span, player_id)
if gate.is_blocked:
    return [_error_msg(
        f"Character creation incomplete: {gate.reason}",
        code="chargen_archetype_unresolved",
    )]
```

Where `_gate_archetype_resolution()` (new helper, sibling to
`_resolve_character_archetype`) returns one of three states:

- **OK_RESOLVED** — `resolved_archetype` is a non-`/` display name and
  `archetype_provenance` is set. Pass.
- **OK_NO_AXES** — `resolved_archetype is None` AND the pack declares
  no archetype axes (`base_archetypes is None and archetype_constraints
  is None`). Pass — pack opted out of the system.
- **BLOCKED_PARTIAL** — anything else: raw `"j/r"` on character, OR
  `resolved_archetype is None` but pack has axes (chargen scenes are
  malformed), OR resolver raised. Fail. This is the
  `pumblestone` case.

### OTEL spans (LOAD-BEARING — gate-blocking per CLAUDE.md)

Define in `sidequest/telemetry/spans.py` and register routes:

| Span | Attributes | Site |
|------|------------|------|
| `chargen.archetype_gate_evaluated` | `state` (`"ok_resolved"`, `"ok_no_axes"`, `"blocked_partial"`), `resolved_archetype` (string or `null`), `pack_has_axes` (bool), `had_jungian_hint` (bool), `had_rpg_role_hint` (bool), `genre`, `world`, `player_id` | every call to `_gate_archetype_resolution()` |
| `chargen.archetype_gate_blocked` | same + `block_reason` (one of: `"raw_pair_unresolved"`, `"missing_axes_with_pack_axes"`, `"resolver_raised"`) | only on BLOCKED_PARTIAL |

Both fire on every chargen-confirm path (the first as the negative
confirmation Sebastien needs that the gate ran; the second as the
explicit lie-detector entry when a chargen would have shipped broken).

### Reuse, don't reinvent

- `_resolve_character_archetype()` at `session_handler.py:2488` stays.
  The new gate is a sibling helper that **inspects the post-resolve
  state**, not a replacement.
- `apply_archetype_resolved()` at `sidequest/game/archetype_apply.py:16`
  is already the canonical write site (`character.resolved_archetype =
  resolution.resolved.name`); the gate must accept that state as OK.
- The existing `character_creation.archetype_resolution_failed` event
  (`session_handler.py:2536`) stays as the inner-resolver event; the
  new spans wrap the outer gate.
- `_error_msg()` (used at lines 2382, 2387, 2459, 2599) is the
  established typed-error frame helper. Add a new `code=
  "chargen_archetype_unresolved"` to its dispatch list rather than
  inventing a new error path.

### Test harness

- `session_handler_factory()` at
  `sidequest-server/tests/server/conftest.py:332` is the WS-driven
  test fixture.
- `_FakeClaudeClient` at `conftest.py:197` lets chargen complete
  deterministically.
- `tests/server/test_chargen_complete_no_hp_leak.py` and
  `tests/server/test_chargen_persist_and_play.py` are the closest
  precedents; the new wire-test belongs alongside them.

## Scope Boundaries

**In scope:**

- New `_gate_archetype_resolution()` helper in
  `sidequest/server/session_handler.py` (sibling to
  `_resolve_character_archetype`).
- Wire the gate into `_chargen_confirmation()` between lines
  2626 (resolve) and 2628 (loadout).
- New error code `chargen_archetype_unresolved` on the typed-ERROR
  frame.
- New OTEL spans `chargen.archetype_gate_evaluated` and
  `chargen.archetype_gate_blocked`, registered in `SPAN_ROUTES`.
- Wire-first test that drives the WS chargen path with a pack that
  has axes and a chargen scene that fails to set both hints — assert
  the gate blocks and the character is NOT persisted.
- Positive wire-test: a pack with no archetype axes (e.g., the
  axis-free path) chargens cleanly and the gate returns
  `OK_NO_AXES`.
- Audit `evropi` chargen scenes (in `sidequest-content/genre_workshopping/heavy_metal/worlds/evropi/`)
  to confirm whether the bug surface is missing-axes-on-scene or
  pack-axis-config; report the finding in the implementation
  notes. Do not fix evropi content here — that's a content-pack
  story.

**Out of scope:**

- Reworking the archetype resolver shim itself
  (`sidequest/genre/archetype/shim.py`). The resolver is correct; the
  bug is in the gate.
- Migrating existing saves with `resolved_archetype=NULL`. Players
  re-roll if they hit the gate; no migration.
- Reworking `CharacterBuilder` to require both hints. Some packs
  legitimately don't use archetype axes; the gate must distinguish.
- UI changes. The typed error frame is server-side; the existing
  ERROR-frame UX surfaces it.
- HP/AC computation. ADR-014/078 replaced HP with EdgePool; "no
  hp/ac" in the playtest report is descriptive (the character had no
  archetype-derived class features), not a separate bug.

## AC Context

1. **Chargen with axes-set pack and fully-set hints succeeds and
   ships a resolved archetype.**
   - Wire-test: a pack with `base_archetypes` and `archetype_constraints`,
     chargen scenes that set both hints, drive
     `_chargen_confirmation()` → assert
     `character.resolved_archetype` is the resolved display name (not
     `"j/r"`), `archetype_provenance` is set, persist runs, state →
     Playing.

2. **Chargen with axes-set pack but unset hints (or partial pair) is
   blocked.**
   - Wire-test (the `pumblestone` regression): pack has axes; chargen
     scenes accumulate `jungian_hint` but not `rpg_role_hint` (or
     vice versa). Drive `_chargen_confirmation()` → assert it returns
     a typed ERROR frame with `code="chargen_archetype_unresolved"`,
     character is NOT appended to `sd.snapshot.characters`,
     `room.save()` is NOT called, state stays `Creating`.
   - This is the negative-to-positive transformation: the bug-evidence
     fixture (`pumblestone` partial) becomes the failing test that
     drives the gate into existence.

3. **Chargen with axes-free pack succeeds with `resolved_archetype=None`.**
   - Wire-test: pack with `base_archetypes is None` AND
     `archetype_constraints is None` (e.g., a minimal test pack).
     Drive chargen, assert character is persisted with
     `resolved_archetype is None`, gate logs `state="ok_no_axes"`.
   - Negative test against AC #2: this path must NOT be blocked. The
     gate distinguishes "pack opted out" from "pack opted in but
     scene malformed."

4. **OTEL `chargen.archetype_gate_evaluated` fires on every
   chargen-confirm with the right state attribute.**
   - Test all three branches (resolved / no_axes / blocked) — span
     fires once each with the correct `state` value and the boolean
     hint flags. `SPAN_ROUTES` registration verified — Sebastien's GM
     panel sees the event.
   - `chargen.archetype_gate_blocked` fires only on the blocked
     branch, with the correct `block_reason`.

5. **The resolver-raised path (case 3 above) routes through
   the gate as `BLOCKED_PARTIAL`.**
   - Test: stub the resolver to raise `GenreValidationError`. Drive
     chargen → existing `archetype_resolution_failed` event fires
     (legacy path), gate observes `resolved_archetype` is still the
     raw `"j/r"`, blocks with `block_reason="resolver_raised"`,
     returns the typed ERROR frame. Character not persisted.
