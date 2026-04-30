"""Shape definitions as collections of line segments.

Every shape — whether built-in, imported from SVG, or loaded from JSON — is
ultimately represented as a numpy array of shape (N, 4), where each row is
[x1, y1, x2, y2] defining one line segment.

The SA engine only ever sees this array; it never knows how the shape was made.
All coordinates are in the approximate [0, 110] x [0, 100] space used by the
original Datasaurus Dozen paper.
"""

import json
import math
from pathlib import Path

import numpy as np
from shapely.geometry import MultiLineString

# Python 3.12 type alias
type Segments = np.ndarray

_REGISTRY: dict[str, Segments] = {}


def segments_to_shapely(segs: Segments) -> MultiLineString:
    """Convert a (N, 4) segment array to a Shapely MultiLineString.

    The SA engine calls Point.distance(shape) which dispatches to GEOS C++,
    giving exact, fast point-to-multilinestring distance with zero custom math.
    """
    return MultiLineString([((r[0], r[1]), (r[2], r[3])) for r in segs])


# ---------------------------------------------------------------------------
# Internal geometry helpers
# ---------------------------------------------------------------------------

def _parametric_to_segments(x_fn, y_fn, t_start: float, t_end: float, n: int = 200) -> Segments:
    """Sample a parametric curve and return consecutive line segments."""
    ts = np.linspace(t_start, t_end, n + 1)
    xs = np.array([x_fn(t) for t in ts])
    ys = np.array([y_fn(t) for t in ts])
    return np.column_stack([xs[:-1], ys[:-1], xs[1:], ys[1:]])


def _circle_segments(cx: float, cy: float, r: float, n: int = 120) -> Segments:
    ts = np.linspace(0, 2 * math.pi, n + 1)
    xs = cx + r * np.cos(ts)
    ys = cy + r * np.sin(ts)
    return np.column_stack([xs[:-1], ys[:-1], xs[1:], ys[1:]])


def _polyline_to_segments(pts: list[tuple[float, float]]) -> Segments:
    arr = np.array(pts)
    return np.column_stack([arr[:-1, 0], arr[:-1, 1], arr[1:, 0], arr[1:, 1]])


def _normalize_segments(segs: Segments, x_range=(10.0, 100.0), y_range=(10.0, 90.0)) -> Segments:
    """Scale and centre segments to fit within the target coordinate box."""
    all_x = np.concatenate([segs[:, 0], segs[:, 2]])
    all_y = np.concatenate([segs[:, 1], segs[:, 3]])
    x_min, x_max = all_x.min(), all_x.max()
    y_min, y_max = all_y.min(), all_y.max()
    x_span = x_max - x_min if x_max != x_min else 1.0
    y_span = y_max - y_min if y_max != y_min else 1.0
    tx0, tx1 = x_range
    ty0, ty1 = y_range
    scale = min((tx1 - tx0) / x_span, (ty1 - ty0) / y_span)
    cx = (tx0 + tx1) / 2 - scale * (x_min + x_max) / 2
    cy = (ty0 + ty1) / 2 - scale * (y_min + y_max) / 2
    out = segs.astype(np.float64).copy()
    out[:, 0] = segs[:, 0] * scale + cx
    out[:, 1] = segs[:, 1] * scale + cy
    out[:, 2] = segs[:, 2] * scale + cx
    out[:, 3] = segs[:, 3] * scale + cy
    return out


# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------

def register(name: str, segs: Segments) -> None:
    _REGISTRY[name] = segs.astype(np.float64)


def shape(name: str):
    """Decorator that builds and registers a shape.

    Usage::

        @shape("my_shape")
        def _():
            return _circle_segments(54, 47, 30)

    The decorated function is called immediately at import time; its return
    value is registered and the name ``_`` is discarded.
    """
    def decorator(fn):
        register(name, fn())
    return decorator


def available_shapes() -> list[str]:
    return sorted(_REGISTRY.keys())


def get_shape(name: str) -> Segments:
    if name not in _REGISTRY:
        raise ValueError(f"Unknown shape '{name}'. Available: {available_shapes()}")
    return _REGISTRY[name]


# ---------------------------------------------------------------------------
# External shape loaders
# ---------------------------------------------------------------------------

def segments_from_json(path: Path) -> Segments:
    """Load segments from a JSON file.

    Accepts either::

        [[x1, y1, x2, y2], ...]
        {"segments": [[x1, y1, x2, y2], ...]}
    """
    data = json.loads(Path(path).read_text())
    if isinstance(data, dict):
        data = data["segments"]
    segs = np.array(data, dtype=np.float64)
    if segs.ndim != 2 or segs.shape[1] != 4:
        raise ValueError("JSON segments must be an array of [x1, y1, x2, y2] rows")
    return _normalize_segments(segs)


