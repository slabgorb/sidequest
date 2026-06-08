# Lobby Identity — Genre-Grouped Picker + Scoped Theming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the SideQuest lobby its own stable identity — a genre-grouped world picker, scope-clear Rules/Lore links, and a "house" chrome that no longer inherits the last-entered world's genre theme.

**Architecture:** All changes are in `sidequest-ui` (React/TS, Vite, Vitest). Two phases. **Phase 1 (theming):** add a neutral `house` chrome archetype, factor the DOM-applying logic so an archetype can be applied to *any* element (not just `<html>`), drive `house` on the document root while the lobby is showing, and scope the *selected* world's genre archetype to the world-preview card. **Phase 2 (picker):** extend the shared `OptionList` with a genre-grouped mode (sticky headers, single radiogroup), rebuild the `ConnectScreen` world list as groups, move **Rules** onto each genre header and **Lore** into the preview card, and retire the orphaned `ReferenceLinks` component. Each phase ends with the full UI suite green and the app working.

**Tech Stack:** React 18, TypeScript, Vite, Vitest + `@testing-library/react`, Tailwind utility classes, shadcn CSS tokens (`var(--background)`, `var(--foreground)`, etc.), CSS custom properties driven by `[data-archetype]` selectors.

**Spec:** `docs/superpowers/specs/2026-06-03-lobby-identity-grouped-picker-design.md`

---

## File Structure

| File | Phase | Responsibility after this plan |
|------|-------|-------------------------------|
| `src/hooks/useChromeArchetype.ts` | 1 | Genre→archetype map (`getArchetypeForGenre`), archetype CSS-var table (`ARCHETYPE_PROPERTIES`) incl. `house`, a pure `applyArchetypeToElement` helper, a root hook `useChromeArchetype(archetype)`, and a scoped hook `useScopedChromeArchetype(ref, archetype)` |
| `src/hooks/__tests__/useChromeArchetype.test.ts` | 1 | Tests for the map (unchanged), the props table (incl. `house`), and both hooks (now archetype-driven) |
| `src/styles/archetype-chrome.css` | 1 | Add a neutral `[data-archetype="house"]` block |
| `src/App.tsx` | 1 | Drive the root archetype: `house` during the `connect` phase, genre archetype otherwise |
| `src/screens/lobby/WorldPreview.tsx` | 1 + 2 | (P1) scope the selected world's genre archetype to the card wrapper via a ref; (P2) host the world-scoped **Lore** link in the card header |
| `src/screens/lobby/OptionList.tsx` | 2 | Add optional genre-grouped mode: sticky `role="presentation"` headers carrying a **Rules** link, single radiogroup across all worlds, auto-scroll the selection into view |
| `src/screens/lobby/__tests__/OptionList.test.tsx` | 2 | New dedicated tests for grouped rendering, single-radiogroup keyboard nav, header Rules link, auto-scroll |
| `src/screens/ConnectScreen.tsx` | 2 | Build `OptionGroup[]` instead of a flat list; render the grouped `OptionList`; pass `loreHref`/`archetype` to `WorldPreview`; remove the standalone `ReferenceLinks` *from the lobby* |
| `src/components/ReferenceLinks.tsx` | 2 | **Kept** — still used in-game by `GameBoard/widgets/NarrativeWidget.tsx`. Only its *lobby* usage is removed; the component and its unit tests stay |
| `src/screens/__tests__/ConnectScreen.reference.test.tsx`, `ConnectScreen.test.tsx` | 2 | Updated to the grouped list + relocated links |

**Locked type/API decisions (used consistently across all tasks):**

```ts
// useChromeArchetype.ts
export type ChromeArchetype = "parchment" | "terminal" | "rugged" | "house";

export function applyArchetypeToElement(
  el: HTMLElement,
  archetype: ChromeArchetype | null,
  prevKeys: string[],
): string[]; // removes prevKeys; null => removes data-archetype & returns []; else sets attr+vars, returns new keys

export function useChromeArchetype(archetype: ChromeArchetype | null): ChromeArchetype | null; // applies to document.documentElement
export function useScopedChromeArchetype(
  ref: React.RefObject<HTMLElement | null>,
  archetype: ChromeArchetype | null,
): void; // applies to ref.current

export function getArchetypeForGenre(genre: string): ChromeArchetype; // unchanged; still throws on unknown
```

```ts
// OptionList.tsx
export interface OptionGroup {
  slug: string;             // genre slug
  label: string;            // genre display name (header text)
  rulesHref: string | null; // /reference/rules/{genreSlug}
  items: OptionItem[];      // worlds in this genre
}
// OptionListProps gains:  groups?: OptionGroup[];   (mutually exclusive with items)
```

> **Note on the chrome-archetype CSS test:** `src/__tests__/chrome-archetype-css.test.ts` asserts the three existing `[data-archetype="X"]` selectors exist. Adding `house` does **not** break it (it only checks for presence of the three). Task 1 adds an optional house assertion for completeness.

---

# Phase 1 — Lobby Theming Scope Fix

*Outcome: the lobby shell renders a neutral `house` chrome; the selected world's genre flavor is confined to the preview card; the document root never carries a stale genre archetype while in the lobby.*

### Task 1: Add the `house` archetype (type + CSS-var table + CSS block)

**Files:**
- Modify: `src/hooks/useChromeArchetype.ts:3` (union), `:33-55` (`ARCHETYPE_PROPERTIES`)
- Modify: `src/styles/archetype-chrome.css` (append house block)
- Test: `src/hooks/__tests__/useChromeArchetype.test.ts`, `src/__tests__/chrome-archetype-css.test.ts`

- [ ] **Step 1: Write the failing test (props table includes house)**

In `src/hooks/__tests__/useChromeArchetype.test.ts`, change the `archetypes` array in the `ARCHETYPE_PROPERTIES` describe block (currently line 73) and add a house font assertion:

```ts
// was: const archetypes: ChromeArchetype[] = ["parchment", "terminal", "rugged"];
const archetypes: ChromeArchetype[] = ["parchment", "terminal", "rugged", "house"];

it("house uses a serif body distinct from parchment", () => {
  expect(ARCHETYPE_PROPERTIES["house"]["--font-body"]).toMatch(/serif/i);
  expect(ARCHETYPE_PROPERTIES["house"]["--font-body"]).not.toEqual(
    ARCHETYPE_PROPERTIES["parchment"]["--font-body"],
  );
});
```

