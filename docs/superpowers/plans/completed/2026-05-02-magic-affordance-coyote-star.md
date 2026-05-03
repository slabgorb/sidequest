# Magic Affordance for Coyote Star — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Sensitivities subsection to the Abilities tab of the character panel that names what coyote_star players are sensing — cryptic pre-bleed, expanded post-bleed — so future playtests actually invoke workings.

**Architecture:** Pure UI work in `sidequest-ui`. New component `SensitivitiesSection` mounted inside the existing `AbilitiesContent` in `CharacterPanel.tsx`. Reads `magicState.ledger` via the existing `getCharacterBars()` helper. Two states: pre-bleed (all character bars at `value === spec.starts_at_chargen`) and post-bleed (any bar drifted). Zero server changes; the existing `LedgerPanel` below the tabs remains the canonical bar surface.

**Tech Stack:** React 19, TypeScript, Vitest, @testing-library/react. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-05-02-magic-affordance-coyote-star-design.md`

**Repo:** `sidequest-ui` only. Default branch: `develop`. Branching strategy: gitflow (`feat/*`).

---

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `sidequest-ui/src/components/SensitivitiesSection.tsx` | Create | Pure presentational component. Two-state text; reads bars via `getCharacterBars`; returns `null` when `magicState == null` or no character bars exist. |
| `sidequest-ui/src/components/CharacterPanel.tsx` | Modify | Thread `magicState` + `character.name` into `AbilitiesContent`; mount `<SensitivitiesSection>` after the bullet list. |
| `sidequest-ui/src/components/__tests__/SensitivitiesSection.test.tsx` | Create | Three component-level wiring tests (pre-bleed / post-bleed / absent). |
| `sidequest-ui/src/__tests__/sensitivities-character-panel-wiring.test.tsx` | Create | One CharacterPanel-level wiring test confirming the section renders inside the Abilities tab when reached through `CharacterPanel`. |

Two test files: the component-level file lives next to the component (matches the `LedgerPanel.test.tsx` co-location pattern); the integration-level wiring test lives in the top-level `__tests__/` (matches `magic-confrontation-wiring.test.tsx`). The two-test-file split satisfies CLAUDE.md "every test suite needs a wiring test."

---

## Task 1: Branch setup

**Files:** none yet (branch only).

- [ ] **Step 1: Confirm clean working tree**

Run from the orchestrator root:

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui && git status -sb
```

Expected: `## develop...origin/develop` and no `M`/`A`/`??` lines. If dirty, stop and resolve before continuing.

- [ ] **Step 2: Confirm develop is up to date**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui && git fetch && git pull
```

Expected: "Already up to date" or fast-forward only.

- [ ] **Step 3: Create the feature branch**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui && git checkout -b feat/sensitivities-magic-affordance-coyote-star
```

Expected: `Switched to a new branch 'feat/sensitivities-magic-affordance-coyote-star'`.

---

## Task 2: Write the failing pre-bleed test

**Files:**
- Create: `sidequest-ui/src/components/__tests__/SensitivitiesSection.test.tsx`

- [ ] **Step 1: Write the test file with the pre-bleed case only**

Create `sidequest-ui/src/components/__tests__/SensitivitiesSection.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SensitivitiesSection } from "../SensitivitiesSection";
import type { MagicState, LedgerBar, LedgerBarSpec } from "../../types/magic";

function makeBar(
  id: string,
  scope: "character" | "world",
  value: number,
  startsAtChargen: number,
): [string, LedgerBar] {
  const spec: LedgerBarSpec = {
    id,
    scope,
    direction: scope === "world" ? "up" : "down",
    range: [0.0, 1.0],
    decay_per_session: 0.0,
    starts_at_chargen: startsAtChargen,
  };
  const owner = scope === "world" ? "coyote_star" : "Itchy";
  return [`${scope}|${owner}|${id}`, { spec, value }];
}

const baseConfig = {
  world_slug: "coyote_star",
  genre_slug: "space_opera",
  allowed_sources: ["innate", "item_based"],
  active_plugins: ["innate_v1", "item_legacy_v1"],
  intensity: 0.25,
  world_knowledge: { primary: "classified" as const, local_register: "folkloric" as const },
  visibility: {},
  hard_limits: [],
  cost_types: ["sanity", "notice"],
  ledger_bars: [],
  can_build_caster: false,
  can_build_item_user: true,
  narrator_register: "",
};

describe("SensitivitiesSection", () => {
  it("renders cryptic pre-bleed copy when all character bars are at starts_at_chargen", () => {
    const ledger = Object.fromEntries([
      makeBar("sanity", "character", 1.0, 1.0),
      makeBar("notice", "character", 0.0, 0.0),
      makeBar("vitality", "character", 0.5, 0.5),
    ]);
    const state: MagicState = { config: baseConfig, ledger, working_log: [] };

    render(<SensitivitiesSection magicState={state} characterId="Itchy" />);

    expect(screen.getByRole("heading", { name: /sensitivities/i })).toBeInTheDocument();
    expect(screen.getByText(/you hear what the others don't\. sometimes\./i)).toBeInTheDocument();
    expect(screen.queryByText(/something stirred/i)).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the test, confirm it fails**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui && npx vitest run src/components/__tests__/SensitivitiesSection.test.tsx
```

Expected: FAIL — module `../SensitivitiesSection` cannot be resolved (component does not exist yet).

- [ ] **Step 3: Commit the failing test**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui && \
  git add src/components/__tests__/SensitivitiesSection.test.tsx && \
  git commit -m "test(magic): add failing pre-bleed test for SensitivitiesSection"
```

---

## Task 3: Make pre-bleed test pass — minimal SensitivitiesSection

**Files:**
- Create: `sidequest-ui/src/components/SensitivitiesSection.tsx`

- [ ] **Step 1: Write the component**

Create `sidequest-ui/src/components/SensitivitiesSection.tsx`:

```tsx
import { getCharacterBars, type LedgerBar, type MagicState } from "../types/magic";

interface SensitivitiesSectionProps {
  magicState: MagicState | null;
  characterId: string;
}

const PRE_BLEED_COPY = "You hear what the others don't. Sometimes.";

function anyBarDrifted(bars: LedgerBar[]): boolean {
  return bars.some((b) => b.value !== b.spec.starts_at_chargen);
}

/**
 * Names the player's coyote_star "Reader" capacity on the Abilities tab.
 *
 * The world's microbleeds (mug jitters, dust profile carries after-rain,
 * the hum that isn't yours) are easy to read as atmosphere — Keith's own
 * playtest confirmed they vanish unnamed. This subsection makes the
 * capacity legible without giving the player a verb list (per CLAUDE.md
 * Zork: no closed option set in the input path). Two states:
 *
 * - Pre-bleed (all character bars at starts_at_chargen): one cryptic line.
 * - Post-bleed (any bar drifted): expanded framing + cost vocabulary.
 *
 * Returns null when there are no character bars to interpret — covers
 * other genres + pre-magic worlds with no extra gating.
 */
