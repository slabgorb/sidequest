---
story_id: "84-2"
jira_key: ""
epic: "84"
workflow: "tdd"
---
# Story 84-2: WI-5 Alias resolution + accretion-fed aliases — mention resolves through epithets, promoted entities accrete via 75-1 path

## Story Details
- **ID:** 84-2
- **Title:** WI-5 Alias resolution + accretion-fed aliases — mention resolves through epithets, promoted entities accrete via 75-1 path
- **Points:** 3
- **Jira Key:** (none — Jira not used for this project)
- **Workflow:** tdd
- **Stack Parent:** 84-1 (unified pertinence scorer)
- **Repos:** sidequest-server

## Workflow Tracking
**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-06-05

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-05 | - | - |

## Scope

### Context

84-2 extends **84-1** (unified pertinence scorer) to harden the `mention` signal by resolving player actions through **aliases/epithets**, not name-match only.

**Current state (84-1):**
- The pertinence scorer (`sidequest/game/pertinence.py`) computes a unified weighted score: `score = w_mention·mention + w_location·here + w_recency·recency + w_sim·cosine`
- The `mention` signal is currently **name-match only** — a player saying "Borin" → name matches → mention=1.0
- **84-1's seam:** `retrieval_orchestration.py` line 300-303 explicitly documents the gap: *"Mention is name-match only for now (WI-5/84-2 adds aliases); the seam is `player_referenced_npcs` flowing in from the caller's word-bounded match."*
- 84-1 passed `mention=1.0 if player_referenced_npcs else 0.0`, gating entirely on the word match from the turn action text

**Goal (84-2 — WI-5):**
Extend `mention` to resolve through **aliases and epithets**, so:
- "the old man" → resolves to Thorn (if Thorn has alias "old man")
- "the Baron" → resolves to House Medici (if "Baron" is in the epithets)
- Off-name references win retrieval just like canonical names do
- **Accretion-fed:** entities that are promoted (via the 75-1 path) accrete aliases from their promotion journey, and those aliases feed back into the mention resolver

### Key Dependencies & Concepts

**ADR-118 §A4 (Alias-aware, accretion-fed mention):**
- `mention` resolves through each card's **aliases/epithets**, not raw player tokens
- World-authored entities carry aliases in YAML; promoted/yes-and entities accrete epithets via the **75-1 accretion path** — mention-matching gets smarter the longer the campaign runs, with no new pipeline
- Without this, the dominant signal degrades to keyword matching

**The 75-1 accretion path (Epic 75, done):**
- Story **75-1** (restore runtime lore accretion): Runtime narrator-discovered facts are written as embedded, retrievable lore fragments each turn — the accretion loop feeds discovered lore back into the RAG
- The concept extends: when an entity is **promoted** (e.g., a narrator-invented NPC becomes mechanically significant), it should **accrete aliases/epithets** from the narration that led to its promotion
- **75-1 implements the embedding pipeline** (`lore_accretion.py`, `accrete_facts_to_lore`); **84-2 reuses that pipeline** for entity aliases

**Entity Index (Epic 76):**
- Stories 76-6 (stateful NPC projector) and 76-7 (faction/location source coverage) populate the entity store
- 84-1 depends on these to have an index to retrieve from
- 84-2 extends that index by enriching entity cards with **alias metadata**

### Technical Approach

**1. Add alias field to Npc (promotion target)**

`Npc` (stateful; `sidequest/game/session.py`) likely needs an `aliases: list[str]` field to accumulate epithets during a session. This is where accretion writes — **check if the field exists; if not, add it as a migration + schema update**.

**2. Extend entity_card.py projectors to capture aliases**

When projecting an NPC to an `EntityCard` (in `project_npc_card`), include aliases in the card's metadata so the mention resolver can access them:

- `EntityCard.metadata["aliases"]` = comma-separated aliases or JSON list
- Reproject deterministically (same aliases → same content every time)

**3. Implement alias-aware mention resolution**

Modify the mention signal calculation in `retrieval_orchestration.py` (around line 302-303):

**Before (84-1):**
```python
mention=1.0 if player_referenced_npcs else 0.0,
```

**After (84-2):**
```python
# Resolve player action through both names and aliases
mention_strength = resolve_mention_through_aliases(
    action=action_text,
    candidates=cards_by_id.values(),
    # Reuse the word-bounded `player_referenced_npcs` as fallback
    player_referenced_npcs=player_referenced_npcs,
)
# ... later in the signals loop:
mention=mention_strength,
```

