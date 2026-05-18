# Save Forensics — UX Redesign Spec (the ol' Tufte)

**Status:** design spec — handoff to Dev. UX Designer does not write code.
**Surface:** `sidequest-server/sidequest/server/static/forensics.html` (single
self-contained file, vanilla JS). All endpoints already exist; **no server
change required** for P0/P1. One fold-output addition for P1 (§6).
**Sibling for consistency:** `/dashboard.html` — already ships **D3 v7**,
`.chart-container svg{width:100%}`, D3 histogram/scatter/flame render fns.
Reuse that technique; keep forensics' own GitHub-dark palette.

---

## Who this is for (from CLAUDE.md)

- **Keith** — forever-GM running the *autopsy*. The question he brings: "did
  the narrator actually track the world, or did it wing it?" That is a
  **comparison** task: derived belief vs stored ground truth, across a long
  game.
- **Sebastien** — mechanics-first. Wants the numbers and the provenance
  legible, not buried in a JSON dump.

This is the post-mortem counterpart to the live OTEL `/dashboard`. It is a
GM/dev lie-detector, not a player surface.

## Tufte thesis

> "At the heart of quantitative reasoning is a single question: *compared to
> what?*"

The page's entire reason to exist is comparison and exception-finding. The
current layout makes both impossible. Fix that and it becomes viable; polish
without fixing it does not.

---

## Diagnosis — 7 failures (each tagged with the Tufte principle it breaks)

1. **The 117-round timeline is a scroll tarpit, not an overview.**
   117 near-identical 3-line rows ("Round N · seq X–Y · NARRATION×1
   SCRAPBOOK_ENTRY×1"). ~115 of 117 are byte-identical. You cannot see the
   *shape* of the game. — *Breaks: micro/macro readings; data-ink ratio
   (117 rows, ≈0 bits).* → **small multiples / sparkline.**

2. **No comparison — purpose defeated by layout.** "Derived state" and
   "Final stored snapshot" are **6 panels apart**, vertically stacked,
   different formats (table vs 20 KB `JSON.stringify`). The one read the
   GM needs requires scrolling and holding state in his head. — *Breaks:
   "compared to what?"; comparisons must be adjacent and like-formatted.*

3. **Chartjunk: 6 nested boxes-in-a-box.** Every panel is
   `background+border+radius+uppercase letter-spaced h2 with its own
   rule`. None of that ink encodes data. — *Breaks: data-ink ratio;
   maximize the proportion of ink that is information.*

4. **The JSON dump.** Three panels render `JSON.stringify(o,null,2)`. "Final
   stored snapshot" dumps the entire `game_state` (~40 keys; `characters`
   ≈8 KB, `magic_state` ≈12.5 KB) as one undifferentiated wall. A GM cannot
   scan it. — *Breaks: data-ink; flatten to the audited fields.*

5. **Color encodes nothing.** Legend implies a stored/derived/absent tier
   system; the body paints narrative, events, *and* scrapbook all
   `tier-stored` green. "stored" means four different things. — *Breaks:
   color must encode one variable.*

6. **No exception surfacing.** The autopsy *is* finding the anomaly — the
   round with unparseable events, the stretch where the narrator stopped
   grounding facts. The page makes you hunt 117 clicks. — *Breaks: the
   graphic should draw the eye to the exception; annotation layer.*

7. **Provenance discarded.** The KnownFacts fold returns `{summary,
   category}` + `source_seqs` but drops the footnote `is_new` flag.
   "*Which round did the narrator first learn this?*" is the single most
   useful autopsy datum and it is not derivable from the current output.
   — *Breaks: layering; the most important variable must be encoded.*
   (Owned-up: I wrote that fold. The gap is real; fix in §6.)

---

## The redesign — one screen, three registers

ASCII wireframe (dark GitHub palette unchanged; `─` = 1 px `--line` rule,
**no panel fills, no box borders, no radius**):

```
 Save Forensics · coyote_star-mp · space_opera/coyote_star    [save ▾]
 ───────────────────────────────────────────────────────────────────────
 MACRO  (the whole 117-round game in ~110px — click a column to drill)
   facts ▁▁▂▂▃▃▄▅▅▆▆▆▇▇▇▇▇████  cumulative KnownFacts  5→107→216
   new   ▎ ▍▎ ▊▎▏ ▍▎▏▎ ▏▎▏ ▏▎  is_new per round (where worldbuilding happened)
   intg  ················|····  · ok  | unparseable  ░ no-events   ← lie row
        R1                R57               R117      ▲ selected: R57
 ───────────────────────────────────────────────────────────────────────
 COMPARISON · Round 57            DERIVED (narrator believed)  │  STORED (truth)
   location        Bay Three / Kestrel        first seq 1      │  Bay Three / Kestrel    ✓
   quest/objective "release the footage"      first seq 51     │  quest_log {}           ⚠ diverged
   party           Ritali, Catalina           seq 1            │  player_seats: 2        ✓
   facts known     107  (Place 23 Lore 23 Person 29 Quest 29 Ability 3)  │  (n/a — belief only)
   integrity       no unparseable events this round                      │
 ───────────────────────────────────────────────────────────────────────
 EVIDENCE  (collapsed — one line each; click to expand inline)
   ▸ Narrative · R57 — "Right — Suri Pell is aboard the Kestrel…"   (2 entries)
   ▸ Event stream · seq 115–116 · NARRATION×1 SCRAPBOOK_ENTRY×1
   ▸ KnownFacts ledger · 107 facts ▸ (table: fact · cat · first-seen · last-seen)
   ▸ Projection lens · 2 players · 0 hidden
   ▸ Scrapbook · "…" · render: skipped_policy
   ▸ Stored snapshot · audited fields ▸ (flattened table, not raw JSON)
```