The existing `"archetypes have distinct border-radius values"` test (line 111) now iterates 4 archetypes and asserts `radii.size === 3`. Update its expectation to `4`:

```ts
it("archetypes have distinct border-radius values", () => {
  const radii = new Set(archetypes.map((a) => ARCHETYPE_PROPERTIES[a]["--border-radius"]));
  expect(radii.size).toBe(4);
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `npx vitest run src/hooks/__tests__/useChromeArchetype.test.ts`
Expected: FAIL — `ARCHETYPE_PROPERTIES["house"]` is `undefined`; radius set size is 3.

- [ ] **Step 3: Add `house` to the union and the props table**

In `src/hooks/useChromeArchetype.ts`:

```ts
export type ChromeArchetype = "parchment" | "terminal" | "rugged" | "house";
```

Add a fourth entry to `ARCHETYPE_PROPERTIES` (after the `rugged` block, before the closing `}`). House is a neutral editorial identity — humanist serif body, neutral UI sans, distinct `3px` radius (parchment=2px, terminal=0px, rugged=4px, so 3px keeps all four distinct):

```ts
  house: {
    "--font-body": "'Iowan Old Style', 'Palatino Linotype', Palatino, Georgia, serif",
    "--font-ui": "'Inter', 'Helvetica Neue', system-ui, sans-serif",
    "--font-display": "'Iowan Old Style', Georgia, serif",
    "--border-radius": "3px",
  },
```

- [ ] **Step 4: Run it to verify it passes**

Run: `npx vitest run src/hooks/__tests__/useChromeArchetype.test.ts`
Expected: PASS.

- [ ] **Step 5: Add the house CSS block + its test**

Append to `src/styles/archetype-chrome.css` (after the rugged background-canvas block, around line 395, before the Narration Pane Typography section is also fine — keep it with the other archetype blocks):

```css
/* ── House ─────────────────────────────────────────────────────────────────
   Neutral SideQuest chrome for the lobby/menu. NOT a genre — deliberately
   plain so a themed world-preview card visibly stands apart from the shell.
   Soft neutral vignette, hairline borders, no texture noise.
   ──────────────────────────────────────────────────────────────────────── */

[data-archetype="house"] .running-header {
  border-bottom: 1px solid var(--border);
  background: var(--surface);
}

[data-archetype="house"] .character-panel {
  border-left: 1px solid var(--border);
  background: var(--surface);
}

[data-archetype="house"] .background-canvas {
  background:
    radial-gradient(
      ellipse at 50% 50%,
      color-mix(in srgb, var(--surface, var(--card)) 85%, transparent),
      color-mix(in srgb, var(--surface, var(--background)) 96%, transparent)
    );
}
```

Add a presence assertion to `src/__tests__/chrome-archetype-css.test.ts` inside the `"archetype CSS selectors"` describe (after the rugged case, ~line 36):

```ts
  it("contains [data-archetype=\"house\"] selector", () => {
    const css = loadArchetypeCSS();
    expect(css).toContain('[data-archetype="house"]');
  });
```

- [ ] **Step 6: Run both test files**

Run: `npx vitest run src/hooks/__tests__/useChromeArchetype.test.ts src/__tests__/chrome-archetype-css.test.ts`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/hooks/useChromeArchetype.ts src/hooks/__tests__/useChromeArchetype.test.ts src/styles/archetype-chrome.css src/__tests__/chrome-archetype-css.test.ts
git commit -m "feat(lobby): add neutral house chrome archetype"
```

---

### Task 2: Factor the DOM applier; make the hooks archetype-driven; add the scoped hook

The current `useChromeArchetype(genreSlug)` resolves the slug internally and only ever writes to `document.documentElement`. We split responsibilities: a pure `applyArchetypeToElement` does the DOM work for any element; `useChromeArchetype(archetype)` applies to the root; `useScopedChromeArchetype(ref, archetype)` applies to a subtree. Genre→archetype resolution moves to the call site.

**Files:**
- Modify: `src/hooks/useChromeArchetype.ts:57-87`
- Test: `src/hooks/__tests__/useChromeArchetype.test.ts:121-221`

- [ ] **Step 1: Rewrite the hook tests to be archetype-driven**

Replace the entire `describe("useChromeArchetype", ...)` block (lines 121-184) and the `describe("useChromeArchetype wiring", ...)` block (lines 190-221) with archetype-input versions, and add a scoped-hook block. Full replacement:

```ts
describe("useChromeArchetype (root)", () => {
  beforeEach(() => {
    document.documentElement.style.cssText = "";
    document.documentElement.removeAttribute("data-archetype");
  });

  it("sets data-archetype on the document element", () => {
    renderHook(() => useChromeArchetype("parchment"));
    expect(document.documentElement.getAttribute("data-archetype")).toBe("parchment");
  });

  it("injects archetype CSS custom properties onto :root", () => {
    renderHook(() => useChromeArchetype("terminal"));
    const style = document.documentElement.style;
    expect(style.getPropertyValue("--font-body")).toMatch(/mono/i);
    expect(style.getPropertyValue("--font-ui")).toBeTruthy();
    expect(style.getPropertyValue("--border-radius")).toBeDefined();
  });

  it("updates archetype when the input changes", () => {
    const { rerender } = renderHook(
      ({ a }: { a: ChromeArchetype }) => useChromeArchetype(a),
      { initialProps: { a: "parchment" as ChromeArchetype } },
    );
    expect(document.documentElement.getAttribute("data-archetype")).toBe("parchment");
    rerender({ a: "terminal" });
    expect(document.documentElement.getAttribute("data-archetype")).toBe("terminal");
  });

  it("cleans up previous CSS properties when switching", () => {
    const { rerender } = renderHook(
      ({ a }: { a: ChromeArchetype }) => useChromeArchetype(a),
      { initialProps: { a: "terminal" as ChromeArchetype } },
    );
    expect(document.documentElement.style.getPropertyValue("--font-body")).toMatch(/mono/i);
    rerender({ a: "parchment" });
    expect(document.documentElement.style.getPropertyValue("--font-body")).toMatch(/serif/i);
    expect(document.documentElement.style.getPropertyValue("--font-body")).not.toMatch(/mono/i);
  });

  it("removes data-archetype when given null", () => {
    const { rerender } = renderHook(
      ({ a }: { a: ChromeArchetype | null }) => useChromeArchetype(a),
      { initialProps: { a: "rugged" as ChromeArchetype | null } },
    );
    expect(document.documentElement.getAttribute("data-archetype")).toBe("rugged");
    rerender({ a: null });
    expect(document.documentElement.getAttribute("data-archetype")).toBeNull();
  });

  it("does not clobber genre color variables", () => {
    document.documentElement.style.setProperty("--primary", "#C4650A");
    renderHook(() => useChromeArchetype("rugged"));
    expect(document.documentElement.style.getPropertyValue("--primary")).toBe("#C4650A");
    expect(document.documentElement.style.getPropertyValue("--font-body")).toBeTruthy();
  });
});

describe("useScopedChromeArchetype", () => {
  it("applies the archetype to the ref element, NOT the document root", () => {
    document.documentElement.removeAttribute("data-archetype");
    const el = document.createElement("div");
    const ref = { current: el };
    renderHook(() => useScopedChromeArchetype(ref, "terminal"));
    expect(el.getAttribute("data-archetype")).toBe("terminal");
    expect(el.style.getPropertyValue("--font-body")).toMatch(/mono/i);
    // Root must be untouched by the scoped applier.
    expect(document.documentElement.getAttribute("data-archetype")).toBeNull();
  });

  it("is a no-op when the ref is empty", () => {
    const ref = { current: null as HTMLElement | null };
    expect(() => renderHook(() => useScopedChromeArchetype(ref, "house"))).not.toThrow();
  });
});
```

