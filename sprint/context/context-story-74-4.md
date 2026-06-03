---
parent: context-epic-74.md
workflow: tdd
---

# Story 74-4: World-flavor hardening — isinstance shape-guard on raw world theme/audio, weather-absence OTEL span, remove dead seed_lore_from_genre_pack

## Business Context

Epic 74 moves all *flavor* (lore, theme, audio, weather, …) from the genre tier to the
world tier. Story **74-1** made the genre-tier flavor loads optional and added the
world-tier loaders; **74-3** authored world lore for every live world and unblocked
genre-lore deletion. Both are **done**. This story is the **hardening pass** that closes
three loose ends the refactor left behind — it adds no new feature surface, it makes the
post-refactor loader *fail loud and observable* and deletes the code the refactor orphaned.

Why it matters to the playgroup: the load path is what stands between Jade/Keith authoring
a new world's `theme.yaml`/`audio.yaml`/`weather.yaml` and that world actually playing.
A malformed flavor file that flows through silently (AC1) produces a subtly-wrong session
with no error — exactly the "why isn't this quite right" debugging the **No Silent
Fallbacks** principle exists to prevent. The weather-absence span (AC2) is the GM-panel
lie detector for "this world has no weather *by design*" vs "the weather subsystem broke."
And dead code (AC3) is, per house rule, worse than no code.

This is a `sidequest-server`-only, 3-point refactor. No content, UI, or daemon changes.

## Technical Guardrails

**Repo / branch:** `sidequest-server` only; branch `feat/74-4-world-flavor-hardening` off
`develop` (github-flow — branch + PR + squash-merge, even solo).

**Test env (mandatory or the suite lies):**
- `SIDEQUEST_DATABASE_URL=postgresql://$USER@localhost:5432/sidequest_test` — unset →
  ~33 phantom `MissingDatabaseUrlError` (ADR-115; not a regression).
- `SIDEQUEST_GENRE_PACKS` set — unset → content-gated `tests/genre/` calibration tests
  silently SKIP.
- Gate on the **full** suite (`tests/server/` + `tests/game/` + `tests/genre/` +
  `tests/integration/`), not a scoped subdir — record the baseline failure list first;
  anything not in it is a regression.

