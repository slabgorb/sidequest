---
name: 'step-07-validate'
description: 'Validate dry-run dir with sidequest-validate + cliche-judge in parallel; promote to real path on full pass'

nextStepFile: './step-08-playtest.md'
wipFile: '{wip_file}'
---

<purpose>Validate all generated content in the dry-run directory against both `sidequest-validate` (structural + schema) and `cliche-judge` (granularity rubric) in parallel. On full pass, atomically promote the dry-run directory to the real `sidequest-content/genre_packs/` path. On failure, preserve the dry-run directory for post-mortem and route fixes back to the originating specialists.</purpose>

<instructions>Fan out sidequest-validate and cliche-judge in parallel against the dry-run dir. Collect findings. Route blockers and fixes to specialists. On full pass, promote dry-run to real path. Never promote on partial pass.</instructions>

<output>Validated content promoted to real path. Validation report in WIP. stepsCompleted: [1, 2, 3, 4, 5, 6, 7].</output>

# Step 7: Validate (sidequest-validate + cliche-judge, parallel)

**Progress: Step 7 of 8**

## CONTEXT

Step 6 populated the dry-run directory at `.session/world-builder-dryrun/{genre}/{world}/`. Nothing has touched `sidequest-content/genre_packs/` yet. This step is the gatekeeper: if both validators pass, we promote. If either fails, we route fixes and re-validate. We never promote on partial pass.

**Two parallel validators:**

1. **`sidequest-validate`** — the Rust CLI binary. Structural and schema correctness. Deserializes every YAML against the actual Rust struct the server uses. Catches: missing required fields, wrong types, extra wrapper keys, malformed adjacency, broken cross-references. This is the hard gate; failures are unambiguous.

2. **`cliche-judge`** — the sixth specialist. Cliche-granularity rubric. Reads every specialist's `sources:` manifest, evaluates each named entity against the rubric, emits severity-tagged findings (`blocker | fix | nit`). Catches: category-level naming, missing sources, conflicts described at the wrong granularity, cliche prose texture. This is the soft gate; findings require judgment.

## SEQUENCE

### 1. Verify the dry-run directory exists and is populated

```bash
DRYRUN_BASE=".session/world-builder-dryrun/{genre}/{world}"
[ -d "$DRYRUN_BASE" ] || { echo "ERROR: no dry-run directory — step 6 must complete first"; exit 1; }
find "$DRYRUN_BASE" -name '*.yaml' | head -5  # sanity check
```

### 2. Fan out two parallel validators

**CRITICAL:** dispatch both in a **single message**. Sequential calls block unnecessarily.

**`sidequest-validate` invocation** (via Bash, not Task — this is a CLI, not an agent):

```bash
cd /Users/keithavery/Projects/oq-1/sidequest-api
cargo run --quiet -p sidequest-validate -- \
    --genre-packs-path /Users/keithavery/Projects/oq-1/.session/world-builder-dryrun/{genre} \
    --genre {genre} \
    2>&1 | tee /Users/keithavery/Projects/oq-1/.session/world-builder-wip/validate-output.txt
VALIDATE_EXIT=${PIPESTATUS[0]}
```

Note: the `--genre-packs-path` points at the dry-run directory, not the real `sidequest-content/genre_packs/`. The validator doesn't care where the genre packs live as long as the structure is right.

**`cliche-judge` invocation** (via Task tool, run in the same message as the Bash call above):

```
Task {
  subagent_type: "cliche-judge",
  description: "Cliche audit of {genre}/{world} dry-run",
  prompt: <cliche-judge task prompt below>
}
```

Cliche-judge task prompt:

```
You are the cliche-judge agent. Audit the just-generated world at the
dry-run directory:

.session/world-builder-dryrun/{genre}/{world}/

Read your agent definition at .claude/agents/cliche-judge.md to
remind yourself of the four-rule rubric and severity tagging.

## Specialist manifests
Every content specialist from step 6 emitted a return manifest with a
sources: field. Read all five manifests at:

.session/world-builder-wip/specialist-manifests/*.yaml

For every named entity in the content files, check that it appears
in the relevant specialist's sources: with a real-world analog at
the instance level. Missing sources = automatic blocker.

## Content files to audit
Walk the entire dry-run directory and read every .yaml file.

## Return findings
Emit your findings in the return manifest format from your agent
definition. Severity-tag every finding:

- blocker: category-level naming, missing sources, or cliche at the
  expertise-threshold level
- fix: one level too coarse, or a cliche phrase in descriptive prose
- nit: polish only

## Do NOT fix anything
You are a read-only auditor. Flag findings; never edit content. The
originating specialist will make fixes in a follow-up Task call.
```

### 3. Wait for both validators to complete

Parse the results:

**sidequest-validate:**
- `VALIDATE_EXIT == 0` → pass
- `VALIDATE_EXIT != 0` → fail; read `validate-output.txt` for errors

**cliche-judge:**
- Read the return manifest
- Count findings by severity
- `blockers == 0 && fixes == 0` → pass
- any blockers or fixes → fail (nits alone do not block)

### 4. On full pass, PROMOTE

If both validators pass:

