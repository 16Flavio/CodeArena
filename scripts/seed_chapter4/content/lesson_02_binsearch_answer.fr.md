# 2. Dichotomie sur les réels et sur la réponse

La leçon 1 dichotomise dans un **tableau trié**. Le vrai moteur
n'était pas le tableau : c'était la **monotonie**. On peut donc
dichotomiser chaque fois qu'on a une fonction monotone - réelle ou
discrète, parfois sans tableau du tout.

---

## 2.1 - Sur les réels : bissection

Soit $f : [a, b] \to \mathbb{R}$ **continue** avec $f(a) < 0 <
f(b)$. Le théorème des valeurs intermédiaires garantit une racine
$r \in [a, b]$. Bissection :

```python
def bisect_real(f, lo, hi, eps=1e-9):
    # Pré-condition : f(lo) < 0 < f(hi).
    while hi - lo > eps:
        mid = (lo + hi) / 2
        if f(mid) < 0: lo = mid
        else:          hi = mid
    return (lo + hi) / 2
```

### Combien d'itérations ?

L'intervalle est divisé par 2 à chaque tour. Pour atteindre une
précision $\varepsilon$ à partir d'une largeur initiale $L$, il
faut $T = \lceil \log_2(L/\varepsilon) \rceil$ tours. **L = 1, ε =
1e-9 → 30 tours suffisent.** En pratique on fixe un nombre fixe
(60-100) qui couvre tout l'écart, plutôt qu'un test `while hi - lo
> eps` qui souffre des erreurs flottantes.

```python
for _ in range(100):
    mid = (lo + hi) / 2
    if f(mid) < 0: lo = mid
    else:          hi = mid
```

### Pièges

- **Monotonie nécessaire** : si $f$ change de signe plus d'une fois
  sur $[a, b]$, la bissection n'a aucune raison de converger vers
  *votre* racine. Plotter, raisonner, ou réduire l'intervalle de
  départ.
- **Tester la sortie** par injection : substituer la racine
  trouvée dans le problème original et vérifier que l'erreur est
  bien $\le \varepsilon$ requis.
- Ne **jamais** comparer à zéro avec `==` après calcul flottant.

---

## 2.2 - Dichotomie sur la réponse

C'est le mouvement le plus payant en programmation compétitive :
au lieu de chercher $x$ dans un tableau, on **devine la valeur de
la réponse** et on demande au problème : "cette réponse est-elle
faisable ?"

### Pré-requis (à vérifier explicitement)

Soit $\text{feasible}(k)$ un prédicat à valeur booléenne. Pour
qu'on puisse dichotomiser, il faut :

$$
\text{feasible}(k) = \text{vrai} \implies
\text{feasible}(k') = \text{vrai} \quad \forall\, k' \le k
$$

(ou la version croissante : faisable au-delà d'un seuil). C'est
l'hypothèse de **monotonie de la prédiction**. La frontière entre
les `vrai` et les `faux` est unique - et c'est elle qu'on cherche.

### Patron

```python
def search_max(lo, hi, feasible):
    # Cherche le plus grand k dans [lo, hi] tel que feasible(k).
    # Pré : feasible(lo) ; non feasible(hi+1).
    while lo < hi:
        mid = (lo + hi + 1) // 2     # +1 pour éviter la boucle infinie
        if feasible(mid): lo = mid
        else:             hi = mid - 1
    return lo
```

> **L'arrondi `+1`.** Sans le `+1`, quand `hi = lo + 1` et
> `feasible(mid)`, on pose `lo = mid = lo` - boucle. Avec `+1`,
> `mid = lo + 1 = hi` et on progresse.

---

## 2.3 - Exemple : Aggressive Cows

> $n$ stalles aux positions $x_1 < \dots < x_n$, on doit y placer
> $k$ vaches en **maximisant la distance minimale** entre deux
> vaches consécutives.

**Réponse $d$ faisable ?** On place une vache en $x_1$, puis on
prend gloutonnement la prochaine stalle à distance $\ge d$ ;
faisable ssi on en place au moins $k$. Cette fonction est
$O(n)$ et **monotone décroissante** en $d$ (plus $d$ est grand,
plus dur de caser les vaches).

**Réponse cherchée** : le plus grand $d$ faisable. Bornes :
$d \in [0, x_n - x_1]$. Coût $O(n \log(x_n - x_1))$.

```python
def feasible(d, X, k):
    last, count = X[0], 1
    for x in X[1:]:
        if x - last >= d:
            last = x; count += 1
            if count >= k: return True
    return count >= k
```

L'astuce **n'est pas** l'algorithme glouton - c'est la
reformulation du problème : *résoudre directement* la version
optimisation est dur, *vérifier* qu'une valeur est faisable est
facile.

---

## 2.4 - Quand l'utiliser

Cherche les signaux suivants dans un énoncé :

- "**maximiser le minimum**" ou "**minimiser le maximum**" → presque
  toujours dichotomie sur la réponse.
- Le problème direct est dur, mais "ce paramètre est-il assez gros /
  petit ?" est facile à vérifier en linéaire.
- L'espace de recherche est borné par le problème (max coordonnée,
  somme totale, …).

Ce patron est *omniprésent* (USACO, ICPC, Codeforces). Maîtriser
la reformulation rend tout un pan de problèmes triviaux.

---

## 2.5 - Exercices

:::exercise{id="{{EX_SE_AGGRCOWS}}"}
:::

:::exercise{id="{{EX_SE_PAINTERS}}"}
:::

:::exercise{id="{{EX_SE_SQRT_REAL}}"}
:::
