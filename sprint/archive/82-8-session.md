---
story_id: "82-8"
jira_key: ""
epic: "82"
workflow: "tdd"
---
# Story 82-8: Wire item narrative_weight / WealthTier gold->label consumer + OTEL + player-facing

## Story Details
- **ID:** 82-8
- **Jira Key:** (none - Jira not enabled)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-03T23:05:18Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-03T22:26:37Z | 2026-06-03T22:29:41Z | 3m 4s |
| red | 2026-06-03T22:29:41Z | 2026-06-03T22:40:18Z | 10m 37s |
| green | 2026-06-03T22:40:18Z | 2026-06-03T22:47:53Z | 7m 35s |
| spec-check | 2026-06-03T22:47:53Z | 2026-06-03T22:49:29Z | 1m 36s |
| verify | 2026-06-03T22:49:29Z | 2026-06-03T22:53:28Z | 3m 59s |
| review | 2026-06-03T22:53:28Z | 2026-06-03T23:04:17Z | 10m 49s |
| spec-reconcile | 2026-06-03T23:04:17Z | 2026-06-03T23:05:18Z | 1m 1s |
| finish | 2026-06-03T23:05:18Z | - | - |

## Sm Assessment

Story 82-8 (2pt, tdd, sidequest-server only) is set up and ready for RED. This is **ADR-021 track 3** within epic 82 "Surface the Dark Subsystems" — wire the item `narrative_weight` / WealthTier gold→label consumer, emit an OTEL/watcher event (GM panel = lie-detector), and make the result player-facing. Per the epic's wiring doctrine, the story does not count as live until there is a **real production consumer AND an OTEL emit**; the unit test alone is insufficient — TEA must include a wiring test proving the consumer is reachable from a production path.

Reference points: `item_catalog_resolution.py ~:31`, `progression.py ~:187-221`. See `docs/adr/AUDIT-2026-06-03.md` and ADR-021. Story context at `sprint/context/context-story-82-8.md`.

Mechanics-first legibility (Sebastien/Jade) is the player-facing rationale: the WealthTier gold→label mapping should surface in a **player-facing** surface, not only a backend span. Keep the OTEL emit (dev/GM observability) and the player-facing label distinct — both required, different audiences.

Branch topology corrected during setup — see Delivery Findings. Routing to **tea** (the Caterpillar) for the RED phase.

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (19 failing, 1 passing) — ready for Dev (the White Rabbit)

**Test File:**
- `tests/server/test_wealth_tier_wiring.py` — 20 tests across 4 ACs.

**Seam chosen:** `WealthTier` gold→label (NOT item `narrative_weight`). The story
permits either; WealthTier is the cleaner single consumer — it has *zero* existing
consumers (purest dead→wired), the gold→label mapping is a pure function ideal for the
AC's boundary-value edge, and a player-facing surface (`InventoryPayload.gold` +
`currency_name`) already exists to extend. `narrative_weight` would require *inventing*
a mechanical effect for item significance (bigger design question, scope risk).

**The contract Dev must implement (GREEN):**
1. `resolve_wealth_tier(gold: int, tiers: list[WealthTier]) -> WealthTier | None` in
   `genre/models/progression.py` (next to `WealthTier`). Semantics: first tier whose
   `max_gold is None or gold <= max_gold`; boundary `gold == max_gold` lands in *that*
   tier; negative gold clamps to the floor tier; empty tiers → `None` (no fabricated
   default — No Silent Fallbacks).
2. `wealth_tier_label: str | None = None` field on `InventoryPayload`
   (`protocol/models.py`) — the player-facing surface.
3. `SPAN_INVENTORY_WEALTH_TIER = "inventory.wealth_tier"` span in
   `telemetry/spans/inventory.py`, mirroring the disposition-shift style; attributes
   must include `gold` and `label` (the GM-panel lie-detector reads these).
