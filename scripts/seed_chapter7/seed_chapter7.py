"""Seed Chapter 7 - Structures de donnees avancees.

Cree (ou met a jour) la section ``structures-avancees`` avec quatre
lecons :

  1. Union-Find (DSU)
  2. Arbres de segments (avec propagation paresseuse)
  3. Fenwick, sparse table & statistiques d'ordre
  4. Trie (arbre de prefixes)

Chaque lecon contient trois exercices inline gradues (standard,
twist, dur). Idempotent.

Pre-deploiement le script verifie que chaque solution de reference
passe sur ses test cases (--validate-only pour ne faire QUE ca).

Usage:
    python scripts/seed_chapter7/seed_chapter7.py
    python scripts/seed_chapter7/seed_chapter7.py --draft
    python scripts/seed_chapter7/seed_chapter7.py --validate-only
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent.parent
CONTENT_DIR = HERE / "content"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


SECTION = {
    "slug": "structures-avancees",
    "title_fr": "Structures de donnees avancees",
    "title_en": "Advanced Data Structures",
    "description_fr": (
        "Les structures qui rendent efficaces les requetes dynamiques : "
        "Union-Find et son analyse en alpha(n), arbres de segments avec "
        "propagation paresseuse, arbres de Fenwick, sparse tables pour le "
        "RMQ statique et statistiques d'ordre, et le trie pour les "
        "prefixes et les astuces XOR binaires."
    ),
    "description_en": (
        "The structures that make dynamic queries efficient: Union-Find "
        "and its alpha(n) analysis, segment trees with lazy propagation, "
        "Fenwick trees, sparse tables for static RMQ and order statistics, "
        "and the trie for prefixes and binary XOR tricks."
    ),
    "order_idx": 6,
}


LESSONS: list[dict] = [
    # =================================================================
    # Lesson 1 - Union-Find
    # =================================================================
    {
        "slug": "union-find",
        "title_fr": "Union-Find (DSU)",
        "title_en": "Union-Find (DSU)",
        "order_idx": 0,
        "content_fr_file": "lesson_01_union_find.fr.md",
        "content_en_file": "lesson_01_union_find.en.md",
        "exercises": [
            {
                "key": "EX_DS_DSU_QUERY",
                "title_fr": "Connectivite dynamique",
                "title_en": "Dynamic connectivity",
                "prompt_fr": (
                    "Gerer $q$ operations sur $n$ elements initialement "
                    "isoles : **union** de deux elements, ou **requete** "
                    "de connexite.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ et $q$ ($1 \\le n, q \\le 2 \\cdot "
                    "10^5$)\n"
                    "- $q$ lignes : `t u v` avec $t = 0$ (unir $u$ et $v$) "
                    "ou $t = 1$ (sont-ils dans le meme ensemble ?), "
                    "sommets 1-indexes\n\n"
                    "**Sortie** : pour chaque requete ($t = 1$), `1` si "
                    "connectes, `0` sinon (une par ligne).\n\n"
                    "**Indice** : Union-Find avec **compression de chemin** "
                    "et **union par taille/rang**. Deux elements sont "
                    "connectes ssi ils ont la meme racine."
                ),
                "prompt_en": (
                    "Handle $q$ operations on $n$ initially isolated "
                    "elements: **union** of two elements, or connectivity "
                    "**query**.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $q$ ($1 \\le n, q \\le 2 \\cdot "
                    "10^5$)\n"
                    "- $q$ lines: `t u v` with $t = 0$ (union $u$ and $v$) "
                    "or $t = 1$ (are they in the same set?), 1-indexed "
                    "vertices\n\n"
                    "**Output**: for each query ($t = 1$), `1` if "
                    "connected, `0` otherwise (one per line).\n\n"
                    "**Hint**: Union-Find with **path compression** and "
                    "**union by size/rank**. Two elements are connected iff "
                    "they share the same root."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.buffer.read().split()\n"
                    "    n = int(data[0]); q = int(data[1]); idx = 2\n"
                    "    par = list(range(n))\n"
                    "    # TODO: find with path compression, union by size.\n"
                    "    out = []\n"
                    "    for _ in range(q):\n"
                    "        t = int(data[idx]); u = int(data[idx+1])-1; v = int(data[idx+2])-1; idx += 3\n"
                    "        # ...\n"
                    "    sys.stdout.write('\\n'.join(out) + ('\\n' if out else ''))\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5 6\n0 1 2\n0 2 3\n1 1 3\n1 1 4\n0 4 5\n1 4 5\n", "expected": "1\n0\n1\n", "is_sample": True},
                    {"input": "2 2\n1 1 2\n0 1 2\n", "expected": "0\n", "is_sample": True},
                    {"input": "4 3\n1 1 1\n0 1 4\n1 4 1\n", "expected": "1\n1\n", "is_sample": False},
                    {"input": "6 5\n0 1 2\n0 3 4\n0 5 6\n1 2 3\n1 5 6\n", "expected": "0\n1\n", "is_sample": False},
                    {"input": "3 4\n0 1 2\n1 1 2\n1 2 3\n0 2 3\n", "expected": "1\n0\n", "is_sample": False},
                    {"input": "1 1\n1 1 1\n", "expected": "1\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_DS_DSU_MAXSIZE",
                "title_fr": "Taille de la plus grande composante",
                "title_en": "Largest component size",
                "prompt_fr": (
                    "Apres avoir applique $q$ unions sur $n$ elements, "
                    "donner la **taille de la plus grande composante**.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ et $q$ ($1 \\le n \\le 2 \\cdot 10^5$, "
                    "$0 \\le q \\le 2 \\cdot 10^5$)\n"
                    "- $q$ lignes : `u v` (unir $u$ et $v$, 1-indexes)\n\n"
                    "**Sortie** : un seul entier.\n\n"
                    "**Indice** : maintenir un tableau `size[racine]` mis a "
                    "jour a chaque union par taille. La reponse est le "
                    "maximum de ces tailles."
                ),
                "prompt_en": (
                    "After applying $q$ unions on $n$ elements, report the "
                    "**size of the largest component**.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $q$ ($1 \\le n \\le 2 \\cdot 10^5$, "
                    "$0 \\le q \\le 2 \\cdot 10^5$)\n"
                    "- $q$ lines: `u v` (union $u$ and $v$, 1-indexed)\n\n"
                    "**Output**: one integer.\n\n"
                    "**Hint**: maintain a `size[root]` array updated at each "
                    "union by size. The answer is the maximum of those "
                    "sizes."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.buffer.read().split()\n"
                    "    n = int(data[0]); q = int(data[1]); idx = 2\n"
                    "    # TODO: DSU by size, track max size.\n"
                    "    print(1)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5 3\n1 2\n2 3\n4 5\n", "expected": "3\n", "is_sample": True},
                    {"input": "4 0\n", "expected": "1\n", "is_sample": True},
                    {"input": "6 3\n1 2\n3 4\n5 6\n", "expected": "2\n", "is_sample": False},
                    {"input": "5 4\n1 2\n2 3\n3 4\n4 5\n", "expected": "5\n", "is_sample": False},
                    {"input": "3 2\n1 1\n2 2\n", "expected": "1\n", "is_sample": False},
                    {"input": "1 0\n", "expected": "1\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_DS_DSU_PARITY",
                "title_fr": "Union-Find avec parite",
                "title_en": "Union-Find with parity",
                "prompt_fr": (
                    "On recoit $q$ contraintes entre $n$ elements : `t u v` "
                    "avec $t = 0$ (« $u$ et $v$ dans le **meme** groupe ») "
                    "ou $t = 1$ (« dans des groupes **differents** »). Une "
                    "contrainte est **contradictoire** si elle est "
                    "incompatible avec les contraintes deja acceptees ; on "
                    "l'ignore alors. Compter les contraintes "
                    "contradictoires.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ et $q$ ($1 \\le n, q \\le 2 \\cdot "
                    "10^5$)\n"
                    "- $q$ lignes : `t u v` (1-indexes)\n\n"
                    "**Sortie** : un seul entier - le nombre de contraintes "
                    "contradictoires.\n\n"
                    "**Indice** : Union-Find **avec parite** - stocker, pour "
                    "chaque element, sa parite (0/1) relative a sa racine. "
                    "L'union fusionne deux arbres en ajustant la parite ; "
                    "une contrainte dont les deux elements ont deja une "
                    "racine commune est verifiee directement."
                ),
                "prompt_en": (
                    "You receive $q$ constraints among $n$ elements: `t u v` "
                    "with $t = 0$ (\"$u$ and $v$ in the **same** group\") or "
                    "$t = 1$ (\"in **different** groups\"). A constraint is "
                    "**contradictory** if it is incompatible with the "
                    "already-accepted constraints; it is then ignored. Count "
                    "the contradictory constraints.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $q$ ($1 \\le n, q \\le 2 \\cdot "
                    "10^5$)\n"
                    "- $q$ lines: `t u v` (1-indexed)\n\n"
                    "**Output**: one integer - the number of contradictory "
                    "constraints.\n\n"
                    "**Hint**: Union-Find **with parity** - store, for each "
                    "element, its parity (0/1) relative to its root. Union "
                    "merges two trees while adjusting the parity; a "
                    "constraint whose two elements already share a root is "
                    "checked directly."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.buffer.read().split()\n"
                    "    n = int(data[0]); q = int(data[1]); idx = 2\n"
                    "    # TODO: parity DSU; count contradictions.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "4 4\n1 1 2\n1 2 3\n1 3 4\n0 1 4\n", "expected": "1\n", "is_sample": True},
                    {"input": "3 3\n1 1 2\n1 2 3\n1 1 3\n", "expected": "1\n", "is_sample": True},
                    {"input": "2 2\n0 1 2\n1 1 2\n", "expected": "1\n", "is_sample": False},
                    {"input": "5 5\n1 1 2\n1 2 3\n0 1 3\n1 3 4\n0 2 4\n", "expected": "0\n", "is_sample": False},
                    {"input": "4 3\n0 1 2\n0 2 3\n0 1 3\n", "expected": "0\n", "is_sample": False},
                    {"input": "1 1\n1 1 1\n", "expected": "1\n", "is_sample": False},
                ],
            },
        ],
    },

    # =================================================================
    # Lesson 2 - Arbres de segments
    # =================================================================
    {
        "slug": "segment-trees",
        "title_fr": "Arbres de segments",
        "title_en": "Segment Trees",
        "order_idx": 1,
        "content_fr_file": "lesson_02_segment_trees.fr.md",
        "content_en_file": "lesson_02_segment_trees.en.md",
        "exercises": [
            {
                "key": "EX_DS_SEG_SUM",
                "title_fr": "Somme de plage, mise a jour ponctuelle",
                "title_en": "Range sum, point update",
                "prompt_fr": (
                    "Maintenir un tableau sous **mise a jour ponctuelle** et "
                    "**somme de plage**.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ et $q$ ($1 \\le n, q \\le 2 \\cdot "
                    "10^5$)\n"
                    "- ligne 2 : $n$ entiers ($|a_i| \\le 10^9$)\n"
                    "- $q$ lignes : `0 i x` (poser $a_i = x$) ou `1 l r` "
                    "(somme de $a_l$ a $a_r$), indices 1-indexes "
                    "inclusifs\n\n"
                    "**Sortie** : une ligne par requete `1`.\n\n"
                    "**Indice** : arbre de segments. Chaque noeud couvre un "
                    "intervalle ; une mise a jour ou une requete ne touche "
                    "que $O(\\log n)$ noeuds."
                ),
                "prompt_en": (
                    "Maintain an array under **point update** and **range "
                    "sum**.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $q$ ($1 \\le n, q \\le 2 \\cdot "
                    "10^5$)\n"
                    "- line 2: $n$ integers ($|a_i| \\le 10^9$)\n"
                    "- $q$ lines: `0 i x` (set $a_i = x$) or `1 l r` (sum "
                    "from $a_l$ to $a_r$), 1-indexed inclusive\n\n"
                    "**Output**: one line per `1` query.\n\n"
                    "**Hint**: segment tree. Each node covers an interval; "
                    "an update or query touches only $O(\\log n)$ nodes."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.buffer.read().split()\n"
                    "    n = int(data[0]); q = int(data[1]); idx = 2\n"
                    "    a = list(map(int, data[idx:idx+n])); idx += n\n"
                    "    # TODO: segment tree, point update + range sum.\n"
                    "    print()\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5 4\n1 2 3 4 5\n1 1 5\n0 3 10\n1 1 3\n1 3 3\n", "expected": "15\n13\n10\n", "is_sample": True},
                    {"input": "3 2\n5 5 5\n1 1 1\n1 1 3\n", "expected": "5\n15\n", "is_sample": True},
                    {"input": "1 2\n7\n1 1 1\n0 1 3\n", "expected": "7\n", "is_sample": False},
                    {"input": "6 3\n1 2 3 4 5 6\n1 2 5\n0 1 0\n1 1 6\n", "expected": "14\n20\n", "is_sample": False},
                    {"input": "4 2\n-1 -2 -3 -4\n1 1 4\n1 2 3\n", "expected": "-10\n-5\n", "is_sample": False},
                    {"input": "5 1\n10 20 30 40 50\n1 3 5\n", "expected": "120\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_DS_SEG_RMQ",
                "title_fr": "Minimum de plage, mise a jour ponctuelle",
                "title_en": "Range minimum, point update",
                "prompt_fr": (
                    "Meme cadre, mais la requete demande le **minimum** de "
                    "la plage.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ et $q$ ($1 \\le n, q \\le 2 \\cdot "
                    "10^5$)\n"
                    "- ligne 2 : $n$ entiers ($|a_i| \\le 10^9$)\n"
                    "- $q$ lignes : `0 i x` (poser $a_i = x$) ou `1 l r` "
                    "(minimum de $a_l$ a $a_r$)\n\n"
                    "**Sortie** : une ligne par requete `1`.\n\n"
                    "**Indice** : identique a la somme, en remplacant "
                    "l'operation de fusion `+` par `min`. C'est la force de "
                    "l'arbre de segments : n'importe quelle operation "
                    "**associative** fonctionne."
                ),
                "prompt_en": (
                    "Same setting, but the query asks for the **minimum** "
                    "over the range.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $q$ ($1 \\le n, q \\le 2 \\cdot "
                    "10^5$)\n"
                    "- line 2: $n$ integers ($|a_i| \\le 10^9$)\n"
                    "- $q$ lines: `0 i x` (set $a_i = x$) or `1 l r` "
                    "(minimum from $a_l$ to $a_r$)\n\n"
                    "**Output**: one line per `1` query.\n\n"
                    "**Hint**: identical to the sum version, replacing the "
                    "merge operation `+` with `min`. That is the power of "
                    "the segment tree: any **associative** operation works."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.buffer.read().split()\n"
                    "    n = int(data[0]); q = int(data[1]); idx = 2\n"
                    "    a = list(map(int, data[idx:idx+n])); idx += n\n"
                    "    # TODO: segment tree with min merge.\n"
                    "    print()\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5 4\n5 3 8 1 9\n1 1 5\n0 4 10\n1 3 5\n1 1 2\n", "expected": "1\n8\n3\n", "is_sample": True},
                    {"input": "3 2\n7 7 7\n1 1 3\n0 2 1\n", "expected": "7\n", "is_sample": True},
                    {"input": "1 1\n42\n1 1 1\n", "expected": "42\n", "is_sample": False},
                    {"input": "6 3\n6 5 4 3 2 1\n1 1 6\n0 6 0\n1 4 6\n", "expected": "1\n0\n", "is_sample": False},
                    {"input": "4 2\n-1 -2 -3 -4\n1 1 4\n1 1 1\n", "expected": "-4\n-1\n", "is_sample": False},
                    {"input": "5 2\n3 1 4 1 5\n1 2 4\n1 4 5\n", "expected": "1\n1\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_DS_SEG_LAZY",
                "title_fr": "Ajout de plage, somme de plage (lazy)",
                "title_en": "Range add, range sum (lazy)",
                "prompt_fr": (
                    "Maintenant les **mises a jour** portent sur une plage : "
                    "ajouter une valeur a **tous** les elements d'un "
                    "intervalle, puis interroger la somme d'un "
                    "intervalle.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ et $q$ ($1 \\le n, q \\le 2 \\cdot "
                    "10^5$)\n"
                    "- ligne 2 : $n$ entiers ($|a_i| \\le 10^9$)\n"
                    "- $q$ lignes : `0 l r x` (ajouter $x$ a $a_l..a_r$) ou "
                    "`1 l r` (somme de $a_l..a_r$)\n\n"
                    "**Sortie** : une ligne par requete `1`.\n\n"
                    "**Indice** : arbre de segments avec **propagation "
                    "paresseuse** (lazy). Un ajout de plage se marque sur "
                    "$O(\\log n)$ noeuds ; la marque `lazy` est repercutee "
                    "aux enfants uniquement quand on les visite."
                ),
                "prompt_en": (
                    "Now the **updates** span a range: add a value to "
                    "**all** elements of an interval, then query the sum of "
                    "an interval.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $q$ ($1 \\le n, q \\le 2 \\cdot "
                    "10^5$)\n"
                    "- line 2: $n$ integers ($|a_i| \\le 10^9$)\n"
                    "- $q$ lines: `0 l r x` (add $x$ to $a_l..a_r$) or "
                    "`1 l r` (sum of $a_l..a_r$)\n\n"
                    "**Output**: one line per `1` query.\n\n"
                    "**Hint**: segment tree with **lazy propagation**. A "
                    "range add marks $O(\\log n)$ nodes; the `lazy` mark is "
                    "pushed to children only when they are visited."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    sys.setrecursionlimit(300000)\n"
                    "    data = sys.stdin.buffer.read().split()\n"
                    "    n = int(data[0]); q = int(data[1]); idx = 2\n"
                    "    a = list(map(int, data[idx:idx+n])); idx += n\n"
                    "    # TODO: lazy segment tree, range add + range sum.\n"
                    "    print()\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5 4\n1 2 3 4 5\n1 1 5\n0 2 4 10\n1 1 5\n1 2 4\n", "expected": "15\n45\n39\n", "is_sample": True},
                    {"input": "3 3\n0 0 0\n0 1 3 5\n1 1 3\n1 2 2\n", "expected": "15\n5\n", "is_sample": True},
                    {"input": "1 2\n7\n0 1 1 3\n1 1 1\n", "expected": "10\n", "is_sample": False},
                    {"input": "6 3\n1 1 1 1 1 1\n0 1 6 2\n0 3 4 1\n1 1 6\n", "expected": "20\n", "is_sample": False},
                    {"input": "4 2\n-5 -5 -5 -5\n0 1 4 5\n1 1 4\n", "expected": "0\n", "is_sample": False},
                    {"input": "5 3\n1 2 3 4 5\n0 1 3 100\n1 1 3\n1 4 5\n", "expected": "306\n9\n", "is_sample": False},
                ],
            },
        ],
    },

    # =================================================================
    # Lesson 3 - Fenwick, sparse table, statistiques d'ordre
    # =================================================================
    {
        "slug": "fenwick-rmq",
        "title_fr": "Fenwick, sparse table & statistiques d'ordre",
        "title_en": "Fenwick, Sparse Table & Order Statistics",
        "order_idx": 2,
        "content_fr_file": "lesson_03_fenwick_rmq.fr.md",
        "content_en_file": "lesson_03_fenwick_rmq.en.md",
        "exercises": [
            {
                "key": "EX_DS_FENWICK",
                "title_fr": "Arbre de Fenwick",
                "title_en": "Fenwick tree",
                "prompt_fr": (
                    "Maintenir un tableau sous **ajout ponctuel** et "
                    "**somme de plage**, avec un arbre de Fenwick (BIT).\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ et $q$ ($1 \\le n, q \\le 2 \\cdot "
                    "10^5$)\n"
                    "- ligne 2 : $n$ entiers ($|a_i| \\le 10^9$)\n"
                    "- $q$ lignes : `0 i x` (ajouter $x$ a $a_i$) ou "
                    "`1 l r` (somme de $a_l..a_r$), 1-indexes\n\n"
                    "**Sortie** : une ligne par requete `1`.\n\n"
                    "**Indice** : un BIT represente les sommes prefixes par "
                    "des blocs alignes sur les bits de poids faible. `i += "
                    "i & -i` monte, `i -= i & -i` descend. La somme de plage "
                    "est `pre(r) - pre(l-1)`."
                ),
                "prompt_en": (
                    "Maintain an array under **point add** and **range "
                    "sum**, using a Fenwick tree (BIT).\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $q$ ($1 \\le n, q \\le 2 \\cdot "
                    "10^5$)\n"
                    "- line 2: $n$ integers ($|a_i| \\le 10^9$)\n"
                    "- $q$ lines: `0 i x` (add $x$ to $a_i$) or `1 l r` "
                    "(sum of $a_l..a_r$), 1-indexed\n\n"
                    "**Output**: one line per `1` query.\n\n"
                    "**Hint**: a BIT represents prefix sums via blocks "
                    "aligned on the low bits. `i += i & -i` goes up, `i -= "
                    "i & -i` goes down. The range sum is `pre(r) - "
                    "pre(l-1)`."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.buffer.read().split()\n"
                    "    n = int(data[0]); q = int(data[1]); idx = 2\n"
                    "    a = list(map(int, data[idx:idx+n])); idx += n\n"
                    "    # TODO: Fenwick tree.\n"
                    "    print()\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5 4\n1 2 3 4 5\n1 1 5\n0 3 10\n1 1 3\n1 3 3\n", "expected": "15\n16\n13\n", "is_sample": True},
                    {"input": "3 2\n5 5 5\n0 2 5\n1 1 3\n", "expected": "20\n", "is_sample": True},
                    {"input": "1 2\n7\n1 1 1\n0 1 3\n", "expected": "7\n", "is_sample": False},
                    {"input": "6 3\n1 2 3 4 5 6\n1 2 5\n0 1 100\n1 1 6\n", "expected": "14\n121\n", "is_sample": False},
                    {"input": "4 2\n-1 -2 -3 -4\n1 1 4\n0 2 2\n", "expected": "-10\n", "is_sample": False},
                    {"input": "5 1\n10 20 30 40 50\n1 3 5\n", "expected": "120\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_DS_SPARSE_RMQ",
                "title_fr": "Sparse table (RMQ statique)",
                "title_en": "Sparse table (static RMQ)",
                "prompt_fr": (
                    "Tableau **statique** (jamais modifie). Repondre a $q$ "
                    "requetes de **minimum de plage** en $O(1)$ chacune "
                    "apres pretraitement.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ et $q$ ($1 \\le n, q \\le 2 \\cdot "
                    "10^5$)\n"
                    "- ligne 2 : $n$ entiers ($|a_i| \\le 10^9$)\n"
                    "- $q$ lignes : `l r` (minimum de $a_l..a_r$, "
                    "1-indexes)\n\n"
                    "**Sortie** : une ligne par requete.\n\n"
                    "**Indice** : la **sparse table** precalcule le minimum "
                    "de chaque plage de longueur $2^k$ en $O(n \\log n)$. "
                    "Une requete $[l, r]$ se couvre par **deux** plages "
                    "chevauchantes de longueur $2^{\\lfloor \\log_2(r-l+1) "
                    "\\rfloor}$ - le chevauchement est sans effet pour le "
                    "min (operation idempotente)."
                ),
                "prompt_en": (
                    "**Static** array (never modified). Answer $q$ **range "
                    "minimum** queries in $O(1)$ each after "
                    "preprocessing.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $q$ ($1 \\le n, q \\le 2 \\cdot "
                    "10^5$)\n"
                    "- line 2: $n$ integers ($|a_i| \\le 10^9$)\n"
                    "- $q$ lines: `l r` (minimum of $a_l..a_r$, "
                    "1-indexed)\n\n"
                    "**Output**: one line per query.\n\n"
                    "**Hint**: the **sparse table** precomputes the minimum "
                    "of each length-$2^k$ range in $O(n \\log n)$. A query "
                    "$[l, r]$ is covered by **two** overlapping ranges of "
                    "length $2^{\\lfloor \\log_2(r-l+1) \\rfloor}$ - the "
                    "overlap is harmless for min (idempotent operation)."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.buffer.read().split()\n"
                    "    n = int(data[0]); q = int(data[1]); idx = 2\n"
                    "    a = list(map(int, data[idx:idx+n])); idx += n\n"
                    "    # TODO: build sparse table, answer queries.\n"
                    "    print()\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5 3\n5 3 8 1 9\n1 5\n2 4\n3 3\n", "expected": "1\n1\n8\n", "is_sample": True},
                    {"input": "3 2\n7 2 5\n1 3\n2 2\n", "expected": "2\n2\n", "is_sample": True},
                    {"input": "1 1\n42\n1 1\n", "expected": "42\n", "is_sample": False},
                    {"input": "6 3\n6 5 4 3 2 1\n1 6\n1 3\n4 6\n", "expected": "1\n4\n1\n", "is_sample": False},
                    {"input": "4 2\n-1 -2 -3 -4\n1 4\n2 3\n", "expected": "-4\n-3\n", "is_sample": False},
                    {"input": "8 2\n3 1 4 1 5 9 2 6\n2 6\n5 8\n", "expected": "1\n2\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_DS_ORDERSTAT",
                "title_fr": "Statistiques d'ordre (k-ieme plus petit)",
                "title_en": "Order statistics (k-th smallest)",
                "prompt_fr": (
                    "Gerer un **multi-ensemble** sous insertions, "
                    "suppressions et requetes du **$k$-ieme plus petit** "
                    "element.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $q$ ($1 \\le q \\le 2 \\cdot 10^5$)\n"
                    "- $q$ lignes : `1 x` (inserer $x$), `2 x` (supprimer "
                    "une occurrence de $x$, presente), ou `3 k` (afficher "
                    "le $k$-ieme plus petit), avec $1 \\le x \\le 10^6$\n\n"
                    "**Sortie** : pour chaque requete `3`, le $k$-ieme plus "
                    "petit, ou $-1$ si le multi-ensemble en contient moins "
                    "de $k$.\n\n"
                    "**Indice** : un arbre de Fenwick indexe **par valeur** "
                    "compte les occurrences. Le $k$-ieme se trouve par "
                    "**descente binaire** sur le BIT en $O(\\log V)$ : "
                    "chercher le plus petit prefixe de somme $\\ge k$."
                ),
                "prompt_en": (
                    "Handle a **multiset** under insertions, deletions, and "
                    "**$k$-th smallest** queries.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $q$ ($1 \\le q \\le 2 \\cdot 10^5$)\n"
                    "- $q$ lines: `1 x` (insert $x$), `2 x` (delete one "
                    "occurrence of $x$, guaranteed present), or `3 k` "
                    "(print the $k$-th smallest), with $1 \\le x \\le "
                    "10^6$\n\n"
                    "**Output**: for each `3` query, the $k$-th smallest, or "
                    "$-1$ if the multiset holds fewer than $k$ "
                    "elements.\n\n"
                    "**Hint**: a Fenwick tree indexed **by value** counts "
                    "occurrences. The $k$-th is found by **binary descent** "
                    "on the BIT in $O(\\log V)$: seek the smallest prefix "
                    "with sum $\\ge k$."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.buffer.read().split()\n"
                    "    q = int(data[0]); idx = 1\n"
                    "    # TODO: Fenwick over values + binary-descent kth.\n"
                    "    print()\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "6\n1 5\n1 3\n1 8\n3 2\n2 3\n3 2\n", "expected": "5\n8\n", "is_sample": True},
                    {"input": "3\n1 10\n3 1\n3 2\n", "expected": "10\n-1\n", "is_sample": True},
                    {"input": "4\n3 1\n1 7\n3 1\n3 2\n", "expected": "-1\n7\n-1\n", "is_sample": False},
                    {"input": "7\n1 4\n1 4\n1 2\n3 1\n3 2\n3 3\n3 4\n", "expected": "2\n4\n4\n-1\n", "is_sample": False},
                    {"input": "5\n1 100\n1 50\n2 100\n3 1\n3 2\n", "expected": "50\n-1\n", "is_sample": False},
                    {"input": "2\n1 1\n3 1\n", "expected": "1\n", "is_sample": False},
                ],
            },
        ],
    },

    # =================================================================
    # Lesson 4 - Trie
    # =================================================================
    {
        "slug": "trie",
        "title_fr": "Trie (arbre de prefixes)",
        "title_en": "Trie (Prefix Tree)",
        "order_idx": 3,
        "content_fr_file": "lesson_04_trie.fr.md",
        "content_en_file": "lesson_04_trie.en.md",
        "exercises": [
            {
                "key": "EX_DS_TRIE_PREFIX",
                "title_fr": "Comptage par prefixe",
                "title_en": "Prefix count",
                "prompt_fr": (
                    "Gerer un ensemble de mots sous insertions et requetes "
                    "« combien de mots inseres commencent par ce prefixe ? "
                    "».\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $q$ ($1 \\le q \\le 2 \\cdot 10^5$)\n"
                    "- $q$ lignes : `1 mot` (inserer) ou `2 prefixe` "
                    "(compter), en lettres minuscules `a`-`z` ; longueur "
                    "totale $\\le 10^6$\n\n"
                    "**Sortie** : une ligne par requete `2`.\n\n"
                    "**Indice** : un **trie** stocke un compteur sur chaque "
                    "noeud, incremente a chaque mot qui le traverse. Le "
                    "compteur au bout du prefixe est la reponse."
                ),
                "prompt_en": (
                    "Handle a set of words under insertions and \"how many "
                    "inserted words start with this prefix?\" queries.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $q$ ($1 \\le q \\le 2 \\cdot 10^5$)\n"
                    "- $q$ lines: `1 word` (insert) or `2 prefix` (count), "
                    "in lowercase letters `a`-`z`; total length $\\le "
                    "10^6$\n\n"
                    "**Output**: one line per `2` query.\n\n"
                    "**Hint**: a **trie** stores a counter on each node, "
                    "incremented by every word passing through it. The "
                    "counter at the end of the prefix is the answer."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.buffer.read().split()\n"
                    "    q = int(data[0]); idx = 1\n"
                    "    # TODO: trie with subtree counters.\n"
                    "    print()\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "6\n1 apple\n1 app\n1 apply\n2 app\n2 appl\n2 banana\n", "expected": "3\n2\n0\n", "is_sample": True},
                    {"input": "3\n1 abc\n1 abd\n2 ab\n", "expected": "2\n", "is_sample": True},
                    {"input": "2\n1 hello\n2 world\n", "expected": "0\n", "is_sample": False},
                    {"input": "5\n1 aaa\n1 aa\n1 a\n2 a\n2 aaa\n", "expected": "3\n1\n", "is_sample": False},
                    {"input": "4\n1 cat\n1 car\n1 dog\n2 ca\n", "expected": "2\n", "is_sample": False},
                    {"input": "3\n2 x\n1 x\n2 x\n", "expected": "0\n1\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_DS_TRIE_XOR",
                "title_fr": "XOR maximal (trie binaire)",
                "title_en": "Maximum XOR (binary trie)",
                "prompt_fr": (
                    "Gerer un ensemble d'entiers. Pour chaque requete, "
                    "renvoyer le **XOR maximal** entre l'entier de la "
                    "requete et un entier deja insere.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $q$ ($1 \\le q \\le 2 \\cdot 10^5$)\n"
                    "- $q$ lignes : `1 x` (inserer $x$) ou `2 x` (afficher "
                    "$\\max_y (x \\oplus y)$ sur les $y$ inseres), avec "
                    "$0 \\le x \\le 10^9$\n\n"
                    "**Sortie** : une ligne par requete `2` (0 si aucun "
                    "entier n'a encore ete insere).\n\n"
                    "**Indice** : un **trie binaire** stocke les entiers "
                    "bit par bit, du plus significatif au moins. Pour "
                    "maximiser le XOR, a chaque bit on suit l'arete du bit "
                    "**oppose** si elle existe."
                ),
                "prompt_en": (
                    "Handle a set of integers. For each query, return the "
                    "**maximum XOR** between the query integer and an "
                    "already-inserted integer.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $q$ ($1 \\le q \\le 2 \\cdot 10^5$)\n"
                    "- $q$ lines: `1 x` (insert $x$) or `2 x` (print "
                    "$\\max_y (x \\oplus y)$ over inserted $y$), with "
                    "$0 \\le x \\le 10^9$\n\n"
                    "**Output**: one line per `2` query (0 if no integer "
                    "has been inserted yet).\n\n"
                    "**Hint**: a **binary trie** stores integers bit by "
                    "bit, most significant first. To maximize the XOR, at "
                    "each bit follow the edge of the **opposite** bit if it "
                    "exists."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.buffer.read().split()\n"
                    "    q = int(data[0]); idx = 1\n"
                    "    # TODO: binary trie, insert + max-xor query.\n"
                    "    print()\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "4\n1 3\n1 10\n2 5\n2 25\n", "expected": "15\n26\n", "is_sample": True},
                    {"input": "2\n1 0\n2 0\n", "expected": "0\n", "is_sample": True},
                    {"input": "3\n1 8\n1 4\n2 2\n", "expected": "10\n", "is_sample": False},
                    {"input": "5\n1 1\n1 2\n1 4\n1 8\n2 15\n", "expected": "14\n", "is_sample": False},
                    {"input": "4\n1 1000000000\n2 0\n1 5\n2 1000000000\n", "expected": "1000000000\n1000000005\n", "is_sample": False},
                    {"input": "3\n1 7\n1 7\n2 7\n", "expected": "0\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_DS_MAX_XOR_SUBARRAY",
                "title_fr": "XOR maximal d'un sous-tableau",
                "title_en": "Maximum XOR subarray",
                "prompt_fr": (
                    "Etant donne un tableau, trouver le **XOR maximal** "
                    "parmi tous les sous-tableaux contigus non vides.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ ($1 \\le n \\le 2 \\cdot 10^5$)\n"
                    "- ligne 2 : $n$ entiers ($0 \\le a_i \\le 10^9$)\n\n"
                    "**Sortie** : un seul entier - le XOR maximal.\n\n"
                    "**Indice** : soit $p_i = a_0 \\oplus \\dots \\oplus "
                    "a_{i-1}$ le XOR prefixe. Le XOR du sous-tableau "
                    "$[l, r)$ vaut $p_r \\oplus p_l$. On veut donc "
                    "maximiser $p_r \\oplus p_l$ : inserer chaque prefixe "
                    "dans un **trie binaire** et interroger le XOR maximal, "
                    "exactement comme l'exercice precedent."
                ),
                "prompt_en": (
                    "Given an array, find the **maximum XOR** over all "
                    "non-empty contiguous subarrays.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($1 \\le n \\le 2 \\cdot 10^5$)\n"
                    "- line 2: $n$ integers ($0 \\le a_i \\le 10^9$)\n\n"
                    "**Output**: one integer - the maximum XOR.\n\n"
                    "**Hint**: let $p_i = a_0 \\oplus \\dots \\oplus "
                    "a_{i-1}$ be the prefix XOR. The XOR of subarray "
                    "$[l, r)$ equals $p_r \\oplus p_l$. So maximize "
                    "$p_r \\oplus p_l$: insert each prefix into a **binary "
                    "trie** and query the maximum XOR, exactly like the "
                    "previous exercise."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.buffer.read().split()\n"
                    "    n = int(data[0])\n"
                    "    a = list(map(int, data[1:1+n]))\n"
                    "    # TODO: prefix XOR + binary trie.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "4\n1 2 3 4\n", "expected": "7\n", "is_sample": True},
                    {"input": "1\n5\n", "expected": "5\n", "is_sample": True},
                    {"input": "3\n8 1 2\n", "expected": "11\n", "is_sample": False},
                    {"input": "5\n1 2 3 4 5\n", "expected": "7\n", "is_sample": False},
                    {"input": "2\n0 0\n", "expected": "0\n", "is_sample": False},
                    {"input": "6\n4 6 7 2 5 1\n", "expected": "7\n", "is_sample": False},
                ],
            },
        ],
    },
]


REFERENCE_SOLUTIONS = {
    "EX_DS_DSU_QUERY": r"""import sys
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); q = int(data[1]); idx = 2
    par = list(range(n)); sz = [1]*n
    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    out = []
    for _ in range(q):
        t = int(data[idx]); u = int(data[idx+1])-1; v = int(data[idx+2])-1; idx += 3
        if t == 0:
            ru, rv = find(u), find(v)
            if ru != rv:
                if sz[ru] < sz[rv]: ru, rv = rv, ru
                par[rv] = ru; sz[ru] += sz[rv]
        else:
            out.append('1' if find(u) == find(v) else '0')
    sys.stdout.write('\n'.join(out) + ('\n' if out else ''))
