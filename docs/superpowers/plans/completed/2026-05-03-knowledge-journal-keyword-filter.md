# KnowledgeJournal Keyword Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a whitespace-tokenized AND keyword filter to the KnowledgeJournal widget, layered on top of the existing category tabs and sort control.

**Architecture:** Pure client-side state added to the existing single-file component. New text input above the category tablist, `useState` for the keyword string, an additional filter pass (`String.includes` per token, AND across tokens) appended to the existing category-filter pipeline. No backend changes, no new files outside the single component and its existing test file.

**Tech Stack:** React 18 + TypeScript, Vitest, @testing-library/react, fireEvent. Existing test patterns in `KnowledgeJournal.test.tsx` (factory `entry()`, `getByTestId('journal-entry')`).

**Spec:** `docs/superpowers/specs/2026-05-03-knowledge-journal-keyword-filter-design.md`

**Files touched:**
- Modify: `sidequest-ui/src/components/KnowledgeJournal.tsx` (~30–40 lines added)
- Modify: `sidequest-ui/src/components/__tests__/KnowledgeJournal.test.tsx` (add new `describe` block)

---

### Task 1: Single keyword filter (input + case-insensitive substring)

**Files:**
- Modify: `sidequest-ui/src/components/KnowledgeJournal.tsx`
- Test: `sidequest-ui/src/components/__tests__/KnowledgeJournal.test.tsx`

- [ ] **Step 1: Write the failing tests**

Add this `describe` block to the bottom of `KnowledgeJournal.test.tsx` (above the closing of the file, after the existing `Edge cases` block):

```tsx
// ---------------------------------------------------------------------------
// AC-9: Keyword filter (spec 2026-05-03)
// ---------------------------------------------------------------------------

describe('AC-9: Keyword filter', () => {
  it('renders a keyword filter input', () => {
    render(<KnowledgeJournal entries={ENTRIES} />);
    expect(screen.getByTestId('keyword-filter')).toBeInTheDocument();
  });

  it('filters entries to those whose content contains the keyword (case-insensitive)', () => {
    render(<KnowledgeJournal entries={ENTRIES} />);
    const input = screen.getByTestId('keyword-filter') as HTMLInputElement;

    fireEvent.change(input, { target: { value: 'corruption' } });

    // f1 (grove tree radiates corruption), f4 (find the source of corruption),
    // f5 (Root-bonding allows you to sense corruption) — three matches.
    expect(screen.getAllByTestId('journal-entry')).toHaveLength(3);
    expect(screen.queryByText(/Elder Mirova/i)).not.toBeInTheDocument();
  });

  it('matches case-insensitively', () => {
    render(<KnowledgeJournal entries={ENTRIES} />);
    const input = screen.getByTestId('keyword-filter') as HTMLInputElement;

    fireEvent.change(input, { target: { value: 'MIROVA' } });

    expect(screen.getAllByTestId('journal-entry')).toHaveLength(1);
    expect(screen.getByText(/Elder Mirova/i)).toBeInTheDocument();
  });

  it('matches substrings, not whole words', () => {
    render(<KnowledgeJournal entries={ENTRIES} />);
    const input = screen.getByTestId('keyword-filter') as HTMLInputElement;

    // "rune" is a substring of "runes" (f3)
    fireEvent.change(input, { target: { value: 'rune' } });

    expect(screen.getAllByTestId('journal-entry')).toHaveLength(1);
    expect(screen.getByText(/ancient runes/i)).toBeInTheDocument();
  });

  it('shows all entries when input is empty', () => {
    render(<KnowledgeJournal entries={ENTRIES} />);
    const input = screen.getByTestId('keyword-filter') as HTMLInputElement;

    fireEvent.change(input, { target: { value: 'corruption' } });
    fireEvent.change(input, { target: { value: '' } });

    expect(screen.getAllByTestId('journal-entry')).toHaveLength(ENTRIES.length);
  });

  it('shows all entries when input is whitespace-only', () => {
    render(<KnowledgeJournal entries={ENTRIES} />);
    const input = screen.getByTestId('keyword-filter') as HTMLInputElement;

    fireEvent.change(input, { target: { value: '   ' } });

    expect(screen.getAllByTestId('journal-entry')).toHaveLength(ENTRIES.length);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run from `sidequest-ui/`:

```bash
npx vitest run src/components/__tests__/KnowledgeJournal.test.tsx
```

Expected: 6 new tests fail with `Unable to find an element by: [data-testid="keyword-filter"]` (or similar). Existing 18+ tests still pass.

- [ ] **Step 3: Add the input + state + filter to KnowledgeJournal.tsx**

Modify `sidequest-ui/src/components/KnowledgeJournal.tsx`:

a) Add a third `useState` after the existing two (around line 15):

```tsx
const [keyword, setKeyword] = useState('');
```

b) Replace the `filtered` derivation (currently lines 33–36) with this expanded version that adds the keyword filter pass after the category filter:

```tsx
const categoryFiltered =
  activeCategory === 'All'
    ? entries
    : entries.filter((e) => e.category === activeCategory);

