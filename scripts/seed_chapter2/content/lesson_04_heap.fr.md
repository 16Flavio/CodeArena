# 4. Tas binaires & heapsort

## 4.1 — L'idée : un arbre presque complet en tableau

Un **tas binaire** (max-heap) est un arbre binaire qui satisfait :

1. **Forme** : c'est un arbre **presque complet** — toutes les
   profondeurs sont remplies, sauf la dernière qui se remplit de
   gauche à droite.
2. **Ordre** : pour chaque nœud $v$, $v.k \ge$ toutes les clés de
   ses descendants. (Pour un min-heap, $\le$.)

Conséquence directe : **la racine est le maximum** de toute la
collection.

### Représentation tableau

Grâce à la forme presque complète, on stocke le tas dans un tableau
$A[0..n[$ sans aucun pointeur :

- racine en $A[0]$,
- les fils de $A[i]$ sont $A[2i+1]$ et $A[2i+2]$,
- le parent de $A[i]$ est $A[\lfloor (i-1)/2 \rfloor]$.

```python
def parent(i):  return (i - 1) // 2
def left(i):    return 2 * i + 1
def right(i):   return 2 * i + 2
```

> **Pourquoi pas un BST ?** Un BST est bien plus puissant (recherche,
> ordre total) mais coûte plus en mémoire (pointeurs) et en
> constante. Le tas se contente de fournir le **min/max** à coût
> minimal — c'est exactement ce qu'il faut pour une *priority queue*.

---

## 4.2 — Opérations primitives : sift-up et sift-down

Quand on viole l'ordre localement, on **fait descendre/monter** le
fauteur de troubles jusqu'à restaurer la propriété.

### `sift_up(i)` : remonter

Après une insertion en queue de tableau ou la diminution de la clé
d'un nœud (pour un min-heap : décroître), le nœud peut violer
l'ordre vis-à-vis de son parent.

```python
def sift_up(A, i):
    while i > 0 and A[parent(i)] < A[i]:
        A[parent(i)], A[i] = A[i], A[parent(i)]
        i = parent(i)
```

Coût : $\Theta(\log n)$ — au pire, on remonte de la feuille à la
racine.

### `sift_down(i)` : descendre

Après extraction de la racine ou dégradation d'un nœud, on échange
avec le **plus grand des fils** tant que l'ordre est violé.

```python
def sift_down(A, n, i):
    while True:
        l, r, largest = left(i), right(i), i
        if l < n and A[l] > A[largest]: largest = l
        if r < n and A[r] > A[largest]: largest = r
        if largest == i: return
        A[i], A[largest] = A[largest], A[i]
        i = largest
```

Coût : $\Theta(\log n)$.

---

## 4.3 — `insert` et `extract_max`

```python
def insert(A, x):
    A.append(x)               # ajoute en feuille la plus à droite
    sift_up(A, len(A) - 1)

def extract_max(A):
    top = A[0]
    last = A.pop()             # retire la feuille la plus à droite
    if A:
        A[0] = last            # la met à la racine, on rééquilibre
        sift_down(A, len(A), 0)
    return top
```

**Correction.** L'invariant `c'est un tas` est restauré à la fin de
chaque opération, par construction des sift.

**Complexité.** Les deux opérations en $\Theta(\log n)$.

---

## 4.4 — `build_heap` : construire un tas en $\Theta(n)$

Étant donné un tableau $A$ quelconque, on veut le transformer en tas.

### Approche naïve

Insérer un par un : $n$ insertions × $\Theta(\log n)$ chacune =
$\Theta(n \log n)$. Ce n'est pas optimal !

### Approche bottom-up

```python
def build_heap(A):
    n = len(A)
    for i in range(n // 2 - 1, -1, -1):
        sift_down(A, n, i)
```

On part de la fin (les dernières feuilles n'ont pas de descendant à
réordonner) et on `sift_down` chaque nœud interne en remontant.

### Preuve : $\Theta(n)$, pas $\Theta(n \log n)$

Le coût de `sift_down(i)` est borné par la **hauteur** du sous-arbre
enraciné en $i$, pas par la profondeur totale.

Dans un arbre presque complet à $n$ nœuds, le nombre de nœuds à
hauteur $h$ est $\le \lceil n / 2^{h+1} \rceil$. Donc :

$$T(n) \le \sum_{h=0}^{\lfloor \log_2 n \rfloor} \left\lceil \frac{n}{2^{h+1}} \right\rceil \cdot O(h) = O\!\left( n \sum_{h=0}^{\infty} \frac{h}{2^h} \right).$$

La série $\sum_{h \ge 0} h / 2^h$ converge vers $2$ (somme classique
$\sum h x^h = x/(1-x)^2$ évaluée en $x = 1/2$). Donc $T(n) = O(n)$.
$\square$

> **À retenir.** Le hash mental « insertion par insertion = $n \log
> n$, bottom-up = $n$ » est la différence entre un build *naïf* et
> un build *intelligent*. Pour heapsort, ça ne change pas la
> complexité globale ($n \log n$), mais c'est élégant.

---

## 4.5 — Heapsort

### Idée

1. `build_heap(A)` — $\Theta(n)$.
2. Répéter $n$ fois : `extract_max` et placer le résultat à la fin
   du tableau (in-place).

```python
def heapsort(A):
    n = len(A)
    # 1. construire un max-heap
    for i in range(n // 2 - 1, -1, -1):
        sift_down(A, n, i)
    # 2. extraire un par un
    for end in range(n - 1, 0, -1):
        A[0], A[end] = A[end], A[0]   # max au fond
        sift_down(A, end, 0)          # heap sur A[0:end]
```

### Correction

Invariant après l'itération `end = k` : `A[k..n[` contient les $n -
k$ plus grands éléments triés ; `A[0..k]` est un max-heap valide
sur les $k+1$ éléments restants.

- Avant la boucle : `A[0..n[` est un max-heap (par `build_heap`).
- À chaque itération, on met le max courant en `A[end]` puis on
  rétablit l'invariant heap sur `A[0..end[` via `sift_down`.

À la fin, `A[1..n[` est trié (croissant) et `A[0]` est le plus
petit — d'où l'invariant satisfait globalement. $\square$

### Complexité

- `build_heap` : $\Theta(n)$.
- $n$ extractions × $\Theta(\log n)$ : $\Theta(n \log n)$.
- **Total** : $\Theta(n \log n)$, dans le pire cas comme dans le
  meilleur — pas de garantie probabiliste à faire (contrairement à
  quicksort).
- **In-place** : $O(1)$ mémoire supplémentaire.
- **Stabilité** : non stable (les rotations dans le tas brouillent
  les ordres relatifs).

| Algo | Pire cas | Moyenne | Mémoire | Stable |
|------|----------|---------|---------|--------|
| Heapsort | $n \log n$ | $n \log n$ | $O(1)$ | non |
| Mergesort | $n \log n$ | $n \log n$ | $O(n)$ | oui |
| Quicksort | $n^2$ | $n \log n$ | $O(\log n)$ | non |

**Pour comparer**, voici un tri par insertion sur les mêmes données.
Lance-le et observe la quantité d'opérations : il n'arrive pas à la
cheville d'un heapsort sur de grandes entrées.

:::viz-sort{algo="insertion" data="[7,3,9,1,5,8,2,6,4]"}
:::

---

## 4.6 — Exercices

:::exercise{id="{{EX_HP_HEAPSORT}}"}
:::

:::exercise{id="{{EX_HP_KSMALL}}"}
:::

:::exercise{id="{{EX_HP_MERGE}}"}
:::
