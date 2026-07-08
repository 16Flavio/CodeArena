# 1. Representations & parcours BFS/DFS

## 1.1 - Intuition

Un **graphe** est un ensemble de sommets relies par des aretes. Il
modelise presque tout : reseaux routiers, dependances entre taches,
relations sociales, grilles de jeu. Deux questions reviennent sans
cesse : « qui est atteignable depuis ici ? » et « quel est le chemin
le plus court ? ». Les deux **parcours** fondamentaux y repondent.

Le parcours en **largeur** (BFS) explore par cercles concentriques :
d'abord les voisins directs, puis les voisins des voisins. Le
parcours en **profondeur** (DFS) plonge le plus loin possible avant
de rebrousser chemin. Le premier mesure des distances, le second
revele la structure (cycles, composantes, ordre).

---

## 1.2 - Representation & algorithmes

Un graphe a $n$ sommets et $m$ aretes se stocke en **liste
d'adjacence** : pour chaque sommet, la liste de ses voisins. C'est
$\Theta(n + m)$ en memoire, contre $\Theta(n^2)$ pour une matrice -
presque toujours le bon choix pour un graphe creux.

```python
from collections import deque

def bfs(adj, s):
    n = len(adj)
    dist = [-1] * n
    dist[s] = 0
    q = deque([s])
    while q:
        u = q.popleft()
        for v in adj[u]:
            if dist[v] == -1:        # jamais vu
                dist[v] = dist[u] + 1
                q.append(v)
    return dist
```

### Invariant du BFS

La file contient toujours des sommets de distance $d$ puis $d+1$, et
jamais deux valeurs eloignees de plus de $1$.

- **Correction (plus court chemin).** La premiere fois qu'on atteint
  un sommet $v$, c'est par un chemin de longueur minimale. Preuve :
  les sommets sortent de la file par distance croissante ; si $v$
  etait atteignable plus court, il aurait ete decouvert depuis un
  sommet sorti plus tot. $\square$

Le DFS, lui, se code recursivement (ou avec une pile explicite) :
visiter un voisin non vu, recurser, revenir.

**Compare les deux parcours** : bascule entre BFS (file) et DFS (pile),
choisis la source, et deroule. Les numeros #k donnent l'ordre de
decouverte ; observe comme BFS s'etend par couches et DFS plonge.

:::viz-graph-traversal{mode="bfs" source="0"}
:::

---

## 1.3 - Complexite

Chaque sommet est enfile une fois, chaque arete examinee au plus deux
fois (une par extremite). D'ou :

$$
T(n, m) = \Theta(n + m).
$$

C'est optimal : il faut au moins regarder chaque sommet et chaque
arete. BFS et DFS partagent cette borne ; ils ne different que par
l'ordre de visite (file contre pile).

---

## 1.4 - Pieges classiques

1. **Marquer a l'enfilement, pas au defilement.** Marquer un sommet
   quand on le sort de la file (au lieu de quand on l'ajoute) le fait
   parfois entrer plusieurs fois - complexite qui explose.
2. **Grilles = graphes implicites.** Une grille $R \times C$ est un
   graphe a $RC$ sommets ; inutile de construire la liste
   d'adjacence, les 4 voisins se calculent a la volee.
3. **Recursion du DFS.** Sur un graphe a $10^5$ sommets en ligne, la
   recursion Python deborde la pile ; passer a une pile explicite ou
   relever `sys.setrecursionlimit`.
4. **Sommets isoles.** Ne pas oublier de lancer le parcours depuis
   **chaque** composante quand on veut tout couvrir.

---

## 1.5 - Ce que chacun revele

BFS donne les distances non ponderees et la couche de proximite. DFS
donne les temps d'entree/sortie, base des algorithmes de la lecon 5
(SCC, ponts). Choisir selon la question : distance minimale ->
BFS ; structure, ordre, cycles -> DFS.

---

## 1.6 - Exercices

:::exercise{id="{{EX_GR_BFS_DIST}}"}
:::

:::exercise{id="{{EX_GR_GRID_BFS}}"}
:::

:::exercise{id="{{EX_GR_ISLANDS}}"}
:::
