---
story_id: "61-18"
jira_key: ""
epic: "61"
workflow: "tdd"
---
# Story 61-18: Audit CONFRONTATION_TRIGGER_CONSTRAINT dead-prose on SDK narrator path

## Story Details
- **ID:** 61-18
- **Jira Key:** (none — Jira not configured)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-29T01:20:57Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-28T20:21:00Z | 2026-05-29T00:34:56Z | 4h 13m |
| red | 2026-05-29T00:34:56Z | 2026-05-29T00:48:42Z | 13m 46s |
| green | 2026-05-29T00:48:42Z | 2026-05-29T01:04:55Z | 16m 13s |
| spec-check | 2026-05-29T01:04:55Z | 2026-05-29T01:07:40Z | 2m 45s |
| verify | 2026-05-29T01:07:40Z | 2026-05-29T01:11:23Z | 3m 43s |
| review | 2026-05-29T01:11:23Z | 2026-05-29T01:19:53Z | 8m 30s |
| spec-reconcile | 2026-05-29T01:19:53Z | 2026-05-29T01:20:57Z | 1m 4s |
| finish | 2026-05-29T01:20:57Z | - | - |

## Story Description

Audit the CONFRONTATION_TRIGGER_CONSTRAINT guardrail prose in the narrator system. Investigation needed:

1. **Current behavior:** The constraint appears to only inject on the retired legacy narrator backend via `_maybe_register_legacy_guardrail`, and is SDK-gated to NOT fire on the anthropic_sdk path (which is the default SIDEQUEST_LLM_BACKEND per ADR-101).

2. **Problem:** This makes it dead prose on the live path — the SDK path narration never sees this constraint.

3. **Decision needed:** Either:
   - **Option A:** Migrate the constraint to tool-description / cached-prose per ADR-111 (Recency-Zone Narrator Guardrails)
   - **Option B:** Confirm that the Intent Router (ADR-113, epic 59) now owns confrontation triggering and the guardrail can be retired entirely

4. **Relevant context:**
   - ADR-111: Recency-Zone Narrator Guardrails → tool descriptions + cached output prose
   - ADR-113: Intent Router (mechanical-engagement spine)
   - ADR-116: Confrontation Requires an Other (participant membership invariant)
   - ADR-067: Unified Narrator Agent
   - ADR-101: Anthropic SDK as narrator backend (anthropic_sdk is the default production path)

## Delivery Findings

Starting investigation phase. No upstream findings yet.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (blocking): The A-vs-B ownership decision is NOT yet made — it is the story's core deliverable, and the SM assessment invited Architect (White Queen) input. My audit produced a strong, evidence-backed recommendation Dev should weigh (see TEA Assessment → Recommendation), but Dev should confirm the A-vs-B call before implementing. Affects `sidequest/agents/intent_router.py` (the `_SYSTEM_PROMPT` confrontation steering — Option B owner) and/or a confrontation/encounter tool `description` (Option A owner). *Found by TEA during test design.*
- **Gap** (non-blocking): The `generate_encounter` tool description is itself stale dead-prose — it reads "this subsystem is not wired — it returns a hard error. To START a confrontation, call begin_confrontation." but `begin_confrontation` was RETIRED in Story 59-4 (ADR-113). It points players/model at a tool that no longer exists. Adjacent to this story's theme but distinct from `CONFRONTATION_TRIGGER_CONSTRAINT`; I did NOT add a forcing RED test for it to avoid silently expanding scope. Affects `sidequest/agents/tools/generate_encounter.py` (rewrite or remove the description's stale `begin_confrontation` pointer). Recommend a follow-up story or fold into this one only with Architect sign-off. *Found by TEA during test design.*
- **Gap** (non-blocking): The other two Recency guardrails (`npc_intro_visual`, `npc_extraction`, `location_patch`) DID migrate (test_57_4 pins them), so this dead-prose risk is confrontation-only — but worth noting the migration was incomplete by exactly one guardrail and nobody caught it for ~3 stories. Affects nothing to change now; documents that the migration test's removal (test_57_4 line 337-340) silently dropped coverage. *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (non-blocking, for SM/develop health — NOT a 61-18 regression): The full server suite (`uv run pytest`) has ~22 pre-existing failures + 17 errors on the develop base, in subsystems unrelated to 61-18: `tests/server/test_reference_integration.py` (16 errors), `test_reference_poi_images.py`, `test_app.py`, `test_forensics_routes.py`, `test_lore_rag_wiring.py`, `test_chargen_complete_no_hp_leak.py`, `test_culture_context.py`, `test_scene_listing.py`, `tests/cli/validate/test_pack_validator*.py`, `tests/scripts/test_audit_namegen_corpora.py`. Confirmed pre-existing by stashing my changes and re-running (same failures). Likely DB/RAG/content-environment dependent. Affects `develop` CI health — recommend a separate triage/patch; 61-18's own + agents suites are fully green. *Found by Dev during implementation.*
- **Gap** (non-blocking): TEA's stale-`generate_encounter`-description finding stands unaddressed — per the Architect ruling it is out of scope for 61-18 (a separate dead-prose artifact). Affects `sidequest/agents/tools/generate_encounter.py`. Recommend a follow-up story. *Found by Dev during implementation (carried from TEA).*

