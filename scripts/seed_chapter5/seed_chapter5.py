"""Seed Chapter 5 - Paradigmes.

Cree (ou met a jour) la section ``paradigmes`` avec quatre lecons :

  1. Diviser pour regner
  2. Algorithmes gloutons & preuves
  3. Programmation dynamique
  4. Backtracking & branch and bound

Chaque lecon contient trois exercices inline gradues (standard,
twist, dur). Idempotent.

Pre-deploiement le script verifie que chaque solution de reference
passe sur ses test cases (--validate-only pour ne faire QUE ca, sans
toucher a la base).

Usage:
    python scripts/seed_chapter5/seed_chapter5.py
    python scripts/seed_chapter5/seed_chapter5.py --draft
    python scripts/seed_chapter5/seed_chapter5.py --validate-only
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
    "slug": "paradigmes",
    "title_fr": "Paradigmes algorithmiques",
    "title_en": "Algorithmic Paradigms",
    "description_fr": (
        "Les quatre grands schemas de conception : diviser pour regner "
        "(et son theoreme maitre), les algorithmes gloutons prouves par "
        "argument d'echange, la programmation dynamique (sous-structure "
        "optimale, memoisation vs bottom-up) et l'exploration exhaustive "
        "elaguee par backtracking et branch and bound."
    ),
    "description_en": (
        "The four master design schemas: divide and conquer (and its "
        "master theorem), greedy algorithms proven by exchange argument, "
        "dynamic programming (optimal substructure, memoization vs "
        "bottom-up) and pruned exhaustive search via backtracking and "
        "branch and bound."
    ),
    "order_idx": 4,
}


# --------------------------------------------------------------------- #
# Exercises                                                             #
# --------------------------------------------------------------------- #

LESSONS: list[dict] = [
    # =================================================================
    # Lesson 1 - Diviser pour regner
    # =================================================================
    {
        "slug": "diviser-pour-regner",
        "title_fr": "Diviser pour regner",
        "title_en": "Divide and Conquer",
        "order_idx": 0,
        "content_fr_file": "lesson_01_divide_conquer.fr.md",
        "content_en_file": "lesson_01_divide_conquer.en.md",
        "exercises": [
            {
                "key": "EX_PA_INVERSIONS",
                "title_fr": "Comptage d'inversions",
                "title_en": "Counting inversions",
                "prompt_fr": (
                    "Compter le nombre d'**inversions** d'un tableau $A$ : "
                    "les paires d'indices $(i, j)$ avec $i < j$ et "
                    "$A[i] > A[j]$.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ ($1 \\le n \\le 10^5$)\n"
                    "- ligne 2 : $n$ entiers ($|a_i| \\le 10^9$)\n\n"
                    "**Sortie** : un seul entier - le nombre d'inversions "
                    "(il peut atteindre $\\approx 5 \\cdot 10^9$, donc penser "
                    "aux entiers 64 bits dans les langages types).\n\n"
                    "**Indice** : adapter le tri fusion. Pendant la fusion, "
                    "quand on prend un element de la moitie droite avant "
                    "des elements restants a gauche, chacun de ces elements "
                    "gauches forme une inversion. $O(n \\log n)$."
                ),
                "prompt_en": (
                    "Count the number of **inversions** of an array $A$: the "
                    "index pairs $(i, j)$ with $i < j$ and $A[i] > A[j]$.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($1 \\le n \\le 10^5$)\n"
                    "- line 2: $n$ integers ($|a_i| \\le 10^9$)\n\n"
                    "**Output**: one integer - the number of inversions (it "
                    "can reach $\\approx 5 \\cdot 10^9$, so use 64-bit "
                    "integers in typed languages).\n\n"
                    "**Hint**: adapt merge sort. During the merge, when you "
                    "take an element from the right half ahead of remaining "
                    "left elements, each of those left elements forms an "
                    "inversion. $O(n \\log n)$."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0])\n"
                    "    a = list(map(int, data[1:1+n]))\n"
                    "    # TODO: count inversions via merge sort.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5\n2 3 8 6 1\n", "expected": "5\n", "is_sample": True},
                    {"input": "1\n5\n", "expected": "0\n", "is_sample": True},
                    {"input": "4\n1 2 3 4\n", "expected": "0\n", "is_sample": False},
                    {"input": "4\n4 3 2 1\n", "expected": "6\n", "is_sample": False},
                    {"input": "6\n5 5 5 5 5 5\n", "expected": "0\n", "is_sample": False},
                    {"input": "8\n-2 3 -2 0 3 1 -5 4\n", "expected": "10\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_PA_MAXSUB",
                "title_fr": "Sous-tableau de somme maximale",
                "title_en": "Maximum subarray sum",
                "prompt_fr": (
                    "Calculer la plus grande somme d'un sous-tableau "
                    "**contigu non vide** de $A$.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ ($1 \\le n \\le 10^5$)\n"
                    "- ligne 2 : $n$ entiers ($|a_i| \\le 10^4$)\n\n"
                    "**Sortie** : un seul entier - la somme maximale (peut "
                    "etre negative si tous les elements le sont).\n\n"
                    "**Indice** : diviser en deux. Le meilleur sous-tableau "
                    "est soit entierement a gauche, soit entierement a "
                    "droite, soit **a cheval** sur le milieu. Le cas a "
                    "cheval se calcule en $O(n)$ (meilleur suffixe gauche + "
                    "meilleur prefixe droit). Recurrence $T(n) = 2T(n/2) + "
                    "O(n) = O(n \\log n)$."
                ),
                "prompt_en": (
                    "Compute the largest sum of a **non-empty contiguous** "
                    "subarray of $A$.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($1 \\le n \\le 10^5$)\n"
                    "- line 2: $n$ integers ($|a_i| \\le 10^4$)\n\n"
                    "**Output**: one integer - the maximum sum (can be "
                    "negative if every element is).\n\n"
                    "**Hint**: split in two. The best subarray is either "
                    "fully on the left, fully on the right, or **straddles** "
                    "the midpoint. The straddling case is $O(n)$ (best left "
                    "suffix + best right prefix). Recurrence $T(n) = 2T(n/2) "
                    "+ O(n) = O(n \\log n)$."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0])\n"
                    "    a = list(map(int, data[1:1+n]))\n"
                    "    # TODO: divide and conquer maximum subarray.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "9\n-2 1 -3 4 -1 2 1 -5 4\n", "expected": "6\n", "is_sample": True},
                    {"input": "1\n-7\n", "expected": "-7\n", "is_sample": True},
                    {"input": "5\n1 2 3 4 5\n", "expected": "15\n", "is_sample": False},
                    {"input": "5\n-1 -2 -3 -4 -5\n", "expected": "-1\n", "is_sample": False},
                    {"input": "8\n-2 -3 4 -1 -2 1 5 -3\n", "expected": "7\n", "is_sample": False},
                    {"input": "3\n0 0 0\n", "expected": "0\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_PA_REVPAIRS",
                "title_fr": "Paires inversees fortes",
                "title_en": "Strong reverse pairs",
                "prompt_fr": (
                    "Compter les paires $(i, j)$ avec $i < j$ et "
                    "$A[i] > 2 \\cdot A[j]$.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ ($1 \\le n \\le 5 \\cdot 10^4$)\n"
                    "- ligne 2 : $n$ entiers ($|a_i| \\le 10^9$)\n\n"
                    "**Sortie** : un seul entier - le nombre de telles "
                    "paires.\n\n"
                    "**Indice** : comme le comptage d'inversions, mais le "
                    "comptage et la fusion se separent. Avant de fusionner "
                    "les deux moities **triees**, balayer avec un pointeur "
                    "glissant : pour chaque $x$ a gauche, avancer $j$ tant "
                    "que $x > 2 \\cdot \\text{droite}[j]$. $O(n \\log n)$."
                ),
                "prompt_en": (
                    "Count the pairs $(i, j)$ with $i < j$ and "
                    "$A[i] > 2 \\cdot A[j]$.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($1 \\le n \\le 5 \\cdot 10^4$)\n"
                    "- line 2: $n$ integers ($|a_i| \\le 10^9$)\n\n"
                    "**Output**: one integer - the number of such pairs.\n\n"
                    "**Hint**: like counting inversions, but counting and "
                    "merging are separated. Before merging the two "
                    "**sorted** halves, sweep with a moving pointer: for "
                    "each $x$ on the left, advance $j$ while "
                    "$x > 2 \\cdot \\text{right}[j]$. $O(n \\log n)$."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0])\n"
                    "    a = list(map(int, data[1:1+n]))\n"
                    "    # TODO: count pairs a[i] > 2*a[j] via merge sort.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5\n1 3 2 3 1\n", "expected": "2\n", "is_sample": True},
                    {"input": "4\n2 4 3 5\n", "expected": "0\n", "is_sample": True},
                    {"input": "4\n1 2 3 4\n", "expected": "0\n", "is_sample": False},
                    {"input": "5\n5 4 3 2 1\n", "expected": "4\n", "is_sample": False},
                    {"input": "6\n-5 -3 0 2 4 6\n", "expected": "1\n", "is_sample": False},
                    {"input": "7\n10 9 8 1 2 3 100\n", "expected": "9\n", "is_sample": False},
                ],
            },
        ],
    },

    # =================================================================
    # Lesson 2 - Algorithmes gloutons
    # =================================================================
    {
        "slug": "glouton",
        "title_fr": "Algorithmes gloutons & preuves",
        "title_en": "Greedy Algorithms & Proofs",
        "order_idx": 1,
        "content_fr_file": "lesson_02_greedy.fr.md",
        "content_en_file": "lesson_02_greedy.en.md",
        "exercises": [
            {
                "key": "EX_PA_ACTIVITY",
                "title_fr": "Selection d'activites",
                "title_en": "Activity selection",
                "prompt_fr": (
                    "On dispose de $n$ activites, chacune un intervalle "
                    "**semi-ouvert** $[s, e)$. Deux activites sont "
                    "compatibles si leurs intervalles ne se chevauchent "
                    "pas (une activite peut commencer exactement quand une "
                    "autre finit). Choisir le **plus grand nombre** "
                    "d'activites deux a deux compatibles.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ ($1 \\le n \\le 10^5$)\n"
                    "- $n$ lignes suivantes : deux entiers $s$ et $e$ "
                    "($0 \\le s < e \\le 10^9$)\n\n"
                    "**Sortie** : un seul entier.\n\n"
                    "**Indice** : trier par **date de fin croissante**, "
                    "puis prendre gloutonnement chaque activite compatible "
                    "avec la derniere retenue. Preuve par argument "
                    "d'echange : la fin la plus precoce laisse le maximum "
                    "de place au reste."
                ),
                "prompt_en": (
                    "You are given $n$ activities, each a **half-open** "
                    "interval $[s, e)$. Two activities are compatible if "
                    "their intervals do not overlap (one activity may start "
                    "exactly when another ends). Pick the **largest number** "
                    "of pairwise-compatible activities.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($1 \\le n \\le 10^5$)\n"
                    "- next $n$ lines: two integers $s$ and $e$ "
                    "($0 \\le s < e \\le 10^9$)\n\n"
                    "**Output**: one integer.\n\n"
                    "**Hint**: sort by **earliest finish time**, then "
                    "greedily take each activity compatible with the last "
                    "kept one. Exchange-argument proof: the earliest finish "
                    "leaves the most room for the rest."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0])\n"
                    "    iv = []\n"
                    "    for i in range(n):\n"
                    "        s = int(data[1+2*i]); e = int(data[2+2*i])\n"
                    "        iv.append((s, e))\n"
                    "    # TODO: sort by end, greedy select.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "3\n1 3\n2 4\n3 5\n", "expected": "2\n", "is_sample": True},
                    {"input": "1\n0 1000000000\n", "expected": "1\n", "is_sample": True},
                    {"input": "4\n1 2\n2 3\n3 4\n4 5\n", "expected": "4\n", "is_sample": False},
                    {"input": "5\n1 10\n2 3\n3 4\n4 5\n5 6\n", "expected": "4\n", "is_sample": False},
                    {"input": "3\n5 6\n5 6\n5 6\n", "expected": "1\n", "is_sample": False},
                    {"input": "6\n1 4\n3 5\n0 6\n5 7\n3 9\n5 9\n", "expected": "2\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_PA_ROPES",
                "title_fr": "Fusion de cordes a cout minimal",
                "title_en": "Minimum cost to connect ropes",
                "prompt_fr": (
                    "On a $n$ cordes de longueurs $a_1, \\dots, a_n$. "
                    "Fusionner deux cordes de longueurs $x$ et $y$ coute "
                    "$x + y$ et produit une corde de longueur $x + y$. "
                    "Fusionner **toutes** les cordes en une seule en "
                    "**minimisant le cout total**.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ ($1 \\le n \\le 10^5$)\n"
                    "- ligne 2 : $n$ entiers $a_i$ ($1 \\le a_i \\le 10^9$)\n\n"
                    "**Sortie** : un seul entier - le cout total minimal "
                    "(0 si $n = 1$). Il peut etre grand : entiers 64 bits.\n\n"
                    "**Indice** : c'est le codage de Huffman. Toujours "
                    "fusionner les **deux plus petites** cordes courantes ; "
                    "un tas-min donne $O(n \\log n)$."
                ),
                "prompt_en": (
                    "You have $n$ ropes of lengths $a_1, \\dots, a_n$. "
                    "Merging two ropes of lengths $x$ and $y$ costs $x + y$ "
                    "and yields a rope of length $x + y$. Merge **all** ropes "
                    "into one while **minimizing total cost**.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($1 \\le n \\le 10^5$)\n"
                    "- line 2: $n$ integers $a_i$ ($1 \\le a_i \\le 10^9$)\n\n"
                    "**Output**: one integer - the minimum total cost (0 if "
                    "$n = 1$). It can be large: use 64-bit integers.\n\n"
                    "**Hint**: this is Huffman coding. Always merge the "
                    "**two smallest** current ropes; a min-heap gives "
                    "$O(n \\log n)$."
                ),
                "starter_code": (
                    "import sys, heapq\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0])\n"
                    "    a = list(map(int, data[1:1+n]))\n"
                    "    # TODO: repeatedly merge two smallest with a heap.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "4\n1 2 3 4\n", "expected": "19\n", "is_sample": True},
                    {"input": "1\n42\n", "expected": "0\n", "is_sample": True},
                    {"input": "2\n5 5\n", "expected": "10\n", "is_sample": False},
                    {"input": "3\n1 2 3\n", "expected": "9\n", "is_sample": False},
                    {"input": "5\n4 3 2 6 1\n", "expected": "35\n", "is_sample": False},
                    {"input": "6\n1 1 1 1 1 1\n", "expected": "16\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_PA_JOBSEQ",
                "title_fr": "Ordonnancement avec deadlines",
                "title_en": "Job sequencing with deadlines",
                "prompt_fr": (
                    "$n$ taches ; la tache $i$ a une **echeance** $d_i$ et un "
                    "**profit** $p_i$. Chaque tache dure une unite de temps ; "
                    "un seul processeur execute une tache par creneau entier "
                    "$1, 2, 3, \\dots$ Une tache ne rapporte son profit que "
                    "si elle est terminee **au plus tard au creneau** $d_i$. "
                    "**Maximiser le profit total.**\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ ($1 \\le n \\le 10^5$)\n"
                    "- $n$ lignes suivantes : $d_i$ et $p_i$ "
                    "($1 \\le d_i \\le n$, $1 \\le p_i \\le 10^9$)\n\n"
                    "**Sortie** : un seul entier - le profit maximal.\n\n"
                    "**Indice** : trier par **profit decroissant**, puis "
                    "placer chaque tache dans le creneau **libre le plus "
                    "tardif** $\\le d_i$. Un Union-Find sur les creneaux "
                    "rend le tout quasi lineaire."
                ),
                "prompt_en": (
                    "$n$ jobs; job $i$ has a **deadline** $d_i$ and a "
                    "**profit** $p_i$. Each job takes one time unit; a single "
                    "processor runs one job per integer slot $1, 2, 3, "
                    "\\dots$ A job pays its profit only if it finishes **by "
                    "slot** $d_i$. **Maximize total profit.**\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($1 \\le n \\le 10^5$)\n"
                    "- next $n$ lines: $d_i$ and $p_i$ "
                    "($1 \\le d_i \\le n$, $1 \\le p_i \\le 10^9$)\n\n"
                    "**Output**: one integer - the maximum profit.\n\n"
                    "**Hint**: sort by **decreasing profit**, then place "
                    "each job in the **latest free slot** $\\le d_i$. A "
                    "Union-Find over slots makes it near-linear."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0])\n"
                    "    jobs = []\n"
                    "    for i in range(n):\n"
                    "        d = int(data[1+2*i]); p = int(data[2+2*i])\n"
                    "        jobs.append((d, p))\n"
                    "    # TODO: greedy by profit, latest free slot.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "4\n2 100\n1 19\n2 27\n1 25\n", "expected": "127\n", "is_sample": True},
                    {"input": "1\n1 50\n", "expected": "50\n", "is_sample": True},
                    {"input": "3\n1 10\n1 20\n1 30\n", "expected": "30\n", "is_sample": False},
                    {"input": "5\n2 20\n2 15\n1 10\n3 5\n3 1\n", "expected": "40\n", "is_sample": False},
                    {"input": "4\n4 70\n1 80\n1 30\n1 100\n", "expected": "170\n", "is_sample": False},
                    {"input": "5\n3 35\n4 30\n4 25\n2 20\n3 15\n", "expected": "110\n", "is_sample": False},
                ],
            },
        ],
    },

    # =================================================================
    # Lesson 3 - Programmation dynamique
    # =================================================================
    {
        "slug": "programmation-dynamique",
        "title_fr": "Programmation dynamique",
        "title_en": "Dynamic Programming",
        "order_idx": 2,
        "content_fr_file": "lesson_03_dynamic_programming.fr.md",
        "content_en_file": "lesson_03_dynamic_programming.en.md",
        "exercises": [
            {
                "key": "EX_PA_LIS",
                "title_fr": "Plus longue sous-suite croissante",
                "title_en": "Longest increasing subsequence",
                "prompt_fr": (
                    "Calculer la **longueur** de la plus longue sous-suite "
                    "**strictement croissante** de $A$ (elements pas "
                    "necessairement contigus, ordre preserve).\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ ($0 \\le n \\le 10^5$)\n"
                    "- ligne 2 : $n$ entiers ($|a_i| \\le 10^9$ ; ligne vide "
                    "si $n = 0$)\n\n"
                    "**Sortie** : un seul entier (0 si $n = 0$).\n\n"
                    "**Indice** : la DP $O(n^2)$ (`dp[i]` = LIS finissant en "
                    "$i$) passe pour de petits $n$. Pour la version "
                    "$O(n \\log n)$, maintenir les **plus petites fins** de "
                    "sous-suites de chaque longueur et faire une recherche "
                    "dichotomique (`bisect_left` pour la version stricte)."
                ),
                "prompt_en": (
                    "Compute the **length** of the longest **strictly "
                    "increasing** subsequence of $A$ (elements not "
                    "necessarily contiguous, order preserved).\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($0 \\le n \\le 10^5$)\n"
                    "- line 2: $n$ integers ($|a_i| \\le 10^9$; empty line "
                    "if $n = 0$)\n\n"
                    "**Output**: one integer (0 if $n = 0$).\n\n"
                    "**Hint**: the $O(n^2)$ DP (`dp[i]` = LIS ending at $i$) "
                    "passes for small $n$. For the $O(n \\log n)$ version, "
                    "keep the **smallest tail** of subsequences of each "
                    "length and binary search (`bisect_left` for the strict "
                    "version)."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0]) if data else 0\n"
                    "    a = list(map(int, data[1:1+n]))\n"
                    "    # TODO: longest strictly increasing subsequence.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "8\n10 9 2 5 3 7 101 18\n", "expected": "4\n", "is_sample": True},
                    {"input": "0\n\n", "expected": "0\n", "is_sample": True},
                    {"input": "1\n5\n", "expected": "1\n", "is_sample": False},
                    {"input": "6\n1 2 3 4 5 6\n", "expected": "6\n", "is_sample": False},
                    {"input": "5\n5 4 3 2 1\n", "expected": "1\n", "is_sample": False},
                    {"input": "7\n2 2 2 3 3 1 4\n", "expected": "3\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_PA_KNAPSACK",
                "title_fr": "Sac a dos 0/1",
                "title_en": "0/1 knapsack",
                "prompt_fr": (
                    "$n$ objets ; l'objet $i$ a un poids $w_i$ et une valeur "
                    "$v_i$. Choisir un sous-ensemble de poids total "
                    "$\\le W$ **maximisant la valeur totale**. Chaque objet "
                    "est pris au plus une fois.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ et $W$ ($1 \\le n \\le 1000$, "
                    "$0 \\le W \\le 1000$)\n"
                    "- $n$ lignes suivantes : $w_i$ et $v_i$ "
                    "($1 \\le w_i \\le 1000$, $1 \\le v_i \\le 10^9$)\n\n"
                    "**Sortie** : un seul entier - la valeur maximale "
                    "(0 si aucun objet ne tient).\n\n"
                    "**Indice** : DP 1D `dp[c]` = meilleure valeur pour une "
                    "capacite $c$. Pour chaque objet, parcourir $c$ de $W$ "
                    "**vers le bas** jusqu'a $w_i$ - le sens decroissant "
                    "garantit qu'on ne reutilise pas l'objet. $O(nW)$."
                ),
                "prompt_en": (
                    "$n$ items; item $i$ has weight $w_i$ and value $v_i$. "
                    "Pick a subset of total weight $\\le W$ **maximizing "
                    "total value**. Each item is taken at most once.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $W$ ($1 \\le n \\le 1000$, "
                    "$0 \\le W \\le 1000$)\n"
                    "- next $n$ lines: $w_i$ and $v_i$ "
                    "($1 \\le w_i \\le 1000$, $1 \\le v_i \\le 10^9$)\n\n"
                    "**Output**: one integer - the maximum value (0 if no "
                    "item fits).\n\n"
                    "**Hint**: 1D DP `dp[c]` = best value for capacity $c$. "
                    "For each item, iterate $c$ from $W$ **downward** to "
                    "$w_i$ - the descending order guarantees the item is not "
                    "reused. $O(nW)$."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n, W = int(data[0]), int(data[1])\n"
                    "    items = []\n"
                    "    for i in range(n):\n"
                    "        w = int(data[2+2*i]); v = int(data[3+2*i])\n"
                    "        items.append((w, v))\n"
                    "    # TODO: 0/1 knapsack DP.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "3 5\n2 3\n3 4\n4 5\n", "expected": "7\n", "is_sample": True},
                    {"input": "1 0\n5 100\n", "expected": "0\n", "is_sample": True},
                    {"input": "4 10\n5 10\n4 40\n6 30\n3 50\n", "expected": "90\n", "is_sample": False},
                    {"input": "3 6\n1 1\n2 2\n3 3\n", "expected": "6\n", "is_sample": False},
                    {"input": "5 10\n2 3\n2 3\n2 3\n2 3\n2 3\n", "expected": "15\n", "is_sample": False},
                    {"input": "2 3\n4 100\n5 200\n", "expected": "0\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_PA_EDIT",
                "title_fr": "Distance d'edition",
                "title_en": "Edit distance",
                "prompt_fr": (
                    "Calculer la **distance de Levenshtein** entre deux "
                    "chaines $s$ et $t$ : le nombre minimal d'operations "
                    "(**insertion**, **suppression**, **substitution** d'un "
                    "caractere, cout 1 chacune) pour transformer $s$ en "
                    "$t$.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : la chaine $s$\n"
                    "- ligne 2 : la chaine $t$\n\n"
                    "avec $0 \\le |s|, |t| \\le 2000$, lettres minuscules "
                    "(une ligne vide represente la chaine vide).\n\n"
                    "**Sortie** : un seul entier.\n\n"
                    "**Indice** : `dp[i][j]` = distance entre les $i$ "
                    "premiers caracteres de $s$ et les $j$ premiers de $t$. "
                    "Si $s_i = t_j$, `dp[i][j] = dp[i-1][j-1]` ; sinon "
                    "$1 + \\min$ des trois voisins. $O(|s|\\,|t|)$, "
                    "reductible a deux lignes en memoire."
                ),
                "prompt_en": (
                    "Compute the **Levenshtein distance** between two "
                    "strings $s$ and $t$: the minimum number of operations "
                    "(**insert**, **delete**, **substitute** one character, "
                    "cost 1 each) to turn $s$ into $t$.\n\n"
                    "**Input**:\n\n"
                    "- line 1: the string $s$\n"
                    "- line 2: the string $t$\n\n"
                    "with $0 \\le |s|, |t| \\le 2000$, lowercase letters (an "
                    "empty line means the empty string).\n\n"
                    "**Output**: one integer.\n\n"
                    "**Hint**: `dp[i][j]` = distance between the first $i$ "
                    "chars of $s$ and the first $j$ of $t$. If $s_i = t_j$, "
                    "`dp[i][j] = dp[i-1][j-1]`; otherwise $1 + \\min$ of the "
                    "three neighbors. $O(|s|\\,|t|)$, reducible to two rows "
                    "of memory."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    s = sys.stdin.readline().rstrip('\\n')\n"
                    "    t = sys.stdin.readline().rstrip('\\n')\n"
                    "    # TODO: Levenshtein DP.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "horse\nros\n", "expected": "3\n", "is_sample": True},
                    {"input": "intention\nexecution\n", "expected": "5\n", "is_sample": True},
                    {"input": "\n\n", "expected": "0\n", "is_sample": False},
                    {"input": "abc\nabc\n", "expected": "0\n", "is_sample": False},
                    {"input": "abc\n\n", "expected": "3\n", "is_sample": False},
                    {"input": "kitten\nsitting\n", "expected": "3\n", "is_sample": False},
                ],
            },
        ],
    },

    # =================================================================
    # Lesson 4 - Backtracking & branch and bound
    # =================================================================
    {
        "slug": "backtracking",
        "title_fr": "Backtracking & branch and bound",
        "title_en": "Backtracking & Branch and Bound",
        "order_idx": 3,
        "content_fr_file": "lesson_04_backtracking.fr.md",
        "content_en_file": "lesson_04_backtracking.en.md",
        "exercises": [
            {
                "key": "EX_PA_NQUEENS",
                "title_fr": "N-reines : comptage",
                "title_en": "N-queens: counting",
                "prompt_fr": (
                    "Compter le nombre de facons de placer $N$ reines sur un "
                    "echiquier $N \\times N$ sans qu'aucune ne puisse en "
                    "attaquer une autre (pas deux sur une meme ligne, "
                    "colonne, ou diagonale).\n\n"
                    "**Entree** : un seul entier $N$ ($1 \\le N \\le 12$).\n\n"
                    "**Sortie** : un seul entier - le nombre de "
                    "placements.\n\n"
                    "**Indice** : backtracking ligne par ligne. Maintenir "
                    "trois ensembles de colonnes/diagonales occupees "
                    "(`col`, `r - c`, `r + c`) pour tester un placement en "
                    "$O(1)$ et **elaguer** des qu'un conflit apparait."
                ),
                "prompt_en": (
                    "Count the number of ways to place $N$ queens on an "
                    "$N \\times N$ board so that none can attack another (no "
                    "two on the same row, column, or diagonal).\n\n"
                    "**Input**: a single integer $N$ ($1 \\le N \\le 12$).\n\n"
                    "**Output**: one integer - the number of placements.\n\n"
                    "**Hint**: row-by-row backtracking. Keep three sets of "
                    "occupied columns/diagonals (`col`, `r - c`, `r + c`) to "
                    "test a placement in $O(1)$ and **prune** as soon as a "
                    "conflict appears."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    n = int(sys.stdin.readline())\n"
                    "    # TODO: backtracking count of N-queens solutions.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "4\n", "expected": "2\n", "is_sample": True},
                    {"input": "1\n", "expected": "1\n", "is_sample": True},
                    {"input": "2\n", "expected": "0\n", "is_sample": False},
                    {"input": "8\n", "expected": "92\n", "is_sample": False},
                    {"input": "6\n", "expected": "4\n", "is_sample": False},
                    {"input": "11\n", "expected": "2680\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_PA_SUBSET_COUNT",
                "title_fr": "Comptage de sous-ensembles de somme donnee",
                "title_en": "Counting subsets with a given sum",
                "prompt_fr": (
                    "Compter le nombre de **sous-ensembles** de $A$ dont la "
                    "somme vaut exactement $T$. Le **sous-ensemble vide** "
                    "compte (sa somme est $0$), et des elements de meme "
                    "valeur a des positions differentes sont distincts.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ et $T$ ($1 \\le n \\le 20$, "
                    "$|T| \\le 2 \\cdot 10^{10}$)\n"
                    "- ligne 2 : $n$ entiers ($|a_i| \\le 10^9$)\n\n"
                    "**Sortie** : un seul entier - le nombre de "
                    "sous-ensembles.\n\n"
                    "**Indice** : backtracking binaire (prendre / ne pas "
                    "prendre chaque element). $2^n$ feuilles - correct "
                    "jusqu'a $n = 20$. Au-dela, la technique du "
                    "**meet in the middle** ramene a $O(2^{n/2})$."
                ),
                "prompt_en": (
                    "Count the number of **subsets** of $A$ whose sum is "
                    "exactly $T$. The **empty subset** counts (its sum is "
                    "$0$), and equal-valued elements at different positions "
                    "are distinct.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $T$ ($1 \\le n \\le 20$, "
                    "$|T| \\le 2 \\cdot 10^{10}$)\n"
                    "- line 2: $n$ integers ($|a_i| \\le 10^9$)\n\n"
                    "**Output**: one integer - the number of subsets.\n\n"
                    "**Hint**: binary backtracking (take / skip each "
                    "element). $2^n$ leaves - fine up to $n = 20$. Beyond "
                    "that, the **meet in the middle** technique brings it "
                    "to $O(2^{n/2})$."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n, t = int(data[0]), int(data[1])\n"
                    "    a = list(map(int, data[2:2+n]))\n"
                    "    # TODO: count subsets summing to t.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "4 5\n1 2 3 4\n", "expected": "2\n", "is_sample": True},
                    {"input": "3 0\n-1 1 0\n", "expected": "4\n", "is_sample": True},
                    {"input": "1 5\n5\n", "expected": "1\n", "is_sample": False},
                    {"input": "5 10\n2 2 2 2 2\n", "expected": "1\n", "is_sample": False},
                    {"input": "4 7\n1 2 3 4\n", "expected": "2\n", "is_sample": False},
                    {"input": "6 0\n1 -1 2 -2 3 -3\n", "expected": "10\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_PA_HAMILTON",
                "title_fr": "Comptage de chemins hamiltoniens",
                "title_en": "Counting Hamiltonian paths",
                "prompt_fr": (
                    "Dans un graphe **non oriente** a $n$ sommets, compter "
                    "les **chemins hamiltoniens** : les sequences ordonnees "
                    "des $n$ sommets ou chaque sommet apparait une fois et "
                    "chaque paire consecutive est reliee par une arete. "
                    "Chaque chemin non oriente est donc compte **deux fois** "
                    "(un sens et son inverse).\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ et $m$ ($1 \\le n \\le 10$, "
                    "$0 \\le m \\le n(n-1)/2$)\n"
                    "- $m$ lignes suivantes : deux entiers $u$ et $v$ "
                    "(sommets **1-indexes**, $u \\ne v$, graphe simple)\n\n"
                    "**Sortie** : un seul entier - le nombre de sequences.\n\n"
                    "**Indice** : backtracking depuis chaque sommet de "
                    "depart, ou DP sur masques de bits `dp[masque][dernier]` "
                    "en $O(2^n n^2)$. Le masque encode l'ensemble des "
                    "sommets deja visites."
                ),
                "prompt_en": (
                    "In an **undirected** graph on $n$ vertices, count the "
                    "**Hamiltonian paths**: the ordered sequences of all $n$ "
                    "vertices where each vertex appears once and each "
                    "consecutive pair is joined by an edge. Each undirected "
                    "path is thus counted **twice** (a direction and its "
                    "reverse).\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $m$ ($1 \\le n \\le 10$, "
                    "$0 \\le m \\le n(n-1)/2$)\n"
                    "- next $m$ lines: two integers $u$ and $v$ "
                    "(**1-indexed** vertices, $u \\ne v$, simple graph)\n\n"
                    "**Output**: one integer - the number of sequences.\n\n"
                    "**Hint**: backtracking from each start vertex, or "
                    "bitmask DP `dp[mask][last]` in $O(2^n n^2)$. The mask "
                    "encodes the set of already-visited vertices."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n, m = int(data[0]), int(data[1])\n"
                    "    edges = []\n"
                    "    for i in range(m):\n"
                    "        u = int(data[2+2*i]) - 1; v = int(data[3+2*i]) - 1\n"
                    "        edges.append((u, v))\n"
                    "    # TODO: count Hamiltonian vertex sequences.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "3 2\n1 2\n2 3\n", "expected": "2\n", "is_sample": True},
                    {"input": "3 3\n1 2\n2 3\n1 3\n", "expected": "6\n", "is_sample": True},
                    {"input": "4 3\n1 2\n2 3\n3 4\n", "expected": "2\n", "is_sample": False},
                    {"input": "4 6\n1 2\n1 3\n1 4\n2 3\n2 4\n3 4\n", "expected": "24\n", "is_sample": False},
                    {"input": "5 4\n1 2\n2 3\n3 4\n4 5\n", "expected": "2\n", "is_sample": False},
                    {"input": "2 1\n1 2\n", "expected": "2\n", "is_sample": False},
                ],
            },
        ],
    },
]


# --------------------------------------------------------------------- #
# Reference solutions - used by --validate-only to confirm the test     #
# cases above are self-consistent. Every key must match an exercise.   #
# --------------------------------------------------------------------- #

REFERENCE_SOLUTIONS = {
    "EX_PA_INVERSIONS": r"""import sys
