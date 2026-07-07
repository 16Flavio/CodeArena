# 2. Arbres de segments

## 2.1 - Intuition

On veut interroger et modifier un tableau de facon repetee : « somme
de la plage $[l, r]$ », « poser $a_i = x$ », des milliers de fois. Un
tableau brut fait la mise a jour en $O(1)$ mais la requete en $O(n)$ ;
les sommes prefixes font l'inverse. L'**arbre de segments** equilibre
les deux : **chaque** operation en $O(\log n)$.

L'idee : un arbre binaire ou chaque noeud resume un intervalle. La
racine couvre tout le tableau, ses enfants chacune une moitie, et
ainsi de suite jusqu'aux feuilles (elements individuels). Toute plage
se decoupe en $O(\log n)$ noeuds.

---

## 2.2 - Algorithme

```python
# Arbre de segments iteratif, somme, mise a jour ponctuelle.
def build(a):
    n = len(a); size = 1
    while size < n: size *= 2
    tree = [0] * (2 * size)
    for i in range(n): tree[size + i] = a[i]
    for i in range(size - 1, 0, -1):
        tree[i] = tree[2*i] + tree[2*i+1]
    return tree, size

def update(tree, size, i, val):
    i += size; tree[i] = val; i //= 2
    while i:
        tree[i] = tree[2*i] + tree[2*i+1]; i //= 2

def query(tree, size, l, r):          # somme sur [l, r]
    res = 0; l += size; r += size + 1
    while l < r:
        if l & 1: res += tree[l]; l += 1
        if r & 1: r -= 1; res += tree[r]
        l //= 2; r //= 2
    return res
```

### Ce qui rend l'arbre general

L'operation de fusion (`+` ici) peut etre **n'importe quelle**
operation **associative** ayant un element neutre : minimum, maximum,
pgcd, XOR... Changer `+` en `min` transforme un arbre de sommes en
arbre de minimums, sans toucher a la structure. C'est la force du
modele.

### Propagation paresseuse

Pour des mises a jour de **plage** (« ajouter $x$ a tout $[l, r]$ »),
on marque le noeud couvrant la plage d'un `lazy` differe, et on ne le
repercute aux enfants qu'au moment de les visiter. Cela garde les
mises a jour de plage en $O(\log n)$.

---

## 2.3 - Complexite

$$
\begin{aligned}
\text{construction} &: \Theta(n), \\
\text{mise a jour / requete} &: \Theta(\log n), \\
\text{avec lazy (plage)} &: \Theta(\log n)\ \text{par operation}.
\end{aligned}
$$

Memoire $\Theta(n)$. Une requete visite au plus deux chemins
racine-feuille, d'ou le $\log n$.

---

## 2.4 - Pieges classiques

1. **Fusion non associative.** L'arbre exige l'associativite ; « le
   deuxieme plus grand » ou « le mode » ne se fusionnent pas
   naivement.
2. **Oublier de pousser le lazy.** Avant de descendre dans les
   enfants (requete ou mise a jour partielle), propager la marque
   differee, sinon les valeurs sont fausses.
3. **Indices inclusifs/exclusifs.** Fixer une convention et s'y tenir ;
   un decalage de 1 corrompt toutes les plages.
4. **Element neutre.** La requete doit partir du neutre correct : $0$
   pour la somme, $+\infty$ pour le min.

---

## 2.5 - Un couteau suisse

Arbre de segments : sommes, min/max, comptages, affectations de plage,
recherche du $k$-ieme, arbre persistant, arbre de segments sur les
valeurs... Peu de structures couvrent autant de requetes de plage. En
maitriser le squelette (couvrir une plage par $O(\log n)$ noeuds) ouvre
toute la famille.

---

## 2.6 - Exercices

:::exercise{id="{{EX_DS_SEG_SUM}}"}
:::

:::exercise{id="{{EX_DS_SEG_RMQ}}"}
:::

:::exercise{id="{{EX_DS_SEG_LAZY}}"}
:::
