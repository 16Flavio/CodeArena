# 2. Hash Tables

## 2.1 - The idea: skip the sort

We want a structure supporting `insert(k, v)`, `lookup(k)`, and
`delete(k)` in $\Theta(1)$ **on average**, with no order maintenance.

Trick: a function $h : \mathcal{U} \to \{0, 1, \dots, m-1\}$ that
maps each key to an array index. We store $(k, v)$ in `T[h(k)]`. If
$h$ scatters keys well, access is near-instant.

> **The catch.** For any fixed $h$ and any adversary who knows it,
> we can craft $n$ keys all colliding into the same bucket -
> performance degrades to $\Theta(n)$. Hence **universal hashing**
> (a random family).

---

## 2.2 - Universal hashing

### Definition

A family $\mathcal{H}$ of functions $h : \mathcal{U} \to [m]$ is
**universal** iff for any two distinct keys $x \neq y$:

$$
\Pr_{h \sim \mathcal{H}}[h(x) = h(y)] \le \frac{1}{m}.
$$

The randomness is over the choice of $h$, **not** the keys. Once
$h$ is drawn, it is fixed for the lifetime of the table.

### Example: linear modular family

Let $p$ be prime $> |\mathcal{U}|$. For $a \in \{1, \dots, p-1\}$
and $b \in \{0, \dots, p-1\}$:

$$
h_{a,b}(k) = ((a\,k + b) \bmod p) \bmod m.
$$

**Theorem.** $\mathcal{H} = \{h_{a,b}\}$ is universal.

*Sketch.* For $x \neq y$, $((ax + b) \bmod p) - ((ay + b) \bmod p)
\equiv a(x - y) \pmod p$ takes all non-zero values uniformly as
$a$ varies. The $\bmod m$ projection adds at most $\lceil p/m
\rceil / p \le 1/m + \varepsilon$ collision probability. $\square$

---

## 2.3 - Collision resolution

Two philosophies:

### Chaining

Each bucket `T[i]` is a (linked) list of pairs `(k, v)` with
$h(k) = i$.

```python
def insert(T, k, v, h):
    T[h(k)].append((k, v))      # or .replace if k exists

def lookup(T, k, h):
    for (kk, vv) in T[h(k)]:
        if kk == k: return vv
    return None
```

**Expected cost** (universal $\mathcal{H}$, $n$ keys, $m$ buckets,
**load factor** $\alpha = n/m$):

$$
\mathbb{E}[\text{bucket size of target}] \le 1 + \alpha.
$$

When $\alpha = O(1)$, `lookup` is $\Theta(1)$ in expectation. To
keep $\alpha$ bounded, **resize** the table (cf. dynamic array,
ch. 1).

:::viz-hash-table{keys="5,12,19,7,42,26,33"}
:::

Play with it: insert more keys, change $m$. The smaller $m$, the
longer the chains; collisions are highlighted in red.

### Open addressing (linear probing)

Store directly in the array; on collision, probe the next cell:

```python
def insert(T, k, v, h, m):
    i = h(k) % m
    while T[i] is not None and T[i].k != k:
        i = (i + 1) % m
    T[i] = Entry(k, v)
```

**Pros**: better cache locality, no pointers.

**Cons**:
- Performance collapses as $\alpha \to 1$ - must resize early
  (typically $\alpha < 0.7$).
- Deletion is non-trivial: you can't `None` a removed slot without
  breaking future probes; use a **tombstone** marker.

**Expected cost** (linear probing, universal hashing):

$$
\mathbb{E}[\text{probes per lookup}] = \Theta\left(\frac{1}{(1 - \alpha)^2}\right).
$$

Knuth's estimate for an unsuccessful search is $\frac{1}{2}\left(1
+ \frac{1}{(1-\alpha)^2}\right)$: about $2.5$ probes at $\alpha =
0.5$, about $50.5$ at $\alpha = 0.9$ - hence the early-resize rule.

### Comparison

| Criterion | Chaining | Open addressing |
|-----------|----------|-----------------|
| Avg lookup | $\Theta(1 + \alpha)$ | $\Theta(1/(1-\alpha)^2)$ |
| Memory | + pointers | none |
| Cache | poor | excellent |
| Practical $\alpha$ | up to $\sim 1$ | $< 0.7$ |
| Deletion | trivial | tombstones |

---

## 2.4 - Algorithm: `lookup` with chaining + complexity proof

### Code

```python
def lookup(T, k):
    h = T.hash(k)
    bucket = T.buckets[h]
    for (kk, vv) in bucket:     # linear scan
        if kk == k:
            return vv
    return None
```

### Expected number of comparisons

Let $n$ keys be stored across $m$ buckets, universal hashing. Search
for key $k$ (present or absent). For each other stored key $k' \neq
k$, set $X_{k'} = \mathbf{1}[h(k') = h(k)]$.

Comparisons $= 1 + \sum_{k' \neq k} X_{k'}$ (the key itself or the
end sentinel, plus each collision).

By universality: $\mathbb{E}[X_{k'}] \le 1/m$.

$$
\mathbb{E}[\text{comparisons}] \le 1 + \sum_{k' \neq k} \frac{1}{m} \le 1 + \frac{n}{m} = 1 + \alpha.
$$

Maintaining $\alpha = O(1)$ via resizing yields lookup in
$\Theta(1)$ expected. $\square$

> **Subtlety.** The worst case is still $\Theta(n)$: an adversary
> who *sees* $h$ after the draw can craft an attack. In production,
> use **cryptographic hashing** (SipHash in Python since 3.4) or
> keyed hash functions.

---

## 2.5 - Exercises

:::exercise{id="{{EX_HT_DISTINCT}}"}
:::

:::exercise{id="{{EX_HT_TWOSUM}}"}
:::

:::exercise{id="{{EX_HT_ZEROSUM}}"}
:::