**Register 1 — MACRO strip (replaces the scroll list).** Full-width SVG,
three small-multiple rows on a shared round x-axis (D3 v7, reuse
dashboard's pattern):
- `facts`: cumulative `len(derived)` per round — area sparkline. The
  learning curve; plateaus = narrator coasting.
- `new`: per-round count of footnotes with `is_new:true` — thin bars. The
  worldbuilding pulse.
- `intg`: one mark/round — red `|` if `unparseable_seqs` non-empty, faint
  `░` if no events, quiet `·` if normal. **The lie row.** This is the
  exception layer; it must be the most salient ink on the page.
Click a column → loads that round. Hover → tooltip. The entire game is now
legible in one viewport with zero scrolling.

**Register 2 — COMPARISON (the headline, the reason it exists).** Two
aligned columns, identical row format, semantic rows the GM actually
audits (location, objective, party, facts-known, integrity). Right column
from `/snapshot` (flattened — `character_locations`, `turn_manager`,
`player_seats`, quest_log keys), left from the cumulative fold at the
selected round. Divergences get a `⚠ diverged` tag; matches a quiet `✓`.
Honest limitation: derived (KnownFacts) and stored (snapshot) don't share a
join key — alignment is by semantic category, best-effort. That is *still*
the autopsy: the GM's eye does the final comparison, which is the entire
point and is impossible when they're 6 panels apart. Don't fabricate a
join; place them adjacent and let the human read it (Tufte: trust the eye
with well-arranged data).

**Register 3 — EVIDENCE (layered, collapsed).** The current 6 panels are
*supporting evidence*, not the headline. Each becomes a one-line summary
that expands inline on click. Two get real treatment:
- *KnownFacts ledger*: a sortable table — `fact_id · category · summary ·
  first-seen seq · last-seen seq · ×N restated`. This is where §6's
  `is_new`/first-seen earns its keep.
- *Stored snapshot*: a **flattened audited-fields table**, never raw JSON.
  Rows: `turn_manager.round`, `character_locations.*`, per-character
  `level/xp/inventory count`, `active_tropes` (id+status+progress),
  `player_dead`, `current_region`. The 20 KB blob stays one expand deeper
  (`▸ raw JSON`) for the rare deep dive.

---

## Prioritized, Dev-actionable spec

**P0 — makes it viable (do these or it stays non-viable):**

- **P0.1 Kill the boxes.** Delete `.panel` fill/border/radius and the
  `<h2>` bottom-rule. Sections separated by one `--line` rule + a quiet
  lowercase label. Pure data-ink. (CSS-only; ~10 lines.)
- **P0.2 Macro strip.** Replace the 117-row `tlBox` loop with one SVG
  small-multiples strip (D3 v7 from the dashboard CDN). Data: the existing
  `/timeline` array + per-round `len(derived)` (one `/turn/{r}` is already
  fetched on click; cumulative fact counts can be derived cheaply — see
  P1.1). Click column = current `selectTurn`. **This single change
  eliminates the scroll tarpit and creates the macro view.**
- **P0.3 Comparison block.** Lift "Derived" and "Stored" out of the panel
  stack into a 2-column aligned block directly under the strip, same row
  keys, flattened snapshot (no `JSON.stringify`). Diverge/✓ tags.
- **P0.4 Collapse the other 4 panels** to one-line expanders. Default
  closed.

**P1 — the autopsy gets sharp:**

- **P1.1 Fold output: add `is_new`/first-seen.** *(server, ~6 lines —
  `forensic_fold.py`.)* Extend `DerivedField` with `first_seq` (the lowest
  seq, captured when the fact first appears) and keep `source_seqs`. The
  strip's `facts`/`new` rows and the ledger table's "first-seen" column
  depend on it. This is the §7 gap; it is small and isolated, full test
  parity with the existing fold tests.
- **P1.2 Integrity row is the loudest ink.** Red marks on the strip for
  any round whose bundle has non-empty `unparseable_seqs`; clicking jumps
  there. This is the lie-detector's headline.
- **P1.3 Divergence detection.** In the comparison block, compare derived
  location/party against snapshot `character_locations`/`player_seats`;
  flag mismatch. (Pure client logic over data already fetched.)

**P2 — refinement:**

- **P2.1** Strip annotations: label the round where cumulative facts
  flatline for ≥5 rounds ("narrator stopped grounding here").
- **P2.2** Keyboard nav (←/→ rounds) — matches a GM scrubbing a game.
- **P2.3** Sparkline tooltip parity with dashboard's hover convention.

**Out of scope / do not do:** palette merge with dashboard (forensics'
GitHub-dark is internally coherent — merging *reduces* consistency);
new dependencies (D3 already on the dashboard CDN); any write path
(read-only contract is load-bearing — see `project_sqlitestore_open_writes`,
`project_saves_no_state_delta`).

---

## Consistency notes (consistency-guardian)

Three existing precedents make this *pattern-following*, not novelty:
1. `/dashboard.html` already does D3 v7 small-multiples (flame, histogram,
   scatter) — same tool family, same technique.
2. The flatten-JSON-to-table move is the dashboard's `tier-chart` /
   `parse-status-chart` convention applied to state.
3. Collapsed-evidence layering mirrors the dashboard's tabbed cards.

Keep: forensics palette, monospace type, read-only contract, all endpoints.

## Handoff

→ **Dev (the White Rabbit).** P0 is CSS + one D3 strip + a re-layout of
existing rendered data — single file, vanilla JS, no endpoint change. P1.1
is a ~6-line server fold addition with existing test parity. Recommend P0
as one branch (`feat/forensics-ux-tufte`), P1 as a follow-up. UX Designer
available for review of the rendered result against this spec.
