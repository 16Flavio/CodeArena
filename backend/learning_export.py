"""Markdown → LaTeX export for the learning zone.

Focused converter - handles the markdown subset the admin UI can
produce, plus our custom directive widgets. We deliberately avoid
pulling in pandoc: it's a 200 MB binary dependency for a use case
this small. The trade-off is that exotic markdown (footnotes,
definition lists, math via $...$) is not supported. If a future
lesson needs LaTeX math it can be entered directly: the converter
passes ``$...$`` and ``$$...$$`` through unchanged.

Widget directives become a single user-customisable LaTeX macro
``\learnwidget{kind}{params}{anchor}`` that authors of the syllabus
.tex can re-define however they want (figure with screenshot,
tcolorbox, sidebar note, …). Default rendering is a tcolorbox with
the directive's name + parameters + a link back to the online
lesson.
"""
from __future__ import annotations

import io
import os
import re
import zipfile
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy.orm import Session

from . import models


# ── Markdown to LaTeX ─────────────────────────────────────────────────────────

# LaTeX-special characters that need escaping in arbitrary text. We
# convert them to their command form so they render as the literal
# character. Order matters - backslash first so we don't double-escape.
_LATEX_ESCAPES = [
    ("\\", r"\textbackslash{}"),
    ("&", r"\&"),
    ("%", r"\%"),
    ("$", r"\$"),
    ("#", r"\#"),
    ("_", r"\_"),
    ("{", r"\{"),
    ("}", r"\}"),
    ("~", r"\textasciitilde{}"),
    ("^", r"\textasciicircum{}"),
]


def _latex_escape(text: str) -> str:
    """Escape LaTeX-special chars in plain text."""
    for src, dst in _LATEX_ESCAPES:
        text = text.replace(src, dst)
    return text


# Inline regex patterns. Order matters: math first so its body isn't
# escaped, code second so its body isn't molested by bold/italic, then
# the rest.
#
# Inline code uses ``\texttt{...}`` rather than ``\verb`` because ``\verb``
# is a fragile command - illegal inside the argument of another command
# (``\subsection``, ``\href``, ``\textbf``...). ``\texttt`` is robust
# everywhere; we just escape the LaTeX-special chars inside.
_INLINE_PATTERNS = [
    # Math display ``$$...$$`` and inline ``$...$`` - body is passed
    # through unchanged. Display first so ``$$`` isn't split as two
    # adjacent inline empties. Multi-line bodies survive because by the
    # time we get here paragraphs have been joined with spaces (cf.
    # markdown_to_latex's paragraph collector).
    (re.compile(r"\$\$([^$]+)\$\$"), lambda m: "$$" + m.group(1) + "$$"),
    (re.compile(r"\$([^$\n]+)\$"),   lambda m: "$" + m.group(1) + "$"),
    (re.compile(r"`([^`\n]+)`"), lambda m: r"\texttt{" + _latex_escape(m.group(1)) + "}"),
    # Bold + italic combined
    (re.compile(r"\*\*\*([^*\n]+)\*\*\*"), lambda m: r"\textbf{\textit{" + _latex_escape(m.group(1)) + "}}"),
    (re.compile(r"\*\*([^*\n]+)\*\*"), lambda m: r"\textbf{" + _latex_escape(m.group(1)) + "}"),
    (re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)"), lambda m: r"\textit{" + _latex_escape(m.group(1)) + "}"),
    # Markdown links [label](url)
    (re.compile(r"\[([^\]]+)\]\(([^)]+)\)"),
     lambda m: r"\href{" + m.group(2) + "}{" + _latex_escape(m.group(1)) + "}"),
]


def _render_inline(text: str) -> str:
    """Convert markdown inline syntax to LaTeX. Plain runs are escaped;
    syntax matches are replaced by their command form. The order in
    ``_INLINE_PATTERNS`` controls precedence (code spans win over bold).

    The naive approach - repeated regex substitution on the whole
    string - over-escapes since we'd re-escape inside our own
    replacements. Instead we tokenise: for each match we keep its
    pre-substituted output, escape the surrounding plain text, and
    join."""
    # Simple state machine: walk left-to-right, find the earliest match
    # of any pattern, take it, escape the gap. Repeat until exhausted.
    out_parts: list[str] = []
    cursor = 0
    while cursor < len(text):
        best_match = None
        best_idx = len(text)
        best_handler = None
        for pattern, handler in _INLINE_PATTERNS:
            m = pattern.search(text, cursor)
            if m is not None and m.start() < best_idx:
                best_match = m
                best_idx = m.start()
                best_handler = handler
        if best_match is None:
            out_parts.append(_latex_escape(text[cursor:]))
            break
        if best_idx > cursor:
            out_parts.append(_latex_escape(text[cursor:best_idx]))
        out_parts.append(best_handler(best_match))
        cursor = best_match.end()
    return "".join(out_parts)


