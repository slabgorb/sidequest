# Confrontation Intent Validator — Design

**Date:** 2026-05-20
**Status:** Design (pending implementation plan)
**Driver bug:** Dust and Lead horse-purchase scene (2026-05-20 save) — 5-turn negotiation played as freeform prose; zero `confrontation.*` OTEL spans fired.
**Related ADRs:** ADR-033 (Confrontation Engine), ADR-067 (Unified Narrator Agent — supersedes ADR-010), ADR-031 (Game Watcher Semantic Telemetry), ADR-103 (Native OTEL via Tool Registry). ADR-067 amendment forthcoming.

---

## Problem

When the narrator generates prose that semantically constitutes a confrontation
(negotiation, standoff, combat, etc.) but does not emit the `confrontation`
field in its tool-use output, the scene plays as freeform fiction. No mechanical
scaffolding fires — no metrics, no beats, no encounter UI, no OTEL spans. The
GM panel cannot tell the difference between "no confrontation was warranted"
and "the narrator forgot." Sebastien-axis mechanical visibility collapses on
exactly the scenes that have the most mechanical stakes.

The 2026-05-20 dust_and_lead horse purchase is the load-bearing example:
five consecutive turns of textbook negotiation prose (`"Fifty don't cover the
feed she's eaten"`, `"Sixty. She's yours"`, `"Eight dollars. Take it or leave
it"`) produced zero confrontation telemetry. Every beat of the `negotiation`
def from `spaghetti_western/rules.yaml` was present in prose; none was claimed
in structure.

Today's lie-detector — `_CONFRONTATION_TRIGGER_PATTERNS` in
`narration_apply.py:431` — is a hardcoded tuple of nine regex patterns
covering only combat and dogfight phrases. The file's own comment at line 425
anticipates this exact playtest moment: *"If a future playtest shows
negotiation under-firing, add patterns here."*

## Doctrinal constraints

Two project doctrines bound the design space:

- **The Zork Problem (SOUL.md).** Surface-level prose regex against arbitrary
  natural-language output is the parser-game failure mode. Keyword matching
  over narration text — even when matching against narrator output rather
  than player input — implies a closed lexicon and degrades signal as
  paraphrase widens.

- **One mechanism per problem
  (`memory/feedback_one_mechanism_per_problem.md`).** Two parallel
  detection systems for the same phenomenon are how SideQuest accumulates
  "we don't know what's actually happening" debugging hell. A migration
  from old to new is a clean cutover, not an additive layer.

## What we already have

A reuse-first audit of intent infrastructure in the server codebase
(2026-05-20) found pre-existing but dormant scaffolding:

- `ActionRewrite.intent` (`orchestrator.py:272`) — a nullable string field
  the narrator emits on every turn per `output_only_sdk.md:224`. Extracted
  and carried through `NarrationTurnResult`. **No downstream consumer.**
  Dead infrastructure.

- `TurnRecord.classified_intent` (`telemetry/turn_record.py:35`) — hardcoded
  to the literal string `"unknown"` on every turn at
  `websocket_session_handler.py:4696`. A stub for OTEL the lie-detector layer
  was meant to populate.

- **ADR-067 (accepted, live)** explicitly states: *"Intent is inferred, not
  classified. The narrator's response implicitly contains intent
  information. Post-narration extraction... extracts the action type from
  the response for OTEL logging and state machine transitions."* The
  inference site was never built.

- ADR-031 specifies an `intent_router.classify` telemetry span that does
  not exist in the Python codebase.

The "great deal of work on intent" turns out to be three accepted-but-unwired
design promises. This design delivers them, rather than building a parallel
system.

## Decision

Activate `ActionRewrite.intent` as the authoritative intent field by adding
its first real downstream consumer: a `confrontation_intent_validator` that
checks the narrator's declared intent against its declared confrontation
choice, using vocabulary owned by each confrontation def in pack YAML.

The validator is the inference site ADR-067 promised. Its output also
populates `TurnRecord.classified_intent`, eliminating the hardcoded
`"unknown"` stub.

