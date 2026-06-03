# Epic 81: Built-Not-Wired Remediation — Magic Validator, Tension & Pacing

## Overview

Three runtime bugs, one root cause: a subsystem that was fully built, unit-tested,
and marked `implementation-status: live` in its ADR — but never imported, instantiated,
or fed from any production code path. Each silently no-ops (or hits a failure branch)
at runtime while looking healthy in isolation. This epic wires the three dark
subsystems into production and adds the missing wiring tests that would have caught
each one.

**Priority:** P1
**Repo:** sidequest-server
**Stories:** 3 (8 points)

- **81-1** (2) — Register magic plugins in production so `MAGIC_PLUGINS` is non-empty at runtime (ADR-126)
- **81-2** (3) — Instantiate and drive `TensionTracker` in the turn pipeline (ADR-024)
- **81-3** (3) — Feed `PacingHint` into `TurnContext` so the `[PACING]` injection fires (ADR-025) — *depends on 81-2*

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| **ADR-vs-Code Audit** (`docs/adr/AUDIT-2026-06-03.md`) | "Overstated" bucket — ADR-126, ADR-024, ADR-025 findings + evidence (the three majors that are real code bugs, not doc drift) |
| **ADR-126 Pluggable Magic System** (`docs/adr/126-pluggable-magic-system.md`) | MagicPlugin Protocol, import-time registry, validator severity model — the import-time registration invariant that does not fire |
| **ADR-024 Dual-Track Tension Model** (`docs/adr/024-dual-track-tension-model.md`) | TensionTracker, action/stakes tracks, event spikes, `pacing_hint()` |
| **ADR-025 Pacing Detection** (`docs/adr/025-pacing-detection.md`) | PacingHint, `[PACING]` prompt injection, quiet-turn detection (latter remains deferred) |
| **CLAUDE.md** (`CLAUDE.md`) | Development Principles → "Verify Wiring, Not Just Existence" and "Every Test Suite Needs a Wiring Test"; OTEL Observability Principle (the lie-detector) |
| **SOUL.md** (loaded via agent context) | "Cost Scales with Drama" / "Cut the Dull Bits" — tension+pacing are the mechanical backing for pacing decisions the narrator currently improvises |

## Background

The 2026-06-03 ADR-vs-code audit (`verify-adr-claims` workflow, run `wf_0f9ed063-1a3`)
checked all 113 non-superseded ADRs against the actual code and put every disagreement
through an adversarial refutation pass. It surfaced 65 confirmed findings. Most were
documentation drift. **Three were genuine runtime bugs** — subsystems whose ADRs claim
`live` but whose production wiring is absent. They share an identical signature: the
component class/registry exists, its unit tests pass (because the tests construct or
import the component directly), and nothing in the server ever does the same.

This is precisely the failure mode CLAUDE.md's wiring doctrine names —
*"Tests passing and files existing means nothing if the component isn't imported, the
hook isn't called, or the endpoint isn't hit in production code"* — and the reason the
project mandates a wiring test per suite. All three slipped through because their
existing tests assert the component works in isolation but never assert it is reachable
from a production path.

**Why these three matter to the table:**

- **Magic validator (ADR-126)** is a correctness firewall. With `MAGIC_PLUGINS` empty,
  every plugin-declared magic effect fails open into the `plugin_known_but_not_registered`
  DEEP_RED branch — the validator that is supposed to police homebrew magic descriptors
  (a Jade/authoring concern) is dead in production.
- **Tension + pacing (ADR-024/025)** are the mechanical backing for the narrator's
  pacing decisions. Without them the narrator has no dual-track signal and improvises
  pacing entirely — exactly the "convincing narration, zero mechanical backing" the OTEL
  lie-detector principle exists to catch. Restoring them gives the GM panel a real
  pacing signal to observe.

## Technical Architecture

All three fixes are **integration, not reimplementation** — the components already
exist and are tested. The work is to connect them and prove the connection.

### The shared anti-pattern and its fix shape

```
EXISTS (tested in isolation)        MISSING (production wiring)         THIS EPIC ADDS
─────────────────────────────       ───────────────────────────        ──────────────
magic plugin modules + registry  →  no prod import of plugins pkg   →   prod import + wiring test (81-1)
TensionTracker class + OTEL       →  never instantiated in prod      →   per-session tracker + feed (81-2)
TurnContext.pacing_hint field     →  never set (sole ctor omits it)  →   derive hint from tracker (81-3)
```

