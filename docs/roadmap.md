# Hexaframe Roadmap

Goal: A Python framework and scaffolding toolkit to build and test hexagonal (ports & adapters) architecture applications with strong developer ergonomics and testing-first experience.

## Current Status Snapshot

Implemented (present with tests where noted):
- Core (Step A):
  - Result/Either with Ok/Err and helpers (sync + async): src/hexaframe/result.py; tests in tests/test_result.py.
  - Error hierarchy with code/message/details: src/hexaframe/errors.py; tests in tests/test_errors.py.
  - Use case bases (sync/async) with hooks and error capture: src/hexaframe/use_case.py; tests in tests/test_use_case_base.py.
  - Ports protocols: LoggerPort, ClockPort, UuidPort in src/hexaframe/ports.py.
  - UnitOfWork protocol with sync/async context hooks: src/hexaframe/uow.py.
  - Common types and to_serializable: src/hexaframe/types.py.
  - DI utilities: src/hexaframe/di.py; tests in tests/test_di.py.
- Adapters (Step B):
  - FastAPI adapter build_router with error mapping: src/hexaframe_fastapi/adapter.py; tests in tests/test_fastapi_adapter.py.
  - Decorators module present: src/hexaframe_fastapi/decorators.py; endpoint helper present: src/hexaframe/endpoint.py.
  - Example app: examples/quickstart/app.py.
- TestKit (partial Step C):
  - Base testkit module: src/hexaframe/testkit.py; tests in tests/test_testkit.py.
- CLI (Step D):
  - Typer CLI with new/generate: src/hexaframe_cli/*; tests in tests/test_cli_new.py and tests/test_cli_generate.py.
  - Templates for project and generators in src/hexaframe_cli/templates/*.

## What’s Left (Gaps vs Roadmap)

Step A – Core polishing
- Add tests that exercise UnitOfWork protocol semantics for both sync and async context-manager flows (begin/commit/rollback, error paths).
- Extend to_serializable tests for dataclasses, enums, datetime, mappings, and sequence edge cases.

Step B – Adapters and decorators
- Flask adapter: implement optional Flask/WSGI adapter mirroring FastAPI behavior (request parsing, output mapping, error mapping).
- Decorators/DX:
  - Ensure decorators expose @endpoint/@use_case ergonomics with ability to register input/output schemas and documented errors.
  - Add/expand tests for decorators, including async routes.
- Error/status coverage:
  - Confirm/customize mappings for authentication (401) and any additional domain/infra cases as needed.
- Keep Pydantic v2 usage within adapters; document that core remains dependency-free.

Step C – Testing-first experience
- TestKit expansions:
  - InMemoryRepository base and InMemoryEventBus.
  - FakeClock (implements ClockPort) and StubUuid (implements UuidPort).
  - TestHarness to execute use cases with fakes and capture logs/events.
- Pytest fixtures:
  - Provide fixtures for app container and FastAPI http_client.
  - Example tests: unit (domain rule), use case with mocked ports, integration (in-memory repo), E2E (FastAPI test client).

Step D – CLI scaffolder
- hexaframe new options matrix:
  - Implement/validate flags: --http fastapi|flask|none; --db none|sqlite|postgres; --tests pytest; --package org.name; --sample.
  - Expand templates to support DB choices and sample domain (e.g., todos) with tests.
- DX commands:
  - hexaframe runserver (when http selected).
  - hexaframe test (pytest wrapper).
- Ensure generate commands and templates fully support both sync and async usecases and ports; validate via tests.

Step 5 – Developer ergonomics (DX)
- Result helpers: optional pattern helpers beyond fold (if desired).
- Validation story: document pure validation in core and pydantic-based parsing in adapters with examples.
- Observability:
  - Logger adapters for stdlib logging, structlog, and loguru implementing LoggerPort.
  - Optional OpenTelemetry hooks (tracing/metrics).

Step 6 – Documentation and examples
- Documentation:
  - Expand README (positioning, why hexagonal, when to use).
  - Concepts: ports/adapters, use cases, DTOs, error handling, transactions, testing strategy.
  - Recipes: pagination, auth, idempotency, background jobs.
  - Quickstart: a 5-minute todo app walkthrough.
- Examples:
  - examples/fastapi-todos (sqlite + in-memory) with tests.
  - examples/orders (postgres + events) with tests.

Step 7 – Opinionated defaults with escape hatches
- Defaults:
  - FastAPI as default web adapter.
  - In-memory repo as default persistence.
  - Optional SQLAlchemy adapter example for persistence.
- Configuration:
  - pydantic-settings driven config in adapters, overridable via env; document usage.

Step 8 – Versioning and stability
- Project policy:
  - Start with 0.x and mark adapters as “experimental”.
  - Add CHANGELOG.md and a migration guide skeleton.
  - Document SemVer adherence and stability goals.

## Incremental Implementation Plan (Updated)

A) Core polishing
- Add UnitOfWork sync/async tests.
- Extend to_serializable edge-case tests.

B) FastAPI adapter and decorators
- Harden decorators with tests; confirm async coverage.
- Decide on and schedule Flask adapter (can be deferred).

C) TestKit and pytest
- Implement InMemoryRepository/EventBus, FakeClock, StubUuid, and TestHarness.
- Publish pytest fixtures and add example tests.

D) CLI scaffolder
- Complete new options matrix and templates (db choices, sample domain).
- Add runserver and test commands.
- Ensure generate commands produce compilable sync/async code; extend tests.

E) Docs and examples
- Expand README and add Concepts/Recipes.
- Build Quickstart todo, fastapi-todos, and orders examples with tests.

F) Observability and defaults
- Implement logger adapters; optional OTEL hooks.
- Add pydantic-settings-based config and SQLAlchemy example.

G) Versioning
- Introduce CHANGELOG and clarify experimental status and SemVer policy.
