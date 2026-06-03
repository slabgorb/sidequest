---
story_id: "59-15"
jira_key: ""
epic: ""
workflow: "trivial"
---
# Story 59-15: Engagement e2e validation — beneath_sunden + road_warrior: confrontation/movement/magic actually fire mechanically (OTEL span proof)

## Story Details
- **ID:** 59-15
- **Jira Key:** (none)
- **Workflow:** trivial
- **Stack Parent:** none
- **Points:** 2
- **Type:** chore

## Overview

This story validates end-to-end that the engagement pipeline (confrontation, movement, magic) actually fires mechanically in two worlds:
- **beneath_sunden** (caverns_and_claudes genre)
- **road_warrior** (road_warrior genre)

The validation is **proof by OTEL spans**, not narrative conviction. Claude is excellent at improvising convincing narration with zero mechanical backing. Only the GM dashboard (via OTEL watcher events) proves the subsystems are actually engaged.

## Technical Approach

### Acceptance Criteria

1. **Confrontation Firing:** Initiate a combat encounter in beneath_sunden. Verify:
   - OTEL spans emitted for confrontation initialization
   - Participant roster correctly populated (player + opponent)
   - Resolution mechanics (dice, ability checks) emit OTEL events
   - No confrontation → narration fallback (Claude improvising without mechanical backing)

2. **Movement Firing:** Execute movement commands in road_warrior. Verify:
   - OTEL spans for location transitions
   - State transitions (entering/exiting zones) emit watcher events
   - No silent fallback to narrative-only movement

3. **Magic Firing:** Cast a spell in both worlds (if available). Verify:
   - OTEL spans for spell resolution
   - Effect application emits mechanical telemetry
   - No magic → narration-only fallback

### Testing Strategy

1. Run playtest scenarios against beneath_sunden and road_warrior with `--otel-verbose` enabled
2. Tail the OTEL dashboard (`just otel`) to verify span emission in real-time
3. Check that each interaction emits expected span types (e.g., `confrontation.init`, `movement.transition`, `spell.cast`)
4. Log findings in the **Delivery Findings** section below

## Sm Assessment

**Routing:** setup → implement (dev / Agent Smith). Trivial/phased workflow, 2pt chore, single repo (sidequest-server).

**What this story is:** Pure validation by observability — prove that confrontation, movement, and magic actually fire *mechanically* in beneath_sunden and road_warrior, with OTEL spans as the evidence, not narration. This is the project's "GM panel is the lie detector" doctrine applied as an acceptance test for Epic 59 (Intent Router / Mechanical-Engagement Spine, ADR-113/123).

**Guidance for dev:**
- This is a chore: the deliverable is a repeatable e2e check (playtest scenario or integration test) plus a findings record, not a new feature. Don't add engine code unless a wiring gap is discovered.
- If a subsystem turns out NOT to emit spans (Claude improvising without mechanical backing), that is a *finding* — log it under Delivery Findings as a blocking Gap and surface it; do not paper over it. Per "No Silent Fallbacks," a missing span is a bug to report, not to hide.
- Server work happens in the `sidequest-server` subrepo (currently on `develop` — branch there per the dual-clone topology; subrepo PRs target develop).
- Validate against running services (`just otel` for the GM dashboard) and the playtest driver.

**No upstream findings from setup.**

## Dev Assessment

**Implementation Complete:** Yes (validation performed; harness hardened; findings routed)

**Files Changed (orchestrator repo — scripts/ + scenarios/ are orchestrator-owned):**
- `scripts/playtest.py` — five harness fixes: PLAYER_ACTION `round` stamping; end-of-run contact-sheet (`--contact-sheet`/`--no-contact-sheet`/`--render-drain-timeout`); render-drain phase; one-action-per-resolved-turn gate; `character.class` caster pin + class-aware stat arrangement.
- `scripts/playtest_messages.py` — `make_action_msg` now sends the required `round` field.
- `scenarios/beneath_sunden_engagement.yaml` (new) — Mage descends into the Sünden Deep; exercises confrontation/movement/magic.
- `scenarios/road_warrior_engagement.yaml` (new) — vehicular pack; confrontation/movement + the AC-B3 magic-negative probe.

