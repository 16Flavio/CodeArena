# 2. Cribles, primalite & CRT

## 2.1 - Intuition

Trois questions reviennent partout en theorie des nombres :
enumerer les premiers jusqu'a $n$, tester si **un** grand nombre est
premier, et recoller des informations modulaires. Trois outils y
repondent, chacun avec sa plage d'usage.

- Le **crible d'Eratosthene** liste tous les premiers $\le n$.
- **Miller-Rabin** teste un seul $n$ gigantesque.
- Le **theoreme des restes chinois** (CRT) fusionne des congruences.

---

## 2.2 - Algorithmes

### Crible d'Eratosthene

```python
def sieve(n):
    is_comp = bytearray(n + 1)
    primes = []
    for i in range(2, n + 1):
        if not is_comp[i]:
            primes.append(i)
            for j in range(i * i, n + 1, i):   # marquer a partir de i^2
                is_comp[j] = 1
    return primes
```

### Miller-Rabin

Ecrire $n - 1 = 2^r d$ avec $d$ impair. Pour un temoin $a$, si
$a^d \not\equiv 1$ et $a^{2^i d} \not\equiv -1$ pour tout $i < r$,
alors $n$ est **compose** (temoin de non-primalite). Avec les temoins
$\{2, 3, 5, \dots, 37\}$, le test est **deterministe** sous
$3{.}3 \cdot 10^{24}$.

### Theoreme des restes chinois

Deux congruences $x \equiv a_1 \pmod{m_1}$ et $x \equiv a_2
\pmod{m_2}$ fusionnent en une seule modulo $\text{lcm}(m_1, m_2)$,

$$
\text{a condition que}\quad \gcd(m_1, m_2) \mid (a_2 - a_1),
$$

sinon le systeme est incompatible. On fusionne les $k$ congruences une
a une.

---

## 2.3 - Complexite

$$
\begin{aligned}
\text{crible} &: \Theta(n \log \log n), \\
\text{Miller-Rabin} &: \Theta(t \log^2 n)\ \text{(} t \text{ temoins)}, \\
\text{CRT (}k\text{ congruences)} &: \Theta(k \log M).
\end{aligned}
$$

Le crible est memoire $\Theta(n)$ ; Miller-Rabin ne stocke rien et
tient jusqu'a $10^{18}$ la ou le crible exploserait.

---

## 2.4 - Pieges classiques

1. **Cribler pour un seul grand nombre.** Inutile et impossible en
   memoire ; pour tester un seul $n$ enorme, c'est Miller-Rabin.
2. **Nombres de Carmichael.** $561 = 3 \cdot 11 \cdot 17$ trompe le
   test de Fermat naif ; Miller-Rabin, lui, les detecte.
3. **CRT et modulos non copremiers.** La version generale exige la
   condition de divisibilite ; l'ignorer donne de fausses solutions.
4. **Debordement dans la fusion CRT.** Le produit $m_1 \cdot t$ peut
   etre enorme ; en langage type, prendre garde au modulo intermediaire.

---

## 2.5 - Le socle de la theorie des nombres

Factorisation (par crible des plus petits facteurs premiers, ou
Pollard rho pour les grands), fonction indicatrice d'Euler, resolution
de systemes modulaires, reconstruction d'un grand resultat a partir de
petits modulos premiers : tout repose sur ces trois briques. Choisir
la bonne selon que l'on enumere, teste, ou recolle.

---

## 2.6 - Exercices

:::exercise{id="{{EX_MA_SIEVE_COUNT}}"}
:::

:::exercise{id="{{EX_MA_MILLER_RABIN}}"}
:::

:::exercise{id="{{EX_MA_CRT}}"}
:::
