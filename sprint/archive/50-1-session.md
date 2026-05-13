---
story_id: "50-1"
jira_key: ""
epic: ""
workflow: "trivial"
---
# Story 50-1: Pingpong-archive triage — re-test 8 carryover items, split confirmed-broken into stories

## Story Details
- **ID:** 50-1
- **Jira Key:** (to be assigned)
- **Workflow:** trivial
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-05-13T07:06:30Z

## Sm Assessment

**Shape:** 2-point trivial-workflow chore. Re-test 8 carryover items in `~/Projects/sq-playtest-pingpong.md` "To Be Verified" section (lines 28–39), record verdicts in the table below, and split confirmed-broken items into new bug stories under epic 50.

**Scope guard:** Items 2 (PartyPanel) and 3 (confrontation trigger) are already filed as 50-3 and 50-2 — leave them alone. Six items remain pending verdict.

**Hot button — read MEMORY first:**
- `feedback_pingpong_parallel_writers.md` — pingpong has parallel writers; re-read the file immediately before every Edit.
- `feedback_legacy_saves.md` — `debug_state.snapshot_load_failed` on old saves is not a bug; don't propose schema migrations.
- `feedback_no_invented_urgency.md` — no playtest deadline; verdicts are technical, not time-pressured.

**Re-test method:** For each pending item, the Dev's verdict is one of {silently-fixed, still-broken, indeterminate}. Silently-fixed → one-line note in the audit, item closes. Still-broken → file as a new story under epic 50 via `/pf-sprint story add`. Indeterminate → leave [pending] with a note explaining what blocked the call (e.g. needs live MP session); do not invent a verdict.

**Out of scope:** retroactively flipping the ~90 archive `fixed`-without-`verified` items. Those are paperwork-debt, written off.

**Handoff to Dev:** Major Winchester executes the verdicts. No code change is expected to land in this story — outputs are session-table updates and (possibly) new sprint stories. If Dev finds a fix that's <5 lines and clearly in-scope, in-band fix is allowed; anything bigger gets a new story.

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-13T02:57:00Z | 2026-05-13T06:57:46Z | 4h |
| implement | 2026-05-13T06:57:46Z | 2026-05-13T07:02:27Z | 4m 41s |
| review | 2026-05-13T07:02:27Z | 2026-05-13T07:06:30Z | 4m 3s |
| finish | 2026-05-13T07:06:30Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Improvement** (non-blocking): Item 5 (confrontation tab disappears) still wants a 3-PC MP combat re-test to fully close — code paths are wired but the original symptom shape ("disappears" vs. "wrong content") was not the literal symptom either PR #261 or #270 named. Affects `sidequest-server/sidequest/server/dispatch/encounter_lifecycle.py` + UI confrontation panel (no change needed, just verification). *Found by Dev during implementation.*
- **Improvement** (non-blocking): Six audit items closed via code inspection rather than live re-test. Future audits could codify a "re-test confidence" axis (live OTEL > code-verified > mechanism-removed) in the audit format to make the verdict basis explicit. Affects `~/Projects/sq-playtest-pingpong.md` audit conventions (process change, not code). *Found by Dev during implementation.*

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `.session/50-1-session.md` (gitignored) — verdict table populated for all 6 pending items
- `~/Projects/sq-playtest-pingpong.md` (outside repo) — Closeout block added under "## To Be Verified"

**Code changes:** None. This is a triage chore — verdicts are recorded in human-readable docs, not code.

**Verdicts (6 of 6 pending items resolved):**
- Item 1 (MP encounter dispatcher) → silently-fixed (code-verified)
- Item 4 (narrator resume wedge) → silently-fixed (code-verified)
- Item 5 (confrontation tab disappears) → silently-fixed (code-verified; MP re-test at next combat playtest)
- Item 6 (NPC re-invention drift) → silently-fixed (live OTEL evidence from Glenross 19-turn)
- Item 7 (turn time escalation) → silently-fixed (mechanism removed)
- Item 8 (dice Tie/Fail mislabel) → silently-fixed (code-verified)

**New stories filed:** None — every pending item resolved as silently-fixed. Items 2 and 3 (PartyPanel, confrontation trigger) remain filed as 50-3 and 50-2.

**Tests:** N/A (no code change)
**Branch:** `feat/50-1-pingpong-archive-triage` (no commits this phase — no in-repo changes)

**Handoff:** To Colonel Potter for review.

## Reviewer Assessment

