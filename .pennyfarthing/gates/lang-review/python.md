<gate name="python-review-checklist" model="haiku">

<purpose>
Python-specific self-review checklist for dev agent before handoff.
Catches recurring review findings that automated tools (ruff, mypy) miss.
Each check targets a class of bug that survives linting but fails in production.
</purpose>

<pass>
Scan all files changed in this PR (`git diff --name-only develop...HEAD`)
that end in `.py`. For each file, check the following rules.

**1. Silent exception swallowing**
Search for these patterns in changed lines:
- `except:` (bare except) — must catch specific exceptions
- `except Exception: pass` or `except Exception as e: pass` — swallows all errors silently
- `except Exception:` with only a `logger.debug()` — error-level events logged at debug
- `try/except` around a single line where the exception type is known — catch specifically
- `suppress()` from contextlib without a comment explaining why suppression is safe

For each match, check if the error path is user-controlled (API input,
file I/O, network calls). If so, it MUST be handled explicitly.

**2. Mutable default arguments**
Search function/method definitions for mutable defaults:
- `def f(items=[])` — use `items=None` with `items = items or []` inside
- `def f(data={})` — use `data=None` with `data = data or {}` inside
- `def f(seen=set())` — same pattern
- Class-level mutable attributes shared across instances (list/dict/set as class var)

**3. Type annotation gaps at boundaries**
At module boundaries (public functions, class `__init__`, API handlers):
- Parameters MUST have type annotations
- Return types MUST be annotated
- `Any` is acceptable only with a comment explaining why
- `# type: ignore` must have a specific error code: `# type: ignore[override]`

Internal/private helpers are exempt.

**4. Logging: coverage AND correctness**
For any module that imports `logging` or `structlog`:
- Error paths MUST have `logger.error()` or `logger.warning()`
- `logger.exception()` must only appear inside `except` blocks
- **Log level classification:** Client errors (4xx) use `warning`, server
  errors (5xx) use `error`. User input validation failures are `info` not `error`.
- Never log sensitive data: passwords, tokens, API keys, PII
- f-strings in log calls: prefer `logger.info("msg %s", var)` over `logger.info(f"msg {var}")`
  for lazy evaluation and structured logging compatibility

**5. Path handling**
Search for string-based path manipulation:
- `os.path.join()` is acceptable but `pathlib.Path` is preferred for new code
- String concatenation for paths (`dir + "/" + file`) — use `Path / file`
- Hardcoded `/` separators — breaks on Windows
- `open()` without `encoding=` parameter — defaults vary by platform (CWE-838)
- Missing `Path.resolve()` before security checks — symlink traversal (CWE-59)

**6. Test quality**
Search test files for:
- `assert True` or `assert not False` — vacuously true
- `assert result` without checking specific value — truthy check misses wrong values
- `mock.patch` on the wrong target (patching where defined, not where used)
- Tests with no assertions (just calling a function)
- `@pytest.mark.skip` without a reason or linked issue
- Parametrized tests where all cases test the same code path
- Missing `conftest.py` fixtures that cause test isolation failures

**7. Resource leaks**
Search for resource usage without context managers:
- `open()` without `with` — file handle leak
- `requests.get()`/`post()` without `with Session()` — connection pool leak
- `sqlite3.connect()` without `with` — database connection leak
- `threading.Lock().acquire()` without `with lock:` — deadlock risk
- `tempfile.NamedTemporaryFile(delete=False)` without cleanup in `finally`

**8. Unsafe deserialization**
Search for deserialization of untrusted input:
- `pickle.loads()` / `pickle.load()` — arbitrary code execution (CWE-502)
- `yaml.load()` without `Loader=SafeLoader` — arbitrary code execution
- `eval()` / `exec()` on any external input — code injection (CWE-94)
- `subprocess` with `shell=True` and interpolated strings — command injection (CWE-78)
- `json.loads()` without schema validation on user input — trusting structure

**9. Async/await pitfalls**
For async code:
- `asyncio.sleep(0)` without comment — usually indicates a workaround
- Blocking calls (`time.sleep`, `requests.get`, file I/O) inside async functions
  — use `aiohttp`, `aiofiles`, or `asyncio.to_thread()`
- `asyncio.gather()` without `return_exceptions=True` — one failure cancels all
- Missing `await` on coroutines (returns coroutine object, never executes)
- `async for` / `async with` in sync context — silent failure

**10. Import hygiene**
- Star imports (`from module import *`) — pollutes namespace, hides dependencies
- Circular imports — check if new imports create cycles
- Runtime imports that should be `TYPE_CHECKING` only (used only in annotations)
- Missing `__all__` on public modules — unclear public API

