#!/usr/bin/env python3
"""Capture the /ws/watcher OTEL span stream to a JSONL file.

Usage: watcher_capture.py <out.jsonl>   (runs until killed)
Each line is one raw watcher message (JSON). The dashboard ('GM panel') consumes
the same stream, so this is a faithful proxy for the router-trace the Sebastien-lens
AC asks us to evaluate.
"""
import asyncio
import sys
import websockets

OUT = sys.argv[1] if len(sys.argv) > 1 else "watcher.jsonl"
URL = "ws://127.0.0.1:8765/ws/watcher"


async def main():
    async with websockets.connect(URL, max_size=None) as ws:
        with open(OUT, "a", buffering=1) as f:
            async for msg in ws:
                f.write(msg if isinstance(msg, str) else msg.decode())
                f.write("\n")


asyncio.run(main())
