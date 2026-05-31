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
related: [1, 39, 58, 28, 67, 73, 98, 112]
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

## Amendment — 2026-05-20: Four-Region Cache Layout

The cacheable surface of the narrator request is documented as four
regions, in cache-prefix order:

| Region | Source | Cache | TTL | Notes |
|--------|--------|-------|-----|-------|
| **Tools** | `_build_tools_array` (last entry marked) | yes | 1h | 27 stable definitions; see live size at `narration.turn.system_block_sizes_json["tools"]`. Marker added 2026-05-20 because Anthropic's default auto-cache on tools was landing in 5m and re-writing every turn the 5m TTL expired. Tools byte-stability gated by `tests/agents/test_cache_ttl_prefix_and_otel.py::test_tool_definitions_json_byte_identical_across_calls`. |
| **Stable** (Primacy + Early) | `system_blocks[0]` | yes | 1h | SOUL, identity, guardrails; see live size at `narration.turn.system_block_sizes_json["stable"]`. Byte-stability is gated by `tests/agents/test_cache_ttl_prefix_and_otel.py::test_compose_split_system_prefix_byte_identical_across_3_turns`. |
| **Valley** | `system_blocks[1]` | no | — | Per-turn drift (narrator vocabulary). Deliberately uncached per Phase D Task 6. |
| **Late + Recency** | `system_blocks[2]` | no | — | Per-turn drift (genre transition hints). Deliberately uncached per Phase D Task 6. |

The orchestrator emits a `narration.turn.system_block_sizes_json` OTEL
attribute carrying token-estimate sizes for all four regions on every
narration turn, so drift inside the "stable" region surfaces in the GM
panel rather than as a cache-write growth on the Anthropic console.

See [spec](../superpowers/specs/2026-05-20-narrator-cache-cost-reduction-design.md) and [plan](../superpowers/plans/2026-05-20-narrator-cache-cost-reduction.md) for the change set.

## Amendment (2026-05-31): Model-Routing Ladder + Cache-Zone Partition Protocol

The original Decision (§Decision items 1 and 4) named "per-call model routing"
and "`cache_control` markers on three system zones" as live capabilities, citing
`model_routing.py`, `anthropic_sdk_client.py`, and the prompt framework, but gave
only one worked example of each. This amendment makes both mechanisms governing
specifications: it does not change the Decision, it pins down the contracts the
Decision relied on. (ADR-112 governs *which* sections are promoted to the Stable
prefix; this amendment governs the partition *mechanism* beneath that decision —
how a section's name and zone deterministically place its bytes in a cached or
uncached block.)

### A. The Model-Routing Ladder

`sidequest/agents/model_routing.py` is the single model-selection point. Every
call site that talks to the Anthropic SDK declares a `CallType`; nothing else
chooses a model.

- **`CallType` taxonomy** (`model_routing.py:18-22`) — a four-member `StrEnum`:
  `NARRATION`, `NARRATION_IMPORTANT`, `CLASSIFICATION`, `SCRATCH`.
- **The default ladder** (`model_routing.py:25-30`, `_DEFAULT`) maps each call
  type to a model id:
  - `NARRATION` → `claude-sonnet-4-6` (the per-turn narrator)
  - `NARRATION_IMPORTANT` → `claude-opus-4-7` (the Opus tier, reserved for
    caller-declared important moments)
  - `CLASSIFICATION` → `claude-haiku-4-5-20251001`
  - `SCRATCH` → `claude-haiku-4-5-20251001`
- **`resolve_model(call_type, *, pack_overrides=None)`** (`model_routing.py:33-42`)
  is the *only* selection function. It fails loud on a non-`CallType` argument
  (`UnknownCallType`, `model_routing.py:38-39`) — No Silent Fallbacks. There is
  no default model: an unrecognized member would `KeyError` on `_DEFAULT`.
- **Pack-override extension point** — when `pack_overrides` contains the call
  type, its mapping wins over `_DEFAULT` (`model_routing.py:40-41`). This is the
  seam through which a genre pack may, e.g., route its narration to Opus or its
  classification to a cheaper model, *without touching engine code* — the
  authoring-surface requirement. The override dict is per-call-type and is the
  governed extension contract: packs supply `dict[CallType, str]`; the resolver
  layers it over the default.

**Live wiring.** `NARRATION` is resolved on the narrator path at
`orchestrator.py:3812` (`resolve_model(CallType.NARRATION)`); `SCRATCH` is
resolved for dungeon materialization at `materializer.py:1213`. `resolve_model`
and `CallType` are re-exported from `sidequest/agents/__init__.py:41,140`.
**Honesty note:** `NARRATION_IMPORTANT` (the Opus tier) and `CLASSIFICATION`
are defined in the ladder but have **no live call site** today — the
"declared-important moment" caller and the SDK-routed classification pass are not
yet wired to `resolve_model`. Pack-override plumbing into `resolve_model` is
likewise not yet threaded from pack config (the parameter exists and is
honored; the call sites pass `pack_overrides=None`). This amendment governs the
contract so those call sites have a fixed target to wire against.

