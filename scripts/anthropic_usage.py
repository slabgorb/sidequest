#!/usr/bin/env python3
"""Pull org-level Usage & Cost from the Anthropic Admin API.

Requires an ADMIN key (``sk-ant-admin…``), NOT the workspace inference key
SideQuest runs on — the cost/usage endpoints reject ``sk-ant-api…`` keys.
Reads the key from ``ANTHROPIC_ADMIN_KEY`` (falls back to ``ANTHROPIC_API_KEY``
only so the failure is a clear 401 rather than "no key").

Usage:
    export ANTHROPIC_ADMIN_KEY=sk-ant-admin-...
    python scripts/anthropic_usage.py                # today, 1d bucket
    python scripts/anthropic_usage.py --days 7        # last 7 days
    python scripts/anthropic_usage.py --raw           # dump full JSON

No third-party deps (stdlib urllib) so it runs anywhere uv/python is present.
Prints HTTP status + response body on error rather than swallowing it.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

_BASE = "https://api.anthropic.com"
_VERSION = "2023-06-01"

# NOTE: health bands are intentionally NOT applied here. Daily totals punish
# you for playing more — a $47 day over 300 turns is healthy, the same $47 over
# 10 turns is a cache footgun. The meaningful signal is cost-PER-TURN, which
# this org-billing endpoint cannot compute (it has no turn/request count). The
# per-turn bands live server-side on the `narration.turn.total_cost_usd` span
# (see sidequest-server anthropic_cost.cost_band). This script stays a pure
# daily-$ reconciliation against the console Cost page.


def _key() -> str:
    key = os.environ.get("ANTHROPIC_ADMIN_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        sys.exit("No ANTHROPIC_ADMIN_KEY (or ANTHROPIC_API_KEY) in env.")
    if not key.startswith("sk-ant-admin"):
        print(
            "WARNING: key is not an admin key (sk-ant-admin…); the cost/usage "
            "endpoints will likely 401/403.",
            file=sys.stderr,
        )
    return key


def _get(path: str, params: dict[str, object], key: str) -> dict:
    # urlencode with doseq so list params (group_by[]) expand correctly.
    query = urllib.parse.urlencode(params, doseq=True)
    url = f"{_BASE}{path}?{query}"
    req = urllib.request.Request(
        url,
        headers={"x-api-key": key, "anthropic-version": _VERSION},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        sys.exit(f"HTTP {exc.code} on {path}\n{body}")
    except urllib.error.URLError as exc:
        sys.exit(f"Network error on {path}: {exc}")


def _rfc3339(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _day_floor(dt: datetime) -> datetime:
    """Snap to 00:00 UTC. cost_report only accepts day-aligned bounds and 400s
    ('ending date must be after starting date') when a sub-day window collapses
    into a single day bucket."""
    return dt.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=1, help="lookback window in days (default 1)")
    ap.add_argument("--bucket", default="1d", help="bucket_width: 1d / 1h / 1m (default 1d)")
    ap.add_argument("--raw", action="store_true", help="print full JSON responses")
    args = ap.parse_args()

    key = _key()
    now = datetime.now(timezone.utc)

    # cost_report only accepts day-aligned bounds and 400s on a sub-day window.
    # Floor to midnight UTC and span at least one full day (incl. today) so
    # --days 1 works. Usage report is happy with timestamp precision.
    cost_start = _rfc3339(_day_floor(now - timedelta(days=args.days)))
    cost_end = _rfc3339(_day_floor(now) + timedelta(days=1))
    usage_start = _rfc3339(now - timedelta(days=args.days))
    usage_end = _rfc3339(now)

    print(f"Window: {cost_start} → {cost_end}  bucket={args.bucket}\n")

    # --- Cost report (billed amount; 'amount' is a string in CENTS despite
    # currency=USD — divide by 100 for dollars. Verified against the console
    # Cost page 2026-05-25: 17198.23758 → $171.98). ---
    cost = _get(
        "/v1/organizations/cost_report",
        {"starting_at": cost_start, "ending_at": cost_end, "bucket_width": args.bucket},
        key,
    )
    # --- Usage report: messages (token + cache breakdown) ---
    usage = _get(
        "/v1/organizations/usage_report/messages",
        {
            "starting_at": usage_start,
            "ending_at": usage_end,
            "bucket_width": args.bucket,
            "group_by[]": ["model"],
        },
        key,
    )

    if args.raw:
        print("=== COST REPORT ===")
        print(json.dumps(cost, indent=2))
        print("\n=== USAGE REPORT (messages) ===")
        print(json.dumps(usage, indent=2))
        return

    # --- Cost: sum the string 'amount' (cents) per day bucket → dollars. ---
    print("=== COST (USD, billed) ===")
    grand = 0.0
    for bucket in cost.get("data", []):
        day = (bucket.get("starting_at") or "")[:10]
        cents = sum(float(r.get("amount", 0)) for r in bucket.get("results", []))
        grand += cents
        print(f"  {day}   ${cents / 100:>10,.2f}")
    print(f"  {'TOTAL':10}  ${grand / 100:>10,.2f}")

    # --- Usage: token + cache breakdown summed across all models. ---
    usage_totals: dict[str, float] = {}
    for bucket in usage.get("data", []):
        for r in bucket.get("results", []):
            for k, v in r.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    usage_totals[k] = usage_totals.get(k, 0) + v

    print("\n=== USAGE TOTALS (tokens, all models) ===")
    for k, v in sorted(usage_totals.items(), key=lambda kv: -kv[1]):
        print(f"  {k:30s} {v:,.0f}")
    print("\n(Use --raw to see per-bucket / per-model structure.)")


if __name__ == "__main__":
    main()
