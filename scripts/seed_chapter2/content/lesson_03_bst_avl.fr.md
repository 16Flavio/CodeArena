# 3. Arbres binaires de recherche & équilibrage (AVL)

## 3.1 - L'arbre binaire de recherche

Un **BST** est un arbre binaire dans lequel, pour chaque nœud $v$ de
clé $v.k$ :

$$\forall u \in \text{sous-arbre gauche}(v),\ u.k < v.k \quad\text{et}\quad \forall u \in \text{sous-arbre droit}(v),\ u.k > v.k.$$

Cette propriété donne immédiatement :

- **Parcours in-order** : visite les clés en ordre croissant - $\Theta(n)$.
- **Recherche** d'une clé : descente le long d'un chemin, $\Theta(h)$
  où $h$ est la hauteur.
- **Insertion** : descente jusqu'à une feuille, puis attache d'un
  nouveau nœud, $\Theta(h)$.
- **Successeur d'un nœud** : si sous-arbre droit non vide, le minimum
  de ce sous-arbre ; sinon, premier ancêtre dont on est dans le
  sous-arbre gauche, $\Theta(h)$.

```python
class Node:
    def __init__(self, k):
        self.k = k
        self.l = None
        self.r = None
        self.h = 1   # hauteur, utilisée par AVL

def search(root, k):
    while root and root.k != k:
        root = root.l if k < root.k else root.r
    return root

def insert(root, k):
    if root is None:    return Node(k)
    if k < root.k:      root.l = insert(root.l, k)
    elif k > root.k:    root.r = insert(root.r, k)
    return root
```

> **Le drame.** Si on insère $1, 2, 3, \dots, n$ dans cet ordre, le
> BST devient une chaîne, $h = n$, toutes les opérations en
> $\Theta(n)$. C'est le pire cas - fréquent en pratique (entrées
> triées).

:::viz-bst{keys="50,30,70,20,40,60,80"}
:::

Reset, puis insère $1, 2, 3, 4, 5$ un par un - l'arbre dégénère en
chaîne (hauteur $5$). Maintenant reset et insère un BST équilibré
comme `4,2,6,1,3,5,7` : hauteur $3$. Même $n = 7$, même clés,
**hauteur radicalement différente selon l'ordre d'insertion**.

---

## 3.2 - Rotations

Une **rotation** restructure un sous-arbre **sans casser la propriété
BST** et change la hauteur localement.

### Rotation droite

```
     y               x
    / \             / \
   x   C    →     A   y
  / \                 / \
 A   B               B   C
```

**Invariant clé.** Comme tous les éléments de $A$ sont $< x.k$, ceux
de $B$ entre $x.k$ et $y.k$, et ceux de $C$ $> y.k$, l'arbre après
rotation reste un BST. Coût : $\Theta(1)$.

```python
def rot_right(y):
    x = y.l
    y.l = x.r
    x.r = y
    update_height(y)        # y est maintenant en bas
    update_height(x)
    return x                # nouvelle racine du sous-arbre
```

La **rotation gauche** est symétrique. Ces deux opérations
$\Theta(1)$ sont la brique de base de tous les arbres équilibrés.

---

## 3.3 - AVL : invariant de hauteur

Inventés en 1962 par Adelson-Velsky et Landis. **Invariant** : pour
chaque nœud $v$,

$$|h(v.l) - h(v.r)| \le 1.$$

On note $\text{bf}(v) = h(v.l) - h(v.r)$ le **facteur d'équilibre**.
Un AVL maintient $\text{bf}(v) \in \{-1, 0, +1\}$.

### Théorème de hauteur

**Théorème.** Un AVL à $n$ nœuds a hauteur $h \le c \cdot \log_2(n+1)
+ O(1)$ pour une constante $c \approx 1{,}44$.

*Preuve.* Soit $N(h)$ le **nombre minimum** de nœuds d'un AVL de
hauteur $h$. Un tel arbre minimal a une racine, un sous-arbre de
hauteur $h-1$ et un de hauteur $h-2$ (l'autre ne peut être plus
petit). Donc :

$$N(h) = 1 + N(h-1) + N(h-2),\quad N(1) = 1,\ N(2) = 2.$$

