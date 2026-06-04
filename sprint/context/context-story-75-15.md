---
parent: context-epic-75.md
workflow: tdd
---

# Story 75-15: RAG starve — creation-seed fragments lost on resume + sub-floor embedding similarities (gulliver 2026-06-02)

> Source: sq-playtest ping-pong BUG "RAG / lore retrieval is effectively dead — near-empty
> corpus, nothing persisted, similarities below the floor" (wry_whimsy/gulliver, session
> `2026-06-02-gulliver`, 36 turns). Found by Keith + Dev (Naomi). FIXER (Ponder Stibbons)
> triaged it 2026-06-04 as **design-first** — NOT an inline patch.

## Business Context

Across a 36-turn gulliver run the RAG injected ~nothing into the narrator prompt: every
`narrator.sdk_path.context_wired` line logged `lore_fragments=3` (turns 19–35). The
narration's continuity was coming from Claude's own knowledge of *Gulliver's Travels* + the
recency window, **not retrieval**. Epic 75 already established the lore RAG fires every turn
and 75-1 restored runtime accretion — yet this session shows the index still starved. That
makes this either a regression against 75-1's "done" state or a second, distinct starvation
path. Either way, the RAG looks wired (telemetry fires) but is **functionally inert**, which
is the worst failure class for the OTEL principle: the lie-detector says "retrieval ran"
while nothing was actually retrieved.

Two engine causes (the FIXER explicitly de-scoped the third, content-authoring, cause as
the least load-bearing — see Scope Boundaries):

1. **Persistence write-through is missing (load-bearing).** A `character_creation_seed`
   event reports `fragments_added=17, total_fragments=20`, but every resume emits
   `rag.lore_store_loaded` with `total_fragments=3` and `reason: slug_resume_reseed` — the
   17 creation-seed fragments are **lost on resume**. The `lore_fragments` Postgres table
   has **0 rows** for the session. The ADR-048 cross-process store is in-memory-only and is
   never written through to Postgres for these fragments.
2. **Embedding / threshold starves retrieval (load-bearing).** Of 36 `lore_retrieval`
   events, 18 returned `selected_count=0`. The **highest cosine similarity recorded across
   the entire session was 0.1499** — *below* the `min_similarity: 0.15` floor. Scores
   cluster at 0.02–0.17 (near-orthogonal). That smells like a degenerate / hash-fallback
   embedding (a No-Silent-Fallback question: is the **real** MiniLM model actually loaded,
   or did something fall back to a hash embedder?) and/or a floor mis-tuned for these long
   (362–383-token) fragments.

## Technical Guardrails

**This is design-first.** Confirm the root cause with measurement before patching, and if
the embedding turns out to be a degenerate fallback, the fix is "fail loud / load the real
model," not "lower the floor until something matches." If the work reveals a design change
(new persistence path, ADR-048 amendment, retrieval-floor doctrine), raise it as a Design
Deviation and route the design to the Architect (Neo).

**Seams (verify before editing):**
- `sidequest/game/lore_store.py` — the RAG store + `query_by_similarity`; the
  `rag.lore_store_loaded` / `slug_resume_reseed` path lives around resume hydration.
- `sidequest/game/lore_seeding.py` — creation-seed + world/genre fragment seeding (the
  `fragments_added=17` creation-seed path).
- `sidequest/game/lore_embedding.py` — the embedding call (MiniLM 384-dim via daemon per
  the epic-75 finding); verify the real model is loaded and that 75-1's per-turn accretion
  is actually persisting.
- `sidequest/game/pg/sessions.py` (and the `lore_fragments` table DDL under
  `alembic/`) — where fragments must be written through and re-read on resume.
- `sidequest/game/retrieval_orchestration.py` + `sidequest/handlers/connect.py` — the
  resume bootstrap that currently reseeds to the 3 static fragments.

**Two independently-shippable threads (either can be the first AC):**
- **Persistence:** creation-seed (and runtime-accreted) fragments must survive resume —
  written through to `lore_fragments` and re-hydrated on connect, so `total_fragments` after
  resume reflects what was seeded/accreted, not the 3 static ones. Cross-check against 75-1
  (is this a regression in that path, or a separate creation-seed path 75-1 didn't cover?).
- **Embedding/floor:** instrument the actual embedding — confirm the loaded model and vector
  norms (a No-Silent-Fallback assertion that it is NOT a hash fallback). If the model is
  real and similarities are genuinely sub-floor for long fragments, the design question is
  fragment granularity vs floor calibration (finer fragments match short action context
  better than 380-token essays) — coordinate with the content-authoring sub-cause below.

**OTEL (mandatory):** the existing `rag.lore_store_loaded` / `lore_retrieval` spans are the
evidence surface — extend them so the GM panel can answer the exact questions this bug
raised: how many fragments persisted vs reseeded, what model produced the embedding, and the
peak similarity vs the floor per turn. A retrieval that selects nothing should be legible as
"nothing cleared the floor" vs "store was empty."

## Scope Boundaries

**In scope:**
- Persist creation-seed + runtime-accreted lore fragments through to `lore_fragments` and
  re-hydrate them on resume (kill `slug_resume_reseed`-to-3).
- Diagnose + fix the embedding/threshold starvation: confirm the real embedding model is
  loaded (fail loud if not), and resolve the sub-0.15 similarity problem (model fix and/or
  floor calibration and/or fragment granularity decision).
- OTEL extensions that make persisted-vs-reseeded and similarity-vs-floor legible.
- Behavioral tests: a seed→resume→retrieve cycle that asserts fragments survive resume; an
  embedding test asserting the real model (non-degenerate vectors) and that a relevant
  fragment clears the floor.

**Out of scope (explicitly de-scoped by the FIXER):**
- **Authoring finer `wry_whimsy` genre/world lore fragments** — this is the third,
  least-load-bearing cause (content lane). Authoring corpus alone would NOT fix retrieval
  while the floor/embedding starve it, so a content-only pass would look done while staying
  inert. Flag it as a separate content task if granularity turns out to be part of the
  embedding fix, but it is not this engine story.
- The universal-retrieval ratification work (75-11..75-14) — different thread of epic 75.
- Quest/stakes durable memory (epic 77) — sibling memory gap, different subsystem.

## AC Context

1. **Fragments survive resume.** After seeding (creation-seed `fragments_added>0`) and a
   resume, `lore_fragments` holds the seeded rows and the store re-hydrates to the seeded
   total — NOT the 3 static fragments (`slug_resume_reseed`-to-3 is gone). Proven by a
   seed→resume→inspect test + the `rag.lore_store_loaded` span.
2. **Real embedding, no silent fallback.** A test asserts the production embedding path uses
   the real model (non-degenerate vectors); if the model can't load, the system fails loud
   rather than hash-falling-back.
3. **Relevant lore clears the floor.** For a fragment relevant to a turn's action context,
   the recorded cosine similarity is at/above the floor and the fragment is selected —
   demonstrated on a representative case (the gulliver session's sub-0.15 ceiling is
   resolved, whether by model fix, floor calibration, or granularity).
4. **Retrieval injects lore.** A driven turn shows `lore_fragments` > the static 3 reaching
   the narrator prompt when relevant lore exists.
5. **OTEL legibility.** Spans distinguish "store empty" from "nothing cleared the floor" and
   surface persisted-vs-reseeded counts + the embedding model + peak-similarity-vs-floor.
6. **Wiring tests.** Fixture-driven behavioral tests through the real seed/persist/retrieve
   path (+ span assertions), not source-text greps. Cross-check 75-1 to confirm whether this
   is a regression in that path or a distinct creation-seed gap, and note it in the PR.
