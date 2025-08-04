from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer


def _run(cmd: list[str]) -> int:
    """
    Run a subprocess streaming output to current stdout/stderr.
    Returns the process return code.
    """
    proc = subprocess.run(cmd)
    return proc.returncode


def _detect_fastapi_app() -> Optional[str]:
    """
    Try to detect a FastAPI app module path in src/*/interface/http/app.py.
    Returns an import path like 'mypkg.interface.http.app:app' if found.
    """
    src = Path("src")
    if not src.exists():
        return None
    for pkg_init in src.glob("*/__init__.py"):
        pkg = pkg_init.parent.name
        app_py = pkg_init.parent / "interface" / "http" / "app.py"
        if app_py.exists():
            return f"{pkg}.interface.http.app:app"
    return None


def runserver_cmd(
    host: str = "127.0.0.1", port: int = 8000, reload: bool = True
) -> None:
    """
    Run uvicorn for detected FastAPI app using uv run if available,
    else python -m uvicorn.
    """
    app_path = _detect_fastapi_app()
    if app_path is None:
        typer.secho(
            "Could not detect a FastAPI app at src/*/interface/http/app.py",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    cmd = ["uv", "run", "uvicorn", app_path, "--host", host, "--port", str(port)]
    if reload:
        cmd.append("--reload")

    rc = _run(cmd)
    if rc != 0:
        # Fallback: try python -m uvicorn
        fallback = [
            sys.executable,
            "-m",
            "uvicorn",
            app_path,
            "--host",
            host,
            "--port",
            str(port),
        ]
        if reload:
            fallback.append("--reload")
        rc2 = _run(fallback)
        raise typer.Exit(rc2)


def test_cmd(extra_args: Optional[str] = None) -> None:
    """
    Run pytest via uv run if available, else python -m pytest.
    """
    base = ["uv", "run", "pytest"]
    if extra_args:
        base.extend(shlex.split(extra_args))

    rc = _run(base)
    if rc != 0:
        fallback = [sys.executable, "-m", "pytest"]
        if extra_args:
            fallback.extend(shlex.split(extra_args))
        rc2 = _run(fallback)
        raise typer.Exit(rc2)
