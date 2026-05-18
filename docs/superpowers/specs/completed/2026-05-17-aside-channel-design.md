# Design — Out-of-Band Aside Channel (Non-Turn-Consuming Player→GM Table-Talk)

**Date:** 2026-05-17
**Author:** GM agent (brainstormed with Keith)
**Status:** design approved, pending spec review
**Genre/World context:** surfaced from the 2026-05-17 Beneath Sünden 5-player MP playtest (finding F6 — players asking the GM clarifying questions inside the action box, burning a turn)
**Proposed ADR:** ADR-107 — Out-of-Band Aside Channel (deliverable of the implementation plan, not this spec)

---

## 1. Problem

During the 2026-05-17 Beneath Sünden MP session, players repeatedly used the in-fiction
action box to ask the GM clarifying questions — Hiken (R7): *"I am very short and don't
know how to swim. Will I be able to wade in the water or will I need to be carried?"* and
(R17): *"Are we able to swim through the water?"* Under submit-and-wait (ADR-036) every
such question **consumes a turn and is fully narrated**, because the `aside` feature is
**half-wired**:

- **Present:** UI toggle (`InputBar` "(…)" → *"What do you whisper?"*), `aside: bool` on
  `PLAYER_ACTION` (`protocol/messages.py`), peer mirror via `ActionRevealPayload.aside`,
  distinct `player-aside` segment rendering (`narrativeSegments.ts`), combat-bracket
  stripping (`handlers/player_action.py`).
- **Missing:** any server branch on `aside` — asides flow through the ADR-036 barrier and
  the full narrator path identically to in-fiction actions, advancing world state.
- **Doc lie:** `docs/api-contract.md` claims `aside:true` = "(not narrated)" *and*
  "broadcast identically to in-character text" — contradictory, and both false.
- **Port drift:** ADR-063 references a Rust `handle_aside()` / `aside.rs` "first-class
  aside narration path"; the ADR-082 Rust→Python port dropped it to a 10-line bracket strip.

**This is a "wire up what exists, don't reinvent" repair plus a doc-lie correction — not a
new feature.**

### Player-audience rationale

- **Alex** (slower typist, freezes under time pressure): a clarifying question must not
  cost a turn or the clock pressure that the action box carries. The aside channel is the
  inclusion fix.
- **Sebastien** (mechanics-first): rules/genre clarification ("how does Edge work?") is a
  *feature* for him, not a leak — consistent with the GM-panel-as-feature stance.
- **Keith / James** (high reading tolerance): recap asides lower the cost of losing the
  thread without replaying it as a turn.

## 2. Settled Requirements (brainstorm decisions)

1. **OOC GM answer, no turn, world frozen.** An aside does not consume a turn or advance
   the world. The narrator answers as the GM, out-of-character, in 1–3 plain sentences.
2. **Fully out-of-band in MP.** An aside never counts toward the ADR-036 barrier, can be
   sent at any moment (before/after the asker's real action, while waiting on a slow
   typist), and is answered immediately. The asker still owes their real action for the
   turn to resolve.
3. **Table-visible.** Both the question and the GM answer are broadcast to the whole room,
   styled as OOC table-talk. Consistent with ADR-036's 2026-05-03 collaborative-visibility
   amendment (no slipped notes; sealed visibility is PvP-only and unimplemented).
4. **Approach A** — finish the existing `aside: bool` flag; branch at the earliest server
   seam; one new typed outbound segment; OTEL span; answer grounded in real state.

## 3. Architecture & Control Flow

The branch sits at the **earliest point the server knows `aside=true`** — the
`handlers/player_action.py` entry, *before* the ADR-036 barrier and *before* any narration
dispatch.

```
WS inbound  PLAYER_ACTION{ aside: true, text: "can I wade or must I be carried?" }
                                  │
        ┌─────────────────────────┴── handlers/player_action.py (entry) ──┐
        │  if payload.aside:                                               │
        │      → AsideResolver.resolve(read-only state view) ─────────────┼──▶ outbound
        │      → emit OTEL span  aside.resolve                             │    ASIDE_ANSWER
        │      → RETURN  (never touches SessionRoom.pending_actions,       │    (table broadcast)
        │                 dispatch_lock, last_dispatched_round,            │
        │                 turn counter, world patch, scrapbook)            │
        └─────────────────────────┬────────────────────────────────────────┘
                                  │  (aside path never reaches here)
                       normal turn: pending_actions buffer → barrier → narration
```

