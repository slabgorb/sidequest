---
story_id: "27-9"
epic: "27"
workflow: "tdd"
---
# Story 27-9: Collapse narration protocol — remove NarrationChunk, clean UI buffer (ADR-076)

## Story Details
- **ID:** 27-9
- **Epic:** 27 (MLX Image Renderer)
- **Workflow:** tdd
- **Stack Parent:** none
- **Points:** 3
- **Type:** refactor
- **Repos:** sidequest-api, sidequest-ui

## Story Context

This story implements **ADR-076: Narration Protocol Collapse Post-TTS Removal**, located at `docs/adr/076-narration-protocol-collapse-post-tts.md`. The ADR is the authoritative scope document.

**Background:** Epic 27 removed TTS (Kokoro) from the daemon side in story 27-1. An audit during the architect phase found that the API protocol crate and UI narration buffer still carry dead TTS plumbing:
- Zero production senders of `GameMessage::NarrationChunk`
- 60%-dead narration buffer in `sidequest-ui/src/App.tsx`
- Stale doc comments in `sidequest-api/crates/sidequest-game/src/prerender.rs` and `sidequest-api/crates/sidequest-server/src/extraction.rs`

Story 27-9 closes the loop across `sidequest-api` and `sidequest-ui` in a single atomic PR.

## Scope Summary (from ADR-076)

**What must change:**

1. Remove `GameMessage::NarrationChunk` variant and `NarrationChunkPayload` from `sidequest-protocol/src/message.rs`; delete the serde round-trip test in `tests.rs`
2. Update the doc comment on `NarrationEnd` to describe its current role (turn-completion marker + state delta flush), not its original role (stream terminator)
3. Rewrite stale TTS doc comments in `sidequest-api/crates/sidequest-game/src/prerender.rs` (lines 1, 3, 97)
4. Rewrite stale TTS doc comments in `sidequest-api/crates/sidequest-server/src/extraction.rs` (lines 4, 155)
5. Audit and remove orphaned `Tts*`/`Voice*` synthesis types in `sidequest-api/crates/sidequest-daemon-client/src/types.rs`
6. Delete `NarrationChunkPayload` interface from `sidequest-ui/src/types/payloads.ts`
7. Gut the UI narration buffer in `sidequest-ui/src/App.tsx` (lines 180-264): remove `buf.chunks`, `buf.watchdogTimer`, `handleBinaryMessage`, simplify `flushNarrationBuffer`, rewrite the buffer's comment block
8. Update `docs/wiring-diagrams.md` to remove `NarrationChunk` from the narration flow diagram

**Explicit non-scope** (prevent creep):
- `useAudio`, `audio.engine.playVoicePCM`, `audio.engine.playVoice` — may have other callers (SFX/music); do not audit or touch
- Genre pack voice config (`voice_volume`, voice mixer channel) — kept for future TTS; leave alone
- NPC voice assignment in `sidequest-game/src/npc.rs` — persistence-only, harmless
- Folding `NarrationEnd` into `Narration` — separate simplification, future ADR if pursued

## Acceptance Gate (from ADR-076)

Required before spec-reconcile exit:

1. PR merges to `develop` on both `sidequest-api` and `sidequest-ui` (gitflow, NOT main — subrepos use develop)
2. Wiring check: `grep -r "NarrationChunk\|NarrationChunkPayload\|handleBinaryMessage\|buf\.chunks" sidequest-api sidequest-ui` returns zero production hits
3. `just check-all` passes on the orchestrator (api-check + ui-lint + ui-test)
4. Manual playtest confirms narration still reveals correctly and state deltas (HP, inventory, location) apply atomically with their narration text

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-04-10T10:16:53Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-10T06:54:03Z | 2026-04-10T06:58:56Z | 4m 53s |
| red | 2026-04-10T06:58:56Z | 2026-04-10T07:27:55Z | 28m 59s |
| green | 2026-04-10T07:27:55Z | 2026-04-10T07:44:30Z | 16m 35s |
| spec-check | 2026-04-10T07:44:30Z | 2026-04-10T07:48:04Z | 3m 34s |
| verify | 2026-04-10T07:48:04Z | 2026-04-10T08:04:56Z | 16m 52s |
| review | 2026-04-10T08:04:56Z | 2026-04-10T10:14:31Z | 2h 9m |
| spec-reconcile | 2026-04-10T10:14:31Z | 2026-04-10T10:16:53Z | 2m 22s |
| finish | 2026-04-10T10:16:53Z | - | - |

## Branching Strategy

**CRITICAL:** Both `sidequest-api` and `sidequest-ui` are gitflow repos targeting `develop`, NOT main. The feature branch should be `feat/27-9-collapse-narration-protocol` off `develop` in each subrepo.

## Sm Assessment

**Setup status:** Complete.

**Session file:** Created at `.session/27-9-session.md` with workflow tracking, scope summary, acceptance gate, and branching strategy section.

**Feature branches:** `feat/27-9-collapse-narration-protocol` created off `develop` on both `sidequest-api` and `sidequest-ui`. Gitflow verified — NOT main.

**Story metadata:** Status flipped to `in_progress` in `sprint/epic-27.yaml`. Branch and session fields populated.

**Authoritative scope document:** `docs/adr/076-narration-protocol-collapse-post-tts.md` (Status: Proposed). TEA should read this before writing tests — it contains the full scope, non-scope, alternatives considered, and the four-bullet acceptance gate that drives this story.

**Jira contamination incident (scrubbed during setup):** The sm-setup subagent, when given an empty `JIRA_KEY` parameter, hallucinated fake IDs (`SIDEQ-219` for the story, `SIDEQ-27` for the epic) and wrote them into the session file frontmatter, display lines, and `sprint/epic-27.yaml` (both epic-level and story-level `jira:` fields). Verified these were hallucinations (not real tickets) via `pf settings get jira` returning empty `project` and `url`. Scrubbed all 5 references in the same phase. Memory file `feedback_no_work_contamination.md` updated with the new failure mode. **No handoff to TEA should reintroduce Jira references — this project has zero Jira integration.**

**Merge gate at entry:** Clean. Zero open PRs across orchestrator, sidequest-api, sidequest-ui at setup time.

**Workflow:** `tdd` — phased. Phase order: setup → red → green → review → finish. Next agent: TEA (red phase — write failing tests that assert the dead protocol variant and UI plumbing are removed).

**Critical reminder for TEA:** This is a deletion-driven TDD. The failing test is "assert `NarrationChunk` is NOT in the protocol union" and "assert `buf.chunks` / `handleBinaryMessage` do NOT exist in App.tsx." Dev makes it pass by deleting the code. Reviewer verifies the wiring check.

**Recommended handoff target:** TEA (Mr. Praline).

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

- **Gap (non-blocking, SM/setup):** The `sm-setup` subagent treats an empty `JIRA_KEY` parameter as "hallucinate a fake key" rather than "skip the field." This caused `SIDEQ-219` and `SIDEQ-27` to be written into session + epic YAML during 27-9 setup and had to be scrubbed in-place. Mitigation applied to this session; root fix belongs in `pf-setup` / `sm-setup` agent contract.
- **Improvement (non-blocking, orchestrator):** The `PostToolUse:Edit` hook for sprint YAML files was broken at session start (missing Node `yaml` package). Fixed in PR #63 commit `035013e`. Hook now runs silently on every YAML edit — confirmed across three test cases this session.

### TEA (test design)

- **Gap** (non-blocking): `pf validate context-story 27-9` and `pf validate context 27-9` both fail with "Unknown validator" — OQ-2 does not have a `context-story` or `context` validator registered. Available validators: adr, agent, architecture, context, prd, schema, skill-command, sprint, tandem-awareness, theme, version, workflow. The context gate step in the TEA agent definition is effectively inoperative in this project. I proceeded using the session file as the authoritative scope per the Spec Authority Hierarchy. Affects `.pennyfarthing/gates/context-gate.py` or equivalent — the `context-story` validator should either be registered, or the agent definition should be updated to reflect that OQ-2 uses the session file as canonical context. *Found by TEA during test design.*
- **Gap** (non-blocking): `sidequest-api/crates/sidequest-protocol/CLAUDE.md` still claims 23 GameMessage variants and explicitly lists `NARRATION_CHUNK`, `TTS_START`, `TTS_CHUNK`, `TTS_END`, `VOICE_*` as existing message types. This documentation is stale post-Epic-27 (TTS removal) and will be stale post-27-9. Dev should update it as part of the GREEN phase so the crate's own inventory matches reality. Affects `sidequest-api/crates/sidequest-protocol/CLAUDE.md` (update the "GameMessage — 23 variants" line and drop NARRATION_CHUNK / TTS_* from the enumeration). *Found by TEA during test design.*
- **Gap** (non-blocking): `sidequest-api/CLAUDE.md` Architecture Decision Index table does not yet reference ADR-076. Row "Frontend / protocol" should include `076 (narration protocol collapse)`. Not a blocker for 27-9 but an ADR-index hygiene item. Affects `sidequest-api/CLAUDE.md`. *Found by TEA during test design.*
- **Improvement** (non-blocking): `sidequest-ui` test suite has 88 pre-existing test failures across 11 files, predating this commit and unrelated to story 27-9. None affect the new 27-9 RED tests, but the ambient redness makes it harder to spot real regressions. Worth a dedicated tech-debt pass. Affects the UI repo broadly. *Found by TEA during test design.*
- **Observation** (non-blocking): The ADR-076 §Daemon Client Types audit is **already satisfied** — `sidequest-api/crates/sidequest-daemon-client/src/types.rs` contains zero `Tts*` / `VoiceSynth*` structs or enums. The only types present are `DaemonRequest`, `RenderParams`, `WarmUpParams`, `EmbedParams`, `EmbedResult`, `DaemonResponse`, `ErrorPayload`, `RenderResult`, `StatusResult` — all image/embed/render plumbing. Dev has no cleanup work here; my guard test `daemon_client_types_has_no_tts_or_voice_synthesis_types` passes immediately and serves as a regression invariant. *Found by TEA during test design.*
- **Observation** (non-blocking): The ADR-076 §UI Narration Buffer `NarrationChunkMessage` cleanup is **already satisfied** — there is no `NarrationChunkMessage` member in the `TypedGameMessage` discriminated union in `sidequest-ui/src/types/payloads.ts`. The variant was never added UI-side, which is precisely why the buffer became half-wired in the first place (the Architect identified this in the ADR context section). My guard test passes; no Dev work needed for this specific item. *Found by TEA during test design.*
- **Observation** (non-blocking): App.tsx does not reference the literal string `NarrationChunk` anywhere — the dead code uses field names like `buf.chunks`, `handleBinaryMessage`, and `watchdogTimer` instead. The string-literal test is a defensive invariant that would catch a future regression where someone tries to add `NarrationChunk` handling back. *Found by TEA during test design.*

