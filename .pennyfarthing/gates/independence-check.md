<gate name="independence-check" model="haiku">

<purpose>
Verify that batch work units have no shared files before fan-out.
Prevents concurrent modification — the worst failure mode of parallel execution.

Runs between the decompose and fan-out phases of the batch workflow.
The architect produces unit definitions with file boundaries during decompose;
this gate validates those boundaries are independent.
</purpose>

<pass>
Run the independence check with the architect's unit definitions:

```bash
pf preflight independence --units '<unit_definitions_json>'
```

**Input format:** JSON with unit file lists from the decompose phase:
```json
{
  "units": [
    {"id": "1", "files": ["src/a.ts", "src/b.ts"], "description": "Component A-B"},
    {"id": "2", "files": ["src/c.ts", "src/d.ts"], "description": "Component C-D"}
  ]
}
```

If exit code 0 (independent), return:

```yaml
GATE_RESULT:
  status: pass
  gate: independence-check
  message: "All {N} units are independent. {M} files, zero overlaps."
  checks:
    - name: file-overlap
      status: pass
      detail: "{N} units, {M} files, no shared files"
```
</pass>

<fail>
If exit code 1 (overlaps found), return:

```yaml
GATE_RESULT:
  status: fail
  gate: independence-check
  message: "{K} file(s) shared across units. Re-decompose or confirm override."
  checks:
    - name: file-overlap
      status: fail
      detail: "Overlapping files: {file_list}"
  overlaps:
    - file: "src/b.ts"
      units: ["1", "3"]
  recovery:
    - "Re-decompose: ask Architect to split overlapping files into a single unit"
    - "Override: developer confirms overlap is acceptable (e.g., read-only imports)"
    - "Merge units: combine overlapping units into one sequential unit"
```

**Developer override:** If the developer inspects the overlaps and confirms they
are acceptable (e.g., files are only read, not written), they may override by
approving the manual gate. The gate blocks by default — override is explicit.
</fail>

</gate>
