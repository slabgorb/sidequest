
### Report only observed mechanics — never extrapolate the system (2026-06-07, from Keith)
- When filing playtest bugs: quote logs, quote UI, quote authored content text. Do NOT predict adjacent behavior the system was never observed to do (e.g. claiming the attention-based disposition model "predicts NPCs drift cold when ignored" — whether relationships degrade at all is unknown). Keith: "stop making shit up."
- Quoting authored content verbatim (ability text, lore) is always fine — the line is between citing what exists and inventing system dynamics.

### A clean log can be a vacuous pass — confirm the subsystem ENGAGED before flipping verified (2026-06-07)
- blackthorn fix-validation: zero `entity_sync.project_failed` WARNs looked like a #736 pass, but blackthorn seeds ZERO tropes (`active_tropes: []`) — the merge path never ran. Same session: zero watcher crashes (#733) but no dispatches fired; zero discarded text blocks (#734) but the narrator never double-drafted.
- Rule: verification requires (a) the fix's trigger condition observed firing AND (b) the bad outcome absent. Absence of the bad outcome alone proves nothing on a world/scene that can't produce the trigger. Leave status at `fixed` with a DRIVER note instead.
- Corollary: pick the verification world to match the repro (tropes → five_points/evropi; dispatch crash → five_points; double-draft → tool-heavy turns).

### "Needs restart: yes" for the server is usually just a pull (2026-06-07)
- uvicorn runs `--reload`: pulling the server tree triggers a WatchFiles reload that boots a fresh worker (verify via the `WatchFiles detected changes` line + a NEW `Started server process [pid]`). The reload also re-reads packs/corpora from the content tree.
- The inverse does NOT hold: a content-tree pull alone triggers nothing (WatchFiles watches the server tree only) — content-only fixes still need a server-tree touch/pull or manual bounce to re-cache.
- Bonus: every hot-reload is a free ui #350 regression test — watch for the client's silent re-bind (`session.auto_seated` + `slug_connect.replay`, zero `message_rejected_unbound`) and confirm an action narrates without a page reload.

### npc_pool[].invented_from is the identity-fork detector (2026-06-07)
- Post server #738, every culture-namer mint carries its source string. One curl of the snapshot shows what each pool NPC was minted FROM — instantly distinguishing real names ('Varra') from role labels ('Barkeep'), descriptive epithets ('The Heavy Man in Broadcloth' — forked a roster identity), and plural groups ('Green-Grocery Door Men' → one they/them individual). Check this field FIRST when prose and mechanics disagree about who someone is.

### Read the other lane's full notes BEFORE filing a "salvage" PR (2026-06-07)
- Filed #392 to restore #389's pakook cleanup over merged #391 — then found #391's notes said the pakook long stems were a DELIBERATE canon-style exemption ("rookarook reduplication is croak style"), not an oversight. What looked like a missed cleanup was an editorial call. Operator ruled: keep the longer dictionary; #392 closed unmerged.
- Rule: when two lanes touch the same content, a diff alone can't distinguish "missed" from "chose to keep." Read the peer's rationale notes first; if a real disagreement remains, flag it for Keith — conlang/flavor style calls are his to arbitrate, not a PR race to win.

### Corpus expansion: legacy machine-generated stem blocks ARE the funnel pathology (2026-06-07)
- The "Abinthe Mori*" reroll-clone artifact isn't only a corpus-size problem — prior expansion passes left single-stem blocks (lotharian Glo* was 37% of the file, yellow Bal*/Dor* similar) that funnel Markov chains even after the file passes the 1000-word threshold. When expanding a corpus, check `cut -c1-3 | sort | uniq -c | sort -rn | head` and enforce ~1.5% per 3-letter prefix; prune legacy blocks (max-min bigram-distinct survivors), don't just dilute around them.
- The conlang subagent handles this well in parallel (one per culture family), but instruct stem caps explicitly and have it report top-5 prefixes as evidence — and set-diff old vs new (`comm -23 <(git show HEAD:f | sort -u) <(sort -u f)`) to verify "kept all originals" claims; re-sort makes raw diff deletions misleading.
- `python -m sidequest.cli.namegen` takes culture DISPLAY names ("Red Martian"), not slugs — fails loud with the list if wrong.

### pf branch-protection hook evaluates the branch BEFORE the compound command runs (2026-06-07)
- `git checkout -b feat/x && git commit ...` in one Bash call gets BLOCKED on a protected branch — the PreToolUse hook sees `git commit` while HEAD is still develop. Split into two calls: checkout first, commit second.

