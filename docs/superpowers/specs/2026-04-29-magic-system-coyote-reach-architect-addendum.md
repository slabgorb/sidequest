# Magic System Coyote Star v1 — Architect Review Addendum

**Date:** 2026-04-29
**Reviewer:** Leonard of Quirm (Architect)
**Reviews:** `2026-04-28-magic-system-coyote-reach-implementation-design.md` (spec) +
              `2026-04-28-magic-system-coyote-reach-v1.md` (plan)
**Outcome:** **Conditional sign-off.** Implementation may proceed against Phase 1 once the
              four resolutions below are folded into the plan. Plan does not require
              structural rewrite — only the call-outs noted in §6.

---

## Scope of this review

The implementation spec asked for an architect pass on four open questions before
Iteration 1 starts. This document answers those four, plus flags a small number of
items I noticed during the codebase grounding pass that are not strictly "open
questions" but should land before Phase 1 to avoid retrofit.

I did not re-derive the framework. The design layer (`docs/design/magic-*.md`,
`docs/design/magic-plugins/*.md`) was reviewed by the GM agent across the
2026-04-27 → 2026-04-28 sessions and is sound. My focus is the implementation
contract, the reuse claims in the spec's §2a, and consistency with the surrounding
codebase.

---

## 1. Open question Q1 — `control_tier` vs `discipline_tier` vs unified `pact_tier`

**Resolution: SPLIT. Three distinct axes. Register `control_tier` in the output catalog
now; defer `discipline_tier` registration until a learned-using world ships.**

### Reasoning

The three tier names are not synonyms with author drift; they are three different
mechanical axes already in the plugin specs:

| Axis | What it measures | Plugin owners | Direction |
|---|---|---|---|
| `pact_tier` | depth of relationship with the magic source | bargained, divine, learned | each tier deepens the bond, mechanism access widens |
| `control_tier` | discipline over the wild thing the character *is* | innate | each tier reduces involuntary expression, increases aim |
| `discipline_tier` | mastery within a taught tradition | learned | each tier widens the move catalog, reduces failure |

`pact_tier` and `control_tier` answer different questions for the same character. A
voidborn at `control_tier 3` may have *no* `pact_tier` — there is no source to bond
with; the character *is* the source. A bargained_for character with `pact_tier 3` may
have no `control_tier` — they don't have to control anything; the patron does the
work. Collapsing these would require every confrontation outcome to disambiguate
"which tier" with a `target_axis` field, and Sebastien's panel readout would say
"Tier: 3" without telling him *which kind of three*.

The `learned_v1.md` spec already uses `pact_tier` as a proxy for discipline-mastery
in its confrontation outputs — that was explicitly flagged as an open call. This is
the cleanest moment to split.

### Concrete decisions for the plan

1. **Add `control_tier` to the output catalog now.** Coyote Star uses
   `innate_v1.control_tier`. The plan's Phase 1 already covers innate's tier
   mechanics; adding the catalog entry is one extra row in
   `docs/design/confrontation-advancement.md` §Output Type Catalog and one extra
   string constant in `magic/models.py::OutputType`. Register it in v1 even though
   the panel will only render it once Phase 5 wires confrontation outcomes — the
   cost is trivial and avoids a back-edit when `learned_v1` ships.

2. **`discipline_tier` registration is deferred until a learned-using world ships.**
   Coyote Star has no learned plugin in v1. Registering an unused output type would
   violate the plan's "no stubbing" principle (CLAUDE.md). The first learned-world
   story claims `discipline_tier` registration as part of its scope.

3. **`pact_tier` keeps its current scope** (bargained/divine/learned source-depth).
   No change.

4. **Document the three-axis decision** in
   `docs/design/confrontation-advancement.md` so the next plugin author doesn't
   re-litigate this. One paragraph under §Output Type Catalog:

   > Three tier-axes coexist intentionally: `pact_tier` (depth of source-relationship,
   > used by bargained/divine/learned), `control_tier` (innate-only, discipline over
   > the wild thing the character is), `discipline_tier` (learned-only, mastery
   > within a taught tradition). A character may have any subset of these
   > simultaneously — they measure different things on the same sheet.

### Forward impact

None for Phase 1 except adding `control_tier` to the catalog. A future learned-using
world claims `discipline_tier` as additive work — no retrofit on v1's code.

### Will this bite us when Iron Hills Bender Academy ships?

No. The split is what `learned_v1.md` itself wants (its own author flagged the
`pact_tier`-as-proxy as a hack). Adding `discipline_tier` then is additive: one
catalog row, one Python constant, one renderer mapping. No data migration.

