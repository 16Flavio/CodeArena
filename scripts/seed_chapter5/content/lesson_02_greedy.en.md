# 2. Greedy Algorithms & Proofs

## 2.1 - Intuition

A **greedy** algorithm builds a solution step by step, making at each
stage the **locally most advantageous** choice, never backtracking.
It is the most naive strategy there is - and yet, for a precise class
of problems, it yields the global optimum.

The danger is real: greedy often fails. Making change with coins
$\{1, 3, 4\}$ for $6$ gives $4 + 1 + 1$ (three coins) when $3 + 3$
suffices. A greedy choice is correct only if you **prove** it. Two
ingredients suffice:

- **Greedy-choice property**: some optimum contains (or can be
  transformed to contain) the first greedy choice.
- **Optimal substructure**: after that choice, the remaining
  subproblem is solved the same way.

---

## 2.2 - Algorithm & exchange argument

Take **activity selection**: $n$ intervals $[s_i, e_i)$, choose a
maximum set of pairwise-disjoint ones.

```python
def select(intervals):
    intervals.sort(key=lambda p: p[1])   # by increasing finish
    count, cur_end = 0, float('-inf')
    for s, e in intervals:
        if s >= cur_end:                 # compatible?
            count += 1
            cur_end = e                  # accept it
    return count
```

The greedy choice: **take the activity that finishes earliest**.

**Watch the greedy pick** : intervals are sorted by earliest finish;
`step` takes each compatible activity and rejects those overlapping the
current end (dashed line).

:::viz-greedy-intervals{intervals="1,4;3,5;0,6;5,7;3,8;5,9;6,10;8,11;8,12;2,13"}
:::

### Proof by exchange argument

Let $g_1$ be the activity with minimum finish time, and let $O$ be an
optimal solution. Sort $O$ by finish time and let $o_1$ be its first
activity.

- By minimality, $e(g_1) \le e(o_1)$.
- So every activity of $O$ compatible with $o_1$ (starting after
  $e(o_1)$) is **also** compatible with $g_1$.
- Replacing $o_1$ by $g_1$ in $O$ yields a valid solution of the
  **same size**: it stays optimal and starts with the greedy choice.

By induction on the subproblem "activities starting after $e(g_1)$",
greedy reaches the optimum. $\square$

The exchange is the universal greedy proof template: show you can
**transform** any optimum so it adopts the first greedy choice
without losing quality.

---

## 2.3 - Complexity

The cost is dominated by the initial sort:

$$
T(n) = \underbrace{\Theta(n \log n)}_{\text{sort}} +
\underbrace{\Theta(n)}_{\text{scan}} = \Theta(n \log n).
$$

For connecting ropes (Huffman coding), the sort is replaced by a
**heap** taking $2n$ operations at $\Theta(\log n)$ each, again
$\Theta(n \log n)$.

---

## 2.4 - Common pitfalls

1. **Sorting by the wrong key.** For activity selection, sorting by
   **finish** (not by start, nor by duration) is what makes greedy
   correct. The key is the heart of the proof.
2. **Confusing greedy with dynamic programming.** If no exchange
   argument holds (0/1 knapsack, for instance), greedy fails and you
   need a DP (lesson 3).
3. **Skipping the proof.** A greedy that "works on the examples" may
   fail on an edge case. No proof, no guarantee.
4. **Boundary equalities.** Half-open intervals $[s, e)$:
   `s >= cur_end` (not `>`) lets an activity start exactly when the
   previous one ends.

---

## 2.5 - When greedy is optimal

Formally, the problems where greedy always yields the optimum are
exactly those whose feasible solutions form a **matroid** - an
abstract independence structure. You do not need the full theory, but
the intuition helps: if "add the best remaining element that
preserves feasibility" gives the optimum regardless of the starting
point, that signals matroid structure.

---

## 2.6 - Exercises

:::exercise{id="{{EX_PA_ACTIVITY}}"}
:::

:::exercise{id="{{EX_PA_ROPES}}"}
:::

:::exercise{id="{{EX_PA_JOBSEQ}}"}
:::
