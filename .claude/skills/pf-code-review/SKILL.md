---
name: code-review
description: Code review checklists and patterns for Pennyfarthing. Use when reviewing PRs, self-reviewing code, or checking for common issues before commit.
---

# Code Review Skill

<run>Review code against the checklists below. Focus on authorization, error handling, TypeScript/React patterns, and performance.</run>

<output>Code review comments using [MUST FIX], [SUGGESTION], [QUESTION], [NICE] prefixes</output>

## Overview

This skill provides code review patterns and checklists for the Pennyfarthing project. Use this when reviewing PRs or self-reviewing before commit.

## Review Checklists

### API Handler Review

- [ ] **Authorization check present** - Uses `utils.GetClientIDsForQuery()` for admin bypass
- [ ] **Input validation** - Request body and params validated
- [ ] **Error handling** - Appropriate status codes, no internal leaks
- [ ] **Response format** - Consistent with other endpoints
- [ ] **Tests** - Cover happy path + edge cases + error cases

### UI Component Review

- [ ] **Props typed correctly** - Interface defined, no `any`
- [ ] **Loading states** - Shows spinner/skeleton while fetching
- [ ] **Error states** - Graceful error display with retry option
- [ ] **Empty states** - Meaningful message when no data
- [ ] **Accessibility** - Proper ARIA labels, keyboard navigation
- [ ] **No hardcoded strings** - Ready for i18n

### Database Changes

- [ ] **Migration reversible** - Can roll back cleanly
- [ ] **Indexes present** - For common query patterns
- [ ] **FK constraints** - Appropriate relationships defined
- [ ] **NULL semantics** - Comments explain NULL meaning
- [ ] **Default values** - Sensible defaults for new columns

### TypeScript/React

- [ ] **Type imports use `import type`** - Required for build
- [ ] **No unused imports** - Remove or use
- [ ] **No `any` types** - Use proper types
- [ ] **useCallback/useMemo** - For expensive operations in deps
- [ ] **Error boundaries** - Around risky components

## Common Review Issues

### Authorization

```go
// BAD - blocks admins with empty ClientIDs
if len(clientIDs) == 0 {
    return http.StatusForbidden
}

// GOOD - use centralized utility
clientIDs, err := utils.GetClientIDsForQuery(user, h.db)
```

### Error Messages

```go
// BAD - leaks internals
http.Error(w, err.Error(), 500)

// GOOD - generic message, log details
log.Error("database error", "error", err, "user_id", user.ID)
http.Error(w, "Internal server error", 500)
```

### TypeScript Imports

```typescript
// BAD - causes build errors
import { SomeType } from './types';

// GOOD
import type { SomeType } from './types';
```

### React Query

```typescript
// BAD - query runs even when not ready
const { data } = useQuery({
  queryKey: ['items', clientId],
  queryFn: () => fetchItems(clientId),
});

// GOOD - only runs when clientId is set
const { data } = useQuery({
  queryKey: ['items', clientId],
  queryFn: () => fetchItems(clientId),
  enabled: !!clientId,
});
```

## Approval Criteria

### Must Have for Approval

1. **Tests pass** - All CI checks green
2. **No security issues** - Auth, input validation, no SQL injection
3. **No breaking changes** - Or migration path provided
4. **Code follows patterns** - Consistent with existing codebase

### Nice to Have

1. Documentation updated
2. Performance considered
3. Error messages helpful
4. Edge cases handled

## Security Checklist

- [ ] **No SQL injection** - Use parameterized queries
- [ ] **No XSS** - Sanitize user input in UI
- [ ] **Auth on all endpoints** - Middleware applied
- [ ] **Client isolation** - Multi-tenant data filtered
- [ ] **No secrets in code** - Use env vars or KMS
- [ ] **SSRF protection** - URL validation for external calls

## Performance Checklist

- [ ] **N+1 queries** - Use preloading/joins
- [ ] **Pagination** - For list endpoints
- [ ] **Indexes** - For filtered/sorted columns
- [ ] **Memoization** - For expensive React renders
- [ ] **Bundle size** - No unnecessary imports

## Review Comments Format

### Requesting Changes

```
**[MUST FIX]** This leaks internal error details to the client.
Suggest: Use a generic message and log the details server-side.
```

### Suggestions

```
**[SUGGESTION]** Consider using `useMemo` here since this calculation
runs on every render.
```

### Questions

```
**[QUESTION]** What happens if `clientId` is undefined? Should we
add an early return or enabled flag?
```

### Praise

```
**[NICE]** Good use of the centralized auth utility here!
```

## Recent Learnings

| Date | Issue | Resolution |
|------|-------|------------|
| Dec 2024 | Admin 403 errors | Use `GetClientIDsForQuery()` |
| Dec 2024 | Type import errors | Use `import type` |
| Dec 2024 | Role-based filtering | Check analyst vs manager vs admin |
| Dec 2024 | Error boundaries | Wrap risky components |