def segments_from_svg(path: Path, n_samples: int = 50) -> Segments:
    """Parse an SVG file and convert all paths to line segments.

    Bezier curves and arcs are approximated by sampling n_samples points per
    sub-segment. Result is normalised and Y is flipped (SVG Y grows downward).
    """
    try:
        from svgpathtools import svg2paths
    except ImportError:
        raise RuntimeError("svgpathtools is required. Run: uv add svgpathtools")

    paths, _ = svg2paths(str(path))
    rows: list[list[float]] = []
    for svg_path in paths:
        for segment in svg_path:
            pts = [segment.point(t / n_samples) for t in range(n_samples + 1)]
            for i in range(len(pts) - 1):
                x1, y1 = pts[i].real, pts[i].imag
                x2, y2 = pts[i + 1].real, pts[i + 1].imag
                rows.append([x1, y1, x2, y2])

    if not rows:
        raise ValueError(f"No path segments found in SVG: {path}")

    segs = np.array(rows, dtype=np.float64)
    # Flip Y (SVG Y grows downward)
    all_y = np.concatenate([segs[:, 1], segs[:, 3]])
    y_max = all_y.max()
    segs[:, 1] = y_max - segs[:, 1]
    segs[:, 3] = y_max - segs[:, 3]
    return _normalize_segments(segs)


# ---------------------------------------------------------------------------
# Built-in shape definitions
# ---------------------------------------------------------------------------
# Add a new shape by writing:
#
#   @shape("my_shape")
#   def _():
#       return <Segments>
#
# All local variables stay inside the function; nothing leaks to module scope.
# ---------------------------------------------------------------------------

_CX, _CY = 54.26, 47.83  # canonical centre from the original paper


@shape("arch")
def _():
    return np.vstack([
        _parametric_to_segments(
            x_fn=lambda t: _CX + 40 * math.cos(t),
            y_fn=lambda t: _CY + 40 * math.sin(t),
            t_start=0, t_end=math.pi, n=150,
        ),
        np.array([
            [_CX - 40, _CY, _CX - 40, _CY - 30],
            [_CX + 40, _CY, _CX + 40, _CY - 30],
        ], dtype=np.float64),
    ])


@shape("arrow")
def _():
    return np.array([
        [10.0, 47.0, 80.0, 47.0],
        [80.0, 47.0, 60.0, 30.0],
        [80.0, 47.0, 60.0, 64.0],
    ], dtype=np.float64)


@shape("away")
def _():
    return np.vstack([
        _circle_segments(25, 75, 3, 20),
        _circle_segments(75, 75, 3, 20),
        _circle_segments(25, 25, 3, 20),
        _circle_segments(75, 25, 3, 20),
    ])


@shape("bar_chart")
def _():
    return np.vstack([
        _polyline_to_segments([(12, 10), (12, 45), (28, 45), (28, 10)]),
        _polyline_to_segments([(33, 10), (33, 68), (49, 68), (49, 10)]),
        _polyline_to_segments([(54, 10), (54, 52), (70, 52), (70, 10)]),
        _polyline_to_segments([(75, 10), (75, 85), (91, 85), (91, 10)]),
        np.array([[8.0, 10.0, 98.0, 10.0]], dtype=np.float64),
    ])


@shape("bowtie")
def _():
    return _polyline_to_segments([(12, 82), (98, 18), (98, 82), (12, 18), (12, 82)])


@shape("bullseye")
def _():
    return np.vstack([
        _circle_segments(_CX, _CY, 18, 120),
        _circle_segments(_CX, _CY,  9, 80),
    ])


@shape("circle")
def _():
    return _circle_segments(_CX, _CY, 30, 120)


@shape("clover")
def _():
    return np.vstack([
        _circle_segments(_CX - 17, _CY + 17, 18, 80),
        _circle_segments(_CX + 17, _CY + 17, 18, 80),
        _circle_segments(_CX - 17, _CY - 17, 18, 80),
        _circle_segments(_CX + 17, _CY - 17, 18, 80),
    ])


@shape("cross")
def _():
    return np.array([
        [15.0, _CY,  95.0, _CY],
        [_CX,  10.0, _CX,  88.0],
    ], dtype=np.float64)


@shape("crown")
def _():
    return _polyline_to_segments([
        (10, 15), (10, 72), (28, 50), (55, 75), (82, 50), (100, 72), (100, 15), (10, 15)
    ])


