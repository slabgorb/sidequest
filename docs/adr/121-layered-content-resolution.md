---
id: 121
title: "Layered Content Resolution — Global→Genre→World→Culture Merge with Per-Field Strategies and Provenance"
status: accepted
date: 2026-05-31
deciders: ["Keith Avery", "Neo (Architect)"]
supersedes: []
superseded-by: null
related: [3, 60, 82]
tags: [core-architecture]
implementation-status: partial
implementation-pointer: "Resolver.resolve_merged four-tier walk is dead code; production uses two-tier shim (archetype/shim.py) — sprint story 82-4 (wire or narrow)"
---

# ADR-121: Layered Content Resolution

> **Documents a system already live in code.** The `LayeredMerge` base class,
> the `MergeStrategy` taxonomy, the `Resolver[T]` / `Resolved[T]` walk, and the
> `Provenance` / `MergeStep` wire types shipped during the Rust→Python port
> (ADR-082) without a governing ADR — they are the Python port of the Rust
> `#[derive(Layered)]` proc-macro + `Resolver<T>` system. This record closes
> that architecture-of-record gap and states what the decision *was*.

## Context

SideQuest content is layered. A single resolved content object — an archetype, a
tone axis, a faction stub — is rarely defined in one place. The doctrine
"Crunch in the Genre, Flavor in the World" (SOUL.md, ADR-003) means a value can
be introduced at a base/global tier, refined by the genre rulebook, overridden by
a specific world, and finally specialized by a culture *within* that world. The
engine needs a deterministic, inspectable way to assemble the final object from
those overlapping tiers.

The Rust prototype solved this with a `#[derive(Layered)]` proc-macro: each model
declared per-field merge behavior via attributes, and the macro emitted a `merge`
implementation; a `Resolver<T>` walked the tier files and produced a `Resolved<T>`
carrying both the value and its provenance. ADR-082 ported the backend from Rust
to Python. Proc-macros have no Python equivalent, so the macro's
compile-time-generated behavior had to be re-expressed as runtime logic — but the
*semantics* (tier order, per-field strategies, provenance trail) had to survive
the port unchanged so existing content files kept resolving identically.

This is **distinct from `loader.py`'s flat-file loads.** `loader.py`
(`load_genre_pack`, ADR-003) reads whole pack files into models. The layered
resolver governs how a *structured content object* is assembled *across tiers*,
recording where each contribution came from. The loader answers "what does this
file contain"; the resolver answers "what is the final value of this axis after
Global, Genre, World, and Culture have each had their say, and which file decided
each field."

Neither ADR-003 (Genre Pack Architecture) nor ADR-060 (Genre Models
Decomposition) governs this merge engine — see *Reconciliation* below.

## Decision

**A four-tier merge walk — Global → Genre → World → Culture — is implemented as a
runtime pydantic base class (`LayeredMerge`) that reads per-field merge strategies
from field metadata at merge time, paired with a `Resolver[T]` that walks the tier
files on disk and emits a `Resolved[T]` carrying the value plus full
`Provenance`.** The provenance types live in the protocol package so they can ride
on wire payloads to the GM panel.

### The four-tier walk

`Resolver[T].resolve_merged(axis, field_path, ctx)`
(`genre/resolver.py`) walks exactly four tiers, in a fixed order, each
optional, each merging *into* the accumulated value when its file exists:

1. **Global** — `{root}/{field_path}.yaml` (`resolver.py`)
2. **Genre** — `{root}/{genre}/{field_path}.yaml` (`resolver.py`)
3. **World** — `{root}/{genre}/worlds/{world}/{field_path}.yaml`
   (`resolver.py`), only when `ctx.world` is set
4. **Culture** — `{root}/{genre}/worlds/{world}/cultures/{culture}/{field_path}.yaml`
   (`resolver.py`), only when both `ctx.world` and `ctx.culture` are set

The tier order is not configurable; it is fixed both in the `Tier` enum docstring
("Always walked in this order: Global, Genre, World, Culture",
`provenance.py`) and in the straight-line structure of `resolve_merged`. A
deeper tier always merges into the value produced by all shallower tiers. The
first tier to supply a file produces the value with `ContributionKind.initial`;
each subsequent tier merges with `ContributionKind.merged` (`resolver.py`,
`328-330`, `361-363`). If no tier supplies the field, the walk raises
`GenreValidationError` (`resolver.py`) — no silent empty default, honoring
*No Silent Fallbacks*. (`Resolver.resolve`, `resolver.py`, is the
single-file World-tier convenience load; `resolve_merged` is the full walk.)

`ResolutionContext` (`resolver.py`) carries the three keys that locate the
deeper-tier files: `genre` (required), `world` (required for World/Culture), and
`culture` (required for Culture only).

### The `MergeStrategy` taxonomy

Each field on a `LayeredMerge` subclass declares how a deeper tier's value
combines with the shallower one, via
`Field(json_schema_extra={"merge": ...})`. `MergeStrategy`
(`resolver.py`) defines four strategies, mapping 1:1 onto the Rust
`MergeStrategy` enum:

