---
story_id: "103-2"
jira_key: ""
epic: "103"
workflow: "tdd"
---
# Story 103-2: Stock system — stock chargen step + per-stock branching of the mutation step; stocks.yaml schema + generic stock application (attr mods/Move/AC/Trauma-Target/granted mutation IDs, zero per-stock special cases); Sleeper implants as System-Strain item sources; awn.stock.applied span; UI chargen branch flow. Ships proof stocks (Sleeper, one Animal). Build plan §D-B.

## Story Details
- **ID:** 103-2
- **Jira Key:** (no Jira integration)
- **Workflow:** tdd
- **Stack Parent:** none (independent story)
- **Points:** 8
- **Priority:** p2

## Workflow Tracking
**Workflow:** tdd
**Repos:** server,ui,content
**Phase:** finish
**Phase Started:** 2026-06-11T04:11:24Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-10T02:52:55Z | 2026-06-11T02:54:51Z | 24h 1m |
| red | 2026-06-11T02:54:51Z | 2026-06-11T03:18:47Z | 23m 56s |
| green | 2026-06-11T03:18:47Z | 2026-06-11T03:49:04Z | 30m 17s |
| review | 2026-06-11T03:49:04Z | 2026-06-11T03:55:54Z | 6m 50s |
| red | 2026-06-11T03:55:54Z | 2026-06-11T03:59:07Z | 3m 13s |
| green | 2026-06-11T03:59:07Z | 2026-06-11T04:05:40Z | 6m 33s |
| review | 2026-06-11T04:05:40Z | 2026-06-11T04:11:24Z | 5m 44s |
| finish | 2026-06-11T04:11:24Z | - | - |

## Branch Strategy
**Branch Strategy:** gitflow (feature/103-2-stock-system)

**Branches created:**
- sidequest-server: feature/103-2-stock-system (off origin/develop)
- sidequest-ui: feature/103-2-stock-system (off origin/develop)
- sidequest-content: feature/103-2-stock-system (off origin/develop)

## Delivery Findings

No upstream findings

### TEA (test design)
- **Gap** (non-blocking): 103-1 shipped `apply_saint_preset` with an actor-presence idempotency guard, which makes sequential stock-then-saint composition impossible (the second call returns early). The layering contract is therefore pinned INSIDE `apply_stock(..., saint_id=)`.
  Affects `sidequest-server/sidequest/mutation/stocks.py` (Dev implements saint layering within apply_stock, reusing the preset's MP math — never a second economy).
  *Found by TEA during test design.*
- **Gap** (non-blocking): 103-1's saint route is plumbed in chargen_mixin but `MechanicalEffects` has no `saint_id` field — the Saint-Marked selection surface was explicitly deferred to this story (chargen_mixin comment, lines 1104/1342). Tests pin `MechanicalEffects.saint_id` + `stock_id` and builder `chosen_saint_id`/`chosen_stock_id`.
  Affects `sidequest-server/sidequest/genre/models/character.py` and `sidequest-server/sidequest/game/builder.py` (additive fields + accumulation).
  *Found by TEA during test design.*
- **Question** (non-blocking): the additive `stock_options` chargen payload (and `requires_stock`/`stock_id` content schema) should be documented in `docs/api-contract.md` per the story-context assumption about additive protocol changes.
  Affects `docs/api-contract.md` (additive CHARACTER_CREATION payload documentation).
  *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): a mid-chargen reconnect that lands directly on the stock scene re-renders through `handlers/connect.py`'s own `to_scene_message` call, which does not pass `_stockify_scene_message` — the frame degrades to a plain choice scene (fully functional, same response protocol, but no deltas preview).
  Affects `sidequest-server/sidequest/handlers/connect.py` (route the resume frame through the stockify helper).
  *Found by Dev during implementation.*
- **Gap** (non-blocking): `CreatureCore.move` and `trauma_target_mod` are stored and span-audited per AC2/AC6 but have no combat consumer yet — lethality trauma rolls and movement do not read them.
  Affects `sidequest-server/sidequest/game/lethality.py` (consult defender trauma_target_mod when 103-10 wires confrontation proof; AWN Plans 3–7 for move).
  *Found by Dev during implementation.*

## Design Deviations

None at setup phase

### TEA (test design)
- **Move/Trauma-Target pinned as new generic CreatureCore fields**
  - Spec source: context-story-103-2.md, Assumptions
  - Spec text: "Trauma Target / Move / AC are already settable via existing creature/character fields from CWN substrate (verified for NPCs; assumed reachable for PC chargen — if not, the hook is added generically, logged as deviation)"
  - Implementation: CreatureCore has no `move` or `trauma_target` field (trauma target exists only on weapon DamageSpec + genre default). Tests pin two new GENERIC creature fields: `move: int | None = None` (override) and `trauma_target_mod: int = 0`, applied by apply_stock to any creature.
  - Rationale: the assumption's escape hatch, exercised; fields are creature-generic (all stocks, NPCs later), not stock-special-cased.
  - Severity: minor
  - Forward impact: AWN Plans 3–7 creatures can reuse both fields; lethality.py trauma rolls should consult `trauma_target_mod` when 103-10 wires confrontation proof.
