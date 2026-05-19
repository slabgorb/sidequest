---
parent: context-epic-54.md
workflow: trivial
---

# Story 54-1: ADR — Persistent Location Descriptions + Mechanical Manifest

## Business Context

This story lands the **durable architectural contract** behind Epic 54 as an ADR (likely ADR-109) so future agents and future-Keith have a single, version-controlled doctrine page to reference instead of re-deriving the design from the spec each time. It encodes the Zork-Problem-safe two-mode resolver split, the three-tier entity taxonomy, the validator surface, the OTEL contract, and the doctrine quotes from `SOUL.md` / `CLAUDE.md` that justify each design choice.

**Audience:** Future agents arriving at any Epic 54 / Epic 55 story; future-Keith reviewing a design choice nine months from now and wanting to know *why* without re-reading the full spec.

**Expected outcome:** A new ADR in `docs/adr/` with status `accepted`, indexed by `scripts/regenerate_adr_indexes.py`. The ADR is short (relative to the spec) and load-bearing — every story in Epic 54 / 55 cites it.

## Technical Guardrails

**Implementation plan:** `docs/superpowers/plans/2026-05-19-story-54-1-adr-persistent-location-descriptions.md` — task-by-task authoring guide.

**Key files:**
- `docs/superpowers/specs/2026-05-19-persistent-location-descriptions-design.md` — the source design; the ADR distils it.
- `docs/adr/README.md` — ADR index; new entry slots in alphabetically + by id.
- `docs/adr/template.md` (or the nearest existing ADR like ADR-100 / ADR-106 as a structural reference).
- `scripts/regenerate_adr_indexes.py` — auto-regenerates `README.md` and the category-keyed index in `CLAUDE.md`.

**Patterns to follow:**
- Match the existing ADR shape: frontmatter (id, title, status, date, deciders, supersedes/superseded-by, related), Context, Decision, Consequences, Notes.
- Cite ADR-100 (KnownFacts — independent lifecycle), ADR-026 (state mirror — UI extension shape), ADR-031 (game watcher — OTEL fan-out), ADR-103 (native OTEL via tool registry — span emit pattern).
- The doctrine quotes (Zork Problem, Yes-And, Diamonds and Coal) from `SOUL.md` are load-bearing — quote them verbatim.

**What NOT to touch:**
- No code changes. This is purely doctrine.
- Do not pre-empt implementation details that belong in subsequent stories' plans (the ADR is the *what* and *why*; the plans are the *how*).

## Scope Boundaries

**In scope:**
- New ADR file in `docs/adr/`.
- `scripts/regenerate_adr_indexes.py` run + the resulting index updates.
- Status `accepted`.

**Out of scope:**
- Any code change (server, ui, content).
- Migration of any existing ADR.
- Authoring the validator, resolver, UI, etc. — those are 54-2 through 54-9.

## AC Context

**AC-1:** A new ADR file exists in `docs/adr/` with frontmatter (id, title, status: accepted, date: 2026-05-19, deciders, related ADRs), Context, Decision, Consequences, Notes sections. The Decision section names: typed three-tier manifest, two-mode resolver, validator, durable promotions table, encounter overlays, dedicated OTEL spans, prose-only Location UI.

**AC-2:** The ADR cites by id the four reused ADRs: ADR-100 (KnownFacts), ADR-026 (state mirror), ADR-031 (game watcher), ADR-103 (native OTEL).

**AC-3:** `python scripts/regenerate_adr_indexes.py` runs cleanly; `docs/adr/README.md` and the ADR-index block in the project `CLAUDE.md` reflect the new entry.

**AC-4:** The doctrine paragraph quotes Zork Problem, Yes-And, and Diamonds and Coal verbatim from `SOUL.md` and explains how the two-mode resolver encodes the Zork-safe split.