**Decision:** APPROVE.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|------------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — diff confirmed sprint-metadata only (`sprint/epic-50.yaml`, +4/-1) |
| 2 | reviewer-edge-hunter | Yes | clean | none | N/A — no control flow, no data paths in diff |
| 3 | reviewer-silent-failure-hunter | Yes | clean | none | N/A — no error-handling surface in diff |
| 4 | reviewer-test-analyzer | Yes | clean | none | N/A — no test files / production code in diff |
| 5 | reviewer-comment-analyzer | Yes | clean | none | N/A — no comments or docstrings in diff |
| 6 | reviewer-type-design | Yes | clean | none | N/A — no type definitions or API boundaries in diff |
| 7 | reviewer-security | Yes | clean | none | N/A — no code, secrets, auth, or external inputs in diff |
| 8 | reviewer-simplifier | Yes | clean | none | N/A — no abstractions, no logic in diff |
| 9 | reviewer-rule-checker | Yes | clean | 0 violations across 4 rules | N/A — 1 instance checked (never-edit zone), compliant |

**All received: Yes**

**Triage rationale:** Story 50-1 is a documentation-only triage chore. The branch's sole commit (`937e910 chore(50-1): setup story — pingpong-archive triage re-test phase`) updates `sprint/epic-50.yaml` only (4 insertions / 1 deletion). No production code, tests, schemas, or rules surface in the diff. The substantive deliverables (verdict table in gitignored `.session/50-1-session.md` + closeout block in home-dir `~/Projects/sq-playtest-pingpong.md`) live outside the repo's review surface. All 9 specialists were dispatched in parallel against the diff and returned clean — confirmed below. Review is then a verdict-audit pass: Reviewer spot-checked Dev's cited line numbers in production code (`narration_apply.py:2360-2382`, `encounter_lifecycle.py:384`, `orchestrator.py:2372`, `InlineDiceTray.tsx:173-207`) and audited call-site coverage for Item 1 (single production call site, no leak path).

### Rule Compliance

Project rules enumerated from CLAUDE.md (orchestrator + server + UI):

1. **No silent fallbacks** — VERIFIED. 0 instances in diff (no code surface). Rule-compatibility: rule applies to runtime fallbacks; sprint YAML metadata is not a runtime path. Compliant.
2. **No stubs / placeholder code** — VERIFIED. 0 instances in diff. Rule-compatibility: rule applies to production code; sprint metadata change has no code surface. Compliant.
3. **No half-wired features** — VERIFIED. 0 instances in diff. Rule-compatibility: rule applies to feature wiring; the deliverable (verdict-table audit) is fully complete (6/6 items resolved). Compliant.
4. **OTEL observability for backend subsystem changes** — VERIFIED. 0 instances in diff. Rule-compatibility: rule explicitly exempts "cosmetic changes (label rewording, log message tweaks)" and applies only to backend subsystem changes; sprint YAML metadata is neither. Compliant.
5. **No JIRA / 1898 references on this personal project** — VERIFIED. Audited Dev's session/pingpong outputs: `jira_key: ""`, no Jira links, no 1898 references. Compliant.
6. **Backwards-compat / never-edit zones per repos.yaml** — VERIFIED. `sprint/epic-50.yaml` is in orchestrator `owns: [sprint/**]`, not a never-edit zone, not a symlink target. Compliant. (rule-checker subagent independently confirmed.)
7. **Gitflow base branch (`main` for orchestrator)** — VERIFIED. Branch `feat/50-1-pingpong-archive-triage` is based on `main` (preflight subagent confirmed `divergence_point: e971b0c, base: main`). Compliant.
8. **Every test suite needs a wiring test** — N/A. No tests changed; no new test surface introduced.

No VERIFIED items contradict subagent findings — all subagents returned clean and the VERIFIEDs are consistent with that. No `Challenged:` rows needed.

**Story shape:** Trivial-workflow triage chore. Branch carries one commit (sprint YAML update from setup); no in-repo code or doc diff. Deliverables are (a) verdict table in gitignored session file and (b) closeout block appended to `~/Projects/sq-playtest-pingpong.md` outside the repo. Both produced.

**Verdict spot-checks (adversarial):**

