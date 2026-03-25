#!/bin/bash
# Generate collision-resistant timestamp for benchmark runs
# Format: YYYYMMDDTHHMMSS_NNNNNN (with microseconds)
# Usage: RUN_TS=$(./scripts/utils/run-timestamp.sh)

# macOS date supports %N for nanoseconds, truncate to microseconds
date -u +%Y%m%dT%H%M%S_%N | cut -c1-22