def _render_image(alt: str, url: str, asset_map: dict[str, str]) -> str:
    """Markdown image → LaTeX includegraphics.

    ``asset_map`` maps the URL the admin wrote in markdown to the path
    it lands at inside the export ZIP (relative to the .tex root). When
    the URL isn't in the map (external image, broken reference) we
    emit a placeholder block instead of a broken \\includegraphics."""
    local = asset_map.get(url)
    if local is None:
        return (
            r"\begin{center}\fbox{\parbox{0.8\linewidth}{\centering "
            + r"\textit{Image externe : " + _latex_escape(url) + "}}}\\end{center}"
        )
    return (
        r"\begin{figure}[H]\centering\includegraphics[max width=\linewidth]{"
        + local + r"}\caption{" + _latex_escape(alt) + r"}\end{figure}"
    )


# Regex for a directive opener / closer. We accept the standard remark-
# directive container form (3+ colons, optional attributes, optional
# closer). The closer ``:::`` ends the block; without one the block
# runs to end of file.
_DIRECTIVE_OPEN_RE = re.compile(
    r"^:{3,}([a-z0-9-]+)(?:\{([^}]*)\})?\s*$"
)


def _parse_directive_attrs(raw: str) -> dict[str, str]:
    """``algo="bubble" data="[5,2,8,1]"`` → {algo: bubble, data: [5,2,8,1]}.
    Tolerates single quotes, missing quotes, and attributes with no
    value (treated as boolean true)."""
    out: dict[str, str] = {}
    if not raw:
        return out
    # Match key=value, key="value", key='value', or bare key.
    pattern = re.compile(
        r"""(\w+)(?:=(?:"([^"]*)"|'([^']*)'|(\S+)))?"""
    )
    for m in pattern.finditer(raw):
        key = m.group(1)
        value = m.group(2) or m.group(3) or m.group(4) or "true"
        out[key] = value
    return out


def _render_widget(name: str, attrs: dict[str, str], lesson_url: str) -> str:
    """A widget directive becomes a call to ``\learnwidget``. The
    main.tex defines this macro; redefine it to customise rendering.

    The URL goes through ``\href`` in the macro body - hyperref handles
    its own escaping, so we pass the URL **raw** (escaping ``_`` to
    ``\_`` would break the link). Args have already been escaped at
    construction so we don't double-escape them either.
    """
    args = ", ".join(
        f"{_latex_escape(k)}={_latex_escape(v)}" for k, v in attrs.items()
    ) or "-"
    return (
        r"\learnwidget{" + _latex_escape(name) + "}{"
        + args + "}{" + lesson_url + "}"
    )


