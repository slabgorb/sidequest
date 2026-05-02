---
id: 91
title: "Culture-Corpus + Markov Naming"
status: accepted
date: 2026-05-02
deciders: ["Keith Avery", "Leonard of Quirm (Architect)"]
supersedes: [43]
superseded-by: null
related: [3, 4, 7, 22]
tags: [npc-character, code-generation]
implementation-status: live
implementation-pointer: null
---

# ADR-091: Culture-Corpus + Markov Naming

> Retrospective. Documents the naming approach in production today and supersedes [ADR-043](043-conlang-morpheme-system.md) (Conlang Morpheme System), whose Rust-era implementation did not survive the 2026-04 port and whose design was actively replaced rather than restored.

## Context

ADR-043 specified runtime name generation via `MorphemeGlossary` — genre packs would declare roots/prefixes/suffixes/particles with meanings, and a `NameGenerator` would combine morphemes using seeded RNG to produce proper nouns sharing roots where they shared conceptual ground. That approach was implemented in the Rust era (`sidequest-api/crates/sidequest-game/src/conlang.rs`, ~1015 LOC) and was the canonical naming system at write-time of ADR-043 (2026-04-01).

The 2026-04 port to Python (ADR-082) did not carry forward `conlang.rs`. Production has since taken a different path with its own running implementation, infrastructure, and content footprint. This ADR documents that path and retires ADR-043's morpheme-glossary design.

## Decision

**Names are generated via culture-bound text corpora trained into character-level Markov chains and assembled by genre-authored templates.** Three layers:

1. **Genre packs ship `corpus/` directories** containing `.txt` files of source text per culture or naming domain (e.g. `caverns_and_claudes/corpus/surface_folk.txt`). Corpora are real-language (English, Spanish, Latin, etc.) or hand-curated word lists; the Markov chain abstracts away which.
2. **Genre packs declare cultures in `cultures.yaml`.** Each `Culture` carries a dict of `slots` (e.g. `given_name`, `surname`, `noun`, `keeper_name`); each slot binds to one or more corpora with weights, an optional static `word_list` fallback, and a `lookback` order (2 or 3) for the Markov chain. A culture also carries `person_patterns` and `place_patterns` — mad-libs templates that reference slots, e.g. `"{given_name} {surname}"`, `"The {noun} of {abstract}"`.
3. **The runtime samples slots and assembles names.** `sidequest/genre/names/` (`markov.py`, `generator.py`, `thresholds.py` — ~604 LOC) trains chains from culture-bound corpora at first use, samples each slot per pattern, and post-filters the resulting name through a stem-collision check before emission.

The character-level Markov implementation in `markov.py` is adapted from Keith Avery's *fantasy-language-maker* (2011–2024) and predates SideQuest. The reuse is intentional: a vetted name generator is more valuable than a bespoke one.

### What "culture coherence" means in this model

ADR-043's morpheme model achieved coherence through **explicit shared roots** — names containing `zar` clustered around fire-things. The corpus model achieves coherence through **implicit phonemic distribution**: a chain trained on Latin produces names that share Latin's letter-transition statistics whether or not any two names overlap on substrings. Cultural identity emerges from corpus selection, not from a morpheme dictionary.

When two names from one culture happen to share a substring (e.g. `Vaal-Kesh` and `Vaal-Tor`), it is intentional in-culture coherence — the same phonotactic rules surfacing the same chunk twice. This is the inverse of the *cross-name* artifact `has_stem_collision` exists to reject ("Frandrew Andrew"), which is the chain echoing within a single name.

### Slot generation

Each `CultureSlot` may declare `corpora: list[CorpusRef]` (corpus name + weight), `word_list` (static fallback or hand-curated list), `lookback` (Markov order), and `reject_files` (banned words). At sample time, `SlotGenerator.generate()` blends sources:

- Both Markov and word-list present: 67 % chain / 33 % list.
- Only Markov: chain only.
- Only word-list: list only.

This keeps high-flavor static names (e.g. authored `keeper_name` lists) in rotation alongside generated names, instead of forcing the genre pack author to choose one or the other.

### Pattern assembly

