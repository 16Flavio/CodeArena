# 4. Trie (Prefix Tree)

## 4.1 - Intuition

How do you organize a dictionary to quickly answer "how many words
start with `pre`?". A **trie** (prefix tree) stores words by sharing
their common prefixes: the root is the empty word, each edge carries a
character, and descending spells a prefix.

Two words sharing a prefix share the corresponding path. This sharing
makes prefix queries natural - and, applied to the **bits** of an
integer, unlocks XOR tricks.

---

## 4.2 - Algorithm

```python
class Trie:
    def __init__(self):
        self.child = [{}]     # child[node][c] -> node
        self.cnt = [0]        # number of words passing through this node

    def _new(self):
        self.child.append({}); self.cnt.append(0)
        return len(self.child) - 1

    def insert(self, word):
        cur = 0
        for c in word:
            if c not in self.child[cur]:
                self.child[cur][c] = self._new()
            cur = self.child[cur][c]
            self.cnt[cur] += 1

    def count_prefix(self, pref):
        cur = 0
        for c in pref:
            if c not in self.child[cur]:
                return 0
            cur = self.child[cur][c]
        return self.cnt[cur]
```

**Step through a search**: descend character by character; the path turns green if it exists, red at the first missing edge.

:::viz-trie{words="car,card,cart,dog,do,dot" query="cart"}
:::

### The binary trie

By storing an integer through its bits (most significant first), you
get a **binary trie** with two children per node. To maximize
$x \oplus y$, descend choosing at each bit the edge **opposite** to
$x$'s bit when it exists: each bit fixed this way contributes $2^b$ to
the result.

---

## 4.3 - Complexity

$$
\begin{aligned}
\text{insert / search} &: \Theta(L)\ \text{(word length)}, \\
\text{prefix count} &: \Theta(|\text{prefix}|), \\
\text{maximum XOR (binary trie)} &: \Theta(B)\ \text{(number of bits)}.
\end{aligned}
$$

Memory is $\Theta(\sum L)$ in the worst case (no shared prefix), but
drops as soon as words resemble each other.

---

## 4.4 - Common pitfalls

1. **Misplaced counter.** For prefix counting, increment `cnt` on
   **every** traversed node, not only on the leaf.
2. **Fixed bit count.** For the binary trie, choose enough bits to
   cover the maximum value (30 bits for $\le 10^9$).
3. **Memory blowup.** A per-node `dict` is flexible but heavy; a
   fixed-size array (26 letters, 2 bits) is faster when the alphabet
   is small.
4. **Missing prefix.** Return $0$ (or a sentinel) as soon as an edge
   is missing, without crashing.

---

## 4.5 - Prefixes and bits

Autocompletion, dictionaries, spell-checking sit alongside bitwise
tricks: maximum XOR of a pair, maximum XOR of a subarray (via prefix
XORs), nearest neighbor in Hamming distance. The trie links these two
worlds - textual and binary - through one idea: **descend character by
character**.

---

## 4.6 - Exercises

:::exercise{id="{{EX_DS_TRIE_PREFIX}}"}
:::

:::exercise{id="{{EX_DS_TRIE_XOR}}"}
:::

:::exercise{id="{{EX_DS_MAX_XOR_SUBARRAY}}"}
:::
