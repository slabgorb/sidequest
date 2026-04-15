# Sprint CLI — Detailed Usage

## Top-Level Commands

### `pf.sh sprint active`

Show which sprint is currently active for this user.

### `pf.sh sprint archive`

Archive a completed story.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `STORY_ID` | Yes | Story ID to archive |
| `PR_NUMBER` | No | Optional PR number if merged via PR |
| `--apply` | No | Also remove from current-sprint.yaml |
| `--dry-run` | No | Show what would be done without making changes |

### `pf.sh sprint backlog`

Show available stories grouped by epic.

### `pf.sh sprint check`

Check story/epic availability. Returns JSON.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `ID` | Yes | Story ID, epic ID, or 'next' for highest priority |

### `pf.sh sprint data`

Output canonical merged sprint data as JSON.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `--json` | No | Output as JSON (required) |

### `pf.sh sprint findings`

Show aggregated findings for a sprint.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `SPRINT_NUMBER` | No |  |
| `--format` | No | Output format (default: markdown). |

### `pf.sh sprint future`

Show future work initiatives and epics.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `EPIC_ID` | No | Optional epic ID to show detailed stories (e.g., epic-55) |

### `pf.sh sprint info`

Output sprint info as JSON.

### `pf.sh sprint list`

Show all registered sprints from the sprint registry.

### `pf.sh sprint metrics`

Display sprint metrics and progress.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `--json` | No | Output in JSON format |

### `pf.sh sprint new`

Initialize a new sprint.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `SPRINT_YYWW` | Yes | Sprint identifier in YYWW format (e.g., 2607) |
| `JIRA_ID` | Yes | Jira sprint ID number (e.g., 278) |
| `START_DATE` | Yes | Sprint start date YYYY-MM-DD |
| `END_DATE` | Yes | Sprint end date YYYY-MM-DD |
| `GOAL` | Yes | Sprint goal (quoted string) |
| `--dry-run` | No | Show what would be done without making changes |

### `pf.sh sprint status`

Show sprint status.

### `pf.sh sprint use`

Switch the active sprint (per-user preference).

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `NAME` | Yes | Sprint name from the registry, or "default" to clear |

### `pf.sh sprint validate`

Validate sprint YAML for syntax, schema, and format issues.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `FILE` | No |  |
| `--fix` | No | Automatically repair format issues |

### `pf.sh sprint work`

Start work on a story.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `STORY_ID` | No | Story ID to work on, or 'next' for highest priority |
| `--dry-run` | No | Show what would be done without making changes |

---

## Epic Commands

### `pf.sh sprint epic archive`

Archive completed epics.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `EPIC_ID` | No | Epic ID to archive (omit to scan all completed epics) |
| `--dry-run` | No | Show what would be done without making changes |
| `--jira` | No | Also update Jira epic status to Done |

### `pf.sh sprint epic cancel`

Cancel an epic and all its stories.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `EPIC_ID` | Yes | Epic ID (e.g., epic-42 or <PROJECT-KEY>) |
| `--jira` | No | Also cancel the epic in Jira |
| `--dry-run` | No | Show what would be done without making changes |

### `pf.sh sprint epic field`

Get a field value from an epic.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `EPIC_ID` | Yes | Epic ID (e.g., epic-79 or 79) |
| `FIELD_NAME` | Yes | Field to extract (e.g., jira, title, status) |

### `pf.sh sprint epic import`

Import BMAD epics-and-stories output to future.yaml.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `EPICS_FILE` | Yes | Path to markdown file from epics-and-stories workflow |
| `INITIATIVE_NAME` | No | Name for the initiative (optional, extracted from file) |
| `--marker` | No | Marker tag for stories (default: imported) |
| `--dry-run` | No | Show what would be done without making changes |

### `pf.sh sprint epic promote`

Move an epic from future initiatives to current-sprint.yaml.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `EPIC_ID` | Yes | Epic ID (e.g., epic-41 or 41) |
| `--dry-run` | No | Show what would be done without making changes |

