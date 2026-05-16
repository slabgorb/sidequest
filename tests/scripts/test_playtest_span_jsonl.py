"""Unit tests for the --span-jsonl Jaeger span-tree capture in playtest.py.

These exercise the pure serialization layer only: a synthetic Jaeger v2
query-API trace payload → JSONL records. No live server, no live Jaeger —
the end-to-end run is validated by the Phase E parity gate (next task).

The capture path deliberately does NOT reuse scripts/playtest_otlp.py:
that buffer is the ADR-058 Claude-subprocess HTTP/JSON telemetry stream,
a different telemetry path. The narration.turn spans this gate eyeballs
come from the server's own OTEL tracer, gRPC-exported to Jaeger per
ADR-103. See the playtest.py module docstring.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

from playtest import (  # noqa: E402
    SpanCaptureEmpty,
    _parent_span_id,
    flatten_jaeger_tags,
    jaeger_span_to_record,
    parse_args,
    traces_to_jsonl_records,
    write_span_jsonl,
)


# ── Synthetic Jaeger v2 query-API payload ───────────────────────────────────

# Shape mirrors GET /api/traces?service=sidequest-server — a narration.turn
# rollup parent with one child llm.request span, exactly the tree the SDK
# narrator path emits per turn (ADR-103 span taxonomy).
_NARRATION_TURN_TAGS = [
    {"key": "world_id", "type": "string", "value": "flickering_reach"},
    {"key": "session_id", "type": "string", "value": "sess-abc123"},
    {"key": "turn_number", "type": "int64", "value": 3},
    {"key": "acting_pc", "type": "string", "value": "Rux"},
    {"key": "narration.turn.model_chosen", "type": "string",
     "value": "claude-sonnet-4-6"},
    {"key": "narration.turn.total_input_tokens", "type": "int64", "value": 4200},
    {"key": "narration.turn.total_output_tokens", "type": "int64", "value": 880},
    {"key": "narration.turn.cache_read_tokens", "type": "int64", "value": 3900},
    {"key": "narration.turn.cache_write_tokens", "type": "int64", "value": 0},
    {"key": "narration.turn.tool_call_count", "type": "int64", "value": 2},
    {
        "key": "narration.turn.tool_calls_json",
        "type": "string",
        "value": json.dumps([
            {"id": "toolu_1", "name": "resolve_roll", "arguments": {"dc": 14}},
            {"id": "toolu_2", "name": "apply_damage",
             "arguments": {"target": "Carl", "amount": 4}},
        ]),
    },
]


def _synthetic_jaeger_payload() -> dict:
    return {
        "data": [
            {
                "traceID": "trace-aaaa",
                "spans": [
                    {
                        "traceID": "trace-aaaa",
                        "spanID": "span-parent",
                        "operationName": "narration.turn",
                        "references": [],
                        "startTime": 1_700_000_000_000_000,
                        "duration": 8_200_000,
                        "tags": _NARRATION_TURN_TAGS,
                    },
                    {
                        "traceID": "trace-aaaa",
                        "spanID": "span-child",
                        "operationName": "llm.request",
                        "references": [
                            {
                                "refType": "CHILD_OF",
                                "traceID": "trace-aaaa",
                                "spanID": "span-parent",
                            }
                        ],
                        "startTime": 1_700_000_000_100_000,
                        "duration": 7_900_000,
                        "tags": [
                            {"key": "llm.model", "type": "string",
                             "value": "claude-sonnet-4-6"},
                            {"key": "llm.cost_usd", "type": "float64",
                             "value": 0.0123},
                            {"key": "ok", "type": "bool", "value": True},
                        ],
                    },
                ],
            }
        ],
        "total": 0,
        "limit": 0,
        "offset": 0,
        "errors": None,
    }


# ── flatten_jaeger_tags ─────────────────────────────────────────────────────


def test_flatten_jaeger_tags_preserves_all_keys_and_native_values():
    flat = flatten_jaeger_tags(_NARRATION_TURN_TAGS)

    assert flat["world_id"] == "flickering_reach"
    assert flat["turn_number"] == 3  # int64 stays an int
    assert flat["narration.turn.model_chosen"] == "claude-sonnet-4-6"
    assert flat["narration.turn.total_input_tokens"] == 4200
    assert flat["narration.turn.total_output_tokens"] == 880
    assert flat["narration.turn.cache_read_tokens"] == 3900
    assert flat["narration.turn.cache_write_tokens"] == 0
    assert flat["narration.turn.tool_call_count"] == 2
    # The lie-detector ledger survives verbatim as a JSON string.
    decoded = json.loads(flat["narration.turn.tool_calls_json"])
    assert [c["name"] for c in decoded] == ["resolve_roll", "apply_damage"]


def test_flatten_jaeger_tags_handles_bool_and_float_types():
    flat = flatten_jaeger_tags([
        {"key": "ok", "type": "bool", "value": True},
        {"key": "cost", "type": "float64", "value": 0.5},
    ])
    assert flat["ok"] is True
    assert flat["cost"] == 0.5


# ── jaeger_span_to_record ───────────────────────────────────────────────────


def test_jaeger_span_to_record_parent_span_has_no_parent_id():
    payload = _synthetic_jaeger_payload()
    parent = payload["data"][0]["spans"][0]
    rec = jaeger_span_to_record(parent)

    assert rec["name"] == "narration.turn"
    assert rec["span_id"] == "span-parent"
    assert rec["trace_id"] == "trace-aaaa"
    assert rec["parent_span_id"] is None
    assert rec["start_us"] == 1_700_000_000_000_000
    assert rec["duration_us"] == 8_200_000
    assert rec["attributes"]["narration.turn.tool_call_count"] == 2


def test_jaeger_span_to_record_child_resolves_parent_from_child_of_ref():
    payload = _synthetic_jaeger_payload()
    child = payload["data"][0]["spans"][1]
    rec = jaeger_span_to_record(child)

    assert rec["name"] == "llm.request"
    assert rec["span_id"] == "span-child"
    assert rec["parent_span_id"] == "span-parent"


def test_parent_span_id_ignores_non_child_of_refs_and_treats_as_root():
    # A FOLLOWS_FROM-only span is not a tree child — it must read as a
    # root (None), not inherit the FOLLOWS_FROM target as a parent.
    span = {
        "spanID": "span-async",
        "references": [
            {
                "refType": "FOLLOWS_FROM",
                "traceID": "trace-aaaa",
                "spanID": "span-parent",
            }
        ],
    }
    assert _parent_span_id(span) is None


# ── traces_to_jsonl_records ─────────────────────────────────────────────────


def test_traces_to_jsonl_records_flattens_all_spans_across_traces():
    records = traces_to_jsonl_records(_synthetic_jaeger_payload())

    assert len(records) == 2
    names = {r["name"] for r in records}
    assert names == {"narration.turn", "llm.request"}


def test_traces_to_jsonl_records_empty_payload_returns_empty_list():
    assert traces_to_jsonl_records({"data": []}) == []
    assert traces_to_jsonl_records({}) == []


# ── write_span_jsonl (fail-loud contract) ───────────────────────────────────


def test_write_span_jsonl_round_trips_one_object_per_line(tmp_path):
    records = traces_to_jsonl_records(_synthetic_jaeger_payload())
    out = tmp_path / "spans.jsonl"

    count = write_span_jsonl(records, out)

    assert count == 2
    lines = out.read_text().splitlines()
    assert len(lines) == 2
    # Every line is a standalone JSON object that round-trips.
    parsed = [json.loads(line) for line in lines]
    assert {p["name"] for p in parsed} == {"narration.turn", "llm.request"}
    turn = next(p for p in parsed if p["name"] == "narration.turn")
    ledger = json.loads(turn["attributes"]["narration.turn.tool_calls_json"])
    assert ledger[1]["name"] == "apply_damage"


def test_write_span_jsonl_raises_on_empty_records_no_file_written(tmp_path):
    # No silent fallback: an empty capture must NOT write a success-looking
    # empty file. It means the run wasn't traced.
    out = tmp_path / "spans.jsonl"
    with pytest.raises(SpanCaptureEmpty):
        write_span_jsonl([], out)
    assert not out.exists()


# ── argparse wiring ─────────────────────────────────────────────────────────


def test_span_jsonl_flag_is_wired_and_optional():
    # Flag absent → None (no-flag path unchanged).
    args = parse_args(["--scenario", "scenarios/smoke_test.yaml"])
    assert args.span_jsonl is None
    assert args.jaeger_url == "http://localhost:16686"

    # Flag present → captured as a Path; jaeger-url overridable.
    args = parse_args([
        "--scenario", "scenarios/smoke_test.yaml",
        "--span-jsonl", "/tmp/out.jsonl",
        "--jaeger-url", "http://jaeger.local:16686",
    ])
    assert args.span_jsonl == Path("/tmp/out.jsonl")
    assert args.jaeger_url == "http://jaeger.local:16686"
