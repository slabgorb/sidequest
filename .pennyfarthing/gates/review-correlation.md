<gate name="review-correlation" model="haiku">

<purpose>
Institutional memory gate: correlates review findings from ALL sources with
language-specific review checklists and ensures the checklist is updated.

Triggered when the dev is addressing feedback — from internal reviewers, CI
failures, or external reviewers (humans, AI bots like CodeRabbit, maintainers).

**External findings are highest priority.** They represent gaps our entire
internal pipeline missed — the dev self-review, the TEA verification, AND the
internal reviewer all failed to catch what an outsider found. These MUST become
new checks with the highest confidence.

Source priority for new checks:
1. External reviewer / maintainer (pipeline-blind-spot — highest signal)
2. CI / automated tooling (reproducible, automatable)
3. Internal reviewer (caught in-process, still valuable)

This is the feedback loop that makes lang-review checklists self-improving.
Every finding either maps to an existing check (process failure: dev missed it)
or becomes a new check (knowledge gap: checklist didn't cover it).
</purpose>

<pass>
## Correlation Process

**Step 1: Gather inputs from ALL sources**

Collect findings from every available source:

**Internal reviewer** — Read the session file for:
- `review_findings` or `## Reviewer Assessment` section
- Delivery findings from other agents

**CI / automated tooling** — Check for:
- CI failure logs (GitHub Actions, etc.) via `gh run view` or session notes
- Linter/formatter violations not caught by local checks
- Security scanner findings (dependabot, CodeQL, Snyk)
- Type checker errors that passed locally but failed in CI

**External reviewers** — Check for:
- PR review comments from humans via `gh pr view --comments`
- AI reviewer feedback (CodeRabbit, Copilot, etc.)
- Maintainer feedback on upstream PRs
- These are tagged `source: external` in the correlation table

Read `**Repos:**` from the session file to determine which repos are involved.
Read `.pennyfarthing/repos.yaml` for the repo's `language` or `languages` field.

Locate the corresponding lang-review checklist(s) at:
- `.pennyfarthing/gates/lang-review/{language}.md` (project-local override), or
- `pennyfarthing-dist/gates/lang-review/{language}.md` (built-in)

If no lang-review checklist exists for this language, return pass with a note
that no checklist is available for correlation.

**Step 2: Correlate each finding**

For each finding from any source, determine:

| Classification | Meaning | Action Required |
|---------------|---------|-----------------|
| **EXISTING_CHECK** | Maps to an existing checklist check | Note which check; dev missed it |
| **NEW_CHECK** | Class of bug not in the checklist | Must add to checklist |
| **NOT_APPLICABLE** | Project-specific, not a language pattern | No checklist update needed |
| **TOOLING** | Should be caught by linter/CI config | Suggest tooling update |
| **PROCESS** | Workflow gap (e.g., missing gate, wrong phase order) | Suggest process change |

**Step 3: Verify checklist updates**

For each finding classified as `NEW_CHECK`:
- Verify a new check was added to the **project-local** lang-review checklist
  at `.pennyfarthing/gates/lang-review/{language}.md` — NEVER write to
  `pennyfarthing-dist/gates/lang-review/` (those are built-in starters that
  get overwritten on framework upgrade). If the project-local file doesn't
  exist yet, copy the built-in starter and then append the new check.
- The new check MUST include:
  - A descriptive title
  - Specific patterns to search for
  - Provenance tag with source and reference:
    - Internal: `*Origin: PR#{number} I{finding_number} ({brief})*`
    - CI: `*Origin: CI#{run_id} ({tool}: {brief})*`
    - External: `*Origin: PR#{number} EXT-{reviewer} ({brief})*`
- The check should be general enough to catch the CLASS of bug, not just this instance
- External-sourced checks get an additional `**[EXT]**` prefix in the title to
  flag that our entire internal pipeline missed this class of issue

For each finding classified as `EXISTING_CHECK`:
- Note which existing check should have caught it
- If the same check is missed repeatedly (3+ times across PRs), flag for
  promotion to an automated gate or CI rule

For each finding classified as `TOOLING`:
- Verify a note was added to the session's Delivery Findings suggesting the
  CI/linter config change

For each finding classified as `PROCESS`:
- Verify a note was added to the session's Delivery Findings describing the
  workflow gap and suggested fix

**Step 4: Verify correlation table**

The dev must have written a correlation table to the session file's
`## Review Correlation` section:

```markdown
## Review Correlation

| # | Source | Finding | Classification | Checklist Check | Action |
|---|--------|---------|---------------|-----------------|--------|
| 1 | reviewer | Missing error handling on parse | EXISTING_CHECK | #1 Silent errors | Dev missed existing check |
| 2 | external | Hardcoded timeout value | NEW_CHECK | — | Added as check #16 [EXT] |
| 3 | CI | Unused import | TOOLING | — | Add to ruff config |
| 4 | external | Missing rate limit on endpoint | NEW_CHECK | — | Added as check #17 [EXT] |
| 5 | reviewer | Typo in variable name | NOT_APPLICABLE | — | Project-specific |
| 6 | CI | Type error in edge case | PROCESS | — | Add stricter CI type check |

### Signal Summary
- **External findings: 2** (pipeline blind spots — highest priority)
- **CI findings: 2** (automatable)
- **Internal findings: 2** (caught in-process)
- **New checks added: 2** (both from external — our process missed these entirely)
```

If ALL of the following are true, return pass:

1. Every finding from every source has a classification
2. Every NEW_CHECK finding has a corresponding new checklist entry with provenance
3. External-sourced NEW_CHECKs are prefixed with `[EXT]` in the checklist
4. Correlation table is present in the session file with Source column
5. Signal summary tallies findings by source

```yaml
GATE_RESULT:
  status: pass
  gate: review-correlation
  message: "Review findings correlated ({N} findings from {sources} sources: {existing} existing, {new} new checks [{ext_new} from external], {na} n/a, {tooling} tooling, {process} process)"
  checks:
    - name: correlation-complete
      status: pass
      detail: "All {N} findings classified (internal: {int}, external: {ext}, CI: {ci})"
    - name: checklist-updates
      status: pass
      detail: "{new} new checks added to {language} checklist ({ext_new} from external sources)"
    - name: external-findings
      status: pass
      detail: "{ext} external findings processed — {ext_new} new checks, {ext_existing} existing, {ext_na} n/a"
    - name: correlation-table
      status: pass
      detail: "Correlation table with source column and signal summary written to session"
```
</pass>

<fail>
If any of the following are true:

- Findings from any source exist but no correlation was attempted
- External findings are not processed (highest priority — cannot skip)
- Findings classified as NEW_CHECK but no checklist entry was added
- New checklist entries are missing provenance tags
- External-sourced NEW_CHECKs are missing the `[EXT]` prefix
- New checklist entries are too specific (only catch this exact bug, not the class)
- Correlation table is missing the Source column
- Correlation table is missing from the session file

```yaml
GATE_RESULT:
  status: fail
  gate: review-correlation
  message: "Review correlation incomplete"
  checks:
    - name: correlation-complete
      status: pass | fail
      detail: "{N} findings not yet classified"
    - name: checklist-updates
      status: pass | fail
      detail: "{N} NEW_CHECK findings without corresponding checklist entry"
    - name: external-findings
      status: pass | fail
      detail: "{N} external findings not processed (these are highest priority)"
    - name: correlation-table
      status: pass | fail
      detail: "Correlation table missing or incomplete"
  recovery:
    - "Process external findings FIRST — they represent pipeline blind spots"
    - "Classify each finding as EXISTING_CHECK, NEW_CHECK, NOT_APPLICABLE, TOOLING, or PROCESS"
    - "For NEW_CHECK: add check to .pennyfarthing/gates/lang-review/{language}.md (project-local, never pennyfarthing-dist/)"
    - "For external NEW_CHECK: prefix with [EXT] and use *Origin: PR#{n} EXT-{reviewer} ({brief})*"
    - "For TOOLING: note CI/linter config change in Delivery Findings"
    - "For PROCESS: note workflow gap in Delivery Findings"
    - "Write correlation table with Source column to session under ## Review Correlation"
    - "Include signal summary tallying findings by source"
    - "Ensure new checks target the CLASS of bug, not just this specific instance"
```
</fail>

</gate>
