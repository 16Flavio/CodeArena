"""Centralised guards for file uploads — caps the body size before it
hits memory and sanitises client-supplied filenames so they can't escape
the upload directory.

The size limits live here so they're easy to tune without grepping the
routers, and so a future review can see at a glance "we cap submissions
at 5 MB" instead of having to chase a magic constant per endpoint.
"""
from __future__ import annotations

import os
import re
import unicodedata

from fastapi import HTTPException, UploadFile

# Per-endpoint caps. Generous enough for normal use, tight enough that a
# malicious client can't fill the disk or burn server memory by sending
# a 100 GB body. Bumped via env if needed (left as code for now).
MAX_SUBMISSION_OUTPUT_BYTES = 5 * 1024 * 1024
MAX_ICPC_SOURCE_BYTES = 1 * 1024 * 1024
MAX_INSTANCE_INPUT_BYTES = 50 * 1024 * 1024
MAX_DOMJUDGE_PACKAGE_BYTES = 100 * 1024 * 1024
MAX_TEAMS_CSV_BYTES = 1 * 1024 * 1024


_FILENAME_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_filename(raw: str | None, fallback: str = "upload.bin") -> str:
    """Strip any directory component, normalise unicode, drop unsafe
    characters. Always returns a non-empty filename — falls back to
    ``fallback`` if everything was stripped or ``raw`` was ``None``.

    The returned name is safe to embed in a filesystem path: no path
    separators, no leading dots, no NUL bytes, no traversal sequences."""
    if not raw:
        return fallback
    # Take basename twice — once with each separator family — so that
    # ``a\b/c.txt`` reduces to ``c.txt`` regardless of platform.
    base = os.path.basename(raw.replace("\\", "/"))
    # Normalise NFKC so visually-identical unicode collapses to the same
    # ASCII (e.g. fullwidth letters → plain ASCII).
    base = unicodedata.normalize("NFKC", base)
    # Replace any leftover unsafe character with ``_``. Keeps the
    # extension intact.
    base = _FILENAME_SAFE.sub("_", base)
    # Strip leading dots so the file isn't hidden / treated as a
    # rc-file by tooling.
    base = base.lstrip(".") or fallback
    # Cap length so a 4000-char filename can't blow up DB columns or
    # filesystems with NAME_MAX = 255.
    if len(base) > 200:
        # Preserve the extension when truncating.
        root, ext = os.path.splitext(base)
        base = root[: 200 - len(ext)] + ext
    return base or fallback


async def read_upload_capped(file: UploadFile, max_bytes: int) -> bytes:
    """Read an UploadFile body into memory, refusing anything past
    ``max_bytes``. Reads in 1 MB chunks so a 100 GB attacker payload
    fails fast instead of allocating its way to OOM.

    Raises ``HTTPException(413)`` when the cap is exceeded.
    """
    chunks: list[bytes] = []
    total = 0
    chunk_size = 1024 * 1024  # 1 MB
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Fichier trop volumineux (max {max_bytes // (1024 * 1024)} Mo)",
            )
        chunks.append(chunk)
    return b"".join(chunks)
