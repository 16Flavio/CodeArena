# 3. Enveloppe convexe

## 3.1 - Intuition

L'**enveloppe convexe** d'un nuage de points est le plus petit polygone
convexe qui les contient tous - imaginez un elastique lache autour de
clous plantes. C'est l'une des structures les plus utiles de la
geometrie : elle capture la « forme exterieure » d'un ensemble et sert
de socle a une foule d'algorithmes (diametre, largeur, distance entre
formes).

Le calcul repose entierement sur l'**orientation** (leçon 1) : on garde
un point tant que le contour tourne dans le bon sens, on le retire des
qu'il cree un creux.

---

## 3.2 - Algorithme : monotone chain

L'algorithme d'Andrew trie les points, puis construit l'enveloppe
**inferieure** et **superieure** par une pile.

```python
def convex_hull(points):
    pts = sorted(set(points))
    if len(pts) <= 1:
        return pts
    def half(seq):
        h = []
        for p in seq:
            while len(h) >= 2 and cross(h[-2], h[-1], p) <= 0:
                h.pop()               # retire un tour a droite (ou plat)
            h.append(p)
        return h
    lower = half(pts)
    upper = half(reversed(pts))
    return lower[:-1] + upper[:-1]    # sans les points repetes
```

- **Correction.** Apres le tri, tout point qui provoque un tour non
  strictement a gauche est interieur ou colineaire, donc retire. La
  pile ne contient au final que les sommets, en ordre antihoraire.
- **Colinearite.** Le test `cross <= 0` **exclut** les points alignes
  sur un bord ; utiliser `< 0` les **inclurait**. Choisir selon le
  besoin.

**Deroule l'algorithme** : `step` avance action par action. Regarde la
pile grandir, puis un point creer un tour a droite (`cross ≤ 0`) et se
faire depiler (croix rouge). `run` joue toute la construction.

:::viz-convex-hull
:::

---

## 3.3 - Complexite

$$
T(n) = \underbrace{\Theta(n \log n)}_{\text{tri}} +
\underbrace{\Theta(n)}_{\text{construction}} = \Theta(n \log n).
$$

La construction est lineaire (chaque point est empile et depile au plus
une fois) ; le tri domine.

---

## 3.4 - Pieges classiques

1. **Doublons et points alignes.** Dedupliquer d'abord ; decider
   explicitement si les points colineaires sur un bord comptent comme
   sommets (`<=` vs `<`).
2. **Moins de 3 points.** Gerer a part : un point, ou tous alignes -
   l'enveloppe degenere en point ou segment.
3. **Sens de parcours.** Selon la convention (`<= 0` avec tri
   croissant), l'enveloppe sort antihoraire ; en tenir compte pour
   l'aire signee.
4. **Flottants.** Aucun n'est necessaire : `cross` entier suffit.

---

## 3.5 - Ce que l'enveloppe debloque

Diametre (les deux points les plus eloignes sont des sommets de
l'enveloppe, trouves par **rotating calipers** en temps lineaire sur
l'enveloppe), largeur minimale, distance entre deux nuages, plus petit
rectangle englobant : autant de problemes qui se resolvent **sur
l'enveloppe** plutot que sur tous les points. La construire, c'est
souvent la moitie du travail.

---

## 3.6 - Exercices

:::exercise{id="{{EX_GE_HULL_SIZE}}"}
:::

:::exercise{id="{{EX_GE_HULL_AREA}}"}
:::

:::exercise{id="{{EX_GE_DIAMETER}}"}
:::