---

## 2. Open question Q2 — Plugin runtime location

**Resolution: server tree, paired files. `sidequest-server/sidequest/magic/plugins/<plugin>_v1.py`
+ `<plugin>_v1.yaml`. Confirmed: NOT served from `sidequest-content/`.**

### Reasoning

The codebase already has a clean split that the plan was asking about:

- **`sidequest-content/genre_packs/.../`** — per-deployment, world-author-tunable
  data: genre packs, worlds, archetypes, lore, audio manifests. Ships via the
  content subrepo. Iterates faster than code; reload-without-restart is a goal.

- **`sidequest-server/sidequest/genre/models/*.py`** — typed Pydantic models
  describing the *shape* of content. Versioned with the server.

- **`sidequest-server/sidequest/genre/loader.py`** — reads YAML from
  `sidequest-content/`, validates against models, produces `GenrePack`. Loader
  knows the search paths (orchestrator root → CWD → `~/.sidequest/`).

A magic plugin's `.yaml` (output catalog descriptions, narrator_register defaults,
ledger_bar templates) describes the **plugin's contract** — what mechanisms are
defined, what costs they take, what flags they raise. That is plugin code's
companion, not deployment data:

- World authors don't tune a plugin's hard_limits or its required span attrs —
  those are mechanical invariants. Worlds tune which plugins are activated, what
  intensity, which factions instantiate which mechanism. Plugin tuning happens at
  plugin design time, not world design time.
- The plugin `.py` and plugin `.yaml` ship as a unit. Bumping a plugin version
  (`innate_v2`) bumps both files together; mismatched versions are a load-time
  loud-fail.
- World `magic.yaml` (which lives in `sidequest-content/genre_packs/<genre>/<world>/`)
  references plugins by id and supplies world-specific instantiation; the plugin's
  own files don't change.

If we put plugin YAML in `sidequest-content/`, we'd be inviting world authors to
edit it — and a world editing `innate_v1.yaml` is editing every other world that
uses `innate_v1` simultaneously. That's a footgun.

### Concrete decision for the plan

Keep the plan's §2b file paths as-is:

```
sidequest-server/sidequest/magic/
  __init__.py
  models.py            # Pydantic core: WorldMagicConfig, MagicState, MagicWorking, Plugin, Flag
  plugin.py            # MagicPlugin Protocol; registry primitives
  validator.py         # validate(working, world_config) -> list[Flag]
  state.py             # MagicState aggregate + apply_working
  context_builder.py   # pre-prompt context block
  plugins/
    __init__.py        # MAGIC_PLUGINS dict; star-imports each plugin module
    innate_v1.py
    innate_v1.yaml
    item_legacy_v1.py
    item_legacy_v1.yaml
sidequest-server/sidequest/genre/
  magic_loader.py      # composes genre + world magic.yaml; references MAGIC_PLUGINS

sidequest-content/genre_packs/
  space_opera/magic.yaml
  space_opera/worlds/coyote_star/magic.yaml
  space_opera/worlds/coyote_star/confrontations.yaml
```

### Forward impact

None — this matches the plan as written. Decision is a confirm, not a change.

---

## 3. Open question Q3 — Plugin registry mechanism

**Resolution: module-level dict, populated at plugin-module import time. Mirrors
`SPAN_ROUTES`. NOT a decorator, NOT an explicit `register_plugin()` call.**

### Reasoning

The codebase has a canonical pattern for this exact problem in
`sidequest/telemetry/spans/`:

```python
# spans/_core.py
SPAN_ROUTES: dict[str, SpanRoute] = {}
FLAT_ONLY_SPANS: set[str] = set()

# spans/__init__.py
from .agent import *  # mutates SPAN_ROUTES at module import
from .audio import *
# ... 30+ domain modules ...

# spans/agent.py
SPAN_AGENT_FOO = "agent.foo"
SPAN_ROUTES[SPAN_AGENT_FOO] = SpanRoute(
    event_type="state_transition",
    component="agent",
    extract=_extract_agent_foo,
)
```

Properties of this pattern that fit magic plugins:

- **Renames break at import time.** A typo in a plugin id is a load-time error,
  not a runtime "plugin not found" deferred to first usage.
- **No "did you forget to register" failure mode.** The act of importing the
  plugin module *is* registration; you cannot import without registering.
