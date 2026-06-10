---
story_id: "93-4"
jira_key: ""
epic: ""
workflow: "tdd"
---
# Story 93-4: History section lore-link plumbing to the ADR-048 store

## Story Details
- **ID:** 93-4
- **Jira Key:** (none — Jira integration not enabled)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-10T23:01:23Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-10T22:22:55Z | 2026-06-10T22:24:53Z | 1m 58s |
| red | 2026-06-10T22:24:53Z | 2026-06-10T22:40:33Z | 15m 40s |
| green | 2026-06-10T22:40:33Z | 2026-06-10T22:46:32Z | 5m 59s |
| review | 2026-06-10T22:46:32Z | 2026-06-10T22:54:47Z | 8m 15s |
| green | 2026-06-10T22:54:47Z | 2026-06-10T22:57:49Z | 3m 2s |
| review | 2026-06-10T22:57:49Z | 2026-06-10T23:01:23Z | 3m 34s |
| finish | 2026-06-10T23:01:23Z | - | - |

## Story Context

**Title:** History section lore-link plumbing to the ADR-048 store

**Type:** story (feature)

**Points:** 5

**Priority:** p3

**Repos:** sidequest-server, sidequest-ui

**Epic:** 93 — Chargen Freeform Resolution & Character History Surface

**Problem:** The History section (93-3) is designed as the home for player-linked lore. This story attaches it to the existing lore store. Story 75-15 already persists creation-seed lore fragments via the ADR-048 lore RAG store — surface the fragments linked to THIS character/player in the History section beneath the origin block.

**Acceptance Criteria:**
- Server exposes a typed list of player-/character-linked lore fragments (creation-seed + player-attributed) in the character snapshot, filtered by perception/visibility.
- The History section renders a 'Lore' subsection under the origin block listing those fragments (title/summary), linking to the lore page where a route exists.
- Fragments are sourced from the existing ADR-048 store (75-15 creation-seed persistence) — no new authoring; a fresh session's seeded fragments appear after creation.
- An unresolvable linked fragment id is skipped loudly (logged), never fabricated (No Silent Fallbacks).
- OTEL/observability: emit a span/log for lore-link resolution count per character so the GM panel can confirm fragments reached the surface.
- Wiring + perception test: a character's linked fragments reach the snapshot and render; another player's private fragments do NOT leak into this character's History.

**Dependencies:** 93-3 (History section container), 93-2 (creation_answers field)

## Branches

- **sidequest-server:** feat/93-4-history-lore-link-plumbing (develop)
- **sidequest-ui:** feat/93-4-history-lore-link-plumbing (develop)

## Sm Assessment

**Setup decision:** Story is genuinely ready. All three dependencies satisfied:
- **93-3** (History section container) — done, ui #373 merged.
- **93-2** (creation_answers field) — done.
- **75-15** (creation-seed lore persistence) — **done & archived** (`sprint/archive/75-15-session.md`). Note: `pf sprint story field 75-15 status` misleadingly reports `backlog` and `show` reports "not found" because 75-15 is out of the active sprint. Do not be fooled — the wiring is live: `rag.character_creation_lore_seeded` exists at `sidequest-server/sidequest/server/websocket_handlers/chargen_mixin.py:1463`. The fragments this story surfaces DO exist in the ADR-048 store.

**Load-bearing risk for TEA/Dev:** This is *plumbing existing fragments to the surface*, not authoring. The RED tests should (1) assert the snapshot exposes the typed fragment list filtered to this character/player, (2) prove the perception firewall — another player's private fragments must NOT leak into this character's History (ADR-104/105), and (3) prove the No-Silent-Fallback path: an unresolvable fragment id is logged/skipped loudly, never fabricated. AC5 wants an OTEL span for lore-link resolution count (the GM-panel lie detector per CLAUDE.md OTEL principle) — make sure a wiring test reaches it.

**Scope guard:** No new lore authoring. If implementation feels like it needs to *create* fragments, that's a signal the upstream seed (75-15) isn't producing them for the test fixture — investigate the seed path before inventing data.

## Delivery Findings

