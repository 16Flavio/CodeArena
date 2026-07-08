"""Seed Chapter 8 - Algorithmique du texte.

Cree (ou met a jour) la section ``texte`` avec quatre lecons :

  1. Hachage de chaines (Rabin-Karp)
  2. KMP & fonction prefixe
  3. Z-function & Manacher
  4. Suffix array & LCP

Chaque lecon contient trois exercices inline gradues (standard,
twist, dur). Idempotent.

Pre-deploiement le script verifie que chaque solution de reference
passe sur ses test cases (--validate-only pour ne faire QUE ca).

Usage:
    python scripts/seed_chapter8/seed_chapter8.py
    python scripts/seed_chapter8/seed_chapter8.py --draft
    python scripts/seed_chapter8/seed_chapter8.py --validate-only
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
    "slug": "texte",
    "title_fr": "Algorithmique du texte",
    "title_en": "String Algorithms",
    "description_fr": (
        "Les algorithmes qui font parler les chaines de caracteres : "
        "hachage polynomial et Rabin-Karp, recherche de motif en temps "
        "lineaire par KMP et sa fonction prefixe, Z-function et l'astuce "
        "de Manacher pour les palindromes, et les suffix arrays avec leur "
        "tableau LCP pour les sous-chaines distinctes et repetees."
    ),
    "description_en": (
        "The algorithms that make strings talk: polynomial hashing and "
        "Rabin-Karp, linear-time pattern matching via KMP and its prefix "
        "function, the Z-function and Manacher's trick for palindromes, "
        "and suffix arrays with their LCP array for distinct and repeated "
        "substrings."
    ),
    "order_idx": 7,
}


LESSONS: list[dict] = [
    # =================================================================
    # Lesson 1 - Hachage de chaines
    # =================================================================
    {
        "slug": "hachage",
        "title_fr": "Hachage de chaines (Rabin-Karp)",
        "title_en": "String Hashing (Rabin-Karp)",
        "order_idx": 0,
        "content_fr_file": "lesson_01_hashing.fr.md",
        "content_en_file": "lesson_01_hashing.en.md",
        "exercises": [
            {
                "key": "EX_TX_RK_COUNT",
                "title_fr": "Nombre d'occurrences",
                "title_en": "Occurrence count",
                "prompt_fr": (
                    "Compter le nombre d'occurrences (chevauchantes "
                    "autorisees) d'un motif $P$ dans un texte $T$.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : le texte $T$ ($1 \\le |T| \\le 10^6$)\n"
                    "- ligne 2 : le motif $P$ ($1 \\le |P| \\le |T|$)\n\n"
                    "en lettres minuscules `a`-`z`.\n\n"
                    "**Sortie** : un seul entier.\n\n"
                    "**Indice** : hachage polynomial. Precalculer le hash de "
                    "chaque fenetre glissante de longueur $|P|$ en $O(1)$ "
                    "par decalage, et comparer au hash de $P$. Un **double "
                    "hash** (deux modulos) evite quasiment toute "
                    "collision."
                ),
                "prompt_en": (
                    "Count the number of (overlapping-allowed) occurrences "
                    "of a pattern $P$ in a text $T$.\n\n"
                    "**Input**:\n\n"
                    "- line 1: the text $T$ ($1 \\le |T| \\le 10^6$)\n"
                    "- line 2: the pattern $P$ ($1 \\le |P| \\le |T|$)\n\n"
                    "in lowercase letters `a`-`z`.\n\n"
                    "**Output**: one integer.\n\n"
                    "**Hint**: polynomial hashing. Precompute the hash of "
                    "each sliding window of length $|P|$ in $O(1)$ per "
                    "shift, and compare to the hash of $P$. A **double "
                    "hash** (two moduli) avoids virtually all collisions."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split('\\n')\n"
                    "    t = data[0]; p = data[1] if len(data) > 1 else ''\n"
                    "    # TODO: rolling-hash occurrence count.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "abababa\naba\n", "expected": "3\n", "is_sample": True},
                    {"input": "hello\nll\n", "expected": "1\n", "is_sample": True},
                    {"input": "aaaa\naa\n", "expected": "3\n", "is_sample": False},
                    {"input": "abcabc\nabc\n", "expected": "2\n", "is_sample": False},
                    {"input": "mississippi\nissi\n", "expected": "2\n", "is_sample": False},
                    {"input": "abc\nxyz\n", "expected": "0\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_TX_DISTINCT_SUBSTR_K",
                "title_fr": "Sous-chaines distinctes de longueur K",
                "title_en": "Distinct substrings of length K",
                "prompt_fr": (
                    "Compter le nombre de sous-chaines **distinctes** de "
                    "longueur **exactement** $k$ d'une chaine $s$.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : la chaine $s$ ($1 \\le |s| \\le 10^5$, "
                    "minuscules)\n"
                    "- ligne 2 : l'entier $k$\n\n"
                    "**Sortie** : un seul entier (0 si $k > |s|$).\n\n"
                    "**Indice** : hacher chaque fenetre de longueur $k$ et "
                    "compter les **hash distincts** (ensemble). Le hachage "
                    "roulant rend chaque fenetre $O(1)$."
                ),
                "prompt_en": (
                    "Count the number of **distinct** substrings of length "
                    "**exactly** $k$ of a string $s$.\n\n"
                    "**Input**:\n\n"
                    "- line 1: the string $s$ ($1 \\le |s| \\le 10^5$, "
                    "lowercase)\n"
                    "- line 2: the integer $k$\n\n"
                    "**Output**: one integer (0 if $k > |s|$).\n\n"
                    "**Hint**: hash each window of length $k$ and count the "
                    "**distinct hashes** (a set). Rolling hashing makes each "
                    "window $O(1)$."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split('\\n')\n"
                    "    s = data[0]; k = int(data[1])\n"
                    "    # TODO: count distinct length-k windows via hashing.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "ababa\n2\n", "expected": "2\n", "is_sample": True},
                    {"input": "aaaa\n1\n", "expected": "1\n", "is_sample": True},
                    {"input": "abcabc\n3\n", "expected": "3\n", "is_sample": False},
                    {"input": "abcde\n5\n", "expected": "1\n", "is_sample": False},
                    {"input": "aaa\n4\n", "expected": "0\n", "is_sample": False},
                    {"input": "banana\n2\n", "expected": "3\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_TX_LONGEST_COMMON_SUBSTR",
                "title_fr": "Plus longue sous-chaine commune",
                "title_en": "Longest common substring",
                "prompt_fr": (
                    "Trouver la **longueur** de la plus longue sous-chaine "
                    "**contigue** commune a deux chaines $s$ et $t$.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $s$ ($1 \\le |s| \\le 5000$)\n"
                    "- ligne 2 : $t$ ($1 \\le |t| \\le 5000$)\n\n"
                    "en minuscules.\n\n"
                    "**Sortie** : un seul entier (0 si aucune).\n\n"
                    "**Indice** : recherche **dichotomique sur la "
                    "longueur** $L$ ; pour un $L$ donne, hacher toutes les "
                    "fenetres de longueur $L$ de $s$ dans un ensemble et "
                    "tester si une fenetre de $t$ y figure. Predicat "
                    "monotone : si une commune de longueur $L$ existe, il en "
                    "existe une de longueur $L-1$."
                ),
                "prompt_en": (
                    "Find the **length** of the longest **contiguous** "
                    "substring common to two strings $s$ and $t$.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $s$ ($1 \\le |s| \\le 5000$)\n"
                    "- line 2: $t$ ($1 \\le |t| \\le 5000$)\n\n"
                    "in lowercase.\n\n"
                    "**Output**: one integer (0 if none).\n\n"
                    "**Hint**: **binary search on the length** $L$; for a "
                    "given $L$, hash all length-$L$ windows of $s$ into a "
                    "set and test whether a window of $t$ is present. "
                    "Monotone predicate: if a common one of length $L$ "
                    "exists, so does one of length $L-1$."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split('\\n')\n"
                    "    s = data[0]; t = data[1] if len(data) > 1 else ''\n"
                    "    # TODO: binary search + hashing (or DP).\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "abcde\ncdefg\n", "expected": "3\n", "is_sample": True},
                    {"input": "abab\nbaba\n", "expected": "3\n", "is_sample": True},
                    {"input": "abc\nxyz\n", "expected": "0\n", "is_sample": False},
                    {"input": "aaaa\naa\n", "expected": "2\n", "is_sample": False},
                    {"input": "competitive\nprogramming\n", "expected": "1\n", "is_sample": False},
                    {"input": "banana\nananas\n", "expected": "5\n", "is_sample": False},
                ],
            },
        ],
    },

    # =================================================================
    # Lesson 2 - KMP
    # =================================================================
    {
        "slug": "kmp",
        "title_fr": "KMP & fonction prefixe",
        "title_en": "KMP & Prefix Function",
        "order_idx": 1,
        "content_fr_file": "lesson_02_kmp.fr.md",
        "content_en_file": "lesson_02_kmp.en.md",
        "exercises": [
            {
                "key": "EX_TX_KMP_POSITIONS",
                "title_fr": "Positions du motif",
                "title_en": "Pattern positions",
                "prompt_fr": (
                    "Trouver **toutes** les positions de depart (1-indexes) "
                    "des occurrences d'un motif $P$ dans un texte $T$.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $T$ ($1 \\le |T| \\le 10^6$)\n"
                    "- ligne 2 : $P$ ($1 \\le |P| \\le |T|$)\n\n"
                    "**Sortie** : les positions par ordre croissant, "
                    "separees par des espaces (ligne vide si aucune).\n\n"
                    "**Indice** : KMP. Calculer la **fonction prefixe** de "
                    "$P$, puis parcourir $T$ en maintenant la longueur du "
                    "prefixe de $P$ actuellement apparie ; un match complet "
                    "signale une occurrence. $O(|T| + |P|)$."
                ),
                "prompt_en": (
                    "Find **all** starting positions (1-indexed) of the "
                    "occurrences of a pattern $P$ in a text $T$.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $T$ ($1 \\le |T| \\le 10^6$)\n"
                    "- line 2: $P$ ($1 \\le |P| \\le |T|$)\n\n"
                    "**Output**: the positions in increasing order, "
                    "space-separated (empty line if none).\n\n"
                    "**Hint**: KMP. Compute the **prefix function** of $P$, "
                    "then scan $T$ keeping the length of the currently "
                    "matched prefix of $P$; a full match signals an "
                    "occurrence. $O(|T| + |P|)$."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split('\\n')\n"
                    "    t = data[0]; p = data[1] if len(data) > 1 else ''\n"
                    "    # TODO: KMP; collect 1-indexed positions.\n"
                    "    print()\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "abababa\naba\n", "expected": "1 3 5\n", "is_sample": True},
                    {"input": "abcabc\nabc\n", "expected": "1 4\n", "is_sample": True},
                    {"input": "aaaa\naa\n", "expected": "1 2 3\n", "is_sample": False},
                    {"input": "abc\nxyz\n", "expected": "\n", "is_sample": False},
                    {"input": "mississippi\nissi\n", "expected": "2 5\n", "is_sample": False},
                    {"input": "aaaaa\na\n", "expected": "1 2 3 4 5\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_TX_MIN_PERIOD",
                "title_fr": "Plus petite periode",
                "title_en": "Smallest period",
                "prompt_fr": (
                    "Trouver la **plus petite periode** $p$ d'une chaine "
                    "$s$ : le plus petit $p$ tel que $s_i = s_{i+p}$ pour "
                    "tout indice valide.\n\n"
                    "**Entree** : une ligne, la chaine $s$ ($1 \\le |s| \\le "
                    "10^6$, minuscules).\n\n"
                    "**Sortie** : un seul entier ($p = |s|$ si la chaine "
                    "n'est pas periodique).\n\n"
                    "**Indice** : avec la fonction prefixe $\\pi$, la plus "
                    "petite periode vaut $|s| - \\pi[|s|-1]$. Le plus long "
                    "**bord** (prefixe = suffixe) determine directement la "
                    "periode."
                ),
                "prompt_en": (
                    "Find the **smallest period** $p$ of a string $s$: the "
                    "smallest $p$ such that $s_i = s_{i+p}$ for every valid "
                    "index.\n\n"
                    "**Input**: one line, the string $s$ ($1 \\le |s| \\le "
                    "10^6$, lowercase).\n\n"
                    "**Output**: one integer ($p = |s|$ if the string is not "
                    "periodic).\n\n"
                    "**Hint**: with the prefix function $\\pi$, the smallest "
                    "period is $|s| - \\pi[|s|-1]$. The longest **border** "
                    "(prefix = suffix) directly determines the period."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    s = sys.stdin.readline().rstrip('\\n')\n"
                    "    # TODO: prefix function -> smallest period.\n"
                    "    print(len(s))\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "ababab\n", "expected": "2\n", "is_sample": True},
                    {"input": "abcabc\n", "expected": "3\n", "is_sample": True},
                    {"input": "aaaa\n", "expected": "1\n", "is_sample": False},
                    {"input": "abcde\n", "expected": "5\n", "is_sample": False},
                    {"input": "abaaba\n", "expected": "3\n", "is_sample": False},
                    {"input": "aabaab\n", "expected": "3\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_TX_BORDERS",
                "title_fr": "Tous les bords",
                "title_en": "All borders",
                "prompt_fr": (
                    "Un **bord** d'une chaine $s$ est un prefixe **propre** "
                    "(strictement plus court que $s$) qui est aussi un "
                    "suffixe. Lister les **longueurs** de tous les bords, "
                    "par ordre croissant.\n\n"
                    "**Entree** : une ligne, la chaine $s$ ($1 \\le |s| \\le "
                    "10^6$, minuscules).\n\n"
                    "**Sortie** : les longueurs des bords, separees par des "
                    "espaces (ligne vide si aucun).\n\n"
                    "**Indice** : le plus long bord a pour longueur "
                    "$\\pi[|s|-1]$. Les bords suivants s'obtiennent en "
                    "**iterant** la fonction prefixe : $\\pi[k-1]$, "
                    "$\\pi[\\pi[k-1]-1]$, etc., jusqu'a 0."
                ),
                "prompt_en": (
                    "A **border** of a string $s$ is a **proper** prefix "
                    "(strictly shorter than $s$) that is also a suffix. List "
                    "the **lengths** of all borders, in increasing order.\n\n"
                    "**Input**: one line, the string $s$ ($1 \\le |s| \\le "
                    "10^6$, lowercase).\n\n"
                    "**Output**: the border lengths, space-separated (empty "
                    "line if none).\n\n"
                    "**Hint**: the longest border has length $\\pi[|s|-1]$. "
                    "The following borders are obtained by **iterating** the "
                    "prefix function: $\\pi[k-1]$, $\\pi[\\pi[k-1]-1]$, etc., "
                    "down to 0."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    s = sys.stdin.readline().rstrip('\\n')\n"
                    "    # TODO: prefix function; iterate the border chain.\n"
                    "    print()\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "ababab\n", "expected": "2 4\n", "is_sample": True},
                    {"input": "abcabc\n", "expected": "3\n", "is_sample": True},
                    {"input": "aaaa\n", "expected": "1 2 3\n", "is_sample": False},
                    {"input": "abcde\n", "expected": "\n", "is_sample": False},
                    {"input": "aabaaaba\n", "expected": "1 4\n", "is_sample": False},
                    {"input": "abacaba\n", "expected": "1 3\n", "is_sample": False},
                ],
            },
        ],
    },

    # =================================================================
    # Lesson 3 - Z-function & Manacher
    # =================================================================
    {
        "slug": "z-manacher",
        "title_fr": "Z-function & Manacher",
        "title_en": "Z-function & Manacher",
        "order_idx": 2,
        "content_fr_file": "lesson_03_z_manacher.fr.md",
        "content_en_file": "lesson_03_z_manacher.en.md",
        "exercises": [
            {
                "key": "EX_TX_ZFUNC",
                "title_fr": "Z-function",
                "title_en": "Z-function",
                "prompt_fr": (
                    "Calculer la **Z-function** d'une chaine $s$ : pour "
                    "chaque $i$, $z_i$ est la longueur du plus long prefixe "
                    "commun entre $s$ et le suffixe $s_i s_{i+1} \\dots$ Par "
                    "convention $z_0 = 0$.\n\n"
                    "**Entree** : une ligne, la chaine $s$ ($1 \\le |s| \\le "
                    "10^6$, minuscules).\n\n"
                    "**Sortie** : les $n$ valeurs $z_0, \\dots, z_{n-1}$ "
                    "separees par des espaces.\n\n"
                    "**Indice** : maintenir une **fenetre** $[l, r]$ = le "
                    "segment correspondant au prefixe le plus a droite deja "
                    "trouve. Si $i < r$, on initialise $z_i$ avec la valeur "
                    "deja calculee en $i - l$, puis on etend. $O(n)$."
                ),
                "prompt_en": (
                    "Compute the **Z-function** of a string $s$: for each "
                    "$i$, $z_i$ is the length of the longest common prefix "
                    "of $s$ and the suffix $s_i s_{i+1} \\dots$ By "
                    "convention $z_0 = 0$.\n\n"
                    "**Input**: one line, the string $s$ ($1 \\le |s| \\le "
                    "10^6$, lowercase).\n\n"
                    "**Output**: the $n$ values $z_0, \\dots, z_{n-1}$ "
                    "space-separated.\n\n"
                    "**Hint**: maintain a **window** $[l, r]$ = the segment "
                    "of the rightmost prefix found so far. If $i < r$, "
                    "initialize $z_i$ with the value already computed at "
                    "$i - l$, then extend. $O(n)$."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    s = sys.stdin.readline().rstrip('\\n')\n"
                    "    # TODO: Z-function.\n"
                    "    print()\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "aabaab\n", "expected": "0 1 0 3 1 0\n", "is_sample": True},
                    {"input": "aaaaa\n", "expected": "0 4 3 2 1\n", "is_sample": True},
                    {"input": "abcde\n", "expected": "0 0 0 0 0\n", "is_sample": False},
                    {"input": "abacaba\n", "expected": "0 0 1 0 3 0 1\n", "is_sample": False},
                    {"input": "abababab\n", "expected": "0 0 6 0 4 0 2 0\n", "is_sample": False},
                    {"input": "a\n", "expected": "0\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_TX_LONGEST_PALINDROME",
                "title_fr": "Plus long palindrome",
                "title_en": "Longest palindrome",
                "prompt_fr": (
                    "Trouver la **longueur** de la plus longue sous-chaine "
                    "**palindrome** de $s$.\n\n"
                    "**Entree** : une ligne, la chaine $s$ ($1 \\le |s| \\le "
                    "10^6$, minuscules).\n\n"
                    "**Sortie** : un seul entier.\n\n"
                    "**Indice** : algorithme de **Manacher**. En inserant "
                    "des separateurs `#` entre les caracteres, on traite "
                    "uniformement palindromes pairs et impairs, et on "
                    "calcule le rayon maximal autour de chaque centre en "
                    "$O(n)$ grace a une fenetre miroir."
                ),
                "prompt_en": (
                    "Find the **length** of the longest **palindromic** "
                    "substring of $s$.\n\n"
                    "**Input**: one line, the string $s$ ($1 \\le |s| \\le "
                    "10^6$, lowercase).\n\n"
                    "**Output**: one integer.\n\n"
                    "**Hint**: **Manacher's** algorithm. By inserting `#` "
                    "separators between characters, you handle even and odd "
                    "palindromes uniformly, and compute the maximum radius "
                    "around each center in $O(n)$ using a mirror window."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    s = sys.stdin.readline().rstrip('\\n')\n"
                    "    # TODO: Manacher.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "babad\n", "expected": "3\n", "is_sample": True},
                    {"input": "cbbd\n", "expected": "2\n", "is_sample": True},
                    {"input": "aaaa\n", "expected": "4\n", "is_sample": False},
                    {"input": "abcde\n", "expected": "1\n", "is_sample": False},
                    {"input": "forgeeksskeegfor\n", "expected": "10\n", "is_sample": False},
                    {"input": "a\n", "expected": "1\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_TX_COUNT_PALINDROMES",
                "title_fr": "Nombre de sous-chaines palindromes",
                "title_en": "Count palindromic substrings",
                "prompt_fr": (
                    "Compter le **nombre total** de sous-chaines "
                    "palindromes de $s$ (toutes positions et longueurs ; "
                    "les occurrences identiques a des positions differentes "
                    "comptent separement).\n\n"
                    "**Entree** : une ligne, la chaine $s$ ($1 \\le |s| \\le "
                    "10^6$, minuscules).\n\n"
                    "**Sortie** : un seul entier.\n\n"
                    "**Indice** : Manacher donne, pour chaque centre, le "
                    "rayon du plus grand palindrome ; le nombre de "
                    "palindromes centres la est $\\lceil (\\text{rayon}+1)/2 "
                    "\\rceil$ apres transformation. La somme sur tous les "
                    "centres est la reponse, en $O(n)$."
                ),
                "prompt_en": (
                    "Count the **total number** of palindromic substrings "
                    "of $s$ (all positions and lengths; identical "
                    "occurrences at different positions count "
                    "separately).\n\n"
                    "**Input**: one line, the string $s$ ($1 \\le |s| \\le "
                    "10^6$, lowercase).\n\n"
                    "**Output**: one integer.\n\n"
                    "**Hint**: Manacher gives, for each center, the radius "
                    "of the largest palindrome; the number of palindromes "
                    "centered there is $\\lceil (\\text{radius}+1)/2 "
                    "\\rceil$ after the transform. The sum over all centers "
                    "is the answer, in $O(n)$."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    s = sys.stdin.readline().rstrip('\\n')\n"
                    "    # TODO: Manacher; sum palindrome counts.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "aaa\n", "expected": "6\n", "is_sample": True},
                    {"input": "abc\n", "expected": "3\n", "is_sample": True},
                    {"input": "ababa\n", "expected": "9\n", "is_sample": False},
                    {"input": "aaaa\n", "expected": "10\n", "is_sample": False},
                    {"input": "abba\n", "expected": "6\n", "is_sample": False},
                    {"input": "racecar\n", "expected": "10\n", "is_sample": False},
                ],
            },
        ],
    },

    # =================================================================
    # Lesson 4 - Suffix array & LCP
    # =================================================================
    {
        "slug": "suffix-array",
        "title_fr": "Suffix array & LCP",
        "title_en": "Suffix Array & LCP",
        "order_idx": 3,
        "content_fr_file": "lesson_04_suffix_array.fr.md",
        "content_en_file": "lesson_04_suffix_array.en.md",
        "exercises": [
            {
                "key": "EX_TX_SUFFIX_ARRAY",
                "title_fr": "Construction du suffix array",
                "title_en": "Suffix array construction",
                "prompt_fr": (
                    "Construire le **suffix array** de $s$ : la liste des "
                    "indices de depart (0-indexes) des suffixes de $s$, "
                    "**tries** par ordre lexicographique.\n\n"
                    "**Entree** : une ligne, la chaine $s$ ($1 \\le |s| \\le "
                    "10^5$, minuscules).\n\n"
                    "**Sortie** : les $n$ indices separes par des espaces.\n\n"
                    "**Indice** : tri par **doublement** - trier les "
                    "suffixes par leurs $2^k$ premiers caracteres en "
                    "reutilisant les rangs de l'etape $2^{k-1}$. "
                    "$O(n \\log^2 n)$ (ou $O(n \\log n)$ avec un tri par "
                    "comptage)."
                ),
                "prompt_en": (
                    "Build the **suffix array** of $s$: the list of starting "
                    "indices (0-indexed) of the suffixes of $s$, **sorted** "
                    "in lexicographic order.\n\n"
                    "**Input**: one line, the string $s$ ($1 \\le |s| \\le "
                    "10^5$, lowercase).\n\n"
                    "**Output**: the $n$ indices space-separated.\n\n"
                    "**Hint**: **prefix-doubling** sort - sort suffixes by "
                    "their first $2^k$ characters, reusing the ranks from "
                    "step $2^{k-1}$. $O(n \\log^2 n)$ (or $O(n \\log n)$ "
                    "with a counting sort)."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    s = sys.stdin.readline().rstrip('\\n')\n"
                    "    # TODO: build suffix array.\n"
                    "    print()\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "banana\n", "expected": "5 3 1 0 4 2\n", "is_sample": True},
                    {"input": "abab\n", "expected": "2 0 3 1\n", "is_sample": True},
                    {"input": "aaaa\n", "expected": "3 2 1 0\n", "is_sample": False},
                    {"input": "abcde\n", "expected": "0 1 2 3 4\n", "is_sample": False},
                    {"input": "mississippi\n", "expected": "10 7 4 1 0 9 8 6 3 5 2\n", "is_sample": False},
                    {"input": "a\n", "expected": "0\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_TX_DISTINCT_SUBSTR_TOTAL",
                "title_fr": "Nombre de sous-chaines distinctes",
                "title_en": "Total distinct substrings",
                "prompt_fr": (
                    "Compter le nombre total de sous-chaines **distinctes** "
                    "(toutes longueurs) d'une chaine $s$.\n\n"
                    "**Entree** : une ligne, la chaine $s$ ($1 \\le |s| \\le "
                    "10^5$, minuscules).\n\n"
                    "**Sortie** : un seul entier.\n\n"
                    "**Indice** : il y a $\\frac{n(n+1)}{2}$ sous-chaines au "
                    "total (avec repetitions). Le tableau **LCP** (via "
                    "Kasai) compte les prefixes communs entre suffixes "
                    "adjacents du suffix array ; la reponse est "
                    "$\\frac{n(n+1)}{2} - \\sum_i \\text{LCP}[i]$."
                ),
                "prompt_en": (
                    "Count the total number of **distinct** substrings (all "
                    "lengths) of a string $s$.\n\n"
                    "**Input**: one line, the string $s$ ($1 \\le |s| \\le "
                    "10^5$, lowercase).\n\n"
                    "**Output**: one integer.\n\n"
                    "**Hint**: there are $\\frac{n(n+1)}{2}$ substrings in "
                    "total (with repetitions). The **LCP** array (via Kasai) "
                    "counts common prefixes between adjacent suffixes of the "
                    "suffix array; the answer is $\\frac{n(n+1)}{2} - "
                    "\\sum_i \\text{LCP}[i]$."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    s = sys.stdin.readline().rstrip('\\n')\n"
                    "    # TODO: suffix array + LCP (Kasai).\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "banana\n", "expected": "15\n", "is_sample": True},
                    {"input": "aaaa\n", "expected": "4\n", "is_sample": True},
                    {"input": "abc\n", "expected": "6\n", "is_sample": False},
                    {"input": "abab\n", "expected": "7\n", "is_sample": False},
                    {"input": "mississippi\n", "expected": "53\n", "is_sample": False},
                    {"input": "a\n", "expected": "1\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_TX_LRS",
                "title_fr": "Plus longue sous-chaine repetee",
                "title_en": "Longest repeated substring",
                "prompt_fr": (
                    "Trouver la **longueur** de la plus longue sous-chaine "
                    "qui apparait **au moins deux fois** dans $s$ "
                    "(chevauchements autorises).\n\n"
                    "**Entree** : une ligne, la chaine $s$ ($1 \\le |s| \\le "
                    "10^5$, minuscules).\n\n"
                    "**Sortie** : un seul entier (0 si aucune "
                    "repetition).\n\n"
                    "**Indice** : deux suffixes partageant un long prefixe "
                    "sont **adjacents** dans le suffix array. La reponse est "
                    "donc le **maximum** du tableau LCP."
                ),
                "prompt_en": (
                    "Find the **length** of the longest substring that "
                    "appears **at least twice** in $s$ (overlaps "
                    "allowed).\n\n"
                    "**Input**: one line, the string $s$ ($1 \\le |s| \\le "
                    "10^5$, lowercase).\n\n"
                    "**Output**: one integer (0 if no repetition).\n\n"
                    "**Hint**: two suffixes sharing a long prefix are "
                    "**adjacent** in the suffix array. So the answer is the "
                    "**maximum** of the LCP array."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    s = sys.stdin.readline().rstrip('\\n')\n"
                    "    # TODO: suffix array + LCP; take the max.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "banana\n", "expected": "3\n", "is_sample": True},
                    {"input": "abcabc\n", "expected": "3\n", "is_sample": True},
                    {"input": "abcde\n", "expected": "0\n", "is_sample": False},
                    {"input": "aaaa\n", "expected": "3\n", "is_sample": False},
                    {"input": "aabcaabxaaz\n", "expected": "3\n", "is_sample": False},
                    {"input": "a\n", "expected": "0\n", "is_sample": False},
                ],
            },
        ],
    },
]


REFERENCE_SOLUTIONS = {
    "EX_TX_RK_COUNT": r"""import sys
