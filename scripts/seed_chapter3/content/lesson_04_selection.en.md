# 4. Selection: Quickselect & Median of Medians

## 4.1 - The selection problem

**Problem**: given an array $A$ of $n$ elements and an integer
$k \in [1, n]$, find the **$k$-th smallest** element ($k$-th order
statistic).

Notable special cases:
- $k = 1$ → minimum.
- $k = n$ → maximum.
- $k = \lceil n/2 \rceil$ → **median**.

### Cost?

- *Trivial*: sort then index → $\Theta(n \log n)$.
- *With a heap*: extract-min $k$ times → $\Theta(n + k \log n)$.
- *Quickselect*: $\Theta(n)$ **expected**.
- *Median of medians*: $\Theta(n)$ **deterministic**.

One of the rare occasions to beat $n \log n$ for a non-trivial
problem.

---

## 4.2 - Quickselect

### Idea

Like quicksort, but **only recurse into the side containing the
$k$-th element**. The partition splits $A$ into left $\le$ pivot,
right $>$ pivot, at position $p$:

- If $k - 1 = p$: pivot is the answer.
- If $k - 1 < p$: $k$-th is on the left; recurse left.
- If $k - 1 > p$: $k$-th is on the right; recurse right with the
  same $k$.

### Code

```python
import random

def quickselect(A, k):
    """k-th smallest (1-indexed) of A - destroys A."""
    lo, hi = 0, len(A) - 1
    while lo <= hi:
        # Random pivot to break adversarial worst case.
        p = random.randint(lo, hi)
        A[p], A[hi] = A[hi], A[p]
        pivot = A[hi]
        i = lo
        for j in range(lo, hi):
            if A[j] <= pivot:
                A[i], A[j] = A[j], A[i]; i += 1
        A[i], A[hi] = A[hi], A[i]
        if i == k - 1: return A[i]
        if i  > k - 1: hi = i - 1
        else:           lo = i + 1
```

### Expected complexity: $\Theta(n)$

Let $T(n)$ be the expected number of comparisons on a size-$n$
array. With a uniform pivot, the recursive sub-array has size
uniform in $\{0, 1, \dots, n-1\}$. For the worst $k$ we recurse
into the larger half, and each size $i \in [n/2, n-1]$ arises from
two pivot ranks:

$$
T(n) \le n + \frac{2}{n} \sum_{i=n/2}^{n-1} T(i).
$$

By induction, $T(n) \le 4n$. **Trick**: with $T(i) \le 4i$,

$$
T(n) \le n + \frac{2}{n} \sum_{i=n/2}^{n-1} 4i = n + \frac{8}{n} \sum_{i=n/2}^{n-1} i,
$$

and $\sum_{i=n/2}^{n-1} i \le \frac{3n^2}{8}$ ($n/2$ terms, each
$< n$, average about $3n/4$), so

$$
T(n) \le n + \frac{8}{n} \cdot \frac{3n^2}{8} = n + 3n = 4n. \square
$$

### Worst case: $\Theta(n^2)$

Like quicksort: if every pivot is the extreme of its sub-array, we
shrink $n$ by one each time. Exponentially small probability with
random pivot, but possible.

---

## 4.3 - Median of medians: $\Theta(n)$ **deterministic**

The Blum-Floyd-Pratt-Rivest-Tarjan algorithm (1973) reaches
$\Theta(n)$ worst case by picking a pivot **guaranteed not to be
too extreme**.

### Algorithm

```python
def select(A, k):
    """k-th smallest (1-indexed) of A. Mutates A."""
    if len(A) <= 5:
        return sorted(A)[k - 1]

    # 1. Split A into groups of 5, take the median of each.
    groups = [A[i:i+5] for i in range(0, len(A), 5)]
    medians = [sorted(g)[len(g) // 2] for g in groups]

    # 2. Recursive median of medians - that's our pivot.
    pivot = select(medians, (len(medians) + 1) // 2)

    # 3. Partition around pivot.
    L = [x for x in A if x < pivot]
    M = [x for x in A if x == pivot]
    R = [x for x in A if x > pivot]

    if k <= len(L):                    return select(L, k)
    if k <= len(L) + len(M):           return pivot
    return select(R, k - len(L) - len(M))
```

### Why it works

**Lemma.** The MoM pivot is greater than at least $\frac{3n}{10}$
elements and smaller than at least $\frac{3n}{10}$ elements.

*Proof.* There are $\lceil n / 5 \rceil$ groups of 5. The median of
medians is greater than half the medians, i.e. $\lceil n/10 \rceil$
medians. Each of those medians is itself greater than the 2
smallest elements of its group. Total:

$$
3 \cdot \left\lceil \frac{n}{10} \right\rceil \ge \frac{3n}{10}
$$

elements $\le$ pivot. Symmetric for $\ge$. $\square$

### Recurrence

Let $T(n)$ be the cost.

- Step 1 (group medians) costs $\Theta(n)$: sorting 5 elements is
  $O(1)$.
- Step 2 (recursive median on $n/5$ medians) costs $T(n/5)$.
- Step 3 (partition + recursion on the large half): large half has
  at most $\frac{7n}{10}$ elements (by the lemma), so $T(7n/10)$.

$$
T(n) \le T(n/5) + T(7n/10) + cn.
$$

Since $\frac{1}{5} + \frac{7}{10} = \frac{9}{10} < 1$, the
recurrence resolves to $T(n) = \Theta(n)$ by induction (or Akra-
Bazzi with $p = 1$ and the integral dominated by $n$). $\square$

### Why groups of 5?

The smallest odd group size that makes $\frac{1}{k} +
\frac{3k-1}{4k} < 1$: groups of 3 → coefficients $1/3 + 2/3 = 1$,
no contraction; groups of 5 → $1/5 + 14/20 = 9/10$, it works.
(And 5 is smaller than 7, so smaller constants.)

> **In practice**, MoM is rarely used: high constants and random
> quickselect is *more than* enough. But theoretically, it kills the
> $n \log n$ bound for selection **without randomness**.

---

## 4.4 - Summary

| Algo | Worst | Average | Memory | Random? |
|------|-------|---------|--------|---------|
| Sort then index | $n \log n$ | $n \log n$ | $O(1)$ or $O(n)$ | no |
| Heap (extract $k$ mins) | $n + k \log n$ | idem | $O(1)$ | no |
| Quickselect (random pivot) | $n^2$ | $\Theta(n)$ | $O(1)$ | yes |
| Median of medians | $\Theta(n)$ | $\Theta(n)$ | $O(n)$ | no |

---

## 4.5 - Exercises

:::exercise{id="{{EX_SO_SELECT}}"}
:::

:::exercise{id="{{EX_SO_MINMAX}}"}
:::

:::exercise{id="{{EX_SO_TOPK}}"}
:::
