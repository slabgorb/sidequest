---
parent: context-epic-72.md
workflow: tdd
---

# Story 72-7: Apply NPC identity drift authoritatively

**Epic:** 72 (NPC Identity Hardening) · **Points:** 3 · **Type:** bug · **Workflow:** tdd · **Repo:** sidequest-server

## Business Context

NPC identity in SideQuest is a case-folded name string split across two unreconciled
stores (epic context, "two-store identity split"). When the narrator re-mentions an
NPC with a *changed* pronoun or role, today the engine **only warns** — it emits
`npc.reinvented` at `severity="warning"` and freezes the canonical value at its
first-mention guess forever. This is the warn-only behavior this story replaces.

**The live failure (the thing being fixed).** From `sq-playtest-pingpong.md` DEEP-DIVE
#1, perseus_cloud session 894 (2026-05-29): turn 1 a floor-boss was minted ungendered
("they"); turn 2 the narrator settled the character as "Sitä-minutta / she." The
pool-hit upsert (`narration_apply.py` ~1271–1278) **only fills empty fields**, so the
ungendered first value won permanently. `_detect_npc_identity_drift`
(`session_helpers.py:2004`) saw the disagreement, logged a warning, and threw the new,
correct pronoun away. For the rest of the session the narrator prompt carried stale
pronouns — exactly the kind of silent identity improvisation the OTEL lie-detector is
supposed to catch but here could only *observe*, never *correct*.

**Who this serves.** This is core to the "good enough to fool a career GM" bar
(playgroup CLAUDE.md, Keith-as-player): a real DM who corrects an NPC's gender or
promotes "the assistant" to "the captain" expects that correction to *stick*, not to be
silently overruled by his first throwaway guess. It also feeds Sebastien/Jade's
mechanical-visibility surfaces — the drift-applied OTEL span lets the GM panel show that
the canonical record actually moved, not just that a mismatch was noticed.

## Technical Guardrails

**Primary seam — the pool-hit upsert.** `narration_apply._apply_npc_mentions`,
`sidequest-server/sidequest/server/narration_apply.py` ~1263–1290. The pool_hit branch
currently does an **additive-only** upsert:

```python
if mention.role and not pool_hit.role:
    pool_hit.role = mention.role
if mention.pronouns and not pool_hit.pronouns:
    pool_hit.pronouns = mention.pronouns
```

This story changes the `role` and `pronouns` upserts from fill-empty to **authoritative
overwrite** when the mention carries a non-empty value that disagrees with the canonical
entry. `appearance` is *not* in scope for overwrite — leave it additive (see Scope
Boundaries). The drift detector call at ~1264 (`_detect_npc_identity_drift`) stays; it
runs *before* the upsert and supplies the span. The cleanest shape is to have the
detector (or the upsert site) record that the overwrite was **applied** rather than
warn-only.