- **Test enforces completeness.** `tests/telemetry/test_routing_completeness.py`
  asserts every span constant is either in `SPAN_ROUTES` or in `FLAT_ONLY_SPANS`.
  Plug-in equivalent: a test asserts every `<plugin>_v1.py` file in
  `magic/plugins/` is imported by `magic/plugins/__init__.py` and present in
  `MAGIC_PLUGINS`.
- **Static-imports keep traceability.** Searching for "where is `innate_v1`
  registered?" lands at the plugin's own module. No runtime registry-walking.

### Concrete shape

```python
# magic/plugins/__init__.py
from .innate_v1 import *      # noqa: F401, F403  — populates MAGIC_PLUGINS
from .item_legacy_v1 import *  # noqa: F401, F403

# magic/plugin.py
MAGIC_PLUGINS: dict[str, MagicPlugin] = {}

class MagicPlugin(Protocol):
    plugin_id: str
    source: Source
    def required_span_attrs(self) -> set[str]: ...
    def validate_working(self, working: MagicWorking, config: WorldMagicConfig) -> list[Flag]: ...
    def hard_limits(self) -> list[HardLimit]: ...
    def threshold_promotions(self, crossing: ThresholdCrossing) -> list[StatusChange]: ...
    def confrontation_outputs(self, branch: str) -> list[Output]: ...

# magic/plugins/innate_v1.py
INNATE_V1_ID = "innate_v1"

class _InnateV1(MagicPlugin):
    plugin_id = INNATE_V1_ID
    # ... implementation ...

MAGIC_PLUGINS[INNATE_V1_ID] = _InnateV1()
```

### Test contract

`tests/magic/test_plugin_registry.py` asserts:

1. Every `<plugin>_v*.py` file in `magic/plugins/` (excluding `__init__.py`) has
   exactly one entry in `MAGIC_PLUGINS` whose `plugin_id` matches the file stem.
2. Every entry in `MAGIC_PLUGINS` is reachable from
   `magic.plugins.__init__` via star-imports (i.e., not orphaned).
3. `MAGIC_PLUGINS` keys are unique (Python's dict-overwrite is silent — the test
   makes it loud).

This is the magic equivalent of `test_routing_completeness.py`. Plan Phase 1
Task 1.2 (Plugin Protocol + Registry) should incorporate this.

### Forward impact

The plan's Task 1.2 already names "Plugin Protocol + Registry." This resolution
fixes the registry shape and the test contract. Cost: zero schedule impact;
the work was already in scope.

---

## 4. Open question Q4 — `MagicState` initialization for legacy saves

**Resolution: `magic_state: MagicState | None = None` field on `GameSnapshot`.
No `@model_validator` migration. World materialization populates from
`magic_loader` when the world has `magic.yaml`; otherwise stays `None`.**

### Reasoning

`GameSnapshot` already has the patterns this needs:

- `model_config = {"extra": "ignore"}` covers forward-compat for legacy saves
  missing the field. Pydantic treats absent optionals as `None` automatically;
  no validator needed.
- Existing optional features use the same pattern:
  - `encounter: StructuredEncounter | None = None`
  - `scenario_state: ScenarioState | None = None`
  - `pending_resolution_signal: ResolutionSignal | None = None`
- The `@model_validator(mode="before")` pattern is reserved for **renames**
  (see the existing `_migrate_legacy_resource_fields` validator). There is no
  old field to migrate from for `magic_state` — it's net-new — so no validator
  is warranted.
- Per project memory ("Legacy saves are throwaway"): `debug_state.snapshot_load_failed`
  warnings on old saves are not bugs. The "init empty, no warning" path the
  spec specifies is the project policy.

### Lifecycle

```
Save without magic_state    →  GameSnapshot.magic_state = None  (Pydantic default)
Save with magic_state       →  GameSnapshot.magic_state = MagicState(...)
World materialization       →  if world has magic.yaml and magic_state is None:
                                 magic_state = magic_loader.materialize(world)
                               else if world has no magic.yaml:
                                 magic_state stays None
                               (else: keep loaded state — preserve in-progress play)
```

The "World materialization populates from `magic_loader`" step is the spec's
"plugin instances eager-instantiated at world-load time" decision (locked
decision D1). It runs once per session-start in
`game/world_materialization.py`. The `if magic_state is None` guard handles both
the first-load case AND the legacy-save-resumes-on-magic-world case identically.

### Worlds without magic.yaml

`magic_state` stays `None`. Pre-prompt context builder (Task 3.1) returns an
empty string for these worlds — no "ACTIVE MAGIC CONTEXT" block in the
narrator's pre-prompt. `StateDelta.magic` stays `False`. UI's `LedgerPanel`
component (Task 4.2) renders nothing when `magic_state` is `None`.

