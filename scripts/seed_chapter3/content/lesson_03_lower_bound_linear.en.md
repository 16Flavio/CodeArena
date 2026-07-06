# 3. The $\Omega(n \log n)$ Lower Bound & Linear Sorts

## 3.1 - Why look for a lower bound?

$\Theta(n \log n)$ sorts pile up: mergesort, heapsort, quicksort
on average. Natural question: **can we do better?**

Answer: **no, not with comparisons alone**. Any algorithm using only
comparisons $a_i < a_j$ has $\Omega(n \log n)$ cost in the worst
case. The proof goes through **decision trees**.

---

## 3.2 - The decision tree

Any deterministic sorting algorithm using only comparisons can be
seen as a **binary decision tree**:

- each internal node is a comparison `A[i] < A[j]`;
- the two children are the `true` / `false` outcomes;
- each leaf carries a **permutation** $\sigma$ of the input - the
  output produced when that path is taken.

**Key observation.** For correctness, every one of the $n!$ possible
input permutations of distinct elements must reach some leaf. So
the tree has **at least $n!$ leaves**.

### Theorem

**Theorem.** Any decision tree sorting $n$ distinct elements has
height $h \ge \log_2(n!)$.

*Proof.* A binary tree of height $h$ has at most $2^h$ leaves. Since
we need at least $n!$: $2^h \ge n!$, so $h \ge \log_2(n!)$. $\square$

### Conclusion: $\Omega(n \log n)$

We want an explicit bound on $\log_2(n!)$. Stirling:

$$n! \ge \left(\frac{n}{e}\right)^n,$$

so

$$\log_2(n!) \ge n \log_2(n/e) = n \log_2 n - n \log_2 e = \Omega(n \log n).$$

→ **Every comparison-based sorting algorithm performs $\Omega(n
\log n)$ comparisons in the worst case.** Mergesort and heapsort are
**asymptotically optimal** in this model. $\square$

> **Direct consequence.** To go below, one must **leave the
> comparison model** - exploit a known structure of the keys. That's
> what linear sorts do.

---

## 3.3 - Counting sort

### Assumption

Keys are **integers** in $[0, k]$, with $k$ not too large vs $n$.

### Algorithm

```python
def counting_sort(A, k):
    cnt = [0] * (k + 1)
    for x in A: cnt[x] += 1
    out = []
    for v in range(k + 1):
        out.extend([v] * cnt[v])
    return out
```

### Complexity

$\Theta(n + k)$ - linear if $k = O(n)$.

### Stability (general version)

The version above loses stability when keys carry payloads (e.g.
`(key, payload)`). The **stable** version uses prefix sums:

```python
def counting_sort_stable(A, k):
    cnt = [0] * (k + 1)
    for x in A: cnt[x] += 1
    for i in range(1, k + 1): cnt[i] += cnt[i - 1]
    out = [None] * len(A)
    for x in reversed(A):
        cnt[x] -= 1
        out[cnt[x]] = x
    return out
```

The **reverse** iteration combined with decrementing `cnt`
guarantees that two equal-keyed elements keep their input order.

---

## 3.4 - Radix sort (LSD)

### Assumption

Keys are **$d$-digit integers** (or fixed-length strings). Pick a
base $b$ (typically $b = 10$ or $b = 256$).

### Algorithm: LSD

Sort digit by digit, **from least to most significant**, using a
**stable** counting sort each pass:

```python
def radix_sort(A):
    if not A: return []
    mx = max(A); exp = 1
    while mx // exp > 0:
        # counting sort on digit (x // exp) % 10
        cnt = [0] * 10
        for x in A: cnt[(x // exp) % 10] += 1
        for i in range(1, 10): cnt[i] += cnt[i - 1]
        out = [0] * len(A)
        for x in reversed(A):
            d = (x // exp) % 10
            cnt[d] -= 1
            out[cnt[d]] = x
        A = out
        exp *= 10
    return A
```

### Correctness (why LSD works)

**Invariant.** After processing digit $i$ (least to most
significant), $A$ is sorted by the **$i$ least-significant digits**.

*Step.* The pass on digit $i+1$ uses a **stable** counting sort:
two keys with the same $(i+1)$-th digit keep the relative order
established by the previous pass - i.e. the global order on the
$i+1$ low digits. $\square$

### Complexity

$\Theta(d \cdot (n + b))$ - linear in $n$ when $d$ and $b$ are
constants (32-bit integers byte by byte: $d = 4$, $b = 256$).

---

## 3.5 - Bucket sort

### Assumption

Keys are **uniformly distributed reals** in $[0, 1]$.

### Algorithm

1. Create $n$ buckets for the intervals $[i/n, (i+1)/n)$.
2. Place each key in its bucket ($\Theta(n)$ total).
3. Sort each bucket (insertion sort suffices).
4. Concatenate.

### Expected complexity

Under the uniform assumption, expected bucket size is $1$.
Insertion sort on a bucket of size $m$ costs $\Theta(m^2)$. Summing
$\mathbb{E}[m^2]$ across buckets gives $\Theta(n)$ - classic
calculation we skip here.

→ **$\Theta(n)$ in expectation** when the uniform assumption holds.
Worst case: $\Theta(n^2)$ if all elements land in the same bucket.

---

## 3.6 - Summary

| Algo | Assumption | Worst case | Stable |
|------|------------|-----------|--------|
| Comparison (general) | none | $\Omega(n \log n)$ by lower bound | depends |
| Counting sort | keys $\in [0, k]$, $k = O(n)$ | $\Theta(n + k)$ | yes (stable variant) |
| Radix sort | $d$-digit keys, base $b$ | $\Theta(d(n + b))$ | yes |
| Bucket sort | u.d. keys in $[0,1]$ | $\Theta(n^2)$ ($\Theta(n)$ expected) | yes |

---

## 3.7 - Exercises

:::exercise{id="{{EX_SO_COUNTING}}"}
:::

:::exercise{id="{{EX_SO_RADIX}}"}
:::

:::exercise{id="{{EX_SO_RADIX_STR}}"}
:::
