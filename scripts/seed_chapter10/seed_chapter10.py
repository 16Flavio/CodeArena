"""Seed Chapter 10 - Geometrie computationnelle.

Cree (ou met a jour) la section ``geometrie`` avec quatre lecons :

  1. Vecteurs, produits & orientation
  2. Intersection de segments
  3. Enveloppe convexe
  4. Balayage (sweep line)

Chaque lecon contient trois exercices inline gradues (standard,
twist, dur). Idempotent. Toute l'arithmetique est entiere (exacte).

Pre-deploiement le script verifie que chaque solution de reference
passe sur ses test cases (--validate-only pour ne faire QUE ca).

Usage:
    python scripts/seed_chapter10/seed_chapter10.py
    python scripts/seed_chapter10/seed_chapter10.py --draft
    python scripts/seed_chapter10/seed_chapter10.py --validate-only
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
    "slug": "geometrie",
    "title_fr": "Geometrie computationnelle",
    "title_en": "Computational Geometry",
    "description_fr": (
        "La geometrie du competiteur, en arithmetique entiere exacte : "
        "produit vectoriel et orientation, aire par la formule du lacet et "
        "theoreme de Pick, intersection de segments, enveloppe convexe "
        "(monotone chain), et algorithmes de balayage (sweep line) pour la "
        "paire la plus proche et l'union de rectangles."
    ),
    "description_en": (
        "The competitor's geometry, in exact integer arithmetic: cross "
        "product and orientation, area via the shoelace formula and Pick's "
        "theorem, segment intersection, convex hull (monotone chain), and "
        "sweep-line algorithms for the closest pair and rectangle union."
    ),
    "order_idx": 9,
}


LESSONS: list[dict] = [
    # =================================================================
    # Lesson 1 - Vecteurs, produits & orientation
    # =================================================================
    {
        "slug": "vecteurs-orientation",
        "title_fr": "Vecteurs, produits & orientation",
        "title_en": "Vectors, Products & Orientation",
        "order_idx": 0,
        "content_fr_file": "lesson_01_vectors.fr.md",
        "content_en_file": "lesson_01_vectors.en.md",
        "exercises": [
            {
                "key": "EX_GE_ORIENT",
                "title_fr": "Orientation de trois points",
                "title_en": "Orientation of three points",
                "prompt_fr": (
                    "Determiner l'orientation du triplet ordonne "
                    "$(A, B, C)$ : tourne-t-on a gauche, a droite, ou les "
                    "points sont-ils alignes ?\n\n"
                    "**Entree** : une ligne, six entiers "
                    "$a_x\\ a_y\\ b_x\\ b_y\\ c_x\\ c_y$ "
                    "($|{\\cdot}| \\le 10^9$).\n\n"
                    "**Sortie** : `1` si $C$ est a **gauche** de $A \\to B$ "
                    "(sens antihoraire), `-1` si a **droite** (sens "
                    "horaire), `0` si $A$, $B$, $C$ sont **alignes**.\n\n"
                    "**Indice** : le signe du **produit vectoriel** "
                    "$\\overrightarrow{AB} \\times \\overrightarrow{AC} = "
                    "(b_x - a_x)(c_y - a_y) - (b_y - a_y)(c_x - a_x)$ donne "
                    "directement la reponse. Tout est entier - aucun "
                    "flottant."
                ),
                "prompt_en": (
                    "Determine the orientation of the ordered triple "
                    "$(A, B, C)$: do you turn left, right, or are the "
                    "points collinear?\n\n"
                    "**Input**: one line, six integers "
                    "$a_x\\ a_y\\ b_x\\ b_y\\ c_x\\ c_y$ "
                    "($|{\\cdot}| \\le 10^9$).\n\n"
                    "**Output**: `1` if $C$ is to the **left** of "
                    "$A \\to B$ (counterclockwise), `-1` if to the "
                    "**right** (clockwise), `0` if $A$, $B$, $C$ are "
                    "**collinear**.\n\n"
                    "**Hint**: the sign of the **cross product** "
                    "$\\overrightarrow{AB} \\times \\overrightarrow{AC} = "
                    "(b_x - a_x)(c_y - a_y) - (b_y - a_y)(c_x - a_x)$ gives "
                    "the answer directly. Everything is integer - no "
                    "floats."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    v = list(map(int, sys.stdin.readline().split()))\n"
                    "    ax, ay, bx, by, cx, cy = v\n"
                    "    # TODO: sign of the cross product.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "0 0 4 0 2 2\n", "expected": "1\n", "is_sample": True},
                    {"input": "0 0 4 0 2 -2\n", "expected": "-1\n", "is_sample": True},
                    {"input": "0 0 4 0 2 0\n", "expected": "0\n", "is_sample": False},
                    {"input": "1 1 5 5 3 3\n", "expected": "0\n", "is_sample": False},
                    {"input": "0 0 1 0 1 1\n", "expected": "1\n", "is_sample": False},
                    {"input": "-3 -3 3 3 0 5\n", "expected": "1\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_GE_POLY_AREA",
                "title_fr": "Aire d'un polygone",
                "title_en": "Polygon area",
                "prompt_fr": (
                    "Calculer **deux fois** l'aire d'un polygone simple "
                    "donne par ses sommets dans l'ordre (horaire ou "
                    "antihoraire).\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ ($3 \\le n \\le 10^5$)\n"
                    "- $n$ lignes : $x_i\\ y_i$ ($|{\\cdot}| \\le 10^9$)\n\n"
                    "**Sortie** : un seul entier - **$2 \\times$ l'aire** "
                    "(toujours entier).\n\n"
                    "**Indice** : formule du **lacet** (shoelace) : "
                    "$2A = \\left| \\sum_i (x_i y_{i+1} - x_{i+1} y_i) "
                    "\\right|$, les indices etant cycliques. On renvoie "
                    "$2A$ pour rester en entiers exacts."
                ),
                "prompt_en": (
                    "Compute **twice** the area of a simple polygon given "
                    "by its vertices in order (clockwise or "
                    "counterclockwise).\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($3 \\le n \\le 10^5$)\n"
                    "- $n$ lines: $x_i\\ y_i$ ($|{\\cdot}| \\le 10^9$)\n\n"
                    "**Output**: one integer - **$2 \\times$ the area** "
                    "(always an integer).\n\n"
                    "**Hint**: the **shoelace** formula: "
                    "$2A = \\left| \\sum_i (x_i y_{i+1} - x_{i+1} y_i) "
                    "\\right|$, with cyclic indices. Return $2A$ to stay in "
                    "exact integers."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.buffer.read().split()\n"
                    "    n = int(data[0]); idx = 1\n"
                    "    pts = []\n"
                    "    for _ in range(n):\n"
                    "        pts.append((int(data[idx]), int(data[idx+1]))); idx += 2\n"
                    "    # TODO: shoelace, output twice the area.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "4\n0 0\n4 0\n4 3\n0 3\n", "expected": "24\n", "is_sample": True},
                    {"input": "3\n0 0\n4 0\n0 3\n", "expected": "12\n", "is_sample": True},
                    {"input": "4\n0 0\n2 0\n2 2\n0 2\n", "expected": "8\n", "is_sample": False},
                    {"input": "5\n0 0\n4 0\n4 4\n2 6\n0 4\n", "expected": "40\n", "is_sample": False},
                    {"input": "3\n0 0\n1 0\n0 1\n", "expected": "1\n", "is_sample": False},
                    {"input": "6\n0 0\n2 0\n3 1\n2 2\n0 2\n-1 1\n", "expected": "12\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_GE_PICK",
                "title_fr": "Theoreme de Pick",
                "title_en": "Pick's theorem",
                "prompt_fr": (
                    "Compter le nombre de points a coordonnees entieres "
                    "**strictement a l'interieur** d'un polygone simple a "
                    "sommets entiers.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ ($3 \\le n \\le 10^5$)\n"
                    "- $n$ lignes : $x_i\\ y_i$ ($|{\\cdot}| \\le 10^6$)\n\n"
                    "**Sortie** : un seul entier - le nombre de points "
                    "interieurs.\n\n"
                    "**Indice** : **theoreme de Pick** : $A = I + "
                    "\\frac{B}{2} - 1$, ou $A$ est l'aire, $I$ le nombre de "
                    "points interieurs, $B$ le nombre de points entiers sur "
                    "le bord. Donc $I = A - \\frac{B}{2} + 1$. On a $B = "
                    "\\sum_{\\text{aretes}} \\gcd(|\\Delta x|, |\\Delta y|)$."
                ),
                "prompt_en": (
                    "Count the number of integer-coordinate points "
                    "**strictly inside** a simple polygon with integer "
                    "vertices.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($3 \\le n \\le 10^5$)\n"
                    "- $n$ lines: $x_i\\ y_i$ ($|{\\cdot}| \\le 10^6$)\n\n"
                    "**Output**: one integer - the number of interior "
                    "points.\n\n"
                    "**Hint**: **Pick's theorem**: $A = I + \\frac{B}{2} - "
                    "1$, where $A$ is the area, $I$ the number of interior "
                    "points, $B$ the number of integer points on the "
                    "boundary. So $I = A - \\frac{B}{2} + 1$. Here $B = "
                    "\\sum_{\\text{edges}} \\gcd(|\\Delta x|, |\\Delta y|)$."
                ),
                "starter_code": (
                    "import sys\n"
                    "from math import gcd\n\n"
                    "def main():\n"
                    "    data = sys.stdin.buffer.read().split()\n"
                    "    n = int(data[0]); idx = 1\n"
                    "    pts = []\n"
                    "    for _ in range(n):\n"
                    "        pts.append((int(data[idx]), int(data[idx+1]))); idx += 2\n"
                    "    # TODO: Pick's theorem: I = A - B/2 + 1.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "4\n0 0\n4 0\n4 4\n0 4\n", "expected": "9\n", "is_sample": True},
                    {"input": "3\n0 0\n4 0\n0 4\n", "expected": "3\n", "is_sample": True},
                    {"input": "4\n0 0\n2 0\n2 2\n0 2\n", "expected": "1\n", "is_sample": False},
                    {"input": "3\n0 0\n6 0\n0 6\n", "expected": "10\n", "is_sample": False},
                    {"input": "4\n0 0\n5 0\n5 3\n0 3\n", "expected": "8\n", "is_sample": False},
                    {"input": "3\n0 0\n1 0\n0 1\n", "expected": "0\n", "is_sample": False},
                ],
            },
        ],
    },

    # =================================================================
    # Lesson 2 - Intersection de segments
    # =================================================================
    {
        "slug": "intersection-segments",
        "title_fr": "Intersection de segments",
        "title_en": "Segment Intersection",
        "order_idx": 1,
        "content_fr_file": "lesson_02_segments.fr.md",
        "content_en_file": "lesson_02_segments.en.md",
        "exercises": [
            {
                "key": "EX_GE_SEG_INTERSECT",
                "title_fr": "Deux segments se croisent",
                "title_en": "Two segments intersect",
                "prompt_fr": (
                    "Determiner si deux segments $[A, B]$ et $[C, D]$ ont au "
                    "moins un point commun.\n\n"
                    "**Entree** : une ligne, huit entiers "
                    "$a_x\\ a_y\\ b_x\\ b_y\\ c_x\\ c_y\\ d_x\\ d_y$ "
                    "($|{\\cdot}| \\le 10^9$).\n\n"
                    "**Sortie** : `1` s'ils se croisent (y compris aux "
                    "extremites ou en recouvrement colineaire), `0` "
                    "sinon.\n\n"
                    "**Indice** : quatre **orientations**. Les segments se "
                    "croisent proprement si $A, B$ sont de part et d'autre "
                    "de la droite $CD$ **et** vice-versa. Traiter a part les "
                    "cas colineaires : une extremite est-elle sur l'autre "
                    "segment ? Tout en entiers."
                ),
                "prompt_en": (
                    "Determine whether two segments $[A, B]$ and $[C, D]$ "
                    "share at least one common point.\n\n"
                    "**Input**: one line, eight integers "
                    "$a_x\\ a_y\\ b_x\\ b_y\\ c_x\\ c_y\\ d_x\\ d_y$ "
                    "($|{\\cdot}| \\le 10^9$).\n\n"
                    "**Output**: `1` if they intersect (including at "
                    "endpoints or in collinear overlap), `0` otherwise.\n\n"
                    "**Hint**: four **orientations**. The segments cross "
                    "properly if $A, B$ lie on opposite sides of line $CD$ "
                    "**and** vice versa. Handle collinear cases separately: "
                    "is an endpoint on the other segment? All in integers."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    v = list(map(int, sys.stdin.readline().split()))\n"
                    "    # TODO: orientation-based segment intersection.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "0 0 4 4 0 4 4 0\n", "expected": "1\n", "is_sample": True},
                    {"input": "0 0 2 2 3 3 5 5\n", "expected": "0\n", "is_sample": True},
                    {"input": "0 0 4 0 2 1 2 5\n", "expected": "0\n", "is_sample": False},
                    {"input": "0 0 4 0 5 0 8 0\n", "expected": "0\n", "is_sample": False},
                    {"input": "0 0 4 4 1 1 2 2\n", "expected": "1\n", "is_sample": False},
                    {"input": "0 0 1 1 2 2 3 3\n", "expected": "0\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_GE_COUNT_INTERSECTIONS",
                "title_fr": "Comptage de paires qui se croisent",
                "title_en": "Counting intersecting pairs",
                "prompt_fr": (
                    "Compter le nombre de **paires** de segments (parmi $n$) "
                    "qui se croisent.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ ($1 \\le n \\le 2000$)\n"
                    "- $n$ lignes : $a_x\\ a_y\\ b_x\\ b_y$ (un segment par "
                    "ligne, $|{\\cdot}| \\le 10^9$)\n\n"
                    "**Sortie** : un seul entier - le nombre de paires "
                    "$(i, j)$, $i < j$, qui s'intersectent.\n\n"
                    "**Indice** : tester chaque paire avec le predicat "
                    "d'intersection de l'exercice precedent. $O(n^2)$. (Un "
                    "balayage abaisse cela a $O(n \\log n)$ - voir la "
                    "leçon 4.)"
                ),
                "prompt_en": (
                    "Count the number of **pairs** of segments (out of $n$) "
                    "that intersect.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($1 \\le n \\le 2000$)\n"
                    "- $n$ lines: $a_x\\ a_y\\ b_x\\ b_y$ (one segment per "
                    "line, $|{\\cdot}| \\le 10^9$)\n\n"
                    "**Output**: one integer - the number of pairs "
                    "$(i, j)$, $i < j$, that intersect.\n\n"
                    "**Hint**: test each pair with the intersection "
                    "predicate from the previous exercise. $O(n^2)$. (A "
                    "sweep lowers this to $O(n \\log n)$ - see lesson 4.)"
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.buffer.read().split()\n"
                    "    n = int(data[0]); idx = 1\n"
                    "    segs = []\n"
                    "    for _ in range(n):\n"
                    "        segs.append(tuple(int(data[idx+t]) for t in range(4))); idx += 4\n"
                    "    # TODO: count intersecting pairs.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "3\n0 0 4 4\n0 4 4 0\n2 0 2 5\n", "expected": "3\n", "is_sample": True},
                    {"input": "2\n0 0 1 1\n2 2 3 3\n", "expected": "0\n", "is_sample": True},
                    {"input": "4\n0 0 4 0\n0 1 4 1\n0 2 4 2\n0 0 0 2\n", "expected": "3\n", "is_sample": False},
                    {"input": "3\n0 0 2 2\n1 0 1 2\n0 2 2 0\n", "expected": "3\n", "is_sample": False},
                    {"input": "2\n0 0 5 5\n1 1 3 3\n", "expected": "1\n", "is_sample": False},
                    {"input": "4\n0 0 1 0\n2 0 3 0\n4 0 5 0\n0 1 5 1\n", "expected": "0\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_GE_SIMPLE_POLYGON",
                "title_fr": "Polygone simple ?",
                "title_en": "Simple polygon?",
                "prompt_fr": (
                    "Determiner si une suite de sommets forme un polygone "
                    "**simple** : aucune paire d'aretes non adjacentes ne se "
                    "croise, et deux aretes adjacentes ne se touchent qu'au "
                    "sommet partage.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ ($3 \\le n \\le 2000$)\n"
                    "- $n$ lignes : $x_i\\ y_i$ (sommets dans l'ordre, "
                    "$|{\\cdot}| \\le 10^9$)\n\n"
                    "**Sortie** : `1` si le polygone est simple, `0` "
                    "sinon.\n\n"
                    "**Indice** : tester l'intersection de chaque paire "
                    "d'aretes **non adjacentes** ; pour les aretes "
                    "adjacentes, verifier qu'elles ne se recouvrent pas "
                    "(colineaires superposees). $O(n^2)$ avec le predicat "
                    "d'intersection."
                ),
                "prompt_en": (
                    "Determine whether a sequence of vertices forms a "
                    "**simple** polygon: no pair of non-adjacent edges "
                    "crosses, and two adjacent edges touch only at the "
                    "shared vertex.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($3 \\le n \\le 2000$)\n"
                    "- $n$ lines: $x_i\\ y_i$ (vertices in order, "
                    "$|{\\cdot}| \\le 10^9$)\n\n"
                    "**Output**: `1` if the polygon is simple, `0` "
                    "otherwise.\n\n"
                    "**Hint**: test the intersection of each pair of "
                    "**non-adjacent** edges; for adjacent edges, check they "
                    "do not overlap (collinear overlapping). $O(n^2)$ with "
                    "the intersection predicate."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.buffer.read().split()\n"
                    "    n = int(data[0]); idx = 1\n"
                    "    pts = []\n"
                    "    for _ in range(n):\n"
                    "        pts.append((int(data[idx]), int(data[idx+1]))); idx += 2\n"
                    "    # TODO: check no improper edge intersections.\n"
                    "    print(1)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "4\n0 0\n4 0\n4 4\n0 4\n", "expected": "1\n", "is_sample": True},
                    {"input": "4\n0 0\n4 4\n4 0\n0 4\n", "expected": "0\n", "is_sample": True},
                    {"input": "3\n0 0\n4 0\n2 3\n", "expected": "1\n", "is_sample": False},
                    {"input": "5\n0 0\n4 0\n4 4\n0 4\n2 2\n", "expected": "1\n", "is_sample": False},
                    {"input": "6\n0 0\n4 0\n4 4\n2 4\n2 2\n0 2\n", "expected": "1\n", "is_sample": False},
                    {"input": "4\n0 0\n3 3\n0 3\n3 0\n", "expected": "0\n", "is_sample": False},
                ],
            },
        ],
    },

    # =================================================================
    # Lesson 3 - Enveloppe convexe
    # =================================================================
    {
        "slug": "enveloppe-convexe",
        "title_fr": "Enveloppe convexe",
        "title_en": "Convex Hull",
        "order_idx": 2,
        "content_fr_file": "lesson_03_convex_hull.fr.md",
        "content_en_file": "lesson_03_convex_hull.en.md",
        "exercises": [
            {
                "key": "EX_GE_HULL_SIZE",
                "title_fr": "Sommets de l'enveloppe convexe",
                "title_en": "Convex hull vertices",
                "prompt_fr": (
                    "Compter le nombre de sommets de l'**enveloppe "
                    "convexe** d'un nuage de points. Les points alignes sur "
                    "un bord ne comptent **pas** comme sommets.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ ($1 \\le n \\le 10^5$)\n"
                    "- $n$ lignes : $x_i\\ y_i$ ($|{\\cdot}| \\le 10^9$, "
                    "doublons possibles)\n\n"
                    "**Sortie** : un seul entier - le nombre de sommets de "
                    "l'enveloppe (1 si tous les points coincident, 2 s'ils "
                    "sont tous alignes).\n\n"
                    "**Indice** : **monotone chain** (Andrew). Trier les "
                    "points, construire l'enveloppe inferieure puis "
                    "superieure en depilant tant que le tour n'est pas "
                    "strictement a gauche (`cross <= 0`). $O(n \\log n)$."
                ),
                "prompt_en": (
                    "Count the number of vertices of the **convex hull** of "
                    "a point cloud. Points collinear on an edge do **not** "
                    "count as vertices.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($1 \\le n \\le 10^5$)\n"
                    "- $n$ lines: $x_i\\ y_i$ ($|{\\cdot}| \\le 10^9$, "
                    "duplicates possible)\n\n"
                    "**Output**: one integer - the number of hull vertices "
                    "(1 if all points coincide, 2 if all are collinear).\n\n"
                    "**Hint**: **monotone chain** (Andrew). Sort the points, "
                    "build the lower then upper hull, popping while the turn "
                    "is not strictly left (`cross <= 0`). $O(n \\log n)$."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.buffer.read().split()\n"
                    "    n = int(data[0]); idx = 1\n"
                    "    pts = []\n"
                    "    for _ in range(n):\n"
                    "        pts.append((int(data[idx]), int(data[idx+1]))); idx += 2\n"
                    "    # TODO: monotone chain; count vertices.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5\n0 0\n4 0\n4 4\n0 4\n2 2\n", "expected": "4\n", "is_sample": True},
                    {"input": "3\n0 0\n2 0\n1 1\n", "expected": "3\n", "is_sample": True},
                    {"input": "4\n0 0\n1 0\n2 0\n3 0\n", "expected": "2\n", "is_sample": False},
                    {"input": "6\n0 0\n4 0\n4 4\n0 4\n2 0\n2 4\n", "expected": "4\n", "is_sample": False},
                    {"input": "1\n5 5\n", "expected": "1\n", "is_sample": False},
                    {"input": "8\n0 0\n1 0\n2 0\n2 1\n2 2\n1 2\n0 2\n0 1\n", "expected": "4\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_GE_HULL_AREA",
                "title_fr": "Aire de l'enveloppe convexe",
                "title_en": "Convex hull area",
                "prompt_fr": (
                    "Calculer **deux fois** l'aire de l'enveloppe convexe "
                    "d'un nuage de points.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ ($1 \\le n \\le 10^5$)\n"
                    "- $n$ lignes : $x_i\\ y_i$ ($|{\\cdot}| \\le 10^9$)\n\n"
                    "**Sortie** : un seul entier - $2 \\times$ l'aire de "
                    "l'enveloppe (0 si tous les points sont alignes).\n\n"
                    "**Indice** : construire l'enveloppe convexe (monotone "
                    "chain), puis appliquer la formule du lacet a ses "
                    "sommets. Combinaison directe des leçons 1 et 3."
                ),
                "prompt_en": (
                    "Compute **twice** the area of the convex hull of a "
                    "point cloud.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($1 \\le n \\le 10^5$)\n"
                    "- $n$ lines: $x_i\\ y_i$ ($|{\\cdot}| \\le 10^9$)\n\n"
                    "**Output**: one integer - $2 \\times$ the hull area (0 "
                    "if all points are collinear).\n\n"
                    "**Hint**: build the convex hull (monotone chain), then "
                    "apply the shoelace formula to its vertices. A direct "
                    "combination of lessons 1 and 3."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.buffer.read().split()\n"
                    "    n = int(data[0]); idx = 1\n"
                    "    pts = []\n"
                    "    for _ in range(n):\n"
                    "        pts.append((int(data[idx]), int(data[idx+1]))); idx += 2\n"
                    "    # TODO: hull + shoelace.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5\n0 0\n4 0\n4 4\n0 4\n2 2\n", "expected": "32\n", "is_sample": True},
                    {"input": "3\n0 0\n4 0\n0 3\n", "expected": "12\n", "is_sample": True},
                    {"input": "4\n0 0\n1 0\n2 0\n3 0\n", "expected": "0\n", "is_sample": False},
                    {"input": "6\n0 0\n4 0\n4 4\n0 4\n2 0\n2 4\n", "expected": "32\n", "is_sample": False},
                    {"input": "5\n0 0\n6 0\n6 4\n3 7\n0 4\n", "expected": "66\n", "is_sample": False},
                    {"input": "4\n-2 -2\n2 -2\n2 2\n-2 2\n", "expected": "32\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_GE_DIAMETER",
                "title_fr": "Diametre d'un nuage de points",
                "title_en": "Point set diameter",
                "prompt_fr": (
                    "Trouver le **carre** de la plus grande distance entre "
                    "deux points du nuage.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ ($2 \\le n \\le 10^5$)\n"
                    "- $n$ lignes : $x_i\\ y_i$ ($|{\\cdot}| \\le 10^9$)\n\n"
                    "**Sortie** : un seul entier - la distance au carre "
                    "maximale (entiere, pas de racine).\n\n"
                    "**Indice** : les deux points les plus eloignes sont "
                    "**forcement des sommets de l'enveloppe convexe**. Les "
                    "**rotating calipers** parcourent l'enveloppe en "
                    "$O(n \\log n)$ (dominee par le tri) au lieu du "
                    "$O(n^2)$ naif. On travaille avec la distance au carre "
                    "pour rester en entiers."
                ),
                "prompt_en": (
                    "Find the **square** of the largest distance between two "
                    "points of the cloud.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($2 \\le n \\le 10^5$)\n"
                    "- $n$ lines: $x_i\\ y_i$ ($|{\\cdot}| \\le 10^9$)\n\n"
                    "**Output**: one integer - the maximum squared distance "
                    "(integer, no square root).\n\n"
                    "**Hint**: the two farthest points are **necessarily "
                    "convex-hull vertices**. **Rotating calipers** traverse "
                    "the hull in $O(n \\log n)$ (dominated by the sort) "
                    "instead of the naive $O(n^2)$. Work with squared "
                    "distance to stay in integers."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.buffer.read().split()\n"
                    "    n = int(data[0]); idx = 1\n"
                    "    pts = []\n"
                    "    for _ in range(n):\n"
                    "        pts.append((int(data[idx]), int(data[idx+1]))); idx += 2\n"
                    "    # TODO: hull + rotating calipers (or brute for small n).\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "4\n0 0\n4 0\n4 3\n0 3\n", "expected": "25\n", "is_sample": True},
                    {"input": "2\n0 0\n5 12\n", "expected": "169\n", "is_sample": True},
                    {"input": "3\n0 0\n1 0\n0 1\n", "expected": "2\n", "is_sample": False},
                    {"input": "5\n0 0\n10 0\n10 10\n0 10\n5 5\n", "expected": "200\n", "is_sample": False},
                    {"input": "4\n-3 0\n3 0\n0 -4\n0 4\n", "expected": "64\n", "is_sample": False},
                    {"input": "6\n0 0\n1 5\n7 2\n3 -4\n-2 3\n5 5\n", "expected": "85\n", "is_sample": False},
                ],
            },
        ],
    },

    # =================================================================
    # Lesson 4 - Balayage (sweep line)
    # =================================================================
    {
        "slug": "sweep-line",
        "title_fr": "Balayage (sweep line)",
        "title_en": "Sweep Line",
        "order_idx": 3,
        "content_fr_file": "lesson_04_sweep.fr.md",
        "content_en_file": "lesson_04_sweep.en.md",
        "exercises": [
            {
                "key": "EX_GE_CLOSEST_PAIR",
                "title_fr": "Paire de points la plus proche",
                "title_en": "Closest pair of points",
                "prompt_fr": (
                    "Trouver le **carre** de la plus petite distance entre "
                    "deux points distincts.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ ($2 \\le n \\le 10^5$)\n"
                    "- $n$ lignes : $x_i\\ y_i$ ($|{\\cdot}| \\le 10^9$)\n\n"
                    "**Sortie** : un seul entier - la distance au carre "
                    "minimale.\n\n"
                    "**Indice** : trier par $x$, balayer en maintenant une "
                    "structure des points dans une bande verticale de "
                    "largeur $\\sqrt{d}$ (la meilleure distance courante). "
                    "Seuls quelques points voisins sont a comparer. "
                    "$O(n \\log n)$. Distance au carre pour rester en "
                    "entiers."
                ),
                "prompt_en": (
                    "Find the **square** of the smallest distance between "
                    "two distinct points.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($2 \\le n \\le 10^5$)\n"
                    "- $n$ lines: $x_i\\ y_i$ ($|{\\cdot}| \\le 10^9$)\n\n"
                    "**Output**: one integer - the minimum squared "
                    "distance.\n\n"
                    "**Hint**: sort by $x$, sweep while maintaining a "
                    "structure of points in a vertical strip of width "
                    "$\\sqrt{d}$ (the current best distance). Only a few "
                    "neighboring points need comparing. $O(n \\log n)$. "
                    "Squared distance to stay in integers."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.buffer.read().split()\n"
                    "    n = int(data[0]); idx = 1\n"
                    "    pts = []\n"
                    "    for _ in range(n):\n"
                    "        pts.append((int(data[idx]), int(data[idx+1]))); idx += 2\n"
                    "    # TODO: closest pair (sweep or divide and conquer).\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "4\n0 0\n10 0\n0 10\n1 1\n", "expected": "2\n", "is_sample": True},
                    {"input": "2\n0 0\n3 4\n", "expected": "25\n", "is_sample": True},
                    {"input": "3\n0 0\n5 0\n5 5\n", "expected": "25\n", "is_sample": False},
                    {"input": "5\n0 0\n2 2\n3 3\n10 10\n2 3\n", "expected": "1\n", "is_sample": False},
                    {"input": "4\n0 0\n0 1\n1 0\n1 1\n", "expected": "1\n", "is_sample": False},
                    {"input": "6\n0 0\n8 8\n1 0\n9 9\n4 4\n5 4\n", "expected": "1\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_GE_RECT_UNION",
                "title_fr": "Aire de l'union de rectangles",
                "title_en": "Area of union of rectangles",
                "prompt_fr": (
                    "Calculer l'aire de l'**union** de $n$ rectangles "
                    "alignes sur les axes.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ ($1 \\le n \\le 10^5$)\n"
                    "- $n$ lignes : $x_1\\ y_1\\ x_2\\ y_2$ avec "
                    "$x_1 < x_2$, $y_1 < y_2$ ($|{\\cdot}| \\le 10^9$)\n\n"
                    "**Sortie** : un seul entier - l'aire couverte (comptee "
                    "une seule fois pour les zones chevauchantes).\n\n"
                    "**Indice** : **balayage vertical**. Trier les "
                    "abscisses ; entre deux abscisses consecutives, "
                    "l'ensemble des rectangles actifs est fixe, et la "
                    "hauteur couverte est la longueur de l'union de leurs "
                    "intervalles $y$. Multiplier hauteur $\\times$ largeur "
                    "de la tranche."
                ),
                "prompt_en": (
                    "Compute the area of the **union** of $n$ axis-aligned "
                    "rectangles.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($1 \\le n \\le 10^5$)\n"
                    "- $n$ lines: $x_1\\ y_1\\ x_2\\ y_2$ with $x_1 < x_2$, "
                    "$y_1 < y_2$ ($|{\\cdot}| \\le 10^9$)\n\n"
                    "**Output**: one integer - the covered area (counted "
                    "once for overlapping regions).\n\n"
                    "**Hint**: **vertical sweep**. Sort the x-coordinates; "
                    "between two consecutive x's, the set of active "
                    "rectangles is fixed, and the covered height is the "
                    "length of the union of their $y$-intervals. Multiply "
                    "height $\\times$ slab width."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.buffer.read().split()\n"
                    "    n = int(data[0]); idx = 1\n"
                    "    rects = []\n"
                    "    for _ in range(n):\n"
                    "        rects.append(tuple(int(data[idx+t]) for t in range(4))); idx += 4\n"
                    "    # TODO: sweep-line union area.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "2\n0 0 3 3\n1 1 4 4\n", "expected": "14\n", "is_sample": True},
                    {"input": "1\n0 0 5 5\n", "expected": "25\n", "is_sample": True},
                    {"input": "2\n0 0 2 2\n3 3 5 5\n", "expected": "8\n", "is_sample": False},
                    {"input": "3\n0 0 4 4\n2 2 6 6\n1 1 3 3\n", "expected": "28\n", "is_sample": False},
                    {"input": "2\n0 0 4 2\n0 0 2 4\n", "expected": "12\n", "is_sample": False},
                    {"input": "4\n0 0 2 2\n2 0 4 2\n0 2 2 4\n2 2 4 4\n", "expected": "16\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_GE_MAX_OVERLAP",
                "title_fr": "Recouvrement maximal",
                "title_en": "Maximum overlap",
                "prompt_fr": (
                    "Etant donnes $n$ rectangles alignes sur les axes, "
                    "trouver le **nombre maximal** de rectangles qui se "
                    "recouvrent en un meme point.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ ($1 \\le n \\le 2000$)\n"
                    "- $n$ lignes : $x_1\\ y_1\\ x_2\\ y_2$ avec "
                    "$x_1 < x_2$, $y_1 < y_2$ ($|{\\cdot}| \\le 10^9$)\n\n"
                    "Un rectangle couvre un point $(x, y)$ si "
                    "$x_1 \\le x < x_2$ et $y_1 \\le y < y_2$ (bord droit et "
                    "haut exclus).\n\n"
                    "**Sortie** : un seul entier - le recouvrement "
                    "maximal.\n\n"
                    "**Indice** : **compression de coordonnees**. Les $x$ et "
                    "$y$ distincts decoupent le plan en cellules ; dans "
                    "chaque cellule le recouvrement est constant. Compter, "
                    "pour chaque cellule, combien de rectangles la "
                    "contiennent, et prendre le maximum."
                ),
                "prompt_en": (
                    "Given $n$ axis-aligned rectangles, find the **maximum "
                    "number** of rectangles overlapping at a single "
                    "point.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ ($1 \\le n \\le 2000$)\n"
                    "- $n$ lines: $x_1\\ y_1\\ x_2\\ y_2$ with $x_1 < x_2$, "
                    "$y_1 < y_2$ ($|{\\cdot}| \\le 10^9$)\n\n"
                    "A rectangle covers a point $(x, y)$ if "
                    "$x_1 \\le x < x_2$ and $y_1 \\le y < y_2$ (right and top "
                    "edges excluded).\n\n"
                    "**Output**: one integer - the maximum overlap.\n\n"
                    "**Hint**: **coordinate compression**. The distinct $x$ "
                    "and $y$ cut the plane into cells; within each cell the "
                    "overlap is constant. Count, for each cell, how many "
                    "rectangles contain it, and take the maximum."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.buffer.read().split()\n"
                    "    n = int(data[0]); idx = 1\n"
                    "    rects = []\n"
                    "    for _ in range(n):\n"
                    "        rects.append(tuple(int(data[idx+t]) for t in range(4))); idx += 4\n"
                    "    # TODO: coordinate compression; max cell coverage.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "3\n0 0 4 4\n2 2 6 6\n1 1 3 3\n", "expected": "3\n", "is_sample": True},
                    {"input": "2\n0 0 2 2\n5 5 7 7\n", "expected": "1\n", "is_sample": True},
                    {"input": "3\n0 0 10 10\n0 0 10 10\n0 0 10 10\n", "expected": "3\n", "is_sample": False},
                    {"input": "2\n0 0 3 3\n1 1 4 4\n", "expected": "2\n", "is_sample": False},
                    {"input": "4\n0 0 2 2\n1 0 3 2\n0 1 2 3\n1 1 3 3\n", "expected": "4\n", "is_sample": False},
                    {"input": "1\n0 0 5 5\n", "expected": "1\n", "is_sample": False},
                ],
            },
        ],
    },
]


REFERENCE_SOLUTIONS = {
    "EX_GE_ORIENT": r"""import sys
