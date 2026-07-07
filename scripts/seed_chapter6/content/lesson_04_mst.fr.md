# 4. Arbres couvrants minimaux

## 4.1 - Intuition

Etant donne un graphe pondere connexe, un **arbre couvrant** relie
tous les sommets avec exactement $n-1$ aretes et sans cycle. Parmi
tous les arbres couvrants, le **minimal** (MST) est celui de poids
total le plus faible : le reseau le moins cher qui garde tout le monde
connecte.

Deux gloutons resolvent le probleme, chacun avec sa preuve par
argument d'echange (cf. le chapitre sur les paradigmes).

- **Kruskal** : trier les aretes, ajouter la plus legere qui ne cree
  pas de cycle.
- **Prim** : faire grossir un seul arbre en ajoutant l'arete sortante
  la plus legere.

---

## 4.2 - Algorithme & preuve

### Kruskal

```python
def kruskal(n, edges):            # edges = [(w, u, v), ...]
    edges.sort()
    par = list(range(n))
    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    total = 0
    for w, u, v in edges:
        ru, rv = find(u), find(v)
        if ru != rv:              # ne cree pas de cycle
            par[ru] = rv
            total += w
    return total
```

### Propriete de coupe

- **Theoreme.** Pour toute **coupe** (partition des sommets en deux),
  l'arete **de poids minimal** qui traverse la coupe appartient a un
  MST. Preuve par echange : soit un MST $T$ ne la contenant pas ;
  ajouter cette arete cree un cycle qui recroise la coupe par une
  arete au moins aussi lourde ; l'echanger ne fait pas augmenter le
  poids. $\square$

Kruskal applique cette propriete : chaque arete ajoutee est la plus
legere traversant la coupe separant sa composante du reste.

---

## 4.3 - Complexite

Kruskal est domine par le tri, plus les operations d'Union-Find quasi
constantes :

$$
T(n, m) = \Theta\bigl(m \log m\bigr).
$$

Prim avec un tas atteint $\Theta(m \log n)$. Les deux sont
essentiellement equivalents ; Kruskal brille sur les graphes creux
donnes par liste d'aretes.

---

## 4.4 - Pieges classiques

1. **Graphe non connexe.** Il n'existe alors aucun arbre couvrant ;
   detecter le cas (moins de $n-1$ aretes retenues) et le signaler.
2. **Goulot minimal != MST unique.** Le MST minimise **aussi** la
   plus grande arete (arbre de goulot minimal), mais un arbre de
   goulot minimal n'est pas forcement un MST.
3. **Union-Find sans compression.** Sans compression de chemin ni
   union par rang, les `find` degenerent en $\Theta(n)$.
4. **Aretes de poids egaux.** Plusieurs MST distincts peuvent
   coexister ; en tenir compte pour les questions d'unicite ou de
   second meilleur arbre.

---

## 4.5 - Au-dela du minimum

Le meme squelette resout des variantes : arbre de goulot minimal
(minimiser l'arete maximale), deuxieme meilleur arbre couvrant
(echanger une arete du MST contre la meilleure de remplacement), ou
maximiser le poids en triant a l'envers. Maitriser la propriete de
coupe, c'est tenir toute la famille.

---

## 4.6 - Exercices

:::exercise{id="{{EX_GR_MST}}"}
:::

:::exercise{id="{{EX_GR_BOTTLENECK}}"}
:::

:::exercise{id="{{EX_GR_SECOND_MST}}"}
:::
