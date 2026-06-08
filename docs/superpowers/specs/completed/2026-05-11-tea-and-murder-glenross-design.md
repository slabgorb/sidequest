# Tea & Murder — `victoria` genre rebrand + new Glenross world

**Date:** 2026-05-11
**Status:** Approved, in authoring
**Audience driver:** Sonia (Keith's partner) and Mandy (Keith's mother). Both new to SideQuest; low cognitive load required; warmth-forward; cosy genre; spoilable world (override of the standard unspoiled policy).
**Spoiler protection:** `tea_and_murder/glenross` is **spoilable** for this design cycle, like `mutant_wasteland/flickering_reach`.

## Summary

Rebrand the existing `victoria` genre from Brontë-gothic / drawing-room-intrigue to **Tea & Murder** — cosy Edwardian (1901-1914) English-language murder mystery in the BritBox register. Author a fresh world `glenross`, a fictional Highland village, as the new flagship world. The existing workshop world `blackthorn_moor` stays in workshop; gothic content does not migrate.

## Genre rebrand

| Aspect | Before (`victoria`) | After (`tea_and_murder`) |
|---|---|---|
| Display name | Victoria | Tea & Murder |
| Era | 1840s-1880s | 1901-1914 (Edwardian, pre-Great-War, pre-1926 music copyright cutoff) |
| Register | Gothic / drawing-room / dread | Cosy / village / puzzle |
| Inspirations | Brontë, Bridgerton, Holmes, Wilkie Collins, James, Gaskell, Dickens | Father Brown (early Chesterton, pre-WWI), Christie pre-war stories, All Creatures Great and Small (moved earlier), Midsomer Murders (structure), Hamish Macbeth (Highland setting) |
| Magic | Tunable innate occult | Off by default at world level; chassis remains for future worlds |
| Tonal axes | gothic / romance / intrigue | cosy / puzzle / gossip / gothic (last near zero in cosy worlds) |
| Lethality | Low — social death > actual | Low — social death > actual; victims always off-camera, never the recurring cast |

### Directory name decision

The genre directory **stays `victoria/`** for this design cycle. The display name `Tea & Murder` lives in `pack.yaml`. A directory rename to `tea_and_murder/` is a separate Dev task because it touches:

- `sidequest-server/sidequest/server/session.py`, `session_room.py`, `narration_apply.py`, `game/builder.py`, `genre/loader.py` (comments + conditionals)
- `sidequest-ui/src/dice/InlineDiceTray.tsx`, test fixtures using `genre: "victoria"`
- Save-file migration (existing `victoria_*.db` saves)

GM agent doesn't edit code; that work is filed via pingpong (see Task #7).

## Glenross — the new world

### High concept

