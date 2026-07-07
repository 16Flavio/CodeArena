# 5. Connectivite : SCC, ponts, articulation

## 5.1 - Intuition

Au-dela de « le graphe est-il connexe ? », on veut mesurer sa
**robustesse** : quels sommets ou aretes sont critiques ? Le DFS,
enrichi de deux horloges, revele cette structure fine.

- **Composantes fortement connexes** (SCC) : dans un graphe oriente,
  les groupes de sommets mutuellement atteignables.
- **Ponts** : les aretes dont le retrait deconnecte le graphe.
- **Points d'articulation** : les sommets dont le retrait deconnecte
  le graphe.

---

## 5.2 - Algorithmes & preuves

### low-link : le cœur de la lecon

Le DFS attribue a chaque sommet une date de decouverte `disc[u]`. On
calcule `low[u]` : la plus petite date atteignable depuis le
sous-arbre de $u$ en empruntant **au plus une** arete retour.

```python
def bridges(n, adj):              # adj[u] = [(v, id_arete), ...]
    disc = [-1] * n; low = [0] * n; timer = [0]; count = [0]
    def dfs(u, pe):
        disc[u] = low[u] = timer[0]; timer[0] += 1
        for v, ei in adj[u]:
            if ei == pe:          # ne pas repasser par l'arete parente
                continue
            if disc[v] == -1:
                dfs(v, ei)
                low[u] = min(low[u], low[v])
                if low[v] > disc[u]:
                    count[0] += 1     # (u, v) est un pont
            else:
                low[u] = min(low[u], disc[v])
    for s in range(n):
        if disc[s] == -1:
            dfs(s, -1)
    return count[0]
```

- **Pont.** L'arete vers un fils $v$ est un pont **ssi**
  `low[v] > disc[u]` : aucun descendant de $v$ ne peut remonter au
  dessus de $u$ sans elle.
- **Articulation.** Un sommet interne $u$ est un point d'articulation
  ssi un fils $v$ verifie `low[v] >= disc[u]`. La **racine** l'est
  ssi elle a au moins deux fils dans l'arbre DFS.

### SCC (Kosaraju)

Un premier DFS empile les sommets par date de fin ; un second DFS sur
le graphe **transpose**, dans l'ordre inverse de la pile, isole chaque
SCC. La correction repose sur le fait que le sommet de plus grande
date de fin appartient a une SCC « source » du graphe condense.

---

## 5.3 - Complexite

Tous ces algorithmes sont des DFS augmentes d'un travail constant par
arete :

$$
T(n, m) = \Theta(n + m).
$$

Kosaraju fait deux parcours (donc $2(n+m)$) ; Tarjan obtient les SCC
en un seul, meme borne asymptotique.

---

## 5.4 - Pieges classiques

1. **Arete parente vs arete retour.** En cherchant les ponts, ignorer
   l'arete par laquelle on est arrive - mais **une seule fois** ; sur
   un graphe avec aretes multiples, indexer par identifiant d'arete,
   pas par sommet.
2. **Cas de la racine.** La regle d'articulation differe pour la
   racine du DFS (deux fils) et pour les sommets internes
   (`low[v] >= disc[u]`).
3. **Graphe non connexe.** Relancer le DFS sur chaque composante.
4. **Recursion profonde.** Sur $10^5$ sommets, relever la limite de
   recursion ou passer en iteratif.

---

## 5.5 - Pourquoi ca compte

Ces notions modelisent la tolerance aux pannes : un pont est un lien
reseau critique, un point d'articulation un routeur dont la chute
isole une region. Les SCC condensent un graphe oriente en un DAG,
premiere etape de nombreux algorithmes (2-SAT, ordonnancement).

---

## 5.6 - Exercices

:::exercise{id="{{EX_GR_SCC}}"}
:::

:::exercise{id="{{EX_GR_BRIDGES}}"}
:::

:::exercise{id="{{EX_GR_ARTIC}}"}
:::
