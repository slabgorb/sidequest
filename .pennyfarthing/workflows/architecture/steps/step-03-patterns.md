# Step 3: Pattern Selection

<step-meta>
step: 3
name: pattern-selection
workflow: architecture
agent: architect
gate: true
next: step-04-components
</step-meta>

<purpose>
Identify and evaluate architectural patterns that address identified concerns with verification of current technology versions, trade-off analysis, and selection of patterns that best fit the project requirements.
</purpose>

<prerequisites>
- Context analysis complete (step 2)
- Key concerns documented in `{output_file}`
- Constraints understood
</prerequisites>

<instructions>
Survey applicable patterns (microservices, event-driven, CQRS, circuit breakers, etc.) based on context concerns. Search web for current stable versions and best practices. Evaluate trade-offs (complexity, team familiarity, overhead, system fit). Select 1-3 primary patterns with rationale.

1. **Survey Applicable Patterns**:
   Based on the context analysis, identify patterns that address the key concerns:
   - For scalability: microservices, event-driven, CQRS
   - For reliability: circuit breakers, bulkheads, retries
   - For maintainability: clean architecture, hexagonal, modular monolith
   - For integration: API gateway, message broker, service mesh

2. **Verify Current Versions** (web search):
   For any frameworks or technologies being considered:
   - What is the current stable version?
   - What are the recommended starter templates?
   - Are there breaking changes in recent releases?

3. **Evaluate Trade-offs**:
   For each candidate pattern, consider:
   - Complexity cost vs. benefit
   - Team familiarity
   - Operational overhead
   - Fit with existing systems

4. **Select Primary Pattern(s)**:
   Choose 1-3 patterns that best address the requirements.
</instructions>

<actions>
- Read: `{output_file}` for context analysis from step 2
- Read: `docs/patterns/*.md` for pattern library (if exists)
- Search: Web for current framework versions and best practices
- Write: Pattern evaluation matrix to `{output_file}`
</actions>

<output format="markdown" target="{output_file}">
Add Pattern Analysis section to architecture document.

```markdown
## Pattern Analysis

### Technology Versions (as of {date})
| Technology | Current Version | Notes |
|------------|-----------------|-------|
| [Tech 1] | [version] | [stability, LTS status] |
| [Tech 2] | [version] | [stability, LTS status] |

### Candidate Patterns
| Pattern | Addresses | Trade-offs | Fit Score |
|---------|-----------|------------|-----------|
| [Pattern 1] | [concerns] | [pros/cons] | [1-5] |
| [Pattern 2] | [concerns] | [pros/cons] | [1-5] |
| [Pattern 3] | [concerns] | [pros/cons] | [1-5] |

### Selected Pattern(s)
1. **[Primary pattern]**: [Why this fits best]
2. **[Secondary pattern]** (if needed): [Why]

### Rejected Alternatives
- [Pattern]: [Why not suitable]
```
</output>

<gate>
## Completion Criteria
- [ ] At least 3 patterns evaluated against context constraints
- [ ] Current technology versions verified via web search
- [ ] Trade-offs clearly documented for each candidate
- [ ] Recommendation includes rationale tied to concerns
- [ ] User confirmed pattern selection
</gate>

<switch tool="AskUserQuestion">
  <case value="continue" next="step-04-components">
    Continue — Save the content and proceed to Component Design
  </case>
  <case value="revise" next="LOOP">
    Revise — Reconsider patterns or gather more information
  </case>
  <case value="advanced" next="LOOP">
    Advanced Elicitation — Explore unconventional or hybrid patterns
  </case>
  <case value="party" next="LOOP">
    Party Mode — Bring multiple perspectives to evaluate trade-offs
  </case>
</switch>

## Advanced Elicitation Mode

When user selects Advanced:
1. Explore hybrid patterns combining multiple approaches
2. Investigate emerging patterns not yet mainstream
3. Consider domain-specific architectural patterns
4. Question assumptions about pattern applicability

## Party Mode

When user selects Party:
1. Present pattern evaluation from multiple viewpoints:
   - **Pragmatist**: What's the simplest thing that works?
   - **Futurist**: What if requirements change significantly?
   - **Skeptic**: What could go wrong with this pattern?
   - **Operator**: How will this pattern affect day-to-day operations?
2. Synthesize perspectives into pattern recommendation

## Failure Modes

- Using outdated technology versions
- Not considering team familiarity
- Selecting overly complex patterns for simple problems
- Proceeding without user confirmation

## Success Metrics

- Patterns evaluated against context constraints
- Current technology versions verified via web search
- Trade-offs clearly documented
- User confirmed pattern selection before proceeding