def main():
    data = sys.stdin.read().split('\n')
    t = data[0]; p = data[1] if len(data) > 1 else ''
    n, m = len(t), len(p)
    if m == 0 or m > n:
        print(0); return
    MOD = (1 << 61) - 1; B = 131
    hp = 0
    for c in p: hp = (hp * B + ord(c)) % MOD
    power = pow(B, m-1, MOD)
    h = 0
    for i in range(m): h = (h * B + ord(t[i])) % MOD
    cnt = 1 if (h == hp and t[:m] == p) else 0
    for i in range(m, n):
        h = ((h - ord(t[i-m]) * power) * B + ord(t[i])) % MOD
        if h == hp and t[i-m+1:i+1] == p:
            cnt += 1
    print(cnt)
main()
""",
    "EX_TX_DISTINCT_SUBSTR_K": r"""import sys
def main():
    data = sys.stdin.read().split('\n')
    s = data[0]; k = int(data[1])
    n = len(s)
    if k <= 0 or k > n:
        print(0); return
    print(len({s[i:i+k] for i in range(n-k+1)}))
main()
""",
    "EX_TX_LONGEST_COMMON_SUBSTR": r"""import sys
def main():
    data = sys.stdin.read().split('\n')
    s = data[0]; t = data[1] if len(data) > 1 else ''
    n, m = len(s), len(t)
    if n == 0 or m == 0:
        print(0); return
    prev = [0]*(m+1); best = 0
    for i in range(1, n+1):
        cur = [0]*(m+1)
        si = s[i-1]
        for j in range(1, m+1):
            if si == t[j-1]:
                v = prev[j-1]+1; cur[j] = v
                if v > best: best = v
        prev = cur
    print(best)
