# Epic 57: Narrator Prompt Token Reduction

## Overview

A pre-sprint audit of the per-turn narrator prompt assembly (driven from `sidequest-server/sidequest/agents/orchestrator.py` and `sidequest/server/session_helpers.py`) identified **15–40 k uncached tokens per narrator turn**, distributed across five distinct sources ranging from a one-line constant to ADR-shaped architectural migrations. Every saved token compounds linearly with playtest hours, and uncached tokens specifically defeat the ADR-101 Phase D Stable/Recency caching split — so cuts that shrink the *uncached* surface deliver outsized cost relief.

This epic ships those five cuts as independent, server-only refactors. Story 57-1 (recency-window `K=4→K=2`) already shipped on 2026-05-19. The remaining four stories each map 1:1 to either an accepted ADR (110/111/112) or a self-contained audit task (57-2). None of the four block each other — they can be claimed in any order and merged in parallel.

**Priority:** P2
**Repos:** server
**Stories:** 5 (16 points; 1 done, 15 remaining — 13 implementation + 2 audit/done)

## Background

### Why this epic exists

SideQuest's narrator runs on the Anthropic SDK (ADR-101) with native tool-use for structured output (ADR-102). The per-turn prompt is assembled into three attention zones (ADR-009: Early / Valley / Late) and routed across two cache buckets via `prompt_framework.bucket.default_bucket_for_section()`:

- **`SectionBucket.System`** → `system=` array on the SDK call, gets `cache_control` breakpoints — *cached across turns*.
- **`SectionBucket.User`** → per-turn user message — *uncached by design*.

The audit found three classes of waste:

1. **Cacheable content that lives in the uncached path.** Static genre prose sections that never change within a session sit in Valley (`SectionBucket.User`) because they're not in the `STABLE_SECTION_NAMES` allowlist at `prompt_framework/bucket.py:28–41`. Fix is allowlist promotion (ADR-112, story 57-3).
2. **High-attention recency-zone guardrails restated every turn.** Four prose blocks at `orchestrator.py:1764 / :1851 / :1934 / :1989` re-state tool-use rules on every turn because the original schema-block instructions in the System zone have decayed attention by turn 20+. Native tool-use offers a cached migration target via the `tools=` array's `description` field (ADR-111, story 57-4).
3. **`<game_state>` snapshot bloat.** The per-turn state payload at `session_helpers.py:485–558` runs `json.loads(snapshot.model_dump_json())` then `json.dumps(..., indent=2)`. `indent=2` is pure encoding waste, pydantic defaults serialize regardless of relevance, and several fields aren't load-bearing because the narrator reads them via dedicated prompt sections (ADR-110, story 57-5).

### Audit-vs-design split

Two of the five stories are pure-audit (one-line or read-only):

- **57-1** (done) — change one constant. Pattern: story 49-1.
- **57-2** — verify whether five tiny `narrator_prompts/*.md` files are load-bearing or dead.

Three are ADR-shaped refactors that ratified design choices already locked in ADRs 110/111/112 on 2026-05-19. Each ADR explicitly carries `implementation-pointer: sprint/current-sprint.yaml#57-N`. There is no further design needed; Dev/TEA read the ADRs and implement.

### Why "audit-driven" matters here

Cutting `<game_state>` blind risks silent quality regression — the narrator-gaslighting doctrine (project memory) materializes ground truth into the snapshot specifically *because* the narrator confabulates when starved. The diamonds-and-coal discipline (SOUL.md, ADR-014) likewise depends on the narrator seeing what matters. Every cut in this epic must show OTEL evidence of no narrative-quality regression after merge — that's the per-CLAUDE.md observability principle as applied to a token-reduction PR.

## Technical Architecture

```
Three-Zone Prompt Assembly (ADR-009)
─────────────────────────────────────
SYSTEM bucket (cached via cache_control)         USER bucket (uncached, per-turn)
─────────────────────────────────────           ────────────────────────────────
narrator_identity                                <game_state>                ← 57-5 (ADR-110)
narrator_dialogue                                  ↑ Valley zone
soul_principles                                  active_tropes (Recency)
output_format                                    recent_narrative_log[-K:]    ← 57-1 done
genre_identity                                    npc_intro_visual_constraint   ← 57-4 (ADR-111)
genre_narrator_voice                              confrontation_trigger_constraint   ← 57-4
genre_npc_voice                                   npc_extraction_constraint    ← 57-4
genre_world_state                                 location_patch_constraint    ← 57-4
narrator_vocabulary                              genre_extraction (Valley)     ← 57-3 (ADR-112)
genre_transition_hints                           genre_keeper_monologue       ← 57-3
                                                 genre_town                   ← 57-3
                                                 genre_chargen                ← 57-3
                                                 genre_combat_voice (conditional — DEFERRED)
                                                 genre_chase_voice (conditional — DEFERRED)
```

