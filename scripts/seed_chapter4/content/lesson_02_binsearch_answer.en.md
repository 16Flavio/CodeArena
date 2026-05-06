# 2. Binary Search on the Reals and on the Answer

Lesson 1 binary-searched a **sorted array**. The real engine was
not the array — it was **monotonicity**. So we can binary-search
whenever we have a monotone function, real or discrete, sometimes
with no array at all.

---

## 2.1 — On the reals: bisection

Let $f : [a, b] \to \mathbb{R}$ be **continuous** with $f(a) < 0 <
f(b)$. The intermediate value theorem guarantees a root $r \in [a,
b]$. Bisection:

```python
def bisect_real(f, lo, hi, eps=1e-9):
    # Pre-condition: f(lo) < 0 < f(hi).
    while hi - lo > eps:
        mid = (lo + hi) / 2
        if f(mid) < 0: lo = mid
        else:          hi = mid
    return (lo + hi) / 2
```

### How many iterations?

The interval halves per round. To reach precision $\varepsilon$
from initial width $L$, need $T = \lceil \log_2(L/\varepsilon)
\rceil$ rounds. **L = 1, ε = 1e-9 → 30 rounds suffice.** In
practice fix a constant (60-100) covering the worst gap, instead
of the test `while hi - lo > eps` which suffers floating-point
artefacts.

```python
for _ in range(100):
    mid = (lo + hi) / 2
    if f(mid) < 0: lo = mid
    else:          hi = mid
```

### Pitfalls

- **Monotonicity required**: if $f$ changes sign more than once on
  $[a, b]$, bisection has no reason to converge to *your* root.
  Plot, reason, or shrink the starting interval.
- **Test the output** by injection: substitute the found root into
  the original problem and check the error is $\le \varepsilon$.
- **Never** compare to zero with `==` after a floating computation.

---

## 2.2 — Binary search on the answer

The single most rewarding move in competitive programming: instead
of looking for $x$ in an array, **guess the answer's value** and
ask the problem "is this answer achievable?"

### Prerequisite (verify explicitly)

Let $\text{feasible}(k)$ be a boolean predicate. To binary-search
we need:

$$
\text{feasible}(k) = \text{true} \implies
\text{feasible}(k') = \text{true} \quad \forall\, k' \le k
$$

(or the increasing version: feasible above some threshold). This
is **monotonicity of the predicate**. The boundary between `true`
and `false` is unique — and that's what we look for.

### Pattern

```python
def search_max(lo, hi, feasible):
    # Find the largest k in [lo, hi] with feasible(k).
    # Pre: feasible(lo); not feasible(hi+1).
    while lo < hi:
        mid = (lo + hi + 1) // 2     # +1 to avoid an infinite loop
        if feasible(mid): lo = mid
        else:             hi = mid - 1
    return lo
```

> **The `+1` rounding.** Without `+1`, when `hi = lo + 1` and
> `feasible(mid)`, we set `lo = mid = lo` — infinite loop. With
> `+1`, `mid = lo + 1 = hi` and we make progress.

---

## 2.3 — Example: Aggressive Cows

> $n$ stalls at positions $x_1 < \dots < x_n$, place $k$ cows so
> as to **maximize the minimum distance** between two consecutive
> cows.

**Is answer $d$ feasible?** Place a cow at $x_1$, greedily take
the next stall at distance $\ge d$; feasible iff we place at
least $k$. The check is $O(n)$ and **monotone decreasing** in $d$
(larger $d$ → harder to fit).

**Target**: largest feasible $d$. Bounds: $d \in [0, x_n - x_1]$.
Cost $O(n \log(x_n - x_1))$.

```python
def feasible(d, X, k):
    last, count = X[0], 1
    for x in X[1:]:
        if x - last >= d:
            last = x; count += 1
            if count >= k: return True
    return count >= k
```

The trick **isn't** the greedy check — it's the reformulation:
*solving* the optimization version is hard, *checking* a value is
easy.

---

## 2.4 — When to use it

Spot these signals in a statement:

- "**maximize the minimum**" or "**minimize the maximum**" →
  almost always binary-search on the answer.
- The direct problem is hard, but "is this parameter big / small
  enough?" is easy to check in linear time.
- The search space is bounded by problem data (max coordinate,
  total sum, …).

Pattern is *everywhere* (USACO, ICPC, Codeforces). Mastering the
reformulation makes a whole class of problems trivial.

---

## 2.5 — Exercises

:::exercise{id="{{EX_SE_AGGRCOWS}}"}
:::

:::exercise{id="{{EX_SE_PAINTERS}}"}
:::

:::exercise{id="{{EX_SE_SQRT_REAL}}"}
:::
