"""Build a standalone HTML page that loads each widget in its own
sandboxed iframe — same setup as CustomWidget.jsx in the app.

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
    {"name": "viz-big-o",       "params": {}},
    {"name": "viz-hash-table",  "params": {"keys": "5,12,19,7,42,26,33"}},
    {"name": "viz-bst",         "params": {"keys": "50,30,70,20,40,60,80"}},
    {"name": "viz-heap",        "params": {"data": "5,12,3,8,17,9,21"}},
    {"name": "viz-partition",   "params": {"data": "3,7,1,8,4,2,5"}},
    {"name": "viz-quicksort",   "params": {"data": "8,3,5,1,9,2,7,4,6"}},
]


def main():
    body_blocks = []
    init_calls = []
    for i, case in enumerate(CASES):
        tmpl = (TEMPLATES / (case["name"] + ".html")).read_text(encoding="utf-8")
        # Wrap exactly like CustomWidget.jsx does: head + style + params injection + template
        srcdoc = (
            "<!DOCTYPE html><html lang='fr'><head>"
            "<meta charset='utf-8' />"
            "<style>"
            "html,body{margin:0;padding:0;height:100%;box-sizing:border-box;}"
            "*,*::before,*::after{box-sizing:inherit;}"
            "body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;"
            "color:#0f172a;background:transparent;padding:12px;}"
            "</style></head><body>"
            f"<script>window.__params = {json.dumps(case['params'])};</script>\n"
            f"{tmpl}"
            "</body></html>"
        )
        # Stash srcdoc inside a script so we can assign it via JS — avoids
        # the nightmare of escaping the srcdoc attribute itself.
        body_blocks.append(
            f'<h2>{i + 1}. {case["name"]} — params = '
            f'<code>{json.dumps(case["params"])}</code></h2>'
            f'<iframe id="iframe-{i}" sandbox="allow-scripts"></iframe>'
        )
        init_calls.append(
            f'document.getElementById("iframe-{i}").srcdoc = '
            f'document.getElementById("src-{i}").textContent;'
        )
    raw_blocks = "\n".join(
        f'<script type="text/plain" id="src-{i}">{json.dumps(srcdoc)[1:-1]}</script>'
        for i, (case, srcdoc) in enumerate(
            (
                (
                    c,
                    "<!DOCTYPE html><html lang='fr'><head>"
                    "<meta charset='utf-8' />"
                    "<style>"
                    "html,body{margin:0;padding:0;height:100%;box-sizing:border-box;}"
                    "*,*::before,*::after{box-sizing:inherit;}"
                    "body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;"
                    "color:#0f172a;background:transparent;padding:12px;}"
                    "</style></head><body>"
                    f"<script>window.__params = {json.dumps(c['params'])};</script>\n"
                    f"{(TEMPLATES / (c['name'] + '.html')).read_text(encoding='utf-8')}"
                    "</body></html>"
                )
                for c in CASES
            )
        )
    )
    # Hmm the above is getting tangled. Let me just inline everything more simply.
    blocks_html = []
    raw_html = []
    for i, case in enumerate(CASES):
        tmpl = (TEMPLATES / (case["name"] + ".html")).read_text(encoding="utf-8")
        srcdoc = (
            "<!DOCTYPE html><html lang=\"fr\"><head>"
            "<meta charset=\"utf-8\" />"
            "<style>"
            "html,body{margin:0;padding:0;height:100%;box-sizing:border-box;}"
            "*,*::before,*::after{box-sizing:inherit;}"
            "body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;"
            "color:#0f172a;background:transparent;padding:12px;}"
            "</style></head><body>"
            f"<script>window.__params = {json.dumps(case['params'])};</script>\n"
            f"{tmpl}"
            "</body></html>"
        )
        blocks_html.append(
            f'<h2>{i + 1}. {case["name"]} — params = '
            f'<code>{json.dumps(case["params"])}</code></h2>'
            f'<iframe id="iframe-{i}" sandbox="allow-scripts"></iframe>'
        )
        # Use a textarea (which can hold ANY content including </script>) to
        # carry the srcdoc, then assign it via JS at load time.
        raw_html.append(
            f'<textarea id="src-{i}" hidden>{srcdoc.replace("&", "&amp;").replace("<", "&lt;")}</textarea>'
        )

    page = (
        "<!DOCTYPE html><html lang=\"fr\"><head><meta charset=\"utf-8\">"
        "<title>Test widgets en isolation</title>"
        "<style>"
        "body{font-family:system-ui;max-width:900px;margin:20px auto;padding:0 20px;}"
        "h1{font-size:22px;}h2{font-size:17px;margin-top:32px;padding-top:14px;border-top:1px solid #e2e8f0;}"
        "p.note{color:#64748b;font-size:13px;}"
        "iframe{width:100%;height:480px;border:1px solid #cbd5e1;border-radius:8px;}"
        "code{background:#f1f5f9;padding:1px 5px;border-radius:3px;font-size:12px;}"
        "</style></head><body>"
        "<h1>Test widgets — iframe sandboxé identique à l'app</h1>"
        "<p class=\"note\">Si un widget s'affiche correctement ici, son code HTML+JS est OK. "
        "Si un widget ne s'affiche pas, ouvre la console du navigateur (F12) et regarde les "
        "erreurs JavaScript dans l'iframe (clique droit dans l'iframe → Inspect).</p>"
        + "\n".join(blocks_html)
        + "\n".join(raw_html)
        + "<script>"
        + "for (var i = 0; i < " + str(len(CASES)) + "; i++) {"
        + "  var src = document.getElementById('src-' + i);"
        + "  var iframe = document.getElementById('iframe-' + i);"
        + "  iframe.srcdoc = src.value;"
        + "}"
        + "</script>"
        "</body></html>"
    )

    OUT.write_text(page, encoding="utf-8")
    print(f"  [ok] wrote {OUT}")
    print(f"  [info] open in your browser, no server needed.")


if __name__ == "__main__":
    main()