def main():
    ax, ay, bx, by, cx, cy = map(int, sys.stdin.readline().split())
    cr = (bx-ax)*(cy-ay) - (by-ay)*(cx-ax)
    print(1 if cr > 0 else (-1 if cr < 0 else 0))
main()
""",
    "EX_GE_POLY_AREA": r"""import sys
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); idx = 1
    pts = []
    for _ in range(n):
        pts.append((int(data[idx]), int(data[idx+1]))); idx += 2
    s = 0
    for i in range(n):
        x1, y1 = pts[i]; x2, y2 = pts[(i+1) % n]
        s += x1*y2 - x2*y1
    print(abs(s))
main()
""",
    "EX_GE_PICK": r"""import sys
from math import gcd
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); idx = 1
    pts = []
    for _ in range(n):
        pts.append((int(data[idx]), int(data[idx+1]))); idx += 2
    area2 = 0; B = 0
    for i in range(n):
        x1, y1 = pts[i]; x2, y2 = pts[(i+1) % n]
        area2 += x1*y2 - x2*y1
        B += gcd(abs(x2-x1), abs(y2-y1))
    area2 = abs(area2)
    print((area2 - B) // 2 + 1)
main()
""",
    "EX_GE_SEG_INTERSECT": r"""import sys
def cross(o, a, b):
    return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
def on_seg(p, q, r):
    return min(p[0], q[0]) <= r[0] <= max(p[0], q[0]) and \
           min(p[1], q[1]) <= r[1] <= max(p[1], q[1])
def inter(p1, p2, p3, p4):
    d1 = cross(p3, p4, p1); d2 = cross(p3, p4, p2)
    d3 = cross(p1, p2, p3); d4 = cross(p1, p2, p4)
    if ((d1 > 0) != (d2 > 0)) and d1 != 0 and d2 != 0 and \
       ((d3 > 0) != (d4 > 0)) and d3 != 0 and d4 != 0:
        return True
    if d1 == 0 and on_seg(p3, p4, p1): return True
    if d2 == 0 and on_seg(p3, p4, p2): return True
    if d3 == 0 and on_seg(p1, p2, p3): return True
    if d4 == 0 and on_seg(p1, p2, p4): return True
    return False
def main():
    v = list(map(int, sys.stdin.readline().split()))
    P = [(v[0], v[1]), (v[2], v[3]), (v[4], v[5]), (v[6], v[7])]
    print(1 if inter(*P) else 0)
main()
""",
    "EX_GE_COUNT_INTERSECTIONS": r"""import sys
def cross(o, a, b):
    return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
def on_seg(p, q, r):
    return min(p[0], q[0]) <= r[0] <= max(p[0], q[0]) and \
           min(p[1], q[1]) <= r[1] <= max(p[1], q[1])
def inter(p1, p2, p3, p4):
    d1 = cross(p3, p4, p1); d2 = cross(p3, p4, p2)
    d3 = cross(p1, p2, p3); d4 = cross(p1, p2, p4)
    if ((d1 > 0) != (d2 > 0)) and d1 != 0 and d2 != 0 and \
       ((d3 > 0) != (d4 > 0)) and d3 != 0 and d4 != 0:
        return True
    if d1 == 0 and on_seg(p3, p4, p1): return True
    if d2 == 0 and on_seg(p3, p4, p2): return True
    if d3 == 0 and on_seg(p1, p2, p3): return True
    if d4 == 0 and on_seg(p1, p2, p4): return True
    return False
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); idx = 1
    segs = []
    for _ in range(n):
        a = (int(data[idx]), int(data[idx+1])); b = (int(data[idx+2]), int(data[idx+3]))
        segs.append((a, b)); idx += 4
    c = 0
    for i in range(n):
        for j in range(i+1, n):
            if inter(segs[i][0], segs[i][1], segs[j][0], segs[j][1]):
                c += 1
    print(c)
