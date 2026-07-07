# 1. RAM Model & Asymptotic Notations

## 1.1 - Why a cost model?

When we say *"this algorithm runs in $O(n \log n)$"*, what exactly are
we counting? Is an addition worth as much as a memory access? What
about multiplying two 1000-digit integers?

We need an **abstract cost model**: precise enough to separate good
algorithms from bad ones, simple enough to be machine-independent.

### The RAM model (Random Access Machine)

- Memory: an infinite array of cells, each holding an integer of at
  most $w$ bits ($w = O(\log n)$ - enough to index the input).
- **Unit-time** elementary operations:
  - cell read / write,
  - arithmetic on two words ($+$, $-$, $\times$, $/$, comparison,
    bitwise operators),
  - conditional branching.
- We count the number of elementary operations as a function of the
  **input size** $n$.

> **Caveat.** The RAM model lies about memory (no caches) and about
> big-number arithmetic. It's a useful abstraction, not a physical
> truth.

### Example: linear search

```python
def linear_search(arr, target):
    for x in arr:           # loop over n elements
        if x == target:     # 1 comparison
            return True     # 1 return
    return False
```

Worst case: `target` is absent. We execute $n$ comparisons and $n$
index increments, i.e. $T(n) = 2n + c$ operations. We write
$T(n) = \Theta(n)$.

---

## 1.2 - Asymptotic notations: formal definitions

Let $f, g : \mathbb{N} \to \mathbb{R}_{\ge 0}$.

### Upper bound: $O$

$$
f(n) = O(g(n)) \iff \exists\, c > 0,\ \exists\, n_0 \in \mathbb{N},\ \forall n \ge n_0,\ f(n) \le c \cdot g(n).
$$

Reads as: *"$f$ grows no faster than $g$, up to a constant factor, from some point on."*

### Lower bound: $\Omega$

$$
f(n) = \Omega(g(n)) \iff \exists\, c > 0,\ \exists\, n_0 \in \mathbb{N},\ \forall n \ge n_0,\ f(n) \ge c \cdot g(n).
$$

### Tight bound: $\Theta$

$$
f(n) = \Theta(g(n)) \iff f(n) = O(g(n))\ \text{and}\ f(n) = \Omega(g(n)).
$$

### Strict domination: $o$ (little-o)

$$
f(n) = o(g(n)) \iff \forall\, c > 0,\ \exists\, n_0,\ \forall n \ge n_0,\ f(n) < c \cdot g(n).
$$

Equivalently, when $g(n) > 0$: $\displaystyle \lim_{n \to \infty} \frac{f(n)}{g(n)} = 0$.

### Strict domination (other side): $\omega$

$$
f(n) = \omega(g(n)) \iff \forall\, c > 0,\ \exists\, n_0,\ \forall n \ge n_0,\ f(n) > c \cdot g(n).
$$

### Summary table

| Notation | Intuitive meaning | Numerical analogue |
|----------|-------------------|--------------------|
| $f = O(g)$ | $f$ upper-bounded by $g$ | $f \le g$ |
| $f = \Omega(g)$ | $f$ lower-bounded by $g$ | $f \ge g$ |
| $f = \Theta(g)$ | same order of magnitude | $f = g$ |
| $f = o(g)$ | $f$ negligible vs $g$ | $f < g$ |
| $f = \omega(g)$ | $f$ strictly dominates $g$ | $f > g$ |

### Visualise the orders of magnitude

:::viz-big-o
:::

Drag the slider: while $n$ stays small, $n^2$ barely dominates
$n \log n$; once $n$ hits a few dozens, the gap explodes. That's
exactly why we bother with $O$ instead of just saying "faster".

### Worked proof: $3n^2 + 5n + 7 = O(n^2)$

Find $c$ and $n_0$ such that $\forall n \ge n_0,\ 3n^2 + 5n + 7 \le c\,n^2$.

For $n \ge 1$: $3n^2 + 5n + 7 \le 3n^2 + 5n^2 + 7n^2 = 15 n^2$.

So $c = 15$ and $n_0 = 1$ work. $\square$

> **Classic pitfall.** $\log_2 n$ and $\log_{10} n$ differ only by a
> constant factor, so $\log_a n = \Theta(\log_b n)$ for any
> $a, b > 1$. We just write $\log n$.

---

## 1.3 - Exercises

:::exercise{id="{{EX_RAM_STD}}"}
:::

:::exercise{id="{{EX_RAM_TWIST}}"}
:::

:::exercise{id="{{EX_RAM_HARD}}"}
:::
