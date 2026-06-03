---
parent: "65"
---
# Story 65-10 Context

## Title
Reference TOC/section-mapping repair + register POI and Cast sections

## Metadata
- **Story ID:** 65-10
- **Points:** 2
- **Priority:** p2
- **Workflow:** tdd
- **Repo:** server
- **Epic:** 65 — Content Infrastructure — R2 asset tracking and audit
- **Base branch:** develop

## Business Context
Lore reference pages (GET /reference/lore/{pack}/{world}, ADR-135 PUBLIC
projection) are the public table tool. This story entered the sprint as a
sparse STUB — title + points only, no description and no acceptance criteria.
The title ("TOC/section-mapping repair + register POI and Cast sections") was
written BEFORE the epic-65 sibling slices landed, and is now partially stale.

## ⚠️ BLOCKER — Resolve scope FIRST (before RED)
The title is NOT literally current. Since it was written:
- **65-9** (done, approved) already **registered the Cast section** on the lore page.
- **65-8** (done) already renders POI images.
- **65-11** (done) added the Map section; **65-12** (done) added the Timeline section.

All three dynamic sections (Cast, Map, Timeline) currently **ad-hoc append**
themselves to `kept_toc` + body HTML *after* `_wrap_sections_by_toc`, rather
than registering through the declarative `PACK_TOC` / `TOC_TO_FILES` machinery.

So "register POI and Cast sections" is **already done**. What plausibly remains
is the **"TOC/section-mapping repair"** half. TEA/Dev (pull Architect if needed)
must pick the real scope before writing tests. Candidate interpretations:
- **(A) — most likely:** Formalize the dynamic-section registration. Replace the
  three ad-hoc append blocks with one declarative registry so a dynamic section
  can never leave a dangling TOC entry (or a TOC entry with no rendered body, or
  vice-versa). Add an invariant/guard + OTEL span proving TOC↔section parity.
- **(B):** Ensure POI is properly represented in `PACK_TOC` / `TOC_TO_FILES`
  (audit whether POI has a TOC entry on par with geography/cast/map/timeline).
- **(C):** Something narrower the title named that the siblings already absorbed —
  in which case this story may be a **partial no-op / close-as-done** candidate;
  if so, say that explicitly with evidence rather than inventing busywork.

**Do not assume the title. Confirm against the code, then write ACs.**

## Technical Guardrails
- **No source-text wiring tests** (server CLAUDE.md): behavior / OTEL /
  fixture-driven only. At least one integration test hits the REAL
  `/reference/lore/{pack}/{world}` route via `gated_client`.
- **OTEL on every decision** (CLAUDE.md): any new section-mapping/repair decision
  emits a span in the reference family so the GM panel can verify it engaged.
  Use `telemetry/spans/reference.py` + `FLAT_ONLY_SPANS`; assert via
  `span_attrs_by_name` / `otel_capture` with complement assertions.
- **No Silent Fallbacks:** a missing/malformed section input fails LOUD, never
  silently drops a TOC entry.
- **ADR-135 PUBLIC projection only:** no `?audience` param, no GM mode.
- Content invariants (every pack/world has X) belong in the pack VALIDATOR, not
  pytest unit tests.

## Key Code References
- TOC machinery: `PACK_TOC` + `TOC_TO_FILES` — `sidequest/server/reference_theme.py` (~268–378)
- Section assembly + dynamic appends: `assemble_lore_page` —
  `sidequest/server/reference_renderer.py` (Cast ~1350–1377, Map ~1379–1407,
  Timeline ~1409–1424); `_wrap_sections_by_toc` (~960–1005)
- Route: `lore_page` — `sidequest/server/reference_routes.py` (~119)
- Reference OTEL spans: `sidequest/telemetry/spans/reference.py`, `FLAT_ONLY_SPANS`
- Test fixtures: `gated_client`, `otel_capture`, `span_attrs_by_name`

## Scope Boundaries
- **In scope:** the TOC/section-mapping repair the BLOCKER section resolves to,
  server-only, on the lore reference page.
- **Out of scope:** new lore sections (Cast/Map/Timeline already shipped),
  any GM-audience projection, content authoring, UI changes.

## AC Context
ACs are **TBD pending the scope decision above** — TEA must author them after
reconciliation. They must cover: the chosen repair behavior, a real-route
integration test, an OTEL span proving the decision engaged (with a complement
assertion), a loud-failure edge, and regression that the existing
geography/cast/map/timeline/history sections still render unchanged.

---
_Recovered by SM (sm-setup context-gap recovery) from the sparse 65-10 stub +
epic-65 sibling history. Scope intentionally left open for TEA/Architect._
