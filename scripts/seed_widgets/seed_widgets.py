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
