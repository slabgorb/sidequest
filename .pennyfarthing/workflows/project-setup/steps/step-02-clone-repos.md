# Step 2: Clone Subrepos (Optional)

<purpose>
Allow users to clone subrepos to set up or complete an orchestrator pattern. This step enables real-time repo cloning during project setup.
</purpose>

<instructions>
1. Analyze discovery results for missing subrepos
2. Check .gitignore for expected but missing repos
3. Offer to clone missing repos or add new ones
4. Update .gitignore with new repo patterns
5. Re-scan after cloning to update discovery
</instructions>

<output>
- Subrepos cloned as needed
- .gitignore updated with new patterns
- Discovery data refreshed with new repos
- User ready to proceed to repos.yaml generation
</output>

## ORCHESTRATOR PATTERN SETUP

### Detecting Missing Subrepos

From step 1, we may have found:
- Patterns in .gitignore that don't have corresponding directories
- A sprint/ directory but no subrepos
- An incomplete orchestrator setup

```
⚠️  Orchestrator Pattern Detected - Missing Subrepos

Expected (from .gitignore):
  ❌ conductor-api/     (not found)
  ❌ conductor-ui/      (not found)

Found:
  ✓ sprint/            (orchestrator confirmed)
  ✓ .pennyfarthing/    (framework installed)
```

### Clone Options Menu

```
📦 Subrepo Setup
════════════════

This appears to be an orchestrator project. Would you like to:

(switch prompt presents cloning options)
    - conductor-api from git@github.com:org/conductor-api.git
    - conductor-ui from git@github.com:org/conductor-ui.git
```

### Clone Workflow

Based on user selection:

#### 1. Gather Repository Information

```
🔗 Clone Subrepo
════════════════

Repository URL: {user enters URL}
  Example: git@github.com:org/project-api.git
  Example: https://github.com/org/project-ui.git

Local directory name: {auto-detect or user enters}
  Suggested: {project}-api (from URL)

Branch to clone: {default: main or develop}
  [Enter] for default, or specify branch
```

#### 2. Execute Clone

```bash
# Clone the repository
git clone {url} {directory_name}

# Optionally checkout specific branch
cd {directory_name} && git checkout {branch}
```

#### 3. Update .gitignore

After successful clone, offer to update .gitignore:

```
✓ Cloned {repo_name} to {directory}/

Add to .gitignore? [Y/n]
```

If yes, append:
```gitignore
# Subrepo - clone separately
{directory_name}/
```

#### 4. Detect Repo Type

After cloning, analyze the new repo:

```
📊 Analyzing {directory_name}...

Detected:
  Type: api
  Language: TypeScript
  Framework: Express
  Test command: npm test
  Build command: npm run build

Is this correct? [Y/n/e]
```

### Setting Up New Orchestrator

If no orchestrator pattern exists but user wants one:

```
🏗️  Create Orchestrator Pattern
═══════════════════════════════

This will set up your project as an orchestrator:

1. Create sprint/ directory structure
2. Create .session/ for work tracking
3. Add Pennyfarthing workflow support

Subrepos to include:
  [ ] Add API repo
  [ ] Add UI repo
  [ ] Add other repo

(switch prompt presents options)
```

### Common Orchestrator Patterns

Offer templates based on project type:

```
📋 Orchestrator Templates
═════════════════════════

[1] API + UI (most common)
    - {project}-api/ (backend)
    - {project}-ui/ (frontend)

[2] API + UI + Shared (monorepo-like)
    - {project}-api/
    - {project}-ui/
    - {project}-shared/

[3] Microservices
    - {project}-gateway/
    - {project}-service-a/
    - {project}-service-b/

[4] Custom - define your own repos
```

## RE-SCAN AFTER CHANGES

After any cloning or setup:

```bash
# Re-run discovery
find . -name ".git" -type d -maxdepth 3

# Update tech stack detection
# (runs same detection as step 1)
```

Present updated discovery:

```
📁 Updated Project Structure
════════════════════════════

Repositories:
┌────────────────┬──────────┬────────────┐
│ Path           │ Type     │ Status     │
├────────────────┼──────────┼────────────┤
│ .              │ orch     │ existing   │
│ conductor-api/ │ api      │ ✓ cloned   │
│ conductor-ui/  │ ui       │ ✓ cloned   │
└────────────────┴──────────┴────────────┘

(switch prompt presents options)
```

## SUCCESS CRITERIA

✅ All desired subrepos cloned
✅ .gitignore properly updated
✅ Discovery data refreshed
✅ Repo types correctly identified
✅ User ready to proceed

## NEXT STEP

After repos are cloned and discovery is refreshed, proceed to `step-03-repos-yaml.md` to generate the repos.yaml configuration.

<switch tool="AskUserQuestion">
  <case value="continue-to-reposyaml-generation" next="step-03-repos-yaml">
    Continue to repos.yaml generation
  </case>
  <case value="add-another-repo" next="LOOP">
    Add another repo
  </case>
  <case value="remove-a-repo-from-tracking" next="LOOP">
    Remove a repo from tracking
  </case>
</switch>