**Validation outcome (both packs, isolated runs, server on oq-3 content, Jaeger live):**
- **Confrontation: PASS** in BOTH packs (`encounter.confrontation_initiated` — beneath ×2, road ×1).
- **Movement: ENGAGED** in both (emits `movement.region_mode`, not the context-predicted `movement.resolved`).
- **Magic: routed gap** — `magic_working` dispatch omits `params['actor']` in both packs (+ `magic_state=None`/59-14 in beneath). The OTEL lie-detector flagged every magic gap (`dispatch_engagement.magic_working.mismatch`).
- Contact sheets built for both (render-drain working; road sheet has 2 captioned tiles).

**Tests:** N/A (validation chore — no unit tests; evidence is the captured OTEL spans). Driver changes are `py_compile`-clean and `ruff`-clean (the one remaining ruff hit, `asyncio.TimeoutError`→`TimeoutError`, was auto-normalized).

**Findings routed (see Delivery Findings):** (1) magic_working `params['actor']` contract → intent-router/magic owner; (2) `movement.resolved` vs `movement.region_mode` context-span reconciliation; (3) mismatch-watcher false-positive on degraded-to-hint dispatch; (4) 59-14 magic_state still None for beneath+Mage; (5) harness: don't chain scenario runs without a daemon cooldown.