### B. The Zone × Bucket Cache-Partition Protocol

The cacheable surface (the §"Four-Region Cache Layout" amendment) is produced by
two orthogonal partitions applied in sequence. The protocol is: **bucket first,
then zone.**

1. **Bucket partition** (`prompt_framework/bucket.py`). Every registered section
   has a name. `default_bucket_for_section(name)` (`bucket.py:99-108`) routes the
   section to `SectionBucket.System` iff its name is in `STABLE_SECTION_NAMES`
   (`bucket.py:28-96`), else to `SectionBucket.User`. The allowlist default is
   **User** — anything per-turn (state, encounter, magic ledger, player action,
   recency guardrails) must be left off the list. Adding a name here is the
   load-bearing decision ADR-112 governs; the *routing* it triggers is governed
   here.
2. **Zone partition within the System bucket** (`prompt_framework/core.py`).
   `compose_split_by_zone(agent_name)` (`core.py:194-246`) returns
   `(system_by_zone, user_text)`: it walks zone-sorted sections, sends
   System-bucket sections into a `{AttentionZone: text}` dict
   (`core.py:233-235`) and all User-bucket sections into `user_text`
   (`core.py:236-237`). Section content for any zone is byte-stable across calls
   given identical registered sections — the gate referenced in the docstring
   (`tests/agents/test_cache_ttl_prefix_and_otel.py`).

The orchestrator then maps zones to cacheable blocks
(`orchestrator.py:3726-3766`):

- `Primacy + Early` → `stable_text` → `system_blocks[0]` with **`cache=True`**
  (`orchestrator.py:3745-3762`)
- `Valley` → `system_blocks[1]`, **`cache=False`** (`orchestrator.py:3753,3763-3764`)
- `Late + Recency` → `system_blocks[2]`, **`cache=False`**
  (`orchestrator.py:3754-3766`)

A section therefore rides the cached prefix iff **both** its bucket is System
**and** its zone is Primacy/Early. The GM-panel attribution helper
`_section_rides_cache(name, zone_value)` (`orchestrator.py:125-139`) computes
exactly this conjunction from the same inputs, so the panel cannot drift from the
SDK assembly. Zone alone is insufficient: Primacy/Early also hold User-bucket
guardrails that land in the uncached user message (`orchestrator.py:108-110`).

### C. Dual-TTL Split and the Correctness Stake

`anthropic_sdk_client.py` marks the cacheable surface at two TTLs, not one:

- **`self.cache_ttl`** — default `"1h"`, from `SIDEQUEST_ANTHROPIC_CACHE_TTL`
  (`anthropic_sdk_client.py:198-207`). Applied to `system_blocks[0]` (the stable
  prefix) in `_build_system_array` (`anthropic_sdk_client.py:1122`) and to the
  last tools entry in `_build_tools_array` (`anthropic_sdk_client.py:1150`).
  These are session-static and amortize across turns; the 1h tier's 2× write
  premium pays off because the content persists and is re-read every turn. The
  `1h` value additionally requires the extended-cache beta header, sent only on
  the 1h path — without it the request 400s (No Silent Fallback;
  `anthropic_sdk_client.py:150-152,319-325`).
- **`_VOLATILE_CACHE_TTL`** — `"5m"` (`anthropic_sdk_client.py:147`). Applied to
  the moving breakpoint on the per-turn user/recency tail in the tool-use
  continuation loop (`anthropic_sdk_client.py:1091-1097`). The tail changes every
  turn, so a 1h (2×) write on it would be invalidated within the hour — pure
  waste (the documented 60-3 incident). The 5m breakpoint's *presence* every iter
  is the 60-7 fix; its 5m *value* is the 61-19 fix.

**The correctness stake.** Because `system_blocks[0]` is marked at 1h and re-read
every turn, any *per-turn* content that leaks into it re-mints the expensive 1h
prefix every single turn — paying the 2× write premium continuously instead of
once. That is why the bucket/zone partition above is load-bearing for *cost*, not
just attention: a section misclassified as System (or mis-zoned into
Primacy/Early) silently destroys the cache rebate. The byte-stability test on
`system_blocks[0]` and the `narration.turn.system_block_sizes_json` OTEL attribute
(`orchestrator.py:3804-3809`) exist precisely so this drift surfaces in the GM
panel rather than as cache-write growth on the Anthropic console.

### Governance summary

ADR-101 cited `model_routing.py`, `prompt_framework/core.py`,
`prompt_framework/bucket.py`, and `anthropic_sdk_client.py` as live. This
amendment promotes them to governed contracts: (1) the `CallType` taxonomy and
`resolve_model` + `pack_overrides` routing seam, and (2) the bucket→zone
cache-partition protocol with its dual-TTL (1h stable prefix / 5m volatile tail).
ADR-112 decides *which* sections are promoted to Stable; this amendment governs
the partition mechanism that turns that decision into cached or uncached bytes.
