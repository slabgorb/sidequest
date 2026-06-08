# Feature Inventory Surfacing — Design Spec

**Date:** 2026-06-03
**Status:** Approved (brainstorming) — ready for implementation planning
**Author:** Tech Writer (GM/content lane); generator + harness implementation hands off to Dev
**Supersedes maintenance model of:** `docs/feature-inventory.md` (hand-maintained)

---

## 1. Problem

`docs/feature-inventory.md` is a hand-maintained markdown ledger of shipped
features, each row tagged with a status (Live & Wired / Live (partial) / Dark /
Deferred / Draft). Because nothing binds the status column to reality, it
**drifts**: a 2026-06-03 audit found stale `genre_workshopping/` and
`low_fantasy` claims throughout, and "Live & Wired" rows whose backing could not
be confirmed by reading the doc. The doc's own definition of "Live & Wired" is
*"OTEL-emitting"* — a machine-checkable property the doc never actually checks.

The project already has the signal needed to check it:

- A **structured span registry** — `sidequest-server/sidequest/telemetry/spans/`
  declares `SPAN_* = "name"` constants and registers each in a `SPAN_ROUTES`
  dict. "What the engine routes" is machine-readable.
- **Wiring tests** by naming convention (`*wiring*.test.tsx`, `test_wiring.py`).
- **Filesystem facts** — packs, worlds, `draft: true` in `world.yaml`.
- **ADR frontmatter** — status/verdict per subsystem (incl. the ADR-087 RESTORE
  roster), already parsed by `scripts/regenerate_adr_indexes.py`.
- **A capture path** — `scripts/playtest.py` + `scripts/playtest_otlp.py` (OTLP
  receiver) already observe emitted spans during headless playtests.

## 2. Goals / Non-goals

**Goals**
- Feature status is **derived and verified against reality**, never asserted by a
  hand-edit alone. A stale claim fails the build, loudly, naming the row.
- Preserve the irreplaceable human value: *what the feature does*, *where it
  lives in code* (grep target), and *how to manually test it*.
- Prove "Live & Wired" means the span actually **fired**, not merely that it is
  registered (the "nail it" standard — observed-emission in scope).
- Generated like the ADR index: single source → generator → markdown → CI guard.

**Non-goals**
- Not a live real-time dashboard (the GM `/dashboard` already serves runtime
  observation). This produces a **committed, reviewed, build-guarded artifact**.
- Not auto-discovery of features from code (a raw span dump is not a feature
  inventory — the human prose is the point).
- Does not replace the GM panel; it complements it by freezing a verified
  snapshot into the repo.

## 3. Architecture

```
docs/feature-inventory/<category>.yaml      ← source manifest (per-category files)
        │   human prose + evidence anchors
        ▼
scripts/regenerate_feature_inventory.py      ← generator
   1. load manifest (glob the directory)
   2. load verification inputs:
        • SPAN_ROUTES keys      (static-parse telemetry/spans/*.py)
        • wiring-test files      (glob)
        • module paths           (filesystem existence)
        • world draft flags      (parse world.yaml)
        • ADR statuses           (frontmatter, reuse ADR-index parser)
        • observed spans         (docs/feature-evidence/observed-spans.json)
   3. verify each feature's claimed status against its evidence
   4. emit docs/feature-inventory.md (static preamble preserved between markers)
   5. emit coverage reports; exit non-zero on any verification failure
        │
        ├─► docs/feature-inventory.md        (generated)
        ├─► coverage: declared-but-never-fired   → FAIL
        └─► coverage: registered-but-never-observed → WARN (logged, never silent)

scenarios/feature-evidence/*.yaml            ← reference suite (forces each subsystem to engage)
        │
        ▼
just feature-evidence                         ← runs suite headless, OTLP receiver captures spans
        ▼
docs/feature-evidence/observed-spans.json     ← union of fired spans, scenario-attributed, stamped

CI / just guard: regen clean (git-diff) ∧ no verification failure ∧ capture fresh
```

The generator never invents status. The human **declares** status + evidence;
the generator **refuses to let a claim stand without backing**. That is the
can't-lie property.

## 4. Components

### 4.1 Source manifest — `docs/feature-inventory/<category>.yaml`

