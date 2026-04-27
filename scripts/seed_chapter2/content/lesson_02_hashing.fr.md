# 2. Tables de hachage

## 2.1 — L'idée : court-circuiter le tri

On veut une structure permettant `insert(k, v)`, `lookup(k)` et
`delete(k)` en $\Theta(1)$ **en moyenne**, sans maintenir d'ordre.

L'astuce : une fonction $h : \mathcal{U} \to \{0, 1, \dots, m-1\}$
qui associe à chaque clé un indice de tableau. On stocke $(k, v)$
dans `T[h(k)]`. Si $h$ disperse bien les clés, on accède quasi
instantanément.

> **Le piège.** Pour toute fonction $h$ fixée et tout adversaire qui
> connaît $h$, on peut construire $n$ clés qui se collent toutes sur
> le même bucket — performance dégradée à $\Theta(n)$. C'est pour ça
> qu'on utilise du **hachage universel** (famille aléatoire).

---

## 2.2 — Hachage universel

### Définition

Une famille $\mathcal{H}$ de fonctions $h : \mathcal{U} \to [m]$ est
**universelle** si pour toutes clés distinctes $x \neq y$ :

$$\Pr_{h \sim \mathcal{H}}[h(x) = h(y)] \le \frac{1}{m}.$$

L'aléa est sur le choix de $h$ dans la famille — pas sur les clés.
Une fois $h$ tirée, elle reste fixée pour toute la durée de vie de
la table.

### Exemple : famille linéaire modulaire

Soit $p$ un premier $> |\mathcal{U}|$. Pour $a \in \{1, \dots, p-1\}$
et $b \in \{0, \dots, p-1\}$, posons :

$$h_{a,b}(k) = ((a\,k + b) \bmod p) \bmod m.$$

**Théorème.** $\mathcal{H} = \{h_{a,b}\}$ est universelle.

*Esquisse.* Pour $x \neq y$, on montre que $((ax + b) \bmod p) -
((ay + b) \bmod p) \equiv a(x - y) \pmod p$ prend toutes les
valeurs non-nulles avec la même probabilité quand $a$ varie. La
projection $\bmod m$ ajoute au plus $\lceil p/m \rceil / p \le 1/m
+ \varepsilon$ de proba de collision. $\square$

---

## 2.3 — Résolution de collisions

Deux philosophies :

### Chaînage

Chaque bucket `T[i]` est une liste (chaînée) des paires `(k, v)`
avec $h(k) = i$.

```python
def insert(T, k, v, h):
    T[h(k)].append((k, v))      # ou .replace si k existe déjà

def lookup(T, k, h):
    for (kk, vv) in T[h(k)]:
        if kk == k: return vv
    return None
```

**Coût en espérance** (avec $\mathcal{H}$ universelle, $n$ clés
insérées, $m$ buckets, **facteur de charge** $\alpha = n/m$) :

$$\mathbb{E}[\text{taille du bucket de la clé recherchée}] \le 1 + \alpha.$$

Quand $\alpha = O(1)$, on a `lookup` en $\Theta(1)$ en espérance.
Pour maintenir $\alpha$ borné, on **redimensionne** la table (cf.
tableau dynamique du ch. 1).

:::viz-hash-table{keys="5,12,19,7,42,26,33"}
:::

Joue avec : insère plusieurs clés, change $m$. Plus $m$ est petit,
plus tu vois s'allonger les chaînes ; les collisions sont colorées
en rouge.

### Adressage ouvert (sondage linéaire)

On stocke directement dans le tableau ; en cas de collision, on
sonde la cellule suivante :

```python
def insert(T, k, v, h, m):
    i = h(k) % m
    while T[i] is not None and T[i].k != k:
        i = (i + 1) % m
    T[i] = Entry(k, v)
```

**Avantages** : meilleure localité cache, pas de pointeurs.

**Inconvénients** :
- Performance s'écroule quand $\alpha \to 1$ — il faut redimensionner
  bien avant ($\alpha < 0{,}7$ typiquement).
- Suppression non triviale : on ne peut pas mettre `None` à la place
  d'un élément supprimé sans casser les sondages futurs ; on
  utilise un marqueur **tombstone**.

**Coût en espérance** (sondage linéaire, hachage universel) :

$$\mathbb{E}[\text{nombre de sondes par lookup}] = \Theta\left(\frac{1}{(1 - \alpha)^2}\right).$$

Avec $\alpha = 0{,}5$, environ 4 sondes en moyenne ; avec $\alpha
= 0{,}9$, $\approx 100$ sondes — d'où la consigne de redimensionner
tôt.

### Tableau comparatif

| Critère | Chaînage | Adressage ouvert |
|---------|----------|------------------|
| Lookup moyen | $\Theta(1 + \alpha)$ | $\Theta(1/(1-\alpha)^2)$ |
| Mémoire | + pointeurs | aucune |
| Cache | médiocre | excellent |
| $\alpha$ pratique | jusqu'à $\sim 1$ | $< 0{,}7$ |
| Suppression | trivial | tombstones |

---

## 2.4 — Algorithme : `lookup` avec chaînage + preuve de complexité

### Code

```python
def lookup(T, k):
    h = T.hash(k)
    bucket = T.buckets[h]
    for (kk, vv) in bucket:     # parcours linéaire
        if kk == k:
            return vv
    return None
```

### Espérance du nombre de comparaisons

Soient $n$ clés stockées et $m$ buckets, hachage universel.
Cherchons une clé $k$ (présente ou absente). Pour chaque autre clé
$k' \neq k$ stockée, posons $X_{k'} = \mathbb{1}[h(k') = h(k)]$.

Le nombre de comparaisons est $1 + \sum_{k' \neq k} X_{k'}$ (la
clé elle-même ou la sentinelle de fin, plus chaque collision).

Par universalité : $\mathbb{E}[X_{k'}] \le 1/m$.

$$\mathbb{E}[\text{nb comparaisons}] \le 1 + \sum_{k' \neq k} \frac{1}{m} \le 1 + \frac{n}{m} = 1 + \alpha.$$

Quand on maintient $\alpha = O(1)$ par redimensionnement, lookup
coûte $\Theta(1)$ en espérance. $\square$

> **Subtilité.** Le pire cas reste $\Theta(n)$ : un adversaire qui
> *voit* la fonction $h$ après son tirage peut forger une attaque.
> En production, on utilise du **hachage cryptographique** (SipHash
> dans Python depuis 3.4) ou des fonctions à clé secrète.

---

## 2.5 — Exercices

:::exercise{id="{{EX_HT_DISTINCT}}"}
:::

:::exercise{id="{{EX_HT_TWOSUM}}"}
:::

:::exercise{id="{{EX_HT_ZEROSUM}}"}
:::