main()
""",
    "EX_DS_DSU_MAXSIZE": r"""import sys
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); q = int(data[1]); idx = 2
    par = list(range(n)); sz = [1]*n
    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    best = 1
    for _ in range(q):
        u = int(data[idx])-1; v = int(data[idx+1])-1; idx += 2
        ru, rv = find(u), find(v)
        if ru != rv:
            if sz[ru] < sz[rv]: ru, rv = rv, ru
            par[rv] = ru; sz[ru] += sz[rv]
            if sz[ru] > best: best = sz[ru]
    print(best)
main()
""",
    "EX_DS_DSU_PARITY": r"""import sys
def main():
    sys.setrecursionlimit(400000)
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); q = int(data[1]); idx = 2
    par = list(range(n)); rel = [0]*n
    def find(x):
        if par[x] == x: return x, 0
        root, pr = find(par[x])
        par[x] = root; rel[x] ^= pr
        return root, rel[x]
    contra = 0
    for _ in range(q):
        t = int(data[idx]); u = int(data[idx+1])-1; v = int(data[idx+2])-1; idx += 3
        ru, pu = find(u); rv, pv = find(v)
        if ru == rv:
            if (pu ^ pv) != t: contra += 1
        else:
            par[ru] = rv; rel[ru] = pu ^ pv ^ t
    print(contra)