Per-category files (mirrors the doc's existing section structure, matches the
ADR per-file precedent, keeps merge-conflict surface small). Each file holds a
list of feature records:

```yaml
# docs/feature-inventory/confrontation-engine.yaml
category: Confrontation Engine
features:
  - id: confrontation_engine
    name: Confrontation engine (genre-typed resource pools)
    modules: [game/encounter.py, game/resource_pool.py]   # grep targets; existence-checked
    ui: ConfrontationOverlay                                # component name or "—"
    manual_test: "Take a turn that triggers a confrontation → overlay shows momentum/resource bars"
    status: live_wired              # human CLAIM — generator must verify it
    evidence:
      spans: [confrontation.beat_selected, confrontation.resolved]
      wiring_tests: [sidequest-ui/src/__tests__/confrontation-wiring.test.tsx]
      adr: 033
```

Evidence anchor types (a row supplies whichever prove its claim):

| Anchor | Verified against | Proves |
|---|---|---|
| `spans` | `SPAN_ROUTES` keys ∧ `observed-spans.json` | routed ∧ fired |
| `wiring_tests` | filesystem glob (Phase 1) / suite pass (later) | exercised path exists |
| `modules` | filesystem existence (see resolution rule) | grep target is real (catches renames) |

> **Module resolution rule.** `modules` entries appear today in mixed forms
> (`server.websocket`, `game/encounter.py`, `ConfrontationOverlay.tsx`). The
> generator normalizes each entry to a file path relative to its owning repo —
> server dotted/path forms resolve under `sidequest-server/sidequest/`, UI
> component names resolve under `sidequest-ui/src/` (glob by basename) — and
> fails the row if no file resolves. The migration normalizes existing entries
> to one consistent form per repo.
| `adr` | ADR frontmatter status | deferred/dark/partial provenance |
| `draft_world` | `world.yaml` `draft:` flag | content gated, not shipped |

`status` enum: `live_wired`, `live_partial`, `dark`, `deferred`, `draft`,
`engineering` (internal seam, no manual test — exempt from span proof).

### 4.2 Generator — `scripts/regenerate_feature_inventory.py`

- Mirrors `regenerate_adr_indexes.py` conventions (static parsing, preamble/
  trailer preservation between generated-block markers, idempotent re-run).
- **Static-parses** `telemetry/spans/*.py` for `SPAN_* = "literal"` constants and
  their `SPAN_ROUTES[...] =` registrations rather than importing the server
  package (keeps the doc script free of server runtime deps — same discipline as
  the ADR generator).
- Emits `docs/feature-inventory.md`: the existing static preamble (Purpose,
  Legend, "How To Use As A Testing Index", smoke-pass) is preserved verbatim
  between markers; only the per-category feature tables are generated.
- Exit non-zero with a named-row report on any verification failure.

### 4.3 Status-verification rules

| Claimed status | Passes when… |
|---|---|
| `live_wired` | ≥1 span ∈ `SPAN_ROUTES` **and** ∈ `observed-spans.json` (fired) **and** ≥1 declared wiring-test file exists |
| `live_partial` | span routed **or** wiring test exists, but not the full three-legged set; **or** `adr` flags a known gap |
| `dark` | no observable span; `adr` present and on the ADR-087 RESTORE roster (data model only) |
| `deferred` | `adr` frontmatter status ∈ {deferred, proposed} |
| `draft` | `draft_world` predicate resolves `draft: true` on disk |
| `engineering` | no manual-test/span obligation; `modules` must still exist |

Any declared `modules` path that no longer exists fails verification regardless
of status (catches silent renames — a grep target that lies is as bad as a
status that lies).

### 4.4 Observed-emission tier (the "actually fired" proof)

- **`scenarios/feature-evidence/*.yaml`** — a reference suite of scripted
  scenarios whose actions **force** each span-bearing subsystem to engage
  (combat, magic cast, confrontation resolution, trope tick, MP seat/presence,
  image render, music cue, dogfight, trial, auction, …).
- **`just feature-evidence`** — runs the suite headless against server + daemon;
  the OTLP receiver (`scripts/playtest_otlp.py`) records every emitted span name,
  attributed to the scenario that fired it.
- **`docs/feature-evidence/observed-spans.json`** — committed artifact: the
  **union** of spans observed across the suite, each with the scenario(s) that
  triggered it and a capture timestamp + server git SHA.
