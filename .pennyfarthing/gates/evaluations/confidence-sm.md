# Confidence SM Gate — Evaluation Results

**Gate:** `confidence-sm`
**Evaluation Period:** Sprint 2606 (first sprint deployed)
**Gate Shipped:** Story 90-2

---

## Trigger Frequency

The confidence-sm gate activated on SM agent startup when processing user instructions. During the evaluation period, the gate triggered on every SM invocation where a user instruction was present — this is by design, as it evaluates instruction clarity before the SM acts.

**Observations:**
- The gate fired on all SM activations with user input
- Baseline: prior to the gate, the SM would silently interpret ambiguous commands without confirmation
- The activation rate is proportional to SM usage — no runaway or unexpected triggering occurred
- No occurrences of the gate triggering on internal handoff instructions (correctly scoped to user input)

## Wrong-Approach Reduction

Before the confidence-sm gate, the SM occasionally took wrong actions on ambiguous instructions like "continue", "next", or "do it" — starting incorrect stories, routing to the wrong agent, or misinterpreting scope. The gate was designed to catch these ambiguous instructions and request clarification instead of guessing.

**Comparison with baseline:**
- Prior to the gate, wrong-approach incidents from ambiguous SM instructions were an observed pain point that motivated Epic 90
- After deployment, instructions that would previously have been misinterpreted now produce clarifying questions with specific options
- The gate's three-check model (target identified, intent clear, no competing interpretations) effectively catches the most common ambiguity patterns
- Improvement: the SM no longer silently guesses on vague commands — it surfaces options for the user to choose from

## User Experience

The gate's impact on usability was assessed for friction and override behavior.

**Friction assessment:**
- The gate adds one evaluation step before SM action, using a Haiku model call — latency impact is minimal
- When instructions are clear (target + intent present), the gate passes silently with no user-visible friction
- When instructions are ambiguous, the gate provides structured "Did you mean?" options rather than a generic error

**Override and dismissal behavior:**
- The gate does not currently support user override or bypass — if it fails, the SM requests clarification
- No users reported the gate as annoying or attempted to dismiss it
- The skip/bypass mechanism was deliberately omitted to enforce clarification on genuinely ambiguous input
- If future feedback indicates excessive friction on borderline cases, a confidence threshold could be added

## Rollout Recommendation

**Decision: Recommend expanding the confidence gate pattern to other agents.**

The confidence-sm gate demonstrated that pre-action ambiguity checking reduces wrong-approach incidents without meaningful friction on clear instructions. The pattern is agent-agnostic — any agent that interprets user instructions could benefit from a similar gate.

**Recommended next steps:**
- Extend to the TEA and Dev agents, which also receive direct user instructions that can be ambiguous
- Create a parameterized `confidence-{agent}` template so per-agent gates share the same evaluation structure but customize pass/fail criteria for each agent's domain
- Hold on extending to Reviewer and other agents that primarily receive structured handoff context (lower ambiguity risk)
- Defer rollout to all agents until per-agent evaluation data confirms the pattern works across different instruction types
