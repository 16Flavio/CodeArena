# 1. String Hashing (Rabin-Karp)

## 1.1 - Intuition

Comparing two strings of length $L$ costs $O(L)$. If you must compare
thousands of windows, that gets slow. The **hashing** idea: summarize
each string by a **number**; two equal strings have the same hash, and
two different hashes guarantee two different strings. Comparison
becomes $O(1)$.

**Polynomial** hashing sees a string as the digits of a number in base
$B$:

$$
h(s) = \bigl(s_0 B^{L-1} + s_1 B^{L-2} + \dots + s_{L-1}\bigr) \bmod M.
$$

Its power: the hash of a sliding window updates in $O(1)$ as you move
one character - that is **Rabin-Karp**.

---

## 1.2 - Algorithm

```python
def count_occurrences(t, p):
    n, m = len(t), len(p)
    if m > n: return 0
    MOD = (1 << 61) - 1; B = 131
    hp = 0
    for c in p: hp = (hp * B + ord(c)) % MOD      # pattern hash
    power = pow(B, m - 1, MOD)
    h = 0
    for i in range(m): h = (h * B + ord(t[i])) % MOD
    cnt = 0
    for i in range(m - 1, n):
        if i >= m:                                # slide the window
            h = ((h - ord(t[i-m]) * power) * B + ord(t[i])) % MOD
        if h == hp and t[i-m+1:i+1] == p:         # verification
            cnt += 1
    return cnt
```

### Collisions and double hashing

Two different strings can share a hash: a **collision**. For a single
modulus $\sim 10^9$, comparing many pairs eventually produces one. The
fix: a **double hash** (two prime moduli $M_1, M_2$), lowering the
probability to $\sim 1/(M_1 M_2)$, negligible. When correctness is
critical, verify the match character by character.

---

## 1.3 - Complexity

$$
\begin{aligned}
\text{preprocessing} &: \Theta(|P|), \\
\text{text scan} &: \Theta(|T|), \\
\text{per window} &: \Theta(1)\ \text{(hash update)}.
\end{aligned}
$$

That is $\Theta(|T| + |P|)$ total, like the dedicated algorithms of the
next lesson - but with a constant often simpler to code.

---

## 1.4 - Common pitfalls

1. **Base or modulus too small.** A modulus of $\sim 10^9$ collides
   once you compare $\sim 10^{4.5}$ pairs (birthday paradox). Prefer
   $M \approx 2^{61} - 1$ or a double hash.
2. **Overflow.** In C++/Java, multiplying two 64-bit integers
   overflows; use `__int128` or a modulus fitting in 32 bits.
3. **Mispowered.** `power = B^(m-1)` must match the exact window
   length.
4. **Blind trust.** For an exact, critical answer, confirm a match with
   a direct comparison.

---

## 1.5 - A versatile tool

Pattern search, counting distinct substrings, longest common substring
(via binary search on the length), $O(1)$ substring comparison after
preprocessing: hashing attacks a host of problems with minimal code.
You just have to stay aware of the collision risk.

---

## 1.6 - Exercises

:::exercise{id="{{EX_TX_RK_COUNT}}"}
:::

:::exercise{id="{{EX_TX_DISTINCT_SUBSTR_K}}"}
:::

:::exercise{id="{{EX_TX_LONGEST_COMMON_SUBSTR}}"}
:::
