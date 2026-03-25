# Step 5: Codify as Formal Scenario

<step-meta>
step: 5
workflow: scenario-discovery
agent: orchestrator
name: codify
gate: true
next: step-06-validate
</step-meta>

<purpose>
Transform the analysis from step 4 into a formal benchmark scenario YAML file following
the schema v2 format. This is where party mode observations become a reproducible,
measurable benchmark.
</purpose>

<prerequisites>
- Analysis complete with behavioral anchors (step 4)
- Persona scores and influence patterns documented
- Difficulty estimated
- Ground truth finalized (including novel findings from party mode)
</prerequisites>

<instructions>
1. **Determine category and ID**
   - Scan `{benchmarks_root}/` for existing scenarios
   - Auto-derive next ID (e.g., if `cr-001` and `cr-002` exist, use `cr-003`)
   - Choose a descriptive slug (e.g., `cr-003-serde-deserialization-bypass`)

2. **Build the scenario YAML**
   Use the appropriate template based on family:
   - Detection: issue catalog with severity weights
   - Divergent: weighted criteria with persona influence mapping

3. **Populate content_source** (required by ADR-0034)
   ```yaml
   content_source:
     type: lang-review | production-bug | orc-ax-finding | swe-bench | owasp-cwe | project-history
     reference: "specific gate check, PR URL, CWE ID, etc."
     provenance: "how this finding was discovered"
   ```

4. **Populate BARS rubric** from the behavioral anchors extracted in step 4
   - Use verbatim quotes from party mode responses where possible
   - Each dimension needs anchors at expert/adequate/poor levels

5. **Populate persona influence section** (both families)
   - Detection: which OCEAN traits affect detection rates
   - Divergent: which traits affect decision-making approach

6. **Populate expected tendencies** from step 4 archetype mapping
   - Map to at least 3 specific character archetypes from known themes

7. **Add difficulty_profile stub**
   ```yaml
   difficulty_profile:
     declared: {estimate from step 4}
     calibration: null  # populated later by control baseline runs
   ```

8. **Write the scenario file** to `{benchmarks_root}/{category}/{id}-{slug}.yaml`
</instructions>

<actions>
- Read: `{benchmarks_root}/{category}/` for existing scenarios and ID derivation
- Read: Analysis document from step 4
- Read: `pennyfarthing/benchmarks/test-cases/pm/pm-002-prioritization-crisis.yaml` as gold standard reference for divergent scenarios
- Read: `pennyfarthing/benchmarks/test-cases/dev/dev-002-tdd-shopping-cart.yaml` as gold standard reference for detection scenarios
- Write: `{benchmarks_root}/{category}/{id}-{slug}.yaml`
</actions>

## Detection Scenario Template

```yaml
# {id}: {title}
# Source: {content_source.type} -- {content_source.reference}
# Family: detection
# Discovered via: scenario-discovery workflow (party mode)

version: "2.0"
family: detection
category: {category}
id: {id}
title: "{descriptive title}"
description: "{what this scenario tests}"
difficulty: {easy|medium|hard|extreme}
agent_target: {dev|reviewer|tea}

content_source:
  type: {source type from step 1}
  reference: "{specific reference}"
  provenance: "{discovery context}"

instructions: |
  Review the following code. Identify all issues, prioritize by severity,
  and recommend fixes.

code:
  language: {language}
  context: "{what the code does, project context}"
  content: |
    {the code snippet from step 2}

known_issues:
  critical:
    - id: {SCREAMING_SNAKE_ID}
      location: "{line or function}"
      description: "{what's wrong}"
  high: []
  medium: []
  low: []

red_herrings:
  - type: {style|performance|pattern}
    description: "{what looks wrong but isn't}"
    severity: {low|medium}

scoring:
  total_issues: {count}
  weights:
    critical: 3
    high: 2
    medium: 1
    low: 0.5
  max_score: {calculated}

rubric:
  correctness:
    weight: 25
    expert: "{verbatim anchor from party mode}"
    adequate: "{anchor}"
    poor: "{anchor}"
  depth:
    weight: 25
    expert: "{anchor}"
    adequate: "{anchor}"
    poor: "{anchor}"
  quality:
    weight: 25
    expert: "{anchor}"
    adequate: "{anchor}"
    poor: "{anchor}"
  persona:
    weight: 25
    expert: "{anchor}"
    adequate: "{anchor}"
    poor: "{anchor}"

persona_influence:
  dimensions:
    - name: risk_tolerance
      high: "{observed effect}"
      low: "{observed effect}"
    - name: conscientiousness
      high: "{observed effect}"
      low: "{observed effect}"

expected_tendencies:
  - archetype: cautious_analytical
    traits: [high_conscientiousness, low_openness]
    expected: "{what this type typically does}"
  - archetype: creative_adventurous
    traits: [high_openness, low_conscientiousness]
    expected: "{what this type typically does}"

difficulty_profile:
  declared: {difficulty}
  calibration: null
```

