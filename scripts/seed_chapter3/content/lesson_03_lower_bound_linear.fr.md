# 3. Borne inférieure $\Omega(n \log n)$ & tris linéaires

## 3.1 — Pourquoi cherche-t-on une borne inférieure ?

Les tris en $\Theta(n \log n)$ s'enchaînent : mergesort, heapsort,
quicksort en moyenne. Question naturelle : **peut-on faire mieux ?**

Réponse : **non, pas avec des comparaisons seules**. Tout algorithme
qui ne consulte que des comparaisons $a_i < a_j$ a un coût
$\Omega(n \log n)$ dans le pire cas. La preuve passe par les
**arbres de décision**.

---

## 3.2 — L'arbre de décision

Tout algorithme déterministe qui trie en utilisant uniquement des
comparaisons peut être représenté comme un **arbre de décision
binaire** :

- chaque nœud interne porte une comparaison `A[i] < A[j]` ;
- les deux fils correspondent aux deux issues `vrai` / `faux` ;
- chaque feuille porte une **permutation** $\sigma$ de l'entrée :
  c'est la sortie produite quand on emprunte ce chemin.

**Observation clé.** Pour que l'algorithme soit correct, chacune
des $n!$ permutations possibles d'une entrée distincte doit être
atteignable comme feuille. Donc l'arbre a **au moins $n!$ feuilles**.

### Théorème

**Théorème.** Tout arbre de décision triant $n$ éléments distincts
a une hauteur $h \ge \log_2(n!)$.

*Preuve.* Un arbre binaire de hauteur $h$ a au plus $2^h$ feuilles.
Comme on a au moins $n!$ feuilles : $2^h \ge n!$, soit $h \ge
\log_2(n!)$. $\square$

### Conclusion : $\Omega(n \log n)$

On veut une borne explicite sur $\log_2(n!)$. Approximation de
Stirling :

$$n! \ge \left(\frac{n}{e}\right)^n,$$

donc

$$\log_2(n!) \ge n \log_2(n/e) = n \log_2 n - n \log_2 e = \Omega(n \log n).$$

→ **Tout algorithme de tri par comparaison effectue $\Omega(n \log n)$
comparaisons dans le pire cas.** Mergesort et heapsort sont
**asymptotiquement optimaux** dans ce modèle. $\square$

> **Conséquence directe.** Pour aller en deçà, il faut **sortir du
> modèle des comparaisons** — tirer parti d'une structure connue des
> clés. C'est ce que font les tris linéaires.

---

## 3.3 — Tri par comptage (counting sort)

### Hypothèse

Les clés sont des **entiers** dans $[0, k]$, avec $k$ pas trop
grand devant $n$.

### Algorithme

```python
def counting_sort(A, k):
    cnt = [0] * (k + 1)
    for x in A: cnt[x] += 1
    out = []
    for v in range(k + 1):
        out.extend([v] * cnt[v])
    return out
```

### Complexité

$\Theta(n + k)$ — linéaire si $k = O(n)$.

### Stabilité (version générale)

La version ci-dessus perd la stabilité si on associe des valeurs
aux clés (genre `(clé, payload)`). La version **stable** utilise
des sommes préfixes :

```python
def counting_sort_stable(A, k):
    cnt = [0] * (k + 1)
    for x in A: cnt[x] += 1
    for i in range(1, k + 1): cnt[i] += cnt[i - 1]
    out = [None] * len(A)
    for x in reversed(A):
        cnt[x] -= 1
        out[cnt[x]] = x
    return out
```

L'itération **inversée** combinée à `cnt` décrémenté garantit que
deux éléments de même clé restent dans leur ordre d'origine.

---

## 3.4 — Tri par base (radix sort, LSD)

### Hypothèse

Les clés sont des **entiers à $d$ chiffres** (ou des chaînes de
longueur fixe $d$). On choisit une base $b$ (typiquement $b = 10$
ou $b = 256$).

### Algorithme : LSD

On trie par chiffre, **du moins significatif au plus significatif**,
en utilisant un counting sort **stable** à chaque étape :

```python
def radix_sort(A):
    if not A: return []
    mx = max(A); exp = 1
    while mx // exp > 0:
        # counting sort sur le chiffre (x // exp) % 10
        cnt = [0] * 10
        for x in A: cnt[(x // exp) % 10] += 1
        for i in range(1, 10): cnt[i] += cnt[i - 1]
        out = [0] * len(A)
        for x in reversed(A):
            d = (x // exp) % 10
            cnt[d] -= 1
            out[cnt[d]] = x
        A = out
        exp *= 10
    return A
```

### Correction (pourquoi LSD marche)

**Invariant.** Après le passage sur le chiffre $i$ (du moins au
plus significatif), $A$ est trié par les **$i$ derniers chiffres**.

*Hérédité.* Le passage sur le chiffre $i+1$ utilise un counting sort
**stable** : deux clés ayant le même chiffre $i+1$ conservent leur
ordre relatif établi à l'étape précédente — donc l'ordre global
sur les $i+1$ derniers chiffres. $\square$

### Complexité

$\Theta(d \cdot (n + b))$ — linéaire en $n$ quand $d$ et $b$ sont
constantes (entiers à 32 bits par octets : $d = 4$, $b = 256$).

---

## 3.5 — Tri par paquets (bucket sort)

### Hypothèse

Les clés sont des **réels uniformément distribués** dans $[0, 1]$.

### Algorithme

1. Créer $n$ paquets correspondant aux intervalles $[i/n, (i+1)/n)$.
2. Mettre chaque clé dans son paquet (en $\Theta(n)$ au total).
3. Trier chaque paquet (insertion sort suffit).
4. Concaténer les paquets.

### Complexité en espérance

Sous l'hypothèse uniforme, le nombre attendu d'éléments par paquet
est $1$. Insertion sort dans un paquet de taille $m$ coûte
$\Theta(m^2)$. La somme des $\mathbb{E}[m^2]$ sur les $n$ paquets
donne $\Theta(n)$ — calcul classique mais hors champ ici.

→ **$\Theta(n)$ en espérance** quand l'hypothèse uniforme tient.
Pire cas : $\Theta(n^2)$ si tous les éléments tombent dans le même
paquet.

---

## 3.6 — Tableau récapitulatif

| Algo | Hypothèse | Pire cas | Stable |
|------|-----------|----------|--------|
| Comparaison (general) | aucune | $\Omega(n \log n)$ par bornes | dépend |
| Counting sort | clés $\in [0, k]$, $k = O(n)$ | $\Theta(n + k)$ | oui (version stable) |
| Radix sort | clés $d$-chiffres en base $b$ | $\Theta(d(n + b))$ | oui |
| Bucket sort | clés u.d. dans $[0,1]$ | $\Theta(n)$ espérance | oui |

---

## 3.7 — Exercices

:::exercise{id="{{EX_SO_COUNTING}}"}
:::

:::exercise{id="{{EX_SO_RADIX}}"}
:::

:::exercise{id="{{EX_SO_RADIX_STR}}"}
:::