### `pf.sh sprint epic reindex`

Adopt an orphaned shard file into the sprint index.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `SHARD_REF` | Yes | Shard reference (e.g., 129, <PROJECT-KEY>) |
| `--dry-run` | No | Preview adoption without writing |
| `--sprint-file` | No | Path to sprint YAML file |

### `pf.sh sprint epic remove`

Remove an epic from future.yaml (for cancelled pre-Jira epics).

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `EPIC_ID` | Yes | Epic ID to remove (e.g., epic-41) |
| `--dry-run` | No | Show what would be removed without making changes |

### `pf.sh sprint epic show`

Show details for a specific epic.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `EPIC_ID` | Yes | Epic ID (e.g., epic-42 or <PROJECT-KEY>) |
| `--json` | No | Output as JSON |

### `pf.sh sprint epic update`

Update an epic's fields by ID.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `EPIC_ID` | Yes | Epic ID (e.g., 103, epic-103, or <PROJECT-KEY>) |
| `--status` | No | New epic status |
| `--priority` | No | New priority (e.g., P0, P1) |
| `--title` | No | New epic title |
| `--jira` | No | Jira epic key (may trigger shard rename) |
| `--description` | No | Epic description text |
| `--repos` | No | Target repo(s) |
| `--dry-run` | No | Show changes without writing |
| `--sprint-file` | No | Path to sprint YAML file |

---

## Initiative Commands

### `pf.sh sprint initiative cancel`

Cancel an initiative and all its epics/stories.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `NAME` | Yes | Initiative slug (e.g., benchmark-reliability, technical-debt) |
| `--jira` | No | Also cancel epics in Jira |
| `--dry-run` | No | Show what would be done without making changes |

### `pf.sh sprint initiative show`

Show details for a specific initiative.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `NAME` | Yes | Initiative slug (e.g., benchmark-reliability, technical-debt) |
| `--json` | No | Output as JSON |

---

## Standalone Commands

### `pf.sh sprint standalone add`

Add a standalone story to current sprint tracking.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `JIRA_KEY` | Yes |  |
| `TITLE` | Yes |  |
| `POINTS` | Yes |  |
| `--status` | No | Story status (default: done) |
| `--repos` | No | Target repo (default: pennyfarthing) |
| `--pr` | No | PR number |
| `--branch` | No | Branch name |
| `--sprint-file` | No | Path to sprint YAML file |
| `--dry-run` | No | Show what would be done without making |

---

## Story Commands

### `pf.sh sprint story claim`

Claim or unclaim a story in Jira.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `STORY_ID` | Yes | Story ID / Jira key to claim |
| `--dry-run` | No | Show what would be done without making changes |

### `pf.sh sprint story field`

Get a field value from a story.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `STORY_ID` | Yes | Story ID (e.g., 79-1 or <PROJECT-KEY>) |
| `FIELD_NAME` | Yes | Field to extract (e.g., workflow, status, points) |

### `pf.sh sprint story finish`

Complete a story: archive session, merge PR, transition Jira, update sprint YAML.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `STORY_ID` | Yes | Story ID (e.g., 83-2) |
| `--dry-run` | No | Show what would be done without executing |

### `pf.sh sprint story remove`

Remove a story from the sprint YAML.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `STORY_ID` | Yes | Story ID (e.g., 76-4, td-1, <PROJECT-KEY>) |
| `--dry-run` | No | Preview removal without writing |
| `--sprint-file` | No | Path to sprint YAML file |

### `pf.sh sprint story show`

Show details for a specific story.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `STORY_ID` | Yes | Story ID (e.g., <PROJECT-KEY> or 67-1) |
| `--json` | No | Output as JSON |

### `pf.sh sprint story size`

Display story sizing guidelines.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `POINTS` | No | Optional specific point value to show guidance for |

### `pf.sh sprint story template`

Display story templates by type.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `TEMPLATE_TYPE` | No |  |