export function SensitivitiesSection({
  magicState,
  characterId,
}: SensitivitiesSectionProps) {
  if (magicState == null) return null;
  const bars = getCharacterBars(magicState, characterId);
  if (bars.length === 0) return null;

  const drifted = anyBarDrifted(bars);

  return (
    <section className="sensitivities-section mt-4 pt-3 border-t border-border/30">
      <h3 className="text-sm italic font-semibold mb-2 text-muted-foreground">
        Sensitivities
      </h3>
      {drifted ? null : (
        <p className="text-sm italic text-muted-foreground/80">{PRE_BLEED_COPY}</p>
      )}
    </section>
  );
}
```

- [ ] **Step 2: Run the test, confirm it passes**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui && npx vitest run src/components/__tests__/SensitivitiesSection.test.tsx
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui && \
  git add src/components/SensitivitiesSection.tsx && \
  git commit -m "feat(magic): SensitivitiesSection — pre-bleed branch"
```

---

## Task 4: Add the failing post-bleed test

**Files:**
- Modify: `sidequest-ui/src/components/__tests__/SensitivitiesSection.test.tsx`

- [ ] **Step 1: Append the post-bleed test inside the existing `describe`**

Add this `it` block immediately after the pre-bleed test in the existing file:

```tsx
  it("renders expanded post-bleed copy when any character bar has drifted from starts_at_chargen", () => {
    const ledger = Object.fromEntries([
      // sanity drifted: starts at 1.0, now 0.95 (microbleed cost applied)
      makeBar("sanity", "character", 0.95, 1.0),
      makeBar("notice", "character", 0.0, 0.0),
      makeBar("vitality", "character", 0.5, 0.5),
    ]);
    const state: MagicState = { config: baseConfig, ledger, working_log: [] };

    render(<SensitivitiesSection magicState={state} characterId="Itchy" />);

    expect(screen.getByRole("heading", { name: /sensitivities/i })).toBeInTheDocument();
    expect(screen.getByText(/something stirred\. you felt it\./i)).toBeInTheDocument();
    expect(screen.getByText(/sanity is the price of staying open/i)).toBeInTheDocument();
    expect(screen.getByText(/your own words, in the input bar/i)).toBeInTheDocument();
    expect(
      screen.queryByText(/you hear what the others don't\. sometimes\./i),
    ).not.toBeInTheDocument();
  });
```

