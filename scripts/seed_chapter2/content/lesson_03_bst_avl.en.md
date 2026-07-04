# 3. Binary Search Trees & Balancing (AVL)

## 3.1 - The binary search tree

A **BST** is a binary tree such that, for every node $v$ with key
$v.k$:

$$\forall u \in \text{left subtree}(v),\ u.k < v.k \quad\text{and}\quad \forall u \in \text{right subtree}(v),\ u.k > v.k.$$

This property gives us:

- **In-order traversal** visits keys in ascending order - $\Theta(n)$.
- **Search**: walks one path, $\Theta(h)$ where $h$ is the height.
- **Insertion**: walks down to a leaf and attaches, $\Theta(h)$.
- **Successor**: if right subtree non-empty, its minimum; otherwise,
  the first ancestor whose left subtree contains $v$, $\Theta(h)$.

```python
class Node:
    def __init__(self, k):
        self.k = k
        self.l = None
        self.r = None
        self.h = 1   # height, used by AVL

def search(root, k):
    while root and root.k != k:
        root = root.l if k < root.k else root.r
    return root

def insert(root, k):
    if root is None:    return Node(k)
    if k < root.k:      root.l = insert(root.l, k)
    elif k > root.k:    root.r = insert(root.r, k)
    return root
```

> **Disaster scenario.** Insert $1, 2, 3, \dots, n$ in order: the
> BST degenerates into a chain, $h = n$, every operation
> $\Theta(n)$. Worst case - frequent in practice (sorted inputs).

:::viz-bst{keys="50,30,70,20,40,60,80"}
:::

Reset, then insert $1, 2, 3, 4, 5$ one by one - the tree degenerates
to a chain (height $5$). Now reset and insert a balanced BST like
`4,2,6,1,3,5,7`: height $3$. Same $n = 7$, same keys, **radically
different height depending on insertion order**.

---

## 3.2 - Rotations

A **rotation** restructures a subtree **without breaking the BST
property** and changes the height locally.

### Right rotation

```
     y               x
    / \             / \
   x   C    →     A   y
  / \                 / \
 A   B               B   C
```

**Key invariant.** Since all elements of $A$ are $< x.k$, those of
$B$ between $x.k$ and $y.k$, and those of $C$ $> y.k$, the rotated
tree is still a BST. Cost: $\Theta(1)$.

```python
def rot_right(y):
    x = y.l
    y.l = x.r
    x.r = y
    update_height(y)        # y is now below
    update_height(x)
    return x                # new root of the subtree
```

The **left rotation** is symmetric. These two $\Theta(1)$ ops are
the building block of every balanced tree.

---

## 3.3 - AVL: height invariant

Invented in 1962 by Adelson-Velsky and Landis. **Invariant**: for
every node $v$,

$$|h(v.l) - h(v.r)| \le 1.$$

Let $\text{bf}(v) = h(v.l) - h(v.r)$ be the **balance factor**. An
AVL keeps $\text{bf}(v) \in \{-1, 0, +1\}$.

### Height theorem

**Theorem.** An AVL with $n$ nodes has height $h \le c \cdot
\log_2(n+1) + O(1)$ for some constant $c \approx 1.44$.

*Proof.* Let $N(h)$ be the **minimum** number of nodes in an AVL of
height $h$. Such a minimal tree has a root, one subtree of height
$h-1$, and one of height $h-2$. So:

$$N(h) = 1 + N(h-1) + N(h-2),\quad N(0) = 1,\ N(1) = 2.$$

This is the shifted Fibonacci sequence: $N(h) = F(h+2) - 1$. Since
$F(k) = \Theta(\varphi^k)$ with $\varphi = (1+\sqrt 5)/2$, we get
$h \le \log_\varphi (n + 1) - O(1) = \frac{\log_2(n+1)}{\log_2
\varphi} + O(1) \approx 1.44 \log_2 n$. $\square$

→ **All operations** (search, insert, delete) are $\Theta(\log n)$
worst-case in an AVL.

---

## 3.4 - AVL insertion: algorithm

After a standard BST insert, walk back up the recursion stack; at
each ancestor:

1. Recompute height.
2. Compute $\text{bf}$. If $\text{bf} \in \{-1, 0, +1\}$, OK.
3. Otherwise, **rebalance** with rotations per the case.

### The four rebalancing cases

Let $v$ be the first unbalanced node found on the way up.

| Case | Description | Action |
|------|-------------|--------|
| **LL** | $\text{bf}(v) = +2$, insertion in left-left subtree | right-rotate $v$ |
| **RR** | $\text{bf}(v) = -2$, in right-right | left-rotate $v$ |
| **LR** | $\text{bf}(v) = +2$, in left-right | left-rotate $v.l$, then right-rotate $v$ |
| **RL** | $\text{bf}(v) = -2$, in right-left | right-rotate $v.r$, then left-rotate $v$ |

### Code

```python
def height(n): return n.h if n else 0
def update_height(n): n.h = 1 + max(height(n.l), height(n.r))
def bf(n): return height(n.l) - height(n.r)

def insert_avl(root, k):
    if root is None: return Node(k)
    if k < root.k:   root.l = insert_avl(root.l, k)
    elif k > root.k: root.r = insert_avl(root.r, k)
    else:            return root   # already present
    update_height(root)
    b = bf(root)
    if b > 1 and k < root.l.k:                      # LL
        return rot_right(root)
    if b < -1 and k > root.r.k:                     # RR
        return rot_left(root)
    if b > 1 and k > root.l.k:                      # LR
        root.l = rot_left(root.l)
        return rot_right(root)
    if b < -1 and k < root.r.k:                     # RL
        root.r = rot_right(root.r)
        return rot_left(root)
    return root
```

### Correctness proof

**Invariant.** After every `insert_avl` call, the returned subtree
is a valid AVL containing exactly the original keys plus $k$.

*Inductive step (key argument).* If the recursive call returns a
valid AVL child, `update_height` is correct. If $|\text{bf}| \le 1$,
return `root`: the AVL invariant holds trivially (children
unchanged).

If $|\text{bf}| = 2$, we're in one of four cases. A case-by-case
analysis (omitted for brevity) shows the rotation(s):

1. preserve the BST property (by construction),
2. restore the subtree's height to its **pre-insertion** value,
3. so no further ancestor can become unbalanced.

Hence the **fundamental property**: an AVL insertion makes at most
**two rotations** ($\Theta(1)$), and the bubble-up stops at the
first rebalance. Total cost $\Theta(\log n)$. $\square$

> **AVL vs red-black.** AVL is **stricter** (tighter balance,
> height $\sim 1.44 \log n$), so searches are slightly faster;
> red-black trees do fewer rotations on average (used in
> `std::map`, Java `TreeMap`, Linux kernel). Read-heavy load: AVL
> wins. Insert/delete-heavy: red-black wins.

---

## 3.5 - Exercises

:::exercise{id="{{EX_BST_INORDER}}"}
:::

:::exercise{id="{{EX_BST_PREORDER}}"}
:::

:::exercise{id="{{EX_BST_HEIGHT}}"}
:::
