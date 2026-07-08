# 2. Intersection de segments

## 2.1 - Intuition

Savoir si deux segments se croisent est la deuxieme primitive
geometrique par ordre d'importance. Elle sert partout : detecter les
collisions, tester si un polygone est simple, decouper des figures. Et
comme l'orientation, elle se resout **exactement** en entiers, sans
jamais calculer le point d'intersection.

L'idee : deux segments $[A, B]$ et $[C, D]$ se croisent proprement si
$A$ et $B$ sont de part et d'autre de la droite $CD$, **et**
symetriquement $C$ et $D$ de part et d'autre de $AB$. Les cas
colineaires (recouvrement, contact bout a bout) se traitent a part.

---

## 2.2 - Algorithme

```python
def seg_intersect(p1, p2, p3, p4):
    d1 = cross(p3, p4, p1); d2 = cross(p3, p4, p2)
    d3 = cross(p1, p2, p3); d4 = cross(p1, p2, p4)
    # croisement propre : signes opposes des deux cotes
    if ((d1 > 0) != (d2 > 0)) and d1 and d2 and \
       ((d3 > 0) != (d4 > 0)) and d3 and d4:
        return True
    # cas colineaires / contact : une extremite sur l'autre segment
    if d1 == 0 and on_seg(p3, p4, p1): return True
    if d2 == 0 and on_seg(p3, p4, p2): return True
    if d3 == 0 and on_seg(p1, p2, p3): return True
    if d4 == 0 and on_seg(p1, p2, p4): return True
    return False
```

`on_seg(p, q, r)` verifie que $r$, deja **colineaire** a $pq$, est bien
dans la boite englobante de $[p, q]$ - donc sur le segment.

- **Correction.** Les quatre orientations couvrent tous les cas : deux
  signes stricts opposes de chaque cote donnent un croisement en un
  point interieur unique ; un zero signale un contact colineaire, teste
  explicitement. $\square$

**Experimente** : deplace les extremites $A, B, C, D$. Les quatre
orientations $d_1 \dots d_4$ et le verdict se mettent a jour en direct ;
essaie un contact bout a bout pour voir le cas colineaire.

:::viz-segment-intersect
:::

---

## 2.3 - Complexite

$$
\begin{aligned}
\text{deux segments} &: \Theta(1), \\
\text{toutes les paires (}n\text{ segments)} &: \Theta(n^2), \\
\text{polygone simple ?} &: \Theta(n^2).
\end{aligned}
$$

Le test unitaire est constant. Un **balayage** (leçon 4) abaisse la
detection d'une intersection quelconque a $\Theta(n \log n)$.

---

## 2.4 - Pieges classiques

1. **Oublier les cas colineaires.** Le test des signes opposes rate les
   recouvrements et les contacts bout a bout ; les traiter par
   `on_seg`.
2. **Bornes inclusives.** Selon que les extremites comptent ou non
   comme intersection, ajuster les tests - definir clairement la
   convention.
3. **Aretes adjacentes d'un polygone.** Elles partagent un sommet : ne
   pas le compter comme une auto-intersection, mais detecter un
   **recouvrement** colineaire, lui, interdit.
4. **Point d'intersection flottant.** Inutile ici : le predicat
   booleen se calcule entierement en entiers exacts.

---

## 2.5 - De la primitive aux applications

Compter les paires qui se croisent, tester la simplicite d'un polygone,
verifier qu'un trace ne se recoupe pas, decouper une scene : tout part
du meme predicat. Le calcul **exact du point** d'intersection (en
rationnels) n'intervient que lorsqu'on en a vraiment besoin - souvent,
savoir **s'il existe** suffit.

---

## 2.6 - Exercices

:::exercise{id="{{EX_GE_SEG_INTERSECT}}"}
:::

:::exercise{id="{{EX_GE_COUNT_INTERSECTIONS}}"}
:::

:::exercise{id="{{EX_GE_SIMPLE_POLYGON}}"}
:::
