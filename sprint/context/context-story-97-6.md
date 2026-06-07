---
parent: context-epic-97.md
workflow: tdd
---

# Story 97-6: test_chargen_name_rig_extraction xdist flake — pg-gated pair fails order-dependently in parallel full-suite runs

## Business Context

A known flake documented in server #741's PR notes: the `tests/server/test_chargen_name_rig_extraction.py::TestNameRigExtractionWiring` pair (`extracted_name_and_renamed_rig`, `extraction_decisions_are_observable`) fails order-dependently under xdist in FULL-suite runs — the `chargen.names_extracted` span is absent from the `InMemorySpanExporter` capture. It passes in isolation, serially, per-directory, and intermittently in full runs with identical code. A flaky pair in the full suite poisons the project's most load-bearing gate: every story's "full suite at baseline" claim now needs a human to adjudicate whether these two reds are "the flake" or a real regression — exactly the ambiguity the full-suite-baseline doctrine exists to eliminate. Note the trap that surfaced it: these pg-gated tests only started RUNNING when `SIDEQUEST_TEST_DATABASE_URL` became part of the standard env — they were silently skipped in earlier baselines, so "this test always passed" claims predate it actually executing.

## Technical Guardrails

- **Fix the isolation, not the assertion.** Weakening the span assertion (retry, sleep, "if present") is explicitly out — the test verifies the ADR-103 lie-detector wiring; a vacuous version is worse than none.
- Suspects named in the filing, in order: (a) shared tracer-provider/span-exporter state across tests in an xdist worker — `InMemorySpanExporter` capture (imported at test file :25, fixture-injected at :119/:160) may be attached to a global `TracerProvider` that another test in the same worker replaces, detaches, or pollutes; (b) an extraction-path global raced by a sibling test.
- Investigation shape: reproduce with `pytest -p xdist ... --dist=loadfile`-style bisection or `pytest-randomly`-style seed capture to find the poisoning sibling; OR audit how `otel_capture` is installed (conftest fixture — find it) versus how other test files install their own span capture. The OTEL SDK's `set_tracer_provider` is set-once-global; two fixtures fighting over it is the classic shape of exactly this symptom.
- Whatever the cause, prefer fixing the **fixture/conftest pattern** so the whole class of span-capture tests is isolated (other span-assertion tests are latent victims), over special-casing this one file. Reuse-first: if a correct shared `otel_capture` fixture exists, converge on it.
- Telemetry module: `sidequest/telemetry/` (spans definitions, watcher hooks). If the fix touches production telemetry init, the wiring test rule applies — prove the production path still exports.
- Verification is statistical: the AC demands 5 consecutive clean full-suite parallel runs — budget the wall-clock (full suite ~10k tests × 5) and run them with the standard env (`SIDEQUEST_GENRE_PACKS`, `SIDEQUEST_TEST_DATABASE_URL=postgresql://$USER@localhost:5432/sidequest_test`).

## Scope Boundaries

**In scope:**
- Root-cause the order-dependent capture failure; fix test isolation
- Root cause documented in the test docstring (AC 2)
- The pair passing 5 consecutive full-suite parallel runs

**Out of scope:**
- The chargen name/rig extraction feature itself (#741 territory, behavior is correct)
- The 2 known epic-96 baseline failures (earthman boon tier-leak, reprisal broadcast-pair)
- A general audit of all span-capture tests — IF the fix lands at the shared-fixture level they benefit for free; an explicit sweep is its own chore

## AC Context

1. **"Pair passes 5 consecutive full-suite parallel runs"** — Test: literal — 5× full-suite xdist runs with the standard env, the pair green in all 5 (the rest of the suite at the known baseline). Evidence: run logs in the session file. Edge: if the flake is seed/order-dependent, also pin one deliberately adversarial ordering (the discovered poisoning sibling scheduled before the pair in the same worker) as a regression test — that converts the statistical claim into a deterministic one.
2. **"Root cause documented in the test docstring"** — Test: the docstring on the test class (or the fixture it depends on) names the mechanism (which global, which sibling/pattern raced it) and the isolation contract that prevents recurrence. A reviewer must be able to read why this won't come back without spelunking the PR.

## Assumptions

- The flake is environmental (test-infra), not a real intermittent absence of the `chargen.names_extracted` span in production — the passes-in-isolation evidence supports this, but the investigation must confirm the span fires unconditionally on the production path before blaming the exporter.
- Postgres is available to the runner (pg-gated tests must RUN — a skip is a vacuous pass and repeats the original silent-skip trap).
- No production code change is needed; if the root cause turns out to be a real race in extraction-path globals (suspect b), the story grows a server-code fix — log the deviation, the points may not hold.
