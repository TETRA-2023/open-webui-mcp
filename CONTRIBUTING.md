# Contributing to open-webui-mcp

This is a vendored fork of `stephanschielke/open-webui-mcp-server`. We do not maintain wrapper-source changes here — everything under `src/openwebui_mcp/` is byte-identical to the imported upstream commit. Our work in this repo is limited to: vendoring, packaging, CI/release, and operational documentation.

## Repository layout

```
src/openwebui_mcp/           vendored verbatim from upstream @ pinned SHA
src/openwebui_mcp/specs/     bundled OpenAPI snapshot (~872 KB) — drives tool generation
Dockerfile                   vendored from upstream; may carry small TETRA-side patches (e.g., COPY of patches/specs/)
pyproject.toml               vendored verbatim from upstream (do NOT patch project.version)
uv.lock                      vendored verbatim from upstream
LICENSE                      vendored verbatim from upstream (MIT)
NOTICE                       fork attribution + modification log
patches/                     downstream-only assets layered over the byte-identical vendor tree at image build (see "Downstream-only spec patch" below)
.github/workflows/           release pipeline (gitleaks + lint + Docker build/publish + drift monitor + drift gate)
scripts/check-spec-drift.sh           drift-detection helper (path/method + delegation to body-schema check)
scripts/check-body-schema-drift.py    deep diff of requestBody / parameters / responses for shared ops
tests/                       vendored upstream integration tests (require docker-compose; not run in CI)
```

