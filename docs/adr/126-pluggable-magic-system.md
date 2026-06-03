---
id: 126
title: "Pluggable Magic System — MagicPlugin Protocol, Import-Time Registry, and Validator Severity Model"
status: accepted
date: 2026-05-31
deciders: ["Keith Avery", "Neo (Architect)"]
supersedes: []
superseded-by: null
related: [97, 113, 117]
tags: [game-systems]
implementation-status: live
implementation-pointer: null
---

# ADR-126: Pluggable Magic System

> **Documents a system already live in code.** The `MagicPlugin` Protocol, the
> module-level `MAGIC_PLUGINS` registry, the three shipped plugins (`innate_v1`,
> `learned_v1`, `item_legacy_v1`), and the yellow/red/deep_red validator
> severity model all shipped in the magic subsystem (`sidequest/magic/`) without
> a governing ADR. This record closes that architecture-of-record gap and states
> what the decision *was* — exactly as ADR-117 did for the `RulesetModule` seam.

## Context

SideQuest's doctrine is **Crunch in the Genre, Flavor in the World**: a genre is
the rulebook, a world is the campaign setting, and one genre hosts many worlds.
Magic is a place where that split is sharp — *how* magic resolves mechanically is
a genre/system concern, but *what magic is, who knows it's real, and what it
costs* is overwhelmingly world flavor. A high-tech space-opera world where
psionics are a classified Hegemony secret and a low-fantasy world where hedge
charms are folklore are mechanically similar but narratively opposite.

