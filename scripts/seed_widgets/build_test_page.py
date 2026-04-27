"""Build a standalone HTML page that loads each widget in its own
sandboxed iframe — same setup as ``CustomWidget.jsx`` in the app
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
]

# Mirror of the CSS preamble injected by CustomWidget.jsx so the local
# preview matches what users see in production.
COMMON_STYLE = """
html, body { margin: 0; padding: 0; height: 100%; box-sizing: border-box; }
*, *::before, *::after { box-sizing: inherit; }
body { font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
       color: #0f172a; background: transparent; padding: 14px 16px; font-size: 13px; }
.btn-primary, .btn-secondary {
  padding: 6px 12px; border: 0; border-radius: 8px; font-size: 13px;
  font-family: inherit; cursor: pointer; line-height: 1.2;
  transition: background-color 0.18s, color 0.18s, opacity 0.18s;
}
.btn-primary { background: #8b5cf6; color: #fff; }
.btn-primary:hover:not(:disabled)   { background: #7c3aed; }
.btn-secondary { background: #e2e8f0; color: #334155; }
.btn-secondary:hover:not(:disabled) { background: #cbd5e1; }
.btn-primary:disabled, .btn-secondary:disabled { opacity: 0.5; cursor: default; }
.form-input, input[type="number"], input[type="text"] {
  padding: 4px 8px; border: 1px solid #cbd5e1; border-radius: 6px;
  background: #fff; color: #0f172a; font: inherit;
}
.form-input:focus, input[type="number"]:focus, input[type="text"]:focus {
  outline: 2px solid #c4b5fd; outline-offset: -1px;
}
.meta-row { display: flex; gap: 14px; flex-wrap: wrap; font-size: 12px;
            color: #64748b; margin-top: 8px; }
.meta-row b { color: #0f172a; font-weight: 600; }
.info-line { font-family: ui-monospace, "SF Mono", Menlo, monospace;
             font-size: 12px; color: #7c3aed; min-height: 16px; }
"""


def build_iframe_srcdoc(template: str, params: dict) -> str:
    return (
        '<!DOCTYPE html><html lang="fr"><head>'
        '<meta charset="utf-8" />'
        f'<style>{COMMON_STYLE}</style>'
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
        # textarea carries the full HTML for assignment via JS — avoids
        # escaping the iframe's srcdoc attribute by hand.
        raw_html.append(
            f'<textarea id="src-{i}" hidden>{srcdoc.replace("&", "&amp;").replace("<", "&lt;")}</textarea>'
        )

    page = (
        '<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">'
        '<title>Test widgets en isolation</title>'
        '<style>'
        'body{font-family:system-ui,-apple-system,sans-serif;max-width:900px;'
        'margin:20px auto;padding:0 20px;color:#0f172a;}'
        'h1{font-size:22px;}'
        '.widget-card{margin:24px 0;padding:16px;border-radius:16px;'
        'border:1px solid #e5e7eb;background:#fff;'
        'box-shadow:0 1px 2px 0 rgba(0,0,0,0.05);}'
        '.widget-card-head{font-size:11px;text-transform:uppercase;'
        'letter-spacing:0.05em;font-weight:600;color:#7c3aed;margin-bottom:10px;}'
        '.widget-card iframe{width:100%;height:460px;border:0;'
        'border-radius:8px;background:transparent;display:block;}'
        '.meta{margin:6px 0 0;font-size:12px;color:#64748b;}'
        'code{background:#f1f5f9;padding:2px 6px;border-radius:4px;font-size:12px;}'
        'p.note{color:#64748b;font-size:13px;}'
        '@media (prefers-color-scheme: dark){'
        'body{background:#0b1220;color:#e2e8f0;}'
        '.widget-card{background:#0f172a;border-color:#1f2937;}'
        '.widget-card-head{color:#c4b5fd;}'
        'code{background:#1e293b;color:#e2e8f0;}'
        '}'
        '</style></head><body>'
        '<h1>Test widgets — iframe sandboxé identique à l\'app</h1>'
        '<p class="note">Cette page reproduit le wrapper extérieur (carte + titre violet) et '
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
