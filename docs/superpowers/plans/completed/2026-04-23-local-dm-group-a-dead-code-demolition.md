# Local DM — Group A: Dead-Code Demolition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retire the write-only `action_flags` pipeline and the hardcoded `classified_intent` constant across server + UI, preparing the ground for the Local DM decomposer (Groups B-G).

**Architecture:** Pure deletion. No new features. No behavior changes visible to players. Every removed piece is currently a write-only data path (fields emitted by the narrator, wrapped into dataclasses, threaded through result types, serialized onto watcher events — and read nowhere). Tests that reference these fields get the same treatment — deleted if dead, trimmed if they assert on still-meaningful adjacent behavior. The narrator's prompt shrinks; its structured output contract shrinks; the `NarrationTurnResult` shape simplifies. The dormant `preprocessor.py` module — a Rust port that was never wired into the Python dispatch flow — is deleted whole.

**Tech Stack:** Python 3.11+, pytest + pytest-asyncio, uv (server). TypeScript/React, vitest (UI). No new dependencies.

**Spec:** `docs/superpowers/specs/2026-04-23-local-dm-decomposer-design.md` — §1 (Problem 1a-1b), §10 Story Group A.

**Repos touched:**
- `sidequest-server/` — server changes (branch: `feat/local-dm-group-a`, targets `develop`)
- `sidequest-ui/` — UI cleanup (branch: `feat/local-dm-group-a`, targets `develop`)
- `.` (orchestrator) — ADR-067 amendment (branch: `feat/local-dm-group-a`, targets `main`)

Per `repos.yaml`: server/UI target `develop`; orchestrator targets `main`. Never assume `main` for all.

---

## Roadmap Context (Groups B-G)

This is one of seven plans for the Local DM effort. Groups are sequenced:

- **Group A (this plan)** — Dead-code demolition. Unblocks everything.
- **Group B** — Decomposer MVP (Haiku-backed `LocalDM.decompose()` between sealed-letter completion and narrator). Depends on A.
- **Group C** — Lethality arbitration + `LethalityVerdict` + genre-pack `lethality_policy`. Depends on B.
- **Group D** — Corpus miner + per-player save diff + standalone labeling tool. Can run parallel to A-B.
- **Group E** — `LlmClient` trait + Ollama/MLX backends + QLoRA fine-tune pipeline (ADR-073 Phases 1-3). Depends on D corpus.
- **Group F** — Specialization (per-genre LoRA, per-player tuning, in-game feedback). Optional; conditional on B eval.
- **Group G (LOAD-BEARING for multiplayer)** — Asymmetric-info wiring: visibility tags feed Perception Rewriter (ADR-028) + ProjectionFilter (Plan 03). Depends on B.

Each of B-G gets its own writing-plans pass when that group begins. This plan only covers A.

---

## Preflight

- [ ] **Preflight 1: Confirm server tests pass on current `develop`**

```bash
cd sidequest-server && git checkout develop && git pull && just server-test 2>&1 | tail -30
```
Expected: full pytest suite passes. If anything is already red, stop and diagnose before demolishing code — a failing test we later delete would mask a real regression.

- [ ] **Preflight 2: Confirm UI tests pass on current `develop`**

```bash
cd sidequest-ui && git checkout develop && git pull && just client-test 2>&1 | tail -30
```
Expected: vitest suite passes.

- [ ] **Preflight 3: Capture the exact set of "write-only" field locations for audit**

```bash
cd /Users/slabgorb/Projects/oq-1 && grep -rn "is_power_grab\|references_inventory\|references_npc\|references_ability\|references_location\|ActionFlags\|action_flags\|classified_intent" sidequest-server/sidequest sidequest-ui/src --include="*.py" --include="*.ts" --include="*.tsx" | grep -v "^[^:]*:.*test_\|__tests__" > /tmp/group-a-preflight-audit.txt
wc -l /tmp/group-a-preflight-audit.txt
```
Expected: a non-zero list. Save this file; re-run the grep after Task 8 and verify the list shrinks to zero production references. This is the demolition completeness check.

- [ ] **Preflight 4: Create server feature branch**

```bash
cd sidequest-server && git checkout -b feat/local-dm-group-a
```

- [ ] **Preflight 5: Create UI feature branch**

```bash
cd sidequest-ui && git checkout -b feat/local-dm-group-a
```

- [ ] **Preflight 6: Create orchestrator feature branch**

```bash
cd /Users/slabgorb/Projects/oq-1 && git checkout -b feat/local-dm-group-a
```

---

## Task 1: Remove `action_flags` section from narrator prompt

**Repo:** `sidequest-server/` (targets `develop`)

**Files:**
- Modify: `sidequest-server/sidequest/agents/narrator.py` — lines 76, 91-100 describe `action_rewrite, action_flags` in the prompt. Remove the `action_flags` portions; `action_rewrite` stays (it has live consumers).
- Modify: `sidequest-server/tests/agents/test_narrator.py` (or wherever the prompt assertions live) — remove any test that asserts the prompt contains `is_power_grab`, `references_inventory`, etc.

