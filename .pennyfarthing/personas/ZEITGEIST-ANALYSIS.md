# Zeitgeist Score: Measuring Persona Articulation Depth

## Purpose

The `zeitgeist_score` is a **measurement dimension** for correlating persona articulation depth with agent benchmark performance. It is NOT a quality judgment or "coolness" rating.

**Research Question:** Does deeper personality articulation affect agent task performance?

**Framework Alignment** (per Wallach et al. 2025):
- Level 1 (Background Concept): "Persona depth" - how well-defined is the character?
- Level 2 (Systematized Concept): Articulation depth across behavioral dimensions
- Level 3 (Operationalization): Rubric-based assessment of theme YAML structure
- Level 4 (Scores): exceptional/rich/moderate/thin/minimal

## Construct Definition

**Zeitgeist measures:** How much personality signal exists in the theme configuration for Claude to express.

**Zeitgeist does NOT measure:**
- Source material quality or popularity
- User preference or entertainment value
- OCEAN profile suitability for roles (separate dimension)
- Benchmark performance (that's the dependent variable)

## Hypothesis

Themes with higher zeitgeist_score provide:
1. More distinctive behavioral anchors for Claude to embody
2. Stronger speech pattern signals for consistent voice
3. Better character differentiation across agents
4. More authentic catchphrases grounding responses

**Expected correlation:** Zeitgeist may interact with OCEAN profiles to affect performance. A high-C (Conscientiousness) character with deep articulation may outperform a high-C character with thin articulation on the same role.

## Assessment Rubric

### Dimensions Measured

| Dimension | Weight | Assessment Criteria |
|-----------|--------|---------------------|
| **Behavioral Specificity** | 25% | Are quirks specific behaviors (e.g., "speaks IN CAPITALS") or generic adjectives (e.g., "methodical")? |
| **Speech Pattern Signal** | 25% | Does the theme encode identifiable speech patterns (accent, vocabulary, cadence)? |
| **Catchphrase Authenticity** | 20% | Are catchphrases actual character quotes or generic role-appropriate phrases? |
| **Helper Characterization** | 15% | Are helpers named characters with personality, or abstract concepts? |
| **Agent Distinctiveness** | 15% | Can agents be distinguished by voice alone, or are they interchangeable? |

### Score Definitions

| Score | Behavioral | Speech | Catchphrases | Helpers | Distinctiveness |
|-------|------------|--------|--------------|---------|-----------------|
| **exceptional** | 5+ specific behaviors per agent | Encoded speech patterns (accent, caps, lisp) | Actual quotes from source | All named characters | Highly distinctive voices |
| **rich** | 4-5 specific behaviors | Some speech patterns | Mostly authentic quotes | Most are characters | Clearly distinguishable |
| **moderate** | 3-4 behaviors, some generic | Minimal patterns | Mix of authentic/generic | Some concepts | Partially distinguishable |
| **thin** | 1-2 behaviors, mostly generic | No patterns | Generic phrases | Mostly concepts | Hard to distinguish |
| **minimal** | Generic only | None | Generic only | Abstract concepts | Interchangeable |

## Measurement Procedure

### Step 1: Count Structural Elements

```bash
# Per theme, count:
quirks_count=$(grep -c "quirks:" theme.yaml)
catchphrases_count=$(grep -c "catchphrases:" theme.yaml)
```

Expected for full articulation: 10 quirks sections, 10 catchphrases sections

### Step 2: Assess Behavioral Specificity

Sample 3 agents, score each quirk:
- **Specific** (2 pts): "Speaks IN CAPITALS always"
- **Semi-specific** (1 pt): "Meticulous about testing"
- **Generic** (0 pts): "Methodical"

Score = (total points) / (total quirks × 2) × 100

### Step 3: Assess Speech Pattern Encoding

Check for explicit speech markers:
- Accent notation ("Scottish accent in writing")
- Case rules ("CAPITALS", "lowercase")
- Verbal tics ("Yeth, marthter" - lisp)
- Vocabulary constraints ("Belter Creole")

Score: 0 (none) to 4 (strong encoding)

### Step 4: Assess Catchphrase Authenticity

Sample 5 catchphrases per theme:
- **Authentic** (2 pts): Actual quote from source
- **In-character** (1 pt): Sounds like character but not a quote
- **Generic** (0 pts): Could be anyone

Score = (total points) / 10 × 100

### Step 5: Assess Helper Characterization

Count helpers that are:
- Named characters with personality: 2 pts
- Named characters, minimal personality: 1 pt
- Abstract concepts ("The Algorithm"): 0 pts

Score = (total points) / 20 × 100

### Step 6: Calculate Composite Score

```
composite = (behavioral × 0.25) + (speech × 0.25) +
            (catchphrase × 0.20) + (helper × 0.15) +
            (distinctiveness × 0.15)
```

Map to categorical (recalibrated for better spread):
- 90-100: exceptional (speech patterns, authentic quotes, named helpers)
- 70-89: rich (mostly authentic, good distinctiveness)
- 50-69: moderate (functional but some generic elements)
- 30-49: thin (concept helpers, object agents, adaptations)
- 0-29: minimal (baseline or incoherent source)

## Correlation Analysis Plan

### With OCEAN Profiles

Test whether zeitgeist interacts with OCEAN:
- Do high-zeitgeist + high-C themes outperform low-zeitgeist + high-C on TEA?
- Does zeitgeist affect SM performance differently than Reviewer?

### With Benchmark Scores

Correlate zeitgeist_score with:
- Best role delta (from job fair)
- Role-specific performance variance
- Inter-run consistency

### Confounds to Control

- **OCEAN profile**: Control for personality type when comparing zeitgeist
- **Theme age**: Older themes may have less structure (artifact, not signal)
- **Source type**: Historical vs fictional may differ systematically

## Current Distribution (Pre-Audit)

| Score | Count | % | Notes |
|-------|-------|---|-------|
| exceptional | 11 | 10.8% | Prestige TV, literary depth |
| rich | 50 | 49.0% | Well-characterized themes |
| moderate | 37 | 36.3% | Functional but generic elements |
| thin | 2 | 2.0% | Limited source characterization |
| minimal | 2 | 2.0% | Baseline/experimental |

## Baseline Themes

For controlled experiments:

| Theme | Zeitgeist | OCEAN | Use Case |
|-------|-----------|-------|----------|
| control | minimal | M-M-M-M-M | Zero-persona baseline |
| discworld | exceptional | varies | Maximum articulation reference |
| mash | rich | M-M-M-M-M (B.J.) | High zeitgeist + neutral OCEAN |

## References

- Wallach et al. (2025) "Position: Evaluating Generative AI Systems Is a Social Science Measurement Challenge" ICML 2025
- OCEAN-BENCHMARK-CORRELATION.md - Personality vs performance data
- future.yaml - Benchmark reliability initiative (epics 41-46)

---

*This is a measurement instrument, not a quality rating. Low zeitgeist is not "bad" - it's a data point for understanding persona effects on agent behavior.*
