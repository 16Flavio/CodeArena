# 2. KMP & Prefix Function

## 2.1 - Intuition

Naively searching for a pattern $P$ in a text $T$ restarts from scratch
at each shift: $O(|T| \cdot |P|)$. The waste is obvious - after a
failure, you **forget** everything you had just matched. The
**Knuth-Morris-Pratt** (KMP) algorithm never moves backward in the
text: when a character fails, it falls back to the longest
**already-matched prefix** that stays valid.

The secret is the pattern's **prefix function** $\pi$: $\pi[i]$ is the
length of the longest prefix of $P$ that is also a suffix of $P[0..i]$.
It encodes "where to resume" after a failure.

---

## 2.2 - Algorithm & proof

```python
def prefix_function(s):
    n = len(s); pi = [0] * n
    for i in range(1, n):
        j = pi[i-1]
        while j > 0 and s[i] != s[j]:
            j = pi[j-1]          # fall back to a shorter prefix
        if s[i] == s[j]:
            j += 1
        pi[i] = j
    return pi
```

To search for $P$ in $T$, compute $\pi$ on the string $P + \# + T$
(with $\#$ absent from the alphabet): each position where $\pi$ reaches
$|P|$ marks an occurrence.

- **Correctness.** The invariant: after reading $s[0..i]$, $j = \pi[i]$
  is the length of the longest prefix of $s$ equal to a suffix. The
  `while` loop tests candidates in decreasing order via the border
  chain $\pi[j-1]$, guaranteeing the longest valid one is found.
  $\square$

- **Amortization.** $j$ increases by at most $1$ per step and can
  decrease only $O(n)$ times in total: each `j = pi[j-1]` consumes a
  prior increase. So the total operations are linear.

---

## 2.3 - Complexity

$$
\begin{aligned}
\text{prefix function} &: \Theta(|P|), \\
\text{full search} &: \Theta(|T| + |P|).
\end{aligned}
$$

No backtracking in the text: each character is examined an amortized
constant number of times.

---

## 2.4 - Common pitfalls

1. **Forgotten separator.** When searching via $P + \# + T$, the
   separator $\#$ must be **outside** the alphabet, else a false match
   spans the boundary.
2. **$\pi$ indexing.** $\pi[i]$ concerns $s[0..i]$ **inclusive**; the
   transition starts from $\pi[i-1]$, not $\pi[i]$.
3. **Borders and period.** Confusing "longest border" ($\pi[n-1]$) and
   "period" ($n - \pi[n-1]$) is a frequent mistake.
4. **Border chain.** All borders are obtained by iterating $\pi[k-1]$
   down to 0 - do not stop at the first.

---

## 2.5 - Far more than searching

The prefix function answers a family of questions: smallest period,
all borders, compression by period, occurrence counts of each prefix,
building a pattern automaton. One $\pi$ array, computed in linear time,
and the whole repetitive structure of the pattern is readable.

---

## 2.6 - Exercises

:::exercise{id="{{EX_TX_KMP_POSITIONS}}"}
:::

:::exercise{id="{{EX_TX_MIN_PERIOD}}"}
:::

:::exercise{id="{{EX_TX_BORDERS}}"}
:::
