---
id: 100
title: "Journal Pipeline Coherence — Footnotes, KnownFacts, JOURNAL_RESPONSE, and the Scenario Clue Hook"
status: accepted
date: 2026-05-13
deciders: ["Keith Avery (Bossmang)", "Major Margaret Houlihan (Architect)"]
supersedes: []
superseded-by: null
related: [39, 53, 57, 76, 87]
tags: [agent-system, frontend-protocol, npc-character]
implementation-status: live
implementation-pointer: "sidequest-server/sidequest/server/websocket_session_handler.py (consume_clue_footnotes) + handlers/journal_request.py (JOURNAL_REQUEST) + ui useStateMirror.ts"
---

# ADR-100: Journal Pipeline Coherence — Footnotes, KnownFacts, JOURNAL_RESPONSE, and the Scenario Clue Hook

> This ADR is **not a redesign**. It is a **map** of an ecosystem that already has five live or half-live pieces and one dark piece. It exists because Keith's playgroup reads the journal every turn — James cites footnotes back to the table, Alex re-reads entries to scaffold her turn, Sebastien wants OTEL proof the entries are real — and the system as currently wired tells a partial lie. This document names every component, every seam, and every known falsehood, then schedules the work that closes the gaps.

## Context

The journal is one of the most player-facing surfaces in SideQuest. It is the persistent record of what the party has learned, and it is consulted between turns more than any other panel except the character sheet. Three concerns converge on it:

1. **Narrator output.** Every turn, the narrator emits structured footnotes in its `game_patch` JSON block. These are the inflow.
2. **Server-side knowledge.** Each `Character` carries a `known_facts: list[KnownFact]` that is the canonical, persistent record of what that character knows.
3. **Scenario clue graph.** Mystery scenarios bind a `ScenarioState` with a `ClueGraph`; players advance the mystery by discovering structured clues.

These three concerns share the journal as their surface, but the pipeline that connects them is currently **layered, partly live, and incompletely wired** — and parts of it actively misrepresent state to the player.

### The discovery that prompted this ADR

While scoping story **50-5** (*"Scenario: wire `discover_clue` to narration consumption"*), the architect found that:

- `ScenarioState.discover_clue()` exists with OTEL span emission (`SPAN_SCENARIO_ADVANCE`) but has **zero production callers** in either the Python tree or the historical Rust reference.
- The `Footnote` model (ADR-039) carries a `fact_id` field that the UI's `KnowledgeJournal` already uses as a dedupe key — but **`useStateMirror.ts` manufactures its own synthetic id and ignores any narrator-supplied `fact_id`**.
- `KnownFact.source` and `KnownFact.learned_turn` are marked `P5-deferred: used by scenario system` (`game/character.py`) — **these fields were designed for scenario clue discoveries that have never been wired**.
- The `JOURNAL_REQUEST` / `JOURNAL_RESPONSE` protocol message types exist in `protocol/enums.py`, and the UI is fully prepared to consume `JOURNAL_RESPONSE` with the canonical knowledge model (`useStateMirror.ts`) — but **no server handler emits `JOURNAL_RESPONSE`**.
- Every footnote that reaches the UI is rendered with `confidence: 'Suspected'` because **`useStateMirror.ts` hardcodes the value** regardless of category, source, or whether a scenario is bound. The "Suspected" label players see in production is a UI default, not a mechanic — a load-bearing lie.

What was scoped as a one-story wiring job is in fact a keystone in a partially-built arch. This ADR names the arch.

## Decision

Treat the journal pipeline as **one coherent subsystem with five named components and three named seams**. Every story that touches any component must cite this ADR. Every component declares its current implementation status. Every seam declares whether it is wired, half-wired, or dark, and which feeder story closes it.

### The five components

