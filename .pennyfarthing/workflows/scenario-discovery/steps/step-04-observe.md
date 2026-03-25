# Step 4: Analyze Observations and Extract Behavioral Anchors

<step-meta>
step: 4
workflow: scenario-discovery
agent: orchestrator
name: observe
gate: true
next: step-05-codify
</step-meta>

<purpose>
Compare party mode observations against ground truth to extract behavioral anchors --
concrete examples of what good, adequate, and poor responses look like for each persona
type. These anchors become the BARS rubric for the formal scenario.

Scientific basis:
- BARS methodology: anchors from observed critical incidents, not hypothetical behavior
- PersonaGym: exemplar responses at each score band, tailored to persona+question
- MBTI-in-Thoughts: personality trait persistence verification
</purpose>

<prerequisites>
- Party mode session completed (step 3)
- Observation notes recorded
- Ground truth from step 1
</prerequisites>

<instructions>
1. **Compare against ground truth**
   - Which personas found the key finding? Which missed it?
   - Were any novel findings legitimate (expand ground truth)?
   - Were any red herrings flagged as real issues (false positives)?

2. **Score each persona's response** using the 4 BARS dimensions:
   - **Correctness** (1-10): Did they identify the right issues / make sound recommendations?
   - **Depth** (1-10): Did they explain WHY, not just WHAT?
   - **Quality** (1-10): Was the response clear, organized, actionable?
   - **Persona** (1-10): Did personality traits visibly influence the analysis?

3. **Extract behavioral anchors** at 3 levels for each dimension:
   - **Expert (9-10):** What the best response looked like (verbatim from party mode if possible)
   - **Adequate (5-6):** What a passing response looked like
   - **Poor (1-2):** What a failing response looked like (or construct from observed misses)

4. **Document persona influence patterns**

   For detection scenarios:
   ```yaml
   persona_influence:
     - dimension: risk_tolerance
       high_trait: "flagged ALL critical issues, may over-report medium/low"
       low_trait: "focused only on obvious issues, missed subtle bugs"
     - dimension: conscientiousness
       high_trait: "systematic scan, checked every function"
       low_trait: "quick glance, caught only surface-level issues"
   ```

   For divergent scenarios:
   ```yaml
   persona_influence:
     - dimension: risk_tolerance
       conservative: "recommended proven technology, minimal change"
       aggressive: "proposed novel architecture, accepted more unknowns"
     - dimension: communication_style
       direct: "stated recommendation immediately with rationale"
       diplomatic: "explored all options before gently suggesting preference"
   ```

5. **Determine expected tendencies per persona archetype**
   Based on observed behavior, document what you'd expect from common character types:
   - The cautious/analytical character (high C, low O)
   - The creative/adventurous character (high O, low C)
   - The team-focused/diplomatic character (high A, high E)
   - The skeptical/thorough character (low A, high C)

6. **Assess scenario difficulty**
   Based on party mode performance:
   - If most personas caught the finding -> easy or medium
   - If only 1-2 caught it -> hard
   - If none caught it -> extreme (or stimulus needs rework)
</instructions>

<actions>
- Read: Party mode transcript and observation notes (step 3)
- Read: `pennyfarthing-dist/guides/rubric-anchors.md` for BARS reference
- Read: `pennyfarthing-dist/personas/TRAIL-OCEAN-MAPPING.md` for trait-error hypotheses
</actions>

<output>
Analysis document containing:

```yaml
analysis:
  ground_truth_validated: true
  novel_findings_added: []     # any legitimate findings not in original ground truth

  persona_scores:
    - persona: "{character name}"
      role: dev
      correctness: 8
      depth: 7
      quality: 8
      persona: 9
      weighted_total: 80
      notable: "caught the deserialization bypass immediately, framed as security risk"
    - persona: "{character name}"
      role: reviewer
      correctness: 6
      depth: 5
      quality: 7
      persona: 7
      weighted_total: 62.5
      notable: "found it but rated medium priority, missed security implications"

  behavioral_anchors:
    correctness:
      expert: "verbatim or paraphrased example from best party mode response"
      adequate: "example of passing but not exceptional response"
      poor: "example of response that missed the key finding"
    depth:
      expert: "..."
      adequate: "..."
      poor: "..."
    quality:
      expert: "..."
      adequate: "..."
      poor: "..."
    persona:
      expert: "..."
      adequate: "..."
      poor: "..."

  persona_influence:
    - dimension: "trait that affected results"
      observed_effect: "how it manifested"

  expected_tendencies:
    cautious_analytical: "expected behavior pattern"
    creative_adventurous: "expected behavior pattern"
    team_focused_diplomatic: "expected behavior pattern"
    skeptical_thorough: "expected behavior pattern"

  difficulty_estimate: easy | medium | hard | extreme
  difficulty_rationale: "why this difficulty based on party mode performance"
```
</output>

<gate>
## Completion Criteria
- [ ] All persona responses compared against ground truth
- [ ] Each persona scored on 4 BARS dimensions
- [ ] Behavioral anchors extracted at 3 levels (expert/adequate/poor)
- [ ] Persona influence patterns documented
- [ ] Expected tendencies mapped to archetypes
- [ ] Difficulty estimated from observed performance
- [ ] User reviewed and approved analysis
</gate>

<next-step>
After analysis is complete, proceed to step-05-codify.md to build the formal scenario YAML.
</next-step>

## Failure Modes

- Anchoring behavioral exemplars to imagined behavior instead of observed behavior
- Inflating scores (central tendency bias -- use the full 1-10 range)
- Ignoring novel findings that emerged during party mode
- Not updating ground truth when legitimate new findings surface
