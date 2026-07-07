# 3. Z-function & Manacher

## 3.1 - Intuition

Two linear-time algorithms, one shared idea: **reuse work already
done** through a window that remembers the rightmost segment explored
so far.

- The **Z-function** measures, at each position, the longest common
  prefix with the start of the string.
- **Manacher** finds all palindromes by exploiting the symmetry of an
  already-known palindrome.

In both cases, a position inside the current window inherits a value
computed at its **mirror position**, avoiding a full restart.

---

## 3.2 - Algorithms

### Z-function

$z_i$ = length of the longest common prefix of $s$ and $s_i s_{i+1}
\dots$ (with $z_0 = 0$).

```python
def z_function(s):
    n = len(s); z = [0] * n
    l = r = 0                          # window [l, r) = rightmost prefix
    for i in range(1, n):
        if i < r:
            z[i] = min(r - i, z[i - l])  # inherit from the mirror
        while i + z[i] < n and s[z[i]] == s[i + z[i]]:
            z[i] += 1                    # extend
        if i + z[i] > r:
            l, r = i, i + z[i]
    return z
```

### Manacher

To handle even and odd palindromes uniformly, insert separators: `abc`
becomes `#a#b#c#`. Every palindrome of the transformed string has odd
length, and its **radius** in the transformed string equals the length
of the original palindrome. The window $[c - p, c + p]$ of the
rightmost palindrome plays the role of the Z-function's window
$[l, r]$.

---

## 3.3 - Complexity

$$
\begin{aligned}
\text{Z-function} &: \Theta(n), \\
\text{Manacher} &: \Theta(n).
\end{aligned}
$$

The argument is identical to KMP: the window's right edge $r$ never
moves backward and advances at most $n$ times, so the total extensions
are linear.

---

## 3.4 - Common pitfalls

1. **The $z_0$ convention.** Some definitions set $z_0 = n$, others
   $z_0 = 0$. Fix yours and stay consistent (here $0$).
2. **Manacher separators.** The `#` must border **both ends**;
   forgetting one shifts every radius.
3. **Radius vs length.** In the transformed string, the radius $p[i]$
   equals the original palindrome length directly - a frequent source
   of confusion.
4. **Mis-updated window.** Extend $[l, r]$ (or $[c, r]$) only when the
   new value strictly exceeds $r$.

---

## 3.5 - Two knives, a thousand cuts

The Z-function does pattern search, border counting, compression.
Manacher counts palindromes, finds the longest, tests symmetries.
Recognizing the **reusable window** is the common thread of this lesson
- the same spring as KMP, applied to two different questions.

---

## 3.6 - Exercises

:::exercise{id="{{EX_TX_ZFUNC}}"}
:::

:::exercise{id="{{EX_TX_LONGEST_PALINDROME}}"}
:::

:::exercise{id="{{EX_TX_COUNT_PALINDROMES}}"}
:::
