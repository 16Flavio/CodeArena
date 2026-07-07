# 2. Applications des parcours

## 2.1 - Intuition

Un simple parcours, bien exploite, resout une surprenante quantite de
problemes. La cle est de **decorer** le parcours : compter ses
lancements, colorier au passage, ou lire l'ordre de fin. Trois
applications classiques illustrent le principe.

- **Composantes connexes** : un parcours par composante.
- **Bipartisme** : un 2-coloriage alternant.
- **Tri topologique** : ordonner les taches d'un graphe de
  dependances sans cycle.

---

## 2.2 - Algorithmes & preuves

### Composantes connexes

Lancer un parcours depuis chaque sommet non encore visite ; le nombre
de lancements est le nombre de composantes. Un **Union-Find** donne la
meme reponse en fusionnant les extremites de chaque arete.

### Bipartisme

Colorier la source en $0$, ses voisins en $1$, et ainsi de suite en
alternant. Un conflit (une arete entre deux memes couleurs) prouve la
non-bipartite.

- **Theoreme.** Un graphe est biparti **ssi** il ne contient aucun
  cycle de longueur impaire. Un conflit de coloriage ferme exactement
  un cycle impair ; reciproquement, l'absence de conflit fournit une
  bipartition valide. $\square$

### Tri topologique (algorithme de Kahn)

```python
import heapq

def topo(n, adj, indeg):
    h = [i for i in range(n) if indeg[i] == 0]
    heapq.heapify(h)                 # tas-min -> ordre lexicographique
    order = []
    while h:
        u = heapq.heappop(h)
        order.append(u)
        for v in adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                heapq.heappush(h, v)
    return order if len(order) == n else None   # None = cycle
```

Un sommet ne peut sortir qu'une fois toutes ses dependances emises.
Si, a la fin, il manque des sommets, ils forment un cycle : aucun
d'eux n'atteint jamais un degre entrant nul.

---

## 2.3 - Complexite

Les trois algorithmes sont des parcours, donc **lineaires** :

$$
T(n, m) = \Theta(n + m).
$$

Le tri topologique lexicographique remplace la file par un tas-min,
ajoutant un facteur logarithmique :

$$
T(n, m) = \Theta\bigl((n + m) \log n\bigr).
$$

---

## 2.4 - Pieges classiques

1. **Bipartisme sur graphe non connexe.** Colorier **chaque**
   composante ; oublier une composante isolee fausse le verdict.
2. **Tri topologique = graphe oriente sans cycle.** Sur un graphe non
   oriente ou cyclique, la notion n'a pas de sens ; Kahn le detecte
   en comptant les sommets emis.
3. **Degre entrant mal initialise.** Chaque arete $u \to v$
   incremente `indeg[v]`, pas `indeg[u]`. Une inversion casse tout.
4. **Cycle vs impossible.** Retourner explicitement une valeur "cycle"
   distincte plutot qu'un ordre partiel silencieux.

---

## 2.5 - Le meme outil, mille usages

Detection de cycle, ordonnancement de compilation, resolution de
dependances de paquets, coloriage de conflits : tous se ramenent a un
parcours decore. Apprendre a **reconnaitre** le parcours cache dans un
enonce est la competence centrale de cette lecon.

---

## 2.6 - Exercices

:::exercise{id="{{EX_GR_COMPONENTS}}"}
:::

:::exercise{id="{{EX_GR_BIPARTITE}}"}
:::

:::exercise{id="{{EX_GR_TOPOSORT}}"}
:::