### Reviewer (code review)
- **Improvement** (non-blocking): The two confrontation slices noted by Dev/TEA — (a) the ~22 pre-existing develop-suite failures and (b) the stale `generate_encounter` description — are both worth a single follow-up "confrontation/CI-health cleanup" story. Affects `develop` CI + `sidequest/agents/tools/generate_encounter.py`. Not blocking 61-18; the audit's confrontation slice is complete and correct. *Found by Reviewer during code review.*

## Design Deviations

### TEA (test design)
- **AC-2 literal "fire a real turn through the SDK path" replaced by a deterministic steering-presence guard + an engager-behavior test**
  - Spec source: context-story-61-18.md, AC-2
  - Spec text: "a test fires a real turn through the SDK path on a trigger-bearing action and asserts the confrontation is emitted (or the owning subsystem's OTEL span fires). The test must fail if confrontation triggering regresses to dead-prose. No source-text grep assertions."
  - Implementation: Two deterministic tests instead of one live-turn test. (1) `test_confrontation_{antidefer,social_trigger}_steering_reaches_a_live_sdk_surface` assert the load-bearing trigger-recognition fingerprints reach at least one runtime SDK surface (router `_SYSTEM_PROMPT` / any tool description / sidecar). (2) `test_router_dispatched_confrontation_actually_engages_encounter` drives the real `run_dispatch_bank` → `run_confrontation_dispatch` → `snapshot.encounter` and confirms the watcher sees no mismatch.
  - Rationale: A literal "fire a real turn through the SDK path on a trigger-bearing action" exercises the IntentRouter's Haiku classification *judgment* — which is the exact thing under audit and requires a live LLM call (non-deterministic, can't run in CI). With a faked LLM the dispatch is forced, so a behavior test can NEVER fail on dead-prose, violating AC-2's regression clause. The steering-presence test IS the faithful regression detector (dead-prose ⟺ steering absent ⟺ test red). The membership checks assert runtime prompt/description STRING VALUES (the artifacts sent to the model), not `.py` `read_text()` — so they honor "No source-text grep" (same accepted pattern as test_57_4's `test_apply_world_patch_tool_description_carries_location_guardrail` and test_confidence_gate's `test_router_prompt_instructs_per_dispatch_confidence`).
  - Severity: minor
  - Forward impact: Dev's fix must make the trigger-recognition steering reach a live SDK surface (ideally by referencing the single-source constant per ADR-111 §Implementation Notes). If Dev deliberately rephrases/compresses the fingerprints (rejected by ADR-111 §Alternatives B), the test fails by design — update the fingerprint constants in the test WITH Architect sign-off.
- **Stale `generate_encounter` description bug left as a finding, not a forcing test**
  - Spec source: context-story-61-18.md, Scope Boundaries (in scope: the `CONFRONTATION_TRIGGER_CONSTRAINT` slice + docstring; out of scope expansion)
  - Spec text: "In scope: ... Resolve to exactly one of (a)/(b) ... Update the `_maybe_register_legacy_guardrail` docstring."
  - Implementation: Recorded the stale `generate_encounter` → retired `begin_confrontation` description as a non-blocking delivery finding rather than a RED test that would force Dev to fix it.
  - Rationale: Adding a hard RED test forces the fix into scope before the A-vs-B decision is made; the disciplined call is to surface it loudly as a finding and let SM/Architect decide whether to fold it in.
  - Severity: minor
  - Forward impact: none unless Dev/Architect elects to fix it in this story.

