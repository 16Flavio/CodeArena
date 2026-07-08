# 3. Combinatoire modulaire

## 3.1 - Intuition

Compter, c'est le cœur de l'algorithmique combinatoire : combien de
sous-ensembles, de chemins, d'arrangements ? La reponse passe presque
toujours par le **coefficient binomial** $\binom{n}{k}$, le nombre de
facons de choisir $k$ objets parmi $n$. Comme ces nombres explosent,
on les calcule **modulo** un premier $p$.

La methode change selon l'echelle : factorielles pre-calculees pour
$n$ raisonnable, **theoreme de Lucas** quand $n$ depasse $p$, formules
fermees pour les familles remarquables comme les nombres de Catalan.

---

## 3.2 - Algorithmes

### Binomial par factorielles (cas $p > n$)

$$
\binom{n}{k} = \frac{n!}{k!\,(n-k)!} \bmod p.
$$

```python
def binom(n, k, p):                 # p premier, p > n
    if k < 0 or k > n: return 0
    num = den = 1
    for i in range(k):
        num = num * (n - i) % p
        den = den * (i + 1) % p
    return num * pow(den, p - 2, p) % p    # inverse par Fermat
```

Precalculer factorielles et inverses rend chaque requete $O(1)$.

**Construis le triangle de Pascal** : chaque case interne est la somme
de ses deux parents, $C(n,k) = C(n-1,k-1) + C(n-1,k)$.

:::viz-pascal{n="8"}
:::

### Theoreme de Lucas (cas $n \ge p$)

Ecrire $n$ et $k$ en base $p$ : $n = \sum n_i p^i$, $k = \sum k_i
p^i$. Alors

$$
\binom{n}{k} \equiv \prod_i \binom{n_i}{k_i} \pmod p.
$$

Chaque chiffre $n_i, k_i$ est $< p$, donc chaque petit binomial se
calcule directement. Si un $k_i > n_i$, le produit est nul.

### Nombres de Catalan

$$
C_n = \frac{1}{n+1} \binom{2n}{n}.
$$

Ils comptent les arbres binaires a $n$ noeuds, les parenthesages
valides, les chemins de Dyck, les triangulations d'un polygone...

---

## 3.3 - Complexite

$$
\begin{aligned}
\text{binomial (factorielles pre-calculees)} &: \Theta(1)\ \text{par requete}, \\
\text{Lucas} &: \Theta(\log_p n \cdot p), \\
\text{Catalan} &: \Theta(n)\ \text{(via factorielles)}.
\end{aligned}
$$

Lucas ramene un calcul sur $n \sim 10^{18}$ a une poignee de petits
binomiaux - le seul moyen quand $p$ est petit.

---

## 3.4 - Pieges classiques

1. **Diviser modulo p.** On ne divise jamais directement ; on
   multiplie par l'inverse modulaire. Oublier l'inverse donne un
   resultat faux.
2. **$p \le n$ sans Lucas.** Si $p \le n$, un facteur $p$ apparait dans
   $n!$ et l'inverse du denominateur n'existe plus : il **faut** Lucas.
3. **Catalan et $p$ petit.** $\frac{1}{n+1}$ n'a d'inverse que si $p
   \nmid (n+1)$ ; garantir $p > 2n$ ou passer par la recurrence.
4. **Bornes de $k$.** Traiter explicitement $k < 0$ et $k > n$ (valeur
   $0$), sinon les boucles se comportent mal.

---

## 3.5 - Compter, encore et toujours

Arrangements, combinaisons avec repetition (**stars and bars**),
inclusion-exclusion, nombres de Stirling et de Bell, denombrement de
Burnside sous symetrie : toute la combinatoire enumerative s'appuie sur
un binomial modulaire fiable. Bien choisir sa methode selon la taille
de $n$ face a $p$ est le reflexe central.

---

## 3.6 - Exercices

:::exercise{id="{{EX_MA_BINOM}}"}
:::

:::exercise{id="{{EX_MA_LUCAS}}"}
:::

:::exercise{id="{{EX_MA_CATALAN}}"}
:::
