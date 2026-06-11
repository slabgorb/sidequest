# Per-Genre Runtime Inheritance — What Each World Actually Reads

Grounded in the real loader (`sidequest-server/sidequest/genre/loader.py`,
`magic_loader.py`, `orbital/loader.py`, `game/world_grounding_loader.py`), **not**
file presence. A world loads the **genre pack defaults**, then its own files override
per the rules below. Files that exist on disk but are never read are flagged.

## Legend / resolution rules

| Edge / box | Meaning |
|------------|---------|
| **genre required** | `pack, rules, progression, axes, prompts, visibility_baseline, lethality_policy` — must exist; always loaded (`loader.py:1547-1927`) |
| **genre optional (loaded)** | present optional genre files actually parsed |
| **world override → REPLACE** | world file fully replaces the genre list: `archetypes, cultures, bestiary, char_creation, classes, spells_wwn, chassis_classes, seed_tropes` (`pack.py:327-364`) |
| **world override → COMPOSE** | `magic.yaml` — per-field last-writer-wins + `hard_limits` append (`magic_loader.py:56-157`) |
| **world override → AUTHORITATIVE** | `theme, audio, visual_style, lore, tropes` — world value wins, genre is fallback (`loader.py:1167-1215`) |
| **world-only** | no genre base: `world, cartography, openings, history, npcs, archetype_funnels, rigs, items, portrait_manifest, premises, calendar, orbits, chart` |
| **globbed dirs** | `legends/`, `scenarios/` scanned as directories (`loader.py:1167,1326`); `.gitkeep`/`_meta.yaml` skipped |
| **cultures — dir SHADOWS root** | `if cultures/ dir exists → read the dir (one Culture per `*.yaml`, files lacking a `name:` key skipped as art-pipeline `visual_tokens` overlays); else → read world-root `cultures.yaml` as a list` (`loader.py:1144-1163`). The dir and the root are **mutually exclusive**, not merged. A world that ships `visual_tokens`-only files in `cultures/` and keeps its name-gen cultures in the root `cultures.yaml` loads **zero** name-gen cultures (this was glenross's silent bug, fixed 2026-06-09 by moving its 6 cultures into `cultures/*_names.yaml`). |
| 🚫 **NOT read** | exists on disk, loader never opens it |

**Files that are NEVER read at runtime (project-wide):**
- All markdown: `combat_design.md`, `magic_design.md`, `CAMPAIGN_NOTES.md`, `players-guide.md`, `README.md`
- `*.draft` / `*.yaml.draft`, `premises.draft.yaml` (only `premises.yaml` is read)
- **`power_tiers.yaml`, `projection.yaml` at the WORLD level** — read **only at genre level** (`load_genre_pack`, loader.py:1673 / 1947). World copies are dead.
- ⚠ **CORRECTION (2026-06-09):** **`inventory.yaml` at the WORLD level IS read.** An
  earlier revision of this doc listed it as genre-only/dead; that is wrong. Epic 94
  added a world-tier read in `_load_single_world` (loader.py:1479) with **world-first
  resolution** (`server.dispatch.inventory_resolve.resolve_inventory`), and the load
  emits a `world_inventory` `state_transition` watcher event. Verified by loading
  coyote_star (`credits` currency, 16 catalog items). The 13 world `inventory.yaml`
  files are live, intended per-world catalogs (ADR-140) — the 🚫 `inventory (dead)`
  marks on the per-genre diagrams below are **stale** and should be read as "world
  inventory loads, world-first."

---

## 1. caverns_and_claudes

```mermaid
flowchart LR
    G["<b>GENRE caverns_and_claudes</b><br/>req: pack·rules·progression·axes·prompts·visibility_baseline·lethality_policy<br/>opt: theme·archetypes·char_creation·visual_style·audio·cultures·tropes·power_tiers·<br/>beat_vocabulary·inventory·backstory_tables·equipment_tables·classes·archetype_constraints·projection·client_theme·magic"]
    W1["<b>beneath_sunden</b><br/>override: archetypes·visual_style·tropes·bestiary·lore · cultures/ · legends/<br/>world-only: world·cartography·openings·history·portrait_manifest<br/>(+ cookbook/ corpus/ rooms/ dirs — caverns-specific)"]
    G -->|inherit defaults, then override| W1
    classDef g fill:#1e3a5f,stroke:#4a90d9,color:#fff
    classDef w fill:#3d2f1e,stroke:#d9a04a,color:#fff
    class G g
    class W1 w
```

---

## 2. elemental_harmony

```mermaid
flowchart LR
    G["<b>GENRE elemental_harmony</b><br/>req: pack·rules·progression·axes·prompts·visibility_baseline·lethality_policy<br/>opt: theme·archetypes·audio·tropes·classes·archetype_constraints·client_theme·spells_wwn·<b>power_tiers</b> ✅<br/>(power_tiers added at genre 2026-06-09 — was the only genre missing it; no genre magic.yaml)"]
    W1["<b>burning_peace</b><br/>override: archetypes·visual_style·tropes·char_creation·bestiary·lore · cultures/ · legends/<br/>world-only: world·cartography·openings·history·archetype_funnels·portrait_manifest<br/>(inventory loads world-first; power_tiers moved to genre 2026-06-09; stale root cultures.yaml deleted)"]
    W2["<b>shattered_accord</b><br/>override: archetypes·visual_style·tropes·char_creation·bestiary·lore · cultures/ · legends/<br/>world-only: world·cartography·openings·history·archetype_funnels·portrait_manifest<br/>🚫 inventory (dead)"]
    G --> W1
    G --> W2
    classDef g fill:#1e3a5f,stroke:#4a90d9,color:#fff
    classDef w fill:#3d2f1e,stroke:#d9a04a,color:#fff
    class G g
    class W1,W2 w
```

---

## 3. heavy_metal

```mermaid
flowchart LR
    G["<b>GENRE heavy_metal</b><br/>req: pack·rules·progression·axes·prompts·visibility_baseline·lethality_policy<br/>opt: theme·audio·power_tiers·beat_vocabulary·classes·archetype_constraints·projection·client_theme·spells_wwn<br/>⚠ no genre archetypes/tropes/visual_style — worlds supply them"]
    W1["<b>barsoom</b><br/>override: archetypes·visual_style·audio·tropes·char_creation·bestiary·lore · cultures/ · legends/<br/>world-only: world·cartography·openings·history·npcs·items·portrait_manifest<br/>🚫 inventory (dead)"]
    W2["<b>evropi</b><br/>override: archetypes·visual_style·tropes·char_creation·bestiary·lore · cultures/ · legends/<br/>world-only: world·cartography·openings·history·archetype_funnels·portrait_manifest<br/>🚫 inventory (dead); + _drafts/ dir"]
    W3["<b>long_foundry</b><br/>override: archetypes·visual_style·tropes·char_creation·<b>magic(COMPOSE)</b>·bestiary·lore · cultures/ · legends/<br/>world-only: world·cartography·openings·history·archetype_funnels·portrait_manifest<br/>🚫 inventory (dead)"]
    G --> W1
    G --> W2
    G --> W3
    classDef g fill:#1e3a5f,stroke:#4a90d9,color:#fff
    classDef w fill:#3d2f1e,stroke:#d9a04a,color:#fff
    class G g
    class W1,W2,W3 w
```

---

## 4. mutant_wasteland

```mermaid
flowchart LR
    G["<b>GENRE mutant_wasteland</b><br/>req: pack·rules·progression·axes·prompts·visibility_baseline·lethality_policy<br/>opt: theme·archetypes·char_creation·visual_style·audio·cultures·tropes·achievements·<br/>power_tiers·pacing·inventory·bestiary·projection·client_theme·magic"]
    W1["<b>flickering_reach</b><br/>override: archetypes·visual_style·tropes·bestiary·lore · cultures/ · legends/<br/>world-only: world·cartography·openings·history·portrait_manifest"]
    G --> W1
    classDef g fill:#1e3a5f,stroke:#4a90d9,color:#fff
    classDef w fill:#3d2f1e,stroke:#d9a04a,color:#fff
    class G g
    class W1 w
```

---

## 5. neon_dystopia

```mermaid
flowchart LR
    G["<b>GENRE neon_dystopia</b><br/>req: pack·rules·progression·axes·prompts·visibility_baseline·lethality_policy<br/>opt: theme·archetypes·char_creation·visual_style·audio·cultures·tropes·achievements·<br/>power_tiers·inventory·archetype_constraints·bestiary·client_theme<br/>🚫 combat_design.md · magic_design.md (docs, never read)"]
    W1["<b>franchise_nations</b><br/>override: archetypes·visual_style·tropes·bestiary·lore · cultures/ · legends/<br/>world-only: world·cartography·openings·history·portrait_manifest"]
    G --> W1
    classDef g fill:#1e3a5f,stroke:#4a90d9,color:#fff
    classDef w fill:#3d2f1e,stroke:#d9a04a,color:#fff
    classDef d fill:#4a1e1e,stroke:#d94a4a,color:#fff
    class G g
    class W1 w
```

---

## 6. pulp_noir

```mermaid
flowchart LR
    G["<b>GENRE pulp_noir</b><br/>req: pack·rules·progression·axes·prompts·visibility_baseline·lethality_policy<br/>opt: theme·archetypes·char_creation·visual_style·audio·cultures·tropes·achievements·<br/>power_tiers·inventory·archetype_constraints·client_theme<br/>🚫 combat_design.md · magic_design.md (docs, never read)"]
    W1["<b>annees_folles</b><br/>override: archetypes·visual_style·tropes·bestiary·lore · cultures/ · legends/ · <b>scenarios/</b><br/>world-only: world·cartography·openings·history·portrait_manifest"]
    G --> W1
    classDef g fill:#1e3a5f,stroke:#4a90d9,color:#fff
    classDef w fill:#3d2f1e,stroke:#d9a04a,color:#fff
    class G g
    class W1 w
```

---

## 7. road_warrior

```mermaid
flowchart LR
    G["<b>GENRE road_warrior</b><br/>req: pack·rules·progression·axes·prompts·visibility_baseline·lethality_policy<br/>opt: theme·archetypes·char_creation·visual_style·audio·cultures·tropes·achievements·<br/>power_tiers·beat_vocabulary·inventory·classes·projection·client_theme·magic<br/>🚫 combat_design.md (doc, never read)"]
    W1["<b>the_circuit</b><br/>override: archetypes·visual_style·tropes·bestiary·lore · cultures/ · legends/<br/>world-only: world·cartography·openings·history·npcs·portrait_manifest<br/>(note: rigs/chassis_classes live at genre, not this world)"]
    G --> W1
    classDef g fill:#1e3a5f,stroke:#4a90d9,color:#fff
    classDef w fill:#3d2f1e,stroke:#d9a04a,color:#fff
    class G g
    class W1 w
```

---

## 8. space_opera  *(richest — magic compose, rigs, orbital tier)*

```mermaid
flowchart LR
    G["<b>GENRE space_opera</b><br/>req: pack·rules·progression·axes·prompts·visibility_baseline·lethality_policy<br/>opt: theme·archetypes·audio·power_tiers·classes·archetype_constraints·projection·client_theme·magic<br/>🚫 combat_design.md · magic_design.md (docs, never read)"]
    W1["<b>aureate_span</b><br/>override: archetypes·visual_style·tropes·char_creation·bestiary·lore · cultures/ · legends/<br/>world-only: world·cartography·openings·history·npcs·archetype_funnels·portrait_manifest<br/>🚫 inventory (dead)"]
    W2["<b>coyote_star</b> ⭐ fullest<br/>override: archetypes·visual_style·tropes·char_creation·<b>magic(COMPOSE)</b>·bestiary·<b>chassis_classes</b>·lore · cultures/ · legends/<br/>world-only: world·cartography·openings·history·npcs·archetype_funnels·<b>rigs·orbits·chart</b>·portrait_manifest<br/>🚫 inventory (dead)"]
    W3["<b>perseus_cloud</b> (Jade's world)<br/>override: archetypes·visual_style·tropes·char_creation·bestiary·lore · cultures/ · legends/ ✅<br/>world-only: world·cartography·openings·history·npcs·portrait_manifest·<b>orbits</b><br/>(inventory loads world-first; legends/ added 2026-06-09 — 3 legends)"]
    G --> W1
    G --> W2
    G --> W3
    classDef g fill:#1e3a5f,stroke:#4a90d9,color:#fff
    classDef w fill:#3d2f1e,stroke:#d9a04a,color:#fff
    class G g
    class W1,W2,W3 w
```

---

## 9. spaghetti_western

```mermaid
flowchart LR
    G["<b>GENRE spaghetti_western</b><br/>req: pack·rules·progression·axes·prompts·visibility_baseline·lethality_policy<br/>opt: theme·visual_style·audio·achievements·power_tiers·classes·projection·client_theme·magic<br/>⚠ no genre archetypes/tropes/char_creation — worlds supply them"]
    W1["<b>dust_and_lead</b><br/>override: archetypes·visual_style·tropes·char_creation·bestiary·lore · cultures/ · legends/<br/>world-only: world·cartography·openings·history·portrait_manifest·<b>calendar</b><br/>🚫 inventory (dead)"]
    W2["<b>five_points</b><br/>override: archetypes·visual_style·audio·tropes·char_creation·bestiary·lore · cultures/ · legends/<br/>world-only: world·cartography·openings·history·npcs·archetype_funnels·portrait_manifest<br/>🚫 inventory (dead)"]
    W3["<b>the_real_mccoy</b><br/>override: archetypes·visual_style·audio·tropes·char_creation·bestiary·lore · cultures/ · legends/<br/>world-only: world·cartography·openings·history·npcs·portrait_manifest·<b>calendar</b><br/>🚫 inventory (dead)"]
    G --> W1
    G --> W2
    G --> W3
    classDef g fill:#1e3a5f,stroke:#4a90d9,color:#fff
    classDef w fill:#3d2f1e,stroke:#d9a04a,color:#fff
    class G g
    class W1,W2,W3 w
```

---

## 10. tea_and_murder  *(mystery — scenarios/ everywhere)*

```mermaid
flowchart LR
    G["<b>GENRE tea_and_murder</b><br/>req: pack·rules·progression·axes·prompts·visibility_baseline·lethality_policy<br/>opt: theme·visual_style·audio·tropes·achievements·power_tiers·beat_vocabulary·<br/>inventory·equipment_tables·client_theme·magic<br/>⚠ no genre archetypes/char_creation/classes — worlds supply them"]
    W1["<b>blackthorn_moor</b> (draft)<br/>override: archetypes·visual_style·tropes·char_creation·bestiary·classes·cultures·lore · cultures/ · legends/ · <b>scenarios/</b><br/>world-only: world·cartography·openings·history·npcs·portrait_manifest<br/>🚫 inventory (dead)"]
    W2["<b>glenross</b><br/>override: archetypes·visual_style·tropes·char_creation·bestiary·classes·seed_tropes·cultures·lore · cultures/ · legends/ · <b>scenarios/</b><br/>world-only: world·cartography·openings·history·npcs·portrait_manifest·<b>calendar</b><br/>🚫 inventory (dead)"]
    G --> W1
    G --> W2
    classDef g fill:#1e3a5f,stroke:#4a90d9,color:#fff
    classDef w fill:#3d2f1e,stroke:#d9a04a,color:#fff
    class G g
    class W1,W2 w
```

---

## 11. wry_whimsy  *(portal-fairytale — premises substrate)*

```mermaid
flowchart LR
    G["<b>GENRE wry_whimsy</b><br/>req: pack·rules·progression·axes·prompts·visibility_baseline·lethality_policy<br/>opt: theme·archetypes·char_creation·audio·tropes·seed_tropes·achievements·power_tiers·<br/>beat_vocabulary·inventory·classes·archetype_constraints·<b>witnessed_acts</b>·client_theme<br/>⚠ no genre visual_style — worlds supply it"]
    W1["<b>gulliver</b><br/>override: archetypes·visual_style·tropes·bestiary·lore · cultures/ · legends/<br/>world-only: world·cartography·openings·history·npcs·archetype_funnels·portrait_manifest"]
    W2["<b>oz</b><br/>override: archetypes·visual_style·tropes·bestiary·lore · cultures/ · legends/<br/>world-only: world·cartography·openings·history·npcs·archetype_funnels·portrait_manifest·<b>premises</b>"]
    W3["<b>wonderland</b><br/>override: archetypes·visual_style·tropes·bestiary·lore · cultures/ · legends/<br/>world-only: world·cartography·openings·history·npcs·archetype_funnels·portrait_manifest"]
    G --> W1
    G --> W2
    G --> W3
    classDef g fill:#1e3a5f,stroke:#4a90d9,color:#fff
    classDef w fill:#3d2f1e,stroke:#d9a04a,color:#fff
    class G g
    class W1,W2,W3 w
```

---

## Cross-genre runtime findings

1. ⚠ **CORRECTED.** ~~`inventory.yaml` ... every world copy is dead.~~ **World-level
   `inventory.yaml` IS loaded** (epic 94, `_load_single_world` loader.py:1479) and
   resolved **world-first** — the 13 world copies are live, intended per-world economies/
   catalogs (ADR-140). The genuinely-dead world files are the singleton world-level
   `power_tiers.yaml` and `projection.yaml` (both read only by `load_genre_pack`,
   loader.py:1673 / 1947). The one shipped world `power_tiers.yaml` (burning_peace) was
   a misfiled *genre* file and was moved to `elemental_harmony/power_tiers.yaml`
   (2026-06-09).
2. **`premises.draft.yaml` is never read** — only `premises.yaml` (gulliver/wonderland ship the draft name; oz ships the real one and is the only world whose premises actually load).
3. ~~**`legends/` missing from perseus_cloud only**~~ ✅ **RESOLVED (2026-06-09):** 3
   legends authored for perseus_cloud (`the_last_lane`, `the_coelitha_survey`,
   `the_lazzaro_compact`), inferred from the world's own history/lore; all parse and
   their `terrain_scars` regions validate against `cartography.yaml`. All 21 worlds now
   load a legends dir.
4. **`magic.yaml` composition is live in exactly 2 worlds:** long_foundry and coyote_star (world magic composes over genre magic). Other genres ship a genre `magic.yaml` that loads with no world override.
5. **Orbital tier (orbits.yaml + chart.yaml) only in space_opera** — coyote_star (both) and perseus_cloud (orbits only). chart.yaml is coyote_star-exclusive.
6. **`*_design.md` never reach the engine** — `combat_design.md` (neon, pulp, road_warrior, space_opera) and `magic_design.md` (neon, pulp, space_opera) are pure docs.
7. **Genres relying on worlds for core content:** heavy_metal, spaghetti_western, space_opera, tea_and_murder, wry_whimsy each omit some of archetypes/tropes/visual_style/char_creation at genre level, requiring every world to supply them (no genre fallback → a new world that forgets them gets nothing).