```bash
DRYRUN_BASE=".session/world-builder-dryrun/{genre}/{world}"
REAL_BASE="sidequest-content/genre_packs/{genre}/worlds/{world}"

# Move the generated files from dry-run to real path
mkdir -p "$(dirname "$REAL_BASE")"

# Use rsync to copy and handle any existing files safely
rsync -av --checksum "$DRYRUN_BASE/worlds/{world}/" "$REAL_BASE/"

# Preserve the dry-run dir for audit (NOT deleted)
mv "$DRYRUN_BASE" ".session/world-builder-wip/dryrun-archive-{genre}-{world}-$(date +%Y%m%d-%H%M%S)"
```

Log the promotion:

```markdown
## Promotion ({date})
From: .session/world-builder-dryrun/{genre}/{world}
To:   sidequest-content/genre_packs/{genre}/worlds/{world}
Validators: sidequest-validate (PASS), cliche-judge (PASS — 0 blockers, 0 fixes, {N} nits parked)
Dry-run archived to: .session/world-builder-wip/dryrun-archive-{...}
```

### 5. On failure, route fixes back to specialists

**sidequest-validate failures:**

Parse the validator output for errors. Each error names a file and a reason. For each error:
1. Determine which specialist owns the file (from the step 6 ownership table)
2. Fire a Task call to that specialist with the validator error text and a fix instruction
3. The specialist writes the fix to the dry-run dir (NOT the real path)

Prompt shape:

```
You previously wrote {file} as part of world-builder fan-out for
{genre}/{world}. sidequest-validate reports the following errors:

{validator error text verbatim}

Fix the errors in the dry-run copy at:
.session/world-builder-dryrun/{genre}/{world}/worlds/{world}/{file}

Return an updated manifest with the files you modified. Do not touch
other specialists' files.
```

**cliche-judge failures:**

For each blocker and fix in cliche-judge's manifest:
1. Identify the originating specialist from the finding's `location:` field
2. Fire a Task call to that specialist with the cliche-judge finding and a rewrite instruction
3. The specialist rewrites the affected content with tighter granularity and updates its sources manifest

Prompt shape:

```
You previously authored {file} for {genre}/{world}. cliche-judge
flagged the following finding:

{finding rendered from manifest}

Rewrite the affected content at one granularity level below the
current level. Update your sources: manifest with the new real-world
analog. Do not change facts: without coordinating with world-builder.

Return an updated manifest.
```

### 6. Re-validate after fixes

Repeat step 2-3 after fixes are applied. **Retry budget: three full fix-and-revalidate cycles.** After three, HALT and escalate to Keith with the remaining failing findings.

### 7. Naming audit (deterministic, world-builder's own work)

After both validators pass, run a final naming audit as a sanity check:

```bash
# Scan every `name:` field across the dry-run world files
# Flag any name that is English-descriptive rather than corpus-derived
python3 -c "
import yaml, os, sys
# ... scan logic ...
"
```

Any English-descriptive name is routed to the conlang agent for a rewrite. This check is belt-and-suspenders — writer and scenario-designer should never introduce English names if they're honoring the 'conlang IS the voice' rule, but the audit catches slip-throughs.

### 8. Update WIP

Append to `{wipFile}`:

```markdown
## Validation

sidequest-validate: PASS
cliche-judge: PASS (0 blockers, 0 fixes, {N} nits parked to follow-up)
Naming audit: PASS
Structural coherence: PASS

Promoted to: sidequest-content/genre_packs/{genre}/worlds/{world}
Dry-run archived: .session/world-builder-wip/dryrun-archive-{...}

### Fixes applied during re-validation
{list of specialists that fixed something, with file counts}
```

Update frontmatter: `stepsCompleted: [1, 2, 3, 4, 5, 6, 7]`

### 9. Hand off to step 8

Step 8 runs the playtest and the second (post-playtest) audit fan-out. The content is now in its real home; step 8 audits it under real rendering conditions.

---

## What this step does NOT do

- Does not author content. Validation is read-only (deterministic checks) or routes fixes to specialists (Task-tool calls). World-builder never edits content files directly in this step.
- Does not run the playtest. Step 8 owns playtest and playtest-driven audit.
- Does not promote on partial pass. Both validators must pass. Cliche-judge nits alone do not block — blockers and fixes do.
- Does not delete the dry-run directory. On promotion, it's moved to an archive folder for post-mortem. The archive is kept until manually cleaned up.
- Does not handle engine bugs. Validator catches YAML schema issues; engine bugs surface in step 8 playtest.

## Failure modes

| Failure | Recovery |
|---|---|
| sidequest-validate exits non-zero | Route errors to owning specialist; retry (budget: 3) |
| cliche-judge returns blockers | Route findings to owning specialist; retry (budget: 3) |
| cliche-judge returns only nits | Park nits to follow-up file; proceed to promotion |
| Specialist's fix introduces new validator error | Increment retry counter; if budget exhausted, escalate |
| Missing specialist manifest in `specialist-manifests/` | Return to step 6 with that specialist flagged for re-run |
| Promotion step fails (rsync error, filesystem issue) | HALT and report; the dry-run dir is still intact |