| # | Component | Location | Status |
|---|-----------|----------|--------|
| 1 | **Narrator footnote emission** — fenced `game_patch` JSON with `footnotes[]` (`marker, summary, category, is_new, fact_id`). | `sidequest-server/sidequest/agents/orchestrator.py+`, prompt at `agents/prompt_framework/core.py` | **Live.** Governed by ADR-039. The footnote field set is current; the `lore_established` → `footnotes` rename happened with ADR-039's 2026-05-02 revival. |
| 2 | **Footnote forwarding to UI** — extracted footnotes coerced into typed `Footnote` models, packaged into `NarrationPayload.footnotes`, broadcast through `EventLog` + `ProjectionFilter`. | `sidequest-server/sidequest/server/websocket_session_handler.py` | **Live.** This is the per-turn ephemeral channel. |
| 3 | **Server-side `Character.known_facts`** — the canonical, persistent journal stored per character. `KnownFact(content, confidence, source, learned_turn)`. | `sidequest-server/sidequest/game/character.py`, mutated via `WorldStatePatch.discovered_facts` at `sidequest-server/sidequest/game/session.py` | **Live for narrator-emitted facts.** `source` and `learned_turn` are explicitly marked P5-deferred for the scenario system — they have valid defaults but no scenario writer has ever populated them. |
| 4 | **UI ephemeral knowledge build** — `useStateMirror` accumulates a `knowledge[]` array from each turn's `NarrationPayload.footnotes`. | `sidequest-ui/src/hooks/useStateMirror.ts` | **Live but lying.** Manufactures synthetic `fact_id` from `${turnCounter}-${marker ?? index}` and ignores narrator-supplied `fact_id`. Hardcodes `source: 'Observation'` and `confidence: 'Suspected'` regardless of input. |
| 5 | **Scenario clue graph + state** — `ClueGraph` model loaded from genre pack scenarios, bound at session-init into `snapshot.scenario_state`. `ScenarioState.discover_clue(clue_id)` exists and emits `SPAN_SCENARIO_ADVANCE`. | `sidequest-server/sidequest/game/scenario_state.py`, `sidequest-server/sidequest/genre/models/scenario.py`, bind at `sidequest-server/sidequest/server/dispatch/scenario_bind.py` | **Data layer live, callers dark.** No production code calls `discover_clue()`. Closed by story 50-5. |

### The three seams

| Seam | What it does | State | Owning story |
|------|--------------|-------|--------------|
| **A. Footnote → Scenario clue** | When a footnote's `fact_id` matches a node in `snapshot.scenario_state.clue_graph`, call `discover_clue(fact_id)`. Fires `SPAN_SCENARIO_ADVANCE`. | **Dark.** | **50-5** (this restoration plan's first story). |
| **B. Scenario clue → KnownFact** | When a scenario clue is discovered, mint a `KnownFact(content=footnote.summary, confidence='Discovered', source='ScenarioClue', learned_turn=current_turn)` on the active character. Lights up the P5-deferred fields. | **Dark.** | **50-5** (bundled — the seam belongs to the same dispatch hook). |
| **C. `KnownFact` → `JOURNAL_RESPONSE` → UI** | Server handler responds to `JOURNAL_REQUEST` by emitting `JOURNAL_RESPONSE` populated from `character.known_facts`. UI replaces synthetic ids with real `fact_id`s and respects `confidence` / `source` from the canonical journal. | **Half-wired** — protocol enum exists, UI consumer exists, no server handler, UI ignores narrator-supplied `fact_id`s when present. | **Feeder story** (separate; closes the playgroup-visible "Suspected" lie). |

### Naming the known falsehoods

Two falsehoods are visible to the player today. This ADR names them and obligates the feeder manifest to retire them:

1. **The "Suspected" label is constant.** Every journal entry players see is rendered as `Suspected` because of `useStateMirror.ts`. The label has no mechanical meaning today. Until the C-seam lands, the label *is the truth* — there is no other source. After C, "Suspected" must come from the server's `KnownFact.confidence` or be removed entirely.
2. **Footnote dedupe is per-turn, not per-fact.** The UI's `seenFactIds` set uses synthetic ids, so two narrations referencing the same fact on different turns produce two journal entries. The narrator's `fact_id` field — designed to prevent exactly this — is ignored.

