# 3. Plus courts chemins

## 3.1 - Intuition

Des que les aretes portent un **poids** (distance, cout, temps), le
BFS ne suffit plus : le chemin avec le moins d'aretes n'est pas le
moins couteux. Trois algorithmes couvrent tous les cas selon la
nature des poids et le nombre de sources.

- **Dijkstra** : une source, poids positifs. Le plus rapide.
- **Bellman-Ford** : une source, poids negatifs autorises, detecte
  les cycles negatifs.
- **Floyd-Warshall** : **toutes** les paires, en une passe.

---

## 3.2 - Algorithmes & preuves

### Dijkstra

```python
import heapq

def dijkstra(adj, s, n):
    dist = [float('inf')] * n
    dist[s] = 0
    pq = [(0, s)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:              # entree perimee
            continue
        for v, w in adj[u]:
            if d + w < dist[v]:
                dist[v] = d + w
                heapq.heappush(pq, (dist[v], v))
    return dist
```

- **Correction.** Quand un sommet $u$ est extrait du tas, `dist[u]`
  est definitif. Preuve : soit un chemin plus court vers $u$ ; il
  passe par un sommet $x$ hors du tas final avec `dist[x] < dist[u]`,
  or $x$ aurait ete extrait avant $u$ - contradiction. Cet argument
  **exige des poids $\ge 0$** ; une arete negative pourrait rabaisser
  `dist[u]` apres son extraction. $\square$

### Bellman-Ford

Relaxer **toutes** les aretes $n-1$ fois suffit : un plus court
chemin simple a au plus $n-1$ aretes. Une $n$-ieme passe qui relache
encore signale un **cycle negatif**.

### Floyd-Warshall

$$
d[i][j] = \min\bigl(d[i][j],\ d[i][k] + d[k][j]\bigr)
$$

en faisant croitre l'ensemble des sommets intermediaires autorises.
La boucle **externe** porte sur $k$ : c'est l'ordre qui garantit la
correction par recurrence sur $k$.

---

## 3.3 - Complexite

$$
\begin{aligned}
\text{Dijkstra (tas)} &: \Theta\bigl((n + m)\log n\bigr), \\
\text{Bellman-Ford} &: \Theta(n\,m), \\
\text{Floyd-Warshall} &: \Theta(n^3).
\end{aligned}
$$

Dijkstra pour une source rapide ; Floyd-Warshall quand $n$ est petit
mais qu'on veut toutes les paires ; Bellman-Ford quand des poids
negatifs sont en jeu.

---

## 3.4 - Pieges classiques

1. **Dijkstra + poids negatif = faux.** L'argument de finalite
   s'effondre. Utiliser Bellman-Ford.
2. **Entrees perimees dans le tas.** Ne pas supprimer les vieilles
   entrees ; tester `d > dist[u]` et les ignorer.
3. **Cycle negatif atteignable.** Une source virtuelle reliee a tous
   les sommets a cout $0$ permet de detecter **n'importe** quel cycle
   negatif, pas seulement ceux issus d'une source donnee.
4. **Ordre des boucles de Floyd.** $k$ **doit** etre la boucle
   externe. $k$ a l'interieur donne des reponses fausses.

---

## 3.5 - Choisir le bon outil

Poids uniformes -> BFS (lecon 1). Poids positifs, une source ->
Dijkstra. Poids negatifs -> Bellman-Ford. Toutes les paires sur petit
graphe -> Floyd-Warshall. Le bon reflexe est de lire les contraintes
(signe des poids, $n$, nombre de requetes) avant de coder.

---

## 3.6 - Exercices

:::exercise{id="{{EX_GR_DIJKSTRA}}"}
:::

:::exercise{id="{{EX_GR_NEGCYCLE}}"}
:::

:::exercise{id="{{EX_GR_FLOYD}}"}
:::