4. Production consumer in `views.party_member_from_character` (`server/views.py` ~:400,
   where `InventoryPayload` is already built): resolve `character.core.inventory.gold`
   against `sd.genre_pack.progression.wealth_tiers`, set `wealth_tier_label`, emit the
   span. Fire the span ONLY when a tier resolves (no tiers → no span, label `None`).

### Rule Coverage

Python lang-review checklist (`.pennyfarthing/gates/lang-review/python.md`):

| Rule | Test(s) | Status |
|------|---------|--------|
| #6 test-quality (meaningful assertions, no vacuous) | every test asserts a specific label/gold/None value; self-checked — none vacuous | n/a (test rubric) |
| #6 wiring test (not source-text — drives real path) | `test_party_member_inventory_carries_wealth_tier_label`, `test_wealth_tier_resolution_emits_otel_span` | failing |
| No Silent Fallbacks (SOUL/CLAUDE) | `test_empty_tiers_returns_none`, `test_no_authored_tiers_leaves_label_none`, `test_no_authored_tiers_emits_no_wealth_tier_span` | failing / 1 passing guard |
| OTEL Observability Principle | `test_wealth_tier_resolution_emits_otel_span` (span fired + carries mechanical data) | failing |
| #3 type annotations at boundary | resolver signature pinned via `test_resolver_returns_wealthtier_object_not_label` | failing |
| boundary/edge values (#6 not-all-same-path) | parametrized boundary + one-above + over-cap + zero + negative | failing |

**Rules checked:** 5 of 13 lang-review rules apply to a pure-resolver + protocol-field +
OTEL-emit story (silent-exceptions, mutable-defaults, paths, resources, async,
deserialization, deps are not exercised by this surface). **Self-check:** 0 vacuous tests.

**Wiring test present:** Yes — two behavioral tests drive the real
`party_member_from_character` consumer (OTEL span assertion + player-facing field
assertion), per CLAUDE.md "No Source-Text Wiring Tests".

**Handoff:** To Dev (the White Rabbit) for GREEN.

## Dev Assessment

**Implementation Complete:** Yes
**Tests:** Full server suite GREEN — 9974 passed, 348 skipped, 0 failed. New file 20/20. Lint clean (ruff).
**Branch:** `feat/82-8-wire-item-narrative-weight-wealthtier` (pushed to origin)

**Files Changed:**
- `sidequest/genre/models/progression.py` — `resolve_wealth_tier(gold, tiers) -> WealthTier | None` (first tier whose cap contains gold; boundary in-tier; negative→floor; empty→None).
- `sidequest/protocol/models.py` — `wealth_tier_label: str | None = None` on `InventoryPayload` (player-facing wire surface).
- `sidequest/telemetry/spans/inventory.py` — `SPAN_INVENTORY_WEALTH_TIER = "inventory.wealth_tier"` + route + `inventory_wealth_tier_span(...)` helper carrying gold/label/tier_index/currency_name.
- `sidequest/server/views.py` — consumer in `party_member_from_character`: resolves `character.core.inventory.gold` against `sd.genre_pack.progression.wealth_tiers`, sets the label, emits the span only when a tier resolves (no tiers → no span, label None).
- `tests/server/test_reference_url_attach.py` — pinned `genre_pack.progression.wealth_tiers = []` on two synthetic-pack MagicMock fixtures the consumer now reads. **Not** a weakening: those tests' `class_reference_url` assertions are unchanged; this mirrors the 68-1 `survivability_pool_label` precedent in the same file. Without the pin, an auto-mocked ladder made the resolver's fallback misfire (StopIteration). Production never passes a MagicMock pack — real packs always have a real list (defaults `[]`).

**Implementation followed TEA's contract exactly** — same symbol names, locations, span name, and consumer site. All 4 ACs met: tier wired (AC-1), OTEL emit (AC-2), player-facing field on the wire (AC-3), behavioral wiring test through the real path + full suite green (AC-4).

**Handoff:** To review (the Queen of Hearts).

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** 2 (both non-blocking)

Verified each AC against the actual diff (`git diff develop...HEAD`), not just the Dev Assessment:
- **AC-1 (tier wired, real path, boundary):** `resolve_wealth_tier` returns the first tier whose `max_gold is None or gold <= max_gold` — boundary `gold == max_gold` lands in-tier, negative clamps to floor, empty → None. Consumed in `party_member_from_character`, the real PARTY_STATUS projection path. ✅
- **AC-2 (OTEL):** `inventory.wealth_tier` span emitted on resolution via `inventory_wealth_tier_span`, routed through `SPAN_ROUTES` mirroring the disposition-shift style; carries `gold` + `label`. ✅
- **AC-3 (player-facing):** `wealth_tier_label` set on `InventoryPayload` (→ `PartyMember.inventory` → PARTY_STATUS on the wire). ✅ (see mismatch 1)
- **AC-4 (wiring test + full green):** 2 behavioral wiring tests drive the real consumer; full suite 9974 passed. ✅

**Mismatches:**
- **Player-facing surface is on-the-wire, not yet UI-rendered** (Ambiguous spec — Behavioral, Minor)
  - Spec: AC-3 "the applied weight or wealth-tier label is visible in a player-facing surface"; Assumptions: "'Player-facing' can reuse an existing projection/state-mirror channel rather than a new panel."
  - Code: label ships on `InventoryPayload`/PARTY_STATUS (an existing projection channel the client receives) but no sidequest-ui component renders it yet.
  - Recommendation: **D — Defer.** The story is scoped server-only (epic 82 lists 82-8 as *server*); putting the label on the existing wire channel satisfies the server-scoped AC per the Assumptions clause. Dev already logged the UI render as a follow-up sidequest-ui finding. No code change needed here.
- **Span carries `tier_index` + `currency_name` beyond the AC's "gold and label"** (Extra in code — Cosmetic, Trivial)
  - Spec: AC-2 / TEA contract require attributes "include `gold` and `label`."
  - Code: span additionally carries `tier_index` (ladder position) and `currency_name`.
  - Recommendation: **A — Accept.** Additive GM-panel context (which tier in the ladder, what currency noun), not scope creep; consistent with the rich-attribute disposition-shift precedent.

**Decision:** Proceed to review (via TEA verify). No hand-back to Dev.

## TEA Assessment (verify phase)

**Phase:** finish
**Status:** GREEN confirmed (full suite was 9974 passed at green; verify changed only a docstring — re-checked: ruff clean, 20/20 wealth-tier tests green)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 6 (4 source + 2 test)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | No duplication; each piece single-responsibility, single-consumer |
| simplify-quality | 6 findings | triaged below — 5 rejected, 1 applied |
| simplify-efficiency | clean | No over-engineering; `is`-identity tier lookup confirmed idiomatic/correct |

**Triage of the 6 quality findings (I verified each against the actual codebase rather than applying blindly):**
- **F2 — span attrs should be `inventory.`-prefixed (high):** REJECTED. Hallucinated convention. Verified against the actual precedent: `SPAN_INVENTORY_NARRATOR_EXTRACTED` and `SPAN_DISPOSITION_SHIFT` both put the namespace in the `field` key and use **plain** attribute names (`gained`, `npc_name`, `delta`). My span (`field: "inventory.wealth_tier"` + plain `gold`/`label`) matches exactly.
- **F1 — `is` identity comparison fragile (medium):** REJECTED. `resolve_wealth_tier` returns an element *of* `wealth_tiers`, so `t is resolved_tier` is guaranteed to match. The suggested `==` would be **worse** — duplicate-field tiers compare equal, risking a wrong index. Efficiency teammate independently confirmed `is` is correct.
- **F3 — span not in FLAT_ONLY_SPANS (medium):** REJECTED. The span IS routed (registered in `SPAN_ROUTES`); routed spans must **not** be in `FLAT_ONLY_SPANS` (that set is for unrouted spans). Mirrors `disposition.shift`. Teammate misread.
- **F5 — test fixture patches unrelated subsystem; "resolver too strict" (medium):** REJECTED. The `wealth_tiers=[]` pin mirrors the existing 68-1 `survivability_pool_label` precedent in the same file. The resolver IS graceful with real empty lists (`if not tiers: return None`); the StopIteration only arose from a MagicMock auto-mock no production path produces. Making the resolver defensive against MagicMocks would be production cruft for a test-only pathology.
- **F4 — "RED phase" docstring / add xfail (low):** NOTED, not applied. The language is historically accurate (the tests DID fail on develop) and matches the repo precedent (`test_party_member_rig_composure.py`). Adding `xfail` would be wrong — the tests now correctly pass.
- **F6 — over-cap clamp not in docstring body (low):** **APPLIED.** The only genuine, zero-risk finding: the `return tiers[-1]` over-cap behavior lived only in an inline comment. Added one sentence to the `resolve_wealth_tier` docstring body documenting it (it returns an *authored* tier, so not a No-Silent-Fallbacks violation). Committed as `refactor: simplify code per verify review` (25930f36).

**Applied:** 1 (F6 docstring clarity). **Flagged for review:** 0. **Noted:** 1 (F4). **Reverted:** 0.

**Overall:** simplify: applied 1 fix (docstring-only, zero behavior change). Reuse + efficiency clean; quality's 5 substantive findings rejected with verified rationale.

**Quality Checks:** ruff clean; wealth-tier suite 20/20 green post-change.
**Handoff:** To Reviewer (the Queen of Hearts) for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (9974 passed, 0 failed, lint clean on branch files, 0 smells) | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings — assessed manually (see [EDGE]) |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings — assessed manually (see [SILENT]) |
| 4 | reviewer-test-analyzer | Yes | findings | 4 | confirmed 4 (all Low/non-blocking), dismissed 0 |
| 5 | reviewer-comment-analyzer | Yes | findings | 3 | confirmed 2 (Low), dismissed 1 ("clamp" pedantic) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings — assessed manually (see [TYPE]) |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings — assessed manually (see [SEC]) |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings — covered in TEA verify + manual (see [SIMPLE]) |
| 9 | reviewer-rule-checker | Yes | findings | 2 (same issue ×2) | confirmed 2 (Low) |

**All received:** Yes (4 enabled subagents returned; 5 disabled, assessed manually)
**Total findings:** 8 confirmed (all Low severity, non-blocking), 1 dismissed (with rationale), 0 deferred

## Reviewer Assessment

**Verdict:** APPROVED

The implementation is correct, complete, and follows established patterns. All four ACs are satisfied with a real production consumer, an OTEL emit, a player-facing field, and behavioral wiring tests; full suite 9974 passed. Every confirmed finding is Low severity (cosmetic / test-hardening) — none Critical or High, so none block.

**Data flow traced:** `character.core.inventory.gold` (validated pydantic int from game state) → `resolve_wealth_tier(gold, sd.genre_pack.progression.wealth_tiers)` → `WealthTier.label` → `InventoryPayload.wealth_tier_label` → `PartyMember.inventory` → PARTY_STATUS on the wire to the client. Safe: gold is server-side validated state (not user input); the label is pack-authored YAML loaded at startup (not user input); the field is outbound-only. No injection/SQL/HTML/path surface.

**Confirmed findings (all Low, non-blocking):**
- **[RULE] Inert `# noqa: ANN001`** at `tests/server/test_wealth_tier_wiring.py:270,292`. Verified: `ANN001` is not in ruff `select = ["E","F","I","UP","B","SIM"]`, so the suppression is dead noise; the sibling `test_turn_span_wiring.py:52,92` uses `otel_capture` params with no such noqa. Cosmetic cleanup.
- **[DOC] Stale "RED phase" module docstring** at `test_wealth_tier_wiring.py:3,21`. The preamble ("these tests fail on current develop"; "Symbols that do not exist yet") is now false — all symbols exist and the suite is GREEN. Misleads a future reader. (Repo has precedent for keeping such language — `test_party_member_rig_composure.py` — but two reviewers flagged it; a one-line refresh would help.)
- **[TEST] Live-content pack load** at `test_wealth_tier_wiring.py:202` (`load_genre_pack(CONTENT_GENRE_PACKS / "caverns_and_claudes")`). Portability nit: depends on the sibling `sidequest-content` subrepo being present. **Matches the established precedent** at `test_multiplayer_party_status.py:74` exactly, so it is a repo-wide convention, not a new regression; this project's dev/CI always checks out the orchestrator with all subrepos. A frozen fixture pack exists (`tests/fixtures/packs/caverns_and_claudes/`) as a future hardening target.
- **[TEST] OTEL span test omits `tier_index`/`player_name` assertions** at `test_wealth_tier_wiring.py:270`. The test asserts `label` + `gold` (the TEA-contracted attrs) but not the identity-derived `tier_index` (which could silently regress to 0). Test-strengthening, not a correctness gap.
- **[TEST] "one above" parametrize gap** at `test_wealth_tier_wiring.py:99` — covers 1/11/51 but not 201→connected / 1001→warlord, while the "exactly on boundary" test covers all four caps. Coverage symmetry nit.
- **[TEST] Tautological serialization test** at `test_wealth_tier_wiring.py:167` — `model_dump(by_alias=True)` equals `by_alias=False` since the field has no alias; redundant with the field-read test but harmless.

**Dismissed:**
- **[DOC] "clamp" wording imprecise** (`progression.py:211`) — DISMISSED: "clamp to the floor tier" is accurate *in effect* (negative gold satisfies `gold <= 0` on the floor tier); the docstring already documents both negative→floor and over-cap→richest. Pedantic, no reader harm.

**Manual assessment of disabled-subagent domains (with evidence):**
- **[EDGE] (subagent disabled — assessed manually)** Resolver boundaries all handled and tested: zero→floor, `gold == max_gold`→in-tier (parametrized ×4), over-cap→richest (`tiers[-1]`), negative→floor, empty→None. `next(i for i,t in enumerate(wealth_tiers) if t is resolved_tier)` at `views.py:414` cannot StopIteration — `resolve_wealth_tier` returns an element *of* `wealth_tiers` (loop element or `tiers[-1]`), so `is`-identity always matches. VERIFIED.
- **[SILENT] (disabled — manual)** No swallowed errors. `if not tiers: return None` (`progression.py:220`) and `if resolved_tier is not None` (`views.py:411`) are explicit authored-state handling, documented as No-Silent-Fallbacks (None label + no span when no tiers), not silent alternative-path fallbacks. VERIFIED.
- **[TYPE] (disabled — manual)** `resolve_wealth_tier -> WealthTier | None` returns the domain newtype (carrying `label`+`description`), not a bare string — `test_resolver_returns_wealthtier_object_not_label` pins it. Field `wealth_tier_label: str | None`; span attrs typed. No stringly-typed API. VERIFIED — `progression.py:205`.
- **[SEC] (disabled — manual)** `gold` from validated pydantic game-state model; `label` from pack-authored YAML loaded at startup; `wealth_tier_label` is an outbound server→UI field. No user-input boundary, no SQL/HTML/path-from-user, no secrets. VERIFIED — `views.py:408-422`.
- **[SIMPLE] (disabled — manual; also covered in TEA verify)** reuse + efficiency teammates both returned clean in the verify phase. The `is`-identity lookup is idiomatic and correct (and superior to `==`, which would mismatch on duplicate-field tiers). Zero-duration `with span(): pass` mirrors the established disposition/reference-url span pattern. No over-engineering. VERIFIED.

### Rule Compliance (Python lang-review, 13 checks)

rule-checker enumerated 47 instances across the diff; I cross-checked the substantive ones:
- #1 silent-exceptions: PASS (no try/except in new code). #2 mutable-defaults: PASS (`None`/`""` defaults, `_ladder()` returns fresh list). #3 type-annotations: PASS except the two inert `# noqa: ANN001` (Low finding above). #4 logging: PASS (OTEL span is the observability channel; None-return is authored state, not an error). #5 paths: PASS (pathlib, test-only paths). #6 test-quality: PASS (no vacuous asserts; OTEL test is a genuine behavioral wiring test, not a source-text grep — per CLAUDE.md). #7 resource-leaks: PASS (`with` context managers). #8 deserialization: PASS (none). #9 async: PASS (sync path, no blocking added). #10 import-hygiene: PASS (function-local imports match the function's existing style; no circular — progression/spans don't import server.views; `from .inventory import *` already re-exports). #11 input-validation: PASS (outbound field, validated-state input). #12 deps: PASS (no pyproject change). #13 fix-regressions: PASS (fixture pin is correct; clamp is documented, not silent).
- **OTEL Observability Principle (CLAUDE.md):** PASS — the subsystem decision (tier resolution) emits `inventory.wealth_tier` carrying `gold`+`label`+`tier_index`, registered in `SPAN_ROUTES`. **No Source-Text Wiring Tests:** PASS — wiring is proven by OTEL span assertion + fixture-driven behavior through the real `party_member_from_character`, not by grepping source.

### Devil's Advocate

Let me argue this code is broken. **A confused content author** writes `wealth_tiers` in *descending* cap order (richest first). `resolve_wealth_tier` consults them in authored order and returns the *first* tier where `gold <= max_gold` — so for a descending ladder, a poor character would resolve to the richest tier. Is this a bug? It's a documented assumption ("packs author ascending by cap") and both shipped packs (mutant_wasteland, road_warrior) author ascending; a mis-authored ladder is a content error the resolver can't divine. Not a code defect, but a content-validation gap — worth a future loader-validation check (logged as a finding). **A malicious user** can't reach this: gold is server-side state, not request input; the label is pack YAML, not user-supplied — no injection vector. **A stressed filesystem**: the only I/O is `load_genre_pack` in the *test* fixture, not production; production reads gold from an in-memory model. **Duplicate-field tiers**: two `WealthTier(max_gold=50, label="x")` in a ladder — the `is`-identity `next()` still resolves to the exact object `resolve_wealth_tier` returned (the first match), so `tier_index` is correct; an `==` implementation would have been the bug here, and the code correctly avoids it. **Span volume**: the span fires on every `party_member_from_character` call (every projection), so an idle party re-emits identical wealth spans — Dev logged this; it's "always reflect current wealth," acceptable, and a threshold-gate is a noted future option. **What if `gold` is huge** (sys.maxsize)? Resolves to the uncapped tier via `tier.max_gold is None`; no overflow in Python ints. **What if `wealth_tiers` is None** rather than `[]`? `ProgressionConfig.wealth_tiers` has `default_factory=list`, so it is never None in production; `if not tiers` handles both empty-and-None defensively anyway. Nothing here rises to a correctness defect. The honest conclusion: the code is sound; the only real gap the devil surfaced is content-side (descending-ladder mis-authoring), which is out of scope for an engine story and logged for a future validator.

**Pattern observed:** OTEL span mirrors the `disposition.shift` style (namespace in `field`, plain attrs) at `telemetry/spans/inventory.py:92`; consumer mirrors the `class_reference_url` block in the same `party_member_from_character` function.
**Error handling:** No error paths introduced — None-return is legitimate authored state, explicitly handled and tested.

**Handoff:** To SM for finish-story.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

- Gap (non-blocking): sm-setup created the feature branch only in the orchestrator (trunk-based/main); the code-bearing repo `sidequest-server` (gitflow/develop) had no branch. SM created `feat/82-8-wire-item-narrative-weight-wealthtier` off `develop` in sidequest-server. Code + PR go to sidequest-server off develop; sprint files travel in the orchestrator branch.

### TEA (test design)
- **Improvement** (non-blocking): `WealthTier` had literally zero consumers repo-wide (only the model def + `__init__` export) — the audit's "data-only" call is exact. The cleanest consumer point is `views.party_member_from_character` (~:400), which already builds the player-facing `InventoryPayload` with `gold` + `currency_name`; adding `wealth_tier_label` there reaches the existing player surface without a new panel. Affects `sidequest/server/views.py` (add the resolve+emit+set), `sidequest/protocol/models.py` (field), `sidequest/genre/models/progression.py` (resolver), `sidequest/telemetry/spans/inventory.py` (span). *Found by TEA during test design.*
- **Question** (non-blocking): item `narrative_weight` (the other track-3 seam) remains un-wired and P2-deferred after this story ships the WealthTier seam. Per the story, one seam satisfies track 3 — note in the PR that `narrative_weight` is the deferred follow-up. Affects `sidequest/game/item_catalog_resolution.py` (~:31 still cosmetic). *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): `wealth_tier_label` now ships on `InventoryPayload` (and thus PARTY_STATUS to the client), but the sidequest-ui inventory panel does not render it yet. A follow-up sidequest-ui story should display the tier label alongside the gold count for full player-facing visibility (mechanics-first legibility). Affects `sidequest-ui` (inventory/party panel components). *Found by Dev during implementation.*
- **Improvement** (non-blocking): the wealth-tier span fires once per `party_member_from_character` call (every party-status projection), which is correct for "always reflect current wealth" but means repeated spans for an unchanged balance. If span volume becomes noisy on the GM panel, a future change could gate emission on a tier *change* (mirroring disposition's threshold-crossing `crossed` field). Affects `sidequest/server/views.py`. *Found by Dev during implementation.*

### Reviewer (code review)
- **Improvement** (non-blocking): remove the two inert `# noqa: ANN001` comments at `tests/server/test_wealth_tier_wiring.py:270,292` — `ANN001` is not in ruff `select`, and the sibling `test_turn_span_wiring.py` omits it for the same `otel_capture` fixture param. Cosmetic. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): refresh the `test_wealth_tier_wiring.py` module docstring (lines 3, 21) — the "RED phase / symbols that do not exist yet" framing is now stale (suite is GREEN, symbols exist). Affects `tests/server/test_wealth_tier_wiring.py`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): optional test-hardening — assert `tier_index` + `player_name` on the OTEL span (`test_wealth_tier_wiring.py:270`), add `201→connected`/`1001→warlord` to the "one above" parametrize (~:99), and consider the live-content pack load (~:202) → frozen fixture pack `tests/fixtures/packs/caverns_and_claudes/` (matches existing `test_multiplayer_party_status.py` precedent, so non-urgent). *Found by Reviewer during code review.*
- **Question** (non-blocking): a future content-validation pass could warn when a pack authors `wealth_tiers` in descending cap order (the resolver assumes ascending; both shipped packs comply). Affects `sidequest/genre/loader.py` / a validator. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Narrowed the either/or seam to WealthTier and pinned the resolver contract**
  - Spec source: context-story-82-8.md, AC-1 ("either item `narrative_weight` ... **or** `WealthTier`")
  - Spec text: "This story may wire **either** seam (whichever yields the cleaner single consumer) and still satisfy track 3 — they are alternatives, not both-required."
  - Implementation: Tests commit to the `WealthTier` gold→label seam and define a concrete resolver API (`genre/models/progression.resolve_wealth_tier(gold, tiers) -> WealthTier | None`), a specific player-facing field (`InventoryPayload.wealth_tier_label`), a specific span name (`inventory.wealth_tier`), and a specific consumer site (`views.party_member_from_character`). The spec left all of these open.
  - Rationale: TDD RED requires concrete failing tests, which forces a seam choice. WealthTier has zero existing consumers (cleanest dead→wired), a pure-function core ideal for the boundary-value AC, and an existing player surface to extend. Choosing one seam is explicitly in scope.
  - Severity: minor
  - Forward impact: Dev should implement against these names/locations; item `narrative_weight` is left as the deferred follow-up. If Dev finds a cleaner consumer site, the protocol-field and resolver tests still hold — only the two views-driven wiring tests are coupled to `party_member_from_character`.
