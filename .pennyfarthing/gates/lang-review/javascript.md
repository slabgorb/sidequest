<gate name="javascript-review-checklist" model="haiku">

<purpose>
JavaScript-specific self-review checklist for dev agent before handoff.
Catches recurring review findings that ESLint misses.
Targets runtime bugs, security issues, and patterns that fail in production
despite passing lint.
</purpose>

<pass>
Scan all files changed in this PR (`git diff --name-only develop...HEAD`)
that end in `.js`, `.mjs`, or `.cjs`. For each file, check the following rules.

**1. Silent error swallowing**
Search for these patterns in changed lines:
- `catch (e) {}` or `catch (e) { /* empty */ }` — swallows errors silently
- `.catch(() => {})` — promise error silently consumed
- `.catch(() => null)` — error replaced with falsy value, caller can't distinguish
- `try/catch` with only `console.log(e)` — error logged but not propagated or handled
- `JSON.parse()` without try/catch — throws on malformed input

**2. Promise and async pitfalls**
- Missing `await` on async function calls — returns Promise object, not value
- `async` function without any `await` — unnecessary async wrapper
- `.then()` chains mixing with `async/await` in same function — pick one style
- `Promise.all()` without error handling — one rejection rejects all
- Floating promises: async call without `await`, `.then()`, or `.catch()`
- `forEach` with async callback — does not await iterations, use `for...of`

**3. Prototype pollution and object safety**
- `Object.assign(target, userInput)` — pollutes target with `__proto__` (CWE-1321)
- Bracket notation with user input: `obj[userInput]` — prototype access
- `JSON.parse()` result used directly without property validation
- Missing `Object.create(null)` or `Map` for user-keyed lookups
- Spread operator on user input into security-sensitive objects

**4. Equality and type coercion**
- `==` or `!=` instead of `===` / `!==` — implicit coercion bugs
- `if (value)` on numbers (0 is falsy) or strings ("" is falsy) — use explicit checks
- `typeof x === "object"` without null check — `typeof null === "object"`
- Array checks: `typeof arr === "object"` — use `Array.isArray()`

**5. DOM and browser security (if applicable)**
- `innerHTML =` with user input — XSS (CWE-79)
- `document.write()` — XSS and performance issues
- `eval()` / `Function()` constructor with user input — code injection (CWE-94)
- `window.location` assignment from user input — open redirect (CWE-601)
- Missing `Content-Security-Policy` headers in server responses

**6. Node.js specific**
- `require()` with variable paths — code injection risk
- `child_process.exec()` with string interpolation — command injection (CWE-78)
  Use `execFile()` or `spawn()` with array args instead
- `fs.readFile()` without encoding — returns Buffer, not string
- `process.env.SECRET` logged or included in error responses
- `Buffer.from(userInput)` without encoding parameter — defaults to UTF-8,
  may truncate binary data

**7. Regex safety**
- User input in `new RegExp()` without escaping — ReDoS (CWE-1333)
- Catastrophic backtracking patterns: `(a+)+`, `(a|a)*`, `(.*a){n}`
- Missing `^` and `$` anchors on validation regexes — partial match passes
- `g` flag on regex used in `test()` — stateful lastIndex causes alternating results

**8. Test quality**
Search test files for:
- `expect(result).toBeTruthy()` — truthy check misses wrong values
- `expect(fn).not.toThrow()` — vacuous without first testing it can throw
- `.mockReturnValue()` without `.toHaveBeenCalled()` — mock may never execute
- `jest.spyOn()` without `.mockRestore()` in afterEach — test pollution
- `.only` or `.skip` without a reason — forgotten debug markers
- Snapshot tests on large objects — brittle, any change breaks

**9. Module and scope issues**
- `var` instead of `const`/`let` — hoisting bugs
- `const` on values that are reassigned — will throw at runtime
- Exports from files that have side effects on import — import order matters
- Circular dependencies between modules — undefined at import time

**10. Error handling patterns**
- Throwing strings instead of Error objects — no stack trace
- `new Error()` without message — unhelpful stack traces
- Error subclasses without `super(message)` — loses message
- `catch (e) { throw e }` — pointless catch, removes nothing
- Custom error types without `name` property — poor debugging

**11. Security: input validation**
At API handlers, middleware, and user-facing functions:
- User input MUST be validated (length, type, pattern)
- SQL in string templates — use parameterized queries (CWE-89)
- Path traversal: `path.join(base, userInput)` without `path.resolve()` + prefix check (CWE-22)
- HTTP header injection: `\r\n` in header values from user input (CWE-113)
- SSRF: user-controlled URLs passed to `fetch()`/`http.get()` without allowlist (CWE-918)

