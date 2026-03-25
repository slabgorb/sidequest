# ADR-008: Three-Tier Rule Taxonomy

> Ported from sq-2. Language-agnostic prompt engineering pattern.

## Status
Accepted

## Context
Agent rules need priority levels. Some rules are absolute ("never control the player"), some are firm guidelines, and some are aesthetic preferences.

## Decision
Rules are organized into three tiers with different binding strengths:

| Tier | Binding | Examples |
|------|---------|----------|
| **Critical** | Non-negotiable | Agency, output format, safety |
| **Firm** | Agent-specific guidelines | Living world, forward momentum, tone |
| **Coherence** | Aesthetic preferences | Brevity, vocabulary, style |

### Genre Pack Overrides
Genre packs can override rules by name without code changes. Override strategy:
- **Critical:** Can only be made stricter, never relaxed
- **Firm:** Can be replaced entirely per genre
- **Coherence:** Can be replaced or removed

### Verification
A `<before-you-respond>` block in the LATE zone lists all Critical rules as a verification checklist the agent must mentally check before responding.

```rust
#[derive(Debug, Clone, Deserialize)]
pub struct RuleDefinition {
    pub name: String,
    pub text: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct RuleTiers {
    pub critical: Vec<RuleDefinition>,
    pub firm: Vec<RuleDefinition>,
    pub coherence: Vec<RuleDefinition>,
}
```

## Consequences
- Agents always honor Critical rules even when context is complex
- Genre packs can customize tone without touching code
- `before-you-respond` block adds ~50 tokens but catches most violations
