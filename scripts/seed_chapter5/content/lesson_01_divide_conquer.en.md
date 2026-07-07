# 1. Divide and Conquer

## 1.1 - Intuition

A problem of size $n$ can be too big to attack head-on, yet become
trivial once cut into pieces. The **divide and conquer** schema
repeats three moves:

1. **Divide**: split the instance into smaller sub-instances,
   typically two halves.
2. **Conquer**: solve each sub-instance recursively.
3. **Combine**: stitch the sub-solutions into a solution of the
   original problem.

Merge sort is the archetype: sort two halves, then **merge** them in
linear time. The paradigm's power comes from combining work - often
linear - being amortized over a logarithmic recursion height.

---

## 1.2 - Algorithm & master theorem

Here is merge sort, whose structure serves as the template for the
whole lesson.

```python
def merge_sort(a):
    if len(a) <= 1:
        return a
    mid = len(a) // 2
    left = merge_sort(a[:mid])       # conquer (left)
    right = merge_sort(a[mid:])      # conquer (right)
    return merge(left, right)        # combine in O(n)
```

The cost follows a **recurrence**: two calls on $n/2$, plus a linear
merge.

$$
T(n) = 2\,T(n/2) + \Theta(n).
$$

### Master theorem

For a recurrence of the form

$$
T(n) = a\,T(n/b) + \Theta(n^d), \qquad a \ge 1,\ b > 1,\ d \ge 0,
$$

compare the growth of the leaves ($n^{\log_b a}$) with that of the
combine work ($n^d$):

$$
T(n) = \begin{cases}
\Theta(n^d) & \text{if } d > \log_b a, \\
\Theta(n^d \log n) & \text{if } d = \log_b a, \\
\Theta(n^{\log_b a}) & \text{if } d < \log_b a.
\end{cases}
$$

**Proof (sketch).** The recursion tree has $a^k$ nodes at level $k$,
each of size $n / b^k$, hence combine work
$a^k \cdot \Theta((n/b^k)^d)$. Summing over the $\log_b n$ levels
gives a geometric series with ratio $a / b^d$. Depending on whether
this ratio is $< 1$, $= 1$, or $> 1$, the sum is dominated by the
root, evenly spread, or dominated by the leaves. $\square$

For merge sort, $a = 2$, $b = 2$, $d = 1$, so
$\log_b a = 1 = d$: the tie case, $T(n) = \Theta(n \log n)$.

---

## 1.3 - Complexity

The case table above reads as a decision rule. The classic
recurrences:

- **Binary search**: $T(n) = T(n/2) + \Theta(1)$, i.e.
  $a = 1, b = 2, d = 0$: $\Theta(\log n)$.
- **Merge sort / counting inversions**: $\Theta(n \log n)$.
- **Karatsuba multiplication**: $T(n) = 3\,T(n/2) + \Theta(n)$,
  $\log_2 3 \approx 1{.}585 > 1$: $\Theta(n^{1.585})$, better than the
  schoolbook $\Theta(n^2)$ product.

$$
\boxed{\;T(n) = 2\,T(n/2) + \Theta(n) = \Theta(n \log n)\;}
$$

---

## 1.4 - Common pitfalls

1. **Forgetting the base case.** A recursion with no stop condition
   on $n \le 1$ does not terminate.
2. **Combine step too expensive.** If the merge becomes
   $\Theta(n^2)$, the gain evaporates: $T(n) = 2T(n/2) + n^2 =
   \Theta(n^2)$. The stitching work is the real stake.
3. **Array copies.** In Python, `a[:mid]` copies; on large $n$ this
   adds a constant factor. Pass indices `(lo, hi)` rather than slices
   when memory matters.
4. **Midpoint overflow.** `(lo + hi) // 2` is safe in Python; in
   C++/Java on `int`, prefer `lo + (hi - lo) // 2`.

---

## 1.5 - Beyond sorting

Divide and conquer reaches far past sorting: closest pair of points
in $\Theta(n \log n)$, the fast Fourier transform (FFT) to convolve
two sequences in $\Theta(n \log n)$, fast exponentiation in
$\Theta(\log n)$. The common thread stays the same: find a split
where combining is cheap.

---

## 1.6 - Exercises

:::exercise{id="{{EX_PA_INVERSIONS}}"}
:::

:::exercise{id="{{EX_PA_MAXSUB}}"}
:::

:::exercise{id="{{EX_PA_REVPAIRS}}"}
:::