**Branch:** `feat/59-15-engagement-e2e-validation` (orchestrator). **Handoff:** To review.

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-06-03T18:00:03Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-03T15:43:32Z | 2026-06-03T15:45:40Z | 2m 8s |
| implement | 2026-06-03T15:45:40Z | 2026-06-03T17:51:15Z | 2h 5m |
| review | 2026-06-03T17:51:15Z | 2026-06-03T18:00:03Z | 8m 48s |
| finish | 2026-06-03T18:00:03Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Reviewer (code review)
- **Improvement** (non-blocking): New pure helpers `AutoChargen._preferred_choice`, `_arrange_stat`, the `make_action_msg` `round` field, and the `turn_in_flight` gate are cheaply unit-testable (synthetic inputs, no content/server) and load-bearing, but untested — and `scripts/tests/test_playtest_split.py` already exists for this module. Empirically proven by the live runs (Mage offered+picked; 7 decompose for 5 actions), so non-blocking, but a fast-follow adding ~4 assertions (default+explicit `round`, class-match vs no-match `_preferred_choice`, caster `_arrange_stat`) would close the gap. Affects `scripts/tests/`. *Found by Reviewer during code review.*
- **Gap** (non-blocking, PRE-EXISTING): `scripts/tests/test_playtest_split.py` is substantially rotted — 9 failures on this branch (16 on `main`) from stale references to removed functions/flags (`make_chargen_choice`→`make_chargen_scene_choice`, `receiver`, `--dashboard-only`, multiplayer-run) AND the suite imports `rich` which is absent from the sidequest-server venv (must run `uv run --with rich`). Predates 59-15; needs a separate cleanup. Affects `scripts/tests/test_playtest_split.py`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): "No Silent Fallbacks" consistency in the post-run contact-sheet/drain code: `_drain_renders` silently skips a `json.JSONDecodeError` frame (the main `_loop` logs `non-JSON frame` — inconsistent); `build_contact_sheet` returns only the placed-tile count so a partial sheet (3 of 5 renders failed) prints "2 render(s)" without flagging the 3 skipped; `ImageFont.load_default()` OSError → `font=None` drops all captions silently. All in best-effort post-run artifact code, but each should log loudly per the project principle. Affects `scripts/playtest.py`. *Found by Reviewer during code review (confirms reviewer-silent-failure-hunter [SILENT]).*
- **Improvement** (non-blocking): `_fetch_image_bytes` buffers `resp.content` with no size cap and `follow_redirects=True`; `build_contact_sheet` decodes server bytes via PIL with no `MAX_IMAGE_PIXELS` guard. Trusted-local-server source makes this LOW, but a size cap + pixel ceiling are cheap hardening for a tool that fetches+decodes network images. Affects `scripts/playtest.py`. *Found by Reviewer during code review (confirms reviewer-security [SEC]).*
- **Improvement** (non-blocking, cosmetic): contact-sheet tiles are top-pinned with no vertical centering, so a landscape thumbnail leaves a gap and its caption sits in blank space (`build_contact_sheet` pastes at `(ox, y)`, caption at `y + thumb_px + 4`). Affects `scripts/playtest.py`. *Found by Reviewer during code review (confirms reviewer-edge-hunter [EDGE]).*
- **Improvement** (non-blocking, the one I'd most want fixed): `_emit_contact_sheet` catches only `ContactSheetError`, not `OSError`/`PermissionError` from `out_path.parent.mkdir` / `sheet.save`. In the `--span-jsonl` path `_emit_contact_sheet` runs BEFORE span capture, so a bad `--contact-sheet` path or a full disk would crash the run and skip the PRIMARY span artifact — contradicting the contact-sheet's own "best-effort, never changes exit code" design intent. Wrap the `build_contact_sheet` call to also swallow `OSError` so the best-effort sheet can never endanger span capture. Affects `scripts/playtest.py`. *Found by Reviewer during code review.*

### Dev (implementation)
- **Gap** (blocking, RESOLVED in-story): The oq-3 headless playtest driver (`scripts/playtest_messages.py::make_action_msg`) did not send `round` in PLAYER_ACTION, but the server's `PlayerActionPayload` (sidequest-server `protocol/messages.py:66`) requires `round: int` (ge=0, Story 71-10 fail-loud). Every scenario action was rejected with "Malformed message … PLAYER_ACTION.payload.round Field required" and the run aborted before any engagement could be measured — i.e. the validation harness itself was broken against current server schema (the dual-clone schema-drift wall the justfile already warns about). Fixed in this story: driver now latches the authoritative round from inbound traffic and stamps it on each action. *Found by Dev during implementation.*
- **Improvement** (non-blocking, DONE in-story): Headless playtests queue daemon image renders end-to-end but the driver disconnected before the async IMAGE messages landed, so the rendered output was unreviewable. Added end-of-run **contact-sheet** generation to `scripts/playtest.py` (`--contact-sheet`, `--no-contact-sheet`, `--render-drain-timeout`) plus a render-drain phase that waits (bounded) for queued renders to arrive before disconnecting, then montages them into a captioned PNG. Operator-requested. *Found by Dev during implementation.*
- **Bug** (non-blocking): The driver's IMAGE display path (`playtest_messages.py::render_message`) read `payload.get("image_url")`, but `ImagePayload` (server `protocol/messages.py:649`) carries the field as `url`. The console `[RENDER]` line therefore printed an empty URL. The new contact-sheet collector reads the correct `url`; the display line still reads `image_url` and could be tidied. Affects `scripts/playtest_messages.py`. *Found by Dev during implementation.*
- **Question** (non-blocking, RESOLVED in-story): In the beneath_sunden auto-chargen run the driver sent 4 actions but Jaeger captured only 2 `narration.turn` spans (3 `intent_router.decompose`). Actions outpaced turn resolution (action N+1 submitted while N still active), collapsing turns. RESOLVED: added a one-action-per-resolved-turn gate (`turn_in_flight`, cleared only on NARRATION_END; idle nudge forces past it). After the fix the 5-action beneath_sunden run captured **7 `intent_router.decompose`** spans with all legs distinctly attributed. Affects `scripts/playtest.py`. *Found by Dev during implementation.*

### Dev (validation results — 2026-06-03, server on oq-3 content, Jaeger live)

**Pack A — beneath_sunden (Mage, descends into the Sünden Deep). Run EXIT=0, 5 actions, 909 spans captured.**
- **AC-A1 Confrontation — PASS.** Router dispatched `confrontation` (conf 0.9 / 0.92); engine engaged: `encounter.confrontation_initiated` ×2, plus `tool.write.advance_confrontation`, `watcher.confrontation_lifecycle` ×3. The descent met real hostiles in the deep (vs the safe Ropefoot camp), so the leg fired for real before the narrator.
- **AC-A2 Movement — ENGAGED, span-name discrepancy.** Router dispatched `movement` (conf 0.95 / 0.92); engine engaged and location advanced (Ropefoot → Sünden Deep), but the emitted span is **`movement.region_mode` ×2**, NOT the `movement.resolved` the context predicted. The region-mode dungeon path (ADR-106) emits a different span than the context's §"Exact OTEL spans" assumed. **Finding (non-blocking):** reconcile context-story-59-15 / the movement proof-span list with the region-mode path, or have the region-mode path also emit `movement.resolved`. Routes to the movement/ADR-106 owner.
- **AC-A3 Magic — DISPATCHED, ENGINE FAILED, lie-detector CAUGHT it (routes to 59-14).** Router dispatched `magic_working` (conf 0.85) for the searing-bolt cast, but the engine raised `MagicWorkingParseError('magic_working emitted but world has no magic_state loaded')` (server log `subsystems.dispatch_failed` / `orchestrator.subsystem_error`), so `magic.working` never fired and the post-turn watcher emitted **`dispatch_engagement.magic_working.mismatch`** (the only mismatch of the run). caverns_and_claudes HAS genre `magic.yaml` and Mage carries `magic_access: innate_v1`, yet `snapshot.magic_state` is None at runtime for beneath_sunden — exactly the AC-A3-gated-on-59-14 case the context predicted. **Finding (blocking the magic leg): 59-14 ("load magic_state for worlds with caster classes") is marked done but magic_state is still None for beneath_sunden + Mage — Mage casting remains a no-op. Re-open / route to 59-14.** This is 59-15 working as designed: the OTEL lie-detector flagged narration-without-mechanics.
- **AC-X1 Lie-detector — 1 mismatch, correctly attributed** (the magic_working one above). `intent_router.failed` = 0, `movement.unresolved` = 0. The single mismatch is a true engagement gap, not a false positive.
- **AC-X2 Clean Subsystems (59-11 signal) — PASS.** `dispatch_bank` and `intent_router.subsystem` fire once per dispatched subsystem per turn; no `TypeError`/duplicate-run rows (59-11 landed).
- Contact sheet built: `/tmp/beneath_sunden-contact-sheet.png` (Ropefoot kept-fire landscape, captioned).

**Pack B — road_warrior / the_circuit. Run EXIT=1 — BLOCKED, route out.**
- Content now loads (server on oq-3 content; the earlier "no seedable lore" error was oq-1-clone drift, since fixed by the server restart). Chargen completes ("Pilot"), the opening narration completes server-side (`session.narration_complete duration_ms=15413`), the turn resolves — then **`ws.send_failed type=CHAPTER_MARKER error=` → `ws.disconnected code=1011`** (server log) and the driver sees "Server closed the connection" before sending a single action. No engagement legs could be measured.
- **Finding (blocking road_warrior validation):** the road_warrior opening drops the WebSocket with a 1011 during/after a `CHAPTER_MARKER` send. Needs its own investigation (CHAPTER_MARKER emission/serialization for the road_warrior opening, or connection-lifecycle) — out of 59-15's no-engine-code scope. Routes to the protocol/session owner. The two engagement scenarios are committed and reproducible the moment that block clears.

### Dev (validation results, cont. — road_warrior debug + isolation)

**The earlier "road_warrior blocked by CHAPTER_MARKER/ws-1011" was MISDIAGNOSED — root cause is back-to-back run contamination.** Re-ran road_warrior ALONE (not chained after beneath_sunden) → **EXIT 0, 812 spans, 6 `intent_router.decompose` for 5 actions, all legs exercised.** In the chained beneath→road run, the road client connection closed ~moments into the opening (server log `connection closed` right after `monster_manual.injected`, ~15s BEFORE the narration completed); the `ws.send_failed type=CHAPTER_MARKER error=` (empty error) + `code=1011` were the *server failing to send to an already-closed client* — a symptom, not the cause. The contamination signature: stale beneath_sunden renders (`render.broadcast_no_recipients room=2026-06-03-beneath_sunden-4/-5`) bleeding into the road session from the shared MLX daemon's backlog while the new run started. **Finding (non-blocking, harness/ops):** validation scenarios must not be chained without a cooldown / daemon-drain between them — the render-drain I added keeps the daemon busy, and starting a fresh run against a backed-up daemon drops the new client early. Affects the playtest harness when running multiple scenarios sequentially. NOT a road_warrior or CHAPTER_MARKER engine bug.

**Pack B — road_warrior / the_circuit (isolated run). EXIT=0.**
- **AC-B1 Confrontation — PASS.** Router dispatched `confrontation` (conf 0.92 / 0.85); `encounter.confrontation_initiated` ×1 + `tool.write.advance_confrontation` ×2, `watcher.confrontation_lifecycle` ×3. Vehicular combat-start engaged the engine for real.
- **AC-B2 Movement — ENGAGED via `movement.region_mode`** (same span-name discrepancy as beneath; see below). Router dispatched `movement` (conf 0.75).
- **AC-B3 Magic negative — PARTIAL.** `magic.working` = 0 (magic correctly never engages in a magic-less pack) ✓, and the router gave the casting-shaped action low confidence and **degraded it to a hint** (`decision=degraded_to_hint confidence=0.35` — the ADR-113 confidence gate working). BUT a `dispatch_engagement.magic_working.mismatch` STILL fired (same `params['actor']` evidence). AC-B3 says "critically NO mismatch" — so this leg is a **partial pass**: magic stays mechanically dark, but the lie-detector false-positives on the degraded dispatch.
- Contact sheet: `/tmp/road_warrior-contact-sheet.png` — TWO captioned tiles (expressway-tunnel landscape + neon-station portrait); multi-image montage confirmed.

**Cross-pack engine findings (reproducible in BOTH packs — route to intent_router/magic owner):**
1. **`magic_working` dispatch omits required `params['actor']`** — every magic dispatch (beneath Mage cast, road hex) carries evidence "malformed dispatch: router omitted required params['actor'] for magic_working". In beneath this compounds with `magic_state=None` (59-14); in road it surfaces on a degraded-to-hint dispatch. The IntentRouter→magic_working param contract is broken. Routes to ADR-113/123 intent-router or the magic_working handler owner.
2. **Movement proof-span mismatch with the context.** Both packs emit `movement.region_mode` on movement engagement and NEVER `movement.resolved` (the span context-story-59-15 §"Exact OTEL spans" predicts). Movement DOES engage mechanically. Reconcile the context's movement proof-span, or have the region-mode path also emit `movement.resolved`.
3. **`dispatch_engagement.magic_working.mismatch` false-positives on a degraded-to-hint dispatch** (road AC-B3) — a dispatch the confidence gate intentionally degraded should not be scored as a "dispatched-but-didn't-engage" lie. Mismatch-watcher refinement.

**NET (both packs, isolated):** Confrontation FIRES for real in both a dungeon pack and a vehicular pack (AC-A1 + AC-B1 PASS). Movement engages in both (via `movement.region_mode`). Magic is the consistent gap — a broken `params['actor']` contract (+ 59-14 magic_state for beneath). The OTEL lie-detector did its job: every magic gap was flagged. The earlier road "block" was a harness back-to-back-run artifact, now understood. The mechanical-engagement spine (Epic 59 / ADR-113/123) is **proven live for confrontation + movement across two structurally different packs**; magic routes to its owners.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Wrote harness tooling code in a "no-code" validation story**
  - Spec source: context-story-59-15.md §Technical Guardrails
  - Spec text: "This is a trivial-workflow validation story — a playtest-driver run + span inspection, not TDD code. Do not write engine code."
  - Implementation: Edited `scripts/playtest.py` + `scripts/playtest_messages.py` — (1) added the required `round` field to PLAYER_ACTION, (2) added end-of-run contact-sheet generation + render-drain.
  - Rationale: (1) was a hard prerequisite — the validation could not run at all because the driver was rejected by the server's current schema (the harness was broken, not the engine). (2) was a direct, live Operator request ("add that fact to the tool, so we make a contact sheet at the end"). Neither touches **engine** code; both are playtest-harness (dev-tool) changes, which the guardrail's "no engine code" intent permits.
  - Severity: minor
  - Forward impact: none on engine; improves the shared playtest harness for all future scenario runs (the round fix unblocks every headless playtest against current server schema).
- **Additional harness tooling beyond the initial round + contact-sheet (Operator directed "all the things")**
  - Spec source: context-story-59-15.md §Technical Guardrails + live Operator direction
  - Spec text: "a playtest-driver run + span inspection, not TDD code. Do not write engine code."
  - Implementation: Three further `scripts/playtest.py` additions — (3) one-action-per-resolved-turn gate (`turn_in_flight`), (4) `character.class` caster pin in AutoChargen, (5) class-aware stat arrangement (`_CLASS_STAT_PRIORITY`) so a requested caster qualifies. All harness-side; no engine code.
  - Rationale: needed to make the validation actually exercise each leg cleanly — without (3) actions outran turns (2 of 4 captured); without (4)+(5) auto-chargen always drew a non-caster (Fighter) so the magic leg could never fire. The Operator explicitly chose maximum validation depth ("all the things").
  - Severity: minor
  - Forward impact: none on engine; the playtest driver now reliably drives one action per turn and can pin a class/caster for any caster-gated validation.

### Reviewer (audit)
- **"Wrote harness tooling code in a no-code validation story"** → ✓ ACCEPTED by Reviewer: the guardrail's intent is "no ENGINE code"; all edits are in `scripts/` (the playtest harness) + `scenarios/` — both orchestrator dev-tooling, not engine. (1) the `round` fix was a hard prerequisite (the harness was rejected by the server's current schema — without it zero validation was possible) and (2) the contact-sheet was a direct Operator request. Sound.
- **"Additional harness tooling (Operator directed 'all the things')"** → ✓ ACCEPTED by Reviewer: turn-pacing gate, caster pin, and class-aware stats were each necessary to exercise the legs cleanly (verified: 7 decompose for 5 actions; Mage offered+picked in the run log) and were explicitly Operator-directed. No engine surface touched. The scope expansion is justified and the changes are well-isolated and reversible.
- No undocumented deviations found — the diff matches the logged deviations.
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (compile/ruff/yaml all pass; 1 low note) | confirmed 0, dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | Yes | findings | 11 (mostly low; 1 high-confidence drain-timeout, 1 med cosmetic) | confirmed 2, dismissed 9 (unreachable/handled) |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 3 | confirmed 3 (non-blocking, routed) |
| 4 | reviewer-test-analyzer | Yes | findings | 4 | confirmed 2, dismissed 2 (proven by live run) |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | findings | 2 (both low) | confirmed 2 (non-blocking, routed) |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (5 enabled returned, 4 disabled pre-filled)
**Total findings:** 9 confirmed (all non-blocking), 11 dismissed (with rationale), 0 deferred

