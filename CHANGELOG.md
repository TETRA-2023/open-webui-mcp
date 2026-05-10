# Changelog

All notable changes to this fork are documented here. The wrapper source itself is vendored verbatim from upstream — entries below describe TETRA-side packaging changes.

## [0.2.2-2] — 2026-05-10

Re-snapshot of `patches/specs/open-webui.openapi.json` from `chat.tetra-ai.fr` after `0.2.2-1` shipped. The earlier snapshot lagged live OWUI by a few minutes and missed: 1 removed op (`GET /api/v1/retrieval/`), 4 operationId renames on `/openai/{path}` per-method, and body-schema drift on `/api/v1/evaluations/feedback` (POST + `{id}/POST`) and `/api/v1/users/default/permissions` (GET + POST). All four classes detected by the new drift tooling shipped in `dbd40d7`. Drift report after re-snapshot: clean, 459 shared ops with no body-schema deltas.

### Updated (TETRA-side)
- `patches/specs/open-webui.openapi.json` — re-captured from `https://chat.tetra-ai.fr/openapi.json` on 2026-05-10. Net diff vs `-1`: -1 op, 4 operationId renames, 4 schema bodies updated.

## [0.2.2-1] — 2026-05-10

TETRA-side OpenAPI spec patch on top of unchanged upstream pin `85d88af`. Upstream's bundled snapshot (committed 2026-04-07) lags the OpenWebUI version we deploy: live `chat.tetra-ai.fr` `/openapi.json` reports 460 operations vs. 422 bundled, with body-schema additions to `/api/v1/auths/admin/config` (new required `ENABLE_AUTOMATIONS`, `ENABLE_CALENDAR`) that block configuration writes through the wrapper. Default policy in CONTRIBUTING.md is to wait for upstream re-snapshot, but upstream has not moved since the initial pin, so this release applies the documented fallback (b): snapshot the spec ourselves.

### Added (TETRA-side)
- `patches/specs/open-webui.openapi.json` — OpenAPI snapshot captured from `https://chat.tetra-ai.fr/openapi.json` on 2026-05-10. 957 KB, 2-space indent, sort_keys to match upstream formatting.
- `Dockerfile` — `COPY patches/specs/open-webui.openapi.json` overwrites the upstream-bundled spec at image build, after the byte-identical `COPY src/`. Source tree under `src/openwebui_mcp/specs/` remains byte-identical to the upstream pin.

### Tag scheme
This release introduces the `-N` suffix scheme contemplated in CONTRIBUTING.md for downstream-only patches that ship without bumping the upstream SHA pin. `pyproject.toml` `project.version` stays `0.2.2` (byte-identical to upstream); the git tag is `v0.2.2-1`. Image tags published: `:stable`, `:0.2.2-1`.

## [0.2.2] — 2026-05-09

Initial TETRA fork. Image tag matches upstream `pyproject` version verbatim — by design, since this fork does not patch wrapper source. Future releases require a new upstream SHA pin (see CONTRIBUTING.md).

### Vendored
- Imported `src/openwebui_mcp/`, `Dockerfile`, `pyproject.toml`, `uv.lock`, `LICENSE`, and `tests/` from `stephanschielke/open-webui-mcp-server@85d88af6e3dd34183a5a0eefb85d474f3e3c2b54` (HEAD of upstream `main` as of 2026-05-09; upstream `pyproject` version `0.2.2`).

### Added (TETRA-side)
- `NOTICE` — fork attribution + modification log.
- `README.md` — deployment instructions, drift-check usage, image tag policy.
- `CONTRIBUTING.md` — upstream-bump procedure, drift-check workflow.
- `SECURITY.md` — disclosure policy.
- `.github/workflows/ci.yml` — gitleaks scan + Docker build validation on PR + `:latest` publish on push to `main`.
- `.github/workflows/release-image.yml` — tag-driven `:stable` + `:<version>` publish on `v*.*.*`.
- `scripts/check-spec-drift.sh` — diff bundled OpenAPI snapshot against a live OpenWebUI's `/openapi.json`.
- `.gitignore`, `.dockerignore`.

No source-level changes to the wrapper. All of `src/openwebui_mcp/` is byte-identical to the imported commit.