Both are documented here as **load-bearing UI debt**, not bugs to chase casually. They are part of the contract the C-seam closes.

### Scope of story 50-5 under this ADR

Story 50-5 carries **two seams** (A and B above), in a single dispatch hook in `websocket_session_handler.py` immediately after `forwarded_footnotes` is built:

- **Seam A:** for each forwarded `Footnote`, if `snapshot.scenario_state` is bound and `fn.fact_id` matches a `ClueNode.id` in `scenario_state.clue_graph`, call `snapshot.scenario_state.discover_clue(fn.fact_id)`. The span fires from inside `discover_clue` — story exit criterion satisfied.
- **Seam B:** on the same match, append a `KnownFact(content=fn.summary, confidence='Discovered', source='ScenarioClue', learned_turn=snapshot.turn_manager.interaction)` to the active player's character's `known_facts`. This finally exercises the P5-deferred fields and makes the canonical server-side journal aware of the discovery.

Both seams happen in the same loop. They share a single integration test fixture (one scenario, one narrator turn with a matching `fact_id`, two assertions: span fired AND `KnownFact` minted with the right `source`/`confidence`).

### What 50-5 does *not* do under this ADR

- **No DAG enforcement.** Orphan discoveries (a clue whose `requires[]` is unmet) are explicitly allowed. That gate is **story 50-6**, already in backlog.
- **No `JOURNAL_REQUEST` handler.** The C-seam is a feeder story, not 50-5's job.
- **No UI changes.** Per-turn footnote flow is unchanged; UI continues to render `Suspected` from the hardcode. The C-seam feeder retires that label.
- **No belief state mutation, no gossip propagation, no accusation evaluator.** Those are ADR-053 restoration items at ADR-087 P2.
- **No new wire message.** All inflow rides existing `NarrationPayload.footnotes`. The C-seam uses the already-defined `JOURNAL_REQUEST`/`JOURNAL_RESPONSE` enum entries.

## Feeder Story Manifest

The feeder stories live under **epic 50** (port cleanup) alongside 50-5 and 50-6. The architect proposes the following stories; PM/SM finalize numbering and prioritization.

| Story | Closes | Points (est.) | Notes |
|-------|--------|---------------|-------|
| **50-5** | Seams A + B | 3 | Specced in `docs/superpowers/specs/2026-05-13-50-5-scenario-clue-discovery-via-journal-design.md`. |
| **50-6** (backlog) | DAG enforcement | 2 | Pre-existing, depends on 50-5. |
| **50-14** — `JOURNAL_REQUEST` handler | Seam C (server side) | 3 | Server replies to `JOURNAL_REQUEST` from `character.known_facts`. Validates `to:` field per ADR-036 multiplayer doctrine. Adds `SPAN_JOURNAL_REPLAY` (zero-duration span; entry count, character id). Depends on 50-5. |
| **50-15** — UI fact_id respect | Seam C (UI side, part 1) | 2 | Drop synthetic `${turn}-${marker}` id manufacture in `useStateMirror.ts`. Consume narrator-supplied `Footnote.fact_id` when present. Per-fact dedupe instead of per-turn. Depends on 50-14. |
| **50-16** — UI confidence propagation | Retire the "Suspected" hardcode | 2 | Drop the `confidence: 'Suspected'` hardcode in `useStateMirror.ts`. The canonical confidence value originates in `KnownFact.confidence` (server-side) and reaches the UI through `JOURNAL_RESPONSE` entries served by 50-14. Per-turn footnote-derived entries either render without a confidence pill until refreshed from canonical, or default to `Suspected` only when no canonical entry exists yet — the exact UX is Klinger's call within this story. Belief-state-derived `Rumored` entries land later with the ADR-053 gossip restoration. Depends on 50-14. |
| **50-17** — `KnownFact.confidence` enum promotion | Type safety | 1 | Promote `KnownFact.confidence: str = "confirmed"` to `Literal["Certain", "Suspected", "Rumored", "Discovered"]`. Migrate existing call sites. Mirrors UI `Confidence` enum already in `GameStateProvider.tsx`. |
| ADR-087 P2 (already scheduled) — Gossip engine | Belief propagation | 8 | Lights up the parallel belief-state surface; future stories plumb belief into journal entries with `confidence: 'Rumored'`. |
| ADR-087 P2 (already scheduled) — Accusation evaluator | Verdict computation | 5 | Consumes the full journal; produces `EvidenceSummary`. |