## Reviewer Assessment

**Verdict:** APPROVED

This is a trivial validation-chore story whose deliverable is captured OTEL spans, plus harness hardening + reproducible scenarios. The change is well-isolated dev-tooling (`scripts/` + `scenarios/`), touches no engine/auth/tenant surface, is `py_compile`- and `ruff`-clean, and does not regress the (already-rotted) test suite. No Critical/High findings. Approving with five non-blocking findings routed for follow-up (see Delivery Findings).

**Observations (evidence-backed):**
- `[VERIFIED]` `make_action_msg` `round` change does not break the existing test — `scripts/tests/test_playtest_split.py:197` `test_make_action_msg` asserts only `type` + `payload["action"]`; it passes with the new payload (ran with `uv run --with rich`: test passes). The added `round` field is correct per `PlayerActionPayload` (`sidequest-server/protocol/messages.py:66`, `ge=0`).
- `[VERIFIED]` `_drain_renders` negative-timeout is NOT a crash — empirically confirmed `asyncio.wait_for(timeout=-0.5)` raises `TimeoutError` (not `ValueError`), which is caught by `except TimeoutError: continue` and the `while time.monotonic() < deadline` re-check then exits the loop cleanly. The reviewer-edge-hunter `[EDGE]` ValueError claim is dismissed (modern-Python behavior).
- `[VERIFIED]` test-suite failures are PRE-EXISTING, not a regression — `scripts/tests/test_playtest_split.py` fails 16 against `main` and 9 on this branch (stale refs to removed `receiver`/`--dashboard-only`/`make_chargen_choice` + `rich` absent from server venv). My branch improves the count; the relevant `test_make_action_msg` passes.
- `[VERIFIED]` turn-pacing gate works — session run log shows the 5-action beneath_sunden run produced 7 `intent_router.decompose` spans (vs 2-for-4 before), and the Mage was offered+picked (`[2] Mage`), confirming `_preferred_choice`/`_arrange_stat`.
- `[MEDIUM]` New pure helpers (`_preferred_choice`/`_arrange_stat`/`round`/`turn_in_flight`) lack unit tests though the suite exists — `scripts/playtest.py` / `scripts/tests/`. Non-blocking (empirically validated + story is explicitly no-TDD), routed as a fast-follow.
- `[SILENT]` Three confirmed silent-fallback-vs-project-principle items in the best-effort contact-sheet/drain code (JSONDecodeError not logged in `_drain_renders`; partial-tile count; font-load fallback). Confirmed (rule-matching — not dismissed), severity downgraded to LOW (post-run artifact), routed.
- `[SEC]` Two LOW: `_fetch_image_bytes` no response size cap + `follow_redirects`; PIL decode without `MAX_IMAGE_PIXELS`. Trusted-local-server source → LOW, routed as cheap hardening.
- `[EDGE]` One MEDIUM-cosmetic: contact-sheet tiles top-pinned (no vertical centering) → landscape caption sits in blank space. Routed.
- `[TEST]` Covered above (pure-function coverage gap + pre-existing rot).
- `[DOC]`, `[TYPE]`, `[SIMPLE]`, `[RULE]` — subagents disabled via `workflow.reviewer_subagents`; reviewer self-checked: comments are accurate and rich (every new block is documented with rationale); types are sound (`set[str]`, `dict[str, str]`, `int | None`); no over-engineering (each helper is minimal); no project-rule violations found in the diff (no engine/security-critical types, no stringly-typed public API, no tenant data).

