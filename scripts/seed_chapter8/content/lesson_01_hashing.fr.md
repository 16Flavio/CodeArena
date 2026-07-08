# 1. Hachage de chaines (Rabin-Karp)

## 1.1 - Intuition

Comparer deux chaines de longueur $L$ coute $O(L)$. Si on doit
comparer des milliers de fenetres, cela devient lent. L'idee du
**hachage** : resumer chaque chaine par un **nombre** ; deux chaines
egales ont le meme hash, et deux hash differents garantissent deux
chaines differentes. La comparaison devient $O(1)$.

Le hachage **polynomial** voit une chaine comme les chiffres d'un
nombre en base $B$ :

$$
h(s) = \bigl(s_0 B^{L-1} + s_1 B^{L-2} + \dots + s_{L-1}\bigr) \bmod M.
$$

Sa force : le hash d'une fenetre glissante se met a jour en $O(1)$
quand on avance d'un caractere - c'est **Rabin-Karp**.

---

## 1.2 - Algorithme

```python
def count_occurrences(t, p):
    n, m = len(t), len(p)
    if m > n: return 0
    MOD = (1 << 61) - 1; B = 131
    hp = 0
    for c in p: hp = (hp * B + ord(c)) % MOD      # hash du motif
    power = pow(B, m - 1, MOD)
    h = 0
    for i in range(m): h = (h * B + ord(t[i])) % MOD
    cnt = 0
    for i in range(m - 1, n):
        if i >= m:                                # faire glisser la fenetre
            h = ((h - ord(t[i-m]) * power) * B + ord(t[i])) % MOD
        if h == hp and t[i-m+1:i+1] == p:         # verification
            cnt += 1
    return cnt
```

### Collisions et double hash

Deux chaines differentes peuvent partager un hash : une **collision**.
Pour un seul modulo $\sim 10^9$, une comparaison de nombreuses paires
finit par en produire. La parade : un **double hash** (deux modulos
$M_1, M_2$ premiers), ramenant la probabilite a $\sim 1/(M_1 M_2)$,
negligeable. En cas de doute critique, verifier le match caractere par
caractere.

---

## 1.3 - Complexite

$$
\begin{aligned}
\text{pretraitement} &: \Theta(|P|), \\
\text{balayage du texte} &: \Theta(|T|), \\
\text{par fenetre} &: \Theta(1)\ \text{(mise a jour du hash)}.
\end{aligned}
$$

Soit $\Theta(|T| + |P|)$ au total, comme les algorithmes dedies de la
lecon suivante - mais avec une constante souvent plus simple a coder.

---

## 1.4 - Pieges classiques

1. **Base ou modulo trop petits.** Un modulo de $\sim 10^9$ collisionne
   des que l'on compare $\sim 10^{4.5}$ paires (paradoxe des
   anniversaires). Preferer $M \approx 2^{61} - 1$ ou un double hash.
2. **Debordement.** En C++/Java, multiplier deux entiers de 64 bits
   deborde ; utiliser `__int128` ou un modulo tenant dans 32 bits.
3. **Puissance mal precalculee.** `power = B^(m-1)` doit correspondre a
   la longueur exacte de la fenetre.
4. **Confiance aveugle.** Pour une reponse exacte et critique,
   confirmer un match par une comparaison directe.

---

## 1.5 - Un outil polyvalent

Recherche de motif, comptage de sous-chaines distinctes, plus longue
sous-chaine commune (par dichotomie sur la longueur), comparaison de
sous-chaines en $O(1)$ apres pretraitement : le hachage attaque une
foule de problemes avec un code minimal. Il faut simplement rester
conscient du risque de collision.

---

## 1.6 - Exercices

:::exercise{id="{{EX_TX_RK_COUNT}}"}
:::

:::exercise{id="{{EX_TX_DISTINCT_SUBSTR_K}}"}
:::

:::exercise{id="{{EX_TX_LONGEST_COMMON_SUBSTR}}"}
:::
