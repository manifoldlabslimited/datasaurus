# Datasaurus

A dinosaur and a circle can have the same mean, the same standard deviation, and the same correlation. You can't tell them apart from five numbers. You have to plot them.

This is the point of [Matejka & Fitzmaurice (CHI 2017)](https://www.autodesk.com/research/publications/same-stats-different-graphs): summary statistics lie by omission. Two datasets can be statistically identical and look nothing alike. The original Datasaurus, created by Alberto Cairo, made this famous. We made it real-time.

Pick shapes. Hit simulate. Watch 142 points rearrange themselves into a parabola, a heart, a spiral — while the stats at the bottom of each cell refuse to budge.

<p align="center">
  <img src="docs/screenshot-running.png" alt="Nine shapes morphing simultaneously, all sharing identical summary statistics" width="100%" />
</p>

<p align="center"><sub>Nine shapes at step 469,000 of 1,000,000. Every cell reads x̄ ≈ 54.26, ȳ ≈ 47.83, σx ≈ 16.76, σy ≈ 26.93, r ≈ −0.06.</sub></p>

---

## How it works

Start with 142 random points that already satisfy the target statistics. Then, a million times:

1. Pick a random point. Nudge it.
2. Did any of the five stats drift outside ±0.01? Reject the move.
3. Did the point land closer to the target shape? Keep it. Further away? Keep it anyway, with a probability that drops as the temperature cools.

That's it. The temperature falls on an S-curve — loose early, tight late. By the end, the cloud looks like a dinosaur (or a heart, or a hexagon) and the stats haven't moved.

Three flavors:

- **SA** — blind random walk, Metropolis acceptance. The original.
- **Langevin** — biased toward the shape boundary, with thermal noise. Smoother convergence.
- **Momentum** — velocity accumulates like a heavy ball rolling downhill. Oscillates, then settles.

---

## The invariant

Every dataset this tool produces shares the same five numbers:

| | Mean | Std Dev |
|:--|--:|--:|
| **x** | 54.26 | 16.76 |
| **y** | 47.83 | 26.93 |
| **r** | −0.06 | |

Tolerance: ±0.01. Enforced on every single step.

---

## 50 shapes

`arch` · `arrow` · `away` · `bar_chart` · `bowtie` · `bullseye` · `circle` · `clover` · `cross` · `crown` · `diamond` · `dino` · `dots` · `double_sine` · `ellipse` · `eye` · `figure_eight` · `fish` · `grid` · `h_lines` · `heart` · `hexagon` · `high_lines` · `hourglass` · `house` · `infinity` · `lightning` · `mountain` · `octagon` · `pac_man` · `parabola` · `pentagon` · `rings` · `s_curve` · `scatter_4` · `sine` · `slant_down` · `slant_up` · `smiley` · `spiral` · `staircase` · `star` · `sun` · `tornado` · `triangle` · `v_lines` · `wave` · `wide_lines` · `x_shape` · `zigzag`

---

## Built with

Python · FastAPI · SSE · NumPy · SciPy · Next.js · Zustand · framer-motion · Canvas

See [CONTRIBUTING.md](CONTRIBUTING.md) to run it locally.

---

## Credits

[Same Stats, Different Graphs](https://www.autodesk.com/research/publications/same-stats-different-graphs) — Justin Matejka & George Fitzmaurice, ACM CHI 2017. The original Datasaurus was created by [Alberto Cairo](http://www.thefunctionalart.com/2016/08/download-datasaurus-never-trust-summary.html).
