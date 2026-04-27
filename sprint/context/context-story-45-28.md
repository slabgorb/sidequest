---
parent: sprint/epic-45.yaml
workflow: wire-first
---

# Story 45-28: Markov namegen min-pool guard + thin-corpus audit

## Business Context

**Playtest 3 evidence:** the Markov namegen produced "Frandrew Andrew" —
a degenerate output where the prefix and suffix collapse onto the same
stem. The classic too-small-corpus signature: when the trained transition
table doesn't have enough alternatives at a given context, the chain
loops back through the same characters, and the output reads as the
training word repeated rather than a novel name. Two players with
"Andrew" stems on the same corpus, neighbouring NPCs called "Frandrew
Andrew" and similar variants — a tell to anyone paying attention, and a
break in the genre spell to everyone else.

This is **a SOUL.md / Genre Truth issue, not a cosmetic bug.** Names are
the load-bearing surface for invented worlds — Sebastien notices the
mechanical artifact, James and Keith feel the broken texture. Cf.
ADR-043 (Conlang Morpheme System), which exists *precisely* because
"naive random syllable generation produces names that are stylistically
incoherent." Markov-on-source-language is a parallel pathway with the
same goal — phonemic coherence — and the same failure mode if its
corpus is too thin.

The actual on-disk evidence (audited 2026-04-27):

```
sidequest-content/genre_packs/space_opera/corpus/
  english.txt    130,074 words / 12,501 lines
  finnish.txt    100,144 words / 20,974 lines
  japanese.txt    98,677 words / 10,316 lines
  russian.txt    566,337 words / 66,041 lines
  spanish.txt    389,656 words / 38,059 lines
  georgian.txt       325 words /    325 lines  ← THIN
  latin.txt          340 words /    340 lines  ← THIN
  polynesian.txt     309 words /    309 lines  ← THIN
```

The three thin corpora are exactly the source pool for `aureate_span`'s
named cultures (`sidequest-content/genre_packs/space_opera/worlds/aureate_span/cultures.yaml`):

- **Span Aristocracy** → latin.txt (340) + spanish.txt
- **Vaal-Kesh** → polynesian.txt (309) + finnish.txt
- **Makhani** → georgian.txt (325) + russian.txt

Two of the three Aureate Span cultures are sampling from a 309-or-340-
word pool. Markov chain at lookback=2 over 309 words has, at best, a few
hundred unique two-character contexts — many with a single child
character. That's the structural cause of "Frandrew Andrew": the chain
walks deterministic paths back to root stems.

Audience: every player. Bad names break the spell across the entire
playgroup. Keith's career-GM bar — "good enough to fool a career GM" —
is failed instantly by a name that reads like a Markov artifact. This
is a P2 in the tracker because it doesn't gate gameplay, but it is
high-touch for genre buy-in.

## Technical Guardrails

### The wire-first seam (gate-blocking)

The wire-first gate requires the test to exercise the actual
**culture lookup → corpus load → MarkovChain training → SlotGenerator
sample** path, not a unit test on a pure threshold check. Two seams:

1. **Corpus-load seam** —
   `sidequest/genre/names/generator.py:127` `build_from_culture(culture,
   corpus_dir, rng, chain_cache)`. This is where each culture's slot
   configurations resolve to corpus files (line 173 onward iterates
   `slot_config.corpora`, opens each `corpus_path`, and calls
   `chain.train_file(text)`). The min-pool guard lands here, after the
   text is read but before training: count words/lines in the corpus
   text, fail loud (warn + OTEL + raise on hard floor) when below the
   configured threshold. The "fail loud" emission MUST happen even when
   the chain still produces output — silent degradation is exactly the
   bug.
2. **Sample-output seam** — `sidequest/cli/namegen/namegen.py:588-597`
   loops up to 10 attempts on `generator.generate_person()`. The
   "no identical prefix and suffix stems" guard lands here as a
   rejection check, with a fallback path when the loop exhausts: emit
   `namegen.stem_collision` OTEL events on each rejection,
   `namegen.fail_loud` on exhaustion.

The wire-first test must call through `build_from_culture` and
`generate_person` with a real (or fixture) culture YAML and a thin
corpus, asserting (a) the warn span fires, (b) the rejection check
catches stem collisions before they reach the caller, (c) when the
corpus is below a hard floor, an exception is raised rather than a
degenerate name returned.

