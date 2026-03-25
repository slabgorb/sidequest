# Step 3: Code Content

<step-meta>
number: 3
name: code-content
gate: true
next: step-04-scoring
</step-meta>

<purpose>
Author the code block for the scenario with intentionally seeded bugs, vulnerabilities, or test targets appropriate to the category and difficulty level.
</purpose>

<prerequisites>
- All metadata fields populated (step 2)
- Category is code-based (code-review, dev, tea, test-writing)
</prerequisites>

<instructions>
1. Select the programming language and filename
2. Author realistic code that serves as the scenario's subject matter
3. Seed intentional issues appropriate to the category:
   - **code-review**: bugs, vulnerabilities, code quality issues across severity levels
   - **dev**: implementation with bugs or incomplete features to fix
   - **tea**: clean code that needs comprehensive test coverage
   - **test-writing**: focused module requiring targeted tests
4. For tea/test-writing categories: also create `tests` block (expected test structure) and optionally a `stub` block
5. Ensure code is realistic and self-contained
6. Track which issues are seeded and where (you'll catalog them in step 4)
</instructions>

<actions>
- Read: `{benchmarks_root}/{scenario_category}/` for existing scenarios as style reference
- Write: code content to scenario draft
</actions>

## Code Authoring Guidelines

### Language Selection
Choose a language that fits the scenario. Common choices:
- **Go** — good for service code, concurrency issues
- **Python** — good for data processing, API code
- **TypeScript** — good for frontend, Node.js services
- **Java** — good for enterprise patterns, OOP issues

### Severity Distribution (for code-review scenarios)

| Difficulty | Critical | High | Medium | Low |
|------------|----------|------|--------|-----|
| easy | 1-2 | 2-3 | 2-3 | 1-2 |
| medium | 3-4 | 3-4 | 3-5 | 2-3 |
| hard | 4-5 | 4-6 | 5-7 | 3-4 |
| extreme | 5+ | 6+ | 7+ | 4+ |

### Issue Types by Category

**code-review issues:**
- SQL injection, XSS, command injection (critical)
- Missing auth checks, data exposure (high)
- Error handling gaps, resource leaks (medium)
- Style issues, magic numbers (low)

**dev issues:**
- Logic errors, off-by-one, race conditions
- Missing edge case handling
- Incomplete implementations

**tea/test-writing targets:**
- Happy path scenarios
- Edge cases and boundary conditions
- Error handling and failure modes
- Concurrency and state management
- Security-related behaviors

### Code Quality

- Code should look realistic (like it came from a real codebase)
- Include proper imports, types, and structure
- Issues should be naturally embedded, not artificially obvious
- Mix of obvious and subtle issues for the chosen difficulty
- 50-150 lines is typical; complex scenarios may go longer

<output>
Complete code block with:
- `language`: programming language
- `filename`: realistic filename
- `content`: the full code with seeded issues
- For tea/test-writing: optional `tests` and `stub` blocks
- Mental inventory of all seeded issues (formalized in step 4)
</output>

<gate>
## Completion Criteria
- [ ] Language and filename selected
- [ ] Code is syntactically valid and realistic
- [ ] Issues seeded at appropriate severity levels for difficulty
- [ ] At least 3 severity levels covered (for code-review)
- [ ] Code is self-contained (no external dependencies needed to understand)
- [ ] For tea/test-writing: test targets are clear from the code
</gate>

<next-step>
After code content is complete, proceed to step-04-scoring.md to catalog issues and configure scoring.
</next-step>

## Failure Modes

- Making issues too obvious (all on one line, clearly wrong)
- Not covering enough severity levels
- Writing unrealistic code that no developer would actually write
- Seeding issues that require external context to identify
