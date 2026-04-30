# Datasaurus

A circle, a heart, and a dinosaur can share identical means, standard deviations, and correlation — down to two decimal places — and look nothing alike when plotted. Matejka & Fitzmaurice demonstrated this at ACM CHI 2017 with the Datasaurus Dozen.

This library generates those datasets. Give it a shape name; it runs simulated annealing to reorganize a random point cloud into that shape while keeping five statistics fixed throughout. This implementation has 50 built-in shapes and a streaming API for watching the process in real time.

---

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
cd backend
uv sync
uv run datasaurus generate dino --plot
```

---

## CLI

### `datasaurus shapes`

```bash
uv run datasaurus shapes
```

### `datasaurus generate SHAPE`

```bash
uv run datasaurus generate circle
uv run datasaurus generate heart --output heart.csv --seed 42
uv run datasaurus generate dino --steps 200000 --plot --quiet
```

| Option | Default | Description |
|---|---|---|
| `SHAPE` | required | Any name from `datasaurus shapes` |
| `-o / --output PATH` | — | Save as CSV |
| `-s / --steps N` | 200 000 | More steps → tighter shape |
| `--seed N` | — | Random seed |
| `-p / --plot` | off | Open a scatter plot when done |
| `-q / --quiet` | off | Suppress the progress bar |

### `datasaurus gallery`

Run all 50 shapes (or a subset) and save the CSVs.

```bash
uv run datasaurus gallery
uv run datasaurus gallery --grid 3x4 --seed 42
uv run datasaurus gallery --shapes circle,heart,dino --grid 1x3
```

| Option | Default | Description |
|---|---|---|
| `--grid ROWSxCOLS` | `5x10` | Layout for the saved plot |
| `--shapes a,b,c` | all | Run only these shapes |
| `--output-dir PATH` | `runs/TIMESTAMP` | Where to write the CSVs |
| `-s / --steps N` | 200 000 | Steps per shape |
| `--seed N` | — | Shared seed across all shapes |
| `-q / --quiet` | off | Suppress progress bars |

### `datasaurus stats FILE`

Print the five statistics for any CSV with `x` and `y` columns.

```bash
uv run datasaurus stats heart.csv
```

### `datasaurus serve`

```bash
uv run datasaurus serve
uv run datasaurus serve --port 8080 --reload
```

---

## API

The streaming endpoint sends a full snapshot of the point cloud every N steps so a frontend can animate the morphing without waiting for annealing to finish.

```bash
uv run datasaurus serve
# http://127.0.0.1:8000
# http://127.0.0.1:8000/docs
```

### `GET /shapes`

```bash
curl http://localhost:8000/shapes
# ["arch", "arrow", "away", ...]
```

### `GET /generate/{shape}`

Server-Sent Events. Each event is the full current point cloud — replace the previous frame with it.

```bash
curl -N "http://localhost:8000/generate/heart?steps=50000&seed=42"
```

| Param | Default | Range | Description |
|---|---|---|---|
| `steps` | 50 000 | 1 000 – 500 000 | Total annealing iterations |
| `seed` | — | — | Random seed |
| `snapshot_every` | 1 000 | 100 – 10 000 | Emit an event every N steps |

Each event:

```json
{ "step": 5000, "total": 50000, "points": [[54.1, 47.2], ...] }
```

Final event adds `stats` and `done`:

```json
{
  "step": 50000, "total": 50000, "done": true,
  "points": [[54.1, 47.2], ...],
  "stats": { "mean_x": 54.26, "mean_y": 47.83, "std_x": 16.76, "std_y": 26.93, "correlation": -0.06 }
}
```

### `GET /generate/{shape}/final`

Blocking. Runs to completion, returns one JSON response.

```bash
curl "http://localhost:8000/generate/heart/final?steps=50000&seed=42"
```

```json
{
  "shape": "heart",
  "steps": 50000,
  "points": [[54.1, 47.2], ...],
  "stats": { "mean_x": 54.26, "mean_y": 47.83, "std_x": 16.76, "std_y": 26.93, "correlation": -0.06 }
}
```

Both endpoints return 404 for unknown shapes.

---

## How it works

Five numbers — mean x, mean y, std x, std y, correlation — can describe an infinite number of distinct datasets. A random cloud of 142 points and a dinosaur-shaped scatterplot can share all five values to two decimal places. The paper demonstrated this, which is why plotting your data matters even when the summary statistics look fine.

The generator starts with 142 points arranged randomly but already satisfying the target statistics. The dataset looks like noise. Annealing then moves it, one point at a time, toward the target shape — accepting moves that bring points closer to the shape and rejecting any move that nudges a statistic outside ±0.01 tolerance. After 200,000 steps the cloud has reorganized into a recognizable shape. The five numbers have not changed.

**The algorithm:**

1. **Initialise.** 142 random points satisfying the target statistics. No structure yet.
2. **Propose.** Pick a random point, nudge it with Gaussian noise (`scale=0.5`).
3. **Evaluate.** Measure the nudged point's distance to the nearest segment of the target shape.
4. **Decide.** Accept if the point moved closer to the shape, is already within `allowed_dist = 2.0` units, or a random draw beats the current temperature.
5. **Enforce.** Check all five statistics before accepting. Any statistic outside ±0.01 of its target discards the move. Runs every step.
6. **Cool.** Temperature falls from 0.4 → 0.0 along an `easeInOutQuad` curve — more exploratory early, more precise late.

**Target statistics** (from the original dino dataset):

| | mean | std |
|---|---|---|
| x | 54.26 | 16.76 |
| y | 47.83 | 26.93 |
| correlation | −0.06 | — |

---

## Shapes (50)

Defined in `shapes.py` with a `@shape("name")` decorator. Each shape is a NumPy array of line segments `[x1, y1, x2, y2]`, centred on the canonical mean.

| | | | | |
|---|---|---|---|---|
| arch | arrow | away | bar_chart | bowtie |
| bullseye | circle | clover | cross | crown |
| diamond | dino | dots | double_sine | ellipse |
| eye | figure_eight | fish | grid | h_lines |
| heart | hexagon | high_lines | hourglass | house |
| infinity | lightning | mountain | octagon | pac_man |
| parabola | pentagon | rings | s_curve | scatter_4 |
| sine | slant_down | slant_up | smiley | spiral |
| staircase | star | sun | tornado | triangle |
| v_lines | wave | wide_lines | x_shape | zigzag |

---

## Tests

```bash
uv run pytest
```

193 tests: stats validation, geometry checks for every shape, SA invariants (stats must hold at every snapshot), and all API endpoints. Runs in ~2 seconds.

---

## Project structure

```
backend/
├── src/datasaurus/
│   ├── stats.py      # TargetStats model, compute_stats, stats_are_valid
│   ├── shapes.py     # @shape decorator, segment geometry, 50 built-in shapes
│   ├── generator.py  # generate_stream() and generate() — the SA core
│   ├── api.py        # FastAPI app: /shapes, /generate/{shape}, /generate/{shape}/final
│   └── cli.py        # Typer CLI: generate, gallery, shapes, stats, serve
├── tests/
│   ├── test_stats.py
│   ├── test_shapes.py
│   ├── test_generator.py
│   └── test_api.py
└── pyproject.toml
```
