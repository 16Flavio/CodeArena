# 4. Analyse amortie & tableau dynamique

## 4.1 - L'idée : moyenner les coûts

Certaines opérations sont *occasionnellement* coûteuses mais
*globalement* bon marché. Les analyser au pire cas surestime
massivement leur coût réel.

**Exemple introductif.** On veut insérer $n$ entiers dans un tableau
dynamique (style `list` Python ou `std::vector` C++). De temps en
temps, le tableau **double** sa capacité - c'est une opération en
$O(\text{capacité})$. Au pire cas, une insertion coûte $O(n)$. Mais sur
$n$ insertions consécutives, le coût total reste $O(n)$ : le coût
**amorti** par insertion est $O(1)$.

L'analyse amortie formalise ce raisonnement avec **trois méthodes
équivalentes** : agrégat, banquier, potentiel.

---

## 4.2 - Méthode de l'agrégat

On calcule le coût total de $n$ opérations, puis on divise par $n$.

**Tableau dynamique.** Capacité initiale $1$. À l'insertion $k$, si le
tableau est plein, on alloue $2k$, on copie $k$ éléments, on insère.

- Le doublement a lieu lorsque $k$ est une puissance de $2$ : $k = 1, 2, 4, 8, \dots$
- Coût d'une insertion sans doublement : $1$ (l'écriture).
- Coût d'une insertion avec doublement à $k = 2^j$ : $2^j$ (copies) $+ 1$.

Coût total des $n$ insertions :

$$\text{Total} = n + \sum_{j=0}^{\lfloor \log_2 n \rfloor} 2^j \le n + 2n = 3n.$$

Coût amorti : $3n / n = O(1)$. $\square$

---

## 4.3 - Méthode du banquier (accounting)

On *facture* à chaque opération un coût artificiel (le **coût amorti**)
qui peut être supérieur à son vrai coût. La différence est stockée
comme **crédit** sur certaines structures.

**Règle de cohérence.** À tout moment, $\sum \text{coût amorti} \ge \sum \text{coût réel}$.

**Tableau dynamique.** On facture $3$ par insertion :
- $1$ pour l'écriture elle-même,
- $1$ comme crédit posé sur le nouvel élément,
- $1$ comme crédit posé sur un élément ancien (pour payer sa future copie).

Quand un doublement survient (passage de $k$ à $2k$), on doit copier
les $k$ éléments existants. Mais chacun a accumulé $\ge 1$ crédit
depuis la dernière réorganisation : ces crédits paient les copies. Le
coût amorti reste $3 = O(1)$ par insertion. $\square$

---

## 4.4 - Méthode du potentiel

On définit une fonction $\Phi$ de l'état de la structure vers
$\mathbb{R}_{\ge 0}$ avec $\Phi(\text{état initial}) = 0$. Le coût
amorti d'une opération est :

$$\hat c_i = c_i + \Phi(D_i) - \Phi(D_{i-1}).$$

Pour $n$ opérations :

$$\sum \hat c_i = \sum c_i + \Phi(D_n) - \Phi(D_0) \ge \sum c_i.$$

Donc $\sum c_i \le \sum \hat c_i$ : majorer le coût amorti suffit.

**Tableau dynamique.** Posons $\Phi = 2 \cdot \text{taille} - \text{capacité}$
(toujours $\ge 0$ après une insertion qui ne déclenche pas de
réallocation, et $= 0$ juste après un doublement).

- Insertion sans doublement : taille passe de $s$ à $s+1$, capacité
  inchangée. $\Delta\Phi = 2$. Coût amorti $= 1 + 2 = 3$.
- Insertion avec doublement à $s = c$ : copie $c$, capacité $\to 2c$,
  taille $\to c+1$. $\Phi$ passe de $2c - c = c$ à $2(c+1) - 2c = 2$.
  $\Delta\Phi = 2 - c$. Coût réel $= c + 1$. Coût amorti $= c + 1 + 2 - c = 3$.

Coût amorti **constant**, $O(1)$ par insertion. $\square$

> **Remarque.** Les trois méthodes donnent le même résultat. Choisir
> celle qui est la plus naturelle au problème : agrégat pour des
> séquences uniformes, banquier pour des structures avec « crédits
> physiques », potentiel pour des invariants algébriques.

---

## 4.5 - Algorithme et preuve de correction

```python
class DynamicArray:
    def __init__(self):
        self.cap = 1
        self.size = 0
        self.buf = [None] * self.cap

    def append(self, x):
        if self.size == self.cap:
            new_cap = 2 * self.cap
            new_buf = [None] * new_cap
            for i in range(self.size):       # O(cap) copies
                new_buf[i] = self.buf[i]
            self.buf = new_buf
            self.cap = new_cap
        self.buf[self.size] = x
        self.size += 1
```

**Correction (esquisse).** Invariant : après chaque `append`, on a
`0 ≤ size ≤ cap`, `cap` est une puissance de $2$, et les $size$
premières positions de `buf` contiennent les éléments insérés dans
l'ordre. L'invariant est trivialement vrai initialement. À chaque
insertion : si on double, le nouvel `buf` contient encore les éléments
en ordre (la boucle de copie préserve les indices). On écrit ensuite
`buf[size]` puis on incrémente `size`. $\square$

**Complexité.** $\Theta(1)$ amorti par `append`, $\Theta(n)$ pour $n$
insertions consécutives.

---

## 4.6 - Exercices

:::exercise{id="{{EX_AMO_STD}}"}
:::

:::exercise{id="{{EX_AMO_TWIST}}"}
:::

:::exercise{id="{{EX_AMO_HARD}}"}
:::
