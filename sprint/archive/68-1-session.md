---
story_id: "68-1"
jira_key: ""
epic: ""
workflow: "tdd"
---
# Story 68-1: Per-genre survivability-pool label reskin — social packs show Composure/Standing/Poise (paired content+server field, extra=forbid)

## Story Details
- **ID:** 68-1
- **Jira Key:** (Jira not configured for this project)
- **Workflow:** tdd
- **Stack Parent:** none

## Story Context

**Title:** Per-genre survivability-pool label reskin — social packs show Composure/Standing/Poise (paired content+server field, extra=forbid)

**Epic:** 68 — Genre tone, terminology & narrator reliability

**Type:** bug

**Points:** 3

**Priority:** p2

**Source:** sq-playtest-pingpong.md (Playtest-3 findings)

**Acceptance Criteria:**

1. Genre pack content model accepts a survivability-pool label field (per-pack override)
2. Server genre models accept this field (pydantic with `extra=forbid`, so the field must be explicitly added to the model, not silently dropped)
3. Social genre packs (tea_and_murder, pulp_noir-style social play) have the label field set to show Composure/Standing/Poise instead of the default HP/Vitality
4. UI surfaces the reskinned label in all survivability-pool displays (character sheet, narration, HUD)
5. Non-social packs continue to use default HP/Vitality terminology (mechanical packs unaffected)

**Implementation Notes:**

- This is a paired content+server field — label originates in genre pack YAML and must be validated by server models
- Server genre models are `pydantic extra=forbid`, meaning unknown fields are rejected; the field must be added to the model definition
- Multiple repos: content (genre packs YAML), server (genre model validation), ui (label surface rendering)
- Workflow: tdd — RED phase will test the field acceptance chain (content → server → ui consumption)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-30T11:19:30Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-30T00:00:00Z | 2026-05-30T10:31:28Z | 10h 31m |
| red | 2026-05-30T10:31:28Z | 2026-05-30T10:43:16Z | 11m 48s |
| green | 2026-05-30T10:43:16Z | 2026-05-30T10:58:45Z | 15m 29s |
| spec-check | 2026-05-30T10:58:45Z | 2026-05-30T11:01:58Z | 3m 13s |
| verify | 2026-05-30T11:01:58Z | 2026-05-30T11:08:30Z | 6m 32s |
| review | 2026-05-30T11:08:30Z | 2026-05-30T11:18:23Z | 9m 53s |
| spec-reconcile | 2026-05-30T11:18:23Z | 2026-05-30T11:19:30Z | 1m 7s |
| finish | 2026-05-30T11:19:30Z | - | - |

## SM Assessment

**Setup complete — ready for RED phase (tea).**

Story 68-1 reskins the survivability-pool label per genre so social packs surface Composure/Standing/Poise instead of HP/Vitality. The crux is a **paired content+server field**: the label originates in genre pack YAML, but server genre models are pydantic `extra=forbid`, so the field must be explicitly added to the model definition — a YAML-only change would be silently rejected at load (violating "No Silent Fallbacks"). Three repos in play: content (pack YAML), server (model + validation), ui (label rendering across character sheet, narration, HUD).

**Key risks for TEA/Dev to cover in tests:**
- Field must round-trip content → server model (extra=forbid means an untyped field fails loud — that failure mode itself is worth a test).
- Non-social packs must keep default HP/Vitality (AC5) — guard against a global default shift.
- UI must read the new field wherever the pool label is shown; verify wiring, not just existence (per project wiring discipline).

**Audience tie-in:** Player-facing legibility fix (Sebastien/Jade want mechanics legible in-tone) — the label is genre-flavor over a shared mechanic, squarely "Crunch in the Genre, Flavor in the World."

No blockers. Jira skipped (not configured). Handing off to Hamlet (tea) for the RED phase.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Behavioral change across content+server+ui (new paired field + render contract).

**Test Files:**
- `sidequest-server/tests/genre/test_survivability_pool_label.py` — 5 tests: `RulesConfig` field acceptance, None default, `extra=forbid` invariant, real-pack loads (tea_and_murder social label ∈ {Composure,Standing,Poise}; caverns_and_claudes default None).
- `sidequest-ui/src/components/__tests__/HpPipScale.test.tsx` — 3 tests: renders genre `survivabilityLabel` (text + aria-label), falls back to "HP" when absent (AC5).

**Tests Written:** 8 tests covering 5 ACs (AC1, AC2, AC3, AC4-primary, AC5)
**Status:** RED — 6 failing as intended; 2 are invariant guards that are correctly GREEN now and must STAY green (server `extra=forbid` typo-rejection; UI "HP" fallback).

**Branches:** `feat/68-1-survivability-pool-label-reskin` created in server + ui (gitflow, target `develop`); orchestrator branch already created by SM.

### AC Coverage

