# 4. Sweep Line

## 4.1 - Intuition

The **sweep line** is the king paradigm of large-scale geometry.
Picture a vertical line gliding from left to right; as it advances, you
maintain a structure of the objects it **crosses** and process events
(appearance, disappearance, crossing) in x-coordinate order.

The key idea: reduce a 2D geometric problem to a sequence of 1D
problems along the sweep line. Closest pair of points, rectangle union,
intersection detection in $O(n \log n)$: all applications of one
schema.

---

## 4.2 - Algorithms

### Closest pair

Sort points by $x$, sweep while maintaining a window of points whose
x-coordinate is within $d$ (the current best distance), sorted by $y$.
For each new point, only neighbors in a strip of height $2d$ need
comparing - a **constant** number.

**Watch the sweep in motion** : the vertical line glides, the active
band of width $d$ trails it, and only the neighbours inside get
compared. The current best pair is joined in green.

:::viz-sweep-line
:::

### Rectangle union

Sort the distinct x-coordinates. Between two consecutive x's, the set
of active rectangles is fixed; the covered height is the length of the
**union of their $y$-intervals**. Slab area = width $\times$ covered
height.

```python
def union_area(rects):
    xs = sorted({r[0] for r in rects} | {r[2] for r in rects})
    total = 0
    for x1, x2 in zip(xs, xs[1:]):
        ys = sorted((ry1, ry2) for rx1, ry1, rx2, ry2 in rects
                    if rx1 <= x1 and x2 <= rx2)
        covered = 0; cur = None
        for lo, hi in ys:                 # 1D interval union
            if cur is None or lo > cur[1]:
                if cur: covered += cur[1] - cur[0]
                cur = [lo, hi]
            else:
                cur[1] = max(cur[1], hi)
        if cur: covered += cur[1] - cur[0]
        total += (x2 - x1) * covered
    return total
```

---

## 4.3 - Complexity

$$
\begin{aligned}
\text{closest pair} &: \Theta(n \log n), \\
\text{rectangle union (segment tree)} &: \Theta(n \log n), \\
\text{max overlap (compression)} &: \Theta(n^2)\ \text{naive}.
\end{aligned}
$$

Sorting the events dominates; the active structure updates in
$O(\log n)$ per event with a segment tree.

---

## 4.4 - Common pitfalls

1. **Inclusive/exclusive edges.** For overlap, fix a convention (e.g.
   $[x_1, x_2)$) and apply it everywhere, else boundary-cell counts
   diverge.
2. **Coordinate compression.** Essential when coordinates are large:
   keep only the distinct values that delimit the cells.
3. **Area overflow.** The union area can reach $\sim 10^{18}$; use
   64-bit integers (or Python).
4. **Event order.** On equal x-coordinates, the processing order
   (opening before closing) changes the result - define it carefully.

---

## 4.5 - The final paradigm

Intersection detection, area and perimeter of a union, closest pair,
segment envelope, rectangle and interval problems: the sweep turns
static geometry into an ordered film of events. It is the chapter's
natural conclusion - and often the difference between a naive $O(n^2)$
and an $O(n \log n)$ that passes.

---

## 4.6 - Exercises

:::exercise{id="{{EX_GE_CLOSEST_PAIR}}"}
:::

:::exercise{id="{{EX_GE_RECT_UNION}}"}
:::

:::exercise{id="{{EX_GE_MAX_OVERLAP}}"}
:::
