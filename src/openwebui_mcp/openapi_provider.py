"""OpenAPI-based MCP provider for Open WebUI.

Wraps OpenWebUI's OpenAPI specification with FastMCP's OpenAPIProvider,
injecting per-request authentication and curating which endpoints become tools.
"""

import json
import os
from pathlib import Path

import httpx
from fastmcp import FastMCP
from fastmcp.server.providers.openapi import MCPType, RouteMap

from openwebui_mcp.auth import get_user_token

SPECS_DIR = Path(__file__).parent / "specs"


def _load_openapi_spec() -> dict:
    spec_path = SPECS_DIR / "open-webui.openapi.json"
    with open(spec_path) as f:
        return json.load(f)


def _build_route_maps() -> list[RouteMap]:
    return [
        RouteMap(pattern=r"^/ollama/.*", mcp_type=MCPType.EXCLUDE),
        RouteMap(pattern=r"^/openai/.*", mcp_type=MCPType.EXCLUDE),
        RouteMap(pattern=r"^/api/v1/analytics/.*", mcp_type=MCPType.EXCLUDE),
        RouteMap(pattern=r"^/api/v1/evaluations/.*", mcp_type=MCPType.EXCLUDE),
        RouteMap(pattern=r"^/api/v1/terminals/.*", mcp_type=MCPType.EXCLUDE),
        RouteMap(pattern=r"^/api/v1/pipelines/.*", mcp_type=MCPType.EXCLUDE),
        RouteMap(pattern=r"^/api/(?!v1/).*", mcp_type=MCPType.EXCLUDE),
        RouteMap(mcp_type=MCPType.TOOL, mcp_tags={"openapi", "auto-generated"}),
    ]


class AuthTransport(httpx.AsyncBaseTransport):
    """Custom transport that injects Bearer auth from context per-request."""

    def __init__(self, base_url: str):
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=60.0)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        token = get_user_token()
        if token:
            request.headers["Authorization"] = f"Bearer {token}"
        if request.url.is_relative_url:
            request.url = httpx.URL(f"{self._base_url}{request.url}")
        return await self._client.send(request)

    async def aclose(self) -> None:
        await self._client.aclose()


def create_mcp_server() -> FastMCP:
    spec = _load_openapi_spec()
    route_maps = _build_route_maps()

    webui_url = os.getenv("WEBUI_URL", "http://localhost:3000")
    transport = AuthTransport(webui_url)
    client = httpx.AsyncClient(transport=transport, base_url=webui_url)

    mcp = FastMCP.from_openapi(
        openapi_spec=spec,
        client=client,
        name="openwebui-mcp-server",
        route_maps=route_maps,
        tags={"openwebui"},
    )

    return mcp
