"""Seed Chapter 9 - Maths pour la competition.

Cree (ou met a jour) la section ``maths-cp`` avec quatre lecons :

  1. Arithmetique modulaire (exponentiation rapide, inverse)
  2. Cribles, primalite & CRT
  3. Combinatoire (binomiaux mod p, Lucas, Catalan)
  4. Convolutions (FFT / NTT)

Chaque lecon contient trois exercices inline gradues (standard,
twist, dur). Idempotent.

Pre-deploiement le script verifie que chaque solution de reference
passe sur ses test cases (--validate-only pour ne faire QUE ca).

Usage:
    python scripts/seed_chapter9/seed_chapter9.py
    python scripts/seed_chapter9/seed_chapter9.py --draft
    python scripts/seed_chapter9/seed_chapter9.py --validate-only
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
    "slug": "maths-cp",
    "title_fr": "Maths pour la competition",
    "title_en": "Competitive Math",
    "description_fr": (
        "La boite a outils mathematique du competiteur : arithmetique "
        "modulaire (exponentiation rapide, inverse par Fermat et Euclide "
        "etendu), cribles et tests de primalite (Miller-Rabin), theoreme "
        "des restes chinois, coefficients binomiaux modulaires et theoreme "
        "de Lucas, et convolutions rapides par FFT/NTT."
    ),
    "description_en": (
        "The competitor's mathematical toolbox: modular arithmetic (fast "
        "exponentiation, inverse via Fermat and extended Euclid), sieves "
        "and primality tests (Miller-Rabin), the Chinese remainder "
        "theorem, modular binomial coefficients and Lucas' theorem, and "
        "fast convolutions via FFT/NTT."
    ),
    "order_idx": 8,
}


LESSONS: list[dict] = [
    # =================================================================
    # Lesson 1 - Arithmetique modulaire
    # =================================================================
    {
        "slug": "arithmetique-modulaire",
        "title_fr": "Arithmetique modulaire",
        "title_en": "Modular Arithmetic",
        "order_idx": 0,
        "content_fr_file": "lesson_01_modular.fr.md",
        "content_en_file": "lesson_01_modular.en.md",
        "exercises": [
            {
                "key": "EX_MA_MODEXP",
                "title_fr": "Exponentiation modulaire",
                "title_en": "Modular exponentiation",
                "prompt_fr": (
                    "Calculer $a^b \\bmod m$.\n\n"
                    "**Entree** : une ligne, trois entiers $a$, $b$, $m$ "
                    "($0 \\le a, b \\le 10^{18}$, $1 \\le m \\le "
                    "10^{18}$).\n\n"
                    "**Sortie** : un seul entier dans $[0, m)$.\n\n"
                    "**Indice** : exponentiation rapide (par carres). "
                    "$a^b = (a^{b/2})^2$ si $b$ est pair, "
                    "$a \\cdot a^{b-1}$ sinon - $O(\\log b)$ "
                    "multiplications, chacune reduite modulo $m$ pour eviter "
                    "tout debordement."
                ),
                "prompt_en": (
                    "Compute $a^b \\bmod m$.\n\n"
                    "**Input**: one line, three integers $a$, $b$, $m$ "
                    "($0 \\le a, b \\le 10^{18}$, $1 \\le m \\le "
                    "10^{18}$).\n\n"
                    "**Output**: one integer in $[0, m)$.\n\n"
                    "**Hint**: fast exponentiation (by squaring). "
                    "$a^b = (a^{b/2})^2$ if $b$ is even, $a \\cdot a^{b-1}$ "
                    "otherwise - $O(\\log b)$ multiplications, each reduced "
                    "modulo $m$ to avoid overflow."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    a, b, m = map(int, sys.stdin.readline().split())\n"
                    "    # TODO: fast modular exponentiation.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "2 10 1000\n", "expected": "24\n", "is_sample": True},
                    {"input": "3 0 7\n", "expected": "1\n", "is_sample": True},
                    {"input": "7 100 13\n", "expected": "9\n", "is_sample": False},
                    {"input": "2 1000000000000000000 1000000007\n", "expected": "719476260\n", "is_sample": False},
                    {"input": "5 3 1\n", "expected": "0\n", "is_sample": False},
                    {"input": "123456 789 1000000007\n", "expected": "182677862\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_MA_MODINV",
                "title_fr": "Inverse modulaire",
                "title_en": "Modular inverse",
                "prompt_fr": (
                    "Calculer l'inverse de $a$ modulo $m$ : l'entier "
                    "$x \\in [0, m)$ tel que $a x \\equiv 1 \\pmod m$.\n\n"
                    "**Entree** : une ligne, deux entiers $a$ et $m$ "
                    "($1 \\le a, m \\le 10^{18}$). $m$ **n'est pas "
                    "necessairement premier**.\n\n"
                    "**Sortie** : l'inverse, ou $-1$ s'il n'existe pas "
                    "(c'est-a-dire si $\\gcd(a, m) \\ne 1$).\n\n"
                    "**Indice** : l'algorithme d'**Euclide etendu** donne "
                    "$x, y$ tels que $a x + m y = \\gcd(a, m)$. Si le pgcd "
                    "vaut $1$, alors $x \\bmod m$ est l'inverse. (Si $m$ est "
                    "premier, $a^{m-2} \\bmod m$ marche aussi, par le petit "
                    "theoreme de Fermat.)"
                ),
                "prompt_en": (
                    "Compute the inverse of $a$ modulo $m$: the integer "
                    "$x \\in [0, m)$ with $a x \\equiv 1 \\pmod m$.\n\n"
                    "**Input**: one line, two integers $a$ and $m$ "
                    "($1 \\le a, m \\le 10^{18}$). $m$ is **not necessarily "
                    "prime**.\n\n"
                    "**Output**: the inverse, or $-1$ if it does not exist "
                    "(i.e. if $\\gcd(a, m) \\ne 1$).\n\n"
                    "**Hint**: the **extended Euclidean** algorithm gives "
                    "$x, y$ with $a x + m y = \\gcd(a, m)$. If the gcd is "
                    "$1$, then $x \\bmod m$ is the inverse. (If $m$ is "
                    "prime, $a^{m-2} \\bmod m$ also works, by Fermat's "
                    "little theorem.)"
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    a, m = map(int, sys.stdin.readline().split())\n"
                    "    # TODO: extended Euclid; inverse or -1.\n"
                    "    print(-1)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "3 11\n", "expected": "4\n", "is_sample": True},
                    {"input": "4 8\n", "expected": "-1\n", "is_sample": True},
                    {"input": "2 1000000007\n", "expected": "500000004\n", "is_sample": False},
                    {"input": "6 9\n", "expected": "-1\n", "is_sample": False},
                    {"input": "1 5\n", "expected": "1\n", "is_sample": False},
                    {"input": "10 17\n", "expected": "12\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_MA_LINCONG",
                "title_fr": "Congruence lineaire",
                "title_en": "Linear congruence",
                "prompt_fr": (
                    "Resoudre $a x \\equiv b \\pmod m$ pour l'inconnue "
                    "$x$.\n\n"
                    "**Entree** : une ligne, trois entiers $a$, $b$, $m$ "
                    "($0 \\le a, b \\le 10^{18}$, $1 \\le m \\le "
                    "10^{18}$).\n\n"
                    "**Sortie** : la **plus petite** solution non negative "
                    "$x$, ou $-1$ si aucune solution n'existe.\n\n"
                    "**Indice** : soit $g = \\gcd(a, m)$. Il y a une "
                    "solution **ssi** $g \\mid b$. Dans ce cas, diviser par "
                    "$g$ donne $a' x \\equiv b' \\pmod{m'}$ avec "
                    "$\\gcd(a', m') = 1$, et $x = b' \\cdot (a')^{-1} \\bmod "
                    "m'$ est la plus petite solution non negative."
                ),
                "prompt_en": (
                    "Solve $a x \\equiv b \\pmod m$ for the unknown "
                    "$x$.\n\n"
                    "**Input**: one line, three integers $a$, $b$, $m$ "
                    "($0 \\le a, b \\le 10^{18}$, $1 \\le m \\le "
                    "10^{18}$).\n\n"
                    "**Output**: the **smallest** non-negative solution "
                    "$x$, or $-1$ if no solution exists.\n\n"
                    "**Hint**: let $g = \\gcd(a, m)$. A solution exists "
                    "**iff** $g \\mid b$. Then dividing by $g$ gives "
                    "$a' x \\equiv b' \\pmod{m'}$ with $\\gcd(a', m') = 1$, "
                    "and $x = b' \\cdot (a')^{-1} \\bmod m'$ is the smallest "
                    "non-negative solution."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    a, b, m = map(int, sys.stdin.readline().split())\n"
                    "    # TODO: solve a x = b (mod m).\n"
                    "    print(-1)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "3 6 9\n", "expected": "2\n", "is_sample": True},
                    {"input": "2 3 4\n", "expected": "-1\n", "is_sample": True},
                    {"input": "4 2 6\n", "expected": "2\n", "is_sample": False},
                    {"input": "5 3 7\n", "expected": "2\n", "is_sample": False},
                    {"input": "6 4 10\n", "expected": "4\n", "is_sample": False},
                    {"input": "14 30 100\n", "expected": "45\n", "is_sample": False},
                ],
            },
        ],
    },

    # =================================================================
    # Lesson 2 - Cribles, primalite & CRT
    # =================================================================
    {
        "slug": "primalite-crt",
        "title_fr": "Cribles, primalite & CRT",
        "title_en": "Sieves, Primality & CRT",
        "order_idx": 1,
        "content_fr_file": "lesson_02_primality.fr.md",
        "content_en_file": "lesson_02_primality.en.md",
        "exercises": [
            {
                "key": "EX_MA_SIEVE_COUNT",
                "title_fr": "Nombre de premiers",
                "title_en": "Count of primes",
                "prompt_fr": (
                    "Compter le nombre de nombres premiers $\\le n$.\n\n"
                    "**Entree** : une ligne, l'entier $n$ ($1 \\le n \\le "
                    "10^7$).\n\n"
                    "**Sortie** : un seul entier.\n\n"
                    "**Indice** : crible d'**Eratosthene**. Marquer les "
                    "multiples de chaque premier a partir de $p^2$. "
                    "$O(n \\log \\log n)$."
                ),
                "prompt_en": (
                    "Count the prime numbers $\\le n$.\n\n"
                    "**Input**: one line, the integer $n$ ($1 \\le n \\le "
                    "10^7$).\n\n"
                    "**Output**: one integer.\n\n"
                    "**Hint**: sieve of **Eratosthenes**. Mark the multiples "
                    "of each prime starting at $p^2$. $O(n \\log \\log n)$."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    n = int(sys.stdin.readline())\n"
                    "    # TODO: sieve; count primes.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "10\n", "expected": "4\n", "is_sample": True},
                    {"input": "2\n", "expected": "1\n", "is_sample": True},
                    {"input": "1\n", "expected": "0\n", "is_sample": False},
                    {"input": "100\n", "expected": "25\n", "is_sample": False},
                    {"input": "1000\n", "expected": "168\n", "is_sample": False},
                    {"input": "30\n", "expected": "10\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_MA_MILLER_RABIN",
                "title_fr": "Test de primalite (Miller-Rabin)",
                "title_en": "Primality test (Miller-Rabin)",
                "prompt_fr": (
                    "Determiner si un entier $n$ est premier.\n\n"
                    "**Entree** : une ligne, l'entier $n$ ($1 \\le n \\le "
                    "10^{18}$).\n\n"
                    "**Sortie** : `1` si $n$ est premier, `0` sinon.\n\n"
                    "**Indice** : test de **Miller-Rabin** deterministe. "
                    "Ecrire $n - 1 = 2^r d$ ($d$ impair) ; pour un ensemble "
                    "fixe de temoins (les 12 premiers premiers suffisent "
                    "sous $3{.}3 \\cdot 10^{24}$), verifier que $a^d \\equiv "
                    "1$ ou $a^{2^i d} \\equiv -1$. Sinon $n$ est compose."
                ),
                "prompt_en": (
                    "Decide whether an integer $n$ is prime.\n\n"
                    "**Input**: one line, the integer $n$ ($1 \\le n \\le "
                    "10^{18}$).\n\n"
                    "**Output**: `1` if $n$ is prime, `0` otherwise.\n\n"
                    "**Hint**: deterministic **Miller-Rabin** test. Write "
                    "$n - 1 = 2^r d$ ($d$ odd); for a fixed set of witnesses "
                    "(the first 12 primes suffice below $3{.}3 \\cdot "
                    "10^{24}$), check that $a^d \\equiv 1$ or $a^{2^i d} "
                    "\\equiv -1$. Otherwise $n$ is composite."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    n = int(sys.stdin.readline())\n"
                    "    # TODO: deterministic Miller-Rabin.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "7\n", "expected": "1\n", "is_sample": True},
                    {"input": "1\n", "expected": "0\n", "is_sample": True},
                    {"input": "561\n", "expected": "0\n", "is_sample": False},
                    {"input": "1000000007\n", "expected": "1\n", "is_sample": False},
                    {"input": "1000000000000000003\n", "expected": "1\n", "is_sample": False},
                    {"input": "999999999999999989\n", "expected": "1\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_MA_CRT",
                "title_fr": "Theoreme des restes chinois",
                "title_en": "Chinese remainder theorem",
                "prompt_fr": (
                    "Resoudre un systeme de congruences $x \\equiv a_i "
                    "\\pmod{m_i}$ pour $i = 1, \\dots, k$. Les modulos ne "
                    "sont **pas necessairement premiers entre eux**.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $k$ ($1 \\le k \\le 10^5$)\n"
                    "- $k$ lignes : $a_i$ et $m_i$ ($0 \\le a_i < m_i$, "
                    "$1 \\le m_i \\le 10^9$)\n\n"
                    "**Sortie** : la **plus petite** solution non negative "
                    "$x$, ou $-1$ si le systeme est incompatible.\n\n"
                    "**Indice** : fusionner les congruences deux a deux. "
                    "Deux congruences $(a_1, m_1)$ et $(a_2, m_2)$ sont "
                    "compatibles **ssi** $\\gcd(m_1, m_2) \\mid (a_2 - "
                    "a_1)$ ; leur fusion a pour modulo $\\text{lcm}(m_1, "
                    "m_2)$, calculee via Euclide etendu."
                ),
                "prompt_en": (
                    "Solve a system of congruences $x \\equiv a_i "
                    "\\pmod{m_i}$ for $i = 1, \\dots, k$. The moduli are "
                    "**not necessarily coprime**.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $k$ ($1 \\le k \\le 10^5$)\n"
                    "- $k$ lines: $a_i$ and $m_i$ ($0 \\le a_i < m_i$, "
                    "$1 \\le m_i \\le 10^9$)\n\n"
                    "**Output**: the **smallest** non-negative solution "
                    "$x$, or $-1$ if the system is inconsistent.\n\n"
                    "**Hint**: merge the congruences pairwise. Two "
                    "congruences $(a_1, m_1)$ and $(a_2, m_2)$ are "
                    "compatible **iff** $\\gcd(m_1, m_2) \\mid (a_2 - a_1)$; "
                    "their merge has modulus $\\text{lcm}(m_1, m_2)$, "
                    "computed via extended Euclid."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    k = int(data[0]); idx = 1\n"
                    "    # TODO: merge congruences pairwise (general CRT).\n"
                    "    print(-1)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "2\n2 3\n3 5\n", "expected": "8\n", "is_sample": True},
                    {"input": "2\n1 2\n0 4\n", "expected": "-1\n", "is_sample": True},
                    {"input": "3\n2 3\n3 5\n2 7\n", "expected": "23\n", "is_sample": False},
                    {"input": "2\n0 6\n1 4\n", "expected": "-1\n", "is_sample": False},
                    {"input": "2\n1 6\n4 9\n", "expected": "13\n", "is_sample": False},
                    {"input": "1\n5 13\n", "expected": "5\n", "is_sample": False},
                ],
            },
        ],
    },

    # =================================================================
    # Lesson 3 - Combinatoire
    # =================================================================
    {
        "slug": "combinatoire",
        "title_fr": "Combinatoire modulaire",
        "title_en": "Modular Combinatorics",
        "order_idx": 2,
        "content_fr_file": "lesson_03_combinatorics.fr.md",
        "content_en_file": "lesson_03_combinatorics.en.md",
        "exercises": [
            {
                "key": "EX_MA_BINOM",
                "title_fr": "Coefficient binomial mod p",
                "title_en": "Binomial coefficient mod p",
                "prompt_fr": (
                    "Calculer $\\binom{n}{k} \\bmod p$.\n\n"
                    "**Entree** : une ligne, trois entiers $n$, $k$, $p$ "
                    "($0 \\le k \\le n \\le 10^6$, $p$ **premier** avec "
                    "$p > n$).\n\n"
                    "**Sortie** : un seul entier.\n\n"
                    "**Indice** : $\\binom{n}{k} = \\frac{n!}{k!\\,(n-k)!}$. "
                    "Precalculer les factorielles modulo $p$ ; la division "
                    "devient une multiplication par l'**inverse "
                    "modulaire** (Fermat, car $p$ est premier). Comme "
                    "$p > n$, aucun facteur $p$ n'apparait au denominateur."
                ),
                "prompt_en": (
                    "Compute $\\binom{n}{k} \\bmod p$.\n\n"
                    "**Input**: one line, three integers $n$, $k$, $p$ "
                    "($0 \\le k \\le n \\le 10^6$, $p$ **prime** with "
                    "$p > n$).\n\n"
                    "**Output**: one integer.\n\n"
                    "**Hint**: $\\binom{n}{k} = \\frac{n!}{k!\\,(n-k)!}$. "
                    "Precompute factorials modulo $p$; the division becomes "
                    "a multiplication by the **modular inverse** (Fermat, "
                    "since $p$ is prime). Because $p > n$, no factor of $p$ "
                    "appears in the denominator."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    n, k, p = map(int, sys.stdin.readline().split())\n"
                    "    # TODO: factorials mod p + modular inverse.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5 2 1000000007\n", "expected": "10\n", "is_sample": True},
                    {"input": "10 0 1009\n", "expected": "1\n", "is_sample": True},
                    {"input": "1000000 500000 1000000007\n", "expected": "996692777\n", "is_sample": False},
                    {"input": "6 3 1000000007\n", "expected": "20\n", "is_sample": False},
                    {"input": "20 10 998244353\n", "expected": "184756\n", "is_sample": False},
                    {"input": "100 50 1000000007\n", "expected": "538992043\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_MA_LUCAS",
                "title_fr": "Theoreme de Lucas",
                "title_en": "Lucas' theorem",
                "prompt_fr": (
                    "Calculer $\\binom{n}{k} \\bmod p$ pour des $n$, $k$ "
                    "**tres grands** et un petit premier $p$.\n\n"
                    "**Entree** : une ligne, $n$, $k$, $p$ "
                    "($0 \\le k \\le n \\le 10^{18}$, $p$ premier, "
                    "$p \\le 10^5$).\n\n"
                    "**Sortie** : un seul entier.\n\n"
                    "**Indice** : theoreme de **Lucas**. Ecrire $n$ et $k$ "
                    "en base $p$ ; alors $\\binom{n}{k} \\equiv \\prod_i "
                    "\\binom{n_i}{k_i} \\pmod p$, ou $n_i, k_i$ sont les "
                    "chiffres. Chaque petit binomial (chiffres $< p$) se "
                    "calcule directement."
                ),
                "prompt_en": (
                    "Compute $\\binom{n}{k} \\bmod p$ for **very large** "
                    "$n$, $k$ and a small prime $p$.\n\n"
                    "**Input**: one line, $n$, $k$, $p$ "
                    "($0 \\le k \\le n \\le 10^{18}$, $p$ prime, "
                    "$p \\le 10^5$).\n\n"
                    "**Output**: one integer.\n\n"
                    "**Hint**: **Lucas'** theorem. Write $n$ and $k$ in base "
                    "$p$; then $\\binom{n}{k} \\equiv \\prod_i "
                    "\\binom{n_i}{k_i} \\pmod p$, where $n_i, k_i$ are the "
                    "digits. Each small binomial (digits $< p$) is computed "
                    "directly."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    n, k, p = map(int, sys.stdin.readline().split())\n"
                    "    # TODO: Lucas' theorem.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "6 2 3\n", "expected": "0\n", "is_sample": True},
                    {"input": "10 3 7\n", "expected": "1\n", "is_sample": True},
                    {"input": "1000000000000 500000000000 13\n", "expected": "0\n", "is_sample": False},
                    {"input": "100 50 5\n", "expected": "1\n", "is_sample": False},
                    {"input": "999999999999999999 123456789 11\n", "expected": "0\n", "is_sample": False},
                    {"input": "7 7 2\n", "expected": "1\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_MA_CATALAN",
                "title_fr": "Nombre de Catalan mod p",
                "title_en": "Catalan number mod p",
                "prompt_fr": (
                    "Calculer le $n$-ieme nombre de **Catalan** modulo "
                    "$p$ : $C_n = \\frac{1}{n+1} \\binom{2n}{n}$.\n\n"
                    "**Entree** : une ligne, deux entiers $n$ et $p$ "
                    "($0 \\le n \\le 10^6$, $p$ **premier** avec "
                    "$p > 2n$).\n\n"
                    "**Sortie** : un seul entier - $C_n \\bmod p$.\n\n"
                    "**Indice** : $C_n = \\binom{2n}{n} \\cdot (n+1)^{-1} "
                    "\\bmod p$. Precalculer les factorielles jusqu'a $2n$ ; "
                    "comme $p > 2n$, tous les inverses existent. Les nombres "
                    "de Catalan comptent les arbres binaires, les "
                    "parenthesages valides, les chemins de Dyck..."
                ),
                "prompt_en": (
                    "Compute the $n$-th **Catalan** number modulo $p$: "
                    "$C_n = \\frac{1}{n+1} \\binom{2n}{n}$.\n\n"
                    "**Input**: one line, two integers $n$ and $p$ "
                    "($0 \\le n \\le 10^6$, $p$ **prime** with "
                    "$p > 2n$).\n\n"
                    "**Output**: one integer - $C_n \\bmod p$.\n\n"
                    "**Hint**: $C_n = \\binom{2n}{n} \\cdot (n+1)^{-1} "
                    "\\bmod p$. Precompute factorials up to $2n$; since "
                    "$p > 2n$, all inverses exist. Catalan numbers count "
                    "binary trees, valid parenthesizations, Dyck paths..."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    n, p = map(int, sys.stdin.readline().split())\n"
                    "    # TODO: C(2n,n) * inv(n+1) mod p.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "3 1000000007\n", "expected": "5\n", "is_sample": True},
                    {"input": "0 1000000007\n", "expected": "1\n", "is_sample": True},
                    {"input": "5 1000000007\n", "expected": "42\n", "is_sample": False},
                    {"input": "10 998244353\n", "expected": "16796\n", "is_sample": False},
                    {"input": "1 7\n", "expected": "1\n", "is_sample": False},
                    {"input": "20 1000000007\n", "expected": "564120378\n", "is_sample": False},
                ],
            },
        ],
    },

    # =================================================================
    # Lesson 4 - Convolutions (FFT / NTT)
    # =================================================================
    {
        "slug": "convolutions",
        "title_fr": "Convolutions (FFT / NTT)",
        "title_en": "Convolutions (FFT / NTT)",
        "order_idx": 3,
        "content_fr_file": "lesson_04_fft.fr.md",
        "content_en_file": "lesson_04_fft.en.md",
        "exercises": [
            {
                "key": "EX_MA_POLYMUL",
                "title_fr": "Multiplication de polynomes",
                "title_en": "Polynomial multiplication",
                "prompt_fr": (
                    "Multiplier deux polynomes modulo $998244353$.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ et $m$ (nombres de coefficients, "
                    "$1 \\le n, m \\le 2 \\cdot 10^5$)\n"
                    "- ligne 2 : $n$ coefficients de $A$ (du degre 0 vers "
                    "le haut)\n"
                    "- ligne 3 : $m$ coefficients de $B$\n\n"
                    "avec $0 \\le \\text{coeff} < 998244353$.\n\n"
                    "**Sortie** : les $n + m - 1$ coefficients du produit "
                    "$A \\cdot B$, separes par des espaces, modulo "
                    "$998244353$.\n\n"
                    "**Indice** : la multiplication naive est $O(nm)$. La "
                    "**NTT** (transformee de Fourier sur les entiers modulo "
                    "$998244353 = 119 \\cdot 2^{23} + 1$) evalue, multiplie "
                    "point a point, puis interpole - le tout en "
                    "$O((n+m) \\log(n+m))$."
                ),
                "prompt_en": (
                    "Multiply two polynomials modulo $998244353$.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $m$ (number of coefficients, "
                    "$1 \\le n, m \\le 2 \\cdot 10^5$)\n"
                    "- line 2: $n$ coefficients of $A$ (from degree 0 "
                    "upward)\n"
                    "- line 3: $m$ coefficients of $B$\n\n"
                    "with $0 \\le \\text{coeff} < 998244353$.\n\n"
                    "**Output**: the $n + m - 1$ coefficients of the product "
                    "$A \\cdot B$, space-separated, modulo $998244353$.\n\n"
                    "**Hint**: naive multiplication is $O(nm)$. The **NTT** "
                    "(Fourier transform over integers modulo "
                    "$998244353 = 119 \\cdot 2^{23} + 1$) evaluates, "
                    "multiplies pointwise, then interpolates - all in "
                    "$O((n+m) \\log(n+m))$."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n, m = int(data[0]), int(data[1])\n"
                    "    A = list(map(int, data[2:2+n]))\n"
                    "    B = list(map(int, data[2+n:2+n+m]))\n"
                    "    # TODO: NTT convolution mod 998244353.\n"
                    "    print()\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "2 2\n1 2\n3 4\n", "expected": "3 10 8\n", "is_sample": True},
                    {"input": "1 1\n5\n7\n", "expected": "35\n", "is_sample": True},
                    {"input": "3 2\n1 0 2\n1 1\n", "expected": "1 1 2 2\n", "is_sample": False},
                    {"input": "2 3\n2 3\n1 0 4\n", "expected": "2 3 8 12\n", "is_sample": False},
                    {"input": "4 1\n1 2 3 4\n2\n", "expected": "2 4 6 8\n", "is_sample": False},
                    {"input": "2 2\n1000000000 1000000000\n1000000000 1000000000\n", "expected": "716070898 433897443 716070898\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_MA_PAIR_SUMS",
                "title_fr": "Comptage de sommes de paires",
                "title_en": "Pair-sum counting",
                "prompt_fr": (
                    "Etant donnes deux tableaux $A$ et $B$ d'entiers dans "
                    "$[0, K]$, compter, pour chaque somme $s \\in [0, 2K]$, "
                    "le nombre de paires $(i, j)$ avec $A_i + B_j = s$.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n_A$, $n_B$, $K$ ($1 \\le n_A, n_B \\le "
                    "2000$, $1 \\le K \\le 2000$)\n"
                    "- ligne 2 : $n_A$ entiers de $A$\n"
                    "- ligne 3 : $n_B$ entiers de $B$\n\n"
                    "**Sortie** : les $2K + 1$ comptes (pour $s = 0, 1, "
                    "\\dots, 2K$), separes par des espaces.\n\n"
                    "**Indice** : construire les **histogrammes** $c_A$ et "
                    "$c_B$ (frequence de chaque valeur). Le resultat est "
                    "leur **convolution** $c_A * c_B$ : "
                    "$(c_A * c_B)[s] = \\sum_v c_A[v]\\, c_B[s - v]$. La FFT "
                    "l'accelere quand $K$ est grand."
                ),
                "prompt_en": (
                    "Given two arrays $A$ and $B$ of integers in $[0, K]$, "
                    "count, for each sum $s \\in [0, 2K]$, the number of "
                    "pairs $(i, j)$ with $A_i + B_j = s$.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n_A$, $n_B$, $K$ ($1 \\le n_A, n_B \\le "
                    "2000$, $1 \\le K \\le 2000$)\n"
                    "- line 2: $n_A$ integers of $A$\n"
                    "- line 3: $n_B$ integers of $B$\n\n"
                    "**Output**: the $2K + 1$ counts (for $s = 0, 1, "
                    "\\dots, 2K$), space-separated.\n\n"
                    "**Hint**: build the **histograms** $c_A$ and $c_B$ "
                    "(frequency of each value). The result is their "
                    "**convolution** $c_A * c_B$: "
                    "$(c_A * c_B)[s] = \\sum_v c_A[v]\\, c_B[s - v]$. The FFT "
                    "speeds it up when $K$ is large."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    nA, nB, K = int(data[0]), int(data[1]), int(data[2])\n"
                    "    A = list(map(int, data[3:3+nA]))\n"
                    "    B = list(map(int, data[3+nA:3+nA+nB]))\n"
                    "    # TODO: convolve the two histograms.\n"
                    "    print()\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "3 3 3\n1 2 3\n0 1 2\n", "expected": "0 1 2 3 2 1 0\n", "is_sample": True},
                    {"input": "2 2 2\n1 1\n2 2\n", "expected": "0 0 0 4 0\n", "is_sample": True},
                    {"input": "4 3 4\n0 1 2 4\n1 1 3\n", "expected": "0 2 2 3 1 3 0 1 0\n", "is_sample": False},
                    {"input": "1 1 5\n3\n2\n", "expected": "0 0 0 0 0 1 0 0 0 0 0\n", "is_sample": False},
                    {"input": "3 2 3\n0 0 3\n1 2\n", "expected": "0 2 2 0 1 1 0\n", "is_sample": False},
                    {"input": "2 4 2\n0 2\n1 1 2 2\n", "expected": "0 2 2 2 2\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_MA_DICE",
                "title_fr": "Sommes de des",
                "title_en": "Dice sums",
                "prompt_fr": (
                    "On lance $n$ des identiques a $k$ faces (valeurs $1$ a "
                    "$k$). Pour chaque somme totale possible $s$, compter le "
                    "nombre de facons de l'obtenir, modulo $998244353$.\n\n"
                    "**Entree** : une ligne, deux entiers $n$ et $k$ "
                    "($1 \\le n \\le 300$, $1 \\le k \\le 300$).\n\n"
                    "**Sortie** : les comptes pour $s = n, n+1, \\dots, "
                    "n \\cdot k$, separes par des espaces.\n\n"
                    "**Indice** : le polynome d'un de est "
                    "$x + x^2 + \\dots + x^k$. La distribution de $n$ des "
                    "est ce polynome **eleve a la puissance $n$** ; les "
                    "coefficients de $(x + \\dots + x^k)^n$ sont la reponse. "
                    "L'exponentiation de polynomes (par carres, avec NTT) "
                    "calcule cela rapidement."
                ),
                "prompt_en": (
                    "You roll $n$ identical $k$-sided dice (values $1$ to "
                    "$k$). For each possible total sum $s$, count the number "
                    "of ways to obtain it, modulo $998244353$.\n\n"
                    "**Input**: one line, two integers $n$ and $k$ "
                    "($1 \\le n \\le 300$, $1 \\le k \\le 300$).\n\n"
                    "**Output**: the counts for $s = n, n+1, \\dots, "
                    "n \\cdot k$, space-separated.\n\n"
                    "**Hint**: a single die's polynomial is "
                    "$x + x^2 + \\dots + x^k$. The distribution of $n$ dice "
                    "is that polynomial **raised to the power $n$**; the "
                    "coefficients of $(x + \\dots + x^k)^n$ are the answer. "
                    "Polynomial exponentiation (by squaring, with NTT) "
                    "computes it fast."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    n, k = map(int, sys.stdin.readline().split())\n"
                    "    # TODO: coefficients of (x + ... + x^k)^n.\n"
                    "    print()\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "2 6\n", "expected": "1 2 3 4 5 6 5 4 3 2 1\n", "is_sample": True},
                    {"input": "1 4\n", "expected": "1 1 1 1\n", "is_sample": True},
                    {"input": "3 6\n", "expected": "1 3 6 10 15 21 25 27 27 25 21 15 10 6 3 1\n", "is_sample": False},
                    {"input": "2 2\n", "expected": "1 2 1\n", "is_sample": False},
                    {"input": "4 3\n", "expected": "1 4 10 16 19 16 10 4 1\n", "is_sample": False},
                    {"input": "5 4\n", "expected": "1 5 15 35 65 101 135 155 155 135 101 65 35 15 5 1\n", "is_sample": False},
                ],
            },
        ],
    },
]


REFERENCE_SOLUTIONS = {
    "EX_MA_MODEXP": r"""import sys
