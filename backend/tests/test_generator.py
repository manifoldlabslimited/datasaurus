"""Tests for generator.py — generate_stream and generate."""

import numpy as np
import pandas as pd
import pytest

from datasaurus.generator import GeneratorConfig, generate, generate_stream
from datasaurus.shapes import get_shape
from datasaurus.stats import TargetStats, stats_are_valid


_FAST_CONFIG = GeneratorConfig(max_steps=5_000, seed=42, show_progress=False)
_SEGS = get_shape("circle")
_TARGET = TargetStats()


class TestGenerateStream:
    def test_first_yield_is_step_zero(self):
        stream = generate_stream(_SEGS, _TARGET, _FAST_CONFIG, snapshot_every=1_000)
        step, x, y = next(stream)
        assert step == 0

    def test_yields_arrays_of_correct_length(self):
        stream = generate_stream(_SEGS, _TARGET, _FAST_CONFIG, snapshot_every=1_000)
        for step, x, y in stream:
            assert len(x) == _FAST_CONFIG.n_points
            assert len(y) == _FAST_CONFIG.n_points

    def test_final_step_equals_max_steps(self):
        *_, last = generate_stream(_SEGS, _TARGET, _FAST_CONFIG, snapshot_every=1_000)
        step, x, y = last
        assert step == _FAST_CONFIG.max_steps

    def test_stats_preserved_throughout(self):
        """Every snapshot must satisfy target statistics."""
        for step, x, y in generate_stream(_SEGS, _TARGET, _FAST_CONFIG, snapshot_every=500):
            assert stats_are_valid(x, y, _TARGET), f"Stats violated at step {step}"

    def test_snapshots_are_copies(self):
        """Yielded arrays must not be mutated by subsequent steps."""
        stream = generate_stream(_SEGS, _TARGET, _FAST_CONFIG, snapshot_every=500)
        _, x0, _ = next(stream)
        snapshot = x0.copy()
        next(stream)
        assert np.array_equal(x0, snapshot)


class TestGenerate:
    def test_returns_dataframe(self):
        df = generate(_SEGS, _TARGET, _FAST_CONFIG)
        assert isinstance(df, pd.DataFrame)

    def test_has_x_and_y_columns(self):
        df = generate(_SEGS, _TARGET, _FAST_CONFIG)
        assert list(df.columns) == ["x", "y"]

    def test_correct_number_of_points(self):
        df = generate(_SEGS, _TARGET, _FAST_CONFIG)
        assert len(df) == _FAST_CONFIG.n_points

    def test_stats_within_tolerance(self):
        df = generate(_SEGS, _TARGET, _FAST_CONFIG)
        assert stats_are_valid(df["x"].to_numpy(), df["y"].to_numpy(), _TARGET)

    def test_seed_produces_same_result(self):
        df1 = generate(_SEGS, _TARGET, _FAST_CONFIG)
        df2 = generate(_SEGS, _TARGET, _FAST_CONFIG)
        pd.testing.assert_frame_equal(df1, df2)

    def test_different_seeds_differ(self):
        cfg_a = GeneratorConfig(max_steps=5_000, seed=1, show_progress=False)
        cfg_b = GeneratorConfig(max_steps=5_000, seed=2, show_progress=False)
        df_a = generate(_SEGS, _TARGET, cfg_a)
        df_b = generate(_SEGS, _TARGET, cfg_b)
        assert not df_a.equals(df_b)


# ── Per-algorithm contract tests ──────────────────────────────────────────────

_ALGORITHM_CONFIGS = [
    GeneratorConfig(max_steps=5_000, seed=42, show_progress=False, algorithm="sa"),
    GeneratorConfig(max_steps=5_000, seed=42, show_progress=False, algorithm="langevin"),
    GeneratorConfig(max_steps=5_000, seed=42, show_progress=False, algorithm="momentum"),
]


class TestAlgorithms:
    @pytest.mark.parametrize("config", _ALGORITHM_CONFIGS, ids=lambda c: c.algorithm)
    def test_stats_preserved(self, config):
        """All algorithms must keep every snapshot within stats tolerance."""
        for step, x, y in generate_stream(_SEGS, _TARGET, config, snapshot_every=500):
            assert stats_are_valid(x, y, _TARGET), f"{config.algorithm}: stats violated at step {step}"

    @pytest.mark.parametrize("config", _ALGORITHM_CONFIGS, ids=lambda c: c.algorithm)
    def test_converges_closer_than_start(self, config):
        """Final point cloud should be meaningfully closer to the shape on average."""
        import shapely as shp
        from datasaurus.shapes import segments_to_shapely
        shape = segments_to_shapely(_SEGS)

        stream = generate_stream(_SEGS, _TARGET, config, snapshot_every=5_000)
        _, x0, y0 = next(stream)
        *_, (_, xf, yf) = stream

        initial_dist = float(shp.distance(shp.points(np.c_[x0, y0]), shape).mean())
        final_dist = float(shp.distance(shp.points(np.c_[xf, yf]), shape).mean())
        assert final_dist < initial_dist, (
            f"{config.algorithm}: final mean dist {final_dist:.3f} not less than initial {initial_dist:.3f}"
        )

    @pytest.mark.parametrize("config", _ALGORITHM_CONFIGS, ids=lambda c: c.algorithm)
    def test_seed_reproducible(self, config):
        """Same seed must produce identical results for every algorithm."""
        df1 = generate(_SEGS, _TARGET, config)
        df2 = generate(_SEGS, _TARGET, config)
        pd.testing.assert_frame_equal(df1, df2)

    @pytest.mark.parametrize("config", _ALGORITHM_CONFIGS, ids=lambda c: c.algorithm)
    def test_final_step_correct(self, config):
        *_, last = generate_stream(_SEGS, _TARGET, config, snapshot_every=1_000)
        assert last[0] == config.max_steps

    def test_algorithms_produce_different_results(self):
        """Langevin and momentum must converge to different point clouds than SA."""
        base = dict(max_steps=5_000, seed=42, show_progress=False)
        results = {}
        for algo in ("sa", "langevin", "momentum"):
            *_, (_, x, _y) = generate_stream(_SEGS, _TARGET, GeneratorConfig(**base, algorithm=algo), snapshot_every=1_000)
            results[algo] = x.copy()
        assert not np.allclose(results["sa"], results["langevin"])
        assert not np.allclose(results["sa"], results["momentum"])

    def test_kdtree_distance_accuracy(self):
        """KDTree distances must stay within 0.2 units of exact Shapely distances."""
        from datasaurus.generator import _build_kdtree
        from shapely.geometry import Point
        from datasaurus.shapes import segments_to_shapely

        tree = _build_kdtree(_SEGS)
        shape = segments_to_shapely(_SEGS)
        rng = np.random.default_rng(0)
        pts = rng.uniform([0, 0], [110, 100], (50, 2))
        kd_dists = tree.query(pts)[0]
        shapely_dists = np.array([Point(p).distance(shape) for p in pts])
        assert np.max(np.abs(kd_dists - shapely_dists)) < 0.2
