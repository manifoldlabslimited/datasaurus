"""Dataset generators: simulated annealing, Langevin dynamics, and momentum.

All three algorithms share the same hard constraint (five summary stats within
tolerance) and temperature schedule, but differ in how they propose moves:

  SA (Matejka & Fitzmaurice 2017):
    Blind random walk; Metropolis acceptance via exp(-ΔE/T).

  Langevin (overdamped Langevin dynamics):
    Gradient-guided drift + temperature-scaled noise following the
    Einstein-Smoluchowski relation: noise_std = √(2αT).
    Energy = dist² so gradients are spring-like: F = nearest − x.
    Flows into the shape; gradients vanish when already on it.

  Momentum (heavy-ball gradient descent):
    Velocity accumulates gradient and decays by friction each step.
    Same dist² energy/gradient as Langevin; noise anneals to zero.
    Creates sweep-and-oscillate motion distinctly different from SA.
"""

import math
from typing import Literal

import numpy as np
import pandas as pd
import pytweening
from pydantic import BaseModel, ConfigDict, Field
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn, TimeRemainingColumn
from scipy.spatial import KDTree

from .shapes import Segments
from .stats import TargetStats, stats_are_valid

Algorithm = Literal["sa", "langevin", "momentum"]

# RNG calls are expensive one-at-a-time. Pre-generate this many values per batch.
_BATCH = 8_192


class _RunningStats:
    """O(1) per-step stats via running sums: Σx, Σy, Σx², Σy², Σxy.

    Replaces the per-step O(n) numpy passes of stats_are_valid.
    A single-point move updates five scalars instead of scanning all n points.
    """
    __slots__ = ("n", "sx", "sy", "sx2", "sy2", "sxy")

    def __init__(self, x: np.ndarray, y: np.ndarray) -> None:
        self.n   = int(len(x))
        self.sx  = float(x.sum())
        self.sy  = float(y.sum())
        self.sx2 = float((x * x).sum())
        self.sy2 = float((y * y).sum())
        self.sxy = float((x * y).sum())

    def move(self, ox: float, oy: float, nx: float, ny: float) -> None:
        """Apply (or reverse when ox↔nx swapped) a single-point move."""
        self.sx  += nx - ox
        self.sy  += ny - oy
        self.sx2 += nx * nx - ox * ox
        self.sy2 += ny * ny - oy * oy
        self.sxy += nx * ny - ox * oy

    def is_valid(self, target: TargetStats) -> bool:
        n   = self.n
        tol = target.tolerance
        mx  = self.sx / n
        my  = self.sy / n
        if abs(mx - target.mean_x) > tol: return False
        if abs(my - target.mean_y) > tol: return False
        vx = (self.sx2 - self.sx * self.sx / n) / (n - 1)
        vy = (self.sy2 - self.sy * self.sy / n) / (n - 1)
        if vx <= 0 or vy <= 0: return False
        sdx = vx ** 0.5
        sdy = vy ** 0.5
        if abs(sdx - target.std_x) > tol: return False
        if abs(sdy - target.std_y) > tol: return False
        cov = (self.sxy - self.sx * self.sy / n) / (n - 1)
        return abs(cov / (sdx * sdy) - target.correlation) <= tol


class GeneratorConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_steps: int = Field(default=200_000, gt=0)
    perturbation_scale: float = Field(default=0.5, gt=0)
    temp_start: float = Field(default=0.4, gt=0, description="Initial SA temperature")
    temp_min: float = Field(default=0.0, ge=0, description="Final SA temperature")
    allowed_dist: float = Field(default=2.0, ge=0, description="Accept if within this distance of shape")
    seed: int | None = Field(default=None)
    n_points: int = Field(default=142, gt=1)
    show_progress: bool = Field(default=True)
    algorithm: Literal["sa", "langevin", "momentum"] = Field(default="sa")


def _temperature(step: int, max_steps: int, temp_start: float, temp_min: float) -> float:
    """S-curve schedule using pytweening.easeInOutQuad — matches the original paper."""
    progress = (max_steps - step) / max_steps  # 1.0 -> 0.0
    return (temp_start - temp_min) * pytweening.easeInOutQuad(progress) + temp_min


def _precompute_temps(config: "GeneratorConfig") -> np.ndarray:
    """Vectorised temperature schedule: temps[step] = T at that step (index 0 unused).

    Replaces 1M individual pytweening.easeInOutQuad calls with one numpy pass.
    """
    s = np.arange(config.max_steps + 1, dtype=np.float64)
    p = (config.max_steps - s) / config.max_steps          # progress 1→0
    ease = np.where(p < 0.5, 2.0 * p * p, -1.0 + (4.0 - 2.0 * p) * p)
    return (config.temp_start - config.temp_min) * ease + config.temp_min


