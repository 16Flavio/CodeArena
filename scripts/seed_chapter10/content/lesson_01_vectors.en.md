# 1. Vectors, Products & Orientation

## 1.1 - Intuition

Computational geometry rests on a tiny operation: the 2D **cross
product**. It answers the most frequent question - "which way do we
turn?" - and from it flow area, orientation, membership, intersection.

Crucially, if the coordinates are **integer**, so is the cross product.
You then avoid floats entirely and their rounding errors, a notorious
source of geometric bugs. This whole lesson stays in **exact**
arithmetic.

---

## 1.2 - Algorithms

### Cross product & orientation

For three points $A$, $B$, $C$:

$$
\overrightarrow{AB} \times \overrightarrow{AC} =
(b_x - a_x)(c_y - a_y) - (b_y - a_y)(c_x - a_x).
$$

```python
def cross(o, a, b):
    return (a[0]-o[0]) * (b[1]-o[1]) - (a[1]-o[1]) * (b[0]-o[0])
```

The **sign** says everything: positive = $C$ left of $A \to B$
(counterclockwise), negative = right (clockwise), zero = collinear.

### Area via the shoelace formula

For a polygon $P_0, \dots, P_{n-1}$:

$$
2A = \left| \sum_{i=0}^{n-1} (x_i y_{i+1} - x_{i+1} y_i) \right|,
$$

with cyclic indices. Return $2A$ to stay integer.

### Pick's theorem

For a polygon with integer vertices,

$$
A = I + \frac{B}{2} - 1,
$$

where $I$ is the number of **interior** integer points and $B$ those on
the **boundary**. Since $B = \sum \gcd(|\Delta x|, |\Delta y|)$ per
edge, you get $I$ directly.

---

## 1.3 - Complexity

$$
\begin{aligned}
\text{cross product / orientation} &: \Theta(1), \\
\text{area, Pick} &: \Theta(n).
\end{aligned}
$$

Everything is linear or constant, and **exact** in integers.

---

## 1.4 - Common pitfalls

1. **Needless floats.** Never convert to float when the inputs are
   integer; the integer cross product suffices and avoids rounding
   errors.
2. **Overflow.** For coordinates $\sim 10^9$, the cross product reaches
   $\sim 10^{18}$: fit in a 64-bit integer (or Python, unbounded).
3. **Signed vs absolute area.** The shoelace formula gives the
   **signed** area (positive if counterclockwise); take the absolute
   value if the order is not guaranteed.
4. **Pick out of scope.** The theorem requires **integer** vertices and
   a **simple** polygon; otherwise the formula fails.

---

## 1.5 - The brick under everything else

Orientation, area, half-plane membership, angular comparison for
sorting: the cross product is the only primitive you truly need.
Segment intersection (lesson 2), convex hull (lesson 3), sweep line
(lesson 4) all follow from it. Mastering it in integers is building on
rock.

---

## 1.6 - Exercises

:::exercise{id="{{EX_GE_ORIENT}}"}
:::

:::exercise{id="{{EX_GE_POLY_AREA}}"}
:::

:::exercise{id="{{EX_GE_PICK}}"}
:::