def main():
    data = sys.stdin.read().split()
    n = int(data[0])
    a = list(map(int, data[1:1+n]))
    def sort_count(arr):
        if len(arr) <= 1:
            return arr, 0
        m = len(arr) // 2
        l, cl = sort_count(arr[:m])
        r, cr = sort_count(arr[m:])
        merged = []
        i = j = 0
        inv = cl + cr
        while i < len(l) and j < len(r):
            if l[i] <= r[j]:
                merged.append(l[i]); i += 1
            else:
                merged.append(r[j]); j += 1
                inv += len(l) - i
        merged.extend(l[i:]); merged.extend(r[j:])
        return merged, inv
    print(sort_count(a)[1])
main()
""",
    "EX_PA_MAXSUB": r"""import sys
sys.setrecursionlimit(300000)
def main():
    data = sys.stdin.read().split()
    n = int(data[0])
    a = list(map(int, data[1:1+n]))
    def dc(lo, hi):
        if lo == hi:
            return a[lo], a[lo], a[lo], a[lo]
        mid = (lo + hi) // 2
        lb, lp, ls, lt = dc(lo, mid)
        rb, rp, rs, rt = dc(mid + 1, hi)
        best = max(lb, rb, ls + rp)
        prefix = max(lp, lt + rp)
        suffix = max(rs, rt + ls)
        total = lt + rt
        return best, prefix, suffix, total
    print(dc(0, n - 1)[0])
