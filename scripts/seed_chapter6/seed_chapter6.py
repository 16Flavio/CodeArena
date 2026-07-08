"""Seed Chapter 6 - Graphes.

Cree (ou met a jour) la section ``graphes`` avec six lecons :

  1. Representations & parcours BFS/DFS
  2. Applications des parcours (composantes, cycles, tri topologique, bipartisme)
  3. Plus courts chemins
  4. Arbres couvrants minimaux
  5. Connectivite (SCC, ponts, points d'articulation)
  6. Flots & couplages

Chaque lecon contient trois exercices inline gradues (standard,
twist, dur). Idempotent.

Pre-deploiement le script verifie que chaque solution de reference
passe sur ses test cases (--validate-only pour ne faire QUE ca, sans
toucher a la base).

Usage:
    python scripts/seed_chapter6/seed_chapter6.py
    python scripts/seed_chapter6/seed_chapter6.py --draft
    python scripts/seed_chapter6/seed_chapter6.py --validate-only
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
    "slug": "graphes",
    "title_fr": "Graphes",
    "title_en": "Graphs",
    "description_fr": (
        "Le langage des graphes et ses algorithmes : parcours en largeur "
        "et en profondeur et leurs applications (composantes, cycles, tri "
        "topologique, bipartisme), plus courts chemins (Dijkstra, "
        "Bellman-Ford, Floyd-Warshall), arbres couvrants minimaux "
        "(Kruskal, Prim), connectivite avancee (composantes fortement "
        "connexes, ponts, points d'articulation) et flots maximaux avec "
        "couplages bipartis."
    ),
    "description_en": (
        "The language of graphs and its algorithms: breadth-first and "
        "depth-first search and their applications (components, cycles, "
        "topological sort, bipartiteness), shortest paths (Dijkstra, "
        "Bellman-Ford, Floyd-Warshall), minimum spanning trees (Kruskal, "
        "Prim), advanced connectivity (strongly connected components, "
        "bridges, articulation points) and maximum flow with bipartite "
        "matching."
    ),
    "order_idx": 5,
}


LESSONS: list[dict] = [
    # =================================================================
    # Lesson 1 - Representations & parcours BFS/DFS
    # =================================================================
    {
        "slug": "representations-parcours",
        "title_fr": "Representations & parcours BFS/DFS",
        "title_en": "Representations & BFS/DFS Traversal",
        "order_idx": 0,
        "content_fr_file": "lesson_01_traversals.fr.md",
        "content_en_file": "lesson_01_traversals.en.md",
        "exercises": [
            {
                "key": "EX_GR_BFS_DIST",
                "title_fr": "Plus court chemin non pondere",
                "title_en": "Unweighted shortest path",
                "prompt_fr": (
                    "Dans un graphe **non oriente non pondere**, trouver le "
                    "nombre minimal d'aretes d'un chemin de $s$ a $t$.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ et $m$ ($1 \\le n \\le 10^5$, "
                    "$0 \\le m \\le 2 \\cdot 10^5$)\n"
                    "- $m$ lignes : deux sommets $u$ et $v$ (1-indexes)\n"
                    "- derniere ligne : $s$ et $t$\n\n"
                    "**Sortie** : la distance, ou $-1$ si $t$ est "
                    "inatteignable.\n\n"
                    "**Indice** : BFS depuis $s$. La premiere fois qu'on "
                    "atteint un sommet, c'est par un plus court chemin - "
                    "propriete fondamentale du parcours en largeur."
                ),
                "prompt_en": (
                    "In an **undirected unweighted** graph, find the "
                    "minimum number of edges on a path from $s$ to $t$.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $m$ ($1 \\le n \\le 10^5$, "
                    "$0 \\le m \\le 2 \\cdot 10^5$)\n"
                    "- $m$ lines: two vertices $u$ and $v$ (1-indexed)\n"
                    "- last line: $s$ and $t$\n\n"
                    "**Output**: the distance, or $-1$ if $t$ is "
                    "unreachable.\n\n"
                    "**Hint**: BFS from $s$. The first time a vertex is "
                    "reached, it is via a shortest path - the fundamental "
                    "property of breadth-first search."
                ),
                "starter_code": (
                    "import sys\n"
                    "from collections import deque\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    idx = 0\n"
                    "    n = int(data[idx]); m = int(data[idx+1]); idx += 2\n"
                    "    adj = [[] for _ in range(n)]\n"
                    "    for _ in range(m):\n"
                    "        u = int(data[idx])-1; v = int(data[idx+1])-1; idx += 2\n"
                    "        adj[u].append(v); adj[v].append(u)\n"
                    "    s = int(data[idx])-1; t = int(data[idx+1])-1\n"
                    "    # TODO: BFS from s.\n"
                    "    print(-1)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5 5\n1 2\n2 3\n3 4\n4 5\n1 5\n1 4\n", "expected": "2\n", "is_sample": True},
                    {"input": "4 2\n1 2\n3 4\n1 4\n", "expected": "-1\n", "is_sample": True},
                    {"input": "1 0\n1 1\n", "expected": "0\n", "is_sample": False},
                    {"input": "6 6\n1 2\n1 3\n2 4\n3 4\n4 5\n5 6\n1 6\n", "expected": "4\n", "is_sample": False},
                    {"input": "3 3\n1 2\n2 3\n1 3\n2 2\n", "expected": "0\n", "is_sample": False},
                    {"input": "5 4\n1 2\n2 3\n3 1\n4 5\n1 5\n", "expected": "-1\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_GR_GRID_BFS",
                "title_fr": "Plus court chemin dans une grille",
                "title_en": "Grid shortest path",
                "prompt_fr": (
                    "Dans une grille $R \\times C$ de cases libres `.` et "
                    "murs `#`, trouver le nombre minimal de deplacements "
                    "(haut/bas/gauche/droite) du coin **haut-gauche** "
                    "$(0,0)$ au coin **bas-droit** $(R-1, C-1)$.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $R$ et $C$ ($1 \\le R, C \\le 1000$)\n"
                    "- $R$ lignes de $C$ caracteres (`.` ou `#`)\n\n"
                    "**Sortie** : la distance, ou $-1$ si le coin d'arrivee "
                    "est inatteignable (ou si un coin est un mur).\n\n"
                    "**Indice** : une grille est un graphe implicite - "
                    "chaque case a jusqu'a 4 voisins. BFS classique, sans "
                    "materialiser la liste d'adjacence."
                ),
                "prompt_en": (
                    "In an $R \\times C$ grid of free cells `.` and walls "
                    "`#`, find the minimum number of moves "
                    "(up/down/left/right) from the **top-left** corner "
                    "$(0,0)$ to the **bottom-right** corner "
                    "$(R-1, C-1)$.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $R$ and $C$ ($1 \\le R, C \\le 1000$)\n"
                    "- $R$ lines of $C$ characters (`.` or `#`)\n\n"
                    "**Output**: the distance, or $-1$ if the destination "
                    "corner is unreachable (or if a corner is a wall).\n\n"
                    "**Hint**: a grid is an implicit graph - each cell has "
                    "up to 4 neighbors. Plain BFS, without materializing "
                    "the adjacency list."
                ),
                "starter_code": (
                    "import sys\n"
                    "from collections import deque\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split('\\n')\n"
                    "    R, C = map(int, data[0].split())\n"
                    "    grid = [data[1+i] for i in range(R)]\n"
                    "    # TODO: BFS from (0,0) to (R-1,C-1).\n"
                    "    print(-1)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "3 3\n...\n.#.\n...\n", "expected": "4\n", "is_sample": True},
                    {"input": "2 2\n.#\n#.\n", "expected": "-1\n", "is_sample": True},
                    {"input": "1 1\n.\n", "expected": "0\n", "is_sample": False},
                    {"input": "3 3\n..#\n##.\n...\n", "expected": "-1\n", "is_sample": False},
                    {"input": "3 4\n....\n.##.\n....\n", "expected": "5\n", "is_sample": False},
                    {"input": "2 3\n.#.\n.#.\n", "expected": "-1\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_GR_ISLANDS",
                "title_fr": "Nombre d'iles",
                "title_en": "Number of islands",
                "prompt_fr": (
                    "Une grille $R \\times C$ de terre `1` et d'eau `0`. "
                    "Compter les **iles** : les composantes connexes de "
                    "terre en **4-connexite** (haut/bas/gauche/droite).\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $R$ et $C$ ($1 \\le R, C \\le 1000$)\n"
                    "- $R$ lignes de $C$ caracteres (`0` ou `1`)\n\n"
                    "**Sortie** : un seul entier - le nombre d'iles.\n\n"
                    "**Indice** : parcourir la grille ; a chaque case de "
                    "terre non encore visitee, lancer un flood fill "
                    "(BFS ou DFS) qui marque toute l'ile, et incrementer "
                    "le compteur."
                ),
                "prompt_en": (
                    "An $R \\times C$ grid of land `1` and water `0`. Count "
                    "the **islands**: the connected components of land in "
                    "**4-connectivity** (up/down/left/right).\n\n"
                    "**Input**:\n\n"
                    "- line 1: $R$ and $C$ ($1 \\le R, C \\le 1000$)\n"
                    "- $R$ lines of $C$ characters (`0` or `1`)\n\n"
                    "**Output**: one integer - the number of islands.\n\n"
                    "**Hint**: scan the grid; at each unvisited land cell, "
                    "launch a flood fill (BFS or DFS) marking the whole "
                    "island, and increment the counter."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split('\\n')\n"
                    "    R, C = map(int, data[0].split())\n"
                    "    grid = [list(data[1+i]) for i in range(R)]\n"
                    "    # TODO: flood fill count.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "4 5\n11000\n11000\n00100\n00011\n", "expected": "3\n", "is_sample": True},
                    {"input": "1 1\n0\n", "expected": "0\n", "is_sample": True},
                    {"input": "3 3\n111\n111\n111\n", "expected": "1\n", "is_sample": False},
                    {"input": "3 3\n101\n010\n101\n", "expected": "5\n", "is_sample": False},
                    {"input": "2 4\n1010\n0101\n", "expected": "4\n", "is_sample": False},
                    {"input": "3 3\n000\n000\n000\n", "expected": "0\n", "is_sample": False},
                ],
            },
        ],
    },

    # =================================================================
    # Lesson 2 - Applications des parcours
    # =================================================================
    {
        "slug": "applications-parcours",
        "title_fr": "Applications des parcours",
        "title_en": "Traversal Applications",
        "order_idx": 1,
        "content_fr_file": "lesson_02_applications.fr.md",
        "content_en_file": "lesson_02_applications.en.md",
        "exercises": [
            {
                "key": "EX_GR_COMPONENTS",
                "title_fr": "Composantes connexes",
                "title_en": "Connected components",
                "prompt_fr": (
                    "Compter le nombre de **composantes connexes** d'un "
                    "graphe non oriente.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ et $m$ ($1 \\le n \\le 10^5$, "
                    "$0 \\le m \\le 2 \\cdot 10^5$)\n"
                    "- $m$ lignes : $u$ et $v$ (1-indexes)\n\n"
                    "**Sortie** : un seul entier.\n\n"
                    "**Indice** : lancer un parcours (DFS/BFS) depuis chaque "
                    "sommet non encore visite ; chaque lancement = une "
                    "nouvelle composante. Union-Find donne la meme reponse "
                    "en quasi-lineaire."
                ),
                "prompt_en": (
                    "Count the number of **connected components** of an "
                    "undirected graph.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $m$ ($1 \\le n \\le 10^5$, "
                    "$0 \\le m \\le 2 \\cdot 10^5$)\n"
                    "- $m$ lines: $u$ and $v$ (1-indexed)\n\n"
                    "**Output**: one integer.\n\n"
                    "**Hint**: run a traversal (DFS/BFS) from each unvisited "
                    "vertex; each launch = one new component. Union-Find "
                    "gives the same answer in near-linear time."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0]); m = int(data[1]); idx = 2\n"
                    "    adj = [[] for _ in range(n)]\n"
                    "    for _ in range(m):\n"
                    "        u = int(data[idx])-1; v = int(data[idx+1])-1; idx += 2\n"
                    "        adj[u].append(v); adj[v].append(u)\n"
                    "    # TODO: count components.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5 3\n1 2\n2 3\n4 5\n", "expected": "2\n", "is_sample": True},
                    {"input": "4 0\n", "expected": "4\n", "is_sample": True},
                    {"input": "1 0\n", "expected": "1\n", "is_sample": False},
                    {"input": "6 3\n1 2\n3 4\n5 6\n", "expected": "3\n", "is_sample": False},
                    {"input": "5 5\n1 2\n2 3\n3 1\n4 5\n5 4\n", "expected": "2\n", "is_sample": False},
                    {"input": "7 4\n1 2\n2 3\n3 4\n5 6\n", "expected": "3\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_GR_BIPARTITE",
                "title_fr": "Test de bipartisme",
                "title_en": "Bipartiteness test",
                "prompt_fr": (
                    "Determiner si un graphe non oriente est **biparti** : "
                    "peut-on 2-colorier les sommets pour qu'aucune arete ne "
                    "relie deux sommets de meme couleur ?\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ et $m$ ($1 \\le n \\le 10^5$, "
                    "$0 \\le m \\le 2 \\cdot 10^5$)\n"
                    "- $m$ lignes : $u$ et $v$ (1-indexes)\n\n"
                    "**Sortie** : `1` si biparti, `0` sinon.\n\n"
                    "**Indice** : BFS/DFS en coloriant alternativement. Un "
                    "graphe est biparti **ssi** il ne contient aucun cycle "
                    "de longueur impaire ; un conflit de coloriage revele "
                    "exactement un tel cycle."
                ),
                "prompt_en": (
                    "Decide whether an undirected graph is **bipartite**: "
                    "can the vertices be 2-colored so that no edge joins two "
                    "same-colored vertices?\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $m$ ($1 \\le n \\le 10^5$, "
                    "$0 \\le m \\le 2 \\cdot 10^5$)\n"
                    "- $m$ lines: $u$ and $v$ (1-indexed)\n\n"
                    "**Output**: `1` if bipartite, `0` otherwise.\n\n"
                    "**Hint**: BFS/DFS coloring alternately. A graph is "
                    "bipartite **iff** it has no odd-length cycle; a "
                    "coloring conflict reveals exactly such a cycle."
                ),
                "starter_code": (
                    "import sys\n"
                    "from collections import deque\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0]); m = int(data[1]); idx = 2\n"
                    "    adj = [[] for _ in range(n)]\n"
                    "    for _ in range(m):\n"
                    "        u = int(data[idx])-1; v = int(data[idx+1])-1; idx += 2\n"
                    "        adj[u].append(v); adj[v].append(u)\n"
                    "    # TODO: 2-coloring.\n"
                    "    print(1)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "4 4\n1 2\n2 3\n3 4\n4 1\n", "expected": "1\n", "is_sample": True},
                    {"input": "3 3\n1 2\n2 3\n3 1\n", "expected": "0\n", "is_sample": True},
                    {"input": "1 0\n", "expected": "1\n", "is_sample": False},
                    {"input": "5 4\n1 2\n2 3\n3 4\n4 5\n", "expected": "1\n", "is_sample": False},
                    {"input": "6 3\n1 2\n3 4\n5 6\n", "expected": "1\n", "is_sample": False},
                    {"input": "5 5\n1 2\n2 3\n3 1\n4 5\n1 4\n", "expected": "0\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_GR_TOPOSORT",
                "title_fr": "Tri topologique lexicographique",
                "title_en": "Lexicographic topological sort",
                "prompt_fr": (
                    "Etant donne un graphe **oriente**, produire l'ordre "
                    "topologique **lexicographiquement le plus petit** "
                    "(sommets 1-indexes), ou detecter un cycle.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ et $m$ ($1 \\le n \\le 10^5$, "
                    "$0 \\le m \\le 2 \\cdot 10^5$)\n"
                    "- $m$ lignes : $u$ et $v$ pour une arete $u \\to v$\n\n"
                    "**Sortie** : les $n$ sommets dans l'ordre, separes par "
                    "des espaces, ou `IMPOSSIBLE` s'il existe un cycle.\n\n"
                    "**Indice** : algorithme de Kahn. Au lieu d'une file, "
                    "utiliser un **tas-min** des sommets de degre entrant "
                    "nul pour obtenir le plus petit ordre lexicographique. "
                    "S'il reste des sommets non emis, il y a un cycle."
                ),
                "prompt_en": (
                    "Given a **directed** graph, output the "
                    "**lexicographically smallest** topological order "
                    "(1-indexed vertices), or detect a cycle.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $m$ ($1 \\le n \\le 10^5$, "
                    "$0 \\le m \\le 2 \\cdot 10^5$)\n"
                    "- $m$ lines: $u$ and $v$ for an edge $u \\to v$\n\n"
                    "**Output**: the $n$ vertices in order, space-separated, "
                    "or `IMPOSSIBLE` if a cycle exists.\n\n"
                    "**Hint**: Kahn's algorithm. Instead of a queue, use a "
                    "**min-heap** of zero-indegree vertices to get the "
                    "lexicographically smallest order. If vertices remain "
                    "unemitted, there is a cycle."
                ),
                "starter_code": (
                    "import sys, heapq\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0]); m = int(data[1]); idx = 2\n"
                    "    adj = [[] for _ in range(n)]; indeg = [0]*n\n"
                    "    for _ in range(m):\n"
                    "        u = int(data[idx])-1; v = int(data[idx+1])-1; idx += 2\n"
                    "        adj[u].append(v); indeg[v] += 1\n"
                    "    # TODO: Kahn with a min-heap.\n"
                    "    print('IMPOSSIBLE')\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "4 3\n1 2\n1 3\n3 4\n", "expected": "1 2 3 4\n", "is_sample": True},
                    {"input": "3 3\n1 2\n2 3\n3 1\n", "expected": "IMPOSSIBLE\n", "is_sample": True},
                    {"input": "1 0\n", "expected": "1\n", "is_sample": False},
                    {"input": "5 4\n2 1\n3 1\n4 2\n4 3\n", "expected": "4 2 3 1 5\n", "is_sample": False},
                    {"input": "6 6\n1 2\n1 3\n2 4\n3 4\n4 5\n4 6\n", "expected": "1 2 3 4 5 6\n", "is_sample": False},
                    {"input": "3 0\n", "expected": "1 2 3\n", "is_sample": False},
                ],
            },
        ],
    },

    # =================================================================
    # Lesson 3 - Plus courts chemins
    # =================================================================
    {
        "slug": "plus-courts-chemins",
        "title_fr": "Plus courts chemins",
        "title_en": "Shortest Paths",
        "order_idx": 2,
        "content_fr_file": "lesson_03_shortest_paths.fr.md",
        "content_en_file": "lesson_03_shortest_paths.en.md",
        "exercises": [
            {
                "key": "EX_GR_DIJKSTRA",
                "title_fr": "Dijkstra",
                "title_en": "Dijkstra",
                "prompt_fr": (
                    "Graphe **oriente pondere** a poids **positifs ou "
                    "nuls**. Trouver la distance minimale de $s$ a $t$.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ et $m$ ($1 \\le n \\le 10^5$, "
                    "$0 \\le m \\le 2 \\cdot 10^5$)\n"
                    "- $m$ lignes : $u$, $v$, $w$ pour une arete "
                    "$u \\to v$ de poids $w$ ($0 \\le w \\le 10^9$)\n"
                    "- derniere ligne : $s$ et $t$\n\n"
                    "**Sortie** : la distance, ou $-1$ si $t$ est "
                    "inatteignable.\n\n"
                    "**Indice** : Dijkstra avec un tas. On extrait toujours "
                    "le sommet non finalise de distance minimale ; sa "
                    "distance est alors definitive - c'est la preuve de "
                    "correction, valable **uniquement** sans poids negatif."
                ),
                "prompt_en": (
                    "**Directed weighted** graph with **non-negative** "
                    "weights. Find the minimum distance from $s$ to $t$.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $m$ ($1 \\le n \\le 10^5$, "
                    "$0 \\le m \\le 2 \\cdot 10^5$)\n"
                    "- $m$ lines: $u$, $v$, $w$ for an edge $u \\to v$ of "
                    "weight $w$ ($0 \\le w \\le 10^9$)\n"
                    "- last line: $s$ and $t$\n\n"
                    "**Output**: the distance, or $-1$ if $t$ is "
                    "unreachable.\n\n"
                    "**Hint**: Dijkstra with a heap. Always extract the "
                    "unfinalized vertex of minimum distance; its distance is "
                    "then final - that is the correctness proof, valid "
                    "**only** without negative weights."
                ),
                "starter_code": (
                    "import sys, heapq\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0]); m = int(data[1]); idx = 2\n"
                    "    adj = [[] for _ in range(n)]\n"
                    "    for _ in range(m):\n"
                    "        u = int(data[idx])-1; v = int(data[idx+1])-1; w = int(data[idx+2]); idx += 3\n"
                    "        adj[u].append((v, w))\n"
                    "    s = int(data[idx])-1; t = int(data[idx+1])-1\n"
                    "    # TODO: Dijkstra.\n"
                    "    print(-1)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5 6\n1 2 2\n2 3 2\n1 3 5\n3 4 1\n4 5 3\n2 5 10\n1 5\n", "expected": "8\n", "is_sample": True},
                    {"input": "3 1\n1 2 4\n1 3\n", "expected": "-1\n", "is_sample": True},
                    {"input": "1 0\n1 1\n", "expected": "0\n", "is_sample": False},
                    {"input": "4 4\n1 2 1\n2 3 1\n3 4 1\n1 4 10\n1 4\n", "expected": "3\n", "is_sample": False},
                    {"input": "5 5\n1 2 3\n1 3 8\n2 3 2\n3 5 4\n2 5 100\n1 5\n", "expected": "9\n", "is_sample": False},
                    {"input": "2 0\n1 2\n", "expected": "-1\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_GR_NEGCYCLE",
                "title_fr": "Detection de cycle negatif",
                "title_en": "Negative cycle detection",
                "prompt_fr": (
                    "Graphe **oriente pondere** a poids quelconques "
                    "(possiblement negatifs). Le graphe contient-il un "
                    "**cycle de poids total negatif** ?\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ et $m$ ($1 \\le n \\le 2000$, "
                    "$0 \\le m \\le 10^4$)\n"
                    "- $m$ lignes : $u$, $v$, $w$ ($|w| \\le 10^9$)\n\n"
                    "**Sortie** : `1` s'il existe un cycle negatif "
                    "(n'importe ou dans le graphe), `0` sinon.\n\n"
                    "**Indice** : Bellman-Ford. Initialiser toutes les "
                    "distances a $0$ (comme si une source virtuelle "
                    "atteignait tout le monde a cout nul), relaxer $n-1$ "
                    "fois, puis tester une $n$-ieme passe : si une arete "
                    "se relache encore, un cycle negatif est atteignable."
                ),
                "prompt_en": (
                    "**Directed weighted** graph with arbitrary "
                    "(possibly negative) weights. Does the graph contain a "
                    "**negative-total-weight cycle**?\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $m$ ($1 \\le n \\le 2000$, "
                    "$0 \\le m \\le 10^4$)\n"
                    "- $m$ lines: $u$, $v$, $w$ ($|w| \\le 10^9$)\n\n"
                    "**Output**: `1` if a negative cycle exists (anywhere in "
                    "the graph), `0` otherwise.\n\n"
                    "**Hint**: Bellman-Ford. Initialize all distances to $0$ "
                    "(as if a virtual source reached everyone at zero cost), "
                    "relax $n-1$ times, then test an $n$-th pass: if any edge "
                    "still relaxes, a negative cycle is reachable."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0]); m = int(data[1]); idx = 2\n"
                    "    edges = []\n"
                    "    for _ in range(m):\n"
                    "        u = int(data[idx])-1; v = int(data[idx+1])-1; w = int(data[idx+2]); idx += 3\n"
                    "        edges.append((u, v, w))\n"
                    "    # TODO: Bellman-Ford negative cycle detection.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "3 3\n1 2 1\n2 3 -1\n3 1 -1\n", "expected": "1\n", "is_sample": True},
                    {"input": "3 3\n1 2 1\n2 3 2\n1 3 4\n", "expected": "0\n", "is_sample": True},
                    {"input": "1 0\n", "expected": "0\n", "is_sample": False},
                    {"input": "4 4\n1 2 1\n2 3 1\n3 4 1\n4 2 -5\n", "expected": "1\n", "is_sample": False},
                    {"input": "3 2\n1 2 -3\n2 3 -4\n", "expected": "0\n", "is_sample": False},
                    {"input": "2 2\n1 2 3\n2 1 -2\n", "expected": "0\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_GR_FLOYD",
                "title_fr": "Floyd-Warshall (toutes paires)",
                "title_en": "Floyd-Warshall (all pairs)",
                "prompt_fr": (
                    "Graphe **oriente pondere** sans cycle negatif. Repondre "
                    "a $q$ requetes de plus court chemin.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ et $m$ ($1 \\le n \\le 400$)\n"
                    "- $m$ lignes : $u$, $v$, $w$ ($|w| \\le 10^6$)\n"
                    "- ligne suivante : $q$\n"
                    "- $q$ lignes : $u$ et $v$\n\n"
                    "**Sortie** : $q$ lignes, la distance de $u$ a $v$ pour "
                    "chaque requete, ou $-1$ si inatteignable ("
                    "$d(u, u) = 0$).\n\n"
                    "**Indice** : Floyd-Warshall. `d[i][j]` se relache via "
                    "un sommet intermediaire $k$ : la boucle **externe** "
                    "porte sur $k$. En $O(n^3)$, on obtient toutes les "
                    "paires d'un coup."
                ),
                "prompt_en": (
                    "**Directed weighted** graph with no negative cycle. "
                    "Answer $q$ shortest-path queries.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $m$ ($1 \\le n \\le 400$)\n"
                    "- $m$ lines: $u$, $v$, $w$ ($|w| \\le 10^6$)\n"
                    "- next line: $q$\n"
                    "- $q$ lines: $u$ and $v$\n\n"
                    "**Output**: $q$ lines, the distance from $u$ to $v$ for "
                    "each query, or $-1$ if unreachable ($d(u, u) = 0$).\n\n"
                    "**Hint**: Floyd-Warshall. `d[i][j]` relaxes via an "
                    "intermediate vertex $k$: the **outer** loop is over "
                    "$k$. In $O(n^3)$ you get all pairs at once."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0]); m = int(data[1]); idx = 2\n"
                    "    INF = float('inf')\n"
                    "    d = [[INF]*n for _ in range(n)]\n"
                    "    for i in range(n): d[i][i] = 0\n"
                    "    for _ in range(m):\n"
                    "        u = int(data[idx])-1; v = int(data[idx+1])-1; w = int(data[idx+2]); idx += 3\n"
                    "        if w < d[u][v]: d[u][v] = w\n"
                    "    q = int(data[idx]); idx += 1\n"
                    "    # TODO: Floyd-Warshall, then answer queries.\n"
                    "    print()\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "4 4\n1 2 3\n2 3 1\n1 3 10\n3 4 2\n3\n1 4\n1 3\n4 1\n", "expected": "6\n4\n-1\n", "is_sample": True},
                    {"input": "3 2\n1 2 5\n2 3 5\n2\n1 3\n3 1\n", "expected": "10\n-1\n", "is_sample": True},
                    {"input": "2 1\n1 2 7\n1\n1 2\n", "expected": "7\n", "is_sample": False},
                    {"input": "4 3\n1 2 -2\n2 3 -1\n3 4 2\n2\n1 4\n2 4\n", "expected": "-1\n1\n", "is_sample": False},
                    {"input": "3 3\n1 2 1\n2 3 1\n1 3 1\n1\n1 1\n", "expected": "0\n", "is_sample": False},
                    {"input": "5 4\n1 2 4\n2 3 4\n3 4 4\n4 5 4\n2\n1 5\n5 1\n", "expected": "16\n-1\n", "is_sample": False},
                ],
            },
        ],
    },

    # =================================================================
    # Lesson 4 - Arbres couvrants minimaux
    # =================================================================
    {
        "slug": "arbres-couvrants",
        "title_fr": "Arbres couvrants minimaux",
        "title_en": "Minimum Spanning Trees",
        "order_idx": 3,
        "content_fr_file": "lesson_04_mst.fr.md",
        "content_en_file": "lesson_04_mst.en.md",
        "exercises": [
            {
                "key": "EX_GR_MST",
                "title_fr": "Poids de l'arbre couvrant minimal",
                "title_en": "Minimum spanning tree weight",
                "prompt_fr": (
                    "Graphe **non oriente pondere**. Calculer le poids total "
                    "de l'**arbre couvrant minimal** (MST).\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ et $m$ ($1 \\le n \\le 10^5$, "
                    "$0 \\le m \\le 2 \\cdot 10^5$)\n"
                    "- $m$ lignes : $u$, $v$, $w$ ($1 \\le w \\le 10^9$)\n\n"
                    "**Sortie** : le poids du MST, ou $-1$ si le graphe "
                    "n'est **pas connexe** (aucun arbre couvrant).\n\n"
                    "**Indice** : Kruskal. Trier les aretes par poids "
                    "croissant, les ajouter si elles relient deux "
                    "composantes differentes (Union-Find). L'argument "
                    "d'echange (leçon sur le glouton) prouve l'optimalite."
                ),
                "prompt_en": (
                    "**Undirected weighted** graph. Compute the total weight "
                    "of the **minimum spanning tree** (MST).\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $m$ ($1 \\le n \\le 10^5$, "
                    "$0 \\le m \\le 2 \\cdot 10^5$)\n"
                    "- $m$ lines: $u$, $v$, $w$ ($1 \\le w \\le 10^9$)\n\n"
                    "**Output**: the MST weight, or $-1$ if the graph is "
                    "**not connected** (no spanning tree).\n\n"
                    "**Hint**: Kruskal. Sort edges by increasing weight, add "
                    "one if it joins two different components (Union-Find). "
                    "The exchange argument (greedy lesson) proves "
                    "optimality."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0]); m = int(data[1]); idx = 2\n"
                    "    edges = []\n"
                    "    for _ in range(m):\n"
                    "        u = int(data[idx])-1; v = int(data[idx+1])-1; w = int(data[idx+2]); idx += 3\n"
                    "        edges.append((w, u, v))\n"
                    "    # TODO: Kruskal.\n"
                    "    print(-1)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "4 5\n1 2 1\n2 3 2\n3 4 3\n4 1 4\n1 3 5\n", "expected": "6\n", "is_sample": True},
                    {"input": "3 1\n1 2 5\n", "expected": "-1\n", "is_sample": True},
                    {"input": "1 0\n", "expected": "0\n", "is_sample": False},
                    {"input": "4 4\n1 2 1\n2 3 2\n3 4 3\n1 4 100\n", "expected": "6\n", "is_sample": False},
                    {"input": "5 6\n1 2 2\n1 3 3\n2 3 1\n3 4 4\n4 5 5\n2 5 6\n", "expected": "12\n", "is_sample": False},
                    {"input": "3 3\n1 2 1\n2 3 1\n1 3 1\n", "expected": "2\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_GR_BOTTLENECK",
                "title_fr": "Arbre couvrant de goulot minimal",
                "title_en": "Minimum bottleneck spanning tree",
                "prompt_fr": (
                    "Graphe **non oriente pondere**. Trouver la plus petite "
                    "valeur $B$ telle qu'il existe un arbre couvrant dont "
                    "**toutes** les aretes ont un poids $\\le B$ (on "
                    "minimise l'arete maximale de l'arbre couvrant).\n\n"
                    "**Entree** : identique a l'exercice MST.\n\n"
                    "**Sortie** : le goulot minimal $B$, ou $-1$ si le "
                    "graphe n'est pas connexe.\n\n"
                    "**Indice** : le MST est aussi un arbre couvrant de "
                    "**goulot minimal** - sa plus grande arete est la "
                    "reponse. (Reciproque non vraie : un arbre de goulot "
                    "minimal n'est pas forcement un MST.)"
                ),
                "prompt_en": (
                    "**Undirected weighted** graph. Find the smallest value "
                    "$B$ such that there is a spanning tree whose **every** "
                    "edge has weight $\\le B$ (you minimize the maximum edge "
                    "of the spanning tree).\n\n"
                    "**Input**: identical to the MST exercise.\n\n"
                    "**Output**: the minimum bottleneck $B$, or $-1$ if the "
                    "graph is not connected.\n\n"
                    "**Hint**: the MST is also a **minimum bottleneck** "
                    "spanning tree - its largest edge is the answer. (The "
                    "converse fails: a minimum bottleneck tree need not be "
                    "an MST.)"
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0]); m = int(data[1]); idx = 2\n"
                    "    edges = []\n"
                    "    for _ in range(m):\n"
                    "        u = int(data[idx])-1; v = int(data[idx+1])-1; w = int(data[idx+2]); idx += 3\n"
                    "        edges.append((w, u, v))\n"
                    "    # TODO: max edge in the MST.\n"
                    "    print(-1)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "4 5\n1 2 1\n2 3 2\n3 4 3\n4 1 4\n1 3 5\n", "expected": "3\n", "is_sample": True},
                    {"input": "3 1\n1 2 5\n", "expected": "-1\n", "is_sample": True},
                    {"input": "1 0\n", "expected": "0\n", "is_sample": False},
                    {"input": "4 4\n1 2 1\n2 3 2\n3 4 3\n1 4 100\n", "expected": "3\n", "is_sample": False},
                    {"input": "5 6\n1 2 2\n1 3 3\n2 3 1\n3 4 4\n4 5 5\n2 5 6\n", "expected": "5\n", "is_sample": False},
                    {"input": "4 5\n1 2 10\n2 3 10\n3 4 10\n1 3 1\n2 4 1\n", "expected": "10\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_GR_SECOND_MST",
                "title_fr": "Deuxieme meilleur arbre couvrant",
                "title_en": "Second-best spanning tree",
                "prompt_fr": (
                    "Graphe **non oriente pondere connexe**. Trouver le "
                    "poids du **deuxieme meilleur** arbre couvrant : le plus "
                    "petit poids d'un arbre couvrant **strictement "
                    "superieur** au poids du MST.\n\n"
                    "**Entree** : identique a l'exercice MST (graphe "
                    "connexe garanti).\n\n"
                    "**Sortie** : le poids du deuxieme meilleur arbre "
                    "couvrant, ou $-1$ s'il n'en existe pas (tous les arbres "
                    "couvrants ont le meme poids, p. ex. le graphe est deja "
                    "un arbre).\n\n"
                    "**Indice** : calculer le MST. Pour chaque arete "
                    "**hors** du MST reliant $u$ a $v$, l'ajouter cree un "
                    "cycle ; retirer la plus grande arete du chemin "
                    "MST entre $u$ et $v$ qui soit **strictement plus "
                    "petite** que l'arete ajoutee. Le minimum de ces "
                    "echanges donne la reponse."
                ),
                "prompt_en": (
                    "**Undirected weighted connected** graph. Find the "
                    "weight of the **second-best** spanning tree: the "
                    "smallest weight of a spanning tree **strictly greater** "
                    "than the MST weight.\n\n"
                    "**Input**: identical to the MST exercise (graph "
                    "guaranteed connected).\n\n"
                    "**Output**: the second-best spanning tree weight, or "
                    "$-1$ if none exists (all spanning trees share the same "
                    "weight, e.g. the graph is already a tree).\n\n"
                    "**Hint**: compute the MST. For each **non**-MST edge "
                    "joining $u$ to $v$, adding it creates a cycle; remove "
                    "the largest edge on the MST path between $u$ and $v$ "
                    "that is **strictly smaller** than the added edge. The "
                    "minimum over these swaps is the answer."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0]); m = int(data[1]); idx = 2\n"
                    "    edges = []\n"
                    "    for _ in range(m):\n"
                    "        u = int(data[idx])-1; v = int(data[idx+1])-1; w = int(data[idx+2]); idx += 3\n"
                    "        edges.append((u, v, w))\n"
                    "    # TODO: second-best spanning tree.\n"
                    "    print(-1)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "4 5\n1 2 1\n2 3 2\n3 4 3\n4 1 4\n1 3 5\n", "expected": "7\n", "is_sample": True},
                    {"input": "3 2\n1 2 1\n2 3 2\n", "expected": "-1\n", "is_sample": True},
                    {"input": "3 3\n1 2 1\n2 3 1\n1 3 1\n", "expected": "-1\n", "is_sample": False},
                    {"input": "4 5\n1 2 1\n2 3 1\n3 4 1\n4 1 1\n1 3 1\n", "expected": "-1\n", "is_sample": False},
                    {"input": "5 6\n1 2 2\n1 3 3\n2 3 1\n3 4 4\n4 5 5\n2 5 6\n", "expected": "13\n", "is_sample": False},
                    {"input": "4 4\n1 2 1\n2 3 2\n3 4 3\n1 4 100\n", "expected": "103\n", "is_sample": False},
                ],
            },
        ],
    },

    # =================================================================
    # Lesson 5 - Connectivite
    # =================================================================
    {
        "slug": "connectivite",
        "title_fr": "Connectivite : SCC, ponts, articulation",
        "title_en": "Connectivity: SCC, Bridges, Articulation",
        "order_idx": 4,
        "content_fr_file": "lesson_05_connectivity.fr.md",
        "content_en_file": "lesson_05_connectivity.en.md",
        "exercises": [
            {
                "key": "EX_GR_SCC",
                "title_fr": "Composantes fortement connexes",
                "title_en": "Strongly connected components",
                "prompt_fr": (
                    "Graphe **oriente**. Compter les **composantes "
                    "fortement connexes** (SCC) : les classes de sommets "
                    "mutuellement atteignables.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ et $m$ ($1 \\le n \\le 10^5$, "
                    "$0 \\le m \\le 2 \\cdot 10^5$)\n"
                    "- $m$ lignes : $u$ et $v$ pour $u \\to v$\n\n"
                    "**Sortie** : un seul entier - le nombre de SCC.\n\n"
                    "**Indice** : Kosaraju - un premier DFS pour ordonner "
                    "les sommets par date de fin, puis un DFS sur le graphe "
                    "**transpose** dans l'ordre inverse. Chaque arbre du "
                    "second parcours est une SCC. (Tarjan fait la meme chose "
                    "en un seul parcours.)"
                ),
                "prompt_en": (
                    "**Directed** graph. Count the **strongly connected "
                    "components** (SCC): the classes of mutually reachable "
                    "vertices.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $m$ ($1 \\le n \\le 10^5$, "
                    "$0 \\le m \\le 2 \\cdot 10^5$)\n"
                    "- $m$ lines: $u$ and $v$ for $u \\to v$\n\n"
                    "**Output**: one integer - the number of SCCs.\n\n"
                    "**Hint**: Kosaraju - a first DFS to order vertices by "
                    "finish time, then a DFS on the **transposed** graph in "
                    "reverse order. Each tree of the second pass is an SCC. "
                    "(Tarjan does the same in a single pass.)"
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0]); m = int(data[1]); idx = 2\n"
                    "    adj = [[] for _ in range(n)]; radj = [[] for _ in range(n)]\n"
                    "    for _ in range(m):\n"
                    "        u = int(data[idx])-1; v = int(data[idx+1])-1; idx += 2\n"
                    "        adj[u].append(v); radj[v].append(u)\n"
                    "    # TODO: Kosaraju / Tarjan.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5 5\n1 2\n2 3\n3 1\n3 4\n4 5\n", "expected": "3\n", "is_sample": True},
                    {"input": "3 3\n1 2\n2 3\n3 1\n", "expected": "1\n", "is_sample": True},
                    {"input": "1 0\n", "expected": "1\n", "is_sample": False},
                    {"input": "4 4\n1 2\n2 1\n3 4\n4 3\n", "expected": "2\n", "is_sample": False},
                    {"input": "6 7\n1 2\n2 3\n3 1\n4 5\n5 6\n6 4\n3 4\n", "expected": "2\n", "is_sample": False},
                    {"input": "4 0\n", "expected": "4\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_GR_BRIDGES",
                "title_fr": "Comptage de ponts",
                "title_en": "Counting bridges",
                "prompt_fr": (
                    "Graphe **non oriente simple** (sans boucle ni arete "
                    "multiple). Compter les **ponts** : les aretes dont le "
                    "retrait augmente le nombre de composantes connexes.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ et $m$ ($1 \\le n \\le 10^5$, "
                    "$0 \\le m \\le 2 \\cdot 10^5$)\n"
                    "- $m$ lignes : $u$ et $v$\n\n"
                    "**Sortie** : un seul entier - le nombre de ponts.\n\n"
                    "**Indice** : DFS avec `disc[u]` (date de decouverte) et "
                    "`low[u]` (plus petite date atteignable en revenant par "
                    "au plus une arete retour). L'arete $(u, v)$ vers un fils "
                    "$v$ est un pont **ssi** `low[v] > disc[u]`."
                ),
                "prompt_en": (
                    "**Undirected simple** graph (no self-loop or multi-"
                    "edge). Count the **bridges**: edges whose removal "
                    "increases the number of connected components.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $m$ ($1 \\le n \\le 10^5$, "
                    "$0 \\le m \\le 2 \\cdot 10^5$)\n"
                    "- $m$ lines: $u$ and $v$\n\n"
                    "**Output**: one integer - the number of bridges.\n\n"
                    "**Hint**: DFS with `disc[u]` (discovery time) and "
                    "`low[u]` (lowest time reachable using at most one back "
                    "edge). The edge $(u, v)$ to a child $v$ is a bridge "
                    "**iff** `low[v] > disc[u]`."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    sys.setrecursionlimit(300000)\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0]); m = int(data[1]); idx = 2\n"
                    "    adj = [[] for _ in range(n)]\n"
                    "    for e in range(m):\n"
                    "        u = int(data[idx])-1; v = int(data[idx+1])-1; idx += 2\n"
                    "        adj[u].append((v, e)); adj[v].append((u, e))\n"
                    "    # TODO: bridge-finding DFS.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5 5\n1 2\n2 3\n3 1\n3 4\n4 5\n", "expected": "2\n", "is_sample": True},
                    {"input": "4 3\n1 2\n2 3\n3 4\n", "expected": "3\n", "is_sample": True},
                    {"input": "1 0\n", "expected": "0\n", "is_sample": False},
                    {"input": "4 4\n1 2\n2 3\n3 4\n4 1\n", "expected": "0\n", "is_sample": False},
                    {"input": "6 6\n1 2\n2 3\n3 1\n4 5\n5 6\n6 4\n", "expected": "0\n", "is_sample": False},
                    {"input": "5 4\n1 2\n2 3\n3 4\n4 5\n", "expected": "4\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_GR_ARTIC",
                "title_fr": "Comptage de points d'articulation",
                "title_en": "Counting articulation points",
                "prompt_fr": (
                    "Graphe **non oriente simple**. Compter les **points "
                    "d'articulation** : les sommets dont le retrait "
                    "augmente le nombre de composantes connexes.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ et $m$ ($1 \\le n \\le 10^5$, "
                    "$0 \\le m \\le 2 \\cdot 10^5$)\n"
                    "- $m$ lignes : $u$ et $v$\n\n"
                    "**Sortie** : un seul entier - le nombre de points "
                    "d'articulation.\n\n"
                    "**Indice** : meme DFS `disc`/`low` que les ponts. Un "
                    "sommet interne $u$ est un point d'articulation ssi il a "
                    "un fils $v$ avec `low[v] >= disc[u]`. La **racine** du "
                    "DFS l'est ssi elle a **au moins deux** fils dans "
                    "l'arbre de parcours."
                ),
                "prompt_en": (
                    "**Undirected simple** graph. Count the **articulation "
                    "points**: vertices whose removal increases the number "
                    "of connected components.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $m$ ($1 \\le n \\le 10^5$, "
                    "$0 \\le m \\le 2 \\cdot 10^5$)\n"
                    "- $m$ lines: $u$ and $v$\n\n"
                    "**Output**: one integer - the number of articulation "
                    "points.\n\n"
                    "**Hint**: same `disc`/`low` DFS as bridges. An internal "
                    "vertex $u$ is an articulation point iff it has a child "
                    "$v$ with `low[v] >= disc[u]`. The DFS **root** is one "
                    "iff it has **at least two** children in the DFS tree."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    sys.setrecursionlimit(300000)\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0]); m = int(data[1]); idx = 2\n"
                    "    adj = [[] for _ in range(n)]\n"
                    "    for _ in range(m):\n"
                    "        u = int(data[idx])-1; v = int(data[idx+1])-1; idx += 2\n"
                    "        adj[u].append(v); adj[v].append(u)\n"
                    "    # TODO: articulation-point DFS.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "5 5\n1 2\n2 3\n3 1\n3 4\n4 5\n", "expected": "2\n", "is_sample": True},
                    {"input": "3 2\n1 2\n2 3\n", "expected": "1\n", "is_sample": True},
                    {"input": "1 0\n", "expected": "0\n", "is_sample": False},
                    {"input": "4 4\n1 2\n2 3\n3 4\n4 1\n", "expected": "0\n", "is_sample": False},
                    {"input": "7 7\n1 2\n2 3\n3 1\n3 4\n4 5\n5 6\n6 4\n", "expected": "2\n", "is_sample": False},
                    {"input": "5 4\n1 2\n1 3\n1 4\n1 5\n", "expected": "1\n", "is_sample": False},
                ],
            },
        ],
    },

    # =================================================================
    # Lesson 6 - Flots & couplages
    # =================================================================
    {
        "slug": "flots-couplages",
        "title_fr": "Flots & couplages",
        "title_en": "Flows & Matching",
        "order_idx": 5,
        "content_fr_file": "lesson_06_flows.fr.md",
        "content_en_file": "lesson_06_flows.en.md",
        "exercises": [
            {
                "key": "EX_GR_MAXFLOW",
                "title_fr": "Flot maximal",
                "title_en": "Maximum flow",
                "prompt_fr": (
                    "Reseau **oriente** de capacites. Calculer le **flot "
                    "maximal** de la source $s$ au puits $t$.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $n$ et $m$ ($1 \\le n \\le 500$, "
                    "$0 \\le m \\le 5000$)\n"
                    "- $m$ lignes : $u$, $v$, $c$ pour un arc $u \\to v$ de "
                    "capacite $c$ ($1 \\le c \\le 10^9$)\n"
                    "- derniere ligne : $s$ et $t$ ($s \\ne t$)\n\n"
                    "**Sortie** : un seul entier - la valeur du flot "
                    "maximal.\n\n"
                    "**Indice** : Edmonds-Karp ou Dinic. Tant qu'il existe "
                    "un chemin augmentant dans le **graphe residuel**, "
                    "pousser du flot. Le theoreme **flot-max / coupe-min** "
                    "garantit l'optimalite : le flot maximal egale la "
                    "capacite de la coupe minimale."
                ),
                "prompt_en": (
                    "**Directed** capacity network. Compute the **maximum "
                    "flow** from source $s$ to sink $t$.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $n$ and $m$ ($1 \\le n \\le 500$, "
                    "$0 \\le m \\le 5000$)\n"
                    "- $m$ lines: $u$, $v$, $c$ for an arc $u \\to v$ of "
                    "capacity $c$ ($1 \\le c \\le 10^9$)\n"
                    "- last line: $s$ and $t$ ($s \\ne t$)\n\n"
                    "**Output**: one integer - the maximum flow value.\n\n"
                    "**Hint**: Edmonds-Karp or Dinic. While an augmenting "
                    "path exists in the **residual graph**, push flow. The "
                    "**max-flow / min-cut** theorem guarantees optimality: "
                    "the max flow equals the minimum cut capacity."
                ),
                "starter_code": (
                    "import sys\n"
                    "from collections import deque\n\n"
                    "def main():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    n = int(data[0]); m = int(data[1]); idx = 2\n"
                    "    edges = []\n"
                    "    for _ in range(m):\n"
                    "        u = int(data[idx])-1; v = int(data[idx+1])-1; c = int(data[idx+2]); idx += 3\n"
                    "        edges.append((u, v, c))\n"
                    "    s = int(data[idx])-1; t = int(data[idx+1])-1\n"
                    "    # TODO: max flow.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "4 5\n1 2 3\n1 3 2\n2 3 1\n2 4 2\n3 4 3\n1 4\n", "expected": "5\n", "is_sample": True},
                    {"input": "2 1\n1 2 7\n1 2\n", "expected": "7\n", "is_sample": True},
                    {"input": "3 2\n1 2 5\n2 3 4\n1 3\n", "expected": "4\n", "is_sample": False},
                    {"input": "4 4\n1 2 1000\n1 3 1000\n2 4 1000\n3 4 1000\n1 4\n", "expected": "2000\n", "is_sample": False},
                    {"input": "6 8\n1 2 10\n1 3 10\n2 3 2\n2 4 4\n2 5 8\n3 5 9\n4 6 10\n5 6 10\n1 6\n", "expected": "14\n", "is_sample": False},
                    {"input": "4 3\n1 2 5\n3 4 5\n2 3 5\n1 4\n", "expected": "5\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_GR_BIPMATCH",
                "title_fr": "Couplage biparti maximal",
                "title_en": "Maximum bipartite matching",
                "prompt_fr": (
                    "Graphe **biparti** entre $L$ sommets a gauche et $R$ a "
                    "droite. Trouver la taille du **couplage maximal** : le "
                    "plus grand ensemble d'aretes sans sommet commun.\n\n"
                    "**Entree** :\n\n"
                    "- ligne 1 : $L$, $R$, $m$ ($1 \\le L, R \\le 500$, "
                    "$0 \\le m \\le L \\cdot R$)\n"
                    "- $m$ lignes : $u$ et $v$ ($u \\in [1, L]$ a gauche, "
                    "$v \\in [1, R]$ a droite)\n\n"
                    "**Sortie** : un seul entier - la taille du couplage "
                    "maximal.\n\n"
                    "**Indice** : algorithme de Kuhn (chemins augmentants). "
                    "Pour chaque sommet gauche, chercher en DFS un chemin "
                    "alternant qui libere un partenaire. C'est un flot "
                    "maximal deguise (capacites unitaires)."
                ),
                "prompt_en": (
                    "**Bipartite** graph between $L$ left vertices and $R$ "
                    "right. Find the size of the **maximum matching**: the "
                    "largest set of edges with no shared vertex.\n\n"
                    "**Input**:\n\n"
                    "- line 1: $L$, $R$, $m$ ($1 \\le L, R \\le 500$, "
                    "$0 \\le m \\le L \\cdot R$)\n"
                    "- $m$ lines: $u$ and $v$ ($u \\in [1, L]$ on the left, "
                    "$v \\in [1, R]$ on the right)\n\n"
                    "**Output**: one integer - the maximum matching size.\n\n"
                    "**Hint**: Kuhn's algorithm (augmenting paths). For each "
                    "left vertex, DFS for an alternating path that frees a "
                    "partner. It is a disguised maximum flow (unit "
                    "capacities)."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    sys.setrecursionlimit(300000)\n"
                    "    data = sys.stdin.read().split()\n"
                    "    L = int(data[0]); R = int(data[1]); m = int(data[2]); idx = 3\n"
                    "    adj = [[] for _ in range(L)]\n"
                    "    for _ in range(m):\n"
                    "        u = int(data[idx])-1; v = int(data[idx+1])-1; idx += 2\n"
                    "        adj[u].append(v)\n"
                    "    # TODO: Kuhn's matching.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "3 3 4\n1 1\n1 2\n2 1\n3 3\n", "expected": "3\n", "is_sample": True},
                    {"input": "2 2 1\n1 1\n", "expected": "1\n", "is_sample": True},
                    {"input": "1 1 0\n", "expected": "0\n", "is_sample": False},
                    {"input": "3 3 3\n1 1\n2 2\n3 3\n", "expected": "3\n", "is_sample": False},
                    {"input": "4 3 5\n1 1\n2 1\n3 2\n4 3\n2 2\n", "expected": "3\n", "is_sample": False},
                    {"input": "3 4 6\n1 1\n1 2\n2 2\n2 3\n3 3\n3 4\n", "expected": "3\n", "is_sample": False},
                ],
            },
            {
                "key": "EX_GR_MINVC",
                "title_fr": "Couverture minimale (Konig)",
                "title_en": "Minimum vertex cover (Konig)",
                "prompt_fr": (
                    "Graphe **biparti**. Trouver la taille de la "
                    "**couverture de sommets minimale** : le plus petit "
                    "ensemble de sommets touchant **toutes** les aretes.\n\n"
                    "**Entree** : identique a l'exercice de couplage "
                    "biparti.\n\n"
                    "**Sortie** : un seul entier - la taille de la "
                    "couverture minimale.\n\n"
                    "**Indice** : theoreme de **Konig** - dans un graphe "
                    "biparti, la taille de la couverture de sommets "
                    "minimale egale la taille du couplage maximal. Il "
                    "suffit donc de calculer le couplage maximal."
                ),
                "prompt_en": (
                    "**Bipartite** graph. Find the size of the **minimum "
                    "vertex cover**: the smallest set of vertices touching "
                    "**every** edge.\n\n"
                    "**Input**: identical to the bipartite matching "
                    "exercise.\n\n"
                    "**Output**: one integer - the minimum vertex cover "
                    "size.\n\n"
                    "**Hint**: **Konig's** theorem - in a bipartite graph, "
                    "the minimum vertex cover size equals the maximum "
                    "matching size. So it suffices to compute the maximum "
                    "matching."
                ),
                "starter_code": (
                    "import sys\n\n"
                    "def main():\n"
                    "    sys.setrecursionlimit(300000)\n"
                    "    data = sys.stdin.read().split()\n"
                    "    L = int(data[0]); R = int(data[1]); m = int(data[2]); idx = 3\n"
                    "    adj = [[] for _ in range(L)]\n"
                    "    for _ in range(m):\n"
                    "        u = int(data[idx])-1; v = int(data[idx+1])-1; idx += 2\n"
                    "        adj[u].append(v)\n"
                    "    # TODO: Konig -> max matching size.\n"
                    "    print(0)\n\n"
                    "main()\n"
                ),
                "test_cases": [
                    {"input": "3 3 4\n1 1\n1 2\n2 1\n3 3\n", "expected": "3\n", "is_sample": True},
                    {"input": "2 2 1\n1 1\n", "expected": "1\n", "is_sample": True},
                    {"input": "1 1 0\n", "expected": "0\n", "is_sample": False},
                    {"input": "3 3 3\n1 1\n2 2\n3 3\n", "expected": "3\n", "is_sample": False},
                    {"input": "4 3 5\n1 1\n2 1\n3 2\n4 3\n2 2\n", "expected": "3\n", "is_sample": False},
                    {"input": "2 3 4\n1 1\n1 2\n2 2\n2 3\n", "expected": "2\n", "is_sample": False},
                ],
            },
        ],
    },
]


# --------------------------------------------------------------------- #
# Reference solutions                                                    #
# --------------------------------------------------------------------- #

REFERENCE_SOLUTIONS = {
    "EX_GR_BFS_DIST": r"""import sys