### Seed/trope YAML: unquoted ": " inside a list-item string silently becomes a dict (2026-06-07)
- Delivery hints written as prose ("The pattern has a shape: one counter, one route...") parse as a one-key mapping and fail SeedTrope's string validation at LOAD, not at write. Hit 4× across 10 seed decks. Pre-flight before committing any authored deck: `grep -n '^    - [^"].*: ' <file>` and quote offenders.
- Always wiring-verify authored pack YAML through the real loader, not just yaml.safe_load: `uv run python -c "from sidequest.genre.loader import load_genre_pack; ..."` from sidequest-server. model_validate on the raw list misses nothing here, but the loader run also proves the file is where the loader looks (seed_tropes.yaml is a STANDALONE file at pack root or worlds/<world>/, NOT a pack.yaml key — the pack.yaml `- seed_tropes` line is just a section list entry).

### World currency lives in a world `inventory.yaml` `currency:` block — and the world file REPLACES the genre inventory WHOLESALE (2026-06-11, story 103-8)
- Currency is NOT a key on `items.yaml`. `WorldItemsCatalog` (server `genre/models/items.py`) is `extra="forbid"` and only accepts named_items/modifier_items/reliquaries/crimson_remnants/consumable_items/implants. Putting `currency:` there fails the load. (An AC that says "currency as items" is loose phrasing — the real surface is the currency block.)
- The currency pattern is the space_opera one: `worlds/<world>/inventory.yaml` with `currency: {name, denominations[], abbreviation, description, secondary}` (model `CurrencyConfig`, extra=forbid). `denominations` accepts a list or a dict; `secondary` accepts a list/dict/string. aureate_span is the reference.
- **THE TRAP:** `server/dispatch/inventory_resolve.resolve_inventory` does `world.inventory **replaces** the genre one — it is NOT merged.` So a currency-only world inventory.yaml silently wipes the genre's `item_catalog` + `starting_equipment` + `starting_gold`, leaving chargen with no loadouts and no gear. To add a world currency you MUST author the FULL inventory surface (currency + item_catalog + starting_equipment per class + starting_gold), world-flavored. Budget for it — "just add coins" is a full-inventory port.

### New `stocks.yaml` entries are NOT auto-wired into chargen — the `char_creation.yaml` stock step lists them separately (2026-06-11, 103-8)
- `stocks.yaml` defines the trait sets and is validated by the loader (every `granted_mutations` id must resolve against the genre `mutations.yaml` or the pack load fails loud — read the catalog FIRST: structure/ sense/ hybrid/ cognition/ pseudo_psychic/ exotic/). But authoring a stock does NOT make it selectable. The chargen stock-selection step is a separate `choices:` list in `worlds/<world>/char_creation.yaml` with `mechanical_effects.stock_id`. Author both, or the roster loads invisibly and a per-stock chargen smoke can only reach the wired few.
- The stock schema has no region/language field — Indigenous-language anchors (e.g. Penobscot `muwin` = bear) live in `description` prose only. The only check is a register read; there's no structured validation.

### Audit sibling stories before authoring — content lands across story lines and out-of-band (2026-06-11, 103-8)
- 103-8 scope listed "bestiary/creatures" but 103-6 had already authored a full `bestiary.yaml`. 103-8's faction-referencing openings depended on "103-7 (backlog)" but the factions were already named in `lore.yaml`'s `factions[]` from the 103-5 world core. Story scopes overlap and the sprint tracker lags the repo (deps marked backlog were merged out-of-band). `ls worlds/<world>/` + grep the existing files before authoring anything — do not trust the story's declared deps or scope boundaries.

### World trope `extends:` must be the SLUGIFIED NAME of a genre `tropes.yaml` trope — NOT a seed-trope id (2026-06-11, 103-8)
- `resolve_trope_inheritance` (server `genre/resolve.py`) builds the parent map from `genre_tropes` keyed by `_slugify(trope.name)`. The valid parents are the genre `tropes.yaml` entries ONLY (mutant_wasteland: `ruin-fever`, `mutation-tide`, `dead-signal`). The `seed_tropes.yaml` deck is a SEPARATE system (SeedTrope model, the trope-deck) and its ids are NOT valid `extends:` targets. A wrong parent fails loud: `GenreMissingParentError: trope 'X' extends 'y' which does not exist`. flickering_reach is the reference (`extends: dead-signal`). If you brief a sub-author to write world tropes, give them the slugified genre-trope names, not the seed-deck ids.

### Validating a `draft: true` world: `load_genre_pack` SKIPS it, so the pack-load smoke proves nothing (2026-06-11, 103-8)
- `_load_single_world` returns None at the `if config.draft:` check (loader.py ~1133) BEFORE loading any of the world's files — so a green `load_genre_pack` run never touched your draft world's stocks/inventory/tropes/openings/char_creation. To actually validate a draft world, force-load it: shim `loader._load_yaml` to flip `WorldConfig.draft` to False, load the mutation catalog + the 3 genre tropes, then call `_load_single_world(world_path, genre_tropes, root, mutations=muts)` directly. That exercises granted-mutation resolution, trope inheritance, inventory schema, and the openings `?`-in-first_turn_invitation contract. (Most worlds under active authoring are draft until the 103-9-style asset gate is met — this applies to nearly every new world.)