- [ ] **Step 2: Run the test, confirm it fails**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui && npx vitest run src/components/__tests__/SensitivitiesSection.test.tsx
```

Expected: FAIL — "Unable to find an element with the text: /something stirred. you felt it./i" (the post-bleed branch returns `null` today).

- [ ] **Step 3: Commit the failing test**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui && \
  git add src/components/__tests__/SensitivitiesSection.test.tsx && \
  git commit -m "test(magic): add failing post-bleed test for SensitivitiesSection"
```

---

## Task 5: Make post-bleed test pass — implement post-bleed copy

**Files:**
- Modify: `sidequest-ui/src/components/SensitivitiesSection.tsx`

- [ ] **Step 1: Replace the post-bleed branch's `null` with the expanded copy**

Open `sidequest-ui/src/components/SensitivitiesSection.tsx`. Replace the entire returned `<section>` so it includes the post-bleed paragraphs. The new file content (full replacement):

```tsx
import { getCharacterBars, type LedgerBar, type MagicState } from "../types/magic";

interface SensitivitiesSectionProps {
  magicState: MagicState | null;
  characterId: string;
}

const PRE_BLEED_COPY = "You hear what the others don't. Sometimes.";

function anyBarDrifted(bars: LedgerBar[]): boolean {
  return bars.some((b) => b.value !== b.spec.starts_at_chargen);
}

/**
 * Names the player's coyote_star "Reader" capacity on the Abilities tab.
 *
 * The world's microbleeds (mug jitters, dust profile carries after-rain,
 * the hum that isn't yours) are easy to read as atmosphere — Keith's own
 * playtest confirmed they vanish unnamed. This subsection makes the
 * capacity legible without giving the player a verb list (per CLAUDE.md
 * Zork: no closed option set in the input path). Two states:
 *
 * - Pre-bleed (all character bars at starts_at_chargen): one cryptic line.
 * - Post-bleed (any bar drifted): expanded framing + cost vocabulary.
 *
 * Returns null when there are no character bars to interpret — covers
 * other genres + pre-magic worlds with no extra gating.
 */
export function SensitivitiesSection({
  magicState,
  characterId,
}: SensitivitiesSectionProps) {
  if (magicState == null) return null;
  const bars = getCharacterBars(magicState, characterId);
  if (bars.length === 0) return null;

  const drifted = anyBarDrifted(bars);

  return (
    <section className="sensitivities-section mt-4 pt-3 border-t border-border/30">
      <h3 className="text-sm italic font-semibold mb-2 text-muted-foreground">
        Sensitivities
      </h3>
      {drifted ? (
        <div className="space-y-2 text-sm text-foreground/85">
          <p>Something stirred. You felt it.</p>
          <p>
            The substrate has weight — the hum behind the hum, the thing
            the dust profile carries that isn't dust. You can answer. You
            can refuse. You can push deeper. You can sit with it.
          </p>
          <p>
            <strong>Sanity</strong> is the price of staying open.{" "}
            <strong>Notice</strong> measures what you catch.{" "}
            <strong>Vitality</strong> decides whether you can carry it back.
          </p>
          <p>
            No one taught you the shape of this. You learn by reaching, or
            by flinching.
          </p>
          <p className="italic text-muted-foreground/80">
            Your own words, in the input bar.
          </p>
        </div>
      ) : (
        <p className="text-sm italic text-muted-foreground/80">{PRE_BLEED_COPY}</p>
      )}
    </section>
  );
}
```

- [ ] **Step 2: Run both tests, confirm both pass**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui && npx vitest run src/components/__tests__/SensitivitiesSection.test.tsx
```

Expected: 2 PASS.

- [ ] **Step 3: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui && \
  git add src/components/SensitivitiesSection.tsx && \
  git commit -m "feat(magic): SensitivitiesSection — post-bleed branch with cost vocabulary"
```

---

## Task 6: Add absence test for non-magic worlds