Vendored files must stay byte-identical to upstream so a future re-vendor is a clean overwrite. Our release identifier is carried by the git tag (which matches upstream's version verbatim), not by patching upstream version strings.

## When to bump the upstream pin

Bump in two situations:

1. **Upstream commits substantive changes** to `src/openwebui_mcp/` or to the bundled `specs/open-webui.openapi.json` — typically when the upstream maintainer re-snapshots the OpenWebUI OpenAPI spec for a new OWUI release.
2. **The OpenWebUI version your deployment runs is upgraded.** The bundled spec must match the running OWUI; otherwise the wrapper will advertise tool signatures that drift from what live OWUI accepts.

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

4. **Re-audit upstream source.** Read `src/openwebui_mcp/{main,auth,openapi_provider}.py` for any logic changes between SHAs. Inventory the operations that survive the `RouteMap` filter in `openapi_provider.py` against the bundled spec — re-classify any added / removed / renamed operations. Update `NOTICE` with the new SHA.

5. **Update CHANGELOG** with an entry naming the new SHA and the OWUI version it targets. We do **not** patch `pyproject.toml`'s `project.version` — that field is kept byte-identical to upstream. The git tag matches the upstream version verbatim.

6. **Commit and tag**:

   ```bash
   git commit -am "chore: re-pin upstream to <new-sha> for OWUI <x.y.z>"
   git tag v<upstream-version>      # e.g., v0.2.3
   git push --follow-tags
   ```

   The `Release Image` workflow publishes `:stable` + `:<tag-without-leading-v>` to ghcr.io (e.g., `:0.2.3`).

   *Edge case*: if a fork-side change (CI workflow, drift script, README) needs to ship without an upstream pin bump, force-retag (delete `v<version>` then re-tag) — accepted because it only re-publishes a deterministic build of the same vendored source. Note this in the CHANGELOG entry. If this becomes frequent, introduce a `-N` suffix scheme on the tag.

7. **Smoke** with the new image against a staging OpenWebUI, then bump both the `open-webui` and `open-webui-mcp` image pins in your deployment compose together.

## What we do **not** patch in this repo

- The wrapper's tool generation logic (`openapi_provider.py`).
- The auth middleware (`auth.py`).
- The OpenWebUI OpenAPI snapshot under `src/openwebui_mcp/specs/` — that file is byte-identical to upstream. When upstream's snapshot lags our deployed OWUI we don't edit it in place; instead we either wait for upstream or apply a downstream-only spec patch (next section).

If you're reaching for a wrapper-source change, that probably belongs upstream.

## Downstream-only spec patch (`-N` suffix releases)

Default policy when the bundled spec lags live OWUI is to wait for upstream to re-snapshot. When upstream has stalled long enough that waiting is no longer tenable, we apply a TETRA-side spec patch on top of the unchanged upstream pin:

1. Snapshot the live OWUI's `/openapi.json` into `patches/specs/open-webui.openapi.json` using 2-space indent and sorted keys to match upstream's formatting:

   ```bash
   curl -fsSL https://owui.example.com/openapi.json \
     | python3 -c 'import json,sys; d=json.load(sys.stdin); json.dump(d, open("patches/specs/open-webui.openapi.json","w"), indent=2, sort_keys=True)'
   ```

2. Confirm the Dockerfile has a `COPY patches/specs/open-webui.openapi.json ./src/openwebui_mcp/specs/open-webui.openapi.json` line after `COPY src/ ./src/`. The byte-identical vendor tree at `src/openwebui_mcp/specs/` is left alone — the patch lands only in the built image.

3. Tag with the `-N` suffix scheme: keep the upstream `project.version` and append `-1`, `-2`, ... per consecutive downstream-only release. Example: `v0.2.2-1`, `v0.2.2-2`. The release workflow's `v*.*.*` glob accepts these tags; the version-extraction step strips the leading `v` and feeds the remainder to the image tag (`:0.2.2-1`).

4. Document the patch in `CHANGELOG.md` under a `[<version>-<N>]` heading, naming the upstream SHA still in force, the OWUI source for the spec, and the operations / schema deltas the patch resolves.

5. Reset the suffix back to `-1` (or drop it) the next time the upstream SHA pin is bumped — the patch is then either folded into upstream's snapshot or carried forward as `-1` again on the new pin.

## Drift detection

The drift workflow has three layers:

1. **`scripts/check-spec-drift.sh`** — local, on-demand. Resolves the *effective* wrapper spec (preferring `patches/specs/open-webui.openapi.json` when present, falling back to `src/openwebui_mcp/specs/open-webui.openapi.json`), fetches `/openapi.json` from the live OpenWebUI, and reports four classes of drift: removed operations, added operations, operationId renames, and body-schema deltas (delegated to `scripts/check-body-schema-drift.py`). Override the spec source with `--source <path>` if needed.

2. **`spec-drift-monitor.yml`** — daily 06:00 UTC cron + `workflow_dispatch`. Runs the drift check against the URL stored in the repo variable `OWUI_URL` (overridable via dispatch input). On drift, opens or updates a single tracking issue labelled `spec-drift`. On clean, auto-closes the open tracking issue with a comment. Title is fixed (`Spec drift detected against live OpenWebUI`); do not rename it manually.

3. **`release-image.yml` pre-release gate** — runs the drift check before publishing `:stable` + `:<version>`. A non-zero exit aborts the release. Two emergency overrides: include `[skip-drift]` in the tag annotation message (e.g., `git tag -a -m 'docs-only release [skip-drift]' v0.2.2-2`), or run the workflow via `workflow_dispatch` with `skip_drift_check: true`. The `OWUI_URL` repo variable must be set; if absent, the gate fails closed.

Standard release flow when drift is reported by the monitor: snapshot the live `/openapi.json` into `patches/specs/`, commit + tag a `-N` release, push. The drift gate at release time should then pass cleanly because the `patches/` overlay is the effective spec.

## Releasing

- `:latest` publishes automatically on every push to `main` (CI `docker` job).
- `:stable` + `:<version>` publish on `v*.*.*` git tags (Release Image workflow), gated by the live-OWUI drift check (see above).
- Space tag-driven releases ≥30 min apart to avoid GitHub Actions release-cadence rate limits.

## License

MIT — same as upstream. See `LICENSE` and `NOTICE`.
