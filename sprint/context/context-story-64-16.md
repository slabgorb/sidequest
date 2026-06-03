---
parent: context-epic-64.md
workflow: trivial
---

# Story 64-16: Expand polynesian.txt + georgian.txt shared corpora for WARN headroom (ADR-091 namegen audit)

> **Bundled delivery.** This session is the driver for the 64-16 + 64-17 pair
> (`REPOS=content,server`). 64-16 is the **content** change (this doc); 64-17 is the
> co-delivered **server** test tidy (`context-story-64-17.md`). Two PRs result:
> content→develop, server→develop. Both are p3 trivial 1-pointers, fallout from 64-7.

## Business Context

The namegen corpus audit (`scripts/audit_namegen_corpora.py`) classifies each culture corpus
as OK / THIN / MISSING against `WARN_BELOW_WORDS=1000`. Two shared corpora sit on a knife's
edge — `polynesian.txt` = 1005 words and `georgian.txt` = 1004 words via `count_words` — only
~5 words above the WARN floor. Any future trim (a dedup pass, a typo fix that drops a line)
flips them to THIN and breaks `test_audit_live_tree_no_named_corpora_left_thin_post_expansion`.
This story adds modest headroom so the corpora can absorb normal churn without tripping the
audit. It's pure quality-of-life hardening for the content-validation gate the epic exists to
make trustworthy.

## Technical Guardrails

**Files (content repo):**
- `sidequest-content/corpus/shared/polynesian.txt` — currently 1005 words.
- `sidequest-content/corpus/shared/georgian.txt` — currently 1004 words.

**Threshold authority (server repo, read-only here):**
- `sidequest-server/sidequest/genre/names/thresholds.py` — `WARN_BELOW_WORDS = 1000`,
  `FAIL_BELOW_WORDS = 200`, and `count_words()` (the canonical counter — strips blanks/comments,
  so add real word lines, not padding).

**Patterns to follow:**
- Add **genuine, culturally-plausible** words to each corpus (these feed lookback-2 Markov name
  generation — junk lines degrade name quality). Polynesian and Georgian phonotactics
  respectively; consult existing entries for register and avoid duplicates (dedup would erase
  the very headroom we're adding).
- Target comfortable headroom (e.g. ~1050+ each) so a small future trim can't reach 1000.

**What NOT to touch:**
- The threshold constants or `count_words` — consume them, don't change the bar.
- Any other corpus file; scope is exactly these two.

## Scope Boundaries

**In scope:**
- Append modest, real-word headroom to `polynesian.txt` and `georgian.txt` (both comfortably
  above `WARN_BELOW_WORDS` post-change).

**Out of scope:**
- Other corpora, the audit script, the threshold module (64-17 handles the server-side test tidy).
- Reworking existing entries / dedup passes.

## AC Context

1. **Headroom added.** After the change, `count_words` for both `polynesian.txt` and
   `georgian.txt` sits comfortably above 1000 (not ~1004/1005) — enough that a small future
   trim won't flip them THIN.
2. **Quality preserved.** Added lines are real, non-duplicate, phonotactically appropriate words
   for each culture (no padding, no placeholder tokens).
3. **Audit stays green.** The live-tree audit still classifies both as OK;
   `test_audit_live_tree_no_named_corpora_left_thin_post_expansion` passes.

## Assumptions

- `count_words` ≈ line count for these files (one word per line, blanks/comments stripped); the
  Dev should confirm via the actual counter rather than `wc -l` when verifying the AC.
- These shared corpora are referenced by multiple cultures via the corpus binding (ADR-091);
  adding words is additive and safe for all consumers.