def markdown_to_latex(
    md: str, *, asset_map: dict[str, str] | None = None,
    lesson_url: str = "",
) -> str:
    """Top-level converter. ``asset_map`` lets us rewrite image URLs to
    their bundled-in-zip paths. Returns LaTeX body suitable for
    inclusion under a ``\\section{}`` heading."""
    asset_map = asset_map or {}
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    in_code = False
    code_buf: list[str] = []

    while i < len(lines):
        line = lines[i]

        # Fenced code block
        if line.startswith("```"):
            if in_code:
                out.append(r"\begin{verbatim}")
                out.extend(code_buf)
                out.append(r"\end{verbatim}")
                code_buf = []
                in_code = False
            else:
                in_code = True
            i += 1
            continue
        if in_code:
            code_buf.append(line)
            i += 1
            continue

        # Directive
        m = _DIRECTIVE_OPEN_RE.match(line)
        if m is not None:
            name, raw_attrs = m.group(1), m.group(2) or ""
            attrs = _parse_directive_attrs(raw_attrs)
            # Skip body lines until matching closer (or EOF).
            i += 1
            while i < len(lines) and not re.match(r"^:{3,}\s*$", lines[i]):
                i += 1
            if i < len(lines):
                i += 1  # consume closer
            out.append(_render_widget(name, attrs, lesson_url))
            continue

        # Headings
        if line.startswith("# "):
            out.append(r"\subsection{" + _render_inline(line[2:].strip()) + "}")
            i += 1
            continue
        if line.startswith("## "):
            out.append(r"\subsubsection{" + _render_inline(line[3:].strip()) + "}")
            i += 1
            continue
        if line.startswith("### "):
            out.append(r"\paragraph{" + _render_inline(line[4:].strip()) + "}")
            i += 1
            continue

        # Image standalone - `![alt](url)` on its own line
        m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", line)
        if m is not None:
            out.append(_render_image(m.group(1), m.group(2), asset_map))
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^-{3,}\s*$", line):
            out.append(r"\noindent\hrulefill")
            i += 1
            continue

        # Unordered list - collect contiguous ``- `` lines
        if re.match(r"^[-*]\s+", line):
            items: list[str] = []
            while i < len(lines) and re.match(r"^[-*]\s+", lines[i]):
                items.append(re.sub(r"^[-*]\s+", "", lines[i]).rstrip())
                i += 1
            out.append(r"\begin{itemize}")
            for it in items:
                out.append(r"  \item " + _render_inline(it))
            out.append(r"\end{itemize}")
            continue

        # Ordered list
        if re.match(r"^\d+\.\s+", line):
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i]):
                items.append(re.sub(r"^\d+\.\s+", "", lines[i]).rstrip())
                i += 1
            out.append(r"\begin{enumerate}")
            for it in items:
                out.append(r"  \item " + _render_inline(it))
            out.append(r"\end{enumerate}")
            continue

        # Blank line - paragraph separator.
        if not line.strip():
            out.append("")
            i += 1
            continue

        # Default: a paragraph line. Collect until a blank or special.
        para = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not _line_is_special(lines[i]):
            para.append(lines[i])
            i += 1
        out.append(_render_inline(" ".join(p.strip() for p in para)))

    # Flush any open code block (defensive - markdown that doesn't
    # close its fence still escapes cleanly).
    if in_code:
        out.append(r"\begin{verbatim}")
        out.extend(code_buf)
        out.append(r"\end{verbatim}")

    return "\n".join(out)


def _line_is_special(line: str) -> bool:
    """A line that isn't part of a flowing paragraph."""
    s = line.lstrip()
    return (
        s.startswith("#")
        or s.startswith("```")
        or s.startswith(":::")
        or re.match(r"^[-*]\s+", s) is not None
        or re.match(r"^\d+\.\s+", s) is not None
        or re.match(r"^!\[[^\]]*\]\(", s) is not None
        or re.match(r"^-{3,}\s*$", s) is not None
    )


# ── ZIP bundling ──────────────────────────────────────────────────────────────

