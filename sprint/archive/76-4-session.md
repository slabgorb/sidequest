---
story_id: "76-4"
jira_key: ""
epic: "76"
workflow: "trivial"
---
# Story 76-4: Harden embed text-too-large log against content leakage

## Story Details
- **ID:** 76-4
- **Jira Key:** (none — project does not use Jira)
- **Workflow:** trivial
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** trivial
**Repos:** sidequest-server
**Phase:** finish
**Phase Started:** 2026-06-03T12:07:12Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-03T12:01:22Z | 2026-06-03T12:01:22Z | 0m |

## Delivery Findings

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

No upstream findings.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No upstream findings.

### Reviewer (code review)
- No upstream findings.

## Design Deviations

No deviations yet.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec.

### Reviewer (audit)
- **Dev: "No deviations from spec."** → ✓ ACCEPTED by Reviewer: the diff is exactly the scoped change (two `exc` → `type(exc).__name__` swaps on the text_too_large path); nothing diverges from the story title/AC. No undocumented deviations spotted — format strings, log levels, and control flow are byte-for-byte unchanged apart from the single interpolated argument at each site.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/game/entity_embedding.py` - text_too_large warning now logs `type(exc).__name__` instead of the `exc` object (line ~129)
- `sidequest/game/lore_embedding.py` - text_too_large warning now logs `type(exc).__name__` instead of the `exc` object (line ~230)

**Premise check:** Both files still logged the exception OBJECT before this change (neither was already hardened by a sibling story). Both required the fix.

**Tests:** 38/38 passing (GREEN) — `tests/game/test_lore_embedding.py` + `tests/game/test_entity_sync.py`, run with both DB env vars set (0 skipped). No test asserted on the old log-object form (counters only), so no test updates were needed.

**Branch:** feat/76-4-log-exc-type-not-value (pushed)

**Handoff:** To next phase (review)

## Subagent Results

Per `workflow.reviewer_subagents` settings, only `preflight` is enabled for this trivial
workflow; the eight diff-based specialists are disabled by project configuration. Disabled
rows are pre-filled as Skipped/disabled per the reviewer protocol. The reviewer covered each
disabled specialist's domain directly against the 4-line diff (recorded in the Reviewer
Assessment with the corresponding dispatch tag).

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — ruff check + ruff format --check clean on both files; 38/38 tests pass (0 skipped, DB env set) |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings (reviewer covered domain directly — see [EDGE] observation) |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings (reviewer covered domain directly — see [SILENT] observation) |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings (reviewer covered domain directly — see [TEST] observation) |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings (reviewer covered domain directly — see [DOC] observation) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings (reviewer covered domain directly — see [TYPE] observation) |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings (reviewer covered domain directly — see [SEC] observation) |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings (reviewer covered domain directly — see [SIMPLE] observation) |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings (reviewer covered domain directly — see [RULE] observation + Rule Compliance) |

**All received:** Yes (1 enabled subagent returned clean; 8 disabled via settings)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred

## Reviewer Assessment

**Verdict:** APPROVED

This is a two-site, single-token defense-in-depth change. At each `except ValueError as exc`
block on the embed "text too large" path, the warning's interpolated argument changed from the
exception object `exc` to `type(exc).__name__`. The `%s` format string, the placeholder/arg
count (3 args for 3 `%`-specifiers), the `logger.warning` level, and the trailing `continue`
control flow are all unchanged. The `exc` binding is still live (consumed by `type(exc).__name__`),
so no unused-variable lint.

**Data flow traced:** A `ValueError` raised by the daemon-client MAX_EMBED_BYTES guard →
caught at the `except ValueError as exc` block → previously the whole exception object (which,
if a content-bearing ValueError were ever introduced upstream, could carry card/fragment text
into log output) flowed into `logger.warning(... error=%s, exc)`. Now only the class name string
(`"ValueError"`) reaches the log line. The content size still appears as the integer `content_bytes`
(safe — a length, not the content). This is exactly the leak surface the story targets, closed at
both embed workers. Safe because the only thing that now reaches the formatter is a class-name
string with no embedded payload.

**Pattern observed:** identical hardening applied symmetrically at
`sidequest/game/entity_embedding.py:129` and `sidequest/game/lore_embedding.py:230` — consistency
is correct; both embed workers had the same latent exposure and both are now closed.

**Error handling:** failure path is unchanged — `mark_embedding_failed(...)` +
`result.failed_text_too_large += 1` + `span.add_event("embed_failed", ...)` + `continue` all
remain. The OTEL `embed_failed` event (reason=text_too_large, content_bytes) is untouched, so the
GM-panel observability of this path is preserved (no OTEL regression; per CLAUDE.md a log-message
tweak is explicitly "not needed" for new OTEL, and none was removed).

### Observations (≥5, with dispatch tags)

- `[VERIFIED]` Placeholder/argument arity intact — evidence: `entity_embedding.py:126-130` and
  `lore_embedding.py:226-231` each have three `%`-specifiers (`%s %d %s`) and three trailing
  args; swapping `exc`→`type(exc).__name__` keeps arity at 3, so no "not all arguments converted"
  / "TypeError during string formatting" risk.
- `[EDGE]` Boundary check — `type(exc).__name__` is total for any caught exception instance
  (every exception class has `__name__`); there is no input that makes it raise. The only objects
  reaching this line are `ValueError` (or subclass) instances from the `except ValueError as exc`
  filter, all of which have a `__name__`. No new failure mode introduced. No finding.
- `[SILENT]` No swallowed error — the change does not alter the catch/continue semantics; the
  failure is still recorded (counter + mark_failed + OTEL span) and logged at WARNING. The fix
  reduces what is logged, not whether it is logged. The story is itself an anti-silent-leak
  hardening. No finding.
- `[TEST]` Test coverage — `tests/game/test_lore_embedding.py::test_worker_failed_text_too_large_counter_matches_value_error_path`
  drives the exact ValueError branch and passes; no test asserted on the old `error=%s` object
  rendering (assertions are on counters/spans), so the change needed no test edit and breaks no
  assertion. A log-content assertion would be over-coupling for a cosmetic log argument; its
  absence is appropriate, not a gap. No finding.
- `[DOC]` Comment accuracy — the `# MAX_EMBED_BYTES guard ... too large` comments above each block
  remain accurate; they describe the guard, not the log argument. No stale/misleading comment
  introduced. No finding.
