---
name: 'step-08-playtest'
description: 'Run playtest, fan out six specialists for domain audits, route fixes, ship PR'

wipFile: '{wip_file}'
---

<purpose>Verify generated content works in an actual game session. Run a playtest, fan out all six specialists (five content + cliche-judge) in parallel for domain-specific audits of the played world, consolidate findings with a severity rubric, route fixes back to the originating specialist, and ship the PR.</purpose>

<instructions>Use the sq-playtest skill to run a playtest. Fan out to the six specialists via Task tool for parallel audits. Consolidate findings. Route blockers and fixes back to specialists; park nits for follow-up. Commit and open PR.</instructions>

<output>Playtest report with domain-audited content verified. Fixes routed and applied. WIP archived. PR opened against develop. stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8].</output>

# Step 8: Playtest & Iterate (Fan-Out Audit)

**Progress: Step 8 of 8**

## CONTEXT

- Content has passed structural validation in step 7.
- This step verifies the content **plays well** — distinct from structural correctness. Plays-well means: the audience experiences it the way we intended, the specialists' work holds up under actual rendering, and nothing in production blocks the world from shipping.
- **Content issues** (shallow prose, orphaned assets, cliche naming, manifest drift, music missing a scene category) → flagged by specialists, routed back to the originator for resolution.
- **Engine bugs** (crashes, wiring issues, protocol errors) → not in any specialist's lane. Hand off to SM via scratch file.

## The fan-out audit pattern

This step reuses the Task-tool-fan-out pattern proven in step 3. All six specialists audit their domain in parallel:

| Specialist | Audits |
|---|---|
| `art-director` | `visual_style.yaml`, portrait sets, POI coverage, LoRA caption schema, portrait manifest threading |
| `music-director` | `audio.yaml`, music/sfx/ambience file presence, ACE-Step params, manifest block sync |
| `writer` | prose coherence, spoiler protection, Story Now alignment, named-figure threading across history/lore/legends |
| `conlang` | `cultures.yaml` bindings, corpus file types and language validity, live namegen output samples |
| `scenario-designer` | `tropes.yaml` escalation completeness, `rules.yaml` resource declarations, archetype mechanical coverage, sidequest-validate status |
| `cliche-judge` | every specialist's `sources:` manifest, cliche-granularity rubric (named entities, conflicts, cultural practices, archetypes, prose texture) |

All audits are **read-only** — they return findings, not fixes. Fixes are routed back to the originating specialist in a follow-up Task call.

## SEQUENCE

### 1. Run the playtest

Use `/sq-playtest` to launch a test session:
- Select the target genre/world
- Play through character creation
- Explore 2-3 regions
- Interact with NPCs
- Trigger at least one trope beat
- Test faction dynamics

The playtest produces a session log at `.session/world-builder-wip/playtest-log.md`. That log is the shared context all six audit specialists read.

### 2. Fan out the six audits in parallel

**CRITICAL:** dispatch all six Task calls in a **single message**. That is what triggers true parallel execution.

For each specialist, the Task prompt is shaped like:

```
You are the {specialist} agent. Audit the just-played world for your
domain. The played world is at:
    sidequest-content/genre_packs/{genre}/worlds/{world}/

The playtest session log is at:
    .session/world-builder-wip/playtest-log.md

Read your own agent definition at .claude/agents/{specialist}.md to
remind yourself of your ownership boundaries, audit rules, and return
manifest requirements.

Audit the content for your domain only. Stay in your lane — if you
find something out of lane, flag it as a cross-lane observation
(severity: nit) and move on.

Every finding must be tagged with a severity:

- blocker: the world cannot ship with this issue
- fix: the world ships worse with this issue; resolve before PR
- nit: polish only, can go to a follow-up file

Return findings in the manifest format defined in your agent
definition. Every finding gets: rule/category, severity, location
(file path + line if applicable), entity/description, reason, and
suggested remediation (or null for nits).

Your manifest MUST be emitted as the last content block of your
response. Missing manifest = retry.

Audit the played world.
```

For `cliche-judge`, the prompt additionally instructs: "Read every other specialist's `sources:` manifest from their prior step 6 returns (collected in `.session/world-builder-wip/specialist-manifests/*.yaml`). Evaluate each named entity against the cliche-granularity rubric. Missing `sources:` is an automatic blocker."

### 3. Wait for all six to complete

Parse each returned manifest. Check for:
- Missing manifest → retry that specialist with the same prompt
- Errors in the manifest's `errors:` field → note and retry once if transient, escalate if persistent

### 4. Consolidate findings

Merge all six specialists' findings into `.session/world-builder-wip/playtest-findings.md`:

