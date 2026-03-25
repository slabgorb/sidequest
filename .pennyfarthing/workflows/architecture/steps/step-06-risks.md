# Step 6: Risk Assessment

<purpose>
Identify technical risks, failure modes, and mitigation strategies. Include risks specific to AI-assisted implementation such as ambiguous requirements or inconsistent interpretations that could cause implementation divergence.
</purpose>

<instructions>
Identify technical risks (bottlenecks, single points of failure, security, data consistency, operational complexity). Assess impact/likelihood for each. Define mitigations and monitoring/alerting strategies. Identify AI implementation risks where agents might misinterpret requirements or diverge on implementation.
</instructions>

<output>
Risk Assessment section with Technical Risks table, Failure Modes with recovery procedures, Security Considerations, AI Implementation Risks, and Operational Readiness plan. Update frontmatter stepsCompleted array after user confirms via the switch prompt.
</output>

<step-meta>
number: 6
name: risk-assessment
gate: true
</step-meta>

## Mandatory Execution Rules

- READ the complete step file before taking any action
- IDENTIFY risks specific to AI agent implementation
- ALWAYS treat this as collaborative discovery between architectural peers
- FOCUS on risks that could cause implementation divergence

## Execution Protocols

- Show your analysis before taking any action
- Present the switch prompt after generating risk assessment
- ONLY save when user confirms via the switch prompt
- Update frontmatter `stepsCompleted: [1, 2, 3, 4, 5, 6]` before loading next step
- FORBIDDEN to load next step until user confirms via the switch prompt

## Purpose

Identify technical risks, potential failure modes, and mitigation strategies. Include risks specific to AI-assisted implementation.

## Instructions

1. **Identify Technical Risks**:
   - Performance bottlenecks
   - Single points of failure
   - Security vulnerabilities
   - Data consistency challenges
   - Operational complexity

2. **Assess Impact and Likelihood**:
   - What happens if this risk materializes?
   - How likely is it?
   - What's the blast radius?

3. **Define Mitigations**:
   - How can each risk be reduced or eliminated?
   - What monitoring/alerting is needed?
   - What's the fallback plan?

4. **AI Implementation Risks** (BMAD pattern):
   - Where could AI agents misinterpret requirements?
   - What ambiguities could lead to incompatible implementations?
   - How do we detect implementation drift early?

## Actions

- Analyze: Each component for failure modes
- Review: Security considerations
- Plan: Monitoring and alerting strategy
- Identify: AI implementation risk points

## Output

Add to session file:

```markdown
## Risk Assessment

### Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| [Risk 1] | High/Med/Low | High/Med/Low | [Strategy] |
| [Risk 2] | High/Med/Low | High/Med/Low | [Strategy] |

### Failure Modes

| Component | Failure Mode | Detection | Recovery |
|-----------|--------------|-----------|----------|
| [A] | [How it fails] | [Monitoring] | [Steps] |
| [B] | [How it fails] | [Monitoring] | [Steps] |

### Security Considerations
- [Authentication approach]
- [Authorization model]
- [Data protection measures]

### AI Implementation Risks
> Risks specific to AI-assisted development

| Risk | Could Cause | Prevention |
|------|-------------|------------|
| Ambiguous requirement | Inconsistent implementation | [Clarification needed] |
| Missing constraint | Invalid assumptions | [Explicit documentation] |

### Operational Readiness
- Monitoring: [What to watch]
- Alerting: [Thresholds]
- Runbooks: [Key procedures needed]
```

<!-- GATE -->

## Success Metrics

- Technical risks identified with impact assessment
- Failure modes documented with recovery procedures
- Security considerations explicitly addressed
- AI implementation risks identified and mitigated
- User confirmed risks are acceptable before proceeding


<switch tool="AskUserQuestion">
  <case value="advanced-elicitation" next="LOOP">
    Advanced Elicitation — Use discovery protocols to explore hidden risks or unconsidered failure modes
  </case>
  <case value="party-mode" next="LOOP">
    Party Mode — Bring multiple perspectives to identify risks from different operational angles
  </case>
  <case value="continue" next="step-07-document">
    Continue — Save the content and proceed to documentation
  </case>
  <case value="revise" next="LOOP">
    Revise — Need to address unacceptable risks before proceeding
  </case>
</switch>

## Failure Modes

- Overlooking critical failure scenarios
- Underestimating risk impact or likelihood
- Missing security considerations
- Not addressing AI implementation risks
- Proceeding without user confirmation
