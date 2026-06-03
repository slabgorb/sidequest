---
parent: context-epic-82.md
workflow: tdd
---

# Story 82-2: Verbosity/Vocabulary player controls — UI sliders + CONNECT plumb + TurnContext read (ADR-049)

## Business Context

ADR-049 lets players tune the narrator on two axes — how much it says (verbosity) and how
ornate the diction is (vocabulary). The prompt plumbing fires every turn, but no player can
actually change the setting: there are no controls, and the server hardcodes "standard" /
"literary" regardless of what a client sends. The promised tuning is inert. Wiring it lets
the table dial the narrator to its taste — a low-reading-tolerance player (Alex) can ask for
terser prose; a high-tolerance one (James) can ask for more — which is squarely a
playgroup-fit feature.

## Technical Guardrails

**Key files (navigate by symbol; 2026-06-03 anchors may drift):**
- `agents/orchestrator.py` — `_build_verbosity_section` / `_build_vocabulary_section` already fire; leave them.
- `server/session_helpers.py` (~:1167-1168) — `TurnContext` hardcodes `narrator_verbosity="standard"` / `narrator_vocabulary="literary"`; read from session/CONNECT instead.
- `handlers/connect.py` (~:1402-1403) — slug-resume passes None; populate from the stored/selected settings.
- `protocol/enums.py` — `NarratorVerbosity` has `default_for_player_count`; `NarratorVocabulary` does not — add it for parity.
- `sidequest-ui/src/types/protocol.ts` (~:128,131) — type aliases exist but no component uses them; add `VerbositySlider` / `VocabularySlider` (no such components today) and a CONNECT payload field.

**Patterns to follow:**
- The CONNECT payload is the transport for session-start preferences; extend it, don't add a side channel.
- Mirror the existing enum `default_for_player_count` pattern from `NarratorVerbosity`.

**What NOT to touch:**
- The prompt-section builders themselves (they work once fed a real value).

## Scope Boundaries

**In scope:**
- UI verbosity + vocabulary controls; selection rides the CONNECT payload.
- `TurnContext` reads the values from session/CONNECT; resume populates them.
- `NarratorVocabulary.default_for_player_count`.
- OTEL of active settings per turn; wiring test.

**Out of scope:**
- `/tone` axis system (82-1).
- Mid-session live re-tuning UI beyond what CONNECT carries (can be a follow-up if desired).

## AC Context

1. **Controls exist and transmit.** UI exposes verbosity + vocabulary controls; the selection
   is sent in the CONNECT payload.
2. **Server reads them.** `TurnContext` derives `narrator_verbosity` / `narrator_vocabulary`
   from the session/CONNECT payload, not hardcoded literals; slug-resume populates them
   (not None). Edge: missing payload falls back to `default_for_player_count`, not a silent
   literal.
3. **Enum parity.** `NarratorVocabulary` implements `default_for_player_count` and it is used
   for the default.
4. **OTEL + wiring test.** A watcher/OTEL event records the active verbosity+vocabulary per
   turn; a wiring test ties slider → CONNECT → `TurnContext` → prompt section and fails on
   current `develop` (hardcoded). `just server-test` + `just client-test` green.

## Assumptions

- The CONNECT handler is the right place to capture session-start preferences (it already
  carries genre/world binding).
- Persisting the chosen settings across resume is in scope via the existing session store;
  if it requires a schema change beyond a field, log a deviation.
