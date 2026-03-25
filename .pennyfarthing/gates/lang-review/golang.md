<gate name="golang-review-checklist" model="haiku">

<purpose>
Go-specific self-review checklist for dev agent before handoff.
Catches recurring review findings that go vet and staticcheck miss.
Targets patterns that compile and pass vet but produce runtime bugs,
security vulnerabilities, or maintenance issues.
</purpose>

<pass>
Scan all files changed in this PR (`git diff --name-only develop...HEAD`)
that end in `.go`. For each file, check the following rules.

**1. Silent error swallowing**
Search for these patterns in changed lines:
- `_ = err` or `err = fn(); _ = err` — explicitly discarding errors
- Return values ignored: `fn()` where fn returns `(T, error)` — must capture both
- `if err != nil { return nil }` — swallows error, caller gets nil with no explanation
- `log.Println(err)` without returning or propagating — error logged but execution continues
- `recover()` in defer without re-panicking or logging — swallows panics silently

For each match, check if the error path involves user input or I/O.
If so, the error MUST be propagated to the caller.

**2. Error wrapping and context**
- `return err` without wrapping — loses call-site context. Use `fmt.Errorf("context: %w", err)`
- `errors.New()` when wrapping an existing error — use `%w` verb to preserve chain
- `fmt.Errorf("...: %v", err)` — uses `%v` not `%w`, breaks `errors.Is()`/`errors.As()`
- Sentinel errors (`var ErrNotFound = errors.New(...)`) without `errors.Is()` checks
- Custom error types without `Error()` and `Unwrap()` methods

**3. Goroutine and concurrency safety**
- Goroutine launched without `sync.WaitGroup` or channel for completion tracking
- Shared variable accessed from goroutine without mutex or channel
- `go func() { ... }()` capturing loop variable — use `go func(v T) { ... }(v)`
  (fixed in Go 1.22+ with `GOEXPERIMENT=loopvar`, but check go.mod version)
- Channel without buffer size consideration — unbuffered blocks sender
- `select {}` without `default` or timeout — blocks forever if no case fires
- Missing `context.Context` propagation in goroutine chains
- `sync.Mutex` embedded in struct that gets copied — mutex copy bug

**4. Resource leaks**
- `http.Get()`/`http.Post()` without `defer resp.Body.Close()` — connection leak
- `resp.Body.Close()` without checking `resp != nil` first — nil deref on error
- `os.Open()`/`os.Create()` without `defer f.Close()` — file handle leak
- `sql.Open()` without `defer db.Close()` and `db.Ping()` verification
- `context.WithCancel()`/`WithTimeout()` without `defer cancel()` — context leak
- `bufio.Scanner` on large input without `scanner.Buffer()` size limit

**5. Nil safety**
- Method call on potentially nil receiver — no nil check before method call
- Nil pointer dereference after type assertion: `v := m["key"].(Type)` — panics if key missing
  Use comma-ok: `v, ok := m["key"].(Type)`
- Nil slice vs empty slice: `var s []T` (nil) vs `s := []T{}` (empty) — JSON marshals differently
- `len(slice)` check without nil check — `len(nil)` is 0 (safe), but nil and empty may have
  different semantics in your domain

**6. HTTP and API patterns**
- `http.ListenAndServe()` without timeouts — slowloris attack (CWE-400)
  Use `http.Server{ReadTimeout, WriteTimeout, IdleTimeout}`
- Handler not setting Content-Type — browser MIME sniffing (CWE-16)
- Missing `X-Content-Type-Options: nosniff` header
- User input in `http.Redirect()` URL — open redirect (CWE-601)
- `json.NewDecoder(r.Body).Decode()` without `MaxBytesReader` — memory exhaustion
- `io.ReadAll(r.Body)` on untrusted input without size limit — OOM (CWE-400)

**7. SQL and database**
- String concatenation in SQL queries — injection (CWE-89)
  Use `db.Query("SELECT ... WHERE id = $1", id)`
- `rows.Close()` not deferred immediately after `db.Query()` — leaked rows
- Missing `rows.Err()` check after iteration — silent iteration errors
- `sql.NullString` etc. not used for nullable columns — scan fails

**8. Test quality**
Search test files (`*_test.go`) for:
- `t.Log()` as only assertion — test never fails
- Table-driven tests without `t.Run()` subtests — poor failure identification
- `reflect.DeepEqual` on structs with unexported fields — always false
- Missing `t.Helper()` on test helper functions — wrong file/line in failures
- `t.Parallel()` with shared mutable state — race condition in tests
- Test fixtures without `t.Cleanup()` or `defer` cleanup

**9. Package and API design**
- Exported function without doc comment — godoc gap
- Returning concrete types instead of interfaces — tight coupling
- `init()` functions with side effects — test pollution, import order dependency
- Package-level variables that are mutable — concurrent access bugs
- `interface{}` / `any` in public APIs without documentation of expected types
- Accepting `*os.File` when `io.Reader`/`io.Writer` suffices — over-specified

**10. Security: input validation at boundaries**
At HTTP handlers, gRPC methods, and CLI commands:
- User input MUST be validated (length, type, range) before use
- File paths from user input MUST use `filepath.Clean()` + prefix check (CWE-22)
- `os/exec.Command()` with user input in args — use allowlist, never shell interpolation
- `template.HTML()` on user input — bypasses escaping (CWE-79)
  Use `text/template` or `html/template` with auto-escaping
