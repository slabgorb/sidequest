# Genre → World File Inheritance

How content resolves per ADR-121 (layered content resolution / per-field merge) and
ADR-140 (genre is the rulebook; the world owns the cast & catalog). The genre pack
supplies defaults; the world overrides per-field; the engine loads the merged result.

Three buckets:
- **Override pairs** — file exists at both levels; world merges over genre (the real inheritance surface).
- **Genre-only** — the rulebook; never overridden by worlds.
- **World-only** — per-world cast & catalog; no genre base.

```mermaid
flowchart TD
    subgraph GENRE["🎲 GENRE PACK LAYER — the rulebook (defaults)"]
        direction TB
        G_ONLY["<b>Genre-only (no world override)</b><br/>rules · prompts · theme · axes<br/>progression · lethality_policy<br/>visibility_baseline · pack · client_theme.css<br/>achievements · archetype_constraints<br/>beat_vocabulary · combat_design.md · magic_design.md"]
        G_SHARED["<b>Overridable defaults</b><br/>archetypes · tropes · visual_style<br/>magic · classes · cultures · audio<br/>char_creation · inventory · openings<br/>projection · power_tiers · bestiary · seed_tropes"]
    end

    subgraph WORLD["🌍 WORLD LAYER — the cast & catalog"]
        direction TB
        W_OVERRIDE["<b>World overrides (merge onto genre)</b><br/>archetypes · tropes · visual_style<br/>magic · classes · cultures · audio<br/>char_creation · inventory · openings<br/>projection · power_tiers · bestiary"]
        W_ONLY["<b>World-only (no genre base)</b><br/>world · lore · history · cartography<br/>portrait_manifest · npcs · archetype_funnels<br/>calendar · orbits · premises · world_register<br/>cultures/ · legends/ · assets/ · scenarios/"]
        W_STRAY["<b>One-offs / drift</b><br/>rigs · chassis_classes · items · inventions<br/>faction_agendas · encounter_tables · confrontations<br/>magic.yaml.draft · CAMPAIGN_NOTES.md · players-guide.md"]
    end

    RESOLVED["⚙️ RESOLVED CONFIG<br/>(per-field merge: world wins, else genre default)"]

    G_SHARED -->|"inherited as default"| W_OVERRIDE
    G_SHARED -.->|"used as-is when world omits"| RESOLVED
    G_ONLY -->|"always from genre"| RESOLVED
    W_OVERRIDE -->|"per-field override"| RESOLVED
    W_ONLY -->|"world-supplied only"| RESOLVED
    W_STRAY -.->|"non-standard, may not load"| RESOLVED

    classDef genre fill:#1e3a5f,stroke:#4a90d9,color:#fff
    classDef world fill:#3d2f1e,stroke:#d9a04a,color:#fff
    classDef stray fill:#4a1e1e,stroke:#d94a4a,color:#fff
    classDef resolved fill:#1e4a2f,stroke:#4ad97a,color:#fff
    class G_ONLY,G_SHARED genre
    class W_OVERRIDE,W_ONLY world
    class W_STRAY stray
    class RESOLVED resolved
```

## Override pairs (the inheritance surface)

These files exist at both genre and world level: `archetypes`, `tropes`, `visual_style`,
`magic`, `classes`, `cultures`, `audio`, `char_creation`, `inventory`, `openings`,
`projection`, `power_tiers`, `bestiary`, `seed_tropes`.

> ⚠ **Correction (2026-06-09) — "merges over" is too simple; the strategy differs per file.**
> Verified against the live loader (`sidequest-server/sidequest/genre/loader.py`). The
> resolution is **not** uniform per-field merge. Real behavior:
>
> - **REPLACE (world list wins wholesale):** `archetypes`, `cultures`, `bestiary`,
>   `char_creation`, `classes`, `spells_wwn`, `chassis_classes`, `seed_tropes`.
> - **AUTHORITATIVE (world value wins, genre is fallback):** `theme`, `audio`,
>   `visual_style`, `lore`, `tropes`.
> - **COMPOSE (per-field last-writer + `hard_limits` append):** `magic.yaml` only.
> - **`inventory` → world-first resolve:** world `inventory.yaml` loads (epic 94) and is
>   resolved ahead of the genre default. *Live, not dead.*
> - **`power_tiers`, `projection` → genre-only:** read **only** by `load_genre_pack`
>   (loader.py:1673 / 1947). **World-level copies are never read** — do not treat these as
>   a world override surface. (The one world `power_tiers.yaml` that shipped, in
>   burning_peace, was a misfiled genre file and was moved to the genre level.)
> - **`cultures` is dir-shadows-root, not a merge:** the loader reads the `cultures/`
>   **directory** if present, **else** the root `cultures.yaml` — they are mutually
>   exclusive. Files in `cultures/` without a `name:` key are art-pipeline `visual_tokens`
>   overlays and are skipped for name generation. A world that puts only overlays in
>   `cultures/` while leaving its name-gen cultures in the (now-shadowed) root loads zero
>   name-gen cultures (glenross's bug, fixed 2026-06-09).
>
> So the `W_OVERRIDE`/`G_SHARED` boxes in the flowchart above are a useful first
> approximation, but `power_tiers` and `projection` belong with the **genre-only** set,
> and `cultures` resolution is shadow-not-merge.