### Concrete decisions for the plan

- Plan §2c says "Add `magic_state: MagicState | None` field." Confirmed. The
  spec already has it right.
- Phase 2 Task 2.3 ("Add magic_state field to GameSnapshot") needs no
  legacy-migration validator. **Plan should explicitly call this out** — there
  is a non-zero risk Dev sees the existing `_migrate_legacy_resource_fields`
  pattern and writes a validator out of misplaced symmetry. The plan should
  say: "No `@model_validator` for this field. Pydantic's default-None
  handling is exactly what we want."
- Phase 2 Task 2.5 (SQLite roundtrip) test should include a "load a save that
  predates the field" case asserting `magic_state == None` and no warning.

### Forward impact

Zero — matches plan. This is a confirm + a reminder for Dev.

---

## 5. Items not in the open-questions list but worth landing now

These surfaced during the grounding pass. Each is small; none rewrite the plan.

### 5.1 Plugin contract YAML composition order

The plan §2f shows plugin `.yaml` containing `narrator_register` defaults. World
`magic.yaml` *also* has a `narrator_register` (the Coyote Star paragraph in spec
§1 "Narrator register"). Composition order should be:

1. Plugin's `.yaml` provides the **default** narrator_register (the genre-neutral
   plugin voice).
2. Genre `magic.yaml` MAY override (genre-flavored plugin voice).
3. World `magic.yaml` MAY override (world-flavored plugin voice).

Last-writer-wins per field. Loader assembles in this order; `WorldMagicConfig`
holds the materialized result. Coyote Star uses (3) — it sets a world-specific
register that wins over the plugin default.

**Plan action:** Phase 1 Task 1.6 (`Magic loader`) should make this composition
order explicit in its docstring and have a test that exercises all three
override layers.

### 5.2 DEEP_RED handling — clearly mark "v1 = flag-only"