No upstream findings at setup.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Improvement** (non-blocking): Creation-seed fragment ids are not player-scoped — `lore_char_creation_<scene_id>_<choice_index>` (lore_seeding.py:217). In MP, two PCs who pick the SAME choice_index in the same scene collide on id and the store dedupes (one fragment, shared). The 93-4 value-match link surfaces it for both, which is correct *only because they made the same pick*. Affects `sidequest/game/lore_seeding.py` (would need per-player id scoping for true attribution). Out of 93-4 scope; surfaces if a future MP story needs strict per-player lore ownership. *Found by TEA during test design.*
- **Question** (non-blocking): AC5 says emit "a span/log for lore-link resolution count per character." The RED test asserts a `lore_retrieval` watcher event (reason=`character_history_link`, `resolved_count`) fired from the views path — mirroring the existing chargen-seed `_watcher_publish` at chargen_mixin.py:1467. Dev should confirm whether to also emit a dedicated OTEL *span* (à la `lore_established_span`) vs the watcher event alone; the test only requires the watcher event reaches the hub. Affects `sidequest/server/views.py` (emit site) or `sidequest/game/lore_linking.py` (if emitted from the resolver via the local-import span pattern). *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): The `character_history_link` watcher event fires on every `party_member_from_character` build (i.e. every PARTY_STATUS for a post-93-2 PC), not once like the chargen seed. Honest but higher-frequency than the seed emit. Affects `sidequest/server/views.py` (emit site). If the Lore tab gets noisy, gate the emit on a state change or move it to a once-per-session path — not needed for correctness. *Found by Dev during implementation.*
- **Resolved** (non-blocking): The TEA AC5 span-vs-event Question is answered — implemented as the watcher event (see Dev deviation above), consistent with the sibling `character_creation_seed` emit. *Found by Dev during implementation.*
- **Question** (non-blocking, rework round 1): Reviewer recommended adding a `character` key to the OTEL `lore_retrieval` payload. Applying it as-is BREAKS the wiring test `test_lore_link_emits_resolution_count_watcher_event` — that test asserts `"Wiring Player" in str(fields.get("character") or fields.get("player_name"))`, and a truthy `character` (= `character.core.name`, e.g. "Solo") short-circuits the `or` so the player_name fallback never fires. Adding the key therefore requires a coordinated TEA test change (assert `player_name == ...` and/or `character == core.name`). Deferred to a TEA pass rather than edited in green-rework (Dev does not modify tests). The event already carries `player_name`, which identifies the source for the GM panel. Affects `sidequest/server/views.py:386` + `tests/integration/test_lore_link_wiring.py:282`. *Found by Dev during rework.*

### Reviewer (code review)
- **Gap** (blocking): `by_choice` typed `dict[tuple[str, str], object]` produces 4 pyright errors and disables static type-checking on the projection accesses. Affects `sidequest/game/lore_linking.py:56` (annotate as `dict[tuple[str, str], LoreFragment]`, import `LoreFragment` from `sidequest.game.lore_store`). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): OTEL `lore_retrieval` payload lacks a `character` key (carries `player_name`); add `character.core.name` for cleaner GM-panel per-PC attribution and to tighten the wiring test's identity assertion. Affects `sidequest/server/views.py:386`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `views.py` pre-existing pyright errors at lines ~602/628 (`object`-typed seat_lookup) are unrelated to 93-4 but sit in the same file — a future cleanup story could annotate `slot_to_player_id`'s return. Affects `sidequest/server/views.py` (out of 93-4 scope). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `sidequest-ui/src/types/payloads.ts:8` file header still says "Mirrors sidequest-protocol (Rust) payload structs" — stale post-ADR-082 (Python port). Pre-existing, not in this diff. Affects `sidequest-ui/src/types/payloads.ts` (header update). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): The lore-link wiring test (`test_lore_link_wiring.py:49`) skips when `sidequest-content` is absent — confirm CI checks out the content subrepo so AC1/AC3/AC5/AC6 wiring is actually exercised, not silently skipped. Affects CI config. *Found by Reviewer during code review.*

## TEA Assessment

**Tests Required:** Yes
**Reason:** 5-pt feature spanning server (snapshot exposure, perception firewall, OTEL, no-silent-fallback) + UI (History Lore subsection). Pure plumbing of existing ADR-048 fragments — high wiring/firewall risk, exactly the No-Silent-Fallback + perception territory that needs paranoid coverage.

**Test Files:**
- `sidequest-server/tests/game/test_lore_linking.py` — pure unit tests for the resolver `linked_lore_for_character` (8 tests): happy path + typed shape, legacy-empty graceful, world/event-lore exclusion, unpicked-sibling-choice exclusion, cross-character firewall, No-Silent-Fallback (caplog WARNING on unresolvable choice answer, no fabrication), freeform-answers-don't-warn, no-fabricated-route.
- `sidequest-server/tests/integration/test_lore_link_wiring.py` — wiring + OTEL (4 tests): real C&C chargen → seed store → `party_member_from_character` → `sheet.lore_fragments` serialized (AC1/AC3); unpicked-calling non-leak; cross-character firewall through views (AC6); `lore_retrieval`/`character_history_link` watcher event carries per-character `resolved_count` (AC5).
- `sidequest-ui/src/components/__tests__/CharacterSheet.test.tsx` — appended "Story 93-4: History Lore subsection" describe (6 tests): Lore subsection under History; title+summary rows; route→anchor; routeless→plain text (no fabricated link); graceful absent; graceful empty.

