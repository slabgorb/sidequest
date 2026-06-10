---
story_id: "93-2"
jira_key: ""
epic: "93"
workflow: "tdd"
---
# Story 93-2: Durable creation_answers provenance model + snapshot exposure

## Story Details
- **ID:** 93-2
- **Jira Key:** (none — Jira not integrated)
- **Workflow:** tdd
- **Repos:** sidequest-server
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-10T19:39:29Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-10T19:07:57.315525+00:00 | 2026-06-10T19:09:11Z | 1m 13s |
| red | 2026-06-10T19:09:11Z | 2026-06-10T19:22:04Z | 12m 53s |
| green | 2026-06-10T19:22:04Z | 2026-06-10T19:31:20Z | 9m 16s |
| review | 2026-06-10T19:31:20Z | 2026-06-10T19:39:29Z | 8m 9s |
| finish | 2026-06-10T19:39:29Z | - | - |

## Sm Assessment

**Setup complete — routing to TEA for the RED phase.**

- **Story:** 93-2 "Durable creation_answers provenance model + snapshot exposure" (5 pts, p2, tdd/phased), server-only; UI render is deferred to 93-3.
- **Why now:** 93-2 is the entry point of the 93-2 → 93-3 → 93-4 dependency chain (user originally requested 93-4, which is blocked until this lands).
- **Branch:** `feat/93-2-creation-answers-provenance` on sidequest-server (base: develop).
- **Context:** `sprint/context/context-story-93-2.md` written with technical approach and ACs.
- **Jira:** Not integrated for this story (jira_key empty) — claim skipped explicitly.
- **Scope guardrails for downstream agents:** this is wiring, not new capture — ChoiceInput.choice_label / FreeformInput.text already exist on SceneResult. Add the `creation_answers` ordered provenance list to the Character model, populate in `builder.build()`, expose in the snapshot serialization (CharacterSheetDetails / views.py). No UI changes.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Question** (non-blocking): barsoom (the 93-1 e2e substrate) has no name-entry scene, so the "name answer is never marked archetype_inferred" doctrine is pinned only transitively (marking contract is tied to `freeform_answer_texts()`, which excludes name scenes). Affects `sidequest-server/tests/server/test_93_1_archetype_inference.py` (a future world with a name scene would exercise the exclusion directly). *Found by TEA during test design.*
- **Improvement** (non-blocking): `apply_choice` does not stamp `scene_id` on its SceneResult (only `apply_freeform`/`_apply_story` do); build() recovers scenes by index alignment. Dev may want to stamp scene_id uniformly at the choice site rather than index-aligning in build(). Affects `sidequest-server/sidequest/game/builder.py` (apply_choice ~1833). *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): MechanicalEffects rejects unknown fields (`extra="forbid"`) and TEA's `_drive_scene` helper used a nonexistent `backstory_hook` field — testing-runner replaced it with the real `goals` field. A drive-scene effects survey might help future test authors know which effect fields exist. Affects `sidequest-server/tests/game/test_builder_creation_answers.py` (already fixed). *Found by Dev during implementation.*

