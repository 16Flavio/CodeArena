# 6. Flows & Matching

## 6.1 - Intuition

Picture a network of pipes: each arc has a maximum **capacity**. How
much water can flow from a source $s$ to a sink $t$? That is the
**maximum flow** problem, and it is surprisingly central: a host of
combinatorial problems (matchings, assignments, cuts) reduce to it.

The augmenting-path idea: while a path from $s$ to $t$ remains along
which flow can be pushed, push it. The **residual graph** even lets
you "undo" flow already sent, which allows self-correction.

---

## 6.2 - Algorithm & theorem

### Augmenting paths (Edmonds-Karp)

While an augmenting path exists in the residual graph (found by BFS),
push along it the minimum residual capacity, and update the forward
and backward arcs.

```python
# Each arc stores a residual capacity; the backward arc
# (initially 0) receives the pushed flow, enabling cancellation.
def augment(residual, s, t):
    # BFS to find a path s -> t with residual capacity > 0,
    # return the pushed bottleneck (0 if no path).
    ...
```

### Max-flow / min-cut theorem

- **Theorem.** The maximum flow value equals the capacity of the
  **minimum cut** (a partition $S \ni s$, $\bar S \ni t$ minimizing
  the sum of capacities of arcs from $S$ to $\bar S$). Proof: every
  flow is bounded by every cut; when Edmonds-Karp stops, the set of
  vertices reachable in the residual graph forms a **saturated** cut,
  hence equal to the flow. $\square$

### Bipartite matching = unit flow

A maximum bipartite matching is computed by linking a source to all
left vertices, all right vertices to the sink, capacities $1$. Kuhn's
algorithm is the direct specialization of this idea.

---

## 6.3 - Complexity

$$
\begin{aligned}
\text{Edmonds-Karp} &: \Theta(V E^2), \\
\text{Dinic} &: \Theta(V^2 E), \\
\text{Kuhn (bipartite matching)} &: \Theta(V E).
\end{aligned}
$$

Dinic is the practical choice for general flow; Kuhn is more than
enough for medium-sized matchings.

---

## 6.4 - Common pitfalls

1. **Forgetting backward arcs.** Without them, no cancellation is
   possible, and the algorithm gets stuck on a suboptimal flow.
2. **BFS vs DFS.** Edmonds-Karp **requires** a BFS (shortest
   augmenting path) for its bound; a naive DFS can be exponential.
3. **Konig.** In a bipartite graph, minimum vertex cover = maximum
   matching. Do not recompute it by brute force.
4. **Zero capacities.** Skip arcs of residual capacity $0$ during
   path search.

---

## 6.5 - A universal hammer

Task assignment, scheduling, project selection, image segmentation,
tournaments: countless problems **reduce** to a flow or a matching.
Recognizing the reduction - modeling the statement as a network - is
the real skill, far more than reciting the algorithm.

---

## 6.6 - Exercises

:::exercise{id="{{EX_GR_MAXFLOW}}"}
:::

:::exercise{id="{{EX_GR_BIPMATCH}}"}
:::

:::exercise{id="{{EX_GR_MINVC}}"}
:::