- **`replace`** — the deeper tier's value wins outright (`resolver.py`,
  returns `other_val`). Mirrors the Rust proc-macro emitting `other.#ident`.
- **`append`** — the deeper tier's list concatenates onto the shallower one,
  shallower items first: `list(self_val) + list(other_val)` (`resolver.py`).
- **`deep_merge`** — recurse into nested `LayeredMerge` instances via
  `self_val.merge(other_val)`; raises `TypeError` if either side is not a
  `LayeredMerge` (`resolver.py`).
- **`culture_final`** — a *documentation-only* semantic signal (see Invariants).

`LayeredMerge.merge` (`resolver.py`) walks every field, reads its strategy
from `json_schema_extra`, and dispatches through `_apply_strategy`
(`resolver.py`), returning a new instance of the same type. An unknown
strategy string raises `ValueError` (`resolver.py`).

### Runtime base class, not code-gen

The choice to re-express the Rust proc-macro as a **runtime pydantic base class**
(reading `json_schema_extra` metadata at merge time) rather than a Python code
generator is deliberate. Python has no compile step into which a derive-macro
equivalent would slot; a code generator would reintroduce a build artifact and a
generated/source skew with no offsetting benefit. The base class keeps the merge
contract co-located with the model definition (the `Field` declaration *is* the
contract) and lets the merge walk be a single ~25-line method instead of N
generated `merge` impls. See *Alternatives considered*.

## Invariants / Contracts

- **`culture_final` has NO runtime enforcement.** Its merge behavior is
  *identical to `replace`* — `_apply_strategy` returns `other_val` for both
  (`resolver.py`). Nothing in the resolver checks that only the Culture
  tier sets a `culture_final` field; a World or Genre tier can set it and the
  merge will happily accept it. This is a **deliberate parity-with-Rust choice**:
  the Rust proc-macro emitted `other.#ident` for both `Replace` and
  `CultureFinal` variants, so the distinction was documentation-only there too
  (`resolver.py`). **This is a trap for future engineers** — the strategy
  name *reads* like a guard ("this field is final at the Culture tier") but
  enforces nothing. Treat `culture_final` strictly as authorial intent
  annotation. If true enforcement is ever wanted, it is a *new* decision, not a
  bug fix, and must be reconciled against Rust parity (see Consequences).

- **Tier order is fixed and total.** Global → Genre → World → Culture, no
  reordering, no per-pack override. A deeper tier never executes before a
  shallower one; the merge accumulator only ever flows downhill.

- **Every field is expected to declare a strategy.** `LayeredMerge.merge` reads
  `extra.get("merge", "replace")` (`resolver.py`) — so an *undeclared* field
  falls back to `replace`. The base-class docstring states every field MUST carry
  a `"merge"` key and that **per-type wiring tests** enforce this on concrete
  subclasses (`resolver.py`, `109-113`). The `"replace"` default in
  `merge` is a structural safety net, not a license to omit the declaration —
  omission is caught by the subclass wiring test, not silently tolerated.

- **`deep_merge` is type-guarded.** It requires both sides to be `LayeredMerge`
  instances and raises `TypeError` otherwise (`resolver.py`) — a misdeclared
  `deep_merge` on a scalar field fails loud, not silently.

- **Provenance is mandatory output.** Every `Resolved[T]` carries a `Provenance`
  with a non-optional ordered `merge_trail: list[MergeStep]`
  (`provenance.py`). The final `source_tier`/`source_file` record the
  deepest tier that contributed (`resolver.py`). Resolution that produces
  a value also always produces the audit trail of how.

## Observability

Provenance *is* the GM-panel surface for this subsystem, satisfying the project's
OTEL/lie-detector principle: the panel must be able to verify the engine engaged
rather than the narrator improvising content origins.

- `Provenance` and `MergeStep` (`provenance.py`) are `ProtocolBase` types,
  living in `sidequest/protocol/` precisely so they **travel on the wire as part
  of `GameMessage` payloads** (`provenance.py`, `resolver.py`). The
  GM panel can therefore show, for any resolved value, which tier produced it and
  the full chain of contributions.
- `MergeStep` records `tier`, `file`, an optional source `span`
  (line/column range, `Span`, `provenance.py`), and a `ContributionKind`
  (`initial` / `replaced` / `appended` / `merged`, `provenance.py`). The
  trail is the human-auditable answer to "where did this archetype's `name` come
  from, and which tier last touched its `tags`."
- The `Resolver` constructs a `MergeStep` at each contributing tier with the file
  path and contribution kind (`resolver.py`, `290-297`, `314-321`,
  `339-346`, `372-379`), and assembles them into the final `merge_trail`.

**Honesty caveat (current state):** `span` is always emitted as `None` by the
resolver today (`resolver.py`, `292`, etc.) — the line/column range is wired
through the *type* and the wire payload but the resolver does not yet populate it
from the YAML parse. The `ContributionKind` set the resolver emits is `initial`
and `merged`; the finer `replaced` / `appended` distinctions exist in the enum but
are not yet emitted per-field (the trail records a tier-level `merged`, not a
per-field breakdown). These are panel-fidelity gaps, not correctness gaps — the
trail is accurate about *which tiers and files contributed in what order*.

