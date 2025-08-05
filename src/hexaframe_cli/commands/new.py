from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import typer

from ..utils.fs import write_file
from ..utils.templating import render_text


@dataclass
class NewOptions:
    http: str = "fastapi"  # fastapi | flask | none
    tests: str = "pytest"  # pytest only for now
    sample: bool = True
    package: Optional[str] = None
    db: str = "none"  # none | sqlite | postgres


def new_cmd(
    project_name: str,
    http: str = "fastapi",
    tests: str = "pytest",
    package: Optional[str] = None,
    sample: bool = True,
    db: str = "none",
) -> None:
    """
    Create a new Hexaframe project (src layout).
    """
    # Ensure plain Python types when called programmatically (bypassing Typer parsing)
    project_name = str(project_name)
    http = str(http)
    tests = str(tests)
    package = None if package is None else str(package)
    sample = bool(sample)
    db = str(db)

    # Compute defaults
    pkg_name = (package if package is not None else project_name).replace("-", "_")
    opts = NewOptions(http=http, tests=tests, sample=sample, package=pkg_name, db=db)
    root = Path(project_name)
    if root.exists() and any(root.iterdir()):
        typer.secho(
            f"Directory '{project_name}' already exists and is not empty.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    package_name = opts.package

    # Create directories
    (root / "src" / package_name / "domain").mkdir(parents=True, exist_ok=True)
    (root / "src" / package_name / "application" / "use_cases").mkdir(
        parents=True, exist_ok=True
    )
    (root / "src" / package_name / "infrastructure").mkdir(parents=True, exist_ok=True)
    (root / "src" / package_name / "interface").mkdir(parents=True, exist_ok=True)
    if opts.http.lower() in ("fastapi", "flask"):
        (root / "src" / package_name / "interface" / "http").mkdir(
            parents=True, exist_ok=True
        )
    (root / "tests").mkdir(parents=True, exist_ok=True)

    # Base files via templates
    write_file(
        root / ".gitignore", render_text("project/gitignore.txt.j2", {}), exist_ok=True
    )
    readme_text = render_text(
        "project/README.md.j2",
        {
            "project_name": project_name,
            "package_name": package_name,
        },
    )
    write_file(root / "README.md", readme_text, exist_ok=True)
    write_file(
        root / "src" / package_name / "__init__.py", "__all__ = []\n", exist_ok=True
    )

    # HTTP sample (FastAPI only for now)
    http_choice = opts.http.lower()
    if http_choice == "fastapi" and opts.sample:
        # ensure __init__.py files so imports work out of the box
        write_file(
            root / "src" / package_name / "interface" / "__init__.py",
            "__all__ = []\n",
            exist_ok=True,
        )
        write_file(
            root / "src" / package_name / "interface" / "http" / "__init__.py",
            "__all__ = []\n",
            exist_ok=True,
        )
        app_py = render_text("project/app_fastapi.py.j2", {})
        write_file(
            root / "src" / package_name / "interface" / "http" / "app.py",
            app_py,
            exist_ok=False,
            overwrite=False,
        )
        # write test
        test_app = render_text("project/test_app.py.j2", {"package_name": package_name})
        write_file(
            root / "tests" / "test_app.py", test_app, exist_ok=False, overwrite=False
        )
    elif http_choice == "flask" and opts.sample:
        typer.secho(
            "Flask sample not yet implemented; scaffolding HTTP directory only.",
            fg=typer.colors.YELLOW,
        )

    # DB choice (placeholder hooks for future templates)
    db_choice = opts.db.lower()
    if db_choice not in ("none", "sqlite", "postgres"):
        typer.secho(
            f"Unknown --db choice '{opts.db}', expected none|sqlite|postgres",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)
    # For now, no DB-specific files.
    # This validates the flag and keeps room for future templates.

    typer.secho(f"Created project at {root}", fg=typer.colors.GREEN)
    # Write a minimal pyproject.toml so the package is importable via uv run (editable)
    # Pass selected options into pyproject template
    # so dependencies (fastapi/sql drivers/tests) are included correctly
    pyproject = render_text(
        "project/pyproject_min.toml.j2",
        {
            "package_name": package_name,
            "http_adapter": http_choice,
            "tests": tests,
            "db": db_choice,
        },
    )
    write_file(root / "pyproject.toml", pyproject, exist_ok=True)

    # Update README with DB/compose instructions if postgres selected
    if http_choice == "fastapi" and db_choice == "postgres":
        readme_text = render_text(
            "project/README.md.j2",
            {
                "project_name": project_name,
                "package_name": package_name,
            },
        )
        write_file(root / "README.md", readme_text, exist_ok=True, overwrite=True)

    # Auto-setup environment so the user can run immediately
    # 1) Create venv
    try:
        import subprocess

        subprocess.run(["uv", "venv"], cwd=str(root), check=True)
        # 2) Install build tooling required for editable installs
        # and legacy builds from TestPyPI if needed
        #    Include setuptools and wheel to satisfy
        # packages using legacy setuptools backend (e.g., some TestPyPI artifacts).
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--index-strategy",
                "unsafe-best-match",
                "hatchling>=1.20",
                "editables>=0.5",
                "setuptools>=68",
                "wheel>=0.41",
            ],
            cwd=str(root),
            check=True,
        )
        # 3) Install project from pyproject
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--no-build-isolation",
                "--index-strategy",
                "unsafe-best-match",
                "-e",
                ".",
            ],
            cwd=str(root),
            check=True,
        )
        # 4) Optionally install HTTP/test deps are already
        # in pyproject dependencies when selected,
        #    so no extra installs needed here.
        # 5) Create a uv.lock for reproducible installs (skip silently if it fails)
        try:
            subprocess.run(["uv", "lock"], cwd=str(root), check=True)
            typer.secho("Created uv.lock", fg=typer.colors.GREEN)
        except Exception:
            # Do not fail the scaffold if
            # lock creation fails (e.g., uv <version> or network)
            typer.secho(
                "Skipping uv.lock creation (uv not available or failed).",
                fg=typer.colors.YELLOW,
            )

        typer.secho("Environment set up in .venv", fg=typer.colors.GREEN)
        if http_choice == "fastapi":
            typer.secho(
                "You can now run:\n"
                f"  cd {project_name}\n"
                "  source .venv/bin/activate\n"
                "  uv run pytest -q\n"
                f"  uv run uvicorn {package_name}.interface.http.app:app --reload",
                fg=typer.colors.BLUE,
            )
        else:
            typer.secho(
                "You can now run:\n"
                f"  cd {project_name}\n"
                "  source .venv/bin/activate\n"
                "  uv run pytest -q",
                fg=typer.colors.BLUE,
            )
    except Exception:
        # Fallback to printed instructions if automation fails
        typer.secho(
            "Automatic environment setup failed; please run manually:",
            fg=typer.colors.YELLOW,
        )
        typer.echo(f"  cd {project_name}")
        typer.echo("  uv venv && source .venv/bin/activate")
        typer.echo(
            "  uv pip install --index-strategy "
            "unsafe-best-match hatchling>=1.20 editables>=0.5"
        )
        typer.echo("  uv pip install --no-build-isolation -e .")
        # Try to produce a lock as a final step; ignore errors
        typer.echo("  # optional but recommended for reproducible installs")
        typer.echo("  uv lock || true")
        if http_choice == "fastapi":
            typer.echo("  uv run pytest -q")
            typer.echo(
                f"  uv run uvicorn {package_name}.interface.http.app:app --reload"
            )
        else:
            typer.echo("  uv run pytest -q")
