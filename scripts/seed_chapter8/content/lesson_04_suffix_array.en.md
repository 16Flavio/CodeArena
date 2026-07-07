# 4. Suffix Array & LCP

## 4.1 - Intuition

Many questions about a string - distinct substrings, repetitions,
search - reduce to **all its suffixes**. Listing them explicitly costs
$O(n^2)$ memory. The **suffix array** represents them by their starting
indices alone, **sorted** in lexicographic order, in $O(n)$ memory.

Once the suffixes are sorted, two suffixes that resemble each other are
**neighbors** in the array. The **LCP** array (*Longest Common
Prefix*) measures, between adjacent suffixes, the length of the common
prefix - the key to almost every application.

---

## 4.2 - Algorithm

### Prefix-doubling construction

Sort the suffixes by their first $2^k$ characters, reusing the ranks
from the previous step: the rank by $2^k$ characters is the pair (rank
by $2^{k-1}$ of the left half, rank of the right half).

```python
def suffix_array(s):
    n = len(s)
    sa = list(range(n))
    rank = [ord(c) for c in s]
    k = 1
    while True:
        sa.sort(key=lambda i: (rank[i], rank[i + k] if i + k < n else -1))
        tmp = [0] * n
        for i in range(1, n):
            prev, cur = sa[i-1], sa[i]
            same = (rank[prev], rank[prev+k] if prev+k < n else -1) == \
                   (rank[cur],  rank[cur+k]  if cur+k  < n else -1)
            tmp[cur] = tmp[prev] + (0 if same else 1)
        rank = tmp
        if rank[sa[-1]] == n - 1:
            break
        k *= 2
    return sa
```

### LCP via Kasai's algorithm

By scanning the suffixes in text order (not array order), the common
prefix length drops by at most 1 per step, yielding the LCP array in
$O(n)$.

---

## 4.3 - Complexity

$$
\begin{aligned}
\text{suffix array (doubling)} &: \Theta(n \log^2 n), \\
\text{counting-sort variant} &: \Theta(n \log n), \\
\text{LCP (Kasai)} &: \Theta(n).
\end{aligned}
$$

Linear-time constructions exist (DC3, SA-IS) but are trickier;
doubling suffices in the vast majority of cases.

---

## 4.4 - Common pitfalls

1. **Suffixes of different lengths.** A shorter suffix that is a prefix
   of another ranks **before** it; hence the $-1$ rank for the missing
   half.
2. **Mis-indexed LCP.** Common convention: `lcp[i]` = common prefix of
   `sa[i-1]` and `sa[i]`, with `lcp[0] = 0`.
3. **Kasai works from ranks.** The algorithm scans **text** positions,
   relying on the inverse rank; swapping the two breaks the linear
   bound.
4. **Distinct substrings.** The formula $\frac{n(n+1)}{2} - \sum
   \text{LCP}$ counts the total minus already-seen prefixes - check the
   sum's indexing.

---

## 4.5 - The ultimate string structure

Suffix array + LCP solve: number of distinct substrings, longest
repeated substring, longest substring common to several texts, pattern
search in $O(|P| \log n)$. Where a trie of suffixes would blow up in
memory, the suffix array fits in an integer array - the reference
structure for large-scale string algorithms.

---

## 4.6 - Exercises

:::exercise{id="{{EX_TX_SUFFIX_ARRAY}}"}
:::

:::exercise{id="{{EX_TX_DISTINCT_SUBSTR_TOTAL}}"}
:::

:::exercise{id="{{EX_TX_LRS}}"}
:::
