# Epic 52: Wire Procedural Megadungeon Output to the ADR-096 Cavern Renderer Pipeline

## Vision

ADR-096 (Cavern Renderer Revival — Pre-Rendered Cellular Caverns for Tactical Maps) defined a
static-authoring approach for cavern visualization. ADR-106 (Runtime Procedural Jaquaysed 
Megadungeon) supersedes this with a runtime generator that produces procedural regions.

This epic bridges the gap: the renderer consumer end is fully implemented (UI can render cavern PNGs),
but the procedural materializer is starved — it currently flags the unwired mask gap at 
`materializer.py:57`. We build the seam so procedural regions serialize ADR-096-shaped mask+PNG 
sidecars that the live UI already renders.

**Verdict:** SUBSUME (no new ADR supersedes; ADR-096 amendment clarifies the runtime path).

## Architecture

The pipeline layers:
1. **ADR-106 Runtime Generator** → produces procedural dungeon regions
2. **Materializer Seam (Story 52-2)** → emits ADR-096 mask + derived block per region
3. **Persistence (Story 52-3)** → mask-BLOB column, loader, reload on resume
4. **Server Sidecar (Story 52-4)** → PNG generation from runtime mask via resolve_asset_url
5. **UI Wiring (Story 52-5)** → TacticalGridRenderer renders runtime-sourced cavern_image_url + OTEL

## Related ADRs

- **ADR-096** (Cavern Renderer Revival) — static approach, now amended for runtime use
- **ADR-106** (Runtime Procedural Jaquaysed Megadungeon) — parent generator
- **ADR-082** (Port sidequest-api from Rust to Python) — context for materializer location
- **ADR-090** (OTEL Dashboard Restoration) — GM panel verification

## Phase 1 Stories

| Story | Points | Type | Repos | Workflow | Status |
|-------|--------|------|-------|----------|--------|
| 52-1: ADR-096 amendment + DRIFT/index | 1 | chore | orchestrator | trivial | backlog |
| 52-2: Materializer emits mask + block | 3 | feature | server | tdd | backlog |
| 52-3: Persistence: mask-BLOB + loader | 3 | feature | server | tdd | backlog |
| 52-4: PNG sidecar from runtime mask | 3 | feature | server | tdd | backlog |
| 52-5: UI wiring + OTEL assert | 2 | feature | ui,server | tdd | backlog |
| **Total** | **12** | | | | |

## Key Decisions

- **No new ADR supersedes** — ADR-096 is amended in-place with a "see ADR-106 for runtime generation" note
- **Symmetric related** — ADR-106 points back at ADR-096; no one-way supersedes-by link
- **Materializer is source of truth** — it emits the mask shape; PNG follows from mask
- **OTEL on every decision** — GM panel must verify subsystem engagement
