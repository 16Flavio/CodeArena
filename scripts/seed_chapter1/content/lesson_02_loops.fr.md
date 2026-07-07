# 2. Analyse de boucles & sommes utiles

## 2.1 - L'idée fondamentale

Le coût d'une boucle est la **somme** des coûts de ses itérations. Pour
analyser un algorithme à boucles imbriquées, on traduit chaque niveau
en somme et on simplifie. Trois sommes reviennent partout.

## 2.2 - Les trois sommes à connaître par cœur

### Somme arithmétique

$$
\sum_{i=1}^{n} i = \frac{n(n+1)}{2} = \Theta(n^2).
$$

**Preuve élégante (Gauss).** Écrire la somme dans les deux sens et
additionner colonne par colonne :

$$
\begin{aligned}
S &= 1 + 2 + \dots + (n-1) + n \\
S &= n + (n-1) + \dots + 2 + 1 \\
\hline
2S &= \underbrace{(n+1) + (n+1) + \dots + (n+1)}_{n \text{ termes}} = n(n+1).
\end{aligned}
$$

D'où $S = n(n+1)/2$. $\square$

### Somme géométrique

$$
\sum_{i=0}^{n-1} r^i = \begin{cases} \dfrac{r^n - 1}{r - 1} & \text{si } r \ne 1 \\ n & \text{si } r = 1. \end{cases}
$$

Pour $r > 1$ on a $\sum_{i=0}^{n-1} r^i = \Theta(r^n)$ : le **dernier
terme domine**. Cette intuition est cruciale en analyse de récursion.

### Somme harmonique

$$
H_n = \sum_{i=1}^{n} \frac{1}{i} = \ln n + \gamma + O(1/n)\quad \text{où } \gamma \approx 0.5772.
$$

En particulier $H_n = \Theta(\log n)$. C'est la complexité au pire cas
d'opérations comme « insertion dans un tas binaire », ou la profondeur
moyenne d'un arbre BST aléatoire.

**Preuve (esquisse).** On encadre la somme par deux intégrales :

$$
\int_1^{n+1} \frac{dx}{x} \le \sum_{i=1}^{n} \frac{1}{i} \le 1 + \int_1^{n} \frac{dx}{x},
$$

soit $\ln(n+1) \le H_n \le 1 + \ln n$. $\square$

---

## 2.3 - Trois patrons d'analyse

### Boucles imbriquées triangulaires

```python
total = 0
for i in range(n):           # n itérations
    for j in range(i):       # i itérations (variable !)
        total += 1
```

Coût total :

$$
T(n) = \sum_{i=0}^{n-1} i = \frac{n(n-1)}{2} = \Theta(n^2).
$$

**Exemple visuel** : le tri par sélection a exactement cette
structure de boucle imbriquée triangulaire, d'où sa complexité
quadratique.

:::viz-sort{algo="selection" data="[5,2,8,1,9,3,7,4]"}
:::

### Boucle multiplicative

```python
i = 1
while i <= n:
    # corps en O(1)
    i *= 2
```

L'indice $i$ prend les valeurs $1, 2, 4, 8, \dots, 2^k$ avec $2^k \le n$.
Donc $k = \lfloor \log_2 n \rfloor$ et le nombre d'itérations est
$\lfloor \log_2 n \rfloor + 1 = \Theta(\log n)$.

### Boucle imbriquée logarithmique

```python
for i in range(n):           # n
    j = 1
    while j <= n:
        j *= 2               # log n
```

Coût : $T(n) = n \cdot \log_2 n = \Theta(n \log n)$.

> **Heuristique utile.** Quand un indice est *divisé* (ou multiplié) par
> une constante $> 1$, le coût est logarithmique. Quand il est
> *décrémenté* d'une constante, il est linéaire.

---

## 2.4 - Exercices

:::exercise{id="{{EX_LOOP_STD}}"}
:::

:::exercise{id="{{EX_LOOP_TWIST}}"}
:::

:::exercise{id="{{EX_LOOP_HARD}}"}
:::
