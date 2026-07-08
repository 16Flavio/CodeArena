# 4. Backtracking & Branch and Bound

## 4.1 - Intuition

When no structure (monotonicity, greedy substructure) offers a
shortcut, **exhaustive search** remains. Backtracking makes it
practical: build a solution **incrementally**, and as soon as a
prefix violates a constraint, **abandon** (backtrack) the whole
branch - no time wasted completing a doomed start.

Picture a maze explored depth-first: advance while you can, and at
the first dead end retreat to the last unexhausted fork. The
difference from a brute enumeration of all $b^n$ candidates is
**pruning**: cutting a branch at depth $d$ eliminates all its
descendants at once.

---

## 4.2 - Algorithm: the skeleton

Every backtracking follows the same recursive template.

```python
def backtrack(state, partial):
    if is_complete(partial):
        record(partial)
        return
    for choice in candidates(state, partial):
        if is_valid(partial, choice):     # pruning
            partial.append(choice)
            backtrack(advance(state, choice), partial)
            partial.pop()                 # undo the choice
```

The **choose - explore - undo** pattern (`append` ... `pop`) is the
signature of backtracking. For **N-queens**, the state is the current
row and `is_valid` tests column and diagonals via three sets:

```python
def solve(n):
    cols, diag, anti = set(), set(), set()
    def bt(r):
        if r == n:
            return 1
        total = 0
        for c in range(n):
            if c in cols or (r - c) in diag or (r + c) in anti:
                continue                  # O(1) pruning
            cols.add(c); diag.add(r - c); anti.add(r + c)
            total += bt(r + 1)
            cols.discard(c); diag.discard(r - c); anti.discard(r + c)
        return total
    return bt(0)
```

Placing one queen per row already encodes the "one per row"
constraint; the sets cover the rest in $O(1)$.

**Explore the tree** : `run` unrolls the N-queens backtracking, placing
row by row. A red cross marks a pruned square (attacked column or
diagonal), and the algorithm backtracks at dead ends.

:::viz-backtracking{n="6"}
:::

---

## 4.3 - Complexity

In the worst case, backtracking stays exponential: the search tree
has size

$$
O(b^n),
$$

where $b$ is the branching factor and $n$ the depth. Pruning does not
change this worst-case bound, but **in practice** it shrinks the
explored tree by orders of magnitude. For N-queens, the naive $n^n$
placements drop to $n!$ via the column constraint, then far lower
still via the diagonals.

**Branch and bound** adds a **bound**: at each node, estimate the
best value reachable in the subtree. If that bound is already worse
than the best known solution, cut. It is pruning applied to
**optimization** rather than constraint satisfaction.

---

## 4.4 - Common pitfalls

1. **Forgetting to undo the choice.** Without the `pop` (or
   `discard`), state leaks into sibling branches and corrupts the
   search.
2. **Pruning too late.** Test validity **before** descending, not
   after completing the solution: that is where the gain lives.
3. **Shared mutable state.** A dictionary or set mutated in place
   must be restored exactly; prefer symmetric markers (`add` /
   `discard`).
4. **Confusing counting with enumeration.** Counting solutions needs
   no storage: returning an integer suffices and avoids a memory
   blowup.

---

## 4.5 - When exponential is acceptable

Backtracking is the right tool when $n$ is **small** (a couple dozen
elements), or when pruning is so effective that the real instance
stays tiny. Beyond that, combine with other ideas: **meet in the
middle** (split the set into two halves of $2^{n/2}$), bitmask DP
(`dp[mask][...]`), or a relaxation that gives a tight bound for branch
and bound.

---

## 4.6 - Exercises

:::exercise{id="{{EX_PA_NQUEENS}}"}
:::

:::exercise{id="{{EX_PA_SUBSET_COUNT}}"}
:::

:::exercise{id="{{EX_PA_HAMILTON}}"}
:::
