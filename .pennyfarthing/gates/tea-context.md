<gate name="tea-context" model="haiku">

<purpose>
Verify story context exists and is valid before TEA begins RED phase.
This is a fail-only gate — no creation trigger. If context is missing,
SM setup didn't complete properly. SM's gate handles auto-creation;
TEA's gate only enforces that the result exists.

Story: 131-3 (TEA Context Gate and Agent Integration)
Epic: 131 (Gate-Enforced Context Pipeline)
</purpose>

<pass>
Extract the story ID {N-N} from the session file. Parse the epic number {N}
from the story ID (e.g., story "131-3" → epic "131").

1. **story-context-validated:** Validate story context document.
   ```bash
   pf validate context-story {N-N}
   ```
   - Exit 0: PASS — story context exists and is valid
   - Exit 2 (not found): FAIL — file `sprint/context/context-story-{N-N}.md` missing
   - Exit 1 (invalid): FAIL — report validation errors from stdout

   **Fallback** (if `pf validate context` is not available): check that
   `sprint/context/context-story-{N-N}.md` exists and is non-empty.

If ALL pass, return:

```yaml
GATE_RESULT:
  status: pass
  gate: tea-context
  message: "Story context validated for {N-N}"
  checks:
    - name: story-context-validated
      status: pass
      detail: "sprint/context/context-story-{N-N}.md valid"
```
</pass>

<fail>
If ANY check fails, return:

```yaml
GATE_RESULT:
  status: fail
  gate: tea-context
  message: "Story context not found or invalid"
  checks:
    - name: story-context-validated
      status: fail
      detail: "{missing or validation errors}"
  recovery:
    - "Ensure SM setup completed successfully"
    - "Run `/pf-context create story {N-N}` manually if needed"
```

**Note:** TEA does NOT auto-trigger context creation. If story context is
missing at this point, the SM setup gate or recovery pipeline failed.
Report the issue and stop.
</fail>

</gate>