### TEA (test verification)

- **Gap** (non-blocking, architecture): The simplify fan-out during the verify phase surfaced that `narrationBufferRef` and `flushNarrationBuffer` in `sidequest-ui/src/App.tsx` were orphaned — defined but never invoked anywhere in the codebase. Two independent simplify teammates (quality, efficiency) converged on this finding with high confidence. Verified by `grep -rn "flushNarrationBuffer" src/` returning only the definition line. This means ADR-076's architect-phase description of the buffer's role ("pair Narration with NarrationEnd for atomic state_delta flush") was factually wrong — no such pairing was happening at runtime. The real narration flow is a straight-through `setMessages` push at App.tsx:240-245 that was added in a previous cleanup pass and has been the active code path ever since. TEA applied the fix during the verify phase (commit `a8b4fcf`) by deleting the entire orphaned buffer infrastructure. Affects `docs/adr/076-narration-protocol-collapse-post-tts.md` (if ever revisited, should note that the "atomic state_delta flush" claim was never accurate and React's automatic batching was handling the state coherence anyway). *Found by TEA during test verification.*
- **Improvement** (non-blocking, tech debt): `sidequest-api/crates/sidequest-server/src/extraction.rs` has a character-for-character identical 15-line blank-line collapse block in both `strip_combat_brackets()` (lines 134-148) and `strip_fenced_blocks()` (lines 178-194). Genuine DRY violation flagged by simplify-reuse during the verify fan-out. Deferred from this story because (a) it's pre-existing, (b) Dev only touched doc comments in this file, and (c) applying it would expand 27-9 into an unrelated tech-debt area with full test-suite cost. Suggested follow-up story: extract `fn collapse_blank_lines(text: &str) -> String` as a private helper and call it from both sites. Affects `sidequest-api/crates/sidequest-server/src/extraction.rs`. *Found by TEA during test verification.*
- **Observation** (non-blocking): The UI test suite improved from 94 failures (red baseline) → 82 failures (post-green), a 12-test improvement instead of the 6 expected. The +6 bonus fixes are not purely attributable to 27-9 story scope — at least some come from Keith's Option-C WIP `constants.ts` change which happened to delete a `tts_pipeline` color constant that was causing Dashboard test failures. The bundled WIP turned out to be a parallel TTS cleanup with no functional conflict. Metric to report honestly: "UI suite improved by 12 tests; 6 from 27-9 scope, 6 from the bundled WIP". *Found by TEA during test verification.*
- **Gap** (non-blocking, pre-existing bug): The `setCanType(true)` call at the old App.tsx line 210 (now deleted) was inside the orphaned `flushNarrationBuffer` — meaning that `setCanType(true)` never fired on narration arrival. If the game currently works, it is because the server sends a `SESSION_EVENT{ready}` after each turn that triggers the reset at line 253. If the server does NOT send that event, `canType` is stuck at `false` after the first player action until the user reconnects. This is a pre-existing latent condition that my buffer deletion surfaced (by removing the last trace of "setCanType(true) on narration"). The ADR-076 manual-playtest acceptance gate should explicitly verify this: after a player sends one action and the narration completes, confirm the input field re-enables. Affects `sidequest-ui/src/App.tsx` and the ADR-076 acceptance gate verification. *Found by TEA during test verification.*
- **Improvement** (non-blocking, UI tech debt): The UI repo has 82 persistent test failures across 10 files — `useAudio.test.ts`, `AudioStatus.test.tsx`, `TurnStatusAutoResolved.test.tsx`, `AudioEngine.test.ts`, `TurnStatusSealedLetter.test.tsx`, `gameboard-wiring.test.tsx`, `GameLayout-resources.test.tsx`, `ptt-flow-e2e.test.tsx`, `usePttMicMuting.test.ts`, `usePushToTalk.test.ts`. These are unrelated to narration and predate 27-9. The ambient redness makes regression detection harder for every future story. Worth a dedicated tech-debt sprint. Affects `sidequest-ui`. *Found by TEA during test verification.*

### Dev (implementation)

- **Gap** (non-blocking): `sidequest-api/crates/sidequest-game/CLAUDE.md` and `sidequest-api/crates/sidequest-server/CLAUDE.md` both claim that `tts_stream.rs` (TtsSegment, TtsSynthesizer trait, TtsStreamer), `segmenter.rs`, `voice_router.rs`, and `AudioMixer::duck_for_tts()` / `on_tts_start()` / `on_tts_end()` are fully complete and production-ready. These references are stale post-Epic-27 and are **out of scope for 27-9** per the ADR non-scope list ("useAudio, audio.engine.playVoicePCM, audio.engine.playVoice may have other callers"). Worth a follow-up story to audit which of those files are actually still alive, which are dead, and which should be rewritten or removed. Affects `sidequest-api/crates/sidequest-game/CLAUDE.md`, `sidequest-api/crates/sidequest-server/CLAUDE.md`, and potentially several source files (`tts_stream.rs`, `segmenter.rs`, `voice_router.rs`). *Found by Dev during implementation.*
- **Observation** (non-blocking): The UI phantom-reference discovery — `isVoiceAudioFrame` and `decodeVoiceFrame` were called in `handleBinaryMessage` but had no import and no definition anywhere in the sidequest-ui repo. They were undefined symbols that vitest was silently allowing past strict checking. Deleting `handleBinaryMessage` removed the only call sites, and `tsc --noEmit` is now clean. This suggests either (a) these functions existed in an earlier codebase state and were deleted from their source file without deleting their callers, or (b) vitest's transform pipeline is ignoring type errors that a full tsc build would catch. Worth a tech-debt investigation into how the UI build/test pipeline handles undefined-symbol references. Affects `sidequest-ui` build config. *Found by Dev during implementation.*
- **Observation** (non-blocking): `docs/wiring-diagrams.md` Section 4 ("TTS Voice Pipeline") was not just a single NarrationChunk reference — it was a full 45-line mermaid diagram of the retired Kokoro pipeline (SentenceSegmenter, VoiceRouter, DaemonSynthesizer, TtsMessage::Start/End, binary voice frames, AudioMixer ducking). ADR-076 only mentioned "remove the chunk arrow and reflect the simplified two-message flow" but the honest fix was to delete the whole section. I replaced it with a concise removal note that points at Section 1 for the current flow and at ADR-076 for rationale. Section numbers preserved (Section 4 is now "removed" rather than renumbered) so anchor links into the doc don't break. *Found by Dev during implementation.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

- No deviations logged during setup. Scope is fully inherited from ADR-076.

### TEA (test design)

- No deviations from spec. The test suite covers every mechanical item in ADR-076's scope summary (protocol variant removal, payload struct removal, NarrationEnd doc comment, prerender.rs doc comments, extraction.rs doc comments, daemon-client audit, UI buffer fields, UI handleBinaryMessage, UI wiring check). Non-mechanical items (wiring diagram prose, new doc-comment text quality) are documented as manual review items in the TEA Assessment and will be verified by Reviewer, not by automated tests.

### TEA (verify)

- **Orphaned narration buffer deleted beyond ADR-076's simplification scope**
  - Spec source: `docs/adr/076-narration-protocol-collapse-post-tts.md` §UI Narration Buffer Cleanup, items 1-6
  - Spec text: "Remove `chunks: GameMessage[]` from `narrationBufferRef`. Remove `watchdogTimer` from `narrationBufferRef`. Delete `handleBinaryMessage` entirely. ... Simplify `flushNarrationBuffer` to only handle `narration` and `narrationEnd`. Rewrite the block comment on lines 180–183 to describe what the buffer actually does now: 'Buffer a Narration until its paired NarrationEnd arrives, then flush both atomically so the StateDelta applies in the same React commit as the narration text.'"
  - Implementation: In the verify phase, TEA deleted the entire `narrationBufferRef` useRef declaration AND the `flushNarrationBuffer` useCallback AND the rewritten block comment — everything the spec said to "simplify" is now gone. The reconnect handler comment at line ~224 was also updated to remove the stale "narration buffer to avoid duplicates" phrasing. Verified by `grep -rn "flushNarrationBuffer\|narrationBufferRef" src/` returning zero hits post-commit.
  - Rationale: Two independent simplify teammates (quality, efficiency) converged on a high-confidence finding that `flushNarrationBuffer` was never called from anywhere in the codebase. Verified manually. That means the "simplified" buffer from ADR-076 was still orphaned after Dev's green-phase fix — the spec asked for a simplification of a component that had no runtime effect in the first place. The spec's description of the buffer's role ("pair Narration with NarrationEnd for atomic state_delta flush") was factually wrong; the real narration path has been a straight-through `setMessages` at App.tsx:240-245 since before 27-9 began. React 18's automatic batching was already handling the state coherence the buffer claimed to provide. Deleting the orphan was the correct application of the project's "no dead code" principle — leaving the simplified buffer would have left a half-wired survivor in the exact pattern ADR-076 was trying to prevent.
  - Severity: minor (expansion of delivered scope, in the direction of the spec's own stated intent)
  - Forward impact: positive — no sibling story depends on the buffer, React batching was already doing the work the buffer claimed. A future ADR revisiting the narration protocol should not describe this buffer as ever having existed functionally. The green-phase "atomic state_delta flush" claim in Dev's rewritten doc comment is retroactively moot.

### Dev (implementation)

- **Section 4 of docs/wiring-diagrams.md deleted entirely, not just the chunk arrow**
  - Spec source: `docs/adr/076-narration-protocol-collapse-post-tts.md` §Cross-Repo Wiring Diagram
  - Spec text: "`docs/wiring-diagrams.md` references `NarrationChunk` in the narration flow diagram. Update to remove the chunk arrow and reflect the simplified two-message flow."
  - Implementation: Replaced the entire 45-line Section 4 ("TTS Voice Pipeline") with a concise removal note. The original diagram didn't have a standalone "chunk arrow" to surgically remove — the whole section was the Kokoro TTS pipeline (SentenceSegmenter, VoiceRouter, DaemonSynthesizer, Kokoro, binary voice frames, AudioMixer ducking), which was retired in Epic 27-1 and is entirely stale documentation. The "simplified two-message flow" (Narration → NarrationEnd) is already fully documented in Section 1 (Core Turn Loop) at dispatch lines 2698/2741, so no replacement diagram is needed.
  - Rationale: A surgical edit of just the NarrationChunk node would leave the rest of the TTS diagram standing, which would be misleading for any future reader. The honest fix is to acknowledge the entire pipeline is gone. Section 4 is now a stub ("removed") that preserves the section number so `#5-music--audio` through `#16-genre-pack-loading` anchors remain stable.
  - Severity: minor (expansion of scope, not contraction)
  - Forward impact: none — any future story reintroducing TTS will need to re-add documentation, but that's expected for a new feature. No sibling story depends on the deleted section's content.

- **daemon-client/src/types.rs audit: no work to do**
  - Spec source: ADR-076 §Daemon Client Types
  - Spec text: "Audit `sidequest-api/crates/sidequest-daemon-client/src/types.rs` for any `Tts*` or `Voice*` synthesis request/response types that have no remaining callers. Delete them."
  - Implementation: Inventoried the file during TEA's red phase. Zero `Tts*` or `VoiceSynth*` structs/enums present. The only types are image/embed/render plumbing (`DaemonRequest`, `RenderParams`, `WarmUpParams`, `EmbedParams`, `EmbedResult`, `DaemonResponse`, `ErrorPayload`, `RenderResult`, `StatusResult`). The audit item is already satisfied by prior Epic 27-1 work. No code changes made.
  - Rationale: The spec's "audit and delete" is conditional on orphaned types existing. They don't. TEA's guard test `daemon_client_types_has_no_tts_or_voice_synthesis_types` enforces this invariant going forward — it's already green and would fail if someone reintroduces the pattern.
  - Severity: trivial
  - Forward impact: none

- **NarrationChunkMessage removal: no work to do**
  - Spec source: ADR-076 §Protocol Layer (by implication — "delete `NarrationChunkPayload` from `sidequest-ui/src/types/payloads.ts`")
  - Spec text: "Delete `NarrationChunkPayload` from `sidequest-ui/src/types/payloads.ts`."
  - Implementation: The `NarrationChunkPayload` interface was deleted (per spec). However, there was never a `NarrationChunkMessage` member in the `TypedGameMessage` discriminated union — the variant existed in the protocol type definition but was never wired into the UI's message dispatch at all. TEA's guard test confirmed this state at RED time and still passes. No additional work needed.
  - Rationale: This is precisely why the half-wired state arose in the first place — the Architect flagged it in ADR-076 §Context. The UI was never a consumer, so there was no union member to remove.
  - Severity: trivial
  - Forward impact: none

- **Stale CLAUDE.md inventories updated even though not listed in ADR-076 scope**
  - Spec source: ADR-076 scope summary (8 numbered items, plus §Daemon Client Types, §Cross-Repo Wiring Diagram)
  - Spec text: The scope summary lists specific files but does not mention `sidequest-api/CLAUDE.md`, `sidequest-api/crates/sidequest-protocol/CLAUDE.md`, or `sidequest-ui/CLAUDE.md`.
  - Implementation: Updated three CLAUDE.md files to reference ADR-076 and to drop the stale `NARRATION_CHUNK` / `TTS_START/CHUNK/END` entries from the protocol crate's GameMessage inventory line. The root `sidequest-api/CLAUDE.md` and `sidequest-ui/CLAUDE.md` ADR index tables now include "076 (narration protocol collapse post-TTS)" in the Frontend/protocol row.
  - Rationale: TEA logged these as Gap findings in the Delivery Findings section. Leaving the inventories stale would create new half-wired documentation state the instant this story merges — the very pattern the project rules exist to prevent. I chose to fix them in-place rather than defer to a separate tech-debt story, consistent with the "fix all gaps in current session" memory rule.
  - Severity: minor (scope expansion, in the direction of the project's own principles)
  - Forward impact: positive — future readers see accurate inventories and a complete ADR index

### Architect (reconcile)

**Review of existing deviation entries:** The TEA (test design), TEA (verify), and Dev (implementation) subsections above are all well-formed with 6-field entries. Spec sources quoted inline, implementation descriptions match the code changes verified in git, forward-impact assessments are accurate. No corrections needed to existing entries.

**Missed deviations added below:**

- **ADR-076 made a factually incorrect claim about the narration buffer's runtime role**
  - Spec source: `docs/adr/076-narration-protocol-collapse-post-tts.md` §UI Narration Buffer Cleanup (the version I wrote as Architect at session start)
  - Spec text: "Rewrite the block comment on lines 180–183 to describe what the buffer actually does now: 'Buffer a `Narration` until its paired `NarrationEnd` arrives, then flush both atomically so the `StateDelta` applies in the same React commit as the narration text.'"
  - Implementation: This spec description was wrong. The narration buffer in `App.tsx` was orphaned — `flushNarrationBuffer` had zero callers in the entire `src/` tree (verified in verify phase by two independent simplify teammates, re-verified by Reviewer via `grep -rn "flushNarrationBuffer" src/`). The real narration path has always been a straight-through `setMessages` at `App.tsx:240-245` which bypasses the buffer entirely. The "atomic state_delta flush" behavior the ADR described never ran at runtime. React 18's automatic batching was handling state coherence without any explicit buffering.
  - Rationale for logging this as a deviation: the Architect (me) produced a specification that did not match the runtime reality of the code being specified. The error propagated downstream — Dev's green-phase doc-comment rewrite in `sidequest-protocol/src/message.rs` inherited the wrong claim into the public API docs, which Reviewer then had to catch and fix inline as commit `176ab1f`. The TEA verify phase's discovery and the Reviewer F1 fix are both logged as their own deviations (TEA verify, Reviewer F1), but the root-cause spec defect was mine as Architect and belongs in the reconcile manifest.
  - Severity: major (factual error in the authoritative scope document for the story)
  - Forward impact: positive going forward — any future ADR revisiting the narration protocol should NOT describe a buffer-based atomic-flush contract. React's automatic batching is the real mechanism. ADR-076 itself should be annotated with a post-hoc correction note in a follow-up if the ADR is ever revisited; currently Proposed status means it can be revised in-place without a superseding ADR, but that is a documentation task outside 27-9's story scope.

- **Reviewer applied two inline fixes beyond the original 27-9 story scope**
  - Spec source: story scope (session file) + ADR-076 §scope summary
  - Spec text: Neither the session file scope nor ADR-076 authorized the Reviewer to apply code fixes. The standard TDD workflow expects Reviewer to approve-or-reject, not to edit.
  - Implementation: Reviewer applied two fixes inline: (1) commit `176ab1f` rewriting the `NarrationEnd` variant and `NarrationEndPayload` struct doc comments in `sidequest-protocol/src/message.rs` to remove the phantom atomic-flush claims (F1); (2) an `rm` of the rogue `sidequest-game/src/lore.rs` file in the working tree (F0, ambient breakage out of 27-9 scope).
  - Rationale: F1 was a two-comment rewrite with no runtime impact, caught in a Reviewer domain (comment_analyzer) that was disabled via settings so no subagent would have surfaced it automatically. Hand-back to Dev would have cost a full phase cycle for a trivial edit; Reviewer-applied inline fix was the pragmatic choice. F0 was out-of-story-scope ambient breakage that Keith explicitly authorized via Option A during the Reviewer phase — not a unilateral Reviewer decision. Both expansions are consistent with the project's "fix all gaps in current session" memory rule.
  - Severity: minor (scope expansion by a non-implementing agent, but pre-authorized for F0 and project-principle-compliant for F1)
  - Forward impact: none — both fixes leave the codebase in a better state than the original 27-9 scope would have; no sibling story depends on the fixed surfaces.

- **The `reviewer-preflight` subagent's scoped build hid ambient breakage**
  - Spec source: reviewer-preflight subagent contract (from the Reviewer agent prompt I drafted)
  - Spec text: N/A — the preflight prompt specified `cargo build -p sidequest-protocol` rather than `cargo build --workspace`. There was no authoritative specification requiring workspace-scope builds.
  - Implementation: The scoped build returned "clean" for the protocol crate while `sidequest-game` was simultaneously broken by two compile errors (E0761 + E0282) caused by the rogue `lore.rs` file. This is a process gap in how Reviewer-phase preflight is scoped, not a 27-9 code correctness issue.
  - Rationale: Logged here for auditability because it explains how F0 survived undetected through Dev green + TEA verify + Reviewer preflight. Memory file `feedback_stale_claude_md_file_fabrication.md` captures the mitigation (always use workspace-scope builds, verify paths with `git ls-files` before editing).
  - Severity: minor (process gap, not a 27-9 correctness gap)
  - Forward impact: positive — future cross-repo reviewer prompts will specify workspace-scope builds in preflight by default.

**AC deferral verification:** Story 27-9 has no deferred ACs. The ac-completion gate during Dev exit did not record any DEFERRED entries (all ADR-076 scope items marked ✓ done in the Dev Assessment's scope coverage table, with two items marked "already satisfied" for daemon-client types and NarrationChunkMessage union — both protected by TEA guard-invariant tests). No AC accountability changes are required during reconcile.

**Spec authority check:** No conflicts between story scope (session file), story context (N/A — OQ-2 does not have `context-story-*.md` files for most stories), ADR-076, or sibling stories in Epic 27. The scope expansions logged above are all documented in-band with their deviation rationales. Nothing to reconcile at the authority-hierarchy level.

**Reconcile verdict:** Deviation manifest is complete and internally consistent. The three missed entries above (ADR-076 factual error, Reviewer inline fixes, preflight scope gap) round out the audit trail that TEA and Dev could not have written themselves. Ready for SM finish.

## TEA Assessment

**Phase:** finish
**Tests Required:** Yes
**Status:** RED (failing — ready for Dev)

### Test Files

- `sidequest-api/crates/sidequest-protocol/src/narration_collapse_story_27_9_tests.rs` — 8 tests, 7 failing (correct RED), 1 passing (daemon-client guard invariant)
- `sidequest-api/crates/sidequest-protocol/src/tests.rs` — removed `narration_chunk_round_trip` (prevents compile failure in GREEN)
- `sidequest-api/crates/sidequest-protocol/src/lib.rs` — registered new test module
- `sidequest-ui/src/__tests__/narration-chunk-deletion-27-9.test.ts` — 8 tests, 6 failing (correct RED), 2 passing (guard invariants)

### Tests Written: 16 tests across 2 repos covering all 9 mechanical scope items in ADR-076

| ADR-076 Section | Mechanical Item | Test(s) | Status |
|---|---|---|---|
| §Protocol Layer | Remove `NarrationChunk` variant | `message_rs_contains_no_narration_chunk_references` | failing |
| §Protocol Layer | Remove `NarrationChunkPayload` struct | `narration_chunk_payload_struct_is_removed` | failing |
| §Protocol Layer | `NarrationChunk` JSON must not deserialize | `narration_chunk_json_does_not_deserialize_as_game_message` | failing |
| §Protocol Layer | Delete round-trip test | (done in this phase by TEA) | ✓ |
| §Protocol Layer | Remove `NarrationChunkPayload` interface (UI) | `payloads.ts does not define NarrationChunkPayload interface` | failing |
| §Narration Flow | Update `NarrationEnd` doc comment | `narration_end_doc_comment_no_longer_claims_stream_terminator` | failing |
| §UI Buffer Cleanup | Remove `buf.chunks` field | `App.tsx narration buffer does not carry buf.chunks field` | failing |
| §UI Buffer Cleanup | Remove `watchdogTimer` field | `App.tsx narration buffer does not carry watchdogTimer field` | failing |
| §UI Buffer Cleanup | Delete `handleBinaryMessage` | `App.tsx does not define handleBinaryMessage callback` | failing |
| §UI Buffer Cleanup | Simplify `flushNarrationBuffer` | (behavioral — verified by wiring check tests) | covered |
| §UI Buffer Cleanup | Rewrite buffer block comment | (prose quality — manual review by Reviewer) | deferred |
| §Doc Cleanup | `prerender.rs` stale TTS phrases | `prerender_rs_has_no_stale_tts_playback_language` | failing |
| §Doc Cleanup | `extraction.rs` stale TTS phrases | `extraction_rs_has_no_stale_tts_clean_language` | failing |
| §Doc Cleanup (new text) | Quality of replacement prose | (prose quality — manual review by Reviewer) | deferred |
| §Daemon Client Types | Audit & remove orphaned Tts*/Voice* | `daemon_client_types_has_no_tts_or_voice_synthesis_types` | ✓ already clean |
| Acceptance Gate wiring check (Rust) | No `NarrationChunk` in production .rs files | `no_production_references_to_narration_chunk_in_sidequest_api` | failing |
| Acceptance Gate wiring check (UI) | No `NarrationChunk` in production .ts/.tsx files | `no production file references NarrationChunk` | failing |
| Acceptance Gate wiring check (UI) | No `handleBinaryMessage` in production | `no production file references handleBinaryMessage` | failing |
| §Cross-Repo Wiring Diagram | Remove NarrationChunk from docs/wiring-diagrams.md | (orchestrator-level, not in subrepo test infra — deferred to manual review) | deferred |

### Deferred to Reviewer (non-mechanical)

- **Prose quality of replacement doc comments** in `NarrationEnd`, `prerender.rs` lines 1/3/97, `extraction.rs` lines 4/155. My tests verify the STALE phrases are gone; they cannot verify the REPLACEMENT prose is good. Reviewer must judge.
- **`flushNarrationBuffer` simplification quality** — the wiring check tests verify that `buf.chunks`, `handleBinaryMessage`, and `watchdogTimer` are gone. They do not verify that the new shape of `flushNarrationBuffer` is idiomatic, well-structured, or bug-free. Reviewer should read the simplified function and confirm it handles the `narration` + `narrationEnd` flush correctly.
- **`docs/wiring-diagrams.md` update** — this lives in the orchestrator repo, not in a subrepo with test infrastructure. I chose not to add cross-repo relative-path file reads from the Rust tests because that would be fragile if the subrepo is ever checked out standalone. Reviewer must eyeball the file on review.
- **Protocol crate `CLAUDE.md` update** — see Delivery Finding above. Reviewer should verify Dev updated it, or push back and ask Dev to.

### Rule Coverage

Read `.pennyfarthing/gates/lang-review/rust.md` (15 checks) and `.pennyfarthing/gates/lang-review/typescript.md` (not read — no new production code to review; only test files added).

This is a **deletion-driven story** with zero new production code. Most Rust rules do not apply because there is nothing new to scan:

| Rule | Applies? | Coverage |
|------|---------|----------|
| #1 silent error swallowing | No | No new error-handling code |
| #2 non_exhaustive on public enums | No | Removing a variant, not adding enums |
| #3 hardcoded placeholders | No | No new constants |
| #4 tracing coverage | No | No new error paths |
| #5 validated constructors | No | No new constructors |
| **#6 test quality** | **Yes** | All 8 Rust tests have meaningful `assert_eq!`/`assert!` with specific failure messages. No `let _ =`, no `is_none()` on always-None, no `assert!(true)`. Self-check pass. Guard tests (daemon-client, NarrationChunkMessage) are invariant-enforcement, not vacuous — they'd catch a regression. |
| #7 unsafe `as` casts | No | No new casts |
| #8 Deserialize bypass | No | No new deserializable types |
| #9 public fields | No | No new types |
| #10 tenant context | No | N/A for this crate |
| #11 workspace dependency | No | No new deps |
| #12 dev-only deps | No | No new deps |
| #13 constructor/Deserialize consistency | No | Removing, not adding |
| #14 fix-introduced regressions | Partial | Will be rechecked by Reviewer after GREEN |
| #15 unbounded input | No | No new parsers |

**Rules meaningfully checked:** 1 of 15 applicable — only rule #6 (test quality) applies to a pure deletion story. Self-check passed.

### RED State Verification

`testing-runner` run ID: `27-9-tea-red`. See earlier subagent output in this session. Summary:
- **sidequest-api:** 7/8 new tests failing at runtime for correct reasons, 1/8 guard invariant already green. 133 pre-existing protocol crate tests: all passing. Zero regressions from the `narration_chunk_round_trip` removal in `tests.rs`.
- **sidequest-ui:** 6/8 new tests failing at runtime for correct reasons, 2/8 guard invariants already green. 0 regressions from my changes. (88 pre-existing UI test failures are unrelated — see Delivery Findings.)

### Note on Commit Hygiene (Option C — left in place)

Commit `d17076c` on the `sidequest-ui` branch `feat/27-9-collapse-narration-protocol` inadvertently swept up a pre-staged `src/components/Dashboard/shared/constants.ts` modification alongside the intended test file. The constants.ts change was staged (not just modified) before I arrived in the subrepo — Keith's WIP from an earlier session that I failed to detect before committing because I misread `git status --short`'s two-column format. Keith chose Option C (leave it) rather than amend or revert. The unrelated file now rides with the 27-9 branch. This is documented here for Reviewer awareness — **Reviewer should check whether `constants.ts` changes conflict with any other in-flight 27-9 work, and if so, flag accordingly**. Memory file `feedback_git_status_misread.md` added to prevent recurrence.

### Handoff

**To Dev (Bicycle Repair Man)** for GREEN phase. Dev's job is to delete the code these tests assert against — the ADR-076 scope summary is the authoritative punch list. When all 13 failing tests flip to green without breaking the 133 passing protocol tests or introducing new UI regressions, GREEN is complete and handoff returns to TEA for the verify phase (simplify + quality-pass).

## Dev Assessment

**Implementation Complete:** Yes
**Phase:** finish (complete)
**Tests:** 16/16 passing across both subrepos (8 Rust + 8 UI). Zero regressions. Workspace build clean. `tsc --noEmit` clean.

### Files Changed

**sidequest-api** (commit `6e0da20` on `feat/27-9-collapse-narration-protocol`, pushed):
- `crates/sidequest-protocol/src/message.rs` — deleted `GameMessage::NarrationChunk` variant and `pub struct NarrationChunkPayload`; rewrote `NarrationEnd` variant doc comment and `NarrationEndPayload` struct doc comment from "End of narration stream" (TTS-era stream terminator) to the current role (turn-completion marker + atomic state-delta flush).
- `crates/sidequest-game/src/prerender.rs` — rewrote three doc comments (lines 1, 3, 97) to describe the actual current trigger (gap between narration turns, whatever its duration) instead of the retired TTS playback window language. Scheduler logic itself is unchanged.
- `crates/sidequest-server/src/extraction.rs` — rewrote module doc and `strip_fenced_blocks` inline comment from "TTS-clean text" / "TTS pipeline" framing to "narration display cleanup" language. Cleanup logic is unchanged.
- `crates/sidequest-protocol/CLAUDE.md` — updated the GameMessage inventory line: removed the specific "23 variants" count and dropped `NARRATION_CHUNK` and `TTS_START/CHUNK/END` from the enumerated variant list. Added note pointing at Epic 27 and ADR-076 for the removal.
- `CLAUDE.md` (root) — added "076 (narration protocol collapse post-TTS)" to the Frontend/protocol row of the Architecture Decision Index.

**sidequest-ui** (commit `c1443a1` on `feat/27-9-collapse-narration-protocol`, pushed):
- `src/types/payloads.ts` — deleted `NarrationChunkPayload` interface.
- `src/App.tsx` — removed `chunks: GameMessage[]` and `watchdogTimer` fields from `narrationBufferRef`; deleted `handleBinaryMessage` useCallback entirely (and with it the phantom references to `isVoiceAudioFrame` / `decodeVoiceFrame` which had no import or definition anywhere); simplified `flushNarrationBuffer` to handle only `narration` + `narrationEnd`; rewrote the buffer's block comment to describe its current job (pair Narration with NarrationEnd for atomic state_delta flush); updated the `useAudio` comment from "unified mixer for TTS, music, SFX" to "unified mixer for music, SFX, ambience".
- `CLAUDE.md` — added "076 (narration protocol collapse post-TTS)" to the Frontend/protocol row of the Architecture Decision Index.

**orchestrator** (commit `b99fcc3` on `feat/27-9-collapse-narration-protocol`, pushed):
- `docs/wiring-diagrams.md` — replaced Section 4 "TTS Voice Pipeline" (45-line stale Kokoro/Piper/VoiceRouter/DaemonSynthesizer/binary-frame mermaid diagram) with a concise removal note that points readers at Section 1 (Core Turn Loop) for the current two-message flow and at ADR-076 for the rationale. Section number preserved so inbound anchor links (`#5-music--audio` through `#16-genre-pack-loading`) do not break. Table of Contents line 16 updated to reflect the "removed" status.

### Branches (pushed, NOT merged)

| Repo | Branch | Commit | Target | Status |
|---|---|---|---|---|
| sidequest-api | `feat/27-9-collapse-narration-protocol` | `6e0da20` | `develop` (gitflow) | pushed, no PR yet |
| sidequest-ui | `feat/27-9-collapse-narration-protocol` | `c1443a1` + `d17076c` (TEA test commit w/ Option C constants.ts) | `develop` (gitflow) | pushed, no PR yet |
| orchestrator | `feat/27-9-collapse-narration-protocol` | `b99fcc3` | `main` (trunk-based) | pushed, no PR yet |

**PR creation is SM's responsibility during the finish phase.** Per the dev agent rules, I do not create PRs.

### Verification (testing-runner run-id `27-9-dev-green`)

| Repo | Command | Result |
|---|---|---|
| sidequest-api | `cargo test -p sidequest-protocol` | 140 passing, 0 failing (was 133 before story; minus 1 deleted round-trip test; plus 8 new 27-9 tests = 140) |
| sidequest-api | `cargo build` (full workspace) | clean, zero errors, all crates link with NarrationChunk gone |
| sidequest-ui | `npx vitest run src/__tests__/narration-chunk-deletion-27-9.test.ts` | 8 passing, 0 failing |
| sidequest-ui | `npx tsc --noEmit` | clean, exit 0 (confirms no broken references from App.tsx surgery) |

### Scope Coverage Against ADR-076

| ADR-076 scope item | Status | Note |
|---|---|---|
| §Protocol Layer — remove `NarrationChunk` variant | ✓ done | message.rs edit |
| §Protocol Layer — remove `NarrationChunkPayload` struct | ✓ done | message.rs edit |
| §Protocol Layer — delete serde round-trip test | ✓ done (by TEA) | tests.rs edit during red phase |
| §Protocol Layer — remove UI `NarrationChunkPayload` interface | ✓ done | payloads.ts edit |
| §Narration Flow — rewrite `NarrationEnd` doc comment | ✓ done | message.rs variant + payload struct comments both rewritten |
| §UI Buffer Cleanup #1 — remove `buf.chunks` | ✓ done | App.tsx edit |
| §UI Buffer Cleanup #2 — remove `buf.watchdogTimer` | ✓ done | App.tsx edit |
| §UI Buffer Cleanup #3 — delete `handleBinaryMessage` | ✓ done | App.tsx edit (unregistration trivial — callback was defined but never referenced) |
| §UI Buffer Cleanup #4 — remove `isVoiceAudioFrame` / `decodeVoiceFrame` imports | N/A | no imports existed; phantom references only, died with `handleBinaryMessage` deletion |
| §UI Buffer Cleanup #5 — simplify `flushNarrationBuffer` | ✓ done | App.tsx edit |
| §UI Buffer Cleanup #6 — rewrite buffer block comment | ✓ done | App.tsx edit |
| §Doc Cleanup — `prerender.rs` doc comments | ✓ done | 3 comments rewritten |
| §Doc Cleanup — `extraction.rs` doc comments | ✓ done | 2 comments rewritten |
| §Daemon Client Types — audit | ✓ done (no work) | zero `Tts*`/`VoiceSynth*` types present; see Dev deviation |
| §Cross-Repo Wiring Diagram | ✓ done | Section 4 deleted with removal note; see Dev deviation |
| Added: protocol crate CLAUDE.md inventory | ✓ done (TEA Gap) | variant list updated |
| Added: api root CLAUDE.md ADR index | ✓ done (TEA Gap) | ADR-076 added to Frontend/protocol row |
| Added: ui CLAUDE.md ADR index | ✓ done | ADR-076 added to Frontend/protocol row for parity |

**All mechanical scope items complete. All deviations logged. All paired commits pushed.**

### Self-Review Checklist

- [x] Tests green across both repos
- [x] Working tree has no unintended changes staged (verified with `git diff --cached --name-only` on each subrepo before commit — new memory rule applied)
- [x] No debug code left behind
- [x] Correct feature branches on each repo (develop-targeted subrepos, main-targeted orchestrator)
- [x] Code wired to production consumers (N/A for deletion story — wiring checks confirm the opposite invariant, that nothing references the removed symbols)
- [x] Project patterns followed (matches `combat-overlay-deletion-28-9.test.ts` and `voice-kill-switches-removed.test.ts` precedent)
- [x] All ADR acceptance criteria addressed (mechanical items done; prose-quality items flagged for Reviewer)
- [x] Error handling — N/A for pure deletion; no new code paths

### Handoff

**To TEA (Mr. Praline)** for the **verify phase** — simplify + quality-pass fan-out to catch any over-engineering or quality issues in my deletion-era code. Note that this is a nearly-pure deletion story with 32 lines added and 97 lines deleted across both subrepos (plus 21 lines added / 38 lines deleted in the orchestrator docs). Simplify findings are likely to be minimal because there's almost no new code to analyze — the risk profile skews toward "did I delete too much" rather than "did I add complexity."

Verify-phase focus areas for TEA:
1. Confirm the simplified `flushNarrationBuffer` in `sidequest-ui/src/App.tsx` has no functional regression — it now unconditionally pushes `buf.narration` then `buf.narrationEnd`, which matches its historical post-TTS behavior.
2. Run the full UI test suite (not just the 27-9 file) to check whether any of the 88 pre-existing UI test failures have changed count or character. A delta there could indicate I inadvertently broke or fixed something unrelated.
3. Run `cargo clippy -- -D warnings` on the sidequest-api workspace — my doc comment rewrites in prerender.rs and extraction.rs may have triggered new warnings (though the earlier build was clean with 15 pre-existing warnings only).
4. The three simplify teammates (reuse, quality, efficiency) may return `status: clean` immediately because there's almost nothing to simplify. That's an expected outcome for a deletion story.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

### Gate Structural Check

`pf handoff resolve-gate 27-9 tdd spec-check` returned `status: ready` with no recovery config. All three structural validations passed:

1. **AC coverage** — every ADR-076 scope item has a corresponding entry in the Dev Assessment's scope coverage table. 16 items, 16 ✓.
2. **Implementation complete** — Dev marked the phase as `Implementation Complete: Yes` and tests are verified green across both subrepos (140 Rust passing, 8 UI passing, `cargo build` clean, `tsc --noEmit` clean).
3. **Deviation logging** — both `### TEA (test design)` and `### Dev (implementation)` subsections exist under `## Design Deviations` with properly formatted 6-field entries.

### Substantive Verification (spot checks)

I spot-checked the four most load-bearing claims in Dev's Assessment by running the grep wiring checks myself rather than trusting the Dev Assessment's summary:

| Claim | Verification command | Result |
|---|---|---|
| "No production `.rs` file in sidequest-api references `NarrationChunk`" | grep across api crates excluding test files | 0 hits ✓ |
| "No production `.ts/.tsx` file in sidequest-ui references `NarrationChunk`" | grep across ui src excluding test files | 0 hits ✓ |
| "daemon-client/src/types.rs has zero Tts*/VoiceSynth* types" | grep on daemon-client types.rs | 0 hits ✓ |
| "`NarrationChunkMessage` never existed in the UI TypedGameMessage union" | grep on ui payloads.ts | 0 hits ✓ |

All four claims verified. No hidden work remaining.

### Dev Deviation Review

Dev logged four deviations, all in the 6-field format. Each is reviewed below.

1. **"Section 4 of docs/wiring-diagrams.md deleted entirely, not just the chunk arrow"** — **Accepted.** The spec said "remove the chunk arrow and reflect the simplified two-message flow." The diagram had no standalone chunk arrow; the entire section was the retired Kokoro pipeline. A surgical edit would have left a misleading diagram standing. The full-section delete with a removal stub is the faithful interpretation of "reflect the simplified two-message flow." Severity: minor (scope expansion in the right direction).

2. **"daemon-client/src/types.rs audit: no work to do"** — **Accepted.** The spec's "audit and delete" is conditional on orphaned types existing. Inventory confirmed none present. TEA's guard test (`daemon_client_types_has_no_tts_or_voice_synthesis_types`) locks this invariant. Severity: trivial.

3. **"NarrationChunkMessage removal: no work to do"** — **Accepted.** The UI-side union was never wired to include this variant — precisely the half-wired state ADR-076 §Context identified as the root cause of the dead code. Nothing to remove. Severity: trivial.

4. **"Stale CLAUDE.md inventories updated even though not listed in ADR-076 scope"** — **Accepted and commended.** TEA logged three Gap findings against CLAUDE.md files during the red phase. Dev fixed them in-place rather than punting to a separate tech-debt story. This matches the `feedback_no_deferring.md` memory rule ("Fix ALL gaps in the current session, never 'defer to separate session'") and the project's own "no half-wired features" principle. Leaving the inventories stale would have produced new half-wired documentation the instant this story merged. Severity: minor (scope expansion in the right direction).

**Pattern observation:** all four deviations are scope expansions toward cleanliness, not contractions of delivered scope. That is exactly the kind of drift the project rewards. No deviation trims what the spec asked for.

### Mismatch Categorization

Following the spec-check template:

- **Missing in code:** None. Every ADR-076 scope item is either done or already satisfied (and the already-satisfied cases are protected by TEA's guard tests).
- **Extra in code:** Three (wiring-diagrams.md section replacement, three CLAUDE.md updates, doc comment scope expansion). All three are minor scope expansions in the spec's own direction.
- **Different behavior:** None. The protocol is strictly smaller, not different.
- **Ambiguous spec:** One (the "remove the chunk arrow" phrasing Dev read as "rewrite the section"). Dev's interpretation is defensible and better than the literal reading.

### Decision

**Spec alignment is verified. No hand-back to Dev. Proceeding to verify phase.**

The story is ready for TEA's simplify + quality-pass fan-out. The risk profile is exactly as Dev described: almost no new code means the simplify teammates are likely to return clean immediately; the substantive verify work is "did the deletion break anything not covered by the RED tests" (e.g., the full UI suite's 88 pre-existing failures, `cargo clippy` drift, manual narration smoke test).

### Handoff

**To TEA (Mr. Praline)** for the verify phase. See Dev's handoff notes above for the four focus areas.
---

## Postfix Verify (TEA simplify phase — 2026-04-10)

**Change:** Deleted orphaned narration buffer infrastructure from `sidequest-ui/src/App.tsx`:
- Removed `narrationBufferRef` useRef declaration (41 lines including comment block)
- Removed `flushNarrationBuffer` useCallback
- Updated reconnect handler comment to remove "narration buffer" reference

**Tests Run:**
1. `npx tsc --noEmit` — **PASS** (zero new errors)
2. `npx vitest run src/__tests__/narration-chunk-deletion-27-9.test.ts` — **PASS** (8/8 tests)
3. `npx vitest run` (full suite) — **82 failures** (baseline: 82, delta: 0)

**Verdict:** SAFE_TO_COMMIT. The buffer deletion removed truly dead code with zero regressions. Type checker confirms no broken references. The 27-9 RED tests all pass, verifying the infrastructure was absent from the current codebase. Full suite failure count is stable at 82, matching the prior verify baseline.

## TEA Assessment (verify phase)

**Phase:** finish (complete)
**Status:** GREEN confirmed, simplify fix applied, ready for Reviewer

### Simplify Fan-Out Report

Three simplify teammates ran in parallel against the 7 changed code files (excluding Keith's Option-C WIP file `constants.ts` and all `.md` docs):

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | findings | 1 high-confidence — `extraction.rs` blank-line collapse duplication between `strip_combat_brackets()` and `strip_fenced_blocks()` |
| simplify-quality | findings | 1 high-confidence — `narrationBufferRef`/`flushNarrationBuffer` orphaned in App.tsx |
| simplify-efficiency | findings | 1 high-confidence — same orphan as quality (independent convergence) |

**Applied:** 1 high-confidence fix (App.tsx orphaned buffer)
**Flagged for follow-up:** 1 high-confidence finding (extraction.rs DRY — deferred as pre-existing tech debt, out of 27-9 scope)
**Noted:** 0 low-confidence observations
**Reverted:** 0

**Overall:** simplify: applied 1 fix, deferred 1 finding

### The Orphaned-Buffer Discovery

Two independent teammates (quality and efficiency) converged on a high-confidence finding that the narration buffer infrastructure in `App.tsx` was **defined but never called**. I verified with `grep -rn "flushNarrationBuffer" src/` — returns only the definition line, no callers anywhere in the codebase.

**What I learned about the real narration flow:**

Lines 240-245 of the current App.tsx (unchanged by this story):

```tsx
// Narration flows straight into the message feed now that TTS is gone.
if (msg.type === MessageType.NARRATION || msg.type === MessageType.NARRATION_END) {
  setThinking(false);
  setMessages((prev) => [...prev, msg]);
  return;
}
```

The active narration handler bypasses the buffer entirely and pushes messages directly to `setMessages`. The comment on line 240 — "Narration flows straight into the message feed now that TTS is gone" — was written in a previous cleanup pass (not in the current green phase). The buffer has been orphaned since then.

**Implications that surface into the spec audit:**

1. **ADR-076's architect-phase description of the buffer's role was factually wrong.** My own architect-phase audit claimed the buffer "paired a Narration with its terminal NarrationEnd for atomic state_delta flush." No such pairing ever happened at runtime because `flushNarrationBuffer` was never invoked. The buffer was dead code that looked alive because its internal structure referenced real types.
2. **Dev's rewritten buffer doc comment during the green phase inherited that wrong description.** Dev rewrote lines 180-184 from "holds NARRATION, NARRATION_END, and NARRATION_CHUNK messages so text reveals sentence-by-sentence in sync with TTS audio playback" to "pair a Narration with its terminal NarrationEnd for atomic state_delta flush". The new wording was better-motivated but equally inaccurate.
3. **The green-phase `flushNarrationBuffer` simplification was premature.** Dev simplified the function from ~45 lines (handling chunks, watchdogTimer, binary frame handler) to ~23 lines (just narration + narrationEnd). That was based on ADR-076's incorrect premise that the buffer was still doing atomic-flush work. The correct move would have been to delete the entire function — which is what this verify-phase fix does.
4. **Deleting the orphan is the right call.** Verified by the post-fix testing-runner run: `tsc --noEmit` clean, 8/8 27-9 tests still passing, full UI suite holds at exactly 82 failures (delta=0 vs the post-green baseline).

**What the fix did not change:**

- The actual runtime behavior of the UI — the buffer was dead, so deleting it does not change what users experience.
- The 27-9 RED tests — they all still pass, including `App.tsx narration buffer does not carry buf.chunks field` and `App.tsx does not define handleBinaryMessage callback`. Those assertions were about dead tokens the TEA phase asked Dev to remove; the current fix removes the *shell* that held those tokens.
- State delta application — the narration handler at line 240-245 pushes `NARRATION` and `NARRATION_END` as separate messages to the React state; the `useStateMirror` hook at line 222 processes each state delta as it arrives. React may or may not batch the commits — that's up to React's scheduler, not the buffer.

**Was the atomic-flush behavior ever needed?** Probably not. React 18+ automatically batches state updates inside event handlers and network callbacks. Any state delta on a `NarrationEnd` would be applied in the same React commit as the previous `Narration` push regardless of whether they came from one `setMessages` call or two, as long as they happen in the same microtask. The buffer was architectural theater — it looked like it was doing something important but React's own batching made it redundant.

### Why the extraction.rs Finding Was Deferred

simplify-reuse flagged that `strip_combat_brackets()` and `strip_fenced_blocks()` in `sidequest-api/crates/sidequest-server/src/extraction.rs` contain a character-for-character identical 15-line block for blank-line collapsing. I verified the claim by reading both functions — the duplication is genuine and high-confidence.

However, I deferred the fix with these reasons:

1. **Pre-existing, not introduced by 27-9.** Dev only touched `extraction.rs` for two doc comment rewrites (lines 4 and 155). The main body of both functions was never in the story's change set. Applying a DRY refactor there would expand 27-9 into a pre-existing tech-debt area unrelated to narration protocol collapse.
2. **Production Rust code, not cosmetic.** Extracting a helper function requires re-running the full `sidequest-api` workspace test suite against new production code, not just doc comments. The testing cost is not proportional to the story's value.
3. **A follow-up story is the cleaner delivery shape.** This is the kind of finding that should go into a `tech-debt` epic or a "refactor: DRY extraction.rs blank-line collapse" chore story. It's worth doing; it's not worth doing under 27-9's banner.

This is documented below as a Delivery Finding (Improvement, non-blocking) so a future SM can pull it into a follow-up.

### Regression Verification (testing-runner run-id `27-9-tea-verify`)

The pre-fix baseline verify run reported:

| Check | Result | Notes |
|---|---|---|
| `cargo clippy --workspace --all-targets -- -D warnings` | clean + 16 pre-existing errors | Zero new warnings from Dev's doc comment rewrites in prerender.rs and extraction.rs. Baseline was 15 missing-docs on `ConfrontationActor`/`ConfrontationMetric`/`ConfrontationBeat` struct fields plus 1 redundant import in `tactical_state_story_29_5_tests.rs`. All unrelated to 27-9. |
| `cargo test -p sidequest-protocol` | 140 passing, 0 failing | Stable re-run; matches Dev's green-phase count exactly. No flakiness. |
| `npx vitest run` (full UI suite) | **82 failures, down from 94 baseline** | **12-test improvement, not the 6 expected.** The 6 intentional 27-9 RED tests flipped to GREEN (expected), PLUS 6 bonus tests flipped to GREEN as side effects. |

### About the 12-Test Bonus Improvement

The testing-runner speculated one source of the 6 bonus fixes is the `tts_pipeline` color constant deletion in `sidequest-ui/src/components/Dashboard/shared/constants.ts`. That's Keith's pre-existing Option-C WIP that rode along with my TEA-phase test commit (documented in Dev Assessment → Note on Commit Hygiene). **I need to be honest about attribution:** the +6 bonus test fixes are not purely attributable to 27-9 story scope. At least some are a side effect of Keith's accidentally-bundled parallel TTS cleanup in `constants.ts`.

This doesn't change the outcome (12 tests improved, story is better than baseline), but Reviewer should know when reading the metrics.

### Post-Fix Verification (testing-runner run-id `27-9-tea-verify-postfix`)

After applying the simplify fix:

| Check | Result |
|---|---|
| `npx tsc --noEmit` | PASS, zero new errors |
| `npx vitest run src/__tests__/narration-chunk-deletion-27-9.test.ts` | 8/8 passing, unchanged |
| `npx vitest run` (full suite) | **82 failures, delta=0 vs 82-baseline** |

Perfect baseline hold. The simplify fix is safe.

### Simplify Phase Commit

Committed as `a8b4fcf` on `feat/27-9-collapse-narration-protocol` (sidequest-ui) and pushed to origin. Commit message: `refactor(27-9): delete orphaned narration buffer per verify review`. Change summary: 1 file changed, 5 insertions(+), 40 deletions(-).

### Scope Expansion Deviation

See the `### TEA (verify)` entry in the Design Deviations section below. The simplify fix exceeded the original ADR-076 scope (which only asked for a buffer simplification, not a full deletion) because the fix was necessary to resolve a high-confidence finding surfaced by two independent simplify teammates. Scope expansion is in the direction of cleanliness, consistent with the project's "no half-wired features" principle.

### Rule Coverage

Re-ran the lang-review rule check for the verify phase. Same applicability as red phase — this is still a deletion-driven story with minimal new code, so rule #6 (test quality) is the only applicable check.

**Rule #6 (test quality) self-check on the verify-phase change:** the simplify commit deletes code without adding tests. The existing 27-9 test file (`narration-chunk-deletion-27-9.test.ts`) already asserts the absence of `buf.chunks`, `handleBinaryMessage`, and `watchdogTimer` at the source-file level. After the verify-phase fix, those tests still pass — the additional deletion of `narrationBufferRef` and `flushNarrationBuffer` is not directly asserted by any existing test, but a new test to assert their absence would be vacuous because the wiring-check tests (`no production file references NarrationChunk`, `no production file references handleBinaryMessage`) already enforce the broader invariant that all buffer-related TTS-era tokens are gone. No new tests needed; existing coverage is sufficient.

### Delivery Findings Capture

Appended under `### TEA (test verification)` in the Delivery Findings section below.

### Handoff

**To Reviewer (The Argument Professional)** for the **review phase**. Everything is green, simplified, committed, and pushed. Reviewer's focus areas:

1. **The orphaned buffer discovery is a substantive architectural finding.** Please confirm you're comfortable with my interpretation that (a) ADR-076 made an incorrect claim about the buffer's role during the architect phase, (b) the green-phase Dev commit inherited that incorrect claim in the rewritten doc comments, and (c) the correct fix — which I applied — was to delete the buffer entirely rather than simplify it. If you disagree, the fix can be reverted and the story re-handed-back to the architect for a revised ADR.
2. **Read the three subrepo commits:** `6e0da20` (api green), `c1443a1` + `a8b4fcf` (ui green + verify), `b99fcc3` (orchestrator wiring diagram). No PR exists yet — SM creates them during finish.
3. **The pre-existing 82 UI test failures are ambient rot, not story regressions.** They predate 27-9 and none changed state because of my work. Worth a dedicated tech-debt pass in a future sprint, but not a 27-9 blocker.
4. **Keith's Option-C WIP in `constants.ts`** rode along with the ui branch. It's in commit `d17076c` from the red phase. Please verify it doesn't conflict with any other in-flight work before merging, per my red-phase note.
5. **The extraction.rs DRY deferral** is documented as a Delivery Finding below. If you think it should be folded into 27-9 instead of a follow-up, say so and I'll pull it in.

The story is ready. Mr. Praline has verified — and re-verified — that the deceased protocol is demonstrably deceased and that its remains have been cleanly buried.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none at the scoped level; **however** the scoped `cargo build -p sidequest-protocol` missed ambient breakage in sidequest-game that Reviewer caught manually (see F0) | N/A at scoped level; F0 supplemented from manual full-workspace build |
| 2 | reviewer-edge-hunter | No | Skipped | disabled via `workflow.reviewer_subagents.edge_hunter: false` | N/A — domain covered manually |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 2 (1 medium canType; 1 low session_sync wildcard) | 1 confirmed-deferred; 1 dismissed with rationale |
| 4 | reviewer-test-analyzer | No | Skipped | disabled via settings | N/A — domain covered manually |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled via settings | N/A — Reviewer caught F1 manually in this domain |
| 6 | reviewer-type-design | Yes | findings | 2 (1 medium non_exhaustive; 1 low Footnote) | both confirmed, both deferred as pre-existing |
| 7 | reviewer-security | No | Skipped | disabled via settings | N/A — pure-deletion story, no new attack surface |
| 8 | reviewer-simplifier | No | Skipped | disabled via settings | N/A — verify phase already ran simplify fan-out |
| 9 | reviewer-rule-checker | Yes | findings | 1 (low NarrationChunkMessage never-RED) | noted as guard-invariant terminology |

**All received:** Yes (4 enabled subagents returned, 5 disabled pre-filled per settings)
**Total findings:** 6 confirmed (2 applied inline, 4 deferred/noted), 1 dismissed with rationale, 0 errored

## Reviewer Manual Review (disabled subagent domain coverage)

### Edge-hunter domain
- Protocol deserialization: `{"type":"NARRATION_CHUNK",...}` now fails loud with "unknown variant", not silent. VERIFIED.
- Match exhaustiveness: `cargo build --workspace` passes clean after F0 fix — no exhaustive consumer was matching on the removed variant. VERIFIED.
- App.tsx narration path edge cases: straight-through handler at 240-245, no hidden paths. VERIFIED.
- Reconnect path: filter logic unchanged, stale buffer comment updated in verify phase. VERIFIED.

### Test-analyzer domain
Covered per-test by rule-checker's R6/TS8 verification. Both test files have meaningful assertions, correct self-exclusion in wiring walkers, no vacuous patterns.

### Comment-analyzer domain — caught F1
See F1 below. Grep-based scan for phantom atomic-flush claims surfaced two doc comments in message.rs that Dev rewrote based on ADR-076's incorrect premise. Applied fix inline as commit `176ab1f`.

### Simplifier domain
Verify phase already ran the three simplify teammates (reuse, quality, efficiency). Findings applied in `a8b4fcf`. No residual simplification opportunities.

### Security domain
No new attack surface on a deletion story. The Footnote `deny_unknown_fields` gap (F3) is pre-existing information-leak risk of the silent-field-acceptance variety, deferred.

## Ambient Breakage Finding — Rogue `lore.rs` (NOT in 27-9 scope, fixed inline)

**F0 [BUILD] High — FIXED in working tree with Keith's Option A authorization:**

During the reviewer phase, I noticed `?? crates/sidequest-game/src/lore.rs` in `git status --short`. Initial dismissal as "pre-existing WIP" was wrong — Keith asked "what is up with lore.rs?" and I investigated.

The file was a **3,042-line orphaned pre-decomposition monolithic `lore.rs`**, untracked, timestamp 2026-04-10 05:51 (this session's lifetime). Commit `f876bf8` ("refactor(lore): decompose lore.rs into 7 focused submodules") had deleted the file in git history and created the `lore/` directory. Something in an earlier agent session resurrected the monolith — most likely an Edit/Write tool call against the stale `sidequest-game/CLAUDE.md` inventory path that fabricated the file.

**Compile errors:**
1. `error[E0761]` at `lib.rs:39` — module found at both `lore.rs` and `lore/mod.rs`
2. `error[E0282]` at `persistence.rs:678` — transitive type inference failure because `LoreFragment` couldn't be resolved while the `lore` module was broken

**Resolution:** Keith authorized Option A ("delete"). I ran `rm crates/sidequest-game/src/lore.rs`, then verified with `cargo build --workspace` — clean, 5 pre-existing warnings, 0 errors. Both E0761 and E0282 resolved by the single deletion, confirming E0282 was transitive cascade from E0761.

**Process failure:** My reviewer-preflight subagent prompt specified `cargo build -p sidequest-protocol` (protocol crate only) instead of `cargo build --workspace`. Scoped builds silently hide problems in other crates. Memory file `feedback_stale_claude_md_file_fabrication.md` captures the pattern for future sessions; key mitigations: (a) verify paths with `git ls-files` before editing, (b) ALWAYS use workspace-scope builds in preflight/regression checks on cross-repo stories.

**Impact on 27-9 verdict:** The finding is NOT caused by 27-9 (no story changes touch the lore module or persistence.rs). It's ambient infrastructure rot that was exposed during my review. Fixing it was pre-authorized by Keith. The current working tree builds clean, so the 27-9 branches can safely merge.

## Confirmed Findings (27-9 + Ambient)

| # | Tag | File / Location | Severity | Source | Status |
|---|---|---|---|---|---|
| F0 | [BUILD] | `sidequest-game/src/lore.rs` (rogue file, not in git) | High | Reviewer manual catch (after Keith flagged) | **FIXED** — `rm`, workspace builds clean |
| F1 | [DOC] | `sidequest-protocol/src/message.rs` lines 119-123, 458-460 — phantom atomic-flush claims | Medium | Reviewer (comment_analyzer disabled, caught manually) | **APPLIED** inline as commit `176ab1f` |
| F2 | [TYPE] | `sidequest-protocol/src/message.rs` line 98 — GameMessage missing `#[non_exhaustive]` | Medium | `reviewer-type-design` + Reviewer | Deferred — pre-existing, not introduced by 27-9 |
| F3 | [TYPE] | `sidequest-protocol/src/message.rs` line 421 — Footnote missing `#[serde(deny_unknown_fields)]` | Low | `reviewer-type-design` | Deferred — pre-existing inconsistency |
| F4 | [SILENT] | `sidequest-ui/src/App.tsx` narration handler — no `setCanType(true)` on NARRATION_END | Medium | `reviewer-silent-failure-hunter` + TEA verify phase | Deferred — pre-existing, surfaced by deletion; follow-up bug story recommended |
| F5 | [RULE] | `sidequest-ui/src/__tests__/narration-chunk-deletion-27-9.test.ts` line 48 — NarrationChunkMessage never-RED | Low | `reviewer-rule-checker` | Noted — guard invariant, kept in place |

## Dismissed

| # | Tag | Location | Rationale |
|---|---|---|---|
| D1 | [SILENT] | `sidequest-server/src/dispatch/session_sync.rs:229` — `_ => {}` wildcard arm | Intentional design — multiplayer sync handles only message types needing observer fanout; behavior correct-by-design, predates story |

## VERIFIED (line-level evidence)

1. **[VERIFIED]** `GameMessage::NarrationChunk` fully removed — `grep -rn "NarrationChunk" crates/ --include="*.rs" | grep -v _tests` returns zero production hits; only references in test files (expected).
2. **[VERIFIED]** UI narration is straight-through — `App.tsx:240-245` pushes NARRATION/NARRATION_END directly, `grep -rn "flushNarrationBuffer" src/` returns zero hits post-a8b4fcf, `tsc --noEmit` clean.
3. **[VERIFIED]** TEA's wiring walker self-excludes — `narration_collapse_story_27_9_tests.rs:219-225` filters on `*_tests.rs`, `tests.rs`, and paths containing `tests` directory.
4. **[VERIFIED]** UI full suite baseline held at 874 passing / 82 failing — 10 failing files all in unrelated subsystems (useAudio, AudioStatus, TurnStatus*, AudioEngine, gameboard-wiring, GameLayout-resources, ptt-flow-e2e, usePttMicMuting, usePushToTalk).
5. **[VERIFIED]** Full workspace `cargo build --workspace` CLEAN after F0 fix — 5 pre-existing warnings (including `prerender_scheduler` dead field in `sidequest-server/src/dispatch/mod.rs:87`, noted as follow-up), zero errors.
6. **[VERIFIED]** Option-C `constants.ts` WIP is thematically correct — removes stale `tts_pipeline: "#ce93d8"` OTEL span color for a span type that stopped being emitted in Epic 27-1.
7. **[VERIFIED]** `wiring-diagrams.md:251` residual NarrationChunk reference is intentional historical doc inside the `(removed)` section header.
8. **[VERIFIED]** Cross-repo branch merge order doesn't matter — UI never consumed NarrationChunk, so api→ui or ui→api sequencing is safe.
9. **[VERIFIED]** TEA's 27-9 test files match deletion-driven TDD precedent (`combat-overlay-deletion-28-9.test.ts`, `voice-kill-switches-removed.test.ts`).

## Rule Compliance Summary (28 rules, exhaustive)

Full per-instance verification in the `reviewer-rule-checker` output. Summary:
- **Rust 15 rules:** COMPLIANT except R2 (F2 deferred) and one pre-existing R9 inconsistency (F3 deferred). R3/R4/R7/R10/R12/R13 N/A.
- **TypeScript 13 rules:** COMPLIANT except TS8 terminology note (F5). TS3/TS9 N/A.

## Devil's Advocate

Required section. Adversarial argument that this story is broken (200+ words).

**Argument 1 — scope expansion at every phase.** Dev expanded in green (three CLAUDE.md updates, full wiring-diagrams section delete). TEA expanded in verify (deleted the entire narration buffer, not just simplified). Reviewer (me) expanded in review (two doc comment fixes + the F0 lore.rs ambient breakage). Every expansion is individually defensible, but cumulative blast radius exceeds the story header. A hostile reviewer would argue this story should have been split. **Counter:** all expansions were defensive against "no half-wired features." F0 was explicitly authorized by Keith as Option A. Accept.

**Argument 2 — canType bug was the moment to fix it and we didn't.** Both TEA and silent-failure-hunter flagged this. The orphaned `flushNarrationBuffer` contained the only `setCanType(true)` call on the narration path. Deleting it removed the last visible trace that the bug existed. **Counter:** the fix requires confirming server behavior, adding a guarded call, adding test coverage — a new story with its own scope. F4 defers with a recommended follow-up bug story.

**Argument 3 — my own preflight scope failure.** I prompted reviewer-preflight to run `cargo build -p sidequest-protocol` instead of `cargo build --workspace`. That single scoping choice made the preflight blind to the lore.rs ambient breakage that I only caught because Keith asked about an untracked file. If I had missed Keith's question or he hadn't noticed, I would have approved 27-9 while sidequest-game was silently broken. **This is the sharpest criticism the devil's advocate can make against THIS review.** It's not a 27-9 correctness issue — the story itself is clean — but it's a process gap in my own work. Memory captured (`feedback_stale_claude_md_file_fabrication.md`) to prevent recurrence.

**Argument 4 — guard invariant test is vacuous dressed up.** F5 — NarrationChunkMessage test never RED. **Counter:** distinction matters — vacuous catches nothing, guard invariant catches future regressions. Keep.

**Argument 5 — cross-repo merge time bomb.** Three branches, three PRs, no enforced order. **Counter:** VERIFIED #8 confirms any-order merge is safe. Process concern, not correctness concern.

**Did the devil's advocate uncover anything the review missed?** Argument 3 is a legitimate process failure on my part. Memory captured. Not a correctness gap in 27-9 but a lesson for future cross-repo reviews.

## Reviewer Assessment

Tagged observations consolidated from subagent findings and manual domain coverage, in the required `[TAG] description at file:line` format:

- `[DOC]` Phantom atomic-flush contract in NarrationEnd doc comments at `sidequest-api/crates/sidequest-protocol/src/message.rs:119-123` and `sidequest-api/crates/sidequest-protocol/src/message.rs:458-460` — fixed inline as commit `176ab1f`, rewrote to describe straight-through state-mirror processing with React's automatic batching.
- `[TYPE]` GameMessage enum missing `#[non_exhaustive]` at `sidequest-api/crates/sidequest-protocol/src/message.rs:98` — pre-existing, not introduced by 27-9, deferred to tech-debt follow-up story.
- `[TYPE]` Footnote struct missing `#[serde(deny_unknown_fields)]` inconsistency with sibling payloads at `sidequest-api/crates/sidequest-protocol/src/message.rs:421` — pre-existing inconsistency, deferred.
- `[SILENT]` Narration handler bypasses `setCanType(true)` re-enablement at `sidequest-ui/src/App.tsx:240-245` — pre-existing condition surfaced by the deletion; the only live `setCanType(true)` paths are SESSION_EVENT{connected|ready} (line 218) and WebSocket reconnect (line 583). Deferred as a follow-up bug story with manual playtest coverage.
- `[SILENT]` Intentional `_ => {}` wildcard arm at `sidequest-api/crates/sidequest-server/src/dispatch/session_sync.rs:229` — correct-by-design for the multiplayer observer fanout, dismissed with rationale.
- `[TEST]` Guard-invariant test that was never RED at `sidequest-ui/src/__tests__/narration-chunk-deletion-27-9.test.ts:48` — the `NarrationChunkMessage` token was never present in `payloads.ts` before or during the story; test is a legitimate regression guard but violates the strict deletion-TDD "must fail first" contract in terminology only. Noted; kept in place.
- `[TEST]` Rust wiring-check walker correctly self-excludes at `sidequest-api/crates/sidequest-protocol/src/narration_collapse_story_27_9_tests.rs:219-225` — filter on `*_tests.rs`, `tests.rs`, and paths containing `tests` directory. No false positives from the test file scanning its own assertion strings. Rule #6 compliant.
- `[TEST]` TypeScript wiring-check walker correctly self-excludes at `sidequest-ui/src/__tests__/narration-chunk-deletion-27-9.test.ts:141-151` — `findTsFiles()` recursive scan filters `__tests__/` directories and `.test.` files. TS Rule #8 compliant.
- `[EDGE]` Deserialization of stale `{"type":"NARRATION_CHUNK",...}` JSON at `sidequest-api/crates/sidequest-protocol/src/message.rs:98` (GameMessage deserialization entry point) — now fails loud with "unknown variant" error instead of silently dropping the message. Verified via the new `narration_chunk_json_does_not_deserialize_as_game_message` test at `narration_collapse_story_27_9_tests.rs:65`.
- `[EDGE]` Match exhaustiveness over GameMessage at all consumer sites — full workspace `cargo build --workspace` passes clean after F0 fix, proving no exhaustive matcher was relying on `NarrationChunk`. Wildcard arms across the dispatch layer absorb the deletion correctly.
- `[EDGE]` Narration straight-through handler at `sidequest-ui/src/App.tsx:240-245` — no hypothetical `NARRATION_CHUNK` handling needed because the server can no longer emit it; handler correctly processes only NARRATION and NARRATION_END.
- `[EDGE]` Reconnect filter at `sidequest-ui/src/App.tsx:232-236` — unchanged logic, stale "narration buffer" comment updated in verify phase. No edge case in reconnect flow.
- `[RULE]` Rust rule #6 (test quality) compliance verified per-test across all 8 new assertions in `narration_collapse_story_27_9_tests.rs` — meaningful assertions, specific failure messages, no vacuous `let _ = result;` or always-None `is_none()` patterns.
- `[RULE]` TypeScript rule #8 (test quality) compliance verified per-test across all 8 new assertions in `narration-chunk-deletion-27-9.test.ts` with one noted terminology exception (see `[TEST]` F5 above).
- `[RULE]` Rust rules #1, #5, #8, #11, #14, #15 verified compliant — full per-instance enumeration in the `reviewer-rule-checker` report section above; no violations introduced by this story.
- `[BUILD]` Ambient breakage fixed at `sidequest-api/crates/sidequest-game/src/lore.rs` — rogue orphaned file producing E0761 module ambiguity + transitive E0282 in `persistence.rs:678`; deleted with Keith's Option A authorization, full workspace build now clean. Out of 27-9 scope but blocked the review until resolved.

## Verdict

**APPROVE (with two Reviewer-applied fixes).**

- Zero Critical findings.
- One High finding (F0 rogue lore.rs) **FIXED inline** with Keith's Option A authorization. Not caused by 27-9; ambient breakage resolved during review.
- One Medium finding (F1 phantom atomic-flush docs) **APPLIED inline as commit `176ab1f`**. Introduced by this story; would have blocked approval if left unfixed.
- Three findings deferred (F2, F3, F4) — all pre-existing tech debt.
- One finding noted (F5) — terminology.
- One dismissed (D1) — correct-by-design.
- Nine VERIFIED items with line-level evidence.
- 28 rules checked exhaustively.
- Tests: 140 Rust passing, 8 UI 27-9 tests passing, 874 UI total / 82 pre-existing baseline held, `cargo build --workspace` clean post-F0, `tsc --noEmit` clean, clippy pre-existing-only.

**The story is ready for SM finish.**

### Handoff

**To SM (The Announcer)** for the **finish phase** — PR creation, merge coordination, story archival.

**SM should be aware of:**

1. **Four deferred findings** (F2, F3, F4, F5) — all pre-existing or terminology, none blocking. Recommended follow-up chores:
   - Add `#[non_exhaustive]` to growable public enums (GameMessage, NarratorVerbosity, NarratorVocabulary, JournalSortOrder)
   - Add `#[serde(deny_unknown_fields)]` to `Footnote` for sibling consistency
   - Bug story for the canType stuck-at-false condition with manual playtest test coverage
   - Optional: annotate the NarrationChunkMessage guard-invariant test with a comment explaining it never had to fail RED
2. **Reviewer-applied inline fix** — commit `176ab1f` on api branch — needs to be included in the api PR. Already pushed to origin, so SM's PR creation picks it up naturally.
3. **Rogue lore.rs deletion is NOT committed to any branch** because the file was never tracked by git. The deletion only affects Keith's working tree. If the file reappears later (another fabrication event), the memory file `feedback_stale_claude_md_file_fabrication.md` documents the detection pattern.
4. **Cross-repo branch coordination** — three branches on sidequest-api, sidequest-ui, orc-quest. Merge order does not matter. SM creates three PRs in the finish phase.
5. **`sidequest-server/src/dispatch/mod.rs:87` `prerender_scheduler` field never read** — new dead-code warning surfaced by the full workspace build. Out of 27-9 scope; follow-up for Epic 27 cleanup.
6. **Manual playtest acceptance gate from ADR-076 is still outstanding** — Keith has to run a playtest and confirm narration + state deltas apply correctly after merge. Recommended sequence: merge all three PRs → Keith runs playtest → SM archives the story once Keith confirms.