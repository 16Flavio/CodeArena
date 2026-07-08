# 2. Sieves, Primality & CRT

## 2.1 - Intuition

Three questions come up everywhere in number theory: enumerate the
primes up to $n$, test whether **one** large number is prime, and glue
modular information back together. Three tools answer them, each with
its usage range.

- The **sieve of Eratosthenes** lists all primes $\le n$.
- **Miller-Rabin** tests a single gigantic $n$.
- The **Chinese remainder theorem** (CRT) merges congruences.

---

## 2.2 - Algorithms

### Sieve of Eratosthenes

```python
def sieve(n):
    is_comp = bytearray(n + 1)
    primes = []
    for i in range(2, n + 1):
        if not is_comp[i]:
            primes.append(i)
            for j in range(i * i, n + 1, i):   # mark from i^2 on
                is_comp[j] = 1
    return primes
```

**Step through the sieve**: at each step take the next unmarked number
(prime, in green), then cross out its multiples starting at its square.

:::viz-sieve{n="60"}
:::

### Miller-Rabin

Write $n - 1 = 2^r d$ with $d$ odd. For a witness $a$, if
$a^d \not\equiv 1$ and $a^{2^i d} \not\equiv -1$ for all $i < r$, then
$n$ is **composite** (a witness of non-primality). With witnesses
$\{2, 3, 5, \dots, 37\}$, the test is **deterministic** below
$3{.}3 \cdot 10^{24}$.

### Chinese remainder theorem

Two congruences $x \equiv a_1 \pmod{m_1}$ and $x \equiv a_2
\pmod{m_2}$ merge into one modulo $\text{lcm}(m_1, m_2)$,

$$
\text{provided that}\quad \gcd(m_1, m_2) \mid (a_2 - a_1),
$$

otherwise the system is inconsistent. Merge the $k$ congruences one by
one.

---

## 2.3 - Complexity

$$
\begin{aligned}
\text{sieve} &: \Theta(n \log \log n), \\
\text{Miller-Rabin} &: \Theta(t \log^2 n)\ \text{(} t \text{ witnesses)}, \\
\text{CRT (}k\text{ congruences)} &: \Theta(k \log M).
\end{aligned}
$$

The sieve is $\Theta(n)$ memory; Miller-Rabin stores nothing and
handles up to $10^{18}$ where the sieve would blow up.

---

## 2.4 - Common pitfalls

1. **Sieving for a single large number.** Useless and impossible in
   memory; to test one huge $n$, use Miller-Rabin.
2. **Carmichael numbers.** $561 = 3 \cdot 11 \cdot 17$ fools the naive
   Fermat test; Miller-Rabin detects them.
3. **CRT with non-coprime moduli.** The general version requires the
   divisibility condition; ignoring it yields false solutions.
4. **Overflow in the CRT merge.** The product $m_1 \cdot t$ can be
   huge; in typed languages, watch the intermediate modulus.

---

## 2.5 - The bedrock of number theory

Factorization (by sieving smallest prime factors, or Pollard rho for
large ones), Euler's totient, solving modular systems, reconstructing a
large result from small prime moduli: all rest on these three bricks.
Pick the right one depending on whether you enumerate, test, or glue.

---

## 2.6 - Exercises

:::exercise{id="{{EX_MA_SIEVE_COUNT}}"}
:::

:::exercise{id="{{EX_MA_MILLER_RABIN}}"}
:::

:::exercise{id="{{EX_MA_CRT}}"}
:::
