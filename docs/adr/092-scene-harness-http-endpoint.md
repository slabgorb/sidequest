---
id: 92
title: "Scene Harness — Dev-Gated HTTP Endpoint for Scenario Fixtures"
status: accepted
date: 2026-05-02
deciders: ["Keith Avery", "Leonard of Quirm (Architect)"]
supersedes: [69]
superseded-by: null
related: [23, 38, 69, 87]
tags: [code-generation, frontend-protocol]
implementation-status: partial
implementation-pointer: 87
---

# ADR-092: Scene Harness — Dev-Gated HTTP Endpoint for Scenario Fixtures

> Successor to [ADR-069](069-scenario-fixtures.md). Ratifies the design pivot
> that occurred during the 2026-04 port: the CLI-driven fixture flow specified
> in ADR-069 was never built in Python; a UI-driven HTTP harness was wired
> instead. This ADR documents the new shape, accepts the trade-offs, and
> closes the open design question flagged in [ADR-087](087-post-port-subsystem-restoration-plan.md).

## Context

[ADR-069](069-scenario-fixtures.md) addressed a real and still-current problem:
playtesting specific game states (combat at low HP, mid-game NPC dialogue,
active chase, trope beat at 50%) requires 20–30 minutes of play to reach the
state of interest, which makes prompt iteration, OTEL verification, and new
subsystem validation impractically slow. ADR-069's problem statement remains
the canonical justification — this successor does not relitigate it.

What ADR-069 specified was a CLI-first flow:

1. `sidequest-fixture load <name>` — workspace binary, ~200 LOC.
2. Reads `scenarios/fixtures/<name>.yaml`, hydrates into a `GameSnapshot` with
   field-level defaulting, writes the snapshot to `~/.sidequest/saves/...` via
   the existing `SqliteStore`.
3. The existing `dispatch_connect()` restore path picks up the save unchanged.
4. Companion integration: `sidequest-promptpreview --fixture <name>` and a
   `fixture:` key plus `strategy: restore` in playtest-driver scenario YAML.
5. The architectural elegance was **"zero new server code"** — the CLI did
   the work of priming a save file, and the server was unchanged.

