---
parent: "75"
---
# Story 75-2 Context — Port budgeted NPC working-set selection (npc_context.rs)

## Business Context

The narrator must read as a living world (SOUL: *Living World*, *Diamonds and
Coal*). Today, every narrator turn dumps the **entire** `snapshot.npc_pool`
verbatim into the prompt — present or absent, relevant or not. As a session
accretes cast, the roster blob grows without bound and crowds out the prompt
budget, while relevance is never consulted. The narrator sees *everyone* every
turn.

The Rust origin (`github.com/slabgorb/sidequest-api`,
`npc_context.rs:11-86` `build_npc_registry_context_budgeted`) solved this by
**selection, not eviction**: scene-present NPCs got full profiles, off-stage
NPCs got name+role, and when the player referenced no NPC, only compact names.
Python dropped this in the port. This story restores it.

**This is a RESTORATION port, and it is the foundation of Epic 75.** Per
ADR-118 (Universal Retrieval Layer), **75-2's selection *is* the deterministic
"floor"** of the per-turn floor-and-fill retrieval that 75-4→75-8 build on top.
The floor guarantees that the entity physically present this turn is *never*
dropped from context, even when semantic retrieval would miss it. Get the floor
wrong and the whole universal-retrieval waterfall stands on sand.

**Supersedes 72-6.** The "cap the pool" / eviction framing was rejected as a
*Diamonds-and-Coal / Living World* violation. Nothing is forgotten; the full
roster persists in the snapshot. Only the relevant working-set enters the
prompt.

**Whom it serves:** Sebastien and Jade (mechanics-first) feel the absence of a
responsive NPC cast; an unbounded roster blob degrades narrator quality for the
whole table. The OTEL span (below) is a Keith/dev observability tool — the GM
panel lie-detector — *not* a player-facing surface.

## Technical Guardrails

The canonical, code-level technical approach lives in the **session file**
(`.session/75-2-session.md`, higher spec authority than this document). These
are the constraints test design must enforce:

- **Repo / language:** `sidequest-server` (Python). Base branch: `develop`.
  Apply the `python.md` lang-review checklist.
- **Selection, never eviction (AC-2 / ADR-014):** the full roster stays in the
  snapshot. Bounding is by *prompt selection* only. A test must prove no NPC is
  removed from the underlying snapshot structure.
- **Three tiers, by recency:**
  - **Full profiles** — scene-present NPCs: `last_seen_turn >= current_turn - 2`.
  - **Brief** — off-stage pool members + off-stage stateful NPCs: name + role only.
  - **Compact names only** — used *when the player referenced no NPC this turn*.
- **Boundary discipline (test-paranoia target):** the recency threshold is
  `>= current_turn - 2`. Pin the exact boundary — an NPC at `last_seen_turn ==
  current_turn - 2` is scene-present (full); at `current_turn - 3` it is
  off-stage (brief). Off-by-one here corrupts the floor.
- **No silent fallback on missing `last_seen_turn`** (SM risk flag #2, *No
  Silent Fallbacks*): if an NPC lacks `last_seen_turn`, the code must fail loud
  or apply an **explicit, documented default** — never silently treat unset as
  scene-present or as turn 0. A test must assert the chosen behavior.
