# Spec Authority Hierarchy

When agents (Dev, TEA, Reviewer, or any other role) encounter conflicting
guidance, they must resolve it using the 4-level authority hierarchy below.
Higher levels always override lower levels. Deviations from a higher-authority
spec require explicit escalation **before implementing**.

## Authority Levels

### 1. Story Scope (Highest Authority)

The acceptance criteria (ACs) in the session file are the highest authority.
They define exactly what must be built, tested, or delivered. No agent may
add, remove, or reinterpret ACs without escalation.

**Examples:**
- "API must return 404 for missing resources" — this is law.
- "Tests must cover edge case X" — TEA must write that test, not substitute a different edge case.

### 2. Story Context

Technical approach, design decisions, and implementation notes recorded in
the session file. These inform *how* to satisfy the ACs but do not override
them. When story context conflicts with story scope, story scope wins.

**Examples:**
- "Use repository pattern for data access" — follow this unless an AC contradicts it.
- "Prefer composition over inheritance for the handler chain" — a design preference, not a requirement.

### 3. Epic Context

Epic-level goals, constraints, and non-functional requirements. These provide
broader direction but yield to story-level specifics.

**Examples:**
- "All APIs in this epic must use OpenAPI 3.1" — applies unless a story AC overrides it.
- "Target 95% code coverage for the epic" — general goal, but a story AC saying "no coverage requirement for generated code" wins.

### 4. Architecture Docs / SOUL.md (Lowest Authority)

Project-wide architectural principles, ADRs, and SOUL.md guidelines. These
are the default baseline and apply when no higher-level spec addresses the
topic.

**Examples:**
- "All services must be stateless" — baseline, but a story AC requiring state is valid.
- "Use structured logging everywhere" — unless a story explicitly says otherwise.

## Deviation Escalation Procedure

When an agent believes a deviation from a higher-authority spec is necessary,
they **must** follow this procedure **before implementing** the change:

### Step 1: Identify the Conflict

Determine which authority levels are in conflict. Name the specific spec
items and why they conflict.

### Step 2: Log in Design Deviations

Add an entry to the **Design Deviations** section of the session file
**before coding or writing tests**. The entry must include:

- **What:** The proposed change
- **Why:** The technical justification
- **Authority conflict:** Which levels conflict (e.g., "Level 3 epic goal vs Level 1 story AC")
- **Risk:** What could go wrong if the deviation is wrong

### Step 3: Escalate if Crossing Authority Levels

If the proposed change operates at a **lower authority level** than the spec
it would override, the agent must escalate:

- **Within the same level:** No escalation needed. Log the deviation and proceed.
- **Lower overriding higher:** Stop. Log the design deviation. Flag it in the
  handoff assessment. Do **not** implement until the deviation is acknowledged
  in a subsequent phase or by the user.

### Step 4: Never Implement Silently

An agent must **never** override a higher-authority spec and only mention it
after the fact. The deviation log exists precisely to prevent this. If you
realize mid-implementation that you deviated without logging, stop, log it,
and note that it was discovered late.

## Common Anti-Patterns

| Anti-Pattern | Why It Fails | Correct Behavior |
|-------------|-------------|-----------------|
| TEA adds tests beyond AC scope | Scope creep from Level 4 overriding Level 1 | Log deviation, flag for review |
| Dev "improves" an AC during implementation | Level 2 context overriding Level 1 scope | Log deviation, do not implement |
| Reviewer demands changes not in ACs | Level 4 principles overriding Level 1 scope | Note as suggestion, not blocker |
| Agent assumes "obvious" improvements are in scope | No authority for the change | If not in ACs, it is out of scope |

## Integration with Workflow

This hierarchy applies at every workflow phase:

- **TEA (RED):** Tests must cover exactly what ACs specify. Additional test
  coverage beyond ACs requires a design deviation entry.
- **Dev (GREEN):** Implementation satisfies the ACs. Refactoring or
  architectural improvements beyond scope require deviation logging.
- **Reviewer:** Findings must distinguish between AC violations (blockers)
  and principle-level suggestions (non-blockers).

## Programmatic Access

The authority hierarchy is available programmatically via
`pf.spec.authority`:

```python
from pf.spec.authority import get_authority_levels, check_deviation_required

# Get all 4 levels in precedence order
levels = get_authority_levels()
# [{"level": 1, "name": "Story scope", ...}, ...]

# Check if a proposed change requires deviation logging
needs_deviation = check_deviation_required(
    proposed_change_level=3,  # Epic context
    current_spec_level=1,     # Story scope
)
# True — lower authority overriding higher requires deviation
```
