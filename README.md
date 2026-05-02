# Datasaurus

<p align="center">
  <img src="docs/screenshot-running.png" alt="Nine shapes morphing simultaneously, all sharing identical summary statistics" width="100%" />
</p>

<p align="center"><sub>Nine different shapes. Same mean, same standard deviation, same correlation. Every cell reads x̄ ≈ 54.26, ȳ ≈ 47.83, σx ≈ 16.76, σy ≈ 26.93, r ≈ −0.06.</sub></p>

---

## Why this exists

When you summarise a dataset, you report a handful of numbers: the mean, the standard deviation, the correlation. These are the first things you compute, the first things you put in a table, and often the last things anyone looks at before drawing conclusions.

The problem is that these numbers throw away almost everything about the data. The mean tells you the centre. The standard deviation tells you the spread. The correlation tells you the linear trend. None of them tell you the *shape* — where the points actually are, how they cluster, what structure they form.

In 2017, Justin Matejka and George Fitzmaurice demonstrated this by constructing thirteen datasets that all share the same summary statistics to two decimal places but look completely different when plotted. One is a dinosaur. One is a star. One is a set of parallel lines. The five numbers are identical. The scatterplots have nothing in common.

The original Datasaurus — a T. rex hiding in a summary table — was created by Alberto Cairo to make this point. Matejka and Fitzmaurice turned it into a method: given any target shape, produce a dataset that matches a set of summary statistics while visually resembling that shape.

The lesson is simple: **if you don't plot your data, you don't understand your data.** Summary statistics are lossy compression. They hide structure, outliers, clusters, gaps, and patterns that would be obvious in a scatterplot. This tool lets you watch that happen in real time.

---

## What this tool does

Datasaurus takes a target shape — a heart, a spiral, a hexagon, any of 50 built-in outlines — and rearranges a cloud of points until the cloud looks like that shape. By default there are 142 points (matching the original paper), adjustable from 50 to 500.

The constraint: five summary statistics must stay within ±0.01 of their target values at every single step. Not just at the end. At every step.

The shapes are just geometry — line segments forming an outline. They don't have statistics. The point cloud has the statistics. The algorithm's job is to move points toward the shape boundary without ever letting the statistics slip.

You can run up to 16 shapes simultaneously in a grid. Each cell morphs independently, and each cell's stats overlay shows the same five numbers throughout. The numbers are useless for telling the shapes apart.

---

## The invariant

Every dataset this tool produces shares the same five numbers, taken from the original Datasaurus dataset:

| | Mean | Std Dev |
|:--|--:|--:|
| **x** | 54.26 | 16.76 |
| **y** | 47.83 | 26.93 |
| **r** | −0.06 | |

Tolerance: ±0.01. Enforced on every step of every run. The enforcement is not a post-hoc check — it's a hard gate. Every proposed point move is speculatively applied to five running sums (Σx, Σy, Σx², Σy², Σxy), and if any derived statistic drifts outside tolerance, the move is reverted before anything else happens. This runs in O(1) per step via incremental updates, not O(n) recomputation.

---

## The shared structure

All three algorithms follow the same loop. Every step, for 400,000 steps:

1. **Pick a point.** Choose one of the 142 points at random.
2. **Propose a move.** How the move is proposed is where the algorithms differ.
3. **Check the stats.** Speculatively update the five running sums. If any statistic leaves the ±0.01 tolerance band, revert immediately. No exceptions.
4. **Check the shape.** Measure the point's distance to the nearest segment of the target shape (via a KDTree built from the rasterised shape boundary). If the point moved closer, accept. If it moved further away, accept with probability exp(−Δd/T) where T is the current temperature.
5. **Cool.** Temperature follows an easeInOutQuad S-curve from 0.4 → 0.0. Exploratory early, precise late.

Step 3 is the hard constraint. Step 4 is the soft objective. The algorithms differ only in step 2.

---

## Annealing

*The original. From the paper.*

### How it proposes moves

Pick a random point. Add Gaussian noise (σ = 0.5) to both coordinates. That's it. The point doesn't know where the shape is. It doesn't know which direction is better. It just wanders.

### Why it works

The acceptance rule in step 4 does all the work. Early in the run, the temperature is high and almost any move is accepted — points explore freely. Late in the run, the temperature is near zero and only moves that reduce distance to the shape survive. Over hundreds of thousands of steps, the random walk is filtered into a directed flow toward the shape boundary.

### Why it's slow