### Two thresholds, not one

To distinguish "thin but usable" from "unusably small", define two
constants. Per CLAUDE.md "no silent fallbacks" and ADR-068 magic-literal
discipline, they live in a single module
(`sidequest/genre/names/thresholds.py` or extend the existing
`sidequest/game/thresholds.py`):

- `WARN_BELOW_WORDS = 1000` — corpus is thin enough that stem-collisions
  are likely; emit `namegen.thin_corpus` OTEL event but allow
  generation to proceed. `latin.txt`, `polynesian.txt`, `georgian.txt`
  all hit this today.
- `FAIL_BELOW_WORDS = 200` — corpus is so thin that the Markov chain
  cannot produce coherent output without near-verbatim regurgitation;
  emit `namegen.fail_loud` OTEL event AND raise
  `ValueError(f"Corpus '{name}' has {n} words; minimum is
  {FAIL_BELOW_WORDS}")`. None of the current corpora hit this; the
  threshold exists to prevent a future copy-paste regression.

The 1000/200 numbers are calibrated against the Markov literature
heuristic (a lookback-2 chain wants ~10× the unique-prefix count for
non-degenerate output; English ~50 phonemic two-grams × 10 ≈ 500 word
floor for genuinely random output; doubled to 1000 for safety) and
against the on-disk distribution (the three thin corpora cluster around
300, well clear of 200; the production corpora are all >50× the warn
floor). Subject to playtest tuning.

### Existing reuse points

- **`MarkovChain`** (`sidequest/genre/names/markov.py:24`) — the
  trained chain itself. Add a `word_count` property or a separate
  counter passed through `build_from_culture` so the threshold check
  doesn't re-read the file. Do NOT add a guard inside `make_word()`
  — it's called per-character, far too hot a path for a guard.
- **`build_from_culture`** (`sidequest/genre/names/generator.py:127`)
  — already reads corpus text into `chain_cache` (line 181). Add a
  `_count_words(text)` step there, attach the count to the chain or
  to the returned `SlotGenerator`, and apply the threshold check
  before returning.
- **`SlotGenerator`** (`sidequest/genre/names/generator.py:20`) —
  generic slot, has the chain handle. Could carry a `corpus_size`
  attribute for diagnostics. Optional.
- **`generate_person`** loop in `cli/namegen.py:589-597` — already has
  a 10-attempt rejection loop for `of /the` prefixes. Extend it with
  the prefix==suffix stem check.

### OTEL spans (LOAD-BEARING — gate-blocking per CLAUDE.md OTEL principle)

Three new spans, registered in `SPAN_ROUTES`. Define constants in
`sidequest/telemetry/spans.py` near the existing
`SPAN_GAME_HANDSHAKE_DELTA_APPLIED` block (line 331) for symmetry.

| Span | When | Required attributes |
|------|------|---------------------|
| `namegen.thin_corpus` (NEW `SPAN_NAMEGEN_THIN_CORPUS`) | corpus loaded, word count < `WARN_BELOW_WORDS` | `corpus_name`, `word_count`, `culture`, `slot_name`, `threshold` |
| `namegen.fail_loud` (NEW `SPAN_NAMEGEN_FAIL_LOUD`) | corpus < `FAIL_BELOW_WORDS` (raises) OR generate-loop exhausts after stem-collision rejections | `corpus_name`, `word_count`, `culture`, `slot_name`, `reason` (`"below_floor"` or `"stem_collision_exhausted"`) |
| `namegen.stem_collision` (NEW `SPAN_NAMEGEN_STEM_COLLISION`) | a generated candidate has identical prefix and suffix stems and is rejected | `culture`, `candidate`, `prefix_stem`, `suffix_stem`, `attempt_index` |

`SPAN_ROUTES` registration: `event_type="state_transition"`,
`component="namegen"`, `field="corpus"`, with `op` differentiated per
span. Follow the pattern at `sidequest/telemetry/spans.py:332`.

