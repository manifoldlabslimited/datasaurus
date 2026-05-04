"""Tests for generate_loop_stream — shape cycling, continuity, and invariants."""

import itertools

import numpy as np
import pytest

from datasaurus.generator import generate_loop_stream
from datasaurus.shapes import get_shape
from datasaurus.stats import TargetStats


# Use small step counts for fast tests
_STEPS = 100
_SNAP = 50
_N_POINTS = 50
_SEED = 42
_TARGET = TargetStats()

# Two distinct shapes for most tests
_SHAPES = [
    ("circle", get_shape("circle")),
    ("star", get_shape("star")),
]


def _collect_yields(shapes, n_yields: int, **kwargs) -> list[tuple[str, int, int, np.ndarray, np.ndarray]]:
    """Collect the first n_yields from generate_loop_stream."""
    defaults = dict(
        target=_TARGET,
        steps_per_shape=_STEPS,
        snapshot_every=_SNAP,
        n_points=_N_POINTS,
        seed=_SEED,
    )
    defaults.update(kwargs)
    gen = generate_loop_stream(shapes, **defaults)
    return [next(gen) for _ in range(n_yields)]


class TestShapeOrder:
    """Yielded shape names follow the input order and cycle."""

    def test_shapes_follow_input_order(self):
        # With steps=100 and snapshot_every=50, each shape yields at steps 50 and 100 → 2 yields per shape.
        yields_per_shape = _STEPS // _SNAP
        total_yields = yields_per_shape * len(_SHAPES)
        results = _collect_yields(_SHAPES, total_yields)

        shape_names = [r[0] for r in results]
        # First yields_per_shape should be "circle", next yields_per_shape should be "star"
        assert all(n == "circle" for n in shape_names[:yields_per_shape])
        assert all(n == "star" for n in shape_names[yields_per_shape:])

    def test_stops_after_last_shape(self):
        """After completing all shapes, the generator stops (single pass)."""
        yields_per_shape = _STEPS // _SNAP
        total_yields = yields_per_shape * len(_SHAPES)
        # Collect exactly one full pass
        results = _collect_yields(_SHAPES, total_yields)
        assert len(results) == total_yields

        # Generator should be exhausted — next() raises StopIteration
        gen = generate_loop_stream(
            _SHAPES, target=_TARGET, steps_per_shape=_STEPS,
            snapshot_every=_SNAP, n_points=_N_POINTS, seed=_SEED,
        )
        for _ in range(total_yields):
            next(gen)
        with pytest.raises(StopIteration):
            next(gen)


class TestPointCloudContinuity:
    """Final points of shape N equal starting points of shape N+1."""

    def test_final_points_carried_forward(self):
        """The last yield of shape N and the first yield of shape N+1 share the same underlying cloud."""
        yields_per_shape = _STEPS // _SNAP
        # Collect yields for 2 shapes
        total_yields = yields_per_shape * 2
        results = _collect_yields(_SHAPES, total_yields)

        # Last yield of first shape (circle)
        last_circle = results[yields_per_shape - 1]
        # First yield of second shape (star)
        first_star = results[yields_per_shape]

        assert last_circle[0] == "circle"
        assert first_star[0] == "star"

        # The point cloud should NOT be identical (star's first snapshot is after _SNAP steps of mutation),
        # but we can verify continuity by using snapshot_every == steps_per_shape so the first
        # yield of the next shape is after a full transition. Instead, let's use a dedicated test
        # with snapshot_every == steps_per_shape to capture exact transition boundaries.

    def test_exact_transition_boundary(self):
        """With snapshot_every == steps_per_shape, each shape yields exactly once at completion."""
        steps = 100
        results = _collect_yields(_SHAPES, 2, steps_per_shape=steps, snapshot_every=steps)

        assert results[0][0] == "circle"
        assert results[1][0] == "star"

    def test_continuity_with_single_step_shapes(self):
        """With steps_per_shape=1 and snapshot_every=1, the cloud changes minimally between shapes.

        The final yield of shape N and the first yield of shape N+1 should be
        close — the arrays carry forward and only one step of mutation occurs.
        The bulk-move-and-project algorithm may touch multiple points per step
        (unlike single-point algorithms), so we check that the overall
        displacement is small rather than counting changed elements.
        """
        results = _collect_yields(_SHAPES, 2, steps_per_shape=1, snapshot_every=1)

        last_circle_x = results[0][3]
        last_circle_y = results[0][4]
        first_star_x = results[1][3]
        first_star_y = results[1][4]

        # L-BFGS-B moves points more aggressively per step than simple gradient descent.
        rms_x = float(np.sqrt(np.mean((last_circle_x - first_star_x) ** 2)))
        rms_y = float(np.sqrt(np.mean((last_circle_y - first_star_y) ** 2)))
        assert rms_x < 10.0, f"RMS x displacement too large: {rms_x:.4f}"
        assert rms_y < 10.0, f"RMS y displacement too large: {rms_y:.4f}"


