# Step 7: Configure Persona Theme

<purpose>
Select and configure a persona theme for the project's AI agents. Themes provide character-based personas that make interactions more engaging and memorable.
</purpose>

<instructions>
1. List available themes
2. Suggest themes based on project type
3. Allow user to browse/preview themes
4. Configure selected theme
5. Update config.local.yaml
</instructions>

<output>
- Theme selected and configured
- config.local.yaml updated
- Theme previewed with sample agent
- User satisfied with selection
</output>

## THEME SELECTION

### List Available Themes

```bash
ls -la .pennyfarthing/personas/themes/
```

### Theme Categories

| Category | Examples | Best For |
|----------|----------|----------|
| **Sci-Fi** | dune, star-trek, firefly | Tech-heavy projects |
| **Fantasy** | tolkien, discworld | Creative projects |
| **Historical** | victorian, renaissance | Enterprise/formal |
| **Pop Culture** | office, parks-rec | Team-oriented |
| **Literature** | sherlock, austen | Analysis-heavy |
| **Mythology** | norse, greek | Framework/infra |

### Theme Suggestions Based on Project Type

```
🎭 Theme Suggestions
════════════════════

Based on your project type ({project_type}), here are recommended themes:

{if api_project}
  🚀 Sci-Fi themes work well for backend development:
    - dune (infrastructure, long-term planning)
    - star-trek (exploration, problem-solving)
    - firefly (scrappy, get-things-done)
{/if}

{if ui_project}
  🎨 Creative themes suit frontend work:
    - studio-ghibli (visual, artistic)
    - pixar (user-focused, storytelling)
    - marvel (dynamic, action-oriented)
{/if}

{if enterprise}
  🏛️ Professional themes for enterprise:
    - victorian (formal, structured)
    - mad-men (business, strategy)
    - west-wing (politics, stakeholders)
{/if}

{if framework}
  ⚔️ Epic themes for infrastructure:
    - tolkien (world-building, architecture)
    - dune (ecology, systems thinking)
    - norse (reliability, strength)
{/if}
```

## THEME PREVIEW

Show sample personas from selected theme:

```
🎭 Theme Preview: dune
═══════════════════════

Characters:
┌─────────────┬────────────────────────────────┬──────────────────────────────────┐
│ Agent       │ Character                      │ Style                            │
├─────────────┼────────────────────────────────┼──────────────────────────────────┤
│ sm          │ Stilgar                        │ Tribal leader, decisive          │
│ tea         │ Thufir Hawat                   │ Mentat, analytical               │
│ dev         │ Reverend Mother Mohiam         │ Precise, powerful                │
│ reviewer    │ Leto II (God Emperor)          │ Long-view, uncompromising        │
│ architect   │ Paul Atreides (Muad'Dib)       │ Visionary, strategic             │
│ pm          │ Lady Jessica                   │ Diplomatic, influential          │
│ devops      │ Planetologist Pardot Kynes     │ Ecological, systems thinker      │
└─────────────┴────────────────────────────────┴──────────────────────────────────┘

User title: "Cousin"

Sample interaction:
  Stilgar: "The water of your code flows strong today, Cousin. Let us see what
           the sietch requires of us in this sprint."

(switch prompt presents theme selection options)
```

## CONFIGURATION

### Update config.local.yaml

```bash
pf theme set dune
```

This updates `.pennyfarthing/config.local.yaml` with the selected theme.

### Theme Activation

After selection:

```
✓ Theme 'dune' selected

Updated files:
  - .pennyfarthing/config.local.yaml

To see your new personas in action:
  - Run any agent command (e.g., /sm, /dev)
  - Agents will now use Dune character personas

To change themes later:
  - /theme list    - see available themes
  - /theme set X   - switch to theme X
  - /theme show    - see current theme details
```

## INTERACTIVE FLOW

```
🎭 Theme Configuration
═══════════════════════

Current theme: {current_theme or "default (none)"}

Options:
[1] Recommended themes (based on project)
[2] Browse all themes by category
[3] Search themes by keyword
[4] Preview a specific theme
[5] Keep current / use default
[6] Create custom theme

> 1

Recommended for {project_type}:

[a] dune - Infrastructure & systems thinking
    "Plans changes across centuries"

[b] star-trek - Exploration & problem-solving
    "Boldly solving bugs no one has solved before"

[c] firefly - Scrappy & pragmatic
    "Keep flying, keep coding"

[d] Show more recommendations

> a

{preview dune theme}

(switch prompt presents selection options)
```

## SUCCESS CRITERIA

✅ Theme selected (or explicitly chose default)
✅ config.local.yaml updated
✅ User previewed theme and is satisfied
✅ Theme ready for agent use

## NEXT STEP

After theme is configured, proceed to `step-08-theme-packs.md` to optionally install additional theme packs.

<switch tool="AskUserQuestion">
  <case value="select-dune" next="LOOP">
    Select 'dune'
  </case>
  <case value="preview-another" next="LOOP">
    Preview another
  </case>
  <case value="back-to-options" next="LOOP">
    Back to options
  </case>
</switch>