- **Defined negative-gold and empty-tier behavior the spec did not specify**
  - Spec source: context-story-82-8.md, AC-1 ("Edge: boundary values (zero/min weight, gold exactly on a tier boundary)")
  - Spec text: "boundary values (zero/min weight, gold exactly on a tier boundary) resolve to the intended label/behavior."
  - Implementation: zero gold → floor tier; `gold == max_gold` → that tier (not the next); negative gold → clamps to floor tier (not None); empty `wealth_tiers` → `None` label and no span.
  - Rationale: The spec named the edges but not their resolution; chose the No-Silent-Fallbacks-consistent reading (never fabricate a tier when none authored; never let debt fall off the bottom).
  - Severity: minor
  - Forward impact: none if Dev implements the documented semantics; the parametrized boundary tests pin them.

### Dev (implementation)
- No deviations from spec. Implemented exactly to TEA's contract (same symbol names, locations, span name, consumer site) and the documented edge semantics. The only test change (pinning `progression.wealth_tiers=[]` on two synthetic MagicMock packs in `test_reference_url_attach.py`) is a fixture update for an attribute the consumer now reads — not a spec deviation, and the affected tests' own assertions are unchanged.

### Reviewer (audit)
- **TEA deviation 1 (seam narrowed to WealthTier + pinned contract)** → ✓ ACCEPTED by Reviewer: choosing one seam is explicitly in-scope per AC-1 ("either … or … alternatives, not both-required"); WealthTier was the cleaner dead→wired seam and the implementation honored the pinned contract exactly.
- **TEA deviation 2 (negative-gold→floor, empty→None edge semantics)** → ✓ ACCEPTED by Reviewer: the No-Silent-Fallbacks reading is the correct one; behavior is documented in the resolver docstring and pinned by parametrized boundary tests.
- **Dev "No deviations from spec"** → ✓ ACCEPTED by Reviewer: verified — implementation matches the TEA contract; the `test_reference_url_attach.py` fixture pin is a necessary update (consumer now reads `progression.wealth_tiers`), mirrors the 68-1 precedent, and leaves those tests' own assertions untouched. Not a spec deviation.
- No undocumented spec deviations found. The diff implements exactly the four ACs; the only divergences (seam choice, edge semantics) were logged by TEA.

