"""Seed Chapter 3 - Tris (algorithmique).

Cree (ou met a jour) la section ``tris`` avec quatre lecons :

  1. Tri par insertion & tri par fusion (preuve n log n complete)
  2. Tri rapide & tri par tas (analyse en esperance)
  3. Borne inferieure Omega(n log n) & tris lineaires
  4. Selection : quickselect & mediane des medianes

Chaque lecon contient trois exercices inline gradues. Idempotent.

Usage:
    python scripts/seed_chapter3/seed_chapter3.py
    python scripts/seed_chapter3/seed_chapter3.py --draft
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Iterable


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent.parent
CONTENT_DIR = HERE / "content"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


SECTION = {
    "slug": "tris",
    "title_fr": "Tris",
    "title_en": "Sorting",
    "description_fr": (
        "Tri par insertion, fusion (preuve n log n complète), tri rapide "
        "(analyse en espérance), tri par tas. Borne inférieure Ω(n log n) "
        "via arbre de décision. Tris linéaires (comptage, radix, bucket). "
        "Sélection : quickselect et médiane des médianes en O(n) "
        "déterministe."
    ),
    "description_en": (
        "Insertion sort, mergesort (full n log n proof), quicksort (expected "
        "analysis), heapsort. Ω(n log n) lower bound via decision trees. "
        "Linear sorts (counting, radix, bucket). Selection: quickselect and "
        "deterministic O(n) median of medians."
    ),
    "order_idx": 2,
}


LESSONS: list[dict] = [
    {
        "slug": "insertion-fusion",
        "title_fr": "Tri par insertion & tri par fusion",
        "title_en": "Insertion Sort & Merge Sort",
        "order_idx": 0,
        "content_fr_file": "lesson_01_insertion_fusion.fr.md",
        "content_en_file": "lesson_01_insertion_fusion.en.md",
        "exercises": [
            {
                "key": "EX_SO_MERGE2",
                "title_fr": "Fusion de deux tableaux triés",
                "title_en": "Merge two sorted arrays",
                "prompt_fr": (
                    "Étant donné deux tableaux **déjà triés** $A$ et $B$, "
                    "produire le tableau trié résultant de leur fusion.\n\n"
                    "**Entrée** :\n\n"
                    "- ligne 1 : $n$ et $m$ ($0 \\le n, m \\le 10^6$)\n"
                    "- ligne 2 : $n$ entiers (vide si $n=0$)\n"
                    "- ligne 3 : $m$ entiers (vide si $m=0$)\n\n"
                    "**Sortie** : les $n + m$ entiers triés, séparés par "
                    "des espaces.\n\n"
                    "**Indice** : deux index, un seul passage. Coût $O(n+m)$."
                ),
                "prompt_en": (
                    "Given two **already sorted** arrays $A$ and $B$, produce "
                    "the merged sorted array.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $m$ ($0 \\le n, m \\le 10^6$)\n"
                    "- line 2: $n$ integers (empty if $n=0$)\n"
                    "- line 3: $m$ integers (empty if $m=0$)\n\n"
                    "**Output**: the $n + m$ sorted integers, space-separated.\n\n"
                    "**Hint**: two indices, single pass. Cost $O(n+m)$."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n, m = int(data[0]), int(data[1])\n"
                    "    a = list(map(int, data[2:2+n]))\n"
                    "    b = list(map(int, data[2+n:2+n+m]))\n"
                    "    # TODO: two-pointer merge.\n"
                    "    print('')\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "3 3\n1 3 5\n2 4 6\n",
                     "expected": "1 2 3 4 5 6\n", "is_sample": True},
                    {"input": "4 0\n1 2 3 4\n\n",
                     "expected": "1 2 3 4\n", "is_sample": True},
                    {"input": "0 4\n\n5 6 7 8\n",
                     "expected": "5 6 7 8\n", "is_sample": False},
                    {"input": "5 5\n1 1 2 3 4\n0 1 5 6 9\n",
                     "expected": "0 1 1 1 2 3 4 5 6 9\n", "is_sample": False},
                    {"input": "1 1\n10\n5\n",
                     "expected": "5 10\n", "is_sample": False},
                    {"input": "3 3\n-3 0 7\n-5 4 9\n",
                     "expected": "-5 -3 0 4 7 9\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_SO_INVERSIONS",
                "title_fr": "Compter les inversions",
                "title_en": "Count inversions",
                "prompt_fr": (
                    "Une **inversion** d'un tableau $A$ est une paire $(i, j)$ "
                    "avec $i < j$ et $A[i] > A[j]$. Compter le nombre total "
                    "d'inversions.\n\n"
                    "**Entrée** :\n\n"
                    "- ligne 1 : $n$ ($1 \\le n \\le 10^5$)\n"
                    "- ligne 2 : $n$ entiers ($|a_i| \\le 10^9$)\n\n"
                    "**Sortie** : un seul entier - le nombre d'inversions.\n\n"
                    "**Indice** : la solution naïve est $O(n^2)$, trop lente. "
                    "Le tri par fusion les compte en $O(n \\log n)$ : à chaque "
                    "fusion, quand on prend un élément du tableau de droite, "
                    "ajouter le nombre d'éléments restants à gauche aux "
                    "inversions."
                ),
                "prompt_en": (
                    "An **inversion** of an array $A$ is a pair $(i, j)$ with "
                    "$i < j$ and $A[i] > A[j]$. Count the total number of "
                    "inversions.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($1 \\le n \\le 10^5$)\n"
                    "- line 2: $n$ integers ($|a_i| \\le 10^9$)\n\n"
                    "**Output**: one integer - the inversion count.\n\n"
                    "**Hint**: the naive solution is $O(n^2)$, too slow. "
                    "Mergesort counts them in $O(n \\log n)$: during each "
                    "merge, when picking an element from the right array, "
                    "add the number of remaining left elements to the count."
                ),
                "starter_code": (
                    "import sys\n"
                    "sys.setrecursionlimit(200000)\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0])\n"
                    "    a = list(map(int, data[1:1+n]))\n"
                    "    # TODO: mergesort that also returns the inversion count.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5\n2 4 1 3 5\n",
                     "expected": "3\n", "is_sample": True},
                    {"input": "4\n4 3 2 1\n",
                     "expected": "6\n", "is_sample": True},
                    {"input": "1\n42\n",
                     "expected": "0\n", "is_sample": False},
                    {"input": "5\n1 2 3 4 5\n",
                     "expected": "0\n", "is_sample": False},
                    {"input": "6\n6 5 4 3 2 1\n",
                     "expected": "15\n", "is_sample": False},
                    {"input": "3\n1 1 1\n",
                     "expected": "0\n", "is_sample": False},
                    {"input": "8\n3 1 4 1 5 9 2 6\n",
                     "expected": "8\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_SO_KMERGE",
                "title_fr": "Fusion de K listes triées",
                "title_en": "Merge K sorted lists",
                "prompt_fr": (
                    "Étant donné $K$ listes triées, produire le tableau trié "
                    "résultant de leur fusion globale.\n\n"
                    "**Entrée** :\n\n"
                    "- ligne 1 : $K$ ($1 \\le K \\le 10^5$)\n"
                    "- pour chaque liste $i$ :\n"
                    "  - ligne donnant la taille $s_i$\n"
                    "  - ligne donnant les $s_i$ entiers (vide si $s_i = 0$)\n\n"
                    "Total : $\\sum s_i \\le 10^6$.\n\n"
                    "**Sortie** : tous les éléments triés, sur une ligne, "
                    "séparés par des espaces.\n\n"
                    "**Indice** : un min-heap contenant un élément de chaque "
                    "liste donne $O(N \\log K)$ où $N = \\sum s_i$."
                ),
                "prompt_en": (
                    "Given $K$ sorted lists, output the merged sorted array.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $K$ ($1 \\le K \\le 10^5$)\n"
                    "- for each list $i$:\n"
                    "  - one line with the size $s_i$\n"
                    "  - one line with $s_i$ integers (empty if $s_i = 0$)\n\n"
                    "Total: $\\sum s_i \\le 10^6$.\n\n"
                    "**Output**: all elements sorted, on one line, "
                    "space-separated.\n\n"
                    "**Hint**: a min-heap holding one element per list gives "
                    "$O(N \\log K)$ with $N = \\sum s_i$."
                ),
                "starter_code": (
                    "import sys\n"
                    "import heapq\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().splitlines()\n"
                    "    k = int(data[0])\n"
                    "    arrs = []\n"
                    "    idx = 1\n"
                    "    for _ in range(k):\n"
                    "        size = int(data[idx]); idx += 1\n"
                    "        if size == 0:\n"
                    "            arrs.append([]); continue\n"
                    "        arrs.append(list(map(int, data[idx].split())))\n"
                    "        idx += 1\n"
                    "    # TODO: merge using a min-heap of (value, list_idx, pos).\n"
                    "    print('')\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "3\n3\n1 4 7\n3\n2 5 8\n3\n3 6 9\n",
                     "expected": "1 2 3 4 5 6 7 8 9\n", "is_sample": True},
                    {"input": "2\n2\n1 2\n3\n3 4 5\n",
                     "expected": "1 2 3 4 5\n", "is_sample": True},
                    {"input": "1\n3\n10 20 30\n",
                     "expected": "10 20 30\n", "is_sample": False},
                    {"input": "3\n1\n5\n1\n3\n1\n8\n",
                     "expected": "3 5 8\n", "is_sample": False},
                    {"input": "2\n4\n1 2 3 4\n0\n\n",
                     "expected": "1 2 3 4\n", "is_sample": False},
                ],
            },
        ],
    },
    {
        "slug": "quicksort-heapsort",
        "title_fr": "Tri rapide & tri par tas",
        "title_en": "Quicksort & Heapsort",
        "order_idx": 1,
        "content_fr_file": "lesson_02_quicksort_heapsort.fr.md",
        "content_en_file": "lesson_02_quicksort_heapsort.en.md",
        "exercises": [
            {
                "key": "EX_SO_PARTITION",
                "title_fr": "Partition de Lomuto",
                "title_en": "Lomuto partition",
                "prompt_fr": (
                    "Implémenter la partition de Lomuto avec **pivot = dernier "
                    "élément**. Sur le tableau partitionné, tous les éléments "
                    "à gauche du pivot sont $\\le$ pivot et tous ceux à droite "
                    "sont $>$ pivot.\n\n"
                    "**Entrée** :\n\n"
                    "- ligne 1 : $n$ ($1 \\le n \\le 10^5$)\n"
                    "- ligne 2 : $n$ entiers\n\n"
                    "**Sortie** :\n\n"
                    "- ligne 1 : la position **0-indexée** du pivot après partition\n"
                    "- ligne 2 : le tableau partitionné, séparé par des espaces\n\n"
                    "**Note** : suivre exactement le pseudo-code de la "
                    "leçon - d'autres ordres de swap donnent un tableau "
                    "valide mais différent."
                ),
                "prompt_en": (
                    "Implement Lomuto partition with **pivot = last element**. "
                    "After partitioning, all left-of-pivot elements are $\\le$ "
                    "pivot and all right-of-pivot elements are $>$ pivot.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($1 \\le n \\le 10^5$)\n"
                    "- line 2: $n$ integers\n\n"
                    "**Output**:\n\n"
                    "- line 1: pivot's **0-indexed** final position\n"
                    "- line 2: partitioned array, space-separated\n\n"
                    "**Note**: follow exactly the lesson pseudocode - different "
                    "swap orders give a valid but different layout."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0])\n"
                    "    a = list(map(int, data[1:1+n]))\n"
                    "    pivot = a[-1]\n"
                    "    i = 0\n"
                    "    # TODO: Lomuto partition (j scans, i is the boundary).\n"
                    "    print(0)\n"
                    "    print(' '.join(map(str, a)))\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5\n3 7 1 8 4\n",
                     "expected": "2\n3 1 4 8 7\n", "is_sample": True},
                    {"input": "6\n2 8 7 1 3 5\n",
                     "expected": "3\n2 1 3 5 7 8\n", "is_sample": True},
                    {"input": "1\n42\n",
                     "expected": "0\n42\n", "is_sample": False},
                    {"input": "3\n1 2 3\n",
                     "expected": "2\n1 2 3\n", "is_sample": False},
                    {"input": "4\n5 5 5 5\n",
                     "expected": "3\n5 5 5 5\n", "is_sample": False},
                    {"input": "5\n1 2 3 4 5\n",
                     "expected": "4\n1 2 3 4 5\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_SO_DUTCH",
                "title_fr": "Drapeau néerlandais (3-way partition)",
                "title_en": "Dutch national flag (3-way partition)",
                "prompt_fr": (
                    "On donne un tableau dont chaque élément vaut $0$, $1$ ou "
                    "$2$. Le trier **en place** en un seul passage. C'est "
                    "exactement le 3-way partitioning de Dijkstra, brique du "
                    "tri rapide à 3 voies utile quand l'entrée a beaucoup de "
                    "doublons.\n\n"
                    "**Entrée** :\n\n"
                    "- ligne 1 : $n$ ($1 \\le n \\le 10^6$)\n"
                    "- ligne 2 : $n$ valeurs dans $\\{0, 1, 2\\}$\n\n"
                    "**Sortie** : le tableau trié, séparé par des espaces.\n\n"
                    "**Algorithme** : trois pointeurs `lo`, `mid`, `hi`. "
                    "$0$ va à gauche de `lo`, $1$ entre `lo` et `mid`, $2$ "
                    "à droite de `hi`."
                ),
                "prompt_en": (
                    "Given an array of values in $\\{0, 1, 2\\}$, sort it "
                    "**in place** in one pass. This is exactly Dijkstra's "
                    "3-way partition, the building block of 3-way quicksort, "
                    "useful when the input has many duplicates.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($1 \\le n \\le 10^6$)\n"
                    "- line 2: $n$ values in $\\{0, 1, 2\\}$\n\n"
                    "**Output**: the sorted array, space-separated.\n\n"
                    "**Algorithm**: three pointers `lo`, `mid`, `hi`. $0$ goes "
                    "left of `lo`, $1$ between `lo` and `mid`, $2$ right of "
                    "`hi`."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0])\n"
                    "    a = list(map(int, data[1:1+n]))\n"
                    "    # TODO: three-way partition with lo / mid / hi.\n"
                    "    print(' '.join(map(str, a)))\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "9\n2 0 2 1 1 0 0 1 2\n",
                     "expected": "0 0 0 1 1 1 2 2 2\n", "is_sample": True},
                    {"input": "5\n0 0 0 0 0\n",
                     "expected": "0 0 0 0 0\n", "is_sample": True},
                    {"input": "5\n2 2 2 2 2\n",
                     "expected": "2 2 2 2 2\n", "is_sample": False},
                    {"input": "6\n2 1 0 2 1 0\n",
                     "expected": "0 0 1 1 2 2\n", "is_sample": False},
                    {"input": "1\n1\n",
                     "expected": "1\n", "is_sample": False},
                    {"input": "4\n2 0 1 0\n",
                     "expected": "0 0 1 2\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_SO_RUNMEDIAN",
                "title_fr": "Médiane glissante (en streaming)",
                "title_en": "Running median (streaming)",
                "prompt_fr": (
                    "On donne un flux d'entiers. À chaque préfixe de longueur "
                    "$1, 2, \\dots, n$, calculer la médiane.\n\n"
                    "Pour rester en arithmétique entière, **renvoyer "
                    "$2 \\times$ médiane** : si la longueur est impaire, c'est "
                    "$2 \\cdot a_{\\text{milieu}}$ ; si paire, c'est la somme "
                    "des deux valeurs centrales.\n\n"
                    "**Entrée** :\n\n"
                    "- ligne 1 : $n$ ($1 \\le n \\le 10^5$)\n"
                    "- ligne 2 : $n$ entiers ($|a_i| \\le 10^9$)\n\n"
                    "**Sortie** : les $n$ valeurs $2 \\times$ médiane, séparées "
                    "par des espaces.\n\n"
                    "**Algorithme cible** : deux tas - un max-heap pour la "
                    "moitié basse, un min-heap pour la moitié haute, équilibrés "
                    "à chaque insertion. Coût $O(n \\log n)$."
                ),
                "prompt_en": (
                    "Given a stream of integers, for each prefix of length "
                    "$1, 2, \\dots, n$ output the median.\n\n"
                    "To stay in integer arithmetic, **output $2 \\times$ "
                    "median**: odd-length prefix gives $2 \\cdot a_{\\text{mid}}$; "
                    "even-length gives the sum of the two central values.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($1 \\le n \\le 10^5$)\n"
                    "- line 2: $n$ integers ($|a_i| \\le 10^9$)\n\n"
                    "**Output**: the $n$ values of $2 \\times$ median, "
                    "space-separated.\n\n"
                    "**Target algorithm**: two heaps - a max-heap for the lower "
                    "half, a min-heap for the upper half, balanced after each "
                    "insertion. Cost $O(n \\log n)$."
                ),
                "starter_code": (
                    "import sys\n"
                    "import heapq\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0])\n"
                    "    a = list(map(int, data[1:1+n]))\n"
                    "    lo = []  # max-heap (negated)\n"
                    "    hi = []  # min-heap\n"
                    "    out = []\n"
                    "    # TODO: maintain |lo| - |hi| in {0, 1}; emit 2*median.\n"
                    "    print(' '.join(map(str, out)))\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5\n1 2 3 4 5\n",
                     "expected": "2 3 4 5 6\n", "is_sample": True},
                    {"input": "4\n4 1 3 2\n",
                     "expected": "8 5 6 5\n", "is_sample": True},
                    {"input": "1\n7\n",
                     "expected": "14\n", "is_sample": False},
                    {"input": "3\n1 1 1\n",
                     "expected": "2 2 2\n", "is_sample": False},
                    {"input": "6\n6 5 4 3 2 1\n",
                     "expected": "12 11 10 9 8 7\n", "is_sample": False},
                ],
            },
        ],
    },
    {
        "slug": "borne-inferieure-tris-lineaires",
        "title_fr": "Borne inférieure & tris linéaires",
        "title_en": "Lower bound & linear sorts",
        "order_idx": 2,
        "content_fr_file": "lesson_03_lower_bound_linear.fr.md",
        "content_en_file": "lesson_03_lower_bound_linear.en.md",
        "exercises": [
            {
                "key": "EX_SO_COUNTING",
                "title_fr": "Tri par comptage",
                "title_en": "Counting sort",
                "prompt_fr": (
                    "Implémenter le **tri par comptage** sur des entiers "
                    "dans $[0, k]$.\n\n"
                    "**Entrée** :\n\n"
                    "- ligne 1 : $n$ et $k$ ($1 \\le n \\le 10^6$, "
                    "$0 \\le k \\le 10^6$)\n"
                    "- ligne 2 : $n$ entiers, chacun dans $[0, k]$\n\n"
                    "**Sortie** : le tableau trié, séparé par des espaces.\n\n"
                    "**Coût attendu** : $\\Theta(n + k)$. Une approche par "
                    "tri standard $O(n \\log n)$ est aussi acceptée mais "
                    "passe à côté de l'objectif pédagogique."
                ),
                "prompt_en": (
                    "Implement **counting sort** on integers in $[0, k]$.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $k$ ($1 \\le n \\le 10^6$, "
                    "$0 \\le k \\le 10^6$)\n"
                    "- line 2: $n$ integers, each in $[0, k]$\n\n"
                    "**Output**: sorted array, space-separated.\n\n"
                    "**Target cost**: $\\Theta(n + k)$. Standard $O(n \\log n)$ "
                    "is accepted but misses the pedagogical point."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n, k = int(data[0]), int(data[1])\n"
                    "    a = list(map(int, data[2:2+n]))\n"
                    "    # TODO: counting sort.\n"
                    "    print('')\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5 5\n3 1 4 1 5\n",
                     "expected": "1 1 3 4 5\n", "is_sample": True},
                    {"input": "6 9\n3 1 4 1 5 9\n",
                     "expected": "1 1 3 4 5 9\n", "is_sample": True},
                    {"input": "1 0\n0\n",
                     "expected": "0\n", "is_sample": False},
                    {"input": "4 3\n2 0 3 1\n",
                     "expected": "0 1 2 3\n", "is_sample": False},
                    {"input": "8 1\n0 1 0 1 1 0 1 0\n",
                     "expected": "0 0 0 0 1 1 1 1\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_SO_RADIX",
                "title_fr": "Tri par base (radix LSD)",
                "title_en": "Radix sort (LSD)",
                "prompt_fr": (
                    "Trier des **entiers non-négatifs** par radix LSD en "
                    "base 10.\n\n"
                    "**Entrée** :\n\n"
                    "- ligne 1 : $n$ ($1 \\le n \\le 10^6$)\n"
                    "- ligne 2 : $n$ entiers dans $[0, 10^9]$\n\n"
                    "**Sortie** : le tableau trié, séparé par des espaces.\n\n"
                    "**Coût attendu** : $\\Theta(n \\cdot d)$ où $d$ est le "
                    "nombre de chiffres."
                ),
                "prompt_en": (
                    "Sort **non-negative integers** by LSD radix sort in "
                    "base 10.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($1 \\le n \\le 10^6$)\n"
                    "- line 2: $n$ integers in $[0, 10^9]$\n\n"
                    "**Output**: sorted array, space-separated.\n\n"
                    "**Target cost**: $\\Theta(n \\cdot d)$ where $d$ is the "
                    "digit count."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0])\n"
                    "    a = list(map(int, data[1:1+n]))\n"
                    "    # TODO: LSD radix sort.\n"
                    "    print('')\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5\n170 45 75 90 802\n",
                     "expected": "45 75 90 170 802\n", "is_sample": True},
                    {"input": "4\n329 457 657 839\n",
                     "expected": "329 457 657 839\n", "is_sample": True},
                    {"input": "1\n42\n",
                     "expected": "42\n", "is_sample": False},
                    {"input": "6\n100 1 10 1000 10000 100000\n",
                     "expected": "1 10 100 1000 10000 100000\n", "is_sample": False},
                    {"input": "5\n0 0 0 0 0\n",
                     "expected": "0 0 0 0 0\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_SO_RADIX_STR",
                "title_fr": "Radix sur chaînes de longueur fixe",
                "title_en": "Radix on fixed-length strings",
                "prompt_fr": (
                    "Trier $n$ chaînes de **même longueur** $d$, composées "
                    "uniquement de minuscules `a-z`, par radix LSD.\n\n"
                    "**Entrée** :\n\n"
                    "- ligne 1 : $n$ et $d$ ($1 \\le n \\le 10^5$, "
                    "$1 \\le d \\le 20$)\n"
                    "- ligne 2 : les $n$ chaînes séparées par des espaces\n\n"
                    "**Sortie** : les $n$ chaînes triées lexicographiquement, "
                    "séparées par des espaces.\n\n"
                    "**Indice** : un counting sort stable par caractère, du "
                    "dernier au premier. Tri stable garantit la correction."
                ),
                "prompt_en": (
                    "Sort $n$ strings of **same length** $d$, made of "
                    "lowercase `a-z` only, using LSD radix sort.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $d$ ($1 \\le n \\le 10^5$, "
                    "$1 \\le d \\le 20$)\n"
                    "- line 2: the $n$ strings, space-separated\n\n"
                    "**Output**: the $n$ strings sorted lexicographically, "
                    "space-separated.\n\n"
                    "**Hint**: stable counting sort per character, last digit "
                    "to first. Stability ensures correctness."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n, d = int(data[0]), int(data[1])\n"
                    "    a = data[2:2+n]\n"
                    "    # TODO: LSD radix on characters.\n"
                    "    print(' '.join(a))\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "4 3\nabc bca cab aaa\n",
                     "expected": "aaa abc bca cab\n", "is_sample": True},
                    {"input": "5 2\nbb aa bc ab cd\n",
                     "expected": "aa ab bb bc cd\n", "is_sample": True},
                    {"input": "1 4\nabcd\n",
                     "expected": "abcd\n", "is_sample": False},
                    {"input": "3 1\nb a c\n",
                     "expected": "a b c\n", "is_sample": False},
                    {"input": "4 3\nzzz aaa zaz aza\n",
                     "expected": "aaa aza zaz zzz\n", "is_sample": False},
                ],
            },
        ],
    },
    {
        "slug": "selection",
        "title_fr": "Sélection : quickselect & médiane des médianes",
        "title_en": "Selection: quickselect & median of medians",
        "order_idx": 3,
        "content_fr_file": "lesson_04_selection.fr.md",
        "content_en_file": "lesson_04_selection.en.md",
        "exercises": [
            {
                "key": "EX_SO_SELECT",
                "title_fr": "k-ème plus petit (quickselect)",
                "title_en": "k-th smallest (quickselect)",
                "prompt_fr": (
                    "Étant donné un tableau de $n$ entiers et un entier $k$ "
                    "($1 \\le k \\le n$), retourner le **$k$-ème plus petit** "
                    "élément.\n\n"
                    "**Entrée** :\n\n"
                    "- ligne 1 : $n$ et $k$ ($1 \\le k \\le n \\le 10^6$)\n"
                    "- ligne 2 : $n$ entiers ($|a_i| \\le 10^9$)\n\n"
                    "**Sortie** : un seul entier.\n\n"
                    "**Algorithme cible** : quickselect, $\\Theta(n)$ en "
                    "espérance. Tri puis indexation aussi accepté pour ces "
                    "tailles."
                ),
                "prompt_en": (
                    "Given an array of $n$ integers and $k$ ($1 \\le k \\le n$), "
                    "return the **$k$-th smallest** element.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $k$ ($1 \\le k \\le n \\le 10^6$)\n"
                    "- line 2: $n$ integers ($|a_i| \\le 10^9$)\n\n"
                    "**Output**: one integer.\n\n"
                    "**Target algorithm**: quickselect, $\\Theta(n)$ expected. "
                    "Sort+index also accepted for these sizes."
                ),
                "starter_code": (
                    "import sys, random\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n, k = int(data[0]), int(data[1])\n"
                    "    a = list(map(int, data[2:2+n]))\n"
                    "    # TODO: quickselect (or sorted(a)[k-1]).\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5 3\n3 1 4 1 5\n",
                     "expected": "3\n", "is_sample": True},
                    {"input": "7 5\n9 4 7 1 3 8 2\n",
                     "expected": "7\n", "is_sample": True},
                    {"input": "1 1\n42\n",
                     "expected": "42\n", "is_sample": False},
                    {"input": "5 5\n5 4 3 2 1\n",
                     "expected": "5\n", "is_sample": False},
                    {"input": "6 1\n3 6 1 2 5 4\n",
                     "expected": "1\n", "is_sample": False},
                    {"input": "8 4\n8 7 6 5 4 3 2 1\n",
                     "expected": "4\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_SO_MINMAX",
                "title_fr": "Min et max simultanés",
                "title_en": "Simultaneous min and max",
                "prompt_fr": (
                    "Trouver **le minimum et le maximum** d'un tableau de "
                    "$n$ entiers.\n\n"
                    "L'approche naïve fait $2(n-1)$ comparaisons. La version "
                    "optimale n'en fait que $\\lceil 3n/2 \\rceil - 2$ : "
                    "comparer les éléments **par paires**, puis comparer le "
                    "plus petit de la paire au min courant et le plus grand "
                    "au max courant. C'est l'occasion de réduire les "
                    "constantes plutôt que l'asymptotique.\n\n"
                    "**Entrée** :\n\n"
                    "- ligne 1 : $n$ ($1 \\le n \\le 10^6$)\n"
                    "- ligne 2 : $n$ entiers\n\n"
                    "**Sortie** : `min max` séparés par un espace, sur une ligne."
                ),
                "prompt_en": (
                    "Find **the minimum and maximum** of an array of $n$ "
                    "integers.\n\n"
                    "Naive: $2(n-1)$ comparisons. Optimal: only "
                    "$\\lceil 3n/2 \\rceil - 2$ - compare elements **in pairs**, "
                    "then compare the smaller of the pair to the running min "
                    "and the larger to the running max. This is about cutting "
                    "constants rather than asymptotics.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($1 \\le n \\le 10^6$)\n"
                    "- line 2: $n$ integers\n\n"
                    "**Output**: `min max` on one line, space-separated."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0])\n"
                    "    a = list(map(int, data[1:1+n]))\n"
                    "    # TODO: pair-wise compare for min and max.\n"
                    "    print(min(a), max(a))\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5\n3 1 4 1 5\n",
                     "expected": "1 5\n", "is_sample": True},
                    {"input": "1\n42\n",
                     "expected": "42 42\n", "is_sample": True},
                    {"input": "4\n7 7 7 7\n",
                     "expected": "7 7\n", "is_sample": False},
                    {"input": "6\n-3 -1 -5 0 2 -2\n",
                     "expected": "-5 2\n", "is_sample": False},
                    {"input": "3\n1000000000 -1000000000 0\n",
                     "expected": "-1000000000 1000000000\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_SO_TOPK",
                "title_fr": "Les k plus petits, triés",
                "title_en": "The k smallest, sorted",
                "prompt_fr": (
                    "Étant donné $n$ entiers et un entier $k$ ($1 \\le k \\le n$), "
                    "afficher les $k$ **plus petits**, triés croissants.\n\n"
                    "**Entrée** :\n\n"
                    "- ligne 1 : $n$ et $k$ ($1 \\le k \\le n \\le 10^6$)\n"
                    "- ligne 2 : $n$ entiers\n\n"
                    "**Sortie** : les $k$ plus petits sur une ligne, séparés "
                    "par des espaces, en ordre croissant.\n\n"
                    "**Indice** : *quickselect partiel*. Après quickselect "
                    "trouvant le $k$-ème, on a un préfixe non trié des $k$ "
                    "plus petits. Le trier coûte $O(k \\log k)$. Total "
                    "$O(n + k \\log k)$ - meilleur que $O(n \\log n)$ quand "
                    "$k \\ll n$."
                ),
                "prompt_en": (
                    "Given $n$ integers and $k$ ($1 \\le k \\le n$), print the "
                    "$k$ **smallest**, sorted ascending.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $k$ ($1 \\le k \\le n \\le 10^6$)\n"
                    "- line 2: $n$ integers\n\n"
                    "**Output**: the $k$ smallest on one line, space-separated, "
                    "ascending order.\n\n"
                    "**Hint**: *partial quickselect*. After quickselect on the "
                    "$k$-th, you have an unsorted prefix of the $k$ smallest. "
                    "Sort it for $O(k \\log k)$. Total $O(n + k \\log k)$ - "
                    "beats $O(n \\log n)$ when $k \\ll n$."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n, k = int(data[0]), int(data[1])\n"
                    "    a = list(map(int, data[2:2+n]))\n"
                    "    # TODO: quickselect on k-th, then sort the prefix.\n"
                    "    print('')\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5 3\n5 4 3 2 1\n",
                     "expected": "1 2 3\n", "is_sample": True},
                    {"input": "8 4\n7 2 9 4 1 6 3 8\n",
                     "expected": "1 2 3 4\n", "is_sample": True},
                    {"input": "1 1\n42\n",
                     "expected": "42\n", "is_sample": False},
                    {"input": "4 1\n10 20 30 40\n",
                     "expected": "10\n", "is_sample": False},
                    {"input": "5 5\n3 1 4 1 5\n",
                     "expected": "1 1 3 4 5\n", "is_sample": False},
                    {"input": "6 2\n100 50 25 10 5 1\n",
                     "expected": "1 5\n", "is_sample": False},
                ],
            },
        ],
    },
]


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
        snippet = content[i : i + 30]
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
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.db:
        os.environ["DATABASE_URL"] = args.db

    from backend import models  # noqa
    from backend.database import SessionLocal  # noqa

    publish = not args.draft

    db = SessionLocal()
    try:
        section = upsert_section(db, models, publish=publish)
        print(f"  [ok]section {section.slug!r} (id={section.id})")

        for lesson_data in LESSONS:
            lesson, created = upsert_lesson(
                db, models, section, lesson_data, publish=publish,
            )
            verb = "created" if created else "updated"
            print(f"    [ok]lesson {lesson.slug!r} {verb} (id={lesson.id})")

            reset_exercises(db, models, lesson)
            placeholders: dict[str, int] = {}
            for ex in lesson_data["exercises"]:
                ex_id = create_exercise(db, models, lesson, ex)
                placeholders[ex["key"]] = ex_id
                print(
                    f"      - exercise {ex['key']:<18} "
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
    print(f"Chapitre 3 - Tris : OK ({state}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
