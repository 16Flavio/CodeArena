# 2. Loop Analysis & Useful Sums

## 2.1 - The core idea

The cost of a loop is the **sum** of the costs of its iterations. To
analyse an algorithm with nested loops, we translate each level into a
sum and simplify. Three sums show up everywhere.

## 2.2 - The three sums to know by heart

### Arithmetic sum

$$
\sum_{i=1}^{n} i = \frac{n(n+1)}{2} = \Theta(n^2).
$$

**Elegant proof (Gauss).** Write the sum twice, in opposite directions,
and add column by column:

$$
\begin{aligned}
S &= 1 + 2 + \dots + (n-1) + n \\
S &= n + (n-1) + \dots + 2 + 1 \\
\hline
2S &= \underbrace{(n+1) + (n+1) + \dots + (n+1)}_{n \text{ terms}} = n(n+1).
\end{aligned}
$$

Hence $S = n(n+1)/2$. $\square$

### Geometric sum

$$
\sum_{i=0}^{n-1} r^i = \begin{cases} \dfrac{r^n - 1}{r - 1} & \text{if } r \ne 1 \\ n & \text{if } r = 1. \end{cases}
$$

For $r > 1$ we have $\sum_{i=0}^{n-1} r^i = \Theta(r^n)$: the **last
term dominates**. This intuition is crucial when analysing recursion.

### Harmonic sum

$$
H_n = \sum_{i=1}^{n} \frac{1}{i} = \ln n + \gamma + O(1/n)\quad \text{with } \gamma \approx 0.5772.
$$

So $H_n = \Theta(\log n)$. This is the worst-case cost of operations
like "insert into a binary heap", or the average depth of a random BST.

**Proof (sketch).** Squeeze the sum between two integrals:

$$
\int_1^{n+1} \frac{dx}{x} \le \sum_{i=1}^{n} \frac{1}{i} \le 1 + \int_1^{n} \frac{dx}{x},
$$

i.e. $\ln(n+1) \le H_n \le 1 + \ln n$. $\square$

---

## 2.3 - Three analysis patterns

### Triangular nested loops

```python
total = 0
for i in range(n):           # n iterations
    for j in range(i):       # i iterations (variable!)
        total += 1
```

Total cost:

$$
T(n) = \sum_{i=0}^{n-1} i = \frac{n(n-1)}{2} = \Theta(n^2).
$$

**Visual example**: selection sort has exactly this triangular nested
structure, hence its quadratic complexity.

:::viz-sort{algo="selection" data="[5,2,8,1,9,3,7,4]"}
:::

### Multiplicative loop

```python
i = 1
while i <= n:
    # O(1) body
    i *= 2
```

Index $i$ takes values $1, 2, 4, 8, \dots, 2^k$ with $2^k \le n$.
So $k = \lfloor \log_2 n \rfloor$ and the iteration count is
$\lfloor \log_2 n \rfloor + 1 = \Theta(\log n)$.

### Nested logarithmic loop

```python
for i in range(n):           # n
    j = 1
    while j <= n:
        j *= 2               # log n
```

Cost: $T(n) = n \cdot \log_2 n = \Theta(n \log n)$.

> **Useful heuristic.** When an index is *divided* (or multiplied) by a
> constant $> 1$, the cost is logarithmic. When it's *decremented* by a
> constant, it's linear.

---

## 2.4 - Exercises

:::exercise{id="{{EX_LOOP_STD}}"}
:::

:::exercise{id="{{EX_LOOP_TWIST}}"}
:::

:::exercise{id="{{EX_LOOP_HARD}}"}
:::
