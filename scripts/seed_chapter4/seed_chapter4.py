"""Seed Chapter 4 - Recherche & invariants.

Cree (ou met a jour) la section ``recherche`` avec quatre lecons :

  1. Recherche dichotomique classique & invariants de boucle
  2. Dichotomie sur les reels et sur la reponse
  3. Two pointers
  4. Sliding window

Chaque lecon contient trois exercices inline gradues (standard,
twist, dur). Idempotent.

Pre-deploiement le script verifie que chaque solution de reference
passe sur ses test cases (--validate-only pour ne faire QUE ca, sans
toucher a la base).

Usage:
    python scripts/seed_chapter4/seed_chapter4.py
    python scripts/seed_chapter4/seed_chapter4.py --draft
    python scripts/seed_chapter4/seed_chapter4.py --validate-only
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
    "slug": "recherche",
    "title_fr": "Recherche & invariants",
    "title_en": "Search & Invariants",
    "description_fr": (
        "Recherche dichotomique avec preuve par invariant. Bissection "
        "sur les reels. Le pattern \"binary search on the answer\" "
        "(maximiser le minimum, minimiser le maximum). Two pointers et "
        "sliding window comme expressions temporelles de la monotonie."
    ),
    "description_en": (
        "Binary search with invariant-based proof. Bisection on reals. "
        "The \"binary search on the answer\" pattern (maximize minimum, "
        "minimize maximum). Two pointers and sliding window as temporal "
        "expressions of monotonicity."
    ),
    "order_idx": 3,
}


# --------------------------------------------------------------------- #
# Exercises                                                             #
# --------------------------------------------------------------------- #

LESSONS: list[dict] = [
    # =================================================================
    # Lesson 1 - Recherche dichotomique classique
    # =================================================================
    {
        "slug": "dichotomie",
        "title_fr": "Recherche dichotomique & invariants",
        "title_en": "Binary Search & Invariants",
        "order_idx": 0,
        "content_fr_file": "lesson_01_dichotomie.fr.md",
        "content_en_file": "lesson_01_dichotomie.en.md",
        "exercises": [
            {
                "key": "EX_SE_LOWERBOUND",
                "title_fr": "Lower bound",
                "title_en": "Lower bound",
                "prompt_fr": (
                    "Etant donne un tableau **trie** $A$ de taille $n$ et $q$ "
                    "requetes, repondre pour chaque $x$ le plus petit indice "
                    "$i$ tel que $A[i] \\ge x$. Si aucun, repondre $n$.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ et $q$ ($1 \\le n, q \\le 10^5$)\n"
                    "- ligne 2 : $n$ entiers tries croissants ($|a_i| \\le 10^9$)\n"
                    "- $q$ lignes suivantes : un entier $x$ par ligne\n\n"
                    "**Sortie** : $q$ lignes, une reponse par requete.\n\n"
                    "**Indice** : intervalle semi-ouvert $[lo, hi)$, "
                    "invariant `A[<lo] < x` et `A[>=hi] >= x`."
                ),
                "prompt_en": (
                    "Given a **sorted** array $A$ of size $n$ and $q$ "
                    "queries, answer for each $x$ the smallest index $i$ "
                    "with $A[i] \\ge x$. If none, output $n$.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $q$ ($1 \\le n, q \\le 10^5$)\n"
                    "- line 2: $n$ ascending integers ($|a_i| \\le 10^9$)\n"
                    "- next $q$ lines: one integer $x$ per line\n\n"
                    "**Output**: $q$ lines, one answer per query.\n\n"
                    "**Hint**: half-open interval $[lo, hi)$, invariant "
                    "`A[<lo] < x` and `A[>=hi] >= x`."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n, q = int(data[0]), int(data[1])\n"
                    "    a = list(map(int, data[2:2+n]))\n"
                    "    out = []\n"
                    "    for k in range(q):\n"
                    "        x = int(data[2+n+k])\n"
                    "        # TODO: binary search.\n"
                    "        out.append(str(0))\n"
                    "    sys.stdout.write('\\n'.join(out) + '\\n')\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5 3\n1 3 5 7 9\n4\n5\n10\n",
                     "expected": "2\n2\n5\n", "is_sample": True},
                    {"input": "1 2\n10\n5\n10\n",
                     "expected": "0\n0\n", "is_sample": True},
                    {"input": "5 1\n1 1 1 1 1\n1\n",
                     "expected": "0\n", "is_sample": False},
                    {"input": "5 1\n1 1 1 1 1\n2\n",
                     "expected": "5\n", "is_sample": False},
                    {"input": "6 4\n-5 -2 0 3 7 10\n-5\n0\n8\n11\n",
                     "expected": "0\n2\n5\n6\n", "is_sample": False},
                    {"input": "1 1\n42\n42\n",
                     "expected": "0\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_SE_FIRSTOCC",
                "title_fr": "Plage d'occurrences",
                "title_en": "Occurrence range",
                "prompt_fr": (
                    "Etant donne un tableau **trie** $A$ et une cible $x$, "
                    "renvoyer la plage d'occurrences de $x$ : la **premiere** "
                    "et la **derniere** position 0-indexees, ou `-1 -1` si "
                    "$x$ est absent.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ ($1 \\le n \\le 10^5$)\n"
                    "- ligne 2 : $n$ entiers tries croissants\n"
                    "- ligne 3 : la cible $x$\n\n"
                    "**Sortie** : `first last` sur une ligne, separes par un "
                    "espace.\n\n"
                    "**Indice** : `lower_bound(x)` et `upper_bound(x) - 1`. "
                    "Tester explicitement la presence."
                ),
                "prompt_en": (
                    "Given a **sorted** array $A$ and a target $x$, return "
                    "the range of $x$'s occurrences: the **first** and "
                    "**last** 0-indexed positions, or `-1 -1` if $x$ is "
                    "absent.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($1 \\le n \\le 10^5$)\n"
                    "- line 2: $n$ ascending integers\n"
                    "- line 3: the target $x$\n\n"
                    "**Output**: `first last` on a single line, "
                    "space-separated.\n\n"
                    "**Hint**: `lower_bound(x)` and `upper_bound(x) - 1`. "
                    "Check presence explicitly."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0])\n"
                    "    a = list(map(int, data[1:1+n]))\n"
                    "    x = int(data[1+n])\n"
                    "    # TODO: lower_bound and upper_bound.\n"
                    "    print(-1, -1)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "8\n1 2 3 3 3 4 5 6\n3\n",
                     "expected": "2 4\n", "is_sample": True},
                    {"input": "5\n1 2 4 5 6\n3\n",
                     "expected": "-1 -1\n", "is_sample": True},
                    {"input": "5\n7 7 7 7 7\n7\n",
                     "expected": "0 4\n", "is_sample": False},
                    {"input": "1\n10\n10\n",
                     "expected": "0 0\n", "is_sample": False},
                    {"input": "1\n10\n5\n",
                     "expected": "-1 -1\n", "is_sample": False},
                    {"input": "6\n-3 -1 0 0 2 5\n0\n",
                     "expected": "2 3\n", "is_sample": False},
                    {"input": "5\n1 2 3 4 5\n6\n",
                     "expected": "-1 -1\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_SE_ISQRT",
                "title_fr": "Racine carree entiere",
                "title_en": "Integer square root",
                "prompt_fr": (
                    "Calculer $\\lfloor \\sqrt{N} \\rfloor$ par dichotomie "
                    "discrete (pas via `math.sqrt`, qui souffre de bruit "
                    "flottant pour les grands $N$).\n\n"
                    "**Entree** : un seul entier $N$ ($0 \\le N \\le 10^{18}$).\n\n"
                    "**Sortie** : un seul entier, le plus grand $k$ tel que "
                    "$k^2 \\le N$.\n\n"
                    "**Indice** : dichotomie sur $k \\in [0, 10^9]$. Le "
                    "predicat $P(k) = (k^2 \\le N)$ est monotone - on "
                    "cherche son plus grand vrai. Patron `search_max` de la "
                    "lecon 2."
                ),
                "prompt_en": (
                    "Compute $\\lfloor \\sqrt{N} \\rfloor$ via discrete "
                    "binary search (NOT `math.sqrt`, which suffers from "
                    "float noise for large $N$).\n\n"
                    "**Input**: a single integer $N$ ($0 \\le N \\le 10^{18}$).\n\n"
                    "**Output**: a single integer, the largest $k$ with "
                    "$k^2 \\le N$.\n\n"
                    "**Hint**: binary search on $k \\in [0, 10^9]$. The "
                    "predicate $P(k) = (k^2 \\le N)$ is monotone - we "
                    "look for its largest true point. Use the lesson 2 "
                    "`search_max` pattern."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    n = int(sys.stdin.readline())\n"
                    "    # TODO: largest k with k*k <= n via binary search.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "0\n",   "expected": "0\n", "is_sample": True},
                    {"input": "16\n",  "expected": "4\n", "is_sample": True},
                    {"input": "1\n",   "expected": "1\n", "is_sample": False},
                    {"input": "2\n",   "expected": "1\n", "is_sample": False},
                    {"input": "99\n",  "expected": "9\n", "is_sample": False},
                    {"input": "100\n", "expected": "10\n", "is_sample": False},
                    {"input": "999999999999999999\n",
                     "expected": "999999999\n", "is_sample": False},
                    {"input": "1000000000000000000\n",
                     "expected": "1000000000\n", "is_sample": False},
                ],
            },
        ],
    },

    # =================================================================
    # Lesson 2 - Dichotomie sur les reels & sur la reponse
    # =================================================================
    {
        "slug": "binsearch-answer",
        "title_fr": "Dichotomie sur les reels & sur la reponse",
        "title_en": "Binary Search on Reals & on the Answer",
        "order_idx": 1,
        "content_fr_file": "lesson_02_binsearch_answer.fr.md",
        "content_en_file": "lesson_02_binsearch_answer.en.md",
        "exercises": [
            {
                "key": "EX_SE_AGGRCOWS",
                "title_fr": "Aggressive Cows",
                "title_en": "Aggressive Cows",
                "prompt_fr": (
                    "$n$ stalles aux positions $x_1, \\dots, x_n$. Placer "
                    "$k$ vaches en **maximisant la distance minimale** "
                    "entre deux vaches consecutives.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ et $k$ ($2 \\le k \\le n \\le 10^5$)\n"
                    "- ligne 2 : $n$ entiers $x_i$ ($0 \\le x_i \\le 10^9$, "
                    "non necessairement tries)\n\n"
                    "**Sortie** : un entier - la distance minimale "
                    "maximisable.\n\n"
                    "**Indice** : trier les positions, puis dichotomie sur "
                    "la reponse $d \\in [0, x_n - x_1]$. Verifier `feasible(d)` "
                    "gloutonnement en $O(n)$."
                ),
                "prompt_en": (
                    "$n$ stalls at positions $x_1, \\dots, x_n$. Place $k$ "
                    "cows so as to **maximize the minimum distance** between "
                    "two consecutive cows.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $k$ ($2 \\le k \\le n \\le 10^5$)\n"
                    "- line 2: $n$ integers $x_i$ ($0 \\le x_i \\le 10^9$, "
                    "not necessarily sorted)\n\n"
                    "**Output**: one integer - the maximizable minimum "
                    "distance.\n\n"
                    "**Hint**: sort positions, then binary search on the "
                    "answer $d \\in [0, x_n - x_1]$. Check `feasible(d)` "
                    "greedily in $O(n)$."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n, k = int(data[0]), int(data[1])\n"
                    "    x = sorted(map(int, data[2:2+n]))\n"
                    "    # TODO: binary search the answer; feasible greedy.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5 3\n1 2 8 4 9\n",
                     "expected": "3\n", "is_sample": True},
                    {"input": "2 2\n0 1000000000\n",
                     "expected": "1000000000\n", "is_sample": True},
                    {"input": "4 4\n1 2 3 4\n",
                     "expected": "1\n", "is_sample": False},
                    {"input": "6 3\n0 3 7 8 12 15\n",
                     "expected": "7\n", "is_sample": False},
                    {"input": "5 2\n100 200 300 400 500\n",
                     "expected": "400\n", "is_sample": False},
                    {"input": "10 5\n1 2 3 4 5 6 7 8 9 10\n",
                     "expected": "2\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_SE_PAINTERS",
                "title_fr": "Painter's partition",
                "title_en": "Painter's partition",
                "prompt_fr": (
                    "$n$ planches a peindre, longueurs $\\ell_1, \\dots, "
                    "\\ell_n$. On dispose de $k$ peintres ; chacun peint "
                    "une **plage contigue** de planches a la vitesse de "
                    "1 unite par minute. **Minimiser le temps maximum** "
                    "passe par un peintre.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ et $k$ ($1 \\le k \\le n \\le 10^5$)\n"
                    "- ligne 2 : $n$ entiers $\\ell_i$ ($1 \\le \\ell_i "
                    "\\le 10^4$)\n\n"
                    "**Sortie** : un entier - le temps minimum.\n\n"
                    "**Indice** : dichotomie sur $T \\in [\\max \\ell_i, "
                    "\\sum \\ell_i]$. `feasible(T)` : balayer les "
                    "planches, ouvrir un nouveau peintre des qu'un "
                    "morceau depasserait $T$. Faisable ssi le nombre de "
                    "peintres ouverts $\\le k$."
                ),
                "prompt_en": (
                    "$n$ boards to paint, lengths $\\ell_1, \\dots, "
                    "\\ell_n$. We have $k$ painters; each paints a "
                    "**contiguous run** of boards at 1 unit per minute. "
                    "**Minimize the maximum time** spent by any "
                    "painter.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $k$ ($1 \\le k \\le n \\le 10^5$)\n"
                    "- line 2: $n$ integers $\\ell_i$ ($1 \\le \\ell_i "
                    "\\le 10^4$)\n\n"
                    "**Output**: one integer - the minimum time.\n\n"
                    "**Hint**: binary search on $T \\in [\\max \\ell_i, "
                    "\\sum \\ell_i]$. `feasible(T)`: scan the boards, "
                    "open a new painter whenever a chunk would exceed "
                    "$T$. Feasible iff number of painters opened "
                    "$\\le k$."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n, k = int(data[0]), int(data[1])\n"
                    "    L = list(map(int, data[2:2+n]))\n"
                    "    # TODO: binary search on T; feasible by greedy split.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5 2\n10 20 30 40 50\n",
                     "expected": "90\n", "is_sample": True},
                    {"input": "4 4\n1 2 3 4\n",
                     "expected": "4\n", "is_sample": True},
                    {"input": "1 1\n100\n",
                     "expected": "100\n", "is_sample": False},
                    {"input": "5 1\n1 2 3 4 5\n",
                     "expected": "15\n", "is_sample": False},
                    {"input": "5 5\n7 7 7 7 7\n",
                     "expected": "7\n", "is_sample": False},
                    {"input": "6 3\n5 10 30 20 15 25\n",
                     "expected": "45\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_SE_SQRT_REAL",
                "title_fr": "Racine carree reelle",
                "title_en": "Real square root",
                "prompt_fr": (
                    "Calculer $\\sqrt{x}$ avec une **precision absolue** "
                    "$\\le 10^{-6}$ par bissection.\n\n"
                    "**Entree** : un seul reel $x$ ($0 \\le x \\le 10^{12}$, "
                    "au plus 9 decimales).\n\n"
                    "**Sortie** : la racine, formatee avec **6 decimales** "
                    "(`{:.6f}` en Python).\n\n"
                    "**Indice** : intervalle initial $[0, \\max(1, x)]$ - "
                    "necessaire car pour $x < 1$, $\\sqrt{x} > x$. Boucler "
                    "100 fois (largement assez : $\\log_2(10^{12} \\cdot "
                    "10^6) \\approx 60$). Comparaison flottante : "
                    "`hi - lo > 1e-9` ou nombre fixe d'iterations.\n\n"
                    "**Tolerance accordee** : verificateur a $\\pm 10^{-4}$ "
                    "sur la sortie a 6 decimales."
                ),
                "prompt_en": (
                    "Compute $\\sqrt{x}$ to **absolute precision** "
                    "$\\le 10^{-6}$ via bisection.\n\n"
                    "**Input**: a single real $x$ ($0 \\le x \\le 10^{12}$, "
                    "at most 9 decimals).\n\n"
                    "**Output**: the root, formatted with **6 decimals** "
                    "(`{:.6f}` in Python).\n\n"
                    "**Hint**: initial interval $[0, \\max(1, x)]$ - "
                    "necessary because for $x < 1$, $\\sqrt{x} > x$. Run "
                    "100 iterations (more than enough: $\\log_2(10^{12} "
                    "\\cdot 10^6) \\approx 60$). Floating compare: "
                    "`hi - lo > 1e-9` or fixed iteration count.\n\n"
                    "**Tolerance**: checker accepts $\\pm 10^{-4}$ on the "
                    "6-decimal output."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    x = float(sys.stdin.readline())\n"
                    "    # TODO: bisection on [0, max(1, x)] for sqrt.\n"
                    "    print(f\"{0.0:.6f}\")\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "0\n",          "expected": "0.000000\n", "is_sample": True},
                    {"input": "1\n",          "expected": "1.000000\n", "is_sample": True},
                    {"input": "2\n",          "expected": "1.414214\n", "is_sample": False},
                    {"input": "100\n",        "expected": "10.000000\n", "is_sample": False},
                    {"input": "0.25\n",       "expected": "0.500000\n", "is_sample": False},
                    {"input": "1000000000000\n",
                     "expected": "1000000.000000\n", "is_sample": False},
                ],
            },
        ],
    },

    # =================================================================
    # Lesson 3 - Two pointers
    # =================================================================
    {
        "slug": "two-pointers",
        "title_fr": "Two pointers",
        "title_en": "Two pointers",
        "order_idx": 2,
        "content_fr_file": "lesson_03_two_pointers.fr.md",
        "content_en_file": "lesson_03_two_pointers.en.md",
        "exercises": [
            {
                "key": "EX_SE_2SUM",
                "title_fr": "2-Sum dans un tableau trie",
                "title_en": "2-Sum on a sorted array",
                "prompt_fr": (
                    "Etant donne un tableau **trie** $A$ de taille $n$ et "
                    "une cible $T$, trouver une paire d'indices "
                    "**0-indexes** $i < j$ tels que $A[i] + A[j] = T$. "
                    "S'il y en a plusieurs, retourner celle avec le **plus "
                    "petit $i$** ; en cas d'egalite, le **plus petit $j$**.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ et $T$ ($2 \\le n \\le 10^6$, "
                    "$|T| \\le 4 \\cdot 10^9$)\n"
                    "- ligne 2 : $n$ entiers tries ($|a_i| \\le 10^9$)\n\n"
                    "**Sortie** : `i j` separes par un espace, ou `-1 -1` "
                    "s'il n'existe pas de paire.\n\n"
                    "**Indice** : two-pointer extremites opposees, "
                    "$O(n)$."
                ),
                "prompt_en": (
                    "Given a **sorted** array $A$ of size $n$ and target "
                    "$T$, find **0-indexed** $i < j$ with $A[i] + A[j] = "
                    "T$. If multiple, return the one with **smallest $i$**; "
                    "ties broken by **smallest $j$**.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $T$ ($2 \\le n \\le 10^6$, "
                    "$|T| \\le 4 \\cdot 10^9$)\n"
                    "- line 2: $n$ sorted integers ($|a_i| \\le 10^9$)\n\n"
                    "**Output**: `i j` space-separated, or `-1 -1` if no "
                    "such pair.\n\n"
                    "**Hint**: opposite-ends two-pointer, $O(n)$."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n, t = int(data[0]), int(data[1])\n"
                    "    a = list(map(int, data[2:2+n]))\n"
                    "    # TODO: two-pointer.\n"
                    "    print(-1, -1)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5 9\n1 2 4 5 7\n",
                     "expected": "1 4\n", "is_sample": True},
                    {"input": "4 100\n1 2 3 4\n",
                     "expected": "-1 -1\n", "is_sample": True},
                    {"input": "2 5\n2 3\n",
                     "expected": "0 1\n", "is_sample": False},
                    {"input": "5 6\n1 2 3 3 4\n",
                     "expected": "1 4\n", "is_sample": False},
                    {"input": "6 0\n-3 -1 0 0 1 3\n",
                     "expected": "0 5\n", "is_sample": False},
                    {"input": "3 0\n-1 0 1\n",
                     "expected": "0 2\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_SE_3SUM",
                "title_fr": "3-Sum",
                "title_en": "3-Sum",
                "prompt_fr": (
                    "Trouver tous les triplets **distincts** $(a, b, c)$ "
                    "avec $a \\le b \\le c$, $a + b + c = 0$, sans "
                    "doublon - sortie triee.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ ($3 \\le n \\le 3000$)\n"
                    "- ligne 2 : $n$ entiers ($|a_i| \\le 10^5$)\n\n"
                    "**Sortie** : un triplet par ligne, valeurs separees "
                    "par des espaces. Triplets en ordre lexicographique. "
                    "Si aucun triplet, ne rien afficher.\n\n"
                    "**Indice** : trier puis fixer le plus petit $a$, "
                    "two-pointer sur le sous-tableau de droite. $O(n^2)$. "
                    "Sauter explicitement les doublons."
                ),
                "prompt_en": (
                    "Find all **distinct** triples $(a, b, c)$ with "
                    "$a \\le b \\le c$, $a + b + c = 0$, no duplicates "
                    "- output sorted.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($3 \\le n \\le 3000$)\n"
                    "- line 2: $n$ integers ($|a_i| \\le 10^5$)\n\n"
                    "**Output**: one triple per line, values "
                    "space-separated. Triples in lexicographic order. If "
                    "no triple, output nothing.\n\n"
                    "**Hint**: sort, fix the smallest $a$, two-pointer "
                    "on the right subarray. $O(n^2)$. Explicitly skip "
                    "duplicates."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0])\n"
                    "    a = sorted(map(int, data[1:1+n]))\n"
                    "    # TODO: 3-sum O(n^2) with dedup.\n"
                    "    pass\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "6\n-1 0 1 2 -1 -4\n",
                     "expected": "-1 -1 2\n-1 0 1\n", "is_sample": True},
                    {"input": "3\n0 0 0\n",
                     "expected": "0 0 0\n", "is_sample": True},
                    {"input": "4\n1 2 3 4\n",
                     "expected": "", "is_sample": False},
                    {"input": "5\n-2 -1 0 1 2\n",
                     "expected": "-2 0 2\n-1 0 1\n", "is_sample": False},
                    {"input": "6\n-2 0 0 2 2 -2\n",
                     "expected": "-2 0 2\n", "is_sample": False},
                    {"input": "3\n1 1 1\n",
                     "expected": "", "is_sample": False},
                ],
            },
            {
                "key": "EX_SE_REMOVE_DUPS",
                "title_fr": "Compactage de doublons (en place)",
                "title_en": "Deduplicate in place",
                "prompt_fr": (
                    "Etant donne un tableau **trie** $A$ de taille $n$, "
                    "produire en sortie : (1) la nouvelle taille apres "
                    "deduplication ; (2) le prefixe $A[0..k-1]$ "
                    "deduplique.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ ($0 \\le n \\le 10^6$)\n"
                    "- ligne 2 : $n$ entiers tries (vide si $n = 0$)\n\n"
                    "**Sortie** :\n\n"
                    "- ligne 1 : $k$, la nouvelle taille\n"
                    "- ligne 2 : les $k$ premiers elements (vide si $k = 0$ "
                    "- ligne vide)\n\n"
                    "**Indice** : deux pointeurs avancant dans le meme "
                    "sens, $w$ pour ecrire (`write`), $j$ pour lire."
                ),
                "prompt_en": (
                    "Given a **sorted** array $A$ of size $n$, output: "
                    "(1) the new size after deduplication; (2) the "
                    "deduplicated prefix $A[0..k-1]$.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($0 \\le n \\le 10^6$)\n"
                    "- line 2: $n$ sorted integers (empty if $n = 0$)\n\n"
                    "**Output**:\n\n"
                    "- line 1: $k$, the new size\n"
                    "- line 2: the first $k$ elements (empty line if "
                    "$k = 0$)\n\n"
                    "**Hint**: two same-direction pointers, $w$ for "
                    "writing, $j$ for reading."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0]) if data else 0\n"
                    "    a = list(map(int, data[1:1+n]))\n"
                    "    # TODO: in-place dedup with two pointers.\n"
                    "    print(0)\n"
                    "    print('')\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "8\n1 1 2 2 3 4 4 5\n",
                     "expected": "5\n1 2 3 4 5\n", "is_sample": True},
                    {"input": "0\n\n",
                     "expected": "0\n\n", "is_sample": True},
                    {"input": "1\n42\n",
                     "expected": "1\n42\n", "is_sample": False},
                    {"input": "5\n7 7 7 7 7\n",
                     "expected": "1\n7\n", "is_sample": False},
                    {"input": "5\n1 2 3 4 5\n",
                     "expected": "5\n1 2 3 4 5\n", "is_sample": False},
                    {"input": "6\n-3 -3 -1 0 0 5\n",
                     "expected": "4\n-3 -1 0 5\n", "is_sample": False},
                ],
            },
        ],
    },

    # =================================================================
    # Lesson 4 - Sliding window
    # =================================================================
    {
        "slug": "sliding-window",
        "title_fr": "Sliding window",
        "title_en": "Sliding window",
        "order_idx": 3,
        "content_fr_file": "lesson_04_sliding_window.fr.md",
        "content_en_file": "lesson_04_sliding_window.en.md",
        "exercises": [
            {
                "key": "EX_SE_FIXEDSUM",
                "title_fr": "Plus grande somme d'une fenetre fixe",
                "title_en": "Max fixed-window sum",
                "prompt_fr": (
                    "Etant donne un tableau $A$ et $k$, calculer la plus "
                    "grande somme parmi tous les sous-tableaux contigus "
                    "de longueur **exactement** $k$.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ et $k$ ($1 \\le k \\le n \\le 10^6$)\n"
                    "- ligne 2 : $n$ entiers ($|a_i| \\le 10^9$)\n\n"
                    "**Sortie** : un seul entier - la somme maximale.\n\n"
                    "**Indice** : maintenir la somme glissante en $O(1)$ "
                    "par decalage."
                ),
                "prompt_en": (
                    "Given an array $A$ and $k$, compute the largest sum "
                    "over all contiguous subarrays of length **exactly** "
                    "$k$.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $k$ ($1 \\le k \\le n \\le 10^6$)\n"
                    "- line 2: $n$ integers ($|a_i| \\le 10^9$)\n\n"
                    "**Output**: one integer - the maximum sum.\n\n"
                    "**Hint**: keep the rolling sum in $O(1)$ per "
                    "shift."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n, k = int(data[0]), int(data[1])\n"
                    "    a = list(map(int, data[2:2+n]))\n"
                    "    # TODO: rolling sum.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5 3\n1 2 3 4 5\n",
                     "expected": "12\n", "is_sample": True},
                    {"input": "5 1\n-1 -2 -3 -4 -5\n",
                     "expected": "-1\n", "is_sample": True},
                    {"input": "1 1\n42\n",
                     "expected": "42\n", "is_sample": False},
                    {"input": "5 5\n1 2 3 4 5\n",
                     "expected": "15\n", "is_sample": False},
                    {"input": "8 4\n-1 5 2 -3 4 6 -2 1\n",
                     "expected": "9\n", "is_sample": False},
                    {"input": "3 2\n-5 -10 -3\n",
                     "expected": "-13\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_SE_LONGEST_UNIQUE",
                "title_fr": "Plus longue sous-chaine sans repetition",
                "title_en": "Longest substring without repetition",
                "prompt_fr": (
                    "Etant donnee une chaine $s$, trouver la **longueur** "
                    "de la plus longue sous-chaine **sans caractere "
                    "repete**.\n\n"
                    "**Entree** : une seule ligne, la chaine $s$ "
                    "($0 \\le |s| \\le 10^5$). Caracteres ASCII "
                    "imprimables uniquement.\n\n"
                    "**Sortie** : un seul entier.\n\n"
                    "**Indice** : sliding window avec dictionnaire "
                    "`last[c] = derniere position`. Quand on revoit `c`, "
                    "sauter $i$ a `max(i, last[c] + 1)`."
                ),
                "prompt_en": (
                    "Given a string $s$, find the **length** of the "
                    "longest substring **with no repeated character**.\n\n"
                    "**Input**: a single line, the string $s$ "
                    "($0 \\le |s| \\le 10^5$). Printable ASCII only.\n\n"
                    "**Output**: a single integer.\n\n"
                    "**Hint**: sliding window with `last[c] = last "
                    "index`. On seeing `c` again, jump $i$ to "
                    "`max(i, last[c] + 1)`."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    s = sys.stdin.readline().rstrip('\\n')\n"
                    "    # TODO: sliding window with last-seen dict.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "abcabcbb\n", "expected": "3\n", "is_sample": True},
                    {"input": "bbbbb\n",    "expected": "1\n", "is_sample": True},
                    {"input": "\n",         "expected": "0\n", "is_sample": False},
                    {"input": "a\n",        "expected": "1\n", "is_sample": False},
                    {"input": "pwwkew\n",   "expected": "3\n", "is_sample": False},
                    {"input": "abcdef\n",   "expected": "6\n", "is_sample": False},
                    {"input": "dvdf\n",     "expected": "3\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_SE_K_DISTINCT",
                "title_fr": "Sous-chaine avec au plus K caracteres distincts",
                "title_en": "Substring with at most K distinct chars",
                "prompt_fr": (
                    "Etant donnee une chaine $s$ et un entier $K$, trouver "
                    "la **longueur** de la plus longue sous-chaine "
                    "contenant **au plus $K$ caracteres distincts**.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $K$ ($0 \\le K \\le 26$)\n"
                    "- ligne 2 : la chaine $s$ ($0 \\le |s| \\le 10^5$, "
                    "ASCII imprimable)\n\n"
                    "**Sortie** : un seul entier.\n\n"
                    "**Indice** : compteur `cnt[c]` + nombre de cles avec "
                    "`cnt > 0`. Tant qu'il y en a $> K$, contracter par "
                    "la gauche."
                ),
                "prompt_en": (
                    "Given a string $s$ and integer $K$, find the "
                    "**length** of the longest substring containing **at "
                    "most $K$ distinct characters**.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $K$ ($0 \\le K \\le 26$)\n"
                    "- line 2: the string $s$ ($0 \\le |s| \\le 10^5$, "
                    "printable ASCII)\n\n"
                    "**Output**: a single integer.\n\n"
                    "**Hint**: counter `cnt[c]` + number of keys with "
                    "`cnt > 0`. While that exceeds $K$, contract from "
                    "the left."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split('\\n')\n"
                    "    k = int(data[0]) if data else 0\n"
                    "    s = data[1] if len(data) > 1 else ''\n"
                    "    # TODO: sliding window with frequency counter.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "2\neceba\n", "expected": "3\n", "is_sample": True},
                    {"input": "1\naaaaa\n", "expected": "5\n", "is_sample": True},
                    {"input": "0\nabc\n",   "expected": "0\n", "is_sample": False},
                    {"input": "0\n\n",      "expected": "0\n", "is_sample": False},
                    {"input": "3\nabcabcabc\n",
                     "expected": "9\n", "is_sample": False},
                    {"input": "2\nabaccc\n",
                     "expected": "4\n", "is_sample": False},
                    {"input": "10\nhello\n",
                     "expected": "5\n", "is_sample": False},
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
    "EX_SE_LOWERBOUND": r"""import sys
