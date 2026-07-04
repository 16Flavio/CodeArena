# 1. Binary Search & Loop Invariants

## 1.1 - Intuition

We look for a value $x$ in a **sorted** array $A[0..n-1]$. Instead
of scanning all $n$ elements, we **cut in half**: if $x$ is smaller
than the middle element, it can only be in the left half;
otherwise in the right half. Each iteration shrinks the search
space by a factor of two - hence $O(\log n)$ comparisons.

Deeper: binary search is a **machine for maintaining an
invariant**. Each iteration preserves a property over the
remaining interval and tightens the bracket until only one
candidate remains.

---

## 1.2 - Algorithm & invariant

We look for the first index $i$ with $A[i] \ge x$ (C++'s
`lower_bound`). It's the most useful primitive: equality search,
upper bound, and insertion all derive from it.

```python
def lower_bound(A, x):
    lo, hi = 0, len(A)        # HALF-OPEN interval [lo, hi)
    while lo < hi:
        mid = (lo + hi) // 2
        if A[mid] < x:
            lo = mid + 1
        else:
            hi = mid
    return lo
```

### Invariant

On entry to the `while`, we maintain:

$$
(\forall j < lo)\ A[j] < x \qquad \text{and} \qquad
(\forall j \ge hi)\ A[j] \ge x.
$$

- **Initialization**: $lo = 0$ and $hi = n$, both quantifiers are
  vacuous - true.
- **Maintenance**: in the next iteration, either $A[\text{mid}] < x$
  and we push $lo = \text{mid} + 1$ (every position $\le \text{mid}$
  is $< x$), or $A[\text{mid}] \ge x$ and we set
  $hi = \text{mid}$ (every position $\ge \text{mid}$ is $\ge x$).
- **Termination**: `hi - lo` strictly decreases each iteration;
  as a positive integer, the loop ends.
- **Correctness on exit**: $lo = hi$, so $A[j] < x$ for $j < lo$
  and $A[j] \ge x$ for $j \ge lo$ - that's the definition of
  `lower_bound`. $\square$

---

## 1.3 - Complexity

The interval $[lo, hi)$ holds at most $n$ elements on entry and
loses **at least half** per round: if it has size $k$,
$\text{mid} - lo \le k/2$ and $hi - (\text{mid}+1) \le k/2$. After
$T$ rounds size $\le n / 2^T$, so $T \le \log_2 n$.

$$\boxed{\;T(n) = \Theta(\log n)\;}$$

---

## 1.4 - Classic pitfalls

1. **Closed vs half-open interval.** With `hi = n - 1` (closed),
   you must write `while lo <= hi` and `hi = mid - 1`, otherwise
   you loop. Half-open is more regular - pick ONE convention and
   stick with it.
2. **`mid = (lo + hi) // 2`.** No risk in Python; on C++/Java
   `int`, write `lo + (hi - lo) / 2` to avoid overflow.
3. **Equality test after `lower_bound`.** The element is present
   iff `lo < n && A[lo] == x`. Test *both* conditions - skipping
   the first walks past the array when $x$ is strictly greater
   than every element.
4. **Unsorted array.** Binary search says nothing useful on an
   unsorted array: monotonicity is *the* assumption. Always sort
   first, or prove monotonicity when binary-searching on the
   answer (cf. lesson 2).

---

## 1.5 - Useful variants

- **`upper_bound(A, x)`**: first index $i$ with $A[i] > x$.
  Replace `<` with `<=` in the middle test.
- **First / last occurrence** of a key $x$: first is
  `lower_bound(A, x)`; last is `upper_bound(A, x) - 1`.
- **Counting** occurrences: `upper_bound(A, x) - lower_bound(A, x)`.
- **Discrete binary search on integers** (no array): find the
  largest $k$ with $P(k)$ true, where $P$ is monotone decreasing.
  Foundation of lesson 2.

---

## 1.6 - Exercises

:::exercise{id="{{EX_SE_LOWERBOUND}}"}
:::

:::exercise{id="{{EX_SE_FIRSTOCC}}"}
:::

:::exercise{id="{{EX_SE_ISQRT}}"}
:::