- `[TYPE]` Type design — `type(exc).__name__` yields `str`, matching the `%s` specifier; this is
  more type-honest than passing an arbitrary exception object to `%s` (which relied on `__str__`).
  No stringly-typed-API or unsafe-cast concern. No finding.
- `[SEC]` Security / info-leakage — this IS a security-hardening change: it removes a potential
  content-leakage-to-logs vector (defense-in-depth against a future content-bearing ValueError).
  `content_bytes` (an int length) is not sensitive. Net reduction in log info exposure. No finding.
- `[SIMPLE]` Simplicity — `type(exc).__name__` is the idiomatic, minimal way to log an exception
  class name without its payload; no over-engineering, no dead code, no simpler alternative that
  also closes the leak. No finding.
- `[RULE]` Project-rule compliance — see Rule Compliance section below; no rule violated. No OTEL
  addition required (CLAUDE.md: cosmetic log-message tweaks are explicitly exempt, and no OTEL was
  removed). No finding.

### Rule Compliance

Rules enumerated from CLAUDE.md (server) / SOUL.md and judged against every element of the diff:

- **No Silent Fallbacks** — COMPLIANT. The failure still fails loudly: WARNING log + OTEL
  `embed_failed` event + `failed_text_too_large` counter. Nothing is silently swallowed; only the
  log *argument* narrowed from object to class name.
- **No Stubbing / No half-wired features** — COMPLIANT. No stub, no placeholder; both real
  production embed workers changed end-to-end.
- **OTEL Observability Principle** — COMPLIANT / N/A. Both `span.add_event("embed_failed", ...)`
  calls are untouched, so subsystem observability is intact. CLAUDE.md explicitly states OTEL is
  "Not needed for: Cosmetic changes (label rewording, log message tweaks)" — this is exactly such a
  tweak, and crucially it *removes* nothing from OTEL.
- **No Source-Text Wiring Tests** — COMPLIANT. No test was added that greps source; existing
  behavior/counter tests cover the path.
- **Backend Language (Python/FastAPI per ADR-082)** — COMPLIANT. Pure Python edit.
- **Personal-project rules (no Jira / slabgorb only)** — COMPLIANT. No Jira interaction; branch on
  slabgorb/sidequest-server.

Every changed line falls under these rules and each is compliant. No rule-matching finding exists
to confirm or dismiss.

### Devil's Advocate

Let me try to break this. *Claim 1: the log line will now crash.* For that, `type(exc).__name__`
would have to raise or mis-format. It cannot — `type()` is a builtin total over all objects,
`__name__` exists on every class object, and the result is a `str` that satisfies the `%s`
specifier. The arg count (3) still matches the specifier count (3), so there is no deferred
"not all arguments converted during string formatting" exception that lazy `%`-logging would
otherwise raise only at emit time. *Claim 2: we lost diagnostic value a maintainer relied on.*
Marginally — a maintainer reading logs no longer sees the exception's message text. But the
intended ValueError on this path is the MAX_EMBED_BYTES guard, whose message would itself echo
sizes/content fragments; that message is precisely the leakage we are removing, and the still-logged
integer `content_bytes` preserves the one genuinely useful diagnostic (how oversized). So the
diagnostic loss is the leak, by design. *Claim 3: an attacker forces content into logs another
way.* The only remaining interpolated values on this line are `card_id`/`frag_id` (identifiers,
not free content) and `content_bytes` (an int) — neither carries fragment/card text. *Claim 4:
the `exc` binding is now dead and ruff should complain / a future edit will drop the `as exc` and
break this.* `exc` is still read by `type(exc).__name__`, so it is live now and ruff confirms clean;
a hypothetical future edit is out of scope. *Claim 5: asymmetry — one file fixed, one missed.* Both
files are changed identically; grep confirmed these were the only two text-too-large log sites and
both now log the class name. *Claim 6: a confused user/operator misreads "error=ValueError" as a new
bug.* "ValueError" is the same class that was already being str-rendered before (its `str()` for the
guard would have begun similarly); the operator-facing meaning ("oversized text rejected") is
unchanged and `reason=text_too_large` is still on the OTEL event. I cannot construct a real defect.
The change is correct, minimal, symmetric, and strictly reduces log exposure.

**Handoff:** To SM for finish-story