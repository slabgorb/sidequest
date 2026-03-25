# TRAIL Error Types → OCEAN Dimension Hypotheses

This document records a priori predictions about which OCEAN personality dimensions predict performance on different error types, based on the TRAIL benchmark's agentic error taxonomy.

## Background

### TRAIL Benchmark
The TRAIL (Tool Reasoning and Agentic Interaction Log) benchmark from Patronus AI evaluates agent debugging capabilities across 148 traces containing 841 errors. It categorizes errors into three types:

- **Reasoning errors**: Logic and decision-making failures
- **Planning errors**: Task orchestration and coordination failures
- **Execution errors**: System and tool interaction failures

### OCEAN Personality Model
The Big Five personality dimensions:
- **O** (Openness): Creativity, curiosity, preference for novelty
- **C** (Conscientiousness): Organization, dependability, self-discipline
- **E** (Extraversion): Sociability, assertiveness, positive emotions
- **A** (Agreeableness): Cooperation, trust, altruism
- **N** (Neuroticism): Emotional instability, anxiety, moodiness

### Research Question
**Which OCEAN dimensions predict which error-detection capabilities?**

---

## Hypothesis 1: Reasoning Errors

> Logic and decision-making failures including incorrect inferences, contradictions, false assumptions, and circular logic.

### Primary Predictor: Openness (O)

| Score | Prediction | Rationale |
|-------|------------|-----------|
| High-O (4-5) | **Better** at detecting reasoning errors | Creative pattern recognition enables novel error detection; willingness to consider unconventional explanations |
| Low-O (1-2) | **Worse** at detecting reasoning errors | Rigid thinking patterns; may miss errors that don't fit expected patterns |

**Testable Prediction H1a**: Agents with O ≥ 4 will detect 15%+ more reasoning errors than agents with O ≤ 2.

### Secondary Predictor: Conscientiousness (C)

| Score | Prediction | Rationale |
|-------|------------|-----------|
| High-C (4-5) | **Moderate boost** | Methodical analysis catches systematic logical errors |
| Low-C (1-2) | **Slight penalty** | May skip thorough logical verification |

**Testable Prediction H1b**: High-O + High-C agents will outperform High-O + Low-C agents by 5-10% on reasoning errors.

---

## Hypothesis 2: Planning Errors

> Task orchestration and coordination failures including sequencing errors, dependency gaps, resource misallocation, and incomplete plans.

### Primary Predictor: Conscientiousness (C)

| Score | Prediction | Rationale |
|-------|------------|-----------|
| High-C (4-5) | **Better** at detecting planning errors | Structured, organized approach naturally identifies gaps in plans and sequences |
| Low-C (1-2) | **Worse** at detecting planning errors | Misses sequencing issues and dependency problems due to less structured analysis |

**Testable Prediction H2a**: Agents with C ≥ 4 will detect 20%+ more planning errors than agents with C ≤ 2.

### Secondary Predictor: Extraversion (E)

| Score | Prediction | Rationale |
|-------|------------|-----------|
| High-E (4-5) | **Slight penalty** | Action-oriented approach may rush through planning phase analysis |
| Low-E (1-2) | **Slight boost** | More reflective, thorough examination of plans |

**Testable Prediction H2b**: High-C + Low-E agents will outperform High-C + High-E agents by 5-10% on planning errors.

---

## Hypothesis 3: Execution Errors

> System and tool interaction failures including timeouts, context overflow, tool misuse, and API errors.

### Primary Predictor: Neuroticism (N) [Inverse Relationship]

| Score | Prediction | Rationale |
|-------|------------|-----------|
| Low-N (1-2) | **Better** at detecting execution errors | Stable under pressure; maintains focus during long traces and complex tool interactions |
| High-N (4-5) | **Worse** at detecting execution errors | Performance degrades in extended contexts; anxiety may cause missed details |

**Testable Prediction H3a**: Agents with N ≤ 2 will detect 15%+ more execution errors than agents with N ≥ 4.

### Secondary Predictor: Conscientiousness (C)

| Score | Prediction | Rationale |
|-------|------------|-----------|
| High-C (4-5) | **Moderate boost** | Careful, methodical tool usage analysis; notices subtle API misuse |
| Low-C (1-2) | **Slight penalty** | May overlook execution details |

**Testable Prediction H3b**: Low-N + High-C agents will outperform Low-N + Low-C agents by 5-10% on execution errors.

---

## Summary: OCEAN × Error Type Matrix

| Error Type | Primary | Direction | Secondary | Direction |
|------------|---------|-----------|-----------|-----------|
| **Reasoning** | O (Openness) | High = Better | C (Conscientiousness) | High = Better |
| **Planning** | C (Conscientiousness) | High = Better | E (Extraversion) | Low = Better |
| **Execution** | N (Neuroticism) | Low = Better | C (Conscientiousness) | High = Better |

### Notable Patterns

1. **Conscientiousness (C)** appears as a predictor in all three categories, suggesting it may be the most broadly beneficial dimension for error detection.

2. **Neuroticism (N)** shows an inverse relationship for execution errors, unique among the predictions.

3. **Agreeableness (A)** is not predicted to be a significant factor in error detection, consistent with its social-interpersonal focus.

---

## Methodology

### Testing Approach

1. **Scenario Selection**: Use debugging scenarios tagged with `error_type` field (from Story 14-1 schema extension)

2. **Agent Sampling**: Run each scenario with agents across the OCEAN spectrum:
   - 10 runs per persona per scenario (statistical power)
   - Minimum 20 distinct OCEAN profiles per error type
   - Include extreme profiles (e.g., O=5/C=1 vs O=1/C=5)

3. **Scoring**: Use `/judge` in error-detection mode (Story 14-3) to calculate:
   - Per-type detection rates
   - False positive rates
   - Overall accuracy by OCEAN dimension

4. **Analysis**:
   - Pearson correlation between OCEAN scores and detection rates
   - Effect size (Cohen's d) for high vs low dimension groups
   - Regression analysis for combined predictors

### Success Criteria

| Metric | Threshold |
|--------|-----------|
| Statistical significance | p < 0.05 |
| Effect size | Cohen's d > 0.5 (medium effect) |
| Prediction accuracy | ≥ 2 of 6 predictions confirmed |

### Null Hypothesis Handling

If predictions are not confirmed:
- Document null results (valuable for ruling out hypotheses)
- Analyze confounding factors (scenario difficulty, agent implementation)
- Consider alternative dimension combinations

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-02 | Initial hypothesis document (Story 14-2) |

---

## References

- TRAIL Benchmark: Patronus AI (2025) - Agentic error taxonomy
- Big Five / OCEAN: Costa & McCrae (1992) - NEO Personality Inventory
- Pennyfarthing OCEAN Profiles: `pennyfarthing-dist/personas/themes/*.yaml` (630 profiles)
- Schema Extension: `scenarios/schema.yaml` - error_type field (Story 14-1)