## Consequences

**Positive**

- Content authors (Keith, Jade, future table members per the homebrew goal) can
  override at the tier that matches their intent — a world override file, a
  culture specialization — without touching engine code or restating the whole
  object. The merge engine composes the layers.
- Per-field strategy keeps the common cases (scalar override, list accretion,
  nested-struct refinement) declarative and local to the model, not buried in
  imperative merge code.
- Provenance makes layered content *debuggable*: when a resolved value looks
  wrong, the merge trail names the exact tier and file to fix, surfaced in the GM
  panel rather than reconstructed by hand.
- The runtime base class survived the Rust→Python port with identical semantics,
  so existing content files resolve the same way they did under the proc-macro.

**Negative / risks**

- **The `culture_final` trap (load-bearing risk).** Because `culture_final`
  enforces nothing at runtime, a field intended to be Culture-final can be quietly
  set by a shallower tier with no error, and a future engineer reading the
  strategy name may *assume* a guard that does not exist. This is the single most
  likely source of a "the merge isn't doing what the field name says" bug. The
  mitigation is this ADR and the explicit docstring (`resolver.py`);
  promoting it to real enforcement is a separate decision that would diverge from
  Rust parity.
- **Undeclared-field fallback.** The `replace` default in `merge` means a field
  that *forgets* its strategy declaration still merges (as `replace`) rather than
  erroring at merge time. Correctness depends on the per-subclass wiring test
  catching the omission; if a subclass ships without that test, the gap is silent.
- **`Resolved`/`Provenance` ride the wire.** Because provenance is a protocol type
  on `GameMessage` payloads, changes to `Provenance`/`MergeStep` shape are
  client-visible contract changes, not purely internal refactors.
- **Provenance fidelity is partial** (see Observability caveat): `span` is
  unpopulated and `ContributionKind` is tier-level, so the panel cannot yet show
  per-field, line-level origin.

## Alternatives considered

- **Python code generation (closest to the Rust proc-macro).** A build step that
  emits a `merge` method per model from field annotations. Rejected: Python has no
  natural compile phase to host it, so it would add a generated-vs-source artifact
  and skew risk, plus a codegen toolchain to maintain — all to reproduce behavior a
  ~25-line runtime walk already provides. The runtime base class keeps the contract
  co-located with the `Field` declaration.
- **Hand-written `merge` per model.** Rejected: N near-identical imperative merge
  methods is exactly the boilerplate the Rust macro existed to eliminate; it would
  drift field-by-field and defeat the uniform per-field-strategy contract.
- **A generic dict deep-merge with no per-field strategy.** Rejected: it cannot
  express the real distinctions content needs (a list that *accretes* across tiers
  vs. a scalar that *replaces*), and it loses type validation — the strategies map
  directly onto authorial intent that a blind deep-merge would flatten.
- **Enforcing `culture_final` at runtime.** Considered and *not* adopted for v1, to
  preserve exact parity with the Rust proc-macro (which did not enforce it). Named
  here as future work, not a defect.

## Reconciliation with ADR-003 / ADR-060 / ADR-082

- **ADR-003 (Genre Pack Architecture)** — defines the pack/world *filesystem
  layout* and the `loader.py` flat-file load path. It does **not** govern this
  merge engine. The resolver consumes the directory structure ADR-003 defines
  (`{genre}/`, `worlds/{world}/`, `cultures/{culture}/`) but adds the orthogonal
  concern of *how structured objects combine across those directories with
  recorded provenance*. ADR-003's "genre vs world (the second axis)" is the
  doctrine; this ADR is the merge mechanism that realizes it and extends it down
  to a fourth (Culture) tier.
- **ADR-060 (Genre Models Decomposition)** — split the monolithic genre models
  file into domain submodules under `genre/models/`. It governs *where model
  definitions live*, not *how their instances merge*. The `LayeredMerge` subclasses
  are among the models ADR-060 organizes, but ADR-060 says nothing about the merge
  walk, the strategy taxonomy, or provenance. The two are complementary: ADR-060
  is layout, ADR-121 is resolution behavior.
- **ADR-082 (Port `sidequest-api` from Rust back to Python)** — the origin event.
  This system is the direct port of the Rust `#[derive(Layered)]` proc-macro +
  `Resolver<T>` (`resolver/merge.rs`, `resolver/load.rs`, `resolver/resolved.rs`,
  cited in `resolver.py`). The proc-macro's compile-time behavior was
  re-expressed as the runtime `LayeredMerge` base class; the merge *semantics*
  (tier order, four strategies, provenance trail) were preserved verbatim — most
  consequentially the documentation-only `culture_final`, kept for exact parity.
  The Rust origin is preserved read-only at
  `github.com/slabgorb/sidequest-api` per ADR-082.
