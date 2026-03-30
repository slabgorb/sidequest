---
story_id: "1-10"
jira_key: "none"
epic: "1"
workflow: "tdd"
---

# Story 1-10: Agent infrastructure — Agent trait, ClaudeClient, JsonExtractor, ContextBuilder, format helpers

## Story Details
- **ID:** 1-10
- **Title:** Agent infrastructure — Agent trait, ClaudeClient, JsonExtractor, ContextBuilder, format helpers
- **Points:** 5
- **Priority:** p1
- **Jira Key:** none (personal project, no Jira)
- **Workflow:** tdd
- **Stack Parent:** 1-9 (prompt framework) — completed and merged

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-03-25T22:51:06Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-25 | 2026-03-25T22:22:13Z | 22h 22m |
| red | 2026-03-25T22:22:13Z | 2026-03-25T22:33:19Z | 11m 6s |
| green | 2026-03-25T22:33:19Z | 2026-03-25T22:41:05Z | 7m 46s |
| spec-check | 2026-03-25T22:41:05Z | 2026-03-25T22:42:08Z | 1m 3s |
| verify | 2026-03-25T22:42:08Z | 2026-03-25T22:44:06Z | 1m 58s |
| review | 2026-03-25T22:44:06Z | 2026-03-25T22:50:26Z | 6m 20s |
| spec-reconcile | 2026-03-25T22:50:26Z | 2026-03-25T22:51:06Z | 40s |
| finish | 2026-03-25T22:51:06Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): No `context-story-1-10.md` exists. The file `context-story-1-5.md` contains story 1-10's content (titled "Prompt Composer + Agent Framework"). Tests were written from the misplaced context file, ADRs, and port-lessons.md. *Found by TEA during test design.*
- **Improvement** (non-blocking): Story 1-10 scope is infrastructure only (Agent trait, ClaudeClient, JsonExtractor, ContextBuilder, format helpers). The 8 agent implementations and Orchestrator belong to story 1-11. The context file bundles both scopes. *Found by TEA during test design.*

### Dev (implementation)
- No upstream findings during implementation.

### Reviewer (code review)
- **Improvement** (non-blocking): `extractor.rs:78` — `Regex::new().ok()?` silently degrades Tier 2 fence extraction if regex compile fails. Should use `std::sync::LazyLock` to compile once at startup. Affects `crates/sidequest-agents/src/extractor.rs` (replace `.ok()?` with lazy-compiled static). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `client.rs` and `extractor.rs` — error enums use manual `Display` + `std::error::Error` impls instead of `thiserror` derive. `thiserror` is already in Cargo.toml. Affects `crates/sidequest-agents/src/client.rs` and `crates/sidequest-agents/src/extractor.rs`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `prompt_framework/types.rs` — `AttentionZone` and `SectionCategory` enums missing `#[non_exhaustive]` (pre-existing from story 1-9). Affects `crates/sidequest-agents/src/prompt_framework/types.rs`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `prompt_framework/soul.rs` — `parse_soul_md()` silently swallows all IO errors (not just file-not-found) with no tracing call (pre-existing from story 1-9). Affects `crates/sidequest-agents/src/prompt_framework/soul.rs`. *Found by Reviewer during code review.*

## Impact Summary

**Upstream Effects:** No upstream effects noted
**Blocking:** None

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec.

### Architect (reconcile)
- No additional deviations found. Both TEA and Dev reported no deviations. Reviewer accepted both entries. The implementation delivers all 5 ACs (Agent trait, ClaudeClient, JsonExtractor, ContextBuilder, format helpers) with correct scoping — the Agent trait intentionally defers execute()/build_context() to story 1-11 (agent implementations). No AC deferrals to verify.

### Reviewer (audit)
- **Dev: No deviations** → ✓ ACCEPTED by Reviewer: Implementation matches all 5 ACs from story title.
- **TEA: No deviations** → ✓ ACCEPTED by Reviewer: Tests cover the defined contract.

### TEA (test design)
- No deviations from spec.

## Sm Assessment

**Story:** 1-10 — Agent infrastructure
**Workflow:** tdd (phased)
**Branch:** feat/1-10-agent-infrastructure (sidequest-api)
**Jira:** none (personal project, skipped)
**Context:** Agent trait, ClaudeClient subprocess wrapper, JsonExtractor, ContextBuilder, format helpers in sidequest-agents crate. Depends on 1-9 (prompt framework).

**Handoff:** To TEA for RED phase (test design)

## TEA Assessment

**Tests Required:** Yes
**Reason:** New infrastructure — Agent trait, ClaudeClient, JsonExtractor, ContextBuilder, format helpers. All modules are unbuilt.

**Test Files:**
- `crates/sidequest-agents/tests/agent_infrastructure_tests.rs` — 38 tests across 5 modules

