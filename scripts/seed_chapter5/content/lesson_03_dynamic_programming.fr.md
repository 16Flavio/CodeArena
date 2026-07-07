# 3. Programmation dynamique

## 3.1 - Intuition

La programmation dynamique (DP) s'applique quand un problème se
décompose en **sous-problèmes qui se chevauchent**. Une récursion
naïve recalculerait alors les mêmes sous-problèmes un nombre
exponentiel de fois ; la DP les résout **une seule fois** et mémorise
le résultat.

Deux conditions rendent la DP applicable :

- **Sous-structure optimale** : la solution optimale se construit à
  partir de solutions optimales de sous-problèmes.
- **Chevauchement** : le nombre de sous-problèmes **distincts** est
  polynomial, même si l'arbre de récursion est exponentiel.

L'exemple canonique : Fibonacci naïf fait $\Theta(\varphi^n)$
appels ; mémorisé, il en fait $\Theta(n)$.

---

## 3.2 - Algorithme : deux styles

Il y a deux manières d'implémenter la même récurrence.

**Top-down (mémoïsation).** On écrit la récursion naturelle et on
met en cache :

```python
from functools import lru_cache

@lru_cache(maxsize=None)
def f(state):
    if base_case(state):
        return base_value
    return combine(f(sub1), f(sub2), ...)
```

**Bottom-up (tabulation).** On remplit un tableau dans l'ordre des
dépendances :

```python
dp = [base] * (n + 1)
for i in range(1, n + 1):
    dp[i] = combine(dp[i-1], dp[i-2], ...)
return dp[n]
```

Prenons la **plus longue sous-suite croissante** (LIS). Soit
$L(i)$ la longueur de la plus longue sous-suite croissante finissant
exactement en $i$ :

$$
L(i) = 1 + \max\bigl(\{\,0\,\} \cup \{\,L(j) : j < i,\ a_j < a_i\,\}\bigr).
$$

La réponse est $\max_i L(i)$. La récurrence est correcte car toute
sous-suite croissante finissant en $i$ se prolonge d'une sous-suite
croissante finissant en un $j < i$ avec $a_j < a_i$ - sous-structure
optimale.

---

## 3.3 - Complexité

Le coût d'une DP est

$$
T = (\text{nombre d'états}) \times (\text{coût par transition}).
$$

- **LIS** : $n$ états, transition $O(n)$, soit $\Theta(n^2)$ ;
  raffinable en $\Theta(n \log n)$ par recherche dichotomique sur les
  plus petites fins.
- **Sac à dos 0/1** : $\Theta(nW)$ états-transitions (pseudo-
  polynomial : dépend de la valeur $W$, pas seulement de sa taille en
  bits).
- **Distance d'édition** : $\Theta(|s|\,|t|)$.

La tabulation permet souvent de **réduire la mémoire** : le sac à dos
et la distance d'édition n'ont besoin que d'une ou deux lignes du
tableau à la fois.

---

## 3.4 - Pièges classiques

1. **Ordre de remplissage.** En bottom-up, un état doit être calculé
   **après** toutes ses dépendances. Pour le sac à dos 0/1, parcourir
   la capacité **de haut en bas** évite de réutiliser un objet.
2. **État incomplet.** Si deux contextes différents mènent à des
   réponses différentes, l'état doit les distinguer. Un état
   sous-spécifié donne des réponses fausses.
3. **Récursion profonde.** En top-down, la pile Python peut déborder
   (`sys.setrecursionlimit`) ; la tabulation l'évite.
4. **Pseudo-polynomial.** $\Theta(nW)$ n'est pas polynomial en la
   **taille de l'entrée** : pour $W = 10^{18}$, la DP par capacité
   est inutilisable ; il faut alors une autre approche.

---

## 3.5 - Reconnaître une DP

Poser la question : « quel est le plus petit ensemble de paramètres
qui décrit complètement un sous-problème ? » Ces paramètres sont
l'**état**. Puis : « comment un état se déduit-il d'états plus
petits ? » C'est la **transition**. Une fois ces deux points fixés,
le choix top-down / bottom-up n'est plus qu'une question de style et
de mémoire.

---

## 3.6 - Exercices

:::exercise{id="{{EX_PA_LIS}}"}
:::

:::exercise{id="{{EX_PA_KNAPSACK}}"}
:::

:::exercise{id="{{EX_PA_EDIT}}"}
:::
