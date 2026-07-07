# 3. Recurrences & Master Theorem

## 3.1 - Why recurrences?

The complexity of a recursive algorithm is naturally written as a
**recurrence relation**:

- *Divide and conquer*: $T(n) = a\,T(n/b) + f(n)$ - $a$ subproblems of
  size $n/b$, plus a divide/combine cost $f(n)$.
- *Linear recursion*: $T(n) = T(n-1) + f(n)$.

Three solving techniques:

1. **Substitution** - guess, then prove by induction.
2. **Recursion tree** - sum the cost level by level.
3. **Master Theorem** - closed-form formula for divide-and-conquer recurrences.

---

## 3.2 - Substitution method

*Guess* the form of the solution and **prove** it by induction on $n$.

**Example.** Let $T(n) = 2T(n/2) + n$ with $T(1) = 1$. We guess
$T(n) = O(n \log n)$, i.e. $T(n) \le c\,n \log_2 n$ for some $c$ and
$n$ large enough.

*Inductive step.* Assume $T(n/2) \le c (n/2) \log_2(n/2)$. Then

$$
\begin{aligned}
T(n) &= 2T(n/2) + n \\
&\le 2 \cdot c (n/2) \log_2(n/2) + n \\
&= c\,n \log_2 n - c\,n + n \\
&\le c\,n \log_2 n
\end{aligned}
$$

as long as $c \ge 1$. *Base case*: pick $c$ large enough to cover it.
$\square$

> **How to use it.** Always reach **exactly** the target form. If you
> stop at $\le c\,n \log_2 n + n$, you proved nothing - the $+n$ must
> be absorbed into the constant.

---

## 3.3 - Recursion tree

For $T(n) = aT(n/b) + f(n)$ we draw the call tree:

- Root: cost $f(n)$.
- Level $k$: $a^k$ nodes, each of size $n/b^k$, total cost $a^k f(n/b^k)$.
- Depth: $\log_b n$ levels until we hit leaves of size $1$, which
  contribute $a^{\log_b n} = n^{\log_b a}$ to the total.

Total cost:

$$
T(n) = \underbrace{n^{\log_b a}}_{\text{leaves}} + \sum_{k=0}^{\log_b n - 1} a^k\, f(n/b^k).
$$

Depending on whether the sum is dominated by leaves, by the root, or
spread evenly across levels, we land in one of the **three cases** of
the Master Theorem.

---

## 3.4 - Master Theorem (statement)

**Theorem.** Let $T(n) = a\,T(n/b) + f(n)$ with $a \ge 1$, $b > 1$, and
$f(n)$ asymptotically positive. Set $\alpha = \log_b a$. Then:

| Case | Hypothesis on $f$ | Conclusion |
|------|-------------------|------------|
| **1** | $f(n) = O(n^{\alpha - \varepsilon})$ for some $\varepsilon > 0$ | $T(n) = \Theta(n^\alpha)$ |
| **2** | $f(n) = \Theta(n^\alpha)$ | $T(n) = \Theta(n^\alpha \log n)$ |
| **3** | $f(n) = \Omega(n^{\alpha + \varepsilon})$ for some $\varepsilon > 0$, with the **regularity** condition $a\,f(n/b) \le c\,f(n)$ for some $c < 1$ and large $n$ | $T(n) = \Theta(f(n))$ |

### Proof sketch

Use the recursion tree with total
$T(n) = n^\alpha + \sum_{k=0}^{\log_b n - 1} a^k f(n/b^k)$.

- **Case 1.** $f(n/b^k) \le C(n/b^k)^{\alpha-\varepsilon}$, so
  $a^k f(n/b^k) \le C\,n^{\alpha-\varepsilon} (a/b^{\alpha-\varepsilon})^k = C\,n^{\alpha-\varepsilon} b^{\varepsilon k}$.
  The sum is geometric with ratio $b^\varepsilon > 1$: dominated by its **last** term,
  which equals $C\,n^{\alpha-\varepsilon} \cdot b^{\varepsilon \log_b n} = C\,n^\alpha$.
  The leaves cost ($n^\alpha$) absorbs everything: $T(n) = \Theta(n^\alpha)$.
- **Case 2.** $f(n/b^k) = \Theta((n/b^k)^\alpha)$, so
  $a^k f(n/b^k) = \Theta(n^\alpha)$ at every level. Summing over the
  $\log_b n$ levels gives $\Theta(n^\alpha \log n)$.
- **Case 3.** Regularity $a f(n/b) \le c f(n)$ with $c < 1$ implies that
  levels **shrink geometrically**, and the sum is dominated by the
  **first** term $f(n)$: $T(n) = \Theta(f(n))$.

$\square$

### Canonical examples

| Recurrence | $a$, $b$, $f$ | $\alpha = \log_b a$ | Case | $T(n)$ |
|-----------|---------------|---------------------|------|--------|
| $T(n) = 2T(n/2) + n$ (merge sort) | $2,2,n$ | $1$ | 2 | $\Theta(n \log n)$ |
| $T(n) = 2T(n/2) + n^2$ | $2,2,n^2$ | $1$ | 3 | $\Theta(n^2)$ |
| $T(n) = 4T(n/2) + n$ | $4,2,n$ | $2$ | 1 | $\Theta(n^2)$ |
| $T(n) = 8T(n/2) + n^2$ | $8,2,n^2$ | $3$ | 1 | $\Theta(n^3)$ |
| $T(n) = 7T(n/2) + n^2$ (Strassen) | $7,2,n^2$ | $\log_2 7 \approx 2.81$ | 1 | $\Theta(n^{\log_2 7})$ |

> **Limit.** The Master Theorem **does not apply** when $f$ sits between
> two powers (e.g. $f(n) = n \log n$ with $\alpha = 1$). Fall back to
> the recursion tree or Akra-Bazzi.

---

## 3.5 - Bonus: Akra-Bazzi

**Theorem (Akra-Bazzi).** Let
$T(n) = \sum_{i=1}^{k} a_i\,T(n/b_i) + f(n)$
with $a_i > 0$, $b_i > 1$. Let $p$ be the unique real such that
$\sum_{i=1}^{k} a_i / b_i^{\,p} = 1$. Then

$$
T(n) = \Theta\!\left( n^p \left(1 + \int_1^n \frac{f(u)}{u^{p+1}}\,du \right)\right).
$$

Akra-Bazzi handles:
- recurrences with **multiple branches of different sizes** (e.g. $T(n) = T(n/3) + T(2n/3) + n$),
- $f(n)$ like $n \log n$ that the Master Theorem rejects.

**Example.** $T(n) = T(n/3) + T(2n/3) + n$. Solve
$1/3^p + (2/3)^p = 1$; the solution is $p = 1$. The integral gives
$\int_1^n du/u = \ln n$, so $T(n) = \Theta(n \log n)$. That's the
*balanced* quicksort complexity - exactly like merge sort.

---

## 3.6 - Exercises

:::exercise{id="{{EX_REC_STD}}"}
:::

:::exercise{id="{{EX_REC_TWIST}}"}
:::

:::exercise{id="{{EX_REC_HARD}}"}
:::