`person_patterns` and `place_patterns` are mad-libs strings interpolated against generated slot values. A culture can carry many patterns; the runtime picks one. Patterns may include free literals (`"de"`, `"Square"`, `"The"`) which are preserved through title-casing via the `small_words` set in `_titlecase_name`.

### Corpus health guards (`thresholds.py`)

A corpus below `FAIL_BELOW_WORDS` raises and emits `namegen.fail_loud`; a corpus below `WARN_BELOW_WORDS` warns and emits `namegen.thin_corpus`. Names that pass generation but fail `has_stem_collision` emit `namegen.stem_collision`. Sebastien sees these on the GM panel; the operator sees them on stderr. This is the OTEL lie-detector pattern from CLAUDE.md applied at the naming layer.

### What gets retired with ADR-043

- `MorphemeGlossary` and the morpheme/root/prefix/suffix/particle data model.
- The `NameGenerator` rooted in morpheme combination.
- The implication that genre pack authors must learn morpheme authoring as a new skill — corpus curation is the live skill instead, supported by the pennyfarthing `conlang` agent (named for historical reasons; the agent is corpus-focused).

### What stays from ADR-043's spirit

- Generative rather than enumerated: corpora and chains scale; pre-authored name lists do not.
- Session-stable when seeded: the same `random.Random` seed produces the same names. (`SlotGenerator.rng` and `MarkovChain.rng` accept injection.)
- Genre-distinctive: each genre's corpora produce a recognizable phonemic palette without LLM cost.

## Alternatives Considered

- **Restore the morpheme glossary** — proposed by ADR-087's P3 RESTORE verdict for ADR-043, written before the Markov+corpus approach was audited. With ~604 LOC of working Python, content authors trained on corpus curation, three OTEL guards, and a per-culture pattern grammar already shipping in every genre pack, restoring morphemes would mean **demoting a working system** to bring back a parallel one with no clear advantage. Rejected.
- **LLM-generated names** — rejected (still): inconsistent across sessions, expensive per call, contradicts itself without a registry.
- **Pre-authored name lists only** — rejected: finite, doesn't scale across genres. Retained as a *fallback* via `CultureSlot.word_list` for high-flavor cultures (Keeper Titles, hireling names) where a hand-curated list reads better than chain output.

## Consequences

**Positive:**

- Names share phonemic identity per culture without any LLM cost.
- The system is already in production across every shipped genre pack — no migration risk.
- Stem-collision filter and corpus-size guards are real OTEL signals, not aspirational.
- Mad-libs patterns let a culture mix Markov-generated and hand-curated tokens in one name (e.g. `"{given_name} de {surname}"` where one slot is chain and the other is list).
- Adding a culture is an authoring task: write a `cultures.yaml` block + drop a `.txt` file. No code change.

**Negative:**

- A culture's "feel" depends on its corpus. Bad corpus → bad names; the pennyfarthing `conlang` agent exists in part to keep this curation honest.
- Real-language corpora can produce real-language words instead of fantasy ones (`reject_files` is the escape hatch; the chain's `reject_words` set excludes them).
- ADR-043's morpheme-meaning surface ("zar means fire in the old tongue") is gone. The chain has no semantic layer. If a future feature needs morpheme-level meaning (e.g. an in-game etymology aside), it has to be authored, not generated.

## References

- [ADR-043: Conlang Morpheme System](043-conlang-morpheme-system.md) — superseded by this ADR.
- [ADR-087: Post-Port Subsystem Restoration Plan](087-post-port-subsystem-restoration-plan.md) — its P3 RESTORE verdict for ADR-043 is obsoleted by this ADR.
- `sidequest-server/sidequest/genre/names/markov.py` — character-level Markov chain.
- `sidequest-server/sidequest/genre/names/generator.py` — slot generator + culture builder + stem-collision filter.
- `sidequest-server/sidequest/genre/names/thresholds.py` — corpus health guards.
- `sidequest-server/sidequest/genre/models/culture.py` — `Culture` / `CultureSlot` / `CorpusRef` data model.
- `sidequest-content/genre_packs/*/cultures.yaml` — culture declarations per genre pack.
- `sidequest-content/genre_packs/*/corpus/` — text corpora per genre pack.
- `~/Projects/orc-penny/pennyfarthing/.../conlang.md` — the `conlang` content agent (corpus curation).
