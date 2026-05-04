"""FastAPI application for Datasaurus.

Endpoints:
  GET /shapes                         — list all built-in shape names
  GET /generate/loop                  — SSE stream cycling through shapes indefinitely
  GET /generate/batch                 — SSE stream for multiple shapes in lockstep
  GET /generate/{shape}               — SSE stream of SA progress snapshots
  GET /generate/{shape}/final         — blocking, returns final dataset as JSON
"""

import asyncio
import os
from collections.abc import AsyncIterable
from typing import Annotated

import numpy as np
import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel, ConfigDict, Field

from .generator import Algorithm, GeneratorConfig, generate_stream, generate_batch_stream, generate_loop_stream
from .shapes import available_shapes, get_shape
from .stats import TargetStats, compute_stats

_TARGET = TargetStats()

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
    available = set(available_shapes())
    unknown = [s for s in shape_list if s not in available]
    if unknown:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown shape(s): {', '.join(unknown)}. GET /shapes for the list.",
        )
    return shape_list


@app.get("/shapes")
def list_shapes() -> list[str]:
    """Return all available built-in shape names."""
    return available_shapes()


@app.get("/generate/loop", response_class=EventSourceResponse)
async def generate_loop_sse(
    shape_list: Annotated[list[str], Depends(_check_batch_shapes)],
    steps_per_shape: int = Query(default=2_000, ge=100, le=100_000),
    snapshot_every: int = Query(default=20, ge=1, le=10_000),
) -> AsyncIterable[ServerSentEvent]:
    """Stream continuous shape morphing over SSE, cycling through shapes indefinitely.

    Uses projected gradient descent. Point count is fixed at 3000 for crisp shapes.
    The point cloud carries forward between shapes without reinitialising.
    """
    loop = asyncio.get_running_loop()
    shape_segments = [(name, get_shape(name)) for name in shape_list]
    stream = generate_loop_stream(
        shape_segments,
        _TARGET,
        steps_per_shape=steps_per_shape,
        snapshot_every=snapshot_every,
        n_points=10_000,
    )

    while True:
        result = await loop.run_in_executor(None, next, stream, None)
        if result is None:
            break

        shape_name, step, total, x, y = result
        df = pd.DataFrame({"x": x, "y": y})
        stats = compute_stats(df)

        event: dict = {
            "shape": shape_name,
            "step": step,
            "total": total,
            "points": np.column_stack([x, y]).tolist(),
            "stats": {k: round(float(v), 6) for k, v in stats.items()},
        }
        yield ServerSentEvent(data=event)


@app.get("/generate/batch", response_class=EventSourceResponse)
async def generate_batch_sse(
    params: Annotated[GenerateParams, Query()],
    shape_list: Annotated[list[str], Depends(_check_batch_shapes)],
) -> AsyncIterable[ServerSentEvent]:
    """Stream SA progress for multiple shapes simultaneously.

    All shapes run in a single thread (Python's GIL means threads don't give
    real parallelism for CPU-bound numpy work). Each SSE event carries the
    full point cloud for every shape at the same step.
    """
    loop = asyncio.get_running_loop()
    shape_segments = [(name, get_shape(name)) for name in shape_list]
    config = GeneratorConfig(
        max_steps=params.steps, seed=params.seed,
        n_points=params.n_points, show_progress=False, algorithm=params.algorithm,
    )
    stream = generate_batch_stream(shape_segments, _TARGET, config, snapshot_every=params.snapshot_every)

    while True:
        result = await loop.run_in_executor(None, next, stream, None)
        if result is None:
            break

        step, shape_data = result
        is_final = step == params.steps
        cells = []
        for shape_name, x, y in shape_data:
            df = pd.DataFrame({"x": x, "y": y})
            stats = compute_stats(df)
            cells.append({
                "shape": shape_name,
                "points": np.column_stack([x, y]).tolist(),
                "stats": {k: round(float(v), 6) for k, v in stats.items()},
            })

        event: dict = {"step": step, "total": params.steps, "cells": cells}
        if is_final:
            event["done"] = True
        yield ServerSentEvent(data=event)


@app.get("/generate/{shape}", response_class=EventSourceResponse, dependencies=[Depends(_check_shape)])
async def generate_sse(
    shape: str,
    params: Annotated[GenerateParams, Query()],
) -> AsyncIterable[ServerSentEvent]:
    """Stream SA progress as Server-Sent Events."""
    segs = get_shape(shape)
    config = GeneratorConfig(max_steps=params.steps, seed=params.seed, n_points=params.n_points, show_progress=False, algorithm=params.algorithm)
    loop = asyncio.get_running_loop()
    stream = generate_stream(segs, _TARGET, config, snapshot_every=params.snapshot_every)

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