**Rule Compliance:**
- *No Silent Fallbacks* (CLAUDE.md, CRITICAL): the load-bearing paths comply (ContactSheetError raised loudly on missing Pillow; render-drain abandonment logged; `make_action_msg` round documented as server-validated). Three minor logging-consistency gaps in post-run artifact code confirmed as `[SILENT]` findings (non-blocking).
- *No Stubbing / Don't Reinvent*: compliant — no stubs; reuses existing `httpx`, `render_message`, `_react`, `make_chargen_scene_choice`.
- *No content in unit tests* (memory): compliant — no new unit tests added content; the new logic is pack-agnostic with the one documented caverns-scoped stat table (fallback-safe for other packs).
- *Wiring*: the new code is reachable from `amain` (`_emit_contact_sheet` called in both span/no-span paths; `_drain_renders` from both scenario-complete returns; `round` stamped on every `_send_next_action`). Verified in the diff.

**Devil's Advocate:** Argue this is broken. A hostile/confused operator points `--contact-sheet` at a path under a directory they lack write permission to → `out_path.parent.mkdir` raises `PermissionError`, which is NOT caught by `_emit_contact_sheet`'s `except ContactSheetError`, so it propagates and crashes the process AFTER the scenario completed — but the span-jsonl is written BEFORE `_emit_contact_sheet`? No: in `amain` the order is `rc = pt.run()` → `_emit_contact_sheet` → (span path) capture. In the no-span path `_emit_contact_sheet` runs last, so a crash only loses the contact sheet (validation already done). In the span path, `_emit_contact_sheet` runs BEFORE span capture (line ~1356), so a `PermissionError`/`OSError` from `sheet.save`/`mkdir` would abort before the spans are written — losing the primary artifact. This is a real but narrow edge (operator-supplied bad path) — a stressed filesystem (disk full on `sheet.save`) hits the same window. Mitigation worth a follow-up: wrap `_emit_contact_sheet`'s `build_contact_sheet` call to also swallow `OSError`/`PermissionError` (it already swallows `ContactSheetError`), so the best-effort sheet never endangers the span capture. A malicious server could feed a decompression-bomb image (covered by `[SEC]`). A confused user reading "2 render(s)" when 5 were expected is the partial-count `[SILENT]` finding. None of these corrupt the validation conclusion; the worst case (span capture skipped due to a contact-sheet OSError on a bad path) is operator-self-inflicted and recoverable by re-running. Adding the `OSError` swallow in `_emit_contact_sheet` is the one finding I'd most want fixed, but it does not rise to High for a dev tool with an easy re-run. (Added as a routed finding below.)