main()
""",
    "EX_GE_SIMPLE_POLYGON": r"""import sys
def cross(o, a, b):
    return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
def on_seg(p, q, r):
    return min(p[0], q[0]) <= r[0] <= max(p[0], q[0]) and \
           min(p[1], q[1]) <= r[1] <= max(p[1], q[1])
def inter(p1, p2, p3, p4):
    d1 = cross(p3, p4, p1); d2 = cross(p3, p4, p2)
    d3 = cross(p1, p2, p3); d4 = cross(p1, p2, p4)
    if ((d1 > 0) != (d2 > 0)) and d1 != 0 and d2 != 0 and \
       ((d3 > 0) != (d4 > 0)) and d3 != 0 and d4 != 0:
        return True
    if d1 == 0 and on_seg(p3, p4, p1): return True
    if d2 == 0 and on_seg(p3, p4, p2): return True
    if d3 == 0 and on_seg(p1, p2, p3): return True
    if d4 == 0 and on_seg(p1, p2, p4): return True
    return False
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); idx = 1
    pts = []
    for _ in range(n):
        pts.append((int(data[idx]), int(data[idx+1]))); idx += 2
    if n < 3:
        print(0); return
    edges = [(pts[i], pts[(i+1) % n]) for i in range(n)]
    for i in range(n):
        for j in range(i+1, n):
            adjacent = (j == i+1) or (i == 0 and j == n-1)
            a, b = edges[i]; c, d = edges[j]
            if adjacent:
                if inter(a, b, c, d) and cross(a, b, c) == 0 and cross(a, b, d) == 0:
                    print(0); return
                continue
            if inter(a, b, c, d):
                print(0); return
    print(1)
