# 1. Tableaux, listes chaînées, piles, files & deques

## 1.1 — Le tableau, structure de base

Un **tableau** est une suite contiguë de cellules en mémoire. Indexé
par un entier $i \in [0, n[$, l'accès $A[i]$ se fait en $\Theta(1)$
grâce à l'arithmétique d'adresses : $\text{adresse}(A[i]) =
\text{base} + i \cdot \text{taille\_élément}$.

| Opération | Tableau statique | Tableau dynamique (cf. ch. 1) |
|-----------|------------------|-------------------------------|
| Accès $A[i]$ | $\Theta(1)$ | $\Theta(1)$ |
| Append fin | impossible | $\Theta(1)$ amorti |
| Insert position $i$ | $\Theta(n - i)$ | $\Theta(n - i)$ |
| Suppression position $i$ | $\Theta(n - i)$ | $\Theta(n - i)$ |

Le coût des insertions/suppressions au milieu vient du **décalage**
de tous les éléments qui suivent.

---

## 1.2 — Listes chaînées

Pour rendre l'insertion/suppression $\Theta(1)$ *à un point connu*,
on remplace la contiguïté mémoire par des **liens** entre nœuds.

### Liste simplement chaînée

```python
class Node:
    def __init__(self, val, nxt=None):
        self.val = val
        self.nxt = nxt
```

- **Insertion en tête** : $\Theta(1)$.
- **Suppression en tête** : $\Theta(1)$.
- **Accès position $i$** : $\Theta(i)$ — il faut parcourir.
- **Insertion après un nœud connu** : $\Theta(1)$.

### Liste doublement chaînée

Chaque nœud porte aussi `prev`. On gagne :

- **Suppression d'un nœud connu** en $\Theta(1)$ (sans avoir à
  retrouver son prédécesseur).
- **Itération inverse**.

Au prix d'un mot de mémoire supplémentaire par nœud.

> **Quand préférer une liste chaînée à un tableau dynamique ?** Quand
> on insère/supprime souvent au milieu *à un point déjà tenu en main*
> (un itérateur, un nœud sentinelle). Sinon, le tableau dynamique gagne
> presque toujours grâce à la localité cache.

---

## 1.3 — Piles, files, deques

Trois interfaces qui s'implémentent au-dessus d'un tableau dynamique
ou d'une liste doublement chaînée.

### Pile (LIFO)

Opérations : `push`, `pop`, `top`. Toutes en $\Theta(1)$ amorti
(tableau dynamique) ou $\Theta(1)$ pire cas (liste).

### File (FIFO)

Opérations : `enqueue` (push arrière), `dequeue` (pop avant).

- **Implémentation tableau circulaire** : deux indices `head` et
  `tail`, modulo la capacité. $\Theta(1)$ amorti.
- **Implémentation liste doublement chaînée** : $\Theta(1)$ pire cas.

### Deque (double-ended queue)

Opérations : `push_front`, `push_back`, `pop_front`, `pop_back`. Toutes
en $\Theta(1)$ avec une liste doublement chaînée ou un tableau
circulaire à doublement.

> **Le deque est l'arme secrète des algos de fenêtre glissante** —
> on l'utilise dans la leçon ci-dessous (max coulissant) pour
> maintenir une fenêtre triée à coût amorti $\Theta(1)$ par élément.

---

## 1.4 — Algorithme : file avec deux piles

Un classique qui montre comment composer des structures.

### Idée

On utilise deux piles, `in` (pour les enqueue) et `out` (pour les
dequeue). Quand `out` est vide et qu'on doit dequeue, on **transfère**
toute `in` vers `out` en l'inversant.

### Code

```python
class Queue:
    def __init__(self):
        self.in_  = []
        self.out_ = []

    def enqueue(self, x):
        self.in_.append(x)

    def dequeue(self):
        if not self.out_:
            while self.in_:
                self.out_.append(self.in_.pop())
        return self.out_.pop() if self.out_ else None
```

### Preuve de correction

**Invariant.** À tout moment, la concaténation `out_[::-1] + in_`
représente la file dans l'ordre d'arrivée.

- *Initialisation.* Les deux piles sont vides, l'invariant est vrai.
- *Hérédité.*
  - `enqueue(x)` ajoute $x$ en sommet de `in_`, donc à la fin de la
    concaténation : OK.
  - `dequeue` quand `out_` non-vide : retire le sommet de `out_`, qui
    est le **premier** élément de `out_[::-1]`. OK.
  - `dequeue` quand `out_` vide : on transfère `in_` en sommet de
    `out_` en l'inversant via `pop`. Après transfert, `out_[::-1]`
    contient les éléments dans le même ordre que `in_` original.
    Puis le `pop` final retire le premier. OK.

$\square$

### Analyse de complexité (amortie)

Chaque élément est `push`é dans `in_` une fois, transféré une fois
vers `out_`, puis `pop`é une fois. Soit **3 opérations en tout** par
élément, sur la durée de vie. Donc le coût amorti d'`enqueue` et de
`dequeue` est $\Theta(1)$, même si une `dequeue` particulière peut
coûter $\Theta(n)$ (au moment du transfert).

C'est exactement la méthode du banquier (cf. ch. 1) : on facture $3$
à chaque `enqueue` ; le crédit posé sur l'élément paie son transfert
puis sa sortie.

---

## 1.5 — Exercices

:::exercise{id="{{EX_DS_QUEUE}}"}
:::

:::exercise{id="{{EX_DS_SLIDING}}"}
:::

:::exercise{id="{{EX_DS_JOSEPHUS}}"}
:::