**Drift detector + span.** `_detect_npc_identity_drift`,
`sidequest-server/sidequest/server/session_helpers.py:2004`. It iterates
`(pronouns, role)`, fires `npc_reinvented_span(...)` on any explicit disagreement
(both mention value and existing value present, case-insensitively different), and logs
`npc.reinvented`. Empty mention fields = "no opinion" and must continue to be ignored
(no overwrite, no span). The span helper `npc_reinvented_span`
(`sidequest/telemetry/spans/npc.py:340`) already accepts `**attrs`, so an
`applied=True` (old→new captured in existing `expected`/`narrator` attributes) attribute
can be threaded without changing the span route. Convert the span from a warn-only alert
into an *applied* drift span per the epic OTEL plan (72-7: "convert `npc.reinvented` from
warn-only to an *applied* span").

**Npc-hit branch is pronoun-only.** The `npcs_hit` branch
(`narration_apply.py` ~1227–1255) calls the same detector but passes
`existing_role=None` (an `Npc` has no narrator-cited string `role`, only the
archetype-id `npc_role_id`) and currently does **no** identity write — it only stamps
`last_seen_*`. `Npc.pronouns` (`session.py:161`, `str | None`) is writable. If you extend
authoritative overwrite to the `npcs_hit` branch, bound it to `pronouns` only; do **not**
invent a string `role` write onto `Npc`. Whether to apply to `npcs_hit` is a design call
for TEA/Dev — at minimum the pool_hit path must overwrite; mirror it onto `npcs_hit`
pronouns if the dossier-injection path (37-44) feeds `Npc` pronouns back to the prompt.

**OTEL is mandatory** (server CLAUDE.md OTEL Observability Principle). The applied
overwrite must emit a span recording old→new so the GM panel can verify the canonical
record moved. No silent overwrite.

**Test style (server rule).** Behavioral / span assertions only. Drive
`_apply_narration_result_to_snapshot` (or `_apply_npc_mentions`) with a synthetic
snapshot + `NarrationTurnResult` carrying an `NpcMention`, then assert on the **mutated
snapshot state** (canonical `pool_hit.pronouns`/`role` now equals the new value) and on
the **emitted span** (`npc.reinvented` with the applied marker, old→new attributes). No
source-text wiring tests — do not grep `narration_apply.py` for the assignment. See
`tests/server/test_npc_identity_drift.py` for the existing fixture shape (Frandrew
captain→demotion multi-turn scenario) to extend.

## Scope Boundaries

**In scope:**
- Pool-hit `role` overwrite on disagreeing re-mention (was fill-empty).
- Pool-hit `pronouns` overwrite on disagreeing re-mention (was fill-empty).
- `npc.reinvented` span carries an *applied* marker + old→new values.
- Bounding the overwrite to identity fields (`pronouns`, `role`) only.

**Out of scope (do not touch):**
- **Reconcile-on-load / npcs↔npc_pool invariant — that is 72-2.** Do not add a load-time
  reconcile pass here.
- **Routing invented names through namegen — that is 72-4.** The Step-3 invented branch
  (`narration_apply.py` ~1292) is untouched.
- **Mechanical state.** Disposition, HP/`HpPool`, `BeliefState`, `ocean`,
  `resolution_tier`, `non_transactional_interactions`, `last_seen_*` — the overwrite must
  **not** reach any of these. Drift is identity-field-only.
- **`appearance`** — remains additive (fill-empty). A re-mention with new appearance prose
  is description accretion, not an identity correction, and overwriting it would churn the
  scaffold on every paraphrase.
- Pool growth caps / pruning (72-6), encounter-presence `last_seen_*` stamping (72-8).

## AC Context

No explicit ACs existed; these are derived per the epic drift-seam description and the
session-894 failure. All are behavioral/span-assertable.

- **AC-1 — Pronoun overwrite (was warn-only).** Given a pool member with canonical
  `pronouns="they/them"`, when a later-turn `NpcMention` for the same case-folded name
  carries `pronouns="she/her"`, the canonical `pool_hit.pronouns` is **overwritten** to
  `"she/her"`. (Today it stays `"they/them"`.) Assert on mutated snapshot state.
- **AC-2 — Role overwrite (was warn-only).** Given a pool member with canonical
  `role="assistant"`, a later mention carrying `role="captain"` overwrites
  `pool_hit.role` to `"captain"`. Assert on mutated snapshot state. (Mirrors the
  Frandrew demotion scenario in `test_npc_identity_drift.py`.)
- **AC-3 — Applied drift span (old→new).** Each authoritative overwrite emits the
  `npc.reinvented` span (`SPAN_NPC_REINVENTED`) carrying the old (`expected`) and new
  (`narrator`) values, `drift_field`, and an attribute distinguishing *applied* from the
  prior warn-only emission. Assert via the span/watcher harness, not log text.
- **AC-4 — Bounded to identity fields; mechanical state untouched.** A re-mention with
  changed pronoun/role leaves the member/`Npc`'s mechanical state unchanged — assert
  `disposition`, `resolution_tier`, `non_transactional_interactions`, and `appearance`
  are byte-identical before/after the overwrite. Only `pronouns`/`role` move.
- **AC-5 — No-op when mention agrees or is empty.** A re-mention whose `pronouns`/`role`
  match the canonical value (case-insensitively), or whose fields are empty/`None`,
  performs **no** overwrite and emits **no** `npc.reinvented` span (preserving the
  "empty = no opinion" contract at `session_helpers.py:2025`).

**Edge cases to cover (test, derived):**
- **Conflicting drift within one turn.** If a single turn yields two mentions of the same
  name with *different* new pronouns/roles, define and test a deterministic
  resolution (last-mention-wins, matching the sequential apply loop) — the canonical
  record must not be left in an order-dependent indeterminate state, and each applied
  step should be observable.
- **Drift on a player-named NPC.** When the disagreeing canonical entry originated from
  the player (e.g. a `world_authored` / player-supplied pool member, not
  `drawn_from="narrator_invented"`), decide and test the policy: narrator drift should
  **not** silently overwrite a player-authored identity. Either suppress the overwrite for
  player-origin members and keep the warning, or gate on `drawn_from` — assert the chosen
  behavior. (No Silent Fallbacks: whichever way it goes, it must be explicit and
  span-visible.)
- **Drift that collides with another NPC's identity.** An overwrite must not mutate the
  *name* (the case-folded join key), so it cannot by itself create a duplicate name. But
  test that overwriting pronoun/role to match a *different* existing NPC's values does not
  merge, alias, or cross-link the two pool entries — they remain two distinct members.

## Assumptions

- `NpcMention` carries optional `pronouns` / `role` / `appearance` (empty string or
  `None` = "no opinion"); the case-folded `name` is the join key and is **not** rewritten
  by this story.
- `NpcPoolMember.role` and `.pronouns` are `str | None` and freely writable
  (`game/npc_pool.py:34–37`); `Npc.pronouns` is `str | None` and writable
  (`session.py:161`). `Npc` has no narrator-cited string `role` to overwrite.
- The detector's pre-existing case-insensitive disagreement test
  (`m_val.strip().lower() != e_val.strip().lower()`, `session_helpers.py:2025`) is the
  correct trigger for "should overwrite" — reuse it; do not loosen "empty = no opinion."
- `npc_reinvented_span(... **attrs)` can absorb an `applied` attribute without a new span
  route (`SPAN_ROUTES[SPAN_NPC_REINVENTED]` unchanged); the GM panel already subscribes to
  this span as a drift alert.
- The pool-hit branch is the authoritative write site; the `npcs_hit` branch's
  pronoun-only overwrite is at TEA/Dev discretion but, if implemented, is bounded to
  `Npc.pronouns` and must not synthesize a `role`.
- Test seam: `_apply_narration_result_to_snapshot`
  (`sidequest/server/session_handler.py`) is the production entry that drives
  `_apply_npc_mentions`; the existing `tests/server/test_npc_identity_drift.py` fixtures
  (synthetic `GameSnapshot` + `NpcPoolMember` + `NarrationTurnResult`) are the pattern to
  extend.
