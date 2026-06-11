"""Wiring tests for send_render's `background` param (Task 8, story 66).

Pins the params projection: in the catalog-composed branch
(subject + genre + world all set), a non-empty `background` kwarg must land
in the daemon request as ``params["background"]`` so the daemon's
``build_cue_from_params`` can thread it onto ``RenderTarget.background``
(which auto-selects the `portrait_in_location` camera preset). An empty
background must omit the key entirely — the daemon treats key-absence as
"no backdrop", and a spurious empty-string key would be a silent contract
drift.

The unix socket is faked: we capture the JSON request send_render writes
and feed back a minimal response matching the request id.
"""

import asyncio
import json

import pytest

from scripts import render_common


class _FakeWriter:
    def __init__(self) -> None:
        self.written = b""
        self.closed = False

    def write(self, data: bytes) -> None:
        self.written += data

    async def drain(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        pass


def _fake_connection(captured: dict):
    """Build a fake open_unix_connection that echoes a matching response."""
    writer = _FakeWriter()
    reader = asyncio.StreamReader()

    async def fake_open(path):
        return reader, writer

    async def respond_when_written():
        # Wait for send_render to write its request, then echo a response
        # line with the same id so the read loop terminates.
        while not writer.written:
            await asyncio.sleep(0)
        req = json.loads(writer.written.decode())
        captured["request"] = req
        reader.feed_data(
            (json.dumps({"id": req["id"], "result": {"ok": True}}) + "\n").encode()
        )
        reader.feed_eof()

    return fake_open, respond_when_written


@pytest.mark.parametrize(
    ("background", "expect_key"),
    [
        ("where:w/plaza", True),
        ("", False),
    ],
    ids=["background-set", "background-empty"],
)
async def test_send_render_background_param_wiring(
    monkeypatch, background: str, expect_key: bool
) -> None:
    captured: dict = {}
    fake_open, responder = _fake_connection(captured)
    monkeypatch.setattr(asyncio, "open_unix_connection", fake_open)

    responder_task = asyncio.ensure_future(responder())
    try:
        result = await render_common.send_render(
            "portrait",
            "",
            "",
            42,
            subject="npc:rux",
            genre="g",
            world="w",
            background=background,
        )
    finally:
        await responder_task

    params = captured["request"]["params"]
    # Catalog branch sanity: subject/genre/world made it into params.
    assert params["subject"] == "npc:rux"
    assert params["genre"] == "g"
    assert params["world"] == "w"

    if expect_key:
        assert params["background"] == "where:w/plaza"
    else:
        assert "background" not in params, (
            "empty background must omit the key — the daemon treats absence "
            "as 'no backdrop'; an empty-string key is contract drift"
        )

    assert result == {"id": captured["request"]["id"], "result": {"ok": True}}