### Story-to-ADR mapping

| Story | Workflow | Pts | Type | ADR | Site |
|---|---|---|---|---|---|
| 57-1 done | trivial | 1 | chore | n/a (49-1 pattern) | `orchestrator.py:102` |
| 57-2 | trivial | 1 | chore | n/a (audit) | `sidequest/agents/narrator_prompts/*.md` |
| 57-3 | tdd | 2 | refactor | **ADR-112** | `prompt_framework/bucket.py:28–41` allowlist + 4 prose sections at `orchestrator.py:1265–1385` |
| 57-4 | tdd | 5 | refactor | **ADR-111** | 4 guardrail registrations at `orchestrator.py:1764, :1851, :1934, :1989` → `tools=` descriptions |
| 57-5 | tdd | 5 | refactor | **ADR-110** | `session_helpers.py:485–558` + `local_dm.py:308` |

### 57-3 surface (ADR-112)

Promote the four **always-fire + session-static** genre prose sections into `STABLE_SECTION_NAMES`:

- `genre_extraction` (Valley, unconditional, source: `prompts.yaml gp.extraction`)
- `genre_keeper_monologue` (Valley, unconditional, source: `prompts.yaml gp.keeper_monologue`)
- `genre_town` (Valley, unconditional, source: `prompts.yaml gp.town`)
- `genre_chargen` (Valley, unconditional, source: `prompts.yaml gp.chargen`)

**Explicitly NOT promoted** (deferred per ADR-112): `genre_combat_voice` and `genre_chase_voice` — these are conditional (gated on `context.in_combat` / `context.in_chase`), and their flip-on/flip-off pattern would thrash the prompt cache. ADR-112 documents this rationale; the implementer must not "complete the set".

### 57-4 surface (ADR-111)

Migrate four Recency-zone guardrails to the `tools=` array's `description` field on the corresponding tool definitions in the native tool-use registry (ADR-102). The Recency-zone registrations come out; the tool description side gains the prose. Tool descriptions are part of the cache key root — sent on every turn, cost once on cache write, amortized across the save.

This is **backend-gated**: the migration only happens on the `anthropic_sdk` backend path. The Ollama / `claude -p` legacy paths keep the Recency-zone prose. Implementation must preserve both paths under the backend switch.

### 57-5 surface (ADR-110)

**Phase A** (zero-risk): Replace `json.loads(snapshot.model_dump_json())` → `json.dumps(..., indent=2)` with `snapshot.model_dump(mode="json", exclude_defaults=True, exclude_none=True)` and compact separators. Pydantic round-trip equivalence holds.

**Phase B** (audit-driven): Drop fields no narrator path consumes (`active_tropes` is already re-rendered in the Recency-zone `pending_trope_context` block, etc.). Allowlist approach, OTEL-verifiable.

Combined target: **≥50% reduction in `<game_state>` bytes per turn**, zero narrator-quality regression. Single story, two phases, one PR. **Diff-with-anchor (Option C) and tool-fetch (Option D) are explicitly deferred** to a follow-up only if A+B savings prove inadequate.

### 57-2 surface (audit)

Five smallest files in `sidequest-server/sidequest/agents/narrator_prompts/`:

| File | Size | Registration site to verify |
|---|---|---|
| `identity.md` | 210 B | trace consumers in `agents/` |
| `referral_rule.md` | 324 B | trace consumers |
| `consequences.md` | 398 B | trace consumers |
| `output_style.md` | 667 B | trace consumers |
| `dialogue_rules.md` | 756 B | trace consumers |

Output: a verdict per file — load-bearing (keep), deprecated (delete + remove registration), or empty stub (delete + remove import). Don't refactor the content if it's load-bearing; this is a one-pass dead-code audit.

