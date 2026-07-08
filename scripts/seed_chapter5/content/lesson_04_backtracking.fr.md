# 4. Backtracking & branch and bound

## 4.1 - Intuition

Quand aucune structure (monotonie, sous-structure gloutonne) ne
permet de raccourci, il reste l'**exploration exhaustive**. Le
backtracking la rend praticable : on construit une solution
**incrémentalement**, et dès qu'un préfixe viole une contrainte, on
**abandonne** (backtrack) toute la branche - on ne perd pas de temps
à compléter un début voué à l'échec.

L'image est celle d'un labyrinthe exploré en profondeur : on avance
tant qu'on peut, et au premier cul-de-sac on rebrousse chemin
jusqu'au dernier embranchement non épuisé. La différence avec une
énumération brute des $b^n$ candidats est l'**élagage** : couper une
branche à la profondeur $d$ élimine d'un coup tous ses descendants.

---

## 4.2 - Algorithme : le squelette

Tout backtracking suit le même patron récursif.

```python
def backtrack(state, partial):
    if is_complete(partial):
        record(partial)
        return
    for choice in candidates(state, partial):
        if is_valid(partial, choice):     # élagage
            partial.append(choice)
            backtrack(advance(state, choice), partial)
            partial.pop()                 # on défait le choix
```

Le motif **choisir - explorer - défaire** (`append` ... `pop`) est la
signature du backtracking. Pour les **N-reines**, l'état est la
ligne courante et `is_valid` teste colonne et diagonales via trois
ensembles :

```python
def solve(n):
    cols, diag, anti = set(), set(), set()
    def bt(r):
        if r == n:
            return 1
        total = 0
        for c in range(n):
            if c in cols or (r - c) in diag or (r + c) in anti:
                continue                  # élagage O(1)
            cols.add(c); diag.add(r - c); anti.add(r + c)
            total += bt(r + 1)
            cols.discard(c); diag.discard(r - c); anti.discard(r + c)
        return total
    return bt(0)
```

Placer une reine par ligne encode déjà la contrainte « une par
ligne » ; les ensembles couvrent le reste en $O(1)$.

**Explore l'arbre** : `run` déroule le backtracking des N-reines,
placement ligne par ligne. Une croix rouge marque un élagage (colonne ou
diagonale attaquée), et l'algorithme rebrousse chemin aux culs-de-sac.

:::viz-backtracking{n="6"}
:::

---

## 4.3 - Complexité

Dans le pire cas, le backtracking reste exponentiel : l'arbre de
recherche a une taille

$$
O(b^n),
$$

où $b$ est le facteur de branchement et $n$ la profondeur. L'élagage
ne change pas cette borne pire cas, mais **en pratique** il réduit
l'arbre exploré de plusieurs ordres de grandeur. Pour les N-reines,
les $n^n$ placements naïfs tombent à $n!$ par la contrainte de
colonne, puis bien plus bas encore par les diagonales.

Le **branch and bound** ajoute une **borne** : à chaque nœud, on
estime la meilleure valeur atteignable dans le sous-arbre. Si cette
borne est déjà pire que la meilleure solution connue, on coupe. C'est
l'élagage appliqué à l'**optimisation** plutôt qu'à la satisfaction
de contraintes.

---

## 4.4 - Pièges classiques

1. **Oublier de défaire le choix.** Sans le `pop` (ou le `discard`),
   l'état fuit vers les branches sœurs et corrompt l'exploration.
2. **Élaguer trop tard.** Tester la validité **avant** de descendre,
   pas après avoir complété la solution : c'est là tout le gain.
3. **États partagés mutables.** Un dictionnaire ou un ensemble
   modifié en place doit être restauré exactement ; préférer des
   marqueurs symétriques (`add` / `discard`).
4. **Confondre comptage et énumération.** Compter les solutions ne
   demande pas de les stocker : renvoyer un entier suffit et évite
   une explosion mémoire.

---

## 4.5 - Quand l'exponentiel est acceptable

Le backtracking est le bon outil quand $n$ est **petit** (une
vingtaine d'éléments), ou quand l'élagage est si efficace que
l'instance réelle reste minuscule. Au-delà, on combine avec d'autres
idées : **meet in the middle** (couper l'ensemble en deux moitiés de
$2^{n/2}$), DP sur masques de bits (`dp[masque][...]`), ou une
relaxation qui fournit une borne serrée pour le branch and bound.

---

## 4.6 - Exercices

:::exercise{id="{{EX_PA_NQUEENS}}"}
:::

:::exercise{id="{{EX_PA_SUBSET_COUNT}}"}
:::

:::exercise{id="{{EX_PA_HAMILTON}}"}
:::
