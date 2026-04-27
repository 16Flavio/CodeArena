# 4. Sélection : quickselect & médiane des médianes

## 4.1 — Le problème de sélection

**Question** : étant donné un tableau $A$ de $n$ éléments et un
entier $k \in [1, n]$, trouver le **$k$-ème plus petit** élément
(la $k$-ème statistique d'ordre).

Cas spéciaux notables :
- $k = 1$ → minimum.
- $k = n$ → maximum.
- $k = \lceil n/2 \rceil$ → **médiane**.

### Combien ça coûte ?

- *Approche triviale* : trier puis indexer → $\Theta(n \log n)$.
- *Avec un tas* : extract-min $k$ fois → $\Theta(n + k \log n)$.
- *Quickselect* : $\Theta(n)$ **en espérance**.
- *Médiane des médianes* : $\Theta(n)$ **déterministe**.

C'est l'une des rares occasions où l'on bat $n \log n$ pour un
problème non trivial.

---

## 4.2 — Quickselect

### Idée

Comme quicksort, mais on **ne récurse que sur le côté qui contient
le $k$-ème élément**. La partition coupe le tableau en gauche
$\le$ pivot, droite $>$ pivot, à la position $p$ :

- Si $k - 1 = p$ : le pivot est notre réponse.
- Si $k - 1 < p$ : le $k$-ème est à gauche, on récurse à gauche.
- Si $k - 1 > p$ : le $k$-ème est à droite, on récurse à droite avec
  la même position $k$.

### Code

```python
import random

def quickselect(A, k):
    """Retourne le k-ème plus petit (1-indexé) de A — détruit A."""
    lo, hi = 0, len(A) - 1
    while lo <= hi:
        # Pivot aléatoire pour casser le pire cas adversarial.
        p = random.randint(lo, hi)
        A[p], A[hi] = A[hi], A[p]
        pivot = A[hi]
        i = lo
        for j in range(lo, hi):
            if A[j] <= pivot:
                A[i], A[j] = A[j], A[i]; i += 1
        A[i], A[hi] = A[hi], A[i]
        if i == k - 1: return A[i]
        if i  > k - 1: hi = i - 1
        else:           lo = i + 1
```

### Complexité en espérance : $\Theta(n)$

Soit $T(n)$ le nombre attendu de comparaisons sur un tableau de
taille $n$. Avec un pivot uniforme, le sous-tableau récursé a une
taille uniformément distribuée dans $\{0, 1, \dots, n-1\}$. Pour
le pire choix de $k$ on récurse dans la moitié la plus grande :

$$T(n) \le n + \frac{1}{n} \sum_{i=n/2}^{n-1} T(i).$$

On montre par induction que $T(n) \le 4n$. **Astuce de la
borne récursive** :

$$T(n) \le n + \frac{1}{n} \sum_{i=n/2}^{n-1} 4i \le n + \frac{4}{n} \cdot \frac{n}{2} \cdot \frac{3n/2 + n/2}{2}/... $$

Plus simple — bornons $\sum_{i=n/2}^{n-1} i \le \frac{3n^2}{4}$ :

$$T(n) \le n + \frac{4}{n} \cdot \frac{3n^2}{4} = n + 3n = 4n. \square$$

### Pire cas : $\Theta(n^2)$

Comme quicksort : si chaque pivot est l'extrême du sous-tableau, on
réduit $n$ d'un seul élément à chaque fois. Probabilité
exponentiellement petite avec pivot aléatoire, mais possible.

---

## 4.3 — Médiane des médianes : $\Theta(n)$ **déterministe**

L'algorithme de Blum-Floyd-Pratt-Rivest-Tarjan (1973) atteint
$\Theta(n)$ pire cas en choisissant un pivot dont on **garantit**
qu'il n'est pas trop extrême.

### Algorithme

```python
def select(A, k):
    """k-ème plus petit (1-indexé) de A. Modifie A."""
    if len(A) <= 5:
        return sorted(A)[k - 1]

    # 1. Diviser A en groupes de 5, prendre la médiane de chacun.
    groups = [A[i:i+5] for i in range(0, len(A), 5)]
    medians = [sorted(g)[len(g) // 2] for g in groups]

    # 2. Médiane récursive des médianes — c'est notre pivot.
    pivot = select(medians, (len(medians) + 1) // 2)

    # 3. Partition autour de pivot.
    L = [x for x in A if x < pivot]
    M = [x for x in A if x == pivot]
    R = [x for x in A if x > pivot]

    if k <= len(L):                    return select(L, k)
    if k <= len(L) + len(M):           return pivot
    return select(R, k - len(L) - len(M))
```

### Pourquoi ça marche

**Lemme.** Le pivot trouvé par MoM est plus grand qu'au moins
$\frac{3n}{10}$ éléments et plus petit qu'au moins $\frac{3n}{10}$
éléments.

*Preuve.* Il y a $\lceil n / 5 \rceil$ groupes de 5. La médiane des
médianes est plus grande que la moitié des médianes, soit $\lceil
n/10 \rceil$ médianes. Chacune de ces médianes est elle-même plus
grande que les 2 plus petits éléments de son groupe (dont elle est
médiane). Total :

$$3 \cdot \left\lceil \frac{n}{10} \right\rceil \ge \frac{3n}{10}$$

éléments $\le$ pivot. Symétriquement pour $\ge$. $\square$

### Récurrence

Soit $T(n)$ le coût.

- L'étape 1 (médianes de groupes de 5) coûte $\Theta(n)$ car le
  tri de 5 éléments est $O(1)$.
- L'étape 2 (médiane récursive des $n/5$ médianes) coûte $T(n/5)$.
- L'étape 3 (partition + récursion sur la grande moitié) : la
  grande moitié a au plus $\frac{7n}{10}$ éléments (par le lemme),
  donc $T(7n/10)$.

$$T(n) \le T(n/5) + T(7n/10) + cn.$$

Comme $\frac{1}{5} + \frac{7}{10} = \frac{9}{10} < 1$, la
récurrence se résout en $T(n) = \Theta(n)$ par induction (ou Akra-
Bazzi avec $p = 1$ et l'intégrale dominée par $n$). $\square$

### Pourquoi des groupes de 5 ?

C'est la plus petite taille impaire qui rend $1/k + (k-1)/k \cdot
3/4 < 1$ : groupes de 3 → coefficients $1/3 + 2/3 = 1$, pas de
contraction ; groupes de 5 → ça passe. (Et 5 est plus petit que 7,
donc constantes minimales.)

> **En pratique.** MoM est rarement utilisé : ses constantes sont
> élevées et quickselect aléatoire est *amplement* suffisant. Mais
> théoriquement, c'est l'algo qui tue la borne $n \log n$ en
> sélection, **sans aléa**.

---

## 4.4 — Tableau récapitulatif

| Algo | Pire cas | Moyenne | Mémoire | Aléatoire ? |
|------|----------|---------|---------|-------------|
| Tri puis index | $n \log n$ | $n \log n$ | $O(1)$ ou $O(n)$ | non |
| Heap (extraire $k$ min) | $n + k \log n$ | idem | $O(1)$ | non |
| Quickselect (pivot rand) | $n^2$ | $\Theta(n)$ | $O(\log n)$ | oui |
| Médiane des médianes | $\Theta(n)$ | $\Theta(n)$ | $O(\log n)$ | non |

---

## 4.5 — Exercices

:::exercise{id="{{EX_SO_SELECT}}"}
:::

:::exercise{id="{{EX_SO_MINMAX}}"}
:::

:::exercise{id="{{EX_SO_TOPK}}"}
:::
