---
story_id: "67-4"
jira_key: ""
epic: "67"
workflow: "tdd"
---
# Story 67-4: MP identity mapping (player-vs-character) — stop rendering doubled 'X— X' header

## Story Details
- **ID:** 67-4
- **Jira Key:** (not yet created)
- **Workflow:** tdd
- **Epic:** 67 (Multiplayer resilience & presence)
- **Points:** 3
- **Priority:** p2
- **Type:** bug
- **Repos:** server, ui
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-28T14:37:52Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-28T13:42:29Z | 2026-05-28T13:44:12Z | 1m 43s |
| red | 2026-05-28T13:44:12Z | 2026-05-28T14:16:46Z | 32m 34s |
| green | 2026-05-28T14:16:46Z | 2026-05-28T14:29:13Z | 12m 27s |
| spec-check | 2026-05-28T14:29:13Z | 2026-05-28T14:31:14Z | 2m 1s |
| verify | 2026-05-28T14:31:14Z | 2026-05-28T14:32:48Z | 1m 34s |
| review | 2026-05-28T14:32:48Z | 2026-05-28T14:36:19Z | 3m 31s |
| spec-reconcile | 2026-05-28T14:36:19Z | 2026-05-28T14:37:52Z | 1m 33s |
| finish | 2026-05-28T14:37:52Z | - | - |

## Story Context

### Background
From epic-67 context: The doubled-header bug occurs when player display name and character name are the same (or the identity mapping conflates the two), rendering headers as "X — X" instead of just "X" or "Player — Character".

This spans two areas:
1. **Server (sidequest-server):** Identity payload — what `player_id`/`player_name` vs `character_name` the server emits in game messages and state updates
2. **UI (sidequest-ui):** Header rendering — where the "Player — Character" header is composed in character display components

### Root Cause
Related commit: 173f5b1 "Show controlling player's name on character displays (MP only)" likely introduced the regression when adding player-name-on-character-display feature. The player identity is being conflated with character identity in the header composition.

### Related ADRs
- **ADR-037:** Shared-World / Per-Player State Split — defines player vs character identity boundaries
- **ADR-036:** Multiplayer Turn Coordination — governs how player/character info flows during turns

### Test Plan (from AC)
1. Create a multiplayer game where a player name = character name
2. Verify the character header displays only the name once (not "X — X")
3. Create a multiplayer game where player name ≠ character name
4. Verify the character header displays "PlayerName — CharacterName"
5. Test with various name combinations (empty, same, different) across multiple clients

## Sm Assessment