`_CONFRONTATION_TRIGGER_PATTERNS` and `_scan_for_confrontation_trigger_keywords`
are deleted in the same change. No prose regex survives. One mechanism, one
source of truth.

## Locked decisions

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| 1 | Scope | Architectural framework, not symptom patch | The pattern (narrator chooses confrontation discretionarily, lie-detector covers only combat) generalises beyond negotiation; we fix the class, not the instance. |
| 2 | Match consequence | Hybrid per type (warn / soft_suggest / reprompt) | Bang catalog enforcement should vary by Bang weight. Standoff missing combat has lethality implications; negotiation missing scaffold is a missed beat, not a missed life. |
| 3 | Intent vocabulary source | Derived from `label` + `beats[].label`, extensible via optional `intent_verbs:` | Auto-derivation gives every confrontation a sane default at authorship time; explicit extension is the steam valve where label tokens undercount. |
| 4 | Reprompt mechanism | Full re-run, single attempt, fall through to warn | Re-narration from scratch lets the narrator restructure the turn around the confrontation it should have opened. Single attempt keeps latency bounded and surfaces persistent failures to the GM panel. |
| 5 | Legacy patterns | Delete entirely | Parallel detection systems are how SideQuest accumulates "we don't know what's actually happening" debt. Single mechanism, clean cutover. |

## Out of scope

- **NPC-initiated confrontations.** When an NPC commits to engagement
  (`"the bandit draws his pistol"`) while the player's intent is benign
  (`"look around the room"`), the player's `action_rewrite.intent` does not
  carry the trigger. Intent-channel detection has a genuine blind spot here.
  The deleted prose regex never reliably solved it either. File as a
  follow-up spec covering narrator output contract (possible second intent
  field for NPC initiative, or a different mechanism entirely).

- **Pre-narration intent classification.** ADR-067 killed this with cause
  (8-17s latency hit). Not revisited.

- **Multi-confrontation turns.** A turn that touches two confrontation types
  in the same prose is rare enough that the deterministic tie-break
  (most-tokens-matching, pack-order) is sufficient. If playtest evidence
  shows otherwise, this spec gets a follow-up.

## Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│ Player action ──► Narrator (Anthropic SDK, ADR-101)                │
│                       │                                            │
│                       ▼                                            │
│   tool-use output (unchanged from today):                          │
│   {                                                                │
│     action_rewrite: {you, named, intent: "negotiate horse price"}  │
│     confrontation: None       ◄── the lie when present             │
│     ...                                                            │
│   }                                                                │
│                       │                                            │
│                       ▼                                            │
│   _extract_from_narration_result  (unchanged)                      │
│                       │                                            │
│                       ▼                                            │
│   ┌─────────────────────────────────────────────────────────┐      │
│   │ confrontation_intent_validator.validate(...)   ◄── NEW  │      │
│   │ ─ reads action_rewrite.intent (was dead, now wired)     │      │
│   │ ─ reads confrontation choice                            │      │
│   │ ─ reads pack.intent_verbs_by_type (cached at load)      │      │
│   │ ─ returns ValidationResult or None                      │      │
│   └─────────────────────────────────────────────────────────┘      │
│                       │                                            │
│              ┌────────┴────────┐                                   │
│              │                 │                                   │
│         match found        no match                                │
│              │                 │                                   │
│              ▼                 ▼                                   │
│   dispatch per-type       apply narration                          │
│   on_intent_mismatch:                                              │
│     ├─ warn ───────► OTEL + classified_intent = match.type         │
│     ├─ soft_suggest ► OTEL + directive queued for turn N+1         │
│     └─ reprompt    ► re-invoke narrator once with directive        │
│                       ├─ comply ─► continue                        │
│                       └─ fail ──► warn + apply first attempt       │
│                                                                    │
│   AT EVERY EXIT, TurnRecord.classified_intent IS POPULATED         │
│   from action_rewrite.intent (or the matched type when mismatch)   │
│   ─ never "unknown" again.                                         │
└────────────────────────────────────────────────────────────────────┘
```

### Load-bearing properties

- **One mechanism.** `_CONFRONTATION_TRIGGER_PATTERNS` and
  `_scan_for_confrontation_trigger_keywords` are deleted in the same change.
  No prose regex survives.
- **One source of truth for intent.** `ActionRewrite.intent` is THE intent
  field. The validator is its only downstream consumer doing semantic work;
  the telemetry path passively reflects the same field.
- **One source of truth for vocabulary.** Each confrontation def in
  `rules.yaml` is self-describing: `label` + `beats[].label` derive the
  baseline intent verb set at pack-load time; optional `intent_verbs:`
  extends it; optional `on_intent_mismatch:` declares the D-behavior.
- **One ADR debt paid.** ADR-067's promise is delivered by the same change.
- **Telemetry stops lying.** `TurnRecord.classified_intent` is populated
  from `action_rewrite.intent` (or `validation_result.matched_type`) on
  every turn. The hardcoded `"unknown"` is removed.

### What does NOT change

- The narrator's tool-use output contract (no new required fields).
- The narrator's prompt assembly (already instructs `action_rewrite.intent`
  per `output_only_sdk.md:224`).
- ADR-067's unified-narrator topology — no specialist agents, no
  pre-narration classifier, no router resurrected from ADR-010.
- ADR-031's `intent_router.classify` span stays unimplemented; the
  validator's `confrontation.intent_mismatch` span replaces its role.

## Components

### NEW — `confrontation_intent_validator` module

**Path:** `sidequest-server/sidequest/agents/confrontation_intent_validator.py`

**Surface:**
```python
@dataclass(frozen=True)
class ValidationResult:
    matched_type: str
    declared: str | None
    severity: Literal["warn", "soft_suggest", "reprompt"]
    matched_tokens: tuple[str, ...]

def validate(
    action_rewrite: ActionRewrite | None,
    declared_confrontation: str | None,
    pack: Pack,
    *,
    active_encounter: bool,
) -> ValidationResult | None: ...
```

**Contract:**
- Returns `None` when there is nothing to flag (declared matches, no intent,
  encounter already active, or no type's vocabulary matches).
- Multi-match tie-break: most token overlap wins; ties broken by
  pack-declaration order (deterministic).
- Never raises on bad input.
- Pure function. No I/O. Stateless.

**Tokenization rules** (encapsulated, not in YAML):
- Lowercase, split on non-alphanumeric.
- Strip ~20 stopwords (`the`, `a`, `an`, `to`, `for`, `with`, `in`, `on`,
  `at`, `of`, `and`, `or`, etc.).
- Light suffix stripping: `-ing`, `-ed`, `-s`. No Porter stemmer (too
  aggressive — would conflate "draw" / "drawer").
- Applied identically at pack-load and at validation time.

### NEW — Pack-load intent vocabulary derivation

Extend the rules.yaml loader. At load time, for each `ConfrontationDef`,
compute and cache `intent_verb_set: frozenset[str]`:
- Tokenize `label` and every `beats[].label`.
- Union with the optional declared `intent_verbs:` list (tokenized
  identically).
- Cache on the `ConfrontationDef` dataclass.

The pack object exposes `pack.intent_verbs_by_type: dict[str, frozenset[str]]`
for the validator.

### REFACTORED — `ConfrontationDef` schema (sidequest-content)

Two optional fields added to every confrontation def:

```yaml
- type: negotiation
  label: "Tense Negotiation"
  intent_verbs: [haggle, bargain, barter, offer, deal, price, sell, buy]
  on_intent_mismatch: warn
