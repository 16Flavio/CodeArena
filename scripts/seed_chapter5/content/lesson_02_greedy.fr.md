# 2. Algorithmes gloutons & preuves

## 2.1 - Intuition

Un algorithme **glouton** construit une solution pas à pas, en
faisant à chaque étape le choix **localement le plus avantageux**,
sans jamais revenir en arrière. C'est la stratégie la plus naïve qui
soit - et pourtant, pour une classe précise de problèmes, elle donne
l'optimum global.

Le danger est réel : le glouton se trompe souvent. Rendre la monnaie
avec les pièces $\{1, 3, 4\}$ pour $6$ donne $4 + 1 + 1$ (trois
pièces) alors que $3 + 3$ suffit. Un choix glouton n'est correct que
si on le **prouve**. Deux ingrédients suffisent :

- **Propriété de choix glouton** : un optimum contient (ou peut être
  transformé pour contenir) le premier choix glouton.
- **Sous-structure optimale** : après ce choix, le sous-problème
  restant se résout de la même manière.

---

## 2.2 - Algorithme & argument d'échange

Prenons la **sélection d'activités** : $n$ intervalles $[s_i, e_i)$,
en choisir un maximum de deux à deux disjoints.

```python
def select(intervals):
    intervals.sort(key=lambda p: p[1])   # par fin croissante
    count, cur_end = 0, float('-inf')
    for s, e in intervals:
        if s >= cur_end:                 # compatible ?
            count += 1
            cur_end = e                  # on l'accepte
    return count
```

Le choix glouton : **prendre l'activité qui finit le plus tôt**.

**Regarde le glouton choisir** : les intervalles sont triés par fin
croissante ; `step` prend chaque activité compatible et rejette celles
qui chevauchent la fin courante (ligne pointillée).

:::viz-greedy-intervals{intervals="1,4;3,5;0,6;5,7;3,8;5,9;6,10;8,11;8,12;2,13"}
:::

### Preuve par argument d'échange

Soit $g_1$ l'activité de fin minimale, et soit $O$ une solution
optimale. Trions $O$ par date de fin et notons $o_1$ sa première
activité.

- Par minimalité, $e(g_1) \le e(o_1)$.
- Donc toute activité de $O$ compatible avec $o_1$ (qui commence
  après $e(o_1)$) est **aussi** compatible avec $g_1$.
- Remplacer $o_1$ par $g_1$ dans $O$ donne une solution valide, de
  **même cardinalité** : elle reste optimale et commence par le
  choix glouton.

Par récurrence sur le sous-problème « activités commençant après
$e(g_1)$ », le glouton atteint l'optimum. $\square$

L'échange est le patron de preuve universel du glouton : montrer
qu'on peut **transformer** tout optimum pour qu'il adopte le premier
choix glouton, sans perdre en qualité.

---

## 2.3 - Complexité

Le coût est dominé par le tri initial :

$$
T(n) = \underbrace{\Theta(n \log n)}_{\text{tri}} +
\underbrace{\Theta(n)}_{\text{balayage}} = \Theta(n \log n).
$$

Pour la fusion de cordes (codage de Huffman), le tri est remplacé
par un **tas** qui reçoit $2n$ opérations en $\Theta(\log n)$
chacune, soit encore $\Theta(n \log n)$.

---

## 2.4 - Pièges classiques

1. **Trier selon le mauvais critère.** Pour la sélection
   d'activités, trier par **fin** (et non par début, ni par durée)
   est ce qui rend le glouton correct. Le critère est le cœur de la
   preuve.
2. **Confondre glouton et programmation dynamique.** Si aucun
   argument d'échange ne tient (sac à dos 0/1, par exemple), le
   glouton échoue et il faut une DP (leçon 3).
3. **Oublier de prouver.** Un glouton qui « marche sur les
   exemples » peut échouer sur un cas limite. Sans preuve, pas de
   garantie.
4. **Égalités frontière.** Intervalles semi-ouverts $[s, e)$ :
   `s >= cur_end` (et non `>`) autorise une activité à commencer
   pile quand la précédente finit.

---

## 2.5 - Quand le glouton est optimal

Formellement, les problèmes où le glouton donne toujours l'optimum
sont exactement ceux dont les solutions faisables forment un
**matroïde** - une structure abstraite d'indépendance. On n'a pas
besoin de la théorie complète, mais l'intuition est utile : si
« ajouter le meilleur élément restant qui préserve la faisabilité »
donne l'optimum quel que soit le point de départ, c'est un signe de
structure matroïdale.

---

## 2.6 - Exercices

:::exercise{id="{{EX_PA_ACTIVITY}}"}
:::

:::exercise{id="{{EX_PA_ROPES}}"}
:::

:::exercise{id="{{EX_PA_JOBSEQ}}"}
:::
