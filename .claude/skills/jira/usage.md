# Jira CLI — Detailed Usage

## Top-Level Commands

### `pf.sh jira assign`

Assign issue to a user (email or GitHub username).

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `KEY` | Yes |  |
| `USER` | Yes |  |
| `--dry-run` | No | Preview without applying |

### `pf.sh jira bidirectional`

Bidirectional sync between YAML and Jira.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `--dry-run` | No | Preview without applying |
| `--yaml-wins` | No | Prefer YAML values on conflict |
| `--status` | No | Sync status field |
| `--points` | No | Sync story points |
| `--assignee` | No | Sync assignee field (Jira -> YAML only) |
| `--all` | No | Sync all fields |
| `--sprint` | No | Target specific sprint |

### `pf.sh jira check`

Check if a story is available to claim.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `KEY` | Yes |  |

### `pf.sh jira claim`

Claim a story (assign to self + move to In Progress).

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `KEY` | Yes |  |
| `--dry-run` | No | Show what would be done without making changes |

### `pf.sh jira link`

Link two Jira issues.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `PARENT_KEY` | Yes |  |
| `CHILD_KEY` | Yes |  |
| `LINK_TYPE` | No |  |
| `--dry-run` | No | Preview without applying |

### `pf.sh jira move`

Transition a Jira issue to a new status.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `KEY` | Yes |  |
| `STATUS` | Yes |  |
| `--dry-run` | No | Preview without applying |

### `pf.sh jira reconcile`

Reconciliation report: sprint YAML vs Jira.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `--fix` | No | Apply automatic fixes where safe |

### `pf.sh jira search`

Search issues using plain text or JQL.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `QUERY` | Yes |  |
| `-p, --project` | No | Jira project key (default: from config) |
| `-n, --max-results` | No | Maximum results (default: 50) |
| `-s, --status` | No | Filter by status (e.g. 'In Progress', 'Done') |
| `-t, --type` | No | Filter by issue type (e.g. Story, Epic, Bug) |
| `--json-output, --json` | No | Output as JSON |

### `pf.sh jira sync`

Sync epic stories from sprint YAML to Jira.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `EPIC` | Yes |  |
| `--dry-run` | No | Preview without applying |
| `--transition` | No | Sync status to Jira |
| `--points` | No | Sync story points |
| `--all` | No | Sync all fields |

### `pf.sh jira view`

View issue details (delegates to jira CLI).

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `KEY` | Yes |  |

---

## Create Commands

### `pf.sh jira create epic`

Create a Jira epic and its child stories from sprint YAML.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `EPIC_ID` | Yes |  |
| `--dry-run` | No | Preview without creating |

### `pf.sh jira create standalone`

Create a standalone Jira story, add to sprint, mark Done.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `TITLE` | Yes | Story summary |
| `--points` | No | Story points (default: 2) |
| `-d, --description` | No | Story description |
| `--dry-run` | No | Preview without creating |

### `pf.sh jira create story`

Create a single Jira story under an epic from sprint YAML.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `EPIC_JIRA_KEY` | Yes |  |
| `STORY_ID` | Yes |  |
| `--dry-run` | No | Preview without creating |

---

## Sprint Commands

### `pf.sh jira sprint add`

Add an issue to a sprint.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `SPRINT_ID` | Yes |  |
| `ISSUE_KEY` | Yes |  |
| `--dry-run` | No | Show what would be done without making changes |

