# 1. Union-Find (DSU)

## 1.1 - Intuition

Comment savoir, au fil d'ajouts de liens, si deux elements sont
**connectes** ? Reconstruire les composantes a chaque question serait
lent. La structure **Union-Find** (ou DSU, *Disjoint Set Union*)
maintient une partition d'elements en ensembles disjoints et repond a
deux operations en temps quasi constant :

- **union** : fusionner les ensembles de deux elements ;
- **find** : trouver le representant (la racine) d'un element.

L'idee : chaque ensemble est un arbre, chaque element pointe vers un
parent, et la racine identifie l'ensemble. Deux elements sont
connectes ssi ils ont la meme racine.

---

## 1.2 - Algorithme & optimisations

```python
class DSU:
    def __init__(self, n):
        self.par = list(range(n))
        self.size = [1] * n

    def find(self, x):
        while self.par[x] != x:
            self.par[x] = self.par[self.par[x]]   # compression de chemin
            x = self.par[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.size[ra] < self.size[rb]:         # union par taille
            ra, rb = rb, ra
        self.par[rb] = ra
        self.size[ra] += self.size[rb]
        return True
```

Deux optimisations rendent la structure efficace :

- **Compression de chemin** : lors d'un `find`, on rebranche les
  noeuds directement (ou presque) sur la racine.
- **Union par taille (ou rang)** : on accroche toujours le petit arbre
  sous le grand, gardant les arbres plats.

---

## 1.3 - Complexite

Avec les **deux** optimisations, une suite de $m$ operations sur $n$
elements coute

$$
T = O\bigl(m \cdot \alpha(n)\bigr),
$$

ou $\alpha$ est l'**inverse de la fonction d'Ackermann** : elle croit
si lentement que $\alpha(n) \le 4$ pour tout $n$ physiquement
imaginable. En pratique, chaque operation est **constante**.

Sans optimisation, un `find` peut couter $\Theta(n)$ (arbre
degenere en liste) ; avec une seule des deux, on tombe a
$\Theta(\log n)$ amorti.

---

## 1.4 - Pieges classiques

1. **Union sans `find`.** Toujours unir les **racines**, pas les
   elements bruts, sinon on casse la structure d'arbre.
2. **Oublier une optimisation.** Compression **et** union par taille
   sont necessaires pour la borne $\alpha(n)$.
3. **Pas de suppression.** Le DSU ne supporte pas la separation d'un
   ensemble ; pour de la connectivite dynamique avec suppressions, il
   faut d'autres techniques (offline, LCT).
4. **Recursion du `find`.** Sur de grands arbres, une version
   recursive deborde la pile ; preferer la boucle ci-dessus.

---

## 1.5 - Variantes puissantes

Le DSU se decline : **union par parite** (stocker la relation
0/1 a la racine, pour des contraintes « meme / different » et la
bipartition), **DSU pondere** (distances relatives), ou **DSU
persistant**. Kruskal (chapitre graphes) en est l'application
vedette. Une structure simple, un eventail d'usages.

---

## 1.6 - Exercices

:::exercise{id="{{EX_DS_DSU_QUERY}}"}
:::

:::exercise{id="{{EX_DS_DSU_MAXSIZE}}"}
:::

:::exercise{id="{{EX_DS_DSU_PARITY}}"}
:::
