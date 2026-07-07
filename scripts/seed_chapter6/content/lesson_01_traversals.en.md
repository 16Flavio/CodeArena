# 1. Representations & BFS/DFS Traversal

## 1.1 - Intuition

A **graph** is a set of vertices joined by edges. It models almost
everything: road networks, task dependencies, social relations, game
grids. Two questions come up endlessly: "who is reachable from here?"
and "what is the shortest path?". The two fundamental **traversals**
answer them.

**Breadth**-first search (BFS) explores in concentric rings: first
the direct neighbors, then the neighbors of neighbors. **Depth**-
first search (DFS) dives as far as possible before backtracking. The
former measures distances, the latter reveals structure (cycles,
components, order).

---

## 1.2 - Representation & algorithms

A graph with $n$ vertices and $m$ edges is stored as an **adjacency
list**: for each vertex, the list of its neighbors. That is
$\Theta(n + m)$ memory, versus $\Theta(n^2)$ for a matrix - almost
always the right choice for a sparse graph.

```python
from collections import deque

def bfs(adj, s):
    n = len(adj)
    dist = [-1] * n
    dist[s] = 0
    q = deque([s])
    while q:
        u = q.popleft()
        for v in adj[u]:
            if dist[v] == -1:        # never seen
                dist[v] = dist[u] + 1
                q.append(v)
    return dist
```

### BFS invariant

The queue always holds vertices of distance $d$ then $d+1$, and never
two values more than $1$ apart.

- **Correctness (shortest path).** The first time a vertex $v$ is
  reached, it is via a minimum-length path. Proof: vertices leave the
  queue by increasing distance; if $v$ were reachable more cheaply, it
  would have been discovered from a vertex dequeued earlier.
  $\square$

DFS, in turn, is coded recursively (or with an explicit stack): visit
an unseen neighbor, recurse, return.

---

## 1.3 - Complexity

Each vertex is enqueued once, each edge examined at most twice (once
per endpoint). Hence:

$$
T(n, m) = \Theta(n + m).
$$

This is optimal: you must at least look at every vertex and every
edge. BFS and DFS share this bound; they differ only in visit order
(queue versus stack).

---

## 1.4 - Common pitfalls

1. **Mark on enqueue, not on dequeue.** Marking a vertex when it
   leaves the queue (instead of when it is added) sometimes lets it
   enter multiple times - blown-up complexity.
2. **Grids = implicit graphs.** An $R \times C$ grid is a graph with
   $RC$ vertices; no need to build the adjacency list, the 4
   neighbors are computed on the fly.
3. **DFS recursion.** On a $10^5$-vertex path graph, Python recursion
   overflows the stack; switch to an explicit stack or raise
   `sys.setrecursionlimit`.
4. **Isolated vertices.** Do not forget to launch the traversal from
   **each** component when you want full coverage.

---

## 1.5 - What each reveals

BFS gives unweighted distances and the proximity layer. DFS gives
entry/exit times, the basis of the lesson 5 algorithms (SCC,
bridges). Choose by the question: minimum distance -> BFS;
structure, order, cycles -> DFS.

---

## 1.6 - Exercises

:::exercise{id="{{EX_GR_BFS_DIST}}"}
:::

:::exercise{id="{{EX_GR_GRID_BFS}}"}
:::

:::exercise{id="{{EX_GR_ISLANDS}}"}
:::