from collections import deque
def main():
    data = sys.stdin.buffer.read().split()
    idx = 0
    n = int(data[idx]); m = int(data[idx+1]); idx += 2
    adj = [[] for _ in range(n)]
    for _ in range(m):
        u = int(data[idx])-1; v = int(data[idx+1])-1; idx += 2
        adj[u].append(v); adj[v].append(u)
    s = int(data[idx])-1; t = int(data[idx+1])-1
    dist = [-1]*n; dist[s] = 0; q = deque([s])
    while q:
        u = q.popleft()
        for v in adj[u]:
            if dist[v] == -1:
                dist[v] = dist[u]+1; q.append(v)
    print(dist[t])
main()
""",
    "EX_GR_GRID_BFS": r"""import sys
from collections import deque
def main():
    data = sys.stdin.read().split('\n')
    R, C = map(int, data[0].split())
    grid = [data[1+i] for i in range(R)]
    if grid[0][0] == '#' or grid[R-1][C-1] == '#':
        print(-1); return
    dist = [[-1]*C for _ in range(R)]; dist[0][0] = 0
    q = deque([(0,0)])
    while q:
        r,c = q.popleft()
        for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
            nr,nc = r+dr, c+dc
            if 0<=nr<R and 0<=nc<C and grid[nr][nc]=='.' and dist[nr][nc]==-1:
                dist[nr][nc] = dist[r][c]+1; q.append((nr,nc))
    print(dist[R-1][C-1])