**Handoff:** To SM for finish-story.
## Impact Summary

**Mechanical-Engagement Spine Validation (Epic 59 / ADR-113/123):**

### Acceptance Criteria Assessment

| Criterion | Status | Evidence |
|-----------|--------|----------|
| **AC-A1: Confrontation fires mechanically** | **PASS** | beneath_sunden: `encounter.confrontation_initiated` ×2, `tool.write.advance_confrontation`, `watcher.confrontation_lifecycle` ×3 (909 spans captured) |
| **AC-B1: Confrontation in vehicular pack** | **PASS** | road_warrior: `encounter.confrontation_initiated` ×1, `tool.write.advance_confrontation` ×2, `watcher.confrontation_lifecycle` ×3 (812 spans captured, isolated run) |
| **AC-A2: Movement mechanics engaged** | **ENGAGED** | beneath_sunden: location advanced (Ropefoot → Sünden Deep), `movement.region_mode` ×2 spans (not `movement.resolved` — span-name reconciliation needed; routes to ADR-106 owner) |
| **AC-B2: Movement in vehicular pack** | **ENGAGED** | road_warrior: `movement.region_mode` spans (same span-name discrepancy; mechanical engagement confirmed) |
| **AC-A3: Magic mechanics engaged** | **BLOCKED** | beneath_sunden: `magic_working` dispatch routed but engine raised `MagicWorkingParseError` — `snapshot.magic_state` is None for beneath_sunden+Mage (59-14 marked done but not live); OTEL lie-detector flagged `dispatch_engagement.magic_working.mismatch` |
| **AC-B3: Magic negative (magic-free pack)** | **PARTIAL** | road_warrior: `magic.working` = 0 ✓ (magic correctly never engages), router degraded low-confidence hex to hint, BUT `dispatch_engagement.magic_working.mismatch` still fires (false-positive on degraded dispatch) |

