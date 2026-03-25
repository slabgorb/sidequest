<gate name="typescript-review-checklist" model="haiku">

<purpose>
TypeScript-specific self-review checklist for dev agent before handoff.
Extends JavaScript checks with type system concerns. Catches patterns
that compile successfully but produce runtime errors or defeat type safety.
</purpose>

<pass>
Scan all files changed in this PR (`git diff --name-only develop...HEAD`)
that end in `.ts` or `.tsx`. For each file, check the following rules.

**1. Type safety escapes**
Search for patterns that defeat the type system:
- `as any` — must have a comment explaining why, and a TODO to remove
- `as unknown as T` — double-cast bypass, almost always wrong
- `@ts-ignore` without specific error code — use `@ts-expect-error` with code
- `@ts-expect-error` without the next line actually producing an error — dead suppression
- `!` (non-null assertion) on values that CAN be null at runtime
- Type predicates (`is` functions) without runtime validation inside

**2. Generic and interface pitfalls**
- `Record<string, any>` — use a proper interface or `Record<string, unknown>`
- `object` type — too broad, use specific interface
- `Function` type — use specific signature `(arg: T) => R`
- Missing `readonly` on array/object parameters that should not be mutated
- `Partial<T>` used where only specific fields are optional — loses required constraints
- `Omit<T, string>` — literal string removes nothing, use union type

**3. Enum anti-patterns**
- `const enum` in library code — breaks declaration emit, can't be used across packages
- Numeric enums without explicit values — fragile to reordering
- String enums where a union type suffices — enums have runtime cost
- Missing exhaustiveness check in switch/case on enum (no `default: assertNever(x)`)

**4. Null/undefined handling**
- Optional chaining `?.` followed by method call without null check on result
- `x ?? defaultValue` where x can be `0` or `""` (falsy but valid) — correct
- `x || defaultValue` where x can be `0` or `""` — BUG, use `??`
- Destructuring without defaults on optional fields: `const { name } = config`
  when `name` might be undefined
- `Map.get()` result used without undefined check

**5. Module and declaration issues**
- Re-exporting types without `export type` — ships runtime code for type-only exports
- `import type` for values that are used at runtime — compile error in isolatedModules
- Ambient declarations (`declare`) that shadow actual implementations
- `.js` extension missing in relative imports (required for ESM/Node16+ resolution)
- `/// <reference>` directives in source files — use proper imports

**6. React/JSX specific (for .tsx files)**
- `useEffect` with missing dependency array — runs on every render
- `useEffect` dependency on object/array literal — infinite re-render loop
- `useMemo`/`useCallback` with empty deps when closure captures changing values
- `key={index}` on lists where items can be reordered/inserted/deleted
- State updates on unmounted components — check if component is still mounted
- `dangerouslySetInnerHTML` with user input — XSS (CWE-79)
- Event handlers not using `useCallback` in performance-critical render paths

