# 5. Connectivity: SCC, Bridges, Articulation

## 5.1 - Intuition

Beyond "is the graph connected?", we want to measure its
**robustness**: which vertices or edges are critical? DFS, enriched
with two clocks, reveals this fine structure.

- **Strongly connected components** (SCC): in a directed graph, the
  groups of mutually reachable vertices.
- **Bridges**: edges whose removal disconnects the graph.
- **Articulation points**: vertices whose removal disconnects the
  graph.

---

## 5.2 - Algorithms & proofs

### low-link: the heart of the lesson

DFS assigns each vertex a discovery time `disc[u]`. We compute
`low[u]`: the smallest time reachable from $u$'s subtree using **at
most one** back edge.

```python
def bridges(n, adj):              # adj[u] = [(v, edge_id), ...]
    disc = [-1] * n; low = [0] * n; timer = [0]; count = [0]
    def dfs(u, pe):
        disc[u] = low[u] = timer[0]; timer[0] += 1
        for v, ei in adj[u]:
            if ei == pe:          # do not reuse the parent edge
                continue
            if disc[v] == -1:
                dfs(v, ei)
                low[u] = min(low[u], low[v])
                if low[v] > disc[u]:
                    count[0] += 1     # (u, v) is a bridge
            else:
                low[u] = min(low[u], disc[v])
    for s in range(n):
        if disc[s] == -1:
            dfs(s, -1)
    return count[0]
```

- **Bridge.** The edge to a child $v$ is a bridge **iff**
  `low[v] > disc[u]`: no descendant of $v$ can climb back above $u$
  without it.
- **Articulation.** An internal vertex $u$ is an articulation point
  iff some child $v$ satisfies `low[v] >= disc[u]`. The **root** is
  one iff it has at least two children in the DFS tree.

### SCC (Kosaraju)

A first DFS stacks vertices by finish time; a second DFS on the
**transposed** graph, in reverse stack order, isolates each SCC.
Correctness rests on the fact that the vertex of largest finish time
belongs to a "source" SCC of the condensed graph.

---

## 5.3 - Complexity

All these algorithms are DFS augmented with constant work per edge:

$$
T(n, m) = \Theta(n + m).
$$

Kosaraju does two passes (so $2(n+m)$); Tarjan gets the SCCs in a
single pass, same asymptotic bound.

---

## 5.4 - Common pitfalls

1. **Parent edge vs back edge.** When finding bridges, ignore the
   edge you arrived by - but **only once**; on a graph with multiple
   edges, index by edge id, not by vertex.
2. **Root case.** The articulation rule differs for the DFS root (two
   children) and for internal vertices (`low[v] >= disc[u]`).
3. **Disconnected graph.** Relaunch the DFS on each component.
4. **Deep recursion.** On $10^5$ vertices, raise the recursion limit
   or go iterative.

---

## 5.5 - Why it matters

These notions model fault tolerance: a bridge is a critical network
link, an articulation point a router whose failure isolates a region.
SCCs condense a directed graph into a DAG, the first step of many
algorithms (2-SAT, scheduling).

---

## 5.6 - Exercises

:::exercise{id="{{EX_GR_SCC}}"}
:::

:::exercise{id="{{EX_GR_BRIDGES}}"}
:::

:::exercise{id="{{EX_GR_ARTIC}}"}
:::
