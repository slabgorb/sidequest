---
id: 121
title: "Layered Content Resolution — Per-Field Merge Strategies and Provenance; the Two-Tier Archetype Shim Is the Production Path"
status: accepted
date: 2026-05-31
deciders: ["Keith Avery", "Neo (Architect)"]
supersedes: []
superseded-by: null
related: [3, 60, 82]
tags: [core-architecture]
implementation-status: live
implementation-pointer: "LayeredMerge/MergeStrategy (genre/resolver.py) + provenance wire types (protocol/provenance.py) + two-tier shim (genre/archetype/shim.py via chargen_mixin); four-tier Resolver walk removed by story 82-4"
---

# ADR-121: Layered Content Resolution

> **Documents a system already live in code.** The `LayeredMerge` base class,
> the `MergeStrategy` taxonomy, and the `Provenance` / `MergeStep` wire types
> shipped during the Rust→Python port (ADR-082) without a governing ADR — they
> are the Python port of the Rust `#[derive(Layered)]` proc-macro system. This
> record closes that architecture-of-record gap and states what the decision
> *was*.
>
> **Amended 2026-06-05 (Story 82-4): narrowed to production reality.** The
> original record also described a four-tier `Resolver[T]` / `Resolved[T]`
> walk (Global → Genre → World → Culture via `resolve_merged`) as live. The
> 2026-06-03 ADR-vs-code audit found that walk had **no production consumer**:
> it was never instantiated outside its own module, no genre pack ships its
> per-tier file layout (no `{axis}.yaml` at any tier; culture directories hold
> flat `{culture}.yaml` corpus files, ADR-091), and the actual production
> resolution path — the two-tier archetype shim — merges *different schemas
> per tier* by pair-constrained lookup, which the same-type `LayeredMerge`
> walk cannot express. Story 82-4 **removed** the dead walk (`Resolver`,
> `ResolutionContext`, `Resolved`, `_load_tier`) per *No Stubbing* ("dead code
> is worse than no code") and narrowed this ADR to what is genuinely live:
> the per-field merge machinery, the provenance wire types, and the two-tier
> shim as the production resolution path. Sections below are rewritten to the
> narrowed scope; the original four-tier design survives in git history and in
> the Rust reference repo.

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

**Layered content resolution is two live pieces plus one production path:**

1. **Per-field merge machinery** — a runtime pydantic base class
   (`LayeredMerge`, `genre/resolver.py`) whose subclasses declare per-field
   merge strategies via `Field(json_schema_extra={"merge": ...})`, dispatched
   through the `MergeStrategy` taxonomy. This is how a deeper tier's instance
   of a model merges into a shallower tier's.
2. **Provenance wire types** — `Provenance` / `MergeStep` / `Tier` /
   `ContributionKind` (`protocol/provenance.py`) live in the protocol package
   so they ride on `GameMessage` payloads to the GM panel.
3. **The two-tier archetype shim is the production resolution path** —
   `resolve_archetype` (`genre/archetype/shim.py`), called from chargen
   (`server/websocket_handlers/chargen_mixin.py`,
   `_resolve_character_archetype`). It resolves a `(jungian, rpg_role)` pair
   through **world funnel → genre fallback**, consuming *different schemas per
   tier* (`archetypes_base.yaml` axes at the global tier,
   `archetype_constraints.yaml` pairing weights at the genre tier,
   `archetype_funnels.yaml` at the world tier) and emitting tier-annotated
   `Provenance` on every resolution.

### What was deliberately removed (82-4)

The Rust port also carried a generic four-tier file walk —
`Resolver[T].resolve_merged` over `{root}/{field_path}.yaml`,
`{root}/{genre}/{field_path}.yaml`, `worlds/{world}/{field_path}.yaml`,
`cultures/{culture}/{field_path}.yaml` — plus its `ResolutionContext` /
`Resolved[T]` carrier types. It was removed rather than wired because:

- **No consumer:** never instantiated in production or tests.
- **No content:** no genre pack ships any `{axis}.yaml` tier file the walk
  could load; culture directories contain flat `{culture}.yaml` corpus files
  (ADR-091 naming), not per-axis subdirectories.
- **Wrong shape for the real problem:** production archetype resolution is
  pair-constrained *lookup* across heterogeneous per-tier schemas — not a
  same-type document merge. `LayeredMerge` cannot express it; the shim does.

If a future axis genuinely needs a same-schema multi-tier document merge, the
building blocks remain (`LayeredMerge` + provenance types) and the removed walk
is recoverable from git history / the Rust reference — but reintroducing it is
a **new decision** that must arrive together with the content layout that
feeds it and a production consumer (the wiring doctrine that retired it).

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

- **Tier precedence is fixed.** In the production shim, World beats Genre — a
  world-funnel match wins; the genre fallback fires only when no funnel
  absorbs the pair. In `LayeredMerge.merge`, the deeper tier always merges
  *into* the shallower one. No per-pack override of precedence exists.

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

- **Provenance is mandatory output.** Every `ArchetypeResolution` carries a
  `Provenance` with a non-optional ordered `merge_trail: list[MergeStep]`
  (`provenance.py`); `source_tier`/`source_file` record the tier that supplied
  the final value (`world` for a funnel hit, `genre` for a fallback —
  `shim.py`). Resolution that produces a value also always produces the audit
  trail of how, and `apply_archetype_resolved` copies it onto the character as
  `archetype_provenance` in lockstep with the resolved name.

## Observability

Provenance *is* the GM-panel surface for this subsystem, satisfying the project's
OTEL/lie-detector principle: the panel must be able to verify the engine engaged
rather than the narrator improvising content origins.

- `Provenance` and `MergeStep` (`provenance.py`) are `ProtocolBase` types,
  living in `sidequest/protocol/` precisely so they **travel on the wire as part
  of `GameMessage` payloads**. The character's `archetype_provenance` carries
  the full record; the GM panel can therefore show, for any resolved archetype,
  which tier produced it and the contribution trail.
- `MergeStep` records `tier`, `file`, an optional source `span`
  (line/column range, `Span`, `provenance.py`), and a `ContributionKind`
  (`initial` / `replaced` / `appended` / `merged`, `provenance.py`). The
  trail is the human-auditable answer to "where did this archetype's `name`
  come from."
- The shim constructs the `MergeStep` at the contributing tier (`shim.py` —
  world funnel or genre fallback, each `ContributionKind.initial`), and the
  production caller emits the **OTEL span events** that make engagement
  verifiable: `character_creation.archetype_resolved` (with `source`,
  `source_tier`, `weight`, `faction` attributes) and
  `character_creation.archetype_resolution_failed`
  (`chargen_mixin._resolve_character_archetype`).

**Honesty caveat (current state):** `span` is always emitted as `None` — the
line/column range is wired through the *type* and the wire payload but not yet
populated from the YAML parse. The shim's trail is single-step (`initial` at
the deciding tier); the finer `replaced` / `appended` kinds exist in the enum
for `LayeredMerge`-based merging but the production path has no multi-step
trail to apply them to. These are panel-fidelity gaps, not correctness gaps —
the trail is accurate about which tier and file decided the value.

## Consequences

**Positive**

- Content authors (Keith, Jade, future table members per the homebrew goal) can
  override at the tier that matches their intent — a world funnel file refines
  the genre's archetype table — without touching engine code or restating the
  whole object. The shim composes the layers and names its sources.
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
- **`Provenance` rides the wire.** Because provenance is a protocol type
  on `GameMessage` payloads (`archetype_provenance`), changes to
  `Provenance`/`MergeStep` shape are client-visible contract changes, not
  purely internal refactors.
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
  resolution behavior. The shim consumes models the loader reads from the
  directory structure ADR-003 defines (`{genre}/`, `worlds/{world}/`) but adds
  the orthogonal concern of *how the final value is chosen across those tiers
  with recorded provenance*. ADR-003's "genre vs world (the second axis)" is
  the doctrine; this ADR is the resolution mechanism that realizes it.
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
  (strategy taxonomy, provenance trail) were preserved verbatim — most
  consequentially the documentation-only `culture_final`, kept for exact parity.
  The ported `Resolver<T>` walk itself was carried across but never gained a
  Python-side consumer and was removed by Story 82-4 (see the amendment note).
  The Rust origin is preserved read-only at
  `github.com/slabgorb/sidequest-api` per ADR-082.
