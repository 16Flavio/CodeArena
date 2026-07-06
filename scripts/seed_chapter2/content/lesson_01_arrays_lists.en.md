# 1. Arrays, Linked Lists, Stacks, Queues & Deques

## 1.1 - Arrays, the workhorse

An **array** is a contiguous sequence of memory cells. Indexed by an
integer $i \in [0, n[$, the access $A[i]$ is $\Theta(1)$ thanks to
address arithmetic: $\text{addr}(A[i]) = \text{base} + i \cdot
\text{element\_size}$.

| Operation | Static array | Dynamic array (cf. ch. 1) |
|-----------|--------------|---------------------------|
| Access $A[i]$ | $\Theta(1)$ | $\Theta(1)$ |
| Append at end | impossible | $\Theta(1)$ amortized |
| Insert at position $i$ | $\Theta(n - i)$ | $\Theta(n - i)$ |
| Remove at position $i$ | $\Theta(n - i)$ | $\Theta(n - i)$ |

The cost of mid-array insertions/removals comes from **shifting**
every following element.

---

## 1.2 - Linked lists

To make insertion/removal $\Theta(1)$ *at a known location*, we
replace memory contiguity by **links** between nodes.

### Singly linked list

```python
class Node:
    def __init__(self, val, nxt=None):
        self.val = val
        self.nxt = nxt
```

- **Head insertion**: $\Theta(1)$.
- **Head removal**: $\Theta(1)$.
- **Index access**: $\Theta(i)$ - must traverse.
- **Insertion after a known node**: $\Theta(1)$.

### Doubly linked list

Each node also carries `prev`. We gain:

- **Removal of a known node** in $\Theta(1)$ (no need to find the
  predecessor).
- **Reverse iteration**.

At the cost of one extra word per node.

> **When to prefer a linked list over a dynamic array?** When you
> often insert/remove mid-sequence *at a position you already hold*
> (an iterator, a sentinel node). Otherwise the dynamic array almost
> always wins thanks to cache locality.

---

## 1.3 - Stacks, queues, deques

Three interfaces, all implementable on top of a dynamic array or a
doubly linked list.

### Stack (LIFO)

Operations: `push`, `pop`, `top`. All $\Theta(1)$ amortized
(dynamic array) or $\Theta(1)$ worst-case (list).

### Queue (FIFO)

Operations: `enqueue` (push back), `dequeue` (pop front).

- **Circular array** implementation: two indices `head` and `tail`
  modulo capacity. $\Theta(1)$ amortized.
- **Doubly linked list** implementation: $\Theta(1)$ worst-case.

### Deque (double-ended queue)

Operations: `push_front`, `push_back`, `pop_front`, `pop_back`. All
$\Theta(1)$ with a doubly linked list or a doubling circular array.

> **The deque is the secret weapon of sliding-window algorithms** -
> we use it in the lesson below (sliding maximum) to maintain a
> decreasing sequence of candidates for the window maximum (not the
> window itself) with amortized $\Theta(1)$ per element.

---

## 1.4 - Algorithm: queue with two stacks

A classic that shows how to compose data structures.

### Idea

Two stacks, `in` (for enqueue) and `out` (for dequeue). When `out` is
empty and a dequeue is requested, we **transfer** everything from
`in` to `out`, reversing the order in the process.

### Code

```python
class Queue:
    def __init__(self):
        self.in_  = []
        self.out_ = []

    def enqueue(self, x):
        self.in_.append(x)

    def dequeue(self):
        if not self.out_:
            while self.in_:
                self.out_.append(self.in_.pop())
        return self.out_.pop() if self.out_ else None
```

### Correctness proof

**Invariant.** At all times, `out_[::-1] + in_` represents the queue
in arrival order.

- *Init.* Both stacks empty, invariant holds.
- *Step.*
  - `enqueue(x)` pushes $x$ on top of `in_`, i.e. at the end of the
    concatenation. ✓
  - `dequeue` with `out_` non-empty: pops the top of `out_`, which is
    the **first** element of `out_[::-1]`. ✓
  - `dequeue` with `out_` empty: transfer `in_` to `out_` reversing
    via `pop`. After transfer, `out_[::-1]` contains the elements in
    the original `in_` order. Final `pop` returns the first. ✓

$\square$

### Complexity (amortized)

Each element is `push`ed onto `in_` once, transferred once to
`out_`, then `pop`ped once. So **3 operations total** per element
over its lifetime. The amortized cost of `enqueue` and `dequeue` is
$\Theta(1)$, even though a single `dequeue` can be $\Theta(n)$ (at
transfer time).

This is exactly the banker's method (cf. ch. 1): charge $3$ on each
`enqueue`; the credit on the element pays for its transfer and its
exit.

---

## 1.5 - Exercises

:::exercise{id="{{EX_DS_QUEUE}}"}
:::

:::exercise{id="{{EX_DS_SLIDING}}"}
:::

:::exercise{id="{{EX_DS_JOSEPHUS}}"}
:::