main()
""",
    "EX_PA_REVPAIRS": r"""import sys
def main():
    data = sys.stdin.read().split()
    n = int(data[0])
    a = list(map(int, data[1:1+n]))
    def sc(arr):
        if len(arr) <= 1:
            return arr, 0
        m = len(arr) // 2
        l, cl = sc(arr[:m])
        r, cr = sc(arr[m:])
        cnt = cl + cr
        j = 0
        for x in l:
            while j < len(r) and x > 2 * r[j]:
                j += 1
            cnt += j
        merged = []
        i = j2 = 0
        while i < len(l) and j2 < len(r):
            if l[i] <= r[j2]:
                merged.append(l[i]); i += 1
            else:
                merged.append(r[j2]); j2 += 1
        merged.extend(l[i:]); merged.extend(r[j2:])
        return merged, cnt
    print(sc(a)[1])
main()
""",
    "EX_PA_ACTIVITY": r"""import sys
def main():
    data = sys.stdin.read().split()
    n = int(data[0])
    iv = []
    for i in range(n):
        s = int(data[1+2*i]); e = int(data[2+2*i])
        iv.append((s, e))
    iv.sort(key=lambda p: (p[1], p[0]))
    cnt = 0
    cur = -(10**18)
    for s, e in iv:
        if s >= cur:
            cnt += 1; cur = e
    print(cnt)