### Dev (implementation)
- **Bundled an incidental fix unrelated to 61-18: the narrator tool-count assertion (28→29)**
  - Spec source: 61-18 story scope (the confrontation-trigger slice + docstring) — this change is OUTSIDE that scope.
  - Spec text: n/a — no 61-18 test required this change.
  - Implementation: Edited `tests/agents/test_narrator_uses_sdk_client.py` to bump the hardcoded `== 28` tool-count assertion to `== 29`, in a separate labeled commit (bdfd0f8).
  - Rationale: The assertion was failing on the develop base — CWN System Strain (#506, pulled at session start) added the `adjust_system_strain` narrator tool but did not update the count. The fix is trivial and correct (29 IS the registry count now), it sits in the agents suite (this story's primary domain), and leaving the agents suite red would fail the dev-exit gate. Kept in a separate commit so it does not muddy 61-18's design diff. The OTHER ~22 pre-existing full-suite failures are unrelated subsystems and were NOT touched (see Delivery Findings → Dev).
  - Severity: minor
  - Forward impact: none — purely brings a stale test in line with the current registry.

### Reviewer (audit)
- **TEA: AC-2 steering-presence guard + engager test in place of a literal live-turn test** → ✓ ACCEPTED by Reviewer: a literal "fire a real turn" needs a live LLM (the router's classification judgment is the thing under audit), so it can't be a deterministic CI test; the steering-presence assertion is the faithful "fails-on-dead-prose" regression detector, and the engager test covers the owning-subsystem-engages edge case. rule-checker independently confirmed these are runtime-value assertions, not source-text wiring tests.
- **TEA: stale `generate_encounter` description left as a finding, not a forcing test** → ✓ ACCEPTED by Reviewer: forcing it would expand scope before the A-vs-B decision; correctly surfaced as a finding and ratified out-of-scope by the Architect.
- **Dev: incidental tool-count fix (28→29) in a separate commit** → ✓ ACCEPTED by Reviewer: pre-existing #506 broken window in the agents suite (this story's domain), trivially correct (29 IS the registry count), isolated in its own commit and logged. The other ~22 develop failures were correctly left untouched (out of scope).
- No undocumented deviations found: the diff matches the logged deviations exactly; the `_SYSTEM_PROMPT` parenthesization was a ruff-format artifact (semantically identical), not an undocumented design change.

### Architect (reconcile)

**Existing-entry verification** (all entries audited against the real spec and the merged code):
- **TEA #1 (AC-2 steering-presence approach)** — VERIFIED accurate and complete. Spec source `context-story-61-18.md` AC-2 exists; the quoted spec text matches the file; the implementation description matches the merged tests; all 6 fields present. Forward impact is correct — the fingerprint coupling is the intended single-source guard. Sound.
- **TEA #2 (stale `generate_encounter` left as finding)** — VERIFIED accurate. Spec source (Scope Boundaries) is real; the out-of-scope classification is correct and I ratified it during the green-phase consult. 6 fields present.
- **Dev #1 (incidental tool-count fix 28→29)** — VERIFIED accurate. I independently confirmed `adjust_system_strain` entered at develop commit `0a7e030` (#506) and the assertion was stale on the base; the fix is correct (29 = current registry count) and isolated in commit `bdfd0f8`. 6 fields present.

**AC deferral check:** No ACs were deferred or descoped. All three are DONE — AC-1 (ground truth pinned by the steering tests), AC-2 (IntentRouter owner ratified + steering migrated + engager test), AC-3 (both docstrings reconciled in `sidequest-server`; the `docs/adr/DRIFT.md` / ADR-111 note completed by me during spec-check, committed to the orchestrator repo as `a67fb79`). No deferral table to reconcile.

**Missed deviations:** No additional deviations found. The merged implementation matches the ratified design (Option B-hybrid + framing-neutral core extraction, approach 2(a)) exactly; the only non-spec'd diffs are (a) the ruff-format parenthesization of `_SYSTEM_PROMPT` (semantically identical) and (b) the cross-repo DRIFT.md doc note (an AC-3 deliverable, not a deviation) — neither is a design departure.

— The White Queen

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

## Sm Assessment

**Story type:** Investigation-led audit with a fork in the road. This is *not* a feature build — it's "find the dead prose, then decide its fate." TEA should treat the RED phase as characterizing current behavior before any change.

**Scope (server-only):** All work is in `sidequest-server`. The locus is `_maybe_register_legacy_guardrail` and the `CONFRONTATION_TRIGGER_CONSTRAINT` prose. First job is to confirm the premise empirically: does the constraint actually fail to reach the `anthropic_sdk` narrator path? Don't trust the title — verify with a test.

**The decision is the deliverable.** The story explicitly allows two outcomes:
- **Option A** — migrate the constraint to tool-description / cached-prose per ADR-111.
- **Option B** — confirm the Intent Router (ADR-113, epic 59) now owns confrontation triggering and retire the guardrail as genuinely dead code.

Per "No Stubbing / Dead code is worse than no code," if Option B holds, deletion is a valid and preferred outcome. Do not leave the legacy guardrail as an inert shell.

**Acceptance criteria (for TEA to sharpen into tests):**
1. A characterization test proves whether `CONFRONTATION_TRIGGER_CONSTRAINT` reaches the SDK narrator path today (expected: it does not).
2. The chosen option is implemented end-to-end and *wired* — if Option A, a test proves the constraint is present on the live SDK path (tool description or cached prose); if Option B, the legacy guardrail and its prose are removed and a test proves the Intent Router covers confrontation triggering.
3. Per project OTEL principle: if the confrontation-trigger decision is a subsystem decision on the live path, it emits an OTEL watcher event so the GM panel can verify engagement. TEA to confirm whether this is in-scope or already covered by epic 59's router spans.
4. No silent fallback introduced; the SDK path is the only default backend and must be the path under test.

**Routing:** Phased tdd → next agent is **tea** (The Caterpillar) for the RED phase. Architect input may be warranted on the A-vs-B call — TEA/Dev should escalate to the White Queen if the ownership boundary between this guardrail and the Intent Router is unclear.

— The Mad Hatter

---
## TEA Assessment

**Tests Required:** Yes
**Reason:** Audit story with a behavioral deliverable (steering must reach the model on the SDK path).

**Test Files:**
- `sidequest-server/tests/agents/test_61_18_confrontation_trigger_sdk_path.py` — confrontation-trigger steering presence on the SDK path + engager engagement.

**Tests Written:** 4 tests covering AC-1 (ground truth) and AC-2 (owner resolution + engager behavior).
**Status:** RED (2 failing assertions ready for Dev; 2 passing guards).

| Test | Role | Status |
|------|------|--------|
| `test_antidefer_fingerprint_is_pinned_in_the_source_constant` | guard (fingerprint is genuinely the constant's text) | PASS |
| `test_confrontation_antidefer_steering_reaches_a_live_sdk_surface` | RED driver — anti-deferral trigger rule reaches no live SDK surface | **FAIL (red)** |
| `test_confrontation_social_trigger_steering_reaches_a_live_sdk_surface` | RED driver — social-pack trigger steering reaches no live SDK surface | **FAIL (red)** |
| `test_router_dispatched_confrontation_actually_engages_encounter` | engager regression guard (AC-2 edge case: owner ACTUALLY engages) | PASS |

Verified via `uv run pytest tests/agents/test_61_18_confrontation_trigger_sdk_path.py -v -n0`: 2 passed, 2 failed (assertion failures, **not** import/collection errors). 31 SDK surfaces searched (router `_SYSTEM_PROMPT`, sidecar, 29 tool descriptions) — the fingerprints are present in none.

### Ground truth (AC-1) — what the audit found

`CONFRONTATION_TRIGGER_CONSTRAINT` reaches the model on the SDK path through **zero** live channels:
- **Suppressed** in `build_narrator_prompt` (gated to legacy-only via `_maybe_register_legacy_guardrail`; the SDK client is a `ToolingLlmClient`). Already pinned by `test_57_4`.
- **Not migrated** to any SDK surface: absent from `intent_router._SYSTEM_PROMPT`, every registered tool `description`, and `NARRATOR_OUTPUT_ONLY`.
- The migration test for it was **removed** — `test_57_4` line 337-340 dropped `test_confrontation_guardrail_migrates_into_an_encounter_tool` when `begin_confrontation` was retired in 59-4, asserting "confrontation engagement is now router-driven" without re-verifying the router carries the *steering*.
- The IntentRouter `_SYSTEM_PROMPT` DOES name `confrontation` as a subsystem and gives generic category guidance ("a parley → a social-category type"), but **none** of the concrete beat→fire trigger-recognition steering the dead prose carried (the very fingerprints ADR-111 §Alternatives B preserved as regression detectors).

Conclusion: Option B (IntentRouter owns confrontation triggering) is **structurally real** — the dispatch handler (`run_confrontation_dispatch`), engager (`instantiate_encounter_from_trigger`), and lie-detector watcher are all wired by 59-4, and the engager test proves they engage. But the **trigger-recognition steering was lost, not migrated.** The 2026-05-03 bug class (prose describes an engagement; no confrontation fires) is now the *router's* exposure, with weaker steering than before.

### Recommendation for Dev (the A-vs-B call — confirm with Architect)

**Option B-hybrid** is the evidence-backed path: confirm the IntentRouter owns confrontation triggering on the SDK path, and **migrate the rich trigger-recognition fingerprints from `CONFRONTATION_TRIGGER_CONSTRAINT` into the router's confrontation steering** (the `confrontation:` bullet in `intent_router._SYSTEM_PROMPT`), referencing the single-source constant per ADR-111 §Implementation Notes (no inline duplication). Then reconcile the `_maybe_register_legacy_guardrail` and `narrator_guardrails` module docstrings to state the truth (AC-3), and update `docs/adr/DRIFT.md` / ADR-111 to record that the confrontation slice was resolved independently of the (still-deferred) broader migration. The two RED tests pass when the fingerprints reach a live surface. **This is a recommendation, not a mandate** — the A-vs-B decision is genuinely open; escalate to the White Queen (Architect) if the ownership boundary is unclear (per SM assessment).

### Rule Coverage

| Rule (server CLAUDE.md) | Test(s) | Status |
|------|---------|--------|
| No Source-Text Wiring Tests | steering checks assert runtime prompt/description string VALUES (not `read_text()`), per the accepted prompt-vocabulary pattern | satisfied |
| No Silent Fallbacks | `test_router_dispatched_confrontation_actually_engages_encounter` asserts a real encounter lands (no quiet no-op) | passing |
| Every Test Suite Needs a Wiring Test | engager test drives real `run_dispatch_bank` → `run_confrontation_dispatch` → `snapshot.encounter` end-to-end | passing |
| OTEL is the lie-detector | engager test asserts `detect_dispatch_engagement_mismatch` reports no confrontation mismatch | passing |

**Rules checked:** 4 of 4 applicable.
**Self-check:** 0 vacuous tests — every test has a meaningful, value-bearing assertion; the two guards (fingerprint-in-constant, engager-engages) protect the RED drivers from silent rot.

**Handoff:** To Dev (The White Rabbit) for the GREEN phase — make the steering reach a live SDK surface (recommended: Option B-hybrid above), reconcile the docstrings (AC-3), and confirm the A-vs-B call with the Architect if needed.

— The Caterpillar

---
## Dev Assessment

**Implementation Complete:** Yes
**Architect consult:** Honored TEA's blocking finding — consulted the White Queen before implementing. She concurred with **Option B-hybrid + approach 2(a)** (extract a framing-neutral core, compose into the router, keep the legacy constant rebuilt from the core, reconcile docstrings, leave the stale `generate_encounter` description as an out-of-scope finding). Implemented exactly as ruled.

**Files Changed:**
- `sidequest/agents/narrator_guardrails.py` — extracted `CONFRONTATION_TRIGGER_CORE` (the framing-neutral trigger-recognition body, single source of truth, carries both regression fingerprints); recomposed `CONFRONTATION_TRIGGER_CONSTRAINT` = xml_open + narrator game_patch opening + CORE + narrator beat_selections tail + xml_close, **byte-identical** to the prior value (verified: 2543 == 2543 chars); rewrote the module docstring to state the true per-guardrail SDK-path homes (AC-3).
- `sidequest/agents/intent_router.py` — imported `CONFRONTATION_TRIGGER_CORE`; composed it into the `confrontation:` bullet of `_SYSTEM_PROMPT` under the router's DispatchPackage framing (concatenation, not f-string, to avoid the prompt's literal `{...}` braces). Both fingerprints now reach the live router prompt.
- `sidequest/agents/orchestrator.py` — reconciled the `_maybe_register_legacy_guardrail` docstring (AC-3): documents the true per-guardrail SDK homes and corrects the prior implication that the confrontation guardrail rode a tool description (it reached nothing — dead prose — until this story).
- `tests/agents/test_narrator_uses_sdk_client.py` — incidental: tool-count assertion 28→29 (pre-existing #506 breakage; separate commit; see Design Deviations → Dev).

**How each AC was met:**
- **AC-1 (ground truth):** established in RED; the audit confirmed the steering reached zero live SDK surfaces. Pinned by the now-passing steering-presence tests.
- **AC-2 (owner resolved with a test):** IntentRouter confirmed as the SDK-path owner (Architect-ratified); the two steering-presence tests now pass (fingerprints reach the router `_SYSTEM_PROMPT`), and the engager-behavior test proves the owner actually engages.
- **AC-3 (docstring/ADR reconciled):** both the module docstring and `_maybe_register_legacy_guardrail` docstring corrected. *Note for spec-check:* I did NOT yet update `docs/adr/DRIFT.md` / ADR-111 (those live in the orchestrator repo, not sidequest-server). Flagging for the Architect spec-check phase to decide whether the DRIFT.md note belongs in this story's scope or a doc follow-up.

**Single-source-of-truth (ADR-111 §Implementation Notes):** honored — one `CONFRONTATION_TRIGGER_CORE`, consumed by both the router (dispatch framing) and the legacy narrator constant (game_patch framing). No prose duplication.

**Tests:**
- Story 61-18 tests: **4/4 passing (GREEN).**
- Targeted regression suites (test_57_4, test_intent_router, test_confidence_gate, test_localdm_wiring, test_orchestrator): **142/142 passing.**
- Full agents suite: **1137 passed, 0 failed.**
- Full server suite (`uv run pytest`): 22 failed + 17 errors — **all pre-existing on develop, none in my changed modules** (confirmed by stashing my changes and reproducing the identical failures). Logged as a non-blocking Delivery Finding for develop CI triage. The one agents-suite failure I DID fix (tool-count) was a #506 broken window.

**Branch:** `feat/61-18-confrontation-trigger-constraint-sdk-audit` (pushed). Commits: db2f3b9 (RED tests, TEA), 1c0ed2f (feat impl), bdfd0f8 (incidental tool-count fix).

**Handoff:** To the Architect (White Queen) for the **spec-check** phase. Two items for her attention: (1) confirm the `docs/adr/DRIFT.md` / ADR-111 note is in-scope here or a doc follow-up; (2) the pre-existing develop suite failures + the stale `generate_encounter` description are flagged as out-of-scope findings.

— The White Rabbit

---
## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (after I completed AC-3's DRIFT.md note in this phase — see below).
**Mismatches Found:** 1 (resolved in-phase), plus 2 correctly-scoped out-of-scope findings (no action).
**Prior involvement:** I was consulted during the green phase and ratified Option B-hybrid + approach 2(a). The implementation matches that ruling exactly (verified the diff: `CONFRONTATION_TRIGGER_CORE` extracted, composed into `intent_router._SYSTEM_PROMPT`, legacy constant byte-identical at 2543 chars, both docstrings reconciled).

**AC-by-AC:**
- **AC-1 (ground truth established).** Aligned. The RED-phase audit empirically confirmed the steering reached zero live SDK surfaces; the now-green steering-presence tests pin it. Evidence is the assembled prompt/registry values, not inference — satisfies the AC's "evidence is the actual assembled prompt / tool array."
- **AC-2 (owner resolved with a test).** Aligned. The IntentRouter is the correct SDK-path owner (the narrator no longer emits the `confrontation` patch field; the router decides pre-narrator per ADR-113). The steering migrated into the router prompt; the two steering-presence tests pass and fail-on-dead-prose; the engager-behavior test proves the owner *actually* engages (the AC edge case), not merely that a handler is registered. No source-text grep (runtime string-value assertions, accepted pattern).
- **AC-3 (docstring/ADR reconciled).** Initially a partial mismatch (Missing in code — Cosmetic/doc, Minor): Dev reconciled both docstrings but correctly deferred the `docs/adr/DRIFT.md` / ADR-111 note to me (orchestrator-repo doc artifact, architect domain). **Resolution: Option A/authored-in-phase** — I added the note to the ADR-111 DRIFT.md row recording that the confrontation slice was resolved independently by 61-18 while the broader ADR-111 migration stays deferred. AC-3 now fully satisfied.

**Out-of-scope items (no action — correctly classified by Dev/TEA):**
- **Incidental tool-count fix (Extra in code — Trivial).** `test_narrator_uses_sdk_client.py` 28→29. A pre-existing #506 broken window, in a separate labeled commit, properly logged as a deviation. **Recommendation: A (accept)** — correct, isolated, keeps the agents suite green. Not 61-18 design.
- **Pre-existing develop suite failures (~22 + 17 errors).** Confirmed pre-existing by Dev's stash reproduction; unrelated subsystems (reference/RAG/forensics/content/DB). **Recommendation: D (defer)** to a develop CI-health triage — out of 61-18 scope.
- **Stale `generate_encounter` description → retired `begin_confrontation`.** A distinct dead-prose artifact. **Recommendation: D (defer)** to a follow-up story — I ruled it out of scope during the green-phase consult.

**Architectural soundness:** The single-source-of-truth extraction (`CONFRONTATION_TRIGGER_CORE`) is the right reuse-first move — no new component, no prose duplication (ADR-111 §Implementation Notes), and it correctly places the trigger-recognition steering where the decision is actually made (the router, ADR-113) rather than on a post-decision narrator/tool surface. The byte-identical legacy constant preserves the opt-in `claude -p`/Ollama path. No coupling concerns.

**Decision:** Proceed to verify (TEA). No hand-back required.

— The White Queen

---
## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 5 (narrator_guardrails.py, intent_router.py, orchestrator.py, test_61_18_…py, test_narrator_uses_sdk_client.py)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 1 finding | LOW: `_combat_pack()` test helper mirrors `synthetic_two_dial_pack` (tests/server/conftest.py) — intentional cross-dir isolation; teammate itself rated it defensible. |
| simplify-quality | 5 findings | 4 LOW (concatenation style, constant naming, fingerprint-constant naming, tool-count comment maintenance) + 1 MEDIUM (intent_router.py:129 comment "shared verbatim" could be read as byte-for-byte rather than core-shared-under-framing). |
| simplify-efficiency | clean | 0 findings — explicitly checked and dismissed over-engineering in the test scaffolding and constant extraction. |

**Applied:** 0 high-confidence fixes (there were none).
**Flagged for Review:** 1 medium — `intent_router.py:129` comment wording. Assessed and **dismissed**: the CORE text *is* shared verbatim (identical bytes in both consumers); only the surrounding opening/tail framing differs, which the comment already says ("…with the narrator's game_patch steering"). The phrasing is accurate; rewording is optional polish, not a correctness issue. Left as-is.
**Noted:** 6 low — all either working-as-designed (single-source two-framing per ADR-111; intentional test isolation) or stylistic preference. None worth a churn on a prose/docstring change.
**Reverted:** 0.

**Overall:** simplify: clean (no high-confidence findings; the lone medium dismissed on the merits).

### Quality Checks
- `ruff check` (all 5 changed files): **All checks passed.**
- `pyright` (changed source — narrator_guardrails.py, intent_router.py): **0 errors, 0 warnings.**
- Agents suite (covers all changed source): **1137 passed, 0 failed** (unchanged from green; verify applied no edits).
- Story 61-18 tests: **4/4 green.**
- Note: the full server suite's ~22 pre-existing failures + 17 errors are unrelated to 61-18 (confirmed pre-existing via Dev's stash reproduction) — see Delivery Findings → Dev. Not gating this story.

**Handoff:** To Reviewer (The Queen of Hearts) for code review.

— The Caterpillar

---
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 smells; GREEN | N/A — tests/lint/types all green |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings (workflow.reviewer_subagents.edge_hunter=false) |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings — reviewer assessed test quality directly (see [TEST]) |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings — reviewer assessed docstrings directly (see [DOC]) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings — no type changes in diff |
| 7 | reviewer-security | Yes | clean | none | N/A — prose-only; ADR-047 boundary untouched, no secrets |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings — verify-phase simplify fan-out already ran clean |
| 9 | reviewer-rule-checker | Yes | clean | 0 violations / 8 rules / 34 instances | N/A — all rules compliant |

**All received:** Yes (3 enabled subagents returned; 6 disabled via settings, pre-filled as Skipped)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred (all enabled subagents clean)

---
## Reviewer Assessment

**Verdict:** APPROVED

**Summary:** A clean, well-scoped audit resolution. The dead-prose gap is real (the confrontation guardrail reached zero live SDK surfaces) and the fix is the minimal, reuse-first move: extract a framing-neutral `CONFRONTATION_TRIGGER_CORE`, compose it into the SDK-path owner (IntentRouter, ADR-113), keep the legacy constant byte-identical. All three enabled subagents returned clean; my independent read agrees.

**Data flow traced:** player action → `IntentRouter.decompose()` builds the system message from `_SYSTEM_PROMPT` (now carrying `CONFRONTATION_TRIGGER_CORE`) → `emit_tool(system=_SYSTEM_PROMPT, …)` (intent_router.py:229, the live SDK call) → Haiku emits a `DispatchPackage` → `run_dispatch_bank` → `run_confrontation_dispatch` → `instantiate_encounter_from_trigger` → `snapshot.encounter` → narrator narrates already-real engagement. The change strengthens steering at the first hop; prose-only, no control-flow change. Safe.

**Observations (≥5):**
- `[VERIFIED]` Legacy constant byte-identical after recomposition — narrator_guardrails.py:143-151 composes `"…TYPES. " + CONFRONTATION_TRIGGER_CORE + "Only emit …"`; runtime check 2543==2543 chars. Complies with ADR-111 §Decision (legacy path byte-identical). Corroborated by rule-checker #1/#8 and test_57_4 still green.
- `[VERIFIED]` Single source of truth — `CONFRONTATION_TRIGGER_CORE` defined once (narrator_guardrails.py:127); consumed by intent_router.py:35 (import+compose) and the legacy constant (line 148). Grep for the fingerprints finds them only in narrator_guardrails.py. Complies with ADR-111 §Implementation Notes. `[RULE]` rule-checker #8 confirms 0 duplication across 5 instances.
- `[VERIFIED]` CORE is genuinely framing-neutral — the narrator-specific clauses (`your game_patch MUST populate`, `use beat_selections`) stayed in the legacy CONSTRAINT's opening/tail (lines 144-150), NOT in CORE. So composing CORE into the router prompt introduces no `game_patch` leakage. Verified by reading the diff boundaries.
- `[TEST]` (test-analyzer disabled — assessed directly) The 4 tests are non-vacuous and well-targeted: 2 steering-presence value assertions (fail-on-dead-prose), 1 fingerprint-in-constant guard (protects the other two from silent rot), 1 real engager wiring test (`run_dispatch_bank` → `snapshot.encounter`, asserts type + watcher no-mismatch). `[RULE]` rule-checker #5 confirms the engager test is a genuine integration wiring test.
- `[RULE]` (rule-checker) "No Source-Text Wiring Tests" (#6) — the steering-presence tests assert membership in runtime `str` constants/registry values (`_SYSTEM_PROMPT`, `NARRATOR_OUTPUT_ONLY`, `td.description`), not `read_text()` of a `.py` file. Sanctioned prompt-vocabulary pattern, structurally identical to test_57_4 / test_confidence_gate. Compliant.
- `[SEC]` (security) Prose-only change; `_build_user_prompt` sanitization boundary (ADR-047) untouched; no user input reaches the static constants; no secrets. Clean.
- `[DOC]` (comment-analyzer disabled — assessed directly) Both reconciled docstrings (narrator_guardrails module + `_maybe_register_legacy_guardrail`) are accurate and correct the prior stale claim that the confrontation guardrail rode a tool description. No misleading comments introduced.
- `[VERIFIED]` OTEL principle — no new subsystem decision is introduced (prompt-prose steering); the confrontation engagement path already emits `intent_router.decompose` / `intent_router.subsystem` / `dispatch_engagement.*` spans. No new span required (CLAUDE.md exempts prose/cosmetic changes). `[RULE]` rule-checker #7 agrees.
- `[EDGE]`/`[SILENT]`/`[TYPE]`/`[SIMPLE]` — subagents disabled via settings. Direct assessment: no new branches/edges (prose composition), no error handling added or swallowed (No Silent Fallbacks intact — rule-checker #1), no type changes, and the verify-phase simplify fan-out already returned clean with 0 high-confidence findings.

### Rule Compliance
Enumerated against the server/orchestrator CLAUDE.md + SOUL.md + ADR-111 rules (no lang-review checklist exists for this project). All compliant — confirmed independently and by `[RULE]` rule-checker (8 rules / 34 instances / 0 violations): No Silent Fallbacks ✓, No Stubbing ✓, Don't Reinvent (CORE extracted from existing constant, imported not copied) ✓, Verify Wiring (CORE flows into the live `emit_tool` call; legacy CONSTRAINT still in `ALL_GUARDRAILS`) ✓, Every Test Suite Needs a Wiring Test ✓, No Source-Text Wiring Tests ✓, OTEL ✓, Single Source of Truth ✓.

### Devil's Advocate
Could this break? I pressed on four fronts. (1) *Prompt bloat / over-firing:* the CORE tells the router to "fire THIS turn" on any stake-binding beat — could it over-trigger confrontations? No: the 71-16 confidence gate still degrades low-confidence dispatches to narrator hints, and the CORE explicitly constrains type choice to `game_state.confrontation_types`, so it cannot invent types. The aggressiveness is the intended fix for the 2026-05-03 under-firing bug, bounded by the gate. (2) *Framing leak:* could narrator-only language ("your game_patch") confuse the router? No — verified those clauses live in the legacy CONSTRAINT's opening/tail, not in CORE; the router bridge sentence reframes for the dispatch contract. (3) *Byte drift on the legacy path:* could the recomposition subtly change the legacy prose and silently alter `claude -p` behavior? No — runtime equality check (2543==2543) and test_57_4's fingerprint + suppression tests both still pass. (4) *The composed prompt's indentation is inconsistent* (CORE is unindented inside an indented bullet) — cosmetic only; LLMs are whitespace-tolerant and it does not affect token semantics. Nothing rose to a finding. The one residual risk is qualitative: whether Haiku actually *acts* on the richer steering — but that is a live-playtest validation question (epic 59 / playtest), explicitly out of this audit's deterministic-test scope and noted as such.

**Error handling:** No new error paths; the router's fail-loud `IntentRouterFailure` policy (intent_router.py:296-298) is untouched.
**Pattern observed:** single-source-constant extraction with two framings — narrator_guardrails.py:127 (CORE) consumed by both legacy CONSTRAINT and router prompt. Sound, refactor-stable.

**Handoff:** To SM (The Mad Hatter) for finish-story.

— The Queen of Hearts