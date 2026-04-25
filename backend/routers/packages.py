import re
import sys
import subprocess
from importlib import metadata

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import models
from ..auth import require_admin

router = APIRouter(prefix="/api/admin/packages", tags=["packages"])

PIP_TIMEOUT_SECONDS = 180

# Packages the app itself needs. Uninstalling any of these will break the server.
CORE_DEPENDENCIES = {
    "fastapi", "uvicorn", "sqlalchemy", "pydantic", "python-jose",
    "passlib", "bcrypt", "python-multipart", "aiofiles", "starlette",
    "anyio", "httpx",
}

# Package name: letters, digits, underscore, hyphen, dot.
# Version/extras specifiers use ==, >=, <=, ~=, !=, >, <, [extras].
# We accept requirement specifiers like "numpy>=1.24,<2.0" or "requests[socks]==2.31".
# Explicitly reject shell metacharacters.
_SAFE_REQUIREMENT_RE = re.compile(r"^[A-Za-z0-9_.\-\[\]=<>!~, ]+$")


class InstallRequest(BaseModel):
    name: str


class PackageInfo(BaseModel):
    name: str
    version: str
    is_core: bool


class PipResult(BaseModel):
    ok: bool
    detail: str
    output: str


def _normalize(name: str) -> str:
    # PEP 503 normalization: lowercase and collapse runs of _, -, . to -
    return re.sub(r"[-_.]+", "-", name.lower())


def _validate_requirement(spec: str) -> str:
    spec = (spec or "").strip()
    if not spec:
        raise HTTPException(status_code=400, detail="Le nom du paquet est requis")
    if len(spec) > 200:
        raise HTTPException(status_code=400, detail="Le spécificateur de paquet est trop long")
    if not _SAFE_REQUIREMENT_RE.match(spec):
        raise HTTPException(
            status_code=400,
            detail="Spécificateur de paquet invalide (seuls lettres, chiffres, _-.=<>!~[], sont autorisés)",
        )
    return spec


def _run_pip(args: list[str]) -> tuple[bool, str]:
    """Run pip with the current interpreter. Returns (ok, combined_output)."""
    cmd = [sys.executable, "-m", "pip", *args, "--disable-pip-version-check"]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=PIP_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, f"pip a expiré après {PIP_TIMEOUT_SECONDS}s"
    except FileNotFoundError:
        return False, "pip n'est pas disponible pour cet interpréteur Python"

    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode == 0, output.strip()


@router.get("/info")
def environment_info(admin: models.User = Depends(require_admin)):
    return {
        "python_version": sys.version.split()[0],
        "python_executable": sys.executable,
    }


@router.get("", response_model=list[PackageInfo])
def list_packages(admin: models.User = Depends(require_admin)):
    seen: dict[str, PackageInfo] = {}
    for dist in metadata.distributions():
        name = dist.metadata["Name"] or ""
        if not name:
            continue
        key = _normalize(name)
        # In case a package shows up twice, keep the first entry.
        if key in seen:
            continue
        seen[key] = PackageInfo(
            name=name,
            version=dist.version or "",
            is_core=key in {_normalize(d) for d in CORE_DEPENDENCIES},
        )
    return sorted(seen.values(), key=lambda p: p.name.lower())


@router.post("/install", response_model=PipResult)
def install_package(
    data: InstallRequest,
    admin: models.User = Depends(require_admin),
):
    spec = _validate_requirement(data.name)
    ok, output = _run_pip(["install", spec])
    return PipResult(
        ok=ok,
        detail=f"{spec} installé" if ok else f"Échec de l'installation de {spec}",
        output=output,
    )


@router.delete("/{name}", response_model=PipResult)
def uninstall_package(
    name: str,
    admin: models.User = Depends(require_admin),
):
    spec = _validate_requirement(name)
    # Refuse to touch pip / setuptools / wheel — removing these bricks pip itself.
    if _normalize(spec) in {"pip", "setuptools", "wheel"}:
        raise HTTPException(
            status_code=400,
            detail=f"Refus de désinstaller « {spec} » (requis par pip lui-même)",
        )
    ok, output = _run_pip(["uninstall", "-y", spec])
    return PipResult(
        ok=ok,
        detail=f"{spec} désinstallé" if ok else f"Échec de la désinstallation de {spec}",
        output=output,
    )