main()
""",
    "EX_DS_SEG_SUM": r"""import sys
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); q = int(data[1]); idx = 2
    a = list(map(int, data[idx:idx+n])); idx += n
    size = 1
    while size < n: size *= 2
    tree = [0]*(2*size)
    for i in range(n): tree[size+i] = a[i]
    for i in range(size-1, 0, -1): tree[i] = tree[2*i]+tree[2*i+1]
    def update(i, val):
        i += size; tree[i] = val; i //= 2
        while i: tree[i] = tree[2*i]+tree[2*i+1]; i //= 2
    def query(l, r):
        res = 0; l += size; r += size+1
        while l < r:
            if l & 1: res += tree[l]; l += 1
            if r & 1: r -= 1; res += tree[r]
            l //= 2; r //= 2
        return res
    out = []
    for _ in range(q):
        t = int(data[idx])
        if t == 0:
            i = int(data[idx+1])-1; x = int(data[idx+2]); idx += 3
            update(i, x)
        else:
            l = int(data[idx+1])-1; r = int(data[idx+2])-1; idx += 3
            out.append(str(query(l, r)))
    sys.stdout.write('\n'.join(out) + ('\n' if out else ''))
main()
""",
    "EX_DS_SEG_RMQ": r"""import sys
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); q = int(data[1]); idx = 2
    a = list(map(int, data[idx:idx+n])); idx += n
    INF = float('inf'); size = 1
    while size < n: size *= 2
    tree = [INF]*(2*size)
    for i in range(n): tree[size+i] = a[i]
    for i in range(size-1, 0, -1): tree[i] = min(tree[2*i], tree[2*i+1])
    def update(i, val):
        i += size; tree[i] = val; i //= 2
        while i: tree[i] = min(tree[2*i], tree[2*i+1]); i //= 2
    def query(l, r):
        res = INF; l += size; r += size+1
        while l < r:
            if l & 1:
                if tree[l] < res: res = tree[l]
                l += 1
            if r & 1:
                r -= 1
                if tree[r] < res: res = tree[r]
            l //= 2; r //= 2
        return res
    out = []
    for _ in range(q):
        t = int(data[idx])
        if t == 0:
            i = int(data[idx+1])-1; x = int(data[idx+2]); idx += 3
            update(i, x)
        else:
            l = int(data[idx+1])-1; r = int(data[idx+2])-1; idx += 3
            out.append(str(query(l, r)))
    sys.stdout.write('\n'.join(out) + ('\n' if out else ''))