def main():
    data = sys.stdin.read().split()
    n, q = int(data[0]), int(data[1])
    a = list(map(int, data[2:2+n]))
    out = []
    for k in range(q):
        x = int(data[2+n+k])
        lo, hi = 0, n
        while lo < hi:
            mid = (lo + hi) // 2
            if a[mid] < x: lo = mid + 1
            else:          hi = mid
        out.append(str(lo))
    sys.stdout.write('\n'.join(out) + '\n')
main()
""",
    "EX_SE_FIRSTOCC": r"""import sys
from bisect import bisect_left, bisect_right
def main():
    data = sys.stdin.read().split()
    n = int(data[0])
    a = list(map(int, data[1:1+n]))
    x = int(data[1+n])
    lo = bisect_left(a, x)
    hi = bisect_right(a, x) - 1
    if lo < n and a[lo] == x:
        print(lo, hi)
    else:
        print(-1, -1)
main()
""",
    "EX_SE_ISQRT": r"""import sys
def main():
    n = int(sys.stdin.readline())
    lo, hi = 0, 10**9
    # Largest k with k*k <= n. Pattern search_max with +1 rounding.
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if mid * mid <= n: lo = mid
        else:              hi = mid - 1
    print(lo)
main()
""",
    "EX_SE_AGGRCOWS": r"""import sys
