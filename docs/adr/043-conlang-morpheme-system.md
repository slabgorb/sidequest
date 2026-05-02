---
id: 43
title: "Conlang Morpheme System"
status: accepted
date: 2026-04-01
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [npc-character]
implementation-status: retired
implementation-pointer: null
---

# ADR-043: Conlang Morpheme System

> Retrospective at write-time (2026-04-01) — documented an implementation already live in the Rust era. The implementation did not survive the 2026-04 port to Python and production has since chosen a different naming approach. See _Implementation status_ below.

## Context
SideQuest generates proper nouns at runtime — NPC names, place names, faction names — that must feel like they belong to the same invented world. Naive random syllable generation produces names that are stylistically incoherent: "Zrath" and "Bumble" feel like different worlds. Pre-authored name lists are finite and don't scale across genre packs. LLM-generated names are expensive and inconsistent across sessions (the same village gets a different name on reload). The system needed generative names with implicit morphological coherence — names that share roots because they share meaning.

## Decision
Genre packs declare a `MorphemeGlossary` in YAML: a collection of morphemes (roots, prefixes, suffixes, particles) each carrying a meaning and pronunciation hints. A `NameGenerator` combines morphemes using seeded RNG (`StdRng::from_seed`) to produce proper nouns that share roots where they share conceptual ground.

```yaml
# Example genre pack morpheme declaration
morpheme_glossary:
  roots:
    - form: "zar"
      meaning: "fire"
      pronunciation: "ZAHR"
    - form: "keth"
      meaning: "place"
      pronunciation: "KETH"
  suffixes:
    - form: "oth"
      meaning: "person/being"
      pronunciation: "OTH"
```

With this glossary, "Zar-keth" (fire-place) and "Zar-oth" (fire-being) both carry the "zar" root — world-building coherence emerges from the morpheme pool without any LLM involvement. The seeded RNG guarantees the same genre pack produces the same name for the same entity across sessions.

Morpheme types — roots, prefixes, suffixes, particles — each contribute to name structure differently. Names are structurally consistent within a genre but distinct across genres (each genre pack has its own glossary).

Implemented in `sidequest-game/src/conlang.rs` (902 LOC).

## Alternatives Considered

- **LLM-generated names** — Inconsistent across sessions, expensive per call, and Claude will contradict its own earlier names without access to a name registry.
- **Random syllable soup** — Produces names that feel random rather than invented. No morphological coherence.
- **Pre-authored name lists** — Finite. Doesn't scale across genre packs. Requires manual curation per genre.

## Consequences

**Positive:**
- Names feel like they belong to the same language without any LLM cost.
- Seeded RNG gives session-stable names — the village is always "Zar-keth".
- New genre packs get a name generator for free by declaring a glossary.
- Morpheme meanings can surface in-game ("zar means fire in the old tongue") without additional data.

**Negative:**
- Glossary authoring is a new skill required of genre pack authors.
- Morpheme combination can produce awkward phoneme clusters if glossary is poorly designed.
- The 80GB hardware-specific seed assumption means name reproducibility is glossary-dependent — changing the glossary changes all names.

## Implementation status (2026-05-02)

The Rust era (`sidequest-api/crates/sidequest-game/src/conlang.rs`, 1015 LOC) implemented this ADR in full. The 2026-04 port to Python did not carry it forward. **Production has since chosen a different naming approach** rather than restoring morpheme glossaries:

- `sidequest/cli/namegen/namegen.py` generates names via **Markov chains + mad-libs patterns + culture corpora** (per the file's own docstring).
- Genre packs ship a `corpus/` directory and `cultures.yaml` per culture; cultures bind to source corpora that the Markov generator samples from.
- The pennyfarthing `conlang` agent is built around _"corpus word lists, culture-to-corpus bindings"_ — explicitly the culture-corpus model, not morpheme glossaries.
- Zero occurrences of `MorphemeGlossary` / `morpheme` across all four repos (server, content, daemon, ui). No genre pack ships morphemes.

The SOUL-level goal of this ADR — names that share roots because they share conceptual ground — is met by the corpus model: corpora are curated per culture, so names sampled from them inherit phonetic/morphological coherence without an explicit morpheme abstraction.

**Status:** `implementation-status: retired`. ADR-087's P3 "RESTORE" verdict for this ADR was written assuming namegen was unwired; that assumption no longer holds. A successor ADR documenting the culture-corpus + Markov approach is queued; on its acceptance this ADR's `status` field will move to `superseded` with `superseded-by` pointing at it. Until then the decision recorded here is preserved as historical reference.
