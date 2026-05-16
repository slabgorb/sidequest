# Anthropic SDK Migration — Phase E Acceptance Playtest

**Date:** 2026-05-16 (session ran 2026-05-14 → resumed/closed 2026-05-16 after in-session fixes)
**Genre / world:** caverns_and_claudes / caverns_sunden
**Mode:** **solo** (Keith, running solo as the acceptance gate — not the full playgroup. The plan template anticipated a multiplayer playgroup session; the reality was a solo acceptance run by the single most load-bearing reviewer: a 40-year GM playing as a player.)
**PC:** Fitz the Bald (Ashgate Ridge → Grimvault)
**Turns:** 9 narration rounds (9 narrator beats / 8 player declarations; 18 events: 9 NARRATION + 9 SCRAPBOOK_ENTRY)
**Save artifact:** `~/.sidequest/saves/anthropic-sdk-migration-acceptance-2026-05-16.db` — consolidated single-file snapshot of session slug `2026-05-14-caverns_sunden-28` (`PRAGMA quick_check` = ok; source `save.db`/`-wal`/`-shm` left byte-for-byte untouched; snapshot captured the 4 MB uncommitted WAL via a copy-then-checkpoint, so no acceptance turns were lost).

## Outcome

**ACCEPTED — with two in-session fixes plus one pre-merge fix.**

This was not a clean pass. During the session Keith caught the SDK narrator **confabulating world canon** — narrating place/lore detail that had no grounding in the genre/world LoreStore. For a system whose entire reason to exist is "good enough to fool a career GM" and whose core doctrine is *OTEL is the lie detector*, a confabulating narrator is the one unacceptable failure. Keith stopped, diagnosed the cause, ordered fixes, and explicitly approved continuing once they were implemented and verified. His merge call at the end was unambiguous: *"merge it, we are moving forward."*

The acceptance is therefore best read as: *the SDK narrator path is mechanically sound and genre-true once the lore-grounding context is actually plumbed into it; the migration's structural lie-detection (ADR-102/103) did its job by surfacing the confabulation, and a subsequent adversarial review caught a second confabulation vector before merge.*

## The confabulation incident and the two in-session fixes

**Root cause:** the SDK narrator path was constructing `TurnContext` without the world/session/lore handles the grounding tools need, and resuming a save by slug never re-seeded the per-genre/world `LoreStore`. With no canon to query, the model did what models do on empty context — it invented plausible-sounding world detail.

**Fix #1 — plumb TurnContext** (`sidequest-server` commit `83a1d9d`): plumb `world_id` / `session_id` / `store` / `lore_store` / `monster_manual` into the SDK `TurnContext` so `query_lore` / `lookup_monster` and the write tools operate against real session state.
- *Verification:* **live in Jaeger** — `narration.turn` spans now carry correct `world_id` / `session_id` / `turn`.

**Fix #2 — re-seed LoreStore on slug-resume** (`sidequest-server` commits `b7cf969` + `b68892e`): a save resumed by slug now re-seeds the genre + world `LoreStore` on connect, so a continued campaign has its canon loaded.
- *Verification:* **connect-level** — `lore.store_loaded_on_resume total=6` (was `0` before the fix).

**Honest evidence gap:** an end-to-end *live-turn* proof — `query_lore` returning `hit_count > 0` inside a real narration turn — was **not** captured. The accepted evidence is the connect-level lore-seed counter plus the unit/wiring tests for both fixes. Keith reviewed this gap and chose to move forward; it is recorded here rather than papered over. Recommended first post-merge follow-up: capture one live `query_lore hit_count>0` turn on `develop` and attach the Jaeger trace to this report.

Both in-session fixes went through spec-compliance + code-quality review to APPROVED before being accepted into the branch.

## Pre-merge fix (adversarial review, before the squash-merge)

An adversarial Reviewer pass on the full branch (no Criticals; branch judged safe to squash-merge) surfaced two **IMPORTANT** findings, both fixed before merge:

1. **`generate_encounter` / `generate_loadout` returned empty SUCCESS.** Both were registered as *live* narrator `@tool`s but returned `ToolResult.ok({combatants:[]…})` / `{items:[]…}` — empty success the SDK narrator could read and then confabulate phantom combat/loot from. This is the *same* SOUL/lie-detector failure class as the world-canon confabulation, and a "no half-wired features" violation.
   - **Fix** (`sidequest-server` commits `12d8186` + `874cf0d`): both tools now return `ToolResult.error(…, recoverable=False)` — a model-visible fatal error with an explicit "do not narrate combatants/items as if they exist" directive — while **still recording every OTEL intent attribute** (genre/difficulty/terrain/theme/`*_wired=False`), so the GM panel still shows *what the narrator asked for*. They stay registered (tool-use spec stability); Phase E+ may wire the real generators. New registry-dispatch wiring tests assert a valid call now yields `is_error=True` / `ERROR:` content.