main()
""",
    "EX_GE_HULL_SIZE": r"""import sys
def cross(o, a, b):
    return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
def hull(pts):
    pts = sorted(set(pts))
    if len(pts) <= 1: return pts
    lo = []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    up = []
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); idx = 1
    pts = []
    for _ in range(n):
        pts.append((int(data[idx]), int(data[idx+1]))); idx += 2
    print(len(hull(pts)))
main()
""",
    "EX_GE_HULL_AREA": r"""import sys
def cross(o, a, b):
    return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
def hull(pts):
    pts = sorted(set(pts))
    if len(pts) <= 1: return pts
    lo = []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    up = []
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); idx = 1
    pts = []
    for _ in range(n):
        pts.append((int(data[idx]), int(data[idx+1]))); idx += 2
    h = hull(pts)
    if len(h) < 3:
        print(0); return
    s = 0
    m = len(h)
    for i in range(m):
        x1, y1 = h[i]; x2, y2 = h[(i+1) % m]
        s += x1*y2 - x2*y1
    print(abs(s))
main()
""",
    "EX_GE_DIAMETER": r"""import sys
def cross(o, a, b):
    return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
def hull(pts):
    pts = sorted(set(pts))
    if len(pts) <= 1: return pts
    lo = []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    up = []
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]
def d2(a, b): return (a[0]-b[0])**2 + (a[1]-b[1])**2
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); idx = 1
    pts = []
    for _ in range(n):
        pts.append((int(data[idx]), int(data[idx+1]))); idx += 2
    h = hull(pts)
    m = len(h)
    if m == 1:
        print(0); return
    if m == 2:
        print(d2(h[0], h[1])); return
    # rotating calipers
    best = 0; j = 1
    for i in range(m):
        ni = (i+1) % m
        while True:
            nj = (j+1) % m
            a = (h[ni][0]-h[i][0], h[ni][1]-h[i][1])
            cur = (h[nj][0]-h[j][0], h[nj][1]-h[j][1])
            if a[0]*cur[1] - a[1]*cur[0] > 0:
                j = nj
            else:
                break
        best = max(best, d2(h[i], h[j]), d2(h[ni], h[j]))
    print(best)
