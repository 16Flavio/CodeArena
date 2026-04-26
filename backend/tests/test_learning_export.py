"""Smoke tests for the LaTeX export. Focus on the converter
correctness — the ZIP plumbing is exercised by the endpoint test."""
import io
import zipfile

import pytest

from .conftest import auth_header
from backend.learning_export import markdown_to_latex


def test_basic_inline_formatting():
    md = "Hello **world**, *italic*, `code`, [link](https://x)."
    out = markdown_to_latex(md)
    assert r"\textbf{world}" in out
    assert r"\textit{italic}" in out
    assert r"\verb|code|" in out
    assert r"\href{https://x}" in out


def test_headings():
    md = "# H1\n\n## H2\n\n### H3\n"
    out = markdown_to_latex(md)
    assert r"\subsection{H1}" in out
    assert r"\subsubsection{H2}" in out
    assert r"\paragraph{H3}" in out


def test_lists():
    md = "- a\n- b\n- c\n\n1. one\n2. two\n"
    out = markdown_to_latex(md)
    assert r"\begin{itemize}" in out
    assert r"\item a" in out
    assert r"\begin{enumerate}" in out
    assert r"\item one" in out


def test_code_block():
    md = "```\nint main() { return 0; }\n```\n"
    out = markdown_to_latex(md)
    assert r"\begin{verbatim}" in out
    assert "int main()" in out
    assert r"\end{verbatim}" in out


def test_special_chars_escaped():
    md = "100% & a_b & {x}"
    out = markdown_to_latex(md)
    assert r"\%" in out
    assert r"\&" in out
    assert r"\_" in out
    assert r"\{" in out and r"\}" in out


def test_widget_directive():
    md = ':::viz-sort{algo="bubble" data="[1,2,3]"}\nbody ignored\n:::\n'
    out = markdown_to_latex(md, lesson_url="https://x/learn/lessons/42")
    assert r"\learnwidget{viz-sort}" in out
    assert "algo=bubble" in out
    # Body content between fences is dropped, by design (the body is
    # the live JSX rendering — only the directive name + attrs survive).
    assert "body ignored" not in out


def test_image_with_asset_map():
    md = "![alt](/api/learning/assets/1/foo.png)"
    out = markdown_to_latex(
        md, asset_map={"/api/learning/assets/1/foo.png": "assets/1/foo.png"},
    )
    assert r"\includegraphics" in out
    assert "assets/1/foo.png" in out


def test_image_external_falls_back():
    md = "![alt](https://external.com/img.png)"
    out = markdown_to_latex(md, asset_map={})
    assert r"\includegraphics" not in out
    assert r"\textit{Image externe" in out


def test_export_endpoint_streams_zip(client):
    admin = auth_header(client, "root")
    # Build a tiny syllabus.
    sid = client.post("/api/admin/learning/sections", json={
        "slug": "tests", "title_fr": "Tests FR", "title_en": "Tests EN",
        "description_fr": None, "description_en": None,
        "order_idx": 0, "is_published": True,
    }, headers=admin).json()["id"]
    client.post(f"/api/admin/learning/sections/{sid}/lessons", json={
        "slug": "intro", "title_fr": "Intro", "title_en": "Intro",
        "content_fr": "# Bonjour\n\nUn paragraphe avec **gras**.\n",
        "content_en": "# Hi\n\nA paragraph with **bold**.\n",
        "order_idx": 0, "is_published": True,
    }, headers=admin)

    r = client.get("/api/admin/learning/export/latex?lang=fr", headers=admin)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/zip")
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = zf.namelist()
    assert "main.tex" in names
    assert "README.md" in names
    assert any(n.startswith("sections/") for n in names)
    main = zf.read("main.tex").decode("utf-8")
    assert r"\documentclass" in main
    assert r"\learnwidget" in main  # the macro is defined in the preamble


def test_export_admin_only(client):
    auth_header(client, "root")  # bootstrap admin
    alice = auth_header(client, "alice")
    r = client.get("/api/admin/learning/export/latex?lang=fr", headers=alice)
    assert r.status_code in (401, 403)
