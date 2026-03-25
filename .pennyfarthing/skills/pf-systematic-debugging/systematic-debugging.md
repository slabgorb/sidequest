---
name: systematic-debugging
description: Systematic debugging approach for isolating and fixing issues. Use when debugging failures, investigating errors, bisecting regressions, or validating fixes.
---

# /pf-systematic-debugging - Systematic Debugging Skill

<run>systematic-debugging</run>

<output>Systematic debugging approach for isolating and fixing issues. Use when debugging failures, investigating errors, bisecting regressions, or validating fixes.</output>

**Purpose:** Guide methodical debugging to find root causes, not just symptoms.

**Use when:** Bug reports, test failures, unexpected behavior, regressions.

---

## When to Use This Skill

- Debugging test failures or unexpected behavior
- Investigating error messages or stack traces
- Bisecting to find when a regression was introduced
- Validating that a fix addresses root cause, not just symptoms
- Intermittent failures that are hard to reproduce

---

## The Debugging Cycle

```
1. REPRODUCE  → Make the failure happen reliably
2. ISOLATE    → Narrow down to minimal reproducer
3. HYPOTHESIZE → Form theory about root cause
4. TEST       → Validate or invalidate hypothesis
5. FIX        → Implement solution
6. VERIFY     → Confirm fix addresses root cause
```

### Quick Reference

| Phase | Question to Answer | Output |
|-------|-------------------|--------|
| REPRODUCE | Can I make it fail consistently? | Reliable reproduction steps |
| ISOLATE | What's the minimal code/input that triggers it? | Minimal reproducer |
| HYPOTHESIZE | What could cause this behavior? | Ranked list of theories |
| TEST | Does evidence support my theory? | Confirmed or refuted hypothesis |
| FIX | What's the minimal change to fix it? | Working code |
| VERIFY | Does the fix address root cause? | Regression test |

---

## Phase 1: REPRODUCE

**Goal:** Make the failure happen reliably.

### Steps

1. **Document exact error** - Copy the full error message, stack trace, logs
2. **Capture environment** - Versions, configuration, system state
3. **Create reproduction steps** - Exact commands/actions to trigger
4. **Test reproduction** - Run it 3+ times to confirm consistency

### For Intermittent Failures

| Pattern | Approach |
|---------|----------|
| Race condition | Add delays, run in tight loop, stress test |
| State-dependent | Reset to clean state, document preconditions |
| Environment-specific | Compare working vs failing environments |
| Timing-dependent | Add timestamps, check for timeouts |

### Example

```bash
# Document the failure
$ npm test -- -t "user authentication"
# Error: Expected 200 but got 401

# Capture environment
$ node --version  # v18.17.0
$ npm --version   # 9.6.7

# Reproduction steps
1. Start fresh database: docker-compose down -v && docker-compose up -d
2. Run: npm test -- -t "user authentication"
3. Observe: 401 error on third test

# Verify reproduction
$ npm test -- -t "user authentication"  # Fails
$ npm test -- -t "user authentication"  # Fails
$ npm test -- -t "user authentication"  # Fails - consistent!
```

---

## Phase 2: ISOLATE

**Goal:** Narrow down to the smallest code/input that triggers the bug.

### Techniques

#### Binary Search (Code)

```
1. Find a known-good commit
2. Find the failing commit
3. git bisect between them
4. Each step: test, mark good/bad
5. Arrive at first bad commit
```

```bash
git bisect start
git bisect bad HEAD
git bisect good v1.2.0
# Git checks out middle commit
npm test -- -t "failing test"
git bisect bad  # or good
# Repeat until found
git bisect reset
```

#### Minimal Reproducer

1. Start with failing test/code
2. Remove components one at a time
3. Stop when removal fixes the bug
4. The last removed component is involved

#### Variable Elimination

| Remove | Still fails? | Conclusion |
|--------|--------------|------------|
| External API calls | Yes | Not API-related |
| Database queries | No | Database-related |
| Specific table | Yes | Not that table |
| Auth middleware | No | Auth is involved |

### Example