**12. Dependency and config hygiene**
- `console.log` in production code (not wrapped in NODE_ENV check)
- Hardcoded secrets, API keys, or connection strings
- `devDependencies` in `dependencies` — ships test tools to production
- Missing `engines` field in package.json for Node.js version requirements

**13. Fix-introduced regressions (meta-check)**
After applying fixes for review findings, re-scan the fix diff against
checks #1-#12. Common patterns:
- Adding error handling with empty catch blocks
- Adding validation but only on one code path
- Fixing one XSS vector while introducing another

If ALL checks pass across all changed `.js`/`.mjs`/`.cjs` files, return:

```yaml
GATE_RESULT:
  status: pass
  gate: javascript-review-checklist
  message: "JavaScript self-review checklist passed (13 checks)"
  checks:
    - name: silent-errors
      status: pass
      detail: "No empty catch blocks or swallowed promise rejections"
    - name: async-pitfalls
      status: pass
      detail: "No missing awaits, floating promises, or async forEach"
    - name: prototype-pollution
      status: pass
      detail: "No unguarded Object.assign or bracket access on user input"
    - name: equality-coercion
      status: pass
      detail: "Strict equality used; explicit type checks"
    - name: dom-security
      status: pass
      detail: "No innerHTML with user input or eval()"
    - name: nodejs-security
      status: pass
      detail: "No shell injection, variable require, or leaked secrets"
    - name: regex-safety
      status: pass
      detail: "No ReDoS patterns or unescaped user input in RegExp"
    - name: test-quality
      status: pass
      detail: "No vacuous assertions, unmocked spies, or .only/.skip"
    - name: module-scope
      status: pass
      detail: "const/let used; no circular deps or side-effect imports"
    - name: error-handling
      status: pass
      detail: "Errors are proper Error objects with messages"
    - name: input-validation
      status: pass
      detail: "User input validated at all boundaries"
    - name: dependency-hygiene
      status: pass
      detail: "No console.log in prod; deps correctly categorized"
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
  gate: javascript-review-checklist
  message: "Found {N} JavaScript review issues"
  checks:
    - name: silent-errors
      status: pass | fail
      detail: "{file}:{line}: empty catch / swallowed promise rejection"
    - name: async-pitfalls
      status: pass | fail
      detail: "{file}:{line}: missing await / floating promise / async forEach"
    - name: prototype-pollution
      status: pass | fail
      detail: "{file}:{line}: Object.assign with user input / unguarded bracket access"
    - name: equality-coercion
      status: pass | fail
      detail: "{file}:{line}: == instead of === / truthy check on {type}"
    - name: dom-security
      status: pass | fail
      detail: "{file}:{line}: innerHTML with user input / eval()"
    - name: nodejs-security
      status: pass | fail
      detail: "{file}:{line}: exec() with interpolation / leaked env var"
    - name: regex-safety
      status: pass | fail
      detail: "{file}:{line}: user input in RegExp / catastrophic backtracking"
    - name: test-quality
      status: pass | fail
      detail: "{file}:{line}: vacuous assertion / unmocked spy / .only"
    - name: module-scope
      status: pass | fail
      detail: "{file}:{line}: var usage / circular dependency"
    - name: error-handling
      status: pass | fail
      detail: "{file}:{line}: thrown string / Error without message"
    - name: input-validation
      status: pass | fail
      detail: "{file}:{line}: unvalidated user input in {context}"
    - name: dependency-hygiene
      status: pass | fail
      detail: "{file}:{line}: console.log in production / misplaced dep"
    - name: fix-regressions
      status: pass | fail
      detail: "{file}:{line}: fix introduces same class of bug (check #{N})"
  recovery:
    - "Add error handling to empty catch blocks; propagate or log at correct level"
    - "Add await to async calls; use for...of instead of forEach for async"
    - "Use Object.create(null) or Map for user-keyed lookups; validate before Object.assign"
    - "Replace == with ===; use explicit type checks instead of truthy"
    - "Use textContent instead of innerHTML; never eval() user input"
    - "Use execFile/spawn with array args; never log process.env secrets"
    - "Escape user input before RegExp; audit regex for backtracking"
    - "Replace toBeTruthy with specific value checks; restore mocks in afterEach"
    - "Replace var with const/let; break circular dependencies"
    - "Throw Error objects with descriptive messages"
    - "Validate user input at handlers; use parameterized queries"
    - "Gate console.log behind NODE_ENV; move test deps to devDependencies"
    - "Re-scan fix diffs against checks #1-#12 before handoff"
```
</fail>

</gate>
