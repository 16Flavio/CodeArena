"""Build a standalone HTML page that loads each widget in its own
sandboxed iframe - same setup as ``CustomWidget.jsx`` in the app
(common style preamble + outer chrome wrapper).

Output: scripts/seed_widgets/test-widgets.html

Usage:
    python scripts/seed_widgets/build_test_page.py
    # then open scripts/seed_widgets/test-widgets.html in your browser.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE / "templates"
OUT = HERE / "test-widgets.html"

CASES = [
    {"name": "viz-big-o",       "params": {},                                "title": "Comparaison des courbes de complexité"},
    {"name": "viz-hash-table",  "params": {"keys": "5,12,19,7,42,26,33"},     "title": "Table de hachage avec chaînage"},
    {"name": "viz-bst",         "params": {"keys": "50,30,70,20,40,60,80"},   "title": "Arbre binaire de recherche (BST)"},
    {"name": "viz-heap",        "params": {"data": "5,12,3,8,17,9,21"},       "title": "Tas binaire (max-heap)"},
    {"name": "viz-partition",   "params": {"data": "3,7,1,8,4,2,5"},          "title": "Partition de Lomuto pas à pas"},
    {"name": "viz-quicksort",   "params": {"data": "8,3,5,1,9,2,7,4,6"},      "title": "Tri rapide complet (vue d'ensemble)"},
    {"name": "viz-cross-product",    "params": {},                            "title": "Produit vectoriel & orientation"},
    {"name": "viz-segment-intersect","params": {},                            "title": "Intersection de segments"},
    {"name": "viz-convex-hull",      "params": {"points": "1,1;3,8;7,2;9,9;5,5;2,6;8,4;4,3;6,7;0,4;9,5;2,1"}, "title": "Enveloppe convexe (monotone chain)"},
    {"name": "viz-sweep-line",       "params": {"points": "0,3;1,7;2,2;3,9;4,4;5,6;6,1;7,8;8,3;9,5;10,2;11,7"}, "title": "Balayage : paire la plus proche"},
    {"name": "viz-binary-search",    "params": {"data": "1,3,4,7,9,11,15,20,25", "target": "11"}, "title": "Recherche dichotomique (lower_bound)"},
    {"name": "viz-two-pointers",     "params": {"data": "1,3,5,8,11,14,18", "target": "16"},       "title": "Two pointers : somme cible"},
    {"name": "viz-sliding-window",   "params": {"data": "2,3,1,2,4,3", "s": "7"},                  "title": "Fenetre glissante : somme >= S"},
    {"name": "viz-greedy-intervals", "params": {"intervals": "1,4;3,5;0,6;5,7;3,8;5,9;6,10;8,11;8,12;2,13"}, "title": "Glouton : selection d'activites"},
    {"name": "viz-dp-table",         "params": {"data": "3,1,8,2,5,9,4,7,6"},                       "title": "DP : plus longue sous-suite croissante"},
    {"name": "viz-backtracking",     "params": {"n": "6"},                                          "title": "Backtracking : N-reines"},
]

# Mirror of the CSS preamble + icon helper injected by CustomWidget.jsx
# so the local preview matches production exactly.
COMMON_STYLE = """
html, body { margin: 0; padding: 0; height: 100%; box-sizing: border-box; }
*, *::before, *::after { box-sizing: inherit; }
body { font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
       color: #18181b; background: transparent; padding: 14px 16px; font-size: 13px; }
.stage { width: 100%; }
.controls {
  display: flex; align-items: center; justify-content: center;
  gap: 8px; margin-top: 14px; flex-wrap: wrap;
}
.controls > .group { display: inline-flex; align-items: center; gap: 6px; }
.btn-icon, .btn-icon-primary, .btn-icon-secondary {
  display: inline-flex; align-items: center; justify-content: center;
  width: 32px; height: 32px; padding: 0; border: 0; border-radius: 8px;
  cursor: pointer; line-height: 1;
  transition: background-color 0.18s, color 0.18s, opacity 0.18s;
}
.btn-icon-primary   { background: #3a6690; color: #fff; }
.btn-icon-primary:hover:not(:disabled)   { background: #325575; }
.btn-icon-secondary { background: #e4e4e7; color: #3f3f46; }
.btn-icon-secondary:hover:not(:disabled) { background: #d4d4d8; }
.btn-icon-primary:disabled, .btn-icon-secondary:disabled { opacity: 0.5; cursor: default; }
.btn-icon-primary svg, .btn-icon-secondary svg { width: 16px; height: 16px; display: block; }
.form-input, input[type="number"], input[type="text"], input[type="range"] {
  padding: 5px 8px; border: 1px solid #d4d4d8; border-radius: 6px;
  background: #fff; color: #18181b; font: inherit; height: 32px;
}
input[type="range"] { padding: 0; min-width: 110px; height: 32px; background: transparent; border: 0; }
.form-input:focus, input[type="number"]:focus, input[type="text"]:focus {
  outline: 2px solid #9cbbd6; outline-offset: -1px;
}
label.field { display: inline-flex; align-items: center; gap: 6px;
              font-size: 12px; color: #52525b; }
label.field input[type="number"], label.field input[type="text"] { width: 80px; }
.meta-row { display: flex; gap: 14px; flex-wrap: wrap; font-size: 12px;
            color: #71717a; margin-top: 10px; justify-content: center; }
.meta-row b { color: #18181b; font-weight: 600; }
.info-line { font-family: ui-monospace, "SF Mono", Menlo, monospace;
             font-size: 12px; color: #325575; min-height: 16px;
             text-align: center; margin-top: 10px; }
@media (prefers-color-scheme: dark) {
  body { color: #e4e4e7; }
  .btn-icon-secondary { background: #3f3f46; color: #e4e4e7; }
  .btn-icon-secondary:hover:not(:disabled) { background: #52525b; }
  .form-input, input[type="number"], input[type="text"] {
    background: #27272a; border-color: #52525b; color: #e4e4e7;
  }
  label.field { color: #a1a1aa; }
  .meta-row { color: #a1a1aa; }
  .meta-row b { color: #e4e4e7; }
  .info-line { color: #9cbbd6; }
}
"""

ICON_HELPER = """
window.__icons = {
  play:   '<polygon points="6 3 20 12 6 21 6 3"/>',
  pause:  '<rect width="4" height="16" x="6" y="4"/><rect width="4" height="16" x="14" y="4"/>',
  step:   '<path d="m6 17 5-5-5-5"/><path d="m13 17 5-5-5-5"/>',
  reset:  '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>',
  plus:   '<path d="M5 12h14"/><path d="M12 5v14"/>',
  minus:  '<path d="M5 12h14"/>',
  load:   '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>'
};
window.__svg = function (name) {
  return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    + (window.__icons[name] || '') + '</svg>';
};
"""


def build_iframe_srcdoc(template: str, params: dict) -> str:
    return (
        '<!DOCTYPE html><html lang="fr"><head>'
        '<meta charset="utf-8" />'
        f'<style>{COMMON_STYLE}</style>'
        f'<script>{ICON_HELPER}</script>'
        '</head><body>'
        f'<script>window.__params = {json.dumps(params)};</script>'
        f'\n{template}'
        '</body></html>'
    )


def main():
    blocks_html = []
    raw_html = []
    for i, case in enumerate(CASES):
        tmpl = (TEMPLATES / (case["name"] + ".html")).read_text(encoding="utf-8")
        srcdoc = build_iframe_srcdoc(tmpl, case["params"])
        blocks_html.append(
            '<div class="widget-card">'
            f'  <div class="widget-card-head">{case["title"]}</div>'
            f'  <iframe id="iframe-{i}" sandbox="allow-scripts"></iframe>'
            '</div>'
            f'<p class="meta">'
            f'  <code>:::{case["name"]}'
            + (
                ('{' + ' '.join(f'{k}="{v}"' for k, v in case["params"].items()) + '}')
                if case["params"] else ''
            )
            + '</code>'
            '</p>'
        )
        # textarea carries the full HTML for assignment via JS - avoids
        # escaping the iframe's srcdoc attribute by hand.
        raw_html.append(
            f'<textarea id="src-{i}" hidden>{srcdoc.replace("&", "&amp;").replace("<", "&lt;")}</textarea>'
        )

    page = (
        '<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">'
        '<title>Test widgets en isolation</title>'
        '<style>'
        'body{font-family:system-ui,-apple-system,sans-serif;max-width:900px;'
        'margin:20px auto;padding:0 20px;color:#18181b;}'
        'h1{font-size:22px;}'
        '.widget-card{margin:24px 0;padding:16px;border-radius:8px;'
        'border:1px solid #e4e4e7;background:#fff;'
        'box-shadow:0 1px 2px 0 rgba(0,0,0,0.05);}'
        '.widget-card-head{font-size:11px;text-transform:uppercase;'
        'letter-spacing:0.05em;font-weight:600;color:#3a6690;margin-bottom:10px;}'
        '.widget-card iframe{width:100%;height:460px;border:0;'
        'border-radius:8px;background:transparent;display:block;}'
        '.meta{margin:6px 0 0;font-size:12px;color:#71717a;}'
        'code{background:#e4e4e7;padding:2px 6px;border-radius:4px;font-size:12px;}'
        'p.note{color:#71717a;font-size:13px;}'
        '@media (prefers-color-scheme: dark){'
        'body{background:#09090b;color:#e4e4e7;}'
        '.widget-card{background:#18181b;border-color:#27272a;}'
        '.widget-card-head{color:#9cbbd6;}'
        'code{background:#27272a;color:#e4e4e7;}'
        '}'
        '</style></head><body>'
        '<h1>Test widgets - iframe sandboxé identique à l\'app</h1>'
        '<p class="note">Cette page reproduit le wrapper extérieur (carte + titre accent) et '
        'le préambule CSS commun de <code>CustomWidget.jsx</code>. Si un widget s\'affiche '
        'correctement ici, son code est OK. Sinon, clique-droit dans l\'iframe → Inspect → '
        'Console pour voir l\'erreur exacte.</p>'
        + '\n'.join(blocks_html)
        + '\n'.join(raw_html)
        + '<script>'
        + 'for (var i = 0; i < ' + str(len(CASES)) + '; i++) {'
        + '  var src = document.getElementById("src-" + i);'
        + '  var iframe = document.getElementById("iframe-" + i);'
        + '  iframe.srcdoc = src.value;'
        + '}'
        + '</script>'
        '</body></html>'
    )

    OUT.write_text(page, encoding="utf-8")
    print(f"  [ok] wrote {OUT}")
    print(f"  [info] open in your browser, no server needed.")


if __name__ == "__main__":
    main()
