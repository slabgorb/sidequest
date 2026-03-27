# Playtest Script — Flickering Reach (mutant_wasteland)

**Genre:** Mutant Wasteland
**World:** The Flickering Reach
**Spoiler status:** FULLY SPOILABLE for testing purposes

This is a structured checklist for exercising SideQuest features during a playtest session. Work through the sections in order. Each item has a verification step — check it off when the expected behavior occurs.

---

## 1. Connection & Setup

- [ ] **Start the stack**
  - `just api-run` (Rust API server)
  - `just daemon-run` (Python media daemon)
  - `just ui-dev` (React client)
- [ ] **Connect to server** — ConnectScreen loads, genre dropdown populates from /api/genres
- [ ] **Select genre** — Choose "Mutant Wasteland" from dropdown
- [ ] **Select world** — Choose "The Flickering Reach"
- [ ] **Enter player name**
- [ ] **Verify:** WebSocket connects, status shows connected

## 2. Character Creation

- [ ] **Origins scene** — "Where You Woke Up" appears with 5 origin choices + freeform input
  - Try "The Heaps" (Scrapborn flavor, max faction integration) or "A Sealed Vault" (Vaultborn, outsider perspective)
- [ ] **Mutation scene** — "What Makes You Different" — 6 mutation choices
  - Try "Psychic Static" for narrative richness (hear whispers from nearby minds)
  - Or "Chitinous Plates" for combat survivability
- [ ] **Artifact scene** — "The Thing You Found" — starting item selection
- [ ] **Name entry** — Enter character name
- [ ] **Confirmation** — Character summary with stats (Brawn, Reflexes, Toughness, Wits, Instinct, Presence), mutation, backstory
- [ ] **Verify:** Portrait renders (Flux image — should reflect mutation and wasteland aesthetic)
- [ ] **Verify:** Genre theme CSS applies (mutant_wasteland styling — gonzo post-apocalyptic)
- [ ] **Accept character** — Game phase begins

## 3. Initial Exploration

- [ ] **Read opening narration** — Narrator sets the scene at the trade post on the edge of the black glass plain
  - Expected: The Glass Flat visible in the distance, humming with mutagenic resonance, the starting location's gritty detail
- [ ] **Verify:** Narration streams in chunks (NARRATION_CHUNK → NARRATION_END)
- [ ] **Verify:** Background music plays (AUDIO_CUE — wasteland/post-apocalyptic track)
- [ ] **Verify:** Scene illustration renders (IMAGE message — wasteland landscape)
- [ ] **Type a simple action** — "I look around" or "I check what's nearby"
- [ ] **Verify:** Intent classification works (action routed to Narrator agent)
- [ ] **Verify:** Response narration arrives with markdown formatting
- [ ] **Verify:** Tone is "gonzo-sincere" — weird but played straight, not campy

## 4. NPC Interaction

- [ ] **Encounter a Dome Syndicate trader** — Scrapborn faction, led by Odige Fuseborn
  - Try: "I look for someone to trade with" or "I approach the merchants"
  - Expected: Pragmatic, everything-has-a-price attitude. Rain-catcher tech as leverage.
- [ ] **Verify:** Ensemble agent handles dialogue
- [ ] **Verify:** NPC disposition affects tone (Dome Syndicate is neutral — mercantile, transactional)
- [ ] **Find a Drifter singer** — The Singers of the Long Signal, led by Åych Przysåuchkin
  - Try: "I look for the nomads" or head toward the dust wastes
  - Expected: Radio-static shamanism, cryptic prophecy, distrust of Vaultborn
- [ ] **Meet a Greenfolk representative** — The Understory Communion
  - Try heading toward the Blooming Tangle: "I follow the overgrowth"
  - Expected: Religious fervor about the root-intelligence, symbiotic mutations
  - Adta the Overgrown — her lower body consumed by roots, carried by them like a palanquin