**Context:** The narrator's structured-output prompt currently instructs Claude to emit an `action_flags` object with five booleans on every turn. Nothing consumes these booleans (verified across server, UI, daemon by preflight audit). The prompt describes `action_rewrite, action_flags` as a paired emission; only `action_flags` is dead. We surgically remove the `action_flags` description and the default-value directive, keeping the `action_rewrite` guidance intact.

- [ ] **Step 1: Read the current narrator prompt builder to locate all `action_flags` references**

```bash
grep -n "action_flags\|is_power_grab\|references_inventory\|references_npc\|references_ability\|references_location" sidequest-server/sidequest/agents/narrator.py
```
Expected: lines ~76, ~91-100 (the `action_flags: Object.` section and its defaults block). Note exact line ranges for editing.

- [ ] **Step 2: Write the failing test — "narrator prompt does not mention action_flags"**

Append to `sidequest-server/tests/agents/test_narrator.py` (create file if absent; follow existing test file conventions — import `from sidequest.agents.narrator import ...`):

```python
def test_narrator_prompt_does_not_mention_action_flags():
    """
    Story group A, Task 1 — action_flags is write-only dead weight.
    Narrator prompt must not instruct Claude to emit it.
    """
    from sidequest.agents.narrator import NARRATOR_SYSTEM_PROMPT  # or whatever the prompt constant is named
    dead_tokens = [
        "action_flags",
        "is_power_grab",
        "references_inventory",
        "references_npc",
        "references_ability",
        "references_location",
    ]
    for token in dead_tokens:
        assert token not in NARRATOR_SYSTEM_PROMPT, (
            f"Dead token {token!r} still present in narrator prompt — "
            "Group A Task 1 not complete"
        )
```

If the prompt is built dynamically, adapt the assertion to call the builder and check the returned string. Check the existing test file for the pattern.

- [ ] **Step 3: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/agents/test_narrator.py::test_narrator_prompt_does_not_mention_action_flags -v
```
Expected: FAIL with `AssertionError: Dead token 'action_flags' still present in narrator prompt`.

- [ ] **Step 4: Delete the `action_flags` section of the narrator prompt**

Edit `sidequest-server/sidequest/agents/narrator.py`:
- Line 76 context: the "Fields:" (or equivalent) list mentions `action_rewrite, action_flags.` — change to `action_rewrite.` (drop the `, action_flags`).
- Lines 91-100: delete the entire `action_flags: Object.` block (from `action_flags: Object. Include on every turn...` through the final `references_location: true if the action \` continuation sentence closing).

Use the Edit tool with exact old_string/new_string matching lines in the file. Preserve surrounding whitespace.

- [ ] **Step 5: Run test to verify it passes**

```bash
cd sidequest-server && uv run pytest tests/agents/test_narrator.py::test_narrator_prompt_does_not_mention_action_flags -v
```
Expected: PASS.

- [ ] **Step 6: Run the full narrator test file to ensure no regressions**

```bash
cd sidequest-server && uv run pytest tests/agents/test_narrator.py -v
```
Expected: all tests pass. If an older test was asserting on `action_flags` being present in the prompt, it now fails — delete that test (it was asserting dead behavior).

- [ ] **Step 7: Commit**

```bash
cd sidequest-server && git add sidequest/agents/narrator.py tests/agents/test_narrator.py && git commit -m "$(cat <<'EOF'
refactor(narrator): remove action_flags from prompt (group A task 1)

The five action_flags booleans (is_power_grab, references_inventory,
references_npc, references_ability, references_location) are write-only
— no server, UI, or daemon consumer reads them. Dropping them from the
narrator prompt reduces dual-task load (ADR-057) and token cost per turn.

Part of the Local DM Group A dead-code demolition. See
docs/superpowers/specs/2026-04-23-local-dm-decomposer-design.md §1 + §10.
EOF
)"
```

---

## Task 2: Remove `ActionFlags` dataclass and extraction threading from orchestrator

**Repo:** `sidequest-server/`

**Files:**
- Modify: `sidequest-server/sidequest/agents/orchestrator.py` — surgical removal of the dataclass and all extraction/construction/threading paths.
- Modify: `sidequest-server/tests/agents/test_orchestrator.py` (or wherever orchestrator tests live) — drop assertions on `action_flags`.
- Modify: `sidequest-server/sidequest/agents/__init__.py` — remove `ActionFlags` from exports if present.

**Context:** `orchestrator.py` is the largest file in the server (~1450 lines). `ActionFlags` is defined at lines 177-200, threaded through `NarrationTurnResult` (line 227), extracted from narrator response (lines 1286-1294, 1331-1338), and passed into the result construction (line 1355). `extract_structured_from_response` at line 412 builds a dict that includes an `"action_flags"` key; the dispatcher at lines 421-466 includes it in the game-patch shape; line 466 is where the patch dict assembles it. All of these come out together. The `NarrationTurnResult.action_flags` field drops.

- [ ] **Step 1: Write the failing test — "NarrationTurnResult has no action_flags field"**

Append to `sidequest-server/tests/agents/test_orchestrator.py` (or the appropriate test file; follow house conventions):

```python
def test_narration_turn_result_has_no_action_flags():
    """
    Story group A, Task 2 — ActionFlags is dead infrastructure.
    NarrationTurnResult must not carry the field.
    """
    from dataclasses import fields
    from sidequest.agents.orchestrator import NarrationTurnResult
    field_names = {f.name for f in fields(NarrationTurnResult)}
    assert "action_flags" not in field_names, (
        "action_flags still present on NarrationTurnResult — Group A Task 2 not complete"
    )