main()
""",
    "EX_GE_CLOSEST_PAIR": r"""import sys
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); idx = 1
    pts = []
    for _ in range(n):
        pts.append((int(data[idx]), int(data[idx+1]))); idx += 2
    pts.sort()
    best = None
    # sweep: keep a window sorted by x; for each point compare to earlier
    # points whose x is within the current best; among those, only y-close
    # ones matter. On the shipped sizes a direct scan of the window suffices.
    import bisect
    win = []  # (y, x) of active points
    lo = 0
    import math
    for i in range(n):
        x, y = pts[i]
        if best is not None:
            d = math.isqrt(best) + 1
            while lo < i and pts[lo][0] < x - d:
                yy, xx = pts[lo][1], pts[lo][0]
                win.pop(bisect.bisect_left(win, (yy, xx)))
                lo += 1
            d = math.isqrt(best) + 1
            l = bisect.bisect_left(win, (y - d, -(1 << 62)))
            r = bisect.bisect_right(win, (y + d, (1 << 62)))
        else:
            l, r = 0, len(win)
        for k in range(l, r):
            yy, xx = win[k]
            dd = (x - xx) ** 2 + (y - yy) ** 2
            if best is None or dd < best:
                best = dd
        bisect.insort(win, (y, x))
    print(best)
