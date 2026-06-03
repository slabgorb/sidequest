---
parent: context-epic-81.md
workflow: tdd
---

# Story 81-1: Register magic plugins in production so MAGIC_PLUGINS is non-empty at runtime (ADR-126)

## Business Context

ADR-126's whole point is a validator firewall for magic descriptors: a misconfigured or
homebrew magic working should be caught and flagged, not silently accepted. Right now that
firewall is dead in production. Because the plugin registry is empty at runtime, every
plugin-declared magic effect skips plugin-side validation and falls into the
`plugin_known_but_not_registered` DEEP_RED branch — the validator reports a configuration
failure for *correctly configured* content, and no plugin validation logic ever runs. For
an authoring-first audience (Jade extending packs, Keith authoring), a magic validator that
can't actually validate is worse than none: it gives a false signal. Fixing the registration
restores the safety net the ADR promised.

## Technical Guardrails

**Key files (navigate by symbol; 2026-06-03 line anchors may drift):**
- `sidequest/magic/__init__.py` (~:24) — currently imports `MAGIC_PLUGINS` from `plugin`, the empty registry. This is the most likely home for the fix import.
- `sidequest/magic/plugin.py:37` — `MAGIC_PLUGINS: dict[str, MagicPlugin] = {}` (the registry being mutated).
- `sidequest/magic/plugins/__init__.py:8-10` — star-imports `innate_v1`, `item_legacy_v1`, `learned_v1`; importing THIS package is what fires registration.
- `sidequest/magic/validator.py:107-123` — the `plugin_known_but_not_registered` DEEP_RED branch that currently always triggers.
- `sidequest/server/narration_apply.py:813` — `magic_validate(...)` production call site.
- `tests/magic/test_wiring.py`, `tests/magic/conftest.py:24` — the existing (insufficient) wiring coverage.

**Patterns to follow:**
- Mirror `sidequest/telemetry/spans/__init__.py` — the star-import-of-domain-modules pattern that `plugins/__init__.py`'s docstring explicitly cites as its model. Registration via import side-effect is the intended mechanism; make it fire in prod, don't replace it.
- Fail-loud (CLAUDE.md): do not add a try/except that swallows an import error and leaves the registry empty.

**Integration points / what NOT to touch:**
- Do not change the plugin modules themselves or the registry shape — they work.
- Watch for import cycles: `sidequest.magic.plugins` submodules import from `sidequest.magic.plugin`/`models`; importing the plugins package from `magic/__init__.py` must not create a cycle. If it does, move the import to the next-narrowest production entrypoint (e.g. the validator module or app startup) rather than deferring it.

## Scope Boundaries

**In scope:**
- Make `MAGIC_PLUGINS` populate via a production import path.
- A wiring test that fails on current code and passes after the fix.

**Out of scope:**
- Any change to plugin validation logic, descriptor schemas, or the validator severity model.
- New plugins. (ADR-117/126 module additions are tracked elsewhere.)

## AC Context

1. **Production import populates the registry.** A test imports `import sidequest.magic`
   (NOT `sidequest.magic.plugins`) and asserts `MAGIC_PLUGINS` contains `innate_v1`,
   `item_legacy_v1`, `learned_v1`. Edge case: assert via the production entrypoint only —
   if the test imports the plugins package it proves nothing (that is the current bug).
2. **DEEP_RED branch no longer mis-fires.** With the registry populated, a test calls
   `magic_validate()` (or the validator directly) for a descriptor-registered plugin id and
   asserts the result does NOT carry `plugin_known_but_not_registered`; plugin-side
   validation actually executes. Edge case: a genuinely unknown plugin id should STILL hit
   the not-registered branch — don't weaken that check.
3. **No import cycle / clean boot.** Importing the server app (the path that reaches
   `narration_apply`) succeeds; `just server` starts without ImportError. Verify by importing
   the app module in a test or a smoke check.
4. **Wiring test is real.** The new test demonstrably fails against current `develop`
   (empty registry through the production path) and passes after the fix. Full
   `just server-test` green; `just server-lint` clean.

## Assumptions

- `sidequest/magic/__init__.py` is import-reachable from the production validation path
  (it is — `narration_apply` imports the validator which lives under `sidequest.magic`).
- Importing the `plugins` package from `magic/__init__.py` does not introduce a cycle. If
  this proves false, log a Design Deviation and relocate the import to the validator module
  or app startup — same outcome (prod path populates the registry), different anchor.
- Resume/load paths do not need separate registration (registration is import-time and
  process-global, not per-session).