**11. Security: input validation at boundaries**
At API handlers, CLI entry points, and file parsers:
- User input MUST be validated before use (length, type, range)
- SQL queries MUST use parameterized queries, never f-strings (CWE-89)
- HTML output MUST be escaped (CWE-79)
- File paths from user input MUST be resolved and checked against allowed dirs (CWE-22)
- `re.compile()` on user input without `re.DOTALL` timeout consideration (ReDoS)

**12. Dependency hygiene**
Check `requirements.txt`, `pyproject.toml`, or `setup.cfg`:
- Unpinned dependencies (`requests` instead of `requests>=2.28,<3`)
- Test-only dependencies in main requirements (pytest, faker, factory-boy)
- Deprecated packages (use `httpx` over `requests` in async code)

**13. Fix-introduced regressions (meta-check)**
After applying fixes for review findings, re-scan the fix diff against
checks #1-#12. Common patterns:
- Adding error handling but catching too broadly
- Adding type annotations with incorrect types
- Adding validation but only on one code path

If ALL checks pass across all changed `.py` files, return:

```yaml
GATE_RESULT:
  status: pass
  gate: python-review-checklist
  message: "Python self-review checklist passed (13 checks)"
  checks:
    - name: silent-exceptions
      status: pass
      detail: "No bare except, swallowed exceptions, or misleveled logging"
    - name: mutable-defaults
      status: pass
      detail: "No mutable default arguments in function signatures"
    - name: type-annotations
      status: pass
      detail: "Public interfaces have type annotations"
    - name: logging
      status: pass
      detail: "Error paths have logging with correct severity levels"
    - name: path-handling
      status: pass
      detail: "Path operations use pathlib or os.path correctly"
    - name: test-quality
      status: pass
      detail: "No vacuous assertions, mock target errors, or missing assertions"
    - name: resource-leaks
      status: pass
      detail: "Resources use context managers"
    - name: unsafe-deserialization
      status: pass
      detail: "No pickle/eval/unsafe yaml on untrusted input"
    - name: async-pitfalls
      status: pass
      detail: "No blocking calls in async, no missing awaits"
    - name: import-hygiene
      status: pass
      detail: "No star imports, circular imports, or missing __all__"
    - name: input-validation
      status: pass
      detail: "User input validated at all boundaries"
    - name: dependency-hygiene
      status: pass
      detail: "Dependencies pinned, test deps separated"
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
  gate: python-review-checklist
  message: "Found {N} Python review issues"
  checks:
    - name: silent-exceptions
      status: pass | fail
      detail: "{file}:{line}: bare except / swallowed {exception_type}"
    - name: mutable-defaults
      status: pass | fail
      detail: "{file}:{line}: mutable default {type} in {function}()"
    - name: type-annotations
      status: pass | fail
      detail: "{file}:{line}: {function}() missing return type annotation"
    - name: logging
      status: pass | fail
      detail: "{file}:{line}: error path without logging / wrong level"
    - name: path-handling
      status: pass | fail
      detail: "{file}:{line}: string path concatenation / missing encoding"
    - name: test-quality
      status: pass | fail
      detail: "{file}:{line}: vacuous assertion / mock patch on wrong target"
    - name: resource-leaks
      status: pass | fail
      detail: "{file}:{line}: {resource} opened without context manager"
    - name: unsafe-deserialization
      status: pass | fail
      detail: "{file}:{line}: {function}() on untrusted input"
    - name: async-pitfalls
      status: pass | fail
      detail: "{file}:{line}: blocking {call}() inside async function"
    - name: import-hygiene
      status: pass | fail
      detail: "{file}:{line}: star import / circular import detected"
    - name: input-validation
      status: pass | fail
      detail: "{file}:{line}: unvalidated user input in {context}"
    - name: dependency-hygiene
      status: pass | fail
      detail: "{file}: {dep} unpinned / test dep in main requirements"
    - name: fix-regressions
      status: pass | fail
      detail: "{file}:{line}: fix introduces same class of bug (check #{N})"
  recovery:
    - "Replace bare except with specific exception types"
    - "Use None defaults with conditional initialization inside function body"
    - "Add type annotations to public function signatures and return types"
    - "Add logging to error paths; use warning for client errors, error for server errors"
    - "Use pathlib.Path for path operations; add encoding= to open()"
    - "Replace vacuous assertions with specific value checks"
    - "Wrap resource acquisition in with statements"
    - "Replace pickle/eval with safe alternatives (json, yaml.safe_load)"
    - "Move blocking calls to asyncio.to_thread() or use async equivalents"
    - "Replace star imports with explicit imports; add __all__ to public modules"
    - "Add input validation at API handlers and CLI entry points"
    - "Pin dependencies; move test-only deps to dev/test requirements"
    - "Re-scan fix diffs against checks #1-#12 before handoff"
```
</fail>

</gate>
