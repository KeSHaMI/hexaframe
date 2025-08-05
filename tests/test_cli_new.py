from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


def run_uv(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """
    Run a command via uv run (for Python execution) or bare uv for pip/venv if needed.
    For scaffolding tests we only need to run pytest in the generated project.

    We set UV_ACTIVE=1 to force uv to use the environment in cwd ('.venv'), avoiding
    conflicts with the repository-level VIRTUAL_ENV that CI may export.
    """
    env = os.environ.copy()
    env["UV_ACTIVE"] = "1"
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


@pytest.mark.skipif(
    sys.platform.startswith("win"), reason="Path activation differs on Windows"
)
def test_cli_scaffold_includes_option_deps_in_pyproject(tmp_path: Path):
    """
    Ensure scaffolded pyproject.toml includes dependencies based on chosen options:
    - Default http=fastapi => fastapi and uvicorn are included
    - tests=pytest => pytest, pytest-cov, pytest-asyncio, httpx are included
    - db=postgres => sqlalchemy and asyncpg are included
    """
    project_dir = tmp_path / "myproj"

    # Run scaffolder with explicit options to validate all conditionals
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path("src").resolve())
    create = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; sys.path.insert(0, r'%s'); "
                "from hexaframe_cli.main import new; "
                "new(project_name='myproj', http='fastapi', tests='pytest', "
                "package=None, sample=True, db='postgres')"
            )
            % str(Path("src").resolve()),
        ],
        cwd=str(tmp_path),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert create.returncode == 0, f"CLI new failed:\n{create.stdout}"

    pyproject_path = project_dir / "pyproject.toml"
    assert pyproject_path.exists(), "pyproject.toml not created"

    content = pyproject_path.read_text()

    # HTTP deps
    assert "fastapi>=" in content, "fastapi dependency missing in pyproject.toml"
    assert "uvicorn[standard]>=" in content, "uvicorn[standard] dependency missing"

    # Test deps
    assert "pytest>=" in content, "pytest dependency missing"
    assert "pytest-cov>=" in content, "pytest-cov dependency missing"
    assert "pytest-asyncio>=" in content, "pytest-asyncio dependency missing"
    assert "httpx>=" in content, "httpx dependency missing"

    # DB deps (postgres)
    assert "sqlalchemy>=" in content, "sqlalchemy dependency missing for postgres"
    assert "asyncpg>=" in content, "asyncpg dependency missing for postgres"


@pytest.mark.skipif(
    sys.platform.startswith("win"), reason="Path activation differs on Windows"
)
def test_cli_scaffold_generates_docker_and_db_files_when_postgres(tmp_path: Path):
    """
    When db='postgres' (now default), the scaffolder must generate:
      - docker-compose.yml, Dockerfile, .env
      - alembic.ini, alembic/env.py, alembic/versions/
      - src/<pkg>/app/db/{config.py, base.py, session.py}
      - src/<pkg>/app/di.py
      - src/<pkg>/app/usecases/pong.py
      - README.md with DB/docker instructions
    """
    project_dir = tmp_path / "myproj"

    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path("src").resolve())

    # Use explicit db='postgres' to be robust to future default changes
    create = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; sys.path.insert(0, r'%s'); "
                "from hexaframe_cli.main import new; "
                "new(project_name='myproj', http='fastapi', tests='pytest', "
                "package=None, sample=True, db='postgres')"
            )
            % str(Path("src").resolve()),
        ],
        cwd=str(tmp_path),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert create.returncode == 0, f"CLI new failed:\n{create.stdout}"

    pkg = "myproj"

    # Docker and env
    assert (project_dir / "docker-compose.yml").exists(), "docker-compose.yml missing"
    assert (project_dir / "Dockerfile").exists(), "Dockerfile missing"
    assert (project_dir / ".env").exists(), ".env missing"

    # Alembic
    assert (project_dir / "alembic.ini").exists(), "alembic.ini missing"
    assert (project_dir / "alembic" / "env.py").exists(), "alembic/env.py missing"
    assert (project_dir / "alembic" / "versions").exists(), "alembic/versions missing"

    # App DB scaffolding
    assert (project_dir / "src" / pkg / "app" / "db" / "config.py").exists()
    assert (project_dir / "src" / pkg / "app" / "db" / "base.py").exists()
    assert (project_dir / "src" / pkg / "app" / "db" / "session.py").exists()

    # DI + Usecase
    assert (project_dir / "src" / pkg / "app" / "di.py").exists()
    assert (project_dir / "src" / pkg / "app" / "usecases" / "pong.py").exists()

    # README should exist (overwritten with docker instructions)
    assert (project_dir / "README.md").exists()

    # Sanity check: FastAPI app still exists
    assert (project_dir / "src" / pkg / "interface" / "http" / "app.py").exists()
    assert (project_dir / "tests" / "test_app.py").exists()