@shape("diamond")
def _():
    return np.array([
        [55.0, 90.0, 95.0, 47.0],
        [95.0, 47.0, 55.0,  5.0],
        [55.0,  5.0, 15.0, 47.0],
        [15.0, 47.0, 55.0, 90.0],
    ], dtype=np.float64)


@shape("dino")
def _():
    # Sauropod (long-neck dinosaur) facing right, pre-normalisation coords 0-100.
    # Body silhouette — closed loop, clockwise from tail tip.
    body = _polyline_to_segments([
        (5, 48),                                    # tail tip (left)
        (12, 55), (20, 61), (30, 65),              # upper tail → back
        (40, 68), (50, 68), (60, 65),              # back
        (68, 60), (72, 52), (70, 44),              # shoulder
        (65, 38), (56, 34), (46, 32),              # chest → belly
        (36, 33), (28, 36), (20, 42), (12, 45),   # lower belly → tail
        (5, 48),                                    # close
    ])
    # Neck + head attached at shoulder (~68, 58).
    neck_head = _polyline_to_segments([
        (68, 58),                                   # neck base
        (72, 50), (76, 40), (79, 30), (81, 21),   # neck curves up-right
        (83, 15), (87, 11), (92, 10),              # crown
        (96, 13), (100, 18), (100, 25),            # snout top
        (98, 31), (94, 34),                         # snout tip → jaw
        (89, 34), (84, 31),                         # lower jaw
        (80, 28), (78, 36), (75, 47), (72, 56),   # throat back down
    ])
    # Four legs — simple U-shapes hanging from belly (y≈33-36).
    leg_fl = _polyline_to_segments([(30, 35), (28, 22), (26, 10), (30, 8), (34, 10), (33, 22), (32, 35)])
    leg_fr = _polyline_to_segments([(42, 33), (40, 20), (39, 8),  (43, 7), (47, 9),  (46, 21), (45, 33)])
    leg_rl = _polyline_to_segments([(54, 34), (52, 21), (51, 9),  (55, 7), (59, 9),  (58, 21), (57, 34)])
    leg_rr = _polyline_to_segments([(64, 37), (63, 24), (62, 12), (66, 9), (70, 12), (70, 24), (68, 37)])
    return _normalize_segments(np.vstack([body, neck_head, leg_fl, leg_fr, leg_rl, leg_rr]))


@shape("dots")
def _():
    return np.vstack([
        _circle_segments(cx, cy, 2, 16)
        for cx in [25.0, 50.0, 75.0]
        for cy in [20.0, 50.0, 80.0]
    ])


@shape("double_sine")
def _():
    return np.vstack([
        _parametric_to_segments(
            x_fn=lambda t: t,
            y_fn=lambda t: _CY + 22 + 16 * math.sin((t - 5) * 2 * math.pi / 100),
            t_start=5, t_end=105, n=300,
        ),
        _parametric_to_segments(
            x_fn=lambda t: t,
            y_fn=lambda t: _CY - 22 + 16 * math.sin((t - 5) * 2 * math.pi / 100 + math.pi),
            t_start=5, t_end=105, n=300,
        ),
    ])


@shape("ellipse")
def _():
    return _parametric_to_segments(
        x_fn=lambda t: _CX + 48 * math.cos(t),
        y_fn=lambda t: _CY + 26 * math.sin(t),
        t_start=0, t_end=2 * math.pi, n=200,
    )


@shape("eye")
def _():
    return np.vstack([
        _parametric_to_segments(
            x_fn=lambda t: _CX + 44 * math.cos(t),
            y_fn=lambda t: _CY + 22 * math.sin(t),
            t_start=0, t_end=math.pi, n=100,
        ),
        _parametric_to_segments(
            x_fn=lambda t: _CX + 44 * math.cos(t),
            y_fn=lambda t: _CY - 22 * math.sin(t),
            t_start=0, t_end=math.pi, n=100,
        ),
        _circle_segments(_CX, _CY, 11, 60),
    ])


@shape("figure_eight")
def _():
    return np.vstack([
        _circle_segments(_CX, _CY + 22, 20, 100),
        _circle_segments(_CX, _CY - 22, 20, 100),
    ])


@shape("fish")
def _():
    return np.vstack([
        _parametric_to_segments(
            x_fn=lambda t: _CX + 8 + 30 * math.cos(t),
            y_fn=lambda t: _CY + 17 * math.sin(t),
            t_start=0, t_end=2 * math.pi, n=120,
        ),
        _polyline_to_segments([
            (_CX - 22, _CY), (_CX - 48, _CY + 22), (_CX - 48, _CY - 22), (_CX - 22, _CY)
        ]),
        _circle_segments(_CX + 22, _CY + 5, 4, 20),
    ])


