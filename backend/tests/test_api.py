"""Tests for api.py — FastAPI endpoints."""

import json

import pytest
from httpx import ASGITransport, AsyncClient

from datasaurus.api import app
from datasaurus.shapes import available_shapes


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


class TestShapesEndpoint:
    async def test_returns_list(self, client):
        r = await client.get("/shapes")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_returns_all_shapes(self, client):
        r = await client.get("/shapes")
        assert set(r.json()) == set(available_shapes())

    async def test_sorted(self, client):
        r = await client.get("/shapes")
        names = r.json()
        assert names == sorted(names)


class TestGenerateFinalEndpoint:
    async def test_returns_200(self, client):
        r = await client.get("/generate/circle/final?steps=2000&seed=42")
        assert r.status_code == 200

    async def test_response_schema(self, client):
        r = await client.get("/generate/circle/final?steps=2000&seed=42")
        body = r.json()
        assert body["shape"] == "circle"
        assert body["steps"] == 2000
        assert isinstance(body["points"], list)
        assert len(body["points"]) > 0
        assert len(body["points"][0]) == 2
        assert set(body["stats"].keys()) == {"mean_x", "mean_y", "std_x", "std_y", "correlation"}

    async def test_unknown_shape_returns_404(self, client):
        r = await client.get("/generate/not_a_shape/final")
        assert r.status_code == 404

    async def test_seed_reproducible(self, client):
        r1 = await client.get("/generate/circle/final?steps=2000&seed=7")
        r2 = await client.get("/generate/circle/final?steps=2000&seed=7")
        assert r1.json()["points"] == r2.json()["points"]


class TestGenerateSSEEndpoint:
    async def test_streams_events(self, client):
        events = []
        async with client.stream("GET", "/generate/circle?steps=3000&seed=1&snapshot_every=1000") as r:
            assert r.status_code == 200
            assert "text/event-stream" in r.headers["content-type"]
            async for line in r.aiter_lines():
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))

        assert len(events) >= 2  # at least initial + final

    async def test_first_event_is_step_zero(self, client):
        events = []
        async with client.stream("GET", "/generate/circle?steps=3000&seed=1&snapshot_every=1000") as r:
            async for line in r.aiter_lines():
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))
                    break
        assert events[0]["step"] == 0

    async def test_final_event_has_done_and_stats(self, client):
        last = None
        async with client.stream("GET", "/generate/circle?steps=3000&seed=1&snapshot_every=1000") as r:
            async for line in r.aiter_lines():
                if line.startswith("data: "):
                    last = json.loads(line[6:])
        assert last is not None
        assert last.get("done") is True
        assert "stats" in last

    async def test_unknown_shape_returns_404(self, client):
        r = await client.get("/generate/not_a_shape")
        assert r.status_code == 404