- Regex on user input without `regexp.Compile` timeout consideration

**11. Module and dependency hygiene**
Check `go.mod` and `go.sum`:
- `replace` directives that should not be committed (local development paths)
- Indirect dependencies with known CVEs — run `govulncheck`
- Missing `go.sum` entries for new imports
- `go` directive version mismatch with CI/deployment Go version
- Vendor directory out of sync if using vendoring

**12. Struct and interface patterns**
- Large structs passed by value — use pointer receiver/parameter
- Struct with both pointer and value receivers — inconsistent method set
- Embedded struct with exported fields in unexported type — leaks API
- `sync.Mutex` as struct field without pointer — copied on assignment
- Interface with too many methods (>5) — consider splitting

**13. Fix-introduced regressions (meta-check)**
After applying fixes for review findings, re-scan the fix diff against
checks #1-#12. Common patterns:
- Adding error handling with `_ = err` instead of propagating
- Adding defer but in wrong scope (inside loop — deferred until func exit)
- Adding context but not cancelling it (context leak)

If ALL checks pass across all changed `.go` files, return:

```yaml
GATE_RESULT:
  status: pass
  gate: golang-review-checklist
  message: "Go self-review checklist passed (13 checks)"
  checks:
    - name: silent-errors
      status: pass
      detail: "No ignored errors or swallowed panics"
    - name: error-wrapping
      status: pass
      detail: "Errors wrapped with context using %w verb"
    - name: concurrency
      status: pass
      detail: "Goroutines tracked; no shared state without sync"
    - name: resource-leaks
      status: pass
      detail: "All resources have defer Close(); contexts cancelled"
    - name: nil-safety
      status: pass
      detail: "Nil checks before method calls; comma-ok on assertions"
    - name: http-api
      status: pass
      detail: "Server timeouts set; input size limited; headers correct"
    - name: sql-database
      status: pass
      detail: "Parameterized queries; rows closed; errors checked"
    - name: test-quality
      status: pass
      detail: "Subtests used; helpers marked; no shared mutable state"
    - name: package-design
      status: pass
      detail: "Exported types documented; interfaces preferred; no mutable globals"
    - name: input-validation
      status: pass
      detail: "User input validated at all boundaries"
    - name: module-hygiene
      status: pass
      detail: "No local replace directives; go.sum in sync"
    - name: struct-interface
      status: pass
      detail: "Consistent receivers; no mutex copy; reasonable interface size"
    - name: fix-regressions
      status: pass
      detail: "Fix commits re-scanned against checks #1-#12"
```
</pass>

<fail>
List each violation with file, line, and the specific pattern matched:

```yaml
GATE_RESULT:
  status: fail
  gate: golang-review-checklist
  message: "Found {N} Go review issues"
  checks:
    - name: silent-errors
      status: pass | fail
      detail: "{file}:{line}: error ignored from {function}()"
    - name: error-wrapping
      status: pass | fail
      detail: "{file}:{line}: return err without wrapping / %v instead of %w"
    - name: concurrency
      status: pass | fail
      detail: "{file}:{line}: goroutine without WaitGroup / shared var without mutex"
    - name: resource-leaks
      status: pass | fail
      detail: "{file}:{line}: {resource} opened without defer Close()"
    - name: nil-safety
      status: pass | fail
      detail: "{file}:{line}: method call on potentially nil {type}"
    - name: http-api
      status: pass | fail
      detail: "{file}:{line}: no server timeouts / no MaxBytesReader"
    - name: sql-database
      status: pass | fail
      detail: "{file}:{line}: string concatenation in SQL / missing rows.Err()"
    - name: test-quality
      status: pass | fail
      detail: "{file}:{line}: no assertions / missing t.Helper() / race in parallel test"
    - name: package-design
      status: pass | fail
      detail: "{file}:{line}: exported {name} without doc comment / mutable package var"
    - name: input-validation
      status: pass | fail
      detail: "{file}:{line}: unvalidated user input in {context}"
    - name: module-hygiene
      status: pass | fail
      detail: "go.mod: local replace directive / go version mismatch"
    - name: struct-interface
      status: pass | fail
      detail: "{file}:{line}: mixed receivers on {Type} / large struct by value"
    - name: fix-regressions
      status: pass | fail
      detail: "{file}:{line}: fix introduces same class of bug (check #{N})"
  recovery:
    - "Capture and propagate all errors; use fmt.Errorf with %w for wrapping"
    - "Add sync.WaitGroup or channels for goroutine tracking"
    - "Add defer Close() immediately after resource acquisition"
    - "Add nil checks before method calls; use comma-ok for type assertions"
    - "Set ReadTimeout, WriteTimeout, IdleTimeout on http.Server"
    - "Use parameterized queries; defer rows.Close(); check rows.Err()"
    - "Add t.Run() subtests; mark helpers with t.Helper(); use t.Cleanup()"
    - "Add doc comments to exported types; return interfaces, accept interfaces"
    - "Validate user input at handlers; use filepath.Clean() on paths"
    - "Remove local replace directives; run govulncheck"
    - "Use pointer receivers consistently; don't embed sync.Mutex without pointer"
    - "Re-scan fix diffs against checks #1-#12 before handoff"
```
</fail>

</gate>
