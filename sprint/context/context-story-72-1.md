---
parent: context-epic-72.md
workflow: tdd
---

# Story 72-1: Revive dormant NPC development pipeline

## Business Context

ADR-014 (Diamonds and Coal) established the project's promotion doctrine: an
object deepens from disposable "coal" to load-bearing "diamond" **when the
player shows genuine interest** — examines it, asks about it, engages with it.
ADR-020 (NPC Disposition System) is the NPC analogue: an NPC's attitude toward
the party is supposed to **evolve through repeated interaction**, drifting along
the numeric disposition axis (`>10` friendly, `-10..10` neutral, `<-10`
hostile).

The NPC development pipeline currently runs **backwards from both ADRs**.
Promotion from a regenerable `NpcPoolMember` scaffold to a stateful `Npc`, and
any escalation of an `Npc`'s depth, fires **only on mechanical necessity** — a
status mutation that needs a `CreatureCore`, or a combat/Monster-Manual stat
block (`Session._npc_from_patch`). It **never fires on player interest**.
Concretely:

- `Npc.resolution_tier` is hard-initialized to `"spawn"`
  (`session.py:177`) and **never escalates**, regardless of how many turns the
  party spends talking to the NPC.
- `Npc.non_transactional_interactions` is **declared but never incremented**
  (`session.py:178`).
- Disposition drift happens **only** via explicit narrator `npc_attitudes`
  deltas in a world patch (`session.py:1392`), never as an emergent function of
  sustained engagement.

The lived consequence: an NPC the playgroup talks to for ten turns stays a flat
`"spawn"`-tier scaffold with a frozen disposition, unless they happen to get hit
in combat. The forever-GM (Keith) and the mechanics-first players (Sebastien,
Jade) experience this as the engine **silently failing to remember who matters**
— the narrator improvises depth the engine never actually tracked. Per the
epic's governing rule, **every leg needs OTEL**: each development decision must
emit a watcher span so the GM panel (the lie detector) can prove the engine —
not the narrator's prose — drove the NPC's advancement. This story revives the
three dormant legs (interest increment → tier escalation → disposition drift),
each instrumented, so interest-driven NPC development becomes a real,
observable, mechanically-grounded subsystem that mirrors ADR-014 rather than
inverting it.

## Technical Guardrails

**Primary seam — the interest signal lives at the existing `npcs_hit` branch.**
`_apply_npc_mentions` (`sidequest/server/narration_apply.py:1171`) already
performs the 3-step case-folded name lookup on every narrator NPC cite. Step 1
(`narration_apply.py:1221-1255`) is the `npcs_hit` branch: the cited name
resolved to an active stateful `Npc`. **This branch is the canonical "player /
narrator engaged this NPC this turn" signal** — it already updates
`last_seen_location` / `last_seen_turn` and fires `npc_referenced_span(
match_strategy="npcs_hit")`. The development tick (increment → escalate → drift)
belongs **here**, alongside the existing last-seen stamping, so it rides the
same per-turn engagement event the rest of the pipeline already trusts. Do
**not** invent a new dispatch path or a new "interest" message type; wire onto
the seam that already fires once per engaged NPC per turn.

**Fields to activate (do not add new fields):**
- `Npc.non_transactional_interactions: int = 0` (`session.py:178`) — increment
  on each non-transactional engagement.
- `Npc.resolution_tier: str = "spawn"` (`session.py:177`) — escalate past
  `"spawn"` at interaction-count thresholds. Keep the value a plain string on
  the wire (it serializes into snapshots and OTEL).
- `Npc.disposition: Disposition` (`session.py:140`) — drift via the
  `Disposition` wrapper. **Construct a new `Disposition(new_value)`** — the
  constructor clamps to ±100 (`disposition.py:147`); do not mutate
  `.value` in place past the clamp. Read the qualitative band with
  `.attitude()` (`disposition.py:149`), which honors genre-configurable
  thresholds (`disposition.py:113`).

**Disposition / attitude rules (ADR-020 — `sidequest/game/disposition.py`):**
- Bands are `value > friendly_at` → friendly, `value < hostile_at` → hostile,
  else neutral. Defaults `friendly_at=10` / `hostile_at=-10`. **Never hardcode
  ±10** in this story's logic — call `Disposition.attitude()` so genre-pack
  threshold overrides (`configure_attitude_thresholds`) still apply. A
  band-crossing test must construct its `Disposition` and read `.attitude()`,
  not compare integers to literals.