**Tests Written:** 18 tests covering all 6 ACs.
**Status:** RED (verified) — server unit fails `ModuleNotFoundError: sidequest.game.lore_linking`; server integration fails `AttributeError: CharacterSheetDetails ... 'lore_fragments'`; UI 93-4 block fails on missing `history-lore` testid. Zero fixture bugs; 93-3 suite (12 tests) still PASSES — no regression.

### Rule Coverage

| Rule (CLAUDE.md / SOUL) | Test(s) | Status |
|---|---|---|
| No Silent Fallbacks (unresolvable id logged+skipped, never fabricated) | `test_unresolvable_choice_answer_is_skipped_loudly_not_fabricated`, `test_no_fabricated_lore_route_when_no_page_exists`, UI `a fragment WITHOUT a lore_route renders plain text` | failing (RED) |
| OTEL Observability (GM-panel lie detector — resolution count) | `test_lore_link_emits_resolution_count_watcher_event` | failing (RED) |
| Every Test Suite Needs a Wiring Test (reachable from production path) | `test_real_chargen_flow_exposes_lore_fragments_in_sheet_payload` (real chargen→views→serialized) | failing (RED) |
| No Source-Text Wiring Tests (behavior/OTEL, not grep) | OTEL watcher-capture + serialized-payload assertions (no `read_text()` greps) | n/a (satisfied by construction) |
| Perception firewall (ADR-104/105 intent — no cross-PC leak) | `test_cross_character_firewall_shared_store`, `test_cross_character_firewall_through_views` | failing (RED) |
| No Stubbing (no premature/placeholder lore surface) | graceful-absent/empty UI tests + inherited 93-3 AC-5 guard | passing (guard intact) |

**Rules checked:** 6 of 6 applicable rules have test coverage.
**Self-check:** 0 vacuous tests — every test has a meaningful assertion; the two graceful-absence UI tests assert `queryByTestId(...).toBeNull()` (real negative), the No-Silent-Fallback test asserts both the skip AND the loud WARNING.