The Rust era implemented this. `sidequest-api/crates/sidequest-fixture/`
existed with `hydrate.rs`, `schema.rs`, `error.rs`, and a `scene_harness_wiring`
test (preserved at <https://github.com/slabgorb/sidequest-api>). The 2026-04
port to Python ([ADR-082](082-port-sidequest-api-back-to-python.md)) did not
carry the crate forward, and a partial restoration with **a meaningfully
different design** was begun and left half-wired:

- `sidequest-ui/src/App.tsx:1183–1217` reads `?scene=NAME` from the URL,
  POSTs `/dev/scene/:name`, expects `{ slug }` in the response, and navigates
  to `/solo/:slug` so `AppInner` owns the WebSocket session via the existing
  slug-based flow. Fail-loud on error.
- 4 fixture YAMLs in `scenarios/fixtures/` (`combat_test.yaml`, `dogfight.yaml`,
  `negotiation.yaml`, `poker.yaml`), all dated 2026-04-21, schema-conformant
  to ADR-069's YAML shape. Each YAML's header documents the URL form
  `http://localhost:5173/?scene=<name> (requires DEV_SCENES=1)`.
- Server: `POST /dev/scene/{name}` does not exist. The UI POSTs into the void.
  No fixture hydrator. No `sidequest-fixture` CLI binary. No
  `sidequest-promptpreview`.

These two shapes are not implementation variants. ADR-069's "no new server
code" claim is a Decision-section commitment; the wired-but-dark UI design
violates it intentionally. ADR-087's row 125 named this as the gating
question: pick one before restoration. This ADR picks.

## Decision

**The scene harness is a dev-gated HTTP endpoint on the server, driven by a
URL parameter from the UI. The CLI-driven design from ADR-069 is retired.**

Concretely:

1. **Single new server route.** `POST /dev/scene/{name}` on `sidequest-server`.
   Gated behind the `DEV_SCENES=1` environment variable — the route is not
   registered when the flag is unset, so production builds carry zero scene-
   harness surface. Returns `{ "slug": "<game_slug>" }` on success; structured
   error JSON on failure.
2. **Server-side hydrator.** The endpoint reads
   `scenarios/fixtures/{name}.yaml`, hydrates a `GameSnapshot` (the ADR-069
   YAML schema is reused unchanged), persists via the existing `SqliteStore`,
   mints a `game_slug`, and returns it. The fixture YAML schema is a fresh-
   game shape — multi-player and reconnect concerns are out of scope.
3. **UI side stays as-is.** `App.tsx:1183–1217` is the canonical client. The
   `?scene=NAME` URL parameter triggers the POST; the response slug drives a
   `navigate('/solo/:slug')`; `AppInner` mounts and connects via the normal
   slug-based WebSocket flow. No new UI is introduced.
4. **Fixture YAMLs are unchanged.** The four YAMLs in `scenarios/fixtures/`
   continue to use the ADR-069 schema. Adding new fixtures requires only a
   new YAML file plus a fixture-name passing through to the URL parameter.
5. **Failure is loud.** Missing fixture YAML → 404 with the missing path in
   the body. Hydration error → 422 with field-level detail. Endpoint
   unreachable (server not running with `DEV_SCENES=1`) → UI surfaces
   `window.alert` with the error. No silent fallback to manual chargen.

### Why this shape, not ADR-069's CLI

| Concern | ADR-069 CLI | This ADR (HTTP) |
|---|---|---|
| New server surface | None | One dev-gated route |
| New binary | `sidequest-fixture` workspace crate (~200 LOC) | None |
| Entry point | Shell out from the dev's terminal | `?scene=` URL param in the browser |
| Pre-hydration step | Required (CLI writes save.db before connect) | Folded into the request |
| Test driver integration | `playtest.py` invokes the CLI before connecting | `playtest.py` opens `?scene=` URL or POSTs the endpoint |
| Production exposure | Zero | Zero (gated by env flag, route absent when off) |
| Promptpreview integration | Spec'd (`--fixture` flag) | Out of scope (promptpreview itself does not exist) |

The CLI design's "zero new server code" property was real and attractive when
the server was Rust. After the port, the server already had to grow slug-
routing for `/solo/:slug` and `/play/:slug` ([ADR-038](038-websocket-transport-architecture.md));
a single companion route gated by `DEV_SCENES=1` is small change. The CLI
design's cost — a new binary with packaging, distribution, install path, and
its own version-skew story versus the server — is no longer justifiable for
a dev-only harness. The browser-driven shape is also closer to how the
playgroup and Keith actually iterate (Vite running, `?scene=` in the URL bar).

### What is lost vs. ADR-069

- **No CLI ergonomics.** A dev cannot `sidequest-fixture load combat_test`
  from the shell without the server running. Acceptable: the server is
  already running during any iteration cycle, and the scene harness is for
  iteration.
- **No `--player` flag.** ADR-069 used `--player fixture` to namespace
  fixture saves under a separate player. Replaced by: every scene-harness
  load mints a fresh `game_slug`, so collisions with "real" saves are
  impossible by construction.
- **No `sidequest-promptpreview --fixture`.** Promptpreview itself does not
  exist in Python. When (if) it lands, it is free to grow its own fixture
  loader against the same `scenarios/fixtures/*.yaml` shape — the YAML is
  the shared contract, not the loader.
- **Test driver integration is different.** `playtest.py`'s `fixture:` key
  (specified in ADR-069 §Integration Points 1) is unimplemented. When
  added, it should POST `/dev/scene/{name}` directly (or load `?scene=` in
  a browser-driver) rather than shell out to a CLI.

## Hydration rules

Inherits from ADR-069 §Hydration Rules without modification. Briefly:

1. Top-level `genre:` and `world:` are required.
2. `character:` block hydrates into `characters[0]`.
3. `combat:` block hydrates into `CombatState` fields.
4. `npcs:` creates NPC entries with name, role, and disposition.
5. `quests:` is `dict[str, str]` — quest name to status string.
6. `tropes:` creates trope state entries with `id` and `progression`.
7. `resources:` populates resource state.
8. Unspecified fields use snapshot defaults.
9. `turn:` populates the interaction turn counter.

Hydration code uses pydantic with `model_config = ConfigDict(extra="ignore")`
and field defaults so new `GameSnapshot` fields are auto-defaulted; only
breaking renames require fixture updates.

## OTEL

Per the project's OTEL principle, the harness must emit watcher events the
GM panel can verify. At minimum:

- `intent: scene_harness_load` with `fixture_name` and `game_slug` attributes.
- `scene_harness.hydrate.ok` with field counts (npcs, tropes, resources hydrated).
- `scene_harness.hydrate.error` on failure with the missing/invalid path.
- `scene_harness.persist.ok` with the slug and store path.

Without these, the harness is a black box and the lie-detection invariant
([ADR-031](031-game-watcher-semantic-telemetry.md)) breaks at exactly the
seam where prompt engineers most need it.

## What this does NOT change

- **Fixture YAML schema** — unchanged from ADR-069.
- **Existing fixture YAMLs** in `scenarios/fixtures/` — unchanged.
- **UI scene-harness code** in `App.tsx:1183–1217` — unchanged. Already
  correct for this design.
- **`SqliteStore` and `dispatch_connect`** — unchanged. The endpoint persists
  via the existing store, and the slug-based reconnect flow does the rest.
- **Production behavior** — zero impact. The route is absent unless
  `DEV_SCENES=1` is set at server start.

## Consequences

### Positive

- Resolves the design pivot blocking ADR-087's P0 restoration item.
- Single self-contained server change (route + hydrator) closes the loop.
- Reuses 100% of existing fixture YAMLs and 100% of existing UI harness code.
- Aligns with how the dev workflow actually runs (server up, Vite up,
  browser open).
- New fixtures are pure content — drop a YAML in `scenarios/fixtures/`,
  visit `?scene=<name>`. Authoring effort = filename + body.

### Negative

- The "zero new server code" elegance of ADR-069 is gone. The trade is
  one dev-gated route in exchange for not maintaining a separate binary.
- `DEV_SCENES=1` is a new operational invariant. If a developer forgets to
  set it, the UI fails loudly (good) but the failure mode requires reading
  the alert. Mitigation: server logs the route registration on startup.
- Fixture YAMLs and the hydrator must stay coupled. If `GameSnapshot` adds
  a non-defaultable field, every fixture needs an update. Pydantic defaults
  + `extra="ignore"` keeps this manageable, but breaking-rename discipline
  is now a content-repo concern.

### Neutral

- ADR-069 is superseded, not deleted. Its problem statement, hydration
  rules, and starter-fixture catalog remain canonical and are referenced
  here by pointer.
- The route shape (`POST /dev/scene/{name}`) was chosen to match what the
  UI already speaks. Changing the route means changing two places.

## Alternatives considered

### A. Amend ADR-069 in place

Rejected. ADR-069's Decision and Design sections describe a different
architectural shape (CLI binary, save.db pre-write, "no new server code").
Editing them to describe the HTTP design would launder history and lose
the trail of *why* the original CLI design was attractive. ADRs are
immutable history; pivots get successors.

### B. Build the ADR-069 CLI as specified, keep the UI HTTP path too

Rejected. Two entry points for the same operation is double the surface
area, double the test burden, and presumes someone will use the CLI
in practice — but the project has run for two weeks without it and
shipped four fixtures via the URL-param path.

### C. Server-Sent Events / WebSocket-only flow

Rejected. The harness is a one-shot stage-and-mint operation. SSE would be
ceremony; reusing the existing slug-based WebSocket connect (post-redirect)
is correct.

### D. Defer the decision

Rejected. ADR-087 P0 cannot proceed without the choice made. Two weeks of
"unresolved design pivot" is exactly the kind of stall ADR-087 was written
to end.

## Implementation

| Item | Effort | Repo |
|---|---|---|
| `POST /dev/scene/{name}` route gated by `DEV_SCENES=1` | ~50 LOC | `sidequest-server` |
| Fixture hydrator (`hydrate_fixture`, `Fixture` schema, error types) | ~150 LOC | `sidequest-server` |
| OTEL spans for `scene_harness_load` / `hydrate.ok` / `hydrate.error` / `persist.ok` | ~30 LOC | `sidequest-server` |
| Tests: hydrator unit tests + endpoint wiring test (per the wiring-test rule) | ~150 LOC | `sidequest-server` |
| Fixture YAML changes | Zero | `sidequest-content` |
| UI changes | Zero | `sidequest-ui` |
| Optional: `playtest.py` `fixture:` key support | ~30 LOC | orchestrator |

## Implementation status (2026-05-02)

**partial.** UI side fully wired (`App.tsx:1183–1217`); fixture YAMLs in place
(`scenarios/fixtures/*.yaml`, four fixtures); server endpoint and hydrator
absent. Restoration tracked in [ADR-087](087-post-port-subsystem-restoration-plan.md)
P0; ADR-069's row in 087's table is owed an update to point here instead of
to the unresolved-pivot framing.
