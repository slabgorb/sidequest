# Test Troubleshooting Guide

## Tests Timing Out

```bash
# Ensure test infrastructure is running
just test-setup        # Or project-specific setup command

# Check container status
docker ps

# Increase timeout if needed
go test -timeout 60s ./...
```

## "No Tests to Run" Message

### Go Tests

The `-run` flag filters by **test function name**, not by file or domain:
- `-run "User"` matches `TestUserCreate` but NOT `TestCreateAccount`
- The pattern is a regex, case-sensitive

```bash
# Run ALL tests in a package (no name filter)
go test ./internal/handlers/...

# Run tests with "Create" in name in specific package
go test -run "Create" ./internal/handlers
```

### JavaScript/TypeScript Tests

The `-t` flag filters by test description:

```bash
# Run tests matching description
npm test -- -t "should create user"

# Run all tests in a file
npm test -- path/to/file.test.ts
```

## Case Sensitivity

### Go
- `-run "User"` - Correct (matches TestUser...)
- `-run "user"` - Won't match (Go regex is case-sensitive)

### Jest/Vitest
- `-t "user"` - Case-insensitive by default

## Package/Path Format

### Go
```bash
./internal/handlers      # Correct - relative with ./
internal/handlers        # May not work without ./
./internal/handlers/...  # Include subpackages
```

### Node
```bash
src/components           # Relative path
./src/components         # Also works
```

## Tests Passing Locally but Failing in CI

1. **Environment differences** - Check env vars
2. **Race conditions** - Run tests multiple times locally
3. **Database state** - Ensure clean state between tests

```bash
# Run full test suite to catch integration issues
just test

# Run tests with race detection (Go)
go test -race ./...
```

## Container Issues

```bash
# Restart test containers
docker-compose -f docker-compose.test.yml down
docker-compose -f docker-compose.test.yml up -d

# Check container logs
docker logs <container-name>

# Verify connectivity
docker exec <container-name> pg_isready  # Postgres
docker exec <container-name> redis-cli ping  # Redis
```

## Database Connection Errors

```bash
# Check environment variables
echo $TEST_DATABASE_URL

# Verify database is accepting connections
psql $TEST_DATABASE_URL -c "SELECT 1"
```

## Common Patterns

### Flaky Tests

1. Check for timing dependencies
2. Look for shared state between tests
3. Ensure proper cleanup in teardown
4. Consider using test isolation

### Memory Issues

```bash
# Run with memory limit (Go)
go test -memprofile mem.out ./...

# Check for goroutine leaks
go test -race ./...
```