main()
""",
    "EX_GR_ISLANDS": r"""import sys
def main():
    data = sys.stdin.read().split('\n')
    R, C = map(int, data[0].split())
    grid = [data[1+i] for i in range(R)]
    seen = [[False]*C for _ in range(R)]
    cnt = 0
    for i in range(R):
        for j in range(C):
            if grid[i][j]=='1' and not seen[i][j]:
                cnt += 1; st = [(i,j)]; seen[i][j] = True
                while st:
                    r,c = st.pop()
                    for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
                        nr,nc = r+dr, c+dc
                        if 0<=nr<R and 0<=nc<C and grid[nr][nc]=='1' and not seen[nr][nc]:
                            seen[nr][nc] = True; st.append((nr,nc))
    print(cnt)
main()
""",
    "EX_GR_COMPONENTS": r"""import sys
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); m = int(data[1]); idx = 2
    par = list(range(n))
    def f(x):
        while par[x]!=x: par[x]=par[par[x]]; x=par[x]
        return x
    for _ in range(m):
        u = int(data[idx])-1; v = int(data[idx+1])-1; idx += 2
        par[f(u)] = f(v)
    print(len({f(i) for i in range(n)}))
main()
""",
    "EX_GR_BIPARTITE": r"""import sys
from collections import deque
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); m = int(data[1]); idx = 2
    adj = [[] for _ in range(n)]
    for _ in range(m):
        u = int(data[idx])-1; v = int(data[idx+1])-1; idx += 2
        adj[u].append(v); adj[v].append(u)
    color = [-1]*n
    for s in range(n):
        if color[s]!=-1: continue
        color[s] = 0; q = deque([s])
        while q:
            u = q.popleft()
            for v in adj[u]:
                if color[v]==-1: color[v]=color[u]^1; q.append(v)
                elif color[v]==color[u]: print(0); return
    print(1)