## Divergent Scenario Template

```yaml
# {id}: {title}
# Source: {content_source.type} -- {content_source.reference}
# Family: divergent
# Discovered via: scenario-discovery workflow (party mode)

version: "2.0"
family: divergent
category: {category}
id: {id}
title: "{descriptive title}"
description: "{what this scenario tests}"
difficulty: {easy|medium|hard|extreme}
agent_target: {architect|pm|sm}

content_source:
  type: {source type from step 1}
  reference: "{specific reference}"
  provenance: "{discovery context}"

instructions: |
  Given the following situation, provide your recommendation with detailed rationale.
  Consider trade-offs, risks, and stakeholder concerns.

situation: |
  {the situation brief from step 2}

rubric:
  categories:
    - name: situation_analysis
      weight: 15
      description: "Understanding of constraints and stakeholder needs"
    - name: recommendation_quality
      weight: 30
      description: "Soundness of recommended approach"
    - name: trade_off_analysis
      weight: 25
      description: "Depth of trade-off consideration"
    - name: communication
      weight: 20
      description: "Clarity and persuasiveness of presentation"
    - name: persona_expression
      weight: 10
      description: "How personality traits influence the recommendation"

  bars_anchors:
    correctness:
      weight: 25
      expert: "{anchor}"
      adequate: "{anchor}"
      poor: "{anchor}"
    depth:
      weight: 25
      expert: "{anchor}"
      adequate: "{anchor}"
      poor: "{anchor}"
    quality:
      weight: 25
      expert: "{anchor}"
      adequate: "{anchor}"
      poor: "{anchor}"
    persona:
      weight: 25
      expert: "{anchor}"
      adequate: "{anchor}"
      poor: "{anchor}"

persona_influence:
  dimensions:
    - name: risk_tolerance
      conservative: "{observed pattern}"
      moderate: "{observed pattern}"
      aggressive: "{observed pattern}"
    - name: stakeholder_approach
      diplomatic: "{observed pattern}"
      direct: "{observed pattern}"

expected_tendencies:
  - archetype: "{character archetype}"
    motivation: "{what drives this character}"
    traits: [trait1, trait2]
    expected: "{how they typically approach this kind of decision}"

difficulty_profile:
  declared: {difficulty}
  calibration: null
```

<output>
Complete scenario YAML file written to `{benchmarks_root}/{category}/{id}-{slug}.yaml`
with all required fields populated from party mode observations.
</output>

<gate>
## Completion Criteria
- [ ] Scenario ID derived from existing files (no collisions)
- [ ] content_source populated with real-world reference
- [ ] Code/situation content included
- [ ] BARS anchors populated from party mode observations (not generic)
- [ ] Persona influence dimensions documented
- [ ] Expected tendencies mapped to at least 3 archetypes
- [ ] Scoring math verified (detection only)
- [ ] difficulty_profile stub included
- [ ] User reviewed the complete YAML
</gate>

<next-step>
After scenario is codified, proceed to step-06-validate.md for schema validation and
optional baseline run.
</next-step>

## Failure Modes

- Generic BARS anchors not grounded in observed party mode behavior
- Missing content_source (ADR-0034 requires provenance)
- Scoring math errors (detection: counts times weights must equal max_score)
- Expected tendencies based on stereotypes instead of observations