main()
""",
    "EX_DS_SEG_LAZY": r"""import sys
def main():
    sys.setrecursionlimit(400000)
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); q = int(data[1]); idx = 2
    a = list(map(int, data[idx:idx+n])); idx += n
    tree = [0]*(4*n); lazy = [0]*(4*n)
    def build(node, l, r):
        if l == r: tree[node] = a[l]; return
        m = (l+r)//2
        build(2*node, l, m); build(2*node+1, m+1, r)
        tree[node] = tree[2*node]+tree[2*node+1]
    def push(node, l, r):
        if lazy[node]:
            m = (l+r)//2
            for ch, cl, cr in ((2*node, l, m), (2*node+1, m+1, r)):
                tree[ch] += lazy[node]*(cr-cl+1); lazy[ch] += lazy[node]
            lazy[node] = 0
    def add(node, l, r, ql, qr, val):
        if qr < l or r < ql: return
        if ql <= l and r <= qr:
            tree[node] += val*(r-l+1); lazy[node] += val; return
        push(node, l, r); m = (l+r)//2
        add(2*node, l, m, ql, qr, val); add(2*node+1, m+1, r, ql, qr, val)
        tree[node] = tree[2*node]+tree[2*node+1]
    def qsum(node, l, r, ql, qr):
        if qr < l or r < ql: return 0
        if ql <= l and r <= qr: return tree[node]
        push(node, l, r); m = (l+r)//2
        return qsum(2*node, l, m, ql, qr)+qsum(2*node+1, m+1, r, ql, qr)
    build(1, 0, n-1)
    out = []
    for _ in range(q):
        t = int(data[idx])
        if t == 0:
            l = int(data[idx+1])-1; r = int(data[idx+2])-1; x = int(data[idx+3]); idx += 4
            add(1, 0, n-1, l, r, x)
        else:
            l = int(data[idx+1])-1; r = int(data[idx+2])-1; idx += 3
            out.append(str(qsum(1, 0, n-1, l, r)))
    sys.stdout.write('\n'.join(out) + ('\n' if out else ''))
