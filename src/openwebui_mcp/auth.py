import os
from contextvars import ContextVar
from typing import Optional

# Context variable to store the current user's token
_current_user_token: ContextVar[Optional[str]] = ContextVar("current_user_token", default=None)


def get_user_token() -> Optional[str]:
    """Get the current user's token from context or environment."""
    token = _current_user_token.get()
    if token:
        return token
    return os.getenv("WEBUI_API_KEY")


def set_user_token(token: str | None) -> None:
    _current_user_token.set(token)


class AuthMiddleware:
    """ASGI middleware to extract Authorization header and set context variable."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode()
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                _current_user_token.set(token)
        await self.app(scope, receive, send)
