"""Typer CLI for Datasaurus.

Commands:
  generate  — one dataset for one shape
  gallery   — grid of datasets
  stats     — summary statistics for an existing CSV
"""

import random
from datetime import datetime
from pathlib import Path
from typing import Annotated

import pandas as pd
import typer
from rich.console import Console
from rich.table import Table

from .generator import GeneratorConfig, generate
from .shapes import available_shapes, get_shape
from .stats import TargetStats, compute_stats

_TARGET = TargetStats()  # canonical stats from the original paper

app = typer.Typer(
    name="datasaurus",
    help="Generate datasets with identical summary statistics but wildly different shapes.",
    add_completion=False,
)
console = Console()


def _build_summary_table(stats: pd.Series, target: TargetStats) -> Table:
    table = Table(title="Summary Statistics", show_header=True)
    table.add_column("Stat", style="cyan")
    table.add_column("Target", justify="right")
    table.add_column("Actual", justify="right")
    table.add_column("Delta", justify="right")
    for name in ("mean_x", "mean_y", "std_x", "std_y", "correlation"):
        tgt = getattr(target, name)
        act = float(stats[name])
        delta = act - tgt
        color = "green" if abs(delta) <= target.tolerance else "red"
        table.add_row(name, f"{tgt:.4f}", f"{act:.4f}", f"[{color}]{delta:+.4f}[/{color}]")
    return table


def _parse_grid(grid: str) -> tuple[int, int]:
    """Parse ROWSxCOLS syntax."""
    try:
        rows_s, cols_s = grid.lower().split("x", maxsplit=1)
        rows, cols = int(rows_s), int(cols_s)
    except ValueError:
        raise typer.BadParameter("Grid must be in ROWSxCOLS format, e.g. 3x4") from None
    if rows <= 0 or cols <= 0:
        raise typer.BadParameter("Grid dimensions must be positive")
    return rows, cols


def _warn_if_low_steps(steps: int) -> None:
    if steps < 20_000:
        console.print(
            "[yellow]Warning:[/yellow] low --steps may produce under-formed shapes. "
            "Use 50k–200k for clear results."
        )


def _select_gallery_shapes(
    rows: int,
    cols: int,
    shapes: str | None,
    all_builtin: list[str],
    rng: random.Random,
) -> list[str]:
    """Select unique shape names for the gallery grid."""
    total_cells = rows * cols
    if shapes is None:
        if total_cells > len(all_builtin):
            raise typer.BadParameter(
                f"Grid has {total_cells} cells but only {len(all_builtin)} built-in shapes. "
                "Use a smaller grid or pass --shapes."
            )
        return rng.sample(all_builtin, total_cells)

    selected = [item.strip() for item in shapes.split(",") if item.strip()]
    if len(selected) != total_cells:
        raise typer.BadParameter(
            f"--shapes must provide exactly {total_cells} names for a {rows}x{cols} grid."
        )
    if len(set(selected)) != len(selected):
        raise typer.BadParameter("--shapes contains duplicates. Repeats are not allowed.")

    missing = sorted(set(selected) - set(all_builtin))
    if missing:
        raise typer.BadParameter(f"Unknown shapes: {', '.join(missing)}")
    return selected


@app.command("generate")
def generate_cmd(
    shape: Annotated[str, typer.Argument(help="Built-in shape name (run 'datasaurus shapes' to list)")],
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Write generated CSV to this path")] = None,
    steps: Annotated[int, typer.Option("--steps", "-s", min=1, help="Annealing steps (default 200k)")] = 200_000,
    seed: Annotated[int | None, typer.Option("--seed", help="Random seed for reproducibility")] = None,
    plot: Annotated[bool, typer.Option("--plot", "-p", help="Show scatter plot after generation")] = False,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Disable progress bar")] = False,
):
    """Generate one dataset shaped like SHAPE.

    Examples:

      datasaurus generate circle
      datasaurus generate heart --output heart.csv --seed 42
      datasaurus generate dino --plot
    """
    _warn_if_low_steps(steps)

    segs = get_shape(shape)
    config = GeneratorConfig(max_steps=steps, seed=seed, show_progress=not quiet)
    df = generate(segs, target=_TARGET, config=config)

    console.print(_build_summary_table(compute_stats(df), _TARGET))

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output, index=False)
        console.print(f"[bold]Saved:[/bold] {output}")

    if plot:
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            raise typer.BadParameter("matplotlib is required for --plot. Run: uv add --dev matplotlib") from None
        plt.figure(figsize=(6, 5))
        plt.scatter(df["x"], df["y"], s=10, alpha=0.7)
        plt.title(f"datasaurus: {shape}")
        plt.xlabel("x")
        plt.ylabel("y")
        plt.tight_layout()
        plt.show()


