# 3. Two pointers

## 3.1 — The pattern

We maintain two indices $i < j$ (or $i$, $j$ at the array's
endpoints) and move them **monotonically**: they **never** step
back. That monotonicity is precisely what turns an $O(n^2)$
algorithm into $O(n)$.

The key insight: at each iteration we **definitively eliminate**
one position. If the algorithm performs at most $2n$ pointer
moves total, the cost is $O(n)$, regardless of what the inner
logic looks like.

---

## 3.2 — Variant 1: opposite ends (sorted array)

> Given a **sorted** array $A$ and target $T$, do indices
> $i \neq j$ exist with $A[i] + A[j] = T$?

```python
def two_sum_sorted(A, T):
    i, j = 0, len(A) - 1
    while i < j:
        s = A[i] + A[j]
        if s == T:   return (i, j)
        elif s < T:  i += 1   # sum too small → bump A[i]
        else:        j -= 1   # sum too large → drop A[j]
    return None
```

### Why is it correct?

**Invariant.** If a witness pair $(i^*, j^*)$ exists, then
$i \le i^* \le j^* \le j$ throughout the loop.

- If $A[i] + A[j] < T$, then $\forall k \le j,\ A[i] + A[k] \le
  A[i] + A[j] < T$. No pair using $i$ can hit $T$ → eliminate
  $i$, i.e. $i \mathrel{+}= 1$.
- Symmetric for $A[i] + A[j] > T$.
- When $i = j$, the invariant forces the pair to be lost → no
  solution.

Each iteration either returns, or **shrinks the interval by 1**.
At most $n$ iterations → **$O(n)$ after sorting**.

---

## 3.3 — Variant 2: pointers in the same direction

> Given an array of **positive** integers $A$ and target $S$, find
> the **smallest** contiguous subarray whose sum $\ge S$.

```python
def smallest_window_geq(A, S):
    i, total, best = 0, 0, len(A) + 1
    for j in range(len(A)):
        total += A[j]
        while total >= S:           # contract while we can
            best = min(best, j - i + 1)
            total -= A[i]
            i += 1
    return best if best <= len(A) else 0
```

**Invariant.** On entry to the `while`, `total = A[i] + A[i+1] +
… + A[j]` and `total < S` ⟹ we must grow the window on the
right. While `total >= S` we contract: the smallest window ending
at $j$ is found on exit from the `while`.

**Amortized cost.** $i$ never goes back; it is incremented at
most $n$ times across the whole run. $j$ as well. Total ops
$\le 2n = O(n)$.

> ⚠️ The trick collapses the moment **negative** values are
> allowed: the sum is no longer monotone in window growth. That
> case needs different machinery (sorted prefix sums, monotone
> deque, etc.).

---

## 3.4 — Variant 3: 3-sum

> Find all triples $(a, b, c)$ with $a \le b \le c$,
> $a + b + c = 0$, no duplicates.

**Idea.** Sort, fix $a$ by outer loop ($O(n)$ choices), look for
$b + c = -a$ in the right subarray with two-pointer in $O(n)$.
Total: **$O(n^2)$**, beating brute force $O(n^3)$.

```python
def three_sum(A):
    A = sorted(A)
    out = []
    n = len(A)
    for i in range(n - 2):
        if i > 0 and A[i] == A[i-1]: continue   # dedupe a
        T = -A[i]
        l, r = i + 1, n - 1
        while l < r:
            s = A[l] + A[r]
            if s == T:
                out.append((A[i], A[l], A[r]))
                l += 1; r -= 1
                while l < r and A[l] == A[l-1]: l += 1
                while l < r and A[r] == A[r+1]: r -= 1
            elif s < T: l += 1
            else:       r -= 1
    return out
```

Note: the `continue` after sorting kills duplicates on the first
element; the two inner `while`s kill them on the others.

---

## 3.5 — When to use it

- The array is sorted (or can be sorted without breaking semantics).
- The observed quantity is **monotone** under one of the pointers
  (growing sum, growing distance, etc.).
- The naive algorithm is $O(n^2)$ and the answer is found by
  progressive exclusion of positions.

Two pointers is the *temporal* expression of the same principle as
binary search: **never** walk back on information already gained
through monotonicity.

---

## 3.6 — Exercises

:::exercise{id="{{EX_SE_2SUM}}"}
:::

:::exercise{id="{{EX_SE_3SUM}}"}
:::

:::exercise{id="{{EX_SE_REMOVE_DUPS}}"}
:::
