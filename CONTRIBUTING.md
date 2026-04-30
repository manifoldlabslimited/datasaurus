# Contributing

## Prerequisites

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- [Bun](https://bun.sh/) (or Node 18+)

## Setup

### Backend

```bash
cd backend
uv sync
uv run datasaurus serve
```

The API runs at `http://localhost:8000`. Hit `/docs` for the Swagger UI.

### Frontend

```bash
cd frontend
bun install
bun run dev
```

Open `http://localhost:3000`.

## CLI

```bash
# List all shapes
uv run datasaurus shapes

# Generate a single dataset
uv run datasaurus generate heart --plot

# Generate a gallery
uv run datasaurus gallery --grid 5x10

# Print stats for a CSV
uv run datasaurus stats heart.csv
```

## Tests

```bash
cd backend
uv run pytest
```

223 tests. Runs in ~3 seconds.

## Project structure

```
backend/
├── src/datasaurus/
│   ├── stats.py        Target statistics, validation, computation
│   ├── shapes.py       50 shapes as line segment arrays
│   ├── generator.py    SA / Langevin / Momentum core loops
│   ├── api.py          FastAPI: SSE streaming, batch endpoint
│   └── cli.py          Typer CLI: generate, gallery, serve
└── tests/              223 tests

frontend/
├── src/
│   ├── app/            Next.js app shell, layout, theme
│   ├── components/     Grid, scatter canvas, controls, shape picker
│   ├── hooks/          SSE streaming hook
│   ├── store/          Zustand state management
│   └── lib/            Types, theme, animation context
└── package.json
```

## API endpoints

| Endpoint | Description |
|---|---|
| `GET /shapes` | List all available shape names |
| `GET /generate/batch?shapes=dino,heart&steps=50000` | SSE stream for multiple shapes in lockstep |
| `GET /generate/{shape}?steps=50000` | SSE stream for a single shape |
| `GET /generate/{shape}/final` | Blocking JSON response with final dataset |
