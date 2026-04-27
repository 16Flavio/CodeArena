# 2. Quicksort & Heapsort

## 2.1 — Quicksort: divide **around a pivot**

Quicksort is another *divide and conquer*, but unlike mergesort
**all the magic is in the split**; the recombination is trivial.

### Algorithm

1. Pick a **pivot** (an array element).
2. **Partition** the array around the pivot: left $\le$ pivot,
   right $>$ pivot.
3. Recurse on both parts.

### Lomuto partition (the simplest)

Pivot = last element. Walk with two indices, swap.

```python
def lomuto_partition(A, lo, hi):
    pivot = A[hi]
    i = lo
    for j in range(lo, hi):
        if A[j] <= pivot:
            A[i], A[j] = A[j], A[i]
            i += 1
    A[i], A[hi] = A[hi], A[i]
    return i  # pivot's new index

def quicksort(A, lo=0, hi=None):
    if hi is None: hi = len(A) - 1
    if lo < hi:
        p = lomuto_partition(A, lo, hi)
        quicksort(A, lo, p - 1)
        quicksort(A, p + 1, hi)
```

:::viz-partition{data="3,7,1,8,4,2,5"}
:::

`step` advances **one comparison**; `i` (boundary between $\le$ pivot
and $>$ pivot) and `j` (the scanner) are shown below the cells. When
`j` reaches the end, the red pivot is swapped to position `i`.

### Worst case: $\Theta(n^2)$

If every recursive pivot is the smallest (or largest) element — for
instance an **already sorted** array with pivot = last — we get a
$n-1, 0$ split. The recurrence

$$T(n) = T(n-1) + \Theta(n)$$

gives $T(n) = \Theta(n^2)$.

**Bird's-eye view** — the animation below runs a **full** quicksort:
you see red pivots being placed one by one, recursions stacking up,
and the call-stack depth growing. Try loading `1,2,3,4,5,6,7,8`
(already sorted) to visualise the worst case — the stack walks down
like a staircase.

:::viz-quicksort{data="8,3,5,1,9,2,7,4,6"}
:::

### Average case: $\Theta(n \log n)$ — expectation proof

Pick the pivot **uniformly at random** in $A[lo..hi]$. For distinct
keys $z_1 < z_2 < \dots < z_n$, let $X_{ij}$ be the indicator
variable equal to $1$ iff $z_i$ and $z_j$ are compared during the
run.

Total cost (in comparisons) is $X = \sum_{i<j} X_{ij}$, so

$$\mathbb{E}[X] = \sum_{i<j} \Pr[z_i \text{ and } z_j \text{ compared}].$$

**Lemma.** $z_i$ and $z_j$ are compared iff the **first pivot
chosen from** $\{z_i, z_{i+1}, \dots, z_j\}$ is $z_i$ or $z_j$. (If
it's another element, $z_i$ and $z_j$ end up in disjoint subarrays
and never meet again.)

Since the $j - i + 1$ elements are equally likely to be the first
pivot, the probability is $\frac{2}{j - i + 1}$.

$$\mathbb{E}[X] = \sum_{i<j} \frac{2}{j - i + 1} = 2 \sum_{i=1}^{n-1} \sum_{k=2}^{n - i + 1} \frac{1}{k} \le 2 n \sum_{k=2}^{n} \frac{1}{k} = 2n\,(H_n - 1).$$

Since $H_n = \Theta(\log n)$ (cf. ch. 1), $\mathbb{E}[X] = \Theta(n \log n)$.

$\square$

> **The mantra.** Random-pivot quicksort is $O(n \log n)$ **in
> expectation, on every input**. The $\Theta(n^2)$ worst case
> exists, but its probability is exponentially small.

### Pivot strategies in practice

| Strategy | Worst | Avg | Cost |
|----------|-------|-----|------|
| First / last element | $n^2$ (sorted input) | $n \log n$ | free |
| Random element | $n^2$ (prob $\to 0$) | $n \log n$ | RNG |
| Median of 3 (first, middle, last) | $n^2$ rare | $n \log n$ | 2 cmp |
| Median of medians | $n \log n$ deterministic (lesson 4) | $n \log n$ | high constant |

---

## 2.2 — Heapsort (recap)

Heapsort was covered in detail in chapter 2 (lesson "Binary heaps &
heapsort"). Just the summary here, for context.

| Algorithm | Worst | Average | Memory | Stable |
|-----------|-------|---------|--------|--------|
| Insertion | $n^2$ | $n^2$ | $O(1)$ | yes |
| Mergesort | $n \log n$ | $n \log n$ | $O(n)$ | yes |
| Quicksort | $n^2$ | $n \log n$ | $O(\log n)$ | no |
| Heapsort | $n \log n$ | $n \log n$ | $O(1)$ | no |

**Right tool for the right job.**

- Tight memory? **Heapsort** (in-place, $n \log n$ guaranteed).
- Stability needed? **Mergesort**.
- Cache + tiny constants? **Quicksort** (wins on modern CPUs in
  practice).
- Small arrays? **Insertion sort**.

---

## 2.3 — Exercises

:::exercise{id="{{EX_SO_PARTITION}}"}
:::

:::exercise{id="{{EX_SO_DUTCH}}"}
:::

:::exercise{id="{{EX_SO_RUNMEDIAN}}"}
:::
