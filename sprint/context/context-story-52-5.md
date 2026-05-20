---
parent: context-epic-52.md
workflow: tdd
---

# Story 52-5: UI End-to-End Wiring Test — TacticalGridRenderer Renders Runtime-Sourced cavern_image_url + OTEL Assert

## Business Context

Epic 52's pipeline (materializer mask → BLOB persistence → server PNG sidecar via
`resolve_asset_url`) is fully implemented across 52-2/52-3/52-4. The renderer
consumer end has been live for static caverns since before the epic. **This story
closes the loop and proves it.**

Without an end-to-end wiring test, the project has no way to catch the most likely
regression: a runtime-generated cavern silently falling back to a missing or static
URL because some seam in `room_file_loader → protocol payload → wire payload →
TacticalGridRenderer prop` quietly drops the runtime-sourced value. SOUL.md and
CLAUDE.md both call this out — "No Silent Fallbacks" and "Verify Wiring, Not Just
Existence." 52-5 is the wiring test that makes the entire epic shippable.

**What this story owns:**
- One end-to-end UI test (React/Vitest) proving `TacticalGridRenderer` mounts a
  runtime-sourced `cavern_image_url` (i.e. a PNG produced by the materializer →
  loader → resolver pipeline, **not** a static asset under `genre_packs/.../rooms/`)
- A server-side OTEL assertion that the runtime PNG resolution span fires when the
  payload is built (so the GM panel can verify the runtime path is actually in use)
- A wiring test (per CLAUDE.md "Every Test Suite Needs a Wiring Test") that lives
  outside the unit-test pile and reads the prop chain end-to-end

