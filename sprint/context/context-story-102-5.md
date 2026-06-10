---
parent: context-epic-102.md
workflow: tdd
---

# Story 102-5: WN narrator tool contract

## Business Context

Retires deferred phase P5 — SWN module design §8 calls this "the hardest surface" and §12's risk note mandates it ship isolated behind tool-level tests + OTEL. Today the narrator participates in WN combat through generic narration surfaces; the module-specific moves (declare, strike, save, spend Effort) are reachable mechanically but the narrator's *typed* verbs for driving them are incomplete — which is why live play can drift into improv (the gap 102-1..3 measured). A complete per-module tool contract means the narrator drives WN resolution through typed tools whose every call emits a span: the structural end of "winging it" for WN scenes. This is the keystone story for making the AC5b proof *durable* rather than patched.

## Technical Guardrails

- **Spec authority:** SWN design §8 (the tool contract), §12 (risk note: tool-level tests + OTEL isolation), §3 (module owns the turn). Read §8 in full before designing — the tool list and call shapes are specified there, including how the contract amends the existing narration tool registry.
- **Build on ADR-102/103:** tool-use protocol for structured output and native OTEL via the tool registry. Every WN tool call gets span coverage *by construction* through the registry — don't hand-roll span emission per tool.
- **ADR-111:** guardrails live in tool descriptions (recency-zone migration) — the WN tools' contracts/descriptions carry the rules, not extra prompt zones.
- **One contract, four modules:** the tool surface is family-shaped with the module slug parameterizing resolution — avoid four parallel tool sets; the module seam (ADR-117) does the differentiation.
- **Coordinate with 102-4:** the `dead_premise` narrator call defined there is *part of* this contract — align call shapes; whichever story lands first stubs nothing (No Stubbing) but defines the shared type in its own scope.
- **Isolation per §12:** tool handlers must be testable without a live narrator (tool-level tests invoke handlers directly with typed payloads) AND have at least one wiring test through the real narrator tool-dispatch path.
- **Unified narrator (ADR-067):** this extends the single narrator's tool belt — no new agent, no multi-agent revival.
- Perception/MP: tool results that reveal per-player information must respect ADR-104/105 perception filtering at the tool layer.

## Scope Boundaries

**In scope:**
- The per-module narrator tool surface per §8 (registration, typed payloads, handlers routing into existing module resolution functions)
- OTEL span coverage per tool via the registry; tool-level tests + narrator-path wiring test
- Prompt-contract documentation updates for the narrator (tool descriptions per ADR-111)

**Out of scope:**
- New resolution mechanics — every tool routes to *existing* module surfaces (the spine from 102-1..3, the turn model from 102-4, psionics arrives in 102-6)
- Narrator backend changes (Anthropic SDK / claude -p selection)
- GM-panel feed consumption (90-8's lane)

## AC Context

1. **Contract completeness:** every WN move §8 enumerates has a registered tool with a typed payload; the narrator's WN-scene toolset matches the spec's list (test: registry enumeration assertion against the spec-derived list).
2. **Tools route to modules:** each tool handler calls the corresponding RulesetModule surface and emits its span; no handler contains resolution math of its own (review-level check + span assertions per tool).
3. **Isolation:** tool-level tests cover each handler with valid/invalid payloads (invalid → typed, loud errors — No Silent Fallbacks).
4. **Wiring:** at least one test drives a real narrator turn that invokes a WN tool through the production tool-dispatch path and asserts the span chain (narrator → tool → module → OTEL).
5. **Improvisation detection preserved:** when the narrator narrates a WN-mechanical event WITHOUT the corresponding tool call, existing lie-detector surfaces still flag it (regression: the contract adds verbs, it must not relax the watcher).

## Assumptions

- §8's tool list is implementable against the post-102-1..4 module surfaces without new mechanics (if a tool needs a missing surface, that's a scope flag to SM, not silent expansion).
- The tool registry's OTEL-by-construction (ADR-103) is live enough to lean on (it's marked *partial* in the ADR index — verify the registered-tool span path early; if the registry's span emission is the gap, fixing it for these tools is in-scope).
- Token-budget impact of added tool descriptions is acceptable within ADR-110/112's prompt-budget regime (measure in the story, don't guess).
