# 1. Modèle RAM & notations asymptotiques

## 1.1 - Pourquoi un modèle de coût ?

Quand on dit *« cet algo tourne en $O(n \log n)$ »*, qu'est-ce qu'on
compte exactement ? Une addition vaut-elle autant qu'un accès mémoire ?
Et que faire d'une multiplication de deux entiers à 1000 chiffres ?

On a besoin d'un **modèle de coût** abstrait : assez précis pour
distinguer les bons algos des mauvais, assez simple pour ne pas dépendre
de la machine.

### Le modèle RAM (Random Access Machine)

- Mémoire : un tableau infini de cellules, chaque cellule contient un
  entier d'au plus $w$ bits ($w = O(\log n)$ - assez pour indexer
  l'entrée).
- Opérations élémentaires en **temps unitaire** :
  - lecture / écriture d'une cellule,
  - opérations arithmétiques entre deux mots ($+$, $-$, $\times$, $/$,
    comparaison, opérations bit-à-bit),
  - branchement conditionnel.
- On compte le nombre d'opérations élémentaires en fonction de la
  **taille de l'entrée** $n$.

> **Limite à connaître.** Le modèle RAM ment sur la mémoire (les caches
> n'existent pas) et sur l'arithmétique des grands nombres. C'est une
> abstraction utile, pas une vérité physique.

### Exemple : recherche linéaire

```python
def linear_search(arr, target):
    for x in arr:           # boucle sur n éléments
        if x == target:     # 1 comparaison
            return True     # 1 retour
    return False
```

Pire cas : `target` n'est pas présent. On exécute $n$ comparaisons et
$n$ incréments d'indice, soit $T(n) = 2n + c$ opérations. On note
$T(n) = \Theta(n)$.

---

## 1.2 - Notations asymptotiques : définitions formelles

Soient $f, g : \mathbb{N} \to \mathbb{R}_{\ge 0}$.

### Borne supérieure : $O$

$$
f(n) = O(g(n)) \iff \exists\, c > 0,\ \exists\, n_0 \in \mathbb{N},\ \forall n \ge n_0,\ f(n) \le c \cdot g(n).
$$

Lecture : *« $f$ ne grandit pas plus vite que $g$, à un facteur constant près, à partir d'un certain rang. »*

### Borne inférieure : $\Omega$

$$
f(n) = \Omega(g(n)) \iff \exists\, c > 0,\ \exists\, n_0 \in \mathbb{N},\ \forall n \ge n_0,\ f(n) \ge c \cdot g(n).
$$

### Borne serrée : $\Theta$

$$
f(n) = \Theta(g(n)) \iff f(n) = O(g(n))\ \text{et}\ f(n) = \Omega(g(n)).
$$

### Domination stricte : $o$ (petit-o)

$$
f(n) = o(g(n)) \iff \forall\, c > 0,\ \exists\, n_0,\ \forall n \ge n_0,\ f(n) < c \cdot g(n).
$$

De manière équivalente, lorsque $g(n) > 0$ : $\displaystyle \lim_{n \to \infty} \frac{f(n)}{g(n)} = 0$.

### Domination stricte (autre côté) : $\omega$

$$
f(n) = \omega(g(n)) \iff \forall\, c > 0,\ \exists\, n_0,\ \forall n \ge n_0,\ f(n) > c \cdot g(n).
$$

### Tableau récapitulatif

| Notation | Sens intuitif | Analogue numérique |
|----------|----------------|---------------------|
| $f = O(g)$ | $f$ borné supérieurement par $g$ | $f \le g$ |
| $f = \Omega(g)$ | $f$ borné inférieurement par $g$ | $f \ge g$ |
| $f = \Theta(g)$ | mêmes ordres de grandeur | $f = g$ |
| $f = o(g)$ | $f$ négligeable devant $g$ | $f < g$ |
| $f = \omega(g)$ | $f$ domine strictement $g$ | $f > g$ |

### Visualiser les ordres de grandeur

:::viz-big-o
:::

Bouge le curseur : tant que $n$ reste petit, $n^2$ domine $n \log n$
de peu ; quand $n$ atteint quelques dizaines, l'écart explose. C'est
exactement la raison pour laquelle on s'embête à écrire $O$ et pas
juste « plus rapide ».

### Exemple complet de preuve : $3n^2 + 5n + 7 = O(n^2)$

On cherche $c$ et $n_0$ tels que $\forall n \ge n_0,\ 3n^2 + 5n + 7 \le c\,n^2$.

Pour $n \ge 1$ : $3n^2 + 5n + 7 \le 3n^2 + 5n^2 + 7n^2 = 15 n^2$.

Donc $c = 15$ et $n_0 = 1$ conviennent. $\square$

> **Piège classique.** $\log_2 n$ et $\log_{10} n$ diffèrent d'un facteur
> constant, donc $\log_a n = \Theta(\log_b n)$ pour toutes bases
> $a, b > 1$. On écrit simplement $\log n$.

---

## 1.3 - Exercices

:::exercise{id="{{EX_RAM_STD}}"}
:::

:::exercise{id="{{EX_RAM_TWIST}}"}
:::

:::exercise{id="{{EX_RAM_HARD}}"}
:::