main()
""",
    "EX_GR_TOPOSORT": r"""import sys, heapq
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); m = int(data[1]); idx = 2
    adj = [[] for _ in range(n)]; indeg = [0]*n
    for _ in range(m):
        u = int(data[idx])-1; v = int(data[idx+1])-1; idx += 2
        adj[u].append(v); indeg[v] += 1
    h = [i for i in range(n) if indeg[i]==0]; heapq.heapify(h)
    order = []
    while h:
        u = heapq.heappop(h); order.append(u)
        for v in adj[u]:
            indeg[v] -= 1
            if indeg[v]==0: heapq.heappush(h, v)
    if len(order)!=n:
        print("IMPOSSIBLE")
    else:
        print(" ".join(str(x+1) for x in order))
main()
""",
    "EX_GR_DIJKSTRA": r"""import sys, heapq
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); m = int(data[1]); idx = 2
    adj = [[] for _ in range(n)]
    for _ in range(m):
        u = int(data[idx])-1; v = int(data[idx+1])-1; w = int(data[idx+2]); idx += 3
        adj[u].append((v, w))
    s = int(data[idx])-1; t = int(data[idx+1])-1
    INF = float('inf')
    dist = [INF]*n; dist[s] = 0; pq = [(0, s)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]: continue
        for v, w in adj[u]:
            nd = d + w
            if nd < dist[v]: dist[v] = nd; heapq.heappush(pq, (nd, v))
    print(dist[t] if dist[t] != INF else -1)
