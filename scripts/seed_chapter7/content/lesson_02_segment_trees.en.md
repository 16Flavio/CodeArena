# 2. Segment Trees

## 2.1 - Intuition

You want to query and modify an array repeatedly: "sum of range
$[l, r]$", "set $a_i = x$", thousands of times. A raw array does the
update in $O(1)$ but the query in $O(n)$; prefix sums do the reverse.
The **segment tree** balances both: **every** operation in
$O(\log n)$.

The idea: a binary tree where each node summarizes an interval. The
root covers the whole array, its children a half each, and so on down
to the leaves (individual elements). Any range splits into $O(\log n)$
nodes.

---

## 2.2 - Algorithm

```python
# Iterative segment tree, sum, point update.
def build(a):
    n = len(a); size = 1
    while size < n: size *= 2
    tree = [0] * (2 * size)
    for i in range(n): tree[size + i] = a[i]
    for i in range(size - 1, 0, -1):
        tree[i] = tree[2*i] + tree[2*i+1]
    return tree, size

def update(tree, size, i, val):
    i += size; tree[i] = val; i //= 2
    while i:
        tree[i] = tree[2*i] + tree[2*i+1]; i //= 2

def query(tree, size, l, r):          # sum over [l, r]
    res = 0; l += size; r += size + 1
    while l < r:
        if l & 1: res += tree[l]; l += 1
        if r & 1: r -= 1; res += tree[r]
        l //= 2; r //= 2
    return res
```

### What makes the tree general

The merge operation (`+` here) can be **any** **associative**
operation with an identity element: minimum, maximum, gcd, XOR...
Changing `+` to `min` turns a sum tree into a minimum tree, without
touching the structure. That is the power of the model.

### Lazy propagation

For **range** updates ("add $x$ to all of $[l, r]$"), mark the node
covering the range with a deferred `lazy` value, and push it to the
children only when they are visited. This keeps range updates at
$O(\log n)$.

**Step through a range-sum query**: the range splits into $O(\log n)$ canonical nodes (green); the point update walks the leaf-to-root path.

:::viz-segment-tree{data="3,1,4,1,5,9,2,6" l="2" r="5"}
:::

---

## 2.3 - Complexity

$$
\begin{aligned}
\text{build} &: \Theta(n), \\
\text{update / query} &: \Theta(\log n), \\
\text{with lazy (range)} &: \Theta(\log n)\ \text{per operation}.
\end{aligned}
$$

Memory $\Theta(n)$. A query visits at most two root-to-leaf paths,
hence the $\log n$.

---

## 2.4 - Common pitfalls

1. **Non-associative merge.** The tree requires associativity; "the
   second largest" or "the mode" do not merge naively.
2. **Forgetting to push lazy.** Before descending into children
   (query or partial update), propagate the deferred mark, otherwise
   the values are wrong.
3. **Inclusive/exclusive indices.** Fix a convention and stick to it;
   an off-by-one corrupts every range.
4. **Identity element.** The query must start from the correct
   identity: $0$ for sum, $+\infty$ for min.

---

## 2.5 - A Swiss army knife

Segment tree: sums, min/max, counts, range assignments, $k$-th search,
persistent tree, segment tree on values... Few structures cover so
many range queries. Mastering its skeleton (covering a range with
$O(\log n)$ nodes) unlocks the whole family.

---

## 2.6 - Exercises

:::exercise{id="{{EX_DS_SEG_SUM}}"}
:::

:::exercise{id="{{EX_DS_SEG_RMQ}}"}
:::

:::exercise{id="{{EX_DS_SEG_LAZY}}"}
:::
