# HexaFrame

HexaFrame is a lightweight Python framework and CLI for building applications using Hexagonal Architecture (Ports & Adapters). It provides:
- Small core primitives for use cases, results, ports, adapters, DI and units-of-work
- A FastAPI integration layer (optional)
- A scaffolding CLI to bootstrap new projects and generate use cases, ports, and adapters
- A testkit to simplify testing your domain and adapters

This README documents setup, usage, and project structure based on the current codebase.

## Packages in this repo

This repository is a monorepo that ships three installable packages from `src/`:

- `hexaframe`: core primitives for hexagonal architecture
  - src/hexaframe/
- `hexaframe-fastapi`: integration helpers for FastAPI
  - src/hexaframe_fastapi/
- `hexaframe-cli`: project scaffolding and code generation CLI
  - src/hexaframe_cli/

There is also:
- `tests/`: full test suite for the framework and CLI

Python: 3.10–3.12

## Install

Install from source in editable mode:

```bash
# in repo root
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -U pip

# Install core + extras for dev and example
pip install -e ".[dev,example]"
```

This installs:
- Core: pydantic, dependency-injector, jinja2
- Dev: ruff, pytest, pytest-cov
- Example-only deps: fastapi, uvicorn, sqlalchemy, etc. (for examples/quickstart)

If you only want the CLI while developing locally:
```bash
pip install -e .
```

## Quick start

See the CLI section below to scaffold a new project and run it locally. The repository ships no example applications.

## CLI

The CLI provides project scaffolding and code generation using Typer.

Entrypoints:
- Module: `python -m hexaframe_cli`
- Console script (if installed as a package): `hexaframe-cli` (depends on your environment)
- In-repo module path: `python -m src.hexaframe_cli` also works when running from source tree

Top-level help:
```bash
python -m hexaframe_cli --help
```

### Create a new project

```bash
python -m hexaframe_cli new myapp \
  --http fastapi \
  --tests pytest \
  --package myapp \
  --sample true
```

Arguments and options (from src/hexaframe_cli/cli.py):
- `project_name` (positional): directory name to create
- `--http` (default: fastapi): which HTTP adapter to scaffold (fastapi|none)
- `--tests` (default: pytest): which test framework to scaffold (currently pytest)
- `--package` (optional): Python package name (defaults to project_name)
- `--sample` (default: true): include a sample domain/use case

What gets created (from templates in `src/hexaframe_cli/templates/project`):
- Minimal `pyproject.toml`
- `app_fastapi.py` if `--http fastapi`
- `test_app.py` for pytest
- `.gitignore`
- README stub

### Generate domain/code artifacts

Use the `generate` subcommands:

```bash
python -m hexaframe_cli generate --help
```

Available generators (see `src/hexaframe_cli/templates/generate`):
- `usecase_sync.py.j2` and `usecase_async.py.j2`: scaffold use case interactors
- `port_protocol.py.j2`: define a domain port (protocol)
- `adapter_inmemory.py.j2`: simple in-memory adapter implementation
- Corresponding pytest templates: `test_usecase_sync.py.j2`, `test_usecase_async.py.j2`, `test_port.py.j2`

Exact command names are defined in `src/hexaframe_cli/commands/generate.py`. Use `--help` on each subcommand to see parameters once the CLI is installed.

## Core concepts (hexaframe)

Key modules:
- `use_case.py`: Base class for use cases (sync/async variants). Encapsulates a unit of business logic.
- `result.py`: A simple Result type for success/error returns that encourages explicit error handling and rich error payloads.
- `errors.py`: Error helpers used by results and FastAPI integration.
- `ports.py`: Port (protocol) definitions and helpers to define boundaries between core and adapters.
- `uow.py`: Unit of Work boundaries to coordinate transactional work across adapters.
- `di.py`: Dependency injection helpers (built on dependency-injector) to wire ports/adapters/use cases together.
- `types.py`: Shared type aliases and small utilities.
- `endpoint.py`: Base endpoint helper to expose use cases as endpoints.
- `testkit.py`: Utilities to simplify testing use cases, ports, and adapters.

Testing references:
- `tests/test_result.py`, `tests/test_errors.py`, `tests/test_use_case_base.py`: examples of Result and use case semantics
- `tests/test_di.py`: DI wiring test
- `tests/test_testkit.py`: testkit usage

## FastAPI integration (hexaframe-fastapi)

The `hexaframe_fastapi` package provides:
- `adapter.py`: Adapters to connect use cases to FastAPI routes
- `decorators.py`: Decorators to map HTTP requests to use case input/outputs
- `__init__.py`: convenience exports

See `tests/test_fastapi_adapter.py` for integration examples.

## Example: wiring a use case with FastAPI

A minimal pattern:

```python
# domain/use_case.py
from hexaframe.use_case import UseCase
from hexaframe.result import Ok, Err, Result

class CreateThing(UseCase[CreateInput, CreateOutput]):
    def execute(self, inp: CreateInput) -> Result[CreateOutput, str]:
        if not inp.name:
            return Err("empty name")
        return Ok(CreateOutput(id="123", name=inp.name))
```

```python
# app.py (FastAPI)
from fastapi import FastAPI
from hexaframe_fastapi.adapter import UseCaseRoute

app = FastAPI()
create_thing = CreateThing()

@app.post("/things")
def create_things_endpoint(body: dict):
    # basic example; in real apps validate with Pydantic models
    return UseCaseRoute(create_thing).handle(body)
```

Check `examples/quickstart/app.py` for a working reference.

## Development

### Setup dev environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev,example]"
```

### Run linters and tests

```bash
# Lint (ruff)
ruff check .

# Run tests
pytest -q

# Coverage
pytest --cov=hexaframe --cov=hexaframe_fastapi --cov=hexaframe_cli -q
```


## Project structure

```
.
├── src/
│   ├── hexaframe/           # core primitives
│   ├── hexaframe_fastapi/   # FastAPI integration
│   └── hexaframe_cli/       # CLI (Typer)
├── tests/                   # Comprehensive test suite
└── pyproject.toml           # package metadata + deps
```

## Testing philosophy

- Keep domain logic pure and testable with the `Result` type
- Define ports (protocols) to decouple domain from external systems
- Provide simple in-memory adapters for fast, hermetic tests
- Use the testkit to standardize setup/teardown and invariants

## Versioning and status

- Current version: 0.1.0 (alpha)
- MIT License
- Python 3.10–3.12

## Contributing

1. Fork and create a feature branch
2. Set up the dev environment (see above)
3. Run `ruff` and `pytest` before submitting PRs
4. Include or update tests for new behavior

## FAQ

- Why hexagonal architecture?
  - It enforces boundaries between core and infrastructure, making change safer and testing easier.
- Do I need FastAPI?
  - No. FastAPI integration is optional. You can adapt to any HTTP framework or to non-HTTP interfaces (CLI, queues, CRON) by writing adapters.
- Do I need the CLI?
  - No, but it accelerates scaffolding and keeps structure consistent.

## Links

- Roadmap: `docs/roadmap.md`
- Templates for new projects: `src/hexaframe_cli/templates/project/`
- Templates for generators: `src/hexaframe_cli/templates/generate/`
