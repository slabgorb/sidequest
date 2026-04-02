"""playtest_otlp.py — OTLP receiver and parsing.

Accepts Claude Code OTEL telemetry (logs, metrics, traces) via HTTP POST,
parses tool invocations and token usage, and broadcasts to dashboard browsers.
See ADR-058.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import deque

from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)


# ── Attribute helpers ──────────────────────────────────────────────────────────


def _attrs_to_dict(attrs: list[dict]) -> dict[str, str | int]:
    """Convert OTLP attribute array to a flat dict."""
    result: dict[str, str | int] = {}
    for attr in attrs:
        key = attr.get("key", "")
        value = attr.get("value", {})
        if "stringValue" in value:
            result[key] = value["stringValue"]
        elif "intValue" in value:
            result[key] = int(value["intValue"])
    return result


# ── Parse functions ────────────────────────────────────────────────────────────


def parse_log_records(payload: dict) -> list[dict]:
    """Parse OTLP /v1/logs payload, extracting tool_result events.

    Returns a list of event dicts with source='claude_otel'.
    Non-tool_result log records are filtered out.
    """
    events: list[dict] = []
    for resource_log in payload.get("resourceLogs", []):
        for scope_log in resource_log.get("scopeLogs", []):
            for record in scope_log.get("logRecords", []):
                body = record.get("body", {}).get("stringValue", "")
                if body != "tool_result":
                    continue
                attrs = _attrs_to_dict(record.get("attributes", []))
                events.append({
                    "source": "claude_otel",
                    "type": "tool_result",
                    "tool_name": attrs.get("tool_name", ""),
                    "tool_id": attrs.get("tool_id", ""),
                    "duration_ms": attrs.get("duration_ms", 0),
                    "timestamp_ns": record.get("timeUnixNano", ""),
                })
    return events


def parse_metric_records(payload: dict) -> list[dict]:
    """Parse OTLP /v1/metrics payload, extracting claude_code.token.usage metrics.

    Returns a list of event dicts with source='claude_otel'.
    Non-token metrics are filtered out.
    """
    events: list[dict] = []
    for resource_metric in payload.get("resourceMetrics", []):
        for scope_metric in resource_metric.get("scopeMetrics", []):
            for metric in scope_metric.get("metrics", []):
                if metric.get("name") != "claude_code.token.usage":
                    continue
                sum_data = metric.get("sum", {})
                for dp in sum_data.get("dataPoints", []):
                    attrs = _attrs_to_dict(dp.get("attributes", []))
                    events.append({
                        "source": "claude_otel",
                        "type": "token_usage",
                        "value": int(dp.get("asInt", 0)),
                        "token_type": attrs.get("token_type", ""),
                        "timestamp_ns": dp.get("timeUnixNano", ""),
                    })
    return events


def parse_trace_spans(payload: dict) -> list[dict]:
    """Parse OTLP /v1/traces payload, extracting spans.

    Returns a list of event dicts with source='claude_otel'.
    Duration is converted from nanoseconds to milliseconds.
    """
    events: list[dict] = []
    for resource_span in payload.get("resourceSpans", []):
        for scope_span in resource_span.get("scopeSpans", []):
            for span in scope_span.get("spans", []):
                start_ns = int(span.get("startTimeUnixNano", 0))
                end_ns = int(span.get("endTimeUnixNano", 0))
                duration_ms = (end_ns - start_ns) // 1_000_000
                events.append({
                    "source": "claude_otel",
                    "type": "span",
                    "name": span.get("name", ""),
                    "span_id": span.get("spanId", ""),
                    "trace_id": span.get("traceId", ""),
                    "duration_ms": duration_ms,
                    "start_ns": start_ns,
                })
    return events


# ── Span buffer ────────────────────────────────────────────────────────────────


class OtlpSpanBuffer:
    """Bounded FIFO buffer for OTEL span events.

    Stores up to max_size events. When full, oldest events are evicted first.
    Late-joining browsers call get_all() to receive history.
    """

    def __init__(self, max_size: int = 500) -> None:
        self.max_size: int = max_size
        self._buffer: deque[dict] = deque(maxlen=max_size)

    def add(self, event: dict) -> None:
        """Add an event to the buffer. Evicts oldest if at capacity."""
        self._buffer.append(event)

    def get_all(self) -> list[dict]:
        """Return a copy of all buffered events, oldest first."""
        return list(self._buffer)

    def __len__(self) -> int:
        return len(self._buffer)


# ── Module-level span buffer (shared with dashboard broadcast) ─────────────────

_otlp_buffer = OtlpSpanBuffer(max_size=500)


# ── OTLP HTTP receiver ────────────────────────────────────────────────────────

# Route table: OTLP endpoint path → parser function
_OTLP_ROUTES: dict[str, callable] = {}


def _register_routes() -> None:
    """Populate route table after parse functions are defined."""
    _OTLP_ROUTES["/v1/logs"] = parse_log_records
    _OTLP_ROUTES["/v1/metrics"] = parse_metric_records
    _OTLP_ROUTES["/v1/traces"] = parse_trace_spans


_register_routes()


async def _handle_otlp_request(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    broadcast_fn: callable,
) -> None:
    """Handle a single HTTP request to the OTLP receiver."""
    try:
        # Read request line
        request_line = await asyncio.wait_for(reader.readline(), timeout=5.0)
        if not request_line:
            writer.close()
            return

        parts = request_line.decode("utf-8", errors="replace").strip().split(" ")
        method = parts[0] if len(parts) >= 1 else ""
        path = parts[1] if len(parts) >= 2 else ""

        # Read headers
        content_length = 0
        while True:
            line = await asyncio.wait_for(reader.readline(), timeout=5.0)
            if line in (b"\r\n", b"\n", b""):
                break
            header = line.decode("utf-8", errors="replace").strip().lower()
            if header.startswith("content-length:"):
                content_length = int(header.split(":", 1)[1].strip())

        # Read body
        body = b""
        if content_length > 0:
            body = await asyncio.wait_for(reader.readexactly(content_length), timeout=10.0)

        if method != "POST" or path not in _OTLP_ROUTES:
            # 404 for unknown paths, 405 for non-POST
            status = "405 Method Not Allowed" if method != "POST" else "404 Not Found"
            writer.write(f"HTTP/1.1 {status}\r\nContent-Length: 0\r\n\r\n".encode())
            await writer.drain()
            writer.close()
            return

        # Parse and broadcast
        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, ValueError):
            writer.write(b"HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\n\r\n")
            await writer.drain()
            writer.close()
            return

        parser = _OTLP_ROUTES[path]
        events = parser(payload)

        for event in events:
            _otlp_buffer.add(event)
            await broadcast_fn(json.dumps(event))

        # 200 OK
        writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
        await writer.drain()

    except (asyncio.TimeoutError, ConnectionResetError, OSError) as exc:
        logger.debug("OTLP request error: %s", exc)
    finally:
        writer.close()


async def run_otlp_receiver(
    otlp_port: int,
    broadcast_fn: callable,
) -> None:
    """Start the OTLP HTTP receiver on the given port.

    Accepts POST to /v1/logs, /v1/metrics, /v1/traces.
    Parses events and broadcasts them via broadcast_fn.
    """
    async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await _handle_otlp_request(reader, writer, broadcast_fn)

    server = await asyncio.start_server(handler, "0.0.0.0", otlp_port)
    console.print(
        f"[bold cyan]OTLP Receiver: http://localhost:{otlp_port}/v1/{{logs,metrics,traces}}[/bold cyan]"
    )
    async with server:
        await server.serve_forever()


def get_otlp_buffer() -> OtlpSpanBuffer:
    """Return the module-level OTLP span buffer for late-join history."""
    return _otlp_buffer