### Architect (reconcile)

Verified the deviation manifest against the spec sources for the definitive audit:
- **Spec sources confirmed real:** `sprint/context/context-story-82-8.md` (4298 b) and `sprint/context/context-epic-82.md` (7257 b) both exist. TEA's quoted AC-1 text ("they are alternatives, not both-required") matches the context file verbatim (line 20-21).
- **TEA deviation 1 (seam → WealthTier):** all 6 fields present and accurate; the implementation matches the pinned contract (resolver, field, span, consumer all at the stated locations). Sound.
- **TEA deviation 2 (negative→floor, empty→None edge semantics):** all 6 fields present; the parametrized boundary tests pin the documented behavior; the resolver docstring documents it. Sound.
- **Dev "No deviations from spec":** verified accurate — the implementation tracks the TEA contract exactly; the `test_reference_url_attach.py` fixture pin is a necessary fixture update (consumer now reads `progression.wealth_tiers`), not a spec deviation.
- **AC deferral check:** N/A — all four ACs are DONE (none deferred or descoped), so there is no deferral table to reconcile.

- **No additional deviations found.** Two candidate divergences considered and dismissed as non-deviations: (1) the OTEL span carries `tier_index`+`currency_name` beyond AC-2's "include gold and label" — "include" permits additional attributes, so this is additive metadata, not a deviation; (2) the verify-phase docstring clarification and the test fixture pin are implementation hygiene, not spec divergences.