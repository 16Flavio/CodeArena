# 4. Minimum Spanning Trees

## 4.1 - Intuition

Given a connected weighted graph, a **spanning tree** links all
vertices with exactly $n-1$ edges and no cycle. Among all spanning
trees, the **minimum** one (MST) has the lowest total weight: the
cheapest network that keeps everyone connected.

Two greedy algorithms solve the problem, each with its exchange-
argument proof (see the paradigms chapter).

- **Kruskal**: sort the edges, add the lightest one that creates no
  cycle.
- **Prim**: grow a single tree by adding the lightest outgoing edge.

---

## 4.2 - Algorithm & proof

### Kruskal

```python
def kruskal(n, edges):            # edges = [(w, u, v), ...]
    edges.sort()
    par = list(range(n))
    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    total = 0
    for w, u, v in edges:
        ru, rv = find(u), find(v)
        if ru != rv:              # creates no cycle
            par[ru] = rv
            total += w
    return total
```

### Cut property

- **Theorem.** For any **cut** (partition of the vertices into two
  sides), the **minimum-weight** edge crossing the cut belongs to some
  MST. Exchange proof: suppose an MST $T$ does not contain it; adding
  the edge creates a cycle that recrosses the cut via an at-least-as-
  heavy edge; swapping them does not increase the weight. $\square$

Kruskal applies this property: each added edge is the lightest
crossing the cut separating its component from the rest.

**Build the MST** : edges are sorted by weight; `step` tests each and
keeps it (green) if it joins two components, or rejects it (red) if it
would form a cycle. The vertex colours show the components merging.

:::viz-mst-kruskal
:::

---

## 4.3 - Complexity

Kruskal is dominated by the sort, plus near-constant Union-Find
operations:

$$
T(n, m) = \Theta\bigl(m \log m\bigr).
$$

Prim with a heap reaches $\Theta(m \log n)$. Both are essentially
equivalent; Kruskal shines on sparse graphs given as an edge list.

---

## 4.4 - Common pitfalls

1. **Disconnected graph.** Then no spanning tree exists; detect the
   case (fewer than $n-1$ edges kept) and report it.
2. **Minimum bottleneck != unique MST.** The MST **also** minimizes
   the largest edge (minimum bottleneck tree), but a minimum
   bottleneck tree need not be an MST.
3. **Union-Find without compression.** Without path compression or
   union by rank, `find` degenerates to $\Theta(n)$.
4. **Equal-weight edges.** Several distinct MSTs can coexist; account
   for that in uniqueness or second-best-tree questions.

---

## 4.5 - Beyond the minimum

The same skeleton solves variants: minimum bottleneck tree (minimize
the maximum edge), second-best spanning tree (swap an MST edge for the
best replacement), or maximize weight by sorting in reverse.
Mastering the cut property means holding the whole family.

---

## 4.6 - Exercises

:::exercise{id="{{EX_GR_MST}}"}
:::

:::exercise{id="{{EX_GR_BOTTLENECK}}"}
:::

:::exercise{id="{{EX_GR_SECOND_MST}}"}
:::
