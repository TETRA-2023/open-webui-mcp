"""Open WebUI MCP Server - Main entry point."""

import os
import sys

from openwebui_mcp.auth import AuthMiddleware
from openwebui_mcp.openapi_provider import create_mcp_server


def main():
    """Run the MCP server."""
    if not os.getenv("WEBUI_URL"):
        print("ERROR: WEBUI_URL environment variable is required", file=sys.stderr)
        print("Example: export WEBUI_URL=https://ai.example.com", file=sys.stderr)
        sys.exit(1)

    mcp = create_mcp_server()
    transport = os.getenv("MCP_TRANSPORT", "stdio").lower()

    if transport == "http":
        host = os.getenv("MCP_HTTP_HOST", "127.0.0.1")
        port = int(os.getenv("MCP_HTTP_PORT", "8000"))
        path = os.getenv("MCP_HTTP_PATH", "/mcp")

        import uvicorn

        app = mcp.http_app(path=path)
        app = AuthMiddleware(app)
        print(f"Starting Open WebUI MCP server on http://{host}:{port}{path}", file=sys.stderr)
        uvicorn.run(app, host=host, port=port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
