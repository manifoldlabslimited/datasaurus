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

Tolerance: ±0.01. Enforced on every step of every run. The enforcement is not a post-hoc check — it's a hard gate. Every proposed point move is speculatively applied to five running sums ($\Sigma x$, $\Sigma y$, $\Sigma x^2$, $\Sigma y^2$, $\Sigma xy$), and if any derived statistic drifts outside tolerance, the move is reverted before anything else happens. This runs in $O(1)$ per step via incremental updates, not $O(n)$ recomputation.

---

## The shared structure

All three algorithms follow the same loop. Every step, for 400,000 steps:

1. **Pick a point.** Choose one of the 142 points at random.
2. **Propose a move.** How the move is proposed is where the algorithms differ.
3. **Check the stats.** Speculatively update the five running sums. If any statistic leaves the ±0.01 tolerance band, revert immediately. No exceptions.
4. **Check the shape.** Measure the point's distance to the nearest segment of the target shape (via a KDTree built from the rasterised shape boundary). If the point moved closer, accept. If it moved further away, accept with probability $e^{-\Delta d / T}$ where $T$ is the current temperature.
5. **Cool.** Temperature follows an easeInOutQuad S-curve from $T_0 = 0.4 \to T_{\min} = 0.0$. Exploratory early, precise late.

Step 3 is the hard constraint. Step 4 is the soft objective. The algorithms differ only in step 2.

---

## Annealing

*The original. From the paper.*

### Inspiration

Simulated annealing borrows its name from metallurgy. When you heat metal and let it cool slowly, the atoms settle into a low-energy crystalline structure. Cool it too fast and you get a brittle, disordered mess. The insight, formalised by Kirkpatrick, Gelatt, and Vecchi in 1983, is that you can apply the same idea to optimisation: let a system explore freely at high temperature, then gradually tighten the acceptance criteria as the temperature drops. The system finds good solutions not by being clever about where to look, but by being patient about how long to look.

Matejka and Fitzmaurice used this to morph datasets. Their 2017 paper is the direct ancestor of this implementation.

### How it proposes moves

Pick one of the $n$ points at random. Add independent Gaussian noise to both coordinates:

$$\mathbf{x}' = \mathbf{x} + \boldsymbol{\eta}, \quad \boldsymbol{\eta} \sim \mathcal{N}(0, \sigma^2 I), \quad \sigma = 0.5$$

The perturbation is isotropic — it has no preferred direction. The point doesn't know where the shape is. It doesn't know which direction would reduce its distance to the boundary. It proposes a move and waits to be told whether it was a good idea.

### The acceptance rule

After the stat constraint passes (step 3), the move reaches the shape check (step 4). Let $d$ be the point's current distance to the nearest shape segment, and $d'$ the distance after the proposed move. Three cases:

