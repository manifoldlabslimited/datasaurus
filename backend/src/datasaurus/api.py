"""FastAPI application for Datasaurus.

Endpoints:
  GET /shapes                         — list all built-in shape names
  GET /generate/batch                 — SSE stream for multiple shapes in lockstep
  GET /generate/{shape}               — SSE stream of SA progress snapshots
  GET /generate/{shape}/final         — blocking, returns final dataset as JSON
"""

import asyncio
import os
import threading
from collections.abc import AsyncIterable
from typing import Annotated

import numpy as np
import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel, ConfigDict, Field

from .generator import Algorithm, GeneratorConfig, generate_stream
from .shapes import available_shapes, get_shape
from .stats import TargetStats, compute_stats

_TARGET = TargetStats()

# ── Guardrails ──
MAX_BATCH_SHAPES = 25          # 5×5 grid max
MAX_CONCURRENT_STREAMS = 10    # total simultaneous SSE connections
_active_streams = 0
_streams_lock = threading.Lock()

ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "").split(",") if os.environ.get("ALLOWED_ORIGINS") else ["*"]


class GenerateParams(BaseModel):
    """Shared query parameters for all generation endpoints."""

    model_config = ConfigDict(frozen=True)

    steps: int = Field(default=50_000, ge=1_000, le=500_000)
    seed: int | None = Field(default=None)
    snapshot_every: int = Field(default=1_000, ge=100, le=10_000)
    n_points: int = Field(default=142, ge=50, le=500)
    algorithm: Algorithm = Field(default="sa")

app = FastAPI(
    title="Datasaurus API",
    description="Generate datasets with identical summary statistics but different shapes.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _check_shape(shape: str) -> None:
    """Dependency: raise 404 before SSE starts if shape is unknown."""
    if shape not in available_shapes():
        raise HTTPException(status_code=404, detail=f"Unknown shape '{shape}'. GET /shapes for the list.")


def _check_batch_shapes(
    shapes: Annotated[str, Query(..., description="Comma-separated shape names, e.g. dino,heart,circle")],
) -> list[str]:
    """Dependency: validate and parse batch shapes before SSE starts."""
    shape_list = [s.strip() for s in shapes.split(",") if s.strip()]
    if not shape_list:
        raise HTTPException(status_code=422, detail="No shapes provided.")
    if len(shape_list) > MAX_BATCH_SHAPES:
        raise HTTPException(status_code=422, detail=f"Too many shapes ({len(shape_list)}). Maximum is {MAX_BATCH_SHAPES}.")
    available = set(available_shapes())
    unknown = [s for s in shape_list if s not in available]
    if unknown:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown shape(s): {', '.join(unknown)}. GET /shapes for the list.",
        )
    return shape_list


def _acquire_stream() -> None:
    """Increment active stream count or reject if at capacity."""
    global _active_streams
    with _streams_lock:
        if _active_streams >= MAX_CONCURRENT_STREAMS:
            raise HTTPException(status_code=503, detail="Server is busy. Try again in a moment.")
        _active_streams += 1


def _release_stream() -> None:
    """Decrement active stream count."""
    global _active_streams
    with _streams_lock:
        _active_streams = max(0, _active_streams - 1)


@app.get("/shapes")
def list_shapes() -> list[str]:
    """Return all available built-in shape names."""
    return available_shapes()