def test_action_flags_class_is_removed():
    """
    ActionFlags dataclass itself should no longer be importable from orchestrator.
    """
    from sidequest.agents import orchestrator
    assert not hasattr(orchestrator, "ActionFlags"), (
        "ActionFlags dataclass still defined — Group A Task 2 not complete"
    )
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd sidequest-server && uv run pytest tests/agents/test_orchestrator.py::test_narration_turn_result_has_no_action_flags tests/agents/test_orchestrator.py::test_action_flags_class_is_removed -v
```
Expected: both FAIL (field still present / class still defined).

- [ ] **Step 3: Delete `ActionFlags` dataclass**

Edit `sidequest-server/sidequest/agents/orchestrator.py`:

Remove the entire `ActionFlags` class (approx. lines 177-200 — verify exact range before editing):

```python
@dataclass
class ActionFlags:
    """
    Port of orchestrator.rs::ActionFlags.
    ...
    """
    is_power_grab: bool = False
    references_inventory: bool = False
    references_npc: bool = False
    references_ability: bool = False
    references_location: bool = False

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ActionFlags":
        return cls(
            is_power_grab=bool(d.get("is_power_grab", False)),
            references_inventory=bool(d.get("references_inventory", False)),
            references_npc=bool(d.get("references_npc", False)),
            references_ability=bool(d.get("references_ability", False)),
            references_location=bool(d.get("references_location", False)),
        )
```

Use Edit with the exact class-block as `old_string`. The deletion should include the preceding blank line(s) that separate the class from its neighbors, to avoid leaving double-blank gaps.

- [ ] **Step 4: Remove `action_flags` field from `NarrationTurnResult`**

Edit `sidequest-server/sidequest/agents/orchestrator.py` at approximately line 227:

```python
    action_flags: ActionFlags | None = None
```

Remove this line and the blank line that separates it from adjacent fields (if any).

- [ ] **Step 5: Remove the `action_flags` extraction path from `extract_structured_from_response`**

At approximately line 466, remove the `"action_flags": patch.get("action_flags"),` entry from the assembled dict.

If the extraction function has a type comment or docstring listing `action_flags` as an extracted field (around line 421), remove the reference.

- [ ] **Step 6: Remove the "warn on missing action_flags" block**

Edit `orchestrator.py` around lines 1291-1294:

```python
            if extraction["action_flags"] is None:
                logger.warning(
                    "action_flags absent from extraction — using default (all flags false)"
                )
```

Delete the block entirely.

- [ ] **Step 7: Remove the `action_flags` build + thread into result**

Edit `orchestrator.py` around lines 1336-1338:

```python
            action_flags: ActionFlags | None = None
            if isinstance(extraction["action_flags"], dict):
                action_flags = ActionFlags.from_dict(extraction["action_flags"])
```

Delete this block.

Then at line ~1355 (the `NarrationTurnResult(...)` constructor call):
Remove the `action_flags=action_flags,` kwarg.

- [ ] **Step 8: Remove the `has_action_flags=` log format arg**

Edit `orchestrator.py` around lines 436-446 — remove the `has_action_flags=%s` token from the logger format string and drop `patch.get("action_flags") is not None,` from the logger args.

- [ ] **Step 9: Remove `ActionFlags` from package exports**

Edit `sidequest-server/sidequest/agents/__init__.py`:
- Remove `ActionFlags,` from the import list at line ~34
- Remove `"ActionFlags",` from `__all__` at line ~72
- Remove the `- ActionRewrite, ActionFlags, ...` comment reference at line ~16 (drop just the `ActionFlags` token from the list)

- [ ] **Step 10: Run the full orchestrator test module**

```bash
cd sidequest-server && uv run pytest tests/agents/test_orchestrator.py -v
```
Expected: new tests PASS. Pre-existing tests that assert on `action_flags` being present will fail — delete them (they were asserting dead behavior). Pre-existing tests that merely mention `action_flags` in setup/mock data should have the field stripped from the mock.

- [ ] **Step 11: Run the server-wide test suite to catch cross-module fallout**

```bash
cd sidequest-server && just server-test 2>&1 | tail -50
```
Expected: green. If other tests fail referencing `ActionFlags`, update them — every reference was dead.

- [ ] **Step 12: Commit**

```bash
cd sidequest-server && git add sidequest/agents/orchestrator.py sidequest/agents/__init__.py tests/ && git commit -m "$(cat <<'EOF'
refactor(orchestrator): remove ActionFlags dataclass and threading (group A task 2)

ActionFlags was write-only: emitted by the narrator, extracted into the
dataclass, threaded through NarrationTurnResult, serialized onto the
watcher event — and read by nothing (verified by grep across server, UI,
daemon).

