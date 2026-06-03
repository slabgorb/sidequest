---
id: 112
title: "Genre Prose Cache Promotion — Four Always-Fire Session-Static Sections Move to Stable, Conditional Sections Defer"
status: accepted
date: 2026-05-19
deciders: ["Keith Avery", "Major Margaret Houlihan (Architect)"]
supersedes: []
superseded-by: null
related: [9, 98, 101, 110, 111]
tags: [agent-system, prompt-engineering, observability]
implementation-status: partial
implementation-pointer: sprint/current-sprint.yaml#57-3
---

# ADR-112: Genre Prose Cache Promotion — Four Always-Fire Session-Static Sections Move to Stable, Conditional Sections Defer

## Status

Accepted. Implementation tracked under epic 57 (Narrator Prompt Token
Reduction), story 57-3. This ADR ratifies the mutability rubric used to
classify genre prose sections as Stable-cacheable, names the four sections
that pass the rubric today, and explicitly defers the conditional genre
sections (`genre_combat_voice`, `genre_chase_voice`) under a documented
cache-thrash concern.

## Context

The narrator prompt framework owns a binary classifier:
`prompt_framework.bucket.default_bucket_for_section()` returns
`SectionBucket.System` for any section name in `STABLE_SECTION_NAMES`,
`SectionBucket.User` otherwise. The System bucket flows into the cached
`system=` array on the Anthropic SDK path (ADR-101 Phase D Task 6); the
User bucket flows into the uncached per-turn user message.

The current allowlist at `bucket.py–41` covers ten section names:

```
narrator_identity
narrator_dialogue
soul_principles
output_format
genre_identity
genre_narrator_voice
genre_npc_voice
genre_world_state
narrator_vocabulary
genre_transition_hints
```

Six genre-prose sections are registered on every narrator turn at
`orchestrator.py–1385` but are **not** on the allowlist:

| Section name | Site | Zone | Registration condition | Source |
|---|---|---|---|---|
| `genre_combat_voice` | `:1306` | Early | `context.in_combat` | `prompts.yaml gp.combat` |
| `genre_chase_voice` | `:1318` | Early | `context.in_chase` | `prompts.yaml gp.chase` |
| `genre_extraction` | `:1330` | Valley | unconditional | `prompts.yaml gp.extraction` |
| `genre_keeper_monologue` | `:1342` | Valley | unconditional | `prompts.yaml gp.keeper_monologue` |
| `genre_town` | `:1353` | Valley | unconditional | `prompts.yaml gp.town` |
| `genre_chargen` | `:1364` | Valley | unconditional | `prompts.yaml gp.chargen` |

The token-cost audit estimated 1–3 KB per section, with the four
unconditional Valley-zone sections contributing 4–12 KB / 1–3 k tokens to
the **uncached** Valley block on every narrator turn. Their content is
genre-pack-static — sourced from `prompts.yaml` which is read once per
session at pack load and never mutated mid-session — so per-turn
recomputation pays no information dividend.