Update the imports at the top of the test file (line 3-8) to include the new exports:

```ts
import {
  type ChromeArchetype,
  getArchetypeForGenre,
  ARCHETYPE_PROPERTIES,
  useChromeArchetype,
  useScopedChromeArchetype,
} from "@/hooks/useChromeArchetype";
```

- [ ] **Step 2: Run it to verify it fails**

Run: `npx vitest run src/hooks/__tests__/useChromeArchetype.test.ts`
Expected: FAIL — `useScopedChromeArchetype` is not exported; `useChromeArchetype("parchment")` currently treats `"parchment"` as a genre slug (not in `GENRE_TO_ARCHETYPE`) and throws.

- [ ] **Step 3: Rewrite the hook implementation**

Replace lines 57-87 of `src/hooks/useChromeArchetype.ts` with:

```ts
/**
 * Apply (or clear) a chrome archetype on a specific element. Sets the
 * `data-archetype` attribute and the archetype's structural CSS custom
 * properties. Returns the list of property keys it set, so the caller can
 * remove exactly those on the next change (no leak across archetype swaps).
 * Passing `null` removes the attribute and clears previously-set keys.
 */
export function applyArchetypeToElement(
  el: HTMLElement,
  archetype: ChromeArchetype | null,
  prevKeys: string[],
): string[] {
  const style = el.style;
  for (const key of prevKeys) {
    style.removeProperty(key);
  }
  if (!archetype) {
    el.removeAttribute("data-archetype");
    return [];
  }
  el.setAttribute("data-archetype", archetype);
  const props = ARCHETYPE_PROPERTIES[archetype];
  const newKeys: string[] = [];
  for (const [key, value] of Object.entries(props)) {
    style.setProperty(key, value);
    newKeys.push(key);
  }
  return newKeys;
}

/**
 * Apply a chrome archetype to the document root (`<html>`). Pass `null` to
 * clear it. Callers resolve genre slugs via `getArchetypeForGenre` before
 * calling — the hook itself is archetype-driven so it can also apply the
 * non-genre `house` chrome.
 */
export function useChromeArchetype(
  archetype: ChromeArchetype | null,
): ChromeArchetype | null {
  const prevKeysRef = useRef<string[]>([]);

  useEffect(() => {
    prevKeysRef.current = applyArchetypeToElement(
      document.documentElement,
      archetype,
      prevKeysRef.current,
    );
  }, [archetype]);

  return archetype;
}

/**
 * Apply a chrome archetype to a specific element (a subtree), leaving the
 * document root untouched. Used to confine a world's genre flavor to the
 * lobby preview card without leaking onto the lobby shell.
 */
export function useScopedChromeArchetype(
  ref: React.RefObject<HTMLElement | null>,
  archetype: ChromeArchetype | null,
): void {
  const prevKeysRef = useRef<string[]>([]);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    prevKeysRef.current = applyArchetypeToElement(el, archetype, prevKeysRef.current);
  }, [ref, archetype]);
}
```

Update the import at the top of the file (line 1) to bring in the `React` type for `RefObject`:

```ts
import { useEffect, useRef } from "react";
import type { RefObject } from "react";
```

And change the `useScopedChromeArchetype` signature to use the imported alias:

```ts
export function useScopedChromeArchetype(
  ref: RefObject<HTMLElement | null>,
  archetype: ChromeArchetype | null,
): void {
```

- [ ] **Step 4: Run it to verify it passes**

Run: `npx vitest run src/hooks/__tests__/useChromeArchetype.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/hooks/useChromeArchetype.ts src/hooks/__tests__/useChromeArchetype.test.ts
git commit -m "refactor(lobby): archetype-driven chrome hooks + scoped applier"
```

---

### Task 3: Drive `house` on the document root during the connect phase

`App.tsx:543` currently calls `useChromeArchetype(currentGenre)` (a genre slug). After Task 2 the hook takes an archetype. Resolve it at the call site: `house` while the lobby (`sessionPhase === "connect"`) is showing, otherwise the genre archetype.

**Files:**
- Modify: `src/App.tsx` (import at top; the `useChromeArchetype` call ~line 543)
- Test: `src/__tests__/lobby-house-archetype-wiring.test.tsx` (new)

- [ ] **Step 1: Write the failing wiring test**

Create `src/__tests__/lobby-house-archetype-wiring.test.tsx`. This is the leak regression test — assert that on first render (connect phase) the root archetype is `house`, not a genre. The app's full mount is heavy; assert via the resolver logic that App uses. Extract the resolver as a tiny exported pure function so it is unit-testable without mounting the whole App:

