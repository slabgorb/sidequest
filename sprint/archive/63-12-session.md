---
story_id: "63-12"
jira_key: "N/A"
epic: "63"
workflow: "tdd"
---

# Story 63-12: Terminal em CSS renders --em-color instead of --accent

## Story Details

- **ID:** 63-12
- **Epic:** 63 (Reference pages v3 — chrome + wiki-like anchor links)
- **Jira Key:** N/A
- **Workflow:** tdd
- **Stack Parent:** none
- **Repos:** sidequest-ui
- **Branch:** feat/63-12-terminal-em-accent-channel

## Technical Context

The SideQuest terminal archetype (neon_dystopia, space_opera genres) uses a two-channel emphasis system for narration body text:

- `<em>` tags render on the **accent channel** — secondary bright highlight (neon green, #39FF14 equivalent)
- `<strong>` tags render on the **primary channel** — main cyan glow (#00FFFF equivalent)

This distinction provides visual separation and tonal identity: emphasis text (clue-bearing object labels, proper nouns, stressed words) glows in accent green, while strong text (narrator emphasis, mechanical resolution) glows in primary cyan.

**Current Bug:** `[data-archetype="terminal"] .narr-text em` renders `color: var(--em-color)` (hardcoded #FFD976, a warm yellow sibling). This violates the two-channel identity and tests expect accent. The `--em-color` variable was likely a fallback when genre theme delivery was fragile; theme injection now works correctly (ADR-079).

**Authoritative Source:** The test suite `src/__tests__/chrome-archetype-css.test.ts` lines 263–302 ("terminal emphasis two-channel identity") encodes the correct design. The three test cases are:
1. `em` renders on accent channel (`var(--accent)`)
2. `strong` renders on primary channel (`var(--primary)`)
3. em and strong are distinct channels (accent ≠ primary)

## Acceptance Criteria

- [x] RED: Both tests fail (test 1: em color is --em-color, not --accent; test 3: emColor resolves undefined)
- [ ] FIX: Update CSS `[data-archetype="terminal"] .narr-text em` color from `var(--em-color)` to `var(--accent)`
- [ ] GREEN: All 35 chrome archetype tests pass (33 passing + 2 previously failing)
- [ ] Verify em and strong channels are distinct in the CSS (accent ≠ primary)
- [ ] Document the two-channel design decision in a code comment on the `em` rule

## Workflow Tracking

**Workflow:** tdd  
**Phase:** red  
**Phase Started:** 2026-05-27T00:30:53Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-26 | 2026-05-27T00:30:53Z | 24h 30m |
| red | 2026-05-27T00:30:53Z | - | - |

## Sm Assessment

**Setup Complete:** Yes
**Story:** 63-12 — Terminal em CSS renders `--em-color` instead of `--accent` (chrome archetype)
**Repos:** sidequest-ui (gitflow, base `develop`)
**Branch:** feat/63-12-terminal-em-accent-channel (created in sidequest-ui off develop)
**Workflow:** tdd (phased) → next phase `red`, owned by TEA

**RED state:** Pre-existing. 2 failing tests in `sidequest-ui/src/__tests__/chrome-archetype-css.test.ts` (lines 263–302, "terminal emphasis two-channel identity"). TEA should verify/confirm the RED rather than author it fresh.

**Technical approach:** Resolve the CSS/test drift at `sidequest-ui/src/styles/archetype-chrome.css:475`. `[data-archetype="terminal"] .narr-text em` currently renders `color: var(--em-color)`; the test expects `var(--accent)`. The em and strong channels must stay distinct (accent ≠ primary). The session Technical Context names the **test** as authoritative (em rides accent), but Dev/TEA should confirm that deliberately before flipping the variable — if the CSS was right and the test drifted, the fix lands on the other side.

**Jira:** N/A — this project never uses Jira (per project rule).

**Handoff:** To TEA (Radar) for the red phase.

## Delivery Findings

No upstream findings.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

No deviations to spec.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->