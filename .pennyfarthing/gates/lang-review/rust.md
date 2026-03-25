<gate name="rust-review-checklist" model="haiku">

<purpose>
Rust-specific self-review checklist for dev agent before handoff.
Catches recurring review findings that automated tools miss.
Updated after every external review round — each check traces to the
PR finding that motivated it.
</purpose>

<pass>
Scan all files changed in this PR (`git diff --name-only develop...HEAD`)
that end in `.rs`. For each file, check the following rules.

**1. Silent error swallowing**
Search for these patterns in changed lines:
- `.ok()` — should be `.map_err(...)` or explicit error handling
- `.unwrap_or_default()` — acceptable only when documented why default is safe
- `.and_then(|v| v.to_str().ok())` — must handle the error case explicitly
- `.expect()` on a parse/conversion where the input is user-controlled
  (e.g., `s.parse::<i64>().expect(...)` where s comes from query input)
- `2>/dev/null` in any doc comments or test scripts

For each match, check if the error path is user-controlled (API input,
config files, headers, query strings). If so, it MUST be handled explicitly.

**2. Missing `#[non_exhaustive]`**
Search for `pub enum` declarations in changed files. Every public enum
that will grow (error types, command types, format types, status codes)
MUST have `#[non_exhaustive]`. Exempt: enums with `#[serde(rename)]` on
every variant where the set is protocol-fixed.

**3. Hardcoded placeholder values**
Search changed files for:
- `"none"` or `"unknown"` as function arguments (trace IDs, user IDs)
- `false` as a struct field literal where the field is semantically meaningful
  (e.g., `negated: false` when a `NOT` branch should exist)
- Magic numbers without comment explaining rationale

**4. Tracing: coverage AND correctness**
For any crate that declares `tracing` in its `Cargo.toml`:
- Error paths MUST have `tracing::error!` or `tracing::warn!`
- Middleware functions SHOULD have `tracing::info!` or `#[instrument]`
- If a SECURITY doc comment claims tracing exists, verify the call is there
- **Log level classification:** 4xx client errors use `warn!`, 5xx server
  errors use `error!`. A blanket `tracing::error!` for all HTTP error
  responses causes alert fatigue and buries real server errors.

**5. Unvalidated constructors at trust boundaries**
Search for `::new(` calls on ID/context types. At API boundaries (handlers,
middleware, deserialization), constructors MUST validate. `new_unchecked()`
is only for tests and trusted internal sources.

**6. Test quality**
Search test files for:
- `assert!(x.is_none() || ...)` — vacuously true, replace with `assert_eq!`
- `let _ = result;` — test with zero assertions
- Negative assertions without verifying the tool actually ran
- Security-fix code paths without regression tests
- CWE-209 tests that check status code but not response body content
  (must verify attacker input is NOT echoed back)
- Tests that check a feature exists but not its actual value/variant
  (e.g., `matches!(x, Foo | Bar)` when only one is correct)

**7. Unsafe `as` casts on external input**
Search for `as usize`, `as u32`, `as i32` etc. in changed lines.
If the source value comes from user input or parsing (not a known-safe
internal constant), use `try_from()` / `try_into()` instead.
`n as usize` silently truncates on 32-bit targets (CWE-190).

**8. `#[derive(Deserialize)]` bypassing validated constructors**
For any type that has a validating `new()` constructor (returns `Result`),
check if it also `#[derive(Deserialize)]`. If so, deserialization bypasses
validation — use `#[serde(try_from = "...")]` or a custom `Deserialize`
impl that calls the validating constructor (CWE-20).

**9. Public fields on types with invariants**
Search for `pub struct` declarations. Two categories of fields MUST be
private with getters:
- **Security-critical:** `tenant_id`, `permissions`, `signature`,
  `auth_token`, `trace_id` — prevents post-construction mutation of
  security policy.
- **Validated invariants:** any field that a custom `Deserialize` impl
  or `new()` constructor validates (e.g., rejects empty). If a field is
  validated on input, it must be private to prevent post-construction
  mutation that defeats the validation.

**10. Tenant context in trait signatures**
Any trait method that touches tenant data MUST include `&TenantId`,
`&TenantContext`, or `&impl TenantScoped` in its signature.
This applies to both write AND read/transform operations.

"The function signature IS the security policy." If one trait in a crate
carries tenant context, ALL analogous traits in the same crate should too.

**11. Workspace dependency compliance**
Check `Cargo.toml` for the changed crate. Any dependency that exists in
the root `[workspace.dependencies]` MUST use `{ workspace = true }` —
never inline version pins. Inline pins cause version drift across crates.

**12. Dev-only dependencies in `[dependencies]`**
Search changed `Cargo.toml` files. If a dependency (e.g., `serde_json`,
`tempfile`, `assert_cmd`) is only imported in `tests/` or `#[cfg(test)]`
modules, it belongs in `[dev-dependencies]`, not `[dependencies]`.

**13. Constructor/Deserialize validation consistency**
For any type with both a manual constructor (`new()`) and a custom
`Deserialize` impl (or `#[serde(try_from)]`): both paths MUST enforce
the same invariants. If Deserialize rejects empty `name`, then `new()`
must also reject empty `name` (and vice versa).

**14. Fix-introduced regressions (meta-check)**
After applying fixes for review findings, re-scan the fix diff against
checks #1-#13. The most common re-review pattern is a fix that introduces
the same class of bug it was fixing.

