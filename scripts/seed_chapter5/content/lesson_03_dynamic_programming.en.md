# 3. Dynamic Programming

## 3.1 - Intuition

Dynamic programming (DP) applies when a problem decomposes into
**overlapping subproblems**. A naive recursion would then recompute
the same subproblems an exponential number of times; DP solves each
**once** and memorizes the result.

Two conditions make DP applicable:

- **Optimal substructure**: the optimal solution is built from
  optimal solutions of subproblems.
- **Overlap**: the number of **distinct** subproblems is polynomial,
  even if the recursion tree is exponential.

The canonical example: naive Fibonacci makes $\Theta(\varphi^n)$
calls; memoized, it makes $\Theta(n)$.

---

## 3.2 - Algorithm: two styles

There are two ways to implement the same recurrence.

**Top-down (memoization).** Write the natural recursion and cache it:

```python
from functools import lru_cache

@lru_cache(maxsize=None)
def f(state):
    if base_case(state):
        return base_value
    return combine(f(sub1), f(sub2), ...)
```

**Bottom-up (tabulation).** Fill a table in dependency order:

```python
dp = [base] * (n + 1)
for i in range(1, n + 1):
    dp[i] = combine(dp[i-1], dp[i-2], ...)
return dp[n]
```

Take the **longest increasing subsequence** (LIS). Let $L(i)$ be the
length of the longest increasing subsequence ending exactly at $i$:

$$
L(i) = 1 + \max\bigl(\{\,0\,\} \cup \{\,L(j) : j < i,\ a_j < a_i\,\}\bigr).
$$

The answer is $\max_i L(i)$. The recurrence is correct because any
increasing subsequence ending at $i$ extends an increasing
subsequence ending at some $j < i$ with $a_j < a_i$ - optimal
substructure.

---

## 3.3 - Complexity

The cost of a DP is

$$
T = (\text{number of states}) \times (\text{cost per transition}).
$$

- **LIS**: $n$ states, $O(n)$ transition, i.e. $\Theta(n^2)$;
  refinable to $\Theta(n \log n)$ via binary search on the smallest
  tails.
- **0/1 knapsack**: $\Theta(nW)$ state-transitions (pseudo-
  polynomial: depends on the value $W$, not just its bit size).
- **Edit distance**: $\Theta(|s|\,|t|)$.

Tabulation often lets you **shrink memory**: knapsack and edit
distance need only one or two rows of the table at a time.

---

## 3.4 - Common pitfalls

1. **Fill order.** In bottom-up, a state must be computed **after**
   all its dependencies. For 0/1 knapsack, iterating capacity **top
   to bottom** avoids reusing an item.
2. **Incomplete state.** If two different contexts lead to different
   answers, the state must distinguish them. An under-specified state
   gives wrong answers.
3. **Deep recursion.** In top-down, the Python stack can overflow
   (`sys.setrecursionlimit`); tabulation avoids it.
4. **Pseudo-polynomial.** $\Theta(nW)$ is not polynomial in the
   **input size**: for $W = 10^{18}$, capacity-indexed DP is
   unusable; another approach is then needed.

---

## 3.5 - Recognizing a DP

Ask: "what is the smallest set of parameters that fully describes a
subproblem?" Those parameters are the **state**. Then: "how is a
state derived from smaller states?" That is the **transition**. Once
these two are fixed, the top-down / bottom-up choice is just a matter
of style and memory.

---

## 3.6 - Exercises

:::exercise{id="{{EX_PA_LIS}}"}
:::

:::exercise{id="{{EX_PA_KNAPSACK}}"}
:::

:::exercise{id="{{EX_PA_EDIT}}"}
:::
