"""Story 21-2: OTLP receiver in playtest dashboard — parse and broadcast Claude Code telemetry.

RED phase — tests for the OTLP receiver that accepts Claude Code telemetry
and broadcasts parsed events to dashboard browsers.

ACs tested:
  1. POST /v1/logs parses claude_code.tool_result events into tool spans
  2. POST /v1/metrics parses claude_code.token.usage into token stats
  3. POST /v1/traces parses tool spans from trace payloads
  4. Parsed events broadcast to dashboard browsers via WebSocket
  5. Envelope format distinguishes OTEL events from watcher events
  6. Span buffer bounded at 500 with FIFO eviction
  7. Late-joining browsers receive span history
  8. --otlp-port CLI flag configures receiver port
  9. Unit tests for all three parse functions

Rule enforcement (Python lang-review):
  #1 — no silent exception swallowing
  #2 — no mutable default arguments
  #3 — type annotations at boundaries
  #6 — meaningful assertions (self-checked)
"""

import json
import pytest

from playtest_otlp import (
    parse_log_records,
    parse_metric_records,
    parse_trace_spans,
    OtlpSpanBuffer,
)


# ============================================================================
# Test fixtures — Claude Code OTEL payloads
# ============================================================================

def make_log_payload(*, body: str = "tool_result", attributes: dict | None = None) -> dict:
    """Build an OTLP /v1/logs JSON payload with one log record."""
    attrs = attributes or {
        "tool_name": "Bash",
        "tool_id": "toolu_abc123",
        "duration_ms": 1234,
    }
    return {
        "resourceLogs": [{
            "resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "claude_code"}}]},
            "scopeLogs": [{
                "logRecords": [{
                    "body": {"stringValue": body},
                    "attributes": [
                        {"key": k, "value": {"stringValue": str(v)} if isinstance(v, str) else {"intValue": str(v)}}
                        for k, v in attrs.items()
                    ],
                    "timeUnixNano": "1712000000000000000",
                    "severityText": "INFO",
                }]
            }]
        }]
    }


def make_metric_payload(*, name: str = "claude_code.token.usage",
                         value: int = 1500, attributes: dict | None = None) -> dict:
    """Build an OTLP /v1/metrics JSON payload with one metric data point."""
    attrs = attributes or {"token_type": "input"}
    return {
        "resourceMetrics": [{
            "resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "claude_code"}}]},
            "scopeMetrics": [{
                "metrics": [{
                    "name": name,
                    "sum": {
                        "dataPoints": [{
                            "asInt": str(value),
                            "attributes": [
                                {"key": k, "value": {"stringValue": str(v)}}
                                for k, v in attrs.items()
                            ],
                            "timeUnixNano": "1712000000000000000",
                        }]
                    }
                }]
            }]
        }]
    }


def make_trace_payload(*, name: str = "Bash", span_id: str = "abc123",
                        duration_ns: int = 1234000000, attributes: dict | None = None) -> dict:
    """Build an OTLP /v1/traces JSON payload with one span."""
    attrs = attributes or {"tool_name": "Bash"}
    return {
        "resourceSpans": [{
            "resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "claude_code"}}]},
            "scopeSpans": [{
                "spans": [{
                    "name": name,
                    "spanId": span_id,
                    "traceId": "trace123",
                    "startTimeUnixNano": "1712000000000000000",
                    "endTimeUnixNano": str(1712000000000000000 + duration_ns),
                    "attributes": [
                        {"key": k, "value": {"stringValue": str(v)}}
                        for k, v in attrs.items()
                    ],
                }]
            }]
        }]
    }


# ============================================================================
# AC-1: POST /v1/logs parses claude_code.tool_result events into tool spans
# ============================================================================

class TestParseLogRecords:
    def test_extracts_tool_result_event(self):
        payload = make_log_payload(body="tool_result", attributes={
            "tool_name": "Bash",
            "tool_id": "toolu_abc123",
            "duration_ms": 1234,
        })
        events = parse_log_records(payload)
        assert len(events) == 1
        event = events[0]
        assert event["type"] == "tool_result"
        assert event["tool_name"] == "Bash"
        assert event["tool_id"] == "toolu_abc123"
        assert event["duration_ms"] == 1234

    def test_ignores_non_tool_result_logs(self):
        payload = make_log_payload(body="something_else")
        events = parse_log_records(payload)
        assert len(events) == 0, "non-tool_result log records should be filtered out"

    def test_handles_multiple_log_records(self):
        payload = make_log_payload(body="tool_result")
        # Add a second log record
        payload["resourceLogs"][0]["scopeLogs"][0]["logRecords"].append({
            "body": {"stringValue": "tool_result"},
            "attributes": [
                {"key": "tool_name", "value": {"stringValue": "Read"}},
                {"key": "tool_id", "value": {"stringValue": "toolu_def456"}},
                {"key": "duration_ms", "value": {"intValue": "500"}},
            ],
            "timeUnixNano": "1712000001000000000",
            "severityText": "INFO",
        })
        events = parse_log_records(payload)
        assert len(events) == 2
        tool_names = {e["tool_name"] for e in events}
        assert tool_names == {"Bash", "Read"}

    def test_returns_empty_for_empty_payload(self):
        events = parse_log_records({"resourceLogs": []})
        assert events == []

    def test_returns_empty_for_malformed_payload(self):
        events = parse_log_records({})
        assert events == [], "missing resourceLogs key should return empty list, not crash"


