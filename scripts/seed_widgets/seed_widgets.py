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
