from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import typer
from click import Command
from typer.testing import CliRunner as TyperCliRunner

from hexaframe_cli.cli import app as cli_app
from hexaframe_cli.main import new as new_programmatic


@contextmanager
def chdir(tmp: Path) -> Iterator[None]:
    prev = Path.cwd()
    os.chdir(tmp)
    try:
        yield
    finally:
        os.chdir(prev)


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _click_cmd(app: Any) -> Command:
    # Normalize Typer app to a Click command across Typer/Click versions
    if isinstance(app, typer.Typer):
        # Prefer the bound Click command on ._click_command (Typer >=0.9)
        cmd = getattr(app, "_click_command", None)
        if cmd is not None:
            return cmd
        # Fallback: Typer internally stores command in .info.command
        info = getattr(app, "info", None)
        if info is not None:
            inner = getattr(info, "command", None)
            if inner is not None:
                return inner
        # Last resort: build a click command from the typer app
        built = app._to_click_command() if hasattr(app, "_to_click_command") else None
        if built is not None:
            return built  # type: ignore[return-value]
        # As an ultimate fallback, Typer.__call__ returns a Click main function.
        # Wrap with Typer.testing helper.
        return app  # type: ignore[return-value]
    # If already a click command
    return app  # type: ignore[return-value]


def test_generate_usecase_and_port_end_to_end(tmp_path: Path):
    # Use Typer's CliRunner to avoid Click expecting .main attribute on callables
    runner = TyperCliRunner()
    _click_cmd(cli_app)

    # 1) scaffold new project into temp dir
    with chdir(tmp_path):
        project_dir = tmp_path / "demoapp"
        assert new_programmatic.__name__ == "new_cmd"  # ensure shim is hooked
        new_programmatic(
            project_name="demoapp",
            http="none",
            tests="pytest",
            package="demoapp",
            sample=False,
        )
        assert project_dir.exists()

    # 2) run generate usecase (async default), then sync variant and port
    with chdir(project_dir):
        # Ensure a src/package layout exists for package detection
        package_dir = project_dir / "src" / "demoapp"
        package_dir.mkdir(parents=True, exist_ok=True)
        (package_dir / "__init__.py").write_text("# demoapp\n", encoding="utf-8")

        # async usecase
        res = runner.invoke(
            _click_cmd(cli_app),
            ["generate", "usecase", "DoThing"],
            prog_name="hexaframe",
        )
        assert res.exit_code == 0, res.output

        # sync usecase
        res = runner.invoke(
            _click_cmd(cli_app),
            ["generate", "usecase", "ComputeValue", "--sync"],
            prog_name="hexaframe",
        )
        assert res.exit_code == 0, res.output

        # port and inmemory adapter
        res = runner.invoke(
            _click_cmd(cli_app), ["generate", "port", "Email"], prog_name="hexaframe"
        )
        assert res.exit_code == 0, res.output

        # idempotency with --force
        res = runner.invoke(
            _click_cmd(cli_app),
            ["generate", "usecase", "DoThing", "--force"],
            prog_name="hexaframe",
        )
        assert res.exit_code == 0, res.output

        # 3) verify files created under src/demoapp and tests
        # use cases
        uc_async = package_dir / "usecases" / "do_thing.py"
        uc_sync = package_dir / "usecases" / "compute_value.py"
        assert uc_async.exists(), "async usecase file missing"
        assert uc_sync.exists(), "sync usecase file missing"

        # ports
        port_proto = package_dir / "ports" / "email.py"
        adapter_inmem = package_dir / "adapters" / "inmemory" / "email.py"
        assert port_proto.exists(), "port protocol missing"
        assert adapter_inmem.exists(), "inmemory adapter missing"

        # tests
        tests_dir = project_dir / "tests"
        test_uc_async = tests_dir / "test_do_thing.py"
        test_uc_sync = tests_dir / "test_compute_value.py"
        test_port = tests_dir / "test_email_port.py"
        assert test_uc_async.exists(), "generated async usecase test missing"
        assert test_uc_sync.exists(), "generated sync usecase test missing"
        assert test_port.exists(), "generated port test missing"

        # 4) spot-check content conventions (snake/camel names present)
        async_content = _read(uc_async)
        assert "class DoThing" in async_content or "def execute" in async_content
        assert "async def" in async_content

        sync_content = _read(uc_sync)
        assert "class ComputeValue" in sync_content or "def execute" in sync_content
        assert "def execute(self" in sync_content and "async def" not in sync_content

        port_content = _read(port_proto)
        assert (
            "class Email" in port_content
            or "class IEmail" in port_content
            or "Protocol" in port_content
        )

        test_async_content = _read(test_uc_async)
        assert (
            "pytest" in test_async_content.lower()
            or "asyncio" in test_async_content.lower()
        )

        test_sync_content = _read(test_uc_sync)
        assert "def test_" in test_sync_content

        test_port_content = _read(test_port)
        assert "InMemory" in test_port_content or "inmemory" in test_port_content