`logger.warning(...)` SHOULD also emit on `thin_corpus` for stdout
visibility (CLI users won't be tailing OTEL); the OTEL event remains the
canonical lie-detector signal.

### Stem-collision predicate

"Identical prefix and suffix stems" needs an operational definition,
because the playtest "Frandrew Andrew" example is more nuanced than
exact equality:

- **Operational definition for the AC:** strip whitespace and
  case-normalize each space-separated token, compute the longest common
  *substring* of length ≥ `STEM_OVERLAP_MIN = 4`. If the substring spans
  more than half of either token, reject.
- **"Frandrew Andrew"** → tokens `frandrew`, `andrew`; LCS `andrew`
  length 6 covers 100% of token 2 and 75% of token 1 → reject.
- **Deliberately allowed:** culturally-coherent stem reuse like
  "Vaal-Kesh / Vaal-Tor" (intentional morphological coherence, ADR-043
  case) is *between separate names*, not within a single name's tokens.
  The predicate operates on tokens within one generated person-name.

The operational definition lives in a single helper, exported from
`sidequest/genre/names/generator.py`, so the test and the production
loop call the same function.

### Audit script — wire-first applied to content

The story description's AC (a) is "audit corpus word-list sizes per
culture; flag any below threshold." This is wire-first applied to
content: the audit script must hit the actual culture-loading path
(`sidequest.genre.load_genre_pack`) and emit a per-culture report. The
script lands at `sidequest-server/scripts/audit_namegen_corpora.py`,
modeled on `sidequest-server/scripts/audit_content_drift.py` (already
present for trope drift). It:

1. Walks `SIDEQUEST_GENRE_PACKS` (or `--path`).
2. For each genre pack, loads the pack and its worlds (so it sees both
   genre-tier and world-tier cultures, the same dual lookup that
   `cli/namegen/namegen.py:524-535` does).
3. For each culture, resolves each slot's `corpora`/`names_file` to disk
   paths and counts words.
4. Emits a markdown report with three sections: OK (≥ warn), THIN (warn
   ≤ x < fail), FAIL (< fail). Exit code is `1` if any FAIL, `0` if
   only THIN/OK — so CI can gate on it.

Per the "in scope" note in the description, the audit ALSO drives the
content expansion (point c): every culture flagged THIN under
`aureate_span` gets its source corpus expanded to ≥ `WARN_BELOW_WORDS`
in this story. This is content work, not just code work — the
`repos: server,content` setting on the story acknowledges that.

### Test files (where new tests should land)

There is currently **no namegen test file at all** — confirmed via
`grep -l "build_from_culture\|MarkovChain"` over `tests/`. New tests
land at:

- New: `tests/genre/test_namegen_thresholds.py` — unit tests on
  `_count_words`, the stem-collision predicate, and threshold behavior
  against a fixture culture pointing at synthetic 50-word and 1500-word
  text files.
- New: `tests/genre/test_namegen_wiring.py` — wire-first boundary test
  driving `build_from_culture` and `NameGenerator.generate_person`
  with the synthetic thin fixture, asserting the OTEL spans fire and
  the rejection loop catches stem collisions.
- New: `tests/scripts/test_audit_namegen_corpora.py` — invokes the
  audit script against a fixture pack, asserts the markdown shape
  and exit-code semantics.
- New CLI smoke test in `tests/cli/test_namegen.py` (existing dir
  may need creation) — runs `python -m sidequest.cli.namegen` against
  a thin fixture, asserts non-zero exit on `FAIL_BELOW_WORDS`.

## Scope Boundaries

**In scope:**

- Word-count helper + threshold guards in `build_from_culture`
  (`sidequest/genre/names/generator.py:127`).
- Stem-collision predicate + rejection loop in
  `cli/namegen/namegen.py:589-597`.
- Three new OTEL spans (`namegen.thin_corpus`, `namegen.fail_loud`,
  `namegen.stem_collision`) registered in `SPAN_ROUTES`.
- Two new constants (`WARN_BELOW_WORDS`, `FAIL_BELOW_WORDS`,
  optionally `STEM_OVERLAP_MIN`) in a thresholds module.
- New audit script at `scripts/audit_namegen_corpora.py` with
  exit-code-based CI gate.
- Expanded corpora committed to `sidequest-content/`:
  `latin.txt`, `polynesian.txt`, `georgian.txt` each grown to at
  least `WARN_BELOW_WORDS` (1000 words). Source: public-domain text
  in those languages from Wikipedia / Project Gutenberg / similar,
  consistent with the existing corpus provenance.
- Wire-first integration test driving the full
  `build_from_culture → generate_person` path.

**Out of scope:**

- **Replacing Markov with a smarter generator.** ADR-043 (Conlang
  Morpheme System) describes a richer namegen pipeline; this story
  does not switch to it. Markov-on-source-language remains the
  generator for cultures with `corpora:`.
- **Genre-pack culture authoring conventions.** The `cultures.yaml`
  schema (`sidequest/genre/models/culture.py`) is unchanged. New
  fields are runtime-only.
- **Per-culture threshold overrides.** A future story could let a
  culture say "I know my corpus is small, suppress the warn"; 45-28
  ships with global thresholds.
- **Cross-culture stem-collision detection.** The predicate operates
  on tokens within one generated name; it does not check that a new
  name doesn't collide with an earlier-generated name in the same
  session (a separate concern, addressable by the registry).
- **Place-name / faction-name generators.** The Frandrew artifact came
  from `generate_person`; the same chain feeds `generate_place`, but
  the test target is `person` only. The threshold guard at
  `build_from_culture` covers both pathways automatically — that's
  correct and intended — but the AC tests target person names.
- **Reject-list expansion.** `MarkovChain.load_reject_file`
  (`markov.py:137`) already filters dictionary words; not modified.

## AC Context

The four lettered ACs in the description map to numbered tests:

1. **(a) Audit script outputs per-culture sizes and flags thin/fail.**
   - Test: invoke `audit_namegen_corpora.py` against the live
     `sidequest-content/` tree. Assert markdown report contains
     `latin.txt (340 words) — THIN`, `polynesian.txt (309 words) —
     THIN`, `georgian.txt (325 words) — THIN` rows under their
     consuming cultures (Span Aristocracy / Vaal-Kesh / Makhani),
     and OK rows for `english.txt`, `russian.txt`, `spanish.txt`,
     `finnish.txt`, `japanese.txt`. Exit code is 0 (no FAIL).
   - Negative test: invoke against a fixture pack with a 50-word
     synthetic corpus. Assert exit code 1 and a `FAIL` row.

2. **(b) Namegen warns + emits `namegen.thin_corpus` OTEL when corpus
   is below WARN threshold.**
   - Wire-first test: `build_from_culture` with a fixture culture
     pointing at a 300-word synthetic corpus. Assert
     `SPAN_NAMEGEN_THIN_CORPUS` is emitted exactly once per loaded
     thin corpus, with attributes `corpus_name`, `word_count`,
     `culture`, `slot_name`, `threshold` populated.
   - Asserts `SPAN_ROUTES[SPAN_NAMEGEN_THIN_CORPUS]` is registered
     (`component="namegen"`) so the GM panel sees the warning.
   - Hard-floor test: `build_from_culture` with a 50-word corpus
     RAISES `ValueError` AND emits `SPAN_NAMEGEN_FAIL_LOUD` with
     `reason="below_floor"` before raising.

3. **(c) Expanded corpora committed.**
   - Test: assert `wc -w` of `latin.txt`, `polynesian.txt`,
     `georgian.txt` in `sidequest-content/genre_packs/space_opera/corpus/`
     each ≥ `WARN_BELOW_WORDS`. This is a content-shape regression
     test, not a Python-runtime one; lands in
     `tests/scripts/test_audit_namegen_corpora.py` so the same
     script that would catch a future regression also exercises the
     fix.
   - Negative regression: `audit_namegen_corpora.py` exit code on
     the live tree is 0 *and* the report no longer contains any THIN
     row from this story's named corpora.

4. **(d) Unit test asserts no generated name has identical prefix
   and suffix stems.**
   - Test: against a deliberately thin fixture corpus (the type that
     would have produced Frandrew Andrew), call `generate_person`
     1000 times with a seeded RNG. Assert no returned name's tokens
     overlap by `STEM_OVERLAP_MIN` characters or more.
   - Test: feed a corpus that DOES produce stem collisions; assert
     `SPAN_NAMEGEN_STEM_COLLISION` fires for the rejected attempts
     and the final returned name passes the predicate, OR the loop
     exhausts and `SPAN_NAMEGEN_FAIL_LOUD` fires with
     `reason="stem_collision_exhausted"`.
   - Wire-first: scenario calls through
     `cli.namegen.namegen.generate_npc`, not through a stub
     name-only helper. The `Frandrew Andrew` regression must be
     unreproducible end-to-end.
