# 6. Flots & couplages

## 6.1 - Intuition

Imaginons un reseau de tuyaux : chaque arc a une **capacite** maximale.
Combien d'eau peut-on faire passer d'une source $s$ a un puits $t$ ?
C'est le probleme du **flot maximal**, et il est etonnamment central :
une foule de problemes combinatoires (couplages, affectations,
coupes) s'y ramenent.

L'idee des chemins augmentants : tant qu'il reste un chemin de $s$ a
$t$ ou l'on peut pousser du flot, on le fait. Le **graphe residuel**
autorise meme a « annuler » du flot deja envoye, ce qui permet de se
corriger.

---

## 6.2 - Algorithme & theoreme

### Chemins augmentants (Edmonds-Karp)

Tant qu'un chemin augmentant existe dans le graphe residuel (trouve
par BFS), pousser le long de ce chemin le minimum des capacites
residuelles, et mettre a jour les arcs directs et retour.

```python
# Chaque arc stocke une capacite residuelle ; l'arc retour
# (initialement 0) recoit le flot pousse, autorisant l'annulation.
def augment(residual, s, t):
    # BFS pour trouver un chemin s -> t a capacite residuelle > 0,
    # renvoyer le goulot pousse (0 si aucun chemin).
    ...
```

### Theoreme flot-max / coupe-min

- **Theoreme.** La valeur du flot maximal egale la capacite de la
  **coupe minimale** (une partition $S \ni s$, $\bar S \ni t$
  minimisant la somme des capacites des arcs de $S$ vers
  $\bar S$). Preuve : tout flot est borne par toute coupe ; quand
  Edmonds-Karp s'arrete, l'ensemble des sommets atteignables dans le
  residuel forme une coupe **saturee**, donc egale au flot. $\square$

### Couplage biparti = flot unitaire

Un couplage biparti maximal se calcule en reliant une source a tous
les sommets de gauche, tous ceux de droite au puits, capacites $1$.
L'algorithme de Kuhn est la specialisation directe de cette idee.

---

## 6.3 - Complexite

$$
\begin{aligned}
\text{Edmonds-Karp} &: \Theta(V E^2), \\
\text{Dinic} &: \Theta(V^2 E), \\
\text{Kuhn (couplage biparti)} &: \Theta(V E).
\end{aligned}
$$

Dinic est le choix pratique pour le flot general ; Kuhn suffit
largement pour les couplages de taille moyenne.

---

## 6.4 - Pieges classiques

1. **Oublier les arcs retour.** Sans eux, pas d'annulation possible,
   et l'algorithme reste bloque sur un flot sous-optimal.
2. **BFS vs DFS.** Edmonds-Karp **exige** un BFS (plus court chemin
   augmentant) pour sa borne ; un DFS naif peut etre exponentiel.
3. **Konig.** Dans un graphe biparti, couverture de sommets minimale
   = couplage maximal. Ne pas la recalculer par force brute.
4. **Capacites nulles.** Ignorer les arcs de capacite residuelle $0$
   lors de la recherche de chemin.

---

## 6.5 - Un marteau universel

Affectation de taches, ordonnancement, selection de projets,
segmentation d'image, tournois : d'innombrables problemes se
**reduisent** a un flot ou un couplage. Reconnaitre la reduction -
modeliser l'enonce comme un reseau - est la vraie competence, bien
plus que reciter l'algorithme.

---

## 6.6 - Exercices

:::exercise{id="{{EX_GR_MAXFLOW}}"}
:::

:::exercise{id="{{EX_GR_BIPMATCH}}"}
:::

:::exercise{id="{{EX_GR_MINVC}}"}
:::
