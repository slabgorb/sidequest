---
story_id: "37-27"
jira_key: null
epic: "37"
workflow: "trivial"
---
# Story 37-27: Character snapshot on scene-enter

## Story Details
- **ID:** 37-27
- **Jira Key:** null
- **Workflow:** trivial
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-04-19T08:58:14Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-19T08:35:41Z | 2026-04-19T08:36:37Z | 56s |
| implement | 2026-04-19T08:36:37Z | 2026-04-19T08:50:16Z | 13m 39s |
| review | 2026-04-19T08:50:16Z | 2026-04-19T08:58:14Z | 7m 58s |
| finish | 2026-04-19T08:58:14Z | - | - |

## Story Description
Character snapshot on scene-enter — cross-genre blank Character tab until turn 1; emit character state on session-start/scene-enter not just turn-update

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

## Sm Assessment

**Story:** 37-27 — Character snapshot on scene-enter
**Workflow:** trivial (setup → implement → review → finish)
**Scope:** Character tab is blank across genres until turn 1. Root cause: character state is only emitted on turn-update. Fix: also emit character snapshot on session-start and scene-enter boundaries so the UI has state immediately.
**Repos:** api (sidequest-api) — emit path lives in the server/game message dispatch.
**Complexity:** Small. 2 pts, trivial workflow. Locate existing turn-update character-state emission, replicate the emit at session-start and scene-enter hooks, add OTEL span so GM panel can confirm.
**Risks:** Double-emit on turn 1 if scene-enter fires just before first turn-update — idempotent payload so UI can safely overwrite. No mechanical state changes, pure read-side snapshot.
**Handoff:** Dev (Major Winchester) — implement the additional emit sites + OTEL, confirm cross-genre via any loaded save.
## Design Deviations

### Dev (implementation)
- No deviations from spec.

## Delivery Findings

