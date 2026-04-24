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
implementation-status: drift
implementation-pointer: 87
---

# ADR-043: Conlang Morpheme System

> Retrospective — documents a decision already implemented in the codebase.

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
