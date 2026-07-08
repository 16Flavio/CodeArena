# 1. Vecteurs, produits & orientation

## 1.1 - Intuition

La geometrie algorithmique repose sur une operation minuscule : le
**produit vectoriel** en 2D. Il repond a la question la plus
frequente - « en quel sens tourne-t-on ? » - et de la decoulent l'aire,
l'orientation, l'appartenance, l'intersection.

Crucialement, si les coordonnees sont **entieres**, le produit
vectoriel l'est aussi. On evite alors totalement les flottants et leurs
erreurs d'arrondi, source de bugs geometriques notoires. Toute cette
lecon reste en arithmetique **exacte**.

---

## 1.2 - Algorithmes

### Produit vectoriel & orientation

Pour trois points $A$, $B$, $C$ :

$$
\overrightarrow{AB} \times \overrightarrow{AC} =
(b_x - a_x)(c_y - a_y) - (b_y - a_y)(c_x - a_x).
$$

```python
def cross(o, a, b):
    return (a[0]-o[0]) * (b[1]-o[1]) - (a[1]-o[1]) * (b[0]-o[0])
```

Le **signe** dit tout : positif = $C$ a gauche de $A \to B$
(antihoraire), negatif = a droite (horaire), nul = alignes.

**A toi de jouer** : glisse le point $C$ et regarde le signe de
`cross(A, B, C)` basculer a l'instant ou il traverse la droite $A \to B$.

:::viz-cross-product
:::

### Aire par la formule du lacet

Pour un polygone $P_0, \dots, P_{n-1}$ :

$$
2A = \left| \sum_{i=0}^{n-1} (x_i y_{i+1} - x_{i+1} y_i) \right|,
$$

les indices etant cycliques. On renvoie $2A$ pour rester entier.

### Theoreme de Pick

Pour un polygone a sommets entiers,

$$
A = I + \frac{B}{2} - 1,
$$

ou $I$ est le nombre de points entiers **interieurs** et $B$ ceux du
**bord**. Comme $B = \sum \gcd(|\Delta x|, |\Delta y|)$ par arete, on
en tire $I$ directement.

---

## 1.3 - Complexite

$$
\begin{aligned}
\text{produit vectoriel / orientation} &: \Theta(1), \\
\text{aire, Pick} &: \Theta(n).
\end{aligned}
$$

Tout est lineaire ou constant, et **exact** en entiers.

---

## 1.4 - Pieges classiques

1. **Flottants inutiles.** Ne jamais convertir en flottant quand les
   entrees sont entieres ; le produit vectoriel entier suffit et evite
   les erreurs d'arrondi.
2. **Debordement.** Pour des coordonnees $\sim 10^9$, le produit
   vectoriel atteint $\sim 10^{18}$ : tenir dans un entier 64 bits (ou
   Python, sans limite).
3. **Aire signee vs absolue.** La formule du lacet donne l'aire
   **signee** (positive si antihoraire) ; prendre la valeur absolue si
   l'ordre n'est pas garanti.
4. **Pick hors cadre.** Le theoreme exige des sommets **entiers** et un
   polygone **simple** ; sinon la formule ne tient pas.

---

## 1.5 - La brique de tout le reste

Orientation, aire, appartenance a un demi-plan, comparaison angulaire
pour trier : le produit vectoriel est le seul primitif dont on a
vraiment besoin. Intersection de segments (leçon 2), enveloppe convexe
(leçon 3), balayage (leçon 4) en decoulent tous. Le maitriser en
entiers, c'est batir sur du roc.

---

## 1.6 - Exercices

:::exercise{id="{{EX_GE_ORIENT}}"}
:::

:::exercise{id="{{EX_GE_POLY_AREA}}"}
:::

:::exercise{id="{{EX_GE_PICK}}"}
:::
