---
story_id: "57-3"
epic: "57"
workflow: "tdd"
---
# Story 57-3: Promote static genre prose into Stable cached zone

## Story Details
- **ID:** 57-3
- **Epic:** 57
- **Workflow:** tdd
- **Points:** 2
- **Repository:** sidequest-server
- **Stack Parent:** none
- **Branch:** feat/57-3-promote-static-genre-prose-stable
- **Type:** refactor

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-20T15:40:20Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-20T00:00:00Z | 2026-05-20T14:51:55Z | 14h 51m |
| red | 2026-05-20T14:51:55Z | 2026-05-20T15:04:28Z | 12m 33s |
| green | 2026-05-20T15:04:28Z | 2026-05-20T15:14:55Z | 10m 27s |
| spec-check | 2026-05-20T15:14:55Z | 2026-05-20T15:17:09Z | 2m 14s |
| verify | 2026-05-20T15:17:09Z | 2026-05-20T15:23:44Z | 6m 35s |
| review | 2026-05-20T15:23:44Z | 2026-05-20T15:28:27Z | 4m 43s |
| spec-reconcile | 2026-05-20T15:28:27Z | 2026-05-20T15:40:20Z | 11m 53s |
| finish | 2026-05-20T15:40:20Z | - | - |

## Story Context

Four genre prose sections currently register unconditionally on every narrator turn at `orchestrator.py:1330–1373` but live in `SectionBucket.User` (uncached) because their names are absent from `STABLE_SECTION_NAMES`:

- `genre_extraction`
- `genre_keeper_monologue`
- `genre_town`
- `genre_chargen`

Each section is sourced from genre-pack-static `prompts.yaml` blocks that do not mutate mid-session. Per ADR-112's mutability rubric, session-static + unconditional registration = cacheable content that should move to `SectionBucket.System` (the cached path).

Two sections **must NOT** be promoted per ADR-112:
- `genre_combat_voice` (conditional on `context.in_combat`)
- `genre_chase_voice` (conditional on `context.in_chase`)

Both exhibit cache-thrash patterns at encounter boundaries if promoted; defer is documented in ADR-112 §Defer.

## Acceptance Criteria

1. **Allowlist updated:** `STABLE_SECTION_NAMES` in `sidequest-server/sidequest/agents/prompt_framework/bucket.py:28–41` adds the four section names. No changes to `orchestrator.py` registration sites.

2. **Bucket classifier tests:** Tests assert `default_bucket_for_section()` returns:
   - `SectionBucket.System` for each of the four promoted sections
   - `SectionBucket.User` for each of the two deferred sections (regression guard)

3. **No registration edits:** `git diff sidequest-server/sidequest/agents/orchestrator.py` is empty; the bucket-classifier change alone routes sections into the cached System block.

4. **OTEL cache evidence:** Integration test or direct assertion that promoted sections appear in the `system=` array passed to the SDK, or playtest-visible proof of cache hit tokens on turn 2+. ADR-112 AC-4 fallback: `system_block_sizes_json["stable"]` jumps by ~promoted-sections char-count/4 vs baseline; `cache_read_input_tokens > 0` on turn 2 confirms cached.

5. **Existing tests green:** `just server-test` passes; no regressions in prompt_framework or agents/orchestrator test modules.

## Delivery Findings

### TEA (test design)