Three load-bearing properties:

1. **Branch before the barrier.** The aside is never written into
   `SessionRoom.pending_actions`, never increments the "everyone submitted" count, never
   takes `dispatch_lock`. An aside arriving mid-round — even while another player's turn is
   dispatching — cannot collide because it shares no mutable turn state.
   **Concurrency-safe by exclusion, not by locking.**
2. **The asker still owes a turn.** Sending an aside does nothing to the asker's
   pending-action slot. The barrier still waits for their real action if unsubmitted; it
   still stands if submitted. The aside is genuinely orthogonal — this is what makes it
   free for Alex.
3. **Read-only resolver.** `AsideResolver` receives a *read* view (asker's character,
   current region/perception projection, inventory, genre rulebook surface, recent
   narration window) and returns text. It holds **no write path** — it structurally cannot
   advance the world, mutate inventory, tick tropes, or touch the dungeon. "No turn
   consumed" is enforced by the resolver having no hands, not by remembering not to use
   them.

The resolve is awaited on the **asker's own WS connection coroutine**, not on the room or
the dispatch path — peers' sockets and the barrier proceed independently while one
player's aside is being answered. "Immediately" means "not deferred to round resolution,"
not "synchronously blocks the table."

Inbound leg (UI toggle, payload, peer mirror) is reused unchanged. Only the outbound leg
is new (§5).

## 4. Resolver Answer Policy & Grounding (GM-craft)

The resolver is a **GM ruling, not a story beat** — it gets GM discipline.

**Answers (the table-talk lane):**
- *Capability/perception* — "Can I wade or must I be carried?" → from the character's own
  size/encumbrance and the region's stated water depth (what the character would already
  perceive standing there).
- *Rules/genre* — "Does Backstab work if they've seen me?", "How does Edge work?" → from
  the genre pack's mechanical surface (the Sebastien lane).
- *Recap* — "Who has the brass key?", "What did the rope-man say?" → from the recent
  narration window and inventory.

**Refuses (the Director-stance wall):**
- Hidden world state — "Is the door trapped?", "Troll HP?", "What's behind the arch?" →
  *"You'd have to check — that's an action, not a question."* Names the action that would
  reveal it and stops. Spoiler protection and Diamonds-and-Coal hold inside the aside
  channel exactly as in narration.
- Anything that would move the fiction → the resolver says so and points back to the
  action box.

**Grounding (lie-detector mandate):** the answer must be traceable to state the resolver
was given (character sheet, region projection, inventory, genre rulebook, recent narration
window). No free improvisation budget. If the inputs don't contain the answer, the honest
output is *"The game doesn't pin that down — treat it as your call or check in-fiction,"*
never a confident invention.

**Cost scales with drama (ADR-101 routing):** an aside is the lowest-drama input in the
system. It routes to the cheap/fast model tier (Haiku). Quiet table-talk earns quiet
spend; this also keeps the answer near-instant, which is the point of an out-of-band
channel.

**Voice:** plain, brief, second-person GM register —
*"Knee-deep on you, Hiken. Wading's slow but you don't need carrying."*
One to three sentences. No scene-setting, no fourth wall, no prose flourish.

## 5. Protocol & UI

**Inbound (unchanged):** `PLAYER_ACTION { aside: true, text }` — existing `InputBar` "(…)"
toggle and payload field. Placeholder copy changes from *"What do you whisper?"* to
*"Ask the GM — no turn spent"* (truer to behavior; no new send path).

**Outbound (the one new piece):** a dedicated typed segment, **not** a generic
`NARRATION` (reusing `NARRATION` would make an OOC ruling indistinguishable from in-fiction
prose in scrollback, scrapbook, and GM panel — the exact conflation we are killing).

New `MessageType.ASIDE_ANSWER` (server `protocol/enums.py` + UI `types/protocol.ts`),
sibling of `NARRATION`, broadcast to the whole room:

```
ASIDE_ANSWER {
  asker_id:     "Hiken"
  question:     "can I wade or must I be carried?"
  answer:       "Knee-deep on you, Hiken. Wading's slow but no carry needed."
  grounded_on:  ["character.size", "region.water_depth"]   # audit trail (§6)
  round:        <current round — ordering only, NOT a turn record>
}
```