@shape("grid")
def _():
    return np.vstack([
        np.array([[x, 5.0, x, 95.0] for x in [20.0, 37.0, 54.0, 71.0, 88.0]], dtype=np.float64),
        np.array([[5.0, y, 100.0, y] for y in [15.0, 32.0, 50.0, 67.0, 85.0]], dtype=np.float64),
    ])


@shape("h_lines")
def _():
    return np.array([[0, y, 110, y] for y in [15.0, 30.0, 50.0, 70.0, 85.0]], dtype=np.float64)


@shape("heart")
def _():
    return _parametric_to_segments(
        x_fn=lambda t: _CX + 16 * math.sin(t) ** 3 * 1.8,
        y_fn=lambda t: _CY + (13 * math.cos(t) - 5 * math.cos(2*t)
                              - 2 * math.cos(3*t) - math.cos(4*t)) * 1.5,
        t_start=0, t_end=2 * math.pi, n=300,
    )


@shape("hexagon")
def _():
    pts = [
        (_CX + 40 * math.cos(math.radians(90 + 60 * i)),
         _CY + 40 * math.sin(math.radians(90 + 60 * i)))
        for i in range(6)
    ]
    return _polyline_to_segments(pts + [pts[0]])


@shape("high_lines")
def _():
    return np.array([[0, y, 110, y] for y in [60.0, 75.0, 90.0]], dtype=np.float64)


@shape("hourglass")
def _():
    return _polyline_to_segments([
        (15, 85), (95, 85), (55, 47), (95, 10), (15, 10), (55, 47), (15, 85)
    ])


@shape("house")
def _():
    return np.vstack([
        _polyline_to_segments([(18, 15), (92, 15), (92, 60), (18, 60), (18, 15)]),
        _polyline_to_segments([(18, 60), (_CX, 90), (92, 60)]),
    ])


@shape("infinity")
def _():
    return _parametric_to_segments(
        x_fn=lambda t: _CX + 38 * math.cos(t) / (1 + math.sin(t) ** 2),
        y_fn=lambda t: _CY + 22 * math.sin(t) * math.cos(t) / (1 + math.sin(t) ** 2),
        t_start=0, t_end=2 * math.pi, n=300,
    )


@shape("lightning")
def _():
    return _polyline_to_segments([
        (60, 90), (38, 52), (55, 52), (30, 10),
        (63, 48), (46, 48), (60, 90),
    ])


@shape("mountain")
def _():
    return _polyline_to_segments([
        (5, 15), (25, 58), (45, 28), (65, 75), (85, 38), (105, 15)
    ])


@shape("octagon")
def _():
    pts = [
        (_CX + 38 * math.cos(math.radians(22.5 + 45 * i)),
         _CY + 38 * math.sin(math.radians(22.5 + 45 * i)))
        for i in range(8)
    ]
    return _polyline_to_segments(pts + [pts[0]])


@shape("pac_man")
def _():
    mouth = math.radians(35)
    return np.vstack([
        _parametric_to_segments(
            x_fn=lambda t: _CX + 36 * math.cos(t),
            y_fn=lambda t: _CY + 36 * math.sin(t),
            t_start=mouth, t_end=2 * math.pi - mouth, n=200,
        ),
        np.array([
            [_CX, _CY, _CX + 36 * math.cos(mouth),  _CY + 36 * math.sin(mouth)],
            [_CX, _CY, _CX + 36 * math.cos(-mouth), _CY + 36 * math.sin(-mouth)],
        ], dtype=np.float64),
    ])


@shape("parabola")
def _():
    return _parametric_to_segments(
        x_fn=lambda t: t,
        y_fn=lambda t: 10 + 80 * ((t - 55) / 50) ** 2,
        t_start=5, t_end=105, n=300,
    )


@shape("pentagon")
def _():
    pts = [
        (_CX + 38 * math.cos(math.radians(90 + 72 * i)),
         _CY + 38 * math.sin(math.radians(90 + 72 * i)))
        for i in range(5)
    ]
    return _polyline_to_segments(pts + [pts[0]])


@shape("rings")
def _():
    return np.vstack([
        _circle_segments(_CX, _CY, 36, 150),
        _circle_segments(_CX, _CY, 24, 100),
        _circle_segments(_CX, _CY, 12, 70),
    ])


@shape("s_curve")
def _():
    return _parametric_to_segments(
        x_fn=lambda t: _CX + 30 * math.sin(t),
        y_fn=lambda t: _CY + 35 * math.sin(2 * t) / 2,
        t_start=-math.pi, t_end=math.pi, n=300,
    )