Removes:
- ActionFlags dataclass + from_dict
- NarrationTurnResult.action_flags field
- action_flags extraction path in extract_structured_from_response
- action_flags warn + build + threading in run_narration_turn
- has_action_flags log token
- ActionFlags export from agents/__init__.py

Part of the Local DM Group A dead-code demolition.
EOF
)"
```

---

## Task 3: Remove `classified_intent` hardcode from orchestrator

**Repo:** `sidequest-server/`

**Files:**
- Modify: `sidequest-server/sidequest/agents/orchestrator.py` — line 1200 hardcodes `classified_intent = "exploration"` per ADR-067. Line 233 defines the field on `NarrationTurnResult`. Lines 1208 and 1254 use it in logging. Line 1359 passes it through.
- Modify: `sidequest-server/tests/agents/test_orchestrator.py` — tests that assert on `classified_intent` on the result get the same treatment as in Task 2.

**Context:** `classified_intent` was the intent-routing hook from ADR-010, made a no-op by ADR-067's "all intents route to narrator" collapse. Keeping the field on the result while hardcoding its value is the split-brain the spec diagnoses (§1b). It leaves for good now; Groups B-G introduce real dispatch via `DispatchPackage` instead.

**Back-compat caveat:** the watcher event at `session_handler.py:1830` publishes `classified_intent` to the UI's timeline — Task 6 handles the watcher payload; Task 7 handles the UI. Task 3 only removes the server-internal field.

- [ ] **Step 1: Write failing test — "NarrationTurnResult has no classified_intent"**

Append:

```python
def test_narration_turn_result_has_no_classified_intent():
    """
    Group A, Task 3 — classified_intent is a dead hardcode.
    NarrationTurnResult must not carry the field.
    """
    from dataclasses import fields
    from sidequest.agents.orchestrator import NarrationTurnResult
    field_names = {f.name for f in fields(NarrationTurnResult)}
    assert "classified_intent" not in field_names
```

- [ ] **Step 2: Run test to verify failure**

```bash
cd sidequest-server && uv run pytest tests/agents/test_orchestrator.py::test_narration_turn_result_has_no_classified_intent -v
```
Expected: FAIL.

- [ ] **Step 3: Remove `classified_intent` field from `NarrationTurnResult`**

Edit `orchestrator.py` at approximately line 233:
```python
    classified_intent: str | None = None
```
Delete the line.

- [ ] **Step 4: Remove the hardcode + logging**

Edit `orchestrator.py` at approximately line 1200:
```python
            # ADR-067: all intents route to narrator
            classified_intent = "exploration"
            agent_name = self._narrator.name()
```

Remove the `classified_intent = "exploration"` line. Keep `agent_name = self._narrator.name()`.

At line ~1208:
```python
            logger.info(
                "unified_narrator.intent_inferred intent=%s source=state_inference",
                classified_intent,
            )
```
Delete the whole logger.info call — it was logging a dead constant.

- [ ] **Step 5: Remove `classified_intent` from degraded-response return (line ~1254)**

In the degraded-path `return NarrationTurnResult(...)`, remove the `classified_intent=classified_intent,` kwarg.

- [ ] **Step 6: Remove `classified_intent` from the success-path return (line ~1359)**

Same treatment — remove the `classified_intent=classified_intent,` kwarg.

- [ ] **Step 7: Run test + full orchestrator suite**

```bash
cd sidequest-server && uv run pytest tests/agents/test_orchestrator.py -v
```
Expected: new test passes; any prior test asserting on `classified_intent` fails — delete it (asserting dead behavior).

- [ ] **Step 8: Run full server suite**

```bash
cd sidequest-server && just server-test 2>&1 | tail -40
```
Expected: green. If session_handler or watcher-publish tests fail because they expected the field on the result, note them — Task 6 will fix the watcher payload side.

- [ ] **Step 9: Commit**

```bash
cd sidequest-server && git add sidequest/agents/orchestrator.py tests/ && git commit -m "$(cat <<'EOF'
refactor(orchestrator): remove classified_intent hardcode (group A task 3)

classified_intent = "exploration" was hardcoded per ADR-067 ("all intents
route to narrator"). The field threads through NarrationTurnResult but
never varies, so any downstream branch on it is dead. Real intent dispatch
returns via DispatchPackage in Group B.

Removes field from NarrationTurnResult and its hardcode + logger + both
constructor kwargs in run_narration_turn.

Part of the Local DM Group A dead-code demolition.
EOF
)"
```

---

## Task 4: Remove flag fields from `PreprocessedAction` in `game/turn.py`

**Repo:** `sidequest-server/`

**Files:**
- Modify: `sidequest-server/sidequest/game/turn.py` — lines 138-142 define the five flag booleans on `PreprocessedAction`.
- Modify: Any tests that construct `PreprocessedAction` with flag kwargs — drop the kwargs.

**Context:** `PreprocessedAction` was populated by the dormant `preprocessor.py` (see Task 5). With the preprocessor going away and nothing consuming the flags, these fields lose their last producer too. The struct itself stays — `you`, `named`, `intent` fields survive as narrator-context scaffolding that the decomposer may reuse.

- [ ] **Step 1: Write failing test**

Append to `sidequest-server/tests/game/test_turn.py` (or equivalent):

```python
def test_preprocessed_action_has_no_flag_fields():
    """
    Group A, Task 4 — remove the five write-only booleans from PreprocessedAction.
    """
    from dataclasses import fields
    from sidequest.game.turn import PreprocessedAction
    field_names = {f.name for f in fields(PreprocessedAction)}
    for dead in [
        "is_power_grab",
        "references_inventory",
        "references_npc",
        "references_ability",
        "references_location",
    ]:
        assert dead not in field_names, (
            f"{dead} still on PreprocessedAction — Group A Task 4 not complete"
        )