@app.command("gallery")
def gallery_cmd(
    grid: Annotated[str, typer.Option("--grid", help="Grid size as ROWSxCOLS (e.g. 3x4)")] = "5x10",
    shapes: Annotated[
        str | None,
        typer.Option("--shapes", help="Comma-separated shape names. Must match grid cell count."),
    ] = None,
    output_dir: Annotated[Path | None, typer.Option("--output-dir", help="Directory for outputs (default: runs/TIMESTAMP)")] = None,
    steps: Annotated[int, typer.Option("--steps", "-s", min=1, help="Annealing steps per dataset (default 200k)")] = 200_000,
    seed: Annotated[int | None, typer.Option("--seed", help="Random seed")] = None,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Disable progress bars")] = False,
):
    """Generate a grid of datasets and save a gallery image + CSVs.

    Examples:

      datasaurus gallery
      datasaurus gallery --grid 3x4 --seed 42
      datasaurus gallery --shapes circle,heart,dino --grid 1x3
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise typer.BadParameter("matplotlib is required for gallery. Run: uv add --dev matplotlib") from None

    rows, cols = _parse_grid(grid)
    all_builtin = available_shapes()
    _warn_if_low_steps(steps)

    rng = random.Random(seed)
    selected_shapes = _select_gallery_shapes(rows, cols, shapes, all_builtin, rng)

    out_dir = output_dir or Path("runs") / datetime.now().strftime("%Y%m%d-%H%M%S")
    datasets_dir = out_dir / "datasets"
    datasets_dir.mkdir(parents=True, exist_ok=True)

    description = (
        f"Datasaurus Gallery ({rows}x{cols}): Same Summary Stats, Different Shapes.\n"
        "Each panel preserves nearly identical mean, standard deviation, and correlation, "
        "yet the geometry differs dramatically."
    )
    (out_dir / "description.txt").write_text(description + "\n")

    fig, axes = plt.subplots(rows, cols, figsize=(4.2 * cols, 3.4 * rows), squeeze=False)
    summary_rows: list[dict] = []

    for idx, shape_name in enumerate(selected_shapes):
        segs = get_shape(shape_name)
        config = GeneratorConfig(
            max_steps=steps,
            seed=None if seed is None else seed + idx,
            show_progress=not quiet,
        )
        df = generate(segs, target=_TARGET, config=config)
        stats = compute_stats(df)

        df.to_csv(datasets_dir / f"{idx + 1:02d}_{shape_name}.csv", index=False)

        r, c = divmod(idx, cols)
        ax = axes[r][c]
        ax.scatter(df["x"], df["y"], s=6, alpha=0.75)
        ax.set_title(shape_name)
        ax.set_xlim(0, 110)
        ax.set_ylim(0, 100)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xticks([])
        ax.set_yticks([])

        summary_rows.append({
            "shape": shape_name,
            **{k: float(stats[k]) for k in stats.index},
            **{f"delta_{k}": float(stats[k]) - getattr(_TARGET, k) for k in stats.index},
        })

    title = f"Datasaurus Gallery ({rows}x{cols}): Same Summary Stats, Different Shapes"
    fig.suptitle(title, fontsize=14)
    fig.tight_layout(rect=(0, 0.0, 1, 0.94))
    gallery_path = out_dir / "gallery.png"
    fig.savefig(gallery_path, dpi=200)
    plt.close(fig)

    pd.DataFrame(summary_rows).to_csv(out_dir / "summary.csv", index=False)

    console.print(f"[bold]Gallery:[/bold] {gallery_path}")
    console.print(f"[bold]Summary:[/bold] {out_dir / 'summary.csv'}")
    console.print(f"[bold]Datasets:[/bold] {datasets_dir}/")


@app.command("stats")
def stats_cmd(
    csv_file: Annotated[
        Path,
        typer.Argument(exists=True, file_okay=True, dir_okay=False, help="CSV file with x and y columns"),
    ],
):
    """Show summary statistics for an existing CSV file."""
    stats = compute_stats(pd.read_csv(csv_file))
    table = Table(title=f"Stats: {csv_file.name}", show_header=True)
    table.add_column("Stat", style="cyan")
    table.add_column("Value", justify="right")
    for key, value in stats.items():
        table.add_row(key, f"{value:.6f}")
    console.print(table)


@app.command("shapes")
def shapes_cmd():
    """List all available built-in shapes."""
    names = available_shapes()
    console.print(f"[bold]{len(names)} built-in shapes:[/bold]")
    for name in names:
        console.print(f"  {name}")


@app.command("serve")
def serve_cmd(
    host: Annotated[str, typer.Option("--host", help="Bind host")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", help="Bind port")] = 8000,
    reload: Annotated[bool, typer.Option("--reload", help="Auto-reload on code changes")] = False,
):
    """Start the FastAPI server.

    Examples:

      datasaurus serve
      datasaurus serve --port 8080 --reload
    """
    try:
        import uvicorn
    except ImportError:
        raise typer.BadParameter("uvicorn is required. Run: uv add uvicorn") from None
    uvicorn.run("datasaurus.api:app", host=host, port=port, reload=reload)


def main() -> None:
    app()