### 81-1 — Magic plugin registration (independent)

- **Gap:** `sidequest/magic/__init__.py:24` imports `MAGIC_PLUGINS` from `sidequest.magic.plugin`
  (the empty registry dict, `plugin.py:37`) but **nothing in production imports the
  `sidequest.magic.plugins` package**, whose star-imports (`plugins/__init__.py:8-10`)
  fire the per-module `MAGIC_PLUGINS[id] = ...` side-effects. Only tests import it
  (`tests/magic/conftest.py:24`, `tests/magic/test_wiring.py:29`).
- **Consumer that breaks:** `magic_validate()` at `sidequest/server/narration_apply.py:813`
  → `sidequest/magic/validator.py:107-123` takes the `plugin_known_but_not_registered`
  DEEP_RED branch for any descriptor-registered plugin because the registry is `{}`.
- **Fix surface:** trigger the registration side-effect from a production path. Preferred:
  `sidequest/magic/__init__.py` imports the `plugins` package (mirrors the
  `sidequest/telemetry/spans/__init__.py` star-import-of-domain-modules pattern that
  `plugins/__init__.py`'s own docstring cites). Guard against import cycles.
- **Wiring-test note:** the *existing* `test_wiring.py` is insufficient — it imports the
  plugins package itself, so it is green while production is empty. The new test must
  populate via a production entrypoint (`import sidequest.magic`) **without** importing
  `sidequest.magic.plugins` directly.

### 81-2 — TensionTracker producer (foundational)

- **Gap:** `TensionTracker` (`sidequest/game/tension_tracker.py:266`; `record_event` :322,
  `pacing_hint` :359) is never instantiated outside tests.
- **Fix surface:** give each session a `TensionTracker` on `_SessionData`
  (`sidequest/server/session_state.py`, alongside `entity_store` at :245) and call
  `record_event(...)` from the turn-processing path as combat/scene events resolve. The
  tracker already emits OTEL (`test_tension_tracker_otel_wiring`); those spans should now
  fire in real turns.
- **Persistence:** per-session in-memory is sufficient for v1; resume-time rehydration is
  an open assumption (log a deviation if it proves load-bearing).

### 81-3 — PacingHint consumer/bridge (depends on 81-2)

- **Gap:** `TurnContext.pacing_hint` (`orchestrator.py:728`, `PacingHint | None = None`) is
  never set; the sole construction site `sidequest/server/session_helpers.py:1158` omits
  it, so the orchestrator's injection at `orchestrator.py:2648-2653`
  (`if context.pacing_hint is not None: register_pacing_section(...)`) never fires.
- **Fix surface:** at the `session_helpers.py:1158` `TurnContext(...)` construction, derive
  the hint from the session `TensionTracker` (81-2) via `tracker.pacing_hint(thresholds)`
  using the genre's `DramaThresholds`, and pass it in. Then `[PACING]` injects into the
  narrator prompt, and a watcher event should record the computed hint.
- **Explicitly out of scope (deferred in code):** the original quiet-turn pre/post
  game-state diff, and the accelerator/decelerator keyword scan stubbed at
  `sidequest/game/trope_tick.py:226-230`.

### Conventions

- Line numbers above are 2026-06-03 anchors and may drift — **navigate by symbol name**,
  not line (this is itself a lesson from the audit; the minor-finding bulk was line rot).
- Each story ships at least one wiring test that **fails on current code and passes after
  the fix**, plus OTEL/watcher emission where the subsystem makes a decision the GM panel
  should be able to verify.

## Cross-Epic Dependencies

**Depends on:**
- None external. Internal ordering only: **81-3 depends on 81-2** (the pacing hint is
  derived from the TensionTracker that 81-2 stands up). 81-1 is fully independent and can
  run in parallel.

**Depended on by:**
- No other epic consumes these directly. Downstream benefit: once 81-2/81-3 land, the GM
  panel gains a real pacing/tension signal, and any future pacing-driven narration work
  (SOUL.md "Cut the Dull Bits" / "Cost Scales with Drama") has a live substrate to build on.
