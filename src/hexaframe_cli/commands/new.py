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
    pyproject = render_text(
        "project/pyproject_min.toml.j2", {"package_name": package_name}
    )
    write_file(root / "pyproject.toml", pyproject, exist_ok=True)

    typer.secho("Next steps:", fg=typer.colors.BLUE)
    typer.echo(f"  cd {project_name}")
    typer.echo("  uv venv && source .venv/bin/activate")
    if http_choice == "fastapi":
        steps = [
            "  uv pip install -e . fastapi uvicorn pytest pytest-asyncio httpx",
            "  hexaframe runserver",
            "  # or: uv run uvicorn yourpkg.interface.http.app:app --reload",
        ]
        for s in steps:
            typer.echo(s)
    else:
        typer.echo("  uv pip install -e . pytest pytest-asyncio httpx")
    typer.echo("  hexaframe test -q  # runs pytest")
