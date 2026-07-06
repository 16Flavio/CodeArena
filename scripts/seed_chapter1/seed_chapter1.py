"""Seed Chapter 1 - Fondations de l'analyse (algorithmique).

Crée (ou met à jour) la section ``fondations-analyse`` avec quatre leçons :

  1. Modèle RAM & notations asymptotiques
  2. Analyse de boucles & sommes utiles
  3. Récurrences & Master Theorem
  4. Analyse amortie & tableau dynamique

Chaque leçon contient trois exercices inline gradués (standard / twist / dur).
Les contenus markdown FR + EN vivent dans ``content/`` à côté du script.

Idempotent : on retrouve la section/leçons par slug, on remplace les
exercices d'une leçon à chaque exécution. Les progressions étudiantes
restent intactes.

Usage::

    python scripts/seed_chapter1/seed_chapter1.py
    python scripts/seed_chapter1/seed_chapter1.py --draft   # garde en brouillon
    python scripts/seed_chapter1/seed_chapter1.py --db /tmp/test.db
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Iterable


# ── Path bootstrap ────────────────────────────────────────────────────────────
HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent.parent
CONTENT_DIR = HERE / "content"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ── Section ───────────────────────────────────────────────────────────────────
SECTION = {
    "slug": "fondations-analyse",
    "title_fr": "Fondations de l'analyse",
    "title_en": "Analysis Foundations",
    "description_fr": (
        "Modèle RAM, notations asymptotiques, analyse de boucles, sommes "
        "utiles, récurrences (substitution / arbre / Master Theorem / "
        "Akra-Bazzi) et analyse amortie."
    ),
    "description_en": (
        "RAM model, asymptotic notations, loop analysis, useful sums, "
        "recurrences (substitution / tree / Master Theorem / Akra-Bazzi), "
        "and amortized analysis."
    ),
    "order_idx": 0,
}


# ── Lessons + exercises ───────────────────────────────────────────────────────
# Each exercise has a ``key`` matching a ``{{EX_<KEY>}}`` placeholder in the
# lesson markdown. After insert, we replace the placeholder with the actual
# exercise id.

LESSONS: list[dict] = [
    {
        "slug": "ram-asymptotique",
        "title_fr": "Modèle RAM & notations asymptotiques",
        "title_en": "RAM Model & Asymptotic Notations",
        "order_idx": 0,
        "content_fr_file": "lesson_01_ram.fr.md",
        "content_en_file": "lesson_01_ram.en.md",
        "exercises": [
            {
                "key": "EX_RAM_STD",
                "title_fr": "Compter les itérations d'une boucle imbriquée",
                "title_en": "Count nested-loop iterations",
                "prompt_fr": (
                    "On exécute le code suivant :\n\n"
                    "```python\n"
                    "for i in range(n):\n"
                    "    for j in range(i):\n"
                    "        op()\n"
                    "```\n\n"
                    "Lire un entier $n$ ($1 \\le n \\le 10^{18}$) sur l'entrée standard. "
                    "Afficher le **nombre exact** d'appels à `op()`."
                ),
                "prompt_en": (
                    "Consider the snippet:\n\n"
                    "```python\n"
                    "for i in range(n):\n"
                    "    for j in range(i):\n"
                    "        op()\n"
                    "```\n\n"
                    "Read an integer $n$ ($1 \\le n \\le 10^{18}$) from stdin. "
                    "Print the **exact** number of `op()` calls."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    n = int(sys.stdin.readline())\n"
                    "    # TODO: print the number of op() calls.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5\n", "expected": "10\n", "is_sample": True},
                    {"input": "1\n", "expected": "0\n", "is_sample": True},
                    {"input": "10\n", "expected": "45\n", "is_sample": False},
                    {"input": "100\n", "expected": "4950\n", "is_sample": False},
                    {"input": "1000000\n", "expected": "499999500000\n", "is_sample": False},
                    {"input": "1000000000000000000\n",
                     "expected": "499999999999999999500000000000000000\n",
                     "is_sample": False},
                ],
            },
            {
                "key": "EX_RAM_TWIST",
                "title_fr": "Plus petit n₀ pour une borne O(n²)",
                "title_en": "Smallest n₀ for an O(n²) bound",
                "prompt_fr": (
                    "Soient $f(n) = a\\,n^2 + b\\,n + c$ et $g(n) = k\\,n^2$. "
                    "Étant donné $a, b, c, k$ entiers avec $1 \\le a < k \\le 1000$ "
                    "et $|b|, |c| \\le 1000$, calculer le plus petit entier "
                    "$n_0 \\ge 1$ tel que **pour tout** $n \\ge n_0$, "
                    "$f(n) \\le g(n)$.\n\n"
                    "Comme $k > a$, un tel $n_0$ existe toujours.\n\n"
                    "**Entrée** : une ligne contenant $a$, $b$, $c$, $k$ séparés "
                    "par des espaces.  \n"
                    "**Sortie** : un entier sur une ligne.\n\n"
                    "**Indice** : la fonction $h(n) = g(n) - f(n) = (k-a)n^2 - bn - c$ "
                    "est une parabole convexe : toutes les violations $h(n) < 0$ "
                    "se trouvent dans un préfixe borné. Parcourir $n$ sur une "
                    "plage suffisante (jusqu'au sommet plus une marge), retenir "
                    "le **dernier** $n$ tel que $h(n) < 0$, et répondre ce $n$ "
                    "plus un (ou $1$ si $h$ n'est jamais négative)."
                ),
                "prompt_en": (
                    "Let $f(n) = a\\,n^2 + b\\,n + c$ and $g(n) = k\\,n^2$. "
                    "Given integers $a, b, c, k$ with $1 \\le a < k \\le 1000$ "
                    "and $|b|, |c| \\le 1000$, compute the smallest integer "
                    "$n_0 \\ge 1$ such that **for all** $n \\ge n_0$, "
                    "$f(n) \\le g(n)$.\n\n"
                    "Because $k > a$, such $n_0$ always exists.\n\n"
                    "**Input**: one line with $a$, $b$, $c$, $k$ separated by "
                    "spaces.  \n"
                    "**Output**: one integer on its own line.\n\n"
                    "**Hint**: $h(n) = g(n) - f(n) = (k-a)n^2 - bn - c$ is a "
                    "convex parabola: all violations $h(n) < 0$ lie in a bounded "
                    "prefix. Scan $n$ over a sufficient range (up to the vertex "
                    "plus a margin), track the **last** $n$ with $h(n) < 0$, and "
                    "answer that $n$ plus one (or $1$ if $h$ is never negative)."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    a, b, c, k = map(int, sys.stdin.read().split())\n"
                    "    # TODO: print the smallest n0 >= 1 such that\n"
                    "    #   for all n >= n0,  a*n*n + b*n + c <= k*n*n.\n"
                    "    print(1)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "1 0 0 2\n", "expected": "1\n", "is_sample": True},
                    {"input": "1 10 0 2\n", "expected": "10\n", "is_sample": True},
                    {"input": "1 -5 100 2\n", "expected": "8\n", "is_sample": False},
                    {"input": "5 -20 50 6\n", "expected": "3\n", "is_sample": False},
                    {"input": "2 100 0 3\n", "expected": "100\n", "is_sample": False},
                    {"input": "3 0 0 4\n", "expected": "1\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_RAM_HARD",
                "title_fr": "Croisement asymptotique",
                "title_en": "Asymptotic crossover",
                "prompt_fr": (
                    "Soient $f(n) = a\\,n$ et $g(n) = b\\,\\lfloor \\log_2 n \\rfloor$ "
                    "($n \\ge 2$ entier, $1 \\le a, b \\le 1000$).\n\n"
                    "Trouver le plus petit entier $n \\ge 2$ tel que "
                    "$a\\,n \\ge b\\,\\lfloor \\log_2 n \\rfloor$.\n\n"
                    "**Entrée** : deux entiers $a$ et $b$ séparés par un espace.  \n"
                    "**Sortie** : un entier sur une ligne.\n\n"
                    "**Indice** : la solution est toujours $\\le 2 \\cdot 10^5$ "
                    "pour ces bornes ; une boucle naïve sur $n$ suffit."
                ),
                "prompt_en": (
                    "Let $f(n) = a\\,n$ and $g(n) = b\\,\\lfloor \\log_2 n \\rfloor$ "
                    "($n \\ge 2$ integer, $1 \\le a, b \\le 1000$).\n\n"
                    "Find the smallest integer $n \\ge 2$ with "
                    "$a\\,n \\ge b\\,\\lfloor \\log_2 n \\rfloor$.\n\n"
                    "**Input**: two integers $a$ and $b$ separated by a space.  \n"
                    "**Output**: one integer on its own line.\n\n"
                    "**Hint**: the answer is always $\\le 2 \\cdot 10^5$ within "
                    "these bounds; a naive loop on $n$ is fast enough."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    a, b = map(int, sys.stdin.read().split())\n"
                    "    # TODO: smallest n >= 2 with a*n >= b * floor(log2 n)\n"
                    "    print(2)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "1 1\n", "expected": "2\n", "is_sample": True},
                    {"input": "1 10\n", "expected": "50\n", "is_sample": True},
                    {"input": "10 1\n", "expected": "2\n", "is_sample": False},
                    {"input": "5 50\n", "expected": "50\n", "is_sample": False},
                    {"input": "2 100\n", "expected": "400\n", "is_sample": False},
                    {"input": "1 100\n", "expected": "900\n", "is_sample": False},
                ],
            },
        ],
    },
    {
        "slug": "boucles-sommes",
        "title_fr": "Analyse de boucles & sommes utiles",
        "title_en": "Loop Analysis & Useful Sums",
        "order_idx": 1,
        "content_fr_file": "lesson_02_loops.fr.md",
        "content_en_file": "lesson_02_loops.en.md",
        "exercises": [
            {
                "key": "EX_LOOP_STD",
                "title_fr": "Somme arithmétique en O(1)",
                "title_en": "Arithmetic sum in O(1)",
                "prompt_fr": (
                    "Lire un entier $n$ ($1 \\le n \\le 10^{18}$) et afficher "
                    "$1 + 2 + \\dots + n$.\n\n"
                    "**Attention** : un `for` naïf est trop lent quand "
                    "$n = 10^{18}$. Utiliser la formule fermée."
                ),
                "prompt_en": (
                    "Read an integer $n$ ($1 \\le n \\le 10^{18}$) and print "
                    "$1 + 2 + \\dots + n$.\n\n"
                    "**Note**: a naive `for` is too slow when $n = 10^{18}$. "
                    "Use the closed-form formula."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    n = int(sys.stdin.readline())\n"
                    "    # TODO: closed-form arithmetic sum.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "1\n", "expected": "1\n", "is_sample": True},
                    {"input": "10\n", "expected": "55\n", "is_sample": True},
                    {"input": "100\n", "expected": "5050\n", "is_sample": False},
                    {"input": "1000000\n", "expected": "500000500000\n", "is_sample": False},
                    {"input": "1000000000\n",
                     "expected": "500000000500000000\n", "is_sample": False},
                    {"input": "1000000000000000000\n",
                     "expected": "500000000000000000500000000000000000\n",
                     "is_sample": False},
                ],
            },
            {
                "key": "EX_LOOP_TWIST",
                "title_fr": "Itérations d'une boucle multiplicative",
                "title_en": "Multiplicative-loop iterations",
                "prompt_fr": (
                    "Pour la boucle :\n\n"
                    "```python\n"
                    "i, count = 1, 0\n"
                    "while i <= n:\n"
                    "    count += 1\n"
                    "    i *= 2\n"
                    "```\n\n"
                    "Étant donné $n$ ($1 \\le n \\le 10^{18}$), calculer la "
                    "valeur de `count` à la sortie de la boucle.\n\n"
                    "Réfléchir : ne pas simuler la boucle pour $n$ astronomique."
                ),
                "prompt_en": (
                    "For the loop:\n\n"
                    "```python\n"
                    "i, count = 1, 0\n"
                    "while i <= n:\n"
                    "    count += 1\n"
                    "    i *= 2\n"
                    "```\n\n"
                    "Given $n$ ($1 \\le n \\le 10^{18}$), print the value of "
                    "`count` once the loop exits.\n\n"
                    "Think before coding: don't simulate the loop for huge $n$."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    n = int(sys.stdin.readline())\n"
                    "    # TODO: number of iterations of the multiplicative loop.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "1\n", "expected": "1\n", "is_sample": True},
                    {"input": "10\n", "expected": "4\n", "is_sample": True},
                    {"input": "2\n", "expected": "2\n", "is_sample": False},
                    {"input": "3\n", "expected": "2\n", "is_sample": False},
                    {"input": "1000\n", "expected": "10\n", "is_sample": False},
                    {"input": "1000000\n", "expected": "20\n", "is_sample": False},
                    {"input": "1000000000000000000\n", "expected": "60\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_LOOP_HARD",
                "title_fr": "Somme géométrique modulaire",
                "title_en": "Modular geometric sum",
                "prompt_fr": (
                    "Étant donné $r$ et $n$ ($1 \\le n \\le 10^9$ et "
                    "$1 \\le r < 10^9 + 7$), calculer\n"
                    "$$1 + r + r^2 + \\dots + r^{n-1} \\pmod{10^9 + 7}.$$\n"
                    "Le calcul naïf en $O(n)$ est trop lent - il faut une "
                    "exponentiation rapide ($O(\\log n)$) et l'inverse modulaire "
                    "(petit théorème de Fermat) pour la division par $r-1$.\n\n"
                    "Cas particulier : $r = 1$ donne $n \\bmod (10^9 + 7)$.\n\n"
                    "**Entrée** : deux entiers $r$ et $n$ séparés par un espace.  \n"
                    "**Sortie** : la somme modulo $10^9 + 7$, sur une ligne."
                ),
                "prompt_en": (
                    "Given $r$ and $n$ ($1 \\le n \\le 10^9$ and "
                    "$1 \\le r < 10^9 + 7$), compute\n"
                    "$$1 + r + r^2 + \\dots + r^{n-1} \\pmod{10^9 + 7}.$$\n"
                    "The naive $O(n)$ computation is too slow - you need fast "
                    "exponentiation ($O(\\log n)$) and the modular inverse "
                    "(Fermat's little theorem) for the division by $r-1$.\n\n"
                    "Edge case: $r = 1$ gives $n \\bmod (10^9 + 7)$.\n\n"
                    "**Input**: integers $r$ and $n$ separated by a space.  \n"
                    "**Output**: the sum modulo $10^9 + 7$, on its own line."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "MOD = 10**9 + 7\n\n"
                    "def main():\n"
                    "    r, n = map(int, sys.stdin.read().split())\n"
                    "    # TODO: 1 + r + r^2 + ... + r^(n-1) mod MOD\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "2 3\n", "expected": "7\n", "is_sample": True},
                    {"input": "1 5\n", "expected": "5\n", "is_sample": True},
                    {"input": "10 4\n", "expected": "1111\n", "is_sample": False},
                    {"input": "3 10\n", "expected": "29524\n", "is_sample": False},
                    {"input": "2 10\n", "expected": "1023\n", "is_sample": False},
                    {"input": "2 30\n", "expected": "73741816\n", "is_sample": False},
                    {"input": "1000000006 2\n", "expected": "0\n", "is_sample": False},
                    {"input": "1 1000000000\n", "expected": "1000000000\n", "is_sample": False},
                ],
            },
        ],
    },
    {
        "slug": "recurrences-master",
        "title_fr": "Récurrences & Master Theorem",
        "title_en": "Recurrences & Master Theorem",
        "order_idx": 2,
        "content_fr_file": "lesson_03_recurrences.fr.md",
        "content_en_file": "lesson_03_recurrences.en.md",
        "exercises": [
            {
                "key": "EX_REC_STD",
                "title_fr": "Profondeur d'arbre récursif",
                "title_en": "Recursion-tree depth",
                "prompt_fr": (
                    "Soit $T(n) = T(\\lfloor n/2 \\rfloor) + 1$ avec $T(1) = 1$. "
                    "Calculer $T(n)$ pour $1 \\le n \\le 10^{18}$.\n\n"
                    "**Entrée** : un entier $n$.  \n"
                    "**Sortie** : $T(n)$ sur une ligne.\n\n"
                    "Forme fermée à reconnaître."
                ),
                "prompt_en": (
                    "Let $T(n) = T(\\lfloor n/2 \\rfloor) + 1$ with $T(1) = 1$. "
                    "Compute $T(n)$ for $1 \\le n \\le 10^{18}$.\n\n"
                    "**Input**: integer $n$.  \n"
                    "**Output**: $T(n)$ on its own line.\n\n"
                    "Closed form expected."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    n = int(sys.stdin.readline())\n"
                    "    # TODO: closed form of T(n) = T(n//2) + 1, T(1) = 1.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "1\n", "expected": "1\n", "is_sample": True},
                    {"input": "16\n", "expected": "5\n", "is_sample": True},
                    {"input": "2\n", "expected": "2\n", "is_sample": False},
                    {"input": "3\n", "expected": "2\n", "is_sample": False},
                    {"input": "4\n", "expected": "3\n", "is_sample": False},
                    {"input": "1000000000\n", "expected": "30\n", "is_sample": False},
                    {"input": "1000000000000000000\n", "expected": "60\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_REC_TWIST",
                "title_fr": "Master Theorem : classifier le cas",
                "title_en": "Master Theorem: classify the case",
                "prompt_fr": (
                    "On considère $T(n) = a\\,T(n/b) + n^d$ avec $a \\ge 1$, "
                    "$b \\ge 2$ et $d \\ge 0$ entiers ($a \\le 100$, $b \\le 100$, "
                    "$d \\le 10$).\n\n"
                    "Sortir un seul chiffre :\n\n"
                    "- `1` si $\\log_b a > d$ (cas 1 du Master Theorem)\n"
                    "- `2` si $\\log_b a = d$ (cas 2)\n"
                    "- `3` si $\\log_b a < d$ (cas 3, régularité supposée)\n\n"
                    "**Entrée** : trois entiers $a$, $b$, $d$ séparés par des espaces.  \n"
                    "**Sortie** : `1`, `2` ou `3`.\n\n"
                    "**Indice** : éviter les flottants. $\\log_b a \\lessgtr d$ "
                    "équivaut à $a \\lessgtr b^d$."
                ),
                "prompt_en": (
                    "Consider $T(n) = a\\,T(n/b) + n^d$ with integers $a \\ge 1$, "
                    "$b \\ge 2$, $d \\ge 0$ ($a \\le 100$, $b \\le 100$, "
                    "$d \\le 10$).\n\n"
                    "Print a single digit:\n\n"
                    "- `1` if $\\log_b a > d$ (Master case 1)\n"
                    "- `2` if $\\log_b a = d$ (case 2)\n"
                    "- `3` if $\\log_b a < d$ (case 3, regularity assumed)\n\n"
                    "**Input**: three integers $a$, $b$, $d$ separated by spaces.  \n"
                    "**Output**: `1`, `2`, or `3`.\n\n"
                    "**Hint**: avoid floats. $\\log_b a \\lessgtr d$ is "
                    "equivalent to $a \\lessgtr b^d$."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    a, b, d = map(int, sys.stdin.read().split())\n"
                    "    # TODO: compare a to b**d to classify the case.\n"
                    "    print(1)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "2 2 1\n", "expected": "2\n", "is_sample": True},
                    {"input": "4 2 1\n", "expected": "1\n", "is_sample": True},
                    {"input": "2 2 2\n", "expected": "3\n", "is_sample": False},
                    {"input": "8 2 2\n", "expected": "1\n", "is_sample": False},
                    {"input": "9 3 2\n", "expected": "2\n", "is_sample": False},
                    {"input": "10 3 2\n", "expected": "1\n", "is_sample": False},
                    {"input": "1 2 0\n", "expected": "2\n", "is_sample": False},
                    {"input": "1 2 1\n", "expected": "3\n", "is_sample": False},
                    {"input": "7 2 2\n", "expected": "1\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_REC_HARD",
                "title_fr": "Évaluer T(n) avec mémoïsation",
                "title_en": "Evaluate T(n) with memoization",
                "prompt_fr": (
                    "On définit\n"
                    "$$T(m) = \\begin{cases} m & \\text{si } m < b \\\\ "
                    "a\\,T(\\lceil m/b \\rceil) + m & \\text{sinon} \\end{cases}$$\n\n"
                    "Étant donné $a$, $b$, $n$ avec $1 \\le a \\le 10$, "
                    "$2 \\le b \\le 10$, $1 \\le n \\le 10^{18}$, calculer "
                    "$T(n) \\bmod (10^9 + 7)$.\n\n"
                    "**Entrée** : $a$ $b$ $n$ séparés par des espaces.  \n"
                    "**Sortie** : $T(n) \\bmod (10^9 + 7)$ sur une ligne.\n\n"
                    "**Indice** : avec mémoïsation, seules $O(\\log_b n)$ "
                    "valeurs distinctes sont visitées."
                ),
                "prompt_en": (
                    "Define\n"
                    "$$T(m) = \\begin{cases} m & \\text{if } m < b \\\\ "
                    "a\\,T(\\lceil m/b \\rceil) + m & \\text{otherwise} \\end{cases}$$\n\n"
                    "Given $a$, $b$, $n$ with $1 \\le a \\le 10$, "
                    "$2 \\le b \\le 10$, $1 \\le n \\le 10^{18}$, compute "
                    "$T(n) \\bmod (10^9 + 7)$.\n\n"
                    "**Input**: $a$ $b$ $n$ separated by spaces.  \n"
                    "**Output**: $T(n) \\bmod (10^9 + 7)$ on its own line.\n\n"
                    "**Hint**: memoization visits only $O(\\log_b n)$ distinct "
                    "values."
                ),
                "starter_code": (
                    "import sys\n"
                    "from functools import lru_cache\n\n"
                    "MOD = 10**9 + 7\n\n"
                    "def main():\n"
                    "    a, b, n = map(int, sys.stdin.read().split())\n\n"
                    "    @lru_cache(maxsize=None)\n"
                    "    def T(m):\n"
                    "        if m < b:\n"
                    "            return m % MOD\n"
                    "        # TODO: the recursive case.\n"
                    "        return 0\n\n"
                    "    print(T(n))\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "2 2 1\n", "expected": "1\n", "is_sample": True},
                    {"input": "2 2 2\n", "expected": "4\n", "is_sample": True},
                    {"input": "2 2 4\n", "expected": "12\n", "is_sample": False},
                    {"input": "2 2 8\n", "expected": "32\n", "is_sample": False},
                    {"input": "3 2 8\n", "expected": "65\n", "is_sample": False},
                    {"input": "1 2 100\n", "expected": "202\n", "is_sample": False},
                    {"input": "1 2 1000000000000000000\n",
                     "expected": "116\n", "is_sample": False},
                ],
            },
        ],
    },
    {
        "slug": "amortie-tableau-dynamique",
        "title_fr": "Analyse amortie & tableau dynamique",
        "title_en": "Amortized Analysis & Dynamic Array",
        "order_idx": 3,
        "content_fr_file": "lesson_04_amortized.fr.md",
        "content_en_file": "lesson_04_amortized.en.md",
        "exercises": [
            {
                "key": "EX_AMO_STD",
                "title_fr": "Coût total des copies (tableau dynamique)",
                "title_en": "Total copy cost (dynamic array)",
                "prompt_fr": (
                    "On insère $n$ éléments dans un tableau dynamique avec la "
                    "stratégie « doublement quand plein », capacité initiale 1. "
                    "Quand l'insertion $k$ trouve le tableau plein (size == cap), "
                    "on alloue $2 \\cdot$cap, on **copie** les `cap` éléments "
                    "existants, puis on insère.\n\n"
                    "Calculer le **nombre total de copies** effectuées sur les "
                    "$n$ insertions ($1 \\le n \\le 10^{18}$).\n\n"
                    "**Entrée** : un entier $n$.  \n"
                    "**Sortie** : le total de copies, sur une ligne.\n\n"
                    "**Indice** : forme fermée. Penser à la somme géométrique "
                    "$1 + 2 + 4 + \\dots$"
                ),
                "prompt_en": (
                    "Insert $n$ elements into a dynamic array using the "
                    "\"double-when-full\" strategy, starting capacity 1. "
                    "When insertion $k$ finds the array full (size == cap), "
                    "allocate $2 \\cdot$cap, **copy** the `cap` existing "
                    "elements, then insert.\n\n"
                    "Compute the **total number of copies** over the $n$ "
                    "insertions ($1 \\le n \\le 10^{18}$).\n\n"
                    "**Input**: one integer $n$.  \n"
                    "**Output**: total copy count on one line.\n\n"
                    "**Hint**: closed form. Think about the geometric sum "
                    "$1 + 2 + 4 + \\dots$"
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    n = int(sys.stdin.readline())\n"
                    "    # TODO: total number of copies during n appends.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "1\n", "expected": "0\n", "is_sample": True},
                    {"input": "5\n", "expected": "7\n", "is_sample": True},
                    {"input": "2\n", "expected": "1\n", "is_sample": False},
                    {"input": "3\n", "expected": "3\n", "is_sample": False},
                    {"input": "8\n", "expected": "7\n", "is_sample": False},
                    {"input": "9\n", "expected": "15\n", "is_sample": False},
                    {"input": "1000\n", "expected": "1023\n", "is_sample": False},
                    {"input": "1000000\n", "expected": "1048575\n", "is_sample": False},
                    {"input": "1000000000000000000\n",
                     "expected": "1152921504606846975\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_AMO_TWIST",
                "title_fr": "Pile avec multipop",
                "title_en": "Stack with multipop",
                "prompt_fr": (
                    "Implémenter une pile supportant trois opérations :\n\n"
                    "- `P x` : push de la valeur $x$ (chaîne sans espace)\n"
                    "- `O`   : pop (sans effet si la pile est vide)\n"
                    "- `M k` : multipop - retire les $k$ éléments du sommet, "
                    "ou tout si la pile contient moins de $k$ éléments\n\n"
                    "**Entrée** :\n\n"
                    "- ligne 1 : entier $q$ ($1 \\le q \\le 10^5$), nombre d'opérations\n"
                    "- $q$ lignes suivantes : une opération chacune\n\n"
                    "**Sortie** : le contenu final de la pile, **du fond vers le "
                    "sommet**, séparé par des espaces, sur une seule ligne. Si la "
                    "pile est vide, écrire le mot `EMPTY`.\n\n"
                    "**Note pédagogique** : prouver que la séquence des $q$ "
                    "opérations a un coût total amorti de $O(q)$ - chaque élément "
                    "n'est poppé qu'une fois sur sa vie."
                ),
                "prompt_en": (
                    "Implement a stack supporting three operations:\n\n"
                    "- `P x` : push value $x$ (a non-whitespace token)\n"
                    "- `O`   : pop (no effect if the stack is empty)\n"
                    "- `M k` : multipop - remove the top $k$ elements, "
                    "or everything if the stack holds fewer than $k$\n\n"
                    "**Input**:\n\n"
                    "- line 1: integer $q$ ($1 \\le q \\le 10^5$), number of operations\n"
                    "- next $q$ lines: one operation each\n\n"
                    "**Output**: the final stack contents, **bottom to top**, "
                    "space-separated, on one line. If the stack is empty, print "
                    "the word `EMPTY`.\n\n"
                    "**Pedagogical note**: argue that the total cost of the $q$ "
                    "operations is $O(q)$ amortized - each element is popped at "
                    "most once during its lifetime."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().splitlines()\n"
                    "    q = int(data[0])\n"
                    "    stack = []\n"
                    "    for i in range(1, q + 1):\n"
                    "        parts = data[i].split()\n"
                    "        op = parts[0]\n"
                    "        # TODO: handle P / O / M\n"
                    "    if not stack:\n"
                    "        print('EMPTY')\n"
                    "    else:\n"
                    "        print(' '.join(stack))\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5\nP 1\nP 2\nP 3\nM 2\nP 4\n",
                     "expected": "1 4\n", "is_sample": True},
                    {"input": "3\nP 5\nO\nO\n",
                     "expected": "EMPTY\n", "is_sample": True},
                    {"input": "4\nP 1\nP 2\nP 3\nM 10\n",
                     "expected": "EMPTY\n", "is_sample": False},
                    {"input": "6\nP 1\nP 2\nP 3\nP 4\nM 2\nM 1\n",
                     "expected": "1\n", "is_sample": False},
                    {"input": "5\nP 7\nP 8\nP 9\nO\nO\n",
                     "expected": "7\n", "is_sample": False},
                    {"input": "1\nO\n",
                     "expected": "EMPTY\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_AMO_HARD",
                "title_fr": "Compteur binaire : total des bit-flips",
                "title_en": "Binary counter: total bit-flips",
                "prompt_fr": (
                    "On part d'un compteur binaire à $0$ et on l'incrémente $k$ "
                    "fois. À chaque incrément, plusieurs bits peuvent basculer "
                    "(ex. $0111 + 1 = 1000$ → 4 flips).\n\n"
                    "Calculer le **nombre total de bit-flips** au cours des $k$ "
                    "incréments ($0 \\le k \\le 10^{18}$).\n\n"
                    "**Entrée** : un entier $k$.  \n"
                    "**Sortie** : le total de bit-flips sur une ligne.\n\n"
                    "**Indice** : le bit $i$ bascule $\\lfloor k / 2^{i+1} \\rfloor "
                    "\\cdot 2 + [k \\bmod 2^{i+1} \\ge 2^i]$ fois… ou plus simplement, "
                    "le total est $2k - \\text{popcount}(k)$. À démontrer !"
                ),
                "prompt_en": (
                    "Start a binary counter at $0$ and increment it $k$ times. "
                    "Each increment may flip multiple bits (e.g. "
                    "$0111 + 1 = 1000$ → 4 flips).\n\n"
                    "Compute the **total bit-flips** across $k$ increments "
                    "($0 \\le k \\le 10^{18}$).\n\n"
                    "**Input**: one integer $k$.  \n"
                    "**Output**: total bit-flips on one line.\n\n"
                    "**Hint**: bit $i$ flips $\\lfloor k / 2^{i+1} \\rfloor "
                    "\\cdot 2 + [k \\bmod 2^{i+1} \\ge 2^i]$ times… or more "
                    "simply, the total is $2k - \\text{popcount}(k)$. Prove it!"
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    k = int(sys.stdin.readline())\n"
                    "    # TODO: total number of bit-flips over k increments.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "0\n", "expected": "0\n", "is_sample": True},
                    {"input": "1\n", "expected": "1\n", "is_sample": True},
                    {"input": "2\n", "expected": "3\n", "is_sample": False},
                    {"input": "3\n", "expected": "4\n", "is_sample": False},
                    {"input": "4\n", "expected": "7\n", "is_sample": False},
                    {"input": "7\n", "expected": "11\n", "is_sample": False},
                    {"input": "1000\n", "expected": "1994\n", "is_sample": False},
                    {"input": "1000000000\n", "expected": "1999999987\n", "is_sample": False},
                    {"input": "1000000000000000000\n",
                     "expected": "1999999999999999976\n", "is_sample": False},
                ],
            },
        ],
    },
]


# ── DB upsert helpers ─────────────────────────────────────────────────────────

def _read_content(filename: str) -> str:
    p = CONTENT_DIR / filename
    if not p.exists():
        raise SystemExit(f"Missing content file: {p}")
    return p.read_text(encoding="utf-8")


def _replace_placeholders(content: str, placeholders: dict[str, int]) -> str:
    """Replace ``{{EX_KEY}}`` markers with their actual exercise ids."""
    for key, exercise_id in placeholders.items():
        content = content.replace("{{" + key + "}}", str(exercise_id))
    return content


def _check_no_placeholders_left(content: str) -> None:
    if "{{EX_" in content:
        # Find the first leftover for a clearer error.
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
    """Drop existing inline exercises for this lesson - we re-create them
    from the seed definition. Inline exercises don't track student
    submissions, so this is safe."""
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


# ── Main ──────────────────────────────────────────────────────────────────────

def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--draft",
        action="store_true",
        help=("Crée la section/leçons en brouillon (is_published=False) ; par "
              "défaut tout est publié pour une visualisation immédiate."),
    )
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help=("URL SQLAlchemy override (par défaut, on utilise la même base "
              "que le backend)."),
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.db:
        os.environ["DATABASE_URL"] = args.db

    # Imports backend après ajustement de DATABASE_URL.
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
                    f"      - exercise {ex['key']:<14} "
                    f"id={ex_id} "
                    f"({len(ex['test_cases'])} test cases)"
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

    state = "publiées" if publish else "en brouillon"
    print()
    print(f"Chapitre 1 - Fondations de l'analyse : OK ({state}).")
    if not publish:
        print("-> Active la publication via l'admin si tu veux les rendre "
              "visibles aux étudiants.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
