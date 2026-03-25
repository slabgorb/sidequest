# Theme — Examples

## Browsing Themes

```bash
# List all available themes with tiers
pf theme list

# Show current theme
pf theme show

# Show specific theme
pf theme show blade-runner

# Show full details (OCEAN, quirks, catchphrases)
pf theme show blade-runner --full
pf theme show fifth-element --full
```

## Changing Theme

```bash
# Set theme
pf theme set blade-runner

# Preview without changing
pf theme set blade-runner --dry-run

# Refresh agent persona after change
pf agent start "sm"
```

## Creating Custom Themes

```bash
# Create from current theme
pf theme create my-team

# Create from specific base
pf theme create my-team --base blade-runner

# Create as user-level (available across projects)
pf theme create my-team --user

# Create from specific base as user-level
pf theme create my-team --base fifth-element --user

# Preview
pf theme create my-team --base blade-runner --dry-run
```

After creation:
1. Edit the theme file to customize agents
2. Run `pf theme set my-team` to activate

## Theme Maker (Interactive)

Use `/theme maker` in Claude Code. The wizard walks through:

1. **Name** — lowercase, hyphens allowed (e.g., `my-universe`)
2. **Mode** — AI-Driven, Guided, or Manual
3. **Characters** — 10 agent personas generated

### AI-Driven Mode
Describe a concept or universe, all 10 personas generated automatically.

### Guided Mode
Describe a universe, get 3-4 character suggestions per agent, pick your favorites.

### Manual Mode
Specify character name, style, and quote for each agent. Skip agents for defaults.

### After Creation
```bash
# Activate the new theme
pf theme set my-universe

# Generate portraits (optional, requires GPU)
./scripts/generate-portraits.sh --theme my-universe
./scripts/generate-portraits.sh --theme my-universe --dry-run
./scripts/generate-portraits.sh --theme my-universe --role dev
```

## Theme Name Rules

- Lowercase letters and numbers only
- Must start with a letter
- Hyphens allowed (no underscores or spaces)
- No conflicts with existing themes

Valid: `blade-runner`, `my-team-2`, `scifi`
Invalid: `Blade_Runner`, `my team`, `2fast`
