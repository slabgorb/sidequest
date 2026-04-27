---
parent: sprint/epic-45.yaml
workflow: wire-first
---

# Story 45-8: Notorious-party gating on session player_count

## Business Context

**Playtest 3 evidence (2026-04-19, evropi session):** during
`pumblestone_sweedlewit`'s **solo** narrative turns, the narrator
referenced Rux by name in the prose. Rux was a separate player's
character on a different save slot in the same playtest day; he had
never met `pumblestone` in fiction. The narrator pulled him in because
the world's lore (`evropi/legends.yaml`, `evropi/cultures.yaml`,
`evropi/history.yaml`) names Rux as the only living kobold and the
opening directive (`first_turn_seed`) of every horden-pattern world
talks about "the party gathers." There is no upstream gate that asks
"is this a multiplayer session?" before injecting party-context lore
into the narrator prompt.

For James (narrative-first), this is a **continuity break**: a player
character from a different fiction-line bleeding into a solo run. For
Sebastien (mechanical-first), this is a **prompt-zone leak** that the
GM panel can't see — the narrator faithfully obeyed the prompt; the
prompt was wrong. For Alex (slower reader), the surface symptom is
"who's Rux? was I supposed to know him?" pacing-killing confusion.

ADR-067 (Unified Narrator Agent — single persistent session) makes
this worse, not better: once the narrator's persistent session
ingests "Rux is here" once, the misframe persists across turns. The
fix has to land at injection time, not retroactively.

ADR-085 (port-drift) applies: the world-context (`world_context`) and
opening (`opening_seed` / `opening_directive`) injection paths were
ported from Rust verbatim and never asked the question "is this
multiplayer?" because the Rust era predated the MP turn coordinator.

## Technical Guardrails

### Outermost reachable layer (wire-first seam)

The wire-first gate requires the boundary test to drive a real solo
session through `_handle_connect` → `_chargen_confirmation()` → first
narration turn, and assert the **narrator orchestrator's actual prompt
context** does not contain notorious-party references. A unit test on
a `gate_party_context()` helper alone fails the bar.

Three injection sites must be inspected; each is an outermost-reachable
seam:

1. **Opening directive / seed** —
   `sidequest/server/dispatch/opening_hook.py:73–118`
   (`resolve_opening()`). Returns `(opening_seed, opening_directive)`
   from `world.openings` or `pack.openings`. The seed contains "the
   party gathers" prose verbatim (`horden/openings.yaml:8` confirms
   this). Called from `session_handler.py:1686` (slug path) and
   `session_handler.py:2188` (legacy path).

2. **World context** —
   `sidequest/server/dispatch/culture_context.py:53` (`resolve_culture_reference`).
   Returns the `=== AVAILABLE CULTURES ===` block. For evropi this
   block names Rux directly (`cultures.yaml:583` —
   `"LORE ONLY — Tismenni servant caste, all dead save one: Rux"`).
   Called from `session_handler.py:1738` and `session_handler.py:2198`.

3. **Legends / history** — `genre/loader.py:259` `_load_legends_flexible`
   loads world legends with `notable_figures` (`evropi/legends.yaml:288`
   names Rux). These are not directly injected into the prompt today but
   are reachable via lore RAG (`game/lore_seeding.py`,
   `game/lore_store.py`); ADR-048 governs the RAG store.

### The gate (where to wire it)

The session knows its `player_count` once seats are bound. Two
reasonable signal sources:

- `len(snapshot.player_seats)` — the per-player chargen binding
  (`session_handler.py:2904`) — but this is empty before chargen
  completes, and the opening directive resolves at *connect* time
  (line 1686 / 2188).
- `room.seated_player_count()` (`session_room.py:280`) — the seat
  count at connect time. This is the better signal: it reflects who
  is committed to this slug, and it's evaluated at the same moment
  `resolve_opening()` runs.

The cleanest gate is **at the resolution functions themselves**. Pass
the player count (or a `is_solo: bool`) through `resolve_opening()`
and `resolve_culture_reference()`, and:

- Opening: when solo, pick from a solo-eligible subset of openings
  (`OpeningHook.solo_eligible: bool = True` default — packs that
  declare an opening as MP-only opt out via `solo_eligible: false`).
  When no solo-eligible opening exists, return `None` rather than
  silently defaulting to a party-framed one — SOUL.md "no silent
  fallbacks."