```markdown
# Playtest Findings — {genre}/{world} — {date}

## Summary
- Blockers: {count across all specialists}
- Fixes: {count}
- Nits: {count}

## Blockers (must fix before ship)

### [{specialist}] {finding title}
- **Location:** {file:line}
- **Reason:** {one sentence}
- **Suggested remediation:** {specialist's suggestion}

[repeat for every blocker]

## Fixes (ship worse without them)

[same structure, grouped by severity]

## Nits (follow-up file)

[same structure, grouped by severity, parked for a follow-up PR]

## Cross-lane observations

[things specialists flagged outside their own lane as nit-severity —
worth a look but not routed as fixes]
```

### 5. Route fixes

For every `blocker` and `fix` finding, fire a follow-up Task call to the **originating specialist** (not a different one, even if the fix looks like it's in another domain — escalate to world-builder for lane reassignment if needed). The prompt is shaped like:

```
You previously audited {genre}/{world} and flagged the following
finding:

{finding rendered from the manifest}

Apply the fix. Write the corrected files. Return a manifest with the
files you modified.

Do not touch other specialists' domains. If the fix requires a change
in another lane, flag it as a nit with `requires_coordinator_routing:
true` and do not make the change.
```

Fan out the fix calls in parallel — one per specialist that has at least one blocker or fix. If multiple specialists each have multiple fixes, each specialist gets one Task call with all their fixes in the prompt.

### 6. Re-validate

After fixes are applied:
1. Run `sidequest-validate` against the real content path (no longer the dry-run dir at this stage — we promoted in step 7)
2. Fan out `cliche-judge` one more time to verify the blocker-level cliche findings were actually resolved
3. If new blockers appear, loop back to step 5

**Retry budget:** three full fix-and-revalidate cycles. After three, HALT and escalate to Keith with the remaining blocker list.

### 7. Park nits for follow-up

Write `.session/world-builder-wip/playtest-nits-followup.md` with all `nit`-severity findings and cross-lane observations. This file becomes a GitHub issue attached to the PR — not a blocker for this world, but a follow-up polish pass.

### 8. Engine bug escalation

If the playtest surfaced an engine bug (crash, wiring issue, protocol error — nothing a content specialist can fix), write to the SM scratch file:

```markdown
## Engine Bug: {description}
- Found during: world-builder playtest of {genre}/{world}
- Symptoms: {what happened}
- Expected: {what should happen}
- Likely location: {guess at code path}
- Playtest log: .session/world-builder-wip/playtest-log.md
```

Do NOT attempt to fix engine code. Route to SM for Dev assignment.

### 9. Archive WIP

Update WIP frontmatter: `stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]`, `status: 'complete'`.

Archive: move `{wipFile}` to `.session/world-builder-{genre}-{world}-complete-{date}.md`. Include links to:
- `.session/world-builder-wip/playtest-log.md`
- `.session/world-builder-wip/playtest-findings.md`
- `.session/world-builder-wip/playtest-nits-followup.md`
- `.session/world-builder-wip/specialist-manifests/`

### 10. Commit content and open PR

```bash
cd sidequest-content
git checkout -b feat/{genre}-{world}
git add genre_packs/{genre}/
git commit -m "feat({genre}): {world} — new world content"
git push -u origin feat/{genre}-{world}
```

Open PR targeting `develop` with body structured as:

```markdown
## Summary
{world} world for the {genre} genre pack, generated via sq-world-builder
federation refactor Phase C.

## Specialists invoked
- writer, scenario-designer, conlang, art-director, music-director
- cliche-judge (validation)

## Playtest findings
- Blockers resolved: {count}
- Fixes applied: {count}
- Nits parked: {count} (see follow-up issue)

## Test plan
- [x] sidequest-validate passes
- [x] cliche-judge passes (no category-level named entities)
- [x] Playtest completed; all blocker findings resolved
- [x] Fact-diff across specialists returned no contradictions (or escalated and resolved)
- [ ] Reviewer spot-check against the source brief

## Related
- Plan: ~/.claude/plans/federated-skipping-frost.md
- Brief: {brief file path}
- Collision: .session/world-builder-wip/collision.md
```

Report final status to Keith.

---

## What this step does NOT do

- Does not fix content directly. Fixes are routed to the originating specialist.
- Does not fix engine code. Engine bugs escalate to SM.
- Does not skip cliche-judge. Cliche-judge runs on the played world even though it already ran in step 7 — step 7 audits the dry-run dir; step 8 audits the promoted content under real rendering conditions.
- Does not write a blanket "ship it" PR without fixes. The retry budget exists for a reason — if it blows out, escalate rather than ship broken.
