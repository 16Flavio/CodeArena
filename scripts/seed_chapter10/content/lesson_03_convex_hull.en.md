# 3. Convex Hull

## 3.1 - Intuition

The **convex hull** of a point cloud is the smallest convex polygon
containing them all - picture a rubber band released around planted
nails. It is one of geometry's most useful structures: it captures the
"outer shape" of a set and underpins a host of algorithms (diameter,
width, distance between shapes).

The computation rests entirely on **orientation** (lesson 1): keep a
point while the contour turns the right way, drop it as soon as it
creates a dent.

---

## 3.2 - Algorithm: monotone chain

Andrew's algorithm sorts the points, then builds the **lower** and
**upper** hull with a stack.

```python
def convex_hull(points):
    pts = sorted(set(points))
    if len(pts) <= 1:
        return pts
    def half(seq):
        h = []
        for p in seq:
            while len(h) >= 2 and cross(h[-2], h[-1], p) <= 0:
                h.pop()               # drop a right (or flat) turn
            h.append(p)
        return h
    lower = half(pts)
    upper = half(reversed(pts))
    return lower[:-1] + upper[:-1]    # without the repeated endpoints
```

- **Correctness.** After the sort, any point causing a non-strictly-
  left turn is interior or collinear, hence dropped. The stack finally
  holds only the vertices, in counterclockwise order.
- **Collinearity.** The test `cross <= 0` **excludes** points collinear
  on an edge; `< 0` would **include** them. Choose per need.

**Step through it** : `step` advances one action at a time. Watch the
stack grow, then a point create a right turn (`cross ≤ 0`) and get
popped (red cross). `run` plays the whole construction.

:::viz-convex-hull
:::

---

## 3.3 - Complexity

$$
T(n) = \underbrace{\Theta(n \log n)}_{\text{sort}} +
\underbrace{\Theta(n)}_{\text{build}} = \Theta(n \log n).
$$

The build is linear (each point is pushed and popped at most once); the
sort dominates.

---

## 3.4 - Common pitfalls

1. **Duplicates and collinear points.** Deduplicate first; explicitly
   decide whether points collinear on an edge count as vertices (`<=`
   vs `<`).
2. **Fewer than 3 points.** Handle separately: a single point, or all
   collinear - the hull degenerates to a point or segment.
3. **Traversal direction.** Depending on the convention (`<= 0` with
   ascending sort), the hull comes out counterclockwise; account for
   that in the signed area.
4. **Floats.** None are needed: the integer `cross` suffices.

---

## 3.5 - What the hull unlocks

Diameter (the two farthest points are hull vertices, found by
**rotating calipers** in linear time on the hull), minimum width,
distance between two clouds, smallest enclosing rectangle: all these
solve **on the hull** rather than on all points. Building it is often
half the work.

---

## 3.6 - Exercises

:::exercise{id="{{EX_GE_HULL_SIZE}}"}
:::

:::exercise{id="{{EX_GE_HULL_AREA}}"}
:::

:::exercise{id="{{EX_GE_DIAMETER}}"}
:::
