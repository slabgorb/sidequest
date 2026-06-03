---
parent: context-epic-64.md
workflow: trivial
---

# Story 64-17: Tidy two pre-existing weak/stale tests in test_audit_namegen_corpora.py (ADR-091 namegen audit)

> **Bundled delivery.** Co-delivered with 64-16 under a single driver session
> (`REPOS=content,server`). 64-17 is the **server** test tidy (this doc); 64-16 is the
> **content** corpus expansion (`context-story-64-16.md`). Two PRs: server→develop,
> content→develop. Both are p3 trivial 1-pointers, fallout from 64-7 (found by Reviewer
> round-2, out-of-diff, deferred).

## Business Context

Two tests in the namegen corpus-audit suite are weak or stale — they pass, but they don't
prove (or they misdescribe) what they claim. Per the epic's goal of making the
content-validation layer *trustworthy*, a test that asserts the wrong thing is a latent gap:
it can stay green while the behavior it's supposed to guard regresses. This story tightens both
so the audit suite means what it says. No production code changes — test-file hygiene only.

## Technical Guardrails

**File (server repo):** `sidequest-server/tests/scripts/test_audit_namegen_corpora.py`

**The two targets:**
- **(a)** `test_audit_synthetic_ample_corpus_exits_zero` (~:315) — asserts `rc=0` and that a
  name is present, but **not** that the corpus is classified **OK**. Add a co-located assertion
  that the audit output carries the OK classification row for the corpus, so the test actually
  pins the OK path (not just a zero exit + non-empty name).
- **(b)** `test_audit_live_tree_exits_zero_after_corpus_expansion` (~:74) — its **docstring**
  claims the pre-fix failure mode was THIN, but the real mode is **MISSING / rc=1**. Refresh the
  docstring/note to describe the actual prior failure (MISSING, rc=1). Behavior of the test is
  fine; only the note is stale.

**Patterns to follow:**
- Tighten assertions against the audit's **actual output classification** (OK row), mirroring how
  the sibling tests inspect the report — don't assert on incidental strings.
- For (b), this is a comment/docstring correction; do not weaken or rewrite the test logic.

**What NOT to touch:**
- `scripts/audit_namegen_corpora.py` and `thresholds.py` — the audit/production code is correct;
  this is test-side only.
- The corpus files (that's 64-16) or any other test.

## Scope Boundaries

**In scope:**
- (a) Add an OK-classification assertion to `test_audit_synthetic_ample_corpus_exits_zero`.
- (b) Correct the stale docstring in `test_audit_live_tree_exits_zero_after_corpus_expansion`
  (THIN → MISSING/rc=1).

**Out of scope:**
- Any production/audit-script change; corpus content (64-16); other tests in the file.

## AC Context

1. **(a) OK-row pinned.** `test_audit_synthetic_ample_corpus_exits_zero` now asserts the audit
   classifies the synthetic corpus as **OK** (a co-located classification check), in addition to
   the existing `rc=0` + name-present assertions.
2. **(b) Docstring accurate.** `test_audit_live_tree_exits_zero_after_corpus_expansion`'s
   docstring/note describes the real pre-fix failure mode (MISSING, rc=1), not THIN.
3. **Suite green.** Full `just server-test` passes; the two edited tests pass with their
   strengthened/corrected forms.

## Assumptions

- The audit report exposes a per-corpus classification (OK/THIN/MISSING) the test can assert on
  in the same way neighboring tests already inspect rows; if the OK signal isn't readily
  assertable, surfacing it minimally is in scope — log a deviation if it turns out larger.
