# 2. Traversal Applications

## 2.1 - Intuition

A plain traversal, well exploited, solves a surprising number of
problems. The key is to **decorate** the traversal: count its
launches, color as you go, or read the finishing order. Three classic
applications illustrate the principle.

- **Connected components**: one traversal per component.
- **Bipartiteness**: an alternating 2-coloring.
- **Topological sort**: order the tasks of an acyclic dependency
  graph.

---

## 2.2 - Algorithms & proofs

### Connected components

Launch a traversal from each unvisited vertex; the number of launches
is the number of components. A **Union-Find** gives the same answer by
merging the endpoints of each edge.

### Bipartiteness

Color the source $0$, its neighbors $1$, and so on, alternating. A
conflict (an edge between two same colors) proves non-bipartiteness.

- **Theorem.** A graph is bipartite **iff** it has no odd-length
  cycle. A coloring conflict closes exactly an odd cycle; conversely,
  the absence of conflict yields a valid bipartition. $\square$

### Topological sort (Kahn's algorithm)

```python
import heapq

def topo(n, adj, indeg):
    h = [i for i in range(n) if indeg[i] == 0]
    heapq.heapify(h)                 # min-heap -> lexicographic order
    order = []
    while h:
        u = heapq.heappop(h)
        order.append(u)
        for v in adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                heapq.heappush(h, v)
    return order if len(order) == n else None   # None = cycle
```

A vertex can leave only once all its dependencies are emitted. If, at
the end, vertices are missing, they form a cycle: none of them ever
reaches zero indegree.

---

## 2.3 - Complexity

All three algorithms are traversals, hence **linear**:

$$
T(n, m) = \Theta(n + m).
$$

The lexicographic topological sort replaces the queue with a min-heap,
adding a logarithmic factor:

$$
T(n, m) = \Theta\bigl((n + m) \log n\bigr).
$$

---

## 2.4 - Common pitfalls

1. **Bipartiteness on a disconnected graph.** Color **each**
   component; skipping an isolated component distorts the verdict.
2. **Topological sort = directed acyclic graph.** On an undirected or
   cyclic graph the notion is meaningless; Kahn detects this by
   counting emitted vertices.
3. **Wrongly initialized indegree.** Each edge $u \to v$ increments
   `indeg[v]`, not `indeg[u]`. An inversion breaks everything.
4. **Cycle vs impossible.** Return an explicit distinct "cycle" value
   rather than a silent partial order.

---

## 2.5 - One tool, a thousand uses

Cycle detection, build scheduling, package dependency resolution,
conflict coloring: all reduce to a decorated traversal. Learning to
**recognize** the traversal hidden in a statement is the central skill
of this lesson.

---

## 2.6 - Exercises

:::exercise{id="{{EX_GR_COMPONENTS}}"}
:::

:::exercise{id="{{EX_GR_BIPARTITE}}"}
:::

:::exercise{id="{{EX_GR_TOPOSORT}}"}
:::