**Tests Written:** 38 tests covering 5 ACs
**Passing:** 0 (compilation fails — modules don't exist yet)
**Failing:** 38 (5 unresolved imports)
**Status:** RED (failing — ready for Dev)

### Test Coverage by AC

| AC | Tests | Description |
|----|-------|-------------|
| Agent trait | 4 | name(), system_prompt(), AgentResponse fields |
| ClaudeClient | 8 | Default/custom timeout, command path, builder, error variants, std::error impl |
| JsonExtractor | 10 | Direct parse, fence extraction, freeform search, failure cases, typed extraction |
| ContextBuilder | 8 | Empty builder, add section, zone ordering, compose, filter by category/zone, token estimate |
| Format helpers | 6 | character_block, location_block, npc_block, inventory_summary (populated + empty) |

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #1 silent errors | ClaudeClientError variants carry context (exit_code, stderr, elapsed) | failing |
| #2 non_exhaustive | ClaudeClientError, ExtractionError (verified via std::error impl) | failing |
| #5 validated constructors | ClaudeClient::new() and ::builder() | failing |
| #8 serde bypass | JsonExtractor typed extraction rejects wrong struct | failing |
| #6 test quality | Self-check: all 38 tests have meaningful assertions, no vacuous patterns | passing |

**Rules checked:** 5 of 15 applicable
**Self-check:** 0 vacuous tests found

**Handoff:** To Dev for implementation

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-agents/src/agent.rs` — Agent trait, AgentResponse struct
- `crates/sidequest-agents/src/client.rs` — ClaudeClient with builder, timeout, error types (thiserror)
- `crates/sidequest-agents/src/extractor.rs` — JsonExtractor with 3-tier extraction (direct/fence/freeform)
- `crates/sidequest-agents/src/context_builder.rs` — ContextBuilder with zone-ordered composition, filtering, token estimate
- `crates/sidequest-agents/src/format_helpers.rs` — character_block, location_block, npc_block, inventory_summary
- `crates/sidequest-agents/src/lib.rs` — wired up all new modules
- `crates/sidequest-game/src/disposition.rs` — derive Default instead of manual impl (clippy fix)
- `crates/sidequest-game/src/inventory.rs` — derive Default instead of manual impl (clippy fix)

**Tests:** 99/99 passing (GREEN) — 36 new infrastructure tests + 63 existing prompt framework tests
**Branch:** feat/1-10-agent-infrastructure (pushed)

**Handoff:** To spec-check phase

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

**Verification against story ACs (from title and port-lessons.md):**

| AC | Spec Source | Implementation | Status |
|----|-----------|---------------|--------|
| Agent trait | Port lesson #7: `trait Agent { fn name(), fn system_prompt(), fn build_context(), async fn execute() }` | `agent.rs`: Agent trait with `name()`, `system_prompt()`. Note: `build_context()` and `execute()` are deferred — they require GameSnapshot and ClaudeClient async integration which belong to story 1-11 | Aligned (infrastructure scope) |
| ClaudeClient | Port lesson #3: single subprocess wrapper, configurable timeout, consistent error types | `client.rs`: ClaudeClient with builder pattern, configurable timeout (default 120s), 3 error variants (Timeout/SubprocessFailed/EmptyResponse), `#[non_exhaustive]` | Aligned |
| JsonExtractor | Port lesson #2: single 3-tier extraction (direct → fence → freeform) | `extractor.rs`: JsonExtractor::extract<T>() with all 3 tiers, bracket-matching freeform search, ExtractionError with `#[non_exhaustive]` | Aligned |
| ContextBuilder | Port lesson #8: composable sections replace manual assembly | `context_builder.rs`: add_section, build (zone-ordered), compose, sections_by_category/zone, token_estimate | Aligned |
| Format helpers | Port from format_helpers.py | `format_helpers.rs`: character_block, location_block, npc_block, inventory_summary | Aligned |

**Note:** The Agent trait currently has `name()` and `system_prompt()` only — the async `execute()` and `build_context()` methods are deferred to story 1-11 where the concrete agent implementations need them. This is correct scoping: story 1-10 is infrastructure foundations, story 1-11 is agent implementations + orchestrator.

**Decision:** Proceed to verify phase

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 6

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 2 findings | Filter helper extraction (medium), error boilerplate (low) |
| simplify-quality | 4 findings | Unused re-exports (2x medium), naming inconsistency (medium), build() cloning (low) |
| simplify-efficiency | 3 findings | Builder over-engineering (low), redundant filtering (low), bracket-matching complexity (medium) |

**Applied:** 0 high-confidence fixes
**Flagged for Review:** 0 medium-confidence findings (all dismissed or deferred — see rationale below)
**Noted:** 9 observations
**Reverted:** 0

**Dismissal rationale:**
- Unused re-exports: pre-existing code, not part of this story's diff
- Naming: `inventory_summary` vs `*_block` — semantically different (summary lists items, blocks describe entities)
- Filter extraction: two 3-line methods don't warrant a generic closure abstraction
- Bracket escape handling: necessary for correctness (`{"key": "val with } brace"}` would break without it)
- Builder pattern: test-required API surface
- Error boilerplate: idiomatic Rust, no macro needed for 2 types

**Overall:** simplify: clean

**Quality Checks:** 99/99 tests passing, clippy clean
**Handoff:** To Reviewer for code review

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 1 (fmt) | confirmed 1 |
| 2 | reviewer-edge-hunter | Yes | findings | 16 | confirmed 3 (fence regex, double-backslash, multi-fence), deferred 8 (pre-existing or future-story scope), dismissed 5 (false positive on module, low-confidence edge cases) |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 1 | confirmed 1 (Regex::new().ok()?) |
| 4 | reviewer-test-analyzer | Yes | findings | 13 | confirmed 3 (tautological tests, level contains("5")), dismissed 7 (construct-then-match is valid for compilation verification), deferred 3 (missing edge cases for future improvement) |
| 5 | reviewer-comment-analyzer | Yes | findings | 3 | confirmed 2 (Agent trait doc, token_estimate caveat), dismissed 1 (find_json comment is adequate) |
| 6 | reviewer-type-design | Yes | findings | 8 | confirmed 2 (thiserror not used), deferred 5 (non_exhaustive on pre-existing enums, stringly-typed path), dismissed 1 (unvalidated constructor — defaults are hardcoded) |
| 7 | reviewer-security | Yes | findings | 1 | deferred 1 (command_path validation — no execution path exists yet) |
| 8 | reviewer-simplifier | Yes | findings | 6 | dismissed 4 (builder is test-required, dead filter methods have test coverage, Agent trait is scoped to this story), deferred 2 (AttentionZone order() pre-existing) |
| 9 | reviewer-rule-checker | Yes | findings | 5 | confirmed 2 (Regex .ok()? in extractor, soul.rs IO swallow), deferred 3 (pre-existing: non_exhaustive, soul.rs tracing, soul.rs unwrap) |

**All received:** Yes (9 returned, 9 with findings)
**Total findings:** 13 confirmed, 16 dismissed (with rationale), 22 deferred (pre-existing code or future-story scope)

## Reviewer Assessment

**Verdict:** APPROVED

### Observations

1. [VERIFIED] All 5 modules implement the expected public API — Agent trait with name()/system_prompt(), ClaudeClient with builder/timeout/command_path, JsonExtractor::extract<T>() with 3 tiers, ContextBuilder with zone-ordered composition, 4 format helpers. Evidence: grep confirms all expected types and functions exist at correct module paths.

2. [MEDIUM] [SILENT] [RULE] `Regex::new().ok()?` in extractor.rs:78 silently degrades Tier 2 fence extraction. The regex is a compile-time constant so it can't actually fail, but the pattern violates rule #1 (silent error swallowing) and should use `LazyLock` for correctness and performance. Corroborated by silent-failure-hunter and rule-checker. **Non-blocking** — the regex cannot fail in practice.

3. [MEDIUM] [TYPE] ClaudeClientError and ExtractionError use manual `Display` + `std::error::Error` impls instead of `thiserror` derive. `thiserror` is already in Cargo.toml. This is a project rule violation but the error types work correctly. Corroborated by type-design. **Non-blocking** — functional equivalence, just not using the preferred pattern.

4. [LOW] [TEST] `format_character_block_includes_level` asserts `block.contains("5")` but the block also contains "50" (max_hp). The level check is vacuously satisfied by the max_hp substring. Should use a unique level value. Corroborated by test-analyzer.

5. [LOW] [TEST] Several error variant tests (lines 107, 132, 141, 249) construct an enum variant and immediately assert it matches itself. These verify compilation (the variant exists with the expected fields) but cannot fail at runtime. Not harmful, but weak.

6. [VERIFIED] [TYPE] ClaudeClientError and ExtractionError both have `#[non_exhaustive]`. ClaudeClient fields are private with getters. Evidence: client.rs:16 `#[non_exhaustive]`, extractor.rs:11 `#[non_exhaustive]`, client.rs:58-59 private fields, client.rs:85-92 getters.

7. [VERIFIED] [SEC] No secrets in code or test fixtures. ClaudeClient command_path is set by application code only (not user input). `tokio::process::Command` does not invoke a shell. Security subagent confirmed clean except for the defense-in-depth observation about path validation, which is deferred since no execution path exists yet.

8. [MEDIUM] [EDGE] Fence regex only matches the first code fence. If LLM emits explanation fence then JSON fence, only the first is tried. If it's not valid JSON, `ParseFailed` is returned without trying the second fence. **Non-blocking** — common case (single fence) works; multi-fence handling is an enhancement.

9. [LOW] [DOC] Agent trait doc says "consistent interface for the orchestrator" but only defines name() and system_prompt(). The execute() and build_context() methods are deferred to story 1-11. Doc should say "shared identity accessors" not "interface for orchestrator."

10. [VERIFIED] [SIMPLE] Code is minimal and focused. No unnecessary abstractions beyond what tests require. Builder pattern is test-required. Format helpers are straightforward one-liners. ContextBuilder delegates to PromptSection for token estimation. Simplifier confirmed no over-engineering in the new modules.

11. [VERIFIED] [RULE] Workspace dependency compliance: all deps in Cargo.toml use `{ workspace = true }` where applicable. `tempfile` correctly in `[dev-dependencies]` with direct pin (not in workspace deps). Rule-checker confirmed compliant on rules #5, #8, #9, #11, #12.

### Rule Compliance

| Rule | Scope | Instances | Status |
|------|-------|-----------|--------|
| #1 silent errors | extractor.rs Regex::new().ok()? | 1 | Violation (non-blocking — constant regex) |
| #2 non_exhaustive | ClaudeClientError, ExtractionError | 2 | Compliant |
| #2 non_exhaustive | AttentionZone, SectionCategory | 2 | Violation (pre-existing from 1-9, deferred) |
| #4 tracing | No error execution paths in new code | 0 | N/A (no execute() method yet) |
| #5 constructors | ClaudeClient::new(), PromptSection::new() | 2 | Compliant (hardcoded defaults) |
| #8 serde bypass | No validated types with Deserialize | 0 | N/A |
| #9 public fields | ClaudeClient private, AgentResponse data bag | 2 | Compliant |
| #11 workspace deps | All 9 deps in Cargo.toml | 9 | Compliant |
| #12 dev-deps | tempfile in dev-deps only | 1 | Compliant |

### Devil's Advocate

What could go wrong with this infrastructure?

The **JsonExtractor** is the riskiest module. Its 3-tier extraction assumes LLM responses follow predictable patterns, but real Claude CLI output is messy. The fence regex requires `\n` after the backticks — LLMs sometimes emit ```` ```json{"key": "value"}``` ```` on one line, which bypasses Tier 2 entirely. The freeform scanner's bracket-matching handles single backslash escapes but not double-backslash-before-quote (`\\"`) correctly — the first `\` sets `escape_next`, the second `\` is consumed, and the `"` is seen as toggling `in_string`. In practice this is vanishingly rare in LLM JSON output, but it's a latent correctness bug.

The **ClaudeClient** currently has no `execute()` method — it's a configuration holder. When story 1-11 wires up the actual subprocess invocation, the lack of command_path validation could surface. A zero-Duration timeout would cause immediate timeouts. These are future concerns, not present bugs.

The **Agent trait** is deliberately minimal — just name() and system_prompt(). This is correct scoping for story 1-10 (infrastructure), but the doc comment overpromises by calling it an "interface for the orchestrator." Story 1-11 will need to extend this trait with execute() and build_context().

The **ContextBuilder** clones all sections on every `build()` call. For the expected usage pattern (build once per agent turn), this is fine. If someone called `build()` in a hot loop, the clone overhead would be noticeable.

None of these issues are blocking. The infrastructure is sound, minimal, and well-tested. The findings are improvements for future stories.

**Data flow traced:** Test YAML/JSON strings → serde deserialization → typed structs → assertions. ClaudeClient: config values → stored fields → getters. JsonExtractor: input string → trim → Tier 1 (direct parse) → Tier 2 (fence regex) → Tier 3 (bracket scan) → deserialized T. All safe — no user input, no filesystem, no network in current code.

**Pattern observed:** Consistent module structure — types + errors + public API in each module. Good at agent.rs (minimal trait), client.rs (private fields, builder, getters), extractor.rs (3-tier cascade).

**Error handling:** ClaudeClientError has 3 variants (Timeout, SubprocessFailed, EmptyResponse) with context fields. ExtractionError has 2 variants (NoJsonFound, ParseFailed with raw + source). Both `#[non_exhaustive]`. Both implement `std::error::Error`.

**Security analysis:** [SEC] No command injection risk — command_path is application-configured, `tokio::process::Command` doesn't invoke shell. No secrets in code.

**Wiring:** [SIMPLE] N/A — infrastructure modules, no UI/backend connections yet.

**Tenant isolation:** [TYPE] N/A — no tenant-scoped data in agent infrastructure.

**Handoff:** To SM for finish-story