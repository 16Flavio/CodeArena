# 2. KMP & fonction prefixe

## 2.1 - Intuition

La recherche naive d'un motif $P$ dans un texte $T$ recommence a zero
a chaque decalage : $O(|T| \cdot |P|)$. Le gaspillage est evident -
apres un echec, on **oublie** tout ce qu'on venait d'apparier.
L'algorithme de **Knuth-Morris-Pratt** (KMP) ne recule jamais dans le
texte : quand un caractere echoue, il se rabat sur le plus long
**prefixe deja apparie** qui reste valide.

Le secret est la **fonction prefixe** $\pi$ du motif : $\pi[i]$ est la
longueur du plus long prefixe de $P$ qui est aussi un suffixe de
$P[0..i]$. Elle encode « ou reprendre » apres un echec.

---

## 2.2 - Algorithme & preuve

```python
def prefix_function(s):
    n = len(s); pi = [0] * n
    for i in range(1, n):
        j = pi[i-1]
        while j > 0 and s[i] != s[j]:
            j = pi[j-1]          # se rabattre sur un prefixe plus court
        if s[i] == s[j]:
            j += 1
        pi[i] = j
    return pi
```

Pour chercher $P$ dans $T$, on calcule $\pi$ sur la chaine
$P + \# + T$ (avec $\#$ absent de l'alphabet) : chaque position ou
$\pi$ atteint $|P|$ marque une occurrence.

- **Correction.** L'invariant : apres avoir lu $s[0..i]$, $j = \pi[i]$
  est la longueur du plus long prefixe de $s$ egal a un suffixe. La
  boucle `while` teste les candidats par ordre decroissant via la
  chaine des bords $\pi[j-1]$, garantissant qu'on trouve le plus long
  valide. $\square$

- **Amortissement.** $j$ augmente d'au plus $1$ par etape et ne peut
  decroitre qu'en tout $O(n)$ fois : chaque `j = pi[j-1]` consomme une
  hausse anterieure. Le total des operations est donc lineaire.

**Suis l'algorithme** : construis d'abord la table pi du motif, puis fais glisser le motif sur le texte en te servant de pi a chaque echec.

:::viz-kmp{text="abxabcabcaby" pattern="abcaby"}
:::

---

## 2.3 - Complexite

$$
\begin{aligned}
\text{fonction prefixe} &: \Theta(|P|), \\
\text{recherche complete} &: \Theta(|T| + |P|).
\end{aligned}
$$

Aucun retour en arriere dans le texte : chaque caractere est examine
un nombre **amorti** constant de fois.

---

## 2.4 - Pieges classiques

1. **Separateur oublie.** Pour chercher via $P + \# + T$, le
   separateur $\#$ doit etre **hors** de l'alphabet, sinon un faux
   match traverse la frontiere.
2. **Indices de $\pi$.** $\pi[i]$ concerne $s[0..i]$ **inclus** ; la
   transition part de $\pi[i-1]$, pas de $\pi[i]$.
3. **Bords et periode.** Confondre « plus long bord » ($\pi[n-1]$) et
   « periode » ($n - \pi[n-1]$) est une erreur frequente.
4. **Chaine de bords.** Tous les bords s'obtiennent en iterant
   $\pi[k-1]$ jusqu'a 0 - ne pas s'arreter au premier.

---

## 2.5 - Bien plus que chercher

La fonction prefixe repond a une famille de questions : plus petite
periode, tous les bords, compression par periode, comptage
d'occurrences de chaque prefixe, construction d'un automate de motif.
Un seul tableau $\pi$, calcule en temps lineaire, et toute la
structure repetitive du motif se lit.

---

## 2.6 - Exercices

:::exercise{id="{{EX_TX_KMP_POSITIONS}}"}
:::

:::exercise{id="{{EX_TX_MIN_PERIOD}}"}
:::

:::exercise{id="{{EX_TX_BORDERS}}"}
:::
