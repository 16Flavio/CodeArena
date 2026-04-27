# 1. Insertion Sort & Merge Sort

## 1.1 — Insertion sort: like a hand of cards

Lining up cards in your hand, you **insert** each new card into its
slot in the already-sorted prefix. That's exactly insertion sort.

```python
def insertion_sort(A):
    for i in range(1, len(A)):
        key = A[i]
        j = i - 1
        while j >= 0 and A[j] > key:
            A[j + 1] = A[j]
            j -= 1
        A[j + 1] = key
    return A
```

:::viz-sort{algo="insertion" data="[5,2,8,1,9,3,7,4]"}
:::

### Correctness (loop invariant)

**Invariant.** At the start of iteration $i$ of the outer loop,
$A[0..i-1]$ contains the original elements of that range, **sorted
in ascending order**.

- *Init.* Before $i = 1$, $A[0..0]$ is trivially sorted.
- *Step.* The inner loop shifts every element of $A[0..i-1]$ that is
  strictly greater than `key`, then inserts `key`. The resulting
  $A[0..i]$ is still sorted.
- *Termination.* After $i = n$, $A[0..n-1] = A$ is sorted.

$\square$

### Complexity

- Worst case (reversed array): $T(n) = \sum_{i=1}^{n-1} i = \Theta(n^2)$.
- Best case (already sorted): $\Theta(n)$ — the inner loop exits
  immediately.
- Expected over a random permutation: $\Theta(n^2)$.

> **Why teach it?** In practice, $n \log n$ algorithms switch to
> insertion sort *internally* for sub-arrays of size $\le 16$: its
> constants are tiny, beating mergesort/quicksort on small inputs.

---

## 1.2 — Merge sort: divide and conquer

### Idea

1. **Divide** the array in half.
2. **Sort** each half recursively.
3. **Merge** the two sorted halves into one sorted array.

The key operation is **merge**: given two sorted arrays $L$ and $R$,
walk two indices and emit at each step the smaller of the two fronts.

```python
def merge(L, R):
    out = []
    i = j = 0
    while i < len(L) and j < len(R):
        if L[i] <= R[j]:
            out.append(L[i]); i += 1
        else:
            out.append(R[j]); j += 1
    out.extend(L[i:])
    out.extend(R[j:])
    return out

def merge_sort(A):
    if len(A) <= 1:
        return A
    mid = len(A) // 2
    return merge(merge_sort(A[:mid]), merge_sort(A[mid:]))
```

### Merge correctness

**Invariant.** After $k$ iterations, `out` contains the $k$ smallest
elements of $L \cup R$, in ascending order.

*Step.* Each iteration emits $\min(L[i], R[j])$. Since $L$ and $R$
are sorted, their fronts are their respective minima; the min of the
two fronts is the global min not yet emitted. $\square$

### Full proof: $T(n) = \Theta(n \log n)$

Recurrence:

$$T(n) = 2\,T(n/2) + cn,\qquad T(1) = c'.$$

**Approach 1 — Master Theorem.** $a = 2$, $b = 2$, $\alpha = \log_b a = 1$,
$f(n) = cn = \Theta(n^\alpha)$: this is **case 2** of the Master
Theorem (cf. ch. 1), so $T(n) = \Theta(n \log n)$.

**Approach 2 — Recursion tree (by hand).**

- Level 0: 1 node of cost $cn$.
- Level $k$: $2^k$ nodes, each of cost $c \cdot n / 2^k$.
- Cost per level: $2^k \cdot (cn/2^k) = cn$ — **constant** per level.
- Depth: $\log_2 n$ levels down to leaves.

$$T(n) = \sum_{k=0}^{\log_2 n} cn = cn\,(\log_2 n + 1) = \Theta(n \log n).$$

$\square$

### Stable? Memory? In practice?

- **Stable**: yes (the merge preserves relative order on equal keys
  — the `<=` in the test).
- **Memory**: $\Theta(n)$ extra (the `out` array).
- **Strong**: the $n \log n$ bound is **guaranteed** on any input —
  no pathological worst case like quicksort.

---

## 1.3 — Exercises

:::exercise{id="{{EX_SO_MERGE2}}"}
:::

:::exercise{id="{{EX_SO_INVERSIONS}}"}
:::

:::exercise{id="{{EX_SO_KMERGE}}"}
:::