main()
""",
    "EX_TX_KMP_POSITIONS": r"""import sys
def main():
    data = sys.stdin.read().split('\n')
    t = data[0]; p = data[1] if len(data) > 1 else ''
    if len(p) == 0:
        print(); return
    s = p + '\x01' + t
    n = len(s); pi = [0]*n
    for i in range(1, n):
        j = pi[i-1]
        while j > 0 and s[i] != s[j]: j = pi[j-1]
        if s[i] == s[j]: j += 1
        pi[i] = j
    m = len(p); out = []
    for i in range(m+1, n):
        if pi[i] == m:
            out.append(str(i - 2*m + 1))
    sys.stdout.write(' '.join(out) + '\n')
main()
""",
    "EX_TX_MIN_PERIOD": r"""import sys
def main():
    s = sys.stdin.readline().rstrip('\n')
    n = len(s)
    if n == 0:
        print(0); return
    pi = [0]*n
    for i in range(1, n):
        j = pi[i-1]
        while j > 0 and s[i] != s[j]: j = pi[j-1]
        if s[i] == s[j]: j += 1
        pi[i] = j
    print(n - pi[n-1])
main()
""",
    "EX_TX_BORDERS": r"""import sys
def main():
    s = sys.stdin.readline().rstrip('\n')
    n = len(s)
    if n == 0:
        print(); return
    pi = [0]*n
    for i in range(1, n):
        j = pi[i-1]
        while j > 0 and s[i] != s[j]: j = pi[j-1]
        if s[i] == s[j]: j += 1
        pi[i] = j
    res = []; k = pi[n-1]
    while k > 0:
        res.append(k); k = pi[k-1]
    res.reverse()
    sys.stdout.write(' '.join(map(str, res)) + '\n')