main()
""",
    "EX_PA_ROPES": r"""import sys, heapq
def main():
    data = sys.stdin.read().split()
    n = int(data[0])
    a = list(map(int, data[1:1+n]))
    if n == 1:
        print(0); return
    heapq.heapify(a)
    cost = 0
    while len(a) > 1:
        x = heapq.heappop(a); y = heapq.heappop(a)
        cost += x + y
        heapq.heappush(a, x + y)
    print(cost)
main()
""",
    "EX_PA_JOBSEQ": r"""import sys
def main():
    data = sys.stdin.read().split()
    n = int(data[0])
    jobs = []
    for i in range(n):
        d = int(data[1+2*i]); p = int(data[2+2*i])
        jobs.append((d, p))
    jobs.sort(key=lambda p: -p[1])
    maxd = max(d for d, _ in jobs)
    parent = list(range(maxd + 1))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    profit = 0
    for d, p in jobs:
        slot = find(min(d, maxd))
        if slot > 0:
            profit += p
            parent[slot] = slot - 1
    print(profit)
main()
""",
    "EX_PA_LIS": r"""import sys
from bisect import bisect_left
def main():
    data = sys.stdin.read().split()
    n = int(data[0]) if data else 0
    a = list(map(int, data[1:1+n]))
    tails = []
    for x in a:
        i = bisect_left(tails, x)
        if i == len(tails):
            tails.append(x)
        else:
            tails[i] = x
    print(len(tails))
