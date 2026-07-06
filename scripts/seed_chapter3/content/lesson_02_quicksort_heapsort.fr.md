# 2. Tri rapide & tri par tas

## 2.1 - Le tri rapide : diviser **autour d'un pivot**

Le tri rapide est un autre *diviser pour régner*, mais à la
différence de mergesort, **toute la magie est dans la division** ; la
recombinaison est triviale.

### Algorithme

1. Choisir un **pivot** (un élément du tableau).
2. **Partitionner** le tableau autour du pivot : gauche $\le$ pivot,
   droite $>$ pivot.
3. Récursion sur les deux parties.

### Partition de Lomuto (la plus simple)

Pivot = dernier élément. On scanne avec deux indices, on swap.

```python
def lomuto_partition(A, lo, hi):
    pivot = A[hi]
    i = lo
    for j in range(lo, hi):
        if A[j] <= pivot:
            A[i], A[j] = A[j], A[i]
            i += 1
    A[i], A[hi] = A[hi], A[i]
    return i  # nouvelle position du pivot

def quicksort(A, lo=0, hi=None):
    if hi is None: hi = len(A) - 1
    if lo < hi:
        p = lomuto_partition(A, lo, hi)
        quicksort(A, lo, p - 1)
        quicksort(A, p + 1, hi)
```

:::viz-partition{data="3,7,1,8,4,2,5"}
:::

`step` avance d'**une comparaison** ; `i` (frontière entre $\le$
pivot et $>$ pivot) et `j` (le scan) sont affichés en dessous des
cellules. Quand `j` atteint la fin, le pivot rouge est swap à la
position `i`.

### Pire cas : $\Theta(n^2)$

Si à chaque récursion le pivot est l'élément le plus petit (ou le
plus grand) - par exemple sur un tableau **déjà trié** avec pivot =
dernier - on obtient une partition de taille $n-1, 0$. La récurrence

$$T(n) = T(n-1) + \Theta(n)$$

donne $T(n) = \Theta(n^2)$.

**Vue d'ensemble** - l'animation ci-dessous lance un tri rapide
**complet** : tu vois les pivots rouges se placer un par un, les
récursions s'enchaîner, et la profondeur de pile grimper. Charge
`1,2,3,4,5,6,7,8` (déjà trié) pour visualiser le pire cas - la pile
descend en escalier.

:::viz-quicksort{data="8,3,5,1,9,2,7,4,6"}
:::

### Cas moyen : $\Theta(n \log n)$ - preuve par espérance

On choisit le pivot **aléatoirement** dans $A[lo..hi]$. Pour des
clés distinctes $z_1 < z_2 < \dots < z_n$, soit $X_{ij}$ la variable
indicatrice valant $1$ si $z_i$ et $z_j$ sont comparés au cours de
l'algorithme.

Le coût total (en nombre de comparaisons) est
$X = \sum_{i<j} X_{ij}$, donc

$$\mathbb{E}[X] = \sum_{i<j} \Pr[z_i \text{ et } z_j \text{ sont comparés}].$$

**Lemme.** $z_i$ et $z_j$ sont comparés ssi le **premier pivot
choisi dans** $\{z_i, z_{i+1}, \dots, z_j\}$ est $z_i$ ou $z_j$. (Si
c'est un autre, ils tombent dans des sous-tableaux disjoints et ne
se rencontrent jamais.)

Comme les $j - i + 1$ éléments ont la même probabilité d'être tirés
en premier, la probabilité que ce soit $z_i$ ou $z_j$ vaut
$\frac{2}{j - i + 1}$.

$$\mathbb{E}[X] = \sum_{i<j} \frac{2}{j - i + 1} = 2 \sum_{i=1}^{n-1} \sum_{k=2}^{n - i + 1} \frac{1}{k} \le 2 n \sum_{k=2}^{n} \frac{1}{k} = 2n\,(H_n - 1).$$

Comme $H_n = \Theta(\log n)$ (cf. ch. 1), $\mathbb{E}[X] = \Theta(n \log n)$.

$\square$

> **Le mantra.** Quicksort « avec pivot aléatoire » est en
> $O(n \log n)$ **en espérance, sur tout input**. Le pire cas
> $\Theta(n^2)$ existe, mais sa probabilité est exponentiellement
> petite.

### Stratégies de pivot en pratique

| Stratégie | Pire cas | Moyenne | Coût |
|-----------|----------|---------|------|
| Premier / dernier élément | $n^2$ (tri déjà trié) | $n \log n$ | gratuit |
| Élément aléatoire | $n^2$ (proba $\to 0$) | $n \log n$ | RNG |
| Médiane de 3 (premier, milieu, dernier) | $n^2$ rare | $n \log n$ | 3 comparaisons (pire cas) |
| Médiane des médianes | $n \log n$ déterministe (cf. leçon 4) | $n \log n$ | constante élevée |

---

## 2.2 - Tri par tas (rappel)

Le tri par tas a déjà été vu en détail au chapitre 2 (leçon « Tas
binaires & heapsort »). On ne reprend que le résumé ici, pour le
mettre en perspective.

| Algo | Pire cas | Moyenne | Mémoire | Stable |
|------|----------|---------|---------|--------|
| Insertion | $n^2$ | $n^2$ | $O(1)$ | oui |
| Mergesort | $n \log n$ | $n \log n$ | $O(n)$ | oui |
| Quicksort | $n^2$ | $n \log n$ | $O(\log n)$ | non |
| Heapsort | $n \log n$ | $n \log n$ | $O(1)$ | non |

**Le bon outil pour le bon problème.**

- Mémoire serrée ? **Heapsort** (in-place, garantie $n \log n$).
- Stabilité requise ? **Mergesort**.
- Cache + constantes minuscules ? **Quicksort** (et il gagne en
  pratique sur les CPU modernes).
- Petits tableaux ? **Insertion sort**.

---

## 2.3 - Exercices

:::exercise{id="{{EX_SO_PARTITION}}"}
:::

:::exercise{id="{{EX_SO_DUTCH}}"}
:::

:::exercise{id="{{EX_SO_RUNMEDIAN}}"}
:::
