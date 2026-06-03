# Story 73-2: trial: author withdraw/concede resolution beat + opposed_check

**ID:** 73-2 | **Points:** 3 | **Epic:** 73 | **Workflow:** tdd

## Problem Statement

**trial confrontation has no mid-encounter exit, creating a soft-lock risk.** During 67-10 playtest, a player committed the UI-labelled "✦ resolution beat" (Concede Gracefully) in a social_duel. The encounter **did not resolve** — no `encounter.resolved` span in OTEL watcher captures; the confrontation panel persisted; action input remained locked.

**Scope is broader than trial.** The concede/withdraw resolution gap is **NOT trial-only**:
- **REPRODUCED LIVE 2026-05-31 in social_duel** (Glenross / Tea & Murder "Duel of Wits", solo Inspector Pryce, 67-10 playtest).
- Evidence: `.sq-playtest-screenshots/67-10-watcher.jsonl` + `67-10-003-after-resolution.png`.
- social_duel's concede resolution_beat does **not flip `encounter.resolved`**.
- The epic's claim "social_duel made resolvable" appears **VICTORY-PATH ONLY** (resolves on dial→7 dial_threshold, not on concede/early-exit).

**Compounds with 73-4** (push CritSuccess scores 0):
- On the 2026-05-31 concede turn, the crit produced zero dial delta.
- Any terminal/threshold check tied to dial movement never fired.
- 73-4 and this soft-lock reinforce each other.

## Affected Subsystems

- **trial confrontation** — the primary target; requires author withdraw beat + opposed_check conversion (like 73-1 for negotiation/scandal).
- **social_duel confrontation** — reproduced failure; verify concede resolution beat now deterministically flips `encounter.resolved`.
- **negotiation & scandal** — audit that 73-1 fixes actually prevent this; verify concede resolution beats flip `encounter.resolved`.

## Acceptance Criteria

1. **trial confrontation** has an author-committed withdraw/concede **resolution beat** (beat_kind: resolution, push-type or equivalent semantics).

2. **trial's opposed_check is wired** — beat_selection uses opposed_check (not beat_selection with frozen opponent).

3. **A committed resolution beat (concede/withdraw) deterministically flips `encounter.resolved`** to `true` and teardown completes:
   - `encounter.resolved` span emitted to OTEL.
   - Confrontation panel closes / removes from state.
   - Action input unlocks (player can submit next turn).
   - Applies to **trial** + **social_duel** + **negotiation** + **scandal**.

4. **Lethality outcome matches beat semantics:**
   - On withdraw/concede, lethality/harm outcome is neutral or absorbed by the loser's choice (not punitive).
   - Confirm via OTEL span inspection: `confrontation_beat_resolved`, `lethality_applied`, or equivalent telemetry.

5. **No soft-lock after concede:**
   - Player can submit actions on the next turn.
   - Encounter state does not persist in player UI.
   - Verified via playtest or watcher capture inspection.

## Technical Approach

### Phase: RED (TEA)
- Write failing tests that cover:
  - trial confrontation with opposed_check + author withdraw beat.
  - Concede beat committed → `encounter.resolved` flips to `true`.
  - Confrontation panel state clears after concede.
  - Lethality is neutral/absorbed, not punitive.
  - Apply to trial, social_duel, negotiation, scandal via parametrized tests.

### Phase: GREEN (Dev)
1. **Add trial withdraw beat** to `sidequest-content/genre_packs/tea_and_murder/confrations/trial.yaml`:
   - Semantics: author commits to withdraw; lethality is absorbed by the author.
   - beat_kind: `resolution`; action: `push` or `pass` (semantics TBD per ADR-093 balance pass).

2. **Convert trial to opposed_check** (ADR-033 StructuredEncounter pattern):
   - Change beat_selection from frozen-opponent to opposed_check.
   - Follow 73-1's recipe for negotiation/scandal conversion.

3. **Wire up resolution beat teardown** in `sidequest-server`:
   - Locate the confrontation resolution handler (likely in `sidequest/handlers/` or `sidequest/game/confrontation.py`).
   - On `beat_kind == "resolution"` + committed beat, emit `encounter.resolved` span + set `encounter.resolved = true`.
   - Trigger confrontation panel close + action input unlock in narration output (via tool-use protocol).

4. **Audit social_duel's concede beat** (from 67-10):
   - Verify it exists + is resolution-kind.
   - Confirm its handler fires the same teardown logic.
   - If social_duel's concede is broken, apply the same fix.

5. **Audit negotiation + scandal** (from 73-1):
   - Spot-check their opposed_check wiring + concede beat handling.
   - Verify they also flip `encounter.resolved` on concede (not just dial-threshold).

### Phase: SPEC-CHECK (Architect)
- Verify beat semantics align with ADR-093 balance pass (Sebastien/Jade crunch expectations).
- Confirm OTEL spans are present and correctly named.
- Check that lethality outcome is intentional and defensible.

### Phase: VERIFY (TEA) + SIMPLIFY Team
- Lint, typecheck, tests passing.
- Code duplication / extraction review.
- Naming and structural clarity.

### Phase: REVIEW (Reviewer)
- Code review approval.

### Phase: SPEC-RECONCILE (Architect)
- Reconcile any deviations from ADR-093 or playgroup feedback.

## References

- **Epic 73:** Confrontation Engine Hardening
- **Story 73-1:** negotiation + scandal → opposed_check (DONE)
- **Story 73-3:** advance_confrontation lost-update fix (DONE)
- **Story 73-4:** push CritSuccess scores 0 (BLOCKING / COMPOUNDS)
- **Story 73-5:** Suppress re-fired encounter.confrontation_initiated span (follow-up)
- **ADR-033:** Genre Mechanics Engine — StructuredEncounter, opposed_check pattern
- **ADR-093:** Confrontation Difficulty Calibration v1
- **Playtest:** 67-10 (2026-05-31) — social_duel soft-lock reproduced
- **Evidence:** `.sq-playtest-screenshots/67-10-watcher.jsonl`, `67-10-003-after-resolution.png`
- **Repos:** sidequest-server, sidequest-content

## Notes

- **No Jira:** Personal project; skip Jira claim/transition.
- **Dual-repo:** Changes span both sidequest-server (engine) and sidequest-content (trial confrontation YAML).
- **Compound risk:** 73-4 (push CritSuccess=0) means concede crit may produce zero dial delta; fix 73-4 first or in parallel to avoid masking this bug.
- **Playgroup impact:** Jade (mechanics-first author) + Sebastien (mechanics observer) will verify crunch legibility; Jade is extending space_opera and will benefit from reproducible early-exit semantics.