- $d' < d$ — the point moved closer. **Always accept.**
- $d' < d_{\text{allowed}}$ (2.0 units) — the point is already near the shape. **Always accept**, even if it moved slightly further away. This prevents points from getting stuck oscillating around the boundary.
- Otherwise — accept with probability $e^{-(d' - d)/T}$. When $T$ is high, this probability is close to 1 and bad moves slip through. When $T$ is near zero, only moves that reduce distance survive.

The temperature $T$ follows an easeInOutQuad curve from 0.4 to 0.0 over the full run. The S-shape means the temperature drops slowly at the start (long exploration phase), accelerates through the middle, and slows again near the end (fine-tuning phase).

### Why it works

No single step is smart. The proposal is random. The acceptance is probabilistic. But over 400,000 steps, the temperature schedule turns a random walk into a directed search. Points that happen to land near the shape boundary stay there (low $T$ rejects moves away). Points that are far from the boundary keep wandering until they stumble close enough to stick.

### Why it's slow

The proposal has no bias toward the shape. In two dimensions, a random perturbation has a roughly equal chance of going in any direction. Only a small fraction of those directions reduce the distance to a specific boundary curve. Late in the run, when $T$ is low and the acceptance threshold is tight, the vast majority of proposals are rejected. The algorithm spends most of its time proposing moves that go nowhere.

This is the method from Matejka & Fitzmaurice (2017). It produces correct results. It's just not efficient about getting there.

---

## Langevin

*Knows which way to go.*

### How it proposes moves

Pick a random point. Look up the nearest point on the target shape boundary (KDTree query). Compute the unit vector from the current position toward that nearest boundary point. The proposed move is:

$$\mathbf{x}' = \mathbf{x} + \underbrace{\alpha(1 - T)\hat{\mathbf{u}}}_{\text{drift toward shape}} + \underbrace{\alpha T \boldsymbol{\eta}}_{\text{thermal noise}}$$

where $\alpha = 0.5$ is the perturbation scale, $T$ is the current temperature, $\hat{\mathbf{u}}$ is the unit direction toward the nearest boundary point, and $\boldsymbol{\eta} \sim \mathcal{N}(0, 1)$.

Two terms. The first is a **drift** toward the shape, scaled by $(1 - T)$ — weak when the temperature is high, strong when it's low. The second is **random noise**, scaled by $T$ — strong when the temperature is high, weak when it's low.

### Why it's faster

The proposals are better. Instead of random noise in every direction, the move is biased toward the shape. Fewer proposals get rejected because more of them are going the right way. Points flow toward the boundary instead of stumbling into it.

### The tradeoff

Early in the run, the noise term dominates and the behaviour is similar to annealing — exploratory, undirected. Late in the run, the drift term dominates and points move almost directly toward the nearest boundary segment. The transition is smooth because both terms are controlled by the same temperature schedule.

The direction is always toward the *nearest* boundary point, not the globally optimal position. For convex shapes this works well. For shapes with concavities (like a star or a figure-eight), a point might drift toward the wrong segment of the boundary. The acceptance rule in step 4 catches most of these, but convergence on complex shapes can be slower than on simple ones.

---

## Momentum

*Carries speed. Overshoots. Settles.*

### How it proposes moves

Each point carries a persistent velocity vector $(\mathbf{v}_x, \mathbf{v}_y)$ that accumulates between steps. Every step:

1. Look up the nearest boundary point and compute the direction $\hat{\mathbf{u}}$ (same as Langevin).
2. Update velocity:

$$\mathbf{v} \leftarrow \text{clamp}\Big(\beta \mathbf{v} + \alpha \hat{\mathbf{u}} + \sigma \boldsymbol{\eta},\; \pm v_{\max}\Big)$$

where $\beta = 0.85$ is the friction coefficient (velocity decays 15% each step), $\alpha = 0.5$ is the perturbation scale, $\sigma = \alpha \cdot \max(0.05, T)$ scales noise by temperature, and $v_{\max} = 1.5$.

3. Propose: $\mathbf{x}' = \mathbf{x} + \mathbf{v}$.

### Why it looks different

Points don't stop when they reach the boundary. They overshoot, swing back, overshoot again, and gradually settle. This produces a visible oscillation during the run that the other two algorithms don't have. It looks like points are bouncing off the shape boundary.

### Why it converges fast

Velocity accumulates. A point that's been moving toward the boundary for several steps has built up speed and covers more ground per step than annealing or Langevin. On shapes with long straight edges (like a triangle or a rectangle), this is a significant advantage — points sweep along the edge quickly.

### When it struggles

If a proposed move is rejected by the stat constraint (step 3), the velocity is zeroed — the point loses all its accumulated speed and starts over. If a move passes the stat check but is rejected by the shape check (step 4), the velocity is reversed and damped: $\mathbf{v} \leftarrow -0.3\mathbf{v}$. This simulates a bounce. On shapes with many tight curves, the constant bouncing and velocity resets slow convergence compared to Langevin's smoother drift.

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