2. **`SIDEQUEST_ANTHROPIC_CACHE_TTL=1h` silently failed.** The client set `cache_control ttl="1h"` but never sent the `extended-cache-ttl-2025-04-11` beta header, so the API rejected it at call time.
   - **Fix** (same commits): `"1h"` dropped from `CacheTtl` / `_VALID_TTLS`; the dead branch removed. `"5m"` (the API default) is the only supported TTL; `1h` is now rejected loudly at construction instead of failing at call time. Not a default-path change.

Three Minor findings were informational only (near-vacuous `test_sidecar_coverage_map.py`; intentional `last_text` carry-forward in `complete_with_tools`; streaming+`anthropic_sdk` asserts loudly on a non-default path) — no action.

Spec-compliance + code-quality review of the pre-merge fix: **APPROVED**.

## Cost telemetry — the real numbers (the plan's target was wrong)

The plan and the original PR-body draft asserted "**cost target hit: per-turn weighted average within $0.05–0.07**." **This is false and is corrected here and in the PR bodies.** No live per-turn rollup was instrumented for the solo session; the authoritative cost evidence is the **Task #4 8-scenario SDK spot-check** (run 2026-05-15, oq-1 `feat/anthropic-sdk-migration`, default `anthropic_sdk` backend, server traced → Jaeger):

| scenario | rc | turns | llm req | $ total | $/turn | cache hit % | tools/turn |
|---|--:|--:|--:|--:|--:|--:|--:|
| smoke_test | 0 | 3 | 10 | 0.595 | 0.198 | 59.0 | 2.33 |
| asymmetric_smoke | 0 | 2 | 4 | 0.209 | 0.104 | 58.9 | 2.50 |
| caverns_smoke | 0 | 7 | 19 | 1.234 | 0.176 | 59.4 | 1.57 |
| combat_otel | 0 | 9 | 37 | 1.873 | 0.208 | 74.6 | 4.89 |
| combat_stress | 0 | 8 | 27 | 1.274 | 0.159 | 73.9 | 3.12 |
| coyote_salvage_smoke | 0 | 3 | 8 | 0.529 | 0.176 | 58.9 | 2.33 |
| merchant_npc_test | 0 | 8 | 22 | 1.301 | 0.163 | 62.9 | 1.75 |
| otel_extended | 0 | 8 | 26 | 1.590 | 0.199 | 64.4 | 3.38 |
| **TOTAL** | — | **48** | **153** | **$8.61** | **$0.179** | **67.0** | **2.92** |

- **Weighted $/turn = $0.179** — ~**2.6×** the over-optimistic $0.05–0.07 target.
- **Cache hit = 67.0%** — **exceeds** the ~60% target.
- **2.92 tool calls/turn** average; mechanical spans (`orchestrator.process_action`, `watcher.state_transition`) fired in **8/8** scenarios → the lie-detector is engaged and narration is mechanically backed.
- 8/8 scenarios `rc=0`; 48 narration turns; $8.61 total for the spot-check.

**Why the miss is structural (and why it was accepted):** the tool-use loop is ~3.2 `llm.request` round-trips per narration turn. Prompt caching discounts *input tokens*, not *call count* — so caching cannot close a gap that comes from making more LLM calls per turn. This is inherent to native tool use (ADR-102), not a tuning bug. Keith reviewed the structural explanation and **accepted** the cost.

### Real-world cost projection (per *narration turn*, not per *player*)

The single most important framing the plan got wrong: **cost scales with merged narration turns, not with player count.** SideQuest's submit-and-wait turn barrier (ADR-036) bundles *all* PCs' declarations into *one* narration turn — a 4-player table and a solo player cost the same per turn. So session cost is `~$0.179 × (merged narration turns)`, independent of headcount:

| Session shape | Merged narration turns | Projected cost |
|---|--:|--:|
| Short scene / one-shot probe | ~15 | ~$2.7 |
| Typical 2 h table (any player count) | ~25–35 | **~$4.5–6.3** |
| Long 3–4 h session | ~50 | ~$9.0 |

