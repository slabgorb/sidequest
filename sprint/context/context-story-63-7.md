# Story 63-7: Reference chrome markup contract alignment per v3 plan Tasks 20–22

**Story ID:** 63-7
**Epic:** 63 (Reference pages v3 — chrome + wiki-like anchor links)
**Workflow:** TDD (red → green → refactor)
**Type:** bug (corrects drift from 63-4, which shipped a parallel markup vocabulary instead of the plan's)
**Points:** 5
**Priority:** p2
**Repos:** server
**Plan Reference:** `docs/superpowers/plans/2026-05-23-reference-pages-v3.md` Tasks 20 (page wrapper), 21 (hero), 22 (layout + TOC + per-file sections)
**Design bundle:** `docs/design-bundles/2026-05-23-lore-and-rules/project/` — `app.jsx`, `theme.css`, `styles.css`
**Predecessor:** 63-4 (done, but markup drifted from the plan — see Root Cause below)

---

## Root Cause (what 63-4 missed)

63-4 shipped the bundled `theme.css` + `styles.css` and emitted *some* chrome markup, but **the markup vocabulary it emitted does not match the class names the bundle's CSS targets.** Result in production (sidequest.slabgorb.com/reference/lore/space_opera/coyote_star and /reference/rules/space_opera): bare browser defaults — `<ul>` bullets at top of page, blue underlined `<a>`, plain `<h1>` titles, no sidebar layout, no parchment/rugged/terminal typography.

| Plan calls for (v3 Tasks 20–22) | 63-4 actually emitted |
|---|---|
| `<body>` body wrapped in `<div class="page">{body}</div>` (plan line 2641) | no `.page` wrapper |
| `<header class="hero"><div class="hero-eyebrow"><span class="glyph">…</span><span class="eyebrow gilt">…</span><span class="rule"></span></div><div class="hero-kicker">…</div><h1 class="hero-title">…</h1><div class="hero-sub">…</div><div class="hero-epigraph narrative-flourish">…<span class="attrib">…</span></div></header>` (plan lines 2675–2685) | `<header class="hero"><h1>{name}</h1><p class="epigraph">…</p></header>` |
| `<div class="layout"><aside class="toc-sticky"><nav class="toc"><div class="toc-title">Contents</div><ol><li><a href="#{id}"><span class="toc-num">I.</span>Label</a></li>…</ol></nav></aside><main>{sections}</main></div>` (plan lines 2787–2800) | `<nav class="contents-rail" data-scroll-spy><ul><li><a href="#{id}">filename.yaml</a></li>…</ul></nav>` then sections at body root |
| Inline observer queries `aside.toc-sticky nav.toc a`, toggles `.active` class, `rootMargin: '-20% 0% -60% 0%'` (plan lines 2807–2828) | observer queries `.contents-rail a[href^="#"]`, toggles `aria-current`, `rootMargin: '-30% 0px -60% 0px'` |
| `PACK_LABELS`, `PACK_BLURBS`, `PACK_EPIGRAPHS`, `PACK_TOC` Python constants ported verbatim from `app.jsx:12-67` and `app.jsx:183-218` (plan lines 2694–2714 and 2762–2777) | not ported — file-name labels used as TOC text instead |
| `_KIND_OVERRIDES["factions"] = "cult"` (plan lines 2832–2839) | not added |

Why 63-4's gates passed: its chrome tests assert containment of `class="contents-rail"` and `class="hero"`. The bundle's CSS has **zero rules for `.contents-rail`** (`grep -c contents-rail sidequest-server/sidequest/server/static/reference/styles.css` returns 0). Nothing in the test suite checked rendered HTML against the served CSS bundle, and the markup-vs-CSS wiring test mandated by the plan (Task 27 / story 63-5) was deferred. 63-4 went green; the chrome doesn't work in the browser.

---

## Story Scope

Replace the invented chrome vocabulary with the plan's vocabulary. Server-only — no UI repo changes, no content/`theme.yaml` changes (the constants are Python, ported from `app.jsx`). Add the wiring test that 63-4 lacked so this drift can't recur.

**In scope:**
1. `_wrap_document` wraps body in `<div class="page">…</div>` (Task 20 step in plan that 63-4 skipped).
2. Hero rewritten to emit the bundle's full 5-element structure (`.hero-eyebrow`, `.hero-kicker`, `.hero-title`, `.hero-sub`, `.hero-epigraph`).
3. Contents rail rewritten as `<aside class="toc-sticky"><nav class="toc">…<ol>…</ol></nav></aside>` wrapped with `<main>` inside `<div class="layout">`.
4. `PACK_LABELS` / `PACK_BLURBS` / `PACK_EPIGRAPHS` / `PACK_TOC` ported from `app.jsx` into `reference_theme.py`.
5. `_KIND_OVERRIDES` extension for `factions → cult`.
6. Inline observer rewritten per plan (rootMargin, `.active` class, `toc-sticky nav.toc a` query).
7. **NEW wiring test** (this is the gate that 63-4 was missing): render the lore + rules pages for the fixture pack, parse out every distinct `class="..."` value the renderer emits, assert each one has at least one matching rule in the served bundle CSS (`theme.css` or `styles.css`). Single test failure if the renderer ever again emits a class the CSS doesn't style — the same failure mode that produced this story.

**Out of scope:**
- Stat strip inside hero (plan line 2734: deferred to Task 22's section walk, which reads from `rules.yaml`/`progression.yaml` — leave for a follow-up).
- TOC scroll-to-target click handlers (plan emits `<a href="#id">` and lets native anchor nav work; smooth-scroll is an enhancement).
- Validator CLI from Task 27 (that's 63-5's territory; this story only adds the markup-vs-CSS unit-level wiring test).
- Any client-side enrichment (one-mechanism-per-problem — server renders, browser displays).

---

## Task Surfaces

### Task A — Page wrapper (plan Task 20, step 4)

**File:** `sidequest-server/sidequest/server/reference_renderer.py` — `_wrap_document`

`<body>` content currently sits at body root after the banner/island/scroll-spy script. Wrap everything from hero through end-of-body (excluding the trailing scroll-spy `<script>`) inside `<div class="page">…</div>`.

Plan reference: line 2641 `f'<div class="page">{body}</div>'`.

### Task B — Hero rewrite (plan Task 21)

**Files:**
- Modify: `sidequest-server/sidequest/server/reference_renderer.py` — `_build_hero`, `_hero_fallback`
- Modify: `sidequest-server/sidequest/server/reference_theme.py` — add `PACK_LABELS`, `PACK_BLURBS`, `PACK_EPIGRAPHS` constants ported from `app.jsx:12-67`
- Extend: `assemble_rules_page` to also build a hero (rules-page hero falls back to pack label per plan line 2683–2688) — 63-4 only built hero on lore page

Emit, in order, inside `<header class="hero">`:

1. `<div class="hero-eyebrow">` containing:
   - `<span class="glyph">{theme.dinkus.medium.glyph}</span>` — pull from existing `ReferenceTheme.dinkus` (already loaded)
   - `<span class="eyebrow gilt">SideQuest · {PACK_LABELS[pack]} · World Reference</span>`
   - `<span class="rule"></span>` (empty, the CSS draws a gradient rule)
2. `<div class="hero-kicker">{kicker}</div>` — first sentence of `lore.world.description` if present, else `PACK_BLURBS[pack]`
3. `<h1 class="hero-title">{world_name or PACK_LABELS[pack]}</h1>`
4. `<div class="hero-sub">{PACK_LABELS[pack]} · Lore &amp; Rules</div>`
5. `<div class="hero-epigraph narrative-flourish">{epigraph_body}<span class="attrib">{epigraph_attrib}</span></div>` — from `PACK_EPIGRAPHS[pack]`, two-field dict `{body, attrib}` ported from `app.jsx`

XSS escape every interpolation via the existing `escape()` import. Missing `lore.world.name` on a lore page → fall back to `PACK_LABELS[pack]` and emit `reference_hero_unbound_span` WARN (already exists from 63-4). Unknown pack key in any `PACK_*` lookup → keep the current loud-fail pattern (`KeyError` bubbles → 500 + ERROR span); add a new `reference_pack_metadata_missing_span` if a span doesn't already cover that path.

### Task C — Layout + TOC rewrite (plan Task 22)

**Files:**
- Modify: `sidequest-server/sidequest/server/reference_renderer.py` — replace `_build_contents_rail` with `_build_toc(pack)`; insert `<div class="layout"><aside…/><main>…</main></div>` wrapping
- Modify: `sidequest-server/sidequest/server/reference_theme.py` — add `PACK_TOC` constant ported from `app.jsx:183-218`

Emit:

```html
<div class="layout">
  <aside class="toc-sticky">
    <nav class="toc">
      <div class="toc-title">Contents</div>
      <ol>
        <li><a href="#reckoning"><span class="toc-num">I.</span>The Reckoning</a></li>
        ...
      </ol>
    </nav>
  </aside>
  <main>
    {existing per-file section renders go here}
  </main>
</div>
```

Hero stays **outside** `.layout` (plan line 2647 says hero goes above the layout grid).

`PACK_TOC` ports the bundle's per-pack numerals (I, II, III…) and label text. **Unknown pack key:** per plan line 2780, fall through to a two-item default (`[{"num":"I","id":"reckoning","label":"The World"},{"num":"II","id":"bearing","label":"Bearing & Make"}]`) **AND** emit a new ERROR span `sidequest.reference.toc_missing` so the GM panel surfaces the gap. This is a loud surface, not a silent fallback — the gap appears visibly in the OTEL dashboard.

### Task D — Per-file section ids match TOC anchors

**File:** `sidequest-server/sidequest/server/reference_renderer.py` — `_render_file`, `_rail_entries_for`

Currently `_render_file` emits `<section class="file" id="file-{slug(stem)}">`. The plan's TOC links target ids like `#reckoning`, `#bearing`, `#edge`, `#confrontations` — section labels, not file names. The mapping from "TOC item" to "rendered section" is the joint:

- The TOC's `id` field (e.g., `reckoning`) is the rendered section's `id` attribute.
- The renderer chooses which YAML file's content goes inside that section. Per the bundle's `app.jsx:335-366`, `reckoning` = lore intro, `bearing` = char_creation + classes + races, `edge` = edge/composure section, etc.

For this story, keep it pragmatic: emit one `<section id="{toc.id}">` per TOC entry; populate it by the existing per-file walk, but use the TOC entry's `id` for the wrapper (not `file-{stem}`). The mapping table `TOC_TO_FILES: dict[str, list[str]]` lives in `reference_theme.py` next to `PACK_TOC` and maps each toc.id to the file stems whose content belongs in that section. Missing files in a pack → section renders empty (don't omit the section; the TOC link 404-equivalents are spoiler-noisy).

This is a small extension of plan Task 22 step 4 (`_kind_for_stem` for `factions`). If the section/file mapping turns out to need more than the TOC ports cover, defer the over-spill to a follow-up story rather than scope-creeping here.

### Task E — Inline observer rewrite (plan Task 22 step 3)

**File:** `sidequest-server/sidequest/server/reference_renderer.py` — replace `_SCROLL_SPY_SCRIPT`

Port the script body verbatim from plan lines 2807–2828:

```javascript
(function(){
  var ids=Array.from(document.querySelectorAll('aside.toc-sticky nav.toc a')).map(function(a){return a.getAttribute('href').slice(1);});
  var sections=ids.map(function(id){return document.getElementById(id);}).filter(Boolean);
  var links={};
  document.querySelectorAll('aside.toc-sticky nav.toc a').forEach(function(a){links[a.getAttribute('href').slice(1)]=a;});
  if(!sections.length)return;
  var obs=new IntersectionObserver(function(entries){
    var visible=entries.filter(function(e){return e.isIntersecting;}).sort(function(a,b){return a.boundingClientRect.top-b.boundingClientRect.top;});
    if(visible[0]){
      Object.values(links).forEach(function(a){a.classList.remove('active');});
      var top=visible[0].target.id;
      if(links[top])links[top].classList.add('active');
    }
  },{rootMargin:'-20% 0% -60% 0%',threshold:0});
  sections.forEach(function(s){obs.observe(s);});
})();
```

Existing bound test (`test_inline_scroll_spy_js_is_bounded` from 63-4) should continue passing — this script is still ~22 lines, well under the 2KB cap.

### Task F — `_KIND_OVERRIDES` extension (plan Task 22 step 4)

**File:** `sidequest-server/sidequest/server/reference_renderer.py`

```python
_KIND_OVERRIDES["factions"] = "cult"
```

For namespaced ids on lore-tier list-of-dict items (`cult-old-folk`, `cult-river-cabal`, etc.).

### Task G — Wiring test (NEW, fills the gap 63-4 left)

**File:** `sidequest-server/tests/server/test_reference_chrome_wiring.py` (new)

```python
def test_every_emitted_class_has_matching_css_rule():
    """Render the fixture lore + rules pages, parse every distinct
    class="..." token the renderer emits, assert each one appears as
    a selector somewhere in the served theme.css OR styles.css.

    Why: 63-4 shipped markup whose class names had no matching CSS
    rules (.contents-rail). The bundle's CSS targets .toc-sticky/.toc
    instead, so production pages rendered with default browser styles.
    This test prevents that recurrence.
    """
    rules_html = assemble_rules_page("fixture_pack", FIXTURE_PACK_DIR)
    lore_html = assemble_lore_page("fixture_pack", "fixture_world", FIXTURE_PACK_DIR, FIXTURE_WORLD_DIR)

    emitted_classes = set()
    for html in (rules_html, lore_html):
        for match in re.finditer(r'class="([^"]+)"', html):
            emitted_classes.update(match.group(1).split())

    css_text = (
        (Path(__file__).parents[1] / "sidequest/server/static/reference/theme.css").read_text()
        + (Path(__file__).parents[1] / "sidequest/server/static/reference/styles.css").read_text()
    )

    # Allowlist for utility/semantic classes that intentionally have no styling
    # (state hooks the JS toggles at runtime, etc.). Keep this LIST SMALL — if it
    # grows, that's a signal the renderer is emitting decorative-but-unstyled markup.
    SEMANTIC_ALLOWLIST = {"dark", "active"}  # extend deliberately, with rationale

    unmatched = sorted(
        cls for cls in emitted_classes
        if cls not in SEMANTIC_ALLOWLIST
        and f".{cls}" not in css_text  # cheap substring check; precise enough
    )
    assert not unmatched, (
        f"Renderer emits {len(unmatched)} class names with no matching CSS rule: "
        f"{unmatched}. Either the renderer is emitting the wrong vocabulary "
        f"(see story 63-7 root cause), or these classes need styling added. "
        f"Allowlist semantic-only classes in SEMANTIC_ALLOWLIST with a comment."
    )
```

This is a flat substring check, not a real CSS parser — that's deliberate. A CSS parser dep would be overkill for a regression guard whose job is "did we ship `.contents-rail` again." False positives (class name appears in a comment but isn't a selector) are extremely rare given the bundle CSS structure; false negatives (real bug slips through) are what we care about, and substring catches the load-bearing case.

