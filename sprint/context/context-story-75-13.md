# Story 75-13 Context

## Title
Wire ratification gate into ADR-135 reference NPC projection — withhold unratified phantoms (ADR-138 D4)

## Metadata
- **Story ID:** 75-13
- **Type:** story
- **Points:** 2
- **Priority:** p2
- **Workflow:** tdd
- **Repo:** sidequest-server
- **Epic:** RAG Retrieval Layer — Restore Accretion, Budgeted Selection, Universal Retrieval Design

## Problem

ADR-138 §D4 specifies that public reference pages (ADR-135) share the ratification gate with the ADR-118 NPC projection index. An unratified, `observation_pending` phantom NPC is **not** rendered on the public reference page, for the same reason it is not indexed: the world has not committed to it.

Story 75-12 wired the gate into the ADR-118 universal retrieval layer (`entity_sync.py`), consulting `is_projectable()` in the NPC `to_card()` projector and emitting `entity_sync.npc_unratified_skipped` telemetry (ADR-138 §D6). Story 75-13 applies the same gate to the ADR-135 reference-page NPC projection (`reference_renderer.py` Cast section) so unratified phantoms are withheld from players.

The reference page's Cast section reads from `portrait_manifest.yaml` (authored, public NPC content per ADR-135), not from a live session's NPC pool. Authored NPCs are never auto-minted and therefore never `observation_pending=True`. However, the projection must still consult the `is_projectable()` predicate defensively so the two surfaces (retrieval index and reference page) enforce the same rule consistently, and future changes to the reference architecture do not accidentally project unratified members.

## Technical Approach

**Reference page projection source:** The Cast section in `assemble_lore_page` reads authored NPCs from `portrait_manifest.yaml` via `load_cast_entries()` and renders them via `present_lore_cast()`. The flow parallels the ADR-118 path: filter entries through the ratification gate before presentation.

**Implementation pattern (mirror 75-12):**

1. **Projection eligibility gate:** Before looping over `cast_entries` in `present_lore_cast()`, filter each entry through `is_projectable()`. Since entries are dicts from YAML (not live NPC objects), construct a transient `NpcPoolMember` with the entry's NPC data to check `observation_pending`. More pragmatically, since authored portrait_manifest NPCs always have `observation_pending=False` by design, document this assumption and add a defensive invariant check with loud failure (No Silent Fallbacks).

2. **OTEL observability:** Emit a count of withheld unratified NPCs per render via a new span `reference.npc_unratified_skipped` (mirrors the ADR-118 `entity_sync.npc_unratified_skipped` span in 75-12). The span fires as part of the reference-render telemetry so the GM panel can distinguish a quiet narrator (clean cast without phantoms) from a silently-broken gate.

3. **Test coverage:** Red test that:
   - An `observation_pending` pool member (if it somehow entered portrait_manifest) would be excluded from the Cast section.
   - A ratified pool member renders normally.
   - The withholding span fires with the correct count.
   - The reference page is safe-by-design: authored NPCs never carry `observation_pending=True` (defensive invariant).

**Reuse:** The `is_projectable()` predicate from `npc_pool.py` (story 75-11) is the single source of truth; both projections (ADR-118 and ADR-135) consult it.

## Scope
- In scope: wire `is_projectable()` into the reference Cast projection; emit observability span; add wiring test that verifies the gate fires.
- Out of scope: changes to `portrait_manifest.yaml` schema or NPC rendering beyond the ratification filter.

## Acceptance Criteria

**Functional (story behavior):**
- An `observation_pending` pool member is excluded from the public reference Cast section (defensive; such members never authored but must be handled loudly if they appear).
- A ratified pool member / promoted `Npc` renders normally on the reference page.
- The reference page renders successfully for worlds with or without authored Cast entries.

**Observability (ADR-138 §D6):**
- A `reference.npc_unratified_skipped` span is emitted per reference-page render (or per Cast section, or per NPC — decide granularity) with the count of withheld unratified members. The span fires regardless of whether any members were actually skipped (0 is a valid count).
- The span is registered in the telemetry routing table so the GM/dev panel surfaces it.

**Wiring test (proof the gate fires):**
- OTEL-behavior test: render a reference page with both ratified and `observation_pending` pool members; assert the ratified member appears in the rendered HTML and the `observation_pending` member does not; assert the span count is correct.
- No source-text grep (CLAUDE.md: "No Source-Text Wiring Tests") — the test constructs a fixture, renders the page, and asserts behavior, not implementation shape.

**Design principle (safe-by-design):**
- A brief design note in the code or test docstring explaining that `portrait_manifest.yaml` contains only authored NPCs (never auto-minted), so `observation_pending=False` is a design invariant. Defensive checks are present to catch invariant violations loudly (No Silent Fallbacks).

---
_Generated by `pf context create story 75-13` from the sprint YAML; refined per ADR-138 §D4 and 75-12 implementation reference._
