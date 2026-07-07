# 3. Récurrences & Master Theorem

## 3.1 - Pourquoi les récurrences ?

La complexité d'un algo récursif s'écrit naturellement comme une
**relation de récurrence** :

- *Diviser pour régner* : $T(n) = a\,T(n/b) + f(n)$ - $a$ sous-problèmes
  de taille $n/b$, plus un coût de division/recombinaison $f(n)$.
- *Récursion linéaire* : $T(n) = T(n-1) + f(n)$.

Trois techniques pour résoudre :

1. **Substitution** - deviner, prouver par récurrence.
2. **Arbre de récurrence** - sommer le coût niveau par niveau.
3. **Master Theorem** - formule fermée pour les récurrences "diviser pour régner".

---

## 3.2 - Méthode de substitution

On *devine* la forme de la solution puis on la **prouve par
récurrence** sur $n$.

**Exemple.** Soit $T(n) = 2T(n/2) + n$ avec $T(1) = 1$. On devine
$T(n) = O(n \log n)$, c'est-à-dire $T(n) \le c\,n \log_2 n$ pour un $c$
bien choisi et $n$ assez grand.

*Hérédité.* Supposons $T(n/2) \le c \cdot (n/2) \log_2(n/2)$. Alors

$$
\begin{aligned}
T(n) &= 2T(n/2) + n \\
&\le 2 \cdot c (n/2) \log_2(n/2) + n \\
&= c\,n \log_2 n - c\,n + n \\
&\le c\,n \log_2 n
\end{aligned}
$$

dès que $c \ge 1$. *Initialisation* : on choisit $c$ assez grand pour
couvrir le cas de base. $\square$

> **Mode d'emploi.** Toujours faire apparaître **exactement** la forme
> visée. Si on s'arrête à $\le c\,n \log_2 n + n$, on n'a rien prouvé -
> il faut absorber le $+n$ dans la constante.

---

## 3.3 - Arbre de récurrence

Pour $T(n) = aT(n/b) + f(n)$ on dessine l'arbre des appels :

- Racine : coût $f(n)$.
- Niveau $k$ : $a^k$ nœuds, chacun de taille $n/b^k$, coût total $a^k \, f(n/b^k)$.
- Profondeur : $\log_b n$ niveaux jusqu'à atteindre des feuilles de
  taille $1$, qui contribuent $a^{\log_b n} = n^{\log_b a}$ au coût
  total.

Coût total :

$$
T(n) = \underbrace{n^{\log_b a}}_{\text{coût des feuilles}} + \sum_{k=0}^{\log_b n - 1} a^k\, f(n/b^k).
$$

Selon que la somme est dominée par les feuilles, par la racine, ou par
tous les niveaux à parts égales, on obtient les **trois cas** du Master
Theorem.

---

## 3.4 - Master Theorem (énoncé)

**Théorème.** Soit $T(n) = a\,T(n/b) + f(n)$ avec $a \ge 1$, $b > 1$, et
$f(n)$ asymptotiquement positive. Posons $\alpha = \log_b a$. Alors :

| Cas | Hypothèse sur $f$ | Conclusion |
|-----|-------------------|------------|
| **1** | $f(n) = O(n^{\alpha - \varepsilon})$ pour un $\varepsilon > 0$ | $T(n) = \Theta(n^\alpha)$ |
| **2** | $f(n) = \Theta(n^\alpha)$ | $T(n) = \Theta(n^\alpha \log n)$ |
| **3** | $f(n) = \Omega(n^{\alpha + \varepsilon})$ pour un $\varepsilon > 0$, et la condition de **régularité** $a\,f(n/b) \le c\,f(n)$ tient pour un $c < 1$ et $n$ grand | $T(n) = \Theta(f(n))$ |

### Esquisse de preuve

On utilise l'arbre de récurrence avec total
$T(n) = n^\alpha + \sum_{k=0}^{\log_b n - 1} a^k f(n/b^k)$.

