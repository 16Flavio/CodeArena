# 1. Recherche dichotomique & invariants de boucle

## 1.1 - Intuition

On cherche une valeur $x$ dans un tableau **trié** $A[0..n-1]$. Au
lieu de scanner les $n$ éléments, on **coupe en deux** : si $x$ est
plus petit que l'élément du milieu, il ne peut être que dans la
moitié gauche, sinon dans la moitié droite. À chaque itération
l'espace de recherche est divisé par 2 - d'où $O(\log n)$
comparaisons.

Plus profondément : la dichotomie est une **machine à entretenir un
invariant**. À chaque tour, on conserve une propriété vraie sur
l'intervalle restant, et on la rétrécit jusqu'à ce qu'il ne reste
qu'un point candidat.

---

## 1.2 - Algorithme & invariant

On cherche le premier indice $i$ tel que $A[i] \ge x$ (ce qu'en
C++ on appelle `lower_bound`). C'est la primitive la plus utile :
recherche d'égalité, de borne supérieure, et d'insertion s'en
déduisent.

```python
def lower_bound(A, x):
    lo, hi = 0, len(A)        # intervalle SEMI-OUVERT [lo, hi)
    while lo < hi:
        mid = (lo + hi) // 2
        if A[mid] < x:
            lo = mid + 1
        else:
            hi = mid
    return lo
```

### Invariant

À l'entrée du `while`, on maintient :

$$
(\forall j < lo)\ A[j] < x \qquad \text{et} \qquad
(\forall j \ge hi)\ A[j] \ge x.
$$

- **Initialisation** : $lo = 0$ et $hi = n$, les deux quantificateurs
  sont vides - vrais.
- **Conservation** : au tour suivant, soit $A[\text{mid}] < x$ et on
  pousse $lo = \text{mid} + 1$ (toutes les positions $\le \text{mid}$
  sont $< x$), soit $A[\text{mid}] \ge x$ et on pose $hi = \text{mid}$
  (toutes les positions $\ge \text{mid}$ sont $\ge x$).
- **Terminaison** : `hi - lo` strictement décroît à chaque tour ;
  comme c'est un entier positif, la boucle termine.
- **Correction à la sortie** : $lo = hi$, donc $A[j] < x$ pour
  $j < lo$ et $A[j] \ge x$ pour $j \ge lo$ - exactement la
  définition de `lower_bound`. $\square$

---

## 1.3 - Complexité

L'intervalle $[lo, hi)$ a au plus $n$ éléments à l'entrée et perd
**au moins la moitié** à chaque tour : si l'intervalle a taille $k$,
$\text{mid} - lo \le k/2$ et $hi - (\text{mid}+1) \le k/2$. Après
$T$ tours, taille $\le n / 2^T$, donc $T \le \log_2 n$.

$$
\boxed{\;T(n) = \Theta(\log n)\;}
$$

---

## 1.4 - Pièges classiques

1. **Intervalle fermé vs semi-ouvert.** Avec `hi = n - 1` (fermé),
   il faut écrire `while lo <= hi` et `hi = mid - 1`, sinon on
   boucle. Le semi-ouvert est plus régulier - un seul style à
   retenir. Choisir UNE convention et s'y tenir.
2. **`mid = (lo + hi) // 2`.** En Python aucun risque ; en C++/Java
   sur des `int`, faire `lo + (hi - lo) / 2` pour éviter l'overflow.
3. **Recherche d'égalité après `lower_bound`.** L'élément est présent
   ssi `lo < n && A[lo] == x`. Tester *les deux* conditions -
   oublier la première fait sortir du tableau quand $x$ est
   strictement plus grand que tout.
4. **Tableau non trié.** La dichotomie ne dit rien d'utile sur un
   tableau non trié : la monotonie est *l'hypothèse*. Toujours
   trier d'abord, ou prouver la monotonie quand on dichotomise sur
   la réponse (cf. leçon 2).

---

## 1.5 - Variantes utiles

- **`upper_bound(A, x)`** : premier indice $i$ avec $A[i] > x$.
  Substituer `<=` à `<` dans le test du milieu.
- **Première / dernière occurrence** d'une clé $x$ : la première est
  `lower_bound(A, x)` ; la dernière est `upper_bound(A, x) - 1`.
- **Comptage** des occurrences : `upper_bound(A, x) - lower_bound(A, x)`.
- **Dichotomie discrète sur entiers** (sans tableau) : trouver le
  plus grand $k$ tel que $P(k)$, où $P$ est monotone décroissante.
  C'est la base de la leçon 2.

---

## 1.6 - Exercices

:::exercise{id="{{EX_SE_LOWERBOUND}}"}
:::

:::exercise{id="{{EX_SE_FIRSTOCC}}"}
:::

:::exercise{id="{{EX_SE_ISQRT}}"}
:::