main()
""",
    "EX_DS_FENWICK": r"""import sys
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); q = int(data[1]); idx = 2
    a = list(map(int, data[idx:idx+n])); idx += n
    bit = [0]*(n+1)
    def upd(i, delta):
        i += 1
        while i <= n: bit[i] += delta; i += i & -i
    def pre(i):
        i += 1; s = 0
        while i > 0: s += bit[i]; i -= i & -i
        return s
    for i in range(n): upd(i, a[i])
    out = []
    for _ in range(q):
        t = int(data[idx])
        if t == 0:
            i = int(data[idx+1])-1; x = int(data[idx+2]); idx += 3
            upd(i, x)
        else:
            l = int(data[idx+1])-1; r = int(data[idx+2])-1; idx += 3
            out.append(str(pre(r) - (pre(l-1) if l > 0 else 0)))
    sys.stdout.write('\n'.join(out) + ('\n' if out else ''))
main()
""",
    "EX_DS_SPARSE_RMQ": r"""import sys
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); q = int(data[1]); idx = 2
    a = list(map(int, data[idx:idx+n])); idx += n
    sp = [a[:]]; k = 1
    while (1 << k) <= n:
        prev = sp[k-1]; cur = []
        half = 1 << (k-1)
        for i in range(n-(1 << k)+1):
            x = prev[i]; y = prev[i+half]
            cur.append(x if x < y else y)
        sp.append(cur); k += 1
    out = []
    for _ in range(q):
        l = int(data[idx])-1; r = int(data[idx+1])-1; idx += 2
        length = r-l+1; j = length.bit_length()-1
        x = sp[j][l]; y = sp[j][r-(1 << j)+1]
        out.append(str(x if x < y else y))
    sys.stdout.write('\n'.join(out) + ('\n' if out else ''))