main()
""",
    "EX_TX_ZFUNC": r"""import sys
def main():
    s = sys.stdin.readline().rstrip('\n')
    n = len(s); z = [0]*n
    l = r = 0
    for i in range(1, n):
        if i < r: z[i] = min(r-i, z[i-l])
        while i+z[i] < n and s[z[i]] == s[i+z[i]]: z[i] += 1
        if i+z[i] > r: l, r = i, i+z[i]
    sys.stdout.write(' '.join(map(str, z)) + '\n')
main()
""",
    "EX_TX_LONGEST_PALINDROME": r"""import sys
def main():
    s = sys.stdin.readline().rstrip('\n')
    if not s:
        print(0); return
    t = '#' + '#'.join(s) + '#'
    n = len(t); p = [0]*n; c = r = 0
    for i in range(n):
        if i < r: p[i] = min(r-i, p[2*c-i])
        while i-p[i]-1 >= 0 and i+p[i]+1 < n and t[i-p[i]-1] == t[i+p[i]+1]:
            p[i] += 1
        if i+p[i] > r: c, r = i, i+p[i]
    print(max(p))
main()
""",
    "EX_TX_COUNT_PALINDROMES": r"""import sys
def main():
    s = sys.stdin.readline().rstrip('\n')
    if not s:
        print(0); return
    t = '#' + '#'.join(s) + '#'
    n = len(t); p = [0]*n; c = r = 0
    for i in range(n):
        if i < r: p[i] = min(r-i, p[2*c-i])
        while i-p[i]-1 >= 0 and i+p[i]+1 < n and t[i-p[i]-1] == t[i+p[i]+1]:
            p[i] += 1
        if i+p[i] > r: c, r = i, i+p[i]
    print(sum((v+1)//2 for v in p))
main()
""",
    "EX_TX_SUFFIX_ARRAY": r"""import sys
def main():
    s = sys.stdin.readline().rstrip('\n')
    n = len(s)
    if n == 0:
        print(); return
    sa = list(range(n))
    rank = [ord(c) for c in s]
    tmp = [0]*n; k = 1
    while True:
        def key(i):
            return (rank[i], rank[i+k] if i+k < n else -1)
        sa.sort(key=key)
        tmp[sa[0]] = 0
        for i in range(1, n):
            tmp[sa[i]] = tmp[sa[i-1]] + (1 if key(sa[i]) != key(sa[i-1]) else 0)
        rank = tmp[:]
        if rank[sa[-1]] == n-1: break
        k *= 2
    sys.stdout.write(' '.join(map(str, sa)) + '\n')
main()
""",
    "EX_TX_DISTINCT_SUBSTR_TOTAL": r"""import sys
def build_sa(s):
    n = len(s)
    sa = list(range(n))
    rank = [ord(c) for c in s]
    tmp = [0]*n; k = 1
    while True:
        def key(i):
            return (rank[i], rank[i+k] if i+k < n else -1)
        sa.sort(key=key)
        tmp[sa[0]] = 0
        for i in range(1, n):
            tmp[sa[i]] = tmp[sa[i-1]] + (1 if key(sa[i]) != key(sa[i-1]) else 0)
        rank = tmp[:]
        if rank[sa[-1]] == n-1: break
        k *= 2
    return sa
def lcp_array(s, sa):
    n = len(s); rank = [0]*n
    for i in range(n): rank[sa[i]] = i
    lcp = [0]*n; h = 0
    for i in range(n):
        if rank[i] > 0:
            j = sa[rank[i]-1]
            while i+h < n and j+h < n and s[i+h] == s[j+h]: h += 1
            lcp[rank[i]] = h
            if h > 0: h -= 1
        else:
            h = 0
    return lcp
def main():
    s = sys.stdin.readline().rstrip('\n')
    n = len(s)
    if n == 0:
        print(0); return
    sa = build_sa(s); lcp = lcp_array(s, sa)
    print(n*(n+1)//2 - sum(lcp))
main()
""",
    "EX_TX_LRS": r"""import sys
def build_sa(s):
    n = len(s)
    sa = list(range(n))
    rank = [ord(c) for c in s]
    tmp = [0]*n; k = 1
    while True:
        def key(i):
            return (rank[i], rank[i+k] if i+k < n else -1)
        sa.sort(key=key)
        tmp[sa[0]] = 0
        for i in range(1, n):
            tmp[sa[i]] = tmp[sa[i-1]] + (1 if key(sa[i]) != key(sa[i-1]) else 0)
        rank = tmp[:]
        if rank[sa[-1]] == n-1: break
        k *= 2
    return sa
def main():
    s = sys.stdin.readline().rstrip('\n')
    n = len(s)
    if n <= 1:
        print(0); return
    sa = build_sa(s)
    rank = [0]*n
    for i in range(n): rank[sa[i]] = i
    h = 0; best = 0
    for i in range(n):
        if rank[i] > 0:
            j = sa[rank[i]-1]
            while i+h < n and j+h < n and s[i+h] == s[j+h]: h += 1
            if h > best: best = h
            if h > 0: h -= 1
        else:
            h = 0
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
                    f"      - exercise {ex['key']:<26} "
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
    print(f"Chapitre 8 - Algorithmique du texte : OK ({state}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