def main():
    data = sys.stdin.read().split()
    n, k = int(data[0]), int(data[1])
    x = sorted(map(int, data[2:2+n]))
    def feasible(d):
        last, cnt = x[0], 1
        for v in x[1:]:
            if v - last >= d:
                last = v; cnt += 1
                if cnt >= k: return True
        return cnt >= k
    lo, hi = 0, x[-1] - x[0]
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if feasible(mid): lo = mid
        else:             hi = mid - 1
    print(lo)
main()
""",
    "EX_SE_PAINTERS": r"""import sys
def main():
    data = sys.stdin.read().split()
    n, k = int(data[0]), int(data[1])
    L = list(map(int, data[2:2+n]))
    def feasible(T):
        painters, cur = 1, 0
        for l in L:
            if cur + l <= T: cur += l
            else:
                painters += 1
                cur = l
                if painters > k: return False
        return painters <= k
    lo, hi = max(L), sum(L)
    # Largest T NOT feasible - but we want smallest T feasible. search_min.
    while lo < hi:
        mid = (lo + hi) // 2
        if feasible(mid): hi = mid
        else:             lo = mid + 1
    print(lo)
main()
""",
    "EX_SE_SQRT_REAL": r"""import sys
def main():
    x = float(sys.stdin.readline())
    lo, hi = 0.0, max(1.0, x)
    for _ in range(100):
        mid = (lo + hi) / 2
        if mid * mid < x: lo = mid
        else:             hi = mid
    print(f"{(lo + hi) / 2:.6f}")
