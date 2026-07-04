# 4. Binary Heaps & Heapsort

## 4.1 - The idea: an almost-complete tree in an array

A **binary heap** (max-heap) is a binary tree satisfying:

1. **Shape**: it is **almost complete** - every depth is filled
   except the last, which fills left-to-right.
2. **Order**: for every node $v$, $v.k \ge$ all keys in its
   descendants. (Min-heap: $\le$.)

Direct consequence: **the root is the maximum** of the collection.

### Array representation

Thanks to the almost-complete shape, we store the heap in an array
$A[0..n[$ pointer-free:

- root at $A[0]$,
- children of $A[i]$ are $A[2i+1]$ and $A[2i+2]$,
- parent of $A[i]$ is $A[\lfloor (i-1)/2 \rfloor]$.

```python
def parent(i):  return (i - 1) // 2
def left(i):    return 2 * i + 1
def right(i):   return 2 * i + 2
```

> **Why not a BST?** A BST is more powerful (search, total order)
> but costs more in memory (pointers) and constants. A heap simply
> exposes **min/max** at minimal cost - exactly what a *priority
> queue* needs.

---

## 4.2 - Primitive ops: sift-up and sift-down

When the order is locally violated, we **slide the offender
up/down** until the property is restored.

### `sift_up(i)`: move up

After insertion at the array tail or a key decrease (min-heap:
key increase), a node may violate order vs its parent.

```python
def sift_up(A, i):
    while i > 0 and A[parent(i)] < A[i]:
        A[parent(i)], A[i] = A[i], A[parent(i)]
        i = parent(i)
```

Cost: $\Theta(\log n)$ - at worst, climb leaf-to-root.

### `sift_down(i)`: move down

After root extraction or node degradation, swap with the **larger
child** while order is violated.

```python
def sift_down(A, n, i):
    while True:
        l, r, largest = left(i), right(i), i
        if l < n and A[l] > A[largest]: largest = l
        if r < n and A[r] > A[largest]: largest = r
        if largest == i: return
        A[i], A[largest] = A[largest], A[i]
        i = largest
```

Cost: $\Theta(\log n)$.

---

## 4.3 - `insert` and `extract_max`

```python
def insert(A, x):
    A.append(x)               # add at rightmost leaf
    sift_up(A, len(A) - 1)

def extract_max(A):
    top = A[0]
    last = A.pop()             # remove rightmost leaf
    if A:
        A[0] = last            # put at root, then rebalance
        sift_down(A, len(A), 0)
    return top
```

**Correctness.** The "is a heap" invariant is restored at the end
of each op, by construction of the sifts.

**Complexity.** Both ops $\Theta(\log n)$.

---

## 4.4 - `build_heap`: heapify in $\Theta(n)$

Given an arbitrary $A$, turn it into a heap.

### Naive

Insert one by one: $n$ inserts × $\Theta(\log n)$ each =
$\Theta(n \log n)$. Suboptimal!

### Bottom-up

```python
def build_heap(A):
    n = len(A)
    for i in range(n // 2 - 1, -1, -1):
        sift_down(A, n, i)
```

Start from the end (last leaves have no descendants to reorder)
and `sift_down` each internal node going up.

### Proof: $\Theta(n)$, not $\Theta(n \log n)$

The cost of `sift_down(i)` is bounded by the **height** of the
subtree rooted at $i$, not by total depth.

In an almost-complete tree with $n$ nodes, the number of nodes at
height $h$ is $\le \lceil n / 2^{h+1} \rceil$. So:

$$T(n) \le \sum_{h=0}^{\lfloor \log_2 n \rfloor} \left\lceil \frac{n}{2^{h+1}} \right\rceil \cdot O(h) = O\!\left( n \sum_{h=0}^{\infty} \frac{h}{2^h} \right).$$

The series $\sum_{h \ge 0} h / 2^h$ converges to $2$ (classic
$\sum h x^h = x/(1-x)^2$ at $x = 1/2$). So $T(n) = O(n)$. $\square$

> **Takeaway.** The mental shortcut "one-by-one = $n \log n$,
> bottom-up = $n$" is the difference between a *naive* and a
> *clever* build. For heapsort the global complexity ($n \log n$)
> doesn't change, but it's elegant.

---

## 4.5 - Heapsort

### Idea

1. `build_heap(A)` - $\Theta(n)$.
2. Repeat $n$ times: `extract_max` and place the result at the end
   of the array (in-place).

```python
def heapsort(A):
    n = len(A)
    # 1. build a max-heap
    for i in range(n // 2 - 1, -1, -1):
        sift_down(A, n, i)
    # 2. extract one at a time
    for end in range(n - 1, 0, -1):
        A[0], A[end] = A[end], A[0]   # max to the back
        sift_down(A, end, 0)          # heap on A[0:end]
```

### Correctness

After iteration `end = k`: `A[k..n[` holds the $n - k$ largest
elements sorted; `A[0..k]` is a valid max-heap on the remaining
$k+1$ elements.

- Before the loop: `A[0..n[` is a max-heap (`build_heap`).
- Each iteration moves the current max to `A[end]`, then restores
  the heap invariant on `A[0..end[` via `sift_down`.

At the end, `A[1..n[` is sorted ascending and `A[0]` is the
smallest - global invariant holds. $\square$

### Complexity

- `build_heap`: $\Theta(n)$.
- $n$ extractions × $\Theta(\log n)$: $\Theta(n \log n)$.
- **Total**: $\Theta(n \log n)$, worst case as well as best -
  no probabilistic argument needed (unlike quicksort).
- **In-place**: $O(1)$ extra memory.
- **Stable**: no (heap rotations scramble relative order).

| Algorithm | Worst | Average | Memory | Stable |
|-----------|-------|---------|--------|--------|
| Heapsort | $n \log n$ | $n \log n$ | $O(1)$ | no |
| Mergesort | $n \log n$ | $n \log n$ | $O(n)$ | yes |
| Quicksort | $n^2$ | $n \log n$ | $O(\log n)$ | no |

**Heap in action**: insert and extract to watch the heap restore
its invariant via sift-up and sift-down.

:::viz-heap{data="5,12,3,8,17,9,21"}
:::

Try a sequence of `extract-max` calls: you pull elements in
descending order - that's exactly the engine of **heapsort**.

---

## 4.6 - Exercises

:::exercise{id="{{EX_HP_HEAPSORT}}"}
:::

:::exercise{id="{{EX_HP_KSMALL}}"}
:::

:::exercise{id="{{EX_HP_MERGE}}"}
:::
