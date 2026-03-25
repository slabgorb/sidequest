# Step 8: Health Summary

<step-meta>
step: 8
name: summary
workflow: installation-check
agent: devops
gate: false
next: complete
</step-meta>

<purpose>
Aggregate results from all previous steps into a final health report with an overall score and prioritized recommendations.
</purpose>

<prerequisites>
- All previous steps (1-7) completed
</prerequisites>

<instructions>
1. Run the full doctor command to get a complete picture
2. Aggregate results into a health score:
   - **HEALTHY**: All checks pass (0 failures, 0 warnings)
   - **GOOD**: No failures, some warnings (non-critical issues)
   - **NEEDS_ATTENTION**: 1-3 failures (some features broken)
   - **NEEDS_FIX**: 4+ failures (significant functionality impaired)
3. Group remaining issues by priority:
   - **Critical**: Failures that break core functionality (missing settings.local.json, broken symlinks, missing manifest)
   - **Important**: Warnings that degrade features (missing hooks, stale commands, non-executable scripts)
   - **Optional**: Informational items (legacy artifacts, missing optional tools)
4. For each remaining issue, provide the specific fix command
5. Write the summary to the output file if configured
6. Suggest next steps based on the health score
</instructions>

<actions>
- Run: `pf validate --json`
- Write: `{output_file}` with full health report
</actions>

<output>
Present the final report:

```markdown
# Pennyfarthing Health Report

**Project:** {project_root}
**Version:** {installed_version} / {package_version}
**Mode:** {installation_type}
**Health:** {HEALTHY | GOOD | NEEDS_ATTENTION | NEEDS_FIX}
**Score:** {pass_count}/{total_count} checks passing

## Results by Category

| Category | Pass | Warn | Fail |
|----------|------|------|------|
| Installation | ... | ... | ... |
| Commands & Skills | ... | ... | ... |
| Hook Configuration | ... | ... | ... |
| Hook Scripts | ... | ... | ... |
| Directory Layout | ... | ... | ... |
| Legacy Artifacts | ... | ... | ... |
| Optional Tools | ... | ... | ... |

## Remaining Issues (by priority)

### Critical
[List failures with fix commands]

### Important
[List warnings with fix commands]

### Optional
[List informational items]

## Recommended Next Steps
1. [Based on health score]
2. [Specific to findings]
```
</output>


<switch tool="AskUserQuestion">
  <case value="fix" next="LOOP">
    Fix — Run `pf validate --fix` to auto-repair all fixable issues
  </case>
  <case value="explain" next="LOOP">
    Explain — Deep dive on any remaining issue
  </case>
  <case value="continue" next="complete">
    Continue — Complete the health check workflow
  </case>
  <case value="recheck" next="LOOP">
    Recheck — Run full check again to verify fixes
  </case>
</switch>

## Failure Modes

- Reporting HEALTHY when critical issues were skipped in earlier steps
- Not prioritizing issues (user doesn't know what to fix first)

## Success Metrics

- Complete health report generated
- All issues categorized by priority
- Clear next steps provided
- User has actionable path to resolve any remaining issues