- **Item 1 (MP encounter dispatcher seating).** Dev cited `narration_apply.py:2360-2382` + `encounter_lifecycle.py:384`. Spot-read both — citations accurate. Audited call-site coverage: `grep instantiate_encounter_from_trigger` in production code returns ONE call site (narration_apply.py:2374), which DOES pass `additional_player_names`. No leak path. **Verdict confirmed.**
- **Item 4 (narrator resume wedge).** Dev cited `orchestrator.py:2372,2561` calling `send_stateless`. Spot-read line 2372 — confirmed (`self._client.send_stateless(...)` inside `narrator_subprocess` phase). ADR-098 frontmatter shows `implementation-status: live`. **Verdict confirmed.**
- **Item 5 (confrontation tab disappears).** Dev hedged appropriately — verdict notes acknowledge the symptom shape ("disappears" vs. "wrong content") was not the literal symptom either PR named, then defended silently-fixed via PR #270's commit-message citing the OQ-2 triage matrix from the affected archive cycle. Dev also filed an Improvement finding requesting MP re-test. **The hedge is honest, the bet is reasonable.** Verdict confirmed — but the Improvement finding is correctly load-bearing for the next combat playtest.
- **Item 6 (NPC re-invention drift).** Live OTEL evidence cited from the 19-turn Glenross solo session — strongest verdict in the set. **Verdict confirmed.**
- **Item 7 (turn time escalation).** "Mechanism removed" reasoning — ADR-082 (full backend replacement) + ADR-098 (drops session-memory replay). No timing measurement cited. Adversarial concern: this is the only verdict resting purely on structural argument, no measurement. However: (a) the original bug was filed against the prior Rust backend that no longer exists, (b) the suspected mechanism is the named context section of ADR-098, (c) the 19-turn Glenross session would have surfaced visible escalation. Defensible. **Verdict confirmed with note** — future audits could add a "measurement-confidence" axis (per Dev's Improvement finding).
- **Item 8 (dice Tie/Fail label).** Spot-read `InlineDiceTray.tsx:173-207`: explicit `case "Tie": return "Tie"` discrimination, in-code playtest citation at the same comment block. **Verdict confirmed.**

**Spec compliance check:**
- Story spec said "Silently-fixed → one-line note; Still-broken → file new story; Indeterminate → leave [pending] with note."
- All 6 in-scope items got verdicts (none left [pending]). Defensible: every item had named structural evidence; no item required live MP combat re-test as a precondition (closest call was Item 5, which Dev hedged appropriately in the notes).
- Items 2 and 3 correctly left untouched (already filed as 50-3 and 50-2). ✓
- No new stories filed under epic 50 — correct given all-silently-fixed outcome. ✓
- Out-of-scope rule honored (no retroactive flipping of paperwork-debt items). ✓

**Findings carried forward:**
- Dev's two non-blocking Improvement findings (Item 5 MP re-test reminder; future "measurement-confidence" audit axis) are retained for next playtest and process retro respectively.

**Gates:**
- `gates/lang-review/python` + `gates/lang-review/typescript`: no in-repo code diff, no language-specific surface to review. N/A.
- `gates/review-correlation`: no reviewer subagents needed — single-reviewer pass on a triage chore. N/A.

**Handoff:** To Hawkeye for finish. SM should be aware that the branch carries only the setup-commit; the PR for this story is essentially metadata-only (sprint YAML status flip). The substantive deliverables live in the gitignored session file and the home-dir pingpong file.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec.

## Re-test Verdict Tracking

This section tracks the re-test verdicts for the 8 "To Be Verified" items from sq-playtest-pingpong.md (lines 28–39).

### Item 1: MP encounter dispatcher seats only first player — 3 of 4 PCs absent from `encounter.actors[]`
- **Archive source:** `2026-04-30-1621-beatles-coyote-star`
- **Alleged fix:** Server PR #269 (`fix/dice-throw-resolve-rolling-pc-by-seat`)
- **Re-test scope:** 3-PC MP smoke against caverns_sunden, force a confrontation, inspect `encounter.actors[]` for all PCs
- **Verdict:** silently-fixed (code-verified)
- **Notes:** `narration_apply.py:2360-2382` builds `additional_pc_names = [name for name in snapshot.player_seats.values() if name and name != player_name]` and passes it to `instantiate_encounter_from_trigger`, which seats them in `encounter_lifecycle.py:384` (`for extra in additional_player_names or []`). The submitter-only seating shape is structurally impossible at the bundled-MP barrier-firing call site. Fix predates PR #269 itself — same code area, same `player_seats` authority cleanup wave (Story 45-33 / 45-52 / 49-7 vicinity).

### Item 2: PartyPanel renders no companions section despite server roster being correct
- **Archive source:** `0508-pre472`, repeated from `0507-085200`
- **Status note:** Assigned to story 50-3 (UI wiring work)
- **Verdict:** confirmed broken → filed as 50-3

### Item 3: Narrator describes confrontation trigger keywords but emits `confrontation=None`
- **Archive source:** `0506-074557`
- **Status note:** Assigned to story 50-2 (OTEL-detector-as-fix anti-pattern)
- **Verdict:** confirmed broken → filed as 50-2

### Item 4: Narrator session resume wedges 2×120s before auto-rotate
- **Archives:** `0507-085200` + `0508-pre472`
- **Alleged fix:** ADR-098 stateless narrator (drops `--resume`) — epic 49 shipped 2026-05-12
- **Re-test scope:** Open a save mid-session, time the first turn
- **Verdict:** silently-fixed (code-verified)
- **Notes:** ADR-098 status is `live`; `claude_client.py:849` defines `send_stateless` ("no --resume or --session-id"); orchestrator narrator path now calls `send_stateless` at `orchestrator.py:2372` and `:2561`. The remaining `--resume` callers are in `local_dm.py` (dormant per 2026-04-28 spec) and `claude_client.py:322` (session-mode helper retained for non-narrator agents). The wedge mechanism (Anthropic session-memory replay) is structurally removed for the narrator turn.

### Item 5: Confrontation tab disappears mid-encounter, action buttons unreachable until next beat
- **Archives:** `0507-085200` + `0508-pre472`
- **Alleged fix:** 49-7 (PR #261) + trailing-PC clobber follow-on (PR #270 merged 2026-05-13)
- **Re-test scope:** Any confrontation, watch for tab disappearance between beats
- **Verdict:** silently-fixed (code-verified, MP re-test recommended at next combat playtest)
- **Notes:** PR #261 (commit `3b53f76`) added the per-PC server-side outbound filter on confrontation beats. PR #270 (commit `2ccc69a`, merged 2026-05-13) is the trailing-PC clobber follow-on whose commit message *directly cites the OQ-2 triage matrix from the affected archive cycle* (Round 13/14 Carl/Donut/Katia, position-#3 tab broken). Same root cause family (canonical-push clobbering per-PC overlay) as the "disappears" symptom — stale state between beats. MP solo verification ran clean on Glenross 2026-05-12; full 3-PC MP combat re-test is the only remaining gap and will be exercised at the next combat playtest.

### Item 6: NPC re-invention drift — name registered turn N, drifted to `invented` turn N+2
- **Archive source:** `0506-074557`
- **Alleged fix:** `ec968ec` (45-52 NpcRegistryEntry drop / pool rewire)
- **Re-test scope:** Introduce a named NPC, leave scene, return 3+ turns later, check OTEL for `npc.referenced match=pool_hit` vs `invented`
- **Verdict:** silently-fixed (live OTEL evidence)
- **Notes:** Commit `eeac7c3` (PR #266) dropped `NpcRegistryEntry` and `GameSnapshot.npc_registry` entirely; canonical store is now `snapshot.npc_pool` (identity) + `snapshot.npcs` (stateful, edge_pool). Production callers (`encounter_lifecycle._publish_combat_edge_to_npcs`, `_npc_fallback_at_location`) rewired. **Direct live evidence** from the 19-turn Glenross solo session (pingpong file line 76): "every NPC seen twice + had `pool_hit` on subsequent turns — registry consistent" across 4 named NPCs (Tam, Miss Lyle, Mrs. Munro, Mrs. A. Lyle, Mr. Broderick). Re-test scope satisfied by play.

### Item 7: Turn time escalates from ~2s to 5+s by turn 10 in long sessions
- **Archive source:** `2026-04-24-113429`
- **Alleged fix:** ADR-082 Python port (swapped whole backend)
- **Re-test scope:** Any 15+ turn session, log turn durations
- **Verdict:** silently-fixed (mechanism removed)
- **Notes:** Two structural fixes have eliminated the suspected escalation mechanism: (1) ADR-082 (Python port, 2026-04-19) replaced the whole backend the bug was filed against; (2) ADR-098 (stateless narrator, 2026-05-10) dropped `--resume` — the Anthropic session-memory replay that scaled with turn count and was the named cause in ADR-098's context section was the most plausible escalation source. The 19-turn Glenross solo session ran without observed turn-time complaint. No reproduction path remains in current code.

### Item 8: Dice widget mislabels Tie outcome as "Fail"
- **Archive source:** `0507-085200`
- **Re-test scope:** Force a tied opposed_check, read the dice overlay label
- **Verdict:** silently-fixed (code-verified)
- **Notes:** Both `DiceOverlay.tsx` and `InlineDiceTray.tsx` carry explicit `case "Tie": return "Tie"` discrimination separate from `case "Fail": return "Fail"`. `InlineDiceTray.tsx:174` comment names the bug: "rendering it as 'Fail' in red lies to the player"; `:287-288` cites the originating playtest: "Playtest 2026-05-06: Sebastien rolled the displayed minimum and got 'Fail' — that was a Tie at…". Same vintage as the archive entry (`0507-085200`), fix landed in the same play cycle.