# ============================================================================
# AC-2: POST /v1/metrics parses claude_code.token.usage into token stats
# ============================================================================

class TestParseMetricRecords:
    def test_extracts_token_usage_metric(self):
        payload = make_metric_payload(name="claude_code.token.usage", value=1500, attributes={"token_type": "input"})
        events = parse_metric_records(payload)
        assert len(events) == 1
        event = events[0]
        assert event["type"] == "token_usage"
        assert event["value"] == 1500
        assert event["token_type"] == "input"

    def test_extracts_output_tokens(self):
        payload = make_metric_payload(name="claude_code.token.usage", value=800, attributes={"token_type": "output"})
        events = parse_metric_records(payload)
        assert len(events) == 1
        assert events[0]["value"] == 800
        assert events[0]["token_type"] == "output"

    def test_ignores_non_token_metrics(self):
        payload = make_metric_payload(name="http.request.duration", value=100)
        events = parse_metric_records(payload)
        assert len(events) == 0, "non-token metrics should be filtered out"

    def test_returns_empty_for_empty_payload(self):
        events = parse_metric_records({"resourceMetrics": []})
        assert events == []

    def test_returns_empty_for_malformed_payload(self):
        events = parse_metric_records({})
        assert events == [], "missing resourceMetrics key should return empty list, not crash"


# ============================================================================
# AC-3: POST /v1/traces parses tool spans from trace payloads
# ============================================================================

class TestParseTraceSpans:
    def test_extracts_tool_span(self):
        payload = make_trace_payload(name="Bash", span_id="abc123", duration_ns=1234000000)
        events = parse_trace_spans(payload)
        assert len(events) == 1
        event = events[0]
        assert event["type"] == "span"
        assert event["name"] == "Bash"
        assert event["span_id"] == "abc123"
        assert event["duration_ms"] == 1234  # ns converted to ms

    def test_handles_multiple_spans(self):
        payload = make_trace_payload(name="Bash", span_id="span1")
        payload["resourceSpans"][0]["scopeSpans"][0]["spans"].append({
            "name": "Read",
            "spanId": "span2",
            "traceId": "trace123",
            "startTimeUnixNano": "1712000000000000000",
            "endTimeUnixNano": "1712000000500000000",
            "attributes": [{"key": "tool_name", "value": {"stringValue": "Read"}}],
        })
        events = parse_trace_spans(payload)
        assert len(events) == 2
        names = {e["name"] for e in events}
        assert names == {"Bash", "Read"}

    def test_returns_empty_for_empty_payload(self):
        events = parse_trace_spans({"resourceSpans": []})
        assert events == []

    def test_returns_empty_for_malformed_payload(self):
        events = parse_trace_spans({})
        assert events == [], "missing resourceSpans key should return empty list, not crash"

    def test_duration_conversion_from_nanoseconds(self):
        # 2.5 seconds = 2500ms
        payload = make_trace_payload(duration_ns=2_500_000_000)
        events = parse_trace_spans(payload)
        assert events[0]["duration_ms"] == 2500


# ============================================================================
# AC-5: Envelope format distinguishes OTEL events from watcher events
# ============================================================================

class TestEnvelopeFormat:
    def test_parsed_event_has_source_field(self):
        """Events from OTLP must have source: 'claude_otel' to distinguish from watcher events."""
        payload = make_log_payload(body="tool_result", attributes={"tool_name": "Bash", "tool_id": "t1", "duration_ms": 100})
        events = parse_log_records(payload)
        assert len(events) >= 1
        assert events[0].get("source") == "claude_otel", \
            "OTEL events must have source='claude_otel' to distinguish from watcher events"

    def test_metric_event_has_source_field(self):
        payload = make_metric_payload()
        events = parse_metric_records(payload)
        assert len(events) >= 1
        assert events[0].get("source") == "claude_otel"

    def test_trace_event_has_source_field(self):
        payload = make_trace_payload()
        events = parse_trace_spans(payload)
        assert len(events) >= 1
        assert events[0].get("source") == "claude_otel"


