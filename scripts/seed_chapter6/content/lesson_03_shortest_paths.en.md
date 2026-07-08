# 3. Shortest Paths

## 3.1 - Intuition

As soon as edges carry a **weight** (distance, cost, time), BFS no
longer suffices: the path with the fewest edges is not the cheapest.
Three algorithms cover every case according to the nature of the
weights and the number of sources.

- **Dijkstra**: one source, non-negative weights. The fastest.
- **Bellman-Ford**: one source, negative weights allowed, detects
  negative cycles.
- **Floyd-Warshall**: **all** pairs, in one pass.

---

## 3.2 - Algorithms & proofs

### Dijkstra

```python
import heapq

def dijkstra(adj, s, n):
    dist = [float('inf')] * n
    dist[s] = 0
    pq = [(0, s)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:              # stale entry
            continue
        for v, w in adj[u]:
            if d + w < dist[v]:
                dist[v] = d + w
                heapq.heappush(pq, (dist[v], v))
    return dist
```

- **Correctness.** When a vertex $u$ is extracted from the heap,
  `dist[u]` is final. Proof: suppose a shorter path to $u$ exists; it
  passes through a vertex $x$ outside the final heap with
  `dist[x] < dist[u]`, but $x$ would have been extracted before $u$ -
  contradiction. This argument **requires weights $\ge 0$**; a
  negative edge could lower `dist[u]` after its extraction. $\square$

**Step through Dijkstra** : at each step the unsettled vertex with the
smallest distance is extracted (it becomes final), then its edges are
relaxed. The labels show the current tentative distance.

:::viz-dijkstra{source="0"}
:::

### Bellman-Ford

Relaxing **all** edges $n-1$ times suffices: a shortest simple path
has at most $n-1$ edges. An $n$-th pass that still relaxes signals a
**negative cycle**.

### Floyd-Warshall

$$
d[i][j] = \min\bigl(d[i][j],\ d[i][k] + d[k][j]\bigr)
$$

while growing the set of allowed intermediate vertices. The **outer**
loop is over $k$: that order guarantees correctness by induction on
$k$.

---

## 3.3 - Complexity

$$
\begin{aligned}
\text{Dijkstra (heap)} &: \Theta\bigl((n + m)\log n\bigr), \\
\text{Bellman-Ford} &: \Theta(n\,m), \\
\text{Floyd-Warshall} &: \Theta(n^3).
\end{aligned}
$$

Dijkstra for a fast single source; Floyd-Warshall when $n$ is small
but you want all pairs; Bellman-Ford when negative weights are in
play.

---

## 3.4 - Common pitfalls

1. **Dijkstra + negative weight = wrong.** The finality argument
   collapses. Use Bellman-Ford.
2. **Stale heap entries.** Do not delete old entries; test
   `d > dist[u]` and skip them.
3. **Reachable negative cycle.** A virtual source linked to all
   vertices at cost $0$ detects **any** negative cycle, not just
   those from a given source.
4. **Floyd loop order.** $k$ **must** be the outer loop. $k$ inside
   gives wrong answers.

---

## 3.5 - Choosing the right tool

Uniform weights -> BFS (lesson 1). Non-negative weights, one source
-> Dijkstra. Negative weights -> Bellman-Ford. All pairs on a small
graph -> Floyd-Warshall. The right reflex is to read the constraints
(sign of weights, $n$, number of queries) before coding.

---

## 3.6 - Exercises

:::exercise{id="{{EX_GR_DIJKSTRA}}"}
:::

:::exercise{id="{{EX_GR_NEGCYCLE}}"}
:::

:::exercise{id="{{EX_GR_FLOYD}}"}
:::