```tsx
import { describe, it, expect } from "vitest";
import { resolveRootArchetype } from "@/App";

describe("lobby root archetype (leak fix)", () => {
  it("is house during the connect phase regardless of last genre", () => {
    expect(resolveRootArchetype("connect", "space_opera")).toBe("house");
    expect(resolveRootArchetype("connect", null)).toBe("house");
  });

  it("is the genre archetype during creation and game", () => {
    expect(resolveRootArchetype("creation", "space_opera")).toBe("terminal");
    expect(resolveRootArchetype("game", "road_warrior")).toBe("rugged");
  });

  it("is null in non-connect phases when no genre is set", () => {
    expect(resolveRootArchetype("game", null)).toBeNull();
  });
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `npx vitest run src/__tests__/lobby-house-archetype-wiring.test.tsx`
Expected: FAIL — `resolveRootArchetype` is not exported from `@/App`.

- [ ] **Step 3: Add the resolver and use it**

In `src/App.tsx`, add the import for `getArchetypeForGenre` and the `ChromeArchetype` type. The file already imports `useChromeArchetype` (line 12); extend that import:

```ts
import { useChromeArchetype, getArchetypeForGenre, type ChromeArchetype } from "@/hooks/useChromeArchetype";
```

Add the exported pure resolver near the top of the module (after the `SessionPhase` type at line 58):

```ts
/**
 * The chrome archetype for the document root. The lobby (`connect`) renders
 * the neutral `house` chrome so it never inherits the last-entered world's
 * genre theme; once a world is committed (creation/game) the genre archetype
 * applies. Exported for wiring tests.
 */
