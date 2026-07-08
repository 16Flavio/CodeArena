# 3. Fenwick, sparse table & statistiques d'ordre

## 3.1 - Intuition

L'arbre de segments est puissant mais un peu lourd. Pour deux besoins
tres frequents, des structures plus legeres suffisent :

- **Fenwick (BIT)** : sommes prefixes dynamiques, en quelques lignes.
- **Sparse table** : minimum de plage sur un tableau **statique**, en
  $O(1)$ par requete.

Et une application phare : les **statistiques d'ordre** (le $k$-ieme
plus petit) via un Fenwick indexe par valeur.

---

## 3.2 - Algorithmes

### Arbre de Fenwick

Un BIT stocke des sommes partielles alignees sur les bits de poids
faible. La magie tient dans `i & -i`, qui isole le dernier bit a 1.

```python
def update(bit, n, i, delta):     # i en 1-indexe
    while i <= n:
        bit[i] += delta
        i += i & -i               # saut vers le bloc parent
def prefix(bit, i):               # somme a[1..i]
    s = 0
    while i > 0:
        s += bit[i]
        i -= i & -i               # descente par blocs
    return s
```

La somme de plage est `prefix(r) - prefix(l-1)`.

**Deroule les sauts de bits** : prefix(i) descend par blocs (i -= i & -i), update(i) remonte (i += i & -i), depuis un meme indice i.

:::viz-fenwick{data="3,1,4,1,5,9,2,6" i="6"}
:::

### Sparse table (RMQ statique)

Precalculer `sp[k][i]` = minimum de la plage $[i, i + 2^k)$. Une
requete $[l, r]$ se couvre par **deux** blocs de longueur
$2^{\lfloor \log_2(r-l+1) \rfloor}$ qui se chevauchent - sans
consequence, car le min est **idempotent** ($\min(x, x) = x$).

### Statistiques d'ordre

Un Fenwick indexe par **valeur** compte les occurrences. Le $k$-ieme
plus petit se trouve par **descente binaire** : parcourir les bits de
haut en bas en avancant tant que la somme cumulee reste $< k$.

---

## 3.3 - Complexite

$$
\begin{aligned}
\text{Fenwick (maj / requete)} &: \Theta(\log n), \\
\text{sparse table (construction)} &: \Theta(n \log n), \\
\text{sparse table (requete)} &: \Theta(1), \\
\text{$k$-ieme (descente sur BIT)} &: \Theta(\log V).
\end{aligned}
$$

Le Fenwick bat l'arbre de segments d'un facteur constant en memoire et
en constante ; la sparse table est imbattable en requete mais fige le
tableau.

---

## 3.4 - Pieges classiques

1. **Fenwick en 1-indexe.** Le `i & -i` suppose des indices commencant
   a $1$ ; decaler les indices d'entree.
2. **Sparse table sur donnees mutables.** Elle ne supporte **aucune**
   mise a jour ; toute modification invalide le pretraitement.
3. **Idempotence requise.** La sparse table $O(1)$ marche pour min,
   max, pgcd - pas pour la somme (le chevauchement compterait deux
   fois).
4. **Domaine de valeurs.** Pour le $k$-ieme, dimensionner le BIT sur
   l'etendue des valeurs (ou les compresser).

---

## 3.5 - Choisir la bonne structure

Sommes dynamiques -> Fenwick. Min statique, requetes massives ->
sparse table. Min dynamique -> arbre de segments. $k$-ieme / rang ->
Fenwick par valeur. Chaque structure echange de la generalite contre
de la vitesse ; lire les contraintes guide le choix.

---

## 3.6 - Exercices

:::exercise{id="{{EX_DS_FENWICK}}"}
:::

:::exercise{id="{{EX_DS_SPARSE_RMQ}}"}
:::

:::exercise{id="{{EX_DS_ORDERSTAT}}"}
:::