The handoff doc (Locked Decision #7) says "DEEP RED can interrupt narration."
The implementation spec (§5d) says "v1 does not interrupt narration — flag-only."
These are not contradictions — v1 ships the flag-only behavior as a deliberate
deferment — but the validator's DEEP_RED handler will be visible code, and a
later contributor reading it cold may "fix" the omission.

**Plan action:** Phase 1 Task 1.5 (`magic.validator`) should include a
`# v1: flag-only emission. Interrupt path is a future iteration.` comment at the
DEEP_RED branch, with an explicit extension point (e.g., a no-op
`on_deep_red_violation` hook callable that future iterations wire up). Keep it
trivially extensible without writing the extension now.

### 5.3 Status auto-promotion — the threshold→Status mapping is config, not code

Plan §3.4 hardcodes `bar_id → (status_text, severity)` mappings:
`sanity → ("Bleeding through", Wound)`, `notice → ("Marked", Wound)`, etc.

This is plugin-content, not engine-content. It belongs in the plugin's `.yaml`
(under a `threshold_promotions:` block per plugin), keyed by `bar_id` →
`{status_text, severity, threshold_value, direction}`. The validator/state
machine reads from there.

Rationale: when `victoria` ships and `notice` becomes `infamy`, the world author
should not be editing `narration_apply.py` to retitle the status. They edit
their plugin's YAML.

**Plan action:** Phase 3 Task 3.4 should pull the mapping table out of code
and into `innate_v1.yaml` / `item_legacy_v1.yaml` under a new
`threshold_promotions:` block. ~30 LOC saved in code; ~20 LOC of YAML added.
Net-zero on size, large win on extensibility.

### 5.4 The "wiring test per suite" is structurally important — keep it

Plan Phase 1 Task 1.8 ("Phase 1 wiring + cut-point verification") and the
embedded wiring tests across phases match CLAUDE.md's "Every Test Suite Needs
a Wiring Test." This is doing the right thing; flagging it explicitly as
load-bearing so review cycles don't relax it.

### 5.5 OTEL `magic.working` span name reservation

Plan Phase 3 Task 3.5 registers `magic.working` in `SPAN_ROUTES`. The span name
matches the existing telemetry naming convention (`<domain>.<event>`).
`tests/telemetry/test_routing_completeness.py` will catch unreached span
constants — make sure the new `magic.py` submodule is added to the
`spans/__init__.py` star-import list, or completeness tests will fail.

**Plan action:** Phase 3 Task 3.5 should explicitly mention adding `from .magic
import *` to `spans/__init__.py`. It's a one-liner that's easy to miss.

### 5.6 Multi-repo PR strategy

The plan touches three repos: `sidequest-server`, `sidequest-content`,
`sidequest-ui`. Phase 1 ends with two PRs (server + content). Phase 4 adds a
third (ui). The plan already calls this out, but the `sidequest-content`
subrepo targets... I don't know without reading `repos.yaml`. Implementer
should check `repos.yaml` per CLAUDE.md before opening any PR. Flagging because
this is the kind of mistake that wastes a half-hour at the end of an
otherwise-clean phase.

---

## 6. Conditional sign-off — what the plan should fold in before Phase 1 starts

| Action | Where | Effort |
|---|---|---|
| Add §1 resolution: `control_tier` registers in v1, `discipline_tier` deferred, `pact_tier` unchanged | `confrontation-advancement.md` Output Catalog + `magic/models.py::OutputType` enum | 1 catalog row + 1 enum value |
| Add §2 confirmation: plugin runtime location is server tree (no change to plan) | (no edit; confirmation only) | — |
| Add §3 resolution: `MAGIC_PLUGINS` module-level dict + completeness test | Plan Task 1.2 | already in scope; resolves shape |
| Add §4 reminder: NO `model_validator` for `magic_state`; rely on Pydantic default-None | Plan Task 2.3 (one-line note) | trivial |
| Add §5.1: plugin/genre/world `narrator_register` composition order + test | Plan Task 1.6 | one extra test case |
| Add §5.2: DEEP_RED extension-point comment in validator | Plan Task 1.5 | one comment |
| Add §5.3: pull threshold-promotion mapping into plugin YAML | Plan Task 3.4 | minor scope shift, no new size |
| Add §5.5: register `magic.py` in `spans/__init__.py` star-imports | Plan Task 3.5 | one line |

**None of these are structural rewrites.** They are call-outs that make existing
work concrete and avoid known-shape pitfalls.

---

## 7. What I am NOT signing off on

- **The Coyote Star `magic.yaml` content itself.** That is GM lane (writer),
  not architect. The schema is sound; whether `sanity 0.40 → Bleeding-Through`
  is the right tuning for the playgroup is a writer/playtest call.
- **Phase 5 confrontation orchestration.** Spec §5d rightly defers
  multi-session confrontations and obligation_scales orchestration. Coyote
  Reach uses neither. When a heavy_metal world ships, the architect sign-off
  for those open implementation patterns (handoff doc Open Issues #4, #5, #6,
  #7) is a separate review. v1 is intentionally narrower.
- **Phases 4/5/6 cut-points.** These are human playtests with the playgroup,
  not architect-verifiable. SDD execution should stop at the end of Phase 4
  Task 4.4 (last machine-checkable cut). Phase 5 starts after solo demo
  feedback; Phase 6 starts after two-player playtest feedback.
- **Effort estimate.** 18-22 engineering-days is the spec's number. I have no
  reason to dispute it; I have no basis to confirm it. It is what it is.

---

## 8. Recommendation

**Sign off conditional on §6 fold-ins. Proceed with Phase 1 via SDD.**

Phase 1 is the highest-risk iteration (the spec correctly identifies
"content authoring surfaces schema gaps" as the #1 risk). Stopping at Phase 1
cut-point — `pytest sidequest/magic` passes, no game integration — is the
right machine-verifiable boundary before committing to Phases 2-3. If
Coyote Star `magic.yaml` authoring (Task 1.7) surfaces schema gaps, fix
them in Phase 1 and re-emit the PR. Phases 2+ stay clean.

Recommended next session sequence:

1. User folds §6 into the plan (or asks Architect to do it as a one-shot edit).
2. User confirms scope: Phase 1 only, or Phase 1 + onward.
3. Set up worktree on a new branch (`feature/magic-coyote-reach-v1`).
4. Commit current `docs/superpowers/{plans,specs}/2026-04-28-*` + this addendum
   as the design corpus on that branch.
5. SDD against Phase 1's 8 tasks.
6. STOP at Phase 1 cut-point. User decides whether to continue.

— Leonard of Quirm

> *I'm rather fond of this approach. The mechanism is sound; the levers go in
> the obvious directions; the failure modes ring loud bells rather than going
> "tic" quietly in the night. I would not, however, like to be the gentleman
> who has to explain to Vetinari why the pre-prompt context block contains
> a line that nothing reads. Leave nothing dangling. The mark of a good
> machine is that every visible piece does something.*