def _make_initial_dataset(target: TargetStats, n: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Generate a dataset that already satisfies target stats before morphing."""
    raw_x = rng.normal(0, 1, n)
    raw_y = rng.normal(0, 1, n)

    raw_x = (raw_x - raw_x.mean()) / raw_x.std(ddof=1)
    raw_y = (raw_y - raw_y.mean()) / raw_y.std(ddof=1)

    # Remove any existing correlation
    r = float(np.corrcoef(raw_x, raw_y)[0, 1])
    raw_y = raw_y - r * raw_x
    raw_y = (raw_y - raw_y.mean()) / raw_y.std(ddof=1)

    # Induce target correlation
    c = target.correlation
    raw_y = c * raw_x + np.sqrt(max(0.0, 1 - c * c)) * raw_y
    raw_y = (raw_y - raw_y.mean()) / raw_y.std(ddof=1)

    x = raw_x * target.std_x + target.mean_x
    y = raw_y * target.std_y + target.mean_y
    return x.astype(np.float64), y.astype(np.float64)


def _build_kdtree(segments: Segments, spacing: float = 0.3) -> KDTree:
    """Rasterize shape boundary into a dense point cloud and build a KDTree.

    Each segment is sampled every `spacing` units. The resulting tree replaces
    per-step Shapely GEOS calls with O(log n) exact nearest-neighbour queries.
    Error is bounded by spacing/2 — well below the allowed_dist threshold.
    """
    parts = []
    for x1, y1, x2, y2 in segments:
        length = math.hypot(x2 - x1, y2 - y1)
        n = max(2, int(math.ceil(length / spacing)))
        ts = np.linspace(0.0, 1.0, n)
        parts.append(np.column_stack([
            x1 + ts * (x2 - x1),
            y1 + ts * (y2 - y1),
        ]))
    return KDTree(np.vstack(parts))


def generate_stream(
    segments: Segments,
    target: TargetStats | None = None,
    config: GeneratorConfig | None = None,
    snapshot_every: int = 1_000,
):
    """Run the chosen algorithm and yield (step, x, y) snapshots at regular intervals.

    Yields:
        Tuple of (step: int, x: np.ndarray, y: np.ndarray).
        step == 0  is the initial state before any moves.
        step == config.max_steps is the final state (always yielded).
    """
    if target is None:
        target = TargetStats()
    if config is None:
        config = GeneratorConfig()

    rng = np.random.default_rng(config.seed)
    tree = _build_kdtree(segments)

    x, y = _make_initial_dataset(target, config.n_points, rng)

    yield 0, x.copy(), y.copy()

    # Precompute all temperatures once instead of calling pytweening 1M times.
    temps = _precompute_temps(config)

    loops = {"sa": _sa_loop, "langevin": _langevin_loop, "momentum": _momentum_loop}
    yield from loops[config.algorithm](x, y, tree, target, config, rng, snapshot_every, temps)


def _sa_loop(x, y, tree: KDTree, target, config, rng, snapshot_every, temps):
    """Matejka & Fitzmaurice (2017) simulated annealing.

    Optimisations vs naïve version:
    - O(1) incremental stats via _RunningStats (no per-step O(n) numpy passes)
    - RNG batched in blocks of _BATCH (eliminates per-call Python overhead)
    - Temperature read from precomputed array (no per-step pytweening call)
    """
    n       = config.n_points
    allowed = config.allowed_dist
    scale   = config.perturbation_scale

    current_dists = tree.query(np.c_[x, y])[0]
    rs = _RunningStats(x, y)
    _pt = np.empty(2)   # reused query buffer

    bi = _BATCH
    for step in range(1, config.max_steps + 1):
        if bi >= _BATCH:
            idx_b = rng.integers(0, n, size=_BATCH)
            dx_b  = rng.normal(0.0, scale, size=_BATCH)
            dy_b  = rng.normal(0.0, scale, size=_BATCH)
            r_b   = rng.random(_BATCH)
            bi = 0

        temp = float(temps[step])
        i    = int(idx_b[bi])
        nxi  = x[i] + dx_b[bi]
        nyi  = y[i] + dy_b[bi]
        rand = float(r_b[bi])
        bi  += 1

        oxi, oyi = x[i], y[i]
        rs.move(oxi, oyi, nxi, nyi)       # speculative update

        if not rs.is_valid(target):
            rs.move(nxi, nyi, oxi, oyi)   # revert
        else:
            x[i], y[i] = nxi, nyi
            _pt[0] = nxi; _pt[1] = nyi
            new_dist = float(tree.query(_pt)[0])
            old_dist = current_dists[i]
            delta    = new_dist - old_dist
            if delta < 0 or new_dist < allowed or (temp > 0 and rand < math.exp(-delta / temp)):
                current_dists[i] = new_dist
            else:
                x[i], y[i] = oxi, oyi
                rs.move(nxi, nyi, oxi, oyi)   # revert

        if step % snapshot_every == 0 or step == config.max_steps:
            yield step, x.copy(), y.copy()


def _langevin_loop(x, y, tree: KDTree, target, config, rng, snapshot_every, temps):
    """Langevin dynamics: biased random walk toward the shape boundary."""
    n       = config.n_points
    allowed = config.allowed_dist
    scale   = config.perturbation_scale

    current_dists = tree.query(np.c_[x, y])[0]
    rs = _RunningStats(x, y)
    _pt = np.empty(2)

    bi = _BATCH
    for step in range(1, config.max_steps + 1):
        if bi >= _BATCH:
            idx_b    = rng.integers(0, n, size=_BATCH)
            noise_b  = rng.normal(0.0, 1.0, size=(_BATCH, 2))
            r_b      = rng.random(_BATCH)
            bi = 0

        temp  = float(temps[step])
        i     = int(idx_b[bi])
        noise = noise_b[bi]
        rand  = float(r_b[bi])
        bi   += 1

        _pt[0] = x[i]; _pt[1] = y[i]
        dist, idx = tree.query(_pt)
        if dist > 1e-6:
            near = tree.data[idx]
            ux = (near[0] - x[i]) / dist
            uy = (near[1] - y[i]) / dist
        else:
            ux = uy = 0.0

        drift = scale * (1.0 - temp)
        sigma = scale * temp
        nxi = x[i] + drift * ux + sigma * noise[0]
        nyi = y[i] + drift * uy + sigma * noise[1]

        oxi, oyi = x[i], y[i]
        rs.move(oxi, oyi, nxi, nyi)

        if not rs.is_valid(target):
            rs.move(nxi, nyi, oxi, oyi)
        else:
            x[i], y[i] = nxi, nyi
            _pt[0] = nxi; _pt[1] = nyi
            new_dist = float(tree.query(_pt)[0])
            old_dist = current_dists[i]
            delta    = new_dist - old_dist
            if delta < 0 or new_dist < allowed or (temp > 0 and rand < math.exp(-delta / temp)):
                current_dists[i] = new_dist
            else:
                x[i], y[i] = oxi, oyi
                rs.move(nxi, nyi, oxi, oyi)

        if step % snapshot_every == 0 or step == config.max_steps:
            yield step, x.copy(), y.copy()


def _momentum_loop(x, y, tree: KDTree, target, config, rng, snapshot_every, temps):
    """Heavy-ball momentum: per-point velocity accumulates directed drift."""
    n       = config.n_points
    allowed = config.allowed_dist
    scale   = config.perturbation_scale
    β       = 0.85
    max_v   = scale * 3.0

    current_dists = tree.query(np.c_[x, y])[0]
    rs = _RunningStats(x, y)
    vx = np.zeros(n)
    vy = np.zeros(n)
    _pt = np.empty(2)

    bi = _BATCH
    for step in range(1, config.max_steps + 1):
        if bi >= _BATCH:
            idx_b   = rng.integers(0, n, size=_BATCH)
            noise_b = rng.normal(0.0, 1.0, size=(_BATCH, 2))
            r_b     = rng.random(_BATCH)
            bi = 0

        temp  = float(temps[step])
        i     = int(idx_b[bi])
        noise = noise_b[bi]
        rand  = float(r_b[bi])
        bi   += 1

        _pt[0] = x[i]; _pt[1] = y[i]
        dist, idx = tree.query(_pt)
        if dist > 1e-6:
            near = tree.data[idx]
            ux = (near[0] - x[i]) / dist
            uy = (near[1] - y[i]) / dist
        else:
            ux = uy = 0.0

        sigma = scale * max(0.05, temp)
        vx[i] = max(-max_v, min(max_v, β * vx[i] + scale * ux + sigma * noise[0]))
        vy[i] = max(-max_v, min(max_v, β * vy[i] + scale * uy + sigma * noise[1]))

        nxi = x[i] + vx[i]
        nyi = y[i] + vy[i]

        oxi, oyi = x[i], y[i]
        rs.move(oxi, oyi, nxi, nyi)

        if not rs.is_valid(target):
            rs.move(nxi, nyi, oxi, oyi)
            vx[i] = 0.0
            vy[i] = 0.0
        else:
            x[i], y[i] = nxi, nyi
            _pt[0] = nxi; _pt[1] = nyi
            new_dist = float(tree.query(_pt)[0])
            old_dist = current_dists[i]
            delta    = new_dist - old_dist
            if delta < 0 or new_dist < allowed or (temp > 0 and rand < math.exp(-delta / temp)):
                current_dists[i] = new_dist
            else:
                x[i], y[i] = oxi, oyi
                rs.move(nxi, nyi, oxi, oyi)
                vx[i] *= -0.3
                vy[i] *= -0.3

        if step % snapshot_every == 0 or step == config.max_steps:
            yield step, x.copy(), y.copy()


def generate(
    segments: Segments,
    target: TargetStats | None = None,
    config: GeneratorConfig | None = None,
) -> pd.DataFrame:
    """Morph a seed dataset toward *segments* while preserving *target* stats.

    Returns:
        DataFrame with x and y columns, shape (n_points, 2).
    """
    if config is None:
        config = GeneratorConfig()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeRemainingColumn(),
        disable=not config.show_progress,
    ) as progress:
        task = progress.add_task("Morphing", total=config.max_steps)
        x, y = np.array([]), np.array([])
        for step, x, y in generate_stream(segments, target, config):
            progress.update(task, completed=step)

    return pd.DataFrame({"x": x, "y": y})