main()
""",
    "EX_SE_2SUM": r"""import sys
def main():
    data = sys.stdin.read().split()
    n, t = int(data[0]), int(data[1])
    a = list(map(int, data[2:2+n]))
    i, j = 0, n - 1
    ans = (-1, -1)
    while i < j:
        s = a[i] + a[j]
        if s == t:
            ans = (i, j); break
        elif s < t: i += 1
        else:       j -= 1
    print(ans[0], ans[1])
main()
""",
    "EX_SE_3SUM": r"""import sys
def main():
    data = sys.stdin.read().split()
    n = int(data[0])
    a = sorted(map(int, data[1:1+n]))
    out = []
    for i in range(n - 2):
        if i > 0 and a[i] == a[i-1]: continue
        T = -a[i]
        l, r = i + 1, n - 1
        while l < r:
            s = a[l] + a[r]
            if s == T:
                out.append(f"{a[i]} {a[l]} {a[r]}")
                l += 1; r -= 1
                while l < r and a[l] == a[l-1]: l += 1
                while l < r and a[r] == a[r+1]: r -= 1
            elif s < T: l += 1
            else:       r -= 1
    sys.stdout.write('\n'.join(out) + ('\n' if out else ''))
main()
""",
    "EX_SE_REMOVE_DUPS": r"""import sys
