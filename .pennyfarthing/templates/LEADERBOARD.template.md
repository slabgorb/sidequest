# {SCENARIO_TITLE} - {ROLE_TITLE} Leaderboard

**Scenario:** `{scenario_name}` ({difficulty} difficulty)
**Role:** {role_title} (`{role}`)
**Baseline:** Control agent, mean {baseline_mean}, std_dev {baseline_std}, n={baseline_n}
**Pennyfarthing Version:** {version}
**Generated:** {generated_timestamp}

**Analysis:** [OCEAN Personality Correlation Analysis](./OCEAN-ANALYSIS.md)

---

## Cohen's d Interpretation

| Effect Size | Cohen's d |
|-------------|-----------|
| Negligible | |d| < 0.20 |
| Small | |d| = 0.20 |
| Medium | |d| = 0.50 |
| Large | |d| = 0.80 |
| Very Large | |d| > 1.20 |

---

## Rankings

| Rank | Theme | Character | Mean | Std Dev | n | Delta | Cohen's d |
|------|-------|-----------|------|---------|---|-------|-----------|
{RANKINGS_ROWS}

---

## Summary Statistics

- **Total Themes:** {total_themes}
- **Themes Beating Baseline:** {themes_above}
- **Themes At/Near Baseline (within 1 point):** {themes_near}
- **Total Benchmark Runs:** {total_runs}

## Top Performers (Above Baseline)

| Theme | Character | Mean | Delta | Cohen's d |
|-------|-----------|------|-------|-----------|
{TOP_PERFORMERS_ROWS}

## Bottom Performers

| Theme | Character | Mean | Delta | Cohen's d |
|-------|-----------|------|-------|-----------|
{BOTTOM_PERFORMERS_ROWS}

---

## Notes

- Cohen's d uses pooled standard deviation: `d = (M1 - M2) / sqrt(((n1-1)*s1² + (n2-1)*s2²) / (n1+n2-2))`
- Positive d indicates theme outperforms baseline; negative indicates underperformance
- Model and token usage tracked per-run in individual result files
- {scenario_description}