### Task H — Update / retire 63-4's vacuous tests

**Files:** `sidequest-server/tests/server/test_reference_chrome.py`, `sidequest-server/tests/server/test_reference_renderer.py`

63-4's chrome tests assert markup containment like `'class="contents-rail"' in html`. Those assertions die with this story. Either update each test to the new class names (`.toc-sticky`, `.toc`, `.hero-title`, etc.) **or** delete the tests that the new wiring test (Task G) makes redundant. Don't leave behind tests that just check the existence of one new class name — the wiring test already covers that surface more thoroughly.

---

## Acceptance Criteria

- AC-1: **`<div class="page">` wraps body content** (excluding the trailing scroll-spy script tag — that stays at the end of `<body>` for parser-friendliness).
- AC-2: **Hero block emits all 5 bundle elements** in order: `.hero-eyebrow` with glyph+eyebrow+rule, `.hero-kicker`, `.hero-title`, `.hero-sub`, `.hero-epigraph` with `.attrib`. Both lore and rules pages get a hero (rules-page hero falls back to `PACK_LABELS[pack]` as the title per plan).
- AC-3: **Layout grid wraps TOC + main:** `<div class="layout"><aside class="toc-sticky"><nav class="toc"><div class="toc-title">Contents</div><ol>…</ol></nav></aside><main>{sections}</main></div>`.
- AC-4: **TOC items use per-pack numerals and labels** ported verbatim from `PACK_TOC` (`app.jsx:183-218`). `<li><a href="#{id}"><span class="toc-num">{num}.</span>{label}</a></li>`. Unknown pack → 2-item default + ERROR span `sidequest.reference.toc_missing`.
- AC-5: **Inline observer matches plan listing exactly:** queries `aside.toc-sticky nav.toc a`, toggles `.active` class on the matching link, rootMargin `-20% 0% -60% 0%`. Still passes the `_SCROLL_SPY_SCRIPT` ≤2KB bound test.
- AC-6: **`PACK_LABELS`, `PACK_BLURBS`, `PACK_EPIGRAPHS`, `PACK_TOC`** all ported into `reference_theme.py`; **all 10 live packs covered** (no fallthrough for `caverns_and_claudes`, `elemental_harmony`, `heavy_metal`, `mutant_wasteland`, `neon_dystopia`, `pulp_noir`, `road_warrior`, `space_opera`, `spaghetti_western`, `tea_and_murder`). `victoria` is fine as-included if the bundle covers it; skip otherwise (not currently a live pack on this branch).
- AC-7: **`_KIND_OVERRIDES["factions"] = "cult"`** added; namespaced ids on lore factions verified by an existing or new unit test.
- AC-8: **Wiring test passes:** `test_every_emitted_class_has_matching_css_rule` (Task G) parses both rendered pages and finds zero unmatched class names against the served CSS bundle, modulo a documented `SEMANTIC_ALLOWLIST` of at most 5 entries.
- AC-9: **All existing 63-4 chrome tests** either updated to the new vocabulary or deleted as redundant with the wiring test — no test references `.contents-rail` after this story merges.
- AC-10: **No silent fallbacks introduced:** unknown pack → loud (TOC error span or pack-metadata error span). Missing world name on lore page → existing WARN span behavior preserved. Missing `lore.world.description` → kicker falls back to `PACK_BLURBS[pack]` (which is content-defined per `app.jsx`, not a silent default).
- AC-11: **Just `check-all` passes:** server lint + server test + UI lint + UI test (no UI changes here, but smoke gate stays clean).
- AC-12: **Production smoke** (manual): after merge + deploy, `https://sidequest.slabgorb.com/reference/lore/space_opera/coyote_star` renders with a hero block, a left sidebar TOC with Roman numerals, and parchment/terminal typography per the space_opera archetype. (Manual because Cloudflare Access gates the live route — this is a Keith-verification step, not a CI check.)

