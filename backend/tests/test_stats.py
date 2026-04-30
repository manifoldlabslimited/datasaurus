"""Tests for stats.py — TargetStats model and constraint checking."""

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from datasaurus.stats import TargetStats, compute_stats, stats_are_valid


class TestTargetStats:
    def test_defaults_are_canonical(self):
        t = TargetStats()
        assert t.mean_x == 54.26
        assert t.mean_y == 47.83
        assert t.std_x == 16.76
        assert t.std_y == 26.93
        assert t.correlation == -0.06
        assert t.tolerance == 0.01

    def test_frozen(self):
        t = TargetStats()
        with pytest.raises(ValidationError):
            t.mean_x = 0.0  # type: ignore[misc]

    def test_invalid_std_rejected(self):
        with pytest.raises(ValidationError):
            TargetStats(std_x=-1.0)

    def test_invalid_correlation_rejected(self):
        with pytest.raises(ValidationError):
            TargetStats(correlation=1.5)

    def test_tolerance_must_be_positive(self):
        with pytest.raises(ValidationError):
            TargetStats(tolerance=0.0)


class TestComputeStats:
    def test_returns_five_stats(self):
        df = pd.DataFrame({"x": [1.0, 2.0, 3.0], "y": [3.0, 2.0, 1.0]})
        stats = compute_stats(df)
        assert set(stats.index) == {"mean_x", "mean_y", "std_x", "std_y", "correlation"}

    def test_correct_values(self):
        rng = np.random.default_rng(0)
        x = rng.normal(54.26, 16.76, 500)
        y = rng.normal(47.83, 26.93, 500)
        df = pd.DataFrame({"x": x, "y": y})
        stats = compute_stats(df)
        assert abs(stats["mean_x"] - x.mean()) < 1e-9
        assert abs(stats["std_x"] - x.std(ddof=1)) < 1e-9


class TestStatsAreValid:
    def _canonical_xy(self, n: int = 200, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
        """Return arrays that satisfy canonical TargetStats within tolerance."""
        from datasaurus.generator import _make_initial_dataset
        target = TargetStats()
        rng = np.random.default_rng(seed)
        return _make_initial_dataset(target, n, rng)

    def test_valid_dataset_passes(self):
        x, y = self._canonical_xy()
        assert stats_are_valid(x, y, TargetStats())

    def test_shifted_mean_fails(self):
        x, y = self._canonical_xy()
        x = x + 5.0  # shifts mean_x far outside tolerance
        assert not stats_are_valid(x, y, TargetStats())

    def test_tight_tolerance_fails(self):
        # Build data whose mean_x is off by 0.005 — outside tight tolerance but inside loose
        target = TargetStats()
        rng = np.random.default_rng(0)
        x = np.full(200, target.mean_x + 0.005)
        y = np.full(200, target.mean_y)
        tight = TargetStats(tolerance=0.001)
        assert not stats_are_valid(x, y, tight)
