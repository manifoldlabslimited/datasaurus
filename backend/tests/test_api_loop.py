"""Tests for /generate/loop SSE endpoint."""

import json

import pytest
from httpx import ASGITransport, AsyncClient

from datasaurus.api import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def _parse_sse_events(text: str) -> list[dict]:
    """Parse SSE text into a list of JSON event dicts."""
    events = []
    for line in text.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


class TestLoopValidation:
    """Shape validation mirrors the batch endpoint."""

    @pytest.mark.asyncio
    async def test_unknown_shape_returns_404(self, client):
        resp = await client.get("/generate/loop?shapes=nonexistent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_empty_shapes_returns_422(self, client):
        resp = await client.get("/generate/loop?shapes=")
        assert resp.status_code == 422


class TestLoopSSEStructure:
    """SSE events have the correct payload shape."""

    @pytest.mark.asyncio
    async def test_returns_200_with_sse_content_type(self, client):
        resp = await client.get(
            "/generate/loop?shapes=circle&steps_per_shape=100&snapshot_every=100",
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

    @pytest.mark.asyncio
    async def test_events_have_correct_fields(self, client):
        resp = await client.get(
            "/generate/loop?shapes=circle&steps_per_shape=100&snapshot_every=100",
        )
        events = _parse_sse_events(resp.text)
        # Should have at least one data event + done event
        assert len(events) >= 2

        # Check a data event (not the done event)
        data_events = [e for e in events if "done" not in e]
        assert len(data_events) >= 1
        ev = data_events[0]
        assert "shape" in ev
        assert "step" in ev
        assert "total" in ev
        assert "points" in ev
        assert "stats" in ev
        assert ev["shape"] == "circle"

    @pytest.mark.asyncio
    async def test_stream_ends_with_done_event(self, client):
        resp = await client.get(
            "/generate/loop?shapes=circle&steps_per_shape=100&snapshot_every=100",
        )
        events = _parse_sse_events(resp.text)
        assert events[-1] == {"done": True}

    @pytest.mark.asyncio
    async def test_multi_shape_stream(self, client):
        resp = await client.get(
            "/generate/loop?shapes=circle,star&steps_per_shape=100&snapshot_every=100",
        )
        events = _parse_sse_events(resp.text)
        data_events = [e for e in events if "done" not in e]
        shapes_seen = {e["shape"] for e in data_events}
        assert "circle" in shapes_seen
        assert "star" in shapes_seen
