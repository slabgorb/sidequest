---
parent: context-epic-65.md
workflow: tdd
---

# Story 65-9: Lore Cast section — public NPC projection + manifest-gated portraits

## Business Context

Epic 65 replaces git-LFS pointer tracking with a checked-in R2 manifest
(`sidequest-content/r2_manifest.json`, 1743 entries — committed by 65-7) so the
dual-clone (OQ-1/OQ-2) workflow can answer "what's actually rendered vs. what
still needs doing" without hitting the network. Story 65-8 (DONE) spent that
manifest oracle for the first player-facing payoff: it lit up the **Points of
Interest** section on the lore reference page with manifest-gated POI images.
This story is the **portrait analog** — it adds a public **Cast** section (the
world's named NPCs) to the same page, with portrait `<img>`s gated on the same
manifest.

The lore reference page (`GET /reference/lore/{pack}/{world}`) is a public table
tool (ADR-135): a single fixed projection any player can open to see a world's
geography, points of interest, history, and factions. A **Cast** section gives
the table a face-name index of the world's dramatis personae — who's who before
and during play. Two readers are served, exactly as in 65-8. The narrative
reader (James/Keith) gets an illustrated who's-who — Diamonds-and-Coal: the
worlds with real portrait art finally show it. The mechanical/legibility reader
(Sebastien/Jade) gets NPC identity surfaced as a stable, scannable list rather
than hunted for in prose.

The manifest gate is what makes this safe. Some worlds (e.g. glenross) have
authored NPCs but **zero** portrait images on R2, so a naive renderer would emit
broken `<img>` tags into a player's face. Gating emission on manifest presence —
authored-but-not-on-R2 NPCs render **text-only**, never a broken image — is
Genre-Truth presentation hygiene: show what exists, silently omit the *image*
when the asset is absent, but **fail loud** when the manifest artifact itself is
missing (No Silent Fallbacks). That last distinction is the load-bearing one and
the gap the 65-8 reviewer flagged for the shared gate; 65-9 closes it.

## Technical Guardrails

**This is a wire-up that REUSES 65-8's landed gate machinery — not a new build.**
The manifest gate shipped in 65-8 and is proven on the live reference page.
Reuse it; do not author a second, divergent manifest parser or gate
(CLAUDE.md: "Don't Reinvent — Wire Up What Exists").

**Repo / branch:** `sidequest-server` only, on `feat/65-9-lore-cast-public-npc-projection`
(off `develop` per repos.yaml — NOT main). Server is Python/FastAPI, uv-managed.
Run tests via the `testing-runner` subagent, never directly.

**As-built seams to reuse (verified on `develop`):**
- `reference_renderer.py:load_r2_manifest_keys(manifest_path: Path) -> frozenset[str]`
  (line ~1131) — the manifest loader. `lru_cache`d, no TTL/mtime. Reuse as-is.
- `reference_renderer.py:_gate_poi_slugs_on_manifest(...)` (line ~1159) — the
  gate-only-when-the-feature-is-present shape. The Cast gate mirrors this.
  Manifest discovery rule: `pack_dir.parent.parent / "r2_manifest.json"`.
- `reference_presenters.py:poi_image_key(pack, world, slug) -> str` (line ~193) —
  builds a **raw R2 key** compared directly against the manifest frozenset. Add a
  **portrait analog**, e.g. `portrait_image_key(pack, world, slug) -> str`,
  returning the NPC portrait key (`.../worlds/{world}/assets/.../{slug}.png` —
  confirm the exact portrait subpath against the manifest entries / existing
  portrait asset convention before pinning the test).
- Spans: `reference_manifest_loaded_span` (`sidequest.reference.manifest_loaded`,
  `telemetry/spans/reference.py`) for the load; reuse the existing portrait
  not-found span family (`scrapbook.npc_portrait_not_found`,
  `telemetry/spans/scrapbook.py`) — or add a `reference`-namespaced portrait span
  if the GM authoring-completeness view (AC8) is wanted. Do NOT invent a parallel
  span vocabulary.
- `resolve_asset_url()` — existing CDN-URL seam. The **presenter** wraps the raw
  key in `resolve_asset_url()`; the **gate** compares the raw key directly and
  must NOT wrap. (This presenter-vs-gate boundary is one of the 65-8 docstrings
  to fix — AC5.)

**Existing test to mirror:** `tests/server/test_reference_poi_manifest_gate.py`
— the POI gate's test module. The new Cast gate test mirrors its structure
(fixture manifest map injected, never live R2).

**Carryover from 65-8 review (PR #573, non-blocking on 65-8, folded here because
65-9 touches the same gate code):** ACs 4–7 below are the carryover items
(assertion tightening, docstring accuracy, type annotations, cache-staleness
runbook). They are in-scope for this story.

## Scope Boundaries

**In scope:**
- A public **Cast** section on the lore reference page rendering the world's
  named NPC projection, with portrait `<img>`s gated on `r2_manifest.json`
  presence (portrait analog of the 65-8 POI gate).
- `portrait_image_key()` (or equivalent) analog to `poi_image_key()`.
- Cast section registered in the page TOC when NPCs exist; omitted when none.
- No-Silent-Fallback e2e route test (absent manifest → 500, not a silently
  image-free page).
- Loud-fail branch coverage: manifest entry dict missing `key` → `ValueError`.
- The four 65-8 carryover items (ACs 4–7): exact-`entry_count` assertion,
  three docstring fixes, two type annotations, cache-staleness runbook note.
- OTEL spans on the manifest load and each portrait decision so the GM/dev panel
  can confirm the gate engaged.

**Out of scope:**
- The **belief firewall / claims projection** — that is ADR-136 (already landed
  separately). This story renders the *public* NPC projection only; it does not
  decide what is public vs. secret. It consumes whatever the existing public
  projection exposes.
- POI map view / SVG (65-11) and world timeline (65-12); Lore Cast *as a
  client-side React surface* (this is server-rendered HTML on the reference
  page).
- Any write to R2 or to the runtime asset ledger; portrait *generation*.
- Mechanical NPC stat surfacing — Cast is a face-name index, not a stat block.
- Live-reloading the manifest cache (AC7 documents the staleness; the optional
  mtime-keyed cache is explicitly optional).

## AC Context

**AC1 — Cast section render + portrait gate.** The public NPC projection renders
as a Cast section; each NPC with a portrait key present in the loaded manifest
gets exactly one `<img>` (CDN URL via `resolve_asset_url()`); NPCs whose portrait
key is **absent** from the manifest render **text-only** — zero `<img>`, no
broken tag. *Pass test:* manifest contains NPC slug's portrait key → one `<img>`
with the resolved URL. *Negative (pins the bug):* key absent → zero `<img`
substrings in the rendered section. Reuse `load_r2_manifest_keys()` +
`pack_dir.parent.parent` discovery; assert on the rendered HTML string, not just
span counts.

**AC2 — No-Silent-Fallback e2e proof.** A route-level test:
`GET /reference/lore/{pack}/{world}` for a **feature-bearing** world (has NPCs)
whose `r2_manifest.json` is **absent** returns **500** (loud), not a silently
image-free 200. *Edge:* a world with **no** NPCs and no manifest must NOT 500
(the gate only fires when the feature is present — mirror
`_gate_poi_slugs_on_manifest`'s gate-when-present shape). Assert the status code
and that the failure is the manifest-missing path, not an unrelated 500.

**AC3 — Loud-fail branch coverage.** Add
`test_load_manifest_entry_missing_key_raises_loudly`: a manifest whose list
entry is a dict **missing the `key` field** must raise `ValueError` (the second,
currently-uncovered loud-fail branch of `load_r2_manifest_keys`). Assert the
exception **type and message**, not `is_none()`.

**AC4 — Assertion tightening (carryover).** The `manifest_loaded` span test must
assert the **exact** fixture `entry_count` (`== N`), not `>= 1`. This proves the
gate read the **fixture** manifest, not the production one — guarding the
`pack_dir.parent.parent` resolution. *Test:* capture the span, assert
`entry_count == <fixture N>`.

**AC5 — Docstring accuracy (carryover).** Fix three 65-8 docstrings in the files
this story already edits: (a) `_gate_poi_slugs_on_manifest` "one span per render"
(false for feature-less worlds — no span when the gate doesn't fire); (b)
`load_r2_manifest_keys` "once per process" (imprecise vs. `lru_cache` semantics);
(c) `poi_image_key` — document that it returns a **raw R2 key** compared directly
to the manifest, that the **presenter** must wrap it in `resolve_asset_url()`,
and the **gate** must NOT. (Verify via the docstring text; no behavioral test
required, but the presenter-vs-gate boundary is exercised by AC1.)

**AC6 — Type annotations (carryover).** Annotate the two test helpers in
`test_reference_poi_manifest_gate.py` (and mirror in the new Cast test module):
`_entry` → `dict[str, object]`, and the `gated_client` fixture →
`Iterator[TestClient]`. *Check:* `ruff`/type pass clean; annotations present.

**AC7 — Cache-staleness runbook (carryover).** Add a runbook/docstring note that
`load_r2_manifest_keys` is `lru_cache`d with no TTL/mtime — a manifest
regenerated after an asset upload is **not** picked up until server restart
(safe-failing: text-only, never broken). *Optional:* key the cache on the
manifest file's mtime so a regenerated manifest is picked up live. The note is
mandatory; the mtime cache is optional (log a Design Deviation if you implement
or skip it).

**AC8 — Optional GM observability.** If the GM authoring-completeness view is
wanted, add a distinct `reference_cast_image_not_in_manifest` (reference-namespaced)
span so "authored but not on R2" is distinguishable from "not authored" — today
both would collapse into the generic portrait-not-found span. **Defer unless the
dashboard needs it**; if deferred, log a one-line Design Deviation noting the
deferral. Per the OTEL principle, the *load* and *per-NPC decision* spans (AC1's
gate path) are NOT optional — they are how the GM panel verifies the gate
engaged rather than Claude improvising a text-only render.

## Assumptions

- **Manifest artifact is present at runtime** at the `SIDEQUEST_GENRE_PACKS`
  mount, discoverable via `pack_dir.parent.parent / "r2_manifest.json"`. If
  absent, AC2's loud-fail (500) is the **correct** behavior — do not work around
  it.
- **A public NPC projection already exists** on the lore page data path (the
  Cast section consumes it). This story does **not** create or filter the
  public/secret split — ADR-136's belief firewall already governs what is public.
  If no public NPC projection is reachable from the lore route, that is a Gap to
  log (blocking) — flag it rather than inventing one.
- **The portrait R2 key convention is stable and discoverable** from the
  committed manifest entries. Confirm the exact portrait subpath against
  `r2_manifest.json` before pinning `portrait_image_key`'s expected string;
  tests inject a **fake** manifest map and must never hit live R2.
- **`load_r2_manifest_keys` / `poi_image_key` signatures are reusable** as-is
  (plus a portrait-key analog). If reuse forces a signature change that ripples
  beyond adding one function or one optional parameter, log a Design Deviation
  before proceeding — that would mean this is no longer a pure wire-up.
- **glenross is the negative fixture** (NPCs yes, portraits-on-R2 no) and a
  portrait-bearing world is the positive fixture. If R2 state has drifted, use a
  manifest **stub**, not the network.

If any assumption proves wrong during implementation, log a Design Deviation and
notify SM — wrong assumptions are the top source of scope creep.

---
_Authored 2026-06-02 to backfill the setup gap (sm-setup produced the session
file but not this story-context doc — the same gap noted on 65-8). Composed via
`/pf-context create story 65-9` solo (no tandem) from the session brief, the
epic-65 context, and the **as-built** 65-8 symbols verified on `develop`
(`load_r2_manifest_keys`, `poi_image_key`, `reference_manifest_loaded_span`,
`scrapbook.npc_portrait_not_found`). Schema-compliant per context-schema.yaml
v1.0.0._
