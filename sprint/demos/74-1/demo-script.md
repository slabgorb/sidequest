> **Pre-requisites:** Server running on `:8765`. GM dashboard open at `http://localhost:8765/dashboard`. Terminal in `sidequest-server/`.

**Scene 1 — Slide 2 (Problem): Show the old hard-require (90 seconds)**

Open `sidequest/genre/loader.py` in the editor and show the comment block above `_load_yaml` calls around line 1125 (the pre-refactor git snapshot). Narrate: "Before this change, every one of these lines raised a file-not-found error if the genre pack didn't have lore, theme, or audio files at the genre root. The loader had no concept of 'optional.'"

*Fallback if live diff unavailable:* show Slide 2 with the before/after table.

**Scene 2 — Slide 3 (What We Built): Run the test suite (60 seconds)**

```bash
cd /path/to/sidequest-server
uv run pytest tests/genre/test_genre_flavor_world_tier.py -v --tb=short
```

Expected output: `17 passed`. Point to the six acceptance criteria listed in the test names — `test_ac1_genre_pack_loads_without_any_genre_flavor`, `test_ac3_genre_lore_no_longer_seeded`, `test_ac4_weather_loads_from_world_dir`, etc.

*Fallback:* show the test result screenshot on Slide 3 with the 17/17 green indicator.

**Scene 3 — Slide 3 continued: Show a live pack loading with world-tier flavor (90 seconds)**

```bash
uv run python -c "
from sidequest.genre.loader import GenreLoader
pack = GenreLoader().load('neon_dystopia')
world = pack.worlds['franchise_nations']
print('World theme:', type(world.theme).__name__, '— not None:', world.theme is not None)
print('Effective theme:', type(pack.worlds['franchise_nations'].effective_theme).__name__)
"
```

Expected output: confirms `world.theme` is populated from the world directory, not the genre root. Narrate: "The world is now the source of truth for its own look and feel."

*Fallback:* show Slide 3 bullet: "World theme loaded from `franchise_nations/theme.yaml`, not `neon_dystopia/theme.yaml`."

**Scene 4 — Slide 4 (Why This Approach): Show the GM dashboard OTEL spans (60 seconds)**

Open the OTEL dashboard. Filter for `op=loaded` and `field=world_theme`. Show two spans — one for `franchise_nations/theme.yaml`, one for `franchise_nations/audio.yaml`. Narrate: "Every time the engine reads world-tier flavor, it leaves a paper trail. If the GM panel ever shows genre flavor being read instead of world flavor, we know a migration step was skipped."

*Fallback:* Slide 4 bullet with span name screenshot: `world_theme state_transition` / `world_audio state_transition`.

**Scene 5 — Slide 5 (Before/After): 45 seconds**

Use the Before/After slide. Point to the single behavioral change: "Before — lore seeding pulled from genre. After — genre_added is always 0. The narrator's memory is world-local."

**Scene 6 — Slide 7 (Roadmap): 60 seconds**

"This story is the unlock. Story 74-2 repoints the consumer surfaces — the reference renderer, the audio backend — to read `World.theme` and `World.audio` instead of the genre object. Story 74-3 authors world-level lore for every live world so the narrator has something to read. Then, and only then, can story 74-4 delete the genre-tier flavor files for good."

---