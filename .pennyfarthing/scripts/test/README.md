# Test Scripts

Scripts for test infrastructure and benchmarking.

## Test-result caching

Caching moved into the Python package (SOUL #9, #11). The `testing-runner`
subagent writes each run's summary to an isolated, RUN_ID-keyed file — never
the live workflow session file (gh #53):

```bash
printf '%s\n' "$RESULT_SUMMARY" | python -m pf.session.test_cache "$RUN_ID"
# → .session/test-runs/${RUN_ID}.md
```

See `pf.session.test_cache` (`test_run_cache_path`, `is_live_session_file`,
`write_test_run_cache`).

> **Note:** the legacy bash helpers (`test-setup.sh`, `test-cache.sh`) and the
> judge scripts that this directory once documented are no longer shipped here.
> Test execution is `pf check` / `scripts/workflow/check.py`.

## Ownership

- **Primary users:** TEA agent, testing-runner subagent
- **Maintained by:** Core Pennyfarthing team
