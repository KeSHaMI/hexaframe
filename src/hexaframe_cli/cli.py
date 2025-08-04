from __future__ import annotations

from typing import Optional

import typer

from .commands.dx import runserver_cmd, test_cmd
from .commands.generate import generate_app
from .commands.new import new_cmd

app = typer.Typer(help="Hexaframe scaffolding CLI")
app.add_typer(generate_app, name="generate")


@app.command("new")
def new(  # thin wrapper to keep command name stable
    project_name: str = typer.Argument(..., help="Project directory name"),
    http: str = typer.Option(
        "fastapi", help="HTTP adapter to scaffold (fastapi|flask|none)"
    ),
    db: str = typer.Option("none", help="Database integration (none|sqlite|postgres)"),
    tests: str = typer.Option("pytest", help="Testing framework (pytest)"),
    package: Optional[str] = typer.Option(
        None, help="Python package name (default: project_name)"
    ),
    sample: bool = typer.Option(True, help="Include sample domain/use case"),
):
    new_cmd(
        project_name=str(project_name),
        http=str(http),
        tests=str(tests),
        package=None if package is None else str(package),
        sample=bool(sample),
        db=str(db),
    )


@app.command("runserver")
def runserver(
    host: str = typer.Option("127.0.0.1", help="Bind host"),
    port: int = typer.Option(8000, help="Bind port"),
    reload: bool = typer.Option(True, help="Enable auto-reload where supported"),
):
    """
    Run the HTTP server for the current project (FastAPI supported).
    """
    runserver_cmd(host=host, port=port, reload=reload)


@app.command("test")
def test(
    extra_args: Optional[str] = typer.Option(
        None, help="Extra args to pass to pytest, e.g. '-q -k test_something'"
    ),
):
    """
    Run tests for the current project (pytest).
    """
    test_cmd(extra_args=extra_args)


def main():
    app()


__all__ = ["app", "main"]