main()
""",
    "EX_DS_ORDERSTAT": r"""import sys
def main():
    data = sys.stdin.buffer.read().split()
    q = int(data[0]); idx = 1
    MAXV = 1000000
    bit = [0]*(MAXV+1)
    def upd(i, d):
        while i <= MAXV: bit[i] += d; i += i & -i
    LOG = 1
    while (1 << LOG) <= MAXV: LOG += 1
    def kth(k):
        pos = 0; r = 1 << (LOG-1)
        while r > 0:
            if pos+r <= MAXV and bit[pos+r] < k:
                pos += r; k -= bit[pos]
            r >>= 1
        return pos+1
    total = 0; out = []
    for _ in range(q):
        t = int(data[idx]); val = int(data[idx+1]); idx += 2
        if t == 1: upd(val, 1); total += 1
        elif t == 2: upd(val, -1); total -= 1
        else:
            out.append(str(kth(val) if val <= total else -1))
    sys.stdout.write('\n'.join(out) + ('\n' if out else ''))
main()
""",
    "EX_DS_TRIE_PREFIX": r"""import sys
def main():
    data = sys.stdin.buffer.read().split()
    q = int(data[0]); idx = 1
    children = [dict()]; cnt = [0]
    out = []
    for _ in range(q):
        t = data[idx]; s = data[idx+1].decode(); idx += 2
        if t == b'1':
            cur = 0
            for ch in s:
                nxt = children[cur].get(ch)
                if nxt is None:
                    children.append(dict()); cnt.append(0)
                    nxt = len(children)-1; children[cur][ch] = nxt
                cur = nxt; cnt[cur] += 1
        else:
            cur = 0; ok = True
            for ch in s:
                nxt = children[cur].get(ch)
                if nxt is None: ok = False; break
                cur = nxt
            out.append(str(cnt[cur] if ok else 0))
    sys.stdout.write('\n'.join(out) + ('\n' if out else ''))
