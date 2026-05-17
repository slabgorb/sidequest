---
id: 101
title: "Anthropic SDK as Narrator Backend"
status: accepted
date: 2026-05-15
deciders: [Keith Avery]
supersedes: [1]
superseded-by: null
amends: [73]
depends_on: [67, 98, 73]
related: [1, 39, 58, 28, 67, 73, 98]
tags: [core-architecture, agent-system]
implementation-status: partial
implementation-pointer: "Backend live + default on develop: sidequest-server/sidequest/agents/llm_factory.py (default anthropic_sdk), anthropic_sdk_client.py, model_routing.py, anthropic_cost.py. Phased cleanups (sidecar/perception-rewriter/OTEL-scraper deletion) tracked by ADR-102/104/103."
load_bearing: true
---

# ADR-101: Anthropic SDK as Narrator Backend

## Status

Proposed. Promotes to **accepted** when `feat/anthropic-sdk-migration`
squash-merges to `develop` at the end of Phase E.

## Context

ADR-001 mandated `claude -p` subprocess calls as the only LLM transport. On
2026-06-15 Anthropic moves `claude -p` into a separate metered "programmatic
credit" pool, billed at API list rates and capped per subscription tier. At
typical playgroup load (200-300 turns × ~30k input / 2k output per turn,
uncached), one weekly session burns $24-36, pushing $96-144/month against a
$200 Max-20× cap. The current path is economically unsustainable post-cutover.

Three secondary problems compound:

1. `claude -p` cannot call tools mid-generation. Every structured output
   (dice, state patches, journal entries, disposition updates, scenario
   advances) routes through ADR-039's fenced-JSON sidecar — a ~200-LOC
   malformed-JSON parser, and a hallucination surface (the narrator can write
   prose claiming an effect with no matching sidecar field).
2. `claude -p` cannot use prompt caching. Every turn pays the full system-
   prompt tax (~25-50k tokens uncached).
3. ADR-058's OTEL passthrough is structurally forensic — it scrapes stderr
   JSON after the fact. ADR-031's "GM panel as lie detector" can only flag
   patterns post-narration.

## Decision

Migrate the narrator path to the Anthropic SDK on a single feature branch
(`feat/anthropic-sdk-migration`, Approach B from the design spec). `develop`
stays on `claude -p` until Phase E merge. The new path captures:

1. **Prompt caching** — `cache_control` markers on three system zones
   (SOUL + rules, tool definitions, world snapshot). Median 60% of input
   tokens cached after warmup; cached input is 90% cheaper than fresh input.
2. **Tool use** — JSON-Schema-validated tool round-trips replace the ADR-039
   sidecar. 26 tools in the v1 catalog cover every sidecar field.
3. **Just-in-time retrieval** — narrator queries subsystems only when each
   turn engages them; prompt-stuffing of unused content ends.
4. **Per-call model routing** — Haiku 4.5 for classification + scratch,
   Sonnet 4.6 for narration, Opus 4.7 for declared-important moments.

Combined target: weighted-average $0.05-0.07 per turn vs. ~$0.12 on
post-cutover `claude -p`. A 250-turn session costs $12-18; a Max-20× cap
covers ~12-14 sessions/month with margin.

The decision is structurally enabling for three additional cleanups,
documented in their respective successor ADRs:
- **ADR-100-successor** (tool-use protocol) — supersedes ADR-039
- **ADR-101-successor** (native OTEL via tool registry) — supersedes ADR-058
- **ADR-102-successor** (perception filtering at the tool layer) — supersedes
  ADR-028

(Successor numbers will be assigned at write-time during Phase D5.)

## Consequences

**Positive:**
- Per-turn cost drops to a level that fits the Max-20× cap with margin for
  dev playtests
- Sidecar parser deleted (Phase D); narration / mechanics divergence
  becomes structurally impossible — the narrator cannot describe a
  mechanical effect without invoking the corresponding tool
- ADR-028 post-pass perception rewriter deleted (Phase D); multiplayer turns
  drop from N+1 model calls to N
- GM panel becomes a structural lie detector — three new verification
  classes (mechanical assertion without action, state described without
  query, perception filter violation) become enforceable
- Prompt cache breakpoints align with existing prompt zones; little
  architectural rework needed beyond the slim pass

**Negative:**
- `ANTHROPIC_API_KEY` becomes a hard runtime requirement on narrator paths
  (no silent fallback — fail loud per CLAUDE.md)
- Tool selection becomes a quality surface — bad tool descriptions or
  overlapping tools degrade narration; mitigated by Phase C per-tool tuning
  with playtest fixtures
- Branch hygiene cost — `feat/anthropic-sdk-migration` rebases weekly
  against `develop` for 3-4 sprints
- Once Phase D deletes the sidecar parser, `SIDEQUEST_LLM_BACKEND=claude` is
  no longer a working narrator backend — the merge is a one-way door

**Neutral:**
- `ClaudeClient` and `OllamaClient` remain in place for non-narrator paths
  (mood classifier, name gen, scratch jobs)
- ADR-073 (LLM backend factory) is amended in scope, not retired — the
  factory still exists; the narrator path just stops being a configuration
  point

## Alternatives considered

**Approach A — Sequential cutover.** Backend swap + caching land first as a
self-contained change to `develop`; tool conversions follow in batches.
Lower per-change risk, but the prompt stays fat through the intermediate
window (no slim wins until later), and intermediate states ship to the
playgroup.

**Approach C — Strangler-fig coexistence.** SDK and CLI clients run side-by-
side on `develop`; tools land one at a time, each independently mergeable.
Rejected because mid-conversion playtests produce variable game quality the
playgroup will notice, and 25+ incremental merges create a heavier rebase
burden than one squash-merge from a feature branch.

**Approach B — Single big-bang on feature branch (selected).** `develop` is
protected throughout; the migration's design coherence (sidecar parser,
perception rewriter, and OTEL scraper deleted together) is achievable;
single squash-merge gives a clean revert path.

## References

- Design spec: `docs/superpowers/specs/2026-05-15-anthropic-sdk-migration-design.md`
- Phase A plan: `docs/superpowers/plans/2026-05-15-anthropic-sdk-migration-phase-a-foundation.md`
- ADR-001 (Claude CLI Only) — superseded on landing
- ADR-039 (JSON sidecar) — superseded on landing
- ADR-058 (Claude subprocess OTEL passthrough) — superseded on landing
- ADR-028 (Perception rewriter) — superseded on landing
- ADR-073 (LLM backend factory) — amended on landing