| AC | Behavior | Test(s) | Status |
|----|----------|---------|--------|
| AC1/AC2 | RulesConfig accepts `survivability_pool_label` (extra=forbid) | `test_rules_config_accepts_survivability_pool_label`, `test_rules_config_still_forbids_unknown_field` | RED (accept) / GREEN guard (forbid) |
| AC3 | Social pack carries social label | `test_tea_and_murder_pack_has_social_survivability_label` | RED |
| AC4 | UI renders reskinned label (primary HUD surface) | `HpPipScale` render + aria tests | RED |
| AC5 | Non-social packs keep default HP | `test_caverns_and_claudes_keeps_default_survivability_label`, UI "falls back to 'HP'" | RED (server) / GREEN guard (UI) |

### Rule Coverage (lang-review `python.md`)

| Rule | Test(s) | Status |
|------|---------|--------|
| #2 mutable defaults | New field is `str \| None = None` (non-mutable) — asserted via `test_rules_config_defaults_..._to_none` | covered |
| #3 type annotations at boundary | Field must be typed `str \| None` on `RulesConfig`; default-None test exercises it | covered |
| #6 test quality (no vacuous asserts) | Self-checked — every test asserts a concrete value; no `assert True`, no truthy-only checks | covered |
| #8 unsafe deserialization | Loader path uses existing `yaml.safe_load`; real-pack tests drive the production loader (no new deserialization) | n/a (no new code) |

**Rules checked:** 3 of 13 lang-review rules are directly applicable to a label-field addition (the rest target async/IO/security surfaces this story does not touch).
**Self-check:** 0 vacuous tests written. The 2 currently-passing tests are deliberate invariant guards (typo-rejection, HP fallback), not vacuous.

**OTEL:** Not required — cosmetic label reskin (per server + UI `CLAUDE.md`).