---

## Constraints / Project Memory

- **No silent fallbacks.** Unknown pack key in PACK_* tables = loud (ERROR span + visible 2-item TOC). Missing CSS class match in wiring test = test failure with a precise message.
- **No content-coupled tests.** Wiring test reads the served CSS files (which are committed in the server tree under `sidequest-server/sidequest/server/static/reference/`) — that's the production CSS bundle, not content from `genre_packs/`. The fixture pack at `tests/fixtures/packs/reference_v2_fixture/` is what the assemble_* calls operate on. Live packs are not loaded.
- **One mechanism per problem.** The renderer is the single chrome emitter — no client-side enrichment, no post-render JS injection beyond the two inline scripts (bad-anchor banner from v2, scroll-spy from v3).
- **No design-tool affordances.** Already enforced by 63-4's regression guards (`.tweaks-*` absent from production CSS). No new affordance markup should appear from this story.
- **Server-only diff.** No content (`theme.yaml`), no UI (`sidequest-ui`), no daemon. All ports are Python constants in `reference_theme.py`.
- **OTEL coverage.** New `sidequest.reference.toc_missing` span (if `PACK_TOC` lookup falls through); register in `FLAT_ONLY_SPANS` following the existing `SPAN_REFERENCE_*` shape in `sidequest/telemetry/spans/reference.py`.