Fictional Highland village in a fictional glen, c. 1908. Stone cottages, slate roofs, the river *Allt Ross* running through, the great house *Castle Ross* on the rise. Single road in, single railway halt out. Large enough to support a minister, a doctor, a school, a post office, and one inn — small enough that everyone knows everyone's business by sundown. The Episcopal rector at St. Margaret's holds the Father-Brown-coded outsider-clergyman slot without invoking Catholic/Protestant sectarian baggage (Scottish Episcopal Church is the Anglican Communion's branch in Scotland, small congregation in the glen).

### POIs (13)

| POI | Anchor | Notes |
|---|---|---|
| The Manse | Rev. Andrew Murchison (CofS minister) | Widower, beekeeper, observant in the quiet way ministers learn to be |
| St. Margaret's Chapel | Rev. Alistair Quill (Scottish Episcopal rector) | Outsider clergyman; the village's most reliably underestimated mind; Father-Brown-coded |
| The Surgery | Dr. Eilidh Ross (GP) | Distantly related to the laird; telephone (one of two in the village) |
| The Post Office | Mrs. Catriona Buchan (postmistress) | Telegraph operator; knows everything before anyone else |
| The School | Miss Margaret Ferguson (schoolmistress) | Has taught every adult under forty |
| The Glenross Arms | Hamish Sinclair (publican) | Three rooms upstairs for visitors |
| The Shinty Pitch & Cricket Field | — | Glenross plays both; rivalry vs Cullenmore is the social fixture of summer |
| Glenross Halt | Stationmaster Albert MacGregor | Single platform; two trains a day to Inverness |
| Castle Ross / Glenross Lodge | Sir Iain & Lady Annabel Ross, Hugo Ross (son) | The laird's seat; village's largest single employer |
| Kirk of St. Maelrubha | — | Norman-Scoto-medieval church on its mound, kirkyard sloping to the burn |
| Mrs. Cameron's Tea Rooms | Mrs. Cameron | The gossip hub that isn't the Post Office |
| The Distillery | Donald Munro (distiller) | Village's economic anchor; Munros have run it three generations |
| The Bridge / Old Drove Road / Long Pass | — | Outdoor settings for body-discovery, chase beats, the storm night |

### Recurring cast (12)

Authored with voice + OCEAN + named relationships to at least three others. None of these ever get murdered — the Sonia-and-Mandy rule. Victims are visitors, awful relatives, blackmailers, distillery rivals, villagers whose secret was about to surface.

1. Rev. Andrew Murchison (CofS minister)
2. Rev. Alistair Quill (Scottish Episcopal rector)
3. Dr. Eilidh Ross (GP)
4. Mrs. Catriona Buchan (postmistress)
5. Miss Margaret Ferguson (schoolmistress)
6. Hamish Sinclair (publican)
7. Sir Iain Ross of Glenross (laird)
8. Lady Annabel Ross
9. Hugo Ross (their son — London-educated, restless)
10. Sergeant Findlay MacRae (village constable)
11. Mrs. Cameron (tea rooms)
12. Donald Munro (distiller)

Plus rotating peripherals across sessions: the doctor's locum, a visiting Aunt up from Edinburgh, the laird's gillie Old Tam, the new schoolmistress's brother on extended leave from the regiment.

## PC day-job archetypes (8)

Each amateur-sleuth-coded; day job opens doors; one "professional courtesy" gives each archetype a mechanical hook.

| Archetype | Professional courtesy | What they notice first | Reference |
|---|---|---|---|
| Country Doctor | Enters any house at any hour without question | Bodies, hands, faces, illness as character tell | Watson, Doc Martin |
| Church of Scotland Minister | Pastoral visit to any household, any class | What people fear to say in their own home | Murchison register |
| Scottish Episcopal Rector | Discreet confession; small congregation includes the laird's family | Patterns of guilt, the shape of motive | Father Brown literal |
| Postmistress | Reads every address; handles every telegram; sees frequencies | Sudden change in correspondence; sudden frugality | Miss Marple |
| Schoolmistress | Children tell her things they tell no one else | What a child is suddenly afraid of, suddenly knows | Cranford |
| Veterinary Surgeon | Practice covers every farm and sporting estate in the glen | Estates as social maps; animal cruelty as character tell | Herriot |
| Village Constable | Official authority but utterly dependent on village cooperation | Who lies first, who lies most carefully | Hamish Macbeth |
| Retired Colonial Officer | Half-pay, building a cottage, restless | Strangers, weapons, men who don't move like civilians | Christie's Colonel Race |

## Chargen — three Glenross-flavored scenes

**Scene 1 — "How Do You Come to Glenross?"** (origins / class)
Old Family of the Glen · The Manse or the Surgery · Trade or Distillery · The Village · From Down South · From Away

**Scene 2 — "What Is Your Vocation?"** (the day-job — pick one of the eight above)

**Scene 3 — "What Do You Always Notice?"** (the crucible — the detective trait)
What's out of place · What isn't said · The children · The money · The room before the people · I won't let it go

## Mystery cadence & tonal axes

**Structure: episodic.** One mystery per session, resolved cleanly. Body discovered in turn 1-2; solve lands by turn 10-12. No carryover mystery debt across sessions.

**Cast continuity:** recurring NPCs evolve across sessions (new curate joins the cast; Hugo Ross drifts toward romance with Dr. Ross; the schoolmistress takes in her invalid sister) — but mysteries are clean per-session units.

**The Tea Cup Test** (the cosy/grim dial):
- Body discovery off-stage or tidy (slumped at desk, fallen in the burn, found in the rose garden by the gardener)
- Forensic moments named, not narrated
- Children, animals, recurring cast — never harmed (hard rule)
- Victim is outsider / awful relative / blackmailer / villager-with-secret

**Axes:**
- `cosy` default 0.7 — warmth and forgiveness of the village register
- `puzzle` default 0.7 — narrator foregrounds mystery-as-puzzle
- `gossip` default 0.5 — social information flow drives the plot
- `gothic` default 0.1 — reserved for storm night / burnt shieling / the Old Drove Road

## Music & visual

**Music (pre-1926 public domain):**
- Hamish MacCunn (d. 1916) — *Land of the Mountain and the Flood*, *The Ship o' the Fiend*
- Mendelssohn — *Hebrides Overture (Fingal's Cave)*
- Marjory Kennedy-Fraser — *Songs of the Hebrides* (collected 1909/1917)
- Traditional: *Skye Boat Song*, *Loch Lomond*, *Mhairi's Wedding*, Burns settings
- Scott Joplin ragtime (PD) for the tea rooms
- Elgar pre-1914 *Salut d'amour*, *Chanson de Matin*
- Sullivan light orchestral, Saint-Saëns, Satie *Gymnopédies*
- Existing Chopin tracks retained — fit cosy register fine

**Visual style:**
- Sunlit watercolor; heather purple, bracken, stone grey, brass-and-cream tea-room palette
- Daylight and golden hour primary; gaslit-night-rain reserved for tonal escalation only
- Stone cottages with slate roofs and smoking chimneys; the kirk on its mound; the big house in Highland baronial style
- Edwardian costume: high collars, ankle-length skirts, straw boaters, tea-gowns, motoring veils; tweeds and kilts for sporting / festival contexts

## Cultures & naming

Genre keeps five existing cultures (English Gentry, London Professional, Servant Class, Industrial North, Colonial). **Add one:**

**Highland Scots** — Gaelic-influenced naming. Family names: Ross, Munro, MacRae, Buchan, Ferguson, Sinclair, MacGregor, Cameron, Murchison, Murray, Fraser, MacKay, Stewart, Sutherland, Quill, Cattanach. Given names: Iain, Eilidh, Catriona, Margaret, Hamish, Andrew, Donald, Findlay, Alistair, Annabel, Hugo, Morag, Aileen, Calum, Effie, Tam, Magnus, Iona.

Corpus files added under `genre_packs/victoria/corpus/`: `highland_scots_first.txt`, `highland_scots_family.txt`.

## File plan

### Genre-tier edits (`sidequest-content/genre_packs/victoria/`)

| File | Action |
|---|---|
| `pack.yaml` | Rewrite — name, description, lobby_blurb, inspirations, era, vibe |
| `axes.yaml` | Rewrite — cosy/puzzle/gossip/gothic |
| `prompts.yaml` | Rewrite — warm/observant narrator register |
| `theme.yaml` + `client_theme.css` | Rewrite — sunlit watercolor palette |
| `beat_vocabulary.yaml` | Rewrite — cosy beats |
| `tropes.yaml` | Rewrite — cosy trope roster |
| `archetypes.yaml` | Rewrite roster to 8 day-job sleuths |
| `char_creation.yaml` | Rewrite — 3-scene Glenross-flavored chargen |
| `audio.yaml` | Extend — keep Chopin, add Highland + parlour PD |
| `magic.yaml` | Tweak — disabled by default at world level |
| `cultures.yaml` | Append — add Highland Scots |
| `corpus/highland_scots_first.txt` | New |
| `corpus/highland_scots_family.txt` | New |
| `lethality_policy.yaml`, `progression.yaml`, `inventory.yaml`, `power_tiers.yaml`, `visibility_baseline.yaml`, `rules.yaml` | Light or no edits |
| `history.yaml`, `cartography.yaml` (genre-tier) | Remove or ignore — unused at genre tier in current schema |

### World-tier — new (`sidequest-content/genre_packs/victoria/worlds/glenross/`)

All required: `world.yaml`, `lore.yaml`, `cartography.yaml`, `cultures.yaml` (notes-only), `legends.yaml`, `tropes.yaml`, `archetypes.yaml`, `visual_style.yaml`, `history.yaml`, `portrait_manifest.yaml`, `char_creation.yaml`, `npcs.yaml`, **`openings.yaml`** (load-blocker).

## Validation

Spec is complete when `load_genre_pack(genre_packs/victoria)` returns a `GenrePack` with `worlds['glenross']` populated, ≥1 solo opening per day-job archetype, ≥1 MP opening, all NPC cross-refs resolving, and no schema errors. Verified via Python repl test (Task #6).

## Out of scope (deferred)

- Directory rename `victoria/` → `tea_and_murder/` (Dev pingpong — Task #7)
- POI image generation for Glenross (separate `/sq-poi` run after first playable smoke test)
- Highland music track uploads to R2 (separate music-director run)
- A second cosy world (Loamshire, Combe Severn, etc.) — single village suffices for v1
- Returning Brontë-gothic register as separate genre `bronte_gothic/` — workshop content preserved for that future possibility
- `blackthorn_moor` migration to live — stays in workshop

## Open question (low-stakes, can resolve at authoring time)

The new Highland Scots culture in `cultures.yaml` and the new corpus files mean any character generated in the genre — including in any future non-Glenross world — can draw Highland names. This is fine for Glenross but slightly noisy for the original Victorian-English register. If a `bronte_gothic` genre is later spun off, the Highland Scots culture moves with `tea_and_murder` and is removed from any English-only sibling. Not a blocker today.