export function resolveRootArchetype(
  phase: SessionPhase,
  currentGenre: string | null,
): ChromeArchetype | null {
  if (phase === "connect") return "house";
  return currentGenre ? getArchetypeForGenre(currentGenre) : null;
}
```

Replace the call at line 543:

```ts
// was: useChromeArchetype(currentGenre);
useChromeArchetype(resolveRootArchetype(sessionPhase, currentGenre));
```

- [ ] **Step 4: Run it to verify it passes**

Run: `npx vitest run src/__tests__/lobby-house-archetype-wiring.test.tsx`
Expected: PASS.

- [ ] **Step 5: Run the App-mounting tests that touch data-archetype to confirm no regression**

Run: `npx vitest run src/__tests__/app-gameboard-world-slug-wiring.test.tsx`
Expected: PASS (this test mounts App and cleans up `data-archetype`; the resolver returns a genre archetype in game phase exactly as before).

- [ ] **Step 6: Commit**

```bash
git add src/App.tsx src/__tests__/lobby-house-archetype-wiring.test.tsx
git commit -m "fix(lobby): render house chrome on root during connect phase (no genre leak)"
```

---

### Task 4: Scope the selected world's genre archetype to the preview card

The lobby shell is now `house`. Give the preview card a contained "taste of the genre" by applying the *selected* world's archetype to the card wrapper only.

**Files:**
- Modify: `src/screens/lobby/WorldPreview.tsx`
- Test: `src/screens/lobby/__tests__/WorldPreview.test.tsx`

- [ ] **Step 1: Write the failing test**

Add to `src/screens/lobby/__tests__/WorldPreview.test.tsx`. (Read the file first for its existing fixture helpers — `pack`/`world` mock objects. Reuse them.) The new prop is `archetype`:

```tsx
it("scopes the genre archetype to the card element, not the document root", () => {
  document.documentElement.removeAttribute("data-archetype");
  const { getByTestId } = render(
    <WorldPreview pack={mockPack} world={mockWorld} archetype="terminal" loreHref={null} />,
  );
  const card = getByTestId("world-preview-card");
  expect(card.getAttribute("data-archetype")).toBe("terminal");
  expect(document.documentElement.getAttribute("data-archetype")).toBeNull();
});
```

> If the existing `render(<WorldPreview pack={...} world={...} />)` calls in this file now fail to typecheck because `archetype`/`loreHref` are required, make those two props **optional** in the component (`archetype?`, `loreHref?`) defaulting to `null` — existing call sites then stay valid.

- [ ] **Step 2: Run it to verify it fails**

Run: `npx vitest run src/screens/lobby/__tests__/WorldPreview.test.tsx`
Expected: FAIL — no `data-testid="world-preview-card"`; `archetype` prop unknown.

- [ ] **Step 3: Add the ref + scoped hook + testid**

In `src/screens/lobby/WorldPreview.tsx`:

Update imports (line 1-3):

```ts
import { useRef, useState } from "react";
import type { GenreMeta, WorldMeta } from "@/types/genres";
import { getToneChips } from "./toneAxes";
import { useScopedChromeArchetype, type ChromeArchetype } from "@/hooks/useChromeArchetype";
```

Extend the props interface (line 5-10):

```ts
export interface WorldPreviewProps {
  pack: GenreMeta | null;
  world: WorldMeta | null;
  /** Selected world's genre archetype, scoped to this card only. */
  archetype?: ChromeArchetype | null;
  /** World-scoped lore reference href, or null when unavailable. */
  loreHref?: string | null;
}
```

Update the destructure and add the ref + hook at the top of the component body (after line 21):

```ts
export function WorldPreview({ pack, world, archetype = null, loreHref = null }: WorldPreviewProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  useScopedChromeArchetype(cardRef, archetype);
```

Attach the ref + testid to the **loaded-state** root `<div>` (currently line 60-61, `className="flex-1 flex flex-col gap-4 px-6"`):

```tsx
  return (
    <div
      ref={cardRef}
      data-testid="world-preview-card"
      className="flex-1 flex flex-col gap-4 px-6"
    >
```

> The empty-state early-return (`!pack || !world`) does not need the ref — when nothing is selected there is no archetype to scope. Leave it as-is.

- [ ] **Step 4: Run it to verify it passes**

Run: `npx vitest run src/screens/lobby/__tests__/WorldPreview.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/screens/lobby/WorldPreview.tsx src/screens/lobby/__tests__/WorldPreview.test.tsx
git commit -m "feat(lobby): scope selected world's genre archetype to the preview card"
```

> **Phase 1 gate:** `npx vitest run` — full UI suite green. The `archetype`/`loreHref` props on `WorldPreview` are not yet wired from `ConnectScreen` (that lands in Phase 2 Tasks 6–7); defaulting to `null` keeps the app working and unt-themed-card in the meantime.

---

# Phase 2 — Genre-Grouped Picker + Link Relocation

*Outcome: the world list is grouped under sticky genre headers in a single radiogroup; Rules lives on each genre header (pack-scoped) and Lore lives in the preview card (world-scoped); the orphaned `ReferenceLinks` block is gone.*

### Task 5: Add a genre-grouped mode to `OptionList`

**Files:**
- Modify: `src/screens/lobby/OptionList.tsx`
- Test: `src/screens/lobby/__tests__/OptionList.test.tsx` (new)

- [ ] **Step 1: Write the failing tests**

Create `src/screens/lobby/__tests__/OptionList.test.tsx`:

```tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { OptionList, type OptionGroup } from "../OptionList";

const groups: OptionGroup[] = [
  {
    slug: "elemental_harmony",
    label: "Elemental Harmony",
    rulesHref: "/reference/rules/elemental_harmony",
    items: [
      { slug: "elemental_harmony/the_burning_peace", label: "The Burning Peace" },
      { slug: "elemental_harmony/the_shattered_accord", label: "The Shattered Accord" },
    ],
  },
  {
    slug: "space_opera",
    label: "Space Opera",
    rulesHref: "/reference/rules/space_opera",
    items: [{ slug: "space_opera/the_aureate_span", label: "The Aureate Span" }],
  },
];

beforeEach(() => {
  // jsdom has no scrollIntoView; stub it so the auto-scroll effect is callable.
  Element.prototype.scrollIntoView = vi.fn();
});

describe("OptionList grouped mode", () => {
  it("renders a genre header per group with a Rules link", () => {
    render(
      <OptionList ariaLabel="World" groups={groups} selected={null} onSelect={() => {}} />,
    );
    expect(screen.getByText("Elemental Harmony")).toBeInTheDocument();
    expect(screen.getByText("Space Opera")).toBeInTheDocument();
    const rules = screen.getByRole("link", { name: "Elemental Harmony rules" });
    expect(rules).toHaveAttribute("href", "/reference/rules/elemental_harmony");
  });

  it("renders one radiogroup spanning every world across groups", () => {
    render(
      <OptionList ariaLabel="World" groups={groups} selected={null} onSelect={() => {}} />,
    );
    expect(screen.getAllByRole("radiogroup")).toHaveLength(1);
    expect(screen.getAllByRole("radio")).toHaveLength(3); // 2 + 1
  });

  it("arrow-key nav flows across genre boundaries and skips headers", () => {
    const onSelect = vi.fn();
    render(
      <OptionList
        ariaLabel="World"
        groups={groups}
        selected="elemental_harmony/the_shattered_accord"
        onSelect={onSelect}
      />,
    );
    const group = screen.getByRole("radiogroup");
    fireEvent.keyDown(group, { key: "ArrowDown" });
    // Next world after the last item of group 1 is the first item of group 2.
    expect(onSelect).toHaveBeenCalledWith("space_opera/the_aureate_span");
  });

  it("scrolls the selected world into view", () => {
    render(
      <OptionList
        ariaLabel="World"
        groups={groups}
        selected="space_opera/the_aureate_span"
        onSelect={() => {}}
      />,
    );
    expect(Element.prototype.scrollIntoView).toHaveBeenCalled();
  });

  it("omits the Rules link when rulesHref is null", () => {
    render(
      <OptionList
        ariaLabel="World"
        groups={[{ ...groups[0], rulesHref: null }]}
        selected={null}
        onSelect={() => {}}
      />,
    );
    expect(screen.queryByRole("link", { name: /rules/i })).toBeNull();
  });
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `npx vitest run src/screens/lobby/__tests__/OptionList.test.tsx`
Expected: FAIL — `OptionGroup` is not exported; `groups` prop unknown.

- [ ] **Step 3: Implement grouped mode**

Rewrite `src/screens/lobby/OptionList.tsx`. Add the `OptionGroup` interface and `groups` prop; derive a flat item list for the radio set + keyboard model; render headers when grouped; add the auto-scroll effect; add `scroll-mt-12` to radios so the sticky header doesn't occlude them.

```tsx
import { useCallback, useEffect, useRef } from "react";

export interface OptionItem {
  slug: string;
  label: string;
  hint?: string;
  annotation?: React.ReactNode;
}

/** A genre section: a sticky header (with an optional Rules link) over its worlds. */
export interface OptionGroup {
  slug: string;
  label: string;
  rulesHref: string | null;
  items: OptionItem[];
}

export interface OptionListProps {
  ariaLabel: string;
  /** Flat mode. Mutually exclusive with `groups`. */
  items?: OptionItem[];
  /** Grouped mode: sticky genre headers over a single radiogroup. */
  groups?: OptionGroup[];
  selected: string | null;
  onSelect: (slug: string) => void;
  disabled?: boolean;
}

export function OptionList({
  ariaLabel,
  items,
  groups,
  selected,
  onSelect,
  disabled = false,
}: OptionListProps) {
  const listRef = useRef<HTMLDivElement>(null);

  // The flat radio set the keyboard model and roving-tabindex operate over,
  // regardless of whether the caller passed flat items or genre groups.
  const flatItems: OptionItem[] = groups ? groups.flatMap((g) => g.items) : items ?? [];

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (disabled || flatItems.length === 0) return;
      const currentIndex = flatItems.findIndex((i) => i.slug === selected);

      let nextIndex = currentIndex;
      switch (e.key) {
        case "ArrowDown":
        case "ArrowRight":
          nextIndex = currentIndex < 0 ? 0 : (currentIndex + 1) % flatItems.length;
          break;
        case "ArrowUp":
        case "ArrowLeft":
          nextIndex = currentIndex <= 0 ? flatItems.length - 1 : currentIndex - 1;
          break;
        case "Home":
          nextIndex = 0;
          break;
        case "End":
          nextIndex = flatItems.length - 1;
          break;
        default:
          return;
      }

      e.preventDefault();
      onSelect(flatItems[nextIndex].slug);

      const nextEl = listRef.current?.querySelector<HTMLButtonElement>(
        `[data-slug="${flatItems[nextIndex].slug}"]`,
      );
      nextEl?.focus();
    },
    [flatItems, selected, onSelect, disabled],
  );

  // Keep the selected world visible (it may sit under a sticky header or below
  // the fold after a restore). `block: "nearest"` avoids jumping the page.
  useEffect(() => {
    if (!selected) return;
    const el = listRef.current?.querySelector<HTMLButtonElement>(
      `[data-slug="${selected}"]`,
    );
    el?.scrollIntoView({ block: "nearest" });
  }, [selected]);

  const renderItem = (item: OptionItem) => {
    const isSelected = item.slug === selected;
    return (
      <button
        key={item.slug}
        type="button"
        role="radio"
        aria-checked={isSelected}
        data-slug={item.slug}
        tabIndex={isSelected || (!selected && item === flatItems[0]) ? 0 : -1}
        disabled={disabled}
        onClick={() => onSelect(item.slug)}
        className={`
          flex items-baseline justify-between
          w-full text-left px-3 py-1.5 scroll-mt-12
          bg-transparent border-0 border-l-4
          transition-colors cursor-pointer
          disabled:cursor-default disabled:opacity-40
          focus-visible:outline-none focus-visible:bg-muted/20
          ${
            isSelected
              ? "border-l-[var(--primary)] bg-[var(--primary)]/20 text-foreground font-semibold shadow-[inset_0_0_0_1px_rgba(255,255,255,0.05)]"
              : "border-l-transparent text-foreground/60 hover:border-l-muted-foreground/40 hover:bg-muted/20 hover:text-foreground/85"
          }
        `}
      >
        <span className="flex items-baseline gap-2">
          <span className="text-base tracking-wide">{item.label}</span>
          {item.hint && (
            <span className="text-xs italic text-muted-foreground/50">{item.hint}</span>
          )}
        </span>
        {item.annotation && (
          <span className="text-xs text-muted-foreground/70 tabular-nums">
            {item.annotation}
          </span>
        )}
      </button>
    );
  };

  return (
    <div
      ref={listRef}
      role="radiogroup"
      aria-label={ariaLabel}
      onKeyDown={handleKeyDown}
      className="flex flex-col w-full overflow-y-auto min-h-0
                 [scrollbar-gutter:stable] [scrollbar-width:thin]"
    >
      {groups
        ? groups.map((group) => (
            <div key={group.slug} role="presentation">
              <div
                role="presentation"
                className="sticky top-0 z-10 flex items-baseline justify-between
                           bg-background px-3 pt-3 pb-1"
              >
                <span className="text-xs uppercase tracking-widest text-muted-foreground/50">
                  {group.label}
                </span>
                {group.rulesHref && (
                  <a
                    href={group.rulesHref}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={`${group.label} rules`}
                    className="text-xs underline hover:no-underline text-muted-foreground/60"
                  >
                    Rules
                  </a>
                )}
              </div>
              {group.items.map(renderItem)}
            </div>
          ))
        : flatItems.map(renderItem)}
    </div>
  );
}
```

- [ ] **Step 4: Run it to verify it passes**

Run: `npx vitest run src/screens/lobby/__tests__/OptionList.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/screens/lobby/OptionList.tsx src/screens/lobby/__tests__/OptionList.test.tsx
git commit -m "feat(lobby): genre-grouped OptionList mode with sticky headers + Rules link"
```

---

### Task 6: Rebuild the `ConnectScreen` world list as groups; remove the standalone links

**Files:**
- Modify: `src/screens/ConnectScreen.tsx` (imports; `worldItems`→`worldGroups` ~line 134-151; the single-world + stale-selection effects ~line 180-200; the render ~line 416-444)
- Test: `src/screens/__tests__/ConnectScreen.reference.test.tsx`, `src/screens/__tests__/ConnectScreen.test.tsx`

- [ ] **Step 1: Update the tests to expect grouped output + relocated links**

Read both test files first. In `ConnectScreen.reference.test.tsx`, the existing assertions target the standalone `ReferenceLinks` block (`data-testid="reference-links"`) — replace them with assertions for the header Rules link and the absence of the old block. Add/replace with:

```tsx
it("renders a Rules link on each genre header (pack-scoped)", () => {
  renderConnectScreen(); // existing helper in this file; mounts with mock genres
  const rules = screen.getAllByRole("link", { name: /rules$/i });
  expect(rules.length).toBeGreaterThan(0);
  expect(rules[0]).toHaveAttribute("href", expect.stringMatching(/^\/reference\/rules\//));
});

it("no longer renders the standalone reference-links block", () => {
  renderConnectScreen();
  expect(screen.queryByTestId("reference-links")).toBeNull();
});
```

> Use the file's existing render helper and mock `genres` fixture (read the top of the test file to find their names — e.g. `renderConnectScreen`/`mockGenres`). If a world is preselected in the fixture, also assert the Lore link appears in the preview card (added in Task 7); otherwise leave Lore coverage to Task 7's WorldPreview test.

In `ConnectScreen.test.tsx`, find any assertion that depends on the flat list (e.g. counting rows, or `hint` genre suffixes) and update it: worlds now render under genre headers, and the genre text appears as a header (`getByText("Space Opera")`) rather than an inline `hint`. Replace a flat-list count assertion with a grouped one, e.g.:

```tsx
it("groups worlds under their genre headers", () => {
  renderConnectScreen();
  // Header present...
  expect(screen.getByText("Space Opera")).toBeInTheDocument();
  // ...and its world rendered as a radio.
  expect(screen.getByRole("radio", { name: /The Aureate Span/ })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run them to verify they fail**

Run: `npx vitest run src/screens/__tests__/ConnectScreen.reference.test.tsx src/screens/__tests__/ConnectScreen.test.tsx`
Expected: FAIL — Rules links not on headers; `reference-links` block still present.

- [ ] **Step 3: Build `worldGroups` and update the dependent effects**

In `src/screens/ConnectScreen.tsx`, update imports (line 5, 18):

```ts
import { OptionList, type OptionItem, type OptionGroup } from "./lobby/OptionList";
// remove:  import { ReferenceLinks } from "@/components/ReferenceLinks";
import { getArchetypeForGenre } from "@/hooks/useChromeArchetype";
```

Replace the `worldItems` memo (lines 134-151) with a `worldGroups` memo plus a `worldCount`:

```ts
  // Worlds grouped by genre. Genre renders as a sticky section header (with a
  // pack-scoped Rules link) rather than an inline hint. Composite "genre/world"
  // slug keeps rows unique across genres that ship same-slug worlds.
  const worldGroups: OptionGroup[] = useMemo(() => {
    const groups: OptionGroup[] = [];
    for (const [gSlug, gMeta] of Object.entries(genres)) {
      const genreLabel = gMeta.name || prettify(gSlug);
      const items: OptionItem[] = [];
      for (const w of gMeta.worlds) {
        const composite = `${gSlug}/${w.slug}`;
        const count = worldPresence[composite] ?? 0;
        items.push({
          slug: composite,
          label: w.name || prettify(w.slug),
          annotation: count > 0 ? `· ${count} here` : undefined,
        });
      }
      if (items.length === 0) continue;
      items.sort((a, b) => a.label.localeCompare(b.label));
      groups.push({
        slug: gSlug,
        label: genreLabel,
        rulesHref: `/reference/rules/${gSlug}`,
        items,
      });
    }
    groups.sort((a, b) => a.label.localeCompare(b.label));
    return groups;
  }, [genres, worldPresence]);

  const worldCount = useMemo(
    () => worldGroups.reduce((n, g) => n + g.items.length, 0),
    [worldGroups],
  );

  const allWorldItems = useMemo(
    () => worldGroups.flatMap((g) => g.items),
    [worldGroups],
  );
```

Update the single-world auto-select effect (lines 182-187) to use `allWorldItems`:

```ts
  useEffect(() => {
    if (allWorldItems.length === 1 && selectedComposite === null) {
      handleSelectWorld(allWorldItems[0].slug);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allWorldItems.length]);
```

Update the stale-selection-clear effect (lines 192-200) to check `allWorldItems`:

```ts
  useEffect(() => {
    if (
      selectedComposite &&
      allWorldItems.length > 0 &&
      !allWorldItems.some((item) => item.slug === selectedComposite)
    ) {
      setGenreSlug(null);
      setWorldSlug(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedComposite, allWorldItems]);
```

- [ ] **Step 4: Update the render — grouped list, drop ReferenceLinks**

Replace the left-column block (lines 417-444) with:

```tsx
            {/* Left column — genre-grouped world radio list */}
            <div className="flex flex-col gap-6 md:w-64 shrink-0">
              <section className="flex flex-col min-h-0">
                <h2 className="text-xs uppercase tracking-widest text-muted-foreground/50 mb-2">
                  World
                  <span className="not-italic text-muted-foreground/40 ml-1">
                    ({worldCount})
                  </span>
                </h2>
                <div className="max-h-[70vh] flex flex-col min-h-0">
                  <OptionList
                    ariaLabel="World"
                    groups={worldGroups}
                    selected={selectedComposite}
                    onSelect={handleSelectWorld}
                    disabled={isConnecting}
                  />
                </div>
              </section>
            </div>
```

(`max-h-[60vh]` → `max-h-[70vh]` gives the list real breathing room per the spec's scrollbar/height note. The `ReferenceLinks` element is removed entirely.)

- [ ] **Step 5: Run the ConnectScreen tests**

Run: `npx vitest run src/screens/__tests__/ConnectScreen.reference.test.tsx src/screens/__tests__/ConnectScreen.test.tsx`
Expected: PASS. (If a flat-`hint` assertion remains in `ConnectScreen.test.tsx`, update it to the header form per Step 1.)

- [ ] **Step 6: Commit**

```bash
git add src/screens/ConnectScreen.tsx src/screens/__tests__/ConnectScreen.reference.test.tsx src/screens/__tests__/ConnectScreen.test.tsx
git commit -m "feat(lobby): genre-grouped world picker; drop orphan reference links"
```

---

### Task 7: Wire Lore + card archetype into the preview from `ConnectScreen`

WorldPreview already accepts `archetype` and `loreHref` (Phase 1 Task 4) but `ConnectScreen` still passes neither. Wire them, and render the Lore link in the card header.

**Files:**
- Modify: `src/screens/ConnectScreen.tsx` (the `<WorldPreview .../>` at ~line 456)
- Modify: `src/screens/lobby/WorldPreview.tsx` (render the Lore link in the title block)
- Test: `src/screens/lobby/__tests__/WorldPreview.test.tsx`

- [ ] **Step 1: Write the failing test (Lore link in the card)**

Add to `src/screens/lobby/__tests__/WorldPreview.test.tsx`:

```tsx
it("renders a world-scoped Lore link when loreHref is provided", () => {
  render(
    <WorldPreview
      pack={mockPack}
      world={mockWorld}
      archetype="terminal"
      loreHref="/reference/lore/space_opera/the_aureate_span"
    />,
  );
  const lore = screen.getByRole("link", { name: `${mockWorld.name} lore` });
  expect(lore).toHaveAttribute("href", "/reference/lore/space_opera/the_aureate_span");
});

it("omits the Lore link when loreHref is null", () => {
  render(<WorldPreview pack={mockPack} world={mockWorld} loreHref={null} />);
  expect(screen.queryByRole("link", { name: /lore$/i })).toBeNull();
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `npx vitest run src/screens/lobby/__tests__/WorldPreview.test.tsx`
Expected: FAIL — no Lore link rendered.

- [ ] **Step 3: Render the Lore link in the title block**

In `src/screens/lobby/WorldPreview.tsx`, replace the title block (lines 126-138) so the world title and the Lore link sit on one row:

```tsx
      {/* Title + era subtitle, with the world-scoped Lore reference. */}
      <div>
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="text-2xl text-foreground/90 tracking-wide">{world.name}</h2>
          {loreHref && (
            <a
              href={loreHref}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`${world.name} lore`}
              className="text-sm underline hover:no-underline text-muted-foreground/70 shrink-0"
            >
              Lore
            </a>
          )}
        </div>
        {(world.setting || world.era) && (
          <p className="text-sm italic text-muted-foreground/70 mt-1">
            {world.setting}
            {world.setting && world.era && " · "}
            {world.era}
          </p>
        )}
      </div>
```

- [ ] **Step 4: Wire the props from ConnectScreen**

In `src/screens/ConnectScreen.tsx`, replace the `<WorldPreview .../>` call (line 456):

```tsx
              <WorldPreview
                pack={currentPack}
                world={currentWorld}
                archetype={genreSlug ? getArchetypeForGenre(genreSlug) : null}
                loreHref={
                  genreSlug && worldSlug
                    ? `/reference/lore/${genreSlug}/${worldSlug}`
                    : null
                }
              />
```

- [ ] **Step 5: Run the WorldPreview + ConnectScreen tests**

Run: `npx vitest run src/screens/lobby/__tests__/WorldPreview.test.tsx src/screens/__tests__/ConnectScreen.reference.test.tsx`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/screens/lobby/WorldPreview.tsx src/screens/ConnectScreen.tsx src/screens/lobby/__tests__/WorldPreview.test.tsx
git commit -m "feat(lobby): world-scoped Lore link + genre-themed preview card wired from ConnectScreen"
```

---

### Task 8: Confirm the lobby no longer references `ReferenceLinks` (component is RETAINED)

`ReferenceLinks` is **not** dead code — `src/components/GameBoard/widgets/NarrativeWidget.tsx:27` renders it as the in-game reference surface. The lobby's relocation of Rules→header and Lore→card removes only the *lobby* usage (done in Task 6). The component and its unit tests stay for the in-game caller. This task is a verification gate, not a deletion.

**Files:** (none changed — verification only)

- [ ] **Step 1: Confirm the lobby no longer imports it, but the in-game caller still does**

Run: `grep -rn "ReferenceLinks" src --include="*.tsx" --include="*.ts" | grep -v "__tests__"`
Expected: NO match in `src/screens/ConnectScreen.tsx` (lobby usage gone after Task 6), and a SURVIVING match in `src/components/GameBoard/widgets/NarrativeWidget.tsx` plus the component definition `src/components/ReferenceLinks.tsx`.

> If `ConnectScreen.tsx` still shows up, Task 6 Step 3's import removal was missed — go back and remove `import { ReferenceLinks } ...` and the `<ReferenceLinks .../>` element.
> Do **NOT** delete `ReferenceLinks.tsx` or its tests — the in-game NarrativeWidget depends on it.

- [ ] **Step 2: Verify the in-game ReferenceLinks tests still pass (untouched by this work)**

Run: `npx vitest run src/components/__tests__/ReferenceLinks.test.tsx src/components/__tests__/ReferenceLinks.disabled.test.tsx src/components/GameBoard/widgets/__tests__/NarrativeWidget.test.tsx`
Expected: PASS — the in-game reference surface is unchanged.

- [ ] **Step 3: No commit** (verification-only task; nothing changed).

---

### Task 9: Full gate + manual verification

- [ ] **Step 1: Lint**

Run: `npm run lint` (from `sidequest-ui/`)
Expected: PASS (no unused imports — confirm `ReferenceLinks` and the old `worldItems` are fully gone; confirm `OptionItem`/`OptionGroup` imports in `ConnectScreen` are both used).

- [ ] **Step 2: Full UI test suite**

Run: `npx vitest run`
Expected: PASS. Record any failure NOT present on a clean pre-change `develop` as a regression to fix before proceeding.

- [ ] **Step 3: Build**

Run: `npm run build`
Expected: succeeds (TypeScript types resolve — `ChromeArchetype` imports, `OptionGroup`, `WorldPreview` props).

- [ ] **Step 4: Manual verification (the three fixes, live)**

Start the stack (`just up` from the orchestrator root) and open the lobby. Confirm:
1. **Grouping:** worlds appear under sticky genre headers; scrolling keeps the current genre header pinned; the selected/restored world is scrolled into view (not clipped at the top).
2. **Links:** each genre header shows a **Rules** link opening `/reference/rules/{genre}`; the preview card shows a **Lore** link opening `/reference/lore/{genre}/{world}`; there is no link block under the list.
3. **Theming (the leak):** enter a world, return to the lobby — the lobby shell is the neutral **house** chrome, NOT the entered genre. Inspect `<html>`: `data-archetype="house"` in the lobby. Select different-genre worlds — only the **preview card** changes typeface (`data-archetype` on the card element), the shell stays house.

- [ ] **Step 5: Final commit (if any polish landed)**

```bash
git add -A
git commit -m "chore(lobby): lint/build polish for grouped picker + scoped theming"
```

---

## Notes for the implementer

- **Branch first.** Per repo policy `sidequest-ui` is gitflow off `develop`: `git checkout -b feat/lobby-grouped-picker-scoped-theming` before Task 1. All commits land on that branch; open a PR to `develop` at the end.
- **`bg-background` token:** the sticky header uses `bg-background` so list rows scroll under it opaquely. If that Tailwind token isn't configured, use `bg-[var(--background)]` (the codebase already uses the `var(--…)` arbitrary-value form for `--primary`).
- **Palette vs archetype (out of scope):** the preview card adopts the genre's *fonts/borders* (archetype) but colors still come from the root palette (`useGenreTheme`). Full per-card palette is explicitly out of scope (see spec §Open Items). Don't try to scope `useGenreTheme` here.
- **In-game chrome unchanged:** `resolveRootArchetype` returns the genre archetype for `creation`/`game`, so the in-world experience is byte-for-byte as before. Only the `connect` phase changed.
- **Slug-mode:** in slug-mode the `connect` phase is transient and `ConnectScreen` is skipped; the root will briefly read `house` before `creation` applies the genre. This is acceptable (the genre re-applies on the next phase) and needs no special-casing.

## Self-Review

- **Spec coverage:** §A grouping → Tasks 5–6. §B Rules→header / Lore→card / remove ReferenceLinks *from the lobby* (component kept for in-game NarrativeWidget) → Tasks 5, 7, 8. §C house archetype + scoped applier + lobby-root house + card scope → Tasks 1–4, 7. Accessibility (single radiogroup, header `role="presentation"`, `aria-label` links, `scroll-mt`) → Tasks 5, 7. Scrollbar/height → Task 6 (`max-h-[70vh]`) + Task 5 (auto-scroll, sticky headers). Testing list → per-task tests + Task 9 gate. All spec sections mapped.
- **Placeholder scan:** no TBD/TODO; every code step shows full code; commands have expected output. The one deliberately-deferred item (house visual fine-tuning, palette-per-card) is logged as out-of-scope, not left as an in-plan placeholder.
- **Type consistency:** `ChromeArchetype` (4 members incl. `house`), `applyArchetypeToElement`/`useChromeArchetype(archetype)`/`useScopedChromeArchetype(ref, archetype)`, `OptionGroup {slug,label,rulesHref,items}`, `WorldPreview` props `archetype?`/`loreHref?`, `resolveRootArchetype(phase, currentGenre)` — names and signatures are identical everywhere they appear across Tasks 1–9.
