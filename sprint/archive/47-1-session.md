---
story_id: "47-1"
jira_key: "skip"
epic: "47"
workflow: "trivial"
---

# Story 47-1: Magic Phase 4 — Verification + cut-point smoke (Tasks 4.4-4.5)

> **RE-SCOPED 2026-05-02:** TEA discovered Phase 4 implementation already shipped via PR #183 (`16ac915`). Story repurposed from "implementation" (4 SP, wire-first) to "verification" (2 SP, trivial). Tasks 4.1-4.3 are DONE on develop; this story closes Tasks 4.4-4.5 (manual smoke + dashboard verification per AC1-AC5). See SM Re-routing Assessment below.

## Story Details

- **ID:** 47-1
- **Title:** Magic Phase 4 — UI Surface (LedgerPanel + dashboard verification)
- **Points:** 4
- **Type:** feature
- **Workflow:** wire-first (5 phases: setup → red → green → review → finish)
- **Repository:** sidequest-ui ONLY
- **Worktree:** /Users/slabgorb/Projects/sidequest-ui-magic-iter-4
- **Branch:** feat/magic-iter-4-ui-surface (pre-created via worktree)
- **Stack Parent:** none (independent feature)

## Story Context

**Plan source:** /Users/slabgorb/Projects/oq-1/docs/superpowers/plans/2026-04-28-magic-system-coyote-reach-v1.md (Phase 4 starts at line 4955)

**Spec source:** /Users/slabgorb/Projects/oq-1/docs/superpowers/specs/2026-04-28-magic-system-coyote-reach-implementation-design.md

**Architect addendum:** /Users/slabgorb/Projects/oq-1/docs/superpowers/specs/2026-04-29-magic-system-coyote-reach-architect-addendum.md

**Phase 1-3 verified shipped (verified 2026-05-02):**
- Magic engine module live at sidequest-server/sidequest/magic/ (16 test files, 110 tests)
- magic_state field on GameSnapshot (session.py:535)
- StateDelta.magic flag, ResourceThreshold.direction field
- apply_magic_working() in narration_apply.py:228
- magic.working span route registered
- Content YAML: space_opera/magic.yaml + worlds/coyote_star/magic.yaml present

## Phase 4 Scope: 5 Tasks

### Task 4.1: TypeScript types mirror server MagicState
- **File:** src/types/magic.ts (create)
- Types: WorldKnowledgePrimary, WorldKnowledge, LedgerScope, LedgerDirection, LedgerBarSpec, LedgerBar, BarKey, Flag, WorldMagicConfig, WorkingRecord, MagicState
- Helpers: barKeyToString(), getCharacterBars(), getWorldBars()
- All types hand-maintained to mirror sidequest/magic/models.py — keep in sync

### Task 4.2: LedgerPanel component + tests
- **Files:** 
  - src/components/LedgerPanel.tsx (create)
  - src/components/__tests__/LedgerPanel.test.tsx (create)
- 5 tests: render character bars, render world bars, null magicState, animate on value change, highlight near-threshold
- BarRow subcomponent: bar-id, bar-value (2dp), fill animation (600ms ease-out)
- Near-threshold highlight: within 10% of threshold applies .near-threshold class
- Returns null when magicState is null

### Task 4.3: Wire LedgerPanel into CharacterPanel (THE RISK)
- **File:** src/components/CharacterPanel.tsx (modify)
- Add import: LedgerPanel, MagicState type
- Add prop: magicState: MagicState | null
- Render: <LedgerPanel magicState={magicState} characterId={character.id} />
- **RISK:** Implementer must read CharacterPanel mount site to thread magicState from session-state hook. This is Task 4.3's highest blocker.
- Add wiring test: static import check that CharacterPanel references LedgerPanel

### Task 4.4: Verify dashboard event feed renders magic.working spans
- Manual verification only (no new test file)
- Dashboard event feed already subscribes to state_transition via SPAN_ROUTES
- Confirm: magic.working spans appear in GM dashboard with plugin/actor/costs_debited/flags/ledger_after attributes
- Verify DEEP_RED flag rendering when hard_limit violated
- No code changes; document any rendering gaps in PR as known limitations

### Task 4.5: Phase 4 cut-point — solo demo session
- Run 10-turn Coyote Star session exercising:
  - One innate working with cost (sanity drops, no threshold)
  - One item working (notice rises)
  - One working that crosses sanity → 0.40 (Bleeding through Status appears)
  - One save/load roundtrip mid-session
  - One DEEP_RED-triggering working (narrator improvises hard_limit violation)
- Acceptance criteria: bars animate in CharacterPanel, bleeding-through Status appears, save/load preserves bars, GM dashboard shows spans, DEEP_RED flags visible

