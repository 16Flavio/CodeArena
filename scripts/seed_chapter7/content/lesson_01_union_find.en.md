# 1. Union-Find (DSU)

## 1.1 - Intuition

As links are added over time, how do you tell whether two elements are
**connected**? Rebuilding the components at each question would be
slow. The **Union-Find** structure (or DSU, *Disjoint Set Union*)
maintains a partition of elements into disjoint sets and answers two
operations in near-constant time:

- **union**: merge the sets of two elements;
- **find**: find the representative (the root) of an element.

The idea: each set is a tree, each element points to a parent, and the
root identifies the set. Two elements are connected iff they share the
same root.

---

## 1.2 - Algorithm & optimizations

```python
class DSU:
    def __init__(self, n):
        self.par = list(range(n))
        self.size = [1] * n

    def find(self, x):
        while self.par[x] != x:
            self.par[x] = self.par[self.par[x]]   # path compression
            x = self.par[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.size[ra] < self.size[rb]:         # union by size
            ra, rb = rb, ra
        self.par[rb] = ra
        self.size[ra] += self.size[rb]
        return True
```

Two optimizations make the structure efficient:

- **Path compression**: during a `find`, rewire nodes directly (or
  nearly) onto the root.
- **Union by size (or rank)**: always attach the small tree under the
  large one, keeping the trees flat.

---

## 1.3 - Complexity

With **both** optimizations, a sequence of $m$ operations on $n$
elements costs

$$
T = O\bigl(m \cdot \alpha(n)\bigr),
$$

where $\alpha$ is the **inverse Ackermann function**: it grows so
slowly that $\alpha(n) \le 4$ for any physically conceivable $n$. In
practice, each operation is **constant**.

Without optimization, a `find` can cost $\Theta(n)$ (tree degenerated
into a list); with only one of the two, it drops to $\Theta(\log n)$
amortized.

---

## 1.4 - Common pitfalls

1. **Union without `find`.** Always union the **roots**, not the raw
   elements, or you break the tree structure.
2. **Skipping one optimization.** Compression **and** union by size
   are both needed for the $\alpha(n)$ bound.
3. **No deletion.** DSU does not support splitting a set; for dynamic
   connectivity with deletions, other techniques are needed (offline,
   LCT).
4. **Recursive `find`.** On large trees, a recursive version overflows
   the stack; prefer the loop above.

---

## 1.5 - Powerful variants

DSU comes in flavors: **union by parity** (store the 0/1 relation to
the root, for "same / different" constraints and bipartitioning),
**weighted DSU** (relative distances), or **persistent DSU**. Kruskal
(graphs chapter) is its flagship application. A simple structure, a
wide range of uses.

---

## 1.6 - Exercises

:::exercise{id="{{EX_DS_DSU_QUERY}}"}
:::

:::exercise{id="{{EX_DS_DSU_MAXSIZE}}"}
:::

:::exercise{id="{{EX_DS_DSU_PARITY}}"}
:::