**4. Implement `resolve_mention_through_aliases(action, candidates, fallback)`**

Likely lives in a new helper or in `pertinence.py`. Logic:

1. For each candidate card, extract aliases from `card.metadata.get("aliases", "")`
2. Split into a set of alias tokens
3. Tokenize the action text (reuse existing word-boundary matching)
4. Score each candidate: does any alias token match a word in the action?
5. Return best match strength (1.0 if high confidence, scaled down if fuzzy)
6. Fallback: if no alias matches, use the original `player_referenced_npcs` logic (canonical name match)

**5. Accretion path (emit aliases when an entity is promoted)**

**Check:** Where are NPCs promoted in the codebase? (This is the 75-1 path equivalent for entities.)

- Likely in a handler or dispatcher when an NPC transitions from invented to canonical
- On promotion, extract any epithets from the turn's narration and **append to `npc.aliases`**
- Mirror 75-1's pattern: emit an OTEL span (`entity.alias_accreted` or similar) so the GM panel sees the accretion
- Persist the updated aliases on the next save

### Files to Investigate & Touch

1. **`sidequest/game/session.py`** — `Npc` class: check for existing `aliases` field; add if missing + migration
2. **`sidequest/game/pertinence.py`** — mention signal calculation: hook alias resolver here
3. **`sidequest/game/retrieval_orchestration.py`** — line 300-303 seam: wire the new alias resolver
4. **`sidequest/game/entity_card.py`** — `project_npc_card`: populate `metadata["aliases"]` from the Npc/pool member
5. **`sidequest/game/lore_accretion.py`** (from 75-1) — study the accretion pattern; mirror for entity aliases
6. **NPC promotion handler** (TBD via investigation) — where NPCs transition to canonical; emit alias accretion there

### ADR References

