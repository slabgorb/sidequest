# Step 4: Considerations & Rubric

<step-meta>
number: 4
name: scoring
gate: true
next: step-05-review
</step-meta>

<purpose>
Define the known considerations, scoring rubric with weighted categories, persona influence areas, and expected tendencies. This is the evaluation framework that makes open-ended scenarios benchmarkable.
</purpose>

<prerequisites>
- Scenario narrative authored (step 3)
- Category is open-ended (architecture, pm, sm)
</prerequisites>

<instructions>
1. Define `known_considerations` organized by domain-specific categories
2. Build `scoring_rubric` with weighted categories (weights must sum to 100)
3. Define `persona_influence_areas` with spectrums
4. Write `expected_tendencies` for 3-5 reference personas
5. Verify all weights sum correctly
</instructions>

## 1. Known Considerations

Organize by category-specific domains. Each consideration gets an ID and description.

### Architecture domains:
```yaml
known_considerations:
  architecture_patterns:
    - id: EVENT_DRIVEN
      description: "Event-driven architecture for scalability"
  components:
    - id: API_GATEWAY
      description: "API layer for receiving requests"
  data_models:
    - id: NOTIFICATION_ENTITY
      description: "Core record with status tracking"
  scalability:
    - id: HORIZONTAL_SCALING
      description: "Workers scale horizontally"
  reliability:
    - id: IDEMPOTENCY
      description: "Idempotent operations"
  trade_offs:
    - id: PUSH_VS_PULL
      description: "Push vs pull for workers"
  security:
    - id: PII_HANDLING
      description: "Personal data handling"
```

### PM domains:
- `situation_assessment`, `prioritization_quality`, `rejection_handling`, `communication_plan`, `adaptability`

### SM domains:
- `breakdown_quality`, `estimation_accuracy`, `dependency_mapping`, `risk_identification`, `sprint_planning`

## 2. Scoring Rubric

Each category has a weight (sum to 100) and criteria with point values:

```yaml
scoring_rubric:
  situation_assessment:
    weight: 15
    criteria:
      - id: DYNAMICS_UNDERSTANDING
        description: "Correctly reads stakeholder relationships"
        points: 5
      - id: RISK_IDENTIFICATION
        description: "Understands what's really at stake"
        points: 5
```

**Weight distribution guidance:**
- Core competency categories: 25-30 weight
- Supporting categories: 15-20 weight
- Persona expression: 5-10 weight
- Total must equal 100

## 3. Persona Influence Areas

Define spectrums where personas should legitimately differ:

```yaml
persona_influence_areas:
  revenue_vs_foundation:
    description: "How do they weigh revenue against technical health?"
    spectrum:
      revenue_first: "Revenue solves all problems"
      balanced: "Mix of revenue and foundation"
      foundation_first: "Fix foundation, revenue follows"
  certainty_vs_upside:
    description: "How do they weigh sure things against big bets?"
    spectrum:
      certainty: "Prefer proven, predictable outcomes"
      balanced: "Some risk tolerance"
      upside: "Willing to bet on transformative features"
```

Include 2-4 influence areas that map to the scenario's key trade-offs.

## 4. Expected Tendencies

Map 3-5 reference personas to expected behaviors:

```yaml
expected_tendencies:
  discworld_vetinari:
    character: "Lord Havelock Vetinari"
    expected_traits:
      - "Makes stakeholders think decision was their idea"
      - "Sees several moves ahead"
    likely_priority: "SSO + Perf + API (control, inevitability)"
    stakeholder_style: "Manipulation through understanding"
```

Choose personas from different themes to show differentiation:
- At least one cautious/conservative persona
- At least one bold/risk-taking persona
- At least one data-driven/analytical persona
- The minimalist (no-persona baseline)

<output>
Complete evaluation framework:
- `known_considerations` organized by domain categories
- `scoring_rubric` with weighted categories summing to 100
- `persona_influence_areas` with 2-4 spectrums
- `expected_tendencies` for 3-5 reference personas
</output>

<gate>
## Completion Criteria
- [ ] Known considerations organized by domain (at least 3 domains)
- [ ] Each consideration has unique ID and description
- [ ] Scoring rubric weights sum to exactly 100
- [ ] Each rubric category has criteria with point values
- [ ] At least 2 persona influence areas defined with spectrums
- [ ] At least 3 expected tendencies mapped to reference personas
- [ ] Tendencies show meaningful differentiation between personas
</gate>

<next-step>
After scoring framework is complete, proceed to step-05-review.md for assembly and review.
</next-step>

## Failure Modes

- Rubric weights not summing to 100
- Considerations too generic (should be specific to the scenario)
- Persona tendencies all predicting the same outcome (defeats purpose)
- Missing the minimalist/baseline persona
- Influence area spectrums that don't meaningfully differentiate
