<gate name="sm-setup-exit" model="haiku">

<purpose>
Verify SM has completed story setup before handing off to the next agent.
Without a properly configured session file, the next agent cannot function.

Checks: session exists, fields set, epic context validated, story context
validated, branch created. Context checks use a cascade pattern — validate
first, report actionable recovery on failure.
</purpose>

<pass>
Run these checks in order. Extract the epic number {N} and story ID {N-N}
from the story ID in the session file.

1. **session-exists:** Check `.session/{story-id}-session.md` exists.
   ```bash
   ls .session/{story-id}-session.md
   ```

2. **session-fields-set:** Read session file and verify:
   - `**Workflow:**` field present and non-empty
   - `**Phase:**` field present and set to `setup`

3. **epic-context-validated:** Validate epic context document.
   ```bash
   pf validate context-epic {N}
   ```
   - Exit 0: PASS — epic context exists and is valid
   - Exit 2 (not found): FAIL — file `sprint/context/context-epic-{N}.md` missing
   - Exit 1 (invalid): FAIL — report validation errors from stdout

   **Fallback** (if `pf validate context` is not available): check that
   `sprint/context/context-epic-{N}.md` exists and is non-empty.

4. **story-context-validated:** Validate story context document.
   ```bash
   pf validate context-story {N-N}
   ```
   - Exit 0: PASS — story context exists and is valid
   - Exit 2 (not found): FAIL — file `sprint/context/context-story-{N-N}.md` missing
   - Exit 1 (invalid): FAIL — report validation errors from stdout

   **Fallback** (if `pf validate context` is not available): check that
   `sprint/context/context-story-{N-N}.md` exists. If no story context file
   exists, check that the session file contains an SM Assessment section
   with technical approach — this is acceptable for stories without
   dedicated context files.

5. **branch-created:** For each repo in session `**Repos:**`:
   - Run `git branch --show-current`
   - Confirm not on `main` or `develop`

If ALL pass, return:

```yaml
GATE_RESULT:
  status: pass
  gate: sm-setup-exit
  message: "Session {story-id} ready. Workflow: {workflow}, Branch: {branch}"
  checks:
    - name: session-exists
      status: pass
      detail: ".session/{story-id}-session.md exists"
    - name: session-fields-set
      status: pass
      detail: "Workflow: {workflow}, Phase: setup"
    - name: epic-context-validated
      status: pass
      detail: "sprint/context/context-epic-{N}.md valid"
    - name: story-context-validated
      status: pass
      detail: "sprint/context/context-story-{N-N}.md valid (or SM Assessment present)"
    - name: branch-created
      status: pass
      detail: "Branch {branch} created in {repos}"
```
</pass>

<fail>
If ANY check fails, report all results:

```yaml
GATE_RESULT:
  status: fail
  gate: sm-setup-exit
  message: "Setup incomplete: {summary}"
  checks:
    - name: session-exists
      status: pass | fail
      detail: "{exists or missing}"
    - name: session-fields-set
      status: pass | fail
      detail: "{fields present or missing fields list}"
    - name: epic-context-validated
      status: pass | fail
      detail: "{valid, missing, or validation errors}"
    - name: story-context-validated
      status: pass | fail
      detail: "{valid, missing, or validation errors}"
    - name: branch-created
      status: pass | fail
      detail: "{branch status per repo}"
  recovery:
    - "Run sm-setup to create session file"
    - "Set Workflow and Phase fields in session"
    - "Run `/pf-context create epic {N}` to create epic context"
    - "Run `/pf-context create story {N-N}` to create story context"
    - "Create feature branch: git checkout -b feat/{story-slug}"
```
</fail>

</gate>
