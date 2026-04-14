---
name: 'step-06-generate'
description: 'Fan out content authoring to five specialists in parallel; write to dry-run dir; merge shared files serially'

nextStepFile: './step-07-validate.md'
wipFile: '{wip_file}'
---

<purpose>Generate all world content by fanning out to the five content specialists in parallel via Task tool. Each specialist writes to the dry-run directory first — nothing touches the real `sidequest-content/genre_packs/` path until step 7 validation passes. Shared files are handled via a serial merge pass after the parallel phase.</purpose>

<instructions>Read the design brief, fan out five Task calls in one message, parse return manifests for partial-failure detection, run fact-diff across specialists, serial-merge shared files, hand off to step 7 for validation and promotion. In surprise mode, fact-diff conflicts are the one place where human escalation is MANDATORY.</instructions>

<output>Dry-run directory populated with all specialist-authored files. Return manifests collected for fact-diff and cliche-judge consumption. stepsCompleted: [1, 2, 3, 4, 5, 6].</output>

# Step 6: Generate (Specialist Fan-Out + Dry-Run Directory)

**Progress: Step 6 of 8**

## CONTEXT

This is the most structurally significant step of the federation refactor. Before Phase C, world-builder authored every YAML file itself inline. Now it delegates authoring to the five content specialists in a single-message parallel Task fan-out.

**Why a dry-run directory:** five parallel subagents writing files is powerful but dangerous. Partial failure (one specialist crashes mid-run, two specialists accidentally touch the same file, a fact-diff reveals contradiction after files are already written) would leave the real `sidequest-content/genre_packs/` path in a half-baked state. The dry-run directory at `.session/world-builder-dryrun/{genre}/{world}/` absorbs all first-pass writes; promotion to the real path happens only after step 7 validation AND cliche-judge both pass.

**Why exclusive file ownership:** two specialists writing the same file in parallel produces last-write-wins. To prevent this, the parallel phase has a strict ownership table (below); shared files (`cultures.yaml`, `archetypes.yaml`) go through a serial merge phase AFTER the parallel phase, owned by world-builder's coordinator merge pass.