A **2 h, 4-player session ≈ $4–9, ~$5–6 typical** — the same as a 2 h solo session of equal pacing. Watch live telemetry over the next 4–6 sessions; if $/turn drifts above ~$0.25, investigate cache-hit decay or tool over-use (combat turns at 4–6 tools/turn are the cost ceiling).

## Scenario parity gate — judgment call, not diff-against-baseline

**No pre-migration baseline recordings ever existed.** Phase E's "diff each SDK run against a recorded `claude -p` baseline" gate (plan Tasks 1–2) was therefore **N/A**. The applied gate was a **judgment-call**: span-tree sanity + cost/cache spot-check across the 8 scenarios above.

**Gate verdict: PASS** on span-tree sanity and cache; cost/turn materially exceeds the (over-optimistic) target — documented, non-blocking, escalated to and cleared by Keith's merge decision. This is recorded so a future reader does not mistake the absence of a baseline-diff for an un-run gate.

## Test / gate status (post-rebase)

- **Server suite: 5990 passed / 0 failed.** The previously-known **35 baseline failures** (`test_chargen_dispatch` 16, `test_scene_harness` 12, `test_scene_harness_hydrator` 7) are **no longer present** — they were resolved by `develop`'s 50-19 / 50-20 / 50-23 hydrator commits pulled in during the post-Phase-D rebase. The plan's "35 known fails are an accepted baseline exception" caveat is **moot**; it is *not* carried forward as an accepted exception.
- Server `ruff` ✓ · `pyright` on touched narrator/lore/tool files: 0 ✓
- Client `vitest` ✓ · client lint ✓ · daemon `ruff` ✓
- Pre-merge fix targeted suite: 32/32 ✓ (`tests/agents/tools/test_generate_encounter.py`, `test_generate_loadout.py`, `test_anthropic_sdk_client.py`, `test_anthropic_sdk_client_wiring.py`)

## Tool selection observations

- Mechanical/lie-detector spans (`orchestrator.process_action`, `watcher.state_transition`) fired in 8/8 spot-check scenarios — narration is backed by mechanics, not improvised.
- Combat turns drive the tool count (4.89 tools/turn on `combat_otel`, 3.12 on `combat_stress`) and the cost ceiling; quiet/narrative turns sit at 1.5–2.5 tools/turn.
- `generate_encounter` / `generate_loadout` are intentionally **not** wired (now fail loud rather than fake success) — any narration of a generated encounter/loadout on the SDK path is still a known gap, now structurally detectable instead of silently confabulated.

## Issues found

1. **World-canon confabulation** — *Critical, fixed in-session.* SDK narrator invented world detail with no LoreStore grounding. Cause: TurnContext not plumbed + LoreStore not re-seeded on slug-resume. Fixes `83a1d9d`, `b7cf969`, `b68892e`. Verified live (Jaeger ids) + connect-level (lore seed counter). **Decision: fix-before-merge — done.**
2. **`generate_encounter`/`generate_loadout` empty-success confabulation vector** — *Important, fixed pre-merge.* Now fatal-error + OTEL intent retained. Fixes `12d8186`, `874cf0d`. **Decision: fix-before-merge — done.**
3. **`SIDEQUEST_ANTHROPIC_CACHE_TTL=1h` silent failure** — *Important, fixed pre-merge.* `1h` dropped; loud rejection at construction. Same commits. **Decision: fix-before-merge — done.**
4. **No live-turn `query_lore hit_count>0` proof** — *Non-blocking gap.* Connect-level + tests accepted by Keith. **Decision: accept; capture on `develop` as first post-merge follow-up.**
5. **Per-turn cost ~2.6× the planned target** — *Non-blocking, structural.* Inherent to the tool-use loop; caching cannot close a call-count gap. **Decision: accept; monitor over 4–6 sessions.**
6. **Honest remaining follow-ups (not blocking merge):** `narrator_output_only` still injected on the SDK path (model can hedge with sidecars *and* tools); location region-canonicalization not run for SDK turns; `quest_updates` / `lore_established` in neither prompt; char-creation lore not re-seeded on resume; `generate_encounter`/`generate_loadout` still not truly wired (now just fail-loud). Each is a small contained story.

## Decision

- [x] **Merge to develop** — server PR → `develop`, orchestrator PR → `main`. Approved by Keith: *"merge it, we are moving forward."*
- [ ] Hold and fix issues before merge — *N/A; all fix-before-merge items resolved and reviewed APPROVED.*
- [ ] Revert — *N/A.*