## Acceptance Criteria (from plan Task 4.5)

- **AC1:** Bars rise/fall in CharacterPanel.LedgerPanel after every working
- **AC2:** "Bleeding through" Wound appears in existing Status renderer when sanity ≤ 0.40
- **AC3:** Save+load roundtrip preserves bars
- **AC4:** GM dashboard shows magic.working spans
- **AC5:** DEEP_RED flag visible in span attributes when narrator violates hard_limit

## Important Implementation Notes

1. **Worktree context:** Plan paths reference `/Users/slabgorb/Projects/oq-2/sidequest-ui` (stale — written when oq-2 was active). All implementation goes in the WORKTREE: `/Users/slabgorb/Projects/sidequest-ui-magic-iter-4`. Tests, types, components, commits all happen there.

2. **Test commands:**
   - Worktree-local: `cd /Users/slabgorb/Projects/sidequest-ui-magic-iter-4 && npx vitest run`
   - Full smoke: from oq-1 with `just up` (boots all services from oq-1's subrepo clones, NOT the worktree)
   - Manual smoke test of 4.5 must coordinate with running services

3. **Branch state:** Do NOT create branch (already done via worktree). Do NOT switch branches in oq-1's sidequest-ui (it's on feat/narration-streaming for unrelated work).

4. **Server→UI contract:** TypeScript types are hand-maintained mirror of pydantic models. Consider a snapshot/contract test before Phase 5 layers more state on top.

5. **Wire-first workflow:** This story uses the wire-first workflow, which means:
   - RED phase: tests must exercise outermost reachable layer (mounted React component with transport)
   - GREEN phase: every new export must have at least one non-test consumer
   - sq-wire-it audits wiring gaps; no deferrals allowed
   - FULL test suite runs once at review entry, not during green

## Workflow Tracking

**Workflow:** trivial  
**Phase:** finish  
**Phase Started:** 2026-05-02T12:33:18Z (re-scoped)

### Phase History

| Phase | Started | Ended | Duration | Notes |
|-------|---------|-------|----------|-------|
| setup (wire-first) | 2026-05-02 | 2026-05-02T11:49:01Z | 11h 49m | Original setup for implementation story |
| red (wire-first) | 2026-05-02T11:49:01Z | 2026-05-02T re-scoped | brief | TEA discovered work already shipped — handed back to SM |
| setup (trivial) | 2026-05-02 | 2026-05-02 | instant | SM re-scoped to verification, skipped formal setup re-run |
| implement | 2026-05-02 | 2026-05-02T12:27:53Z | 12h 27m |
| review | 2026-05-02T12:27:53Z | 2026-05-02T12:33:18Z | 5m 25s |
| finish | 2026-05-02T12:33:18Z | - | - |

## Sm Assessment

**Setup completed:** 2026-05-02

**Story scope:** Magic Phase 4 — UI Surface only (4 SP). Phase 5 (confrontations, 8-10 SP) is a separate future story.

**Pre-flight verification:**
- Phases 1-3 of magic plan verified shipped (Architect verification 2026-05-02): magic engine module live (16 test files, 110 tests), `magic_state` field on GameSnapshot, StateDelta + ResourceThreshold extended, `apply_magic_working` wired, `magic.working` span route registered, content YAMLs in place.
- Worktree pre-created at `/Users/slabgorb/Projects/sidequest-ui-magic-iter-4` on branch `feat/magic-iter-4-ui-surface` off `origin/develop`.
- New Epic 47 created in current sprint (Sprint 3) — note: foreign to sprint goal "Playtest 3 closeout"; user explicitly approved scope inflation 89→93 pts.

**Workflow choice rationale:** wire-first selected over plain TDD per user. Phase 4's primary risk is Task 4.3 wiring `magicState` from session-state hook through `CharacterPanel` mount site — wire-first's "boundary tests, no half-wired code" discipline directly targets this risk.

**Architect-flagged risks delivered to TEA in session context (above):**
1. Task 4.3 wiring path is implementer-discovery (not pre-resolved in plan)
2. Server↔UI contract is a hand-maintained TypeScript mirror of pydantic models — drift risk for Phase 5
3. Phase 4 cut-point is a manual 10-turn browser session via `just up` from oq-1 (not the worktree)

**Special path note:** Plan text references `/Users/slabgorb/Projects/oq-2/sidequest-ui` paths throughout. These are STALE — written when oq-2 was the active workspace. All implementation work happens in the worktree at `/Users/slabgorb/Projects/sidequest-ui-magic-iter-4`. Session/sprint/plan reads are from oq-1.

