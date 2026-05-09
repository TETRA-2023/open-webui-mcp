ARG PYTHON_VERSION="3.10"
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml uv.lock README.md ./
COPY src/openwebui_mcp/specs/ ./src/openwebui_mcp/specs/

# Install dependencies
RUN uv --python-preference=only-system sync --locked --no-install-project

# Copy application code
COPY src/ ./src/

# Install the project itself
RUN uv --python-preference=only-system sync --locked

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"
ENV MCP_TRANSPORT="http"
ENV MCP_HTTP_HOST="0.0.0.0"
ENV MCP_HTTP_PORT=7999
ENV MCP_HTTP_PATH="/mcp"

# Expose MCP port
EXPOSE ${MCP_HTTP_PORT}

# Run the MCP server
CMD ["openwebui-mcp"]
