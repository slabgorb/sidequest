# Anthropic SDK Migration — Phase E: Merge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Updates 2026-05-15 (post-Phase-D):** This plan was drafted before Phases A-D executed. Several deltas now apply:
>
> 1. **ADR numbering:** The plan was written assuming the parent ADR would land as ADR-099. It actually merged as **ADR-101** (commit 3485073). Successor ADRs shifted accordingly:
>    - "ADR-099" (this plan's old name for the parent) → **ADR-101** Anthropic SDK as Narrator Backend
>    - "ADR-100" Tool-Use Protocol → **ADR-102**
>    - "ADR-101" Native OTEL via Tool Registry → **ADR-103**
>    - "ADR-102" Perception Filtering at the Tool Layer → **ADR-104**
>
>    Every reference below has been rewritten to the current numbers. ADR-099 (coyote-object-salvage-hooks) and ADR-100 (journal-pipeline-coherence) are unrelated and already merged.
>
> 2. **Phase D did NOT delete the sidecar parser, perception rewriter, or OTEL scraper.** Each "deletion" target turned out to be misread (see Phase D plan §Updates and successor ADR bodies for details):
>    - `sidequest/agents/perception_rewriter.py` — load-bearing for MP fan-out (status-effect fidelity override on broadcast). Survives.
>    - `sidequest/agents/claude_stream_parser.py` — Claude CLI NDJSON parser, not the ADR-039 sidecar parser. Survives.
>    - ADR-058 "stderr scraping" — never existed; ADR-058's mechanism is env-var passthrough, which survives for auxiliary callers.
>    - The actual ADR-039 sidecar parser (`extract_structured_from_response` in `sidequest/agents/orchestrator.py`, plus `stream_fence.py` for the streaming variant) is still live because Phase C did NOT retire the `narrator_output_only` injection in `NarratorAgent.build_output_format` — the narrator prompt still asks the model to emit a `game_patch` sidecar, and the SDK path's `_assemble_turn_result` still parses it.
>
>    Phase E's PR bodies and merge ceremony are updated below to reflect this. The "Retires:" list in the original draft was aspirational; the actual end-of-Phase-D state is "SDK path is wired and is the default backend; legacy parsers coexist."
>
> 3. **Two follow-up stories should be scoped before, or immediately after, the Phase E merge** (depending on whether you want the migration to be "complete" at merge):
>    - **Drop `narrator_output_only` on the SDK path.** Either gate the injection behind backend identity (only inject for ClaudeClient) or rewrite it to instruct the model to use tools instead of sidecars.
>    - **Tolerate sidecar-free output in `_assemble_turn_result`.** Currently the function relies on `extract_structured_from_response`; on the SDK path it should fall back to a tool-call ledger from `ToolingResult.tool_calls` to populate `NarrationTurnResult`.
>
>    Without these, the SDK path's structural lie-detection benefit (ADR-103) is partially compromised — the model can hedge by emitting both sidecars and tool calls, and downstream code reads whichever shows up.
>
> 4. **Scene harness CLI does not exist.** `sidequest.cli.scene_harness` was referenced in the plan's parity-capture commands but is HTTP-only (lives at `sidequest.server.scene_harness_router`). Task 1/2 baseline capture either needs a thin CLI wrapper added first, or the work happens by driving the HTTP endpoint from a script. See Task 1.2 below for the corrected approach.
>
> 5. **35 pre-existing baseline test failures** in `tests/server/test_chargen_dispatch.py` (16), `tests/server/test_scene_harness.py` (12), and `tests/game/test_scene_harness_hydrator.py` (7) exist on `develop` and persist on the feature branch. They are NOT introduced by the migration. Task 8.1 review should treat them as baseline.

**Goal:** Take `feat/anthropic-sdk-migration` from "feature-complete on the branch" to merged on `develop` in both the server and orchestrator repos. Three gates: (1) scenario baseline parity against pre-migration recordings; (2) one live playgroup session on the feature branch; (3) clean squash-merge with ADR status flips.

**Architecture:** No code changes; this phase is validation + ceremony. The only commit on the feature branch itself is the post-merge ADR-status flip (which happens *after* squash-merge to `develop`).

**Tech Stack:** Same as Phases A-D.

**Scope:** Phase E only — 3 stories (E1-E3, 7 pts). Phases A-D must all be merged to the feature branch before this plan starts. After this phase, the migration is done; later epics (genre-pack-specific tool catalogs, batch-API between-scene work) start as fresh tracks.

**Branches:** `feat/anthropic-sdk-migration` in `sidequest-server/` and `orc-quest/`.

---

## File Structure

**Created:**
- `sidequest-server/scenarios/baseline-recordings/<scenario>.jsonl` — one recording per `scenarios/*.yaml`, captured from the *pre-migration* `claude -p` path before the feature branch began
- `docs/superpowers/playtest-reports/2026-MM-DD-anthropic-sdk-migration-acceptance.md` — short report of the E2 playgroup session

**Modified (post-merge):**
- `docs/adr/101-anthropic-sdk-as-narrator-backend.md` — `status: accepted`
- `docs/adr/102-tool-use-protocol-for-structured-output.md` — `status: accepted`
- `docs/adr/103-native-otel-via-tool-registry.md` — `status: accepted`
- `docs/adr/104-perception-filtering-at-the-tool-layer.md` — `status: accepted`
- `docs/adr/001-claude-cli-only.md` — `status: superseded` (was already implicitly via ADR-101's `supersedes: [1, 39, 58, 28]`; this confirms in the frontmatter)
- `docs/adr/039-narrator-structured-output.md` — `status: superseded`
- `docs/adr/058-claude-subprocess-otel-passthrough.md` — `status: superseded` (note: the env-var passthrough mechanism stays live for auxiliary ClaudeClient callers; superseded means "no longer load-bearing for the narrator path")
- `docs/adr/028-perception-rewriter.md` — `status: superseded` (note: the deterministic span-strip in `perception_rewriter.py` stays live for MP fan-out per ADR-104; superseded refers to ADR-028's *envisioned* LLM rewriter, which the codebase never had)
- `docs/adr/README.md` — regenerated index

---

## Self-Review (pre-execution)

Spec coverage:
- E1 (run all `scenarios/*.yaml`; capture baselines) → Tasks 1-2
- E2 (live playgroup session on feature branch) → Tasks 3-5
- E3 (code review, squash-merge to develop, deploy) → Tasks 6-9

Note on baselines: ideally these were captured *before* the feature branch began (and certainly before Phase C began modifying the prompt). If they weren't, capture them now by checking out `develop` and running the harness — see Task 1.

Placeholder scan: every step lists specific commands or specific decisions.

---

## Task 1 — Capture pre-migration baselines (if not already)

If baselines were captured before Phase C, skip to Task 2. Otherwise:

- [ ] **Step 1.1: Stash current work**

Per [[feedback_commit_dont_stash]] (memory), **do not** `git stash`. Instead, commit any WIP and create a short-lived comparison branch:

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git status  # confirm clean
git checkout develop
git pull --ff-only origin develop
```

- [ ] **Step 1.2: Run every scenario against the pre-migration `claude -p` path**

**Note (2026-05-15 update):** `sidequest.cli.scene_harness` does NOT exist. The scene harness is HTTP-only via `sidequest.server.scene_harness_router` (per ADR-092 dev-gated endpoint). Two options:

**Option A — add a thin CLI shim** (preferred if the harness CLI will be reused for parity tests beyond this migration). Create `sidequest/cli/scene_replay.py` that boots an in-process FastAPI test client, POSTs each scenario fixture to `/scene/load`, drives turn input via the harness, and writes the resulting span tree + event log to a JSONL file. ~50 LOC; mirrors how `test_scene_harness.py` drives the endpoint today.

**Option B — drive via curl** (faster, throwaway). Boot the dev stack against `develop`, then loop:

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
SIDEQUEST_LLM_BACKEND=claude SIDEQUEST_DEV_SCENES=1 uv run uvicorn sidequest.server.app:app --port 8765 &
SERVER_PID=$!
mkdir -p scenarios/baseline-recordings
for f in scenarios/*.yaml; do
    name=$(basename "$f" .yaml)
    curl -sX POST http://localhost:8765/scene/load -F "fixture=@$f" -o "scenarios/baseline-recordings/${name}.scene-load.json"
    # Drive scripted turns via /scene/turn-input or whatever the router exposes;
    # capture stdout/log/OTEL into the JSONL file via the GM dashboard
    # SSE feed at /otel/stream
done
kill $SERVER_PID
```

The detailed driver script is out of scope for this plan — write it as the first task of Phase E1 and commit it to `sidequest-server/scripts/scene_replay.sh` (or `.py`) so it can be reused for future migrations.

If neither option works because the playgroup hasn't recorded baselines from `develop` yet, the scenario-parity gate (Task 2) becomes a "spot-check the SDK runs produce sane span trees" judgment call rather than a diff-against-baseline check. Document explicitly which gate is being applied.

- [ ] **Step 1.3: Commit baselines to develop**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git add scenarios/baseline-recordings/
git commit -m "test(scenarios): capture pre-migration baselines for Phase E parity

Recorded against claude -p on develop. Used by the feature branch's
Phase E acceptance to detect structural drift in mechanical events,
state transitions, and beat sequencing.

The branch matches recordings, not narration prose — narration is
expected to differ within tolerance."
git push origin develop
```

- [ ] **Step 1.4: Back to the feature branch**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git checkout feat/anthropic-sdk-migration
git merge develop --no-edit  # or rebase per branch-hygiene preference
```

Resolve any conflicts.

---

## Task 2 — Run scenario parity on the feature branch

- [ ] **Step 2.1: Run every scenario against the SDK path**

Per the Task 1.2 update, scene-harness CLI does not exist. Use the same script/HTTP-driver approach with `SIDEQUEST_LLM_BACKEND` unset (so the default `anthropic_sdk` is picked, per Phase D Task 2):

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
unset SIDEQUEST_LLM_BACKEND
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY SIDEQUEST_DEV_SCENES=1 uv run uvicorn sidequest.server.app:app --port 8765 &
SERVER_PID=$!
mkdir -p /tmp/sdk-migration-runs
# Same loop as Task 1.2; write to /tmp/sdk-migration-runs/
kill $SERVER_PID
```

If `scripts/scene_replay.sh` was added in Task 1.2, use it here.

- [ ] **Step 2.2: Diff each pair**

`scene_harness --diff` doesn't exist either. Diff at the JSONL level — focus on the OTEL event sequence (tool calls, write spans, state-patch payloads), not on narration prose:

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
for baseline in scenarios/baseline-recordings/*.jsonl; do
    name=$(basename "$baseline" .jsonl)
    migrated="/tmp/sdk-migration-runs/${name}.jsonl"
    echo "=== $name ==="
    # Pull the event-kind sequence from each and diff
    jq -r '.event_kind // .span_name // empty' "$baseline" > /tmp/baseline-events.txt
    jq -r '.event_kind // .span_name // empty' "$migrated" > /tmp/migrated-events.txt
    diff /tmp/baseline-events.txt /tmp/migrated-events.txt || echo "STRUCTURAL DIFFERENCE in $name"
done
```

The baseline used the sidecar parser (one extraction span per turn); the SDK path uses `tool.*.*` spans (multiple per turn). Some differences are expected and good — the diff is for catching *missing* events on the SDK side that the baseline had, not extra tool spans the SDK gained.

Acceptance criteria per scenario:
- Same set of mechanical events fired (dice rolls, state patches, status applications)
- Same beat transitions occurred in the same order
- Same scenario clues advanced
- Narration prose may differ; narration *length* within ±30% of baseline
- Tool call count per turn within tolerance (combat turns may use 4-6 tools; baseline used 0 because tools didn't exist — accept as expected)

- [ ] **Step 2.3: Triage failures**

For each scenario with a structural difference, decide:
- **Genuine regression** → fix the offending tool or filter (return to Phase C); do not proceed
- **Acceptable drift** (e.g., better tool selection produces a different but valid mechanical sequence) → document in the playtest report
- **Baseline bug** (the old path was wrong) → document in the playtest report

- [ ] **Step 2.4: Capture cost telemetry**

The scenarios are the cheapest way to validate spec §Success criteria #7 ("Per-turn cost telemetry shows weighted average $0.05-0.07").

`--cost-rollup` doesn't exist as a CLI flag. Compute the rollup from the JSONL files with a one-liner:

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
jq -s '
  [.[] | select(.span_name == "narration.turn") | .attributes."narration.turn.total_cost_usd"]
  | add / length
' /tmp/sdk-migration-runs/*.jsonl
```

Expected: weighted-average `narration.turn.total_cost_usd` in range $0.05-0.07. If higher, investigate cache hit rate:

```bash
jq -s '
  [.[] | select(.span_name == "narration.turn")
   | (.attributes."narration.turn.cache_read_tokens" / .attributes."narration.turn.total_input_tokens")]
  | add / length
' /tmp/sdk-migration-runs/*.jsonl
```

should average ~60% per spec §Slim prompt target.

- [ ] **Step 2.5: Commit run results**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
# Don't commit the /tmp runs — those are ephemeral. Just commit any fix
# commits Step 2.3 may have produced, if any.
```

---

## Task 3 — Pre-session checklist (live playgroup acceptance)

Before scheduling the playgroup session:

- [ ] **Step 3.1: Confirm Phase D end-of-phase still green**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest -q
cd /Users/slabgorb/Projects/oq-1/
just check-all
```

The expected baseline is 5871 passed + 35 failed (the pre-existing test_chargen_dispatch / test_scene_harness / test_scene_harness_hydrator failures listed in the header preamble). Any *new* failure here means Phase D drifted or a `develop` change collided with the feature branch — investigate before continuing.

- [ ] **Step 3.2: Verify `ANTHROPIC_API_KEY` is configured on the play machine**

```bash
echo "${ANTHROPIC_API_KEY:0:7}..."  # should print the key prefix; if empty, configure before session
```

- [ ] **Step 3.3: Set cost-alert threshold**

For the live session, add a transient watchdog. Verify the live cost-telemetry alert from spec §Risks fires correctly. A simple smoke check: run two scenarios with the harness while watching the GM panel; confirm `narration.turn.total_cost_usd` appears in spans.

- [ ] **Step 3.4: Confirm the playgroup is briefed**

Per spec §Approach B, the playgroup plays on `develop` until merge. The Phase E2 session is the *one* time they play on the feature branch. Brief them: "We're testing the new backend — if anything feels weird, tell us. Save state at end of session goes to /tmp; cleanup happens after we merge."

The session expectation is *acceptance*, not soft-launch. If it goes badly we revert.

---

## Task 4 — Run the playgroup session on the feature branch

- [ ] **Step 4.1: Make sure the feature branch is the running code**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git branch --show-current  # should be feat/anthropic-sdk-migration
cd /Users/slabgorb/Projects/oq-1/
git branch --show-current  # should be feat/anthropic-sdk-migration
```

- [ ] **Step 4.2: Boot the stack**

```bash
cd /Users/slabgorb/Projects/oq-1/
just down  # in case anything stale is running
just up
```

Tail the logs in a second pane:
```bash
just logs
```

- [ ] **Step 4.3: Run the session**

Run a normal-length session (target ~2-4 hours, 100-250 turns). Monitor:
- Narration quality (Keith's gut check — "still SideQuest?")
- Tool-call rate sanity (spec §Slim prompt target → 1-3 tool calls per typical turn; 4-6 on combat turns)
- Cost rollup (target average $0.05-0.07/turn)
- Cache hit rate (target ~60% after warmup)
- Any errors or surprises

Take notes in real time on:
- Any turn that felt off (tool selection, narration tone, mechanical accuracy)
- Any tool that fired when it shouldn't have, or didn't fire when it should have
- GM panel readability — does the new span tree make sense?
- Cost vs. spec target

- [ ] **Step 4.4: Preserve the session save**

After the session ends, copy the save file out of `~/.sidequest/saves/` to a versioned location:
```bash
cp ~/.sidequest/saves/<genre>_<world>.db ~/.sidequest/saves/anthropic-sdk-migration-acceptance-$(date +%Y-%m-%d).db
```

This is the artifact that proves the session ran.

---

## Task 5 — Playtest report

- [ ] **Step 5.1: Write the playtest report**

Create `docs/superpowers/playtest-reports/2026-MM-DD-anthropic-sdk-migration-acceptance.md`:

```markdown
# Anthropic SDK Migration — Phase E Acceptance Playtest

**Date:** YYYY-MM-DD
**Genre / world:** <which one was used>
**Duration:** <hours>
**Turns:** <count>
**Players present:** <names>

## Outcome

<one-paragraph summary: did Keith feel it was "still SideQuest"? Did the playgroup notice the change?>

## Cost telemetry

- Average per-turn cost: $X.XX (target $0.05-0.07)
- Cache hit rate (cache_read / total_input): X% (target ~60%)
- Tool calls per turn: <average>; combat turns <average>; quiet turns <average>
- Total session cost: $X.XX

## Mechanical accuracy

<List any cases where narration claimed a mechanical effect that didn't fire (tool.write.* span missing), or where a tool fired without corresponding narration. Phase D made these structurally detectable — the playtest is the first chance to see them in the wild.>

## Tool selection observations

<For each tool the model used heavily or surprisingly: short note. For tools that *didn't* fire when they should have: short note.>

## Issues found

<Numbered list. Each item: severity, repro hint, decision (fix-before-merge / fix-post-merge / accept).>

## Decision

- [ ] Merge to develop
- [ ] Hold and fix issues N, N, N before merge
- [ ] Revert — abandon branch, restart
```

- [ ] **Step 5.2: Commit the report**

```bash
cd /Users/slabgorb/Projects/oq-1/
git add docs/superpowers/playtest-reports/
git commit -m "docs(playtest): Phase E acceptance session report

<Two-line summary: what the session showed; merge decision.>"
```

- [ ] **Step 5.3: If issues found that block merge → fix on the feature branch**

For each fix-before-merge issue, identify which phase's tool/filter is responsible and fix in place. Re-run Task 2 (scenario parity) after each fix. Re-run a follow-up mini-session if the change touched narration quality (Keith's call).

---

## Task 6 — Final rebase against `develop`

- [ ] **Step 6.1: Server**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git fetch origin
git rebase origin/develop
# Resolve any conflicts; the feature branch should already be regularly
# rebased per spec §Branch hygiene, so this should be small.
git push --force-with-lease origin feat/anthropic-sdk-migration
```

- [ ] **Step 6.2: Orchestrator**

```bash
cd /Users/slabgorb/Projects/oq-1/
git fetch origin
git rebase origin/main  # orchestrator targets main per repos.yaml
git push --force-with-lease origin feat/anthropic-sdk-migration
```

- [ ] **Step 6.3: Re-run gates after rebase**

```bash
cd /Users/slabgorb/Projects/oq-1/
just check-all
```

---

## Task 7 — Open the PRs

- [ ] **Step 7.1: Server PR (targets `develop`)**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
gh pr create --base develop --title "feat: Anthropic SDK migration (SDK narrator path live; default backend flipped)" --body "$(cat <<'EOF'
## Summary

Single-branch big-bang migration of the narrator from the `claude -p` subprocess to the Anthropic SDK. Captures four foundation wins: prompt caching (~60% cache hit rate on warm turns, 90% discount on cached input), native tool use (26 typed tools registered, every former sidecar field covered), per-call model routing (Haiku/Sonnet/Opus via `model_routing`), and structured-output via `tool_use` round-trips (ADR-102).

**Cost target hit:** per-turn weighted average within $0.05-0.07 (see playtest report).

**What landed:**
- New `AnthropicSdkClient.complete_with_tools` (Phase A)
- 26-tool typed registry + dispatch + `NarratorPerceptionFilter` (Phases B-C)
- `Orchestrator._run_narration_turn_sdk` — routes to SDK when client is a `ToolingLlmClient`, wrapped in `narration_turn_cost_span` (Phase D Task 1)
- `llm_factory` default flipped to `anthropic_sdk` (Phase D Task 2)

**What did NOT happen** (deferred to follow-ups; see Phase E plan §Updates 2026-05-15):
- ADR-039 sidecar parser is NOT deleted — `extract_structured_from_response` + `stream_fence.py` remain live because `NarratorAgent.build_output_format` still injects `narrator_output_only` and the SDK path still feeds `ToolingResult.text` back through `_assemble_turn_result`.
- ADR-028 perception rewriter file (`sidequest/agents/perception_rewriter.py`) is NOT deleted — it's a deterministic span-strip pass for MP fan-out (status-effect fidelity override), not the LLM rewriter ADR-028 envisioned.
- ADR-058 env-var passthrough is NOT removed — it's still in use by the auxiliary `ClaudeClient` paths.

**New ADRs (proposed → accepted on merge):**
- ADR-101 Anthropic SDK as Narrator Backend (already on `develop` as proposed; flips to accepted post-merge)
- ADR-102 Tool-Use Protocol for Structured Output
- ADR-103 Native OTEL via Tool Registry
- ADR-104 Perception Filtering at the Tool Layer

**Status changes (post-merge follow-up commit, Task 9):**
- ADR-001 (Claude CLI Only) → superseded by ADR-101
- ADR-039, ADR-058, ADR-028 → superseded by ADR-102/103/104 respectively
- ADR-013 (Lazy JSON Extraction) → drift (frontmatter already updated in Phase D)
- ADR-073 (Local Fine-Tuned Model Architecture) → amended by ADR-101

## Test plan

- [x] Phase A foundation tests pass (`AnthropicSdkClient`, `FakeAnthropicSdkClient`, cost math, model routing, telemetry spans)
- [x] Phase B registry tests pass (decorator, dispatch, perception filter, parallel/serialized tool semantics)
- [x] Phase C: all 26 tools registered, sidecar coverage map full (`test_sidecar_coverage_map.py`), per-tool unit + perception tests pass
- [x] Phase D Task 1: SDK narrator path wired (`tests/agents/test_narrator_uses_sdk_client.py`); narrator path uses SDK when `isinstance(client, ToolingLlmClient)`
- [x] Phase D Task 2: factory default flipped (`tests/agents/test_llm_factory.py::test_default_is_anthropic_sdk`)
- [x] Phase E: scenario parity verified against pre-migration spans; live playgroup session approved (see `docs/superpowers/playtest-reports/...`)
- [x] Full server suite: 5871 pass / 35 fail (35 fails are pre-existing baseline drift on `develop` — see Phase E plan header preamble)
- [x] `uv run ruff check .` clean; `uv run pyright sidequest/agents/orchestrator.py` 1 error (pre-existing baseline)

## Known follow-ups (not blocking merge)

1. **Drop `narrator_output_only` injection on the SDK path** so the model stops emitting sidecars when tools are available. Either gate the injection behind backend identity or rewrite the rule.
2. **Update `_assemble_turn_result`** on the SDK path to populate `NarrationTurnResult` from `ToolingResult.tool_calls` instead of (or in addition to) the sidecar parser.
3. Once 1+2 land, **actually delete** `extract_structured_from_response`, `stream_fence.py`, and (when ClaudeClient is removed entirely) `claude_stream_parser.py`.

Each is a small, contained follow-up story; together they complete ADR-102's structural-lie-detection benefit.
EOF
)"
```

- [ ] **Step 7.2: Orchestrator PR (targets `main`)**

```bash
cd /Users/slabgorb/Projects/oq-1/
gh pr create --base main --title "docs(adr): Anthropic SDK migration ADR set" --body "$(cat <<'EOF'
## Summary

ADR companion to the sidequest-server SDK migration PR. The parent ADR-101 (Anthropic SDK as Narrator Backend) is already on `develop` as proposed; this PR adds the three successor ADRs and updates frontmatter on superseded/amended ADRs.

**New ADRs:**
- ADR-102 Tool-Use Protocol for Structured Output (supersedes ADR-039)
- ADR-103 Native OTEL via Tool Registry (supersedes ADR-058 for the narrator path; ADR-058's env-var passthrough survives for auxiliary callers)
- ADR-104 Perception Filtering at the Tool Layer (supersedes ADR-028 conceptually; the deterministic MP fan-out span-strip in `sidequest/agents/perception_rewriter.py` survives — see ADR-104 body)

**Frontmatter updates:**
- ADR-001 — `status: superseded` (was already implicit via ADR-101's `supersedes: [1, 39, 58, 28]`; this confirms in frontmatter and on the index)
- ADR-039, ADR-058, ADR-028 — `superseded-by:` already wired in Phase D Task 7; `status:` flips in Task 9 post-merge
- ADR-073 — `amended-by: [101]` already wired in Phase D Task 7
- ADR-013 — `implementation-status: drift` already set in Phase D commit 69a36f1

Lands together with the server merge so the ADR index reflects reality on `main`.

## Test plan

- [x] `python3 scripts/regenerate_adr_indexes.py` is idempotent (no diff after a second run)
- [x] `docs/adr/README.md` lists the four new ADRs in the correct categories
- [x] `docs/adr/DRIFT.md` includes ADR-013 with pointer to ADR-102
- [x] `CLAUDE.md` ADR index block updated and lints clean
EOF
)"
```

---

## Task 8 — Squash-merge

- [ ] **Step 8.1: Code review pass**

The Reviewer agent runs adversarial review on the diff. For a migration this size, expect ~10-30 findings; most should be `nit`-level. Critical findings block merge; majors get triaged into fix-before-merge or fix-immediately-after-merge.

```bash
# In the orchestrator session, hand off to /pf-reviewer
```

- [ ] **Step 8.2: Squash-merge the server PR**

Once review is clean:

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
gh pr merge --squash --delete-branch
```

The squash-merge commit message uses the PR title + body (or whatever your repo's policy is). Verify the body lists every retired ADR + new ADR.

- [ ] **Step 8.3: Squash-merge the orchestrator PR**

```bash
cd /Users/slabgorb/Projects/oq-1/
gh pr merge --squash --delete-branch
```

---

## Task 9 — Post-merge ADR status flips

Spec §Approach B: the proposed → accepted / accepted → superseded flips happen *after* the squash-merge, on a follow-on commit to `main`.

- [ ] **Step 9.1: Pull and branch**

```bash
cd /Users/slabgorb/Projects/oq-1/
git checkout main
git pull --ff-only
git checkout -b docs/adr-status-flips-anthropic-sdk-migration
```

- [ ] **Step 9.2: Flip the statuses**

Edit each ADR's frontmatter:

| ADR | New status |
|---|---|
| 101 | accepted |
| 102 | accepted |
| 103 | accepted |
| 104 | accepted |
| 001 | superseded |
| 028 | superseded |
| 039 | superseded |
| 058 | superseded |
| 013 | drift (already set in Phase D commit 69a36f1; verify only) |
| 073 | accepted (unchanged; amended-by: [101] already set in Phase D commit 82ff503) |

Leave bodies untouched. Update `categories:` if any of them got reclassified.

Note: ADR-058's `status: superseded` refers to the **narrator path**. The env-var OTEL passthrough mechanism in `sidequest/agents/claude_client.py:429-442` stays live for auxiliary callers (mood classifier, name gen, scratch). ADR-103's body documents the coexistence. Likewise for ADR-028: `status: superseded` refers to the **envisioned LLM rewriter** that ADR-028 described; the deterministic span-strip in `sidequest/agents/perception_rewriter.py` survives, and ADR-104's body documents the doctrine split.

- [ ] **Step 9.3: Regenerate the index**

```bash
cd /Users/slabgorb/Projects/oq-1/
python3 scripts/regenerate_adr_indexes.py
```

(Use `python3` — `python` is not on PATH on this machine.) Verify `docs/adr/README.md` now shows the four new ADRs (101/102/103/104) as load-bearing/accepted and the four superseded ones (001/028/039/058) in the appropriate section. The regen script writes `SUPERSEDED.md` and `DRIFT.md` automatically from frontmatter; no manual edits should be needed.

- [ ] **Step 9.4: Commit + PR + merge**

```bash
cd /Users/slabgorb/Projects/oq-1/
git add docs/adr/
git commit -F /tmp/adr-flips-msg.txt
git push -u origin docs/adr-status-flips-anthropic-sdk-migration
gh pr create --base main --title "docs(adr): post-migration status flips" --body "Flips ADR statuses after the SDK migration squash-merge. Trivial; no behavior change."
gh pr merge --squash --delete-branch
```

Where `/tmp/adr-flips-msg.txt` contains (write via the Write tool to avoid system-reminder leakage in heredocs — see [[feedback_implementer_commit_leakage]]):

```
docs(adr): flip statuses post Anthropic-SDK-migration merge

ADR-101/102/103/104 → accepted.
ADR-001/028/039/058 → superseded.

ADR-058's env-var passthrough mechanism stays live for auxiliary
ClaudeClient callers — superseded means "no longer load-bearing for
the narrator path". ADR-028's deterministic span-strip in
sidequest/agents/perception_rewriter.py stays live for MP fan-out —
superseded means "the envisioned LLM rewriter is retired" (it was
never built).

ADR-013 (drift) and ADR-073 (amended-by 101) were already set in
Phase D — no change in this commit.
```

---

## Phase E completion check

- [ ] **Both PRs squash-merged.** (Task 8)
- [ ] **ADR status flips merged on main.** (Task 9)
- [ ] **`develop` runs SDK narrator.** Run a smoke playtest after the merge:
  ```bash
  cd /Users/slabgorb/Projects/oq-1/
  git checkout main && cd sidequest-server && git checkout develop && git pull --ff-only
  cd /Users/slabgorb/Projects/oq-1/
  just up
  # play one short scene; confirm narration arrives and tool spans show in the GM panel.
  ```
- [ ] **Cost per turn matches target.** Smoke playtest's `narration.turn.total_cost_usd` averages $0.05-0.07.
- [ ] **Feature branches deleted.** Both server and orchestrator `feat/anthropic-sdk-migration` branches removed (the `gh pr merge --delete-branch` did this).
- [ ] **Playtest report committed.** Available at `docs/superpowers/playtest-reports/`.
- [ ] **Sprint tracking updated.** If a Sprint-4 epic was opened for this migration, mark it closed.

---

## Migration retrospective (optional but recommended)

After merge, run a brief retrospective covering:
- What did the cost telemetry actually show vs the spec's $0.05-0.07 target?
- Which tools were used heavily? Which never fired?
- Did the narrator quality match what Keith expected when designing for himself-as-player?
- What blocked us most: a per-tool conversion, the perception filter, or the prompt slim?
- What deferred items (genre-pack-specific tools, batch API) should move into the active backlog?

Capture findings in `docs/superpowers/playtest-reports/2026-MM-DD-anthropic-sdk-migration-retro.md`. Optional; the retro informs the next migration epic.

---

## After this phase

- **Watch the cost telemetry over the next 4-6 sessions.** If average per-turn cost drifts >$0.10, investigate: cache hit rate dropping, model routing not engaging, tool over-use.
- **Genre-pack-specific tool catalogs** become a viable epic (spec §Non-goals → "deferred to a post-migration follow-on").
- **Batch API integration for between-scene NPC simulation** becomes a viable epic (spec §Non-goals → "out of v1").
- **Local fine-tuned model story 48-4** is unblocked — it always could have proceeded in parallel, but the SDK migration narrowed its surface (per ADR-101's amendment to ADR-073).
