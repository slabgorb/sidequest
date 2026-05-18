---
id: 108
title: "MP Item Attribution — Per-Recipient Tagging in the Narration Tool Contract"
status: accepted
date: 2026-05-18
deciders: ["Keith Avery", "The White Queen (Architect)"]
supersedes: []
superseded-by: null
related: [37, 102, 36, 104, 14]
tags: [multiplayer, agent-system, game-systems]
implementation-status: deferred
implementation-pointer: docs/adr/108-mp-item-attribution-recipient-tagging.md#implementation-guidance-for-dev
---

# ADR-108: MP Item Attribution — Per-Recipient Tagging in the Narration Tool Contract

## Status

accepted — implementation deferred to Dev (the White Rabbit). This ADR is
the contract; no code ships with the ADR itself.

## Context

Playtest 2026-05-17 `coyote_star-mp` (Ritali Veer + Catalina Valentine,
117 sealed rounds). Keith's report: *"inventory and xp all go to the host
player, this is a bug."*

The XP half was a bounded server fix (per-turn tick made party-wide;
PR #321, merged; live save repaired). The **inventory half is a contract
change, not a patch**, and was deliberately not free-handed by Dev.

Root cause: `narration_apply.py` (`_apply_*`, ~line 1944) applies the
narrator's `items_gained` / `items_lost` / `items_discarded` /
`items_consumed` to `snapshot.characters[0]` — a literal artifact of the
single-player Rust port (ADR-082). In MP this dumps every narrator-granted
item on the first/host seat regardless of who the narration says received
it (coyote_star: the Station Map Chip and ×2 Corvette Scan Data all landed
on Ritali, including a scan chip the prose explicitly had Ritali *hand to
Catalina*).

Two structural facts make this a contract problem:

1. **Sealed rounds (ADR-036).** Every seated PC submits an action each
   round; the narrator resolves them together into one narration. There
   is **no single "acting player" per turn** — so "give the item to the
   actor" is not implementable from turn structure alone. *Who received
   what* is information only the narrator holds (it just wrote the prose
   that says so).

2. **Per-player inventory (ADR-037).** `PlayerState` holds the character
   sheet/HP/inventory per player. There is no shared-inventory model, so
   there is no correct party-default; the item must be attributed to a
   specific seated PC.

`items_gained` entries are `list[dict[str, Any]]` and carry no recipient;
the apply path reads no recipient key; there is no `give_item` tool. The
recipient signal **does not exist in the protocol**. Any non-narrator
attribution (prose-mining, positional guess) is the same fragility class
the project forbids, and `characters[0]` is simply the bug.

## Decision

Extend the narration tool contract (ADR-102) so **every item-mutation
entry carries an explicit `recipient`** — the name of the seated PC the
item belongs to — and resolve it through the existing seat machinery.
This is an **extension of existing infrastructure, not a new system**
(see *Reuse Justification*).

### 1. Contract surface (extends ADR-102)

Each entry in **all four item lanes** — `items_gained`, `items_lost`,
`items_discarded`, `items_consumed` — gains an optional-in-schema,
**required-by-contract** string field:

```
recipient: <exact name of a seated PC, as it appears in player_seats.values()>
```

The narrator already does exactly this for `BeatSelection.actor`
(orchestrator.py:123) — it names which PC each beat belongs to and that
name is validated against the seated-PC set. Item recipients reuse the
same convention and the same vocabulary the narrator already produces.

The tool/prompt guidance (the ADR-102 structured-output instructions)
must state: *for every item a specific PC gains, loses, discards, or
consumes, set `recipient` to that PC's exact name; in a sealed multi-PC
round this is mandatory, never omit it.*

### 2. Resolution (reuse the seated-PC machinery)

A new single helper — `resolve_item_recipient(snapshot, entry, *,
narrating_character_name)` — resolves each entry's target Character:

- `recipient` names a seated PC (∈ `snapshot.player_seats.values()`,
  matched to a `snapshot.characters[*].core.name`) → **that Character**.
- `recipient` absent **or** not a seated PC → **absent-recipient rule**
  (§3). Never `snapshot.characters[0]` as a positional default.

Single-player / no seat manifest: `player_seats` empty ⇒ the lone
character is the only resolution; behaviour is unchanged (parity with the
ADR-108 sibling XP fix and the `character_locations` precedent).

All four lanes call this one helper (reuse-first; anything narrower
re-introduces the identical bug on the untouched lanes — Catalina
consuming her own medpatch must not remove it from Ritali).

### 3. Absent-recipient rule (decided)

Recipient is **contractually required**. When the narrator omits it (or
names a non-seated entity) it is a **narrator contract violation**, and
the apply path must *fail loud and degrade defensibly — never drop a
narrated item, never use `characters[0]`*:

- Emit a GM-panel-visible watcher event
  `inventory.recipient_missing` (component `inventory`) with the item
  name, the lane, the offered `recipient` (if any), and the seated set.
  This is the OTEL lie-detector: Keith/the GM panel sees exactly how
  often the narrator violates the contract, so the prompt can be tuned
  against real miss rates.
- Attribute the item to the **narrating socket's PC** —
  `acting_character_name` (already threaded into `_apply_*` for location
  binding; falls back to `player_name`). This is the least-wrong,
  *deterministic and observable* default in a sealed round: exactly one
  socket's narration turn is being applied, and that socket's PC is a
  defensible owner. It is explicitly **not** `characters[0]`.

Rationale: dropping a narrated item ("the officer hands you the map
chip" → no chip) is a continuity break that violates *Yes, And* and
player trust; a shared/unassigned pool contradicts ADR-037; prose-mining
is forbidden fragility. "Strict contract + loud telemetry + non-breaking
defensible degradation" is the codebase's established pattern (the
`seated_pc_names` beat gate, the ADR-108-sibling XP `seat_mismatch`
handling, the `region_projection` "log loud, emit OTEL, continue"
precedent).

### 4. Observability (mandatory, per CLAUDE.md OTEL principle)

Every item application emits a watcher event (component `inventory`)
naming the resolved recipient, the lane, and whether resolution was
`tagged` | `recipient_missing` | `non_seated_recipient`. The GM panel
must be able to answer "did Catalina actually get the medpatch, or did
the narrator wing it?" — the same lie-detector standard the XP fix met.

## Consequences

**Positive**
- Narrator-granted items land on the PC the story says received them.
- One helper fixes all four lanes; no latent twin bug left behind.
- Recipient-miss rate becomes a *measured* signal (watcher), driving
  prompt tuning instead of silent corruption.
- Pure extension: no new schema class, no new state model, no shared
  inventory; `dict[str, Any]` already admits the `recipient` key.

**Negative / cost**
- The ADR-102 prompt/tool guidance must be updated and the narrator's
  compliance is probabilistic — hence the mandatory loud telemetry and
  the deterministic fallback. Early sessions will show non-zero
  `recipient_missing`; that is expected and visible, not silent.
- Slightly more work per turn (resolution + watcher per entry) — within
  the per-turn budget; "Cost Scales with Drama" — inventory changes are
  exactly when the spend is warranted.

**Neutral**
- Pre-MP / single-player saves are unaffected (empty `player_seats`).
- Existing items_* tests that assert `characters[0]` for single-player
  remain green (single-player resolution is unchanged).

## Alternatives Considered

**Absent-recipient = hard-fail + drop the item.** Cleanest No-Silent-
Fallbacks reading, rejected: a player who was just narrated receiving an
item ending up without it is a continuity break that violates *Yes, And*
and erodes the "good enough to fool a career GM" bar. Telemetry-loud +
defensible attribution achieves the No-Silent-Fallbacks intent (nothing
is hidden) without the UX break.

**Absent-recipient = `characters[0]` / party-leader default.** This *is*
the bug. Rejected by definition.

**Prose-mining / positional inference of the recipient.** Rejected —
fragile state-from-text heuristics are the same anti-pattern as
keyword-gating player input; the narrator already emits structured actor
attribution for beats, so there is no reason to guess.

**Shared / party "unassigned" inventory pool.** Rejected — contradicts
ADR-037 (inventory is per-player `PlayerState`; no shared model exists)
and would be net-new infrastructure, violating reuse-first.

**Scope = `items_gained` only.** Rejected — `lost`/`discarded`/`consumed`
share the identical `characters[0]` defect; a narrower fix knowingly
leaves a twin bug for a future playtest to rediscover. One shared helper
covers all four at no extra design cost.

**New `give_item` tool.** Rejected — net-new tool surface when the
existing structured-output extraction + a `recipient` key on the entries
(mirroring `BeatSelection.actor`) already carries the signal.

## Reuse Justification (pragmatic-restraint)

No new component is introduced. The decision reuses, in order:

1. `BeatSelection.actor` (orchestrator.py:123) — the established
   "narrator names the PC" structured-output convention; `recipient` is
   the same idea on item entries.
2. The `seated_pc_names` validation contract (narration_apply.py:529-585)
   — narrator-supplied actor name validated against
   `snapshot.player_seats.values()`. Reused verbatim for recipients.
3. The `player_seats` seated-PC idiom and the loud-watcher-on-mismatch
   pattern shipped in the sibling XP fix (PR #321).
4. The already-threaded `acting_character_name` in `_apply_*` (used for
   location binding) — the deterministic absent-recipient fallback.
5. `dict[str, Any]` item entries + the existing extraction seam
   (orchestrator.py:2651/2949) — no schema-class change required.

## Implementation Guidance for Dev

Hand to the White Rabbit. TDD, rigid. Branch off `develop`
(`feat/mp-item-recipient-attribution`).

1. **Helper** — add `resolve_item_recipient(snapshot, entry, *,
   narrating_character_name) -> Character` near the item-apply block in
   `sidequest/server/narration_apply.py`. Logic per §2/§3. Pure,
   unit-testable.
2. **Apply seam** — replace the single `character = snapshot.characters[0]`
   (~line 1944) so each of the four lanes resolves its own recipient
   per-entry via the helper (the lanes already iterate entries; move the
   character binding inside the per-entry loop).
3. **Watcher** — emit `inventory` component events: one per applied entry
   (resolved recipient + lane + resolution mode) and the explicit
   `inventory.recipient_missing` on contract violation. Mirror the XP
   fix's `_watcher_publish("state_transition", {...}, component=...)`
   shape.
4. **Tool/prompt contract** — add `recipient` to the items guidance in
   the ADR-102 structured-output instructions (the same file/section that
   documents `items_gained` shape and `BeatSelection.actor`). State it is
   mandatory in multi-PC rounds.
5. **Tests (TDD, all RED first)**:
   - 2-seat MP: `items_gained` with `recipient="Catalina Valentine"`
     lands on Catalina, not `characters[0]`.
   - Same for `items_lost`, `items_discarded`, `items_consumed` (the
     anti-twin-bug guard).
   - Absent recipient → item lands on the narrating socket's PC **and**
     an `inventory.recipient_missing` watcher event fires (assert both).
   - Non-seated `recipient` → same absent-recipient path.
   - Single-player / empty `player_seats` regression guard (lone PC
     still receives; existing behaviour unchanged).
   - **Wiring test** (CLAUDE.md mandate): the helper is invoked from the
     real `narration_apply` path that production `_execute_narration_turn`
     calls — not merely unit-callable.
6. **Save repair (deferred companion)** — after the code lands, the
   `2026-05-17-coyote_star-mp` save's mis-stored items (Station Map Chip,
   ×2 Corvette Scan Data on Ritali) get moved per the now-correct rule,
   WAL-safe with a backup, paralleling the XP save repair already done.

## Decision Record

- Absent-recipient rule: **loud `inventory.recipient_missing` watcher +
  narrating-socket PC**, never `characters[0]`, never drop the item.
  (Keith, 2026-05-18.)
- Scope: **all four item lanes** via one shared helper. (Keith,
  2026-05-18.)
