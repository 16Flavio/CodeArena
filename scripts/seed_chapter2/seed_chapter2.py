"""Seed Chapter 2 - Structures de donnees elementaires (algorithmique).

Cree (ou met a jour) la section ``structures-de-donnees`` avec quatre
lecons :

  1. Tableaux, listes chainees, piles, files, deques
  2. Tables de hachage (universel, chainage / sondage lineaire)
  3. Arbres binaires de recherche & equilibrage (AVL)
  4. Tas binaires & heapsort

Chaque lecon contient trois exercices inline gradues (standard / twist
/ dur). Les contenus markdown FR + EN vivent dans ``content/``.

Idempotent : on retrouve la section/lecons par slug, on remplace les
exercices d'une lecon a chaque execution. Les progressions etudiantes
restent intactes.

Usage:

    python scripts/seed_chapter2/seed_chapter2.py
    python scripts/seed_chapter2/seed_chapter2.py --draft
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
    "slug": "structures-de-donnees",
    "title_fr": "Structures de données élémentaires",
    "title_en": "Elementary Data Structures",
    "description_fr": (
        "Tableaux, listes chaînées, piles, files, deques. Tables de "
        "hachage (universel, chaînage vs sondage). BST + AVL avec "
        "rotations. Tas binaires et heapsort."
    ),
    "description_en": (
        "Arrays, linked lists, stacks, queues, deques. Hash tables "
        "(universal hashing, chaining vs probing). BST + AVL with "
        "rotations. Binary heaps and heapsort."
    ),
    # Vient apres le chapitre 1 (order_idx=0).
    "order_idx": 1,
}


LESSONS: list[dict] = [
    {
        "slug": "tableaux-listes-deques",
        "title_fr": "Tableaux, listes chaînées, piles, files, deques",
        "title_en": "Arrays, Linked Lists, Stacks, Queues, Deques",
        "order_idx": 0,
        "content_fr_file": "lesson_01_arrays_lists.fr.md",
        "content_en_file": "lesson_01_arrays_lists.en.md",
        "exercises": [
            {
                "key": "EX_DS_QUEUE",
                "title_fr": "File implémentée avec deux piles",
                "title_en": "Queue with two stacks",
                "prompt_fr": (
                    "Implémenter une file FIFO en utilisant **deux piles**.\n\n"
                    "**Entrée** :\n\n"
                    "- ligne 1 : entier $q$ ($1 \\le q \\le 10^5$), nombre d'opérations\n"
                    "- $q$ lignes suivantes :\n"
                    "  - `P x` : enqueue de la valeur $x$ (chaîne sans espace)\n"
                    "  - `D`   : dequeue - afficher l'élément retiré (ou `EMPTY` si la file est vide)\n\n"
                    "**Sortie** : pour chaque opération `D`, une ligne avec la valeur "
                    "(ou `EMPTY`).\n\n"
                    "**Indice** : voir le pseudo-code de la leçon. Coût amorti $O(q)$ "
                    "sur $q$ opérations."
                ),
                "prompt_en": (
                    "Implement a FIFO queue using **two stacks**.\n\n"
                    "**Input**:\n\n"
                    "- line 1: integer $q$ ($1 \\le q \\le 10^5$), operation count\n"
                    "- next $q$ lines:\n"
                    "  - `P x`: enqueue value $x$ (a non-whitespace token)\n"
                    "  - `D`  : dequeue - print the removed element (or `EMPTY` if the queue is empty)\n\n"
                    "**Output**: for each `D` op, one line with the value (or `EMPTY`).\n\n"
                    "**Hint**: see the lesson pseudocode. Amortized cost $O(q)$ over "
                    "$q$ ops."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().splitlines()\n"
                    "    q = int(data[0])\n"
                    "    in_, out_ = [], []\n"
                    "    out = []\n"
                    "    for i in range(1, q + 1):\n"
                    "        parts = data[i].split()\n"
                    "        # TODO: handle 'P x' and 'D'.\n"
                    "    sys.stdout.write('\\n'.join(out) + ('\\n' if out else ''))\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5\nP 1\nP 2\nD\nP 3\nD\n",
                     "expected": "1\n2\n", "is_sample": True},
                    {"input": "3\nD\nP 5\nD\n",
                     "expected": "EMPTY\n5\n", "is_sample": True},
                    {"input": "6\nP a\nP b\nP c\nD\nD\nD\n",
                     "expected": "a\nb\nc\n", "is_sample": False},
                    {"input": "1\nD\n",
                     "expected": "EMPTY\n", "is_sample": False},
                    {"input": "4\nP 10\nD\nP 20\nD\n",
                     "expected": "10\n20\n", "is_sample": False},
                    {"input": "8\nP 1\nP 2\nD\nP 3\nP 4\nD\nD\nD\n",
                     "expected": "1\n2\n3\n4\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_DS_SLIDING",
                "title_fr": "Maximum sur fenêtre glissante",
                "title_en": "Sliding window maximum",
                "prompt_fr": (
                    "Soit un tableau $a[0..n[$ et une fenêtre de taille $k$. "
                    "Pour chaque position $i \\in [0, n-k]$, calculer "
                    "$\\max(a[i..i+k[)$.\n\n"
                    "**Entrée** :\n\n"
                    "- ligne 1 : $n$ et $k$ ($1 \\le k \\le n \\le 2\\cdot 10^5$)\n"
                    "- ligne 2 : $n$ entiers ($-10^9 \\le a_i \\le 10^9$)\n\n"
                    "**Sortie** : les $n - k + 1$ maximums sur une seule ligne, "
                    "séparés par des espaces.\n\n"
                    "**Algorithme cible** : deque monotone décroissante, $O(n)$ amorti. "
                    "Une approche naïve en $O(n\\,k)$ n'est pas assez rapide."
                ),
                "prompt_en": (
                    "Given an array $a[0..n[$ and a window size $k$, for each "
                    "position $i \\in [0, n-k]$ compute "
                    "$\\max(a[i..i+k[)$.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $k$ ($1 \\le k \\le n \\le 2\\cdot 10^5$)\n"
                    "- line 2: $n$ integers ($-10^9 \\le a_i \\le 10^9$)\n\n"
                    "**Output**: the $n - k + 1$ maxima on a single line, "
                    "space-separated.\n\n"
                    "**Target algorithm**: monotone decreasing deque, $O(n)$ amortized. "
                    "A naive $O(n\\,k)$ approach is too slow."
                ),
                "starter_code": (
                    "import sys\n"
                    "from collections import deque\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n, k = int(data[0]), int(data[1])\n"
                    "    a = list(map(int, data[2:2 + n]))\n"
                    "    # TODO: monotone deque sliding window maximum.\n"
                    "    print('')\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "8 3\n1 3 -1 -3 5 3 6 7\n",
                     "expected": "3 3 5 5 6 7\n", "is_sample": True},
                    {"input": "5 1\n5 4 3 2 1\n",
                     "expected": "5 4 3 2 1\n", "is_sample": True},
                    {"input": "5 5\n5 4 3 2 1\n",
                     "expected": "5\n", "is_sample": False},
                    {"input": "1 1\n42\n",
                     "expected": "42\n", "is_sample": False},
                    {"input": "6 2\n2 1 5 4 3 6\n",
                     "expected": "2 5 5 4 6\n", "is_sample": False},
                    {"input": "7 4\n1 2 3 4 3 2 1\n",
                     "expected": "4 4 4 4\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_DS_JOSEPHUS",
                "title_fr": "Le survivant de Josephus",
                "title_en": "Josephus survivor",
                "prompt_fr": (
                    "$n$ personnes numérotées de $1$ à $n$ se tiennent en cercle. "
                    "On compte $k$ personnes et on élimine la $k$-ème ; on "
                    "recommence à partir de la suivante jusqu'à ce qu'il n'en "
                    "reste qu'une. Calculer le numéro (1-indexé) du survivant.\n\n"
                    "**Entrée** : deux entiers $n$ et $k$ ($1 \\le n \\le 10^7$, "
                    "$1 \\le k \\le 10^9$).\n\n"
                    "**Sortie** : le numéro du survivant.\n\n"
                    "**Indice** : la formule récursive\n\n"
                    "$$J(1, k) = 0,\\quad J(m, k) = (J(m-1, k) + k) \\bmod m$$\n\n"
                    "donne la position 0-indexée. Itérer pour éviter le débordement "
                    "de pile."
                ),
                "prompt_en": (
                    "$n$ people numbered $1$ to $n$ stand in a circle. We count "
                    "$k$ people and eliminate the $k$-th; we start again from the "
                    "next one until only one remains. Compute the (1-indexed) "
                    "number of the survivor.\n\n"
                    "**Input**: two integers $n$ and $k$ ($1 \\le n \\le 10^7$, "
                    "$1 \\le k \\le 10^9$).\n\n"
                    "**Output**: the survivor's number.\n\n"
                    "**Hint**: the recursive formula\n\n"
                    "$$J(1, k) = 0,\\quad J(m, k) = (J(m-1, k) + k) \\bmod m$$\n\n"
                    "gives the 0-indexed position. Iterate to avoid stack overflow."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    n, k = map(int, sys.stdin.read().split())\n"
                    "    # TODO: iteratively compute J(n, k) and print survivor.\n"
                    "    print(1)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "1 1\n", "expected": "1\n", "is_sample": True},
                    {"input": "5 3\n", "expected": "4\n", "is_sample": True},
                    {"input": "2 2\n", "expected": "1\n", "is_sample": False},
                    {"input": "7 2\n", "expected": "7\n", "is_sample": False},
                    {"input": "10 5\n", "expected": "3\n", "is_sample": False},
                    {"input": "100 7\n", "expected": "50\n", "is_sample": False},
                    {"input": "10000 1000\n", "expected": "5981\n", "is_sample": False},
                    {"input": "1000000 999999999\n",
                     "expected": "266898\n", "is_sample": False},
                ],
            },
        ],
    },
    {
        "slug": "tables-hachage",
        "title_fr": "Tables de hachage",
        "title_en": "Hash Tables",
        "order_idx": 1,
        "content_fr_file": "lesson_02_hashing.fr.md",
        "content_en_file": "lesson_02_hashing.en.md",
        "exercises": [
            {
                "key": "EX_HT_DISTINCT",
                "title_fr": "Compter les valeurs distinctes",
                "title_en": "Count distinct values",
                "prompt_fr": (
                    "Étant donné $n$ entiers, retourner le nombre de valeurs "
                    "**distinctes**.\n\n"
                    "**Entrée** :\n\n"
                    "- ligne 1 : $n$ ($1 \\le n \\le 10^6$)\n"
                    "- ligne 2 : $n$ entiers séparés par des espaces ($|a_i| \\le 10^9$)\n\n"
                    "**Sortie** : un seul entier - le nombre de distincts."
                ),
                "prompt_en": (
                    "Given $n$ integers, return the count of **distinct** values.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($1 \\le n \\le 10^6$)\n"
                    "- line 2: $n$ space-separated integers ($|a_i| \\le 10^9$)\n\n"
                    "**Output**: one integer - the number of distinct values."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0])\n"
                    "    vals = list(map(int, data[1:1 + n]))\n"
                    "    # TODO: print the number of distinct values.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5\n1 2 3 2 1\n", "expected": "3\n", "is_sample": True},
                    {"input": "1\n42\n", "expected": "1\n", "is_sample": True},
                    {"input": "10\n7 7 7 7 7 7 7 7 7 7\n",
                     "expected": "1\n", "is_sample": False},
                    {"input": "8\n1 2 3 4 5 6 7 8\n",
                     "expected": "8\n", "is_sample": False},
                    {"input": "6\n-1 -2 -1 0 0 5\n",
                     "expected": "4\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_HT_TWOSUM",
                "title_fr": "Two-Sum",
                "title_en": "Two-Sum",
                "prompt_fr": (
                    "Étant donné un tableau et une cible $t$, trouver les indices "
                    "1-indexés $i < j$ tels que $a[i] + a[j] = t$. S'il y a "
                    "plusieurs solutions, retourner celle dont $j$ est minimal "
                    "(la première complétée en parcourant de gauche à droite).\n\n"
                    "**Entrée** :\n\n"
                    "- ligne 1 : $n$ et $t$ ($1 \\le n \\le 10^6$, $|t| \\le 2 \\cdot 10^9$)\n"
                    "- ligne 2 : $n$ entiers ($|a_i| \\le 10^9$)\n\n"
                    "**Sortie** :\n\n"
                    "- `i j` (séparés par un espace) si une solution existe,\n"
                    "- `NONE` sinon.\n\n"
                    "**Indice** : un dictionnaire valeur → premier indice donne "
                    "$O(n)$."
                ),
                "prompt_en": (
                    "Given an array and a target $t$, find 1-indexed $i < j$ "
                    "such that $a[i] + a[j] = t$. If multiple, return the pair "
                    "with smallest $j$ (the first one completed scanning left to "
                    "right).\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $t$ ($1 \\le n \\le 10^6$, $|t| \\le 2 \\cdot 10^9$)\n"
                    "- line 2: $n$ integers ($|a_i| \\le 10^9$)\n\n"
                    "**Output**:\n\n"
                    "- `i j` (space-separated) if a solution exists,\n"
                    "- `NONE` otherwise.\n\n"
                    "**Hint**: a dictionary value → earliest index gives $O(n)$."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n, t = int(data[0]), int(data[1])\n"
                    "    a = list(map(int, data[2:2 + n]))\n"
                    "    # TODO: scan once with a hash map.\n"
                    "    print('NONE')\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "4 7\n1 2 3 5\n", "expected": "2 4\n", "is_sample": True},
                    {"input": "5 100\n1 2 3 4 5\n",
                     "expected": "NONE\n", "is_sample": True},
                    {"input": "3 0\n-1 1 0\n",
                     "expected": "1 2\n", "is_sample": False},
                    {"input": "2 8\n5 3\n",
                     "expected": "1 2\n", "is_sample": False},
                    {"input": "6 10\n1 2 3 4 5 6\n",
                     "expected": "4 6\n", "is_sample": False},
                    {"input": "1 5\n5\n",
                     "expected": "NONE\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_HT_ZEROSUM",
                "title_fr": "Plus court sous-tableau de somme nulle",
                "title_en": "Shortest zero-sum subarray",
                "prompt_fr": (
                    "Soit un tableau $a[0..n[$ d'entiers (positifs ou négatifs). "
                    "Trouver la longueur du **plus court** sous-tableau contigu "
                    "non vide dont la somme vaut $0$. S'il n'en existe pas, "
                    "afficher `-1`.\n\n"
                    "**Entrée** :\n\n"
                    "- ligne 1 : $n$ ($1 \\le n \\le 10^6$)\n"
                    "- ligne 2 : $n$ entiers ($|a_i| \\le 10^9$)\n\n"
                    "**Sortie** : la longueur, ou `-1`.\n\n"
                    "**Indice** : sommes préfixes + dictionnaire (préfixe → "
                    "**dernier** indice). Solution attendue : $O(n)$."
                ),
                "prompt_en": (
                    "Given an array $a[0..n[$ of (signed) integers, find the "
                    "**shortest** non-empty contiguous subarray summing to $0$. "
                    "If none exists, print `-1`.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($1 \\le n \\le 10^6$)\n"
                    "- line 2: $n$ integers ($|a_i| \\le 10^9$)\n\n"
                    "**Output**: the length, or `-1`.\n\n"
                    "**Hint**: prefix sums + dictionary (prefix → **most recent** "
                    "index). Target: $O(n)$."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0])\n"
                    "    a = list(map(int, data[1:1 + n]))\n"
                    "    # TODO: prefix sums + dict (sum -> most recent index)\n"
                    "    print(-1)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5\n3 -3 1 2 -3\n",
                     "expected": "2\n", "is_sample": True},
                    {"input": "4\n1 2 3 4\n",
                     "expected": "-1\n", "is_sample": True},
                    {"input": "1\n0\n",
                     "expected": "1\n", "is_sample": False},
                    {"input": "6\n1 -1 2 -2 3 -3\n",
                     "expected": "2\n", "is_sample": False},
                    {"input": "5\n-5 5 0 0 1\n",
                     "expected": "1\n", "is_sample": False},
                    {"input": "3\n1 0 1\n",
                     "expected": "1\n", "is_sample": False},
                ],
            },
        ],
    },
    {
        "slug": "bst-avl",
        "title_fr": "Arbres binaires de recherche & équilibrage (AVL)",
        "title_en": "Binary Search Trees & Balancing (AVL)",
        "order_idx": 2,
        "content_fr_file": "lesson_03_bst_avl.fr.md",
        "content_en_file": "lesson_03_bst_avl.en.md",
        "exercises": [
            {
                "key": "EX_BST_INORDER",
                "title_fr": "Parcours in-order d'un BST",
                "title_en": "BST in-order traversal",
                "prompt_fr": (
                    "Insérer une suite d'entiers dans un BST naïf (les doublons "
                    "sont ignorés), puis afficher le **parcours in-order** des "
                    "clés.\n\n"
                    "**Entrée** :\n\n"
                    "- ligne 1 : $n$ ($1 \\le n \\le 10^5$)\n"
                    "- ligne 2 : $n$ entiers à insérer dans l'ordre ($|a_i| \\le 10^9$)\n\n"
                    "**Sortie** : les clés du BST en ordre croissant, séparées par "
                    "des espaces, sur une ligne.\n\n"
                    "**Indice** : sans doublons, l'in-order produit toujours la "
                    "suite triée des entrées distinctes."
                ),
                "prompt_en": (
                    "Insert a sequence of integers into a plain BST (duplicates "
                    "ignored), then print the **in-order traversal**.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($1 \\le n \\le 10^5$)\n"
                    "- line 2: $n$ integers to insert in order ($|a_i| \\le 10^9$)\n\n"
                    "**Output**: keys in ascending order, space-separated, on one line.\n\n"
                    "**Hint**: with no duplicates, in-order is always the sorted "
                    "list of distinct inputs."
                ),
                "starter_code": (
                    "import sys\n"
                    "sys.setrecursionlimit(200000)\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0])\n"
                    "    a = list(map(int, data[1:1 + n]))\n"
                    "    # TODO: build BST iteratively, then in-order traversal.\n"
                    "    print('')\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5\n3 1 4 1 5\n",
                     "expected": "1 3 4 5\n", "is_sample": True},
                    {"input": "7\n5 3 7 1 4 6 8\n",
                     "expected": "1 3 4 5 6 7 8\n", "is_sample": True},
                    {"input": "1\n42\n",
                     "expected": "42\n", "is_sample": False},
                    {"input": "5\n1 2 3 4 5\n",
                     "expected": "1 2 3 4 5\n", "is_sample": False},
                    {"input": "5\n5 4 3 2 1\n",
                     "expected": "1 2 3 4 5\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_BST_PREORDER",
                "title_fr": "Validation d'un parcours préordre BST",
                "title_en": "Validate BST preorder",
                "prompt_fr": (
                    "On donne une suite de $n$ entiers (tous distincts). "
                    "Décider si **cette suite peut être le parcours préordre** "
                    "d'un BST. Afficher `YES` ou `NO`.\n\n"
                    "**Entrée** :\n\n"
                    "- ligne 1 : $n$ ($1 \\le n \\le 10^5$)\n"
                    "- ligne 2 : $n$ entiers distincts\n\n"
                    "**Sortie** : `YES` ou `NO`.\n\n"
                    "**Indice** : parcourir avec une pile, en maintenant une "
                    "**borne inférieure** mise à jour à chaque dépop. "
                    "Pseudocode classique en $O(n)$."
                ),
                "prompt_en": (
                    "Given a sequence of $n$ distinct integers, decide whether "
                    "**this sequence can be the preorder traversal** of some "
                    "BST. Print `YES` or `NO`.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($1 \\le n \\le 10^5$)\n"
                    "- line 2: $n$ distinct integers\n\n"
                    "**Output**: `YES` or `NO`.\n\n"
                    "**Hint**: walk with a stack, maintaining a **lower bound** "
                    "updated each time we pop. Classic $O(n)$."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0])\n"
                    "    a = list(map(int, data[1:1 + n]))\n"
                    "    # TODO: stack-based validation.\n"
                    "    print('YES')\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5\n5 3 1 4 7\n",
                     "expected": "YES\n", "is_sample": True},
                    {"input": "5\n5 3 7 1 4\n",
                     "expected": "NO\n", "is_sample": True},
                    {"input": "1\n42\n",
                     "expected": "YES\n", "is_sample": False},
                    {"input": "3\n1 2 3\n",
                     "expected": "YES\n", "is_sample": False},
                    {"input": "3\n3 2 1\n",
                     "expected": "YES\n", "is_sample": False},
                    {"input": "4\n8 5 6 9\n",
                     "expected": "YES\n", "is_sample": False},
                    {"input": "4\n8 5 9 6\n",
                     "expected": "NO\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_BST_HEIGHT",
                "title_fr": "Hauteur d'un BST naïf",
                "title_en": "Naive BST height",
                "prompt_fr": (
                    "Insérer une suite d'entiers dans un BST naïf (sans "
                    "rééquilibrage). Afficher la **hauteur** finale (nombre de "
                    "nœuds sur le plus long chemin racine-feuille). Un arbre "
                    "vide a hauteur $0$ ; un seul nœud a hauteur $1$.\n\n"
                    "**Entrée** :\n\n"
                    "- ligne 1 : $n$ ($1 \\le n \\le 10^5$)\n"
                    "- ligne 2 : $n$ entiers à insérer (doublons ignorés)\n\n"
                    "**Sortie** : la hauteur.\n\n"
                    "**Note** : insérer $1, 2, \\dots, n$ dans l'ordre donne une "
                    "chaîne de hauteur $n$ - c'est exactement le pire cas dont "
                    "parle la leçon."
                ),
                "prompt_en": (
                    "Insert a sequence of integers into a plain (unbalanced) "
                    "BST. Print the final **height** (number of nodes on the "
                    "longest root-to-leaf path). An empty tree has height $0$; "
                    "a single node has height $1$.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($1 \\le n \\le 10^5$)\n"
                    "- line 2: $n$ integers to insert (duplicates ignored)\n\n"
                    "**Output**: the height.\n\n"
                    "**Note**: inserting $1, 2, \\dots, n$ in order gives a "
                    "height-$n$ chain - exactly the worst case the lesson warns "
                    "about."
                ),
                "starter_code": (
                    "import sys\n"
                    "sys.setrecursionlimit(200000)\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0])\n"
                    "    a = list(map(int, data[1:1 + n]))\n"
                    "    # TODO: build BST, compute height.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5\n1 2 3 4 5\n",
                     "expected": "5\n", "is_sample": True},
                    {"input": "7\n4 2 6 1 3 5 7\n",
                     "expected": "3\n", "is_sample": True},
                    {"input": "5\n5 4 3 2 1\n",
                     "expected": "5\n", "is_sample": False},
                    {"input": "1\n42\n",
                     "expected": "1\n", "is_sample": False},
                    {"input": "5\n3 1 4 5 2\n",
                     "expected": "3\n", "is_sample": False},
                    {"input": "10\n5 3 8 1 4 7 9 2 6 10\n",
                     "expected": "4\n", "is_sample": False},
                ],
            },
        ],
    },
    {
        "slug": "tas-heapsort",
        "title_fr": "Tas binaires & heapsort",
        "title_en": "Binary Heaps & Heapsort",
        "order_idx": 3,
        "content_fr_file": "lesson_04_heap.fr.md",
        "content_en_file": "lesson_04_heap.en.md",
        "exercises": [
            {
                "key": "EX_HP_HEAPSORT",
                "title_fr": "Tri par tas",
                "title_en": "Heapsort",
                "prompt_fr": (
                    "Trier un tableau de $n$ entiers par ordre **croissant** "
                    "en utilisant un tas (bibliothèque `heapq` ou implémentation "
                    "personnelle).\n\n"
                    "**Entrée** :\n\n"
                    "- ligne 1 : $n$ ($1 \\le n \\le 10^6$)\n"
                    "- ligne 2 : $n$ entiers\n\n"
                    "**Sortie** : les entiers triés, séparés par des espaces, sur "
                    "une ligne."
                ),
                "prompt_en": (
                    "Sort an array of $n$ integers in **ascending** order using "
                    "a heap (built-in `heapq` or your own implementation).\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($1 \\le n \\le 10^6$)\n"
                    "- line 2: $n$ integers\n\n"
                    "**Output**: sorted integers, space-separated, on one line."
                ),
                "starter_code": (
                    "import sys\n"
                    "import heapq\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0])\n"
                    "    a = list(map(int, data[1:1 + n]))\n"
                    "    # TODO: heap-sort, then print.\n"
                    "    print('')\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5\n3 1 4 1 5\n",
                     "expected": "1 1 3 4 5\n", "is_sample": True},
                    {"input": "7\n9 8 7 6 5 4 3\n",
                     "expected": "3 4 5 6 7 8 9\n", "is_sample": True},
                    {"input": "1\n42\n",
                     "expected": "42\n", "is_sample": False},
                    {"input": "6\n-3 -1 -5 0 2 -2\n",
                     "expected": "-5 -3 -2 -1 0 2\n", "is_sample": False},
                    {"input": "8\n5 5 5 5 5 5 5 5\n",
                     "expected": "5 5 5 5 5 5 5 5\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_HP_KSMALL",
                "title_fr": "Les k plus petits éléments",
                "title_en": "The k smallest elements",
                "prompt_fr": (
                    "Étant donné $n$ entiers et un entier $k$ ($1 \\le k \\le n$), "
                    "afficher les $k$ **plus petits** dans l'ordre croissant.\n\n"
                    "**Entrée** :\n\n"
                    "- ligne 1 : $n$ et $k$ ($1 \\le k \\le n \\le 10^6$)\n"
                    "- ligne 2 : $n$ entiers\n\n"
                    "**Sortie** : les $k$ plus petits, séparés par des espaces, "
                    "triés croissants.\n\n"
                    "**Indice** : un max-heap de taille $k$ donne $O(n \\log k)$, "
                    "préférable à un tri complet $O(n \\log n)$ quand $k \\ll n$. "
                    "(Tri complet accepté.)"
                ),
                "prompt_en": (
                    "Given $n$ integers and $k$ ($1 \\le k \\le n$), print the "
                    "$k$ **smallest** in ascending order.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $k$ ($1 \\le k \\le n \\le 10^6$)\n"
                    "- line 2: $n$ integers\n\n"
                    "**Output**: the $k$ smallest, space-separated, in ascending "
                    "order.\n\n"
                    "**Hint**: a max-heap of size $k$ gives $O(n \\log k)$, "
                    "better than a full sort $O(n \\log n)$ when $k \\ll n$. "
                    "(Full sort is accepted.)"
                ),
                "starter_code": (
                    "import sys\n"
                    "import heapq\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n, k = int(data[0]), int(data[1])\n"
                    "    a = list(map(int, data[2:2 + n]))\n"
                    "    # TODO: keep the k smallest, print sorted.\n"
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
                    {"input": "5 5\n3 1 4 1 5\n",
                     "expected": "1 1 3 4 5\n", "is_sample": False},
                    {"input": "3 2\n-5 -2 -8\n",
                     "expected": "-8 -5\n", "is_sample": False},
                    {"input": "4 1\n10 20 30 40\n",
                     "expected": "10\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_HP_MERGE",
                "title_fr": "Coût minimal de fusion (Huffman simple)",
                "title_en": "Minimum merge cost (simple Huffman)",
                "prompt_fr": (
                    "On a $n$ cordes de longueurs $\\ell_1, \\dots, \\ell_n$. Le "
                    "coût pour fusionner deux cordes vaut la somme de leurs "
                    "longueurs. On souhaite **minimiser le coût total** pour "
                    "obtenir une seule corde.\n\n"
                    "**Entrée** :\n\n"
                    "- ligne 1 : $n$ ($1 \\le n \\le 10^5$)\n"
                    "- ligne 2 : $n$ longueurs entières positives ($1 \\le \\ell_i \\le 10^6$)\n\n"
                    "**Sortie** : le coût total minimum (ou $0$ si $n = 1$).\n\n"
                    "**Indice** : à chaque étape, fusionner les **deux plus "
                    "petites** cordes courantes. Min-heap, $O(n \\log n)$. "
                    "C'est l'algorithme de Huffman avec poids uniformes."
                ),
                "prompt_en": (
                    "You have $n$ ropes of lengths $\\ell_1, \\dots, \\ell_n$. "
                    "Merging two ropes costs the sum of their lengths. **Minimize "
                    "the total cost** to combine them into a single rope.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($1 \\le n \\le 10^5$)\n"
                    "- line 2: $n$ positive integer lengths ($1 \\le \\ell_i \\le 10^6$)\n\n"
                    "**Output**: minimum total cost (or $0$ if $n = 1$).\n\n"
                    "**Hint**: at each step, merge the **two smallest** current "
                    "ropes. Min-heap, $O(n \\log n)$. This is Huffman with "
                    "uniform weights."
                ),
                "starter_code": (
                    "import sys\n"
                    "import heapq\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0])\n"
                    "    a = list(map(int, data[1:1 + n]))\n"
                    "    # TODO: greedy merge with a min-heap.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "3\n4 3 2\n", "expected": "14\n", "is_sample": True},
                    {"input": "4\n1 2 3 4\n", "expected": "19\n", "is_sample": True},
                    {"input": "2\n5 7\n", "expected": "12\n", "is_sample": False},
                    {"input": "1\n10\n", "expected": "0\n", "is_sample": False},
                    {"input": "5\n1 2 3 4 5\n",
                     "expected": "33\n", "is_sample": False},
                    {"input": "6\n8 6 7 5 3 9\n",
                     "expected": "97\n", "is_sample": False},
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
    parser.add_argument("--db", type=str, default=None,
                        help="DATABASE_URL override.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.db:
        os.environ["DATABASE_URL"] = args.db

    from backend import models  # noqa: E402
    from backend.database import SessionLocal  # noqa: E402

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
                    f"      - exercise {ex['key']:<16} "
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
    print(f"Chapitre 2 - Structures de donnees elementaires : OK ({state}).")
    if not publish:
        print("-> Active la publication via l'admin si tu veux les rendre "
              "visibles aux etudiants.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
