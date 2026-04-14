---
name: 'step-01-orient'
description: 'Select mode, identify target genre/world, check for WIP'

nextStepFile: './step-02-riff.md'
skipToStepFile: './step-03-research.md'
wipFile: '{wip_file}'
---

<purpose>Determine what kind of content work the user needs, identify the target genre pack and world, and check for existing work-in-progress.</purpose>

<instructions>Check WIP, ask user for mode, identify target, read existing content for context.</instructions>

<output>Initialized WIP file with mode, target genre/world, and session goals.</output>

# Step 1: Orient

**Progress: Step 1 of 8**

## PREAMBLE — Drift Check (ALWAYS RUN FIRST)

Before anything else, verify the content specialists at `/Users/keithavery/Projects/oq-1/.claude/agents/` have not drifted from the canonical copies at `/Users/keithavery/Projects/oq-1/sidequest-content/.claude/agents/`. Claude Code discovers subagents only from the project root, so OQ-1 needs a local copy — but the source of truth lives in sidequest-content. Drift means world-builder is invoking a stale specialist.

Run this bash preamble. If it fails, HALT and ask Keith to reconcile before proceeding:

```bash
DRIFT=0
for agent in art-director music-director writer conlang scenario-designer cliche-judge; do
    OQ1="/Users/keithavery/Projects/oq-1/.claude/agents/$agent.md"
    SQC="/Users/keithavery/Projects/oq-1/sidequest-content/.claude/agents/$agent.md"
    if [ ! -f "$OQ1" ]; then
        echo "ERROR: $agent.md missing from OQ-1 (.claude/agents/)"
        DRIFT=1
    elif [ ! -f "$SQC" ]; then
        echo "ERROR: $agent.md missing from sidequest-content (.claude/agents/)"
        DRIFT=1
    elif ! diff -q "$OQ1" "$SQC" >/dev/null 2>&1; then
        echo "DRIFT: $agent.md differs between OQ-1 and sidequest-content. Reconcile before proceeding."
        DRIFT=1
    fi
done
[ $DRIFT -eq 0 ] && echo "OK: all specialist files in sync."
exit $DRIFT
```

**Fail loudly. Never silently overwrite either side.** Reconciliation is a human decision about which version is authoritative. If the check passes, continue to SEQUENCE.

## SEQUENCE

### 0. Check for Work in Progress

a) Check if `{wipFile}` exists.

b) **IF WIP EXISTS:**
1. Read frontmatter: `mode`, `genre`, `world`, `stepsCompleted`
2. Present:
```
Found world-builder session in progress:

**{genre}/{world}** — Mode: {mode}, Step {lastStep} of 6

[Y] Continue where I left off
[N] Start fresh
```
3. **HALT and wait for user selection.**
   - **[Y]** → Jump to next incomplete step
   - **[N]** → Archive WIP to `.session/world-builder-{genre}-{world}-archived-{date}.md`

### 1. Mode Selection

Ask the user which mode:

1. **New Genre Pack** — Create a genre from scratch
2. **New World** — Build a world within an existing genre pack
3. **Asset Management** — Fonts, visual style, theme, audio config
4. **DM Prep** — Between-session tuning (NPCs, regions, tropes, audio)
5. **Playtest & Iterate** — Run playtest, interpret results, fix content

Also ask whether **Surprise Mode** is on for this session:

- **Surprise Mode OFF (default)** — Standard stepped workflow with human approval gates at steps 2, 3, 4, 5
- **Surprise Mode ON** — Gates skipped. Research runs as a three-lens parallel fan-out. Design brief auto-generates. Generation writes to the dry-run directory first. The only human contact points are: (a) this mode selection, (b) step 2 seed input, (c) fact-conflict escalations from step 6 (if any), (d) final PR review. The deterministic safety rails (coherence assertion, dry-run dir, `sidequest-validate`, `cliche-judge`) still run. Surprise Mode is compatible with New Genre, New World, and DM Prep modes only.

**HALT and wait for selection.**

### 2. Identify Target

Based on mode:
- **New Genre:** Ask for genre concept, inspirations, tone
- **New World:** Which genre pack? What historical/cultural concept?
- **Asset Management:** Which genre/world? What assets?
- **DM Prep:** Which active campaign?
- **Playtest:** Which genre/world to test?

### 3. Read Existing Content

- Read `{genre_packs_path}/<genre>/pack.yaml` (if existing genre)
- Read `{genre_packs_path}/<genre>/rules.yaml` — understand the mechanical framework
- Read `{genre_packs_path}/<genre>/cultures.yaml` — **CRITICAL: internalize naming patterns**
- Read `{genre_packs_path}/<genre>/axes.yaml` — tone configuration
- Scan existing worlds in the genre for reference

### 4. Initialize WIP

Create `{wipFile}`:
```yaml
---
mode: '{mode}'
surprise: {true | false}    # Surprise Mode flag from step 1 selection
genre: '{genre}'
world: '{world}'
created: '{date}'
status: 'in-progress'
stepsCompleted: [1]
concept: '{brief concept description}'
---
```

When `surprise: true`, later steps skip their HALT approval gates but still run all deterministic safety checks. World-builder reads the `surprise` field at the start of every step and routes accordingly.

### 5. Mode-Based Routing

| Mode | Next Step |
|------|-----------|
| New Genre | step-02-riff |
| New World | step-02-riff |
| Asset Management | step-07-validate (skip to validation) |
| DM Prep | step-06-generate (skip to generation) |
| Playtest | step-08-playtest (skip to end) |

Present the routing decision and **continue to the appropriate step**.