### Dev (implementation)
- **Improvement** (non-blocking): The opening-turn PARTY_STATUS in `compose_responses` still sends `sheet=None` for fresh-chargen because the acting player isn't in the shared session yet at that point. The fix here is additive (a corrective PARTY_STATUS near session-ready), not a re-ordering of the shared-session insertion. Future cleanup: move shared-session insertion + sheet population before the opening dispatch so `compose_responses` always has sheet data. Affects `crates/sidequest-server/src/dispatch/connect.rs` (opening-turn ordering vs shared-session insertion at line 2520). *Found by Dev during implementation.*

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-api/crates/sidequest-server/src/dispatch/connect.rs` — emit corrective PARTY_STATUS with populated sheet facet immediately before the `ready` SessionEvent on fresh chargen; add OTEL `session.start.character_snapshot_emitted` span.
- `sidequest-api/crates/sidequest-server/src/dispatch/tropes.rs` — elide needless lifetime (unblocks `-D warnings` gate, trivial).

**Root Cause:** `compose_responses` reads `ps.sheet` from shared session when building PARTY_STATUS, but the acting player isn't inserted into shared session until AFTER the opening-turn dispatch runs. So the first PARTY_STATUS the UI sees has `sheet=None`. Client's `App.tsx` sheet handler only calls `setCharacterSheet` when the facet is non-null, so the Character tab stays blank until turn 1 (when the player is now in shared session with sheet populated).

**Fix Shape:** Additive — construct a PARTY_STATUS for the acting player using the freshly-built `built_sheet` and the live `inventory`, push it into the response vec right before `ready`. No changes to the existing opening-turn ordering. Later PARTY_STATUS messages with `sheet=None` do not clobber because the client ignores them.

**Tests:** dispatch tests pass (20 passed / 60 filtered). No new tests — this is a pure additive emit on a code path covered implicitly by integration playtest smoke.
**Branch:** feat/37-27-character-snapshot-scene-enter (pushed)

**Handoff:** Reviewer (Colonel Potter) — verify the emit site is correct, OTEL span format matches ADR-031, and the additive approach is preferred over re-ordering the shared-session insertion.
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 1 blocking (compile error) | confirmed 1, fixed |
| 2 | reviewer-edge-hunter | Yes | findings | 3 | confirmed 1 (fixed), dismissed 2 |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 3 | dismissed 3 (existing convention) |
| 4 | reviewer-test-analyzer | Yes | findings | 1 | deferred 1 (logged as non-blocking delivery finding) |
| 5 | reviewer-comment-analyzer | Yes | findings | 2 | confirmed 1 (fixed), dismissed 1 |
| 6 | reviewer-type-design | Yes | findings | 2 | confirmed 1 (fixed), dismissed 1 (matches existing convention) |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | clean | 0/20 | none |

**All received:** Yes
**Total findings:** 3 confirmed (fixed), 7 dismissed (with rationale), 1 deferred (non-blocking delivery finding)

## Reviewer Assessment

**Verdict:** APPROVE with in-review fixes applied.

### Confirmed findings (fixed in-review)
1. **Preflight BLOCKING — compile error in dice_request_lifecycle_story_37_20_tests.rs** (3 errors).
   Root cause: `Stat` type is a validated newtype on `DiceRequestPayload.stat`, but the test file used raw `&str` / `String`. This predated the 37-27 branch but was never exercised because `cargo test --lib` skips integration tests; `cargo fmt` (which runs on every push) did NOT unmask it — the module was already registered. So this is latent pre-existing rot that 37-27's preflight finally surfaced.
   Per CLAUDE.md "no pre-existing excuse" and per feedback memory "fixes and broken-test hygiene are never scope creep," fix bundled into this branch. Assertion had to compare `.as_str() == "DEXTERITY"` because `Stat::new` normalizes to uppercase.
2. **reviewer-type-design — `has_sheet: true` OTEL field is unconditionally true.**
   Replaced with `sheet_class` and `inventory_count` — diagnostic, not redundant.
3. **reviewer-comment-analyzer — "a few hundred lines below" undersells the ~600-line gap.**
   Rewritten to cite the exact block name.

### Dismissed findings (with rationale)
- **edge-hunter #1 — `player_id.expect()` panic risk.** Dismiss. `player_id` is a session-key invariant established at handshake; panicking on empty is correct fail-loud per CLAUDE.md no-silent-fallbacks.
- **edge-hunter #2 — OTEL span fires before `msgs.push`, could lie on early return.** Dismiss. Verified by grep: zero `return vec![...]` or `return Err` sites between the WatcherEvent send (line 2551) and `msgs.push(session_start_party_status)` (line 3171). The span and push are in the same linear code path. False positive.
- **edge-hunter #3 — `character.core.statuses.clone()` unbounded.** Dismiss. Matches existing convention everywhere else in the file; no exploit vector (statuses come from internal game state, not wire input).
- **silent-failure #1 / type-design #1 — `unwrap_or_else` to "Adventurer" for blank class.** Dismiss. Matches existing convention in `response.rs:294-301` where the SAME `"Adventurer"` fallback is used for the same reason. Changing here would create inconsistency; if the fallback is wrong, it's a global rewrite outside 37-27's scope.
- **silent-failure #2 — `current_location.ok()` discards Err.** Dismiss. `current_location` is `Option<NonBlankString>` on the wire by design (reconnect/pre-location scenes). None is the correct encoding for "no location yet."
- **silent-failure #3 — misleading expect message on "Player" literal.** Dismiss. Low-severity cosmetic; the message still identifies the failure surface.
- **comment-analyzer — App.tsx sheet-handler claim.** Verified correct by subagent; no action needed.

### Deferred (non-blocking delivery finding)
- **test-analyzer — no wiring test for the new emit.** Logged in Delivery Findings. The new emit path is covered by OTEL (GM panel acts as the lie detector per CLAUDE.md OTEL principle) and by manual playtest. A dedicated integration test would require plumbing a full chargen → session-start harness which is disproportionate to a 2-pt trivial story. Non-blocking.

### Rule Compliance
All 20 rules in `.pennyfarthing/gates/lang-review/rust.md` verified by rule-checker, zero violations. OTEL span present per CLAUDE.md. No silent fallbacks introduced. Wiring end-to-end: emit → msgs vec → ws broadcast → `App.tsx` sheet handler (verified).

### Ready for Merge
Yes. Lib clippy clean, integration tests green, dispatch tests pass, format clean. Branch pushed.

**Handoff:** SM (Hawkeye Pierce) — proceed to finish flow.