main()
""",
    "EX_PA_KNAPSACK": r"""import sys
def main():
    data = sys.stdin.read().split()
    n, W = int(data[0]), int(data[1])
    dp = [0] * (W + 1)
    for i in range(n):
        w = int(data[2+2*i]); v = int(data[3+2*i])
        for c in range(W, w - 1, -1):
            cand = dp[c-w] + v
            if cand > dp[c]:
                dp[c] = cand
    print(dp[W])
main()
""",
    "EX_PA_EDIT": r"""import sys
def main():
    s = sys.stdin.readline().rstrip('\n')
    t = sys.stdin.readline().rstrip('\n')
    n, m = len(s), len(t)
    prev = list(range(m + 1))
    for i in range(1, n + 1):
        cur = [i] + [0] * m
        si = s[i-1]
        for j in range(1, m + 1):
            if si == t[j-1]:
                cur[j] = prev[j-1]
            else:
                cur[j] = 1 + min(prev[j], cur[j-1], prev[j-1])
        prev = cur
    print(prev[m])
main()
""",
    "EX_PA_NQUEENS": r"""import sys
def main():
    n = int(sys.stdin.readline())
    cols = set(); d1 = set(); d2 = set()
    cnt = 0
    def bt(r):
        nonlocal cnt
        if r == n:
            cnt += 1; return
        for c in range(n):
            if c in cols or (r - c) in d1 or (r + c) in d2:
                continue
            cols.add(c); d1.add(r - c); d2.add(r + c)
            bt(r + 1)
            cols.discard(c); d1.discard(r - c); d2.discard(r + c)
    bt(0)
    print(cnt)