- [ ] **Verify:** Different NPCs have distinct voice/personality in narration
- [ ] **Test faction tensions** — Mention the Dome Syndicate to a Greenfolk, or Vaultborn to a Drifter
  - Expected: Hostility, old grudges surface (the Bargain, Karta's sabotage, the Unsealing)

## 5. Slash Commands & UI Panels

- [ ] **Type `/character`** — Character sheet panel opens
  - Verify: Stats grid (Brawn/Reflexes/Toughness/Wits/Instinct/Presence), mutation, backstory
  - Verify: Can also toggle with keyboard shortcut (C)
- [ ] **Type `/inventory`** — Inventory panel opens
  - Verify: Starting items shown (artifact from creation), salvage currency
  - Verify: Can also toggle with keyboard shortcut (I)
- [ ] **Type `/quests`** — Quest log opens
  - Verify: Any initial quests from the starting situation
- [ ] **Type `/journal`** — Journal/handout viewer opens
  - Verify: Any handout images appear as thumbnails, click to lightbox
- [ ] **Press M** — Map overlay opens
  - Verify: SVG map with explored locations (CRT/phosphor map style)
  - Verify: Current location highlighted, fog of war on unexplored regions
  - Expected regions: Glass Flat, Przyå Dust, Bone Wind, Tood's Dome, Blind Reach, Blooming Tangle, Vault Echo, etc.
- [ ] **Press P** — Party panel toggles
  - Verify: Character portrait (with mutation visible), HP bar, status
- [ ] **Press Escape** — All overlays close

## 6. Travel & Navigation

- [ ] **Travel to Tood's Dome** — "I head to Tood's Dome" or "I follow the trade road to the settlement"
  - Expected: Chapter/location marker. Scrapborn settlement, industrial salvage aesthetic.
- [ ] **Verify:** Map updates with new location revealed
- [ ] **Verify:** Ambience audio changes (industrial clanging, different mood)
- [ ] **Verify:** Scene illustration updates for new location
- [ ] **Cross the Przyå Dust** — "I head into the dust wastes"
  - Expected: Dangerous crossing. Radioactive grey powder, Drifter caravans in wet hide wraps. Narration should convey environmental hazard.
- [ ] **Approach the Glass Flat** — "I head toward the black glass plain"
  - Expected: The 40-mile fused plain, humming, mutagenic. The green eye blinking below. Narrator should warn of danger. Nobody goes to the center.
- [ ] **Visit Bone Wind** — Drifter waystation
  - Expected: Bleached mount-bones, wind harps, rider-poets trading route-songs
- [ ] **Visit the Blooming Tangle** — "I push into the overgrowth"
  - Expected: Hyper-mutated jungle consuming industrial wreckage, spores causing synesthesia, Greenfolk in the canopy

## 7. Combat

- [ ] **Provoke a combat encounter** — Explore dangerous territory (Glass Flat edges, Przyå Dust) or antagonize a faction
  - Or: "I try to salvage from the Singing Pit" — contested Scrapborn territory
- [ ] **Verify:** Combat overlay appears (CombatOverlay component)
  - Enemy list with HP bars
  - Turn order display
- [ ] **Verify:** Combat narration is cinematic and wasteland-flavored (mutations, improvised weapons, environmental hazards)
- [ ] **Take a combat action** — "I swing my salvage axe" or "I use my psychic static to disorient them"
  - If you have a mutation, try using it in combat
- [ ] **Verify:** State patches update HP bars in real-time
- [ ] **Verify:** Combat SFX play (AUDIO_CUE with combat sounds)
- [ ] **Take damage** — Get hit, verify HP bar updates in Party panel
  - Check color coding: green (healthy) → orange (wounded) → red (critical)
  - Lethality is "moderate" — deaths should be possible but not trivial
- [ ] **Win or flee combat** — Resolve the encounter
- [ ] **Verify:** Combat overlay clears, normal narration resumes

## 8. Trope Engine

The Flickering Reach inherits genre-level tropes from mutant_wasteland. Watch for these narrative patterns firing naturally:

- [ ] **The Mentor** archetype — An unlikely teacher figure (a Drifter singer? Won Pyru equivalent?)
  - Watch for: Reluctant teaching, lessons through crisis, cost of knowledge
- [ ] **The Corruption** archetype — Institutional rot
  - Expected: The Dome Syndicate's rain-catcher monopoly, or Vaultborn isolationism
  - Corruption is structural, not individual — removing one person changes nothing
- [ ] **The Prophecy** archetype — The Long Signal's predictions
  - Drifter singers predicted the last three dust storms and a mine collapse
  - Prophecies should be ambiguous — multiple valid interpretations
- [ ] **Verify:** Trope progression visible in GM Mode (watcher dashboard)
  - Progress bars for active tropes
  - Beat injection markers

## 9. Diamonds and Coal (Dramatic Moments)

The SOUL principle "Diamonds and Coal" means not every moment is epic. Test this:

- [ ] **Do something mundane** — "I patch my gear" or "I eat whatever's in my pack"
  - Expected: Short, simple narration (coal). Wasteland life between crises.
- [ ] **Do something dramatic** — "I confront Odige Fuseborn about the rain-catcher prices" or "I tell the Drifter singer I'm from a vault"
  - Expected: Longer, more vivid narration (diamond). Faction tensions, personal stakes.
- [ ] **Verify:** Beat filter suppresses image renders for low-drama actions
- [ ] **Verify:** High-drama actions trigger image generation

## 10. Voice & Audio

- [ ] **Test push-to-talk** — Hold mic button, speak an action, release
  - Verify: Recording indicator shows duration
  - Verify: Whisper transcribes speech to text
  - Verify: Transcript preview appears for editing
  - Verify: Confirm sends the transcribed action
- [ ] **Verify:** TTS voice narration plays
  - Character voices should be distinct per NPC (Scrapborn grit vs Drifter mysticism vs Greenfolk serenity)
  - Music should duck during voice playback
- [ ] **Test audio controls** — AudioStatus panel (bottom-left)
  - Adjust music volume slider
  - Adjust SFX volume slider
  - Mute/unmute individual channels
  - Verify: Settings persist across page reload (localStorage)

## 11. Multiplayer

- [ ] **Open second browser tab/window** — Connect as a second player
  - Same genre (Mutant Wasteland), same world (Flickering Reach), different player name
  - Try different origins (one Vault Dweller, one Heap Rat) for contrast
- [ ] **Verify:** Both players see each other's actions
- [ ] **Verify:** Turn barrier works — both players submit before narrator responds
- [ ] **Verify:** Party panel shows both characters with distinct mutations
- [ ] **Test perception rewriter** — If one character has psychic static and the other doesn't, narration should differ (psychic hears whispers the other doesn't)
- [ ] **Test WebRTC voice** — Both players should hear each other via peer voice chat
- [ ] **Mid-session join** — Open a third tab, connect mid-game
  - Verify: Catch-up narration provides context for the joining player

