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
    """
    return subprocess.run(
        cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )


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
    r2 = run_uv(["uv", "pip", "install", "-e", "."], cwd=project_dir)
    assert r2.returncode == 0, f"uv pip install -e . failed:\n{r2.stdout}"
    r2b = run_uv(
        ["uv", "pip", "install", "fastapi", "pytest", "pytest-asyncio", "httpx"],
        cwd=project_dir,
    )
    assert r2b.returncode == 0, f"uv pip install deps failed:\n{r2b.stdout}"

    r3 = run_uv(["uv", "run", "pytest", "-q"], cwd=project_dir)
    assert r3.returncode == 0, f"scaffolded tests failed:\n{r3.stdout}"
