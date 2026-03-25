# Step 3: Hook Configuration

<step-meta>
step: 3
name: hooks
workflow: installation-check
agent: devops
gate: true
next: step-04-scripts
</step-meta>

<purpose>
Verify all 9 hook configurations in settings.local.json. Hooks are the runtime integration between Pennyfarthing and Claude Code — each one controls a critical behavior. This is the most complex and consequential category, which is why it has a gate.
</purpose>

<prerequisites>
- settings.local.json exists (verified in step 2)
- User understands that hooks are registered in `.claude/settings.local.json`
</prerequisites>

<instructions>
1. Run the doctor command for the hooks category
2. For each of the 9 hook checks, explain what it does, why it matters, and the impact of it being missing:

   **SessionStart hooks:**
   - **session-start-hook**: Exports `PROJECT_ROOT` env var. Without it, agents can't find project files. The most critical hook.
   - **otel-auto-start**: Starts Frame server and configures 5 OTEL env vars for telemetry. Legacy `.sh` version only sets 2 of 5 vars.
   - **auto-load-sm**: Auto-invokes `/sm` agent on new sessions. Without it, users must manually run `/sm` every time.

   **Stop hooks:**
   - **stop-hook**: Runs reflector-check to enforce UI markers at turn end. Without it, Frame GUI QuickActions won't render.

   **PostToolUse hooks:**
   - **post-tool-use-hook**: Bell mode — injects queued messages via `additionalContext`. Without it, `/bell` messages are lost.
   - **sprint-yaml-validation**: Validates sprint YAML after edits. Without it, malformed YAML breaks SprintPanel.

   **PreToolUse hooks:**
   - **context-circuit-breaker**: Auto-saves session when context exceeds threshold. Without it, long sessions lose work.
   - **schema-validation**: Validates XML schema on Write to session/skill/step files. Without it, malformed files slip through.

   **Permissions:**
   - **benchmark-permissions**: `Bash(claude:*)` needed for parallel benchmarks. Without it, only sequential runs work.

3. For each warning/failure, explain the specific impact and offer targeted fix
4. Present gate criteria for user approval

**IMPORTANT:** Modifying settings.local.json affects all Claude Code sessions. Explain this to the user before applying fixes.
</instructions>

<actions>
- Run: `pf validate --json --category hooks`
- Read: `.claude/settings.local.json` to show current hook configuration
</actions>

<output>
Present results grouped by hook type:

```markdown
## Hook Configuration Results

### SessionStart Hooks
| Hook | Status | Detail |
|------|--------|--------|
| session-start | ... | ... |
| otel-auto-start | ... | ... |
| auto-load-sm | ... | ... |

### Stop Hooks
| Hook | Status | Detail |
|------|--------|--------|
| reflector-check | ... | ... |

### PostToolUse Hooks
| Hook | Status | Detail |
|------|--------|--------|
| bell-mode | ... | ... |
| sprint-yaml | ... | ... |

### PreToolUse Hooks
| Hook | Status | Detail |
|------|--------|--------|
| context-circuit-breaker | ... | ... |
| schema-validation | ... | ... |

### Permissions
| Check | Status | Detail |
|-------|--------|--------|
| benchmark-permissions | ... | ... |
```
</output>

<gate>
## Completion Criteria
- [ ] All 9 hook checks reviewed with user
- [ ] User understands what each hook controls
- [ ] Any fixes to settings.local.json approved by user
- [ ] User confirmed hook configuration is acceptable
</gate>

<switch tool="AskUserQuestion">
  <case value="fix" next="LOOP">
    Fix — Run `pf validate --fix --category hooks` to add missing hooks
  </case>
  <case value="explain" next="LOOP">
    Explain — Deep dive on a specific hook's behavior
  </case>
  <case value="continue" next="step-04-scripts">
    Continue — Approve configuration and proceed to Scripts check
  </case>
  <case value="recheck" next="LOOP">
    Recheck — Re-run after manual edits to settings.local.json
  </case>
</switch>

<next-step>
After user approves hook configuration, proceed to step-04-scripts.md for Hook Scripts verification.
</next-step>

## Failure Modes

- Applying fixes without understanding what each hook does
- Not realizing settings.local.json changes affect all sessions
- Skipping gate without reviewing critical hooks (session-start, context-circuit-breaker)

## Success Metrics

- All 9 hooks configured or user made informed decision to skip
- User understands the relationship between hooks and features
- Gate approval recorded
