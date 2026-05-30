#!/usr/bin/env python3
"""Extract 59-8-relevant router/confrontation spans from the live watcher capture.

Usage: turn_spans.py [from_line]
  from_line: only consider watcher.jsonl lines AFTER this line number (checkpoint).
Prints: router decompose (latency/dispatch/retry/confidence), subsystem decisions,
confrontation lifecycle, encounter spans, and ANY dispatch_engagement.*.mismatch
(the AC lie-detector). Ends by printing the current line count for the next checkpoint.
"""
import json
import sys

FROM = int(sys.argv[1]) if len(sys.argv) > 1 else 0
PATH = "watcher.jsonl"

ROUTER = {"intent_router.decompose", "intent_router.subsystem", "intent_router.failed",
          "intent_router.dispatch_bank", "intent_router.lethality_arbitrate"}
lines = open(PATH).read().splitlines()
total = len(lines)

def keep(name):
    if not name:
        return False
    return (name in ROUTER
            or name.startswith("confrontation")
            or "encounter" in name
            or "dispatch_engagement" in name)

for i, line in enumerate(lines[FROM:], start=FROM + 1):
    line = line.strip()
    if not line:
        continue
    try:
        o = json.loads(line)
    except Exception:
        continue
    f = o.get("fields") or {}
    n = f.get("name")
    if not keep(n):
        continue
    ts = o.get("timestamp", "")[11:23]
    rest = {k: v for k, v in f.items() if k not in ("name", "duration_ms")}
    flag = "  <<< MISMATCH" if "dispatch_engagement" in (n or "") and "mismatch" in (n or "") else ""
    print(f"{ts}  {n}{flag}")
    print(f"      {rest}")

print(f"\n[checkpoint] watcher.jsonl now has {total} lines (pass {total} as from_line next turn)")
