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
| **globbed dirs** | `cultures/`, `legends/`, `scenarios/` scanned as directories (`loader.py:1118,1139,1326`); `.gitkeep`/`_meta.yaml` skipped |
| 🚫 **NOT read** | exists on disk, loader never opens it |

**Files that are NEVER read at runtime (project-wide):**
- All markdown: `combat_design.md`, `magic_design.md`, `CAMPAIGN_NOTES.md`, `players-guide.md`, `README.md`
- `*.draft` / `*.yaml.draft`, `premises.draft.yaml` (only `premises.yaml` is read)
- **`inventory.yaml`, `power_tiers.yaml`, `projection.yaml` at the WORLD level** — these are read **only at genre level** (`loader.py:1647,1622,1897`). World copies are dead.

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
    G["<b>GENRE elemental_harmony</b><br/>req: pack·rules·progression·axes·prompts·visibility_baseline·lethality_policy<br/>opt: theme·archetypes·audio·tropes·classes·archetype_constraints·client_theme·spells_wwn<br/>⚠ no power_tiers (only genre missing it); no genre magic.yaml"]
    W1["<b>burning_peace</b><br/>override: archetypes·visual_style·tropes·char_creation·bestiary·cultures·lore · cultures/ · legends/<br/>world-only: world·cartography·openings·history·archetype_funnels·portrait_manifest<br/>🚫 inventory·power_tiers·projection (world copies dead)"]
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
    W3["<b>perseus_cloud</b> (Jade's world)<br/>override: archetypes·visual_style·tropes·char_creation·bestiary·lore · cultures/<br/>world-only: world·cartography·openings·history·npcs·portrait_manifest·<b>orbits</b><br/>🚫 inventory (dead); ⚠ no legends/ dir (only world missing it)"]
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

1. **Dead world files (exist, never loaded):** `inventory.yaml` ships in 13 worlds but is read **only at genre level** — every world copy is dead. Same for the singleton world-level `power_tiers.yaml` and `projection.yaml` (both genre-only loaders). If a world wants custom loadout/economy it must do it at genre tier or via a different mechanism.
2. **`premises.draft.yaml` is never read** — only `premises.yaml` (gulliver/wonderland ship the draft name; oz ships the real one and is the only world whose premises actually load).
3. **`legends/` missing from perseus_cloud only** — every other world loads a legends dir; perseus_cloud silently has none.
4. **`magic.yaml` composition is live in exactly 2 worlds:** long_foundry and coyote_star (world magic composes over genre magic). Other genres ship a genre `magic.yaml` that loads with no world override.
5. **Orbital tier (orbits.yaml + chart.yaml) only in space_opera** — coyote_star (both) and perseus_cloud (orbits only). chart.yaml is coyote_star-exclusive.
6. **`*_design.md` never reach the engine** — `combat_design.md` (neon, pulp, road_warrior, space_opera) and `magic_design.md` (neon, pulp, space_opera) are pure docs.
7. **Genres relying on worlds for core content:** heavy_metal, spaghetti_western, space_opera, tea_and_murder, wry_whimsy each omit some of archetypes/tropes/visual_style/char_creation at genre level, requiring every world to supply them (no genre fallback → a new world that forgets them gets nothing).