def main():
    a, b, m = map(int, sys.stdin.readline().split())
    print(pow(a, b, m))
main()
""",
    "EX_MA_MODINV": r"""import sys
def ext_gcd(a, b):
    if b == 0: return a, 1, 0
    g, x, y = ext_gcd(b, a % b)
    return g, y, x - (a // b) * y
def main():
    a, m = map(int, sys.stdin.readline().split())
    a %= m
    g, x, _ = ext_gcd(a, m)
    print(-1 if g != 1 else x % m)
main()
""",
    "EX_MA_LINCONG": r"""import sys
from math import gcd
def ext_gcd(a, b):
    if b == 0: return a, 1, 0
    g, x, y = ext_gcd(b, a % b)
    return g, y, x - (a // b) * y
def modinv(a, m):
    g, x, _ = ext_gcd(a % m, m)
    return -1 if g != 1 else x % m
def main():
    a, b, m = map(int, sys.stdin.readline().split())
    a %= m; b %= m
    g = gcd(a, m)
    if b % g != 0:
        print(-1); return
    a1, b1, m1 = a // g, b // g, m // g
    inv = modinv(a1 % m1, m1)
    print((b1 % m1) * inv % m1)
main()
""",
    "EX_MA_SIEVE_COUNT": r"""import sys
def main():
    n = int(sys.stdin.readline())
    if n < 2:
        print(0); return
    is_comp = bytearray(n+1)
    cnt = 0
    for i in range(2, n+1):
        if not is_comp[i]:
            cnt += 1
            for j in range(i*i, n+1, i):
                is_comp[j] = 1
    print(cnt)
main()
""",
    "EX_MA_MILLER_RABIN": r"""import sys
def is_prime(n):
    if n < 2: return 0
    small = (2,3,5,7,11,13,17,19,23,29,31,37)
    for p in small:
        if n % p == 0: return 1 if n == p else 0
    d = n-1; r = 0
    while d % 2 == 0: d //= 2; r += 1
    for a in small:
        x = pow(a, d, n)
        if x == 1 or x == n-1: continue
        for _ in range(r-1):
            x = x*x % n
            if x == n-1: break
        else:
            return 0
    return 1
def main():
    n = int(sys.stdin.readline())
    print(is_prime(n))
main()
""",
    "EX_MA_CRT": r"""import sys
def ext_gcd(a, b):
    if b == 0: return a, 1, 0
    g, x, y = ext_gcd(b, a % b)
    return g, y, x - (a // b) * y
def main():
    data = sys.stdin.buffer.read().split()
    k = int(data[0]); idx = 1
    x = 0; mod = 1
    ok = True
    for _ in range(k):
        a = int(data[idx]); m = int(data[idx+1]); idx += 2
        g, p, q = ext_gcd(mod, m)
        if (a - x) % g != 0:
            ok = False; break
        lcm = mod // g * m
        t = ((a - x) // g * p) % (m // g)
        x = (x + mod * t) % lcm
        mod = lcm
    print(x % mod if ok else -1)
main()
""",
    "EX_MA_BINOM": r"""import sys
def main():
    n, k, p = map(int, sys.stdin.readline().split())
    if k < 0 or k > n:
        print(0); return
    num = 1; den = 1
    for i in range(k):
        num = num * ((n - i) % p) % p
        den = den * ((i + 1) % p) % p
    print(num * pow(den, p-2, p) % p)
main()
""",
    "EX_MA_LUCAS": r"""import sys
def binom_small(n, k, p):
    if k < 0 or k > n: return 0
    num = 1; den = 1
    for i in range(k):
        num = num * ((n - i) % p) % p
        den = den * ((i + 1) % p) % p
    return num * pow(den, p-2, p) % p
def main():
    n, k, p = map(int, sys.stdin.readline().split())
    res = 1
    while n > 0 or k > 0:
        ni, ki = n % p, k % p
        if ki > ni:
            print(0); return
        res = res * binom_small(ni, ki, p) % p
        n //= p; k //= p
    print(res)
main()
""",
    "EX_MA_CATALAN": r"""import sys
def main():
    n, p = map(int, sys.stdin.readline().split())
    if n == 0:
        print(1 % p); return
    fact = [1]*(2*n+1)
    for i in range(1, 2*n+1):
        fact[i] = fact[i-1] * i % p
    inv_n = pow(fact[n], p-2, p)
    binom = fact[2*n] * inv_n % p * inv_n % p
    print(binom * pow(n+1, p-2, p) % p)
main()
""",
    "EX_MA_POLYMUL": r"""import sys
MOD = 998244353
def ntt(a, invert):
    n = len(a)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit; bit >>= 1
        j |= bit
        if i < j: a[i], a[j] = a[j], a[i]
    length = 2
    while length <= n:
        w = pow(3, (MOD-1)//length, MOD)
        if invert: w = pow(w, MOD-2, MOD)
        for i in range(0, n, length):
            wn = 1
            half = length >> 1
            for k in range(i, i+half):
                u = a[k]; v = a[k+half]*wn % MOD
                a[k] = (u+v) % MOD
                a[k+half] = (u-v) % MOD
                wn = wn*w % MOD
        length <<= 1
    if invert:
        ninv = pow(n, MOD-2, MOD)
        for i in range(n): a[i] = a[i]*ninv % MOD
def main():
    data = sys.stdin.read().split()
    n, m = int(data[0]), int(data[1])
    A = list(map(int, data[2:2+n]))
    B = list(map(int, data[2+n:2+n+m]))
    rl = n + m - 1
    sz = 1
    while sz < rl: sz <<= 1
    fa = [x % MOD for x in A] + [0]*(sz-n)
    fb = [x % MOD for x in B] + [0]*(sz-m)
    ntt(fa, False); ntt(fb, False)
    for i in range(sz): fa[i] = fa[i]*fb[i] % MOD
    ntt(fa, True)
    sys.stdout.write(' '.join(map(str, fa[:rl])) + '\n')
main()
""",
    "EX_MA_PAIR_SUMS": r"""import sys
def main():
    data = sys.stdin.read().split()
    nA, nB, K = int(data[0]), int(data[1]), int(data[2])
    A = list(map(int, data[3:3+nA]))
    B = list(map(int, data[3+nA:3+nA+nB]))
    ca = [0]*(K+1); cb = [0]*(K+1)
    for x in A: ca[x] += 1
    for x in B: cb[x] += 1
    res = [0]*(2*K+1)
    for i in range(K+1):
        if ca[i] == 0: continue
        ci = ca[i]
        for j in range(K+1):
            if cb[j]: res[i+j] += ci*cb[j]
    sys.stdout.write(' '.join(map(str, res)) + '\n')
main()
""",
    "EX_MA_DICE": r"""import sys
MOD = 998244353
def main():
    n, k = map(int, sys.stdin.readline().split())
    dp = [0]*(n*k+1)
    for s in range(1, k+1): dp[s] = 1
    for _ in range(2, n+1):
        nd = [0]*(n*k+1)
        for s in range(len(dp)):
            v = dp[s]
            if v == 0: continue
            top = s + k
            for f in range(s+1, min(top, n*k) + 1):
                nd[f] = (nd[f] + v) % MOD
        dp = nd
    sys.stdout.write(' '.join(str(dp[s]) for s in range(n, n*k+1)) + '\n')
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
                    timeout=15,
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
    print(f"Chapitre 9 - Maths pour la competition : OK ({state}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