**OTEL — follow the existing span shapes exactly.** All NPC spans live in
`sidequest/telemetry/spans/npc.py`; disposition shifts have their own span in
`sidequest/telemetry/spans/disposition.py`. New development-tick span must
register a `SpanRoute` in `SPAN_ROUTES` (event_type `state_transition`) the same
way `SPAN_NPC_REFERENCED` / `SPAN_DISPOSITION_SHIFT` do, and provide a
`@contextmanager` opener mirroring `npc_referenced_span`. For the disposition
leg, **reuse the existing `disposition.shift` span contract** — it already
carries `before`/`after`/`before_attitude`/`after_attitude`/`crossed`
(`disposition.py:17-26`; emitted at `session.py:1416`). The development tick
should emit, per engaged NPC: `non_transactional_interactions` (new count),
`resolution_tier` old → new, and the disposition before/after + `crossed`
(parallel to the `disposition.shift` route, per the epic's "72-1: a
development-tick span" mandate). Attribute key for the NPC name is **`npc_name`**
— `name` is an OTEL-reserved span attribute (see the note at `npc.py:217`).

**What NOT to touch:**
- Do **not** modify `_promote_pool_member_to_npc` (`narration_apply.py:916`) or
  the load-time reconcile — that is **72-2**.
- Do **not** change the warn-only drift detector `_detect_npc_identity_drift`
  or the pool-hit additive upsert (`narration_apply.py:1271-1278`) — that is
  **72-7**.
- Do **not** seed OCEAN or `belief_state` — that is **72-9**.
- Do **not** touch the born-hostile `disposition=-20` default
  (`session.py:1533`) — that is **72-5**.
- Do **not** add pool-cap / prune logic — that is **72-6**.

**Integration read point:** `run_npc_agency`
(`sidequest/agents/subsystems/npc_agency.py:40`) already reads
`npc_hit.disposition.attitude()` and surfaces it in its directive. The newly
drifted disposition and escalated tier become readable here **for free** once
they're written onto the `Npc` — no change required in `npc_agency.py` for this
story, but the development tick must mutate the same `Npc` instance that
`run_npc_agency` resolves so the depth is visible to the next turn's directive.

**Server test rule (CLAUDE.md "No Source-Text Wiring Tests"):** every AC below
is verified by **driving the real `_apply_npc_mentions` flow over a synthetic
snapshot fixture and asserting on emitted spans / mutated `Npc` state** — never
by grepping production source for a call site. The wiring test is an OTEL
span-fired assertion (drive an `npcs_hit` mention, assert the development-tick
span fired and the `Npc` mutated), per the canonical fixture-driven shape.

## Scope Boundaries

**In scope:**
- Increment `Npc.non_transactional_interactions` on each non-transactional
  engagement (the `npcs_hit` branch of `_apply_npc_mentions`).
- Escalate `Npc.resolution_tier` past `"spawn"` at defined interaction-count
  thresholds.
- Apply emergent disposition drift on sustained engagement, using the
  `Disposition` wrapper + `.attitude()` band logic (ADR-020).
- Emit an OTEL watcher span on **each** of the three legs (increment, tier
  escalation, disposition drift), reusing the `disposition.shift` span contract
  for the drift leg and adding a development-tick span for the
  increment/escalation legs.
- One fixture/span-driven wiring test proving the development tick is reachable
  from the real narration-apply production path.

**Out of scope (sibling stories — do NOT absorb):**
- **72-2** — preserve disposition on pool→Npc promotion + load-time reconcile
  of `npcs` ↔ `npc_pool`. This story does not touch promotion or migration.
- **72-7** — make identity drift authoritative (overwrite canonical
  pronoun/role on re-mention). This story leaves the warn-only drift detector
  and additive upsert exactly as-is.
- **72-9** — wire OCEAN + scenario `belief_state` onto narrator-invented NPCs.
  This story drifts disposition only; it does not seed personality or beliefs.
- Also out: 72-3 (`manual_origin`), 72-4 (namegen routing), 72-5 (born-hostile
  default), 72-6 (pool cap/prune), 72-8 (encounter-presence last-seen stamp),
  72-10 (gate-ordering assert).

## AC Context

> No explicit ACs were authored; the title is the spec. The following are
> derived, each testable behaviorally / via span assertion (server rule: no
> source-text wiring tests). "Transactional" engagement = combat strike, status
> mutation, MM/stat-block materialization (the paths that already promote on
> mechanical necessity); "non-transactional" = a narrator NPC mention that
> resolves to an existing `Npc` via the `npcs_hit` branch without a mechanical
> mutation. The thresholds named below (`spawn` < `acquaintance` < `established`)
> are the recommended ladder; TEA/Dev may rename the tiers, but the **escalation
> behavior, monotonicity, and span emission are load-bearing** and must hold.

### AC1 — Interest signal increments on non-transactional engagement
**Must be true:** when a narrator mention resolves to an existing `Npc` through
the `npcs_hit` branch of `_apply_npc_mentions`, that `Npc`'s
`non_transactional_interactions` increments by exactly 1 for that turn.
**Edge cases:** multiple distinct NPCs mentioned in one turn each increment
independently (per-NPC counter, not a global tick). The same NPC named twice in
one turn's mention list increments **once per engagement event** — Dev to pick
and document the de-dup rule; the test pins whichever rule is chosen so it can't
silently regress. A pool-only (`pool_hit`) or `invented` mention does **not**
increment (those NPCs have no stateful `Npc` to carry the counter).
**Test verifies:** build a synthetic `GameSnapshot` with one `Npc` already in
`snapshot.npcs`; drive `_apply_npc_mentions` with a mention of that NPC's name;
assert the `Npc.non_transactional_interactions` went from N to N+1. A second
test drives a `pool_hit`/`invented` mention and asserts no counter change on any
`Npc`.

### AC2 — resolution_tier escalates past "spawn" at interaction thresholds
**Must be true:** as `non_transactional_interactions` crosses defined
thresholds, `resolution_tier` advances monotonically up the ladder (e.g.
`spawn → acquaintance` at the first threshold, `acquaintance → established` at
the second). It never escalates on a single transactional combat hit alone
(that path is unchanged by this story) and never **de**escalates.
**Edge cases:** below the first threshold the tier stays `"spawn"`. Exactly-at-
threshold escalates (define `>=` vs `>` and pin it in the test). An `Npc`
already at the top tier stays there (no overflow, no error). Thresholds must be
named constants, not magic literals scattered in the branch.
**Test verifies:** drive enough `npcs_hit` mentions across simulated turns to
cross each threshold; assert `resolution_tier` equals the expected band at each
step and is monotonic non-decreasing across the sequence; assert a single
mention below threshold leaves it `"spawn"`.

### AC3 — Disposition drifts emergently on sustained engagement (ADR-020)
**Must be true:** sustained non-transactional engagement nudges the `Npc`'s
`Disposition.value` (e.g. a small positive drift per qualifying engagement),
and the qualitative `attitude()` band updates accordingly when a numeric
threshold is crossed. The drift is applied by **constructing a new
`Disposition`** (clamped ±100), not by unbounded mutation, and band derivation
goes through `Disposition.attitude()` so genre-pack threshold overrides apply.
**Edge cases:** drift respects the ±100 clamp (no overflow). Band-crossing
(`neutral → friendly`) is detected via attitude identity, not a `|delta|`
literal — so a pack with custom `friendly_at` still flips at its own boundary.
Drift sign/magnitude is a deliberate design choice (Dev to document: e.g.
neutral engagement warms slightly); the test pins the chosen rule. Drift must
**not** fire on `pool_hit`/`invented` (no stateful `Npc`).
**Test verifies:** drive repeated `npcs_hit` mentions; assert `disposition.value`
moved in the expected direction and that `attitude()` flips bands at the
genre-configured boundary (set a non-default threshold via
`configure_attitude_thresholds` in one test to prove the boundary is honored,
not hardcoded). Assert the value never exceeds ±100.

### AC4 — Development-tick OTEL span fires on the increment / escalation legs
**Must be true:** each development tick emits a watcher span (registered in
`SPAN_ROUTES`, event_type `state_transition`, component in the `npc*` family)
carrying at minimum: `npc_name`, the new `non_transactional_interactions` count,
and `resolution_tier` old → new. The span uses `npc_name` (not the reserved
`name` attribute) and routes through `WatcherSpanProcessor` so the GM panel sees
it.
**Edge cases:** the span fires on **every** qualifying engagement, including
ticks that increment the counter but do **not** cross a tier threshold (the GM
panel must see the engine "counting," not only the rarer escalations). When an
escalation does occur, old and new tier differ in the span; when it doesn't,
old == new.
**Test verifies:** use the test span/watcher capture harness; drive an
`npcs_hit` mention; assert exactly one development-tick span fired with the
expected `npc_name`, incremented count, and tier old/new fields. This is also
the story's **wiring test** — it proves the new tick is reachable from the real
`_apply_npc_mentions` production path (fixture-driven, span-asserted; no
source-text grep).

### AC5 — Disposition-drift leg emits the disposition.shift span contract
**Must be true:** whenever AC3's drift changes an `Npc`'s disposition, a
`disposition.shift` span fires carrying `npc_name`, `delta`, `before`, `after`,
`before_attitude`, `after_attitude`, and `crossed` — the exact contract already
registered at `disposition.py:17-26` and emitted at `session.py:1416` for
narrator-driven `npc_attitudes` deltas. `crossed` is `True` iff
`before_attitude != after_attitude`.
**Edge cases:** an engagement that nudges the value **within** a band emits the
span with `crossed=False` (intra-band drift is still observable). A drift of net
zero (e.g. clamped at ±100) should either emit with `delta=0`/`crossed=False` or
be skipped — Dev to choose and pin it; the GM panel must not show phantom
shifts. Reuse the existing span, do not fork a new disposition span shape.
**Test verifies:** drive engagement that crosses a band; assert a
`disposition.shift` span fired with `crossed=True` and matching
before/after attitudes. A second test drives intra-band drift and asserts
`crossed=False` with non-zero `delta`.

### AC6 — Transactional-only paths remain unchanged (regression guard)
**Must be true:** the existing mechanical-necessity promotion paths
(`_promote_pool_member_to_npc`, `Session._npc_from_patch`, combat strike) still
behave exactly as before — this story **adds** the interest leg without
altering the transactional leg. A combat-only encounter that never produces an
`npcs_hit` narration mention does not spuriously increment
`non_transactional_interactions` or escalate tier.
**Test verifies:** drive a transactional materialization (MM patch / status
mutation) with no narrator `npcs_hit` mention; assert
`non_transactional_interactions` stays 0 and `resolution_tier` stays `"spawn"`
(the development tick is gated to the non-transactional engagement signal only).

## Assumptions

- **The `npcs_hit` branch is the interest signal.** A narrator mention resolving
  to an existing stateful `Npc` (step 1 of `_apply_npc_mentions`) is treated as
  the canonical "this NPC was engaged this turn" event. This is the only path
  the development tick hooks; pool-only and invented mentions are explicitly out
  (they have no `Npc` to carry counters). If TEA judges that a richer interest
  signal is needed (e.g. distinguishing player-directed engagement from
  incidental name-drops), that is a larger design change and should be raised
  rather than silently widened here.
- **Tier ladder and thresholds are Dev's to name, behavior is fixed.** The
  recommended ladder is `spawn → acquaintance → established`; exact tier names
  and numeric thresholds are implementation choices, but they must be named
  constants, monotonic, and span-observable. Tests pin whatever is chosen.
- **Drift magnitude/sign is a documented design choice.** A small positive warm
  on neutral engagement is the assumed default (sustained friendly contact
  deepens rapport, per ADR-020's "evolves through interaction"), but the precise
  delta and any context-sensitivity is Dev's call, documented and test-pinned.
- **Reuse over reinvention for spans.** The disposition leg reuses the live
  `disposition.shift` span; only the increment/escalation legs need a new
  development-tick span. No new disposition span shape is introduced.
- **`Disposition` is a value type with ±100 clamping** (`disposition.py:147`)
  and genre-configurable bands (`configure_attitude_thresholds`). All drift goes
  through the constructor and all band reads through `.attitude()` — no integer
  literal band comparisons.
- **Dependency:** ADR-020's disposition→attitude layer and the
  `disposition.shift` span are already live (Stories 50-10/50-11/50-13); this
  story consumes them, it does not build them. ADR-014 is reference doctrine,
  not a code dependency.
- **No persistence/schema change.** All three fields
  (`non_transactional_interactions`, `resolution_tier`, `disposition`) already
  exist on `Npc` and round-trip through the snapshot; reviving them needs no
  Alembic migration.