Stories 50-14 through 50-17 belong together and should land before tea_and_murder receives serious playtest hours — they are the difference between players seeing a coherent journal and seeing the "Suspected" lie.

## Alternatives Considered

**Introduce a new `clue_intent` sidecar JSON in `game_patch`.** Initially proposed during brainstorming. Rejected: the journal already has a stable channel (`Footnote.fact_id`) that the narrator already emits and the UI already (almost) consumes. Adding a parallel sidecar would create a fourth state-mutation pathway when the existing third one is exactly the right shape. ADR-039 + KnownFact + Footnote already define the contract; the failure mode is wiring, not protocol design.

**Body-anchored keyword matching against narrator prose.** Rejected: brittle, authoring-heavy (every `ClueNode` would need trigger phrases), and violates the SOUL principle that mechanics live in the genre, not in pattern-matching the LLM's word choice. The narrator is asked to mark structural intent (`fact_id`); the server trusts that mark. Body-anchored matching also reintroduces the Zork problem from a different angle — it makes the narrator's prose load-bearing for mechanics, which constrains its freedom.

**Add a brand-new `ScenarioClueDiscovered` wire message.** Rejected: doubles the journal surface area. The clue *is* a journal entry; making it a separate message would force the UI to merge two streams that the canonical `JOURNAL_RESPONSE` already unifies.

**Land 50-5 narrow (span only, no `KnownFact` mint).** Rejected during party-mode brainstorming. The party-mode consensus (recorded in conversation): the canonical journal mint is six lines in the same dispatch hook; splitting it off manufactures process where craftsmanship would do, and doubles the integration-test fixture work. Going broad costs less than going narrow once the seam is open.

## Consequences

### Positive

- **One front door for journal stories.** Any future story touching the journal cites this ADR and reads one map instead of grepping five files.
- **Visible debt becomes named debt.** The "Suspected" hardcode and the synthetic-`fact_id` bug are now documented liabilities with owning feeder stories.
- **P5-deferred fields finally exercised.** `KnownFact.source` and `KnownFact.learned_turn` have been waiting since the port for a scenario clue writer. Story 50-5 lights them up.
- **Test coverage improves.** A single integration test for 50-5 now asserts two seams (span fires + `KnownFact` minted). The follow-up story J-1 inherits a real canonical journal to replay.
- **OTEL lie-detection extends to the journal.** When the C-seam lands, GM dashboard can show `Footnotes emitted: N | KnownFacts minted: M | Journal entries shown to player: P` and any mismatch is a real bug. Per CLAUDE.md: "the GM panel is the lie detector."
- **The "Suspected" label retires.** Players see truthful confidence after J-3.

### Negative

- **Two writers of `Character.known_facts`.** After 50-5, both `WorldStatePatch.discovered_facts` and the scenario clue hook will mint `KnownFact`s. The pipelines do not conflict (different `source` values, different write paths), but the discipline must be enforced: scenario clue mints come only from the post-extraction hook, not from arbitrary narrator patches. Story 50-5's spec documents this.
- **Coordination cost.** Stories that previously could ship independently now have a shared ADR they must reference. Mitigation: this ADR's manifest enumerates the work explicitly; PM/SM have a queue, not a free-for-all.
- **Feeder stories must land in order.** J-1 (server handler) before J-2/J-3 (UI consumption), or the UI breaks. Sequencing is documented in the manifest.