**Jira:** skipped (personal project, no Jira tracking).

**Hand-off:** TEA (Fezzik) for RED phase — write failing wire-first boundary tests for LedgerPanel + CharacterPanel integration.

---

## Sm Re-routing Assessment (2026-05-02)

**Trigger:** TEA escalation — Phase 4 implementation already shipped on develop (PR #183, commit `16ac915`). Files present in worktree base: `src/types/magic.ts`, `src/components/LedgerPanel.tsx` + tests, `CharacterPanel.tsx` line 185 wires `<LedgerPanel magicState={magicState} characterId={character.name} />`.

**Decision:** Repurpose 47-1 (user approved path B). New scope is verification of the manual gates in plan Tasks 4.4-4.5 that were never closed.

**Changes applied:**
| Field | Before | After |
|-------|--------|-------|
| Title | Magic Phase 4 — UI Surface (LedgerPanel + dashboard verification) | Magic Phase 4 — Verification + cut-point smoke (Tasks 4.4-4.5) |
| Points | 4 | 2 |
| Workflow | wire-first (5 phases) | trivial (4 phases) |
| Phase | red | implement |
| Description | Implementation work | Verification + manual smoke |

**Verification scope for Dev (Inigo Montoya):**

1. **Worktree dependency setup** at `/Users/slabgorb/Projects/sidequest-ui-magic-iter-4`:
   - `cd /Users/slabgorb/Projects/sidequest-ui-magic-iter-4 && npm install`
   - Sanity-check the install succeeds; report any package version drift vs. develop's lockfile.

2. **Automated test verification** (Tasks 4.1-4.3 ACs):
   - `cd /Users/slabgorb/Projects/sidequest-ui-magic-iter-4 && npx vitest run src/components/__tests__/LedgerPanel.test.tsx`
   - Confirm all 5 LedgerPanel tests pass.
   - Spot-check that types in `src/types/magic.ts` still match `sidequest-server/sidequest/magic/models.py` (the architect's flagged drift risk).

3. **Manual smoke test** (Task 4.5 — full ACs 1-5) — must run from oq-1, NOT the worktree:
   - `cd /Users/slabgorb/Projects/oq-1 && just up`
   - Browser to http://localhost:5173, start a new game in Coyote Star
   - Take 10 turns exercising:
     - One innate working with cost (sanity drops, no threshold) → AC1
     - One item working (notice rises) → AC1
     - One working that crosses sanity → 0.40 → AC1+AC2 ("Bleeding through" Wound appears)
     - One save/load roundtrip mid-session → AC3
     - One DEEP_RED-triggering working (narrator improvises hard_limit violation) → AC5
   - Open GM dashboard via `just otel` → confirm `magic.working` spans appear with attributes → AC4
   - Confirm DEEP_RED flag visible in span attributes → AC5

4. **Report findings** in Delivery Findings section. Each AC: PASS / FAIL / blocked. If anything fails, document specifically what broke (browser console, span feed contents, save file dump).

5. **Optional improvement (non-blocking, per TEA finding #3):** tick the Phase 4 task checkboxes in `/Users/slabgorb/Projects/oq-1/docs/superpowers/plans/2026-04-28-magic-system-coyote-reach-v1.md` (Tasks 4.1-4.3 done, 4.4-4.5 done IF smoke passes). One small commit on the orchestrator on a separate branch — NOT mixed into the worktree.

**Why trivial workflow:** No new code authoring expected. Existing automated tests cover Tasks 4.1-4.3. Tasks 4.4-4.5 are inherently manual smoke gates. If the smoke test reveals bugs requiring code fixes, escalate back to SM to either (a) extend this story scope, or (b) file a follow-up bug story.

**Why skip formal setup re-run:** Session file is intact, worktree is intact, ACs are unchanged, branch is unchanged. Only the workflow type and phase pointer changed. Re-running sm-setup would re-create the same artifacts.

**Acceptance criteria (unchanged):**
- AC1: Bars rise/fall in CharacterPanel.LedgerPanel after every working
- AC2: "Bleeding through" Wound appears in existing Status renderer when sanity ≤ 0.40
- AC3: Save+load roundtrip preserves bars
- AC4: GM dashboard shows magic.working spans
- AC5: DEEP_RED flag visible in span attributes when narrator violates hard_limit

**Tooling note (also flagged loudly):** `pf hooks schema-validation` PostToolUse hook is broken at orchestrator root — `node_modules/yaml` package missing. Hook fails on every Edit to `sprint/*.yaml`. Files validate fine via `pf sprint epic show`. Recommend either:
- Run `npm install yaml` at orchestrator root, OR
- Switch hook to use a Python YAML validator (project standard is Python tooling per CLAUDE.md "Pennyfarthing scripts are Python-based").

This affects every agent making sprint YAML edits. Should be a tiny chore story (`pf-chore` candidate).

**Hand-off:** Dev (Inigo Montoya) for implement phase. After Dev completes verification, Reviewer (Westley) audits the findings, then SM finishes 47-1 and creates 47-2 for Phase 5 per user-approved path C.

---

## Dev Assessment (verification, 2026-05-02)

**Implementation:** N/A (verification chore — no code authored). Story is to confirm Phase 4 ships per ACs.

### Automated Verification — COMPLETE ✅

| Step | Command | Result |
|------|---------|--------|
| Worktree deps | `cd /Users/slabgorb/Projects/sidequest-ui-magic-iter-4 && npm install` | ✅ 757 packages installed, 1 moderate vuln (not blocking) |
| LedgerPanel tests | `npx vitest run src/components/__tests__/LedgerPanel.test.tsx` | ✅ **7 tests passed in 497ms** |
| Type drift spot-check | Compared `src/types/magic.ts` ↔ `sidequest-server/sidequest/magic/models.py` + `state.py` | See drift findings below |

The 7 tests cover:
- Render character bars with values, sections (covers UI half of **AC1**)
- Render world bars in own section (covers UI half of **AC1**)
- Null magicState → null render
- Animate transition on value change (covers UI half of **AC1**)
- Highlight near-threshold (relevant to **AC2** UI cue)
- **Wiring test 1:** CharacterPanel renders LedgerPanel bars when magicState provided — proves Architect Risk #1 (mount-site wiring) closed
- **Wiring test 2:** CharacterPanel renders without LedgerPanel when magicState null

### Type Drift Findings (Architect Risk #2)

| Drift | Server (Python pydantic) | UI (TypeScript) | Severity | Phase 4 impact | Phase 5 risk |
|-------|--------------------------|-----------------|---------:|----------------|--------------|
| **`StatusPromotion` missing** | `LedgerBarSpec.promote_to_status: StatusPromotion \| None` (models.py:151) | No `promote_to_status`, no `StatusPromotion` interface | **Major** | None — Phase 4 doesn't render promotions in LedgerPanel; AC2 satisfied by existing Status renderer (server-driven) | **HIGH** — Phase 5 mandatory_outputs include `status_add_wound`, `status_add_scar`. UI may need to read `promote_to_status` to display the right status text/severity. |
| `HardLimit` shape | Named `HardLimit` BaseModel (models.py:192) | Inline anonymous shape `Array<{ id, description, references_plugin? }>` | Trivial | None | Cosmetic |
| `Plugin` model absent | `Plugin` BaseModel (models.py:205) | Not in TS | Trivial | None — plugins not UI-facing in v1 | Reassess in Phase 5 if confrontation overlay needs plugin metadata |
| Runtime validators absent | pydantic `model_validator` blocks for awareness ordering, threshold direction, range bounds | TS interfaces have no runtime guards | Acceptable | None — server is authoritative, UI receives validated data | Acceptable |
| `WorkingRecord` ↔ `MagicWorking` | Server has BOTH: `MagicWorking` (literal-typed narrator event) AND `WorkingRecord` (looser persisted history) | TS only has `WorkingRecord` matching the loose persisted shape | OK — INTENTIONAL | None — TS mirrors what's actually serialized in `working_log` | None |

**Recommendation for Phase 5 (47-2):** Add `StatusPromotion` interface + `promote_to_status?: StatusPromotion | null` field to `LedgerBarSpec` in TS. Either at the start of Phase 5 or as a Phase 5 prerequisite ticket.

### Manual Smoke Test (Tasks 4.4 + 4.5, AC1-AC5) — REQUIRES USER 🛑

I cannot autonomously perform the 10-turn solo demo because:
1. AC1, AC2, AC5 require live narrator output triggering specific working types and threshold crossings — non-deterministic LLM behavior, cannot be scripted without breaking the test's purpose (it IS the integration test).
2. AC4 requires browser-side observation of the GM dashboard's event feed.
3. AC3 (save/load) is theoretically scriptable but only meaningful if combined with the above.

The `sq-playtest` skill (full-stack Playwright) is interactive — needs human eyes for the playgroup-quality smoke. The honest read: this is a Keith-driven test. He's the one who knows what "Bleeding through Wound appears correctly" looks like.

**Required user actions to close 47-1:**

```bash
# Terminal 1
cd /Users/slabgorb/Projects/oq-1
just up

# Browser: http://localhost:5173
# 1. Start a new game in Coyote Star
# 2. Take 10 turns covering:
#    - Innate working with cost (sanity drops, no threshold)         → AC1
#    - Item working (notice rises)                                    → AC1
#    - Working that crosses sanity ≤ 0.40 (Bleeding through appears)  → AC1 + AC2
#    - Save mid-session, close, reload                                → AC3
#    - Working that violates a hard_limit (DEEP_RED triggers)         → AC5
# 3. Open GM dashboard (just otel) → confirm magic.working spans      → AC4
# 4. Confirm DEEP_RED flag in span attributes                         → AC5
```

**Findings to record after smoke:** PASS / FAIL per AC, with notes on any drift between expected and actual.

### Dev Verdict

**Status:** PARTIAL — automated verification GREEN; manual smoke pending user.

**Recommendation:** Story 47-1 is *implementation-complete* (the work shipped via PR #183) and *automated-test-complete* (7 tests pass, including wiring). Manual smoke is the only outstanding gate. Three sub-options for closing:

| Option | Action | Tradeoff |
|--------|--------|----------|
| 1. User runs smoke now | User executes the 10-turn session, returns PASS/FAIL per AC, Dev appends results, hands to Reviewer | Most thorough; requires Keith's time |
| 2. Defer smoke to next playgroup session | Mark 47-1 as conditionally passed (automated gates green), file a `47-1-followup` to record smoke results when actual playtest happens | Pragmatic; leaves a small open loop |
| 3. Use sq-playtest skill | Invoke `/sq-playtest` for a Playwright-driven smoke (still needs human observation) | Same as #1 with browser automation overhead |

**My recommendation:** Option 2 if no playgroup session is scheduled this week. Phase 5 (47-2) is the unblocker for Rig MVP Phase C, and the smoke gate has been silently broken for ~5 days already (PR #183 merged without the cut-point being closed). Closing 47-1 conditionally + filing the followup is consistent with the actual project state.

### Hand-off

If user picks Option 1 → I append smoke results, hand to Reviewer (Westley).
If user picks Option 2 → SM (Vizzini) closes 47-1 with conditional pass + creates 47-1-followup ticket + creates 47-2 (Phase 5).
If user picks Option 3 → I invoke `/sq-playtest` and we run automated smoke now.

## Subagent Results

All received: Yes. All four code-review subagents spawned in parallel against the (empty) diff. All returned clean — confirms no code was authored in 47-1 (verification chore).

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none — diff is empty (0 files, 0 additions, 0 deletions); no PR | N/A — verification-only story, preflight passes trivially |
| 2 | reviewer-edge-hunter | Yes | clean | none — no diff to analyze | N/A — no edge cases possible without code changes |
| 3 | reviewer-rule-checker | Yes | clean | none — 0 rules checked, 0 violations | N/A — no diff to check rules against |
| 4 | reviewer-security | Yes | clean | none — no diff to scan | N/A — no security surface added |
| 5 | reviewer-comment-analyzer | Yes | clean | none — no diff | N/A — no comments to analyze |
| 6 | reviewer-test-analyzer | Yes | clean | none — no test diff | N/A — no tests authored in this story (existing 7 tests from PR #183 out of scope) |

**Rationale:** Code-review specialists analyze the change diff (`git diff origin/develop`). Story 47-1's diff is provably empty (verified by all 4 subagents independently). The work product was a verification report (Dev Assessment) plus findings (StatusPromotion drift, deferred-smoke decision). Reviewer audited those artifacts directly — see Reviewer Assessment below.

The code under verification (`LedgerPanel.tsx`, `magic.ts`, `CharacterPanel.tsx`) was authored and code-reviewed via PR #183 prior to this story. Re-reviewing those files here would be a duplicate gate.

**Forward note:** If a future verification story DOES author small fixes (e.g., the `StatusPromotion` drift fix in 47-2), the next Reviewer should still run the full subagent suite — the empty-diff condition is the ONLY justification for this clean-by-default outcome.

## Reviewer Assessment (2026-05-02)

**Verdict:** APPROVED with two MANDATORY follow-ups (see below).
**Story type:** Verification chore. No code authored, no PR, no merge action. Review scope = audit of Dev's verification work + drift findings + conditional-pass decision.

### Specialist findings incorporated

- **[DOC]** (reviewer-comment-analyzer): clean — no diff means no new/changed comments or doc strings to evaluate. Forward note: when 47-2 adds `StatusPromotion` interface, the comment-analyzer should verify the interface carries an explanatory docstring referencing this drift finding.
- **[RULE]** (reviewer-rule-checker): clean — 0 rules checked, 0 violations. No code = no project-rule surface.
- **[TEST]** (reviewer-test-analyzer): clean — no test diff. The 7 existing tests in `LedgerPanel.test.tsx` (authored in PR #183) are out of scope for this story's review. Reviewer independently re-ran them and confirmed 7/7 pass; their substance is audited in the "Independent verification" table below, not in this specialist tag.

### Independent verification

| Claim | Verified? | Evidence |
|-------|----------:|----------|
| `npm install` succeeded in worktree | YES (assumed — node_modules present, vitest runs) | Vitest cold-loads test runner without missing-module errors |
| 7/7 LedgerPanel tests pass | **YES (re-run by reviewer)** | `npx vitest run src/components/__tests__/LedgerPanel.test.tsx` → 7 passed in 673ms |
| `StatusPromotion` drift exists | **YES** | `grep -n "StatusPromotion\|promote_to_status" src/types/magic.ts` returns nothing; same grep in `sidequest-server/sidequest/magic/models.py` returns 3 hits (class definition, docstring, field declaration) |
| `WorkingRecord` ↔ `MagicWorking` is intentional, not drift | YES | Server has both classes (`models.py:73 MagicWorking` for narrator events, `state.py:42 WorkingRecord` for persisted history). TS mirrors `WorkingRecord`. Dev's analysis is correct. |
| No git changes in worktree | YES | `git diff origin/develop --stat` empty; `git log origin/develop..HEAD` empty |

Dev's verification work is honest and accurate.

### Adversarial pass — was anything skipped?

| Concern | Result |
|---------|--------|
| Did Dev test `MagicState | null` handling for new sessions? | Yes — wiring test #2 covers it (`renders without LedgerPanel when magicState is null`) |
| Are the 5 plan-spec tests actually present and meaningful? | Yes — the 5 plan tests (character bars, world bars, null state, animate, near-threshold) are all in the file, plus 2 wiring tests that I'd argue are MORE valuable than the plan asked for. |
| Is the worktree pollution an issue? | No — node_modules is gitignored. Worktree is clean for Phase 5 reuse if desired (or can be removed). |
| Is the review-correlation gate satisfied? | Gate `gates/wiring-check` extension applies. The wiring tests in `LedgerPanel.test.tsx:123-181` mount `CharacterPanel` with a `magicState` prop and assert ledger entries render — proves the magicState thread path works end-to-end. **Wiring requirement met.** |
| Was Architect Risk #1 (CharacterPanel mount-site wiring) actually closed? | YES — wiring test #1 mounts CharacterPanel with magicState and asserts both character bars and world bars render. The mount-site wiring is provably correct. |
| Was Architect Risk #2 (server↔UI drift) addressed? | PARTIAL — drift CHECKED and FOUND. The fix isn't in this story's scope (would be code authoring, which 47-1 explicitly isn't). Documented as Dev finding for Phase 5 to consume. |

### Adversarial pass — is Option 2 (defer smoke) actually correct?

I pushed back on this internally:

| Counter-argument | My response |
|------------------|-------------|
| "PR #183 has been live ~5 days; if it were broken Keith would know" | This assumes someone has actually played Coyote Star with magic in those 5 days. No evidence either way. The smoke gate is genuinely unverified. |
| "Closing 47-1 with conditional pass risks losing the followup" | **VALID.** I'm making the followup mandatory, not optional (see below). |
| "The drift finding alone could justify keeping 47-1 open until fixed" | No — the drift fix is Phase 5 work, not Phase 4 verification work. Conflating them would re-enlarge a story we just down-scoped. Phase 5 must consume the finding. |
| "Maybe we should run sq-playtest now even with browser overhead" | Could, but Option 2 was user-chosen with full knowledge. Reviewer respects user judgment unless objectively wrong. Option 2 is defensible: the smoke needs Keith's eyes for "playgroup quality" assessment, not just automated assertions. |

**Verdict on Option 2:** Acceptable, conditional on the two mandatory follow-ups below.

### Mandatory follow-ups (BLOCKING for SM finish)

1. **File `47-1-followup` story** in Epic 47 BEFORE finishing 47-1. Title: "Magic Phase 4 — playtest smoke verification (AC1-AC5)". 1 SP. Workflow: trivial. Description must reference: this session file, the 5 ACs, the manual-test runbook from Dev's assessment. Status: backlog.

2. **Add to 47-2's setup phase a prerequisite check** confirming `StatusPromotion` interface gets added to `src/types/magic.ts` BEFORE Phase 5's confrontation outcome work. The drift finding is currently in 47-1's session — it WILL get lost if 47-2's setup doesn't actively reference 47-1's archive. SM (Vizzini) must include it in the 47-2 session-context block. Recommend adding a "Phase 5 prerequisites" subsection to 47-2's session.

If SM cannot file the followup or wire the Phase 5 prerequisite, REJECT 47-1 finish and escalate.

### Tooling complaint (concur with SM)

The `pf hooks schema-validation` PostToolUse hook is broken at orchestrator root. Reviewer ran into the same `node_modules/yaml` missing-package error indirectly via Edits. This is real friction that wastes context on every YAML touch. Worth a 1 SP chore story (NOT in Epic 47 — this is Pennyfarthing tooling).

### Code-quality and security passes

N/A. No code authored in this story. Existing `LedgerPanel.tsx`, `magic.ts`, and `CharacterPanel.tsx` changes shipped via PR #183 (already reviewed at that time per Pennyfarthing's standard merge-gate). Re-reviewing them in this story is out of scope.

### Hand-off

To SM (Vizzini) for finish flow. SM MUST:
1. File `47-1-followup` story (mandatory follow-up #1)
2. Note the StatusPromotion drift finding for 47-2's setup (mandatory follow-up #2)
3. Then run `pf sprint story finish 47-1`
4. Then create 47-2 (Phase 5) with the StatusPromotion prerequisite baked into the setup brief

## Sm Finish Assessment (2026-05-02)

**Verdict:** READY TO FINISH. Both Reviewer mandatory follow-ups executed.

### Reviewer follow-ups closed

| # | Reviewer requirement | Action taken | Verification |
|--:|---------------------|--------------|--------------|
| 1 | File `47-1-followup` story for deferred manual smoke | Created story **47-2** "Magic Phase 4 — Playtest smoke verification (AC1-AC5)", 1 SP, trivial workflow, type=chore, repos=ui+server. Description references this archive + smoke runbook. | `pf sprint story show 47-2` |
| 2 | Wire StatusPromotion drift into Phase 5 setup brief | Created story **47-3** "Magic Phase 5 — Confrontations Wired", 8 SP, wire-first workflow, type=feature. Description includes "PHASE 5 PREREQUISITE" block referencing the drift, the server source locations (`models.py:114, :151`), the UI gap, and the mandatory_outputs that depend on it. | `pf sprint story show 47-3` |

Westley's get-used-to-disappointment threshold cleared.

### Impact summary

**Story scope:** Verification chore for Magic Phase 4 (already shipped via PR #183). Story repurposed mid-flow when TEA discovered the implementation work was already done.

**Code authored:** Zero. Verified by all 6 review subagents (empty diff against origin/develop).

**Tests run:** 7 LedgerPanel tests independently re-verified by Reviewer (7/7 pass, 673ms).

**Drift discovered:** `StatusPromotion` interface + `promote_to_status` field present server-side, missing from UI types. No Phase 4 impact (existing Status renderer handles auto-promotions); high Phase 5 risk (confrontation `mandatory_outputs` need it). Documented and wired into 47-3 setup brief.

**Manual smoke (AC1-AC5):** Deferred to 47-2 per user-approved Option 2. The 5-day silent gap since PR #183 acknowledged in Reviewer Assessment.

**Phase History (re-scoped mid-flow):**
- setup (wire-first) → red (wire-first, brief discovery) → SM re-route → setup (trivial, instant) → implement (Dev verification) → review (Reviewer audit) → finish (this assessment)

**Sprint impact:** Sprint 3 scope grew 89 → 91 (47-1 = 2 SP). Adds 47-2 (+1 SP) and 47-3 (+8 SP) as new backlog. Final sprint scope: 100 SP (89 original + 2 + 1 + 8).

**Sprint goal alignment:** Epic 47 remains foreign to "Playtest 3 closeout" sprint goal — explicitly user-approved during initial epic creation. Future epics should be scoped at sprint planning time, not mid-flight.

### Outstanding (not blocking 47-1 finish)

1. **`pf hooks schema-validation` broken** — flagged THREE times this session (SM, Dev, Reviewer). Worth its own Pennyfarthing-side chore story (NOT Epic 47). Recommend: `npm install yaml` at orchestrator root OR port hook to Python (project standard). Not filed yet — out of Epic 47 scope.
2. **Plan file checkboxes still unticked** — TEA finding #3 (non-blocking). `docs/superpowers/plans/2026-04-28-magic-system-coyote-reach-v1.md` Phase 4 tasks should be ticked to reflect PR #183. Suggestion: tick during 47-2 close (after smoke verifies) or roll into 47-3 prep.
3. **Worktree retention decision** — `/Users/slabgorb/Projects/sidequest-ui-magic-iter-4` is on `feat/magic-iter-4-ui-surface` (no commits). Either: (a) keep for 47-2 smoke (will need npm install + just up coordination), (b) remove now and recreate later. No code changes ever landed there. Recommend remove after finish — keep environment clean.

### Hand-off

After `pf sprint story finish 47-1` runs:
- 47-1 archives to `sprint/archive/47-1-session.md`
- 47-2 (smoke followup) becomes available for next pickup
- 47-3 (Phase 5) becomes available for next pickup
- Worktree cleanup is user discretion

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement  
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap (blocking):** Phase 4 implementation is ALREADY SHIPPED on develop via `16ac915 feat(magic): Phase 4 — UI surface (LedgerPanel inside CharacterPanel) (#183)`. Tasks 4.1 (`src/types/magic.ts`), 4.2 (`LedgerPanel.tsx` + tests), and 4.3 (CharacterPanel wiring at line 185 with `magicState` prop) are all present in worktree base. The architect's pre-flight verification (2026-05-02) checked Phases 1-3 but did not check Phase 4 — it had silently shipped before this story was created. Affects entire story scope (`47-1`). *Found by TEA during test design.*
- **Question (blocking):** What remains for Phase 4: only Tasks 4.4 (manual dashboard span verification) and 4.5 (10-turn solo demo cut-point covering AC1-5). These are inherently manual smoke tests, not automated tests. RED phase has nothing to fail because tests already exist and presumably pass. Story 47-1 should be repurposed to "Phase 4 verification + cut-point smoke" (~1-2 SP, workflow=trivial), not torn down — the manual verification gates were never closed. Then create 47-2 for Phase 5 (Confrontations). User confirmed this path (B then C). *Found by TEA during test design.*
- **Improvement (non-blocking):** Plan file at `docs/superpowers/plans/2026-04-28-magic-system-coyote-reach-v1.md` should have its Phase 4 task checkboxes ticked to reflect the merged PR #183 — currently the plan body is misleading about completion state, which is what trapped the architect's audit. Affects `docs/superpowers/plans/2026-04-28-magic-system-coyote-reach-v1.md` (mark Tasks 4.1-4.3 done, leave 4.4-4.5 unchecked). *Found by TEA during test design.*

### Dev (verification)
- **Gap (non-blocking):** TS↔server type drift confirmed — `StatusPromotion` interface and `LedgerBarSpec.promote_to_status` field present on server (`models.py:114, :151`), absent from `src/types/magic.ts`. No Phase 4 impact (auto-promoted Statuses render via existing Status renderer, not LedgerPanel) but **HIGH risk for Phase 5**: confrontation `mandatory_outputs` like `status_add_wound`/`status_add_scar` will need this surface. Affects `sidequest-ui/src/types/magic.ts` (add `StatusPromotion` interface + optional field). *Found by Dev during verification.*
- **Improvement (non-blocking):** Worktree `npm install` works cleanly. 1 moderate npm audit vuln present in transitive deps (matches develop's lockfile, not introduced by this work). Worth a periodic `npm audit fix --force` evaluation in a dedicated chore. *Found by Dev during verification.*
- **Question (blocking for AC closure, NOT for code):** Manual smoke test (AC1-AC5) cannot be executed autonomously. Requires user-driven 10-turn Coyote Star session + GM dashboard observation. PR #183 merged ~5 days ago without the cut-point being closed. User must choose: (1) run smoke now, (2) defer to next playgroup with conditional pass + followup, or (3) use sq-playtest. See Dev Assessment for details. *Found by Dev during verification.*

### Reviewer (review)
- **Gap (blocking for SM finish):** Manual smoke gate (AC1-AC5) deferred per Option 2 (user choice). SM MUST file `47-1-followup` story in Epic 47 BEFORE running `pf sprint story finish 47-1` — without it, the conditional-pass becomes a silent skip. See Reviewer Assessment "Mandatory follow-ups #1". *Found by Reviewer during review.*
- **Conflict (blocking for Phase 5):** Dev's `StatusPromotion` drift finding will be silently orphaned unless 47-2's session-context brief explicitly references this session's drift table. SM must wire the prerequisite into 47-2 setup. See Reviewer Assessment "Mandatory follow-ups #2". *Found by Reviewer during review.*
- **Improvement (non-blocking, second concur):** Tooling chore for `pf hooks schema-validation` (missing `node_modules/yaml` at orchestrator root) — second confirmation across this story (SM also flagged). Cumulative friction across multiple agents this session. Bumping urgency: this is real workflow tax on every YAML edit. Worth filing a Pennyfarthing-side chore (NOT Epic 47 — different repo). *Found by Reviewer during review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

No deviations logged yet.