@app.get("/generate/batch", response_class=EventSourceResponse)
async def generate_batch_sse(
    params: Annotated[GenerateParams, Query()],
    shape_list: Annotated[list[str], Depends(_check_batch_shapes)],
    _stream: Annotated[None, Depends(_acquire_stream)],
) -> AsyncIterable[ServerSentEvent]:
    """Stream SA progress for multiple shapes simultaneously."""
    loop = asyncio.get_running_loop()
    cancelled = threading.Event()
    queues: list[asyncio.Queue] = [asyncio.Queue(maxsize=2) for _ in shape_list]

    def producer(segs, config, q: asyncio.Queue) -> None:
        for step, x, y in generate_stream(segs, _TARGET, config, snapshot_every=params.snapshot_every):
            if cancelled.is_set():
                return
            future = asyncio.run_coroutine_threadsafe(q.put((step, x.copy(), y.copy())), loop)
            try:
                future.result(timeout=5.0)
            except Exception:
                return
        if not cancelled.is_set():
            asyncio.run_coroutine_threadsafe(q.put(None), loop).result(timeout=5.0)

    producer_futures = [
        loop.run_in_executor(
            None,
            producer,
            get_shape(shape),
            GeneratorConfig(max_steps=params.steps, seed=params.seed, n_points=params.n_points, show_progress=False, algorithm=params.algorithm),
            q,
        )
        for shape, q in zip(shape_list, queues)
    ]

    try:
        while True:
            snapshots = await asyncio.gather(*[q.get() for q in queues])
            if any(s is None for s in snapshots):
                break

            step: int = snapshots[0][0]
            is_final = step == params.steps
            cells = []
            for shape_name, (_, x, y) in zip(shape_list, snapshots):
                df = pd.DataFrame({"x": x, "y": y})
                stats = compute_stats(df)
                cell: dict = {
                    "shape": shape_name,
                    "points": np.column_stack([x, y]).tolist(),
                    "stats": {k: round(float(v), 6) for k, v in stats.items()},
                }
                cells.append(cell)

            event: dict = {"step": step, "total": params.steps, "cells": cells}
            if is_final:
                event["done"] = True
            yield ServerSentEvent(data=event)
    finally:
        cancelled.set()
        await asyncio.gather(*producer_futures, return_exceptions=True)
        _release_stream()


@app.get("/generate/{shape}", response_class=EventSourceResponse, dependencies=[Depends(_check_shape)])
async def generate_sse(
    shape: str,
    params: Annotated[GenerateParams, Query()],
    _stream: Annotated[None, Depends(_acquire_stream)],
) -> AsyncIterable[ServerSentEvent]:
    """Stream SA progress as Server-Sent Events."""
    segs = get_shape(shape)
    config = GeneratorConfig(max_steps=params.steps, seed=params.seed, n_points=params.n_points, show_progress=False, algorithm=params.algorithm)
    loop = asyncio.get_running_loop()
    stream = generate_stream(segs, _TARGET, config, snapshot_every=params.snapshot_every)

    try:
        while True:
            result = await loop.run_in_executor(None, next, stream, None)
            if result is None:
                break
            step, x, y = result
            is_final = step == params.steps
            data: dict = {"step": step, "total": params.steps, "points": np.column_stack([x, y]).tolist()}
            if is_final:
                df = pd.DataFrame({"x": x, "y": y})
                stats = compute_stats(df)
                data["stats"] = {k: round(float(v), 6) for k, v in stats.items()}
                data["done"] = True
            yield ServerSentEvent(data=data)
    finally:
        _release_stream()


@app.get("/generate/{shape}/final", dependencies=[Depends(_check_shape)])
async def generate_final(
    shape: str,
    params: Annotated[GenerateParams, Query()],
):
    """Run SA to completion and return the final dataset as JSON (blocking)."""
    segs = get_shape(shape)
    config = GeneratorConfig(max_steps=params.steps, seed=params.seed, n_points=params.n_points, show_progress=False)
    loop = asyncio.get_running_loop()

    def run():
        *_, last = generate_stream(segs, _TARGET, config)
        return last

    _, x, y = await loop.run_in_executor(None, run)
    df = pd.DataFrame({"x": x, "y": y})
    stats = compute_stats(df)
    return {
        "shape": shape,
        "steps": params.steps,
        "points": np.column_stack([x, y]).tolist(),
        "stats": {k: round(float(v), 6) for k, v in stats.items()},
    }
