---
parent: context-epic-59.md
workflow: trivial
---

# Story 59-25: Multi-key entity extraction in leak_audit

## ⚠️ Staleness Check

**The gap is LIVE as of 2026-05-29** — verified against `origin/develop` after
the 59-24 merge while authoring this context. This is the third in a chain:
**59-9** closed the primary firewall hole (`redact_dispatch_package`), **59-24**
closed the secondary lie-detector hole for `cross_player`, and **59-25** closes
the *deeper* hole both leak-audit branches share — the entity-extraction key
assumption.

Evidence (`sidequest/telemetry/leak_audit.py`, `audit_canonical_prose`, on
`develop` post-59-24):

- Both collection loops extract the redacted entity from **`params["target"]`
  only**:
  - per_player loop, line 82: `target = d.params.get("target") if isinstance(d.params, dict) else None`
  - cross_player loop, line 96: identical (added by 59-24).
- But subsystems key their entity identity under **different** param names
  (confirmed in source):
  - `distinctive_detail_hint` → `params["target"]` (`subsystems/distinctive_detail.py:26`) ✅ covered
  - `npc_agency` → `params["npc_name"]` (`subsystems/npc_agency.py:64`; router contract `intent_router.py:140`) ❌ **missed**
  - `magic_working` → `params["actor"]` (`MagicWorking`-shaped params; `subsystems/magic_working.py:7,58`) ❌ **missed**
- Net effect: a `SubsystemDispatch` from `npc_agency` or `magic_working` tagged
  `redact_from_narrator_canonical=True` has its entity name read from the wrong
  key, so it **never enters `redacted_entities`** at all. Because
  `redact_tag_count = len(redacted_entities)` (`leak_audit.py:116`), the dispatch
  is invisible to the audit on both axes: it is not counted, and the prose scan
  never looks for its name. If that name then appears in canonical narrator
  prose, `audit_canonical_prose` returns `leaks_detected=0` — a **silent false
  negative** in the GM-panel lie-detector. (Note: this refines the 59-24 finding,
  which said the dispatch "increments redact_tag_count but drops the name" — in
  fact it does neither, since the count is derived from the same list.)
- This was surfaced by the 59-24 security review (medium confidence). It is a
  **pre-existing** gap in the per_player branch that 59-24 faithfully mirrored
  into cross_player per its scope; 59-25 fixes **both branches together**.

## Business Context

`audit_canonical_prose` is the OTEL lie-detector for the structural-hiding
firewall (ADR-104/105, SOUL "Illusionism"; CLAUDE.md OTEL principle: *the GM
panel is the lie detector*). A leak audit that silently fails to scan an entire
class of redacted entities gives a **false sense of safety** — the exact failure
the OTEL discipline exists to prevent.

**Priority p3 (lower than 59-9/59-24) — maturity caveat:** the gap only bites
when the **Group G perception rewriter** (ADR-104/105, *partial*) actually emits
`npc_agency`/`magic_working` dispatches tagged `redact_from_narrator_canonical=True`.
Current production redaction is largely `distinctive_detail_hint`, where
`"target"` is the correct key. The redaction tests
(`tests/.../test_localdm_wiring.py`) do exercise a redacted `npc_agency`
dispatch, so the scenario is real, but live exposure is gated on that layer
maturing. This is hardening ahead of that layer, not a current live leak.

## Technical Guardrails

**File to modify:**
- `sidequest/telemetry/leak_audit.py` — `audit_canonical_prose`. Replace the
  single-key `target` extraction in **BOTH** loops (per_player ~line 82 and
  cross_player ~line 96) with a multi-key lookup.

**Test file to extend:**
- `tests/telemetry/test_leak_audit.py` — add cases for `npc_agency`
  (`params["npc_name"]`) and/or `magic_working` (`params["actor"]`), covering
  both per_player and cross_player.

**Suggested extraction (apply identically to both loops):**
```python
target = None
if isinstance(d.params, dict):
    for k in ("target", "npc_name", "actor"):
        v = d.params.get(k)
        if isinstance(v, str):
            target = v
            break
if target is not None:
    redacted_entities.append(target)
```
Keep both branches symmetric — do not fix per_player and leave cross_player
behind (or vice versa); the whole point is that 59-24 made them mirrors, so they
must stay mirrors. Consider extracting a tiny local helper to enforce the
symmetry mechanically, but a duplicated literal key-tuple is acceptable for a
1-pointer if a helper feels heavier than the win (Dev's call; do not
over-engineer).

**OTEL — reuse, don't add:** multi-key targets flow into the same
`redacted_entities` list, counted by the existing
`narrator.canonical_leak_audit` span. **No new span.**

**No silent fallback nuance:** the current silent-drop on a missing `target`
is what *causes* this gap. Widening the key set narrows the silent-drop surface
to genuinely keyless dispatches. Do NOT add a hard failure for a dispatch with
none of the known keys — that would be over-reach for this story; the multi-key
widening is the fix. (If a future audit wants to *flag* keyless redacted
dispatches, that is a separate concern.)

## Scope Boundaries

**In scope:**
- Widen entity extraction in `audit_canonical_prose` to cover `target`,
  `npc_name`, and `actor`, in BOTH the per_player and cross_player loops.
- Tests pinning npc_agency / magic_working leak detection (FAIL against current
  main), across both branches.

**Out of scope:**
- `redact_dispatch_package` (`prompt_redaction.py`) — that redactor strips by
  the binary `redact_from_narrator_canonical` flag at the dispatch level and
  does not need per-key entity extraction; 59-9 already handled it. Do not
  touch it.
- The orchestrator call sites — unchanged (they correctly pass the canonical
  pre-redaction package).
- Adding a new OTEL span.
- Any fidelity / `secrets_for` / `visible_to` handling (ADR-105 broadcast
  concern).
- Hard-failing on keyless redacted dispatches (separate future concern).

## AC Context

The trivial-fix bar is one+ test that FAILS against current `main` and pins the
new multi-key behavior across both branches.

**AC1 — npc_agency redacted entity is leak-detected (per_player):** Build a
package with a `per_player` `npc_agency` `SubsystemDispatch`,
`redact_from_narrator_canonical=True`, `params={"npc_name": "<entity_id>"}`,
prose containing that entity's token. Assert `leaks_detected >= 1` and the
entity in `leaked_entities`. RED today (npc_name not extracted → 0).

**AC2 — Same coverage in the cross_player branch:** Mirror AC1 with the dispatch
inside a `cross_player` `CrossAction`. Assert leak detected. RED today.

**AC3 — magic_working `actor` key covered (either branch):** A redacted
`magic_working` dispatch with `params["actor"]="<entity_id>"` whose token leaks
into prose is detected. (Optionally also assert `redact_tag_count` reflects the
newly-collected entity.)

**AC4 — No regression / no false positive:** the existing `target`-keyed cases
still pass, and a clean-prose multi-key case yields `leaks_detected=0`.

## Assumptions

- The documented entity-identifier keys are `target` (distinctive_detail_hint),
  `npc_name` (npc_agency), `actor` (magic_working) — confirmed in source on
  2026-05-29. If a new subsystem introduces another entity key, this list will
  need extending (note it in code as the canonical key set).
- The fix stays inside `audit_canonical_prose`; no protocol/schema change.
- Reference: 59-24 (`sprint/archive/59-24-session.md`) for the cross_player
  mirror this builds on, and its security finding that motivated this story.