```

`on_intent_mismatch` accepts: `warn` | `soft_suggest` | `reprompt`. Defaults
to `warn` when omitted so unmodified packs continue to load.

**Initial migration policy across the 7 production packs** (authored as part
of this work, not deferred). The migration enumerates every confrontation
type that actually exists in each pack and assigns a default per the
categories below; the table is the policy, not a complete type list:

| Category | Default | Reasoning |
|---|---|---|
| Lethal / Genre-Truth heavy (combat, standoff, dogfight, and any pack-specific equivalents) | `reprompt` | Lethality implications; missing these is a high-cost failure |
| Social-pressure / transactional (negotiation, poker, and any pack-specific equivalents — e.g. tea_and_murder's drawing-room standoffs) | `warn` | Tune toward `soft_suggest` per playtest evidence |
| Anything else | `warn` | Conservative default |

`sidequest/cli/validate.py` gains a schema check: unknown values for
`on_intent_mismatch` fail loudly at pack load.

### REFACTORED — `narration_apply` dispatch

**Path:** `sidequest-server/sidequest/server/narration_apply.py`

The call site at line 2533 — where `_scan_for_confrontation_trigger_keywords`
is invoked today — is replaced:

```python
# OLD
matched_triggers = _scan_for_confrontation_trigger_keywords(result.narration)

# NEW
mismatch = confrontation_intent_validator.validate(
    result.action_rewrite,
    result.confrontation,
    pack,
    active_encounter=snapshot.encounter is not None,
)
```

Branch on `mismatch.severity`:
- `warn` → emit OTEL span; apply normally.
- `soft_suggest` → emit OTEL span + append to
  `snapshot.next_turn_directives`; apply normally.
- `reprompt` → return a `RepromptRequest` to the orchestrator; do not apply
  narration yet.

In every branch — including `mismatch is None` — `TurnRecord.classified_intent`
is populated:
- `mismatch is None` → from `action_rewrite.intent` verbatim (empty string
  if intent itself was empty — see error-handling rules).
- mismatch present → `mismatch.matched_type` (the inferred truth).

### REFACTORED — Orchestrator reprompt loop

**Path:** `sidequest-server/sidequest/agents/orchestrator.py`

Single-iteration retry wrapper around the narration call. Pseudocode for
the shape — concrete signatures (including whether the directive is passed
via a new `extra_directive` parameter to the narrator entry point, an
injection into the recency-zone assembly, or another channel) are
implementation-plan decisions:

```python
result = narrator.run(...)
applied = narration_apply._apply_narration_result_to_snapshot(result, ...)
if applied.reprompt_request and not already_reprompted:
    result = narrator.run(..., extra_directive=applied.reprompt_request.directive)
    applied = narration_apply._apply_narration_result_to_snapshot(
        result, ..., already_reprompted=True
    )