- The generator intersects each feature's declared `spans` with this set for the
  `live_wired` proof.

### 4.5 Coverage reports

- **Declared-but-never-fired** — a feature claims `live_wired` but a declared span
  never appears in `observed-spans.json` → **FAIL**. This is exactly the
  "convincing narration, zero mechanical backing" lie the GM panel exists to
  catch, now enforced at build time.
- **Registered-but-never-observed** — spans in `SPAN_ROUTES` no scenario ever
  triggers → **WARN** (logged loudly, never silently dropped). Ambiguous between
  dead route and missing scenario; surfaced for human triage, not auto-failed.

## 5. Determinism strategy (the load-bearing risk)

Span *values* are non-deterministic (LLM narration); span *emission* is mostly
deterministic given scripted actions — **except** where LLM-mediated routing
(Intent Router, ADR-123 confidence gates) decides whether a subsystem engages.
A single run can miss a span the narrator chose not to trigger. Mitigations
(all normative in this design):

1. **Unambiguous scenario actions** — drive actions that force the intended
   classification ("attack the bandit", not "approach warily"), so the routing
   decision is not a coin-flip.
2. **Union across K runs** — `observed-spans.json` is the union over K repetitions
   of the suite (K configurable, default ≥3). A span seen in *any* recent run
   counts as fired.
3. **Freshness window** — `observed-spans.json` carries a capture timestamp and
   server git SHA. A CI staleness check fails when the capture predates the
   current server HEAD beyond a configured window, so an old capture cannot vouch
   for new code.

Honest boundary, stated in the generated doc: `live_wired` means "routed ∧
observed-firing-under-exercise ∧ wiring-tested," not "fires on every possible
path." Where the suite cannot force a subsystem deterministically, the feature
is downgraded to `live_partial` with a noted reason rather than over-claimed.

## 6. Migration = the correctness pass

Porting the existing `docs/feature-inventory.md` rows into the per-category
manifests **is** the requested content update. Every row must name evidence; the
generator rejects any row whose evidence does not verify. All current stale
claims therefore surface **mechanically**, not by manual eyeballing. Phaseable
category-by-category; un-migrated legacy sections remain as static prose between
the preamble markers until their manifest lands.

## 7. CI / `just` guards

- `just feature-inventory-check` — regen + `git diff --exit-code` on
  `docs/feature-inventory.md` (stale committed doc fails) + non-zero generator
  exit on verification failure.
- `just feature-evidence` — capture refresh (operator/CI-scheduled, since it
  needs a live server+daemon); writes `observed-spans.json`.
- Freshness guard — capture timestamp vs. server HEAD within window.

## 8. Testing

- Generator unit tests: golden manifest → expected markdown; injected
  bad-evidence rows (span not in registry; missing wiring test; renamed module;
  declared-but-never-fired span) → expected named failures.
- A wiring test for the generator itself (per project doctrine: every test suite
  needs a wiring test) — asserts the generator is invoked by the `just`/CI guard
  and that its output path is the committed doc.
- Reference-suite smoke: `just feature-evidence` produces a non-empty,
  schema-valid `observed-spans.json`.

## 9. Phasing (for the implementation plan)

- **Phase 1 — Manifest + static verification + migration.** Schema, generator,
  static anchors (SPAN_ROUTES membership, wiring-test/module existence, ADR,
  draft), preamble preservation, CI git-diff guard. Migrate all existing rows;
  every current stale claim surfaces. (`live_wired` provisionally = routed ∧
  wiring-tested until Phase 2.)
- **Phase 2 — Observed-emission.** Reference-scenario suite, `just
  feature-evidence` capture, `observed-spans.json`, three-legged `live_wired`
  rule, freshness guard.
- **Phase 3 — Coverage reports.** Declared-but-never-fired (FAIL),
  registered-but-never-observed (WARN), wired into CI.

## 10. Open questions (resolve during planning)

- Exact `K` (suite repetitions) and the freshness window duration.
- Whether `wiring_tests` verification stays at "file exists" (Phase 1) or
  escalates to "test passes in CI" (heavier; couples doc regen to the test run).
- Naming-collision policy for `id` across category files (must be globally
  unique; generator enforces).
