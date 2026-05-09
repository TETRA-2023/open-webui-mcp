# open-webui-mcp

TETRA fleet wrapper of [stephanschielke/open-webui-mcp-server](https://github.com/stephanschielke/open-webui-mcp-server).

Vendored at upstream commit `85d88af6e3dd34183a5a0eefb85d474f3e3c2b54` (2026-04-07). See [NOTICE](NOTICE) for fork attribution and rationale.

## What it does

Exposes OpenWebUI's admin REST API as a Model Context Protocol (MCP) server. Tool definitions are generated from a bundled snapshot of OpenWebUI's OpenAPI spec via [FastMCP](https://github.com/jlowin/fastmcp); 317 tools survive the upstream `RouteMap` filter (after excluding `/ollama/*`, `/openai/*`, `/api/v1/{analytics,evaluations,terminals,pipelines}/*`, and any non-`/api/v1/` paths).

Within the TETRA fleet this image runs as the `open-webui-mcp` sidecar in `TETRA-OPEN-WEBUI`, fronted by the LiteLLM gateway with bearer auth and team-scoped to `TETRA-OPS`. See US #871 in project Tetra for the deployment plan.

## Deployment

```yaml
# TETRA-OPEN-WEBUI/docker-compose.yml (excerpt)
services:
  open-webui-mcp:
    image: ghcr.io/tetra-2023/open-webui-mcp:stable
    environment:
      WEBUI_URL: http://open-webui:8080
      WEBUI_API_KEY: ${WEBUI_API_KEY}        # admin token, see TETRA-OPEN-WEBUI/stack.env
      MCP_TRANSPORT: http
      MCP_HTTP_HOST: 0.0.0.0
      MCP_HTTP_PORT: "7999"
      MCP_HTTP_PATH: /mcp
    depends_on: [open-webui]
```

Pin to a specific tag (`:0.2.2-tetra1`) or digest in production. `:stable` floats with the most recent release tag; `:latest` floats with `main`.

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

When bumping OpenWebUI, run the drift check before bumping the wrapper:

```bash
./scripts/check-spec-drift.sh https://owui.example.com  # uses $WEBUI_API_KEY
```

Reports added / removed / changed operations between the bundled snapshot and the live OWUI's `/openapi.json`. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full bump procedure.

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
- OpenWebUI upstream RFE for first-party admin MCP: https://github.com/open-webui/open-webui/discussions/16891
- Deployment US: project Tetra (#9), US #871