**7. Async/Promise patterns**
All JavaScript async checks (#2 from JS checklist) apply, plus:
- `Promise<void>` return type on functions that should return data
- Async functions that never throw returning `Promise<T>` instead of `T`
- `ReturnType<typeof asyncFn>` gives `Promise<T>`, not `T` — use `Awaited<>`
- `try/catch` in async that catches and re-throws without adding context

**8. Test quality**
All JavaScript test checks (#8 from JS checklist) apply, plus:
- `as any` in test assertions to make types match — fix the types instead
- Mock types not matching real implementation signatures
- `jest.mock()` / `vi.mock()` with incorrect generic parameters
- Integration tests that import from `dist/` instead of `src/`
- Missing `@types/*` for test dependencies

**9. Build and config concerns**
- `compilerOptions.strict` disabled or individual strict flags turned off
- `skipLibCheck: true` hiding real type errors in dependencies
- Source maps disabled in development (`sourceMap: false`)
- `outDir` and `rootDir` misconfigured causing flat output structure
- `paths` aliases without corresponding `moduleNameMapper` in test config

**10. Security: type-level input validation**
- User input typed as `string` instead of branded/validated type
- API response typed with `interface` but no runtime validation (Zod, io-ts, etc.)
- `JSON.parse()` typed with `as T` instead of runtime schema validation
- URL/path parameters cast to expected type without validation
- Template literal types that accept arbitrary string interpolation

**11. Error handling**
All JavaScript error checks (#10 from JS checklist) apply, plus:
- `catch (e: any)` — use `catch (e: unknown)` and narrow
- Error types without discriminant field — can't narrow in catch
- `Result<T, E>` patterns without exhaustive error handling
- Async error boundaries that swallow type information

**12. Performance and bundle concerns**
- Large imports from barrel files (`import { x } from '@pkg'`) — tree-shaking issues
- Dynamic `import()` without chunking strategy — unexpected bundle size
- `JSON.stringify()` on large objects in hot paths without caching
- Synchronous `fs` operations in server request handlers

**13. Fix-introduced regressions (meta-check)**
After applying fixes for review findings, re-scan the fix diff against
checks #1-#12. Common patterns:
- Adding `as any` to silence a type error instead of fixing it
- Adding null checks but using `||` instead of `??`
- Adding runtime validation but not updating the type to match

If ALL checks pass across all changed `.ts`/`.tsx` files, return:

```yaml
GATE_RESULT:
  status: pass
  gate: typescript-review-checklist
  message: "TypeScript self-review checklist passed (13 checks)"
  checks:
    - name: type-safety-escapes
      status: pass
      detail: "No unwarranted as any, ts-ignore, or non-null assertions"
    - name: generic-interface
      status: pass
      detail: "Proper types used; no Record<string,any> or Function type"
    - name: enum-patterns
      status: pass
      detail: "Enums correctly valued and exhaustively matched"
    - name: null-undefined
      status: pass
      detail: "Nullish coalescing used correctly; optional fields handled"
    - name: module-declarations
      status: pass
      detail: "Type-only exports marked; .js extensions present"
    - name: react-jsx
      status: pass
      detail: "Hooks deps correct; no dangerouslySetInnerHTML with user input"
    - name: async-promises
      status: pass
      detail: "Async patterns correct; Awaited<> used where needed"
    - name: test-quality
      status: pass
      detail: "No as any in tests; mock types match implementations"
    - name: build-config
      status: pass
      detail: "Strict mode enabled; paths and maps consistent"
    - name: input-validation
      status: pass
      detail: "Runtime validation at API boundaries; no as T on JSON.parse"
    - name: error-handling
      status: pass
      detail: "catch(e: unknown) with narrowing; typed errors"
    - name: performance-bundle
      status: pass
      detail: "No barrel file over-imports; async fs in handlers"
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
  gate: typescript-review-checklist
  message: "Found {N} TypeScript review issues"
  checks:
    - name: type-safety-escapes
      status: pass | fail
      detail: "{file}:{line}: as any / @ts-ignore / non-null assertion on nullable"
    - name: generic-interface
      status: pass | fail
      detail: "{file}:{line}: Record<string,any> / Function type / missing readonly"
    - name: enum-patterns
      status: pass | fail
      detail: "{file}:{line}: const enum in library / missing exhaustiveness check"
    - name: null-undefined
      status: pass | fail
      detail: "{file}:{line}: || instead of ?? on nullable / missing undefined check"
    - name: module-declarations
      status: pass | fail
      detail: "{file}:{line}: missing export type / .js extension / reference directive"
    - name: react-jsx
      status: pass | fail
      detail: "{file}:{line}: useEffect missing dep / key={index} / dangerouslySetInnerHTML"
    - name: async-promises
      status: pass | fail
      detail: "{file}:{line}: missing await / ReturnType without Awaited"
    - name: test-quality
      status: pass | fail
      detail: "{file}:{line}: as any in test / mock type mismatch"
    - name: build-config
      status: pass | fail
      detail: "{file}: strict disabled / paths without moduleNameMapper"
    - name: input-validation
      status: pass | fail
      detail: "{file}:{line}: as T on user input without runtime validation"
    - name: error-handling
      status: pass | fail
      detail: "{file}:{line}: catch(e: any) / unnarrowed unknown error"
    - name: performance-bundle
      status: pass | fail
      detail: "{file}:{line}: barrel import / sync fs in handler"
    - name: fix-regressions
      status: pass | fail
      detail: "{file}:{line}: fix introduces same class of bug (check #{N})"
  recovery:
    - "Remove as any; fix the underlying type error or use as unknown with narrowing"
    - "Replace Record<string,any> with typed interface; use specific function signatures"
    - "Add explicit values to numeric enums; add default: assertNever(x) to switches"
    - "Replace || with ?? for nullable values; add undefined checks after Map.get()"
    - "Add export type for type-only re-exports; add .js to relative imports"
    - "Fix useEffect deps; replace key={index} with stable IDs"
    - "Add await to async calls; use Awaited<ReturnType<typeof fn>>"
    - "Fix mock types to match implementation; remove as any from assertions"
    - "Enable strict mode; sync paths aliases with test moduleNameMapper"
    - "Add Zod/io-ts validation at API boundaries; validate JSON.parse results"
    - "Use catch(e: unknown) and narrow with instanceof/type guards"
    - "Import specific exports instead of barrel; use async fs in handlers"
    - "Re-scan fix diffs against checks #1-#12 before handoff"
```
</fail>

</gate>
