"""Tests for /generate/batch SSE endpoint."""

import json

import pytest
from httpx import ASGITransport, AsyncClient

from datasaurus.api import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


_SHAPES = "circle,heart,dino"
_FAST = "steps=3000&seed=1&snapshot_every=1000"


async def _collect_events(client, url: str) -> list[dict]:
    events = []
    async with client.stream("GET", url) as r:
        assert r.status_code == 200
        async for line in r.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    return events


class TestBatchValidation:
    async def test_unknown_shape_returns_404(self, client):
        r = await client.get(f"/generate/batch?shapes=circle,not_a_shape&{_FAST}")
        assert r.status_code == 404

    async def test_empty_shapes_returns_422(self, client):
        r = await client.get(f"/generate/batch?shapes=&{_FAST}")
        assert r.status_code == 422

    async def test_missing_shapes_param_returns_422(self, client):
        r = await client.get(f"/generate/batch?{_FAST}")
        assert r.status_code == 422


class TestBatchSSEStructure:
    async def test_returns_200_with_sse_content_type(self, client):
        async with client.stream("GET", f"/generate/batch?shapes={_SHAPES}&{_FAST}") as r:
            assert r.status_code == 200
            assert "text/event-stream" in r.headers["content-type"]

    async def test_first_event_is_step_zero(self, client):
        events = await _collect_events(client, f"/generate/batch?shapes={_SHAPES}&{_FAST}")
        assert events[0]["step"] == 0

    async def test_first_event_has_all_shapes(self, client):
        events = await _collect_events(client, f"/generate/batch?shapes={_SHAPES}&{_FAST}")
        first = events[0]
        returned_shapes = {c["shape"] for c in first["cells"]}
        assert returned_shapes == {"circle", "heart", "dino"}

    async def test_every_event_has_same_number_of_cells(self, client):
        events = await _collect_events(client, f"/generate/batch?shapes={_SHAPES}&{_FAST}")
        assert all(len(e["cells"]) == 3 for e in events)

    async def test_every_event_has_correct_total(self, client):
        events = await _collect_events(client, f"/generate/batch?shapes={_SHAPES}&{_FAST}")
        assert all(e["total"] == 3000 for e in events)

    async def test_all_events_on_same_step(self, client):
        """All cells in each event must be at the same step."""
        events = await _collect_events(client, f"/generate/batch?shapes={_SHAPES}&{_FAST}")
        # Steps are on the event itself, not per-cell — just verify step increases
        steps = [e["step"] for e in events]
        assert steps == sorted(steps)
        assert steps[0] == 0
        assert steps[-1] == 3000

    async def test_cells_have_points(self, client):
        events = await _collect_events(client, f"/generate/batch?shapes={_SHAPES}&{_FAST}")
        for event in events:
            for cell in event["cells"]:
                assert isinstance(cell["points"], list)
                assert len(cell["points"]) > 0
                assert len(cell["points"][0]) == 2


class TestBatchFinalEvent:
    async def test_final_event_has_done_true(self, client):
        events = await _collect_events(client, f"/generate/batch?shapes={_SHAPES}&{_FAST}")
        assert events[-1].get("done") is True

    async def test_final_event_has_stats_per_cell(self, client):
        events = await _collect_events(client, f"/generate/batch?shapes={_SHAPES}&{_FAST}")
        last = events[-1]
        for cell in last["cells"]:
            assert "stats" in cell
            assert set(cell["stats"].keys()) == {"mean_x", "mean_y", "std_x", "std_y", "correlation"}

    async def test_final_step_equals_requested_steps(self, client):
        events = await _collect_events(client, f"/generate/batch?shapes={_SHAPES}&{_FAST}")
        assert events[-1]["step"] == 3000

    async def test_all_events_include_stats(self, client):
        events = await _collect_events(client, f"/generate/batch?shapes={_SHAPES}&{_FAST}")
        for event in events:
            for cell in event["cells"]:
                assert "stats" in cell
                assert set(cell["stats"].keys()) == {"mean_x", "mean_y", "std_x", "std_y", "correlation"}


class TestBatchReproducibility:
    async def test_same_seed_same_result(self, client):
        url = f"/generate/batch?shapes=circle,heart&steps=2000&seed=99&snapshot_every=2000"
        e1 = await _collect_events(client, url)
        e2 = await _collect_events(client, url)
        assert e1[-1]["cells"] == e2[-1]["cells"]

    async def test_single_shape_batch_matches_per_shape_endpoint(self, client):
        """A batch with one shape should produce the same final points as the individual endpoint."""
        seed = 7
        steps = 2000
        batch_events = await _collect_events(
            client, f"/generate/batch?shapes=circle&steps={steps}&seed={seed}&snapshot_every={steps}"
        )
        single_events = await _collect_events(
            client, f"/generate/circle?steps={steps}&seed={seed}&snapshot_every={steps}"
        )
        batch_points = batch_events[-1]["cells"][0]["points"]
        single_points = single_events[-1]["points"]
        assert batch_points == single_points