## 12. GM Mode / Watcher

- [ ] **Open GM Mode** — Use the GM debugging panel
- [ ] **Verify:** Event stream shows real-time events with subsystem tags
- [ ] **Verify:** Trope timeline shows active tropes and progress bars
- [ ] **Verify:** State snapshot inspector shows current GameSnapshot
- [ ] **Verify:** Validation alerts show any warnings/errors
- [ ] **Verify:** Subsystem histogram shows agent invocation distribution

## 13. Persistence

- [ ] **Save game** — The session should auto-persist to SQLite
- [ ] **Reload page** — Reconnect to the same session
- [ ] **Verify:** Game state restored (characters, location, quest progress, narrative log)
- [ ] **Verify:** "Previously On" recap narration plays on reconnect

## 14. Edge Cases & Stress

- [ ] **Rapid input** — Type several actions quickly
  - Verify: Action queue handles them gracefully
- [ ] **Long input** — Type a very long action (multiple sentences)
  - Verify: Input sanitization works, no XSS
- [ ] **Disconnect and reconnect** — Kill the browser tab, reopen
  - Verify: Session recovery works
- [ ] **Daemon cold start** — Stop and restart sidequest-daemon
  - Verify: Graceful degradation (game continues without media, recovers when daemon returns)

---

## Feature Coverage Checklist

After completing the playtest, verify these systems were exercised:

| System | Exercised? | Notes |
|--------|-----------|-------|
| WebSocket connection | | |
| Character creation | | |
| Intent classification | | |
| Narrator agent | | |
| WorldBuilder agent | | |
| CreatureSmith agent | | |
| Ensemble agent (dialogue) | | |
| Dialectician agent | | |
| Troper agent | | |
| State patching | | |
| Combat system | | |
| Trope engine | | |
| Image generation (Flux) | | |
| TTS (Kokoro) | | |
| Music (mood-based) | | |
| Audio mixing (3-channel) | | |
| Push-to-talk (Whisper) | | |
| WebRTC voice chat | | |
| Slash commands | | |
| Map overlay | | |
| Inventory panel | | |
| Character sheet | | |
| Journal/handouts | | |
| Multiplayer (2+ players) | | |
| GM Mode / Watcher | | |
| SQLite persistence | | |
| Genre theming (CSS) | | |
| Beat filter | | |