```

- [ ] **Step 2: Run test to verify failure**

```bash
cd sidequest-server && uv run pytest tests/game/test_turn.py::test_preprocessed_action_has_no_flag_fields -v
```
Expected: FAIL.

- [ ] **Step 3: Remove the five fields**

Edit `sidequest-server/sidequest/game/turn.py` around lines 138-142:

```python
    is_power_grab: bool = False
    references_inventory: bool = False
    references_npc: bool = False
    references_ability: bool = False
    references_location: bool = False
```

Delete these five lines. Preserve the surrounding struct layout.

- [ ] **Step 4: Run test + turn suite**

```bash
cd sidequest-server && uv run pytest tests/game/test_turn.py -v
```
Expected: new test passes; any test constructing `PreprocessedAction` with flag kwargs fails — fix each by dropping the kwarg from the constructor call.

- [ ] **Step 5: Run full server suite**

```bash
cd sidequest-server && just server-test 2>&1 | tail -40
```
Expected: green.

- [ ] **Step 6: Commit**

```bash
cd sidequest-server && git add sidequest/game/turn.py tests/ && git commit -m "$(cat <<'EOF'
refactor(turn): remove flag fields from PreprocessedAction (group A task 4)

The five flag booleans on PreprocessedAction had one producer (the
dormant preprocessor module, deleted in task 5) and no consumers. The
you/named/intent perspective fields remain — they're scaffolding the
decomposer may reuse in Group B.

Part of the Local DM Group A dead-code demolition.
EOF
)"
```

---

## Task 5: Delete dormant `preprocessor.py` module + exports

**Repo:** `sidequest-server/`

**Files:**
- Delete: `sidequest-server/sidequest/agents/preprocessor.py` (entire file; 205 lines).
- Delete: `sidequest-server/tests/agents/test_preprocessor.py` if present.
- Modify: `sidequest-server/sidequest/agents/__init__.py` — drop `preprocess_action`, `preprocess_action_with_client`, and `PreprocessorError` (and any subclasses) from imports and `__all__`.

**Context:** `preprocessor.py` is a 1:1 port of the Rust `sidequest-agents::preprocessor`. It was ported during the Python transition but **never wired into the Python dispatch flow** — grep across `server/dispatch/` and `server/session_handler.py` returns zero call sites. It's a complete, tested, unreachable module. Deleting it removes both the code and the temptation to revive it as a workaround for Groups B-G.

- [ ] **Step 1: Verify no non-test caller exists**

```bash
grep -rn "preprocess_action\b\|from sidequest.agents.preprocessor\|import preprocessor" sidequest-server --include="*.py" | grep -v "test_\|preprocessor.py\|__init__.py"
```
Expected: **zero output**. If any line appears, stop and investigate — the module is actually live and the spec is wrong.

- [ ] **Step 2: Write failing test — "preprocessor module is not importable"**

Append to `sidequest-server/tests/agents/test_agents_exports.py` (create if absent):

```python
def test_preprocessor_module_is_removed():
    """
    Group A, Task 5 — the dormant preprocessor port is deleted.
    Nothing in the Python server wires it in; it was stubbed infrastructure.
    """
    import importlib
    try:
        importlib.import_module("sidequest.agents.preprocessor")
    except ModuleNotFoundError:
        return  # expected
    raise AssertionError(
        "sidequest.agents.preprocessor still importable — Group A Task 5 not complete"
    )

def test_preprocessor_exports_are_gone():
    """
    No re-exports from the agents package either.
    """
    from sidequest.agents import __all__
    for dead in [
        "preprocess_action",
        "preprocess_action_with_client",
        "PreprocessError",
        "LlmFailed",
        "ParseFailed",
        "OutputTooLong",
    ]:
        assert dead not in __all__, (
            f"{dead} still exported from sidequest.agents — Group A Task 5 not complete"
        )
```

- [ ] **Step 3: Run tests to verify failure**

```bash
cd sidequest-server && uv run pytest tests/agents/test_agents_exports.py -v
```
Expected: FAIL (module still importable; exports still present).

- [ ] **Step 4: Delete the preprocessor module**

```bash
rm sidequest-server/sidequest/agents/preprocessor.py
```

- [ ] **Step 5: Delete the preprocessor test module (if present)**

```bash
[ -f sidequest-server/tests/agents/test_preprocessor.py ] && rm sidequest-server/tests/agents/test_preprocessor.py || echo "no test file to remove"
```

- [ ] **Step 6: Remove exports from `agents/__init__.py`**

Edit `sidequest-server/sidequest/agents/__init__.py`:

Remove the import lines that pull from `preprocessor` (around lines ~53-54):

```python
    preprocess_action,
    preprocess_action_with_client,