def test_cli_scaffold_auto_setup_env(tmp_path: Path):
    """
    Ensure `hexaframe new` auto-creates a venv and installs the project
    using the unsafe-best-match index strategy, so users can run immediately.
    """
    project_dir = tmp_path / "myproj"

    # Invoke the CLI by running the module with Python, pointing PYTHONPATH to our src
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path("src").resolve())

    # Create the project (this should perform auto-setup: uv venv + installs)
    create = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; sys.path.insert(0, r'%s'); "
                "from hexaframe_cli.main import new; "
                "new(project_name='myproj', http='fastapi', tests='pytest', "
                "package=None, sample=True, db='postgres')"
            )
            % str(Path("src").resolve()),
        ],
        cwd=str(tmp_path),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert create.returncode == 0, f"CLI new failed:\n{create.stdout}"

    # Validate the venv exists
    assert (project_dir / ".venv").exists(), "Auto-created .venv is missing"

    # Validate editable install resulted in an
    # importable package by running pytest in-project venv
    # Use UV_ACTIVE=1 to target the project venv and avoid repo-level virtual envs.
    # Include index strategy to resolve deps across PyPI and TestPyPI.
    # Use --no-build-isolation to avoid setuptools legacy
    # build quirks from TestPyPI artifacts,
    # and include index strategy to resolve across indexes.
    # Force uv to use the project's venv and avoid rebuilding deps on run
    env2 = os.environ.copy()
    env2["UV_ACTIVE"] = "1"
    env2["UV_NO_SYNC"] = "1"
    r = subprocess.run(
        [
            "uv",
            "run",
            "--no-build-isolation",
            "--index-strategy",
            "unsafe-best-match",
            "pytest",
            "-q",
        ],
        cwd=str(project_dir),
        env=env2,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert r.returncode == 0, f"Auto-setup environment tests failed:\n{r.stdout}"


@pytest.mark.skipif(
    sys.platform.startswith("win"), reason="Path activation differs on Windows"
)
def test_cli_scaffold_fastapi_sample(tmp_path: Path):
    # Arrange: create a simple runner that invokes our CLI module directly
    # We avoid installing console scripts; import and call main using python -m.
    project_dir = tmp_path / "myproj"

    # Invoke the CLI by running the module with Python, pointing PYTHONPATH to our src
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path("src").resolve())

    # Create the project
    create = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; sys.path.insert(0, r'%s'); "
                "from hexaframe_cli.main import new; "
                "new(project_name='myproj', http='fastapi', tests='pytest', "
                "package=None, sample=True)"
            )
            % str(Path("src").resolve()),
        ],
        cwd=str(tmp_path),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert create.returncode == 0, f"CLI new failed:\n{create.stdout}"

    # Assert files exist
    assert (project_dir / "README.md").exists()
    assert (project_dir / "src" / "myproj" / "interface" / "http" / "app.py").exists()
    assert (project_dir / "tests" / "test_app.py").exists()

    # Install minimal deps and run tests inside the scaffold (using uv)
    # Note: This uses uv if available in PATH.
    r1 = run_uv(["uv", "venv"], cwd=project_dir)
    assert r1.returncode == 0, f"uv venv failed:\n{r1.stdout}"

    # Install the scaffolded project itself so `myproj` is importable, and test deps
    # Install test deps first, then install the local package in editable mode
    r2b = run_uv(
        [
            "uv",
            "pip",
            "install",
            # allow resolving packages across all configured indexes
            "--index-strategy",
            "unsafe-best-match",
            # build backend for editable install
            "hatchling>=1.20",
            # ensure editable support is present for hatchling editable builds
            "editables>=0.5",
            # runtime + test deps
            "fastapi",
            "pytest",
            "pytest-asyncio",
            "httpx",
        ],
        cwd=project_dir,
    )
    assert r2b.returncode == 0, f"uv pip install deps failed:\n{r2b.stdout}"

    # Install the scaffolded project itself so `myproj` is importable
    # Use --no-build-isolation to prevent uv from trying
    # to resolve workspace-only deps (like private 'hexaframe')
    r2 = run_uv(
        [
            "uv",
            "pip",
            "install",
            "--no-build-isolation",
            # allow resolving packages across all
            # configured indexes when building editable
            "--index-strategy",
            "unsafe-best-match",
            "-e",
            ".",
        ],
        cwd=project_dir,
    )
    assert r2.returncode == 0, f"uv pip install -e . failed:\n{r2.stdout}"

    # Ensure uv targets the newly-created project venv
    # and does not try to resolve workspace deps
    # We already set UV_ACTIVE=1 in run_uv(), so running from project_dir is enough.
    # Explicitly pass UV_NO_SYNC=1 to avoid background dependency sync attempts in CI.
    os.environ["UV_NO_SYNC"] = "1"
    r3 = run_uv(["uv", "run", "pytest", "-q"], cwd=project_dir)
    assert r3.returncode == 0, f"scaffolded tests failed:\n{r3.stdout}"