- **Wired into BOTH consumers (SM risk flag #1, project wiring rule):** the
  selection must reach the narrator through *both* drop points —
  `session_helpers.py` `_build_turn_context` (~:1179) **and**
  `orchestrator.py` `register_npc_roster_section` (~:682 / roster registration).
  At least one **integration/wiring test** must prove the budgeted working-set
  is reachable from a production turn-build path, not merely unit-correct in
  isolation.
- **OTEL span is mandatory (AC-3, ADR-118 D5, project OTEL principle):** a span
  must fire on **every** narrator turn recording `full_count`, `brief_count`,
  `compact_only`, and `total_pool` (considered-vs-selected, with tier). This is
  how the GM panel proves the budgeting engaged rather than Claude improvising
  the roster. A test must assert the span fires with correct tier counts.
- **Meaningful assertions only:** no `assert x is not None` where the value is
  the real contract — assert the *tier membership and counts*.

## Scope Boundaries

**In scope:**
- The `build_npc_working_set` selection function (recency classification into
  full / brief / compact tiers).
- New `TurnContext` fields for the budgeted tiers and the
  `register_npc_roster_section` rendering change.
- The OTEL working-set-selection span.
- Wiring into the live turn-build path (both consumers).

**Out of scope (do not let tests demand these):**
- **Semantic retrieval / embedding / vector search.** That is the *fill*
  (75-5), not the floor. 75-2 is pure recency/reference selection — no
  `EntityCard`, no `LoreStore`, no MiniLM.
- **`EntityCard` model and per-type projectors** — that is 75-4.
- **Locations and factions** — 75-2 is NPC-only. Locations/factions enter at
  75-4+.
- **Accretion / lore re-feed** — that is 75-1 (already merged).
- **Pool-member `last_seen_turn` tracking:** pool members (`NpcPoolMember`)
  carry no recency field in the current model; treat all pool members as
  off-stage (brief/compact) by default. Adding recency tracking to pool members
  is explicitly *future work*, not this story. (Log a deviation only if the test
  strategy needs to assert this default.)

## AC Context

The four ACs (verbatim source: session file `## Acceptance Criteria`) and what
each demands of test design:

1. **Budgeting function implemented** — ports `npc_context.rs:11-86`: select a
   working-set (scene-present full, others name+role, none-referenced compact)
   instead of loading `npc_pool` verbatim.
   *Tests:* `test_npc_working_set_budgeting_classifies_by_recency` (3 present /
   2 off-stage → 3 full, 2 brief) and the recency-boundary edge cases above.

2. **No eviction** — full pool persists in the snapshot; bounding is
   prompt-selection only.
   *Tests:* assert the source snapshot roster is unchanged in size after
   selection; assert pool members never appear in `full_profiles`
   (`test_npc_pool_members_always_brief_or_compact`).

3. **OTEL observability** — span records considered-vs-selected with tier
   (full/brief/compact) so the GM panel can verify selection fired.
   *Tests:* assert the span fires with correct `full_count` / `brief_count` /
   `compact_only` / `total_pool`.

4. **Wiring test** — a pool of N NPCs with only k scene-present
   (`last_seen_turn >= turn - 2`) yields a prompt section with k full profiles
   and the rest abbreviated, *through the real turn-build path*.
   *Tests:* `test_npc_budgeting_wired_into_turn_context` — build a turn, call
   `_build_turn_context`, assert non-empty `npc_pool_budgeted` / `npc_pool_brief`
   and that the OTEL span fired.

**Negative / paranoia cases test design should add (beyond the AC minimum):**
- Empty pool → no crash, span fires with zeroes.
- All NPCs off-stage + player referenced an NPC → full=0, all brief (not
  compact — compact is *only* the no-reference case).
- Player referenced an NPC that is off-stage → that reference does not promote
  an off-stage NPC to full unless recency qualifies (clarify against session
  spec; log a deviation if behavior is ambiguous).
- Missing `last_seen_turn` → asserted explicit behavior (no silent default).

## Assumptions

- The recency window `N = 2` matches the Rust origin and the session spec; it is
  a tunable constant, not a magic literal scattered across call sites (extract
  per project rules).
- "Player referenced no NPC this turn" is determined by an existing
  NPC-mention/reference detection upstream; 75-2 consumes that signal and does
  not reimplement reference detection.
- ADR-118 is the design of record; this story implements only its **floor**, and
  the retrieval *contract* it feeds is defined there (D4) — 75-2 need not know
  about fill.

---
_Authored by Neo (Architect) during RED-phase context recovery, 2026-05-31.
Sources: ADR-118 (D4 floor role, composition waterfall), epic-75 context
(scout audit), and the session file's canonical technical approach + ACs.
The session file remains the higher-authority spec; this document is the
test-strategy lens TEA's gate requires._