```

`already_reprompted=True` forces the second-call dispatcher to degrade
`severity=reprompt` to `warn`. Bounded at exactly one retry.

The directive is a short structured string injected into the recency zone
of the second prompt:

> "Previous attempt described a `negotiation` (intent: 'negotiate horse
> price') but did not open one. Either set `confrontation=negotiation` or
> rewrite without negotiating language."

### NEW — `next_turn_directives` snapshot field

**Path:** the turn-scoped snapshot model in `sidequest-server/sidequest/game/`
(exact module to confirm during the implementation plan).

Add `next_turn_directives: list[str] = field(default_factory=list)` to the
shared-world snapshot. Consumed and cleared by prompt assembly at the start
of the next turn, rendered into the recency zone per ADR-049/111.

The shared-world placement is the working assumption; if perception
filtering (ADR-104/105) requires per-player scoping for directives that
should be visible only to specific seats, revisit during the implementation
plan. For the initial scope — confrontation type mismatches — shared-world
is correct because the missed encounter affects the whole table.

### DELETED — Legacy prose pattern detector

Removed in the same PR:
- `_CONFRONTATION_TRIGGER_PATTERNS` tuple (`narration_apply.py:431-475`).
- `_scan_for_confrontation_trigger_keywords` function
  (`narration_apply.py:478-498`).
- The `confrontation_trigger_constraint` watcher event format
  (`orchestrator.py:1882` area) — replaced by `confrontation.intent_mismatch`.
- All tests exercising the regex tuple — rebuilt against the validator.

GM panel and dashboard need a small update to surface the new event name —
included in this work, not deferred.

## Data flow

### Happy path (no mismatch)

```
1. Player submits action via WebSocket
2. orchestrator.process_action span opens
3. Narrator runs, produces tool-use output with action_rewrite + confrontation
4. _extract_from_narration_result builds NarrationTurnResult
5. confrontation_intent_validator.validate(...) → returns None
6. _apply_narration_result_to_snapshot proceeds normally
7. TurnRecord.classified_intent ← action_rewrite.intent (verbatim)
8. Narration broadcast; turn complete
```

No new latency. No new spans on the happy path beyond a single attribute
write to `classified_intent`.

### Mismatch dispatch (warn / soft_suggest)

```
5. validate(...) → ValidationResult{matched_type, declared, severity, matched_tokens}
6. Dispatcher branches on severity:

   severity = "warn":
     ├─ emit OTEL span: confrontation.intent_mismatch
     │    attributes: matched_type, declared_type, severity=warn,
     │                matched_tokens, reprompt_attempted=False
     ├─ classified_intent ← matched_type
     ├─ apply narration normally
     └─ broadcast; turn complete

   severity = "soft_suggest":
     ├─ emit OTEL span (severity=soft_suggest)
     ├─ classified_intent ← matched_type
     ├─ append to snapshot.next_turn_directives:
     │    "Last turn's intent suggested {matched_type}. If this scene is in
     │     fact a {matched_type}, open the encounter on this turn."
     ├─ apply narration normally
     └─ broadcast; turn complete
```

### Reprompt loop (severity = reprompt)

```
6. Dispatcher returns RepromptRequest; narration NOT yet applied
7. Orchestrator sees applied.reprompt_request set, already_reprompted=False:
   ├─ emit OTEL span: confrontation.intent_mismatch (attempt=1)
   ├─ narrator.run(..., extra_directive=...) — second call (~3-6s)
   ├─ _apply_narration_result_to_snapshot(..., already_reprompted=True)
   │
   ├─ Second-call dispatcher branches:
   │   ─ validate returns None → success
   │       ├─ emit confrontation.intent_mismatch_resolved (attempt=2)
   │       ├─ classified_intent ← matched_type
   │       └─ apply, broadcast, turn complete
   │
   │   ─ validate returns mismatch again → fall-through to warn
   │       ├─ emit confrontation.intent_mismatch
   │       │    (severity=warn, reprompt_attempted=True, outcome=fall_through)
   │       ├─ classified_intent ← matched_type
   │       ├─ apply the SECOND attempt's narration (newer wins)
   │       └─ broadcast, turn complete
   │
   │   ─ narrator second call raises:
   │       ├─ emit confrontation.intent_mismatch_reprompt_failed
   │       ├─ classified_intent ← matched_type (from first attempt)
   │       └─ apply the FIRST attempt's narration (player keeps their turn)
