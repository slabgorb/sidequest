# Step 8: Browse Additional Themes (Optional)

<purpose>
Show the user the full catalog of available themes beyond the base set. All themes ship with the pf CLI — no additional installation needed.
</purpose>

<instructions>
1. Explain that all themes are included with pf
2. Show theme categories and counts
3. Let user browse and preview themes
4. Confirm or change the selected theme from step 7
</instructions>

<output>
- User informed about full theme catalog
- Theme confirmed (or changed after browsing)
- User knows how to switch themes later
</output>

## THEME CATALOG

All themes ship with the `pf` CLI and are available immediately — no extra packages or install steps needed.

```bash
# List all available themes
pf theme list
```

### Theme Categories

| Category | Themes | Examples |
|----------|--------|----------|
| Sci-Fi | ~8 | Dune, Star Trek, Firefly, Fifth Element |
| Literary | ~15 | Dickens, Shakespeare, Austen, Sherlock Holmes |
| Prestige TV | ~17 | Breaking Bad, The Wire, Mad Men, Succession |
| Comedy | ~9 | The Office, Parks & Rec, Futurama, Ted Lasso |
| Realistic | ~14 | Renaissance masters, jazz legends, composers |
| Mythology & Fantasy | ~4 | Greek, Norse, His Dark Materials |
| Superheroes | ~4 | Marvel MCU, Avatar: The Last Airbender |

## BROWSING

```bash
# Preview a specific theme
pf theme show dune

# Set a different theme
pf theme set breaking-bad
```

## CHANGING LATER

```
You can switch themes anytime:

  pf theme list            - See all available themes
  pf theme show <name>     - Preview a theme's characters
  pf theme set <name>      - Switch to a different theme
```

## SUCCESS CRITERIA

- User has browsed available themes
- Theme selection confirmed
- User knows how to switch later

## NEXT STEP

After theme browsing, proceed to `step-09-jira.md` to configure the Jira project key.

<switch tool="AskUserQuestion">
  <case value="browse-themes" next="LOOP">
    Browse more themes
  </case>
  <case value="continue" next="step-09-jira">
    Continue with current theme
  </case>
</switch>
