# Step 9: Configure Jira Project (Optional)

<purpose>
Ask the user which Jira project key their work tracks against and persist it to config. This allows `pf jira` commands to target the correct project without environment variables.
</purpose>

<instructions>
1. Ask the user for their Jira project key
2. Optionally ask for a custom Jira URL if not using the default
3. Save to config via `pf settings set`
4. Verify the setting was persisted
</instructions>

<output>
- Jira project key saved to config (or skipped)
- User knows how to change it later
</output>

## JIRA PROJECT CONFIGURATION

```
🔗 Jira Project Configuration
═══════════════════════════════

Pennyfarthing integrates with Jira for sprint and story management.
If your team uses Jira, configure the project key so CLI commands
target the right board.

What is your Jira project key?
(This is the prefix on your tickets, e.g. BMAD, PROJ, ENG)

[1] Enter project key
[2] Skip - I don't use Jira
```

### If User Provides a Key

Ask the user for their project key, then save it:

```bash
pf settings set jira.project <KEY>
```

### Jira URL

```
What is your Jira Cloud URL?
Example: https://your-org.atlassian.net

[1] Enter URL
[2] Skip (configure later)
```

```bash
pf settings set jira.url https://your-org.atlassian.net
```

## VERIFICATION

```bash
pf settings show
```

Expected:
```
jira:
  project: BMAD
```

## CHANGING LATER

```
You can update your Jira project anytime:

  pf settings set jira.project NEWKEY
  pf settings set jira.url https://other.atlassian.net

Environment variables JIRA_PROJECT and JIRA_URL also work
but config.local.yaml takes priority.
```

## SUCCESS CRITERIA

- Jira project key saved to config (or user explicitly skipped)
- User knows how to change it later via `pf settings set`

## NEXT STEP

After Jira configuration, proceed to `step-10-gui.md` to optionally configure the Frame GUI.