main()
""",
    "EX_GR_NEGCYCLE": r"""import sys
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); m = int(data[1]); idx = 2
    edges = []
    for _ in range(m):
        u = int(data[idx])-1; v = int(data[idx+1])-1; w = int(data[idx+2]); idx += 3
        edges.append((u, v, w))
    dist = [0]*n
    for _ in range(n-1):
        changed = False
        for u, v, w in edges:
            if dist[u]+w < dist[v]: dist[v] = dist[u]+w; changed = True
        if not changed: break
    for u, v, w in edges:
        if dist[u]+w < dist[v]: print(1); return
    print(0)
main()
""",
    "EX_GR_FLOYD": r"""import sys
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); m = int(data[1]); idx = 2
    INF = float('inf')
    d = [[INF]*n for _ in range(n)]
    for i in range(n): d[i][i] = 0
    for _ in range(m):
        u = int(data[idx])-1; v = int(data[idx+1])-1; w = int(data[idx+2]); idx += 3
        if w < d[u][v]: d[u][v] = w
    for k in range(n):
        dk = d[k]
        for i in range(n):
            dik = d[i][k]
            if dik == INF: continue
            di = d[i]
            for j in range(n):
                nd = dik + dk[j]
                if nd < di[j]: di[j] = nd
    q = int(data[idx]); idx += 1
    out = []
    for _ in range(q):
        u = int(data[idx])-1; v = int(data[idx+1])-1; idx += 2
        out.append(str(-1 if d[u][v]==INF else d[u][v]))
    print("\n".join(out))
