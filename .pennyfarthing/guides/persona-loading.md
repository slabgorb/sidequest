# Persona Loading (For Command Files)

This block is included in command files to pre-load the agent's persona before the agent file is read.

## Usage in Command Files

Add this block BEFORE `<agent-activation>`:

```markdown
<persona-loading agent="{agent-name}">
Load this agent's persona before activation:
1. Read `.pennyfarthing/config.local.yaml`
2. Get `theme` value (e.g., "discworld")
3. Read `pennyfarthing-dist/personas/themes/{theme}.yaml` (or `.pennyfarthing/personas/themes/`)
4. Extract `agents.{agent-name}` section (character, style, helper, etc.)
5. Apply `attributes` from config (verbosity, formality, humor, emoji_use)
6. Store resolved persona for use during session
</persona-loading>
```

## What Gets Resolved

From theme file (`agents.{agent-name}`):
- `character` - The persona name (e.g., "Captain Carrot")
- `style` - Communication style
- `expertise` - Domain expertise
- `helper` - Helper name and style
- `emoji` - Default emoji

From config (`attributes`):
- `verbosity` - low | medium | high
- `formality` - formal | casual | playful
- `humor` - enabled | disabled | subtle
- `emoji_use` - none | minimal | frequent

## Agent File Reference

After persona loading, the agent file just needs:

```markdown
## Persona

**Fallback:** {brief description if config unavailable}
```

The agent receives the resolved persona from the command file's loading step.