### Routed Findings (Non-Blocking Engine Gaps)

1. **`magic_working` dispatch omits `params['actor']`** (ADR-113/123 intent-router owner) — both packs emit evidence "malformed dispatch: router omitted required params['actor']"; in beneath compounds with `magic_state=None` (59-14); in road surfaces on degraded dispatch
2. **Movement proof-span mismatch** (ADR-106 region-mode dungeon owner) — both packs emit `movement.region_mode` (not predicted `movement.resolved`); mechanical engagement confirmed but span-name reconciliation needed
3. **`dispatch_engagement.magic_working.mismatch` false-positive on degraded-to-hint dispatch** (mismatch-watcher owner) — road AC-B3: confidence gate intentionally degraded the dispatch, but lie-detector still scores it as "dispatched-but-didn't-engage"
4. **`magic_state` still None for beneath_sunden+Mage** (59-14 owner — marked done but not live) — magic access/innate_v1 requires `magic_state` loaded; without it every cast fails at engine layer

### Harness & Tooling Impact

- **PLAYER_ACTION schema compliance** (prerequisite fix): driver now stamps required `round` field; unblocks all future headless playtests against current server schema (sidequest-server `protocol/messages.py:66`)
- **Contact-sheet generation** (operator-requested): reproducible artifact capture from daemon image renders; both scenarios produce captioned montages (beneath: Ropefoot landscape; road: expressway-tunnel landscape + neon-station portrait)
- **Render-drain phase** (best-effort image collection): bounded wait for queued IMAGE messages before disconnection; prevents loss of in-flight renders
- **Turn-pacing gate** (`turn_in_flight`): ensures one action per resolved turn; beneath_sunden run produced 7 `intent_router.decompose` spans for 5 actions (vs 2-for-4 before)
- **Class-aware character pinning** (`_preferred_choice`, `_arrange_stat`, `_CLASS_STAT_PRIORITY`): auto-chargen can now pin a caster class; beneath_sunden run confirmed Mage offered+picked; enables magic-leg validation

### Validation Harness Lessons

- **Back-to-back scenario contamination** (non-blocking): earlier road_warrior "block" was daemon-backlog bleed from prior beneath_sunden run, not an engine bug. Scenarios must not chain without daemon cooldown; render-drain mitigates.
- **OTEL lie-detector working as designed**: single true-positive (magic_working for beneath_sunden+Mage); road AC-B3 false-positive on degraded dispatch identified for watcher refinement

### Net Assessment

**Engagement spine proven live for confrontation + movement** across two structurally different packs (dungeon + vehicular). **Magic remains blocked by engine gap** (59-14 magic_state + intent-router param contract). The validation scenarios and hardened harness are reproducible and committed; unblocks future mechanical-engagement validation.