const tokens = keyword
  .toLowerCase()
  .split(/\s+/)
  .filter((t) => t.length > 0);

const filtered =
  tokens.length === 0
    ? categoryFiltered
    : categoryFiltered.filter((e) => {
        const content = e.content.toLowerCase();
        return tokens.every((t) => content.includes(t));
      });
```

c) Add the input element as the first child of the outer `<div data-testid="knowledge-journal">` returned at line 50. Insert this block **before** the existing `<div role="tablist">`:

```tsx
<div className="mb-3">
  <input
    type="text"
    data-testid="keyword-filter"
    value={keyword}
    onChange={(e) => setKeyword(e.target.value)}
    placeholder="Filter by keyword"
    className="w-full text-sm px-2 py-1 rounded
               border border-border/40 bg-transparent
               text-foreground placeholder:text-muted-foreground/50
               focus:outline-none focus:border-border/70 transition-colors"
  />
</div>
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npx vitest run src/components/__tests__/KnowledgeJournal.test.tsx
```

Expected: All AC-9 tests pass plus all 18+ existing tests still pass.

- [ ] **Step 5: Commit**

```bash
git add src/components/KnowledgeJournal.tsx src/components/__tests__/KnowledgeJournal.test.tsx
git commit -m "feat(knowledge-journal): keyword filter — single-token substring match"
```

---

### Task 2: Multi-token AND-narrow

**Files:**
- Test: `sidequest-ui/src/components/__tests__/KnowledgeJournal.test.tsx` (add to AC-9 block)

The implementation already supports multi-token AND from Task 1 (the `tokens.every((t) => ...)` clause). This task pins the behavior with a test.

- [ ] **Step 1: Add the multi-token test**

Append this `it` to the `AC-9: Keyword filter` describe block:

```tsx
it('narrows by AND across multiple tokens', () => {
  render(<KnowledgeJournal entries={ENTRIES} />);
  const input = screen.getByTestId('keyword-filter') as HTMLInputElement;

  // "corruption sense" should match only f5 (Root-bonding allows you to
  // sense corruption) — both tokens present in content. f1 has corruption
  // but not sense; f4 has corruption but not sense.
  fireEvent.change(input, { target: { value: 'corruption sense' } });

  expect(screen.getAllByTestId('journal-entry')).toHaveLength(1);
  expect(screen.getByText(/Root-bonding/i)).toBeInTheDocument();
});