```

### Single exit invariant

Every code path through `_apply_narration_result_to_snapshot` populates
`TurnRecord.classified_intent` with a non-empty string before the turn ends.

| Scenario | Source of value |
|---|---|
| Happy path, no mismatch | `action_rewrite.intent` verbatim |
| Mismatch (any severity, any branch) | `mismatch.matched_type` |
| `action_rewrite` missing or empty intent | The literal `"unspecified"` — *not* `"unknown"`. Distinguishes "narrator omitted required output" from a real classification failure. |
| Reprompt failure paths | `mismatch.matched_type` from whichever attempt produced a ValidationResult; otherwise `"unspecified"`. |

The hardcoded `"unknown"` at `websocket_session_handler.py:4696` is **removed**,
not redirected. A test asserts `classified_intent != "unknown"` post-turn.

### What lives across turns

- `snapshot.next_turn_directives: list[str]` — consumed by prompt assembly
  at the start of the next turn, then cleared.
- Nothing else. Validator is stateless; reprompt is bounded to one
  iteration within a single turn.

## Error handling

### Pack-load failures

Schema validation at load. Raises loudly; server does not start with bad packs.

| Failure | Behavior |
|---|---|
| `intent_verbs:` not a list | `PackValidationError` with field path and offending value |
| `intent_verbs:` contains non-string elements | `PackValidationError` with index of bad element |
| `on_intent_mismatch:` invalid value | `PackValidationError` listing accepted values |
| Derived intent verb set empty after tokenization | Log warning, store empty frozenset. Validator never matches this type. Content debt, not runtime failure. |

### Validator runtime — input edge cases

Pure function; never raises. Each edge has a defined return:

| Input edge | Return |
|---|---|
| `action_rewrite` is `None` | `None` |
| `action_rewrite.intent` is empty / whitespace | `None` |
| `pack` is `None` or `pack.rules is None` | `None` — defensively |
| `active_encounter=True` | `None` — encounter already running |
| `declared_confrontation` unknown type | Treat as `None` for matching purposes |
| Intent tokens match the declared type | `None` |

### Reprompt loop failures

Bounded to one retry. Every failure mode terminates the loop and applies
SOME narration.

| Failure | Behavior |
|---|---|
| Second narrator call raises | Emit `confrontation.intent_mismatch_reprompt_failed`. Apply first attempt. |
| Second call produces invalid output | Same. |
| Second call still flags a mismatch | `already_reprompted=True` degrades severity to `warn`. Apply second attempt (newer wins). |
| Recursive reprompt (orchestrator bug) | Hard-asserted impossible. Assertion failure is a server bug worth surfacing immediately. |

### OTEL emission failures

Telemetry is observability, never load-bearing for game logic. Existing
span-context pattern handles emission errors; no new error handling needed.

### The `classified_intent` invariant

Single load-bearing rule: when a turn completes,
`TurnRecord.classified_intent` is a non-empty string and is never `"unknown"`.

### What we resist falling back to

- Narrator omits `action_rewrite` entirely → validator returns `None`. Do
  NOT scan prose to recover. Fix the prompt, not the validator.
- Confrontation def has empty derived intent verb set → validator never
  matches this type. Do NOT silently fall back to type-name string matching.
  Pack author sees content debt; system stays honest.

## Testing

### Validator unit tests

`tests/test_confrontation_intent_validator.py` — pure function coverage with
a small `Pack` mock.

- Tokenization correctness (case fold, stopword strip, suffix strip).
- Derivation from def (label + beats produces expected set).
- Extension via `intent_verbs:` unions correctly.
- Empty / `None` inputs all return `None`, no exceptions.
- Active encounter short-circuit.
- Declared matches inferred → `None`.
- Single mismatch → correct `matched_type`, severity from def, `matched_tokens`.
- Multi-type tie-break (overlap count, pack-order, deterministic).
- Severity propagation per `on_intent_mismatch` value.

### Dispatch integration tests

`tests/test_narration_apply_intent_dispatch.py` — branch logic with a
minimal `tests/fixtures/packs/intent_test_pack/`.

- Each severity branch (warn / soft_suggest / reprompt).
- `RepromptRequest` returned correctly on `reprompt`.
- `already_reprompted=True` degradation path.
- `classified_intent` invariant on every branch.

### Reprompt loop integration test

`tests/test_orchestrator_reprompt_loop.py` — orchestrator wrapper with
scripted narrator stub.

- First mismatch + second compliance.
- First mismatch + second still mismatched (fall-through).
- First mismatch + second raises (apply first).
- `already_reprompted` enforcement (no third call ever).

### Pack-load schema tests

`tests/test_pack_load_intent_schema.py`.

- All 7 production packs load successfully after migration.
- Malformed `intent_verbs:` raises.
- Invalid `on_intent_mismatch:` raises.
- Empty derived set loads with warning.
- Pack-load tokenization byte-for-byte matches validator-runtime tokenization.

### Wiring tests (load-bearing per CLAUDE.md)

- Validator import wiring — assert `confrontation_intent_validator.validate`
  is referenced in `narration_apply.py`; assert legacy symbols are GONE.
- Orchestrator wiring — assert the retry wrapper shape exists.
- OTEL wiring — end-to-end test hitting `process_action` with a mismatched
  stub; assert `confrontation.intent_mismatch` span lands in the in-memory
  exporter with all expected attributes.

### Replay regression test

`tests/test_dust_and_lead_horse_replay.py` — extract minimal `events` and
`game_state` from the 2026-05-20 dust_and_lead save; replay turns 5-10
against the new validator.

- Assert `confrontation.intent_mismatch` span fires with
  `matched_type=negotiation`.
- Assert `classified_intent` is `"negotiation"`, not `"unknown"`.
- Assert (with `warn` default) narration still applies.
- Assert (with the def changed to `reprompt`) the second-call span fires.

### Legacy deletion guards

- `test_legacy_trigger_patterns_removed.py` — greps `narration_apply.py`
  for legacy symbol names; fails if present.
- `test_classified_intent_no_unknown.py` — searches codebase for
  `classified_intent` assignments to the literal `"unknown"`; fails if found.

### Intentionally NOT tested

- LLM-grade correctness of the narrator's `intent` string (black-box quality
  concern, not a unit test).
- Per-pack intent vocabulary tuning (content authorship; quality lives in
  playtest loop + GM panel).
- NPC-initiation gap (acknowledged out-of-scope above).

## ADR amendment

This work delivers ADR-067's unfulfilled inference-and-extraction promise
and removes the lying `classified_intent = "unknown"` stub. ADR-067 itself
should be amended (or a short follow-up ADR filed) to record:

1. The inference site is `confrontation_intent_validator.validate(...)`.
2. The extracted action type is exposed via `TurnRecord.classified_intent`,
   populated from the validator's `matched_type` on mismatch and from
   `action_rewrite.intent` otherwise.
3. The legacy prose-regex lie-detector
   (`_CONFRONTATION_TRIGGER_PATTERNS`) is retired in the same change.

The amendment is part of the implementation work, not a precondition.

## Migration plan

The whole change ships in one PR per the one-mechanism doctrine:

1. New validator module + unit tests.
2. Pack-load extension + schema validator + unit tests.
3. `narration_apply.py` dispatch refactor + integration tests.
4. Orchestrator reprompt loop + integration tests.
5. `next_turn_directives` field + prompt-assembly consumption.
6. `classified_intent` invariant — remove `"unknown"` hardcoding.
7. Telemetry: new `confrontation.intent_mismatch[_resolved|_reprompt_failed]`
   spans; GM panel / dashboard update to surface them.
8. Pack-content authoring: add `on_intent_mismatch:` to every confrontation
   def across all 7 production packs (initial values per the table above).
9. Legacy deletion: `_CONFRONTATION_TRIGGER_PATTERNS`,
   `_scan_for_confrontation_trigger_keywords`,
   `confrontation_trigger_constraint` event.
10. Replay regression test against the dust_and_lead save fixture.
11. ADR-067 amendment.

Spans repos: `sidequest-server`, `sidequest-content`, and `sidequest-ui`
(GM panel surface for the new span names). Estimated 5-8 story points
across one sprint — to be confirmed during plan decomposition.

## Open questions for the implementation plan

These are implementation-detail decisions for plan/code, not design
choices that should hold up this spec:

- Exact path of the rules.yaml loader (under `sidequest-server/sidequest/genre/`).
- Whether `next_turn_directives` stays shared-world (the working assumption)
  or needs per-player scoping for any directive category that may emerge
  (ADR-037 / ADR-104 implications).
- Concrete stopword list and suffix-strip rules — pinned by test, not by
  this spec.
- The exact channel for passing the reprompt directive to the narrator
  (new `extra_directive` parameter vs. recency-zone injection vs. another
  mechanism). Doesn't affect the doctrinal shape.
- Whether the GM panel surfaces a new "Intent Mismatch" tab or reuses an
  existing OTEL view. UX detail.
