# 4. Balayage (sweep line)

## 4.1 - Intuition

Le **balayage** (sweep line) est le paradigme roi de la geometrie a
grande echelle. On imagine une droite verticale qui glisse de gauche a
droite ; a mesure qu'elle avance, on maintient une structure des objets
qu'elle **traverse** et on traite les evenements (apparition,
disparition, croisement) dans l'ordre des abscisses.

L'idee-force : reduire un probleme geometrique 2D a une suite de
problemes 1D le long de la ligne de balayage. La paire de points la
plus proche, l'union de rectangles, la detection d'intersections en
$O(n \log n)$ : autant d'applications d'un meme schema.

---

## 4.2 - Algorithmes

### Paire la plus proche

Trier les points par $x$, balayer en maintenant une fenetre des points
dont l'abscisse est a moins de $d$ (la meilleure distance courante),
tries par $y$. Pour chaque nouveau point, seuls les voisins dans une
bande de hauteur $2d$ sont a comparer - un nombre **constant**.

**Regarde le balayage vivre** : la ligne verticale glisse, la bande
active de largeur $d$ la suit, et seuls les voisins a l'interieur sont
compares. La meilleure paire courante est reliee en vert.

:::viz-sweep-line
:::

### Union de rectangles

Trier les abscisses distinctes. Entre deux abscisses consecutives,
l'ensemble des rectangles actifs est fixe ; la hauteur couverte est la
longueur de l'**union de leurs intervalles $y$**. Aire de la tranche =
largeur $\times$ hauteur couverte.

```python
def union_area(rects):
    xs = sorted({r[0] for r in rects} | {r[2] for r in rects})
    total = 0
    for x1, x2 in zip(xs, xs[1:]):
        ys = sorted((ry1, ry2) for rx1, ry1, rx2, ry2 in rects
                    if rx1 <= x1 and x2 <= rx2)
        covered = 0; cur = None
        for lo, hi in ys:                 # union d'intervalles 1D
            if cur is None or lo > cur[1]:
                if cur: covered += cur[1] - cur[0]
                cur = [lo, hi]
            else:
                cur[1] = max(cur[1], hi)
        if cur: covered += cur[1] - cur[0]
        total += (x2 - x1) * covered
    return total
```

---

## 4.3 - Complexite

$$
\begin{aligned}
\text{paire la plus proche} &: \Theta(n \log n), \\
\text{union de rectangles (segment tree)} &: \Theta(n \log n), \\
\text{recouvrement max (compression)} &: \Theta(n^2)\ \text{naif}.
\end{aligned}
$$

Le tri des evenements domine ; la structure active se met a jour en
$O(\log n)$ par evenement avec un arbre de segments.

---

## 4.4 - Pieges classiques

1. **Bords inclusifs/exclusifs.** Pour le recouvrement, fixer une
   convention (par ex. $[x_1, x_2)$) et l'appliquer partout, sinon les
   comptes des cellules frontieres divergent.
2. **Compression de coordonnees.** Indispensable quand les coordonnees
   sont grandes : ne garder que les valeurs distinctes qui delimitent
   les cellules.
3. **Depassement d'aire.** L'aire d'union peut atteindre $\sim
   10^{18}$ ; entiers 64 bits (ou Python).
4. **Ordre des evenements.** En cas d'egalite d'abscisse, l'ordre de
   traitement (ouverture avant fermeture) change le resultat - le
   definir soigneusement.

---

## 4.5 - Le dernier paradigme

Detection d'intersections, aire et perimetre d'une union, plus proche
paire, enveloppe de segments, problemes de rectangles et
d'intervalles : le balayage transforme une geometrie statique en un
film ordonne d'evenements. C'est la conclusion naturelle du chapitre -
et souvent la difference entre un $O(n^2)$ naif et un $O(n \log n)$ qui
passe.

---

## 4.6 - Exercices

:::exercise{id="{{EX_GE_CLOSEST_PAIR}}"}
:::

:::exercise{id="{{EX_GE_RECT_UNION}}"}
:::

:::exercise{id="{{EX_GE_MAX_OVERLAP}}"}
:::