Most proposals are wasted. A random perturbation has no reason to point toward the shape. Late in the run, when the temperature is low and the acceptance threshold is tight, the vast majority of proposals are rejected. The algorithm spends most of its time proposing moves that go nowhere.

This is the method from Matejka & Fitzmaurice (2017). It works. It's just not efficient.

---

## Langevin

*Knows which way to go.*

### How it proposes moves

Pick a random point. Look up the nearest point on the target shape boundary (KDTree query). Compute the unit vector from the current position toward that nearest boundary point. The proposed move is:

```
new_position = current + scale × (1 − T) × direction + scale × T × noise
```

Two terms. The first is a **drift** toward the shape, scaled by `(1 − T)` — weak when the temperature is high, strong when it's low. The second is **random noise**, scaled by `T` — strong when the temperature is high, weak when it's low.

### Why it's faster

The proposals are better. Instead of random noise in every direction, the move is biased toward the shape. Fewer proposals get rejected because more of them are going the right way. Points flow toward the boundary instead of stumbling into it.

### The tradeoff

Early in the run, the noise term dominates and the behaviour is similar to annealing — exploratory, undirected. Late in the run, the drift term dominates and points move almost directly toward the nearest boundary segment. The transition is smooth because both terms are controlled by the same temperature schedule.

The direction is always toward the *nearest* boundary point, not the globally optimal position. For convex shapes this works well. For shapes with concavities (like a star or a figure-eight), a point might drift toward the wrong segment of the boundary. The acceptance rule in step 4 catches most of these, but convergence on complex shapes can be slower than on simple ones.

---

## Momentum

*Carries speed. Overshoots. Settles.*

### How it proposes moves

Each point carries a persistent velocity vector (vx, vy) that accumulates between steps. Every step:

1. Look up the nearest boundary point and compute the direction (same as Langevin).
2. Update velocity: `v = β × v + scale × direction + noise`. The friction coefficient β = 0.85 means velocity decays by 15% each step. Noise is scaled by temperature.
3. Clamp velocity to ±1.5 (3 × scale) to prevent runaway.
4. Propose: `new_position = current + v`.

### Why it looks different

Points don't stop when they reach the boundary. They overshoot, swing back, overshoot again, and gradually settle. This produces a visible oscillation during the run that the other two algorithms don't have. It looks like points are bouncing off the shape boundary.

### Why it converges fast

Velocity accumulates. A point that's been moving toward the boundary for several steps has built up speed and covers more ground per step than annealing or Langevin. On shapes with long straight edges (like a triangle or a rectangle), this is a significant advantage — points sweep along the edge quickly.

### When it struggles

If a proposed move is rejected by the stat constraint (step 3), the velocity is zeroed — the point loses all its accumulated speed and starts over. If a move passes the stat check but is rejected by the shape check (step 4), the velocity is reversed and damped: `v *= −0.3`. This simulates a bounce. On shapes with many tight curves, the constant bouncing and velocity resets slow convergence compared to Langevin's smoother drift.

---

## 50 shapes

Every shape is defined as line segments in `shapes.py` with a `@shape("name")` decorator. The KDTree is built by rasterising these segments at 0.3-unit spacing — dense enough that the nearest-point query error is well below the 2.0-unit acceptance threshold.

`arch` · `arrow` · `away` · `bar_chart` · `bowtie` · `bullseye` · `circle` · `clover` · `cross` · `crown` · `diamond` · `dino` · `dots` · `double_sine` · `ellipse` · `eye` · `figure_eight` · `fish` · `grid` · `h_lines` · `heart` · `hexagon` · `high_lines` · `hourglass` · `house` · `infinity` · `lightning` · `mountain` · `octagon` · `pac_man` · `parabola` · `pentagon` · `rings` · `s_curve` · `scatter_4` · `sine` · `slant_down` · `slant_up` · `smiley` · `spiral` · `staircase` · `star` · `sun` · `tornado` · `triangle` · `v_lines` · `wave` · `wide_lines` · `x_shape` · `zigzag`

---

## Built with

Python · FastAPI · SSE · NumPy · SciPy · Next.js · Zustand · framer-motion · Canvas

See [CONTRIBUTING.md](CONTRIBUTING.md) to run it locally.

---

## Credits

[Same Stats, Different Graphs](https://www.autodesk.com/research/publications/same-stats-different-graphs) — Justin Matejka & George Fitzmaurice, ACM CHI 2017. The original Datasaurus was created by [Alberto Cairo](http://www.thefunctionalart.com/2016/08/download-datasaurus-never-trust-summary.html).