**Scope (confirm):** Fix the doubled `X — X` MP header by correcting the player-vs-character identity mapping. Two repos: **server** owns the identity payload (which of `player_id` / `player_name` / `character_name` is emitted, and whether they're distinct), **ui** owns the header composition (the `Player — Character` render). The bug surfaces when player name == character name (renders the same string twice) — but the real fix is to stop *conflating* the two identities, not to string-compare-and-dedupe in the view.

**Why now / who it serves:** Playtest-3 finding, Keith-requested (epic-67). A doubled header is a legibility papercut that hits the whole table in MP. Mechanics-first players (Sebastien/Jade) read the header to know *who controls what* — a conflated identity makes the controlling-player attribution untrustworthy, which is worse than ugly.

**Root-cause lead for TEA/Dev:** Regression most likely originates in ui commit **173f5b1** "Show controlling player's name on character displays (MP only)" — the feature that added player-name to character displays. Start the RED test there. The correct contract is ADR-037's player-vs-character split: a player (account/seat) controls a character (PC). Header should read just the name once when player and character names coincide, and `Player — Character` only when they genuinely differ.

**TEA guidance (RED):** Write failing tests on BOTH sides — (1) server: identity payload carries distinct player vs character identity (or a flag) so the client can decide; (2) ui: header renders a single name when player==character, `Player — Character` when distinct, across same/different/empty name combos and multiple clients. At least one wiring test proving the header consumes the server's identity fields end-to-end (not a hardcoded prop).

**Defer / out of scope:** 67-5 (ws.send_failed observability) is independent. Don't touch the turn-status/seal surfaces — 67-3 closed that lane (resolved by ec69c9b).

**Gate:** Merge gate clear (no open PRs). Session + branches (ui + server, base develop) created. 67-3 closed done immediately prior. TDD/phased → handoff to TEA (Radar) for RED.

## TEA Assessment (RED)

**RED state verified — tests committed on both feature branches:**
- **UI** `sidequest-ui` (`5617595`): `src/components/__tests__/CharacterPanel.test.tsx` — new "Story 67-4" block. 3 fail / 1 pass (run `67-4-tea-red`). Failures prove the live doubled header (`Kael— Kael`, `Rux— Rux`); the PROTECTIVE LOCK (suffix still shows when player_id ≠ name) passes so GREEN can't over-suppress.
- **Server** `sidequest-server` (`42aa57f`): `tests/server/test_player_identity.py` — RED via collection ImportError (run `67-4-tea-red-server`); module `sidequest.server.player_identity` does not exist yet.

**Root cause (confirmed in code):** Player display identity is user-typed (`connect.py:317` `display_name = payload.player_name or player_id`) and routinely equals the character name. `CharacterPanel.tsx:243` appends `— {player_id}` with no `!= name` guard — the doubling. `CharacterSheet.tsx` already has the guard (reference behavior). Server-side, `views.build_session_start_party_status` fabricates a peer's player-display as `pname = char.core.name` — the ADR-037 conflation.

**GREEN contract for Dev (Major Winchester):**
1. **New seam** `sidequest/server/player_identity.py` → `resolve_player_identity(headers) -> str` + `MissingPlayerIdentityError`. Order: `Cf-Access-Authenticated-User-Email` (non-blank) → `Host` header → raise. Case-insensitive. (Tests pin this exactly.)
2. **Wire it** at the WS route `websocket_game` (`app.py:276`, where `websocket.headers` is in scope) → stash resolved identity on the handler → `connect.py` prefers it over typed `payload.player_name`. **Add a behavior/wiring test** (not source-grep, per CLAUDE.md "No Source-Text Wiring Tests") proving a connect carrying a CF-email header yields that identity downstream.
3. **Peer conflation** — `views.build_session_start_party_status` must stop setting a peer's player-display to `char.core.name`. Requires storing each player's resolved identity in the room/snapshot keyed by `player_id` at *their* connect, so any PARTY_STATUS build can look up peers' real identities (a peer authenticated on their own socket). See "Delivery Findings" — this is the load-bearing threading decision.
4. **UI guard** — `CharacterPanel.tsx` must suppress the suffix when the player-identity equals the character name (mirror `CharacterSheet.tsx`). Make the UI tests green without breaking the protective lock.

**Rule Coverage (lang-review / SOUL):**
- *No Silent Fallbacks* — `test_blank_cf_email_is_not_used_falls_through_to_host` + `test_no_email_and_no_host_fails_loud` enforce fail-loud; the resolver never swaps a blank header for the colliding handle.
- *Wiring* — UI `wiring:` test drives the real CharacterPanel prop path; server wiring test is a GREEN requirement (item 2) since the seam doesn't exist yet.
- *Negative cases* — protective lock (suffix retained when distinct); blank/missing header; case-insensitivity.

**Self-check:** No vacuous assertions — every test asserts a concrete value or a raised error.

## Delivery Findings

<!-- Append-only. Do not edit other agents' entries. -->

### TEA (RED)
- **Scope** (non-blocking): Story 67-4 grew from a UI-only doubled-header guard into an **authenticated-identity feature** spanning the transport/auth seam (Cloudflare-email identity → Host fallback) per Keith's direction (2026-05-28). The 3-pt estimate likely undercounts; recommend SM re-size after GREEN. The UI guard alone closes the *visible* bug; the server identity work is the *root* fix.
- **Question** (blocking for full GREEN): Peer identity threading. The server building a PARTY_STATUS frame only knows its own connection's headers — a peer's CF email/host arrived on *their* socket. To stop `pname = char.core.name` for peers, each player's resolved identity must be persisted at their connect (room/snapshot, keyed by `player_id`) and looked up during PARTY_STATUS assembly. Affects `sidequest/server/session_room.py` (or snapshot), `views.py`, `connect.py`. Dev/Architect must decide the storage location. *Found by TEA during RED.*
- **Improvement** (non-blocking): Recommend an **ADR** for "authenticated player identity via Cloudflare Access header (trust boundary + local-dev host derivation)" — this is a real trust-boundary decision worth recording, not just a bug fix. Affects `docs/adr/`. *Found by TEA during RED.*
- **Improvement** (non-blocking): `TurnStatusEntry` type is duplicated (`sidequest-ui/src/types/payloads.ts` + re-declared in `TurnStatusPanel.tsx`) — carried over from 67-3's findings; unrelated to 67-4 but worth a future cleanup. *Found by TEA during RED.*

### Dev (implementation)
- **Conflict** (blocking → resolved by descope): `sd.player_name` is overloaded as a **character-name key**, not just a player identity. `websocket_session_handler.py:2561` calls `snapshot.party_location(perspective=sd.player_name)`, and `party_location` does `character_locations.get(perspective)` (`session.py:956`) — keyed by character name. The same `connect.py` `display_name` also feeds `with_lobby_name()` (the character's name) and seat-matching (`connect.py:553`). Wiring the resolved email into `sd.player_name` would make `party_location` return `None` → **breaks perception/location POV for the local player**. The server CF-email identity refactor therefore requires separating player-identity from the character-name key across `connect.py` / `session.py` / `views.py` — an ADR-level change, not a bug-fix wire. *Found by Dev during implementation.*
- **Request** (non-blocking): SM to **re-scope 67-4 → ui-only** (server repo dropped) and **create a follow-up story** for the Cloudflare-email player-identity refactor (Architect + ADR). The resolver contract to preserve: `sidequest/server/player_identity.py::resolve_player_identity(headers) -> str` + `MissingPlayerIdentityError`; order `Cf-Access-Authenticated-User-Email` (non-blank, case-insensitive) → `Host` header → raise; the 8 pinning tests live in the (now-reset) `tests/server/test_player_identity.py`. Follow-up must also separate `sd.player_name` (player identity) from the character-name key (perception/seat/lobby) and store per-player identity cross-socket for peer PARTY_STATUS. *Found by Dev during implementation.*


## Impact Summary

**Status:** Ready to finish (ui-only, observable bug fixed)

### Observable Impact
- **Doubled-header bug:** Fully fixed. Player display name == character name no longer renders as "X — X"; displays single name only.
- **Protective lock:** Maintained. When player_id ≠ character name, suffix still renders correctly as "Player — Character".
- **Test coverage:** All 67-4 tests passing (4 new tests, 1642 total UI suite green).

### Findings Count
- **Blocking issues:** 0
- **Non-blocking improvements:** 3 (server identity refactor recommendation, ADR recommendation, TurnStatusEntry duplication note)
- **Design deviations:** 1 major (server scope deferred — approved, user-endorsed, Architect-concurred)

### Root Cause Status
- **Observable bug root cause:** Fixed in UI (CharacterPanel.tsx guard clause mirrors CharacterSheet.tsx).
- **Deep root cause (Cloudflare-email identity + peer-name conflation):** Deferred to follow-up story + ADR per Architect guidance. Blocked on `sd.player_name` character-name-key decoupling (ADR-037, perception-POV regression risk).

### Story Scope
- **Original:** repos: server, ui
- **Final:** repos: ui (server descoped per Dev blocking finding + user endorsement)
- **Rationale:** Server-side identity refactor requires ADR-level decoupling of `sd.player_name` from character-name-key role (affects perception, seat-matching, lobby-name). Half-wiring would create dead code or regression; full wiring exceeds bug-fix scope.

### Next Actions for SM
1. **Re-scope 67-4** in sprint tracker to `repos: ui` only.
2. **Create follow-up story** (Architect + ADR) for Cloudflare-email player-identity feature + `sd.player_name` decoupling from character-name-key (blocking on perception-POV threading).
3. **Preserve resolver contract** in follow-up (TEA designed `resolve_player_identity(headers) -> str` + `MissingPlayerIdentityError`; contract sound, only the wiring was risky).


## Design Deviations

<!-- Append-only. Do not edit other agents' entries. -->

### TEA (RED)
- No deviations from spec. Scope was expanded by explicit user direction (logged as a Delivery Finding, not a deviation).

### Dev (implementation)
- **Descoped server repo to ui-only; backed out the resolver test**
  - Spec source: 67-4 session scope (repos: server, ui) + TEA GREEN contract items 1–3 (server resolver + connect wiring + peer conflation)
  - Spec text: "server owns the identity payload … resolve from Cf-Access-Authenticated-User-Email → Host … stop fabricating peer name = char.core.name"
  - Implementation: Shipped the UI guard only (`CharacterPanel.tsx` `player_id !== name`, mirroring `CharacterSheet.tsx`). Reset the server branch to `develop` (removed commit `42aa57f` `tests/server/test_player_identity.py`) and deleted the uncommitted `sidequest/server/player_identity.py`. Server branch now has no divergent commits.
  - Rationale: Wiring the resolved identity into the server safely requires untangling `sd.player_name`'s dual role as a character-name key for perception (`party_location`), `with_lobby_name`, and seat-matching — an ADR-level refactor with perception-POV regression risk. Per CLAUDE.md "No half-wired features / fix it right," shipping the resolver unwired (dead code) or rewiring blind (regression) are both wrong. The UI guard fully fixes the observable doubled-header bug on its own. User endorsed the split (2026-05-28, "Please continue" on the ship-UI-only + spin-out recommendation).
  - Severity: major (story scope change — server work deferred to a new story)
  - Forward impact: The doubled-header bug is fixed and shippable. The Cloudflare-email identity (the *root* fix) moves to a designed follow-up story (Architect + ADR). 67-4 should be re-scoped to ui-only by SM. No sibling story currently depends on the server resolver.

### Architect (reconcile)

**Reviewed existing entries:**
- *TEA (RED)* — "No deviations from spec; scope expanded by user direction (logged as Delivery Finding)." Accurate. The expansion-then-contraction of scope is correctly tracked as findings + the Dev deviation, not as a TEA test-design deviation.
- *Dev (implementation)* — "Descoped server repo to ui-only; backed out the resolver test." Verified all 6 fields are substantive and accurate: spec source (67-4 session scope `repos: server,ui`) is real; the cited code (`websocket_session_handler.py:2561` `party_location(perspective=sd.player_name)` → `session.py:956` `character_locations.get(perspective)`) is confirmed by direct read; the implementation description matches the diff (one guard clause in `CharacterPanel.tsx`, server branch reset to `develop`); severity (major — scope change) and forward impact (root fix deferred to a designed story) are correct. No correction needed.

**Missed deviations:** No additional deviations found. The server descope is the sole material deviation and Dev captured it completely.

**AC deferral verification:** 67-4 carried no formal ac-completion AC table (bug story; ACs derived from the title + epic context + session test plan). The observable ACs — no doubled `X — X` header (suppression tests), differ-case suffix retained (protective lock), same/different/empty name combos (the 4-test block) — are all DONE and verified green. The server-side identity-payload AC (stop conflating player-vs-character) is **DEFERRED**, not dropped: it is the root fix, blocked on the `sd.player_name`-as-character-name-key decoupling (ADR-level), and is carried forward to a designed follow-up story + ADR per the spec-check guidance. No deferred AC was inadvertently addressed or invalidated during review (Reviewer verdict APPROVED, both enabled specialists clean).

**Definitive manifest:** One major deviation (server scope deferred), fully documented, user-endorsed, Architect-concurred. Bug fixed; root cause routed to a new story. Clean to finish.

## Dev Assessment

**Implementation Complete:** Yes (descoped to ui-only — see deviation)
**Files Changed:**
- `sidequest-ui/src/components/CharacterPanel.tsx` — added `player_id !== character.name` guard to the controlling-player suffix (mirrors `CharacterSheet.tsx`), suppressing the doubled `X — X` MP header.

**Tests:** Full sidequest-ui suite **1642/1642** passing (run `67-4-dev-green-ui-full`); CharacterPanel + CharacterSheet **95/95** including the 67-4 block (4) with no 56-1 regression (run `67-4-dev-green-ui`).
**Branches:**
- `sidequest-ui` `feat/67-4-mp-identity-mapping-doubled-header` — RED tests (`5617595`) + guard fix (`e0eb479`), **pushed**.
- `sidequest-server` same branch — reset to `develop`, no changes (to be torn down at finish; server descoped).

**Server work deferred:** Cloudflare-email player-identity refactor → new story (resolver contract + perception-POV constraint preserved in Delivery Findings). See Dev deviation for why it can't be wired safely in this bug-fix branch.

**Handoff:** To Reviewer (Colonel Potter) for review of the UI guard. SM to re-scope 67-4 → ui-only and file the follow-up identity story.
## Architect Assessment (spec-check)

**Spec Alignment:** Drift detected (scope reduction — server descoped to ui-only)
**Mismatches Found:** 1

- **Server identity-mapping fix not implemented** (Missing in code — Architectural, Major)
  - Spec: Story scoped `server,ui`; SM/TEA contract called for resolving player identity server-side (`Cf-Access-Authenticated-User-Email` → `Host`) and ending the peer `pname = char.core.name` conflation (ADR-037 player-vs-character split).
  - Code: UI-only — `CharacterPanel.tsx` gained the `player_id !== character.name` guard (mirroring `CharacterSheet.tsx`); the server branch was reset to `develop` with no changes.
  - Recommendation: **D — Defer.** Verified Dev's blocking finding in code: `websocket_session_handler.py:2561` calls `party_location(perspective=sd.player_name)`, and `party_location` resolves `character_locations.get(perspective)` (`session.py:956`) — `sd.player_name` is a **character-name key**, not merely a player label. Rewiring it to an email/host identity would return `None` and break perception/location POV for the local player. The server identity refactor therefore requires separating player-identity from the character-name key across `connect.py`/`session.py`/`views.py` plus cross-socket peer-identity storage — an ADR-level change that cannot be done safely inside a bug-fix branch. Concur with the descope.

**Architectural guidance for the follow-up story:**
- File an **ADR**: "Authenticated player identity via Cloudflare Access header + player-vs-character identity split" — covers (1) the transport trust boundary (`Cf-Access-Authenticated-User-Email`, local-dev `Host` derivation), and (2) decoupling `sd.player_name` from its character-name-key role so identity and perception no longer share a field. This sits squarely under ADR-037's umbrella; reference it.
- Reuse-first: the resolver contract Dev/TEA designed (`resolve_player_identity(headers)` + `MissingPlayerIdentityError`) is sound and should be recreated in the follow-up — it is not the risky part. The risk is the `sd.player_name` decoupling; the ADR must specify the new identity field and every read site that must migrate off `player_name`-as-character-key.

**Decision:** Proceed (UI guard satisfies the observable ACs — no doubled `X — X`; differ-case preserved). Server work cleanly deferred to a designed follow-up. Next: TEA verify.
## TEA Assessment (verify)

**Simplify:** Skipped the 3-agent fan-out — the production change is a single guard clause (`&& character.player_id !== character.name`) added to one conditional, reusing `CharacterSheet.tsx`'s established pattern verbatim. No duplication introduced, no dead code, no over-engineering surface to analyze.

**Quality-pass:**
- `npx tsc --noEmit` — clean.
- `npx eslint src/components/CharacterPanel.tsx` — clean.
- Full sidequest-ui suite 1642/1642 (Dev run `67-4-dev-green-ui-full`); CharacterPanel/CharacterSheet 95/95 incl. the 67-4 block.

**Verify verdict:** GREEN, minimal, idiomatic. No regressions. Proceed to review.
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | Yes | clean | none | N/A |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings |

**All received:** Yes (2 enabled returned clean; 7 disabled via workflow.reviewer_subagents)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred

## Reviewer Assessment

**Verdict: APPROVED**

**Diff reviewed:** `sidequest-ui` — `CharacterPanel.tsx` (one guard clause + comment) and `CharacterPanel.test.tsx` (+151, the Story 67-4 block). Server branch: no changes (descoped).

### Rule Compliance (lang-review/typescript — 13 checks, enumerated against the diff)
- **#1 Type-safety escapes:** No `as any`, `@ts-ignore`, or non-null `!` in the new code. PASS.
- **#4 Null/undefined:** `header.textContent ?? ""` correctly uses `??` (textContent is nullable); the production guard is string truthiness + `!==` equality. PASS.
- **#6 React/JSX:** Change is a single conditional-render clause — no `useEffect`/deps change, no `key={index}`, no `dangerouslySetInnerHTML`. PASS.
- **#8 Test quality:** All 4 new tests carry meaningful assertions (`queryByTestId().not.toBeInTheDocument()`, regex `not.toMatch(/Kael\s*—\s*Kael/)`, `getByTestId().toBeInTheDocument()` + `toMatch`). No `as any`, no vacuous assertions, includes a protective lock against over-suppression and a wiring-shaped roster test. PASS.
- **#10 Input validation:** No new `JSON.parse`/`as T`/user-input cast; `player_id`/`name` are display strings already on `CharacterSheetData`. PASS.
- Checks #2/#3/#5/#7/#9/#11/#12/#13: not applicable to a one-clause display guard (no generics/enums/modules/async/build-config/error-handling/fix-regression surface introduced). PASS by non-applicability.

### Adversarial notes (what the tests don't cover — assessed, non-blocking)
- **Near-duplicate by case/whitespace:** `player_id = "kael"` vs `name = "Kael"`, or trailing whitespace, would pass `!==` and render `"Kael — kael"`. Not a defect of this change — `CharacterSheet.tsx`, the mirrored reference, has the identical exact-match semantics, and the deferred Cloudflare-email identity story makes the colliding-handle case moot at the source. Not blocking.
- **Descope (server deferred):** Already substantively reviewed and concurred by the Architect (spec-check) — verified Dev's `sd.player_name`-as-character-name-key finding is real (`party_location` keys on it). Approved deferral; the follow-up identity story + ADR carry the root fix.

### Verdict rationale
Minimal, correct, idiomatic — the guard mirrors `CharacterSheet.tsx` so the two header surfaces can no longer disagree. Both enabled subagents clean. Full UI suite 1642/1642; tsc + eslint clean. The observable doubled-`X — X` bug is fixed with a protective lock preventing over-suppression. **Approved to merge.**

### Subagent coverage (enabled specialists — tagged)
- **[PREFLIGHT]** clean — 1642/1642 tests GREEN, 0 code smells, tsc + eslint clean. No finding to confirm or dismiss.
- **[SEC]** clean — 0 findings, 0 rule violations. The change *narrows* the render condition (removes the doubled-`X — X` path), exposes no previously hidden identity, and the falsy branch yields `null` (no silent fallback). Server-side SP suppression (`App.tsx:941-943`) remains the load-bearing control; this guard is display-layer defense-in-depth. No finding to confirm or dismiss.