```

Remove the `PreprocessError` / `LlmFailed` / `ParseFailed` / `OutputTooLong` import lines if present.

Remove from `__all__` (around lines ~104-105):

```python
    "preprocess_action",
    "preprocess_action_with_client",
```

Remove the `- PreprocessorError hierarchy + preprocess_action, preprocess_action_with_client` docstring bullet at line ~13.

- [ ] **Step 7: Run tests**

```bash
cd sidequest-server && uv run pytest tests/agents/test_agents_exports.py -v && just server-test 2>&1 | tail -40
```
Expected: new tests pass; full suite green.

- [ ] **Step 8: Commit**

```bash
cd sidequest-server && git add -A sidequest/agents/preprocessor.py sidequest/agents/__init__.py tests/ && git commit -m "$(cat <<'EOF'
refactor(agents): delete dormant preprocessor module (group A task 5)

preprocessor.py was a 1:1 port from Rust during the Python transition but
was never wired into the Python dispatch flow — zero non-test callers.
Deleting removes the dead code and the temptation to revive it as a
workaround for Group B's decomposer.

Part of the Local DM Group A dead-code demolition.
EOF
)"
```

---

## Task 6: Remove `classified_intent` from session_handler watcher payload

**Repo:** `sidequest-server/`

**Files:**
- Modify: `sidequest-server/sidequest/server/session_handler.py` — line 1830 publishes `"classified_intent": result.classified_intent` onto the `turn_complete` watcher event.
- Modify: related tests that assert on the watcher payload shape.

**Context:** Task 3 removed `classified_intent` from `NarrationTurnResult`. This task removes the last producer — the watcher event. The UI will stop receiving the key; Task 7 handles UI cleanup.

- [ ] **Step 1: Write failing test — "turn_complete watcher payload has no classified_intent"**

Append to `sidequest-server/tests/server/test_session_handler.py` (or equivalent):

```python
def test_turn_complete_watcher_payload_omits_classified_intent():
    """
    Group A, Task 6 — classified_intent is dead, watcher payload must not carry it.
    """
    import inspect
    from sidequest.server import session_handler
    source = inspect.getsource(session_handler)
    assert '"classified_intent"' not in source and "'classified_intent'" not in source, (
        "classified_intent string key still in session_handler — Task 6 not complete"
    )
```

(If a higher-fidelity test is possible by actually building a turn and inspecting the emitted payload, that's better — adapt to the test harness. The string-search test is a minimum viable lock.)

- [ ] **Step 2: Run test to verify failure**

```bash
cd sidequest-server && uv run pytest tests/server/test_session_handler.py::test_turn_complete_watcher_payload_omits_classified_intent -v
```
Expected: FAIL.

- [ ] **Step 3: Remove the line from the payload dict**

Edit `sidequest-server/sidequest/server/session_handler.py` at approximately line 1830:

```python
                "classified_intent": result.classified_intent,
```

Delete the line.

- [ ] **Step 4: Run tests**

```bash
cd sidequest-server && uv run pytest tests/server/test_session_handler.py -v
```
Expected: green.

- [ ] **Step 5: Run full server suite**

```bash
cd sidequest-server && just server-test 2>&1 | tail -40
```
Expected: green.

- [ ] **Step 6: Commit**

```bash
cd sidequest-server && git add sidequest/server/session_handler.py tests/ && git commit -m "$(cat <<'EOF'
refactor(session-handler): drop classified_intent from watcher payload (group A task 6)

Task 3 removed classified_intent from NarrationTurnResult. This drops the
last producer — the turn_complete watcher event — completing the server
side of the classified_intent retirement. UI cleanup in group-a task 7.

Part of the Local DM Group A dead-code demolition.
EOF
)"
```

---

## Task 7: Remove `classified_intent` consumers + dead Combat branch in UI

**Repo:** `sidequest-ui/` (targets `develop`)

**Files:**
- Modify: `sidequest-ui/src/types/watcher.ts` — line 39 declares `classified_intent?: string;`. Remove.
- Modify: `sidequest-ui/src/components/Dashboard/tabs/TimelineTab.tsx` — lines 57, 71, 297 reference the field. Remove all three call sites, including the dead `classified_intent === "Combat"` branch (line 297).

**Context:** The UI has three sites that read `classified_intent`: a display formatter at line 57 (`Turn ${turn_id} · ${classified_intent} → ${agent_name}`), an intent badge at line 71 (`<b>Intent:</b> {classified_intent}`), and a dead conditional-render branch at line 297 (`{!f.is_degraded && f.classified_intent === "Combat" && (...)}`). With the server no longer emitting the key (Task 6), the `??` fallback in the display formatter silently renders "?" — cleaner to remove.

- [ ] **Step 1: Write failing test — "watcher event type has no classified_intent"**

Append to `sidequest-ui/src/__tests__/types.test.ts` (create if absent):

```typescript
import { describe, it, expect } from "vitest";

