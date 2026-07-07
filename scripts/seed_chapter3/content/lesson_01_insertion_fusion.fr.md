# 1. Tri par insertion & tri par fusion

## 1.1 - Le tri par insertion : intuitif comme une main de cartes

Quand on aligne des cartes en main, on **insère** chaque nouvelle carte
à sa place dans la partie déjà triée. C'est exactement le tri par
insertion.

```python
def insertion_sort(A):
    for i in range(1, len(A)):
        key = A[i]
        j = i - 1
        while j >= 0 and A[j] > key:
            A[j + 1] = A[j]
            j -= 1
        A[j + 1] = key
    return A
```

:::viz-sort{algo="insertion" data="[5,2,8,1,9,3,7,4]"}
:::

### Preuve de correction (invariant de boucle)

**Invariant.** Au début de l'itération $i$ de la boucle externe,
$A[0..i-1]$ contient les éléments originaux de cette plage, **triés
en ordre croissant**.

- *Initialisation.* Avant $i = 1$, $A[0..0]$ est trivialement trié.
- *Hérédité.* La boucle interne décale tout élément de $A[0..i-1]$
  qui est strictement plus grand que `key`, puis insère `key`. Le
  résultat $A[0..i]$ est encore trié.
- *Terminaison.* Après $i = n$, $A[0..n-1] = A$ est trié.

$\square$

### Complexité

- Pire cas (tableau inversé) : $T(n) = \sum_{i=1}^{n-1} i = \Theta(n^2)$.
- Meilleur cas (tableau déjà trié) : $\Theta(n)$ - la boucle interne
  s'arrête tout de suite.
- En espérance sur permutation aléatoire : $\Theta(n^2)$.

> **Pourquoi l'enseigner ?** En pratique, on bascule vers insertion
> sort *à l'intérieur* d'algos $n \log n$ pour les sous-tableaux de
> taille $\le 16$ : ses constantes sont si petites qu'il bat
> mergesort/quicksort sur les petits.

---

## 1.2 - Le tri par fusion : diviser pour régner

### Idée

1. **Diviser** le tableau en deux moitiés.
2. **Trier** chaque moitié récursivement.
3. **Fusionner** les deux moitiés triées en un tableau trié.

L'opération clé est la **fusion** : étant donné deux tableaux triés
$L$ et $R$, on les parcourt à deux indices et on émet à chaque étape
le plus petit des deux fronts.

```python
def merge(L, R):
    out = []
    i = j = 0
    while i < len(L) and j < len(R):
        if L[i] <= R[j]:
            out.append(L[i]); i += 1
        else:
            out.append(R[j]); j += 1
    out.extend(L[i:])
    out.extend(R[j:])
    return out

def merge_sort(A):
    if len(A) <= 1:
        return A
    mid = len(A) // 2
    return merge(merge_sort(A[:mid]), merge_sort(A[mid:]))
```

### Correction de la fusion

**Invariant de fusion.** Après $k$ itérations, `out` contient les
$k$ plus petits éléments de $L \cup R$, dans l'ordre croissant.

*Hérédité.* À chaque tour on émet $\min(L[i], R[j])$. Comme $L$ et
$R$ sont triés, leurs fronts sont leurs minima respectifs ; le min
des deux fronts est donc le min global non encore émis. $\square$

### Preuve complète $T(n) = \Theta(n \log n)$

La récurrence est

$$
T(n) = 2\,T(n/2) + cn,\qquad T(1) = c'.
$$

**Approche 1 - Master Theorem.** $a = 2$, $b = 2$, $\alpha = \log_b a = 1$,
$f(n) = cn = \Theta(n^\alpha)$ : on est dans le **cas 2** du Master
Theorem (cf. ch. 1) et $T(n) = \Theta(n \log n)$.

**Approche 2 - Arbre de récurrence (à la main).**

- Niveau 0 : 1 nœud de coût $cn$.
- Niveau $k$ : $2^k$ nœuds, chacun de coût $c \cdot n / 2^k$.
- Coût d'un niveau : $2^k \cdot (cn/2^k) = cn$ - **constant** par niveau.
- Profondeur : $\log_2 n$ niveaux jusqu'aux feuilles.

$$
T(n) = \sum_{k=0}^{\log_2 n} cn = cn\,(\log_2 n + 1) = \Theta(n \log n).
$$

$\square$

### Stabilité, mémoire, en pratique

- **Stable** : oui (la fusion préserve l'ordre relatif quand les
  clés sont égales - `<=` dans le test).
- **Mémoire** : $\Theta(n)$ supplémentaires (le tableau `out`).
- **Forte** : la borne $n \log n$ est **garantie** quel que soit
  l'input - pas de pire cas pathologique comme quicksort.

---

## 1.3 - Exercices

:::exercise{id="{{EX_SO_MERGE2}}"}
:::

:::exercise{id="{{EX_SO_INVERSIONS}}"}
:::

:::exercise{id="{{EX_SO_KMERGE}}"}
:::
