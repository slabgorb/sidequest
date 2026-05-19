---
parent: context-epic-57.md
workflow: trivial
---

# Story 57-2: Audit five empty narrator_prompts/*.md stubs (load-bearing bug check)

## Business Context

The token-reduction audit that birthed epic 57 flagged five tiny `narrator_prompts/*.md` files in `sidequest-server/sidequest/agents/narrator_prompts/`. Each is under 1 KB; the smallest (`identity.md`) is 210 bytes. The audit could not determine from filename alone whether they were:

1. Load-bearing — small but critical (e.g., a referral rule that prevents a known regression).
2. Deprecated — content moved elsewhere; the file is a leftover.
3. Empty stubs — placeholder for never-built features (CLAUDE.md "No Stubbing" violation).

The cost of *not* knowing is that nobody can confidently delete them, so the imports stay, the assembly stays, and the dead-code rot compounds. The cost of getting it wrong is a silent narrator regression (e.g., deleting `identity.md` and discovering at playtest that it was the prose declaring "you are the narrator, not the player"). This story is a one-pass audit that produces a delete-or-keep verdict per file with evidence, so a future story can act on it cleanly.

## Technical Guardrails

**Files under audit** (size in bytes from `ls`):

| File | Size | Hypothesis |
|---|---|---|
| `sidequest-server/sidequest/agents/narrator_prompts/identity.md` | 210 | likely load-bearing (root identity declaration) |
| `sidequest-server/sidequest/agents/narrator_prompts/referral_rule.md` | 324 | likely load-bearing (anti-leak rule) |
| `sidequest-server/sidequest/agents/narrator_prompts/consequences.md` | 398 | unclear |
| `sidequest-server/sidequest/agents/narrator_prompts/output_style.md` | 667 | unclear — may have been superseded by `output_only_sdk.md` |
| `sidequest-server/sidequest/agents/narrator_prompts/dialogue_rules.md` | 756 | unclear — may overlap with `narrator_dialogue` section |

**Evidence-gathering pattern:**

1. `grep -r "identity.md" sidequest-server/sidequest/` (and the other four filenames) — find every load site.
2. For each load site, trace what *section name* it registers as (the `prompt_framework` section name is what the bucket allowlist sees, not the filename).
3. For each section name, check whether `default_bucket_for_section` returns System (cached) or User (per-turn).
4. Diff against `narrator_prompts/output_only_sdk.md` (23 KB) and `narrator_prompts/output_only.md` (24 KB) — if the small file's content was absorbed into the SDK monolith, the small file is deprecated.

**What NOT to touch:**

- Do **not** edit `output_only_sdk.md` or `output_only.md` — they are the live SDK / legacy output-format files; out of scope for this audit.
- Do **not** rewrite content in any audited file. If it's load-bearing, leave it alone. The audit ships a verdict, not a rewrite.
- Do **not** delete files in this story even with a "delete" verdict — the deletion + import cleanup is a *separate* follow-up story, kept out so the audit's reviewable scope stays tiny.

## Scope Boundaries

**In scope:**
- Read all five files in full.
- For each file, grep for load sites in `sidequest-server/sidequest/`.
- For each file, classify load-bearing / deprecated / stub with a one-paragraph rationale per file.
- Write the audit verdict into the session file's "Audit Findings" subsection.
- File a follow-up story for any "delete" verdicts.

**Out of scope:**
- Editing any of the five files.
- Deleting any of the five files (follow-up story).
- Removing import statements (follow-up story).
- Auditing the two large `output_only*.md` files.
- Refactoring `prompt_framework/bucket.py` or `core.py`.

## AC Context

1. **Each of the five files has a verdict.** "load-bearing", "deprecated", or "empty stub". No file may be left "unclear" — if evidence is genuinely insufficient, the verdict is "load-bearing, do not delete" by default (CLAUDE.md "No Silent Fallbacks" — fail safe).
2. **Each verdict cites evidence.** Specifically: filename grep results showing import/load sites, and a one-sentence claim about whether the content is still consumed.
3. **Follow-up story exists for any non-load-bearing files.** If verdicts include "deprecated" or "empty stub", file a new story `57-N` (next ID) titled "Delete deprecated narrator_prompts stubs (per 57-2 audit)" with the files listed.
4. **No file modified.** `git diff --stat sidequest-server/sidequest/agents/narrator_prompts/` shows zero changes after the audit.

## Assumptions

- The five filenames listed are stable — assumed no `narrator_prompts/` reorganization happens mid-audit.
- The `output_only_sdk.md` / `output_only.md` distinction is the SDK vs. `claude -p` backend split (per ADR-101 and project memory `project_claude_p_no_reactive_tools.md`). If the audit reveals it's a different distinction, log a Design Deviation.
- The audit uses ripgrep / grep across `sidequest-server/sidequest/` only. Other repos (daemon, ui, content) are presumed not to load narrator prompt fragments — if they do, that's a Design Deviation worth surfacing because cross-repo prompt fragment loading would be its own architecture problem.
