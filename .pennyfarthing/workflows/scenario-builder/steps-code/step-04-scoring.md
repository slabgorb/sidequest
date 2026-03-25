# Step 4: Issue Catalog & Scoring

<step-meta>
number: 4
name: scoring
gate: true
next: step-05-review
</step-meta>

<purpose>
Catalog every seeded issue with IDs, locations, and severities. Configure scoring weights and verify the math adds up.
</purpose>

<prerequisites>
- Code content authored with seeded issues (step 3)
- Mental inventory of all issues from code authoring
</prerequisites>

<instructions>
1. Catalog each seeded issue in `known_issues` (for code-review) or `baseline_tests` (for tea/test-writing):
   - Assign a unique SCREAMING_SNAKE_CASE ID (e.g., `SQL_INJECTION_1`, `TEST_SUCCESSFUL_PAYMENT`)
   - Reference the location (line number or function name)
   - Write a clear description
   - Assign severity: critical, high, medium, low
2. Optionally add `bonus_issues` — things a thorough reviewer might catch beyond baseline
3. Optionally add `red_herrings` — things that look like issues but aren't (requires: type, description, severity)
4. Configure `scoring` section:
   - `total_issues`: count of all baseline issues
   - `weights`: points per severity level (standard: critical=3, high=2, medium=1, low=0.5)
   - `max_score`: calculated sum of (count * weight) per severity
5. Verify the math: issue counts per severity times weights must equal max_score
</instructions>

## Issue Catalog Format

### For code-review and dev categories:

```yaml
known_issues:
  critical:
    - id: SQL_INJECTION_1
      location: "line 18 (GetUser)"
      description: "SQL injection via string formatting with user input"
  high:
    - id: NO_AUTH_CHECK
      location: "line 35 (UpdateEmail)"
      description: "No authorization check - any user can update any email"
  medium:
    - id: ROWS_NOT_CLOSED
      location: "line 86 (ListUsers)"
      description: "rows.Close() not called, resource leak"
  low:
    - id: MISSING_CONTENT_TYPE
      location: "multiple handlers"
      description: "JSON responses don't set Content-Type header"
```

### For tea and test-writing categories:

```yaml
baseline_tests:
  happy_path:
    - id: TEST_SUCCESSFUL_PAYMENT
      description: "Basic successful payment flow"
  validation:
    - id: TEST_ZERO_AMOUNT
      description: "Reject zero amount payment"
  error_handling:
    - id: TEST_CARD_DECLINED
      description: "Handle card declined from gateway"

bonus_tests:
  concurrency:
    - id: TEST_CONCURRENT_REQUESTS
      description: "Concurrent requests with same idempotency key"
```

### Red Herrings (optional, any category):

```yaml
red_herrings:
  - type: style
    description: "Variable naming follows team convention despite looking unusual"
    severity: low
  - type: performance
    description: "Appears inefficient but is correct for the use case"
    severity: medium
```

## Scoring Math Verification

Calculate and verify:
```
max_score = (critical_count * 3) + (high_count * 2) + (medium_count * 1) + (low_count * 0.5)
```

Example: 3 critical + 4 high + 4 medium + 2 low = (9) + (8) + (4) + (1) = 22

For tea/test-writing, scoring is simpler:
```yaml
scoring:
  baseline_tests: 20   # count of baseline tests
  bonus_tests: 15      # count of bonus tests
```

<output>
Complete scoring configuration:
- All issues cataloged with IDs, locations, descriptions, severities
- Optional bonus issues and red herrings
- Scoring weights and max_score calculated
- Math verified
</output>

<gate>
## Completion Criteria
- [ ] Every seeded issue has a unique ID
- [ ] Every issue has location reference and description
- [ ] Issue counts per severity are accurate
- [ ] Scoring weights configured
- [ ] max_score math verified (count * weight per severity = total)
- [ ] Red herrings (if any) have required fields: type, description, severity
</gate>

<next-step>
After scoring is configured and verified, proceed to step-05-review.md for assembly and review.
</next-step>

## Failure Modes

- Forgetting to catalog an issue that was seeded in the code
- Miscounting issues (total_issues doesn't match actual count)
- Math error in max_score calculation
- Red herrings missing required fields (will fail validator)
