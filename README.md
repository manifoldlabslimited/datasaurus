# Datasaurus

A dinosaur, a star, and a circle walk into a dataset. They have the same mean, the same standard deviation, and the same correlation. You can't tell them apart by their statistics. You can only tell them apart by *looking*.

This is the core insight behind [Matejka & Fitzmaurice's 2017 CHI paper](https://www.autodesk.com/research/publications/same-stats-different-graphs): summary statistics can be identical across wildly different distributions. The only defense is to **plot your data**.

Datasaurus makes this visceral. Pick a grid of target shapes, hit Simulate, and watch 142 points rearrange themselves — in real time — from random noise into recognizable figures, all while five statistics hold steady to two decimal places.

## The numbers that never change

Every dataset produced by Datasaurus shares these statistics (±0.01):

| Statistic | Value |
|---|---|
| Mean x | 54.26 |
| Mean y | 47.83 |
| Std dev x | 16.76 |
| Std dev y | 26.93 |
| Correlation | −0.06 |

A heart and a dinosaur. A spiral and a grid. Same five numbers. Different stories.

---

## How it works

1. **Start with noise.** 142 random points, carefully constructed to already satisfy the target statistics.
2. **Pick a point, nudge it.** Small Gaussian perturbation — just enough to explore.
3. **Check the stats.** If any of the five statistics drifts outside ±0.01 tolerance, reject the move. Non-negotiable.
4. **Check the shape.** If the point moved closer to the target shape, accept. If not, maybe accept anyway — with probability that decreases as the system cools.
5. **Repeat a million times.** The temperature drops along an easeInOutQuad curve. Early on, the system explores freely. Late in the run, it locks into the shape.

The result: a point cloud that looks like a dinosaur but is statistically indistinguishable from a circle.

Three algorithms are available:
- **Simulated Annealing (SA)** — the classic. Blind random walk with Metropolis acceptance.
- **Langevin Dynamics** — gradient-guided drift toward the shape boundary, plus temperature-scaled noise.
- **Momentum** — heavy-ball gradient descent. Velocity accumulates, creating a distinctive sweep-and-oscillate motion.

All three preserve the same five statistics throughout.

---

## Quick start

### Backend

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
cd backend
uv sync
uv run datasaurus serve
```

The API is now at `http://localhost:8000`. Hit `/docs` for the interactive Swagger UI.

### Frontend

Requires [Bun](https://bun.sh/) (or Node 18+).

```bash
cd frontend
bun install
bun run dev
```

Open `http://localhost:3000`. Pick shapes. Hit Simulate. Watch.

---

## CLI

The backend doubles as a command-line tool.

```bash
# List all 50 shapes
uv run datasaurus shapes

# Generate a single dataset
uv run datasaurus generate heart --plot
uv run datasaurus generate dino --steps 500000 --seed 42 --output dino.csv

# Generate a gallery of all shapes
uv run datasaurus gallery --grid 5x10

# Print stats for any CSV with x,y columns
uv run datasaurus stats heart.csv

# Start the API server
uv run datasaurus serve --port 8080 --reload
```

---

## API

### `GET /shapes`

Returns all available shape names.

### `GET /generate/batch?shapes=dino,heart,circle&steps=50000`

Server-Sent Events. Streams progress for multiple shapes in lockstep — every event carries the full point cloud for every shape at the same step.

```json
{
  "step": 25000,
  "total": 50000,
  "cells": [
    { "shape": "dino", "points": [[54.1, 47.2], ...], "stats": { ... } },
    { "shape": "heart", "points": [[52.3, 48.1], ...], "stats": { ... } }
  ]
}
```

Final event includes `"done": true`.

### `GET /generate/{shape}?steps=50000`

SSE stream for a single shape.

### `GET /generate/{shape}/final`

Blocking. Runs to completion, returns one JSON response.

---

## Shapes (50)

Every shape is defined as line segments in `shapes.py` with a `@shape("name")` decorator.

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

## Architecture

```
backend/
├── src/datasaurus/
│   ├── stats.py        Target statistics, validation, computation
│   ├── shapes.py       50 shapes as line segment arrays
│   ├── generator.py    SA / Langevin / Momentum core loops
│   ├── api.py          FastAPI: SSE streaming, batch endpoint
│   └── cli.py          Typer CLI: generate, gallery, serve
└── tests/              223 tests — stats, shapes, generator, API

frontend/
├── src/
│   ├── app/            Next.js app shell, layout, globals
│   ├── components/     Grid, scatter canvas, controls, shape picker
│   ├── hooks/          SSE streaming hook
│   ├── store/          Zustand state management
│   └── lib/            Types, theme, animation context
└── package.json
```

---

## Tests

```bash
cd backend
uv run pytest
```

223 tests covering stats validation, geometry for every shape, SA invariants (statistics must hold at every snapshot), and all API endpoints. Runs in ~3 seconds.

---

## Credits

Based on [Same Stats, Different Graphs](https://www.autodesk.com/research/publications/same-stats-different-graphs) by Justin Matejka and George Fitzmaurice (ACM CHI 2017). The original Datasaurus was created by Alberto Cairo.