_PREAMBLE = r"""\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[french,english]{babel}
\usepackage{lmodern}
\usepackage[a4paper,margin=2.5cm]{geometry}
\usepackage{graphicx}
\usepackage[export]{adjustbox}
\usepackage{hyperref}
\usepackage{tcolorbox}
\usepackage{float}
\usepackage{enumitem}
\usepackage{xcolor}
\usepackage{amsmath}
\usepackage{amssymb}

%% Unicode math symbols frequently typed in lessons. ``inputenc`` covers
%% accented Latin glyphs but not these. ``\ensuremath`` makes them work
%% in both text and math context, so a stray ``≤`` mid-paragraph no
%% longer triggers ``Missing $ inserted``. Extend the list when an
%% author types a new symbol that pdflatex chokes on.
\DeclareUnicodeCharacter{2264}{\ensuremath{\le}}
\DeclareUnicodeCharacter{2265}{\ensuremath{\ge}}
\DeclareUnicodeCharacter{2260}{\ensuremath{\ne}}
\DeclareUnicodeCharacter{2248}{\ensuremath{\approx}}
\DeclareUnicodeCharacter{2261}{\ensuremath{\equiv}}
\DeclareUnicodeCharacter{00B1}{\ensuremath{\pm}}
\DeclareUnicodeCharacter{00D7}{\ensuremath{\times}}
\DeclareUnicodeCharacter{00F7}{\ensuremath{\div}}
\DeclareUnicodeCharacter{00B7}{\ensuremath{\cdot}}
\DeclareUnicodeCharacter{2192}{\ensuremath{\rightarrow}}
\DeclareUnicodeCharacter{2190}{\ensuremath{\leftarrow}}
\DeclareUnicodeCharacter{21D2}{\ensuremath{\Rightarrow}}
\DeclareUnicodeCharacter{21D4}{\ensuremath{\Leftrightarrow}}
\DeclareUnicodeCharacter{2200}{\ensuremath{\forall}}
\DeclareUnicodeCharacter{2203}{\ensuremath{\exists}}
\DeclareUnicodeCharacter{2208}{\ensuremath{\in}}
\DeclareUnicodeCharacter{2209}{\ensuremath{\notin}}
\DeclareUnicodeCharacter{222A}{\ensuremath{\cup}}
\DeclareUnicodeCharacter{2229}{\ensuremath{\cap}}
\DeclareUnicodeCharacter{2282}{\ensuremath{\subset}}
\DeclareUnicodeCharacter{2286}{\ensuremath{\subseteq}}
\DeclareUnicodeCharacter{221E}{\ensuremath{\infty}}
\DeclareUnicodeCharacter{221A}{\ensuremath{\sqrt{}}}
\DeclareUnicodeCharacter{2211}{\ensuremath{\sum}}
\DeclareUnicodeCharacter{220F}{\ensuremath{\prod}}
\DeclareUnicodeCharacter{222B}{\ensuremath{\int}}
\DeclareUnicodeCharacter{2207}{\ensuremath{\nabla}}
\DeclareUnicodeCharacter{2202}{\ensuremath{\partial}}
\DeclareUnicodeCharacter{00B2}{\ensuremath{^2}}
\DeclareUnicodeCharacter{00B3}{\ensuremath{^3}}
\DeclareUnicodeCharacter{0394}{\ensuremath{\Delta}}
\DeclareUnicodeCharacter{0398}{\ensuremath{\Theta}}
\DeclareUnicodeCharacter{039B}{\ensuremath{\Lambda}}
\DeclareUnicodeCharacter{03A0}{\ensuremath{\Pi}}
\DeclareUnicodeCharacter{03A3}{\ensuremath{\Sigma}}
\DeclareUnicodeCharacter{03A6}{\ensuremath{\Phi}}
\DeclareUnicodeCharacter{03A9}{\ensuremath{\Omega}}
\DeclareUnicodeCharacter{03B1}{\ensuremath{\alpha}}
\DeclareUnicodeCharacter{03B2}{\ensuremath{\beta}}
\DeclareUnicodeCharacter{03B3}{\ensuremath{\gamma}}
\DeclareUnicodeCharacter{03B4}{\ensuremath{\delta}}
\DeclareUnicodeCharacter{03B5}{\ensuremath{\varepsilon}}
\DeclareUnicodeCharacter{03B8}{\ensuremath{\theta}}
\DeclareUnicodeCharacter{03BB}{\ensuremath{\lambda}}
\DeclareUnicodeCharacter{03BC}{\ensuremath{\mu}}
\DeclareUnicodeCharacter{03C0}{\ensuremath{\pi}}
\DeclareUnicodeCharacter{03C1}{\ensuremath{\rho}}
\DeclareUnicodeCharacter{03C3}{\ensuremath{\sigma}}
\DeclareUnicodeCharacter{03C6}{\ensuremath{\varphi}}
\DeclareUnicodeCharacter{03C8}{\ensuremath{\psi}}
\DeclareUnicodeCharacter{03C9}{\ensuremath{\omega}}
\DeclareUnicodeCharacter{25A1}{\ensuremath{\square}}

\hypersetup{
  colorlinks=true,
  linkcolor=violet,
  urlcolor=violet,
  citecolor=violet,
}

%% Customise this command to control how widget directives render.
%% #1 = widget kind (e.g. viz-sort), #2 = parameters, #3 = link back.
\newcommand{\learnwidget}[3]{%
  \begin{tcolorbox}[colback=violet!5!white,colframe=violet!50!black,
                    title={Widget interactif : \texttt{#1}}]
    \textit{Cette animation n'est lisible qu'en ligne.}
    \par\smallskip
    Paramètres : \texttt{#2}
    \par\smallskip
    \href{#3}{Voir l'animation $\rightarrow$}
  \end{tcolorbox}
}

\title{__TITLE__}
\author{__AUTHOR__}
\date{__DATE__}

\begin{document}
\maketitle
\tableofcontents
\newpage
"""


