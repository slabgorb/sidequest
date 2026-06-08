#!/usr/bin/env python3
"""Dark-spend reconciliation — story 91-5 (epic 91 "Dark Spend").

Compares Anthropic Admin API billed totals against the server's
instrumented spend (from GET /api/debug/cost/instrumented).
Fires a loud alert (ERROR log + non-zero exit) when the gap exceeds
DARK_SPEND_ALERT_THRESHOLD_PCT (10.0%).

Usage:
    export ANTHROPIC_ADMIN_KEY=sk-ant-admin-...
    export SIDEQUEST_SERVER_URL=http://localhost:8765   # optional
    python scripts/reconcile_dark_spend.py
    python scripts/reconcile_dark_spend.py --days 1

No third-party deps beyond stdlib + the existing anthropic_usage.py logic.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# Threshold pinned: tests verify this is exactly 10.0.
# Any intentional change MUST update test_91_5_dark_spend_reconcile.py too.
DARK_SPEND_ALERT_THRESHOLD_PCT: float = 10.0

_BASE = "https://api.anthropic.com"
_VERSION = "2023-06-01"
_DEFAULT_SERVER_URL = "http://localhost:8765"


@dataclass(frozen=True)
class ReconcileResult:
    """Immutable result of one reconciliation run."""

    instrumented_usd: float
    billed_usd: float
    gap_pct: float
    alert: bool


def compute_gap(*, instrumented_usd: float, billed_usd: float) -> ReconcileResult:
    """Compute the dark-spend gap between billed and instrumented totals.

    gap_pct = (billed - instrumented) / billed * 100
    alert fires when gap_pct > DARK_SPEND_ALERT_THRESHOLD_PCT.

    Division-by-zero guard: when billed == 0, gap is 0% (nothing to reconcile).
    """
    if billed_usd <= 0.0:
        gap_pct = 0.0
    else:
        gap_pct = max(0.0, (billed_usd - instrumented_usd) / billed_usd * 100.0)
    alert = gap_pct > DARK_SPEND_ALERT_THRESHOLD_PCT
    return ReconcileResult(
        instrumented_usd=instrumented_usd,
        billed_usd=billed_usd,
        gap_pct=gap_pct,
        alert=alert,
    )


def fetch_billed_usd(admin_key: str | None, *, days: int = 1) -> float:
    """Fetch the billed total (USD) from the Anthropic Admin API.

    Raises (not sys.exit) on HTTP errors or network failures so callers can
    distinguish an API error from an alert condition. (No Silent Fallbacks.)

    Args:
        admin_key: The sk-ant-admin-… key. If None, falls back to env.
        days: Lookback window in days.

    Raises:
        ValueError: If no admin key is available (names the env var).
        urllib.error.HTTPError: On HTTP 4xx/5xx from the Admin API.
        urllib.error.URLError: On network-level failures.
    """
    key = admin_key or os.environ.get("ANTHROPIC_ADMIN_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError(
            "No ANTHROPIC_ADMIN_KEY in environment — required for dark-spend reconciliation. "
            "Set ANTHROPIC_ADMIN_KEY=sk-ant-admin-... before running this script."
        )

    now = datetime.now(timezone.utc)

    def _day_floor(dt: datetime) -> datetime:
        return dt.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    def _rfc3339(dt: datetime) -> str:
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    start = _rfc3339(_day_floor(now - timedelta(days=days)))
    end = _rfc3339(_day_floor(now) + timedelta(days=1))

    params = {"starting_at": start, "ending_at": end, "bucket_width": "1d"}
    query = urllib.parse.urlencode(params)
    url = f"{_BASE}/v1/organizations/cost_report?{query}"
    req = urllib.request.Request(
        url,
        headers={"x-api-key": key, "anthropic-version": _VERSION},
        method="GET",
    )
    # Raises HTTPError / URLError on failures — not swallowed.
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())

    # cost_report amount is a string in CENTS despite currency=USD.
    total_cents = 0.0
    for bucket in data.get("data", []):
        for r in bucket.get("results", []):
            total_cents += float(r.get("amount", 0))
    return total_cents / 100.0


def fetch_instrumented_usd(server_url: str | None = None) -> float:
    """Fetch the instrumented spend total from the running server.

    Calls GET /api/debug/cost/instrumented on the server.
    Returns 0.0 if the server is unreachable (the gap will then be billed_usd,
    which is exactly the worst-case signal to alert on).
    """
    base = (server_url or os.environ.get("SIDEQUEST_SERVER_URL") or _DEFAULT_SERVER_URL).rstrip("/")
    url = f"{base}/api/debug/cost/instrumented"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        return float(data.get("instrumented_usd", 0.0))
    except (urllib.error.URLError, OSError):
        logger.warning(
            "Could not reach server at %s — treating instrumented_usd as 0.0", url
        )
        return 0.0


def emit_alert(result: ReconcileResult) -> None:
    """Log a loud ERROR when a dark-spend gap is detected.

    Called by main() and can be called directly by callers who have an
    already-computed ReconcileResult (e.g. tests, cron wrappers).
    Only logs when result.alert is True.
    """
    if result.alert:
        logger.error(
            "DARK SPEND ALERT: gap=%.1f%% billed=$%.4f instrumented=$%.4f — "
            "%.1f%% of Anthropic spend is uninstrumented. "
            "Check epic-91 doctrine: every call must go through the OTEL choke point.",
            result.gap_pct,
            result.billed_usd,
            result.instrumented_usd,
            result.gap_pct,
        )


def _post_result_to_server(result: ReconcileResult, server_url: str | None = None) -> None:
    """POST reconciliation result to the server's dark-spend endpoint.

    Best-effort: logs a warning on failure but does not raise — the
    script's main job is reconciliation + alerting, not server delivery.
    """
    base = (server_url or os.environ.get("SIDEQUEST_SERVER_URL") or _DEFAULT_SERVER_URL).rstrip("/")
    url = f"{base}/api/debug/cost/reconciliation"
    payload = json.dumps({
        "instrumented_usd": result.instrumented_usd,
        "billed_usd": result.billed_usd,
        "gap_pct": result.gap_pct,
        "alert": result.alert,
    }).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
    except (urllib.error.URLError, OSError) as exc:
        logger.warning("Could not post reconciliation result to server: %s", exc)


def main() -> None:
    """Run the dark-spend reconciliation and exit with appropriate code.

    Exit codes:
        0 — reconciliation clean (gap <= threshold)
        1 — dark-spend alert fired (gap > threshold)
        2 — error fetching data (Admin API failure, missing key, etc.)
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=1, help="lookback window in days (default 1)")
    ap.add_argument("--server-url", default=None, help="SideQuest server URL (default: $SIDEQUEST_SERVER_URL or http://localhost:8765)")
    args = ap.parse_args()

    admin_key = os.environ.get("ANTHROPIC_ADMIN_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not admin_key:
        logger.error(
            "ANTHROPIC_ADMIN_KEY not set — cannot fetch billed totals. "
            "Set ANTHROPIC_ADMIN_KEY=sk-ant-admin-... to run reconciliation."
        )
        sys.exit(2)

    try:
        billed = fetch_billed_usd(admin_key, days=args.days)
    except Exception as exc:
        logger.error("Failed to fetch billed totals from Admin API: %s", exc)
        sys.exit(2)

    instrumented = fetch_instrumented_usd(args.server_url)
    result = compute_gap(instrumented_usd=instrumented, billed_usd=billed)

    logger.info(
        "Reconciliation: billed=$%.4f instrumented=$%.4f gap=%.1f%% alert=%s",
        result.billed_usd,
        result.instrumented_usd,
        result.gap_pct,
        result.alert,
    )

    _post_result_to_server(result, args.server_url)

    if result.alert:
        emit_alert(result)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
