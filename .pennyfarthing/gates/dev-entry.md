<gate name="dev-entry" model="haiku">

<purpose>
Entry gate for DEV phase. Forces a full audit of existing source files
before writing any implementation code. Catches silent failures, security
vulnerabilities, and type design issues that pre-date the current story.
</purpose>

<check name="silent-failure-audit">
Do not proceed with any implementation until you have read EVERY source file
(not tests) and listed all issues found with file:line references.

For each function, check:

1. **Error swallowing** — functions that hide failures behind defaults:
   - `unwrap_or_default()` on Results that could fail for multiple reasons
   - `unwrap_or(fallback)` where the fallback masks real errors
   - `ok()` that converts errors to None, discarding the error type
   - `match` arms with `_ => default` that catch errors meant to propagate
   - Functions that catch ALL errors (e.g. any IO error) when they should
     only catch specific ones (e.g. NotFound) and propagate the rest

2. **Empty error handling**:
   - Empty `catch` / `except` blocks
   - `if let Err(_) = ...` with no body or just a log
   - `.map_err(|_| ...)` that discards the original error context

3. **Silent fallbacks**:
   - Functions named `*_or_default` / `from_file_or_default` that return
     a default value on ANY error, not just "not found"
   - Config loaders that silently use defaults when the file is corrupt
   - Retry logic that eventually returns a default instead of failing
</check>

<check name="security-audit">
1. **Injection risks**:
   - Raw `String` used where a newtype should enforce invariants
     (HTTP headers, file paths, SQL, shell commands)
   - User input concatenated into structured formats without escaping

2. **Secret handling**:
   - Config fields that accept secrets but silently ignore them
   - Tokens/credentials left on disk after use
   - Error messages that include secret values (CWE-209)

3. **Auth/access**:
   - Permission checks that can be bypassed
   - Default-open access patterns
</check>

<check name="type-design-audit">
1. **Stringly-typed APIs** — String parameters that should be enums or newtypes
2. **Unsafe casts** — numeric conversions without bounds checking
3. **Weak invariants** — public fields that should be validated on construction
</check>

<pass>
List every issue found across all checks, then return:

```yaml
GATE_RESULT:
  status: pass
  gate: dev-entry
  message: "Audit complete: {N} pre-existing source issues found"
  findings:
    - file: "{source_file}"
      line: {line}
      issue: "{description}"
      category: "silent-failure | security | type-design"
      severity: "critical | high | medium"
```

Do not proceed with implementation until all critical and high findings are fixed.
Fix medium findings if they touch the same files as story work.
</pass>

<fail>
If source files cannot be read:

```yaml
GATE_RESULT:
  status: fail
  gate: dev-entry
  message: "Cannot audit: {reason}"
  recovery:
    - "{action to unblock}"
```
</fail>

</gate>
