# 4. Sliding window

## 4.1 - Intuition

A **sliding window** is a special case of two-pointers where the
zone $[i, j]$ represents a **contiguous subsequence** of a stream
or array, and we maintain at each step a *statistic* about that
window (sum, max, frequency dictionary). We iterate $j$ from left
to right and **advance $i$** as soon as the window becomes
invalid.

Cost: $O(n)$ amortized, because $i$ and $j$ can only grow. Memory
cost: the window's statistic, often $O(\Sigma)$ where $\Sigma$ is
the alphabet size.

---

## 4.2 - **Fixed-size** window of length $k$

> Largest sum over all subarrays of length $k$.

```python
def max_window_sum(A, k):
    s = sum(A[:k])
    best = s
    for j in range(k, len(A)):
        s += A[j] - A[j - k]    # A[j] enters, A[j-k] leaves
        best = max(best, s)
    return best
```

The trick: keep the statistic in $O(1)$ per shift instead of
recomputing in $O(k)$. General pattern: **add** what enters,
**remove** what leaves.

---

## 4.3 - **Variable-size** window: the pattern

This is the most powerful case. We want the longest (or
shortest) window satisfying a predicate $P$ "monotone under
contraction":

$$P(i, j) = \text{true} \implies P(i+1, j) = \text{true}.$$

That is, **shrinking** a valid window keeps it valid.
Symmetrically for "min" variants: growing an invalid window keeps
it invalid.

### Pattern: longest valid subarray

```python
def longest_valid(A, predicate):
    i = 0
    best = 0
    state = init()                        # window statistic
    for j in range(len(A)):
        add(state, A[j])                  # A[j] enters
        while not predicate(state):       # restore validity
            remove(state, A[i])
            i += 1
        best = max(best, j - i + 1)
    return best
```

**Why $O(n)$?** $i$ never goes back, so total increments are
$\le n$. The inner `while` runs at most $n$ times across the
whole algorithm - it **doesn't increase** the total cost.

---

## 4.4 - Application: longest substring without repetition

> Given a string $s$, find the length of the longest substring
> with **no repeated character**.

Statistic: a dictionary `last[c] = last index of c`. The predicate
"window valid" is *no repetition*.

```python
def longest_unique(s):
    last = {}
    i = 0
    best = 0
    for j, c in enumerate(s):
        if c in last and last[c] >= i:
            i = last[c] + 1     # direct jump, no while !
        last[c] = j
        best = max(best, j - i + 1)
    return best
```

Optimization tip: instead of looping with `while`, jump $i$
directly to `last[c] + 1`. **Equivalent** in complexity (still
$O(n)$) but a better constant.

---

## 4.5 - Application: subarray with sum $\ge S$

That's lesson 3's example - already seen. The boundary between
"two-pointer" and "sliding window" is fuzzy: same idea, different
emphasis (two indices vs an aggregated statistic).

---

## 4.6 - Pitfalls

1. **Non-monotone predicate**: if shrinking a valid window can
   make it invalid, the pattern fails.
   *Counter-example*: "longest window whose sum equals exactly
   $S$" with negative values - adding can swing the sum either
   way.
2. **Statistic too expensive to update**: if `add` or `remove`
   cost $O(\log n)$ (insertion in a sorted set, …), the total
   cost climbs to $O(n \log n)$. Still fine, but no longer *pure*
   sliding window.
3. **Hidden inner loops**: in the pattern, the inner `while` must
   *amortize* to $O(n)$ total. Doing non-trivial work per
   iteration kills the amortization.

---

## 4.7 - Exercises

:::exercise{id="{{EX_SE_FIXEDSUM}}"}
:::

:::exercise{id="{{EX_SE_LONGEST_UNIQUE}}"}
:::

:::exercise{id="{{EX_SE_K_DISTINCT}}"}
:::
