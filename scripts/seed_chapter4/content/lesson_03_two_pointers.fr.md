# 3. Two pointers

## 3.1 - Le patron

On entretient deux indices $i < j$ (ou $i$, $j$ aux extrémités du
tableau) et on les déplace **de façon monotone** : ils ne reculent
**jamais**. Cette monotonie est exactement ce qui fait passer un
algorithme de $O(n^2)$ à $O(n)$.

Le truc à voir : à chaque tour de boucle, on **élimine
définitivement** une position. Si l'algorithme effectue au plus
$2n$ déplacements de pointeurs au total, le coût est $O(n)$, peu
importe à quoi ressemble la logique interne.

---

## 3.2 - Variante 1 : extrémités opposées (tableau trié)

> Étant donné un tableau **trié** $A$ et une cible $T$, existe-t-il
> $i \neq j$ tels que $A[i] + A[j] = T$ ?

```python
def two_sum_sorted(A, T):
    i, j = 0, len(A) - 1
    while i < j:
        s = A[i] + A[j]
        if s == T:   return (i, j)
        elif s < T:  i += 1   # somme trop petite → augmenter A[i]
        else:        j -= 1   # somme trop grande → diminuer A[j]
    return None
```

### Pourquoi c'est correct ?

**Invariant.** Si la paire $(i^*, j^*)$ existe, alors elle
satisfait $i \le i^* \le j^* \le j$ tout au long de la boucle.

- Si $A[i] + A[j] < T$, alors $\forall k \le j,\ A[i] + A[k] \le
  A[i] + A[j] < T$. Aucune paire avec $i$ ne peut donner $T$ →
  on peut éliminer $i$, c'est-à-dire poser $i \mathrel{+}= 1$.
- Symétriquement pour $A[i] + A[j] > T$.
- Quand $i = j$, l'invariant force la paire à être perdue → pas de
  solution.

À chaque tour soit on retourne, soit on **réduit l'intervalle de
1**. Au plus $n$ itérations → **$O(n)$ après tri**.

---

## 3.3 - Variante 2 : pointeurs dans le même sens

> Soit un tableau d'entiers **positifs** $A$ et une cible $S$.
> Trouver la **plus petite** sous-tableau contigu de somme $\ge S$.

```python
def smallest_window_geq(A, S):
    i, total, best = 0, 0, len(A) + 1
    for j in range(len(A)):
        total += A[j]
        while total >= S:           # on contracte tant qu'on peut
            best = min(best, j - i + 1)
            total -= A[i]
            i += 1
    return best if best <= len(A) else 0
```

**Invariant.** À l'entrée du `while`, `total = A[i] + A[i+1] + …
+ A[j]` et `total < S` ⟹ il faut grandir la fenêtre côté droit.
Tant que `total >= S` on contracte : la fenêtre minimale
finissant en $j$ est trouvée à la sortie du `while`.

**Coût amorti.** $i$ ne recule jamais ; il est incrémenté au plus
$n$ fois sur tout l'algorithme. $j$ aussi. Total des opérations
$\le 2n = O(n)$.

> ⚠️ La méthode tombe à l'eau dès qu'on autorise des nombres
> **négatifs** : la somme n'est plus monotone en grandissant la
> fenêtre. Pour ce cas il faut autre chose (préfixes triés, deque
> monotone, etc.).

---

## 3.4 - Variante 3 : 3-sum

> Trouver tous les triplets $(a, b, c)$ avec $a \le b \le c$,
> $a + b + c = 0$, sans doublon.

**Idée.** On trie, on fixe $a$ par boucle externe ($O(n)$
positions), on cherche $b + c = -a$ dans le sous-tableau de droite
par two-pointer en $O(n)$. Total : **$O(n^2)$**, ce qui bat la
force brute $O(n^3)$.

```python
def three_sum(A):
    A = sorted(A)
    out = []
    n = len(A)
    for i in range(n - 2):
        if i > 0 and A[i] == A[i-1]: continue   # éviter doublons sur a
        T = -A[i]
        l, r = i + 1, n - 1
        while l < r:
            s = A[l] + A[r]
            if s == T:
                out.append((A[i], A[l], A[r]))
                l += 1; r -= 1
                while l < r and A[l] == A[l-1]: l += 1
                while l < r and A[r] == A[r+1]: r -= 1
            elif s < T: l += 1
            else:       r -= 1
    return out
```

Note : le `continue` après tri élimine les doublons sur le premier
élément ; les deux petits `while` les éliminent sur les autres.

---

## 3.5 - Quand l'utiliser

- Le tableau est trié (ou peut être trié sans changer la sémantique).
- La quantité observée est **monotone** en l'avancée d'un pointeur
  (somme croissante, distance croissante, etc.).
- L'algorithme naïf est $O(n^2)$ et la sortie est trouvée par
  exclusion progressive de positions.

Two pointers est l'expression *temporelle* du même principe que la
dichotomie : ne **jamais** revenir en arrière sur de l'information
acquise par monotonie.

---

## 3.6 - Exercices

:::exercise{id="{{EX_SE_2SUM}}"}
:::

:::exercise{id="{{EX_SE_3SUM}}"}
:::

:::exercise{id="{{EX_SE_REMOVE_DUPS}}"}
:::