```typescript
// Full failing code
async function createUser(data) {
  validateInput(data);
  const hash = await hashPassword(data.password);
  const user = await db.insert({ ...data, password: hash });
  await sendWelcomeEmail(user.email);
  return user;
}

// Minimal reproducer (isolated the issue)
async function createUser(data) {
  const user = await db.insert(data);  // Fails here!
  return user;
}
// Conclusion: Issue is in db.insert, not validation/email
```

---

## Phase 3: HYPOTHESIZE

**Goal:** Form testable theories about root cause.

### Common Root Causes

| Category | Examples |
|----------|----------|
| State | Uninitialized variable, stale cache, leftover data |
| Timing | Race condition, timeout, async ordering |
| Input | Edge case, null/undefined, empty collection, boundary |
| Environment | Missing env var, wrong version, config mismatch |
| Logic | Off-by-one, wrong operator, incorrect condition |

### Hypothesis Formation

1. **Read the error message carefully** - Often tells you exactly what's wrong
2. **Check recent changes** - `git log --oneline -20`, `git diff HEAD~5`
3. **Consider edge cases** - What if null? Empty? Max value?
4. **Look for patterns** - When does it fail vs succeed?

### Rank Hypotheses

```
Hypothesis 1 (HIGH): Database connection timing out
- Evidence: Error mentions timeout, happens under load
- Test: Check connection pool settings

Hypothesis 2 (MEDIUM): Invalid input not validated
- Evidence: Stack trace shows null pointer in parser
- Test: Add input validation logging

Hypothesis 3 (LOW): Bug in library
- Evidence: Nothing obvious in our code
- Test: Check library issues, try downgrade
```

---

## Phase 4: TEST

**Goal:** Validate or invalidate each hypothesis.

### Testing Approaches

| Approach | When to Use |
|----------|-------------|
| Add logging | Need to see values at runtime |
| Debugger breakpoint | Need to inspect state interactively |
| Unit test | Can isolate the specific function |
| Print statements | Quick check in specific location |
| Assertion | Verify assumption holds |

### Logging Strategy

```typescript
// Add strategic logging
console.log('[DEBUG] Input:', JSON.stringify(data));
console.log('[DEBUG] Before DB call, user:', user?.id);
console.log('[DEBUG] After DB call, result:', result);
console.log('[DEBUG] Query took:', endTime - startTime, 'ms');
```

### Hypothesis Testing

```
HYPOTHESIS: Connection pool exhausted under load

TEST 1: Check pool stats
> db.pool.stats()
{ active: 50, idle: 0, waiting: 12 }  // Pool full!

TEST 2: Increase pool size
> config.pool.max = 100
> Rerun test
> PASS

CONCLUSION: Hypothesis confirmed. Pool too small.
```

### When Hypothesis is Wrong

If evidence doesn't support your theory:
1. Don't force-fit the evidence
2. Return to HYPOTHESIZE phase
3. Form new theory based on new observations
4. Repeat until you find the cause

---

## Phase 5: FIX

**Goal:** Implement the minimal change that fixes the issue.

### Fix Principles

1. **Fix the root cause, not the symptom**
   - BAD: Add try/catch to hide the error
   - GOOD: Fix why the error occurs

2. **Minimal change**
   - Change only what's necessary
   - Don't refactor while fixing bugs

3. **One fix per bug**
   - Don't bundle unrelated changes
   - Makes it clear what fixed what

### Fix Template

```typescript
// BEFORE: Bug - pool exhaustion under load
const pool = new Pool({ max: 10 });

// AFTER: Fix - increase pool size based on expected load
const pool = new Pool({
  max: 50,  // Increased from 10 to handle peak load
  idleTimeoutMillis: 30000,
});
```

---

## Phase 6: VERIFY

**Goal:** Confirm the fix addresses root cause and doesn't break anything else.

### Verification Checklist

- [ ] Original reproduction steps now pass
- [ ] New test case covers the bug (regression test)
- [ ] Existing tests still pass
- [ ] Fix doesn't introduce new issues
- [ ] Fix addresses root cause, not just symptom

