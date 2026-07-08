# 2. Segment Intersection

## 2.1 - Intuition

Knowing whether two segments cross is the second most important
geometric primitive. It is used everywhere: collision detection,
testing whether a polygon is simple, cutting shapes. And like
orientation, it is solved **exactly** in integers, without ever
computing the intersection point.

The idea: two segments $[A, B]$ and $[C, D]$ cross properly if $A$ and
$B$ lie on opposite sides of line $CD$, **and** symmetrically $C$ and
$D$ on opposite sides of $AB$. Collinear cases (overlap, endpoint
touch) are handled separately.

---

## 2.2 - Algorithm

```python
def seg_intersect(p1, p2, p3, p4):
    d1 = cross(p3, p4, p1); d2 = cross(p3, p4, p2)
    d3 = cross(p1, p2, p3); d4 = cross(p1, p2, p4)
    # proper crossing: opposite signs on both sides
    if ((d1 > 0) != (d2 > 0)) and d1 and d2 and \
       ((d3 > 0) != (d4 > 0)) and d3 and d4:
        return True
    # collinear / touch cases: an endpoint on the other segment
    if d1 == 0 and on_seg(p3, p4, p1): return True
    if d2 == 0 and on_seg(p3, p4, p2): return True
    if d3 == 0 and on_seg(p1, p2, p3): return True
    if d4 == 0 and on_seg(p1, p2, p4): return True
    return False
```

`on_seg(p, q, r)` checks that $r$, already **collinear** with $pq$,
lies within the bounding box of $[p, q]$ - hence on the segment.

- **Correctness.** The four orientations cover all cases: two strict
  opposite signs on each side give a crossing at a unique interior
  point; a zero signals a collinear contact, tested explicitly.
  $\square$

**Experiment** : drag the endpoints $A, B, C, D$. The four orientations
$d_1 \dots d_4$ and the verdict update live; try an end-to-end contact
to see the collinear case.

:::viz-segment-intersect
:::

---

## 2.3 - Complexity

$$
\begin{aligned}
\text{two segments} &: \Theta(1), \\
\text{all pairs (}n\text{ segments)} &: \Theta(n^2), \\
\text{simple polygon?} &: \Theta(n^2).
\end{aligned}
$$

The unit test is constant. A **sweep** (lesson 4) lowers detecting any
intersection to $\Theta(n \log n)$.

---

## 2.4 - Common pitfalls

1. **Forgetting collinear cases.** The opposite-signs test misses
   overlaps and endpoint touches; handle them with `on_seg`.
2. **Inclusive bounds.** Depending on whether endpoints count as an
   intersection, adjust the tests - define the convention clearly.
3. **Adjacent polygon edges.** They share a vertex: do not count it as
   a self-intersection, but a collinear **overlap** is forbidden and
   must be detected.
4. **Floating intersection point.** Unnecessary here: the boolean
   predicate is computed entirely in exact integers.

---

## 2.5 - From primitive to applications

Counting intersecting pairs, testing a polygon's simplicity, checking a
path does not self-cross, cutting a scene: all start from the same
predicate. The **exact intersection point** (in rationals) is computed
only when truly needed - often, knowing **whether it exists** is
enough.

---

## 2.6 - Exercises

:::exercise{id="{{EX_GE_SEG_INTERSECT}}"}
:::

:::exercise{id="{{EX_GE_COUNT_INTERSECTIONS}}"}
:::

:::exercise{id="{{EX_GE_SIMPLE_POLYGON}}"}
:::
