# 4. Convolutions (FFT / NTT)

## 4.1 - Intuition

Multiplying two polynomials, or more generally computing a
**convolution**

$$
(A * B)[s] = \sum_{i + j = s} A_i \, B_j,
$$

naively costs $O(nm)$. Yet this operation is everywhere: polynomial
product, distribution of a sum of variables, counting pairs by value.
The **fast Fourier transform** (FFT) brings it down to $O(n \log n)$.

The trick: a polynomial can be represented either by its
**coefficients** or by its **values** at well-chosen points. In the
value representation, multiplying two polynomials is a simple pointwise
product. The FFT converts between the two representations in
$O(n \log n)$.

---

## 4.2 - Algorithm

### The general scheme

$$
A * B = \text{FFT}^{-1}\bigl(\text{FFT}(A) \odot \text{FFT}(B)\bigr),
$$

where $\odot$ is the pointwise product. The FFT evaluates at the
**roots of unity** $\omega^k$ by divide and conquer: split even and
odd indices, solve each half, recombine.

### NTT: the exact FFT

The floating FFT suffers rounding errors. The **NTT** (*Number
Theoretic Transform*) does the same thing modulo a well-chosen prime,
with a **primitive root** instead of $\omega$. The prime
$998244353 = 119 \cdot 2^{23} + 1$ is ideal: it admits roots of unity
of order $2^{23}$, covering sizes up to $2^{23}$ while staying
**exact** over the integers.

---

## 4.3 - Complexity

$$
\begin{aligned}
\text{naive convolution} &: \Theta(nm), \\
\text{FFT / NTT} &: \Theta\bigl((n+m) \log(n+m)\bigr).
\end{aligned}
$$

The gain is spectacular once $n$ exceeds a few thousand: going from
$10^{10}$ to $\sim 10^6$ operations.

---

## 4.4 - Common pitfalls

1. **Non-power-of-2 size.** The recursive FFT requires a length $2^k$;
   pad with zeros up to the next power of 2 $\ge n + m - 1$.
2. **Rounding errors (floating FFT).** For integer coefficients, prefer
   the NTT (exact) or round the result carefully.
3. **Incompatible modulus.** The NTT is exact only if the prime admits
   a root of unity of the required order; $998244353$ is the canonical
   choice.
4. **Size overflow.** The result has $n + m - 1$ coefficients; size the
   arrays accordingly.

---

## 4.5 - Far more than polynomials

Sum of random variables, polynomial exponentiation (sum of $n$ dice),
string matching with wildcards, big-integer multiplication, counting
subsets by sum: countless problems **reduce** to a convolution.
Recognizing the hidden convolution in a statement, then solving it by
NTT, is the flagship skill of this lesson.

---

## 4.6 - Exercises

:::exercise{id="{{EX_MA_POLYMUL}}"}
:::

:::exercise{id="{{EX_MA_PAIR_SUMS}}"}
:::

:::exercise{id="{{EX_MA_DICE}}"}
:::
