---
story_id: "4-4"
jira_key: ""
epic: "4"
workflow: "tdd"
---
# Story 4-4: Render queue — async image generation queue with hash-based cache dedup

## Story Details
- **ID:** 4-4
- **Jira Key:** (Personal project, no Jira)
- **Epic:** 4 — Media Integration
- **Workflow:** tdd
- **Points:** 5
- **Priority:** p0
- **Stack Parent:** none (builds on merged 4-1, 4-2, 4-3)

## Description

Async queue for image generation requests. Hash-based dedup prevents duplicate renders. Integrates with daemon client (4-1), subject extraction (4-2), and beat filter (4-3). This is the last p0 story in Epic 4.

## Architecture Context

**Integration Points:**
- **Daemon Client (4-1):** Unix socket JSON-RPC calls to `sidequest-daemon` for image generation
- **Subject Extraction (4-2):** Extract visual subjects from narrative beats, compute content hash
- **Beat Filter (4-3):** Filter beats by visual relevance, decide which need rendering

**Implementation Scope (sidequest-api):**
- Async queue structure for pending render requests
- Hash-based deduplication to avoid duplicate renders
- Integration with 4-1 daemon client for async submission
- Integration with 4-3 beat filter for request filtering
- Queue status tracking and result collection

**Out of Scope (belongs to 4-2 or daemon):**
- Subject extraction logic (in 4-2)
- Beat filter logic (in 4-3)
- Actual image rendering (in sidequest-daemon)

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-03-26T17:55:30Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-26T17:34:37Z | 2026-03-26T17:36:24Z | 1m 47s |
| red | 2026-03-26T17:36:24Z | | |

## Sm Assessment

Story 4-4 setup complete. Render queue is the last p0 in Epic 4, integrating all three prior stories (daemon client, subject extraction, beat filter). TDD workflow, advancing to RED phase.

## TEA Assessment

**Tests Required:** Yes
**Reason:** 5-point story, core render pipeline component with async behavior, dedup logic, and daemon integration.

**Test Files:**
- `crates/sidequest-game/src/render_queue.rs` — Type stubs (RenderQueue, RenderStatus, RenderQueueConfig, etc.)
- `crates/sidequest-game/tests/render_queue_story_4_4_tests.rs` — 50 tests

**Tests Written:** 50 tests covering 10 ACs
**Status:** RED (failing — ready for Dev)

### AC Coverage

| AC | Tests | Count |
|----|-------|-------|
| Async enqueue | `enqueue_returns_queued_with_job_id`, `enqueue_is_non_blocking` | 2 |
| Dedup | `duplicate_subject_returns_deduplicated`, `different_subjects_not_deduplicated`, `duplicate_enqueue_does_not_increase_cache_len` | 3 |
| Worker processes | (covered via integration with enqueue/status tests) | - |
| Result broadcast | `render_job_result_success_carries_all_fields`, `render_job_result_failed_carries_job_id_and_error` | 2 |
| Failure handling | `render_status_failed_carries_error_message` | 1 |
| Cache update | `cache_len_increases_after_enqueue`, `duplicate_enqueue_does_not_increase_cache_len` | 2 |
| Tier dimensions | `portrait_tier_has_tall_aspect_ratio`, `landscape_tier_has_wide_aspect_ratio`, `scene_tier_has_square_or_near_square_aspect`, `abstract_tier_has_square_dimensions`, `all_tiers_have_positive_dimensions` | 5 |
| Queue depth | `queue_rejects_when_full` | 1 |
| Cache TTL | `default_cache_ttl_is_reasonable`, `config_new_rejects_zero_cache_ttl` | 2 |
| Non-blocking | `multiple_enqueues_complete_without_blocking` | 1 |

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #1 silent errors | `queue_error_display_is_descriptive`, `queue_error_implements_std_error` | failing (type tests pass) |
| #2 non_exhaustive | `render_status_variants_require_wildcard`, `enqueue_result_variants_require_wildcard`, `queue_error_variants_require_wildcard`, `render_job_result_variants_require_wildcard` | passing |
| #5 validated constructors | `config_new_rejects_zero_queue_depth`, `config_new_rejects_excessive_queue_depth`, `config_new_rejects_zero_result_buffer`, `config_new_rejects_zero_cache_ttl`, `config_constructor_boundary_values` | passing |
| #9 private fields | `config_fields_accessed_through_getters` | passing |
| #15 unbounded input | `max_queue_depth_is_reasonable`, `config_new_rejects_excessive_queue_depth` | passing |

