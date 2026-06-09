---
parent: context-epic-98.md
workflow: tdd
---

# Story 98-1: C1 Content — split perseus_cloud orbits.yaml into systems/<id>.yaml, delete fake root, author yula

## Business Context

This is the **root of the critical path** (C1 → S1 → U1). Today
`perseus_cloud/orbits.yaml` models a 34-system star cluster as a *single solar
system* — a fabricated `perseus_cloud` primary with every real system hung off it
as a child planet. The orrery renderer faithfully draws that knot: 34
stars-as-planets on one disc, unreadable. Until the content is restructured, no
amount of server or UI work can make the campaign map legible — the malformed
data is the disease (ADR-141 §Context).

This story re-authors the orbital data into the **one-file-per-system** unit
ADR-141 mandates, starting with `yula` (the system current play occupies). It
deletes the unwarranted hierarchy tier. The payoff: the existing `system_root()`
contract (one parent-less primary per file) holds verbatim downstream, and a
content author — including future homebrew authors per ADR-140 — faces a
tractable single-system file, not a 140-body monolith.

## Technical Guardrails

**Lane:** GM/World-Builder (YAML only). No engine code in this story.

**Key files:**
- `worlds/perseus_cloud/orbits.yaml` — **delete** the fabricated primary (orbits.yaml:17, `type: star`, label "PERSEUS CLOUD"); retire the monolith.
- `worlds/perseus_cloud/systems/yula.yaml` — **new**, the first per-system orrery file.

**Patterns to follow:**
- `yula`'s real primary becomes the **single parent-less body** (root of the file). Its directly-parented children are re-homed in by stripping the `parent: perseus_cloud` linkage. This is exactly what makes `system_root()` work unchanged in 98-2.
- Preserve calendar linkage (ADR-130): `clock.epoch_days` at file level, `period_days` + `epoch_phase_deg` per body. The shared game clock drives angular positions; do not invent a per-system clock.
- The 97 correctly-parented bodies across the cluster are **salvageable** — this is restructuring, not rewriting. Re-home `yula`'s subset; leave the rest for on-demand authoring.

**What NOT to touch:**
- Do **not** author the other ~33 systems (Diamonds-and-Coal — on demand).
- Do **not** touch `coyote_star` (genuine single system, out of epic scope).
- Do **not** promote `perseus_cloud.sector.json` to anything — it stays a dormant authoring reference (No Silent Fallbacks).
- Do **not** add jump mechanics to `cartography.yaml` here — that is 98-4.

## Scope Boundaries

**In scope:**
- Create `systems/yula.yaml` with `yula`'s real primary as sole root + its re-homed children, calendar fields intact.
- Delete the fabricated `perseus_cloud` primary tier.
- Retire the monolithic `orbits.yaml` for `perseus_cloud`.

**Out of scope:**
- Authoring any system file other than `yula` (deferred — on demand).
- Server loader changes to find the new file (98-2).
- UI rendering of the result (98-3).
- Jump-mechanics edges in `cartography.yaml` (98-4).

## AC Context

- **AC1 — `systems/yula.yaml` exists, correctly rooted.** `yula`'s real primary
  is the single parent-less body; its directly-parented children are present with
  the `parent: perseus_cloud` linkage stripped (so `yula` is their root). *Test:*
  load the file, assert exactly one body has no `parent`, and it is `yula`'s
  primary; assert former children now parent to `yula`'s bodies, not to
  `perseus_cloud`.
- **AC2 — fake primary deleted.** The fabricated `perseus_cloud` body
  (orbits.yaml:17) exists nowhere, and no body anywhere parents to it. *Test:*
  grep/parse asserts no body has `id: perseus_cloud` and no `parent: perseus_cloud`
  remains in any authored system file.
- **AC3 — calendar linkage preserved (ADR-130).** `yula.yaml` carries
  `clock.epoch_days`; every body carries `period_days` + `epoch_phase_deg`.
  *Test:* schema/load assertion that these fields are present and well-typed;
  resolving body positions through `orbital/clock.py` against a campaign day count
  yields finite angles. *Edge case:* a static body (a star) still needs a defined
  phase/period or an explicit "fixed" marker — confirm the renderer's expectation.
- **AC4 — monolith retired.** `orbits.yaml` is removed for `perseus_cloud` (preferred), or emptied to a documented retirement stub. *Test:* the loader path in 98-2 must agree with whichever form is chosen — coordinate so S1 fails loud rather than silently reading a stale monolith.
- **AC5 — other systems intentionally absent.** No `systems/<id>.yaml` exists for the other ~33 systems, and that is *correct*: a node with no system file is still a valid jump destination (98-2 AC3 makes the orrery drill-down fail loud, while the galactic graph still renders the node). *Test:* assert the `systems/` dir contains only `yula.yaml` at end of this story.

## Assumptions

- The 97 correctly-parented bodies in the current `orbits.yaml` accurately describe `yula`'s real orbital structure once the fake root is stripped — i.e., re-homing is mechanical, not a re-derivation of orbital elements. If `yula`'s bodies turn out to have been distorted to fit the single-disc fiction (e.g., AU values fabricated for the cluster layout), log a Design Deviation — that becomes a re-authoring task, not a restructuring one.
- The TDD workflow tag for a YAML-only content story means tests are **schema/load-validation** tests (file parses, root invariant holds, calendar fields present), not engine behavior tests. Confirm with TEA which harness validates content files.
- 98-2 (S1) is **not** merged before this — this story ships the data; S1 ships the resolver. They are sequenced C1 → S1, so the loader will look for `yula.yaml` only after it exists.
