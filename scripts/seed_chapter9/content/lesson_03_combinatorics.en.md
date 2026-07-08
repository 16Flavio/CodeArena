# 3. Modular Combinatorics

## 3.1 - Intuition

Counting is the heart of combinatorial algorithmics: how many subsets,
paths, arrangements? The answer almost always runs through the
**binomial coefficient** $\binom{n}{k}$, the number of ways to choose
$k$ objects among $n$. Since these numbers explode, we compute them
**modulo** a prime $p$.

The method changes with scale: precomputed factorials for reasonable
$n$, **Lucas' theorem** when $n$ exceeds $p$, closed forms for
remarkable families like the Catalan numbers.

---

## 3.2 - Algorithms

### Binomial via factorials (case $p > n$)

$$
\binom{n}{k} = \frac{n!}{k!\,(n-k)!} \bmod p.
$$

```python
def binom(n, k, p):                 # p prime, p > n
    if k < 0 or k > n: return 0
    num = den = 1
    for i in range(k):
        num = num * (n - i) % p
        den = den * (i + 1) % p
    return num * pow(den, p - 2, p) % p    # inverse by Fermat
```

Precomputing factorials and inverses makes each query $O(1)$.

**Build Pascal's triangle**: each interior cell is the sum of its two
parents, $C(n,k) = C(n-1,k-1) + C(n-1,k)$.

:::viz-pascal{n="8"}
:::

### Lucas' theorem (case $n \ge p$)

Write $n$ and $k$ in base $p$: $n = \sum n_i p^i$, $k = \sum k_i p^i$.
Then

$$
\binom{n}{k} \equiv \prod_i \binom{n_i}{k_i} \pmod p.
$$

Each digit $n_i, k_i$ is $< p$, so each small binomial is computed
directly. If any $k_i > n_i$, the product is zero.

### Catalan numbers

$$
C_n = \frac{1}{n+1} \binom{2n}{n}.
$$

They count binary trees with $n$ nodes, valid parenthesizations, Dyck
paths, triangulations of a polygon...

---

## 3.3 - Complexity

$$
\begin{aligned}
\text{binomial (precomputed factorials)} &: \Theta(1)\ \text{per query}, \\
\text{Lucas} &: \Theta(\log_p n \cdot p), \\
\text{Catalan} &: \Theta(n)\ \text{(via factorials)}.
\end{aligned}
$$

Lucas reduces a computation on $n \sim 10^{18}$ to a handful of small
binomials - the only way when $p$ is small.

---

## 3.4 - Common pitfalls

1. **Dividing modulo p.** You never divide directly; you multiply by
   the modular inverse. Forgetting the inverse gives a wrong result.
2. **$p \le n$ without Lucas.** If $p \le n$, a factor of $p$ appears
   in $n!$ and the denominator's inverse no longer exists: you **must**
   use Lucas.
3. **Catalan with small $p$.** $\frac{1}{n+1}$ has an inverse only if
   $p \nmid (n+1)$; guarantee $p > 2n$ or use the recurrence.
4. **Bounds on $k$.** Explicitly handle $k < 0$ and $k > n$ (value
   $0$), or the loops misbehave.

---

## 3.5 - Counting, again and again

Arrangements, combinations with repetition (**stars and bars**),
inclusion-exclusion, Stirling and Bell numbers, Burnside counting under
symmetry: all of enumerative combinatorics rests on a reliable modular
binomial. Choosing the right method by the size of $n$ against $p$ is
the central reflex.

---

## 3.6 - Exercises

:::exercise{id="{{EX_MA_BINOM}}"}
:::

:::exercise{id="{{EX_MA_LUCAS}}"}
:::

:::exercise{id="{{EX_MA_CATALAN}}"}
:::
