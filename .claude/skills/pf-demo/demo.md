---
name: demo
description: |
  Generate demo artifacts for completed stories. Use when creating demo scripts,
  summaries, or presentation materials from story session data.
args: "[generate] <story-id> [--dry-run] [--corrections TEXT]"
---

# /pf-demo - Demo Artifact Generator

<run>
Main commands:
- `pf demo generate <story-id>` - Generate demo artifacts for a completed story
- `pf demo generate <story-id> --dry-run` - Preview what would be generated
- `pf demo generate <story-id> --corrections "feedback"` - Regenerate with developer feedback
</run>

<output>
- `generate` outputs the directory path where artifacts were written, plus a list of generated files
- `--dry-run` outputs the target directory without writing files
- Warnings are printed for missing or incomplete session data
</output>

## Commands

### `/pf-demo generate <story-id>`

Generate demo artifacts (narrative, demo script, metadata, diagrams) for a completed story.

**Run:**
```bash
pf demo generate <story-id>
```

<args>
| Arg | Required | Description |
|-----|----------|-------------|
| `story-id` | Yes | Story identifier (e.g., `42-1`) |
| `--dry-run` | No | Preview without writing files |
| `--corrections` | No | Developer feedback for regeneration |
</args>

<example>
pf demo generate 42-1
# Generated demo artifacts in: sprint/demos/42-1/
# Files generated (3):
#   sprint/demos/42-1/narrative.md
#   sprint/demos/42-1/demo-script.md
#   sprint/demos/42-1/metadata.yaml
</example>

---

### `/pf-demo generate <story-id> --dry-run`

Preview what would be generated without writing any files.

**Run:**
```bash
pf demo generate <story-id> --dry-run
```

<example>
pf demo generate 42-1 --dry-run
# Dry run — would generate to: sprint/demos/42-1/
</example>

---

### `/pf-demo generate <story-id> --corrections "feedback"`

Regenerate artifacts with developer feedback to refine the output.

**Run:**
```bash
pf demo generate <story-id> --corrections "Focus more on the API changes"
```

<example>
pf demo generate 42-1 --corrections "Emphasize the new WebSocket endpoint"
# Generated demo artifacts in: sprint/demos/42-1/
# Files generated (3):
#   sprint/demos/42-1/narrative.md
#   sprint/demos/42-1/demo-script.md
#   sprint/demos/42-1/metadata.yaml
</example>
