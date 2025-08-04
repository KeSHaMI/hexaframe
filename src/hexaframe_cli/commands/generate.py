from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import typer

from ..utils.fs import write_file
from ..utils.templating import render_text

generate_app = typer.Typer(help="Code generation commands")


def _to_snake(name: str) -> str:
    name = name.strip().replace("-", "_").replace(" ", "_")
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
    snake = re.sub(r"[^a-z0-9_]", "_", snake)
    snake = re.sub(r"__+", "_", snake).strip("_")
    return snake or "name"


def _to_camel(name: str) -> str:
    # Normalize to snake first to preserve word boundaries from any input form,
    # then build CamelCase by capitalizing each part.
    snake = _to_snake(name)
    parts = [p for p in snake.split("_") if p]
    return "".join(p.capitalize() for p in parts) or "Name"


def _detect_package(root: Path) -> Optional[str]:
    # Try pyproject [project.name]
    py = root / "pyproject.toml"
    if py.exists():
        text = py.read_text(encoding="utf-8")
        if re.search(r"^\s*\[project\]\s*$", text, re.MULTILINE):
            m = re.search(r'^\s*name\s*=\s*"([^"]+)"', text, re.MULTILINE)
            if m:
                return m.group(1).replace("-", "_")
    # Fallback: single directory under src
    src = root / "src"
    if src.exists() and src.is_dir():
        dirs = [
            d.name for d in src.iterdir() if d.is_dir() and not d.name.startswith("_")
        ]
        if len(dirs) == 1:
            return dirs[0]
    return None


@generate_app.command("usecase")
def generate_usecase(
    name: str = typer.Argument(..., help="Use case name (CamelCase or snake_case)"),
    package: Optional[str] = typer.Option(
        None, help="Package name under src/. If omitted, auto-detect."
    ),
    sync: bool = typer.Option(
        False,
        "--sync/--async",
        help="Generate sync UseCase instead of async",
        rich_help_panel="Behavior",
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite existing files"),
):
    """
    Generate a use case skeleton and a matching test.
    Run inside project root (where pyproject.toml lives).
    """
    name = str(name)
    snake = _to_snake(name)
    cls = _to_camel(name)
    root = Path(".").resolve()
    pkg = package or _detect_package(root)
    if not pkg:
        typer.secho("Could not determine package. Pass --package.", fg=typer.colors.RED)
        raise typer.Exit(2)

    template_key = "usecase_sync.py.j2" if sync else "usecase_async.py.j2"
    test_key = "test_usecase_sync.py.j2" if sync else "test_usecase_async.py.j2"

    uc_path = root / "src" / pkg / "usecases" / f"{snake}.py"
    test_path = root / "tests" / f"test_{snake}.py"

    content = render_text(
        f"generate/{template_key}", {"ClassName": cls, "snake_name": snake}
    )
    test_content = render_text(
        f"generate/{test_key}",
        {"package_name": pkg, "snake_name": snake, "ClassName": cls},
    )

    if uc_path.exists() and not force:
        typer.secho(
            f"File exists: {uc_path}. Use --force to overwrite.", fg=typer.colors.RED
        )
        raise typer.Exit(3)
    if test_path.exists() and not force:
        typer.secho(
            f"File exists: {test_path}. Use --force to overwrite.", fg=typer.colors.RED
        )
        raise typer.Exit(3)

    write_file(uc_path, content, exist_ok=False, overwrite=True if force else False)
    write_file(
        test_path, test_content, exist_ok=False, overwrite=True if force else False
    )
    typer.secho(f"Generated use case '{cls}' at {uc_path}", fg=typer.colors.GREEN)
    typer.secho(f"Generated test at {test_path}", fg=typer.colors.GREEN)


@generate_app.command("port")
def generate_port(
    name: str = typer.Argument(..., help="Port name (e.g., Payment)"),
    package: Optional[str] = typer.Option(
        None, help="Package name under src/. If omitted, auto-detect."
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite existing files"),
):
    """
    Generate a port protocol, an in-memory adapter, and a minimal test.
    """
    name = str(name)
    snake = _to_snake(name)
    cls = _to_camel(name)
    root = Path(".").resolve()
    pkg = package or _detect_package(root)
    if not pkg:
        typer.secho("Could not determine package. Pass --package.", fg=typer.colors.RED)
        raise typer.Exit(2)

    port_path = root / "src" / pkg / "ports" / f"{snake}.py"
    adapter_dir = root / "src" / pkg / "adapters" / "inmemory"
    adapter_path = adapter_dir / f"{snake}.py"
    test_path = root / "tests" / f"test_{snake}_port.py"

    port_content = render_text("generate/port_protocol.py.j2", {"ClassName": cls})
    adapter_content = render_text("generate/adapter_inmemory.py.j2", {"ClassName": cls})
    test_content = render_text(
        "generate/test_port.py.j2",
        {"package_name": pkg, "snake_name": snake, "ClassName": cls},
    )

    for p in [port_path, adapter_path, test_path]:
        if p.exists() and not force:
            typer.secho(
                f"File exists: {p}. Use --force to overwrite.", fg=typer.colors.RED
            )
            raise typer.Exit(3)

    write_file(
        port_path, port_content, exist_ok=False, overwrite=True if force else False
    )
    write_file(
        adapter_path,
        adapter_content,
        exist_ok=False,
        overwrite=True if force else False,
    )
    write_file(
        test_path, test_content, exist_ok=False, overwrite=True if force else False
    )
    typer.secho(f"Generated port '{cls}Port' at {port_path}", fg=typer.colors.GREEN)
    typer.secho(f"Generated in-memory adapter at {adapter_path}", fg=typer.colors.GREEN)
    typer.secho(f"Generated test at {test_path}", fg=typer.colors.GREEN)