**Files:**
- Modify: `sidequest-ui/src/components/__tests__/SensitivitiesSection.test.tsx`

- [ ] **Step 1: Append two absence cases inside the existing `describe`**

Add these `it` blocks at the end of the existing `describe`:

```tsx
  it("renders nothing when magicState is null (other genres / pre-magic worlds)", () => {
    const { container } = render(
      <SensitivitiesSection magicState={null} characterId="Itchy" />,
    );
    expect(container.firstChild).toBeNull();
    expect(screen.queryByRole("heading", { name: /sensitivities/i })).not.toBeInTheDocument();
  });

  it("renders nothing when the character has no ledger bars", () => {
    // magicState present but only world bars — character has not been added
    // to the ledger yet.
    const ledger = Object.fromEntries([
      makeBar("hegemony_heat", "world", 0.3, 0.3),
    ]);
    const state: MagicState = { config: baseConfig, ledger, working_log: [] };

    const { container } = render(
      <SensitivitiesSection magicState={state} characterId="Itchy" />,
    );
    expect(container.firstChild).toBeNull();
  });
```

- [ ] **Step 2: Run all four tests, confirm all pass**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui && npx vitest run src/components/__tests__/SensitivitiesSection.test.tsx
```

Expected: 4 PASS. The two new tests pass against the existing implementation (the early returns already handle `magicState == null` and empty-bars), so this task confirms behavior rather than driving new code. That confirmation is the wiring guarantee for AC3 and is required before declaring the component done.

- [ ] **Step 3: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui && \
  git add src/components/__tests__/SensitivitiesSection.test.tsx && \
  git commit -m "test(magic): SensitivitiesSection absence cases (null state, empty bars)"
```

---

## Task 7: Mount the section inside AbilitiesContent

**Files:**
- Modify: `sidequest-ui/src/components/CharacterPanel.tsx`

- [ ] **Step 1: Import the new component**

Open `sidequest-ui/src/components/CharacterPanel.tsx`. After the existing imports (after `import type { MagicState } from "@/types/magic";`), add:

```tsx
import { SensitivitiesSection } from "./SensitivitiesSection";
```

- [ ] **Step 2: Update `AbilitiesContent` signature and body**

Find the existing `AbilitiesContent` function (around line 344 in the current file, identified by its `function AbilitiesContent({ abilities }: { abilities: string[] }) {` signature). Replace the entire function with this version (note: the signature now accepts `magicState` and `characterId`, and the body mounts `<SensitivitiesSection>` after the bullet list):

```tsx
function AbilitiesContent({
  abilities,
  magicState,
  characterId,
}: {
  abilities: string[];
  magicState: MagicState | null;
  characterId: string;
}) {
  const real = abilities.filter((a) => !a.includes("auto-filled"));
  return (
    <div>
      {real.length === 0 ? (
        <p className="text-sm text-muted-foreground/60">No abilities.</p>
      ) : (
        <ul className="list-disc list-inside text-sm space-y-1">
          {real.map((ability) => (
            <li key={ability}>{ability}</li>
          ))}
        </ul>
      )}
      <SensitivitiesSection magicState={magicState} characterId={characterId} />
    </div>
  );
}
```

- [ ] **Step 3: Update the `AbilitiesContent` invocation**

Find the existing line in `CharacterPanel`'s render (around line 171):

```tsx
{activeTab === "abilities" && <AbilitiesContent abilities={character.abilities} />}
```

Replace with:

```tsx
{activeTab === "abilities" && (
  <AbilitiesContent
    abilities={character.abilities}
    magicState={magicState}
    characterId={character.name}
  />
)}
```

- [ ] **Step 4: Type-check + run all SensitivitiesSection tests**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui && \
  npx tsc --noEmit && \
  npx vitest run src/components/__tests__/SensitivitiesSection.test.tsx
```

Expected: tsc passes (no errors), 4 vitest tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui && \
  git add src/components/CharacterPanel.tsx && \
  git commit -m "feat(magic): mount SensitivitiesSection inside AbilitiesContent"
```

---

## Task 8: CharacterPanel-level wiring test

**Files:**
- Create: `sidequest-ui/src/__tests__/sensitivities-character-panel-wiring.test.tsx`

This is the integration test required by CLAUDE.md ("every test suite needs a wiring test"). It proves `SensitivitiesSection` reaches users through the production code path (the Abilities tab on `CharacterPanel`), not just in isolation.

- [ ] **Step 1: Write the wiring test**

