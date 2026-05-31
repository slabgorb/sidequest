---
parent: context-epic-71.md
workflow: trivial
---

# Story 71-27: Router emits combat dispatch with no registered handler — register or stop emitting

## Business Context

The Intent Router's confidence-gated dispatch spine (ADR-113) engages a mechanical
engine for each `SubsystemDispatch` whose `subsystem` key matches a registered
handler. The registry (`run_dispatch_bank`, `sidequest/agents/subsystems/__init__.py`)
registers exactly seven subsystems: `confrontation`, `magic_working`,
`scenario_clue`, `reflect_absence`, `distinctive_detail_hint`, `npc_agency`,
`movement`. The 2026-05-27 `coyote_star` playtest observed the router (Haiku)
emitting a dispatch with `subsystem="combat"` — a key that has **no registered
handler**. When the bank hits it, `_REGISTRY.get("combat")` returns `None` and the
dispatch is logged `unknown_subsystem` and skipped (line ~295-304). The dispatch
fires, the GM panel shows a span, but **no engine ever engages** — a dead dispatch.

This is exactly the failure ADR-113 exists to prevent and a "No Silent Fallbacks"
violation: a player attempts combat, the router recognizes the intent, and the
mechanical engagement silently no-ops while the narrator is free to wing convincing
combat prose with zero mechanical backing (the SOUL Illusionism failure mode). The
fix is a clean either/or decision: **register a `combat` handler** (almost certainly
an alias/normalization to the existing `confrontation` engager, since the router's
own prompt classifies physical contests as a *combat-category* `confrontation` type)
**or stop the router from ever emitting `combat`** and assert it. Either way the dead
dispatch must be eliminated, not left as a silent skip.

## Technical Guardrails

**The dead-dispatch site:**
- `sidequest/agents/subsystems/__init__.py` — `run_dispatch_bank` (line ~214).
  Registry `_REGISTRY` is populated in `_register_defaults()` (line ~162) with the
  seven keys above (`combat` is NOT among them). At line ~295,
  `fn = _REGISTRY.get(d.subsystem)`; when `None`, it logs
  `"subsystems.unknown subsystem=%s ..."`, sets `sub_span.set_attribute("error",
  "unknown_subsystem")`, and `continue`s — the silent skip this story closes.

**Why `combat` is leaking from the router:**
- `sidequest/agents/intent_router.py` — the `_SYSTEM_PROMPT` (line ~103) instructs
  Haiku to use `confrontation` for "structured encounter (combat, negotiation,
  chase, etc.)" and to set `params={"type": "<one of
  game_state.confrontation_types[].type>"}`, choosing "a combat-category type" for a
  physical contest (lines ~120-126). The word "combat" appears as a *category
  descriptor*, and Haiku is over-eagerly emitting it as the `subsystem` key itself.
  So the two real options map cleanly:
  - **Register/alias:** add `combat` → `run_confrontation_dispatch` (the existing
    engager `confrontation` already uses, from
    `sidequest/agents/subsystems/confrontation.py`), OR normalize `combat` →
    `confrontation` before lookup. This keeps the player's combat intent engaging a
    real encounter.
  - **Stop emitting:** tighten the router prompt so `combat` is never a `subsystem`
    value (only a `confrontation` type), and add a test asserting the bank never
    sees `subsystem="combat"`.
- `SubsystemDispatch.subsystem` is a free `str` (`sidequest/protocol/dispatch.py`
  line ~89: "must be registered at runtime") — there is no enum constraining it, so
  an LLM-emitted typo/synonym reaches the bank unguarded. That is the structural
  reason this leak is possible.

**The "register" path entrypoint:** `run_confrontation_dispatch` in
`sidequest/agents/subsystems/confrontation.py` is the live engager that replaced the
retired `begin_confrontation` sidecar tool. If aliasing, route `combat` to it.

**OTEL:** if a handler is registered, the existing `intent_router.subsystem` span
already records `decision`/`error`/`produced_directives` — confirm `combat` engaging
emits the same engagement span (not `error="unknown_subsystem"`). If emission is
stopped, the assertion test stands in for the OTEL proof.

**Existing test to mirror:** `tests/agents/test_subsystem_registry.py:77`
(`test_run_dispatch_bank_unknown_subsystem_is_skipped`) is the canonical
unknown-subsystem behavior test — model the new test on it.

**Do NOT touch:** the confidence-gate logic, the other six handlers, the precondition
gate, or the bank's per-handler error catching.

## Scope Boundaries

**In scope:**
- Decide and implement ONE resolution: register a `combat` handler (alias to the
  confrontation engager) OR stop the router emitting `combat`.
- If registering: the handler fires and emits an engagement OTEL span.
- If removing: the router no longer emits `combat`, asserted by test.

**Out of scope:**
- Converting `SubsystemDispatch.subsystem` to a constrained enum/`Literal` (a
  broader protocol-hardening change — note as a Delivery Finding if the team wants
  it, but do not do it here).
- Any new combat mechanics or changes to the confrontation engine itself.
- The other unregistered-key possibilities — this story is scoped to `combat`.

## AC Context

**Either branch must eliminate the silent no-op.**

**If "register":**
- Test: build a `DispatchPackage` with a `SubsystemDispatch(subsystem="combat", ...)`
  at confidence ≥ threshold and run `run_dispatch_bank`; assert the confrontation
  engager is invoked (an encounter is engaged / a directive produced) AND the
  `intent_router.subsystem` span does NOT carry `error="unknown_subsystem"`.
- Edge case: `combat` below the confidence threshold still degrades to a narrator
  hint (gate runs before registry lookup) — assert it does not error.

**If "stop emitting":**
- Test: assert the router prompt/contract no longer permits `combat` as a
  `subsystem` value (behavioral: drive the router over representative actions and
  assert no emitted dispatch has `subsystem == "combat"`; OR assert a normalization
  step rewrites `combat`→`confrontation` before the bank). A pure source-text grep
  is NOT acceptable (CLAUDE.md "No Source-Text Wiring Tests").

**Regression guard (both branches):** a test asserts that a `combat` key no longer
reaches the bank as an `unknown_subsystem` silent skip — i.e. the dead-dispatch path
is gone.

## Assumptions

- The intended semantics of a `combat` dispatch are "engage a combat-category
  structured encounter" — i.e. it is a synonym for `confrontation` with a
  combat-category `type`, not a distinct subsystem. (Strongly supported by the
  router prompt's own language.) If the team intends `combat` to be a genuinely
  distinct engine, that is out of scope and must be re-scoped — flag to SM.
- The reuse-first answer (alias `combat`→`confrontation`) is preferred over inventing
  a new engine, per Architect restraint and CLAUDE.md "Don't Reinvent."
- `run_confrontation_dispatch` accepts the same dispatch shape `combat` would carry
  (params `{"type": ...}`); if the params differ (e.g. `combat` carries no `type`),
  normalization must supply a sensible default-fail-loud, not silently invent a type.

If the params shapes are incompatible, log a Design Deviation and notify SM rather
than fabricating a confrontation `type`.