### Reviewer (code review)
- **Gap** (non-blocking): chargen freeform payload fields (`choice`, `background`, `description`) have no max_length at the WS boundary — verbatim text now persists on Character and re-broadcasts in every PARTY_STATUS frame, so an unbounded answer is an amplification vector (pre-existing gap; 93-1 already had to bound its own fodder at 4k chars). Affects `sidequest-server/sidequest/protocol/messages.py` (add `Field(max_length=...)` caps as a small follow-up story). *Found by Reviewer during code review.*
- **Question** (non-blocking): `creation_answers` (the player's verbatim chargen words) is visible to all party members, same as `backstory` — consistent with ADR-036 collaborative-visibility doctrine, but 93-3 should consciously confirm the History section exposure policy for peers. Affects `sidequest-ui` History section design (93-3). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): marking matches by raw text equality, so a name-scene answer byte-identical to a fodder answer would be falsely badged `archetype_inferred` on packs that have a name scene; empty/whitespace-only freeform answers also reach the sheet as `value=""` entries. Affects `sidequest-server/sidequest/game/builder.py` + the 93-3 renderer (tolerate/skip empty values; optionally match fodder by scene_id instead of text). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `tests/game/test_builder_creation_answers.py` and `tests/integration/test_creation_answers_wiring.py` need `uv run ruff format` (format is not CI-gated; 18 unrelated files already drift). Affects those two test files (one command + commit at finish). *Found by Reviewer during code review.*

## TEA Assessment

**Tests Required:** Yes
**Reason:** 5-point feature story — new model field, builder population, snapshot exposure, inference marking.

**Test Files:**
- `sidequest-server/tests/game/test_builder_creation_answers.py` — NEW. Unit surface (synthetic scenes): `CreationAnswer` model contract (closed kind Literal, extra=forbid, archetype_inferred default False, `Character.creation_answers` defaults `[]` for pre-93-2 saves), choice/freeform/mixed/StoryInput population in `build()`, prompt==scene.title, verbatim-not-derived values, combined-origin + drive scenes faithful, un-answered scenes excluded, go_back revert safety, JSON + GameSnapshot round-trips preserving `archetype_inferred=True` (persisted-not-recomputed).
- `sidequest-server/tests/integration/test_creation_answers_wiring.py` — NEW. Mandatory wiring test: real caverns_and_claudes chargen walk → `build()` → `party_member_from_character` → `CharacterSheetDetails.creation_answers` → `model_dump()` payload (asserts the serialized wire shape, not just the in-memory model).
- `sidequest-server/tests/server/test_93_1_archetype_inference.py` — APPENDED `TestCreationAnswersInferenceMarking`: all-freeform barsoom e2e marks exactly the fodder scenes `archetype_inferred=True` (marked ⟺ text ∈ `freeform_answer_texts()`); preset walk records answers but marks nothing and never touches the inference SDK.

**Tests Written:** 19 tests covering 6 ACs
**Status:** RED (verified by testing-runner, RUN_ID 93-2-tea-red — cache at `.session/test-runs/93-2-tea-red.md`)

- Failure reasons are all the missing feature: `ImportError: CreationAnswer` (collection) and `AttributeError: 'Character' object has no attribute 'creation_answers'`.
- Baseline intact: `tests/game/test_builder_freeform_class_label.py` + `tests/integration/test_class_signature_wiring.py` — 19/19 pass.
- No unexpected passes.
- Committed on `feat/93-2-creation-answers-provenance` as `0f06cc87 test: add failing tests for 93-2 creation_answers provenance`.

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #2 mutable defaults (class-level list sharing) | `test_character_creation_answers_defaults_empty` (pins per-instance `[]` default) | failing |
| #3 typed boundaries | `test_kind_is_closed_literal` (closed Literal, not str) | failing |
| #6 test quality | Self-check done — every assertion checks specific values; no `assert True`, no bare truthy-only checks without follow-up value assertions | n/a (meta) |
| #8 deserialization trusts structure | `test_unknown_keys_rejected` (extra=forbid), `test_character_json_round_trip_preserves_answers` (model_validate_json) | failing |
| #11 input validation at boundaries | Verbatim value storage tests pin that player text is stored, never eval'd/derived; protocol exposure via typed pydantic model | failing |

**Rules checked:** 4 of 13 lang-review rules applicable to this model/wiring surface have test coverage (remaining rules target exception handling, async, paths, deps — not exercised by a pydantic provenance field; Dev's GREEN diff re-scans all 13).
**Self-check:** 0 vacuous tests found.

**Implementation notes for Julia (Dev):**
- `CreationAnswer` goes in `sidequest/game/character.py`; populate in `builder.build()` from `self._results` (scene recovery: index alignment like the abilities loop at builder.py:2528, or stamp `scene_id` in `apply_choice` — see Delivery Finding).
- Marking seam is the 93-1 confirm path (`chargen_mixin._maybe_infer_archetype_from_freeform` succeeds → mark entries whose text is in `builder.freeform_answer_texts()`); build() itself never marks.
- Snapshot exposure: `CharacterSheetDetails` (protocol/models.py:398) + `party_member_from_character` (views.py:375).
- No UI changes (93-3). No lore plumbing (93-4).

**Handoff:** To Julia (Dev) for implementation (GREEN).

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/protocol/models.py` — NEW `CreationAnswer` model (plain BaseModel, `extra="forbid"`, closed `kind` Literal, `archetype_inferred` default False) placed beside `AbilityDefinition` for the same game→protocol layering reason; `CharacterSheetDetails.creation_answers: list[CreationAnswer]` added (default `[]`).
- `sidequest-server/sidequest/game/character.py` — re-exports `CreationAnswer`; `Character.creation_answers` field (default `[]` so pre-93-2 saves validate); module `__all__`.
- `sidequest-server/sidequest/game/builder.py` — `build()` composes the list from `zip(self._scenes, self._results, strict=False)` (index alignment, the same invariant the abilities loop uses; `result.scene_id` stamp wins when present): FreeformInput → verbatim text; StoryInput → background/description joined (same join as `_apply_story`, pronouns excluded); ChoiceInput with `choice_label` → the label; label-less ChoiceInput (auto-advance, arrangement confirm) skipped. Emits `chargen.creation_answers_recorded` OTEL event (count/kind split/scene_ids).
- `sidequest-server/sidequest/server/views.py` — `party_member_from_character` copies `character.creation_answers` onto the sheet.
- `sidequest-server/sidequest/server/websocket_handlers/chargen_mixin.py` — after successful 93-1 inference, marks entries with `kind=="freeform"` and value ∈ the fodder set (`freeform_answer_texts()` — the single fodder definition, name scenes already excluded there) `archetype_inferred=True`; `provenance_marked` count attribute added to the `chargen.archetype_inferred` span (OTEL lie-detector shows marking engaged).
- `sidequest-server/tests/game/test_builder_creation_answers.py` — test-data fix by testing-runner: `_drive_scene` used a nonexistent `backstory_hook` effect field (MechanicalEffects is `extra="forbid"`); replaced with the real `goals` field. Plus a stale docstring path corrected. No assertion weakened.

**Tests:** 20/20 story tests passing; full regression sweep 3,196 passed / 0 failed / 58 skipped (testing-runner RUN_ID `93-2-dev-green`, cache `.session/test-runs/93-2-dev-green.md`).
**Quality:** ruff clean on all changed files; pyright 21 errors before and after on the touched files (all pre-existing, zero introduced).
**Branch:** `feat/93-2-creation-answers-provenance` (pushed; commits `0f06cc87` tests, `3f5b57f2` implementation).

**Handoff:** To O'Brien (TEA) for verify (simplify + quality-pass).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 1 (format drift, 2 test files) | confirmed 1 (downgraded LOW), dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | Yes | findings | 6 | confirmed 3, dismissed 2, deferred 1 |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings — domain covered by lead, see [SILENT] |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings — domain covered by lead, see [TEST] |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings — domain covered by lead, see [DOC] |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings — domain covered by lead, see [TYPE] |
| 7 | reviewer-security | Yes | findings | 4 | confirmed 2, dismissed 1, deferred 1 |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings — domain covered by lead, see [SIMPLE] |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings — lead performed rule-by-rule enumeration, see Rule Compliance |

**All received:** Yes (3 enabled returned; 6 disabled via workflow.reviewer_subagents)
**Total findings:** 6 confirmed, 3 dismissed (with rationale), 2 deferred

**Decisions detail:**
- [EDGE] empty-StoryInput `value=""` entry (medium) — CONFIRMED as [MEDIUM], non-blocking; 93-3 renderer must tolerate empty values.
- [EDGE] whitespace-only freeform recorded unstripped while fodder strips (medium) — CONFIRMED as [MEDIUM], non-blocking; marking stays correct (unmarked); display-only concern for 93-3.
- [EDGE] peer exposure of verbatim answers (medium) — CONFIRMED, downgraded to [LOW]: identical exposure profile to the existing `backstory` field at views.py:387, and CLAUDE.md/ADR-036 doctrine (2026-05-09) is collaborative visibility for this table, sealed visibility reserved for PvP. Captured as a Delivery Finding for the 93-3/product surface.
- [EDGE] scene_id-vs-position divergence diagnostic (low) — DEFERRED: they cannot disagree today (stamped from the same `self._scenes[scene_index]`); a debug assert is a nice-to-have for future refactors.
- [EDGE] mixed-hint scene relabeling (low) — DISMISSED: `_filter_class_choices` only drops choices, never relabels (builder.py:2836 `model_copy(update={"choices": kept})`); the flagged path cannot occur.
- [EDGE] old-server-loads-new-save forward compat (low) — DISMISSED as out of scope: single-operator deployment, saves migrate forward only (ADR-115 importer is one-way); `extra="forbid"` on Character is the project's documented fail-loud stance.
- [SEC] unbounded freeform length at protocol boundary (medium) — CONFIRMED as [MEDIUM], non-blocking, and pre-existing: `CharacterCreationPayload.choice/background/description` had no cap before this story; the diff widens persistence of the same field. Captured as a Delivery Finding (the right fix is at the payload boundary, not this story's surface). The inference path already bounds fodder at 4k chars (llm_factory.py:750) per the 93-1 truncation test.
- [SEC] peer broadcast of creation_answers (medium) — CONFIRMED, merged with the [EDGE] finding above (same root), downgraded [LOW] with the same doctrine citation.
- [SEC] scene_ids in span attributes (low) — DISMISSED: scene ids are content-author-controlled pack identifiers ("the_origin"), not player text; explicitly verified by the unit no raw player text rides any new span attribute.
- [SEC] in-place mutation race at the marking seam (low) — DEFERRED: per-session row locks serialize writes (ADR-115) and each player has their own builder (`sd.builder`); the model_copy suggestion is a hardening nicety, not a current defect.
- [PREFLIGHT] ruff format drift in `tests/game/test_builder_creation_answers.py` + `tests/integration/test_creation_answers_wiring.py` — CONFIRMED as [LOW] (verified myself: `2 files would be reformatted`): format is not CI-gated (`just check-all` runs `ruff check`, not `format --check`; 18 pre-existing files already drift). Fix is `uv run ruff format` on the two files — flagged to SM/Dev for the finish phase, non-blocking.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** player freeform text → `CharacterCreationPayload.choice` (WS boundary, pydantic) → `apply_freeform` → `SceneResult.input_type.text` → `build()` → `CreationAnswer.value` (typed, `extra="forbid"`, closed `kind` Literal) → `Character.creation_answers` → PG snapshot JSONB via `model_dump_json()` + parameterized queries (ADR-115) → `party_member_from_character` (views.py:393) → `CharacterSheetDetails.creation_answers` → PARTY_STATUS. Safe because: typed end-to-end, no SQL/shell/eval interpolation, no narrator prompt consumes `creation_answers` today (verified: orchestrator has zero references), and the one LLM path that reads the same text (93-1 inference) wraps it in structural delimiters per ADR-047 with a 4k-char bound.

**Pattern observed:** good — the layering follows the `AbilityDefinition` precedent exactly (protocol owns the model at protocol/models.py:401, game re-exports at character.py:23, both Character and sheet carry the same type); the marking seam reuses `freeform_answer_texts()` as the single fodder definition rather than re-deriving "what fed the inference" (chargen_mixin.py:751) — one source of truth, the name-scene exclusion inherited for free.

**Error handling:** build() runs from Confirmation phase only (`WrongPhaseError` guard at builder.py:2308); zip alignment verified — `answer_followup` mutates the last result without appending (builder.py:2037), `apply_arrangement_reject` appends nothing, so one result per walked scene holds on every path including go_back/revert; no new try/except, no swallowed errors in the diff.

**Observations (tagged, with evidence):**
1. `[VERIFIED]` zip(scenes, results) alignment is sound on every input path — apply_choice/apply_freeform/_apply_story/apply_auto_advance/apply_arrangement_confirm each append exactly one SceneResult then advance; followups mutate in place (builder.py:2037-2060); go_back pops symmetrically (builder.py:2265). Checked against python.md #1/#13 — no rule conflict.
2. `[VERIFIED]` label-less ChoiceInput results (auto-advance builder.py:2117, arrangement builder.py:2174) are excluded by the `choice_label is not None` guard at builder.py:2756 — exactly the "answered scenes only" contract TEA pinned.
3. `[SILENT]` clean — no bare except, no fallback paths added; `result.scene_id or scene_for_answer.id` is a coalesce between two always-equal sources (apply_freeform stamps from the same `self._scenes[scene_index]` the zip walks), not a config-masking fallback.
4. `[TEST]` strong — 19 tests + wiring test assert the serialized payload (`model_dump()["sheet"]["creation_answers"]`), not just in-memory state; testing-runner's fixture fix (`backstory_hook`→`goals`) weakened no assertion. Gap noted: no test for the all-empty StoryInput entry (tracked as the [MEDIUM] above).
5. `[DOC]` accurate — the chargen_mixin comment "this seam is the only writer of archetype_inferred=True" is true (grep: no other assignment site); CreationAnswer field docstrings match behavior; Dev fixed the one stale docstring path.
6. `[TYPE]` sound — closed `Literal["choice","freeform"]`, `extra="forbid"`, bool default False, `default_factory=list` on both new list fields (no shared mutable default, python.md #2). The protocol model is a plain BaseModel like AbilityDefinition (protocol/models.py:42), so nested `model_dump()` keeps all keys (ProtocolBase's empty-omission applies only to the outer sheet — empty list omitted is the documented pre-93-2 shape).
7. `[SEC]` two confirmed non-blocking findings (unbounded payload length — pre-existing boundary gap; peer visibility — consistent with backstory exposure and table doctrine); span attributes carry zero player text (builder.py:2766-2774 logs counts + content ids only).
8. `[SIMPLE]` proportionate — three constructor branches over a tagged union beat a clever dispatch table at this size; no dead code, no speculative abstraction.
9. `[EDGE]` two confirmed edge findings (empty/whitespace values reach the UI layer) — both display-only, both land on 93-3's renderer, neither corrupts marking or persistence.
10. `[RULE]` see Rule Compliance — 13/13 checks enumerated, no violations in the diff.

**Wiring:** verified end-to-end — `build()` (production chargen path, chargen_mixin.py:808) → Character → `party_member_from_character` (called for self + peers in the PARTY_STATUS builder) → wire payload. The integration test drives the same chain against real content. Non-test consumers exist at every link.

### Rule Compliance

| python.md check | Instances in diff | Judgment |
|---|---|---|
| #1 silent exceptions | 0 try/except added | compliant |
| #2 mutable defaults | `creation_answers` ×2 — both `Field(default_factory=list)` (character.py:152, models.py:466) | compliant |
| #3 type annotations | CreationAnswer fields, `creation_answers: list[CreationAnswer]` local (builder.py:2724) | compliant |
| #4 logging | no new error paths; decisions surfaced via OTEL events/attrs instead | compliant |
| #5 path handling | no path operations in diff | n/a |
| #6 test quality | specific value assertions throughout; zero vacuous; fixture fix verified | compliant (format drift [LOW] in 2 test files — style only) |
| #7 resource leaks | no resources acquired | n/a |
| #8 unsafe deserialization | pydantic `extra="forbid"` + closed Literal; round-trip via model_validate_json | compliant |
| #9 async pitfalls | marking loop is pure sync mutation inside the existing async seam; no blocking calls | compliant |
| #10 import hygiene | protocol→game direction preserved (game imports protocol, never reverse); `__all__` added to character.py; no cycles | compliant |
| #11 input validation | player text stored verbatim BY SPEC (AC: "verbatim text, not a derived label"); no interpolation sinks; length cap gap is pre-existing at the payload boundary (Delivery Finding) | compliant for this diff's scope |
| #12 dependency hygiene | no dependency changes | n/a |
| #13 fix-introduced regressions | testing-runner's fixture fix re-scanned — test-data only, no production change | compliant |

### Devil's Advocate

Assume this is broken. The marking seam matches by raw text equality — so a player who types the same words into two scenes gets both marked, and a player whose NAME happens to equal one of their fodder answers gets the name entry falsely badged "inferred from your words." Real? Yes — but only when the name string is byte-identical to a hint-bearing answer, the pack has a name scene (barsoom doesn't), AND the inference fired. The badge would overclaim on one row; no mechanics read the flag. I judge it a genuine but cosmetic edge; logged as a Delivery Finding rather than a blocker. Second attack: a hostile player submits a 10 MB freeform answer. Nothing in the payload caps it; it persists into the snapshot and re-broadcasts in every PARTY_STATUS frame to every socket — amplification, not just storage. This is the strongest finding in the review, and it predates the story (backstory has carried the same unbounded text since chargen existed; the 93-1 inference already had to add its own 4k bound). It needs a payload-boundary cap as its own small story — widening 93-2 to redesign the WS boundary would be scope creep, but leaving it unlogged would be negligence; it's a Delivery Finding with a concrete fix. Third: a future 93-3/93-4 author trusts `value` into a narrator prompt or renders it as HTML — the field is a loaded gun labeled "verbatim player text"; the docstrings say so, but nothing enforces it. Fourth: concurrent confirms mutating shared Character references — per-session serialization (ADR-115 row locks) and per-player builders make this unreachable today. None of these rise to Critical/High; all four are recorded where the next story will trip over them.

**Handoff:** To Winston Smith (SM) for finish-story. Before/at merge: run `uv run ruff format tests/game/test_builder_creation_answers.py tests/integration/test_creation_answers_wiring.py` and amend/commit (LOW, non-blocking, not CI-gated).

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Un-answered scenes excluded from creation_answers**
  - Spec source: context-story-93-2.md, AC "one entry per answered scene"
  - Spec text: "creation_answers contains one entry per answered scene"
  - Implementation: Tests pin that auto-advance display scenes and the arrangement-confirm contribute NO entry — only scenes the player answered (choice pick, freeform text, StoryInput) appear
  - Rationale: "Answered" read strictly: a Continue-ack or stat arrangement has no prompt/answer pair for the 93-3 History section to render
  - Severity: minor
  - Forward impact: 93-3 UI renders exactly the answered list; if product later wants arrangement rows, the contract loosens (tests relax, nothing breaks)
- **Name-entry scene IS recorded (unmarked)**
  - Spec source: context-story-93-2.md, AC "one entry per answered scene"
  - Spec text: same AC; the spec is silent on the name scene specifically
  - Implementation: `test_name_scene_answer_is_recorded` pins the name answer as a normal kind='freeform' entry; the marking contract (fodder-set-based) guarantees it is never archetype_inferred
  - Rationale: The name scene is an answered scene; presentation belongs to 93-3, provenance should not editorialize
  - Severity: minor
  - Forward impact: 93-3 may choose to special-case the name row in display
- **archetype_inferred marking pinned to the fodder set, not "all freeform scenes"**
  - Spec source: context-story-93-2.md, AC "scene(s) whose freeform fed 93-1's inference are marked"
  - Spec text: "The scene(s) whose freeform fed 93-1's archetype inference are marked archetype_inferred=true"
  - Implementation: e2e tests assert marked ⟺ (entry text ∈ `builder.freeform_answer_texts()` AND inference fired); preset walk marks nothing
  - Rationale: `freeform_answer_texts()` IS the 93-1 definition of "fed the inference" (name scenes excluded there); reusing it keeps one source of truth
  - Severity: minor
  - Forward impact: Dev should mark from the same fodder definition, not blanket-flag freeform entries
- **StoryInput recorded as kind='freeform'; pronouns excluded from value**
  - Spec source: context-story-93-2.md, AC kind 'choice' | 'freeform'
  - Spec text: "kind ('choice' | 'freeform'), value (the player's verbatim freeform text OR the chosen option label)"
  - Implementation: the_story (StoryInput) entry asserts kind='freeform' and value CONTAINS the verbatim background + description strings (substring, not equality); pronouns are not asserted into value
  - Rationale: The kind enum is closed; StoryInput is freeform-shaped. Substring assertion leaves Dev free to join background/description fields (the builder already joins with " | " for MechanicalEffects.background); pronouns are mechanical (pronoun_hint), not narrative words
  - Severity: minor
  - Forward impact: 93-3 renders the joined text; exact join format is Dev's choice
- **Save/load AC tested via pydantic JSON round-trip, not a live PG cycle**
  - Spec source: context-story-93-2.md, AC "round-trips through save/load (persisted, not recomputed)"
  - Spec text: "creation_answers is carried in the character snapshot payload and round-trips through save/load (persisted, not recomputed)"
  - Implementation: `GameSnapshot.model_validate_json(model_dump_json())` round-trip with an `archetype_inferred=True` entry (a recompute would lose the flag — that distinguishes persisted from recomputed); no PG store test added
  - Rationale: The PG snapshot store persists the GameSnapshot JSON blob — the model round-trip is the load-bearing seam, and the pg harness adds infra weight without adding coverage of 93-2 code
  - Severity: minor
  - Forward impact: none — pg store tests already cover blob fidelity generically

### Dev (implementation)
- **CreationAnswer defined in protocol/models.py, re-exported from game/character.py**
  - Spec source: context-story-93-2.md, AC-1 + .session file scope ("Add a creation_answers provenance record to the Character model")
  - Spec text: "Character gains a typed creation_answers field"
  - Implementation: The model class lives in `sidequest/protocol/models.py` (plain BaseModel, extra=forbid) and `sidequest/game/character.py` re-exports it; `Character.creation_answers` carries it
  - Rationale: Dependency direction — game imports protocol, never the reverse; the sheet (protocol) and the Character (game) share the type. Identical layering to AbilityDefinition, documented at the definition site. TEA's import path (`from sidequest.game.character import CreationAnswer`) works via the re-export
  - Severity: minor
  - Forward impact: 93-3 (UI) reads the same shape off CharacterSheetDetails; no behavioral difference
- No other deviations from spec — population, marking seam, and snapshot exposure follow TEA's pinned contract exactly.

### Reviewer (audit)
- **TEA: Un-answered scenes excluded from creation_answers** → ✓ ACCEPTED by Reviewer: agrees with author reasoning — a Continue-ack has no answer to render; the strict reading serves the 93-3 surface.
- **TEA: Name-entry scene IS recorded (unmarked)** → ✓ ACCEPTED by Reviewer: provenance should not editorialize; one cosmetic edge (name text colliding with fodder text gets falsely badged) logged as a Delivery Finding, not a flaw in the deviation.
- **TEA: archetype_inferred marking pinned to the fodder set** → ✓ ACCEPTED by Reviewer: single-source-of-truth reuse of `freeform_answer_texts()` is exactly right; verified the implementation does this (chargen_mixin.py:751).
- **TEA: StoryInput recorded as kind='freeform'; pronouns excluded** → ✓ ACCEPTED by Reviewer: pronouns are mechanical, and the substring assertion leaves the join format free; implementation matches (`" | "` join, builder.py:2745).
- **TEA: Save/load AC via pydantic JSON round-trip, not live PG** → ✓ ACCEPTED by Reviewer: the JSONB blob IS `model_dump_json()` output — the round-trip tests the load-bearing seam; a live-PG test would duplicate generic blob-fidelity coverage.
- **Dev: CreationAnswer defined in protocol/models.py, re-exported** → ✓ ACCEPTED by Reviewer: dependency direction is correct and the AbilityDefinition precedent is cited at the definition site; TEA's import path works unchanged.