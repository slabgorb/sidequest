
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