- **Improvement** (non-blocking): Story context AC-4 references the new
  span `narrator.system_block_composition` (with attrs
  `stable_section_names`, `stable_section_bytes`, `user_section_bytes`,
  `cache_warm`) per ADR-112 §Observability discipline, but that span is
  not yet emitted by the production code path. The RED tests use the
  existing `narration.turn.system_block_sizes_json` attribute (shipped
  in PRs #360 + #264, 2026-05-20) as the direct cache-evidence surface
  instead. ADR-112 §Observability marks the new span as **mandatory**;
  Dev should either add it during GREEN and have the integration test
  also pin it, OR amend ADR-112 to deprecate the redundant span in
  favour of `system_block_sizes_json["stable"]`. The current RED tests
  do NOT block on the new span — they probe the cache plumbing
  directly via the recorded SDK request's system blocks.
  Affects `sidequest-server/sidequest/agents/orchestrator.py` (would
  need a `narrator.system_block_composition` span emit at the
  bucket-classifier hand-off) and/or `docs/adr/112-genre-prose-stable-
  cache-promotion.md` (deprecate the new span). *Found by TEA during
  test design.*

- **Conflict** (blocking): ADR-112 §Decision claims promotion to
  `STABLE_SECTION_NAMES` "moves four Valley-zone sections into the
  cached Stable block" (§Consequences:Positive line 246), and the
  story-start brief expects `system_block_sizes_json["stable"]` to
  jump by the promoted sections' size. BUT the current zone-aligned
  cache split at `orchestrator.py:3112-3135` (ADR-101 Phase D Task 6)
  builds `stable_text` from **Primacy + Early** zones only, while the
  four sections register at `AttentionZone.Valley`. So allowlist
  promotion alone routes them into `system_blocks[1]` (the **uncached**
  Valley follow-on block), not `system_blocks[0]` (cached). The literal
  4-line allowlist edit is necessary but not sufficient: Dev will hit
  the integration-test assertion that the markers must land in
  `system_blocks[0].text` and need to choose between (a) re-zone the
  four registrations from Valley → Primacy/Early at
  `orchestrator.py:1373..1408` (small additional edit, contradicts
  ADR-112's "registration sites unchanged" claim but realises the
  cache savings), (b) mark Valley cacheable via an additional
  `cache_control` block (extends ADR-101 Phase D Task 6 — bigger
  change), or (c) update the test expectation to allow Valley
  placement and amend ADR-112 to remove the "cached Stable block"
  claim (records that allowlist-only is a structural reorganization
  with no actual cache rebate). Recommend escalating to user mid-GREEN
  if the resolution isn't obvious.
  Affects `sidequest-server/sidequest/agents/orchestrator.py:1373-1408`
  (registration sites) AND/OR `docs/adr/112-genre-prose-stable-cache-
  promotion.md` (mechanism claim). *Found by TEA during test design.*

### Dev (implementation)

- **Improvement** (non-blocking): The "Stable" name in
  `STABLE_SECTION_NAMES` is now actively misleading. The allowlist is
  really "System bucket vs User bucket" — three current members
  (`narrator_vocabulary` Late, `genre_transition_hints` Late,
  pre-57-3 the four Valley sections) are or were on the list while
  registering in non-cache-marked zones (Late or Valley), so the
  allowlist alone never implied "cached." Now that 57-3 forces the
  cache mechanism question into the open, a future cleanup could
  either: rename `STABLE_SECTION_NAMES → SYSTEM_BUCKET_SECTION_NAMES`
  and let cache-marker placement be the cache contract; or audit the
  remaining Late-zone allowlist members (`narrator_vocabulary`,
  `genre_transition_hints`) for whether they too should re-zone into
  Early to ride the cache. ADR-112 §Note flagged for follow-up
  already calls out `narrator_vocabulary`'s dynamism question — that
  story would be the natural home. Not in 57-3 scope.
  Affects `sidequest-server/sidequest/agents/prompt_framework/bucket.py`
  (naming and/or docstring) and possibly `sidequest/agents/orchestrator.py`
  (zone updates if the audit promotes more sections). *Found by Dev
  during implementation.*

- **Question** (non-blocking): Story 57-3's AC-4 references the
  ADR-112-mandated `narrator.system_block_composition` OTEL span
  (with `stable_section_names`, `stable_section_bytes`,
  `user_section_bytes`, `cache_warm` attrs). That span is NOT emitted
  by the current production code path; 57-3's integration test instead
  pins the four marker tags in `system_blocks[0].text` directly. The
  GM-panel dashboard row that shipped in PR #360 (2026-05-20) already
  surfaces the per-region byte totals via
  `narration.turn.system_block_sizes_json`, which arguably obsoletes
  the composition span. Open question for Architect: keep the
  composition span as a future task (it adds the section-name list
  which sizes alone don't), or formally deprecate it in an ADR-112
  amendment? Recommend deferring to the next narrator-cache audit;
  the existing `system_block_sizes_json` covers the load-bearing
  observability gap for now.
  Affects `docs/adr/112-genre-prose-stable-cache-promotion.md`
  (§Observability discipline section) and possibly
  `sidequest-server/sidequest/agents/orchestrator.py` (would emit the
  new span). *Found by Dev during implementation.*

### TEA (test verification)

- **Improvement** (non-blocking): `just check-all` surfaces a stale
  upstream TS error in the external `dice-lib` repo
  (`/Users/slabgorb/Projects/dice-lib/src/DiceTray.tsx:11` — TS1484:
  `'Root' is a type and must be imported using a type-only import
  when 'verbatimModuleSyntax' is enabled`). Pre-existing — last touch
  at `e1b74d8 wip: pre-tuner-plan changes (doubles fix, throwAll API,
  docs)` predates 57-3's branch. Not a 57-3 regression. Recommend
  pinning this as a separate chore against `dice-lib`: either fix the
  import to `import type { Root } from …` or relax `verbatimModuleSyntax`
  in the consumer tsconfig. Until then, `just check-all` will report
  a non-zero exit for any sidequest-server story whose review touches
  the full gate. Affects `/Users/slabgorb/Projects/dice-lib/src/DiceTray.tsx`
  (one-line type-only import change) AND/OR
  `sidequest-ui/tsconfig.json` (verbatimModuleSyntax flag). *Found
  by TEA during test verification.*

## Design Deviations

### TEA (test design)

- **Direct cache-evidence assertion instead of new
  `narrator.system_block_composition` span**
  - Spec source: context-story-57-3.md AC-4 + ADR-112 §Observability
    discipline (line 178-189)
  - Spec text: "Add one OTEL span at the bucket-classifier hand-off…
    `narrator.system_block_composition` with `stable_section_names`,
    `stable_section_bytes`, `user_section_bytes`, `cache_warm`"
  - Implementation: Integration test reads the existing
    `narration.turn.system_block_sizes_json` attribute (shipped
    2026-05-20 in PRs #360 + #264) and the recorded
    `system_blocks[*].text` from `FakeAnthropicSdkClient` directly,
    rather than asserting on the not-yet-emitted
    `narrator.system_block_composition` span.
  - Rationale: Per Story 57-3 brief (2026-05-20): "The story context
    AC-4 falls back to 'proxy evidence' (assert system= array contains
    promoted sections). That fallback is now obsolete." The brief
    explicitly redirects the OTEL gate to the cache-plumbing surface
    that shipped in #360+#264. Asserting on the SDK request's
    `system_blocks[0].text` is a *stronger* check than the
    composition-span's `stable_section_names` list (which would pass
    even if the content rode in an uncached follow-on block — the
    bomb the Conflict finding above describes).
  - Severity: minor
  - Forward impact: If ADR-112's new span ships during GREEN, Dev
    should add an additional assertion pinning the four section names
    in its `stable_section_names` attribute. If the span is dropped
    from ADR-112 in favour of the existing `system_block_sizes_json`
    surface, no further action.

- **Single integration test instead of full pre/post-promotion
  baseline comparison**
  - Spec source: context-story-57-3.md AC-4
  - Spec text: "playtest run (or a deterministic integration test)
    emits `cache_creation_input_tokens` on turn 1 and
    `cache_read_input_tokens > 0` on turn 2 for the promoted sections"
  - Implementation: One turn-0 narration with all four promoted
    sections populated on the injected `Prompts` model. The
    pre-promotion comparison is implicit (current state of the
    allowlist, run via the existing test infrastructure), and the
    cache-hit-on-turn-2 metric is left to playtest verification
    rather than a deterministic integration test.
  - Rationale: A two-turn deterministic test would require fake-SDK
    cache-hit metadata to be honoured by the production
    `cumulative_cache_write_*` plumbing — that's a significant
    fixturing effort for a 2-pt story. The single-turn test catches
    the load-bearing failure mode (markers NOT landing in cached
    block); the playtest catches the operational savings.
  - Severity: minor
  - Forward impact: If GREEN-phase Dev wants belt-and-braces, they
    can extend the test to two turns and pin
    `result.cached_input_read_tokens > 0` on the second call. Not
    blocking.

### Dev (implementation)

- **Re-zoned four registration sites from `AttentionZone.Valley` to
  `AttentionZone.Early` alongside the allowlist promotion**
  - Spec source: context-story-57-3.md AC-3 + Technical Guardrails
    "Primary edit site" + ADR-112 §Decision:Promote (pre-amendment)
  - Spec text: "No changes to `orchestrator.py` registration sites …
    same name, same zone, same content, same `PromptSection.new(...)`
    arguments. The classifier change at `bucket.py:28` is the only
    edit needed."
  - Implementation: In addition to the four-entry allowlist edit at
    `bucket.py`, flipped the `AttentionZone` argument from `Valley`
    to `Early` at the four registration sites
    (`orchestrator.py:1374..1408`). ADR-112 amended in the same
    change with a 2026-05-20 amendment block in §Decision:Promote
    explaining the Valley → Early re-zone; §Consequences:Neutral
    updated to reflect the realised zone shift; ADR-112
    `implementation-status` flipped `deferred → partial`.
  - Rationale: ADR-101 Phase D Task 6 (`orchestrator.py:3112..3135`)
    builds `stable_text` (the cache-marked `system_blocks[0]`) from
    `Primacy + Early` zones ONLY. Valley-zone System-bucket content
    rides `system_blocks[1]` with `cache=False`. A literal allowlist-
    only change therefore moves the four sections from the per-turn
    user message into `system_blocks[1]` — uncached — with no actual
    cache rebate. The integration test
    `test_promoted_genre_prose_lands_in_cached_system_block` (TEA
    paranoid check pinning markers in `system_blocks[0].text`)
    surfaces this directly. The Valley → Early re-zone is small (four
    `AttentionZone` argument flips) and is the load-bearing edit;
    keeping the existing single-cache-marker invariant pinned by
    `test_sdk_path_emits_zone_aligned_cacheable_blocks` intact rules
    out the alternative (a second cache marker on the valley block).
    The attention-zone shift was already documented as an accepted
    consequence in ADR-112 §Consequences:Negative — this change
    realises it rather than introducing a new design surface.
  - Severity: minor (scope is the same 4 sections; mechanism differs
    from the pre-amendment ADR text by 4 argument flips, no behaviour
    drift beyond what ADR-112 already accepted)
  - Forward impact: ADR-112's "registration sites unchanged" claim is
    no longer accurate — amended in this change. Future authors who
    consult ADR-112 for guidance on promoting a Valley-zone section
    into Stable now have the correct mechanism in §Decision:Promote.
    No sibling-story impact (epic 57's other live story, 57-5, is on
    `session_helpers.py` snapshot slimming and doesn't touch the
    bucket-classifier / zone-split surface).

### TEA (verify)

- **Skipped the three-agent simplify fan-out during verify phase**
  - Spec source: `pennyfarthing-dist/agents/tea.md` `<verify-workflow>`
    Step 2 ("Fan-out — Spawn Simplify Teammates" — reuse, quality,
    efficiency teammates spawned simultaneously)
  - Spec text: "Spawn all three teammates **simultaneously** using
    the Agent tool. Each gets the same file list but analyzes through
    a different lens."
  - Implementation: Ran the regression sweep (`just check-all`) and
    server-side ruff/pytest as the load-bearing quality gate; did
    NOT spawn the three simplify-* subagents. Single-implementer
    pass; manual review of the diff (4 allowlist entries with
    provenance comments + 4 `AttentionZone.Valley → Early` argument
    flips with provenance comments) confirms no reuse/quality/
    efficiency findings worth a fan-out.
  - Rationale: Project memory rule `feedback_plan_ceremony` —
    "Right-size plan ceremony to the work — <200 LOC mechanical
    refactors get one implementer pass; don't copy big-plan
    TDD-per-method + spec+quality reviewer ceremony onto small
    extractions." The 57-3 production diff is 32 LOC of mechanical
    behaviour (8 single-token edits + comments). Three simplify
    teammates × 3 lenses on this surface is signal-poor relative
    to the overhead. SM's setup-phase assessment also pre-authorised
    the right-size: "No spec/quality reviewer fan-out, no per-method
    TDD ceremony."
  - Severity: trivial (process deviation, not a code or behaviour
    deviation; the load-bearing gate — `just check-all` — still ran
    and passed)
  - Forward impact: None. If future audit shows simplify findings
    were missed, they can be picked up in a follow-up. The
    Reviewer phase still runs and catches anything material.

### Architect (reconcile)

Verified the three existing deviation entries (TEA test design, Dev
implementation, TEA verify) against the actual code, tests, and
ADR-112 amendment. All three carry accurate spec sources, accurate
implementation descriptions, and substantive 6-field content. One
minor accuracy note and no missed deviations:

- **Annotation on TEA (test design) entry — "Direct cache-evidence
  assertion instead of new `narrator.system_block_composition` span"**
  - Cited spec line range "(line 178-189)" is approximate against the
    post-amendment ADR-112 (the `### Observability discipline` heading
    sits at line 189; the span definition body now spans roughly lines
    196–212 after Dev's 2026-05-20 amendment shifted line counts). The
    section name is accurate; only the line range is slightly stale.
    Not load-bearing — section headers are the durable reference.

- **No additional deviations found.** AC-1, AC-2, AC-4, AC-5 were met
  cleanly. The single AC-3 deviation (registration-site re-zone) was
  identified in real-time by TEA in the RED-phase Conflict finding,
  resolved by Dev with the minimum-viable mechanism, and amended in
  ADR-112 in the same PR. The two non-blocking Improvement / Question
  delivery findings (`STABLE_SECTION_NAMES` naming, deferred
  `narrator.system_block_composition` span) are appropriately scoped
  as follow-ups, not 57-3 work.

- **AC deferral records:** no ACs were deferred or descoped — the
  ac-completion gate step is a no-op.

- **Cross-story impact (Epic 57):** confirmed clean. The sibling story
  57-5 (`session_helpers.py` snapshot slimming, 5 pts, TDD per ADR-110)
  operates on a separate code surface (`server/session_helpers.py:485..558`)
  and does not touch the bucket classifier, attention-zone routing, or
  the cache-aligned system-block split. No regression risk between
  the two stories; they can ship independently in any order.

## Sm Assessment

**Scope.** Pure allowlist promotion — 4 entries added to `STABLE_SECTION_NAMES` in `bucket.py`. No registration-site changes. Surgical 2-point refactor.

**Ceremony.** Right-sized: one TEA RED pass + one Dev GREEN pass. No spec/quality reviewer fan-out, no per-method TDD ceremony. Allowlist promotion is a single classifier behavior with a clear positive/negative test pair.

**Test home.** `sidequest-server/tests/agents/test_cache_ttl_prefix_and_otel.py` has OTEL fixtures + fake-SDK wiring. TEA should also add (or extend) a `prompt_framework` bucket-classifier unit test that pins both the promoted-four and the deferred-two (combat/chase voice) — the deferred-two assertion is the regression guard ADR-112 §Defer demands.

**OTEL gate.** AC-4 is now directly verifiable thanks to today's #360+#264. Prefer the direct path (`system_block_sizes_json["stable"]` delta + `cache_read_input_tokens > 0` on turn 2) over the proxy-evidence fallback. Pre-promotion baseline can be captured by temporarily skipping the new entries or by snapshot before/after on a frozen turn fixture.

**Hazards.**
- Cache thrash if the wrong sections get promoted — do NOT include `genre_combat_voice` or `genre_chase_voice`. ADR-112 §Defer explicit on this.
- Pattern reference `sprint/archive/57-4-session.md` is the prior promotion (narrator_vocabulary). Mirror its test shape.
- Personal repo — no Jira step. Story finish writes archive + sprint YAML only.
- ADR-112 implementation-status flips `deferred → partial` when story starts; Dev does that update in the GREEN phase along with the code change.

**Routing.** Phased TDD → TEA picks up RED phase. No tandem/team pairing required for a 2-point allowlist change.

## TEA Assessment

**Tests Required:** Yes
**Reason:** ADR-112 allowlist promotion has a load-bearing wiring
invariant beyond the four-byte allowlist edit (see Delivery Findings,
"Conflict" entry). Unit tests for the bucket classifier alone are
insufficient — they would pass on a literal-spec allowlist-only change
even if the cache plumbing never benefits.

**Test Files:**
- `sidequest-server/tests/agents/test_prompt_framework/test_bucket.py` —
  6 new tests (4 promotion pins + 2 deferral regression guards) plus an
  updated `test_allowlist_minimum_contents` required set.
- `sidequest-server/tests/agents/test_cache_ttl_prefix_and_otel.py` —
  2 new integration tests:
  - `test_promoted_genre_prose_lands_in_cached_system_block` (paranoid
    direct-cache-evidence assertion — markers must land in
    `system_blocks[0].text`, not the user message or any uncached
    follow-on system block)
  - `test_deferred_combat_voice_does_not_ride_cached_system_block`
    (regression guard against an "unconditional-and-promoted" failure
    mode for combat / chase voice).

**Tests Written:** 8 new tests + 1 existing-test extension covering
ACs 1, 2, 4, and 5. AC-3 (no registration-site edits to
`orchestrator.py`) is a reviewer/diff check, not a test, per the
context's literal phrasing.

**Status:** RED (failing as designed — ready for Dev)

### Rule Coverage

`.pennyfarthing/gates/lang-review/python.md` rules applicable to a
~244-line test-only diff:

| Rule | Test(s) | Status |
|------|---------|--------|
| #6 Test quality (vacuous assertions / `assert True`) | self-checked — every new test has a specific bucket / membership / text-substring assertion with a diagnostic failure message | clean |
| #3 Type annotations at module boundaries | `_prompts_with_all_promotions()` helper is private-module scope; existing test helpers in this file follow the same convention (no annotation) | n/a |
| #1 Silent exception swallowing | no `try/except` added | n/a |
| #2 Mutable default arguments | no new function defaults | n/a |
| #4 Logging coverage/correctness | no new logging in test code | n/a |
| #5 Path handling | no path manipulation in tests | n/a |

**Rules checked:** 6 of 6 applicable lang-review rules; only #6 has
material coverage (and is met by construction).

**Self-check:** 0 vacuous tests found. Every assertion compares an
observable value (bucket enum, set membership, substring in a
captured prompt block) against a specific expected value with a
diagnostic failure message naming the section.

**Sidequest project-rules coverage:**
- "Every Test Suite Needs a Wiring Test" (`CLAUDE.md`): the integration
  test in `test_cache_ttl_prefix_and_otel.py` is the wiring test —
  it drives the full `Orchestrator.run_narration_turn` path through
  `FakeAnthropicSdkClient` and asserts on the recorded SDK request.
  Unit tests alone (`test_bucket.py`) only prove the classifier
  returns the right enum.
- "Verify Wiring, Not Just Existence" (`CLAUDE.md`): the integration
  test asserts the four marker tags reach the cached `system_blocks[0]`
  — proves the bucket classifier output is actually consumed by the
  zone-aligned cache split.
- OTEL Observability Principle (`CLAUDE.md`): flagged in Delivery
  Findings as an Improvement — the new `narrator.system_block_
  composition` span ADR-112 mandates is not yet pinned by any test;
  Dev's GREEN-phase scope decision will determine whether it ships.

**Handoff:** To Dev (Major Winchester). GREEN phase resolves the
literal 4-line allowlist edit + the Conflict finding (re-zone vs
new ADR vs test relaxation). Recommend escalating to user mid-GREEN
if the cache-plumbing path isn't obvious from the integration-test
failure message.

## Dev Assessment

**Implementation Complete:** Yes
**Resolution of TEA Conflict finding:** Path B — allowlist promotion
plus `Valley → Early` re-zone at the four registration sites. Real
cache rebate (content rides cache-marked `system_blocks[0]`); honors
the single-cache-marker invariant pinned by
`test_sdk_path_emits_zone_aligned_cacheable_blocks`; consistent with
ADR-112 §Consequences:Negative which already accepted the
attention-zone shift as a known cost. ADR amended in the same change
to remove the contradictory "registration sites unchanged" claim.

**Files Changed (sidequest-server, branch
`feat/57-3-promote-static-genre-prose-stable`):**
- `sidequest/agents/prompt_framework/bucket.py` — add four entries
  (`genre_extraction`, `genre_keeper_monologue`, `genre_town`,
  `genre_chargen`) to `STABLE_SECTION_NAMES`, plus block-comment
  documenting the ADR-112 / 57-3 provenance and the Defer guard for
  the two combat/chase voices.
- `sidequest/agents/orchestrator.py:1367–1411` — four
  `AttentionZone.Valley → Early` argument flips on the registrations
  at lines 1374, 1386, 1397, 1408 (now lines 1374..1417 after the
  inline comments). No other code edits.

**Files Changed (oq-2 orchestrator, branch
`feat/57-3-adr-112-implementation-status`):**
- `docs/adr/112-genre-prose-stable-cache-promotion.md` —
  `implementation-status: deferred → partial`; amend §Decision:Promote
  with a dated 2026-05-20 amendment explaining the Valley → Early
  re-zone; update §Consequences:Neutral line numbers + reflect the
  realised zone shift.

**Tests:** 6866/6866 server suite passing (0 failures, 396 skipped,
115s wall-clock). Targeted Story-57-3 tests (8/8 in
`test_prompt_framework/test_bucket.py` + 10/10 in
`test_cache_ttl_prefix_and_otel.py` including the two new integration
tests) all GREEN. The previously-pinned cache-plumbing assertions —
prefix byte-identity, zone-aligned cacheable blocks, single
cache_marker, system_block_sizes_json schema — remain GREEN unchanged.

**Lint:** `ruff check` clean on the two changed server files.

**Branches pushed:**
- `slabgorb/sidequest-server` `feat/57-3-promote-static-genre-prose-stable` (1 commit ahead of develop)
- `slabgorb/sidequest` `feat/57-3-adr-112-implementation-status` (1 commit ahead of main)

**Acceptance criteria status:**
- AC-1 (allowlist contains four new entries; two deferred names absent): ✅ — verified by `test_allowlist_minimum_contents` plus the per-name pins.
- AC-2 (bucket classifier returns System for the four / User for the two deferred): ✅ — six per-name unit tests.
- AC-3 (no registration-site changes to `orchestrator.py`): ⚠️ deviated — see Design Deviation entry below. AC-3 is the literal claim from the story context that the implementation found to be inaccurate. Re-zone is required to realise the cache rebate AC-4 promises; AC-1/2/4/5 cannot all hold under a literal reading of AC-3.
- AC-4 (OTEL cache evidence; promoted sections in cached system block): ✅ — verified by `test_promoted_genre_prose_lands_in_cached_system_block` asserting all four `<genre-…>` markers land in `system_blocks[0].text`.
- AC-5 (existing tests green): ✅ — full server suite 6866/6866 passes.

**Handoff:** To Reviewer (Colonel Potter) for code review and
PR-creation hand-off back to SM (finish phase).

## Architect Assessment (spec-check)

**Spec Alignment:** Drift detected — single architectural deviation, fully resolved in-PR.
**Mismatches Found:** 1

- **AC-3 ("no registration-site changes to `orchestrator.py`")**
  (different-behavior — architectural, major)
  - Spec: AC-3 in `context-story-57-3.md` reads "`git diff
    sidequest-server/sidequest/agents/orchestrator.py` is empty;
    the bucket-classifier change alone routes sections into the cached
    System block." ADR-112 §Decision:Promote (pre-amendment) reinforced
    this with "the classifier change at `bucket.py:28` is the only edit
    needed."
  - Code: 4 lines of behavioural change at
    `sidequest/agents/orchestrator.py:1374..1408` — each of
    `genre_extraction`, `genre_keeper_monologue`, `genre_town`,
    `genre_chargen` had its `AttentionZone` argument flipped from
    `Valley` to `Early`. Plus 4 inline comments referencing ADR-112 /
    Story 57-3. No other code change.
  - Recommendation: **A — Update spec.** The pre-amendment spec was
    internally inconsistent. AC-3 ("no `orchestrator.py` changes")
    and AC-4 ("OTEL cache evidence; promoted sections in cached
    system block") could not simultaneously hold under the ADR-101
    Phase D Task 6 zone-aligned cache split, which builds the
    cache-marked `stable_text` from Primacy + Early zones only —
    Valley-zone System content rides `system_blocks[1]` uncached.
    Dev surfaced this directly via TEA's paranoid integration test
    `test_promoted_genre_prose_lands_in_cached_system_block`,
    selected the smallest viable resolution (4 `AttentionZone`
    argument flips, no behavioural shift beyond what ADR-112
    §Consequences:Negative already accepted as a known cost), and
    amended ADR-112 in the same change with a dated 2026-05-20
    block in §Decision:Promote correcting the mechanism claim plus
    a §Consequences:Neutral update. ADR-112
    `implementation-status: deferred → partial`. The code is the
    correct answer; the pre-amendment spec was wrong. No hand-back
    to Dev required — the spec has been updated in-PR.

**Alternative resolutions ruled out:**
- **B — Fix code (back to literal AC-3):** would require landing
  the four sections in `system_blocks[1]` uncached, which fails
  AC-4 and renders the cache cost-reduction goal of ADR-112
  structurally inert. Rejected — AC-4 takes priority per AC ordering.
- **C — Mark Valley cacheable (second cache marker):** would break
  the load-bearing single-cache-marker invariant pinned by
  `test_sdk_path_emits_zone_aligned_cacheable_blocks`, the
  byte-stability gate at `test_compose_split_system_prefix_byte_
  identical_across_3_turns`, and would require an ADR-101 Phase D
  Task 6 amendment far broader than 57-3's 2-pt scope. Rejected —
  out-of-scope architectural surface.
- **D — Defer:** the deviation is fully resolved by Dev's amendment;
  there's nothing to push to a future story. Rejected — no need.

**Other ACs:** AC-1, AC-2, AC-4, AC-5 all met cleanly; verified by
the targeted test suite (8 + 10 tests green) and full server suite
(6866/6866 green).

**ADR amendment quality check:**
- `docs/adr/112-genre-prose-stable-cache-promotion.md` carries a dated
  2026-05-20 amendment block in §Decision:Promote that explains the
  mechanism shift in human-readable terms and cross-references
  ADR-101 Phase D Task 6 (the load-bearing constraint).
- `§Consequences:Neutral` was updated in the same change to match —
  the prior "registration sites untouched" note is now an accurate
  "registrations carry `AttentionZone.Early`, re-zoned by 57-3"
  note. No stale text left behind.
- `implementation-status: partial` is the correct status — ADR-112's
  §Observability discipline still has the `narrator.system_block_
  composition` span unshipped (logged as a non-blocking Question in
  Delivery Findings). Dev's recommendation to defer that span is
  endorsed: PR #360's `narration.turn.system_block_sizes_json` covers
  the load-bearing observability gap. A future ADR-112 amendment
  should either ship the span or formally deprecate it; not in 57-3
  scope.

**Test design integrity:**
- TEA's integration test
  `test_promoted_genre_prose_lands_in_cached_system_block` (paranoid
  cached-block assertion) is exactly the lie-detector that surfaced
  the AC-3 / AC-4 contradiction during RED. The test will continue
  to pin the load-bearing invariant for future authors: "promoted to
  Stable" must mean "rides `system_blocks[0]`" — anything else
  silently breaks the cache rebate claim. Keep this test.
- The companion deferral guard
  `test_deferred_combat_voice_does_not_ride_cached_system_block`
  catches the "unconditional-and-promoted" cache-thrash failure mode.
  Keep this test.
- The 6 per-name unit tests in `test_bucket.py` are individually
  trivial but together pin the exact promote/defer split ADR-112
  §Decision mandates. Set-iteration would have hidden which specific
  section broke on regression. Keep.

**Cross-references to pending follow-up work (not blockers):**
- **`narrator.system_block_composition` span** — ADR-112
  §Observability discipline marks this as mandatory, but the
  GM-panel dashboard surface that shipped 2026-05-20 in PRs #360+#264
  (per-region byte totals via
  `narration.turn.system_block_sizes_json`) arguably obsoletes it.
  Either deprecate or ship in a future story. Dev's recommendation
  to defer to a future narrator-cache audit is sound — the existing
  surface covers the load-bearing observability gap.
- **`STABLE_SECTION_NAMES` naming** — Dev's improvement finding that
  the name is now actively misleading is correct: the allowlist is
  "System bucket vs User bucket," not "cached." A future cleanup
  could either rename the symbol or audit the remaining Late-zone
  allowlist members (`narrator_vocabulary`, `genre_transition_hints`)
  for promotion to Early. Not in 57-3 scope.

**Decision:** Proceed to TEA verify phase. Spec drift was discovered
during implementation, resolved by Dev with the minimum-viable
mechanism, and documented exhaustively across the session deviation
log and ADR-112's 2026-05-20 amendment. No hand-back required.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** none (skipped — see deviation below)
**Files Analyzed:** 0

**Overall:** simplify: skipped — right-sized to a 32 LOC mechanical
refactor (4 allowlist entries + 4 zone argument flips + inline
ADR-112 provenance comments). Three-agent simplify fan-out is
big-plan ceremony for a refactor this small; project memory rule
`feedback_plan_ceremony` ("right-size plan ceremony to the work —
<200 LOC mechanical refactors get one implementer pass") applies.

### Quality Checks

**Server (`uv run pytest`):** 6866 passed, 396 skipped, 0 failures
(113.85s). Confirms the targeted Story-57-3 surface and the broader
narrator / prompt-framework regression sweep stay green.

**Server (`uv run ruff check` on changed files):** clean (verified by
Dev pre-commit; confirmed in this phase by `just check-all` running
the full server lint+test gate).

**Client (`npm run lint`):** 0 errors, 1 warning (pre-existing
`react-hooks/exhaustive-deps` in `sidequest-ui/src/App.tsx:1708` —
unrelated to 57-3; lives in App.tsx which 57-3 does not touch).

**Client (`npx tsc -b`):** 1 error in
`/Users/slabgorb/Projects/dice-lib/src/DiceTray.tsx:11` (TS1484:
'Root' is a type and must be imported using a type-only import
when 'verbatimModuleSyntax' is enabled). Captured as a Delivery
Finding (Improvement, non-blocking) — `dice-lib` is an external
sibling repo last touched at `e1b74d8 wip: pre-tuner-plan changes
(doubles fix, throwAll API, docs)` well before 57-3 branched. Not
a regression from this story.

**Handoff:** To Reviewer (Colonel Potter). Server gate clean;
client-side error is pre-existing and upstream — does not block
57-3 review or merge.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — 18/18 spot-check pass, branch linear, ADR frontmatter valid, no code smells |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.edge_hunter=false` |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.silent_failure_hunter=false` |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.test_analyzer=false` |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.comment_analyzer=false` |
| 6 | reviewer-type-design | No | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.type_design=false` |
| 7 | reviewer-security | No | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.security=false` |
| 8 | reviewer-simplifier | No | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.simplifier=false` |
| 9 | reviewer-rule-checker | No | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.rule_checker=false` |

**All received:** Yes (1 returned with clean status, 8 pre-filled as skipped per `pf settings get workflow.reviewer_subagents`)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred from subagents; 3 trivial Reviewer-only observations dismissed in the assessment below.

## Reviewer Assessment

**Verdict:** APPROVE — proceed to finish.

**Surface reviewed:**
- Server production: `sidequest/agents/prompt_framework/bucket.py` (+14, allowlist extension with provenance comment) and `sidequest/agents/orchestrator.py` (+18 / −6, four `AttentionZone.Valley → Early` argument flips with ADR-112 reference comments).
- Server tests: `tests/agents/test_prompt_framework/test_bucket.py` (+100, six per-name unit tests + required-set extension) and `tests/agents/test_cache_ttl_prefix_and_otel.py` (+144, two integration tests + a `_prompts_with_all_promotions` helper).
- Orchestrator docs: `docs/adr/112-genre-prose-stable-cache-promotion.md` (+26 / −14, dated 2026-05-20 amendment to §Decision:Promote + §Consequences:Neutral + `implementation-status: deferred → partial`).
- Branch hygiene: both branches linear, no force-push artifacts, working trees clean.

**Adversarial findings (Reviewer's own read):**

1. **[TEST] trivial** — `test_deferred_combat_voice_does_not_ride_cached_system_block`
   is partially vacuous under the current `simple_turn_context`
   (turn-0 peace; `context.in_combat` and `context.in_chase` both False),
   so the conditional registration guards at `orchestrator.py:1344` and
   `:1357` short-circuit and the `<genre-combat>` / `<genre-chase>` markers
   would be absent regardless of bucket-classifier state.
   **Decision: DISMISS.** The load-bearing defer guards are the two unit
   tests `test_genre_combat_voice_remains_in_user_bucket` and
   `test_genre_chase_voice_remains_in_user_bucket` in `test_bucket.py`,
   which pin the bucket classifier output directly. This integration
   test is belt-and-braces — it would catch the rare double-bug failure
   mode (unconditional registration + classifier promotion in the same
   change) and that's worth keeping even if it doesn't catch any
   single-bug regression on its own.

2. **[COMMENT] trivial** — The three "see comment above" comments at
   `orchestrator.py:1387`, `:1398`, `:1409` reference the canonical
   ADR-112 comment block 12–22 lines earlier. Reordering or splitting
   the four-section block would invalidate the back-reference.
   **Decision: DISMISS.** Idiomatic adjacent-comment de-duplication.
   Re-stating the same five-line block four times would be worse.

3. **[COMMENT] trivial** — Several test docstrings carry orchestrator
   line numbers (`orchestrator.py:1368..1411`, `:1344..1356`) that may
   already be one or two lines off after Dev's inline comments
   (canonical version is `:1374..1417` post-commit). Informational only.
   **Decision: DISMISS.** Line numbers in docstrings rot quickly across
   any nontrivial repo; the section names are the load-bearing reference.
   Not worth a comment-churn commit.

**Spec drift assessment:** The AC-3 deviation ("no registration-site
edits") is fully documented in `### Dev (implementation)` + Architect's
spec-check assessment + ADR-112's 2026-05-20 amendment. I concur with
Architect's Recommendation A (update spec): the pre-amendment spec was
internally inconsistent — AC-3 and AC-4 could not both hold under the
ADR-101 Phase D Task 6 zone-aligned cache split. Dev chose the
minimum-viable mechanism (four `AttentionZone` argument flips) and
amended the contradictory ADR text in the same change. No hand-back.

**Project rules adherence (rubric from `.pennyfarthing/gates/lang-review/python.md`):**

| Rule | Compliance |
|------|------------|
| #1 Silent exception swallowing | n/a — no `try/except` added |
| #2 Mutable default arguments | n/a — no new function defaults |
| #3 Type annotation gaps at boundaries | `_prompts_with_all_promotions()` returns `Any` (avoids importing `Prompts` at module scope where the helper file does dynamic imports for similar reasons); test helper, not a module boundary — compliant |
| #4 Logging coverage / correctness | n/a — no new logging |
| #5 Path handling | n/a — no path manipulation |
| #6 Test quality | every new assertion compares a specific observable (bucket enum, set membership, or substring of a captured prompt block) against a specific expected value with a diagnostic failure message. No `assert True`, no `let _`, no vacuous-pass risk other than the partially-vacuous integration deferred-voice test dismissed above — compliant |

**SOUL.md and CLAUDE.md adherence:**

- "No Silent Fallbacks" (CLAUDE.md): preserved — the bucket classifier
  remains explicit; the four sections fail loudly via the AC tests if
  the allowlist regresses.
- "No Stubbing" / "Don't Reinvent — Wire Up What Exists" (CLAUDE.md):
  the four `AttentionZone.Early` flips reuse the existing zone-aligned
  cache split (ADR-101 Phase D Task 6) and existing cache-marker
  semantics — no new infrastructure introduced.
- "Verify Wiring, Not Just Existence" (CLAUDE.md): the integration
  test `test_promoted_genre_prose_lands_in_cached_system_block` is the
  wiring test — drives `Orchestrator.run_narration_turn` through
  `FakeAnthropicSdkClient` and asserts on the recorded SDK request's
  `system_blocks[0].text`. Catches the "promoted but uncached" failure
  mode this story specifically exists to address.
- "Every Test Suite Needs a Wiring Test" (CLAUDE.md): satisfied — see
  above.
- OTEL Observability Principle (CLAUDE.md): partial — the
  `narration.turn.system_block_sizes_json` attr shipped in PR #360
  covers the load-bearing observability gap. The ADR-112 §Observability
  `narrator.system_block_composition` span is deferred and tracked via
  ADR `implementation-status: partial` + Dev's Question Delivery Finding.

**Pending follow-ups (not blockers):**

- ADR-112 §Observability `narrator.system_block_composition` span —
  deferred to a future narrator-cache audit. ADR is correctly marked
  `partial`.
- `STABLE_SECTION_NAMES` symbol rename to clarify "system bucket" ≠
  "cached" — out of scope, Dev's Improvement finding.
- Upstream `dice-lib` TS1484 verbatimModuleSyntax error — out of scope,
  TEA's Improvement finding.

**Handoff:** To SM (Hawkeye) for finish phase — create the PR, run the
finish ceremony, archive the session.