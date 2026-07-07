# 4. Convolutions (FFT / NTT)

## 4.1 - Intuition

Multiplier deux polynomes, ou plus generalement calculer une
**convolution**

$$
(A * B)[s] = \sum_{i + j = s} A_i \, B_j,
$$

coute naivement $O(nm)$. Or cette operation est partout : produit de
polynomes, distribution d'une somme de variables, comptage de paires
par valeur. La **transformee de Fourier rapide** (FFT) la ramene a
$O(n \log n)$.

L'astuce : un polynome peut etre represente soit par ses
**coefficients**, soit par ses **valeurs** en des points bien choisis.
Dans la representation par valeurs, multiplier deux polynomes est un
simple produit point a point. La FFT convertit entre les deux
representations en $O(n \log n)$.

---

## 4.2 - Algorithme

### Le schema general

$$
A * B = \text{FFT}^{-1}\bigl(\text{FFT}(A) \odot \text{FFT}(B)\bigr),
$$

ou $\odot$ est le produit point a point. La FFT evalue en les
**racines de l'unite** $\omega^k$ par diviser-pour-regner : separer
les indices pairs et impairs, resoudre chaque moitie, recombiner.

### NTT : la FFT exacte

La FFT flottante souffre d'erreurs d'arrondi. La **NTT** (*Number
Theoretic Transform*) fait la meme chose modulo un premier bien
choisi, avec une **racine primitive** au lieu de $\omega$. Le premier
$998244353 = 119 \cdot 2^{23} + 1$ est ideal : il admet des racines de
l'unite d'ordre $2^{23}$, ce qui couvre des tailles jusqu'a $2^{23}$
en restant **exact** sur les entiers.

---

## 4.3 - Complexite

$$
\begin{aligned}
\text{convolution naive} &: \Theta(nm), \\
\text{FFT / NTT} &: \Theta\bigl((n+m) \log(n+m)\bigr).
\end{aligned}
$$

Le gain est spectaculaire des que $n$ depasse quelques milliers :
passer de $10^{10}$ a $\sim 10^6$ operations.

---

## 4.4 - Pieges classiques

1. **Taille non puissance de 2.** La FFT recursive exige une longueur
   $2^k$ ; completer par des zeros jusqu'a la prochaine puissance de 2
   $\ge n + m - 1$.
2. **Erreurs d'arrondi (FFT flottante).** Pour des coefficients
   entiers, preferer la NTT (exacte) ou arrondir soigneusement le
   resultat.
3. **Modulo incompatible.** La NTT n'est exacte que si le premier admet
   une racine de l'unite de l'ordre voulu ; $998244353$ est le choix
   canonique.
4. **Depassement de la taille.** Le resultat a $n + m - 1$
   coefficients ; dimensionner les tableaux en consequence.

---

## 4.5 - Bien plus que des polynomes

Somme de variables aleatoires, exponentiation de polynomes (somme de
$n$ des), correspondance de chaines avec jokers, multiplication de
grands entiers, comptage de sous-ensembles par somme : d'innombrables
problemes se **reduisent** a une convolution. Reconnaitre la
convolution cachee dans un enonce, puis la resoudre par NTT, est la
competence phare de cette lecon.

---

## 4.6 - Exercices

:::exercise{id="{{EX_MA_POLYMUL}}"}
:::

:::exercise{id="{{EX_MA_PAIR_SUMS}}"}
:::

:::exercise{id="{{EX_MA_DICE}}"}
:::
