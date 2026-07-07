# 3. Z-function & Manacher

## 3.1 - Intuition

Deux algorithmes lineaires, une meme idee : **reutiliser un travail
deja fait** grace a une fenetre qui memorise le segment le plus a
droite deja explore.

- La **Z-function** mesure, en chaque position, le plus long prefixe
  commun avec le debut de la chaine.
- **Manacher** trouve tous les palindromes en exploitant la symetrie
  d'un palindrome deja connu.

Dans les deux cas, une position a l'interieur de la fenetre courante
herite d'une valeur calculee a sa **position miroir**, evitant de tout
recommencer.

---

## 3.2 - Algorithmes

### Z-function

$z_i$ = longueur du plus long prefixe commun de $s$ et de $s_i s_{i+1}
\dots$ (avec $z_0 = 0$).

```python
def z_function(s):
    n = len(s); z = [0] * n
    l = r = 0                          # fenetre [l, r) = prefixe le plus a droite
    for i in range(1, n):
        if i < r:
            z[i] = min(r - i, z[i - l])  # heritage du miroir
        while i + z[i] < n and s[z[i]] == s[i + z[i]]:
            z[i] += 1                    # extension
        if i + z[i] > r:
            l, r = i, i + z[i]
    return z
```

### Manacher

Pour traiter uniformement palindromes pairs et impairs, on insere des
separateurs : `abc` devient `#a#b#c#`. Chaque palindrome de la chaine
transformee a une longueur impaire, et son **rayon** dans la chaine
transformee egale la longueur du palindrome original. La fenetre
$[c - p, c + p]$ du palindrome le plus a droite joue le role de la
fenetre $[l, r]$ de la Z-function.

---

## 3.3 - Complexite

$$
\begin{aligned}
\text{Z-function} &: \Theta(n), \\
\text{Manacher} &: \Theta(n).
\end{aligned}
$$

L'argument est identique a KMP : le bord droit $r$ de la fenetre ne
recule jamais et avance au plus $n$ fois, donc le total des extensions
est lineaire.

---

## 3.4 - Pieges classiques

1. **Convention de $z_0$.** Certaines definitions posent $z_0 = n$,
   d'autres $z_0 = 0$. Fixer la sienne et rester coherent (ici $0$).
2. **Separateurs de Manacher.** Le `#` doit border **les deux
   extremites** ; oublier un bord decale tous les rayons.
3. **Rayon vs longueur.** Dans la chaine transformee, le rayon $p[i]$
   egale directement la longueur du palindrome original - une source
   frequente de confusion.
4. **Fenetre mal mise a jour.** N'etendre $[l, r]$ (ou $[c, r]$) que
   lorsque la nouvelle valeur depasse strictement $r$.

---

## 3.5 - Deux couteaux, mille coupes

La Z-function fait de la recherche de motif, du comptage de bordures,
de la compression. Manacher denombre les palindromes, trouve le plus
long, teste des symetries. Reconnaitre la **fenetre reutilisable** est
le fil commun de cette lecon - le meme ressort que KMP, applique a
deux questions differentes.

---

## 3.6 - Exercices

:::exercise{id="{{EX_TX_ZFUNC}}"}
:::

:::exercise{id="{{EX_TX_LONGEST_PALINDROME}}"}
:::

:::exercise{id="{{EX_TX_COUNT_PALINDROMES}}"}
:::