---

## Known Limitations (Current Sprint)

These features are **not yet available** — don't expect them to work:

- **Drama-aware text delivery** — Text streams at one speed regardless of drama_weight
- **Faction agendas** — The Dome Syndicate doesn't proactively inject events yet (Epic 6 backlog)
- **Server-side slash commands** — /status, /inventory etc. are client-side only
- **Scenario/mystery mechanics** — No whodunit, belief state, or gossip propagation
- **OCEAN personality** — NPCs don't have Big Five profiles yet
- **Lore retrieval** — No RAG or semantic search (the Long Signal's knowledge isn't indexed)
- **Tone command** — Can't adjust genre axes (hope/tech_level/weirdness) mid-session
- **Turn reminders** — Idle players won't get nudged

## World Reference (Spoilers)

### Factions

| Faction | Leader | Disposition | Agenda |
|---------|--------|-------------|--------|
| **Dome Syndicate** (Tood's Dome) | Odige Fuseborn | Neutral | Rain-catcher monopoly, control all critical infrastructure |
| **Singers of the Long Signal** | Åych Przysåuchkin | Wary | Justice for the Bargain, Drifter independence |
| **Understory Communion** | Adta the Overgrown | Cautious | Let the root-network spread unchecked |
| **Vaultborn** (Vault Echo) | Unnamed leader | Isolationist | Total isolation, Protocol dogma |

### Key Locations

| Region | Description | Faction Presence |
|--------|-------------|-----------------|
| **Glass Flat** | 40-mile fused black glass plain, mutagenic, green eye at center | Scrapborn salvage edges |
| **Przyå Dust** | Radioactive grey powder belt, nothing grows, metal crumbles | Drifter crossings |
| **Tood's Dome** | Scrapborn trading hub, rain-catcher manufacturing | Dome Syndicate HQ |
| **Bone Wind** | Drifter waystation, mount-bone cairns, wind harps | Singer gathering point |
| **Blind Reach** | Canyon of the Bargain, psychic frogs croak tithed children's names | Contested |
| **Blooming Tangle** | Hyper-mutated jungle over industrial ruins, spore synesthesia | Understory Communion |
| **Sporecap Garden** | Greenfolk settlement at jungle edge | Understory Communion |
| **Vault Echo** | Sealed Vaultborn complex, trade-locks only | Vaultborn |

### Key NPCs

| NPC | Faction | Role | Secret/Hook |
|-----|---------|------|-------------|
| **Odige Fuseborn** | Dome Syndicate | Merchant-engineer leader | "Everything has a price and most things have two" |
| **Darty Ironlung** | Dome Syndicate | Excavation lead at Rusted Junction | Seeking second atmospheric processor |
| **Åych Przysåuchkin** | Singers | Ancient singer, rides 7-limbed mount | Claims continuous conversation with Third Conclave's ghost-signal |
| **Fortilkacaå** | Singers (militant) | Burnt Camp faction leader | Wants to march on Vault Echo for Bargain reparations |
| **Adta the Overgrown** | Understory Communion | Elder, root-consumed lower body | Roots carry her like a palanquin — "a gift, not a disease" |
| **Minem Fernwalk** | Understory Communion | Ambassador to surface | Gets screamed at by Scrapborn whose settlements are being devoured |
| **Katomod Saplimb** | Understory Communion | Young radical | Secretly feeding pre-war biotech to roots — accelerating growth |
| **Päàn Sporecap** | Understory Communion | — | Claims to have heard the Understory laugh |
| **Hicienck** | Scrapborn (cult) | Bright Grid cult leader | Pre-war world was paradise destroyed by divine negligence |
| **Which-seven** | Vaultborn | Theologian-functionary at Silent Vault | "The surface is a punishment, ascending is a sin" |

### Historical Hooks

- **The Unsealing of Silo Prime** (1,200 years ago) — Third Conclave AI tried to unseal, reactor meltdown, created the Glass Flat, mutated Drifter bloodlines
- **The Bargain** — Vaultborn tithed Drifter children in exchange for moisture tech; Karta sabotaged the harvester
- **Kuinem's Great Sowing** (600 years ago) — Created the root-intelligence now worshipped by Greenfolk