- **ADR-118 Amendment §A4** — Alias-aware, accretion-fed mention concept
- **ADR-118 §D4** (superseded by 84-1's pertinence scorer)
- **ADR-048 (Lore RAG)** — the embedding + retrieval model that extends to entities
- **ADR-035** (Unix Socket IPC) — the daemon client for embeddings
- **Epic 75** (done) — 75-1 lore accretion + 75-2 NPC budgeted selection + 75-4/5 entity card + 75-6 card sync

## TEA Assessment

**Tests Required:** Yes
**Reason:** Net-new alias subsystem + a behavioral widening of the dominant `mention` signal on a live retrieval path — every AC needs failing coverage, and the OTEL principle makes the accretion span load-bearing.

**Migration decision (investigated, confirmed):** **NO Alembic migration.** Add `aliases: list[str] = Field(default_factory=list)` to the `Npc` Pydantic model. `GameSnapshot` (which holds `npcs: list[Npc]`) persists as ONE JSON blob via `snapshot.model_dump_json()` → `game_state.snapshot_json` (`sidequest/game/pg/snapshot.py:83-92`); NPCs are NOT columnar. Only two Alembic migrations exist (`0001_initial_unified_schema`, `0002_asset_ledger`) — neither stores NPCs in columns. The field rides the blob; `default_factory=list` means pre-84-2 saves (no `aliases` key) load to `[]`. A Postgres column would be over-engineering — there is no column to add to.

**Promotion-handler location:** `_promote_pool_member_to_npc` (`sidequest/server/narration_apply.py:1075`, the invented→canonical factory) + the call site inside `resolve_status_target` (~`narration_apply.py:1240-1269`, where `snapshot.npcs.append(promoted)` + the `promoted_from_pool` watcher event fire). This is the alias-accretion hook. Mirror `lore_accretion.accrete_facts_to_lore` (`sidequest/game/lore_accretion.py:70`) for the idempotent shape.

**Mention seam:** `retrieval_orchestration.py:300-303` (mention name-match only). The live value flows from `server/dispatch/universal_retrieval.py:70` → `player_referenced_npcs_from_action` (`agents/npc_context.py:62`) — extend THAT to read `Npc.aliases`.

**Test Files:**
- `sidequest-server/tests/game/test_alias_resolution.py` — pure resolver + accretion-merge helper (AC-1, AC-3 pure). 12 tests.
- `sidequest-server/tests/game/test_npc_aliases_field.py` — `Npc.aliases` field + `project_npc_card` metadata + JSON-blob persistence/legacy-default (AC-2, AC-4). 7 tests.
- `sidequest-server/tests/server/test_alias_accretion.py` — `accrete_npc_aliases` on promotion + `entity.alias_accreted` OTEL span (AC-3, AC-5). Run `-n0`. 7 tests.
- `sidequest-server/tests/game/test_alias_mention_retrieval.py` — alias-aware `player_referenced_npcs_from_action`, drama-gate-skip-yet-surfaces, live working-set BRIEF-toggle wiring (AC-6, AC-7). Run `-n0`. 5 tests.

**Tests Written:** 31 tests covering AC-1…AC-7 (AC-8 is the GREEN-gate quality check).
**Status:** RED — 29 failing, 0 passing.
- 18 `ModuleNotFoundError` (`alias_resolution` + `alias_accretion` absent); 11 `ValidationError`/`AttributeError`/`AssertionError` from `Npc(aliases=...)` rejected by `extra="forbid"` / `.aliases` absent / `model_fields` missing the key — all clean feature-absence, no fixture/typo bugs.
- I strengthened one initially-vacuous test (`test_no_aliases_metadata_when_empty` → `test_empty_vs_populated_aliases_projection_differs`): the original passed trivially because today's projector adds no `aliases` key at all; the rewrite asserts the populated side projects a recoverable key so it fails RED until projection exists.
- The two "name still resolves" no-regression tests fail now only because their `Npc(aliases=...)` fixture can't construct yet; once the field lands they pin the 84-1 name-match behavior is preserved.

**Wiring path:** `_retrieve_entities_for_turn` → `server/dispatch/universal_retrieval.retrieve_for_turn` → `player_referenced_npcs_from_action` (alias-aware, WI-5) → `retrieve_turn_context` mention / `build_npc_working_set` BRIEF toggle. The wiring test asserts the off-stage aliased NPC flips to BRIEF on the real working-set path.

**Run command (OTEL-sensitive — serial):**
`uv run pytest -n0 tests/game/test_alias_resolution.py tests/game/test_npc_aliases_field.py tests/server/test_alias_accretion.py tests/game/test_alias_mention_retrieval.py`

**Handoff:** To Dev (Naomi) for implementation (GREEN).

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/game/alias_resolution.py` (NEW, pure) — `resolve_mention(action, *, names, aliases_by_name)` (word-bounded `\b`, case-insensitive, multi-word-phrase, names OR aliases) + `accrete_aliases(existing, new)` (idempotent, case-folded dedup, no blank, no-mutate).
- `sidequest/game/alias_accretion.py` (NEW) — `AliasAccretionResult`, `accrete_npc_aliases(npc, epithets, *, turn)` (mutates `npc.aliases`, emits `entity.alias_accreted` span ONLY on real accretion via `SPAN_ALIAS_ACCRETED`), and the CONSERVATIVE `extract_epithets_for_npc(narration, name)`.
- `sidequest/game/session.py` — added `aliases: list[str] = Field(default_factory=list)` to `Npc` (rides the snapshot JSON blob; NO migration; legacy saves default `[]`).
- `sidequest/game/entity_card.py` — `project_npc_card` carries `Npc.aliases` into `metadata["aliases"]` as a JSON-encoded SORTED list (deterministic for 75-6 reproject); empty NPC projects no key.
- `sidequest/agents/npc_context.py` — `player_referenced_npcs_from_action` EXTENDED (not forked) to resolve aliases by delegating to `resolve_mention` (one shared `\b` matcher); dropped the now-dead local `re` import.
- `sidequest/server/narration_apply.py` — accretion HOOK: `resolve_status_target` takes optional `narration_text`; on a pool-member promotion it extracts conservative epithets from the promotion turn's narration and accretes them. Wired from the status-change call site (`result.narration` in scope).

**Alias storage:** Pydantic `list[str]` field on `Npc`, persisted in the `GameSnapshot` JSON blob (`model_dump_json` → `game_state.snapshot_json`). No columnar storage, NO Alembic migration. `default_factory=list` makes pre-84-2 saves load to `[]`.

**OTEL:** `entity.alias_accreted` span (`SPAN_ALIAS_ACCRETED`) emitted in `accrete_npc_aliases` ONLY on a real accretion (no span on a no-op), carrying `npc_name`, `aliases_accreted`, `alias_count`, `turn`. The GM-panel lie-detector for engine-written aliases.

**Epithet extraction (what's conservative):** matches ONLY a determiner-led, LOWERCASE appositive directly anchored on the canonical name — `Name, the old smith` / `the old smith, Name`. Lowercase-locked (case-sensitive epithet body) so a capitalized proper-name run ("Borin, Thorn, and Vex") can't be mistaken for an epithet; determiner-required so a bare noun doesn't qualify; 1-3 trailing words so it's an epithet not a clause; no-comma forms ("Borin the Grey") are deliberately skipped. §A4 "alias correctness is load-bearing" — better to miss than to mint garbage that degrades the dominant mention signal.

**Tests:** 29/29 new green (12 resolver + 7 field/projection/persistence + 6 accretion/OTEL + 4 mention/wiring). Regression: retrieval+entity+pertinence 79, narration-apply/status/promotion 92, session+pg-snapshot+working-set 59 — all passed. `ruff check` clean on all changed files.
**Branch:** feat/84-2-alias-resolution (committed; not pushed — SM finishes).

**Handoff:** To review (Chrisjen Avasarala).

## Delivery Findings

No upstream findings at setup.

### TEA (test design)
- **Decision** (non-blocking): Alias storage = Pydantic field on `Npc`, NO migration (investigated; JSON-blob persistence confirmed at `pg/snapshot.py:83`). Dev must NOT run `alembic revision` — there is no column. Affects `sidequest/game/session.py`.
- **Question** (non-blocking): §A4 also names "world-authored entities carry aliases in YAML." That authoring surface (genre-pack YAML → alias) is a CONTENT change scoped OUT of WI-5 (the resolver reads `Npc.aliases` whatever its source). Flagged so it isn't conflated; a follow-up content story can add it. Affects `sidequest-content` (not this story).
- **Improvement** (non-blocking): The accretion hook needs an epithet SOURCE — WI-5 extracts epithets from the promotion turn's narration. The tests pin the helper `accrete_npc_aliases(npc, epithets, *, turn)` and its idempotency/OTEL, but leave the epithet-extraction-from-prose to Dev (where in `resolve_status_target` the narration text is in scope). Keep extraction conservative — a weak extractor that mints garbage aliases degrades the dominant signal (§A4 "alias correctness is load-bearing"). Affects `sidequest/server/narration_apply.py` (~1246).
- **Improvement** (non-blocking): Extend `player_referenced_npcs_from_action` (don't fork it) so the SAME word-bounded `\b` matcher serves names + aliases — otherwise "art" matches inside "start". The resolver tests pin that boundary. Affects `sidequest/agents/npc_context.py`.

### Dev (implementation)
- **Improvement** (non-blocking): The accretion hook fires from the STATUS-CHANGE promotion path (`resolve_status_target` called with `narration_text` from the status-change loop). The OTHER caller (`status_clear.py`) passes no narration text, so a promotion triggered solely by a status-CLEAR accretes nothing this turn — acceptable (a clear isn't the epithet-introducing moment), but a future story could broaden the epithet source to all promotion triggers. Affects `sidequest/server/narration_apply.py` + `sidequest/server/status_clear.py`. *Found by Dev during implementation.*
- **Improvement** (non-blocking): Epithet extraction currently requires an explicit comma-appositive ("Borin, the old smith"). Comma-less forms ("Borin the Grey", "the dock-warden Borin") are conservatively SKIPPED to avoid false positives. If playtest shows the narrator routinely uses comma-less epithets, the extractor can be widened — but only with care (§A4 alias correctness is load-bearing). Affects `sidequest/game/alias_accretion.py::extract_epithets_for_npc`. *Found by Dev during implementation.*
- **Improvement** (non-blocking): §A4's world-authored-aliases-in-YAML leg remains OUT of scope (TEA flagged it). The resolver reads `Npc.aliases` regardless of source, so a future content story need only populate `Npc.aliases` at materialization (e.g. from a pack `aliases:` key) — no resolver change required. Affects `sidequest-content` + the world-materialization path (future). *Found by Dev during implementation.*
- No blocking upstream findings.

## Design Deviations

No deviations at setup.

### TEA (test design)
- No deviations. ACs derive from ADR-118 §A4 + the 84-2 session brief + live investigation.

### Dev (implementation)
- No deviations from spec. Implemented exactly to AC-1…AC-7 and TEA's four Delivery Findings: `Npc.aliases` Pydantic field (no migration), shared `\b` resolver extended into `player_referenced_npcs_from_action` (not forked), `accrete_npc_aliases` mirroring the 75-1 lore-accretion shape with `entity.alias_accreted` on real accretion only, deterministic sorted alias metadata on the projected card, and a conservative comma-appositive epithet extractor hooked at the promotion seam where the narration text is in scope. No stubs, no silent fallbacks.

## Reviewer Assessment (84-2, commit 8eb99bd)

**Reviewer:** Chrisjen Avasarala (adversarial review, Lap 3)
**Verdict:** APPROVED — merge-ready. No Blocker or High. ONE load-bearing Should-fix (extractor clause false-positives + missing negative tests) that I want tracked before the extractor is reused for factions/locations.

**Scope reviewed:** full diff `develop...feat/84-2-alias-resolution` (1047 +/5 -): new `alias_resolution.py` + `alias_accretion.py`, `Npc.aliases` field, `project_npc_card` metadata, `player_referenced_npcs_from_action` extension, the promotion accretion hook, 4 new test files. Verified vs ADR-118 §A4 + context ACs 1-8.

**Verification run (OTEL-sensitive, -n0 serial):**
- 84-2 suites (resolution + aliases-field + accretion + mention-retrieval): **32 passed**.
- Regression (84-1 scorer + supersedes-d4 + orchestration + dispatch + 75-10 signal): **63 passed**; entity_card: **27 passed**.
- `ruff check` on all 6 changed files: clean. Tree clean; subrepo HEAD 8eb99bd; no Alembic migration added.
- Independent ReDoS stress (50k-char pathological inputs on both regexes): all <2ms — no catastrophic backtracking.
- Independent persistence probe: legacy `Npc` dict (no `aliases` key) → `[]`; alias round-trips through `model_dump_json`/`model_validate_json`; `extra=forbid` intact.

**Adversarial checks (8 observations):**
1. **Resolver correctness + ReDoS — VERIFIED SAFE.** `resolve_mention` uses `\b{re.escape(phrase)}\b`
   (escaped literal, no quantifiers over input) — word boundary holds ("art"∉"start", tested),
   case-insensitive, multi-word phrase matches. `extract_epithets_for_npc`'s `_EPITHET_BODY` has a
   bounded `{0,2}` repeat with non-overlapping token classes — linear on 50k-char adversarial inputs
   (measured <2ms). No ReDoS on either untrusted-text path.
2. **Extractor false-positives — DEFECT FOUND (Should-fix #1).** The conservative guards (capitalized-
   proper-name rejection, length cap) work for proper-name runs ("Borin, Thorn, and Vex" → []) and caps,
   BUT there is NO clause/verb guard. Realistic promotion narration of the shape `"<Name>, the <noun>
   <verb>..."` mints a SCENE CLAUSE as an NPC alias — confirmed through the REAL extractor:
   `"Borin, the torch sputters and dies..."` → alias `"the torch sputters and"`;
   `"Borin, the door swings open..."` → alias `"the door swings open"`. This pollutes the DOMINANT
   mention signal — exactly the §A4 load-bearing risk the story names. (Player-name INJECTION is NOT
   possible: the extractor runs on NARRATION only, never on player action text — verified.)
3. **No migration — VERIFIED.** `Npc.aliases: list[str] = Field(default_factory=list)` rides the
   `snapshot_json` blob; no Alembic revision; legacy saves default to `[]` honestly. No columnar
   assumption anywhere (grep + live round-trip confirmed).
4. **Accretion wiring + idempotency — VERIFIED.** The hook lives in `resolve_status_target`
   (narration_apply.py:1291-1294) — the SOLE `_promote_pool_member_to_npc` call site (grep-confirmed,
   one caller). The mutated `promoted` IS the object appended to `snapshot.npcs` at :1261 (same
   reference — proven by `test_real_promotion_path...` asserting the alias on the in-snapshot NPC).
   Idempotent + case-folded dedup via shared `accrete_aliases`; the 3 `TestRealPromotionAccretionWiring`
   tests are NOT vacuous (real seam, persisted-NPC identity, span fired, JSON round-trip, no-op honesty).
   No unbounded growth (re-accretion returns []).
5. **No Silent Fallbacks — AGREE with TEA.** `entity.alias_accreted` fires ONLY on real accretion
   (`if accreted:` guard) — no-op turns emit nothing (tested, both pure + real-seam). The `status_clear`
   caller (status_clear.py:175) doesn't pass `narration_text` → no accretion on a clear turn; this is
   §A4 "miss don't mint" and is defensible — accretion is additive + idempotent, so the next real
   status_change promotion re-accretes. Concur it's not a gap.
6. **Mention seam end-to-end — VERIFIED, no double-count.** `test_alias_match_skips_embed_and_npc_still_
   surfaces` drives `retrieve_turn_context` with alias-resolved `player_referenced_npcs`, asserts
   `embed_skipped is True` + `fake.calls == []` + the NPC surfaces in the floor — the alias raises the
   dominant signal exactly as a name does. 84-1's mention is binary (`1.0 if player_referenced_npcs`),
   so an alias hit and a name hit yield identical `mention=1.0` — no signal corruption, no double-counting.
   The resolver is EXTENDED into `player_referenced_npcs_from_action`, not forked — one `\b` matcher.
7. **Determinism / type design — VERIFIED.** `project_npc_card` → `metadata={"aliases": json.dumps(
   sorted(aliases))}` — sorted before encode, so same alias SET → identical metadata (75-6 reproject
   safe, tested). Aliases never enter `content` (don't pollute the embedding vector — good). `metadata`
   is `None` (not a bogus empty value) when an NPC has no aliases. Pool members carry no aliases
   (identity-only) — handled correctly.
8. **AC-7 wiring test overclaims (Nit).** `test_live_turn_resolves_alias_to_referenced_npc` docstrings
   "drive the LIVE `_retrieve_entities_for_turn` delegate" but actually calls
   `player_referenced_npcs_from_action` + `build_npc_working_set` directly — the real production
   FUNCTIONS, but not a full handler drive (unlike 84-1/84-4's `handle_message` wiring). Per server's
   "No Source-Text Wiring Tests" it's valid (behavior, not grep) and the seam IS production, but the
   docstring's "LIVE delegate" framing is inaccurate and the proof is weaker than the prior stories'.

**Findings (none blocking per the Critical/High rule):**

| Severity | Finding | Location |
|----------|---------|----------|
| Should-fix | The epithet extractor mints comma-led scene CLAUSES as NPC aliases (`"Borin, the torch sputters and..."` → alias `"the torch sputters and"`), polluting the DOMINANT mention signal — the exact §A4 load-bearing risk. The docstring claims a conservatism the regex doesn't deliver (no verb/clause guard). Add a guard rejecting epithet bodies containing a finite verb / requiring a pure noun-phrase appositive. Low practical blast radius (fires only on promotion turns; only mis-fires if a later player action repeats the exact phrase; additive/idempotent), so not a Blocker — but it IS a correctness defect against the story's headline guard. | `sidequest/game/alias_accretion.py:42,45-70` |
| Should-fix | NO direct unit test for `extract_epithets_for_npc`'s negative guards. The load-bearing component (§A4: "a garbage extractor pollutes the DOMINANT signal") is tested only via happy-path promotion + a no-comma no-op. Add direct tests feeding: a comma-led clause (→ []), a capitalized epithet (→ []), a proper-name run (→ []), and the length cap — this would have caught Should-fix #1. | `tests/server/test_alias_accretion.py` (new `TestExtractEpithets` class) |
| Nit | AC-7 "wiring" test docstring overclaims "LIVE `_retrieve_entities_for_turn` delegate" — it exercises the production seam functions directly, not a handler drive. Either drive `handle_message` (as 84-1/84-4 do) or soften the docstring to "the live mention seam." | `tests/game/test_alias_mention_retrieval.py:147` |

**Deviation audit:**
- TEA + Dev both logged **"No deviations."** — confirmed against the diff (implemented to AC-1…AC-7 +
  TEA's findings; no migration, resolver extended not forked, no scorer change, no stubs). **ACCEPTED.**
- TEA's CONDITIONAL PASS condition (add the real-promotion wiring guard) is met — `8eb99bd` adds the 3
  `TestRealPromotionAccretionWiring` tests. Confirmed present and non-vacuous.

**Handoff:** To SM for finish-story. The two Should-fix items are a matched pair (the missing negative
tests are why the clause-minting defect shipped) — strongly recommend folding a verb/clause guard +
direct extractor negative tests into THIS story before merge, because WI-5's extractor is the template
the §A4 faction/location alias work will copy, and a garbage-epithet regex is a bad thing to propagate.
If deferred, track as a blocking 84-x follow-up, not a backlog nicety — alias correctness is load-bearing
by the ADR's own words. The Nit is cosmetic (docstring).

### Re-check addendum (84-2, commit 7830d0e) — Should-fixes folded in

**Verdict:** CONFIRM-CLOSED (merge-ready). The two Should-fixes from my Lap-3 review are addressed; the
specific defect I flagged is genuinely fixed. Two minor RESIDUALS remain (new Nits, NOT a re-open) — track
them for the §A4 faction/location extractor reuse, don't block this merge.

**Re-verified on `7830d0e` (fix on top of e0f93f4 + 8eb99bd):**
- **Should-fix #1 (clause-minting) — CLOSED.** Re-ran ALL my original minting cases — every one now returns
  `[]`: `"Borin, the torch sputters and dies…"` → []; `"…the door swings open…"` → []; `"…the air grows
  cold…"` → []; `"You attack Borin, the dragon breathes fire."` → []. Plus 12 NEW singular-present scene
  clauses I had not tested (haggles/blesses/salutes/barks/carries/weeps/churns/disperses/tolls, epithet-first
  mirrors) — all `[]`. The high-frequency `Name, the <noun> <3rd-sing-verb>…` form is dead. The truncate-then-
  verb-check subtlety holds: `"the grand high warlock of the seven towers"` → mints `"the grand high warlock"`
  (the later `-s` "towers" is past the 1-3-word head), while `"the crowd parts"` → [] (verb in the head).
- **Should-fix #2 (negative tests) — DELIVERED.** `TestExtractEpithets` = 11/11 (7 scene-clause rejects +
  4 positive mints), enumerated and green. RED-proven per Dev. This is the root-cause test class that was
  missing; it would have caught the original defect.
- **Regression — CLEAN.** Full accretion file 20/20; retrieval/alias regression 61 passed (Dev's "62" is a
  file-selection delta, no failures); `ruff check` clean.

**Residual gaps I found in the re-check (NEW Nits — lower-frequency, lower-impact than the closed defect):**

| Severity | Finding | Location |
|----------|---------|----------|
| Nit | **Under-rejection: plural-subject + past-tense clauses still mint in appositive position.** The verb guard is 3rd-person-singular `-s`-based, so a clause with a plural subject ("the men fight", "the women weep", "the oxen pull") or a past-tense verb ("the door fell", "the crowd grew", "a fire spread") in `Name, <clause>,` / `<clause>, Name` position is NOT caught → minted as an alias. Materially rarer than the singular-present form just closed (requires the clause to sit in a comma-closed appositive slot), and same low blast radius (additive/idempotent; only mis-fires if a later player action repeats the phrase). Not a re-open — the flagged class is fixed; this is an adjacent class. | `sidequest/game/alias_accretion.py:73-89` (`_looks_like_finite_verb` is `-s`-only) |
| Nit | **Over-rejection: valid `-s` NOUN epithets wrongly dropped.** The structural `-s` heuristic flags real nouns NOT in the `_NOUN_S_SUFFIXES` whitelist as verbs — confirmed dropped: "chaos", "atlas", "lens", "species", "series", "kudos", "pathos", "gallows", "bellows". So `"Borin, the chaos cultist,"` → [] (recall loss on the dominant signal). Uncommon as epithet head-nouns but plausible in genre prose. The whitelist (`ss/us/is/ous/ics/ness/ess`) is the brittle enumeration the §A4 reuse will inherit — a POS-tagger or a fuller noun-suffix set would generalize better than growing the list. | `sidequest/game/alias_accretion.py:70` (`_NOUN_S_SUFFIXES`) |

**On Q3 (stoplist brittleness):** the structural `-s` heuristic does carry real weight beyond the stoplist
(it caught haggles/salutes/disperses/tolls etc. that aren't enumerated), so it is NOT purely stoplist-
dependent for the singular-present case — good. But it is the SAME mechanism that causes both residuals
above (it can't see plural/past verbs, and it false-positives on `-s` nouns). For the §A4 faction/location
extractor, a light POS check (or spaCy/nltk tag) would close both residuals at once and retire the dual
stoplist/whitelist maintenance burden. Flagging as the forward-looking recommendation, not a blocker.

**Bottom line:** the merge-blocking concern from Lap 3 is resolved. CONFIRM-CLOSED. The two residual Nits
are real but acceptable to ship — they should ride into the WI-5 faction/location follow-on as "harden the
verb guard with POS tagging," since that's where this extractor becomes a reused template.