main()
""",
    "EX_GR_MST": r"""import sys
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); m = int(data[1]); idx = 2
    edges = []
    for _ in range(m):
        u = int(data[idx])-1; v = int(data[idx+1])-1; w = int(data[idx+2]); idx += 3
        edges.append((w, u, v))
    edges.sort()
    par = list(range(n))
    def f(x):
        while par[x]!=x: par[x]=par[par[x]]; x=par[x]
        return x
    total = 0
    for w, u, v in edges:
        ru, rv = f(u), f(v)
        if ru != rv: par[ru] = rv; total += w
    print(total if len({f(i) for i in range(n)})==1 else -1)
main()
""",
    "EX_GR_BOTTLENECK": r"""import sys
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); m = int(data[1]); idx = 2
    edges = []
    for _ in range(m):
        u = int(data[idx])-1; v = int(data[idx+1])-1; w = int(data[idx+2]); idx += 3
        edges.append((w, u, v))
    edges.sort()
    par = list(range(n))
    def f(x):
        while par[x]!=x: par[x]=par[par[x]]; x=par[x]
        return x
    mx = 0
    for w, u, v in edges:
        ru, rv = f(u), f(v)
        if ru != rv: par[ru] = rv; mx = max(mx, w)
    print(mx if len({f(i) for i in range(n)})==1 else -1)