### Neutral

- The narrator prompt grows by a `<scenario_clues>` section when `scenario_state` is bound. Token cost is minor (one clue per line, ~30 tokens each). Only renders when a scenario is bound, so non-mystery genres pay nothing.
- Existing genre packs that don't use the scenario system are unaffected — `scenario_state is None` is the no-op path through both seams.

## Cross-References

- **[ADR-039 Narrator Structured Output](039-narrator-structured-output.md)** — defines the `game_patch` JSON block, the `Footnote` schema, and the field-set evolution. This ADR adds *use cases* for `Footnote.fact_id`; it does not modify the protocol.
- **[ADR-053 Scenario System](053-scenario-system.md)** — designs the `ClueGraph`, `BeliefState`, `GossipEngine`, `AccusationEvaluator`. Currently `partial`. This ADR closes the first wiring step (`discover_clue` caller); ADR-087 P2 schedules gossip and accusation.
- **[ADR-057 Narrator Crunch Separation](057-narrator-crunch-separation.md)** — deprecated. Important context: the footnote pipeline (this ADR's primary inflow) is the survivor of ADR-057's design space, not a placeholder for it.
- **[ADR-076 Narration Protocol Collapse Post-TTS](076-narration-protocol-collapse-post-tts.md)** — relevant if any feeder story proposes a new wire message; this ADR confirms no new wire message is needed for the journal seams.
- **[ADR-087 Post-Port Subsystem Restoration Plan](087-post-port-subsystem-restoration-plan.md)** — schedules gossip + accusation at P2 RESTORE under ADR-053. This ADR extends 087's manifest with the four J-series feeder stories above, all tracked under epic 50 (port cleanup) alongside 50-5 and 50-6.
- **[ADR-088 ADR Frontmatter Schema](088-adr-frontmatter-schema.md)** — schema that this ADR conforms to.

## Implementation Status

`partial` — components 1–3 are live, component 5 is data-layer-live/caller-dark, component 4 is live with documented load-bearing lies. Seam A and B close with story 50-5. Seam C closes with feeder stories J-1, J-2, J-3.

When all feeder stories land, this ADR's frontmatter flips to `implementation-status: live` and the implementation pointer clears.

## What This ADR Does **Not** Do

- **Does not modify ADR-039.** The narrator's `Footnote` schema is unchanged; this ADR uses the existing `fact_id` field rather than introducing a new one. J-3 may add a `confidence` field to `Footnote`; if so, that lands as an ADR-039 amendment, not here.
- **Does not redesign ADR-053.** The scenario system's intent stands; this ADR schedules the first caller of `discover_clue`.
- **Does not commit to a feeder-story epic number.** PM/SM owns story-id assignment; this ADR specifies the *work*, not the *epic*.
- **Does not specify UI visual treatment of clue discoveries.** Whether the journal renders a "Clue Discovered!" badge, a special icon, or just a confidence pill is a UX-Designer (Klinger) decision tracked separately from this architectural map.
- **Does not address belief state surfacing in the journal.** Belief-derived entries (NPC X *suspects* Y) belong with ADR-053's gossip restoration; a future J-5 / J-6 would feed `BeliefState` into the journal with `confidence: 'Rumored'` and a `source: 'Gossip'`. Out of scope here.
- **Does not resolve multiplayer-visibility of the journal.** Per-player journal filtering rides on ADR-036 / ADR-037 projection filtering, which is already governed by the `JOURNAL_RESPONSE.to` invariant at `sidequest-server/sidequest/game/projection/invariants.py`. This ADR inherits that doctrine without restating it.