main()
""",
    "EX_DS_TRIE_XOR": r"""import sys
def main():
    data = sys.stdin.buffer.read().split()
    q = int(data[0]); idx = 1
    BITS = 30
    ch = [[-1, -1]]
    out = []
    for _ in range(q):
        t = int(data[idx]); x = int(data[idx+1]); idx += 2
        if t == 1:
            cur = 0
            for b in range(BITS, -1, -1):
                bit = (x >> b) & 1
                if ch[cur][bit] == -1:
                    ch.append([-1, -1]); ch[cur][bit] = len(ch)-1
                cur = ch[cur][bit]
        else:
            if ch[0][0] == -1 and ch[0][1] == -1:
                out.append('0'); continue
            cur = 0; res = 0
            for b in range(BITS, -1, -1):
                bit = (x >> b) & 1; want = 1-bit
                if ch[cur][want] != -1:
                    res |= (1 << b); cur = ch[cur][want]
                else:
                    cur = ch[cur][bit]
            out.append(str(res))
    sys.stdout.write('\n'.join(out) + ('\n' if out else ''))
main()
""",
    "EX_DS_MAX_XOR_SUBARRAY": r"""import sys
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0])
    a = list(map(int, data[1:1+n]))
    BITS = 30
    ch = [[-1, -1]]
    def insert(x):
        cur = 0
        for b in range(BITS, -1, -1):
            bit = (x >> b) & 1
            if ch[cur][bit] == -1:
                ch.append([-1, -1]); ch[cur][bit] = len(ch)-1
            cur = ch[cur][bit]
    def query(x):
        cur = 0; res = 0
        for b in range(BITS, -1, -1):
            bit = (x >> b) & 1; want = 1-bit
            if ch[cur][want] != -1:
                res |= (1 << b); cur = ch[cur][want]
            else:
                cur = ch[cur][bit]
        return res
    insert(0)
    pref = 0; best = 0
    for v in a:
        pref ^= v
        c = query(pref)
        if c > best: best = c
        insert(pref)
    print(best)
