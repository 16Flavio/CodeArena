# 1. Diviser pour régner

## 1.1 - Intuition

Un problème de taille $n$ est parfois trop gros pour être attaqué
d'un bloc, mais devient trivial une fois coupé en morceaux. Le
schéma **diviser pour régner** répète trois gestes :

1. **Diviser** : couper l'instance en sous-instances plus petites,
   typiquement deux moitiés.
2. **Régner** : résoudre chaque sous-instance récursivement.
3. **Combiner** : recoller les sous-solutions en une solution du
   problème initial.

Le tri fusion en est l'archétype : trier deux moitiés puis les
**fusionner** en temps linéaire. La puissance du paradigme vient de
ce que le travail de combinaison, souvent linéaire, est amorti sur
une hauteur de récursion logarithmique.

---

## 1.2 - Algorithme & théorème maître

Écrivons le tri fusion, dont la structure sert de gabarit à toute la
leçon.

```python
def merge_sort(a):
    if len(a) <= 1:
        return a
    mid = len(a) // 2
    left = merge_sort(a[:mid])       # régner (gauche)
    right = merge_sort(a[mid:])      # régner (droite)
    return merge(left, right)        # combiner en O(n)
```

Le coût suit une **récurrence** : deux appels sur $n/2$, plus une
fusion linéaire.

$$
T(n) = 2\,T(n/2) + \Theta(n).
$$

### Théorème maître

Pour une récurrence de la forme

$$
T(n) = a\,T(n/b) + \Theta(n^d), \qquad a \ge 1,\ b > 1,\ d \ge 0,
$$

on compare la croissance des feuilles ($n^{\log_b a}$) à celle du
travail de combinaison ($n^d$) :

$$
T(n) = \begin{cases}
\Theta(n^d) & \text{si } d > \log_b a, \\
\Theta(n^d \log n) & \text{si } d = \log_b a, \\
\Theta(n^{\log_b a}) & \text{si } d < \log_b a.
\end{cases}
$$

**Preuve (esquisse).** L'arbre de récursion a $a^k$ nœuds au niveau
$k$, chacun de taille $n / b^k$, donc un travail de combinaison
$a^k \cdot \Theta((n/b^k)^d)$. Sommer sur les $\log_b n$ niveaux
donne une série géométrique de raison $a / b^d$. Selon que cette
raison est $< 1$, $= 1$ ou $> 1$, la somme est dominée par la
racine, répartie également, ou dominée par les feuilles. $\square$

Pour le tri fusion, $a = 2$, $b = 2$, $d = 1$, donc
$\log_b a = 1 = d$ : cas d'égalité, $T(n) = \Theta(n \log n)$.

---

## 1.3 - Complexité

Le tableau des cas ci-dessus se lit comme une règle de décision. Les
récurrences classiques :

- **Recherche dichotomique** : $T(n) = T(n/2) + \Theta(1)$, soit
  $a = 1, b = 2, d = 0$ : $\Theta(\log n)$.
- **Tri fusion / comptage d'inversions** : $\Theta(n \log n)$.
- **Multiplication de Karatsuba** : $T(n) = 3\,T(n/2) + \Theta(n)$,
  $\log_2 3 \approx 1{.}585 > 1$ : $\Theta(n^{1.585})$, mieux que le
  produit scolaire en $\Theta(n^2)$.

$$
\boxed{\;T(n) = 2\,T(n/2) + \Theta(n) = \Theta(n \log n)\;}
$$

---

## 1.4 - Pièges classiques

1. **Oublier le cas de base.** Une récursion sans condition d'arrêt
   sur $n \le 1$ ne termine pas.
2. **Combinaison trop coûteuse.** Si la fusion devient
   $\Theta(n^2)$, le gain s'évapore : $T(n) = 2T(n/2) + n^2 =
   \Theta(n^2)$. Le travail de recollement est le vrai enjeu.
3. **Copies de tableaux.** En Python, `a[:mid]` recopie ; sur de
   grands $n$ cela ajoute un facteur constant. Passer des indices
   `(lo, hi)` plutôt que des tranches quand la mémoire compte.
4. **Débordement du milieu.** `(lo + hi) // 2` est sûr en Python ;
   en C++/Java sur `int`, préférer `lo + (hi - lo) // 2`.

---

## 1.5 - Au-delà du tri

Diviser pour régner dépasse largement le tri : paire de points la
plus proche en $\Theta(n \log n)$, transformée de Fourier rapide
(FFT) pour convoluer deux suites en $\Theta(n \log n)$, exponentiation
rapide en $\Theta(\log n)$. Le fil conducteur reste le même :
identifier une découpe où la combinaison est bon marché.

---

## 1.6 - Exercices

:::exercise{id="{{EX_PA_INVERSIONS}}"}
:::

:::exercise{id="{{EX_PA_MAXSUB}}"}
:::

:::exercise{id="{{EX_PA_REVPAIRS}}"}
:::