Create `sidequest-ui/src/__tests__/sensitivities-character-panel-wiring.test.tsx`:

```tsx
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { CharacterPanel } from "../components/CharacterPanel";
import type { CharacterSheetData } from "../components/CharacterSheet";
import type { MagicState, LedgerBar, LedgerBarSpec } from "../types/magic";

function makeBar(
  id: string,
  scope: "character" | "world",
  value: number,
  startsAtChargen: number,
): [string, LedgerBar] {
  const spec: LedgerBarSpec = {
    id,
    scope,
    direction: scope === "world" ? "up" : "down",
    range: [0.0, 1.0],
    decay_per_session: 0.0,
    starts_at_chargen: startsAtChargen,
  };
  const owner = scope === "world" ? "coyote_star" : "Itchy";
  return [`${scope}|${owner}|${id}`, { spec, value }];
}

const baseConfig = {
  world_slug: "coyote_star",
  genre_slug: "space_opera",
  allowed_sources: ["innate", "item_based"],
  active_plugins: ["innate_v1", "item_legacy_v1"],
  intensity: 0.25,
  world_knowledge: { primary: "classified" as const, local_register: "folkloric" as const },
  visibility: {},
  hard_limits: [],
  cost_types: ["sanity", "notice"],
  ledger_bars: [],
  can_build_caster: false,
  can_build_item_user: true,
  narrator_register: "",
};

const character: CharacterSheetData = {
  name: "Itchy",
  class: "smuggler",
  level: 1,
  stats: { Edge: 10 },
  abilities: ["Read a Manifest at a Glance"],
  backstory: "",
};

describe("Sensitivities wiring through CharacterPanel", () => {
  beforeEach(() => {
    // useLocalPrefs reads localStorage on mount — clear between tests so
    // the per-test localStorage.setItem call is the only source of state.
    window.localStorage.clear();
  });

  it("renders Sensitivities on the Abilities tab when coyote_star magicState is present", () => {
    const ledger = Object.fromEntries([
      makeBar("sanity", "character", 1.0, 1.0),
      makeBar("notice", "character", 0.0, 0.0),
      makeBar("vitality", "character", 0.5, 0.5),
    ]);
    const magicState: MagicState = { config: baseConfig, ledger, working_log: [] };

    // Force the abilities tab via localStorage prefs (the panel persists
    // activeTab through useLocalPrefs). Set BEFORE render.
    window.localStorage.setItem(
      "sq-character-panel",
      JSON.stringify({ activeTab: "abilities" }),
    );

    render(<CharacterPanel character={character} magicState={magicState} />);

    expect(screen.getByRole("heading", { name: /sensitivities/i })).toBeInTheDocument();
    expect(screen.getByText(/you hear what the others don't\. sometimes\./i)).toBeInTheDocument();
  });

  it("omits Sensitivities entirely when magicState is null", () => {
    window.localStorage.setItem(
      "sq-character-panel",
      JSON.stringify({ activeTab: "abilities" }),
    );

    render(<CharacterPanel character={character} magicState={null} />);

    expect(screen.queryByRole("heading", { name: /sensitivities/i })).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the wiring test**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui && npx vitest run src/__tests__/sensitivities-character-panel-wiring.test.tsx
```

Expected: 2 PASS.

- [ ] **Step 3: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui && \
  git add src/__tests__/sensitivities-character-panel-wiring.test.tsx && \
  git commit -m "test(magic): CharacterPanel-level wiring test for SensitivitiesSection"
```

---

## Task 9: Full check — vitest + tsc + lint

**Files:** none (verification only).

- [ ] **Step 1: Run the entire vitest suite**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui && npx vitest run
```

Expected: all tests pass. If unrelated failures appear, capture them in the PR body as pre-existing — but verify via `git stash` + re-run that they exist on `develop` head before declaring them unrelated.

- [ ] **Step 2: Type-check**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui && npx tsc --noEmit
```

Expected: zero errors.

- [ ] **Step 3: Lint**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui && npx eslint src/components/SensitivitiesSection.tsx src/components/CharacterPanel.tsx src/components/__tests__/SensitivitiesSection.test.tsx src/__tests__/sensitivities-character-panel-wiring.test.tsx
```

Expected: zero errors, zero warnings on touched files.

- [ ] **Step 4: If any check fails, fix the root cause**