The engine therefore needs a way to say "this world has *this kind* of magic, with
*these* sources and costs," validate that the narrator's emitted magic events are
coherent with that world's rules, and do so without a hardcoded `if source ==
"innate" … elif source == "item" …` ladder buried in the turn loop. Different
*kinds* of magic (born-with-it gifts vs. prepared spells vs. cursed heirlooms)
have genuinely different validation contracts — an innate gift has a `flavor` and
a `consent_state`; a learned spell has a `spell_id` and a `slot_level`; an item
working has an `item_id` and an `alignment_with_item_nature`. These are not the
same shape of thing, and forcing them through one monolithic validator would be
the kind of stringly-typed contortion the project's quality rules reject.

The magic subsystem was built to handle this, and it has been live and emitting
through `game_patch.magic_working` (the narrator's per-turn magic event, see
`sidequest/magic/models.py` `MagicWorking`). It just never got its own ADR.
This record states the decision.

## Decision

**Each *kind* of magic is a pluggable module implementing a `MagicPlugin`
Protocol. Plugins register themselves into a module-level `MAGIC_PLUGINS` registry
by side effect at import time. A two-layer validator — framework-side checks plus
per-plugin `validate_working` — grades each magic working against the world's
magic config and emits a list of `Flag`s under a three-level severity model
(yellow / red / deep_red). Three plugins ship: `innate_v1`, `learned_v1`,
`item_legacy_v1`.**

This is **distinct from the pluggable ruleset (ADR-117).** The `RulesetModule`
seam governs *resolution dice* — attack-vs-AC, saves, skill checks, how a
confrontation beat resolves. The `MagicPlugin` seam governs *spell validation and
narrative cost* — whether a magic working is coherent with the world's declared
magic and whether the narrator stayed in its lane. They are orthogonal seams; the
boundary is drawn explicitly in Reconciliation below.

### The Protocol contract

`sidequest/magic/plugin.py` defines `MagicPlugin` as a `@runtime_checkable`
`typing.Protocol`, not an ABC. A plugin class is anything that structurally
satisfies it:

- `plugin_id: str` — the registry key (`plugin.py`).
- `required_attrs() -> set[str]` — the plugin-specific `MagicWorking` fields that
  MUST be populated for this kind of magic (`plugin.py`). All three shipped
  plugins return `set(descriptor.required_span_attrs)`, sourcing the answer from
  the plugin's YAML descriptor (e.g. `innate_v1.py`).
- `validate_working(working, config) -> list[Flag]` — plugin-side validation
  producing yellow/red/deep_red flags; an empty list means clean (`plugin.py`).

Protocol (structural typing) was chosen over an ABC because plugins are paired
files — a `.py` module of mechanics and a `.yaml` file of content — and the
runtime instance only needs to satisfy the three-member shape. Nothing inherits.

### The import-time registry (same shape as OTEL span-route registration)

`MAGIC_PLUGINS: dict[str, MagicPlugin]` (`plugin.py`) is a bare module-level
dict. Each plugin module mutates it in place at import time as a side effect — the
last line of every plugin file is `MAGIC_PLUGINS["<id>"] = <Plugin>()`
(`innate_v1.py`, `item_legacy_v1.py`, `learned_v1.py`). The package
`__init__.py` star-imports each plugin submodule so the side-effect mutation fires
for every shipped plugin; importing the package *is* registration.

This deliberately mirrors the codebase's house pattern in
`sidequest/telemetry/spans/_core.py`, where `SPAN_ROUTES` is mutated by domain
submodules at import — the module docstring at `plugin.py` calls this out
explicitly, and the plugin-package `__init__.py` docstring names
`sidequest/telemetry/spans/__init__.py` as its model. Renames break at import
time (loud), and `tests/magic/test_plugin_registry.py` enforces registry
completeness in the same shape `tests/telemetry/test_routing_completeness.py` does
for spans (`plugin.py`).

A `get_plugin(plugin_id)` lookup helper (`plugin.py`) raises a `KeyError` that
lists *what is* registered — fail-loud per No Silent Fallbacks, not a `None`
return.

### The plugin taxonomy

Three plugins ship, each owning a distinct *source* of magic and a distinct
required-attr contract:

- **`innate_v1`** (`innate_v1.py`) — character-as-source magic (source `innate`).
  Required attrs: `flavor` and `consent_state`. The plugin checks a
  `flavor → consent_state` coherence table (`innate_v1.py`, e.g. `acquired` and
  `born_to_it` expect `involuntary`) and enforces plugin-lane respect: an innate
  working with `mechanism == "faction"` is a RED lane violation because a
  faction-mediated working belongs to `bargained_for_v1`/`learned_v1`
  (`innate_v1.py`).
- **`learned_v1`** (`learned_v1.py`) — prepared-spell magic for caster classes
  (source `learned`; loose-Vancian known/prepared lists, daily slots). Required
  attrs: `spell_id` and `slot_level` (`slot_level < 1` is RED, `learned_v1.py`).
  Lane respect rejects item mechanisms (`discovery`, `mccoy`, `relational`,
  `faction`) and innate mechanisms (`native`, `condition`) as RED
  (`learned_v1.py`, `:77-98`); learned magic must use `studied` or
  `granted`.
- **`item_legacy_v1`** (`item_legacy_v1.py`) — items as agents
  (McCoy/discovery/relational delivery; source `item_based`). Required attrs:
  `item_id` and `alignment_with_item_nature` (out of `[-1.0, 1.0]` is RED,
  `item_legacy_v1.py`). Lane respect: a `native`-mechanism working is a RED
  violation because native delivery is innate territory — items must be
  carried/found/built (`item_legacy_v1.py`).

The plugin source map also names forward-looking entries (`learned_v1`,
`divine_v1`, `bargained_for_v1`) in the validator's `_PLUGIN_SOURCE`
(`validator.py`) so a world config referencing an unbuilt plugin is rejected
with a clean DEEP_RED rather than crashing — see Invariants.

### The flag-severity model

`FlagSeverity` (`models.py`) is a three-level `StrEnum`: `yellow`, `red`,
`deep_red`. A `Flag` (`models.py`) carries `severity`, a machine-readable
`reason`, and a human `detail`. The top-level `validate(working, config)`
(`validator.py`) composes two layers and returns the accumulated `list[Flag]`
(empty = clean):

1. **Framework-side checks** (`validator.py`):
   - plugin ∈ `config.active_plugins` — else DEEP_RED `plugin_not_in_active_plugins`
     and **early return** (don't run plugin-side validation for an inactive plugin);
   - plugin's source ∈ `config.allowed_sources` — unknown plugin id → DEEP_RED
     `unknown_plugin_id` and early return; source not allowed → DEEP_RED;
   - each cost type ∈ `config.cost_types` — else YELLOW `unknown_cost_type`;
   - hard-limit keyword match against `narrator_basis` (a deliberately crude v1
     substring detector, `validator.py`) → DEEP_RED
     `hard_limit_violation:<id>`.
2. **Plugin-side validation** (`validator.py`): resolve the plugin via
   `get_plugin`, defend against a known-but-unregistered forward-looking id
   (DEEP_RED `plugin_known_but_not_registered`), then `flags.extend(plugin.
   validate_working(working, config))`.

Severity is graded, not binary: a missing required attr is YELLOW (the narrator
under-specified), a lane violation or out-of-range value is RED (the narrator
crossed a plugin boundary), and a world-config / hard-limit violation is DEEP_RED
(the world says this magic cannot exist here).

**v1 policy — flags emit, they do not interrupt.** Per the explicit comment at
`validator.py`, even DEEP_RED flags surface in OTEL but do **not** halt
narration in v1. The interruption path (route DEEP_RED through an
`on_deep_red_violation` hook in `narration_apply.py` before delivery) is a named,
deliberate future extension, not an oversight — flag-only emission is the stated
policy. This makes the validator a lie-detector channel for the GM panel
(per the OTEL Observability Principle) without yet being a narration gate.

## Invariants / Contracts

- **Import-time registration is the only registration.** A plugin is registered
  iff its module is imported; the package `__init__.py` star-import is what fires
  every shipped plugin's side effect (`plugins/__init__.py`). There is no
  decorator, no explicit `register()` call, and no runtime discovery. Adding a
  plugin = add the `.py`/`.yaml` pair and add its star-import line. This is the
  same contract as `SPAN_ROUTES` (`plugin.py`).
- **`required_attrs` / `validate_working` are the whole plugin contract.** A
  plugin must expose `plugin_id` and implement both methods to satisfy the
  `@runtime_checkable` Protocol (`plugin.py`). `required_attrs()` declares
  which optional `MagicWorking` fields this kind of magic populates;
  `validate_working()` is the only place plugin-specific coherence and lane-respect
  rules live. Framework concerns (active/allowed/cost/hard-limit) stay in
  `validator.py` and are never duplicated into a plugin.
- **`get_plugin` fails loud.** Lookup of an unregistered id raises a `KeyError`
  enumerating the registered set (`plugin.py`); the validator catches it
  specifically to convert a forward-looking-but-unbuilt plugin into a clean
  DEEP_RED rather than an unhandled crash (`validator.py`).
- **WorldKnowledge awareness ordering: `local_register` ≤ `primary`.**
  `WorldKnowledge` (`models.py`) carries a `primary` awareness tag and an
  optional `local_register` sub-tag, both drawn from the ordered axis
  `denied < folkloric < mythic_lapsed < esoteric < classified < acknowledged`
  (`_AWARENESS_ORDER`, `models.py`). A `model_validator` enforces that
  `local_register` cannot exceed `primary` on that axis (`models.py`): a
  locality cannot be *more* aware that magic is real than the world's primary
  register is. (Coyote Star: the Hegemony `classifies` while frontier folk know it
  `folklorically` — local is *less* aware, which is legal; the inverse is a loud
  `ValueError` at model construction.) All magic models use `extra='forbid'`
  (`models.py` and throughout) per No Silent Fallbacks — an unknown field is a
  validation error, not a silently dropped key.

## Consequences

**Positive**

- New kinds of magic are additive: ship a `.py`/`.yaml` pair, add one star-import
  line, register by side effect. No turn-loop conditionals, no validator surgery.
- Per-plugin validation keeps each kind of magic's contract local and legible;
  the lane-respect checks stop the narrator from quietly attributing item magic to
  an innate gift (or vice versa), which the GM panel can see via the emitted flags.
- The import-time-registry pattern reuses a contract contributors already know from
  `SPAN_ROUTES`; the completeness test mirrors the span routing test.
- Graded severity lets the validator distinguish "narrator under-specified"
  (YELLOW) from "narrator broke a world rule" (DEEP_RED) without a binary
  pass/fail, feeding richer OTEL signal.

**Negative / cost**

- Side-effect-at-import registration is implicit: forgetting the `__init__.py`
  star-import line silently un-registers a plugin (caught by the completeness
  test, but the failure mode is non-obvious). This is the known trade for matching
  the house `SPAN_ROUTES` pattern.
- The validator carries a `_PLUGIN_SOURCE` map (`validator.py`) that mirrors
  data living on the YAML `Plugin` descriptor (`models.py` `source`) because
  the runtime Protocol instance does not expose `source`. That duplication must be
  kept in sync by hand until the descriptor and runtime instance are unified.
- Hard-limit detection is a crude substring match in v1 (`validator.py`),
  with acknowledged false-positive risk for short keywords; smarter detection is
  deferred.
- DEEP_RED does not yet interrupt narration (`validator.py`), so a world
  rule can be violated in prose while only a flag is emitted. Closing that is named
  future work, not done here.

## Alternatives considered

- **Hardcoded magic (a fixed `if source == … elif …` ladder in the turn loop).**
  Rejected: the three kinds of magic have genuinely different required-attr
  contracts and lane rules; a single hardcoded validator would be a stringly-typed
  contortion, and adding a fourth kind (`divine_v1`, `bargained_for_v1`) would mean
  editing the turn loop rather than dropping in a file. Violates Don't-Reinvent and
  the project's quality rules.
- **Folding magic into the `RulesetModule` seam (ADR-117).** Rejected: the two
  seams answer different questions. The ruleset module decides *how dice resolve*
  (one module per *session*, bound per genre, stateless singleton). Magic
  validation decides *whether a magic working is coherent with this world's
  declared magic* and *whether the narrator stayed in its lane* — and a single
  world can have multiple active magic plugins at once (`config.active_plugins` is a
  list, `models.py`), unlike the one-module-per-session ruleset binding. Merging
  them would couple resolution dice to spell validation and force a list-of-plugins
  concept into a one-of-N binding. Keeping them orthogonal keeps each seam's
  invariants clean.
- **ABC instead of Protocol.** Rejected: nothing inherits; plugins are paired
  file pairs whose runtime instance only needs the three-member shape. A
  `@runtime_checkable` Protocol expresses that contract without an inheritance
  hierarchy.
- **Explicit `register()` call / decorator instead of import side effect.**
  Considered; rejected to match the established `SPAN_ROUTES` house pattern
  (`plugin.py`) and keep the registry completeness test shape identical to
  the telemetry one.

## Reconciliation with ADR-097 / ADR-113 / ADR-117

- **ADR-117 (Pluggable Ruleset Module System) — adjacent, governs dice, not
  magic.** ADR-117 owns the `RulesetModule` ABC + fail-loud `get_ruleset_module`
  registry: *resolution behavior* (attack-vs-AC, saves, skill checks, beat apply,
  damage) bound one-per-session per genre. This ADR owns the `MagicPlugin`
  Protocol + import-time `MAGIC_PLUGINS` registry: *spell validation and narrative
  cost*, multiple plugins active per world. Both honor No Silent Fallbacks via
  fail-loud registries, but they are independent seams — a `swn`-bound session and
  an `innate_v1`/`learned_v1` world are configured separately and do not interact
  through either registry. ADR-117 does not govern magic-plugin architecture; it
  explicitly scopes itself to resolution procedure.
- **ADR-097 (Class Mechanical Surface) — names the slot, does not govern the
  architecture.** ADR-097 says, in one line, "Mage → no Class signature; magic
  plugin fills the slot" (`097-class-mechanical-surface.md`, and the framing at
  `:33`/`:38`). That sentence asserts that caster classes get their mechanical
  signature *from* a magic plugin rather than from a Class-signature ability — it
  is a consumer of this seam, not its design of record. It says nothing about the
  Protocol, the registry, the taxonomy, or the severity model. This ADR governs
  those.
- **ADR-113 (Intent Router — Mechanical-Engagement Spine) — uses "magic plugin"
  as a dispatch term-of-art.** ADR-113 routes `magic_working` as one of its
  dispatch subsystems (`apply_magic_working` in `server/narration_apply.py`,
  `resolve_magic_confrontation` in `dispatch/confrontation.py`, see
  `113-*.md:68`, `:183`). It treats the magic subsystem as a black-box engagement
  target the router fires and the engagement watcher checks — it does not define
  how plugins register or how workings are validated. The validator's flag stream
  is the natural OTEL signal ADR-113's lie-detector consumes, but the plugin
  architecture itself is governed here.

None of the three governs the plugin architecture: ADR-117 governs the orthogonal
dice seam, ADR-097 merely consumes the slot, and ADR-113 merely dispatches to the
subsystem. This ADR is the architecture-of-record for the `MagicPlugin` Protocol,
the import-time registry, the plugin taxonomy, and the validator severity model.
