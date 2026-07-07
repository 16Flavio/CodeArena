# 4. Sliding window

## 4.1 - Intuition

Une **fenêtre glissante** est un cas particulier de two-pointers où
la zone $[i, j]$ représente une **sous-séquence contiguë** d'un
flux ou d'un tableau, et où on entretient à chaque tour une
*statistique* sur cette fenêtre (somme, max, dictionnaire de
fréquences). On itère $j$ de la gauche vers la droite et on
**fait avancer $i$** dès que la fenêtre devient invalide.

Coût : $O(n)$ amorti, parce que $i$ et $j$ chacun ne peuvent que
croître. Coût mémoire : la statistique de la fenêtre, souvent
$O(\Sigma)$ avec $\Sigma$ la taille de l'alphabet.

---

## 4.2 - Fenêtre de **taille fixe** $k$

> Plus grande somme parmi toutes les sous-tableaux de longueur $k$.

```python
def max_window_sum(A, k):
    s = sum(A[:k])
    best = s
    for j in range(k, len(A)):
        s += A[j] - A[j - k]    # entre A[j], sort A[j-k]
        best = max(best, s)
    return best
```

L'astuce : maintenir la statistique en $O(1)$ par déplacement
plutôt que la recalculer en $O(k)$. Patron général : on **ajoute**
ce qui rentre, on **retire** ce qui sort.

---

## 4.3 - Fenêtre de **taille variable** : le patron

C'est le cas le plus puissant. On veut la plus longue (ou plus
petite) fenêtre satisfaisant un prédicat $P$ "monotone par
contraction" :

$$
P(i, j) = \text{vrai} \implies P(i+1, j) = \text{vrai}.
$$

Autrement dit, **rétrécir** une fenêtre valide la garde valide.
Symétriquement pour les variantes "min" : élargir une fenêtre
invalide la garde invalide.

### Patron : plus longue sous-tableau valide

```python
def longest_valid(A, predicate):
    i = 0
    best = 0
    state = init()                        # statistique de la fenêtre
    for j in range(len(A)):
        add(state, A[j])                  # A[j] entre
        while not predicate(state):       # restaurer la validité
            remove(state, A[i])
            i += 1
        best = max(best, j - i + 1)
    return best
```

**Pourquoi $O(n)$ ?** $i$ ne recule pas, donc le total des
incréments est $\le n$. Le `while` interne est exécuté au plus $n$
fois sur l'ensemble de l'algorithme - il **n'augmente pas** le
coût total.

---

## 4.4 - Application : plus longue sous-chaîne sans répétition

> Étant donnée une chaîne $s$, trouver la longueur de la plus
> longue sous-chaîne **sans caractère répété**.

Statistique : un dictionnaire `last[c] = dernière position de c`.
Le prédicat "fenêtre valide" est *aucune répétition*.

```python
def longest_unique(s):
    last = {}
    i = 0
    best = 0
    for j, c in enumerate(s):
        if c in last and last[c] >= i:
            i = last[c] + 1     # saut direct, pas de while !
        last[c] = j
        best = max(best, j - i + 1)
    return best
```

Astuce d'optimisation : au lieu de boucler avec `while`, on saute
$i$ directement à `last[c] + 1`. C'est **équivalent** en
complexité (toujours $O(n)$) mais une constante meilleure.

---

## 4.5 - Application : sous-tableau de somme $\ge S$

C'est l'exemple de la leçon 3 - déjà vu. La frontière entre
"two-pointer" et "sliding window" est floue : c'est la même idée,
juste un focus différent (deux index vs une statistique
agrégée).

---

## 4.6 - Pièges

1. **Prédicat non monotone** : si rétrécir une fenêtre valide peut
   la rendre invalide, le patron ne fonctionne pas.
   *Contre-exemple* : "plus longue fenêtre dont la somme est
   exactement $S$" avec valeurs négatives - ajouter des éléments
   peut faire osciller la somme.
2. **Statistique trop coûteuse à mettre à jour** : si l'opération
   `add` ou `remove` coûte $O(\log n)$ (insertion dans un sorted
   set, etc.), le coût global passe à $O(n \log n)$. C'est encore
   bon, mais ce n'est plus du *pure* sliding window.
3. **Doubles boucles cachées** : dans le patron, le `while` interne
   doit *amortir* à $O(n)$ total. Si on y fait du travail
   non-trivial pour chaque tour, l'amortissement saute.

---

## 4.7 - Exercices

:::exercise{id="{{EX_SE_FIXEDSUM}}"}
:::

:::exercise{id="{{EX_SE_LONGEST_UNIQUE}}"}
:::

:::exercise{id="{{EX_SE_K_DISTINCT}}"}
:::