---

## Files (likely)

**Modify:**
- `sidequest-server/sidequest/server/reference_renderer.py` — `_wrap_document` (page wrap), `_build_hero`, `_hero_fallback`, `_build_contents_rail` (replace with `_build_toc`), `_rail_entries_for` (extend or replace), `_SCROLL_SPY_SCRIPT`, `_KIND_OVERRIDES`
- `sidequest-server/sidequest/server/reference_theme.py` — add `PACK_LABELS`, `PACK_BLURBS`, `PACK_EPIGRAPHS`, `PACK_TOC`, `TOC_TO_FILES` constants
- `sidequest-server/sidequest/telemetry/spans/reference.py` — add `SPAN_REFERENCE_TOC_MISSING` + helper, register in `FLAT_ONLY_SPANS`
- `sidequest-server/tests/server/test_reference_chrome.py` — update assertions to new vocabulary or delete redundant cases
- `sidequest-server/tests/server/test_reference_renderer.py` — same

**New:**
- `sidequest-server/tests/server/test_reference_chrome_wiring.py` — the wiring test that prevents recurrence

**Untouched:**
- `sidequest-server/sidequest/server/static/reference/{theme,styles}.css` — bundle stays as-is (it's the source of truth)
- `sidequest-server/sidequest/server/reference_routes.py` — routes unchanged
- `sidequest-content/` — no content changes
- `sidequest-ui/` — no UI changes

---

## Risks & Gotchas

1. **Hero on rules pages didn't exist before.** 63-4's `assemble_rules_page` calls `_wrap_document` without `hero_html`. Adding a rules-page hero is new surface — verify existing rules-page tests pass when a hero block is inserted ahead of the layout. The TOC list shows the rules-page-only files (achievements, classes, rules, progression, etc.) so the section walk doesn't need restructuring, but the hero injection point does.

2. **Section/file mapping is the trickiest bit.** The bundle's TOC entries (e.g., `bearing`) aggregate content from multiple YAML files (`char_creation.yaml` + `classes.yaml` + `races.yaml`). The current renderer walks files one-per-section. The `TOC_TO_FILES` mapping is the bridge. **If this turns out to be exponentially complex** (which Architect should check before green), defer the multi-file aggregation to a follow-up and emit one section per file with the TOC pointing at `#file-{stem}` — keep this story's diff narrow.

3. **TOC anchors must collide-free with namespaced ids from Task 2.** The bundle uses `id="bearing"`, `id="confrontations"`, etc. Task 2 already namespaces list-of-dict items as `class-knight`, `culture-loyalist`. Verify no Task 2 namespace collides with a TOC top-level id. Quick grep: TOC ids are short keywords (`reckoning`, `bearing`, `edge`, etc.), Task 2 namespaces are `{kind}-{slug}` — no overlap expected, but worth a one-line assertion in the wiring test.

4. **`victoria` is in the bundle but may not be a live pack.** Check `sidequest-content/genre_packs/` — if `victoria` is absent, skip its entry in `PACK_*` tables; if present, include. Either way, no live-pack coupling in tests.

5. **The Cloudflare Access gate** on production means CI can't smoke-test the deployed pages directly. The wiring test (Task G) is the last automated stop; production verification (AC12) is Keith opening the URL.

6. **`v3 plan Task 27` is 63-5's territory** — that's the full validator CLI. This story does the minimum wiring test to guard against the *specific* drift 63-4 produced; the broader validator stays with 63-5.

---

## Plan Anchors (line references for fast lookup)

| Plan section | Lines | What it specifies |
|---|---|---|
| Page wrapper in `_wrap_document` | 2627–2644 | `<div class="page">{body}</div>` |
| Hero markup | 2674–2685 | Full 5-element hero structure with classes |
| Hero rendering rules | 2688–2734 | Loader extension, fallback semantics, escape rules |
| `PACK_LABELS` example | 2698–2712 | Heavy_metal, space_opera, victoria, … |
| Layout + TOC markup | 2750–2801 | `<div class="layout"><aside class="toc-sticky">…</aside><main>…</main></div>` |
| `PACK_TOC` shape | 2765–2778 | Per-pack numerals + section labels |
| Observer script | 2807–2828 | Verbatim port from `app.jsx` |
| `_KIND_OVERRIDES["factions"]` | 2832–2839 | Lore-tier list-of-dict namespacing |

---

## Handoff

**To TEA** for RED phase. Test-design priorities:

1. **Wiring test first** (Task G). The whole point of this story is to establish a regression guard that catches 63-4's failure mode.
2. **Per-AC hero/TOC structural tests** against the fixture pack: assert each of the 5 hero elements present with correct class, assert layout grid wraps TOC + main, assert TOC links resolve to `<section id="{toc.id}">` wrappers.
3. **Loud-on-missing tests** for the new `sidequest.reference.toc_missing` span path.
4. **Vacuous-test scrub** of 63-4's existing chrome tests. Mark any that survive only by being trivially true ("the string 'page' appears somewhere in the HTML") for deletion or replacement with a real structural assertion.