def main():
    data = sys.stdin.read().split()
    n = int(data[0]) if data else 0
    a = list(map(int, data[1:1+n]))
    if n == 0:
        print(0); print(''); return
    w = 1
    for j in range(1, n):
        if a[j] != a[w-1]:
            a[w] = a[j]; w += 1
    print(w)
    print(' '.join(map(str, a[:w])))
main()
""",
    "EX_SE_FIXEDSUM": r"""import sys
def main():
    data = sys.stdin.read().split()
    n, k = int(data[0]), int(data[1])
    a = list(map(int, data[2:2+n]))
    s = sum(a[:k])
    best = s
    for j in range(k, n):
        s += a[j] - a[j-k]
        if s > best: best = s
    print(best)
main()
""",
    "EX_SE_LONGEST_UNIQUE": r"""import sys
def main():
    s = sys.stdin.readline().rstrip('\n')
    last = {}
    i = 0
    best = 0
    for j, c in enumerate(s):
        if c in last and last[c] >= i:
            i = last[c] + 1
        last[c] = j
        if j - i + 1 > best:
            best = j - i + 1
    print(best)
main()
""",
    "EX_SE_K_DISTINCT": r"""import sys
def main():
    data = sys.stdin.read().split('\n')
    k = int(data[0]) if data and data[0] else 0
    s = data[1] if len(data) > 1 else ''
    if k == 0 or not s:
        print(0); return
    cnt = {}
    distinct = 0
    i = 0
    best = 0
    for j, c in enumerate(s):
        if cnt.get(c, 0) == 0: distinct += 1
        cnt[c] = cnt.get(c, 0) + 1
        while distinct > k:
            cnt[s[i]] -= 1
            if cnt[s[i]] == 0: distinct -= 1
            i += 1
        if j - i + 1 > best: best = j - i + 1
    print(best)
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


def _floats_close(actual: str, expected: str, tol: float) -> bool:
    """Loose comparator for the real-sqrt exercise. Compares each token
    pairwise; numeric tokens within ``tol`` count as equal."""
    a, b = actual.split(), expected.split()
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        try:
            if abs(float(x) - float(y)) <= tol: continue
            return False
        except ValueError:
            if x != y: return False
    return True


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
            ok = (actual == expected)
            # Float tolerance only for the real-sqrt exercise.
            if not ok and key == "EX_SE_SQRT_REAL":
                ok = _floats_close(actual, expected, tol=1e-4)
            if not ok:
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
# DB upsert (mirrors seed_chapter3 exactly so behavior is identical)    #
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
    print(f"Chapitre 4 - Recherche & invariants : OK ({state}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
