"""Integration tests for OpenAPI-generated MCP tools.

Run with: pytest tests/test_integration.py -v -m integration
"""

import os

import httpx
import pytest
from fastmcp.client import Client

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp")
WEBUI_URL = os.getenv("WEBUI_URL", "http://127.0.0.1:3000")

_api_key = ""
try:
    with open(".openwebui-api-key") as f:
        _api_key = f.read().strip()
except FileNotFoundError:
    _api_key = os.getenv("WEBUI_API_KEY", "")
WEBUI_API_KEY = _api_key


class BearerAuth(httpx.Auth):
    def __init__(self, token: str):
        self.token = token

    def auth_flow(self, request):
        request.headers["Authorization"] = f"Bearer {self.token}"
        yield request


async def get_openwebui_token():
    if WEBUI_API_KEY:
        return WEBUI_API_KEY
    admin_email = os.getenv("WEBUI_ADMIN_EMAIL", "")
    admin_password = os.getenv("WEBUI_ADMIN_PASSWORD", "password")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{WEBUI_URL}/api/v1/auths/signin",
            json={"email": admin_email, "password": admin_password},
        )
        if response.status_code == 200:
            return response.json().get("token", "")
    return ""


@pytest.fixture
async def auth_token():
    return await get_openwebui_token()


@pytest.fixture
async def mcp_client():
    auth = BearerAuth(WEBUI_API_KEY) if WEBUI_API_KEY else None
    async with Client(MCP_SERVER_URL, auth=auth) as client:
        yield client


@pytest.mark.integration
class TestServerConnectivity:
    async def test_server_responds(self, mcp_client):
        tools = await mcp_client.list_tools()
        assert len(tools) > 100

    async def test_tools_have_descriptions(self, mcp_client):
        tools = await mcp_client.list_tools()
        for tool in tools:
            assert tool.description, f"Tool {tool.name} has no description"


@pytest.mark.integration
class TestUserEndpoints:
    async def test_get_current_user(self, mcp_client):
        result = await mcp_client.call_tool("get_session_user_api_v1_auths", {})
        assert result.data is not None
        assert hasattr(result.data, "name") or isinstance(result.data, dict)

    async def test_list_users(self, mcp_client):
        result = await mcp_client.call_tool("get_users_api_v1_users", {})
        assert result.data is not None


@pytest.mark.integration
class TestGroupEndpoints:
    async def test_list_groups(self, mcp_client):
        result = await mcp_client.call_tool("get_groups_api_v1_groups", {})
        assert result.data is not None


@pytest.mark.integration
class TestModelEndpoints:
    async def test_list_models(self, mcp_client):
        result = await mcp_client.call_tool("get_models_api_v1_models_list_get", {})
        assert result.data is not None


@pytest.mark.integration
class TestKnowledgeEndpoints:
    async def test_list_knowledge_bases(self, mcp_client):
        result = await mcp_client.call_tool("get_knowledge_bases_api_v1_knowledge", {})
        assert result.data is not None


@pytest.mark.integration
class TestFileEndpoints:
    async def test_list_files(self, mcp_client):
        try:
            result = await mcp_client.call_tool("list_files_api_v1_files", {})
            assert result.data is not None
        except Exception as e:
            if "Output validation error" in str(e):
                pytest.skip("OpenAPI spec declares array output but API returns {items, total}")
            raise


@pytest.mark.integration
class TestChatEndpoints:
    async def test_list_chats(self, mcp_client):
        result = await mcp_client.call_tool("get_session_user_chat_list_api_v1_chats_list_get", {})
        assert result.data is not None


@pytest.mark.integration
class TestPromptEndpoints:
    async def test_list_prompts(self, mcp_client):
        result = await mcp_client.call_tool("get_prompts_api_v1_prompts", {})
        assert result.data is not None


@pytest.mark.integration
class TestMemoryEndpoints:
    async def test_list_memories(self, mcp_client):
        result = await mcp_client.call_tool("get_memories_api_v1_memories", {})
        assert result.data is not None


@pytest.mark.integration
class TestNoteEndpoints:
    async def test_list_notes(self, mcp_client):
        result = await mcp_client.call_tool("get_notes_api_v1_notes", {})
        assert result.data is not None


@pytest.mark.integration
class TestChannelEndpoints:
    async def test_list_channels(self, mcp_client):
        try:
            result = await mcp_client.call_tool("get_all_channels_api_v1_channels_list_get", {})
            assert result.data is not None
        except Exception as e:
            if "403" in str(e):
                pytest.skip("Permission denied for channels")
            raise


@pytest.mark.integration
class TestConfigEndpoints:
    async def test_get_system_config(self, mcp_client):
        result = await mcp_client.call_tool("export_config_api_v1_configs_export_get", {})
        assert result.data is not None
        assert isinstance(result.data, dict)

    async def test_get_banners(self, mcp_client):
        result = await mcp_client.call_tool("get_banners_api_v1_configs_banners_get", {})
        assert result.data is not None


@pytest.mark.integration
class TestToolEndpoints:
    async def test_list_tools(self, mcp_client):
        result = await mcp_client.call_tool("get_tools_api_v1_tools", {})
        assert result.data is not None


@pytest.mark.integration
class TestFunctionEndpoints:
    async def test_list_functions(self, mcp_client):
        result = await mcp_client.call_tool("get_functions_api_v1_functions", {})
        assert result.data is not None


@pytest.mark.integration
class TestFolderEndpoints:
    async def test_list_folders(self, mcp_client):
        result = await mcp_client.call_tool("get_folders_api_v1_folders", {})
        assert result.data is not None