main()
""",
}


def _flatten_exercises():
    for lesson in LESSONS:
        for ex in lesson["exercises"]:
            yield ex


def _normalise(out: str) -> str:
    lines = [ln.rstrip() for ln in out.splitlines()]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def validate_reference_solutions() -> int:
    failures: list[str] = []
    for ex in _flatten_exercises():
        key = ex["key"]
        if key not in REFERENCE_SOLUTIONS:
            failures.append(f"{key}: no reference solution"); continue
        ref = REFERENCE_SOLUTIONS[key]
        for idx, tc in enumerate(ex["test_cases"]):
            with tempfile.NamedTemporaryFile(
                "w", suffix=".py", delete=False, encoding="utf-8",
            ) as f:
                f.write(ref)
                src_path = f.name
            try:
                proc = subprocess.run(
                    [sys.executable, src_path],
                    input=tc["input"], capture_output=True, text=True,
                    timeout=10,
                )
            finally:
                try: os.remove(src_path)
                except OSError: pass
            actual = _normalise(proc.stdout or "")
            expected = _normalise(tc["expected"] or "")
            if actual != expected:
                failures.append(
                    f"{key}#{idx}: stdin={tc['input']!r}\n"
                    f"  expected={expected!r}\n"
                    f"  actual  ={actual!r}\n"
                    f"  stderr  ={proc.stderr!r}"
                )
    if failures:
        print("VALIDATION FAILURES:")
        for f in failures: print(" -", f)
        return 1
    total = sum(len(ex["test_cases"]) for ex in _flatten_exercises())
    print(f"VALIDATION OK - {total} test cases across "
          f"{sum(1 for _ in _flatten_exercises())} exercises.")
    return 0


def _read_content(filename: str) -> str:
    p = CONTENT_DIR / filename
    if not p.exists():
        raise SystemExit(f"Missing content file: {p}")
    return p.read_text(encoding="utf-8")


def _replace_placeholders(content: str, placeholders: dict[str, int]) -> str:
    for key, exercise_id in placeholders.items():
        content = content.replace("{{" + key + "}}", str(exercise_id))
    return content


def _check_no_placeholders_left(content: str) -> None:
    if "{{EX_" in content:
        i = content.index("{{EX_")
        snippet = content[i: i + 30]
        raise SystemExit(f"Unresolved placeholder: {snippet!r}")


def upsert_section(db, models, *, publish: bool):
    existing = db.query(models.LearningSection).filter(
        models.LearningSection.slug == SECTION["slug"]
    ).first()
    if existing:
        existing.title_fr = SECTION["title_fr"]
        existing.title_en = SECTION["title_en"]
        existing.description_fr = SECTION["description_fr"]
        existing.description_en = SECTION["description_en"]
        existing.is_published = bool(publish or existing.is_published)
        db.flush()
        return existing
    section = models.LearningSection(
        slug=SECTION["slug"],
        title_fr=SECTION["title_fr"],
        title_en=SECTION["title_en"],
        description_fr=SECTION["description_fr"],
        description_en=SECTION["description_en"],
        order_idx=SECTION["order_idx"],
        is_published=publish,
    )
    db.add(section)
    db.flush()
    return section


def upsert_lesson(db, models, section, lesson_data: dict, *, publish: bool):
    existing = db.query(models.Lesson).filter(
        models.Lesson.section_id == section.id,
        models.Lesson.slug == lesson_data["slug"],
    ).first()
    if existing:
        existing.title_fr = lesson_data["title_fr"]
        existing.title_en = lesson_data["title_en"]
        existing.order_idx = lesson_data["order_idx"]
        existing.is_published = bool(publish or existing.is_published)
        db.flush()
        return existing, False
    lesson = models.Lesson(
        section_id=section.id,
        slug=lesson_data["slug"],
        title_fr=lesson_data["title_fr"],
        title_en=lesson_data["title_en"],
        order_idx=lesson_data["order_idx"],
        is_published=publish,
        content_fr="",
        content_en="",
        created_by=None,
    )
    db.add(lesson)
    db.flush()
    return lesson, True


def reset_exercises(db, models, lesson) -> None:
    db.query(models.LessonExercise).filter(
        models.LessonExercise.lesson_id == lesson.id
    ).delete(synchronize_session=False)
    db.flush()


def create_exercise(db, models, lesson, exercise_data: dict) -> int:
    ex = models.LessonExercise(
        lesson_id=lesson.id,
        title_fr=exercise_data["title_fr"],
        title_en=exercise_data["title_en"],
        prompt_fr=exercise_data["prompt_fr"],
        prompt_en=exercise_data["prompt_en"],
        language="py3",
        starter_code=exercise_data["starter_code"],
        test_cases=json.dumps(exercise_data["test_cases"]),
        time_limit_ms=2000,
    )
    db.add(ex)
    db.flush()
    return ex.id


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--draft", action="store_true",
                        help="Cree en brouillon (par defaut tout est publie).")
    parser.add_argument("--db", type=str, default=None)
    parser.add_argument("--validate-only", action="store_true",
                        help="Valide les test cases vs solutions de "
                             "reference et quitte sans toucher a la base.")
    parser.add_argument("--skip-validate", action="store_true",
                        help="Saute la validation pre-deploiement.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.validate_only:
        return validate_reference_solutions()

    if not args.skip_validate:
        rc = validate_reference_solutions()
        if rc != 0:
            print("Refus de seeder : la validation a echoue.")
            return rc

    if args.db:
        os.environ["DATABASE_URL"] = args.db

    from backend import models  # noqa
    from backend.database import SessionLocal  # noqa

    publish = not args.draft

    db = SessionLocal()
    try:
        section = upsert_section(db, models, publish=publish)
        print(f"  [ok] section {section.slug!r} (id={section.id})")

        for lesson_data in LESSONS:
            lesson, created = upsert_lesson(
                db, models, section, lesson_data, publish=publish,
            )
            verb = "created" if created else "updated"
            print(f"    [ok] lesson {lesson.slug!r} {verb} (id={lesson.id})")

            reset_exercises(db, models, lesson)
            placeholders: dict[str, int] = {}
            for ex in lesson_data["exercises"]:
                ex_id = create_exercise(db, models, lesson, ex)
                placeholders[ex["key"]] = ex_id
                print(
                    f"      - exercise {ex['key']:<22} "
                    f"id={ex_id} ({len(ex['test_cases'])} test cases)"
                )

            content_fr = _read_content(lesson_data["content_fr_file"])
            content_en = _read_content(lesson_data["content_en_file"])
            content_fr = _replace_placeholders(content_fr, placeholders)
            content_en = _replace_placeholders(content_en, placeholders)
            _check_no_placeholders_left(content_fr)
            _check_no_placeholders_left(content_en)
            lesson.content_fr = content_fr
            lesson.content_en = content_en
            db.flush()

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    state = "publiees" if publish else "en brouillon"
    print()
    print(f"Chapitre 7 - Structures de donnees avancees : OK ({state}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
