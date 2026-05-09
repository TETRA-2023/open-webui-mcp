# Contributing to open-webui-mcp

This is a vendored fork of `stephanschielke/open-webui-mcp-server`. We do not maintain wrapper-source changes here — everything under `src/openwebui_mcp/` is byte-identical to the imported upstream commit. Our work in this repo is limited to: vendoring, packaging, CI/release, and operational documentation.

## Repository layout

```
src/openwebui_mcp/           vendored verbatim from upstream @ pinned SHA
src/openwebui_mcp/specs/     bundled OpenAPI snapshot (~872 KB) — drives tool generation
Dockerfile                   vendored verbatim from upstream
pyproject.toml               vendored verbatim from upstream (do NOT patch project.version)
uv.lock                      vendored verbatim from upstream
LICENSE                      vendored verbatim from upstream (MIT)
NOTICE                       fork attribution + modification log
.github/workflows/           TETRA fleet release pipeline
scripts/check-spec-drift.sh  drift-detection helper
tests/                       vendored upstream integration tests (require docker-compose; not run in CI)
```

Vendored files must stay byte-identical to upstream so a future re-vendor is a clean overwrite. Our release identifier is carried by the git tag (`v<upstream-version>-tetra<N>`), not by patching upstream version strings.

## When to bump the upstream pin

Bump in two situations:

1. **Upstream commits substantive changes** to `src/openwebui_mcp/` or to the bundled `specs/open-webui.openapi.json` — typically when the upstream maintainer re-snapshots the OpenWebUI OpenAPI spec for a new OWUI release.
2. **We bump the OpenWebUI image in `TETRA-OPEN-WEBUI/docker-compose.yml`**. The bundled spec must match the running OWUI; otherwise the wrapper will advertise tool signatures that drift from what live OWUI accepts.

These often go together but not always. Run the drift check (below) to decide.

## Bump procedure

1. **Pre-flight drift check** against the OWUI version we are about to deploy:

   ```bash
   WEBUI_API_KEY=... ./scripts/check-spec-drift.sh https://owui.example.com
   ```

   Reports added / removed / changed operations between the bundled snapshot and the target OWUI's live `/openapi.json`.

2. **Identify the next upstream SHA** that matches the target OWUI:

   ```bash
   gh api repos/stephanschielke/open-webui-mcp-server/branches/main \
     --jq '{sha: .commit.sha, date: .commit.commit.committer.date}'
   ```

   Cross-check whether the upstream maintainer has refreshed `src/openwebui_mcp/specs/open-webui.openapi.json` for the target OWUI. If not, decide whether to (a) wait, (b) snapshot the spec ourselves into a downstream-only patch (small `Dockerfile` mod), or (c) accept the drift and tighten T07 smoke coverage. Default is (a).

3. **Re-vendor at the new SHA** (keep `src/`, `pyproject.toml`, `uv.lock`, `Dockerfile`, `LICENSE` byte-identical to upstream):

   ```bash
   SHA=<new-sha>
   BASE=https://raw.githubusercontent.com/stephanschielke/open-webui-mcp-server/$SHA
   for f in src/openwebui_mcp/__init__.py src/openwebui_mcp/main.py \
            src/openwebui_mcp/auth.py src/openwebui_mcp/openapi_provider.py \
            src/openwebui_mcp/specs/open-webui.openapi.json \
            Dockerfile pyproject.toml uv.lock LICENSE \
            tests/__init__.py tests/test_integration.py ; do
     curl -fsSL "$BASE/$f" -o "$f"
   done
   ```

4. **Re-run the T01 source audit** (see US #871 audit report for the template). Re-classify any new / changed operations. Update `NOTICE` with the new SHA.

5. **Update CHANGELOG** with an entry naming the new SHA and the OWUI version it targets. We do **not** patch `pyproject.toml`'s `project.version` — that field is kept byte-identical to upstream. The git tag matches the upstream version verbatim.

6. **Commit and tag**:

   ```bash
   git commit -am "chore: re-pin upstream to <new-sha> for OWUI <x.y.z>"
   git tag v<upstream-version>      # e.g., v0.2.3
   git push --follow-tags
   ```

   The `Release Image` workflow publishes `:stable` + `:<tag-without-leading-v>` to ghcr.io (e.g., `:0.2.3`).

   *Edge case*: if a TETRA-side change (CI workflow, drift script, README) needs to ship without an upstream pin bump, force-retag (delete `v<version>` then re-tag) — accepted because it only re-publishes a deterministic build of the same vendored source. Note this in the CHANGELOG entry. If this becomes frequent, reintroduce a `-tetraN` suffix scheme.

7. **Smoke** with the new image against staging OWUI, then bump both `open-webui` and `open-webui-mcp` image pins in `TETRA-OPEN-WEBUI/docker-compose.yml` together.

## What we do **not** patch in this repo

- The wrapper's tool generation logic (`openapi_provider.py`).
- The auth middleware (`auth.py`).
- The OpenWebUI OpenAPI snapshot — we use whatever upstream ships at the pinned SHA. If the snapshot is wrong for our running OWUI, we wait for upstream or fork upward.

If you're reaching for a wrapper-source change, that probably belongs upstream.

## Releasing

- `:latest` publishes automatically on every push to `main` (CI `docker` job).
- `:stable` + `:<version>` publish on `v*.*.*` git tags (Release Image workflow).
- Space tag-driven releases ≥30 min apart per fleet convention.

## License

MIT — same as upstream. See `LICENSE` and `NOTICE`.