_README = """# Syllabus LaTeX export

This zip is a self-contained LaTeX project. To compile it to PDF:

## Option 1 - local

```bash
cd export-extracted/
pdflatex main.tex
pdflatex main.tex   # second pass for the table of contents
```

You'll need a TeX distribution installed (TeX Live, MiKTeX, MacTeX).

## Option 2 - Overleaf

1. Create a new Overleaf project.
2. Upload this zip via "Menu → Upload project".
3. Click "Recompile".

## Customisation

* `main.tex` is the entry point. Tweak `\\title`, `\\author`, the
  preamble, or the `\\learnwidget` command to change how interactive
  widgets render in the PDF.
* `sections/` contains one .tex file per learning section. Re-order
  them in `main.tex` if you want a different curriculum order.
* `assets/` holds the images embedded in lessons.

## Widget directives

Interactive animations from the online platform (sort visualizations,
etc.) are inert in PDF: the macro `\\learnwidget` renders a coloured
box that points the reader at the online lesson where the animation
lives. Override the macro if you'd rather embed a screenshot.
"""


def _slugify(s: str) -> str:
    s = (s or "untitled").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "untitled"


def build_export_zip(db: Session, *, lang: str = "fr",
                     site_url: str = "") -> bytes:
    """Generate the export. ``lang`` picks which content_* / title_*
    columns to read. ``site_url`` is the public base URL of the
    platform - embedded in widget links so the printed reader can
    click back to the live animation.
    """
    if lang not in ("fr", "en"):
        raise ValueError("lang must be 'fr' or 'en'")

    sections = (
        db.query(models.LearningSection)
        .filter(models.LearningSection.is_published.is_(True))
        .order_by(models.LearningSection.order_idx, models.LearningSection.id)
        .all()
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Preamble - main.tex
        title = "CodeArena - Syllabus" if lang == "en" else "CodeArena - Syllabus"
        author = "CodeArena"
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        main_lines = [
            _PREAMBLE.replace("__TITLE__", _latex_escape(title))
                     .replace("__AUTHOR__", _latex_escape(author))
                     .replace("__DATE__", _latex_escape(today))
        ]

        # Asset bundling: walk every published lesson, find its assets,
        # write them to assets/<lesson_id>/<filename>, and build a map
        # from the URL the admin wrote in markdown to the local path.
        asset_map: dict[str, str] = {}
        for section in sections:
            for lesson in sorted(
                [l for l in section.lessons if l.is_published],
                key=lambda l: (l.order_idx, l.id),
            ):
                for asset in lesson.assets or []:
                    if not asset.path or not os.path.exists(asset.path):
                        continue
                    rel_in_zip = (
                        f"assets/{lesson.id}/{os.path.basename(asset.path)}"
                    )
                    zf.write(asset.path, rel_in_zip)
                    # The URL the admin wrote was something like
                    # /api/learning/assets/<lesson_id>/<file>. Map it
                    # to the relative path inside the zip.
                    api_url = (
                        f"/api/learning/assets/{lesson.id}/"
                        f"{os.path.basename(asset.path)}"
                    )
                    asset_map[api_url] = rel_in_zip

        # Per-section .tex files
        for s_idx, section in enumerate(sections):
            section_title = (s.title_fr if lang == "fr" else s.title_en) if False else (
                section.title_fr if lang == "fr" else section.title_en
            )
            slug = _slugify(section.slug or section_title)
            sec_path = f"sections/{s_idx:02d}-{slug}.tex"
            sec_lines = [
                r"\section{" + _latex_escape(section_title) + "}",
            ]
            section_desc = section.description_fr if lang == "fr" else section.description_en
            if section_desc:
                sec_lines.append(_render_inline(section_desc.strip()))
                sec_lines.append("")
            for lesson in sorted(
                [l for l in section.lessons if l.is_published],
                key=lambda l: (l.order_idx, l.id),
            ):
                lesson_title = lesson.title_fr if lang == "fr" else lesson.title_en
                lesson_body = lesson.content_fr if lang == "fr" else lesson.content_en
                lesson_url = (
                    f"{site_url.rstrip('/')}/learn/lessons/{lesson.id}"
                    if site_url else f"/learn/lessons/{lesson.id}"
                )
                sec_lines.append(
                    r"\subsection{" + _latex_escape(lesson_title) + "}"
                )
                sec_lines.append(
                    markdown_to_latex(
                        lesson_body or "",
                        asset_map=asset_map,
                        lesson_url=lesson_url,
                    )
                )
                sec_lines.append("")
            zf.writestr(sec_path, "\n".join(sec_lines))
            main_lines.append(r"\input{" + sec_path[:-4] + "}")

        main_lines.append(r"\end{document}")
        zf.writestr("main.tex", "\n".join(main_lines))
        zf.writestr("README.md", _README)

    return buf.getvalue()