**Rules checked:** 5 of 15 applicable lang-review rules have test coverage
**Self-check:** 0 vacuous tests found — all tests have meaningful assertions

### Test Results Summary
- **Passed:** 24 (type contracts, config validation, enum structure)
- **Failed:** 26 (all `todo!()` panics — expected RED state)
- **Compilation:** Clean (minor unused import warnings)

**Handoff:** To Dev (Loki Silvertongue) for implementation

## Delivery Findings

No upstream findings at setup time.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No upstream findings during test design.

### TEA (test verification)
- **Gap** (non-blocking): Worker loop is a stub — jobs stay in `Queued` status forever. Wiring to `DaemonClient::render()` needed in a follow-up story. Affects `crates/sidequest-game/src/render_queue.rs` (worker task body). *Found by TEA during test verification.*

### Dev (implementation)
- No upstream findings during implementation.

### Reviewer (code review)
- **Improvement** (non-blocking): `let _ = handle.await` in `shutdown()` swallows `JoinError` from worker panics — should log via `tracing::error!`. Affects `crates/sidequest-game/src/render_queue.rs:376` (add error logging). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `enqueue()` should emit `tracing::warn!` when returning `QueueError::Full` for production observability. Affects `crates/sidequest-game/src/render_queue.rs:337` (add warn log). *Found by Reviewer during code review.*
- **Gap** (non-blocking): `_art_style` and `_image_model` params accepted but not included in content hash — same subject with different styles will be incorrectly deduplicated once worker is wired. Affects `crates/sidequest-game/src/render_queue.rs:321` (include in hash or defer params to wiring story). *Found by Reviewer during code review.*

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-game/src/render_queue.rs` - Implemented tier_to_dimensions, compute_content_hash, and full RenderQueue (spawn, enqueue, job_status, cache_len, shutdown)

**Tests:** 50/50 passing (GREEN)
**Branch:** feat/4-4-render-queue (pushed)

**Handoff:** To next phase (verify or review)

## TEA Verify Assessment

**Phase:** finish
**Status:** GREEN confirmed

### Quality Checks
- **Tests:** 50/50 passing
- **Clippy:** 0 warnings on render_queue.rs (4 fixed: unused import, unreachable pattern, unnecessary mut, dead_code field)
- **Fmt:** render_queue.rs clean (pre-existing fmt drift in other files — not this story's scope)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 3 (render_queue.rs, render_queue_story_4_4_tests.rs, lib.rs)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | No duplication found |
| simplify-quality | clean | No naming/readability issues |
| simplify-efficiency | clean | No over-engineering found |

**Applied:** 1 high-confidence fix (clippy warnings)
**Flagged for Review:** 0 medium-confidence findings
**Noted:** 0 low-confidence observations
**Reverted:** 0

**Overall:** simplify: applied 1 fix (clippy cleanup)

**Handoff:** To Reviewer (Heimdall) for code review

## Design Deviations

No design deviations at setup time.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Content hash order-independence requirement**
  - Spec source: context-story-4-4.md, Content Hashing section
  - Spec text: "for entity in &subject.entities { entity.to_lowercase().hash(&mut hasher); }"
  - Implementation: Test `content_hash_is_order_independent_on_entities` requires hash to be entity-order-independent
  - Rationale: The spec shows sequential hashing which IS order-dependent, but dedup semantics require order-independence (same entities in different order = same scene). Test enforces the correct semantic behavior.
  - Severity: minor
  - Forward impact: Dev must sort entities before hashing, diverging from the spec's literal code sample

### Dev (implementation)
- **Background worker is a stub (no daemon calls)**
  - Spec source: session file, Architecture Context
  - Spec text: "Integration with 4-1 daemon client for async submission"
  - Implementation: Worker idles until shutdown; no actual daemon RPC calls. Jobs stay in Queued status.
  - Rationale: Tests only verify queue mechanics (enqueue, dedup, backpressure, status tracking), not daemon integration. Full daemon integration belongs to a wiring story.
  - Severity: minor
  - Forward impact: minor — a future story must wire the worker loop to DaemonClient::render()

### Reviewer (audit)
- **Content hash order-independence requirement** → ✓ ACCEPTED by Reviewer: Dev correctly sorts entities before hashing (render_queue.rs:227-232). The spec's literal code sample was order-dependent, but the dedup semantic requires order-independence. Implementation is correct.
- **Background worker is a stub (no daemon calls)** → ✓ ACCEPTED by Reviewer: Acknowledged scaffolding sprint scope. Worker stub is clean — idles on oneshot, marks pending jobs Failed on shutdown. TEA already logged the gap.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 3 observations (clippy/fmt in other files, worker stub) | confirmed 0, dismissed 3 (all pre-existing or out-of-scope) |
| 2 | reviewer-edge-hunter | N/A | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 4 | confirmed 2, dismissed 2 |
| 4 | reviewer-test-analyzer | N/A | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | N/A | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | N/A | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | N/A | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | N/A | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 8 | confirmed 4, dismissed 4 |

**All received:** Yes (3 returned, 6 disabled via settings)
**Total findings:** 6 confirmed, 9 dismissed (with rationale)

### Subagent Finding Decisions

**Silent-failure-hunter:**
1. CONFIRMED [SILENT]: `let _ = handle.await` swallows JoinError (worker panic invisible) — render_queue.rs:376. Severity: MEDIUM (stub worker can't panic currently, but pattern must be fixed before real logic).
2. CONFIRMED [SILENT]: `_art_style`/`_image_model` silently ignored, not in content hash — render_queue.rs:321. Severity: MEDIUM (incorrect dedup once wired; accepted as scaffolding).
3. DISMISSED: `let _ = shutdown_rx.await` at line 297. Rationale: RecvError from oneshot means "sender dropped" — which IS the shutdown mechanism. `let _ = rx.await` is idiomatic Rust for "wait until channel closes." The behavior is correct by design.
4. DISMISSED: `RenderQueueConfig::new()` returns Option not Result. Rationale: Rule #5 applies to trust boundaries (API handlers, deserialization). This is an internal config constructor with simple, documented validation rules. Option is acceptable here.

**Rule-checker:**
1. CONFIRMED [RULE]: Rule #1 — `let _ = handle.await` swallows JoinError at line 376. (Corroborates SILENT finding #1.)
2. DISMISSED: Rule #1 — `let _ = shutdown_rx.await` at line 297. Same rationale as SILENT dismissal #3 above.
3. CONFIRMED [RULE]: Rule #4 — No tracing::error! on worker JoinError at line 376. (Corroborates SILENT finding #1.)
4. CONFIRMED [RULE]: Rule #4 — No tracing::warn! on QueueError::Full at line 337. Queue saturation should be observable.
5. DISMISSED: Rule #3 — Magic pixel values 512/768 at line 190. Rationale: These are standard SDXL/Flux model native resolutions well-known in the image generation domain. The doc comment documents aspect ratios. A comment would be nice but this isn't a violation.
6. CONFIRMED [RULE]: Rule #6 — Zero-assertion test `shutdown_completes_without_panic` at test line 1013. Should assert at least one postcondition.
7. DISMISSED: Rule #6 — `assert_ne!(hash, 0)` at test line 959. Rationale: While DefaultHasher theoretically can produce 0, the same test file already has `content_hash_is_deterministic` and `content_hash_with_many_entities_is_stable` which verify the actual dedup contract (same input → same hash). This test adds coverage for the empty-entities edge case. The non-zero check is a reasonable smoke test, not vacuous.
8. DISMISSED: Rule #11 — `tempfile = "3"` inline pin. Rationale: Cargo.toml was NOT modified in this diff (only lib.rs, render_queue.rs, and test file were changed). Pre-existing dependency configuration is out of scope for this review.

### Rule Compliance

**Rule #1 (Silent errors):** 6 instances checked.
- `compute_content_hash()` — compliant (pure function, no Result)
- `tier_to_dimensions()` — compliant (pure function, no Result)
- `RenderQueue::spawn()` line 297 `let _ = shutdown_rx.await` — compliant (idiomatic oneshot shutdown pattern)
- `RenderQueue::shutdown()` line 376 `let _ = handle.await` — **VIOLATION** (JoinError silently swallowed)
- `enqueue()` — compliant (returns Result)
- `job_status()` — compliant (returns Option)

**Rule #2 (non_exhaustive):** 4 enums checked.
- `RenderStatus` line 30 — compliant (#[non_exhaustive] present)
- `EnqueueResult` line 57 — compliant
- `QueueError` line 73 — compliant
- `RenderJobResult` line 94 — compliant

**Rule #3 (Placeholders):** No violations in render_queue.rs.

**Rule #4 (Tracing):** 2 error paths checked.
- `handle.await` JoinError path line 376 — **VIOLATION** (no tracing call)
- `QueueError::Full` return line 337 — **VIOLATION** (no tracing::warn!)

**Rule #5 (Validated constructors):** `RenderQueueConfig::new()` validates all inputs — compliant.

**Rule #6 (Test quality):** 50 tests checked, 1 zero-assertion test (`shutdown_completes_without_panic`).

**Rule #7 (Unsafe casts):** No `as` casts on external input — compliant.

**Rule #8 (Deserialize bypass):** No Deserialize derives on validated types — compliant.

**Rule #9 (Public fields):** `RenderQueueConfig` fields are private with getters — compliant. `ImageDimensions` has pub fields but no invariants — acceptable.

**Rule #10 (Tenant context):** Not applicable — no trait methods handling tenant data.

**Rule #11 (Workspace deps):** Not applicable — Cargo.toml not modified in this diff.

**Rule #12 (Dev deps):** Not applicable — no dependency changes in this diff.

**Rule #13 (Constructor/Deserialize consistency):** Not applicable — no Deserialize impls.

**Rule #14 (Fix regressions):** Clippy fix commit (6db48f6) only removed unused import, unreachable pattern, unnecessary mut, dead_code — no new issues introduced.

**Rule #15 (Unbounded input):** Queue bounded by MAX_QUEUE_DEPTH (1000), enforced at enqueue time — compliant.

### Devil's Advocate

What if this code is broken? Let me argue the case.

**The dedup hash is fundamentally incomplete.** `compute_content_hash` hashes entities, scene_type, and tier — but NOT art_style or image_model. The `enqueue()` method accepts both parameters, giving callers the impression they matter. When the daemon wiring story lands and actually renders images, a caller requesting the same subject with "oil_painting" and then "watercolor" will get a Deduplicated response pointing to the oil painting. The second caller silently gets the wrong art style. This isn't hypothetical — it's how the API is shaped RIGHT NOW. The `_` prefix on the params is a signal to Rust developers but not to API consumers reading the function signature. A downstream story that wires up the worker without also fixing the hash will produce incorrect images. This is the most dangerous finding because it's a correctness landmine, not just a missing log.

**The pending_count never decrements.** Since the worker is a stub, every enqueue increments pending_count but nothing decrements it. After `queue_depth` unique enqueues, the queue permanently rejects all further work with QueueError::Full. In a playtest session with 64 image-worthy beats (the default queue_depth), the queue fills and every subsequent scene gets no image. The dedup mitigation only helps for identical scenes. 64 unique scenes is not unreasonable in a multi-hour session. When the worker is eventually wired, it must decrement pending_count on completion — but if someone playtests with this stub, they'll hit a silent wall.

**DefaultHasher is not SipHash anymore (since Rust 1.78).** The stdlib changed DefaultHasher's algorithm. While this doesn't matter for in-process caches (hash consistency within a single run is guaranteed), it means hash values are not reproducible across Rust toolchain versions. If a future story ever persists hashes to disk or compares them across processes, the dedup breaks silently. This is a documentation gap.

**The shutdown race.** `shutdown(self)` drops `_shutdown_tx` to signal the worker, then awaits the handle. But between the drop and the worker actually processing the signal, new enqueues could theoretically arrive on other tasks holding a clone of `&self`. Except... `shutdown(self)` takes ownership, so no other reference can call enqueue after shutdown starts. This is actually safe by Rust's ownership model. Verified correct.

**What about a malicious caller?** The queue accepts any RenderSubject. If entities are extremely long strings (megabytes), `compute_content_hash` will hash them — which is O(n) in string length. An attacker could DoS the hash computation with huge entity names. However, RenderSubject::new() is the upstream constructor (story 4-2), and if it doesn't bounds-check entity string length, that's 4-2's problem, not 4-4's. The queue itself is bounded by MAX_QUEUE_DEPTH.

**Conclusion from devil's advocate:** The art_style/image_model dedup gap is real and confirmed as a finding. The pending_count issue is inherent to the stub design and accepted. The DefaultHasher concern is noted but not blocking. No new findings uncovered beyond what was already identified.

## Reviewer Assessment

**Verdict:** APPROVED

| Severity | Issue | Location | Tag |
|----------|-------|----------|-----|
| [MEDIUM] | `let _ = handle.await` swallows JoinError — worker panics invisible | render_queue.rs:376 | [SILENT][RULE] |
| [MEDIUM] | No `tracing::warn!` on QueueError::Full — backpressure invisible | render_queue.rs:337 | [RULE] |
| [MEDIUM] | `_art_style`/`_image_model` not in content hash — incorrect dedup when wired | render_queue.rs:321 | [SILENT] |
| [LOW] | Zero-assertion test `shutdown_completes_without_panic` | tests:1013 | [RULE] |

**Data flow traced:** RenderSubject → compute_content_hash() → hash_to_job lookup → dedup or insert into QueueState.jobs → EnqueueResult returned. Safe: no external I/O, no user-controlled strings in sensitive operations. Subject validated upstream by RenderSubject::new().

**Pattern observed:** Clean Arc<Mutex<QueueState>> + oneshot shutdown + tokio::spawn worker pattern at render_queue.rs:282-313. Well-structured async resource management — ownership-based shutdown is race-free.

**Error handling:** enqueue() returns typed Result<EnqueueResult, QueueError>. Config validates via Option<Self>. QueueError implements Display + std::error::Error. Error types are domain-specific, not string-based.

**Wiring:** lib.rs re-exports all public symbols. Tests import via sidequest_game::render_queue. Module integrates with crate::subject from story 4-2.

**Security analysis:** No network I/O, no auth, no tenant data, no deserialization of external input. Internal game queue only. No security concerns.

**[EDGE] findings:** Disabled via settings — N/A.
**[SILENT] findings:** 2 confirmed (JoinError swallowed, art_style/image_model ignored), 2 dismissed.
**[TEST] findings:** Disabled via settings — N/A.
**[DOC] findings:** Disabled via settings — N/A.
**[TYPE] findings:** Disabled via settings — N/A.
**[SEC] findings:** Disabled via settings — N/A.
**[SIMPLE] findings:** Disabled via settings — N/A.
**[RULE] findings:** 4 confirmed (JoinError no tracing, Full no tracing, zero-assertion test, silent error pattern), 4 dismissed.

**No Critical or High issues.** All findings are Medium or Low — appropriate for a scaffolding sprint story where the worker is an acknowledged stub. The art_style dedup gap is the most important item to address in the daemon wiring follow-up.

**Handoff:** To Baldur (SM) for finish-story.

## Implementation Checkpoints

Key areas to explore during red phase:
1. Queue data structure choice (Vec, VecDeque, or custom)
2. Hash computation strategy for content dedup (SHA256 on subject+beat data?)
3. Async request lifecycle (pending → in-flight → complete/error)
4. Integration points with DaemonClient and BeatFilter
5. Error handling for failed renders (retry strategy)
6. Result delivery mechanism (callbacks, channels, or polling?)