**Established patterns to mirror (don't invent new shapes):**
- **AC1 — shape guard.** `loader.py:1077` loads `world_theme`/`world_audio` via
  `_load_yaml_raw_optional(...)` returning `Any`. The required-flavor surfaces already
  fail loud via `GenreLoadError`/the loader's error path (`sidequest/genre/error.py`).
  The guard must raise the loader's existing error type with a message naming the
  offending file and the bad type — not a bare `assert`, not a silent coerce/skip.
  Mirror how mandatory files validate today (see the `visibility_baseline` /
  `lethality_policy` required-load precedent referenced in the epic context).
- **AC2 — OTEL span.** Existing spans `world_grounding.weather_proposed` /
  `world_grounding.weather_used` live in
  `sidequest/telemetry/spans/world_grounding.py`, re-exported via
  `sidequest/telemetry/spans/__init__.py:108-109`. Add the weather-**absence** span in
  the *same* module, re-export it the *same* way, and emit it at the seam where weather
  is resolved for a world and found to be absent (companion to `weather_used`, which
  fires when weather IS returned). Per ADR-132 / WatcherHub, use the same emit helper
  shape as its siblings.
- **AC3 — dead-code delete.** `seed_lore_from_genre_pack` is defined at
  `sidequest/game/lore_seeding.py:53`, exported at `:476`. Its docstring already calls it
  a survivor ("world lore exclusively … survives as a"). One non-test reference remains at
  `sidequest/server/websocket_handlers/chargen_mixin.py:1124` — **read that call site and
  confirm it is genuinely dead** (the comment there says it was a wiring fix; verify 74-3
  made the genre-seed a no-op / unreachable) before removing. Then delete the function,
  its export, and its now-orphaned tests **in this same PR** (house rule). Affected tests:
  `tests/game/test_lore_seeding.py` (note `:232` already xfails it "deleted in epic 74"),
  `tests/server/test_lore_seeding_dispatch.py`,
  `tests/server/test_lore_store_resume_reseed.py`,
  `tests/genre/test_genre_flavor_world_tier.py:261`. Remove only the assertions that
  exercise the genre-pack seeding path; keep `seed_lore_from_world` coverage intact.

**Hard rules:**
- **No Silent Fallbacks** — AC1's whole point. A non-dict flavor file must abort the load.
- **No Stubbing** — AC2 emits a real span at a real seam, not a placeholder.
- **Delete dead code in the same PR** — AC3; do not leave the function "for later."
- **Every test suite needs a wiring test** — each AC ships an integration/wiring test:
  AC1 = malformed world flavor file triggers the guard through the real loader; AC2 = the
  absence span fires for a real (or fixture) weatherless world reaching the resolve seam;
  AC3 = a test proving the genre-seed path no longer exists / chargen still seeds world
  lore.

## Scope Boundaries

**In scope:**
- isinstance/shape validation on raw `world_theme` and `world_audio` in `loader.py`,
  failing loud (AC1).
- A `world_grounding.weather_absent` (name TBD by TEA, follow the `weather_*` convention)
  OTEL span + its `__init__` re-export + emit at the weather-resolve seam (AC2).
- Deletion of `seed_lore_from_genre_pack`, its export, and orphaned genre-seed tests; the
  chargen_mixin reference verified-dead and removed (AC3).
- Wiring/integration test per AC.

**Out of scope:**
- The other genre→world flavor *moves* themselves (cultures/archetypes/tropes engine,
  visual_style render-pipeline repoint) — those are 74-1's landed work or separate stories.
- `seed_lore_from_world` behavior — leave intact; only the *genre-pack* seeding path dies.
- Any `sidequest-content` YAML changes — this is a server-only story. (If a malformed
  fixture is needed for the AC1 test, add it under the server's `tests/` fixtures, not the
  live content tree — tests must not point at live content.)
- Re-litigating `theme.yaml` as flavor — it carries CSS styling but is loaded as a
  world-tier file here; the guard is about *shape*, not its mechanics-vs-flavor status.

## AC Context

### AC1 — isinstance shape-guard on raw world theme/audio
`_load_yaml_raw_optional(world_path / "theme.yaml")` and the `audio.yaml` equivalent at
`loader.py:1077`-ff return `Any`. **Given** a world whose `theme.yaml` or `audio.yaml`
parses to a non-mapping (e.g. a list, scalar, or empty/`null`), **when** `_load_single_world`
runs, **then** the loader raises its error type with a message identifying the file and the
unexpected type — it must NOT pass the malformed value downstream as if valid. **And** a
well-formed (dict) or absent (`None`, already handled) file still loads unchanged.
*Wiring proof:* an integration test loads a fixture world with a malformed flavor file and
asserts the loader raises (not that an isolated helper raises).

### AC2 — weather-absence OTEL span
**Given** a world that authors no weather (the resolve seam finds weather absent — the
companion condition to `weather_used`, which fires when `"weather" in include` AND
`ctx.weather_state is not None`), **when** that resolve runs, **then** a new
`world_grounding.weather_*` span fires recording the absence, so the GM panel distinguishes
"no weather by design" from "weather subsystem broken." It lives in
`telemetry/spans/world_grounding.py`, is re-exported from `telemetry/spans/__init__.py`,
and shares the `seed`/join-key convention of its siblings where applicable.
*Wiring proof:* a real-OTEL test (capture emitted spans) asserts the absence span fires on
a weatherless path — not just that the emit function exists.

### AC3 — remove dead seed_lore_from_genre_pack
**Given** 74-3 deleted genre-tier lore, `seed_lore_from_genre_pack` has no live production
effect. **When** this story lands, **then** the function and its `__all__` export at
`lore_seeding.py:53/:476` are gone, the `chargen_mixin.py:1124` reference is confirmed dead
and removed, and the orphaned genre-seed tests are deleted — **in this PR**. `seed_lore_from_world`
and its tests remain. **And** the full suite is green (with DB + GENRE_PACKS env set);
no test still imports the removed symbol.
*Wiring proof:* a test asserting world-lore seeding still reaches the LoreStore through the
chargen path (the surviving, intended behavior), confirming the deletion didn't sever it.