**Handoff:** To Puck (Dev) for GREEN — add the `RulesConfig` field, set `tea_and_murder/rules.yaml`, choose + wire the UI label transport (see Delivery Finding Q), reskin the remaining four UI surfaces.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest-server/sidequest/genre/models/rules.py` — `RulesConfig.survivability_pool_label: str | None = None` (extra=forbid intact).
- `sidequest-server/sidequest/protocol/models.py` — `PartyMember.survivability_pool_label: str | None = None`.
- `sidequest-server/sidequest/server/views.py` — `build_party_member` stamps `sd.genre_pack.rules.survivability_pool_label` on every member.
- `sidequest-server/tests/server/test_reference_url_attach.py` — pin the new attr (`= None`) on two MagicMock-pack fixtures (else PartyMember validation fails).
- `sidequest-content/genre_packs/tea_and_murder/rules.yaml` — `survivability_pool_label: Composure`.
- `sidequest-ui/src/components/HpPipScale.tsx` — optional `survivabilityLabel` prop; otherwise reads the genre label off the resolved character; default "HP".
- `sidequest-ui/src/types/party.ts` — `CharacterSummary.survivability_pool_label?`.
- `sidequest-ui/src/components/CharacterSheet.tsx` — `CharacterSheetData.survivability_pool_label?`.
- `sidequest-ui/src/App.tsx` — fan the label from PARTY_STATUS into `CharacterSummary` (party array) + `CharacterSheetData` (built sheet).
- `sidequest-ui/src/components/CharacterPanel.tsx` — `EdgeBadge`, `FolioEdgeTicks`, and the party-row readout use the label (default "HP").

**Wiring (end-to-end, not half-wired):**
`rules.yaml` → `RulesConfig` → `build_party_member` → `PartyMember` wire → `App.tsx` fan-out → `CharacterSummary`/`CharacterSheetData` → `HpPipScale` (HUD) + `CharacterPanel` (sheet). The `HpPipScale` prop is an optional override; production feeds the label via the character data, which is populated from the server. Verified GREEN.

**Tests:** 8/8 new tests GREEN (5 server + 3 UI). Touched-component regression GREEN (CharacterPanel, CharacterSheet, edge-badge wiring: 98/98). Full server suite: only 6 **pre-existing** failures remain (4 namegen-corpus audits = epic 64-7 backlog; 2 pack-validator = documented missing asset dirs / trope ids) — none reference `survivability_pool_label` and all are structurally unrelated to this change. Lint/format/tsc clean on changed files (2 pre-existing eslint warnings in unrelated App.tsx hooks).

**Branch:** `feat/68-1-survivability-pool-label-reskin` pushed in server, content, ui.

**OTEL:** None added — cosmetic label reskin (exempt per CLAUDE.md).

**Handoff:** To Portia (Reviewer).

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (after one Major git-hygiene fix applied in-phase)
**Mismatches Found:** 3 (1 Major — resolved here; 2 Minor — accepted/deferred)

- **Content commit contaminated with unrelated yulan namegen-corpus WIP** (Extra in code — process/PR-hygiene, **Major**)
  - Spec: 68-1 content change is the single `tea_and_murder/rules.yaml` label.
  - Code: the Dev's content commit (`git add -A`) swept in three uncommitted epic-64-7 files sitting in the shared content working tree — `corpus/shared/yulan_given.txt`, `corpus/shared/yulan_surname.txt`, `genre_packs/space_opera/worlds/perseus_cloud/cultures/yulan.yaml`.
  - Recommendation: **B (fix code)** — applied during spec-check rather than bounced: `git reset --soft` + unstage the three yulan files + recommit only `rules.yaml` + `push --force-with-lease`. The yulan WIP is preserved untouched as uncommitted working-tree changes (1 modified + 2 untracked). Content branch now diffs develop by exactly `tea_and_murder/rules.yaml`. Server + ui commits were already clean.
- **AC3: pulp_noir not reskinned** (Missing in code — behavioral, **Minor**)
  - Spec: "Social genre packs (tea_and_murder, **pulp_noir-style social play**) … Composure/Standing/Poise".
  - Code: only `tea_and_murder` set (→ Composure).
  - Recommendation: **D (defer)** — `pulp_noir` is a gunplay-bearing noir/detective pack, not a drawing-room social pack; whether its survivability pool should reskin is a content judgment, not a server/UI gap. `tea_and_murder` is the canonical social pack and satisfies the AC's spirit. The field is per-pack opt-in, so a later one-line content change covers pulp_noir if desired. Non-blocking.
- **AC4: reskin scoped to player-facing social-pack surfaces, not literally "all displays"** (Different behavior — scoped, **Minor**)
  - Spec: "all survivability-pool displays (character sheet, narration, HUD)".
  - Code: HpPipScale (HUD) + CharacterPanel (sheet) reskinned; CavernActionPanel/TacticalGridRenderer (mechanical-pack-only tactical surfaces) and Dashboard StateTab (dev/GM OTEL panel) left at "HP"; "narration" is narrator prose, not a UI render.
  - Recommendation: **A (update spec)** — the literal "all displays" is over-broad. The un-reskinned surfaces either never render in a social-pack session or are dev-facing; every surface still defaults to "HP", so nothing regresses. Endorse the Dev/TEA deviation; the scoping is sound and documented.

**Architecture note (endorsed):** Dev routed the label on the per-character `PartyMember` frame (stamped from `genre_pack.rules`) rather than a new genre/theme payload. This reuses the existing survivability channel that already carries `current_hp/max_hp` — Reuse-First, minimal new surface, backward-compatible (optional field, old clients ignore it). Mild per-member redundancy (genre-uniform value) is an acceptable trade for not inventing a payload. No coupling concern.

**Decision:** Proceed to review (TEA verify). No hand-back required — the one Major finding was a git-hygiene error corrected in-phase, not a code-logic defect.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 8 (3 server + 5 ui production-code surfaces of the 68-1 diff)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 2 findings | Extract the `label === "HP" ? "HP / Vitality" : label` tooltip ternary (3–4 sites) and the `?? "HP"` default into shared helpers. |
| simplify-quality | 4 findings | **CharacterSheet.tsx survivability bar hardcoded "HP"** while the field was declared on `CharacterSheetData` (real cross-surface inconsistency); add a genre-label test; snake_case/camelCase prop naming (idiom, low). |
| simplify-efficiency | 1 finding | `HpPipScale.survivabilityLabel` prop is a test/override seam not used by production (data rides the character). |

**Applied:** 1 high-confidence fix — reskinned `CharacterSheet.tsx` (the literal "character sheet" survivability bar) to `data.survivability_pool_label ?? "HP"`, matching CharacterPanel/HpPipScale, and added a test locking both the label ("Poise") and default ("HP") paths. This closes an AC4 gap on a player-facing surface (it sits under a rig-only guard today, so it's forward-looking — but it removes the declared-but-unused field inconsistency). Committed `refactor(68-1): CharacterSheet survivability bar uses genre label`.

**Flagged for Review (not applied):**
- *Remove the `survivabilityLabel` prop* (efficiency, medium) — the prop is a harmless override/test seam; removing it would churn the RED tests for marginal gain. Dismissed for this story; a future cleanup could drop it and have tests set the label on the character fixture.
- *Extract tooltip/default helpers* (reuse, medium) — declined: hoisting a one-line ternary across two components into a new shared module is premature abstraction for a 3-pt change; the duplication is trivial and self-documenting. Counter-productive in a *simplify* pass.

**Noted (dismissed):** snake_case (`survivability_pool_label`) vs camelCase prop (`survivabilityLabel`) — standard React wire-vs-prop idiom; no action.

**Reverted:** 0

**Overall:** simplify: applied 1 fix

**Quality Checks:** UI — 102/102 touched-suite tests GREEN, `tsc` clean, eslint clean on changed files. Server — new + touched suites GREEN; the only remaining full-suite failures (6) are pre-existing and unrelated (4 namegen-corpus = epic 64-7; 2 pack-validator = documented missing asset dirs/trope ids), confirmed structurally independent of this label change.

**Handoff:** To Portia (Reviewer).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 blocking (126 tests pass; lint/tsc clean; 1 cosmetic note) | confirmed 0, dismissed 1 (pre-existing cast style), deferred 0 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings — edge cases assessed by Reviewer (empty-string label, below) |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings — assessed by Reviewer (no swallowed errors; `?? "HP"` is a documented display default) |
| 4 | reviewer-test-analyzer | Yes | findings | 5 (2 high, 1 med, 2 low) | confirmed 3 (non-blocking), dismissed 0, deferred 2 (low DRY/scope) |
| 5 | reviewer-comment-analyzer | Yes | findings | 3 (2 high, 1 med) | confirmed 3 (non-blocking doc), dismissed 0, deferred 0 |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings — type design assessed by Reviewer + rule-checker (TS section) |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings — assessed by Reviewer (operator content, not user input; no auth/secret surface) |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings — simplify already run in TEA verify phase (1 fix applied) |
| 9 | reviewer-rule-checker | Yes | findings | 3 (all pre-existing/structural; 0 Python violations of 17 rules) | confirmed 1 (UI test-path gap, non-blocking), dismissed 2 (pre-existing, not in delta) |

**All received:** Yes (4 enabled returned; 5 disabled via `workflow.reviewer_subagents`)
**Total findings:** 4 confirmed non-blocking (2 test-coverage MEDIUM, 1 edge MEDIUM, 3 doc LOW collapsed), 3 dismissed (pre-existing/not-in-delta), 2 deferred (low)

## Reviewer Assessment

**Verdict:** APPROVED

**Summary:** A small, additive, fully-wired per-genre label reskin. Implementation is **verified correct end-to-end**; the confirmed findings are regression-coverage and documentation hardening (MEDIUM/LOW, non-blocking), not runtime defects. No Critical/High.

**Data flow traced (input → destination, safe because…):**
`tea_and_murder/rules.yaml: survivability_pool_label: Composure` → `RulesConfig.survivability_pool_label` (loaded under `extra=forbid`, so a typo fails loud) → `party_member_from_character` stamps it onto `PartyMember.survivability_pool_label` (`views.py:520`) → PARTY_STATUS wire → `App.tsx` maps it into `CharacterSummary` + `CharacterSheetData` behind a `typeof === "string"` runtime guard (non-string → `undefined`, never a spoofed `"HP"`) → `HpPipScale` (`local.survivability_pool_label`), `CharacterPanel` (EdgeBadge/FolioEdgeTicks/party-row), `CharacterSheet` (badge), each `?? "HP"`. Safe: every hop is typed, the value is operator-authored content (not user input), and every render site defaults to "HP" so mechanical packs are untouched (AC5).

### Observations (8+)

- `[VERIFIED]` extra=forbid preserved — `rules.py:974` (RulesConfig) + `protocol/models.py:56` (ProtocolBase) both forbid extras; new field explicitly declared, not via `extra=allow`. Test `test_rules_config_still_forbids_unknown_field` locks it. Complies with No-Silent-Fallbacks.
- `[VERIFIED]` field typing — `str | None = None` on both models; immutable default; mirrors sibling `race_label`/`class_label`. No mutable-default risk.
- `[VERIFIED]` UI default consistency — every render site (`HpPipScale:47`, `CharacterPanel:313/326/577`, `CharacterSheet:170`) falls back to "HP"; `??` (not `||`) correctly coalesces only null/undefined.
- `[VERIFIED]` App.tsx ingestion is guarded — `typeof m.survivability_pool_label === "string"` before use; non-string WebSocket payload → `undefined`, no unguarded trust of wire input (`[SEC]` domain — disabled subagent assessed here: operator content, no auth/secret/injection surface).
- `[TEST]` **(MEDIUM, non-blocking)** Server plumbing at `views.py:520` is unasserted — both `test_reference_url_attach` tests pin the mock to `None` but never assert `member.survivability_pool_label`; the line could be deleted and tests still pass. Confirmed (test-analyzer high). Recommend a fast-follow assertion (`= "Composure"` → `assert member.survivability_pool_label == "Composure"`).
- `[TEST]`/`[RULE]` **(MEDIUM, non-blocking)** `HpPipScale` production path untested — `GameBoard:597` passes no `survivabilityLabel` prop, so production reads `local.survivability_pool_label`; tests cover only the prop path + fully-absent path. Confirmed independently by test-analyzer (high) AND rule-checker (ADD-TS-1, high). Recommend a test: no prop + `character({survivability_pool_label:"Composure"})` → asserts render.
- `[EDGE]` **(MEDIUM/LOW, non-blocking)** Empty-string label (`survivability_pool_label: ""`) is not rejected — `??` passes `""` through, rendering a blank label; `CharacterSheet` title (truthy check) and text (`??`) diverge on `""`. Low plausibility (a YAML empty scalar parses to `None`, which is handled; the server type is `str | None`). Disabled edge-hunter — assessed by Reviewer. Recommend either `NonBlankString | None` on `RulesConfig.survivability_pool_label` or a documented decision to allow it.
- `[DOC]` **(LOW, non-blocking)** Three doc nits: (a) pre-existing stale `CharacterSheet.tsx:45` `hp` doc claims ADR-078/EdgePool (`character.core.edge.current`) — superseded by ADR-114, server writes `hp.current`; now adjacent to my new doc, making the contradiction visible; (b) my `rules.py` comment lists `"HP" / "Vitality"` as the default though only "HP" is the rendered text default; (c) `HpPipScale` "override / tests" comment under-states that the character field is the production path.
- `[SIMPLE]` `(LOW, dismissed)` Redundant `as string` after `typeof` guard (`App.tsx:913/967`) and `key={i}` (`CharacterPanel:798`) — pre-existing patterns the diff replicated/did-not-touch; not introduced by 68-1. Simplify already ran in verify (1 fix applied). Dismissed: not in this story's delta.
- `[TYPE]` `[VERIFIED]` No `any`, no stringly-typed escapes in the new props/fields; `import type` used correctly; field types consistent across the server/client boundary (`str | None` ↔ `string | undefined`).

### Rule Compliance

- **No Silent Fallbacks** (CLAUDE.md <critical>): COMPLIANT. extra=forbid preserved on both models; the `?? "HP"` is a documented *display* default for an intentionally-optional genre-flavor field, not a config-masking fallback (rule-checker ADD-PY-3 concurs).
- **No Stubbing / No half-wired features** (<critical>): COMPLIANT. Full pipeline connected rules→model→wire→App→all render sites; verified by trace + preflight GREEN. (The `survivabilityLabel` prop is an unused-in-prod override, but the production path via the character field IS wired — not a half-wired feature.)
- **Verify Wiring, Not Just Existence** (<critical>): WIRING VERIFIED by Reviewer trace + green integration loader tests. Caveat recorded: the *regression-test* coverage of two specific wiring points (server plumbing, UI prod path) is thin — the two MEDIUM `[TEST]` findings above. The wiring exists and works; the gap is future-regression protection.
- **Every Test Suite Needs a Wiring Test** (<critical>): COMPLIANT at suite level — `test_survivability_pool_label.py` drives real content through the production `load_genre_pack`; UI component tests render real components. (rule-checker PY-6 concurs.)
- **Crunch in the Genre, Flavor in the World** (SOUL.md): COMPLIANT. Label lives on genre `RulesConfig`, uniform across the table; mechanic (ADR-114 ablative HP) unchanged.
- **OTEL Observability**: N/A — cosmetic label reskin (explicitly exempt per CLAUDE.md "Not needed for: Cosmetic UI changes (labels)").
- **No Source-Text Wiring Tests**: COMPLIANT — all tests are behavior/fixture-driven; no source-grep assertions.

### Devil's Advocate

Argue this is broken. *Attack 1 — the prop is theater.* `HpPipScale.survivabilityLabel` is never passed by `GameBoard`; the AC4 tests exercise a code path production never runs, so a regression in the *real* path (`local.survivability_pool_label`) would ship green. A cynic says the headline AC4 test is decorative. **Rebuttal:** the production path IS exercised by `CharacterSheet`'s new "Poise" test (character-data → render) and by my manual trace; but the cynic is right enough that I've recorded the missing `HpPipScale` no-prop test as a confirmed MEDIUM finding. *Attack 2 — silent server delete.* Delete `views.py:520` and every test passes; the "paired content+server field" could rot to content-only and CI wouldn't notice. **Rebuttal:** true, hence the confirmed server-assertion finding; but the field *is* plumbed today (verified), so this is regression risk, not a current bug. *Attack 3 — empty/whitespace content.* A confused homebrew author (Jade!) writes `survivability_pool_label: ""` or `"  "`; `??` lets it through and the HUD shows a blank or whitespace label while the tooltip silently says "HP / Vitality" — a confusing half-state, and exactly the homebrew-robustness the project cares about. **Rebuttal:** YAML empty scalar → `None` (handled); producing `""` requires explicit quoting, an unusual author error — but I've flagged it as a MEDIUM edge case with a concrete fix (`NonBlankString | None`). *Attack 4 — stale doc poisons future readers.* The adjacent ADR-078 EdgePool comment now contradicts the new survivability doc; a future dev "fixing" the pool to match the stale comment could regress HP. **Rebuttal:** real but pre-existing; logged as a LOW doc finding to clean while here. None of these are runtime-breaking on shipped content (mechanical packs → `None` → "HP"; `tea_and_murder` → "Composure"), so none rise to High — but each is a genuine hardening item, recorded, not waved away.

**Pattern observed:** Reuse-First label transport — the genre label rides the existing per-character survivability channel (`PartyMember.current_hp/max_hp`) it labels, rather than inventing a payload (`views.py:520`, `CharacterPanel.tsx:309-319`). Good pattern.

**Error handling:** App.tsx `typeof === "string"` guard on untyped WebSocket payload (`App.tsx:911-914, 965-968`) — non-string → `undefined` → "HP". Correct, defensive.

**Handoff:** To SM for finish-story. Two MEDIUM test-coverage findings + LOW doc nits recorded as non-blocking Delivery Findings with a recommended fast-follow (see below).

## Delivery Findings

No upstream findings at this time.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Reviewer (code review)

- **Improvement** (non-blocking, recommended fast-follow): Server plumbing at
  `views.py:520` (`survivability_pool_label=sd.genre_pack.rules...`) has no behavioral
  assertion — deleting the line would not fail any test. Affects
  `sidequest-server/tests/server/test_reference_url_attach.py` (set one mock's
  `rules.survivability_pool_label = "Composure"` and assert
  `member.survivability_pool_label == "Composure"`). *Found by Reviewer during code review.*
- **Improvement** (non-blocking, recommended fast-follow): `HpPipScale`'s production path
  (no `survivabilityLabel` prop → `local.survivability_pool_label`) is untested; tests
  cover the prop path + fully-absent path only. Affects
  `sidequest-ui/src/components/__tests__/HpPipScale.test.tsx` (add a no-prop test with
  `character({survivability_pool_label:"Composure"})`). Confirmed independently by
  test-analyzer + rule-checker. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Empty/whitespace label (`survivability_pool_label: ""`)
  is not rejected — renders a blank label (homebrew-robustness gap; Jade authors content).
  Affects `sidequest-server/sidequest/genre/models/rules.py` (consider
  `NonBlankString | None`) or document that `""` is acceptable. *Found by Reviewer during
  code review.*
- **Improvement** (non-blocking, doc): (a) pre-existing stale `CharacterSheet.tsx:45` `hp`
  doc cites ADR-078/EdgePool — superseded by ADR-114; (b) `rules.py` comment lists
  `"HP"/"Vitality"` as the rendered default though only "HP" is the text default;
  (c) `HpPipScale.tsx` "override / tests" comment under-states the character field is the
  production path. Affects `sidequest-ui/src/components/{CharacterSheet,HpPipScale}.tsx`,
  `sidequest-server/sidequest/genre/models/rules.py`. *Found by Reviewer during code review.*

### TEA (test design)

- **Question** (non-blocking): The wire path for the genre-level survivability label
  to reach the UI is undecided. Established patterns split two ways — genre LABELS are
  resolved server-side (`sidequest/server/dispatch/chargen_summary.py::field_label`),
  while per-character survivability VALUES ride `PartyMember.current_hp/max_hp`
  (`protocol/models.py`) and fan into `CharacterSummary.hp/hp_max` in the UI. Dev must
  decide whether the resolved label rides the party payload (per-member; path of least
  resistance, mildly redundant since it's uniform across the table) or a genre/theme
  payload (genre-level; cleaner). Affects `sidequest-server/sidequest/server/views.py`
  (`build_party_member`), `protocol/models.py`, and `sidequest-ui` App.tsx →
  `CharacterSummary`/props. *Found by TEA during test design.*
- **Gap** (non-blocking): AC4 names "all survivability-pool displays (character sheet,
  narration, HUD)" — 5 UI surfaces (CharacterPanel HP badge, HpPipScale,
  CavernActionPanel, TacticalGridRenderer, Dashboard StateTab). Only **HpPipScale** is
  test-pinned (the primary input-co-located HUD readout). Dev must reskin the other four
  consistently. Affects `sidequest-ui/src/components/{CharacterPanel,CavernActionPanel,
  TacticalGridRenderer,Dashboard/tabs/StateTab}.tsx`. Also: an existing wiring test
  `sidequest-ui/src/__tests__/edge-badge-party-status-wiring.test.tsx` asserts the
  survivability pool is labeled "HP" — Dev must confirm it still holds for mechanical
  packs (and update expectations only if it loads a social pack). *Found by TEA during
  test design.*
- **Improvement** (non-blocking): The exact social word for `tea_and_murder` is left to
  content/Dev. `tea_and_murder` already uses "Standing" as a social-capital *resource*
  (`rules.yaml` `resources:`), so reusing "Standing" for the survivability pool is
  semantically ambiguous — "Composure" or "Poise" reads cleaner. The server test only
  asserts membership in {Composure, Standing, Poise}, leaving the choice open. Affects
  `sidequest-content/genre_packs/tea_and_murder/rules.yaml`. *Found by TEA during test
  design.*
- **Note** (non-blocking): This is a cosmetic label reskin — per both server and UI
  `CLAUDE.md` ("Not needed for: Cosmetic UI changes (labels)"), **no OTEL spans are
  required** for this story. Dev/Reviewer should not flag missing telemetry.
- **Improvement** (non-blocking, *test verification*): Two simplify findings were flagged
  but not applied — (1) drop the `HpPipScale.survivabilityLabel` override prop and have
  tests set the label on the character fixture; (2) hoist the `?? "HP"` / `"HP / Vitality"`
  tooltip fallbacks into a shared helper. Both are marginal cleanups deferred to avoid
  test churn / premature abstraction in a 3-pt change. Affects
  `sidequest-ui/src/components/{HpPipScale,CharacterPanel,CharacterSheet}.tsx`. *Found by
  TEA during test verification.*

### Dev (implementation)

- **Resolved (TEA Question — wire transport):** Chose to ride the **per-character
  `PartyMember` channel** rather than a new genre/theme payload. The label is stamped in
  `build_party_member` from `sd.genre_pack.rules.survivability_pool_label`, travels on
  `PartyMember.survivability_pool_label`, and fans into `CharacterSummary` /
  `CharacterSheetData` in `App.tsx`. Rationale: the label *labels* `current_hp/max_hp`,
  which already ride this exact frame — keeping them together reuses the established
  survivability data path (Wire-Up-What-Exists) and adds no new payload surface. Mildly
  redundant (uniform across the table) but the simplest fully-wired path. *Found by Dev
  during implementation.*
- **Resolved (TEA Improvement — social word):** `tea_and_murder` → **Composure** (avoids
  collision with the existing `standing` social-capital resource; fits the cosy-Edwardian
  register). *Found by Dev during implementation.*
- **Note** (non-blocking): The pre-existing UI wiring test
  `edge-badge-party-status-wiring.test.tsx` still passes — its fixtures carry no
  `survivability_pool_label`, so the default "HP" holds (AC5 preserved). *Found by Dev
  during implementation.*
- **Gap** (non-blocking): No end-to-end integration test yet covers the full
  server→wire→UI label path (per-component contracts only). A PARTY_STATUS round-trip
  test asserting a social pack surfaces "Composure" in the rendered HUD would harden this.
  Affects `sidequest-ui` integration tests. *Found by Dev during implementation.*

## Design Deviations

### TEA (test design)
- **Partial AC4 coverage — one UI surface tested, not all five**
  - Spec source: session file AC-4
  - Spec text: "UI surfaces the reskinned label in all survivability-pool displays (character sheet, narration, HUD)"
  - Implementation: Tests pin only `HpPipScale` (the input-co-located HUD readout); the CharacterPanel HP badge, CavernActionPanel, TacticalGridRenderer, and Dashboard StateTab are flagged for Dev as a Delivery Finding rather than test-pinned.
  - Rationale: Keep RED scope proportional to a 3-pt story and avoid brittle multi-component coupling before the label's wire path is decided. HpPipScale is the clearest, most player-facing survivability readout; the server real-pack tests carry the load-bearing content+server contract.
  - Severity: minor
  - Forward impact: Dev must reskin the remaining four surfaces; Reviewer must verify each consumes the label.
- **UI contract pinned at component-prop level, not transport level**
  - Spec source: session file AC-4
  - Spec text: "UI surfaces the reskinned label..."
  - Implementation: The UI test asserts a `survivabilityLabel` prop on `HpPipScale` (with "HP" fallback) rather than asserting an end-to-end payload→render path.
  - Rationale: How the genre-level label reaches the client is an undecided design question (logged as a Delivery Finding for Dev/Architect). Pinning the prop contract keeps the test decoupled from the transport choice while still proving the render behavior and AC5 fallback.
  - Severity: minor
  - Forward impact: Dev owns the transport wiring; a later integration test should cover the full path once the seam is chosen.
- **Verify-phase addendum — CharacterSheet survivability bar reskinned + tested**
  - Spec source: session file AC-4
  - Spec text: "UI surfaces the reskinned label in all survivability-pool displays (character sheet ...)"
  - Implementation: During verify, a simplify-quality finding surfaced that `CharacterSheet.tsx` rendered the survivability bar with a hardcoded "HP" despite the field being declared on `CharacterSheetData`. Applied the `data.survivability_pool_label ?? "HP"` fix and added a test (label="Poise" + default="HP"). This narrows the earlier "partial AC4 coverage" deviation by one surface.
  - Rationale: Closes a declared-but-unused inconsistency on the literal "character sheet" surface; forward-looking (the bar sits under a rig-only guard today).
  - Severity: trivial
  - Forward impact: none — additive consistency fix, default unchanged.

### Dev (implementation)
- **AC4 reskin scoped to player-facing social-pack surfaces; tactical + dev surfaces left at "HP"**
  - Spec source: session file AC-4
  - Spec text: "UI surfaces the reskinned label in all survivability-pool displays (character sheet, narration, HUD)"
  - Implementation: Reskinned the player-facing survivability displays that render in a social-pack session — `HpPipScale` (HUD) and `CharacterPanel` (header `EdgeBadge`, `FolioEdgeTicks` tick-bar, and the party-row inline readout). Did NOT reskin `CavernActionPanel` or `TacticalGridRenderer` (tactical/dungeon surfaces — only appear in mechanical-pack play, where the pack sets no label so they correctly render the "HP" default) or `Dashboard/tabs/StateTab` (the GM/dev OTEL panel — dev-facing, not a player surface per the Sebastien/dev-tooling distinction in CLAUDE.md). "narration" is narrator prose (genre prompt), not a UI render surface — no UI change applies.
  - Rationale: All four un-reskinned surfaces either never render in a social-pack context or are dev-only; reskinning them would add threading with zero player-visible effect. Every surface still defaults to "HP", so nothing regresses. Honest scoping, not a silent cut.
  - Severity: minor
  - Forward impact: If a future pack is BOTH social AND uses tactical maps, `CavernActionPanel`/`TacticalGridRenderer` would show "HP" while the HUD shows the social label — a follow-up would thread the label there. No such pack exists today.

### Reviewer (audit)

- **TEA — Partial AC4 coverage (one UI surface tested)** → ✓ ACCEPTED by Reviewer: reasonable RED scoping for a 3-pt change; the server real-pack tests carry the load-bearing contract. (Noted separately: the *production* HpPipScale path remains untested — captured as a non-blocking Delivery Finding, not a deviation reversal.)
- **TEA — UI contract pinned at component-prop level, not transport level** → ✓ ACCEPTED by Reviewer: decoupling the prop contract from the transport was sound; Dev later chose the transport (PartyMember channel) and it is verified wired. The residual gap (prop is test-only in prod) is logged as a Delivery Finding.
- **TEA — Verify-phase addendum: CharacterSheet survivability bar reskinned + tested** → ✓ ACCEPTED by Reviewer: correct catch and fix; narrows the AC4 scope gap by one player-facing surface. Verified GREEN.
- **Dev — AC4 reskin scoped to player-facing social-pack surfaces; tactical + dev surfaces left at "HP"** → ✓ ACCEPTED by Reviewer: the un-reskinned surfaces (Cavern/TacticalGrid = mechanical-pack-only; Dashboard StateTab = dev panel) never render a social label today and all default to "HP" — no regression, honest documented scoping consistent with the Architect's spec-check endorsement.
- **No undocumented spec deviations found.** The AC3 pulp_noir non-reskin was already captured in the Architect's spec-check (deferred, content judgment). All divergences are explicitly logged and accepted.

### Architect (reconcile)

**Existing-entry verification:** Reviewed all TEA (3) and Dev (1) deviation entries against the code. Each is accurate — spec sources resolve to real text (session-file AC-4), implementation descriptions match the diff, severities and forward-impacts are sound. The Reviewer's audit stamps (4 ACCEPTED) are well-founded. No corrections needed.

**Missed deviation now formalized (6-field):**

- **AC3 partially met — only `tea_and_murder` reskinned, not the "pulp_noir-style social play" AC3 also names**
  - Spec source: `sprint/context/context-story-68-1.md`, AC-3 (and session-file AC-3)
  - Spec text: "Social genre packs (tea_and_murder, **pulp_noir-style social play**) have the label field set to show Composure/Standing/Poise instead of the default HP/Vitality"
  - Implementation: Only `genre_packs/tea_and_murder/rules.yaml` sets `survivability_pool_label: Composure`. `pulp_noir` was not given a label and continues to render the default "HP".
  - Rationale: `pulp_noir` is a gunplay-bearing noir/detective pack, not a drawing-room social-register pack; reskinning its survivability pool is a content/tone judgment, not the server/UI contract this story delivers. `tea_and_murder` is the canonical social pack and exercises the full paired-field path. The field is per-pack opt-in, so covering `pulp_noir` later is a one-line content change with zero engine work — exactly the homebrew-extensibility this story establishes.
  - Severity: minor
  - Forward impact: AC3 is satisfied in spirit (the mechanism + the canonical social pack ship); a follow-up content-only edit can add `pulp_noir` (or any future social world) if the table wants it. No engine dependency on sibling stories.

**AC deferral verification:** No ACs were formally DEFERRED/DESCOPED in an ac-completion table (none present for this story). AC1, AC2, AC3 (tea_and_murder), AC4 (player-facing surfaces), AC5 are all DONE and verified GREEN; AC3's pulp_noir extension and AC4's literal "all displays" are scoped/deferred as documented above and in the Reviewer audit. Nothing slipped through undocumented.

**Reconcile decision:** Manifest complete. Proceed to SM finish.