> **⚠️ KNOWN ISSUE (Story 60-3, 2026-05-22): the amortization described in
> this section does NOT currently materialize.** The Stable block IS byte-stable
> and correctly marked 1h, but the narrator runs a tool-use loop, and every
> continuation call re-mints the whole prefix at 5m because the growing
> `tool_use`/`tool_result` conversation carries no cache breakpoint. So promoting
> prose into Stable is still *correct* (it's the right zone), but the cache rebate
> is not realized until Story 60-4 adds a moving 1h breakpoint on the continuation.
> The byte-identity invariant below remains load-bearing and unchanged. See
> `sprint/archive/60-3-session.md`.

The cache contract behind the savings: ADR-101 Phase D ships three
`system=` blocks; the first (Stable) carries `cache_control={"type":
"ephemeral", "ttl": "1h"}` and is *intended to* amortize its cost over every
turn after cache warmup (but see the Known Issue above — amortization is
defeated by the tool-loop continuation until 60-4). The current allowlist's
content is correctly cached on the first (non-continuation) call; any
section meeting the same byte-identity-across-turns invariant pays only
on the first turn after the pack loads — once 60-4 lands.

`STABLE_SECTION_NAMES` is described at `bucket.py–27` as
*"Section names whose content is byte-identical across every turn of the
same game given fixed operator settings."* That is the load-bearing
invariant. Violating it — registering a section into `STABLE_SECTION_NAMES`
whose content varies per-turn — is worse than leaving it uncached: a
mutating Stable section invalidates the cache root on every turn, so
**every** Stable section above it pays the cache-miss cost in addition to
no longer amortizing itself.

Conditional registration interacts badly with Stable classification.
`genre_combat_voice` is registered only when `context.in_combat` is true.
If it joined `STABLE_SECTION_NAMES`, the System block's bytes would
change at every combat boundary:

- Turn N (peace, not registered) → System block has no `genre_combat_voice` → cache key A
- Turn N+1 (combat starts, registered) → System block contains `genre_combat_voice` → cache key B (cache MISS, full system-block re-write)
- Turn N+2 (still combat, registered) → cache key B (cache HIT)
- Turn N+3 (combat ends, not registered) → cache key A (cache MISS)

Each encounter boundary would force a full Stable-block re-cache. The
amortization model only works for sections that are *always-on* relative
to a given fixed-cost cache root.

## Decision

**Promote the four unconditional, session-static genre prose sections into
`STABLE_SECTION_NAMES`. Defer the two conditional sections under a
documented cache-thrash concern.**

### Promote

Add to `bucket.STABLE_SECTION_NAMES`:

- `genre_extraction`
- `genre_keeper_monologue`
- `genre_town`
- `genre_chargen`

> **Superseded in part — see Amendment 2026-05-25 below.** Story 61-11
> later **demoted `genre_chargen`** (removed from `STABLE_SECTION_NAMES`,
> now conditionally registered + User-bucketed) and **deferred
> `genre_extraction` / `genre_keeper_monologue`** (no runtime signal for
> per-scene relevance; they remain in the allowlist but their attention
> budget is suboptimal). Only `genre_town` carries forward as originally
> promoted. The four-section list above is the *as-decided* state; read
> the 2026-05-25 amendment for the *as-shipped* state.

Each section's registration site at `orchestrator.py–1411` keeps
the same name, content, and `SectionCategory.Genre`. The attention zone
is changed from `Valley → Early` so the System-bucket content actually
lands in the cache-marked `system_blocks[0]` block; the bucket
classifier alone is insufficient under the ADR-101 Phase D Task 6
zone-aligned cache split (only Primacy + Early compose the cached
`stable_text`). The bucket classifier change at `bucket.py` AND the
four `AttentionZone.Early` updates at the registration sites are the
two edits needed to route the content into the cached System block.

> **2026-05-20 amendment (Story 57-3 implementation):** This block was
> originally "registration site unchanged … classifier change is the
> only edit needed." That claim missed a load-bearing interaction with
> ADR-101 Phase D Task 6, which only caches `Primacy + Early` zones —
> Valley-zone System content rides `system_blocks[1]` uncached. The
> required `Valley → Early` re-zone is small (four `AttentionZone`
> argument flips) and is consistent with §Consequences:Negative below
> which already documented the attention-zone shift as accepted.

### Defer

Do not promote `genre_combat_voice` or `genre_chase_voice` in this story.
Their conditional registration shape is incompatible with Stable
classification (cache thrash at every encounter boundary), and the
straightforward fix — unconditional registration — has its own cost: the
combat/chase prose would ride in the prompt on every peace turn and could
subtly bias the narrator's tone away from genre-default toward genre-
combat. The right home for those sections is a follow-up story that
either:

1. Accepts the unconditional inclusion (audit each genre pack's combat
   prose for "peace-safe" framing), or
2. Builds a third cache zone with a shorter TTL that boundary-crosses
   gracefully, or
3. Leaves them in User and accepts the per-combat-turn cost.

This ADR does not pre-decide that choice; it documents the deferral so
57-3 ships clean and the conditional question gets its own analysis.

### Mutability rubric (forward-applicable)

Any future section proposed for `STABLE_SECTION_NAMES` MUST pass all four
checks:

1. **Registered unconditionally.** The section is added to the registry
   on every narrator turn (no `if context.x` guard at the registration
   site). Conditional registration plus Stable classification produces
   cache thrash; ship one or the other, not both.
2. **Source is session-static.** The content is sourced from a value
   that does not mutate mid-session: a genre-pack YAML field, a project
   constant, the narrator persona, etc. Any field that the narrator can
   change via tool call or that the dispatcher updates per-turn fails
   this check.
3. **Operator-setting-stable.** The content does not vary with per-turn
   operator inputs — verbosity axis, tone axis, dynamic vocabulary tier.
   If the field can change *within a session* via a runtime tone command
   or an `/axis` adjustment, it fails this check even though it is
   "session-static" in the colloquial sense.
4. **No per-turn data interpolation.** The rendered prose contains no
   per-turn variables — no character name, no current location, no turn
   counter, no recent action. String interpolation that produces
   byte-different output per turn fails by definition.

The four promoted sections satisfy all four checks. The deferred
conditional sections fail check 1.

### Forward-applicable validator (not blocking, flagged)

A potential follow-up is a runtime assertion that every section name in
`STABLE_SECTION_NAMES` produced byte-identical content across the last
N turns of a save. The OTEL surface for this is straightforward — hash
each registered Stable section's content per turn and emit a span on
mismatch — but is not in 57-3's scope. Flagging here so it does not get
lost.

### Observability discipline (mandatory per repo CLAUDE.md)

Add one OTEL span at the bucket-classifier hand-off (one shot per turn,
at the System/User partition step in `orchestrator.compose_split_by_zone`
or the equivalent SDK-path partition site):

```
narrator.system_block_composition {
  stable_section_names: list[str],         # the allowlist applied this turn
  stable_section_bytes: int,               # total bytes routed to System
  user_section_bytes: int,                 # total bytes routed to User
  cache_warm: bool,                        # heuristic: turn_number > 0
}
```

This is the per-turn proof the classifier change is engaged AND it
catches a future regression — a section silently leaving the allowlist
because of an unrelated edit would show up as `stable_section_bytes`
dropping by the migrated section's size.

The existing prompt-zone size instrumentation continues to fire; this
new span specifically targets the System/User partition, which is the
cache-payoff seam.

### Note flagged for follow-up: `narrator_vocabulary` invariant audit

The token-cost audit characterized `narrator_vocabulary` as "per-turn
dynamic." `narrator_vocabulary` is on the current `STABLE_SECTION_NAMES`
allowlist. Either the audit overstated dynamism (the section is keyed
off a session-stable operator setting and its content is identical
across turns) or the section is incorrectly classified and is silently
thrashing the cache. This is **not** in 57-3's scope, but the new
`narrator.system_block_composition.stable_section_bytes` span will
expose any per-turn mutation. **If the value oscillates, file a
follow-up immediately** — silent cache thrash is the most expensive
kind of regression because it cancels every other section's
amortization.

### Acceptance gate

Story 57-3 is complete when, on a representative recorded playtest
replay exercising the SDK backend:

1. The four promoted section names appear in
   `narrator.system_block_composition.stable_section_names` on every
   turn after the first.
2. `narrator.system_block_composition.stable_section_bytes` is **stable
   turn-to-turn** across turns 2…N within the same save (allowing for
   conditional sections like an in-combat boundary on `genre_npc_voice`
   if any registration shape were to change — none expected from this
   migration). Any oscillation in the value indicates a non-Stable
   section was wrongly promoted; revert that section's promotion.
3. The per-turn `user_section_bytes` drops by **≥ 4 KB** relative to
   the pre-change baseline measured on the same replay.
4. The narrator output on a side-by-side comparison of the pre- and
   post-change runs shows no regression in genre-tone fidelity for
   `genre_extraction`, `genre_keeper_monologue`, `genre_town`, or
   `genre_chargen` content surfaces (extraction scenes, keeper-tier
   monologues, town descriptions, character creation prompts). The
   migration moves prose between buckets; it does not change what the
   model receives in aggregate. A regression here implies an
   attention-zone effect (Valley → System reading-order shift) and
   would warrant per-section restoration on a case-by-case basis with
   a documented `# KEEP — attention regression on $scene` comment.

## Consequences

### Positive

- **Direct cost reduction on every SDK turn after warmup:** 1–3 k tokens
  / turn relocated from the uncached Valley block to the cached Stable
  block. Multiplied by playtest turns over the life of a save, this is
  the most boring possible cost cut — a single allowlist edit — and the
  amortization is automatic.
- **Mutability rubric formalized:** the four checks above become the
  written gate for future `STABLE_SECTION_NAMES` additions. The current
  allowlist was assembled organically; this ADR turns the assembly rule
  into a checked invariant.
- **Latent cache-thrash bug surface lit up:** the new system_block_
  composition span exposes any future section that silently violates the
  byte-identity invariant. The unchecked invariant today is load-
  bearing — the audit caught at least one suspicious case
  (`narrator_vocabulary`) that needs verification.

### Negative

- **Attention-zone shift for the four sections.** Valley → System is a
  reading-order change. The Stable block leads the prompt; Valley sits
  mid-prompt. ADR-009's attention-aware zone model puts Primacy and
  Recency at the extremes of attention and Valley in the middle. The
  promoted sections were authored against Valley attention; reading them
  in the System block earlier in the prompt could subtly shift weight.
  Mitigation: the acceptance gate's narrator-output comparison catches
  observable regressions; the rubric does not permit silent restoration —
  any KEEP requires a documented incident reference.
- **Cache-invalidation cost on `prompts.yaml` edits:** any edit to a
  genre pack's `extraction`/`keeper_monologue`/`town`/`chargen` prose
  invalidates the Stable block for every active save in that pack. The
  invalidation cost is one cache write per affected save; rapid
  iteration on those prose blocks is more expensive after this change
  than before. Mitigation: pack-prose edits are reviewed at ADR cadence,
  not per-playtest.
- **Allowlist surface area growing without an enforcement mechanism.**
  Adding four entries makes the allowlist 40 % larger. The mutability
  rubric is documented prose, not enforced code. Mitigation: the
  follow-up validator (flagged above) is the right enforcement seam if
  the allowlist drift becomes a regression source.

### Neutral

- The four registration sites at `orchestrator.py–1411` have
  `AttentionZone.Early` (re-zoned from Valley by Story 57-3 — see the
  2026-05-20 amendment in §Decision:Promote above). Same name, same
  category (Genre). The bucket-classifier change AND the zone change
  together route the content into the cached System block. The
  attention-zone shift documented as a known consequence in
  §Consequences:Negative is now realized.

## Alternatives Considered

### A. Promote all six (including combat / chase voice)

Add all six genre prose sections to `STABLE_SECTION_NAMES`.

Rejected. The cache-thrash analysis above shows the two conditional
sections would invalidate the Stable cache root at every encounter
boundary. On a save that crosses N combat boundaries, the rebate from
caching the four unconditional sections is offset by 2N full Stable-block
cache misses. The math is bad unless the conditional sections become
unconditional first, which is a separate decision (genre-pack-prose
audit for peace-safe framing) outside 57-3's scope.

### B. Unconditional registration for combat / chase, then promote

Drop the `context.in_combat` / `context.in_chase` guards at the
registration sites and add all six to the allowlist.

Rejected for this story. Unconditional combat / chase prose may bias
narration during peace turns. The audit work to verify per-pack peace-
safe framing is meaningful for six current packs plus five workshop
packs (per `CLAUDE.md`'s pack list). That audit is its own story, not a
sub-step of a classifier-widening change.

### C. New "Conditional-Stable" bucket with a shorter TTL

Introduce a third cache block with a TTL of 5 minutes (Anthropic
ephemeral cache) for sections that are stable while active but blink
on/off. Combat / chase voice ride there.

Rejected as premature. Three cache blocks already exist (Stable, Valley,
Late+Recency per ADR-101 Phase D). A fourth introduces ordering and TTL
coordination complexity. If the conditional-genre-prose cost proves
worth it after this story ships, that decision gets its own ADR with
concrete savings numbers.

### D. Audit the existing allowlist; remove `narrator_vocabulary` if dynamic

Investigate the `narrator_vocabulary` per-turn-dynamic claim from the
token-cost audit before adding new sections.

Partially adopted. The mutability rubric's check 3 names the suspect
behavior, and the new OTEL span will expose it on the next replay. But
proactively *removing* `narrator_vocabulary` before evidence is the
wrong direction — if it is genuinely stable, removal pays a per-turn
cost for no benefit. The right pattern: ship 57-3 with the four
promotions and the new span, then read the span's `stable_section_bytes`
oscillation behavior on the first post-merge replay. If
`narrator_vocabulary` is dynamic, the bytes value moves and a follow-up
story drops it from the allowlist. If it is stable, the value holds and
no further action is needed.

## Implementation Notes

- The change is a one-line edit to the frozenset in
  `prompt_framework/bucket.py`. No new module, no constructor changes,
  no migration path. The four registration sites are byte-for-byte
  unchanged.
- The new OTEL span belongs at the System/User partition point — wherever
  the SDK path consumes the `default_bucket_for_section` classifier to
  build the `system=` array vs the user `messages[0]` content. Today
  that is `orchestrator.py–3193` per the audit; the implementation
  pass verifies the exact line.
- Tests (per the server-side wiring-test rule): a unit test asserts the
  four section names resolve to `SectionBucket.System` under
  `default_bucket_for_section`. An integration test against a fixture
  genre pack asserts the four sections appear in the assembled
  `system=` array and **do not** appear in the user message. A
  byte-identity test runs three consecutive turns on a fixed snapshot
  and asserts `stable_section_bytes` is identical across all three.
- Coordinates with ADR-110 and ADR-111: independent. ADR-110 shrinks
  the Valley-zone `<game_state>` blob in-place; ADR-111 removes
  Recency-zone guardrail prose from the user message on the SDK path;
  this ADR moves four Valley-zone sections into the cached System
  block. The three stories touch overlapping files
  (`orchestrator.py`, `session_helpers.py`, `bucket.py`,
  `narrator_prompts/`) but not overlapping lines. Any merge order is
  safe; conflicts are mechanical if they occur.

## Amendments

### 2026-05-25 — `genre_chargen` demoted; `genre_extraction` / `genre_keeper_monologue` deferred

Story 61-11 (sidequest-server PR #403, commit `476c3bd` on develop)
partially reversed the four-section promotion from Story 57-3:

1. **`genre_chargen` demoted to User bucket.** Removed from
   `STABLE_SECTION_NAMES`; registration gated on
   `TurnContext.opening_directive` (the sole existing runtime signal
   that distinguishes character-creation turns from normal play).
   Chargen prose was firing on every turn despite being relevant only
   during character creation — unconditional registration satisfied the
   mutability rubric (check 1) but violated its *spirit*: always-fire
   is wasteful when the section's content is irrelevant 95% of the
   time. The predicate gate fixes the waste; demotion from Stable
   follows because conditional registration fails check 1.

2. **`genre_extraction` and `genre_keeper_monologue` deferred — no
   runtime signal.** These sections remain unconditionally registered
   (they pass the mutability rubric) but their scene-scoped content
   fires on every turn regardless of whether the scene type matches.
   No existing runtime signal expresses "this is an extraction scene"
   or "keeper monologue is relevant." Future stories must either build
   runtime signals (analogous to `context.in_combat`) or migrate these
   sections to ADR-113's tool-attached scope model. Until then they
   stay in `STABLE_SECTION_NAMES` — the cache math is still correct
   even if the attention budget is suboptimal.

3. **`genre_town` unchanged — deferred per original §Defer.** High
   firing rate; needs profiling before any reclassification. No action
   taken by 61-11.

4. **Net state of `STABLE_SECTION_NAMES` after 61-11:** the four
   sections promoted by 57-3 are now three (`genre_extraction`,
   `genre_keeper_monologue`, `genre_town`). `genre_chargen` is
   conditionally registered and User-bucketed.

## References

- ADR-009 — Attention-Aware Prompt Zones (the zone model the
  promoted sections are migrating across)
- ADR-098 — Stateless Narrator Turns (the bounded-prompt regime the
  cache amortization operates within)
- ADR-101 — Anthropic SDK as Narrator Backend (the three-zone caching
  split this ADR exploits)
- ADR-110 — Game-State Snapshot Slimming (sibling story 57-5)
- ADR-111 — Recency-Zone Narrator Guardrails Migrate to Tool
  Descriptions (sibling story 57-4)
- `sidequest-server/sidequest/agents/prompt_framework/bucket.py` — the
  allowlist this ADR edits
- `docs/superpowers/specs/2026-05-10-stateless-narrator-design.md` —
  the spec § cited by `bucket.py` for the mutability invariant