main()
""",
    "EX_GR_SECOND_MST": r"""import sys
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); m = int(data[1]); idx = 2
    edges = []
    for _ in range(m):
        u = int(data[idx])-1; v = int(data[idx+1])-1; w = int(data[idx+2]); idx += 3
        edges.append((u, v, w))
    par = list(range(n))
    def f(x):
        while par[x]!=x: par[x]=par[par[x]]; x=par[x]
        return x
    W0 = 0; tree_set = set()
    adj = [[] for _ in range(n)]
    for w, u, v in sorted((w,u,v) for u,v,w in edges):
        ru, rv = f(u), f(v)
        if ru != rv:
            par[ru] = rv; W0 += w
            tree_set.add((u,v)); tree_set.add((v,u))
            adj[u].append((v,w)); adj[v].append((u,w))
    best = float('inf')
    for u, v, w in edges:
        if (u, v) in tree_set: continue
        parent = {u: -1}; pmax = {u: (-1, -1)}; st = [u]
        while st:
            x = st.pop()
            if x == v: break
            for y, wy in adj[x]:
                if y not in parent:
                    parent[y] = x
                    m1, m2 = pmax[x]
                    if wy > m1: nm1, nm2 = wy, m1
                    elif wy > m2: nm1, nm2 = m1, wy
                    else: nm1, nm2 = m1, m2
                    pmax[y] = (nm1, nm2); st.append(y)
        m1, m2 = pmax[v]
        if m1 < w: cand = W0 + w - m1
        elif m2 != -1 and m2 < w: cand = W0 + w - m2
        else: continue
        if cand > W0 and cand < best: best = cand
    print(best if best != float('inf') else -1)
