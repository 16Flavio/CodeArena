# 4. Suffix array & LCP

## 4.1 - Intuition

Beaucoup de questions sur une chaine - sous-chaines distinctes,
repetitions, recherche - se ramenent a **tous les suffixes**. Les
lister explicitement coute $O(n^2)$ en memoire. Le **suffix array**
les represente par leurs seuls indices de depart, **tries** par ordre
lexicographique, en $O(n)$ memoire.

Une fois les suffixes tries, deux suffixes qui se ressemblent sont
**voisins** dans le tableau. Le tableau **LCP** (*Longest Common
Prefix*) mesure, entre suffixes adjacents, la longueur du prefixe
commun - la cle de presque toutes les applications.

---

## 4.2 - Algorithme

### Construction par doublement

On trie les suffixes par leurs $2^k$ premiers caracteres, en
reutilisant les rangs de l'etape precedente : le rang selon $2^k$
caracteres est le couple (rang selon $2^{k-1}$ de la moitie gauche,
rang de la moitie droite).

```python
def suffix_array(s):
    n = len(s)
    sa = list(range(n))
    rank = [ord(c) for c in s]
    k = 1
    while True:
        sa.sort(key=lambda i: (rank[i], rank[i + k] if i + k < n else -1))
        tmp = [0] * n
        for i in range(1, n):
            prev, cur = sa[i-1], sa[i]
            same = (rank[prev], rank[prev+k] if prev+k < n else -1) == \
                   (rank[cur],  rank[cur+k]  if cur+k  < n else -1)
            tmp[cur] = tmp[prev] + (0 if same else 1)
        rank = tmp
        if rank[sa[-1]] == n - 1:
            break
        k *= 2
    return sa
```

### LCP par l'algorithme de Kasai

En parcourant les suffixes dans l'ordre du texte (et non du tableau),
la longueur du prefixe commun ne diminue que de 1 a chaque pas, ce qui
donne le tableau LCP en $O(n)$.

---

## 4.3 - Complexite

$$
\begin{aligned}
\text{suffix array (doublement)} &: \Theta(n \log^2 n), \\
\text{variante par comptage} &: \Theta(n \log n), \\
\text{LCP (Kasai)} &: \Theta(n).
\end{aligned}
$$

Des constructions lineaires existent (DC3, SA-IS) mais sont plus
delicates ; le doublement suffit dans l'immense majorite des cas.

---

## 4.4 - Pieges classiques

1. **Suffixes de longueurs differentes.** Un suffixe plus court qui
   est prefixe d'un autre se classe **avant** ; d'ou le rang $-1$ pour
   la moitie manquante.
2. **LCP mal indexe.** Convention courante : `lcp[i]` = prefixe commun
   de `sa[i-1]` et `sa[i]`, avec `lcp[0] = 0`.
3. **Kasai part des rangs.** L'algorithme parcourt les positions du
   **texte**, en s'appuyant sur le rang inverse ; inverser les deux
   casse la borne lineaire.
4. **Sous-chaines distinctes.** La formule $\frac{n(n+1)}{2} - \sum
   \text{LCP}$ compte le total moins les prefixes deja vus - verifier
   l'indexation de la somme.

---

## 4.5 - La structure ultime des chaines

Suffix array + LCP resolvent : nombre de sous-chaines distinctes, plus
longue sous-chaine repetee, plus longue sous-chaine commune a
plusieurs textes, recherche de motif en $O(|P| \log n)$. La ou le trie
des suffixes exploserait en memoire, le suffix array tient dans un
tableau d'entiers - la structure de reference pour l'algorithmique du
texte a grande echelle.

---

## 4.6 - Exercices

:::exercise{id="{{EX_TX_SUFFIX_ARRAY}}"}
:::

:::exercise{id="{{EX_TX_DISTINCT_SUBSTR_TOTAL}}"}
:::

:::exercise{id="{{EX_TX_LRS}}"}
:::
