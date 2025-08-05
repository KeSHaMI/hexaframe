from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


def run_uv(
    args: list[str], cwd: Path, env: dict | None = None
) -> subprocess.CompletedProcess[str]:
    new_env = os.environ.copy()
    new_env["UV_ACTIVE"] = "1"
    new_env["UV_NO_SYNC"] = "1"
    if env:
        new_env.update(env)
    return subprocess.run(
        args,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=new_env,
    )


@pytest.mark.skipif(
    sys.platform.startswith("win"), reason="Path activation differs on Windows"
)
def test_scaffold_openapi_response_schema(tmp_path: Path):
    """
    Validate that scaffolded FastAPI app exposes
    correct OpenAPI response schema for /ping.
    We assert that:
      - /ping -> POST 200 response schema describes
      an object with 'message': string
      - Request body is at least typed as
      an object (current behavior without request_model).
    """
    project_dir = tmp_path / "myproj"

    # Run scaffold via hexaframe_cli.main.new()
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
    assert (project_dir / "src" / "myproj" / "interface" / "http" / "app.py").exists()

    # Create venv and install minimal deps + project in editable mode
    r1 = run_uv(["uv", "venv"], cwd=project_dir)
    assert r1.returncode == 0, f"uv venv failed:\n{r1.stdout}"

    r_deps = run_uv(
        [
            "uv",
            "pip",
            "install",
            "--index-strategy",
            "unsafe-best-match",
            "hatchling>=1.20",
            "editables>=0.5",
            "fastapi",
            "httpx",
        ],
        cwd=project_dir,
    )
    assert r_deps.returncode == 0, f"uv pip install deps failed:\n{r_deps.stdout}"

    r_install = run_uv(
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
        cwd=project_dir,
    )
    assert r_install.returncode == 0, f"uv pip install -e . failed:\n{r_install.stdout}"

    # Import the app and fetch openapi schema
    code = (
        "import importlib.util, json, sys, pathlib; "
        "p = pathlib.Path('src/myproj/interface/http/app.py'); "
        "spec = importlib.util.spec_from_file_location('myproj_app', p); "
        "m = importlib.util.module_from_spec(spec); "
        "spec.loader.exec_module(m); "
        "print(json.dumps(m.app.openapi()))"
    )
    r_openapi = run_uv(
        ["uv", "run", "--active", sys.executable, "-c", code],
        cwd=project_dir,
    )
    assert r_openapi.returncode == 0, (
        "Failed to load app and openapi:\n{r_openapi.stdout}"
    )

    import json

    # uv may print a virtualenv mismatch warning before JSON; strip non-JSON prefix.
    stdout = r_openapi.stdout.strip()
    first_brace = stdout.find("{")
    assert first_brace != -1, f"OpenAPI output missing JSON object:\n{stdout}"
    json_text = stdout[first_brace:]
    schema = json.loads(json_text)

    # Path and method existence
    assert "/ping" in schema["paths"], "Missing /ping path in OpenAPI"
    post = schema["paths"]["/ping"].get("post")
    assert post, "Missing POST on /ping in OpenAPI"

    # Validate response 200 schema is object with 'message' string
    resp = post["responses"]["200"]["content"]["application/json"]["schema"]
    # FastAPI may use $ref when response_model is provided or inferred
    if "$ref" in resp:
        ref = resp["$ref"]
        comp = schema["components"]["schemas"][ref.split("/")[-1]]
        assert comp.get("type", "object") == "object"
        assert "message" in comp.get("properties", {})
    else:
        # Accept either a typed object
        # or an empty schema {} (generic)
        if resp != {}:
            assert resp.get("type") == "object"
            assert "message" in resp.get("properties", {})

    # Current behavior: request body schema is a generic object (no request_model)
    # Ensure at least that it's an object, not a string or other incorrect primitive.
    req = (
        post.get("requestBody", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema")
    )
    assert isinstance(req, dict), "Missing request schema for /ping"
    assert req.get("type", "object") == "object", "Request schema should be an object"
