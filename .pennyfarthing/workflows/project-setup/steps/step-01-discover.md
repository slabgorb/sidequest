# Step 1: Project Discovery

<purpose>
Discover the project structure, detect repositories, identify tech stack, and gather information needed to configure Pennyfarthing.
</purpose>

<instructions>
1. Scan project root for repository structure
2. Detect package managers and languages
3. Identify monorepo vs single-repo structure
4. Find test/build/lint commands
5. Present discovery summary for user confirmation
</instructions>

<output>
- Project structure map
- Detected repositories with paths
- Tech stack (languages, frameworks, package managers)
- Extracted commands (test, build, lint)
- User-confirmed discovery ready for repos.yaml generation
</output>

## PRE-FLIGHT: Environment Check

Before discovery, verify `pf` is installed:

```bash
pf --version
```

**If not found**, install via pipx: `pipx install pennyfarthing-scripts` (or from local source for dev).

---

## DISCOVERY TASKS

### 1. Detect Repository Structure

Scan for git repositories and orchestrator patterns:

```bash
# Find all .git directories (indicates repos)
find . -name ".git" -type d -maxdepth 3 2>/dev/null

# Check if this is a monorepo
ls -la pnpm-workspace.yaml lerna.json turborepo.json package.json 2>/dev/null

# Check for orchestrator pattern (sprint/, .session/ directories)
ls -la sprint/ .session/ 2>/dev/null

# Check .gitignore for ignored subrepo patterns
grep -E "^[a-zA-Z].*-api/?$|^[a-zA-Z].*-ui/?$|^[a-zA-Z]+/$" .gitignore 2>/dev/null
```

**Classify structure:**
- **Single repo**: Only `./.git` exists, no sprint/
- **Monorepo**: Workspace config found (pnpm-workspace.yaml, lerna.json, etc.)
- **Orchestrator**: Has sprint/ and/or multiple `.git` directories (subrepos)

### 1a. Detect Orchestrator Pattern (Critical)

The orchestrator pattern uses gitignored subrepos:

```
my-project/                    # Orchestrator (git repo)
├── .gitignore                 # Contains: my-project-api/, my-project-ui/
├── sprint/                    # Sprint tracking (key indicator)
├── .session/                  # Work sessions
├── my-project-api/            # Subrepo (separate git, gitignored)
│   └── .git/
└── my-project-ui/             # Subrepo (separate git, gitignored)
    └── .git/
```

**Detection steps:**
1. Check for `sprint/` directory → indicates orchestrator
2. Parse `.gitignore` for directory patterns (ending in `/`)
3. Check if those directories exist AND have their own `.git`
4. These are subrepos, not just ignored directories

**Example .gitignore patterns to look for:**
```gitignore
# Subrepos (cloned separately)
conductor-api/
conductor-ui/

# OR with wildcards
*-api/
*-ui/
```

**Important:** Subrepos may not exist yet (not cloned). The .gitignore tells us what SHOULD be there.

### 2. Detect Tech Stack

For each repository/directory, check for:

| File | Indicates | Extract |
|------|-----------|---------|
| `package.json` | Node.js/JavaScript/TypeScript | name, scripts, dependencies |
| `Cargo.toml` | Rust | name, version |
| `pyproject.toml` / `requirements.txt` | Python | name, dependencies |
| `go.mod` | Go | module name |
| `pom.xml` / `build.gradle` | Java | project info |
| `tsconfig.json` | TypeScript | compiler options |

### 3. Extract Commands

From `package.json` scripts or equivalent:

```yaml
test_command: npm test | pnpm test | cargo test | pytest
build_command: npm run build | cargo build | python setup.py build
lint_command: npm run lint | cargo clippy | ruff check
dev_command: npm run dev | cargo watch
```

### 4. Identify Project Type

Based on discovery, classify:

| Type | Indicators |
|------|------------|
| `api` | Express, FastAPI, Gin, Actix endpoints |
| `ui` | React, Vue, Svelte, frontend frameworks |
| `cli` | bin entry in package.json, main.rs with clap |
| `library` | exports, no bin entry |
| `orchestrator` | sprint/, .session/, multiple subrepos |
| `framework` | distributable content, templates |

### 5. Present Discovery Summary

```
📁 Project Discovery Summary
════════════════════════════

Project Name: {detected_name}
Structure: {single|monorepo|orchestrator}

Repositories Found:
┌────────────────┬──────────┬────────────┬─────────────────┐
│ Path           │ Type     │ Language   │ Framework       │
├────────────────┼──────────┼────────────┼─────────────────┤
│ .              │ {type}   │ {lang}     │ {framework}     │
│ packages/api   │ api      │ TypeScript │ Express         │
│ packages/ui    │ ui       │ TypeScript │ React           │
└────────────────┴──────────┴────────────┴─────────────────┘

Detected Commands:
  test:  {test_command}
  build: {build_command}
  lint:  {lint_command}

(switch prompt presents options)
```

## SUCCESS CRITERIA

✅ All git repositories detected
✅ Tech stack accurately identified
✅ Commands extracted from package files
✅ Project type classified
✅ User confirms discovery is accurate

<switch tool="AskUserQuestion">
  <case value="confirm-and-continue-to-reposyaml-generation" next="step-02-clone-repos">
    Confirm and continue to repos.yaml generation
  </case>
  <case value="edit" next="LOOP">
    Edit — let me provide corrections
  </case>
  <case value="rescan-with-different-parameters" next="LOOP">
    Rescan with different parameters
  </case>
</switch>
