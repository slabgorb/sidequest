---
parent: context-epic-57.md
workflow: tdd
---

# Story 57-3: Promote static genre prose into Stable cached zone

## Business Context

Four genre prose sections — `genre_extraction`, `genre_keeper_monologue`, `genre_town`, `genre_chargen` — register on **every** narrator turn at `orchestrator.py:1265–1385` but live in `SectionBucket.User` because their section names are not in the `STABLE_SECTION_NAMES` allowlist at `prompt_framework/bucket.py:28–41`. Per ADR-101 Phase D, `SectionBucket.User` content rides in the per-turn user message — uncached. Each section is sourced from a `prompts.yaml` block that is session-static (changes only when the genre pack or world changes, which forces a new session anyway).

This is **cacheable content sitting in the uncached path**. Promoting these four section names into the allowlist moves them to the `system=` array with `cache_control`, paying the cache-write cost once per session and the cache-read cost on every subsequent turn. The net effect is direct token savings on every narrator turn after the first.

ADR-112 ratifies this decision and *also* documents two sections that must **not** be promoted: `genre_combat_voice` and `genre_chase_voice`. Both are conditional (gated on `context.in_combat` / `context.in_chase`), and their flip-on/flip-off pattern across combat boundaries would thrash the prompt cache — paying cache-write costs more than once per session. The mutability rubric in ADR-112 §Decision is the discriminator: "always-fire + session-static" promotes; "conditional" defers.

## Technical Guardrails

**Source ADR:** `docs/adr/112-genre-prose-stable-cache-promotion.md` — read in full before starting. Specifically:

- §Context — the allowlist's current 10 entries and the six unallowlisted sections.
- §Decision — the four promotions and the two deferrals.
- §Mutability rubric — the discriminator for future authors.
- §Note on `narrator_vocabulary` invariant audit — a flagged follow-up; **not in scope for this story** but worth reading so you don't accidentally widen scope.

**Primary edit site:** `sidequest-server/sidequest/agents/prompt_framework/bucket.py`, the `STABLE_SECTION_NAMES` set at lines 28–41. Add four entries:

```python
"genre_extraction",
"genre_keeper_monologue",
"genre_town",
"genre_chargen",
```

**Do NOT add:** `genre_combat_voice`, `genre_chase_voice`. ADR-112 §Defer documents the cache-thrash rationale.

**Registration sites to verify (read-only):** `orchestrator.py:1265–1385`. The registrations themselves do **not** change — only the bucket classifier output changes. The bucket is read from `default_bucket_for_section(section_name)` at registration time.

**Pattern to follow:** This is identical in shape to the prior `narrator_vocabulary` promotion (already in the allowlist). Mirror its existence in tests and call sites.

**What NOT to touch:**

- Do not modify the four genre prose sections' content in `prompts.yaml` — content authoring is out of scope.
- Do not touch `orchestrator.py` registration sites — only the bucket classifier changes.
- Do not audit `narrator_vocabulary` for the dynamic-invariant question flagged in ADR-112 — that is a separate follow-up.
- Do not promote `genre_combat_voice` or `genre_chase_voice` even if "completing the set" feels natural. ADR-112 explicitly forbids it for this story.

## Scope Boundaries

**In scope:**
- Add four section names to `STABLE_SECTION_NAMES`.
- Add a test asserting each of the four promoted sections returns `SectionBucket.System` from `default_bucket_for_section`.
- Add a test asserting each of the two deferred sections returns `SectionBucket.User` from `default_bucket_for_section` (regression guard — proves we didn't over-promote).
- Add the ADR-112-mandated OTEL evidence: a one-shot integration test (or playtest hook) capturing `cache_creation_input_tokens` and `cache_read_input_tokens` before/after to verify the cache actually catches the promoted content.

**Out of scope:**
- The `narrator_vocabulary` dynamic-invariant audit (separate follow-up per ADR-112).
- Promoting `genre_combat_voice` / `genre_chase_voice`.
- Editing genre prose content.
- Modifying the registration sites at `orchestrator.py:1265–1385`.
- A forward-applicable allowlist validator (ADR-112 §Forward-applicable validator notes it as "not blocking, flagged" — out of scope for this story).

## AC Context

1. **Allowlist contains four new entries.** `grep -A1 STABLE_SECTION_NAMES sidequest-server/sidequest/agents/prompt_framework/bucket.py` shows the four added names: `genre_extraction`, `genre_keeper_monologue`, `genre_town`, `genre_chargen`. The two deferred names are absent.
2. **Bucket classifier tests pass.** Tests assert `default_bucket_for_section("genre_extraction") == SectionBucket.System` (and analogous for the other three). Tests also assert `default_bucket_for_section("genre_combat_voice") == SectionBucket.User` and `default_bucket_for_section("genre_chase_voice") == SectionBucket.User`.
3. **No registration-site changes.** `git diff sidequest-server/sidequest/agents/orchestrator.py` is empty for this story.
4. **OTEL cache delta visible.** A playtest run (or a deterministic integration test) emits `cache_creation_input_tokens` on turn 1 and `cache_read_input_tokens > 0` on turn 2 for the promoted sections. If the test cannot directly assert the API response's cache metadata, fall back to asserting that the `system=` array passed to the SDK call contains the promoted sections (proxy evidence).
5. **Existing tests stay green.** Full `just server-test` runs green; no regressions in `prompt_framework` or `agents/orchestrator` test modules.

## Assumptions

- ADR-101 Phase D Stable-zone caching is **live** in `sidequest-server`. If the `cache_control` plumbing is still partial (per ADR-101's `implementation-status: partial`), the promotion still ships — the cache writes are the SDK's job and will start working when the SDK plumbing completes. Log a Design Deviation if the bucket → `system=` array assembly is not actually consuming `STABLE_SECTION_NAMES` membership.
- The `prompts.yaml` `gp.extraction` / `gp.keeper_monologue` / `gp.town` / `gp.chargen` blocks are session-static — they don't mutate at runtime. ADR-112 documented this; this story assumes it. If implementation finds runtime mutation, log a Design Deviation immediately (it would mean ADR-112's mutability rubric needs sharpening).
- Cache-thrash for conditional sections is real and worth deferring. If the implementer believes ADR-112 is wrong about `genre_combat_voice` / `genre_chase_voice`, that goes in a new ADR amendment, not in this story.
