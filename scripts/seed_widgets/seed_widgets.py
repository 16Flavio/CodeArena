"""Seed the LearningWidget DB table with the custom widgets we want
referenced from the chapter lessons.

Each widget body lives in ``templates/<name>.html`` next to this
script. Idempotent: upserts by ``name``.

Usage:
    python scripts/seed_widgets/seed_widgets.py
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
TEMPLATES = HERE / "templates"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


WIDGETS = [
    {
        "name": "viz-big-o",
        "title_fr": "Comparaison des courbes de complexité",
        "title_en": "Big-O growth curves",
        "description_fr": (
            "Trace les fonctions $1$, $\\log n$, $n$, $n \\log n$, $n^2$ et "
            "$2^n$ sur le même graphique. Curseur pour ajuster $n_{\\max}$, "
            "interrupteur pour passer en échelle log."
        ),
        "description_en": (
            "Plots $1$, $\\log n$, $n$, $n \\log n$, $n^2$, $2^n$ on the same "
            "axes. Slider to tune $n_{\\max}$, toggle for log Y-axis."
        ),
        "template_file": "viz-big-o.html",
        "params_schema": [],
        "example_params": {},
    },
    {
        "name": "viz-hash-table",
        "title_fr": "Table de hachage avec chaînage",
        "title_en": "Hash table with chaining",
        "description_fr": (
            "Visualise une table de hachage à $m$ buckets avec résolution par "
            "chaînage. Insère interactivement des clés ; les collisions sont "
            "mises en évidence en rouge."
        ),
        "description_en": (
            "Visualises an $m$-bucket hash table with chaining. Interactively "
            "insert keys; collisions are highlighted in red."
        ),
        "template_file": "viz-hash-table.html",
        "params_schema": [
            {"name": "keys", "description": "clés initiales à insérer (CSV)", "example": "5,12,19,7,42"},
            {"name": "m",    "description": "taille initiale (override par UI)", "example": "7"},
        ],
        "example_params": {"keys": "5,12,19,7,42"},
    },
    {
        "name": "viz-bst",
        "title_fr": "Arbre binaire de recherche (BST)",
        "title_en": "Binary search tree (BST)",
        "description_fr": (
            "Construit un BST naïf à partir d'une suite de clés et l'affiche. "
            "Insère interactivement de nouvelles clés et observe la hauteur "
            "(qui peut dégénérer en chaîne - c'est le pire cas dont parle la "
            "leçon)."
        ),
        "description_en": (
            "Builds a plain BST from a sequence of keys and renders it. "
            "Interactively insert new keys and observe the height (which can "
            "degenerate to a chain - the worst case the lesson warns about)."
        ),
        "template_file": "viz-bst.html",
        "params_schema": [
            {"name": "keys", "description": "clés initiales à insérer (CSV)", "example": "50,30,70,20,40,60,80"},
        ],
        "example_params": {"keys": "50,30,70,20,40,60,80"},
    },
    {
        "name": "viz-heap",
        "title_fr": "Tas binaire (max-heap)",
        "title_en": "Binary heap (max-heap)",
        "description_fr": (
            "Visualise un max-heap stocké en tableau implicite. Boutons "
            "`insert` (sift-up) et `extract-max` (sift-down) pour observer "
            "comment le tas se rééquilibre."
        ),
        "description_en": (
            "Visualises a max-heap stored as an implicit array. `insert` "
            "(sift-up) and `extract-max` (sift-down) buttons to watch the heap "
            "rebalance."
        ),
        "template_file": "viz-heap.html",
        "params_schema": [
            {"name": "data", "description": "valeurs initiales à insérer (CSV)", "example": "5,12,3,8,17,9"},
        ],
        "example_params": {"data": "5,12,3,8,17,9"},
    },
    {
        "name": "viz-quicksort",
        "title_fr": "Tri rapide complet (vue d'ensemble)",
        "title_en": "Full quicksort (bird's-eye view)",
        "description_fr": (
            "Anime un tri rapide **complet** sur un tableau : chaque appel "
            "récursif choisit un pivot (rouge), partitionne autour, puis "
            "récurse sur les deux sous-tableaux. Affiche la profondeur de "
            "pile, le nombre de comparaisons et de swaps cumulés. "
            "Complémentaire de `viz-partition` qui zoome sur **une seule** "
            "partition Lomuto pas à pas."
        ),
        "description_en": (
            "Animates a **full** quicksort run on an array: every recursive "
            "call picks a pivot (red), partitions around it, then recurses "
            "into both subarrays. Shows recursion depth and cumulative "
            "comparison/swap counts. Complementary to `viz-partition` which "
            "zooms onto a **single** Lomuto partition step-by-step."
        ),
        "template_file": "viz-quicksort.html",
        "params_schema": [
            {"name": "data", "description": "tableau à trier (CSV)", "example": "8,3,5,1,9,2,7,4,6"},
        ],
        "example_params": {"data": "8,3,5,1,9,2,7,4,6"},
    },
    {
        "name": "viz-partition",
        "title_fr": "Partition de Lomuto pas à pas",
        "title_en": "Lomuto partition step-by-step",
        "description_fr": (
            "Anime la partition de Lomuto avec pivot = dernier élément. "
            "Affiche les pointeurs `i` et `j`, met en couleur les éléments "
            "$\\le$ pivot (vert) et $>$ pivot (gris). Bouton `step` pour "
            "avancer une itération à la fois, ou `run` pour tout dérouler."
        ),
        "description_en": (
            "Animates Lomuto partition with pivot = last element. Shows the "
            "`i` and `j` pointers, colours $\\le$-pivot elements (green) and "
            "$>$-pivot elements (grey). `step` button to advance one "
            "iteration; `run` to play to completion."
        ),
        "template_file": "viz-partition.html",
        "params_schema": [
            {"name": "data", "description": "tableau initial (CSV ou JSON)", "example": "3,7,1,8,4,2,5"},
        ],
        "example_params": {"data": "3,7,1,8,4,2,5"},
    },
    {
        "name": "viz-cross-product",
        "title_fr": "Produit vectoriel & orientation",
        "title_en": "Cross product & orientation",
        "description_fr": (
            "Plan cartesien avec un segment oriente $A \\to B$ et un point $C$ "
            "a glisser. Affiche en direct le signe du produit vectoriel "
            "`cross(A, B, C)` et l'orientation : $C$ a gauche (antihoraire), a "
            "droite (horaire) ou aligne. Coordonnees entieres, calcul exact."
        ),
        "description_en": (
            "Cartesian plane with a directed segment $A \\to B$ and a draggable "
            "point $C$. Live-updates the sign of `cross(A, B, C)` and the "
            "orientation: $C$ to the left (counter-clockwise), right (clockwise) "
            "or collinear. Integer coordinates, exact arithmetic."
        ),
        "template_file": "viz-cross-product.html",
        "params_schema": [],
        "example_params": {},
    },
    {
        "name": "viz-segment-intersect",
        "title_fr": "Intersection de segments",
        "title_en": "Segment intersection",
        "description_fr": (
            "Deux segments $[A, B]$ et $[C, D]$ a extremites deplacables. "
            "Affiche les quatre orientations $d_1, d_2, d_3, d_4$ et le verdict "
            "de croisement, exactement comme le predicat `seg_intersect` de la "
            "lecon (signes opposes de chaque cote, cas colineaires compris)."
        ),
        "description_en": (
            "Two segments $[A, B]$ and $[C, D]$ with draggable endpoints. Shows "
            "the four orientations $d_1, d_2, d_3, d_4$ and the intersection "
            "verdict, exactly like the lesson's `seg_intersect` predicate "
            "(opposite signs on each side, collinear cases included)."
        ),
        "template_file": "viz-segment-intersect.html",
        "params_schema": [],
        "example_params": {},
    },
    {
        "name": "viz-convex-hull",
        "title_fr": "Enveloppe convexe (monotone chain)",
        "title_en": "Convex hull (monotone chain)",
        "description_fr": (
            "Anime l'algorithme d'Andrew pas a pas : tri des points, puis "
            "construction des chaines inferieure et superieure par une pile. Le "
            "test `cross <= 0` depile les tours a droite (croix rouge). Boutons "
            "`step` / `run`. Points passes en parametre (paires `x,y` separees "
            "par `;`)."
        ),
        "description_en": (
            "Animates Andrew's algorithm step-by-step: sort the points, then "
            "build the lower and upper chains with a stack. The `cross <= 0` "
            "test pops right turns (red cross). `step` / `run` buttons. Points "
            "passed as a parameter (`x,y` pairs separated by `;`)."
        ),
        "template_file": "viz-convex-hull.html",
        "params_schema": [
            {"name": "points", "description": "nuage de points, paires x,y separees par ;",
             "example": "1,1;3,8;7,2;9,9;5,5;2,6;8,4;4,3;6,7;0,4;9,5;2,1"},
        ],
        "example_params": {"points": "1,1;3,8;7,2;9,9;5,5;2,6;8,4;4,3;6,7;0,4;9,5;2,1"},
    },
    {
        "name": "viz-sweep-line",
        "title_fr": "Balayage : paire la plus proche",
        "title_en": "Sweep line: closest pair",
        "description_fr": (
            "Visualise le balayage pour la paire la plus proche : une ligne "
            "verticale glisse de gauche a droite, une bande active de largeur "
            "$d$ (meilleure distance courante) suit, et seuls les voisins dans "
            "la bande sont compares. La meilleure paire est reliee en vert. "
            "Boutons `step` / `run`."
        ),
        "description_en": (
            "Visualises the closest-pair sweep: a vertical line sweeps left to "
            "right, an active band of width $d$ (current best distance) trails "
            "it, and only neighbours inside the band are compared. The best pair "
            "is joined in green. `step` / `run` buttons."
        ),
        "template_file": "viz-sweep-line.html",
        "params_schema": [
            {"name": "points", "description": "nuage de points, paires x,y separees par ;",
             "example": "0,3;1,7;2,2;3,9;4,4;5,6;6,1;7,8;8,3;9,5;10,2;11,7"},
        ],
        "example_params": {"points": "0,3;1,7;2,2;3,9;4,4;5,6;6,1;7,8;8,3;9,5;10,2;11,7"},
    },
    {
        "name": "viz-binary-search",
        "title_fr": "Recherche dichotomique (lower_bound)",
        "title_en": "Binary search (lower_bound)",
        "description_fr": (
            "Deroule `lower_bound` pas a pas sur un tableau trie, en intervalle "
            "**semi-ouvert** $[lo, hi)$. Met en couleur la fenetre active, le "
            "milieu `mid`, et les zones deja exclues (prouvees $< x$ a gauche, "
            "$\\ge x$ a droite). Parametres `data` (tableau) et `target` (cible)."
        ),
        "description_en": (
            "Steps through `lower_bound` on a sorted array using a "
            "**half-open** interval $[lo, hi)$. Colours the active window, the "
            "`mid` midpoint, and the already-excluded zones (proven $< x$ on the "
            "left, $\\ge x$ on the right). Params `data` (array) and `target`."
        ),
        "template_file": "viz-binary-search.html",
        "params_schema": [
            {"name": "data", "description": "tableau trie (CSV)", "example": "1,3,4,7,9,11,15,20,25"},
            {"name": "target", "description": "valeur cherchee", "example": "11"},
        ],
        "example_params": {"data": "1,3,4,7,9,11,15,20,25", "target": "11"},
    },
    {
        "name": "viz-two-pointers",
        "title_fr": "Two pointers : somme cible",
        "title_en": "Two pointers: target sum",
        "description_fr": (
            "Anime `two_sum_sorted` : deux pointeurs $i$ (gauche) et $j$ "
            "(droite) sur un tableau trie convergent vers une cible $T$. Si la "
            "somme est trop petite `i++`, trop grande `j--` ; la paire trouvee "
            "est mise en vert. Parametres `data` et `target`."
        ),
        "description_en": (
            "Animates `two_sum_sorted`: two pointers $i$ (left) and $j$ (right) "
            "on a sorted array converge on a target $T$. If the sum is too small "
            "`i++`, too large `j--`; the found pair turns green. Params `data` "
            "and `target`."
        ),
        "template_file": "viz-two-pointers.html",
        "params_schema": [
            {"name": "data", "description": "tableau trie (CSV)", "example": "1,3,5,8,11,14,18"},
            {"name": "target", "description": "somme cible", "example": "16"},
        ],
        "example_params": {"data": "1,3,5,8,11,14,18", "target": "16"},
    },
    {
        "name": "viz-sliding-window",
        "title_fr": "Fenetre glissante : somme >= S",
        "title_en": "Sliding window: sum >= S",
        "description_fr": (
            "Cherche la plus **petite** sous-tableau contigu de somme $\\ge S$. "
            "La fenetre $[i, j]$ s'etend a droite (`j`), puis se contracte a "
            "gauche (`i`) tant qu'elle reste valide. Cout $O(n)$ amorti : aucun "
            "pointeur ne recule. Parametres `data` et `s`."
        ),
        "description_en": (
            "Finds the **smallest** contiguous subarray with sum $\\ge S$. The "
            "window $[i, j]$ grows on the right (`j`), then contracts on the "
            "left (`i`) while it stays valid. Amortised $O(n)$: neither pointer "
            "moves backward. Params `data` and `s`."
        ),
        "template_file": "viz-sliding-window.html",
        "params_schema": [
            {"name": "data", "description": "tableau d'entiers positifs (CSV)", "example": "2,3,1,2,4,3"},
            {"name": "s", "description": "seuil de somme", "example": "7"},
        ],
        "example_params": {"data": "2,3,1,2,4,3", "s": "7"},
    },
    {
        "name": "viz-greedy-intervals",
        "title_fr": "Glouton : selection d'activites",
        "title_en": "Greedy: activity selection",
        "description_fr": (
            "Anime la selection d'activites : les intervalles sont tries par "
            "**fin croissante**, puis on prend gloutonnement chaque activite "
            "compatible ($s \\ge$ fin courante). Choisis en vert, rejetes "
            "(chevauchant) en gris, ligne de fin courante en pointille. "
            "Parametre `intervals` (paires `s,e` separees par `;`)."
        ),
        "description_en": (
            "Animates activity selection: intervals are sorted by **earliest "
            "finish**, then each compatible activity ($s \\ge$ current end) is "
            "greedily taken. Chosen in green, rejected (overlapping) in grey, "
            "current-end line dashed. Param `intervals` (`s,e` pairs separated "
            "by `;`)."
        ),
        "template_file": "viz-greedy-intervals.html",
        "params_schema": [
            {"name": "intervals", "description": "intervalles, paires s,e separees par ;",
             "example": "1,4;3,5;0,6;5,7;3,8;5,9;6,10;8,11;8,12;2,13"},
        ],
        "example_params": {"intervals": "1,4;3,5;0,6;5,7;3,8;5,9;6,10;8,11;8,12;2,13"},
    },
    {
        "name": "viz-dp-table",
        "title_fr": "DP : plus longue sous-suite croissante",
        "title_en": "DP: longest increasing subsequence",
        "description_fr": (
            "Remplit la table DP de la **LIS** pas a pas : $L(i) = 1 + "
            "\\max\\{L(j) : j < i,\\ a_j < a_i\\}$. Case courante en orange, "
            "predecesseur choisi en bleu ; a la fin, la sous-suite reconstruite "
            "s'illumine en vert. Parametre `data` (la suite)."
        ),
        "description_en": (
            "Fills the **LIS** DP table step-by-step: $L(i) = 1 + \\max\\{L(j) : "
            "j < i,\\ a_j < a_i\\}$. Current cell orange, chosen predecessor "
            "blue; at the end the reconstructed subsequence lights up green. "
            "Param `data` (the sequence)."
        ),
        "template_file": "viz-dp-table.html",
        "params_schema": [
            {"name": "data", "description": "suite d'entiers (CSV)", "example": "3,1,8,2,5,9,4,7,6"},
        ],
        "example_params": {"data": "3,1,8,2,5,9,4,7,6"},
    },
    {
        "name": "viz-backtracking",
        "title_fr": "Backtracking : N-reines",
        "title_en": "Backtracking: N-queens",
        "description_fr": (
            "Explore l'arbre de recherche des **N-reines** : placement ligne par "
            "ligne, elagage O(1) sur colonnes et diagonales (croix rouge), "
            "backtrack quand une ligne est bloquee. Compte les solutions. "
            "Parametre `n` (taille de l'echiquier, 4 a 8)."
        ),
        "description_en": (
            "Explores the **N-queens** search tree: row-by-row placement, O(1) "
            "pruning on columns and diagonals (red cross), backtrack when a row "
            "is blocked. Counts the solutions. Param `n` (board size, 4 to 8)."
        ),
        "template_file": "viz-backtracking.html",
        "params_schema": [
            {"name": "n", "description": "taille de l'echiquier (4 a 8)", "example": "6"},
        ],
        "example_params": {"n": "6"},
    },
    {
        "name": "viz-graph-traversal",
        "title_fr": "Parcours de graphe : BFS / DFS",
        "title_en": "Graph traversal: BFS / DFS",
        "description_fr": (
            "Compare le parcours en largeur (BFS, file) et en profondeur (DFS, "
            "pile) sur un meme graphe. Bascule le mode et la source ; les "
            "numeros `#k` donnent l'ordre de decouverte. BFS s'etend par "
            "couches, DFS plonge le plus loin possible."
        ),
        "description_en": (
            "Compares breadth-first (BFS, queue) and depth-first (DFS, stack) "
            "traversal on the same graph. Toggle the mode and the source; the "
            "`#k` labels give the discovery order. BFS spreads in layers, DFS "
            "plunges as deep as possible."
        ),
        "template_file": "viz-graph-traversal.html",
        "params_schema": [
            {"name": "mode", "description": "bfs ou dfs", "example": "bfs"},
            {"name": "source", "description": "sommet de depart (0 a 7)", "example": "0"},
        ],
        "example_params": {"mode": "bfs", "source": "0"},
    },
    {
        "name": "viz-dijkstra",
        "title_fr": "Dijkstra : plus courts chemins",
        "title_en": "Dijkstra: shortest paths",
        "description_fr": (
            "Deroule l'algorithme de Dijkstra sur un graphe pondere positif. A "
            "chaque etape le sommet non fige de plus petite distance est extrait "
            "(fige, definitif), puis ses aretes sont relachees. Les etiquettes "
            "montrent la distance provisoire de chaque sommet."
        ),
        "description_en": (
            "Runs Dijkstra on a non-negative weighted graph. At each step the "
            "unsettled vertex with the smallest distance is extracted (settled, "
            "final), then its edges are relaxed. The labels show each vertex's "
            "tentative distance."
        ),
        "template_file": "viz-dijkstra.html",
        "params_schema": [
            {"name": "source", "description": "sommet source (0 a 7)", "example": "0"},
        ],
        "example_params": {"source": "0"},
    },
    {
        "name": "viz-mst-kruskal",
        "title_fr": "Kruskal : arbre couvrant minimal",
        "title_en": "Kruskal: minimum spanning tree",
        "description_fr": (
            "Construit un MST par l'algorithme de Kruskal : les aretes sont "
            "triees par poids croissant ; chaque arete est retenue (vert) si "
            "elle relie deux composantes distinctes, ou rejetee (rouge) si elle "
            "formerait un cycle (test par Union-Find). Les couleurs des sommets "
            "montrent les composantes fusionner."
        ),
        "description_en": (
            "Builds an MST with Kruskal's algorithm: edges are sorted by "
            "increasing weight; each edge is kept (green) if it joins two "
            "distinct components, or rejected (red) if it would form a cycle "
            "(tested with Union-Find). The vertex colours show the components "
            "merging."
        ),
        "template_file": "viz-mst-kruskal.html",
        "params_schema": [],
        "example_params": {},
    },
    {
        "name": "viz-sieve",
        "title_fr": "Crible d'Eratosthene",
        "title_en": "Sieve of Eratosthenes",
        "description_fr": (
            "Deroule le crible d'Eratosthene sur une grille de $2$ a $n$ : "
            "chaque prochain nombre non marque est premier (vert), puis ses "
            "multiples a partir de $p^2$ sont barres (gris/rouge)."
        ),
        "description_en": (
            "Steps through the sieve of Eratosthenes on a grid from $2$ to $n$: "
            "each next unmarked number is prime (green), then its multiples from "
            "$p^2$ on are crossed out (grey/red)."
        ),
        "template_file": "viz-sieve.html",
        "params_schema": [
            {"name": "n", "description": "borne superieure de la grille (clampe 20..120)", "example": "60"},
        ],
        "example_params": {"n": "60"},
    },
    {
        "name": "viz-fast-exp",
        "title_fr": "Exponentiation modulaire rapide",
        "title_en": "Fast modular exponentiation",
        "description_fr": (
            "Calcule $a^b \\bmod m$ bit par bit (du poids faible au poids fort) : "
            "a chaque bit on carre la base et, si le bit vaut $1$, on multiplie "
            "le resultat. Table d'etat et bits mis en evidence."
        ),
        "description_en": (
            "Computes $a^b \\bmod m$ bit by bit (LSB to MSB): at each bit the base "
            "is squared and, if the bit is $1$, it is multiplied into the result. "
            "State table with highlighted bits."
        ),
        "template_file": "viz-fast-exp.html",
        "params_schema": [
            {"name": "a", "description": "base", "example": "3"},
            {"name": "b", "description": "exposant", "example": "13"},
            {"name": "m", "description": "modulo (>= 2)", "example": "1000"},
        ],
        "example_params": {"a": "3", "b": "13", "m": "1000"},
    },
    {
        "name": "viz-pascal",
        "title_fr": "Triangle de Pascal",
        "title_en": "Pascal's triangle",
        "description_fr": (
            "Construit le triangle des coefficients binomiaux $\\binom{n}{k}$ "
            "case par case via $C(n,k) = C(n-1,k-1) + C(n-1,k)$, en mettant en "
            "evidence les deux parents. Cible optionnelle via `hn`/`hk`."
        ),
        "description_en": (
            "Builds the triangle of binomial coefficients $\\binom{n}{k}$ cell by "
            "cell via $C(n,k) = C(n-1,k-1) + C(n-1,k)$, highlighting the two "
            "parents. Optional target via `hn`/`hk`."
        ),
        "template_file": "viz-pascal.html",
        "params_schema": [
            {"name": "n",  "description": "nombre de lignes (clampe 3..12)", "example": "8"},
            {"name": "hn", "description": "ligne cible a mettre en evidence (optionnel)", "example": "8"},
            {"name": "hk", "description": "colonne cible a mettre en evidence (optionnel)", "example": "4"},
        ],
        "example_params": {"n": "8", "hn": "8", "hk": "4"},
    },
    {
        "name": "viz-union-find",
        "title_fr": "Union-Find (DSU) : foret & compression",
        "title_en": "Union-Find (DSU): forest & compression",
        "description_fr": (
            "Deroule une suite d'`union(a, b)` par taille sur une foret d'arbres "
            "(les racines en bleu portent leur taille), puis un `find(x)` avec "
            "**compression de chemin** qui rebranche le noeud le plus profond "
            "directement sur la racine. Boutons `step` / `run`. Parametres `n` et `ops`."
        ),
        "description_en": (
            "Steps through a sequence of `union(a, b)` by size over a forest of trees "
            "(blue roots carry their size), then a `find(x)` with **path compression** "
            "that rewires the deepest node straight onto its root. `step` / `run` "
            "buttons. Params `n` and `ops`."
        ),
        "template_file": "viz-union-find.html",
        "params_schema": [
            {"name": "n", "description": "nombre d'elements (2 a 16)", "example": "8"},
            {"name": "ops", "description": "unions a jouer, paires a-b separees par ;",
             "example": "0-1;2-3;1-3;4-5;5-6;3-6"},
        ],
        "example_params": {"n": "8", "ops": "0-1;2-3;1-3;4-5;5-6;3-6"},
    },
    {
        "name": "viz-segment-tree",
        "title_fr": "Arbre de segments (somme)",
        "title_en": "Segment tree (sum)",
        "description_fr": (
            "Construit un arbre de segments de sommes puis deroule une requete "
            "`somme[l, r]` : les noeuds entierement couverts (canoniques, verts) sont "
            "les $O(\\log n)$ noeuds visites, les disjoints sont ignores (rouge). "
            "Enchaine avec une mise a jour ponctuelle qui remonte le chemin "
            "feuille -> racine. Parametres `data`, `l`, `r`."
        ),
        "description_en": (
            "Builds a sum segment tree then steps through a `sum[l, r]` query: the "
            "fully-covered (canonical, green) nodes are the $O(\\log n)$ visited "
            "nodes, disjoint ones are pruned (red). Follows up with a point update "
            "walking the leaf-to-root path. Params `data`, `l`, `r`."
        ),
        "template_file": "viz-segment-tree.html",
        "params_schema": [
            {"name": "data", "description": "tableau d'entiers (CSV)", "example": "3,1,4,1,5,9,2,6"},
            {"name": "l", "description": "borne gauche de la requete", "example": "2"},
            {"name": "r", "description": "borne droite de la requete", "example": "5"},
        ],
        "example_params": {"data": "3,1,4,1,5,9,2,6", "l": "2", "r": "5"},
    },
    {
        "name": "viz-fenwick",
        "title_fr": "Arbre de Fenwick (BIT)",
        "title_en": "Fenwick tree (BIT)",
        "description_fr": (
            "Affiche le tableau `a[]` et le tableau `bit[]` (avec la plage couverte "
            "par chaque case), puis anime les sauts de bits depuis un meme indice "
            "`i` : `prefix(i)` descend par blocs (`i -= i & -i`) en cumulant la "
            "somme, `update(i)` remonte (`i += i & -i`). Le `lowbit` est affiche a "
            "chaque etape. Parametres `data` et `i`."
        ),
        "description_en": (
            "Shows the `a[]` array and the `bit[]` array (with the range each cell "
            "covers), then animates the bit jumps from the same index `i`: "
            "`prefix(i)` descends by blocks (`i -= i & -i`) accumulating the sum, "
            "`update(i)` climbs (`i += i & -i`). The `lowbit` is shown at each step. "
            "Params `data` and `i`."
        ),
        "template_file": "viz-fenwick.html",
        "params_schema": [
            {"name": "data", "description": "tableau d'entiers (CSV, 1-indexe a l'affichage)", "example": "3,1,4,1,5,9,2,6"},
            {"name": "i", "description": "indice de depart (1-indexe)", "example": "6"},
        ],
        "example_params": {"data": "3,1,4,1,5,9,2,6", "i": "6"},
    },
    {
        "name": "viz-trie",
        "title_fr": "Trie (arbre de prefixes)",
        "title_en": "Trie (prefix tree)",
        "description_fr": (
            "Insere un jeu de mots pour construire le trie (aretes etiquetees par "
            "caractere, noeuds de fin de mot cercles), puis recherche un mot `query` "
            "en descendant caractere par caractere : le chemin parcouru devient vert "
            "s'il existe, rouge des la premiere arete manquante. Boutons `step` / "
            "`run`. Parametres `words` et `query`."
        ),
        "description_en": (
            "Inserts a set of words to build the trie (edges labelled by character, "
            "end-of-word nodes ringed), then searches a `query` word descending "
            "character by character: the traced path turns green if it exists, red "
            "at the first missing edge. `step` / `run` buttons. Params `words` and "
            "`query`."
        ),
        "template_file": "viz-trie.html",
        "params_schema": [
            {"name": "words", "description": "mots a inserer (separes par des virgules)", "example": "car,card,cart,dog,do,dot"},
            {"name": "query", "description": "mot a rechercher", "example": "cart"},
        ],
        "example_params": {"words": "car,card,cart,dog,do,dot", "query": "cart"},
    },
    {
        "name": "viz-kmp",
        "title_fr": "KMP : fonction prefixe & recherche",
        "title_en": "KMP: prefix function & search",
        "description_fr": (
            "Deroule Knuth-Morris-Pratt en deux temps : construction de la table "
            "`pi` du motif, puis glissement du motif sur le texte en se servant de "
            "`pi` a chaque echec. Caracteres compares mis en couleur, decalage "
            "affiche, correspondances en vert. Parametres `text` et `pattern`."
        ),
        "description_en": (
            "Walks through Knuth-Morris-Pratt in two phases: building the pattern's "
            "`pi` table, then sliding the pattern over the text using `pi` on every "
            "mismatch. Compared characters are coloured, the shift is shown, matches "
            "turn green. Params `text` and `pattern`."
        ),
        "template_file": "viz-kmp.html",
        "params_schema": [
            {"name": "text", "description": "texte a fouiller", "example": "abxabcabcaby"},
            {"name": "pattern", "description": "motif recherche", "example": "abcaby"},
        ],
        "example_params": {"text": "abxabcabcaby", "pattern": "abcaby"},
    },
    {
        "name": "viz-z-array",
        "title_fr": "Z-function & boite [l, r]",
        "title_en": "Z-function & [l, r] box",
        "description_fr": (
            "Calcule la Z-function : $z[i]$ = plus long prefixe commun de $s$ et de "
            "$s[i:]$. Montre la boite $[l, r)$ la plus a droite, l'heritage du "
            "miroir puis l'extension naive, et remplit les valeurs $z$ de gauche a "
            "droite. Parametre `s`."
        ),
        "description_en": (
            "Computes the Z-function: $z[i]$ = longest common prefix of $s$ and "
            "$s[i:]$. Shows the rightmost $[l, r)$ box, the mirror inheritance then "
            "the naive extension, and fills the $z$ values left to right. Param `s`."
        ),
        "template_file": "viz-z-array.html",
        "params_schema": [
            {"name": "s", "description": "chaine a analyser", "example": "aabxaabxcaabxaabxay"},
        ],
        "example_params": {"s": "aabxaabxcaabxaabxay"},
    },
    {
        "name": "viz-rolling-hash",
        "title_fr": "Hachage glissant (Rabin-Karp)",
        "title_en": "Rolling hash (Rabin-Karp)",
        "description_fr": (
            "Fait glisser une fenetre de la taille du motif sur le texte et met a "
            "jour le hash polynomial en $O(1)$ (retire le caractere de tete, ajoute "
            "celui de queue). Compare le hash de la fenetre a celui du motif ; "
            "egalite verifiee en vert, collision en orange. Parametres `text`, "
            "`pattern` (et `base`, `mod`)."
        ),
        "description_en": (
            "Slides a pattern-length window over the text and updates the "
            "polynomial hash in $O(1)$ (drop the leading char, add the trailing "
            "one). Compares the window hash to the pattern hash; a verified match is "
            "green, a collision orange. Params `text`, `pattern` (and `base`, `mod`)."
        ),
        "template_file": "viz-rolling-hash.html",
        "params_schema": [
            {"name": "text", "description": "texte a fouiller", "example": "abracadabra"},
            {"name": "pattern", "description": "motif recherche", "example": "cada"},
            {"name": "base", "description": "base du polynome (optionnel)", "example": "31"},
            {"name": "mod", "description": "modulo (optionnel)", "example": "1000000007"},
        ],
        "example_params": {"text": "abracadabra", "pattern": "cada"},
    },
]


def _read_template(filename: str) -> str:
    path = TEMPLATES / filename
    if not path.exists():
        raise SystemExit(f"Missing template: {path}")
    return path.read_text(encoding="utf-8")


def upsert_widget(db, models, w: dict, *, publish: bool):
    template = _read_template(w["template_file"])
    existing = db.query(models.LearningWidget).filter(
        models.LearningWidget.name == w["name"]
    ).first()
    if existing:
        existing.title_fr = w["title_fr"]
        existing.title_en = w["title_en"]
        existing.description_fr = w["description_fr"]
        existing.description_en = w["description_en"]
        existing.html_template = template
        existing.params_schema = json.dumps(w["params_schema"])
        existing.example_params = json.dumps(w["example_params"])
        existing.is_published = bool(publish or existing.is_published)
        db.flush()
        return existing, False
    widget = models.LearningWidget(
        name=w["name"],
        title_fr=w["title_fr"],
        title_en=w["title_en"],
        description_fr=w["description_fr"],
        description_en=w["description_en"],
        html_template=template,
        params_schema=json.dumps(w["params_schema"]),
        example_params=json.dumps(w["example_params"]),
        is_published=publish,
        created_by=None,
    )
    db.add(widget)
    db.flush()
    return widget, True


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
        for w in WIDGETS:
            widget, created = upsert_widget(db, models, w, publish=publish)
            verb = "created" if created else "updated"
            size = len(widget.html_template)
            print(f"  [ok]widget {widget.name!r} {verb} (id={widget.id}, "
                  f"{size} bytes HTML)")
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    state = "publies" if publish else "en brouillon"
    print()
    print(f"Widgets : OK ({state}). {len(WIDGETS)} widgets disponibles via "
          f"`:::nom-du-widget{{params}}` dans les lecons.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