- **Cas 1.** $f(n/b^k) \le C (n/b^k)^{\alpha - \varepsilon}$, donc
  $a^k f(n/b^k) \le C\,n^{\alpha-\varepsilon} (a/b^{\alpha - \varepsilon})^k = C\,n^{\alpha-\varepsilon} b^{\varepsilon k}$.
  La somme est une géométrique de raison $b^\varepsilon > 1$ : elle est dominée par son **dernier** terme,
  qui vaut $C\,n^{\alpha - \varepsilon} \cdot b^{\varepsilon \log_b n} = C\,n^\alpha$.
  Le coût des feuilles ($n^\alpha$) absorbe tout : $T(n) = \Theta(n^\alpha)$.
- **Cas 2.** $f(n/b^k) = \Theta((n/b^k)^\alpha)$, donc
  $a^k f(n/b^k) = \Theta(n^\alpha)$ pour tout niveau. La somme sur les
  $\log_b n$ niveaux donne $\Theta(n^\alpha \log n)$.
- **Cas 3.** La régularité $a f(n/b) \le c f(n)$ avec $c < 1$ implique
  que les niveaux **diminuent géométriquement**, et la somme est
  dominée par le **premier** terme $f(n)$ : $T(n) = \Theta(f(n))$.

$\square$

### Exemples canoniques

| Récurrence | $a$, $b$, $f$ | $\alpha = \log_b a$ | Cas | $T(n)$ |
|-----------|---------------|---------------------|-----|--------|
| $T(n) = 2T(n/2) + n$ (merge sort) | $2,2,n$ | $1$ | 2 | $\Theta(n \log n)$ |
| $T(n) = 2T(n/2) + n^2$ | $2,2,n^2$ | $1$ | 3 | $\Theta(n^2)$ |
| $T(n) = 4T(n/2) + n$ | $4,2,n$ | $2$ | 1 | $\Theta(n^2)$ |
| $T(n) = 8T(n/2) + n^2$ | $8,2,n^2$ | $3$ | 1 | $\Theta(n^3)$ |
| $T(n) = 7T(n/2) + n^2$ (Strassen) | $7,2,n^2$ | $\log_2 7 \approx 2{,}81$ | 1 | $\Theta(n^{\log_2 7})$ |

> **Limite.** Le Master Theorem **ne s'applique pas** quand $f$ se
> situe entre deux puissances ($f(n) = n \log n$ avec $\alpha = 1$ par
> ex.). On bascule alors sur l'arbre de récurrence ou Akra-Bazzi.

---

## 3.5 - Bonus : Akra-Bazzi

**Théorème (Akra-Bazzi).** Soit
$T(n) = \sum_{i=1}^{k} a_i\,T(n/b_i) + f(n)$
avec $a_i > 0$, $b_i > 1$. Soit $p$ l'unique réel vérifiant
$\sum_{i=1}^{k} a_i / b_i^{\,p} = 1$. Alors

$$
T(n) = \Theta\!\left( n^p \left(1 + \int_1^n \frac{f(u)}{u^{p+1}}\,du \right)\right).
$$

Akra-Bazzi gère :
- des récurrences à **plusieurs branches de tailles différentes** (ex. $T(n) = T(n/3) + T(2n/3) + n$),
- des $f(n)$ comme $n \log n$ que le Master Theorem rejette.

**Exemple.** $T(n) = T(n/3) + T(2n/3) + n$. On résout
$1/3^p + (2/3)^p = 1$ ; la solution est $p = 1$. L'intégrale donne
$\int_1^n du/u = \ln n$, donc $T(n) = \Theta(n \log n)$. C'est la
complexité du quicksort *équilibré* - exactement comme merge sort.

---

## 3.6 - Exercices

:::exercise{id="{{EX_REC_STD}}"}
:::

:::exercise{id="{{EX_REC_TWIST}}"}
:::

:::exercise{id="{{EX_REC_HARD}}"}
:::
