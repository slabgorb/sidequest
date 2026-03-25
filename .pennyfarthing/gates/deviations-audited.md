<gate name="deviations-audited" model="haiku">

<purpose>
Verify the Reviewer audited all Design Deviations before approval.
Every TEA and Dev deviation entry must be stamped ACCEPTED or FLAGGED.
Undocumented deviations found by the reviewer should be logged under `### Reviewer (audit)`.

Used by: reviewer exit (before approval verdict).
</purpose>

<arguments>
| Argument | Required | Description |
|----------|----------|-------------|
| `SESSION_FILE` | Yes | Path to session file |
</arguments>

<pass>
1. Count deviation entries from TEA and Dev sections (lines starting with `- **`).
2. Count entries stamped with `→ ✓ ACCEPTED` or `→ ✗ FLAGGED`.
3. If stamped count >= entry count, all deviations are audited.
4. If TEA/Dev wrote "No deviations from spec." — that counts as zero entries to audit (auto-pass).

```yaml
GATE_RESULT:
  status: pass
  gate: deviations-audited
  message: "All {N} design deviations audited by Reviewer"
  checks:
    - name: deviations-audited
      status: pass
      detail: "{accepted} accepted, {flagged} flagged, {undocumented} undocumented additions"
```
</pass>

<fail>
If any deviation entry lacks an ACCEPTED or FLAGGED stamp:

```yaml
GATE_RESULT:
  status: fail
  gate: deviations-audited
  message: "{N} design deviations not yet audited"
  checks:
    - name: deviations-audited
      status: fail
      detail: "Unstamped deviations: {list of unstamped entries}"
  recovery:
    - "Review each entry in '## Design Deviations' and stamp ACCEPTED or FLAGGED"
    - "Add any undocumented deviations under '### Reviewer (audit)'"
```
</fail>

</gate>