- **Saint affinity layering pinned as a single entry point, not sequential calls**
  - Spec source: context-story-103-2.md, AC4
  - Spec text: "the proof Animal stock applies its trait set AND can layer one Saint affinity bundle via 103-1's preset path without double-pricing"
  - Implementation: `apply_stock(..., saints=, saint_id=)` performs the layering internally; sequential `apply_stock` then `apply_saint_preset` is NOT the contract (the preset's actor-idempotency guard would no-op the second call).
  - Rationale: preserves 103-1's idempotency contract untouched while keeping one application path and one span per actor.
  - Severity: minor
  - Forward impact: chargen confirm passes both ids in one call; 103-8's full roster authors `saint_affinity_allowed` per stock.
- **Implants pinned to a new `implants` lane on WorldItemsCatalog + `use_implant` helper**
  - Spec source: context-story-103-2.md, Technical Guardrails / AC3
  - Spec text: "implants authored as System-Strain item sources (same pool slot as AWN cyberware/stims — reuse system_strain.py hooks, no parallel implant economy)"
  - Implementation: the 5 spec implants live in `worlds/seaboard_of_saints/items.yaml` under a new `implants:` section (sibling to the five existing lanes); `use_implant(core, item, *, module, cfg, actor, session_id)` in `mutation/stocks.py` reads `strain_cost` and charges through `CwnRulesetModule.apply_system_strain` verbatim.
  - Rationale: the spec named the items but no schema home; items.yaml lanes are the established world-tier pattern, and the helper proves pool reuse rather than reimplementation.
  - Severity: minor
  - Forward impact: implant install/uninstall mid-game (deferred, world spec §13) gets a ready item lane; 103-8 can author more implants without schema work.
- **Stock branching pinned as a generic `requires_stock` scene tag**
  - Spec source: context-story-103-2.md, Technical Guardrails
  - Spec text: "insert a stock step that branches the `mutation` step"
  - Implementation: `CharCreationScene.requires_stock: str | None` — the builder presents a tagged scene only when a prior choice carried matching `mechanical_effects.stock_id`; untagged scenes always present. The world AUTHORS the per-stock branch scenes; the engine only matches tags.
  - Rationale: zero per-stock engine cases (the epic guardrail) — branching is data, not code; flickering_reach regression is automatic (no tags authored → no behavior change).
  - Severity: minor
  - Forward impact: 103-8 authors the remaining four stock branches purely in content.
- **UI stock step pinned as preview-before-commit with explicit confirm**
  - Spec source: context-story-103-2.md, AC7 + Business Context
  - Spec text: "stock selection renders, branches correctly, and displays mechanical deltas pre-confirmation"; "must not rush slow readers (Alex) and must show the mechanical consequences of a stock pick legibly (Sebastien/Jade)"
  - Implementation: `input_type: "stock"` + `stock_options` payload (id, label, description, deltas); selecting previews deltas without responding; a separate confirm button sends the STANDARD `{phase: "scene", choice: "<index+1>"}` response.
  - Rationale: browse-freely/commit-deliberately serves Alex; signed deltas + mutation display names serve Sebastien/Jade; reusing the scene-choice wire protocol keeps the server contract additive.
  - Severity: minor
  - Forward impact: the payload shape is the template for any future preview-bearing chargen step (Roll the Bones, 103-3, may reuse the deltas panel).

### Dev (implementation)
- **Saint-Marked implemented as an inert stocks.yaml entry, not a bare preset call**
  - Spec source: context-story-103-2.md, Technical Guardrails (stock → expression mapping)
  - Spec text: "Saint-Marked → 103-1's preset"
  - Implementation: `saint_marked` ships as an all-inert stock with `saint_affinity_allowed: true`; the branch scene (the_spring) supplies saint_id and apply_stock's layering reproduces apply_saint_preset's MP arithmetic exactly (same terms, same log ordering)
  - Rationale: gives Saint-Marked the same requires_stock branch machinery as every other path with zero engine special cases; the preset math is shared semantics, not a duplicated economy
  - Severity: minor
  - Forward impact: 103-8's full roster keeps one branching idiom; apply_saint_preset remains the engine for non-stock worlds
- **Wild Mutant has no stocks.yaml entry by design**
  - Spec source: context-story-103-2.md, Technical Guardrails
  - Spec text: "Wild → existing freeform MP spend"
  - Implementation: the Wild choice carries no stock_id; a stock-less walk skips every tagged branch scene and chargen confirm falls through to the classic `seed_character_mutations` path unchanged
  - Rationale: absence of a stock IS the Wild path — encoding it as a seventh entry would force the stock route to special-case wild seeding
  - Severity: minor
  - Forward impact: any world authoring a stock scene must leave its Wild-style choice untagged; documented in the stocks.yaml header comment

## Sm Assessment

Setup completed successfully at 2026-06-10T02:52:55Z.

**Workflow Type:** phased (tdd)
**Next Phase:** red (TEA agent)
**Next Agent:** tea

**Pre-requisites verified:**
- Story context exists at sprint/context/context-story-103-2.md
- Epic context exists at sprint/context/epic-103-context.md
- All subrepos (server, ui, content) on origin/develop
- Feature branches created in all three subrepos
- No Jira integration required (JIRA_KEY empty)

**Story Dependencies:**
- Depends on 103-1 (Saint layer) — COMPLETED 2026-06-10
- Blocks 103-8 (stocks + dramatic content) via schema freeze
- Blocks 103-10 (end-to-end wiring) as critical path

**Acceptance Criteria from Build Plan §D-B:**
1. stocks.yaml schema with generic stock application (attr mods, Move, AC, Trauma-Target, granted mutation IDs)
2. Stock chargen step implementation
3. Per-stock branching of mutation step
4. Sleeper implants as System-Strain item sources
5. awn.stock.applied OTEL span
6. UI chargen branch flow
7. Proof stocks shipped: Sleeper, one Animal stock
8. Zero per-stock special cases (pure schema-driven system)
## TEA Assessment

**Tests Required:** Yes
**Reason:** 8-point engine story; net-new subsystem surface across server + UI.

**Test Files:**
- `sidequest-server/tests/mutation/test_stocks_models.py` — StockDef/StockRegistry/load_stock_registry schema + loud catalog cross-validation (AC5)
- `sidequest-server/tests/mutation/test_stock_apply.py` — the ONE generic application path: trait deltas, grants-are-free MP property, schema-not-name property (AC2/AC8), idempotency, saint layering priced once (AC4), `awn.stock.applied` span + SPAN_ROUTES (AC6)
- `sidequest-server/tests/mutation/test_implant_strain.py` — Sleeper implants as System-Strain item sources through the EXISTING pool, over-max refusal, loud non-source rejection (AC3)
- `sidequest-server/tests/mutation/test_stock_init.py` — the production join point: init_mutation_state_for_session stock route + loud config errors
- `sidequest-server/tests/game/test_builder_stock_branching.py` — requires_stock/stock_id branching walk, chosen_stock_id/chosen_saint_id confirm plumbing, single-path regression (AC1)
- `sidequest-server/tests/genre/test_stocks_world_load.py` — World.stocks loader seam (production path on fixture pack), real-content proofs: seaboard stocks.yaml (sleeper + animal), stock chargen scene + sleeper implant branch, 5 spec implants with strain_cost, flickering_reach stays stockless (AC1/AC5)
- `sidequest-ui/src/components/CharacterCreation/__tests__/CharacterCreation.stock-step.test.tsx` — stock cards, preview-before-commit deltas, explicit confirm protocol (AC7)
- `sidequest-ui/src/__tests__/character-creation-wiring.test.tsx` (appended `103-2: stock step wiring` block) — stock scene over WebSocket, choice response on the wire, server-branched follow-up scene renders

**Tests Written:** 47 server (38 failing + 5 module-collection-error files + 1 passing regression guard) + 8 UI (all failing) covering all 7 ACs + AC8 (zero per-stock cases)
**Status:** RED (verified by direct run — see below)

**RED verification (direct `uv run pytest -n0` / `npx vitest run`, 2026-06-10):**
- server: 5 files error on `ModuleNotFoundError: sidequest.mutation.stocks` (the right reason — module doesn't exist); `test_builder_stock_branching.py`: 9 failed, 1 passed (`test_flow_without_stock_machinery_walks_unchanged` — deliberate regression guard pinning current single-path behavior)
- ui: stock-step unit 6/6 failed; wiring file 2 new failed / 16 existing passed (no regression introduced)

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| python #1 silent exceptions / No Silent Fallbacks | `test_unknown_granted_mutation_fails_loudly`, `test_loader_rejects_*`, `test_stock_id_without_{registry,catalog,character}_fails_loud`, `test_item_without_strain_cost_refused_naming_item`, `test_saint_id_without_registry_fails_loud` | failing |
| python #6 test quality (no vacuous asserts) | self-check pass — every test asserts specific values/messages; no `assert True`, no bare truthy checks | done |
| python #8 unsafe deserialization | loader tests pin the `load_stock_registry(path, catalog)` contract mirroring saints' `yaml.safe_load`; fixtures use safe_load only | failing |
| python #11 input validation at boundaries | `test_id_must_be_bare_snake_case`, `test_granted_mutations_reject_negatives`, `test_duplicate_*_rejected`, `test_non_positive_strain_cost_refused` | failing |
| CLAUDE.md wiring-test mandate | production-seam tests: `test_loader_populates_world_stocks` (load_genre_pack path), `test_stock_route_applies_stock_to_character_and_state` (init join point), UI wiring block (full App over MockWebSocket) | failing |
| CLAUDE.md no source-text wiring tests | reflection-only seam checks (`World.model_fields`, `WorldItemsCatalog.model_fields`) — the sanctioned tripwire pattern; zero read_text-on-source assertions | done |
| OTEL Observability Principle (D-D) | `TestStockAppliedSpan` — span fires with trait deltas, no refire on replay, SPAN_ROUTES registration | failing |

**Rules checked:** 5 of 13 python checks applicable to test-design phase have coverage; remainder (logging levels, resource leaks, async, imports, deps) are implementation-phase checks for Dev/Reviewer.
**Self-check:** 0 vacuous tests found.

**Contract notes for Agent Smith (Dev):** the RED suite DEFINES these surfaces — `sidequest/mutation/stocks.py` (StockDef, StockRegistry, load_stock_registry, apply_stock, use_implant), `awn_stock_applied_span` in `telemetry/spans/awn.py` + SPAN_ROUTES entry, `World.stocks` + loader block (mirror saints seam at loader.py:1515), `MechanicalEffects.stock_id`/`saint_id`, `CharCreationScene.requires_stock`, builder skip-walk + `chosen_stock_id`/`chosen_saint_id`, `init_mutation_state_for_session(stocks=, stock_id=, character=)`, `WorldItemsCatalog.implants`, CreatureCore `move`/`trauma_target_mod`; content: seaboard `stocks.yaml` + `char_creation.yaml` (stock scene + sleeper implant branch) + `items.yaml` implants lane (ids: subdermal_weave, cortex_booster, optic_suite, dermal_vox, blood_filter); UI: `input_type "stock"` + `stock_options` in CreationScene/CharacterCreationPayload, testids `stock-option-{id}`/`stock-deltas`/`stock-confirm`. See Design Deviations for rationale on each pinned choice.

**Handoff:** To Agent Smith (Dev) for implementation (GREEN)
## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**

*sidequest-server* (branch `feature/103-2-stock-system`, pushed):
- `sidequest/mutation/stocks.py` — NEW: StockDef/StockRegistry/load_stock_registry (loud catalog cross-validation), apply_stock (one generic path; free grants; Saint layering priced once via 103-1 math; idempotent), use_implant (strain through existing CwnRulesetModule pool)
- `sidequest/telemetry/spans/awn.py` — awn.stock.applied span + SPAN_ROUTES route
- `sidequest/game/creature_core.py` — generic `move` / `trauma_target_mod` trait hooks
- `sidequest/game/builder.py` — requires_stock skip-walk in `_advance_scene`; `chosen_stock_id`/`chosen_saint_id` accumulators
- `sidequest/genre/models/pack.py` + `genre/loader.py` — World.stocks field + stocks.yaml loader seam (mirror of saints)
- `sidequest/genre/models/character.py` — MechanicalEffects.stock_id/saint_id; CharCreationScene.requires_stock
- `sidequest/genre/models/items.py` — WorldItemsCatalog.implants lane
- `sidequest/protocol/messages.py` — StockOption/StockDeltas payloads + stock_options field
- `sidequest/server/mutation_init.py` — stock route with loud config errors
- `sidequest/server/websocket_handlers/chargen_mixin.py` — `_stockify_scene_message` frame upgrade in `_next_message`; both confirm-time init sites plumb stocks/stock_id/saint_id/character

*sidequest-ui* (branch `feature/103-2-stock-system`, pushed):
- `src/components/CharacterCreation/CharacterCreation.tsx` — input_type "stock" branch: cards, preview-before-commit deltas panel, explicit Choose → standard scene-choice response
- `src/types/payloads.ts` — StockOptionPayload/StockDeltasPayload + stock_options

*sidequest-content* (branch `feature/103-2-stock-system`, pushed):
- `worlds/seaboard_of_saints/stocks.yaml` — proof stocks: sleeper (inert), saint_marked (inert + affinity), harbor_seal (full Animal trait set + affinity)
- `worlds/seaboard_of_saints/char_creation.yaml` — world flow with stock step + branches (the_spring, the_cold_rack, the_seal_devotion)
- `worlds/seaboard_of_saints/items.yaml` — the 5 spec implants with strain_cost

*orchestrator* (uncommitted; rides the finish commit):
- `docs/api-contract.md` — additive stock-step payload documented per story-context assumption

**Tests:** server 11704 passed / 0 failed (full suite, 2 consecutive runs; requires `SIDEQUEST_TEST_DATABASE_URL` + `SIDEQUEST_DATABASE_URL` exported — earlier "failures" were missing env vars + the known xdist PythonFinalizationError red herring). UI 2071/2071 passed; lint 0 errors (1 pre-existing App.tsx warning); build clean. Ruff + format clean on changed files; pyright errors on changed files are all pre-existing mixin-pattern noise at untouched lines.
**Branch:** feature/103-2-stock-system (pushed in server, ui, content)

**Handoff:** To The Architect (TEA) for verify phase
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings — domain covered by lead (see [EDGE] finding 1) |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings — domain covered by lead + security overlap (see [SILENT]/[SEC] findings) |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings — lead spot-check: no vacuous assertions in new tests; coverage gap noted in finding 1 ([TEST]) |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings — lead spot-check: docstrings accurate, no stale refs found ([DOC] clean) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings — lead spot-check: pydantic extra=forbid on new models, Literal-typed traditions, validated ids ([TYPE] clean) |
| 7 | reviewer-security | Yes | findings | 4 | confirmed 2 (downgraded HIGH→MEDIUM with rationale), deferred 2 |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings — lead spot-check: no dead code; _stockify guard order is minimal ([SIMPLE] clean) |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings — lead performed rule-by-rule sweep (see Rule Compliance) ([RULE]) |

**All received:** Yes (2 enabled returned, 7 disabled via settings and covered by lead)
**Total findings:** 5 confirmed, 0 dismissed, 2 deferred

### Rule Compliance

Rules swept against every new/changed type and function in the diff (python lang-review + CLAUDE.md criticals):

| Rule | Instances checked | Result |
|------|-------------------|--------|
| #1 silent exceptions | stocks.py (0 bare except), loader stock block (catch ValueError → GenreLoadError re-raise), mutation_init guards, _stockify | **2 VIOLATIONS** — _stockify's two silent early-returns (findings 2, 3); all other paths loud |
| #2 mutable defaults | StockDef/StockRegistry/StockDeltas/StockOption (Field(default_factory)), apply_stock/use_implant signatures | compliant |
| #3 type annotations | all new public functions annotated incl. returns (stocks.py, mutation_init, spans/awn.py, _stockify) | compliant |
| #4 logging | mutation_init logger.info lazy %s-style; no secrets/PII in logs or span attrs | compliant |
| #5 path handling | load_stock_registry: Path + read_text(encoding="utf-8") | compliant |
| #6 test quality | new test files: value-specific assertions, error-message content asserted, no skips | compliant |
| #8 unsafe deserialization | yaml.safe_load only (stocks.py:387 region) | compliant |
| #11 input validation | StockDef id regex, negative-grant rejection, dup rejection, attr-presence check, use_implant strain_cost type/positivity | compliant at schema level; **no numeric range bounds** (finding 4, deferred) |
| No Silent Fallbacks (CLAUDE.md) | loader absence-vs-error split, mutation_init loud guards, by_id KeyErrors naming known ids | compliant EXCEPT _stockify early-returns (findings 2, 3) |
| Every Test Suite Needs a Wiring Test | loader production-path tests, init-seam test, full-App UI wiring block | compliant |
| No Source-Text Wiring Tests | model_fields reflection only (sanctioned tripwire) | compliant |
| OTEL Observability Principle | awn.stock.applied + SPAN_ROUTES + mutation.stock_init watcher event | compliant |

### Devil's Advocate

Assume this code is broken and a player is trying to break it. The most dangerous user is not malicious — it is Alex, slow and careful, who clicks "← Back" to re-read something. The builder's `go_back` pops one SceneResult and targets `scene_index = len(_results)`. Before this story, every presented scene appended exactly one result, so that arithmetic held. The new skip-walk presents FEWER scenes than the list contains: a Sleeper's walk through the seaboard flow skips `the_spring` and `the_seal_devotion`, so after the cold rack the result count and the scene index have diverged. Back out of the artifact scene and the arithmetic lands you on a scene your stock should never see — the Saint spring. Pick a Saint there (why wouldn't you? the game showed it to you) and `chosen_saint_id` is now set against a stock with `saint_affinity_allowed: false`; the confirm path raises ValueError and chargen dies at the very last step, eating ten minutes of a slow reader's careful choices. That is precisely the player this feature was designed to protect. Second angle: a homebrew author (Jade) writes `stock_id: sleper` — a typo. Load passes (char_creation and stocks.yaml are never cross-checked), the scene frame upgrade raises KeyError at RENDER time mid-session, not load time. Third: the same author authors stock_id choices but forgets stocks.yaml entirely — `_stockify` shrugs silently and the flow limps to a deferred confirm-time crash. The review's findings all came from walking these three users, and the first one is blocking.

### Reviewer (audit)

All seven logged deviations audited:
- **Move/Trauma-Target as new generic CreatureCore fields** (TEA) → ✓ ACCEPTED by Reviewer: the story-context assumption explicitly sanctioned the generic hook; fields are creature-generic with inert defaults.
- **Saint affinity layering as single entry point** (TEA) → ✓ ACCEPTED by Reviewer: sequential composition is provably impossible against 103-1's idempotency guard; one path, one span is the cleaner contract.
- **Implants lane + use_implant helper** (TEA) → ✓ ACCEPTED by Reviewer: established items.yaml lane pattern; strain charged through the live CwnRulesetModule (verified stocks.py use_implant delegates, no parallel pool math).
- **requires_stock generic scene tag** (TEA) → ✓ ACCEPTED by Reviewer: zero per-stock engine cases verified (no stock-id string comparisons outside tag matching); HOWEVER see [HIGH] finding 1 — the tag filter's interaction with back-navigation was missed by both TEA and Dev.
- **UI preview-before-commit** (TEA) → ✓ ACCEPTED by Reviewer: serves the playgroup rubric directly; standard wire protocol preserved (verified CharacterCreation.tsx responds {phase:"scene", choice}).
- **Saint-Marked as inert stocks.yaml entry** (Dev) → ✓ ACCEPTED by Reviewer: MP arithmetic verified identical to apply_saint_preset (same terms, drawback-first log); one branching idiom is worth the indirection.
- **Wild Mutant has no stocks.yaml entry** (Dev) → ✓ ACCEPTED by Reviewer: absence-as-Wild is coherent with the loader's absence-is-authored-choice doctrine and documented in the content header.

No undocumented deviations found beyond the findings below.

## Reviewer Assessment

**Verdict:** REJECTED

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] [EDGE] | `go_back`/`revert` target `scene_index = len(_results)`, an invariant the requires_stock skip-walk breaks — backing up after a skipped branch scene lands the player on the WRONG stock's branch scene (e.g. Sleeper sees the Saint spring), and choosing there poisons chosen_saint_id into a loud confirm-time crash. Reachable via the UI Back button (handlers/character_creation.py:78-88) | sidequest-server/sidequest/game/builder.py:2265-2266, 2279-2280 | Make back-navigation branch-aware: record each result's presented scene_index on SceneResult (or replay the skip-walk) so go_back/revert return to the scene actually answered. TEA: failing test first — go_back across a skipped branch scene (both go_back and revert paths) |
| [MEDIUM] [SEC] [SILENT] | `_stockify_scene_message` returns silently when choices carry stock_id but the world ships no stock registry — the frame degrades to a plain choice scene and the misconfiguration surfaces only as a deferred confirm-time ValueError. (Downgraded from subagent HIGH: the early return precedes input_type promotion, so the frame is NOT broken-promoted, and confirm does fail loud — but the FIRST wrong moment must be the loud one per No Silent Fallbacks) | sidequest-server/sidequest/server/websocket_handlers/chargen_mixin.py (_stockify, registry-None branch) | Raise ValueError naming the world slug and the offending stock_id(s) when stock_id choices exist with no registry |
| [MEDIUM] [SEC] [SILENT] | `_stockify`'s `catalog is None` defensive branch silently renders a granting stock with an empty mutations list — masks an invariant violation (a loaded registry guarantees a catalog) and shows mechanics-first players false math | sidequest-server/sidequest/server/websocket_handlers/chargen_mixin.py (_stockify, granted_names) | Raise ValueError naming the stock when catalog is None and granted_mutations is non-empty |
| [MEDIUM] [EDGE] | `apply_stock` validates attr_mods keys per-attr DURING mutation — an unknown attr raises after earlier attrs already applied (partial mutation). Harmless on the production confirm path (Character rebuilt per attempt) but a corrupting trap for any other caller | sidequest-server/sidequest/mutation/stocks.py (attr_mods loop) | Two-pass: validate all keys against character.stats, then apply |
| [MEDIUM] [TEST] | No test covers back-navigation across a skipped branch scene — the exact gap that let finding 1 through; existing go_back coverage (test_builder_creation_answers.py:398) is linear-flow only | sidequest-server/tests/game/test_builder_stock_branching.py | TEA adds failing tests for go_back + revert across skips during rework |

**Verified good (with evidence):**
- [VERIFIED] [RULE] Loader stock seam fails loud and absence is authored choice — loader.py stock block re-raises ValueError as GenreLoadError carrying path + stock id + mutation id; absence path sets None without fallback. Complies with No Silent Fallbacks.
- [VERIFIED] [TYPE] All new models are extra=forbid with validated constructors — StockDef id regex rejects catalog-shaped ids, granted_mutations reject negatives, registries reject duplicate ids naming them; StockDeltas/StockOption protocol models typed. Complies with input-validation rules.
- [VERIFIED] [SEC] yaml.safe_load + encoding="utf-8" at the only new file-read; no eval/exec/shell, no secrets in logs/spans, no dangerouslySetInnerHTML in the UI diff.
- [VERIFIED] [SIMPLE] One generic application path confirmed — no stock-id branching anywhere in engine code (grep: zero `== "sleeper"`-shaped comparisons outside tag matching); schema-driven twin test enforces it.
- [VERIFIED] [DOC] Docstrings match behavior (apply_stock documents idempotency + layering math as implemented; stocks.yaml header documents the Wild-absence convention).
- [VERIFIED] [EDGE] Index alignment client↔server — stock_options built in scene.choices order from the same filtered view (_filter_class_choices) the wire protocol uses; UI responds String(index+1); server maps 1-based back. Traced end-to-end stocks.yaml → loader → _stockify → client → apply_choice → chosen_stock_id → init_mutation → apply_stock → span.
- [VERIFIED] [TEST] No vacuous assertions in the new suites — value-specific asserts incl. error-message content; wiring tests at production seams (load_genre_pack, init seam, full-App WebSocket).

**Data flow traced:** stocks.yaml → load_stock_registry (catalog cross-validated, loud) → World.stocks → _stockify (labels/deltas only, no protocol shape change) → client index response → builder.apply_choice → chosen_stock_id/chosen_saint_id → init_mutation_state_for_session (loud guards) → apply_stock (idempotent, generic) → character/state + awn.stock.applied span. Safe except at the two _stockify silent-return branches and the back-navigation divergence above.
**Pattern observed:** good — the saints.yaml seam pattern (absence/presence/loud-failure triple) faithfully replicated for stocks at loader.py stock block; bad — back-nav arithmetic (`len(_results)` as scene index) was an implicit invariant nobody owned.
**Error handling:** loud and naming the offender everywhere except the two _stockify branches (findings 2, 3).
**Deferred (recorded as delivery findings):** trait-value range bounds (→ 103-8 schema freeze); lore-seeding sanitization of world-authored chargen prose (pre-existing ADR-047 gap, not introduced here).

**Handoff:** Back to TEA (red rework) — finding 1 is a testable logic bug; findings 2-4 get tests in the same pass.

### Reviewer (code review) — Delivery Findings

- **Improvement** (non-blocking): StockDef numeric trait hooks (attr_mods values, move, ac, trauma_target_mod) have no range bounds — crafted content can author any integer.
  Affects `sidequest-server/sidequest/mutation/stocks.py` (add plausible-envelope field validators when 103-8 freezes the full-roster schema).
  *Found by Reviewer during code review.*
- **Gap** (non-blocking): world-authored char_creation prose (labels, descriptions, narration) is seeded into narrator-reachable lore without passing the ADR-047 `sanitize_player_text` seam — pre-existing path, surface enlarged by every new world flow.
  Affects `sidequest-server/sidequest/game/lore_seeding.py` (route content-YAML strings through the existing sanitization seam).
  *Found by Reviewer during code review.*
## TEA Assessment (rework, 2026-06-11)

**Tests Required:** Yes — review rework pass pinning all four Reviewer findings.

**Test Files (rework delta):**
- `tests/game/test_builder_stock_branching.py` — +4 back-navigation tests: go_back/revert across a skipped branch scene return to the scene actually ANSWERED (harbor_seal walk — the discriminating shape where the skip precedes the answered scene), back-then-forward branch coherence, double-back. Pins review [HIGH] finding 1 + [TEST] finding 5.
- `tests/server/test_stockify_stock_frame.py` — NEW: direct contract suite for `_stockify_scene_message` — happy path (frame upgrade, 1:1 option alignment, display names) + the two loud-failure contracts (registry-None naming world+stock_ids; catalog-None naming the granting stock). Pins review findings 2, 3.
- `tests/mutation/test_stock_apply.py` — +1 atomicity test: unknown attr key raises with ZERO prior mutation and no state registration. Pins review finding 4.

**Tests Written:** 9 rework tests; **Status:** RED verified by direct run — 6 failed / 30 passed (passing = prior GREEN suite + the happy-path pins; the sleeper-walk variant of back-nav passes coincidentally because its skip follows the answered scene — documented in the test docstring; the harbor_seal variants fail as intended).

**Rule Coverage (delta):** No Silent Fallbacks → both _stockify loud-failure tests; input-validation atomicity → atomic attr test; missing-edge-case ([TEST] review finding) → back-nav suite.
**Self-check:** 0 vacuous tests.

### TEA (test design) — rework deviations
- No deviations from spec — rework tests pin the Reviewer's findings verbatim.

**Handoff:** To Agent Smith (Dev) for GREEN (fix back-nav, _stockify loud failures, atomic attrs)
## Dev Assessment (rework, 2026-06-11)

**Implementation Complete:** Yes — all four review findings fixed.

**Files Changed (rework delta, sidequest-server only):**
- `sidequest/game/builder.py` — SceneResult gains `scene_index` (stamped at all five construction sites: apply_choice, apply_freeform, arrangement-confirm, arrangement-reject, story-input); `go_back`/`revert` target the popped result's recorded index instead of `len(_results)` (review [HIGH])
- `sidequest/server/websocket_handlers/chargen_mixin.py` — `_stockify_scene_message` raises naming world + stock_ids when stock choices exist with no registry, and naming the stock when a granting stock has no catalog (review findings 2, 3)
- `sidequest/mutation/stocks.py` — attr_mods validated atomically before any mutation (review finding 4)

**Tests:** rework suite 39/39 green; full server suite 11712 passed / 0 real failures (single xdist-flaky `test_102_5_wn_tool_narrator_wiring` passes serially — the documented heavy-e2e-under-xdist pattern). Ruff check + format clean on changed files.
**Branch:** feature/103-2-stock-system (pushed, server @ 101dc2e0)

### Dev (implementation) — rework deviations
- No deviations from spec — fixes implement the Reviewer's prescribed remedies verbatim (SceneResult.scene_index was the Reviewer's suggested mechanism).

**Handoff:** To The Merovingian (Reviewer) for re-review
## Subagent Results (re-review, 2026-06-11)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (server 11712 GREEN incl. -n0 confirmation of the known xdist flake; UI 2071 GREEN; ruff clean; 0 smells; all branches synced with origin — its "2 ahead" was stale tracking data, re-fetched and verified in-sync by lead) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings — lead probed the delta's edges: all five SceneResult append sites stamped (verified by grep — exactly 5 constructions + 2 in-place followup mutations, no unstamped appends) ([EDGE]) |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings — domain covered by security scan ([SILENT]) |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings — lead spot-check: rework tests assert behavior + error-message content; the harbor_seal walk is the correct discriminating shape ([TEST]) |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings — lead spot-check: SceneResult.scene_index doc and _stockify docstring updated to match new behavior ([DOC]) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings — delta adds one optional int field; no type-design surface ([TYPE]) |
| 7 | reviewer-security | Yes | findings | 2 | confirmed 2 (both non-blocking — see below), dismissed 0, deferred 0 |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings — security's dead-ternary finding covers the one simplification in the delta ([SIMPLE]) |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings — security re-verified the four No-Silent-Fallbacks/atomicity rule sites: all compliant ([RULE]) |

**All received:** Yes (2 enabled returned; 7 disabled via settings, domains covered by lead)
**Total findings:** 2 confirmed (non-blocking), 0 dismissed, 0 deferred

### Devil's Advocate (re-review)

Argue the rework is broken. The fix hangs on every result carrying its true scene_index — so hunt for an append that doesn't. There are exactly five SceneResult constructions in builder.py and all five now stamp the index from the same `_phase` match that selected the scene; the followup path mutates the last result in place rather than appending, so it cannot desynchronize the ledger. The None-fallback in go_back/revert is the next suspect: could production reach it? Only if a SceneResult is constructed outside the builder and injected into `_results` — no production code does this (the five test fixtures that do never navigate backward). Could the stamped index itself be stale? It is captured inside the same `case InProgress(scene_index=...)` that selected the scene the player answered — the two cannot diverge within a single call. Could go_back now land on a SKIPPED scene? It targets the index of a scene that was demonstrably PRESENTED and ANSWERED (it produced a result), so no. Could the new _stockify raise crash an innocent world? Only worlds whose char_creation authors stock_id choices — exactly the misconfiguration that must be loud; flickering_reach and every legacy world have no stock_id choices and never reach the check (verified by the regression tests). The double-back test does pass through a transiently-correct intermediate state untested in isolation — but the final landing is asserted and the intermediate is the answered stock scene by the same invariant. I cannot break it.

## Reviewer Assessment (re-review, 2026-06-11)

**Verdict:** APPROVED

All four prior findings verified fixed in commit 101dc2e0:
- [VERIFIED] [EDGE] [HIGH→fixed] Branch-aware back-navigation — SceneResult.scene_index stamped at all five construction sites (builder.py apply_choice/apply_freeform/arrangement-confirm/arrangement-reject/story-input); go_back (builder.py:2274-2282) and revert (:2291-2296) target popped.scene_index. The four rework tests pass, including the discriminating harbor_seal walk and the back-then-forward coherence pin. Complies with the one-result-per-presented-scene ledger doctrine.
- [VERIFIED] [SEC] [SILENT→fixed] _stockify registry-None branch raises naming world + sorted stock_ids (chargen_mixin.py:147 region); catalog-None with a granting stock raises naming the stock. No remaining silent path; error text discloses content identifiers only, no secrets. Complies with No Silent Fallbacks.
- [VERIFIED] [RULE] Atomic attr application — unknown keys collected before any mutation (stocks.py); test asserts zero prior mutation AND no state registration on failure.
- [VERIFIED] [TEST] The exact coverage gap that admitted the [HIGH] is now pinned (go_back/revert/forward/double-back across skips).
- [VERIFIED] [PRE] Mechanical state: server 11712 GREEN (xdist flake confirmed pre-existing, passes -n0), UI 2071 GREEN, ruff clean, 0 smells, all three branches in sync with origin (lead re-verified after preflight's stale tracking read).
- [VERIFIED] [DOC] [TYPE] [SIMPLE] Docstrings updated to the new loud contract; one optional int field added; no over-engineering beyond the two confirmed hygiene items below.

Confirmed non-blocking findings (recorded as delivery findings; Medium/Low do not block per severity policy — neither is production-reachable):
| Severity | Issue | Location | Disposition |
|----------|-------|----------|-------------|
| [MEDIUM] [SEC] | Latent silent fallback: go_back/revert's `scene_index is None → len(_results)` guard re-opens the exact wrong formula for any FUTURE externally-constructed result; production-unreachable today (all five builder sites stamp; the five test fixtures that hand-roll SceneResult never navigate). Rule-matching, so confirmed — not dismissed; severity Medium because the branch is proven unreachable in production | builder.py go_back/revert | Fix in a follow-up: replace the fallback with a loud raise naming the result's scene_id |
| [LOW] [SIMPLE] | Dead `else []` ternary after the catalog-None guard — unreachable (empty list is falsy) but invites regression if the guard is later edited | chargen_mixin.py granted_names | Remove ternary; catalog is provably non-None at that point |

**Data flow traced (delta):** player Back click → handlers/character_creation.py:88 go_back → popped.scene_index (stamped at answer time from the same InProgress match) → InProgress(scene_index=target) → presented scene is always one previously answered. Safe.
**Pattern observed:** good — the fix records provenance on the ledger entry (scene_index on SceneResult) rather than re-deriving it, the same pattern as the existing scene_id field (builder.py:420-428).
**Error handling:** all three new failure paths loud, naming the offender; no secrets in messages.
**Handoff:** To Morpheus (SM) for finish-story

### Reviewer (audit) — rework deviations
- **TEA rework: no deviations** → ✓ ACCEPTED by Reviewer: tests pin the findings verbatim.
- **Dev rework: no deviations** → ✓ ACCEPTED by Reviewer: fixes implement the prescribed remedies; SceneResult.scene_index was the review's suggested mechanism.

### Reviewer (code review) — re-review Delivery Findings
- **Improvement** (non-blocking): replace go_back/revert's scene_index None-fallback with a loud raise naming the offending result, and drop the dead `else []` ternary in _stockify — both latent-silent-fallback hygiene, production-unreachable today.
  Affects `sidequest-server/sidequest/game/builder.py` and `sidequest-server/sidequest/server/websocket_handlers/chargen_mixin.py` (two-line cleanups; bundle into 103-10's wiring pass).
  *Found by Reviewer during code review.*