Per CLAUDE.md "No Silent Fallbacks" + "no half-wired features": no `// @ts-expect-error`, no `eslint-disable`, no `.skip`. Fix it properly. If a fix turns out to be larger than expected, stop and surface it — do not commit a hack.

- [ ] **Step 5: No commit needed for this task** — verification only.

---

## Task 10: Push, PR, merge, pull

**Files:** none (git/gh operations only).

- [ ] **Step 1: Push the branch**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui && \
  git push -u origin feat/sensitivities-magic-affordance-coyote-star
```

Expected: branch published; URL printed.

- [ ] **Step 2: Open the PR against `develop`**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui && \
  gh pr create --base develop \
    --head feat/sensitivities-magic-affordance-coyote-star \
    --title "feat(magic): Sensitivities subsection on Abilities tab — coyote_star" \
    --body "$(cat <<'EOF'
## Summary

Adds a Sensitivities subsection to the Abilities tab that names what coyote_star players are sensing. Two states:

- **Pre-bleed** (all character bars at \`starts_at_chargen\`): one cryptic line — *"You hear what the others don't. Sometimes."*
- **Post-bleed** (any bar drifted): expanded framing introducing the cost vocabulary (Sanity / Notice / Vitality) and pointing the player at the input bar in their own words.

Returns null when \`magicState == null\` or the character has no ledger bars — coyote_star scope by content, no genre-slug check needed.

## Why

8 coyote_star playtest saves spanning 2026-04-30 → 2026-05-02 produced ZERO magic workings. \`magic_state\` persists fine, but no one has invoked. Keith confirmed in playtest that the in-fiction microbleeds (mug jitters, dust profile carries after-rain, etc.) read as atmosphere — even the system author had no clue what they were. This surface names the capacity without closing the input set: no buttons, no chips, no pre-fill. River-Tam-shaped (Chalmers / Leckie / Wells / Tchaikovsky), not space-wizard. In-confrontation magic stays as the existing beat-button architecture.

Spec: \`docs/superpowers/specs/2026-05-02-magic-affordance-coyote-star-design.md\`

## Test plan

- [x] \`SensitivitiesSection.test.tsx\` — 4 tests (pre-bleed, post-bleed, null state, no character bars)
- [x] \`sensitivities-character-panel-wiring.test.tsx\` — 2 wiring tests through \`CharacterPanel\`
- [x] \`npx tsc --noEmit\` clean
- [x] \`npx eslint\` clean on touched files
- [ ] Manual: \`just up\` → coyote_star solo → Abilities tab shows pre-bleed line at chargen → after first narration with a microbleed, expanded copy appears
- [ ] AC6 (post-merge): next coyote_star playtest produces at least one entry in \`magic_state.recent_workings\` OR a Phase-5 confrontation event

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Expected: PR URL printed.

- [ ] **Step 3: Merge the PR (squash + delete branch)**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui && \
  gh pr merge --squash --delete-branch
```

Expected: "Merged pull request" and branch deletion confirmation.

- [ ] **Step 4: Switch to develop and pull**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui && \
  git checkout develop && git pull
```

Expected: fast-forward to the squash-merge commit.

- [ ] **Step 5: Confirm the merged commit is on develop**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui && git log --oneline -3
```

Expected: top commit is the squash-merge with title `feat(magic): Sensitivities subsection on Abilities tab — coyote_star (#NNN)`.

---

## Self-review checklist (run after the plan ships)

- **Spec coverage:**
  - AC1 (chargen Reader hint, pre-bleed copy on Abilities tab) → Tasks 2, 3, 7, 8.
  - AC2 (post-bleed unfold when any bar drifts) → Tasks 4, 5.
  - AC3 (other-genre absence) → Task 6 + Task 8 second case.
  - AC4 (no bar HUD on Abilities tab) → guaranteed by component design (Task 3 / Task 5 — no bar markup written).
  - AC5 (no buttons / no interactivity) → guaranteed by component design (no `onClick`, no `<button>`, no input).
  - AC6 (next playtest produces a working) → not testable in implementation; the PR body lists it as the post-merge gate.
- **Placeholder scan:** no TBD, no TODO, no "implement later" anywhere in this plan; every code block is the full content the engineer types.
- **Type consistency:** `SensitivitiesSection` props are named `magicState` / `characterId` everywhere (component file, both test files, Task 7 invocation). `getCharacterBars` is called with `(magicState, characterId)` matching the existing `@/types/magic` export. `MagicState` and `LedgerBar` types come from `@/types/magic` (or relative `../types/magic`) consistently.