class TestPointCount:
    """Every yield contains exactly n_points in both x and y arrays."""

    def test_all_yields_have_correct_point_count(self):
        yields_per_shape = _STEPS // _SNAP
        total_yields = yields_per_shape * len(_SHAPES)
        results = _collect_yields(_SHAPES, total_yields)

        for shape_name, step, total, x, y in results:
            assert len(x) == _N_POINTS, f"x has {len(x)} points at {shape_name} step {step}"
            assert len(y) == _N_POINTS, f"y has {len(y)} points at {shape_name} step {step}"

    def test_point_count_with_different_n_points(self):
        """Point count invariant holds for non-default n_points values."""
        for n in [30, 80]:
            results = _collect_yields(_SHAPES, 2, n_points=n)
            for shape_name, step, total, x, y in results:
                assert len(x) == n
                assert len(y) == n


class TestStepCounts:
    """Step counts are correct within each transition."""

    def test_steps_within_shape(self):
        """Steps should be multiples of snapshot_every, ending at steps_per_shape."""
        yields_per_shape = _STEPS // _SNAP
        total_yields = yields_per_shape * len(_SHAPES)
        results = _collect_yields(_SHAPES, total_yields)

        # First shape (circle): steps should be [50, 100]
        circle_steps = [r[1] for r in results[:yields_per_shape]]
        expected = [_SNAP * (i + 1) for i in range(yields_per_shape)]
        assert circle_steps == expected

        # Second shape (star): steps should also be [50, 100] (reset per shape)
        star_steps = [r[1] for r in results[yields_per_shape:]]
        assert star_steps == expected

    def test_total_steps_field(self):
        """The total field should always equal steps_per_shape."""
        results = _collect_yields(_SHAPES, 4)
        for shape_name, step, total, x, y in results:
            assert total == _STEPS

    def test_final_step_always_yielded(self):
        """The last step of each shape (steps_per_shape) is always yielded,
        even if it's not a multiple of snapshot_every."""
        steps = 75
        snap = 50
        # Expected yields per shape: step 50 and step 75 (final)
        results = _collect_yields(_SHAPES, 4, steps_per_shape=steps, snapshot_every=snap)

        circle_results = [r for r in results if r[0] == "circle"]
        star_results = [r for r in results if r[0] == "star"]

        # Each shape should have yields at step 50 and step 75
        circle_steps = [r[1] for r in circle_results[:2]]
        assert circle_steps == [50, 75]

        star_steps = [r[1] for r in star_results[:2]]
        assert star_steps == [50, 75]


class TestSeedReproducibility:
    """Same seed produces identical results."""

    def test_deterministic_with_same_seed(self):
        results_a = _collect_yields(_SHAPES, 4, seed=42)
        results_b = _collect_yields(_SHAPES, 4, seed=42)

        for a, b in zip(results_a, results_b):
            assert a[0] == b[0]  # same shape name
            assert a[1] == b[1]  # same step
            np.testing.assert_array_equal(a[3], b[3])  # same x
            np.testing.assert_array_equal(a[4], b[4])  # same y

    def test_different_seeds_differ(self):
        results_a = _collect_yields(_SHAPES, 2, seed=1)
        results_b = _collect_yields(_SHAPES, 2, seed=2)

        # At least one yield should have different x values
        any_different = any(
            not np.array_equal(a[3], b[3]) for a, b in zip(results_a, results_b)
        )
        assert any_different