- Culture: solo runs strip cultures whose `description` references
  notorious-party figures. The cleanest hook is a new
  `Culture.solo_eligible: bool = True` field; lore-only cultures
  that exist *because* of a specific NPC (Rux's Tismenni line) opt
  out via `solo_eligible: false` at the content layer.

This is a wire-first story: the gate is **plumbing**, the content
metadata is the source-of-truth flag. Land both together — gate code
without metadata is dead; metadata without gate is silent.

### OTEL spans (LOAD-BEARING — gate-blocking per CLAUDE.md)

Define in `sidequest/telemetry/spans.py` and register `SPAN_ROUTES`
entries:

| Span | Attributes | Site |
|------|------------|------|
| `prompt.party_context_gated` | `gate` (one of `"opening"`, `"culture"`, `"both"`), `player_count`, `mode` (`"solo"` / `"multiplayer"`), `excluded_count` (number of openings/cultures filtered), `genre`, `world` | every call to `resolve_opening()` and `resolve_culture_reference()` — fires on every connect, with `excluded_count=0` on the no-op path |
| `prompt.party_context_leak_prevented` | same + `excluded_ids` (list of opening-hook ids or culture names that were filtered out) | only when `excluded_count > 0` |

`prompt.party_context_gated` MUST fire on every connect (including the
no-op path where every opening/culture is solo-eligible). Sebastien's
GM panel needs the negative confirmation that the gate ran; firing
only on the leak-prevented branch is the bug being fixed in spirit.

### Reuse, don't reinvent

- `OpeningHook` model (`sidequest/genre/models/narrative.py`) gets the
  new `solo_eligible: bool = True` field. Backward-compatible default.
- `Culture` model (`sidequest/genre/models/culture.py`) already
  carries `chargen: bool` (lore-only filter) — `solo_eligible: bool =
  True` is sibling-shape. The existing `chargen` filter at
  `sidequest/server/dispatch/culture_context.py:44` is the precedent for the
  filter pattern.
- `room.seated_player_count()` (`session_room.py:280`) and the
  forthcoming `room.playing_player_count()` from 45-2 are the count
  sources. 45-2 is sibling to this story; both must agree on which
  count is "the player count for prompt-context purposes" (Keith:
  prefer the same source 45-2 picks for the barrier — once a peer
  reaches `playing`, party-context unlocks).
- `_watcher_publish` (`session_handler.py`) is the existing watcher
  emit; pair with the OTEL span via `WatcherSpanProcessor`'s
  `SPAN_ROUTES` mapping.

### Content metadata — required updates

This is a server-side story but it lands two content flags. Where
they go:

- `evropi/cultures.yaml`: the Tismenni-servant culture and any other
  notorious-party-pegged culture get `solo_eligible: false`. Audit
  list compiled from `notable_figures` references in
  `evropi/legends.yaml`.
- `caverns_and_claudes/worlds/horden/openings.yaml`: openings whose
  `first_turn_seed` says "the party gathers" or similar get
  `solo_eligible: false`, OR get rewritten so the seed prose is
  player-count-neutral. **Prefer rewrite where the opening's intent
  is solo-compatible** — most horden openings are solo-fine if the
  prose just stops saying "the party."

### Test harness

- `session_handler_factory(seated_player_count=1)` and
  `session_handler_factory(seated_player_count=2)` — extend the
  fixture in `sidequest-server/tests/server/conftest.py:332` if it
  does not already accept this; the seat count drives the gate.
- `_FakeClaudeClient` at `conftest.py:197` lets the test inspect the
  prompt the orchestrator would have sent — assert "Rux" / "the
  party" tokens are absent in the solo case.

### Test files (where new tests should land)

- New: `tests/server/test_party_context_gate.py` — unit tests for the
  `resolve_opening(player_count)` / `resolve_culture_reference(player_count)`
  signatures and filter behavior.
- New: `tests/server/test_party_context_wire.py` — wire-test:
  solo session connects, drives narration turn, asserts the prompt
  the narrator received does not contain notorious-party tokens.
- Extend: `tests/server/test_culture_context.py` — add solo-eligibility
  cases.

## Scope Boundaries

**In scope:**

- New `solo_eligible: bool = True` field on `OpeningHook`.
- New `solo_eligible: bool = True` field on `Culture`.
- Pass-through `player_count` (or `is_solo` derived from it) into
  `resolve_opening()` and `resolve_culture_reference()`.
- Filter logic: solo runs select only `solo_eligible=True` openings
  and cultures.
- Loud failure when no solo-eligible opening is available (return
  `None` and log a watcher event — SOUL.md "no silent fallbacks").
- New OTEL spans `prompt.party_context_gated` and
  `prompt.party_context_leak_prevented`, registered in `SPAN_ROUTES`.
- Content updates to `evropi/cultures.yaml` and the
  `caverns_and_claudes/horden` openings (whichever subset is
  contaminated). Prefer rewriting prose to be player-count-neutral
  where the opening is solo-compatible.
- Wire-first boundary test: solo connect → narration turn → prompt
  inspection; asserts no notorious-party leak. Multiplayer connect
  on the same world → leak permitted.

**Out of scope:**

- The lore RAG store (`game/lore_store.py`, `game/lore_embedding.py`,
  `game/lore_seeding.py`). RAG-retrieved fragments may still surface
  notorious figures; that's a separate ADR-048 concern — the in-prompt
  zone gate this story implements is the load-bearing fix for the
  reported bug. File a follow-up note if the wire-test surfaces RAG
  leakage.
- Reworking how the narrator's persistent session (ADR-067) handles
  prior-context staleness. The gate prevents re-injection on solo
  sessions; cleaning up an already-poisoned session is its own
  problem.
- Multiplayer-specific party-context shaping (e.g., omitting a peer's
  notable-figure references when their PC isn't co-present). That's
  the perception rewriter (ADR-028) territory.
- UI changes. The gate is server-side; players see "no leak" not "a
  new control."

## AC Context

1. **Solo connect to a world with notorious-party context produces a
   prompt with no notorious-party tokens.**
   - Wire-test (the `pumblestone` regression): solo session,
     `seated_player_count == 1`. Drive `_handle_connect` →
     `_chargen_confirmation()` → first narration turn. Capture the
     prompt the orchestrator received. Assert the prompt does NOT
     contain `"Rux"` or `"the party"` tokens (or the equivalent
     content-flagged strings).
   - Negative test: same scenario with `seated_player_count == 2` —
     prompt MAY contain those tokens; assertion inverts.

2. **`resolve_opening(player_count=1)` returns only solo-eligible
   openings; returns `None` (with watcher event) when none exist.**
   - Test: pack with mix of openings (some `solo_eligible=False`,
     some `True`) — solo path returns from the `True` subset only.
   - Test: pack with all openings `solo_eligible=False` — solo
     returns `None`, `prompt.party_context_gated` fires with
     `excluded_count == len(openings)`.
   - Negative: `player_count=2` returns from the full set.

3. **`resolve_culture_reference(player_count=1)` strips cultures
   whose `solo_eligible=False`.**
   - Test: pack with mixed cultures — solo path emits a
     reference block excluding the `False` ones.
   - Test: empty result (every culture `solo_eligible=False`) returns
     `""` (existing pattern at `culture_context.py:46`), and
     `world_context` becomes `None` at the call site.

4. **OTEL `prompt.party_context_gated` fires on every connect.**
   - Test: 3 connects (1 solo no-leak, 1 solo with-leak-prevented, 1
     MP) — span fires 3 times (once per
     `resolve_opening`/`resolve_culture_reference` call, so 6 spans
     total across the 3 connects), each with the correct `mode`,
     `player_count`, and `excluded_count`. Sebastien's lie-detector
     requires the firing-on-no-op case.
   - Test: `prompt.party_context_leak_prevented` fires only when
     `excluded_count > 0`, with the correct `excluded_ids` list.

5. **Content audit lands the metadata.**
   - Test: load `evropi/cultures.yaml` and assert the Tismenni
     servant culture has `solo_eligible: false`. (Pin to the bug
     evidence — Rux is the leak; his culture is the gate.)
   - Test: load every `caverns_and_claudes/horden/openings.yaml`
     opening and assert each is either `solo_eligible: true` (prose
     reads cleanly) OR `solo_eligible: false`. No mid-state.
