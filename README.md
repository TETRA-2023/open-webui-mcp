# open-webui-mcp

A vendored fork of [stephanschielke/open-webui-mcp-server](https://github.com/stephanschielke/open-webui-mcp-server) packaged for container deployment, with a SHA-pinned upstream snapshot, a published `ghcr.io` image, and a small drift-detection helper.

Vendored at upstream commit `85d88af6e3dd34183a5a0eefb85d474f3e3c2b54` (2026-04-07). The wrapper source under `src/openwebui_mcp/` is byte-identical to upstream — see [NOTICE](NOTICE) for full attribution.

## What it does

Exposes OpenWebUI's admin REST API as a Model Context Protocol (MCP) server. Tool definitions are generated from a bundled snapshot of OpenWebUI's OpenAPI spec via [FastMCP](https://github.com/jlowin/fastmcp); 317 tools survive the upstream `RouteMap` filter (after excluding `/ollama/*`, `/openai/*`, `/api/v1/{analytics,evaluations,terminals,pipelines}/*`, and any non-`/api/v1/` paths).

This image is intended to run behind an authenticating MCP gateway (e.g. LiteLLM, an mTLS proxy, or anything that fronts streamable-HTTP MCP). It exposes the full OpenWebUI admin surface — including mutating and destructive operations — by design. Do not expose port 7999 to untrusted networks; always front it with bearer auth or equivalent.

## Deployment

```yaml
services:
  open-webui-mcp:
    image: ghcr.io/tetra-2023/open-webui-mcp:stable
    environment:
      WEBUI_URL: http://open-webui:8080         # base URL of your OpenWebUI
      WEBUI_API_KEY: ${WEBUI_API_KEY}           # admin token sourced from your secrets store
      MCP_TRANSPORT: http
      MCP_HTTP_HOST: 0.0.0.0
      MCP_HTTP_PORT: "7999"
      MCP_HTTP_PATH: /mcp
    depends_on: [open-webui]
```

Pin to a specific tag (`:0.2.2`) or digest in production. `:stable` floats with the most recent release tag; `:latest` floats with `main`.

## Local run (debug)

```bash
docker run --rm -p 7999:7999 \
  -e WEBUI_URL=http://host.docker.internal:8080 \
  -e WEBUI_API_KEY=$WEBUI_API_KEY \
  -e MCP_TRANSPORT=http \
  -e MCP_HTTP_HOST=0.0.0.0 \
  ghcr.io/tetra-2023/open-webui-mcp:stable
```

## Spec drift check

When upgrading OpenWebUI, run the drift check before bumping this wrapper. The bundled OpenAPI snapshot drives tool generation, so a mismatch between the snapshot and live OWUI causes the wrapper to advertise tool schemas that no longer match the running endpoints.

```bash
WEBUI_API_KEY=... ./scripts/check-spec-drift.sh https://owui.example.com
```

Reports added / removed / renamed operations between the bundled snapshot and the live OWUI's `/openapi.json`. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full bump procedure.

## Tags published on ghcr.io

| Tag | When | Source |
|---|---|---|
| `:latest` | every push to `main` | CI `docker` job |
| `:stable` | every `v*.*.*` git tag | Release Image workflow |
| `:<version>` | every `v*.*.*` git tag | Release Image workflow |

## License

MIT — see [LICENSE](LICENSE) (verbatim from upstream) and [NOTICE](NOTICE) (fork attribution + modifications).

## Refs

- Upstream source: https://github.com/stephanschielke/open-webui-mcp-server
- Original fork: https://github.com/troylar/open-webui-mcp-server
- OpenWebUI upstream RFE for a first-party admin MCP: https://github.com/open-webui/open-webui/discussions/16891
