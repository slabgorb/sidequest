---
name: testing
description: Test commands and patterns for TDD workflow. This skill should be used when running tests, debugging test failures, setting up test infrastructure, or writing new tests. Provides framework-agnostic patterns that projects customize.
---

# Testing Skill

<run>
Main test commands for running the test suite:

```bash
just test              # If using just
npm test               # If using npm
go test ./...          # If using Go directly
```

These commands execute the full test suite and are the primary entry point for validating code changes.
</run>

<output>
Test output varies by framework:

- **Go tests:** Display pass/fail status for each test, summary of tests run, coverage reports (if enabled), and PASS/FAIL result code
- **Node/npm tests (Vitest/Jest):** Shows test file results, individual test names, execution time, coverage percentages (if enabled), and pass/fail summary
- **Just:** Delegates to underlying test runner, output depends on what test command is configured

Output includes execution time and a final summary line indicating total tests passed/failed.
</output>

## When to Use This Skill

- Running tests (backend, frontend, or all)
- Debugging test failures
- Setting up test containers/infrastructure
- Writing new tests
- Pre-commit verification
- Understanding TDD workflow

## TDD Workflow (RED → GREEN → REFACTOR)

```
1. TEA writes failing tests (RED)
2. Dev implements code to pass tests (GREEN)
3. Dev refactors while keeping tests GREEN
4. Reviewer validates quality
```

## Quick Reference

```bash
# Setup test infrastructure (run once per session)
# Project-specific: check your justfile or package.json

# Run all tests
just test              # If using just
npm test               # If using npm
go test ./...          # If using Go directly

# Run specific test patterns
just test-api -run "TestName"     # Go pattern
npm test -- -t "test name"        # Jest/Vitest pattern
```

## Test Command Patterns

### Go (Backend)

```bash
# Run all tests
go test ./...

# Run tests in specific package
go test ./internal/handlers

# Run tests matching pattern
go test -run "TestCreate" ./...

# Verbose output
go test -v ./internal/handlers

# With coverage
go test -cover ./...
```

### Node/React (Frontend)

```bash
# Run all tests (Vitest)
npm test

# Run tests matching pattern
npm test -- -t "button"

# Watch mode
npm test -- --watch

# Coverage
npm test -- --coverage
```

## Test File Naming Conventions

| Type | Go Pattern | TypeScript Pattern |
|------|------------|-------------------|
| Unit test | `*_test.go` | `*.test.ts`, `*.test.tsx` |
| Integration | `*_integration_test.go` | `*.integration.test.ts` |
| E2E | N/A | `*.e2e.test.ts` |

## Reference Documentation

- **Troubleshooting:** See `references/troubleshooting.md`
- **TDD Policy:** See `references/tdd-policy.md` (project-specific)
- **Backend Patterns:** See `references/backend-patterns.md` (project-specific)
- **Frontend Patterns:** See `references/frontend-patterns.md` (project-specific)

## Project Customization

Projects should create their own testing skill in `.claude/project/skills/testing/` with:
- Project-specific test commands
- Custom patterns and conventions
- Infrastructure setup instructions