it('treats each whitespace-separated token as an independent substring', () => {
  render(<KnowledgeJournal entries={ENTRIES} />);
  const input = screen.getByTestId('keyword-filter') as HTMLInputElement;

  // f6 ("hooded figure was seen near the well at midnight") contains
  // both "well" and "midnight". Token order does not matter.
  fireEvent.change(input, { target: { value: 'midnight well' } });

  expect(screen.getAllByTestId('journal-entry')).toHaveLength(1);
  expect(screen.getByText(/hooded figure/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run tests to verify they pass (no impl change required)**

```bash
npx vitest run src/components/__tests__/KnowledgeJournal.test.tsx
```

Expected: Both new tests pass without code changes (Task 1's filter already tokenizes).

- [ ] **Step 3: Commit**

```bash
git add src/components/__tests__/KnowledgeJournal.test.tsx
git commit -m "test(knowledge-journal): pin multi-token AND-narrow behavior"
```

---

### Task 3: Empty-result variant

**Files:**
- Modify: `sidequest-ui/src/components/KnowledgeJournal.tsx`
- Test: `sidequest-ui/src/components/__tests__/KnowledgeJournal.test.tsx` (add to AC-9 block)

When the journal has entries but the active filters (category + keyword) leave zero matches, show a distinct message instead of a silently empty list.

- [ ] **Step 1: Write the failing test**

Append to the AC-9 describe block:

```tsx
it('shows empty-result message when filters yield zero matches', () => {
  render(<KnowledgeJournal entries={ENTRIES} />);
  const input = screen.getByTestId('keyword-filter') as HTMLInputElement;

  fireEvent.change(input, { target: { value: 'xyznomatch' } });

  expect(screen.queryAllByTestId('journal-entry')).toHaveLength(0);
  expect(screen.getByTestId('keyword-filter-empty')).toBeInTheDocument();
  expect(screen.getByTestId('keyword-filter-empty')).toHaveTextContent(/xyznomatch/);
});

it('does NOT show empty-result message when filter is empty', () => {
  render(<KnowledgeJournal entries={ENTRIES} />);
  expect(screen.queryByTestId('keyword-filter-empty')).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
npx vitest run src/components/__tests__/KnowledgeJournal.test.tsx
```

Expected: First new test fails (`Unable to find an element by: [data-testid="keyword-filter-empty"]`). Second test passes already.

- [ ] **Step 3: Add the empty-result branch**

In `KnowledgeJournal.tsx`, find the `<div className="space-y-2">` block (around line 104) that renders the entry list. Replace it with:

```tsx
<div className="space-y-2">
  {sorted.length === 0 && tokens.length > 0 && (
    <p
      data-testid="keyword-filter-empty"
      className="text-muted-foreground/60 italic text-sm py-4"
    >
      No entries match "{tokens.join(' ')}"
    </p>
  )}
  {sorted.map((entry) => (
    <div key={entry.fact_id} data-testid="journal-entry" className="text-sm border-l-2 border-border/30 pl-3 py-1">
      <p className="text-foreground/80">{entry.content}</p>
      <div className="flex gap-2 text-xs text-muted-foreground/50 mt-0.5">
        <span>{entry.category}</span>
        <span>Turn {entry.learned_turn}</span>
        {entry.source && <span>{entry.source}</span>}
        {entry.confidence && <span>{entry.confidence}</span>}
        {entry.is_new && (
          <span
            data-testid="knowledge-new-pill"
            className="inline-flex items-center rounded-full bg-[var(--primary)]/25 px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--primary)]"
          >
            New
          </span>
        )}
      </div>
    </div>
  ))}
</div>
```

The only change is the new conditional `<p data-testid="keyword-filter-empty">` block before the entry map. Everything else is unchanged.

- [ ] **Step 4: Run tests to verify they pass**

```bash
npx vitest run src/components/__tests__/KnowledgeJournal.test.tsx
```

Expected: Both empty-result tests pass; full suite still green.

- [ ] **Step 5: Commit**

```bash
git add src/components/KnowledgeJournal.tsx src/components/__tests__/KnowledgeJournal.test.tsx
git commit -m "feat(knowledge-journal): empty-result message when keyword filter matches nothing"
```

---

### Task 4: Clear button

**Files:**
- Modify: `sidequest-ui/src/components/KnowledgeJournal.tsx`
- Test: `sidequest-ui/src/components/__tests__/KnowledgeJournal.test.tsx` (add to AC-9 block)

A small × button that appears inside the input when there's text and resets the filter on click.

- [ ] **Step 1: Write the failing tests**

Append to the AC-9 describe block:

```tsx
it('renders a clear button when the input has text', () => {
  render(<KnowledgeJournal entries={ENTRIES} />);
  const input = screen.getByTestId('keyword-filter') as HTMLInputElement;

  expect(screen.queryByTestId('keyword-filter-clear')).not.toBeInTheDocument();

  fireEvent.change(input, { target: { value: 'corruption' } });

  expect(screen.getByTestId('keyword-filter-clear')).toBeInTheDocument();
});

it('clears the keyword when the clear button is clicked', () => {
  render(<KnowledgeJournal entries={ENTRIES} />);
  const input = screen.getByTestId('keyword-filter') as HTMLInputElement;

  fireEvent.change(input, { target: { value: 'corruption' } });
  expect(screen.getAllByTestId('journal-entry')).toHaveLength(3);

  fireEvent.click(screen.getByTestId('keyword-filter-clear'));

  expect(input.value).toBe('');
  expect(screen.getAllByTestId('journal-entry')).toHaveLength(ENTRIES.length);
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npx vitest run src/components/__tests__/KnowledgeJournal.test.tsx
```

Expected: Both new tests fail (`Unable to find an element by: [data-testid="keyword-filter-clear"]`).

- [ ] **Step 3: Add the clear button**

Replace the existing keyword input wrapper in `KnowledgeJournal.tsx` (the `<div className="mb-3">` you added in Task 1) with this version that wraps input + clear button in a relative container:

```tsx
<div className="mb-3 relative">
  <input
    type="text"
    data-testid="keyword-filter"
    value={keyword}
    onChange={(e) => setKeyword(e.target.value)}
    placeholder="Filter by keyword"
    className="w-full text-sm px-2 py-1 pr-7 rounded
               border border-border/40 bg-transparent
               text-foreground placeholder:text-muted-foreground/50
               focus:outline-none focus:border-border/70 transition-colors"
  />
  {keyword.length > 0 && (
    <button
      type="button"
      data-testid="keyword-filter-clear"
      onClick={() => setKeyword('')}
      aria-label="Clear keyword filter"
      className="absolute right-1 top-1/2 -translate-y-1/2
                 text-muted-foreground/60 hover:text-foreground
                 text-sm leading-none px-1"
    >
      ×
    </button>
  )}
</div>
```

Changes from Task 1's version:
- Wrapper has `relative` for absolute-positioned button
- Input has `pr-7` to leave room for the × on the right
- New `<button>` rendered conditionally when `keyword.length > 0`

- [ ] **Step 4: Run tests to verify they pass**

```bash
npx vitest run src/components/__tests__/KnowledgeJournal.test.tsx
```

Expected: Both clear-button tests pass; full suite still green.

- [ ] **Step 5: Commit**

```bash
git add src/components/KnowledgeJournal.tsx src/components/__tests__/KnowledgeJournal.test.tsx
git commit -m "feat(knowledge-journal): clear button (×) for keyword filter"
```

---

### Task 5: Wiring — stacks with category tab + dock-mounted assertion

**Files:**
- Test: `sidequest-ui/src/components/__tests__/KnowledgeJournal.test.tsx` (add to AC-9 block)

Two assertions: keyword filter intersects with category tab (not replaces), and KnowledgeJournal is actually wired into the dock via `KnowledgeWidget` (per CLAUDE.md "Every Test Suite Needs a Wiring Test").

- [ ] **Step 1: Write the stacks-with-category test**

Append to the AC-9 describe block:

```tsx
it('stacks with the active category tab (intersection, not replace)', () => {
  render(<KnowledgeJournal entries={ENTRIES} />);
  const input = screen.getByTestId('keyword-filter') as HTMLInputElement;

  // Activate Person tab — should show f2 (Elder Mirova) and f6 (hooded figure).
  fireEvent.click(screen.getByRole('tab', { name: /person/i }));
  expect(screen.getAllByTestId('journal-entry')).toHaveLength(2);

  // Type 'well' — both f2 (...beneath the well) and f6 (...near the well...)
  // contain 'well'. With Person tab still active, both should remain.
  fireEvent.change(input, { target: { value: 'well' } });
  expect(screen.getAllByTestId('journal-entry')).toHaveLength(2);

  // Type 'midnight' — only f6 contains 'midnight'. Person tab still active.
  fireEvent.change(input, { target: { value: 'midnight' } });
  expect(screen.getAllByTestId('journal-entry')).toHaveLength(1);
  expect(screen.getByText(/hooded figure/i)).toBeInTheDocument();

  // Verify no Lore entries (e.g. f3 ancient runes) leak in despite matching nothing.
  expect(screen.queryByText(/ancient runes/i)).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Write the dock-wiring assertion**

Append to the AC-9 describe block:

```tsx
it('KnowledgeWidget (the dock wrapper) renders KnowledgeJournal with the keyword filter', async () => {
  // Wiring guard: per CLAUDE.md "Every Test Suite Needs a Wiring Test" —
  // unit tests prove KnowledgeJournal works in isolation; this confirms
  // it's mounted from the production dock path so the keyword filter is
  // actually reachable by players.
  const mod = await import('@/components/GameBoard/widgets/KnowledgeWidget');
  expect(typeof mod.KnowledgeWidget).toBe('function');

  const sample: KnowledgeEntry[] = [ENTRIES[0]];
  render(<mod.KnowledgeWidget entries={sample} />);
  expect(screen.getByTestId('keyword-filter')).toBeInTheDocument();
});
```

- [ ] **Step 3: Run tests to verify behavior**

```bash
npx vitest run src/components/__tests__/KnowledgeJournal.test.tsx
```

Expected: Both stacks-with-category and dock-wiring tests pass without further code changes (KnowledgeWidget already wraps KnowledgeJournal with the entries prop).

If the dock-wiring test fails because `KnowledgeWidget` has a different prop name or signature, **stop and inspect** `sidequest-ui/src/components/GameBoard/widgets/KnowledgeWidget.tsx` — adjust the test to match the real signature (this is the test catching real wiring drift, which is its job). Do not silently change the component to make the test pass.

- [ ] **Step 4: Run the full UI test suite**

```bash
npx vitest run
```

Expected: Entire test suite green. No regressions in other components.

- [ ] **Step 5: TypeScript check**

```bash
npx tsc --noEmit
```

Expected: Exit 0, no errors.

- [ ] **Step 6: Commit**

```bash
git add src/components/__tests__/KnowledgeJournal.test.tsx
git commit -m "test(knowledge-journal): stacks-with-category + dock-mount wiring guard"
```

---

### Task 6: Push branch + open PR

**Files:** none (git operations only)

- [ ] **Step 1: Push the feature branch**

The Dev workflow assumes work is done on a `feat/...` branch. If you're not on one, create it first from `develop` (sidequest-ui's default per `repos.yaml`):

```bash
# Only if you started directly on develop:
# git checkout -b feat/knowledge-journal-keyword-filter

git push -u origin "$(git branch --show-current)"
```

- [ ] **Step 2: Open the PR against `develop`**

```bash
gh pr create --base develop --title "feat(knowledge-journal): keyword filter (token AND match)" --body "$(cat <<'EOF'
## Summary
- Adds a whitespace-tokenized AND keyword filter to `KnowledgeJournal`.
- Live-filter input above the existing category tablist; case-insensitive substring per token; stacks with the active category tab and sort.
- New empty-result variant ("No entries match …") for when filters yield zero matches.
- × clear button when the input has text.
- ~30–40 lines added to one component file plus an `AC-9` `describe` block in the existing test file.

Spec: `docs/superpowers/specs/2026-05-03-knowledge-journal-keyword-filter-design.md`
Plan: `docs/superpowers/plans/2026-05-03-knowledge-journal-keyword-filter.md`

## Test plan
- [x] `npx vitest run src/components/__tests__/KnowledgeJournal.test.tsx` — 11 new AC-9 tests passing
- [x] `npx vitest run` — full UI suite green
- [x] `npx tsc --noEmit` — clean
- [ ] Live verification: open Knowledge tab in any active session, type `Bunjo Kestrel`, confirm only entries containing both substrings appear

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 3: Confirm PR URL printed**

The PR URL should print to stdout. Capture it in the next session note.

---

## Self-review notes

**Spec coverage (against `2026-05-03-knowledge-journal-keyword-filter-design.md`):**

| Spec section | Tasks |
|---|---|
| Parse: split on whitespace, discard empty tokens | Task 1 (impl + tests for empty/whitespace) |
| Match: empty → no filter | Task 1 (`shows all entries when input is empty/whitespace`) |
| Match: AND across tokens, case-insensitive substring | Task 1 + Task 2 |
| Stacks with category tabs (intersection) | Task 5 |
| Sort unaffected | Implicit — sort runs after filter; existing AC-7 tests still pass (Task 5 step 4 full suite) |
| Input above tablist | Task 1 step 3 (insert before `<div role="tablist">`) |
| Placeholder "Filter by keyword" | Task 1 step 3 |
| Clear × inside input | Task 4 |
| Live filter on each keystroke | Task 1 step 3 (`onChange={(e) => setKeyword(e.target.value)}`) |
| Empty-result variant `No entries match "<keyword>"` | Task 3 |
| Existing zero-entries empty state preserved | Task 3 leaves the early-return guard at line 25 untouched |
| No new dependencies / no backend / no persistence | All tasks — verified by file-touch list |
| Wiring test per CLAUDE.md | Task 5 dock-mount assertion |

**Placeholder scan:** none. Every step has either runnable code or an exact command + expected outcome.

**Type consistency:**
- `data-testid` values used: `keyword-filter`, `keyword-filter-clear`, `keyword-filter-empty`, `journal-entry` (existing). All consistent across Task 1–5.
- State variable name: `keyword` / `setKeyword` (consistent throughout).
- Local derivation names: `categoryFiltered` (intermediate), `tokens`, `filtered` (matches existing). The original component had `filtered` directly from category; we now insert `categoryFiltered` between, then re-bind `filtered`. Existing downstream code (`sorted = [...filtered]`) unchanged.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-03-knowledge-journal-keyword-filter.md`. Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