main()
""",
    "EX_GR_SCC": r"""import sys
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); m = int(data[1]); idx = 2
    adj = [[] for _ in range(n)]; radj = [[] for _ in range(n)]
    for _ in range(m):
        u = int(data[idx])-1; v = int(data[idx+1])-1; idx += 2
        adj[u].append(v); radj[v].append(u)
    seen = [False]*n; order = []
    for s in range(n):
        if seen[s]: continue
        st = [(s, 0)]
        while st:
            u, i = st.pop()
            if i == 0:
                if seen[u]: continue
                seen[u] = True
            if i < len(adj[u]):
                st.append((u, i+1))
                w = adj[u][i]
                if not seen[w]: st.append((w, 0))
            else:
                order.append(u)
    comp = [-1]*n; c = 0
    for u in reversed(order):
        if comp[u] != -1: continue
        st = [u]; comp[u] = c
        while st:
            x = st.pop()
            for y in radj[x]:
                if comp[y] == -1: comp[y] = c; st.append(y)
        c += 1
    print(c)
main()
""",
    "EX_GR_BRIDGES": r"""import sys
def main():
    sys.setrecursionlimit(300000)
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); m = int(data[1]); idx = 2
    adj = [[] for _ in range(n)]
    for e in range(m):
        u = int(data[idx])-1; v = int(data[idx+1])-1; idx += 2
        adj[u].append((v, e)); adj[v].append((u, e))
    disc = [-1]*n; low = [0]*n; timer = [0]; cnt = [0]
    def dfs(u, pe):
        disc[u] = low[u] = timer[0]; timer[0] += 1
        for v, ei in adj[u]:
            if ei == pe: continue
            if disc[v] == -1:
                dfs(v, ei)
                if low[v] < low[u]: low[u] = low[v]
                if low[v] > disc[u]: cnt[0] += 1
            else:
                if disc[v] < low[u]: low[u] = disc[v]
    for s in range(n):
        if disc[s] == -1: dfs(s, -1)
    print(cnt[0])
main()
""",
    "EX_GR_ARTIC": r"""import sys
def main():
    sys.setrecursionlimit(300000)
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); m = int(data[1]); idx = 2
    adj = [[] for _ in range(n)]
    for _ in range(m):
        u = int(data[idx])-1; v = int(data[idx+1])-1; idx += 2
        adj[u].append(v); adj[v].append(u)
    disc = [-1]*n; low = [0]*n; timer = [0]; ap = [False]*n
    def dfs(u, parent):
        disc[u] = low[u] = timer[0]; timer[0] += 1
        children = 0
        for v in adj[u]:
            if v == parent: continue
            if disc[v] == -1:
                children += 1
                dfs(v, u)
                if low[v] < low[u]: low[u] = low[v]
                if parent != -1 and low[v] >= disc[u]: ap[u] = True
            else:
                if disc[v] < low[u]: low[u] = disc[v]
        if parent == -1 and children > 1: ap[u] = True
    for s in range(n):
        if disc[s] == -1: dfs(s, -1)
    print(sum(ap))
main()
""",
    "EX_GR_MAXFLOW": r"""import sys
from collections import deque
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0]); m = int(data[1]); idx = 2
    graph = [[] for _ in range(n)]
    def add(u, v, c):
        graph[u].append([v, c, len(graph[v])])
        graph[v].append([u, 0, len(graph[u])-1])
    for _ in range(m):
        u = int(data[idx])-1; v = int(data[idx+1])-1; c = int(data[idx+2]); idx += 3
        add(u, v, c)
    s = int(data[idx])-1; t = int(data[idx+1])-1
    def bfs():
        level = [-1]*n; level[s] = 0; q = deque([s])
        while q:
            u = q.popleft()
            for e in graph[u]:
                if e[1] > 0 and level[e[0]] < 0:
                    level[e[0]] = level[u]+1; q.append(e[0])
        return level
    def dfs(u, f, level, it):
        if u == t: return f
        while it[u] < len(graph[u]):
            e = graph[u][it[u]]
            v = e[0]
            if e[1] > 0 and level[v] == level[u]+1:
                d = dfs(v, min(f, e[1]), level, it)
                if d > 0:
                    e[1] -= d; graph[v][e[2]][1] += d; return d
            it[u] += 1
        return 0
    flow = 0; INF = float('inf')
    while True:
        level = bfs()
        if level[t] < 0: break
        it = [0]*n
        while True:
            f = dfs(s, INF, level, it)
            if f == 0: break
            flow += f
    print(flow)
main()
""",
    "EX_GR_BIPMATCH": r"""import sys
def main():
    sys.setrecursionlimit(300000)
    data = sys.stdin.buffer.read().split()
    L = int(data[0]); R = int(data[1]); m = int(data[2]); idx = 3
    adj = [[] for _ in range(L)]
    for _ in range(m):
        u = int(data[idx])-1; v = int(data[idx+1])-1; idx += 2
        adj[u].append(v)
    matchR = [-1]*R
    def try_kuhn(u, vis):
        for v in adj[u]:
            if not vis[v]:
                vis[v] = True
                if matchR[v] == -1 or try_kuhn(matchR[v], vis):
                    matchR[v] = u; return True
        return False
    res = 0
    for u in range(L):
        vis = [False]*R
        if try_kuhn(u, vis): res += 1
    print(res)
main()
""",
    "EX_GR_MINVC": r"""import sys
def main():
    sys.setrecursionlimit(300000)
    data = sys.stdin.buffer.read().split()
    L = int(data[0]); R = int(data[1]); m = int(data[2]); idx = 3
    adj = [[] for _ in range(L)]
    for _ in range(m):
        u = int(data[idx])-1; v = int(data[idx+1])-1; idx += 2
        adj[u].append(v)
    matchR = [-1]*R
    def try_kuhn(u, vis):
        for v in adj[u]:
            if not vis[v]:
                vis[v] = True
                if matchR[v] == -1 or try_kuhn(matchR[v], vis):
                    matchR[v] = u; return True
        return False
    res = 0
    for u in range(L):
        vis = [False]*R
        if try_kuhn(u, vis): res += 1
    print(res)
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
    print(f"Chapitre 6 - Graphes : OK ({state}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