describe("Group A Task 7 — classified_intent retirement", () => {
  it("WatcherTurnCompleteEvent type excludes classified_intent", async () => {
    const source = await (await fetch("/src/types/watcher.ts")).text().catch(() => "");
    // In CI, vitest can't fetch — fall back to fs read via node
    // adjust to the project's idiomatic way of reading src files in tests
    // simplest: use vite-plugin-raw or a raw-import
  });
});
```

**(Note to the implementing engineer: the correct vitest pattern for "source must not contain X" in this repo is to use an import-as-string loader or a `node:fs` read in a test setup. If there's no precedent in `sidequest-ui/src/__tests__/`, use this simpler positive assertion instead:)**

```typescript
import { describe, it, expect } from "vitest";
import type { WatcherTurnCompleteEvent } from "../types/watcher";

describe("Group A Task 7 — classified_intent retirement", () => {
  it("WatcherTurnCompleteEvent does not carry classified_intent", () => {
    // Structural check via typechecker — this object must typecheck.
    // If classified_intent is still on the type, this still typechecks
    // because the prop is optional, so we need a runtime check on a
    // component that once rendered it. See TimelineTab test below.
    const ev = {} as WatcherTurnCompleteEvent;
    // @ts-expect-error — classified_intent should no longer be a property
    ev.classified_intent = "foo";
  });
});
```

- [ ] **Step 2: Verify the test fails with classified_intent still on the type**

```bash
cd sidequest-ui && npx vitest run src/__tests__/types.test.ts 2>&1 | tail -20
```
Expected: the `@ts-expect-error` directive is UNUSED (because the assignment typechecks), causing vitest to flag the test. That's the "failing" state.

- [ ] **Step 3: Remove the type field**

Edit `sidequest-ui/src/types/watcher.ts` at line 39:

```typescript
  classified_intent?: string;
```

Delete the line.

- [ ] **Step 4: Remove the TimelineTab display references**

Edit `sidequest-ui/src/components/Dashboard/tabs/TimelineTab.tsx`:

**Line 57** — the template literal `Turn ${turn_id} · ${classified_intent} → ${agent_name}`:

Replace with `Turn ${turn_id} · ${agent_name}` — drop the classified_intent interpolation and the middle separator.

**Line 71** — the `<b>Intent:</b> {classified_intent}` block:

Delete the enclosing JSX node entirely.

**Line 297** — the dead Combat branch:

```tsx
{!f.is_degraded && f.classified_intent === "Combat" && (
  <...>
)}
```

Delete the entire conditional block.

- [ ] **Step 5: Run the UI test suite**

```bash
cd sidequest-ui && just client-test 2>&1 | tail -30
```
Expected: green. The `@ts-expect-error` test now passes because the assignment to `.classified_intent` genuinely is a type error.

- [ ] **Step 6: Smoke-check the dashboard by running the app**

```bash
cd sidequest-ui && npm run build 2>&1 | tail -20
```
Expected: clean build. If tsc reports leftover `classified_intent` references, fix them.

- [ ] **Step 7: Commit**

```bash
cd sidequest-ui && git add src/types/watcher.ts src/components/Dashboard/tabs/TimelineTab.tsx src/__tests__/types.test.ts && git commit -m "$(cat <<'EOF'
refactor(ui): drop classified_intent consumers + dead Combat branch (group A task 7)

Server stopped emitting classified_intent in group-a task 6 (it was
hardcoded to "exploration" per ADR-067 and read nowhere meaningful).
UI cleanup:
- Remove classified_intent? from WatcherTurnCompleteEvent type
- Strip classified_intent interpolation from TimelineTab header
- Remove Intent: display
- Delete the classified_intent === "Combat" conditional branch (dead
  code — the hardcode meant it could never fire)

Part of the Local DM Group A dead-code demolition.
EOF
)"
```

---

## Task 8: Amend ADR-067 to note the inline-flag retirement

**Repo:** `.` (orchestrator, targets `main`)

**Files:**
- Modify: `docs/adr/067-unified-narrator-agent.md` — add a dated amendment subsection noting the retirement of the inline flags and the hardcoded classified_intent, and pointing forward to the Local DM decomposer spec.

**Context:** ADR-067 is the ADR that accepted "all intents route to narrator" and introduced the hardcoded `classified_intent`. The decomposer design retires both; ADR-067 should carry a forward-pointer. Don't rewrite the ADR history — amend it.

- [ ] **Step 1: Read the current state of ADR-067**

```bash
cat docs/adr/067-unified-narrator-agent.md | tail -30
```

Identify a suitable location for an amendment subsection — ADRs in this repo commonly close with a `## Consequences` section; add an `## Amendments` section after it if absent, or append to an existing one.

- [ ] **Step 2: Append the amendment**

Use the Edit tool to add (at the end of the file, or at the appropriate location per step 1):