main()
""",
    "EX_GE_RECT_UNION": r"""import sys
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); idx = 1
    rects = []
    for _ in range(n):
        rects.append((int(data[idx]), int(data[idx+1]), int(data[idx+2]), int(data[idx+3]))); idx += 4
    xs = sorted(set([r[0] for r in rects] + [r[2] for r in rects]))
    total = 0
    for i in range(len(xs)-1):
        x1, x2 = xs[i], xs[i+1]
        width = x2 - x1
        ys = []
        for rx1, ry1, rx2, ry2 in rects:
            if rx1 <= x1 and x2 <= rx2:
                ys.append((ry1, ry2))
        ys.sort()
        covered = 0; cur_lo = cur_hi = None
        for lo, hi in ys:
            if cur_hi is None:
                cur_lo, cur_hi = lo, hi
            elif lo > cur_hi:
                covered += cur_hi - cur_lo; cur_lo, cur_hi = lo, hi
            else:
                if hi > cur_hi: cur_hi = hi
        if cur_hi is not None:
            covered += cur_hi - cur_lo
        total += width * covered
    print(total)
main()
""",
    "EX_GE_MAX_OVERLAP": r"""import sys
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); idx = 1
    rects = []
    for _ in range(n):
        rects.append((int(data[idx]), int(data[idx+1]), int(data[idx+2]), int(data[idx+3]))); idx += 4
    xs = sorted(set([r[0] for r in rects] + [r[2] for r in rects]))
    ys = sorted(set([r[1] for r in rects] + [r[3] for r in rects]))
    best = 0
    for i in range(len(xs)-1):
        cx = xs[i]; cx2 = xs[i+1]
        active = [r for r in rects if r[0] <= cx and cx2 <= r[2]]
        for j in range(len(ys)-1):
            cy = ys[j]; cy2 = ys[j+1]
            cnt = 0
            for r in active:
                if r[1] <= cy and cy2 <= r[3]:
                    cnt += 1
            if cnt > best: best = cnt
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
                    f"      - exercise {ex['key']:<24} "
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
    print(f"Chapitre 10 - Geometrie computationnelle : OK ({state}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