**15. Unbounded recursive/nested input (CWE-674, CWE-400)**
Any parser, recursive function, or combinator accepting user input MUST
have a depth or size limit. Check for:
- `recursive()` calls without a nesting depth counter
- Recursive function patterns without a `max_depth` parameter
- `parse_*()` entry points without an input length check

If ALL checks pass across all changed `.rs` and `Cargo.toml` files, return:

```yaml
GATE_RESULT:
  status: pass
  gate: rust-review-checklist
  message: "Rust self-review checklist passed (15 checks)"
  checks:
    - name: silent-errors
      status: pass
      detail: "No unhandled .ok()/.unwrap_or_default()/.expect() on user-controlled paths"
    - name: non-exhaustive
      status: pass
      detail: "All public enums have #[non_exhaustive]"
    - name: placeholders
      status: pass
      detail: "No hardcoded placeholder values"
    - name: tracing
      status: pass
      detail: "Error paths have tracing calls with correct severity levels"
    - name: constructors
      status: pass
      detail: "Trust boundary constructors validate input"
    - name: test-quality
      status: pass
      detail: "No vacuous assertions, zero-assertion tests, or missing regression tests"
    - name: unsafe-casts
      status: pass
      detail: "No silent `as` casts on user-controlled values"
    - name: serde-bypass
      status: pass
      detail: "Derive(Deserialize) types with validating constructors use serde(try_from)"
    - name: public-fields
      status: pass
      detail: "Fields with security or validation invariants are private with getters"
    - name: tenant-context
      status: pass
      detail: "Side-effect trait methods include tenant context parameter"
    - name: workspace-deps
      status: pass
      detail: "All deps use { workspace = true } where available"
    - name: dev-deps
      status: pass
      detail: "Test-only deps are in [dev-dependencies]"
    - name: constructor-deserialize-consistency
      status: pass
      detail: "Constructor and Deserialize enforce identical invariants"
    - name: fix-regressions
      status: pass
      detail: "Fix commits re-scanned against checks #1-#13"
    - name: unbounded-input
      status: pass
      detail: "Recursive parsers and user input have depth/size limits"
```
</pass>

<fail>
List each violation with file, line, and the specific pattern matched:

```yaml
GATE_RESULT:
  status: fail
  gate: rust-review-checklist
  message: "Found {N} Rust review issues"
  checks:
    - name: silent-errors
      status: pass | fail
      detail: "{file}:{line}: .ok() swallows {error_type} on user input"
    - name: non-exhaustive
      status: pass | fail
      detail: "{file}:{line}: pub enum {Name} missing #[non_exhaustive]"
    - name: placeholders
      status: pass | fail
      detail: "{file}:{line}: hardcoded \"{value}\" — use actual value or config"
    - name: tracing
      status: pass | fail
      detail: "{file}: error paths have no tracing calls / wrong log level"
    - name: constructors
      status: pass | fail
      detail: "{file}:{line}: {Type}::new() at trust boundary without validation"
    - name: test-quality
      status: pass | fail
      detail: "{file}:{line}: vacuously true assertion / missing regression test"
    - name: unsafe-casts
      status: pass | fail
      detail: "{file}:{line}: `as usize` on user-controlled value — use try_from()"
    - name: serde-bypass
      status: pass | fail
      detail: "{file}:{line}: derive(Deserialize) bypasses {Type}::new() validation"
    - name: public-fields
      status: pass | fail
      detail: "{file}:{line}: pub {field} on security-critical type {Type}"
    - name: tenant-context
      status: pass | fail
      detail: "{file}:{line}: {Trait}::{method}() missing tenant context parameter"
    - name: workspace-deps
      status: pass | fail
      detail: "{file}: {dep} uses inline version instead of {{ workspace = true }}"
    - name: dev-deps
      status: pass | fail
      detail: "{file}: {dep} only used in tests but listed in [dependencies]"
    - name: constructor-deserialize-consistency
      status: pass | fail
      detail: "{file}: {Type}::new() accepts invalid {field} that Deserialize rejects"
    - name: fix-regressions
      status: pass | fail
      detail: "{file}:{line}: fix commit introduces same class of bug (check #{N})"
    - name: unbounded-input
      status: pass | fail
      detail: "{file}:{line}: recursive/unbounded input without depth/size limit"
  recovery:
    - "Replace .ok()/.expect() with explicit error handling"
    - "Add #[non_exhaustive] to public enums"
    - "Replace hardcoded values with actual data from context"
    - "Add tracing calls; use warn! for 4xx, error! for 5xx"
    - "Use validated constructors at API boundaries"
    - "Replace vacuous assertions with assert_eq!; add regression tests for CWE fixes"
    - "Replace `as usize` with usize::try_from() on user input"
    - "Add #[serde(try_from)] or custom Deserialize for validated types"
    - "Make security-critical fields private, add getters"
    - "Add &TenantId or &impl TenantScoped to side-effect trait methods"
    - "Switch inline version pins to { workspace = true }"
    - "Move test-only deps to [dev-dependencies]"
    - "Ensure new()/Deserialize enforce identical validation rules"
    - "Re-scan fix diffs against checks #1-#13 before handoff"
    - "Add depth/size limits to recursive parsers and user input paths"
```
</fail>

</gate>