@shape("scatter_4")
def _():
    return np.vstack([
        _circle_segments(28, 28, 14, 70),
        _circle_segments(82, 28, 14, 70),
        _circle_segments(28, 72, 14, 70),
        _circle_segments(82, 72, 14, 70),
    ])


@shape("sine")
def _():
    return _parametric_to_segments(
        x_fn=lambda t: t,
        y_fn=lambda t: _CY + 28 * math.sin((t - 5) * 2 * math.pi / 100),
        t_start=5, t_end=105, n=400,
    )


@shape("slant_down")
def _():
    return np.array([[0.0, 90.0, 110.0, 5.0]], dtype=np.float64)


@shape("slant_up")
def _():
    return np.array([[0.0, 5.0, 110.0, 90.0]], dtype=np.float64)


@shape("smiley")
def _():
    return np.vstack([
        _circle_segments(_CX, _CY, 38, 120),
        _circle_segments(_CX - 14, _CY + 10, 4, 20),
        _circle_segments(_CX + 14, _CY + 10, 4, 20),
        _parametric_to_segments(
            x_fn=lambda t: _CX + 20 * math.cos(t),
            y_fn=lambda t: _CY - 18 + 12 * math.sin(t),
            t_start=math.pi, t_end=2 * math.pi, n=80,
        ),
    ])


@shape("spiral")
def _():
    return _parametric_to_segments(
        x_fn=lambda t: _CX + (4 + 4.5 * t) * math.cos(t),
        y_fn=lambda t: _CY + (4 + 4.5 * t) * math.sin(t),
        t_start=0, t_end=3.8 * math.pi, n=600,
    )


@shape("staircase")
def _():
    return _polyline_to_segments([
        (8, 10), (8, 28), (28, 28), (28, 46), (48, 46),
        (48, 64), (68, 64), (68, 82), (102, 82),
    ])


@shape("star")
def _():
    R, r = 35.0, 14.0
    outer = [
        (_CX + R * math.cos(math.radians(90 + 72 * i)),
         _CY + R * math.sin(math.radians(90 + 72 * i)))
        for i in range(5)
    ]
    inner = [
        (_CX + r * math.cos(math.radians(90 + 72 * i + 36)),
         _CY + r * math.sin(math.radians(90 + 72 * i + 36)))
        for i in range(5)
    ]
    segs = []
    for i in range(5):
        segs.append([*outer[i], *inner[i]])
        segs.append([*inner[i], *outer[(i + 1) % 5]])
    return np.array(segs, dtype=np.float64)


@shape("sun")
def _():
    return np.vstack([
        _circle_segments(_CX, _CY, 16, 80),
        np.array([
            [_CX + 20 * math.cos(math.radians(45 * i)), _CY + 20 * math.sin(math.radians(45 * i)),
             _CX + 32 * math.cos(math.radians(45 * i)), _CY + 32 * math.sin(math.radians(45 * i))]
            for i in range(8)
        ], dtype=np.float64),
    ])


@shape("tornado")
def _():
    return _parametric_to_segments(
        x_fn=lambda t: _CX + (2 + 5.5 * t) * math.cos(t * 3),
        y_fn=lambda t: _CY + (2 + 5.5 * t) * math.sin(t * 3),
        t_start=0, t_end=4 * math.pi, n=600,
    )


@shape("triangle")
def _():
    return np.array([
        [20.0, 15.0, 90.0, 15.0],
        [90.0, 15.0, 55.0, 85.0],
        [55.0, 85.0, 20.0, 15.0],
    ], dtype=np.float64)


@shape("v_lines")
def _():
    return np.array([[x, 0, x, 100] for x in [15.0, 30.0, 50.0, 70.0, 85.0]], dtype=np.float64)


@shape("wave")
def _():
    return _parametric_to_segments(
        x_fn=lambda t: t,
        y_fn=lambda t: _CY + 30 * math.sin((t - 5) * 4 * math.pi / 100),
        t_start=5, t_end=105, n=500,
    )


@shape("wide_lines")
def _():
    return np.array([
        [0, 50, 110, 50],
        [0, 70, 110, 70],
    ], dtype=np.float64)


@shape("x_shape")
def _():
    return np.array([
        [0.0,   0.0, 100.0, 100.0],
        [100.0, 0.0,   0.0, 100.0],
    ], dtype=np.float64)


@shape("zigzag")
def _():
    return _polyline_to_segments([
        (5, 50), (18, 80), (32, 20), (46, 80),
        (60, 20), (74, 80), (88, 20), (105, 50),
    ])
