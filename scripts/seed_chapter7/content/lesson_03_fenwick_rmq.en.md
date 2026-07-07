# 3. Fenwick, Sparse Table & Order Statistics

## 3.1 - Intuition

The segment tree is powerful but a bit heavy. For two very common
needs, lighter structures suffice:

- **Fenwick (BIT)**: dynamic prefix sums, in a few lines.
- **Sparse table**: range minimum on a **static** array, in $O(1)$
  per query.

And a flagship application: **order statistics** (the $k$-th smallest)
via a value-indexed Fenwick tree.

---

## 3.2 - Algorithms

### Fenwick tree

A BIT stores partial sums aligned on the low bits. The magic is in
`i & -i`, which isolates the lowest set bit.

```python
def update(bit, n, i, delta):     # i is 1-indexed
    while i <= n:
        bit[i] += delta
        i += i & -i               # jump to the parent block
def prefix(bit, i):               # sum a[1..i]
    s = 0
    while i > 0:
        s += bit[i]
        i -= i & -i               # descend by blocks
    return s
```

The range sum is `prefix(r) - prefix(l-1)`.

### Sparse table (static RMQ)

Precompute `sp[k][i]` = minimum of range $[i, i + 2^k)$. A query
$[l, r]$ is covered by **two** overlapping blocks of length
$2^{\lfloor \log_2(r-l+1) \rfloor}$ - harmlessly, since min is
**idempotent** ($\min(x, x) = x$).

### Order statistics

A **value**-indexed Fenwick counts occurrences. The $k$-th smallest is
found by **binary descent**: walk the bits from high to low, advancing
while the running sum stays $< k$.

---

## 3.3 - Complexity

$$
\begin{aligned}
\text{Fenwick (update / query)} &: \Theta(\log n), \\
\text{sparse table (build)} &: \Theta(n \log n), \\
\text{sparse table (query)} &: \Theta(1), \\
\text{$k$-th (BIT descent)} &: \Theta(\log V).
\end{aligned}
$$

The Fenwick beats the segment tree by a constant factor in memory and
constant; the sparse table is unbeatable per query but freezes the
array.

---

## 3.4 - Common pitfalls

1. **Fenwick is 1-indexed.** The `i & -i` trick assumes indices
   starting at $1$; shift input indices.
2. **Sparse table on mutable data.** It supports **no** updates; any
   modification invalidates the preprocessing.
3. **Idempotence required.** The $O(1)$ sparse table works for min,
   max, gcd - not for sum (the overlap would double-count).
4. **Value domain.** For the $k$-th, size the BIT over the value range
   (or compress it).

---

## 3.5 - Choosing the right structure

Dynamic sums -> Fenwick. Static min, massive queries -> sparse table.
Dynamic min -> segment tree. $k$-th / rank -> value-indexed Fenwick.
Each structure trades generality for speed; reading the constraints
guides the choice.

---

## 3.6 - Exercises

:::exercise{id="{{EX_DS_FENWICK}}"}
:::

:::exercise{id="{{EX_DS_SPARSE_RMQ}}"}
:::

:::exercise{id="{{EX_DS_ORDERSTAT}}"}
:::