**Handoff:** To Dev (Naomi Nagata) for GREEN implementation.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/game/lore_linking.py` (new) — `linked_lore_for_character(store, character)`: indexes the session store's `CharacterCreation` fragments by `(scene_id, choice_label)`, matches each `kind=="choice"` creation_answer, projects to `LinkedLoreFragment`. Unresolvable choice → WARNING + skip (no fabrication); freeform → skipped silently; `lore_route` left None.
- `sidequest-server/sidequest/protocol/models.py` — new `LinkedLoreFragment` model + `CharacterSheetDetails.lore_fragments` field (default `[]`, backward-compatible).
- `sidequest-server/sidequest/server/views.py` — `party_member_from_character` resolves `lore_fragments` from `sd.lore_store`, sets it on the sheet, and emits the `lore_retrieval`/`character_history_link` watcher event (`resolved_count`) when the PC has creation_answers.
- `sidequest-ui/src/types/payloads.ts` — new `LinkedLoreFragment` interface.
- `sidequest-ui/src/components/CharacterSheet.tsx` — `CharacterSheetData.lore_fragments` + a `history-lore` subsection beneath the origin block; title links via `lore_route` when set, else plain text; hidden when empty/absent.

**Tests:** GREEN — server 12/12 (8 unit + 4 integration), UI 47/47 (93-4 block + 93-3 regression + rest). Regression guards pass: `test_snapshot_field_governance` + `test_creation_answers_wiring` (10/10). ruff clean on touched files; `tsc --noEmit` clean.

**Branches (pushed):**
- `sidequest-server`: feat/93-4-history-lore-link-plumbing
- `sidequest-ui`: feat/93-4-history-lore-link-plumbing

**Self-review:**
- Wired end-to-end: store → resolver → views → CharacterSheetDetails → serialized PARTY_STATUS → React History/Lore subsection. Not just a field add — `linked_lore_for_character` has a non-test consumer (`views.py`), proven by the real-chargen integration test.
- No Silent Fallbacks honored (loud WARNING + skip on unresolvable; no fabricated route).
- OTEL lie-detector wired (per-character resolved_count).
- Minimal: no abstractions beyond what the 18 tests demand.

**Handoff:** To TEA (Amos Burton) for verify phase (simplify + quality-pass).

### Dev Rework (round 1 — addressing Reviewer REJECT)
- **Blocking fix applied:** `sidequest/game/lore_linking.py` — imported `LoreFragment` and annotated `by_choice: dict[tuple[str, str], LoreFragment]` (was `object`). `uv run pyright sidequest/game/lore_linking.py` → **0 errors** (was 4). Type safety on `.id/.metadata/.content/.source` restored.
- **Non-blocking folded in:** softened the module docstring's MP firewall claim to acknowledge same-pick fragment sharing (Reviewer [DOC] + TEA scoping finding).
- **Non-blocking NOT taken (with rationale):** the recommended OTEL `character` key was tried then reverted — it breaks the wiring test's `or`-assertion and needs a coordinated TEA test change (logged as a Dev finding). views.py has no net change this round.
- **Verification:** 12 (93-4) + 10 (regression) = 22 tests GREEN; ruff clean; pyright clean on the touched file. Pushed to `feat/93-4-history-lore-link-plumbing`.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 80 GREEN; lint/tsc/eslint clean; pyright NOT installed in its sandbox (skipped); 1 note (content-gated skip) | confirmed 1 note (deferred), 0 blocking |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings — self-assessed [EDGE] below |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings — self-assessed [SILENT] below |
| 4 | reviewer-test-analyzer | Yes | findings | 8 (all test-strengthening) | confirmed 0 blocking, 6 deferred (non-blocking), 2 dismissed |
| 5 | reviewer-comment-analyzer | Yes | findings | 4 | confirmed 1 (the `object` dict — folds into #9), 2 deferred, 1 dismissed (pre-existing) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings — self-assessed [TYPE] below (ran pyright manually) |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings — self-assessed [SEC] below |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings — self-assessed [SIMPLE] below |
| 9 | reviewer-rule-checker | Yes | findings | 3 violations (PY-3 low, PY-10 low, ADD-4 medium) | confirmed 1 (PY-3 → blocking), 1 dismissed (PY-10), 1 deferred (ADD-4) |

**All received:** Yes (4 enabled returned; 5 disabled pre-filled and self-assessed)
**Total findings:** 1 confirmed blocking, 8 deferred (non-blocking), 4 dismissed (with rationale)

## Rule Compliance

Mapped to `.pennyfarthing/gates/lang-review/{python,typescript}.md` + CLAUDE.md/SOUL doctrine. Exhaustive over the 3 server + 2 UI changed units.

- **PY-1 Silent exception swallowing:** COMPLIANT — no try/except in any changed file.
- **PY-3 Type annotations at boundaries:** **VIOLATION** — `lore_linking.py:56` `by_choice: dict[tuple[str, str], object]`. Values are concrete `LoreFragment`; accesses `.id/.metadata/.content/.source` (lines 78-91) on the `object`-typed value produce **4 pyright errors** (verified locally) and disable static checking on the module's core projection. The function signature itself is fully annotated (compliant); the defect is the over-broad internal value type. → Finding #1 (blocking).
- **PY-4 Logging coverage/correctness:** COMPLIANT — `lore_linking.py:74` WARNING on unresolvable link, lazy `%s` formatting, no PII (in-game character name only), correct severity for fail-loud absence.
- **PY-6 Test quality:** COMPLIANT on vacuity rules — specific assertions throughout; `# type: ignore[method-assign]` carries a specific code. (Test-analyzer's "could be stronger" notes are non-vacuous edge gaps, deferred.)
- **PY-10 Import hygiene:** COMPLIANT (dismissed rule-checker finding) — function-body imports at `views.py:157,163` match the established house style of `party_member_from_character`, which local-imports `CharacterSheetDetails`, `NonBlankString`, `resolve_inventory`, etc. throughout. Not inconsistent within this function. No circular import introduced (server→game is one-way).
- **PY-11 Input validation at boundaries:** COMPLIANT — resolver inputs are internal typed objects (`LoreStore`, `Character`); OTEL payload values come from session data, not raw user input.
- **TS-4 Null/undefined handling:** COMPLIANT — `CharacterSheet.tsx:33` `data.lore_fragments && .length > 0` guards undefined; `:44` `fragment.lore_route ?` handles null; `payloads.ts` types `lore_route?: string | null` explicitly.
- **TS-5 Module/declaration:** COMPLIANT — `import type` used for the type-only `LinkedLoreFragment` import.
- **TS-6 React/JSX:** COMPLIANT — `key={fragment.fragment_id}` is a stable server id, not array index. (rule-checker's theoretical `javascript:` href is server-origin / same-origin trusted; see [SEC].)
- **ADD-1 No Silent Fallbacks:** COMPLIANT — unresolvable choice → WARNING + skip, no fabrication (`lore_linking.py:72-81`); routeless fragment → plain text, no fabricated href (`CharacterSheet.tsx:51-53`); `lore_route=None` not invented.
- **ADD-2 No half-wired features:** COMPLIANT — `linked_lore_for_character` has a production consumer at `views.py:380`; field flows store → resolver → sheet → serialized PARTY_STATUS → React render. Proven by the real-chargen wiring test.
- **ADD-4 OTEL Observability:** COMPLIANT (with deferred polish) — `views.py:386` emits `lore_retrieval`/`character_history_link` with `resolved_count`. rule-checker notes the payload lacks a `character` key (has `player_name`, which identifies the source); adding `character.core.name` is recommended polish, non-blocking.
- **ADD-5 Pydantic extra=forbid:** COMPLIANT — `LinkedLoreFragment` sets `model_config = {"extra": "forbid"}`, matching sibling `CreationAnswer`.
- **ADD-6 Backward compatibility:** COMPLIANT — `CharacterSheetDetails.lore_fragments = Field(default_factory=list)` and TS `lore_fragments?` optional; legacy payloads validate. Verified by `test_snapshot_field_governance` (passing).

## Observations

- **[TYPE] HIGH** `by_choice: dict[tuple[str, str], object]` defeats type-checking on the projection — `sidequest/game/lore_linking.py:56`. Verified: `uv run pyright sidequest/game/lore_linking.py` → 4 errors (`.id`, `.metadata`, `.content`, `.source` unknown on `object`). Disables static verification on the exact logic that defines correctness. Corroborated by [DOC] (comment-analyzer HIGH) and [RULE] (PY-3).
- **[SILENT] VERIFIED good** — No Silent Fallbacks honored: unresolvable choice answer logs WARNING and skips (`lore_linking.py:73-81`); freeform absence is expected and silent by design; no fabricated rows. Evidence: `lore_linking.py:72-81`, tests `test_unresolvable_choice_answer_is_skipped_loudly_not_fabricated` + `test_freeform_answers_do_not_warn`. Self-assessed (subagent disabled); concurs with rule-checker ADD-1.
- **[EDGE] VERIFIED good** — composite `(scene_id, choice_label)` key prevents cross-scene label collision; unpicked sibling choices excluded (`lore_linking.py:71`). Duplicate label within one scene → last-write-wins (`:64`), acceptable (labels unique per scene). Test-analyzer flags these edges as untested (deferred), but the code is correct. Self-assessed (subagent disabled).
- **[SEC] VERIFIED good** — no user-controlled input reaches the resolver (internal `LoreStore`/`Character`); the `<a href={lore_route}>` is server-origin and currently always `None` for creation-seed. Theoretical `javascript:` href injection requires a compromised server (same-origin WS trust model). Non-blocking; note for future if `lore_route` ever carries user-influenced data. Self-assessed (subagent disabled).
- **[SIMPLE] VERIFIED good** — resolver is minimal (index + match + project); no dead code, no over-engineering, no abstractions beyond the tests. Self-assessed (subagent disabled).
- **[TEST] MEDIUM (deferred)** — OTEL wiring test asserts `resolved_count == resolved` where `resolved` derives from the same call (test_lore_link_wiring.py:277), and uses one character so per-character isolation of the count is unproven. Plus missing edge tests (choice value matching a different scene's fragment; duplicate label across scenes). Non-blocking: production code is correct and all 6 ACs are covered; these would harden the suite.
- **[DOC] MEDIUM (deferred)** — module docstring (`lore_linking.py:22-25`) overclaims the firewall as absolute ("never see each other's pick") — same-pick MP collision exists (TEA already logged the underlying fragment-id scoping). Soften the claim. Also `views.py` `answered_scenes` counts freeform answers, making the GM-panel delta vs `resolved_count` less legible.
- **[RULE] DISMISSED** — PY-10 function-body imports: matches the house style of `party_member_from_character` (dismissed with evidence above).
- **[DOC] DISMISSED** — `payloads.ts:8` "Mirrors Rust protocol" stale header: PRE-EXISTING (not in this diff); the diff's own new interface correctly says "Mirrors sidequest-server protocol." Out of scope; noted as non-blocking cleanup for a future story.

## Devil's Advocate

Assume this code is broken. Where does it fail? The resolver runs on **every** `party_member_from_character` call — i.e. every PARTY_STATUS broadcast, for every PC, in every multiplayer session. It iterates the *entire* session lore store building `by_choice` each time. For a long campaign whose store has accumulated hundreds of arc/world/creation fragments, that's a full linear scan per PC per status push — O(fragments × PCs) per broadcast. Not catastrophic at playgroup scale (≤5 PCs, hundreds of fragments), but it is recomputed work with no memoization, and the OTEL event fires every time too (Dev's own flagged finding). A confused GM watching the Lore tab will see the `character_history_link` event spam on every status tick and may misread it as activity. Worse: `answered_scenes` includes freeform answers, so a PC who answered 5 scenes but only made 2 choices shows `answered_scenes=5, resolved_count=2` — a reader cannot tell whether 3 are "expected freeform" or 3 are genuine unresolved-choice WARNINGs without reading source. That undermines the lie-detector's purpose.

What would a malicious/confused *content author* do? Author two choices in one scene with the **same label**. The `by_choice` index silently drops one (last-write-wins, `:64`) — the PC who picked the dropped one would still resolve (the answer value matches the surviving fragment's label), so the content is right by luck, but a third choice with that label would mask the others. No warning fires. A content author renaming a choice label after a save exists would orphan that PC's fragment → WARNING + skip (correct, fail-loud — good).

The type defect is the real lurking bug-amplifier: because `fragment` is `object`, a future refactor renaming `LoreFragment.content` → `LoreFragment.body` would **not** be caught by pyright here — `fragment.content` would raise `AttributeError` at runtime on the next PARTY_STATUS, crashing the sheet build for any PC with linked lore. The `object` annotation converts a compile-time catch into a production crash. That is precisely why this is blocking: it's not cosmetic, it removes the safety net from the module's hot path. The UI side is safe (null-guarded, stable keys); the server type hole is the one that bites.

## Reviewer Assessment

**Verdict:** REJECTED

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] | `by_choice` typed `dict[tuple[str, str], object]` — produces 4 pyright errors and disables static type-checking on `.id/.metadata/.content/.source`, the module's core projection. A future `LoreFragment` attribute rename becomes a runtime crash on the PARTY_STATUS hot path instead of a compile-time catch. | `sidequest-server/sidequest/game/lore_linking.py:56` (+ accesses 78-91) | Import `LoreFragment` (already in `sidequest.game.lore_store`, alongside the existing `LoreSource, LoreStore` import) and annotate `by_choice: dict[tuple[str, str], LoreFragment]`. Re-run `uv run pyright sidequest/game/lore_linking.py` → expect 0 errors. |

**Recommended while in the file (NON-blocking — fold into the same green-rework, no test changes needed):**
- Add `"character": character.core.name` to the `lore_retrieval` payload (`views.py:386`) — resolves the test-analyzer's loose `or` assertion and the rule-checker ADD-4 note; the GM panel then has both character + player_name.
- Soften the `lore_linking.py` module docstring firewall claim (lines 22-25) to acknowledge same-pick MP fragment sharing (TEA's logged scoping caveat).
- Consider renaming `answered_scenes` → `choice_answers`/`total_answers` (or splitting) so the GM-panel `resolved_count` delta is self-explanatory.

**Deferred to a potential follow-up / TEA verify (NON-blocking):** the test-strengthening set — concrete `resolved_count == 1` assertion, two-character OTEL isolation test, scene_id-isolation edge, duplicate-label-across-scenes edge, removing the inert `toBeInTheDocument()`. Production code is correct; these harden the suite.

**Subagent dispatch (enabled specialists incorporated):** [TYPE]/[DOC] — the `object`-dict type defeat (comment-analyzer HIGH); [RULE] — PY-3 confirmed, PY-10 dismissed, ADD-4 deferred (rule-checker); [TEST] — 8 test-strengthening findings, all non-blocking, deferred (test-analyzer); [SILENT]/[EDGE]/[SEC]/[SIMPLE] — self-assessed (subagents disabled), all VERIFIED good. See `## Observations` for per-tag detail.

**Why REJECT and not APPROVE-with-followup:** the fix is a one-line annotation + one import that restores type safety on the module's hot path. The preflight's pyright was skipped (not installed in its sandbox), so the dev-exit lang-review (a checklist scan, not a real pyright run) never caught it. Leaving 4 type-checker errors and a disabled safety net in newly-merged code, when the fix is trivial, fails the project's own pyright standard (CLAUDE.md). This is lint/type-only — green-rework, not a test redesign.

**Handoff:** Back to Dev (Naomi Nagata) for the type-annotation fix (green-rework).

---

## Subagent Results (Round 2 — re-review of rework)

Rework delta is **logic-free**: `lore_linking.py` `by_choice` annotation `object → LoreFragment` (+ import) and a docstring softening; views.py net-unchanged (the recommended `character` key was tried then reverted). The round-1 fan-out examined all of this code; round-2 re-runs preflight for fresh mechanical numbers and self-assesses the diff-based domains against the 7-line, zero-behavior delta.

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 22 server + 47 UI GREEN; ruff/tsc clean; 0 smells | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | No logic change — round-1 [EDGE] assessment stands |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | No control-flow change — round-1 [SILENT] VERIFIED stands |
| 4 | reviewer-test-analyzer | N/A | not re-run | none | No test files changed since round 1; deferred findings unchanged |
| 5 | reviewer-comment-analyzer | N/A | self-assessed | 1 (round-1 [DOC]) now RESOLVED | docstring softened per round-1 finding — verified accurate |
| 6 | reviewer-type-design | No | Skipped | disabled | **Round-1 [TYPE] HIGH RESOLVED** — `uv run pyright lore_linking.py` → 0 errors (was 4) |
| 7 | reviewer-security | No | Skipped | disabled | No change — round-1 [SEC] VERIFIED stands |
| 8 | reviewer-simplifier | No | Skipped | disabled | Annotation narrowing is a simplification, not added complexity |
| 9 | reviewer-rule-checker | N/A | self-assessed | PY-3 RESOLVED | `by_choice` now concretely typed; PY-10 dismissal stands; ADD-4 deferred |

**All received:** Yes (preflight re-run clean; diff-based domains self-assessed against the logic-free delta)
**Total findings:** 0 new; round-1 blocking [TYPE] HIGH **resolved** (pyright 0 errors); round-1 [DOC] medium **resolved** (docstring softened)

## Reviewer Assessment (Round 2 — APPROVED)

**Verdict:** APPROVED

The single round-1 blocker is fixed and verified:
- **[TYPE] RESOLVED** — `by_choice: dict[tuple[str, str], LoreFragment]` (was `object`). `uv run pyright sidequest/game/lore_linking.py` → **0 errors, 0 warnings** (was 4 errors). Type safety restored on the `.id/.metadata/.content/.source` projection — a future `LoreFragment` attribute rename is now a compile-time catch again. Evidence: `lore_linking.py:40,56`.
- **[DOC] RESOLVED** — module docstring (`lore_linking.py:18-25`) now accurately states same-pick MP fragment sharing instead of claiming absolute isolation. Verified against the code's actual `(scene_id, choice_label)` match semantics.
- **[SILENT] VERIFIED** — unchanged; No-Silent-Fallbacks intact (`lore_linking.py:73-81` WARNING+skip, no fabrication).
- **[EDGE] VERIFIED** — unchanged; composite-key scene isolation intact (`lore_linking.py:71`).
- **[SEC] VERIFIED** — unchanged; no user-controlled input reaches the resolver; routeless fragments render plain text.
- **[SIMPLE] VERIFIED** — the annotation change is a net simplification (concrete type < `object`); no complexity added.
- **[TEST] NOTE** — no test files changed; round-1 test-strengthening suggestions remain deferred (non-blocking; all 6 ACs covered, 69 tests green across both repos). The Dev correctly deferred the OTEL `character` key because adding it breaks the wiring test's `or`-assertion — that's a coordinated TEA change, not green-rework. I concur with the deferral; `player_name` already identifies the source for the GM panel.
- **[RULE] VERIFIED** — PY-3 resolved; PY-10 dismissal (function-body imports match house style) stands; ADD-1/ADD-2/ADD-5/ADD-6 (No-Silent-Fallbacks, wiring, extra=forbid, backward-compat) all compliant.

**Data flow traced:** chargen choice → `seed_lore_from_char_creation` → session `LoreStore` → `linked_lore_for_character` (scene_id+choice_label match) → `CharacterSheetDetails.lore_fragments` → serialized PARTY_STATUS → React `history-lore` subsection. Firewall holds (value-match); No-Silent-Fallbacks honored end-to-end.
**Pattern observed:** clean projection-at-the-sheet-seam (`views.py::party_member_from_character`), consistent with the 93-2 `creation_answers` precedent.
**Error handling:** unresolvable choice → loud WARNING + skip, never fabricated (`lore_linking.py:73-81`).

**Non-blocking items carried forward as Delivery Findings** (do not block merge): OTEL `character` key + wiring-test tightening (TEA follow-up), per-build emit frequency, stale Rust header in payloads.ts, content-gated wiring-test skip in CI, MP fragment-id scoping. None affect correctness.

**Handoff:** To SM (Camina Drummer) for finish-story.

## Design Deviations

No deviations from spec at setup.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Perception firewall tested via choice-label match, not ADR-104/105 status-effect filtering**
  - Spec source: context-story-93-4.md, AC1 + AC6 ("filtered by perception/visibility"; "another player's private fragments do NOT leak")
  - Spec text: "a typed list ... filtered to the character's creation-seed + player-attributed fragments (perception/visibility honored)" / "another player's private fragments do NOT leak into this character's History"
  - Implementation: Tests pin the firewall as a per-character value match — `fragment.metadata['choice_label'] == Character.creation_answers[].value` — rather than ADR-104/105 perception rewriting. Rationale grounded in the data model: `seed_lore_from_char_creation` (lore_seeding.py:206) seeds a fragment for EVERY choice in EVERY scene (including unpicked ones), all into one shared per-session `LoreStore`; the only correct per-character discriminator is the answer the PC actually gave.
  - Rationale: Creation-seed lore is durable *sheet* content, not per-turn *broadcast* content, so ADR-104/105 status-effect perception (blinded→audio_only etc., perception_rewriter.py) does not apply here. The leak vector AC6 actually guards is cross-character contamination in the shared store; the choice-label match closes it. Tested both at unit level (`test_cross_character_firewall_shared_store`) and through the real views path (`test_cross_character_firewall_through_views`).
  - Severity: minor
  - Forward impact: If Dev later needs true player-attribution (e.g. MP where two PCs pick the *same* choice_index in the same scene and the seeder dedupes the fragment id), the value-match is insufficient and the fragment id would need player scoping — out of scope for 93-4 (flagged as a Delivery Finding).
- **Contract names defined by the RED suite (story delegated technical approach to TEA/Dev)**
  - Spec source: context-story-93-4.md, "Technical Approach" ("_Approach hints to be refined by TEA/Dev_")
  - Spec text: "expose the player-/character-linked lore fragments ... a typed list of {fragment_id, title/summary, source}"
  - Implementation: The tests pin concrete symbols the GREEN phase must satisfy — `sidequest/game/lore_linking.py::linked_lore_for_character(store, character) -> list[LinkedLoreFragment]`; protocol model `LinkedLoreFragment{fragment_id, title, summary, source, lore_route: str|None}` in `protocol/models.py`; `CharacterSheetDetails.lore_fragments`; UI `CharacterSheetData.lore_fragments` + `LinkedLoreFragment` in `types/payloads.ts`; testids `history-lore` / `history-lore-item`; OTEL `lore_retrieval` event with `reason="character_history_link"` + `resolved_count`.
  - Rationale: TDD requires concrete targets; names follow the 93-2/93-3 precedents (`CreationAnswer`/`creation_answers`, `history-lore` anchor reserved by 93-3 AC-5).
  - Severity: minor
  - Forward impact: Dev may rename via push-back, but must update the pinning tests in lockstep.
- **`lore_route` left None for creation-seed fragments (no lore-page route exists yet)**
  - Spec source: context-story-93-4.md, AC2 ("linking to the lore page where one exists")
  - Spec text: "render those as a 'Lore' subsection ... linking to the lore page where a route exists"
  - Implementation: Server tests assert `lore_route is None` for creation-seed fragments; UI tests cover BOTH branches (route present → anchor; route absent → plain text, no fabricated href). No lore-page route was found in the UI router during exploration.
  - Rationale: No Silent Fallbacks — a dead/invented link is worse than no link. The route branch is still exercised so the wiring is proven for when a lore page lands.
  - Severity: minor
  - Forward impact: When a lore-page route ships, the linker can populate `lore_route` without test changes (the anchor branch is already covered).

### Dev (implementation)
- **AC5 emitted as a watcher event, not a dedicated OTEL span**
  - Spec source: context-story-93-4.md, AC5
  - Spec text: "emit a span/log for lore-link resolution count per character so the GM panel can confirm fragments reached the surface"
  - Implementation: `party_member_from_character` (views.py) calls `_watcher_publish("lore_retrieval", {reason: "character_history_link", resolved_count, answered_scenes, player_name, genre_slug, world_slug}, component="rag")` — the same mechanism as the existing chargen-seed emit at `chargen_mixin.py:1467`, not a `Span.open(...)` OTEL span.
  - Rationale: AC says "span/log"; the watcher event IS the GM-panel signal and matches the sibling `character_creation_seed` lore emit exactly, keeping the Lore tab's event shape consistent. The RED test (`test_lore_link_emits_resolution_count_watcher_event`) asserts the watcher event, satisfied here. Resolves the TEA Question finding in favour of the watcher event.
  - Severity: minor
  - Forward impact: none — if a Jaeger trace span is later wanted, it can be added alongside without changing the event contract.

### Reviewer (audit)
- **TEA: Perception firewall via choice-label match (not ADR-104/105)** → ✓ ACCEPTED by Reviewer: sound. The data model (shared store, fragment-per-choice incl. unpicked) makes the `(scene_id, choice_label)` match the only correct discriminator; creation-seed lore is sheet content, not broadcast content, so status-effect perception doesn't apply. Verified the firewall holds in `lore_linking.py:71` and is tested both unit + views-path.
- **TEA: Contract names defined by RED suite** → ✓ ACCEPTED by Reviewer: story explicitly delegated technical approach to TEA/Dev; names follow 93-2/93-3 precedent. Implemented faithfully.
- **TEA: `lore_route` left None (no lore page yet)** → ✓ ACCEPTED by Reviewer: correct No-Silent-Fallbacks call. UI exercises both branches; no dead href fabricated.
- **Dev: AC5 as watcher event, not OTEL span** → ✓ ACCEPTED by Reviewer: matches the sibling `character_creation_seed` emit (chargen_mixin.py:1467); AC says "span/log" and the watcher event is the GM-panel signal. Consistent with house pattern.