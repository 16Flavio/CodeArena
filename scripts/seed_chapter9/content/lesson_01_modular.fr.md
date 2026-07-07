# 1. Arithmetique modulaire

## 1.1 - Intuition

En competition, les reponses depassent souvent la capacite des
entiers : le nombre de chemins, de configurations, de facons... On
travaille alors **modulo** un grand nombre $m$ (souvent premier),
c'est-a-dire sur les restes de division par $m$. L'arithmetique
modulaire garde tous les calculs bornes tout en preservant additions,
soustractions et multiplications.

La division, elle, demande un detour : diviser par $a$ revient a
multiplier par son **inverse** $a^{-1}$, l'unique nombre tel que
$a \cdot a^{-1} \equiv 1 \pmod m$. Deux outils dominent la lecon :
l'exponentiation rapide et le calcul d'inverse.

---

## 1.2 - Algorithmes

### Exponentiation rapide

```python
def modexp(a, b, m):
    result = 1
    a %= m
    while b > 0:
        if b & 1:
            result = result * a % m
        a = a * a % m
        b >>= 1
    return result
```

On decompose $b$ en binaire : chaque bit double l'exposant. D'ou
$O(\log b)$ multiplications.

### Inverse modulaire

Deux methodes :

- **Fermat** (si $m$ premier) : $a^{-1} \equiv a^{m-2} \pmod m$, par
  le petit theoreme de Fermat $a^{m-1} \equiv 1$.
- **Euclide etendu** (cas general) : il calcule $x, y$ tels que

$$
a x + m y = \gcd(a, m).
$$

Si $\gcd(a, m) = 1$, alors $x \bmod m$ est l'inverse. L'inverse
**n'existe que si** $\gcd(a, m) = 1$.

---

## 1.3 - Complexite

$$
\begin{aligned}
\text{exponentiation rapide} &: \Theta(\log b), \\
\text{Euclide etendu} &: \Theta(\log \min(a, m)), \\
\text{congruence lineaire} &: \Theta(\log m).
\end{aligned}
$$

Toutes ces operations sont **logarithmiques** : elles restent
instantanees meme pour des modulos de $10^{18}$.

---

## 1.4 - Pieges classiques

1. **Debordement.** En C++/Java, $a \cdot a$ pour $a \sim 10^9$
   deborde un `long long` ; utiliser `__int128` ou un modulo tenant
   sur 32 bits. En Python, aucun souci.
2. **Fermat hors contexte.** $a^{m-2}$ n'est un inverse que si $m$ est
   **premier**. Pour un $m$ composite, passer par Euclide etendu.
3. **Inverse inexistant.** Si $\gcd(a, m) \ne 1$, l'inverse n'existe
   pas - le signaler plutot que de renvoyer une valeur fausse.
4. **Restes negatifs.** Apres une soustraction, ramener dans
   $[0, m)$ par `% m` (en Python, `%` renvoie deja un reste positif).

---

## 1.5 - Une brique fondamentale

Exponentiation et inverse sont les fondations de presque tout le
chapitre : coefficients binomiaux modulaires (leçon 3), NTT
(leçon 4), tests de primalite (leçon 2). Les congruences lineaires et
le theoreme des restes chinois en decoulent directement. Maitriser ces
deux gestes, c'est tenir la moitie de la boite a outils.

---

## 1.6 - Exercices

:::exercise{id="{{EX_MA_MODEXP}}"}
:::

:::exercise{id="{{EX_MA_MODINV}}"}
:::

:::exercise{id="{{EX_MA_LINCONG}}"}
:::