**Why fact-diff escalates:** specialists declare structured facts in their return manifests (`facts:` block). World-builder runs a fact-diff across all five manifests. Contradictions (writer says kingdom fell 1240; scenario-designer's tropes assume kingdom active) are the one place surprise mode MUST break surprise and escalate to Keith. Factual contradictions are narrative decisions, not mechanical ones — a coordinator papering over them would produce an incoherent world.

## PREREQUISITES

Before fanning out:
1. The design brief exists at `.session/world-builder-wip/design-brief.md` (written in step 5).
2. The collision artifact exists at `.session/world-builder-wip/collision.md` (written in step 3).
3. The dry-run directory structure is ready: `.session/world-builder-dryrun/{genre}/{world}/`.
4. The drift check in step 1 passed (OQ-1 and sidequest-content agent copies are in sync).
5. `cultures.yaml` at the pack level is SOLID — world-builder has read it and verified the naming system is in place. **This is the "conlang IS the voice" gatekeeper check.** If cultures.yaml is missing or the corpus bindings are broken, HALT and run conlang as a preparatory single invocation to fix it BEFORE the parallel fan-out.

## OWNERSHIP TABLE (parallel phase)

Each specialist has exclusive ownership of its files during the parallel phase. No two specialists write the same file in parallel.

| Specialist | Owns (parallel phase) |
|---|---|
| `writer` | `worlds/{world}/lore.yaml`, `history.yaml`, `legends.yaml`, `openings.yaml` |
| `scenario-designer` | `worlds/{world}/tropes.yaml` |
| `conlang` | `worlds/{world}/cultures.yaml` (world-scoped corpus bindings + naming patterns) |
| `art-director` | `worlds/{world}/visual_style.yaml`, `worlds/{world}/portrait_manifest.yaml` |
| `music-director` | `worlds/{world}/audio.yaml` |

**Shared files** — written in the serial merge phase AFTER parallel:
- `worlds/{world}/archetypes.yaml` — writer supplies prose fields, scenario-designer supplies mechanical fields; world-builder merges
- `worlds/{world}/cartography.yaml` — writer supplies POI prose, world-builder owns structure (adjacency, terrain); merged by coordinator

Genre-pack-level files (`pack.yaml`, `rules.yaml`, `powers.yaml`, etc.) are **out of scope for a new-world run** — they already exist. A new-genre run (not covered in this step file's primary flow) would require a separate pack-level fan-out with pack-level ownership.

## SEQUENCE

### 1. Create the dry-run directory

```bash
DRYRUN_BASE=".session/world-builder-dryrun/{genre}/{world}"
mkdir -p "$DRYRUN_BASE/worlds/{world}"
mkdir -p ".session/world-builder-wip/specialist-manifests"
```

Clean any prior dry-run output for this target (dry-run is ephemeral; each generation starts clean):

```bash
rm -rf "$DRYRUN_BASE"
mkdir -p "$DRYRUN_BASE/worlds/{world}"
```

### 2. Verify the design brief exists

```bash
BRIEF=".session/world-builder-wip/design-brief.md"
[ -f "$BRIEF" ] || { echo "ERROR: design brief missing at $BRIEF. Step 5 must complete before step 6."; exit 1; }
```

### 3. Fan out five parallel Task calls in a single message

**CRITICAL:** dispatch all five Task calls in ONE message. Sequential calls block; parallel calls run concurrently.

Each specialist gets a prompt shaped like:

```
You are the {specialist} agent. Author your domain's content for the
new world {genre}/{world}.

## Design brief (primary input — read this first)
.session/world-builder-wip/design-brief.md

## Research collision (creative fuel)
.session/world-builder-wip/collision.md

## Per-lens research (reference material, consult as needed)
.session/world-builder-wip/research-political.md
.session/world-builder-wip/research-material.md
.session/world-builder-wip/research-spiritual.md

## Your agent definition
.claude/agents/{specialist}.md — read this to remind yourself of your
ownership boundaries, CLAUDE.md principles, cliche-granularity
discipline, and return manifest requirements.

## Genre pack context
sidequest-content/genre_packs/{genre}/ — the target genre pack.
Read rules.yaml, cultures.yaml, and axes.yaml for mechanical and
tonal context.

## Output target
.session/world-builder-dryrun/{genre}/{world}/worlds/{world}/

Write YOUR files (per your ownership table entry) to that path. DO NOT
write to sidequest-content/genre_packs/ directly — the dry-run
directory is the target for this pass. World-builder will promote
the files after step 7 validation passes.

## Your file ownership this pass
{specialist's file list from the ownership table}

## Cliche-granularity discipline (MANDATORY)
Every named entity you introduce must operate at least one
granularity level below the audience's expertise threshold. The
audience is a 40-year TTRPG veteran. Not "voodoo" — "Candomblé Ketu."
Not "colonial India" — "1887 Mysore succession dispute." Not "fallen
empire" — "Vijayanagara post-Talikota 1565."

Every named entity must appear in your return manifest's `sources:`
field with its real-world analog at the instance level. No `sources:`
entry = automatic cliche-judge blocker in step 7.

## Return manifest (MANDATORY — final content block)
Emit your manifest as the LAST content block of your response,
per the format in your agent definition. Missing manifest = task
failure, world-builder will retry. Required fields:

- files_written: [list of files you wrote in the dry-run dir]
- files_skipped: [files you were supposed to write but couldn't,
  with reasons]
- errors: [any errors encountered]
- facts: {scalar facts about the world you committed to in your
  content — dates, counts, named anchors — for fact-diff across
  specialists}
- sources: {named entity → real-world analog mapping for every
  entity you introduced}

## Go
Author your files now. Stay in your lane.
```

### 4. Wait for all five to complete

Read each specialist's final response. Extract the manifest block.

For each specialist:
1. If the manifest is missing → retry that specialist with the same prompt. Max 2 retries. After 2, HALT and escalate.
2. If the manifest has errors in `errors:` → evaluate: transient (retry) vs persistent (escalate).
3. Save the manifest to `.session/world-builder-wip/specialist-manifests/{specialist}.yaml`.

### 5. Fact-diff across specialists

Read all five `facts:` blocks. Look for contradictions:

- **Scalar contradiction** — same key, different values. Example: `writer.facts.kingdom_falls = 1240` but `scenario-designer.facts.kingdom_falls = 1315`.
- **Compositional contradiction** — related keys that don't line up. Example: `writer.facts.pantheon_size = 7` but `scenario-designer` references 9 deities in tropes.
- **Boolean contradiction** — `writer.facts.magic_is_public = true` but `art-director.facts.magic_visual_style = "hidden/coded"`.

For each contradiction found, **HALT regardless of surprise mode** and escalate to Keith:

```
FACT-DIFF CONFLICT

{writer}: {key} = {value}
{scenario-designer}: {key} = {value}

This is a narrative decision that needs human resolution. Two options:

A) {phrasing of option A, with which specialists need to rewrite what}
B) {phrasing of option B}

Which?
```

Wait for Keith's choice. Then fire a Task call to the specialist(s) whose facts need to change, instructing them to rewrite with the new fact. Re-run fact-diff until clean.

**Retry budget:** three fact-diff cycles. After three, the seed may be underspecified or intrinsically contradictory — escalate to step 4 refine for a new take.

### 6. Serial merge phase (shared files)

After the parallel phase and fact-diff are clean, world-builder handles the shared files:

#### archetypes.yaml

Writer and scenario-designer both contribute. Writer's return manifest includes prose fields (`description`, `personality_traits`, `dialogue_quirks`, `inventory_hints`). Scenario-designer's manifest includes mechanical fields (`stat_ranges`, `ocean`, `typical_classes`, `starting_inventory`).

World-builder reads both, constructs the merged archetypes.yaml in the dry-run dir. Validates that every archetype has BOTH halves populated. If writer missed an archetype's prose OR scenario-designer missed an archetype's mechanics, fire a targeted Task call to the missing specialist.

#### cartography.yaml

Writer provides POI prose text. World-builder owns the structural fields (regions, adjacency, routes, terrain). World-builder reads the writer's POI slice and assembles the cartography.yaml with:
- Structural framework from the design brief
- POI prose from writer's slice
- Adjacency check (bidirectional — A→B implies B→A)
- Route endpoint resolution (every route references existing regions)

### 7. Run structural coherence checks (deterministic)

Before handing off to step 7:
- **Cartography adjacency** — every `region.connects_to` has a reciprocal entry
- **Naming threading** — every `name` field in the dry-run world files matches a `place_pattern` or `person_pattern` from the culture's naming system. No English descriptive names.
- **Resource declarations** — every resource referenced in tropes or powers is declared in `rules.yaml` at the pack level
- **File completeness** — every file required by the target mode exists in the dry-run dir
- **Cross-file reference resolution** — every named figure in history.yaml appears in legends.yaml or archetypes.yaml or vice versa

If any check fails, route the fix back to the originating specialist. Do not silently patch in world-builder's own voice.

### 8. Update WIP

Append to `{wipFile}`:

```markdown
## Generation (Specialist Fan-Out)

Dry-run location: `.session/world-builder-dryrun/{genre}/{world}/`
Specialist manifests: `.session/world-builder-wip/specialist-manifests/`

### Files written (by specialist)
- writer: {list}
- scenario-designer: {list}
- conlang: {list}
- art-director: {list}
- music-director: {list}

### Shared files (serial merge)
- archetypes.yaml (writer prose + scenario-designer mechanics)
- cartography.yaml (writer POIs + world-builder structure)

### Fact-diff status
{clean | escalations resolved: {count}}

### Structural checks
- Cartography adjacency: pass
- Naming threading: pass
- Resource declarations: pass
- File completeness: pass
- Cross-file references: pass

Ready for step 7 validation (promotion blocked until sidequest-validate
AND cliche-judge pass against the dry-run dir).
```

Update frontmatter: `stepsCompleted: [1, 2, 3, 4, 5, 6]`

### 9. Hand off to step 7

Step 7 will run `sidequest-validate` and `cliche-judge` in parallel against the dry-run dir. Only on full pass does step 7 promote the dry-run files to the real `sidequest-content/genre_packs/` path.

Do NOT write anything to the real path from this step. Do NOT preemptively commit the dry-run files. The dry-run is ephemeral; promotion is step 7's job.

---

## What this step does NOT do

- Does not write to `sidequest-content/genre_packs/` directly. All writes go to the dry-run dir first.
- Does not resolve factual contradictions silently. Fact-diff conflicts HALT and escalate to Keith regardless of surprise mode.
- Does not invoke cliche-judge. Cliche-judge runs in step 7 after the dry-run dir is fully populated.
- Does not run `sidequest-validate`. Also step 7.
- Does not handle pack-level (genre-level) file generation in its primary flow. That's a separate fan-out with pack-level ownership, not covered here.
- Does not promote files from dry-run to real path. Step 7 owns promotion as the atomic final act after validation.

## Failure modes and recovery

| Failure | Recovery |
|---|---|
| Specialist returns without a manifest | Retry that specialist (max 2) |
| Specialist's `errors:` is non-empty (transient) | Retry once |
| Specialist's `errors:` is non-empty (persistent) | Escalate to Keith with error text |
| Two specialists write the same non-shared file | Never happens if ownership table is enforced — but if it does, HALT and audit |
| Fact-diff contradiction | Escalate to Keith (mandatory human interruption, even in surprise mode) |
| Fact-diff contradiction after 3 cycles | Escalate to step 4 refine for new take |
| Structural check fails | Route to originating specialist; retry once |
| Dry-run dir cannot be created | System failure; HALT |