- **Table-visibility is free** — rides the existing room broadcast, not a per-recipient
  perception firewall (ADR-104/105 untouched).
- **Not persisted as a turn.** No `narrative_log` row (author='narrator'), no
  `scrapbook_entries` row, no `session_meta` turn/round advance. MAY be journaled to a
  separate lightweight aside log for replay fidelity, but it is structurally outside the
  turn record. (Forensic timelines like the R3-stall analysis stay clean — asides never
  pollute the narration log.)
- **UI rendering:** existing `narrativeSegments.ts` already de-emphasizes the *question*
  as `player-aside`; add a paired `gm-aside` kind for the *answer*, same OOC visual
  register (indented, lighter, marginal table-talk), rendered inline where it was asked so
  the Q&A reads as a unit. No new panel/modal.

**Doc-lie correction (rides this work):** `docs/api-contract.md` rewritten to the real
contract — aside → OOC GM answer, no turn, no world advance, `ASIDE_ANSWER` outbound,
table-visible. Remove the "(not narrated)" / "broadcast identically" contradiction.

## 6. Error Handling & OTEL

**OTEL (lie-detector mandate — non-negotiable):** every aside emits a routed
`aside.resolve` span the GM panel can see, carrying `asker_id`, `question`, `answer`,
`grounded_on[]`, `model`, `latency_ms`, `outcome ∈ {answered, refused_hidden_state,
refused_would_advance, ungrounded_declined, resolver_error}`. A missing span means the
channel didn't engage; a present span with empty `grounded_on` on a factual answer is an
ungrounded-aside finding — visible and auditable, exactly as for narration. The aside
channel does not get to be a blind spot.

**Error handling (No Silent Fallbacks):**
- Resolver LLM call fails/times out → loud `gm-aside` segment *"(The GM didn't catch that
  — ask again.)"* + `ERROR`-level log + `outcome=resolver_error`. No turn is lost (there
  was none); the asker's pending real action is untouched.
- Empty/whitespace aside text → rejected at the handler with a typed `ERROR`, no resolver
  call.
- Resolver cannot ground an answer → declines honestly (`outcome=ungrounded_declined`),
  never improvises (§4).

## 7. Testing

**Mandatory wiring test (centerpiece):** drive the real `PLAYER_ACTION{aside:true}` path
through the real handler and assert **all** of:
1. no `narrative_log` row added
2. no `scrapbook_entries` row
3. `session_meta` turn/round unchanged
4. no world patch / inventory / trope mutation
5. in a 3-player MP room, an aside mid-round leaves the barrier still waiting on the
   asker's real action and the other two players' submissions unaffected
6. an `ASIDE_ANSWER` is broadcast to all seats
7. the `aside.resolve` span fired

**Units:**
- answer-policy boundary: capability question → `answered`; "is it trapped?" →
  `refused_hidden_state`
- grounding traceability: factual answer carries non-empty `grounded_on`
- doc-contract test: `api-contract.md` no longer contains "(not narrated)" for `aside`

## 8. Deliverables

- Server: `AsideResolver` (read-only), handler branch in `handlers/player_action.py`,
  `MessageType.ASIDE_ANSWER` + payload (`protocol/enums.py`, `protocol/messages.py`),
  `aside.resolve` OTEL span (registered in the telemetry span registry + `SPAN_ROUTES`).
- UI: `ASIDE_ANSWER` in `types/protocol.ts`, kind-map route, `gm-aside` segment in
  `narrativeSegments.ts`, `InputBar` placeholder copy.
- Docs: `docs/api-contract.md` correction; **ADR-107** authored (cross-refs ADR-036, 063,
  082, 101, SOUL).
- Tests: the mandatory wiring test + units above.

## 9. Out of Scope (YAGNI)

- Private / sealed-visibility asides (PvP paradigm; ADR-036 reserves this, unimplemented —
  not for the co-op playgroup).
- Aside threading/history panel — asides render inline in the existing scroll; no new
  surface.
- Aside-driven world changes ("yes-and" canonization via aside) — an aside that would move
  the fiction is refused and pointed back to the action box.
- Voice/TTS for aside answers (TTS removed post-2026-04).