### Cross-story execution order

```
57-1 (done)
57-2 ─┐
57-3 ─┤   independent — claim in any order, merge in parallel
57-4 ─┤
57-5 ─┘
```

No story blocks any other. Each is a single-repo (`server`) refactor with its own ADR or audit boundary. The natural "first claim" is 57-2 (1 pt audit) to clear it; the highest-leverage claim is 57-4 (5 pt, biggest token reduction per ADR-111) or 57-5 (5 pt, biggest single-blob reduction per ADR-110).

### OTEL / observability gates

Per repo CLAUDE.md ("OTEL Observability Principle"), every subsystem fix adds OTEL spans so the GM panel can verify. Each ADR carries its own observability discipline:

- **ADR-110:** `<game_state>` byte-size span before/after, per-turn.
- **ADR-111:** Pre- and post-migration narrator-output diff counter (regression detector).
- **ADR-112:** `cache_creation_input_tokens` vs `cache_read_input_tokens` delta after promotion (validates the cache actually catches the promoted sections).

These are gate requirements for the respective stories' Reviewer phase, not stretch goals.

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| `docs/adr/110-game-state-snapshot-slimming.md` | **Authoritative source for 57-5.** §Decision (Phase A + Phase B), §Alternatives (why C/D deferred), §Implementation Notes (`session_helpers.py:485–558` and `local_dm.py:308` sites). |
| `docs/adr/111-narrator-guardrails-into-tool-descriptions.md` | **Authoritative source for 57-4.** §Context (four guardrails table with sites + sizes), §Decision (migration rule, backend-gating discipline), §References (per-tool mapping done at impl time). |
| `docs/adr/112-genre-prose-stable-cache-promotion.md` | **Authoritative source for 57-3.** §Decision (four-section promotion + two-section deferral), §Mutability rubric, §Note on `narrator_vocabulary` audit follow-up. |
| `docs/adr/009-attention-aware-prompt-zones.md` | The Early/Valley/Late zone definitions that 57-3 and 57-4 manipulate. |
| `docs/adr/101-anthropic-sdk-narrator.md` | Phase D Stable-zone caching design — the cache surface 57-3 promotes into. |
| `docs/adr/102-tool-use-protocol-structured-output.md` | The `tools=` array as a caching surface — the migration target for 57-4. |
| `docs/adr/098-stateless-narrator-turns.md` | Bounded per-turn prompts — the rationale that makes 57-1 / 57-5 safe (no `--resume` window growth). |
| `sprint/archive/57-1-session.md` | Pattern reference for 57-2 (both are 1 pt chores; trivial workflow shape). |
| `CLAUDE.md` "Who This Is For" | Keith is the lie-detector — cost savings here don't compromise narrator quality because the playtest cadence with Keith catches regressions. Sebastien (mechanical-first) benefits directly from cleaner OTEL emit when the prompt surface is leaner. |
| `CLAUDE.md` "OTEL Observability Principle" | Every cut in this epic ships a corresponding OTEL span — gate condition per story. |
| Project memory `project_narrator_gaslighting_doctrine.md` | Why `<game_state>` slimming is audit-driven, not blind — the narrator must see materialized ground truth. |
| Project memory `project_claude_p_no_reactive_tools.md` | Reminder that 57-4's tool-description migration only applies to the `anthropic_sdk` backend — `claude -p` is one-shot and cannot reactively call tools mid-generation. |

**No external spec doc.** This epic was captured directly as ADRs on 2026-05-19; the three ADRs are the spec. No `docs/superpowers/specs/*-token-reduction-*.md` exists.

## Cross-Epic Dependencies

**Depends on:**
- *None.* The epic is self-contained within `sidequest-server`. ADR-101 (SDK backend), ADR-102 (tool-use protocol), and ADR-098 (stateless turns) are all already live — this epic harvests value from those substrates rather than waiting on them.

**Depended on by:**
- **Cost-of-playtest curve (not an epic, but a project-level concern).** Every hour of playtest time pays for itself faster after this epic lands; the 57-3/4/5 cuts compound across save resumption. No formal epic dependency, but operationally this epic is a force-multiplier for any future playtest work, especially the tea_and_murder/glenross dogfooding tied to epic 22 (Seed Tropes) and epic 24 (Procedural World-Grounding).
