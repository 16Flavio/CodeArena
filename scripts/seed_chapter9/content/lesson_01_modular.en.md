# 1. Modular Arithmetic

## 1.1 - Intuition

In competition, answers often exceed integer capacity: the number of
paths, of configurations, of ways... So you work **modulo** a large
number $m$ (often prime), that is, on the remainders of division by
$m$. Modular arithmetic keeps every computation bounded while
preserving addition, subtraction, and multiplication.

Division, however, needs a detour: dividing by $a$ amounts to
multiplying by its **inverse** $a^{-1}$, the unique number with
$a \cdot a^{-1} \equiv 1 \pmod m$. Two tools dominate the lesson: fast
exponentiation and inverse computation.

---

## 1.2 - Algorithms

### Fast exponentiation

```python
def modexp(a, b, m):
    result = 1
    a %= m
    while b > 0:
        if b & 1:
            result = result * a % m
        a = a * a % m
        b >>= 1
    return result
```

Decompose $b$ in binary: each bit doubles the exponent. Hence
$O(\log b)$ multiplications.

**Step through fast exponentiation**: each bit of $b$, from lowest to
highest, squares the base and multiplies it into the result when the
bit is 1.

:::viz-fast-exp{a="3" b="13" m="1000"}
:::

### Modular inverse

Two methods:

- **Fermat** (if $m$ prime): $a^{-1} \equiv a^{m-2} \pmod m$, by
  Fermat's little theorem $a^{m-1} \equiv 1$.
- **Extended Euclid** (general case): it computes $x, y$ with

$$
a x + m y = \gcd(a, m).
$$

If $\gcd(a, m) = 1$, then $x \bmod m$ is the inverse. The inverse
**exists only if** $\gcd(a, m) = 1$.

---

## 1.3 - Complexity

$$
\begin{aligned}
\text{fast exponentiation} &: \Theta(\log b), \\
\text{extended Euclid} &: \Theta(\log \min(a, m)), \\
\text{linear congruence} &: \Theta(\log m).
\end{aligned}
$$

All these operations are **logarithmic**: they stay instant even for
moduli of $10^{18}$.

---

## 1.4 - Common pitfalls

1. **Overflow.** In C++/Java, $a \cdot a$ for $a \sim 10^9$ overflows a
   `long long`; use `__int128` or a modulus fitting in 32 bits. In
   Python, no issue.
2. **Fermat out of context.** $a^{m-2}$ is an inverse only if $m$ is
   **prime**. For a composite $m$, use extended Euclid.
3. **Nonexistent inverse.** If $\gcd(a, m) \ne 1$, the inverse does not
   exist - report it rather than returning a wrong value.
4. **Negative remainders.** After a subtraction, bring back into
   $[0, m)$ with `% m` (in Python, `%` already returns a positive
   remainder).

---

## 1.5 - A foundational brick

Exponentiation and inverse underpin almost the whole chapter: modular
binomial coefficients (lesson 3), NTT (lesson 4), primality tests
(lesson 2). Linear congruences and the Chinese remainder theorem
follow directly. Mastering these two moves is half the toolbox.

---

## 1.6 - Exercises

:::exercise{id="{{EX_MA_MODEXP}}"}
:::

:::exercise{id="{{EX_MA_MODINV}}"}
:::

:::exercise{id="{{EX_MA_LINCONG}}"}
:::