(La hauteur compte les nœuds, comme dans le code ci-dessus : un
nœud seul a hauteur $1$.) C'est la suite de Fibonacci décalée :
$N(h) = F(h+2) - 1$ où $F$ est Fibonacci avec $F(1) = F(2) = 1$ -
vérification : $F(3) - 1 = 1$, $F(4) - 1 = 2$, $F(5) - 1 = 4$,
$F(6) - 1 = 7$. Comme $F(k) = \Theta(\varphi^k)$ avec $\varphi =
(1+\sqrt 5)/2$, on a $h \le \log_\varphi (n + 1) - O(1) =
\frac{\log_2(n+1)}{\log_2 \varphi} + O(1) \approx 1{,}44 \log_2 n$.
$\square$

→ **Toutes les opérations** (search, insert, delete) sont
$\Theta(\log n)$ pire cas dans un AVL.

---

## 3.4 - Insertion AVL : algorithme

Après une insertion BST classique, on remonte la trace de récursion ;
à chaque ancêtre :

1. Recalculer la hauteur.
2. Calculer $\text{bf}$. Si $\text{bf} \in \{-1, 0, +1\}$, OK.
3. Sinon, **rééquilibrer** par rotations selon le cas.

### Les quatre cas de rééquilibrage

Soit $v$ le premier nœud déséquilibré rencontré en remontant.

| Cas | Description | Action |
|-----|-------------|--------|
| **LL** | $\text{bf}(v) = +2$, l'insertion est dans le sous-arbre gauche-gauche | rotation droite sur $v$ |
| **RR** | $\text{bf}(v) = -2$, dans le droit-droit | rotation gauche sur $v$ |
| **LR** | $\text{bf}(v) = +2$, dans le gauche-droit | rotation gauche sur $v.l$, puis droite sur $v$ |
| **RL** | $\text{bf}(v) = -2$, dans le droit-gauche | rotation droite sur $v.r$, puis gauche sur $v$ |

### Code

```python
def height(n): return n.h if n else 0
def update_height(n): n.h = 1 + max(height(n.l), height(n.r))
def bf(n): return height(n.l) - height(n.r)

def insert_avl(root, k):
    if root is None: return Node(k)
    if k < root.k:   root.l = insert_avl(root.l, k)
    elif k > root.k: root.r = insert_avl(root.r, k)
    else:            return root   # déjà présent
    update_height(root)
    b = bf(root)
    if b > 1 and k < root.l.k:                      # LL
        return rot_right(root)
    if b < -1 and k > root.r.k:                     # RR
        return rot_left(root)
    if b > 1 and k > root.l.k:                      # LR
        root.l = rot_left(root.l)
        return rot_right(root)
    if b < -1 and k < root.r.k:                     # RL
        root.r = rot_right(root.r)
        return rot_left(root)
    return root
```

### Preuve de correction

**Invariant.** Après chaque appel à `insert_avl`, le sous-arbre
retourné est un AVL contenant exactement les clés du sous-arbre
d'origine plus $k$.

*Hérédité (l'argument-clé).* Si le sous-arbre fils correspondant est
un AVL après l'appel récursif, alors `update_height` rend la hauteur
correcte. Si $|\text{bf}| \le 1$, on retourne $\text{root}$, qui
satisfait l'invariant AVL trivialement (on n'a pas modifié les fils).

Si $|\text{bf}| = 2$, on est dans un des quatre cas. Une analyse cas
par cas (qu'on ne reproduit pas en entier ici) montre que la (les)
rotation(s) :

1. préservent la propriété BST (par construction),
2. ramènent la hauteur du sous-arbre à sa valeur **avant
   insertion**,
3. donc en remontant, aucun ancêtre supplémentaire ne peut être
   déséquilibré.

D'où la propriété **fondamentale** : une insertion AVL fait au plus
**deux rotations** ($\Theta(1)$), et la remontée s'arrête dès le
premier rééquilibrage. Coût total $\Theta(\log n)$. $\square$

> **AVL vs rouge-noir.** L'AVL est **plus strict** (équilibrage
> serré, hauteur $\sim 1{,}44 \log n$), donc les recherches sont
> légèrement plus rapides ; en revanche les rouge-noir font moins
> de rotations en moyenne (utilisé dans `std::map`, `TreeMap` Java,
> Linux kernel). Pour une charge majoritaire en lecture, AVL gagne ;
> pour des insertions/suppressions intensives, rouge-noir.

---

## 3.5 - Exercices

:::exercise{id="{{EX_BST_INORDER}}"}
:::

:::exercise{id="{{EX_BST_PREORDER}}"}
:::

:::exercise{id="{{EX_BST_HEIGHT}}"}
:::
