# Changelog

All notable changes to this fork are documented here. The wrapper source itself is vendored verbatim from upstream — entries below describe TETRA-side packaging changes.

## [0.2.2-tetra1] — 2026-05-09

Initial TETRA fork.

### Vendored
- Imported `src/openwebui_mcp/`, `Dockerfile`, `pyproject.toml`, `uv.lock`, `LICENSE`, and `tests/` from `stephanschielke/open-webui-mcp-server@85d88af6e3dd34183a5a0eefb85d474f3e3c2b54` (HEAD of upstream `main` as of 2026-05-09; upstream `pyproject` version `0.2.2`).

### Added (TETRA-side)
- `NOTICE` — fork attribution + modification log.
- `README.md` — TETRA fleet deployment instructions.
- `CONTRIBUTING.md` — upstream-bump procedure, drift-check workflow.
- `SECURITY.md` — disclosure policy.
- `.github/workflows/ci.yml` — gitleaks scan + Docker build validation on PR + `:latest` publish on push to `main`.
- `.github/workflows/release-image.yml` — tag-driven `:stable` + `:<version>` publish on `v*.*.*`.
- `scripts/check-spec-drift.sh` — diff bundled OpenAPI snapshot against a live OpenWebUI's `/openapi.json`.
- `.gitignore`, `.dockerignore`.

No source-level changes to the wrapper. All of `src/openwebui_mcp/` is byte-identical to the imported commit.
