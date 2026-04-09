# Repo Split Plan

## Goal

Promote `apps/ollama-bridge/` into its own public GitHub repository with its own releases.

## Candidate Repository

- repo name: `webmasteros-ollama-bridge`
- visibility: `public`
- release channel: GitHub Releases

## What Moves With The Split

- `bridge.py`
- `pyproject.toml`
- `config/`
- `packaging/`
- `.github/workflows/`
- `README.md`
- `INSTALLER-PLAN.md`
- `FIRST-RUN-CONFIG.md`
- `CHANGELOG.md`
- `LICENSE-NOTICE.md`
- release build and installer docs

## What Stays Here

- browser-extension integration code
- product-strategy docs for the full WebmasterOS stack
- monorepo orchestration and release wiring for the other software surfaces

## Release Model

- `webmasteros-ollama-bridge` gets its own versioning and changelog
- binaries and installer artifacts publish through its own GitHub Releases
- the main WebmasterOS repo consumes released bridge artifacts instead of treating the helper as plugin-local code

## Split Trigger

The split should happen before public community contribution is invited so issue tracking, pull requests, and release notes all land in the helper's own repository from the start.