**What this story does NOT own:**
- New runtime mask generation logic (52-2's seam)
- Persistence shape changes (52-3's job)
- Server-side PNG emission code (52-4 shipped it)
- Any change to `TacticalGridRenderer`'s render strategy — if the wiring test
  forces a renderer change, the change is in scope; otherwise the renderer is
  treated as a black box consumer

## Technical Guardrails

### UI layer — already in place

| File | Role |
|------|------|
| `sidequest-ui/src/components/TacticalGridRenderer.tsx` | Consumer; renders cavern PNG from prop |
| `sidequest-ui/src/types/tactical.ts` | Typed wire payload incl. `cavern_image_url` |
| `sidequest-ui/src/lib/tacticalGridFromWire.ts` | Wire → component prop adapter |
| `sidequest-ui/src/__tests__/tactical-grid-renderer.test.tsx` | Existing unit test surface (extend here, don't replace) |

The UI is the renderer consumer — **do not redesign it**. The test should drive a
runtime-shaped payload through `tacticalGridFromWire` and assert the rendered DOM
points at the runtime URL. Static-cavern coverage already exists in
`tactical-grid-renderer.test.tsx`; the new test should sit beside it and use a
fixture that mimics the 52-4 runtime emission shape.

### Server layer — wire-format contract from 52-4

| File | Role |
|------|------|
| `sidequest-server/sidequest/game/room_file_loader.py` | Resolves cavern PNG URL (static + runtime branches) |
| `sidequest-server/tests/game/test_room_file_loader_runtime_png.py` | 52-4 runtime coverage (read for fixture shape) |
| `sidequest-server/tests/integration/test_cavern_static_mount.py` | 52-4 static wiring proof (mirror pattern) |
| `sidequest-server/sidequest/protocol/...` (cavern grid payload model) | `cavern_image_url: str \| None` field |

The new server-side test should exercise the runtime branch end-to-end (mask →
PNG → `cavern_image_url`) and assert an OTEL span fires that names the runtime
source path (the GM panel must distinguish runtime from static). Reuse the
existing fixture style from `test_cavern_static_mount.py` — do not invent a new
harness.

### OTEL — what the GM panel needs

The runtime path must emit a span (or attribute on an existing span) that lets the
GM panel answer: *"is this cavern PNG runtime-generated, or a static asset?"*
Per ADR-090 and the project OTEL Observability Principle, this is non-negotiable.
If 52-4 already emits the span (check before adding one), the story narrows to a
test asserting it fires; if not, the story includes adding the span and asserting
it.

### Constraints (project-wide)

- **No silent fallbacks** — if the runtime PNG can't be resolved, the test should
  watch the loader fail loudly, not paper over a `None`
- **No stubbing** — the wiring test must exercise the real `room_file_loader`,
  not a mock; if a fixture pack is needed, use an existing world (e.g.
  `caverns_and_claudes/worlds/caverns_sunden`) or generate the mask through the
  materializer in setup
- **caverns_sunden is deprecated** as a *content target* (see project memory) but
  legacy save fixtures using it are acceptable as test inputs since 52-4's
  coverage already does so; don't promote it back into live content
- **HP→Edge translation** — not relevant here (no creatures touched), called out
  only to head off accidental scope creep into snapshot mechanics
- **Gitflow** — ui and server both target `develop` (see `.pennyfarthing/repos.yaml`)

## Scope Boundaries

### In scope
- New UI test (React/Vitest) under `sidequest-ui/src/__tests__/` covering the
  runtime payload shape rendering through `TacticalGridRenderer`
- New server-side wiring/integration test (Pytest) proving the runtime branch
  produces a `cavern_image_url` *and* fires the runtime-discriminator OTEL span
- A minimal OTEL emission addition **only if** 52-4 did not already include one
- Fixture data sufficient to drive both tests without standing up the full
  daemon/UI dev server stack

### Out of scope
- Any change to the materializer (52-2's territory)
- Any change to BLOB persistence (52-3)
- Any change to PNG emission strategy (52-4)
- Any change to the existing static-cavern code path or its tests
- Adding new UI features to `TacticalGridRenderer` (it's a consumer, not a target)

## AC Context

| AC | Test / Verification |
|----|---------------------|
| Runtime-sourced `cavern_image_url` rendered by `TacticalGridRenderer` | New UI test: feed runtime-shaped payload through `tacticalGridFromWire`, mount `TacticalGridRenderer`, assert the rendered `<img>` (or background-image) URL matches the runtime path |
| Wire payload preserves runtime URL through adapter | UI test asserts the prop arriving at `TacticalGridRenderer` is the same string the wire payload supplied; no nullification or rewrite in `tacticalGridFromWire` |
| OTEL span fires distinguishing runtime path from static | Server test asserts the runtime-discriminator span (name + attrs verified) appears in the emitted span set when the payload is built for a runtime-mask room |
| Non-test consumers (CLAUDE.md "Verify Wiring") | New test exercises the same `room_file_loader` + protocol path used by the live WebSocket dispatch; no mocks of `room_file_loader.resolve_asset_url` |
| No silent fallback on missing runtime PNG | Server test exercises the failure mode: when the runtime mask is present but the PNG cannot be resolved, the loader raises loudly instead of returning `cavern_image_url=None` |
| Static path remains unbroken | Existing static cavern tests still pass unchanged |

## References

- **ADR-096** (Cavern Renderer Revival) — wire payload contract, cell-stepped math
- **ADR-106** (Runtime Procedural Jaquaysed Megadungeon) — runtime mask source
- **ADR-090** (OTEL Dashboard Restoration) — GM-panel verification doctrine
- **Epic 52 vision** — pipeline layers 1–5 (this story is layer 5)
- **52-4 tests** (`test_cavern_static_mount.py`, `test_room_file_loader_runtime_png.py`) — fixture and OTEL patterns to mirror
- **Project OTEL principle** (CLAUDE.md) — every backend fix must add watcher events
- **SOUL.md "No Silent Fallbacks"** — the loader must fail loudly on missing runtime PNG

## Notes

- The Sünden runtime path is the most likely place a regression hides — the
  static path has had production traffic, the runtime path has had Story 52-4
  unit coverage only. This is the test that proves it through to the renderer.
- This story is a *wiring* story by design — the bulk of work is fixture setup
  and assertion shape, not new production code. If Dev finds production code
  needs to change to make the wiring test pass, that change is the bug 52-5
  exists to surface — treat it as in-scope and fix it here, not in a follow-up.
- TDD discipline: RED phase should land **two** failing tests (one UI, one
  server) before any production change. If 52-4 already fires the OTEL span,
  the server test goes green immediately on first run — that's fine; the wiring
  test is still the contract.