### Write a Regression Test

```typescript
// This test should have caught the bug
test('handles concurrent requests without pool exhaustion', async () => {
  const requests = Array(100).fill(null).map(() => api.createUser());
  const results = await Promise.all(requests);
  expect(results.every(r => r.status === 201)).toBe(true);
});
```

### Symptom vs Root Cause Check

Ask yourself:
- "Would this bug happen again in a different form?"
- "Did I fix WHY it happened, or just WHAT happened?"

| Fix | Symptom or Root Cause? |
|-----|------------------------|
| Add null check | Symptom (why is it null?) |
| Initialize variable properly | Root cause |
| Increase timeout | Symptom (why is it slow?) |
| Fix N+1 query | Root cause |

---

## Debugging Anti-Patterns

### What NOT to Do

| Anti-Pattern | Why It's Bad | Instead |
|--------------|--------------|---------|
| Random changes | Introduces new bugs, wastes time | Follow the cycle |
| Fix without reproducing | Can't verify fix works | Always reproduce first |
| Blame external factors | Delays finding real cause | Assume it's your code |
| Skip verification | Bug may not be fixed | Always verify |
| Big refactor as "fix" | Hides what actually fixed it | Minimal changes |

### Common Traps

1. **Confirmation bias** - Looking for evidence that supports your theory
2. **Premature optimization** - Fixing performance before correctness
3. **Tunnel vision** - Fixating on one hypothesis
4. **Solution jumping** - Skipping to fix before understanding

---

## Quick Debugging Commands

### Git Bisect (Find Regression)

```bash
git bisect start
git bisect bad                 # Current commit is bad
git bisect good v1.0.0         # Known good commit
# Run test, then:
git bisect good  # or bad
# Repeat until found
git bisect reset
```

### Find Recent Changes

```bash
# What changed recently?
git log --oneline -20
git diff HEAD~5

# Who changed this file?
git blame path/to/file.ts

# When did this line change?
git log -p -S "problematic code" -- path/to/file.ts
```

### Check Running Processes

```bash
# What's using resources?
ps aux | grep node
lsof -i :3000

# Check memory/CPU
top -l 1 | head -20
```

---

## Visual/UI Debugging with Playwright MCP

For debugging UI issues in Electron apps or web applications, use the `interactive-debug` workflow
with Playwright MCP.

### Electron Apps (Requires CDP)

1. **Start with CDP enabled:**
   ```bash
   # Via justfile (if configured)
   just myapp cdp

   # Or direct
   electron --remote-debugging-port=9222 dist/main.js
   ```

2. **Get internal server URL:**
   ```bash
   curl -s http://localhost:9222/json/list | grep '"url"'
   # Returns: "url": "http://localhost:60178/"
   ```

3. **Connect Playwright to internal URL (not CDP port):**
   ```
   mcp__playwright__browser_navigate to http://localhost:60178/
   mcp__playwright__browser_snapshot  # See accessibility tree
   ```

**Important:** Playwright MCP doesn't connect to CDP directly. It uses its own browser.
Connect to the app's internal server URL discovered via `/json/list`.

### Web Apps

Simply navigate to the dev server URL:
```
mcp__playwright__browser_navigate to http://localhost:3000/
```

### Playwright Debugging Commands

| Tool | Purpose |
|------|---------|
| `browser_snapshot` | Get accessibility tree (better than screenshots) |
| `browser_click` | Interact with elements |
| `browser_console_messages` | Check for JS errors |
| `browser_network_requests` | Debug API calls |

See: `/pf-workflow interactive-debug` for full workflow.

---

## Integration with Other Skills

| Skill | How It Complements |
|-------|-------------------|
| `/pf-testing` | Run tests to verify fixes |
| `/pf-agentic-patterns` | ReAct pattern for systematic investigation |
| `/pf-workflow interactive-debug` | UI debugging with Playwright MCP |

---

**Remember:** Debugging is detective work. Follow the evidence, test your theories, and fix the root cause. Rushing leads to band-aid fixes that break later.
