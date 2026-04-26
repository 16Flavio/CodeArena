# 4. Amortized Analysis & Dynamic Array

## 4.1 — The idea: averaging costs

Some operations are *occasionally* expensive but *globally* cheap.
Worst-case analysis grossly overestimates their real cost.

**Motivating example.** Insert $n$ integers into a dynamic array
(Python `list`, C++ `std::vector`). Once in a while the array
**doubles** its capacity — an $O(\text{capacity})$ operation. Worst
case, one insertion costs $O(n)$. But over $n$ insertions, the total
cost stays $O(n)$: the **amortized** cost per insertion is $O(1)$.

Amortized analysis formalizes this with **three equivalent methods**:
aggregate, accounting, potential.

---

## 4.2 — Aggregate method

Compute the total cost of $n$ operations, divide by $n$.

**Dynamic array.** Initial capacity $1$. On insertion $k$, if the array
is full, allocate $2k$, copy $k$ elements, insert.

- Doubling happens when $k$ is a power of $2$: $k = 1, 2, 4, 8, \dots$
- Insertion without doubling: $1$ (the write).
- Insertion with doubling at $k = 2^j$: $2^j$ (copies) $+ 1$.

Total cost over $n$ insertions:

$$\text{Total} = n + \sum_{j=0}^{\lfloor \log_2 n \rfloor} 2^j \le n + 2n = 3n.$$

Amortized cost: $3n / n = O(1)$. $\square$

---

## 4.3 — Accounting method (banker's)

We *charge* each operation an artificial cost (the **amortized cost**)
that may exceed its real cost. The difference is stored as **credit**
on specific structure elements.

**Consistency rule.** At any time, $\sum \text{amortized} \ge \sum \text{real}$.

**Dynamic array.** Charge $3$ per insertion:
- $1$ for the write itself,
- $1$ as credit on the new element,
- $1$ as credit on an old element (to pay for its future copy).

When a doubling happens (going from $k$ to $2k$), we must copy the $k$
existing elements. But each has accumulated $\ge 1$ credit since the
last reorganization: those credits pay the copies. Amortized cost
stays at $3 = O(1)$ per insertion. $\square$

---

## 4.4 — Potential method

Define a function $\Phi$ from the structure's state into
$\mathbb{R}_{\ge 0}$ with $\Phi(\text{initial}) = 0$. The amortized cost
of an operation is:

$$\hat c_i = c_i + \Phi(D_i) - \Phi(D_{i-1}).$$

Over $n$ operations:

$$\sum \hat c_i = \sum c_i + \Phi(D_n) - \Phi(D_0) \ge \sum c_i.$$

So $\sum c_i \le \sum \hat c_i$: bounding amortized costs is enough.

**Dynamic array.** Set $\Phi = 2 \cdot \text{size} - \text{capacity}$
(always $\ge 0$ after an insertion that doesn't trigger a realloc,
and $= 0$ right after a doubling).

- Insertion without doubling: size goes from $s$ to $s+1$, capacity
  unchanged. $\Delta\Phi = 2$. Amortized $= 1 + 2 = 3$.
- Insertion with doubling at $s = c$: copy $c$, capacity $\to 2c$,
  size $\to c+1$. $\Phi$ goes from $2c - c = c$ to $2(c+1) - 2c = 2$.
  $\Delta\Phi = 2 - c$. Real cost $= c + 1$. Amortized $= c + 1 + 2 - c = 3$.

**Constant** amortized cost, $O(1)$ per insertion. $\square$

> **Note.** All three methods give the same answer. Pick the one
> closest to the problem: aggregate for uniform sequences, accounting
> for "physical credits", potential for algebraic invariants.

---

## 4.5 — Algorithm and proof of correctness

```python
class DynamicArray:
    def __init__(self):
        self.cap = 1
        self.size = 0
        self.buf = [None] * self.cap

    def append(self, x):
        if self.size == self.cap:
            new_cap = 2 * self.cap
            new_buf = [None] * new_cap
            for i in range(self.size):       # O(cap) copies
                new_buf[i] = self.buf[i]
            self.buf = new_buf
            self.cap = new_cap
        self.buf[self.size] = x
        self.size += 1
```

**Correctness (sketch).** Invariant: after each `append`, we have
`0 ≤ size ≤ cap`, `cap` is a power of $2$, and the first `size`
positions of `buf` hold the inserted elements in order. The invariant
holds initially. On each insertion: if we double, the new `buf` still
holds the elements in order (the copy loop preserves indices). Then we
write `buf[size]` and increment `size`. $\square$

**Complexity.** $\Theta(1)$ amortized per `append`, $\Theta(n)$ for $n$
consecutive insertions.

---

## 4.6 — Exercises

:::exercise{id="{{EX_AMO_STD}}"}
:::

:::exercise{id="{{EX_AMO_TWIST}}"}
:::

:::exercise{id="{{EX_AMO_HARD}}"}
:::