def test_package_detection_and_overwrite(tmp_path: Path):
    runner = TyperCliRunner()
    _click_cmd(cli_app)

    # Create project with only pyproject.toml defining tool.poetry / project.name.
    # Or derive the package from the src directory name.
    project_dir = tmp_path / "pkgdetect"
    project_dir.mkdir(parents=True)
    (project_dir / "pyproject.toml").write_text(
        '[project]\nname = "pkgdetect"\nversion = "0.0.0"\n',
        encoding="utf-8",
    )
    src_dir = project_dir / "src" / "pkgdetect"
    src_dir.mkdir(parents=True)
    (src_dir / "__init__.py").write_text("", encoding="utf-8")

    with chdir(project_dir):
        # First generation creates file
        res = runner.invoke(
            _click_cmd(cli_app),
            ["generate", "usecase", "MakeThing"],
            prog_name="hexaframe",
        )
        assert res.exit_code == 0, res.output
        target = src_dir / "usecases" / "make_thing.py"
        assert target.exists()

        # Second generation without --force should fail or no-op with informative
        # message; we only assert non-zero exit or success with message.
        res2 = runner.invoke(
            _click_cmd(cli_app),
            ["generate", "usecase", "MakeThing"],
            prog_name="hexaframe",
        )
        # Accept either: exit_code != 0 or 0 with "exists" in output depending
        # on implementation.
        assert (res2.exit_code != 0) or ("exist" in res2.output.lower()), res2.output

        # With --force should succeed
        res3 = runner.invoke(
            _click_cmd(cli_app),
            ["generate", "usecase", "MakeThing", "--force"],
            prog_name="hexaframe",
        )
        assert res3.exit_code == 0, res3.output


def test_generate_with_package_override(tmp_path: Path):
    runner = TyperCliRunner()
    _click_cmd(cli_app)

    project_dir = tmp_path / "overridepkg"
    project_dir.mkdir()

    # Prepare multiple packages but choose one via --package
    src_dir = project_dir / "src"
    a_pkg = src_dir / "a_pkg"
    b_pkg = src_dir / "b_pkg"
    a_pkg.mkdir(parents=True)
    b_pkg.mkdir(parents=True)
    (a_pkg / "__init__.py").write_text("", encoding="utf-8")
    (b_pkg / "__init__.py").write_text("", encoding="utf-8")

    with chdir(project_dir):
        res = runner.invoke(
            _click_cmd(cli_app),
            ["generate", "usecase", "RouteOrder", "--package", "b_pkg"],
            prog_name="hexaframe",
        )
        assert res.exit_code == 0, res.output

        file_expected = b_pkg / "usecases" / "route_order.py"
        file_other = a_pkg / "usecases" / "route_order.py"
        assert file_expected.exists()
        assert not file_other.exists()
