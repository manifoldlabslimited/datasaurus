"""Tests for shapes.py — registry, geometry helpers, built-in shapes."""

import math

import numpy as np
import pytest

from datasaurus.shapes import (
    _circle_segments,
    _normalize_segments,
    _polyline_to_segments,
    available_shapes,
    get_shape,
    register,
    segments_to_shapely,
)


class TestRegistry:
    def test_fifty_shapes_registered(self):
        assert len(available_shapes()) == 50

    def test_available_shapes_sorted(self):
        names = available_shapes()
        assert names == sorted(names)

    def test_get_known_shape(self):
        segs = get_shape("circle")
        assert segs.ndim == 2
        assert segs.shape[1] == 4

    def test_get_unknown_shape_raises(self):
        with pytest.raises(ValueError, match="Unknown shape"):
            get_shape("not_a_real_shape")

    def test_register_and_retrieve(self):
        segs = np.array([[0.0, 0.0, 1.0, 1.0]])
        register("_test_shape", segs)
        result = get_shape("_test_shape")
        assert result.shape == (1, 4)
        # cleanup
        from datasaurus.shapes import _REGISTRY
        del _REGISTRY["_test_shape"]


class TestSegmentHelpers:
    def test_circle_segments_shape(self):
        segs = _circle_segments(50, 50, 20, n=60)
        assert segs.shape == (60, 4)

    def test_circle_is_closed(self):
        segs = _circle_segments(50, 50, 20, n=60)
        # last endpoint should connect back to first startpoint
        last_end = segs[-1, 2:]
        first_start = segs[0, :2]
        assert np.allclose(last_end, first_start, atol=1e-6)

    def test_polyline_to_segments_count(self):
        pts = [(0, 0), (1, 0), (1, 1), (0, 1)]
        segs = _polyline_to_segments(pts)
        assert segs.shape == (3, 4)

    def test_normalize_fits_within_range(self):
        segs = np.array([[0.0, 0.0, 1000.0, 1000.0]])
        norm = _normalize_segments(segs, x_range=(10, 100), y_range=(10, 90))
        all_x = np.concatenate([norm[:, 0], norm[:, 2]])
        all_y = np.concatenate([norm[:, 1], norm[:, 3]])
        assert all_x.min() >= 10 - 1e-9
        assert all_x.max() <= 100 + 1e-9
        assert all_y.min() >= 10 - 1e-9
        assert all_y.max() <= 90 + 1e-9


class TestSegmentsToShapely:
    def test_returns_multilinestring(self):
        from shapely.geometry import MultiLineString
        segs = _circle_segments(50, 50, 20, n=30)
        geom = segments_to_shapely(segs)
        assert isinstance(geom, MultiLineString)

    def test_distance_from_centre_is_radius(self):
        from shapely.geometry import Point
        r = 20.0
        segs = _circle_segments(50.0, 50.0, r, n=360)
        geom = segments_to_shapely(segs)
        # Point at exact centre should be ~radius away from the circle outline
        d = Point(50.0, 50.0).distance(geom)
        assert abs(d - r) < 0.1


class TestAllShapesValid:
    @pytest.mark.parametrize("name", available_shapes())
    def test_shape_is_float64_array(self, name):
        segs = get_shape(name)
        assert segs.dtype == np.float64

    @pytest.mark.parametrize("name", available_shapes())
    def test_shape_has_four_columns(self, name):
        segs = get_shape(name)
        assert segs.ndim == 2 and segs.shape[1] == 4

    @pytest.mark.parametrize("name", available_shapes())
    def test_shape_has_no_nan_or_inf(self, name):
        segs = get_shape(name)
        assert np.all(np.isfinite(segs))