main()
""",
    "EX_PA_SUBSET_COUNT": r"""import sys
def main():
    data = sys.stdin.read().split()
    n, t = int(data[0]), int(data[1])
    a = list(map(int, data[2:2+n]))
    cnt = 0
    def bt(i, s):
        nonlocal cnt
        if i == n:
            if s == t:
                cnt += 1
            return
        bt(i + 1, s)
        bt(i + 1, s + a[i])
    bt(0, 0)
    print(cnt)
main()
""",
    "EX_PA_HAMILTON": r"""import sys
def main():
    data = sys.stdin.read().split()
    n, m = int(data[0]), int(data[1])
    adj = [[False] * n for _ in range(n)]
    for i in range(m):
        u = int(data[2+2*i]) - 1; v = int(data[3+2*i]) - 1
        adj[u][v] = True; adj[v][u] = True
    dp = [[0] * n for _ in range(1 << n)]
    for i in range(n):
        dp[1 << i][i] = 1
    for mask in range(1 << n):
        row = dp[mask]
        for last in range(n):
            cnt = row[last]
            if not cnt:
                continue
            al = adj[last]
            for nxt in range(n):
                if mask >> nxt & 1:
                    continue
                if al[nxt]:
                    dp[mask | 1 << nxt][nxt] += cnt
    full = (1 << n) - 1
    print(sum(dp[full][i] for i in range(n)))
main()
""",
}


def _flatten_exercises():
    for lesson in LESSONS:
        for ex in lesson["exercises"]:
            yield ex


def _normalise(out: str) -> str:
    """Trim trailing whitespace per line so a checker that's
    whitespace-tolerant agrees with our literal expectations."""
    lines = [ln.rstrip() for ln in out.splitlines()]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def validate_reference_solutions() -> int:
    """Run every REFERENCE_SOLUTIONS entry against its DB-bound test
    cases. Exits non-zero on the first mismatch - this catches
    test-case bugs before they ship to students."""
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


# --------------------------------------------------------------------- #
# DB upsert (mirrors seed_chapter4 exactly so behavior is identical)    #
# --------------------------------------------------------------------- #

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
                    f"      - exercise {ex['key']:<20} "
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
    print(f"Chapitre 5 - Paradigmes : OK ({state}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