```markdown
## Amendments

### 2026-04-23 — Inline flag retirement (Local DM Group A)

The `action_flags` inline-emission pattern established here (five booleans
emitted by the narrator alongside prose) has been retired. The flags were
write-only in practice: no server, UI, or daemon code consumed them, and
the narrator's dual-task load (prose + large structured sidecar) was the
dominant source of hallucination and field-drop warnings.

The hardcoded `classified_intent = "exploration"` this ADR established as a
transitional fallback has also been retired. All intent inference is
replaced by a server-side decomposer layer that emits structured dispatch
and visibility metadata before the narrator runs.

See `docs/superpowers/specs/2026-04-23-local-dm-decomposer-design.md` for
the replacement architecture. The unified-narrator decision from this ADR
stands — one canonical narrator per turn remains correct. Only the
self-reporting of intent and flags is changed.
```

- [ ] **Step 3: Sanity-check the file renders**

```bash
head -5 docs/adr/067-unified-narrator-agent.md && echo "---" && tail -25 docs/adr/067-unified-narrator-agent.md
```
Expected: clean markdown with the amendment at the tail.

- [ ] **Step 4: Commit**

```bash
git add docs/adr/067-unified-narrator-agent.md && git commit -m "$(cat <<'EOF'
docs(adr): amend ADR-067 with flag-retirement note (group A task 8)

The inline action_flags and the hardcoded classified_intent transitional
fallback have been retired. Points forward to the Local DM decomposer
spec. The unified-narrator decision itself still stands.

Part of the Local DM Group A dead-code demolition.
EOF
)"
```

---

## Final Verification

- [ ] **Final 1: Re-run the demolition completeness audit**

```bash
cd /Users/slabgorb/Projects/oq-1 && grep -rn "is_power_grab\|references_inventory\|references_npc\|references_ability\|references_location\|ActionFlags\|action_flags\|classified_intent" sidequest-server/sidequest sidequest-ui/src --include="*.py" --include="*.ts" --include="*.tsx" | grep -v "^[^:]*:.*test_\|__tests__" > /tmp/group-a-final-audit.txt
wc -l /tmp/group-a-final-audit.txt
```
Expected: **zero lines.** If any line appears, a reference escaped — investigate and patch.

- [ ] **Final 2: Server full suite green**

```bash
cd sidequest-server && just server-test 2>&1 | tail -20
```
Expected: green.

- [ ] **Final 3: UI full suite green**

```bash
cd sidequest-ui && just client-test 2>&1 | tail -20
```
Expected: green.

- [ ] **Final 4: End-to-end smoke test**

```bash
cd /Users/slabgorb/Projects/oq-1 && just up 2>&1 &
# wait ~10s for boot
sleep 10
# in another shell, run a quick playtest
just playtest-scenario smoke_test 2>&1 | tail -30
just down
```
Expected: playtest completes without errors. A narrator turn runs, the watcher event fires without `classified_intent` or `action_flags`, nothing downstream breaks.

- [ ] **Final 5: Push branches + open PRs**

```bash
cd sidequest-server && git push -u origin feat/local-dm-group-a
cd /Users/slabgorb/Projects/oq-1/sidequest-ui && git push -u origin feat/local-dm-group-a
cd /Users/slabgorb/Projects/oq-1 && git push -u origin feat/local-dm-group-a
```

Open three PRs (one per repo), titled:
- `refactor(server): Local DM Group A — dead-code demolition`
- `refactor(ui): Local DM Group A — classified_intent consumer cleanup`
- `docs(adr): Local DM Group A — amend ADR-067`

PR descriptions should cross-link the three and reference the spec.

- [ ] **Final 6: Commit any remaining sprint tracking updates (orchestrator)**

If sprint YAML needs updating for this work, do it now per `/pf-sprint` conventions. (Not strictly in scope for a writing-plans plan but typical for this repo's workflow.)

---

## Scope Recovery (if something goes wrong)

- **If a test was asserting on `classified_intent === "Combat"` and its removal surfaces a real behavioral requirement,** pause and investigate — there may have been a live path that was *supposed* to work but wasn't because of the hardcode. Document the finding in the session file; this belongs in Group B (decomposer MVP) to handle properly with real intent classification.

- **If preprocessor.py turns out to be live** (grep in Task 5 Step 1 finds a non-test caller), stop and diagnose. The spec's claim that it's dead is based on current-state grep; if something was added recently that wires it in, the spec needs amendment.

- **If any "dead" test files have assertions that are actually testing *adjacent* behavior** (e.g., a test that happens to set `action_flags` in mock setup but is really testing something else), trim the test rather than deleting it. Delete only when the test's sole purpose was asserting on the dead surface.

---

## What this unblocks

Once Group A lands on `develop` (server + UI) and `main` (orchestrator ADR):

- The narrator prompt is ~20 tokens leaner and no longer dual-tasked on flag extraction
- `NarrationTurnResult` is a cleaner struct for Group B's `DispatchPackage` consumer wiring
- The decomposer in Group B has a clean insertion point (no dead hardcode to replace, just an empty slot)
- The ProjectionFilter work in Group G has one less dead field to reason about on the wire
- The corpus miner in Group D sees unambiguous `events` / `narrative_log` schema with no ambiguous dead fields

Ship Group A, then kick off Group B's writing-plans pass.
