---
description: Manage persona themes - list, show, set, create, or interactive wizard
args: "[list|show|set|create|maker] [options]"
---

# Theme Management

<purpose>
Manage persona themes: list available themes, view details, switch themes, create custom themes, and run the interactive AI-driven theme wizard.
</purpose>

## Commands

### `/theme` or `/theme show [name]`

Show current theme or specific theme details.

```bash
pf theme show [name]

# Show extended details (OCEAN scores, quirks, catchphrases)
pf theme show [name] --full
```

### `/theme list`

List all available themes with current theme highlighted.

```bash
pf theme list
```

Output shows current theme marked with `*` and tier brackets: `[S]` elite, `[A]` excellent, `[B]` strong, `[C]` good, `[D]` below average, `[U]` unbenchmarked.

### `/theme set <name>`

Set the active persona theme.

```bash
pf theme set <name>
```

After setting, refresh the current agent's persona:
```bash
pf agent start "sm"
```

### `/theme create <name> [--base <theme>] [--user]`

Create a new custom theme by copying from a base.

```bash
# Create from default base (minimalist)
pf theme create my-theme

# Create from specific base
pf theme create my-theme --base blade-runner

# Create as user-level theme (available across all projects)
pf theme create my-theme --user
```

### `/theme maker`

Interactive wizard for AI-driven theme creation. Supports three modes:

| Mode | Description |
|------|-------------|
| AI-Driven | Describe a concept, AI generates all 10 agent personas |
| Guided | AI suggests characters per agent, you pick |
| Manual | You specify character, style, and quote for each agent |

## Quick Reference

| Command | Action |
|---------|--------|
| `/theme` | Show current theme |
| `/theme list` | List all themes |
| `/theme show blade-runner` | Show specific theme |
| `/theme show blade-runner --full` | Extended details |
| `/theme set discworld` | Switch to theme |
| `/theme create my-theme` | Create from base |
| `/theme maker` | Interactive wizard |

## Related

| Skill | Purpose |
|-------|---------|
| `/theme` | Full skill with maker wizard details |

<reference>
- **Skill:** `.claude/skills/theme/skill.md`
- **CLI:** `pf theme [list|show|set|create]`
- **Config:** `.pennyfarthing/config.local.yaml`
</reference>
