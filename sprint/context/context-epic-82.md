# Epic 82: Surface the Dark Subsystems — Wire Consumers + OTEL for Overstated ADRs

## Overview

ADRs from the audit's "overstated" bucket whose infrastructure exists and was marked
`implementation-status: live`, but which have **no production consumer** — so by the
project's own wiring doctrine they are not actually live. The active stories give each a
real consumer that reaches the existing infrastructure, plus an OTEL/watcher emission (the
GM panel is the lie-detector: a subsystem that emits nothing can't be proven engaged). Two
ADRs in this bucket turned out to be *abandoned directions* rather than wiring gaps and
were resolved by **deprecation**, not implementation.

**Priority:** P2
**Repo:** sidequest-server + sidequest-ui
**Stories:** 3 active (18 points); 1 resolved-by-decision; 1 dropped

- **82-2** (5) — Verbosity/Vocabulary player controls: UI sliders + CONNECT plumb + TurnContext read (ADR-049) — *server + ui*
- **82-3** (8) — Wire progression tracks 1-3: milestone level-up, affinity tiers, item narrative_weight (ADR-021) — *server; may split*
- **82-4** (5) — Make the four-tier Resolver the production path or narrow ADR-121 (ADR-121) — *server*
- **82-5** (2, **done**) — Reconcile ADR-040 No-Raw-Stats → **deprecated** (decision executed)
- ~~82-1 — /tone ToneCommand (ADR-052)~~ — **DROPPED**: tone is the content author's domain (pack prose/config/world flavor), not an engine command. ADR-052 deprecated.

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| **ADR-vs-Code Audit** (`docs/adr/AUDIT-2026-06-03.md`) | "Overstated" bucket — the five "plumbing live, surface absent" findings with file:line evidence |
| **ADR-052 Narrative Axis System** (`docs/adr/052-narrative-axis-system.md`) | now **deprecated** — context for why `/tone` is not an engine feature (content-author domain) |
| **ADR-049 Narrator Verbosity & Vocabulary** (`docs/adr/049-narrator-verbosity-vocabulary.md`) | two-axis text tuning, player controls, `default_for_player_count` |
| **ADR-021 Progression System** (`docs/adr/021-progression-system.md`) | four progression tracks (only track 4 wired) |
| **ADR-121 Layered Content Resolution** (`docs/adr/121-layered-content-resolution.md`) | `Resolver.resolve_merged` four-tier walk vs the two-tier shim |
| **ADR-040 Narrative Character Sheet** (`docs/adr/040-narrative-character-sheet.md`) | now **deprecated** — context for the 82-5 decision |
| **CLAUDE.md** | "Verify Wiring, Not Just Existence"; "Every Test Suite Needs a Wiring Test"; OTEL Observability Principle; mechanics-first audience (Sebastien/Jade want the math legible — drives 82-3) |

## Background

The 2026-06-03 audit found a recurring "overstated" pattern distinct from the runtime bugs
in Epic 81: subsystems where the *plumbing* is live (loaded, defined, sometimes even
injected into prompts) but **nothing in production drives it from the player/runtime side**.
The narrator prompt has verbosity/vocabulary sections, but no UI lets a player choose and
`TurnContext` hardcodes the defaults. The four-tier `Resolver` exists but the real archetype
path is a two-tier shim. Progression has four tracks but only one is wired.

Two findings in this bucket were not wiring gaps and were **deprecated** instead of built:
ADR-052 (`/tone` narrative axes — tone belongs to the content author, expressed through pack
prose/config/world flavor, not an engine command) and ADR-040 (no-raw-stats — see below).

By the project's wiring doctrine — *"a component isn't live if it isn't imported, the hook
isn't called, or the endpoint isn't hit in production"* — and the user's framing ("no
consumer fails the wire-it test"), these are not `live`. Their frontmatter has been
**downgraded `live` → `partial`** with a pointer to the relevant story until a consumer
lands. Each story's bar for "done" is therefore higher than "the code runs": it must have a
**production consumer**, an **OTEL/watcher emission** so the GM panel can confirm engagement,
and a **wiring test that fails on current code**.

**ADR-040 was different and is already resolved.** Its "fix" would have been to *hide* raw
stats — but that reverses the live mechanics-first direction (players consistently ask for
*more* visibility; Sebastien/Jade want the math; ADR-114 deliberately surfaces HP). It was
deprecated (82-5), not wired.

## Technical Architecture

Each story is integration of an existing component, not new infrastructure. Shared shape:
**find the live-but-unconsumed seam → add the production consumer → emit OTEL → wiring test.**

```
ADR   live-but-unconsumed seam                     consumer to add (this epic)
────  ────────────────────────────────────────    ───────────────────────────────────────
049   _build_verbosity/_vocabulary_section fire,    UI sliders -> CONNECT payload ->
      TurnContext hardcodes defaults                 TurnContext reads them
021   tracks 1-3 are data models only              milestone->level-up, affinity tiers,
      (TODO / P2 / P6 deferred)                      item narrative_weight engines
121   Resolver.resolve_merged = dead code          route prod resolution through it
      prod uses two-tier shim                        (or narrow ADR-121 to the shim)
```
(ADR-052's seam — `pack.axes` loaded but never read — is intentionally left unconsumed:
deprecated, content-author domain.)

**Key files by story (navigate by symbol; 2026-06-03 anchors may drift):**

- **82-2 (049):** `protocol/enums.py` (`NarratorVocabulary.default_for_player_count` missing), `server/session_helpers.py` (~:1167-1168 hardcoded defaults), `handlers/connect.py` (~:1402-1403 None on resume), `agents/orchestrator.py` (`_build_verbosity_section`/`_build_vocabulary_section`), new `sidequest-ui` sliders + CONNECT payload field.
- **82-3 (021):** `genre/models/progression.py` (~:62 level-up TODO; ~:187-221 WealthTier), `game/character.py` (~:55-57,102-103 AffinityState P6), `game/item_catalog_resolution.py` (~:31 narrative_weight P2); player-facing advancement-delta surface (mechanics-first).
- **82-4 (121):** `genre/resolver.py` (~:200-390 `Resolver`/`resolve_merged`), `genre/archetype/shim.py` (~:64-158 two-tier path), `server/websocket_handlers/chargen_mixin.py` (~:391 caller), `protocol/provenance.py`.

**Conventions:** every story emits OTEL/watcher events for the subsystem decision it wires
(OTEL Observability Principle), ships a wiring test that fails on current `develop`, and
navigates by symbol name rather than the line anchors above.

## Cross-Epic Dependencies

**Depends on:**
- None hard. **Coordination with Epic 81:** 82-2 touches `TurnContext` construction
  (`session_helpers.py`) and narrator prompt assembly (`orchestrator.py`) — the same surfaces
  as 81-3 (pacing hint). If both epics run concurrently, expect merge contention there;
  sequence or rebase accordingly.

**Depended on by:**
- None. Sibling epic to 81 (both remediate the 2026-06-03 audit's "built-not-wired" class —
  81 the runtime bugs, 82 the absent consumers).