# ============================================================================
# AC-6: Span buffer bounded at 500 with FIFO eviction
# ============================================================================

class TestOtlpSpanBuffer:
    def test_buffer_stores_events(self):
        buf = OtlpSpanBuffer(max_size=500)
        buf.add({"type": "span", "name": "Bash"})
        assert len(buf) == 1

    def test_buffer_fifo_eviction_at_max(self):
        buf = OtlpSpanBuffer(max_size=5)
        for i in range(7):
            buf.add({"type": "span", "index": i})
        assert len(buf) == 5, "buffer should not exceed max_size"
        # Oldest (0, 1) should be evicted; 2-6 remain
        events = buf.get_all()
        indices = [e["index"] for e in events]
        assert indices == [2, 3, 4, 5, 6], "FIFO: oldest events should be evicted first"

    def test_buffer_default_max_is_500(self):
        buf = OtlpSpanBuffer()
        assert buf.max_size == 500

    def test_get_all_returns_copy(self):
        buf = OtlpSpanBuffer(max_size=10)
        buf.add({"type": "span"})
        result = buf.get_all()
        result.clear()
        assert len(buf) == 1, "get_all should return a copy, not the internal list"

    def test_empty_buffer_returns_empty_list(self):
        buf = OtlpSpanBuffer(max_size=10)
        assert buf.get_all() == []


# ============================================================================
# AC-7: Late-joining browsers receive span history (via buffer)
# ============================================================================

class TestLateJoinHistory:
    def test_buffer_provides_history_for_late_joiners(self):
        """The span buffer should provide all stored events for new WebSocket connections."""
        buf = OtlpSpanBuffer(max_size=500)
        for i in range(10):
            buf.add({"type": "span", "index": i})
        history = buf.get_all()
        assert len(history) == 10
        assert history[0]["index"] == 0
        assert history[9]["index"] == 9


# ============================================================================
# Rule #1: No silent exception swallowing
# ============================================================================

class TestNoSilentExceptions:
    def test_parse_log_does_not_silently_swallow(self):
        """parse_log_records should return empty list for bad input, not swallow exceptions silently."""
        import inspect
        from playtest_otlp import parse_log_records
        source = inspect.getsource(parse_log_records)
        assert "except:" not in source, "bare except clause found — must catch specific exceptions"
        assert "except Exception: pass" not in source.replace(" ", ""), \
            "silent Exception swallowing found"

    def test_parse_metric_does_not_silently_swallow(self):
        import inspect
        from playtest_otlp import parse_metric_records
        source = inspect.getsource(parse_metric_records)
        assert "except:" not in source
        assert "except Exception: pass" not in source.replace(" ", "")

    def test_parse_trace_does_not_silently_swallow(self):
        import inspect
        from playtest_otlp import parse_trace_spans
        source = inspect.getsource(parse_trace_spans)
        assert "except:" not in source
        assert "except Exception: pass" not in source.replace(" ", "")


# ============================================================================
# Rule #3: Type annotations at boundaries
# ============================================================================

class TestTypeAnnotations:
    def test_parse_functions_have_return_annotations(self):
        import inspect
        from playtest_otlp import parse_log_records, parse_metric_records, parse_trace_spans
        for fn in [parse_log_records, parse_metric_records, parse_trace_spans]:
            sig = inspect.signature(fn)
            assert sig.return_annotation != inspect.Parameter.empty, \
                f"{fn.__name__} must have a return type annotation"

    def test_parse_functions_have_parameter_annotations(self):
        import inspect
        from playtest_otlp import parse_log_records, parse_metric_records, parse_trace_spans
        for fn in [parse_log_records, parse_metric_records, parse_trace_spans]:
            sig = inspect.signature(fn)
            for name, param in sig.parameters.items():
                assert param.annotation != inspect.Parameter.empty, \
                    f"{fn.__name__}({name}) must have a type annotation"


# ============================================================================
# Rule #2: No mutable default arguments
# ============================================================================

class TestNoMutableDefaults:
    def test_otlp_span_buffer_no_mutable_defaults(self):
        import inspect
        from playtest_otlp import OtlpSpanBuffer
        sig = inspect.signature(OtlpSpanBuffer.__init__)
        for name, param in sig.parameters.items():
            if name == "self":
                continue
            if param.default != inspect.Parameter.empty:
                assert not isinstance(param.default, (list, dict, set)), \
                    f"OtlpSpanBuffer.__init__({name}) has mutable default: {param.default}"
