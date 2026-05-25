---
parent: epic-51.yaml
workflow: tdd
---

# Story 51-4: Remove DEV_SCENES gate + add fixture picker to connect screen

## Business Context

The scene harness (ADR-092) is currently gated behind `DEV_SCENES=1` — an env var that must be set at server startup to register the `POST /dev/scene/{name}` route. This gate was appropriate when the harness was a raw dev tool, but it now adds zero security value: the Cloudflare Zero Trust tunnel already gates all access to the server (see memory `project_auth_cloudflare_zero_trust`). The env var just makes fixtures harder to use — Keith has to remember to set it, and the `just serve` (production-style) recipe explicitly omits it, so fixtures vanish when running through the tunnel.

This story removes the gate and adds a user-facing fixture picker to the ConnectScreen, turning the scene library from a dev-only power tool into a first-class entry point.

**Audience:** Keith (the forever-GM who authored every fixture and needs fast iteration); the playgroup for playtesting specific scenarios without navigating through character creation.

**Expected outcome:** The server always registers the scene harness route. A new `GET /dev/scenes` endpoint returns metadata for all available fixture YAMLs. The ConnectScreen shows a "Scene Library" section where clicking a fixture card loads the scene via `?scene={name}` and connects.

## Technical Guardrails

**Key files (server):**
- `sidequest-server/sidequest/server/app.py` — Lines 275-291: the `DEV_SCENES` gate. Remove the `if _os.environ.get("DEV_SCENES") == "1"` conditional and always register `create_scene_harness_router()`. Also remove the `SIDEQUEST_FIXTURES_DIR` env var indirection — hardcode the `fixtures_dir` resolution to `scenarios/fixtures` relative to the orchestrator root, matching the justfile's `SIDEQUEST_FIXTURES_DIR` default.
- `sidequest-server/sidequest/server/scene_harness_router.py` — Add a `GET /dev/scenes` handler to the existing router. Returns `[{name, description, genre, world}]` by scanning `fixtures_dir` for `*.yaml` files and extracting the top-level `genre`, `world`, and optional `description` fields via `yaml.safe_load`. Use the same `_FIXTURE_NAME_RE` validation that `hydrate_fixture` already applies.
- `sidequest-server/sidequest/game/scene_harness.py` — No changes needed. The hydrator is already decoupled from the gate.

**Key files (UI):**
- `sidequest-ui/src/screens/ConnectScreen.tsx` — Add a "Scene Library" section. Fetch `GET /dev/scenes` on mount. Display fixture cards showing name + description + genre badge. Clicking a card navigates to load `?scene={name}` and connects (or use `POST /dev/scene/{name}` directly and navigate to the returned slug).

**Key files (cleanup):**
- `justfile` — Lines 72-73: remove the `DEV_SCENES="${DEV_SCENES:-1}"` and `SIDEQUEST_FIXTURES_DIR="${SIDEQUEST_FIXTURES_DIR:-{{root}}/scenarios/fixtures}"` env vars from `_server-cmd`. Line 119: update the comment on `serve` that mentions "no DEV_SCENES/FIXTURES_DIR".
- `docs/playtest-cookbook.md` — Remove any references to `DEV_SCENES` (currently none found, but verify).

**Patterns to follow:**
- The existing `scene_harness_router.py` for OTEL span patterns (`scene_harness.intent.load`, etc.). The new listing endpoint should emit a span for discoverability.
- The existing `create_rest_router()` pattern in `app.py` for always-registered routers.
- The `ConnectScreen.tsx` world-picker pattern for fetch-on-mount + card display.

**What NOT to touch:**
- The `POST /dev/scene/{name}` endpoint itself — its behavior is unchanged.
- The `hydrate_fixture()` function — no changes to hydration logic.
- The `_disambiguate()` slug logic — no changes.
- The `just serve` recipe — it currently omits DEV_SCENES intentionally; after this story, scene harness is always available so `serve` needs no change beyond removing the stale comment.

## Existing Test Coverage

- `tests/server/test_scene_harness.py` — Integration tests for `POST /dev/scene/{name}`. These tests currently use `monkeypatch.setenv("DEV_SCENES", "1")` in `_build_dev_scenes_app()`. After this story, that env var is no longer needed — tests should be updated to remove the `DEV_SCENES` setup while keeping the route registration verification.
- `tests/game/test_scene_harness_hydrator.py` — Unit tests for `hydrate_fixture()`. No changes needed.

## Acceptance Criteria

### Server
- AC-1: Remove the `if DEV_SCENES == "1"` conditional in `create_app()` — always register `create_scene_harness_router()`.
- AC-2: Always register `create_scene_harness_router()` — the route is present in every `create_app()` call.
- AC-3: Add `GET /dev/scenes` listing endpoint returning `[{name, description, genre, world}]` for each valid YAML in `fixtures_dir`.
- AC-4: Drop `SIDEQUEST_FIXTURES_DIR` env var indirection — resolve `fixtures_dir` from a known path relative to the project root.

### UI
- AC-5: Add "Scene Library" section to ConnectScreen.
- AC-6: Fetch `GET /dev/scenes` on mount.
- AC-7: Display fixture cards (name + description + genre badge).
- AC-8: Click loads the scene and navigates to play.

### Cleanup
- AC-9: Update justfile to remove `DEV_SCENES` and `SIDEQUEST_FIXTURES_DIR` env vars from `_server-cmd`.
- AC-10: Update `just serve` comment to remove DEV_SCENES/FIXTURES_DIR mention.
- AC-11: Update `playtest-cookbook.md` to remove any DEV_SCENES references (if any exist).

## Scope Boundaries

**In scope:**
- Removing the env var gate from `app.py`.
- Adding the listing endpoint to the scene harness router.
- Adding the Scene Library section to ConnectScreen.
- Cleaning up justfile and docs.
- Updating existing tests to remove DEV_SCENES setup.

**Out of scope:**
- Changing fixture YAML schema or hydration logic.
- Adding fixture editing/creation UI.
- Modifying `POST /dev/scene/{name}` behavior.
- Adding fixture-specific OTEL beyond what the listing endpoint emits.

## Fixtures Dir Resolution

The `SIDEQUEST_FIXTURES_DIR` indirection currently allows the fixtures directory to be overridden via env var. The story says to drop this. The resolution should use a stable path relative to the project root. The server already has `genre_pack_search_paths` as a constructor arg; `fixtures_dir` can follow the same pattern — constructor arg with a sensible default. For production, the default `scenarios/fixtures` relative to cwd (the orchestrator root, where `just server` runs from) works. Tests already inject `fixtures_dir` explicitly via `_build_dev_scenes_app`.
